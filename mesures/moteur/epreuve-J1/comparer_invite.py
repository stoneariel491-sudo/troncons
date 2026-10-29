"""Argmax position par position : vérité numpy (argmax_toutes) contre l'empreinte CSV de troncons.

Rend le taux d'accord par tranche de positions, la première position en désaccord, et, sur les
positions notées du .kld de troncons, la KL(vérité ‖ troncons).
Commande : python -I -X utf8 comparer_invite.py <verite.npz> <empreintes.csv> <troncons.kld> <journal.json>
"""
import csv
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comparer_kld import Kld, kl  # noqa: E402

z = np.load(sys.argv[1])
am = z["argmax_toutes"]
lpa = z["lp_argmax_toutes"]
lignes = list(csv.DictReader(open(sys.argv[2], encoding="utf-8")))
at = np.array([int(r["argmax"]) for r in lignes])
P = len(am)
accord = at[:P] == am
tranches = {}
for a, b in ((0, 128), (128, 256), (256, 384), (384, 512), (512, 640), (640, P)):
    tranches[f"{a}-{b}"] = float(accord[a:b].mean())
k = Kld(sys.argv[3])
lp = z["log_p"]
pos = z["positions"]
kls = np.array([kl(lp[i].astype(np.float64), k.log_p(0, int(p))) for i, p in enumerate(pos) if p < k.n_ctx - 1])
pk = pos[: kls.size]
r = {"positions": P, "accord_argmax_total": float(accord.mean()), "accord_par_tranche": tranches,
     "premieres_positions_en_desaccord": [int(i) for i in np.nonzero(~accord)[0][:20]],
     "kl_moyenne_par_tranche": {f"{a}-{b}": float(kls[(pk >= a) & (pk < b)].mean())
                                for a, b in ((354, 512), (512, 640), (640, 707)) if ((pk >= a) & (pk < b)).any()},
     "derniere_position": {"verite_argmax": int(am[-1]), "troncons_argmax": int(at[P - 1]),
                           "verite_lp_argmax": float(lpa[-1])}}
json.dump(r, open(sys.argv[4], "w", encoding="utf-8"), indent=1)
print(json.dumps(r, indent=1))
