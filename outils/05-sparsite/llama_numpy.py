"""Passe avant d'un modèle d'architecture « llama » (GGUF F16), en numpy pur,
avec un crochet sur l'entrée de chaque projection linéaire.

Pourquoi l'écrire : mesurer la sparsité des activations (Deja Vu, CATS, TEAL,
PowerInfer), il faut voir le vecteur qui entre dans chaque matrice et pouvoir
en mettre des composantes à zéro. Une composante nulle à l'entrée de W, c'est
une colonne de W qu'on n'a pas besoin de lire : c'est là que la sparsité se
convertit en octets économisés.

Les quatre entrées crochetées, par couche :
  'attn_in' : h = rmsnorm(x), entrée de Wq, Wk, Wv (3 matrices)
  'o_in'    : sortie concaténée de l'attention, entrée de Wo
  'ffn_in'  : h = rmsnorm(x), entrée de Wgate et Wup (2 matrices)
  'down_in' : a = silu(Wgate h) * (Wup h), entrée de Wdown

Conventions de llama.cpp pour l'architecture llama : le convertisseur permute
les lignes de Wq et Wk pour que la rotation RoPE « normale » (paires de
composantes voisines (2i, 2i+1)) donne le même résultat que la rotation par
moitiés du modèle d'origine. On applique donc la rotation par paires voisines.
Le témoin est la perplexité de llama-perplexity sur les mêmes jetons.
"""
from __future__ import annotations

import numpy as np

from gguf_f16 import Lecteur

ENTREES = ("attn_in", "o_in", "ffn_in", "down_in")


class Modele:
    def __init__(self, chemin: str):
        L = Lecteur(chemin)
        m = L.meta
        a = m["general.architecture"]
        if a != "llama":
            raise ValueError(f"architecture {a} : seule 'llama' est prise en charge")
        self.n_couches = int(m[f"{a}.block_count"])
        self.d = int(m[f"{a}.embedding_length"])
        self.n_tetes = int(m[f"{a}.attention.head_count"])
        self.n_kv = int(m[f"{a}.attention.head_count_kv"])
        self.d_tete = self.d // self.n_tetes
        self.eps = float(m[f"{a}.attention.layer_norm_rms_epsilon"])
        self.base = float(m.get(f"{a}.rope.freq_base", 10000.0))
        self.embd = L.tableau("token_embd.weight")
        self.sortie = (L.tableau("output.weight") if "output.weight" in L.tenseurs
                       else self.embd)
        self.norm_finale = L.tableau("output_norm.weight")
        self.c = []
        for i in range(self.n_couches):
            p = f"blk.{i}."
            self.c.append({k: L.tableau(p + k + ".weight") for k in (
                "attn_norm", "attn_q", "attn_k", "attn_v", "attn_output",
                "ffn_norm", "ffn_gate", "ffn_up", "ffn_down")})
        self.d_ffn = self.c[0]["ffn_gate"].shape[0]
        self._rope_cache = {}

    def _rmsnorm(self, x, w):
        return x / np.sqrt(np.mean(x * x, axis=-1, keepdims=True) + self.eps) * w

    def _rope(self, n):
        if n not in self._rope_cache:
            i = np.arange(self.d_tete // 2, dtype=np.float64)
            freq = self.base ** (-2.0 * i / self.d_tete)
            ang = np.arange(n, dtype=np.float64)[:, None] * freq[None, :]
            self._rope_cache[n] = (np.cos(ang).astype(np.float32),
                                   np.sin(ang).astype(np.float32))
        return self._rope_cache[n]

    def _tourner(self, t, cos, sin):
        # t : (n, tetes, d_tete) ; paires voisines (2i, 2i+1).
        a, b = t[..., 0::2], t[..., 1::2]
        c, s = cos[:, None, :], sin[:, None, :]
        r = np.empty_like(t)
        r[..., 0::2] = a * c - b * s
        r[..., 1::2] = a * s + b * c
        return r

    def avant(self, jetons, crochet=None, depuis=0):
        """Renvoie les logits (n - depuis, vocab) des positions depuis..n-1.
        crochet(couche, entree, v) -> v, où v a la forme (n, dim) ; il peut
        lire v (statistiques) ou le modifier."""
        n = len(jetons)
        x = self.embd[np.asarray(jetons)]
        cos, sin = self._rope(n)
        masque = np.triu(np.full((n, n), -np.inf, dtype=np.float32), 1)
        g = self.n_tetes // self.n_kv
        for i, c in enumerate(self.c):
            h = self._rmsnorm(x, c["attn_norm"])
            if crochet:
                h = crochet(i, "attn_in", h)
            q = (h @ c["attn_q"].T).reshape(n, self.n_tetes, self.d_tete)
            k = (h @ c["attn_k"].T).reshape(n, self.n_kv, self.d_tete)
            v = (h @ c["attn_v"].T).reshape(n, self.n_kv, self.d_tete)
            q, k = self._tourner(q, cos, sin), self._tourner(k, cos, sin)
            k = np.repeat(k, g, axis=1)
            v = np.repeat(v, g, axis=1)
            s = np.einsum("qhd,khd->hqk", q, k) / np.sqrt(self.d_tete) + masque
            s -= s.max(axis=-1, keepdims=True)
            p = np.exp(s)
            p /= p.sum(axis=-1, keepdims=True)
            o = np.einsum("hqk,khd->qhd", p, v).reshape(n, self.d)
            if crochet:
                o = crochet(i, "o_in", o)
            x = x + o @ c["attn_output"].T
            h = self._rmsnorm(x, c["ffn_norm"])
            if crochet:
                h = crochet(i, "ffn_in", h)
            gt = h @ c["ffn_gate"].T
            a = gt / (1.0 + np.exp(-gt)) * (h @ c["ffn_up"].T)
            if crochet:
                a = crochet(i, "down_in", a)
            x = x + a @ c["ffn_down"].T
        x = self._rmsnorm(x[depuis:], self.norm_finale)
        return x @ self.sortie.T

    def octets_par_entree(self, octets_par_poids=2.0):
        """Octets de poids lus derrière chaque entrée crochetée, par couche."""
        c = self.c[0]
        lignes = {
            "attn_in": c["attn_q"].shape[0] + c["attn_k"].shape[0] + c["attn_v"].shape[0],
            "o_in": c["attn_output"].shape[0],
            "ffn_in": c["ffn_gate"].shape[0] + c["ffn_up"].shape[0],
            "down_in": c["ffn_down"].shape[0],
        }
        largeur = {"attn_in": self.d, "o_in": self.d, "ffn_in": self.d,
                   "down_in": self.d_ffn}
        return {e: lignes[e] * largeur[e] * octets_par_poids for e in ENTREES}, largeur


def nll_chunk(logits, jetons, premier):
    """Somme des -log p(jeton suivant) pour les positions premier..n-2, comme
    llama-perplexity (la seconde moitié de chaque fenêtre). logits porte les
    positions premier..n-1 (avant(..., depuis=premier))."""
    z = logits[:-1].astype(np.float64)
    z -= z.max(axis=-1, keepdims=True)
    lse = np.log(np.exp(z).sum(axis=-1))
    cible = np.asarray(jetons[premier + 1:])
    return float(np.sum(lse - z[np.arange(len(cible)), cible])), len(cible)
