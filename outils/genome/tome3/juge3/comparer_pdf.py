# Juge de la troisième passe : compare deux PDF page à page, par les mots et leurs boîtes (PyMuPDF) et par l'image
# (rendu en gris à 50 dpi par PyMuPDF, le même moteur des deux côtés). Règles déclarées (JUGEMENT-figures3.md § 1.1) :
#   - mots : même suite de mots ; chaque boîte bouge de moins de 0,5 pt ; le carré « ■ » (et ses variantes) est
#     retiré des deux côtés et compté à part ;
#   - image : une page est différente à l'œil si plus de 0,05 % de ses pixels diffèrent de plus de 64 niveaux.
# Usage : python -I -X utf8 comparer_pdf.py A.pdf B.pdf sortie.json
import difflib, json, sys
import fitz
import numpy as np

CARRES = {"■", "□", "∎", "▪", "◼", "\U0001D7CE"}
a_pdf, b_pdf, sortie = sys.argv[1:4]
A, B = fitz.open(a_pdf), fitz.open(b_pdf)


def mots(page):
    out, carres = [], 0
    for x0, y0, x1, y1, w, *_ in page.get_text("words"):
        n = sum(w.count(c) for c in CARRES)
        carres += n
        for c in CARRES:
            w = w.replace(c, "")
        if w:
            out.append((w, x0, y0, x1, y1))
    return out, carres


def image(page):
    pm = page.get_pixmap(dpi=50, colorspace=fitz.csGRAY, alpha=False)
    return np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width).astype(np.int16)


res = {"a": a_pdf, "b": b_pdf, "pages_a": A.page_count, "pages_b": B.page_count, "pages": []}
for i in range(min(A.page_count, B.page_count)):
    ma, ca = mots(A[i])
    mb, cb = mots(B[i])
    ligne = {"page": i + 1, "carres_a": ca, "carres_b": cb}
    wa, wb = [m[0] for m in ma], [m[0] for m in mb]
    if wa == wb:
        dep = max((max(abs(p - q) for p, q in zip(x[1:], y[1:])) for x, y in zip(ma, mb)), default=0.0)
        ligne["mots"] = "egaux"
        ligne["deplacement_max_pt"] = round(dep, 3)
    else:
        sm = difflib.SequenceMatcher(a=wa, b=wb, autojunk=False)
        ops = [(t, wa[i1:i2], wb[j1:j2]) for t, i1, i2, j1, j2 in sm.get_opcodes() if t != "equal"]
        ligne["mots"] = "differents"
        ligne["ecarts"] = [(t, " ".join(x)[:80], " ".join(y)[:80]) for t, x, y in ops][:6]
        ligne["n_mots"] = (len(wa), len(wb))
    ia, ib = image(A[i]), image(B[i])
    if ia.shape != ib.shape:
        ligne["image"] = "tailles differentes"
    else:
        diff = np.abs(ia - ib) > 64
        ligne["part_pixels"] = round(float(diff.mean()) * 100, 4)
    egal_mots = ligne["mots"] == "egaux" and ligne["deplacement_max_pt"] < 0.5
    egal_image = ligne.get("part_pixels", 100) <= 0.05
    ligne["egale"] = bool(egal_mots and egal_image)
    res["pages"].append(ligne)
diff_pages = [l["page"] for l in res["pages"] if not l["egale"]]
res["pages_differentes"] = diff_pages
res["pages_differentes_par_mots"] = [l["page"] for l in res["pages"] if l["mots"] != "egaux" or l["deplacement_max_pt"] >= 0.5]
res["pages_differentes_par_image"] = [l["page"] for l in res["pages"] if l.get("part_pixels", 100) > 0.05]
res["carres"] = (sum(l["carres_a"] for l in res["pages"]), sum(l["carres_b"] for l in res["pages"]))
res["part_pixels_max"] = max(l.get("part_pixels", 100) for l in res["pages"])
open(sortie, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
print(json.dumps({k: res[k] for k in ("pages_a", "pages_b", "pages_differentes", "pages_differentes_par_mots",
                                      "pages_differentes_par_image", "carres", "part_pixels_max")}, ensure_ascii=False))
for l in res["pages"]:
    if not l["egale"]:
        print(json.dumps(l, ensure_ascii=False)[:600])
