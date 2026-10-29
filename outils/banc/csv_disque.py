"""Extrait du journal du balayage disque (disque-balayage.jsonl) un CSV pour les figures du mémoire :
une ligne par cellule (accès, bloc, profondeur), débit et latence médiane aux passages A et B.

Le passage se déduit de l'ordre : la première occurrence d'une cellule du balayage est A, la
seconde B (ordre ABBA du pilote). Les passes de témoin et la comparaison IOCP/IoRing sont exclues.

Bibliothèque standard seulement. Usage :
  python -I -X utf8 outils/banc/csv_disque.py JOURNAL.jsonl SORTIE.csv
"""
import json
import sys

vu = {}
for l in open(sys.argv[1], encoding="utf-8"):
    d = json.loads(l)
    if d.get("genre") != "balayage" or d.get("moteur") != "iocp":
        continue
    cle = (d["acces"], int(d["bloc"]), int(d["qd"]))
    vu.setdefault(cle, []).append(d)
with open(sys.argv[2], "w", encoding="utf-8") as f:
    f.write("acces,bloc_o,qd,go_s_A,go_s_B,go_s_moy,bruit_rel,p50_us_A,p50_us_B,cpu_s_A,cpu_s_B\n")
    for (acces, bloc, qd), ds in sorted(vu.items()):
        if len(ds) < 2:
            continue
        a, b = ds[0], ds[1]
        m = (a["debit_go_s"] + b["debit_go_s"]) / 2
        f.write(f"{acces},{bloc},{qd},{a['debit_go_s']},{b['debit_go_s']},{m:.4f},{abs(a['debit_go_s'] - b['debit_go_s']) / m:.3f},"
                f"{a['lat_p50_us']},{b['lat_p50_us']},{a['cpu_s']},{b['cpu_s']}\n")
print(f"{sum(1 for v in vu.values() if len(v) >= 2)} cellules écrites")
