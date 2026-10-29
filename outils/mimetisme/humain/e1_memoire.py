"""E1 : politique de cache « mémoire humaine » (Anderson et Schooler 1991, ACT-R) contre LRU, LFU et Belady.

Seuils et témoins déclarés avant la lecture : mesures/mimetisme/humain/00-seuils-declares.md.
Les instruments LRU, LFU (demi-vie 8) et Belady sont ceux du dépôt (outils/gptoss_localite.py), importés
tels quels, non recopiés.

Score ACT-R d'un expert i à l'instant t : B_i(t) = ln sum_j (t - t_j + 1)^(-d), sur ses H derniers usages
(historique gardé aussi hors du cache). Éviction : score le plus bas parmi les résidents hors du groupe courant.

Usage :
  python -I -X utf8 e1_memoire.py temoins  <dossier_traces> <prefixe> <sortie.json>
  python -I -X utf8 e1_memoire.py courbe   <dossier_traces> <prefixe> <ds> <sortie.json> [--genres] [--melange]
"""
import glob
import importlib.util
import json
import os
import random
import sys

import numpy as np

RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUTILS = os.path.join(RACINE, "outils")
sys.path.insert(0, OUTILS)
import chargement_localite as cl  # noqa: E402

spec = importlib.util.spec_from_file_location("gptoss_localite", os.path.join(OUTILS, "gptoss_localite.py"))
gl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gl)

BUDGETS = [0.10, 0.15, 0.20, 0.30]


def g_actr(groupes, N, n_items, par_jeton, d, H=32, temps="jeton"):
    """Cache global à éviction ACT-R. temps = 'jeton' (t = indice du jeton) ou 'acces' (t = numéro d'accès,
    sert au témoin W2 : H = 1 doit rendre LRU)."""
    ut = np.full((n_items, H), -1.0)
    ptr = np.zeros(n_items, dtype=np.int64)
    inres = np.zeros(n_items, dtype=bool)
    stamp = np.zeros(n_items)
    nres, succes, total, seq = 0, 0, 0, 0
    for i, g in enumerate(groupes):
        t = float(i // par_jeton) if temps == "jeton" else float(i)
        for x in g:
            seq += 1
            total += 1
            if inres[x]:
                succes += 1
            else:
                inres[x] = True
                nres += 1
            ut[x, ptr[x] % H] = t
            ptr[x] += 1
            stamp[x] = seq
        exces = nres - N
        if exces > 0:
            idx = np.flatnonzero(inres)
            u = ut[idx]
            v = np.where(u >= 0, np.maximum(t + 1.0 - u, 1.0) ** (-d), 0.0)
            sc = np.log(np.maximum(v.sum(axis=1), 1e-300))
            sc[np.isin(idx, g)] = np.inf
            ev = idx[np.lexsort((stamp[idx], sc))[:exces]]  # score le plus bas, départage par ancienneté exacte
            inres[ev] = False
            nres -= len(ev)
    return succes / total


def charger(dossier, prefixe, melange=False):
    genres = {}
    for f in sorted(glob.glob(os.path.join(dossier, f"{prefixe}.*.lecture.trace"))):
        nom = os.path.basename(f)[len(prefixe) + 1:].split(".")[0]
        j, E = cl.lire_trace(f)
        genres[nom] = j
    tous = [t for n in sorted(genres) for t in genres[n]]
    if melange:
        rng = random.Random(20261026)
        tous = list(tous)
        rng.shuffle(tous)
        for n in genres:
            genres[n] = list(genres[n])
            rng.shuffle(genres[n])
    return genres, tous, E


def taux(jetons, E, f, d=None, lfu=True, lru=True, belady=True):
    L, k = len(jetons[0]), len(jetons[0][0])
    gs = gl.flux(jetons, E)
    N = max(k, round(f * L * E))
    r = {"N": N}
    if lru:
        r["lru"] = gl.g_lru(gs, N)
    if lfu:
        r["lfu"] = gl.g_lfu(gs, N, L)
    if belady:
        r["belady"] = gl.g_belady(gs, N)
    if d is not None:
        for dd in d:
            r[f"actr_{dd}"] = g_actr(gs, N, L * E, L, dd)
    return r


def temoins(dossier, prefixe, sortie):
    out = {}
    genres, tous, E = charger(dossier, prefixe)
    # W1 : LRU/LFU/Belady de mon pipeline contre le CSV publié (20b seulement)
    pub = {}
    csvp = os.path.join(RACINE, "mesures", "localite-gpt-oss", "figures", f"succes-gpt-oss-{prefixe[1:]}-lecture.csv")
    if os.path.exists(csvp):
        for lg in open(csvp, encoding="utf-8").read().strip().splitlines()[1:]:
            c = lg.split(",")
            pub[int(c[0])] = {"lru": float(c[1]), "lfu": float(c[2]), "belady": float(c[5])}
    w1 = {}
    for b in (10, 20):
        if b in pub:
            m = taux(tous, E, b / 100)
            w1[b] = {x: {"mien": m[x], "publie": pub[b][x], "ecart": abs(m[x] - pub[b][x])} for x in ("lru", "lfu", "belady")}
    out["W1"] = w1
    out["W1_tient"] = bool(w1) and all(v["ecart"] < 1e-5 for b in w1.values() for v in b.values())
    # W1 cassure : demi-vie 9
    L, k = len(tous[0]), len(tous[0][0])
    gs = gl.flux(tous, E)
    N = max(k, round(0.10 * L * E))
    lfu9 = gl.g_lfu(gs, N, L, demi_vie=9.0)
    out["W1_cassure_lfu_hl9"] = {"lfu9": lfu9, "ecart_au_publie": abs(lfu9 - pub.get(10, {}).get("lfu", float('nan')))}
    out["W1_cassure_tombe"] = out["W1_cassure_lfu_hl9"]["ecart_au_publie"] > 1e-5
    # W2 : ACT-R H = 1, temps = numéro d'accès = LRU
    w2 = {}
    for f in (0.15, 0.30):
        N = max(k, round(f * L * E))
        a = g_actr(gs, N, L * E, L, 0.5, H=1, temps="acces")
        b = gl.g_lru(gs, N)
        w2[f] = {"actr_h1": a, "lru": b, "ecart": abs(a - b)}
    out["W2"] = w2
    out["W2_tient"] = all(v["ecart"] < 1e-9 for v in w2.values())
    json.dump(out, open(sortie, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps(out, indent=1, ensure_ascii=False))


def courbe(dossier, prefixe, ds, sortie, par_genre, melange):
    genres, tous, E = charger(dossier, prefixe, melange)
    res = {"prefixe": prefixe, "melange": melange, "ds": ds, "pooled": {}}
    for f in BUDGETS:
        res["pooled"][f"{f:.2f}"] = taux(tous, E, f, d=ds)
        print(prefixe, "pooled", f, res["pooled"][f"{f:.2f}"], flush=True)
    if par_genre:
        res["genres"] = {}
        for n, j in genres.items():
            res["genres"][n] = {}
            for f in (0.15, 0.20):
                res["genres"][n][f"{f:.2f}"] = taux(j, E, f, d=ds, belady=True)
                print(prefixe, n, f, res["genres"][n][f"{f:.2f}"], flush=True)
    json.dump(res, open(sortie, "w", encoding="utf-8"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "temoins":
        temoins(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        ds = [float(x) for x in sys.argv[4].split(",")]
        courbe(sys.argv[2], sys.argv[3], ds, sys.argv[5], "--genres" in sys.argv, "--melange" in sys.argv)
