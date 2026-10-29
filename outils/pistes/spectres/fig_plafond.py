"""Piste spectres : CSV des figures du plafond (P1 : plafond par rang ; P2 : α̂ contre levier payé).

Lit `plafond-rang.out` et `fig-alpha-levier.csv` (commités) ; écrit `fig-plafond-rang-<famille>.csv`
(médianes par rang de G_r réel, G_r permuté, N_r(16)), `fig-plafond-rang-plante.csv` et
`fig-alpha-levier-<famille>.csv`. Aucun calcul de mesure : des médianes et des filtres.
Utilisation : python -X utf8 fig_plafond.py
"""
from __future__ import annotations

import commun

import csv
import os
from collections import defaultdict

import numpy as np

M = commun.MESURES


def famille(i: str) -> str:
    return "attention" if ".attn_" in i else i.split(".")[1]


def main() -> None:
    with open(os.path.join(M, "plafond-rang.out"), encoding="utf8") as f:
        lignes = list(csv.DictReader(f))
    par = defaultdict(lambda: defaultdict(list))        # (fam, genre) -> r -> [(G, N16)]
    for l in lignes:
        if l["genre"] == "temoin":
            continue
        base = l["id"].removesuffix(".perm")
        if ".attn_k" in base or ".attn_v" in base:       # p = 512 : rangs différents, hors des médianes
            continue
        par[(famille(base), l["genre"])][int(l["r"])].append((float(l["G_r"]), float(l["N_r_16"])))
    for fam in ("gate", "up", "down", "attention"):
        with open(os.path.join(M, f"fig-plafond-rang-{fam}.csv"), "w", encoding="utf8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["r", "G_reel", "G_perm", "N16_reel", "N16_perm"])
            for r in sorted(par[(fam, "reel")]):
                re, pe = par[(fam, "reel")][r], par[(fam, "perm")][r]
                w.writerow([r, f"{np.median([x[0] for x in re]):.6f}", f"{np.median([x[0] for x in pe]):.6f}",
                            f"{np.median([x[1] for x in re]):.6f}", f"{np.median([x[1] for x in pe]):.6f}"])
    with open(os.path.join(M, "fig-plafond-rang-plante.csv"), "w", encoding="utf8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["r", "G_plante", "G_perm", "N16_plante", "N16_perm"])
        d = {l["id"]: {} for l in lignes if l["genre"] == "temoin"}
        for l in lignes:
            if l["genre"] == "temoin":
                d[l["id"]][int(l["r"])] = (float(l["G_r"]), float(l["N_r_16"]))
        for r in sorted(d["T-plante-rang8"]):
            a, b = d["T-plante-rang8"][r], d["T-plante-rang8.perm"][r]
            w.writerow([r, f"{a[0]:.6f}", f"{b[0]:.6f}", f"{a[1]:.6f}", f"{b[1]:.6f}"])
    with open(os.path.join(M, "fig-alpha-levier.csv"), encoding="utf8") as f:
        al = list(csv.DictReader(f))
    for fam in ("gate", "up", "down", "attention"):
        with open(os.path.join(M, f"fig-alpha-levier-{fam}.csv"), "w", encoding="utf8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["id", "couche", "alpha", "N16", "E"])
            for l in al:
                if famille(l["id"]) == fam:
                    w.writerow([l["id"], l["couche"], l["alpha"], l["N16"], l["E"]])


if __name__ == "__main__":
    main()
