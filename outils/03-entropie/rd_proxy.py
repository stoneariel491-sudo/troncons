"""Au-delà du sans-perte : à erreur égale, combien de bits gagne une quantification
taillée pour un codeur entropique (ECSQ), face à une quantification à débit fixe ?

Source : des tenseurs déquantifiés d'un GGUF, pris comme substituts des poids
d'origine (Q6_K : 6,56 bits/poids ; Q8_0 : 8,5 bits/poids). Leur propre erreur est
environ 16 fois (Q6_K) et 256 fois (Q8_0) plus petite que celle d'une quantification
4 bits : le substitut garde la forme de la distribution, mais il est posé sur une
grille, ce qui peut abaisser un peu l'entropie mesurée (biais écrit dans le livrable).

Quantificateurs comparés, sur des blocs de 256 poids contigus d'une ligne :
  KQ4  : à la manière de Q4_K (8 sous-blocs de 32, échelle et minimum par sous-bloc
         cherchés pour l'erreur quadratique minimale, puis ramenés sur 6 bits sous un
         couple fp16 par bloc) : 4,5 bits/poids exactement. Réécrit de zéro ; il n'a ni
         la pondération imatrix ni la recherche exacte de llama.cpp.
  MM4  : min-max asymétrique sans recherche, groupes de 32 et de 64, échelle et
         minimum fp16 : 5,0 et 4,5 bits/poids.
  ECSQ : pas uniforme Δ = c·σ_bloc (σ_bloc en fp16 : 0,0625 bit/poids), arrondi au plus
         proche, codes entiers non bornés, codés par un code entropique à table par
         tenseur. Débit = H(codes) + 0,0625. c est cherché par dichotomie pour égaler
         l'erreur quadratique de KQ4 (et, à part, pour égaler son débit de 4,5 bits).
Référence : R_G(D) = moyenne sur les blocs de max(0, ½ log2(σ_b² / D_b)), borne de
Shannon d'une source gaussienne de mêmes variances par bloc (aucune source de même
variance ne demande plus ; une source réelle peut demander moins).

Usage : python rd_proxy.py <fichier.gguf> <sortie.json> <tenseur> [<tenseur> ...]
"""
import json
import sys

import numpy as np
from gguf import GGMLQuantizationType, quants

from gguf_lecture import LecteurGGUF

BLOC = 256
SOUS = 32


def entropie_codes(q: np.ndarray) -> float:
    v, c = np.unique(q, return_counts=True)
    p = c / c.sum()
    return float(-(p * np.log2(p)).sum())


def fp16(x):
    return np.asarray(x, np.float32).astype(np.float16).astype(np.float32)


def kq4(w: np.ndarray):
    """w : (n, 256). Rend (reconstruction, codes)."""
    n = w.shape[0]
    x = w.reshape(n, 8, SOUS)
    lo0 = x.min(axis=2, keepdims=True)
    hi0 = x.max(axis=2, keepdims=True)
    etendue = hi0 - lo0
    meilleur = np.full((n, 8, 1), np.inf, np.float32)
    lo_b = lo0.copy()
    hi_b = hi0.copy()
    grille = np.linspace(0.0, 0.3, 13)
    for a in grille:
        for b in grille:
            lo = np.minimum(lo0 + a * etendue, 0.0)    # le minimum reste <= 0 (forme ggml)
            hi = hi0 - b * etendue
            s = np.maximum(hi - lo, 1e-12) / 15.0
            q = np.clip(np.rint((x - lo) / s), 0, 15)
            e = ((q * s + lo - x) ** 2).sum(axis=2, keepdims=True)
            mieux = e < meilleur
            meilleur = np.where(mieux, e, meilleur)
            lo_b = np.where(mieux, lo, lo_b)
            hi_b = np.where(mieux, hi, hi_b)
    s = (np.maximum(hi_b - lo_b, 1e-12) / 15.0)[..., 0]     # (n, 8)
    m = (-lo_b)[..., 0]                                     # >= 0
    d = fp16(s.max(axis=1) / 63.0)
    dm = fp16(np.maximum(m.max(axis=1), 1e-12) / 63.0)
    sc = np.clip(np.rint(s / np.maximum(d[:, None], 1e-12)), 1, 63)
    mc = np.clip(np.rint(m / np.maximum(dm[:, None], 1e-12)), 0, 63)
    S = (d[:, None] * sc)[..., None]
    Mn = (dm[:, None] * mc)[..., None]
    q = np.clip(np.rint((x + Mn) / S), 0, 15)
    r = q * S - Mn
    return r.reshape(n, BLOC), q.astype(np.int64).reshape(n, BLOC)


def minmax(w: np.ndarray, g: int):
    n = w.shape[0]
    x = w.reshape(n, BLOC // g, g)
    lo = fp16(x.min(axis=2, keepdims=True))
    s = fp16(np.maximum(x.max(axis=2, keepdims=True) - lo, 1e-12) / 15.0)
    q = np.clip(np.rint((x - lo) / s), 0, 15)
    return (q * s + lo).reshape(n, BLOC), q.astype(np.int64).reshape(n, BLOC)


def ecsq(w: np.ndarray, sigma: np.ndarray, c: float):
    delta = (c * sigma)[:, None]
    q = np.rint(w / delta)
    return q * delta, q.astype(np.int64)


def chercher_c(w, sigma, cible, quantite):
    """Dichotomie sur log(c) pour que quantite(c) == cible (quantité croissante en c)."""
    a, b = np.log(1e-3), np.log(10.0)
    for _ in range(40):
        m = 0.5 * (a + b)
        if quantite(np.exp(m)) < cible:
            a = m
        else:
            b = m
    return float(np.exp(0.5 * (a + b)))


def main():
    chemin, sortie = sys.argv[1], sys.argv[2]
    noms = sys.argv[3:]
    L = LecteurGGUF(chemin)
    par_nom = {t.nom: t for t in L.tenseurs}
    resultats = []
    for nom in noms:
        t = par_nom[nom]
        brut = np.asarray(L.octets(t))
        w = quants.dequantize(brut, GGMLQuantizationType[t.nom_type]).astype(np.float32).reshape(-1)
        # au plus 8 Mi poids, pris en lignes entières régulièrement espacées
        ne0 = t.dims[0]
        lignes = w.size // ne0
        pas = max(1, (w.size // (8 << 20)))
        w = w.reshape(lignes, ne0)[::pas].reshape(-1, BLOC)
        var = (w.astype(np.float64) ** 2).mean()
        sigma = fp16(np.sqrt((w.astype(np.float64) ** 2).mean(axis=1)) + 1e-12)
        r_k, q_k = kq4(w)
        mse_k = float(((r_k - w) ** 2).mean())
        h_k = entropie_codes(q_k)
        mm = {}
        for g in (32, 64):
            r_m, q_m = minmax(w, g)
            mm[g] = {"bits_par_poids": 4 + 32 / g, "mse_rel": float(((r_m - w) ** 2).mean() / var),
                     "H_codes": entropie_codes(q_m)}

        def mse_de(c):
            r, _ = ecsq(w, sigma, c)
            return float(((r - w) ** 2).mean())

        def debit_de(c):
            _, q = ecsq(w, sigma, c)
            return -(entropie_codes(q) + 16 / BLOC)   # décroissant en c : on prend l'opposé

        c_mse = chercher_c(w, sigma, mse_k, mse_de)
        _, q_e = ecsq(w, sigma, c_mse)
        h_e = entropie_codes(q_e)
        c_deb = chercher_c(w, sigma, -4.5, debit_de)
        mse_e_deb = mse_de(c_deb)
        # borne gaussienne par bloc à la distorsion de KQ4 (eau inversée par bloc)
        var_b = (w.astype(np.float64) ** 2).mean(axis=1)
        lo_t, hi_t = 0.0, float(var_b.max())
        for _ in range(60):
            th = 0.5 * (lo_t + hi_t)
            if np.minimum(var_b, th).mean() < mse_k:
                lo_t = th
            else:
                hi_t = th
        r_g = float(np.maximum(0.0, 0.5 * np.log2(var_b / np.maximum(th, 1e-30))).mean())
        res = {
            "tenseur": nom, "type_source": t.nom_type, "poids_mesures": int(w.size),
            "kurtosis": float(((w.astype(np.float64) ** 4).mean()) / var ** 2),
            "KQ4": {"bits_par_poids": 4.5, "mse_rel": mse_k / var, "H_codes": h_k},
            "MM4_g32": mm[32], "MM4_g64": mm[64],
            "ECSQ_meme_erreur": {"c": c_mse, "H_codes": h_e, "bits_par_poids": h_e + 16 / BLOC,
                                 "gain_bits_par_poids": 4.5 - (h_e + 16 / BLOC),
                                 "alphabet": int(q_e.max() - q_e.min() + 1)},
            "ECSQ_meme_debit": {"c": c_deb, "mse_rel": mse_e_deb / var,
                                "gain_dB": float(10 * np.log10(mse_k / mse_e_deb))},
            "borne_gauss_par_bloc_bits": r_g,
        }
        resultats.append(res)
        print(f"{nom} ({t.nom_type}, kurtosis {res['kurtosis']:.2f}) : KQ4 4,5 b/p, MSE rel {mse_k/var:.5f}, H codes {h_k:.3f} | "
              f"MM4 g32 MSE rel {mm[32]['mse_rel']:.5f} H {mm[32]['H_codes']:.3f} ; g64 MSE {mm[64]['mse_rel']:.5f} H {mm[64]['H_codes']:.3f} | "
              f"ECSQ même erreur : {h_e + 16/BLOC:.3f} b/p (gain {4.5 - h_e - 16/BLOC:.3f}, alphabet {res['ECSQ_meme_erreur']['alphabet']}) ; "
              f"même débit : {res['ECSQ_meme_debit']['gain_dB']:.2f} dB | borne gauss {r_g:.3f} b/p", flush=True)
    json.dump(resultats, open(sortie, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
