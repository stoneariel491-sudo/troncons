"""P4, juge : la jambe « génération » du verdict. Les deux traces de génération du 120b bouclent-elles, et que donne le
prédicteur sur leur moitié de test ? Usage : python -I -X utf8 juge_generation.py <dossier_traces_120b> <sortie.json>"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import juge_p4 as jp  # noqa: E402


def main():
    dossier, sortie = sys.argv[1], sys.argv[2]
    out = {}
    for nom in ("t120b.prose-en.generation", "w120b.wiki.generation"):
        J, E = jp.lire(os.path.join(dossier, nom + ".trace"))
        T, L, k = J.shape
        demi = T // 2
        lignes = [tuple(map(tuple, J[t])) for t in range(T)]
        # part des jetons de la moitié de test dont le chemin complet (36 couches, ensembles triés) a déjà été vu
        vus = set(tuple(tuple(sorted(c)) for c in lignes[t]) for t in range(demi))
        deja = sum(tuple(tuple(sorted(c)) for c in lignes[t]) in vus for t in range(demi, T))
        cand, conf = jp.predire(J, E, 2)
        lab = jp.etiqueter(J, cand)
        dft, pres = jp.lru(J, E, 326, 2, cand)
        val = cand >= 0
        cal = np.zeros_like(val)
        cal[:demi] = True
        r = {"T": T, "chemins_test_deja_vus_en_calibration": deja / (T - demi),
             "theta_calibre": jp.calibrer(conf[cal & val & ~pres], lab[cal & val & ~pres]), "seuils": {}}
        for th in (0.7, 0.8, 0.9, 0.96):
            sc = cal & val & ~pres & (conf >= th - 1e-12)
            st = ~cal & val & ~pres & (conf >= th - 1e-12)
            r["seuils"][str(th)] = {"n_cal": int(sc.sum()), "prec_cal": float(lab[sc].mean()) if sc.sum() else None,
                                    "n_test": int(st.sum()), "prec_test": float(lab[st].mean()) if st.sum() else None,
                                    "borne_cp_cal": jp.borne_inf(int(lab[sc].sum()), int(sc.sum())) if sc.sum() else None}
        out[nom] = r
        print(nom, json.dumps(r, ensure_ascii=False), flush=True)
    json.dump(out, open(sortie, "w", encoding="utf-8"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
