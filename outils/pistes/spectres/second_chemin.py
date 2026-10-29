"""Piste spectres : le second chemin du chiffre principal (seuil.md § 6).

Indépendant de `commun.matrice_*`, de `np.linalg.svd` et de `csn.py` :
1. déquantification par la spécification : lecture du fichier par `seek`/`read` (pas de carte
   mémoire), MXFP4 décodé bit à bit (E2M1 : signe, 2 bits d'exposant, 1 bit de mantisse ; échelle
   E8M0 = 2^(e − 127)), Q8_0 par un dtype structuré ; empreinte SHA-256 comparée au manifeste ;
2. valeurs propres par `eigvalsh` de la plus petite des deux matrices de Gram ;
3. ajustement refait autrement : balayage de x_min entièrement vectorisé par morceaux, α par
   maximisation numérique de la vraisemblance, D vérifiée par `scipy.stats.kstest`, concurrentes par
   `scipy.stats` (`expon`, `lognorm`, tronquées par logpdf − logsf, ajustées par Nelder-Mead),
   p_gof avec une autre graine.

Utilisation : python -X utf8 second_chemin.py > second-chemin.csv
"""
from __future__ import annotations

import commun

import csv
import hashlib
import json
import math
import os
import struct
import sys

import numpy as np
from scipy import optimize, special, stats


# --- 1. déquantification par la spécification ------------------------------------------------
def e2m1(code: np.ndarray) -> np.ndarray:
    s = (code >> 3) & 1
    e = (code >> 1) & 3
    m = code & 1
    mag = np.where(e == 0, 0.5 * m, np.ldexp(1.0 + 0.5 * m, e.astype(np.int64) - 1))
    return np.where(s == 1, -mag, mag)


def lire(f, decalage: int, n: int) -> bytes:
    f.seek(decalage)
    return f.read(n)


def matrice_spec(f, t, e: int) -> np.ndarray:
    if t.nom_type == "MXFP4":
        colonnes, lignes, ne = t.dims
        par_expert = t.nb_octets // ne
        brut = np.frombuffer(lire(f, t.decalage + e * par_expert, par_expert),
                             dtype=np.dtype([("e", "u1"), ("qs", "u1", 16)]))
        bas = brut["qs"] & 0x0F
        haut = brut["qs"] >> 4
        valeurs = np.concatenate([e2m1(bas), e2m1(haut)], axis=1)  # ggml : 16 bas puis 16 hauts
        echelle = np.ldexp(1.0, brut["e"].astype(np.int64) - 127)
        return (valeurs * echelle[:, None]).reshape(lignes, colonnes)
    colonnes, lignes = t.dims
    brut = np.frombuffer(lire(f, t.decalage, t.nb_octets), dtype=np.dtype([("d", "<f2"), ("q", "i1", 32)]))
    return (brut["q"].astype(np.float64) * brut["d"].astype(np.float64)[:, None]).reshape(lignes, colonnes)


# --- 3. ajustement refait autrement ------------------------------------------------------------
def balayage_vectorise(x: np.ndarray, n_min: int = 50, morceau: int = 256):
    N = x.size
    lx = np.log(x)
    queue_somme = np.cumsum(lx[::-1])[::-1]
    idx = np.arange(N - n_min + 1)
    # candidats : premières occurrences des valeurs distinctes
    idx = idx[np.r_[True, x[idx[1:]] != x[idx[1:] - 1]]]
    n = N - idx
    a = 1.0 + n / (queue_somme[idx] - n * lx[idx])
    Dmin, imin = math.inf, -1
    for d in range(0, idx.size, morceau):
        ii = idx[d:d + morceau]
        aa = a[d:d + morceau][:, None]
        nn = n[d:d + morceau][:, None]
        j = np.arange(N)[None, :] - ii[:, None]          # rang dans la queue
        valide = j >= 0
        q = np.where(valide, x[None, :] / x[ii][:, None], 1.0)
        F = 1.0 - q ** (1.0 - aa)
        dp = np.where(valide, (j + 1) / nn - F, -np.inf).max(axis=1)
        dm = np.where(valide, F - j / nn, -np.inf).max(axis=1)
        D = np.maximum(dp, dm)
        k = int(np.argmin(D))
        if D[k] < Dmin:
            Dmin, imin = float(D[k]), int(ii[k])
    return imin, Dmin


def alpha_numerique(t: np.ndarray, xm: float) -> float:
    ly = np.log(t / xm).sum()
    n = t.size
    # ℓ(α) = n ln(α − 1) − n ln x_min − α Σ ln(tᵢ/x_min)
    # (version 1, fausse : « − α (ly + n ln x_min) » = − α Σ ln tᵢ ; journal second-chemin.log, barré)
    r = optimize.minimize_scalar(lambda a: -(n * math.log(a - 1) - n * math.log(xm) - a * ly),
                                 bounds=(1.0001, 50.0), method="bounded", options={"xatol": 1e-12})
    return float(r.x)


def lr_scipy(t: np.ndarray, xm: float, a: float):
    lpl = stats.pareto.logpdf(t, a - 1.0, scale=xm)
    lex = stats.expon.logpdf(t, loc=xm, scale=t.mean() - xm)
    lt = np.log(t)

    def nll(p):
        mu, s = p
        if s <= 1e-4:
            return 1e300
        d = stats.lognorm(s, scale=math.exp(mu))
        return -float((d.logpdf(t) - d.logsf(xm)).sum())

    best = None
    for d0 in [(lt.mean(), lt.std() + 1e-3), (math.log(xm) - 10, 3.0), (math.log(xm) - 30, 5.0)]:
        r = optimize.minimize(nll, d0, method="Nelder-Mead", options={"xatol": 1e-9, "fatol": 1e-9, "maxiter": 20000})
        if best is None or r.fun < best.fun:
            best = r
    mu, s = best.x
    d = stats.lognorm(s, scale=math.exp(mu))
    lln = d.logpdf(t) - d.logsf(xm)

    def v(l):
        R = float(l.sum())
        return R, float(special.erfc(abs(R) / (l.std() * math.sqrt(2 * l.size))))
    return v(lpl - lex), v(lpl - lln)


def p_gof_autre(x, i, xm, a, D, rng, rep=100):
    N = x.size
    plus = 0
    for _ in range(rep):
        nq = rng.binomial(N, (N - i) / N)
        xr = np.sort(np.concatenate([rng.choice(x[:i], N - nq) if i > 0 and nq < N else np.empty(0),
                                     xm * (1 - rng.random(nq)) ** (-1.0 / (a - 1.0))]))
        _, Dr = balayage_vectorise(xr)
        plus += Dr >= D
    return plus / rep


def main() -> None:
    commun.priorite_basse()
    lec = commun.lecteur()   # pour les décalages et formes seulement (en-tête)
    index = {t.nom: t for t in lec.tenseurs}
    with open(os.path.join(commun.MESURES, "manifeste.json"), encoding="utf8") as f:
        man = {m["id"]: m for m in json.load(f)["matrices"]}
    vs = np.load(os.path.join(commun.MESURES, "valeurs-singulieres.npz"))
    rng = np.random.default_rng(commun.GRAINE + 7777)
    sortie = csv.writer(sys.stdout, lineterminator="\n")
    sortie.writerow(["id", "sha_egal", "ecart_rel_max_queue", "alpha2", "x_min2", "n_queue2", "ks2", "ks_scipy",
                     "R_exp2", "p_exp2", "R_ln2", "p_ln2", "p_gof2", "verdict2", "compatible2"])
    with open(commun.FICHIER, "rb") as f:
        for m in commun.echantillon():
            commun.attendre_calme()
            w = matrice_spec(f, index[m["tenseur"]], max(m["expert"], 0))
            # le décodeur bit à bit rend −0,0 pour le code 8 (signe du zéro), la table +0,0 :
            # w + 0,0 ramène −0,0 à +0,0 (IEEE 754), on compare les valeurs, pas le signe d'un zéro
            w = w + 0.0
            sha = hashlib.sha256(np.ascontiguousarray(w).tobytes()).hexdigest()
            g = w @ w.T if w.shape[0] <= w.shape[1] else w.T @ w
            lam = np.sort(np.linalg.eigvalsh(g))
            del w, g
            x = lam[lam > 0]
            i, D = balayage_vectorise(x)
            xm = float(x[i])
            t = x[i:]
            a = alpha_numerique(t, xm)
            D_scipy = stats.kstest(t, lambda u: 1.0 - (u / xm) ** (1.0 - a)).statistic
            (Re, pe), (Rl, pl) = lr_scipy(t, xm, a)
            pg = p_gof_autre(x, i, xm, a, D, rng)
            if Re > 0 and pe < 0.05 and Rl > 0 and pl < 0.05:
                verdict = "loi de puissance"
            elif (Re < 0 and pe < 0.05) or (Rl < 0 and pl < 0.05):
                verdict = "autre loi préférée"
            else:
                verdict = "non départagée"
            compat = (Re > 0 and pe < 0.05) and not (Rl < 0 and pl < 0.05) and pg >= 0.1
            s2 = np.sort(vs[f"reel/{m['id']}"] ** 2)
            s2 = s2[s2 > 0][-t.size:]
            ecart = float(np.max(np.abs(t - s2) / s2)) if s2.size == t.size else float("nan")
            sortie.writerow([m["id"], sha == man[m["id"]]["sha256_f64"], f"{ecart:.3e}", a, xm, t.size, D, D_scipy,
                             Re, pe, Rl, pl, pg, verdict, compat])
            sys.stdout.flush()
            print(f"{m['id']:16s} sha={'=' if sha == man[m['id']]['sha256_f64'] else 'DIFF'} écart {ecart:.1e} "
                  f"α2={a:.4f} {verdict} compat={compat}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
