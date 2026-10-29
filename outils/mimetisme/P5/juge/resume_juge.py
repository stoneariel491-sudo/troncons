"""P5 juge : agrège les journaux de juge_p5.py et les compare aux chiffres de P5 (gains-d1.csv, table-regime.csv).
  python -I -X utf8 resume_juge.py > mesures/mimetisme/P5/juge/resume.json
"""
import csv
import glob
import json
import os
import statistics as st

ICI = os.path.dirname(os.path.abspath(__file__))
M = os.path.join(ICI, "..", "..", "..", "..", "mesures", "mimetisme", "P5")
J = os.path.join(M, "juge")
INST = [(l, e) for l in (0, 8, 16, 23) for e in (0, 16)]


def lire(chemin):
    try:
        with open(chemin, encoding="utf8") as f:
            return json.load(f)
    except Exception:
        return None


def tag(l, e):
    return f"L{l:02d}-E{e:02d}"


def serie(fmt):
    out = {}
    for l, e in INST:
        d = lire(os.path.join(J, fmt.format(t=tag(l, e))))
        if d:
            out[tag(l, e)] = d
    return out


def stats(gains):
    g = list(gains.values())
    if not g:
        return None
    return dict(n=len(g), mediane=st.median(g), moyenne=st.mean(g), min=min(g), max=max(g),
                au_dessus_10=sum(x >= 0.10 for x in g), negatifs=sum(x < 0 for x in g))


def main():
    p5 = {}
    with open(os.path.join(M, "etape1", "gains-d1.csv"), encoding="utf8") as f:
        for r in csv.DictReader(f):
            if r["methode"] == "cd" and float(r["lam"]) == 0.0:
                p5[tag(int(r["couche"]), int(r["expert"]))] = dict(gain=float(r["gain_eval"]),
                                                                   err_babai=float(r["err_eval_babai"]),
                                                                   err_cd=float(r["err_eval"]))
    reg = {}
    with open(os.path.join(M, "etape1-regime", "table-regime.csv"), encoding="utf8") as f:
        for r in csv.DictReader(f):
            reg[tag(int(r["couche"]), int(r["expert"]))] = r
    j1, j2 = serie("j1/{t}-g1.json"), serie("j2/{t}-g2026.json")
    lam = serie("lam02/{t}-g1.json")
    zero, perm = serie("temoins/zero-{t}.json"), serie("temoins/perm-{t}.json")
    t2, pl, inc = serie("j3/test2-{t}.json"), serie("j3/plus-{t}.json"), serie("j3/inclus-{t}.json")
    demi = serie("j5/demi-{t}.json")
    out = dict(outil="resume_juge.py")
    lignes = {}
    for k, d in j1.items():
        ref = p5.get(k, {})
        lignes[k] = dict(N=d["n_train"], gain_juge=d["gain_test"], gain_P5=ref.get("gain"),
                         ecart_points=None if ref.get("gain") is None else 100 * (d["gain_test"] - ref["gain"]),
                         err_babai_rel=None if not ref else abs(d["res"]["babai"]["err_test"] / ref["err_babai"] - 1),
                         err_cd_rel=None if not ref else abs(d["res"]["cd"]["err_test"] / ref["err_cd"] - 1),
                         j0_symboles_differents=d.get("j0_symboles_differents"), j0_quant=d.get("j0_quant_identique"),
                         second_chemin_x=abs(d["res"]["cd"]["err_test_x"] / d["res"]["cd"]["err_test"] - 1),
                         dh0=d["dh0"], gain_calib=d["gain_calib"])
    out["J1_par_instance"] = lignes
    out["J1"] = stats({k: d["gain_test"] for k, d in j1.items()})
    out["J1_P5_cd_lam0"] = stats({k: v["gain"] for k, v in p5.items()})
    out["J1_calib"] = stats({k: d["gain_calib"] for k, d in j1.items()})
    out["J2_graine2026"] = stats({k: d["gain_test"] for k, d in j2.items()})
    out["J2_par_instance"] = {k: d["gain_test"] for k, d in j2.items()}
    out["lam02"] = stats({k: d["gain_test"] for k, d in lam.items()})
    out["lam02_dh0"] = {k: d["dh0"] for k, d in lam.items()}
    # chiffre de P5 : meilleur des deux lambda de CD, chacun contre Babai lambda = 0, paire comptee si |dH0| <= 0,005
    best = {}
    for k in j1:
        if k in lam:
            rb = j1[k]["res"]["babai"]
            c = [1 - d["res"]["cd"]["err_test"] / rb["err_test"] for d in (j1[k], lam[k])
                 if abs(d["res"]["cd"]["h0"] - rb["h0"]) <= 0.005]
            if c:
                best[k] = max(c)
    out["meilleur_des_deux_lam_contre_babai_lam0"] = stats(best)
    out["meilleur_des_deux_par_instance"] = best
    out["dh0_cd_lam02_contre_babai_lam0"] = {k: lam[k]["res"]["cd"]["h0"] - j1[k]["res"]["babai"]["h0"] for k in j1 if k in lam}
    out["T1_zero_ecart_max"] = max([abs(d["gain_test"]) for d in zero.values()], default=None)
    out["T2_perm"] = stats({k: d["gain_test"] for k, d in perm.items()})
    out["T3_inclus"] = stats({k: d["gain_test"] for k, d in inc.items()})
    j3 = {}
    for k in t2:
        if k in pl:
            bt2 = t2[k]["res"]["babai"]["err_test"]
            j3[k] = dict(gain_test2=t2[k]["gain_test"], gain_plus=pl[k]["gain_test"],
                         montee_points=100 * (pl[k]["gain_test"] - t2[k]["gain_test"]),
                         cd_plus_sur_babai_test2=pl[k]["res"]["cd"]["err_test"] / bt2,
                         babai_plus_sur_babai_test2=pl[k]["res"]["babai"]["err_test"] / bt2,
                         P5_cd_plus_sur_babai_test2=float(reg[k]["err_test_CD_plus_sur_Babai_test2"]) if k in reg else None,
                         N_test2=t2[k]["n_train"], N_plus=pl[k]["n_train"], dh0_plus=pl[k]["dh0"])
    out["J3_par_instance"] = j3
    if j3:
        out["J3"] = dict(mediane_test2=st.median([v["gain_test2"] for v in j3.values()]),
                         mediane_plus=st.median([v["gain_plus"] for v in j3.values()]),
                         montee_mediane_points=st.median([v["montee_points"] for v in j3.values()]),
                         montee_des_medianes_points=100 * (st.median([v["gain_plus"] for v in j3.values()])
                                                          - st.median([v["gain_test2"] for v in j3.values()])),
                         en_hausse=sum(v["montee_points"] > 0 for v in j3.values()),
                         moyenne_cd_plus_sur_babai_test2=st.mean([v["cd_plus_sur_babai_test2"] for v in j3.values()]),
                         moyenne_babai_plus_sur_babai_test2=st.mean([v["babai_plus_sur_babai_test2"] for v in j3.values()]))
    j5 = {}
    for k in demi:
        if k in j1:
            j5[k] = dict(N_base=j1[k]["n_train"], N_demi=demi[k]["n_train"], gain_base=j1[k]["gain_test"],
                         gain_demi=demi[k]["gain_test"], baisse_points=100 * (j1[k]["gain_test"] - demi[k]["gain_test"]),
                         babai_demi_sur_babai_base=demi[k]["res"]["babai"]["err_test"] / j1[k]["res"]["babai"]["err_test"],
                         cd_demi_sur_babai_base=demi[k]["res"]["cd"]["err_test"] / j1[k]["res"]["babai"]["err_test"])
    out["J5_par_instance"] = j5
    if j5:
        out["J5"] = dict(mediane_base=st.median([v["gain_base"] for v in j5.values()]),
                         mediane_demi=st.median([v["gain_demi"] for v in j5.values()]),
                         baisse_des_medianes_points=100 * (st.median([v["gain_base"] for v in j5.values()])
                                                          - st.median([v["gain_demi"] for v in j5.values()])),
                         en_baisse=sum(v["baisse_points"] > 0 for v in j5.values()),
                         mediane_babai_demi_sur_base=st.median([v["babai_demi_sur_babai_base"] for v in j5.values()]))
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
