"""E2 : tri par poids de mélange (triage) des défauts de cache. Proxy de masse, pas de qualité.

Seuils et témoins déclarés avant la lecture : mesures/mimetisme/humain/00-seuils-declares.md.

Usage : python -I -X utf8 e2_triage.py <dossier_traces> <prefixe> <budget> <sortie.json> [--melange]
"""
import glob
import heapq
import importlib.util
import json
import math
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


def lire_poids(chemin):
    out = []
    for ligne in open(chemin, encoding="utf-8"):
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or ligne.startswith("E="):
            continue
        out.append([[float(x) for x in c.split()] for c in ligne.split("|")])
    return out


def lfu_defauts(groupes, N, par_jeton, demi_vie=8.0):
    """Même LFU que gl.g_lfu (logique reprise de notre propre outil), qui rend en plus le drapeau
    succès/défaut de chaque accès, dans l'ordre des groupes."""
    ld = math.log(0.5) / demi_vie
    cle, vu = {}, {}
    cache, tas, drap = set(), [], []
    for i, g in enumerate(groupes):
        t = i // par_jeton
        for x in g:
            ancien = cle.get(x)
            v = 1.0 if ancien is None else math.exp(ancien + t * ld) + 1.0
            cle[x] = math.log(v) - t * ld
            vu[x] = i
            if x in cache:
                drap.append(True)
            else:
                drap.append(False)
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
    return np.array(drap)


def main():
    dossier, prefixe, budget, sortie = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]
    melange = "--melange" in sys.argv
    jetons, poids = [], []
    for f in sorted(glob.glob(os.path.join(dossier, f"{prefixe}.*.lecture.trace"))):
        j, E = cl.lire_trace(f)
        w = lire_poids(f[:-len(".trace")] + ".poids")
        assert len(j) == len(w), f
        jetons += j
        poids += w
    L, k = len(jetons[0]), len(jetons[0][0])
    # témoin : chaque ligne de poids somme à 1 (4 décimales)
    sommes = np.array([[sum(c) for c in t] for t in poids])
    temoin_somme = float(np.abs(sommes - 1).max())
    W = np.array(poids)  # T, L, k
    if melange:  # cassure : les poids sont mélangés entre accès, sans toucher aux experts
        rng = np.random.default_rng(20261026)
        flat = W.reshape(-1)
        rng.shuffle(flat)
        W = flat.reshape(W.shape)
    gs = gl.flux(jetons, E)
    N = max(k, round(budget * L * E))
    succes = lfu_defauts(gs, N, L).reshape(len(jetons), L, k)
    taux_ref = gl.g_lfu(gs, N, L)
    w = W
    wm, ws = w[~succes], w[succes]
    res = {"prefixe": prefixe, "budget": budget, "N": N, "melange": melange,
           "temoin_somme_max_ecart": temoin_somme,
           "temoin_taux_lfu": {"mien": float(succes.mean()), "gl.g_lfu": taux_ref,
                               "ecart": abs(float(succes.mean()) - taux_ref)},
           "defauts": int((~succes).sum()), "acces": int(succes.size),
           "poids_median_defauts": float(np.median(wm)), "poids_median_succes": float(np.median(ws)),
           "rapport_medianes": float(np.median(wm) / np.median(ws)),
           "poids_moyen_defauts": float(wm.mean()), "poids_moyen_succes": float(ws.mean())}
    # rang dans le groupe (l'ordre de la trace suit le plus grand poids en premier ? vérifié ci-dessous)
    ordre_decroissant = float((np.diff(W, axis=2) <= 1e-9).all()) if not melange else None
    res["poids_decroissants_dans_la_ligne"] = ordre_decroissant
    res["part_defauts_par_rang"] = [float((~succes[:, :, r]).sum() / (~succes).sum()) for r in range(k)]
    res["taux_defaut_par_rang"] = [float((~succes[:, :, r]).mean()) for r in range(k)]
    courbe = []
    T = len(jetons)
    for th in (0.01, 0.02, 0.03, 0.05, 0.07, 0.1, 0.15, 0.2, 0.3):
        evit = (~succes) & (w < th)
        n_ev = int(evit.sum())
        masse = float(w[evit].sum()) / (T * L)
        hasard = float(wm.mean()) * n_ev / (T * L)
        courbe.append({"theta": th, "part_defauts_evites": n_ev / int((~succes).sum()),
                       "masse_perdue_par_jeton_couche": masse, "masse_si_hasard": hasard,
                       "gain_vitesse_plafond": 1.0 / (1.0 - n_ev / int((~succes).sum())) - 1.0})
    res["courbe"] = courbe
    # critère déclaré : à masse <= 0,03, part des défauts évités ; interpolation prudente (dernier theta qui tient)
    tenus = [c for c in courbe if c["masse_perdue_par_jeton_couche"] <= 0.03]
    res["meilleur_theta_a_masse_0_03"] = tenus[-1] if tenus else None
    json.dump(res, open(sortie, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in res.items() if k != "courbe"}, indent=1, ensure_ascii=False))
    for c in courbe:
        print({a: round(b, 4) for a, b in c.items()})


if __name__ == "__main__":
    main()
