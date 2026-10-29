"""Loi de puissance par la méthode de Clauset, Shalizi et Newman (arXiv 0706.1062), écrite de zéro.

Loi continue p(x) = (α − 1)/x_min · (x / x_min)^(−α), x ≥ x_min.
1. x_min par minimum de la distance de Kolmogorov-Smirnov (queue d'au moins `n_min` points) ;
   α par maximum de vraisemblance : α̂ = 1 + n / Σ ln(xᵢ / x_min).
2. Concurrentes sur la même queue, tronquées en x_min : exponentielle (forme close), log-normale
   (maximum de vraisemblance numérique, deux départs).
3. Rapport de vraisemblance de Vuong normalisé : R = Σ ℓᵢ, p = erfc(|R| / (σ̂ √(2n))).
4. Plausibilité : p_gof par répliques semi-paramétriques (CSN § 4.1).
Le verdict est celui de seuil.md § 4.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import optimize, special

N_MIN = 50


def balayer_xmin(x: np.ndarray, n_min: int = N_MIN):
    """x trié croissant. Rend (i*, x_min, α, D) au minimum de KS sur les candidats admissibles."""
    n_tot = x.size
    lx = np.log(x)
    # sommes de queue de ln x : S[i] = Σ_{j ≥ i} ln x_j
    S = np.concatenate([np.cumsum(lx[::-1])[::-1], [0.0]])
    meilleur = (None, None, None, math.inf)
    dernier = n_tot - n_min
    i = 0
    while i <= dernier:
        xm = x[i]
        n = n_tot - i
        somme = S[i] - n * lx[i]
        if somme > 0:
            a = 1.0 + n / somme
            q = x[i:] / xm
            F = 1.0 - q ** (1.0 - a)
            j = np.arange(n)
            D = max(float(np.max((j + 1) / n - F)), float(np.max(F - j / n)))
            if D < meilleur[3]:
                meilleur = (i, float(xm), float(a), D)
        # candidats = valeurs distinctes : sauter les égales
        k = i + 1
        while k <= dernier and x[k] == xm:
            k += 1
        i = k
    return meilleur


def logp_pl(q: np.ndarray, a: float, xm: float) -> np.ndarray:
    return math.log(a - 1.0) - math.log(xm) - a * np.log(q)


def ajuster_exp(t: np.ndarray, xm: float):
    lam = 1.0 / (t.mean() - xm)
    return np.log(lam) - lam * (t - xm), {"lambda": float(lam)}


def _nll_lognormale(par, y, ly_xm):
    """y = ln x de la queue, ly_xm = ln x_min ; par = (μ, ln σ)."""
    mu, ls = par
    s = math.exp(ls)
    z0 = (ly_xm - mu) / s
    lsurv = special.log_ndtr(-z0)
    lp = -y - ls - 0.5 * math.log(2 * math.pi) - (y - mu) ** 2 / (2 * s * s) - lsurv
    return -float(lp.sum())


def ajuster_lognormale(t: np.ndarray, xm: float):
    y = np.log(t)
    lxm = math.log(xm)
    departs = [(float(y.mean()), math.log(max(float(y.std()), 1e-3))),
               (lxm - 10.0, math.log(3.0)), (lxm, math.log(max(float(y.std()), 1e-3)) + 1.0)]
    bornes = [(lxm - 200.0, lxm + 50.0), (-6.0, 5.0)]
    meilleur = None
    for d in departs:
        r = optimize.minimize(_nll_lognormale, d, args=(y, lxm), method="L-BFGS-B", bounds=bornes)
        if meilleur is None or r.fun < meilleur.fun:
            meilleur = r
    mu, ls = meilleur.x
    s = math.exp(ls)
    lp = -y - ls - 0.5 * math.log(2 * math.pi) - (y - mu) ** 2 / (2 * s * s) - special.log_ndtr(-(lxm - mu) / s)
    return lp, {"mu": float(mu), "sigma": float(s)}


def vuong(l: np.ndarray):
    n = l.size
    R = float(l.sum())
    sd = float(l.std())
    if sd == 0:
        return R, 1.0
    return R, float(special.erfc(abs(R) / (sd * math.sqrt(2 * n))))


def verdict_principal(R_exp, p_exp, R_ln, p_ln) -> str:
    if R_exp > 0 and p_exp < 0.05 and R_ln > 0 and p_ln < 0.05:
        return "loi de puissance"
    if (R_exp < 0 and p_exp < 0.05) or (R_ln < 0 and p_ln < 0.05):
        return "autre loi préférée"
    return "non départagée"


def p_gof(x: np.ndarray, i: int, xm: float, a: float, D: float, rng, repliques: int = 100) -> float:
    """CSN § 4.1 : répliques semi-paramétriques, x_min et α ré-estimés ; part des D_rep ≥ D."""
    n_tot = x.size
    corps = x[:i]
    p_queue = (n_tot - i) / n_tot
    plus = 0
    for _ in range(repliques):
        nq = rng.binomial(n_tot, p_queue)
        queue = xm * rng.random(nq) ** (-1.0 / (a - 1.0))
        bas = rng.choice(corps, n_tot - nq, replace=True) if i > 0 and nq < n_tot else np.empty(0)
        xr = np.sort(np.concatenate([bas, queue]))
        r = balayer_xmin(xr)
        if r[0] is not None and r[3] >= D:
            plus += 1
    return plus / repliques


def ajuster(valeurs: np.ndarray, rng=None, repliques: int = 0) -> dict:
    """Ajustement complet sur des valeurs > 0 (ici les valeurs propres λ = σ²)."""
    x = np.sort(np.asarray(valeurs, dtype=np.float64))
    x = x[x > 0]
    i, xm, a, D = balayer_xmin(x)
    t = x[i:]
    q = t / xm
    lpl = logp_pl(q, a, xm)
    lex, pex = ajuster_exp(t, xm)
    lln, pln = ajuster_lognormale(t, xm)
    R_exp, p_exp = vuong(lpl - lex)
    R_ln, p_ln = vuong(lpl - lln)
    n = t.size
    sortie = {
        "n": int(x.size), "n_queue": int(n), "x_min": xm, "alpha": a,
        "alpha_err": (a - 1.0) / math.sqrt(n), "ks": D,
        "R_exp": R_exp, "p_exp": p_exp, "R_lognormale": R_ln, "p_lognormale": p_ln,
        "exp": pex, "lognormale": pln,
        "verdict": verdict_principal(R_exp, p_exp, R_ln, p_ln),
    }
    if repliques and rng is not None:
        sortie["p_gof"] = p_gof(x, i, xm, a, D, rng, repliques)
        sortie["verdict_strict"] = (sortie["verdict"] == "loi de puissance" and sortie["p_gof"] >= 0.1)
    return sortie
