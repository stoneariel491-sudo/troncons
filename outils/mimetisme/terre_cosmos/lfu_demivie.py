"""Post hoc, hors seuil déclaré : la LFU de la base (demi-vie 8 jetons) est-elle réglée au bon endroit ?
Taux de succès moyen sur les quatre genres (cache vide au début de chaque genre) pour des demi-vies de 8 à
1024 jetons, mêmes budgets. Politique de gptoss_localite.g_lfu, importée telle quelle.
Usage : python -I -X utf8 lfu_demivie.py <20b|120b> <dossier_traces> <sortie.json>"""
import json
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
sys.path.insert(0, os.path.abspath(os.path.join(ICI, "..", "..")))
import cache_terre as ct  # noqa: E402
import gptoss_localite as gl  # noqa: E402

HLS = [8, 32, 64, 128, 256, 1024]
pref, dossier, sortie = "t" + sys.argv[1], sys.argv[2], sys.argv[3]
data = {g: ct.charger(pref, dossier, g) for g in ct.GENRES}
E = data["code"][1]
L = len(data["code"][0][0])
flux = {g: gl.flux(data[g][0], E) for g in ct.GENRES}
res = {}
for f in ct.BUDGETS:
    N = max(4, round(f * L * E))
    ligne = {}
    for hl in HLS:
        v = [gl.g_lfu(flux[g], N, L, float(hl)) for g in ct.GENRES]
        ligne[str(hl)] = {"moy": sum(v) / 4, "genres": dict(zip(ct.GENRES, v))}
    ligne["lru"] = sum(gl.g_lru(flux[g], N) for g in ct.GENRES) / 4
    res[f"{f:.2f}"] = {"N": N, **ligne}
    print(sys.argv[1], f, "LRU %.4f" % ligne["lru"], " ".join("hl%d %.4f" % (hl, ligne[str(hl)]["moy"]) for hl in HLS), flush=True)
json.dump(res, open(sortie, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
