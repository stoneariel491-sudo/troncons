"""Ce que la recette graine + coefficients peut atteindre au mieux, calculé (sans quantifier les
coefficients) : la meilleure de N = 2^K projections sur un sous-espace aléatoire de dimension P d'un
bloc de C poids.

Pour une direction uniforme sur la sphère de R^C et un sous-espace aléatoire de dimension P, la part
de l'énergie hors du sous-espace suit ρ ~ Bêta((C − P)/2, P/2). Le minimum de N tirages
indépendants a pour espérance E[min] = ∫₀¹ (1 − F(ε))^N dε, F la fonction de répartition de la loi
Bêta (calcul exact par quadrature, scipy). Asymptote : F(ε) ≈ ε^a / (a B(a, b)), a = (C − P)/2, d'où
E[min] ≈ Γ(1 + 1/a) (a B(a, b) / N)^(1/a).

Le cas P = 1 avec un gain est la quantification « forme-gain » par un livre de codes aléatoire.

Utilisation : python -I -X utf8 graine_theorie.py > graine-theorie.json
"""
import json

import numpy as np
from scipy import integrate, special, stats

CONFIGS = [(8, 3, 16), (12, 4, 16), (12, 3, 16), (14, 4, 16), (16, 5, 16), (16, 4, 16), (12, 2, 16), (8, 1, 16), (8, 2, 16), (10, 3, 16)]


def esperance_min(c, p, k):
    a, b = (c - p) / 2, p / 2
    n = 2.0 ** k
    f = lambda e: np.exp(n * np.log1p(-stats.beta.cdf(e, a, b))) if e < 1 else 0.0
    # l'intégrande vaut ≈ 1 jusque vers ε*, puis tombe : on intègre par morceaux autour de ε*
    asym = special.gamma(1 + 1 / a) * (a * special.beta(a, b) / n) ** (1 / a)
    pts = sorted({min(0.999, asym * x) for x in (0.1, 0.5, 1, 2, 5, 10)})
    v, _ = integrate.quad(f, 0, 1, points=pts, limit=400)
    return v, asym


sortie = []
for c, p, k in CONFIGS:
    v, asym = esperance_min(c, p, k)
    sortie.append({"c": c, "p": p, "k": k, "debit": (k + 4 + 4 * p) / c, "residu_attendu": v, "asymptote": asym,
                   "shannon_au_meme_debit": 2.0 ** (-2 * (k + 4 + 4 * p) / c)})
print(json.dumps(sortie, indent=1))
