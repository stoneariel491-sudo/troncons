"""Juge : l'autre classe de modèle (probabilités par classes) refaite, et sa sensibilité aux ex aequo.

Le modèle par classes de seuil-declare-indices.md § 6 rend des scores en paliers (au plus 20 × 4 × 4 classes) :
la frontière des 1 226 cellules gardées par fenêtre coupe presque toujours un palier, et le second chemin
de la piste départage ces ex aequo par l'indice de cellule, couche croissante (les couches basses d'abord).
Ce choix n'est pas neutre. Ce script rend, pour le même modèle écrit à neuf (bornes par numpy.quantile) :
- le départage par couche croissante (celui de la piste),
- le départage par couche décroissante,
- l'espérance exacte sous un départage uniforme au hasard dans le palier frontière (sans tirage).
Il fait de même pour M0 (sans effet : la marge f32 n'a presque pas d'ex aequo) à titre de témoin.

Un fil, priorité sous la normale, attente du verrou de la carte s'il annonce une séance de vitesse.
"""

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"

import json
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import juge_indices as J  # noqa: E402  (le lecteur et les indices du juge, pas ceux de la piste)

K = 1226


def classe_f4(v):
    return np.where(v == 0, 0, np.where(v <= 0.05, 1, np.where(v <= 0.15, 2, 3)))


def frontiere(score, y, ident_ordre):
    """Rend (couche croissante, couche décroissante, espérance au hasard) des attrapées pour K cellules."""
    o1 = np.lexsort((ident_ordre, -score))
    o2 = np.lexsort((-ident_ordre, -score))
    a1 = int(y[o1[:K]].sum())
    a2 = int(y[o2[:K]].sum())
    s_k = score[o1[K - 1]]
    sup = score > s_k
    eg = score == s_k
    reste = K - int(sup.sum())
    esp = float(y[sup].sum()) + reste * float(y[eg].sum()) / float(eg.sum())
    return a1, a2, esp, int(eg.sum())


def main():
    J.sous_la_normale()
    J.attendre_verrou()
    nl, npos, eA, _ = J.lire(*J.JOURNAUX["A"])
    _, _, eB, mBp = J.lire(*J.JOURNAUX["B"])
    Y = np.any(np.sort(eA, axis=2) != np.sort(eB, axis=2), axis=2).reshape(nl, J.NF, J.NP).astype(np.int64)
    mB = mBp.reshape(nl, J.NF, J.NP)
    f1, f2, f3, f4, f5 = J.indices(mB, nl)
    ident = (np.arange(nl)[:, None] * J.NP + np.arange(J.NP)[None, :]).ravel()
    nb = [int(Y[:, t].sum()) for t in range(J.NF)]
    out = {"M0": [], "classes": [], "taille_palier_frontiere": []}
    for t in range(J.NF):
        tr = [w for w in range(J.NF) if w != t]
        e1 = np.quantile(f1[:, tr].ravel(), np.arange(1, 20) / 20)
        e2 = np.quantile(f2[:, tr].ravel(), np.arange(1, 4) / 4)

        def cl(sl):
            return (np.searchsorted(e1, f1[:, sl], side="right") * 16
                    + np.searchsorted(e2, f2[:, sl], side="right") * 4 + classe_f4(f4[:, sl]))

        ctr = cl(tr).ravel()
        ytr = Y[:, tr].ravel()
        n = np.bincount(ctr, minlength=320)
        k = np.bincount(ctr, weights=ytr, minlength=320)
        pr = (k + 1.0) / (n + 20.0)
        s = pr[cl(t).ravel()]
        yt = Y[:, t].ravel()
        a1, a2, esp, taille = frontiere(s, yt, ident)
        out["classes"].append([a1, a2, esp])
        out["taille_palier_frontiere"].append(taille)
        b1, b2, besp, _ = frontiere(-mB[:, t].ravel(), yt, ident)
        out["M0"].append([b1, b2, besp])
    tot = sum(nb)
    m0 = sum(r[2] for r in out["M0"])
    for i, nom in enumerate(("couche_croissante", "couche_decroissante", "esperance_hasard")):
        c = sum(r[i] for r in out["classes"])
        out[nom] = {"b_pct": 100 * c / tot, "gain_sur_M0": 100 * (c - m0) / tot,
                    "fenetres_positives": sum(1 for r, q in zip(out["classes"], out["M0"]) if r[i] > q[2])}
    out["M0_b_pct"] = 100 * m0 / tot
    with open(os.path.join(J.SORTIE, "juge-classes.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.exit(main())
