"""C4 par la vérité du juge : comparaison appariée (troncons contre llama.cpp, mêmes positions).

d_i = KL(V ‖ troncons)_i − KL(V ‖ llama)_i ; σ̂(d̄) = s_d / √n. Premier choix : intervalles de
Wilson à 95 %. Verdict littéral du § 7.1 (moyenne et taux) et verdict apparié (d̄ + 2σ̂ < 0).
Commande : python -I -X utf8 verdict_c4.py <csv de comparer_kld> <colonne troncons> <colonne llama>
"""
import csv
import json
import math
import sys


def wilson(k, n, z=1.96):
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [c - h, c + h]


lignes = list(csv.DictReader(open(sys.argv[1], encoding="utf-8")))
t, l = sys.argv[2], sys.argv[3]
kt = [float(r[f"kl_{t}"]) for r in lignes]
kl = [float(r[f"kl_{l}"]) for r in lignes]
pt = [int(r[f"meme_premier_{t}"]) for r in lignes]
pl = [int(r[f"meme_premier_{l}"]) for r in lignes]
n = len(kt)
d = [a - b for a, b in zip(kt, kl)]
dm = sum(d) / n
sd = math.sqrt(sum((x - dm) ** 2 for x in d) / (n - 1))
r = {"n": n, "kl_troncons": sum(kt) / n, "kl_llama": sum(kl) / n, "d_moyen": dm, "sigma_d_moyen": sd / math.sqrt(n),
     "premier_troncons": sum(pt) / n, "wilson_troncons": wilson(sum(pt), n),
     "premier_llama": sum(pl) / n, "wilson_llama": wilson(sum(pl), n)}
r["litteral_tient"] = r["kl_troncons"] <= r["kl_llama"] and r["premier_troncons"] >= r["premier_llama"]
r["apparie_tient"] = dm + 2 * r["sigma_d_moyen"] < 0
print(json.dumps(r, indent=1))
