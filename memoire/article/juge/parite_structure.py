"""Parité EN/FR par un autre chemin que parite_nombres.py : structure et nombres, élément par élément, dans l'ordre.

Lit les deux .tex (chemins en argument), retire les commentaires, et compare :
- la suite des commandes de structure (section, subsection, paragraph, figure, table, proposition...) ;
- la suite des clés citées, dans l'ordre ;
- la suite des étiquettes de provenance (\\mes, \\calc, \\litt) ;
- la suite des nombres dans l'ordre (séparateur décimal normalisé), en ne gardant que les nombres
  hors des noms de fichiers (\\fichier{...}) ;
- le nombre de \\barre, \\textbf, \\emph.
Témoin : --casser retire le premier \\cite du français ; la parité des citations doit tomber.
"""
import re
import sys
from pathlib import Path


def corps(chemin, casser=False):
    t = Path(chemin).read_text(encoding="utf-8").split(r"\begin{document}", 1)[1]
    t = "\n".join(re.sub(r"(?<!\\)%.*", "", l) for l in t.splitlines())
    if casser:
        t = t.replace(r"\citep{", r"\XXX{", 1)
    return t


def nombres_hors_fichiers(t):
    t = re.sub(r"\\fichier\{[^}]*\}", " ", t)
    t = re.sub(r"\\(label|cref|Cref|ref)\{[^}]*\}", " ", t)
    t = t.replace("{,}", ".")
    t = re.sub(r"(\d),(\d)", r"\1.\2", t)
    return re.findall(r"\d+(?:\.\d+)?", t)


def main():
    casser = "--casser" in sys.argv
    en, fr = sys.argv[1], sys.argv[2]
    E, F = corps(en), corps(fr, casser)
    ok = True
    struct = r"\\(section\*?|subsection|paragraph|begin\{(?:figure|table|proposition|corollary|lemma|remark|proof|equation|itemize|enumerate|quote)\})"
    for nom, motif in [("structure", struct), ("citations", r"\\cite[pt]?\{([^}]*)\}"),
                       ("provenance", r"\\(mes|calc|litt)\b"), ("figures incluses", r"\\Figure\{(\d)\}\{([\d.]+)\}")]:
        a, b = re.findall(motif, E), re.findall(motif, F)
        tient = a == b
        ok &= tient
        print(f"{nom}: EN {len(a)}, FR {len(b)}, suite égale : {tient}")
        if not tient:
            for i, (x, y) in enumerate(zip(a, b)):
                if x != y:
                    print("   premier écart", i, x, y)
                    break
    a, b = nombres_hors_fichiers(E), nombres_hors_fichiers(F)
    tient = a == b
    ok &= tient
    print(f"nombres dans l'ordre (hors fichiers et étiquettes) : EN {len(a)}, FR {len(b)}, suite égale : {tient}")
    if not tient:
        import difflib
        for op in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
            if op[0] != "equal":
                print("   ", op[0], a[op[1]:op[2]], b[op[3]:op[4]])
    for c in ("barre", "textbf", "emph"):
        x, y = len(re.findall(r"\\" + c + r"\{", E)), len(re.findall(r"\\" + c + r"\{", F))
        print(f"\\{c}: EN {x}, FR {y}")
    print("PARITÉ :", "tient" if ok else "tombe")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
