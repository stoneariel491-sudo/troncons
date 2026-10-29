"""P5 : reglage du PT sur les instances ou la premiere passe (200 balayages, 8 temperatures, 0,03 a 1,5)
n'a pas retrouve l'optimum de la force brute. Les echecs de la premiere passe restent ecrits (W1a: faux)."""
import json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p5lib as P
import temoins as T
from concurrent.futures import ThreadPoolExecutor

res = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "temoins-instances.json")))
echecs = [r["i"] for r in res if not r["pt_ok"]]

def essai(args):
    i, nsw, nt, lo, hi = args
    rng = np.random.default_rng(1000 + i)
    H, w = T.instance(rng)
    lev = np.tile(T.NIV, (T.N, 1))
    qb = P.babai_generique(H, w, lev, np.zeros((T.N, T.K)))
    temps = T.temperatures(H, nt, lo, hi)
    qp, st = T.pt_toy(H, w, qb, temps, nsw)
    ep = float(P.energie(H, w, np.ones(T.N), T.NIV, np.zeros(T.K), 0.0, qp)[0])
    eopt = res[i]["eopt"]
    return ep <= eopt * (1 + 1e-9) + 1e-12

sortie = []
for (nsw, nt, lo, hi) in ((1000, 8, 0.03, 1.5), (1000, 12, 0.01, 3.0), (3000, 12, 0.01, 3.0), (3000, 16, 0.005, 6.0)):
    t0 = time.time()
    with ThreadPoolExecutor(2) as ex:
        ok = list(ex.map(essai, [(i, nsw, nt, lo, hi) for i in echecs]))
    sortie.append(dict(balayages=nsw, temperatures=nt, tmin=lo, tmax=hi, retrouve=int(sum(ok)), sur=len(echecs),
                       duree_s=time.time() - t0, encore_en_echec=[i for i, o in zip(echecs, ok) if not o]))
    print(json.dumps(sortie[-1], ensure_ascii=False), flush=True)
