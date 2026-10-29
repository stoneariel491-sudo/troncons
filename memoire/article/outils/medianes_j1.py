"""Médianes par fichier des passes du J1 (séance s2 du lot A), pour le tableau du coût par jeton de l'article.

Lit mesures/genome/construction/codon/j1-s2-passes.csv (commité) et écrit, pour A (v1.0 d'origine) et B (v1.2),
la médiane des quatre passes de chaque colonne utile. Aucune autre donnée.
Usage, depuis la racine du dépôt : python -I -X utf8 memoire/article/outils/medianes_j1.py
Témoin : la médiane des jetons/s doit égaler celle de j1-s2-verdicts.json (jetons_s_mediane_A et _B) ; l'outil
s'arrête sinon.
"""
import csv
import json
import statistics
import sys
from pathlib import Path

DOSSIER = Path("mesures/genome/construction/codon")
COLONNES = ["jetons_s", "prefill_jetons_s", "octets_troncons_par_jeton", "defauts_par_jeton",
            "s_lectures_par_jeton", "ms_decodage_par_jeton", "ms_copie_par_jeton", "debit_lecture_go_s",
            "pointe_ensemble_travail"]


def main() -> int:
    lignes = list(csv.DictReader(open(DOSSIER / "j1-s2-passes.csv", encoding="utf-8")))
    verdicts = json.load(open(DOSSIER / "j1-s2-verdicts.json", encoding="utf-8"))
    sortie = {}
    for f in "AB":
        choisies = [l for l in lignes if l["fichier"] == f]
        sortie[f] = {c: statistics.median(float(l[c]) for l in choisies) for c in COLONNES}
        sortie[f]["passes"] = len(choisies)
        attendu = verdicts[f"jetons_s_mediane_{f}"]
        if abs(sortie[f]["jetons_s"] - attendu) > 1e-12:
            print(f"TÉMOIN TOMBÉ : médiane {f} {sortie[f]['jetons_s']} au lieu de {attendu}", file=sys.stderr)
            return 1
    print(json.dumps(sortie, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
