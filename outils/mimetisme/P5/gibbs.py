"""P5 : l'estimateur de Gibbs. La mecanique statistique de l'apprentissage (Seung, Sompolinsky, Tishby 1992 ;
Watkin, Rau, Opper 1993 [mem.]) dit que, quand la calibration est un echantillon fini, l'etat fondamental de
l'energie empirique sur-ajuste et qu'un etat tire a temperature finie generalise mieux. Ici : bain thermique
a UNE temperature T depuis Babai, sans trempe, etat final ; on mesure l'erreur d'evaluation (entrees tenues a
l'ecart) en fonction de T. T = 0 est la descente cyclique.

  python -I -X utf8 gibbs.py --couche 8 --expert 0 --lignes 32 --damp 1 --taus 0 0.02 0.05 0.1 0.2 0.4 0.7 1.0
Les temperatures sont des multiples tau de l'erreur moyenne par poids de Babai (dans les unites de H_train).
"""
import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import etape1 as E1  # noqa: E402
import p5lib as P  # noqa: E402

syn, C8, CEN = P.syn, E1.C8, E1.CEN


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--couche", type=int, default=8)
    ap.add_argument("--expert", type=int, default=0)
    ap.add_argument("--lignes", type=int, default=32)
    ap.add_argument("--damp", type=float, default=1.0)
    ap.add_argument("--taus", type=float, nargs="+", default=[0, 0.02, 0.05, 0.1, 0.2, 0.4, 0.7, 1.0])
    ap.add_argument("--sweeps", type=int, default=30)
    ap.add_argument("--trempe-apres", type=int, default=0, help="balayages de descente apres le tirage (0 = etat de Gibbs brut)")
    ap.add_argument("--graine", type=int, default=1)
    ap.add_argument("--fils", type=int, default=2)
    a = ap.parse_args()
    t0 = time.time()
    rng = np.random.default_rng(a.graine)
    M = E1.matrices(a.couche, a.expert, a.damp)
    Wq, ex, codes = E1.poids_synthetiques(a.lignes, rng)
    S = np.repeat(syn.echelle(ex), 32, axis=-1)
    sf = syn.sym_frontiere(codes)
    ell = syn.longueurs(np.bincount(sf.ravel(), minlength=8).astype(np.float64))
    Qb = P.sym_vers_niveau(syn.choisir(Wq, ex, CEN, M["Htr"], 0.0, ell))
    d = Wq - C8[Qb] * S
    err_b = float(np.einsum("ij,jk,ik->", d, M["Htr"], d, optimize=True)) / d.size
    sortie = dict(couche=a.couche, expert=a.expert, damp=a.damp, lignes=a.lignes, sweeps=a.sweeps, lignes_res=[])
    sortie["lignes_res"].append(E1.ligne("babai", 0.0, Qb, Wq, S, M))
    for tau in a.taus:
        if tau == 0:
            Q, _ = P.pt(M["Htr"], Wq, S, C8, ell, 0.0, Qb, np.array([1.0]), 0, trempe=30, seed=a.graine, fils=a.fils)
        else:
            Q, st = P.pt(M["Htr"], Wq, S, C8, ell, 0.0, Qb, np.array([tau * err_b]), a.sweeps, every=1,
                         trempe=a.trempe_apres, seed=a.graine, fils=a.fils, dernier=1)
        sortie["lignes_res"].append(E1.ligne("gibbs", float(tau), Q, Wq, S, M))
    sortie["duree_s"] = time.time() - t0
    print(json.dumps(sortie, ensure_ascii=False, indent=1))
    b = sortie["lignes_res"][0]
    for r in sortie["lignes_res"][1:]:
        print("tau=%-5s H0=%.4f train=%+.1f%% calib=%+.1f%% eval=%+.1f%% (contre Babai)" % (
            r["lam"], r["bits_H0"], 100 * (1 - r["err_train"] / b["err_train"]), 100 * (1 - r["err_calib"] / b["err_calib"]),
            100 * (1 - r["err_eval"] / b["err_eval"])), file=sys.stderr)


if __name__ == "__main__":
    main()
