"""Verdict F (fidélité de sortie) depuis le journal de `genome fidelite`.

Pour chaque expert et chaque variante (uniforme, pondérée) : l'erreur de sortie à 2,64 bits contre celle
de la base, les positions où la recette gagne, et les bits qu'il faut pour égaler l'erreur de sortie de
la base (interpolation linéaire en log(erreur) entre deux cibles voisines). Écrit csv/fidelite.csv et
un résumé JSON sur la sortie standard.

Utilisation : python -I -X utf8 analyse_fidelite.py JOURNAL.log CSV_SORTIE > verdict-fidelite.json
"""
import csv
import json
import math
import re
import sys
from collections import defaultdict

MOTIF = re.compile(r"couche (\d+) expert (\d+) (uniforme|pondérée) cible ([\d.]+) : ([\d.]+) b ; poids ([\d.]+) % ; sortie ([\d.]+) % \(base ([\d.]+) %\) ; (\d+)/(\d+)")


def main():
    journal, sortie_csv = sys.argv[1], sys.argv[2]
    pts = defaultdict(list)
    base = {}
    lignes = []
    for l in open(journal, encoding="utf8"):
        m = MOTIF.search(l)
        if not m:
            continue
        c, e, var, cible, bits, ep, es, eb, g, n = m.groups()
        cle = (int(c), int(e), var)
        pts[cle].append((float(bits), float(es) / 100, float(ep) / 100, int(g), int(n)))
        base[(int(c), int(e))] = float(eb) / 100
        lignes.append([c, e, var, cible, bits, float(ep) / 100, float(es) / 100, float(eb) / 100, g, n])
    with open(sortie_csv, "w", newline="", encoding="utf8") as f:
        w = csv.writer(f)
        w.writerow(["couche", "expert", "variante", "cible", "bits", "erreur_poids", "erreur_sortie", "erreur_sortie_base", "positions_gagnees", "positions"])
        w.writerows(lignes)
    res = []
    for (c, e, var), p in sorted(pts.items()):
        p.sort()
        eb = base[(c, e)]
        b_egal = float("nan")
        for (b0, e0, *_), (b1, e1, *_) in zip(p, p[1:]):
            if e0 >= eb >= e1:
                b_egal = b0 + (math.log(e0) - math.log(eb)) / (math.log(e0) - math.log(e1)) * (b1 - b0)
        a264 = [x for x in p if abs(x[0] - 2.64) < 0.01]
        res.append({"couche": c, "expert": e, "variante": var, "erreur_sortie_base": eb,
                    "bits_a_sortie_egale": b_egal,
                    "erreur_sortie_a_2_64": a264[0][1] if a264 else None,
                    "positions_gagnees_a_2_64": a264[0][3] if a264 else None,
                    "positions": a264[0][4] if a264 else None})
    par_var = defaultdict(list)
    for r in res:
        par_var[r["variante"]].append(r)
    verdict = {}
    for var, rs in par_var.items():
        gagnes = sum(1 for r in rs if r["erreur_sortie_a_2_64"] is not None and r["erreur_sortie_a_2_64"] < r["erreur_sortie_base"])
        bits = [r["bits_a_sortie_egale"] for r in rs if r["bits_a_sortie_egale"] == r["bits_a_sortie_egale"]]
        verdict[var] = {"experts": len(rs), "experts_gagnes_a_2_64": gagnes,
                        "bits_a_sortie_egale_moyenne": sum(bits) / len(bits) if bits else None,
                        "bits_a_sortie_egale_min": min(bits) if bits else None, "bits_a_sortie_egale_max": max(bits) if bits else None,
                        "rapport_erreur_sortie_a_2_64_moyen": sum(r["erreur_sortie_a_2_64"] / r["erreur_sortie_base"] for r in rs if r["erreur_sortie_a_2_64"]) / len(rs)}
    print(json.dumps({"journal": journal, "par_expert": res, "verdict": verdict}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
