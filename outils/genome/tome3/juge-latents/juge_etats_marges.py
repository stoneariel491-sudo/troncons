"""Juge du lot « espaces latents », III-7.6 : ce que dit la taille des points.

Écrit pour troncons le 2026-10-27. La figure colore chaque état par son expert premier (frontière des
couleurs : z(1) = z(2)) et règle sa taille par la marge z(4) − z(5) (frontière de l'ensemble des quatre
experts servis). La note de la synthèse (F10) attend que « les états de petite marge dessinent les
frontières entre les nuées ». Ce script mesure, sans rien tracer, si les gros points de la figure sont
plus souvent au bord des nuées colorées que les autres, et ce que ferait la marge z(1) − z(2).

Mesure du bord : pour un état, la part de ses 10 plus proches voisins (espace d'origine, et plan t-SNE
commité) dont l'expert premier diffère du sien. Classes de marge : sous le 10e centile, jusqu'à la
médiane, au-delà (les classes de la figure), pour z(4) − z(5) et pour z(1) − z(2).
Entrées : la capture h-L23.f32 et le CSV commité etats-c23.csv (expert premier, marges, plans).

Usage : python -I -X utf8 juge_etats_marges.py > juge-etats-marges.json
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import juge_commun as jc  # noqa: E402
from juge_etats import voisins_et_rangs, LAT  # noqa: E402


def classes(m):
    q10, q50 = np.quantile(m, 0.1), np.quantile(m, 0.5)
    return np.where(m < q10, 0, np.where(m < q50, 1, 2))


def main():
    h, _, _ = jc.captures("calib", 23)
    X = np.asarray(h, dtype=np.float64)
    X -= X.mean(axis=0)
    lot = jc.lire_csv(os.path.join(LAT, "etats-c23.csv"))
    premier = np.array([int(r["premier"]) for r in lot])
    m45 = np.array([float(r["marge45"]) for r in lot])
    m12 = np.array([float(r["marge12"]) for r in lot])
    Ts = np.array([[float(r["tsne1"]), float(r["tsne2"])] for r in lot])
    Vx, _ = voisins_et_rangs(X)
    Vt, _ = voisins_et_rangs(Ts)
    bord_x = (premier[Vx] != premier[:, None]).mean(axis=1)
    bord_t = (premier[Vt] != premier[:, None]).mean(axis=1)
    out = {"outil": "outils/genome/tome3/juge-latents/juge_etats_marges.py",
           "definition_bord": "part des 10 voisins dont l'expert premier diffère",
           "classes": ["sous le 10e centile (gros points)", "jusqu'à la médiane", "au-delà"]}
    for nom, m in (("marge45", m45), ("marge12", m12)):
        c = classes(m)
        out[nom] = {"bord_origine": [float(bord_x[c == k].mean()) for k in range(3)],
                    "bord_tsne": [float(bord_t[c == k].mean()) for k in range(3)],
                    "effectifs": [int((c == k).sum()) for k in range(3)]}
    # corrélation de rang entre marges et bord (Spearman, écrit ici)
    def rang(v):
        r = np.empty(v.size); r[np.argsort(v, kind="stable")] = np.arange(v.size); return r
    for nom, m in (("marge45", m45), ("marge12", m12)):
        out[nom]["spearman_marge_bord_origine"] = float(np.corrcoef(rang(m), rang(bord_x))[0, 1])
        out[nom]["spearman_marge_bord_tsne"] = float(np.corrcoef(rang(m), rang(bord_t))[0, 1])
    out["spearman_marge45_marge12"] = float(np.corrcoef(rang(m45), rang(m12))[0, 1])
    # robustesse de la définition du bord : k = 5 et k = 20 (espace d'origine)
    import juge_etats as je
    je.K = 20
    V20, _ = je.voisins_et_rangs(X)                   # rangés du plus proche au plus loin
    rob = {}
    for k in (5, 20):
        b = (premier[V20[:, :k]] != premier[:, None]).mean(axis=1)
        rob[f"k{k}"] = {nom: [float(b[classes(m) == c].mean()) for c in range(3)]
                        for nom, m in (("marge45", m45), ("marge12", m12))}
    out["robustesse_bord_origine"] = rob
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
