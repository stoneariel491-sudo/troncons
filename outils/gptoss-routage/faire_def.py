"""Tire un fichier .def (bibliothèque d'importation) de la sortie de « dumpbin /exports ».

Une ligne d'export de dumpbin a la forme « ordinal indice RVA nom » (trois nombres puis le nom) ;
toute autre ligne est ignorée. Usage : python -I faire_def.py exports.txt nom.dll sortie.def
"""
import re
import sys

entree, dll, sortie = sys.argv[1:4]
noms = []
for ligne in open(entree, encoding="utf-8", errors="replace"):
    m = re.match(r"^\s+\d+\s+[0-9A-Fa-f]+\s+[0-9A-Fa-f]{8}\s+(\S+)", ligne)
    if m:
        noms.append(m.group(1))
with open(sortie, "w", encoding="ascii") as f:
    f.write(f"LIBRARY {dll}\nEXPORTS\n")
    for n in noms:
        f.write(f"  {n}\n")
print(f"{dll} : {len(noms)} exports")
