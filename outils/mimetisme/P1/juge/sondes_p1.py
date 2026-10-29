"""P1, juge : sondes S1 (tête avant la fin de message), S3 (fenêtres froides) et cassure C1ter (post hoc, dite).

Usage : python sondes_p1.py  (écrit mesures/mimetisme/P1/juge/sondes.json)
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import juge_p1 as J  # noqa: E402

CAP = 326
H = [8, 32, 64, 128, math.inf]


def nomh(h):
    return "inf" if math.isinf(h) else str(h)


def main():
    out = {}
    # C1ter : 50 groupes chauds de 4 (200 clés) cyclés, chacun suivi de 2 groupes froids jamais revus.
    synth = []
    froid = 10_000
    for i in range(1500):
        synth.append([[4 * (i % 50) + j for j in range(4)]])
        for _ in range(2):
            synth.append([[froid, froid + 1, froid + 2, froid + 3]])
            froid += 4
    out["C1ter"] = {"lru": J.taux(J.simuler(synth, CAP, "lru")),
                    "lfu_inf": J.taux(J.simuler(synth, CAP, "lfu", math.inf)),
                    "lfu_32": J.taux(J.simuler(synth, CAP, "lfu", 32))}
    print("C1ter", out["C1ter"], flush=True)

    # S1 : tête des générations (prose-en : <|return|> au jeton 109 de la génération ; wiki : boucle dès ~160)
    s1 = {}
    for gen, fin in [("prose-en", 109), ("wiki", 160)]:
        tg = J.lire(gen + ".generation")
        pl = J.simuler(tg, CAP, "lru")
        r = {"fin": fin, "lru_tete": J.taux(pl, 0, fin), "lru_queue": J.taux(pl, fin)}
        for h in H:
            pf = J.simuler(tg, CAP, "lfu", h)
            d_t = J.taux(pf, 0, fin) - J.taux(pl, 0, fin)
            d_q = J.taux(pf, fin) - J.taux(pl, fin)
            # blocs de 32 sur la tête seulement (blocs entiers)
            nb = fin // 32
            ds = [J.taux(pf, i, i + 32) - J.taux(pl, i, i + 32) for i in range(0, nb * 32, 32)]
            r[nomh(h)] = {"d_tete": d_t, "d_queue": d_q, "blocs_tete": ds}
        s1[gen] = r
        print("S1", gen, {k: (v if not isinstance(v, dict) else (round(v["d_tete"], 4), round(v["d_queue"], 4))) for k, v in r.items()}, flush=True)
    out["S1"] = s1

    # S3 : fenêtres froides de 256 jetons sur les lectures, cache vide à chaque fenêtre
    lect = ["code", "dialogue", "prose-en", "prose-fr", "wiki"]
    fen = []
    for L in lect:
        tr = J.lire(L + ".lecture")
        for a in range(0, len(tr) - 255, 256):
            w = tr[a:a + 256]
            r = {"genre": L, "debut": a, "lru": J.taux(J.simuler(w, CAP, "lru"))}
            for h in H:
                r[nomh(h)] = J.taux(J.simuler(w, CAP, "lfu", h))
            r["inv8"] = J.taux(J.simuler(w, CAP, "inv", 8))
            fen.append(r)
    hstar = {}
    for L in lect:
        autres = [f for f in fen if f["genre"] != L]
        moy = {nomh(h): sum(f[nomh(h)] - f["lru"] for f in autres) / len(autres) for h in H}
        hstar[L] = max(moy, key=lambda k: moy[k])
    ds = [f[hstar[f["genre"]]] - f["lru"] for f in fen]
    dinf = [f["inf"] - f["lru"] for f in fen]
    dinv = [f["inv8"] - f["lru"] for f in fen]

    def stat(v):
        m = sum(v) / len(v)
        s = math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1)) / math.sqrt(len(v))
        return {"n": len(v), "moyenne": m, "sigma": s, "z": m / s, "positifs": sum(x > 0 for x in v)}

    out["S3"] = {"hstar": hstar, "lfu_hstar_moins_lru": stat(ds), "lfu_inf_moins_lru": stat(dinf),
                 "inv8_moins_lru": stat(dinv), "fenetres": fen}
    print("S3", hstar, out["S3"]["lfu_hstar_moins_lru"], out["S3"]["lfu_inf_moins_lru"], out["S3"]["inv8_moins_lru"], flush=True)
    with open(os.path.join(J.SORTIE, "sondes.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    if sys.platform == "win32":
        import ctypes
        k = ctypes.windll.kernel32
        k.SetPriorityClass(k.GetCurrentProcess(), 0x4000)
    main()
