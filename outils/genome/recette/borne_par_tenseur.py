"""Ce qu'atteindrait un code gaussien idéal (débit-distorsion de Shannon) sur les rangées de
l'échantillon, à l'erreur de la base de chaque tenseur : avec répartition par remplissage inverse
entre rangées (variances de rangée mesurées), et sans répartition (½ log₂(1/D)).
C'est le débit d'un livre de codes gaussien de dimension infinie pour une source de cette variance ;
pour la vraie source (non gaussienne), la fonction débit-distorsion est plus basse ou égale.

Utilisation : python -I -X utf8 borne_par_tenseur.py CSV_RANGEES > borne.json
"""
import csv
import json
import math
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, __import__("os").path.dirname(__file__))
from structure import debit_remplissage  # noqa: E402

par_t = defaultdict(lambda: [[], 0.0])
with open(sys.argv[1], newline="", encoding="utf8") as f:
    for l in csv.DictReader(f):
        d = par_t[l["tenseur"]]
        d[0].append(float(l["energie"]))
        d[1] += float(l["err_base"])
sortie = []
for t, (en, eb) in par_t.items():
    v = np.array(en) / 2880.0
    cible = eb / sum(en)
    sortie.append({"tenseur": t, "erreur_base": cible, "bits_shannon_reparti": debit_remplissage(v, cible),
                   "bits_shannon_uniforme": 0.5 * math.log2(1 / cible),
                   "gain_repartition_haut_debit": 0.5 * math.log2(v.mean() / math.exp(np.log(v).mean()))})
print(json.dumps(sortie, indent=1))
