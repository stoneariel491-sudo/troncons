"""E-I : un prédicteur de synergies, appris sur d'autres genres, devine-t-il les experts du jeton suivant ?
Seuil et témoins : genome/mimetisme/vivant/seuil-declare.md (ajout E-I).
Usage : python -I predicteur_synergies.py DOSSIER_TRACES
"""
import importlib.util
import json
import statistics
import sys
from pathlib import Path

import numpy as np

ici = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("bt", ici / "bancs_traces.py")
bt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bt)
bt.sous_la_normale()

K_COMP = 64
ALPHA = 1.0
dossier = sys.argv[1]
rng = np.random.default_rng(20261027)


def indicateurs(sets, E):
    return bt.matrice_indicateurs(sets, E).astype(np.float64)


def paires(Xs):
    """Concatène les paires (X_t, X_{t+1}) de chaque séquence, sans traverser les frontières."""
    A = np.vstack([X[:-1] for X in Xs])
    B = np.vstack([X[1:] for X in Xs])
    return A, B


def svd_aleatoire(Ac, k, sur=10, iters=4):
    """Axes principaux par SVD aléatoire (Halko, Martinsson, Tropp 2011), graine fixe."""
    r = np.random.default_rng(7)
    Om = r.standard_normal((Ac.shape[1], k + sur))
    Y = Ac @ Om
    for _ in range(iters):
        Y, _ = np.linalg.qr(Y)
        Y = Ac @ (Ac.T @ Y)
    Q, _ = np.linalg.qr(Y)
    B = Q.T @ Ac
    _, _, Vt = np.linalg.svd(B, full_matrices=False)
    return Vt[:k].T


def apprendre(Xs, k, melange=False):
    A, B = paires(Xs)
    if melange:
        B = B[rng.permutation(len(B))]
    mu = A.mean(axis=0)
    Ac = A - mu
    # ACP par la matrice de Gram des colonnes : A^T A est (D, D), on prend les k premiers vecteurs propres
    V = svd_aleatoire(Ac, k)                      # (D, k) : les k premiers axes principaux
    Z = Ac @ V
    nu = B.mean(axis=0)
    lam = ALPHA * (Z ** 2).sum() / Z.shape[1] * 1e-3
    W = np.linalg.solve(Z.T @ Z + lam * np.eye(k), Z.T @ (B - nu))
    return mu, V, W, nu


def predire(modele_p4, X):
    mu, V, W, nu = modele_p4
    return ((X - mu) @ V) @ W + nu


def rappel_depuis_scores(scores, Ysuiv, L, E, C):
    """scores, Ysuiv : (n, L*E). Rappel@C moyen : part des experts vrais dans les C premiers de chaque couche."""
    tot = 0.0
    n = scores.shape[0]
    for c in range(L):
        s = scores[:, c * E:(c + 1) * E]
        y = Ysuiv[:, c * E:(c + 1) * E]
        top = np.argpartition(-s, C - 1, axis=1)[:, :C]
        dans = np.take_along_axis(y, top, axis=1).sum(axis=1)
        tot += (dans / y.sum(axis=1)).mean()
    return tot / L


def p1_scores(X, E, L):
    """Popularité à décroissance en ligne (demi-vie 8) : score au jeton t = comptes décroissants jusqu'à t inclus."""
    dec = 0.5 ** (1 / 8)
    out = np.zeros_like(X)
    acc = np.zeros(X.shape[1])
    for t in range(X.shape[0]):
        acc = acc * dec + X[t]
        out[t] = acc
    return out


def p3_scores(Xtest, N, n, E, L, sets_test):
    """Association de même couche, comptes hors ligne N[c][e', e], n[c][e'] ; mise à jour en ligne."""
    T = Xtest.shape[0]
    out = np.zeros_like(Xtest)
    N = N.copy()
    n = n.copy()
    for t in range(T):
        for c in range(L):
            a = sets_test[t, c]
            sc = (N[c][a] / (n[c][a][:, None] + 1.0)).sum(axis=0)
            out[t, c * E:(c + 1) * E] = sc
        if t + 1 < T:
            for c in range(L):
                a = sets_test[t, c]
                b = sets_test[t + 1, c]
                N[c][np.ix_(a, b)] += 1.0
                n[c][a] += 1.0
    return out


def comptes_association(sets_list, E, L):
    N = np.zeros((L, E, E))
    n = np.zeros((L, E))
    for sets in sets_list:
        for c in range(L):
            a = sets[:-1, c, :]
            b = sets[1:, c, :]
            for i in range(a.shape[1]):
                for j in range(b.shape[1]):
                    np.add.at(N[c], (a[:, i], b[:, j]), 1.0)
            for i in range(a.shape[1]):
                np.add.at(n[c], a[:, i], 1.0)
    return N, n


def rang_somme(*scores):
    """Somme des rangs par ligne (P4m)."""
    tot = 0
    for s in scores:
        tot = tot + np.argsort(np.argsort(s, axis=1, kind="stable"), axis=1)
    return tot.astype(np.float64)


def rang_par_couche(*scores, L, E):
    out = np.zeros_like(scores[0])
    for c in range(L):
        sl = slice(c * E, (c + 1) * E)
        out[:, sl] = rang_somme(*[s[:, sl] for s in scores])
    return out


def main():
    res = {}
    for modele in ("20b", "120b"):
        jeu = {g: bt.charger(dossier, modele, g)[0] for g in bt.GENRES}
        E = bt.charger(dossier, modele, bt.GENRES[0])[2]
        L = jeu[bt.GENRES[0]].shape[1]
        X = {g: indicateurs(jeu[g], E) for g in bt.GENRES}
        res[modele] = {}
        for g in bt.GENRES:
            autres = [x for x in bt.GENRES if x != g]
            Xtr = [X[x] for x in autres]
            m64 = apprendre(Xtr, K_COMP)
            m1 = apprendre(Xtr, 1)
            mmel = apprendre(Xtr, K_COMP, melange=True)
            Xt = X[g]
            A, Ysuiv = Xt[:-1], Xt[1:]
            s4 = predire(m64, A)
            s4k1 = predire(m1, A)
            s4mel = predire(mmel, A)
            s1 = p1_scores(Xt, E, L)[:-1]
            pop = np.vstack(Xtr).mean(axis=0)
            s0 = np.tile(pop, (A.shape[0], 1))
            N, n = comptes_association([jeu[x] for x in autres], E, L)
            s3 = p3_scores(Xt, N, n, E, L, jeu[g])[:-1]
            s4m = rang_par_couche(s4, s1, L=L, E=E)
            res[modele][g] = {}
            for C in bt.BUDGETS[modele]:
                r = {nom: rappel_depuis_scores(s, Ysuiv, L, E, C) for nom, s in
                     (("P0", s0), ("P1", s1), ("P3", s3), ("P4", s4), ("P4m", s4m), ("P4_K1", s4k1), ("P4_melange", s4mel))}
                r["persistance"] = float(np.mean([len(set(jeu[g][t, c]) & set(jeu[g][t + 1, c])) / 4
                                                  for t in range(0, jeu[g].shape[0] - 1, 5) for c in range(L)]))
                res[modele][g][str(C)] = r
                print(modele, g, C, {k: round(v, 4) for k, v in r.items()}, flush=True)
    verdict = {}
    for modele in res:
        ok = True
        det = {}
        for C in bt.BUDGETS[modele]:
            diff = []
            for g in bt.GENRES:
                r = res[modele][g][str(C)]
                diff.append(max(r["P4"], r["P4m"]) - max(r["P1"], r["P3"]))
            diff_mel = [max(res[modele][g][str(C)]["P4_melange"], 0) - max(res[modele][g][str(C)]["P1"], res[modele][g][str(C)]["P3"]) for g in bt.GENRES]
            med = statistics.median(diff)
            pos = sum(1 for x in diff if x > 0)
            passe = med >= 0.05 and pos >= 4
            det[str(C)] = {"diff_par_genre": diff, "mediane": med, "positifs": pos, "passe": passe,
                           "diff_modele_melange": diff_mel}
            ok &= passe
        verdict[modele] = {"detail": det, "passe": ok}
    bt.ecrire("ei-brut.json", res)
    bt.ecrire("ei-verdict.json", verdict)
    print(json.dumps({m: x["passe"] for m, x in verdict.items()}))


if __name__ == "__main__":
    main()
