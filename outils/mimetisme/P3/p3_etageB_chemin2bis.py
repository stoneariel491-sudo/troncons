"""P3 étage B, second chemin du chiffre principal : KL moyenne, premier choix identique, KL cumulée par fenêtre
et arrêt d'O'Brien-Fleming, recalculés en numpy depuis le CSV par position du juge (sans repasser par son résumé).
Usage : python p3_etageB_chemin2bis.py <nom> [<nom> ...]   (dossier mesures/mimetisme/P3/etage-B)"""
import csv
import json
import math
import pathlib
import sys

import numpy as np

D = pathlib.Path("~/dev/active/troncons/mesures/mimetisme/P3/etage-B")
sortie = {}
for nom in sys.argv[1:]:
    fen, kl, mp = [], [], []
    with open(D / f"juge-kl-p3-{nom}.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            fen.append(int(r["fenetre"])); kl.append(float(r["kl"])); mp.append(int(r["meme_premier"]))
    fen, kl, mp = np.array(fen), np.array(kl), np.array(mp)
    par = [float(kl[fen == w].mean()) for w in range(10)]
    cum6 = float(kl[fen < 6].mean())
    # écart-type de la moyenne par rééchantillonnage des fenêtres (bootstrap, 20 000 tirages, graine 1)
    rng = np.random.default_rng(1)
    bs = [np.mean(rng.choice(par, 10)) for _ in range(20000)]
    sortie[nom] = {"n": int(len(kl)), "kl_moyenne": float(kl.mean()), "meme_premier": float(mp.mean()),
                   "kl_par_fenetre": par, "kl_cumulee_6_premieres_fenetres": cum6,
                   "kl_bootstrap_fenetres_p2_5_p97_5": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                   "arret_OBF_cum6_depasse_0_07": cum6 > 0.07}
print(json.dumps(sortie, indent=1))
(D / "chemin2bis-" + "-".join(sys.argv[1:]) + ".json" if False else D / ("chemin2bis-" + "-".join(sys.argv[1:]) + ".json")).write_text(json.dumps(sortie, indent=1), encoding="utf-8")
