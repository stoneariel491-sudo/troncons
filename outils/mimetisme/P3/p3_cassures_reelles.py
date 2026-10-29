"""P3 : les cassures des témoins W3 et W5 sur les données réelles (elles n'avaient été passées que sur les logits synthétiques).
W3-hasard : un masque sans lien avec le cache, de même densité, avec bêta = +0,1 ; il doit retirer bien moins de défauts que le masque des résidents.
W3-absents : masque inversé, bêta = +0,1 ; il doit AUGMENTER les défauts. W5-cassure : 1 000 cellules des ensembles bêta = 0,1 remplacées par des experts au hasard,
le rejeu par cache2.lru1 doit changer de compte."""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p3_routage as P

Z = np.load(os.path.join(P.LOURDS, "logits-20b-eval.npy"))
ORD = P.preparer(Z)
T, L, E = Z.shape
res = {}
for nom, frac in P.BUDGETS.items():
    n = round(frac * L * E)
    S0, M0, d0 = P.simuler(Z, ORD, n, 0.0)
    S1, M1, d1 = P.simuler(Z, ORD, n, 0.1)
    Sh, Mh, dh = P.simuler(Z, ORD, n, 0.1, masque="hasard")
    Sa, Ma, da = P.simuler(Z, ORD, n, 0.1, masque="absents")
    rng = np.random.default_rng(3)
    Sb = S1.copy()
    for i in rng.permutation(T * L)[:1000]:
        t, l = divmod(int(i), L)
        Sb[t, l] = rng.permutation(E)[:4]
    dc = P.rejouer_cache2(Sb, n, E)
    res[nom] = {"d0": d0, "d_residents": d1, "d_hasard": dh, "d_absents": da, "d_cache2_abimes": dc,
                "W3_hasard_tient": dh > d1, "W3_absents_tient": da > d0, "W5_cassure_tient": dc != d1}
    print(nom, res[nom], flush=True)
json.dump(res, open(os.path.join(P.SORTIE, "cassures-reelles.json"), "w", encoding="utf-8"), indent=1)
