"""Place d'IQ2_XXS (llama.cpp) sur le banc gaussien du § 2 de fondations/02-quantification.md.

Codeur écrit ici d'après le format lu dans llama.cpp (ggml-common.h, shader Vulkan
mul_mat_vec_iq2_xxs.comp), pas d'après son code de quantification :
  - super-bloc de 256 poids, échelle d (flottant ; fp16 dans le format, écart négligeable) ;
  - 8 sous-blocs de 32 poids, sous-échelle de 4 bits ls : db = d * 0.25 * (0.5 + ls) ;
  - 4 groupes de 8 poids par sous-bloc : un index de 8 bits dans la grille de 256
    vecteurs de magnitudes (octets 8, 25, 43 : la table iq2xxs_grid, lue dans le clone),
    7 bits de signe, le 8e fixé par la parité (nombre pair de signes négatifs) ;
  - 2,0625 bits/poids.
Le codeur est optimal pour une échelle donnée : pour chaque groupe et chaque entrée de la
grille, l'erreur est Σ(|x| − db·g)² plus, si le nombre de négatifs est impair, le coût du
retournement le moins cher, min_j 4·|x_j|·db·g_j ; on garde l'entrée de coût minimal.
Les 16 valeurs de ls sont essayées pour chaque sous-bloc ; d est cherché sur une grille.

Témoin, seuil déclaré avant (4 erreurs-types) : avec une grille faite de toutes les
combinaisons de deux magnitudes {0.45278, 1.51042}^8 (256 entrées), sans contrainte de
parité et à échelle fixe, ce codeur EST le quantificateur scalaire de Lloyd-Max à 2 bits :
il doit rendre 0,117482. --casser décale la seconde magnitude de 10 %.

Usage : python quant-mse-iq2xxs.py <ggml-common.h> [--blocs 512] [--casser] > journal.json
"""
import argparse
import json
import math
import re
import sys

import numpy as np


def lire_grille(chemin):
    t = open(chemin, encoding="utf-8").read()
    m = re.search(r"GGML_TABLE_BEGIN\(uint64_t, iq2xxs_grid, 256\)(.*?)GGML_TABLE_END", t, re.S)
    vals = [int(v, 16) for v in re.findall(r"0x[0-9a-fA-F]{16}", m.group(1))]
    assert len(vals) == 256
    g = np.array([[(v >> (8 * k)) & 0xFF for k in range(8)] for v in vals], dtype=np.float64)
    return g


def cout_groupes(xa, neg_impair, db, grille, parite):
    """xa : (G, 8) magnitudes ; rend (G,) coût minimal et (G,) index, pour une échelle db."""
    rec = db * grille                                   # (256, 8)
    e = ((xa[:, None, :] - rec[None, :, :]) ** 2).sum(-1)   # (G, 256)
    if parite:
        flip = (4.0 * xa[:, None, :] * rec[None, :, :]).min(-1)   # (G, 256)
        e = e + neg_impair[:, None] * flip
    i = e.argmin(1)
    return e[np.arange(len(xa)), i], i


def mse_iq2xxs(x, grille, parite=True, d_grille=None, ls_fixe=None):
    blocs = x.reshape(-1, 256)
    total = 0.0
    erreurs = []
    for b in blocs:
        meilleur = math.inf
        for d in d_grille:
            eb = 0.0
            for s in range(8):
                sb = b[32 * s:32 * s + 32].reshape(4, 8)
                xa = np.abs(sb)
                neg = ((sb < 0).sum(1) % 2).astype(np.float64)
                lss = [ls_fixe] if ls_fixe is not None else range(16)
                eb += min(cout_groupes(xa, neg, d * 0.25 * (0.5 + ls), grille, parite)[0].sum() for ls in lss)
            meilleur = min(meilleur, eb)
        erreurs.append(meilleur / 256)
        total += meilleur
    e = np.array(erreurs)
    return float(e.mean()), float(e.std() / math.sqrt(len(e)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entete")
    ap.add_argument("--blocs", type=int, default=512)
    ap.add_argument("--casser", action="store_true")
    a = ap.parse_args()
    rng = np.random.default_rng(7)
    sortie = {"outil": "quant-mse-iq2xxs.py", "blocs": a.blocs}

    # Témoin : Lloyd-Max à 2 bits refait par la même machinerie
    m1, m2 = 0.45278, 1.51042 * (1.1 if a.casser else 1.0)
    combos = np.array([[m2 if (i >> k) & 1 else m1 for k in range(8)] for i in range(256)])
    xt = rng.standard_normal(256 * 256)
    # échelle fixe : d tel que d * 0.25 * (0.5 + 3) = 1, ls = 3
    m, se = mse_iq2xxs(xt, combos, parite=False, d_grille=[1.0 / (0.25 * 3.5)], ls_fixe=3)
    ok = abs(m - 0.117482) < 4 * se
    sortie["temoin"] = {"mse": round(m, 6), "erreur_type": round(se, 7), "attendu": 0.117482,
                        "tient": bool(ok), "casser": a.casser}
    print(json.dumps(sortie["temoin"]), file=sys.stderr)
    if a.casser:
        print(json.dumps(sortie, indent=1))
        return

    grille = lire_grille(a.entete)
    x = rng.standard_normal(256 * a.blocs)
    # d : la plus grande magnitude 43 doit couvrir ~2,5 σ avec ls au milieu ; grille large
    # Passe 1 : grille 0,02..0,10, l'optimum tombait au bord bas (journal
    # mse-iq2xxs-passe1-d-au-bord.json) ; grille élargie vers le bas, et l'outil dit si
    # l'optimum est intérieur.
    dg = np.linspace(0.004, 0.06, 29)
    # affinage autour du meilleur d trouvé sur un sous-échantillon
    res = [(mse_iq2xxs(x[: 256 * 32], grille, d_grille=[d])[0], d) for d in dg]
    dbest = min(res)[1]
    sortie["d_optimum_interieur"] = bool(dg[0] < dbest < dg[-1])
    sortie["recherche_d"] = [[round(float(d), 4), round(float(e), 6)] for e, d in res]
    dg2 = np.linspace(dbest * 0.85, dbest * 1.15, 7)
    m, se = mse_iq2xxs(x, grille, d_grille=dg2)
    sortie["iq2xxs"] = {"bits_par_poids": 2.0625, "mse": round(m, 6), "erreur_type": round(se, 7),
                        "d_grille": [round(float(v), 5) for v in dg2]}
    m2_, se2 = mse_iq2xxs(x[: 256 * 128], grille, parite=False, d_grille=dg2)
    sortie["iq2xxs_sans_parite_2_1875_bits"] = {"mse": round(m2_, 6), "erreur_type": round(se2, 7),
                                               "note": "8 bits de signe libres : 2,1875 bits/poids, pour mesurer le coût de la parité"}
    print(json.dumps(sortie, indent=1))


if __name__ == "__main__":
    main()
