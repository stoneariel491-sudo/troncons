"""Où tombe l'erreur de la recette : par colonne (canal d'entrée) de chaque matrice d'un expert.

Lit la reconstruction écrite par `genome fidelite --ecrire` (Lll-Eee.f32w : gate, up, down en F32) et
l'expert exact du GGUF ; rend, par matrice : l'erreur relative, la part d'erreur des colonnes de rang
k mod 64 (rang 0 = la colonne que la transformée de Hadamard inverse charge d'une erreur constante sur
un morceau), le rapport max/moyenne de l'énergie d'erreur par colonne, et l'énergie de la colonne
exacte la plus forte (rapport à la moyenne).

Utilisation : python -I -X utf8 erreur_colonnes.py DOSSIER L E [L E ...] > erreur-colonnes.json
"""
import importlib.util
import json
import os
import sys

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("structure", os.path.join(ICI, "structure.py"))
st = importlib.util.module_from_spec(spec)
sys.modules["structure"] = st
spec.loader.exec_module(st)


def main():
    dossier = sys.argv[1]
    paires = list(zip(sys.argv[2::2], sys.argv[3::2]))
    lec = st.charger_lecteur().LecteurGGUF(st.FICHIER)
    idx = {t.nom: t for t in lec.tenseurs}
    sortie = []
    for l, e in paires:
        l, e = int(l), int(e)
        R = np.fromfile(os.path.join(dossier, f"L{l:02d}-E{e:02d}.f32w"), dtype=np.float32).reshape(3, 2880, 2880)
        for i, r in enumerate(st.ROLES):
            w = st.expert(lec, idx[f"blk.{l}.{r}.weight"], e)
            d = R[i] - w
            ce = (d ** 2).sum(0)
            cw = (w ** 2).sum(0)
            sortie.append({
                "couche": l, "expert": e, "role": r,
                "erreur_relative": float((d ** 2).sum() / (w ** 2).sum()),
                "part_colonnes_mod64": {str(k): float(ce[k::64].sum() / ce.sum() * 64) for k in (0, 1, 31, 63)},
                "erreur_colonne_max_sur_moyenne": float(ce.max() / ce.mean()),
                "colonne_erreur_max": int(ce.argmax()),
                "energie_colonne_max_sur_moyenne": float(cw.max() / cw.mean()),
                "colonne_energie_max": int(cw.argmax()),
            })
            print(json.dumps(sortie[-1]), file=sys.stderr)
    print(json.dumps(sortie, indent=1))


if __name__ == "__main__":
    main()
