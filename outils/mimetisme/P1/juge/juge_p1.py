"""P1, juge : simulateur indépendant de cache à règle de groupe (LRU, LFU à demi-vie, décroissance inversée).

Écrit depuis la spécification de genome/mimetisme/P1/protocole.md seule, sans lire cache_p1.py ni cache2.py.
Usage : python juge_p1.py  (écrit mesures/mimetisme/P1/juge/juge.json)
"""
import heapq
import json
import math
import os
import random
import sys

DON = "~/dev/mimetisme-P1-donnees/t120"
SORTIE = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "mesures", "mimetisme", "P1", "juge")

SORTIE_NOM = "juge.json"

FICHIERS = {
    "code.lecture": "t120b.code.lecture.trace",
    "dialogue.lecture": "t120b.dialogue.lecture.trace",
    "prose-en.lecture": "t120b.prose-en.lecture.trace",
    "prose-fr.lecture": "t120b.prose-fr.lecture.trace",
    "wiki.lecture": "w120b.wiki.lecture.trace",
    "prose-en.generation": "t120b.prose-en.generation.trace",
    "wiki.generation": "w120b.wiki.generation.trace",
}


def lire(nom):
    """Liste de jetons ; chaque jeton = liste de groupes (couche, [experts])."""
    jetons = []
    with open(os.path.join(DON, FICHIERS[nom]), encoding="utf-8") as f:
        for ligne in f:
            ligne = ligne.strip()
            if not ligne or ligne.startswith("#") or ligne.startswith("E="):
                continue
            groupes = [[int(x) for x in g.split()] for g in ligne.split("|")]
            jetons.append(groupes)
    return jetons


GARDE = True  # le compte survit à l'éviction (passe 2) ; False = compte perdu (passe 1)


def simuler(jetons, cap, politique, h=None):
    """Rend la liste des succès par jeton (nombre de succès, nombre d'accès).

    politique : 'lru', 'lfu' (h fini ou math.inf), 'inv' (décroissance inversée, h fini).
    Horloge = indice du jeton. Score d'éviction : plus petit évincé ; départage par numéro d'accès le plus ancien.
    """
    present = {}      # clé -> (score, dernier numéro d'accès)
    compte = {}       # clé -> (c au dernier accès, t du dernier accès)
    tas = []          # (score, numero, clé), invalidation paresseuse
    num = 0
    par_jeton = []
    for t, groupes in enumerate(jetons):
        s_hit = 0
        s_acc = 0
        for couche, experts in enumerate(groupes):
            groupe = set()
            for e in experts:
                cle = (couche, e)
                groupe.add(cle)
                s_acc += 1
                if cle in present:
                    s_hit += 1
                num += 1
                if politique == "lru":
                    score = num
                elif politique == "lfu":
                    if math.isinf(h):
                        c = (compte[cle][0] if (cle in present or (GARDE and cle in compte)) else 0) + 1
                        score = c
                    else:
                        if cle in present or (GARDE and cle in compte):
                            c0, t0 = compte[cle]
                            c = c0 * 2.0 ** (-(t - t0) / h) + 1.0
                        else:
                            c = 1.0
                        score = math.log2(c) + t / h
                    compte[cle] = (c, t)
                elif politique == "inv":
                    if cle in present or (GARDE and cle in compte):
                        c0, t0 = compte[cle]
                        c = c0 * 2.0 ** (+(t - t0) / h) + 1.0
                    else:
                        c = 1.0
                    compte[cle] = (c, t)
                    # score courant = c·2^(+(t_now−t)/h) ; comparaison invariante : log2 c − t/h
                    score = math.log2(c) - t / h
                else:
                    raise ValueError(politique)
                present[cle] = (score, num)
                heapq.heappush(tas, (score, num, cle))
            # éviction après insertion du groupe, victimes hors du groupe
            mis_de_cote = []
            while len(present) > cap:
                score, n, cle = heapq.heappop(tas)
                if cle not in present or present[cle] != (score, n):
                    continue
                if cle in groupe:
                    mis_de_cote.append((score, n, cle))
                    continue
                del present[cle]
                if not GARDE:
                    compte.pop(cle, None)
            for x in mis_de_cote:
                heapq.heappush(tas, x)
        par_jeton.append((s_hit, s_acc))
        if len(tas) > 8 * cap + 10000:
            tas = [(s, n, k) for k, (s, n) in present.items()]
            heapq.heapify(tas)
    return par_jeton


def taux(pj, a=0, b=None):
    seg = pj[a:b]
    return sum(x[0] for x in seg) / sum(x[1] for x in seg)


def ecart_z(pj_a, pj_b, a, b, bloc=32):
    """d = taux(b) − taux(a) sur [a, b) ; z par blocs appariés de 32 jetons."""
    ds = []
    for i in range(a, b, bloc):
        ds.append(taux(pj_b, i, min(i + bloc, b)) - taux(pj_a, i, min(i + bloc, b)))
    d = taux(pj_b, a, b) - taux(pj_a, a, b)
    n = len(ds)
    m = sum(ds) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in ds) / (n - 1))
    s = sd / math.sqrt(n)
    return d, s, (d / s if s > 0 else float("inf")), ds


def main():
    cap = 326
    H = [8, 32, 64, 128, math.inf]
    nomh = lambda h: "inf" if math.isinf(h) else str(h)
    traces = {k: lire(k) for k in FICHIERS}
    out = {"capacite": cap, "longueurs": {k: len(v) for k, v in traces.items()}}

    # témoins
    g = traces["prose-en.generation"]
    lru_g = simuler(g, cap, "lru")
    out["T1"] = {"lru": taux(lru_g), "lfu_h1e-3": taux(simuler(g, cap, "lfu", 1e-3))}
    out["T2_lfu_inf"] = taux(simuler(g, cap, "lfu", math.inf))
    synth = [[[4 * i, 4 * i + 1, 4 * i + 2, 4 * i + 3]] for i in range(82)] * 10
    synth2 = [[[4 * i, 4 * i + 1, 4 * i + 2, 4 * i + 3]] for i in range(164)] * 10  # C1 corrigé, post hoc
    out["C1"] = {"lru": taux(simuler(synth, cap, "lru")), "lfu_inf": taux(simuler(synth, cap, "lfu", math.inf))}
    out["C1bis"] = {"lru": taux(simuler(synth2, cap, "lru")), "lfu_inf": taux(simuler(synth2, cap, "lfu", math.inf))}
    out["C2"] = {"inv8": taux(simuler(g, cap, "inv", 8)), "lru": taux(lru_g)}
    print("GARDE", GARDE, "témoins", out["T1"], out["T2_lfu_inf"], out["C1"], out["C1bis"], out["C2"], flush=True)

    # validation croisée de h* sur les lectures, 326 emplacements
    lect = ["code", "dialogue", "prose-en", "prose-fr", "wiki"]
    cv = {}
    for L in lect:
        tr = traces[L + ".lecture"]
        r = {"lru": taux(simuler(tr, cap, "lru"))}
        for h in H:
            r["lfu:" + nomh(h)] = taux(simuler(tr, cap, "lfu", h))
        cv[L] = r
        print("lecture", L, r, flush=True)
    out["lectures"] = cv
    hstar = {}
    for gen in ["prose-en", "wiki"]:
        autres = [L for L in lect if L != gen]
        moy = {nomh(h): sum(cv[L]["lfu:" + nomh(h)] - cv[L]["lru"] for L in autres) / len(autres) for h in H}
        best = max(H, key=lambda h: (round(moy[nomh(h)], 12), -h if not math.isinf(h) else -1e18))
        hstar[gen] = {"moyennes": moy, "h": nomh(best)}
    out["hstar"] = hstar
    print("h*", hstar, flush=True)

    # verdict : quatre cas
    cas = {}
    for gen in ["prose-en", "wiki"]:
        hs = hstar[gen]["h"]
        hv = math.inf if hs == "inf" else int(hs)
        tg = traces[gen + ".generation"]
        tl = traces[gen + ".lecture"]
        n = len(tg)
        res = {}
        for nomc, tr, a in [("gen", tg, 0), ("chaine", tl + tg, len(tl))]:
            pl = simuler(tr, cap, "lru")
            r = {"lru": taux(pl, a), "par_h": {}}
            for h in H:
                pf = simuler(tr, cap, "lfu", h)
                d, s, z, ds = ecart_z(pl, pf, a, a + n)
                r["par_h"][nomh(h)] = {"lfu": taux(pf, a), "d": d, "sigma": s, "z": z, "blocs": ds}
                if nomh(h) == hs and nomc == "gen" and gen == "prose-en":
                    # C3 : appariement détruit par permutation des blocs
                    rnd = random.Random(7)
                    perm = ds[:]
                    blocs_l = [taux(pl, i, i + 32) for i in range(0, n, 32)]
                    blocs_f = [taux(pf, i, i + 32) for i in range(0, n, 32)]
                    rnd.shuffle(blocs_f)
                    dd = [f - l for f, l in zip(blocs_f, blocs_l)]
                    m = sum(dd) / len(dd)
                    sdp = math.sqrt(sum((x - m) ** 2 for x in dd) / (len(dd) - 1)) / math.sqrt(len(dd))
                    out["C3"] = {"z_apparie": z, "z_permute": m / sdp, "sigma_apparie": s, "sigma_permute": sdp}
            r["verdict_h*"] = r["par_h"][hs]
            res[nomc] = r
            print(gen, nomc, "LRU", r["lru"], "h*", hs, {k: (round(v["d"], 4), round(v["z"], 2)) for k, v in r["par_h"].items()}, flush=True)
        cas[gen] = res
    out["cas"] = cas

    os.makedirs(SORTIE, exist_ok=True)
    with open(os.path.join(SORTIE, SORTIE_NOM), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=str)


if __name__ == "__main__":
    if sys.platform == "win32":
        import ctypes
        k = ctypes.windll.kernel32
        k.SetPriorityClass(k.GetCurrentProcess(), 0x4000)  # sous la normale
    if "--oubli" in sys.argv:
        GARDE = False
        SORTIE_NOM = "juge-oubli.json"
    main()
