"""La famille de gènes : les 32 experts d'une couche partagent-ils un sous-espace (un « domaine » commun) ?

La duplication stricte (un parent par expert) est la forme la plus étroite de la parenté. Sa forme
large, celle des familles de gènes, est un domaine partagé : tous les gènes d'une famille vivent
près d'un même sous-espace, sans qu'aucun ne soit la copie d'un autre. Pour les rangées d'un rôle
(gate, up : vecteurs de l'espace d'entrée d_modele ; down : colonnes, vecteurs de l'espace de sortie
d_modele), on accumule la matrice de covariance commune
  Σ = (1/N) Σ_experts Σ_rangées x xᵀ,  N = E · d_ff,
puis ses valeurs propres λ (la base de Karhunen-Loève commune à la famille).

Débit de Shannon d'une source gaussienne de covariance Σ, à distorsion D par composante
(remplissage inverse) : R(D) = (1/n) Σ_i max(0, ½ log₂(λ_i / θ)), avec Σ_i min(λ_i, θ) = n·D.
On compare, à la MÊME erreur quadratique relative ε = D / (tr Σ / n) :
  iso  : toutes les composantes de variance égale (aucune structure) : R = ½ log₂(1/ε) ;
  diag : les variances par coordonnée σ_ii seules (une échelle par colonne, aucune rotation) ;
  klt  : le spectre λ (rotation commune à la famille).
Le gain de la famille est R_diag − R_klt ; il se paie par le stockage de la base (n² nombres par
couche et par rôle, ou k·n pour un sous-espace de rang k), compté à part.
Témoin : une famille dont les coordonnées de chaque expert sont permutées au hasard (chaque expert
garde ses statistiques propres, le domaine commun est détruit) ; son R_klt − R_diag mesure le biais
d'estimation du spectre (N = 92 160 échantillons pour n = 2 880 dimensions, Marchenko-Pastur).
La covariance d'un expert seul (2 880 échantillons pour 2 880 dimensions) n'est pas estimable : non
calculée.

Utilisation : python -I -X utf8 spectre_famille.py --couches 0,12,23 [--eps 0.0429] > j.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import experts as X  # noqa: E402


def debit_remplissage(lam: np.ndarray, eps: float) -> float:
    """R(D) en bits par composante pour le spectre lam, à erreur relative eps (dichotomie sur θ)."""
    lam = np.maximum(lam.astype(np.float64), 1e-30)
    n = lam.size
    D = eps * lam.mean()
    lo, hi = 0.0, lam.max()
    for _ in range(200):
        th = 0.5 * (lo + hi)
        if np.minimum(lam, th).sum() / n > D:
            hi = th
        else:
            lo = th
    th = 0.5 * (lo + hi)
    return float(np.maximum(0.0, 0.5 * np.log2(lam / th)).sum() / n)


def debits(S: np.ndarray, eps: float) -> dict:
    lam = np.linalg.eigvalsh(S)[::-1]
    diag = np.diag(S)
    r_iso = 0.5 * np.log2(1 / eps)
    r_diag = debit_remplissage(diag, eps)
    r_klt = debit_remplissage(lam, eps)
    c = np.cumsum(lam) / lam.sum()
    return {"R_iso": r_iso, "R_diag": r_diag, "R_klt": r_klt, "gain_klt_sur_diag": r_diag - r_klt,
            "gain_diag_sur_iso": r_iso - r_diag,
            "rang_90pc_energie": int(np.searchsorted(c, 0.90) + 1),
            "rang_99pc_energie": int(np.searchsorted(c, 0.99) + 1),
            "lambda_max_sur_moyenne": float(lam[0] / lam.mean())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--couches", default="0,12,23")
    ap.add_argument("--eps", type=float, default=0.0429)
    ap.add_argument("--modele", default="20b")
    ap.add_argument("--graine", type=int, default=20261016)
    a = ap.parse_args()
    ex = X.Experts(X.FICHIER_20B if a.modele == "20b" else X.FICHIER_120B)
    rng = np.random.default_rng(a.graine)
    sortie = {"outil": "spectre_famille.py", "arguments": vars(a), "resultats": []}
    t0 = time.time()
    for L in [int(c) for c in a.couches.split(",")]:
        for role in X.ROLES:
            n = ex.d_ff
            S = np.zeros((n, n), dtype=np.float64)
            St = np.zeros((n, n), dtype=np.float64)
            N = 0
            for e in range(ex.nb_experts):
                w = ex.poids(L, role, e)
                w = w if role != "down" else np.ascontiguousarray(w.T)   # rangées = gènes
                G = (w.T @ w).astype(np.float64)
                S += G
                p = rng.permutation(w.shape[1])
                wp = w[:, p]
                St += (wp.T @ wp).astype(np.float64)
                N += w.shape[0]
            S /= N
            St /= N
            ligne = {"couche": L, "role": role, "famille": debits(S, a.eps),
                     "temoin_famille_permutee": debits(St, a.eps)}
            sortie["resultats"].append(ligne)
            f = ligne["famille"]
            print(f"couche {L} {role} : R iso {f['R_iso']:.3f} diag {f['R_diag']:.3f} klt {f['R_klt']:.3f} ; "
                  f"témoin diag {ligne['temoin_famille_permutee']['R_diag']:.3f} klt {ligne['temoin_famille_permutee']['R_klt']:.3f} ; "
                  f"{time.time() - t0:.0f} s", file=sys.stderr, flush=True)
    sortie["duree_s"] = time.time() - t0
    print(json.dumps(sortie, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
