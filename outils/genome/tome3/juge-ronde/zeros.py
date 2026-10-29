"""Juge du lot « ronde » : les nombres imprimés qui perdent un zéro final (fixed sans zerofill)."""
import csv
import os
import re
import sys
from decimal import Decimal, ROUND_HALF_UP

ICI = os.path.dirname(os.path.abspath(__file__))
R = os.path.normpath(os.path.join(ICI, "..", "..", "..", ".."))
sys.stdout.reconfigure(encoding="utf-8")
for lot, px in (("eclaireur", "ecl"), ("synthese", "synth"), ("genome", "gen"), ("duplication", "dup")):
    vals = {r["cle"]: float(r["valeur"]) for r in csv.DictReader(open(os.path.join(R, "memoire", "figures", "tome3", "donnees", f"{lot}-nombres.csv"), encoding="utf-8"))}
    t = open(os.path.join(R, "memoire", "figures", "tome3", f"{lot}-figures.tex"), encoding="utf-8").read()
    motif = "\\\\" + px + r"Nombre\[([^\]]*)\]\{([^}#]+)\}"
    for m in re.finditer(motif, t):
        opt, cle = m.group(1), m.group(2)
        mm = re.search(r"precision=(\d+)", opt)
        if not mm or "zerofill" in opt:
            continue
        p = int(mm.group(1))
        if p == 0:
            continue
        q = Decimal(repr(vals[cle])).quantize(Decimal(1).scaleb(-p), rounding=ROUND_HALF_UP)
        s = format(q, "f")
        if s.endswith("0"):
            print(f"{lot} {cle} precision {p} : valeur {vals[cle]} imprimée {s.rstrip('0').rstrip('.')} au lieu de {s}")
