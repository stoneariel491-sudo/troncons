"""E-K : mémoire épisodique clairsemée (la mouche), cosinus exact. Seuil : seuil-declare.md (E-K).
Usage : python -I memoire_episodique.py DOSSIER_TRACES
"""
import importlib.util
import json
import statistics
import sys
from pathlib import Path

import numpy as np

ici = Path(__file__).resolve().parent


def charger_module(nom, fichier):
    spec = importlib.util.spec_from_file_location(nom, ici / fichier)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


bt = charger_module("bt", "bancs_traces.py")
ps = charger_module("ps", "predicteur_synergies.py")
bt.sous_la_normale()
dossier = sys.argv[1]
KV = 8


def p1_decroissance(X, hl):
    dec = 0.5 ** (1 / hl)
    out = np.zeros_like(X)
    acc = np.zeros(X.shape[1])
    for t in range(X.shape[0]):
        acc = acc * dec + X[t]
        out[t] = acc
    return out


def scores_knn(X, k, rng, successeurs_au_hasard=False):
    """Score pour le jeton t + 1, calculé à la fin du jeton t, en ne regardant que j <= t - 1 (successeur j + 1 <= t)."""
    T = X.shape[0]
    S = X @ X.T                                      # produit scalaire : les lignes ont toutes la même norme (4 × L uns)
    out = np.zeros_like(X)
    for t in range(1, T):
        row = S[t, :t]                                # j = 0 .. t-1
        kk = min(k, t)
        idx = np.argpartition(-row, kk - 1)[:kk]
        w = row[idx]
        suc = idx + 1
        if successeurs_au_hasard:
            suc = rng.integers(1, t + 1, size=kk)
        out[t] = w @ X[suc]
    return out


def main():
    rng = np.random.default_rng(20261027)
    res = {}
    for modele in ("20b", "120b"):
        jeu = {g: bt.charger(dossier, modele, g)[0] for g in bt.GENRES}
        E = bt.charger(dossier, modele, bt.GENRES[0])[2]
        L = jeu[bt.GENRES[0]].shape[1]
        X = {g: bt.matrice_indicateurs(jeu[g], E).astype(np.float32) for g in bt.GENRES}
        res[modele] = {}
        for g in bt.GENRES:
            autres = [x for x in bt.GENRES if x != g]
            Xt = X[g]
            A, Ysuiv = Xt[:-1], Xt[1:]
            p1 = p1_decroissance(Xt.astype(np.float64), 64)[:-1]
            N, n = ps.comptes_association([jeu[x] for x in autres], E, L)
            p3 = ps.p3_scores(Xt.astype(np.float64), N, n, E, L, jeu[g])[:-1]
            knn = scores_knn(Xt, KV, rng)[:-1]
            knn1 = scores_knn(Xt, 1, rng)[:-1]
            knn_h = scores_knn(Xt, KV, rng, successeurs_au_hasard=True)[:-1]
            knnm = ps.rang_par_couche(knn, p1, L=L, E=E)
            res[modele][g] = {}
            for C in bt.BUDGETS[modele]:
                r = {nom: ps.rappel_depuis_scores(s, Ysuiv.astype(np.float64), L, E, C) for nom, s in
                     (("P1_hl64", p1), ("P3", p3), ("KNN", knn), ("KNNm", knnm), ("KNN_k1", knn1), ("KNN_succ_hasard", knn_h))}
                res[modele][g][str(C)] = r
                print(modele, g, C, {k: round(float(v), 4) for k, v in r.items()}, flush=True)
    verdict = {}
    for modele in res:
        ok = True
        det = {}
        for C in bt.BUDGETS[modele]:
            diff, diff_h = [], []
            for g in bt.GENRES:
                r = res[modele][g][str(C)]
                base = max(r["P1_hl64"], r["P3"])
                diff.append(max(r["KNN"], r["KNNm"]) - base)
                diff_h.append(r["KNN_succ_hasard"] - base)
            med = statistics.median(diff)
            pos = sum(1 for x in diff if x > 0)
            det[str(C)] = {"diff_par_genre": diff, "mediane": med, "positifs": pos, "diff_succ_hasard": diff_h,
                           "passe": med >= 0.05 and pos >= 4}
            ok &= det[str(C)]["passe"]
        verdict[modele] = {"detail": det, "passe": ok}
    bt.ecrire("ek-brut.json", res)
    bt.ecrire("ek-verdict.json", verdict)
    print(json.dumps({m: x["passe"] for m, x in verdict.items()}))


if __name__ == "__main__":
    main()
