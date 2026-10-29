"""Loi conjointe pondérée par la sensibilité mesurée : l'élagage synaptique dépendant de l'activité.

Dans le cerveau en développement, une synapse peu utilisée est retirée (« use it or lose it ») :
l'élagage dépend de l'activité, pas seulement de la force de la synapse. Pour une matrice W et des
entrées x de covariance Σ, l'erreur de sortie d'une perturbation ΔW vaut
    E‖ΔW x‖² = tr(ΔW Σ ΔWᵀ) ≈ Σ_ij ΔW_ij² Σ_jj
(approximation diagonale ; exacte si les erreurs de colonnes différentes sont décorrélées, ce que
la quantification indépendante de chaque poids rend vrai en moyenne). La sensibilité d'un poids
est donc s_j = E[x_j²], l'activité de sa colonne d'entrée, mesurée sur les entrées réelles.

Ce que l'outil compte, par (tenseur, e, classe de colonne q, code) : le nombre de poids N et la
somme S des s_j, où q est le quartile de s_j dans l'expert (carte de 2 bits par colonne et par
expert : 2 880 × 2 bits = 720 octets par matrice d'expert, 0,0007 bit par poids, envoyée avec
l'expert). Les s_j viennent des fenêtres de calibration 0 à 4 ; l'évaluation (sortie_experts.py)
se fait sur les fenêtres 5 à 9.
Entrées de gate et up : X capturé ; entrée de down : A = swiglu(X Wgᵀ + bg, X Wuᵀ + bu), poids
exacts.

Sortie : un .npz : N (tenseurs, 256, 4, 16) uint32, S (idem) float64, et les cartes de classes
(tenseurs, experts, colonnes) uint8. Un expert sans jeton de calibration reçoit s_j = 1 partout
(classe 3), ce qui le traite comme la métrique des poids.

Utilisation : python -I -X utf8 histo_sensibilite.py DOSSIER_ENTREES SORTIE.npz
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mxfp4 as mx  # noqa: E402
from sortie_experts import FENETRE, biais, lire_entrees, swiglu  # noqa: E402

CALIB = range(0, 5)
NQ = 4


def main():
    dossier, sortie = sys.argv[1], sys.argv[2]
    lec = mx.lecteur()
    par_nom = {t.nom: t for t in lec.tenseurs}
    tenseurs = mx.tenseurs_etude(lec)
    T = len(tenseurs)
    N = np.zeros((T, 256, NQ, 16), dtype=np.uint32)
    S = np.zeros((T, 256, NQ, 16), dtype=np.float64)
    E_, R_, C_ = mx.forme(tenseurs[0])
    cartes = np.full((T, E_, C_), NQ - 1, dtype=np.uint8)
    sens = np.ones((T, E_, C_), dtype=np.float32)
    t0 = time.time()
    for ic, couche in enumerate(mx.COUCHES):
        _, d, entrees = lire_entrees(os.path.join(dossier, f"entrees-{couche}.bin"))
        noms = [f"blk.{couche}.{r}.weight" for r in mx.ROLES]
        bs = [biais(lec, f"blk.{couche}.{r}.bias") for r in mx.ROLES]
        for e in range(E_):
            mats = [mx.expert(lec, par_nom[n], e) for n in noms]
            s_in = np.ones(C_)
            s_down = np.ones(C_)
            if e in entrees:
                pos, X = entrees[e]
                garde = np.isin(pos // FENETRE, list(CALIB))
                if garde.any():
                    X = X[garde].astype(np.float64)
                    Wg = mx.valeurs(*mats[0])
                    Wu = mx.valeurs(*mats[1])
                    A = swiglu(X @ Wg.T + bs[0][e], X @ Wu.T + bs[1][e])
                    s_in = (X ** 2).mean(axis=0)
                    s_down = (A ** 2).mean(axis=0)
            for r, (codes, ech) in enumerate(mats):
                t = ic * 3 + r
                s = s_down if r == 2 else s_in
                q = np.searchsorted(np.quantile(s, [0.25, 0.5, 0.75]), s, side="right").astype(np.int64)
                q = np.minimum(q, NQ - 1)
                cartes[t, e] = q
                sens[t, e] = s
                ee = np.repeat(ech.astype(np.int64), 32, axis=1)
                cle = (ee * NQ + q[None, :]) * 16 + codes
                N[t] += np.bincount(cle.ravel(), minlength=256 * NQ * 16).reshape(256, NQ, 16).astype(np.uint32)
                S[t] += np.bincount(cle.ravel(), weights=np.broadcast_to(s[None, :], codes.shape).ravel(),
                                    minlength=256 * NQ * 16).reshape(256, NQ, 16)
        print(f"couche {couche} : {time.time() - t0:.0f} s", file=sys.stderr)
    np.savez_compressed(sortie, N=N, S=S, cartes=cartes, sens=sens, noms=np.array([t.nom for t in tenseurs]))


if __name__ == "__main__":
    main()
