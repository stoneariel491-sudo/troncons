"""Localité des experts d'un jeton au suivant, et ce qu'un cache en tire.

Entrée : une trace de routage, un jeton par ligne, les couches séparées par « | », les
experts d'une couche séparés par des espaces. Exemple pour 2 couches, top-2 :
    3 17 | 5 9
    3 40 | 5 2
Une ligne qui commence par « # » est un commentaire. La première ligne non commentée peut
déclarer « E=128 » (nombre d'experts par couche) ; sinon E = plus grand identifiant + 1.

Mesures, couche par couche puis moyennées :
  - réutilisation adjacente r = |S_t ∩ S_{t-1}| / k ;
  - sa valeur « au hasard » sous deux hypothèses : uniforme, k / E ; et à popularité
    réelle, sum_e pi_e^2 / k, où pi_e est la fréquence d'inclusion de l'expert e
    (deux tirages indépendants de même loi marginale) ;
  - distance de réutilisation (jetons entre deux usages du même expert) : médiane, moyenne ;
  - taux de succès d'un cache de C experts par couche, pour LRU, LFU à demi-vie, épinglage
    statique calibré sur les premiers 10 % (évalué sur le reste), épinglage statique oracle
    (fréquences de toute la trace) et Belady (optimum hors ligne, borne haute).

Témoins synthétiques (--temoins), chacun avec sa réponse connue et sa tolérance déclarée
avant le calcul (4 écarts-types de l'estimateur, dérivés analytiquement) :
  T1 routage i.i.d. uniforme : r = k/E ; tout cache sans connaissance du futur a un
     succès C/E (les demandes futures sont indépendantes de son contenu) ;
  T2 routage figé (même ensemble à chaque jeton) : r = 1, succès -> 1 dès que C >= k ;
  T3 routage collant : chaque place garde son expert avec la probabilité rho, sinon tire
     parmi les experts absents de l'ensemble courant : r = rho, plus un terme positif borné
     par (1 - rho)^2 k / (E - k) (une place tirée après une autre peut reprendre l'expert que
     celle-ci vient de libérer) ;
  T4 invariant : Belady >= LRU et LFU, sur chaque couche et chaque budget (même capacité,
     mêmes défauts de démarrage). L'épinglage statique n'entre pas dans l'invariant : il
     garde C experts épinglés plus les k du jeton courant en transit, soit C + k places, et
     ne paie pas de défaut de démarrage ; il peut donc dépasser Belady de peu. (Première
     passe : l'invariant l'incluait, et il est tombé à tort sur la trace mélangée.)
--casser mélange l'ordre des jetons avant la mesure : la localité de T3 disparaît, r
retombe au hasard, et le témoin T3 doit tomber (preuve que l'instrument voit l'ordre).

Usage :
  python -I outils/chargement_localite.py --temoins [--casser] [--sortie J.json]
  python -I outils/chargement_localite.py --trace T.txt --budgets 4,8,16,32 [--sortie J.json]
"""

import argparse
import json
import math
import os
import random
import statistics
import sys
from collections import OrderedDict


def lire_trace(chemin):
    jetons, E = [], None
    with open(chemin, encoding="utf-8") as f:
        for ligne in f:
            ligne = ligne.strip()
            if not ligne or ligne.startswith("#"):
                continue
            if ligne.startswith("E="):
                E = int(ligne[2:])
                continue
            jetons.append([[int(x) for x in c.split()] for c in ligne.split("|")])
    if E is None:
        E = 1 + max(e for t in jetons for c in t for e in c)
    return jetons, E


def par_couche(jetons, couche):
    return [t[couche] for t in jetons]


def reutilisation(seq, E):
    k = len(seq[0])
    r = [len(set(a) & set(b)) / k for a, b in zip(seq, seq[1:])]
    compte = [0] * E
    for s in seq:
        for e in s:
            compte[e] += 1
    T = len(seq)
    pi = [c / T for c in compte]
    hasard_pop = sum(p * p for p in pi) / k
    return statistics.fmean(r), k / E, hasard_pop, compte


def distances(seq):
    dernier, d = {}, []
    for t, s in enumerate(seq):
        for e in s:
            if e in dernier:
                d.append(t - dernier[e])
            dernier[e] = t
    if not d:
        return None, None
    return statistics.median(d), statistics.fmean(d)


def cache_lru(seq, C):
    cache, succes, total = OrderedDict(), 0, 0
    for s in seq:
        for e in s:
            total += 1
            if e in cache:
                succes += 1
                cache.move_to_end(e)
            else:
                cache[e] = True
                if len(cache) > C:
                    # on n'évince jamais un expert demandé par le jeton courant
                    for v in cache:
                        if v not in s:
                            del cache[v]
                            break
    return succes / total


def cache_lfu(seq, C, demi_vie=8.0):
    """LFU à compteurs décroissants (demi-vie en jetons), départage par ancienneté."""
    # Décroissance paresseuse : score[e] = (valeur, instant) ; valeur effective au temps t =
    # valeur * decroit^(t - instant). Comparer à t fixé revient à comparer log-valeurs.
    decroit = 0.5 ** (1.0 / demi_vie)
    score, vu, cache, succes, total = {}, {}, set(), 0, 0

    def effectif(e, t):
        v, t0 = score.get(e, (0.0, t))
        return v * decroit ** (t - t0)

    for t, s in enumerate(seq):
        for e in s:
            total += 1
            score[e] = (effectif(e, t) + 1.0, t)
            vu[e] = t
            if e in cache:
                succes += 1
            else:
                cache.add(e)
                if len(cache) > C:
                    candidats = [v for v in cache if v not in s]
                    victime = min(candidats, key=lambda v: (effectif(v, t), vu.get(v, -1)))
                    cache.remove(victime)
    return succes / total


def cache_statique(seq, C, calibration):
    compte = {}
    for s in calibration:
        for e in s:
            compte[e] = compte.get(e, 0) + 1
    epingles = set(sorted(compte, key=lambda e: -compte[e])[:C])
    total = sum(len(s) for s in seq)
    return sum(1 for s in seq for e in s if e in epingles) / total


def cache_belady(seq, C):
    """Optimum hors ligne : on évince l'expert dont le prochain usage est le plus lointain."""
    T = len(seq)
    prochain = [dict() for _ in range(T)]
    suivant = {}
    for t in range(T - 1, -1, -1):
        for e in seq[t]:
            prochain[t][e] = suivant.get(e, math.inf)
        for e in seq[t]:
            suivant[e] = t
    cache, succes, total = {}, 0, 0  # expert -> prochain usage
    for t, s in enumerate(seq):
        for e in s:
            total += 1
            if e in cache:
                succes += 1
            cache[e] = prochain[t][e]
        while len(cache) > C:
            candidats = [v for v in cache if v not in s]
            victime = max(candidats, key=lambda v: cache[v])
            del cache[victime]
    return succes / total


def mesurer(jetons, E, budgets, demi_vie):
    L = len(jetons[0])
    couches = []
    for c in range(L):
        seq = par_couche(jetons, c)
        r, h_unif, h_pop, compte = reutilisation(seq, E)
        dmed, dmoy = distances(seq)
        n_cal = max(1, len(seq) // 10)
        res = {"couche": c, "reutilisation": r, "hasard_uniforme": h_unif, "hasard_popularite": h_pop,
               "distance_mediane": dmed, "distance_moyenne": dmoy,
               "experts_vus": sum(1 for x in compte if x), "caches": {}}
        trie = sorted(compte, reverse=True)
        tot = sum(compte)
        cumul, n95 = 0, 0
        for x in trie:
            cumul += x
            n95 += 1
            if cumul >= 0.95 * tot:
                break
        res["experts_pour_95pct"] = n95
        for C in budgets:
            res["caches"][str(C)] = {
                "lru": cache_lru(seq, C),
                "lfu": cache_lfu(seq, C, demi_vie),
                "statique_calibre": cache_statique(seq[n_cal:], C, seq[:n_cal]),
                "statique_oracle": cache_statique(seq, C, seq),
                "belady": cache_belady(seq, C),
            }
        couches.append(res)
    moy = lambda cle: statistics.fmean(x[cle] for x in couches)
    resume = {"reutilisation": moy("reutilisation"), "hasard_uniforme": moy("hasard_uniforme"),
              "hasard_popularite": moy("hasard_popularite"), "caches": {}}
    for C in budgets:
        resume["caches"][str(C)] = {p: statistics.fmean(x["caches"][str(C)][p] for x in couches)
                                    for p in ("lru", "lfu", "statique_calibre", "statique_oracle", "belady")}
    return {"couches": couches, "resume": resume, "E": E, "k": len(jetons[0][0]), "L": L, "T": len(jetons)}


# ---- témoins synthétiques ----

def synth_uniforme(T, L, E, k, rng):
    return [[rng.sample(range(E), k) for _ in range(L)] for _ in range(T)]


def synth_fige(T, L, E, k, rng):
    fixe = [rng.sample(range(E), k) for _ in range(L)]
    return [[list(f) for f in fixe] for _ in range(T)]


def synth_collant(T, L, E, k, rho, rng):
    etat = [rng.sample(range(E), k) for _ in range(L)]
    jetons = []
    for _ in range(T):
        for c in range(L):
            s = etat[c]
            for i in range(k):
                if rng.random() >= rho:
                    libres = [e for e in range(E) if e not in s]
                    s[i] = rng.choice(libres)
        jetons.append([list(s) for s in etat])
    return jetons


def temoins(casser, graine=20261015):
    rng = random.Random(graine)
    T, L, E, k = 4000, 4, 128, 8
    budgets = [8, 16, 32, 64]
    echecs, rapport = [], {}

    def tolerance_moyenne(p, n):
        # écart-type d'une moyenne de n proportions indépendantes de paramètre p
        return 4 * math.sqrt(p * (1 - p) / n)

    def prep(j):
        if casser:
            j = list(j)
            rng.shuffle(j)
        return j

    # T1
    m = mesurer(prep(synth_uniforme(T, L, E, k, rng)), E, budgets, 8.0)
    tol_r = tolerance_moyenne(k / E, (T - 1) * k * L)
    ok = abs(m["resume"]["reutilisation"] - k / E) <= tol_r
    rapport["T1_reutilisation"] = {"mesure": m["resume"]["reutilisation"], "attendu": k / E, "tolerance": tol_r, "reussi": ok}
    if not ok:
        echecs.append("T1 réutilisation")
    for C in budgets:
        tol = tolerance_moyenne(C / E, T * k * L)
        for p in ("lru", "lfu"):
            v = m["resume"]["caches"][str(C)][p]
            ok = abs(v - C / E) <= tol + k / (T * 1.0)  # + défauts de démarrage, au plus C/(T k) par expert
            rapport[f"T1_{p}_C{C}"] = {"mesure": v, "attendu": C / E, "tolerance": tol, "reussi": ok}
            if not ok:
                echecs.append(f"T1 {p} C={C}")
    # T2
    m = mesurer(prep(synth_fige(T, L, E, k, rng)), E, budgets, 8.0)
    ok = abs(m["resume"]["reutilisation"] - 1.0) < 1e-12
    rapport["T2_reutilisation"] = {"mesure": m["resume"]["reutilisation"], "attendu": 1.0, "reussi": ok}
    if not ok:
        echecs.append("T2 réutilisation")
    attendu = 1 - 1 / T  # un seul défaut de démarrage par expert
    for C in budgets:
        v = m["resume"]["caches"][str(C)]["lru"]
        ok = v >= attendu - 1e-9
        rapport[f"T2_lru_C{C}"] = {"mesure": v, "attendu_min": attendu, "reussi": ok}
        if not ok:
            echecs.append(f"T2 lru C={C}")
    # T3
    rho = 0.6
    m = mesurer(prep(synth_collant(T, L, E, k, rho, rng)), E, budgets, 8.0)
    attendu = rho
    # Correction de la première passe (2026-10-15) : l'attendu écrit d'abord, rho + (1-rho) k/E,
    # était faux (les places tirées à neuf évitent l'ensemble courant) ; mesuré 0,604 contre 0,625.
    # Tolérance : 4 sigma de part et d'autre, plus le terme positif borné (1-rho)^2 k/(E-k).
    sig4 = tolerance_moyenne(attendu, (T - 1) * k * L)
    eps = (1 - rho) ** 2 * k / (E - k)
    v = m["resume"]["reutilisation"]
    tol = sig4 + eps
    ok = attendu - sig4 <= v <= attendu + sig4 + eps
    rapport["T3_reutilisation"] = {"mesure": m["resume"]["reutilisation"], "attendu": attendu, "tolerance": tol, "reussi": ok}
    if not ok:
        echecs.append("T3 réutilisation (localité)")
    # T4 sur T3
    viol = 0
    for x in m["couches"]:
        for C in budgets:
            cc = x["caches"][str(C)]
            for p in ("lru", "lfu"):
                if cc[p] > cc["belady"] + 1e-12:
                    viol += 1
    rapport["T4_belady_borne"] = {"violations": viol, "reussi": viol == 0}
    if viol:
        echecs.append("T4 Belady dépassé")
    rapport["T3_caches"] = m["resume"]["caches"]
    return rapport, echecs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace")
    ap.add_argument("--budgets", default="4,8,16,32")
    ap.add_argument("--demi-vie", type=float, default=8.0)
    ap.add_argument("--temoins", action="store_true")
    ap.add_argument("--casser", action="store_true")
    ap.add_argument("--sortie")
    a = ap.parse_args()
    if a.temoins:
        rapport, echecs = temoins(a.casser)
        sortie = {"outil": "chargement_localite.py", "mode": "temoins", "casser": a.casser,
                  "rapport": rapport, "echecs": echecs,
                  "verdict": "INSTRUMENT VALIDE" if not echecs else "TEMOIN TOMBE"}
        for cle, v in rapport.items():
            if "reussi" in v:
                print(f"{cle:22s} {'ok ' if v['reussi'] else 'NON'} {json.dumps({x: round(y, 4) if isinstance(y, float) else y for x, y in v.items() if x != 'reussi'})}")
        print(sortie["verdict"], *echecs, sep="\n  ")
    else:
        jetons, E = lire_trace(a.trace)
        budgets = [int(x) for x in a.budgets.split(",")]
        sortie = {"outil": "chargement_localite.py", "trace": a.trace, **mesurer(jetons, E, budgets, a.demi_vie)}
        r = sortie["resume"]
        print(f"T={sortie['T']} L={sortie['L']} E={E} k={sortie['k']}")
        print(f"réutilisation adjacente {r['reutilisation']:.3f} (hasard uniforme {r['hasard_uniforme']:.3f}, "
              f"à popularité réelle {r['hasard_popularite']:.3f})")
        for C, v in r["caches"].items():
            print(f"C={C:>4s} " + " ".join(f"{p}={x:.3f}" for p, x in v.items()))
        echecs = []
    if a.sortie:
        os.makedirs(os.path.dirname(a.sortie) or ".", exist_ok=True)
        with open(a.sortie, "w", encoding="utf-8") as f:
            json.dump(sortie, f, ensure_ascii=False, indent=1)
    return 0 if not echecs else 2


if __name__ == "__main__":
    sys.exit(main())
