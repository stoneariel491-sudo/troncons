"""E7 (POST HOC, descriptif, sans critère déclaré) : borne haute des défauts qu'un routage conscient du cache pourrait éviter
en échangeant le 4e expert contre le 5e quand leur marge de logit est sous tau (le 5e est supposé résident : borne optimiste).
Données : journal de routage de la référence f64 du juge (20 b, 24 couches), format de mesures/moteur/R/bascules.py :
u32 couches, u32 positions, puis pour chaque couche et chaque position 4 x u8 experts et f32 marge (4e moins 5e logit biaisé).
On suppose les 4 experts rangés par logit décroissant (à vérifier : la part de défauts par rang le montrerait).
Usage : python -I -X utf8 e7_marge.py <routage.bin> <budget> <sortie.json>
"""
import heapq
import json
import math
import struct
import sys

import numpy as np

chemin, budget, sortie = sys.argv[1], float(sys.argv[2]), sys.argv[3]
o = open(chemin, "rb").read()
L, T = struct.unpack_from("<II", o, 0)
assert len(o) == 8 + L * T * 8
ex = np.zeros((T, L, 4), dtype=np.int64)
mg = np.zeros((T, L))
for l in range(L):
    for p in range(T):
        d = 8 + (l * T + p) * 8
        ex[p, l] = list(o[d:d + 4])
        mg[p, l] = struct.unpack_from("<f", o, d + 4)[0]
E = int(ex.max()) + 1
N = max(4, round(budget * L * E))
ld = math.log(0.5) / 8.0
cle, vu, cache, tas = {}, {}, set(), []
manque = np.zeros((T, L, 4), dtype=bool)
for t in range(T):
    for l in range(L):
        i = t * L + l
        g = [l * E + int(e) for e in ex[t, l]]
        for r, x in enumerate(g):
            anc = cle.get(x)
            v = 1.0 if anc is None else math.exp(anc + t * ld) + 1.0
            cle[x] = math.log(v) - t * ld
            vu[x] = i
            manque[t, l, r] = x not in cache
            cache.add(x)
            heapq.heappush(tas, (cle[x], vu[x], x))
        dans = set(g)
        mis = []
        while len(cache) > N:
            c, v, x = heapq.heappop(tas)
            if x not in cache or cle[x] != c or vu[x] != v:
                continue
            if x in dans:
                mis.append((c, v, x))
                continue
            cache.remove(x)
        for e in mis:
            heapq.heappush(tas, e)
tot = int(manque.sum())
res = {"positions": T, "couches": L, "experts": E, "N": N, "taux_succes": 1 - tot / manque.size,
       "defauts": tot, "defauts_par_rang": [int(manque[:, :, r].sum()) for r in range(4)],
       "marge_mediane": float(np.median(mg)), "quantiles_marge": {str(q): float(np.quantile(mg, q)) for q in (0.05, 0.1, 0.25, 0.5, 0.75)},
       "bornes": []}
for tau in (0.001, 0.003, 0.01, 0.03, 0.1, 0.3):
    ok = manque[:, :, 3] & (mg < tau)
    res["bornes"].append({"tau": tau, "part_cellules_sous_tau": float((mg < tau).mean()),
                          "part_des_defauts_evitables_au_plus": float(ok.sum() / tot)})
json.dump(res, open(sortie, "w", encoding="utf-8"), indent=1)
print(json.dumps(res, indent=1))
