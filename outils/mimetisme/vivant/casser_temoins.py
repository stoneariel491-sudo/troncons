"""Cassures des témoins de bancs_traces.py : chaque témoin doit pouvoir tomber.

On force la condition à faux (une politique fautive, une fuite du futur, une allocation non uniforme) et
on vérifie que le test correspondant échoue. Usage : python -I casser_temoins.py DOSSIER_TRACES
"""
import importlib.util
import math
import sys
from pathlib import Path

import numpy as np

ici = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("bt", ici / "bancs_traces.py")
bt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bt)

dossier = sys.argv[1]
ins = bt.instrument()
resultats = {}

# W1 cassé : une politique qui évince le PLUS récent doit s'écarter du LRU de l'instrument
class PolMRU(bt.PolDernier):
    def victime(self, cands, t, s):
        return max(cands, key=lambda v: self.dernier.get(v, -1))

sets, _, E = bt.charger(dossier, "20b", "code")
seq = bt.par_couche(sets, 0)
ecart = abs(bt.simuler(seq, 6, PolMRU(E), E) - ins.cache_lru(seq, 6))
resultats["W1_casse_MRU"] = {"ecart": ecart, "tombe": ecart > 1e-12}

# W3 cassé : un prédicteur qui regarde le jeton suivant doit échouer au test de causalité
class FuiteAssoc(bt.PolAssoc):
    def __init__(self, E, seq):
        super().__init__(E)
        self.seq = seq

    def victime(self, cands, t, s):
        # regarde 40 jetons plus loin : la moitié de trace ne contient pas ce futur, la trace entière si
        futur = set(x for u in self.seq[t + 1:t + 41] for x in u)
        # garde ce que le jeton suivant va demander : évince un expert hors du futur
        hors = [v for v in cands if v not in futur]
        return (hors or cands)[0]

sets, _, E = bt.charger(dossier, "20b", "dialogue")
seq = bt.par_couche(sets, 3)
demi = len(seq) // 2
_, f_plein = bt.simuler(seq, 6, FuiteAssoc(E, seq), E, pas_hits=True)
_, f_demi = bt.simuler(seq[:demi], 6, FuiteAssoc(E, seq[:demi]), E, pas_hits=True)
resultats["W3_casse_fuite"] = {"identiques": f_plein[:len(f_demi)] == f_demi, "tombe": f_plein[:len(f_demi)] != f_demi}

# W4 cassé : une politique à oracle sur routage i.i.d. sort de la tolérance
rng = np.random.default_rng(20261026)
T, E, L, C = 2500, 128, 1, 26
sy = np.array([[rng.choice(E, 4, replace=False)] for _ in range(T)])
seq = bt.par_couche(sy, 0)
p = C / E
tol = 4 * math.sqrt(p * (1 - p) / (T * 4 * L)) + 4 / T
v = bt.simuler(seq, C, FuiteAssoc(E, seq), E)
resultats["W4_casse_oracle_iid"] = {"mesure": v, "attendu": p, "tolerance": tol, "tombe": abs(v - p) > tol}

# W9 cassé : courbes différentes -> allocation non uniforme
courbe_a = 1 - np.exp(-np.arange(0, 65) / 10.0)
courbe_b = 1 - np.exp(-np.arange(0, 65) / 40.0)
courbes = np.array([courbe_a if i % 2 == 0 else courbe_b for i in range(36)])
al = bt.allouer(courbes, 36 * 13, 4)
resultats["W9_casse_courbes_differentes"] = {"min": int(al.min()), "max": int(al.max()), "tombe": bool(al.min() != al.max())}

# W5 cassé : seuil tau trop large -> les poids égaux deviennent abandonnables
def abandon(w, tau):
    w = sorted(w); m = n = 0
    for x in w:
        if m + x <= tau + 1e-12:
            m += x; n += 1
        else:
            break
    return n
resultats["W5_casse_tau"] = {"n": abandon([0.25] * 4, 0.30), "tombe": abandon([0.25] * 4, 0.30) != 0}

# W8 cassé : rang 4 planté au lieu de 3 -> le rang mesuré doit changer
X = np.vstack([np.random.default_rng(1).random((300, 10)) @ np.random.default_rng(2).random((10, 50))])
ev = bt.gram_energies(X)
resultats["W8_casse_rang"] = {"rang": int((ev > 1e-6 * ev.max()).sum()), "tombe": int((ev > 1e-6 * ev.max()).sum()) != 3}

for k, v in resultats.items():
    print(k, "TOMBE (bien)" if v["tombe"] else "NE TOMBE PAS (témoin mou)", v)
print("TOUTES LES CASSURES TOMBENT" if all(v["tombe"] for v in resultats.values()) else "UN TÉMOIN EST MOU")
