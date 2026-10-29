# Juge de la rédaction du Tome III (français) : les chiffres barrés dans les sources reviennent-ils, non
# barrés, dans le texte ?
#
# 1. Relève chaque passage barré (~~…~~) des sources du tome : genome/*.md, genome/mimetisme/**/*.md,
#    genome/pistes/{tropicale,spectres}/*.md, memoire/tome3/*.md (jugements des figures), et chaque
#    \barre{…} des chapitres eux-mêmes.
# 2. En tire les nombres « informatifs » (décimaux, ou entiers d'au moins trois chiffres hors années).
# 3. Cherche chaque nombre dans le texte du tome assemblé, hors \barre{…} et hors commentaires, et rend
#    chaque occurrence avec son contexte : c'est une liste à lire, pas un verdict (un nombre barré peut
#    revenir à bon droit, cité comme ce qui a été barré, ou parce qu'il désigne une autre grandeur).
# Témoin : un nombre barré ajouté en mémoire, non barré, au premier chapitre, doit sortir (--casser).
#
# Usage : python -I -X utf8 barres.py memoire/essai/juge-redaction-fr-brouillon [--casser]
import argparse
import pathlib
import re
import sys

DEPOT = pathlib.Path(__file__).resolve().parents[4]
# Un passage barré ne passe pas une ligne vide et ne dépasse pas 800 signes : un « ~~ » cité dans le texte
# (JUGEMENT-figures-latents.md l. 49) ne doit pas barrer tout ce qui le suit.
RE_BARRE_MD = re.compile(r"~~((?:(?!\n[ \t]*\n).){1,800}?)~~", re.S)
RE_NOMBRE = re.compile(r"(?<![\w.,\-/])(\d+(?:[,.]\d+)?)(?![\w/]|[.,]\d)")
RE_COMMENT = re.compile(r"(?<!\\)%.*")


def nombres(t):
    for m in RE_NOMBRE.finditer(t):
        n = m.group(1).replace(".", ",")
        if "," in n or (n.isdigit() and int(n) >= 100 and not 1900 <= int(n) <= 2100):
            if n.startswith("0,") and len(n) <= 3:
                continue  # 0,1 0,5 : trop communs pour être lus
            yield n


def sans_barres_tex(t):
    """Retire \\barre{...} (accolades équilibrées) et les commentaires."""
    t = "\n".join(RE_COMMENT.sub("", l) for l in t.splitlines())
    out, i = [], 0
    while True:
        j = t.find("\\barre{", i)
        if j < 0:
            out.append(t[i:])
            break
        out.append(t[i:j])
        k, prof = j + len("\\barre{"), 1
        while k < len(t) and prof:
            prof += {"{": 1, "}": -1}.get(t[k], 0)
            k += 1
        out.append(" " * (k - j))
        i = k
    return "".join(out)


def normaliser(t):
    t = re.sub(r"\\num\{([^}]*)\}", r"\1", t)
    t = re.sub(r"\\SI\{([^}]*)\}", r"\1", t)
    t = t.replace("{,}", ",")
    t = re.sub(r"(?<=\d)\\[,;! ](?=\d{3})", "", t)
    # décimaux à point (chapitres 0, 9, 10, 13) -> virgule ; pas les numéros de section (§ 5.3) ni v1.2
    t = re.sub(r"(§+\s*)?\b(\d+)\.(\d+)",
               lambda m: m.group(0) if m.group(1) else f"{m.group(2)},{m.group(3)}", t)
    return t


def main():
    p = argparse.ArgumentParser()
    p.add_argument("dossier")
    p.add_argument("--casser", action="store_true")
    a = p.parse_args()
    sources = sorted(set((DEPOT / "genome").glob("*.md")) | set((DEPOT / "genome/mimetisme").rglob("*.md"))
                     | set((DEPOT / "genome/pistes/tropicale").glob("*.md"))
                     | set((DEPOT / "genome/pistes/spectres").glob("*.md"))
                     | set((DEPOT / "memoire/tome3").glob("JUGEMENT*.md")))
    sources = [s for s in sources if "second-tirage" not in s.name and "REPRISE" not in s.name]
    barres = {}
    for s in sources:
        for m in RE_BARRE_MD.finditer(s.read_text(encoding="utf-8", errors="replace")):
            for n in nombres(m.group(1)):
                barres.setdefault(n, set()).add(f"{s.relative_to(DEPOT)}")
    d = DEPOT / a.dossier
    fichiers = sorted((d / "chapitres").glob("*.tex")) + sorted((d / "annexes").glob("*.tex"))
    for f in fichiers:
        brut = f.read_text(encoding="utf-8")
        for m in re.finditer(r"\\barre\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}", brut):
            for n in nombres(normaliser(m.group(1))):
                barres.setdefault(n, set()).add(f"{f.name} (\\barre)")
    textes = {f: normaliser(sans_barres_tex(f.read_text(encoding="utf-8"))) for f in fichiers}
    if a.casser:
        n0 = sorted(barres)[0]
        textes[fichiers[1]] += f"\nUn chiffre barré revenu : {n0}.\n"
    sorties = 0
    trouve_casse = False
    for n in sorted(barres, key=lambda x: float(x.replace(",", "."))):
        motif = re.compile(r"(?<![\w,\-/])" + re.escape(n) + r"(?![\d])")
        for f, t in textes.items():
            for i, l in enumerate(t.splitlines(), 1):
                if motif.search(l):
                    if a.casser and "Un chiffre barré revenu" in l:
                        trouve_casse = True
                    j = motif.search(l).start()
                    print(f"[{n}] {f.name}:{i} | barré dans {', '.join(sorted(barres[n]))[:120]}")
                    print(f"      … {l[max(0, j - 110):j + 60].strip()} …")
                    sorties += 1
    print(f"{len(barres)} nombres barrés dans les sources ; {sorties} occurrences non barrées à lire")
    if a.casser:
        return 1 if trouve_casse else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
