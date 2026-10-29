# Juge de la rédaction du Tome III (français) : tire au hasard les chiffres du texte à refaire.
#
# Lit chaque chapitre et chaque annexe du tome assemblé (assembler.py), sans les commentaires, et relève
# chaque nombre « informatif » du texte : un décimal (0,1234 ; 0{,}1234 ; 57,1 %) ou un entier d'au moins
# trois chiffres qui n'est pas une année (\num{…} et les milliers séparés par \, compris). Sont exclus les
# nombres d'une commande qui n'est pas du texte (\fichier, \label, \ref, \cref, \cite…, options entre
# crochets, dimensions), les numéros de figure (III-8.6), de section (§ 2.1) et de commit.
# Version 2 (2026-10-29, avant toute vérification) : la version 1 ne prenait pas les décimaux à point
# (0.1446, \SI{71.3}{...}, écrits ainsi aux chapitres 9 et 10) et lisait 399.5 comme l'entier 399 ;
# elle comptait une graine (20261026) comme un chiffre. Son tirage est gardé (tirage-v1.csv), non utilisé.
# Le tirage est stratifié par fichier : --par nombres dans chaque chapitre (moins s'il en a moins), tirés
# par random.Random(graine) dans l'ordre des fichiers ; la graine s'écrit dans la sortie.
#
# Usage : python -I -X utf8 tirage.py memoire/essai/juge-redaction-fr-brouillon --graine 20261029 --par 5 \
#             --sortie outils/genome/tome3/juge-redaction/journaux/tirage.csv
import argparse
import csv
import pathlib
import random
import re
import sys

DEPOT = pathlib.Path(__file__).resolve().parents[4]
RE_COMMENT = re.compile(r"(?<!\\)%.*")
# Commandes dont l'argument n'est pas du texte à chiffres.
RE_HORS = re.compile(r"\\(?:fichier|label|ref|cref|Cref|eqref|pageref|cite|textcite|parencite|autocite|"
                     r"footcite|citeauthor|citeyear|url|href|includegraphics|FigureHorsStyle|FigureSpectres|"
                     r"input|LegendeFigure|sourcefig|texttt|begin|end|hspace|vspace|setlength|"
                     r"Graphe\w*)\*?(?:\[[^\]]*\])?\{[^{}]*\}")
RE_OPTION = re.compile(r"\[[^\]\n]*(?:pt|em|cm|mm|ex|width|linewidth|textwidth)[^\]\n]*\]")
RE_NOMBRE = re.compile(r"(?<![\w.\-/])(\d+(?:[,.]\d+)?)(\s*%)?(?![\w/]|[.,]\d)")


def normaliser(t: str) -> str:
    t = "\n".join(RE_COMMENT.sub("", l) for l in t.splitlines())
    t = re.sub(r"\\num\{([^}]*)\}", r"\1", t)
    t = t.replace("{,}", ",").replace("{.}", ".")
    t = re.sub(r"(?<=\d)\\[,;! ](?=\d{3})", "", t)        # milliers : 5\,087 -> 5087
    t = re.sub(r"(?<=\d)~(?=\d{3}\b)", "", t)
    t = t.replace("\\%", "%").replace("\\,%", " %")
    t = re.sub(r"\\[,;:!]", " ", t)
    return t


def nombres(texte: str):
    lignes = texte.splitlines()
    for i, l0 in enumerate(lignes, 1):
        l = RE_HORS.sub(lambda m: " " * len(m.group(0)), l0)
        l = RE_OPTION.sub(lambda m: " " * len(m.group(0)), l)
        for m in RE_NOMBRE.finditer(l):
            n = m.group(1)
            avant = l[max(0, m.start() - 6):m.start()]
            if re.search(r"(III-|§\s*|chapitre\s*|ch\.\s*|Tome\s*|P|J|K|R|S|B|L|E|blk\.)$", avant):
                continue
            if re.search(r"graine\s*$", l[max(0, m.start() - 8):m.start()]):
                continue
            if "," not in n and "." not in n:
                v = int(n)
                if v < 100 or (1900 <= v <= 2100):
                    continue
            ctx = l0[max(0, m.start() - 70):m.end() + 50].replace("\n", " ")
            yield i, n + ("%" if m.group(2) else ""), ctx.strip()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("dossier")
    p.add_argument("--graine", type=int, required=True)
    p.add_argument("--par", type=int, default=5)
    p.add_argument("--sortie", required=True)
    a = p.parse_args()
    d = DEPOT / a.dossier
    fichiers = sorted((d / "chapitres").glob("*.tex")) + sorted((d / "annexes").glob("*.tex"))
    hasard = random.Random(a.graine)
    lignes = []
    total = 0
    for f in fichiers:
        tous = list(nombres(normaliser(f.read_text(encoding="utf-8"))))
        total += len(tous)
        k = min(a.par, len(tous)) if f.parent.name == "chapitres" else min(2, len(tous))
        choisis = sorted(hasard.sample(range(len(tous)), k))
        for j in choisis:
            i, n, ctx = tous[j]
            lignes.append({"id": f"{f.stem[:2]}-{len(lignes) + 1:02d}", "fichier": f"{f.parent.name}/{f.name}",
                           "ligne": i, "nombre": n, "rang": j, "sur": len(tous), "contexte": ctx})
    with open(DEPOT / a.sortie, "w", encoding="utf-8", newline="") as s:
        s.write(f"# graine {a.graine}, {a.par} par chapitre, 2 par annexe ; {total} nombres candidats\n")
        w = csv.DictWriter(s, fieldnames=list(lignes[0]))
        w.writeheader()
        w.writerows(lignes)
    print(f"graine {a.graine} : {len(lignes)} nombres tirés sur {total} candidats")
    for x in lignes:
        print(f"{x['id']} {x['fichier']}:{x['ligne']} [{x['nombre']}] {x['contexte'][:150]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
