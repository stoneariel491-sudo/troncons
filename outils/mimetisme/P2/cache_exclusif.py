"""P2, cache exclusif VRAM vers RAM : simulateur et bancs (mon implémentation, indépendante de cache2.py).

Seuils : genome/mimetisme/P2/seuil-declare.md (commité avant toute lecture de trace).
Règle de groupe de `trc-cache` : les k experts d'un groupe (jeton, couche) sont épinglés ; la victime VRAM
est le moins récent non épinglé. Un fil, Python pur + numpy pour la lecture seulement.

Modes :
  seul      LRU VRAM sans RAM (R ignoré)
  inclusif  règle actuelle de trc-cache : la RAM est remplie à chaque défaut disque, rafraîchie à chaque
            succès VRAM d'une entrée qui s'y trouve ; une lecture RAM garde l'entrée en RAM
  exclusif  démotion : la victime VRAM descend en RAM ; une lecture RAM retire l'entrée de la RAM
  cass_a    exclusif sans démotion (RAM jamais remplie)           -> doit redonner `seul`
  cass_b    exclusif avec remplissage au défaut disque, au lieu de la démotion -> doit redonner `inclusif`
            (mêmes interrupteurs que l'inclusif : elle est donc égale par construction ; sa valeur est de
            vérifier que les interrupteurs, seuls, font l'inclusif ; l'indépendance vient du T4 et du Rust)
  cass_c    hybride (remplissage au défaut, retrait à la remontée), diagnostic sans témoin

Usage : python -I -X utf8 cache_exclusif.py <dossier des traces> <temoins|grille|chaine> <csv de sortie>
"""
import csv
import sys
from collections import OrderedDict

import numpy as np

L, E, K = 36, 128, 4
GENRES = {
    "code.lecture": "t120b.code.lecture.trace",
    "dialogue.lecture": "t120b.dialogue.lecture.trace",
    "prose-en.lecture": "t120b.prose-en.lecture.trace",
    "prose-fr.lecture": "t120b.prose-fr.lecture.trace",
    "wiki.lecture": "w120b.wiki.lecture.trace",
    "prose-en.generation": "t120b.prose-en.generation.trace",
    "wiki.generation": "w120b.wiki.generation.trace",
}


def charger(chemin):
    jetons = []
    for ligne in open(chemin, encoding="utf-8"):
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or ligne.startswith("E="):
            continue
        cs = [c.split() for c in ligne.split("|")]
        assert len(cs) == L
        jetons.append([[l * E + int(x) for x in c] for l, c in enumerate(cs)])
    a = np.array(jetons, dtype=np.int32)
    assert a.shape[1:] == (L, K)
    return a


def traces(dossier):
    t = {nom: charger(f"{dossier}/{f}") for nom, f in GENRES.items()}
    t["tous.lecture"] = np.concatenate([t[g] for g in GENRES if g.endswith("lecture")])
    return t


# interrupteurs : demotion, remplissage au defaut disque, retrait de la RAM a la remontee, rafraichissement
# de l'entree RAM lors d'un succes VRAM
MODES = {
    "seul":     None,
    "inclusif": dict(demotion=False, remplit=True,  retire=False, rafraichit=True),
    "exclusif": dict(demotion=True,  remplit=False, retire=True,  rafraichit=False),
    "cass_a":   dict(demotion=False, remplit=False, retire=True,  rafraichit=False),  # redonne seul
    "cass_b":   dict(demotion=False, remplit=True,  retire=False, rafraichit=True),   # redonne inclusif
    "cass_c":   dict(demotion=False, remplit=True,  retire=True,  rafraichit=False),  # hybride, diagnostic
}


def sim(G, V, R, mode, depuis=0, epingle=True):
    """Rejoue G (T, L, K). Compte les acces des jetons >= depuis (le cache est chauffe avant)."""
    f = MODES[mode]
    vram, ram = OrderedDict(), OrderedDict()
    c = dict(acces=0, sv=0, sr=0, disque=0, demotions=0, evict_ram=0, remplissages=0)
    avec_ram = f is not None and R > 0

    def inserer_ram(x):
        if x in ram:
            ram.move_to_end(x)
            return
        if len(ram) >= R:
            ram.popitem(last=False)
            c["evict_ram"] += 1
        ram[x] = True

    for t in range(G.shape[0]):
        compte = t >= depuis
        for l in range(L):
            g = [int(x) for x in G[t, l]]
            pins = set(g) if epingle else set()
            for x in g:
                if compte:
                    c["acces"] += 1
                if x in vram:
                    if compte:
                        c["sv"] += 1
                    vram.move_to_end(x)
                    if avec_ram and f["rafraichit"] and x in ram:
                        ram.move_to_end(x)
                    continue
                victime = None
                if len(vram) >= V:
                    for v in vram:
                        if v not in pins:
                            victime = v
                            break
                    del vram[victime]
                vram[x] = True
                dans_ram = avec_ram and (x in ram)
                if dans_ram:
                    if compte:
                        c["sr"] += 1
                    if f["retire"]:
                        del ram[x]
                    else:
                        ram.move_to_end(x)
                else:
                    if compte:
                        c["disque"] += 1
                    if avec_ram and f["remplit"]:
                        c["remplissages"] += 1
                        inserer_ram(x)
                if avec_ram and f["demotion"] and victime is not None:
                    if compte:
                        c["demotions"] += 1
                    inserer_ram(victime)
    a = c["acces"]
    c["part_disque"] = c["disque"] / a
    c["succes_vram"] = c["sv"] / a
    c["succes_ram"] = c["sr"] / a
    c["jetons"] = G.shape[0] - depuis
    return c


CHAMPS = ["trace", "V", "R", "mode", "jetons", "acces", "succes_vram", "succes_ram", "part_disque",
          "disque", "demotions", "demotions_par_jeton", "remplissages", "evict_ram"]


def ligne(nom, V, R, mode, c):
    return [nom, V, R, mode, c["jetons"], c["acces"], round(c["succes_vram"], 6), round(c["succes_ram"], 6),
            round(c["part_disque"], 6), c["disque"], c["demotions"],
            round(c["demotions"] / c["jetons"], 4), c["remplissages"], c["evict_ram"]]


def ecrire(chemin, lignes):
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(CHAMPS)
        w.writerows(lignes)


if __name__ == "__main__":
    dossier, cmd, sortie = sys.argv[1], sys.argv[2], sys.argv[3]
    tr = traces(dossier)
    lignes = []
    if cmd == "temoins":
        for nom, G in tr.items():
            if nom == "tous.lecture":
                continue
            V = 326
            for R in (0, 80, 336):
                for mode in ("seul", "inclusif", "exclusif", "cass_a", "cass_b", "cass_c"):
                    lignes.append(ligne(nom, V, R, mode, sim(G, V, R, mode)))
            lignes.append(ligne(nom, V, 160, "inclusif", sim(G, V, 160, "inclusif")))
            for R in (80, 336):
                lignes.append(ligne(nom, V + R, 0, "unique_V+R", sim(G, V + R, 0, "seul")))
            print(nom, flush=True)
    elif cmd == "t1bord":
        for nom, G in tr.items():
            if nom != "tous.lecture":
                lignes.append(ligne(nom, 326, 326, "inclusif", sim(G, 326, 326, "inclusif")))
                lignes.append(ligne(nom, 326, 326, "exclusif", sim(G, 326, 326, "exclusif")))
    elif cmd == "grille":
        for nom, G in tr.items():
            for V in (326, 922):
                lignes.append(ligne(nom, V, 0, "seul", sim(G, V, 0, "seul")))
                for R in (80, 160, 336, 672, 1344):
                    for mode in ("inclusif", "exclusif"):
                        lignes.append(ligne(nom, V, R, mode, sim(G, V, R, mode)))
            print(nom, flush=True)
    elif cmd == "chaine":
        for genre, (lec, gen) in {"prose-en": ("prose-en.lecture", "prose-en.generation"),
                                  "wiki": ("wiki.lecture", "wiki.generation")}.items():
            G = np.concatenate([tr[lec], tr[gen]])
            depuis = tr[lec].shape[0]
            for V in (326, 922):
                lignes.append(ligne(f"{genre}.chaine", V, 0, "seul", sim(G, V, 0, "seul", depuis)))
                for R in (80, 160, 336, 672, 1344):
                    for mode in ("inclusif", "exclusif"):
                        lignes.append(ligne(f"{genre}.chaine", V, R, mode, sim(G, V, R, mode, depuis)))
            print(genre, flush=True)
    ecrire(sortie, lignes)
