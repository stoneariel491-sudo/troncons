"""Ce qu'un codeur d'octets d'ordre 0 (le décodeur v4) peut prendre à chaque type K,
si l'on sépare le bloc en flux d'octets de même nature (le « byte grouping » de ZipNN,
appliqué aux champs des blocs K) : H0 de chaque flux, et taux total, contre la borne
des codes entiers (mesure_entropie.py).

Usage : python flux_octets.py <fichier.gguf> <sortie.json> [max_tenseurs_par_type]
"""
import json
import sys
from collections import defaultdict

import numpy as np

from gguf_lecture import LecteurGGUF

# (nom du flux, début, fin) dans le bloc, d'après ggml-common.h ; d et dmin sont
# coupés en octet bas et octet haut (l'octet haut porte signe et exposant fp16).
CHAMPS = {
    "Q4_K": (144, [("d_bas", 0, 1), ("d_haut", 1, 2), ("dmin_bas", 2, 3), ("dmin_haut", 3, 4),
                   ("echelles", 4, 16), ("qs", 16, 144)]),
    "Q5_K": (176, [("d_bas", 0, 1), ("d_haut", 1, 2), ("dmin_bas", 2, 3), ("dmin_haut", 3, 4),
                   ("echelles", 4, 16), ("qh", 16, 48), ("qs", 48, 176)]),
    "Q6_K": (210, [("ql", 0, 128), ("qh", 128, 192), ("echelles", 192, 208),
                   ("d_bas", 208, 209), ("d_haut", 209, 210)]),
    "Q8_0": (34, [("d_bas", 0, 1), ("d_haut", 1, 2), ("qs", 2, 34)]),
}


def h0(hist):
    p = hist[hist > 0] / hist.sum()
    return float(-(p * np.log2(p)).sum())


def main():
    chemin, sortie = sys.argv[1], sys.argv[2]
    maxi = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
    L = LecteurGGUF(chemin)
    vus = defaultdict(int)
    hist = defaultdict(lambda: np.zeros(256, np.int64))
    octets_type = defaultdict(int)
    for t in L.tenseurs:
        if t.nom_type not in CHAMPS or vus[t.nom_type] >= maxi:
            continue
        vus[t.nom_type] += 1
        taille, champs = CHAMPS[t.nom_type]
        b = np.asarray(L.octets(t)).reshape(-1, taille)
        octets_type[t.nom_type] += b.size
        for nom, a, z in champs:
            hist[(t.nom_type, nom)] += np.bincount(b[:, a:z].ravel(), minlength=256)
    res = {}
    for ty, (taille, champs) in CHAMPS.items():
        if not octets_type[ty]:
            continue
        bits = 0.0
        detail = {}
        for nom, a, z in champs:
            h = hist[(ty, nom)]
            e = h0(h)
            detail[nom] = {"octets_par_bloc": z - a, "H0_bits_par_octet": e}
            bits += e * (z - a)
        res[ty] = {"tenseurs": vus[ty], "octets": octets_type[ty], "flux": detail,
                   "bits_par_bloc_ideaux": bits, "taux_ordre0_par_flux": taille * 8 / bits}
        print(f"{ty} ({vus[ty]} tenseurs) : taux d'ordre 0 par flux d'octets {taille * 8 / bits:.4f} ; "
              + ", ".join(f"{n} {d['H0_bits_par_octet']:.3f}" for n, d in detail.items()))
    json.dump(res, open(sortie, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
