"""Données des figures de la garde tropicale (Tome III), tirées des journaux commités, et la coupe
réelle du routeur (régions top-4 et bande de garde) rendue par matplotlib.

Écrit sous mesures/pistes/tropicale/figures/ :
  fig-courbe.csv          (c, b) de la garde pour : toutes les bascules, racines, secondaires, min(A,B)
  fig-par-couche.csv      b(τ₁₀) par couche : toutes, racines, secondaires ; σ de δ (robuste)
  fig-survie.csv          P(m > x) par couche (couches 0, 8, 16, 23), et la loi exponentielle de même moyenne
  fig-loi-bascule.csv     P(bascule | m) par classe logarithmique, trois groupes de couches, et Φ(−m/σ̂)
  fig-extrapolation.csv   b(τ₁₀) prédit contre le facteur s (toutes : gauss, empirique ; racines : empirique)
  coupe-routeur-c<ℓ>-<fr|en>.png les régions top-4 du routeur de la couche ℓ dans le plan de ses deux premières
                          directions singulières (vue large et agrandissement autour d'un sommet)

Usage : python -I -X utf8 figures.py [--sans-coupe]
"""

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import routage as R  # noqa: E402

import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

FIG = R.SORTIE / "figures"
GGUF = Path("~/dev/modeles/gguf/gpt-oss-20b-MXFP4.gguf")


def ecrire(nom, entete, lignes):
    with open(FIG / nom, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(entete)
        w.writerows(lignes)


def courbe_dense(m, sel, parts):
    """b à chaque part de cellules donnée (τ = quantile des marges de toutes les cellules)."""
    s = np.sort(m.ravel())
    out = []
    for c in parts:
        k = int(round(c * s.size))
        t = s[min(k, s.size - 1)] if k < s.size else np.inf
        out.append(float(np.mean(m[sel] < t)))
    return out


def donnees():
    ea, ma = R.lire(R.A)
    eb, mb = R.lire(R.B)
    L, N = mb.shape
    bas = R.bascules(ea, eb)
    avant = np.zeros_like(bas)
    avant[1:] = np.cumsum(bas, axis=0)[:-1] > 0
    prim, sec = bas & ~avant, bas & avant
    parts = np.concatenate([np.linspace(0, 0.02, 21), np.linspace(0.025, 0.5, 96)])
    mo = np.minimum(ma, mb)
    cols = [courbe_dense(mb, bas, parts), courbe_dense(mb, prim, parts), courbe_dense(mb, sec, parts),
            courbe_dense(mo, bas, parts)]
    ecrire("fig-courbe.csv", ["c", "toutes", "racines", "secondaires", "oracle"],
           [[f"{c:.4f}", *[f"{col[i]:.4f}" for col in cols]] for i, c in enumerate(parts)])

    t10 = R.tau_decile(mb)
    sig = mb < t10
    lois = json.loads((R.SORTIE / "lois-resume.json").read_text(encoding="utf-8"))["loi_bascule"]
    ecrire("fig-par-couche.csv", ["couche", "toutes", "racines", "secondaires", "sigma_delta", "taux_bascule"],
           [[l, f"{sig[l][bas[l]].mean():.4f}", f"{sig[l][prim[l]].mean():.4f}",
             (f"{sig[l][sec[l]].mean():.4f}" if sec[l].any() else "nan"),
             f"{lois[str(l)]['sigma_delta_robuste']:.5f}", f"{bas[l].mean():.5f}"] for l in range(L)])

    xs = np.linspace(0, 0.8, 81)
    lignes = []
    for x in xs:
        r = [f"{x:.3f}"]
        for l in (0, 8, 16, 23):
            r += [f"{np.mean(mb[l] > x):.6f}", f"{np.exp(-x / mb[l].astype(np.float64).mean()):.6f}"]
        lignes.append(r)
    ecrire("fig-survie.csv", ["x", "s0", "e0", "s8", "e8", "s16", "e16", "s23", "e23"], lignes)

    bords = np.logspace(-4.5, 0, 19)
    centres = np.sqrt(bords[:-1] * bords[1:])
    groupes = {"g1": range(0, 8), "g2": range(8, 16), "g3": range(16, 24)}
    # δ empirique du groupe : m_A − m_B sur les cellules sans bascule à grande marge (m_B > 0,1)
    deltas = {g: np.sort(np.concatenate([(ma[l] - mb[l]).astype(np.float64)[(~bas[l]) & (mb[l] > 0.1)] for l in ls]))
              for g, ls in groupes.items()}
    lignes = []
    for i, cm in enumerate(centres):
        r = [f"{cm:.4e}"]
        for g, ls in groupes.items():
            m = np.concatenate([mb[l] for l in ls]).astype(np.float64)
            b = np.concatenate([bas[l] for l in ls])
            s = (m >= bords[i]) & (m < bords[i + 1])
            p = b[s].mean() if s.sum() >= 20 else np.nan
            sig_g = np.median([lois[str(l)]["sigma_phi"] for l in ls])
            emp = np.searchsorted(deltas[g], -cm, side="left") / deltas[g].size
            r += [f"{p:.5f}" if np.isfinite(p) else "nan", int(s.sum()), f"{stats.norm.cdf(-cm / sig_g):.5f}", f"{emp:.5f}"]
        lignes.append(r)
    ecrire("fig-loi-bascule.csv", ["m", "p1", "n1", "phi1", "emp1", "p2", "n2", "phi2", "emp2", "p3", "n3", "phi3", "emp3"], lignes)

    ex = json.loads((R.SORTIE / "lois-resume.json").read_text(encoding="utf-8"))["extrapolation"]
    ra = {str(e["facteur_s"]): e["b_tau10_racines_predit"]
          for e in json.loads((R.SORTIE / "cascades.json").read_text(encoding="utf-8"))["extrapolation_racines_empirique"]}
    lignes = []
    for s in ("0.5", "1.0", "1.5", "2.0", "3.0", "5.0", "10.0"):
        lignes.append([s, f"{ex[s]['b_tau10_gauss']:.4f}", f"{ex[s]['b_tau10_empirique']:.4f}", f"{ra[s]:.4f}"])
    ecrire("fig-extrapolation.csv", ["s", "toutes_gauss", "toutes_empirique", "racines_empirique"], lignes)
    return t10


def coupe(couche, t10):
    """Régions top-4 du routeur réel dans un plan : h = a u + b v, u et v les deux premières directions
    singulières à droite de W_r ; z = W_r h + b_r. Vue large, et agrandissement autour du point du plan où
    la marge est la plus petite près du centre. La bande de garde est {m < τ₁₀}, τ₁₀ des journaux."""
    sys.path.insert(0, str(R.DEPOT / "mesures" / "moteur" / "epreuve-J1"))
    from decodeur_s4 import Gguf  # lecteur GGUF de l'épreuve J1 (lecture de quelques centaines de Kio)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap

    g = Gguf(str(GGUF))
    p = f"blk.{couche}."
    tw, tb = g.tenseurs[p + "ffn_gate_inp.weight"], g.tenseurs[p + "ffn_gate_inp.bias"]
    assert tw["type"] == 0 and tb["type"] == 0
    W = np.frombuffer(g.lire(tw["absolu"], tw["octets"]), "<f4").astype(np.float64).reshape(32, -1)
    bvec = np.frombuffer(g.lire(tb["absolu"], tb["octets"]), "<f4").astype(np.float64)
    U, S, Vt = np.linalg.svd(W, full_matrices=False)

    def carte(a0, a1, b0, b1, n):
        a = np.linspace(a0, a1, n)
        b = np.linspace(b0, b1, n)
        A_, B_ = np.meshgrid(a, b)
        Z = A_[..., None] * (S[0] * U[:, 0]) + B_[..., None] * (S[1] * U[:, 1]) + bvec
        o = np.sort(Z, axis=2)
        marge = o[..., -4] - o[..., -5]
        top = np.argsort(-Z, axis=2)[..., :4]
        cle = np.sort(top, axis=2) @ np.array([32 ** 3, 32 ** 2, 32, 1])
        return a, b, cle, marge

    R_ = 4.0 / S[1]  # demi-largeur : 4 unités de logit le long de la seconde direction
    a, b, cle, marge = carte(-R_ * S[1] / S[0], R_ * S[1] / S[0], -R_, R_, 900)
    uniq, ids = np.unique(cle, return_inverse=True)
    ids = ids.reshape(cle.shape)
    rng = np.random.default_rng(7)
    base = np.array([[0x1F, 0x5C, 0x99], [0x2E, 0x8B, 0x57], [0xD6, 0x89, 0x10], [0x8E, 0x44, 0xAD],
                     [0x6C, 0x7A, 0x89], [0x1F, 0x7A, 0x8C], [0x8B, 0x5A, 0x2B], [0xC0, 0x39, 0x2B]]) / 255
    pal = np.array([1 - 0.22 * (1 - base[rng.integers(len(base))]) for _ in range(len(uniq))])
    cmap = ListedColormap(pal)
    # l agrandissement se centre sur un sommet du complexe : le pixel le plus proche du point (−0,2 ; 0,7)
    # du plan (en logits) dont le voisinage 7 × 7 touche au moins trois régions ; ce point
    # est au milieu de la grappe de petites régions de la vue large (choix de cadrage, pas de mesure)
    n_ = ids.shape[0]
    pad = np.pad(ids, 3, mode="edge")
    fen = np.stack([pad[i:i + n_, j:j + n_] for i in range(7) for j in range(7)], axis=-1)
    fen_s = np.sort(fen, axis=-1)
    nreg = 1 + np.sum(fen_s[..., 1:] != fen_s[..., :-1], axis=-1)
    jj, ii = np.meshgrid(np.arange(n_), np.arange(n_))
    d2 = (a[jj] * S[0] + 0.2) ** 2 + (b[ii] * S[1] - 0.7) ** 2
    d2[nreg < 3] = np.inf
    ci, cj = np.unravel_index(np.argmin(d2), d2.shape)
    ac, bc = a[cj], b[ci]
    zoom = 0.35 / S[1]  # demi-largeur de l agrandissement : 0,35 unité de logit
    a2, b2, cle2, marge2 = carte(ac - zoom * S[1] / S[0], ac + zoom * S[1] / S[0], bc - zoom, bc + zoom, 700)
    ids2 = np.searchsorted(uniq, cle2)
    ids2 = np.where(ids2 < len(uniq), ids2, 0)

    # la police du mémoire (Libertinus, livrée avec MiKTeX), pour que la coupe parle comme les graphes
    from matplotlib import font_manager
    polices = Path("~/AppData/Local/Programs/MiKTeX/fonts/opentype/public/libertinus-fonts")
    famille = "serif"
    for nom in ("LibertinusSerif-Regular.otf", "LibertinusSerif-Italic.otf", "LibertinusMath-Regular.otf"):
        if (polices / nom).exists():
            font_manager.fontManager.addfont(str(polices / nom))
            famille = "Libertinus Serif"
    plt.rcParams.update({"font.family": famille, "font.size": 8.5, "axes.edgecolor": "#555555",
                         "mathtext.fontset": "custom", "mathtext.rm": famille, "mathtext.it": f"{famille}:italic"})
    sorties = []
    for langue, titres in (("fr", ("vue large", "agrandissement")), ("en", ("wide view", "close-up"))):
        sorties.append(dessiner(plt, ListedColormap, cmap, uniq, S, t10, (a, b, ids, marge), (a2, b2, ids2, marge2),
                                (ac, bc, zoom), titres, FIG / f"coupe-routeur-c{couche}-{langue}.png"))
    info = {"couche": couche, "sigma1": float(S[0]), "sigma2": float(S[1]), "regions_vue_large": int(len(np.unique(ids))),
            "part_bande_vue_large": float(np.mean(marge < t10)), "part_bande_agrandissement": float(np.mean(marge2 < t10)),
            "tau10": t10, "police": famille,
            "images": [str(s.relative_to(R.DEPOT)).replace("\\", "/") for s in sorties]}
    return info


def dessiner(plt, ListedColormap, cmap, uniq, S, t10, large, gros, cadre, titres, sortie):
    a, b, ids, marge = large
    a2, b2, ids2, marge2 = gros
    ac, bc, zoom = cadre
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.5), dpi=220)
    for ax, aa, bb, ii, mm, titre in ((axs[0], a, b, ids, marge, titres[0]), (axs[1], a2, b2, ids2, marge2, titres[1])):
        ax.imshow(ii, origin="lower", extent=(aa[0] * S[0], aa[-1] * S[0], bb[0] * S[1], bb[-1] * S[1]),
                  cmap=cmap, vmin=0, vmax=len(uniq) - 1, interpolation="nearest", aspect="equal")
        bande = np.ma.masked_where(mm >= t10, np.ones_like(mm))
        ax.imshow(bande, origin="lower", extent=(aa[0] * S[0], aa[-1] * S[0], bb[0] * S[1], bb[-1] * S[1]),
                  cmap=ListedColormap(["#C0392B"]), alpha=0.6, interpolation="nearest", aspect="equal")
        frontiere = (np.diff(ii, axis=0, prepend=ii[:1]) != 0) | (np.diff(ii, axis=1, prepend=ii[:, :1]) != 0)
        ax.contour(aa * S[0], bb * S[1], frontiere.astype(float), levels=[0.5], colors="#1A1A1A", linewidths=0.5)
        ax.set_xlabel(r"$\sigma_1 a$ (logit)")
        ax.set_ylabel(r"$\sigma_2 b$ (logit)")
        ax.set_title(titre, fontsize=9)
        ax.tick_params(labelsize=7)
    axs[0].add_patch(plt.Rectangle(((ac - zoom * S[1] / S[0]) * S[0], (bc - zoom) * S[1]), 2 * zoom * S[1], 2 * zoom * S[1],
                                   fill=False, edgecolor="#C0392B", linewidth=0.9))
    fig.tight_layout()
    fig.savefig(sortie, dpi=220)
    plt.close(fig)
    return sortie


def main():
    R.sous_la_normale()
    R.attendre_calme()
    FIG.mkdir(parents=True, exist_ok=True)
    t10 = donnees()
    res = {"outil": "outils/pistes/tropicale/figures.py", "tau10": t10}
    if "--sans-coupe" not in sys.argv:
        R.attendre_calme()
        res["coupes"] = [coupe(l, t10) for l in (12,)]
    (FIG / "figures.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
