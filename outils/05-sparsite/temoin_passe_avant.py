"""Témoin de la passe avant numpy : sa perplexité doit retrouver celle de
llama-perplexity (b11515) sur les mêmes jetons, fenêtre 512, 16 fenêtres.

Seuil déclaré avant le lancement : écart relatif de la perplexité cumulée
< 0,5 % à chaque fenêtre. Raison : les poids sont F16 dans les deux calculs ;
llama.cpp arrondit en plus les activations en F16 dans ses produits (erreur
relative ~ 2^-11 ≈ 5e-4 par élément), ce qui ne peut déplacer la perplexité
que de l'ordre du dixième de pour cent ; 0,5 % laisse une marge de 5 sans
masquer une vraie erreur (une rotation RoPE fausse ou un masque causal décalé
déplacent la perplexité de dizaines de pour cent).

--casser : remplace la rotation par paires voisines par la rotation par
moitiés ; le témoin doit alors échouer (preuve qu'il peut tomber).

Usage : python -I temoin_passe_avant.py MODELE.gguf test.ids SORTIE_LLAMACPP
        [--casser] [--fenetres N]
"""
import json
import math
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import numpy as np  # noqa: E402

from llama_numpy import Modele, nll_chunk  # noqa: E402

SEUIL = 0.005


def tourner_moities(t, cos, sin):
    h = t.shape[-1] // 2
    a, b = t[..., :h], t[..., h:]
    c, s = cos[:, None, :], sin[:, None, :]
    return np.concatenate([a * c - b * s, a * s + b * c], axis=-1)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    mod_chemin, ids_chemin, ref_chemin = sys.argv[1:4]
    casser = "--casser" in sys.argv
    ref = [float(v) for v in re.findall(r"\[\d+\](\d+\.\d+)", Path(ref_chemin).read_text(errors="replace"))]
    if "--fenetres" in sys.argv:
        ref = ref[:int(sys.argv[sys.argv.index("--fenetres") + 1])]
    jetons = json.loads(Path(ids_chemin).read_text())
    m = Modele(mod_chemin)
    if casser:
        m._tourner = tourner_moities
    n_ctx, premier = 512, 256
    tot, cnt, ok = 0.0, 0, True
    t0 = time.time()
    for k in range(len(ref)):
        fen = jetons[k * n_ctx:(k + 1) * n_ctx]
        s, c = nll_chunk(m.avant(fen, depuis=premier), fen, premier)
        tot, cnt = tot + s, cnt + c
        ppl = math.exp(tot / cnt)
        ecart = abs(ppl - ref[k]) / ref[k]
        ok &= ecart < SEUIL
        print(f"[{k + 1}] numpy {ppl:.4f}  llama.cpp {ref[k]:.4f}  écart {100 * ecart:.3f} %", flush=True)
    print(f"durée {time.time() - t0:.1f} s ; seuil {100 * SEUIL} % ; "
          f"{'RÉUSSI' if ok else 'ÉCHEC'}{' (mode cassé)' if casser else ''}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
