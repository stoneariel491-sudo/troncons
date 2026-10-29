"""Données de la figure F-S2 du lot B : la fonction de survie de la KL par position, P(KL > t),
sur une grille logarithmique de t, pour plusieurs passes `juge kl` (CSV par position).

Écrit pour troncons, rôle « synonyme » de la construction, le 2026-10-17. N'entre dans aucun verdict.

Usage : python -I -X utf8 survie_kl.py sortie.csv nom1=positions1.csv [nom2=positions2.csv …]
"""
from __future__ import annotations

import csv
import math
import sys


def main():
    sortie = sys.argv[1]
    series = {}
    for arg in sys.argv[2:]:
        nom, chemin = arg.split("=", 1)
        with open(chemin, encoding="utf-8") as f:
            series[nom] = sorted(float(r["kl"]) for r in csv.DictReader(f))
    grille = [10 ** (-5 + 0.05 * i) for i in range(int(6 / 0.05) + 1)]  # 1e-5 à 10
    with open(sortie, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["t"] + list(series))
        for t in grille:
            ligne = [f"{t:.6e}"]
            for v in series.values():
                # nombre de valeurs > t par recherche dichotomique
                lo, hi = 0, len(v)
                while lo < hi:
                    m = (lo + hi) // 2
                    if v[m] <= t:
                        lo = m + 1
                    else:
                        hi = m
                ligne.append(f"{(len(v) - lo) / len(v):.6f}")
            w.writerow(ligne)
    print(f"écrit : {sortie} ({len(grille)} points, {len(series)} séries)")


if __name__ == "__main__":
    main()
