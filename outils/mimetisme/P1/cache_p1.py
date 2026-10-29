"""P1 : mémoire du cache à deux échelles (LFU à demi-vie), jugée en génération.

Simulateur écrit pour ce rôle (rien n'est repris de cache2.py sauf, comme repère indépendant, ses
fonctions lru1 / politique pour les témoins). Protocole déclaré avant toute mesure :
genome/mimetisme/P1/protocole.md (commit c861e8f).

Règle de groupe de trc-cache : les k experts d'un (jeton, couche) sont épinglés pendant le groupe ; on
évince, après insertion du groupe, les plus petits scores hors du groupe ; départage : accès le plus ancien
d'abord. L'horloge est l'indice du jeton (continue dans une chaîne).

Usage : python -I -X utf8 cache_p1.py <commande> ...
  temoins                       W1 à W6 (avant toute autre mesure)
  grille <120b|20b> <cap,cap>   calcule tous les succès par jeton, range dans mesures/mimetisme/P1/
  juge <120b|20b> <cap>         verdict au seuil déclaré, à partir de la grille
"""

import csv
import ctypes
import heapq
import json
import math
import os
import sys
from collections import OrderedDict

import numpy as np

BASE = "~/dev/active/troncons"
DONNEES = "~/dev/mimetisme-P1-donnees"
SORTIE = f"{BASE}/mesures/mimetisme/P1"
LN2 = math.log(2.0)

H_GRILLE = [8, 32, 64, 128, math.inf]
W_GRILLE = [0.1, 0.3, 0.5, 0.7, 0.9]
H_RAPIDE, H_LENTE = 8.0, 128.0


def baisser_priorite():
    """Priorité sous la normale (consigne de cohabitation)."""
    try:
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    except Exception:
        pass


# --------------------------------------------------------------------------- données


def charger(chemin):
    """Trace -> (tableau (T, L, K) d'identifiants globaux couche*E + expert, E)."""
    E = None
    jetons = []
    for ligne in open(chemin, encoding="utf-8"):
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#"):
            continue
        if ligne.startswith("E="):
            E = int(ligne[2:])
            continue
        couches = [c.split() for c in ligne.split("|")]
        jetons.append([[l * E + int(x) for x in c] for l, c in enumerate(couches)])
    a = np.array(jetons, dtype=np.int32)
    return a, E


def dossier_modele(m):
    return f"{DONNEES}/{'t120' if m == '120b' else 't20'}"


def prefixe(m, genre):
    """Préfixe de fichier : t120b.<genre> sauf wiki (w120b.wiki)."""
    p = "t" if genre != "wiki" else "w"
    return f"{p}{m}.{genre}"


GENRES = {"120b": ["code", "dialogue", "prose-en", "prose-fr", "wiki"], "20b": ["code", "dialogue", "prose-en", "prose-fr", "wiki"]}
GEN_DISPO = {"120b": ["prose-en", "wiki"], "20b": ["code", "dialogue", "prose-en", "prose-fr", "wiki"]}


def lire(m, genre, mode):
    return charger(f"{dossier_modele(m)}/{prefixe(m, genre)}.{mode}.trace")


# --------------------------------------------------------------------------- politiques (rendent les succès par jeton)


def lru(Gl, N):
    T = len(Gl)
    hits = [0] * T
    cache = OrderedDict()
    for t in range(T):
        hh = 0
        for g in Gl[t]:
            for x in g:
                if x in cache:
                    hh += 1
                    cache.move_to_end(x)
                else:
                    cache[x] = True
            while len(cache) > N:
                cache.popitem(last=False)
        hits[t] = hh
    return np.array(hits, dtype=np.int32)


def lfu(Gl, N, h, inverse=False):
    """LFU à décroissance exponentielle, demi-vie h en jetons (math.inf : compte qui ne vieillit jamais).
    Entre deux mises à jour deux scores décroissent du même facteur : l'ordre ne change pas, on range
    donc log(score) − t·ld dans un tas à invalidation paresseuse. inverse=True : décroissance inversée
    (cassure : les vieux comptes pèsent plus)."""
    T = len(Gl)
    hits = [0] * T
    fini = not math.isinf(h)
    ld = 0.0
    if fini:
        ld = (LN2 / h) if inverse else -(LN2 / h)
    cle, vu, cnt = {}, {}, {}
    cache, tas = set(), []
    seq = 0
    for t in range(T):
        hh = 0
        for g in Gl[t]:
            for x in g:
                seq += 1
                if fini:
                    a = cle.get(x)
                    v = 1.0 if a is None else math.exp(min(a + t * ld, 700.0)) + 1.0
                    k = math.log(v) - t * ld
                else:
                    c = cnt.get(x, 0) + 1
                    cnt[x] = c
                    k = c
                cle[x] = k
                vu[x] = seq
                if x in cache:
                    hh += 1
                else:
                    cache.add(x)
                heapq.heappush(tas, (k, seq, x))
            if len(cache) > N:
                dg = set(g)
                mis = []
                while len(cache) > N:
                    k_, s_, x_ = heapq.heappop(tas)
                    if x_ not in cache or cle[x_] != k_ or vu[x_] != s_:
                        continue
                    if x_ in dg:
                        mis.append((k_, s_, x_))
                        continue
                    cache.remove(x_)
                for e in mis:
                    heapq.heappush(tas, e)
        hits[t] = hh
    return np.array(hits, dtype=np.int32)


def _squelette(G, NN, N, score, apres_jeton=None):
    """Boucle commune aux politiques vectorisées (une opération numpy par groupe). score.maj(g, t) met à
    jour l'état des k experts du groupe g ; score(cand, t, l) rend les scores des candidats (plus petit =
    évincé d'abord). Départage : numéro d'accès le plus ancien."""
    T, L, K = G.shape
    hits = np.zeros(T, dtype=np.int32)
    resident = np.zeros(NN, dtype=bool)
    pin = np.zeros(NN, dtype=bool)
    seqa = np.zeros(NN, dtype=np.int64)
    ordre = np.arange(1, K + 1)
    seq = 0
    nres = 0
    for t in range(T):
        hh = 0
        for l in range(L):
            g = G[t, l]
            nh = int(np.count_nonzero(resident[g]))
            hh += nh
            nres += K - nh
            resident[g] = True
            score.maj(g, t)
            seqa[g] = seq + ordre
            seq += K
            if nres > N:
                pin[g] = True
                cand = np.flatnonzero(resident & ~pin)
                pin[g] = False
                s = score(cand, t, l)
                o = np.lexsort((seqa[cand], s))
                resident[cand[o[: nres - N]]] = False
                nres = N
        hits[t] = hh
        if apres_jeton is not None:
            apres_jeton(t)
    return hits


class _Melange:
    def __init__(self, NN, w, h1=H_RAPIDE, h2=H_LENTE):
        self.c1 = np.zeros(NN)
        self.c2 = np.zeros(NN)
        self.last = np.zeros(NN, dtype=np.int64)
        self.w, self.h1, self.h2 = w, h1, h2
        self.r1, self.r2 = LN2 / h1, LN2 / h2

    def maj(self, g, t):
        dt = t - self.last[g]
        self.c1[g] = self.c1[g] * np.exp2(-dt / self.h1) + 1.0
        self.c2[g] = self.c2[g] * np.exp2(-dt / self.h2) + 1.0
        self.last[g] = t

    def __call__(self, cand, t, l):
        dt = t - self.last[cand]
        return (1 - self.w) * self.r1 * self.c1[cand] * np.exp2(-dt / self.h1) + self.w * self.r2 * self.c2[cand] * np.exp2(-dt / self.h2)


def melange(G, N, w):
    L, E = G.shape[1], None
    return _squelette(G, int(G.max()) + 1, N, _Melange(int(G.max()) + 1, w))


class _Etr:
    def __init__(self, NN, L, E):
        self.p = np.zeros(NN)
        self.u = np.zeros(NN)
        self.couche = np.arange(NN) // E
        self.L = L

    def maj(self, g, t):
        self.u[g] = 1.0

    def __call__(self, cand, t, l):
        d = ((self.couche[cand] - l - 1) % self.L) + 1
        return -(d + self.L * (1.0 / np.maximum(self.p[cand], 0.01) - 1.0))  # ETR haut = évincé d'abord

    def apres(self, t):
        self.p = 0.95 * self.p + 0.05 * self.u
        self.u[:] = 0.0


def etr(G, N, L, E):
    """Horloge de couches (mêmes paramètres que cache2.politique('etr') : 0,95 par jeton, plancher 0,01)."""
    s = _Etr(L * E, L, E)
    return _squelette(G, L * E, N, s, apres_jeton=s.apres)


def politique(G, N, nom, L, E):
    """nom : 'lru', 'lfu:<h>' (h = 8, 32, ..., 'inf', 'inv:<h>' pour la cassure), 'mix:<w>', 'etr'."""
    k, _, a = nom.partition(":")
    if nom == "lru":
        return lru(G.tolist(), N)
    if k == "lfu":
        return lfu(G.tolist(), N, math.inf if a == "inf" else float(a))
    if k == "inv":
        return lfu(G.tolist(), N, float(a), inverse=True)
    if k == "mix":
        return melange(G, N, float(a))
    if k == "etr":
        return etr(G, N, L, E)
    raise ValueError(nom)


def noms_politiques(python_seul=False):
    """Toutes les politiques ; python_seul : sans le mélange (calculé par noyau-p1, voir rust_p1.py : le
    mélange vectorisé en Python coûte plus d'une minute par trace de lecture, sous charge)."""
    return (["lru"] + ["lfu:" + ("inf" if math.isinf(h) else str(h)) for h in H_GRILLE]
            + ([] if python_seul else ["mix:" + str(w) for w in W_GRILLE]) + ["etr"])


# --------------------------------------------------------------------------- statistiques


def ecart_blocs(h_pol, h_ref, deb, fin, ak, bloc=32):
    """Écart moyen (succès pol − succès ref) sur les jetons [deb, fin) et son écart-type par blocs de `bloc`
    jetons (blocs entiers seulement), ak = nombre d'accès par jeton. Rend (d, sigma, z, nb_blocs)."""
    a = h_pol[deb:fin].astype(float)
    b = h_ref[deb:fin].astype(float)
    d = float((a - b).sum() / (len(a) * ak))
    nb = len(a) // bloc
    if nb < 2:
        return d, float("nan"), float("nan"), nb
    db = (a[: nb * bloc] - b[: nb * bloc]).reshape(nb, bloc).sum(axis=1) / (bloc * ak)
    sigma = float(db.std(ddof=1) / math.sqrt(nb))
    z = d / sigma if sigma > 0 else (math.inf if d > 0 else (-math.inf if d < 0 else 0.0))
    return d, sigma, z, nb


def verdict(cas):
    """cas : {'gen-A': (d, z), 'gen-B': (d, z), 'chaine-A': (d, z), 'chaine-B': (d, z)}.
    Seuil déclaré (ec124f5 + protocole c861e8f) : tient si d >= 0,02 et z > 2 partout ; tombe si l'une des
    deux générations seules < 0,005 ; ouvert sinon."""
    gens = [k for k in cas if k.startswith("gen-")]
    tout = list(cas)
    if any(cas[k][0] < 0.005 for k in gens):
        return "tombe"
    if all(cas[k][0] >= 0.02 and cas[k][1] > 2 for k in tout):
        return "tient"
    return "ouvert"


# --------------------------------------------------------------------------- grille


def cle(m, trace, cap, pol):
    return "__".join([m, trace, str(cap), pol.replace(":", "-")])


def traces_a_calculer(m):
    """Liste (nom, G, E, [coupure]) : lectures, générations, chaînes. coupure = indice du premier jeton de la génération."""
    out = []
    for g in GENRES[m]:
        G, E = lire(m, g, "lecture")
        out.append((f"lecture-{g}", G, E, None))
    for g in GEN_DISPO[m]:
        Gg, E = lire(m, g, "generation")
        out.append((f"gen-{g}", Gg, E, None))
        Gr, _ = lire(m, g, "lecture")
        out.append((f"chaine-{g}", np.concatenate([Gr, Gg]), E, len(Gr)))
    return out


def cmd_grille(m, caps):
    store_chemin = f"{SORTIE}/hits-{m}.npz"
    store = {}
    if os.path.exists(store_chemin):
        z = np.load(store_chemin)
        store = {k: z[k] for k in z.files}
    for nom, G, E, coupure in traces_a_calculer(m):
        L = G.shape[1]
        for cap in caps:
            for pol in noms_politiques(python_seul=True):
                k = cle(m, nom, cap, pol)
                if k in store:
                    continue
                import time

                t0 = time.time()
                store[k] = politique(G, cap, pol, L, E)
                tot = store[k].sum() / (G.shape[0] * L * G.shape[2])
                print(f"{nom} N={cap} {pol} succes={tot:.5f} ({time.time() - t0:.1f}s)", flush=True)
            np.savez_compressed(store_chemin, **store)
    print("grille finie", flush=True)


def charger_store(m):
    """Succès par jeton : lru, lfu, etr de cache_p1.py ; mix de noyau-p1 (hits-<m>-rust.npz)."""
    z = np.load(f"{SORTIE}/hits-{m}.npz")
    st = {k: z[k] for k in z.files}
    chemin = f"{SORTIE}/hits-{m}-rust.npz"
    if os.path.exists(chemin):
        r = np.load(chemin)
        for k in r.files:
            if "__mix-" in k:
                st[k] = r[k]
    return st


def cmd_juge(m, cap):
    store = charger_store(m)
    sorties = {}
    lectures = GENRES[m]
    _g = lire(m, GEN_DISPO[m][0], "generation")[0]
    L, K = _g.shape[1], _g.shape[2]
    ak = L * K

    def succ(trace, pol, a=0, b=None):
        h = store[cle(m, trace, cap, pol)]
        b = len(h) if b is None else b
        return float(h[a:b].sum() / ((b - a) * ak))

    # h* et w* par validation croisée sur les lectures des autres genres
    def meilleur(famille, genre):
        autres = [g for g in lectures if g != genre]
        sc = {}
        for p in famille:
            sc[p] = float(np.mean([succ(f"lecture-{g}", p) - succ(f"lecture-{g}", "lru") for g in autres]))
        best = max(famille, key=lambda p: (sc[p], -famille.index(p)))  # égalité : le premier (plus petit h)
        return best, sc

    pols = [p for p in noms_politiques() if cle(m, "lecture-code", cap, p) in store]  # le mélange manque au 20b
    fam_lfu = [p for p in pols if p.startswith("lfu:")]
    fam_mix = [p for p in pols if p.startswith("mix:")]
    res = {"modele": m, "capacite": cap, "cas": {}, "cv": {}}
    cas_v = {}
    for g in GEN_DISPO[m]:
        hstar, scv = meilleur(fam_lfu, g)
        wstar, scw = meilleur(fam_mix, g) if fam_mix else (None, {})
        res["cv"][g] = {"lfu": scv, "h_etoile": hstar, "mix": scw, "w_etoile": wstar}
        for typ in ("gen", "chaine"):
            tr = f"{typ}-{g}"
            h_ref = store[cle(m, tr, cap, "lru")]
            T = len(h_ref)
            deb = 0 if typ == "gen" else T - 256
            ligne = {"segment": [deb, T]}
            if typ == "chaine":
                ligne["lru_chaine_entiere"] = succ(tr, "lru")
            for p in pols:
                d, s, z, nb = ecart_blocs(store[cle(m, tr, cap, p)], h_ref, deb, T, ak)
                ligne[p] = {"succes": succ(tr, p, deb, T), "d": d, "sigma": s, "z": z, "blocs": nb}
            # le chiffre du verdict : LFU(h*) ; comparateurs : mix(w*), etr ; oracle : meilleur h sur la trace jugée
            ligne["h_etoile"] = hstar
            ligne["d_lfu_hetoile"] = ligne[hstar]["d"]
            ligne["z_lfu_hetoile"] = ligne[hstar]["z"]
            ligne["mix_wetoile"] = wstar
            ligne["d_mix_wetoile"] = ligne[wstar]["d"] if wstar else None
            ligne["z_mix_wetoile"] = ligne[wstar]["z"] if wstar else None
            oracle = max(fam_lfu, key=lambda p: ligne[p]["d"])
            ligne["h_oracle"] = oracle
            ligne["d_oracle"] = ligne[oracle]["d"]
            ligne["d_etr"] = ligne["etr"]["d"]
            res["cas"][tr] = ligne
            cas_v[tr] = (ligne[hstar]["d"], ligne[hstar]["z"])
    res["verdict_cas"] = {k: list(v) for k, v in cas_v.items()}
    if m == "120b" and cap == 326:
        res["verdict"] = verdict(cas_v)
    json.dump(res, open(f"{SORTIE}/juge-{m}-{cap}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps({k: v for k, v in res.items() if k != "cas"}, ensure_ascii=False, indent=1, default=str))
    for tr, l in res["cas"].items():
        print(tr, "LRU %.4f" % l["lru"]["succes"], "| h*=%s d=%+.4f z=%.1f" % (l["h_etoile"], l["d_lfu_hetoile"], l["z_lfu_hetoile"]),
              "| oracle %s d=%+.4f" % (l["h_oracle"], l["d_oracle"]),
              "| mix w*=%s d=%s" % (l["mix_wetoile"], "%+.4f" % l["d_mix_wetoile"] if l["d_mix_wetoile"] is not None else "-"), "| etr d=%+.4f" % l["d_etr"])


# --------------------------------------------------------------------------- témoins


def cmd_temoins():
    sys.path.insert(0, f"{BASE}/outils/mimetisme/ingenierie")
    import cache2

    lignes = []
    ok = {}

    def note(temoin, trace, cap, mesure, ref, tol):
        e = abs(mesure - ref)
        lignes.append({"temoin": temoin, "trace": trace, "capacite": cap, "mesure": round(mesure, 6), "reference": round(ref, 6), "ecart": round(e, 6), "tol": tol, "tient": bool(e <= tol)})
        ok.setdefault(temoin, True)
        ok[temoin] &= e <= tol
        print(lignes[-1], flush=True)

    N = 326
    d = dossier_modele("120b")
    G = {}
    for g in ("code", "dialogue", "prose-en", "prose-fr"):
        G[f"lecture-{g}"] = lire("120b", g, "lecture")[0]
    G["lecture-wiki"] = lire("120b", "wiki", "lecture")[0]
    G["gen-prose-en"] = lire("120b", "prose-en", "generation")[0]
    G["gen-wiki"] = lire("120b", "wiki", "generation")[0]
    G["tous.lecture"] = np.concatenate([G[f"lecture-{g}"] for g in ("code", "dialogue", "prose-en", "prose-fr")])
    ak = 36 * 4
    sr = lambda h, G_: float(h.sum() / (G_.shape[0] * ak))

    # repères publiés : à retrouver avant tout (preuve que mon chargement et la règle sont les bons)
    pub = {"gen-prose-en": 0.7379, "tous.lecture": 0.45279}
    for nom, G_ in G.items():
        Gl = G_.tolist()
        h_lru = lru(Gl, N)
        ref1 = cache2.lru1(G_, N)
        note("W0 mon LRU = cache2.lru1", nom, N, sr(h_lru, G_), ref1, 1e-4)
        if nom in pub:
            note("W0b cache2.lru1 = publié du seuil", nom, N, ref1, pub[nom], 6e-5)
        # W1 : demi-vie vers 0
        h_w1 = lfu(Gl, N, 0.001)
        note("W1 LFU(h->0) = LRU", nom, N, sr(h_w1, G_), sr(h_lru, G_), 1e-4)
        # W2 : demi-vie infinie
        h_w2 = lfu(Gl, N, math.inf)
        ref2 = cache2.politique(G_, N, "lfu")
        note("W2 LFU(inf) = cache2 lfu", nom, N, sr(h_w2, G_), ref2, 1e-4)
        if nom == "gen-prose-en":
            note("W2b cache2 lfu = publié du seuil", nom, N, ref2, 0.66268, 6e-5)
        if nom == "tous.lecture":
            note("W2b cache2 lfu = publié du seuil", nom, N, ref2, 0.42632, 6e-5)
        # W4 : cassure, décroissance inversée
        h_inv = lfu(Gl, N, 8, inverse=True)
        chute = sr(h_lru, G_) - sr(h_inv, G_)
        lignes.append({"temoin": "W4 cassure : decroissance inversee h=8 sous le LRU de plus de 0,02", "trace": nom, "capacite": N,
                       "mesure": round(sr(h_inv, G_), 6), "reference": round(sr(h_lru, G_), 6), "ecart": round(chute, 6), "tol": 0.02, "tient": bool(chute > 0.02)})
        ok.setdefault("W4", True)
        ok["W4"] &= chute > 0.02
        print(lignes[-1], flush=True)

    # W3 : mélange aux extrêmes, ETR contre cache2
    for nom in ("lecture-code", "gen-prose-en"):
        G_ = G[nom]
        Gl = G_.tolist()
        m0 = melange(G_, N, 0.0)
        m1 = melange(G_, N, 1.0)
        note("W3 M(0) = LFU(8)", nom, N, sr(m0, G_), sr(lfu(Gl, N, 8), G_), 1e-4)
        note("W3 M(1) = LFU(128)", nom, N, sr(m1, G_), sr(lfu(Gl, N, 128), G_), 1e-4)
        note("W3 mon ETR = cache2 etr", nom, N, sr(etr(G_, N, 36, 128), G_), cache2.politique(G_, N, "etr"), 1e-4)
    # W6 : Belady au-dessus de tout
    for nom in ("gen-prose-en", "gen-wiki"):
        G_ = G[nom]
        Gl = G_.tolist()
        bel = cache2.politique(G_, N, "belady")
        meilleur = max(sr(politique(G_, N, p, 36, 128), G_) for p in noms_politiques())
        lignes.append({"temoin": "W6 Belady >= toute politique", "trace": nom, "capacite": N, "mesure": round(bel, 6), "reference": round(meilleur, 6),
                       "ecart": round(bel - meilleur, 6), "tol": 0.0, "tient": bool(bel >= meilleur)})
        ok.setdefault("W6", True)
        ok["W6"] &= bel >= meilleur
        print(lignes[-1], flush=True)

    # W5 : la fonction de verdict elle-même
    tests = [
        ({"gen-a": (0.03, 10), "gen-b": (0.03, 10), "chaine-a": (0.03, 10), "chaine-b": (0.03, 10)}, "tient"),
        ({"gen-a": (0.001, 10), "gen-b": (0.03, 10), "chaine-a": (0.03, 10), "chaine-b": (0.03, 10)}, "tombe"),
        ({"gen-a": (0.012, 10), "gen-b": (0.03, 10), "chaine-a": (0.03, 10), "chaine-b": (0.03, 10)}, "ouvert"),
        ({"gen-a": (0.03, 1.5), "gen-b": (0.03, 10), "chaine-a": (0.03, 10), "chaine-b": (0.03, 10)}, "ouvert"),
    ]
    ok["W5"] = True
    for cas, attendu in tests:
        r = verdict(cas)
        lignes.append({"temoin": "W5 verdict", "cas": str(cas), "attendu": attendu, "rendu": r, "tient": r == attendu})
        ok["W5"] &= r == attendu
        print(lignes[-1], flush=True)

    json.dump({"tient": {k: bool(v) for k, v in ok.items()}, "lignes": lignes}, open(f"{SORTIE}/temoins.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("TEMOINS :", {k: bool(v) for k, v in ok.items()})


if __name__ == "__main__":
    baisser_priorite()
    os.makedirs(SORTIE, exist_ok=True)
    c = sys.argv[1]
    if c == "temoins":
        cmd_temoins()
    elif c == "grille":
        cmd_grille(sys.argv[2], [int(x) for x in sys.argv[3].split(",")])
    elif c == "juge":
        cmd_juge(sys.argv[2], int(sys.argv[3]))
