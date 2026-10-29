"""Lecture des experts MXFP4 de gpt-oss, matrice par matrice, pour l'étude predictif-elagage.

Disposition (03-entropie-derivations § 1.2, vérifiée par le témoin `temoin-champs-mxfp4.log`) :
un tenseur d'experts `blk.L.ffn_{gate,up,down}_exps.weight` a pour dimensions ggml
(ne0 = colonnes d'entrée, ne1 = lignes de sortie, ne2 = experts). Chaque ligne est une suite de
blocs de 17 octets : l'échelle E8M0 `e`, puis 16 octets de demi-octets ; l'octet j porte
l'élément j (demi-octet faible) et l'élément j + 16 (demi-octet fort).

Valeur réelle d'un code c (4 bits : signe c >> 3, magnitude m = c & 7) :
    w = K[c] · 2^(e − 128),  K = ±{0, 1, 2, 3, 4, 6, 8, 12}
(les grandeurs E2M1 doublées, d'où 2^(e − 128) au lieu de 2^(e − 127) ; trc-reference
`echelle_e8m0_demi`).

La médiane de ligne est celle du codeur de 03 (`taux_mxfp4.rs`) : l'élément de rang 45 des 90
échelles triées (médiane haute).
"""
from __future__ import annotations

import importlib.util
import os
import sys

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
LECTEUR = os.path.join(ICI, "..", "..", "03-entropie", "gguf_lecture.py")
FICHIER_20B = "~/dev/modeles/gguf/gpt-oss-20b-MXFP4.gguf"
FICHIER_120B = "~/dev/modeles/gguf/gpt-oss-120b-MXFP4.gguf"
COUCHES = (0, 8, 16, 23)
ROLES = ("ffn_gate_exps", "ffn_up_exps", "ffn_down_exps")

# Magnitudes E2M1 doublées par indice m = c & 7, et valeur signée par code c.
MAG = np.array([0, 1, 2, 3, 4, 6, 8, 12], dtype=np.float64)
VAL = np.concatenate([MAG, -MAG])


def lecteur(chemin: str = FICHIER_20B):
    spec = importlib.util.spec_from_file_location("gguf_lecture", LECTEUR)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gguf_lecture"] = mod
    spec.loader.exec_module(mod)
    return mod.LecteurGGUF(chemin)


def tenseurs_etude(lec, couches=COUCHES, roles=ROLES):
    """Les tenseurs d'experts de l'étude, dans l'ordre (couche, rôle)."""
    par_nom = {t.nom: t for t in lec.tenseurs}
    sortie = []
    for c in couches:
        for r in roles:
            t = par_nom[f"blk.{c}.{r}.weight"]
            if t.nom_type != "MXFP4":
                raise SystemExit(f"{t.nom} n'est pas en MXFP4 ({t.nom_type})")
            sortie.append(t)
    return sortie


def forme(t):
    """(experts, lignes, colonnes)."""
    colonnes, lignes, experts = t.dims
    return experts, lignes, colonnes


def expert(lec, t, e: int):
    """Codes (lignes, colonnes) en uint8 0..15 et échelles (lignes, blocs) en uint8, pour l'expert e."""
    E, R, C = forme(t)
    nb = C // 32
    taille = R * nb * 17
    brut = np.asarray(lec.octets(t)[e * taille:(e + 1) * taille]).reshape(R, nb, 17)
    ech = brut[:, :, 0].copy()
    qs = brut[:, :, 1:]
    codes = np.concatenate([qs & 15, qs >> 4], axis=2).reshape(R, C)
    return codes, ech


def mediane_ligne(ech: np.ndarray) -> np.ndarray:
    """Médiane haute (rang n // 2 du tri) de chaque ligne d'échelles, comme taux_mxfp4.rs."""
    return np.sort(ech, axis=1)[:, ech.shape[1] // 2]


def kappa(ech: np.ndarray, med: np.ndarray) -> np.ndarray:
    """Classe d'échelle de chaque bloc : 0 sous la médiane, 1 égale, 2 au-dessus (03 § 1.6)."""
    d = ech.astype(np.int16) - med[:, None].astype(np.int16)
    return (np.sign(d) + 1).astype(np.uint8)


def valeurs(codes: np.ndarray, ech: np.ndarray) -> np.ndarray:
    """Poids réels en f64 (exacts : au plus 4 bits significatifs et un exposant normal)."""
    R, C = codes.shape
    e = np.repeat(ech.astype(np.float64) - 128.0, 32, axis=1)
    return VAL[codes] * np.exp2(e)


def entropie(comptes: np.ndarray) -> float:
    p = comptes[comptes > 0].astype(np.float64)
    p /= p.sum()
    return float(-(p * np.log2(p)).sum())


def entropie_conditionnelle(comptes_ctx_sym: np.ndarray) -> tuple[float, float]:
    """(bits totaux, nombre de symboles) pour un tableau (contextes, symboles) de comptes."""
    tot = 0.0
    n = 0.0
    for ligne in comptes_ctx_sym:
        s = ligne.sum()
        if s > 0:
            tot += s * entropie(ligne)
            n += s
    return tot, n
