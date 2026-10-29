"""Témoin de la chaîne à poids altérés : les entrées .kld d'un plan sans perte en valeur sont-elles
identiques, octet pour octet, à celles de la référence exacte, sur les fenêtres calculées ?

Les deux fichiers ont le format de llama-perplexity (en-tête, jetons, puis par fenêtre 255 entrées de
mots_par_entree(n_vocab) mots de 16 bits). On compare les entrées des n premières fenêtres du test à
celles de la base. Rend le nombre d'entrées différentes (0 attendu pour identité et zéro fondu).

Utilisation : python -I kld_identiques.py BASE.kld TEST.kld
"""
import json
import sys

import numpy as np


def entete(chemin):
    with open(chemin, "rb") as f:
        assert f.read(8) == b"_logits_"
        n_ctx, n_vocab, n_chunk = np.frombuffer(f.read(12), dtype="<i4")
    nv = 2 * ((int(n_vocab) + 1) // 2) + 4
    debut = 20 + int(n_ctx) * int(n_chunk) * 4
    par_fen = (int(n_ctx) // 2 - 1) * nv  # positions notées [n_ctx/2, n_ctx − 1)
    return int(n_ctx), int(n_vocab), int(n_chunk), nv, debut, par_fen


def main():
    base, test = sys.argv[1], sys.argv[2]
    nb, vb, cb, nvb, db, pfb = entete(base)
    nt, vt, ct, nvt, dt, pft = entete(test)
    assert (nb, vb) == (nt, vt)
    mb = np.memmap(base, dtype="<u2", mode="r", offset=db)
    mt = np.memmap(test, dtype="<u2", mode="r", offset=dt)
    n = ct * pft
    a = np.asarray(mb[:n]).reshape(ct * (nb // 2 - 1), nvt)
    b = np.asarray(mt[:n]).reshape(ct * (nt // 2 - 1), nvt)
    diff = int((a != b).any(axis=1).sum())
    print(json.dumps({"base": base, "test": test, "fenetres": ct, "entrees": int(a.shape[0]),
                      "entrees_differentes": diff, "identiques": diff == 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
