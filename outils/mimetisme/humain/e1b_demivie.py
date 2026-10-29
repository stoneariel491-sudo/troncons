"""E1b (POST HOC, non déclaré avant) : le LFU du dépôt (demi-vie 8) est-il mal réglé ? Balayage de la demi-vie,
pooled et par genre, et meilleur réglage par genre (borne de ce qu'un apprentissage en ligne du réglage pourrait rendre).
Usage : python -I -X utf8 e1b_demivie.py <dossier_traces> <prefixe> <sortie.json>
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e1_memoire as m  # noqa: E402

dossier, prefixe, sortie = sys.argv[1], sys.argv[2], sys.argv[3]
genres, tous, E = m.charger(dossier, prefixe)
HL = [2, 4, 8, 16, 32, 64, 128, 256]
res = {}
traces = {"pooled": tous, **genres}
for nom, j in traces.items():
    L, k = len(j[0]), len(j[0][0])
    gs = m.gl.flux(j, E)
    res[nom] = {}
    for f in (0.15, 0.20):
        N = max(k, round(f * L * E))
        res[nom][f"{f:.2f}"] = {str(h): m.gl.g_lfu(gs, N, L, demi_vie=float(h)) for h in HL}
        print(prefixe, nom, f, res[nom][f"{f:.2f}"], flush=True)
json.dump(res, open(sortie, "w", encoding="utf-8"), indent=1)
