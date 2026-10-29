"""Lectures communes du lot « espaces latents » du Tome III (figures III-9.1 (c) et III-9.7).

Écrit pour troncons le 2026-10-27. Rien n'y calcule un résultat : on y lit les octets du GGUF (par le
lecteur de 03, en memmap), les fichiers .sym du lot B et les captures de l'éclaireur (en memmap), avec
les conventions écrites dans outils/genome/synonyme/verifier_sym.py et outils/genome/eclaireur/synonyme.py.

  MXFP4 : un bloc de 32 poids = 1 octet d'exposant E8M0 e, puis 16 octets ; le poids t du bloc est le
          demi-octet faible de l'octet t, le poids 16 + t le fort. Code de 4 bits : bit 3 le signe,
          bits 0-2 la grandeur E2M1, rangée « doublée » comme dans ggml : MAG = 0, 1, 2, 3, 4, 6, 8, 12 ;
          valeur = ± MAG · 2^(e − 128) = ± (MAG / 2) · 2^(e − 127).
  .sym  : « SYM1 », 4 centres f64 (mêmes grandeurs doublées), puis gate, up, down : 2 880 × 2 880
          symboles de 4 bits, deux par octet (l'indice pair au demi-octet faible) ; bits 0-1 la classe,
          bit 2 le signe négatif ; valeur = ± centre[classe] · 2^(e − 128).
"""
from __future__ import annotations

import importlib.util
import os
import sys

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", "..", ".."))
GGUF = "~/dev/modeles/gguf/gpt-oss-20b-MXFP4.gguf"
CAPT = "~/dev/essais/troncons/genome/eclaireur"
SYM = "~/dev/essais/troncons/genome/synonyme/sym"
N = 2880
NB = N // 32
ROLES = ("gate", "up", "down")
MAG2 = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0])


def lecteur():
    spec = importlib.util.spec_from_file_location("gguf_lecture", os.path.join(RACINE, "outils/03-entropie/gguf_lecture.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gguf_lecture"] = mod
    spec.loader.exec_module(mod)
    lec = mod.LecteurGGUF(GGUF)
    return lec, {t.nom: t for t in lec.tenseurs}


def blocs_expert(lec, tens, couche, role, e):
    """(exposants (R, NB) int32, codes (R, C) uint8 dans l'ordre des colonnes) de l'expert e."""
    t = tens[f"blk.{couche}.ffn_{role}_exps.weight"]
    assert t.nom_type == "MXFP4", t.nom_type
    o = np.asarray(lec.octets(t)).reshape(t.dims[2], N, NB, 17)[e]
    ex = o[..., 0].astype(np.int32)
    qs = o[..., 1:]
    codes = np.concatenate([qs & 15, qs >> 4], axis=-1).reshape(N, N)
    return ex, codes


def matrice_exacte(ex, codes):
    v = MAG2[codes & 7] * np.repeat(np.ldexp(1.0, ex - 128), 32, axis=1)
    return np.where((codes & 8) != 0, -v, v)


def lire_sym(variante, couche, e):
    chemin = os.path.join(SYM, variante, f"L{couche:02d}-E{e:02d}.sym")
    o = np.fromfile(chemin, dtype=np.uint8)
    if bytes(o[:4]) != b"SYM1":
        raise ValueError(f"{chemin} : magie")
    centres = o[4:36].view("<f8").copy()
    corps = o[36:]
    if corps.size != 3 * N * N // 2:
        raise ValueError(f"{chemin} : taille {corps.size}")
    mats = []
    for j in range(3):
        b = corps[j * N * N // 2:(j + 1) * N * N // 2]
        s = np.empty(N * N, dtype=np.uint8)
        s[0::2] = b & 15
        s[1::2] = b >> 4
        mats.append(s.reshape(N, N))
    return centres, mats, chemin


def matrice_base(ex, sym, centres):
    v = centres[sym & 3] * np.repeat(np.ldexp(1.0, ex - 128), 32, axis=1)
    return np.where((sym & 4) != 0, -v, v)


def entrees(quoi, couche, e):
    """Entrées réelles de l'expert e à la couche (f64) et leurs poids de routeur g."""
    h = np.memmap(os.path.join(CAPT, quoi, f"h-L{couche:02d}.f32"), dtype="<f4", mode="r").reshape(-1, N)
    r = np.fromfile(os.path.join(CAPT, quoi, f"routage-L{couche:02d}.bin"), dtype=np.uint8).reshape(-1, 20)
    choix, g = r[:, :4], r[:, 4:].copy().view("<f4").reshape(-1, 4)
    p, j = np.nonzero(choix == e)
    return np.asarray(h[p], dtype=np.float64), g[p, j].astype(np.float64), p


def lire_spectre(couche, e, role):
    """Le CSV du lot B (mesures/genome/construction/synonyme/figures/spectre-L..-E..-role.csv)."""
    import csv
    chemin = os.path.join(RACINE, f"mesures/genome/construction/synonyme/figures/spectre-L{couche:02d}-E{e:02d}-{role}.csv")
    with open(chemin, encoding="utf-8") as f:
        lignes = list(csv.DictReader(f))
    return {k: np.array([float(r[k]) for r in lignes]) for k in lignes[0]}, chemin
