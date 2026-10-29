"""P6, étape 0 : cache d'experts à niveaux (exact / rapide) et portillon de poids de mélange.

Seuils : mesures/mimetisme/P6/00-seuils-declares.md (commit 4d2b915, amendement c206831), écrits avant
toute lecture de trace. Ce module ne mesure rien tout seul : `etape0.py` l'appelle.

Modèle (voir § 1 du fichier de seuils) :
  - la politique (LFU à demi-vie h, ou LRU) ne lit pas l'étiquette de niveau : l'ensemble des défauts et les
    séjours (un séjour = de l'entrée d'un expert dans le cache à son éviction) sont les mêmes pour toutes
    les règles ; on les calcule une fois (`cache`), puis chaque règle est un calcul vectorisé sur les séjours.
  - chaque accès (jeton t, couche l, rang s) porte son poids de mélange w.
"""
import math

import numpy as np

K = 4


def charger(trace, poids):
    """Rend (experts [T,L,K] int32, poids [T,L,K] float64, E)."""
    E = None
    ex, wt = [], []
    for ligne in open(trace, encoding="utf-8"):
        l = ligne.strip()
        if not l or l.startswith("#"):
            continue
        if l.startswith("E="):
            E = int(l[2:])
            continue
        ex.append([[int(x) for x in g.split()] for g in l.split("|")])
    for ligne in open(poids, encoding="utf-8"):
        l = ligne.strip()
        if not l or l.startswith("#"):
            continue
        wt.append([[float(x) for x in g.split()] for g in l.split("|")])
    ex = np.array(ex, dtype=np.int32)
    wt = np.array(wt, dtype=np.float64)
    assert ex.shape == wt.shape, (ex.shape, wt.shape)
    assert ex.shape[2] == K
    return ex, wt, E


def cache(ex, E, N, politique="lfu", demi_vie=8.0):
    """Simule le cache global (règle de `noyau-cache` : groupe (t, l) servi entier, éviction après lui,
    jamais un expert du groupe, départage par ancienneté du dernier accès).
    Rend (defaut [T,L,K] bool, sejour [T,L,K] int32 : numéro du séjour de l'expert à cet accès)."""
    T, L, _ = ex.shape
    items = L * E
    tau = demi_vie / math.log(2.0)
    d = np.exp(-np.arange(T + 2, dtype=np.float64) / tau)
    c = np.zeros(items)
    last_t = np.zeros(items, dtype=np.int64)
    vu = np.zeros(items, dtype=np.int64)
    en_cache = np.zeros(items, dtype=bool)
    sej_courant = np.zeros(items, dtype=np.int64)
    n_res = 0
    n_sej = 0
    idx_groupe = 0
    defaut = np.zeros((T, L, K), dtype=bool)
    sejour = np.zeros((T, L, K), dtype=np.int32)
    inf = np.inf
    for tt in range(T):
        for l in range(L):
            idx_groupe += 1
            g = ex[tt, l]
            xs = l * E + g.astype(np.int64)
            for s in range(K):
                x = int(xs[s])
                if politique == "lfu":
                    c[x] = c[x] * d[tt - last_t[x]] + 1.0
                last_t[x] = tt
                vu[x] = idx_groupe
                if en_cache[x]:
                    pass
                else:
                    defaut[tt, l, s] = True
                    en_cache[x] = True
                    n_res += 1
                    n_sej += 1
                    sej_courant[x] = n_sej
                sejour[tt, l, s] = sej_courant[x]
            while n_res > N:
                if politique == "lfu":
                    sc = np.where(en_cache, c * d[tt - last_t], inf)
                else:
                    sc = np.where(en_cache, vu.astype(np.float64), inf)
                sc[xs] = inf
                m = sc.min()
                cand = np.flatnonzero(sc == m)
                if len(cand) > 1:
                    cand = cand[np.argmin(vu[cand])]
                else:
                    cand = cand[0]
                en_cache[cand] = False
                n_res -= 1
    return defaut, sejour


def regle(defaut, sejour, w, theta, nom, rho, theta_p=None):
    """Applique une règle de niveau. nom : 'accepter' ou 'remonter' (avec theta_p).
    Rend (energie [n], octets [n], bloc_jeton [n]) par accès, dans l'ordre des séjours (stable)."""
    T, L, _ = w.shape
    wf = w.reshape(-1)
    df = defaut.reshape(-1)
    sf = sejour.reshape(-1)
    tf = np.repeat(np.arange(T), L * K)
    ordre = np.argsort(sf, kind="stable")
    w_s, d_s, t_s = wf[ordre], df[ordre], tf[ordre]
    n = len(w_s)
    pos = np.arange(n)
    debut = np.maximum.accumulate(np.where(d_s, pos, 0))
    assert d_s[debut].all(), "un séjour ne commence pas par un défaut"
    F = w_s[debut] < theta
    if nom == "accepter":
        servi_rapide = F
        reread = np.zeros(n, dtype=bool)
    else:
        fort = (~d_s) & (w_s >= theta_p) & F
        cum = np.cumsum(fort)
        cs = cum - cum[debut]
        servi_rapide = F & (cs == 0)
        reread = fort & (cs == 1)
    energie = np.where(servi_rapide, w_s * w_s, 0.0)
    octets = np.where(d_s, np.where(F, rho, 1.0), 0.0) + np.where(reread, 1.0, 0.0)
    return energie, octets, t_s


def blocs_trace(energie, octets, t_s, w, defaut, bloc=32):
    """Sommes par blocs de `bloc` jetons : énergie servie rapide, octets lus, énergie totale, défauts."""
    T = w.shape[0]
    nb = (T + bloc - 1) // bloc
    b = t_s // bloc
    tf = np.repeat(np.arange(T), w.shape[1] * K)
    bt = tf // bloc
    return np.stack([np.bincount(b, weights=energie, minlength=nb),
                     np.bincount(b, weights=octets, minlength=nb),
                     np.bincount(bt, weights=(w.reshape(-1) ** 2), minlength=nb),
                     np.bincount(bt, weights=defaut.reshape(-1).astype(float), minlength=nb)])


def _calc(M, rho):
    E_, B_, Et_, Nm_ = M.sum(axis=1)
    S = (Nm_ - B_) / Nm_
    e = E_ / Et_
    r = e / (S / (1.0 - rho)) if S > 0 else float("inf")
    return S, e, r


def bilan_blocs(liste, rho, tirages=2000, graine=20261027):
    """r, S, E/E_tout sur un ou plusieurs traces (liste de `blocs_trace`), sigma par blocs de jetons."""
    M = np.concatenate(liste, axis=1)
    nb = M.shape[1]
    S, e, r = _calc(M, rho)
    rng = np.random.default_rng(graine)
    idx = rng.integers(0, nb, size=(tirages, nb))
    sr = np.array([_calc(M[:, idx[i]], rho) for i in range(tirages)])
    rs = sr[:, 2]
    rs_f = rs[np.isfinite(rs)]
    return {"S": float(S), "E_rel": float(e), "r": float(r), "sigma_S": float(sr[:, 0].std()),
            "sigma_E_rel": float(sr[:, 1].std()),
            "sigma_r": float(rs_f.std()) if len(rs_f) else None, "tirages_finis": int(len(rs_f)),
            "defauts": int(M[3].sum()), "blocs": int(nb)}


def bilan(energie, octets, t_s, w, defaut, rho, bloc=32, tirages=2000, graine=20261027):
    return bilan_blocs([blocs_trace(energie, octets, t_s, w, defaut, bloc)], rho, tirages, graine)


def sans_portage(defaut, w, theta):
    """Comptage de physique : énergie des seuls défauts de poids < theta (pas de portage aux succès)."""
    sel = defaut & (w < theta)
    return {"defauts": int(defaut.sum()), "defauts_sous": int(sel.sum()),
            "g2_defauts_sous": float((w[sel] ** 2).sum()), "g2_total": float((w ** 2).sum())}


def _prelude(defaut, sejour, w):
    T, L, _ = w.shape
    wf = w.reshape(-1)
    df = defaut.reshape(-1)
    sf = sejour.reshape(-1)
    tf = np.repeat(np.arange(T), L * K)
    ordre = np.argsort(sf, kind="stable")
    w_s, d_s, t_s = wf[ordre], df[ordre], tf[ordre]
    pos = np.arange(len(w_s))
    debut = np.maximum.accumulate(np.where(d_s, pos, 0))
    return w_s, d_s, t_s, debut


def regle_etiquette(defaut, sejour, w, F_sejour, rho):
    """Comme 'accepter', mais l'étiquette de chaque séjour est donnée : F_sejour[numéro de séjour] bool.
    Sert à la borne clairvoyante et à la sélection au hasard."""
    w_s, d_s, t_s, debut = _prelude(defaut, sejour, w)
    sf = sejour.reshape(-1)[np.argsort(sejour.reshape(-1), kind="stable")]
    F = F_sejour[sf]
    energie = np.where(F, w_s * w_s, 0.0)
    octets = np.where(d_s, np.where(F, rho, 1.0), 0.0)
    return energie, octets, t_s


def max_par_sejour(defaut, sejour, w):
    """Plus grand poids reçu pendant chaque séjour (indice = numéro de séjour, 1..n)."""
    w_s, d_s, t_s, debut = _prelude(defaut, sejour, w)
    sf = sejour.reshape(-1)[np.argsort(sejour.reshape(-1), kind="stable")]
    n = int(sf.max())
    m = np.zeros(n + 1)
    np.maximum.at(m, sf, w_s)
    return m
