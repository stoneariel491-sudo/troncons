# Juge de la rédaction du Tome III (français) : chaque énoncé (théorème, proposition, lemme, corollaire)
# est-il suivi de sa démonstration ? Rend, par chapitre, les énoncés qui ne sont pas suivis d'un
# environnement proof avant l'énoncé suivant, avec leur titre et les 300 signes qui suivent (une preuve
# peut être écrite en prose, « Démonstration » ou renvoi : c'est à lire).
# Usage : python -I -X utf8 enonces.py memoire/essai/juge-redaction-fr-brouillon
import pathlib
import re
import sys

DEPOT = pathlib.Path(__file__).resolve().parents[4]
RE_COMMENT = re.compile(r"(?<!\\)%.*")
RE_ENONCE = re.compile(r"\\begin\{(theoreme|proposition|lemme|corollaire)\}(\[[^\]]*\])?")


def main():
    d = DEPOT / sys.argv[1]
    total, sans = 0, 0
    for f in sorted((d / "chapitres").glob("*.tex")):
        t = "\n".join(RE_COMMENT.sub("", l) for l in f.read_text(encoding="utf-8").splitlines())
        ms = list(RE_ENONCE.finditer(t))
        for i, m in enumerate(ms):
            total += 1
            fin_enonce = t.find("\\end{" + m.group(1) + "}", m.end())
            suivant = ms[i + 1].start() if i + 1 < len(ms) else len(t)
            entre = t[fin_enonce:suivant]
            if "\\begin{proof}" not in entre:
                sans += 1
                print(f"{f.name} : {m.group(1)} {m.group(2) or ''}")
                print("      … " + entre[len('\\end{' + m.group(1) + '}'):][:300].replace("\n", " ") + " …")
    print(f"{total} énoncés ; {sans} sans environnement proof avant l'énoncé suivant")
    return 0


if __name__ == "__main__":
    sys.exit(main())
