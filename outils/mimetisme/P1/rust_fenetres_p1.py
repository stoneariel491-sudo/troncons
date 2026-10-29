"""P1, second chemin des fenêtres froides : noyau-p1 rejoue LRU et LFU(h) sur des fenêtres de 256 jetons écrites
en fichiers, comparées à fenetres-120b.csv (cache_p1.py). Usage : python -I -X utf8 rust_fenetres_p1.py"""
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cache_p1 as cp  # noqa: E402
import rust_p1 as rp  # noqa: E402

cp.baisser_priorite()
os.makedirs(rp.TMP, exist_ok=True)
lignes = list(csv.DictReader(open(f"{cp.SORTIE}/fenetres-120b.csv", encoding="utf-8")))
d = cp.dossier_modele("120b")
pire = 0.0
n = 0
for cap in (326, 922):
    for g in cp.GENRES["120b"]:
        lec = rp.lignes_donnees(f"{d}/{cp.prefixe('120b', g)}.lecture.trace")
        nfen = len(lec) // 256
        for i in range(nfen):
            fic = f"{rp.TMP}/fenetre.trace"
            with open(fic, "w", encoding="utf-8") as f:
                f.write("E=128\n" + "\n".join(lec[i * 256:(i + 1) * 256]) + "\n")
            r = rp.lancer("fenetre", [fic], 128, cap)
            ref = [l for l in lignes if int(l["capacite"]) == cap and l["genre"] == g and int(l["fenetre"]) == i][0]
            for nom, colonne in (("lru", "lru"), ("lfu-8", "lfu:8"), ("lfu-32", "lfu:32"), ("lfu-64", "lfu:64"), ("lfu-128", "lfu:128"), ("lfu-inf", "lfu:inf")):
                s = float(r[nom].sum() / (256 * 144))
                pire = max(pire, abs(s - float(ref[colonne])))
                n += 1
print("fenêtres x politiques comparées :", n, "| pire écart de succès :", pire)
