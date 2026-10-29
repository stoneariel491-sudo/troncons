"""Erreur à la SORTIE des experts, sur les entrées réelles capturées par la référence f64.

Pour chaque couche capturée (0, 8, 16, 23) et chaque expert, les entrées X sont les états normés
après l'attention des positions routées vers lui (sonde capture, 10 fenêtres de 512 jetons du
corpus du lot R). On calcule l'expert exact et l'expert reconstruit selon chaque plan :
  G = X Wgᵀ + bg, U = X Wuᵀ + bu, A = swiglu_oai(G, U), Y = A Wdᵀ + bd
(swiglu_oai : g ← min(g, 7), u ← clamp(u, −7, 7), g·σ(1,702 g)·(u + 1), comme trc-reference).

Erreurs relatives, sommées sur les experts (pondération par les jetons, celle de la couche) :
  - gate, up : ‖X ΔWᵀ‖² / ‖G‖², ‖U‖² ;
  - down seul : ‖A ΔWdᵀ‖² / ‖Y‖² (entrée exacte) ;
  - expert entier : ‖Ŷ − Y‖² / ‖Y‖² (les trois matrices reconstruites).
Évaluation sur les fenêtres 5 à 9 (les fenêtres 0 à 4 restent pour calibrer les plans qui lisent
les activations).

Seuil (déclaré avant) : un plan « fait mieux que la base à la sortie » si son erreur d'expert
entier, moyenne des quatre couches, est ≤ 0,95 × celle de la base (5 % : au-dessus de la
dispersion entre couches de la base, mesurée ici et écrite dans le journal).
Témoins : le plan identité rend une erreur nulle au bit ; cassure (--casser) : le plan identité
reçoit T[code 1] × 1,01 et le témoin doit tomber.

Utilisation : python -I -X utf8 sortie_experts.py DOSSIER_ENTREES PLAN1.npz [PLAN2.npz …] SORTIE.json [--casser]
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mxfp4 as mx  # noqa: E402

FENETRE = 511
EVAL = range(5, 10)
SEUIL = 0.95


def lire_entrees(chemin):
    """{expert: (positions, X f32)} d'un fichier entrees-L.bin."""
    o = np.fromfile(chemin, dtype=np.uint8)
    assert bytes(o[:4]) == b"ENTR", chemin
    couche, d, ne = np.frombuffer(o[4:16].tobytes(), dtype="<u4")
    p = 16
    out = {}
    while p < len(o):
        e, m = np.frombuffer(o[p:p + 8].tobytes(), dtype="<u4")
        p += 8
        pos = np.frombuffer(o[p:p + 4 * m].tobytes(), dtype="<u4").copy()
        p += 4 * m
        X = np.frombuffer(o[p:p + 4 * m * d].tobytes(), dtype="<f4").reshape(m, d).copy()
        p += 4 * m * d
        out[int(e)] = (pos, X)
    return int(couche), int(d), out


def swiglu(g, u):
    g = np.minimum(g, 7.0)
    u = np.clip(u, -7.0, 7.0)
    return g / (1.0 + np.exp(-1.702 * g)) * (u + 1.0)


class Plan:
    def __init__(self, chemin, casser=False):
        z = np.load(chemin)
        self.nom = os.path.basename(chemin).removesuffix(".npz")
        self.mode = str(z["mode"])
        self.noms = [str(s) for s in z["noms"]]
        self.luts = {}
        self.cartes = z["cartes"] if "cartes" in z.files else None
        self.cartes_lig = z["cartes_lig"] if "cartes_lig" in z.files else None
        taille = {"e_q": 256 * 4, "e_lc": 256 * 16, "d_lc": 7 * 16}.get(self.mode, 256)
        for t, nom in enumerate(self.noms):
            lut = np.zeros((taille, 16))
            for k, v in zip(z[f"t{t}_ctx"], z[f"t{t}_val"]):
                lut[int(k)] = v
            if casser and self.mode == "identite":
                lut[:, 1] *= 1.01
            self.luts[nom] = lut

    def contexte(self, ech, med):
        if self.mode in ("e", "e_q", "e_lc"):
            return ech.astype(np.int64)
        d = ech.astype(np.int64) - med[:, None].astype(np.int64)
        if self.mode == "kappa":
            return np.sign(d) + 1
        if self.mode == "delta7":
            return np.clip(d, -3, 3)  # clés −3 … 3 des plans (indices négatifs : numpy les replie comme à l'écriture)
        return np.zeros_like(d)

    def matrice(self, nom, codes, ech, expert):
        med = mx.mediane_ligne(ech)
        ctx = np.repeat(self.contexte(ech, med), 32, axis=1)
        if self.mode == "e_q":
            ctx = ctx * 4 + self.cartes[self.noms.index(nom), expert][None, :].astype(np.int64)
        if self.mode == "d_lc":
            d = ech.astype(np.int64) - med[:, None].astype(np.int64)
            t = self.noms.index(nom)
            ctx = (np.repeat(np.clip(d, -3, 3) + 3, 32, axis=1) * 16
                   + self.cartes_lig[t, expert][:, None].astype(np.int64) * 4
                   + self.cartes[t, expert][None, :].astype(np.int64))
        if self.mode == "e_lc":
            t = self.noms.index(nom)
            ctx = (ctx * 16 + self.cartes_lig[t, expert][:, None].astype(np.int64) * 4
                   + self.cartes[t, expert][None, :].astype(np.int64))
        e = np.repeat(ech.astype(np.float64) - 128.0, 32, axis=1)
        return self.luts[nom][ctx, codes] * np.exp2(e)


def biais(lec, nom):
    t = [x for x in lec.tenseurs if x.nom == nom][0]
    return np.frombuffer(np.asarray(lec.octets(t)).tobytes(), dtype="<f4").reshape(t.dims[1], t.dims[0])


def main():
    casser = "--casser" in sys.argv
    argv = [a for a in sys.argv[1:] if not a.startswith("--")]
    dossier, chemins, sortie = argv[0], argv[1:-1], argv[-1]
    plans = [Plan(c, casser) for c in chemins]
    lec = mx.lecteur()
    par_nom = {t.nom: t for t in lec.tenseurs}
    t0 = time.time()
    res = {p.nom: {} for p in plans}
    for couche in mx.COUCHES:
        _, d, entrees = lire_entrees(os.path.join(dossier, f"entrees-{couche}.bin"))
        noms = [f"blk.{couche}.{r}.weight" for r in mx.ROLES]
        bs = [biais(lec, f"blk.{couche}.{r}.bias") for r in mx.ROLES]
        acc = {p.nom: np.zeros(8) for p in plans}  # ΔG², G², ΔU², U², ΔYd², Y², ΔY², jetons
        par_expert = {p.nom: [] for p in plans}
        for e, (pos, X) in sorted(entrees.items()):
            garde = np.isin(pos // FENETRE, list(EVAL))
            if not garde.any():
                continue
            X = X[garde].astype(np.float32)
            mats = [mx.expert(lec, par_nom[n], e) for n in noms]
            W = [mx.valeurs(c, s).astype(np.float32) for c, s in mats]
            G = X @ W[0].T + bs[0][e]
            U = X @ W[1].T + bs[1][e]
            A = swiglu(G, U)
            Y = A @ W[2].T + bs[2][e]
            for p in plans:
                Wh = [p.matrice(n, c, s, e).astype(np.float32) for n, (c, s) in zip(noms, mats)]
                dG = X @ (Wh[0] - W[0]).T
                dU = X @ (Wh[1] - W[1]).T
                dYd = A @ (Wh[2] - W[2]).T
                Gh, Uh = G + dG, U + dU
                Yh = swiglu(Gh, Uh) @ Wh[2].T + bs[2][e]
                v = np.array([(dG.astype(np.float64) ** 2).sum(), (G.astype(np.float64) ** 2).sum(),
                              (dU.astype(np.float64) ** 2).sum(), (U.astype(np.float64) ** 2).sum(),
                              (dYd.astype(np.float64) ** 2).sum(), (Y.astype(np.float64) ** 2).sum(),
                              ((Yh - Y).astype(np.float64) ** 2).sum(), float(len(X))])
                acc[p.nom] += v
                par_expert[p.nom].append(v[6] / v[5])
        for p in plans:
            a = acc[p.nom]
            res[p.nom][str(couche)] = {"gate": a[0] / a[1], "up": a[2] / a[3], "down_seul": a[4] / a[5],
                                       "expert": a[6] / a[5], "jetons": int(a[7]),
                                       "expert_max_par_expert": float(max(par_expert[p.nom])),
                                       "experts": len(par_expert[p.nom])}
        print(f"couche {couche} : {time.time() - t0:.0f} s", file=sys.stderr)
    resume = {}
    for p in plans:
        r = res[p.nom]
        resume[p.nom] = {k: float(np.mean([r[c][k] for c in r])) for k in ("gate", "up", "down_seul", "expert")}
    base = next((p.nom for p in plans if "base" in p.nom), None)
    verdicts = {}
    if base:
        for p in plans:
            verdicts[p.nom] = {"rapport_expert_a_la_base": resume[p.nom]["expert"] / resume[base]["expert"],
                               "fait_mieux": bool(resume[p.nom]["expert"] <= SEUIL * resume[base]["expert"])}
    ident = next((p.nom for p in plans if "identite" in p.nom), None)
    temoins = {}
    if ident:
        temoins["identite_erreur_nulle"] = bool(all(res[ident][c]["expert"] == 0.0 for c in res[ident]))
    sortie_j = {"outil": "genome/predictif-elagage/sortie_experts.py", "entrees": dossier, "fenetres_evaluation": list(EVAL),
                "casser": casser, "seuil": SEUIL, "par_couche": res, "moyenne_des_couches": resume,
                "verdicts": verdicts, "temoins": temoins, "duree_s": time.time() - t0}
    with open(sortie, "w", encoding="utf-8") as f:
        json.dump(sortie_j, f, ensure_ascii=False, indent=1)
    print(json.dumps({"moyenne_des_couches": resume, "verdicts": verdicts, "temoins": temoins}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
