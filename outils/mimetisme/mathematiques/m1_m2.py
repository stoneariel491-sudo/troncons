"""Éclaireur « mathématiques et théorie de l'information » : mesures M1 et M2.

Seuils et témoins déclarés avant toute lecture : mesures/mimetisme/mathematiques/00-seuils-declares.md
(commit 2017fcf). Un fil, priorité sous la normale, aucun fichier modèle, aucune carte.

M1 : un prédicteur causal des demandes d'experts (moyennes mobiles exponentielles + régression
     logistique, la forme la plus simple de « prédire = compresser », Vitter et Krishnan 1996) mène-t-il
     un cache global plus près de Belady que LRU et LFU ?
M2 : l'union des experts sur T jetons consécutifs (plafond de la vérification groupée).

Usage : python -I m1_m2.py --traces <dossier extrait> --sortie <dossier> [--temoins-seuls]
"""
import argparse
import ctypes
import importlib.util
import json
import math
import os
import random
import sys
import time

import numpy as np

HALF = (1, 3, 8, 24, 96)  # demi-vies des moyennes mobiles, en jetons
GRAINE = 20261026
OUTILS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")


def sous_la_normale():
    try:
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    except Exception:
        pass


def charger(nom):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(OUTILS, nom + ".py"))
    m = importlib.util.module_from_spec(spec)
    sys.modules[nom] = m
    spec.loader.exec_module(m)
    return m


# ---------------------------------------------------------------- traces
def vers_tableau(jetons, L, E):
    """bool [T, L, E] : l'expert e est choisi à la couche l du jeton t."""
    A = np.zeros((len(jetons), L, E), dtype=bool)
    for t, jt in enumerate(jetons):
        for l, c in enumerate(jt):
            A[t, l, c] = True
    return A


# ---------------------------------------------------------------- prédicteur
def alphas():
    return np.array([0.5 ** (1.0 / h) for h in HALF])


def traits(M):
    """M : [5, L, E] moyennes mobiles -> traits [L, E, 11] : 1, 5 moyennes, 5 log(moyenne + 0,01)."""
    m = np.moveaxis(M, 0, -1)
    return np.concatenate([np.ones(m.shape[:-1] + (1,)), m, np.log(m + 0.01)], axis=-1)


def ajuster(tableaux, iterations=8):
    """Régression logistique (IRLS) de A[t] sur les traits bâtis avec l'historique jusqu'à t-1."""
    a = alphas()[:, None, None]
    w = np.zeros(11)
    for it in range(iterations):
        H = np.zeros((11, 11))
        g = np.zeros(11)
        ll = 0.0
        n = 0
        for A in tableaux:
            M = np.zeros((len(HALF),) + A.shape[1:])
            for t in range(A.shape[0]):
                X = traits(M).reshape(-1, 11)
                y = A[t].reshape(-1).astype(float)
                z = X @ w
                p = 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))
                s = p * (1 - p) + 1e-9
                H += (X * s[:, None]).T @ X
                g += X.T @ (y - p)
                ll += -np.sum(y * np.log(p + 1e-12) + (1 - y) * np.log(1 - p + 1e-12))
                n += y.size
                M = a * M + (1 - a) * A[t][None]
        w = w + np.linalg.solve(H + 1e-6 * np.eye(11), g)
        print(f"  IRLS {it}: log-perte {ll / n * 36 * 128 / 36:.5f} nat par (couche, expert)", flush=True)
    return w


def logperte_bits(A, w):
    """Bits par décision (jeton, couche) : log-perte binaire sommée sur les 128 experts, en bits."""
    a = alphas()[:, None, None]
    M = np.zeros((len(HALF),) + A.shape[1:])
    tot = 0.0
    for t in range(A.shape[0]):
        X = traits(M).reshape(-1, 11)
        y = A[t].reshape(-1).astype(float)
        p = 1.0 / (1.0 + np.exp(-np.clip(X @ w, -30, 30)))
        tot += -np.sum(y * np.log2(p + 1e-12) + (1 - y) * np.log2(1 - p + 1e-12))
        M = a * M + (1 - a) * A[t][None]
    return tot / (A.shape[0] * A.shape[1])


def logperte_bits_frequence(A):
    """Référence : fréquence fixe par (couche, expert) sur la trace elle-même (borne basse du modèle
    sans mémoire, avantageux car il voit toute la trace)."""
    f = A.mean(axis=0).clip(1e-6, 1 - 1e-6)
    h = -(f * np.log2(f) + (1 - f) * np.log2(1 - f)).sum(axis=-1)
    return float(h.mean())


# ---------------------------------------------------------------- cache PB
def pb(A, N, w=None, oracle=False, fp=None):
    """Politique PB : éviction du plus grand d + L(1-p)/p. Modèle du projet : on insère le groupe,
    puis on évince jusqu'à N en épargnant le groupe courant. Rend le taux de succès en accès."""
    T, L, E = A.shape
    a = alphas()[:, None, None]
    M = np.zeros((len(HALF),) + (L, E))
    idx = np.arange(L * E)
    couche = idx // E
    dans = np.zeros(L * E, dtype=bool)
    p = np.full(L * E, 0.03)  # avant tout historique
    if oracle is True:
        p[:] = 1e-3
        for l in range(L):
            p[l * E:(l + 1) * E] = np.where(A[0, l], 1 - 1e-3, 1e-3)
    elif w is not None:
        p = (1.0 / (1.0 + np.exp(-np.clip(traits(M).reshape(-1, 11) @ w, -30, 30))))
        if oracle == "mixte":
            for l in range(L):
                p[l * E:(l + 1) * E] = np.where(A[0, l], 1 - 1e-3, p[l * E:(l + 1) * E])
    dist = np.empty((L, L * E))
    for l in range(L):
        d = (couche - l) % L
        d[d == 0] = L
        dist[l] = d
    succes = total = 0
    n = 0
    sets = [[np.flatnonzero(A[t, l]) for l in range(L)] for t in range(T)]
    for t in range(T):
        for l in range(L):
            g = l * E + sets[t][l]
            total += len(g)
            for x in g:
                if dans[x]:
                    succes += 1
            if not dans[g].all():
                dans[g] = True
                n = int(dans.sum())
            # mise à jour de l'estimation de la couche l (historique jusqu'à t inclus)
            M[:, l, :] = a[:, 0, :] * M[:, l, :] + (1 - a[:, 0, :]) * A[t, l][None]
            if oracle is True:
                tt = t + 1 if t + 1 < T else t
                p[l * E:(l + 1) * E] = np.where(A[tt, l], 1 - 1e-3, 1e-3)
            elif w is not None:
                X = traits(M[:, l:l + 1, :]).reshape(-1, 11)
                pp = 1.0 / (1.0 + np.exp(-np.clip(X @ w, -30, 30)))
                if oracle == "mixte":  # témoin T2bis : le prédicteur, corrigé par l'indicateur vrai du prochain jeton
                    tt = t + 1 if t + 1 < T else t
                    pp = np.where(A[tt, l], 1 - 1e-3, pp)
                p[l * E:(l + 1) * E] = pp
            if n > N:
                prot = np.zeros(L * E, dtype=bool)
                prot[g] = True
                cle = dist[l] + L * (1 - p) / np.clip(p, 1e-4, 1.0)
                cle = np.where(dans & ~prot, cle, -1.0)
                k = n - N
                if k >= len(g) * 0 + 1:
                    ev = np.argpartition(-cle, k - 1)[:k]
                    dans[ev] = False
                    n -= k
    return succes / total


def reference(A, N, g, jetons):
    """LRU, LFU (4 demi-vies, la meilleure), statique oracle, Belady : outils du projet, inchangés.
    `jetons` = la trace d'origine, avec l'ordre du score à l'intérieur de chaque groupe (LRU en dépend :
    la première version triait par numéro d'expert et le témoin T1 a tombé de 5,4e-5)."""
    E = A.shape[2]
    gr = g.flux(jetons, E)
    L = A.shape[1]
    r = {"lru": g.g_lru(gr, N), "statique_oracle": g.g_statique(gr, N, gr), "belady": g.g_belady(gr, N)}
    lfu = {h: g.g_lfu(gr, N, L, demi_vie=float(h)) for h in (2, 8, 32, 128)}
    r["lfu_par_demi_vie"] = lfu
    r["lfu_8"] = lfu[8]
    r["lfu_meilleur"] = max(lfu.values())
    return r


# ---------------------------------------------------------------- M2
def union_moyenne(A, Ts):
    T, L, E = A.shape
    cs = np.concatenate([np.zeros((1, L, E), dtype=np.int16), np.cumsum(A, axis=0, dtype=np.int16)], axis=0)
    out = {}
    for w in Ts:
        if w > T:
            continue
        u = ((cs[w:] - cs[:-w]) > 0).sum(axis=-1)  # [T-w+1, L]
        out[w] = u.mean(axis=0)  # par couche
    return out


def temoins_m2(rng):
    res = {}
    L, E, k, T = 36, 128, 4, 4000
    Au = np.zeros((T, L, E), dtype=bool)
    for t in range(T):
        for l in range(L):
            Au[t, l, rng.sample(range(E), k)] = True
    Ts = (1, 2, 4, 8, 16)
    u = union_moyenne(Au, Ts)
    res["W1_uniforme"] = {str(w): [float(u[w].mean()), E * (1 - (1 - k / E) ** w)] for w in Ts}
    Af = np.zeros((T, L, E), dtype=bool)
    Af[:, :, :k] = True
    uf = union_moyenne(Af, Ts)
    res["W2_fige"] = {str(w): [float(uf[w].mean()), float(k)] for w in Ts}
    return res


# ---------------------------------------------------------------- principal
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--traces", required=True)
    ap.add_argument("--sortie", required=True)
    ap.add_argument("--temoins-seuls", action="store_true")
    a = ap.parse_args()
    sous_la_normale()
    os.makedirs(a.sortie, exist_ok=True)
    g = charger("gptoss_localite")
    cl = charger("chargement_localite")
    rng = random.Random(GRAINE)
    out = {"graine": GRAINE, "halflives": HALF}
    t0 = time.time()

    def lire(nom):
        jetons, E = cl.lire_trace(os.path.join(a.traces, nom))
        return vers_tableau(jetons, len(jetons[0]), E), jetons

    # ---- témoin T1 : les politiques du projet redonnent leurs propres nombres
    Aw, jw = lire("w120b.wiki.generation.trace")
    ref = json.load(open(os.path.join(OUTILS, "..", "mesures", "localite-gpt-oss", "cache-base-contre-optimum.json")))["120b"]
    r = reference(Aw, 323, g, jw)
    ecarts = {"lru": abs(r["lru"] - ref["lru"]), "lfu": abs(r["lfu_8"] - ref["lfu"]),
              "statique": abs(r["statique_oracle"] - ref["statique_oracle"]), "belady": abs(r["belady"] - ref["belady"])}
    out["T1"] = {"ecarts": ecarts, "tient": all(v < 1e-9 for v in ecarts.values())}
    print("T1", out["T1"], flush=True)

    # ---- M2 (témoins puis mesure)
    out["M2_temoins"] = temoins_m2(rng)
    print("M2 temoins", json.dumps(out["M2_temoins"]), flush=True)
    if a.temoins_seuls:
        json.dump(out, open(os.path.join(a.sortie, "temoins.json"), "w"), indent=1)
        return 0
    lect = ["t120b.prose-en.lecture.trace", "t120b.code.lecture.trace", "t120b.dialogue.lecture.trace",
            "t120b.prose-fr.lecture.trace", "w120b.wiki.lecture.trace"]
    Ts = (1, 2, 3, 4, 6, 8, 12, 16, 24, 32)
    m2 = {}
    tabs = {}
    jets = {}
    for nom in lect:
        A, jt = lire(nom)
        tabs[nom] = A
        jets[nom] = jt
        u = union_moyenne(A, Ts)
        m2[nom] = {str(w): {"union_par_couche_moyenne": float(u[w].mean()), "G": float(4 * w / u[w].mean()),
                            "G_min_couche": float(4 * w / u[w].max()), "G_max_couche": float(4 * w / u[w].min())}
                   for w in u}
        # cassure : ordre mélangé
        perm = np.random.default_rng(GRAINE).permutation(A.shape[0])
        us = union_moyenne(A[perm], Ts)
        m2[nom]["melange"] = {str(w): float(4 * w / us[w].mean()) for w in us}
    out["M2"] = m2
    for nom in lect:
        print("M2", nom, {w: round(m2[nom][w]["G"], 3) for w in m2[nom] if w != "melange"}, flush=True)

    # ---- M1
    train = [tabs["t120b.prose-en.lecture.trace"], tabs["t120b.code.lecture.trace"]]
    print("ajustement du prédicteur sur 2 traces...", flush=True)
    w = ajuster(train)
    out["M1_poids"] = [float(x) for x in w]
    tests = {"dialogue (lecture)": (tabs["t120b.dialogue.lecture.trace"], jets["t120b.dialogue.lecture.trace"]),
             "prose-fr (lecture)": (tabs["t120b.prose-fr.lecture.trace"], jets["t120b.prose-fr.lecture.trace"]),
             "wiki (lecture)": (tabs["w120b.wiki.lecture.trace"], jets["w120b.wiki.lecture.trace"])}
    tests["wiki (génération)"] = lire("w120b.wiki.generation.trace")
    tests["prose-en (génération)"] = lire("t120b.prose-en.generation.trace")
    m1 = {}
    for nom, (A, JT) in tests.items():
        m1[nom] = {"jetons": int(A.shape[0]),
                   "bits_par_decision_modele": logperte_bits(A, w),
                   "bits_par_decision_frequence_de_la_trace": logperte_bits_frequence(A)}
        perm = np.random.default_rng(GRAINE).permutation(A.shape[0])
        Am = A[perm]
        JTm = [JT[i] for i in perm]
        for N in (323, 922):
            t1 = time.time()
            ref = reference(A, N, g, JT)
            h = pb(A, N, w)
            ho = pb(A, N, oracle=True)
            refm = reference(Am, N, g, JTm)
            hm = pb(Am, N, w)
            base = max(ref["lru"], ref["lfu_meilleur"])
            basem = max(refm["lru"], refm["lfu_meilleur"])
            m1[nom][str(N)] = {"ref": ref, "pb": h, "pb_oracle_un_jeton": ho, "delta": h - base,
                               "delta_oracle": ho - base, "melange": {"pb": hm, "base": basem, "delta": hm - basem},
                               "part_de_l_ecart_a_belady_prise": (h - base) / (ref["belady"] - base),
                               "secondes": time.time() - t1}
            print(f"M1 {nom} N={N}: LRU {ref['lru']:.4f} LFU* {ref['lfu_meilleur']:.4f} PB {h:.4f} (delta {h - base:+.4f}) "
                  f"oracle {ho:.4f} Belady {ref['belady']:.4f} | mélangé delta {hm - basem:+.4f}", flush=True)
    out["M1"] = m1
    out["secondes_total"] = time.time() - t0
    json.dump(out, open(os.path.join(a.sortie, "m1_m2.json"), "w"), indent=1)
    print("fini", out["secondes_total"], flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
