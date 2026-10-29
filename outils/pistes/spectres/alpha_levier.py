"""Piste spectres : l'exposant α̂ prédit-il le levier de rang payé ? (exploratoire, NON déclaré avant)

Rang de Spearman entre α̂ (ajustements.out) et max_r N_r(16) (plafond-rang.out), sur les 48 matrices,
et le même entre α̂ et l'excès E (plafond.out). Rapporté comme exploration, sans verdict.
Utilisation : python -X utf8 alpha_levier.py > alpha-levier.out
"""
from __future__ import annotations

import commun

import csv
import os

import numpy as np
from scipy.stats import spearmanr

M = commun.MESURES


def lire(nom):
    with open(os.path.join(M, nom), encoding="utf8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    commun.priorite_basse()
    aj = {l["id"]: l for l in lire("ajustements.out")}
    n16: dict[str, float] = {}
    for l in lire("plafond-rang.out"):
        if l["genre"] == "reel":
            n16[l["id"]] = max(n16.get(l["id"], -9.0), float(l["N_r_16"]))
    g = {l["id"].split("/", 1)[1]: float(l["G_0.044"]) for l in lire("plafond.out") if l["id"].startswith(("reel/", "perm/"))
         and l["id"].startswith("reel/")}
    gp = {l["id"].split("/", 1)[1]: float(l["G_0.044"]) for l in lire("plafond.out") if l["id"].startswith("perm/")}
    ids = list(aj)
    a = np.array([float(aj[i]["alpha"]) for i in ids])
    n = np.array([n16[i] for i in ids])
    e = np.array([g[i] - gp[i] for i in ids])
    w = csv.writer(open(os.path.join(M, "fig-alpha-levier.csv"), "w", encoding="utf8", newline=""), lineterminator="\n")
    w.writerow(["id", "role", "couche", "alpha", "N16", "E"])
    for i, x, y, z in zip(ids, a, n, e):
        w.writerow([i, aj[i]["role"], aj[i]["couche"], f"{x:.4f}", f"{y:.6f}", f"{z:.6f}"])
    r1 = spearmanr(a, n)
    r2 = spearmanr(a, e)
    print(f"Spearman(α̂, max_r N_r(16)) = {r1.statistic:+.3f} (p = {r1.pvalue:.2g}, n = {len(ids)})")
    print(f"Spearman(α̂, E) = {r2.statistic:+.3f} (p = {r2.pvalue:.2g})")
    for seuil in (2.0, 2.5, 3.0):
        bas = n[a < seuil]
        haut = n[a >= seuil]
        print(f"α̂ < {seuil} : {bas.size} matrices, N16 médian {np.median(bas):+.4f}, levier > 0,05 : "
              f"{int((bas > 0.05).sum())} ; α̂ ≥ {seuil} : {haut.size}, médian {np.median(haut):+.4f}, "
              f"levier > 0,05 : {int((haut > 0.05).sum())}")


if __name__ == "__main__":
    main()
