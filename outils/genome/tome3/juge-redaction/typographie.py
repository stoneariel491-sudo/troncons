# Juge de la rédaction du Tome III (français) : les décimaux à point qui s'imprimeraient tels quels.
#
# Dans la version française, siunitx rend \num{0.1522} et \SI{5.6}{\percent} avec une virgule
# (memoire/commun/preambule.tex, \sisetup{output-decimal-marker={,}} sous \ifanglais faux). Un décimal écrit
# hors de \num, \SI, \numrange (en texte ou en mode mathématique, « $0.013 \pm 0.016$ ») s'imprime avec un
# point, au milieu de décimaux à virgule. L'outil compte ces décimaux par fichier, hors commentaires,
# commandes de fichier et d'étiquette, numéros de section (§ 5.3), versions (v1.2) et noms (blk.8, L00.down).
# Témoin : --casser ajoute « 0.123 » au premier chapitre ; le compte doit monter d'un (code 1).
# Usage : python -I -X utf8 typographie.py memoire/essai/juge-redaction-fr-brouillon [--casser]
import argparse
import pathlib
import re
import sys

DEPOT = pathlib.Path(__file__).resolve().parents[4]
RE_COMMENT = re.compile(r"(?<!\\)%.*")
RE_COMMANDES = re.compile(r"\\(?:num|SI|numrange|SIrange|ang|qty|fichier|texttt|label|cref|Cref|ref|url|href|"
                          r"includegraphics|FigureHorsStyle|FigureSpectres|input|cite|parencite|textcite|"
                          r"setlength|hspace|vspace)\*?(?:\[[^\]]*\])?\{[^{}]*\}(?:\{[^{}]*\})?")
RE_POINT = re.compile(r"(?<![\w.\-/\\])(\d+\.\d+)(?![\w.])")


def compter(t: str):
    t = "\n".join(RE_COMMENT.sub("", l) for l in t.splitlines())
    t = RE_COMMANDES.sub(" ", t)
    t = re.sub(r"\[[^\]\n]*\]", " ", t)
    t = re.sub(r"\{[0-9.]+\\(?:linewidth|textwidth)\}", " ", t)
    sorties = []
    for m in RE_POINT.finditer(t):
        avant = t[max(0, m.start() - 6):m.start()]
        if re.search(r"(§\s*|§§\s*|,\s*|et\s)$", avant) and re.search(r"§", t[max(0, m.start() - 30):m.start()]):
            continue
        sorties.append(t[max(0, m.start() - 50):m.end() + 25].replace("\n", " "))
    return sorties


def main():
    p = argparse.ArgumentParser()
    p.add_argument("dossier")
    p.add_argument("--casser", action="store_true")
    a = p.parse_args()
    d = DEPOT / a.dossier
    fichiers = sorted((d / "chapitres").glob("*.tex")) + sorted((d / "annexes").glob("*.tex"))
    total = 0
    for i, f in enumerate(fichiers):
        t = f.read_text(encoding="utf-8")
        if a.casser and i == 1:
            t += "\nUn décimal à point : 0.123 ;\n"
        s = compter(t)
        total += len(s)
        print(f"{f.name:<24} {len(s):>4}")
        for x in s[:4]:
            print(f"      … {x} …")
    print(f"total : {total}")
    if a.casser:
        return 1 if any("0.123" in x for x in compter(fichiers[1].read_text(encoding="utf-8")
                                                        + "\nUn décimal à point : 0.123 ;\n")) else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
