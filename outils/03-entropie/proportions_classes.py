"""Proportions des trois classes d'échelle (e < médiane de ligne, e = médiane, e > médiane)
sur tous les tenseurs MXFP4 d'un GGUF : elles fixent le banc de réassemblage
(cuda/dispersion.cu) sur la répartition réelle.

Usage : python proportions_classes.py <fichier.gguf>
"""
import sys

import numpy as np

from gguf_lecture import LecteurGGUF

L = LecteurGGUF(sys.argv[1])
compte = np.zeros(3, np.int64)
for t in [t for t in L.tenseurs if t.nom_type == "MXFP4"]:
    blocs_ligne = t.dims[0] // 32
    e = np.ascontiguousarray(L.carte[t.decalage: t.decalage + t.nb_octets].reshape(-1, 17)[:, 0]).reshape(-1, blocs_ligne)
    med = np.sort(e, axis=1)[:, blocs_ligne // 2][:, None]   # même médiane que taux_mxfp4.rs
    compte += [(e < med).sum(), (e == med).sum(), (e > med).sum()]
p = compte / compte.sum()
print(f"{p[0]:.4f} {p[1]:.4f} {p[2]:.4f}")
