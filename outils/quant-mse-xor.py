"""Treillis à décalage à code linéaire par parités (sans multiplication), sur source N(0,1).

Question : un décodeur de treillis sans multiplication ni table de 2^L valeurs, fait de
parités masquées (ce que XOR-Trellis, arXiv:2610.00432, propose pour le matériel, sans
publier ses masques), atteint-il la MSE des codes calculés de QTIP et d'EXL3 (0,068 à
2 bits, journal mse-treillis-2b.json) ?

Le code « parite » : pour un état s de L bits, l'index j = Σ_q parité(s & m_q) · 2^q,
q = 0..P-1, est une fonction linéaire de s sur GF(2) ; la valeur émise est palette[j],
où la palette est faite des 2^P quantiles gaussiens centrés Φ^{-1}((j + 1/2) / 2^P),
renormalisés. Si la matrice des masques est de rang P, chaque index est atteint par
2^(L-P) états : la loi marginale des valeurs émises est uniforme sur la palette, donc
proche de la gaussienne. Sur un GPU : P fois (ET, comptage de bits, ET 1), une lecture
dans une palette de 2^P flottants ; aucune multiplication.

Recherche des masques : M tirages aléatoires de rang plein, chacun évalué sur une suite
courte ; le meilleur est mesuré en entier. Le même Viterbi que quant-mse-gaussien.py
(importé de ce fichier), même source, même graine.

Témoin : le code « mul1 » repassé par la même machinerie doit redonner 0,0682 ± 0,0007
(journal mse-treillis-2b.json) à 4 erreurs-types près ; --casser décale toutes les tables
de 0,6 (après normalisation) et doit faire tomber la comparaison.

Usage : python -I outils/quant-mse-xor.py [--P 4] [--tirages 16] [--suites 8] [--casser]
"""
import argparse
import importlib.util
import json
import math
import os
import sys
import time

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("mse_g", os.path.join(ICI, "quant-mse-gaussien.py"))
mse_g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mse_g)


def quantile_normal(p):
    # Inverse de Φ par bissection sur mse_g.Phi (précision 1e-10, suffisant ici).
    lo, hi = -10.0, 10.0
    for _ in range(80):
        mi = 0.5 * (lo + hi)
        if mse_g.Phi(mi) < p:
            lo = mi
        else:
            hi = mi
    return 0.5 * (lo + hi)


def rang_gf2(masques, L):
    lignes = list(masques)
    r = 0
    for bit in range(L):
        piv = next((i for i in range(r, len(lignes)) if (lignes[i] >> bit) & 1), None)
        if piv is None:
            continue
        lignes[r], lignes[piv] = lignes[piv], lignes[r]
        for i in range(len(lignes)):
            if i != r and (lignes[i] >> bit) & 1:
                lignes[i] ^= lignes[r]
        r += 1
    return r


def parite(v):
    v = v ^ (v >> 16)
    v = v ^ (v >> 8)
    v = v ^ (v >> 4)
    v = v ^ (v >> 2)
    v = v ^ (v >> 1)
    return v & 1


def table_parite(masques, palette, L):
    etats = np.arange(1 << L, dtype=np.uint32)
    j = np.zeros(1 << L, dtype=np.uint32)
    for q, m in enumerate(masques):
        j |= parite(etats & np.uint32(m)) << np.uint32(q)
    return palette[j]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--P", type=int, default=4)
    ap.add_argument("--L", type=int, default=16)
    ap.add_argument("--R", type=int, default=2)
    ap.add_argument("--T", type=int, default=4096)
    ap.add_argument("--suites", type=int, default=8)
    ap.add_argument("--tirages", type=int, default=16)
    ap.add_argument("--graine", type=int, default=1)
    ap.add_argument("--casser", action="store_true")
    ap.add_argument("--gain-max", type=float, default=1.05,
                    help="borne haute de la grille du gain (1,05 dans les passes 1 et 2)")
    ap.add_argument("--masques", default="", help="masques imposés (saute la recherche)")
    ap.add_argument("--palette", default="quantiles", choices=["quantiles", "uniforme"],
                    help="uniforme : 16 niveaux également espacés = somme de ±c_q (décodage sans table)")
    ap.add_argument("--sauter-temoin", action="store_true")
    a = ap.parse_args()
    L, R, P = a.L, a.R, a.P
    journal = {"gain_max": a.gain_max, "outil": "quant-mse-xor.py", "palette": a.palette, "L": L, "R": R, "P": P, "T": a.T, "suites": a.suites,
               "tirages": a.tirages, "graine": a.graine, "casser": a.casser}
    # Même loi et même graine que quant-mse-gaussien.py ; on consomme le générateur dans le
    # même ordre (témoin, table rptc) sans garantir les mêmes suites que la passe 2.
    rng = np.random.default_rng(a.graine)
    rng.standard_normal(1 << 20)                       # échantillons du témoin Lloyd-Max
    rng.standard_normal(1 << L)                        # table rptc
    xs = rng.standard_normal(a.suites * a.T)
    court = xs[: 2 * 1024]

    palette = np.array([quantile_normal((j + 0.5) / (1 << P)) for j in range(1 << P)])
    if a.palette == "uniforme":
        # Index j = Σ_q b_q 2^q ; valeur ∝ 2j − (2^P − 1) = Σ_q (2 b_q − 1) 2^q : une somme de
        # ±2^q, calculable par un produit scalaire des 4 parités signées, sans table.
        palette = np.array([2.0 * j - ((1 << P) - 1) for j in range(1 << P)])
    palette = palette / palette.std()

    def mesure(table, nom):
        t = (table - table.mean()) / table.std() + (0.6 if a.casser else 0.0)
        g = mse_g.meilleur_gain(lambda g: mse_g.mse_treillis(court, t * g, L, R, 1024),
                                np.linspace(0.75, a.gain_max, 1 + round((a.gain_max - 0.75) / 0.05)))
        t0 = time.time()
        m, se, ns = mse_g.mse_treillis(xs, t * g, L, R, a.T)
        return {"code": nom, "gain": round(float(g), 3), "mse": round(m, 6), "erreur_type": round(se, 7),
                "suites": ns, "bits_par_poids": round(R + (L - R) / a.T, 4), "secondes": round(time.time() - t0, 1)}

    # Témoin : mul1 par la même machinerie.
    if not a.sauter_temoin:
        etats = np.arange(1 << L, dtype=np.uint32)
        tm = mesure(mse_g.code_mul1(etats), "mul1-temoin")
        tm["attendu"] = 0.068236
        tm["tient"] = bool(abs(tm["mse"] - 0.068236) < 4 * math.hypot(tm["erreur_type"], 0.0007416))
        journal["temoin"] = tm
        print(json.dumps(tm, ensure_ascii=False), file=sys.stderr)

    # Recherche des masques sur la suite courte.
    essais = []
    for i in range(a.tirages):
        while True:
            masques = [int(v) for v in rng.integers(1, 1 << L, size=P)]
            if rang_gf2(masques, L) == P:
                break
        t = table_parite(masques, palette, L)
        t = (t - t.mean()) / t.std() + (0.6 if a.casser else 0.0)
        m = min(mse_g.mse_treillis(court, t * g, L, R, 1024)[0] for g in np.linspace(0.8, 1.05, 6))
        essais.append({"masques": [hex(v) for v in masques], "mse_court": round(m, 5)})
        print(json.dumps(essais[-1]), file=sys.stderr)
    journal["recherche"] = essais
    if a.masques:
        masques = [int(v, 16) for v in a.masques.split(",")]
    else:
        meilleur = min(essais, key=lambda e: e["mse_court"])
        masques = [int(v, 16) for v in meilleur["masques"]]
    res = mesure(table_parite(masques, palette, L), "parite")
    res["masques"] = [hex(v) for v in masques]
    journal["resultat"] = res
    print(json.dumps(res, ensure_ascii=False), file=sys.stderr)
    print(json.dumps(journal, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
