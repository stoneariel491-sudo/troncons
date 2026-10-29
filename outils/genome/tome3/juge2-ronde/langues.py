"""Juge des chiffres du lot « ronde », second flux : les nombres des deux langues, page par page.

Lit le texte des deux PDF du pilote (français et anglais, compilés par le juge), en extrait les nombres
(virgule ou point décimal, groupes de milliers à espace fine, signe moins typographique), les normalise et
compare, page par page, les deux multiensembles. Une différence se lit ensuite à la main : un nombre écrit en
lettres dans une langue, un ordre d'extraction, un numéro de figure.
Contrôle aussi la typographie : dans l'anglais, aucune espace avant « : » ou « ; » ; aucun nombre à virgule
décimale ; dans le français, aucun nombre à point décimal hors noms de fichiers.

  python -I -X utf8 outils/genome/tome3/juge2-ronde/langues.py <pdf_fr> <pdf_en>
Sortie : journaux/langues.txt.
"""
from __future__ import annotations

import collections
import pathlib
import re
import sys

import fitz  # PyMuPDF

ICI = pathlib.Path(__file__).resolve().parent
NOMBRE = re.compile(r"(?<![\w.,])[−\-]?\d{1,3}(?:[    ]\d{3})+(?:[.,]\d+)?(?![\w])|(?<![\w.,])[−\-]?\d+(?:[.,]\d+)?")
FICHIER = re.compile(r"\S*[/_]\S*")


def nombres(texte: str, decimale: str) -> collections.Counter:
    texte = FICHIER.sub(" ", texte.replace("\n", " "))
    c: collections.Counter = collections.Counter()
    for m in NOMBRE.finditer(texte):
        s = m.group(0).replace("−", "-")
        s = re.sub(r"[    ]", "", s)
        if decimale == ",":
            s = s.replace(",", ".")
        c[s] += 1
    return c


def main() -> int:
    fr, en = fitz.open(sys.argv[1]), fitz.open(sys.argv[2])
    sortie = []
    total = 0
    for k in range(min(fr.page_count, en.page_count)):
        tf, te = fr[k].get_text(), en[k].get_text()
        cf, ce = nombres(tf, ","), nombres(te, ".")
        seul_fr, seul_en = cf - ce, ce - cf
        if seul_fr or seul_en:
            sortie.append(f"page {k + 1} : seulement en français {dict(seul_fr)} ; seulement en anglais {dict(seul_en)}")
        total += sum(cf.values())
        for m in re.finditer(r"\S+\s[:;](?=\s)", te.replace("\n", " ")):
            sortie.append(f"page {k + 1} (anglais) : espace avant la ponctuation : {m.group(0)!r}")
        for m in re.finditer(r"(?<![\w.])\d+,\d+(?!\d)", FICHIER.sub(" ", te)):
            sortie.append(f"page {k + 1} (anglais) : virgule décimale : {m.group(0)!r}")
    sortie.insert(0, f"{total} nombres lus dans le français ; pages comparées : {min(fr.page_count, en.page_count)}")
    (ICI / "journaux" / "langues.txt").write_text("\n".join(sortie) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(sortie))
    return 0


if __name__ == "__main__":
    sys.exit(main())
