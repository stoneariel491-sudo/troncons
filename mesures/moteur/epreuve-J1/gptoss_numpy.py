"""Une troisième passe avant de gpt-oss, en numpy f64, écrite par le juge de l'épreuve J1.

Pourquoi : C4 juge troncons et llama.cpp contre la référence f64 du lot R (trc-reference), et les
noyaux de troncons ont été validés contre cette même référence (K3). Si la référence se trompait
d'une convention, troncons hériterait de l'erreur et C4 ne le verrait pas. Ce calcul n'importe rien
d'un lot : il lit le GGUF par le lecteur écrit pour l'épreuve (decodeur_s4.Gguf) et suit la forme du
modèle publiée par OpenAI (gpt_oss/torch/model.py, licence Apache-2.0 ; rien n'est copié : chaque
opération est réécrite ici depuis sa définition) :
  - x = enchâssement(jeton) ;
  - par couche ℓ : t = RMSNorm(x) ; q, k, v = projections + biais ; RoPE (moitiés, « NeoX ») avec la
    rampe de YaRN réelle (truncate = false) et la concentration 0,1 ln 32 + 1 sur cos et sin ;
    attention à 64 têtes q, 8 têtes kv (la tête q h lit la tête kv ⌊h/8⌋), échelle 1/8, puits appris
    par tête ajouté au dénominateur du softmax, fenêtre de 128 clés (j > i − 128) sur les couches
    paires ; sortie + biais ; x += ... ;
    t = RMSNorm(x) ; logits du routeur (+ biais) ; les 4 plus grands, softmax sur ces 4 ; pour chaque
    expert : g = W_gate t + b, u = W_up t + b ; g ← min(g, 7) ; u ← clamp(u, −7, 7) ;
    a = g · σ(1,702 g) · (u + 1) ; W_down a + b ; x += Σ poids · sortie ;
  - logits = W_out · RMSNorm(x).
Tout en f64 ; les poids sont déquantifiés exactement (Q8_0 : d·q ; MXFP4 : k[code]·2^(e−128), k les
grandeurs E2M1 doublées, les 16 premiers éléments d'un bloc dans les demi-octets bas).

Variante --rampe llamacpp : bornes de la rampe arrondies (bas vers le bas, haut vers le haut), la
forme de ggml_rope_yarn_corr_dims ; pour savoir de quel côté tombe chaque fichier.

Sortie : un .npz des log-probabilités f64 des positions notées [n_ctx/2, P) de la fenêtre, et un
journal JSON. Commande :
  python -I -X utf8 gptoss_numpy.py <modele.gguf> <base.kld> <sortie.npz> [--fenetre 0]
         [--positions 288] [--rampe openai|llamacpp]
"""
import argparse
import datetime
import json
import math
import os
import struct
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decodeur_s4 import Gguf  # noqa: E402  (lecteur GGUF écrit pour l'épreuve)

K2 = np.array([0, 1, 2, 3, 4, 6, 8, 12, -0.0, -1, -2, -3, -4, -6, -8, -12], np.float64)


def lire_kld_entete(chemin):
    with open(chemin, "rb") as f:
        tete = f.read(20)
        if tete[:8] != b"_logits_":
            raise ValueError("pas un fichier de logits de llama-perplexity")
        n_ctx, n_vocab, n_chunk = struct.unpack("<Iii", tete[8:20])
        jetons = np.frombuffer(f.read(4 * n_ctx * n_chunk), "<i4").reshape(n_chunk, n_ctx)
    return n_ctx, n_vocab, n_chunk, jetons


class Poids:
    def __init__(self, g: Gguf):
        self.g = g

    def brut(self, nom, decalage=0, octets=None):
        t = self.g.tenseurs[nom]
        n = t["octets"] if octets is None else octets
        return self.g.lire(t["absolu"] + decalage, n)

    def f32(self, nom):
        t = self.g.tenseurs[nom]
        assert t["type"] == 0, nom
        return np.frombuffer(self.brut(nom), "<f4").astype(np.float64)

    def q8_0_lignes(self, nom, debut, n):
        """Lignes [debut, debut + n) d'un tenseur Q8_0 (ne = [C, R]) → (n, C) f64."""
        t = self.g.tenseurs[nom]
        assert t["type"] == 8, nom
        C = t["ne"][0]
        B = C // 32
        b = np.frombuffer(self.brut(nom, debut * B * 34, n * B * 34), np.uint8).reshape(n * B, 34)
        d = b[:, :2].copy().view("<f2").astype(np.float64)
        q = b[:, 2:].view(np.int8).astype(np.float64)
        return (d * q).reshape(n, C)

    def q8_0(self, nom):
        R = self.g.tenseurs[nom]["ne"][1]
        return self.q8_0_lignes(nom, 0, R)

    def mxfp4_expert(self, nom, x):
        """Matrice de l'expert x d'un tenseur MXFP4 (ne = [C, R, E]) → (R, C) f64."""
        t = self.g.tenseurs[nom]
        assert t["type"] == 39, nom
        C, R = t["ne"][0], t["ne"][1]
        B = C // 32
        n = R * B * 17
        b = np.frombuffer(self.brut(nom, x * n, n), np.uint8).reshape(R * B, 17)
        e = b[:, 0].astype(np.int64)
        qs = b[:, 1:]
        codes = np.concatenate([qs & 0x0F, qs >> 4], axis=1)
        v = K2[codes] * np.ldexp(1.0, e - 128)[:, None]
        return v.reshape(R, C)

    def biais_expert(self, nom, x):
        t = self.g.tenseurs[nom]
        R = t["ne"][0]
        return np.frombuffer(self.brut(nom, x * R * 4, R * 4), "<f4").astype(np.float64)


def rmsnorm(x, w, eps):
    return x / np.sqrt(np.mean(x * x, axis=-1, keepdims=True) + eps) * w


def yarn(base, facteur, ctx0, beta_rapide, beta_lent, d, rampe):
    demi = d // 2
    freq = base ** (np.arange(0, d, 2, dtype=np.float64) / d)
    bas = demi * math.log(ctx0 / (beta_rapide * 2 * math.pi)) / math.log(base)
    haut = demi * math.log(ctx0 / (beta_lent * 2 * math.pi)) / math.log(base)
    if rampe == "llamacpp":
        bas, haut = max(0.0, math.floor(bas)), min(d - 1.0, math.ceil(haut))
    interp = 1.0 / (facteur * freq)
    extrap = 1.0 / freq
    r = np.clip((np.arange(demi, dtype=np.float64) - bas) / (haut - bas), 0.0, 1.0)
    masque = 1.0 - r
    inv = interp * (1 - masque) + extrap * masque
    return inv, 0.1 * math.log(facteur) + 1.0, (bas, haut)


def rope(x, pos, inv, conc):
    """x : (P, têtes, 64) ; rotation par moitiés."""
    ang = pos[:, None] * inv[None, :]
    c = (np.cos(ang) * conc)[:, None, :]
    s = (np.sin(ang) * conc)[:, None, :]
    d = x.shape[-1] // 2
    x1, x2 = x[..., :d], x[..., d:]
    return np.concatenate([x1 * c - x2 * s, x2 * c + x1 * s], axis=-1)


def principal():
    ap = argparse.ArgumentParser()
    ap.add_argument("gguf")
    ap.add_argument("kld")
    ap.add_argument("sortie")
    ap.add_argument("--fenetre", type=int, default=0)
    ap.add_argument("--positions", type=int, default=288)
    ap.add_argument("--rampe", choices=["openai", "llamacpp"], default="openai")
    ap.add_argument("--jetons", help="fichier des identifiants (liste Python, sortie de llama-tokenize --ids) "
                                     "au lieu d'une fenêtre du .kld ; les positions notées sont alors les "
                                     "--dernieres dernières")
    ap.add_argument("--dernieres", type=int, default=1)
    ap.add_argument("--kv-f16", action="store_true",
                    help="imitation : k (après RoPE) et v arrondis en f16 au plus proche, comme le cache KV du moteur")
    ap.add_argument("--argmax-toutes", action="store_true",
                    help="garde aussi l'argmax et sa log-probabilité à CHAQUE position (tête de sortie en lots)")
    a = ap.parse_args()
    t_debut = time.time()

    g = Gguf(a.gguf)
    W = Poids(g)
    kv = g.kv
    arch = kv["general.architecture"]
    L = kv[f"{arch}.block_count"]
    nq = kv[f"{arch}.attention.head_count"]
    nkv = kv[f"{arch}.attention.head_count_kv"]
    dt = kv[f"{arch}.attention.key_length"]
    eps = kv[f"{arch}.attention.layer_norm_rms_epsilon"]
    fen = kv[f"{arch}.attention.sliding_window"]
    E = kv[f"{arch}.expert_count"]
    k = kv[f"{arch}.expert_used_count"]
    inv, conc, bornes = yarn(kv[f"{arch}.rope.freq_base"], kv[f"{arch}.rope.scaling.factor"],
                             kv[f"{arch}.rope.scaling.original_context_length"],
                             kv[f"{arch}.rope.scaling.yarn_beta_fast"],
                             kv[f"{arch}.rope.scaling.yarn_beta_slow"], dt, a.rampe)

    n_ctx, n_vocab, n_chunk, jetons = lire_kld_entete(a.kld)
    if a.jetons:
        import ast
        ids = np.array(ast.literal_eval(open(a.jetons).read().strip().splitlines()[-1]), np.int64)
        P = ids.size
    else:
        P = a.positions
        ids = jetons[a.fenetre, :P].astype(np.int64)
    pos = np.arange(P, dtype=np.float64)

    # enchâssement : une ligne Q8_0 par jeton
    x = np.stack([W.q8_0_lignes("token_embd.weight", int(t), 1)[0] for t in ids])
    masque_causal = np.triu(np.full((P, P), -np.inf), 1)
    i = np.arange(P)
    masque_fenetre = np.where(i[None, :] <= i[:, None] - fen, -np.inf, 0.0)
    routage = np.zeros((L, P, k), np.int64)
    t_couches = []
    for l in range(L):
        tc = time.time()
        p = f"blk.{l}."
        t = rmsnorm(x, W.f32(p + "attn_norm.weight"), eps)
        q = t @ W.q8_0(p + "attn_q.weight").T + W.f32(p + "attn_q.bias")
        kk = t @ W.q8_0(p + "attn_k.weight").T + W.f32(p + "attn_k.bias")
        v = t @ W.q8_0(p + "attn_v.weight").T + W.f32(p + "attn_v.bias")
        q = rope(q.reshape(P, nq, dt), pos, inv, conc)
        kk = rope(kk.reshape(P, nkv, dt), pos, inv, conc)
        v = v.reshape(P, nkv, dt)
        if a.kv_f16:
            kk = kk.astype(np.float16).astype(np.float64)
            v = v.astype(np.float16).astype(np.float64)
        puits = W.f32(p + "attn_sinks.weight")
        masque = masque_causal + (masque_fenetre if l % 2 == 0 else 0.0)
        sortie = np.empty((P, nq, dt))
        for h in range(nq):
            hk = h // (nq // nkv)
            s = (q[:, h, :] @ kk[:, hk, :].T) / math.sqrt(dt) + masque
            m = np.maximum(s.max(axis=1), puits[h])
            e = np.exp(s - m[:, None])
            den = e.sum(axis=1) + np.exp(puits[h] - m)
            sortie[:, h, :] = (e / den[:, None]) @ v[:, hk, :]
        x = x + sortie.reshape(P, nq * dt) @ W.q8_0(p + "attn_output.weight").T + W.f32(p + "attn_output.bias")

        t = rmsnorm(x, W.f32(p + "post_attention_norm.weight"), eps)
        wr = W.f32(p + "ffn_gate_inp.weight").reshape(E, -1)
        z = t @ wr.T + W.f32(p + "ffn_gate_inp.bias")
        # les 4 plus grands, ordre décroissant (égalités : indice croissant)
        top = np.argsort(-z, axis=1, kind="stable")[:, :k]
        routage[l] = top
        zv = np.take_along_axis(z, top, axis=1)
        poids = np.exp(zv - zv.max(axis=1, keepdims=True))
        poids /= poids.sum(axis=1, keepdims=True)
        moe = np.zeros_like(x)
        for ex in np.unique(top):
            lignes, rang = np.nonzero(top == ex)
            tt = t[lignes]
            gg = tt @ W.mxfp4_expert(p + "ffn_gate_exps.weight", ex).T + W.biais_expert(p + "ffn_gate_exps.bias", ex)
            uu = tt @ W.mxfp4_expert(p + "ffn_up_exps.weight", ex).T + W.biais_expert(p + "ffn_up_exps.bias", ex)
            gg = np.minimum(gg, 7.0)
            uu = np.clip(uu, -7.0, 7.0)
            act = gg / (1.0 + np.exp(-1.702 * gg)) * (uu + 1.0)
            dd = act @ W.mxfp4_expert(p + "ffn_down_exps.weight", ex).T + W.biais_expert(p + "ffn_down_exps.bias", ex)
            moe[lignes] += poids[lignes, rang][:, None] * dd
        x = x + moe
        t_couches.append(time.time() - tc)
        print(f"couche {l} : {t_couches[-1]:.1f} s, {np.unique(top).size} experts", flush=True)

    h = rmsnorm(x, W.f32("output_norm.weight"), eps)
    argmax_toutes = lp_argmax_toutes = None
    if a.argmax_toutes:
        V = g.tenseurs["output.weight"]["ne"][1]
        meilleur = np.full(P, -np.inf)
        argmax_toutes = np.zeros(P, np.int64)
        lse = np.zeros(P)
        mx = np.full(P, -np.inf)
        for r0 in range(0, V, 16384):
            n = min(16384, V - r0)
            z = h @ W.q8_0_lignes("output.weight", r0, n).T
            zm = z.max(axis=1)
            i = z.argmax(axis=1)
            mieux = zm > meilleur
            argmax_toutes[mieux] = r0 + i[mieux]
            meilleur = np.maximum(meilleur, zm)
            nm = np.maximum(mx, zm)
            lse = lse * np.exp(mx - nm) + np.exp(z - nm[:, None]).sum(axis=1)
            mx = nm
        lp_argmax_toutes = meilleur - (mx + np.log(lse))
    debut = P - a.dernieres if a.jetons else n_ctx // 2
    hs = h[debut:P]
    V = g.tenseurs["output.weight"]["ne"][1]
    logits = np.empty((hs.shape[0], V))
    pas = 16384
    for r0 in range(0, V, pas):
        n = min(pas, V - r0)
        logits[:, r0:r0 + n] = hs @ W.q8_0_lignes("output.weight", r0, n).T
    m = logits.max(axis=1, keepdims=True)
    lp = logits - m - np.log(np.exp(logits - m).sum(axis=1, keepdims=True))
    extra = {}
    if argmax_toutes is not None:
        extra = {"argmax_toutes": argmax_toutes, "lp_argmax_toutes": lp_argmax_toutes}
    np.savez(a.sortie, log_p=lp.astype(np.float32) if a.dernieres > 8 else lp, positions=np.arange(debut, P),
             jetons=ids, routage=routage, fenetre=a.fenetre, **extra)
    j = {"outil": "mesures/moteur/epreuve-J1/gptoss_numpy.py", "commande": sys.argv,
         "date": datetime.datetime.now().isoformat(timespec="seconds"), "rampe": a.rampe, "kv_f16": a.kv_f16,
         "bornes_rampe": bornes, "concentration": conc, "positions": P, "fenetre": a.fenetre,
         "notees": [debut, P], "secondes": time.time() - t_debut, "secondes_par_couche": t_couches,
         "jetons_premiers": ids[:8].tolist(), "eps": eps, "couches": L, "experts": E}
    with open(a.sortie.replace(".npz", ".json"), "w", encoding="utf-8") as f:
        json.dump(j, f, ensure_ascii=False, indent=1)
    print(json.dumps({k_: j[k_] for k_ in ("rampe", "bornes_rampe", "secondes")}))


if __name__ == "__main__":
    principal()
