# Juge de design du second flux (Tome III) : une zone d'une page en trois vues côte à côte, couleur, gris
# (luminance relative) et deutéranope (Machado, Oliveira et Fernandes 2009, sévérité 1, matrices de l'outil
# du premier juge, outils/genome/tome3/juge-design/palette.py, appelées sans modification).
# Usage : python -I -X utf8 vues.py PDF PAGE DPI x0 y0 x1 y1 sortie.png [modes, par défaut couleur,gris,deuter]
import contextlib, io, os, runpy, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
from PIL import Image

DEPOT = Path(__file__).resolve().parents[4]
argv0 = sys.argv
sys.argv = ["palette.py"]
with contextlib.redirect_stdout(io.StringIO()):
    J1 = runpy.run_path(str(DEPOT / "outils/genome/tome3/juge-design/palette.py"))
sys.argv = argv0
MACHADO = J1["MACHADO"]

pdf, page, dpi = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
x0, y0, x1, y1 = map(float, sys.argv[4:8])
sortie = sys.argv[8]
modes = sys.argv[9].split(",") if len(sys.argv) > 9 else ["couleur", "gris", "deuter"]
tmp = tempfile.mkdtemp()
base = os.path.join(tmp, "p")
subprocess.run(["pdftoppm", "-r", str(dpi), "-f", str(page), "-l", str(page), "-png", "-singlefile", pdf, base],
               check=True)
im = Image.open(base + ".png").convert("RGB")
w, h = im.size
im = im.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)))
a = np.asarray(im).astype(np.float64) / 255.0
lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
vues = []
for m in modes:
    if m == "couleur":
        vues.append(im)
        continue
    if m == "gris":
        y = lin @ np.array([0.2126, 0.7152, 0.0722])
        l = np.repeat(y[..., None], 3, axis=2)
    else:
        l = np.clip(lin @ np.array(MACHADO[m]).T, 0, 1)
    s = np.where(l <= 0.0031308, 12.92 * l, 1.055 * l ** (1 / 2.4) - 0.055)
    vues.append(Image.fromarray((np.clip(s, 0, 1) * 255).round().astype(np.uint8)))
W, H = vues[0].size
out = Image.new("RGB", (W * len(vues) + 8 * (len(vues) - 1), H), (255, 0, 255))
for i, v in enumerate(vues):
    out.paste(v, (i * (W + 8), 0))
out.save(sortie)
print(sortie, out.size)
