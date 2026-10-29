"""Localité des experts de gpt-oss sur traces réelles, et plafond de jetons/s qui en découle.

Entrées : les traces du traceur (outils/gptoss-routage/traceur.cpp), au format de
outils/chargement_localite.py (étude 04), un fichier par genre et par mode (lecture, generation),
et les octets lus dans l'en-tête des fichiers (outils/gptoss_octets.py).

Ce que l'outil calcule :
 1. Par couche, avec l'instrument de l'étude 04 (chargement_localite.mesurer, inchangé) :
    réutilisation d'un jeton au suivant, ses deux références de hasard (k/E et à popularité réelle),
    succès de LRU, LFU à demi-vie de 8 jetons, épinglage statique calibré (10 % premiers) et
    oracle, Belady, pour des budgets de 5 à 40 % des experts de chaque couche (C = arrondi de f·E).
    Seuls les budgets C >= k sont calculés par couche : pour gpt-oss-20b (E = 32, k = 4), 5 et 10 %
    donnent C < k, un cache par couche qui ne tient pas même les experts d'un jeton (et le LFU de
    l'étude 04 lève alors une erreur, faute d'expert à évincer : mesuré).
 2. Global, entre toutes les couches (ce que fait le cache d'experts de llama.cpp, un LRU unique par
    groupe de couches de même disposition, src/llama-moe-cache.cpp lu dans b11515) : le flux des
    accès (jeton t, couche l, expert e), dans l'ordre du calcul, passe dans un cache de N = arrondi
    de f·L·E emplacements ; mêmes politiques. Un emplacement = un expert d'une couche (tous les
    experts de gpt-oss ont la même taille, 13,25 Mo : succès en accès = succès en octets).
 3. Le plafond de jetons/s pour chaque succès h, avec les débits MESURÉS de fondations/01-machine.md :
    VRAM 251,3 Go/s (lecture par nuanceur), RAM -> carte 12,2 Go/s (DMA, au calme), disque
    2,82 Go/s (16 Mio, QD 1, BitLocker actif). Pour un jeton : A octets toujours lus (en VRAM),
    R = k·L·e octets routés, dont h·R servis par le cache et (1 - h)·R par l'étage suivant.
      - scénario « RAM » (le fichier tient en RAM, misses copiés par la PCIe) :
          t_série = (A + h·R)/B_vram + (1 - h)·R/B_pcie ; t_recouvert = max des deux termes ;
      - scénario « disque » (misses lus sur le disque puis copiés) :
          t_série = (A + h·R)/B_vram + (1 - h)·R·(1/B_disque + 1/B_pcie) ;
          t_recouvert = max((A + h·R)/B_vram, (1 - h)·R/B_pcie, (1 - h)·R/B_disque) ;
      - scénario « deux étages » (gpt-oss-120b : VRAM de capacité f_v, RAM jusqu'à f, disque) : LRU,
        Belady et l'épinglage statique sont des algorithmes à pile (le contenu à la capacité C est
        inclus dans celui à C' > C), donc h_v = h(f_v), h_r = h(f) - h(f_v), défauts 1 - h(f) :
          t_série = (A + h_v·R)/B_vram + h_r·R/B_pcie + (1 - h)·R·(1/B_disque + 1/B_pcie) ;
          t_recouvert = max((A + h_v·R)/B_vram, (1 - h_v)·R/B_pcie, (1 - h)·R/B_disque).
    Le calcul est supposé gratuit (la carte calcule un expert présent à la vitesse de la VRAM) :
    ce sont des plafonds, pas des prévisions.

Témoins (déclarés avant le calcul ; --temoins) :
  G1 ~~routage uniforme i.i.d. : LRU et LFU globaux = N/(L·E)~~ (attendu faux, voir temoins()) ;
     corrigé : G1a routage figé, LRU global à N = (L-1)·k -> 0, à L·k - 1 -> (k-1)/k·(1 - 1/T), à L·k -> 1 - 1/T ;
     G1b routage uniforme, épinglage statique calibré = N/(L·E) à 4 écarts-types ;
  G2 une seule couche : le cache global rend exactement le cache par couche de l'étude 04 (LRU et
     Belady, mêmes règles d'éviction) ;
  G3 Belady >= LRU, LFU sur chaque trace réelle et chaque budget (vérifié pendant la mesure) ;
  G4 cassure : l'ordre des jetons mélangé, la réutilisation adjacente doit retomber sur le hasard à
     popularité réelle (à 4 écarts-types près) et l'avantage de LRU sur l'épinglage oracle doit
     disparaître ; sur la trace en ordre, ce n'est pas le cas (preuve que l'instrument voit l'ordre).
  G5 second chemin : le taux de succès que publie llama.cpp pour son cache (même trace, même nombre
     d'emplacements, journal « llama_moe_cache: ubatch <= 8 ») contre notre LRU global simulé sur la
     trace de génération relevée dans la même exécution (--temoin-llama).

Usage :
  python -I gptoss_localite.py --temoins --sortie <dossier>
  python -I gptoss_localite.py --traces <dossier> --prefixe t120 --modele gpt-oss-120b-MXFP4.gguf
         --octets octets-gpt-oss.json --sortie <dossier> [--vram-libre-go 4.8 --ram-libre-go 11]
"""
import argparse
import csv
import glob
import heapq
import importlib.util
import json
import math
import os
import random
import statistics
import sys
from collections import OrderedDict

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import chargement_localite as cl  # noqa: E402  (instrument de l'étude 04, inchangé)

# Débits mesurés (fondations/01-machine.md, § 0), en octets par seconde
B_VRAM = 251.3e9
B_PCIE = 12.2e9
B_DISQUE = 2.82e9
BUDGETS = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]
POLITIQUES = ("lru", "lfu", "statique_calibre", "statique_oracle", "belady")


# ---------- cache global (entre couches) ----------

def flux(jetons, E):
    """Groupes d'accès dans l'ordre du calcul : un groupe = les k experts d'un (jeton, couche)."""
    return [[l * E + e for e in couche] for t in jetons for l, couche in enumerate(t)]


def g_lru(groupes, N):
    cache, succes, total = OrderedDict(), 0, 0
    for g in groupes:
        for x in g:
            total += 1
            if x in cache:
                succes += 1
                cache.move_to_end(x)
            else:
                cache[x] = True
        while len(cache) > N:
            # le plus ancien n'est jamais du groupe courant (ses experts viennent d'aller en fin), N >= k
            cache.popitem(last=False)
    return succes / total


def g_lru_llama(groupes, N):
    """Réplique de la règle de plan() du cache de llama.cpp b11515 (src/llama-moe-cache.cpp, lu,
    rien copié) : les succès sont « touchés » d'abord, dans l'ordre du score ; puis les défauts,
    triés par numéro d'expert croissant, prennent chacun l'emplacement le moins récemment utilisé.
    Rend (succès, accès). Sert au témoin G5 ; g_lru diffère seulement par l'ordre des défauts
    d'un même groupe dans la liste (4 et 5 succès d'écart sur 98 304 et 24 576 accès, mesuré)."""
    cache, succes, total = OrderedDict(), 0, 0
    for g in groupes:
        total += len(g)
        for x in g:
            if x in cache:
                cache.move_to_end(x)
                succes += 1
        for x in sorted(g):
            if x not in cache:
                if len(cache) >= N:
                    cache.popitem(last=False)
                cache[x] = True
    return succes, total


def g_lfu(groupes, N, groupes_par_jeton, demi_vie=8.0):
    """LFU à compteurs décroissants (demi-vie en jetons). Entre deux mises à jour, deux scores
    décroissent du même facteur : leur ordre ne change pas. On range donc log(score) - t·log(d)
    (constant dans le temps) dans un tas à invalidation paresseuse ; départage par ancienneté."""
    ld = math.log(0.5) / demi_vie
    cle, vu = {}, {}
    cache, tas, succes, total = set(), [], 0, 0
    for i, g in enumerate(groupes):
        t = i // groupes_par_jeton
        for x in g:
            total += 1
            ancien = cle.get(x)
            v = 1.0 if ancien is None else math.exp(ancien + t * ld) + 1.0  # valeur effective à t, + 1
            cle[x] = math.log(v) - t * ld
            vu[x] = i
            if x in cache:
                succes += 1
            else:
                cache.add(x)
            heapq.heappush(tas, (cle[x], vu[x], x))
        dans_g = set(g)
        mis_de_cote = []
        while len(cache) > N:
            c, v, x = heapq.heappop(tas)
            if x not in cache or cle[x] != c or vu[x] != v:
                continue  # entrée périmée
            if x in dans_g:
                mis_de_cote.append((c, v, x))
                continue
            cache.remove(x)
        for e in mis_de_cote:
            heapq.heappush(tas, e)
    return succes / total


def g_statique(groupes, N, calibration):
    compte = {}
    for g in calibration:
        for x in g:
            compte[x] = compte.get(x, 0) + 1
    epingles = set(sorted(compte, key=lambda x: (-compte[x], x))[:N])
    total = sum(len(g) for g in groupes)
    return sum(1 for g in groupes for x in g if x in epingles) / total


def g_belady(groupes, N):
    prochain_g = [None] * len(groupes)
    suivant = {}
    for i in range(len(groupes) - 1, -1, -1):
        prochain_g[i] = [suivant.get(x, math.inf) for x in groupes[i]]
        for x in groupes[i]:
            suivant[x] = i
    cache, tas, succes, total = {}, [], 0, 0
    for i, g in enumerate(groupes):
        for x, p in zip(g, prochain_g[i]):
            total += 1
            if x in cache:
                succes += 1
            cache[x] = p
            heapq.heappush(tas, (-p, x))
        dans_g = set(g)
        mis_de_cote = []
        while len(cache) > N:
            mp, x = heapq.heappop(tas)
            if x not in cache or cache[x] != -mp:
                continue
            if x in dans_g:
                mis_de_cote.append((mp, x))
                continue
            del cache[x]
        for e in mis_de_cote:
            heapq.heappush(tas, e)
    return succes / total


def mesurer_global(jetons, E, fractions):
    L = len(jetons[0])
    k = len(jetons[0][0])
    groupes = flux(jetons, E)
    n_cal = max(1, len(jetons) // 10) * L
    res = {}
    for f in fractions:
        N = max(k, round(f * L * E))
        r = {"emplacements": N,
             "lru": g_lru(groupes, N),
             "lfu": g_lfu(groupes, N, L),
             "statique_calibre": g_statique(groupes[n_cal:], N, groupes[:n_cal]),
             "statique_oracle": g_statique(groupes, N, groupes),
             "belady": g_belady(groupes, N)}
        if r["lru"] > r["belady"] + 1e-12 or r["lfu"] > r["belady"] + 1e-12:
            raise SystemExit(f"G3 tombé : Belady dépassé à f = {f}")
        res[f"{f:.2f}"] = r
    return res


# ---------- plafonds ----------

def plafonds(h, A, R, hv=None):
    """jetons/s (série, recouvert) pour les trois scénarios."""
    out = {}
    tv = (A + h * R) / B_VRAM
    out["ram_serie"] = 1 / (tv + (1 - h) * R / B_PCIE)
    out["ram_recouvert"] = 1 / max(tv, (1 - h) * R / B_PCIE)
    out["disque_serie"] = 1 / (tv + (1 - h) * R * (1 / B_DISQUE + 1 / B_PCIE))
    out["disque_recouvert"] = 1 / max(tv, (1 - h) * R / B_PCIE, (1 - h) * R / B_DISQUE)
    if hv is not None:
        hr = h - hv
        t1 = (A + hv * R) / B_VRAM
        out["deux_etages_serie"] = 1 / (t1 + hr * R / B_PCIE + (1 - h) * R * (1 / B_DISQUE + 1 / B_PCIE))
        out["deux_etages_recouvert"] = 1 / max(t1, (1 - hv) * R / B_PCIE, (1 - h) * R / B_DISQUE)
    return out


# ---------- témoins ----------

def temoins(sortie):
    rng = random.Random(20261015)
    rapport, echecs = {}, []
    T, L, E, k = 4000, 4, 32, 4
    # G1, première passe (2026-10-15), FAUSSE : « sous routage uniforme i.i.d., LRU et LFU globaux
    # valent N/(L·E) ». Mesuré : 0,032 contre 0,102 à f = 10 %. L'erreur était dans l'attendu, pas
    # dans le code : le flux global est cyclique dans les couches (couche 0, 1, …, L-1, puis 0) ;
    # un expert de la couche l ne revient qu'après L·k accès des autres couches, et un LRU de
    # N < L·k emplacements l'a toujours évincé avant (pathologie classique de LRU sur une boucle).
    # Le résultat « C/E » de l'étude 04 vaut pour un cache par couche, pas pour un cache partagé.
    # Témoins corrigés, chacun avec une réponse exacte :
    #  G1a routage figé (chaque couche garde ses k experts), boucle de L·k clés. Le cache juge les k
    #      accès d'un (jeton, couche) contre son contenu AVANT d'évincer (règle de plan() dans
    #      src/llama-moe-cache.cpp : les k experts doivent être présents ensemble). Donc :
    #      N = (L-1)·k -> 0 succès exactement ; N = L·k - 1 -> (k-1)/k · (1 - 1/T) (le cache tient
    #      les 3 derniers accès de la couche qui revient) ; N = L·k -> 1 - 1/T.
    #      (Deuxième erreur de cette passe, dite : j'avais d'abord écrit 0 pour N = L·k - 1, vrai pour
    #      un LRU qui évince à chaque accès, faux pour un LRU qui évince après le groupe ; mesuré
    #      0,74981 = 0,75 · (1 - 1/4000).)
    #  G1b routage uniforme i.i.d. : un épinglage statique calibré (sur les 10 % premiers, évalué sur
    #      le reste, donc sans biais de sélection) vaut N/(L·E), à 4 écarts-types près.
    fige = [[list(range(l, l + k)) for l in range(L)] for _ in range(T)]
    gf = flux(fige, E)
    for N, attendu in (((L - 1) * k, 0.0), (L * k - 1, (k - 1) / k * (1 - 1 / T)), (L * k, 1 - 1 / T)):
        v = g_lru(gf, N)
        ok = abs(v - attendu) < 1e-12
        rapport[f"G1a_lru_N{N}"] = {"mesure": v, "attendu": attendu, "reussi": ok}
        if not ok:
            echecs.append(f"G1a lru N={N}")
    jetons = [[rng.sample(range(E), k) for _ in range(L)] for _ in range(T)]
    groupes = flux(jetons, E)
    n_cal = (T // 10) * L
    for f in (0.10, 0.25, 0.40):
        N = round(f * L * E)
        n = (T - T // 10) * L * k
        p = N / (L * E)
        tol = 4 * math.sqrt(p * (1 - p) / n)
        v = g_statique(groupes[n_cal:], N, groupes[:n_cal])
        ok = abs(v - p) <= tol
        rapport[f"G1b_statique_f{f:.2f}"] = {"mesure": v, "attendu": p, "tolerance": tol, "reussi": ok}
        if not ok:
            echecs.append(f"G1b statique f={f}")
        # référence sans localité de LRU et LFU globaux (publiée, pas un témoin)
        rapport[f"ref_uniforme_lru_f{f:.2f}"] = {"mesure": g_lru(groupes, N), "reussi": True}
        rapport[f"ref_uniforme_lfu_f{f:.2f}"] = {"mesure": g_lfu(groupes, N, L), "reussi": True}
    # G2 : une couche, global == par couche (étude 04)
    j1 = [[t[0]] for t in cl.synth_collant(3000, 1, 64, 4, 0.6, rng)]
    g1 = flux(j1, 64)
    seq = cl.par_couche(j1, 0)
    for C in (8, 16, 32):
        a, b = g_lru(g1, C), cl.cache_lru(seq, C)
        c, d = g_belady(g1, C), cl.cache_belady(seq, C)
        ok = abs(a - b) < 1e-12 and abs(c - d) < 1e-12
        rapport[f"G2_C{C}"] = {"lru_global": a, "lru_couche": b, "belady_global": c, "belady_couche": d, "reussi": ok}
        if not ok:
            echecs.append(f"G2 C={C}")
    sortie_j = {"outil": "gptoss_localite.py", "mode": "temoins", "rapport": rapport, "echecs": echecs,
                "verdict": "INSTRUMENT VALIDE" if not echecs else "TEMOIN TOMBE"}
    for c, v in rapport.items():
        print(f"{c:18s} {'ok ' if v['reussi'] else 'NON'} " + json.dumps({x: round(y, 5) if isinstance(y, float) else y for x, y in v.items() if x != "reussi"}))
    print(sortie_j["verdict"], *echecs)
    os.makedirs(sortie, exist_ok=True)
    json.dump(sortie_j, open(os.path.join(sortie, "temoins-global.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 0 if not echecs else 2


# ---------- programme ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--temoins", action="store_true")
    ap.add_argument("--traces")
    ap.add_argument("--prefixe")
    ap.add_argument("--modele")
    ap.add_argument("--octets")
    ap.add_argument("--sortie", required=True)
    ap.add_argument("--vram-libre-go", type=float, default=None,
                    help="capacité de la VRAM pour le cache d'experts (scénario deux étages)")
    ap.add_argument("--ram-libre-go", type=float, default=None)
    ap.add_argument("--casser", action="store_true", help="mélange l'ordre des jetons (témoin G4)")
    ap.add_argument("--casser-seuil", action="store_true",
                    help="cassure du témoin de la Proposition 1 : attend 0 succès à (L-1)·k + 1 emplacements")
    ap.add_argument("--g5", action="append", default=[],
                    help="témoin G5 : 'nom:emplacements:succès publiés par llama.cpp:trace1,trace2,…'")
    a = ap.parse_args()
    if a.temoins:
        return temoins(a.sortie)
    if a.g5:
        rapport, echec = {}, False
        for spec in a.g5:
            nom, N, attendu, fichiers = spec.split(":", 3)
            jetons, E = [], None
            for f in fichiers.split(","):
                j, E = cl.lire_trace(f)
                jetons += j
            h, n = g_lru_llama(flux(jetons, E), int(N))
            h2 = g_lru(flux(jetons, E), int(N)) * n
            ok = h == int(attendu)
            echec |= not ok
            rapport[nom] = {"emplacements": int(N), "succes_llama": int(attendu), "succes_simules": h,
                            "succes_g_lru": round(h2), "acces": n, "taux_llama": int(attendu) / n, "reussi": ok}
            print(nom, rapport[nom])
        os.makedirs(a.sortie, exist_ok=True)
        json.dump(rapport, open(os.path.join(a.sortie, "temoin-g5.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return 2 if echec else 0
    oct_ = json.load(open(a.octets, encoding="utf-8"))[a.modele]
    A, R, E, Lc, k = oct_["toujours_lus_octets"], oct_["routes_par_jeton_octets"], oct_["experts"], oct_["couches"], oct_["k"]
    os.makedirs(a.sortie, exist_ok=True)
    fichiers = sorted(glob.glob(os.path.join(a.traces, f"{a.prefixe}.*.trace")))
    traces = {}
    for f in fichiers:
        nom = os.path.basename(f)[len(a.prefixe) + 1:-len(".trace")]  # genre.mode
        jetons, E_ = cl.lire_trace(f)
        assert E_ == E and len(jetons[0]) == Lc and len(jetons[0][0]) == k, f
        traces[nom] = jetons
    lectures = [n for n in traces if n.endswith(".lecture")]
    traces["tous.lecture"] = [t for n in sorted(lectures) for t in traces[n]]
    gens = [n for n in traces if n.endswith(".generation")]
    if gens:
        traces["tous.generation"] = [t for n in sorted(gens) for t in traces[n]]
    rng = random.Random(20261015)
    if a.casser:
        for n in traces:
            traces[n] = list(traces[n])
            rng.shuffle(traces[n])
    suffixe = "-casse" if a.casser else ""
    bilan = {"modele": a.modele, "A_octets": A, "R_octets": R, "E": E, "L": Lc, "k": k, "casser": a.casser,
             "debits_o_s": {"vram": B_VRAM, "pcie": B_PCIE, "disque": B_DISQUE}, "traces": {}}
    lignes_courbes, lignes_couches, lignes_plafonds = [], [], []
    for nom, jetons in traces.items():
        T = len(jetons)
        # C < k : l'instrument de l'étude 04 ne le permet pas (son LFU n'a plus de candidat à évincer
        # quand le cache ne contient que les experts du jeton courant : ValueError, mesuré sur 20b) ;
        # un cache par couche plus petit que k n'a de toute façon pas de sens physique. Ces budgets
        # ne sont calculés qu'en portée globale.
        budgets_c = sorted({round(f * E) for f in BUDGETS if round(f * E) >= k})
        mc = cl.mesurer(jetons, E, budgets_c, 8.0)
        mg = mesurer_global(jetons, E, BUDGETS)
        # Proposition 1 de mesures/gpt-oss.md (§ 7), vérifiée aux capacités exactes du seuil (ajout du
        # 2026-10-15 : sur 120b, (L-1)·k = 140 emplacements, 3,04 %, sous le plus petit budget étudié) :
        # N = (L-1)·k -> 0 exactement ; N >= L·k -> au moins r̄ (réutilisation adjacente sur t >= 1,
        # rapportée aux accès des jetons t >= 1 ; sur tous les accès, au moins r̄·(T-1)/T)
        gs = flux(jetons, E)
        r_moy = mc["resume"]["reutilisation"]
        seuil = {str(N): g_lru(gs, N) for N in ((Lc - 1) * k, Lc * k - 1, Lc * k, Lc * k + 1)}
        n_zero = (Lc - 1) * k + (1 if a.casser_seuil else 0)  # cassure : un emplacement de plus
        h_zero = seuil.get(str(n_zero), None)
        if h_zero is None:
            h_zero = g_lru(gs, n_zero)
        if h_zero != 0.0 or seuil[str(Lc * k)] < r_moy * (T - 1) / T - 1e-12:
            raise SystemExit(f"Proposition 1 tombée sur {nom} : LRU({n_zero}) = {h_zero}, "
                             f"LRU({Lc * k}) = {seuil[str(Lc * k)]} pour une borne {r_moy * (T - 1) / T}")
        # G4 : hasard à popularité réelle, et son écart-type pour la moyenne des réutilisations
        r_moy = mc["resume"]["reutilisation"]
        hp = mc["resume"]["hasard_popularite"]
        sig = math.sqrt(max(hp * (1 - hp), 1e-12) / ((T - 1) * k * Lc))
        bilan["traces"][nom] = {"jetons": T, "par_couche": {"resume": mc["resume"], "budgets_C": budgets_c},
                                "global": mg, "seuil_lru_partage": seuil,
                                "seuil_borne_ii": r_moy * (T - 1) / T,
                                "reutilisation": r_moy, "hasard_uniforme": k / E,
                                "hasard_popularite": hp, "ecart_type_hasard": sig,
                                "ecart_au_hasard_en_sigma": (r_moy - hp) / sig,
                                "couches": [{x: c[x] for x in ("couche", "reutilisation", "hasard_popularite",
                                                               "distance_mediane", "distance_moyenne",
                                                               "experts_vus", "experts_pour_95pct")}
                                            for c in mc["couches"]]}
        for c in mc["couches"]:
            lignes_couches.append({"trace": nom, "couche": c["couche"], "reutilisation": round(c["reutilisation"], 5),
                                   "hasard_uniforme": round(k / E, 5), "hasard_popularite": round(c["hasard_popularite"], 5),
                                   "distance_mediane": c["distance_mediane"], "experts_pour_95pct": c["experts_pour_95pct"]})
        for f in BUDGETS:
            C = round(f * E)
            for p in POLITIQUES:
                if C >= k:
                        lignes_courbes.append({"trace": nom, "portee": "couche", "budget_pct": round(100 * f), "capacite": C,
                                           "politique": p, "succes": round(mc["resume"]["caches"][str(C)][p], 5)})
                lignes_courbes.append({"trace": nom, "portee": "globale", "budget_pct": round(100 * f),
                                       "capacite": mg[f"{f:.2f}"]["emplacements"], "politique": p,
                                       "succes": round(mg[f"{f:.2f}"][p], 5)})
        # plafonds sur la trace « tous » (lecture et génération), cache global
        if nom.startswith("tous."):
            fv = None
            if a.vram_libre_go:
                fv = min(1.0, a.vram_libre_go * 1e9 / oct_["experts_total_octets"])
            # h(f_v) de chaque politique, calculé une fois (avant le 2026-10-15 : recalculé pour chaque
            # budget et chaque politique, 24 fois le même résultat)
            jg = mesurer_global(jetons, E, [fv])[f"{fv:.2f}"] if fv is not None else None
            if jg is not None:
                bilan.setdefault("succes_a_la_vram", {})[nom] = jg
            for f in BUDGETS:
                for p in ("lru", "lfu", "statique_oracle", "belady"):
                    h = mg[f"{f:.2f}"][p]
                    hv = None
                    if fv is not None and fv < f and p in ("lru", "belady", "statique_oracle"):
                        # h(f_v) par la même politique, à la capacité de la VRAM (algorithmes à pile)
                        hv = jg[p]
                        if hv > h + 1e-12:
                            raise SystemExit(f"propriété de pile démentie : {p}, h({fv:.4f}) = {hv} > h({f}) = {h}")
                    pl = plafonds(h, A, R, hv)
                    lignes_plafonds.append({"trace": nom, "budget_pct": round(100 * f), "politique": p,
                                            "succes": round(h, 5), "succes_vram": None if hv is None else round(hv, 5),
                                            **{x: round(y, 3) for x, y in pl.items()}})
            pl0 = plafonds(0.0, A, R)
            bilan.setdefault("sans_cache", pl0)
            if fv is not None:
                bilan["fraction_vram"] = fv
        print(f"[{nom}] T={T} réutilisation {r_moy:.3f} (uniforme {k/E:.3f}, popularité {hp:.3f}, "
              f"{(r_moy-hp)/sig:+.1f} sigma) ; global LRU 10/20/40 % : "
              + " / ".join(f"{mg[f'{f:.2f}']['lru']:.3f}" for f in (0.10, 0.20, 0.40))
              + " ; Belady : " + " / ".join(f"{mg[f'{f:.2f}']['belady']:.3f}" for f in (0.10, 0.20, 0.40))
              + " ; seuil LRU " + " ".join(f"N={n}:{v:.4f}" for n, v in seuil.items())
              + f" (borne {r_moy * (T - 1) / T:.4f})", flush=True)
    base = a.modele.replace("-MXFP4.gguf", "")
    json.dump(bilan, open(os.path.join(a.sortie, f"localite-{base}{suffixe}.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    for nomf, lignes in ((f"courbes-{base}{suffixe}.csv", lignes_courbes), (f"couches-{base}{suffixe}.csv", lignes_couches),
                         (f"plafonds-{base}{suffixe}.csv", lignes_plafonds)):
        if not lignes:
            continue
        with open(os.path.join(a.sortie, nomf), "w", newline="", encoding="utf-8") as f:
            # union ordonnée des colonnes : le scénario « deux étages » n'existe que pour les budgets
            # au-dessus de la capacité de la VRAM (défaut trouvé sur 120b le 2026-10-15 : la première
            # ligne, à 5 %, n'avait pas ces colonnes et l'écriture tombait)
            champs = list(dict.fromkeys(c for ligne in lignes for c in ligne))
            w = csv.DictWriter(f, fieldnames=champs)
            w.writeheader()
            w.writerows(lignes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
