"""P6 étape 0 : témoins T0, T1, T4 (et sa cassure), avant toute mesure.
Usage : python -I -X utf8 temoins.py <dossier t120> <exe noyau-cache> <dossier_sortie> <portillon-de-poids.json>"""
import json
import math
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import tiers

dossier, exe, sortie, ref_json = sys.argv[1:5]
os.makedirs(sortie, exist_ok=True)
TR = {"code": "t120b.code.lecture", "dialogue": "t120b.dialogue.lecture", "prose-en": "t120b.prose-en.lecture",
      "prose-fr": "t120b.prose-fr.lecture", "wiki-lecture": "w120b.wiki.lecture",
      "gen-prose-en": "t120b.prose-en.generation", "gen-wiki": "w120b.wiki.generation"}
N = 323
EPS = [0.02, 0.05, 0.1, 0.15, 0.2, 0.25]
RHO = 0.718
res = {}

noyau = os.path.join(sortie, "noyau-h8.txt")
open(noyau, "w").write("exp_h8\t1:%.9g\n" % (8 / math.log(2)))
data = {}
for cle, base in TR.items():
    ex, w, E = tiers.charger(os.path.join(dossier, base + ".trace"), os.path.join(dossier, base + ".poids"))
    data[cle] = (ex, w, E)

# ---- T4 : hits/total contre le Rust, sur les 7 traces
t4 = {}
for cle, base in TR.items():
    ex, w, E = data[cle]
    sj = os.path.join(sortie, f"rust-{cle}.jsonl")
    subprocess.run([exe, os.path.join(dossier, base + ".trace"), os.path.join(dossier, base + ".poids"),
                    str(N), noyau, sj], check=True)
    r = json.loads(open(sj, encoding="utf-8").readline())
    df, sj_ = tiers.cache(ex, E, N, "lfu", 8.0)
    ecart_taux = abs((1 - df.mean()) - r["taux"])
    sp = [tiers.sans_portage(df, w, e) for e in EPS]
    t4[cle] = {"rust_hits": r["hits"], "rust_total": r["total"], "rust_defauts": r["defauts"],
               "py_defauts": int(df.sum()), "ecart_taux": ecart_taux,
               "defauts_sous_ok": [sp[i]["defauts_sous"] == r["defauts_sous"][i] for i in range(6)],
               "ecart_g2_sous_max": max(abs(sp[i]["g2_defauts_sous"] - r["defauts_g2"][i]) for i in range(6)),
               "ecart_g2_total": abs(sp[0]["g2_total"] - r["g2_total"])}
    print("T4", cle, t4[cle], flush=True)
res["T4"] = t4
res["T4_tient"] = bool(all(v["ecart_taux"] < 1e-3 and v["py_defauts"] == v["rust_defauts"]
                           and all(v["defauts_sous_ok"]) for v in t4.values()))

# ---- T1 : le comptage de physique, 4 genres lecture, contre portillon-de-poids.json
ref = json.load(open(ref_json, encoding="utf-8"))
GEN4 = ["code", "dialogue", "prose-en", "prose-fr"]


def t1(demi_vie):
    tot = {"defauts": 0, "acces": 0, "sous": np.zeros(6), "g2s": np.zeros(6), "g2t": 0.0}
    for cle in GEN4:
        ex, w, E = data[cle]
        df, _ = tiers.cache(ex, E, N, "lfu", demi_vie)
        tot["defauts"] += int(df.sum())
        tot["acces"] += df.size
        for i, e in enumerate(EPS):
            sp = tiers.sans_portage(df, w, e)
            tot["sous"][i] += sp["defauts_sous"]
            tot["g2s"][i] += sp["g2_defauts_sous"]
        tot["g2t"] += float((w ** 2).sum())
    part = tot["sous"] / tot["defauts"]
    en_rel = tot["g2s"] / tot["g2t"]
    ecarts = [abs(part[i] - ref["lignes"][i]["part_defauts"]) for i in range(6)]
    ecarts_e = [abs(en_rel[i] - ref["lignes"][i]["energie_g2_relative_au_tout_rapide"]) for i in range(6)]
    return {"defauts": tot["defauts"], "defauts_ref": ref["defauts"], "acces": tot["acces"],
            "part_defauts": part.tolist(), "energie_rel": en_rel.tolist(),
            "ecart_part_max": max(ecarts), "ecart_energie_max": max(ecarts_e)}


res["T1"] = t1(8.0)
res["T1_tient"] = bool(res["T1"]["defauts"] == ref["defauts"] and res["T1"]["ecart_part_max"] < 1e-3
                       and res["T1"]["ecart_energie_max"] < 1e-3)
print("T1", res["T1"], res["T1_tient"], flush=True)
res["T1_cassure_demi_vie_9"] = t1(9.0)
c = res["T1_cassure_demi_vie_9"]
res["T1_cassure_tombe"] = bool(c["defauts"] != ref["defauts"] or c["ecart_part_max"] > 1e-3
                               or c["ecart_energie_max"] > 1e-3)
print("T1 cassure", c, res["T1_cassure_tombe"], flush=True)

# ---- T0 : theta = 0 et theta > 1
t0 = {}
for cle in ("gen-prose-en", "gen-wiki"):
    ex, w, E = data[cle]
    df, sj_ = tiers.cache(ex, E, N, "lfu", 8.0)
    e0, b0, ts = tiers.regle(df, sj_, w, 0.0, "accepter", RHO)
    r0 = tiers.bilan(e0, b0, ts, w, df, RHO, tirages=10)
    e1, b1, ts = tiers.regle(df, sj_, w, 1.0001, "accepter", RHO)
    r1 = tiers.bilan(e1, b1, ts, w, df, RHO, tirages=10)
    t0[cle] = {"theta0_E": r0["E_rel"], "theta0_S": r0["S"],
               "theta1_Erel_moins_1": r1["E_rel"] - 1.0, "theta1_S_moins_(1-rho)": r1["S"] - (1 - RHO),
               "theta1_r_moins_1": r1["r"] - 1.0}
    print("T0", cle, t0[cle], flush=True)
res["T0"] = t0
res["T0_tient"] = bool(all(abs(v["theta0_E"]) == 0 and abs(v["theta0_S"]) == 0
                           and abs(v["theta1_Erel_moins_1"]) < 1e-12 and abs(v["theta1_S_moins_(1-rho)"]) < 1e-12
                           and abs(v["theta1_r_moins_1"]) < 1e-9 for v in t0.values()))
print("T0 tient", res["T0_tient"])
json.dump(res, open(os.path.join(sortie, "temoins.json"), "w", encoding="utf-8"), indent=1, default=float)
