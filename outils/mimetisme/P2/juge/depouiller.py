"""P2, juge : confronte juge-brut.json aux seuils de genome/mimetisme/P2/juge-seuil.md (rend verdict-juge.json).
Usage : python -I -X utf8 depouiller.py <dossier mesures/mimetisme/P2/juge>"""
import json
import os
import sys

d = sys.argv[1]
B = json.load(open(os.path.join(d, "juge-brut.json"), encoding="utf-8"))
A, BR, JETON = 4.1, 1.09, 345.0
ANNONCE = {"prose-en.generation": dict(inc=0.2573, exc=0.1845, desc=36.5, s1=0.1769, d1=18.1),
           "wiki.generation": dict(inc=0.5926, exc=0.2885, desc=85.9, s1=0.3649, d1=42.7)}
ANNONCE_TEMPS = {"prose-en.generation": dict(seul=154.7, serie=160.9, recouvert=121.1),
                 "wiki.generation": dict(seul=357.6, serie=313.8, recouvert=220.1)}
V = {}
for nom, a in ANNONCE.items():
    r = B[nom]
    inc, exc = r["inclusif"], r["exclusif"]
    red = (inc["part_disque"] - exc["part_disque"]) / inc["part_disque"]
    desc_ms = exc["descentes_par_jeton"] * BR
    j1 = (abs(inc["part_disque"] - a["inc"]) <= 1e-3 and abs(exc["part_disque"] - a["exc"]) <= 1e-3
          and abs(exc["descentes_par_jeton"] / a["desc"] - 1) <= 0.02)
    md = r["mattson_defauts"]
    j2_exact = r["exclusif_sans_pins"]["disque"] == md[str(326 + 336)]
    j2_seul_exact = None
    j2_pins = abs(exc["part_disque"] - r["lru_VR_pins"]["part_disque"])
    casse = {k: r[k]["part_disque"] - exc["part_disque"] for k in ("casse_mru", "casse_garde", "exclusif_ram_fifo")}
    j3 = abs(casse["casse_mru"]) > 1e-2 and abs(casse["casse_garde"]) > 1e-2
    sens = {"inclusif_ordre_inverse": r["inclusif_ordre_inverse"]["part_disque"] - inc["part_disque"],
            "exclusif_ordre_inverse": r["exclusif_ordre_inverse"]["part_disque"] - exc["part_disque"],
            "inclusif_pins_ram": r["inclusif_pins_ram"]["part_disque"] - inc["part_disque"],
            "succes_ram_inclusif_R336": inc["sr"] / inc["acces"],
            "succes_ram_inclusif_R160": r["inclusif_R160"]["sr"] / r["inclusif_R160"]["acces"]}
    seul = r["seul"]
    t_seul = seul["disque_par_jeton"] * A
    t_rec = exc["disque_par_jeton"] * A + exc["ram_par_jeton"] * BR
    t_ser = t_rec + desc_ms
    s1 = r["selectif_s1"]
    t1_rec = s1["disque_par_jeton"] * A + s1["ram_par_jeton"] * BR
    t1_ser = t1_rec + s1["descentes_par_jeton"] * BR
    j4c = (abs(t_seul - ANNONCE_TEMPS[nom]["seul"]) <= 1 and abs(t_ser - ANNONCE_TEMPS[nom]["serie"]) <= 1
           and abs(t_rec - ANNONCE_TEMPS[nom]["recouvert"]) <= 1)
    j5 = (abs(s1["part_disque"] - a["s1"]) <= 1e-3 and abs(s1["descentes_par_jeton"] / a["d1"] - 1) <= 0.02
          and r["selectif_s0"]["disque"] == exc["disque"] and r["selectif_s0"]["descentes"] == exc["descentes"])
    V[nom] = dict(
        part_inclusif=inc["part_disque"], part_exclusif=exc["part_disque"], reduction=red,
        descentes_par_jeton=exc["descentes_par_jeton"], descente_sur_345=desc_ms / JETON,
        descente_sur_jeton_propre=desc_ms / max(JETON, t_seul), J1=j1,
        mattson_LRU_VR=md[str(326 + 336)], exclusif_sans_pins=r["exclusif_sans_pins"]["disque"], J2_exact=j2_exact,
        J2_ecart_pins=j2_pins, J2=j2_exact and j2_pins <= 7e-4,
        mattson_LRU_V=md["326"], cassures=casse, J3=j3, sensibilite=sens,
        temps=dict(seul=t_seul, serie=t_ser, recouvert=t_rec, gain_serie=t_seul - t_ser, gain_recouvert=t_seul - t_rec,
                   s1_serie=t1_ser, s1_gain_serie=t_seul - t1_ser), J4c=j4c,
        s1=dict(part=s1["part_disque"], descentes=s1["descentes_par_jeton"],
                reduction_contre_inclusif=(inc["part_disque"] - s1["part_disque"]) / inc["part_disque"]), J5_120b=j5)
P = V["prose-en.generation"]
W = V["wiki.generation"]
cond1 = P["reduction"] >= 0.15 and W["reduction"] >= 0.15
cond2 = P["descente_sur_345"] <= 0.25 and W["descente_sur_345"] <= 0.25
mort = P["reduction"] < 0.05 or W["reduction"] < 0.05
V["verdict_P2_par_mon_chemin"] = "tient" if (cond1 and cond2) else ("tombe" if mort else "ouvert")
# 20b
v20 = {}
for Vk in ("V154", "V54"):
    a = b = c = 0
    detail = {}
    for g, r in B["20b"].items():
        x = r[Vk]
        red = (x["inclusif"]["part_disque"] - x["s1"]["part_disque"]) / x["inclusif"]["part_disque"]
        ok_a = red >= 0.15
        ok_b = x["s1"]["part_disque"] <= x["s0"]["part_disque"] + 0.01
        ok_c = x["s1"]["descentes"] <= 0.6 * x["s0"]["descentes"]
        a += ok_a; b += ok_b; c += ok_c
        detail[g] = dict(reduction=red, s1=x["s1"]["part_disque"], s0=x["s0"]["part_disque"],
                         ratio_descentes=x["s1"]["descentes"] / max(1, x["s0"]["descentes"]),
                         part_seul=x["seul"]["part_disque"])
    verdict = "succes" if (a >= 4 and b >= 4 and c == 5) else ("mort" if (5 - b) >= 3 else "ouvert")
    v20[Vk] = dict(a=a, b=b, c=c, verdict=verdict, detail=detail)
V["20b_selectif"] = v20
json.dump(V, open(os.path.join(d, "verdict-juge.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(json.dumps(V, indent=1, ensure_ascii=False))
