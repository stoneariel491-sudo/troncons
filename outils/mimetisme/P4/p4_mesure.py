"""P4 : mesure par session (calibration fendue, bras P et R, simulateur, second chemin, cassure).

Usage : python -I -X utf8 p4_mesure.py <dossier_traces> <temoins.json> <N_7pct> <N_20pct> <sortie.json> [d,d,...]
Les paramètres du simulateur (fenêtre w_total, surcoût o par couche) viennent du JSON des témoins (étalonnés sur le
120b, 7 %, pas sur les sessions mesurées ici).
"""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p4  # noqa: E402

TR = 4.1
_MEMO = {}


def _predire(nom, J, E, d, alea=False):
    cle = (nom, d, alea)
    if cle not in _MEMO:
        _MEMO[cle] = p4.predire(J, E, d, aleatoire=alea)
    return _MEMO[cle]


def session(nom, J, E, N, d, par, w_layer_ms, complet=True):
    T, L, k = J.shape
    half = T // 2
    ng = T * L
    vide = [[] for _ in range(ng)]
    pred, conf = _predire(nom, J, E, d)
    lab = p4.etiquettes(J, pred)
    faults, present = p4.passe_cache(J, E, N, d, pred, conf)
    valid = pred >= 0
    cal = np.zeros(pred.shape, dtype=bool)
    cal[:half] = True
    tst = np.zeros(pred.shape, dtype=bool)
    tst[half:] = True
    r = {"session": nom, "N": N, "d": d, "T": T, "L": L, "half": half}

    # ---- calibration du bras P (candidats absents du cache)
    selP = cal & valid & ~present
    thP, crb = p4.calibrer(conf[selP], lab[selP])
    r["thP"] = thP
    r["courbeP_cal"] = crb
    # ---- calibration du bras R (candidats déjà présents)
    selR = cal & valid & present
    thR, crbR = p4.calibrer(conf[selR], lab[selR])
    r["thR"] = thR
    r["courbeR_cal"] = crbR

    # ---- courbe de test (précision et couverture par seuil), pour la figure
    Ftest = int(sum(len(faults[g]) for g in range(half * L, ng)))
    r["F_test_base"] = Ftest
    courbe = []
    for th in p4.GRILLE:
        s = tst & valid & ~present & (conf >= th - 1e-9)
        n = int(s.sum())
        x = int(lab[s].sum())
        sc = cal & valid & ~present & (conf >= th - 1e-9)
        nc = int(sc.sum())
        xc = int(lab[sc].sum())
        courbe.append({"theta": float(th), "n_test": n, "x_test": x, "n_cal": nc, "x_cal": xc})
    r["courbe"] = courbe

    base = p4.des(J, E, d, faults, vide, par, "prio")
    tb = float(base["tok"][half:].sum())
    r["t_base_test_ms"] = tb
    r["ms_par_jeton_base"] = tb / (T - half)
    r["defauts_par_jeton_base"] = Ftest / (T - half)
    r["succes_cache_test"] = 1.0 - Ftest / ((T - half) * L * k)

    # ---- bras P
    if thP is None:
        r["P"] = {"charges": 0, "justes": 0, "gain": 0.0, "octets_plus": 0.0, "note": "aucun seuil ne tient : pas de préchargement"}
    else:
        charges, just = p4.construire_charges(J, E, d, pred, conf, present, thP, half)
        C = int(sum(len(charges[g]) for g in range(half * L, ng)))
        U = int(just[half * L:].sum())
        arm = p4.des(J, E, d, faults, charges, par, "prio")
        ta = float(arm["tok"][half:].sum())
        dem = int(arm["dem"][half * L:].sum())
        bgn = int(arm["bg"][half * L:].sum())
        armp = p4.des(J, E, d, faults, charges, par, "prio", purge_totale=True)
        tp = float(armp["tok"][half:].sum())
        armf = p4.des(J, E, d, faults, charges, par, "fifo")
        tf = float(armf["tok"][half:].sum())
        omega_tot = par["w_total"] * (T - half)
        saved = min(U * TR, (U / C if C else 0) * min(C * TR, omega_tot)) if C else 0.0
        ferme = saved / (tb - saved)
        p_real = U / C if C else None
        f = par["w_total"] / 460.0
        part_disque = Ftest * TR / tb
        r["P"] = {
            "charges": C, "justes": U, "precision_test": p_real, "couverture": U / Ftest if Ftest else None,
            "gain": tb / ta - 1.0, "gain_purge_totale": tb / tp - 1.0, "gain_fifo_meme_charges": tb / tf - 1.0,
            "octets_plus": (dem + bgn) / Ftest - 1.0 if Ftest else None,
            "lectures_demande": dem, "lectures_fond": bgn,
            "gain_formule_fermee": ferme,
            "gain_formule_O_fifo": (f - (1 - p_real) / p_real * part_disque) if p_real else None,
        }
        # précision en calibration au seuil retenu
        s = cal & valid & ~present & (conf >= thP - 1e-9)
        r["P"]["precision_cal"] = float(lab[s].mean()) if s.sum() else None
        r["P"]["n_cal"] = int(s.sum())

    # ---- bras R
    if thR is None:
        r["R"] = {"gain": 0.0, "note": "aucun seuil ne tient : pas d'épingle"}
    else:
        fR, _ = p4.passe_cache(J, E, N, d, pred, conf, theta=thR, t_from=half)
        armR = p4.des(J, E, d, fR, vide, par, "prio")
        tR = float(armR["tok"][half:].sum())
        FR = int(sum(len(fR[g]) for g in range(half * L, ng)))
        s = tst & valid & present & (conf >= thR - 1e-9)
        r["R"] = {"gain": tb / tR - 1.0, "defauts_R": FR, "defauts_base": Ftest,
                  "defauts_moins": 1.0 - FR / Ftest if Ftest else None,
                  "octets_plus": FR / Ftest - 1.0 if Ftest else None,
                  "epingles_candidats_test": int(s.sum()),
                  "precision_epingles_test": float(lab[s].mean()) if s.sum() else None}

    if not complet:
        return r
    # ---- cassure : étiquettes mélangées (ensembles vrais permutés entre jetons)
    rng = np.random.default_rng(20261027 + d)
    perm = rng.permutation(T)
    lab_m = p4.etiquettes(J[perm], pred)
    thm, _ = p4.calibrer(conf[selP], lab_m[selP])
    r["cassure"] = {"theta_sur_etiquettes_melangees": thm}
    if thP is not None:
        s = tst & valid & ~present & (conf >= thP - 1e-9)
        r["cassure"]["precision_test_vraie"] = float(lab[s].mean()) if s.sum() else None
        r["cassure"]["precision_test_etiquettes_melangees"] = float(lab_m[s].mean()) if s.sum() else None
        r["cassure"]["hasard_k_sur_E"] = k / E

    # ---- voisins au hasard (même causalité)
    predA, confA = _predire(nom, J, E, d, True)
    labA = p4.etiquettes(J, predA)
    _, presA = p4.passe_cache(J, E, N, d, predA, confA)
    vA = predA >= 0
    selA = cal & vA & ~presA
    thA, _ = p4.calibrer(confA[selA], labA[selA])
    r["voisins_hasard"] = {"theta_calibre": thA}
    if thP is not None:
        s = tst & vA & ~presA & (confA >= thP - 1e-9)
        r["voisins_hasard"]["precision_test_au_seuil_P"] = float(labA[s].mean()) if s.sum() else None
        r["voisins_hasard"]["n"] = int(s.sum())
    s0 = tst & vA & ~presA
    r["voisins_hasard"]["precision_theta0"] = float(labA[s0].mean()) if s0.sum() else None
    s0 = tst & valid & ~present
    r["precision_theta0_vraie"] = float(lab[s0].mean()) if s0.sum() else None
    r["couverture_theta0"] = float(lab[s0].sum() / Ftest) if Ftest else None
    return r


def main():
    dossier, tem, n7, n20, sortie = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
    ds = [int(x) for x in sys.argv[6].split(",")] if len(sys.argv) > 6 else [2]
    budgets = sys.argv[7].split(",") if len(sys.argv) > 7 else ["7%", "20%"]
    t = json.load(open(tem, encoding="utf-8"))
    w_layer = t["T2_w_final"] / t["L"]
    data = p4.charger(dossier)
    out = {"parametres": {"w_total_120b": t["T2_w_final"], "o_layer": t["T2_o_final"], "L120": t["L"], "w_layer": w_layer},
           "sessions": []}
    t0 = time.time()
    for nom, (J, E) in data.items():
        L = J.shape[1]
        par = {"w_total": w_layer * L, "w_layer": w_layer, "tail": 1.85, "tr": TR, "o": t["T2_o_final"]}
        for d in ds:
            for budget, N in (("7%", n7), ("20%", n20)):
                if budget not in budgets:
                    continue
                r = session(nom, J, E, N, d, par, w_layer, complet=(d == 2))
                r["budget"] = budget
                out["sessions"].append(r)
                P, R = r["P"], r["R"]
                print(f"{nom:18s} N={N:4d} d={d} thP={r['thP']} thR={r['thR']} | P gain {100*P['gain']:+.2f} % "
                      f"octets {100*(P.get('octets_plus') or 0):+.1f} % prec {P.get('precision_test')} | R gain {100*R['gain']:+.2f} % "
                      f"[{time.time()-t0:.0f}s]", flush=True)
        json.dump(out, open(sortie, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    json.dump(out, open(sortie, "w", encoding="utf-8"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
