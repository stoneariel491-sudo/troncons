"""P1 : figures du mémoire, tirées des données commitées (hits-*.npz, fenetres-*.csv) et des traces extraites.
Usage : python -I -X utf8 figures_p1.py
Écrit genome/mimetisme/P1/figures/*.png et mesures/mimetisme/P1/figure-*.csv (données de chaque figure)."""
import csv
import math
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cache_p1 as cp  # noqa: E402

FIG = f"{cp.BASE}/genome/mimetisme/P1/figures"
C = {"lru": "#8a8a8a", "lfu:32": "#1f5fa8", "lfu:inf": "#c4572a", "etr": "#2e8b57"}
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150})


def fig_blocs():
    st = cp.charger_store("120b")
    fig, ax = plt.subplots(2, 2, figsize=(9, 5.4), sharex="col")
    lignes = []
    for j, g in enumerate(("prose-en", "wiki")):
        tr = f"gen-{g}"
        for pol, lab in (("lru", "LRU"), ("lfu:32", "LFU, demi-vie 32"), ("lfu:inf", "LFU sans décroissance"), ("etr", "horloge de couches")):
            h = st[cp.cle("120b", tr, 326, pol)]
            y = [h[i:i + 32].sum() / (32 * 144) for i in range(0, 256, 32)]
            ax[0, j].plot(range(8), y, "-o", ms=3, color=C[pol], label=lab)
            for i, v in enumerate(y):
                lignes.append((tr, pol, i, v))
        ax[0, j].set_title(f"génération {g}, 326 emplacements, cache vide", fontsize=9)
        ax[0, j].set_ylabel("taux de succès par bloc de 32 jetons")
        f = {"prose-en": "t120/t120b.prose-en.generation.jetons", "wiki": "t120/w120b.wiki.generation.jetons"}[g]
        toks = [int(x) for x in open(f"{cp.DONNEES}/{f}").read().split()][-256:]
        dist = [len(set(toks[i:i + 32])) for i in range(0, 256, 32)]
        ax[1, j].bar(range(8), dist, color="#555", width=0.6)
        ax[1, j].set_ylabel("jetons distincts par bloc")
        ax[1, j].set_xlabel("bloc de 32 jetons de la génération")
        for i, v in enumerate(dist):
            lignes.append((tr, "jetons_distincts", i, v))
    ax[0, 0].legend(frameon=False, fontsize=8)
    fig.suptitle("Les deux générations du 120b finissent en boucle : l'écart LFU − LRU y est un effet de la période de la boucle", fontsize=10)
    fig.tight_layout()
    fig.savefig(f"{FIG}/p1-blocs-generations.png")
    plt.close(fig)
    with open(f"{cp.SORTIE}/figure-blocs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["trace", "grandeur", "bloc", "valeur"])
        w.writerows(lignes)


def fig_fenetres():
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.6))
    for a, (m, cap) in zip(ax, (("120b", 326), ("20b", 217))):
        L = [l for l in csv.DictReader(open(f"{cp.SORTIE}/fenetres-{m}.csv", encoding="utf-8")) if int(l["capacite"]) == cap]
        x = np.array([float(l["lru"]) for l in L])
        y = np.array([float(l["lfu:32"]) for l in L])
        yi = np.array([float(l["lfu:inf"]) for l in L])
        a.plot([x.min() - .02, x.max() + .02], [x.min() - .02, x.max() + .02], color="#999", lw=0.8)
        a.scatter(x, yi, s=14, color=C["lfu:inf"], label="LFU sans décroissance", alpha=.8)
        a.scatter(x, y, s=14, color=C["lfu:32"], label="LFU, demi-vie 32", alpha=.9)
        a.set_xlabel("succès du LRU sur la fenêtre")
        a.set_ylabel("succès de la politique")
        a.set_title(f"{m}, {cap} emplacements, {len(L)} fenêtres froides de 256 jetons")
    ax[0].legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(f"{FIG}/p1-fenetres-froides.png")
    plt.close(fig)


def usage_blocs(G, bloc=32):
    T = G.shape[0]
    nb = T // bloc
    NN = int(G.shape[1] * (G.max() // G.shape[1] + 1)) if False else 36 * 128
    M = np.zeros((nb, NN))
    for b in range(nb):
        ids = G[b * bloc:(b + 1) * bloc].reshape(-1)
        np.add.at(M[b], ids, 1.0)
    return M


def fig_topologie():
    fig, ax = plt.subplots(2, 2, figsize=(9, 7.2))
    lignes = []
    for j, g in enumerate(("wiki", "prose-en")):
        Gr, _ = cp.lire("120b", g, "lecture")
        Gg, _ = cp.lire("120b", g, "generation")
        G = np.concatenate([Gr, Gg])
        nr = len(Gr) // 32
        M = usage_blocs(G)
        Mn = M / np.linalg.norm(M, axis=1, keepdims=True)
        S = Mn @ Mn.T
        im = ax[0, j].imshow(S, cmap="viridis", vmin=0.3, vmax=1)
        ax[0, j].axvline(nr - .5, color="w", lw=.8)
        ax[0, j].axhline(nr - .5, color="w", lw=.8)
        ax[0, j].set_title(f"{g} : similarité cosinus des usages d'experts,\nblocs de 32 jetons (lecture puis génération)")
        fig.colorbar(im, ax=ax[0, j], shrink=.8)
        X = Mn - Mn.mean(axis=0)
        U, s, Vt = np.linalg.svd(X, full_matrices=False)
        P = U[:, :2] * s[:2]
        part = s ** 2 / (s ** 2).sum()
        t = np.arange(len(P))
        sc = ax[1, j].scatter(P[:nr, 0], P[:nr, 1], c=t[:nr], cmap="Blues", s=22, edgecolor="none")
        ax[1, j].scatter(P[nr:, 0], P[nr:, 1], c="#c4572a", s=22, marker="s", label="génération")
        ax[1, j].plot(P[:, 0], P[:, 1], color="#bbb", lw=.5, zorder=0)
        ax[1, j].set_title(f"plan principal ({100 * part[0]:.0f} % et {100 * part[1]:.0f} % de la variance)", fontsize=9)
        ax[1, j].set_xlabel("axe 1")
        ax[1, j].set_ylabel("axe 2")
        for i in range(len(P)):
            lignes.append((g, i, "generation" if i >= nr else "lecture", P[i, 0], P[i, 1]))
    ax[1, 0].legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(f"{FIG}/p1-topologie-usages.png")
    plt.close(fig)
    with open(f"{cp.SORTIE}/figure-topologie.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["genre", "bloc", "phase", "axe1", "axe2"])
        w.writerows(lignes)


if __name__ == "__main__":
    cp.baisser_priorite()
    os.makedirs(FIG, exist_ok=True)
    fig_blocs()
    fig_fenetres()
    fig_topologie()
    print("figures écrites")
