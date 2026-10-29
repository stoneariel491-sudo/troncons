"""Piste spectres, pas 3 : ajustement CSN des 48 spectres réels et de leurs témoins T-perm.

Lit `valeurs-singulieres.npz` ; ajuste sur λ = σ² (seuil.md § 2) ; écrit sur la sortie standard
le CSV `ajustements.csv` (une ligne par matrice réelle, avec son témoin permuté à côté).

Utilisation : python -X utf8 ajuster.py > ajustements.csv
"""
from __future__ import annotations

import commun

import csv
import json
import os
import sys

import numpy as np

import csn
from puissance_critere import compatible

COLONNES = ["id", "couche", "role", "expert", "m", "n", "n_valeurs",
            "alpha", "alpha_err", "x_min", "n_queue", "ks",
            "R_exp", "p_exp", "R_lognormale", "p_lognormale", "lognormale_mu", "lognormale_sigma",
            "p_gof", "verdict", "verdict_strict", "compatible",
            "perm_alpha", "perm_n_queue", "perm_verdict", "perm_compatible",
            "part_energie_5pc", "part_energie_5pc_perm", "sigma1_sur_rms", "sigma1_sur_rms_perm"]


def part5(s: np.ndarray) -> float:
    e = s ** 2
    r = max(1, int(round(0.05 * s.size)))
    return float(e[:r].sum() / e.sum())


def main() -> None:
    commun.priorite_basse()
    vs = np.load(os.path.join(commun.MESURES, "valeurs-singulieres.npz"))
    with open(os.path.join(commun.MESURES, "manifeste.json"), encoding="utf8") as f:
        man = {m["id"]: m for m in json.load(f)["matrices"]}
    ecrivain = csv.DictWriter(sys.stdout, fieldnames=COLONNES, lineterminator="\n")
    ecrivain.writeheader()
    for i, m in enumerate(commun.echantillon()):
        commun.attendre_calme()
        s = vs[f"reel/{m['id']}"]
        sp = vs[f"perm/{m['id']}"]
        rng = np.random.default_rng(commun.GRAINE + 100 + i)
        r = csn.ajuster(s ** 2, rng=rng, repliques=100)
        rp = csn.ajuster(sp ** 2, rng=rng, repliques=100)
        ligne = {
            "id": m["id"], "couche": m["couche"], "role": m["role"], "expert": m["expert"],
            "m": man[m["id"]]["forme"][0], "n": man[m["id"]]["forme"][1], "n_valeurs": s.size,
            "alpha": r["alpha"], "alpha_err": r["alpha_err"], "x_min": r["x_min"], "n_queue": r["n_queue"],
            "ks": r["ks"], "R_exp": r["R_exp"], "p_exp": r["p_exp"], "R_lognormale": r["R_lognormale"],
            "p_lognormale": r["p_lognormale"], "lognormale_mu": r["lognormale"]["mu"],
            "lognormale_sigma": r["lognormale"]["sigma"], "p_gof": r["p_gof"], "verdict": r["verdict"],
            "verdict_strict": r["verdict_strict"], "compatible": compatible(r),
            "perm_alpha": rp["alpha"], "perm_n_queue": rp["n_queue"], "perm_verdict": rp["verdict"],
            "perm_compatible": compatible(rp),
            "part_energie_5pc": part5(s), "part_energie_5pc_perm": part5(sp),
            "sigma1_sur_rms": float(s[0] / np.sqrt((s ** 2).mean())),
            "sigma1_sur_rms_perm": float(sp[0] / np.sqrt((sp ** 2).mean())),
        }
        ecrivain.writerow(ligne)
        sys.stdout.flush()
        print(f"{m['id']:16s} α={r['alpha']:.2f} n_q={r['n_queue']} {r['verdict']:18s} "
              f"compat={compatible(r)} p_gof={r['p_gof']:.2f} | perm α={rp['alpha']:.2f} "
              f"{rp['verdict']} compat={compatible(rp)}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
