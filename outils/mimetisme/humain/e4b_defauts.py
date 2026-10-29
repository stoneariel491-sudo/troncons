"""E4b (POST HOC, non déclaré avant) : le prédicteur « précédent » de E4 (régime en ligne) couvre-t-il les DÉFAUTS de cache ?

Pour chaque genre : un LFU (demi-vie 8) à 20 % tourne sur le flux ; à la couche l0 + d du jeton t, avant ses accès, on
compare l'ensemble prédit P (k experts, voisins de chemin des couches 0..l0, jetons antérieurs <= t - 2) à l'état du cache :
  charges = P \ cache ; utiles = charges ∩ vrais ; défauts = vrais \ cache.
Rendus : couverture = utiles / défauts ; gaspillage = 1 - utiles / charges. Le gain de cache dû aux préchargements
(pollution, évictions) n'est PAS simulé : borne optimiste sur la couverture, borne pessimiste sur le coût.
Témoin : voisins tirés au hasard (même causalité) ; couverture attendue très inférieure.
Usage : python -I -X utf8 e4b_defauts.py <dossier_traces> <prefixe> <budget> <sortie.json>
"""
import heapq
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e345  # noqa: E402

K = 20


def predire(Mt, l0, d, k, E, aleatoire, rng):
    A = np.concatenate([Mt[l] for l in range(l0 + 1)], axis=1)
    S = A @ A.T
    T = S.shape[0]
    idx = np.arange(T)[None, :]
    ok = idx <= (np.arange(T)[:, None] - 2)
    if aleatoire:
        S = rng.random(S.shape)
    S = np.where(ok, S, -1.0)
    top = np.argpartition(-S, min(K, T) - 1, axis=1)[:, :K]
    w = np.take_along_axis(S, top, axis=1)
    valid = w >= 0 if aleatoire else w > 0
    w = np.where(valid, np.maximum(w, 0) + 1e-9, 0.0)
    votes = np.zeros((T, E))
    Y = Mt[l0 + d]
    for j in range(top.shape[1]):
        votes += w[:, j:j + 1] * Y[top[:, j]]
    pred = np.argsort(-votes, axis=1)[:, :k]
    pred[votes.sum(axis=1) == 0] = -1  # aucun antécédent valide : pas de prédiction
    return pred


def simuler(jetons, E, N, preds):
    """LFU hl 8 (logique de gl.g_lfu) ; preds = {(l, ) : (T, k) prédits} pour la couche cible ; rend les compteurs."""
    L, k = len(jetons[0]), len(jetons[0][0])
    ld = math.log(0.5) / 8.0
    cle, vu = {}, {}
    cache, tas = set(), []
    cnt = {l: dict(charges=0, utiles=0, defauts=0) for l in preds}
    gs = [[l * E + e for e in c] for t in jetons for l, c in enumerate(t)]
    for i, g in enumerate(gs):
        t, l = divmod(i, L)
        if l in preds:
            P = {l * E + int(e) for e in preds[l][t]} if preds[l][t][0] >= 0 else set()
            vrais = set(g)
            ch = P - cache
            cnt[l]["charges"] += len(ch)
            cnt[l]["utiles"] += len(ch & vrais)
            cnt[l]["defauts"] += len(vrais - cache)
        for x in g:
            ancien = cle.get(x)
            v = 1.0 if ancien is None else math.exp(ancien + t * ld) + 1.0
            cle[x] = math.log(v) - t * ld
            vu[x] = i
            cache.add(x)
            heapq.heappush(tas, (cle[x], vu[x], x))
        dans_g = set(g)
        mis = []
        while len(cache) > N:
            c, v, x = heapq.heappop(tas)
            if x not in cache or cle[x] != c or vu[x] != v:
                continue
            if x in dans_g:
                mis.append((c, v, x))
                continue
            cache.remove(x)
        for e in mis:
            heapq.heappush(tas, e)
    return cnt


def main():
    dossier, prefixe, budget, sortie = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]
    genres, E = e345.charger(dossier, prefixe)
    L, k = len(genres[sorted(genres)[0]][0]), len(genres[sorted(genres)[0]][0][0])
    l0s = (3, 8, 14) if L == 24 else (4, 12, 22)
    N = max(k, round(budget * L * E))
    rng = np.random.default_rng(20261026)
    res = {"prefixe": prefixe, "budget": budget, "N": N, "genres": {}}
    for nom in sorted(genres):
        j = genres[nom]
        Mt = e345.multihot(j, L, E)
        res["genres"][nom] = {}
        for d in (1, 2, 4):
            for alea in (False, True):
                preds = {l0 + d: predire(Mt, l0, d, k, E, alea, rng) for l0 in l0s}
                # les 300 premiers jetons n'ont pas assez d'antécédents : leurs prédictions sont écartées
                for l in preds:
                    preds[l] = preds[l]
                cnt = simuler(j, E, N, preds)
                ch = sum(c["charges"] for c in cnt.values())
                ut = sum(c["utiles"] for c in cnt.values())
                df = sum(c["defauts"] for c in cnt.values())
                res["genres"][nom][f"d={d},{'hasard' if alea else 'knn'}"] = {
                    "couverture": ut / df, "gaspillage": 1 - ut / ch if ch else None, "charges": ch, "utiles": ut, "defauts": df}
        print(prefixe, nom, flush=True)
    syn = {}
    for key in {k2 for g in res["genres"].values() for k2 in g}:
        v = [res["genres"][g][key] for g in res["genres"]]
        ut, df, ch = sum(a["utiles"] for a in v), sum(a["defauts"] for a in v), sum(a["charges"] for a in v)
        syn[key] = {"couverture": ut / df, "gaspillage": 1 - ut / ch}
    res["synthese"] = dict(sorted(syn.items()))
    json.dump(res, open(sortie, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps(res["synthese"], indent=1))


if __name__ == "__main__":
    main()
