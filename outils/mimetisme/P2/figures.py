"""P2 : figures tirées des CSV commités (aucune valeur saisie à la main).
  fig1  distances de pile LRU : le gain de l'exclusif est la bande V..V+R sous la courbe
  fig2  part disque en fonction de R, inclusif contre exclusif, deux générations, deux capacités V
Usage : python -I -X utf8 figures.py
"""
import csv
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

B = "~/dev/active/troncons/mesures/mimetisme/P2"
O = "~/dev/active/troncons/genome/mimetisme/P2/figures"
import os  # noqa: E402

os.makedirs(O, exist_ok=True)
ENCRE, GRIS, ROUGE, BLEU, OR = "#1d1d1f", "#8e8e93", "#c0392b", "#1f5fa8", "#b9770e"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": GRIS, "axes.labelcolor": ENCRE,
                     "xtick.color": ENCRE, "ytick.color": ENCRE, "axes.spines.top": False, "axes.spines.right": False})

# ---------------------------------------------------------------- fig1
dist = {}
for r in csv.DictReader(open(f"{B}/explore-distances.csv", encoding="utf-8")):
    dist.setdefault(r["trace"], []).append((int(r["C"]), float(r["succes_LRU_C"])))
fig, axs = plt.subplots(1, 2, figsize=(7.4, 2.9), sharey=True)
V, R = 326, 336
for ax, (nom, titre) in zip(axs, (("prose-en.generation", "prose-en, génération"), ("wiki.generation", "wiki, génération"))):
    xs, ys = zip(*dist[nom])
    ax.plot(xs, ys, color=ENCRE, lw=1.4)
    ax.axvspan(V, V + R, color=OR, alpha=0.22, lw=0)
    ax.axvline(V, color=BLEU, lw=1, ls="--")
    ax.axvline(V + R, color=ROUGE, lw=1, ls="--")
    ax.set_xlim(0, 1400)
    ax.set_xticks([0, 400, 800, 1200])
    ax.set_title(titre, fontsize=9, loc="left", color=ENCRE)
    ax.set_xlabel("capacité C (emplacements)")
    ax.text(V - 8, 0.04, "V", color=BLEU, ha="right")
    ax.text(V + R + 8, 0.04, "V + R", color=ROUGE, ha="left")
    # valeurs lues sur la courbe aux deux abscisses les plus proches de la grille
    def f(c):
        return min(dist[nom], key=lambda t: abs(t[0] - c))[1]
    ax.annotate(f"gain ≈ {f(V + R) - f(V):.2f}", xy=((V + V + R) / 2, (f(V) + f(V + R)) / 2),
                xytext=(V + R + 120, (f(V) + f(V + R)) / 2 - 0.2), color=OR, fontsize=8,
                arrowprops=dict(arrowstyle="-", color=OR, lw=0.8))
axs[0].set_ylabel("P(distance de pile ≤ C)\n= succès d'un LRU de capacité C")
fig.tight_layout()
fig.savefig(f"{O}/fig1-distances-de-pile.pdf")
fig.savefig(f"{O}/fig1-distances-de-pile.png", dpi=200)

# ---------------------------------------------------------------- fig2
g = {}
for r in csv.DictReader(open(f"{B}/grille.csv", encoding="utf-8")):
    g[(r["trace"], int(r["V"]), int(r["R"]), r["mode"])] = float(r["part_disque"])
fig, axs = plt.subplots(2, 2, figsize=(7.4, 5.0), sharex=True)
Rs = [80, 160, 336, 672, 1344]
for i, (nom, titre) in enumerate((("prose-en.generation", "prose-en, génération"), ("wiki.generation", "wiki, génération"))):
    for j, Vv in enumerate((326, 922)):
        ax = axs[i][j]
        seul = g[(nom, Vv, 0, "seul")]
        ax.axhline(seul, color=GRIS, lw=1, ls=":")
        ax.plot(Rs, [g[(nom, Vv, r, "inclusif")] for r in Rs], "-o", color=ROUGE, ms=3.5, lw=1.4, label="inclusif (règle actuelle)")
        ax.plot(Rs, [g[(nom, Vv, r, "exclusif")] for r in Rs], "-o", color=BLEU, ms=3.5, lw=1.4, label="exclusif (démotion)")
        ax.set_xscale("log")
        ax.set_xticks(Rs)
        ax.set_xticklabels([str(r) for r in Rs])
        ax.set_title(f"{titre}, V = {Vv}", fontsize=9, loc="left")
        ax.set_ylim(0, max(seul * 1.08, 0.3))
        if j == 0:
            ax.set_ylabel("part disque")
        if i == 1:
            ax.set_xlabel("R, emplacements de RAM")
        if i == 0 and j == 0:
            ax.legend(frameon=False, fontsize=8, loc="lower left")
        ax.text(Rs[0], seul, "LRU seul", color=GRIS, va="bottom", fontsize=7.5)
fig.tight_layout()
fig.savefig(f"{O}/fig2-part-disque-contre-R.pdf")
fig.savefig(f"{O}/fig2-part-disque-contre-R.png", dpi=200)
print("ok")
