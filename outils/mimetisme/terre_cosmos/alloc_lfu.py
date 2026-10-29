"""Post hoc, hors seuil déclaré : M-A avec une LFU (demi-vie 32 jetons) par couche au lieu d'un LRU.
Allocation par programmation dynamique sur les courbes par couche des trois autres genres ; jugée sur le
quatrième. Comparée à : LFU globale (demi-vie 32), LFU par couche uniforme (n = N // L).
Usage : python -I -X utf8 alloc_lfu.py <20b|120b> <dossier_traces> <sortie.json>"""
import json
import os
import sys

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
sys.path.insert(0, os.path.abspath(os.path.join(ICI, "..", "..")))
import cache_terre as ct  # noqa: E402
import gptoss_localite as gl  # noqa: E402

HL = 32.0
pref, dossier, sortie = "t" + sys.argv[1], sys.argv[2], sys.argv[3]
data = {g: ct.charger(pref, dossier, g) for g in ct.GENRES}
E = data["code"][1]
L = len(data["code"][0][0])
k = len(data["code"][0][0][0])
PAS = 1 if E <= 32 else 4  # 120b : tailles par pas de 4 pour tenir en temps


def lfu_couche(seq, n):
    groupes = [list(g) for g in seq]
    return gl.g_lfu(groupes, n, 1, HL) * sum(len(g) for g in groupes)  # nombre de succès


tailles = [0] + list(range(k, E + 1, PAS))
courbes = {}
for g in ct.GENRES:
    c = np.zeros((L, E + 1), dtype=np.int64)
    for l in range(L):
        seq = [t[l] for t in data[g][0]]
        for n in tailles[1:]:
            c[l, n] = round(lfu_couche(seq, n))
        # remplir les tailles sautées par la valeur de la taille inférieure (concave par morceaux : borne basse)
        for n in range(k, E + 1):
            if c[l, n] == 0 and n > k:
                c[l, n] = c[l, n - 1]
    courbes[g] = c
    print("courbes", g, flush=True)

res = {}
for f in (0.15, 0.20, 0.30):
    N = max(k, round(f * L * E))
    lignes = {}
    for g in ct.GENRES:
        autres = [x for x in ct.GENRES if x != g]
        cs = sum(courbes[x] for x in autres)
        alloc = ct.allocation_dp(cs, N, k, E)
        tot = sum(len(t[l]) for t in data[g][0] for l in range(L))
        h = sum(lfu_couche([t[l] for t in data[g][0]], alloc[l]) if alloc[l] else 0 for l in range(L))
        n_u = N // L
        hu = sum(lfu_couche([t[l] for t in data[g][0]], n_u) for l in range(L)) if n_u >= k else float("nan")
        glob = gl.g_lfu(gl.flux(data[g][0], E), N, L, HL)
        lignes[g] = {"A_lfu": h / tot, "uniforme_lfu": hu / tot, "globale_lfu": glob, "alloc": alloc}
    moy = lambda c: sum(lignes[g][c] for g in ct.GENRES) / 4
    res[f"{f:.2f}"] = {"N": N, "genres": lignes, "A_lfu": moy("A_lfu"), "uniforme": moy("uniforme_lfu"), "globale": moy("globale_lfu"),
                       "pos": sum(1 for g in ct.GENRES if lignes[g]["A_lfu"] > lignes[g]["globale_lfu"])}
    print(sys.argv[1], f, "A+LFU %.4f  LFU par couche uniforme %.4f  LFU globale %.4f  (%d/4 genres au-dessus de la globale)" %
          (res[f"{f:.2f}"]["A_lfu"], res[f"{f:.2f}"]["uniforme"], res[f"{f:.2f}"]["globale"], res[f"{f:.2f}"]["pos"]), flush=True)
json.dump(res, open(sortie, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
