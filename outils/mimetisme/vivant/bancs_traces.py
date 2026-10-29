"""Bancs de l'éclaireur du vivant, sur les traces de routage de gpt-oss (aucun fichier de modèle ouvert).

Seuils et témoins : genome/mimetisme/vivant/seuil-declare.md (commité avant ce code).
Entrées : mesures/localite-gpt-oss/traces-{20b,120b}/*.tar.xz, dépaquetés par --extraire.
Sorties : mesures/mimetisme/vivant/.

  python -I outils/mimetisme/vivant/bancs_traces.py --extraire DOSSIER
  python -I outils/mimetisme/vivant/bancs_traces.py --temoins DOSSIER
  python -I outils/mimetisme/vivant/bancs_traces.py --banc ea|eb|ec|ed|ee|ef DOSSIER

Un fil, priorité sous la normale (consigne de cohabitation).
"""

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import argparse
import importlib.util
import json
import math
import statistics
import sys
import tarfile
from pathlib import Path

import numpy as np

DEPOT = Path(__file__).resolve().parents[3]
SORTIE = DEPOT / "mesures" / "mimetisme" / "vivant"
GENRES = ["code", "dialogue", "prose-en", "prose-fr", "wiki"]
BUDGETS = {"20b": [6, 10], "120b": [13, 26]}
K = 4


def sous_la_normale():
    try:
        import ctypes
        k = ctypes.windll.kernel32
        k.GetCurrentProcess.restype = ctypes.c_void_p
        k.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        k.SetPriorityClass(k.GetCurrentProcess(), 0x00004000)
    except Exception as e:
        print(f"priorité non baissée : {e}")


def charger_instrument():
    chemin = DEPOT / "outils" / "chargement_localite.py"
    spec = importlib.util.spec_from_file_location("chargement_localite", chemin)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


INS = None


def instrument():
    global INS
    if INS is None:
        INS = charger_instrument()
    return INS


# ---------------------------------------------------------------- lecture

def extraire(dossier):
    dossier = Path(dossier)
    for modele in ("20b", "120b"):
        arch = DEPOT / "mesures" / "localite-gpt-oss" / f"traces-{modele}" / f"traces-{modele}.tar.xz"
        cible = dossier / modele
        cible.mkdir(parents=True, exist_ok=True)
        with tarfile.open(arch) as t:
            t.extractall(cible, filter="data")
        print("extrait", arch.name, "->", cible)


def nom_fichier(modele, genre, mode, ext):
    pre = "w" if genre == "wiki" else "t"
    return f"{pre}{modele}.{genre}.{mode}.{ext}"


def lire_poids(chemin):
    lignes = []
    with open(chemin, encoding="utf-8") as f:
        for l in f:
            l = l.strip()
            if not l or l.startswith("#"):
                continue
            lignes.append([[float(x) for x in c.split()] for c in l.split("|")])
    return np.array(lignes, dtype=np.float64)


def charger(dossier, modele, genre, mode="lecture"):
    d = Path(dossier) / modele
    ins = instrument()
    jetons, E = ins.lire_trace(d / nom_fichier(modele, genre, mode, "trace"))
    sets = np.array(jetons, dtype=np.int16)          # (T, L, k)
    poids = lire_poids(d / nom_fichier(modele, genre, mode, "poids"))
    assert sets.shape == poids.shape, (sets.shape, poids.shape)
    return sets, poids, E


# ---------------------------------------------------------------- simulateur générique par couche

def simuler(seq, C, politique, E, pas_hits=False):
    """Même sémantique que chargement_localite.cache_lru : insertion sur défaut, on n'évince jamais un
    expert demandé par le jeton courant. `politique` fournit voir(t, s), demande(e, t, s),
    victime(candidats, t, s). Retourne le taux de succès (et, si pas_hits, la liste des succès par accès)."""
    cache = set()
    succes = total = 0
    drapeaux = []
    for t, s in enumerate(seq):
        politique.voir(t, s)
        for e in s:
            total += 1
            politique.demande(e, t, s)
            if e in cache:
                succes += 1
                if pas_hits:
                    drapeaux.append(True)
            else:
                if pas_hits:
                    drapeaux.append(False)
                cache.add(e)
                if len(cache) > C:
                    cands = [v for v in cache if v not in s]
                    cache.remove(politique.victime(cands, t, s))
    return (succes / total, drapeaux) if pas_hits else succes / total


class PolDernier:
    """Score = dernier instant d'usage : LRU (témoin W2)."""
    def __init__(self, E):
        self.dernier = {}
        self.n = 0

    def voir(self, t, s):
        pass

    def demande(self, e, t, s):
        self.n += 1
        self.dernier[e] = self.n

    def victime(self, cands, t, s):
        return min(cands, key=lambda v: self.dernier.get(v, -1))


class PolActR:
    """Activation de base ACT-R : B(e) = ln somme_j (t - t_j + 1)^(-d). On évince la plus basse."""
    def __init__(self, E, T, d=0.5):
        self.E, self.d = E, d
        self.M = np.zeros((T, E), dtype=np.float32)       # M[t, e] = 1 si e demandé au jeton t
        self.tab = np.arange(0, T + 3, dtype=np.float64)
        self.tab[0] = 1.0
        self.puiss = self.tab ** (-d)                      # puiss[lag]
        self.dernier = {}

    def voir(self, t, s):
        pass

    def demande(self, e, t, s):
        self.M[t, e] = 1.0
        self.dernier[e] = t

    def victime(self, cands, t, s):
        if t == 0:
            return cands[0]
        # j = 0 .. t-1, lag = t - j + 1 -> puiss[t+1], ..., puiss[2]
        w = self.puiss[2:t + 2][::-1]
        sc = w @ self.M[:t][:, cands]
        pire = min(range(len(cands)), key=lambda i: (sc[i], self.dernier.get(cands[i], -1)))
        return cands[pire]


class PolAssoc:
    """Anticipation apprise : score(e) = somme_{e' in S_t} (N[e'][e] + p0(e)) / (n[e'] + 1), N comptant en
    ligne les paires (e' dans S_{t-1}, e dans S_t) déjà vues dans la couche ; p0 = fréquence à demi-vie 8."""
    def __init__(self, E):
        self.E = E
        self.N = np.zeros((E, E), dtype=np.float64)
        self.n = np.zeros(E, dtype=np.float64)
        self.p0 = np.zeros(E, dtype=np.float64)
        self.dec = 0.5 ** (1.0 / 8.0)
        self.prec = None
        self.dernier = {}
        self.score = None

    def voir(self, t, s):
        # transition (S_{t-1} -> S_t) : S_t est connu dès sa demande, donc apprenable ici
        if self.prec is not None:
            a = np.array(self.prec)
            b = np.array(s)
            self.N[np.ix_(a, b)] += 1.0
            self.n[a] += 1.0
        self.p0 *= self.dec
        for e in s:
            self.p0[e] += 1.0
        a = np.array(s)
        tot = self.p0.sum()
        p = self.p0 / tot if tot > 0 else self.p0
        self.score = ((self.N[a] + p[None, :]) / (self.n[a][:, None] + 1.0)).sum(axis=0)
        self.prec = list(s)

    def demande(self, e, t, s):
        self.dernier[e] = t

    def victime(self, cands, t, s):
        return min(cands, key=lambda v: (self.score[v], self.dernier.get(v, -1)))


def hit_pol(seq, C, E, nom, d=0.5):
    T = len(seq)
    if nom == "dernier":
        p = PolDernier(E)
    elif nom == "actr":
        p = PolActR(E, T, d)
    elif nom == "assoc":
        p = PolAssoc(E)
    else:
        raise ValueError(nom)
    return simuler(seq, C, p, E)


def par_couche(sets, c):
    return [list(map(int, sets[t, c])) for t in range(sets.shape[0])]


def moyenne_couches(sets, E, C, nom, d=0.5):
    return statistics.fmean(hit_pol(par_couche(sets, c), C, E, nom, d) for c in range(sets.shape[1]))


# ---------------------------------------------------------------- témoins

def temoins(dossier):
    rap, echecs = {}, []
    ins = instrument()
    # W1 : mon LRU (politique « dernier ») égale cache_lru de l'instrument ; W2 est la même égalité
    # côté simulateur générique. Belady : on lit celui de l'instrument, qui est le seul utilisé.
    cas = [("20b", "code"), ("120b", "wiki")]
    for modele, genre in cas:
        sets, poids, E = charger(dossier, modele, genre)
        for C in BUDGETS[modele]:
            ecart = 0.0
            for c in range(min(6, sets.shape[1])):
                seq = par_couche(sets, c)
                ecart = max(ecart, abs(hit_pol(seq, C, E, "dernier") - ins.cache_lru(seq, C)))
            ok = ecart <= 1e-12
            rap[f"W1_lru_{modele}_{genre}_C{C}"] = {"ecart_max": ecart, "reussi": ok}
            if not ok:
                echecs.append(f"W1 {modele} {genre} C={C}")
    # W3 : causalité
    sets, poids, E = charger(dossier, "20b", "dialogue")
    seq = par_couche(sets, 3)
    demi = len(seq) // 2
    for nom in ("actr", "assoc"):
        C = 6
        T = len(seq)
        pol = (PolActR(E, T) if nom == "actr" else PolAssoc(E))
        _, f_plein = simuler(seq, C, pol, E, pas_hits=True)
        pol = (PolActR(E, demi) if nom == "actr" else PolAssoc(E))
        _, f_demi = simuler(seq[:demi], C, pol, E, pas_hits=True)
        ok = f_plein[:len(f_demi)] == f_demi
        rap[f"W3_causalite_{nom}"] = {"acces_compares": len(f_demi), "reussi": ok}
        if not ok:
            echecs.append(f"W3 {nom}")
    # W4 : routage uniforme i.i.d. : rien à apprendre
    rng = np.random.default_rng(20261026)
    T, E, L = 2500, 128, 6
    for C in (13, 26):
        sy = np.array([[rng.choice(E, K, replace=False) for _ in range(L)] for _ in range(T)])
        n = T * K * L
        p = C / E
        tol = 4 * math.sqrt(p * (1 - p) / n) + K / T
        for nom in ("dernier", "actr", "assoc"):
            v = moyenne_couches(sy, E, C, nom)
            ok = abs(v - p) <= tol
            rap[f"W4_iid_{nom}_C{C}"] = {"mesure": v, "attendu": p, "tolerance": tol, "reussi": ok}
            if not ok:
                echecs.append(f"W4 {nom} C={C}")
    # W5 : E-C, poids synthétiques
    def abandon(w, tau):
        w = sorted(w)
        m, n = 0.0, 0
        for x in w:
            if m + x <= tau + 1e-12:
                m += x
                n += 1
            else:
                break
        return n
    ok1 = abandon([0.25] * 4, 0.02) == 0
    ok2 = abandon([0.97, 0.01, 0.01, 0.01], 0.03) == 3
    rap["W5_abandon"] = {"egaux_tau2": abandon([0.25] * 4, 0.02), "concentre_tau3": abandon([0.97, 0.01, 0.01, 0.01], 0.03),
                         "reussi": ok1 and ok2}
    if not (ok1 and ok2):
        echecs.append("W5 abandon")
    # W6 : E-E, queue au routage uniforme
    sy6 = np.array([rng.choice(128, K, replace=False) for _ in range(512)])[:, None, :]
    ct = queue_fenetre(sy6, 128)
    ok = ct["queue_parmi_touches"] == 0.0
    rap["W6_queue_iid"] = {**ct, "reussi": ok}
    if not ok:
        echecs.append("W6 queue")
    # W7 : E-F, figé et iid
    figé = np.tile(np.array([[3, 9, 27, 100]]), (200, 1))[:, None, :]
    u = union_gamma(figé, 128, 8)
    ok = all(abs(u[g - 1] - K) < 1e-12 for g in range(1, 9))
    rap["W7_union_fige"] = {"U": u, "reussi": ok}
    if not ok:
        echecs.append("W7 union figé")
    sy = np.array([[rng.choice(128, K, replace=False)] for _ in range(4000)])
    u = union_gamma(sy, 128, 8)
    att = [128 * (1 - (1 - K / 128) ** g) for g in range(1, 9)]
    ok = all(abs(a - b) <= 0.15 for a, b in zip(u, att))
    rap["W7_union_iid"] = {"U": u, "attendu": att, "reussi": ok}
    if not ok:
        echecs.append("W7 union iid")
    # W8 : E-D, rang planté
    X, rang = synergies_plantees(rng)
    ok = rang == 3
    rap["W8_rang_plante"] = {"rang": rang, "reussi": ok}
    if not ok:
        echecs.append("W8 rang planté")
    # W9 : E-B, courbes identiques -> allocation uniforme ; total conservé
    L, C0, Cmax = 36, 13, 64
    courbe = 1 - np.exp(-np.arange(0, Cmax + 1) / 20.0)
    allocs = allouer(np.tile(courbe, (L, 1)), L * C0, 4)
    ok = (allocs == C0).all() and allocs.sum() == L * C0
    rap["W9_alloc_uniforme"] = {"alloc": allocs.tolist(), "reussi": bool(ok)}
    if not ok:
        echecs.append("W9 allocation")
    sortie = {"rapport": rap, "echecs": echecs, "verdict": "INSTRUMENT VALIDE" if not echecs else "TEMOIN TOMBE"}
    return sortie


# ---------------------------------------------------------------- E-A

def banc_ea(dossier, casser_ordre=False, d_sens=(0.3, 0.8)):
    ins = instrument()
    rng = np.random.default_rng(20261026)
    res = {}
    for modele in ("20b", "120b"):
        res[modele] = {}
        for genre in GENRES:
            sets, poids, E = charger(dossier, modele, genre)
            if casser_ordre:
                sets = sets[rng.permutation(sets.shape[0])]
            for C in BUDGETS[modele]:
                L = sets.shape[1]
                lru = statistics.fmean(ins.cache_lru(par_couche(sets, c), C) for c in range(L))
                lfu = statistics.fmean(ins.cache_lfu(par_couche(sets, c), C, 8.0) for c in range(L))
                bel = statistics.fmean(ins.cache_belady(par_couche(sets, c), C) for c in range(L))
                actr = moyenne_couches(sets, E, C, "actr", 0.5)
                assoc = moyenne_couches(sets, E, C, "assoc")
                ligne = {"lru": lru, "lfu8": lfu, "belady": bel, "actr_d0.5": actr, "assoc": assoc}
                if not casser_ordre:
                    for d in d_sens:
                        ligne[f"actr_d{d}"] = moyenne_couches(sets, E, C, "actr", d)
                res[modele][f"{genre}|{C}"] = ligne
                print(modele, genre, C, {k: round(v, 4) for k, v in ligne.items()}, flush=True)
    return res


def gain_relatif(ligne, cle):
    meilleur = max(ligne["lru"], ligne["lfu8"])
    return ((1 - meilleur) - (1 - ligne[cle])) / (1 - meilleur)


def verdict_ea(res, cle):
    sortie = {}
    for modele in res:
        ok_tous = True
        det = {}
        for C in BUDGETS[modele]:
            g = [gain_relatif(res[modele][f"{gr}|{C}"], cle) for gr in GENRES]
            med = statistics.median(g)
            pos = sum(1 for x in g if x > 0)
            det[str(C)] = {"gains": g, "mediane": med, "positifs": pos, "passe": med >= 0.10 and pos >= 4}
            ok_tous &= det[str(C)]["passe"]
        sortie[modele] = {"detail": det, "passe": ok_tous}
    return sortie


# ---------------------------------------------------------------- E-B

def mrc_lru(sets, Cmax):
    """Courbe de succès LRU par couche et par C = 0 .. Cmax (C < 4 : 0 par convention, hors domaine)."""
    ins = instrument()
    L = sets.shape[1]
    out = np.zeros((L, Cmax + 1))
    for c in range(L):
        seq = par_couche(sets, c)
        for C in range(K, Cmax + 1):
            out[c, C] = ins.cache_lru(seq, C)
    return out


def allouer(courbes, N, cmin):
    """Sac à dos exact : maximise la somme des succès moyens, sum C_l = N, C_l >= cmin."""
    L, Cmax1 = courbes.shape
    Cmax = Cmax1 - 1
    NEG = -1e18
    dp = np.full((L + 1, N + 1), NEG)
    ch = np.zeros((L + 1, N + 1), dtype=np.int32)
    dp[0, 0] = 0.0
    for l in range(L):
        for n in range(N + 1):
            if dp[l, n] <= NEG / 2:
                continue
            for C in range(cmin, min(Cmax, N - n) + 1):
                v = dp[l, n] + courbes[l, C]
                if v > dp[l + 1, n + C] + 1e-15:
                    dp[l + 1, n + C] = v
                    ch[l + 1, n + C] = C
    alloc = np.zeros(L, dtype=np.int32)
    n = N
    for l in range(L, 0, -1):
        C = ch[l, n]
        alloc[l - 1] = C
        n -= C
    return alloc


def lru_alloue(sets, alloc):
    ins = instrument()
    return statistics.fmean(ins.cache_lru(par_couche(sets, c), int(alloc[c])) for c in range(sets.shape[1]))


def banc_eb(dossier):
    rng = np.random.default_rng(20261026)
    res = {}
    for modele in ("20b", "120b"):
        Cmax = 32 if modele == "20b" else 64
        jeu = {g: charger(dossier, modele, g)[0] for g in GENRES}
        courbes = {g: mrc_lru(jeu[g], Cmax) for g in GENRES}
        L = jeu[GENRES[0]].shape[1]
        res[modele] = {}
        for C0 in BUDGETS[modele]:
            N = L * C0
            ligne = {}
            for g in GENRES:
                autres = [x for x in GENRES if x != g]
                moy = np.mean([courbes[x] for x in autres], axis=0)
                alloc = allouer(moy, N, K)
                perm = rng.permutation(L)
                alloc_perm = allouer(moy[perm], N, K)
                # alloc_perm[i] est l'optimum de la courbe moy[perm[i]] (celle d'une AUTRE couche) : la couche i
                # reçoit l'allocation qui convenait à la courbe d'une autre. (Première version : alloc_perm
                # était remis dans l'ordre de perm, ce qui redonnait l'allocation vraie et rendait le témoin vide.)
                alloc_perm_reel = alloc_perm
                uni = lru_alloue(jeu[g], np.full(L, C0))
                opt = lru_alloue(jeu[g], alloc)
                per = lru_alloue(jeu[g], alloc_perm_reel)
                ligne[g] = {"uniforme": uni, "alloue_autres_genres": opt, "alloue_courbes_permutees": per,
                            "alloc": alloc.tolist(), "total": int(alloc.sum()), "N": N}
                print(modele, C0, g, round(uni, 4), round(opt, 4), round(per, 4), flush=True)
            res[modele][str(C0)] = ligne
    return res


def verdict_eb(res):
    out = {}
    for modele in res:
        ok = True
        det = {}
        for C0, ligne in res[modele].items():
            gains = [((1 - v["uniforme"]) - (1 - v["alloue_autres_genres"])) / (1 - v["uniforme"]) for v in ligne.values()]
            gper = [((1 - v["uniforme"]) - (1 - v["alloue_courbes_permutees"])) / (1 - v["uniforme"]) for v in ligne.values()]
            med, pos = statistics.median(gains), sum(1 for x in gains if x > 0)
            medp = statistics.median(gper)
            passe = med >= 0.10 and pos >= 4 and medp < med / 3
            det[C0] = {"gains": gains, "mediane": med, "positifs": pos, "mediane_permutee": medp, "passe": passe,
                       "totaux_ok": all(v["total"] == v["N"] for v in ligne.values())}
            ok &= passe
        out[modele] = {"detail": det, "passe": ok}
    return out


# ---------------------------------------------------------------- E-C

def drapeaux_defauts_lru(sets, C, E):
    """Pour chaque (jeton, couche, rang), vrai si l'accès est un défaut du LRU par couche de taille C."""
    T, L, k = sets.shape
    fl = np.zeros((T, L, k), dtype=bool)
    for c in range(L):
        seq = par_couche(sets, c)
        _, h = simuler(seq, C, PolDernier(E), E, pas_hits=True)
        fl[:, c, :] = (~np.array(h, dtype=bool)).reshape(T, k)
    return fl


def abandonnables(poids, taus):
    """Pour chaque tau, masque (T, L, k) des experts abandonnés : les plus faibles tant que la masse cumulée <= tau."""
    T, L, k = poids.shape
    ordre = np.argsort(poids, axis=2, kind="stable")
    tri = np.take_along_axis(poids, ordre, axis=2)
    cum = np.cumsum(tri, axis=2)
    res = {}
    for tau in taus:
        ok_tri = cum <= tau + 1e-12
        masque = np.zeros_like(ok_tri)
        np.put_along_axis(masque, ordre, ok_tri, axis=2)
        res[tau] = masque
    return res


def banc_ec(dossier):
    taus = [0.01, 0.02, 0.05]
    res = {}
    for modele in ("20b", "120b"):
        res[modele] = {}
        for genre in GENRES:
            sets, poids, E = charger(dossier, modele, genre)
            ab = abandonnables(poids, taus)
            ligne = {"poids_rang": [float(poids[:, :, i].mean()) for i in range(K)],
                     "part_toutes_lectures": {str(t): float(ab[t].mean()) for t in taus}}
            for C in BUDGETS[modele]:
                fl = drapeaux_defauts_lru(sets, C, E)
                ligne[f"C{C}"] = {"defauts": float(fl.mean()),
                                  **{f"abandonnable_{t}": float((fl & ab[t]).sum() / fl.sum()) for t in taus}}
            res[modele][genre] = ligne
            print(modele, genre, json.dumps(ligne)[:300], flush=True)
    return res


def verdict_ec(res):
    out = {}
    for modele in res:
        det = {}
        for C in BUDGETS[modele]:
            v = [res[modele][g][f"C{C}"]["abandonnable_0.02"] for g in GENRES]
            det[str(C)] = {"par_genre": v, "mediane": statistics.median(v), "passe": statistics.median(v) >= 0.15}
        out[modele] = {"detail": det, "passe": all(x["passe"] for x in det.values())}
    return out


# ---------------------------------------------------------------- E-D

def gram_energies(X):
    Xc = X - X.mean(axis=0, keepdims=True)
    G = Xc @ Xc.T
    ev = np.linalg.eigvalsh(G)[::-1]
    ev = np.clip(ev, 0, None)
    return ev


def k_energie(ev, frac=0.5):
    c = np.cumsum(ev) / ev.sum()
    return int(np.searchsorted(c, frac) + 1)


def matrice_indicateurs(sets, E):
    T, L, k = sets.shape
    X = np.zeros((T, L * E), dtype=np.float32)
    for c in range(L):
        for i in range(k):
            X[np.arange(T), c * E + sets[:, c, i]] = 1.0
    return X


def nul_couches_independantes(sets, rng):
    T, L, k = sets.shape
    out = sets.copy()
    for c in range(L):
        out[:, c, :] = sets[rng.permutation(T), c, :]
    return out


def synergies_plantees(rng):
    T, D = 800, 300
    B = (rng.random((3, D)) < 0.1).astype(np.float64) * rng.random((3, D))
    A = rng.exponential(1.0, (T, 3))
    X = A @ B
    ev = gram_energies(X)
    rang = int((ev > 1e-6 * ev.max()).sum())
    return X, rang


def banc_ed(dossier):
    rng = np.random.default_rng(20261026)
    res = {}
    for modele in ("20b", "120b"):
        res[modele] = {}
        for genre in GENRES:
            sets, poids, E = charger(dossier, modele, genre)
            ev = gram_energies(matrice_indicateurs(sets, E))
            nul = nul_couches_independantes(sets, rng)
            ev_n = gram_energies(matrice_indicateurs(nul, E))
            nul2 = nul_couches_independantes(sets, rng)
            ev_n2 = gram_energies(matrice_indicateurs(nul2, E))
            lig = {"K50_reel": k_energie(ev), "K50_nul": k_energie(ev_n), "K50_nul2": k_energie(ev_n2),
                   "K80_reel": k_energie(ev, 0.8), "K80_nul": k_energie(ev_n, 0.8),
                   "energie_1ere_reel": float(ev[0] / ev.sum()), "energie_1ere_nul": float(ev_n[0] / ev_n.sum()),
                   "T": int(sets.shape[0])}
            lig["rapport_K50"] = lig["K50_nul"] / lig["K50_reel"]
            lig["rapport_nul_nul"] = lig["K50_nul"] / lig["K50_nul2"]
            res[modele][genre] = lig
            print(modele, genre, lig, flush=True)
    return res


def verdict_ed(res):
    out = {}
    for modele in res:
        r = [res[modele][g]["rapport_K50"] for g in GENRES]
        rn = [res[modele][g]["rapport_nul_nul"] for g in GENRES]
        out[modele] = {"rapports": r, "mediane": statistics.median(r), "nul_nul": rn,
                       "nul_nul_dans_intervalle": all(0.8 <= x <= 1.25 for x in rn),
                       "passe": statistics.median(r) >= 2.0}
    return out


# ---------------------------------------------------------------- E-E et E-F

def queue_fenetre(sets, E):
    """sets : (P, L, k). Par couche : experts touchés, queue = touchés par <= 2 jetons."""
    P, L, k = sets.shape
    touches = queue = aff_q = aff = 0
    for c in range(L):
        cnt = np.bincount(sets[:, c, :].ravel(), minlength=E)
        t = cnt > 0
        q = t & (cnt <= 2)
        touches += int(t.sum())
        queue += int(q.sum())
        aff_q += int(cnt[q].sum())
        aff += int(cnt.sum())
    return {"touches": touches, "queue": queue, "queue_parmi_touches": queue / touches,
            "affectations_queue": aff_q / aff}


def banc_ee(dossier):
    res = {}
    for modele in ("20b", "120b"):
        res[modele] = {}
        for genre in GENRES:
            sets, poids, E = charger(dossier, modele, genre)
            T = sets.shape[0]
            for P in (128, 512):
                lig = []
                for d in range(0, T - P + 1, P):
                    lig.append(queue_fenetre(sets[d:d + P], E))
                res[modele][f"{genre}|{P}"] = {
                    "fenetres": len(lig),
                    "queue_parmi_touches": statistics.fmean(x["queue_parmi_touches"] for x in lig),
                    "affectations_queue": statistics.fmean(x["affectations_queue"] for x in lig),
                    "touches_sur_E": statistics.fmean(x["touches"] for x in lig) / (sets.shape[1] * E)}
                print(modele, genre, P, res[modele][f"{genre}|{P}"], flush=True)
    return res


def verdict_ee(res):
    out = {}
    for modele in res:
        det = {}
        for P in (128, 512):
            q = [res[modele][f"{g}|{P}"]["queue_parmi_touches"] for g in GENRES]
            a = [res[modele][f"{g}|{P}"]["affectations_queue"] for g in GENRES]
            det[str(P)] = {"queue": q, "affectations": a,
                           "passe": statistics.median(q) >= 0.20 and statistics.median(a) <= 0.02}
        out[modele] = {"detail": det, "passe": any(x["passe"] for x in det.values())}
    return out


def union_gamma(sets, E, gmax):
    T, L, k = sets.shape
    out = []
    for g in range(1, gmax + 1):
        tot, n = 0, 0
        for c in range(L):
            col = sets[:, c, :]
            for d in range(0, T - g + 1, g):
                tot += len(set(col[d:d + g].ravel().tolist()))
                n += 1
        out.append(tot / n)
    return out


def banc_ef(dossier):
    res = {}
    for modele in ("20b", "120b"):
        res[modele] = {}
        for genre in GENRES:
            sets, poids, E = charger(dossier, modele, genre)
            u = union_gamma(sets, E, 8)
            res[modele][genre] = {"U": u, "U_sur_gk": [u[g - 1] / (g * K) for g in range(1, 9)]}
            print(modele, genre, [round(x, 3) for x in res[modele][genre]["U_sur_gk"]], flush=True)
    return res


# ---------------------------------------------------------------- principal

def ecrire(nom, obj):
    SORTIE.mkdir(parents=True, exist_ok=True)
    def conv(o):
        if isinstance(o, np.generic):
            return o.item()
        if isinstance(o, np.ndarray):
            return o.tolist()
        raise TypeError(type(o))
    (SORTIE / nom).write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=conv), encoding="utf-8")
    print("écrit", SORTIE / nom)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dossier")
    ap.add_argument("--extraire", action="store_true")
    ap.add_argument("--temoins", action="store_true")
    ap.add_argument("--banc")
    ap.add_argument("--casser", action="store_true")
    a = ap.parse_args()
    sous_la_normale()
    if a.extraire:
        extraire(a.dossier)
    elif a.temoins:
        r = temoins(a.dossier)
        for k, v in r["rapport"].items():
            print(k, "ok " if v["reussi"] else "NON", {x: y for x, y in v.items() if x != "reussi"} if not v["reussi"] else "")
        print(r["verdict"])
        ecrire("temoins.json", r)
    elif a.banc == "ea":
        res = banc_ea(a.dossier, a.casser)
        suf = "-casse" if a.casser else ""
        ecrire(f"ea-brut{suf}.json", res)
        v = {c: verdict_ea(res, c) for c in ("actr_d0.5", "assoc")}
        if not a.casser:
            for c in ("actr_d0.3", "actr_d0.8"):
                v[c] = verdict_ea(res, c)
        ecrire(f"ea-verdict{suf}.json", v)
        print(json.dumps({c: {m: x["passe"] for m, x in vv.items()} for c, vv in v.items()}))
    elif a.banc == "eb":
        res = banc_eb(a.dossier)
        ecrire("eb-brut.json", res)
        v = verdict_eb(res)
        ecrire("eb-verdict.json", v)
        print(json.dumps({m: x["passe"] for m, x in v.items()}))
    elif a.banc == "ec":
        res = banc_ec(a.dossier)
        ecrire("ec-brut.json", res)
        v = verdict_ec(res)
        ecrire("ec-verdict.json", v)
        print(json.dumps({m: x["passe"] for m, x in v.items()}))
    elif a.banc == "ed":
        res = banc_ed(a.dossier)
        ecrire("ed-brut.json", res)
        v = verdict_ed(res)
        ecrire("ed-verdict.json", v)
        print(json.dumps({m: x["passe"] for m, x in v.items()}))
    elif a.banc == "ee":
        res = banc_ee(a.dossier)
        ecrire("ee-brut.json", res)
        v = verdict_ee(res)
        ecrire("ee-verdict.json", v)
        print(json.dumps({m: x["passe"] for m, x in v.items()}))
    elif a.banc == "ef":
        res = banc_ef(a.dossier)
        ecrire("ef-brut.json", res)
    else:
        ap.error("rien à faire")


if __name__ == "__main__":
    main()
