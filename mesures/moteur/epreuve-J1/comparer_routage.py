"""Routage de troncons (trace du moteur, une ligne par pas, L groupes de k experts) contre celui de la
vérité numpy (routage[L, P, k]) : part des (couche, position) au même ensemble d'experts, par tranche
de positions, et première bascule par couche.
Commande : python -I -X utf8 comparer_routage.py <verite.npz> <moteur.trace> <journal.json>
"""
import json
import sys

import numpy as np

z = np.load(sys.argv[1])
R = z["routage"]  # (L, P, k)
L, P, k = R.shape
lignes = [l for l in open(sys.argv[2], encoding="utf-8").read().splitlines() if l and not l.startswith(("#", "E="))]
T = np.array([[sorted(int(x) for x in g.split()) for g in l.split("|")] for l in lignes[:P]])  # (P, L, k)
egal = np.array([[set(T[p, l]) == set(R[l, p]) for p in range(P)] for l in range(L)])  # (L, P)
tranches = {}
for a, b in ((0, 256), (256, 512), (512, 600), (600, P)):
    tranches[f"{a}-{b}"] = float(egal[:, a:b].mean())
premiere = {}
for l in range(L):
    d = np.nonzero(~egal[l])[0]
    premiere[l] = int(d[0]) if d.size else None
par_couche_apres_512 = [float(egal[l, 512:].mean()) for l in range(L)]
r = {"couches": L, "positions": P, "accord_par_tranche": tranches,
     "premiere_bascule_par_couche": premiere, "accord_par_couche_positions_512_et_plus": par_couche_apres_512,
     "accord_par_couche_positions_256_511": [float(egal[l, 256:512].mean()) for l in range(L)]}
json.dump(r, open(sys.argv[3], "w", encoding="utf-8"), indent=1)
print(json.dumps({k_: r[k_] for k_ in ("accord_par_tranche",)}, indent=1))
print("par couche, 256-511 :", " ".join(f"{x:.2f}" for x in r["accord_par_couche_positions_256_511"]))
print("par couche, 512+    :", " ".join(f"{x:.2f}" for x in par_couche_apres_512))
