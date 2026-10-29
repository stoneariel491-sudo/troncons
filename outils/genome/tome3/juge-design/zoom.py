# Rend une page d'un PDF à une résolution donnée et en découpe une zone (fractions de page).
# Usage : python zoom.py pdf page dpi x0 y0 x1 y1 sortie.png [mode]
# mode : couleur (défaut), gris (luminance), deuter, protan, tritan (simulation Machado 2009, sévérité 1).
import subprocess, sys, os, tempfile
import numpy as np
from PIL import Image

pdf, page, dpi = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
x0, y0, x1, y1 = map(float, sys.argv[4:8])
sortie = sys.argv[8]
mode = sys.argv[9] if len(sys.argv) > 9 else "couleur"
tmp = tempfile.mkdtemp()
base = os.path.join(tmp, "p")
subprocess.run(["pdftoppm", "-r", str(dpi), "-f", str(page), "-l", str(page), "-png", "-singlefile", pdf, base], check=True)
im = Image.open(base + ".png").convert("RGB")
w, h = im.size
im = im.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)))
MACHADO = {
    "protan": [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
    "deuter": [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
    "tritan": [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]],
}
if mode != "couleur":
    a = np.asarray(im).astype(np.float64) / 255.0
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    if mode == "gris":
        y = lin @ np.array([0.2126, 0.7152, 0.0722])
        lin = np.repeat(y[..., None], 3, axis=2)
    else:
        lin = np.clip(lin @ np.array(MACHADO[mode]).T, 0, 1)
    s = np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * lin ** (1 / 2.4) - 0.055)
    im = Image.fromarray((np.clip(s, 0, 1) * 255).round().astype(np.uint8))
im.save(sortie)
print(sortie, im.size)
