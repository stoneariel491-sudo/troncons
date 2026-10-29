"""Chaque chemin \\fichier{...} de l'article existe-t-il dans le dépôt ? (racine en argument 1, .tex en argument 2)"""
import glob
import re
import sys
from pathlib import Path

racine = Path(sys.argv[1])
texte = Path(sys.argv[2]).read_text(encoding="utf-8")
vus = sorted(set(re.findall(r"\\fichier\{([^}]*)\}", texte)))
absents = 0
for p in vus:
    q = p.replace(r"\_", "_")
    trouve = glob.glob(str(racine / q)) if ("*" in q) else ([q] if (racine / q).exists() else [])
    if not trouve:
        # un nom nu (sans dossier) : chercher où il est
        ou = [str(x.relative_to(racine)) for x in racine.rglob(Path(q).name)] if "/" not in q else []
        print(f"ABSENT {q}" + (f"  (trouvé sous : {ou[:3]})" if ou else ""))
        absents += 1
    else:
        print(f"ok     {q}")
print("absents :", absents)
