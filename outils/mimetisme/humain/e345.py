"""E3 (allocation marginale par couche), E4 (précédent inter-couches), E5 (classes ABC).
Seuils et témoins déclarés avant l'écriture de cet outil : mesures/mimetisme/humain/00-seuils-declares.md (amendement).

Usage :
  python -I -X utf8 e345.py e3 <dossier_traces> <prefixe> <sortie.json> [--cassure]
  python -I -X utf8 e345.py e4 <dossier_traces> <prefixe> <sortie.json>
  python -I -X utf8 e345.py e5 <dossier_traces> <prefixe> <sortie.json>
"""
import glob
import importlib.util
import json
import os
import sys

import numpy as np

RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUTILS = os.path.join(RACINE, "outils")
sys.path.insert(0, OUTILS)
import chargement_localite as cl  # noqa: E402

spec = importlib.util.spec_from_file_location("gptoss_localite", os.path.join(OUTILS, "gptoss_localite.py"))
gl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gl)


def charger(dossier, prefixe):
    genres = {}
    for f in sorted(glob.glob(os.path.join(dossier, f"{prefixe}.*.lecture.trace"))):
        nom = os.path.basename(f)[len(prefixe) + 1:].split(".")[0]
        j, E = cl.lire_trace(f)
        genres[nom] = j
    return genres, E


def lru_couche(seq, C):
    """Succès (compte) de cache_lru du dépôt, sur une séquence d'ensembles."""
    return cl.cache_lru(seq, C) * sum(len(s) for s in seq)


def courbes(jetons, L, E, grille):
    """hits[l][i] = succès de LRU par couche à la capacité grille[i] ; accès par couche."""
    hits = np.zeros((L, len(grille)))
    for l in range(L):
        seq = [t[l] for t in jetons]
        for i, C in enumerate(grille):
            hits[l, i] = lru_couche(seq, C)
    return hits


def enveloppe_concave(xs, ys):
    pts = []
    for x, y in zip(xs, ys):
        pts.append((x, y))
        while len(pts) >= 3:
            (x1, y1), (x2, y2), (x3, y3) = pts[-3:]
            if (y2 - y1) * (x3 - x2) <= (y3 - y2) * (x2 - x1):  # pente croissante : le point central est sous la corde
                pts.pop(-2)
            else:
                break
    return pts


def allouer(hits, grille, N, k):
    """Gloutonne par pente décroissante des segments de l'enveloppe concave de chaque couche (plancher k)."""
    L = hits.shape[0]
    segs = []
    base = np.full(L, k)
    for l in range(L):
        xs = [c for c in grille if c >= k]
        ys = [hits[l, grille.index(c)] for c in xs]
        h = enveloppe_concave(xs, ys)
        for (x1, y1), (x2, y2) in zip(h[:-1], h[1:]):
            segs.append(((y2 - y1) / (x2 - x1), l, x1, x2))
    segs.sort(key=lambda s: -s[0])
    alloc = base.copy()
    reste = N - alloc.sum()
    for pente, l, x1, x2 in segs:
        if reste <= 0:
            break
        pas = min(x2 - x1, reste)
        alloc[l] += pas
        reste -= pas
    return alloc


def e3(dossier, prefixe, sortie, cassure):
    genres, E = charger(dossier, prefixe)
    noms = sorted(genres)
    L, k = len(genres[noms[0]][0]), len(genres[noms[0]][0][0])
    grille = list(range(k, min(E, 36) + 1, 1)) if E <= 32 else list(range(k, 88, 4))
    res = {"prefixe": prefixe, "grille": grille, "cassure": cassure, "decoupes": {}}
    # témoin : lru_couche = cache_lru
    seq0 = [t[0] for t in genres[noms[0]]]
    res["temoin_lru"] = {"mien": lru_couche(seq0, 8) / sum(len(s) for s in seq0), "depot": cl.cache_lru(seq0, 8)}
    for test in noms:
        train = [t for n in noms if n != test for t in genres[n]]
        appris = genres[test] if cassure else train
        hits = courbes(appris, L, E, grille)
        res["decoupes"][test] = {}
        tj = genres[test]
        gs = gl.flux(tj, E)
        for f in (0.10, 0.15, 0.20):
            N = max(k * L, round(f * L * E))
            alloc = allouer(hits, grille, N, k)
            tot = sum(len(t[l]) for t in tj for l in range(L))
            h_alloc = sum(lru_couche([t[l] for t in tj], int(alloc[l])) for l in range(L)) / tot
            u = [N // L + (1 if i < N % L else 0) for i in range(L)]
            h_unif = sum(lru_couche([t[l] for t in tj], u[l]) for l in range(L)) / tot
            h_lfu = gl.g_lfu(gs, N, L)
            res["decoupes"][test][f"{f:.2f}"] = {"N": N, "alloc_min": int(alloc.min()), "alloc_max": int(alloc.max()),
                                                 "somme": int(alloc.sum()), "alloc_lru": h_alloc,
                                                 "uniforme_lru": h_unif, "lfu_global": h_lfu}
            print(prefixe, test, f, res["decoupes"][test][f"{f:.2f}"], flush=True)
    moy = {}
    for f in ("0.10", "0.15", "0.20"):
        v = [res["decoupes"][t][f] for t in noms]
        moy[f] = {x: float(np.mean([a[x] for a in v])) for x in ("alloc_lru", "uniforme_lru", "lfu_global")}
        moy[f]["gain_contre_meilleur"] = moy[f]["alloc_lru"] - max(moy[f]["uniforme_lru"], moy[f]["lfu_global"])
    res["moyenne"] = moy
    json.dump(res, open(sortie, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps(moy, indent=1))


def multihot(jetons, L, E):
    M = np.zeros((L, len(jetons), E), dtype=np.float32)
    for t, tok in enumerate(jetons):
        for l in range(L):
            M[l, t, tok[l]] = 1.0
    return M


def e4(dossier, prefixe, sortie):
    genres, E = charger(dossier, prefixe)
    noms = sorted(genres)
    L, k = len(genres[noms[0]][0]), len(genres[noms[0]][0][0])
    l0s = (3, 8, 14) if L == 24 else (4, 12, 22)
    ds = (1, 2, 4)
    K = 20
    rng = np.random.default_rng(20261026)
    res = {"prefixe": prefixe, "K": K, "l0": l0s, "d": ds, "regimes": {}}

    def predire(Mtest, Mtrain, l0, d, aleatoire=False, causal=False):
        # similarité cumulée sur les couches 0..l0
        A = np.concatenate([Mtest[l] for l in range(l0 + 1)], axis=1)
        B = np.concatenate([Mtrain[l] for l in range(l0 + 1)], axis=1)
        S = A @ B.T
        T = S.shape[0]
        if causal:  # jeton t ne voit que j <= t-2
            idx = np.arange(S.shape[1])[None, :]
            S = np.where(idx <= (np.arange(T)[:, None] - 2), S, -1.0)
        if aleatoire:
            S = rng.random(S.shape)
            if causal:
                idx = np.arange(S.shape[1])[None, :]
                S = np.where(idx <= (np.arange(T)[:, None] - 2), S, -1.0)
        nvois = min(K, S.shape[1])
        top = np.argpartition(-S, nvois - 1, axis=1)[:, :nvois]
        w = np.take_along_axis(S, top, axis=1)
        w = np.maximum(w, 0.0) + (1e-6 if aleatoire else 0.0) * 0 + 1e-9
        votes = np.zeros((T, E), dtype=np.float64)
        Y = Mtrain[l0 + d]
        for j in range(nvois):
            votes += w[:, j:j + 1] * Y[top[:, j]]
        pred = np.argsort(-votes, axis=1)[:, :k]
        return pred

    def rappel(pred, vrai_M):
        T = pred.shape[0]
        return float(np.mean([vrai_M[t, pred[t]].sum() / k for t in range(T)]))

    for regime in ("autre_genre", "en_ligne"):
        res["regimes"][regime] = {}
        for test in noms:
            Mt = multihot(genres[test], L, E)
            if regime == "autre_genre":
                train_tok = [t for n in noms if n != test for t in genres[n]]
                Mtr = multihot(train_tok, L, E)
            else:
                Mtr = Mt
            for l0 in l0s:
                for d in ds:
                    causal = regime == "en_ligne"
                    p = predire(Mt, Mtr, l0, d, causal=causal)
                    pr = predire(Mt, Mtr, l0, d, aleatoire=True, causal=causal)
                    if causal:
                        sel = slice(300, None)  # jetons ayant déjà 300 antécédents
                    else:
                        sel = slice(0, None)
                    vrai = Mt[l0 + d]
                    # b1 : les k plus populaires de la couche dans l'apprentissage (en ligne : dans les jetons antérieurs, ici toute la séquence d'apprentissage = le texte lui-même, borne haute)
                    pop = np.argsort(-Mtr[l0 + d].sum(axis=0))[:k]
                    b1 = float(vrai[sel][:, pop].sum(axis=1).mean() / k)
                    # b2 : ensemble du jeton précédent
                    b2 = float((vrai[1:] * vrai[:-1]).sum(axis=1)[sel.start - 1 if sel.start else 0:].mean() / k) if True else 0
                    r = rappel(p[sel], vrai[sel])
                    rr = rappel(pr[sel], vrai[sel])
                    res["regimes"][regime].setdefault(test, {})[f"l0={l0},d={d}"] = {"knn": r, "voisins_hasard": rr, "b1_populaires": b1, "b2_precedent": b2}
            print(prefixe, regime, test, flush=True)
    # synthèse : moyenne sur genres et l0, par d
    syn = {}
    for regime in res["regimes"]:
        for d in ds:
            v = [res["regimes"][regime][g][f"l0={l0},d={d}"] for g in noms for l0 in l0s]
            syn[f"{regime},d={d}"] = {x: float(np.mean([a[x] for a in v])) for x in ("knn", "voisins_hasard", "b1_populaires", "b2_precedent")}
            syn[f"{regime},d={d}"]["marge_sur_meilleure_base"] = syn[f"{regime},d={d}"]["knn"] - max(syn[f"{regime},d={d}"]["b1_populaires"], syn[f"{regime},d={d}"]["b2_precedent"])
    res["synthese"] = syn
    json.dump(res, open(sortie, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps(syn, indent=1))


def rangs(v):
    v = np.asarray(v, dtype=float)
    o = np.argsort(v, kind="mergesort")
    r = np.empty(len(v))
    r[o] = np.arange(len(v))
    for val in np.unique(v):  # rangs moyens pour les égalités
        m = v == val
        if m.sum() > 1:
            r[m] = r[m].mean()
    return r


def spearman(a, b):
    ra, rb = rangs(a), rangs(b)
    if ra.std() == 0 or rb.std() == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def e5(dossier, prefixe, sortie):
    genres, E = charger(dossier, prefixe)
    noms = sorted(genres)
    L, k = len(genres[noms[0]][0]), len(genres[noms[0]][0][0])
    freq = {}
    for n in noms:
        F = np.zeros((L, E))
        for tok in genres[n]:
            for l in range(L):
                F[l, tok[l]] += 1
        freq[n] = F / len(genres[n])
    tout = sum(freq[n] * len(genres[n]) for n in noms)
    parts = []
    for l in range(L):
        f = np.sort(tout[l])
        parts.append(float(f[: E // 2].sum() / f.sum()))
    rho = []
    for i, a in enumerate(noms):
        for b in noms[i + 1:]:
            for l in range(L):
                rho.append(spearman(freq[a][l], freq[b][l]))
    # témoin : uniforme synthétique
    rng = np.random.default_rng(20261026)
    Fu = [np.bincount(rng.integers(0, E, 3000 * k), minlength=E) for _ in range(2)]
    f = np.sort(Fu[0])
    # cassure : trace mélangée expert par expert (fréquences permutées entre genres)
    rho_casse = []
    for l in range(L):
        a = freq[noms[0]][l]
        b = rng.permutation(freq[noms[1]][l])
        rho_casse.append(spearman(a, b))
    # POST HOC (non déclaré avant) : la moitié rare apprise sur trois genres, sa part d'accès dans le quatrième
    cross = []
    for test in noms:
        autres = [n for n in noms if n != test]
        for l in range(L):
            fa = sum(freq[n][l] * len(genres[n]) for n in autres)
            rare = np.argsort(fa)[: E // 2]
            cross.append(float(freq[test][l][rare].sum() / freq[test][l].sum()))
    res = {"post_hoc_part_test_de_la_moitie_rare_apprise_ailleurs": float(np.mean(cross)),
           "post_hoc_pire_couche_genre": float(max(cross)),
           "prefixe": prefixe, "part_acces_50pct_rares_moyenne": float(np.mean(parts)),
           "part_acces_50pct_rares_min_max": [float(min(parts)), float(max(parts))],
           "spearman_entre_genres_moyen": float(np.nanmean(rho)),
           "temoin_uniforme": {"part_50pct_rares": float(f[: E // 2].sum() / f.sum()),
                               "spearman": float(spearman(Fu[0], Fu[1]))},
           "cassure_spearman_permute": float(np.nanmean(rho_casse))}
    json.dump(res, open(sortie, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "e3":
        e3(sys.argv[2], sys.argv[3], sys.argv[4], "--cassure" in sys.argv)
    elif cmd == "e4":
        e4(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "e5":
        e5(sys.argv[2], sys.argv[3], sys.argv[4])
