"""Données des figures du chapitre 4 du Tome III (la duplication de gènes), tirées des fichiers commités de
mesures/genome/duplication/ (aucun chiffre recopié à la main).

Sources :
  csv/scores-parente.csv, paires-temoin-planter-0.5.json   III-4.2 : score de parenté par candidat ;
  arbre-c23.json                                           III-4.2 : le témoin du hasard de la couche 23
                                                           (8 paires ; M3 du juge ronde : le témoin se
                                                           trace sur la couche où il est mesuré) ;
  csv/phylogenie-c23-noeuds.csv, -aretes.csv, phylogenie-c23.json   III-4.8 : l'arbre des experts de la
                                                           couche 23 (arbre couvrant maximal ; MDS).

Écrit sous memoire/figures/tome3/donnees/ (virgule, fin de ligne LF) :
  duplication-scores-<genre>.csv   un point par candidat : x (position dans la bande de sa couche),
                                   score en bits, couche de l'enfant, enfant ;
  duplication-noeuds.csv           les 32 experts : x, y (MDS), degré dans l'arbre ;
  duplication-aretes.csv           les 31 arêtes : extrémités et score (épaisseur), positions MDS ;
  duplication-radial-noeuds.csv    les 32 experts dans la disposition d'arbre radiale (G8 du juge de
                                   design) : x, y, profondeur depuis le moyeu, degré, poids des arêtes ;
  duplication-radial-aretes.csv    les 31 arêtes dans cette disposition (parent, enfant, score, rel) ;
  duplication-nombres.csv          chaque nombre d'une légende ou d'une annotation.

La disposition radiale est un calcul de dessin, pas une mesure : le moyeu (l'expert dont les arêtes pèsent
le plus) au centre, chaque expert sur le cercle de sa profondeur dans l'arbre, chaque sous-arbre dans un
secteur proportionnel à son nombre de feuilles (les arêtes ne se croisent donc pas), les enfants rangés par
score décroissant. Second chemin : le degré de chaque expert est recompté depuis les arêtes.

  python -I -X utf8 memoire/outils/tome3_duplication.py
"""
from __future__ import annotations

import csv
import json
import math
import pathlib
import statistics

RACINE = pathlib.Path(__file__).resolve().parents[2]
M = RACINE / "mesures/genome/duplication"
D = RACINE / "memoire/figures/tome3/donnees"
NOMBRES: list[tuple[str, str, str]] = []
GENRES = ("intra", "voisine", "meme_indice")
DECALAGE = 1.0          # disposition radiale : le cercle de profondeur d a pour rayon d + DECALAGE (d ≥ 1)
ECART_ETIQUETTE = 0.32  # (second flux ; remplacé à la troisième passe par la place calculée ci-dessous)
# Troisième passe (DN7 du juge de design, N4 du juge ronde) : la valeur d'une arête lourde se pose là où sa
# boîte est le plus loin de tout autre trait. Grandeurs du dessin de duplication-figures.tex, en cm : une unité
# vaut 0,80 cm ; la boîte d'une valeur (« 0,089 » en \scriptsize, halo compris, avec une marge) 0,70 × 0,30 ;
# un trait d'arête 0,6 + 4,6 rel pt ; un disque 0,40 + 0,035 degré de diamètre ; seuil d'une arête lourde
# rel > 0,25 (le même que le .tex).
UNITE_CM, BOITE_CM, PT_CM, SEUIL_LOURDE = 0.80, (0.70, 0.30), 0.03515, 0.25


def nombre(cle: str, valeur: float, source: str, chiffres: int = 6) -> float:
    NOMBRES.append((cle, f"{valeur:.{chiffres}g}", source.replace(",", " ;")))  # pgfplotstable ne lit pas les guillemets
    return valeur


def ecrire(nom: str, entete: list[str], lignes: list[list]) -> None:
    with open(D / nom, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=",", lineterminator="\n")
        w.writerow(entete)
        w.writerows(lignes)


def lire_csv(chemin: pathlib.Path) -> list[dict]:
    with open(chemin, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def scores() -> None:
    src = "mesures/genome/duplication/csv/scores-parente.csv"
    rows = lire_csv(M / "csv/scores-parente.csv")
    couches = sorted({int(r["couche"]) for r in rows})
    enfants = {c: sorted({int(r["enfant"]) for r in rows if int(r["couche"]) == c}) for c in couches}
    # Position : une bande par couche (indice 0 à 3), une sous-bande par enfant, un décalage par genre ;
    # dans la sous-bande, les candidats sont rangés par score (un essaim déterministe, sans hasard).
    largeur_enfant = 0.8 / max(len(v) for v in enfants.values())
    decal = {"intra": -0.33, "voisine": 0.0, "meme_indice": 0.33}
    sortie = {g: [] for g in GENRES}
    for ic, c in enumerate(couches):
        for ie, e in enumerate(enfants[c]):
            for g in GENRES:
                pts = sorted((float(r["score_bits"]) for r in rows if int(r["couche"]) == c and int(r["enfant"]) == e
                              and r["genre"] == g))
                for k, s in enumerate(pts):
                    eta = (k / max(1, len(pts) - 1) - 0.5) if len(pts) > 1 else 0.0
                    x = ic - 0.4 + largeur_enfant * (ie + 0.5) + largeur_enfant * (decal[g] + 0.22 * eta)
                    sortie[g].append([f"{x:.4f}", f"{s:.6e}", c, e])
    for g in GENRES:
        ecrire(f"duplication-scores-{g}.csv", ["x", "score", "couche", "enfant"], sortie[g])
        v = [float(r["score_bits"]) for r in rows if r["genre"] == g]
        nombre(f"s-{g}-n", len(v), src)
        nombre(f"s-{g}-max", max(v), src)
        nombre(f"s-{g}-med", statistics.median(v), src)
    nombre("s-n", len(rows), src)
    nombre("s-couches", len(couches), src)
    for i, c in enumerate(couches):
        nombre(f"s-couche-{i}", c, src)
    nombre("s-enfants", len(enfants[couches[0]]), src)
    nombre("s-max", max(float(r["score_bits"]) for r in rows), src)
    nombre("s-min", min(float(r["score_bits"]) for r in rows), src)
    t = json.load(open(M / "paires-temoin-planter-0.5.json", encoding="utf-8"))
    ts = "mesures/genome/duplication/paires-temoin-planter-0.5.json"
    nombre("t-hasard", t["scores"]["hasard_moyen"], ts)
    nombre("t-plante-attendu", t["temoin_planter"]["gain_attendu"], ts)
    nombre("t-plante-mesure", t["temoin_planter"]["score_0_1"], ts)
    nombre("t-rho", t["temoin_planter"]["rho0"], ts)
    nombre("t-couche", t["arguments"]["couche"], ts)
    # Le témoin du hasard de la couche 23, où se trouve le plus grand score (M3 du juge ronde) : la figure
    # trace chaque témoin sur sa couche, et le rapport « au plus ×27 » se prend contre celui-là.
    a = json.load(open(M / "arbre-c23.json", encoding="utf-8"))
    sa = "mesures/genome/duplication/arbre-c23.json"
    assert a["arguments"]["couche"] == 23
    nombre("t23-hasard", a["scores"]["hasard_moyen"], sa)
    nombre("t23-paires", len(a["temoin_hasard"]), sa)
    nombre("t-paires", len(t["temoin_hasard"]), ts)
    rmax = max(rows, key=lambda r: float(r["score_bits"]))
    assert int(rmax["couche"]) == 23 and int(rmax["cand_couche"]) == 23, rmax
    nombre("s-max-enfant", int(rmax["enfant"]), src)
    nombre("s-max-parent", int(rmax["cand_expert"]), src)
    nombre("s-sur-hasard", float(rmax["score_bits"]) / a["scores"]["hasard_moyen"], src + " ; " + sa + " (calculé)")
    nombre("t-couche-bande", couches.index(23), src + " (rang de la couche 23 parmi les couches tracées)")
    # Le plancher de la couche 0 : ses candidats de même couche ont tous un score haut, porté par une
    # corrélation commune des colonnes de down (cos de down), pas par une parenté (M3).
    c0 = [r for r in rows if int(r["couche"]) == couches[0] and r["genre"] == "intra"]
    nombre("c0-n", len(c0), src)
    nombre("c0-score-min", min(float(r["score_bits"]) for r in c0), src)
    nombre("c0-score-max", max(float(r["score_bits"]) for r in c0), src)
    nombre("c0-cos-down-min", min(float(r["cos_down"]) for r in c0), src)
    nombre("c0-cos-down-max", max(float(r["cos_down"]) for r in c0), src)
    autres = [r for r in rows if int(r["couche"]) != couches[0]]
    nombre("autres-cos-down-med", statistics.median(float(r["cos_down"]) for r in autres), src + " (couches 8 ; 16 ; 23)")
    nombre("s-sous-plante", t["temoin_planter"]["gain_attendu"] / max(float(r["score_bits"]) for r in rows), src + " (calculé)")
    nombre("s-par-voisine", len([r for r in rows if r["genre"] == "voisine"]) // (len(couches) - 1) // len(enfants[couches[1]]),
           src + " (candidats de la couche précédente par enfant)")
    nombre("s-par-intra", len([r for r in rows if r["genre"] == "intra"]) // len(couches) // len(enfants[couches[0]]),
           src + " (candidats de la même couche par enfant)")


def arbre() -> None:
    sn = "mesures/genome/duplication/csv/phylogenie-c23-noeuds.csv"
    noeuds = lire_csv(M / "csv/phylogenie-c23-noeuds.csv")
    aretes = lire_csv(M / "csv/phylogenie-c23-aretes.csv")
    pj = json.load(open(M / "phylogenie-c23.json", encoding="utf-8"))
    sj = "mesures/genome/duplication/phylogenie-c23.json"
    assert len(aretes) == len(noeuds) - 1
    deg = {}
    for a in aretes:
        for k in ("i", "j"):
            deg[a[k]] = deg.get(a[k], 0) + 1
    for n in noeuds:
        assert deg[n["expert"]] == int(n["degre"]), n  # second chemin du degré, depuis les arêtes
    ecrire("duplication-noeuds.csv", ["expert", "x", "y", "degre"], [[n["expert"], n["x"], n["y"], n["degre"]] for n in noeuds])
    smax = max(float(a["score"]) for a in aretes)
    ecrire("duplication-aretes.csv", ["i", "j", "score", "xi", "yi", "xj", "yj", "rel"],
           [[a["i"], a["j"], a["score"], a["xi"], a["yi"], a["xj"], a["yj"], f"{float(a['score']) / smax:.4f}"] for a in aretes])
    nombre("a-experts", len(noeuds), sn)
    nombre("a-aretes", len(aretes), sn)
    nombre("a-paires", len(noeuds) * (len(noeuds) - 1) // 2, sn + " (calculé)")
    nombre("a-variance", pj["part_variance_plan"], sj)
    nombre("a-spearman", pj["spearman_plan_distances"], sj)
    nombre("a-temoin", pj["temoin_distances_permutees"], sj)
    nombre("a-smax", pj["s_max"], sj)
    assert abs(pj["s_max"] - smax) < 1e-4
    # Le moyeu, par le poids de ses arêtes (M4 du juge ronde : trois experts ont le degré maximal ; un seul
    # porte les arêtes les plus lourdes).
    poids: dict[str, float] = {}
    for a in aretes:
        for k in ("i", "j"):
            poids[a[k]] = poids.get(a[k], 0.0) + float(a["score"])
    dmax = max(deg.values())
    au_max = sorted((e for e in deg if deg[e] == dmax), key=int)
    moyeu = max(poids, key=lambda e: poids[e])
    second = max((e for e in au_max if e != moyeu), key=lambda e: poids[e])
    nombre("a-moyeu", int(moyeu), sn)
    nombre("a-moyeu-degre", deg[moyeu], sn)
    nombre("a-moyeu-poids", poids[moyeu], sn + " (calculé : somme des scores de ses arêtes)")
    nombre("a-degmax", dmax, sn)
    nombre("a-degmax-n", len(au_max), sn)
    for k, e in enumerate(au_max):
        nombre(f"a-degmax-{k}", int(e), sn)
    nombre("a-second", int(second), sn)
    nombre("a-second-poids", poids[second], sn + " (calculé)")
    lourdes = sorted(aretes, key=lambda a: -float(a["score"]))
    nombre("a-moyeu-lourdes", next(k for k, a in enumerate(lourdes) if moyeu not in (a["i"], a["j"])),
           sn + " (calculé : les k plus lourdes arêtes touchent toutes le moyeu)")
    nombre("a-score-min", min(float(a["score"]) for a in aretes), sn)
    nombre("a-feuilles", sum(1 for n in noeuds if int(n["degre"]) == 1), sn)
    a0 = lourdes[0]
    nombre("a-max-i", int(a0["i"]), sn)
    nombre("a-max-j", int(a0["j"]), sn)
    # Le témoin du hasard de la même couche (arbre-c23.json), pour l'échelle des liens.
    radial(noeuds, aretes, moyeu, deg, poids, smax)


def radial(noeuds: list[dict], aretes: list[dict], racine: str, deg: dict, poids: dict, smax: float) -> None:
    """La disposition d'arbre radiale (G8 du juge de design), voir l'en-tête."""
    voisins: dict[str, list[tuple[float, str]]] = {}
    for a in aretes:
        voisins.setdefault(a["i"], []).append((float(a["score"]), a["j"]))
        voisins.setdefault(a["j"], []).append((float(a["score"]), a["i"]))
    parent, prof, enfants = {racine: None}, {racine: 0}, {}
    file = [racine]
    while file:
        u = file.pop(0)
        enfants[u] = [v for _, v in sorted(voisins[u], key=lambda t: (-t[0], int(t[1]))) if v not in parent]
        for v in enfants[u]:
            parent[v], prof[v] = u, prof[u] + 1
            file.append(v)
    assert len(parent) == len(noeuds)  # l'arbre est connexe
    feuilles: dict[str, int] = {}

    def compter(u: str) -> int:
        feuilles[u] = 1 if not enfants[u] else sum(compter(v) for v in enfants[u])
        return feuilles[u]

    total = compter(racine)
    angle: dict[str, float] = {}
    # Le secteur d'un sous-arbre suit son nombre de feuilles plus un : un petit sous-arbre près du moyeu
    # garde de la place (sans le « plus un », les quatre voisins légers du moyeu se touchaient).
    poids_secteur = lambda v: feuilles[v] + 1

    def placer(u: str, a0: float, a1: float) -> None:
        angle[u] = (a0 + a1) / 2
        a = a0
        somme = sum(poids_secteur(v) for v in enfants[u])
        for v in enfants[u]:
            da = (a1 - a0) * poids_secteur(v) / somme
            placer(v, a, a + da)
            a += da

    # Le plus gros sous-arbre commence en haut, dans le sens horaire.
    placer(racine, math.pi / 2, math.pi / 2 - 2 * math.pi)
    rayon = lambda d: 0.0 if d == 0 else d + DECALAGE  # premier cercle plus loin : les arêtes lourdes se voient
    pos = {u: (rayon(prof[u]) * math.cos(angle[u]), rayon(prof[u]) * math.sin(angle[u])) for u in parent}
    ecrire("duplication-radial-noeuds.csv", ["expert", "x", "y", "profondeur", "degre", "poids", "moyeu"],
           [[u, f"{pos[u][0]:.4f}", f"{pos[u][1]:.4f}", prof[u], deg[u], f"{poids[u]:.5f}", int(u == racine)]
            for u in sorted(parent, key=int)])
    lignes = []
    # Les traits et les disques du dessin, en cm, pour placer les valeurs (troisième passe, voir l'en-tête).
    segs = []
    for a in aretes:
        p, e = (a["i"], a["j"]) if parent.get(a["j"]) == a["i"] else (a["j"], a["i"])
        rel = float(a["score"]) / smax
        segs.append(((p, e), [c * UNITE_CM for c in pos[p]], [c * UNITE_CM for c in pos[e]],
                     (0.6 + 4.6 * rel) * PT_CM / 2))
    disques = [([c * UNITE_CM for c in pos[u]], (0.40 + 0.035 * deg[u]) / 2) for u in parent]
    w2, h2 = BOITE_CM[0] / 2, BOITE_CM[1] / 2

    def dist_boite(cx: float, cy: float, px: float, py: float) -> float:
        """Distance d'un point au rectangle de la boîte centrée en (cx, cy) (0 dedans)."""
        return math.hypot(max(abs(px - cx) - w2, 0.0), max(abs(py - cy) - h2, 0.0))

    def jeu(cx: float, cy: float, posees: list) -> float:
        """Le plus petit jeu (cm) entre la boîte et tout autre trait, disque ou valeur déjà posée."""
        j = math.inf
        for _, a0, a1, demi in segs:
            for k in range(41):
                t = k / 40
                j = min(j, dist_boite(cx, cy, a0[0] + t * (a1[0] - a0[0]), a0[1] + t * (a1[1] - a0[1])) - demi)
        for c, r in disques:
            j = min(j, dist_boite(cx, cy, c[0], c[1]) - r)
        for qx, qy in posees:
            j = min(j, max(abs(qx - cx) - 2 * w2, abs(qy - cy) - 2 * h2))
        return j

    posees, jeux, place = [], [], {}
    # Les arêtes les plus lourdes (les plus épaisses) d'abord : elles choisissent leur place avant les autres.
    for (p, e), a0, a1, demi in sorted(segs, key=lambda s: -s[3]):
        if (demi * 2 / PT_CM - 0.6) / 4.6 <= SEUIL_LOURDE:
            continue
        dx, dy = a1[0] - a0[0], a1[1] - a0[1]
        n = math.hypot(dx, dy)
        ux, uy = dx / n, dy / n
        meilleur = None
        for k in range(4, 19):
            t = k / 20
            for cote in (1, -1):
                nx, ny = cote * uy, -cote * ux
                # l'écart qui sort la boîte de son propre trait : demi-étendue de la boîte sur la normale
                for plus in (0.05, 0.15, 0.25):
                    ecart = w2 * abs(nx) + h2 * abs(ny) + demi + plus
                    cx, cy = a0[0] + t * dx + ecart * nx, a0[1] + t * dy + ecart * ny
                    j = jeu(cx, cy, posees)
                    if meilleur is None or j > meilleur[0] + 1e-9:
                        meilleur = (j, cx, cy)
        posees.append(meilleur[1:])
        jeux.append(meilleur[0])
        print(f"  arête {p}-{e} : jeu {meilleur[0]:.3f} cm")
        place[(p, e)] = (meilleur[1] / UNITE_CM, meilleur[2] / UNITE_CM)
    for a in aretes:
        p, e = (a["i"], a["j"]) if parent.get(a["j"]) == a["i"] else (a["j"], a["i"])
        assert parent[e] == p
        rel = float(a["score"]) / smax
        mx, my = place.get((p, e), ((pos[p][0] + pos[e][0]) / 2, (pos[p][1] + pos[e][1]) / 2))
        lignes.append([p, e, a["score"], f"{pos[p][0]:.4f}", f"{pos[p][1]:.4f}", f"{pos[e][0]:.4f}", f"{pos[e][1]:.4f}",
                       f"{rel:.4f}", f"{mx:.4f}", f"{my:.4f}"])
    # La règle : aucune valeur ne touche un autre trait, un disque ou une autre valeur (jeu > 0) ; sinon on s'arrête.
    print(f"valeurs d'arêtes posées : {len(jeux)}, plus petit jeu {min(jeux):.3f} cm")
    assert min(jeux) > 0, "une valeur d'arête touche un trait, un disque ou une autre valeur"
    ecrire("duplication-radial-aretes.csv", ["parent", "enfant", "score", "xp", "yp", "xe", "ye", "rel", "xm", "ym"], lignes)
    sr = "calcul de dessin depuis mesures/genome/duplication/csv/phylogenie-c23-aretes.csv"
    nombre("r-decalage", DECALAGE, sr + " (rayon du cercle d de profondeur : d + r-decalage)")
    nombre("r-profondeur-max", max(prof.values()), sr)
    nombre("r-feuilles", total, sr)
    nombre("r-rayon-max", rayon(max(prof.values())), sr)


def main() -> int:
    D.mkdir(parents=True, exist_ok=True)
    scores()
    arbre()
    ecrire("duplication-nombres.csv", ["cle", "valeur", "source"], [list(n) for n in NOMBRES])
    for c, v, _ in NOMBRES:
        print(f"{c:22s} {v}")
    print("écrit :", sorted(p.name for p in D.glob("duplication-*.csv")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
