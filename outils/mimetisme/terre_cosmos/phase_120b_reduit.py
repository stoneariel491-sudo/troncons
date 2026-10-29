"""M-C sur le 120b, version réduite (la passe complète coûte 150 s par cas et a été arrêtée après 3 cas sur 16) :
budgets 20 % et 30 % seulement (ceux du seuil), demi-vies 16 et 32 (les deux choisies sur le 20b), contre la
LFU de même demi-vie et la phase à l'envers. Choix de la demi-vie de M-C et de la LFU sur les trois autres genres.
Usage : python -I -X utf8 phase_120b_reduit.py <dossier_traces_120b> <sortie.json>"""
import json
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
sys.path.insert(0, os.path.abspath(os.path.join(ICI, "..", "..")))
import cache_terre as ct  # noqa: E402
import gptoss_localite as gl  # noqa: E402
import phase_terre as pt  # noqa: E402

data = {g: ct.charger("t120b", sys.argv[1], g) for g in ct.GENRES}
E = data["code"][1]
L = len(data["code"][0][0])
flux = {g: gl.flux(data[g][0], E) for g in ct.GENRES}
res = {}
for f in (0.20, 0.30):
    N = round(f * L * E)
    b = {g: {} for g in ct.GENRES}
    for g in ct.GENRES:
        for hl in (16, 32):
            s, tot = pt.g_phase(flux[g], N, L, E, hl, "phase")
            b[g][f"phase{hl}"] = s / tot
            b[g][f"lfu{hl}"] = gl.g_lfu(flux[g], N, L, float(hl))
            s2, _ = pt.g_phase(flux[g], N, L, E, hl, "envers")
            b[g][f"envers{hl}"] = s2 / tot
        print(f, g, b[g], flush=True)
    lignes = {}
    for g in ct.GENRES:
        autres = [x for x in ct.GENRES if x != g]
        hl = max((16, 32), key=lambda h: sum(b[x][f"phase{h}"] for x in autres))
        hl_l = max((16, 32), key=lambda h: sum(b[x][f"lfu{h}"] for x in autres))
        lignes[g] = {"hl_C": hl, "C": b[g][f"phase{hl}"], "hl_lfu": hl_l, "lfu": b[g][f"lfu{hl_l}"],
                     "envers": b[g][f"envers{hl}"], "dC_pt": (b[g][f"phase{hl}"] - b[g][f"lfu{hl_l}"]) * 100}
    res[f"{f:.2f}"] = {"N": N, "genres": lignes, "moy_dC_pt": sum(l["dC_pt"] for l in lignes.values()) / 4,
                       "pos": sum(1 for l in lignes.values() if l["dC_pt"] > 0), "brut": b}
    print("RÉSUMÉ", f, res[f"{f:.2f}"]["moy_dC_pt"], res[f"{f:.2f}"]["pos"], flush=True)
json.dump(res, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
