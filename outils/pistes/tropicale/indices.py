"""La garde à indices multiples (mémoire du conflit) : protocole de genome/pistes/tropicale/seuil-declare-indices.md.

Chemin principal (numpy). Lit les journaux A et B du lot R, construit les cinq indices f1 à f5 à partir de
la seule marge de B, entraîne une régression logistique pli par pli (un pli = une fenêtre de test),
signale dans chaque fenêtre de test exactement les 10 % de cellules de plus fort score, compte les
bascules attrapées, passe les témoins W1 à W4 et écrit les scores pour le second chemin.

Cohabitation : priorité sous la normale, un fil, pas de carte, pause sur le verrou.
"""

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import routage as R  # noqa: E402  (fixe aussi OMP_NUM_THREADS=1 avant numpy)
import numpy as np  # noqa: E402

SORTIE = R.SORTIE / "indices"
SEUIL_F4 = 0.01241          # le tau_10 du verdict, déjà publié
PART = 0.10
LAMBDA = 1.0
GRAINE = 20261026
EMPREINTES = {
    "A": "f0a19c1182a3db507c7ade3d49734f765372bd6d1e101e3f4d0cb9be785b8d3c",
    "B": "07a9d4f974fd00ea8e56330865021f139025741fd63afe5b45c562336fd549d0",
}
L, W, P = 24, 10, 511


def empreinte(chemin):
    return hashlib.sha256(Path(chemin).read_bytes()).hexdigest()


def charger():
    for k, c in (("A", R.A), ("B", R.B)):
        e = empreinte(c)
        if e != EMPREINTES[k]:
            raise SystemExit(f"empreinte de {k} différente : {e}")
    ea, ma = R.lire(R.A)
    eb, mb = R.lire(R.B)
    y = R.bascules(ea, eb)                     # (L, N)
    assert (mb > 0).all(), "marge nulle ou négative dans B"
    return y.reshape(L, W, P), mb.astype(np.float64).reshape(L, W, P)


def indices(mb):
    """f1 à f5, chacun (L, W, P). N'utilise que la marge de B."""
    f1 = np.log(mb)
    cm = np.minimum.accumulate(mb, axis=0)
    f2 = np.zeros_like(f1)
    f2[1:] = np.log(cm[:-1])
    f3 = np.zeros_like(f1)
    f3[:, :, 1:] = f1[:, :, :-1]
    hit = (mb < SEUIL_F4).astype(np.float64)
    # coups cumulés sur les couches 0..l, pour chaque position
    ch = np.cumsum(hit, axis=0)                 # (L, W, P)
    cp = np.concatenate([np.zeros((L, W, 1)), np.cumsum(ch, axis=2)], axis=2)  # somme cumulée sur p
    f4 = np.zeros_like(f1)
    for p in range(1, P):
        lo = max(0, p - 8)
        s = cp[:, :, p] - cp[:, :, lo]          # somme des positions lo..p-1
        n = (p - lo) * (np.arange(L) + 1)[:, None]
        f4[:, :, p] = s / n
    f5 = np.broadcast_to((np.arange(L) / 23.0)[:, None, None], f1.shape).copy()
    return f1, f2, f3, f4, f5


def colonnes(f, modele):
    f1, f2, f3, f4, f5 = f
    if modele == "M1":
        cols = [f1]
    elif modele == "M2":
        cols = [f1, f5, f1 * f5]
    elif modele == "M3":
        cols = [f1, f2, f3, f4, f5, f1 * f5]
    else:
        raise ValueError(modele)
    return np.stack([c.reshape(-1) for c in cols], axis=1)  # (L*W*P, k), ordre (l, w, p)


def ajuster(X, y, lam=LAMBDA, it=60):
    """Régression logistique, pénalité L2 `lam` hors intercept, IRLS."""
    mu, sd = X.mean(0), X.std(0) + 1e-12
    Z = np.hstack([np.ones((len(X), 1)), (X - mu) / sd])
    w = np.zeros(Z.shape[1])
    pen = lam * np.eye(Z.shape[1]); pen[0, 0] = 0
    for _ in range(it):
        eta = Z @ w
        p = 1 / (1 + np.exp(-np.clip(eta, -30, 30)))
        g = Z.T @ (p - y) + pen @ w
        H = (Z * (p * (1 - p))[:, None]).T @ Z + pen
        d = np.linalg.solve(H, g)
        w -= d
        if np.abs(d).max() < 1e-9:
            break
    return w, mu, sd


def score_logit(X, w, mu, sd):
    return np.hstack([np.ones((len(X), 1)), (X - mu) / sd]) @ w


def top_part(score, part=PART):
    """Indices des K cellules de plus fort score (K = floor(part n)), ex aequo départagés par l'indice."""
    k = int(part * score.size)
    ordre = np.argsort(-score, kind="stable")
    return ordre[:k]


def evaluer(cols_fn, y, modele_cols, entrainer=True, y_entr=None, ret_scores=False):
    """Dix plis, un par fenêtre. cols_fn : (L*W*P, k) déjà construit. Rend caught[w], n_bas[w], scores (L, W, P)."""
    Y = y.reshape(L, W, P)
    X = modele_cols.reshape(L, W, P, -1)
    caught = np.zeros(W, int)
    nbas = np.zeros(W, int)
    sc_tout = np.zeros((L, W, P))
    for w in range(W):
        tr = [i for i in range(W) if i != w]
        Xtr = X[:, tr].reshape(-1, X.shape[-1])
        ytr = (y_entr if y_entr is not None else Y)[:, tr].reshape(-1).astype(float)
        Xte = X[:, w].reshape(-1, X.shape[-1])
        yte = Y[:, w].reshape(-1)
        wv, mu, sd = ajuster(Xtr, ytr)
        s = score_logit(Xte, wv, mu, sd)
        sel = top_part(s)
        caught[w] = int(yte[sel].sum())
        nbas[w] = int(yte.sum())
        sc_tout[:, w] = s.reshape(L, P)
    return caught, nbas, sc_tout


def garde_marge(mb, y):
    """M0 : la garde actuelle, rang croissant de la marge de B, 10 % par fenêtre."""
    caught = np.zeros(W, int); nbas = np.zeros(W, int)
    for w in range(W):
        m = mb[:, w].reshape(-1); yw = y[:, w].reshape(-1)
        sel = top_part(-m)
        caught[w] = int(yw[sel].sum()); nbas[w] = int(yw.sum())
    return caught, nbas


def _nat(o):
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    raise TypeError(type(o))


def pct(c, n):
    return 100.0 * c.sum() / n.sum()


def bootstrap_diff(c3, c0, nb, tirages=10000, graine=GRAINE):
    rng = np.random.default_rng(graine)
    d = np.empty(tirages)
    for t in range(tirages):
        idx = rng.integers(0, W, W)
        d[t] = 100.0 * (c3[idx].sum() - c0[idx].sum()) / nb[idx].sum()
    return float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def main():
    R.sous_la_normale()
    R.attendre_calme()
    SORTIE.mkdir(parents=True, exist_ok=True)
    y, mb = charger()
    nb_tot = int(y.sum())
    f = indices(mb)
    res = {"bascules": nb_tot, "cellules": int(y.size)}

    c0, nb = garde_marge(mb, y)
    res["M0"] = {"b_pct": pct(c0, nb), "par_fenetre": c0.tolist(), "bascules_par_fenetre": nb.tolist()}
    sc = {}
    cc = {}
    for m in ("M1", "M2", "M3"):
        X = colonnes(f, m)
        c, nbm, s = evaluer(None, y, X)
        cc[m] = c; sc[m] = s
        res[m] = {"b_pct": pct(c, nbm), "par_fenetre": c.tolist()}
    res["M3"]["gain_points"] = res["M3"]["b_pct"] - res["M0"]["b_pct"]
    res["M3"]["gain_ic95"] = bootstrap_diff(cc["M3"], c0, nb)
    res["M3"]["fenetres_positives"] = int((cc["M3"] > c0).sum())
    res["M2"]["gain_points"] = res["M2"]["b_pct"] - res["M0"]["b_pct"]
    res["M2"]["gain_ic95"] = bootstrap_diff(cc["M2"], c0, nb)
    res["M2"]["fenetres_positives"] = int((cc["M2"] > c0).sum())

    # ---- témoins
    tem = {}
    tem["W1_identite"] = {"M1_egal_M0": bool((cc["M1"] == c0).all()), "M1": cc["M1"].tolist(), "M0": c0.tolist()}
    rng = np.random.default_rng(GRAINE)
    # cassure de W1 : étiquette d'entraînement mélangée
    ymel = y.copy().reshape(-1); rng.shuffle(ymel); ymel = ymel.reshape(y.shape)
    X1 = colonnes(f, "M1")
    cm, _, _ = evaluer(None, y, X1, y_entr=ymel)
    tem["W1_cassure_etiquette_melangee"] = {"b_pct": pct(cm, nb), "attendu": "10 +- 2"}
    # W2 : f2, f3, f4 permutés dans chaque couche
    fp = [f[0]] + [np.stack([rng.permutation(g[l].reshape(-1)).reshape(W, P) for l in range(L)]) for g in f[1:4]] + [f[4]]
    cw2, _, _ = evaluer(None, y, colonnes(fp, "M3"))
    tem["W2_faux_indices"] = {"b_pct": pct(cw2, nb), "gain_points": pct(cw2, nb) - res["M0"]["b_pct"], "attendu": "gain dans +-1,5"}
    # W3 : f2 = bascule vérifiée à (l-1, p)
    orac = np.zeros_like(f[1]); orac[1:] = y[:-1].astype(float)
    fo = [f[0], orac, f[2], f[3], f[4]]
    cw3, _, _ = evaluer(None, y, colonnes(fo, "M3"))
    tem["W3_indice_oracle"] = {"b_pct": pct(cw3, nb), "gain_points": pct(cw3, nb) - res["M0"]["b_pct"], "attendu": "gain > 15"}
    # W4 : M3 entraîné sur étiquettes mélangées
    cw4, _, _ = evaluer(None, y, colonnes(f, "M3"), y_entr=ymel)
    tem["W4_etiquette_melangee_M3"] = {"b_pct": pct(cw4, nb), "attendu": "10 +- 2"}
    res["temoins"] = tem

    # ---- verdicts au seuil déclaré
    g = res["M3"]
    lo, hi = g["gain_ic95"]
    res["verdict"] = {
        "passe_80_10": res["M3"]["b_pct"] >= 80.0,
        "utile": bool(g["gain_points"] >= 5.0 and lo > 0 and g["fenetres_positives"] >= 8),
        "criteres": {"gain>=5": g["gain_points"] >= 5.0, "ic_exclut_0": lo > 0, "fenetres>=8": g["fenetres_positives"] >= 8},
    }
    (SORTIE / "indices-resume.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=_nat), encoding="utf-8")

    # scores pour le second chemin : cellule (l, w, p) dans l'ordre l, w, p
    with open(SORTIE / "scores-M3.csv", "w", encoding="utf-8", newline="") as fh:
        fh.write("l,w,p,score\n")
        for l in range(L):
            for w in range(W):
                for p in range(P):
                    fh.write(f"{l},{w},{p},{sc["M3"][l, w, p]:.17g}\n")
    print(json.dumps({k: res[k] for k in ("M0", "M1", "M2", "M3", "temoins", "verdict")}, indent=1, ensure_ascii=False, default=_nat))


if __name__ == "__main__":
    main()
