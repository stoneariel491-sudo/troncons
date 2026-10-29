"""Écart des log-probabilités entre la vérité numpy du juge et un .kld, hors plancher du format.

Pour chaque position notée : max |log q − log p| sur les jetons au-dessus du plancher du fichier
(code > 0), et la même chose pondérée par p. Le pas de quantification du fichier (≤ 16 / 65 535 =
2,4·10⁻⁴ nat) borne ce qu'un calcul identique peut donner : un écart sous pas/2 + l'arrondi f32 du
fichier est « égal au format près ».
Commande : python -I -X utf8 ecart_logp.py <verite.npz> <journal.json> --fichier nom=chemin …
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comparer_kld import Kld  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("npz")
ap.add_argument("journal")
ap.add_argument("--fichier", action="append", default=[])
a = ap.parse_args()
z = np.load(a.npz)
lp_tout, pos, fen = z["log_p"], z["positions"], int(z["fenetre"])
res = {}
for nom, c in (f.split("=", 1) for f in a.fichier):
    k = Kld(c)
    ecarts, pas_max, rapport = [], [], []
    for i, p in enumerate(pos):
        lq = k.log_p(fen, int(p))
        lp = lp_tout[i]
        dessus = lq > lq.min()
        e = float(np.abs(lq[dessus] - lp[dessus]).max())
        ecarts.append(e)
        pas = (lq[dessus].max() - lq.min()) / 65535
        pas_max.append(float(pas))
        rapport.append(e / pas)
    res[nom] = {"ecart_max": float(max(ecarts)), "ecart_median": float(np.median(ecarts)),
                "pas_median": float(np.median(pas_max)), "ecart_max_en_pas": float(max(rapport)),
                "positions_sous_un_pas": int(sum(r <= 1.0 for r in rapport)), "n": len(pos)}
    print(nom, json.dumps(res[nom]))
json.dump(res, open(a.journal, "w", encoding="utf-8"), indent=1)
