"""P5 etape 1 : agrege les journaux mesures/mimetisme/P5/etape1/L??-E??-d<delta>.json, applique la regle declaree
(mesures/mimetisme/P5/00-seuil-declare.md + addendum) et ecrit un CSV et un verdict.

  python -I -X utf8 agreger_etape1.py [delta ...]      (defaut : 1)
"""
import csv
import glob
import json
import os
import sys

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
DOSSIER = os.path.join(ICI, "..", "..", "..", "mesures", "mimetisme", "P5", "etape1")
TOL = 0.005


def charger(delta):
    out = []
    for f in sorted(glob.glob(os.path.join(DOSSIER, f"L??-E??-d{delta}.json"))):
        out.append(json.load(open(f, encoding="utf-8")))
    return out


def gains(inst):
    lig = inst["lignes_res"]
    bab = [r for r in lig if r["methode"] == "babai" and r["lam"] == 0.0][0]
    res = []
    for r in lig:
        if r["methode"] not in ("cd", "pt"):
            continue
        dR = r["bits_H0"] - bab["bits_H0"]
        res.append(dict(couche=inst["couche"], expert=inst["expert"], damp=inst["damp"], methode=r["methode"], lam=r["lam"],
                        dR=dR, comparable=bool(abs(dR) <= TOL),
                        gain_train=1 - r["err_train"] / bab["err_train"], gain_calib=1 - r["err_calib"] / bab["err_calib"],
                        gain_eval=1 - r["err_eval"] / bab["err_eval"], gain_eval_x=1 - r["err_eval_x"] / bab["err_eval_x"],
                        err_eval=r["err_eval"], err_eval_babai=bab["err_eval"],
                        ecart_second_chemin=abs(r["err_eval"] - r["err_eval_x"]) / r["err_eval"]))
    return res


def principal(lignes, methode):
    """Meilleur des points lambda a debit egal, par instance."""
    par = {}
    for g in lignes:
        if g["methode"] != methode or not g["comparable"]:
            continue
        k = (g["couche"], g["expert"])
        if k not in par or g["gain_eval"] > par[k]["gain_eval"]:
            par[k] = g
    return par


def main():
    deltas = sys.argv[1:] or ["1"]
    sortie = []
    for d in deltas:
        insts = charger(d)
        tout = [g for inst in insts for g in gains(inst)]
        with open(os.path.join(DOSSIER, f"gains-d{d}.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(tout[0].keys()))
            w.writeheader()
            w.writerows(tout)
        r = dict(damp=d, instances=len(insts))
        for m in ("cd", "pt"):
            p = principal(tout, m)
            ge = [v["gain_eval"] for v in p.values()]
            r[m] = dict(n_comparables=len(ge), gain_eval_par_instance={f"L{k[0]}E{k[1]}": round(v["gain_eval"], 4) for k, v in p.items()},
                        gain_eval_median=float(np.median(ge)) if ge else None, gain_eval_moyenne=float(np.mean(ge)) if ge else None,
                        nb_ge_10pct=int(sum(g >= 0.10 for g in ge)), nb_negatifs=int(sum(g < 0 for g in ge)),
                        gain_calib_median=float(np.median([v["gain_calib"] for v in p.values()])) if p else None,
                        gain_train_median=float(np.median([v["gain_train"] for v in p.values()])) if p else None,
                        ecart_second_chemin_max=float(max(v["ecart_second_chemin"] for v in p.values())) if p else None,
                        dR_max=float(max(abs(v["dR"]) for v in p.values())) if p else None)
            if ge:
                n = len(insts)
                if np.median(ge) < 0.03 or sum(g < 0 for g in ge) >= 4:
                    r[m]["verdict_etape1"] = "MORT"
                elif sum(g >= 0.10 for g in ge) >= 6:
                    r[m]["verdict_etape1"] = "AUTORISE L'ETAPE 2"
                else:
                    r[m]["verdict_etape1"] = "OUVERT"
        sortie.append(r)
    print(json.dumps(sortie, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
