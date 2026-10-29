"""Juge du lot « espaces latents » : les nombres de III-7.6 (l'espace latent des 6 132 états de la
couche 23), refaits de zéro depuis la capture h-L23.f32, le journal routage-L23.bin, le routeur lu
dans le GGUF, et les coordonnées commitées (mesures/genome/tome3/latents/etats-c23.csv).

Écrit pour troncons le 2026-10-27, sans lire outils/genome/tome3/latents_etats.py ni
memoire/outils/tome3_latents.py. Définitions prises dans la légende de la figure, pas dans le code :
  - expert premier : le plus grand logit biaisé z = W h + b ; marge : z(4) − z(5) (logits triés).
  - ACP centrée non réduite ; part de variance = valeur propre / trace de la covariance.
  - confiance T(k) et continuité C(k) (Venna et Kaski 2001) :
      T(k) = 1 − 2/(n k (2n − 3k − 1)) Σ_i Σ_{j ∈ U_k(i)} (r(i, j) − k),
      U_k(i) les k voisins de i dans le plan qui ne sont pas parmi ses k voisins d'origine,
      r(i, j) le rang de j autour de i dans l'espace d'origine (1 = le plus proche) ;
      C(k) idem en échangeant les deux espaces.
    Les rangs se comptent exactement (nombre de points strictement plus proches, plus un), ligne par
    ligne, sans matrice n × n en mémoire.
  - Spearman des distances : sur 2 000 000 paires tirées (graine du juge), pas celles du lot.
  - accord : part des k = 10 plus proches voisins (soi exclu) qui ont le même expert premier ;
    hasard : Σ_e n_e (n_e − 1) / (n (n − 1)) (deux états distincts tirés au hasard), et Σ p_e².

Usage : python -I -X utf8 juge_etats.py > juge-etats.json
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import juge_commun as jc  # noqa: E402

GRAINE_JUGE = 27102026
COUCHE = 23
K = 10
LAT = os.path.join(jc.DEPOT, "mesures/genome/tome3/latents")
DON = os.path.join(jc.DEPOT, "memoire/figures/tome3/donnees")
BLOC = 256


def d2_lignes(A, i0, i1, nA):
    """Distances au carré des lignes i0:i1 de A à toutes les lignes (Gram, f64), soi mis à +inf."""
    G = A[i0:i1] @ A.T
    d = nA[i0:i1, None] + nA[None, :] - 2.0 * G
    np.maximum(d, 0.0, out=d)
    d[np.arange(i1 - i0), np.arange(i0, i1)] = np.inf
    return d


def voisins_et_rangs(A):
    """Les K voisins de chaque point (indices) dans l'espace A."""
    n = A.shape[0]
    nA = (A * A).sum(axis=1)
    V = np.empty((n, K), dtype=np.int64)
    for i0 in range(0, n, BLOC):
        i1 = min(n, i0 + BLOC)
        d = d2_lignes(A, i0, i1, nA)
        idx = np.argpartition(d, K, axis=1)[:, :K]
        dd = np.take_along_axis(d, idx, axis=1)
        o = np.argsort(dd, axis=1, kind="stable")
        V[i0:i1] = np.take_along_axis(idx, o, axis=1)
    return V, nA


def penalite(A, nA, Vproj, Vorig):
    """Σ_i Σ_{j ∈ Vproj(i) \\ Vorig(i)} (r_A(i, j) − K), r_A le rang dans l'espace A."""
    n = A.shape[0]
    s = 0.0
    for i0 in range(0, n, BLOC):
        i1 = min(n, i0 + BLOC)
        d = d2_lignes(A, i0, i1, nA)
        for t in range(i1 - i0):
            i = i0 + t
            hors = np.setdiff1d(Vproj[i], Vorig[i], assume_unique=True)
            for j in hors:
                r = int((d[t] < d[t, j]).sum()) + 1
                s += r - K
    return s


def fidelite(X, nX, Vx, Y):
    n = X.shape[0]
    Vy, nY = voisins_et_rangs(Y)
    z = 2.0 / (n * K * (2 * n - 3 * K - 1))
    T = 1.0 - z * penalite(X, nX, Vy, Vx)
    C = 1.0 - z * penalite(Y, nY, Vx, Vy)
    gardes = float(np.mean([len(np.intersect1d(Vx[i], Vy[i])) / K for i in range(n)]))
    return T, C, Vy, gardes


def spearman_paires(X, Y, rng, m=2_000_000):
    n = X.shape[0]
    i = rng.integers(0, n, size=m)
    j = rng.integers(0, n, size=m)
    ok = i != j
    i, j = i[ok], j[ok]
    dx = np.empty(i.size); dy = np.empty(i.size)
    for a in range(0, i.size, 4_000):
        b = min(i.size, a + 4_000)
        dx[a:b] = np.sqrt(((X[i[a:b]] - X[j[a:b]]) ** 2).sum(axis=1))
        dy[a:b] = np.sqrt(((Y[i[a:b]] - Y[j[a:b]]) ** 2).sum(axis=1))
    rx = np.empty(i.size); rx[np.argsort(dx, kind="stable")] = np.arange(i.size)
    ry = np.empty(i.size); ry[np.argsort(dy, kind="stable")] = np.arange(i.size)
    return float(np.corrcoef(rx, ry)[0, 1]), int(i.size)


def accord(V, premier):
    return float((premier[V] == premier[:, None]).mean())


def main():
    rng = np.random.default_rng(GRAINE_JUGE)
    out = {"outil": "outils/genome/tome3/juge-latents/juge_etats.py", "graine_juge": GRAINE_JUGE}
    h, experts, poids = jc.captures("calib", COUCHE)
    X = np.asarray(h, dtype=np.float64)
    n = X.shape[0]
    out["etats"] = n
    out["d_modele"] = X.shape[1]
    # le routeur relu
    g = jc.Gguf()
    Wr = g.f32(f"blk.{COUCHE}.ffn_gate_inp.weight")          # (32, 2880)
    br = g.f32(f"blk.{COUCHE}.ffn_gate_inp.bias")            # (32,)
    out["routeur_formes"] = [list(Wr.shape), list(br.shape)]
    z = X @ Wr.T + br
    zs = -np.sort(-z, axis=1)
    ordre = np.argsort(-z, axis=1, kind="stable")
    premier = ordre[:, 0]
    top4 = np.sort(ordre[:, :4], axis=1)
    out["W0_ensembles_egaux"] = int((top4 == np.sort(experts, axis=1)).all(axis=1).sum())
    out["W0_premiers_egaux_journal_col0"] = int((premier == experts[:, 0]).sum())
    z0 = X @ Wr.T
    t40 = np.sort(np.argsort(-z0, axis=1, kind="stable")[:, :4], axis=1)
    out["W0_cassure_sans_biais"] = int((t40 == np.sort(experts, axis=1)).all(axis=1).sum())
    # poids du journal contre le softmax des logits des quatre experts du journal, dans son ordre
    zj = np.take_along_axis(z, experts, axis=1)
    pj = np.exp(zj - zj.max(axis=1, keepdims=True)); pj /= pj.sum(axis=1, keepdims=True)
    out["W0_ecart_poids_max"] = float(np.abs(pj - poids).max())
    out["journal_col0_est_le_plus_grand_logit"] = int((zj.argmax(axis=1) == 0).sum())
    m45 = zs[:, 3] - zs[:, 4]
    m12 = zs[:, 0] - zs[:, 1]
    qs = [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]
    out["marge45_quantiles"] = dict(zip(map(str, qs), np.quantile(m45, qs).tolist()))
    out["marge12_quantiles"] = dict(zip(map(str, qs), np.quantile(m12, qs).tolist()))
    cnt = np.bincount(premier, minlength=32)
    rangs = np.argsort(-cnt, kind="stable")
    out["comptes_premier"] = cnt.tolist()
    out["huit_premiers"] = [[int(e), int(cnt[e]), 100 * cnt[e] / n] for e in rangs[:8]]
    out["huit_part_pct"] = 100 * cnt[rangs[:8]].sum() / n
    out["premiers_distincts"] = int((cnt > 0).sum())
    out["neuvieme_dixieme"] = [[int(e), int(cnt[e])] for e in rangs[8:10]]
    out["hasard_paires_distinctes"] = float((cnt * (cnt - 1)).sum() / (n * (n - 1)))
    out["hasard_somme_p2"] = float(((cnt / n) ** 2).sum())
    # le CSV commité contre la source
    lot = jc.lire_csv(os.path.join(LAT, "etats-c23.csv"))
    pos = np.array([int(r["position"]) for r in lot])
    out["csv_positions_dans_l_ordre"] = bool(np.array_equal(pos, np.arange(n)))
    pr = np.array([int(r["premier"]) for r in lot])
    e4 = np.array([[int(r[f"e{k}"]) for k in range(1, 5)] for r in lot])
    out["csv_premier_egal"] = int((pr == premier).sum())
    out["csv_e1_e4_egaux_ordre_des_logits"] = int((e4 == ordre[:, :4]).all(axis=1).sum())
    mc = np.array([float(r["marge45"]) for r in lot])
    out["csv_marge45_ecart_rel_max"] = float(np.max(np.abs(mc - m45) / np.maximum(m45, 1e-30)))
    A = np.array([[float(r["acp1"]), float(r["acp2"])] for r in lot])
    Ts = np.array([[float(r["tsne1"]), float(r["tsne2"])] for r in lot])
    # ACP
    mu = X.mean(axis=0)
    Xc = X - mu
    Cov = Xc.T @ Xc / n
    ev, U = np.linalg.eigh(Cov)
    ev, U = ev[::-1], U[:, ::-1]
    out["acp_parts_pct"] = (100 * ev[:3] / ev.sum()).tolist()
    out["acp_plan_pct"] = float(100 * ev[:2].sum() / ev.sum())
    P = Xc @ U[:, :2]
    sg = np.sign((P * A).sum(axis=0))
    out["acp_signes_lot_contre_juge"] = sg.tolist()
    out["acp_coordonnees_ecart_max"] = float(np.max(np.abs(P * sg - A)))
    del Cov
    # voisins d'origine (sur X brut : les distances ne changent pas au centrage)
    Vx, nX = voisins_et_rangs(Xc)
    out["accord_origine_pct"] = 100 * accord(Vx, premier)
    for nom, Y in (("acp", A), ("tsne", Ts)):
        T, C, Vy, gardes = fidelite(Xc, nX, Vx, Y)
        rho, m = spearman_paires(Xc, Y, rng)
        out[nom] = {"T": T, "C": C, "voisins_gardes_pct": 100 * gardes, "spearman": rho, "paires": m,
                    "accord_plan_pct": 100 * accord(Vy, premier)}
        print(nom, out[nom], file=sys.stderr, flush=True)
    # W1 : ACP complète (rotation) et plan permuté
    perm = rng.permutation(n)
    Tp, Cp, _, _ = fidelite(Xc, nX, Vx, A[perm])
    out["W1_cassure_plan_permute"] = {"T": Tp, "C": Cp}
    # les données de la figure (memoire/figures/tome3/donnees) contre le CSV de mesure
    q10, q50 = np.quantile(m45, 0.1), np.quantile(m45, 0.5)
    groupe = {int(e): f"g{k + 1}" for k, e in enumerate(rangs[:8])}
    fig = {}
    for nom, Y in (("acp", A), ("tsne", Ts)):
        rows = jc.lire_csv(os.path.join(DON, f"latents-etats-{nom}.csv"))
        cle = {(round(float(r["x"]), 6), round(float(r["y"]), 6)): r for r in rows}
        mauvais = 0
        for i in range(n):
            r = cle.get((round(Y[i, 0], 6), round(Y[i, 1], 6)))
            if r is None:
                mauvais += 1
                continue
            gr = groupe.get(int(premier[i]), "autres")
            ta = 1.55 if m45[i] < q10 else (0.85 if m45[i] < q50 else 0.42)
            if r["groupe"] != gr or abs(float(r["taille"]) - ta) > 1e-9:
                mauvais += 1
        tailles = [float(r["taille"]) for r in rows]
        croissant = all(tailles[k] <= tailles[k + 1] for k in range(len(tailles) - 1))
        fig[nom] = {"lignes": len(rows), "etats_mal_places": mauvais, "gros_dessines_en_dernier": croissant,
                    "classes": {t: tailles.count(t) for t in sorted(set(tailles))}}
    out["donnees_figure"] = fig
    # points tirés au hasard : un par série (8 groupes et « autres »), contrôlés à la source
    ctl = []
    for gname in [f"g{k}" for k in range(1, 9)] + ["autres"]:
        idx = np.nonzero(np.array([groupe.get(int(e), "autres") for e in premier]) == gname)[0]
        i = int(rng.choice(idx))
        ctl.append({"serie": gname, "position": i, "premier_source": int(premier[i]),
                    "top4_source": ordre[i, :4].tolist(), "journal": experts[i].tolist(),
                    "marge45_source": float(m45[i]), "marge45_csv": float(mc[i]),
                    "acp_source": (P[i] * sg).tolist(), "acp_csv": A[i].tolist()})
    out["points_tires"] = ctl
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
