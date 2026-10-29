# Juge de design du Tome III : distances entre les couleurs du préambule et des lots,
# en vision normale, deutéranope, protanope (Machado, Oliveira, Fernandes 2009, sévérité 1)
# et en niveaux de gris (luminance relative). Distance : ΔE CIE76 dans CIELAB (D65).
# Témoin T0 (déclaré avant) : un gris pur reste gris sous chaque matrice (ΔE < 0,5), et une paire
# rouge-vert connue pour être confondue (C0392B contre 2E8B57) a un ΔE deutéranope < 1/2 du normal.
# Cassure (--casser) : les matrices sont remplacées par l'identité ; le second témoin doit tomber.
# Usage : python -I -X utf8 palette.py [--casser] > sortie.json
import json, sys
import numpy as np

MACHADO = {
    "deuter": [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
    "protan": [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
}
if "--casser" in sys.argv:
    MACHADO = {k: np.eye(3).tolist() for k in MACHADO}

def lin(h):
    c = np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)]) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

def lab(l):
    M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
    xyz = M @ l / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])

def vue(h, mode):
    l = lin(h)
    if mode == "gris":
        y = float(l @ np.array([0.2126, 0.7152, 0.0722]))
        l = np.array([y, y, y])
    elif mode in MACHADO:
        l = np.clip(np.array(MACHADO[mode]) @ l, 0, 1)
    return lab(l)

def de(a, b, mode):
    return float(np.linalg.norm(vue(a, mode) - vue(b, mode)))

MODES = ["normal", "deuter", "protan", "gris"]
# Paires que les figures demandent de distinguer (couleur et rôle tirés des fichiers *-figures.tex).
PAIRES = {
    "III-8.1 zéros (Echelle) / négatifs (Signe)": ("D68910", "C0392B"),
    "III-8.4 cassure (Signe) / grille égale (Mant!30 = C0DCCD)": ("C0392B", "C0DCCD"),
    "III-9.2 frontière (SerieF) / λ=0 (SerieC)": ("6C7A89", "2E8B57"),
    "III-9.2 λ=1 (SerieA) / λ=0 (SerieC)": ("1F5C99", "2E8B57"),
    "III-9.2 frontière (SerieF) / λ=1 (SerieA)": ("6C7A89", "1F5C99"),
    "III-9.3 R1 (SerieA) / neuves (SerieE)": ("1F5C99", "8E44AD"),
    "III-10.1 R1 seul (SerieA!50 = 8FAECC) / neuves seules (SerieE!50 = C6A2D6)": ("8FAECC", "C6A2D6"),
    "III-7.4 brin (SerieB) / S* (SerieC)": ("C0392B", "2E8B57"),
    "III-7.4 base (black!45 = 8C8C8C) / S* (SerieC)": ("8C8C8C", "2E8B57"),
    "III-7.6 expert 24 (SerieB) / expert 4 (Disque)": ("C0392B", "8B5A2B"),
    "III-7.6 expert 12 (SerieA) / expert 21 (SerieE)": ("1F5C99", "8E44AD"),
    "III-7.6 expert 12 (SerieA) / expert 13 (Ram)": ("1F5C99", "1F7A8C"),
    "III-7.6 expert 31 (SerieC) / expert 27 (latRose)": ("2E8B57", "B03A7A"),
    "III-7.6 expert 23 (SerieD) / expert 4 (Disque)": ("D68910", "8B5A2B"),
    "III-4.2 couche voisine (SerieC) / même indice (SerieD)": ("2E8B57", "D68910"),
    "III-3.4 l=12 (SerieA) / l=16 (SerieE)": ("1F5C99", "8E44AD"),
    "III-8.6 v1.2 (SerieB) / compagnon (SerieC)": ("C0392B", "2E8B57"),
}
sortie = {"methode": "ΔE CIE76, CIELAB D65 ; Machado et al. 2009 sévérité 1 ; gris = luminance relative",
          "casse": "--casser" in sys.argv, "paires": {}}
for nom, (a, b) in PAIRES.items():
    sortie["paires"][nom] = {m: round(de(a, b, m), 1) for m in MODES}
# Témoins.
gris_ok = all(np.linalg.norm(vue("808080", m)[1:]) < 0.5 for m in ("deuter", "protan"))
rv = sortie["paires"]["III-7.4 brin (SerieB) / S* (SerieC)"]
rv_ok = rv["deuter"] < 0.5 * rv["normal"]
sortie["temoin_gris_reste_gris"] = bool(gris_ok)
sortie["temoin_rouge_vert_confondu_deuter"] = bool(rv_ok)
print(json.dumps(sortie, ensure_ascii=False, indent=1))
