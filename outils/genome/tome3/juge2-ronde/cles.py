"""Juge des chiffres du lot « ronde », second flux : l'inventaire des nombres neufs ou déplacés.

Compare, pour chacun des quatre lots (eclaireur, genome, duplication, synthese), l'état jugé au premier flux
(le parent du commit du second flux) et l'état du second flux (HEAD par défaut) :
  - les clés de <lot>-nombres.csv : neuves, retirées, de valeur changée ;
  - les clés que les figures utilisent (\\<p>Nombre, \\<p>Entier, \\<p>Pct, \\<p>Val), macros à paramètres
    développées (\\SynthPromesse{p3-kappa} -> p3-kappa-bits, p3-kappa-rapport, etc.) : imprimées pour la
    première fois, imprimées avec un autre format, ou devenues seulement des coordonnées.
Écrit journaux/cles.csv (une ligne par clé et par lot) et imprime le compte de chaque état.
Lit les fichiers par `git show <rev>:<chemin>` : rien n'est écrit dans le dépôt hors de journaux/.

  python -I -X utf8 outils/genome/tome3/juge2-ronde/cles.py [--avant <rev>] [--apres <rev>]
"""
from __future__ import annotations

import argparse
import csv
import io
import pathlib
import re
import subprocess

RACINE = pathlib.Path(__file__).resolve().parents[4]
ICI = pathlib.Path(__file__).resolve().parent
LOTS = {"eclaireur": "ecl", "genome": "gen", "duplication": "dup", "synthese": "synth"}
COMMIT_SECOND_FLUX = "6292203"


def git_show(rev: str, chemin: str) -> str:
    r = subprocess.run(["git", "-C", str(RACINE), "show", f"{rev}:{chemin}"], capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"git show {rev}:{chemin} : {r.stderr.decode('utf-8', 'replace')}")
    return r.stdout.decode("utf-8")


def nombres(rev: str, lot: str) -> dict[str, str]:
    texte = git_show(rev, f"memoire/figures/tome3/donnees/{lot}-nombres.csv")
    return {r["cle"]: r["valeur"] for r in csv.DictReader(io.StringIO(texte))}


def accolade(texte: str, i: int) -> int:
    """Indice qui suit l'accolade fermante appariée à celle en texte[i] (qui doit être « { »)."""
    assert texte[i] == "{"
    prof = 0
    for k in range(i, len(texte)):
        c = texte[k]
        if c == "\\":
            continue
        if c == "{" and (k == 0 or texte[k - 1] != "\\"):
            prof += 1
        elif c == "}" and texte[k - 1] != "\\":
            prof -= 1
            if prof == 0:
                return k + 1
    raise ValueError("accolade non fermée")


def sans_commentaires(texte: str) -> str:
    return "\n".join(re.sub(r"(?<!\\)%.*$", "", l) for l in texte.splitlines())


def usages(texte: str, p: str) -> list[tuple[str, str, str]]:
    """(clé, genre, format) de chaque usage d'une clé ; genre : Nombre, Entier, Pct, Val."""
    motif = re.compile(r"\\" + p + r"(Nombre|Entier|Pct|Val)(\[[^\]]*\])?\{([^{}]*)\}")
    return [(m.group(3), m.group(1), (m.group(2) or "")) for m in motif.finditer(texte)]


def developper(texte: str, p: str) -> list[tuple[str, str, str]]:
    """Les usages, avec les macros à paramètres développées sur chacun de leurs appels."""
    texte = sans_commentaires(texte)
    defs: dict[str, tuple[int, str]] = {}
    for m in re.finditer(r"\\newcommand\{\\(\w+)\}\[(\d)\]", texte):
        j = texte.index("{", m.end())
        fin = accolade(texte, j)
        defs[m.group(1)] = (int(m.group(2)), texte[j + 1:fin - 1])
    sortie = []
    for cle, genre, fmt in usages(texte, p):
        if "#" not in cle:
            sortie.append((cle, genre, fmt))
    for nom, (n, corps) in defs.items():
        modeles = [(c, g, f) for c, g, f in usages(corps, p) if "#" in c]
        if not modeles:
            continue
        for m in re.finditer(r"\\" + nom + r"(?![A-Za-z])", texte):
            k, args = m.end(), []
            while len(args) < n and k < len(texte) and texte[k] == "{":
                fin = accolade(texte, k)
                args.append(texte[k + 1:fin - 1])
                k = fin
            if len(args) < n:
                continue  # la définition elle-même, ou un appel incomplet
            for c, g, f in modeles:
                for a in range(n, 0, -1):
                    c = c.replace(f"#{a}", args[a - 1])
                    f = f.replace(f"#{a}", args[a - 1])
                sortie.append((c, g, f))
    return sortie


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--avant", default=f"{COMMIT_SECOND_FLUX}~1")
    ap.add_argument("--apres", default="HEAD")
    a = ap.parse_args()
    lignes = []
    comptes: dict[str, int] = {}
    for lot, p in LOTS.items():
        n0, n1 = nombres(a.avant, lot), nombres(a.apres, lot)
        t0 = git_show(a.avant, f"memoire/figures/tome3/{lot}-figures.tex")
        t1 = git_show(a.apres, f"memoire/figures/tome3/{lot}-figures.tex")
        u0, u1 = developper(t0, p), developper(t1, p)
        imp0 = {(c, g, f) for c, g, f in u0 if g != "Val"}
        imp1 = {(c, g, f) for c, g, f in u1 if g != "Val"}
        cles0 = {c for c, _, _ in u0}
        cles1 = {c for c, _, _ in u1}
        imprimees0 = {c for c, _, _ in imp0}
        imprimees1 = {c for c, _, _ in imp1}
        for c in sorted(set(n0) | set(n1) | cles1):
            if c not in n1 and c in cles1:
                etat = "absente du CSV (erreur de compilation)"
            elif c not in n0:
                etat = "neuve"
            elif c not in n1:
                etat = "retirée"
            elif n0[c] != n1[c]:
                etat = "valeur changée"
            elif c in imprimees1 and c not in imprimees0:
                etat = "imprimée pour la première fois"
            elif c in imprimees1 and {(g, f) for k, g, f in imp1 if k == c} - {(g, f) for k, g, f in imp0 if k == c}:
                etat = "format neuf"
            elif c in cles1 and c not in cles0:
                etat = "coordonnée neuve"
            elif c in imprimees1 or c in cles1:
                etat = "inchangée"
            else:
                etat = "non utilisée"
            formats = sorted({f"{g}{f}" for k, g, f in u1 if k == c})
            lignes.append([lot, c, etat, n0.get(c, ""), n1.get(c, ""), " ; ".join(formats)])
            comptes[etat] = comptes.get(etat, 0) + 1
    (ICI / "journaux").mkdir(exist_ok=True)
    with open(ICI / "journaux" / "cles.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["lot", "cle", "etat", "valeur_avant", "valeur_apres", "usages_apres"])
        w.writerows(lignes)
    for e, n in sorted(comptes.items()):
        print(f"{e:35s} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
