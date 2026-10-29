"""Témoin : notre découpe des champs reconstruit exactement les poids que la
bibliothèque gguf (llama.cpp, licence MIT, second chemin indépendant) déquantifie.

Usage : python temoin_champs.py <fichier.gguf> [--casser]
--casser inverse les deux demi-octets de Q4_K et de MXFP4 : le témoin doit alors tomber.
"""
import sys

import numpy as np
from gguf import GGMLQuantizationType, quants

import champs_k
from gguf_lecture import LecteurGGUF

casser = "--casser" in sys.argv
L = LecteurGGUF(sys.argv[1])
vus = set()
echecs = 0
for t in L.tenseurs:
    if t.nom_type not in champs_k.DECOUPEURS or t.nom_type in vus:
        continue
    vus.add(t.nom_type)
    taille = champs_k.DECOUPEURS[t.nom_type][1]
    brut = np.asarray(L.octets(t)[: taille * 4096]).reshape(-1, taille)
    notre = brut
    if casser and t.nom_type == "Q4_K":   # la panne ne touche que notre chemin
        notre = brut.copy()
        q = notre[:, 16:]
        notre[:, 16:] = ((q & 0x0F) << 4) | (q >> 4)
    if casser and t.nom_type == "MXFP4":
        notre = brut.copy()
        q = notre[:, 1:]
        notre[:, 1:] = ((q & 0x0F) << 4) | (q >> 4)
    a = champs_k.deconstruire(t.nom_type, notre).reshape(-1)
    b = quants.dequantize(brut.reshape(-1), GGMLQuantizationType[t.nom_type]).reshape(-1)
    ecart = float(np.max(np.abs(a - b)))
    ok = ecart <= 1e-6 * float(np.max(np.abs(b)))
    echecs += not ok
    print(f"{t.nom_type:5s} {t.nom:30s} écart max {ecart:.3e}  {'OK' if ok else 'ÉCHEC'}")
print("TÉMOIN", "TOMBÉ" if echecs else "TENU", f"({echecs} échec(s))")
sys.exit(1 if echecs else 0)
