"""Piste spectres : L3 v3, le quantificateur scalaire à tramage soustractif (seuil.md § 7 ter).

Pourquoi : L3 v2 (quantificateur uniforme sans tramage) est faussé sur une source à valeurs
discrètes comme une matrice MXFP4 : l'entropie des indices dépend de l'alignement du pas sur la grille
des valeurs, et retirer une part de rang faible rend la source continue ; le témoin T-perm l'a montré
(L00.up.E00 : +0,148 réel, +0,154 permuté). Avec un tramage soustractif u ~ U(−½, ½) connu du
décodeur, q = round(x/Δ + u), x̂ = (q − u)Δ : l'erreur est uniforme et indépendante de x, son énergie
vaut exactement N Δ²/12, donc Δ = √(12 · total / N) sans dichotomie, et l'entropie de q ne dépend
plus de la grille (Zamir et Feder, « On universal quantization by randomized uniform/lattice
quantizers », IEEE Trans. IT 38(2), 1992, de mémoire, à vérifier).

Pour chaque matrice et son témoin T-perm, rangs 0 et {1, 2, 4, 8, 16, 32, 64} : L3d (entropie des
indices, sans information annexe) et L3dr (conditionnelle à la rangée), gain net = H(W) − H(W − L̂_r) − c(r).

Utilisation : python -X utf8 levier_l3.py [--temoin-plante] > levier-l3.csv
"""
from __future__ import annotations

import commun

import csv
import math
import sys

import numpy as np

from levier import RANGS, D_REL, cout, entropie_cond, facteurs, quantifier_mxfp4


def h_tramee(x: np.ndarray, total: float, graine: int):
    delta = math.sqrt(12.0 * total / x.size)
    u = np.random.default_rng(graine).random(x.shape) - 0.5
    q = np.round(x / delta + u).astype(np.int64)
    err = float((((q - u) * delta - x) ** 2).sum())
    q -= q.min()
    ns = int(q.max()) + 1
    cnt = np.bincount(q.ravel(), minlength=ns).astype(np.float64)
    p = cnt[cnt > 0] / cnt.sum()
    hg = float(-(p * np.log2(p)).sum())
    lignes = np.repeat(np.arange(x.shape[0]), x.shape[1]).reshape(x.shape)
    hl = entropie_cond(q, lignes, ns)
    return hg, hl, err / total


def ligne(nom, w, graine_svd, ecrivain, entete):
    m, n = w.shape
    total = D_REL * float((w ** 2).sum())
    us, v = facteurs(w, max(RANGS), graine_svd)
    g0, l0, e0 = h_tramee(w, total, 11)
    lig = {"id": nom, "L3d_0": g0, "L3dr_0": l0, "erreur_relative_0": e0}
    for r in RANGS[1:]:
        res = w - us[:, :r] @ v[:r]
        g, l, e = h_tramee(res, total, 11)
        c = cout(r, m, n)
        lig[f"L3d_{r}"] = g0 - (g + c)
        lig[f"L3dr_{r}"] = l0 - (l + c)
        lig[f"err_{r}"] = e
    if entete[0]:
        ecrivain.writerow(list(lig.keys()))
        entete[0] = False
    ecrivain.writerow([f"{x:.6f}" if isinstance(x, float) else x for x in lig.values()])
    sys.stdout.flush()
    print(f"{nom:24s} H0 {g0:.4f}  L3d max {max(lig[f'L3d_{r}'] for r in RANGS[1:]):+.4f}  "
          f"L3dr max {max(lig[f'L3dr_{r}'] for r in RANGS[1:]):+.4f}  err/cible {e0:.4f}", file=sys.stderr, flush=True)


def main() -> None:
    commun.priorite_basse()
    ecrivain = csv.writer(sys.stdout, lineterminator="\n")
    entete = [True]
    rng = np.random.default_rng(commun.GRAINE + 60)
    if "--temoin-plante" in sys.argv:
        r0 = np.random.default_rng(commun.GRAINE + 50)          # même planté que levier.py
        n = 2880
        a = r0.standard_normal((n, 8)) @ r0.standard_normal((8, n))
        bruit = r0.standard_normal((n, n))
        w0 = a / np.sqrt((a ** 2).mean()) * math.sqrt(0.3) + bruit * math.sqrt(0.7)
        codes, expo = quantifier_mxfp4(w0 * 0.02)
        w = commun.K[codes] * np.ldexp(1.0, np.repeat(expo, 32, axis=1) - 128)
        ligne("T-plante-rang8", w, 1, ecrivain, entete)
        ligne("T-plante-rang8.perm", rng.permutation(w.ravel()).reshape(w.shape), 3, ecrivain, entete)
        return
    lec = commun.lecteur()
    index = {t.nom: t for t in lec.tenseurs}
    for i, m in enumerate(commun.echantillon()):
        commun.attendre_calme()
        w = commun.matrice(lec, index, m)
        ligne(m["id"], w, 100 + i, ecrivain, entete)
        ligne(m["id"] + ".perm", rng.permutation(w.ravel()).reshape(w.shape), 300 + i, ecrivain, entete)
        del w


if __name__ == "__main__":
    main()
