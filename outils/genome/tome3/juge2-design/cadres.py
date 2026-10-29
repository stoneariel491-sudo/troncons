# Juge de design du second flux (Tome III) : deux critères déclarés (JUGEMENT-figures2-design.md § 1.3), mesurés
# sur les fichiers commités, par un code à moi.
#   G8 (III-4.8) : nombre de croisements entre arêtes de l'arbre radial (segments droits entre nœuds), et la plus
#                  petite distance d'un nœud à une arête qui ne le touche pas (en unités du dessin).
#   G7 (III-9.6) : part de la largeur et de la hauteur (échelle log) du cadre couverte par les trois variantes,
#                  barres ± 2σ comprises.
# Témoin : un arbre en croix fabriqué (deux segments qui se croisent) doit donner 1 croisement ; --casser
# remplace le test d'intersection par « jamais », et le témoin doit tomber.
import csv, json, math, re, sys
from pathlib import Path

DEPOT = Path(__file__).resolve().parents[4]
D = DEPOT / "memoire/figures/tome3/donnees"
CASSER = "--casser" in sys.argv


def croise(p1, p2, p3, p4):
    if CASSER:
        return False
    def o(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    d1, d2, d3, d4 = o(p3, p4, p1), o(p3, p4, p2), o(p1, p2, p3), o(p1, p2, p4)
    return (d1 * d2 < 0) and (d3 * d4 < 0)


def dist_seg(p, a, b):
    ax, ay = b[0] - a[0], b[1] - a[1]
    t = max(0, min(1, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / (ax * ax + ay * ay)))
    return math.hypot(p[0] - a[0] - t * ax, p[1] - a[1] - t * ay)


sortie = {"casse": CASSER}
# Témoin.
sortie["temoin_croix"] = {"croisements": int(croise((0, 0), (1, 1), (0, 1), (1, 0)))}
sortie["temoin_croix"]["tient"] = sortie["temoin_croix"]["croisements"] == 1

# G8.
noeuds = {r["expert"]: (float(r["x"]), float(r["y"])) for r in csv.DictReader(open(D / "duplication-radial-noeuds.csv", encoding="utf-8"))}
lignes = list(csv.DictReader(open(D / "duplication-radial-aretes.csv", encoding="utf-8")))
cles = list(lignes[0].keys())
ka, kb = cles[0], cles[1]
aretes = [(r[ka], r[kb]) for r in lignes]
n = 0
for i in range(len(aretes)):
    for j in range(i + 1, len(aretes)):
        a, b = aretes[i]
        c, d = aretes[j]
        if len({a, b, c, d}) < 4:
            continue
        n += croise(noeuds[a], noeuds[b], noeuds[c], noeuds[d])
dmin = min((dist_seg(noeuds[k], noeuds[a], noeuds[b]), k, a, b) for k in noeuds for a, b in aretes if k not in (a, b))
sortie["G8"] = {"colonnes_aretes": cles, "aretes": len(aretes), "noeuds": len(noeuds), "croisements": n,
                "plus_proche_noeud_arete": {"distance": round(dmin[0], 3), "noeud": dmin[1], "arete": [dmin[2], dmin[3]]}}

# G7.
nb = (D / "synonyme-nombres.tex").read_text(encoding="utf-8")
v = {m.group(1): float(m.group(2)) for m in re.finditer(r"\\def\\SynoNVar(\w+)\{(-?[0-9.]+)\}", nb)}
xs = [v["FBits"], v["UnBits"], v["ZeroBits"]]
ys = []
for k in ("F", "Un", "Zero"):
    ys += [v[k + "KL"] - 2 * v[k + "Sf"], v[k + "KL"] + 2 * v[k + "Sf"]]
largeur = (max(xs) - min(xs)) / (v["Xmax"] - v["Xmin"])
hauteur = (math.log(max(ys)) - math.log(min(ys))) / (math.log(v["Ymax"]) - math.log(v["Ymin"]))
sortie["G7"] = {"cadre": [v["Xmin"], v["Xmax"], v["Ymin"], v["Ymax"]], "bits": xs, "kl_2sigma": [round(y, 4) for y in ys],
                "part_largeur": round(largeur, 3), "part_hauteur_log": round(hauteur, 3),
                "seuil_declare": "> 0,5 de la largeur", "tient": largeur > 0.5}
print(json.dumps(sortie, ensure_ascii=False, indent=1))
