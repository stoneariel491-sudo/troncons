"""Juge des chiffres du second flux, lot « construction » : chaque cadre de chaque figure contre ses données.

Le second flux a posé une règle (G1 et G2 du juge des chiffres) : aucun point hors du cadre, et le script
s'arrête si un point sort. Le lot l'a appliquée à III-9.3, III-8.8, III-9.6, III-8.3 et III-8.5 (c) ; les
autres bornes sont tapées dans les .tex. Cet outil prend TOUTES les bornes : celles du script sont lues
dans les *-nombres.tex ; celles qui sont tapées sont recopiées ici à la main, et leur texte exact est
cherché dans le .tex (TAPEES ci-dessous : si le .tex change, l'outil s'arrête au lieu de juger un cadre qui
n'existe plus). Puis il vérifie chaque série tracée (les CSV du lot, régénérés au bit par regenerer.py) et
chaque nombre posé comme coordonnée. La liste des axes est écrite ici à la main, figure et panneau.

Remarque : la « règle » du lot (bornes tirées des données, assertion que tout point est dedans) est vraie
par construction, puisque les bornes sont calculées depuis les mêmes points ; elle ne peut pas tomber.
C'est cet outil, qui lit aussi les bornes tapées, qui peut.

Cassure (--casser) : la borne haute de III-8.8 ramenée à 10 (celle du premier flux) ; un point doit sortir.

    python -I -X utf8 cadres.py [--casser]
"""
from __future__ import annotations

import argparse
import csv
import math
import pathlib
import re
import sys

RACINE = pathlib.Path(__file__).resolve().parents[4]
FIG = RACINE / "memoire/figures/tome3"
DON = FIG / "donnees"


def lc(n):
    with open(DON / n, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def macros() -> dict[str, float]:
    m = {}
    for n in ("codon", "synonyme", "juge"):
        for x in re.finditer(r"\\def\\(\w+)\{([^}]*)\}", (DON / f"{n}-nombres.tex").read_text(encoding="utf-8")):
            try:
                m[x.group(1)] = float(x.group(2))
            except ValueError:
                pass
    return m


def col(n, c, filtre=None):
    out = []
    for r in lc(n):
        if filtre and not filtre(r):
            continue
        v = r[c]
        if v in ("", "nan"):
            continue
        out.append(float(v))
    return out


# Les bornes tapées que l'outil recopie, et le texte exact qui les porte dans le .tex.
TAPEES = [
    ("codon", "xmin=0.108, xmax=0.245, ymin=0.108, ymax=0.245"),
    ("codon", "xmin=0.108, xmax=0.245, ymin=-2.5, ymax=2.5"),
    ("codon", "point meta min=0, point meta max=1.8"),
    ("codon", "xmin=-0.7, xmax=11.7, ymin=-0.012, ymax=0.16"),
    ("codon", "xmin=0, xmax=0.18"),
    ("codon", "xmin=0.5, xmax=8.5, ymin=1.55, ymax=3.15"),
    ("codon", "xmin=678, xmax=718, ymin=1.55, ymax=3.15"),
    ("codon", "xmin=-0.6, xmax=3.6, ymin=0, ymax=3.7"),
    ("codon", "ymin=0, ymax=2.25"),
    ("codon", "xmin=-0.6, xmax=5.6, ymin=0, ymax=4.5"),
    ("juge", "xmin=-0.03, xmax=1.03, ymin=\\JconsNPartAxeMin, ymax=\\JconsNPartAxeMax"),
    ("juge", "ymin=0, ymax=0.16"),
    ("juge", "ymin=5e-5, ymax=1"),
    ("synonyme", "xmin=0, xmax=2880, ymin=1e-3, ymax=1e3"),
    ("synonyme", "xmin=0, xmax=2880, ymin=1e-3, ymax=0.1"),
    ("synonyme", "xmin=0, xmax=2880, ymin=0, ymax=1.02"),
    ("synonyme", "xmin=1e-2, xmax=10, ymin=3e-4, ymax=1.4"),
    ("synonyme", "xmin=\\SynoNForXmin, xmax=\\SynoNForXmax"),
    ("synonyme", "xmin=\\SynoNVarXmin, xmax=\\SynoNVarXmax, ymin=\\SynoNVarYmin, ymax=\\SynoNVarYmax"),
    ("codon", "ymin=\\CodonNSansPerteMin, ymax=\\CodonNSansPerteMax"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--casser", action="store_true")
    a = ap.parse_args()
    for lot, texte in TAPEES:
        src = (FIG / f"{lot}-figures.tex").read_text(encoding="utf-8")
        assert texte in src, f"borne introuvable dans {lot}-figures.tex : {texte}"
    M = macros()
    if a.casser:
        M["JconsNPartAxeMax"] = 10.0
    R: list[tuple[str, float, float, list[float], str]] = []  # (axe, bas, haut, valeurs, quoi)

    # III-8.3 (a)(b) : codon-figures.tex, bornes tapées 0,108–0,245 et −2,5–2,5.
    for m in ("20b", "120b"):
        R.append(("III-8.3 (a) x", 0.108, 0.245, col(f"codon-theoreme-{m}.csv", "x"), m))
        R.append(("III-8.3 (a) y", 0.108, 0.245, col(f"codon-theoreme-{m}.csv", "y"), m))
        R.append(("III-8.3 (b) y", -2.5, 2.5, col(f"codon-theoreme-{m}.csv", "residu"), m))
    # III-8.2 : l'échelle de couleur va de 0 à 1,8.
    for v in ("v10", "v12"):
        R.append(("III-8.2 couleur", 0, 1.8, col(f"codon-octets-{v}.csv", "v"), v))
    # III-8.5 (a) −0,012–0,16 ; (b) 0–0,18 ; (c) bornes du script.
    R.append(("III-8.5 (a) y", -0.012, 0.16, col("codon-colonne.csv", "gain"), "gain"))
    R.append(("III-8.5 (b) x", 0, 0.18, [M["CodonNColonneModele"], M["CodonNZeroGain"]], "barres"))
    for c in ("sans_perte", "zero", "colonne"):
        R.append(("III-8.5 (c) y", M["CodonNSansPerteMin"], M["CodonNSansPerteMax"], col("codon-sans-perte.csv", c), c))
    # III-8.6 (a)(b) : y 1,55–3,15 ; (b) x 678–718.
    for v in ("v10", "v12"):
        R.append(("III-8.6 (a)(b) y", 1.55, 3.15, col(f"codon-j1-{v}.csv", "jetons_s"), v))
        R.append(("III-8.6 (b) x", 678, 718, col(f"codon-j1-{v}.csv", "mo_par_jeton"), v))
    R.append(("III-8.6 (a) y", 1.55, 3.15, [M["CodonNJiBandeBas"], M["CodonNJiBandeHaut"]], "bande ±2σ"))
    R.append(("III-8.6 (b) x,y", 1.55, 3.15, [M["CodonNJiPreditB"]], "losange prédit (y)"))
    R.append(("III-8.6 (b) x", 678, 718, [M["CodonNJiMoB"], M["CodonNJiMoA"]], "Mo par jeton"))
    iso = lc("codon-j1-iso.csv")
    R.append(("III-8.6 (b) y", 1.55, 3.15, [float(r["jetons_s"]) for r in iso if 678 <= float(r["mo_par_jeton"]) <= 718], "courbe iso"))
    # III-8.6 bis (c) 0–3,7 ; encart 0–2,25 ; (d) 0–4,5.
    for p in ("p1", "p2", "p3", "p4", "mediane"):
        R.append(("III-8.6 bis (c) y", 0, 3.7, col("codon-j1-motif.csv", p), p))
    R.append(("III-8.6 bis encart y", 0, 2.25, col("codon-j1-encart.csv", "go_s"), "barres"))
    R.append(("III-8.6 bis (d) y", 0, 4.5, col("codon-j1-cascade.csv", "haut"), "marches"))
    # III-8.8 (a) : bornes du script ; (b) 0–0,16.
    R.append(("III-8.8 (a) y", M["JconsNPartAxeMin"], M["JconsNPartAxeMax"], col("juge-codon-experts.csv", "part"), "parts"))
    R.append(("III-8.8 (a) x", -0.03, 1.03, col("juge-codon-experts.csv", "x"), "profondeur"))
    R.append(("III-8.8 (a) y", M["JconsNPartAxeMin"], M["JconsNPartAxeMax"], [M["JconsNPartVingt"], M["JconsNPartCent"]], "tirets"))
    R.append(("III-8.8 (b) y", 0, 0.16, [M["JconsNGainVingt"], M["JconsNGainCent"], M["JconsNSeuilCdeux"]], "barres, seuil"))
    # III-9.1 (a) log 1e-3–1e3 ; (b) log 1e-3–0,1 ; (b′) 0–1,02.
    R.append(("III-9.1 (a) y", 1e-3, 1e3, col("synonyme-spectre.csv", "lambda_calib"), "λ calib (les nan ne sont pas tracés)"))
    R.append(("III-9.1 (a) y", 1e-3, 1e3, col("synonyme-spectre.csv", "lambda_eval"), "λ éval"))
    for c in ("e_frontiere", "e_synonyme"):
        R.append(("III-9.1 (b) y", 1e-3, 0.1, col("synonyme-energie.csv", c), c))
    for c in ("synonyme_calib", "synonyme_eval", "frontiere_calib", "frontiere_eval"):
        R.append(("III-9.1 (b′) y", 0, 1.02, col("synonyme-cumul.csv", c), c))
    # III-9.2 : x log 1e-2–10 ; y log 3e-4–1,4 (les P nuls ne sont pas tracés).
    for c in ("q2_0", "frontiere", "lambda1", "lambda0"):
        R.append(("III-9.2 y", 3e-4, 1.4, [v for v in col("synonyme-survie.csv", c) if v > 0], c))
    R.append(("III-9.2 x", 1e-2, 10, col("synonyme-survie.csv", "t"), "grille"))
    R.append(("III-9.2 x", 1e-2, 10, col("synonyme-quantiles.csv", "mediane") + col("synonyme-quantiles.csv", "p999"), "marques"))
    # III-9.3 : bornes du script, points et bandes.
    for cle in ("un-frontiere", "zero-un", "zero-frontiere"):
        R.append(("III-9.3 x", M["SynoNForXmin"], M["SynoNForXmax"], col(f"synonyme-foret-{cle}.csv", "d"), cle))
        mo = lc(f"synonyme-foret-{cle}-moyennes.csv")
        R.append(("III-9.3 x", M["SynoNForXmin"], M["SynoNForXmax"],
                  [float(r["moyenne"]) + s * float(r["deux_sigma"]) for r in mo for s in (-1, 1)], cle + " bandes"))
    # III-9.6 : cadre du script, trois variantes et leurs barres ; Q2_0 et l'exact doivent être HORS du cadre.
    var = {r["variante"]: r for r in lc("synonyme-variantes.csv")}
    for v in ("frontiere", "synonyme-l1", "synonyme-l0"):
        r = var[v]
        R.append(("III-9.6 x", M["SynoNVarXmin"], M["SynoNVarXmax"], [float(r["bits"])], v))
        R.append(("III-9.6 y", M["SynoNVarYmin"], M["SynoNVarYmax"],
                  [float(r["kl"]) - float(r["deux_sigma_f"]), float(r["kl"]) + float(r["deux_sigma_f"])], v + " ±2σ"))
    hors = []
    for v in ("llama-q2_0", "exact"):
        r = var[v]
        x, y = float(r["bits"]), float(r["kl"])
        dedans = M["SynoNVarXmin"] <= x <= M["SynoNVarXmax"] and M["SynoNVarYmin"] <= y <= M["SynoNVarYmax"]
        hors.append((v, x, y, dedans))
    # III-10.3 : y log 5e-5–1.
    for c in ("frontiere", "lambda1", "lambda0", "exact"):
        R.append(("III-10.3 y", 5e-5, 1, col("juge-kl-fenetres.csv", c), c))

    sortis = 0
    for axe, bas, haut, vals, quoi in R:
        if not vals:
            print(f"  VIDE    {axe:<22} {quoi}")
            sortis += 1
            continue
        lo, hi = min(vals), max(vals)
        dehors = [v for v in vals if not (bas <= v <= haut)]
        # marge relative au cadre (log pour les axes logarithmiques détectés par bas > 0 et haut/bas > 50)
        if bas > 0 and haut / bas > 50:
            ml = (math.log10(lo) - math.log10(bas)) / (math.log10(haut) - math.log10(bas))
            mh = (math.log10(haut) - math.log10(hi)) / (math.log10(haut) - math.log10(bas))
        else:
            ml, mh = (lo - bas) / (haut - bas), (haut - hi) / (haut - bas)
        etat = "dedans " if not dehors else "DEHORS "
        sortis += len(dehors)
        print(f"  {etat} {axe:<22} [{bas:g}, {haut:g}]  {quoi:<34} min {lo:.6g} max {hi:.6g}  "
              f"marges {100 * ml:.1f} % / {100 * mh:.1f} %" + (f"  {len(dehors)} hors : {dehors[:4]}" if dehors else ""))
    for v, x, y, dedans in hors:
        print(f"  {'DEDANS ' if dedans else 'hors   '} III-9.6 repère {v} ({x:.4f} bits, KL {y:.4f}) : doit être hors du cadre")
        sortis += int(dedans)
    print(f"\n{len(R)} séries ou repères contre leur cadre : {sortis} point(s) mal placé(s){' (cassure)' if a.casser else ''}")
    return 1 if sortis else 0


if __name__ == "__main__":
    sys.exit(main())
