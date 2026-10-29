"""Découpe des blocs quantifiés ggml en leurs champs, écrite de zéro.

Pour chaque type, on rend les codes entiers dans l'ordre logique des poids
(l'ordre de la déquantification), et les champs de métadonnées tels quels :
échelles fp16 (en entiers u16, pour mesurer leur entropie bit à bit), échelles
et minimums 6 bits, échelles int8.

La disposition des blocs suit ggml-common.h (dépôt ggml-org/llama.cpp, licence
MIT) ; elle est redérivée ici et vérifiée par deconstruire() == gguf.dequantize
dans temoin_champs.py, par un second chemin indépendant.
"""
from __future__ import annotations

import numpy as np


def _echelles_k4(sc: np.ndarray):
    """sc : (n, 12) u8. Rend (echelles, minimums) : (n, 8) u8 sur 6 bits."""
    s = np.empty((sc.shape[0], 8), np.uint8)
    m = np.empty((sc.shape[0], 8), np.uint8)
    s[:, :4] = sc[:, 0:4] & 63
    m[:, :4] = sc[:, 4:8] & 63
    s[:, 4:] = (sc[:, 8:12] & 0x0F) | ((sc[:, 0:4] >> 6) << 4)
    m[:, 4:] = (sc[:, 8:12] >> 4) | ((sc[:, 4:8] >> 6) << 4)
    return s, m


def q4_k(blocs: np.ndarray) -> dict:
    """blocs : (n, 144) u8."""
    d = blocs[:, 0:2].copy().view(np.uint16)[:, 0]
    dmin = blocs[:, 2:4].copy().view(np.uint16)[:, 0]
    s, m = _echelles_k4(blocs[:, 4:16])
    qs = blocs[:, 16:144].reshape(-1, 4, 32)
    q = np.empty((blocs.shape[0], 4, 64), np.uint8)
    q[:, :, :32] = qs & 0x0F
    q[:, :, 32:] = qs >> 4
    return {"codes": q.reshape(-1, 256), "d": d, "dmin": dmin,
            "echelles": s, "minimums": m, "bits_code": 4}


def q5_k(blocs: np.ndarray) -> dict:
    """blocs : (n, 176) u8 : d, dmin, scales[12], qh[32], qs[128]."""
    d = blocs[:, 0:2].copy().view(np.uint16)[:, 0]
    dmin = blocs[:, 2:4].copy().view(np.uint16)[:, 0]
    s, m = _echelles_k4(blocs[:, 4:16])
    qh = blocs[:, 16:48]
    qs = blocs[:, 48:176].reshape(-1, 4, 32)
    q = np.empty((blocs.shape[0], 4, 64), np.uint8)
    for j in range(4):
        b1 = (qh >> (2 * j)) & 1
        b2 = (qh >> (2 * j + 1)) & 1
        q[:, j, :32] = (qs[:, j] & 0x0F) | (b1 << 4)
        q[:, j, 32:] = (qs[:, j] >> 4) | (b2 << 4)
    return {"codes": q.reshape(-1, 256), "d": d, "dmin": dmin,
            "echelles": s, "minimums": m, "bits_code": 5}


def q6_k(blocs: np.ndarray) -> dict:
    """blocs : (n, 210) u8 : ql[128], qh[64], scales[16] i8, d."""
    ql = blocs[:, 0:128]
    qh = blocs[:, 128:192]
    sc = blocs[:, 192:208]
    d = blocs[:, 208:210].copy().view(np.uint16)[:, 0]
    q = np.empty((blocs.shape[0], 2, 4, 32), np.uint8)
    for moitie in range(2):
        l = ql[:, 64 * moitie: 64 * moitie + 64]
        h = qh[:, 32 * moitie: 32 * moitie + 32]
        q[:, moitie, 0] = (l[:, 0:32] & 0x0F) | (((h >> 0) & 3) << 4)
        q[:, moitie, 1] = (l[:, 32:64] & 0x0F) | (((h >> 2) & 3) << 4)
        q[:, moitie, 2] = (l[:, 0:32] >> 4) | (((h >> 4) & 3) << 4)
        q[:, moitie, 3] = (l[:, 32:64] >> 4) | (((h >> 6) & 3) << 4)
    return {"codes": q.reshape(-1, 256), "d": d, "echelles": sc.copy(),
            "bits_code": 6}


def q8_0(blocs: np.ndarray) -> dict:
    """blocs : (n, 34) u8 : d, qs[32] i8."""
    d = blocs[:, 0:2].copy().view(np.uint16)[:, 0]
    return {"codes": blocs[:, 2:34].copy(), "d": d, "bits_code": 8}


def mxfp4(blocs: np.ndarray) -> dict:
    """blocs : (n, 17) u8 : e (échelle E8M0), qs[16] ; code j en demi-octet bas de
    qs[j], code j+16 en demi-octet haut (ggml-common.h, block_mxfp4)."""
    e = blocs[:, 0].astype(np.uint16)
    qs = blocs[:, 1:17]
    q = np.empty((blocs.shape[0], 32), np.uint8)
    q[:, :16] = qs & 0x0F
    q[:, 16:] = qs >> 4
    return {"codes": q, "d": e, "bits_code": 4}


DECOUPEURS = {"Q4_K": (q4_k, 144), "Q5_K": (q5_k, 176),
              "Q6_K": (q6_k, 210), "Q8_0": (q8_0, 34),
              "MXFP4": (mxfp4, 17)}


def deconstruire(type_nom: str, blocs: np.ndarray) -> np.ndarray:
    """Déquantifie à partir des champs (sert de témoin contre gguf)."""
    f = DECOUPEURS[type_nom][0](blocs)
    d = f["d"].view(np.float16).astype(np.float32)
    if type_nom in ("Q4_K", "Q5_K"):
        dm = f["dmin"].view(np.float16).astype(np.float32)
        sc = np.repeat(f["echelles"].astype(np.float32), 32, axis=1)
        mn = np.repeat(f["minimums"].astype(np.float32), 32, axis=1)
        return d[:, None] * sc * f["codes"] - dm[:, None] * mn
    if type_nom == "Q6_K":
        sc = f["echelles"].view(np.int8).astype(np.float32)   # (n,16)
        # ordre logique : moitié, quart j (0..3), l (0..31), échelle is=l//16
        idx = np.array([8 * mo + 2 * j + l // 16
                        for mo in range(2) for j in range(4) for l in range(32)])
        return d[:, None] * sc[:, idx] * (f["codes"].astype(np.float32) - 32)
    if type_nom == "Q8_0":
        return d[:, None] * f["codes"].view(np.int8).astype(np.float32)
    if type_nom == "MXFP4":
        # E2M1 doublé (valeurs 0..12) et échelle 2^(e-127) divisée par 2
        kv = np.array([0, 1, 2, 3, 4, 6, 8, 12, 0, -1, -2, -3, -4, -6, -8, -12], np.float32)
        ech = np.ldexp(np.float32(1.0), f["d"].astype(np.int32) - 128).astype(np.float32)
        return ech[:, None] * kv[f["codes"]]
    raise ValueError(type_nom)
