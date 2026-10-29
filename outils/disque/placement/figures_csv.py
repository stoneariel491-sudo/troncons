"""Données des figures du placement disque, en CSV pour pgfplots (genome/placement-pour-le-memoire.md § 2).

  python -I -X utf8 outils/disque/placement/figures_csv.py

Écrit sous mesures/disque/placement/figures/ :
- carte-volume.csv : pour chaque fichier, l'occupation du volume par cases de 1/2 000 du volume
  (fichier, case, fraction_debut, grappes du fichier dans la case, extents qui commencent dans la case) ;
- temps-<passe>.csv : débit par seconde pendant une passe (lectures achevées dans la seconde) ;
- lectures-<passe>.csv : un point par lecture (LCN, débit par lecture, morceaux), pour les nuages.
"""
import csv
import glob
import json
import os
import pathlib

R = pathlib.Path(__file__).resolve().parents[3]
M = R / "mesures/disque/placement"
FIG = M / "figures"
CASES = 2000


def carte_volume():
    lignes = []
    for f in sorted(glob.glob(str(M / "carte-*.json")) + glob.glob(str(M / "p2b-*/carte-*.json"))):
        c = json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
        total = c["grappes_volume"]
        occ = [0] * CASES
        deb = [0] * CASES
        for vcn, n, lcn in c["liste_extents"]:
            if lcn < 0:
                continue
            deb[min(CASES - 1, lcn * CASES // total)] += 1
            a = lcn
            while n > 0:
                k = min(CASES - 1, a * CASES // total)
                fin_case = (k + 1) * total // CASES
                m = min(n, max(1, fin_case - a))
                occ[k] += m
                a += m
                n -= m
        nom = pathlib.Path(c["fichier"]).name
        for k in range(CASES):
            if occ[k] or deb[k]:
                lignes.append([nom, k, round(k / CASES, 5), occ[k], deb[k]])
    with open(FIG / "carte-volume.csv", "w", newline="", encoding="utf-8") as g:
        w = csv.writer(g)
        w.writerow(["fichier", "case", "fraction_debut", "grappes", "extents_commencant"])
        w.writerows(lignes)


def temps_et_nuages():
    for f in sorted(glob.glob(str(M / "p*/*-lire-*.csv"))):
        nom = pathlib.Path(f).stem
        with open(f, newline="", encoding="utf-8") as g:
            L = list(csv.DictReader(g))
        if not L:
            continue
        fin = max(float(l["fin_us"]) for l in L)
        sec = [0] * (int(fin // 1e6) + 1)
        for l in L:
            sec[int(float(l["fin_us"]) // 1e6)] += int(l["longueur"])
        with open(FIG / f"temps-{nom}.csv", "w", newline="", encoding="utf-8") as g:
            w = csv.writer(g)
            w.writerow(["seconde", "go_s"])
            for i, b in enumerate(sec[:-1]):  # la dernière seconde est partielle
                w.writerow([i, round(b / 1e9, 4)])
        if "-lire-tout-" in nom:
            with open(FIG / f"lectures-{nom}.csv", "w", newline="", encoding="utf-8") as g:
                w = csv.writer(g)
                w.writerow(["decalage_gio", "lcn_frac", "debit_go_s", "morceaux", "debut_s"])
                for l in L:
                    d = int(l["longueur"]) / (float(l["fin_us"]) - float(l["debut_us"])) / 1e3
                    w.writerow([round(int(l["decalage"]) / 2**30, 4), l["lcn_frac"], round(d, 4), l["morceaux"], round(float(l["debut_us"]) / 1e6, 3)])


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    carte_volume()
    temps_et_nuages()
    print("\n".join(sorted(os.listdir(FIG))))


if __name__ == "__main__":
    main()
