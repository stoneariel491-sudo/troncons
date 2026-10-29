"""P5 : bibliotheque du recuit et de l'echange de repliques sur les symboles synonymes.

Colle Python (numpy) et noyau Rust (p5core, ctypes). Ecrit le 2026-10-27, de zero, pour la piste P5.
Le Babai de reference du depot est `synonyme.py::choisir` (la retroaction d'erreur actuelle) ; un Babai
generique (n'importe quelle grille) est ecrit ici pour les temoins et verifie contre lui (temoin W4).

Convention des symboles, celle de synonyme.py : indice de niveau m = classe + 4 * (signe negatif),
niveau = c8[m] * echelle de bloc, c8 = (c0..c3, -c0..-c3).
"""
from __future__ import annotations

import ctypes
import importlib.util
import os
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from scipy import linalg

ICI = os.path.dirname(os.path.abspath(__file__))
DLL = os.environ.get("P5_DLL", "~/dev/cibles/troncons-p5/release/p5core.dll")
SYN = os.path.join(ICI, "..", "..", "genome", "eclaireur", "synonyme.py")
D = 2880

_dp = ctypes.POINTER(ctypes.c_double)
_up = ctypes.POINTER(ctypes.c_uint8)
_ip = ctypes.POINTER(ctypes.c_int32)


def _charger_syn():
    spec = importlib.util.spec_from_file_location("synonyme_ref", SYN)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["synonyme_ref"] = mod
    spec.loader.exec_module(mod)
    return mod


syn = _charger_syn()

_lib = ctypes.CDLL(DLL)
_lib.pt_rows.argtypes = [ctypes.c_size_t, ctypes.c_size_t, _dp, _dp, _dp, _dp, _dp, ctypes.c_double, _up, _up,
                         ctypes.c_size_t, ctypes.c_size_t, _dp, ctypes.c_size_t, ctypes.c_size_t,
                         ctypes.c_size_t, ctypes.c_size_t, ctypes.c_uint64, _dp, ctypes.c_int32]
_lib.pt_rows.restype = None
_lib.energie.argtypes = [ctypes.c_size_t, ctypes.c_size_t, _dp, _dp, _dp, _dp, _dp, ctypes.c_double, _up, _dp]
_lib.energie.restype = None
_lib.enum_best.argtypes = [ctypes.c_size_t, ctypes.c_size_t, _dp, _dp, _dp, _dp, ctypes.c_int32, ctypes.c_double,
                           _ip, ctypes.POINTER(ctypes.c_uint64)]
_lib.enum_best.restype = ctypes.c_double


def _p(a, t):
    return a.ctypes.data_as(t)


def energie(H, w, s, c, ell, lamp, q):
    """(E totale, partie erreur, bits), recalcules de zero par le noyau."""
    H = np.ascontiguousarray(H, dtype=np.float64)
    w = np.ascontiguousarray(w, dtype=np.float64)
    s = np.ascontiguousarray(s, dtype=np.float64)
    c = np.ascontiguousarray(c, dtype=np.float64)
    ell = np.ascontiguousarray(ell, dtype=np.float64)
    q = np.ascontiguousarray(q, dtype=np.uint8)
    out = np.zeros(3)
    _lib.energie(len(w), len(c), _p(H, _dp), _p(w, _dp), _p(s, _dp), _p(c, _dp), _p(ell, _dp), float(lamp),
                 _p(q, _up), _p(out, _dp))
    return tuple(out)


def pt(H, W, S, c, ell, lamp, Q0, temps, nsweeps, every=1, trempe=20, seed=1, fils=2, dernier=0):
    """Echange de repliques sur chaque rangee de W (R, n), grille c * S. Rend (Q, stats (R, 8))."""
    H = np.ascontiguousarray(H, dtype=np.float64)
    W = np.ascontiguousarray(W, dtype=np.float64)
    S = np.ascontiguousarray(S, dtype=np.float64)
    c = np.ascontiguousarray(c, dtype=np.float64)
    ell = np.ascontiguousarray(ell, dtype=np.float64)
    Q0 = np.ascontiguousarray(Q0, dtype=np.uint8)
    temps = np.ascontiguousarray(temps, dtype=np.float64)
    R, n = W.shape
    Q = np.zeros_like(Q0)
    st = np.zeros((R, 8))
    bornes = np.linspace(0, R, fils + 1).astype(int)

    def tache(i):
        r0, r1 = int(bornes[i]), int(bornes[i + 1])
        if r1 > r0:
            _lib.pt_rows(n, len(c), _p(H, _dp), _p(W, _dp), _p(S, _dp), _p(c, _dp), _p(ell, _dp), float(lamp),
                         _p(Q0, _up), _p(Q, _up), r0, r1, _p(temps, _dp), len(temps), int(nsweeps), int(every),
                         int(trempe), int(seed), _p(st, _dp), int(dernier))
    if fils <= 1:
        tache(0)
    else:
        with ThreadPoolExecutor(fils) as ex:
            list(ex.map(tache, range(fils)))
    return Q, st


def enum_best(L, lev, w, cost, prune, init_best=float("inf")):
    """Force brute (prune=False) ou decodage par sphere (prune=True). L : Cholesky inferieur de H.
    lev (n, k), cost (n, k). Rend (E optimale, indices, noeuds)."""
    n, k = lev.shape
    L = np.ascontiguousarray(L, dtype=np.float64)
    lev = np.ascontiguousarray(lev, dtype=np.float64)
    w = np.ascontiguousarray(w, dtype=np.float64)
    cost = np.ascontiguousarray(cost, dtype=np.float64)
    idx = np.zeros(n, dtype=np.int32)
    nd = ctypes.c_uint64(0)
    e = _lib.enum_best(n, k, _p(L, _dp), _p(lev, _dp), _p(w, _dp), _p(cost, _dp), int(bool(prune)),
                       float(init_best), _p(idx, _ip), ctypes.byref(nd))
    return e, idx, nd.value


def babai_generique(H, w, lev, cost, lamp=0.0, U=None, signe8=False):
    """Babai (retroaction d'erreur type GPTQ) pour une grille quelconque par coordonnee.
    lev (n, k), cost (n, k). Tous les niveaux sont candidats (le signe n'est pas fixe par w).
    Rend les indices (n,). Meme recurrence que synonyme.py::choisir : U^T U = H^-1, U triangulaire sup.
    signe8 : la grille a 8 colonnes (4 positives puis 4 negatives) et seul le signe du poids courant (apres
    retroaction) est candidat, comme dans `choisir` (le Babai deploye)."""
    n = len(w)
    if U is None:
        U = syn.facteur_inverse(H)
    wc = np.array(w, dtype=np.float64)
    idx = np.zeros(n, dtype=np.int64)
    for j in range(n):
        ujj = U[j, j]
        cout = (wc[j] - lev[j]) ** 2 + lamp * ujj * ujj * cost[j]
        if signe8:
            if np.signbit(wc[j]):
                cout[:4] = np.inf
            else:
                cout[4:] = np.inf
        m = int(np.argmin(cout))
        idx[j] = m
        err = (wc[j] - lev[j, m]) / ujj
        wc[j:] -= U[j, j:] * err
    return idx


def entropie_symboles(Q, k=8):
    """H0 (bits par symbole) de l'histogramme des indices de niveau Q."""
    h = np.bincount(np.asarray(Q).ravel(), minlength=k).astype(np.float64)
    p = h[h > 0] / h.sum()
    return float(-(p * np.log2(p)).sum())


def sym_vers_niveau(sym):
    """symbole de synonyme.py (bits 0-1 classe, bit 2 signe) -> indice de niveau m = classe + 4 * signe."""
    sym = np.asarray(sym)
    return ((sym & 3) + 4 * ((sym >> 2) & 1)).astype(np.uint8)


def niveau_vers_sym(m):
    m = np.asarray(m)
    return ((m & 3) | ((m >> 2) << 2)).astype(np.uint8)


def echelles_mxfp4(W):
    """Echelle de bloc de 32 (en grandeurs doublees, comme ggml) : 2^(floor(log2 amax) - 3) ;
    amax / echelle dans [8, 16[ et les codes montent a 12 (l'ecretage de la specification MX)."""
    R, C = W.shape
    a = np.abs(W).reshape(R, C // 32, 32).max(axis=-1)
    a = np.maximum(a, 1e-300)
    return np.ldexp(1.0, np.floor(np.log2(a)).astype(np.int32) - 3)


def quantifier_mxfp4(W):
    """W (R, C) flottants -> (W sur la grille MXFP4 doublee, exposants E8M0 (R, C/32) u8, codes u8)."""
    R, C = W.shape
    s = echelles_mxfp4(W)
    ss = np.repeat(s, 32, axis=-1)
    v = np.abs(W) / ss
    mag = syn.MAG
    code = np.abs(v[..., None] - mag).argmin(axis=-1).astype(np.uint8)
    codes = code | (np.signbit(W).astype(np.uint8) << 3)
    ex = (np.round(np.log2(s)).astype(np.int32) + 128).astype(np.uint8)
    return syn.dequant(ex, codes), ex, codes
