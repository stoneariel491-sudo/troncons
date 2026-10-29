"""J0 du juge du placement disque : recalcul, sur les journaux commités de l'enquête, de ses chiffres publiés.

  python -I -X utf8 outils/disque/placement/juge/recalcul.py

Chemin propre : rien n'est importé des outils de l'enquête (analyse.py, lire.py, carte.py, seance.py) ; les
journaux sont lus tels qu'ils sont commités (JSON des passes `troncons disque`, CSV des profils de lire.py,
JSON de `troncons mesurer`). Seuils : mesures/disque/placement/juge/00-seuils-declares.md (déclarés avant).
Écrit mesures/disque/placement/juge/J0-recalcul.json et imprime le résumé (journal J0-recalcul.log).
"""
import csv
import hashlib
import json
import math
import pathlib
import statistics as st

R = pathlib.Path(__file__).resolve().parents[4]
P = R / "mesures/disque/placement"
JUGE_C = R / "mesures/genome/construction/juge/vitesse"
LOT_B = R / "mesures/genome/construction/synonyme/vitesse"
SORTIE = P / "juge"
GRAINE = 1618033
PLANCHER = 0.118


def tirage(n, k, sel=""):
    """Les k premiers indices de range(n) rangés par SHA-256(« juge-placement:G:sel:i »)."""
    cle = lambda i: hashlib.sha256(f"juge-placement:{GRAINE}:{sel}{i}".encode()).digest()
    return sorted(range(n), key=cle)[:k]


def e_soi(v):
    return (max(v) - min(v)) / (sum(v) / len(v)) if len(v) > 1 else 0.0


def verdict(r, s):
    return "diffèrent" if abs(r - 1) > s else ("égaux" if abs(r - 1) < s / 2 else "entre deux")


def nom_court(chemin):
    n = chemin.replace("\\", "/").split("/")[-1]
    return {"gpt-oss-20b.trc": "A20", "gpt-oss-20b-v12.trc": "B20", "gpt-oss-120b.trc": "A120",
            "gpt-oss-120b-v12.trc": "B120", "gpt-oss-120b-v10-recode.trc": "C120", "D20.trc": "D20",
            "F20.trc": "F20", "gpt-oss-20b-synonyme-l0.rapide.trc": "R20",
            "gpt-oss-120b-frontiere.rapide.trc": "R120"}.get(n, n)


def rangs(v):
    o = sorted(range(len(v)), key=v.__getitem__)
    r = [0.0] * len(v)
    i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
            j += 1
        for k in range(i, j + 1):
            r[o[k]] = (i + j) / 2
        i = j + 1
    return r


def pearson(x, y):
    mx, my = st.fmean(x), st.fmean(y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    return sxy / math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y))


def spearman(x, y):
    return pearson(rangs(x), rangs(y))


# ------------------------------------------------------------------------------------------------ J0-a

def seance_disque(s):
    """Passes `troncons disque` d'une séance de l'enquête, regroupées par (fichier, profondeur)."""
    d = P / s
    passes = {}
    for f in sorted(d.glob(f"{s}-*-disque-*.json")):
        if f.name.endswith(".erreur.json"):
            continue
        j = json.loads(f.read_text(encoding="utf-8"))
        if j.get("outil") != "troncons disque":  # les passes lire.py « -lire-disque- » ne sont pas l'instrument
            continue
        passes.setdefault((nom_court(j["fichier"]), j.get("profondeur", 4)), []).append(round(j["go_s"], 6))
    return passes


def resume_seance(passes):
    med = {k: st.median(v) for k, v in passes.items()}
    es = {k: e_soi(v) for k, v in passes.items()}
    S = max(2 * max(es.values()), PLANCHER)
    return med, es, S


def j0a():
    out = {}
    for s in ["p2a", "p2b-D", "p2b-D2", "p2b-F", "p2b-Fb", "p2b-Fb2", "p4", "p5"]:
        passes = seance_disque(s)
        med, es, S = resume_seance(passes)
        paires = {}
        cles = sorted(med)
        for i, a in enumerate(cles):
            for b in cles[i + 1:]:
                if a[1] == b[1]:
                    r = med[b] / med[a]
                    paires[f"{b[0]}/{a[0]} q{a[1]}"] = (round(r, 4), verdict(r, S))
                if a[0] == b[0] and a[1] != b[1]:
                    r = med[b] / med[a]
                    paires[f"{a[0]} q{b[1]}/q{a[1]}"] = (round(r, 4), verdict(r, S))
        out[s] = {"passes": {f"{k[0]} q{k[1]}": v for k, v in passes.items()},
                  "mediane": {f"{k[0]} q{k[1]}": round(v, 4) for k, v in med.items()},
                  "e_soi": {f"{k[0]} q{k[1]}": round(v, 4) for k, v in es.items()}, "S": round(S, 4), "rapports": paires}
    # le juge de la construction (20b, étage disque)
    jc = {}
    for f in sorted(JUGE_C.glob("20b-disque-*.json")):
        j = json.loads(f.read_text(encoding="utf-8"))
        jc.setdefault(nom_court(j["fichier"]), []).append(j["go_s"])
    out["juge-construction-20b"] = {"passes": jc, "mediane": {k: st.median(v) for k, v in jc.items()}}
    # σ_inter de r(B20/A20) à q = 4
    r = {}
    for s in ["p2a", "p2b-D", "p2b-F", "p2b-Fb2", "p4", "p5"]:
        m = {k: st.median(v) for k, v in seance_disque(s).items()}
        r[s] = m[("B20", 4)] / m[("A20", 4)]
    r["juge-construction"] = st.median(jc["B20"]) / st.median(jc["A20"])
    v = list(r.values())
    out["sigma_inter"] = {"r_par_seance": {k: round(x, 4) for k, x in r.items()}, "moyenne": round(st.fmean(v), 4),
                          "ecart_type_relatif": round(st.stdev(v) / st.fmean(v), 4)}
    # p2b-Fb2 : F20 contre A20, passe par passe (résidu)
    fb2 = seance_disque("p2b-Fb2")
    a, f = fb2[("A20", 4)], fb2[("F20", 4)]
    u = sum(1 for x in f for y in a if x > y)
    out["Fb2_F20_contre_A20"] = {"F20_au_dessus_de_A20_paires": f"{u}/{len(f) * len(a)}",
                                 "min_F20": min(f), "max_A20": max(a),
                                 "p_bilateral_exact_4_contre_4": round(2 / math.comb(8, 4), 4) if u == 16 else None}
    # p3 : bout en bout
    p3 = {}
    for fj in sorted((P / "p3").glob("p3-*-mesurer-*.json")):
        j = json.loads(fj.read_text(encoding="utf-8"))
        c = j["compteurs_generation"]
        p3[fj.stem] = {"jetons_s": round(j["generation_jetons_s"], 3), "s_lectures": round(c["s_lectures"], 2),
                       "s_pas": round(c["s_pas"], 2), "texte": j["texte_sha256"][:12],
                       "octets_troncons": c["octets_lus_troncons"], "defauts": c["defauts_disque"]}
    ga = [x["jetons_s"] for k, x in p3.items() if k.endswith("A20")]
    gd = [x["jetons_s"] for k, x in p3.items() if k.endswith("D20")]
    out["p3"] = {"passes": p3, "A20": st.median(ga), "D20": st.median(gd), "rapport": round(st.median(gd) / st.median(ga), 4),
                 "e_soi": {"A20": round(e_soi(ga), 4), "D20": round(e_soi(gd), 4)},
                 "textes": sorted({x["texte"] for x in p3.values()}), "octets": sorted({x["octets_troncons"] for x in p3.values()}),
                 "s_lectures_median": st.median(x["s_lectures"] for x in p3.values()), "s_pas_median": st.median(x["s_pas"] for x in p3.values())}
    return out


# ------------------------------------------------------------------------------------------------ profils

def lire_profil(nom):
    p = P / "p2a" / f"{nom}.csv"
    with open(p, newline="", encoding="utf-8") as g:
        lignes = []
        for x in csv.DictReader(g):
            l = {k: (float(v) if k in ("lcn_frac", "debut_us", "fin_us") else int(v)) for k, v in x.items()}
            l["duree_us"] = l["fin_us"] - l["debut_us"]
            l["debit"] = l["longueur"] / l["duree_us"] / 1e3  # Go/s
            lignes.append(l)
    return lignes


def ajuster(points):
    """Moindres carrés y = a + b x. points : (x, y)."""
    mx = st.fmean(x for x, _ in points)
    my = st.fmean(y for _, y in points)
    b = sum((x - mx) * (y - my) for x, y in points) / sum((x - mx) ** 2 for x, _ in points)
    return my - b * mx, b


CLASSES = [(1, 1), (2, 9), (10, 99), (100, 10 ** 9)]


def classe(n):
    for i, (a, b) in enumerate(CLASSES):
        if a <= n <= b:
            return i


def j0b(prof):
    """H1 : le modèle de 08, la puissance de son critère, un critère par classe."""
    out = {}
    med_cl = {}
    for nom, lignes in prof.items():
        pts = [(l["morceaux"] - 1, l["duree_us"] / l["longueur"] * 12e6) for l in lignes]
        pair, impair = pts[0::2], pts[1::2]
        t1, tau = ajuster(pair)
        mes = sum(y for _, y in impair)
        moy_pair = st.fmean(y for _, y in pair)
        modeles = {"08 (t1 + (n-1) tau)": (t1, tau), "constant (moyenne des paires)": (moy_pair, 0.0),
                   "tau x 0,5": (t1, tau * 0.5), "tau x 2": (t1, tau * 2.0)}
        crit = {}
        for m, (a, b) in modeles.items():
            pred = sum(a + b * x for x, _ in impair)
            par_cl = {}
            for c in range(len(CLASSES)):
                ys = [y for x, y in impair if classe(x + 1) == c]
                ps = [a + b * x for x, y in impair if classe(x + 1) == c]
                if ys:
                    par_cl[c] = st.median(ps) / st.median(ys) - 1
            crit[m] = {"somme_impaires_predite_sur_mesuree": round(pred / mes, 4), "critere_08_10pc": abs(pred / mes - 1) < 0.10,
                       "erreur_mediane_par_classe": {f"{CLASSES[c][0]}-{CLASSES[c][1] if CLASSES[c][1] < 10**9 else '...'}": round(e, 4) for c, e in par_cl.items()}}
        # le débit rendu par Little (X = q L / t moyen) avec chaque modèle
        n_moy = st.fmean(l["morceaux"] for l in lignes)
        out[nom] = {"t1_ms": round(t1 / 1e3, 3), "tau_us": round(tau, 2), "n_lectures": len(lignes),
                    "morceaux_moyen": round(n_moy, 3), "criteres": crit}
        med_cl[nom] = {c: st.median([l["duree_us"] / l["longueur"] * 12e6 for l in lignes if classe(l["morceaux"]) == c]) for c in range(len(CLASSES))}
    # tolérance par classe T_n = max(10 %, 2 × |méd17 / méd18 − 1|)
    a, b = med_cl["p2a-17-lire-tout-C120"], med_cl["p2a-18-lire-tout-C120"]
    tn = {c: max(0.10, 2 * abs(a[c] / b[c] - 1)) for c in a}
    out["T_n"] = {f"{CLASSES[c][0]}-{CLASSES[c][1] if CLASSES[c][1] < 10**9 else '...'}": round(v, 4) for c, v in tn.items()}
    etiquette = {f"{CLASSES[c][0]}-{CLASSES[c][1] if CLASSES[c][1] < 10**9 else '...'}": c for c in range(len(CLASSES))}
    for nom in prof:
        for m, x in out[nom]["criteres"].items():
            x["critere_par_classe"] = all(abs(e) < tn[etiquette[c]] for c, e in x["erreur_mediane_par_classe"].items())
    # bruit des sous-échantillons de taille N = 1 200 (tolérances T_tau, T_t de J5)
    N = 1200
    for nom, lignes in prof.items():
        t1s, taus = [], []
        for k in range(200):
            idx = tirage(len(lignes), N, sel=f"boot{k}:")
            sous = [lignes[i] for i in idx]
            pts = [(l["morceaux"] - 1, l["duree_us"] / l["longueur"] * 12e6) for l in sous]
            t1, tau = ajuster(pts[0::2])
            t1s.append(t1)
            taus.append(tau)
        t1s.sort()
        taus.sort()
        dl = lambda v: (v[194] - v[5]) / 2 / st.median(v)  # demi-largeur relative à 95 % (rangs 5 et 194 sur 200)
        out[nom]["sous_echantillons_N1200"] = {"t1_demi_largeur_95": round(dl(t1s), 4), "tau_demi_largeur_95": round(dl(taus), 4)}
    hw_t = max(out[n]["sous_echantillons_N1200"]["t1_demi_largeur_95"] for n in prof)
    hw_tau = max(out[n]["sous_echantillons_N1200"]["tau_demi_largeur_95"] for n in prof)
    out["T_t"] = round(max(2 * hw_t, 0.10), 4)
    out["T_tau"] = round(max(2 * hw_tau, 0.10), 4)
    return out


def j0c(lignes):
    """Composition de la file : part du temps des voisines en vol qui sont des lectures coupées."""
    ordre = sorted(range(len(lignes)), key=lambda i: lignes[i]["debut_us"])
    deb = [lignes[i]["debut_us"] for i in ordre]
    res = []
    for pos, i in enumerate(ordre):
        u = lignes[i]
        if u["morceaux"] != 1:
            continue
        coupe = tout = 0.0
        # voisines : celles qui commencent avant la fin de u et finissent après son début
        j = pos
        while j > 0 and deb[j - 1] > u["debut_us"] - 5e6:
            j -= 1
        while j < len(ordre) and deb[j] < u["fin_us"]:
            o = lignes[ordre[j]]
            if ordre[j] != i:
                rec = min(u["fin_us"], o["fin_us"]) - max(u["debut_us"], o["debut_us"])
                if rec > 0:
                    tout += rec
                    if o["morceaux"] > 1:
                        coupe += rec
            j += 1
        res.append((coupe / tout if tout else 0.0, u["debit"]))
    bas = [d for p, d in res if p < 0.25]
    haut = [d for p, d in res if p > 0.75]
    milieu = [d for p, d in res if 0.25 <= p <= 0.75]
    return {"non_coupees": len(res), "part_sous_0_25": len(bas), "part_0_25_a_0_75": len(milieu), "part_sur_0_75": len(haut),
            "debit_par_lecture_median_part_sous_0_25": round(st.median(bas), 4) if bas else None,
            "debit_par_lecture_median_part_0_25_a_0_75": round(st.median(milieu), 4) if milieu else None,
            "debit_par_lecture_median_part_sur_0_75": round(st.median(haut), 4) if haut else None,
            "rapport_haut_sur_bas": round(st.median(haut) / st.median(bas), 4) if bas and haut else None,
            "rho_part_debit": round(spearman([p for p, _ in res], [d for _, d in res]), 4)}


def par_tranches(lignes, pas_s=5.0):
    """Débit par tranche de temps (octets de chaque lecture répartis sur sa durée)."""
    fin = max(l["fin_us"] for l in lignes)
    n = int(fin / 1e6 / pas_s) + 1
    o = [0.0] * n
    for l in lignes:
        a, b = l["debut_us"] / 1e6, l["fin_us"] / 1e6
        v = l["longueur"] / (b - a)
        k = int(a / pas_s)
        while k * pas_s < b and k < n:
            o[k] += v * (min(b, (k + 1) * pas_s) - max(a, k * pas_s))
            k += 1
    return [x / pas_s / 1e9 for x in o]


def j0d(prof):
    out = {}
    for nom in ["p2a-15-lire-tout-A120", "p2a-20-lire-tout-A120"]:
        l = prof[nom]
        t = par_tranches(l, 5.0)
        t1 = par_tranches(l, 1.0)
        # plages : suites de secondes sous 0,5 Go/s
        plages, k = [], 0
        while k < len(t1):
            if t1[k] < 0.5:
                j = k
                while j < len(t1) and t1[j] < 0.5:
                    j += 1
                plages.append((k, j - k))
                k = j
            else:
                k += 1
        sec = (max(x["fin_us"] for x in l) - min(x["debut_us"] for x in l)) / 1e6
        out[nom] = {"go_s": round(sum(x["longueur"] for x in l) / sec / 1e9, 3), "par_5_s": [round(x, 2) for x in t],
                    "plages_sous_0_5_go_s_de_10_s_ou_plus": [(a, n) for a, n in plages if n >= 10],
                    "secondes_sous_0_5": sum(n for _, n in plages)}
    a = {x["indice"]: x["debit"] for x in prof["p2a-15-lire-tout-A120"]}
    b = {x["indice"]: x["debit"] for x in prof["p2a-20-lire-tout-A120"]}
    k = sorted(a)
    out["rho_entre_passes_A120"] = round(spearman([a[i] for i in k], [b[i] for i in k]), 4)
    a = {x["indice"]: x["debit"] for x in prof["p2a-17-lire-tout-C120"]}
    b = {x["indice"]: x["debit"] for x in prof["p2a-18-lire-tout-C120"]}
    out["rho_entre_passes_C120"] = round(spearman([a[i] for i in k], [b[i] for i in k]), 4)
    # A120 hors des arrêts : lectures finies dans une seconde à plus de 1 Go/s
    for nom in ["p2a-15-lire-tout-A120", "p2a-20-lire-tout-A120"]:
        l = prof[nom]
        t1 = par_tranches(l, 1.0)
        hors = [x["debit"] for x in l if all(t1[s] > 1.0 for s in range(int(x["debut_us"] / 1e6), min(len(t1), int(x["fin_us"] / 1e6) + 1)))]
        out[nom]["debit_par_lecture_median_hors_arrets"] = round(st.median(hors), 4)
        out[nom]["lectures_hors_arrets"] = len(hors)
    return out


def j0e():
    out = {}
    lb = {}
    for f in sorted(LOT_B.glob("s2-120b-*.json")):
        j = json.loads(f.read_text(encoding="utf-8"))
        lb.setdefault(nom_court(j["commande"].split("--modele ")[1].split(" ")[0]), []).append(round(j["generation_jetons_s"], 3))
    out["lot_B_s2_120b_generation"] = {k: {"passes": v, "mediane": round(st.median(v), 3)} for k, v in lb.items()}
    jc = {}
    for f in sorted(JUGE_C.glob("120b-moteur-*.json")):
        j = json.loads(f.read_text(encoding="utf-8"))
        jc.setdefault(nom_court(j["commande"].split("--modele ")[1].split(" ")[0]), []).append(round(j["generation_jetons_s"], 3))
    out["juge_construction_120b_generation"] = {k: {"passes": v, "mediane": round(st.median(v), 3)} for k, v in jc.items()}
    jd = {}
    for f in sorted(JUGE_C.glob("120b-disque-*.json")):
        j = json.loads(f.read_text(encoding="utf-8"))
        jd.setdefault(nom_court(j["fichier"]), []).append(round(j["go_s"], 3))
    out["juge_construction_120b_disque"] = jd
    return out


def j0f(a):
    """Puissance de p6 : gain prédit contre bruit des séries de bout en bout."""
    T, L = a["p3"]["s_pas_median"], a["p3"]["s_lectures_median"]
    G = lambda k: T / (T - L * (1 - 1 / k))
    jc = {}
    for f in sorted(JUGE_C.glob("20b-moteur-*.json")):
        j = json.loads(f.read_text(encoding="utf-8"))
        jc.setdefault(nom_court(j["commande"].split("--modele ")[1].split(" ")[0]), []).append(j["generation_jetons_s"])
    lb = {}
    for f in sorted(LOT_B.glob("s2-[0-9]-*.json")):
        j = json.loads(f.read_text(encoding="utf-8"))
        lb.setdefault(nom_court(j["commande"].split("--modele ")[1].split(" ")[0]), []).append(j["generation_jetons_s"])
    bruit = {"p3 A20": a["p3"]["e_soi"]["A20"], "p3 D20": a["p3"]["e_soi"]["D20"]}
    bruit.update({f"juge construction 20b {k}": round(e_soi(v), 4) for k, v in jc.items()})
    bruit.update({f"lot B s2 20b {k}": round(e_soi(v), 4) for k, v in lb.items()})
    gains = {f"k = {k}": round(G(k), 4) for k in (1.080, 1.125, 1.133, 1.147)}
    return {"T_s": T, "L_s": L, "gains_predits": gains, "e_soi_bout_en_bout": bruit,
            "seuil_2_e_soi_p3": round(2 * max(a["p3"]["e_soi"].values()), 4),
            "seuil_2_e_soi_juge_construction_A20": round(2 * e_soi(jc["A20"]), 4)}


def j0g(prof):
    """Compléments : H2 (ρ débit-LCN, bandes), H1 (un morceau contre dix et plus), H4 (trié / aléatoire),
    températures des passes A20 et B20 de p2a, débit du disque lu sur demandé (H5 a)."""
    out = {}
    for nom, l in prof.items():
        d = [x["debit"] for x in l]
        haut = [x["debit"] for x in l if x["lcn_frac"] > 0.75]
        bas = [x["debit"] for x in l if x["lcn_frac"] < 0.5]
        un = [x["debit"] for x in l if x["morceaux"] == 1]
        dix = [x["debit"] for x in l if x["morceaux"] >= 10]
        out[nom] = {"rho_lcn": round(spearman([x["lcn_frac"] for x in l], d), 4),
                    "haute_sur_basse": round(st.median(haut) / st.median(bas), 4) if haut and bas else None,
                    "un_sur_dix": round(st.median(un) / st.median(dix), 4) if un and dix else None,
                    "n_dix_et_plus": len(dix), "debit_par_lecture_median": round(st.median(d), 4)}
    s = json.loads((P / "p2a" / "seance-p2a.json").read_text(encoding="utf-8"))
    go = {}
    for p in s["passes"]:
        j = P / "p2a" / f"{p['nom']}.json"
        if j.exists():
            x = json.loads(j.read_text(encoding="utf-8"))
            go[p["nom"]] = x.get("go_s")
    out["H4"] = {}
    for f in ["A120", "B120"]:
        ale = [v for k, v in go.items() if f"-lire-disque-{f}" in k]
        tri = [v for k, v in go.items() if f"-lire-trie-{f}" in k]
        out["H4"][f] = {"aleatoire": ale, "trie": tri, "rapport": round(st.median(tri) / st.median(ale), 4)}
    temp = {}
    ratios = []
    for p in s["passes"]:
        e = p.get("smart_ecart") or {}
        if "-disque-" in p["nom"] and "lire" not in p["nom"]:
            temp.setdefault(p["nom"][-3:], []).append((e.get("temp_avant"), e.get("temp_apres")))
        j = P / "p2a" / f"{p['nom']}.json"
        if "-lire-" in p["nom"] and j.exists():
            x = json.loads(j.read_text(encoding="utf-8"))
            if x.get("octets_disque_sur_demandes"):
                ratios.append(x["octets_disque_sur_demandes"])
    out["temperatures_troncons_disque_p2a"] = temp
    out["H5a_disque_sur_demande"] = [round(min(ratios), 4), round(max(ratios), 4)] if ratios else None
    return out


def main():
    SORTIE.mkdir(parents=True, exist_ok=True)
    out = {"outil": "outils/disque/placement/juge/recalcul.py", "graine": GRAINE}
    out["J0a"] = j0a()
    noms = ["p2a-15-lire-tout-A120", "p2a-17-lire-tout-C120", "p2a-18-lire-tout-C120", "p2a-20-lire-tout-A120",
            "p2a-16-lire-tout-B120", "p2a-19-lire-tout-B120"]
    prof = {n: lire_profil(n) for n in noms}
    c = {n: prof[n] for n in noms if "C120" in n}
    out["J0b"] = j0b(c)
    out["J0c"] = {n: j0c(prof[n]) for n in noms if "C120" in n}
    # même mesure sur B120 et A120 (pas de lecture coupée de taille : témoin de l'outil, part ≈ 0)
    out["J0c_temoins"] = {n: j0c(prof[n]) for n in ["p2a-16-lire-tout-B120", "p2a-15-lire-tout-A120"]}
    # débit par lecture médian des non coupées, et × 4 (débit agrégé qu'aurait une file de quatre telles lectures)
    for n in noms:
        un = [l["debit"] for l in prof[n] if l["morceaux"] == 1]
        out.setdefault("non_coupees", {})[n] = {"n": len(un), "debit_par_lecture_median": round(st.median(un), 4),
                                                "fois_4": round(4 * st.median(un), 3)}
    out["J0d"] = j0d(prof)
    out["J0e"] = j0e()
    out["J0f"] = j0f(out["J0a"])
    out["J0g"] = j0g({n: prof[n] for n in noms})
    (SORTIE / "J0-recalcul.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    # résumé
    a = out["J0a"]
    for s in ["p2a", "p2b-D", "p2b-D2", "p2b-F", "p2b-Fb", "p2b-Fb2", "p4", "p5"]:
        print(f"{s} : médianes {a[s]['mediane']} ; e_soi {a[s]['e_soi']} ; S {a[s]['S']}")
        for k, v in a[s]["rapports"].items():
            print(f"    {k} = {v[0]} ({v[1]})")
    print("juge construction 20b :", {k: round(v, 4) for k, v in a["juge-construction-20b"]["mediane"].items()})
    print("σ_inter :", a["sigma_inter"])
    print("Fb2 F20 contre A20 :", a["Fb2_F20_contre_A20"])
    print("p3 :", {k: v for k, v in a["p3"].items() if k != "passes"})
    for k, v in a["p3"]["passes"].items():
        print("   ", k, v)
    b = out["J0b"]
    for n in c:
        print(f"H1 {n} : t1 {b[n]['t1_ms']} ms, tau {b[n]['tau_us']} µs, sous-échantillons {b[n]['sous_echantillons_N1200']}")
        for m, x in b[n]["criteres"].items():
            print(f"    {m:32s} somme {x['somme_impaires_predite_sur_mesuree']} (08 : {x['critere_08_10pc']}) ; par classe {x['erreur_mediane_par_classe']} ({x['critere_par_classe']})")
    print("T_n", b["T_n"], "T_t", b["T_t"], "T_tau", b["T_tau"])
    print("J0c :", json.dumps(out["J0c"], ensure_ascii=False))
    print("J0c témoins :", json.dumps(out["J0c_temoins"], ensure_ascii=False))
    print("non coupées :", json.dumps(out["non_coupees"], ensure_ascii=False))
    d = out["J0d"]
    for n in ["p2a-15-lire-tout-A120", "p2a-20-lire-tout-A120"]:
        print(n, {k: v for k, v in d[n].items()})
    print("rho entre passes A120", d["rho_entre_passes_A120"], "C120", d["rho_entre_passes_C120"])
    print("J0e :", json.dumps(out["J0e"], ensure_ascii=False))
    print("J0f :", json.dumps(out["J0f"], ensure_ascii=False))
    print("J0g :", json.dumps(out["J0g"], ensure_ascii=False))


if __name__ == "__main__":
    main()
