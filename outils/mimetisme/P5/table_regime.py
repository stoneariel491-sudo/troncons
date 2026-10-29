"""Addendum 3 : variation de N. Gain de CD contre Babai du meme regime, sur le test, par instance."""
import csv, glob, json, os
import numpy as np
ICI = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(ICI, "..", "..", "..", "mesures", "mimetisme", "P5", "etape1-regime")
res = {}
for f in glob.glob(os.path.join(D, "*-L??-E??.json")):
    j = json.load(open(f, encoding="utf-8"))
    L = {r["methode"]: r for r in j["lignes_res"] if r["lam"] == 0.0}
    res[(j["regime"], j["couche"], j["expert"])] = dict(n_calib=j["n_calib"], n_eval=j["n_eval"], b=L["babai"], c=L["cd"])
regs = ["test2", "plus", "inclus"]
inst = sorted({(k[1], k[2]) for k in res})
out = []
for k in inst:
    row = dict(couche=k[0], expert=k[1])
    for r in regs:
        v = res.get((r,) + k)
        if v:
            row[f"N_{r}"] = v["n_calib"]
            row[f"gain_test_{r}"] = 1 - v["c"]["err_eval"] / v["b"]["err_eval"]
            row[f"gain_calib_{r}"] = 1 - v["c"]["err_calib"] / v["b"]["err_calib"]
            row[f"dR_{r}"] = v["c"]["bits_H0"] - v["b"]["bits_H0"]
    if "test2" in regs and (("test2",) + k) in res and (("plus",) + k) in res:
        row["err_test_Babai_plus_sur_Babai_test2"] = res[("plus",) + k]["b"]["err_eval"] / res[("test2",) + k]["b"]["err_eval"]
        row["err_test_CD_plus_sur_Babai_test2"] = res[("plus",) + k]["c"]["err_eval"] / res[("test2",) + k]["b"]["err_eval"]
        row["err_test_CD_test2_sur_Babai_test2"] = res[("test2",) + k]["c"]["err_eval"] / res[("test2",) + k]["b"]["err_eval"]
    out.append(row)
with open(os.path.join(D, "table-regime.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=sorted({c for r in out for c in r}, key=lambda c: (c not in ("couche", "expert"), c))); w.writeheader(); w.writerows(out)
for r in regs:
    g = [x[f"gain_test_{r}"] for x in out if f"gain_test_{r}" in x]
    gc = [x[f"gain_calib_{r}"] for x in out if f"gain_calib_{r}" in x]
    if g:
        print("%-7s n=%d  gain test CD/Babai: median %+.1f%% moyenne %+.1f%% | gain calib median %+.1f%% | N moyen %.0f | dR max %.4f" % (
            r, len(g), 100 * np.median(g), 100 * np.mean(g), 100 * np.median(gc), np.mean([x[f"N_{r}"] for x in out if f"N_{r}" in x]), max(abs(x[f"dR_{r}"]) for x in out if f"dR_{r}" in x)))
pairs = [(x["gain_test_test2"], x["gain_test_plus"]) for x in out if "gain_test_plus" in x and "gain_test_test2" in x]
if pairs:
    d = [b - a for a, b in pairs]
    print("montee test2 -> plus : median %+.1f points, instances en hausse %d/%d" % (100 * np.median(d), sum(x > 0 for x in d), len(d)))
for c in ("err_test_Babai_plus_sur_Babai_test2", "err_test_CD_plus_sur_Babai_test2", "err_test_CD_test2_sur_Babai_test2"):
    v = [x[c] for x in out if c in x]
    if v: print(c, "moyenne %.4f mediane %.4f" % (np.mean(v), np.median(v)))
