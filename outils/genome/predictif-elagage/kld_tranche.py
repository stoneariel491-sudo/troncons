"""Tranche un fichier .kld (format de llama-perplexity) : garde les fenêtres [a, b).

Sert à évaluer la KL sur les fenêtres 5 à 9 seulement, tenues à l'écart de la calibration des plans
qui lisent les activations (fenêtres 0 à 4) : la tranche sert à la fois de source de jetons pour la
sonde et de base pour `juge kl`.

Témoin : relire la tranche, ses jetons et ses entrées égalent ceux des fenêtres [a, b) de l'original.

Utilisation : python -I kld_tranche.py ORIGINAL.kld A B SORTIE.kld
"""
import json
import sys

import numpy as np


def main():
    src, a, b, dst = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    with open(src, "rb") as f:
        tete = f.read(20)
        assert tete[:8] == b"_logits_"
        n_ctx, n_vocab, n_chunk = np.frombuffer(tete[8:20], dtype="<i4")
        n_ctx, n_vocab, n_chunk = int(n_ctx), int(n_vocab), int(n_chunk)
        jetons = np.frombuffer(f.read(n_ctx * n_chunk * 4), dtype="<i4")
        nv = 2 * ((n_vocab + 1) // 2) + 4
        par_fen = (n_ctx // 2 - 1) * nv * 2
        f.seek(20 + n_ctx * n_chunk * 4 + a * par_fen)
        entrees = f.read((b - a) * par_fen)
    assert len(entrees) == (b - a) * par_fen
    with open(dst, "wb") as g:
        g.write(b"_logits_")
        g.write(np.array([n_ctx, n_vocab, b - a], dtype="<i4").tobytes())
        g.write(jetons[a * n_ctx:b * n_ctx].tobytes())
        g.write(entrees)
    # Témoin : relecture.
    with open(dst, "rb") as g:
        g.seek(20)
        j2 = np.frombuffer(g.read(n_ctx * (b - a) * 4), dtype="<i4")
        e2 = g.read()
    ok = bool((j2 == jetons[a * n_ctx:b * n_ctx]).all() and e2 == entrees)
    print(json.dumps({"source": src, "fenetres": [a, b], "sortie": dst, "temoin_relu_egal": ok}, ensure_ascii=False))


if __name__ == "__main__":
    main()
