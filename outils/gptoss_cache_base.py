"""Le cache d'experts de la base (llama.cpp b11515, 323 emplacements) contre les autres politiques, sur
la génération réelle de l'invite de la base (traces « w » du traceur : la même exécution que celle dont
llama.cpp publie le bilan, témoin G5).

Pour chaque trace : la réplique exacte de la règle de llama.cpp (g_lru_llama, témoin G5 : égale au
succès près au bilan publié), notre LRU, LFU à demi-vie de 8 jetons, l'épinglage statique oracle (le
meilleur ensemble fixe de N experts, vu toute la trace) et Belady (l'optimum hors ligne), tous au même
nombre d'emplacements, en portée globale (un cache pour toutes les couches, comme llama.cpp).

Usage : python -I gptoss_cache_base.py --sortie <json> nom:emplacements:trace [...]
"""
import argparse
import json
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import chargement_localite as cl  # noqa: E402
import gptoss_localite as g  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sortie", required=True)
    ap.add_argument("specs", nargs="+")
    a = ap.parse_args()
    out = {}
    for spec in a.specs:
        nom, n, chemin = spec.split(":", 2)
        N = int(n)
        jetons, E = cl.lire_trace(chemin)
        L = len(jetons[0])
        gr = g.flux(jetons, E)
        acces = sum(len(x) for x in gr)
        r = {"trace": os.path.basename(chemin), "jetons": len(jetons), "couches": L, "experts": E,
             "emplacements": N, "fraction": N / (L * E), "acces": acces,
             "lru_llama": g.g_lru_llama(gr, N)[0] / acces, "lru": g.g_lru(gr, N), "lfu": g.g_lfu(gr, N, L),
             "statique_oracle": g.g_statique(gr, N, gr), "belady": g.g_belady(gr, N)}
        if max(r["lru"], r["lfu"], r["lru_llama"]) > r["belady"] + 1e-12:
            raise SystemExit(f"G3 tombé sur {nom}")
        out[nom] = r
        print(nom, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
    json.dump(out, open(a.sortie, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
