# Juge de la troisième passe : sur une page de PDF, relève les traits dessinés (segments droits des chemins vectoriels,
# par PyMuPDF get_drawings) qui traversent la boîte d'un mot (get_text « words »), boîte rétrécie de 0,3 pt.
# Sert à G10 (le trait de la loupe de III-7.1) et à la recherche des chevauchements neufs. Écrit aussi, pour une zone
# donnée, la plus petite distance entre chaque segment et chaque mot (pour dire « à 2 mm »).
# Usage : python -I -X utf8 croisements.py PDF PAGE [x0 y0 x1 y1 (pt, zone)] [--min LONGUEUR_PT]
import json, math, sys
import fitz

pdf, page = sys.argv[1], int(sys.argv[2])
zone = tuple(map(float, sys.argv[3:7])) if len(sys.argv) >= 7 and not sys.argv[3].startswith("--") else None
LMIN = float(sys.argv[sys.argv.index("--min") + 1]) if "--min" in sys.argv else 4.0
P = fitz.open(pdf)[page - 1]
mots = [(fitz.Rect(w[:4]), w[4]) for w in P.get_text("words")]


def segs():
    for d in P.get_drawings():
        if d.get("color") is None:          # remplissage seul : pas un trait
            continue
        for it in d["items"]:
            if it[0] == "l":
                yield it[1], it[2], d
            elif it[0] == "c":
                yield it[1], it[4], d       # une courbe : sa corde (approximation)
            elif it[0] == "re" and False:
                pass


def coupe(a, b, r):
    """Le segment ab coupe-t-il le rectangle r ? (échantillonné finement)"""
    n = max(2, int(math.dist((a.x, a.y), (b.x, b.y)) / 0.2))
    for k in range(n + 1):
        t = k / n
        if r.contains(fitz.Point(a.x + t * (b.x - a.x), a.y + t * (b.y - a.y))):
            return True
    return False


def dist(a, b, r):
    n = max(2, int(math.dist((a.x, a.y), (b.x, b.y)) / 0.2))
    best = 1e9
    for k in range(n + 1):
        t = k / n
        x, y = a.x + t * (b.x - a.x), a.y + t * (b.y - a.y)
        dx = max(r.x0 - x, 0, x - r.x1)
        dy = max(r.y0 - y, 0, y - r.y1)
        best = min(best, math.hypot(dx, dy))
    return best


res = {"pdf": pdf, "page": page, "croisements": [], "proches": []}
for a, b, d in segs():
    L = math.dist((a.x, a.y), (b.x, b.y))
    if L < LMIN:
        continue
    if zone and not (zone[0] <= min(a.x, b.x) and max(a.x, b.x) <= zone[2] and zone[1] <= min(a.y, b.y)
                     and max(a.y, b.y) <= zone[3]):
        continue
    for r, w in mots:
        rr = fitz.Rect(r.x0 + 0.3, r.y0 + 0.3, r.x1 - 0.3, r.y1 - 0.3)
        if rr.is_empty:
            continue
        if coupe(a, b, rr):
            res["croisements"].append({"mot": w, "segment": [round(a.x, 1), round(a.y, 1), round(b.x, 1), round(b.y, 1)],
                                       "longueur_pt": round(L, 1), "couleur": d.get("color"), "largeur": d.get("width")})
        elif zone:
            dd = dist(a, b, r)
            if dd < 12:
                res["proches"].append({"mot": w, "distance_pt": round(dd, 2), "distance_mm": round(dd * 25.4 / 72, 2),
                                       "segment": [round(a.x, 1), round(a.y, 1), round(b.x, 1), round(b.y, 1)],
                                       "couleur": d.get("color")})
print(json.dumps(res, ensure_ascii=False, indent=1))
