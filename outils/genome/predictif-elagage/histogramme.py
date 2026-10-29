"""Loi conjointe exacte (échelle e, δ de ligne, code) de chaque tenseur d'experts MXFP4.

Tout le débit-distorsion de l'étude (élagage, quantification par contexte, base de la
frontière) se calcule sur ces comptes, sans relire les poids : pour une partition des codes et
une reconstruction par contexte, l'erreur et l'entropie conditionnelle sont des sommes sur
(e, δ, code). C'est le geste de l'étude 07 (raffinement_mxfp4.py, loi (e, code)), étendu au δ de
ligne, que le décodeur connaît avant les codes.

Sortie : un .npz compressé, `comptes` de forme (tenseurs, 256, 17, 16) en uint32 (δ borné à
±8, indice δ + 8), et les noms des tenseurs.

Témoin : la somme des comptes de chaque tenseur égale son nombre de poids ; et la loi (e, code)
obtenue en sommant sur δ redonne, pour les 12 tenseurs de la frontière, H(code) = 3,860 bits et
une erreur de base de 4,2920 % (raffinement-mxfp4-gptoss20b.json), vérifié par debit_distorsion.py.

Utilisation : python -I -X utf8 histogramme.py [--toutes-couches] [--fichier F] SORTIE.npz
"""
from __future__ import annotations

import sys
import time

import numpy as np

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import mxfp4 as mx  # noqa: E402


def main():
    fichier = mx.FICHIER_20B
    if "--fichier" in sys.argv:
        fichier = sys.argv[sys.argv.index("--fichier") + 1]
    sortie = sys.argv[-1]
    lec = mx.lecteur(fichier)
    if "--toutes-couches" in sys.argv:
        n = int(lec.meta[[k for k in lec.meta if k.endswith(".block_count")][0]])
        couches = tuple(range(n))
    else:
        couches = mx.COUCHES
    tenseurs = mx.tenseurs_etude(lec, couches)
    comptes = np.zeros((len(tenseurs), 256, 17, 16), dtype=np.uint32)
    t0 = time.time()
    for i, t in enumerate(tenseurs):
        E, R, C = mx.forme(t)
        for e in range(E):
            codes, ech = mx.expert(lec, t, e)
            med = mx.mediane_ligne(ech)
            d = np.clip(ech.astype(np.int16) - med[:, None].astype(np.int16), -8, 8) + 8
            cle = (np.repeat(ech.astype(np.int64), 32, axis=1) * 17
                   + np.repeat(d.astype(np.int64), 32, axis=1)) * 16 + codes
            comptes[i] += np.bincount(cle.ravel(), minlength=256 * 17 * 16).reshape(256, 17, 16).astype(np.uint32)
        assert int(comptes[i].sum(dtype=np.int64)) == E * R * C, t.nom
        print(f"{t.nom} : {time.time() - t0:.0f} s", file=sys.stderr)
    np.savez_compressed(sortie, comptes=comptes, noms=np.array([t.nom for t in tenseurs]),
                        fichier=np.array(fichier))


if __name__ == "__main__":
    main()
