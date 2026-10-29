"""P2, explorations POST-HOC (hors seuil déclaré, à lire comme des pistes, pas comme le verdict).

  distances   distribution des distances de pile LRU (Mattson 1970) sur les deux générations et sur
              prose-en.lecture : P(d <= C) est le succès d'un LRU de capacité C (hors épinglage). C'est la
              raison pour laquelle l'exclusif vaut un LRU de V + R : le gain est la masse de distances
              comprise entre V et V + R.
  selectif    démotion sélective : la victime VRAM ne descend en RAM que si elle a été réutilisée pendant
              son séjour en VRAM (ou si elle venait de la RAM), pour réduire le trafic de descente.
  seuils      la même chose pour un seuil de réutilisation s (>= s succès VRAM pendant le séjour).
Usage : python -I -X utf8 explorations.py <dossier des traces> <distances|selectif> <csv de sortie>
"""
import csv
import sys
from collections import OrderedDict

import numpy as np

sys.path.insert(0, "~/dev/active/troncons/outils/mimetisme/P2")
from cache_exclusif import L, traces  # noqa: E402


def distances(G, cmax=4608):
    """Rend l'histogramme des distances de pile (index 1..cmax) et le nombre de premiers accès."""
    pile = []  # tête = plus récent à la fin
    hist = np.zeros(cmax + 2, dtype=np.int64)
    froids = 0
    n = 0
    for t in range(G.shape[0]):
        for l in range(L):
            for x in G[t, l]:
                x = int(x)
                n += 1
                try:
                    i = len(pile) - 1 - pile[::-1].index(x)  # position depuis le bas
                    d = len(pile) - i
                    pile.pop(i)
                    hist[min(d, cmax + 1)] += 1
                except ValueError:
                    froids += 1
                pile.append(x)
    return hist, froids, n


def sim_sel(G, V, R, seuil, L=L):
    """Exclusif LRU avec démotion sélective : la victime descend si son compteur de succès VRAM
    pendant le séjour est >= seuil (seuil = 0 : exclusif simple). Une entrée montée de la RAM arrive
    avec le compteur = seuil (elle a déjà prouvé sa réutilisation)."""
    vram, ram = OrderedDict(), OrderedDict()  # vram : id -> compteur de succès pendant le séjour
    c = dict(acces=0, sv=0, sr=0, disque=0, demotions=0, saute=0)
    for t in range(G.shape[0]):
        for l in range(L):
            g = [int(x) for x in G[t, l]]
            pins = set(g)
            for x in g:
                c["acces"] += 1
                if x in vram:
                    c["sv"] += 1
                    vram[x] += 1
                    vram.move_to_end(x)
                    continue
                victime = None
                vc = 0
                if len(vram) >= V:
                    for v in vram:
                        if v not in pins:
                            victime = v
                            break
                    vc = vram.pop(victime)
                if x in ram:
                    c["sr"] += 1
                    del ram[x]
                    vram[x] = seuil
                else:
                    c["disque"] += 1
                    vram[x] = 0
                if victime is not None:
                    if vc >= seuil:
                        c["demotions"] += 1
                        if victime in ram:
                            ram.move_to_end(victime)
                        else:
                            if len(ram) >= R:
                                ram.popitem(last=False)
                            ram[victime] = True
                    else:
                        c["saute"] += 1
    c["jetons"] = G.shape[0]
    c["part_disque"] = c["disque"] / c["acces"]
    return c


if __name__ == "__main__":
    dossier, cmd, sortie = sys.argv[1], sys.argv[2], sys.argv[3]
    tr = traces(dossier)
    if cmd == "distances":
        with open(sortie, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["trace", "C", "succes_LRU_C", "acces", "premiers_acces"])
            for nom in ("prose-en.generation", "wiki.generation"):
                h, froids, n = distances(tr[nom])
                cum = np.cumsum(h[: 4608 + 1])
                for C in list(range(1, 64, 7)) + list(range(64, 2049, 16)) + [2560, 3072, 4096, 4608]:
                    w.writerow([nom, C, round(float(cum[C]) / n, 6), n, froids])
                print(nom, flush=True)
    elif cmd == "selectif":
        with open(sortie, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["trace", "V", "R", "seuil_reutilisation", "part_disque", "demotions_par_jeton",
                        "demotions_sautees_par_jeton", "succes_ram"])
            for nom in ("prose-en.generation", "wiki.generation", "code.lecture", "dialogue.lecture",
                        "prose-en.lecture", "prose-fr.lecture", "wiki.lecture"):
                for R in (160, 336, 672):
                    for s in (0, 1, 2, 3):
                        c = sim_sel(tr[nom], 326, R, s)
                        w.writerow([nom, 326, R, s, round(c["part_disque"], 6),
                                    round(c["demotions"] / c["jetons"], 4), round(c["saute"] / c["jetons"], 4),
                                    round(c["sr"] / c["acces"], 6)])
                print(nom, flush=True)
