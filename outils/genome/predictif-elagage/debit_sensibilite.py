"""Débit-distorsion à la sensibilité mesurée : remplissage inverse sur (échelle e, activité de colonne q).

Distorsion d'un poids : 4^(e − emax) · s_j · (K − r)², s_j = E[x_j²] mesurée sur les fenêtres de
calibration (histo_sensibilite.py) : c'est l'erreur de sortie prédite (approximation diagonale).
Métrique : moyenne sur les tenseurs de l'erreur de sortie relative prédite, Σ A (K − r)² / Σ A K².

Familles (toutes jugées à la même erreur prédite que la base) :
  - base : la frontière (partition fixe, centres communs) ;
  - sens_e : partitions par contexte e, masses pondérées par l'activité (pas de carte de colonnes) ;
  - sens_e_q : partitions par (e, q), q le quartile d'activité de la colonne (carte de 2 bits par
    colonne et par expert, comptée : 720 octets par matrice d'expert) ;
  - poids_e : le plan ecsq_e de la métrique des poids (debit_distorsion), évalué ici, pour dire ce
    que la sensibilité ajoute.

Seuil (déclaré avant) : sens_e_q « fait mieux » si son débit à erreur prédite égale est ≤ 0,99 ×
celui de sens_e (sinon la carte de colonnes ne paie pas) ; et la vérité reste la mesure sur les
fenêtres d'évaluation (sortie_experts.py) puis la KL.

Utilisation : python -I -X utf8 debit_sensibilite.py HISTO_SENS.npz PLAN_POIDS_E.npz DOSSIER_SORTIE
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import debit_distorsion as dd  # noqa: E402

NQ = 4
BITS_CARTE = 2 * 2880  # par matrice d'expert


class SourceSens:
    def __init__(self, N, S, avec_q):
        T = N.shape[0]
        e = np.arange(256)
        self.emax = int(np.nonzero(N.sum(axis=(0, 2, 3)))[0].max())
        p = 4.0 ** (e - self.emax)
        A = S * p[None, :, None, None]
        self.T = T
        self.N = float(N.sum(dtype=np.float64))
        self.Et = (A * (dd.VAL ** 2)[None, None, None, :]).sum(axis=(1, 2, 3))
        self.E = float(self.Et.sum())
        self.metrique = "par_tenseur"
        self.stats = []
        for t in range(T):
            for ee in np.nonzero(N[t].sum(axis=(1, 2)))[0]:
                qs = range(NQ) if avec_q else [None]
                for q in qs:
                    n = (N[t, ee, q] if q is not None else N[t, ee].sum(axis=0)).astype(np.float64)[dd.ORDRE]
                    if n.sum() == 0:
                        continue
                    a = (A[t, ee, q] if q is not None else A[t, ee].sum(axis=0))[dd.ORDRE]
                    k = int(ee) * NQ + q if q is not None else int(ee)
                    self.stats.append((t, k, n, a, a * dd.VAL_O, a * dd.VAL_O ** 2))


def erreur_table(N, S, emax, tables_par_t, mode):
    """Erreur de sortie prédite (moyenne par tenseur) d'un plan donné en tables T[ctx][code]."""
    e = np.arange(256)
    A = S * (4.0 ** (e - emax))[None, :, None, None]
    errs = []
    for t, tab in enumerate(tables_par_t):
        num = 0.0
        den = 0.0
        for ee in np.nonzero(N[t].sum(axis=(1, 2)))[0]:
            for q in range(NQ):
                a = A[t, ee, q]
                if mode == "e_q":
                    r = tab[int(ee) * NQ + q]
                elif mode == "e":
                    r = tab[int(ee)]
                else:
                    r = tab[0]
                num += float((a * (dd.VAL - r) ** 2).sum())
                den += float((a * dd.VAL ** 2).sum())
        errs.append(num / den)
    return float(np.mean(errs)), errs


def chercher(src, cible):
    lo, hi = 1e-14, 1e-5
    for _ in range(60):
        mu = (lo * hi) ** 0.5
        if dd.evaluer_famille(src, mu)["erreur"] > cible:
            hi = mu
        else:
            lo = mu
    return dd.evaluer_famille(src, lo, garder=True)


def main():
    histo, plan_poids, dossier = sys.argv[1], sys.argv[2], sys.argv[3]
    z = np.load(histo)
    N, S = z["N"], z["S"]
    noms = [str(s) for s in z["noms"]]
    T = N.shape[0]
    emax = int(np.nonzero(N.sum(axis=(0, 2, 3)))[0].max())
    # La base de la frontière, et le plan ecsq_e de la métrique des poids, sous la métrique d'activité.
    zb = np.load(os.path.join(os.path.dirname(plan_poids), "plan-12-base.npz"))
    base_tab = [{0: zb[f"t{t}_val"][0]} for t in range(T)]
    err_base, err_base_t = erreur_table(N, S, emax, base_tab, "base")
    zp = np.load(plan_poids)
    pe = []
    for t in range(T):
        d = {}
        for k, v in zip(zp[f"t{t}_ctx"], zp[f"t{t}_val"]):
            d[int(k)] = v
        pe.append(d)
    err_pe, _ = erreur_table(N, S, emax, pe, "e")
    res = {"histogramme": histo, "erreur_predite_base": err_base, "erreur_predite_base_par_tenseur": err_base_t,
           "erreur_predite_poids_e": err_pe}
    os.makedirs(dossier, exist_ok=True)
    for nom, avec_q in (("sens_e", False), ("sens_e_q", True)):
        src = SourceSens(N, S, avec_q)
        r = chercher(src, err_base)
        plan = r.pop("plan")
        n_mat = T * N.shape[0] and T * 32
        carte = (T * 32 * BITS_CARTE / src.N) if avec_q else 0.0
        r["bits_carte"] = carte
        r["bits_total_carte_comprise"] = r["bits_total"] + carte
        res[nom] = r
        tables = [dict() for _ in range(T)]
        for (t, k, cellules) in plan:
            v = np.zeros(16)
            for (i, j, rr) in cellules:
                for pos in range(i, j + 1):
                    v[dd.ORDRE[pos]] = rr
            tables[t][k] = v
        mode = "e_q" if avec_q else "e"
        sortie = os.path.join(dossier, f"plan-12-{nom}")
        extra = {"cartes": z["cartes"]} if avec_q else {}
        np.savez_compressed(sortie + ".npz", noms=np.array(noms), mode=np.array(mode), **extra,
                            **{f"t{t}_ctx": np.array(sorted(tables[t]), dtype=np.int64) for t in range(T)},
                            **{f"t{t}_val": np.array([tables[t][k] for k in sorted(tables[t])]) for t in range(T)})
        ecrire_bin(noms, tables, mode, z["cartes"] if avec_q else None, sortie + ".bin")
    res["verdict_carte_paie"] = bool(res["sens_e_q"]["bits_total_carte_comprise"] <= 0.99 * res["sens_e"]["bits_total"])
    with open(os.path.join(dossier, "debit-sensibilite-12.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=float)
    print(json.dumps({k: v for k, v in res.items() if k != "erreur_predite_base_par_tenseur"}, ensure_ascii=False, indent=1, default=float))


def ecrire_bin(noms, tables, mode, cartes, chemin):
    import struct
    roles = {"ffn_gate_exps": 0, "ffn_up_exps": 1, "ffn_down_exps": 2}
    o = bytearray(b"PEPL")
    o += struct.pack("<I", len(noms))
    for t, (nom, tab) in enumerate(zip(noms, tables)):
        _, couche, role, _ = nom.split(".")
        es = sorted({k // NQ for k in tab}) if mode == "e_q" else sorted(tab)
        a, b = min(es), max(es)
        ncol = NQ if mode == "e_q" else 1
        o += struct.pack("<IIIiiI", int(couche), roles[role], 1, a, b, ncol)
        for ee in range(a, b + 1):
            for q in range(ncol):
                k = ee * NQ + q if mode == "e_q" else ee
                o += np.asarray(tab.get(k, np.zeros(16)), dtype="<f8").tobytes()
        if mode == "e_q":
            o += cartes[t].astype(np.uint8).tobytes()
    with open(chemin, "wb") as f:
        f.write(bytes(o))


if __name__ == "__main__":
    main()
