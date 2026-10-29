"""Juge : le témoin W4 (M3 entraîné sur étiquettes mélangées) sur vingt graines.

seuil-declare-indices.md § 5 attend b(M3) = 10 % ± 2 sous étiquettes mélangées. La piste l'a obtenu avec une
seule graine (11,6 %) ; la passe du juge, avec une autre graine, a rendu 22,4 %. Une logistique ajustée sur du
bruit rend une direction presque au hasard dans l'espace des indices, et une direction au hasard sur des
indices qui portent l'information n'attrape pas 10 % en moyenne. Ce script en donne la distribution : graines
1 à 20, mélange des seules étiquettes d'entraînement, fenêtre de test intacte.
"""

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import json
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import juge_indices as J  # noqa: E402


def main():
    J.sous_la_normale()
    J.attendre_verrou()
    nl, npos, eA, _ = J.lire(*J.JOURNAUX["A"])
    _, _, eB, mBp = J.lire(*J.JOURNAUX["B"])
    Y = np.any(np.sort(eA, axis=2) != np.sort(eB, axis=2), axis=2).reshape(nl, J.NF, J.NP).astype(np.int64)
    mB = mBp.reshape(nl, J.NF, J.NP)
    F = J.indices(mB, nl)
    ident = (np.arange(nl)[:, None, None] * npos + np.arange(npos).reshape(J.NF, J.NP)[None]).astype(np.int64)
    tot = int(Y.sum())
    b = []
    for g in range(1, 21):
        att = J.plis(F, Y, ident, "M3", 1226, melange=np.random.default_rng(g))
        b.append(100.0 * sum(att) / tot)
        print(g, round(b[-1], 2), flush=True)
    b = np.array(b)
    out = {"b_pct_par_graine": b.tolist(), "moyenne": float(b.mean()), "ecart_type": float(b.std(ddof=1)),
           "min": float(b.min()), "max": float(b.max()),
           "part_dans_10_pm_2": float(np.mean((b >= 8) & (b <= 12)))}
    with open(os.path.join(J.SORTIE, "juge-w4.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "b_pct_par_graine"}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
