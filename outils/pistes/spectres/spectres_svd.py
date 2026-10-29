"""Piste spectres, pas 2 : les valeurs singulières complètes de l'échantillon et de ses témoins.

Écrit `mesures/pistes/spectres/valeurs-singulieres.npz` (compressé) et `manifeste.json` :
- `reel/<id>` : les min(m, n) valeurs singulières de la matrice réelle (f64, décroissantes) ;
- `perm/<id>` : celles de la même matrice, entrées permutées (T-perm) ;
- `mp/<m>x<n>` : celles d'une gaussienne i.i.d. aux mêmes dimensions (T-MP) ;
- `pareto` : T-Pareto (α = 2,5 planté sur les valeurs propres, passé par une vraie matrice).
Le manifeste porte, par matrice, la forme, la norme de Frobenius, le kurtosis des entrées et
l'empreinte SHA-256 des octets f64 de la matrice (pour le second chemin).

Utilisation : python -X utf8 spectres_svd.py
"""
from __future__ import annotations

import commun  # pose les fils avant numpy

import hashlib
import json
import os
import sys
import time

import numpy as np


def kurtosis(w: np.ndarray) -> float:
    x = w - w.mean()
    return float((x ** 4).mean() / (x ** 2).mean() ** 2)


def orthogonale(rng, n: int) -> np.ndarray:
    q, r = np.linalg.qr(rng.standard_normal((n, n)))
    return q * np.sign(np.diag(r))


def main() -> None:
    commun.priorite_basse()
    os.makedirs(commun.MESURES, exist_ok=True)
    lec = commun.lecteur()
    index = {t.nom: t for t in lec.tenseurs}
    rng = np.random.default_rng(commun.GRAINE)
    tableaux: dict[str, np.ndarray] = {}
    manifeste = {"graine": commun.GRAINE, "experts": commun.tirer_experts(), "matrices": []}
    formes = set()
    t_debut = time.time()
    for m in commun.echantillon():
        commun.attendre_calme()
        w = commun.matrice(lec, index, m)
        formes.add(w.shape)
        s = np.linalg.svd(w, compute_uv=False)
        wp = rng.permutation(w.ravel()).reshape(w.shape)
        sp = np.linalg.svd(wp, compute_uv=False)
        tableaux[f"reel/{m['id']}"] = s
        tableaux[f"perm/{m['id']}"] = sp
        ligne = dict(m, forme=list(w.shape), frobenius=float(np.sqrt((w ** 2).sum())),
                     kurtosis=kurtosis(w),
                     sha256_f64=hashlib.sha256(np.ascontiguousarray(w).tobytes()).hexdigest(),
                     sigma_max=float(s[0]), sigma_max_perm=float(sp[0]))
        manifeste["matrices"].append(ligne)
        print(f"{m['id']:18s} {w.shape} σ1 {s[0]:.4f} (perm {sp[0]:.4f}) "
              f"kurt {ligne['kurtosis']:.1f}  {time.time() - t_debut:.0f} s", file=sys.stderr, flush=True)
        del w, wp
    # T-MP : gaussiennes i.i.d. aux mêmes formes (variance 1 ; l'exposant ne dépend pas de l'échelle)
    for forme in sorted(formes):
        commun.attendre_calme()
        g = rng.standard_normal(forme)
        tableaux[f"mp/{forme[0]}x{forme[1]}"] = np.linalg.svd(g, compute_uv=False)
        print(f"T-MP {forme}", file=sys.stderr, flush=True)
        del g
    # T-Pareto : λ ~ Pareto(α = 2,5, λ ≥ 1), densité ∝ λ^(−α) ; inversion : λ = u^(−1/(α−1))
    n = 2880
    lam = rng.random(n) ** (-1.0 / 1.5)
    u, v = orthogonale(rng, n), orthogonale(rng, n)
    w = (u * np.sqrt(lam)) @ v.T
    tableaux["pareto"] = np.linalg.svd(w, compute_uv=False)
    tableaux["pareto_plante"] = np.sort(np.sqrt(lam))[::-1]
    del u, v, w
    np.savez_compressed(os.path.join(commun.MESURES, "valeurs-singulieres.npz"), **tableaux)
    manifeste["duree_s"] = round(time.time() - t_debut, 1)
    with open(os.path.join(commun.MESURES, "manifeste.json"), "w", encoding="utf8") as f:
        json.dump(manifeste, f, indent=1, ensure_ascii=False)
    print(f"fini en {manifeste['duree_s']} s", file=sys.stderr)


if __name__ == "__main__":
    main()
