# Juge de la troisième passe : version rapide de croisements.py pour toutes les pages d'un PDF. Relève les segments
# droits tracés (get_drawings, éléments « l » à trait coloré, longueur ≥ 5 pt, hors gris très pâles des grilles)
# qui coupent la boîte précise d'un caractère (rawdict, TEXT_ACCURATE_BBOXES, rétrécie de 0,2 pt), par l'intersection
# exacte segment-rectangle (Liang-Barsky). Sort, par page, les paires (mot, segment). Sert à comparer deux états
# (second flux et troisième passe) et à trouver les chevauchements neufs.
# Usage : python -I -X utf8 croisements_vite.py PDF sortie.json [pages, ex. 4-14]
import json, sys
import fitz

pdf, sortie = sys.argv[1], sys.argv[2]
D = fitz.open(pdf)
if len(sys.argv) > 3:
    a, b = map(int, sys.argv[3].split("-"))
    pages = range(a, b + 1)
else:
    pages = range(1, D.page_count + 1)


def coupe(x0, y0, x1, y1, r):
    dx, dy = x1 - x0, y1 - y0
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x0 - r[0]), (dx, r[2] - x0), (-dy, y0 - r[1]), (dy, r[3] - y0)):
        if p == 0:
            if q < 0:
                return False
        else:
            t = q / p
            if p < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
            if t0 > t1:
                return False
    return True


res = {}
for n in pages:
    pg = D[n - 1]
    chars = []
    for bl in pg.get_text("rawdict", flags=fitz.TEXT_ACCURATE_BBOXES)["blocks"]:
        for l in bl.get("lines", []):
            for s in l["spans"]:
                mot = "".join(c["c"] for c in s["chars"]).strip()
                for c in s["chars"]:
                    r = c["bbox"]
                    if c["c"].strip() and r[2] - r[0] > 0.6 and r[3] - r[1] > 0.6:
                        chars.append(((r[0] + 0.2, r[1] + 0.2, r[2] - 0.2, r[3] - 0.2), mot[:40]))
    trouves = set()
    for d in pg.get_drawings():
        col = d.get("color")
        if col is None or min(col) > 0.8:
            continue
        for it in d["items"]:
            if it[0] != "l":
                continue
            p0, p1 = it[1], it[2]
            if abs(p1.x - p0.x) + abs(p1.y - p0.y) < 5:
                continue
            bx = (min(p0.x, p1.x), min(p0.y, p1.y), max(p0.x, p1.x), max(p0.y, p1.y))
            for r, mot in chars:
                if r[2] < bx[0] or r[0] > bx[2] or r[3] < bx[1] or r[1] > bx[3]:
                    continue
                if coupe(p0.x, p0.y, p1.x, p1.y, r):
                    trouves.add((mot, round(p0.x, 1), round(p0.y, 1), round(p1.x, 1), round(p1.y, 1),
                                 tuple(round(v, 2) for v in col)))
    res[n] = sorted(trouves)
json.dump({str(k): v for k, v in res.items()}, open(sortie, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(sum(len(v) for v in res.values()), "croisements sur", len(res), "pages")
