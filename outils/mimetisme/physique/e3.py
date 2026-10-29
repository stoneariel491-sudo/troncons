"""E3 : admission par seuil de score (BYPASS) contre LFU ordinaire à capacité égale de pointe.
Seuil : mesures/mimetisme/physique/00-seuils-declares.md, section E3 (commit eee6925).
Usage : python -I -X utf8 e3.py <dossier_traces> <exe> <sortie>"""
import json, math, os, subprocess, sys
import numpy as np

dossier, exe, sortie = sys.argv[1:4]
os.makedirs(sortie, exist_ok=True)
GENRES = ["code", "dialogue", "prose-en", "prose-fr"]
TRACES = {"code": "t120b.code.lecture", "dialogue": "t120b.dialogue.lecture", "prose-en": "t120b.prose-en.lecture",
          "prose-fr": "t120b.prose-fr.lecture", "wiki-lecture": "w120b.wiki.lecture",
          "gen-prose-en": "t120b.prose-en.generation", "gen-wiki": "w120b.wiki.generation"}
HL = [2, 4, 8, 16, 32, 64, 128]
open(os.path.join(sortie, "noyaux.txt"), "w").write(
    "\n".join(f"exp_h{h}\t1:{h/math.log(2):.9g}" for h in HL) + "\n")
res = {}
for variante, N, byp in (("ordinaire327", 327, "0"), ("bypass323", 323, "1")):
    for melange in (False, True):
        for cle, base in TRACES.items():
            if melange and cle not in GENRES:
                continue
            f = os.path.join(sortie, f"{variante}-{cle}{'-melange' if melange else ''}.jsonl")
            cmd = [exe, os.path.join(dossier, base + ".trace"), os.path.join(dossier, base + ".poids"),
                   str(N), os.path.join(sortie, "noyaux.txt"), f] + (["20261027"] if melange else [])
            subprocess.run(cmd, check=True, env={**os.environ, "BYPASS": byp})
            res[(variante, cle, melange)] = {j["noyau"]: j for j in map(json.loads, open(f, encoding="utf-8"))}
        print("fait", variante, melange, flush=True)

def t(v, c, n, m=False):
    r = res[(v, c, m)][n]
    return r["hits"], r["total"]

def cv(v, m=False):
    H = T = 0
    par, ch = {}, {}
    for dehors in GENRES:
        autres = [g for g in GENRES if g != dehors]
        b = max((f"exp_h{h}" for h in HL), key=lambda n: np.mean([t(v, g, n, m)[0] / t(v, g, n, m)[1] for g in autres]))
        h_, t_ = t(v, dehors, b, m)
        H += h_; T += t_; par[dehors] = h_ / t_; ch[dehors] = b
    return H / T, par, ch

out = {}
for m in (False, True):
    a, pa, ca = cv("ordinaire327", m)
    b, pb, cb = cv("bypass323", m)
    out["melange" if m else "vrai"] = {"ordinaire327": {"pool": a, "par_genre": pa, "choix": ca},
                                      "bypass323": {"pool": b, "par_genre": pb, "choix": cb}, "gain": b - a}
reserv = {}
for c in ("wiki-lecture", "gen-prose-en", "gen-wiki"):
    bo = max((f"exp_h{h}" for h in HL), key=lambda n: np.mean([t("ordinaire327", g, n)[0] / t("ordinaire327", g, n)[1] for g in GENRES]))
    bb = max((f"exp_h{h}" for h in HL), key=lambda n: np.mean([t("bypass323", g, n)[0] / t("bypass323", g, n)[1] for g in GENRES]))
    reserv[c] = {"ordinaire": t("ordinaire327", c, bo)[0] / t("ordinaire327", c, bo)[1],
                 "bypass": t("bypass323", c, bb)[0] / t("bypass323", c, bb)[1], "reglages": [bo, bb]}
out["reservees"] = reserv
v = out["vrai"]
out["bilan"] = {"gain_pool": v["gain"],
                "genres_gagnes_sur_4": sum(1 for g in GENRES if v["bypass323"]["par_genre"][g] > v["ordinaire327"]["par_genre"][g]),
                "reservees_gagnees_sur_3": sum(1 for c in reserv if reserv[c]["bypass"] > reserv[c]["ordinaire"]),
                "gain_melange_W2": out["melange"]["gain"]}
out["bilan"]["passe_seuil"] = bool(out["bilan"]["gain_pool"] >= 0.015 and out["bilan"]["genres_gagnes_sur_4"] >= 3
                                   and out["bilan"]["reservees_gagnees_sur_3"] >= 2)
json.dump(out, open(os.path.join(sortie, "E3-bilan.json"), "w", encoding="utf-8"), indent=1)
print(json.dumps(out["bilan"], indent=1))
print({k: round(x, 4) for k, x in v["ordinaire327"]["par_genre"].items()}, round(v["ordinaire327"]["pool"], 4))
print({k: round(x, 4) for k, x in v["bypass323"]["par_genre"].items()}, round(v["bypass323"]["pool"], 4))
