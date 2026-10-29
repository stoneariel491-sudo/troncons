"""Juge des chiffres du lot « espaces latents », second flux : compiler le pilote du lot, en français et en
anglais, sur les fichiers du commit jugé, et relever erreurs, boîtes, renvois et pages.

Écrit pour troncons le 2026-10-27.

  1. `git archive <commit> memoire` dans un brouillon hors du dépôt (fins de ligne du commit) ; le pilote du lot
     (memoire/essai/pilote-tome3-latents.tex, ignoré par git) y est copié, ses chemins tournés vers le brouillon.
  2. Aucun contournement. Depuis la mise à jour de MiKTeX 26.2 → 26.5 du 2026-10-27 (vers 12 h 22 ; LaTeX
     2026-06-01), thmtools 0.76 ne sait plus déclarer un théorème à compteur partagé : « Command \\c@proposition
     already defined » aux lignes 190 à 195 du préambule commun, pour tout document (reproduit sur un fichier de
     neuf lignes ; amsthm seul passe). lualatex tourne donc sans -halt-on-error : une erreur fatale efface le PDF
     du même nom dans le dossier courant, même avec -output-directory (vérifié sur un faux PDF). Chaque erreur est
     rangée selon sa ligne : celles des \\declaretheorem du préambule commun d'un côté, toutes les autres de
     l'autre. Les figures n'emploient aucun théorème ; le préambule n'est ni au lot ni au juge.
  3. lualatex deux passes par langue (trois si le journal demande encore de relancer) ; journal : erreurs, boîtes
     trop pleines ou trop creuses, références indéfinies, « Float too large », pages.
  4. Le texte des pages (pdftotext de MiKTeX) pour y retrouver les nombres imprimés.

  python -I -X utf8 juge2_compiler.py <brouillon> [--commit 326969f] > compilation.json
"""
from __future__ import annotations

import io
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tarfile

DEPOT = pathlib.Path("~/dev/active/troncons")
PILOTE = DEPOT / "memoire/essai/pilote-tome3-latents.tex"
RE_ERREUR = re.compile(r"^! (.*)\n(?:.*\n){0,9}?l\.(\d+) (.*)", re.M)


def bilan(log: pathlib.Path) -> dict:
    t = log.read_text(encoding="utf-8", errors="replace")
    pages = re.search(r"Output written on .*?\((\d+) pages?", t, re.S)
    toutes = len(re.findall(r"^! ", t, re.M))
    preambule = [e for e in RE_ERREUR.findall(t) if "already defined" in e[0] and "declaretheorem" in e[2]]
    return {
        "erreurs": toutes,
        "erreurs_du_preambule_commun_thmtools": len(preambule),
        "erreurs_hors_preambule": toutes - len(preambule),
        "boites_trop_pleines": len(re.findall(r"Overfull \\[hv]box", t)),
        "boites_trop_creuses": len(re.findall(r"Underfull \\[hv]box", t)),
        "references_indefinies": len(re.findall(r"Reference .* undefined|There were undefined references", t)),
        "relancer": "Rerun to get" in t,
        "float_too_large": len(re.findall(r"Float too large", t)),
        "pages": int(pages.group(1)) if pages else 0,
        "moteur": t.splitlines()[0][:100],
    }


def main() -> int:
    args = sys.argv[1:]
    commit = args[args.index("--commit") + 1] if "--commit" in args else "326969f"
    br = pathlib.Path([a for a in args if not a.startswith("--") and a != commit][0]).resolve()
    racine = br / "racine"
    if racine.exists():
        shutil.rmtree(racine)
    racine.mkdir(parents=True)
    tar = subprocess.run(["git", "-C", str(DEPOT), "-c", "core.autocrlf=false", "-c", "core.eol=lf", "archive",
                          "--format=tar", commit, "--", "memoire"], check=True, capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(tar)) as t:
        t.extractall(racine, filter="data")
    src = PILOTE.read_text(encoding="utf-8")
    r = racine.as_posix()
    src = src.replace("~/dev/active/troncons/memoire", r + "/memoire")
    src = src.replace(r"\newcommand{\Depot}{~/dev/active/troncons}", r"\newcommand{\Depot}{" + r + "}")
    (br / "pilote-j2.tex").write_text(src, encoding="utf-8", newline="\n")
    res = {"outil": "outils/genome/tome3/juge2-latents/juge2_compiler.py", "commit": commit}
    for langue, nom, cmd in (("fr", "pilote-j2", ["pilote-j2.tex"]),
                             ("en", "pilote-j2-en", ["-jobname=pilote-j2-en", r"\def\ANGLAIS{1}\input{pilote-j2.tex}"])):
        passe = 0
        for passe in (1, 2, 3):
            subprocess.run(["lualatex", "-interaction=nonstopmode", *cmd], cwd=str(br), capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
            if passe >= 2 and not bilan(br / f"{nom}.log")["relancer"]:
                break
        res[langue] = {"passes": passe, **bilan(br / f"{nom}.log")}
        pdft = shutil.which("pdftotext")
        if pdft:
            subprocess.run([pdft, "-layout", f"{nom}.pdf", f"{nom}.txt"], cwd=str(br), capture_output=True)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
