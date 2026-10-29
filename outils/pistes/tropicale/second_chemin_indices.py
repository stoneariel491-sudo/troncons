"""Second chemin de la garde à indices multiples (seuil-declare-indices.md § 6).

Python pur : ni numpy, ni le code de indices.py. Lit les journaux A et B avec la fonction `lire` du lot R
(mesures/moteur/R/bascules.py), recalcule les étiquettes et les indices f1, f2, f4 par boucles, puis :
  (a) recompte, par classement explicite des scores de scores-M3.csv, les bascules attrapées par pli ;
  (b) ajuste une autre classe de modèle, des probabilités par classes (f1 en 20 quantiles, f2 en 4, f4 en
      4 classes, lissage de Laplace +1 bascule +20 cellules) sur les mêmes dix plis.
Priorité sous la normale ; pause sur le verrou de la carte.
"""
import bisect
import csv
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
DEPOT = Path(__file__).resolve().parents[3]
SORTIE = DEPOT / "mesures" / "pistes" / "tropicale" / "indices"
VERROU = Path("~/dev/verrou-carte.txt")
L, W, P = 24, 10, 511
SEUIL_F4 = 0.01241


def baisser():
    try:
        import ctypes
        k = ctypes.windll.kernel32
        k.GetCurrentProcess.restype = ctypes.c_void_p
        k.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        k.SetPriorityClass(k.GetCurrentProcess(), 0x4000)
    except Exception as e:
        print("priorité non baissée :", e)


def calme():
    while True:
        try:
            t = VERROU.read_text(encoding="utf-8", errors="replace").lower()
        except OSError:
            return
        if not any(m in t for m in ("abba", "j1", "vitesse")):
            return
        time.sleep(30)


def charger_lot_r():
    spec = importlib.util.spec_from_file_location("bascules_lot_r", DEPOT / "mesures" / "moteur" / "R" / "bascules.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.lire


def top_k(scores):
    """Indices (dans l'ordre l-majeur, p) des K = floor(0,1 n) plus forts scores, ex aequo par indice croissant."""
    k = int(0.10 * len(scores))
    return sorted(range(len(scores)), key=lambda i: (-scores[i], i))[:k]


def main():
    baisser(); calme()
    lire = charger_lot_r()
    _, n, ea, ma = lire(DEPOT / "mesures/moteur/R/r1/routage/ref-openai-bis-20b.bin")
    _, _, eb, mb = lire(DEPOT / "mesures/moteur/R/r1/routage/ref-llamacpp-bis-20b.bin")
    assert n == W * P
    # étiquettes et indices par cellule (l, w, p), index plat i = (l * W + w) * P + p
    y = [[ea[l][i] != eb[l][i] for i in range(n)] for l in range(L)]
    f1 = [[math.log(mb[l][i]) for i in range(n)] for l in range(L)]
    cm = [[0.0] * n for _ in range(L)]      # min des marges de B sur les couches <= l
    for i in range(n):
        m = float("inf")
        for l in range(L):
            m = min(m, mb[l][i]); cm[l][i] = m
    f2 = [[0.0 if l == 0 else math.log(cm[l - 1][i]) for i in range(n)] for l in range(L)]
    hit = [[1 if mb[l][i] < SEUIL_F4 else 0 for i in range(n)] for l in range(L)]
    f4 = [[0.0] * n for _ in range(L)]
    for l in range(L):
        for w in range(W):
            for p in range(1, P):
                lo = max(0, p - 8)
                s = 0
                for ll in range(l + 1):
                    for pp in range(lo, p):
                        s += hit[ll][w * P + pp]
                f4[l][w * P + p] = s / ((p - lo) * (l + 1))
    res = {"bascules": sum(sum(r) for r in y)}

    # (a) recomptage de M3 et de M0 par classement explicite
    scores = {}
    with open(SORTIE / "scores-M3.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            scores[(int(r["l"]), int(r["w"]), int(r["p"]))] = float(r["score"])
    cmp3, cmp0, nbf = [], [], []
    for w in range(W):
        cells = [(l, p) for l in range(L) for p in range(P)]
        s3 = [scores[(l, w, p)] for (l, p) in cells]
        s0 = [-mb[l][w * P + p] for (l, p) in cells]
        cmp3.append(sum(y[cells[i][0]][w * P + cells[i][1]] for i in top_k(s3)))
        cmp0.append(sum(y[cells[i][0]][w * P + cells[i][1]] for i in top_k(s0)))
        nbf.append(sum(y[l][w * P + p] for (l, p) in cells))
    res["recompte"] = {"M3": cmp3, "M0": cmp0, "bascules_par_fenetre": nbf,
                       "b_M3": 100 * sum(cmp3) / sum(nbf), "b_M0": 100 * sum(cmp0) / sum(nbf)}

    # (b) l'autre classe de modèle : probabilités par classes
    def classe_f4(v):
        return 0 if v == 0 else 1 if v <= 0.05 else 2 if v <= 0.15 else 3
    cmpb, nb_tot = [], 0
    for w in range(W):
        train = [(l, i) for l in range(L) for i in range(n) if i // P != w]
        def edges(vals, k):
            s = sorted(vals)
            return [s[int(j * len(s) / k)] for j in range(1, k)]
        e1 = edges([f1[l][i] for l, i in train], 20)
        e2 = edges([f2[l][i] for l, i in train], 4)
        tab = {}
        for l, i in train:
            c = (bisect.bisect_right(e1, f1[l][i]), bisect.bisect_right(e2, f2[l][i]), classe_f4(f4[l][i]))
            a = tab.setdefault(c, [0, 0]); a[0] += 1; a[1] += 1 if y[l][i] else 0
        cells = [(l, p) for l in range(L) for p in range(P)]
        sc = []
        for (l, p) in cells:
            i = w * P + p
            c = (bisect.bisect_right(e1, f1[l][i]), bisect.bisect_right(e2, f2[l][i]), classe_f4(f4[l][i]))
            a = tab.get(c, [0, 0])
            sc.append((a[1] + 1) / (a[0] + 20))
        cmpb.append(sum(y[cells[j][0]][w * P + cells[j][1]] for j in top_k(sc)))
    res["classes"] = {"par_fenetre": cmpb, "b": 100 * sum(cmpb) / sum(nbf),
                      "gain_sur_M0": 100 * (sum(cmpb) - sum(cmp0)) / sum(nbf),
                      "fenetres_positives": sum(1 for a, b in zip(cmpb, cmp0) if a > b)}
    (SORTIE / "second-chemin-indices.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
