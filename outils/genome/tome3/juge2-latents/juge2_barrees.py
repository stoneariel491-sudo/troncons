"""Juge des chiffres du lot « espaces latents », second flux : une phrase barrée revient-elle dans une légende ?

Écrit pour troncons le 2026-10-27. Relève chaque passage barré (~~…~~) des documents Markdown commités du dépôt
(tous, pistes et mimétisme compris : on les lit, on n'y écrit pas), le découpe en suites de cinq mots
(minuscules, ponctuation retirée), et cherche chacune dans le texte des légendes et des annotations de
memoire/figures/tome3/latents-figures.tex au commit jugé (macros LaTeX retirées, nombres des macros remplacés
par leur valeur française). Témoin (--casser) : une phrase barrée tirée au hasard (graine du juge) est glissée
dans le texte des légendes ; elle doit être trouvée.

  python -I -X utf8 juge2_barrees.py [--casser] [--commit 326969f] > barrees.json
"""
from __future__ import annotations

import json
import random
import re
import subprocess
import sys

DEPOT = "~/dev/active/troncons"
GRAINE = 2710202602


def git(*a: str) -> str:
    return subprocess.run(["git", "-C", DEPOT, "-c", "core.autocrlf=false", *a], check=True, capture_output=True,
                          text=True, encoding="utf-8", errors="replace").stdout


def mots(s: str) -> list[str]:
    s = s.lower().replace("’", "'")
    s = re.sub(r"[^\w'%,.]+", " ", s)
    s = re.sub(r"(?<!\d)[,.]|[,.](?!\d)", " ", s)
    return s.split()


def ngrammes(m: list[str], n: int = 5) -> set[tuple]:
    return {tuple(m[i:i + n]) for i in range(len(m) - n + 1)}


def texte_legendes(tex: str, chiffres: str) -> str:
    val = {}
    for l in chiffres.splitlines():
        m = re.match(r"\\providecommand\{\\(Lat\w+)\}\{\\EF\{.*?\}\{(.*)\}\}$", l)
        if m:
            val[m.group(1)] = m.group(2).replace("{,}", ",").replace("\\,", " ").replace("\\ensuremath{-}", "-")
    t = re.sub(r"\\(Lat\w+)(\{\})?", lambda m: " " + val.get(m.group(1), "") + " ", tex)
    t = re.sub(r"%.*", " ", t)
    t = re.sub(r"\\[a-zA-Z]+\*?", " ", t)
    t = re.sub(r"[{}$\\^_~]", " ", t)
    return t


def main() -> int:
    casser = "--casser" in sys.argv
    commit = sys.argv[sys.argv.index("--commit") + 1] if "--commit" in sys.argv else "326969f"
    fichiers = [f for f in git("ls-tree", "-r", "--name-only", commit).splitlines() if f.endswith(".md")]
    barres = []
    for f in fichiers:
        try:
            s = git("show", f"{commit}:{f}")
        except subprocess.CalledProcessError:
            continue
        for m in re.finditer(r"~~(.+?)~~", s, re.S):
            barres.append((f, m.group(1)))
    tex = git("show", f"{commit}:memoire/figures/tome3/latents-figures.tex")
    chif = git("show", f"{commit}:memoire/figures/tome3/donnees/latents-chiffres.tex")
    leg = texte_legendes(tex, chif)
    temoin = None
    if casser:
        rnd = random.Random(GRAINE)
        longues = [b for b in barres if len(mots(b[1])) >= 8]
        temoin = rnd.choice(longues)
        leg = leg + " " + temoin[1]
    lg = ngrammes(mots(leg))
    trouves = []
    for f, b in barres:
        commun = ngrammes(mots(b)) & lg
        if commun:
            trouves.append({"fichier": f, "barre": b[:200], "suites_communes": [" ".join(c) for c in sorted(commun)][:5]})
    res = {"outil": "outils/genome/tome3/juge2-latents/juge2_barrees.py", "commit": commit,
           "documents_lus": len(fichiers), "passages_barres": len(barres),
           "mots_des_legendes": len(mots(leg)), "retours": trouves}
    if casser:
        res["temoin_glisse"] = {"fichier": temoin[0], "barre": temoin[1][:200]}
        res["temoin_trouve"] = any(t["fichier"] == temoin[0] and t["barre"] == temoin[1][:200] for t in trouves)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
