"""Éclaireur Terre et cosmos : deux politiques de cache d'experts inspirées de la Terre, jugées sur les
traces de routage commitées (seuils : genome/mimetisme/terre_cosmos/seuil-declare.md, commité avant).

M-A  allocation des emplacements entre couches par utilité marginale (programmation dynamique sur les
     courbes de succès par couche, calculées sur les AUTRES genres), un LRU par couche.
M-B  éviction par score de réutilisation à noyau en loi de puissance (Omori-Utsu) :
     S(x, t) = sum_i (t - t_i + c)^(-p) sur les M derniers accès de x, t en jetons fractionnaires.

Les politiques de base (LRU, LFU, Belady) sont celles de outils/gptoss_localite.py, importées telles
quelles. Un cache global : un groupe d'accès = les k experts d'un (jeton, couche), dans l'ordre du calcul.

Usage :
  python -I -X utf8 cache_terre.py mesure <20b|120b> <dossier_traces> <sortie_dir> [--melange]
  python -I -X utf8 cache_terre.py temoins <dossier_traces_20b> <sortie_dir>
  python -I -X utf8 cache_terre.py gaps <20b|120b> <dossier_traces> <sortie_dir>
"""
import json
import math
import os
import random
import sys
import time

os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np  # noqa: E402

ICI = os.path.dirname(os.path.abspath(__file__))
OUTILS = os.path.abspath(os.path.join(ICI, "..", ".."))
sys.path.insert(0, OUTILS)
import chargement_localite as cl  # noqa: E402
import gptoss_localite as gl  # noqa: E402

GENRES = ["code", "dialogue", "prose-en", "prose-fr"]
BUDGETS = [0.10, 0.15, 0.20, 0.30]
M_HIST = 32
GRILLE_B = [(p, c) for p in (0.5, 1.0, 1.5) for c in (0.5, 2.0)]
GRILLE_LFU = [2, 4, 8, 16, 32]
if os.environ.get("OMORI") == "reduit":  # 120b : le noyau en loi de puissance coûte 4 min par cas ; déclaré dans le journal
    GRILLE_B = [(1.0, 2.0), (0.5, 2.0)]
    BUDGETS_B = [0.20, 0.30]
else:
    BUDGETS_B = BUDGETS


def charger(prefixe, dossier, genre, melange=False, graine=20261026):
    jetons, E = cl.lire_trace(os.path.join(dossier, f"{prefixe}.{genre}.lecture.trace"))
    if melange:
        random.Random(graine).shuffle(jetons)
    return jetons, E


# ---------- M-B : score en loi de puissance ----------

def g_omori(groupes, N, L, E, p, c, M=M_HIST):
    """Cache global, éviction du plus petit score en loi de puissance. Rend (succès, total)."""
    n_items = L * E
    hist = np.full((n_items, M), -1e18)
    ptr = np.zeros(n_items, dtype=np.int64)
    dernier = np.full(n_items, -1, dtype=np.int64)
    pos = {}
    membres = np.zeros(N + 16, dtype=np.int64)
    taille = 0
    succes = total = 0
    for i, g in enumerate(groupes):
        t = i / L
        for x in g:
            total += 1
            if x in pos:
                succes += 1
            else:
                pos[x] = taille
                membres[taille] = x
                taille += 1
            hist[x, ptr[x] % M] = t
            ptr[x] += 1
            dernier[x] = i
        exces = taille - N
        if exces > 0:
            m = membres[:taille]
            h = hist[m]
            delta = np.where(h > -1e17, t - h + c, np.inf)  # entrées vides : score 0
            sc = np.power(delta, -p).sum(axis=1)
            for x in g:  # le groupe courant n'est jamais évincé
                sc[pos[x]] = np.inf
            ordre = np.lexsort((m, dernier[m], sc))[:exces]
            ev = sorted(int(j) for j in ordre)
            for j in reversed(ev):
                x = int(membres[j])
                del pos[x]
                taille -= 1
                if j != taille:
                    y = int(membres[taille])
                    membres[j] = y
                    pos[y] = j
    return succes, total


def g_omori_pur(groupes, N, L, E, p, c, M=M_HIST):
    """Second chemin (T4) : Python pur, boucles explicites, mêmes règles."""
    from collections import deque
    hist = {}
    dernier = {}
    cache = set()
    succes = total = 0
    for i, g in enumerate(groupes):
        t = i / L
        for x in g:
            total += 1
            if x in cache:
                succes += 1
            else:
                cache.add(x)
            hist.setdefault(x, deque(maxlen=M)).append(t)
            dernier[x] = i
        gs = set(g)
        while len(cache) > N:
            meilleur = None
            for y in cache:
                if y in gs:
                    continue
                s = 0.0
                for ty in hist[y]:
                    s += (t - ty + c) ** (-p)
                cle = (s, dernier[y], y)
                if meilleur is None or cle < meilleur:
                    meilleur = cle
            cache.remove(meilleur[2])
    return succes, total


# ---------- M-A : allocation entre couches ----------

def succes_par_couche(jetons, L, k, E):
    """hits_l[n] pour n dans {0} + [k..E] : LRU par couche à n emplacements (n = 0 : traversée sans cache)."""
    res = np.zeros((L, E + 1), dtype=np.int64)
    for l in range(L):
        seq = [t[l] for t in jetons]
        for n in range(k, E + 1):
            res[l, n] = _lru_couche(seq, n)
    return res


def _lru_couche(seq, n):
    from collections import OrderedDict
    cache, h = OrderedDict(), 0
    for g in seq:
        for x in g:
            if x in cache:
                h += 1
                cache.move_to_end(x)
            else:
                cache[x] = True
        while len(cache) > n:
            cache.popitem(last=False)
    return h


def allocation_dp(courbes, N, k, E):
    """Maximise la somme des succès, somme des n_l <= N, n_l dans {0} + [k..E]. Rend la liste des n_l."""
    L = courbes.shape[0]
    options = [0] + list(range(k, E + 1))
    NEG = -1
    best = np.full(N + 1, NEG, dtype=np.int64)
    best[0] = 0
    choix = []
    for l in range(L):
        nouv = np.full(N + 1, NEG, dtype=np.int64)
        ch = np.zeros(N + 1, dtype=np.int64)
        for n in options:
            if n > N:
                break
            gain = courbes[l, n]
            cand = np.full(N + 1, NEG, dtype=np.int64)
            cand[n:] = np.where(best[:N + 1 - n] >= 0, best[:N + 1 - n] + gain, NEG)
            mieux = cand > nouv
            nouv = np.where(mieux, cand, nouv)
            ch = np.where(mieux, n, ch)
        best = nouv
        choix.append(ch)
    b = int(np.argmax(best))
    alloc = [0] * L
    for l in range(L - 1, -1, -1):
        n = int(choix[l][b])
        alloc[l] = n
        b -= n
    return alloc


def lru_par_couche(jetons, L, alloc):
    h = tot = 0
    for l in range(L):
        seq = [t[l] for t in jetons]
        tot += sum(len(g) for g in seq)
        if alloc[l] == 0:
            continue
        h += _lru_couche(seq, alloc[l])
    return h, tot


# ---------- mesure ----------

def mesure(prefixe, dossier, sortie, melange):
    os.makedirs(sortie, exist_ok=True)
    data = {g: charger(prefixe, dossier, g, melange) for g in GENRES}
    E = data[GENRES[0]][1]
    L = len(data[GENRES[0]][0][0])
    k = len(data[GENRES[0]][0][0][0])
    res = {"modele": prefixe, "melange": melange, "L": L, "E": E, "k": k, "genres": {}}
    t0 = time.time()
    # courbes par couche, par genre (pour M-A)
    courbes = {g: succes_par_couche(data[g][0], L, k, E) for g in GENRES}
    print(f"courbes par couche : {time.time() - t0:.0f} s", flush=True)
    flux = {g: gl.flux(data[g][0], E) for g in GENRES}
    for f in BUDGETS:
        N = max(k, round(f * L * E))
        brut = {g: {} for g in GENRES}
        for g in GENRES:
            gr = flux[g]
            b = brut[g]
            b["lru"] = gl.g_lru(gr, N)
            b["belady"] = gl.g_belady(gr, N)
            for hl in GRILLE_LFU:
                b[f"lfu{hl}"] = gl.g_lfu(gr, N, L, float(hl))
            if f in BUDGETS_B:
                for (p, c) in GRILLE_B:
                    s, tot = g_omori(gr, N, L, E, p, c)
                    b[f"omori_p{p}_c{c}"] = s / tot
            print(f"f={f} {g} : {time.time() - t0:.0f} s", flush=True)
        # M-A : allocation réglée sur les trois autres genres
        for g in GENRES:
            autres = [x for x in GENRES if x != g]
            cs = sum(courbes[x] for x in autres)
            alloc = allocation_dp(cs, N, k, E)
            h, tot = lru_par_couche(data[g][0], L, alloc)
            brut[g]["A_alloc"] = alloc
            brut[g]["A"] = h / tot
            # témoin T5 : allocation uniforme par le même code (si faisable)
            if N >= L * k:
                n_u = N // L
                alloc_u = [n_u] * L
                hu, _ = lru_par_couche(data[g][0], L, alloc_u)
                brut[g]["uniforme"] = hu / tot
        res.setdefault("budgets", {})[f"{f:.2f}"] = {"N": N, "brut": brut}
    # sélection par validation croisée par genre
    synth = {}
    for fk, bl in res["budgets"].items():
        brut = bl["brut"]
        lignes = {}
        for g in GENRES:
            autres = [x for x in GENRES if x != g]
            # M-B : meilleur (p, c) sur les autres genres
            cles_b = [f"omori_p{p}_c{c}" for (p, c) in GRILLE_B] if float(fk) in BUDGETS_B else []
            cb = max(cles_b, key=lambda cle: sum(brut[x][cle] for x in autres)) if cles_b else None
            cl_ = max([f"lfu{hl}" for hl in GRILLE_LFU], key=lambda cle: sum(brut[x][cle] for x in autres))
            ligne = {"B_choix": cb, "B": (brut[g][cb] if cb else None), "lfu_choix": cl_, "lfu_regle": brut[g][cl_],
                     "lru": brut[g]["lru"], "belady": brut[g]["belady"], "A": brut[g]["A"],
                     "A_alloc": brut[g]["A_alloc"], "lfu8": brut[g]["lfu8"]}
            if "uniforme" in brut[g]:
                ligne["uniforme"] = brut[g]["uniforme"]
            base_A = [brut[g]["lru"], ligne["lfu_regle"]] + ([brut[g]["uniforme"]] if "uniforme" in brut[g] else [])
            ligne["meilleur_base_A"] = max(base_A)
            ligne["dB"] = (ligne["B"] - ligne["lfu_regle"]) if cb else None
            ligne["dA"] = ligne["A"] - ligne["meilleur_base_A"]
            lignes[g] = ligne
        moy = lambda cle: sum(lignes[g][cle] for g in GENRES) / 4
        a_b = float(fk) in BUDGETS_B
        synth[fk] = {"N": bl["N"], "genres": lignes,
                     "moy_dB": moy("dB") if a_b else None, "moy_dA": moy("dA"),
                     "pos_dB": sum(1 for g in GENRES if a_b and lignes[g]["dB"] > 0),
                     "pos_dA": sum(1 for g in GENRES if lignes[g]["dA"] > 0),
                     "moy_belady": moy("belady"), "moy_lfu": moy("lfu_regle"), "moy_lru": moy("lru"),
                     "moy_A": moy("A"), "moy_B": moy("B") if a_b else None}
    res["synthese"] = synth
    nom = f"mesure-{prefixe}{'-melange' if melange else ''}.json"
    with open(os.path.join(sortie, nom), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    for fk, s in synth.items():
        print(f"f={fk} N={s['N']} : LRU {s['moy_lru']:.4f} LFU réglée {s['moy_lfu']:.4f} "
              f"B {s['moy_B'] if s['moy_B'] is None else round(s['moy_B'],4)} (dB {None if s['moy_dB'] is None else round(s['moy_dB']*100,2)} pt, {s['pos_dB']}/4) "
              f"A {s['moy_A']:.4f} (dA {s['moy_dA']*100:+.2f} pt, {s['pos_dA']}/4) Belady {s['moy_belady']:.4f}")
    print(f"total {time.time() - t0:.0f} s")


def temoins(dossier, sortie):
    os.makedirs(sortie, exist_ok=True)
    out = {}
    # T1 : reproduction des valeurs publiées sur la trace quatre genres en ordre
    jetons, E = [], None
    for g in GENRES:
        j, E = charger("t20b", dossier, g)
        jetons += j
    L, k = len(jetons[0]), len(jetons[0][0])
    gr = gl.flux(jetons, E)
    N = max(k, round(0.20 * L * E))
    t1 = {"N": N, "lru": gl.g_lru(gr, N), "lfu8": gl.g_lfu(gr, N, L, 8.0), "belady": gl.g_belady(gr, N)}
    attendu = {"lru": 0.601, "lfu8": 0.684, "belady": 0.814}
    t1["ecart"] = {c: t1[c] - attendu[c] for c in attendu}
    t1["tient"] = all(abs(v) <= 0.002 for v in t1["ecart"].values())
    out["T1"] = t1
    print("T1", t1, flush=True)
    # T4 : second chemin de M-B sur le genre code, f = 0,20
    jc, _ = charger("t20b", dossier, "code")
    grc = gl.flux(jc, E)
    t0 = time.time()
    a = g_omori(grc, N, L, E, 1.0, 0.5)
    b = g_omori_pur(grc, N, L, E, 1.0, 0.5)
    out["T4"] = {"numpy": a, "pur": b, "ecart_succes": a[0] - b[0], "secondes": time.time() - t0,
                 "tient": abs(a[0] - b[0]) <= 2 and a[1] == b[1]}
    print("T4", out["T4"], flush=True)
    # T4 cassure : un score qui oublie le noyau (p = 0, tout score égal) doit s'écarter
    c = g_omori(grc, N, L, E, 0.0, 0.5)
    out["T4_cassure_p0"] = {"succes_p0": c[0], "succes_p1": a[0], "differe": c[0] != a[0]}
    print("T4 cassure", out["T4_cassure_p0"], flush=True)
    # T5 : DP restreint à l'uniforme redonne l'uniforme (somme des succès par couche à n_u)
    cs = succes_par_couche(jc, L, k, E)
    n_u = N // L
    hu, _ = lru_par_couche(jc, L, [n_u] * L)
    somme = int(sum(cs[l, n_u] for l in range(L)))
    out["T5"] = {"n_u": n_u, "lru_par_couche": hu, "somme_courbes": somme, "tient": hu == somme}
    print("T5", out["T5"], flush=True)
    # T5 cassure : allocation DP sur N : jamais pire que l'uniforme sur ses propres courbes
    alloc = allocation_dp(cs, N, k, E)
    hdp, _ = lru_par_couche(jc, L, alloc)
    out["T5_dp"] = {"dp_en_echantillon": hdp, "uniforme": hu, "dp_ge_uniforme": hdp >= hu, "alloc": alloc}
    print("T5 dp", out["T5_dp"], flush=True)
    with open(os.path.join(sortie, "temoins.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)


def gaps(prefixe, dossier, sortie, melange=False):
    """Diagnostic : la loi des écarts entre deux accès au même expert (en jetons) : loi de puissance ou exponentielle ?"""
    os.makedirs(sortie, exist_ok=True)
    gaps_all = []
    for g in GENRES:
        jetons, E = charger(prefixe, dossier, g, melange)
        L = len(jetons[0])
        dernier = {}
        for t, tok in enumerate(jetons):
            for l, couche in enumerate(tok):
                for e in couche:
                    x = (l, e)
                    if x in dernier:
                        gaps_all.append(t - dernier[x])
                    dernier[x] = t
    a = np.array(gaps_all)
    gs = np.arange(1, 257)
    surv = np.array([(a >= x).mean() for x in gs])
    # ajustement sur g dans [2, 64] : log-log (loi de puissance) contre semi-log (exponentielle)
    m = (gs >= 2) & (gs <= 64) & (surv > 0)
    x, y = gs[m].astype(float), np.log(surv[m])

    def r2(u, v):
        A = np.vstack([u, np.ones_like(u)]).T
        sol, res, *_ = np.linalg.lstsq(A, v, rcond=None)
        pred = A @ sol
        return sol, 1 - ((v - pred) ** 2).sum() / ((v - v.mean()) ** 2).sum()
    s_pl, r_pl = r2(np.log(x), y)
    s_ex, r_ex = r2(x, y)
    out = {"modele": prefixe, "n_ecarts": int(len(a)), "mediane": float(np.median(a)), "moyenne": float(a.mean()),
           "p90": float(np.percentile(a, 90)), "p99": float(np.percentile(a, 99)),
           "pente_loglog": float(s_pl[0]), "R2_puissance": float(r_pl),
           "pente_semilog": float(s_ex[0]), "R2_exponentielle": float(r_ex),
           "surv": {str(int(g)): float(s) for g, s in zip(gs[[0, 1, 3, 7, 15, 31, 63, 127, 255]], surv[[0, 1, 3, 7, 15, 31, 63, 127, 255]])}}
    with open(os.path.join(sortie, f"gaps-{prefixe}{'-melange' if melange else ''}.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "mesure":
        mesure("t" + sys.argv[2], sys.argv[3], sys.argv[4], "--melange" in sys.argv)
    elif cmd == "temoins":
        temoins(sys.argv[2], sys.argv[3])
    elif cmd == "gaps":
        gaps("t" + sys.argv[2], sys.argv[3], sys.argv[4], "--melange" in sys.argv)
