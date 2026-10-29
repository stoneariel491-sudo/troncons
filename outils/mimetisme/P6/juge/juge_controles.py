"""Juge P6 : contrôles exploratoires (hors seuils déclarés, étiquetés tels dans JUGEMENT.md).

1. Part de l'énergie de « accepter » portée par les succès (le rôle de mesure dit 77 %).
2. Raisonnement du témoin T2 (mélange par couche) : sous mélange, l'énergie des seuls succès d'un séjour F
   doit valoir la part des succès tombés dans un séjour F (poids indépendants) ; l'écart à r = 1 vient alors
   de l'accès d'entrée, sélectionné petit.
3. Sensibilité du verdict au choix θ = 0,20 : r à S = 8 % exactement, trace par trace (balayage fin de θ).
Usage : python -I -X utf8 juge_controles.py <dossier traces 120b> <sortie.json>
"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import juge_p6 as J

d120, sortie = sys.argv[1:3]
G = {"gen-prose-en": "t120b.prose-en.generation", "gen-wiki": "w120b.wiki.generation"}
res = {}
donnees = {}
for k, base in G.items():
    ex, wt, E = J.charger(d120, base)
    donnees[k] = (ex, wt, J.simuler(ex, E, 323))

# 1. part des succès dans l'énergie de « accepter », theta 0,20
e_def = e_succ = 0.0
for k, (ex, wt, acc) in donnees.items():
    etiq = {}
    for (t, l, s, x, d, sj) in acc:
        w = wt[t][l][s]
        if d:
            etiq[sj] = w < 0.20
            if etiq[sj]:
                e_def += w * w
        elif etiq[sj]:
            e_succ += w * w
res["part_energie_succes_accepter"] = e_succ / (e_def + e_succ)

# 2. mélange par couche des vecteurs de poids (comme T2), énergie des succès seulement
rng = random.Random(5)
num = den = n_succ_F = n_succ = 0.0
for k, (ex, wt, acc) in donnees.items():
    T, L = len(wt), len(wt[0])
    perm = [[None] * L for _ in range(T)]
    for l in range(L):
        ordre = list(range(T))
        rng.shuffle(ordre)
        for t in range(T):
            perm[t][l] = wt[ordre[t]][l]
    etiq = {}
    for (t, l, s, x, d, sj) in acc:
        w = perm[t][l][s]
        if d:
            etiq[sj] = w < 0.20
        else:
            n_succ += 1
            den += w * w
            if etiq[sj]:
                n_succ_F += 1
                num += w * w
res["T2_melange_succes"] = {"part_energie_succes_F": num / den, "part_succes_F": n_succ_F / n_succ,
                            "rapport": (num / den) / (n_succ_F / n_succ)}

# 3. r à S = 8 % exactement par trace (accepter), balayage de theta par pas de 0,0005
courbe = {}
for k, (ex, wt, acc) in donnees.items():
    pts = []
    th = 0.15
    while th <= 0.26:
        S, e, r, _ = J.bilan(list(J.appliquer(acc, wt, th, "accepter").values()))
        pts.append((th, S, r))
        th = round(th + 0.0005, 4)
    # interpolation linéaire au passage de S = 0,08
    for (t0, S0, r0), (t1, S1, r1) in zip(pts, pts[1:]):
        if S0 < 0.08 <= S1:
            a = (0.08 - S0) / (S1 - S0)
            courbe[k] = {"theta_a_S8": t0 + a * (t1 - t0), "r_a_S8": r0 + a * (r1 - r0)}
            break
    courbe[k]["points"] = [p for p in pts if abs(p[0] - 0.20) < 0.0201]
res["accepter_r_a_S_8pct"] = courbe
print(json.dumps({k: v for k, v in res.items() if k != "accepter_r_a_S_8pct"}, ensure_ascii=False))
print({k: {kk: vv for kk, vv in v.items() if kk != "points"} for k, v in courbe.items()})
with open(sortie, "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
