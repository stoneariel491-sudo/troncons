"""Piste spectres : les témoins de l'instrument (seuil.md § 5), et leur cassure.

- T-Pareto doit être reconnu « loi de puissance », α̂ ∈ [2,3 ; 2,7] ;
- T-MP (les trois formes), T-exp, T-lognormale ne doivent pas l'être.
`--casser` échange les entrées de T-Pareto et de T-MP 2880×2880 : les deux doivent afficher ÉCHEC.

Utilisation : python -X utf8 temoins.py [--casser] > journal.json
"""
from __future__ import annotations

import commun

import json
import os
import sys

import numpy as np

import csn


def main() -> None:
    commun.priorite_basse()
    casser = "--casser" in sys.argv
    vs = np.load(os.path.join(commun.MESURES, "valeurs-singulieres.npz"))
    rng = np.random.default_rng(commun.GRAINE + 1)
    entrees = {
        "T-Pareto": vs["pareto"] ** 2,
        "T-MP 2880x2880": vs["mp/2880x2880"] ** 2,
        "T-MP 4096x2880": vs["mp/4096x2880"] ** 2,
        "T-MP 2880x4096": vs["mp/2880x4096"] ** 2,
        "T-MP 512x2880": vs["mp/512x2880"] ** 2,
        "T-exp": rng.exponential(1.0, 2880),
        "T-lognormale": rng.lognormal(0.0, 1.0, 2880),
    }
    if casser:
        entrees["T-Pareto"], entrees["T-MP 2880x2880"] = entrees["T-MP 2880x2880"], entrees["T-Pareto"]
    sortie = {"casser": casser, "temoins": {}}
    tous = True
    for nom, val in entrees.items():
        commun.attendre_calme()
        r = csn.ajuster(val, rng=np.random.default_rng(commun.GRAINE + 2), repliques=100)
        if nom == "T-Pareto":
            ok = r["verdict"] == "loi de puissance" and 2.3 <= r["alpha"] <= 2.7
        else:
            ok = r["verdict"] != "loi de puissance"
        r["attendu"] = "loi de puissance, α ∈ [2,3 ; 2,7]" if nom == "T-Pareto" else "pas loi de puissance"
        r["resultat"] = "TIENT" if ok else "ÉCHEC"
        tous &= ok
        sortie["temoins"][nom] = r
        print(f"{nom:16s} {r['resultat']:5s} verdict={r['verdict']:20s} α={r['alpha']:.3f}±{r['alpha_err']:.3f} "
              f"n_queue={r['n_queue']} R_exp={r['R_exp']:.1f} (p={r['p_exp']:.2g}) "
              f"R_ln={r['R_lognormale']:.1f} (p={r['p_lognormale']:.2g}) p_gof={r['p_gof']:.2f}",
              file=sys.stderr, flush=True)
    sortie["tous_tiennent"] = tous
    print(json.dumps(sortie, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
