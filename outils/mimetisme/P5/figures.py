"""P5 : figures vraies, tirees des donnees commitees (CSV ecrits a cote). Sorties : mesures/mimetisme/P5/figures/.

  python -I -X utf8 figures.py spectre   [--couche 8 --expert 0 --lignes 32]   (eigh de H : ~1 min, 2 fils)
  python -I -X utf8 figures.py paysage                                         (toy n = 10, rapide)
  python -I -X utf8 figures.py gains                                           (lit etape1/gains-d1.csv)
  python -I -X utf8 figures.py delta                                           (lit etape1/delta-*.json)
"""
import argparse
import csv
import glob
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ICI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ICI, "..", "..", "..", "mesures", "mimetisme", "P5", "figures")
ET1 = os.path.join(ICI, "..", "..", "..", "mesures", "mimetisme", "P5", "etape1")
os.makedirs(OUT, exist_ok=True)

COUL = {"frontiere": "#9a9a9a", "babai": "#2b4c7e", "cd": "#e07b00", "pt": "#a1222b", "gibbs": "#2a7f62"}
NOMS = {"frontiere": "frontière", "babai": "Babai (déployé)", "cd": "descente cyclique", "pt": "échange de répliques"}
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.8,
                     "figure.dpi": 150, "savefig.bbox": "tight", "font.family": "DejaVu Sans"})


def enreg(fig, nom):
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(OUT, f"{nom}.{ext}"))
    plt.close(fig)


def spectre(a):
    import etape1 as E1
    import p5lib as P
    syn = P.syn
    rng = np.random.default_rng(1)
    M = E1.matrices(a.couche, a.expert, a.damp)
    Wq, ex, codes = E1.poids_synthetiques(a.lignes, rng)
    S = np.repeat(syn.echelle(ex), 32, axis=-1)
    sf = syn.sym_frontiere(codes)
    ell = syn.longueurs(np.bincount(sf.ravel(), minlength=8).astype(np.float64))
    Qs = {"frontiere": P.sym_vers_niveau(sf)}
    Qs["babai"] = P.sym_vers_niveau(syn.choisir(Wq, ex, E1.CEN, M["Htr"], 0.0, ell))
    Qs["cd"], _ = P.pt(M["Htr"], Wq, S, E1.C8, ell, 0.0, Qs["babai"], np.array([1.0]), 0, trempe=30, seed=1)
    d = Wq - E1.C8[Qs["babai"]] * S
    eb = float(np.einsum("ij,jk,ik->", d, M["Htr"], d, optimize=True)) / d.size
    Qs["pt"], _ = P.pt(M["Htr"], Wq, S, E1.C8, ell, 0.0, Qs["babai"], E1.temperatures(eb, 8, 0.02, 1.0), a.sweeps,
                       every=1, trempe=30, seed=1)
    lam, U = np.linalg.eigh(M["Htr"])
    he = np.einsum("ik,ij,jk->k", U, M["He"], U, optimize=True)      # u_k^T H_eval u_k
    hc = np.einsum("ik,ij,jk->k", U, M["Hc"], U, optimize=True)      # u_k^T H_calib u_k
    den_e = float(np.einsum("ij,jk,ik->", Wq, M["He"], Wq, optimize=True))
    den_t = float(np.einsum("ij,jk,ik->", Wq, M["Htr"], Wq, optimize=True))
    ordre = np.argsort(lam)[::-1]
    # 14 groupes de directions, du haut du spectre vers le bas (effectifs egaux)
    groupes = np.array_split(ordre, 14)
    lignes = []
    for nom, Q in Qs.items():
        dW = Wq - E1.C8[Q] * S
        c = dW @ U                                                # coordonnees de l'erreur dans la base propre
        e_k = (c * c).sum(axis=0)
        for gi, g in enumerate(groupes):
            lignes.append(dict(methode=nom, groupe=gi, lam_moy=float(lam[g].mean()), n_dir=len(g),
                               part_train=float((e_k[g] * lam[g]).sum() / den_t),
                               part_calib=float((e_k[g] * hc[g]).sum() / float(np.einsum("ij,jk,ik->", Wq, M["Hc"], Wq, optimize=True))),
                               part_eval=float((e_k[g] * he[g]).sum() / den_e), energie_poids=float(e_k[g].sum() / (Wq * Wq).sum())))
    with open(os.path.join(OUT, "spectre-erreur.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0].keys()))
        w.writeheader()
        w.writerows(lignes)
    fig, ax = plt.subplots(1, 3, figsize=(10.5, 3.1), sharex=True)
    xs = np.arange(14)
    for j, (cle, titre) in enumerate((("energie_poids", "énergie de l'erreur sur les poids"),
                                      ("part_train", "erreur de sortie vue par H d'entraînement"),
                                      ("part_eval", "erreur de sortie vue par H tenu à l'écart"))):
        for nom in ("frontiere", "babai", "cd", "pt"):
            ys = [l[cle] for l in lignes if l["methode"] == nom]
            ax[j].plot(xs, ys, "-o", ms=3, lw=1.2, color=COUL[nom], label=NOMS[nom])
        ax[j].set_title(titre, fontsize=8.5)
        ax[j].set_yscale("log")
    fig.supxlabel("14 groupes de directions propres de H, du haut du spectre (0) vers le bas (13) ; les groupes 7 à 13 sont dans le noyau de la calibration", fontsize=8)
    ax[0].set_ylabel("part de l'énergie (poids ou sortie)")
    ax[0].legend(frameon=False, fontsize=7.5)
    fig.suptitle(f"Où l'erreur est déplacée : couche {a.couche}, expert {a.expert}, δ = {a.damp}", fontsize=9.5, y=1.03)
    enreg(fig, "spectre-erreur")
    print("ok spectre", lam[ordre][[0, 767, 2879]], "he/hc moyens par groupe:",
          [round(float(he[g].sum() / max(hc[g].sum(), 1e-300)), 2) for g in groupes])


def paysage(a):
    import p5lib as P
    import temoins as T
    from scipy import linalg
    res = json.load(open(os.path.join(ICI, "..", "..", "..", "mesures", "mimetisme", "P5", "temoins-passe2-instances.json")))
    cand = [r for r in res if not r["babai_ok"]]
    # l'instance ou l'ecart de Babai est le plus grand en valeur relative et reste lisible (energie optimale > 5)
    cand = [r for r in cand if r["eopt"] > 5]
    r = max(cand, key=lambda r: (r["eb"] - r["eopt"]) / r["eopt"])
    i = r["i"]
    rng = np.random.default_rng(1000 + i)
    H, w = T.instance(rng)
    lev = np.tile(T.NIV, (T.N, 1))
    L = linalg.cholesky(H, lower=True)
    eopt, idx, _ = P.enum_best(L, lev, w, np.zeros((T.N, T.K)), False)
    qb = P.babai_generique(H, w, lev, np.zeros((T.N, T.K)))
    diff = np.nonzero(qb != idx)[0]
    # deux coordonnees parmi celles qui different, les plus eloignees de Babai
    a_, b_ = diff[:2] if len(diff) >= 2 else (diff[0], (diff[0] + 1) % T.N)
    carte = np.zeros((T.K, T.K))
    for u in range(T.K):
        for v in range(T.K):
            q = qb.copy(); q[a_] = u; q[b_] = v
            carte[u, v] = P.energie(H, w, np.ones(T.N), T.NIV, np.zeros(T.K), 0.0, q.astype(np.uint8))[0]
    q2 = idx.copy().astype(np.int64); q2[a_] = idx[a_]; q2[b_] = idx[b_]
    with open(os.path.join(OUT, "paysage-toy.csv"), "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["instance", i, "coord_a", int(a_), "coord_b", int(b_), "E_babai", r["eb"], "E_optimum", float(eopt), "cond", r["cond"]])
        for u in range(T.K):
            wr.writerow([f"niveau_a={u}"] + [float(x) for x in carte[u]])
    fig, ax = plt.subplots(figsize=(3.6, 3.2))
    im = ax.imshow(np.log10(carte), origin="lower", cmap="magma_r")
    ax.plot(qb[b_], qb[a_], "o", color="#2b4c7e", ms=9, mfc="none", mew=2, label="Babai")
    ax.plot(idx[b_], idx[a_], "*", color="#e07b00", ms=12, label="optimum exact (force brute)")
    ax.set_xlabel(f"niveau de la coordonnée {b_}"); ax.set_ylabel(f"niveau de la coordonnée {a_}")
    ax.set_xticks(range(T.K)); ax.set_yticks(range(T.K))
    ax.set_title(f"Coupe 2D d'un paysage à {T.K}^{T.N} états\n(autres coordonnées figées à Babai)", fontsize=8.5)
    ax.legend(frameon=True, fontsize=6.5, loc="upper right")
    fig.colorbar(im, ax=ax, label="log10 E", shrink=0.8)
    enreg(fig, "paysage-toy")
    print("ok paysage", i, r["eb"], float(eopt))


def gains(a):
    rows = list(csv.DictReader(open(os.path.join(ET1, "gains-d1.csv"), encoding="utf-8")))
    inst = sorted({(int(r["couche"]), int(r["expert"])) for r in rows})
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.2), sharey=True)
    for j, meth in enumerate(("cd", "pt")):
        for k, (cle, nom, al) in enumerate((("gain_calib", "calibration (H brut)", 0.35), ("gain_train", "objectif optimisé (H amorti)", 0.65), ("gain_eval", "évaluation tenue à l'écart", 1.0))):
            ys = []
            for (l, e) in inst:
                cand = [float(r[cle]) for r in rows if int(r["couche"]) == l and int(r["expert"]) == e and r["methode"] == meth and r["comparable"] == "True"]
                ys.append(100 * max(cand) if cand else np.nan)
            ax[j].bar(np.arange(len(inst)) + (k - 1) * 0.27, ys, 0.26, color=COUL[meth], alpha=al, label=nom)
        ax[j].axhline(10, color="k", lw=0.8, ls="--"); ax[j].text(-0.45, 10.8, "seuil de succès 10 %", ha="left", fontsize=7)
        ax[j].axhline(3, color="k", lw=0.8, ls=":"); ax[j].text(-0.45, 0.4, "mort sous 3 %", ha="left", fontsize=7, color="#555")
        ax[j].set_xticks(range(len(inst))); ax[j].set_xticklabels([f"L{l}\nE{e}" for l, e in inst])
        ax[j].set_title(NOMS[meth] + " contre Babai (poids synthétiques, H réel)", fontsize=8.5)
    ax[0].set_ylabel("baisse de l'erreur (%) à débit égal")
    ax[0].legend(frameon=False, fontsize=7)
    enreg(fig, "gains-etape1")
    print("ok gains")


def delta(a):
    fs = sorted(glob.glob(os.path.join(ET1, "L??-E??-d*.json")))
    data = {}
    for f in fs:
        j = json.load(open(f, encoding="utf-8"))
        d = j["damp"]
        for r in j["lignes_res"]:
            if r["lam"] == 0.0 and r["methode"] in ("babai", "cd", "pt"):
                data.setdefault((j["couche"], j["expert"]), {}).setdefault(r["methode"], {})[d] = (r["err_eval"], r["bits_H0"])
    deltas = sorted({d for v in data.values() for m in v.values() for d in m})
    fig, ax = plt.subplots(figsize=(4.6, 3.3))
    for meth in ("babai", "cd", "pt"):
        ys, ds = [], []
        for d in deltas:
            vals = [v[meth][d][0] / v["babai"][1.0][0] for v in data.values() if meth in v and d in v[meth] and 1.0 in v["babai"]]
            if vals:
                ys.append(np.mean(vals)); ds.append(d)
        if ys:
            ax.plot(ds, ys, "-o", color=COUL[meth], label=NOMS[meth], ms=4)
    ax.set_xscale("log"); ax.set_xlabel("amortissement δ (× moyenne de diag H)"); ax.set_ylabel("erreur d'évaluation / Babai à δ = 1")
    ax.legend(frameon=False, fontsize=7.5)
    enreg(fig, "delta")
    print("ok delta")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("quoi", choices=["spectre", "paysage", "gains", "delta"])
    ap.add_argument("--couche", type=int, default=8)
    ap.add_argument("--expert", type=int, default=0)
    ap.add_argument("--lignes", type=int, default=32)
    ap.add_argument("--damp", type=float, default=1.0)
    ap.add_argument("--sweeps", type=int, default=40)
    a = ap.parse_args()
    {"spectre": spectre, "paysage": paysage, "gains": gains, "delta": delta}[a.quoi](a)
