"""Témoin T2bis (amendement du 2026-10-26) : PB avec le prédicteur appris, relevé par l'indicateur vrai
du prochain jeton. Seuil déclaré : au moins +0,05 sur la référence (dialogue, N = 323)."""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m1_m2 as m
m.sous_la_normale()
traces, sortie = sys.argv[1], sys.argv[2]
d = json.load(open(os.path.join(sortie, "m1_m2.json")))
w = np.array(d["M1_poids"])
cl = m.charger("chargement_localite")
jetons, E = cl.lire_trace(os.path.join(traces, "t120b.dialogue.lecture.trace"))
A = m.vers_tableau(jetons, len(jetons[0]), E)
h = m.pb(A, 323, w, oracle="mixte")
ref = d["M1"]["dialogue (lecture)"]["323"]["ref"]
base = max(ref["lru"], ref["lfu_meilleur"])
res = {"pb_mixte": h, "reference": base, "delta": h - base, "seuil": 0.05, "tient": (h - base) >= 0.05}
print(res)
json.dump(res, open(os.path.join(sortie, "t2bis.json"), "w"), indent=1)
