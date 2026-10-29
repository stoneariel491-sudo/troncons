"""Juge du lot « ronde » (Tome III, figures des ch. 1 à 4 et 7) : chaque nombre refait par un autre chemin.

Écrit de zéro par le juge le 2026-10-27, sans lire les scripts du lot (memoire/outils/tome3_*.py).
Il relit les journaux et CSV commités sous mesures/ (et ceux qu'ils citent), refait chaque grandeur par
son propre calcul, puis la compare à la valeur que le lot a écrite dans
memoire/figures/tome3/donnees/<lot>-nombres.csv.

Règle de comparaison, déclarée avant la première exécution :
  - entier : égalité exacte ;
  - réel : |lot − juge| ≤ 2e-5 · max(|juge|, 1e-12) (le lot écrit six chiffres significatifs) ;
  - une clé que le juge ne sait pas refaire est marquée « choix » ou « non refaite », jamais « tient ».
Témoin de l'instrument (déclaré avant) : avec --casser, chaque valeur du juge est multipliée par
1,001 ; toutes les clés réelles non nulles doivent alors tomber.

Sortie : journaux/refaire-<lot>.csv (cle, lot, juge, ecart_rel, etat, chemin) et un résumé sur la
sortie standard. Aucune écriture hors de journaux/.

Usage : python -I -X utf8 refaire.py [--casser]
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys

import numpy as np
from scipy.stats import spearmanr

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", "..", "..", ".."))
CASSER = "--casser" in sys.argv
JOURNAUX = os.path.join(ICI, "journaux")
sys.stdout.reconfigure(encoding="utf-8")


def ch(*p):
    return os.path.join(RACINE, *p)


def lj(*p):
    with open(ch(*p), encoding="utf-8") as f:
        return json.load(f)


def lc(*p):
    with open(ch(*p), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def H2(p):
    if p <= 0 or p >= 1:
        return 0.0
    return -(p * math.log2(p) + (1 - p) * math.log2(1 - p))


# --------------------------------------------------------------------------------------------------
# 1. L'éclaireur (III-1.2, III-2.1)
# --------------------------------------------------------------------------------------------------
def eclaireur():
    v = {}
    J = ("mesures", "genome", "etat-de-l-art", "journaux")
    b = lj(*J, "borne-rd.json")
    pts = b["uniforme_precis"]
    v["points-uniformes"] = (len(pts), "borne-rd.json : longueur de uniforme_precis")
    conv = [p for p in pts if p["converge"]]
    nonc = [p for p in pts if not p["converge"]]
    v["points-converges"] = (len(conv), "borne-rd.json : drapeaux converge")
    v["points-nonconverges"] = (len(nonc), "borne-rd.json : drapeaux converge")
    v["nonconv-bits-min"] = (min(p["bits"] for p in nonc), "borne-rd.json : min des bits non convergés")
    v["nonconv-bits-max"] = (max(p["bits"] for p in nonc), "borne-rd.json : max des bits non convergés")
    # H(V) refait depuis la loi publiée (et non lu dans H_v_bits)
    p = np.array(list(b["loi_v"].values()), dtype=float)
    p = p / p.sum()
    v["H-v"] = (float(-(p * np.log2(p)).sum()), "borne-rd.json : −Σ p log2 p sur loi_v (15 valeurs)")
    zt = lj(*J, "zero-temoin-sans-drapeau.json")
    zc = lj(*J, "zero-canonique.json")
    fb = zt["bpp"]["niveau0_base"]
    v["frontiere-bits"] = (fb, "zero-temoin-sans-drapeau.json : bpp.niveau0_base")
    v["canonique-bits"] = (zc["bpp"]["niveau0_base"], "zero-canonique.json : bpp.niveau0_base")
    fe = zc["erreur_base_commune"]
    # second chemin de l'erreur : frontiere.json de l'équipe genome (recompte des 12 tenseurs entiers)
    fr = lj("mesures", "genome", "genome", "frontiere.json")
    fe2 = None
    for k in ("erreur", "erreur_relative", "erreur_frontiere", "erreur_recomptee"):
        if isinstance(fr.get(k), (int, float)):
            fe2 = fr[k]
    v["frontiere-d-pct"] = (100 * fe, f"zero-canonique.json : 100 × erreur_base_commune (frontiere.json : {fe2})")
    # cordes : partage du temps entre deux itérés (linéaire en D, D étant une moyenne d'erreur quadratique)
    P = sorted((q["D"], q["bits"]) for q in pts)
    Ds = np.array([a for a, _ in P])
    Bs = np.array([c for _, c in P])
    corde_b = float(np.interp(fe, Ds, Bs))
    Q = sorted((q["bits"], q["D"]) for q in pts)
    corde_d = float(np.interp(fb, np.array([a for a, _ in Q]), np.array([c for _, c in Q])))
    v["corde-bits-a-d"] = (corde_b, "borne-rd.json : interpolation linéaire en D entre itérés voisins, à D = frontière")
    v["corde-d-pct-a-r"] = (100 * corde_d, "borne-rd.json : interpolation linéaire en bits entre itérés voisins, au débit frontière")
    v["ecart-bits"] = (fb - corde_b, "calculé : frontiere-bits − corde-bits-a-d")
    v["part-erreur"] = (100 * corde_d / (100 * fe), "calculé : corde-d / frontiere-d")
    # 20b et 120b
    for m in ("20b", "120b"):
        z = lj(*J, f"zero-compte-{m}.json")
        t = z["par_tenseur"]
        v[f"{m}-tenseurs"] = (len(t), f"zero-compte-{m}.json : longueur de par_tenseur")
        couches = {int(x["tenseur"].split(".")[1]) for x in t}
        v[f"{m}-couches"] = (len(couches), f"zero-compte-{m}.json : couches distinctes des noms")
        poids = sum(x["poids"] for x in t)
        v[f"{m}-poids"] = (int(poids), f"zero-compte-{m}.json : Σ poids par tenseur")
        # coût refait : p0 × H(signe | zéro), pondéré par les poids
        cout_t = [(x["p_plus0"] + x["p_moins0"]) * H2(x["p_plus0"] / (x["p_plus0"] + x["p_moins0"])) for x in t]
        v[f"{m}-cout"] = (sum(c * x["poids"] for c, x in zip(cout_t, t)) / poids,
                          f"zero-compte-{m}.json : Σ poids·p0·H2(p+/p0) / Σ poids (refait)")
        v[f"{m}-cout-min"] = (min(cout_t), f"zero-compte-{m}.json : min par tenseur de p0·H2 (refait)")
        v[f"{m}-cout-max"] = (max(cout_t), f"zero-compte-{m}.json : max par tenseur de p0·H2 (refait)")
        pp = sum(x["p_plus0"] * x["poids"] for x in t) / poids
        pm = sum(x["p_moins0"] * x["poids"] for x in t) / poids
        v[f"{m}-p-plus"] = (100 * pp, f"zero-compte-{m}.json : part pondérée des +0 (refaite)")
        v[f"{m}-p-moins"] = (100 * pm, f"zero-compte-{m}.json : part pondérée des −0 (refaite)")
        v[f"{m}-H-signe"] = (H2(pp / (pp + pm)), f"zero-compte-{m}.json : H2(p+/p0) global (refait)")
        v[f"{m}-H-signe-min"] = (min(H2(x["p_plus0"] / (x["p_plus0"] + x["p_moins0"])) for x in t),
                                 f"zero-compte-{m}.json : min par tenseur de H2 (refait)")
        v[f"{m}-blocs-nuls"] = (int(sum(x["blocs_tout_zero"] for x in t)), f"zero-compte-{m}.json : Σ blocs_tout_zero")
        v[f"{m}-blocs"] = (int(poids // 32), f"zero-compte-{m}.json : Σ poids / 32")
    return v


# --------------------------------------------------------------------------------------------------
# 2. La synthèse (III-7.1 à III-7.4), refaite depuis les journaux d'origine et non depuis frontiere.csv
# --------------------------------------------------------------------------------------------------
def synthese():
    v = {}
    E = ("mesures", "genome", "etat-de-l-art")
    jb = lj(*E, "journaux", "kl-frontiere-juge.json")["resume"]
    js = lj(*E, "journaux", "kl-synonyme-d1-juge.json")["resume"]
    fr8 = lj(*E, "passes", "frontiere-lam0-damp0.01.json")
    s0 = lj(*E, "passes", "synonyme-lam0-damp1.json")
    s1 = lj(*E, "passes", "synonyme-lam1-damp1-e0_8_16_24.json")
    fr4 = lj(*E, "passes", "frontiere-lam0-damp0.01-e0_8_16_24.json")
    v["p1-base-bits"] = (fr8["bits_H0_sym"], "passes/frontiere-lam0-damp0.01.json : bits_H0_sym")
    v["p1-base-rapport"] = (1.0, "définition")
    v["p1-syn-bits"] = (s0["bits_H0_sym"], "passes/synonyme-lam0-damp1.json : bits_H0_sym")
    # rapport refait depuis les positions (moyennes) et non lu dans les juges
    pb = lc(*E, "journaux", "kl-frontiere-positions.csv")
    ps = lc(*E, "journaux", "kl-synonyme-d1-positions.csv")
    kb = np.array([float(r["kl"]) for r in pb])
    ks = np.array([float(r["kl"]) for r in ps])
    assert all((a["fenetre"], a["position"]) == (c["fenetre"], c["position"]) for a, c in zip(pb, ps))
    v["p1-syn-rapport"] = (ks.mean() / kb.mean(), "kl-*-positions.csv : moyenne synonyme / moyenne base")
    v["syn-rapport"] = v["p1-syn-rapport"]
    v["s-lam1-bits"] = (s1["bits_H0_sym"], "passes/synonyme-lam1-damp1-e0_8_16_24.json : bits_H0_sym")
    v["s-baselam1-bits"] = (fr4["bits_H0_sym"], "passes/frontiere-lam0-damp0.01-e0_8_16_24.json : bits_H0_sym")
    zt = lj(*E, "journaux", "zero-temoin-sans-drapeau.json")
    v["p2-base-bits"] = (round(zt["bpp"]["niveau0_base"], 4), "zero-temoin-sans-drapeau.json : niveau0_base, 4 décimales (frontiere.py l'écrit 2,6441 en dur)")
    v["p2-base-rapport"] = (1.0, "définition")
    v["p2-sstar-bits"] = (2.64, "débit cible de S* (fichier kl10-recette-ponderee-exc-264 ; frontiere.py l'écrit en dur)")
    c10 = lj("mesures", "genome", "genome", "kl", "comparer10-base-contre-recette.json")
    v["p2-sstar-rapport"] = (c10["b_contre_verite"]["kl_moyenne"] / c10["a_contre_verite"]["kl_moyenne"],
                             "comparer10-base-contre-recette.json : b / a")
    v["sstar-rapport"] = v["p2-sstar-rapport"]
    v["sstar-apparie"] = (c10["apparie"]["kl_difference_b_moins_a"], "comparer10 : apparie.kl_difference_b_moins_a")
    v["sstar-apparie-sigma"] = (c10["apparie"]["kl_ecart_type"], "comparer10 : apparie.kl_ecart_type")
    res = {r["plan"]: r for r in lc("mesures", "genome", "predictif-elagage", "resume-12.csv")}
    kb3 = float(res["base"]["kl_moyenne"])
    v["p3-base-bits"] = (float(res["base"]["bits_reels"]), "resume-12.csv : base")
    v["p3-base-rapport"] = (1.0, "définition")
    plans = {"kappat": "ecsq_kappa_t", "kappa": "ecsq_kappa", "hebbdlc": "hebb_d_lc", "hebbe": "hebb_e",
             "hebbelc": "hebb_e_lc", "partse": "ecsq_e", "elag": "sens_e_q"}
    for k, plan in plans.items():
        v[f"p3-{k}-bits"] = (float(res[plan]["bits_reels"]), f"resume-12.csv : {plan}.bits_reels")
        v[f"p3-{k}-rapport"] = (float(res[plan]["kl_moyenne"]) / kb3, f"resume-12.csv : {plan}.kl / base.kl")
    vw = lj("mesures", "genome", "genome", "verdict-tourne-l12-second-chemin.json")["tenseurs"]
    v["s-brin-bits"] = (float(np.mean([t["bits_recette"] for t in vw])), "verdict-tourne-l12-second-chemin.json : moyenne bits_recette")
    vs = lj("mesures", "genome", "genome", "verdict-fidelite-sstar.json")["par_expert"]
    v["s-sstar-bits"] = (float(np.mean([t["bits_a_sortie_egale"] for t in vs])), "verdict-fidelite-sstar.json : moyenne bits_a_sortie_egale")
    dup = lj("mesures", "genome", "duplication", "verdicts.json")
    v["s-d2b-bits"] = (dup["D2b"]["debit_base_avec_parent"], "duplication/verdicts.json : D2b.debit_base_avec_parent")
    v["s-graine-bits"] = (3.06, "genome/genome.md § 2.3 (valeur du livrable, interpolée ; non refaite ici)")
    v["s-motifs-bits"] = (2.90, "genome/genome.md § 8.1 (valeur du livrable, interpolée ; non refaite ici)")
    k10 = lc("mesures", "genome", "construction", "synthese", "k10", "frontiere.csv")
    v["points-total"] = (len(k10), "k10/frontiere.csv : lignes")
    v["points-kl"] = (2 + 2 + 8, "compte : P1 (2), P2-10 (2), P3 (8) ; P2 à 3 fenêtres écarté (R4)")
    v["points-sans-kl"] = (sum(1 for r in k10 if r["kl_moyenne"] == "" ), "k10/frontiere.csv : lignes sans KL")
    tr = lj("mesures", "genome", "predictif-elagage", "taux-reel-colonne-12-gptoss20b.json")
    tt = tr["tenseurs"]
    v["sans-perte"] = (float(np.mean([t["bpp_total_identite"] for t in tt])), "taux-reel-colonne : moyenne des 12 bpp_total_identite")
    v["codon"] = (float(np.mean([t["bpp_total_zero_fondu"] for t in tt])), "taux-reel-colonne : moyenne des 12 bpp_total_zero_fondu")
    v["colonne"] = (float(np.mean([t["bpp_total_nib_kappa_colonne"] for t in tt])), "taux-reel-colonne : moyenne des 12 bpp_total_nib_kappa_colonne")
    v["d1"] = (tr["bpp"]["total_identite"] - dup["D1"]["gain_net_moyen"] + dup["D1"]["cout_ajoute"],
               "taux-reel total_identite − D1.gain_net_moyen + D1.cout_ajoute")
    v["syn-ecart-bits"] = (s0["bits_H0_sym"] - fr8["bits_H0_sym"], "calculé")
    v["seuil-colonne"] = (0.015, "règle déclarée (05 § 0 et frontiere.py) ; non refaite")
    v["kappa-t-bits"] = v["p3-kappat-bits"]
    v["kappa-t-part-bits"] = (float(res["ecsq_kappa_t"]["bits_reels"]) / float(res["base"]["bits_reels"]), "calculé")
    rapports = [v[f"p3-{k}-rapport"][0] for k in plans] + [v["p1-syn-rapport"][0], v["p2-sstar-rapport"][0]]
    v["rapport-max"] = (max(rapports), "max des rapports tracés")
    gain = [t["bpp_total_zero_fondu"] - t["bpp_total_nib_kappa_colonne"] for t in tt]
    v["colonne-retenues"] = (sum(1 for g in gain if g >= 0.015), "taux-reel-colonne : gain octet − colonne ≥ 0,015")
    v["colonne-seuil-moyen"] = (float(np.mean([t["bpp_total_nib_kappa_colonne"] if g >= 0.015 else t["bpp_total_zero_fondu"]
                                               for t, g in zip(tt, gain)])), "calculé : règle des 0,015 bit")
    v["colonne-perd"] = (sum(1 for g in gain if g < 0), "taux-reel-colonne : colonne > codon en octets")
    # erreur d'expert contre KL
    x_syn = s0["err_sortie_expert_eval"] / fr8["err_sortie_expert_eval"]
    v["ek-syn-x"] = (round(x_syn, 4), "passes : err_sortie_expert_eval synonyme / frontière (4 décimales comme le CSV)")
    v["ek-syn-y"] = (round(js["kl_moyenne"] / jb["kl_moyenne"], 4), "juges : kl_moyenne synonyme / base")
    xs = float(np.mean([t["erreur_sortie_a_2_64"] / t["erreur_sortie_base"] for t in vs]))
    c3 = lj("mesures", "genome", "genome", "kl", "comparer-base-contre-recette.json")
    v["ek-sstar3-x"] = (round(xs, 4), "verdict-fidelite-sstar.json : moyenne des rapports à 2,64 bits")
    v["ek-sstar3-y"] = (round(c3["b_contre_verite"]["kl_moyenne"] / c3["a_contre_verite"]["kl_moyenne"], 4), "comparer (3 fenêtres) : b / a")
    v["ek-sstar10-x"] = (round(xs, 4), "idem (mêmes 8 experts)")
    v["ek-sstar10-y"] = (round(v["p2-sstar-rapport"][0], 4), "comparer10 : b / a")
    eb = float(res["base"]["erreur_expert_mesuree"])
    for k, plan in (("kappa", "ecsq_kappa"), ("hebbe", "hebb_e"), ("hebbelc", "hebb_e_lc"), ("partse", "ecsq_e")):
        v[f"ek-{k}-x"] = (round(float(res[plan]["erreur_expert_mesuree"]) / eb, 4), f"resume-12.csv : {plan} erreur_expert / base")
        v[f"ek-{k}-y"] = (round(float(res[plan]["kl_moyenne"]) / kb3, 4), f"resume-12.csv : {plan} kl / base")
    bande = [(v["ek-sstar10-x"][0], v["ek-sstar10-y"][0]), (v["ek-kappa-x"][0], v["ek-kappa-y"][0]),
             (v["ek-hebbe-x"][0], v["ek-hebbe-y"][0])]
    tous = bande + [(v["ek-syn-x"][0], v["ek-syn-y"][0]), (v["ek-hebbelc-x"][0], v["ek-hebbelc-y"][0]),
                    (v["ek-partse-x"][0], v["ek-partse-y"][0])]
    dans = [p for p in tous if 0.74 <= p[0] <= 1.03]
    v["bande-n"] = (len(dans), "points tenus dont l'abscisse est dans [0,74 ; 1,03] (05 § 2.1 c)")
    v["bande-x-min"] = (min(p[0] for p in dans), "calculé")
    v["bande-x-max"] = (max(p[0] for p in dans), "calculé")
    v["bande-y-min"] = (min(p[1] for p in dans), "calculé")
    v["bande-y-max"] = (max(p[1] for p in dans), "calculé")
    # III-7.3
    v["positions"] = (len(kb), "kl-frontiere-positions.csv : lignes")
    v["fenetres"] = (len({r["fenetre"] for r in pb}), "kl-frontiere-positions.csv : fenêtres distinctes")
    v["sous-plancher"] = (int((kb < 1e-5).sum() + (ks < 1e-5).sum()), "positions : KL < 1e-5, deux séries")
    v["plancher"] = (1e-5, "choix d'axe (non refait)")
    v["med-base"] = (float(np.median(kb)), "positions : médiane (numpy)")
    v["med-syn"] = (float(np.median(ks)), "positions : médiane (numpy)")
    v["med-rapport"] = (float(np.median(kb) / np.median(ks)), "calculé")
    v["moy-base"] = (float(kb.mean()), "positions : moyenne")
    v["moy-syn"] = (float(ks.mean()), "positions : moyenne")
    v["moy-rapport"] = (float(kb.mean() / ks.mean()), "calculé")
    v["p999-base"] = (jb["kl_p999"], "kl-frontiere-juge.json : kl_p999 (le quantile du juge)")
    v["p999-syn"] = (js["kl_p999"], "kl-synonyme-d1-juge.json : kl_p999")
    n = len(kb)
    for nom, arr in (("base", kb), ("syn", ks)):
        tri = np.sort(arr)[::-1]
        for pct, cle in ((0.01, "1pct"), (0.10, "10pct")):
            k = int(math.ceil(pct * n))
            v[f"part-{cle}-{nom}"] = (float(tri[:k].sum() / arr.sum()), f"positions : part de la somme portée par les ⌈{pct:g}·n⌉ = {k} plus grandes")
    v["positions-gagnees"] = (int((ks < kb).sum()), "positions : KL synonyme < KL base")
    # III-7.4
    cc = lc("mesures", "genome", "genome", "csv", "colonnes-energie-erreur.csv")
    en = np.array([float(r["energie_exacte"]) for r in cc])
    eb_ = np.array([float(r["erreur_brin_pondere"]) for r in cc])
    es = np.array([float(r["erreur_s_etoile"]) for r in cc])
    ebase = np.array([float(r["erreur_base"]) for r in cc])
    g = int(np.argmax(en))
    v["col-massive"] = (int(cc[g]["colonne"]), "colonnes-energie-erreur.csv : argmax energie_exacte")
    v["col-n"] = (len(cc), "colonnes-energie-erreur.csv : lignes")
    v["col-energie-x"] = (float(en[g] / en.mean()), "calculé : énergie / moyenne")
    v["col-brin-x"] = (float(eb_[g] / eb_.mean()), "calculé : erreur_brin_pondere / moyenne")
    v["col-sstar-x"] = (float(es[g] / es.mean()), "calculé : erreur_s_etoile / moyenne")
    v["col-base-x"] = (float(ebase[g] / ebase.mean()), "calculé : erreur_base / moyenne")
    idx = np.arange(len(cc))
    bord = (idx % 64 == 0) & (idx != g)
    v["col-bord-x"] = (float(eb_[bord].mean() / eb_.mean()), "calculé : moyenne des colonnes ≡ 0 mod 64 / moyenne de toutes")
    m0 = (g // 64) * 64
    v["col-morceau-debut"] = (m0, "calculé : morceau de 64 de la colonne géante")
    v["col-morceau-fin"] = (m0 + 63, "calculé")
    mor = (idx >= m0) & (idx <= m0 + 63) & (idx != g)
    v["col-morceau-x"] = (float(eb_[mor].mean() / eb_.mean()), "calculé : autres colonnes du morceau / moyenne")
    return v


# --------------------------------------------------------------------------------------------------
# 3. Le génome (III-3.4, III-3.6)
# --------------------------------------------------------------------------------------------------
def genome():
    v = {}
    G = ("mesures", "genome", "genome")
    L = [json.loads(l) for l in open(ch(*G, "gauss-balayage.jsonl"), encoding="utf-8") if l.strip()]

    def db(m, kb_, vv):
        return 10 * math.log10(m / 2 ** (-2 * kb_ / vv))

    formes = {}
    for d in L:
        if d["melangeur"] == "fort" and d["lloyd"] == 0 and d["q"] == 8 and d["l"] in (12, 16):
            if d["l"] == 16 or d["l"] == 12:
                formes.setdefault(d["l"], {})[(d["kb"], d["v"])] = d
    for l in (12, 16):
        F = formes[l]
        # les sept formes ; à 2 bits (2,1) la ligne de la fenêtre sert aussi de forme
        v[f"g-l{l}-formes"] = (len(F), "gauss-balayage.jsonl : formes distinctes (fort, q = 8, sans Lloyd)")
        dbs = {k: db(d["mse"], k[0], k[1]) for k, d in F.items()}
        v[f"g-l{l}-db-min"] = (min(dbs.values()), "calculé : 10 log10(mse / 2^(−2 kb/v))")
        v[f"g-l{l}-db-max"] = (max(dbs.values()), "calculé")
        for (kb_, vv), x in dbs.items():
            v[f"g-l{l}-{kb_}-{vv}-db"] = (x, "calculé")
            v[f"g-l{l}-{kb_}-{vv}-r"] = (kb_ / vv, "kb / v")
    for d in L:
        if d["kb"] == 2 and d["v"] == 1 and d["melangeur"] == "fort" and d["lloyd"] == 0 and d["q"] == 8:
            v[f"g-fen-{d['l']}"] = (d["mse"], "gauss-balayage.jsonl")
        if d["l"] == 12 and d["kb"] == 2:
            if d["melangeur"] == "court":
                v["g-var-court"] = (d["mse"], "gauss-balayage.jsonl")
                v["g-var-court-db"] = (db(d["mse"], 2, 1), "calculé")
            if d["lloyd"] == 3:
                v["g-var-lloyd3"] = (d["mse"], "gauss-balayage.jsonl")
                v["g-var-lloyd3-db"] = (db(d["mse"], 2, 1), "calculé")
            if d["q"] in (6, 10):
                v[f"g-var-q{d['q']}"] = (d["mse"], "gauss-balayage.jsonl")
                v[f"g-var-q{d['q']}-db"] = (db(d["mse"], 2, 1), "calculé")
    t1 = json.loads(open(ch(*G, "gauss-T1.json"), encoding="utf-8").read().strip().splitlines()[0])
    v["g-t1"] = (t1["mse"], "gauss-T1.json")
    v["g-t1-db"] = (db(t1["mse"], 2, 1), "calculé")
    v["g-t1-rangees"] = (t1["rangees"], "gauss-T1.json")
    rg = sorted({d["rangees"] for d in L})
    v["g-rangees"] = (rg[-1], f"gauss-balayage.jsonl : rangées distinctes {rg} (la légende n'en dit qu'une)")
    v["g-longueur"] = (sorted({d["poids"] // d["rangees"] for d in L})[0], "poids / rangées")
    v["g-shannon-2"] = (2 ** -4, "2^(−2·2)")
    v["g-q"] = (8, "q des formes")
    # III-3.6 : le verdict, et un second chemin du débit à erreur égale par la courbe elle-même
    vt = lc(*G, "csv", "verdict-par-tenseur.csv")
    ct = lc(*G, "csv", "courbes-tourne-l12.csv")
    gains = []
    manque = 0
    for r in vt:
        c = int(r["tenseur"].split(".")[1])
        role = r["tenseur"].split(".")[2].split("_")[1]
        base_b = float(r["bits_frontiere"])
        err = float(r["erreur_base"])
        # bits du brin tourné à l'erreur de la base : le plus petit débit de la courbe dont l'erreur
        # descend à err, par interpolation linéaire entre les deux points qui l'encadrent (courbe triée)
        pts = sorted((float(x["bits"]), float(x["erreur"])) for x in ct if x["tenseur"] == r["tenseur"])
        bt = None
        for (b1, e1), (b2, e2) in zip(pts, pts[1:]):
            if e1 >= err >= e2 and e1 != e2:
                bt = b1 + (err - e1) * (b2 - b1) / (e2 - e1)
                break
        v[f"v-{c}-{role}-bits"] = (base_b, "verdict-par-tenseur.csv : bits_frontiere")
        v[f"v-{c}-{role}-err"] = (err, "verdict-par-tenseur.csv : erreur_base")
        v[f"v-{c}-{role}-tourne"] = (float(r["bits_tourne"]), f"verdict-par-tenseur.csv : bits_tourne (courbe interpolée : {bt:.5f})")
        v[f"v-{c}-{role}-gain"] = (base_b - float(r["bits_tourne"]), "calculé : bits_frontiere − bits_tourne")
        gains.append(base_b - float(r["bits_tourne"]))
        if r["bits_brut"] in ("nan", "", "NaN"):
            manque += 1
    v["v-gain-moyen"] = (float(np.mean(gains)), "calculé")
    v["v-gain-min"] = (min(gains), "calculé")
    v["v-gain-max"] = (max(gains), "calculé")
    v["v-tenseurs"] = (len(vt), "verdict-par-tenseur.csv : lignes")
    v["v-brut-manquants"] = (manque, "verdict-par-tenseur.csv : bits_brut = nan")
    cb = lc(*G, "csv", "courbes-brut-l12.csv")
    v["c-tourne-points"] = (sum(1 for x in ct if x["tenseur"] != "global"), "courbes-tourne-l12.csv hors « global »")
    v["c-brut-points"] = (sum(1 for x in cb if x["tenseur"] != "global"), "courbes-brut-l12.csv hors « global »")
    return v


# --------------------------------------------------------------------------------------------------
# 4. La duplication (III-4.2, III-4.8)
# --------------------------------------------------------------------------------------------------
def duplication():
    v = {}
    D = ("mesures", "genome", "duplication")
    S = lc(*D, "csv", "scores-parente.csv")
    for genre in ("intra", "voisine", "meme_indice"):
        s = [float(r["score_bits"]) for r in S if r["genre"] == genre]
        v[f"s-{genre}-n"] = (len(s), "scores-parente.csv")
        v[f"s-{genre}-max"] = (max(s), "scores-parente.csv")
        v[f"s-{genre}-med"] = (float(np.median(s)), "scores-parente.csv : médiane (numpy)")
    allsc = [float(r["score_bits"]) for r in S]
    v["s-n"] = (len(S), "scores-parente.csv : lignes")
    couches = sorted({int(r["couche"]) for r in S})
    v["s-couches"] = (len(couches), "scores-parente.csv")
    for i, c in enumerate(couches):
        v[f"s-couche-{i}"] = (c, "scores-parente.csv")
    enf = {(r["couche"], r["enfant"]) for r in S}
    v["s-enfants"] = (len(enf) // len(couches), "scores-parente.csv : enfants par couche")
    v["s-max"] = (max(allsc), "scores-parente.csv")
    v["s-min"] = (min(allsc), "scores-parente.csv")
    t = lj(*D, "paires-temoin-planter-0.5.json")
    v["t-hasard"] = (float(np.mean([p["score_bits"] for p in t["temoin_hasard"]])), "planter-0.5 : moyenne des témoins de hasard (refaite)")
    rho = t["temoin_planter"]["rho0"]
    v["t-plante-attendu"] = (-0.5 * math.log2(1 - rho ** 2), "calculé : −½ log2(1 − ρ²)")
    v["t-plante-mesure"] = (t["temoin_planter"]["score_0_1"], "planter-0.5 : score_0_1")
    v["t-rho"] = (rho, "planter-0.5 : rho0")
    v["t-couche"] = (t["arguments"]["couche"], "planter-0.5 : arguments.couche")
    v["s-sur-hasard"] = (max(allsc) / v["t-hasard"][0], "calculé")
    v["s-sous-plante"] = (v["t-plante-attendu"][0] / max(allsc), "calculé")
    par = {}
    for r in S:
        par.setdefault((r["couche"], r["enfant"], r["genre"]), 0)
        par[(r["couche"], r["enfant"], r["genre"])] += 1
    v["s-par-voisine"] = (max(n for (c, e, g), n in par.items() if g == "voisine"), "scores-parente.csv : candidats voisins par enfant")
    v["s-par-intra"] = (max(n for (c, e, g), n in par.items() if g == "intra"), "scores-parente.csv : candidats intra par enfant")
    # l'arbre, refait depuis les 496 paires (Kruskal écrit ici) et la MDS refaite
    a = lj(*D, "arbre-c23.json")
    n = 32
    Sm = np.zeros((n, n))
    for p in a["paires"]:
        Sm[p["i"], p["j"]] = Sm[p["j"], p["i"]] = p["score_bits"]
    paires = sorted(((Sm[i, j], i, j) for i in range(n) for j in range(i + 1, n)), reverse=True)
    pere = list(range(n))

    def racine(x):
        while pere[x] != x:
            pere[x] = pere[pere[x]]
            x = pere[x]
        return x

    arbre = []
    for s, i, j in paires:
        ri, rj = racine(i), racine(j)
        if ri != rj:
            pere[ri] = rj
            arbre.append((i, j, s))
    deg = np.zeros(n, dtype=int)
    for i, j, s in arbre:
        deg[i] += 1
        deg[j] += 1
    ref = {tuple(sorted((e["i"], e["j"]))) for e in a["arbre"]}
    mien = {tuple(sorted((i, j))) for i, j, s in arbre}
    v["a-experts"] = (n, "arbre-c23.json")
    v["a-aretes"] = (len(arbre), f"Kruskal refait ; mêmes arêtes que arbre-c23.json : {ref == mien}")
    v["a-paires"] = (len(a["paires"]), "arbre-c23.json : paires")
    smax = Sm.max()
    Dm = np.zeros((n, n))
    iu = np.triu_indices(n, 1)
    Dm[iu] = np.log2(smax / Sm[iu])
    Dm = Dm + Dm.T
    Jc = np.eye(n) - 1.0 / n
    B = -0.5 * Jc @ (Dm ** 2) @ Jc
    w, V = np.linalg.eigh(B)
    o = np.argsort(w)[::-1]
    w, V = w[o], V[:, o]
    X = V[:, :2] * np.sqrt(np.maximum(w[:2], 0))
    part = float(np.maximum(w[:2], 0).sum() / np.maximum(w, 0).sum())
    Ep = np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(-1))
    v["a-variance"] = (part, "MDS classique refaite : Σ 2 premières valeurs propres positives / Σ positives")
    v["a-spearman"] = (float(spearmanr(Dm[iu], Ep[iu]).statistic), "Spearman refait (plan contre d)")
    v["a-temoin"] = (lj(*D, "phylogenie-c23.json")["temoin_distances_permutees"], "phylogenie-c23.json (une seule permutation ; non refait au bit, voir journaux/temoin-mds.csv)")
    v["a-smax"] = (float(smax), "arbre-c23.json : max des paires")
    poids_deg = np.zeros(n)
    for i, j, s in arbre:
        poids_deg[i] += s
        poids_deg[j] += s
    ex_aequo = [int(k) for k in np.nonzero(deg == deg.max())[0]]
    moyeu = max(ex_aequo, key=lambda k: poids_deg[k])
    v["a-moyeu"] = (moyeu, f"Kruskal refait : degré maximal {int(deg.max())} PARTAGÉ par {ex_aequo} ; "
                           f"{moyeu} a la plus grande somme d'arêtes ({poids_deg[moyeu]:.4f} bit)")
    v["a-moyeu-degre"] = (int(deg.max()), "Kruskal refait")
    v["a-score-min"] = (round(min(s for i, j, s in arbre), 5), "Kruskal refait : arête la plus faible (5 décimales comme le CSV)")
    v["a-feuilles"] = (int((deg == 1).sum()), "Kruskal refait : degré 1")
    i, j, s = max(arbre, key=lambda e: e[2])
    v["a-max-i"] = (min(i, j), "Kruskal refait : arête la plus lourde")
    v["a-max-j"] = (max(i, j), "Kruskal refait : arête la plus lourde")
    # le témoin MDS, sur 200 permutations (sa dispersion, que la légende ne dit pas)
    rng = np.random.default_rng(20261027)
    rs = []
    for _ in range(200):
        vv = Dm[iu].copy()
        rng.shuffle(vv)
        Dp = np.zeros((n, n))
        Dp[iu] = vv
        Dp = Dp + Dp.T
        Bp = -0.5 * Jc @ (Dp ** 2) @ Jc
        wp, Vp = np.linalg.eigh(Bp)
        op = np.argsort(wp)[::-1]
        Xp = Vp[:, op[:2]] * np.sqrt(np.maximum(wp[op[:2]], 0))
        Eq = np.sqrt(((Xp[:, None, :] - Xp[None, :, :]) ** 2).sum(-1))
        rs.append(spearmanr(Dm[iu], Eq[iu]).statistic)
    os.makedirs(JOURNAUX, exist_ok=True)
    with open(os.path.join(JOURNAUX, "temoin-mds.csv"), "w", encoding="utf-8", newline="") as f:
        f.write("graine,permutations,moyenne,ecart_type,q05,q95\n")
        f.write(f"20261027,200,{np.mean(rs):.4f},{np.std(rs):.4f},{np.quantile(rs, 0.05):.4f},{np.quantile(rs, 0.95):.4f}\n")
    return v


# --------------------------------------------------------------------------------------------------
# Ce que la légende imprime : les usages \<préfixe>Nombre[options]{cle}, \<préfixe>Entier{cle},
# \<préfixe>Pct[p]{cle} lus dans le .tex du lot ; une clé qui ne tient pas au 2e-5 près est rejugée
# à la précision où elle est imprimée (arrondi au plus proche, demi vers le haut, comme pgf).
PREFIXES = {"eclaireur": "ecl", "synthese": "synth", "genome": "gen", "duplication": "dup"}
PCT_DEFAUT = {"synth": 0, "gen": 1, "dup": 1, "ecl": 1}


def usages(lot):
    import re
    px = PREFIXES[lot]
    texte = open(ch("memoire", "figures", "tome3", f"{lot}-figures.tex"), encoding="utf-8").read()
    u = {}
    for m in re.finditer(r"\\" + px + r"(Nombre|Entier|Pct|Val)(\[[^\]]*\])?\{([^}]+)\}", texte):
        genre, opt, cle = m.group(1), m.group(2) or "", m.group(3)
        if "#" in cle:
            continue
        if genre == "Entier":
            p, f = 0, 1.0
        elif genre == "Pct":
            p = int(opt.strip("[]")) if opt.strip("[]").isdigit() else PCT_DEFAUT[px]
            f = 100.0
        elif genre == "Nombre":
            mm = re.search(r"precision=(\d+)", opt)
            p, f = (int(mm.group(1)) if mm else 2), 1.0
        else:
            p, f = None, 1.0
        u.setdefault(cle, set()).add((genre, p, f))
    # usages par macro à paramètre (#1-...) : les clés v-<c>-<rôle>-*, <modèle>-* sont imprimées par
    # \GenPanneau et \EclZeros ; on les ajoute à la main d'après le .tex
    if lot == "genome":
        for c in (0, 8, 16, 23):
            for r in ("gate", "up", "down"):
                u.setdefault(f"v-{c}-{r}-gain", set()).add(("Nombre", 2, 1.0))
                for s in ("bits", "err", "tourne"):
                    u.setdefault(f"v-{c}-{r}-{s}", set()).add(("Val", None, 1.0))
    if lot == "eclaireur":
        for m_ in ("20b", "120b"):
            u.setdefault(f"{m_}-cout", set()).add(("Nombre", 4, 1.0))
            # imprimée à 9 décimales depuis la correction du juge (commit 2824930 ; 7 avant, arrondie
            # au-dessus du minimum vrai : la borne « ≥ » était fausse)
            u.setdefault(f"{m_}-H-signe-min", set()).add(("Nombre", 9, 1.0))
            u.setdefault(f"{m_}-tenseurs", set()).add(("Entier", 0, 1.0))
            u.setdefault(f"{m_}-poids", set()).add(("Entier", 0, 1.0))
    if lot == "synthese":
        for k in ("p3-kappa", "p3-hebbdlc", "p3-hebbe", "p3-hebbelc", "p3-partse", "p3-elag", "p3-kappat"):
            u.setdefault(f"{k}-bits", set()).add(("Val", None, 1.0))
            u.setdefault(f"{k}-rapport", set()).add(("Val", None, 1.0))
        for k in ("syn", "sstar3", "sstar10", "kappa", "hebbe", "hebbelc", "partse"):
            u.setdefault(f"ek-{k}-x", set()).add(("Val", None, 1.0))
            u.setdefault(f"ek-{k}-y", set()).add(("Val", None, 1.0))
    return u


def arrondi(x, p):
    from decimal import Decimal, ROUND_HALF_UP
    return Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-p), rounding=ROUND_HALF_UP)


def comparer(lot, valeurs):
    lignes = lc("memoire", "figures", "tome3", "donnees", f"{lot}-nombres.csv")
    U = usages(lot)
    sortie = []
    bilan = {"tient": 0, "tient à l'impression": 0, "tombe": 0, "choix": 0, "non refaite": 0, "jamais utilisée": 0}
    for r in lignes:
        cle, val = r["cle"], float(r["valeur"])
        if cle not in valeurs:
            sortie.append([cle, r["valeur"], "", "", "non refaite", ""])
            bilan["non refaite"] += 1
            continue
        j, chemin = valeurs[cle]
        j = float(j) * (1.001 if CASSER else 1.0)
        if "choix" in chemin or "non refaite" in chemin or "définition" in chemin or "règle déclarée" in chemin \
                or "valeur du livrable" in chemin or "débit cible" in chemin:
            etat = "choix"
        else:
            entier = float(val).is_integer() and float(j).is_integer() and abs(j) >= 1
            if entier:
                etat = "tient" if val == j else "tombe"
            else:
                etat = "tient" if abs(val - j) <= 2e-5 * max(abs(j), 1e-12) else "tombe"
        imp = []
        for genre, p, fct in sorted(U.get(cle, set()), key=str):
            if p is None:
                imp.append("coordonnée")
                continue
            a, b = arrondi(val * fct, p), arrondi(j * fct, p)
            imp.append(f"{genre}[{p}] {a}{'=' if a == b else '≠'}{b}")
            if etat == "tombe" and a == b:
                etat = "tient à l'impression"
            if etat in ("tient", "tient à l'impression") and a != b:
                etat = "tombe"
        if not U.get(cle):
            imp.append("jamais utilisée dans le .tex")
            if etat in ("tient", "tient à l'impression"):
                etat = "jamais utilisée"
        ec = "" if j == 0 else f"{(val - j) / abs(j):.2e}"
        sortie.append([cle, r["valeur"], f"{j:.9g}", ec, etat, " ; ".join(imp), chemin])
        bilan[etat] += 1
    if not CASSER:
        os.makedirs(JOURNAUX, exist_ok=True)
        with open(os.path.join(JOURNAUX, f"refaire-{lot}.csv"), "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["cle", "lot", "juge", "ecart_rel", "etat", "impression", "chemin"])
            w.writerows(sortie)
    print(f"{lot:12s} {bilan}")
    for s in sortie:
        if s[4] not in ("tient", "choix"):
            print("   ", s[4], s[0], "lot", s[1], "juge", s[2], "|", s[5], "|", s[6])
    return bilan


if __name__ == "__main__":
    print("témoin de l'instrument : --casser actif" if CASSER else "passe normale")
    for nom, f in (("eclaireur", eclaireur), ("synthese", synthese), ("genome", genome), ("duplication", duplication)):
        comparer(nom, f())
