"""Débits de décompression sur le processeur : zstd et lz4 contre une recopie mémoire.

Le lot : les premiers tenseurs Q4_K d'un GGUF jusqu'à --lot-mo Mio (octets bruts du
tenseur, tels qu'ils seraient stockés). Il est découpé en morceaux de --morceau-ko Kio,
compressés indépendamment (c'est la condition de la décompression parallèle et de
l'accès par tuile). Pour chaque codec et chaque nombre de fils : séries ABBA codec /
recopie numpy des mêmes octets, médiane et meilleure passe, dispersion.

zstd sur ces données ne trouve presque aucune correspondance : son débit de
décompression mesure surtout son décodeur de Huffman des littéraux (huff0, 4 flux).

Usage : python debits_cpu.py <fichier.gguf> <sortie.json> [--lot-mo 256] [--morceau-ko 1024] [--passes 5]
"""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import lz4.block
import numpy as np
import zstandard

from gguf_lecture import LecteurGGUF


def arg(nom, defaut):
    return int(sys.argv[sys.argv.index(nom) + 1]) if nom in sys.argv else defaut


def main():
    chemin, sortie = sys.argv[1], sys.argv[2]
    lot = arg("--lot-mo", 256) << 20
    morceau = arg("--morceau-ko", 1024) << 10
    passes = arg("--passes", 5)
    L = LecteurGGUF(chemin)
    parts = []
    total = 0
    for t in L.tenseurs:
        if t.nom_type != "Q4_K":
            continue
        if total + t.nb_octets > lot and parts:
            break
        parts.append(np.asarray(L.octets(t)))
        total += t.nb_octets
    brut = np.concatenate(parts)
    morceaux = [bytes(brut[i:i + morceau]) for i in range(0, len(brut), morceau)]
    codecs = {}
    for niveau in (1, 3):
        c = zstandard.ZstdCompressor(level=niveau)
        codecs[f"zstd{niveau}"] = ([c.compress(m) for m in morceaux], "zstd")
    codecs["lz4"] = ([lz4.block.compress(m, store_size=True) for m in morceaux], "lz4")
    resultats = {"fichier": chemin, "octets": len(brut), "morceau": morceau, "passes": passes, "codecs": {}}
    dz = zstandard.ZstdDecompressor()
    dest = np.empty_like(brut)

    def recopie(fils):
        def un(i):
            a = i * morceau
            np.copyto(dest[a:a + morceau], brut[a:a + morceau])
        with ThreadPoolExecutor(fils) as ex:
            list(ex.map(un, range(len(morceaux))))

    for nom, (comp, sorte) in codecs.items():
        taux = len(brut) / sum(len(c) for c in comp)
        assert all((dz.decompress(c) if sorte == "zstd" else lz4.block.decompress(c)) == m
                   for c, m in zip(comp[:4], morceaux[:4]))
        resultats["codecs"][nom] = {"taux": taux, "fils": {}}
        for fils in (1, 6, 16):
            def decomp(fils=fils):
                f = (lambda c: zstandard.ZstdDecompressor().decompress(c)) if sorte == "zstd" else lz4.block.decompress
                with ThreadPoolExecutor(fils) as ex:
                    list(ex.map(f, comp))
            td, tc = [], []
            for _ in range(passes):
                for etape in (0, 1, 1, 0):
                    t0 = time.perf_counter()
                    decomp() if etape == 0 else recopie(fils)
                    (td if etape == 0 else tc).append(time.perf_counter() - t0)
            md, mc = float(np.median(td)), float(np.median(tc))
            r = {"decomp_go_s_mediane": len(brut) / md / 1e9, "decomp_go_s_meilleure": len(brut) / min(td) / 1e9,
                 "recopie_go_s_mediane": len(brut) / mc / 1e9,
                 "dispersion_decomp": (max(td) - min(td)) / min(td), "temps": td}
            resultats["codecs"][nom]["fils"][fils] = r
            print(f"{nom:6s} taux {taux:.4f} {fils:2d} fils : {r['decomp_go_s_mediane']:.2f} Go/s "
                  f"(meilleure {r['decomp_go_s_meilleure']:.2f}), recopie {r['recopie_go_s_mediane']:.2f} Go/s, "
                  f"dispersion {100 * r['dispersion_decomp']:.0f} %", flush=True)
    json.dump(resultats, open(sortie, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
