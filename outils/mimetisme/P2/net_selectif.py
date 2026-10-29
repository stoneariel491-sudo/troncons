"""P2 : temps de service des défauts par jeton, 120b, R = 336 : LRU seul, exclusif simple (s=0), sélectif (s=1).
a = 4,1 ms (disque), b = 1,09 ms (RAM décodée et descente). Série : la descente s'ajoute ; recouvert : elle disparaît."""
import csv

B = "~/dev/active/troncons/mesures/mimetisme/P2"
a, b, T = 4.1, 1.09, 345.0
rows = {(r["trace"], r["R"], r["seuil_reutilisation"]): r for r in csv.DictReader(open(f"{B}/explore-selectif.csv", encoding="utf-8"))}
out = [["trace", "R", "s", "disque_par_jeton", "ram_par_jeton", "descentes_par_jeton", "base_ms", "serie_ms", "recouvert_ms",
        "gain_serie_ms", "gain_recouvert_ms", "descente_part_jeton"]]
for (t, R, s), r in sorted(rows.items()):
    if R != "336" or s not in ("0", "1"):
        continue
    ac = 144.0
    disq, ram, dem = float(r["part_disque"]) * ac, float(r["succes_ram"]) * ac, float(r["demotions_par_jeton"])
    base = (disq + ram) * a
    serie = disq * a + ram * b + dem * b
    rec = disq * a + ram * b
    out.append([t, R, s, round(disq, 2), round(ram, 2), round(dem, 2), round(base, 1), round(serie, 1), round(rec, 1),
                round(base - serie, 1), round(base - rec, 1), round(dem * b / T, 4)])
with open(f"{B}/net-selectif-120b.csv", "w", newline="", encoding="utf-8") as f:
    csv.writer(f).writerows(out)
for l in out:
    print(*l)
