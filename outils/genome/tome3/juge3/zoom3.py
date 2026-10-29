# Juge de la troisième passe : rend une zone d'une page (en points PDF) à fort agrandissement par PyMuPDF (clip), en
# couleur, et, sur demande, en gris et en deutéranope côte à côte par les matrices de l'outil du premier juge de design
# (outils/genome/tome3/juge-design/palette.py, appelées sans modification, comme vues.py du second juge).
# Usage : python -I -X utf8 zoom3.py PDF PAGE DPI x0 y0 x1 y1 sortie.png [couleur,gris,deuter]
import contextlib, io, runpy, sys
from pathlib import Path
import fitz
import numpy as np
from PIL import Image

DEPOT = Path(__file__).resolve().parents[4]
pdf, page, dpi = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
x0, y0, x1, y1 = map(float, sys.argv[4:8])
sortie = sys.argv[8]
modes = sys.argv[9].split(",") if len(sys.argv) > 9 else ["couleur"]
pm = fitz.open(pdf)[page - 1].get_pixmap(dpi=dpi, clip=fitz.Rect(x0, y0, x1, y1), alpha=False)
im = Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
vues = []
if any(m != "couleur" for m in modes):
    argv0 = sys.argv
    sys.argv = ["palette.py"]
    with contextlib.redirect_stdout(io.StringIO()):
        J1 = runpy.run_path(str(DEPOT / "outils/genome/tome3/juge-design/palette.py"))
    sys.argv = argv0
    a = np.asarray(im).astype(np.float64) / 255.0
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
for m in modes:
    if m == "couleur":
        vues.append(im)
        continue
    if m == "gris":
        y = lin @ np.array([0.2126, 0.7152, 0.0722])
        l = np.repeat(y[..., None], 3, axis=2)
    else:
        l = np.clip(lin @ np.array(J1["MACHADO"][m]).T, 0, 1)
    s = np.where(l <= 0.0031308, 12.92 * l, 1.055 * l ** (1 / 2.4) - 0.055)
    vues.append(Image.fromarray((np.clip(s, 0, 1) * 255).round().astype(np.uint8)))
W, H = vues[0].size
out = Image.new("RGB", (W * len(vues) + 8 * (len(vues) - 1), H), (255, 0, 255))
for i, v in enumerate(vues):
    out.paste(v, (i * (W + 8), 0))
out.save(sortie)
print(sortie, out.size)
