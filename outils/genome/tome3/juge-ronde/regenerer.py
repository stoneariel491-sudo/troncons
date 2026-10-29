"""Juge du lot « ronde » : régénère les CSV du lot par ses propres scripts et les compare au bit.

Écrit par le juge le 2026-10-27. Les scripts du lot (memoire/outils/tome3_{eclaireur,synthese,genome,
duplication}.py) sont lancés tels quels, sans être lus. Pour chaque fichier memoire/figures/tome3/donnees/
<lot>-*.csv, l'empreinte git (git hash-object) du fichier régénéré est comparée à celle du blob commité
(git rev-parse HEAD:<chemin>). Un fichier qui diffère est copié dans journaux/regen/ puis remis à son
contenu commité (git show HEAD:<chemin>), pour ne rien laisser de modifié dans le dépôt.

Contrôles de plus : aucune fin de ligne CRLF, séparateur virgule, et l'état `git status --porcelain`
des dossiers memoire/ et mesures/ avant et après chaque script (un script qui écrirait ailleurs se voit).

Témoin (déclaré avant) : --casser ajoute un octet à la copie régénérée d'un fichier avant la
comparaison ; ce fichier doit alors tomber.

Usage : python -I -X utf8 regenerer.py [--casser]
"""
from __future__ import annotations

import os
import subprocess
import sys
import time

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", "..", "..", ".."))
DONNEES = os.path.join(RACINE, "memoire", "figures", "tome3", "donnees")
JOURNAUX = os.path.join(ICI, "journaux")
CASSER = "--casser" in sys.argv
sys.stdout.reconfigure(encoding="utf-8")


def git(*a, binaire=False):
    r = subprocess.run(["git", "-C", RACINE, *a], capture_output=True)
    return r.stdout if binaire else r.stdout.decode("utf-8").strip()


def etat():
    return set(git("status", "--porcelain", "--", "memoire", "mesures").splitlines())


def main():
    os.makedirs(os.path.join(JOURNAUX, "regen"), exist_ok=True)
    lignes = ["lot,fichier,octets,blob_commite,blob_regenere,au_bit,crlf,duree_s"]
    total = {"au bit": 0, "diffère": 0}
    for lot in ("eclaireur", "synthese", "genome", "duplication"):
        fichiers = sorted(f for f in os.listdir(DONNEES) if f.startswith(lot + "-") and f.endswith(".csv"))
        avant = etat()
        t0 = time.time()
        r = subprocess.run([sys.executable, "-I", "-X", "utf8", os.path.join(RACINE, "memoire", "outils", f"tome3_{lot}.py")],
                           cwd=RACINE, capture_output=True)
        duree = time.time() - t0
        apres = etat()
        if r.returncode != 0:
            print(lot, "ÉCHEC", r.stderr.decode("utf-8", "replace")[-800:])
        neufs = sorted(apres - avant)
        if neufs:
            print(lot, "changements hors données attendues :", neufs)
        for i, f in enumerate(fichiers):
            rel = f"memoire/figures/tome3/donnees/{f}"
            commite = git("rev-parse", f"HEAD:{rel}")
            chemin = os.path.join(DONNEES, f)
            octets = open(chemin, "rb").read()
            if CASSER and i == 0:
                octets = octets + b" "
            tmp = os.path.join(JOURNAUX, "regen", f + ".tmp")
            open(tmp, "wb").write(octets)
            regen = git("hash-object", tmp)
            os.remove(tmp)
            au_bit = regen == commite
            crlf = b"\r\n" in octets
            if not au_bit and not CASSER:
                open(os.path.join(JOURNAUX, "regen", f), "wb").write(octets)
                open(chemin, "wb").write(git("show", f"HEAD:{rel}", binaire=True))
            total["au bit" if au_bit else "diffère"] += 1
            lignes.append(f"{lot},{f},{len(octets)},{commite},{regen},{int(au_bit)},{int(crlf)},{duree:.1f}")
        print(f"{lot:12s} {len(fichiers)} fichiers, script {duree:.1f} s, code {r.returncode}")
    if not CASSER:
        open(os.path.join(JOURNAUX, "regenerer.csv"), "w", encoding="utf-8", newline="\n").write("\n".join(lignes) + "\n")
    print(("TÉMOIN --casser : " if CASSER else "") + str(total))


if __name__ == "__main__":
    main()
