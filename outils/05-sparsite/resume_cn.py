"""Résumé des séries ABBA de llama-bench (pp n, -n 0) : temps d'une passe de n
jetons, médiane des séries, bruit, et verdict contre le seuil déclaré.

Seuil déclaré avant lecture : une configuration n'est utilisable que si
l'écart-type relatif de llama-bench (sur ses 5 répétitions) est < 10 % dans
chaque série, et si l'écart entre séries A et B est < 2 fois ce bruit.
Sinon le chiffre est rapporté comme « indicatif ».

Usage : python -I resume_cn.py FICHIER.json [FICHIER.json ...]
"""
import json
import statistics
import sys


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    series = {}
    for f in sys.argv[1:]:
        for r in json.load(open(f, encoding="utf-8")):
            n = r["n_prompt"]
            t_ms = n / r["avg_ts"] * 1000
            bruit = r["stddev_ts"] / r["avg_ts"]
            series.setdefault(n, []).append((t_ms, bruit, f))
    t1 = statistics.median(t for t, _, _ in series[min(series)])
    print("n  médiane_ms  rapport_à_n=1  bruit_max  verdict")
    for n in sorted(series):
        ts = [t for t, _, _ in series[n]]
        b = max(b for _, b, _ in series[n])
        med = statistics.median(ts)
        ok = b < 0.10 and (max(ts) - min(ts)) / med < 2 * 0.10
        print(f"{n:4d} {med:9.1f} {med / t1:9.2f} {100 * b:8.0f} %  "
              f"{'utilisable' if ok else 'indicatif'}  séries {[round(t, 1) for t in ts]}")


if __name__ == "__main__":
    main()
