# Juge de la rédaction du Tome III (français) : refait la correction neuve du chapitre 4 (rédacteur A),
# « substituer n'est jamais meilleur que retirer l'expert » (genome/duplication.md § 0 point 6,
# genome/05-synthese.md § 3.2) démentie par mesures/genome/duplication/csv/paralogues.csv.
# Compte, par couche, les experts où l'erreur de sortie de la couche est plus basse en substituant le
# paralogue qu'en retirant l'expert (couche_substitue < couche_retire), et les deux moyennes.
# Témoin : en échangeant les deux colonnes (--casser), chaque compte k sur n devient n − k − (égalités).
import argparse
import csv
import pathlib
import statistics
import sys

DEPOT = pathlib.Path(__file__).resolve().parents[4]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--casser", action="store_true")
    a = p.parse_args()
    lignes = list(csv.DictReader(open(DEPOT / "mesures/genome/duplication/csv/paralogues.csv", encoding="utf-8")))
    par = {}
    for l in lignes:
        s, r = float(l["couche_substitue"]), float(l["couche_retire"])
        if a.casser:
            s, r = r, s
        par.setdefault(int(l["couche"]), []).append((s, r))
    for c in sorted(par):
        v = par[c]
        k = sum(1 for s, r in v if s < r)
        print(f"couche {c:>2} : substituer meilleur pour {k} sur {len(v)} ; moyennes {statistics.fmean(s for s, _ in v):.4f} "
              f"(substitué) contre {statistics.fmean(r for _, r in v):.4f} (retiré)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
