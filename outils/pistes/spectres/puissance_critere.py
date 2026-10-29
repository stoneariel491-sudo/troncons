"""Piste spectres : la puissance du critère déclaré, mesurée sur des lois de puissance vraies.

Avant toute lecture des spectres réels : 20 tirages de Pareto (n = 2 880) pour α = 2,5 et α = 3,5,
et 20 tirages exponentiels et log-normaux ; on compte les verdicts du critère principal (seuil.md
§ 4) et ceux du critère amendé (seuil.md § 4 bis). Un critère qui ne dit jamais « oui » sur une loi
de puissance vraie ne peut rien dire des poids.

Utilisation : python -X utf8 puissance_critere.py > puissance-critere.json
"""
from __future__ import annotations

import commun

import json
import sys
from collections import Counter

import numpy as np

import csn


def compatible(r: dict) -> bool:
    """Critère amendé (seuil.md § 4 bis), le « modéré ou mieux » de CSN."""
    exp_rejetee = r["R_exp"] > 0 and r["p_exp"] < 0.05
    ln_preferee = r["R_lognormale"] < 0 and r["p_lognormale"] < 0.05
    return exp_rejetee and not ln_preferee and r["p_gof"] >= 0.1


def main() -> None:
    commun.priorite_basse()
    rng = np.random.default_rng(commun.GRAINE + 3)
    familles = {
        "Pareto α=2,5": lambda: rng.random(2880) ** (-1 / 1.5),
        "Pareto α=3,5": lambda: rng.random(2880) ** (-1 / 2.5),
        "exponentielle": lambda: rng.exponential(1.0, 2880),
        "log-normale σ=1": lambda: rng.lognormal(0.0, 1.0, 2880),
    }
    sortie = {}
    for nom, tirer in familles.items():
        principal, amende, alphas, p_ln = Counter(), Counter(), [], []
        for _ in range(20):
            commun.attendre_calme()
            r = csn.ajuster(tirer(), rng=rng, repliques=50)
            principal[r["verdict"]] += 1
            amende["compatible" if compatible(r) else "non"] += 1
            alphas.append(r["alpha"])
            p_ln.append(r["p_lognormale"])
        sortie[nom] = {"principal": dict(principal), "amende": dict(amende),
                       "alpha_mediane": float(np.median(alphas)), "p_lognormale_mediane": float(np.median(p_ln))}
        print(nom, sortie[nom], file=sys.stderr, flush=True)
    print(json.dumps(sortie, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
