"""Témoin de l'instrument du juge : log Σ exp(log q) de chaque entrée d'un .kld (0 si normalisé).

Le format de llama-perplexity code log q ≈ pas · code + log q min, où les logits sous max − 16
reçoivent le code 0 (log q min). Ce qui dépasse 0 vient de la quantification et de ce plancher.
Commande : python -I -X utf8 normalisation_kld.py <journal.json> --fichier nom=chemin [--fenetre 0]
           [--positions 256:511] [--npz verite.npz]
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comparer_kld import Kld  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("journal")
ap.add_argument("--fichier", action="append", default=[])
ap.add_argument("--fenetre", type=int, default=0)
ap.add_argument("--positions", default="256:511")
ap.add_argument("--npz")
a = ap.parse_args()
p0, p1 = (int(x) for x in a.positions.split(":"))
v = np.load(a.npz)["log_p"] if a.npz else None
res = {}
for nom, c in (f.split("=", 1) for f in a.fichier):
    k = Kld(c)
    lse, plancher, decal = [], [], []
    for p in range(p0, p1):
        lq = k.log_p(a.fenetre, p)
        m = lq.max()
        lse.append(float(m + np.log(np.exp(lq - m).sum())))
        plancher.append(int((lq == lq.min()).sum()))
        if v is not None:
            lp = v[p - p0]
            i = int(np.argmax(lp))
            decal.append(float(lq[i] - lp[i]))
    lse = np.array(lse)
    res[nom] = {"lse_moyen": float(lse.mean()), "lse_min": float(lse.min()), "lse_max": float(lse.max()),
                "entrees_au_plancher_moyen": float(np.mean(plancher))}
    if decal:
        res[nom]["log_q_moins_log_p_au_premier_choix_moyen"] = float(np.mean(decal))
    print(nom, json.dumps(res[nom]))
json.dump(res, open(a.journal, "w", encoding="utf-8"), indent=1)
