"""E-G : résidence partielle (« polymérase en pause »). Seuil et prédiction : seuil-declare.md, ajout du 2026-10-27.

Octets lus par accès, en experts pleins : A = 1 - h(X) ; B = (1 - h(X/r)) + h(X/r) (1 - r), r = 2,64 / 3,68.
h : succès LRU par couche (moyenne des couches), interpolé linéairement entre budgets entiers.
Usage : python -I residence_partielle.py DOSSIER_TRACES
"""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

ici = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("bt", ici / "bancs_traces.py")
bt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bt)
bt.sous_la_normale()

R = 2.64 / 3.68
dossier = sys.argv[1]
res = {}
for modele in ("20b", "120b"):
    Cmax = 32 if modele == "20b" else 64
    res[modele] = {}
    for g in bt.GENRES:
        sets, _, E = bt.charger(dossier, modele, g)
        h = bt.mrc_lru(sets, Cmax).mean(axis=0)       # h[C], C >= 4 ; h[<4] = 0 hors domaine
        hh = lambda x: float(np.interp(x, np.arange(Cmax + 1), h))
        lignes = {}
        for X in range(4, int(Cmax * R)):
            A = 1 - hh(X)
            B = (1 - hh(X / R)) + hh(X / R) * (1 - R)
            lignes[str(X)] = {"A": A, "B": B, "B_sur_A": B / A}
        res[modele][g] = lignes
        c0 = bt.BUDGETS[modele]
        print(modele, g, {str(x): round(lignes[str(x)]["B_sur_A"], 3) for x in c0}, "min B/A sur X :",
              round(min(v["B_sur_A"] for v in lignes.values()), 3), flush=True)
verdict = {}
for modele in res:
    verdict[modele] = {}
    for C0 in bt.BUDGETS[modele]:
        v = [res[modele][g][str(C0)]["B_sur_A"] for g in bt.GENRES]
        verdict[modele][str(C0)] = {"B_sur_A": v, "passe": sum(1 for x in v if x <= 0.9) >= 4}
out = {"brut": res, "verdict": verdict}
bt.ecrire("eg.json", out)
print(json.dumps({m: {c: x["passe"] for c, x in d.items()} for m, d in verdict.items()}))
