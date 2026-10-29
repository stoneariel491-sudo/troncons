"""Données des figures du chapitre 3 du Tome III (le génome des poids : le brin lu par codons), tirées des
fichiers commités de mesures/genome/genome/ (aucun chiffre recopié à la main).

Sources :
  gauss-balayage.jsonl, gauss-T1.json            III-3.4 : le brin sur une gaussienne i.i.d. ;
  csv/courbes-tourne-l12.csv, csv/courbes-brut-l12.csv, csv/verdict-par-tenseur.csv
                                                 III-3.6 : débit-distorsion par tenseur, point de la base.

Écrit sous memoire/figures/tome3/donnees/ (virgule, fin de ligne LF) :
  genome-gauss-l12.csv, genome-gauss-l16.csv    les formes (kb, v) du balayage, mélangeur fort, q = 8,
                                                 sans Lloyd : débit, erreur, borne 2^(-2R), écart en dB ;
  genome-gauss-fenetre.csv                       à 2 bits, la longueur de fenêtre l = 8 à 16 ;
  genome-courbes-<norme>-<couche>-<rôle>.csv     une courbe (bits, erreur) par tenseur et par norme ;
  genome-verdict.csv                             par tenseur : base (bits, erreur), bits du brin tourné ;
  genome-nombres.csv                             chaque nombre d'une légende ou d'une annotation.

  python -I -X utf8 memoire/outils/tome3_genome.py
"""
from __future__ import annotations

import csv
import json
import math
import pathlib
import statistics

RACINE = pathlib.Path(__file__).resolve().parents[2]
G = RACINE / "mesures/genome/genome"
D = RACINE / "memoire/figures/tome3/donnees"
NOMBRES: list[tuple[str, str, str]] = []
ROLES = ("gate", "up", "down")


def nombre(cle: str, valeur: float, source: str, chiffres: int = 6) -> float:
    NOMBRES.append((cle, f"{valeur:.{chiffres}g}", source.replace(",", " ;")))  # pgfplotstable ne lit pas les guillemets
    return valeur


def ecrire(nom: str, entete: list[str], lignes: list[list]) -> None:
    with open(D / nom, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=",", lineterminator="\n")
        w.writerow(entete)
        w.writerows(lignes)


def lire_csv(chemin: pathlib.Path) -> list[dict]:
    with open(chemin, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def gauss() -> None:
    src = "mesures/genome/genome/gauss-balayage.jsonl"
    lignes = [json.loads(l) for l in open(G / "gauss-balayage.jsonl", encoding="utf-8") if l.strip()]
    base = [d for d in lignes if d["melangeur"] == "fort" and d["q"] == 8 and d["lloyd"] == 0]
    for l in (12, 16):
        pts = sorted((d for d in base if d["l"] == l), key=lambda d: d["debit"])
        # Les formes (kb, v) ; à 2 bits et l = 12, la forme (2, 1) est aussi celle du balayage en l : une ligne.
        vus, rows = set(), []
        for d in pts:
            if (d["kb"], d["v"]) in vus:
                continue
            vus.add((d["kb"], d["v"]))
            # L'écart en dB est recalculé (second chemin) et comparé à celui du journal.
            db = 10 * math.log10(d["mse"] / d["borne_shannon"])
            assert abs(db - d["ecart_db"]) < 2e-3, (d, db)
            assert abs(d["borne_shannon"] - 2 ** (-2 * d["debit"])) < 1e-5
            rows.append([f"{d['debit']:.4f}", f"{d['mse']:.6f}", f"{d['borne_shannon']:.6f}", f"{db:.4f}", d["kb"], d["v"], d["rangees"]])
        ecrire(f"genome-gauss-l{l}.csv", ["debit", "erreur", "shannon", "ecart_db", "kb", "v", "rangees"], rows)
        nombre(f"g-l{l}-formes", len(rows), src)
        nombre(f"g-l{l}-db-min", min(float(r[3]) for r in rows), src + " (calculé)")
        nombre(f"g-l{l}-db-max", max(float(r[3]) for r in rows), src + " (calculé)")
        for r in rows:
            nombre(f"g-l{l}-{r[4]}-{r[5]}-db", float(r[3]), src + " (calculé)")
            nombre(f"g-l{l}-{r[4]}-{r[5]}-r", float(r[0]), src)
    fen = sorted((d for d in base if d["kb"] == 2 and d["v"] == 1), key=lambda d: d["l"])
    vus, rows = set(), []
    for d in fen:
        if d["l"] in vus:
            continue
        vus.add(d["l"])
        rows.append([d["l"], f"{d['mse']:.6f}", f"{10 * math.log10(d['mse'] / d['borne_shannon']):.4f}"])
        nombre(f"g-fen-{d['l']}", d["mse"], src)
    ecrire("genome-gauss-fenetre.csv", ["l", "erreur", "ecart_db"], rows)
    var = [d for d in lignes if d["l"] == 12 and d["kb"] == 2 and d["v"] == 1 and not (d["melangeur"] == "fort" and d["q"] == 8 and d["lloyd"] == 0)]
    for d in var:
        cle = "court" if d["melangeur"] == "court" else (f"lloyd{d['lloyd']}" if d["lloyd"] else f"q{d['q']}")
        nombre(f"g-var-{cle}", d["mse"], src)
        nombre(f"g-var-{cle}-db", 10 * math.log10(d["mse"] / d["borne_shannon"]), src + " (calculé)")
    t1 = json.JSONDecoder().raw_decode(open(G / "gauss-T1.json", encoding="utf-8").read())[0]
    nombre("g-t1", t1["mse"], "mesures/genome/genome/gauss-T1.json")
    nombre("g-t1-db", 10 * math.log10(t1["mse"] / t1["borne_shannon"]), "mesures/genome/genome/gauss-T1.json (calculé)")
    nombre("g-t1-rangees", t1["rangees"], "mesures/genome/genome/gauss-T1.json")
    nombre("g-rangees", statistics.mode(d["rangees"] for d in base), src)
    nombre("g-longueur", statistics.mode(d["poids"] // d["rangees"] for d in base), src + " (poids / rangées)")
    nombre("g-shannon-2", next(d["borne_shannon"] for d in base if d["debit"] == 2.0), src)
    nombre("g-q", statistics.mode(d["q"] for d in base), src)
    # Le nombre de rangées n'est pas le même pour toutes les formes (M1 du juge ronde : « 64 rangées » est
    # faux pour 6 des 7 formes à l = 16) : on le compte par fenêtre, avec ses exceptions.
    for l in (12, 16):
        formes = {}
        for d in base:
            if d["l"] == l:
                formes.setdefault((d["kb"], d["v"]), set()).add(d["rangees"])
        assert all(len(v) == 1 for v in formes.values()), formes  # une forme, un nombre de rangées
        par_forme = {k: next(iter(v)) for k, v in formes.items()}
        mode = statistics.mode(par_forme.values())
        exceptions = sorted(k for k, v in par_forme.items() if v != mode)
        nombre(f"g-l{l}-rangees", mode, src)
        nombre(f"g-l{l}-valeurs", mode * statistics.mode(d["poids"] // d["rangees"] for d in base), src + " (calculé)")
        nombre(f"g-l{l}-exceptions", len(exceptions), src)
        for k, (kb, v) in enumerate(exceptions):
            nombre(f"g-l{l}-exc{k}-kb", kb, src)
            nombre(f"g-l{l}-exc{k}-v", v, src)
            nombre(f"g-l{l}-exc{k}-rangees", par_forme[(kb, v)], src)


def courbes() -> None:
    src = "mesures/genome/genome/csv/verdict-par-tenseur.csv"
    ver = lire_csv(G / "csv/verdict-par-tenseur.csv")
    rows, gains = [], []
    for i, r in enumerate(ver):
        c, role = r["tenseur"].split(".")[1:3]
        role = role.replace("ffn_", "").replace("_exps", "")
        brut = r["bits_brut"]
        rows.append([c, role, f"{float(r['bits_frontiere']):.5f}", f"{float(r['erreur_base']):.6f}",
                     f"{float(r['bits_tourne']):.5f}", "nan" if brut == "nan" else f"{float(brut):.5f}"])
        cle = f"v-{c}-{role}"
        nombre(f"{cle}-bits", float(r["bits_frontiere"]), src)
        nombre(f"{cle}-err", float(r["erreur_base"]), src)
        nombre(f"{cle}-tourne", float(r["bits_tourne"]), src)
        nombre(f"{cle}-gain", float(r["gain_tourne"]), src)
        gains.append(float(r["gain_tourne"]))
        assert abs(float(r["bits_frontiere"]) - float(r["bits_tourne"]) - float(r["gain_tourne"])) < 1e-9
    ecrire("genome-verdict.csv", ["couche", "role", "bits_base", "erreur_base", "bits_tourne", "bits_brut"], rows)
    # L'échantillon du critère W (M2 du juge ronde) : les experts et les rangées par tenseur, lus dans la
    # passe du brin tourné qui a produit les courbes.
    cj = json.load(open(G / "codons-tourne-l12.json", encoding="utf-8"))
    sj = "mesures/genome/genome/codons-tourne-l12.json"
    for k, e in enumerate(cj["experts"]):
        nombre(f"c-expert-{k}", e, sj)
    nombre("c-experts", len(cj["experts"]), sj)
    rang = {t["rangees"] for t in cj["tenseurs"]}
    assert len(rang) == 1, rang
    nombre("c-rangees", rang.pop(), sj + " (rangées de l'échantillon par tenseur)")
    nombre("c-formes", len(cj["formes"]), sj)
    nombre("v-gain-moyen", statistics.fmean(gains), src + " (calculé)")
    nombre("v-gain-min", min(gains), src)
    nombre("v-gain-max", max(gains), src)
    nombre("v-tenseurs", len(gains), src)
    nombre("v-brut-manquants", sum(1 for r in ver if r["bits_brut"] == "nan"), src)
    for norme in ("tourne", "brut"):
        c_src = f"mesures/genome/genome/csv/courbes-{norme}-l12.csv"
        par: dict[str, list] = {}
        for r in lire_csv(G / f"csv/courbes-{norme}-l12.csv"):
            par.setdefault(r["tenseur"], []).append((float(r["bits"]), float(r["erreur"])))
        for t, pts in par.items():
            if t == "global":
                continue
            c, role = t.split(".")[1:3]
            role = role.replace("ffn_", "").replace("_exps", "")
            pts.sort()
            ecrire(f"genome-courbes-{norme}-{c}-{role}.csv", ["bits", "erreur"], [[f"{b:.5f}", f"{e:.6f}"] for b, e in pts])
        nombre(f"c-{norme}-points", sum(len(v) for k, v in par.items() if k != "global"), c_src)


def main() -> int:
    D.mkdir(parents=True, exist_ok=True)
    gauss()
    courbes()
    ecrire("genome-nombres.csv", ["cle", "valeur", "source"], [list(n) for n in NOMBRES])
    for c, v, _ in NOMBRES:
        print(f"{c:22s} {v}")
    print("écrit :", len(list(D.glob("genome-*.csv"))), "fichiers genome-*.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
