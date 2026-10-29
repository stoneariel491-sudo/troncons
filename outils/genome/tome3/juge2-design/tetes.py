# Juge de design du second flux (Tome III) : relevé des légendes dans les fichiers *-figures.tex.
# Pour chaque \Legende{Nom}{prov}{tête en}{tête fr}{texte en}{texte fr} : la tête porte-t-elle un nombre composé
# par une macro (\num, macro de nombre, mode mathématique, \Pourcent), que le gras de la tête ne touche pas ;
# et la longueur de la légende française, en mots.
# Usage : python -I -X utf8 tetes.py memoire/figures/tome3 > journaux/tetes.txt
import re, sys
from pathlib import Path

R = Path(sys.argv[1])
BS = chr(92)


def args(s, i, n):
    out = []
    for _ in range(n):
        while s[i] in " \n\r\t%":
            if s[i] == "%":
                i = s.index("\n", i)
            i += 1
        assert s[i] == "{", s[i - 20:i + 20]
        d, j = 0, i
        while True:
            if s[j] == "{" and s[j - 1] != BS:
                d += 1
            elif s[j] == "}" and s[j - 1] != BS:
                d -= 1
                if d == 0:
                    break
            j += 1
        out.append(s[i + 1:j])
        i = j + 1
    return out


MACRO_NOMBRE = re.compile(r"\\num|\\Pourcent|\\[A-Za-z]*N[A-Z][A-Za-z]*\b|\\[a-z]+[A-Z][A-Za-z]*\{")
MATH = re.compile(r"\$")
for f in sorted(R.glob("*-figures.tex")):
    s = f.read_text(encoding="utf-8")
    for m in re.finditer(re.escape(BS + "Legende{"), s):
        debut = s.rfind("\n", 0, m.start()) + 1
        if "%" in s[debut:m.start()] or s[m.start() - 1:m.start()] == "@" or "<Nom>" in s[m.end():m.end() + 6]:
            continue  # dans un commentaire, ou la définition elle-même
        nom, prov, ten, tfr, xen, xfr = args(s, m.end() - 1, 6)
        num = bool(MACRO_NOMBRE.search(tfr))
        mat = bool(MATH.search(tfr))
        mots = len(re.sub(r"\\[A-Za-z]+|[{}$]", " ", tfr + " " + xfr).split())
        print(f"{f.name:24s} {nom:22s} nombre_macro={'oui' if num else 'non'} math={'oui' if mat else 'non'} mots_fr={mots}")
