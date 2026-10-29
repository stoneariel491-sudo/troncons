# Juge de la troisième passe : la zone de la figure d'une page de pilote (du haut du texte à la ligne « Figure n.m »),
# rendue par zoom3.py en couleur, gris et deutéranope côte à côte.
# Usage : python -I -X utf8 figure3.py PDF PAGE DPI sortie.png [modes] [--legende]  (--legende : la légende seule)
import subprocess, sys
from pathlib import Path
import fitz

pdf, page, dpi, sortie = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
modes = sys.argv[5] if len(sys.argv) > 5 and not sys.argv[5].startswith("--") else "couleur,gris,deuter"
pg = fitz.open(pdf)[page - 1]
hits = [fitz.Rect(b[:4]) for b in pg.get_text("blocks") if b[4].startswith("Figure ")]
haut = min(h.y0 for h in hits) if hits else pg.rect.y1
blocs = [b for b in pg.get_text("blocks") if b[3] < haut and b[1] > 30]
if "--legende" in sys.argv:
    zone = (50, haut - 3, pg.rect.x1 - 50, pg.rect.y1 - 40)
else:
    dessins = [d["rect"] for d in pg.get_drawings() if d["rect"].y1 < haut]
    y0 = min([r.y0 for r in dessins] + [b[1] for b in blocs] + [haut - 100]) - 4
    zone = (40, max(y0, 30), pg.rect.x1 - 40, haut + 2)
subprocess.run([sys.executable, "-I", "-X", "utf8", str(Path(__file__).with_name("zoom3.py")), pdf, str(page), dpi,
                *map(str, zone), sortie, modes], check=True)
