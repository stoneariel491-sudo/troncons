"""Parenté d'expert à expert à une permutation des neurones près, et l'arbre de parenté le plus économe.

Un expert de gpt-oss est une fonction x ↦ W_downᵀ · SwiGLU(W_gate x + b_g, W_up x + b_u) + b_d.
Permuter ses d_ff neurones cachés (rangées de gate et up, colonnes de down, et biais b_g, b_u)
ne change pas la fonction. Deux experts « dupliqués » peuvent donc avoir des neurones dans un
ordre quelconque : la parenté se juge après le meilleur appariement des neurones.

Appariement : pour la paire (A, B), coût du neurone i de A avec le neurone j de B
  c_ij = Σ_rôles cos²(A_r[i], B_r[j])   (rôles gate, up, down ; cos² : le signe d'un α par rangée est
  libre) ; affectation optimale (algorithme hongrois, scipy.optimize.linear_sum_assignment).
Score de la paire (bits par poids que gagne B codé comme mutation de A, source gaussienne, même
distorsion) : s(A, B) = moyenne sur les 3 rôles et les d_ff rangées de −½ log₂(1 − cos²) pour les
neurones appariés. s est symétrique (cos² et l'appariement le sont).
Arbre le plus économe : chaque expert se code seul (racine virtuelle, gain 0) ou comme mutation d'un
parent déjà décodé ; le coût total est minimal pour l'arbre couvrant de poids MAXIMAL sur s
(Kruskal ; tous les s > 0, donc un seul expert codé seul). Gain de la couche = Σ_arêtes s / E.

Témoins :
  hasard  : la paire (A, B′), B′ = B dont les dimensions d'entrée de chaque rôle sont permutées au
            hasard : le score de la parenté fortuite après appariement (le plancher de l'instrument) ;
  planter : (--planter ρ₀) l'expert B est remplacé par un descendant fabriqué de A, neurones permutés,
            corrélation ρ₀ par rangée ; le score doit valoir ≈ −½ log₂(1 − ρ₀²), l'appariement doit
            retrouver la permutation, et l'arbre doit relier A et B.

Utilisation :
  python -I -X utf8 paires_arbre.py --couche 12 [--voisine 13] [--experts 32] [--planter 0.5] > j.json
  (--voisine : paires bipartites couche × voisine au lieu des paires intra-couche)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

import numpy as np
from scipy.optimize import linear_sum_assignment

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import experts as X  # noqa: E402


def gene(ex, couche, role, e):
    w = ex.poids(couche, role, e)
    w = w if role != "down" else np.ascontiguousarray(w.T)
    n = np.linalg.norm(w, axis=1, keepdims=True)
    n[n == 0] = 1
    return (w / n).astype(np.float16)


def charger_couche(ex, couche, n_exp, rng=None, permuter_entree=False):
    """[rôle][expert] → rangées normées (d_ff, d) en float16."""
    out = []
    for role in X.ROLES:
        lst = []
        for e in range(n_exp):
            g = gene(ex, couche, role, e)
            if permuter_entree:
                g = np.ascontiguousarray(g[:, rng.permutation(g.shape[1])])
            lst.append(g)
        out.append(lst)
    return out


def apparier(GA, GB):
    """GA, GB : listes de 3 matrices (d_ff, d) normées. Rend (score, cos par rôle des appariés, perm)."""
    C2 = None
    cos = []
    for a, b in zip(GA, GB):
        c = a.astype(np.float32) @ b.astype(np.float32).T
        cos.append(c)
        C2 = c * c if C2 is None else C2 + c * c
    r, col = linear_sum_assignment(-C2)
    par_role = [np.abs(c[r, col]) for c in cos]
    g = [(-0.5 * np.log2(1 - np.minimum(x.astype(np.float64) ** 2, 1 - 1e-12))).mean() for x in par_role]
    return float(np.mean(g)), [float(x.mean()) for x in par_role], [float(v) for v in g], col


def kruskal_max(n, aretes):
    """aretes : (poids, i, j). Arbre couvrant de poids maximal (union-find)."""
    parent = list(range(n))

    def racine(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    arbre = []
    for w, i, j in sorted(aretes, reverse=True):
        ri, rj = racine(i), racine(j)
        if ri != rj:
            parent[ri] = rj
            arbre.append((i, j, w))
    return arbre


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--couche", type=int, required=True)
    ap.add_argument("--voisine", type=int, default=None)
    ap.add_argument("--experts", type=int, default=32)
    ap.add_argument("--planter", type=float, default=None)
    ap.add_argument("--temoins-hasard", type=int, default=8)
    ap.add_argument("--modele", default="20b")
    ap.add_argument("--graine", type=int, default=20261016)
    a = ap.parse_args()
    ex = X.Experts(X.FICHIER_20B if a.modele == "20b" else X.FICHIER_120B)
    rng = np.random.default_rng(a.graine)
    t0 = time.time()
    n = a.experts
    A = charger_couche(ex, a.couche, n)
    B = charger_couche(ex, a.voisine, n) if a.voisine is not None else A
    perm_plantee = None
    if a.planter is not None:
        # B[1] devient un descendant de A[0] : x′ = ρ₀ P(x) + √(1−ρ₀²) bruit, renormé par rangée.
        perm_plantee = rng.permutation(ex.d_ff)
        nouv = []
        for r in range(3):
            x = A[r][0].astype(np.float32)[perm_plantee]
            bruit = rng.standard_normal(x.shape).astype(np.float32)
            bruit /= np.linalg.norm(bruit, axis=1, keepdims=True)
            y = a.planter * x + math.sqrt(1 - a.planter ** 2) * bruit
            y /= np.linalg.norm(y, axis=1, keepdims=True)
            nouv.append(y.astype(np.float16))
        if B is A:
            B = [list(l) for l in A]
            A = B
        for r in range(3):
            B[r][1] = nouv[r]
    paires = []
    S = np.zeros((n, n))
    if a.voisine is None:
        liste = [(i, j) for i in range(n) for j in range(i + 1, n)]
    else:
        liste = [(i, j) for i in range(n) for j in range(n)]
    for k, (i, j) in enumerate(liste):
        s, cosr, gr, col = apparier([A[r][i] for r in range(3)], [B[r][j] for r in range(3)])
        ligne = {"i": i, "j": j, "score_bits": s, "cos_moyen_par_role": cosr, "gain_par_role": gr}
        if perm_plantee is not None and (i, j) == (0, 1):
            # col[k] = neurone de B apparié au neurone k de A ; attendu : perm_plantee⁻¹.
            inv = np.argsort(perm_plantee)
            ligne["permutation_retrouvee"] = float((col == inv).mean())
        paires.append(ligne)
        S[i, j] = s
        if a.voisine is None:
            S[j, i] = s
        if k % 25 == 0:
            print(f"paire {k}/{len(liste)} ({i},{j}) : {s:.4f} b ; {time.time() - t0:.0f} s", file=sys.stderr, flush=True)
    # Témoin de hasard : paires (i, B′_j) avec entrées permutées.
    hasard = []
    for k in range(a.temoins_hasard):
        i, j = int(rng.integers(n)), int(rng.integers(n))
        Bj = []
        for r in range(3):
            g = B[r][j]
            Bj.append(np.ascontiguousarray(g[:, rng.permutation(g.shape[1])]))
        s, cosr, gr, _ = apparier([A[r][i] for r in range(3)], Bj)
        hasard.append({"i": i, "j": j, "score_bits": s, "cos_moyen_par_role": cosr, "gain_par_role": gr})
    sortie = {"outil": "paires_arbre.py", "arguments": vars(a), "paires": paires, "temoin_hasard": hasard}
    scores = np.array([p["score_bits"] for p in paires])
    sortie["scores"] = {"moyen": float(scores.mean()), "max": float(scores.max()), "min": float(scores.min()),
                        "hasard_moyen": float(np.mean([h["score_bits"] for h in hasard]))}
    if a.voisine is None:
        arbre = kruskal_max(n, [(S[i, j], i, j) for i in range(n) for j in range(i + 1, n)])
        sortie["arbre"] = [{"i": i, "j": j, "score_bits": w} for i, j, w in arbre]
        sortie["gain_couche_bits_par_poids"] = float(sum(w for _, _, w in arbre) / n)
        if perm_plantee is not None:
            sortie["temoin_planter"] = {"rho0": a.planter, "gain_attendu": -0.5 * math.log2(1 - a.planter ** 2),
                                        "score_0_1": float(S[0, 1]),
                                        "arete_0_1_dans_arbre": any({i, j} == {0, 1} for i, j, _ in arbre)}
    else:
        # Meilleur parent dans la voisine pour chaque expert de la couche : borne d'un arbre inter-couches.
        sortie["meilleur_parent_voisine"] = [float(S[i].max()) for i in range(n)]
        sortie["gain_meilleur_parent_moyen"] = float(np.mean(sortie["meilleur_parent_voisine"]))
        sortie["gain_meme_indice_apparie_moyen"] = float(np.mean([S[i, i] for i in range(n)]))
    sortie["duree_s"] = time.time() - t0
    print(json.dumps(sortie, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
