# -*- coding: utf-8 -*-
"""Juge des figures du lot « construction » : régénérer les données des figures et les comparer au bit.

Exporte de git (HEAD, sans conversion de fins de ligne) les scripts du lot et les fichiers qu'ils lisent dans
un dossier temporaire, y lance memoire/outils/tome3_codon.py, tome3_synonyme.py et tome3_juge.py (chacun
écrit sous memoire/figures/tome3/donnees/ de la copie, jamais dans le dépôt), puis compare l'empreinte
SHA-256 de chaque fichier écrit à celle du blob commité du même chemin.

Usage : python -I -X utf8 regenerer.py [--racine DÉPÔT] [--casser]
  --casser : témoin qui doit tomber ; dans la copie, la vitesse de la passe 1 de j1-s2-passes.csv est
             changée (1,98… devient 1,99…) avant de lancer les scripts : au moins un fichier doit différer.
Code de sortie : 0 si chaque fichier régénéré égale son blob, 1 sinon.
"""
import argparse
import hashlib
import io
import os
import subprocess
import sys
import tarfile
import tempfile

CHEMINS = ['memoire/outils', 'memoire/figures/tome3/donnees', 'mesures/genome/construction',
           'mesures/genome/predictif-elagage/histo-12-gptoss20b.npz', 'mesures/genome/etat-de-l-art/journaux',
           'mesures/disque/placement/juge/seance', 'mesures/moteur/O/journaux/o3']
SCRIPTS = ['tome3_codon.py', 'tome3_synonyme.py', 'tome3_juge.py']
PREFIXES = ('codon-', 'synonyme-', 'juge-')


def git(racine, *args):
    return subprocess.run(['git', '-C', racine, '-c', 'core.autocrlf=false', *args], check=True,
                          capture_output=True).stdout


def principal():
    ap = argparse.ArgumentParser()
    ici = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument('--racine', default=os.path.normpath(os.path.join(ici, '..', '..', '..', '..')))
    ap.add_argument('--casser', action='store_true')
    a = ap.parse_args()
    tete = git(a.racine, 'rev-parse', 'HEAD').decode().strip()
    with tempfile.TemporaryDirectory(prefix='juge-construction-') as copie:
        tar = git(a.racine, 'archive', '--format=tar', tete, *CHEMINS)
        with tarfile.open(fileobj=io.BytesIO(tar)) as t:
            t.extractall(copie, filter='data')
        if a.casser:
            # Une unité de fréquence passe d'un octet à l'autre dans la table CODES_CTX dessinée en III-8.2
            # (120b, v1.0, couche 18, up, κ = 1 : octet 0 de 15 à 16, octet 1 de 19 à 18 ; la somme reste
            # 4 096) : codon-octets-v10.csv doit changer. Deux cassures plus grossières font tomber les gardes
            # du lot lui-même avant toute écriture (vu par le juge) : la passe 1 de j1-s2-passes.csv changée
            # (assertion contre j1-s2-verdicts.json) et une fréquence augmentée seule (somme ≠ 4 096).
            p = os.path.join(copie, 'mesures/genome/construction/codon/tables-octets.csv')
            with open(p, 'rb') as f:
                octets = f.read()
            casse = octets.replace(b'\n120b,1.0,18,1,1,0,15\n120b,1.0,18,1,1,1,19\n',
                                   b'\n120b,1.0,18,1,1,0,16\n120b,1.0,18,1,1,1,18\n', 1)
            assert casse != octets, 'les lignes à casser sont introuvables'
            with open(p, 'wb') as f:
                f.write(casse)
        for s in SCRIPTS:
            r = subprocess.run([sys.executable, '-I', '-X', 'utf8', os.path.join(copie, 'memoire', 'outils', s)],
                               capture_output=True, text=True, encoding='utf-8')
            print(f'{s} : code {r.returncode}')
            if r.returncode != 0:
                print(r.stderr)
                return 1
        dossier = os.path.join(copie, 'memoire', 'figures', 'tome3', 'donnees')
        faux = 0
        n = 0
        for nom in sorted(os.listdir(dossier)):
            if not nom.startswith(PREFIXES):
                continue
            with open(os.path.join(dossier, nom), 'rb') as f:
                mien = hashlib.sha256(f.read()).hexdigest()
            blob = hashlib.sha256(git(a.racine, 'show', f'{tete}:memoire/figures/tome3/donnees/{nom}')).hexdigest()
            n += 1
            egal = mien == blob
            faux += 0 if egal else 1
            print(f'{nom:<46} {mien[:16]}  {"égal au blob" if egal else "DIFFÈRE du blob " + blob[:16]}')
        print(f'\nHEAD {tete[:7]} : {n} fichiers régénérés, {n - faux} égaux au bit, {faux} différents.')
        return 0 if faux == 0 else 1


if __name__ == '__main__':
    sys.exit(principal())
