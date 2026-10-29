"""Compare deux traces de routage du même texte : part des choix (jeton, couche) identiques.

Deux moteurs justes (ou deux chemins de calcul d'un même moteur) lisent les mêmes poids ; s'ils
routent différemment, c'est que les états cachés diffèrent assez pour faire basculer un quasi
ex aequo du routeur, et l'écart se propage aux couches suivantes et aux jetons suivants (par le
cache KV). Rend : la part des ensembles de k experts identiques, globale et par couche, le nombre
de jetons identiques à toutes les couches, le premier écart, et la part des experts communs
(|A ∩ B| / k) quand les ensembles diffèrent.

Usage : python -I gptoss_comparer_traces.py A.trace B.trace --csv sortie.csv [--etiquette nom]
"""
import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chargement_localite as cl  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--csv", required=True)
    ap.add_argument("--etiquette", default="")
    x = ap.parse_args()
    A, _ = cl.lire_trace(x.a)
    B, _ = cl.lire_trace(x.b)
    T = min(len(A), len(B))
    L = len(A[0])
    k = len(A[0][0])
    memes = [0] * L
    communs = [0] * L
    jetons_identiques, premier = 0, None
    for t in range(T):
        tout = True
        for l in range(L):
            sa, sb = set(A[t][l]), set(B[t][l])
            communs[l] += len(sa & sb)
            if sa == sb:
                memes[l] += 1
            else:
                tout = False
                if premier is None:
                    premier = [t, l]
        jetons_identiques += tout
    res = {"etiquette": x.etiquette, "a": os.path.basename(x.a), "b": os.path.basename(x.b), "jetons": T,
           "couches": L, "k": k, "choix_identiques": sum(memes) / (T * L), "experts_communs": sum(communs) / (T * L * k),
           "jetons_identiques": jetons_identiques, "premier_ecart_jeton_couche": premier}
    print(json.dumps(res, ensure_ascii=False))
    with open(x.csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["couche", "choix_identiques", "experts_communs"])
        for l in range(L):
            w.writerow([l, round(memes[l] / T, 5), round(communs[l] / (T * k), 5)])
    with open(os.path.splitext(x.csv)[0] + ".json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
