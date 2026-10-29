"""La forme de l'erreur de sortie : quelle part est un simple changement de gain (parallèle à la sortie
exacte), quelle part est orthogonale ; et l'erreur par position (médiane, queue).

Hypothèse à tester : la base quantifie chaque poids vers le centre de sa classe ; une part de son erreur
est corrélée au poids lui-même (rétrécissement), donc à la sortie, ce qu'une normalisation en aval
efface en partie ; l'erreur du brin est, elle, de direction quelconque.

Pour un expert (l, e) et les positions « eval » routées vers lui : y exact, y_base, y_S* (poids lus dans
les fichiers .f32w de `base-f32w` et de `fidelite --ecrire`), biais du GGUF.

Utilisation : python -I -X utf8 erreur_sortie_forme.py DOSSIER_BASE DOSSIER_RECETTE EVAL L E [L E …]
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


def swiglu(g, u):
    g = np.minimum(g, 7.0)
    u = np.clip(u, -7.0, 7.0)
    return g / (1.0 + np.exp(-1.702 * g)) * (u + 1.0)


def sortie(W, b, x):
    g = x @ W[0].T + b[0]
    u = x @ W[1].T + b[1]
    return swiglu(g, u) @ W[2].T + b[2]


def main():
    d_base, d_rec, d_eval = sys.argv[1:4]
    paires = list(zip(sys.argv[4::2], sys.argv[5::2]))
    lec = st.charger_lecteur().LecteurGGUF(st.FICHIER)
    idx = {t.nom: t for t in lec.tenseurs}
    res = []
    for l, e in paires:
        l, e = int(l), int(e)
        h = np.fromfile(os.path.join(d_eval, f"h-L{l:02d}.f32"), dtype=np.float32).reshape(-1, 2880)
        r = np.fromfile(os.path.join(d_eval, f"routage-L{l:02d}.bin"), dtype=np.uint8).reshape(-1, 20)[:, :4]
        x = h[(r == e).any(1)][:512].astype(np.float64)
        W = [st.expert(lec, idx[f"blk.{l}.{ro}.weight"], e) for ro in st.ROLES]
        b = []
        for ro in st.ROLES:
            t = idx[f"blk.{l}.{ro}.bias"]
            o = np.asarray(lec.octets(t)).view(np.float32).reshape(-1, 2880)
            b.append(o[e].astype(np.float64))
        Wb = np.fromfile(os.path.join(d_base, f"L{l:02d}-E{e:02d}.f32w"), dtype=np.float32).reshape(3, 2880, 2880).astype(np.float64)
        Wr = np.fromfile(os.path.join(d_rec, f"L{l:02d}-E{e:02d}.f32w"), dtype=np.float32).reshape(3, 2880, 2880).astype(np.float64)
        y = sortie(W, b, x)
        ligne = {"couche": l, "expert": e, "positions": int(len(x))}
        for nom, Wq in (("base", Wb), ("recette", Wr)):
            yq = sortie(Wq, b, x)
            err = yq - y
            n2 = (y ** 2).sum(1)
            par = (err * y).sum(1) / n2            # gain : err = par · y + orth
            orth = err - par[:, None] * y
            rel = (err ** 2).sum(1) / n2
            ligne[nom] = {
                "erreur_relative_cumulee": float((err ** 2).sum() / n2.sum()),
                "part_parallele": float(((par[:, None] * y) ** 2).sum() / (err ** 2).sum()),
                "gain_moyen": float(par.mean()),
                "erreur_orthogonale_cumulee": float((orth ** 2).sum() / n2.sum()),
                "erreur_relative_mediane_par_position": float(np.median(rel)),
                "erreur_relative_p99_par_position": float(np.quantile(rel, 0.99)),
            }
        res.append(ligne)
        print(json.dumps(ligne), file=sys.stderr)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
