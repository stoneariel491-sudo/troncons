"""Éclaireur Terre et cosmos : eau-filling par l'usage (addendum 2 de seuil-declare.md, commité avant).

Gain en bits par poids lu = demi-KL(loi des défauts || loi des accès), à distorsion pondérée par l'usage
égale. Réalisé en validation croisée par genre. Voir l'addendum pour la dérivation et le seuil (0,126 bit).

Usage : python -I -X utf8 eau_usage.py <20b|120b> <dossier_traces> <sortie_dir>
        python -I -X utf8 eau_usage.py temoins <sortie_dir>
"""
import json
import math
import os
import random
import sys
from collections import OrderedDict

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
sys.path.insert(0, os.path.abspath(os.path.join(ICI, "..", "..")))
import cache_terre as ct  # noqa: E402
import gptoss_localite as gl  # noqa: E402

RMIN, RMAX = 1.0, 8.0


def lru_defauts(groupes, N, n_items):
    m = np.zeros(n_items)
    p = np.zeros(n_items)
    cache = OrderedDict()
    for g in groupes:
        for x in g:
            p[x] += 1
            if x in cache:
                cache.move_to_end(x)
            else:
                m[x] += 1
                cache[x] = True
        while len(cache) > N:
            cache.popitem(last=False)
    return m, p


def lfu_defauts(groupes, N, L, n_items, hl=8.0):
    """LFU à compteurs décroissants, mêmes règles que gptoss_localite.g_lfu, avec les défauts par expert."""
    import heapq
    ld = math.log(0.5) / hl
    cle, vu = {}, {}
    cache, tas = set(), []
    m = np.zeros(n_items)
    p = np.zeros(n_items)
    for i, g in enumerate(groupes):
        t = i // L
        for x in g:
            p[x] += 1
            ancien = cle.get(x)
            v = 1.0 if ancien is None else math.exp(ancien + t * ld) + 1.0
            cle[x] = math.log(v) - t * ld
            vu[x] = i
            if x not in cache:
                m[x] += 1
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
    return m, p


def delta_en_echantillon(m, p):
    mh, ph = m / m.sum(), p / p.sum()
    ok = mh > 0
    return 0.5 * float((mh[ok] * np.log2(mh[ok] / ph[ok])).sum())


def forme_allocation(m, p):
    """R_x - R_0 : forme de l'allocation optimale non bornée, lissée de Laplace (+1)."""
    ms, ps = m + 1.0, p + 1.0
    return 0.5 * np.log2((ps / ps.sum()) / (ms / ms.sum()))


def realise(forme, m_test, p_test, R0=3.0):
    """Décale la forme d'un scalaire s pour que sum p'_x 2^(-2 R_x) = sum p'_x 2^(-2 R0), R_x borné [RMIN, RMAX].
    Rend le gain en bits par poids lu : R0 - sum m'_x R_x / sum m'_x."""
    cible = (p_test * 2.0 ** (-2.0 * R0)).sum()

    def D(s):
        R = np.clip(R0 + forme + s, RMIN, RMAX)
        return (p_test * 2.0 ** (-2.0 * R)).sum(), R

    lo, hi = -10.0, 10.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        d, _R = D(mid)
        if d > cible:
            lo = mid  # trop de distorsion : plus de bits
        else:
            hi = mid
    d, R = D(hi)
    return R0 - float((m_test * R).sum() / m_test.sum()), float(R.mean())


def mesure(prefixe, dossier, sortie):
    os.makedirs(sortie, exist_ok=True)
    data = {g: ct.charger(prefixe, dossier, g) for g in ct.GENRES}
    E = data[ct.GENRES[0]][1]
    L = len(data[ct.GENRES[0]][0][0])
    k = len(data[ct.GENRES[0]][0][0][0])
    n_items = L * E
    N = round(0.20 * L * E)
    res = {"modele": prefixe, "N": N}
    pols = ("lru", "lfu8") + (("lfu32",) if os.environ.get("EAU_POST") else ())  # lfu32 : post hoc, hors seuil déclaré
    for pol in pols:
        mp = {}
        for g in ct.GENRES:
            gr = gl.flux(data[g][0], E)
            mp[g] = (lru_defauts(gr, N, n_items) if pol == "lru"
                     else lfu_defauts(gr, N, L, n_items, hl=float(pol[3:])))
        out = {"en_echantillon": {}, "valide": {}}
        for g in ct.GENRES:
            m, p = mp[g]
            out["en_echantillon"][g] = delta_en_echantillon(m, p)
            autres = [x for x in ct.GENRES if x != g]
            ma = sum(mp[x][0] for x in autres)
            pa = sum(mp[x][1] for x in autres)
            forme = forme_allocation(ma, pa)
            gain, rmoy = realise(forme, m, p)
            # cassure : forme permutée au hasard entre experts (casse le lien entre p, m et la forme)
            rng = np.random.default_rng(20261027)
            gains_casse = [realise(rng.permutation(forme), m, p)[0] for _ in range(5)]
            out["valide"][g] = {"gain": gain, "R_moyen": rmoy, "cassure_permutee_moy": float(np.mean(gains_casse))}
        out["moy_en_echantillon"] = float(np.mean(list(out["en_echantillon"].values())))
        out["moy_valide"] = float(np.mean([v["gain"] for v in out["valide"].values()]))
        out["moy_cassure"] = float(np.mean([v["cassure_permutee_moy"] for v in out["valide"].values()]))
        res[pol] = out
        print(prefixe, pol, "en échantillon", round(out["moy_en_echantillon"], 4),
              "validé", round(out["moy_valide"], 4), "cassure", round(out["moy_cassure"], 4), flush=True)
    with open(os.path.join(sortie, f"eau-usage-{prefixe}.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)


def temoins(sortie):
    """Routage i.i.d. uniforme : Delta ~ 0. (La cassure déclarée « Delta tombe » était mal posée : une demi-KL est >= 0 ;
    la cassure retenue est la forme d'allocation permutée entre experts, dans mesure().)"""
    os.makedirs(sortie, exist_ok=True)
    rng = random.Random(20261027)
    L, E, k, T = 24, 32, 4, 4000
    jetons = [[rng.sample(range(E), k) for _ in range(L)] for _ in range(T)]
    gr = gl.flux(jetons, E)
    N = round(0.20 * L * E)
    m, p = lru_defauts(gr, N, L * E)
    d = delta_en_echantillon(m, p)
    out = {"uniforme_iid_delta": d, "tient": abs(d) <= 0.01}
    print(out)
    with open(os.path.join(sortie, "temoins-eau.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    if sys.argv[1] == "temoins":
        temoins(sys.argv[2])
    else:
        mesure("t" + sys.argv[1], sys.argv[2], sys.argv[3])
