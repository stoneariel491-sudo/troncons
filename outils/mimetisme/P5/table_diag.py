"""Addendum 2 : cible diagonale de l'amortissement. Erreur d'evaluation (Babai, CD) rapportee a Babai iso delta = 1."""
import csv, glob, json, os
import numpy as np
ICI = os.path.dirname(os.path.abspath(__file__))
ET1 = os.path.join(ICI, "..", "..", "..", "mesures", "mimetisme", "P5", "etape1")
DG = os.path.join(ICI, "..", "..", "..", "mesures", "mimetisme", "P5", "etape1-diag")
base = {}
for f in glob.glob(os.path.join(ET1, "L??-E??-d1.json")):
    j = json.load(open(f, encoding="utf-8"))
    for r in j["lignes_res"]:
        if r["methode"] == "babai" and r["lam"] == 0.0:
            base[(j["couche"], j["expert"])] = r
data = {}
for f in glob.glob(os.path.join(DG, "*-L??-E??-d*.json")):
    j = json.load(open(f, encoding="utf-8"))
    for r in j["lignes_res"]:
        if r["lam"] == 0.0 and r["methode"] in ("babai", "cd"):
            data.setdefault((j["cible"], j["damp"], r["methode"]), {})[(j["couche"], j["expert"])] = r
lignes = []
for (cible, d, meth), par in sorted(data.items()):
    gains, dR, gc = [], [], []
    for k, r in par.items():
        b = base[k]
        gains.append(1 - r["err_eval"] / b["err_eval"]); dR.append(r["bits_H0"] - b["bits_H0"]); gc.append(1 - r["err_calib"] / b["err_calib"])
    ok = [abs(x) <= 0.005 for x in dR]
    lignes.append(dict(cible=cible, damp=d, methode=meth, n=len(gains), gain_eval_median=float(np.median(gains)), gain_eval_moyenne=float(np.mean(gains)),
                       nb_ge_10=int(sum(g >= 0.10 for g in gains)), nb_comparables=int(sum(ok)), dR_moyen=float(np.mean(dR)), gain_calib_median=float(np.median(gc))))
with open(os.path.join(DG, "table-diag.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(lignes[0].keys())); w.writeheader(); w.writerows(lignes)
for l in lignes:
    print("%-9s d=%-4s %-5s n=%d gain eval median %+.1f%% moy %+.1f%%  >=10%%: %d  comparables(+-0.005): %d  dR %+.4f  calib %+.1f%%" % (
        l["cible"], l["damp"], l["methode"], l["n"], 100 * l["gain_eval_median"], 100 * l["gain_eval_moyenne"], l["nb_ge_10"], l["nb_comparables"], l["dR_moyen"], 100 * l["gain_calib_median"]))
