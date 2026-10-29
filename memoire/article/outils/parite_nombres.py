"""Parité des nombres entre les deux versions de l'article (anglaise et française).

Extrait du corps de chaque .tex (après \\begin{document}, commentaires retirés) tous les nombres, normalisés
(séparateur décimal « , » ou « {,} » ramené à « . »), et compare les deux multiensembles. Rend 0 si les deux versions
portent exactement les mêmes nombres, autant de fois chacun ; 1 sinon, en listant les écarts.
Usage, depuis la racine du dépôt : python -I -X utf8 memoire/article/outils/parite_nombres.py
Témoin : --casser ajoute un nombre à la version française ; l'outil doit alors rendre 1.
"""
import re
import sys
from collections import Counter
from pathlib import Path

RACINE = Path("memoire/article")
NOMBRE = re.compile(r"\d+(?:\.\d+)?")


def nombres(chemin: Path, casser: bool = False) -> Counter:
    texte = chemin.read_text(encoding="utf-8").split("\\begin{document}", 1)[1]
    texte = "\n".join(re.sub(r"(?<!\\)%.*", "", ligne) for ligne in texte.splitlines())
    texte = texte.replace("{,}", ".")
    texte = re.sub(r"(\d),(\d)", r"\1.\2", texte)
    # Les étiquettes (sec:… / sec-…), les numéros de section du dépôt (§ 5.3) et les chemins comptent aussi :
    # ils sont les mêmes dans les deux langues.
    if casser:
        texte += " 424242 "
    return Counter(NOMBRE.findall(texte))


def main() -> int:
    casser = "--casser" in sys.argv
    en = nombres(RACINE / "en" / "troncons-article.tex")
    fr = nombres(RACINE / "fr" / "troncons-article.tex", casser)
    ecarts = {n: (en[n], fr[n]) for n in set(en) | set(fr) if en[n] != fr[n]}
    print(f"nombres distincts : EN {len(en)}, FR {len(fr)} ; occurrences : EN {sum(en.values())}, FR {sum(fr.values())}")
    for n, (a, b) in sorted(ecarts.items()):
        print(f"  écart : {n} — EN {a}, FR {b}")
    print("PARITÉ : " + ("tient" if not ecarts else f"tombe ({len(ecarts)} nombres)"))
    return 0 if not ecarts else 1


if __name__ == "__main__":
    sys.exit(main())
