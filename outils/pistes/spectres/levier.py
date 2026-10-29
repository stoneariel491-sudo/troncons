"""Piste spectres, pas 4 : le spectre ouvre-t-il un levier de compression ? (seuil.md § 7)

Pour chaque matrice de l'échantillon et son témoin, aux rangs r ∈ {0, 1, 2, 4, 8, 16, 32, 64} :
- L1 (sans perte, matrices MXFP4) : H(code | échelle) − H(code | échelle, case de L̂_r / échelle), en
  bits par poids, le signe du zéro fondu d'abord (le levier est compté au-delà du codon synonyme) ;
  L̂_r = (U_r Σ_r) Vᵣᵀ, facteurs arrondis en f16 (ce que le décodeur aurait) ; 16 cases : la valeur
  E2M1 la plus proche de la prédiction (15 valeurs) et le signe de la prédiction pour la case zéro.
  Témoin T-blocs : les blocs MXFP4 (échelle + 32 codes) permutés au hasard ; H(code | échelle) est
  inchangé, toute structure entre blocs est détruite.
- L2 (avec perte, calculé) : remplissage inverse par rangée, gaussienne par rangée, à l'erreur absolue
  D · ‖W‖² (D = 0,044) : sur W, puis sur W − L̂_r, plus le coût des facteurs.
- L3d (avec perte, mesuré, v3) : quantificateur scalaire uniforme à tramage soustractif, pas en forme
  close Δ = √(12 · D · ‖W‖² / N), entropie empirique des indices (L3d : sans information annexe ;
  L3dr : conditionnelle à la rangée), sur W puis sur W − L̂_r, plus le coût des facteurs.
  ~~L3 (v2) : même quantificateur sans tramage, pas par dichotomie~~ : faussé par la discrétude des
  matrices MXFP4 (seuil.md § 7 ter) ; la fonction `ecsq` est gardée pour la trace, non appelée.
  Témoin T-perm pour L2 et L3d : entrées permutées, L̂_r tiré de la SVD de la matrice permutée.
Coût des facteurs : 16 · r · (m + n) / (m · n) bits par poids.

Utilisation : python -X utf8 levier.py [--temoin-plante] > levier.csv
"""
from __future__ import annotations

import commun

import csv
import math
import sys

import numpy as np
from scipy.sparse.linalg import svds

D_REL = 0.044
RANGS = (0, 1, 2, 4, 8, 16, 32, 64)
GRILLE = np.array([-12, -8, -6, -4, -3, -2, -1, 0, 1, 2, 3, 4, 6, 8, 12], dtype=np.float64)  # en unités K
MILIEUX = 0.5 * (GRILLE[1:] + GRILLE[:-1])
# code MXFP4 (table K) de chaque valeur de GRILLE ; le zéro prend le code 0 (+0)
CODE_DE_GRILLE = np.array([15, 14, 13, 12, 11, 10, 9, 0, 1, 2, 3, 4, 5, 6, 7], dtype=np.uint8)


def entropie_cond(sym: np.ndarray, ctx: np.ndarray, n_sym: int) -> float:
    """H(sym | ctx) en bits, estimateur par comptage (ctx entier ≥ 0)."""
    cle = ctx.astype(np.int64) * n_sym + sym.astype(np.int64)
    c = np.bincount(cle.ravel(), minlength=(int(ctx.max()) + 1) * n_sym).reshape(-1, n_sym).astype(np.float64)
    tot = c.sum(axis=1, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        h = -np.nansum(c * np.log2(np.where(c > 0, c / np.where(tot > 0, tot, 1), 1)))
    return float(h / c.sum())


def facteurs(w: np.ndarray, kmax: int, graine: int):
    rng = np.random.default_rng(graine)
    u, s, vt = svds(w, k=kmax, v0=rng.standard_normal(min(w.shape)))
    o = np.argsort(s)[::-1]
    us = (u[:, o] * s[o]).astype(np.float16).astype(np.float64)
    v = vt[o].astype(np.float16).astype(np.float64)
    return us, v


def cout(r: int, m: int, n: int) -> float:
    return 16.0 * r * (m + n) / (m * n)


# --- L1 ------------------------------------------------------------------------------------
def l1(codes: np.ndarray, expo: np.ndarray, us, v) -> dict:
    m, n = codes.shape
    c = codes.copy()
    c[c == 8] = 0                                    # −0 fondu sur +0
    e_poids = np.repeat(expo, 32, axis=1)            # exposant de chaque poids
    e_ctx = e_poids - e_poids.min()
    base = entropie_cond(c, e_ctx, 16)
    sortie = {"H_base": base}
    echelle = np.ldexp(1.0, e_poids - 128)
    for r in RANGS[1:]:
        p = (us[:, :r] @ v[:r]) / echelle            # prédiction en unités de la table K
        case = np.searchsorted(MILIEUX, p)                     # 0..14, valeur de GRILLE la plus proche
        case = np.where((case == 7) & (p < 0), 15, case)       # la case zéro coupée par le signe
        h = entropie_cond(c, e_ctx * 16 + case, 16)
        sortie[r] = base - h - cout(r, m, n)
    return sortie


# --- L2 ------------------------------------------------------------------------------------
def debit_absolu(v: np.ndarray, total: float) -> float:
    lo, hi = 0.0, float(v.max())
    for _ in range(200):
        th = 0.5 * (lo + hi)
        if np.minimum(th, v).sum() > total:
            hi = th
        else:
            lo = th
    d = np.minimum(lo, v)
    ok = v > 0
    return float(np.sum(0.5 * np.log2(v[ok] / d[ok])) / v.size)


# --- L3 ------------------------------------------------------------------------------------
def ecsq(x: np.ndarray, total: float):
    """Pas global Δ tel que Σ (x − Δ·round(x/Δ))² = total ; rend (H global, H | rangée)."""
    def erreur(y, d):
        return float(((y - d * np.round(y / d)) ** 2).sum())

    # 1) dichotomie sur un sous-échantillon fixe de 400 000 entrées (cible mise à l'échelle) ;
    # 2) encadrement à ± 3 % sur toutes les données, vérifié, puis 12 moitiés en log sur toutes
    #    les données : Δ connu à 1 + 1,5·10⁻⁵ près, soit ≈ 2·10⁻⁵ bit sur le débit.
    plat = x.ravel()
    sous = plat[np.random.default_rng(7).choice(plat.size, min(400_000, plat.size), replace=False)]
    cible_sous = total * sous.size / plat.size
    lo, hi = 1e-9, 4.0 * float(np.abs(x).max()) + 1e-9
    for _ in range(40):
        d = math.sqrt(lo * hi)
        if erreur(sous, d) > cible_sous:
            hi = d
        else:
            lo = d
    d0 = math.sqrt(lo * hi)
    lo, hi = d0 / 1.03, d0 * 1.03
    if not (erreur(plat, lo) <= total < erreur(plat, hi)):
        lo, hi = 1e-9, 4.0 * float(np.abs(x).max()) + 1e-9   # repli : dichotomie complète
        n_iter = 40
    else:
        n_iter = 12
    for _ in range(n_iter):
        d = math.sqrt(lo * hi)
        if erreur(plat, d) > total:
            hi = d
        else:
            lo = d
    q = np.round(x / lo).astype(np.int64)
    q -= q.min()
    ns = int(q.max()) + 1
    cnt = np.bincount(q.ravel(), minlength=ns).astype(np.float64)
    p = cnt[cnt > 0] / cnt.sum()
    h_glob = float(-(p * np.log2(p)).sum())
    lignes = np.repeat(np.arange(x.shape[0]), x.shape[1]).reshape(x.shape)
    h_ligne = entropie_cond(q, lignes, ns)
    return h_glob, h_ligne


def avec_perte(w: np.ndarray, us, v) -> dict:
    m, n = w.shape
    total = D_REL * float((w ** 2).sum())
    sortie = {}
    # debit_absolu compare à Σᵢ vᵢ (variances PAR POIDS des rangées) : la cible est total / n.
    # (version 1, fausse : « total » passé tel quel, n fois trop grand ⇒ θ = max v, débit nul,
    # gain L2 = −c(r) partout ; attrapé par le témoin planté, journal levier-temoin.log du 04:26)
    r0_l2 = debit_absolu((w ** 2).mean(axis=1), total / n)
    g0, l0, e0 = h_tramee(w, total, 11)
    sortie["L2_0"], sortie["L3d_0"], sortie["L3dr_0"], sortie["err_0"] = r0_l2, g0, l0, e0
    for r in RANGS[1:]:
        res = w - us[:, :r] @ v[:r]
        c = cout(r, m, n)
        sortie[f"L2_{r}"] = r0_l2 - (debit_absolu((res ** 2).mean(axis=1), total / n) + c)
        g, l, _ = h_tramee(res, total, 11)
        sortie[f"L3d_{r}"] = g0 - (g + c)
        sortie[f"L3dr_{r}"] = l0 - (l + c)
    return sortie


def h_tramee(x: np.ndarray, total: float, graine: int):
    """Tramage soustractif : q = round(x/Δ + u), x̂ = (q − u)Δ, u ~ U(−½, ½) connu du décodeur.

    L'erreur est uniforme et indépendante de x : énergie N Δ²/12, d'où Δ = √(12 · total / N).
    Rend (H(q) global, H(q | rangée), énergie d'erreur mesurée / cible).
    """
    delta = math.sqrt(12.0 * total / x.size)
    u = np.random.default_rng(graine).random(x.shape) - 0.5
    q = np.round(x / delta + u).astype(np.int64)
    err = float((((q - u) * delta - x) ** 2).sum())
    q -= q.min()
    ns = int(q.max()) + 1
    cnt = np.bincount(q.ravel(), minlength=ns).astype(np.float64)
    p = cnt[cnt > 0] / cnt.sum()
    hg = float(-(p * np.log2(p)).sum())
    lignes = np.repeat(np.arange(x.shape[0]), x.shape[1]).reshape(x.shape)
    hl = entropie_cond(q, lignes, ns)
    return hg, hl, err / total


# --- quantificateur MXFP4 (pour le témoin planté) ------------------------------------------
def quantifier_mxfp4(w: np.ndarray):
    m, n = w.shape
    b = w.reshape(-1, 32)
    amax = np.abs(b).max(axis=1)
    e = np.where(amax > 0, np.ceil(np.log2(np.maximum(amax, 1e-300) / 12.0)), -127).astype(np.int64) + 128
    e = np.clip(e, 1, 254)
    k = b / np.ldexp(1.0, e - 128)[:, None]
    codes = CODE_DE_GRILLE[np.searchsorted(MILIEUX, k)]
    return codes.reshape(m, n), e.reshape(m, n // 32)


def ligne_mxfp4(nom, codes, expo, w, graine, ecrivain, entete, perte=True):
    """perte=False pour T-blocs : ce témoin ne sert qu'à L1 (seuil.md § 7) ; L2 et L3 en NaN."""
    us, v = facteurs(w, max(RANGS), graine)
    a = l1(codes, expo, us, v)
    if perte:
        b = avec_perte(w, us, v)
    else:
        b = {"L2_0": float("nan"), "L3d_0": float("nan"), "L3dr_0": float("nan"), "err_0": float("nan")}
        b.update({f"{p}_{r}": float("nan") for r in RANGS[1:] for p in ("L2", "L3d", "L3dr")})
    lig = {"id": nom, "H_base": a["H_base"]}
    lig.update({f"L1_{r}": a[r] for r in RANGS[1:]})
    lig.update(b)
    if entete[0]:
        ecrivain.writerow(list(lig.keys()))
        entete[0] = False
    ecrivain.writerow([f"{x:.6f}" if isinstance(x, float) else x for x in lig.values()])
    sys.stdout.flush()
    print(f"{nom:24s} L1 max {max(a[r] for r in RANGS[1:]):+.4f}  "
          f"L2 max {max(b[f'L2_{r}'] for r in RANGS[1:]):+.4f}  L3d max {max(b[f'L3d_{r}'] for r in RANGS[1:]):+.4f}  "
          f"L3dr max {max(b[f'L3dr_{r}'] for r in RANGS[1:]):+.4f}", file=sys.stderr, flush=True)


def main() -> None:
    commun.priorite_basse()
    ecrivain = csv.writer(sys.stdout, lineterminator="\n")
    entete = [True]
    rng = np.random.default_rng(commun.GRAINE + 50)
    if "--temoin-plante" in sys.argv:
        # rang 8 planté (30 % de l'énergie) + bruit gaussien, quantifié MXFP4 ; puis sa version T-blocs
        n = 2880
        a = rng.standard_normal((n, 8)) @ rng.standard_normal((8, n))
        bruit = rng.standard_normal((n, n))
        w0 = a / np.sqrt((a ** 2).mean()) * math.sqrt(0.3) + bruit * math.sqrt(0.7)
        codes, expo = quantifier_mxfp4(w0 * 0.02)
        w = commun.K[codes] * np.ldexp(1.0, np.repeat(expo, 32, axis=1) - 128)
        ligne_mxfp4("T-plante-rang8", codes, expo, w, 1, ecrivain, entete)
        o = rng.permutation(codes.size // 32)
        cb = codes.reshape(-1, 32)[o].reshape(n, n)
        eb = expo.reshape(-1)[o].reshape(n, n // 32)
        wb = commun.K[cb] * np.ldexp(1.0, np.repeat(eb, 32, axis=1) - 128)
        ligne_mxfp4("T-plante-rang8.blocs", cb, eb, wb, 2, ecrivain, entete, perte=False)
        # témoin négatif de L2 et L3 : le planté, entrées permutées (même chemin que T-perm)
        wp = rng.permutation(w.ravel()).reshape(w.shape)
        us, v = facteurs(wp, max(RANGS), 3)
        b = avec_perte(wp, us, v)
        lig = {"id": "T-plante-rang8.perm", "H_base": float("nan")}
        lig.update({f"L1_{r}": float("nan") for r in RANGS[1:]})
        lig.update(b)
        ecrivain.writerow([f"{x:.6f}" if isinstance(x, float) else x for x in lig.values()])
        print(f"{'T-plante-rang8.perm':24s} L2 max {max(b[f'L2_{r}'] for r in RANGS[1:]):+.4f}  "
              f"L3d max {max(b[f'L3d_{r}'] for r in RANGS[1:]):+.4f}", file=sys.stderr, flush=True)
        return
    lec = commun.lecteur()
    index = {t.nom: t for t in lec.tenseurs}
    for i, m in enumerate(commun.echantillon()):
        commun.attendre_calme()
        t = index[m["tenseur"]]
        if m["expert"] >= 0:
            codes, expo = commun.codes_mxfp4(lec, t, m["expert"])
            w = commun.matrice_mxfp4(lec, t, m["expert"])
            ligne_mxfp4(m["id"], codes, expo, w, 100 + i, ecrivain, entete)
            # T-blocs : blocs (échelle + 32 codes) permutés
            mm, nn = codes.shape
            o = rng.permutation(codes.size // 32)
            cb = codes.reshape(-1, 32)[o].reshape(mm, nn)
            eb = expo.reshape(-1)[o].reshape(mm, nn // 32)
            wb = commun.K[cb] * np.ldexp(1.0, np.repeat(eb, 32, axis=1) - 128)
            ligne_mxfp4(m["id"] + ".blocs", cb, eb, wb, 200 + i, ecrivain, entete, perte=False)
            del cb, eb, wb
        else:
            w = commun.matrice_q8_0(lec, t)
            us, v = facteurs(w, max(RANGS), 100 + i)
            b = avec_perte(w, us, v)
            lig = {"id": m["id"], "H_base": float("nan")}
            lig.update({f"L1_{r}": float("nan") for r in RANGS[1:]})
            lig.update(b)
            ecrivain.writerow([f"{x:.6f}" if isinstance(x, float) else x for x in lig.values()])
            sys.stdout.flush()
            print(f"{m['id']:24s} L2 max {max(b[f'L2_{r}'] for r in RANGS[1:]):+.4f}  "
                  f"L3d max {max(b[f'L3d_{r}'] for r in RANGS[1:]):+.4f}", file=sys.stderr, flush=True)
        # T-perm pour L2 et L3 : entrées permutées
        wp = rng.permutation(w.ravel()).reshape(w.shape)
        us, v = facteurs(wp, max(RANGS), 300 + i)
        b = avec_perte(wp, us, v)
        lig = {"id": m["id"] + ".perm", "H_base": float("nan")}
        lig.update({f"L1_{r}": float("nan") for r in RANGS[1:]})
        lig.update(b)
        ecrivain.writerow([f"{x:.6f}" if isinstance(x, float) else x for x in lig.values()])
        sys.stdout.flush()
        print(f"{m['id'] + '.perm':24s} L2 max {max(b[f'L2_{r}'] for r in RANGS[1:]):+.4f}  "
              f"L3d max {max(b[f'L3d_{r}'] for r in RANGS[1:]):+.4f}", file=sys.stderr, flush=True)
        del w, wp


if __name__ == "__main__":
    main()
