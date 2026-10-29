"""P3 : découpe affinage.csv en séries pour pgfplots (une par variante et budget, bêta positifs jusqu'à 1, triés), défauts évités en % du compte à bêta = 0."""
import csv
import os

ICI = os.path.dirname(os.path.abspath(__file__))
D = os.path.normpath(os.path.join(ICI, "..", "..", "..", "mesures", "mimetisme", "P3"))
rows = list(csv.DictReader(open(os.path.join(D, "affinage.csv"), encoding="utf-8")))
for v in ("V1", "V2"):
    for b in ("19", "31"):
        s = sorted((r for r in rows if r["variante"] == v and r["budget"] == b and 0 < float(r["beta"]) <= 1.0), key=lambda r: float(r["beta"]))
        with open(os.path.join(D, "series", f"{v}-{b}.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["beta", "cellules_pct", "evites_pct", "kl_prior"])
            for r in s:
                ev = -float(r["variation_relative"]) * 100
                w.writerow([r["beta"], f"{float(r['part_cellules_changees']) * 100:.4f}", f"{ev:.4f}", f"{float(r['kl_prior']):.5f}"])
