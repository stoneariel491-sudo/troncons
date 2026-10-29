"""P5 juge, phase optionnelle (descriptive) : échange de répliques écrit de zéro en numpy, sur les poids de J1.

Bain thermique par coordonnée (tirage de Gumbel), 8 températures géométriques de 0,02 à 1,0 fois l'erreur
de Babai par poids (le réglage déclaré par P5), échange entre voisines après chaque balayage, meilleur état
de chaque rangée gardé, puis trempe à T = 0 (ma CD) depuis lui. Ne réutilise rien du noyau Rust de P5.
  python -I -X utf8 juge_pt.py --couche 0 --expert 16 [--balayages 40]
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import juge_p5 as J  # noqa: E402  (fixe les fils a 2 et la priorite sous la normale)
import numpy as np  # noqa: E402
from scipy.linalg import blas  # noqa: E402


def pt(W, s, Q0, H, temps, nbal, rng):
    R, n = W.shape
    K = len(temps)
    C = R * K
    Wr = np.repeat(W, K, axis=0)            # chaine c = rangee c // K, temperature c % K
    sr = np.repeat(s, K, axis=0)
    Q = np.repeat(Q0, K, axis=0)
    Wh = J.C8[Q] * sr
    Dl = Wr - Wh
    G = np.ascontiguousarray(Dl @ H)
    E = np.sum(G * Dl, axis=1)
    T = np.tile(temps, R)
    dH = np.diag(H).copy()
    bestE = E.reshape(R, K).min(axis=1)
    bestQ = Q0.copy()
    lignes = np.arange(C)
    ech = 0
    tent = 0
    for _ in range(nbal):
        for j in range(n):
            v = J.C8[None, :] * sr[:, j][:, None]
            dl = Wh[:, j][:, None] - v
            dE = 2 * dl * G[:, j][:, None] + dl * dl * dH[j]
            gum = rng.gumbel(size=dE.shape)
            k = np.argmax(-dE / T[:, None] + gum, axis=1)
            d = dl[lignes, k]
            if np.any(d != 0):
                blas.dger(1.0, H[j], d, a=G.T, overwrite_a=True)   # G += d H_j (Fortran view of G)
                E += dE[lignes, k]
                Wh[:, j] = v[lignes, k]
                Q[:, j] = k
        Er = E.reshape(R, K)
        m = Er.argmin(axis=1)
        amel = Er[np.arange(R), m] < bestE
        for r in np.nonzero(amel)[0]:
            bestE[r] = Er[r, m[r]]
            bestQ[r] = Q[r * K + m[r]]
        # echange entre temperatures voisines, alternance pair / impair
        for a0 in (0, 1):
            for t in range(a0, K - 1, 2):
                c1 = np.arange(R) * K + t
                c2 = c1 + 1
                x = (E[c1] - E[c2]) * (1 / T[c1] - 1 / T[c2])
                ok = np.log(rng.random(R)) < x
                tent += R
                ech += int(ok.sum())
                ii1, ii2 = c1[ok], c2[ok]
                for arr in (Q, Wh, G):
                    tmp = arr[ii1].copy()
                    arr[ii1] = arr[ii2]
                    arr[ii2] = tmp
                tmp = E[ii1].copy()
                E[ii1] = E[ii2]
                E[ii2] = tmp
    return bestQ, ech / max(tent, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--couche", type=int, required=True)
    ap.add_argument("--expert", type=int, required=True)
    ap.add_argument("--graine", type=int, default=1)
    ap.add_argument("--lignes", type=int, default=64)
    ap.add_argument("--balayages", type=int, default=40)
    a = ap.parse_args()
    t0 = time.time()
    l, e = a.couche, a.expert
    hc, cc, gc_ = J.lire("calib", l)
    he, ce, ge_ = J.lire("eval", l)
    Xc, gc = J.entrees(hc, cc, gc_, e)
    Xt, gt = J.entrees(he, ce, ge_, e)
    Htr, Hc, Ht = J.gram(Xc, gc, 1.0), J.gram(Xc, gc, 0.0), J.gram(Xt, gt, 0.0)
    W, s, *_ = J.mxfp4(np.random.default_rng(a.graine).standard_normal((a.lignes, J.N)))
    Qb = J.babai(W, s, J.facteur(Htr))
    Db = W - J.C8[Qb] * s
    eb = float(np.sum((Db @ Htr) * Db) / Db.size)
    temps = eb * np.geomspace(0.02, 1.0, 8)
    tp = time.time()
    Qbest, tx = pt(W, s, Qb, Htr, temps, a.balayages, np.random.default_rng(11))
    Qp, nb = J.cd(W, s, Qbest, Htr)
    tp = time.time() - tp
    Qc, _ = J.cd(W, s, Qb, Htr)
    res = {}
    for nom, Q in (("babai", Qb), ("cd", Qc), ("pt", Qp)):
        Wh = J.C8[Q] * s
        res[nom] = dict(err_train=J.err_rel(W, Wh, Htr), err_calib=J.err_rel(W, Wh, Hc), err_test=J.err_rel(W, Wh, Ht),
                        h0=J.h0(Q))
    print(json.dumps(dict(outil="juge_pt.py", couche=l, expert=e, graine=a.graine, lignes=a.lignes,
                          balayages=a.balayages, temperatures=temps.tolist(), taux_echange=tx, t_pt_s=tp, res=res,
                          gain_test_pt=1 - res["pt"]["err_test"] / res["babai"]["err_test"],
                          gain_test_cd=1 - res["cd"]["err_test"] / res["babai"]["err_test"],
                          gain_train_pt=1 - res["pt"]["err_train"] / res["babai"]["err_train"],
                          gain_train_cd=1 - res["cd"]["err_train"] / res["babai"]["err_train"],
                          dh0_pt=res["pt"]["h0"] - res["babai"]["h0"], duree_s=time.time() - t0),
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
