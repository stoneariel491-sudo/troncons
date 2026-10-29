"""P5 : l'erreur d'evaluation de chaque methode a chaque amortissement, rapportee a Babai deploye (delta = 1, lam = 0).
Ecrit mesures/mimetisme/P5/etape1/table-delta.csv ; affiche la table (moyenne et mediane sur les 8 instances)."""
import csv, glob, json, os, re
import numpy as np
ICI = os.path.dirname(os.path.abspath(__file__))
ET1 = os.path.join(ICI, "..", "..", "..", "mesures", "mimetisme", "P5", "etape1")
data = {}
for f in glob.glob(os.path.join(ET1, "L??-E??-d*.json")):
    j = json.load(open(f, encoding="utf-8"))
    for r in j["lignes_res"]:
        data[(j["couche"], j["expert"], j["damp"], r["methode"], r["lam"])] = r
inst = sorted({(k[0], k[1]) for k in data})
deltas = sorted({k[2] for k in data})
lignes = []
for d in deltas:
    for meth in ("babai", "cd", "pt"):
        for lam in (0.0, 0.2):
            rel, rate = [], []
            for (l, e) in inst:
                b1 = data.get((l, e, 1.0, "babai", 0.0))
                r = data.get((l, e, d, meth, lam))
                if b1 and r:
                    rel.append(r["err_eval"] / b1["err_eval"]); rate.append(r["bits_H0"] - b1["bits_H0"])
            if rel:
                lignes.append(dict(damp=d, methode=meth, lam=lam, n=len(rel), eval_sur_babai_d1_moyenne=float(np.mean(rel)),
                                   eval_sur_babai_d1_mediane=float(np.median(rel)), eval_sur_babai_d1_min=float(np.min(rel)),
                                   dR_moyen=float(np.mean(rate))))
with open(os.path.join(ET1, "table-delta.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(lignes[0].keys())); w.writeheader(); w.writerows(lignes)
for l in lignes:
    print("d=%-4s %-6s lam=%-3s n=%d  eval/Babai(d=1): moy %.4f med %.4f min %.4f   dR=%+.4f" % (l["damp"], l["methode"], l["lam"], l["n"], l["eval_sur_babai_d1_moyenne"], l["eval_sur_babai_d1_mediane"], l["eval_sur_babai_d1_min"], l["dR_moyen"]))
