"""E6 : arrêt séquentiel de groupe (forme O'Brien-Fleming) rejoué sur les séries de KL par fenêtre du juge.
Seuils et témoins déclarés avant : mesures/mimetisme/humain/00-seuils-declares.md (amendement du 2026-10-27).
Usage : python -I -X utf8 e6_sequentiel.py <dossier_kl> <sortie.json>
"""
import glob
import json
import os
import sys

import numpy as np

LOOKS = (4, 6, 8, 10)
N = 10


def tstats(x):
    """t_k pour k dans LOOKS, x de forme (..., 10)."""
    out = []
    for k in LOOKS:
        s = x[..., :k]
        m = s.mean(axis=-1)
        sd = s.std(axis=-1, ddof=1)
        out.append(m / (sd / np.sqrt(k) + 1e-300))
    return np.stack(out, axis=-1)


def taux_franchissement(c, graine, n=200000):
    rng = np.random.default_rng(graine)
    x = rng.standard_normal((n, N))
    t = np.abs(tstats(x))
    bornes = np.array([c * np.sqrt(N / k) for k in LOOKS])
    return float((t >= bornes).any(axis=1).mean())


def calibrer(graine=20261027):
    lo, hi = 1.0, 6.0
    for _ in range(40):
        c = (lo + hi) / 2
        if taux_franchissement(c, graine, 100000) > 0.05:
            lo = c
        else:
            hi = c
    return (lo + hi) / 2


def main():
    dossier, sortie = sys.argv[1], sys.argv[2]
    c = calibrer()
    res = {"c": c, "temoin_taux_nulle_fraiche": taux_franchissement(c, 777),
           "cassure_c_sur_2": taux_franchissement(c / 2, 777), "series": {}}
    bornes = [c * np.sqrt(N / k) for k in LOOKS]
    res["bornes"] = dict(zip(map(str, LOOKS), bornes))
    utilises, signes_ok = [], []
    for f in sorted(glob.glob(os.path.join(dossier, "apparie-*-par-fenetre.csv"))):
        d = np.array([float(l.split(",")[1]) for l in open(f, encoding="utf-8").read().strip().splitlines()[1:]])
        assert len(d) == N
        t = tstats(d)
        arret = next((k for k, tk, b in zip(LOOKS, t, bornes) if abs(tk) >= b), None)
        final = bool(abs(t[-1]) >= bornes[-1])
        nom = os.path.basename(f)[len("apparie-"):-len("-par-fenetre.csv")]
        res["series"][nom] = {"t_aux_regards": [float(x) for x in t], "arret_a": arret, "decisif_a_10": final,
                              "signe_final": int(np.sign(d.mean())),
                              "signe_a_l_arret": int(np.sign(d[:arret].mean())) if arret else None}
        if final:
            utilises.append(arret if arret else N)
            signes_ok.append(arret is None or np.sign(d[:arret].mean()) == np.sign(d.mean()))
    res["fenetres_moyennes_series_decisives"] = float(np.mean(utilises)) if utilises else None
    res["n_series_decisives"] = len(utilises)
    res["memes_signes"] = bool(all(signes_ok))
    res["critere_tenu"] = bool(utilises and np.mean(utilises) <= 7 and all(signes_ok))
    json.dump(res, open(sortie, "w", encoding="utf-8"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
