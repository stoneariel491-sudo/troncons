"""Le choix de l'amortissement δ de la mutation synonyme, par validation croisée SUR LA CALIBRATION SEULE.

Éclaireur du génome des poids (genome/01-eclaireur.md § 5). Écrit le 2026-10-16, après le diagnostic de
sur-apprentissage (journaux/diagnostic-L0-E0.json : à δ = 0,01, erreur de sortie de calibration 0,2 %,
d'évaluation 4,4 %, frontière 3,5 %). Les entrées d'évaluation (fenêtres 0 à 9) ne sont PAS lues ici :
le choix de δ ne voit que la calibration (fenêtres 10 à 21), coupée en deux (10-15 pour ajuster, 16-21
pour juger).

PROCÉDURE, DÉCLARÉE AVANT LE LANCEMENT : experts 2 de chacune des couches 0, 8, 16, 23 (hors des experts
mesurés, qui sont les multiples de 4) ; matrices gate, up, down ; δ ∈ {0,1 ; 0,3 ; 1 ; 3 ; 10} ; score
= moyenne sur les 12 matrices du rapport (erreur de sortie synonyme / erreur de sortie frontière) sur la
moitié de jugement. δ* = l'argmin. La passe `synonyme` suivante tourne à δ* sur toute la calibration ;
son jugement reste celui déclaré dans synonyme.py (évaluation tenue à l'écart, deux moitiés, quatre
couches).

Utilisation : python -I -X utf8 choix_delta.py > journal.json
"""
import json
import sys
import time

import numpy as np

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
import synonyme as S  # noqa: E402

DELTAS = (0.1, 0.3, 1.0, 3.0, 10.0)
EXPERT = 2


def err(X, g, W, Wh):
    w2 = g * g
    return float((w2 * ((X @ (W - Wh).T) ** 2).sum(axis=1)).sum() / (w2 * ((X @ W.T) ** 2).sum(axis=1)).sum())


def main():
    m = S.Modele()
    cen = S.centres_globaux(m)["2"]
    t0 = time.time()
    rapports = {d: [] for d in DELTAS}
    lignes = []
    for l in S.COUCHES:
        calib = S.Entrees("calib", l)
        coupe = calib.h.shape[0] // 2
        Xa, ga = calib.expert(EXPERT, (0, coupe))
        Xb, gb = calib.expert(EXPERT, (coupe, calib.h.shape[0]))
        Ws = {}
        b = {r: m.biais(l, r, EXPERT) for r in S.ROLES}
        for role in S.ROLES:
            ex, codes = m.blocs(l, role, EXPERT)
            ex, codes = ex[0], codes[0]
            W = S.dequant(ex, codes)
            Ws[role] = W
            if role == "down":
                Xa_r = S.swiglu(Xa @ Ws["gate"].T + b["gate"], Xa @ Ws["up"].T + b["up"])
                Xb_r = S.swiglu(Xb @ Ws["gate"].T + b["gate"], Xb @ Ws["up"].T + b["up"])
            else:
                Xa_r, Xb_r = Xa, Xb
            ef = err(Xb_r, gb, W, S.reconstruire(ex, S.sym_frontiere(codes), cen))
            for d in DELTAS:
                sym = S.choisir(W, ex, cen, S.hessienne(Xa_r, ga, d), 0.0, np.zeros(8))
                es = err(Xb_r, gb, W, S.reconstruire(ex, sym, cen))
                rapports[d].append(es / ef)
                lignes.append({"couche": l, "role": role, "delta": d, "n_ajuste": int(Xa.shape[0]), "n_juge": int(Xb.shape[0]),
                               "err_frontiere": ef, "err_synonyme": es, "rapport": es / ef})
                print(l, role, d, f"{es / ef:.3f}", f"{time.time() - t0:.0f} s", file=sys.stderr, flush=True)
    moy = {str(d): float(np.mean(v)) for d, v in rapports.items()}
    dstar = min(DELTAS, key=lambda d: np.mean(rapports[d]))
    print(json.dumps({"outil": "choix_delta.py", "expert": EXPERT, "couches": S.COUCHES, "rapport_moyen": moy,
                      "delta_etoile": dstar, "lignes": lignes, "duree_s": time.time() - t0}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
