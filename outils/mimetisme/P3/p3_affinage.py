"""P3, affinage post hoc de l'étage A (déclaré dans mesures/mimetisme/P3/01-affinage-declare.md avant ce lancement).

Quatre choses : grille fine de bêta et franchissement de -10 % de défauts ; incertitude par fenêtre de 511 positions ; seconde politique
d'éviction (LFU de demi-vie 8, celle de E7) pour savoir si le gain est un artefact du LRU ; le tout sur les logits réels déjà calculés
(~/dev/essais/troncons/mimetisme/P3/logits-20b-eval.npy, 31 Mo).

Usage : python -I -X utf8 p3_affinage.py
"""
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "2"

import csv
import heapq
import json
import math
import sys
import time

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import p3_routage as P

FINS = [0.04, 0.05, 0.06, 0.07, 0.08, 0.15, 0.2]
FENETRE = 511


class CacheLFU:
    """LFU à décroissance exponentielle (demi-vie en positions), règle de groupe : les quatre experts du groupe ne sont pas évincés.
    Même logique que E7 (outils/mimetisme/humain/e7_marge.py) : insertion du groupe, puis éviction jusqu'à N en sautant les experts du groupe."""

    def __init__(self, n, total, demi_vie=8.0):
        self.n = n
        self.ld = math.log(0.5) / demi_vie
        self.cle, self.vu, self.cache, self.tas = {}, {}, set(), []
        self.res = np.zeros(total)
        self.defauts = 0
        self.compteur = 0

    def groupe(self, ids, t):
        manque = []
        for x in ids:
            anc = self.cle.get(x)
            v = 1.0 if anc is None else math.exp(anc + t * self.ld) + 1.0
            self.cle[x] = math.log(v) - t * self.ld
            self.compteur += 1
            self.vu[x] = self.compteur
            absent = x not in self.cache
            manque.append(absent)
            if absent:
                self.defauts += 1
                self.cache.add(x)
                self.res[x] = 1.0
            heapq.heappush(self.tas, (self.cle[x], self.vu[x], x))
        dans = set(ids)
        mis = []
        while len(self.cache) > self.n:
            c, v, x = heapq.heappop(self.tas)
            if x not in self.cache or self.cle[x] != c or self.vu[x] != v:
                continue
            if x in dans:
                mis.append((c, v, x))
                continue
            self.cache.remove(x)
            self.res[x] = 0.0
        for e in mis:
            heapq.heappush(self.tas, e)
        return manque


def croisement(points, cible=-0.10):
    """points : liste triée de (beta, variation_relative, part_changee, kl_prior). Interpolation linéaire au franchissement de `cible`."""
    for (b0, v0, c0, k0), (b1, v1, c1, k1) in zip(points, points[1:]):
        if v0 > cible >= v1:
            a = (cible - v0) / (v1 - v0)
            return {"beta": b0 + a * (b1 - b0), "part_changee": c0 + a * (c1 - c0), "kl_prior": k0 + a * (k1 - k0)}
    return None


def main():
    os.makedirs(P.SORTIE, exist_ok=True)
    journal = []
    log = lambda s: (journal.append(s), print(s, flush=True))
    t0 = time.time()
    Z = np.load(os.path.join(P.LOURDS, "logits-20b-eval.npy"))
    ORD = P.preparer(Z)
    T, L, E = Z.shape
    brut = json.load(open(os.path.join(P.SORTIE, "etage-A.json"), encoding="utf-8"))
    officiel = brut["lignes"]
    res_off = {k: v["defauts"] for k, v in brut["defauts_beta0"].items()}
    res = {"fin": [], "croisement_moins_10": {}, "fenetres": {}, "lfu": {}}
    # 1. grille fine
    lignes = list(officiel)
    for nom, frac in P.BUDGETS.items():
        n = round(frac * L * E)
        S0, _, dd0 = P.simuler(Z, ORD, n, 0.0)
        d0 = dd0
        assert d0 == res_off[nom], (d0, res_off[nom])
        for variante in ("V1", "V2"):
            for beta in FINS:
                S, M, d = P.simuler(Z, ORD, n, beta, variante)
                st = P.statistiques(Z, ORD, S0, S)
                lignes.append({"variante": variante, "budget": nom, "N": n, "beta": beta, "defauts": d, "variation_relative": d / d0 - 1.0, **st,
                               "kl_prior": P.KL_PAR_CELLULE * st["part_cellules_changees"]})
                log(f"fin {variante} N={n} β={beta}: défauts {d} ({(d / d0 - 1) * 100:+.1f} %), cellules {st['part_cellules_changees'] * 100:.2f} %")
    for variante in ("V1", "V2"):
        for nom in P.BUDGETS:
            pts = sorted(((l["beta"], l["variation_relative"], l["part_cellules_changees"], l["kl_prior"]) for l in lignes
                          if l["variante"] == variante and l["budget"] == nom and l["beta"] >= 0.0), key=lambda p: p[0])
            res["croisement_moins_10"][f"{variante}/{nom}"] = croisement(pts)
            log(f"franchissement de -10 % {variante} budget {nom} : {res['croisement_moins_10'][f'{variante}/{nom}']}")
    res["fin"] = [l for l in lignes if l["beta"] in FINS]
    # 2. fenêtres de 511 positions
    for nom, frac in P.BUDGETS.items():
        n = round(frac * L * E)
        S0, M0, d0 = P.simuler(Z, ORD, n, 0.0)
        base = M0.sum((1, 2)).reshape(-1, FENETRE).sum(1)
        for variante in ("V1", "V2"):
            for beta in (0.03, 0.1):
                S, M, d = P.simuler(Z, ORD, n, beta, variante)
                cur = M.sum((1, 2)).reshape(-1, FENETRE).sum(1)
                g = 1.0 - cur / base
                res["fenetres"][f"{variante}/{nom}/{beta}"] = {"gains_par_fenetre": [float(x) for x in g], "moyenne": float(g.mean()),
                                                               "ecart_type_moyenne": float(g.std(ddof=1) / math.sqrt(len(g))), "min": float(g.min())}
                log(f"fenêtres {variante} N={n} β={beta}: gain {g.mean() * 100:.1f} ± {g.std(ddof=1) / math.sqrt(len(g)) * 100:.1f} % (min {g.min() * 100:.1f} %)")
    # 3. LFU(8)
    S0, M0, d0 = P.simuler(Z, ORD, 154, 0.0, fabrique=CacheLFU)
    e7 = json.load(open(os.path.join(P.RACINE, "mesures", "mimetisme", "humain", "e7-marge-20b.json"), encoding="utf-8"))
    taux = 1 - d0 / (T * L * 4)
    res["lfu"]["temoin_e7"] = {"taux_succes": taux, "taux_e7": e7["taux_succes"], "ecart": taux - e7["taux_succes"], "tient": abs(taux - e7["taux_succes"]) <= 0.002}
    log(f"témoin LFU(8) N=154 β=0 : succès {taux:.5f} contre E7 {e7['taux_succes']:.5f} : {'TIENT' if res['lfu']['temoin_e7']['tient'] else 'TOMBE'}")
    for nom, frac in P.BUDGETS.items():
        n = round(frac * L * E)
        S0, M0, d0 = P.simuler(Z, ORD, n, 0.0, fabrique=CacheLFU)
        for variante in ("V1", "V2"):
            for beta in (0.03, 0.1):
                S, M, d = P.simuler(Z, ORD, n, beta, variante, fabrique=CacheLFU)
                st = P.statistiques(Z, ORD, S0, S)
                res["lfu"][f"{variante}/{nom}/{beta}"] = {"N": n, "defauts_beta0": d0, "defauts": d, "variation_relative": d / d0 - 1.0, **st}
                log(f"LFU(8) {variante} N={n} β={beta}: défauts {d} contre {d0} ({(d / d0 - 1) * 100:+.1f} %), cellules {st['part_cellules_changees'] * 100:.2f} %")
    json.dump(res, open(os.path.join(P.SORTIE, "affinage.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    with open(os.path.join(P.SORTIE, "affinage.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["variante", "budget", "N", "beta", "defauts", "variation_relative", "part_cellules_changees",
                                          "experts_changes_par_cellule_changee", "part_plus_haut_logit_garde", "kl_prior"], extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(lignes, key=lambda l: (l["variante"], l["budget"], l["beta"])))
    open(os.path.join(P.SORTIE, "affinage.log"), "w", encoding="utf-8").write("\n".join(journal) + "\n")
    log(f"# fin, {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
