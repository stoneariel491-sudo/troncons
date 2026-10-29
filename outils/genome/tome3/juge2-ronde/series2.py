"""Juge des chiffres du lot « ronde », second flux : les séries neuves, point par point.

Séries neuves ou colonnes neuves du second flux :
  duplication-radial-noeuds.csv, duplication-radial-aretes.csv   (III-4.8, disposition radiale, G8)
  synthese-queue-base.csv, synthese-queue-syn.csv                 (III-7.3, les deux queues, M9)
  synthese-positions.csv, colonne « queue »                       (III-7.3)
  synthese-frontiere-kl.csv, colonnes « classe » et « origine »   (III-7.1, G1)
  synthese-erreur-kl.csv, colonne « classe »                      (III-7.2)

1. Un point tiré par série (graine 20261027, la série k tire avec 20261027 + k), retrouvé à la source.
2. Puis chaque ligne, quand la source le permet (toutes ici), et le compte de lignes.
3. Le dessin radial refait par le juge depuis l'arbre (arbre-c23.json, pleine précision), d'après la phrase de
   la légende et l'en-tête du script (moyeu au centre, cercle de profondeur d de rayon d + 1, secteur d'un
   sous-arbre proportionnel à ses feuilles + 1, enfants par score décroissant, départ en haut, sens horaire) ;
   puis ce que la légende affirme : aucune arête n'en croise une autre. Mesuré aussi, à l'échelle de la page
   (x = 0,80 cm, disques de 0,40 + 0,035 × degré cm de diamètre) : la plus petite distance entre une arête et un
   disque qu'elle ne touche pas, et les étiquettes de valeur qui touchent un disque ou une arête.
Témoin (--casser) : une position radiale déplacée de 0,01, une ligne de queue retirée, une classe changée :
chaque contrôle concerné doit tomber.

  python -I -X utf8 outils/genome/tome3/juge2-ronde/series2.py [--casser]
Sortie : journaux/series2.txt (ou series2-casser.txt).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import pathlib
import random
import sys

RACINE = pathlib.Path(__file__).resolve().parents[4]
ICI = pathlib.Path(__file__).resolve().parent
ETAT = RACINE / "mesures/genome/etat-de-l-art"
DUP = RACINE / "mesures/genome/duplication"
DONNEES = RACINE / "memoire/figures/tome3/donnees"
GRAINE = 20261027
ECHELLE_CM = 0.80
SORTIE: list[str] = []
ECHECS: list[str] = []


def dire(s: str) -> None:
    SORTIE.append(s)
    print(s)


def controle(ok: bool, quoi: str) -> None:
    dire(("  tient : " if ok else "  TOMBE : ") + quoi)
    if not ok:
        ECHECS.append(quoi)


def lire_csv(p: pathlib.Path) -> list[dict]:
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# --- Le dessin radial ----------------------------------------------------------------------------------
def radial_juge() -> tuple[dict, dict, dict, list]:
    a = json.load(open(DUP / "arbre-c23.json", encoding="utf-8"))
    aretes = [(e["i"], e["j"], e["score_bits"]) for e in a["arbre"]]
    voisins: dict[int, list[tuple[float, int]]] = {}
    poids: dict[int, float] = {}
    for i, j, s in aretes:
        voisins.setdefault(i, []).append((s, j))
        voisins.setdefault(j, []).append((s, i))
        poids[i] = poids.get(i, 0) + s
        poids[j] = poids.get(j, 0) + s
    moyeu = max(poids, key=poids.get)
    parent, prof, enfants = {moyeu: None}, {moyeu: 0}, {}
    ordre = [moyeu]
    k = 0
    while k < len(ordre):
        u = ordre[k]
        k += 1
        enfants[u] = [w for s, w in sorted(voisins[u], key=lambda t: (-t[0], t[1])) if w not in parent]
        for w in enfants[u]:
            parent[w], prof[w] = u, prof[u] + 1
            ordre.append(w)
    feuilles: dict[int, int] = {}
    for u in reversed(ordre):
        feuilles[u] = 1 if not enfants[u] else sum(feuilles[w] for w in enfants[u])
    angle: dict[int, float] = {}
    pile = [(moyeu, math.pi / 2, math.pi / 2 - 2 * math.pi)]
    while pile:
        u, a0, a1 = pile.pop()
        angle[u] = (a0 + a1) / 2
        tot = sum(feuilles[w] + 1 for w in enfants[u])
        x = a0
        for w in enfants[u]:
            da = (a1 - a0) * (feuilles[w] + 1) / tot
            pile.append((w, x, x + da))
            x += da
    pos = {u: ((prof[u] + 1 if prof[u] else 0) * math.cos(angle[u]), (prof[u] + 1 if prof[u] else 0) * math.sin(angle[u]))
           for u in parent}
    return pos, prof, parent, aretes


def croise(p1, p2, q1, q2) -> bool:
    def o(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    d1, d2, d3, d4 = o(q1, q2, p1), o(q1, q2, p2), o(p1, p2, q1), o(p1, p2, q2)
    return (d1 * d2 < 0) and (d3 * d4 < 0)


def dist_point_segment(p, a, b) -> float:
    ax, ay = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / (ax * ax + ay * ay)))
    return math.hypot(a[0] + t * ax - p[0], a[1] + t * ay - p[1])


def dessin(casser: bool) -> None:
    dire("III-4.8, disposition radiale")
    pos, prof, parent, aretes = radial_juge()
    noeuds = lire_csv(DONNEES / "duplication-radial-noeuds.csv")
    ar = lire_csv(DONNEES / "duplication-radial-aretes.csv")
    if casser:
        noeuds[5]["x"] = f"{float(noeuds[5]['x']) + 0.01:.4f}"
    rng = random.Random(GRAINE + 0)
    n = rng.choice(noeuds)
    u = int(n["expert"])
    controle(abs(float(n["x"]) - pos[u][0]) < 1e-4 and abs(float(n["y"]) - pos[u][1]) < 1e-4
             and int(n["profondeur"]) == prof[u], f"point tiré : expert {u} ({n['x']}, {n['y']}), profondeur {n['profondeur']}")
    pire = max(max(abs(float(r["x"]) - pos[int(r["expert"])][0]), abs(float(r["y"]) - pos[int(r["expert"])][1]))
               for r in noeuds)
    controle(len(noeuds) == 32 and pire < 1e-4, f"32 experts, positions refaites par le juge (écart max {pire:.1e})")
    controle(all(int(r["profondeur"]) == prof[int(r["expert"])] for r in noeuds), "profondeurs")
    deg = {}
    for i, j, _ in aretes:
        deg[i] = deg.get(i, 0) + 1
        deg[j] = deg.get(j, 0) + 1
    controle(all(int(r["degre"]) == deg[int(r["expert"])] for r in noeuds), "degrés")
    controle([int(r["expert"]) for r in noeuds if r["moyeu"] == "1"] == [k for k in prof if prof[k] == 0], "moyeu")
    rng = random.Random(GRAINE + 1)
    e = rng.choice(ar)
    plein = {frozenset((i, j)): s for i, j, s in aretes}
    s = plein[frozenset((int(e["parent"]), int(e["enfant"])))]
    controle(f"{s:.5f}" == e["score"] and parent[int(e["enfant"])] == int(e["parent"]),
             f"arête tirée : {e['parent']} → {e['enfant']}, score {e['score']} (source {s:.10f})")
    smax = max(plein.values())
    ok = len(ar) == 31 and all(
        f"{plein[frozenset((int(r['parent']), int(r['enfant'])))]:.5f}" == r["score"]
        and parent[int(r["enfant"])] == int(r["parent"])
        and abs(float(r["rel"]) - plein[frozenset((int(r['parent']), int(r['enfant'])))] / smax) < 1e-4
        and abs(float(r["xp"]) - pos[int(r["parent"])][0]) < 1e-4 and abs(float(r["xe"]) - pos[int(r["enfant"])][0]) < 1e-4
        for r in ar)
    controle(ok, "31 arêtes : extrémités, sens parent → enfant, score, s/s_max")
    # Les croisements, sur le dessin du lot (pas le mien).
    P = {int(r["expert"]): (float(r["x"]), float(r["y"])) for r in noeuds}
    segs = [(int(r["parent"]), int(r["enfant"])) for r in ar]
    croisements = [(a, b) for k, a in enumerate(segs) for b in segs[k + 1:]
                   if not set(a) & set(b) and croise(P[a[0]], P[a[1]], P[b[0]], P[b[1]])]
    controle(not croisements, f"aucune arête n'en croise une autre ({len(croisements)} croisements : {croisements})")
    # Une arête qui passe sous un disque qu'elle ne touche pas (à l'échelle de la page).
    rayon = {int(r["expert"]): (0.40 + 0.035 * int(r["degre"])) / 2 for r in noeuds}
    marge = min((dist_point_segment(P[u], P[a], P[b]) * ECHELLE_CM - rayon[u], u, (a, b))
                for u in P for a, b in segs if u not in (a, b))
    controle(marge[0] > 0, f"aucune arête ne passe sous un disque étranger (marge minimale {marge[0]:.3f} cm : "
                           f"expert {marge[1]}, arête {marge[2]})")
    # Deux arêtes sans extrémité commune : leur plus petite distance (échantillonnée), à l'échelle de la page.
    def dist_segments(a, b) -> float:
        return min(min(dist_point_segment((P[a[0]][0] + t * (P[a[1]][0] - P[a[0]][0]),
                                           P[a[0]][1] + t * (P[a[1]][1] - P[a[0]][1])), P[b[0]], P[b[1]])
                       for t in [k / 50 for k in range(51)]),
                   min(dist_point_segment((P[b[0]][0] + t * (P[b[1]][0] - P[b[0]][0]),
                                           P[b[0]][1] + t * (P[b[1]][1] - P[b[0]][1])), P[a[0]], P[a[1]])
                       for t in [k / 50 for k in range(51)]))
    proche = min((dist_segments(a, b) * ECHELLE_CM, a, b) for k, a in enumerate(segs) for b in segs[k + 1:]
                 if not set(a) & set(b))
    dire(f"  mesuré : deux arêtes disjointes les plus proches : {proche[1]} et {proche[2]}, {proche[0]:.3f} cm")
    # La longueur visible des quatre arêtes les plus lourdes (hors des deux disques) : D5 du juge du premier flux.
    for r in sorted(ar, key=lambda r: -float(r["rel"]))[:4]:
        p, e = int(r["parent"]), int(r["enfant"])
        long = math.hypot(P[p][0] - P[e][0], P[p][1] - P[e][1]) * ECHELLE_CM - rayon[p] - rayon[e]
        dire(f"  mesuré : arête {p}–{e} (s/s_max {float(r['rel']):.3f}) visible sur {long:.2f} cm hors des disques")
    # Les étiquettes de valeur (liens > s_max / 4) : boîte de 0,52 × 0,26 cm centrée en (xm, ym).
    lw, lh = 0.52, 0.26
    touches = []
    for r in ar:
        if float(r["rel"]) <= 0.25:
            continue
        cx, cy = float(r["xm"]) * ECHELLE_CM, float(r["ym"]) * ECHELLE_CM
        for u, (x, y) in P.items():
            dx = max(abs(x * ECHELLE_CM - cx) - lw / 2, 0)
            dy = max(abs(y * ECHELLE_CM - cy) - lh / 2, 0)
            if math.hypot(dx, dy) < rayon[u]:
                touches.append((f"{r['parent']}-{r['enfant']}", f"disque {u}"))
        for a, b in segs:
            # la boîte est touchée si le segment passe à moins de la demi-diagonale réduite : test par échantillons
            for t in [k / 40 for k in range(41)]:
                x = (P[a][0] + t * (P[b][0] - P[a][0])) * ECHELLE_CM
                y = (P[a][1] + t * (P[b][1] - P[a][1])) * ECHELLE_CM
                if abs(x - cx) < lw / 2 and abs(y - cy) < lh / 2:
                    touches.append((f"{r['parent']}-{r['enfant']}", f"arête {a}-{b}"))
                    break
    dire(f"  mesuré : {sum(1 for r in ar if float(r['rel']) > 0.25)} étiquettes de valeur ; contacts estimés "
         f"(boîte {lw} × {lh} cm) : {touches}")


# --- Les queues de III-7.3 ----------------------------------------------------------------------------
def queues(casser: bool) -> None:
    dire("III-7.3, les deux queues")
    pb = lire_csv(ETAT / "journaux/kl-frontiere-positions.csv")
    ps = lire_csv(ETAT / "journaux/kl-synonyme-d1-positions.csv")
    kb = [float(r["kl"]) for r in pb]
    ks = [float(r["kl"]) for r in ps]
    n = len(kb)
    n1 = n // 100
    qb = sorted(range(n), key=lambda i: -kb[i])[:n1]
    qs = sorted(range(n), key=lambda i: -ks[i])[:n1]
    fmt = lambda i: (f"{max(kb[i], 1e-5):.6e}", f"{max(ks[i], 1e-5):.6e}")
    for k, (nom, q) in enumerate((("base", qb), ("syn", qs))):
        rows = lire_csv(DONNEES / f"synthese-queue-{nom}.csv")
        if casser and nom == "syn":
            rows = rows[:-1]
        rng = random.Random(GRAINE + 2 + k)
        r = rng.choice(rows)
        cible = {fmt(i) for i in q}
        controle((r["kl_base"], r["kl_syn"]) in cible, f"point tiré de la queue {nom} : ({r['kl_base']}, {r['kl_syn']})")
        controle(len(rows) == n1 and {(x["kl_base"], x["kl_syn"]) for x in rows} == cible,
                 f"queue {nom} : {len(rows)} lignes, les {n1} plus grandes positions")
    pos = lire_csv(DONNEES / "synthese-positions.csv")
    attendu = [(1 if i in set(qb) else 0) + (2 if i in set(qs) else 0) for i in range(n)]
    rng = random.Random(GRAINE + 4)
    i = rng.randrange(n)
    controle(pos[i]["queue"] == str(attendu[i]) and (pos[i]["kl_base"], pos[i]["kl_syn"]) == fmt(i),
             f"point tiré de synthese-positions.csv : ligne {i}, queue {pos[i]['queue']}")
    controle(len(pos) == n and [int(r["queue"]) for r in pos] == attendu, "colonne « queue » : 2 550 lignes")


# --- Les classes de III-7.1 et III-7.2 --------------------------------------------------------------------
def classes(casser: bool) -> None:
    dire("III-7.1 et III-7.2, classes et origine")
    juge = {r["cle"]: r for r in lire_csv(ICI / "journaux/classes2.csv")}
    fk = lire_csv(DONNEES / "synthese-frontiere-kl.csv")
    if casser:
        fk[5]["classe"] = "gagne"
    rng = random.Random(GRAINE + 5)
    r = rng.choice([x for x in fk if x["classe"] != "ref"])
    controle(juge[r["cle"]]["classe_juge"] == r["classe"], f"point tiré de III-7.1 : {r['cle']} {r['classe']}")
    ok = all((x["classe"] == "ref" and x["origine"] == "source") or
             (juge[x["cle"]]["classe_juge"] == x["classe"] and (x["origine"] == "regle") == (juge[x["cle"]]["d"] != ""))
             for x in fk)
    controle(ok and len(fk) == 12, "12 points : classe par la règle, origine « regle » si et seulement si une appariée existe")
    ek = lire_csv(DONNEES / "synthese-erreur-kl.csv")
    m = {"syn": "p1-syn", "sstar10": "p2-sstar", "kappa": "p3-kappa", "hebbe": "p3-hebbe",
         "hebbelc": "p3-hebbelc", "partse": "p3-partse"}
    rng = random.Random(GRAINE + 6)
    r = rng.choice([x for x in ek if x["cle"] in m])
    controle(juge[m[r["cle"]]]["classe_juge"] == r["classe"], f"point tiré de III-7.2 : {r['cle']} {r['classe']}")
    controle(all(x["classe"] == ("barre" if x["etat"] == "barre" else juge[m[x["cle"]]]["classe_juge"]) for x in ek)
             and len(ek) == 7, "7 points de III-7.2 : même classe que dans III-7.1, S* à 3 fenêtres barré")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--casser", action="store_true")
    a = ap.parse_args()
    dessin(a.casser)
    queues(a.casser)
    classes(a.casser)
    dire(f"contrôles tombés : {len(ECHECS)}")
    nom = "series2-casser.txt" if a.casser else "series2.txt"
    (ICI / "journaux" / nom).write_text("\n".join(SORTIE) + "\n", encoding="utf-8", newline="\n")
    if a.casser:
        return 0 if len(ECHECS) >= 3 else 1  # une perturbation, un contrôle qui tombe
    return 0 if not ECHECS else 1


if __name__ == "__main__":
    sys.exit(main())
