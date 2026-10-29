"""Données de la figure « l'arbre phylogénétique des experts » (SOCLE : espaces latents, 2026-10-17).

Lit `mesures/genome/duplication/arbre-c23.json` (les 496 paires appariées de la couche 23 et l'arbre
couvrant de poids maximal) et écrit, pour pgfplots/TikZ :
  csv/phylogenie-c23-noeuds.csv : expert, x, y (plongement de distances par MDS classique), degré dans
                                  l'arbre, score de sa meilleure arête ;
  csv/phylogenie-c23-aretes.csv : i, j, score, xi, yi, xj, yj (les 31 arêtes de l'arbre) ;
  et sur la sortie standard : la part de la variance que le plan garde (la fidélité de l'image).
Distance entre deux experts : d_ij = log₂(s_max / s_ij), s le score d'appariement (bit par poids) : nulle
pour la paire la plus parente, et grande pour une paire au niveau du hasard (0,0016 bit).
MDS classique (Torgerson 1952) : B = −½ J D² J, coordonnées = vecteurs propres de B × √valeurs propres.
Témoin : la distance euclidienne du plan doit être corrélée à d (Spearman rapporté) ; un plongement de
distances permutées au hasard doit donner une corrélation proche de 0 avec les vraies distances.
"""
from __future__ import annotations

import csv
import json
import os

import numpy as np
from scipy.stats import spearmanr

ICI = os.path.dirname(os.path.abspath(__file__))
J = os.path.normpath(os.path.join(ICI, "..", "..", "..", "mesures", "genome", "duplication"))


def mds(D, k=2):
    n = D.shape[0]
    Jc = np.eye(n) - np.ones((n, n)) / n
    B = -0.5 * Jc @ (D ** 2) @ Jc
    w, V = np.linalg.eigh(B)
    o = np.argsort(w)[::-1]
    w, V = w[o], V[:, o]
    X = V[:, :k] * np.sqrt(np.maximum(w[:k], 0))
    part = float(np.maximum(w[:k], 0).sum() / np.maximum(w, 0).sum())
    return X, part


def main():
    d = json.load(open(os.path.join(J, "arbre-c23.json"), encoding="utf-8"))
    n = 32
    S = np.zeros((n, n))
    for p in d["paires"]:
        S[p["i"], p["j"]] = S[p["j"], p["i"]] = p["score_bits"]
    smax = S.max()
    D = np.zeros((n, n))
    iu = np.triu_indices(n, 1)
    D[iu] = np.log2(smax / S[iu])
    D = D + D.T
    X, part = mds(D)
    E = np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(-1))
    rho = spearmanr(D[iu], E[iu]).statistic
    rng = np.random.default_rng(20261017)
    v = D[iu].copy()
    rng.shuffle(v)
    Dp = np.zeros((n, n))
    Dp[iu] = v
    Dp = Dp + Dp.T
    Xp, _ = mds(Dp)
    Ep = np.sqrt(((Xp[:, None, :] - Xp[None, :, :]) ** 2).sum(-1))
    rho_temoin = spearmanr(D[iu], Ep[iu]).statistic
    arbre = d["arbre"]
    deg = np.zeros(n, dtype=int)
    best = np.zeros(n)
    for a in arbre:
        for k in (a["i"], a["j"]):
            deg[k] += 1
            best[k] = max(best[k], a["score_bits"])
    os.makedirs(os.path.join(J, "csv"), exist_ok=True)
    with open(os.path.join(J, "csv", "phylogenie-c23-noeuds.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["expert", "x", "y", "degre", "meilleure_arete"])
        for e in range(n):
            w.writerow([e, f"{X[e, 0]:.5f}", f"{X[e, 1]:.5f}", deg[e], f"{best[e]:.5f}"])
    with open(os.path.join(J, "csv", "phylogenie-c23-aretes.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["i", "j", "score", "xi", "yi", "xj", "yj"])
        for a in arbre:
            i, j = a["i"], a["j"]
            w.writerow([i, j, f"{a['score_bits']:.5f}", f"{X[i, 0]:.5f}", f"{X[i, 1]:.5f}", f"{X[j, 0]:.5f}", f"{X[j, 1]:.5f}"])
    print(json.dumps({"outil": "figure_phylogenie.py", "part_variance_plan": part,
                      "spearman_plan_distances": rho, "temoin_distances_permutees": rho_temoin,
                      "s_max": smax}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
