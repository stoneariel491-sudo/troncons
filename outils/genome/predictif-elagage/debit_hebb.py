"""Débit-distorsion à la sensibilité hebbienne : remplissage inverse sur (e, classe de ligne, classe de colonne).

Distorsion prédite d'un poids : 4^(e − emax) · r_i · s_j · (K − r)² (histo_hebb.py) ; métrique :
moyenne sur les tenseurs de l'erreur de sortie d'expert prédite, Σ A (K − r)² / Σ A K².

Familles, jugées à l'erreur prédite de la base sous la même métrique :
  - hebb_e : partitions par e, masses hebbiennes (aucune carte) ;
  - hebb_e_lc : partitions par (e, qr, qc), cartes de 2 bits par ligne et par colonne et par matrice
    d'expert (2 × 720 octets, 0,0014 bit par poids, comptées) ;
Pour chacune : plan .npz (sortie_experts.py) et .bin (sonde, taux_plan : mode 1 = e ; n_col = 16 :
classe = 4 · qr + qc, cartes de colonnes puis de lignes).

Utilisation : python -I -X utf8 debit_hebb.py HISTO_HEBB.npz PLAN_BASE.npz DOSSIER_SORTIE
"""
from __future__ import annotations

import json
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import debit_distorsion as dd  # noqa: E402

NQ = 4
NC = NQ * NQ


class SourceHebb:
    """ctx : 'e' (e seul) ou 'e_lc' (e × 16 classes (ligne, colonne))."""

    def __init__(self, N, S, ctx, cle_delta=False):
        T = N.shape[0]
        e = np.arange(256)
        self.emax = int(np.nonzero(N.sum(axis=(0, 2, 3, 4)))[0].max())
        # Clé δ : S porte déjà la masse 4^(e − 127) ; clé e : on l'applique ici.
        A = S if cle_delta else S * (4.0 ** (e - self.emax))[None, :, None, None, None]
        self.T = T
        self.N = float(N.sum(dtype=np.float64))
        self.Et = (A * (dd.VAL ** 2)).sum(axis=(1, 2, 3, 4))
        self.E = float(self.Et.sum())
        self.metrique = "par_tenseur"
        self.stats = []
        for t in range(T):
            for ee in np.nonzero(N[t].sum(axis=(1, 2, 3)))[0]:
                if ctx == "e":
                    groupes = [(int(ee), N[t, ee].sum(axis=(0, 1)), A[t, ee].sum(axis=(0, 1)))]
                else:
                    groupes = [(int(ee) * NC + ql * NQ + qc, N[t, ee, ql, qc], A[t, ee, ql, qc])
                               for ql in range(NQ) for qc in range(NQ)]
                for k, n, a in groupes:
                    n = n.astype(np.float64)[dd.ORDRE]
                    if n.sum() == 0:
                        continue
                    a = a[dd.ORDRE]
                    self.stats.append((t, k, n, a, a * dd.VAL_O, a * dd.VAL_O ** 2))


def erreur_base(N, S, v_base, cle_delta=False):
    e = np.arange(256)
    emax = int(np.nonzero(N.sum(axis=(0, 2, 3, 4)))[0].max())
    A = S if cle_delta else S * (4.0 ** (e - emax))[None, :, None, None, None]
    At = A.sum(axis=(1, 2, 3))                               # (T, 16)
    num = (At * (dd.VAL - v_base) ** 2).sum(axis=1)
    den = (At * dd.VAL ** 2).sum(axis=1)
    return float(np.mean(num / den)), list(num / den)


def chercher(src, cible):
    lo, hi = 1e-16, 1e-4
    for _ in range(70):
        mu = (lo * hi) ** 0.5
        if dd.evaluer_famille(src, mu)["erreur"] > cible:
            hi = mu
        else:
            lo = mu
    return dd.evaluer_famille(src, lo, garder=True)


def tables_de(plan, T):
    tables = [dict() for _ in range(T)]
    for (t, k, cellules) in plan:
        v = np.zeros(16)
        for (i, j, rr) in cellules:
            for pos in range(i, j + 1):
                v[dd.ORDRE[pos]] = rr
        tables[t][k] = v
    return tables


def ecrire_bin(noms, tables, mode, cl, cc, chemin):
    roles = {"ffn_gate_exps": 0, "ffn_up_exps": 1, "ffn_down_exps": 2}
    o = bytearray(b"PEPL")
    o += struct.pack("<I", len(noms))
    for t, (nom, tab) in enumerate(zip(noms, tables)):
        _, couche, role, _ = nom.split(".")
        avec = mode in ("e_lc", "d_lc")
        es = sorted({k // NC for k in tab}) if avec else sorted(tab)
        a, b = min(es), max(es)
        ncol = NC if avec else 1
        m = 0 if mode == "d_lc" else 1
        if mode == "d_lc":            # clés δ + 3 (0 … 6) : le décodeur calcule δ, borné à ±3
            a, b = a - 3, b - 3
        o += struct.pack("<IIIiiI", int(couche), roles[role], m, a, b, ncol)
        for ee in range(a, b + 1):
            for q in range(ncol):
                eek = ee + 3 if mode == "d_lc" else ee
                k = eek * NC + q if avec else eek
                o += np.asarray(tab.get(k, np.zeros(16)), dtype="<f8").tobytes()
        if avec:
            o += cc[t].astype(np.uint8).tobytes()
            o += cl[t].astype(np.uint8).tobytes()
    with open(chemin, "wb") as f:
        f.write(bytes(o))


def main():
    histo, plan_base, dossier = sys.argv[1], sys.argv[2], sys.argv[3]
    cle_delta = "--cle-delta" in sys.argv
    z = np.load(histo)
    N, S = z["N"], z["S"]
    noms = [str(s) for s in z["noms"]]
    T = N.shape[0]
    vb = np.load(plan_base)["t0_val"][0]
    err_b, err_b_t = erreur_base(N, S, vb, cle_delta)
    res = {"histogramme": histo, "erreur_predite_base": err_b, "erreur_predite_base_par_tenseur": err_b_t}
    familles = (("hebb_d_lc", "e_lc"),) if cle_delta else (("hebb_e", "e"), ("hebb_e_lc", "e_lc"))
    for nom, ctx in familles:
        src = SourceHebb(N, S, ctx, cle_delta)
        r = chercher(src, err_b)
        tables = tables_de(r.pop("plan"), T)
        cartes = (2 * 2 * 2880 * 32 * T / src.N) if ctx == "e_lc" else 0.0
        r["bits_cartes"] = cartes
        r["bits_total_cartes_comprises"] = r["bits_total"] + cartes
        res[nom] = r
        sortie = os.path.join(dossier, f"plan-12-{nom}")
        extra = {"cartes": z["cartes_col"], "cartes_lig": z["cartes_lig"]} if ctx == "e_lc" else {}
        mode_plan = "d_lc" if cle_delta else ctx
        np.savez_compressed(sortie + ".npz", noms=np.array(noms), mode=np.array(mode_plan), **extra,
                            **{f"t{t}_ctx": np.array(sorted(tables[t]), dtype=np.int64) for t in range(T)},
                            **{f"t{t}_val": np.array([tables[t][k] for k in sorted(tables[t])]) for t in range(T)})
        ecrire_bin(noms, tables, mode_plan, z["cartes_lig"], z["cartes_col"], sortie + ".bin")
    with open(os.path.join(dossier, "debit-hebb-delta-12.json" if cle_delta else "debit-hebb-12.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=float)
    print(json.dumps({k: v for k, v in res.items() if "par_tenseur" not in k}, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
