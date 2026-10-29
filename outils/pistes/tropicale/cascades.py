"""Exploration, après le verdict (ne décide rien, seuil-declare.md § 5) : les cascades de bascules.

La propagation mesurée par lois.py (P(bascule en ℓ+1 | bascule en ℓ) = 26,6 % contre 3,4 %) dit que
beaucoup de bascules sont les suites d'une première. Une garde qui réparerait la première ferait
disparaître ses suites ; ce qu'il faut attraper, c'est la racine. Ce script mesure, avec la même garde
(marge de B < τ₁₀ global) :

- bascule **primaire** : aucune bascule à une couche antérieure, même position ; **secondaire** sinon ;
  b(τ₁₀) pour chaque classe ;
- garde **par position** : part des positions à bascule dont la première bascule est signalée ;
- allocation **par couche** du budget de 10 % (τ_ℓ appris sur une moitié des fenêtres, jugé sur
  l'autre, puis l'inverse), pour voir ce que rendrait une garde réglée couche par couche.

Usage : python -I -X utf8 cascades.py
"""

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import routage as R  # noqa: E402

import numpy as np  # noqa: E402


def main():
    R.sous_la_normale()
    R.attendre_calme()
    ea, ma = R.lire(R.A)
    eb, mb = R.lire(R.B)
    L, N = mb.shape
    bas = R.bascules(ea, eb)
    t10 = R.tau_decile(mb)
    sig = mb < t10
    avant = np.zeros_like(bas)
    avant[1:] = np.cumsum(bas, axis=0)[:-1] > 0  # une bascule à une couche antérieure, même position
    prim = bas & ~avant
    sec = bas & avant
    res = {"outil": "outils/pistes/tropicale/cascades.py", "tau10": t10,
           "bascules": int(bas.sum()), "primaires": int(prim.sum()), "secondaires": int(sec.sum()),
           "b_tau10_primaires": float(sig[prim].mean()), "b_tau10_secondaires": float(sig[sec].mean()),
           "marge_mediane_primaires": float(np.median(mb[prim])), "marge_mediane_secondaires": float(np.median(mb[sec]))}
    # par position : la première bascule est-elle signalée ?
    a_bascule = bas.any(axis=0)
    premiere = np.argmax(bas, axis=0)
    p_idx = np.nonzero(a_bascule)[0]
    res["positions_a_bascule"] = int(a_bascule.sum())
    res["positions"] = int(N)
    res["part_positions_premiere_signalee"] = float(sig[premiere[p_idx], p_idx].mean())
    # par couche : primaires et secondaires
    lignes = []
    for l in range(L):
        lignes.append([l, int(prim[l].sum()), int(sec[l].sum()),
                       f"{sig[l][prim[l]].mean() if prim[l].any() else float('nan'):.4f}",
                       f"{sig[l][sec[l]].mean() if sec[l].any() else float('nan'):.4f}",
                       f"{np.median(mb[l][prim[l]]) if prim[l].any() else float('nan'):.4e}",
                       f"{np.median(mb[l][sec[l]]) if sec[l].any() else float('nan'):.4e}"])
    with open(R.SORTIE / "cascades-par-couche.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["couche", "primaires", "secondaires", "b_tau10_primaires", "b_tau10_secondaires",
                    "marge_mediane_primaires", "marge_mediane_secondaires"])
        w.writerows(lignes)

    # allocation par couche, validée de façon croisée par fenêtres (5 + 5)
    fen = np.arange(N) // R.LONG
    bords = np.concatenate([[0.0], np.logspace(-5, 0, 26), [np.inf]])
    croise = []
    for apprendre, juger in ((fen < 5, fen >= 5), (fen >= 5, fen < 5)):
        # P(bascule | classe de marge, couche), lissée (a priori : le taux de la couche, poids 2)
        score = np.zeros((L, int(juger.sum())))
        for l in range(L):
            m_a, b_a = mb[l][apprendre], bas[l][apprendre]
            k_a = np.digitize(m_a, bords) - 1
            base = b_a.mean()
            p = np.array([(b_a[k_a == k].sum() + 2 * base) / ((k_a == k).sum() + 2) for k in range(len(bords) - 1)])
            score[l] = p[np.digitize(mb[l][juger], bords) - 1]
        bj = bas[:, juger]
        n_budget = int(0.10 * score.size)
        ordre = np.argsort(-score.ravel(), kind="stable")[:n_budget]
        choisi = np.zeros(score.size, dtype=bool)
        choisi[ordre] = True
        choisi = choisi.reshape(score.shape)
        sig_g = mb[:, juger] < R.tau_decile(mb[:, juger])
        croise.append({"b_par_couche_apprise": float(bj[choisi].sum() / bj.sum()),
                       "b_global_meme_moitie": float(bj[sig_g].sum() / bj.sum()),
                       "part_cellules": float(choisi.mean())})
    res["allocation_par_couche_validee"] = croise

    # extrapolation pour les racines (modèle, dit tel) : δ = m_A − m_B sur les cellules sans bascule
    # antérieure ni présente, à grande marge (m_B > 0,1) ; P(racine | m, rien avant) = P(s δ < −m) ;
    # garde : marge de B < τ₁₀ global ; la part attendue des racines signalées se lit pour chaque s.
    ext = []
    for s in (0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0):
        att = tot = 0.0
        for l in range(L):
            libre = ~avant[l]
            d = np.sort((ma[l] - mb[l]).astype(np.float64)[libre & ~bas[l] & (mb[l] > 0.1)])
            m = mb[l][libre].astype(np.float64)
            pe = np.searchsorted(d, -m / s, side="left") / d.size
            att += pe[sig[l][libre]].sum()
            tot += pe.sum()
        ext.append({"facteur_s": s, "racines_predites": tot, "b_tau10_racines_predit": att / tot})
    res["extrapolation_racines_empirique"] = ext
    res["validation_s1"] = {"racines_comptees": int(prim.sum()), "b_tau10_mesure": float(sig[prim].mean())}
    (R.SORTIE / "cascades.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=2))
    for r in lignes:
        print(*r)


if __name__ == "__main__":
    main()
