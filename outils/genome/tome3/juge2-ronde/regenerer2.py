"""Juge des chiffres du lot « ronde », second flux : les données du lot se régénèrent-elles au bit ?

Tire par `git archive` (sans conversion de fin de ligne : core.autocrlf=false) les quatre scripts du lot et les
mesures qu'ils lisent, dans un dossier temporaire hors du dépôt ; y lance chaque script ; compare chaque fichier
écrit à son blob commité (empreinte git), et la liste des fichiers écrits à la liste des fichiers commités
{eclaireur,genome,duplication,synthese}-* sous memoire/figures/tome3/donnees/. Vérifie aussi : aucun CRLF,
aucun fichier du dépôt modifié (le dépôt n'est pas touché : tout s'écrit dans la copie).

Témoin (--casser) : un octet est ajouté à une copie d'un fichier par lot avant la comparaison ; les quatre
doivent tomber.

  python -I -X utf8 outils/genome/tome3/juge2-ronde/regenerer2.py [--rev HEAD] [--casser] [--fois 2]
Sortie : journaux/regenerer2.csv (ou regenerer2-casser.csv), et le résumé à l'écran.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile

RACINE = pathlib.Path(__file__).resolve().parents[4]
ICI = pathlib.Path(__file__).resolve().parent
LOTS = ("eclaireur", "genome", "duplication", "synthese")
ENTREES = ["mesures/genome/etat-de-l-art", "mesures/genome/genome", "mesures/genome/duplication",
           "mesures/genome/construction/synthese", "mesures/genome/predictif-elagage"]


def git(*args: str) -> bytes:
    r = subprocess.run(["git", "-C", str(RACINE), "-c", "core.autocrlf=false", *args], capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} : {r.stderr.decode('utf-8', 'replace')}")
    return r.stdout


def empreinte_blob(octets: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(octets) + octets).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rev", default="HEAD")
    ap.add_argument("--casser", action="store_true")
    ap.add_argument("--fois", type=int, default=1, help="nombre de passes (chacune dans une copie neuve)")
    a = ap.parse_args()
    commites = {}
    for ligne in git("ls-tree", "-r", a.rev, "memoire/figures/tome3/donnees/").decode().splitlines():
        meta, chemin = ligne.split("\t")
        nom = chemin.rsplit("/", 1)[1]
        if nom.split("-", 1)[0] in LOTS:
            commites[nom] = meta.split()[2]
    scripts = [f"memoire/outils/tome3_{l}.py" for l in LOTS]
    lignes, ecarts = [], 0
    for passe in range(a.fois):
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="juge2-ronde-"))
        try:
            with tarfile.open(fileobj=io.BytesIO(git("archive", "--format=tar", a.rev, "--", *scripts, *ENTREES))) as t:
                t.extractall(tmp, filter="data")
            (tmp / "memoire/figures/tome3/donnees").mkdir(parents=True)
            for s in scripts:
                r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(tmp / s)], capture_output=True, cwd=tmp)
                if r.returncode != 0:
                    print(r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace"))
                    raise SystemExit(f"{s} : code {r.returncode}")
            ecrits = {p.name: p for p in sorted((tmp / "memoire/figures/tome3/donnees").iterdir())}
            casses = set()
            if a.casser:
                for lot in LOTS:
                    nom = sorted(n for n in ecrits if n.startswith(lot + "-"))[0]
                    with open(ecrits[nom], "ab") as f:
                        f.write(b"\n")
                    casses.add(nom)
            for nom in sorted(set(ecrits) | set(commites)):
                if nom not in ecrits:
                    etat, e = "commité, non écrit", ""
                elif nom not in commites:
                    etat, e = "écrit, non commité", empreinte_blob(ecrits[nom].read_bytes())
                else:
                    octets = ecrits[nom].read_bytes()
                    e = empreinte_blob(octets)
                    etat = "égal au bit" if e == commites[nom] else "DIFFÉRENT"
                    if b"\r\n" in octets:
                        etat += " ; CRLF"
                if etat != "égal au bit":
                    ecarts += 1
                lignes.append([passe + 1, nom, commites.get(nom, ""), e, etat, "cassé" if nom in casses else ""])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    sale = git("status", "--porcelain", "--", "memoire/figures/tome3/donnees/", "mesures/genome/").decode()
    sale_lot = [l for l in sale.splitlines() if any(f"/{lot}-" in l for lot in LOTS) or "mesures/genome/" in l]
    nom = "regenerer2-casser.csv" if a.casser else "regenerer2.csv"
    with open(ICI / "journaux" / nom, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["passe", "fichier", "blob_commite", "empreinte_regeneree", "etat", "temoin"])
        w.writerows(lignes)
    n = len(lignes) // a.fois
    print(f"{n} fichiers par passe, {a.fois} passe(s) ; écarts : {ecarts} ; fichiers du lot ou mesures modifiés "
          f"dans le dépôt : {len(sale_lot)}")
    for l in lignes:
        if l[4] != "égal au bit":
            print("  ", l)
    if a.casser:
        return 0 if ecarts == 4 * a.fois else 1
    return 0 if ecarts == 0 and not sale_lot else 1


if __name__ == "__main__":
    sys.exit(main())
