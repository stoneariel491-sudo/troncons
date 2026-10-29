"""P1, analyse post hoc A : fenêtres froides de 256 jetons sur des textes cohérents (lectures du 120b).
Déclarée avant calcul : genome/mimetisme/P1/posthoc-declare.md (commit 00093d8).

Usage : python -I -X utf8 fenetres_p1.py [modèle [cap,cap]]  (l'écart de cassure et le verdict portent sur la première capacité)
Écrit mesures/mimetisme/P1/fenetres-120b.json et fenetres-120b.csv
"""

import csv
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cache_p1 as cp  # noqa: E402

M = sys.argv[1] if len(sys.argv) > 1 else "120b"
CAPS = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [326, 922]
LARGEUR = 256
POLS = ["lru"] + ["lfu:" + ("inf" if math.isinf(h) else str(h)) for h in cp.H_GRILLE]


def main():
    cp.baisser_priorite()
    genres = cp.GENRES[M]
    res = {"capacites": {}}
    lignes = []
    inv = {}
    for cap in CAPS:
        # succès par fenêtre et par politique
        succ = {}  # (genre, fenêtre, pol) -> succès
        for g in genres:
            G, E = cp.lire(M, g, "lecture")
            ak = G.shape[1] * G.shape[2]
            nfen = G.shape[0] // LARGEUR
            for i in range(nfen):
                Gf = G[i * LARGEUR:(i + 1) * LARGEUR]
                for p in POLS:
                    h = cp.politique(Gf, cap, p, G.shape[1], E)
                    succ[(g, i, p)] = float(h.sum() / (LARGEUR * ak))
                if cap == CAPS[0]:
                    hinv = cp.lfu(Gf.tolist(), cap, 8, inverse=True)
                    inv[(g, i)] = float(hinv.sum() / (LARGEUR * ak))
        fen = {g: sorted({i for (gg, i, p) in succ if gg == g}) for g in genres}
        # h* de chaque genre : meilleur écart moyen sur les fenêtres des autres genres
        lfus = [p for p in POLS if p.startswith("lfu:")]

        def d(g, i, p):
            return succ[(g, i, p)] - succ[(g, i, "lru")]

        sortie = {"par_genre": {}, "global": {}}
        toutes = []
        for g in genres:
            autres = [(gg, i) for gg in genres if gg != g for i in fen[gg]]
            sc = {p: float(np.mean([d(gg, i, p) for gg, i in autres])) for p in lfus}
            hstar = max(lfus, key=lambda p: (sc[p], -lfus.index(p)))
            ds = [d(g, i, hstar) for i in fen[g]]
            orac = {p: float(np.mean([d(g, i, p) for i in fen[g]])) for p in lfus}
            sortie["par_genre"][g] = {"n": len(ds), "h_etoile": hstar, "cv_autres": sc, "d_moyen": float(np.mean(ds)), "oracle_par_h": orac,
                                      "lru_moyen": float(np.mean([succ[(g, i, "lru")] for i in fen[g]]))}
            toutes += ds
            for i in fen[g]:
                lignes.append({"capacite": cap, "genre": g, "fenetre": i, "h_etoile": hstar, "lru": succ[(g, i, "lru")],
                               **{p: succ[(g, i, p)] for p in lfus}, "d_hetoile": d(g, i, hstar)})
        toutes = np.array(toutes)
        dm = float(toutes.mean())
        sig = float(toutes.std(ddof=1) / math.sqrt(len(toutes)))
        sortie["global"] = {"n_fenetres": int(len(toutes)), "d_moyen": dm, "sigma": sig, "z": dm / sig,
                            "genres_au_dessus_de_0_02": int(sum(1 for g in genres if sortie["par_genre"][g]["d_moyen"] >= 0.02)),
                            "fenetres_ou_lfu_gagne": int((toutes > 0).sum())}
        if cap == CAPS[0]:
            ok = dm >= 0.02 and dm / sig > 2 and sortie["global"]["genres_au_dessus_de_0_02"] >= 3
            sortie["global"]["verdict_posthoc"] = "tient" if ok else ("tombe" if dm < 0.005 else "ouvert")
            ecarts_inv = [succ[(g, i, "lru")] - inv[(g, i)] for g in genres for i in fen[g]]
            sortie["cassure_inversee_h8"] = {"chute_moyenne_sous_le_lru": float(np.mean(ecarts_inv)), "tient_si_plus_de_0_02": bool(np.mean(ecarts_inv) > 0.02)}
        res["capacites"][str(cap)] = sortie
        print(cap, json.dumps(sortie["global"], ensure_ascii=False), flush=True)
        for g in genres:
            pg = sortie["par_genre"][g]
            print("  ", g, pg["n"], pg["h_etoile"], "d moyen %+.4f" % pg["d_moyen"], "LRU moyen %.4f" % pg["lru_moyen"], flush=True)
    json.dump(res, open(f"{cp.SORTIE}/fenetres-{M}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(f"{cp.SORTIE}/fenetres-{M}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0].keys()))
        w.writeheader()
        w.writerows(lignes)


if __name__ == "__main__":
    main()
