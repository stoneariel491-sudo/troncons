"""Ce que 05 § 3.1 dit non mesuré, lu sur les mêmes journaux (seuil-declare.md § 5) :

1. la loi de la marge par couche (quantiles, densité près de zéro, pente log-log, ajustements) ;
2. la corrélation des marges d'une couche à la suivante, même position (Spearman, permutations) ;
3. la loi de bascule P(bascule | marge) par couche, la perturbation de l'écart δ = m_A − m_B, et
   l'extrapolation de b(τ₁₀) quand la perturbation grandit (modèle, dit tel) ;
4. la propagation : P(bascule en ℓ + 1 | bascule en ℓ, marge en ℓ + 1) ;
5. la marge comme priorité de préchargement, lectures P1 (couche suivante) et P2 (jeton suivant).

Usage : python -I -X utf8 lois.py
"""

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import routage as R  # noqa: E402

import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

GRAINE = 20261021
N_PERM = 999


def ecrire(nom, entete, lignes):
    with open(R.SORTIE / nom, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(entete)
        w.writerows(lignes)


def loi_marge(mb):
    lignes = []
    resume = []
    for l in range(mb.shape[0]):
        m = mb[l].astype(np.float64)
        q = np.quantile(m, [0.01, 0.1, 0.5, 0.9, 0.99])
        # densité près de zéro, par deux largeurs ; pente de log P(m < τ) contre log τ sur [1e-4, 1e-2]
        f1 = np.mean(m < 1e-3) / 1e-3
        f2 = np.mean(m < 1e-2) / 1e-2
        ts = np.logspace(-4, -2, 9)
        ps = np.array([np.mean(m < t) for t in ts])
        ok = ps > 0
        pente = float(np.polyfit(np.log(ts[ok]), np.log(ps[ok]), 1)[0]) if ok.sum() >= 3 else float("nan")
        moy = m.mean()
        ks_exp = stats.kstest(m, "expon", args=(0, moy)).statistic
        a, _, sc = stats.gamma.fit(m, floc=0)
        ks_gam = stats.kstest(m, "gamma", args=(a, 0, sc)).statistic
        sh = np.sqrt(np.mean(m ** 2))
        ks_hn = stats.kstest(m, "halfnorm", args=(0, sh)).statistic
        mp = m[m > 0]
        s_ln, _, sc_ln = stats.lognorm.fit(mp, floc=0)
        ks_ln = stats.kstest(mp, "lognorm", args=(s_ln, 0, sc_ln)).statistic
        lignes.append([l, *[f"{x:.6e}" for x in q], f"{moy:.6e}", f"{f1:.4f}", f"{f2:.4f}", f"{1 / moy:.4f}",
                       f"{pente:.4f}", f"{ks_exp:.4f}", f"{a:.4f}", f"{sc:.6e}", f"{ks_gam:.4f}", f"{ks_hn:.4f}", f"{ks_ln:.4f}"])
        resume.append({"couche": l, "mediane": q[2], "moyenne": moy, "densite_0_1e3": f1, "un_sur_moyenne": 1 / moy,
                       "pente_loglog": pente, "ks": {"exp": ks_exp, "gamma": ks_gam, "demi_normale": ks_hn, "lognormale": ks_ln},
                       "gamma_forme": a})
    ecrire("loi-marge-par-couche.csv",
           ["couche", "q01", "q10", "q50", "q90", "q99", "moyenne", "densite_sous_1e-3", "densite_sous_1e-2",
            "un_sur_moyenne", "pente_loglog_1e-4_1e-2", "ks_exponentielle", "gamma_forme", "gamma_echelle",
            "ks_gamma", "ks_demi_normale", "ks_lognormale"], lignes)
    return resume


def correlation_couches(mb, rng):
    L = mb.shape[0]
    lignes, res = [], []
    t10 = R.tau_decile(mb)
    for l in range(L - 1):
        x, y = mb[l], mb[l + 1]
        rho = stats.spearmanr(x, y).statistic
        nul = np.array([stats.spearmanr(x, rng.permutation(y)).statistic for _ in range(N_PERM // 9)])  # 111 tirages par couple
        bas_x, bas_y = x < t10, y < t10
        p_cond = float(bas_y[bas_x].mean()) if bas_x.any() else float("nan")
        lignes.append([l, l + 1, f"{rho:.4f}", f"{np.quantile(np.abs(nul), 0.999):.4f}",
                       f"{np.corrcoef(np.log(x + 1e-6), np.log(y + 1e-6))[0, 1]:.4f}",
                       f"{bas_y.mean():.4f}", f"{p_cond:.4f}", f"{p_cond / bas_y.mean():.3f}"])
        res.append({"couches": [l, l + 1], "spearman": rho, "nul_999e_centile_abs": float(np.quantile(np.abs(nul), 0.999)),
                    "p_sous_tau10_sachant_sous_tau10_avant": p_cond, "levier": p_cond / bas_y.mean()})
    # le chiffre groupé, avec 999 permutations (positions permutées dans chaque couche suivante)
    X = np.concatenate([mb[l] for l in range(L - 1)])
    Y = np.concatenate([mb[l + 1] for l in range(L - 1)])
    rho_g = stats.spearmanr(X, Y).statistic
    rx, ry = stats.rankdata(X), None
    nul_g = []
    for _ in range(N_PERM):
        Yp = np.concatenate([rng.permutation(mb[l + 1]) for l in range(L - 1)])
        nul_g.append(np.corrcoef(rx, stats.rankdata(Yp))[0, 1])
    ecrire("correlation-couches.csv",
           ["couche", "couche_suivante", "spearman", "nul_999e_centile_abs_111_tirages", "pearson_log",
            "p_sous_tau10", "p_sous_tau10_sachant_sous_tau10_avant", "levier"], lignes)
    return {"par_couple": res, "spearman_groupe": float(rho_g),
            "nul_groupe_999e_centile_abs": float(np.quantile(np.abs(nul_g), 0.999)), "permutations": N_PERM}


def loi_bascule(ma, mb, bas):
    """P(bascule | marge de B) par classes logarithmiques ; δ = m_A − m_B sur les cellules sans bascule
    à grande marge (m_B > 0,1, où la troncature par la bascule est négligeable) ; ajustement d'un σ par
    couche (vraisemblance de P = Φ(−m/σ), la forme dérivée, et de 2Φ(−m/σ), la forme déclarée)."""
    L = mb.shape[0]
    bords = np.concatenate([[0.0], np.logspace(-5, 0, 21), [np.inf]])
    lignes_b, lignes_s, sig = [], [], {}
    for l in range(L):
        m, b = mb[l].astype(np.float64), bas[l]
        idx = np.digitize(m, bords) - 1
        for k in range(len(bords) - 1):
            sel = idx == k
            if sel.any():
                lignes_b.append([l, f"{bords[k]:.3e}", f"{bords[k + 1]:.3e}", int(sel.sum()), int(b[sel].sum()),
                                 f"{b[sel].mean():.6f}"])
        d = (ma[l] - mb[l]).astype(np.float64)[(~b) & (mb[l] > 0.1)]
        s_rob = 1.4826 * np.median(np.abs(d - np.median(d)))
        best = {}
        for forme, fac in (("phi", 1.0), ("deux_phi", 2.0)):
            grid = np.logspace(-5, 0, 401)
            ll = []
            for s in grid:
                p = np.clip(fac * stats.norm.cdf(-m / s), 1e-12, 1 - 1e-12)
                ll.append(np.sum(np.where(b, np.log(p), np.log1p(-p))))
            ll = np.array(ll)
            best[forme] = (float(grid[ll.argmax()]), float(ll.max()))
        sig[l] = {"sigma_delta_robuste": s_rob, "ecart_type_delta": float(d.std()), "n_delta": int(d.size),
                  "kurtosis_delta": float(stats.kurtosis(d)),
                  "sigma_phi": best["phi"][0], "logv_phi": best["phi"][1],
                  "sigma_deux_phi": best["deux_phi"][0], "logv_deux_phi": best["deux_phi"][1],
                  "p_bascule_marge_sous_1e-4": float(b[m < 1e-4].mean()) if (m < 1e-4).any() else None,
                  "n_marge_sous_1e-4": int((m < 1e-4).sum())}
        lignes_s.append([l, f"{s_rob:.6e}", f"{d.std():.6e}", f"{stats.kurtosis(d):.3f}", int(d.size),
                         f"{best['phi'][0]:.6e}", f"{best['phi'][1]:.2f}", f"{best['deux_phi'][0]:.6e}", f"{best['deux_phi'][1]:.2f}",
                         sig[l]["p_bascule_marge_sous_1e-4"], sig[l]["n_marge_sous_1e-4"]])
    ecrire("loi-bascule-classes.csv", ["couche", "marge_de", "marge_a", "cellules", "bascules", "p_bascule"], lignes_b)
    ecrire("loi-bascule-sigma.csv", ["couche", "sigma_delta_robuste", "ecart_type_delta", "kurtosis_delta", "n_delta",
                                     "sigma_phi_mv", "logv_phi", "sigma_deux_phi_mv", "logv_deux_phi",
                                     "p_bascule_marge_sous_1e-4", "n_marge_sous_1e-4"], lignes_s)
    return sig


def extrapolation(ma, mb, bas, sig):
    """b(τ₁₀) prédit quand la perturbation de l'écart est multipliée par s, deux modèles :
    (g) gaussien, σ_ℓ du maximum de vraisemblance de Φ ; (e) forme empirique de δ (cellules sans bascule,
    m_B > 0,1), mise à l'échelle par s. La garde reste la marge de B, τ₁₀ global fixé par les marges."""
    L = mb.shape[0]
    t10 = R.tau_decile(mb)
    sous = mb < t10
    deltas = {l: np.sort((ma[l] - mb[l]).astype(np.float64)[(~bas[l]) & (mb[l] > 0.1)]) for l in range(L)}
    lignes, res = [], {}
    for s in (0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0, 20.0):
        att_g = tot_g = att_e = tot_e = 0.0
        for l in range(L):
            m = mb[l].astype(np.float64)
            pg = stats.norm.cdf(-m / (s * sig[l]["sigma_phi"]))
            dl = deltas[l]
            pe = np.searchsorted(dl, -m / s, side="left") / dl.size  # P(δ s < −m)
            att_g += pg[sous[l]].sum(); tot_g += pg.sum()
            att_e += pe[sous[l]].sum(); tot_e += pe.sum()
        n = mb.size
        lignes.append([s, f"{tot_g / n:.5f}", f"{att_g / tot_g:.4f}", f"{tot_e / n:.5f}", f"{att_e / tot_e:.4f}"])
        res[str(s)] = {"taux_bascule_gauss": tot_g / n, "b_tau10_gauss": att_g / tot_g,
                       "taux_bascule_empirique": tot_e / n, "b_tau10_empirique": att_e / tot_e}
    ecrire("extrapolation-garde.csv", ["facteur_s", "taux_bascule_predit_gauss", "b_tau10_gauss",
                                       "taux_bascule_predit_empirique", "b_tau10_empirique"], lignes)
    # validation à s = 1, par couche : bascules prédites contre comptées
    val = []
    for l in range(L):
        m = mb[l].astype(np.float64)
        pg = stats.norm.cdf(-m / sig[l]["sigma_phi"])
        dl = deltas[l]
        pe = np.searchsorted(dl, -m, side="left") / dl.size
        val.append([l, int(bas[l].sum()), f"{pg.sum():.1f}", f"{pe.sum():.1f}",
                    f"{(bas[l] & sous[l]).sum() / max(1, bas[l].sum()):.4f}",
                    f"{pg[sous[l]].sum() / pg.sum():.4f}", f"{pe[sous[l]].sum() / pe.sum():.4f}"])
    ecrire("extrapolation-validation.csv", ["couche", "bascules_comptees", "predites_gauss", "predites_empirique",
                                            "b_tau10_mesure", "b_tau10_gauss", "b_tau10_empirique"], val)
    return res


def propagation(mb, bas):
    """P(bascule en ℓ+1 | bascule en (ℓ, p)) contre le taux de base, par classe de marge en ℓ+1."""
    L = mb.shape[0]
    X = np.concatenate([bas[l] for l in range(L - 1)])
    Y = np.concatenate([bas[l + 1] for l in range(L - 1)])
    M = np.concatenate([mb[l + 1] for l in range(L - 1)])
    bords = [0, 1e-3, 1e-2, 3e-2, 1e-1, np.inf]
    lignes = []
    for a, b in zip(bords[:-1], bords[1:]):
        sel = (M >= a) & (M < b)
        p1 = Y[sel & X].mean() if (sel & X).any() else float("nan")
        p0 = Y[sel & ~X].mean() if (sel & ~X).any() else float("nan")
        lignes.append([a, b, int((sel & X).sum()), f"{p1:.4f}", int((sel & ~X).sum()), f"{p0:.4f}"])
    ecrire("propagation.csv", ["marge_suivante_de", "a", "n_bascule_avant", "p_bascule_sachant_bascule_avant",
                               "n_sans_bascule_avant", "p_bascule_sachant_rien_avant"], lignes)
    return {"p_bascule_sachant_bascule_avant": float(Y[X].mean()), "p_bascule_sachant_rien_avant": float(Y[~X].mean()),
            "n_bascule_avant": int(X.sum())}


def auc_et_nul(score, y, rng):
    a = R.auc(score, y)
    r = stats.rankdata(-np.asarray(score, dtype=np.float64))
    n1 = int(y.sum()); n0 = y.size - n1
    nul = []
    for _ in range(N_PERM):
        yp = rng.permutation(y)
        nul.append((r[yp].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))
    q = float(np.quantile(nul, 0.999))
    return {"auc": a, "nul_999e_centile": q, "permutations": N_PERM, "positifs": n1, "n": int(y.size),
            "priorite_utile": bool(a > 0.60 and a > q)}


def prechargement(ea, eb, mb, bas, rng):
    L, N = mb.shape
    # P1 : la marge en ℓ annonce-t-elle une bascule en ℓ + 1, même position ?
    S1 = np.concatenate([mb[l] for l in range(L - 1)])
    Y1 = np.concatenate([bas[l + 1] for l in range(L - 1)])
    S1ref = np.concatenate([mb[l + 1] for l in range(L - 1)])
    p1 = auc_et_nul(S1, Y1, rng)
    p1["reference_marge_de_la_couche_meme"] = R.auc(S1ref, Y1)
    # P2 : la marge de (ℓ, p) annonce-t-elle que p + 1 change d'ensemble à la couche ℓ (calcul B seul) ?
    pos = np.arange(N)
    dans = (pos % R.LONG) < (R.LONG - 1)  # p + 1 dans la même fenêtre
    change = np.any(eb[:, 1:, :] != eb[:, :-1, :], axis=2)  # (L, N−1)
    garde = np.zeros((L, N - 1), dtype=np.int8)
    for l in range(L):
        garde[l] = [len(set(eb[l, p].tolist()) & set(eb[l, p + 1].tolist())) for p in range(N - 1)]
    sel = dans[:-1]
    S2 = mb[:, :-1][:, sel].ravel()
    Y2 = change[:, sel].ravel()
    G2 = garde[:, sel].ravel()
    p2 = auc_et_nul(S2, Y2, rng)
    p2["part_ensembles_identiques"] = float(1 - Y2.mean())
    p2["experts_gardes_moyens"] = float(G2.mean())
    dec = np.quantile(S2, np.linspace(0, 1, 11))
    lignes = []
    for k in range(10):
        s = (S2 >= dec[k]) & (S2 <= dec[k + 1] if k == 9 else S2 < dec[k + 1])
        lignes.append([k + 1, f"{dec[k]:.4e}", f"{dec[k + 1]:.4e}", int(s.sum()), f"{1 - Y2[s].mean():.4f}", f"{G2[s].mean():.4f}"])
    ecrire("prechargement-jeton-suivant.csv", ["decile_marge", "de", "a", "n", "part_meme_ensemble", "experts_gardes_moyens"], lignes)
    p2["spearman_marge_experts_gardes"] = float(stats.spearmanr(S2, G2).statistic)
    return {"P1_couche_suivante": p1, "P2_jeton_suivant": p2}


def main():
    R.sous_la_normale()
    R.attendre_calme()
    rng = np.random.default_rng(GRAINE)
    ea, ma = R.lire(R.A)
    eb, mb = R.lire(R.B)
    bas = R.bascules(ea, eb)
    res = {"outil": "outils/pistes/tropicale/lois.py", "graine": GRAINE}
    res["loi_marge"] = loi_marge(mb)
    R.attendre_calme()
    res["correlation_couches"] = correlation_couches(mb, rng)
    R.attendre_calme()
    res["loi_bascule"] = loi_bascule(ma, mb, bas)
    res["extrapolation"] = extrapolation(ma, mb, bas, res["loi_bascule"])
    res["propagation"] = propagation(mb, bas)
    R.attendre_calme()
    res["prechargement"] = prechargement(ea, eb, mb, bas, rng)
    (R.SORTIE / "lois-resume.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("extrapolation", "propagation", "prechargement")}, ensure_ascii=False, indent=1, default=float))
    print("corrélation groupée :", res["correlation_couches"]["spearman_groupe"], "nul :", res["correlation_couches"]["nul_groupe_999e_centile_abs"])
    for d in res["loi_marge"]:
        print(d["couche"], f"med={d['mediane']:.4f} 1/moy={d['un_sur_moyenne']:.2f} f0={d['densite_0_1e3']:.2f} pente={d['pente_loglog']:.3f} forme={d['gamma_forme']:.3f}",
              {k: round(v, 4) for k, v in d["ks"].items()})
    for l, d in res["loi_bascule"].items():
        print(l, f"sig_rob={d['sigma_delta_robuste']:.2e} sd={d['ecart_type_delta']:.2e} kurt={d['kurtosis_delta']:.1f} sig_phi={d['sigma_phi']:.2e} ({d['logv_phi']:.1f}) sig_2phi={d['sigma_deux_phi']:.2e} ({d['logv_deux_phi']:.1f}) p(b|m<1e-4)={d['p_bascule_marge_sous_1e-4']} n={d['n_marge_sous_1e-4']}")


if __name__ == "__main__":
    main()
