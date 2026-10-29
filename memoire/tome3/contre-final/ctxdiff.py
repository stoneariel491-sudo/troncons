"""Contre-juge : chaque changement d'un flux de corrections, mot à mot, avec son contexte (8 mots avant, 6 après).

Usage : python -I -X utf8 ctxdiff.py DEPOT REV_A REV_B CHEMIN...
Les seuls passages de « 3.6\\% » à « 3.6\\,\\% » (M2) sont tus : ils sont comptés à part, pas montrés.
"""
import difflib
import subprocess
import sys

BS = "\\"
depot, a, b = sys.argv[1], sys.argv[2], sys.argv[3]


def montrer(rev, p):
    r = subprocess.run(["git", "-C", depot, "show", f"{rev}:{p}"], capture_output=True)
    return r.stdout.decode("utf-8").replace("\r\n", "\n")


tus = 0
for p in sys.argv[4:]:
    o, n = montrer(a, p).split(), montrer(b, p).split()
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, o, n, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        vieux, neuf = " ".join(o[i1:i2]), " ".join(n[j1:j2])
        if vieux.replace(BS + "%", BS + "," + BS + "%") == neuf:
            tus += 1
            continue
        avant, apres = " ".join(o[max(0, i1 - 8):i1]), " ".join(o[i2:i2 + 6])
        print(f"{p.split('/')[-1]}: ...{avant} [-{vieux}-]{{+{neuf}+}} {apres}...")
print(f"(passages du pour-cent à l'espace fine, tus : {tus})")
