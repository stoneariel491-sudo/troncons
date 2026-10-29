"""Contrôle de E-A (non déclaré avant, dit tel) : le gain d'ACT-R contre LFU8 vient-il seulement d'une mémoire plus longue ?

LFU à décroissance exponentielle, demi-vie h dans {4 ... 512} jetons ; h choisi sur les QUATRE AUTRES genres
(le meilleur taux de succès moyen), évalué sur le genre testé. Comparé à ACT-R d = 0,5 (aucun réglage) et au
LFU8 de la règle. Usage : python -I ablation_demivie.py DOSSIER_TRACES
"""
import importlib.util
import json
import statistics
import sys
from pathlib import Path

ici = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("bt", ici / "bancs_traces.py")
bt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bt)
bt.sous_la_normale()
ins = bt.instrument()
dossier = sys.argv[1]
HL = [4, 8, 16, 32, 64, 128, 256, 512]
brut = json.load(open(bt.SORTIE / "ea-brut.json"))
res = {}
for modele in ("20b", "120b"):
    jeu = {g: bt.charger(dossier, modele, g)[0] for g in bt.GENRES}
    L = jeu[bt.GENRES[0]].shape[1]
    res[modele] = {}
    for C in bt.BUDGETS[modele]:
        table = {}
        for g in bt.GENRES:
            table[g] = {}
            for h in HL:
                table[g][h] = statistics.fmean(ins.cache_lfu(bt.par_couche(jeu[g], c), C, float(h)) for c in range(L))
            print(modele, C, g, {h: round(v, 4) for h, v in table[g].items()}, flush=True)
        gains, choisis = [], {}
        for g in bt.GENRES:
            autres = [x for x in bt.GENRES if x != g]
            h_star = max(HL, key=lambda h: statistics.fmean(table[x][h] for x in autres))
            choisis[g] = h_star
            lfu_h = table[g][h_star]
            actr = brut[modele][f"{g}|{C}"]["actr_d0.5"]
            lfu8 = table[g][8]
            lru = brut[modele][f"{g}|{C}"]["lru"]
            meilleur = max(lru, lfu8)
            gains.append({"genre": g, "h_choisi_ailleurs": h_star, "lfu_h": lfu_h, "actr": actr, "lfu8": lfu8,
                          "gain_lfu_h_vs_meilleur_connu": ((1 - meilleur) - (1 - lfu_h)) / (1 - meilleur),
                          "gain_actr_vs_meilleur_connu": ((1 - meilleur) - (1 - actr)) / (1 - meilleur),
                          "gain_actr_vs_lfu_h": ((1 - lfu_h) - (1 - actr)) / (1 - lfu_h)})
        res[modele][str(C)] = {"table": table, "gains": gains,
                               "mediane_lfu_h": statistics.median(x["gain_lfu_h_vs_meilleur_connu"] for x in gains),
                               "mediane_actr": statistics.median(x["gain_actr_vs_meilleur_connu"] for x in gains),
                               "mediane_actr_vs_lfu_h": statistics.median(x["gain_actr_vs_lfu_h"] for x in gains)}
        print(modele, C, "médianes : LFU(h choisi ailleurs)", round(res[modele][str(C)]["mediane_lfu_h"], 4),
              "ACT-R", round(res[modele][str(C)]["mediane_actr"], 4),
              "ACT-R contre LFU(h)", round(res[modele][str(C)]["mediane_actr_vs_lfu_h"], 4), flush=True)
bt.ecrire("ablation-demivie.json", res)
