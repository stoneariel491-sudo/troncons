"""Témoin T2 (cassure) déclaré dans seuil-declare.md : ordre des jetons mélangé, l'avance de M-B sur la LFU doit
tomber dans +-0,5 point ; M-C est aussi passée à l'ordre mélangé (sa phase ne lit pas l'ordre des jetons).
20b, f = 0,20, genres code et prose-en, demi-vie 32 pour la LFU et M-C, (p, c) = (0,5 ; 2) pour M-B.
Usage : python -I -X utf8 t2_melange.py <dossier_traces_20b> <sortie.json>"""
import json
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
sys.path.insert(0, os.path.abspath(os.path.join(ICI, "..", "..")))
import cache_terre as ct  # noqa: E402
import gptoss_localite as gl  # noqa: E402
import phase_terre as pt  # noqa: E402

out = {}
for genre in ("code", "prose-en"):
    for melange in (False, True):
        jetons, E = ct.charger("t20b", sys.argv[1], genre, melange)
        L = len(jetons[0])
        gr = gl.flux(jetons, E)
        N = round(0.20 * L * E)
        lfu = gl.g_lfu(gr, N, L, 32.0)
        s, tot = ct.g_omori(gr, N, L, E, 0.5, 2.0)
        sc, _ = pt.g_phase(gr, N, L, E, 32, "phase")
        out[f"{genre}-{'melange' if melange else 'ordre'}"] = {"lfu32": lfu, "B": s / tot, "dB_pt": (s / tot - lfu) * 100,
                                                              "C": sc / tot, "dC_pt": (sc / tot - lfu) * 100}
        print(genre, melange, out[f"{genre}-{'melange' if melange else 'ordre'}"], flush=True)
json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
