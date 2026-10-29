"""P2, juge, contrôle hors seuil (dit comme tel) : l'inclusif à R <= V est dégénéré par construction ; la vraie
alternative à l'exclusif est l'inclusif avec plus de RAM (aucune descente). Compare à budget de RAM égal en Go :
exclusif décodé (13,25 Mo l'entrée) contre inclusif encodé (11,6 Mo) ou décodé.
Usage : python -I -X utf8 a_budget_egal.py <dossier traces 120b> <json de sortie>"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from juge_p2 import jouer, lire_trace  # noqa: E402

d120, sortie = sys.argv[1], sys.argv[2]
A, B_DEC, B_ENC = 4.1, 1.09, 1.8
V = 326
res = {}
for nom, f in {"prose-en.generation": "t120b.prose-en.generation.trace",
               "wiki.generation": "w120b.wiki.generation.trace"}.items():
    G, L, E = lire_trace(os.path.join(d120, f))
    n = L * E
    r = {}
    seul = jouer(G, n, V, 0, "seul")
    t_seul = seul["disque_par_jeton"] * A
    for R in (336, 384, 507, 662):
        for mode in ("inclusif", "exclusif"):
            k = jouer(G, n, V, R, mode)
            if mode == "exclusif":
                go = R * 13.25e-3
                t_rec = k["disque_par_jeton"] * A + k["ram_par_jeton"] * B_DEC
                t_ser = t_rec + k["descentes_par_jeton"] * B_DEC
            else:
                go = R * 11.6e-3
                t_rec = k["disque_par_jeton"] * A + k["ram_par_jeton"] * B_ENC
                t_ser = t_rec
            r[f"{mode}_R{R}"] = dict(part_disque=k["part_disque"], go=go, descentes=k["descentes_par_jeton"],
                                     gain_serie_ms=t_seul - t_ser, gain_recouvert_ms=t_seul - t_rec)
    res[nom] = r
    print(nom, json.dumps(r, indent=1), flush=True)
json.dump(res, open(sortie, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
