"""Juge des chiffres du second flux, lot « construction » : régénère au bit les fichiers de données du lot.

Une copie de HEAD (git archive, sans conversion de fins de ligne) des trois scripts du lot et des mesures
qu'ils lisent est posée dans un dossier temporaire, avec un dossier de données VIDE (aucun fichier commité
n'y est recopié : un fichier que le script n'écrirait pas manquerait). Les trois scripts y tournent tels
quels (python -I -X utf8) ; chaque fichier écrit est comparé par SHA-256 au blob commité de même nom, et
l'ensemble des fichiers écrits à l'ensemble des fichiers commités du lot (codon-*, synonyme-*, juge-*).

Cassure (--casser) : dans la copie, un appel déplacé d'un expert à un autre de la même couche dans
routage-grille.csv (totaux gardés) ; juge-grille.csv doit différer, seul ou presque.

Les témoins NEUFS du lot (--temoins) : chacun est forcé à faux dans une copie neuve, et le script du lot doit
s'arrêter (code non nul) avant d'écrire ; un témoin qui laisse passer sa cassure est un témoin qui ne sait
pas tomber (SOCLE). Cinq cassures, une par témoin neuf :
  roue      tailles.json : moins_zero_fondus du 20b + 1           -> tome3_codon.py doit tomber
  sansperte k10/frontiere.csv : 3.70639 -> 3.70739                 -> tome3_codon.py doit tomber
  centile   kl-frontiere-768-juge.json : kl_p999 + 0,001            -> tome3_synonyme.py doit tomber
  repere    variantes-768.csv : Q2_0 à 2,60 bits (dans le cadre)    -> tome3_synonyme.py doit tomber
  jetons    routage-grille.csv : un appel de R1 ajouté, sans retrait -> tome3_juge.py doit tomber

    python -I -X utf8 regenerer.py [--casser] [--temoins] [--garder]
"""
from __future__ import annotations

import argparse
import hashlib
import io
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile

RACINE = pathlib.Path(__file__).resolve().parents[4]
SCRIPTS = ["memoire/outils/tome3_codon.py", "memoire/outils/tome3_synonyme.py", "memoire/outils/tome3_juge.py"]
ENTREES = ["mesures/genome/construction", "mesures/genome/predictif-elagage", "mesures/genome/etat-de-l-art/journaux",
           "mesures/disque/placement/juge/seance", "mesures/moteur/O/journaux/o3"]
DONNEES = "memoire/figures/tome3/donnees"


def git(*args: str) -> bytes:
    return subprocess.run(["git", "-C", str(RACINE), *args], check=True, capture_output=True).stdout


def remplacer(p: pathlib.Path, vieux: bytes, neuf: bytes) -> None:
    b = p.read_bytes()
    assert b.count(vieux) >= 1, (p, vieux)
    p.write_bytes(b.replace(vieux, neuf, 1))


def temoins(tete: str) -> int:
    """Chaque témoin neuf forcé à faux dans une copie neuve : le script du lot doit s'arrêter."""
    C = "mesures/genome/construction/"
    cas = {
        "roue": ("memoire/outils/tome3_codon.py", C + "codon/tailles.json",
                 b'"moins_zero_fondus": 1221698587', b'"moins_zero_fondus": 1221698588'),
        "sansperte": ("memoire/outils/tome3_codon.py", C + "synthese/k10/frontiere.csv", b",3.70639,", b",3.70739,"),
        "centile": ("memoire/outils/tome3_synonyme.py", C + "synonyme/kl/kl-frontiere-768-juge.json",
                    b'"kl_p999": 4.065994566823495', b'"kl_p999": 4.066994566823495'),
        "repere": ("memoire/outils/tome3_synonyme.py", C + "synonyme/figures/variantes-768.csv",
                   b"llama-q2_0,2.25,", b"llama-q2_0,2.60,"),
        "jetons": ("memoire/outils/tome3_juge.py", C + "juge/figures/routage-grille.csv", b"\n0,0,", None),
    }
    tombes = 0
    for nom, (script, cible, vieux, neuf) in cas.items():
        tmp = pathlib.Path(tempfile.mkdtemp(prefix=f"juge2-temoin-{nom}-"))
        try:
            archive = git("-c", "core.autocrlf=false", "archive", "--format=tar", tete, *SCRIPTS, *ENTREES)
            with tarfile.open(fileobj=io.BytesIO(archive)) as t:
                t.extractall(tmp, filter="data")
            (tmp / DONNEES).mkdir(parents=True, exist_ok=True)
            p = tmp / cible
            if neuf is None:  # routage-grille : appels_r1 de la couche 0, expert 0, plus un
                lignes = p.read_bytes().split(b"\n")
                for i, l in enumerate(lignes):
                    c = l.split(b",")
                    if c[:2] == [b"0", b"0"]:
                        c[2] = str(int(c[2]) + 1).encode()
                        lignes[i] = b",".join(c)
                p.write_bytes(b"\n".join(lignes))
            else:
                remplacer(p, vieux, neuf)
            r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(tmp / script)], capture_output=True,
                               text=True, encoding="utf-8", cwd=tmp)
            derniere = (r.stderr.strip().splitlines() or [""])[-1][:160]
            etat = "tombe" if r.returncode else "PASSE"
            tombes += int(bool(r.returncode))
            print(f"  témoin {nom:<10} {script:<34} {etat} (code {r.returncode}) {derniere}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{tombes} témoins sur {len(cas)} tombent quand on les force à faux")
    return 0 if tombes == len(cas) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--casser", action="store_true")
    ap.add_argument("--temoins", action="store_true")
    ap.add_argument("--garder", action="store_true")
    a = ap.parse_args()
    tete = git("rev-parse", "HEAD").decode().strip()
    if a.temoins:
        return temoins(tete)
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="juge2-construction-"))
    try:
        archive = git("-c", "core.autocrlf=false", "archive", "--format=tar", tete, *SCRIPTS, *ENTREES)
        with tarfile.open(fileobj=io.BytesIO(archive)) as t:
            t.extractall(tmp, filter="data")
        (tmp / DONNEES).mkdir(parents=True, exist_ok=True)
        if a.casser:
            p = tmp / "mesures/genome/construction/juge/figures/routage-grille.csv"
            lignes = p.read_bytes().split(b"\n")
            # couche 0, expert 0 : un appel de R1 en moins ; couche 0, expert 1 : un appel de R1 en plus
            for i, l in enumerate(lignes):
                c = l.split(b",")
                if c[:2] == [b"0", b"0"]:
                    c[2] = str(int(c[2]) - 1).encode()
                elif c[:2] == [b"0", b"1"]:
                    c[2] = str(int(c[2]) + 1).encode()
                lignes[i] = b",".join(c)
            p.write_bytes(b"\n".join(lignes))
        for s in SCRIPTS:
            r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(tmp / s)], capture_output=True, text=True,
                               encoding="utf-8", cwd=tmp)
            print(f"{s} : code {r.returncode}")
            if r.returncode:
                print(r.stdout[-2000:], r.stderr[-2000:])
                return 2
        ecrits = {p.name for p in (tmp / DONNEES).iterdir() if p.is_file()}
        commites = {pathlib.PurePosixPath(n).name for n in git("ls-tree", "--name-only", tete, DONNEES + "/").decode().split("\n")
                    if n and pathlib.PurePosixPath(n).name.split("-")[0] in ("codon", "synonyme", "juge")}
        egaux, differents = [], []
        for n in sorted(ecrits | commites):
            if n not in ecrits:
                differents.append((n, "commité, non réécrit"))
                continue
            if n not in commites:
                differents.append((n, "écrit, non commité"))
                continue
            neuf = hashlib.sha256((tmp / DONNEES / n).read_bytes()).hexdigest()
            vieux = hashlib.sha256(git("show", f"{tete}:{DONNEES}/{n}")).hexdigest()
            (egaux if neuf == vieux else differents).append((n, neuf[:16] if neuf == vieux else f"{neuf[:12]} ≠ {vieux[:12]}"))
        for n, h in egaux:
            print(f"  égal      {n}  {h}")
        for n, h in differents:
            print(f"  DIFFÉRENT {n}  {h}")
        print(f"\nHEAD {tete[:10]} : {len(egaux)} égaux au bit, {len(differents)} différents"
              f"{' (cassure)' if a.casser else ''} ; {len(commites)} fichiers commités du lot")
        return 1 if differents else 0
    finally:
        if a.garder:
            print("copie gardée :", tmp)
        else:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
