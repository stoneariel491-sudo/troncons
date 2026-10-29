"""Juge des chiffres du lot « ronde », second flux : une phrase barrée revient-elle dans une légende ?

Relève chaque passage barré (~~…~~) des documents Markdown sous genome/ (hors genome/pistes/, autre flux) et
sous memoire/tome3/, en extrait les nombres distinctifs (au moins trois chiffres significatifs, ou un
multiplicateur ×n), et les cherche dans le texte français du pilote (légendes et annotations, pages des
figures). Chaque rencontre se relit à la main : un nombre barré peut revenir à bon droit (rattaché à ce qui
le remplace), ou à tort (la phrase barrée revit).
Témoin (--casser) : un passage barré fabriqué, dont le nombre est imprimé dans une légende (« 0,476 »),
est ajouté ; il doit être trouvé.

  python -I -X utf8 outils/genome/tome3/juge2-ronde/barrees.py <pdf_fr> [--casser]
Sortie : journaux/barrees.txt (ou barrees-casser.txt).
"""
from __future__ import annotations

import pathlib
import re
import sys

import fitz

RACINE = pathlib.Path(__file__).resolve().parents[4]
ICI = pathlib.Path(__file__).resolve().parent
BARRE = re.compile(r"~~(.+?)~~", re.S)
NOMBRE = re.compile(r"×\s?\d+(?:,\d+)?|\d+,\d{2,}|\d+,\d(?=\D)|\d{1,3}(?:[   ]\d{3})+|\d{3,}")


def norme(s: str) -> str:
    """Groupes de milliers recollés (espace fine ou insécable entre chiffres seulement), signe moins unifié."""
    s = s.replace("−", "-")
    return re.sub(r"(?<=\d)[    ](?=\d{3}(?!\d))", "", s)


def distinctif(n: str) -> bool:
    chiffres = re.sub(r"\D", "", n).lstrip("0")
    return n.startswith("×") or len(chiffres) >= 3


def main() -> int:
    casser = "--casser" in sys.argv
    pdf = fitz.open(sys.argv[1])
    texte = norme(" ".join(p.get_text() for p in pdf).replace("\n", " "))
    docs = [p for p in sorted((RACINE / "genome").rglob("*.md")) if "pistes" not in p.parts]
    docs += sorted((RACINE / "memoire/tome3").glob("*.md"))
    passages = []
    for d in docs:
        for m in BARRE.finditer(d.read_text(encoding="utf-8")):
            passages.append((d.relative_to(RACINE).as_posix(), m.group(1)))
    if casser:
        passages.append(("(témoin fabriqué)", "la borne vaut 0,476 bit sous la frontière"))
    sortie = [f"{len(passages)} passages barrés dans {len(docs)} documents"]
    rencontres = 0
    for d, p in passages:
        nombres = sorted({norme(n) for n in NOMBRE.findall(p) if distinctif(n)})
        vus = [n for n in nombres if n in texte]
        if vus:
            rencontres += 1
            extrait = " ".join(p.split())[:220]
            sortie.append(f"- {d} : {vus} dans « {extrait} »")
    sortie.append(f"passages dont un nombre distinctif est imprimé : {rencontres}")
    nom = "barrees-casser.txt" if casser else "barrees.txt"
    (ICI / "journaux" / nom).write_text("\n".join(sortie) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(sortie))
    if casser:
        return 0 if any("témoin fabriqué" in s for s in sortie) else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
