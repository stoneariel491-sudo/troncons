"""Piste spectres : les chiffres du livrable, lus dans les journaux commités (rien de mémoire).

Lit `ajustements.out`, `second-chemin.out`, `levier.out`, `levier-temoin.out`, `temoins*.out`,
`puissance-critere.out` ; écrit `rapport.json` (tous les chiffres cités par spectres.md) et les CSV
des figures (`fig-ccdf.csv`, `fig-alpha.csv`, `fig-levier.csv`).

Utilisation : python -X utf8 rapport.py
"""
from __future__ import annotations

import commun

import csv
import json
import math
import os

import numpy as np

M = commun.MESURES


def lire_csv(nom):
    with open(os.path.join(M, nom), encoding="utf8") as f:
        return list(csv.DictReader(f))


def famille(role: str) -> str:
    return "attention" if role.startswith("attn") else role


def vrai(x) -> bool:
    return str(x) == "True"


def main() -> None:
    commun.priorite_basse()
    aj = lire_csv("ajustements.out")
    sortie: dict = {"n_matrices": len(aj)}

    # --- verdicts ---
    fams = ["gate", "up", "down", "attention"]
    dec = {}
    for f in fams + ["tout"]:
        lignes = [l for l in aj if f == "tout" or famille(l["role"]) == f]
        dec[f] = {
            "n": len(lignes),
            "loi_de_puissance": sum(l["verdict"] == "loi de puissance" for l in lignes),
            "non_departagee": sum(l["verdict"] == "non départagée" for l in lignes),
            "autre_loi": sum(l["verdict"] == "autre loi préférée" for l in lignes),
            "strict": sum(vrai(l["verdict_strict"]) for l in lignes),
            "compatible": sum(vrai(l["compatible"]) for l in lignes),
            "exp_ecartee": sum(float(l["R_exp"]) > 0 and float(l["p_exp"]) < 0.05 for l in lignes),
            "lognormale_preferee": sum(float(l["R_lognormale"]) < 0 and float(l["p_lognormale"]) < 0.05 for l in lignes),
            "p_gof_ge_0_1": sum(float(l["p_gof"]) >= 0.1 for l in lignes),
            "perm_compatible": sum(vrai(l["perm_compatible"]) for l in lignes),
            "perm_loi_de_puissance": sum(l["perm_verdict"] == "loi de puissance" for l in lignes),
        }
    sortie["verdicts"] = dec
    sortie["gpt_oss_loi_de_puissance"] = dec["tout"]["loi_de_puissance"] >= 32
    sortie["gpt_oss_compatible"] = dec["tout"]["compatible"] >= 32

    # --- α par rôle et par couche ---
    alpha = {}
    for f in fams:
        for c in commun.COUCHES:
            ls = [l for l in aj if famille(l["role"]) == f and int(l["couche"]) == c]
            if not ls:
                continue
            a = np.array([float(l["alpha"]) for l in ls])
            ap = np.array([float(l["perm_alpha"]) for l in ls])
            nq = np.array([int(l["n_queue"]) for l in ls])
            alpha[f"{f}/L{c}"] = {
                "ids": [l["id"] for l in ls], "alpha": a.round(3).tolist(),
                "alpha_mediane": float(np.median(a)), "n_queue": nq.tolist(),
                "alpha_perm_mediane": float(np.median(ap)),
                "compatible": [vrai(l["compatible"]) for l in ls],
                "part5": float(np.median([float(l["part_energie_5pc"]) for l in ls])),
                "part5_perm": float(np.median([float(l["part_energie_5pc_perm"]) for l in ls])),
            }
    sortie["alpha"] = alpha
    with open(os.path.join(M, "fig-alpha.csv"), "w", encoding="utf8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["id", "famille", "couche", "x", "alpha", "alpha_err", "n_queue", "compatible", "perm_alpha"])
        xs = {"gate": 0, "up": 1, "down": 2, "attention": 3}
        for l in aj:
            fa = famille(l["role"])
            x = xs[fa] * 4 + commun.COUCHES.index(int(l["couche"])) * 1.0 + 0.5
            w.writerow([l["id"], fa, l["couche"], x, l["alpha"], l["alpha_err"], l["n_queue"],
                        int(vrai(l["compatible"])), l["perm_alpha"]])

    # --- second chemin ---
    sc = {l["id"]: l for l in lire_csv("second-chemin-v2.out")}
    da = [abs(float(sc[l["id"]]["alpha2"]) - float(l["alpha"])) for l in aj]
    sortie["second_chemin"] = {
        "sha_egaux": sum(vrai(sc[l["id"]]["sha_egal"]) for l in aj),
        "ecart_rel_max_queue": max(float(sc[l["id"]]["ecart_rel_max_queue"]) for l in aj),
        "verdicts_egaux": sum(sc[l["id"]]["verdict2"] == l["verdict"] for l in aj),
        "compatibles_egaux": sum(sc[l["id"]]["compatible2"] == l["compatible"] for l in aj),
        "compatible2_total": sum(vrai(sc[l["id"]]["compatible2"]) for l in aj),
        "loi2_total": sum(sc[l["id"]]["verdict2"] == "loi de puissance" for l in aj),
        "alpha_ecart_max": max(da),
        "xmin_egaux": sum(math.isclose(float(sc[l["id"]]["x_min2"]), float(l["x_min"]), rel_tol=1e-6) for l in aj),
        "differences": [l["id"] for l in aj if sc[l["id"]]["compatible2"] != l["compatible"]
                        or sc[l["id"]]["verdict2"] != l["verdict"]],
    }

    # --- CCDF pour la figure : un représentant par famille (couche 12), son permuté, MP ---
    vs = np.load(os.path.join(M, "valeurs-singulieres.npz"))
    choix = [l["id"] for l in aj if int(l["couche"]) == 12 and l["role"] in ("gate", "up", "down")][::4]
    choix += ["L12.attn_q"]
    with open(os.path.join(M, "fig-ccdf.csv"), "w", encoding="utf8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["serie", "lambda_norm", "ccdf"])
        series = {i: vs[f"reel/{i}"] for i in choix}
        series.update({i + ".perm": vs[f"perm/{i}"] for i in choix})
        series["MP_2880x2880"] = vs["mp/2880x2880"]
        series["Pareto_2_5"] = vs["pareto"]
        for nom, s in series.items():
            lam = np.sort(s ** 2)[::-1]
            lam = lam / lam.mean()
            n = lam.size
            # points espacés en log du rang (figure légère, valeurs exactes)
            rangs = np.unique(np.round(np.logspace(0, math.log10(n), 120)).astype(int)) - 1
            with open(os.path.join(M, f"fig-ccdf-{nom}.csv"), "w", encoding="utf8", newline="") as g:
                wg = csv.writer(g, lineterminator="\n")
                wg.writerow(["lambda_norm", "ccdf"])
                for k in rangs:
                    w.writerow([nom, f"{lam[k]:.6g}", f"{(k + 1) / n:.6g}"])
                    wg.writerow([f"{lam[k]:.6g}", f"{(k + 1) / n:.6g}"])
    sortie["ccdf_series"] = choix

    # --- levier ---
    nom_levier = os.environ.get("LEVIER", "levier-v3.out")
    if not os.path.exists(os.path.join(M, nom_levier)):
        finir(sortie)
        return
    lv = lire_csv(nom_levier)
    rangs = (1, 2, 4, 8, 16, 32, 64)
    par = {l["id"]: l for l in lv}

    def meilleur(l, cle):
        v = [float(l[f"{cle}_{r}"]) for r in rangs]
        if any(math.isnan(x) for x in v):
            return float("nan"), None
        k = int(np.argmax(v))
        return v[k], rangs[k]

    lev = {}
    for f in fams:
        ids = [l["id"] for l in aj if famille(l["role"]) == f]
        bloc = {}
        for cle in ("L1", "L2", "L3d", "L3dr"):
            reel = [meilleur(par[i], cle) for i in ids]
            if cle == "L1":
                tem = [meilleur(par[i + ".blocs"], cle) for i in ids if i + ".blocs" in par]
            else:
                tem = [meilleur(par[i + ".perm"], cle) for i in ids]
            g = [x for x, _ in reel if not math.isnan(x)]
            gt = [x for x, _ in tem if not math.isnan(x)]
            if not g:
                continue
            med, medt = float(np.median(g)), float(np.median(gt))
            bloc[cle] = {"gain_net_median": med, "gain_net_min": float(min(g)), "gain_net_max": float(max(g)),
                         "rang_median": float(np.median([r for _, r in reel])),
                         "temoin_median": medt,
                         "levier": bool(med > 0.05 and medt < med / 4)}
        lev[f] = bloc
    sortie["levier"] = lev
    for l in lv:
        if l["id"].startswith("L") and "." in l["id"]:
            pass
    sortie["levier_L3d_0_median"] = {f: float(np.median([float(par[i]["L3d_0"]) for i in
                                                         [l["id"] for l in aj if famille(l["role"]) == f]]))
                                    for f in fams}
    sortie["levier_L2_0_median"] = {f: float(np.median([float(par[i]["L2_0"]) for i in
                                                         [l["id"] for l in aj if famille(l["role"]) == f]]))
                                    for f in fams}
    entete_lv = ["id", "famille", "rang", "L1", "L2", "L3d", "L1_temoin", "L2_temoin", "L3d_temoin"]
    par_fam = {f: [] for f in fams}
    with open(os.path.join(M, "fig-levier.csv"), "w", encoding="utf8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(entete_lv)
        for i in [l["id"] for l in aj]:
            fa = famille(next(l["role"] for l in aj if l["id"] == i))
            for r in rangs:
                b = par.get(i + ".blocs")
                lig = [i, fa, r, par[i][f"L1_{r}"], par[i][f"L2_{r}"], par[i][f"L3d_{r}"],
                       b[f"L1_{r}"] if b else "nan", par[i + ".perm"][f"L2_{r}"], par[i + ".perm"][f"L3d_{r}"]]
                w.writerow(lig)
                par_fam[fa].append(lig)
    for fa, lignes in par_fam.items():
        with open(os.path.join(M, f"fig-levier-{fa}.csv"), "w", encoding="utf8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(entete_lv)
            w.writerows(lignes)
    try:
        sortie["levier_temoin_plante"] = {l["id"]: dict(l) for l in lire_csv("levier-temoin-v3.out")}
    except FileNotFoundError:
        pass
    finir(sortie)


def finir(sortie: dict) -> None:

    # --- plafond spectral (seuil.md § 7 quinquies à septies) : les journaux, lus tels quels ---
    for nom in ("plafond", "plafond-casse", "plafond-rang", "plafond-rang-casse"):
        try:
            with open(os.path.join(M, f"{nom}.log"), encoding="utf8") as f:
                sortie[f"journal_{nom}"] = f.read().splitlines()
        except FileNotFoundError:
            pass
    try:
        pl = lire_csv("plafond.out")
        sortie["plafond_G"] = {l["id"]: float(l["G_0.044"]) for l in pl}
    except FileNotFoundError:
        pass

    # --- témoins et puissance ---
    for nom in ("temoins", "temoins-casse", "puissance-critere"):
        try:
            with open(os.path.join(M, f"{nom}.out"), encoding="utf8") as f:
                sortie[nom] = json.load(f)
        except FileNotFoundError:
            pass
    # témoins sous le verdict amendé (seuil.md § 4 bis), lus dans les journaux des témoins
    from puissance_critere import compatible
    amendes = {}
    for nom in ("temoins", "temoins-casse"):
        if nom not in sortie:
            continue
        lignes = {}
        for t, r in sortie[nom]["temoins"].items():
            c = compatible(r)
            if t == "T-Pareto":
                ok = c and 2.3 <= r["alpha"] <= 2.7
            elif t == "T-lognormale":
                ok = None                     # rapporté sans attente
            else:
                ok = not c
            lignes[t] = {"compatible": c, "alpha": r["alpha"],
                         "resultat": "rapporté" if ok is None else ("TIENT" if ok else "ÉCHEC")}
        amendes[nom] = lignes
    sortie["temoins_amendes"] = amendes
    with open(os.path.join(M, "rapport.json"), "w", encoding="utf8") as f:
        json.dump(sortie, f, indent=1, ensure_ascii=False)
    print(json.dumps({k: sortie.get(k) for k in ("verdicts", "gpt_oss_loi_de_puissance", "gpt_oss_compatible",
                                                 "second_chemin", "temoins_amendes", "levier")},
                     indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
