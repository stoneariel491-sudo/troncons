"""P3 étage B à N = 238 : choix de beta_1 (premier pas de 0,001 qui retire au moins 10 % des défauts) et fichiers imposés.

Ne lit aucune KL. Défauts rejoués par le LRU de simuler() puis par le second chemin (cache2.py, W5).
Usage : python -I -X utf8 p3_fichiers_N238.py [beta ...]   (sans argument : balayage 0,040 à 0,050 par pas de 0,001)
Écrit sous ~/dev/essais/troncons/mimetisme/P3/B238 et mesures/mimetisme/P3/ensembles-N238.json.
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
n = round(P.BUDGETS["31"] * L * E)
dossier = os.path.join(P.LOURDS, "B238")
os.makedirs(dossier, exist_ok=True)
S0, _, d0 = P.simuler(Z, ORD, n, 0.0)
betas = [float(x) for x in sys.argv[1:]] or [round(0.040 + 0.001 * i, 3) for i in range(11)]
res = {"N": n, "defauts_beta0": d0, "seuil_10pct": d0 * 0.9, "lignes": {}}
for b in betas:
    S, M, d = P.simuler(Z, ORD, n, b)
    chemin = os.path.join(dossier, f"routage-impose-V1-b{b}-N31.bin")
    sha = P.ecrire_journal(S, marge, chemin)
    rej = P.rejouer_cache2(S, n)
    chg = P.statistiques(Z, ORD, S0, S)
    res["lignes"][str(b)] = {"defauts": d, "variation": d / d0 - 1, "rejeu_cache2": rej, "sha256": sha, "stats": {k: float(v) for k, v in chg.items()}}
    print(b, d, round(d / d0 - 1, 5), rej, chg, flush=True)
json.dump(res, open(os.path.join(P.SORTIE, "ensembles-N238.json" if len(sys.argv) > 1 else "balayage-N238.json"), "w", encoding="utf-8"), indent=1)
