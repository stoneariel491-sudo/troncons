"""Compléments de la garde à indices multiples, APRÈS le verdict (étiquetés exploratoires).

1. Les deux témoins dont l'attendu déclaré n'a pas tenu : W1 (cassure) et W3 (oracle). On refait la cassure
   de W1 par une autre voie (marges de test permutées) et on calcule le plafond de W3 par un modèle à classes
   (20 quantiles de f1 x bascule vérifiée en l-1), plus proche du meilleur usage possible de cet indice.
2. Les ablations : d'où vient le gain de M3 (f2, f3, f4 un par un, et M3 privé de chacun).
3. Les coefficients de M3 ajusté sur toutes les fenêtres (en échantillon : pour lire, pas pour juger).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import indices as I  # noqa: E402
import routage as R  # noqa: E402
import numpy as np  # noqa: E402

L, W, P = I.L, I.W, I.P


def classes_modele(f1, extra, y, nq=20):
    """Probabilités par classes (f1 en nq quantiles x extra entier), Laplace +1/+20, dix plis."""
    caught = np.zeros(W, int)
    for w in range(W):
        tr = [i for i in range(W) if i != w]
        v = f1[:, tr].reshape(-1)
        e = np.quantile(v, np.arange(1, nq) / nq)
        def cl(a, b):
            return np.searchsorted(e, a, side="right") * 8 + b
        ctr = cl(f1[:, tr], extra[:, tr]).reshape(-1)
        ytr = y[:, tr].reshape(-1).astype(float)
        n = np.bincount(ctr, minlength=nq * 8); k = np.bincount(ctr, weights=ytr, minlength=nq * 8)
        pr = (k + 1) / (n + 20)
        cte = cl(f1[:, w], extra[:, w]).reshape(-1)
        s = pr[cte]
        sel = I.top_part(s)
        caught[w] = int(y[:, w].reshape(-1)[sel].sum())
    return caught


def main():
    R.sous_la_normale(); R.attendre_calme()
    y, mb = I.charger()
    f = I.indices(mb)
    c0, nb = I.garde_marge(mb, y)
    b0 = I.pct(c0, nb)
    out = {"M0_b": b0}
    rng = np.random.default_rng(I.GRAINE)

    # W1, cassure par une autre voie : M1 ajusté sur les vraies étiquettes, mais marges de test permutées
    X = I.colonnes(f, "M1").reshape(L, W, P, 1)
    caught = np.zeros(W, int)
    for w in range(W):
        tr = [i for i in range(W) if i != w]
        wv, mu, sd = I.ajuster(X[:, tr].reshape(-1, 1), y[:, tr].reshape(-1).astype(float))
        xt = X[:, w].reshape(-1, 1).copy(); rng.shuffle(xt)
        s = I.score_logit(xt, wv, mu, sd)
        caught[w] = int(y[:, w].reshape(-1)[I.top_part(s)].sum())
    out["W1_cassure_marges_test_permutees"] = {"b_pct": I.pct(caught, nb), "attendu": "10 +- 2"}

    # W3, plafond : bascule vérifiée en (l-1, p) avec la marge, par classes
    orac = np.zeros(y.shape, int); orac[1:] = y[:-1].astype(int)
    cw = classes_modele(f[0], orac, y)
    out["W3_plafond_par_classes"] = {"b_pct": I.pct(cw, nb), "gain_points": I.pct(cw, nb) - b0}
    # et la logistique du témoin, pour comparer (déjà dans indices-resume.json)
    # fraction des bascules qui ont une bascule vérifiée en l-1 (même position) :
    out["part_bascules_avec_bascule_en_l_moins_1"] = float((y[1:] & y[:-1]).sum() / y.sum())
    out["part_cellules_avec_bascule_en_l_moins_1"] = float(orac.mean())

    # ablations
    ab = {}
    def run(cols):
        c, _, _ = I.evaluer(None, y, cols)
        return c
    f1, f2, f3, f4, f5 = f
    def mod(*fs):
        return np.stack([g.reshape(-1) for g in fs] + [(f1 * f5).reshape(-1)], axis=1)
    cas = {"f1+f5": mod(f1, f5), "f1+f5+f2": mod(f1, f5, f2), "f1+f5+f3": mod(f1, f5, f3), "f1+f5+f4": mod(f1, f5, f4),
           "M3 sans f2": mod(f1, f3, f4, f5), "M3 sans f3": mod(f1, f2, f4, f5), "M3 sans f4": mod(f1, f2, f3, f5)}
    for k, X in cas.items():
        c = run(X)
        ab[k] = {"b_pct": I.pct(c, nb), "gain_points": I.pct(c, nb) - b0,
                 "ic95": I.bootstrap_diff(c, c0, nb), "fenetres_positives": int((c > c0).sum())}
    out["ablations"] = ab

    # coefficients, en échantillon, M3 sur toutes les fenêtres
    X3 = I.colonnes(f, "M3")
    wv, mu, sd = I.ajuster(X3, y.reshape(-1).astype(float))
    noms = ["intercept", "f1", "f2", "f3", "f4", "f5", "f1*f5"]
    out["coefficients_M3_en_echantillon"] = {n: float(v) for n, v in zip(noms, wv)}
    # autocorrélation brute des indices avec la bascule (Spearman)
    from scipy.stats import spearmanr
    out["spearman_avec_bascule"] = {n: float(spearmanr(g.reshape(-1), y.reshape(-1))[0]) for n, g in zip(["f1", "f2", "f3", "f4", "f5"], f)}
    Path(I.SORTIE / "complements.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=I._nat), encoding="utf-8")
    print(json.dumps(out, indent=1, ensure_ascii=False, default=I._nat))


if __name__ == "__main__":
    main()
