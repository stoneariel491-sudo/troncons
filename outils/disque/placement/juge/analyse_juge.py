"""Analyse de la séance du juge du placement disque, aux seuils déclarés (00-seuils-declares.md).

  python -I -X utf8 outils/disque/placement/juge/analyse_juge.py

Lit mesures/disque/placement/juge/seance/*.json|csv et J0-recalcul.json ; écrit
mesures/disque/placement/juge/analyse-juge.json et imprime les verdicts. Une passe « sous charge » est
écartée des verdicts (et nommée). Rien n'est importé des outils de l'enquête.
"""
import csv
import json
import pathlib
import statistics as st

R = pathlib.Path(__file__).resolve().parents[4]
J = R / "mesures/disque/placement/juge"
S_ = J / "seance"
PLANCHER = 0.118


def e_soi(v):
    return (max(v) - min(v)) / (sum(v) / len(v)) if len(v) > 1 else 0.0


def verdict(r, s):
    return "diffèrent" if abs(r - 1) > s else ("égaux" if abs(r - 1) < s / 2 else "entre deux")


def passes(prefixe):
    out = []
    for f in sorted(S_.glob(f"{prefixe}-*.json")):
        if f.name.endswith(".troncons.json") or f.name.endswith(".mesurer.json"):
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(d, dict) and "nom" in d:
            out.append(d)
    return out


ARRETS = {}  # nom de passe → secondes sous 0,5 Go/s (plages de 3 s ou plus), rempli par marquer_arrets()
SANS_ARRETS = False  # vue indicative, non déclarée : passes à arrêt écartées


def marquer_arrets(ps):
    for p in ps:
        c = S_ / f"{p['nom']}.csv"
        if c.exists() and p["nom"] not in ARRETS:
            t = par_seconde(lire_csv(p["nom"]))
            ARRETS[p["nom"]] = sum(n for _, n in plages_lentes(t[:-1], 0.5, 3))


def groupes(ps, cle):
    """Écarte les passes sous charge et celles qui ont fini sur batterie (00 § 4) ; en vue indicative,
    écarte aussi les passes à arrêt du disque."""
    g, charge = {}, []
    marquer_arrets(ps)
    for p in ps:
        if p.get("sous_charge") or p.get("secteur_apres") is False:
            charge.append(p["nom"])
            continue
        if SANS_ARRETS and ARRETS.get(p["nom"], 0) > 0:
            charge.append(p["nom"] + " (arrêt)")
            continue
        g.setdefault(cle(p), []).append(p["go_s"])
    return g, charge


def serie(g):
    med = {k: st.median(v) for k, v in g.items()}
    es = {k: e_soi(v) for k, v in g.items()}
    S = max(2 * max(es.values()), PLANCHER)
    return med, es, S


def lire_csv(nom):
    with open(S_ / f"{nom}.csv", newline="", encoding="utf-8") as f:
        l = []
        for x in csv.DictReader(f):
            d = {"indice": int(x["indice"]), "decalage": int(x["decalage"]), "longueur": int(x["longueur"]),
                 "morceaux": int(x["morceaux"]) if x["morceaux"] else None,
                 "debut_us": float(x["debut_us"]), "fin_us": float(x["fin_us"])}
            d["duree_us"] = d["fin_us"] - d["debut_us"]
            l.append(d)
        return l


def ajuster(pts):
    mx = st.fmean(x for x, _ in pts)
    my = st.fmean(y for _, y in pts)
    b = sum((x - mx) * (y - my) for x, y in pts) / sum((x - mx) ** 2 for x, _ in pts)
    return my - b * mx, b


CLASSES = [(1, 1), (2, 9), (10, 99), (100, 10 ** 9)]
ETIQ = ["1-1", "2-9", "10-99", "100-..."]


def classe(n):
    for i, (a, b) in enumerate(CLASSES):
        if a <= n <= b:
            return i


def par_seconde(l):
    fin = max(x["fin_us"] for x in l)
    o = [0.0] * (int(fin / 1e6) + 1)
    for x in l:
        a, b = x["debut_us"] / 1e6, x["fin_us"] / 1e6
        v = x["longueur"] / (b - a)
        k = int(a)
        while k < b and k < len(o):
            o[k] += v * (min(b, k + 1) - max(a, k))
            k += 1
    return [y / 1e9 for y in o]


def plages_lentes(t1, seuil=0.5, duree=10):
    p, k = [], 0
    while k < len(t1):
        if t1[k] < seuil:
            j = k
            while j < len(t1) and t1[j] < seuil:
                j += 1
            if j - k >= duree:
                p.append((k, j - k))
            k = j
        else:
            k += 1
    return p


def main(vue_sans_arrets=False):
    global SANS_ARRETS
    SANS_ARRETS = vue_sans_arrets
    j0 = json.loads((J / "J0-recalcul.json").read_text(encoding="utf-8"))
    sigma = j0["J0a"]["sigma_inter"]["ecart_type_relatif"]
    out = {"sous_charge": [], "smart": {}}
    toutes = [x for k in ("J2", "J3", "J4", "J5", "J6", "J7", "J8") for x in passes(k)]
    out["sous_charge"] = [p["nom"] for p in toutes if p.get("sous_charge")]
    rap = [p["smart_ecart"]["octets_lus_disque"] / p["octets"] for p in toutes
           if p.get("smart_ecart") and p.get("octets") and p.get("outil", "").endswith("lecteur.py") and not p.get("sous_charge")]
    temps = [t for p in toutes if p.get("smart_ecart") for t in p["smart_ecart"]["temperature"]]
    out["smart"] = {"disque_lu_sur_demande_min": min(rap), "disque_lu_sur_demande_max": max(rap), "passes": len(rap),
                    "temperature_min": min(temps), "temperature_max": max(temps),
                    "tmt_transitions": sum(p["smart_ecart"]["tmt"] for p in toutes if p.get("smart_ecart")),
                    "ecrit_par_hote_mo_max": max(p["smart_ecart"]["octets_ecrits_disque"] / 1e6 for p in toutes if p.get("smart_ecart"))}
    # J1
    out["J1"] = json.loads((S_ / "J1-cartes.json").read_text(encoding="utf-8"))
    # J2
    ps = [p for p in passes("J2") if "frein" not in p["nom"] and "troncons" not in p["nom"]]
    g, ch = groupes(ps, lambda p: p["cle"])
    med, es, S = serie(g)
    r = med["B20"] / med["A20"]
    Ta = max(2 * sigma, S / 2)
    td = {p["cle"]: p for p in passes("J2") if "troncons" in p["nom"]}
    fr = [p for p in passes("J2") if "frein" in p["nom"]][0]
    sha = json.loads((S_ / "J2-temoin-sha.json").read_text(encoding="utf-8"))
    out["J2"] = {"passes": g, "mediane": med, "e_soi": es, "S_j": S, "B20_sur_A20": r, "verdict": verdict(r, S),
                 "T_a": Ta, "ecart_a_1_423": r / 1.423 - 1, "a_redonne": (r - 1 > S) and abs(r / 1.423 - 1) < Ta,
                 "temoin_troncons": {k: {"troncons_go_s": td[k]["go_s"], "moi_sur_troncons": med[k] / td[k]["go_s"],
                                         "tient": abs(med[k] / td[k]["go_s"] - 1) < S / 2,
                                         "sous_charge": td[k].get("sous_charge")} for k in td},
                 "cassure_frein": {"go_s": fr["go_s"], "sur_troncons_A20": fr["go_s"] / td["A20"]["go_s"],
                                   "tombe": abs(fr["go_s"] / td["A20"]["go_s"] - 1) > S / 2},
                 "temoin_sha": sha, "sous_charge": ch}
    # J3
    ps = passes("J3")
    g, ch = groupes(ps, lambda p: f"{p['cle']}-{'croise' if 'croise' in p['nom'] else 'natif'}")
    med, es, S = serie(g)
    ra = med["A20-croise"] / med["A20-natif"]
    rb = med["B20-croise"] / med["B20-natif"]
    suit_fichier = abs(ra - 1) < S / 2 and abs(rb - 1) < S / 2
    suit_motif = (ra - 1 > S) and (rb - 1 < -S)
    out["J3"] = {"passes": g, "mediane": med, "e_soi": es, "S_j": S, "A20_croise_sur_natif": ra, "B20_croise_sur_natif": rb,
                 "B20_natif_sur_A20_natif": med["B20-natif"] / med["A20-natif"],
                 "B20_croise_sur_A20_natif": med["B20-croise"] / med["A20-natif"],
                 "verdict": "suit le fichier" if suit_fichier else ("suit le motif" if suit_motif else "ni l'un ni l'autre au seuil"),
                 "sous_charge": ch}
    # J4
    g, ch = groupes(passes("J4"), lambda p: p["cle"])
    med, es, S = serie(g)
    ra, rb = med["R20"] / med["A20"], med["R20"] / med["B20"]
    tombe_17 = (ra - 1 > S) and abs(rb - 1) < S / 2
    out["J4"] = {"passes": g, "mediane": med, "e_soi": es, "S_j": S, "R20_sur_A20": ra, "R20_sur_B20": rb,
                 "B20_sur_A20": med["B20"] / med["A20"], "verdict_R_A": verdict(ra, S), "verdict_R_B": verdict(rb, S),
                 "etat_du_17_tombe": tombe_17, "R20_retombe": abs(ra - 1) < S / 2, "sous_charge": ch}
    # J7
    g, ch = groupes(passes("J7"), lambda p: f"{p['cle']} q{p['q']}")
    med, es, S = serie(g)
    out["J7"] = {"passes": g, "mediane": med, "e_soi": es, "S_j": S, "sous_charge": ch}
    for k in ["A20", "B20"]:
        out["J7"][f"{k}_q2_sur_q4"] = med[f"{k} q2"] / med[f"{k} q4"]
        out["J7"][f"{k}_q8_sur_q4"] = med[f"{k} q8"] / med[f"{k} q4"]
    out["J7"]["q2_tient"] = all(out["J7"][f"{k}_q2_sur_q4"] - 1 > S for k in ["A20", "B20"])
    out["J7"]["q8_ne_cache_rien"] = all(out["J7"][f"{k}_q8_sur_q4"] < 1 + S / 2 for k in ["A20", "B20"])
    # J5
    b0 = j0["J0b"]
    Tn = b0["T_n"]
    j5 = {}
    for p in passes("J5"):
        l = lire_csv(p["nom"])
        pts = [(x["morceaux"] - 1, x["duree_us"] / x["longueur"] * 12e6) for x in l]
        pair, impair = pts[0::2], pts[1::2]
        t1, tau = ajuster(pair)
        mes = sum(y for _, y in impair)
        moy = st.fmean(y for _, y in pair)
        crit = {}
        for m, (a, b) in {"lineaire": (t1, tau), "constant": (moy, 0.0)}.items():
            ec_med, ec_moy = {}, {}
            for c in range(len(CLASSES)):
                ys = [y for x, y in impair if classe(x + 1) == c]
                pr = [a + b * x for x, y in impair if classe(x + 1) == c]
                if ys:
                    ec_med[ETIQ[c]] = st.median(pr) / st.median(ys) - 1
                    ec_moy[ETIQ[c]] = st.fmean(pr) / st.fmean(ys) - 1
            crit[m] = {"somme_impaires": sum(a + b * x for x, _ in impair) / mes,
                       "critere_08": abs(sum(a + b * x for x, _ in impair) / mes - 1) < 0.10,
                       "erreur_mediane_par_classe": ec_med, "critere_par_classe_declare": all(abs(e) < Tn[c] for c, e in ec_med.items()),
                       "erreur_moyenne_par_classe_non_declare": ec_moy}
        n_cl = {ETIQ[c]: sum(1 for x, _ in pts if classe(x + 1) == c) for c in range(len(CLASSES))}
        c_frac = sum(1 for x in l if x["morceaux"] > 1) / len(l)
        nbar = st.fmean(x["morceaux"] for x in l if x["morceaux"] > 1)
        L = st.fmean(x["longueur"] for x in l)
        little = 4 * L / ((t1 + c_frac * (nbar - 1) * tau) * L / 12e6) / 1e3  # Go/s : q L / t moyen (t ramené à L)
        j5[p["nom"]] = {"go_s": p["go_s"], "t1_ms": t1 / 1e3, "tau_us": tau, "lectures_par_classe": n_cl, "criteres": crit,
                        "fraction_coupees": c_frac, "morceaux_moyens_des_coupees": nbar, "little_go_s": little,
                        "t1_dans_T_t": abs(t1 / 1e3 / 17.1 - 1) < b0["T_t"], "tau_dans_T_tau": abs(tau / 366 - 1) < b0["T_tau"],
                        "sous_charge": p.get("sous_charge")}
    out["J5"] = j5
    # J6
    g, ch = groupes(passes("J6"), lambda p: p["cle"])
    med, es, S = serie(g)
    rca = med["C120"] / med["A120"]
    c5 = st.median(x["go_s"] for x in j5.values())
    out["J6"] = {"passes": g, "mediane": med, "e_soi": es, "S_j": S, "C_sur_A": rca, "verdict_C_A": verdict(rca, S),
                 "C_sur_B": med["C120"] / med["B120"], "B_sur_A": med["B120"] / med["A120"],
                 "C_non_coupe_tient": rca - 1 > S, "C_non_coupe_tombe": abs(rca - 1) < S / 2,
                 "C120_tire_J5_go_s": c5, "contigu_aujourd_hui_sur_tire": med["C120"] / c5, "sous_charge": ch}
    # J8
    p8 = passes("J8")
    if p8:
        p = p8[0]
        l = lire_csv(p["nom"])
        t1 = par_seconde(l)
        pl = plages_lentes(t1)
        lentes = set()
        for a, n in pl:
            lentes |= {x["indice"] for x in l if x["fin_us"] / 1e6 > a and x["debut_us"] / 1e6 < a + n}
        # lectures prises dans les plages lentes de p2a-15 et p2a-20
        anciennes = set()
        for nom in ["p2a-15-lire-tout-A120", "p2a-20-lire-tout-A120"]:
            with open(R / "mesures/disque/placement/p2a" / f"{nom}.csv", newline="", encoding="utf-8") as f:
                la = [{"indice": int(x["indice"]), "debut_us": float(x["debut_us"]), "fin_us": float(x["fin_us"]),
                       "longueur": int(x["longueur"])} for x in csv.DictReader(f)]
            for a, n in plages_lentes(par_seconde(la)):
                anciennes |= {x["indice"] for x in la if x["fin_us"] / 1e6 > a and x["debut_us"] / 1e6 < a + n}
        out["J8"] = {"go_s": p["go_s"], "secondes": p["secondes"], "plages_sous_0_5_de_10_s_ou_plus": pl,
                     "secondes_sous_0_5": sum(1 for x in t1 if x < 0.5), "par_seconde": [round(x, 3) for x in t1],
                     "lectures_lentes": len(lentes), "lectures_lentes_anciennes": len(anciennes),
                     "communes": len(lentes & anciennes),
                     "communes_attendues_au_hasard": len(lentes) * len(anciennes) / 4608, "sous_charge": p.get("sous_charge")}
    out["arrets_par_passe_s"] = {k: v for k, v in ARRETS.items() if v}
    out["vue"] = "indicative, non déclarée : passes à arrêt écartées" if vue_sans_arrets else "déclarée (00-seuils-declares.md)"
    (J / ("analyse-juge-sans-arrets.json" if vue_sans_arrets else "analyse-juge.json")).write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    # impression
    print("sous charge :", out["sous_charge"])
    print("SMART :", out["smart"])
    print("J1 :", {k: (v.get("extents"), v.get("egal_carte_08"), v.get("coupes")) for k, v in out["J1"].items() if isinstance(v, dict)},
          "témoins", out["J1"]["temoins"], "RÉP A120 = C120", out["J1"]["repertoires_A120_C120_egaux"])
    for t in ["J2", "J3", "J4", "J7", "J6"]:
        print(t, json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in out[t].items() if k != "passes"}, ensure_ascii=False, default=str))
        print("   passes", {k: [round(x, 3) for x in v] for k, v in out[t]["passes"].items()})
    for k, v in out["J5"].items():
        print("J5", k, json.dumps(v, ensure_ascii=False, default=lambda x: round(x, 4) if isinstance(x, float) else str(x)))
    if "J8" in out:
        print("J8", {k: v for k, v in out["J8"].items() if k != "par_seconde"})


def analyse_jbis():
    """Amendement § 5 : verdicts de J3, J4, J7 sur J-bis (passes à arrêt écartées), J9, J8."""
    def grp(prefixe, cle):
        g, ecartees = {}, []
        for p in passes(prefixe):
            e = p.get("smart_ecart") or {}
            ratio = e.get("octets_lus_disque", 0) / p["octets"] if p.get("octets") else 1.0
            if p.get("sous_charge") or p.get("secteur_apres") is False or p.get("arret_s") or not 0.98 <= ratio <= 1.02:
                # témoin (iii) du § 2 des seuils : le disque doit lire 0,98 à 1,02 fois ce qui est demandé ; au-delà,
                # un autre lecteur a pris le disque pendant la passe
                ecartees.append(f"{p['nom']} (arrêt {p.get('arret_s')} s)" if p.get("arret_s") else
                                (f"{p['nom']} (disque lu / demandé {ratio:.4f})" if not 0.98 <= ratio <= 1.02 else p["nom"]))
                continue
            g.setdefault(cle(p), []).append(p["go_s"])
        return g, ecartees
    etq = lambda p: p["nom"].split("-", 2)[2]
    out = {}
    if not passes("Jb3"):
        return out
    g, ec = grp("Jb3", etq)
    med, es, S = serie(g)
    ra, rb = med["A20-croise"] / med["A20-natif"], med["B20-croise"] / med["B20-natif"]
    out["J3"] = {"passes": g, "mediane": med, "e_soi": es, "S_j": S, "A20_croise_sur_natif": ra, "B20_croise_sur_natif": rb,
                 "verdict": "suit le fichier" if abs(ra - 1) < S / 2 and abs(rb - 1) < S / 2 else
                 ("suit le motif" if ra - 1 > S and rb - 1 < -S else "ni l'un ni l'autre au seuil"), "ecartees": ec}
    g, ec = grp("Jb4", etq)
    med, es, S = serie(g)
    ra, rb = med["R20"] / med["A20"], med["R20"] / med["B20"]
    out["J4"] = {"passes": g, "mediane": med, "e_soi": es, "S_j": S, "R20_sur_A20": ra, "R20_sur_B20": rb,
                 "verdict_R_A": verdict(ra, S), "verdict_R_B": verdict(rb, S),
                 "etat_du_17_tombe": ra - 1 > S and abs(rb - 1) < S / 2, "R20_retombe": abs(ra - 1) < S / 2, "ecartees": ec}
    g, ec = grp("Jb7", etq)
    med, es, S = serie(g)
    o = {"passes": g, "mediane": med, "e_soi": es, "S_j": S, "ecartees": ec}
    for k in ["A20", "B20"]:
        o[f"{k}_q2_sur_q4"] = med[f"q2-{k}"] / med[f"q4-{k}"]
        o[f"{k}_q8_sur_q4"] = med[f"q8-{k}"] / med[f"q4-{k}"]
        o[f"{k}_q2_verdict"] = verdict(o[f"{k}_q2_sur_q4"], S)
    o["q2_tient"] = all(o[f"{k}_q2_sur_q4"] - 1 > S for k in ["A20", "B20"])
    o["q8_ne_cache_rien"] = all(o[f"{k}_q8_sur_q4"] < 1 + S / 2 for k in ["A20", "B20"])
    out["J7"] = o
    g, ec = grp("Jb9", etq)
    med, es, S = serie(g)
    r = {"Ar/An": med["A20-raccourci"] / med["A20-natif"], "Ba/Bn": med["B20-allonge"] / med["B20-natif"],
         "Ap/An": med["A20-pas12Mio"] / med["A20-natif"], "Bp/Bn": med["B20-pasA"] / med["B20-natif"]}
    out["J9"] = {"passes": g, "mediane": med, "e_soi": es, "S_j": S, "rapports": r,
                 "longueur_decide": r["Ar/An"] - 1 > S and r["Ba/Bn"] - 1 < -S,
                 "longueur_ne_decide_pas": abs(r["Ar/An"] - 1) < S / 2 and abs(r["Ba/Bn"] - 1) < S / 2,
                 "pas_decide": r["Ap/An"] - 1 > S or r["Bp/Bn"] - 1 < -S,
                 "pas_ne_decide_pas": abs(r["Ap/An"] - 1) < S / 2 and abs(r["Bp/Bn"] - 1) < S / 2, "ecartees": ec}
    # lecture par sous-test (l'amendement § 5 déclare J9-L et J9-P avec chacun son ordre) : S_j de chacun
    gl = {k: v for k, v in g.items() if k in ("A20-natif", "A20-raccourci", "B20-natif", "B20-allonge")}
    gp = {k: v for k, v in g.items() if k in ("A20-pas12Mio", "B20-pasA")}
    _, esl, Sl = serie(gl)
    _, esp, Sp = serie(gp)
    out["J9"]["par_sous_test"] = {
        "J9-L": {"S_j": Sl, "longueur_decide": r["Ar/An"] - 1 > Sl and r["Ba/Bn"] - 1 < -Sl,
                 "longueur_ne_decide_pas": abs(r["Ar/An"] - 1) < Sl / 2 and abs(r["Ba/Bn"] - 1) < Sl / 2,
                 "verdict_A": verdict(r["Ar/An"], Sl), "verdict_B": verdict(r["Ba/Bn"], Sl)},
        "J9-P": {"S_j": Sp, "pas_decide": r["Ap/An"] - 1 > Sp or r["Bp/Bn"] - 1 < -Sp,
                 "pas_ne_decide_pas": abs(r["Ap/An"] - 1) < Sp / 2 and abs(r["Bp/Bn"] - 1) < Sp / 2,
                 "verdict_A": verdict(r["Ap/An"], Sp), "verdict_B": verdict(r["Bp/Bn"], Sp)}}
    if passes("J10"):
        g, ec = grp("J10", etq)
        med, es, S = serie(g)
        r = med["A20-moities"] / med["A20-natif"]
        tem = json.loads((S_ / "J10-temoin.json").read_text(encoding="utf-8")) if (S_ / "J10-temoin.json").exists() else None
        out["J10"] = {"passes": g, "mediane": med, "e_soi": es, "S_j": S, "moities_sur_natif": r, "verdict": verdict(r, S),
                      "levier_tient": r - 1 > S, "levier_tombe": abs(r - 1) < S / 2, "temoin": tem, "ecartees": ec}
    if passes("J11"):
        g, ec = grp("J11", etq)
        med, es, S = serie(g)
        r = med["A20-moities-q4"] / med["A20-natif"]
        out["J11"] = {"passes": g, "mediane": med, "e_soi": es, "S_j": S, "moities_q4_sur_natif": r, "verdict": verdict(r, S),
                      "levier_tient": r - 1 > S, "levier_tombe": abs(r - 1) < S / 2, "moins_vite": r - 1 < -S, "ecartees": ec}
    p8 = passes("Jb8")
    if p8:
        p = p8[0]
        l = lire_csv(p["nom"])
        t1 = par_seconde(l)
        out["J8"] = {"go_s": p["go_s"], "secondes": p["secondes"], "arret_s": p.get("arret_s"),
                     "plages_sous_0_5_de_10_s_ou_plus": plages_lentes(t1[:-1]),
                     "plages_de_3_s_ou_plus": plages_lentes(t1[:-1], 0.5, 3), "par_seconde": [round(x, 3) for x in t1]}
    (J / "analyse-jbis.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    for t, v in out.items():
        print("J-bis", t, json.dumps({k: (round(x, 4) if isinstance(x, float) else x) for k, x in v.items() if k not in ("passes", "par_seconde")}, ensure_ascii=False, default=str))
        if "passes" in v:
            print("   passes", {k: [round(x, 3) for x in y] for k, y in v["passes"].items()})
    return out


if __name__ == "__main__":
    import sys
    if "--jbis" in sys.argv:
        analyse_jbis()
    else:
        main("--sans-arrets" in sys.argv)
