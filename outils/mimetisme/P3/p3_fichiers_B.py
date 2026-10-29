"""P3 : les fichiers d'entrée de l'étage B (ensembles imposés à la référence f64), autour du franchissement de -10 % de défauts.

Format : journal de routage de r1_reference.py. Écrits sous ~/dev/essais/troncons/mimetisme/P3/B ; les empreintes vont dans
mesures/mimetisme/P3/fichiers-B.json. Contient aussi le fichier de contrôle beta = 0 (KL attendue nulle au bit) et le fichier de cassure
(1 % des cellules ont leur 4e expert remplacé par un expert tiré au hasard : la KL doit être nettement non nulle).
Usage : python -I -X utf8 p3_fichiers_B.py
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p3_routage as P

Z = np.load(os.path.join(P.LOURDS, "logits-20b-eval.npy"))
ORD = P.preparer(Z)
T, L, E = Z.shape
marge = np.take_along_axis(Z, ORD[..., 3:4], -1)[..., 0] - np.take_along_axis(Z, ORD[..., 4:5], -1)[..., 0]
sortie_dir = os.path.join(P.LOURDS, "B")
os.makedirs(sortie_dir, exist_ok=True)
res = {}
plan = [("V1", b, "19") for b in (0.0, 0.04, 0.05, 0.06, 0.07, 0.08)] + [("V1", b, "31") for b in (0.0, 0.04, 0.05, 0.06)] + [("V2", 0.1, "19")]
for variante, beta, nom in plan:
    n = round(P.BUDGETS[nom] * L * E)
    S, M, d = P.simuler(Z, ORD, n, beta, variante)
    chemin = os.path.join(sortie_dir, f"routage-impose-{variante}-b{beta}-N{nom}.bin")
    res[os.path.basename(chemin)] = {"defauts": d, "sha256": P.ecrire_journal(S, marge, chemin)}
    print(os.path.basename(chemin), d, flush=True)
# cassure : 1 % des cellules, 4e expert remplacé par un expert hors de l'ensemble
S0, _, _ = P.simuler(Z, ORD, round(0.19 * L * E), 0.0)
rng = np.random.default_rng(20261027)
S = S0.copy()
for i in rng.permutation(T * L)[: T * L // 100]:
    t, l = divmod(int(i), L)
    hors = [e for e in range(E) if e not in S[t, l]]
    S[t, l, 3] = rng.choice(hors)
chemin = os.path.join(sortie_dir, "routage-impose-CASSURE-1pct.bin")
res[os.path.basename(chemin)] = {"cellules_cassees": T * L // 100, "sha256": P.ecrire_journal(S, marge, chemin)}
json.dump(res, open(os.path.join(P.SORTIE, "fichiers-B.json"), "w", encoding="utf-8"), indent=1)
