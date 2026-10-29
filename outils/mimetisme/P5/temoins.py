"""P5 : temoins W1, W2, W4 (sans fichier modele, sans capture). Seuils : mesures/mimetisme/P5/00-seuil-declare.md.

  python -I -X utf8 temoins.py > journal.json
W3 (decodage par sphere a n = 16 sur un bloc reel de H) est dans etape1.py : il lit une capture.
"""
import json
import os
import sys
import time

import numpy as np
from scipy import linalg

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p5lib as P  # noqa: E402
from concurrent.futures import ThreadPoolExecutor  # noqa: E402

N, K = 10, 5
NINST = 1000
NSW = int(os.environ.get('P5_SWEEPS', 200))
NT_ = int(os.environ.get('P5_NT', 8))
LO = float(os.environ.get('P5_LO', 0.03))
HI = float(os.environ.get('P5_HI', 1.5))
SKIP_PY = bool(int(os.environ.get('P5_SKIP_PY', 0)))
NIV = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])


def hessienne_correlee(rng, n):
    """H = V diag(l) V^T, V orthogonale aleatoire, spectre log-uniforme sur 3 decades."""
    V, _ = np.linalg.qr(rng.standard_normal((n, n)))
    lam = 10 ** rng.uniform(0, 3, n)
    H = (V * lam) @ V.T
    return (H + H.T) / 2


def instance(rng):
    H = hessienne_correlee(rng, N)
    w = 1.5 * rng.standard_normal(N)
    return H, w


def temperatures(H, nt=8, lo=0.03, hi=1.5):
    u = float(np.trace(H) / len(H))  # echelle d'un changement de niveau de pas 1
    return u * np.geomspace(lo, hi, nt)


def pt_toy(H, w, q0, temps, nsweeps, trempe=20, seed=1):
    lev = np.tile(NIV, (N, 1))
    Q, st = P.pt(H, w[None, :], np.ones((1, N)), NIV, np.zeros(K), 0.0, q0[None, :].astype(np.uint8), temps, nsweeps,
                 every=1, trempe=trempe, seed=seed, fils=1)
    return Q[0], st[0]


def une_instance(i):
    rng = np.random.default_rng(1000 + i)
    H, w = instance(rng)
    L = linalg.cholesky(H, lower=True)
    lev = np.tile(NIV, (N, 1))
    cost = np.zeros((N, K))
    eopt, idx, nd = P.enum_best(L, lev, w, cost, False)
    qb = P.babai_generique(H, w, lev, cost)
    eb = float(P.energie(H, w, np.ones(N), NIV, np.zeros(K), 0.0, qb.astype(np.uint8))[0])
    temps = temperatures(H, NT_, LO, HI)
    qp, stp = pt_toy(H, w, qb, temps, NSW)
    ep = float(P.energie(H, w, np.ones(N), NIV, np.zeros(K), 0.0, qp)[0])
    # cassure (i) : zero balayage, pas de trempe -> Babai exactement
    q0, _ = pt_toy(H, w, qb, temps, 0, trempe=0)
    e0 = float(P.energie(H, w, np.ones(N), NIV, np.zeros(K), 0.0, q0)[0])
    # cassure (ii) : temperatures gelees
    qg, _ = pt_toy(H, w, qb, np.full(8, 1e-9) * np.arange(1, 9), NSW)
    eg = float(P.energie(H, w, np.ones(N), NIV, np.zeros(K), 0.0, qg)[0])
    # cassure (iii) : H permute (colonnes et rangees melangees) : l'etat trouve sous le mauvais H, evalue sous le vrai
    perm = rng.permutation(N)
    Hp = H[np.ix_(perm, perm)]
    qpp, _ = pt_toy(Hp, w, qb, temperatures(Hp, NT_, LO, HI), NSW)
    epp = float(P.energie(H, w, np.ones(N), NIV, np.zeros(K), 0.0, qpp)[0])
    cond = float(np.linalg.cond(H))
    return dict(i=i, eopt=float(eopt), eb=eb, ep=ep, e0=e0, eg=eg, epp=epp, noeuds=int(nd), cond=cond,
                babai_ok=bool(eb <= eopt * (1 + 1e-9) + 1e-12), pt_ok=bool(ep <= eopt * (1 + 1e-9) + 1e-12),
                gel_ok=bool(eg <= eopt * (1 + 1e-9) + 1e-12), perm_ok=bool(epp <= eopt * (1 + 1e-9) + 1e-12),
                zero_egal_babai=bool(abs(e0 - eb) <= 1e-12 * max(1.0, abs(eb))))


def python_force_brute(i):
    """Second enumerateur, en numpy pur et par morceaux, sur l'instance i (independant du Rust)."""
    rng = np.random.default_rng(1000 + i)
    H, w = instance(rng)
    best = np.inf
    # fixe les deux premiers chiffres, enumere les 8 autres par morceaux
    import itertools
    rest = np.array(list(itertools.product(range(K), repeat=N - 3)), dtype=np.int8)  # 5^7 = 78125
    for a in range(K):
        for b in range(K):
            for c3 in range(K):
                idx = np.concatenate([np.tile(np.array([a, b, c3], dtype=np.int8), (len(rest), 1)), rest], axis=1)
                r = w[None, :] - NIV[idx]
                e = np.einsum("ij,jk,ik->i", r, H, r, optimize=True)
                best = min(best, float(e.min()))
    return best


def main():
    t0 = time.time()
    with ThreadPoolExecutor(2) as ex:
        res = list(ex.map(une_instance, range(NINST)))
    t1 = time.time()
    babai_echecs = [r for r in res if not r["babai_ok"]]
    pt_echecs = [r for r in res if not r["pt_ok"]]
    # parmi les instances ou Babai echoue : le PT les retrouve-t-il, le gele les retrouve-t-il ?
    pt_sur_babai_echecs = sum(r["pt_ok"] for r in babai_echecs)
    gel_sur_babai_echecs = sum(r["gel_ok"] for r in babai_echecs)
    perm_sur_babai_echecs = sum(r["perm_ok"] for r in babai_echecs)
    # second enumerateur sur 12 instances
    bruts = []
    for i in range(0 if SKIP_PY else 12):
        eb_py = python_force_brute(i)
        bruts.append(dict(i=i, rust=res[i]["eopt"], python=eb_py,
                          egal=bool(abs(eb_py - res[i]["eopt"]) <= 1e-9 * max(1.0, abs(eb_py)))))
    t2 = time.time()
    # W4 : Babai generique == synonyme.choisir sur 256 colonnes (une rangee, grille reelle, lam = 0)
    rng = np.random.default_rng(7)
    n4, R4 = 256, 8
    Xs = rng.standard_normal((600, n4)) * (10 ** rng.uniform(-1, 1, n4))
    Hs = (Xs.T @ Xs) / 600
    Hs += 0.01 * np.mean(np.diag(Hs)) * np.eye(n4)
    Wg = rng.standard_normal((R4, n4)) * 0.05
    Wq, ex, codes = P.quantifier_mxfp4(Wg)
    cen = np.array([0.4743314623654055, 2.8485956707018243, 6.837153999339096, 12.0])
    sym_ref = P.syn.choisir(Wq, ex, cen, Hs, 0.0, np.zeros(8))
    c8 = np.concatenate([cen, -cen])
    S = np.repeat(P.syn.echelle(ex), 32, axis=-1)
    U = P.syn.facteur_inverse(Hs)
    diff = 0
    for r in range(R4):
        lev = c8[None, :] * S[r][:, None]
        cost = np.zeros((n4, 8))
        m = P.babai_generique(Hs, Wq[r], lev, cost, lamp=0.0, U=U, signe8=True)
        diff += int((P.niveau_vers_sym(m) != sym_ref[r]).sum())
    j = dict(
        outil="temoins.py", reglage_PT=dict(balayages=NSW, temperatures=NT_, tmin=LO, tmax=HI), n=N, niveaux=K, instances=NINST, etats_par_instance=K ** N,
        duree_s_PT_et_brute=t1 - t0, duree_s_python=t2 - t1,
        babai_echecs=len(babai_echecs), babai_echecs_pct=100 * len(babai_echecs) / NINST,
        pt_echecs=len(pt_echecs),
        W1a_pt_retrouve_optimum_sur_toutes=bool(len(pt_echecs) == 0),
        W1b_il_existe_une_instance_ou_babai_echoue=bool(len(babai_echecs) > 0),
        W2i_zero_balayage_egal_babai_sur_toutes=bool(all(r["zero_egal_babai"] for r in res)),
        W2ii_gele_retrouve_optimum_sur_les_echecs_de_babai=f"{gel_sur_babai_echecs}/{len(babai_echecs)}",
        W2ii_gele_echoue_sur_au_moins_une=bool(gel_sur_babai_echecs < len(babai_echecs)),
        W2iii_H_permute_retrouve_optimum_sur_les_echecs_de_babai=f"{perm_sur_babai_echecs}/{len(babai_echecs)}",
        pt_retrouve_sur_les_echecs_de_babai=f"{pt_sur_babai_echecs}/{len(babai_echecs)}",
        second_enumerateur_python=bruts, second_enumerateur_tous_egaux=bool(all(b["egal"] for b in bruts)) if bruts else None,
        W4_symboles_differents_babai_generique_contre_choisir=diff, W4_tient=bool(diff == 0),
        ecart_relatif_babai_median_sur_les_echecs=float(np.median([(r["eb"] - r["eopt"]) / r["eopt"] for r in babai_echecs])) if babai_echecs else None,
        ecart_relatif_babai_max=float(max((r["eb"] - r["eopt"]) / r["eopt"] for r in res)),
        conditionnement_median=float(np.median([r["cond"] for r in res])),
        premieres_echecs_de_pt=[r["i"] for r in pt_echecs][:20],
    )
    print(json.dumps(j, ensure_ascii=False, indent=1))
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "mesures", "mimetisme", "P5", "temoins-instances.json"), "w") as f:
        json.dump(res, f)


if __name__ == "__main__":
    main()
