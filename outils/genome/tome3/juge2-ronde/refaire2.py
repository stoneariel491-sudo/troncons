"""Juge des chiffres du lot « ronde », second flux : chaque nombre neuf ou déplacé, refait par un autre chemin.

Écrit sans lire memoire/outils/tome3_*.py. Chaque valeur est refaite depuis les fichiers commités sous mesures/
(journaux de mesure, passes, positions), par le chemin le plus court vers la mesure, puis comparée à la valeur
que le lot écrit dans memoire/figures/tome3/donnees/<lot>-nombres.csv.

Règle de comparaison, déclarée avant la passe : égalité à 2e-5 relatif (2e-9 absolu près de zéro) ; sinon,
la valeur est rejugée à la précision où la figure l'imprime (formats relevés par cles.py dans le .tex) ; une
valeur qui diffère à la précision imprimée est un écart.

Aussi refaits ici : la classe de chaque point de III-7.1 et III-7.2 par la règle que la légende énonce
(d̄ + 2σ < 0 : meilleur ; |d̄| ≤ 2σ : égal ; d̄ − 2σ > 0 : pire), avec d̄ et σ lus dans les journaux du juge
(`juge comparer`) ou refaits depuis les positions (P1), et les rapports de KL depuis les journaux `juge kl`.

Témoin (--casser) : chaque valeur du juge est multipliée par 1,001 ; toutes les clés non nulles doivent
tomber au seuil strict, et la classe de κ tenseur par tenseur, calculée avec σ divisé par 2, doit tomber.

  python -I -X utf8 outils/genome/tome3/juge2-ronde/refaire2.py [--casser]
Sorties : journaux/refaire2.csv (clé par clé), journaux/classes2.csv, et le résumé à l'écran.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import pathlib
import statistics
import sys

RACINE = pathlib.Path(__file__).resolve().parents[4]
ICI = pathlib.Path(__file__).resolve().parent
ETAT = RACINE / "mesures/genome/etat-de-l-art"
GEN = RACINE / "mesures/genome/genome"
DUP = RACINE / "mesures/genome/duplication"
PE = RACINE / "mesures/genome/predictif-elagage"
DONNEES = RACINE / "memoire/figures/tome3/donnees"


def lire_json(p: pathlib.Path) -> dict:
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def lire_csv(p: pathlib.Path) -> list[dict]:
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


class Juge:
    def __init__(self) -> None:
        self.v: dict[tuple[str, str], tuple[float, str]] = {}

    def __setitem__(self, k: tuple[str, str], val: tuple[float, str]) -> None:
        self.v[k] = val


J = Juge()
NOTES: list[str] = []


# --- Chapitres 1 et 2 : ce que la borne ne compte pas (M12) --------------------------------------------
def eclaireur() -> None:
    pf = lire_json(ETAT / "passes/frontiere-lam0-damp0.01-e0_8_16_24.json")
    p1 = lire_json(ETAT / "passes/synonyme-lam1-damp1-e0_8_16_24.json")
    t = pf["debit_par_tenseur"]
    # H0 des symboles : moyenne pondérée par les poids des 12 tenseurs (second chemin) contre le total écrit.
    h0 = sum(x["poids"] * x["H0_sym"] for x in t.values()) / sum(x["poids"] for x in t.values())
    assert abs(h0 - pf["bits_H0_sym"]) < 1e-9, (h0, pf["bits_H0_sym"])
    J["eclaireur", "h0-bits"] = (h0, "frontiere-lam0-damp0.01-e0_8_16_24.json : moyenne pondérée des 12 tenseurs")
    # Les échelles : lus − H0 ; la même différence dans la passe λ = 1 (mêmes blocs, mêmes échelles).
    e0 = pf["bits_lus_H0_plus_echelles"] - pf["bits_H0_sym"]
    e1 = p1["bits_lus_H0_plus_echelles"] - p1["bits_H0_sym"]
    assert abs(e0 - e1) < 1e-12
    J["eclaireur", "echelles-bits"] = (e0, "lus − H0 de la base ; égal dans la passe λ = 1")
    # Les experts : les poids des 12 tenseurs divisés par une matrice d'expert (2 880 × 2 880) et par trois rôles.
    n_exp = sum(x["poids"] for x in t.values()) / (3 * 2880 * 2880)
    assert n_exp == len(pf["experts"]) * len(pf["couches"])
    J["eclaireur", "h0-experts"] = (n_exp, "Σ poids / (3 rôles × 2 880²)")
    # La corde : enveloppe convexe inférieure des 40 itérés (D, bits), lue à l'erreur de la frontière.
    br = lire_json(ETAT / "journaux/borne-rd.json")
    pts = sorted((p["D"], p["bits"]) for p in br["uniforme_precis"])
    enveloppe: list[tuple[float, float]] = []
    for p in pts:
        while len(enveloppe) >= 2:
            (x1, y1), (x2, y2) = enveloppe[-2], enveloppe[-1]
            if (x2 - x1) * (p[1] - y1) - (y2 - y1) * (p[0] - x1) <= 0:
                enveloppe.pop()
            else:
                break
        enveloppe.append(p)
    zc = lire_json(ETAT / "journaux/zero-canonique.json")
    d_f = None
    for k in ("erreur_base_commune",):
        if k in zc:
            d_f = zc[k]
    if d_f is None:
        raise SystemExit("zero-canonique.json : erreur_base_commune absente")
    d_f = float(d_f)
    if d_f > 1:  # en pour cent
        d_f /= 100
    corde = None
    for (x1, y1), (x2, y2) in zip(enveloppe, enveloppe[1:]):
        if x1 <= d_f <= x2:
            corde = y1 + (y2 - y1) * (d_f - x1) / (x2 - x1)
    J["eclaireur", "corde-bits-a-d"] = (corde, "enveloppe convexe inférieure des itérés de borne-rd.json")
    J["eclaireur", "ecart-bits-h0"] = (h0 - corde, "H0 (16 experts) − corde")


# --- Chapitre 3 : les rangées de la gaussienne (M1), l'échantillon du critère W (M2) -------------------
def genome() -> None:
    recs = [json.loads(l) for l in open(GEN / "gauss-balayage.jsonl", encoding="utf-8") if l.strip()]
    sept = [r for r in recs if r["q"] == 8 and r["melangeur"] == "fort" and r["lloyd"] == 0 and not r["casser"]]
    for l in (12, 16):
        formes: dict[tuple[int, int], set[int]] = {}
        for r in sept:
            if r["l"] == l:
                formes.setdefault((r["kb"], r["v"]), set()).add(r["rangees"])
        assert len(formes) == 7 and all(len(s) == 1 for s in formes.values()), formes
        comptes = [next(iter(s)) for s in formes.values()]
        mode = max(set(comptes), key=comptes.count)
        exc = sorted(k for k, s in formes.items() if next(iter(s)) != mode)
        J["genome", f"g-l{l}-rangees"] = (mode, f"gauss-balayage.jsonl, 7 formes à l = {l}")
        J["genome", f"g-l{l}-exceptions"] = (len(exc), "id.")
        longueur = {r["poids"] // r["rangees"] for r in sept}
        assert longueur == {2880}
        J["genome", f"g-l{l}-valeurs"] = (mode * 2880, "rangées × 2 880")
        for k, (kb, v) in enumerate(exc):
            J["genome", f"g-l{l}-exc{k}-kb"] = (kb, "id.")
            J["genome", f"g-l{l}-exc{k}-v"] = (v, "id.")
            J["genome", f"g-l{l}-exc{k}-rangees"] = (next(iter(formes[(kb, v)])), "id.")
    cj = lire_json(GEN / "codons-tourne-l12.json")
    for k, e in enumerate(cj["experts"]):
        J["genome", f"c-expert-{k}"] = (e, "codons-tourne-l12.json")
    J["genome", "c-experts"] = (len(cj["experts"]), "id.")
    rang = {t["rangees"] for t in cj["tenseurs"]}
    assert len(rang) == 1 and len(cj["tenseurs"]) == 12
    # Second chemin : 4 experts de 2 880 rangées, une rangée sur quatre (genome.md § 2, critère W).
    assert rang == {len(cj["experts"]) * 2880 // 4}
    J["genome", "c-rangees"] = (rang.pop(), "codons-tourne-l12.json ; = 4 experts × 2 880 / 4")
    J["genome", "c-formes"] = (len(cj["formes"]), "codons-tourne-l12.json")


# --- Chapitre 4 : le témoin de la couche 23, le plancher de la couche 0 (M3), le moyeu (M4), le dessin (G8)
def kruskal_max(paires: list[dict]) -> list[tuple[int, int, float]]:
    parent = list(range(64))

    def racine(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    arbre = []
    for p in sorted(paires, key=lambda p: -p["score_bits"]):
        a, b = racine(p["i"]), racine(p["j"])
        if a != b:
            parent[a] = b
            arbre.append((p["i"], p["j"], p["score_bits"]))
    return arbre


def duplication() -> None:
    rows = lire_csv(DUP / "csv/scores-parente.csv")
    couches = sorted({int(r["couche"]) for r in rows})
    a23 = lire_json(DUP / "arbre-c23.json")
    tp = lire_json(DUP / "paires-temoin-planter-0.5.json")
    assert a23["arguments"]["couche"] == 23
    # Le témoin du hasard de la couche 23 : la moyenne de ses paires, recomptée (pas le champ « hasard_moyen »).
    t23 = statistics.fmean(p["score_bits"] for p in a23["temoin_hasard"])
    J["duplication", "t23-hasard"] = (t23, "arbre-c23.json : moyenne des paires du témoin")
    J["duplication", "t23-paires"] = (len(a23["temoin_hasard"]), "arbre-c23.json")
    J["duplication", "t-paires"] = (len(tp["temoin_hasard"]), "paires-temoin-planter-0.5.json")
    rmax = max(rows, key=lambda r: float(r["score_bits"]))
    assert int(rmax["couche"]) == 23
    J["duplication", "s-max-enfant"] = (int(rmax["enfant"]), "scores-parente.csv")
    J["duplication", "s-max-parent"] = (int(rmax["cand_expert"]), "scores-parente.csv")
    # Second chemin du plus haut score : la paire (enfant, parent) dans les 496 paires de la couche 23.
    paire = [p for p in a23["paires"] if {p["i"], p["j"]} == {int(rmax["enfant"]), int(rmax["cand_expert"])}]
    assert len(paire) == 1 and abs(paire[0]["score_bits"] - float(rmax["score_bits"])) < 1e-6, paire
    J["duplication", "s-sur-hasard"] = (float(rmax["score_bits"]) / t23, "max des 880 scores / témoin de la couche 23")
    J["duplication", "t-couche-bande"] = (couches.index(23), "rang de la couche 23")
    c0 = [r for r in rows if int(r["couche"]) == 0]
    assert all(r["genre"] == "intra" for r in c0)
    J["duplication", "c0-n"] = (len(c0), "scores-parente.csv, couche 0")
    J["duplication", "c0-score-min"] = (min(float(r["score_bits"]) for r in c0), "id.")
    J["duplication", "c0-score-max"] = (max(float(r["score_bits"]) for r in c0), "id.")
    J["duplication", "c0-cos-down-min"] = (min(float(r["cos_down"]) for r in c0), "id.")
    J["duplication", "c0-cos-down-max"] = (max(float(r["cos_down"]) for r in c0), "id.")
    autres = [float(r["cos_down"]) for r in rows if int(r["couche"]) != 0]
    autres_intra = [float(r["cos_down"]) for r in rows if int(r["couche"]) != 0 and r["genre"] == "intra"]
    J["duplication", "autres-cos-down-med"] = (statistics.median(autres), "médiane, couches 8, 16, 23, tous genres")
    NOTES.append(f"cos de down, couches 8/16/23 : médiane tous genres {statistics.median(autres):.4f} "
                 f"({len(autres)} candidats), même couche seule {statistics.median(autres_intra):.4f} "
                 f"({len(autres_intra)}) ; max même couche {max(autres_intra):.4f}")
    # L'arbre : Kruskal refait sur les 496 paires, comparé à l'arbre du journal et au CSV du dessin.
    mien = kruskal_max(a23["paires"])
    assert len(a23["paires"]) == 496 and len(mien) == 31
    leur = {frozenset((e["i"], e["j"])) for e in a23["arbre"]}
    assert {frozenset((i, j)) for i, j, _ in mien} == leur
    csv_ar = lire_csv(DUP / "csv/phylogenie-c23-aretes.csv")
    assert {frozenset((int(r["i"]), int(r["j"]))) for r in csv_ar} == leur
    deg: dict[int, int] = {}
    poids: dict[int, float] = {}
    for i, j, s in mien:
        for e in (i, j):
            deg[e] = deg.get(e, 0) + 1
            poids[e] = poids.get(e, 0.0) + s
    dmax = max(deg.values())
    au_max = sorted(e for e in deg if deg[e] == dmax)
    moyeu = max(poids, key=poids.get)
    J["duplication", "a-degmax"] = (dmax, "Kruskal du juge sur arbre-c23.json")
    J["duplication", "a-degmax-n"] = (len(au_max), "id.")
    for k, e in enumerate(au_max):
        J["duplication", f"a-degmax-{k}"] = (e, "id.")
    J["duplication", "a-moyeu-poids"] = (poids[moyeu], "somme des scores (pleine précision) des arêtes du moyeu")
    second_deg = max((e for e in au_max if e != moyeu), key=poids.get)
    second_tous = max((e for e in poids if e != moyeu), key=poids.get)
    J["duplication", "a-second"] = (second_deg, "le plus lourd des autres experts de degré maximal")
    J["duplication", "a-second-poids"] = (poids[second_deg], "id.")
    NOTES.append(f"moyeu {moyeu} : {poids[moyeu]:.5f} bit ; second de degré maximal {second_deg} : "
                 f"{poids[second_deg]:.5f} ; second de tous {second_tous} : {poids[second_tous]:.5f} ; "
                 f"poids par expert (5 plus lourds) : "
                 + ", ".join(f"{e} {poids[e]:.4f}" for e in sorted(poids, key=lambda e: -poids[e])[:5]))
    lourdes = sorted(mien, key=lambda t: -t[2])
    k = 0
    while moyeu in lourdes[k][:2]:
        k += 1
    J["duplication", "a-moyeu-lourdes"] = (k, "arêtes les plus lourdes consécutives qui touchent le moyeu")
    # Le dessin radial : profondeur et feuilles depuis le moyeu (le reste du dessin : series2.py).
    voisins: dict[int, list[int]] = {}
    for i, j, _ in mien:
        voisins.setdefault(i, []).append(j)
        voisins.setdefault(j, []).append(i)
    prof = {moyeu: 0}
    pile = [moyeu]
    while pile:
        u = pile.pop()
        for w in voisins[u]:
            if w not in prof:
                prof[w] = prof[u] + 1
                pile.append(w)
    feuilles = sum(1 for u in prof if u != moyeu and len(voisins[u]) == 1)
    J["duplication", "r-profondeur-max"] = (max(prof.values()), "profondeur depuis le moyeu")
    J["duplication", "r-feuilles"] = (feuilles, "feuilles de l'arbre enraciné au moyeu")
    J["duplication", "r-rayon-max"] = (max(prof.values()) + 1, "profondeur maximale + 1 (rayon d + 1 dit dans l'en-tête)")
    J["duplication", "r-decalage"] = (1, "constante de dessin (rayon d + 1)")


# --- Chapitre 7 : la règle (G1), λ = 1 (M5), les queues (M9, M11), la KL négative (M10), D1 (M8) --------
def classe(d: float, s: float) -> str:
    if d + 2 * s < 0:
        return "gagne"
    if d - 2 * s > 0:
        return "tombe"
    return "egal"


def synthese(casser: bool) -> list[list]:
    jb = lire_json(ETAT / "journaux/kl-frontiere-juge.json")["resume"]
    js = lire_json(ETAT / "journaux/kl-synonyme-d1-juge.json")["resume"]
    pb = lire_csv(ETAT / "journaux/kl-frontiere-positions.csv")
    ps = lire_csv(ETAT / "journaux/kl-synonyme-d1-positions.csv")
    assert [(r["fenetre"], r["position"]) for r in pb] == [(r["fenetre"], r["position"]) for r in ps]
    kb = [float(r["kl"]) for r in pb]
    ks = [float(r["kl"]) for r in ps]
    n = len(kb)
    # P1, appariée refaite depuis les positions : d̄, σ naïf, σ par fenêtres (blocs).
    d = [s - b for b, s in zip(kb, ks)]
    dm = statistics.fmean(d)
    s_naif = statistics.stdev(d) / math.sqrt(n)
    fen = sorted({r["fenetre"] for r in pb}, key=int)
    moy_f = [statistics.fmean(x for x, r in zip(d, pb) if r["fenetre"] == f) for f in fen]
    s_fen = statistics.stdev(moy_f) / math.sqrt(len(moy_f))
    NOTES.append(f"P1 appariée : d̄ = {dm:.6g}, σ naïf {s_naif:.6g}, σ par fenêtres {s_fen:.6g} "
                 f"(le plus grand des deux est retenu par la source)")
    s1 = max(s_naif, s_fen)
    J["synthese", "syn-apparie"] = (dm, "positions (2 550), syn − base")
    J["synthese", "syn-apparie-sigma"] = (s1, "max(σ naïf, σ par fenêtres)")
    J["synthese", "syn-apparie-z"] = (dm / s1, "calculé")
    ap = lire_json(PE / "kl/comparer-base-ecsq_kappa_t-f5-9.json")["apparie"]
    J["synthese", "kappa-t-apparie"] = (ap["kl_difference_b_moins_a"], "comparer-base-ecsq_kappa_t-f5-9.json")
    J["synthese", "kappa-t-apparie-sigma"] = (ap["kl_ecart_type"], "id.")
    J["synthese", "kappa-t-apparie-z"] = (ap["kl_difference_b_moins_a"] / ap["kl_ecart_type"], "calculé")
    # Les rapports de KL imprimés pour la première fois, depuis les journaux `juge kl` (pas resume-12.csv).
    kbase3 = lire_json(PE / "kl/kl-12-base-f5-9.json")["resume"]["kl_moyenne"]
    for cle, plan in (("p3-kappat-rapport", "ecsq_kappa_t"), ("p3-partse-rapport", "ecsq_e"),
                      ("p3-elag-rapport", "sens_e_q")):
        k = lire_json(PE / f"kl/kl-12-{plan}-f5-9.json")["resume"]["kl_moyenne"]
        J["synthese", cle] = (k / kbase3, f"kl-12-{plan}-f5-9.json / kl-12-base-f5-9.json")
    J["synthese", "p1-syn-rapport"] = (statistics.fmean(ks) / statistics.fmean(kb), "positions : moyenne syn / base")
    # λ = 1 : 16 experts (4 × 4 couches), sous-ensemble des 32 de P1 (experts 0, 4, …, 28 des mêmes couches).
    p1 = lire_json(ETAT / "passes/synonyme-lam1-damp1-e0_8_16_24.json")
    assert set(p1["experts"]) <= set(range(0, 32, 4)) and p1["couches"] == [0, 8, 16, 23]
    J["synthese", "lam1-experts"] = (len(p1["experts"]) * len(p1["couches"]), "passe λ = 1")
    J["synthese", "lam1-base-bits"] = (lire_json(ETAT / "passes/frontiere-lam0-damp0.01-e0_8_16_24.json")["bits_H0_sym"],
                                       "frontiere-lam0-damp0.01-e0_8_16_24.json")
    # Les queues : les ⌊n/100⌋ plus grandes positions de chacun.
    n1 = n // 100
    qb = set(sorted(range(n), key=lambda i: -kb[i])[:n1])
    qs = set(sorted(range(n), key=lambda i: -ks[i])[:n1])
    J["synthese", "n-1pct"] = (n1, "⌊2 550 / 100⌋")
    J["synthese", "n-1pct-part"] = (n1 / n, "id.")
    J["synthese", "queue-communes"] = (len(qb & qs), "positions")
    parf: dict[str, int] = {}
    for i in qb:
        parf[pb[i]["fenetre"]] = parf.get(pb[i]["fenetre"], 0) + 1
    J["synthese", "queue-base-fenetres"] = (len(parf), "positions")
    J["synthese", "queue-base-fenetre-max"] = (max(parf.values()), "positions")
    NOTES.append("queue de la base par fenêtre : " + ", ".join(f"{f}:{parf.get(f, 0)}" for f in fen))
    J["synthese", "part-1pct-base"] = (sum(kb[i] for i in qb) / sum(kb), "positions, 25 plus grandes de la base")
    J["synthese", "part-1pct-syn"] = (sum(ks[i] for i in qs) / sum(ks), "positions, 25 plus grandes du synonyme")
    neg = [x for x in kb + ks if x < 0]
    J["synthese", "kl-negatives"] = (len(neg), "positions")
    J["synthese", "kl-negative"] = (min(neg), "positions")
    assert abs(min(neg) - js["kl_min"]) < 1e-15 and jb["kl_min"] > 1e-5
    sous = [i for i in range(n) if min(kb[i], ks[i]) < 1e-5]
    NOTES.append(f"positions sous 1e-5 : {sous} ; base {[kb[i] for i in sous]}, syn {[ks[i] for i in sous]}")
    # D1 sans perte (M8) : la formule de la source, relue sur ses deux journaux.
    tr = lire_json(PE / "taux-reel-colonne-12-gptoss20b.json")["bpp"]
    vd = lire_json(DUP / "verdicts.json")["D1"]
    J["synthese", "d1"] = (tr["total_identite"] - vd["gain_net_moyen"] + vd["cout_ajoute"],
                           "total_identite − gain net + coût ajouté (formule de frontiere.py)")
    # --- Les classes, par la règle, depuis les journaux ---------------------------------------------------
    c10 = lire_json(GEN / "kl/comparer10-base-contre-recette.json")
    classes = [["p1-syn", "P1", dm, s1, classe(dm, s1), "positions"],
               ["p2-sstar", "P2-10", c10["apparie"]["kl_difference_b_moins_a"], c10["apparie"]["kl_ecart_type"],
                classe(c10["apparie"]["kl_difference_b_moins_a"], c10["apparie"]["kl_ecart_type"]),
                "comparer10-base-contre-recette.json"]]
    for cle, f in (("p3-kappat", "ecsq_kappa_t"), ("p3-kappa", "kappa"), ("p3-hebbdlc", "hebb_d_lc"),
                   ("p3-hebbe", "hebb_e"), ("p3-hebbelc", "hebb_e_lc")):
        a = lire_json(PE / f"kl/comparer-base-{f}-f5-9.json")["apparie"]
        s = a["kl_ecart_type"] / (2 if casser and cle == "p3-kappat" else 1)
        classes.append([cle, "P3", a["kl_difference_b_moins_a"], s, classe(a["kl_difference_b_moins_a"], s),
                        f"comparer-base-{f}-f5-9.json"])
    for cle, f in (("p3-partse", "ecsq_e"), ("p3-elag", "sens_e_q")):
        k = lire_json(PE / f"kl/kl-12-{f}-f5-9.json")["resume"]["kl_moyenne"] / kbase3
        classes.append([cle, "P3", "", "", "tombe" if k > 1 else "?", f"rapport {k:.4f} (pas d'appariée)"])
    return classes


def imprime(v: float, fmt: str) -> str:
    """Le nombre tel que pgfmathprintnumber l'imprimerait, pour les formats du lot (fixed, sci, Pct, Entier)."""
    if fmt.startswith("Entier"):
        return f"{v:.0f}"
    if fmt.startswith("Pct"):
        p = int(fmt[4:-1]) if fmt.startswith("Pct[") else 0
        return f"{100 * v:.{p}f}"
    if "sci" in fmt:
        p = int(fmt.split("precision=")[1].split("]")[0].split(",")[0])
        return f"{v:.{p}e}"
    if "precision=" in fmt:
        p = int(fmt.split("precision=")[1].split("]")[0].split(",")[0])
        return f"{v:.{p}f}"
    return f"{v:.6g}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--casser", action="store_true")
    a = ap.parse_args()
    eclaireur()
    genome()
    duplication()
    classes = synthese(a.casser)
    usages = {(r["lot"], r["cle"]): r["usages_apres"] for r in lire_csv(ICI / "journaux/cles.csv")}
    lot_vals = {}
    for lot in ("eclaireur", "genome", "duplication", "synthese"):
        for r in lire_csv(DONNEES / f"{lot}-nombres.csv"):
            lot_vals[lot, r["cle"]] = float(r["valeur"])
    lignes, ecarts, stricts = [], 0, 0
    for (lot, cle), (v, src) in sorted(J.v.items()):
        if a.casser:
            v *= 1.001
        if (lot, cle) not in lot_vals:
            lignes.append([lot, cle, f"{v:.10g}", "", "", "absente du lot", src])
            ecarts += 1
            continue
        w = lot_vals[lot, cle]
        strict = abs(v - w) <= max(2e-5 * abs(w), 2e-9)
        stricts += strict
        fmts = [f for f in usages.get((lot, cle), "").split(" ; ") if f and f != "Val"]
        imprimes = [(imprime(v, f), imprime(w, f)) for f in fmts]
        verdict = "égal" if strict else ("égal à l'impression" if imprimes and all(x == y for x, y in imprimes)
                                         else "ÉCART")
        if verdict == "ÉCART":
            ecarts += 1
        lignes.append([lot, cle, f"{v:.10g}", f"{w:.10g}", " | ".join(f"{x}/{y}" for x, y in imprimes), verdict, src])
    nom = "refaire2-casser.csv" if a.casser else "refaire2.csv"
    with open(ICI / "journaux" / nom, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["lot", "cle", "juge", "lot_valeur", "imprime_juge/lot", "verdict", "chemin_du_juge"])
        w.writerows(lignes)
    # Les classes : celles du juge contre les deux CSV du lot.
    fk = {r["cle"]: r["classe"] for r in lire_csv(DONNEES / "synthese-frontiere-kl.csv")}
    ek = {r["cle"]: r["classe"] for r in lire_csv(DONNEES / "synthese-erreur-kl.csv")}
    ek_cle = {"p1-syn": "syn", "p2-sstar": "sstar10", "p3-kappa": "kappa", "p3-hebbe": "hebbe",
              "p3-hebbelc": "hebbelc", "p3-partse": "partse"}
    desaccords = 0
    with open(ICI / "journaux" / ("classes2-casser.csv" if a.casser else "classes2.csv"), "w", encoding="utf-8",
              newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["cle", "protocole", "d", "sigma", "z", "classe_juge", "classe_III-7.1", "classe_III-7.2", "source"])
        for c in classes:
            z = f"{c[2] / c[3]:+.3f}" if c[2] != "" else ""
            c71 = fk.get(c[0], "absent")
            c72 = ek.get(ek_cle.get(c[0], ""), "—")
            if c71 != c[4] or (c72 != "—" and c72 != c[4]):
                desaccords += 1
            w.writerow([c[0], c[1], c[2], c[3], z, c[4], c71, c72, c[5]])
    n = len(lignes)
    print(f"{n} clés refaites ; égales au seuil strict : {stricts} ; écarts : {ecarts} ; classes en désaccord : {desaccords}")
    for note in NOTES:
        print("  note :", note)
    for l in lignes:
        if l[5] != "égal":
            print("  ", l[:6])
    if a.casser:
        tombees = n - stricts
        print(f"témoin : {tombees} clés sur {n} tombent au seuil strict ; classes en désaccord : {desaccords}")
        return 0 if tombees >= sum(1 for (lot, cle), (v, _) in J.v.items() if v != 0) and desaccords >= 1 else 1
    return 0 if ecarts == 0 and desaccords == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
