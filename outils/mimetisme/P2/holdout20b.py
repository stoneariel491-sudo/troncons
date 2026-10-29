"""P2, test de la démotion sélective sur le 20b (seuil : genome/mimetisme/P2/seuil-declare-selectif.md).
Usage : python -I -X utf8 holdout20b.py <dossier des traces 20b> <csv de sortie> <json des témoins>
"""
import csv
import json
import sys

import numpy as np

sys.path.insert(0, "~/dev/active/troncons/outils/mimetisme/P2")
import cache_exclusif as ce  # noqa: E402
from explorations import sim_sel  # noqa: E402

ce.L, ce.E, ce.K = 24, 32, 4
L = 24
N = 24 * 32
FICH = {}
for g in ("code", "dialogue", "prose-en", "prose-fr"):
    FICH[f"{g}.lecture"] = f"t20b.{g}.lecture.trace"
    FICH[f"{g}.generation"] = f"t20b.{g}.generation.trace"
FICH["wiki.lecture"] = "w20b.wiki.lecture.trace"
FICH["wiki.generation"] = "w20b.wiki.generation.trace"

dossier, sortie, sortie_t = sys.argv[1], sys.argv[2], sys.argv[3]
tr = {k: ce.charger(f"{dossier}/{f}") for k, f in FICH.items()}
Vp, Vs, R = round(0.0707 * N), round(0.2001 * N), round(0.0729 * N)
print("N", N, "V", Vp, Vs, "R", R, flush=True)
lignes = []
tem = {"N": N, "V": [Vp, Vs], "R": R}
t0 = t1 = t2 = t3 = cas = True
t2d = {}
for nom, G in tr.items():
    for V in (Vp, Vs):
        seul = ce.sim(G, V, 0, "seul")
        inc = ce.sim(G, V, R, "inclusif")
        exc = ce.sim(G, V, R, "exclusif")
        s0 = sim_sel(G, V, R, 0, L)
        s1 = sim_sel(G, V, R, 1, L)
        sinf = sim_sel(G, V, R, 10 ** 9, L)
        t3 &= (s0["disque"] == exc["disque"] and s0["demotions"] == exc["demotions"])
        cas &= (sinf["disque"] == seul["disque"] and sinf["demotions"] == 0)
        u = ce.sim(G, V + R, 0, "seul")
        e2 = exc["succes_vram"] + exc["succes_ram"] - u["succes_vram"]
        t2d[f"{nom}|V={V}"] = round(e2, 6)
        t2 &= abs(e2) <= 7e-4
        t0 &= ce.sim(G, V, 0, "exclusif")["disque"] == seul["disque"]
        if V == Vp:
            i40 = ce.sim(G, V, 40, "inclusif")
            t1 &= i40["succes_ram"] <= 1e-4
        for nm, c in (("seul", seul), ("inclusif", inc), ("exclusif", exc)):
            lignes.append([nom, V, R, nm, "", round(c["part_disque"], 6), round(c["demotions"] / c["jetons"], 4), c["jetons"]])
        lignes.append([nom, V, R, "sel_s0", 0, round(s0["part_disque"], 6), round(s0["demotions"] / s0["jetons"], 4), s0["jetons"]])
        lignes.append([nom, V, R, "sel_s1", 1, round(s1["part_disque"], 6), round(s1["demotions"] / s1["jetons"], 4), s1["jetons"]])
        lignes.append([nom, V, R, "sel_s1_defauts_vram", 1, round(1 - s1["sv"] / s1["acces"], 6), round(1 - s1["sv"] / s1["acces"], 6), s1["jetons"]])
    print(nom, flush=True)
tem.update(T0=bool(t0), T1=bool(t1), T2=bool(t2), T2_ecarts=t2d, T3_s0_egale_exclusif=bool(t3), cassure_s_infini_redonne_seul=bool(cas))
with open(sortie, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["trace", "V", "R", "mode", "s", "part_disque", "demotions_par_jeton", "jetons"])
    w.writerows(lignes)
json.dump(tem, open(sortie_t, "w", encoding="utf-8"), indent=1)
print(tem)
