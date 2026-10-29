"""Simulateur de cache d'experts à un ou deux étages, sur les traces de routage du 120b.

Éclaireur « ingénierie et informatique » (2026-10-26). Seuils : genome/mimetisme/ingenierie/seuils-declares.md.
Règle de groupe de `trc-cache` : les k experts d'un groupe (jeton, couche) sont épinglés pendant le groupe ;
la victime est la moins récente non épinglée. Un fil, Python + numpy.

Usage : python -I -X utf8 cache2.py <dossier des traces> <commande> ...
  temoins                   T1, T2, T3 (doivent tenir avant tout)
  h1 | h2                   hypothèses H1 et H2
  h3                        hypothèse H3 (politiques)
"""

import csv
import sys
from collections import OrderedDict

import numpy as np

L, E, K = 36, 128, 4
N = L * E
GENRES = ["code", "dialogue", "prose-en", "prose-fr"]


def charger(chemin):
    """Trace -> tableau (T, L, K) d'identifiants globaux couche*E + expert."""
    jetons = []
    for ligne in open(chemin, encoding="utf-8"):
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or ligne.startswith("E="):
            continue
        couches = [c.split() for c in ligne.split("|")]
        assert len(couches) == L, len(couches)
        jetons.append([[l * E + int(x) for x in c] for l, c in enumerate(couches)])
    a = np.array(jetons, dtype=np.int32)
    assert a.shape[1:] == (L, K)
    return a


def traces(dossier):
    t = {}
    for g in GENRES:
        t[g + ".lecture"] = charger(f"{dossier}/t120b.{g}.lecture.trace")
    t["prose-en.generation"] = charger(f"{dossier}/t120b.prose-en.generation.trace")
    t["tous.lecture"] = np.concatenate([t[g + ".lecture"] for g in GENRES])
    return t


# --------------------------------------------------------------------------- un étage, LRU


def lru1(G, V, epingle=True):
    """Succès d'un LRU global à V emplacements, règle de groupe de trc-cache."""
    cache = OrderedDict()
    succes = acces = 0
    for t in range(G.shape[0]):
        for l in range(L):
            g = [int(x) for x in G[t, l]]
            pins = set(g) if epingle else set()
            for x in g:
                acces += 1
                if x in cache:
                    succes += 1
                    cache.move_to_end(x)
                    continue
                if len(cache) >= V:
                    for v in cache:
                        if v not in pins:
                            del cache[v]
                            break
                cache[x] = True
    return succes / acces


# --------------------------------------------------------------------------- deux étages, LRU


def lru2(G, V, R, mode):
    """mode 'inclusif' (règle de trc-cache : la RAM voit tous les accès) ou 'exclusif' (démotion).
    Rend (succès VRAM, succès RAM) en part des accès."""
    vram = OrderedDict()
    ram = OrderedDict()
    sv = sr = acces = 0
    for t in range(G.shape[0]):
        for l in range(L):
            g = [int(x) for x in G[t, l]]
            pins = set(g)
            for x in g:
                acces += 1
                if x in vram:
                    sv += 1
                    vram.move_to_end(x)
                    if mode == "inclusif" and x in ram:
                        ram.move_to_end(x)
                    continue
                victime = None
                if len(vram) >= V:
                    for v in vram:
                        if v not in pins:
                            victime = v
                            break
                    del vram[victime]
                en_ram = x in ram
                if mode == "inclusif":
                    if en_ram:
                        sr += 1
                        ram.move_to_end(x)
                    else:
                        if R > 0:
                            if len(ram) >= R:
                                ram.popitem(last=False)
                            ram[x] = True
                else:  # exclusif : lu de la RAM -> retiré de la RAM ; la victime VRAM descend en RAM
                    if en_ram:
                        sr += 1
                        del ram[x]
                    if victime is not None and R > 0:
                        if victime in ram:
                            ram.move_to_end(victime)
                        else:
                            if len(ram) >= R:
                                ram.popitem(last=False)
                            ram[victime] = True
                vram[x] = True
    return sv / acces, sr / acces


# --------------------------------------------------------------------------- politiques à un étage


def prochains_usages(G):
    """Pour chaque accès (dans l'ordre à plat), la position de l'accès suivant au même identifiant."""
    flat = G.reshape(-1)
    n = len(flat)
    suiv = np.empty(n, dtype=np.int64)
    dernier = {}
    for i in range(n - 1, -1, -1):
        x = int(flat[i])
        suiv[i] = dernier.get(x, 1 << 60)
        dernier[x] = i
    return suiv


def politique(G, V, nom):
    """Succès d'une politique à V emplacements. nom : lru, lfu, slru, adm, etr, belady."""
    T = G.shape[0]
    resident = np.zeros(N, dtype=bool)
    nres = 0
    cnt = np.zeros(N, dtype=np.int64)
    dern = np.zeros(N, dtype=np.int64)
    p = np.zeros(N, dtype=np.float64)
    nxt = np.full(N, 1 << 60, dtype=np.int64)
    couche_de = np.arange(N) // E
    suiv = prochains_usages(G) if nom == "belady" else None
    # slru
    if nom == "slru":
        prob, prot = OrderedDict(), OrderedDict()
        cap_prob = max(1, int(0.2 * V))
    horloge = 0
    succes = acces = 0
    pos = 0
    epingle_m = np.zeros(N, dtype=bool)
    for t in range(T):
        for l in range(L):
            g = [int(x) for x in G[t, l]]
            pins = set(g)
            epingle_m[:] = False
            epingle_m[g] = True
            for x in g:
                acces += 1
                horloge += 1
                cnt[x] += 1
                if nom == "adm" and horloge % 10000 == 0:
                    cnt >>= 1
                if nom == "belady":
                    nxt[x] = suiv[pos]
                pos += 1
                hit = resident[x]
                if nom == "slru":
                    hit = x in prob or x in prot
                if hit:
                    succes += 1
                    dern[x] = horloge
                    if nom == "slru":
                        if x in prob:
                            del prob[x]
                            prot[x] = True
                            if len(prot) > V - cap_prob:
                                a, _ = prot.popitem(last=False)
                                prob[a] = True
                        else:
                            prot.move_to_end(x)
                    continue
                # défaut
                if nom == "slru":
                    if len(prob) + len(prot) >= V:
                        src = prob if any(v not in pins for v in prob) else prot
                        for v in src:
                            if v not in pins:
                                del src[v]
                                break
                    prob[x] = True
                    dern[x] = horloge
                    continue
                if nres >= V:
                    cand = np.flatnonzero(resident & ~epingle_m)
                    if nom in ("lru", "adm"):
                        v = cand[np.argmin(dern[cand])]
                    elif nom == "lfu":
                        v = cand[np.argmin(cnt[cand] * (1 << 40) + dern[cand])]
                    elif nom == "etr":
                        d = ((couche_de[cand] - l - 1) % L) + 1
                        etr = d + L * (1.0 / np.maximum(p[cand], 0.01) - 1.0)
                        v = cand[np.argmax(etr)]
                    elif nom == "belady":
                        v = cand[np.argmax(nxt[cand])]
                    if nom == "adm" and cnt[x] <= cnt[v]:
                        continue  # contourné : servi depuis un tampon d'arrivée, n'entre pas
                    resident[v] = False
                    nres -= 1
                resident[x] = True
                nres += 1
                dern[x] = horloge
        if nom == "etr":
            u = np.zeros(N)
            u[G[t].reshape(-1)] = 1.0
            p = 0.95 * p + 0.05 * u
    return succes / acces


# --------------------------------------------------------------------------- commandes


def publie(dossier_csv):
    r = {}
    for x in csv.DictReader(open(dossier_csv, encoding="utf-8")):
        if x["portee"] == "globale":
            r[(x["trace"], x["politique"], int(x["capacite"]))] = float(x["succes"])
    return r


def cmd_temoins(tr, publie_csv, sortie):
    pub = publie(publie_csv)
    lignes = []
    ok1 = True
    cassure_voit = False
    for nom, G in tr.items():
        for V in (230, 461):
            m = lru1(G, V)
            ref = pub[(nom, "lru", V)]
            lignes.append(("T1", nom, V, round(m, 5), ref, round(m - ref, 5)))
            ok1 &= abs(m - ref) <= 0.002
            if V == 230:
                s = lru1(G, V, epingle=False)
                lignes.append(("T2-sans-epinglage", nom, V, round(s, 5), ref, round(s - ref, 5)))
                cassure_voit |= abs(s - ref) > 0.002
    ok3 = True
    for nom in ("prose-en.generation", "prose-en.lecture"):
        G = tr[nom]
        for V, R in ((326, 80), (326, 336)):
            sv, sr = lru2(G, V, R, "exclusif")
            u = lru1(G, V + R)
            lignes.append(("T3", nom, f"{V}+{R}", round(sv + sr, 5), round(u, 5), round(sv + sr - u, 5)))
            ok3 &= abs(sv + sr - u) <= 0.003
    with open(sortie, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["temoin", "trace", "capacite", "mesure", "reference", "ecart"])
        w.writerows(lignes)
    print("T1 tient :", ok1, "| T2 la cassure voit la règle :", cassure_voit, "| T3 tient :", ok3)
    for l in lignes:
        print(*l)


def cmd_h(tr, quoi, sortie):
    V = 326
    lignes = []
    noms = ["prose-en.generation", "tous.lecture"] if quoi == "h2" else list(tr)
    Rs = (80, 160, 326) if quoi == "h1" else (80, 336, 672)
    for nom in noms:
        G = tr[nom]
        seul = lru1(G, V)
        lignes.append((nom, "seul", V, 0, round(seul, 5), 0.0, round(1 - seul, 5)))
        for R in Rs:
            for mode in ("inclusif", "exclusif") if quoi == "h2" else ("inclusif",):
                sv, sr = lru2(G, V, R, mode)
                lignes.append((nom, mode, V, R, round(sv, 5), round(sr, 5), round(1 - sv - sr, 5)))
    with open(sortie, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["trace", "mode", "V", "R", "succes_vram", "succes_ram", "part_disque"])
        w.writerows(lignes)
    for l in lignes:
        print(*l)


def cmd_h3(tr, sortie, noms=None, caps=(326,)):
    """Amendement n° 2 : par défaut V = 326 seulement (temps) ; noms : sous-ensemble de traces."""
    lignes = []
    for nom, G in tr.items():
        if noms and nom not in noms:
            continue
        for V in caps:
            for pol in ("lru", "lfu", "slru", "adm", "etr", "belady"):
                lignes.append((nom, V, pol, round(politique(G, V, pol), 5)))
                print(*lignes[-1], flush=True)
    with open(sortie, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["trace", "V", "politique", "succes"])
        w.writerows(lignes)


if __name__ == "__main__":
    dossier, cmd = sys.argv[1], sys.argv[2]
    tr = traces(dossier)
    base = "~/dev/active/troncons"
    sortie = f"{base}/mesures/mimetisme/ingenierie"
    if cmd == "temoins":
        cmd_temoins(tr, f"{base}/mesures/localite-gpt-oss/120b/courbes-gpt-oss-120b.csv", f"{sortie}/temoins.csv")
    elif cmd in ("h1", "h2"):
        cmd_h(tr, cmd, f"{sortie}/{cmd}.csv")
    elif cmd == "h3":
        noms = sys.argv[3].split(",") if len(sys.argv) > 3 else None
        etiq = sys.argv[4] if len(sys.argv) > 4 else "h3"
        cmd_h3(tr, f"{sortie}/{etiq}.csv", noms)
