"""P5, juge indépendant : le gain d'évaluation de la descente cyclique (CD) contre Babai, par un chemin écrit de zéro.

Rien de p5lib.py, etape1.py ni du noyau Rust de P5. Seuils : mesures/mimetisme/P5/juge/00-seuil-juge.md (commit c5d8c30).
`synonyme.py::choisir` n'est appelé que pour J0 (vérifier que mon Babai est bien le Babai déployé).

  python -I -X utf8 juge_p5.py --couche 8 --expert 0 --regime base --graine 1 [--temoin perm|zero] [--lam 0]
"""
import argparse
import ctypes
import importlib.util
import json
import os
import sys
import time

for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[v] = "2"
import numpy as np  # noqa: E402
from scipy import linalg  # noqa: E402

try:  # sous la normale (BELOW_NORMAL_PRIORITY_CLASS)
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
except Exception:
    pass

CAPT = "~/dev/essais/troncons/genome/eclaireur"
N = 2880
MAGS = np.array([0.0, 1, 2, 3, 4, 6, 8, 12])
CLASSE = np.array([0, 0, 1, 1, 1, 2, 2, 3])  # partition de 07 (frontière)
CEN = np.array([0.4743314623654055, 2.8485956707018243, 6.837153999339096, 12.0])
C8 = np.concatenate([CEN, -CEN])


# ------------------------------------------------------------------ entrées
def lire(quoi, l):
    d = os.path.join(CAPT, quoi)
    h = np.fromfile(os.path.join(d, f"h-L{l:02d}.f32"), dtype="<f4")
    P = h.size // N
    h = h.reshape(P, N)
    rb = np.fromfile(os.path.join(d, f"routage-L{l:02d}.bin"), dtype=np.uint8)
    assert rb.size == 20 * P, (rb.size, P)
    rb = rb.reshape(P, 20)
    choix = rb[:, :4]
    gates = np.frombuffer(rb[:, 4:].tobytes(), dtype="<f4").reshape(P, 4)
    return h, choix, gates


def entrees(h, choix, gates, e, p0=0, p1=None):
    p1 = h.shape[0] if p1 is None else p1
    rows, slot = np.where(choix[p0:p1] == e)
    return h[p0:p1][rows].astype(np.float64), gates[p0:p1][rows, slot].astype(np.float64)


def gram(X, g, delta):
    a = g * g
    Xw = X * np.sqrt(a)[:, None]
    H = Xw.T @ Xw / a.sum()
    if delta:
        H = H + delta * np.trace(H) / N * np.eye(N)
    return H


# ------------------------------------------------------------------ poids
def mxfp4(Wg):
    R = Wg.shape[0]
    b = np.abs(Wg).reshape(R, N // 32, 32).max(axis=2)
    ex = np.floor(np.log2(b)).astype(int) - 3
    s = np.repeat(2.0 ** ex, 32, axis=1)
    mag = np.abs(Wg) / s
    code = np.argmin(np.abs(mag[:, :, None] - MAGS[None, None, :]), axis=2)
    neg = np.signbit(Wg)
    Wq = np.where(neg, -1.0, 1.0) * MAGS[code] * s
    return Wq, s, code, neg, (ex + 128).astype(np.uint8), (code | (neg.astype(int) << 3)).astype(np.uint8)


# ------------------------------------------------------------------ Babai
def facteur(H):
    """U supérieure, U^T U = H^-1 : Cholesky de H^-1 (chemin GPTQ classique, pas celui de synonyme.py)."""
    Hi = linalg.cho_solve(linalg.cho_factor(H, lower=True), np.eye(N))
    return np.linalg.cholesky(Hi).T.copy()


def babai(W, s, U, lamp=0.0, ell=None):
    """Indices de niveau m in [0, 8) (m = classe + 4 * signe), signe fixé par le poids courant."""
    R = W.shape[0]
    Wc = W.copy()
    Q = np.zeros((R, N), dtype=np.int64)
    for j in range(N):
        w = Wc[:, j]
        neg = np.signbit(w)
        cand = s[:, j][:, None] * CEN[None, :]
        c = (np.abs(w)[:, None] - cand) ** 2
        if lamp > 0:
            c = c + lamp * U[j, j] ** 2 * np.where(neg[:, None], ell[None, 4:], ell[None, :4])
        k = np.argmin(c, axis=1)
        Q[:, j] = k + 4 * neg
        q = np.where(neg, -1.0, 1.0) * cand[np.arange(R), k]
        err = (w - q) / U[j, j]
        Wc[:, j:] -= err[:, None] * U[j, j:][None, :]
    return Q


# ------------------------------------------------------------------ descente cyclique
def cd(W, s, Q0, H, lamp=0.0, ell=None, max_bal=30):
    Q = Q0.copy()
    R = W.shape[0]
    Wh = C8[Q] * s
    G = (W - Wh) @ H                     # g = H r par rangée
    dH = np.diag(H).copy()
    elln = np.zeros(8) if ell is None else ell
    bal = 0
    for bal in range(1, max_bal + 1):
        chg = 0
        for j in range(N):
            v = C8[None, :] * s[:, j][:, None]             # (R, 8)
            dl = Wh[:, j][:, None] - v                      # delta r_j
            dE = 2 * dl * G[:, j][:, None] + dl * dl * dH[j]
            if lamp > 0:
                dE = dE + lamp * (elln[None, :] - elln[Q[:, j]][:, None])
            k = np.argmin(dE, axis=1)
            best = dE[np.arange(R), k]
            m = best < -1e-15 * (1 + np.abs(G[:, j] * Wh[:, j]))
            if m.any():
                ii = np.nonzero(m)[0]
                d = dl[ii, k[ii]]
                G[ii] += d[:, None] * H[j][None, :]
                Wh[ii, j] = v[ii, k[ii]]
                Q[ii, j] = k[ii]
                chg += len(ii)
        if chg == 0:
            break
    return Q, bal


def err_rel(W, Wh, H):
    D = W - Wh
    return float(np.sum((D @ H) * D) / np.sum((W @ H) * W))


def err_rel_x(W, Wh, X, g):
    a = g * g
    A = X @ (W - Wh).T
    B = X @ W.T
    return float((a * (A * A).sum(1)).sum() / (a * (B * B).sum(1)).sum())


def h0(Q):
    c = np.bincount(Q.ravel(), minlength=8).astype(float)
    p = c[c > 0] / c.sum()
    return float(-(p * np.log2(p)).sum())


def charger_syn():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "genome", "eclaireur", "synonyme.py")
    spec = importlib.util.spec_from_file_location("syn_ref", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--couche", type=int, required=True)
    ap.add_argument("--expert", type=int, required=True)
    ap.add_argument("--regime", default="base", choices=["base", "test2", "plus", "inclus", "demi"])
    ap.add_argument("--graine", type=int, default=1)
    ap.add_argument("--lignes", type=int, default=64)
    ap.add_argument("--delta", type=float, default=1.0)
    ap.add_argument("--lam", type=float, default=0.0)
    ap.add_argument("--temoin", default="", choices=["", "perm", "zero"])
    ap.add_argument("--j0", action="store_true", help="compare mon Babai a synonyme.py::choisir")
    a = ap.parse_args()
    t0 = time.time()
    l, e = a.couche, a.expert
    hc, cc, gc_ = lire("calib", l)
    he, ce, ge_ = lire("eval", l)
    Xc, gc = entrees(hc, cc, gc_, e)
    Pe = he.shape[0]
    if a.regime in ("base", "demi"):
        Xt, gt = entrees(he, ce, ge_, e)
        if a.regime == "demi":   # addendum J5 : N seul, premiere moitie des positions de calibration
            Xc, gc = entrees(hc, cc, gc_, e, 0, hc.shape[0] // 2)
    else:
        mo = Pe // 2
        X1, g1 = entrees(he, ce, ge_, e, 0, mo)
        Xt, gt = entrees(he, ce, ge_, e, mo, Pe)
        if a.regime == "plus":
            Xc, gc = np.concatenate([Xc, X1]), np.concatenate([gc, g1])
        elif a.regime == "inclus":
            Xc, gc = np.concatenate([Xc, Xt]), np.concatenate([gc, gt])
    Htr = gram(Xc, gc, a.delta)
    Hc = gram(Xc, gc, 0.0)
    Ht = gram(Xt, gt, 0.0)
    rng = np.random.default_rng(a.graine)
    Wg = rng.standard_normal((a.lignes, N))
    W, s, code, neg, exb, codes = mxfp4(Wg)
    U = facteur(Htr)
    lamp, ell = 0.0, None
    if a.lam > 0:
        sf = (neg.astype(int) << 2) | CLASSE[code]
        hist = np.bincount(sf.ravel(), minlength=8).astype(float)
        ell = -np.log2((hist + 0.5) / (hist + 0.5).sum())
        kf = (sf & 3) + 4 * (sf >> 2)
        Df = W - C8[kf] * s
        lamp = a.lam * float(np.sum((Df @ Htr) * Df) / Df.size)
    tb = time.time()
    Qb = babai(W, s, U, lamp, ell)
    tb = time.time() - tb
    out = dict(outil="juge_p5.py", couche=l, expert=e, regime=a.regime, graine=a.graine, lignes=a.lignes,
               delta=a.delta, lam=a.lam, temoin=a.temoin, n_train=int(Xc.shape[0]), n_test=int(Xt.shape[0]),
               positions_eval=int(Pe))
    if a.j0:
        syn = charger_syn()
        ell_s = np.zeros(8) if ell is None else ell
        sym = syn.choisir(W, exb, CEN, Htr, lamp, ell_s)
        Qs = ((sym & 3) + 4 * ((sym >> 2) & 1)).astype(np.int64)
        out["j0_symboles_differents"] = int((Qs != Qb).sum())
        out["j0_quant_identique"] = bool(np.array_equal(syn.dequant(exb, codes), W))
    Whb = C8[Qb] * s
    if a.temoin == "zero":
        Qc, nb = Qb.copy(), 0
    else:
        Hopt = Htr
        if a.temoin == "perm":
            p = np.random.default_rng(7).permutation(N)
            Hopt = Htr[np.ix_(p, p)]
        tc = time.time()
        Qc, nb = cd(W, s, Qb, Hopt, lamp, ell)
        out["t_cd_s"] = time.time() - tc
    Whc = C8[Qc] * s
    res = {}
    for nom, Wh, Q in (("babai", Whb, Qb), ("cd", Whc, Qc)):
        res[nom] = dict(err_train=err_rel(W, Wh, Htr), err_calib=err_rel(W, Wh, Hc), err_test=err_rel(W, Wh, Ht),
                        err_test_x=err_rel_x(W, Wh, Xt, gt), h0=h0(Q))
    out.update(res=res, balayages_cd=nb, t_babai_s=tb,
               gain_test=1 - res["cd"]["err_test"] / res["babai"]["err_test"],
               gain_calib=1 - res["cd"]["err_calib"] / res["babai"]["err_calib"],
               gain_train=1 - res["cd"]["err_train"] / res["babai"]["err_train"],
               dh0=res["cd"]["h0"] - res["babai"]["h0"], duree_s=time.time() - t0)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
