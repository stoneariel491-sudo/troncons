"""Juge du lot « ronde » : un point tiré au hasard dans chaque série tracée, contrôlé à la source.

Écrit par le juge le 2026-10-27, sans lire les scripts du lot. Graine écrite : 20261027 ; la série k
(dans l'ordre de la liste SERIES) tire sa ligne par numpy.random.default_rng(20261027 + k). Pour chaque
série, la ligne tirée est retrouvée dans le fichier commité sous mesures/ et comparée colonne à colonne
(tolérance relative 1e-4, les CSV du lot écrivant 5 à 7 chiffres significatifs). En plus du point tiré,
le compte de lignes de la série est comparé à celui de la source (ce qui manque ou ce qui est en trop
se voit).

Témoin (déclaré avant) : --casser multiplie par 1,01 chaque valeur (hors identifiants) de la ligne tirée ;
chaque série doit alors tomber.

Sortie : journaux/echantillon.csv. Usage : python -I -X utf8 echantillon.py [--casser]
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", "..", "..", ".."))
DON = os.path.join(RACINE, "memoire", "figures", "tome3", "donnees")
CASSER = "--casser" in sys.argv
GRAINE = 20261027
sys.stdout.reconfigure(encoding="utf-8")


def ch(*p):
    return os.path.join(RACINE, *p)


def lc(chemin):
    with open(chemin, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def lj(*p):
    with open(ch(*p), encoding="utf-8") as f:
        return json.load(f)


def proche(a, b, tol=1e-4):
    a, b = float(a), float(b)
    if math.isnan(a) and math.isnan(b):
        return True
    return abs(a - b) <= tol * max(abs(b), 1e-9)


RES = []


ID = {"couche", "enfant", "role", "cle", "protocole", "colonne", "l", "expert", "i", "j", "fenetre", "kb", "v",
      "rangees", "classe", "etat", "tenseur", "converge", "colonne_retenue", "log10_kl", "degre"}
INDEX = {}


def serie(k, nom, fichier, source_n, verif):
    """verif(ligne) -> (bool, texte) ; source_n : le compte attendu (ou None)."""
    L = lc(os.path.join(DON, fichier))
    rng = np.random.default_rng(GRAINE + k)
    i = int(rng.integers(len(L)))
    ligne = dict(L[i])
    if CASSER:
        for c in ligne:
            if c not in ID:
                try:
                    ligne[c] = repr(float(ligne[c]) * 1.01)
                except ValueError:
                    pass
    INDEX["i"] = i
    ok, txt = verif(ligne)
    n_ok = (source_n is None) or (source_n == len(L))
    RES.append([k, nom, fichier, len(L), source_n if source_n is not None else "", int(n_ok), i, int(ok), txt])
    print(f"{k:2d} {nom:38s} ligne {i:4d}/{len(L):4d} compte {'ok' if n_ok else 'DIFFÈRE ' + str(source_n)}  point {'tient' if ok else 'TOMBE'}  {txt}")


def main():
    E = ("mesures", "genome", "etat-de-l-art", "journaux")
    k = 0
    # --- III-1.2 ---------------------------------------------------------------------------------
    up = lj(*E, "borne-rd.json")["uniforme_precis"]
    dans = [p for p in up if 100 * p["D"] >= 1e-4]

    def v_borne(l):
        p = min(up, key=lambda q: abs(q["bits"] - float(l["bits"])))
        return (proche(l["bits"], p["bits"]) and proche(l["d_pct"], 100 * p["D"]) and int(l.get("converge", int(p["converge"]))) == int(p["converge"]),
                f"β = {p['beta']:.4g} : bits {p['bits']:.6f}, D {100 * p['D']:.6e} %, convergé {p['converge']}")
    serie(k, "III-1.2 courbe uniforme_precis", "eclaireur-borne-rd.csv", len(dans), v_borne); k += 1
    serie(k, "III-1.2 itérés convergés", "eclaireur-borne-converge.csv", sum(p["converge"] for p in dans), v_borne); k += 1
    serie(k, "III-1.2 itérés non convergés", "eclaireur-borne-nonconv.csv", sum(not p["converge"] for p in dans), v_borne); k += 1
    # --- III-2.1 ---------------------------------------------------------------------------------
    for m in ("20b", "120b"):
        t = {x["tenseur"]: x for x in lj(*E, f"zero-compte-{m}.json")["par_tenseur"]}
        nc = len({n.split(".")[1] for n in t})

        def v_z(l, t=t):
            c = l["couche"]
            ok = all(proche(l[r], t[f"blk.{c}.ffn_{r}_exps.weight"]["cout_signe_des_zeros"]) for r in ("gate", "up", "down"))
            return ok, f"couche {c} : " + ", ".join(f"{r} {t[f'blk.{c}.ffn_{r}_exps.weight']['cout_signe_des_zeros']:.6f}" for r in ("gate", "up", "down"))
        serie(k, f"III-2.1 coût par tenseur {m}", f"eclaireur-zeros-{m}.csv", nc, v_z); k += 1
    # --- III-7.1 ---------------------------------------------------------------------------------
    F = lc(ch("mesures", "genome", "construction", "synthese", "k10", "frontiere.csv"))
    par_nom = {
        "p1-base": "base frontière (07, F1)", "p1-syn": "mutation synonyme λ = 0, δ* = 1",
        "p2-base": "base frontière (8 experts, 10 fenêtres)", "p2-sstar": "S* (10 fenêtres)",
        "p3-base": "base frontière (12 tenseurs)", "p3-kappat": "partitions par κ, chaque tenseur à l'erreur de la base",
        "p3-kappa": "partitions par κ, erreur moyenne égale", "p3-hebbdlc": "hebbien (δ, ligne, colonne)",
        "p3-hebbe": "hebbien par e (erreur d'expert égale à la base)", "p3-hebbelc": "hebbien (e, ligne, colonne)",
        "p3-partse": "partitions par e (remplissage inverse des poids)", "p3-elag": "élagage par activité de colonne (e, q)",
        "s-brin": "brin lu par codons, tourné (critère W, erreur de poids égale)", "s-sstar": "S* à erreur de sortie d'expert égale",
        "s-lam1": "mutation synonyme λ = 1, δ* = 1 (KL non mesurée)", "s-baselam1": "base frontière, mêmes experts que λ = 1",
        "s-d2b": "duplication D2b (parent comme contexte, base inchangée)", "s-graine": "graine + coefficients (SeedLM écrit de zéro)",
        "s-motifs": "motifs partagés (dictionnaire commun, RVQ)"}
    FN = {r["mecanisme"]: r for r in F}

    def v_f(l):
        r = FN[par_nom[l["cle"]]]
        ok = proche(l["bits"], r["bits_par_poids"]) and (("rapport" not in l) or proche(l["rapport"], r["rapport_kl"]))
        return ok, f"{l['cle']} → « {r['mecanisme']} » ({r['protocole']}) bits {r['bits_par_poids']} rapport {r['rapport_kl'] or '—'} ; verdict source « {r['verdict']} » ; classe du lot « {l['classe']} »"
    serie(k, "III-7.1 points jugés à la KL", "synthese-frontiere-kl.csv", 12, v_f); k += 1
    serie(k, "III-7.1 points sans KL", "synthese-frontiere-sans-kl.csv", sum(1 for r in F if r["kl_moyenne"] == ""), v_f); k += 1
    C = {r["tenseur"]: r for r in lc(ch("mesures", "genome", "construction", "synthese", "k10", "colonne-par-tenseur.csv"))}

    def v_c(l):
        c, r_ = l["tenseur"].split()
        s = C[f"blk.{c.split('.')[1]}.ffn_{r_}_exps.weight"]
        ok = proche(l["sans_perte"], s["sans_perte"]) and proche(l["zero"], s["zero_octet_kappa"]) and proche(l["colonne"], s["zero_demi_octet_kappa_colonne"]) \
            and int(l["colonne_retenue"]) == int(float(s["zero_octet_kappa"]) - float(s["zero_demi_octet_kappa_colonne"]) >= 0.015)
        return ok, f"{l['tenseur']} : sans perte {s['sans_perte']}, octet κ {s['zero_octet_kappa']}, demi-octet κ {s['zero_demi_octet_kappa']}, + colonne {s['zero_demi_octet_kappa_colonne']}"
    serie(k, "III-7.1 axe sans perte par tenseur", "synthese-colonne.csv", len(C), v_c); k += 1
    # --- III-7.2 ---------------------------------------------------------------------------------
    EK = lc(ch("mesures", "genome", "construction", "synthese", "k10", "erreur-contre-kl.csv"))
    cle_ek = {"syn": "mutation synonyme λ = 0", "sstar3": "S*", "sstar10": "S* (10 fenêtres)",
              "kappa": "partitions par κ, erreur moyenne égale", "hebbe": "hebbien par e (erreur d'expert égale à la base)",
              "hebbelc": "hebbien (e, ligne, colonne)", "partse": "partitions par e (remplissage inverse des poids)"}
    EKN = {r["mecanisme"]: r for r in EK}

    def v_ek(l):
        r = EKN[cle_ek[l["cle"]]]
        return proche(l["x"], r["rapport_erreur_expert"]) and proche(l["y"], r["rapport_kl"]), \
            f"{l['cle']} ({l['etat']}) → {r['mecanisme']} ({r['protocole']}) {r['rapport_erreur_expert']} ; {r['rapport_kl']}"
    serie(k, "III-7.2 erreur d'expert contre KL", "synthese-erreur-kl.csv", len(EK), v_ek); k += 1
    # --- III-7.3 ---------------------------------------------------------------------------------
    pb = lc(ch(*E, "kl-frontiere-positions.csv"))
    ps = lc(ch(*E, "kl-synonyme-d1-positions.csv"))
    L73 = lc(os.path.join(DON, "synthese-positions.csv"))

    def v_p(l):
        i = INDEX["i"]
        a, b = pb[i], ps[i]
        kb_, ks_ = max(float(a["kl"]), 1e-5), max(float(b["kl"]), 1e-5)
        return proche(l["kl_base"], kb_) and proche(l["kl_syn"], ks_) and l["fenetre"] == a["fenetre"], \
            f"ligne {i} : fenêtre {a['fenetre']} position {a['position']} base {a['kl']} synonyme {b['kl']}"
    serie(k, "III-7.3 positions", "synthese-positions.csv", len(pb), v_p); k += 1
    for nom, src in (("base", pb), ("syn", ps)):
        lk = np.log10(np.maximum(np.array([float(r["kl"]) for r in src]), 1e-5))

        def v_d(l, lk=lk):
            # case de largeur 0,125 centrée sur log10_kl ; densité = part des positions / largeur (hypothèse
            # du juge, à vérifier : on teste aussi la part brute)
            c = float(l["log10_kl"])
            n_ = int(((lk >= c - 0.0625) & (lk < c + 0.0625)).sum())
            part = n_ / len(lk)
            return proche(l["densite"], part / 0.125, 2e-3) or proche(l["densite"], part, 2e-3), \
                f"case {c:+.4f} : {n_} positions, part {part:.6f}, part/largeur {part / 0.125:.6f}, lot {l['densite']}"
        serie(k, f"III-7.3 densité marginale {nom}", f"synthese-densite-{nom}.csv", 48, v_d); k += 1
    # --- III-7.4 ---------------------------------------------------------------------------------
    CE = lc(ch("mesures", "genome", "genome", "csv", "colonnes-energie-erreur.csv"))
    moy = {c: np.mean([float(r[c]) for r in CE]) for c in ("energie_exacte", "erreur_brin_pondere", "erreur_s_etoile", "erreur_base")}

    def v_ce(l):
        r = CE[int(l["colonne"])]
        ok = proche(l["energie"], float(r["energie_exacte"]) / moy["energie_exacte"]) and proche(l["brin"], float(r["erreur_brin_pondere"]) / moy["erreur_brin_pondere"]) \
            and proche(l["sstar"], float(r["erreur_s_etoile"]) / moy["erreur_s_etoile"]) and proche(l["base"], float(r["erreur_base"]) / moy["erreur_base"])
        return ok, f"colonne {r['colonne']} : énergie/moy {float(r['energie_exacte']) / moy['energie_exacte']:.5g}, brin {float(r['erreur_brin_pondere']) / moy['erreur_brin_pondere']:.5g}"
    serie(k, "III-7.4 colonnes (blk.8 down, e16)", "synthese-colonnes.csv", len(CE), v_ce); k += 1
    # --- III-3.4 ---------------------------------------------------------------------------------
    G = [json.loads(x) for x in open(ch("mesures", "genome", "genome", "gauss-balayage.jsonl"), encoding="utf-8") if x.strip()]
    for l_ in (12, 16):
        def v_g(l, l_=l_):
            d = [x for x in G if x["l"] == l_ and x["kb"] == int(l["kb"]) and x["v"] == int(l["v"]) and x["melangeur"] == "fort" and x["lloyd"] == 0 and x["q"] == 8][0]
            return proche(l["erreur"], d["mse"]) and int(l["rangees"]) == d["rangees"] and proche(l["shannon"], 2 ** (-2 * d["kb"] / d["v"]), 1e-3), \
                f"l = {l_}, ({d['kb']}, {d['v']}) : mse {d['mse']}, rangées {d['rangees']}"
        serie(k, f"III-3.4 formes l = {l_}", f"genome-gauss-l{l_}.csv", 7, v_g); k += 1

    def v_fen(l):
        d = [x for x in G if x["l"] == int(l["l"]) and x["kb"] == 2 and x["v"] == 1 and x["melangeur"] == "fort" and x["lloyd"] == 0 and x["q"] == 8][0]
        return proche(l["erreur"], d["mse"]), f"l = {l['l']} : mse {d['mse']}, rangées {d['rangees']}"
    serie(k, "III-3.4 fenêtre à 2 bits", "genome-gauss-fenetre.csv", 5, v_fen); k += 1
    # --- III-3.6 ---------------------------------------------------------------------------------
    for norme in ("tourne", "brut"):
        src = lc(ch("mesures", "genome", "genome", "csv", f"courbes-{norme}-l12.csv"))
        for c in (0, 8, 16, 23):
            for r_ in ("gate", "up", "down"):
                ref = [x for x in src if x["tenseur"] == f"blk.{c}.ffn_{r_}_exps.weight"]

                def v_cb(l, ref=ref):
                    m = [x for x in ref if proche(x["bits"], l["bits"], 1e-5) and proche(x["erreur"], l["erreur"], 1e-4)]
                    return len(m) >= 1, f"{len(m)} point(s) de la source à (bits {l['bits']}, erreur {l['erreur']})"
                serie(k, f"III-3.6 {norme} {c} {r_}", f"genome-courbes-{norme}-{c}-{r_}.csv", len(ref), v_cb); k += 1
    VT = {x["tenseur"]: x for x in lc(ch("mesures", "genome", "genome", "csv", "verdict-par-tenseur.csv"))}

    def v_v(l):
        s = VT[f"blk.{l['couche']}.ffn_{l['role']}_exps.weight"]
        return proche(l["bits_base"], s["bits_frontiere"]) and proche(l["erreur_base"], s["erreur_base"]) and proche(l["bits_tourne"], s["bits_tourne"]) \
            and proche(l["bits_brut"], s["bits_brut"]), f"{l['couche']} {l['role']} : {s['bits_frontiere']} {s['erreur_base']} {s['bits_tourne']} {s['bits_brut']}"
    serie(k, "III-3.6 verdict par tenseur", "genome-verdict.csv", 12, v_v); k += 1
    # --- III-4.2 ---------------------------------------------------------------------------------
    SP = lc(ch("mesures", "genome", "duplication", "csv", "scores-parente.csv"))
    couches = sorted({int(r["couche"]) for r in SP})
    for genre in ("intra", "voisine", "meme_indice"):
        ref = [r for r in SP if r["genre"] == genre]

        def v_s(l, ref=ref):
            m = [r for r in ref if r["couche"] == l["couche"] and r["enfant"] == l["enfant"] and proche(r["score_bits"], l["score"], 1e-5)]
            x = float(l["x"])
            colonne = couches.index(int(l["couche"]))
            return len(m) == 1 and colonne - 0.5 < x < colonne + 0.5, \
                f"couche {l['couche']} enfant {l['enfant']} score {l['score']} : {len(m)} candidat(s) {[(r['cand_couche'], r['cand_expert']) for r in m]} ; x = {x} dans la colonne {colonne}"
        serie(k, f"III-4.2 scores {genre}", f"duplication-scores-{genre}.csv", len(ref), v_s); k += 1
    # --- III-4.8 ---------------------------------------------------------------------------------
    NO = {r["expert"]: r for r in lc(ch("mesures", "genome", "duplication", "csv", "phylogenie-c23-noeuds.csv"))}
    AR = lc(ch("mesures", "genome", "duplication", "csv", "phylogenie-c23-aretes.csv"))
    smax = max(float(a["score"]) for a in AR)

    def v_n(l):
        s = NO[l["expert"]]
        return proche(l["x"], s["x"]) and proche(l["y"], s["y"]) and l["degre"] == s["degre"], f"expert {l['expert']} : ({s['x']}, {s['y']}) degré {s['degre']}"
    serie(k, "III-4.8 nœuds", "duplication-noeuds.csv", len(NO), v_n); k += 1

    def v_a(l):
        s = [a for a in AR if a["i"] == l["i"] and a["j"] == l["j"]][0]
        return proche(l["score"], s["score"]) and proche(l["rel"], float(s["score"]) / smax, 1e-3) and proche(l["xi"], s["xi"]) and proche(l["yj"], s["yj"]), \
            f"arête ({s['i']}, {s['j']}) score {s['score']} rel {float(s['score']) / smax:.4f}"
    serie(k, "III-4.8 arêtes", "duplication-aretes.csv", len(AR), v_a); k += 1

    if not CASSER:
        with open(os.path.join(ICI, "journaux", "echantillon.csv"), "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["serie", "nom", "fichier", "lignes_lot", "lignes_source", "compte_ok", "ligne_tiree", "point_tient", "controle"])
            w.writerows(RES)
    print(("TÉMOIN --casser : " if CASSER else "") + f"{sum(r[7] for r in RES)} points tenus sur {len(RES)} ; comptes égaux : {sum(r[5] for r in RES)} sur {len(RES)}")


if __name__ == "__main__":
    main()
