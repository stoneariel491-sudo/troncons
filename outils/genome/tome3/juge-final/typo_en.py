# Juge final : typographie anglaise du Tome III (sources anglaises), relevé mécanique, hors commentaires.
# Relève : espace avant « ; : ! ? » (usage français), guillemets « » hors d'une citation française, virgule
# décimale (texte ou {,}), espace fine avant %, mots français courants hors citation, \og/\fg.
# Usage : python -I -X utf8 typo_en.py <racine tome3>
import pathlib
import re
import sys

racine = pathlib.Path(sys.argv[1]) / "en"
REGLES = [
    ("espace avant ; : ! ?", re.compile(r"[^\s\\$&{(]\s+[;:!?](?=\s|$)")),
    ("guillemets français", re.compile(r"[«»]")),
    ("virgule décimale", re.compile(r"(?<![\d,])\d+(?:\{,\}|,)\d+(?![\d,])")),
    ("espace fine avant %", re.compile(r"\d\s*\\,\s*\\%")),
    ("mot français", re.compile(r"\b(?:chapitre|fichier|tome|nous|avec|sans|pour|mais|donc|où|être|selon)\b", re.I)),
    ("\\og/\\fg", re.compile(r"\\(?:og|fg)\b")),
]
compte = {}
for f in sorted(racine.rglob("*.tex")):
    for n, l in enumerate(f.read_text(encoding="utf-8").split("\n"), 1):
        m = re.search(r"(?<!\\)%", l)
        l = l[:m.start()] if m else l
        for nom, rx in REGLES:
            for x in rx.finditer(l):
                compte[nom] = compte.get(nom, 0) + 1
                a = max(0, x.start() - 70)
                print(f"{f.relative_to(racine)}:{n} [{nom}] …{l[a:x.end() + 50]}…")
print(compte)
