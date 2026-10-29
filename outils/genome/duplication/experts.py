"""Accès aux experts MXFP4 de gpt-oss pour l'étude de la duplication (génome des poids).

Rôle : rendre, pour une couche et un rôle (gate, up, down), les codes E2M1 (4 bits), les
échelles E8M0 et les poids déquantifiés d'un expert, sans jamais charger plus d'un tenseur.

Format (ggml, type 39 MXFP4 ; structure au bit près : fondations/03-entropie-derivations.md § 1.2) :
  bloc de 17 octets = e (E8M0, 1 octet) puis 16 octets ; le demi-octet bas de l'octet j est le
  poids j, le haut le poids j + 16 ; poids = kvalues[q] · 2^(e − 128), avec
  kvalues = (0, 1, 2, 3, 4, 6, 8, 12, 0, −1, −2, −3, −4, −6, −8, −12) (magnitudes E2M1 doublées).
Disposition d'un tenseur d'experts : dims GGUF (ne0, ne1, ne2) = (entrée, sortie, expert) ; les
blocs courent le long de l'entrée ; l'expert e occupe les rangées [e·ne1, (e+1)·ne1).
  gate, up : entrée = d_modele, sortie = d_ff ; down : entrée = d_ff, sortie = d_modele.
La permutation des neurones cachés (d_ff) permute donc les RANGÉES de gate et up (les blocs
restent entiers) et les COLONNES de down (elle traverse les blocs).

Le lecteur GGUF est celui de l'étude 03 (outils/03-entropie/gguf_lecture.py), écrit de zéro.
"""
from __future__ import annotations

import importlib.util
import os
import sys

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
LECTEUR = os.path.normpath(os.path.join(ICI, "..", "..", "03-entropie", "gguf_lecture.py"))
FICHIER_20B = "~/dev/modeles/gguf/gpt-oss-20b-MXFP4.gguf"
FICHIER_120B = "~/dev/modeles/gguf/gpt-oss-120b-MXFP4.gguf"
ROLES = ("gate", "up", "down")

KVALUES = np.array([0, 1, 2, 3, 4, 6, 8, 12, 0, -1, -2, -3, -4, -6, -8, -12], dtype=np.float32)


def _charger_lecteur():
    if "gguf_lecture" in sys.modules:
        return sys.modules["gguf_lecture"]
    spec = importlib.util.spec_from_file_location("gguf_lecture", LECTEUR)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gguf_lecture"] = mod
    spec.loader.exec_module(mod)
    return mod


class Experts:
    """Les tenseurs d'experts d'un GGUF gpt-oss, lus à la demande (memmap, aucune copie)."""

    def __init__(self, chemin: str = FICHIER_20B):
        g = _charger_lecteur()
        self.lecteur = g.LecteurGGUF(chemin)
        self.par_nom = {t.nom: t for t in self.lecteur.tenseurs}
        self.couches = int(self.lecteur.meta.get("gpt-oss.block_count"))
        self.nb_experts = int(self.lecteur.meta.get("gpt-oss.expert_count"))
        t = self.tenseur(0, "gate")
        self.d_entree_gate, self.d_ff = t.dims[0], t.dims[1]

    def tenseur(self, couche: int, role: str):
        return self.par_nom[f"blk.{couche}.ffn_{role}_exps.weight"]

    def blocs(self, couche: int, role: str, expert: int) -> np.ndarray:
        """Les blocs bruts (rangées, blocs par rangée, 17) d'un expert, en vue memmap."""
        t = self.tenseur(couche, role)
        assert t.type_ggml == 39, "MXFP4 attendu"
        n_in, n_out = t.dims[0], t.dims[1]
        par_expert = n_out * (n_in // 32) * 17
        brut = self.lecteur.octets(t)
        return brut[expert * par_expert:(expert + 1) * par_expert].reshape(n_out, n_in // 32, 17)

    def codes_echelles(self, couche: int, role: str, expert: int):
        """(codes uint8 (sortie, entrée), échelles uint8 (sortie, entrée/32))."""
        b = np.asarray(self.blocs(couche, role, expert))
        e = b[:, :, 0].copy()
        qs = b[:, :, 1:]
        codes = np.concatenate([qs & 15, qs >> 4], axis=2)  # (sortie, nb, 32)
        return codes.reshape(b.shape[0], -1), e

    def poids(self, couche: int, role: str, expert: int) -> np.ndarray:
        """Poids déquantifiés exacts en float32 (sortie, entrée). Exacts : kvalues · 2^k tient en f32
        tant que e ∈ [1, 254] (2^(e−128) normal) ; e = 0 ou 255 se signale."""
        codes, e = self.codes_echelles(couche, role, expert)
        if (e == 255).any():
            raise ValueError("échelle E8M0 = 255 (NaN) rencontrée")
        ech = np.ldexp(np.float32(1.0), e.astype(np.int32) - 128).astype(np.float32)
        w = KVALUES[codes].reshape(e.shape[0], e.shape[1], 32) * ech[:, :, None]
        return w.reshape(codes.shape)

    def biais(self, couche: int, role: str) -> np.ndarray:
        """Les biais des experts (E, sortie) en float32."""
        t = self.par_nom[f"blk.{couche}.ffn_{role}_exps.bias"]
        assert t.type_ggml == 0
        return np.frombuffer(self.lecteur.octets(t).tobytes(), dtype=np.float32).reshape(t.dims[1], t.dims[0])


def neurones(ex: Experts, couche: int, expert: int) -> np.ndarray:
    """Le vecteur de chaque neurone caché : [rangée de gate | rangée de up | colonne de down],
    (d_ff, 3·d_modele), en float32. Une permutation des neurones permute les rangées de ce tableau,
    et la fonction de l'expert est inchangée si elle s'applique aussi aux biais de gate et up."""
    g = ex.poids(couche, "gate", expert)
    u = ex.poids(couche, "up", expert)
    d = ex.poids(couche, "down", expert)
    return np.concatenate([g, u, d.T], axis=1)
