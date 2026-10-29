"""Piste spectres : CSV de la figure P3 (d'où vient le plafond : échelles de rangée, artefact MP, structure).

Lit `plafond-rangee.out` (commité). Pour chaque matrice couverte (45, sans attn_q) :
    G_blanc = (R_blanc − L2_0)  [gain des échelles de rangée]
            + G_rang_ref        [ce que gagne une base offerte sur la même matrice sans structure entre rangées]
            + E_rang            [la structure entre rangées, au-delà du nul]
(identité : G_rang = L2_0 − R_KLT, donc G_blanc − (R_blanc − L2_0) = G_rang = G_rang_ref + E_rang).
Écrit `fig-rangee.csv` (une ligne par matrice, ordre du tirage) et `fig-rangee-famille.csv` (moyennes).
Aucun calcul de mesure. Utilisation : python -X utf8 fig_rangee.py
"""
from __future__ import annotations

import commun

import csv
import math
import os

import numpy as np

import plafond

M = commun.MESURES
BLANC = 0.5 * math.log2(1.0 / plafond.D_PRINCIPAL)


def famille(role: str) -> str:
    return "attention" if role.startswith("attn") else role


def main() -> None:
    with open(os.path.join(M, "plafond-rangee.out"), encoding="utf8") as f:
        lignes = [l for l in csv.DictReader(f) if l["couvert"] == "1"]
    sortie, par = [], {}
    for k, l in enumerate(lignes):
        echelles = BLANC - float(l["L2_0"])
        ref, exc = float(l["G_rang_ref"]), float(l["E_rang"])
        gb = float(l["G_blanc"])
        assert abs(echelles + ref + exc - gb) < 1e-5, l["id"]      # l'identité du plafond
        sortie.append((k, l["id"], famille(l["role"]), echelles, ref, exc, gb))
        par.setdefault(famille(l["role"]), []).append((echelles, ref, exc, gb))
    with open(os.path.join(M, "fig-rangee.csv"), "w", encoding="utf8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["x", "id", "famille", "echelles", "reference", "exces", "G_blanc"])
        for k, i, fam, a, b, c, gb in sortie:
            w.writerow([k, i, fam, f"{a:.6f}", f"{b:.6f}", f"{c:.6f}", f"{gb:.6f}"])
    with open(os.path.join(M, "fig-rangee-famille.csv"), "w", encoding="utf8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["x", "famille", "n", "echelles", "reference", "exces", "G_blanc"])
        for x, fam in enumerate(("gate", "up", "down", "attention")):
            v = np.array(par[fam])
            w.writerow([x, fam, len(v)] + [f"{np.mean(v[:, j]):.6f}" for j in range(4)])


if __name__ == "__main__":
    main()
