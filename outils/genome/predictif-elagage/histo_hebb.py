"""Sensibilité hebbienne de chaque poids d'un expert : activité présynaptique × influence postsynaptique.

Constat qui la motive (sortie_experts.py, 2026-10-16) : un plan qui respecte l'erreur relative de
chaque matrice (gate, up, down à 1 à 4 %) peut rendre la sortie de l'expert fausse à 22 à 68 %
(ecsq_e, élagage lagrangien). La raison : le remplissage inverse d'une matrice vide ses lignes de
petite échelle ; or une ligne i de gate ou de up n'agit sur la sortie qu'à travers la colonne i de
down, et l'entraînement répartit librement l'échelle entre les deux (symétrie de réétalonnage du
SwiGLU sur le chemin up). Une ligne petite dans gate peut être lourde en sortie.

Développement au premier ordre de la sortie y = Wd a(g, u) + bd de l'expert :
  ∂y/∂Wg_ij = Wd[:, i] · ∂a_i/∂g_i · x_j,   ∂y/∂Wu_ij = Wd[:, i] · ∂a_i/∂u_i · x_j,   ∂y/∂Wd_ij = e_i a_j,
d'où, en factorisant l'espérance (approximation de Kronecker, celle de K-FAC),
  E‖Δy‖² ≈ Σ_ij ΔW_ij² · r_i · s_j,
  r_i = ‖Wd[:, i]‖² · E[(∂a_i/∂g_i)²] (gate), ‖Wd[:, i]‖² · E[(∂a_i/∂u_i)²] (up), 1 (down),
  s_j = E[x_j²] (gate, up), E[a_j²] (down).
Avec swiglu_oai : g' = min(g, 7), u' = clamp(u, −7, 7), σ = sigmoïde(1,702 g'),
  ∂a/∂g = [g < 7] · (σ + 1,702 g' σ (1 − σ)) · (u' + 1),   ∂a/∂u = [|u| < 7] · g' σ.
Le poids d'une synapse est le produit de l'activité de son entrée et de l'influence de sa sortie :
le produit de Hebb.

Comptes : N et S = Σ r_i s_j par (tenseur, e, classe de ligne qr, classe de colonne qc, code), qr
et qc les quartiles de r_i et s_j dans la matrice d'expert (cartes de 2 bits par ligne et par
colonne). Calibration : fenêtres 0 à 4.

Option --cle-delta : la clé d'échelle devient δ = e − médiane de la ligne, borné à ±3 (7 classes,
indice δ + 3), et S reçoit directement la masse 4^(e − 127) · r_i · s_j (le centre optimal reste
pondéré par l'échelle absolue). Ce sont les contextes relatifs à la ligne, ceux du plan qui a tenu à
la sortie (ecsq_kappa).

Utilisation : python -I -X utf8 histo_hebb.py DOSSIER_ENTREES SORTIE.npz [--cle-delta]
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mxfp4 as mx  # noqa: E402
from sortie_experts import FENETRE, biais, lire_entrees  # noqa: E402

CALIB = range(0, 5)
NQ = 4
ALPHA = 1.702


def quartiles(v):
    q = np.searchsorted(np.quantile(v, [0.25, 0.5, 0.75]), v, side="right")
    return np.minimum(q, NQ - 1).astype(np.int64)


def main():
    dossier, sortie = sys.argv[1], sys.argv[2]
    cle_delta = "--cle-delta" in sys.argv
    lec = mx.lecteur()
    par_nom = {t.nom: t for t in lec.tenseurs}
    tenseurs = mx.tenseurs_etude(lec)
    T = len(tenseurs)
    E_, R_, C_ = mx.forme(tenseurs[0])
    N = np.zeros((T, 256, NQ, NQ, 16), dtype=np.uint32)
    S = np.zeros((T, 256, NQ, NQ, 16), dtype=np.float64)
    cartes_col = np.full((T, E_, C_), NQ - 1, dtype=np.uint8)
    cartes_lig = np.full((T, E_, R_), NQ - 1, dtype=np.uint8)
    t0 = time.time()
    for ic, couche in enumerate(mx.COUCHES):
        _, d, entrees = lire_entrees(os.path.join(dossier, f"entrees-{couche}.bin"))
        noms = [f"blk.{couche}.{r}.weight" for r in mx.ROLES]
        bs = [biais(lec, f"blk.{couche}.{r}.bias") for r in mx.ROLES]
        for e in range(E_):
            mats = [mx.expert(lec, par_nom[n], e) for n in noms]
            W = [mx.valeurs(c, s) for c, s in mats]
            rs = [np.ones(R_)] * 3
            ss = [np.ones(C_)] * 3
            if e in entrees:
                pos, X = entrees[e]
                garde = np.isin(pos // FENETRE, list(CALIB))
                if garde.any():
                    X = X[garde].astype(np.float64)
                    G = X @ W[0].T + bs[0][e]
                    U = X @ W[1].T + bs[1][e]
                    gp = np.minimum(G, 7.0)
                    up = np.clip(U, -7.0, 7.0)
                    sg = 1.0 / (1.0 + np.exp(-ALPHA * gp))
                    A = gp * sg * (up + 1.0)
                    dadg = (G < 7.0) * (sg + ALPHA * gp * sg * (1.0 - sg)) * (up + 1.0)
                    dadu = (np.abs(U) < 7.0) * gp * sg
                    cd = (W[2] ** 2).sum(axis=0)              # ‖Wd[:, i]‖²
                    rs = [cd * (dadg ** 2).mean(axis=0), cd * (dadu ** 2).mean(axis=0), np.ones(R_)]
                    sx = (X ** 2).mean(axis=0)
                    ss = [sx, sx, (A ** 2).mean(axis=0)]
            for r, (codes, ech) in enumerate(mats):
                t = ic * 3 + r
                ql = quartiles(rs[r])
                qc = quartiles(ss[r])
                cartes_lig[t, e] = ql
                cartes_col[t, e] = qc
                ee = np.repeat(ech.astype(np.int64), 32, axis=1)
                masse = 1.0
                if cle_delta:
                    med = mx.mediane_ligne(ech).astype(np.int64)
                    dl = np.clip(ech.astype(np.int64) - med[:, None], -3, 3) + 3
                    masse = np.repeat(4.0 ** (ech.astype(np.float64) - 127.0), 32, axis=1)
                    ee = np.repeat(dl, 32, axis=1)
                cle = ((ee * NQ + ql[:, None]) * NQ + qc[None, :]) * 16 + codes
                N[t] += np.bincount(cle.ravel(), minlength=256 * NQ * NQ * 16).reshape(256, NQ, NQ, 16).astype(np.uint32)
                poids = rs[r][:, None] * ss[r][None, :] * masse
                S[t] += np.bincount(cle.ravel(), weights=poids.ravel(),
                                    minlength=256 * NQ * NQ * 16).reshape(256, NQ, NQ, 16)
        print(f"couche {couche} : {time.time() - t0:.0f} s", file=sys.stderr)
    np.savez_compressed(sortie, N=N, S=S, cartes_col=cartes_col, cartes_lig=cartes_lig,
                        noms=np.array([t.nom for t in tenseurs]))


if __name__ == "__main__":
    main()
