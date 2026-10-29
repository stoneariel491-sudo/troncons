"""Diagnostic de la mutation synonyme : apprend-elle les entrées, ou seulement l'échantillon ?

Éclaireur du génome des poids (genome/01-eclaireur.md § 5). Écrit le 2026-10-16, APRÈS que les premiers
experts de la passe `synonyme λ=0, δ=0,01` ont rendu une erreur de sortie d'expert PLUS HAUTE que la
frontière sur les entrées d'évaluation (couche 0 : 0,083 contre 0,059 pour l'expert 0).

Hypothèse (déclarée avant ce diagnostic) : sur-apprentissage. Chaque expert ne reçoit que ≈ 766 entrées
de calibration en dimension 2 880 : la covariance estimée est de rang ≤ 766, et la rétroaction pousse
l'erreur dans les ≈ 2 100 directions que l'échantillon ne voit pas, mais que les entrées d'évaluation
excitent. Prédictions chiffrables : (1) l'erreur de sortie de calibration de `synonyme` est bien sous
celle de la frontière, celle d'évaluation au-dessus ; (2) l'écart évaluation/calibration se resserre
quand l'amortissement δ grandit ou quand on régularise H vers sa diagonale ; (3) avec la moitié des
entrées de calibration, l'erreur d'évaluation empire.
Témoin : la frontière (sans rétroaction) a la même erreur en calibration et en évaluation à ±10 %
(elle n'apprend rien de l'échantillon) ; cassure : aucune (diagnostic, pas une mesure publiée seule).

Utilisation : python -I -X utf8 diagnostic_calibration.py <couche> <expert> > journal.json
"""
import json
import sys
import time

import numpy as np

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
import synonyme as S  # noqa: E402


def err_sortie(X, g, W, Wh):
    w2 = g * g
    num = ((X @ (W - Wh).T) ** 2).sum(axis=1)
    den = ((X @ W.T) ** 2).sum(axis=1)
    return float((w2 * num).sum() / (w2 * den).sum())


def main():
    l, e = int(sys.argv[1]), int(sys.argv[2])
    m = S.Modele()
    cen = S.centres_globaux(m)["2"]
    calib, ev = S.Entrees("calib", l), S.Entrees("eval", l)
    Xc, gc = calib.expert(e)
    Xe, ge = ev.expert(e)
    t0 = time.time()
    res = {"couche": l, "expert": e, "n_calib": int(Xc.shape[0]), "n_eval": int(Xe.shape[0]), "lignes": []}
    for role in ("gate", "up"):
        ex, codes = m.blocs(l, role, e)
        ex, codes = ex[0], codes[0]
        W = S.dequant(ex, codes)
        Wf = S.reconstruire(ex, S.sym_frontiere(codes), cen)
        res["lignes"].append({"role": role, "variante": "frontiere", "calib": err_sortie(Xc, gc, W, Wf), "eval": err_sortie(Xe, ge, W, Wf)})
        essais = [("delta", d, Xc, gc) for d in (0.01, 0.1, 1.0, 10.0)]
        moitie = Xc.shape[0] // 2
        essais.append(("delta_moitie_calib", 0.01, Xc[:moitie], gc[:moitie]))
        essais.append(("delta_moitie_calib", 1.0, Xc[:moitie], gc[:moitie]))
        for nom, d, X, g in essais:
            H = S.hessienne(X, g, d)
            sym = S.choisir(W, ex, cen, H, 0.0, np.zeros(8))
            Wh = S.reconstruire(ex, sym, cen)
            res["lignes"].append({"role": role, "variante": f"synonyme {nom}={d}", "n": int(X.shape[0]),
                                  "calib": err_sortie(Xc, gc, W, Wh), "eval": err_sortie(Xe, ge, W, Wh),
                                  "err_poids": float(((W - Wh) ** 2).sum() / (W * W).sum())})
            print(role, nom, d, res["lignes"][-1], f"{time.time() - t0:.0f} s", file=sys.stderr, flush=True)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
