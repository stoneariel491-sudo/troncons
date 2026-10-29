"""Calculs du chapitre « Compression sans perte » : l'entropie des codes de 4 bits d'une
quantification min-max, selon la plage et selon la taille du groupe.

Pourquoi ce calcul : l'étude 03 (fondations/03-entropie.md, § 6) mesure 3,86 bits par code sur
les K-quants et 3,73 à 3,86 bits sur des min-max par groupes de 32 et 64, contre « 0,6 à 1,0 bit »
publiés pour des int4 (arXiv 2606.15789). Ce script refait la chose par un second chemin, la
théorie : il calcule exactement l'entropie des 16 codes d'une source gaussienne ou laplacienne
quantifiée sur une plage R (en écarts-types), et l'estime par Monte-Carlo pour un min-max par
groupes de g poids. Rien n'est mesuré ici : tout est « calculé ».

Sorties (memoire/figures/donnees/) :
  entropie-plage.csv          H(R) exacte, gaussienne et laplacienne : min-max à 16 niveaux sur
                              [-R/2, R/2], et grille symétrique à 15 niveaux (zéro au centre)
  entropie-groupes.csv        H(g) d'un min-max par groupes de g, Monte-Carlo à graine fixe
  entropie-groupes-mesures.csv  les min-max mesurés par l'étude 03 (rd-proxy-4B.json), pour comparer
  entropie-seuils.csv         la plage R qui ramène l'entropie à 0,6, 1, 2 et 3 bits (« inf » : jamais)
Bibliothèque standard seule. Usage : python -I -X utf8 memoire/outils/calculs_entropie.py
"""
import csv
import json
import math
import random
from pathlib import Path

DEPOT = Path(__file__).resolve().parents[2]
SORTIE = DEPOT / "memoire" / "figures" / "donnees"
J03 = DEPOT / "fondations" / "journaux" / "03-entropie"
NIVEAUX = 16  # codes de 4 bits


def ecrire(nom, entetes, lignes):
    SORTIE.mkdir(parents=True, exist_ok=True)
    with open(SORTIE / nom, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(entetes)
        w.writerows(lignes)
    return nom


# Fonctions de répartition, variance unité.
def F_gauss(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def F_laplace(x):
    b = 1.0 / math.sqrt(2.0)  # variance 2 b^2 = 1
    return 0.5 * math.exp(x / b) if x < 0 else 1.0 - 0.5 * math.exp(-x / b)


def entropie_plage(F, R):
    """Entropie (bits) des 16 codes d'une quantification min-max (à point zéro) de [-R/2, R/2] :
    code k (0..15) pour x dans [-R/2 + (k - 1/2) D, -R/2 + (k + 1/2) D[, D = R/15, les deux
    codes extrêmes prenant aussi les queues (écrêtage). Zéro tombe sur la frontière des codes 7
    et 8 : pour une source symétrique, H ne descend jamais sous 1 bit."""
    D = R / (NIVEAUX - 1)
    bornes = [-R / 2 + (k + 0.5) * D for k in range(NIVEAUX - 1)]
    return _entropie_bornes(F, bornes)


def entropie_symetrique(F, R):
    """Entropie (bits) d'une quantification symétrique à 15 niveaux k D, k = -7..7, D = R/14
    (le maximum de |x| vaut R/2 = 7 D), le niveau 0 au centre : H tend vers 0 quand R grandit."""
    D = R / 14
    bornes = [(k + 0.5) * D for k in range(-7, 7)]
    return _entropie_bornes(F, bornes)


def _entropie_bornes(F, bornes):
    cdf = [0.0] + [F(b) for b in bornes] + [1.0]
    h = 0.0
    for k in range(len(cdf) - 1):
        p = cdf[k + 1] - cdf[k]
        if p > 0:
            h -= p * math.log2(p)
    return h


def seuil(F, cible, grille=None):
    """Plage R (en écarts-types) pour laquelle l'entropie vaut `cible` bits ; H décroît en R.
    Rend l'infini si la cible est sous la limite de la grille (1 bit pour le min-max)."""
    grille = grille or entropie_plage
    a, b = 0.5, 1e6
    # Limite de H quand R grandit : 1 bit exactement pour le min-max d'une source symétrique
    # (la moitié des poids de chaque côté de la frontière 7 | 8), 0 pour la grille symétrique.
    # Une cible à moins de 10^-3 bit de cette limite n'est jamais atteinte à une plage finie
    # utile : le calcul en virgule flottante rendrait un croisement fictif.
    if grille(F, b) > cible or cible - grille(F, 1e9) < 1e-3:
        return math.inf
    for _ in range(200):
        m = math.sqrt(a * b)
        if grille(F, m) > cible:
            a = m
        else:
            b = m
    return math.sqrt(a * b)


def entropie_groupes(tirage, g, n_echantillons, graine):
    """Min-max par groupes de g : code = arrondi((x - min) / D), D = (max - min) / 15.
    Histogramme commun à tous les groupes, entropie en bits."""
    rnd = random.Random(graine)
    compte = [0] * NIVEAUX
    groupes = max(1, n_echantillons // g)
    for _ in range(groupes):
        xs = [tirage(rnd) for _ in range(g)]
        lo, hi = min(xs), max(xs)
        D = (hi - lo) / (NIVEAUX - 1)
        for x in xs:
            compte[min(NIVEAUX - 1, int((x - lo) / D + 0.5))] += 1
    n = sum(compte)
    return -sum(c / n * math.log2(c / n) for c in compte if c)


def tirage_gauss(rnd):
    return rnd.gauss(0.0, 1.0)


def tirage_laplace(rnd):
    # Différence de deux exponentielles de paramètre sqrt(2) : laplacienne de variance 1.
    return (rnd.expovariate(1.0) - rnd.expovariate(1.0)) / math.sqrt(2.0)


def main():
    faits = []
    plages = [2.0 + 0.25 * i for i in range(33)] + [10.0 + i for i in range(1, 51)]
    faits.append(ecrire("entropie-plage.csv", ["R", "gauss", "laplace", "gauss_sym", "laplace_sym"],
                        [(f"{R:g}", f"{entropie_plage(F_gauss, R):.5f}", f"{entropie_plage(F_laplace, R):.5f}",
                          f"{entropie_symetrique(F_gauss, R):.5f}", f"{entropie_symetrique(F_laplace, R):.5f}")
                         for R in plages]))

    tailles = [8, 16, 32, 64, 128, 256, 1024, 4096]
    N = 1 << 18
    lignes = []
    for i, g in enumerate(tailles):
        hg = entropie_groupes(tirage_gauss, g, N, 1000 + i)
        hl = entropie_groupes(tirage_laplace, g, N, 2000 + i)
        lignes.append((g, f"{hg:.5f}", f"{hl:.5f}"))
    faits.append(ecrire("entropie-groupes.csv", ["g", "gauss", "laplace"], lignes))

    # Les min-max mesurés par l'étude 03 sur trois tenseurs réels (substituts déquantifiés).
    rd = json.loads((J03 / "rd-proxy-4B.json").read_text(encoding="utf-8-sig"))
    mesures = []
    for t in rd:
        mesures.append((32, f"{t['MM4_g32']['H_codes']:.5f}", t["tenseur"], f"{t['kurtosis']:.2f}"))
        mesures.append((64, f"{t['MM4_g64']['H_codes']:.5f}", t["tenseur"], f"{t['kurtosis']:.2f}"))
    faits.append(ecrire("entropie-groupes-mesures.csv", ["g", "H", "tenseur", "kurtosis"], mesures))

    def f(v):
        return "inf" if math.isinf(v) else f"{v:.3f}"
    faits.append(ecrire("entropie-seuils.csv", ["bits", "R_gauss", "R_laplace", "R_gauss_sym", "R_laplace_sym"],
                        [(c, f(seuil(F_gauss, c)), f(seuil(F_laplace, c)),
                          f(seuil(F_gauss, c, entropie_symetrique)), f(seuil(F_laplace, c, entropie_symetrique)))
                         for c in (0.6, 1.0, 1.01, 2, 3)]))
    print(f"{len(faits)} fichiers écrits sous {SORTIE.relative_to(DEPOT)}")


if __name__ == "__main__":
    main()
