"""E-L : éviction pilotée par la mémoire épisodique (cosinus exact, pas de deux jetons). Seuil : seuil-declare.md (E-L).
Usage : python -I eviction_episodique.py DOSSIER_TRACES
"""
import importlib.util
import statistics
import sys
from pathlib import Path

import numpy as np

ici = Path(__file__).resolve().parent
dossier = sys.argv[1]
sys.argv = [sys.argv[0], dossier, "--hl", "64"]       # eviction_synergies lit --hl : popularité de demi-vie 64


def charger_module(nom, fichier):
    spec = importlib.util.spec_from_file_location(nom, ici / fichier)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ev = charger_module("ev", "eviction_synergies.py")
bt = ev.bt
ins = ev.ins


def scores_epi(X, k, rng, hasard=False):
    """Ligne i = prédiction de l'usage au jeton i + 2... (voir seuil) : voisins j <= i - 2, vote X[j + 2], j + 2 <= i."""
    T = X.shape[0]
    S = X @ X.T
    out = np.zeros_like(X)
    for i in range(2, T):
        row = S[i, :i - 1]                            # j = 0 .. i - 2
        kk = min(k, i - 1)
        idx = np.argpartition(-row, kk - 1)[:kk]
        w = row[idx]
        suc = idx + 2
        if hasard:
            suc = rng.integers(2, i + 1, size=kk)
        out[i] = w @ X[suc]
    return out


def lancer():
    rng = np.random.default_rng(20261027)
    res = {}
    for modele in ("20b", "120b"):
        jeu = {g: bt.charger(ev.dossier, modele, g)[0] for g in bt.GENRES}
        E = bt.charger(ev.dossier, modele, bt.GENRES[0])[2]
        L = jeu[bt.GENRES[0]].shape[1]
        res[modele] = {}
        for g in bt.GENRES:
            X = bt.matrice_indicateurs(jeu[g], E).astype(np.float32)
            P8 = scores_epi(X, 8, rng)
            P1 = scores_epi(X, 1, rng)
            PH = scores_epi(X, 8, rng, hasard=True)
            P0 = np.zeros_like(P8)
            for C in bt.BUDGETS[modele]:
                lig = {"lru": [], "lfu8": [], "p1": [], "epi": [], "epi_k1": [], "epi_succ_hasard": [], "epi_constante": []}
                for c in range(L):
                    seq = bt.par_couche(jeu[g], c)
                    sl = slice(c * E, (c + 1) * E)
                    lig["lru"].append(ins.cache_lru(seq, C))
                    lig["lfu8"].append(ins.cache_lfu(seq, C, 8.0))
                    lig["p1"].append(bt.simuler(seq, C, ev.PolSyn(E, None, "p1"), E))
                    lig["epi"].append(bt.simuler(seq, C, ev.PolSyn(E, P8[:, sl]), E))
                    lig["epi_k1"].append(bt.simuler(seq, C, ev.PolSyn(E, P1[:, sl]), E))
                    lig["epi_succ_hasard"].append(bt.simuler(seq, C, ev.PolSyn(E, PH[:, sl]), E))
                    lig["epi_constante"].append(bt.simuler(seq, C, ev.PolSyn(E, P0[:, sl]), E))
                moy = {k: statistics.fmean(v) for k, v in lig.items()}
                res[modele][f"{g}|{C}"] = moy
                print(modele, g, C, {k: round(v, 4) for k, v in moy.items()}, flush=True)
    return res


def verdict(res):
    out = {}
    for modele in res:
        ok = True
        det = {}
        for C in bt.BUDGETS[modele]:
            gains, gh, g1 = [], [], []
            for g in bt.GENRES:
                r = res[modele][f"{g}|{C}"]
                meilleur = max(r["lru"], r["lfu8"], r["p1"])
                f = lambda k: ((1 - meilleur) - (1 - r[k])) / (1 - meilleur)
                gains.append(f("epi")); gh.append(f("epi_succ_hasard")); g1.append(f("epi_k1"))
            med, pos = statistics.median(gains), sum(1 for x in gains if x > 0)
            ecart = max(abs(res[modele][f"{g}|{C}"]["epi_constante"] - res[modele][f"{g}|{C}"]["p1"]) for g in bt.GENRES)
            det[str(C)] = {"gains": gains, "mediane": float(med), "positifs": int(pos), "gains_succ_hasard": gh,
                           "mediane_succ_hasard": float(statistics.median(gh)), "gains_k1": g1,
                           "mediane_k1": float(statistics.median(g1)), "ecart_constante_vs_p1": float(ecart),
                           "passe": bool(med >= 0.10 and pos >= 4)}
            ok &= det[str(C)]["passe"]
        out[modele] = {"detail": det, "passe": bool(ok)}
    return out


if __name__ == "__main__":
    res = lancer()
    bt.ecrire("el-brut.json", res)
    v = verdict(res)
    bt.ecrire("el-verdict.json", v)
    print({m: x["passe"] for m, x in v.items()})
