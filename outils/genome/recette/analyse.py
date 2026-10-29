"""Second chemin du verdict W : refait, depuis les CSV par rangée de `genome codons`, les courbes
débit-distorsion par allocation lagrangienne et les bits à erreur égale, tenseur par tenseur et en
global, avec toute la comptabilité des bits. Plusieurs CSV sur les mêmes rangées (formes différentes)
se fusionnent : chaque rangée choisit parmi toutes les formes mesurées.

Comptabilité (bits par poids), par tenseur :
  brin + fenêtre initiale + 3 bits d'indice de forme par rangée (+ 16 bits de σ par rangée en « tourne ») :
      lus dans le CSV (colonne bits_*) ;
  tables : une table de 2^8 valeurs de 16 bits par forme, pour le tenseur entier (32 experts) ;
  échelles E8M0 (seulement en « brut ») : δ de F1 + 8/2880 de médianes ;
  alignement de chaque matrice d'expert sur 4 096 octets, au pire : 32 768 / 8 294 400.
Frontière F1 par tenseur : base + δ + 8/2880 + 0,00007 de tables.

Utilisation :
  python -I -X utf8 analyse.py NORME SORTIE.csv CSV1 [CSV2 ...] > verdict.json
"""
import csv
import json
import math
import sys
from collections import defaultdict

CSV_F1 = "~/dev/active/troncons/decisions/journaux/arbitre/csv/f1-par-tenseur.csv"
POIDS_TENSEUR = 2880 * 2880 * 32
MEDIANES = 8 / 2880
ALIGNEMENT = 32768 / 8294400


def lire_f1():
    f1 = {}
    with open(CSV_F1, newline="", encoding="utf8") as f:
        for l in csv.DictReader(f):
            d = float(l["delta"])
            f1[l["tenseur"]] = {
                "frontiere": float(l["base"]) + d + MEDIANES + 0.00007,
                "sans_perte": float(l["codes_a_ctx"]) + d + MEDIANES + 0.000062,
                "echelles": d + MEDIANES,
                "erreur_f1": float(l["erreur_base_centres_communs"]),
            }
    return f1


def lire_rangees(fichiers):
    """{(tenseur, expert, rangée): {"energie", "err_base", "formes": {nom: (err, bits)}}}"""
    rangees = {}
    formes = []
    for fi in fichiers:
        with open(fi, newline="", encoding="utf8") as f:
            r = csv.reader(f)
            tete = next(r)
            noms = [tete[i][4:] for i in range(5, len(tete), 2)]
            formes += [n for n in noms if n not in formes]
            for l in r:
                cle = (l[0], int(l[1]), int(l[2]))
                d = rangees.setdefault(cle, {"energie": float(l[3]), "err_base": float(l[4]), "formes": {}})
                for k, n in enumerate(noms):
                    d["formes"][n] = (float(l[5 + 2 * k]), float(l[6 + 2 * k]))
    return rangees, formes


def courbe(lignes, extra_par_rangee, n_lambda=2000):
    """Points (bits par poids, erreur relative) de l'allocation lagrangienne (chaque rangée prend la
    forme qui minimise err + λ · bits), pour n_lambda valeurs de λ en progression géométrique."""
    import numpy as np
    noms = sorted(lignes[0]["formes"])
    E = np.array([[l["formes"][n][0] for n in noms] for l in lignes])
    B = np.array([[l["formes"][n][1] for n in noms] for l in lignes])
    poids = 2880 * len(lignes)
    energie = sum(l["energie"] for l in lignes)
    echelle = energie / poids
    pts = []
    for i in range(n_lambda):
        lam = echelle * 10 ** (-9 + 13 * i / (n_lambda - 1))
        k = np.argmin(E + lam * B, axis=1)
        idx = np.arange(len(lignes))
        pts.append(((B[idx, k].sum() + extra_par_rangee * len(lignes)) / poids, E[idx, k].sum() / energie))
    return sorted(set(pts))


def bits_a_erreur(pts, cible):
    for (b0, e0), (b1, e1) in zip(pts, pts[1:]):
        if e0 >= cible >= e1 and e0 > e1:
            t = (math.log(e0) - math.log(cible)) / (math.log(e0) - math.log(e1))
            return b0 + t * (b1 - b0)
    return float("nan")


def main():
    norme, sortie_csv, fichiers = sys.argv[1], sys.argv[2], sys.argv[3:]
    f1 = lire_f1()
    rangees, formes = lire_rangees(fichiers)
    par_t = defaultdict(list)
    for (t, e, r), d in rangees.items():
        if len(d["formes"]) == len(formes):
            par_t[t].append(d)
    tables = len(formes) * 256 * 16 / POIDS_TENSEUR
    res = {"norme": norme, "formes": formes, "fichiers": fichiers, "tenseurs": []}
    lignes_csv = []
    toutes, extra_global = [], []
    for t, lignes in par_t.items():
        fixe = tables + ALIGNEMENT + (f1[t]["echelles"] if norme == "brut" else 0.0)
        pts = courbe(lignes, fixe * 2880)
        energie = sum(l["energie"] for l in lignes)
        cible = sum(l["err_base"] for l in lignes) / energie
        b = bits_a_erreur(pts, cible)
        res["tenseurs"].append({
            "tenseur": t, "rangees": len(lignes), "erreur_base_echantillon": cible, "erreur_base_f1": f1[t]["erreur_f1"],
            "bits_frontiere": f1[t]["frontiere"], "bits_recette": b, "gain_bits": f1[t]["frontiere"] - b,
            "gain_relatif": (f1[t]["frontiere"] - b) / f1[t]["frontiere"],
            "erreur_min_courbe": pts[-1][1], "erreur_max_courbe": pts[0][1],
        })
        for p in pts:
            lignes_csv.append((norme, t, p[0], p[1]))
        for l in lignes:
            toutes.append(l)
            extra_global.append(fixe * 2880)
    # global : un seul λ pour toutes les rangées
    poids = 2880 * len(toutes)
    energie = sum(l["energie"] for l in toutes)
    cible = sum(l["err_base"] for l in toutes) / energie
    extra = sum(extra_global) / len(toutes)
    pts = courbe(toutes, extra, 1000)
    b = bits_a_erreur(pts, cible)
    front = sum(f1[t["tenseur"]]["frontiere"] * t["rangees"] for t in res["tenseurs"]) / sum(t["rangees"] for t in res["tenseurs"])
    sp = sum(f1[t["tenseur"]]["sans_perte"] * t["rangees"] for t in res["tenseurs"]) / sum(t["rangees"] for t in res["tenseurs"])
    gagnes = sum(1 for t in res["tenseurs"] if t["gain_bits"] > 0)
    res["global"] = {"erreur_base": cible, "bits_frontiere": front, "bits_sans_perte": sp, "bits_recette": b,
                     "gain_bits": front - b, "gain_relatif": (front - b) / front,
                     "tenseurs_gagnes": gagnes, "tenseurs": len(res["tenseurs"]),
                     "verdict_W": "marche" if gagnes == len(res["tenseurs"]) and front - b > 0 else "ne marche pas"}
    for p in pts:
        lignes_csv.append((norme, "global", p[0], p[1]))
    with open(sortie_csv, "w", newline="", encoding="utf8") as f:
        w = csv.writer(f)
        w.writerow(["norme", "tenseur", "bits", "erreur"])
        for l in lignes_csv:
            w.writerow([l[0], l[1], f"{l[2]:.6f}", f"{l[3]:.7f}"])
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
