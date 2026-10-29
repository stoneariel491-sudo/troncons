"""Piste spectres : stabilité de la référence « permuté par rangée » d'une graine à l'autre (seuil.md § 7 undecies).

Six matrices fixées d'avance ; G_rang du permuté par rangée avec trois graines neuves, comparé à la colonne
G_rang_ref de `plafond-rangee.out` (passe principale). Seuil : écart max <= 0,0125. Témoin : la référence
« permuté complet » sur L00.down.E24 s'écarte de plus de 0,0125. Cassure (--casser) : +0,02 sur une graine
doit faire échouer le seuil.

Utilisation : python -X utf8 rangee_graine.py [--casser] > rangee-graine.out 2> rangee-graine.log
"""
from __future__ import annotations

import commun

import csv
import os
import sys

import numpy as np

import plafond_rangee as pr

M = commun.MESURES
CHOIX = ["L00.down.E24", "L00.gate.E22", "L12.up.E01", "L12.down.E01", "L23.gate.E07", "L23.attn_output"]
GRAINES = (777001, 777002, 777003)
TOL = 0.0125


def main() -> None:
    commun.priorite_basse()
    casser = "--casser" in sys.argv
    with open(os.path.join(M, "plafond-rangee.out"), encoding="utf8") as f:
        principal = {l["id"]: float(l["G_rang_ref"]) for l in csv.DictReader(f)}
    lec = commun.lecteur()
    index = {t.nom: t for t in lec.tenseurs}
    mats = {m["id"]: m for m in commun.echantillon()}
    ecart_max, ecrit = 0.0, csv.writer(sys.stdout, lineterminator="\n")
    ecrit.writerow(["id", "graine", "G_rang_ref", "principal", "ecart"])
    t_complet = None
    for k, i in enumerate(CHOIX):
        commun.attendre_calme()
        w = commun.matrice(lec, index, mats[i])
        for j, g in enumerate(GRAINES):
            rng = np.random.default_rng(g)
            v = pr.g_rang(rng.permuted(w, axis=1))[0] + (0.02 if casser and k == 0 and j == 0 else 0.0)
            e = v - principal[i]
            ecart_max = max(ecart_max, abs(e))
            ecrit.writerow([i, g, f"{v:.6f}", f"{principal[i]:.6f}", f"{e:+.6f}"])
            print(f"{i:18s} graine {g}  G_rang_ref {v:+.4f}  principal {principal[i]:+.4f}  écart {e:+.4f}",
                  file=sys.stderr, flush=True)
        if i == "L00.down.E24" and not casser:
            commun.attendre_calme()
            wp = np.random.default_rng(GRAINES[0]).permutation(w.ravel()).reshape(w.shape)
            t_complet = pr.g_rang(wp)[0] - principal[i]
        del w
    ok = ecart_max <= TOL
    print(f"\nécart maximal {ecart_max:.4f} (seuil {TOL}) : {'TIENT' if ok else 'ÉCHEC'}", file=sys.stderr)
    if t_complet is not None:
        print(f"témoin : référence « permuté complet » sur L00.down.E24 s'écarte de {t_complet:+.4f} "
              f"(attendu > {TOL} en valeur absolue) : {'TIENT' if abs(t_complet) > TOL else 'ÉCHEC'}",
              file=sys.stderr)


if __name__ == "__main__":
    main()
