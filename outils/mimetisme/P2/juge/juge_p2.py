"""P2, juge : mon chemin pour refaire le chiffre principal (seuils : genome/mimetisme/P2/juge-seuil.md).

Écrit sans importer ni recopier outils/mimetisme/P2/*.py. Structures : horodatage par cellule dans des tableaux
numpy (-1 = absent), victime = argmin de l'horodatage hors épinglés. Troisième chemin : distances de pile de
Mattson par arbre de Fenwick (aucun cache simulé).

Usage : python -I -X utf8 juge_p2.py <dossier traces 120b> <dossier traces 20b> <dossier de sortie>
"""
import json
import os
import sys

import numpy as np

GRAND = np.iinfo(np.int64).max


def lire_trace(chemin):
    """Rend (tableau T x L x K d'identifiants l*E+e, L, E)."""
    E = None
    jetons = []
    with open(chemin, encoding="utf-8") as f:
        for brut in f:
            s = brut.strip()
            if not s or s[0] == "#":
                continue
            if s.startswith("E="):
                E = int(s[2:])
                continue
            couches = s.split("|")
            jetons.append([[int(v) for v in c.split()] for c in couches])
    a = np.asarray(jetons, dtype=np.int64)
    T, L, K = a.shape
    a = a + (np.arange(L, dtype=np.int64) * E)[None, :, None]
    return a, L, E


class Banc:
    """Deux étages. mode : 'seul', 'inclusif', 'exclusif'. Options de cassure et de sensibilité :
    casse='mru'      la démotion descend l'entrée la plus récente de la VRAM (hors épinglés) au lieu de la victime
    casse='garde'    à la remontée RAM -> VRAM, la copie reste en RAM (pas de retrait)
    ram_fifo=True    l'étage RAM évince par ordre d'insertion
    pins_ram=True    la victime RAM évite les épinglés (lib.rs l. 228)
    epingle=False    aucune règle de groupe
    seuil_sel=s      démotion sélective (None : exclusif simple)."""

    def __init__(self, n, V, R, mode, casse=None, ram_fifo=False, pins_ram=False, epingle=True, seuil_sel=None):
        self.V, self.R, self.mode = V, R, mode
        self.casse, self.ram_fifo, self.pins_ram, self.epingle = casse, ram_fifo, pins_ram, epingle
        self.sel = seuil_sel
        self.hv = np.full(n, -1, dtype=np.int64)    # horodatage VRAM
        self.hr = np.full(n, -1, dtype=np.int64)    # horodatage RAM (usage ou insertion)
        self.nb_succes = np.zeros(n, dtype=np.int64)  # succès VRAM pendant le séjour (sélectif)
        self.nv = 0
        self.nr = 0
        self.horloge = 0
        self.k = dict(acces=0, sv=0, sr=0, disque=0, descentes=0)

    def _victime(self, h, pins):
        m = np.where(h >= 0, h, GRAND)
        if pins:
            m[list(pins)] = GRAND
        i = int(np.argmin(m))
        assert m[i] != GRAND
        return i

    def _vers_ram(self, x, pins):
        if self.hr[x] >= 0:
            if not self.ram_fifo:
                self.hr[x] = self._tic()
            return
        if self.nr >= self.R:
            y = self._victime(self.hr, pins if self.pins_ram else ())
            self.hr[y] = -1
            self.nr -= 1
        self.hr[x] = self._tic()
        self.nr += 1

    def _tic(self):
        self.horloge += 1
        return self.horloge

    def couche(self, groupe):
        pins = set(int(x) for x in groupe) if self.epingle else set()
        ram = self.mode != "seul" and self.R > 0
        for x in groupe:
            x = int(x)
            k = self.k
            k["acces"] += 1
            if self.hv[x] >= 0:
                k["sv"] += 1
                self.hv[x] = self._tic()
                self.nb_succes[x] += 1
                if ram and self.mode == "inclusif" and self.hr[x] >= 0 and not self.ram_fifo:
                    self.hr[x] = self._tic()
                continue
            victime = None
            if self.nv >= self.V:
                if ram and self.mode == "exclusif" and self.casse == "mru":
                    m = np.where(self.hv >= 0, self.hv, -1)
                    if pins:
                        m[list(pins)] = -1
                    descendue = int(np.argmax(m))
                else:
                    descendue = None
                victime = self._victime(self.hv, pins)
                vs = int(self.nb_succes[victime])
                self.hv[victime] = -1
                self.nv -= 1
            self.hv[x] = self._tic()
            self.nv += 1
            if ram and self.hr[x] >= 0:
                k["sr"] += 1
                if self.mode == "exclusif" and self.casse != "garde":
                    self.hr[x] = -1
                    self.nr -= 1
                elif not self.ram_fifo:
                    self.hr[x] = self._tic()
                self.nb_succes[x] = self.sel if self.sel is not None else 0
            else:
                k["disque"] += 1
                self.nb_succes[x] = 0
                if ram and self.mode == "inclusif":
                    self._vers_ram(x, pins)
            if ram and self.mode == "exclusif" and victime is not None:
                if self.sel is not None and vs < self.sel:
                    continue
                k["descentes"] += 1
                if self.casse == "mru":
                    # cassure : on « descend » une copie de l'entrée la plus récente, la victime est perdue
                    self._vers_ram(descendue, pins)
                else:
                    self._vers_ram(victime, pins)


def jouer(G, n, V, R, mode, ordre_inverse=False, **opt):
    b = Banc(n, V, R, mode, **opt)
    T, L, _ = G.shape
    for t in range(T):
        for l in range(L):
            g = G[t, l]
            b.couche(g[::-1] if ordre_inverse else g)
    k = dict(b.k)
    k["jetons"] = T
    k["part_disque"] = k["disque"] / k["acces"]
    k["descentes_par_jeton"] = k["descentes"] / T
    k["defauts_vram_par_jeton"] = (k["sr"] + k["disque"]) / T
    k["disque_par_jeton"] = k["disque"] / T
    k["ram_par_jeton"] = k["sr"] / T
    return k


def lru_mattson(G, capacites):
    """Défauts d'un LRU (sans épinglage) pour chaque capacité, par distances de pile (Fenwick)."""
    flux = G.reshape(-1)
    N = flux.size
    arbre = np.zeros(N + 1, dtype=np.int64)

    def ajoute(i, v):
        i += 1
        while i <= N:
            arbre[i] += v
            i += i & -i

    def somme(i):  # somme des positions [0, i)
        s = 0
        while i > 0:
            s += arbre[i]
            i -= i & -i
        return s

    dernier = {}
    dist = np.empty(N, dtype=np.int64)
    for p in range(N):
        x = int(flux[p])
        q = dernier.get(x)
        if q is None:
            dist[p] = GRAND
        else:
            dist[p] = somme(p) - somme(q + 1) + 1  # éléments distincts touchés depuis q, x compris
            ajoute(q, -1)
        ajoute(p, 1)
        dernier[x] = p
    return {C: int(np.sum(dist > C)) for C in capacites}


def main():
    d120, d20, sortie = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(sortie, exist_ok=True)
    out = {}
    gens = {"prose-en.generation": "t120b.prose-en.generation.trace",
            "wiki.generation": "w120b.wiki.generation.trace"}
    V, R = 326, 336
    for nom, f in gens.items():
        G, L, E = lire_trace(os.path.join(d120, f))
        n = L * E
        assert (L, E, G.shape[2]) == (36, 128, 4)
        r = {"jetons": G.shape[0]}
        r["seul"] = jouer(G, n, V, 0, "seul")
        r["inclusif"] = jouer(G, n, V, R, "inclusif")
        r["exclusif"] = jouer(G, n, V, R, "exclusif")
        # J2 : troisième chemin
        r["exclusif_sans_pins"] = jouer(G, n, V, R, "exclusif", epingle=False)
        r["mattson_defauts"] = lru_mattson(G, [V, V + R])
        r["lru_VR_pins"] = jouer(G, n, V + R, 0, "seul")
        # J3 : cassures
        r["casse_mru"] = jouer(G, n, V, R, "exclusif", casse="mru")
        r["casse_garde"] = jouer(G, n, V, R, "exclusif", casse="garde")
        r["exclusif_ram_fifo"] = jouer(G, n, V, R, "exclusif", ram_fifo=True)
        # J4 : sensibilité
        r["inclusif_ordre_inverse"] = jouer(G, n, V, R, "inclusif", ordre_inverse=True)
        r["exclusif_ordre_inverse"] = jouer(G, n, V, R, "exclusif", ordre_inverse=True)
        r["inclusif_pins_ram"] = jouer(G, n, V, R, "inclusif", pins_ram=True)
        r["inclusif_R160"] = jouer(G, n, V, 160, "inclusif")
        # J5 : sélectif
        r["selectif_s1"] = jouer(G, n, V, R, "exclusif", seuil_sel=1)
        r["selectif_s0"] = jouer(G, n, V, R, "exclusif", seuil_sel=0)
        out[nom] = r
        print(nom, r["inclusif"]["part_disque"], r["exclusif"]["part_disque"], flush=True)
    # J5 sur le 20b, V = 154 et V = 54, R = round(0,0729 N)
    out20 = {}
    for g in ("code", "dialogue", "prose-en", "prose-fr", "wiki"):
        prefixe = "w20b" if g == "wiki" else "t20b"
        G, L, E = lire_trace(os.path.join(d20, f"{prefixe}.{g}.generation.trace"))
        n = L * E
        R20 = round(0.0729 * n)
        r = {"L": L, "E": E, "K": int(G.shape[2]), "N": n, "R": R20, "jetons": G.shape[0]}
        for V20 in (round(0.2001 * n), round(0.0707 * n)):
            r[f"V{V20}"] = {m: jouer(G, n, V20, R20, *a, **kw) for m, a, kw in (
                ("seul", ("seul",), {}), ("inclusif", ("inclusif",), {}),
                ("s0", ("exclusif",), {}), ("s1", ("exclusif",), {"seuil_sel": 1}))}
        out20[g] = r
        print(g, flush=True)
    out["20b"] = out20
    with open(os.path.join(sortie, "juge-brut.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
