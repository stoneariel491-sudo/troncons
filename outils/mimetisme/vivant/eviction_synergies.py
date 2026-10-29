"""E-J : éviction pilotée par le prédicteur de synergies (pas de deux jetons). Seuil : seuil-declare.md (E-J).
Usage : python -I eviction_synergies.py DOSSIER_TRACES [--temoins-seulement]
"""
import importlib.util
import json
import statistics
import sys
from pathlib import Path

import numpy as np

ici = Path(__file__).resolve().parent


def charger_module(nom, fichier):
    spec = importlib.util.spec_from_file_location(nom, ici / fichier)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


bt = charger_module("bt", "bancs_traces.py")
sys.argv = [sys.argv[0]] + [a for a in sys.argv[1:]]
HL = 8.0
SUF = ""
if "--hl" in sys.argv:           # E-J2 : même chose avec la popularité de demi-vie réglée (déclaré avant calcul)
    i = sys.argv.index("--hl")
    HL = float(sys.argv[i + 1])
    SUF = f"-hl{int(HL)}"
    del sys.argv[i:i + 2]
ps = charger_module("ps", "predicteur_synergies.py")
bt.sous_la_normale()
dossier = sys.argv[1]
ins = bt.instrument()


def apprendre_pas(Xs, k, pas, melange=False, rng=None):
    A = np.vstack([X[:-pas] for X in Xs])
    B = np.vstack([X[pas:] for X in Xs])
    if melange:
        B = B[rng.permutation(len(B))]
    mu = A.mean(axis=0)
    Ac = A - mu
    V = ps.svd_aleatoire(Ac, k)
    Z = Ac @ V
    nu = B.mean(axis=0)
    lam = ps.ALPHA * (Z ** 2).sum() / Z.shape[1] * 1e-3
    W = np.linalg.solve(Z.T @ Z + lam * np.eye(k), Z.T @ (B - nu))
    return mu, V, W, nu


class PolSyn:
    """Éviction du plus petit rang-somme de (prédicteur, popularité à décroissance). `pred` : (T-2, E) scores de
    cette couche, ligne i = prédiction de l'usage au jeton i+2 faite avec X_i. Au jeton t', on lit la ligne t'-1."""

    def __init__(self, E, pred=None, mode="syn"):
        self.E, self.pred, self.mode = E, pred, mode
        self.p1 = np.zeros(E)
        self.dec = 0.5 ** (1 / HL)
        self.dernier = {}
        self.ligne = None

    def voir(self, t, s):
        self.p1 *= self.dec
        for e in s:
            self.p1[e] += 1.0
        self.ligne = self.pred[t - 1] if (self.pred is not None and 1 <= t <= len(self.pred)) else None

    def demande(self, e, t, s):
        self.dernier[e] = t

    def victime(self, cands, t, s):
        c = np.array(cands)
        r1 = np.unique(self.p1[c], return_inverse=True)[1]       # rang dense : les égalités restent égales
        if self.mode == "p1" or self.ligne is None:
            tot = r1
        else:
            r4 = np.unique(self.ligne[c], return_inverse=True)[1]
            tot = r1 + r4
        pire = min(range(len(cands)), key=lambda i: (tot[i], self.dernier.get(cands[i], -1)))
        return cands[pire]


def lancer():
    rng = np.random.default_rng(20261027)
    res = {}
    for modele in ("20b", "120b"):
        jeu = {g: bt.charger(dossier, modele, g)[0] for g in bt.GENRES}
        E = bt.charger(dossier, modele, bt.GENRES[0])[2]
        L = jeu[bt.GENRES[0]].shape[1]
        X = {g: bt.matrice_indicateurs(jeu[g], E).astype(np.float64) for g in bt.GENRES}
        res[modele] = {}
        for g in bt.GENRES:
            autres = [x for x in bt.GENRES if x != g]
            Xtr = [X[x] for x in autres]
            m2 = apprendre_pas(Xtr, ps.K_COMP, 2)
            m2mel = apprendre_pas(Xtr, ps.K_COMP, 2, melange=True, rng=rng)
            P2 = ps.predire(m2, X[g][:-2])
            P2mel = ps.predire(m2mel, X[g][:-2])
            Pcst = np.zeros_like(P2)
            for C in bt.BUDGETS[modele]:
                lig = {"lru": [], "lfu8": [], "p1": [], "syn2": [], "syn2_melange": [], "syn2_constante": []}
                for c in range(L):
                    seq = bt.par_couche(jeu[g], c)
                    sl = slice(c * E, (c + 1) * E)
                    lig["lru"].append(ins.cache_lru(seq, C))
                    lig["lfu8"].append(ins.cache_lfu(seq, C, 8.0))
                    lig["p1"].append(bt.simuler(seq, C, PolSyn(E, None, "p1"), E))
                    lig["syn2"].append(bt.simuler(seq, C, PolSyn(E, P2[:, sl]), E))
                    lig["syn2_melange"].append(bt.simuler(seq, C, PolSyn(E, P2mel[:, sl]), E))
                    lig["syn2_constante"].append(bt.simuler(seq, C, PolSyn(E, Pcst[:, sl]), E))
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
            gains, gains_mel = [], []
            for g in bt.GENRES:
                r = res[modele][f"{g}|{C}"]
                meilleur = max(r["lru"], r["lfu8"], r["p1"])
                gains.append(((1 - meilleur) - (1 - r["syn2"])) / (1 - meilleur))
                gains_mel.append(((1 - meilleur) - (1 - r["syn2_melange"])) / (1 - meilleur))
            med, pos = statistics.median(gains), sum(1 for x in gains if x > 0)
            ecart_const = max(abs(res[modele][f"{g}|{C}"]["syn2_constante"] - res[modele][f"{g}|{C}"]["p1"]) for g in bt.GENRES)
            passe = med >= 0.10 and pos >= 4
            det[str(C)] = {"gains": gains, "mediane": med, "positifs": pos, "gains_melange": gains_mel,
                           "mediane_melange": statistics.median(gains_mel), "ecart_constante_vs_p1": ecart_const,
                           "passe": passe}
            ok &= passe
        out[modele] = {"detail": det, "passe": ok}
    return out


if __name__ == "__main__":
    res = lancer()
    bt.ecrire(f"ej{SUF}-brut.json", res)
    v = verdict(res)
    bt.ecrire(f"ej{SUF}-verdict.json", v)
    print(json.dumps({m: x["passe"] for m, x in v.items()}))
