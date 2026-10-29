"""Piste spectres : d'où vient la queue ? (mesure exploratoire, NON déclarée avant ; dite comme telle)

Hypothèse : la queue lourde de down (couche 0 surtout) vient de l'hétérogénéité des normes de
rangées (les canaux de sortie géants, propriété (b) de 05 § 2.1), pas d'une invariance d'échelle.
Test : on divise chaque rangée par sa norme (W_r = D_r⁻¹ W), puis chaque colonne (W_c = W D_c⁻¹), et
on refait la SVD et l'ajustement CSN. Si la queue vient des rangées, α remonte vers celui des
permutées et la part d'énergie des 5 % premières directions retombe vers le hasard.
Second regard, sans ajustement : le rapport σ₁ / (plus grande norme de rangée) ; il vaut au moins 1,
et près de 1 quand la première direction est une rangée.

Utilisation : python -X utf8 normalise.py > normalise.csv
"""
from __future__ import annotations

import commun

import csv
import sys

import numpy as np

import csn
from puissance_critere import compatible


def part5(s):
    e = s ** 2
    r = max(1, int(round(0.05 * s.size)))
    return float(e[:r].sum() / e.sum())


def main() -> None:
    commun.priorite_basse()
    lec = commun.lecteur()
    index = {t.nom: t for t in lec.tenseurs}
    out = csv.writer(sys.stdout, lineterminator="\n")
    out.writerow(["id", "variante", "alpha", "n_queue", "p_gof", "compatible", "part5", "sigma1_sur_rangee_max",
                  "cv_normes_rangees", "cv_normes_colonnes"])
    for i, m in enumerate(commun.echantillon()):
        if m["role"] not in ("down", "gate", "attn_output"):
            continue
        commun.attendre_calme()
        w = commun.matrice(lec, index, m)
        nr = np.sqrt((w ** 2).sum(axis=1))
        nc = np.sqrt((w ** 2).sum(axis=0))
        cvr, cvc = float(nr.std() / nr.mean()), float(nc.std() / nc.mean())
        for nom, x in (("brute", w), ("rangees", w / np.where(nr > 0, nr, 1)[:, None]),
                       ("colonnes", w / np.where(nc > 0, nc, 1)[None, :])):
            s = np.linalg.svd(x, compute_uv=False)
            r = csn.ajuster(s ** 2, rng=np.random.default_rng(commun.GRAINE + 500 + i), repliques=50)
            rmax = float(np.sqrt((x ** 2).sum(axis=1)).max())
            out.writerow([m["id"], nom, f"{r['alpha']:.4f}", r["n_queue"], f"{r['p_gof']:.2f}", compatible(r),
                          f"{part5(s):.4f}", f"{s[0] / rmax:.4f}", f"{cvr:.4f}", f"{cvc:.4f}"])
            sys.stdout.flush()
            print(f"{m['id']:16s} {nom:9s} α={r['alpha']:.2f} n_q={r['n_queue']} compat={compatible(r)} "
                  f"part5={part5(s):.3f} σ1/rangée_max={s[0] / rmax:.3f} cv_r={cvr:.2f} cv_c={cvc:.2f}",
                  file=sys.stderr, flush=True)
        del w


if __name__ == "__main__":
    main()
