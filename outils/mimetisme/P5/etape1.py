"""P5 etape 1 : le H reel des captures, des poids SYNTHETIQUES gaussiens sur la grille MXFP4.

Compare Babai (la retroaction deployee, synonyme.py::choisir), la descente cyclique de coordonnees (CD)
et l'echange de repliques (PT) sur l'erreur de sortie ponderee, calibration contre evaluation tenue a
l'ecart. Seuils : mesures/mimetisme/P5/00-seuil-declare.md (commit ab92f4e), declares avant la lecture.

  python -I -X utf8 etape1.py une   --couche 8 --expert 0 --lignes 64 --damp 1 --lams 0 --sweeps 60 [--csv f]
  python -I -X utf8 etape1.py sphere (W3, second chemin, n = 16)
"""
import argparse
import json
import os
import sys
import time

import numpy as np
from scipy import linalg

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p5lib as P  # noqa: E402

syn = P.syn
CEN = np.array([0.4743314623654055, 2.8485956707018243, 6.837153999339096, 12.0])  # centres.json["2"]
C8 = np.concatenate([CEN, -CEN])

# U = facteur de Cholesky de H^-1 : memoise par H (la meme H sert a tous les lambda)
_orig_fi = syn.facteur_inverse
_cache = {}


def _fi(H):
    # le cache garde une reference a H : son id ne peut pas etre reutilise par un autre tableau tant qu'il vit
    # (une premiere version cle sur id(H) seul pouvait rendre le U d'une matrice liberee ; corrige le 2026-10-27)
    k = (id(H), H.shape[0])
    if k not in _cache:
        _cache.clear()
        _cache[k] = (H, _orig_fi(H))
    return _cache[k][1]


syn.facteur_inverse = _fi


def matrices(l, e, damp, cible="iso", regime="base"):
    calib, ev = syn.Entrees("calib", l), syn.Entrees("eval", l)
    Xc, gc = calib.expert(e)
    Xe, ge = ev.expert(e)
    if regime in ("test2", "plus", "inclus"):          # addendum 3
        moitie = ev.h.shape[0] // 2
        X1, g1 = ev.expert(e, (0, moitie))
        X2, g2 = ev.expert(e, (moitie, ev.h.shape[0]))
        if regime == "test2":
            Xe, ge = X2, g2
        elif regime == "plus":
            Xc, gc = np.concatenate([Xc, X1]), np.concatenate([gc, g1])
            Xe, ge = X2, g2
        else:                                           # cassure : le test est inclus dans l'entrainement
            Xc, gc = np.concatenate([Xc, X2]), np.concatenate([gc, g2])
            Xe, ge = X2, g2
    Hc = syn.hessienne(Xc, gc, 0.0)
    if cible == "iso":
        Htr = syn.hessienne(Xc, gc, damp)
    elif cible == "diag":      # amortissement de cible diagonale : H + damp * diag(H)
        Htr = Hc.copy()
        Htr[np.diag_indices_from(Htr)] += damp * np.diag(Hc)
    elif cible == "diag-perm":  # cassure : cible diagonale melangee (mauvaises colonnes)
        Htr = Hc.copy()
        Htr[np.diag_indices_from(Htr)] += damp * np.random.default_rng(5).permutation(np.diag(Hc))
    else:
        raise ValueError(cible)
    He = syn.hessienne(Xe, ge, 0.0)
    return dict(Xc=Xc, gc=gc, Xe=Xe, ge=ge, Htr=Htr, Hc=Hc, He=He)


def poids_synthetiques(R, rng):
    """R rangees gaussiennes, quantifiees MXFP4 : la matrice que la mutation synonyme verrait."""
    Wg = rng.standard_normal((R, P.D))
    Wq, ex, codes = P.quantifier_mxfp4(Wg)
    return Wq, ex, codes


def erreur_rel(W, Wh, H):
    d = W - Wh
    num = float(np.einsum("ij,jk,ik->", d, H, d, optimize=True))
    den = float(np.einsum("ij,jk,ik->", W, H, W, optimize=True))
    return num / den


def erreur_rel_x(W, Wh, X, g):
    """Second chemin : sans H, directement sur les entrees : sum_i g_i^2 ||(W - Wh) x_i||^2 / sum_i g_i^2 ||W x_i||^2."""
    w2 = g * g
    a = X @ (W - Wh).T
    b = X @ W.T
    return float((w2 * (a * a).sum(axis=1)).sum() / (w2 * (b * b).sum(axis=1)).sum())


def ligne(nom, lam, Q, W, S, M, extra=None):
    Wh = C8[Q] * S
    d = dict(methode=nom, lam=lam, bits_H0=P.entropie_symboles(Q),
             err_train=erreur_rel(W, Wh, M["Htr"]), err_calib=erreur_rel(W, Wh, M["Hc"]),
             err_eval=erreur_rel(W, Wh, M["He"]),
             err_eval_x=erreur_rel_x(W, Wh, M["Xe"], M["ge"]), err_calib_x=erreur_rel_x(W, Wh, M["Xc"], M["gc"]),
             err_poids=float(((W - Wh) ** 2).sum() / (W * W).sum()))
    if extra:
        d.update(extra)
    return d


def temperatures(e_babai_par_poids, nt, lo, hi):
    return e_babai_par_poids * np.geomspace(lo, hi, nt)


def une(args):
    t0 = time.time()
    rng = np.random.default_rng(args.graine)
    M = matrices(args.couche, args.expert, args.damp, args.cible, args.regime)
    t_h = time.time() - t0
    Wq, ex, codes = poids_synthetiques(args.lignes, rng)
    S = np.repeat(syn.echelle(ex), 32, axis=-1)
    sf = syn.sym_frontiere(codes)
    ell = syn.longueurs(np.bincount(sf.ravel(), minlength=8).astype(np.float64))
    # unite de lambda : erreur moyenne par poids de la frontiere dans les unites de H_train (cf. symboles_variante)
    cfront = syn.cout_unitaire(Wq, syn.reconstruire(ex, sf, CEN), M["Htr"])
    sortie = dict(couche=args.couche, expert=args.expert, damp=args.damp, cible=args.cible, regime=args.regime, lignes=args.lignes,
                  n_calib=int(M["Xc"].shape[0]), n_eval=int(M["Xe"].shape[0]),
                  mean_diag_Htr=float(np.mean(np.diag(M["Htr"]))), cfront=cfront, t_H_s=t_h, lignes_res=[])
    sortie["lignes_res"].append(ligne("frontiere", 0.0, P.sym_vers_niveau(sf), Wq, S, M))
    for lam in args.lams:
        lamp = lam * cfront
        tb = time.time()
        symb = syn.choisir(Wq, ex, CEN, M["Htr"], lamp, ell)
        Qb = P.sym_vers_niveau(symb)
        tb = time.time() - tb
        # energie par poids de Babai dans la fonction objectif (erreur de train + lamp * bits) : echelle des temperatures
        e_b = (sortie["lignes_res"][0]["err_train"] * 0 + 1) * 0  # place-holder, remplace ci-dessous
        Wh = C8[Qb] * S
        d = Wq - Wh
        err_b = float(np.einsum("ij,jk,ik->", d, M["Htr"], d, optimize=True)) / d.size
        sortie["lignes_res"].append(ligne("babai", lam, Qb, Wq, S, M, dict(t_s=tb, e_par_poids=err_b)))
        # descente cyclique de coordonnees depuis Babai
        tc = time.time()
        Qc, stc = P.pt(M["Htr"], Wq, S, C8, ell, lamp, Qb, np.array([1.0]), 0, trempe=args.trempe, seed=args.graine,
                       fils=args.fils)
        tc = time.time() - tc
        sortie["lignes_res"].append(ligne("cd", lam, Qc, Wq, S, M, dict(t_s=tc, balayages=float(stc[:, 7].mean()))))
        # echange de repliques depuis Babai
        if args.sweeps > 0:
            temps = temperatures(err_b, args.nt, args.tlo, args.thi)
            tp = time.time()
            Qp, stp = P.pt(M["Htr"], Wq, S, C8, ell, lamp, Qb, temps, args.sweeps, every=1, trempe=args.trempe,
                           seed=args.graine, fils=args.fils)
            tp = time.time() - tp
            sortie["lignes_res"].append(ligne("pt", lam, Qp, Wq, S, M, dict(
                t_s=tp, taux_echange=float(stp[:, 4].mean()), chg_froid=float(stp[:, 5].mean()),
                chg_chaud=float(stp[:, 6].mean()), temps=temps.tolist(), sweeps=args.sweeps)))
        # coherence : l'energie tenue par le noyau egale l'energie recomputee par le chemin numpy (une rangee)
        e_noy = P.energie(M["Htr"], Wq[0], S[0], C8, ell, lamp, Qb[0])
        e_py = float((Wq[0] - Wh[0]) @ M["Htr"] @ (Wq[0] - Wh[0]))
        sortie.setdefault("coherence_noyau_numpy", []).append(dict(lam=lam, noyau_err=e_noy[1], numpy_err=e_py,
                                                                   rel=abs(e_noy[1] - e_py) / abs(e_py)))
    sortie["duree_s"] = time.time() - t0
    print(json.dumps(sortie, ensure_ascii=False, indent=1))


def sphere(args):
    """W3 : decodage par sphere (n = 16) contre PT, grille reelle, sous-blocs 16 x 16 de H reel (damp 0,01)."""
    rng = np.random.default_rng(args.graine)
    res = []
    for (l, e) in ((0, 0), (8, 0), (16, 16), (23, 16)):
        M = matrices(l, e, 0.01)
        Wq, ex, codes = poids_synthetiques(8, rng)
        S = np.repeat(syn.echelle(ex), 32, axis=-1)
        sf = syn.sym_frontiere(codes)
        ell = syn.longueurs(np.bincount(sf.ravel(), minlength=8).astype(np.float64))
        for t in range(3 if (l, e) in ((0, 0), (8, 0)) else 2):
            i0 = 32 * (t * 7 + 3)
            idx = np.arange(i0, i0 + 16)
            Hs = M["Htr"][np.ix_(idx, idx)]
            w = Wq[t, idx]
            s = S[t, idx]
            L = linalg.cholesky(Hs, lower=True)
            lev = C8[None, :] * s[:, None]
            cost = np.zeros((16, 8))
            mb = P.babai_generique(Hs, w, lev, cost, signe8=True)
            qb = mb.astype(np.uint8)
            eb = P.energie(Hs, w, s, C8, np.zeros(8), 0.0, qb)[0]
            ts = time.time()
            es, idxs, nd = P.enum_best(L, lev, w, cost, True, init_best=eb * (1 + 1e-9) + 1e-300)
            ts = time.time() - ts
            temps = float(np.trace(Hs) / 16) * np.geomspace(0.002, 0.2, 8) * float(np.mean(s) ** 2) * 10
            Qp, stp = P.pt(Hs, w[None, :], s[None, :], C8, np.zeros(8), 0.0, qb[None, :], temps, 300, every=1,
                           trempe=20, seed=3, fils=1)
            ep = P.energie(Hs, w, s, C8, np.zeros(8), 0.0, Qp[0])[0]
            res.append(dict(couche=l, expert=e, bloc=i0, eb=float(eb), esphere=float(es), ept=float(ep),
                            noeuds=int(nd), t_sphere_s=ts, babai_optimal=bool(eb <= es * (1 + 1e-9)),
                            pt_egal_sphere=bool(abs(ep - es) <= 1e-9 * max(abs(es), 1e-300)),
                            sphere_trouve=bool(es < np.inf and (idxs >= 0).all())))
    print(json.dumps(dict(outil="etape1.py sphere", n=16, instances=res,
                          pt_egal_partout=bool(all(r["pt_egal_sphere"] for r in res)),
                          babai_non_optimal=int(sum(not r["babai_optimal"] for r in res))), ensure_ascii=False, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("commande", choices=["une", "sphere"])
    ap.add_argument("--couche", type=int, default=8)
    ap.add_argument("--expert", type=int, default=0)
    ap.add_argument("--lignes", type=int, default=64)
    ap.add_argument("--damp", type=float, default=1.0)
    ap.add_argument("--cible", default="iso", choices=["iso", "diag", "diag-perm"])
    ap.add_argument("--regime", default="base", choices=["base", "test2", "plus", "inclus"])
    ap.add_argument("--lams", type=float, nargs="+", default=[0.0])
    ap.add_argument("--sweeps", type=int, default=60)
    ap.add_argument("--nt", type=int, default=8)
    ap.add_argument("--tlo", type=float, default=0.02)
    ap.add_argument("--thi", type=float, default=1.0)
    ap.add_argument("--trempe", type=int, default=30)
    ap.add_argument("--fils", type=int, default=2)
    ap.add_argument("--graine", type=int, default=1)
    a = ap.parse_args()
    {"une": une, "sphere": sphere}[a.commande](a)


if __name__ == "__main__":
    main()
