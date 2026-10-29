# Juge de la troisième passe : refait, par une colorimétrie écrite ici (sRGB → CIELAB D65 ; gris = luminance Rec. 709
# affichée en gris ; deutéranope = Machado, Oliveira et Fernandes 2009, sévérité 1, matrice recopiée de l'article),
# les ΔE CIE76 des dix paires neuves de palette-tome3-paires.csv (1482dbe) et les comptes de palette-tome3-nombres.tex,
# en résolvant moi-même les expressions xcolor (« X!t » = t X + (1 − t) blanc, sur les composantes sRGB).
# Usage : python -I -X utf8 paires3.py
import csv, json, re
from pathlib import Path
import numpy as np

DEPOT = Path(__file__).resolve().parents[4]
DON = DEPOT / "memoire/figures/tome3/donnees"
MACHADO_D = np.array([[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]])
BASE = {"Encre": "1A1A1A", "Signe": "C0392B", "CouleurSigne": "C0392B", "CouleurVunDeux": "D68910",
        "CouleurFrontiereMarque": "363D44", "blanc": "FFFFFF", "black": "000000", "white": "FFFFFF",
        "VunDeux": "D68910", "FrontiereMarque": "363D44"}


def rgb(h):
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float64) / 255


def resoudre(expr):
    m = re.fullmatch(r"(\w+)!(\d+)", expr)
    if m:
        return float(m.group(2)) / 100 * rgb(BASE[m.group(1)]) + (1 - float(m.group(2)) / 100) * 1.0
    return rgb(BASE[expr])


def lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def enc(l):
    l = np.clip(l, 0, 1)
    return np.where(l <= 0.0031308, 12.92 * l, 1.055 * l ** (1 / 2.4) - 0.055)


def lab_lin(l):
    M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
    xyz = M @ l / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def vue(c, mode):
    """La couleur vue, en sRGB codé sur 8 bits (comme un rendu), puis en Lab."""
    l = lin(c)
    if mode == "gris":
        y = l @ np.array([0.2126, 0.7152, 0.0722])
        l = np.array([y, y, y])
    elif mode == "deuter":
        l = MACHADO_D @ l
    s = np.round(enc(l) * 255) / 255
    return lab_lin(lin(s))


def de(a, b, mode):
    return float(np.linalg.norm(vue(a, mode) - vue(b, mode)))


lignes = list(csv.DictReader(open(DON / "palette-tome3-paires.csv", encoding="utf-8")))
neuves = lignes[36:]
assert len(neuves) == 10
res = []
for r in neuves:
    a, b = resoudre(r["a"]), resoudre(r["b"])
    g, d = round(de(a, b, "gris"), 1), round(de(a, b, "deuter"), 1)
    tient = g >= 5 and d >= 10
    res.append({"a": r["a"], "b": r["b"], "figure": r["figures"], "gris_lot": float(r["gris"]), "gris_juge": g,
                "deuter_lot": float(r["deuter"]), "deuter_juge": d, "verdict_lot": r["verdict"],
                "verdict_juge": "tient" if tient else "tombe", "forme": r["forme"]})
tiennent = sum(1 for r in lignes if r["verdict"] == "tient")
print(json.dumps({"paires": len(lignes), "tiennent_selon_le_csv": tiennent, "neuves": res}, ensure_ascii=False, indent=1))
