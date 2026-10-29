"""Résumé d'une série de la base (passes.csv de gptoss_base_serie.py) : moyenne, bruit, décision.

Pour chaque configuration et chaque grandeur : moyenne et extrêmes des passes retenues (échauffement
exclu), bruit = le plus grand |X1 - X2| / moyenne sur les paires symétriques d'un même palindrome
(règle de 06-modeles.md § 7.5). Pour chaque paire de configurations : la différence relative des
moyennes, et le verdict « réelle » si elle dépasse 2 × le plus grand des deux bruits ET 3 %.

Usage : python -I gptoss_base_resume.py <passes.csv> <resume.csv>
"""
import csv
import itertools
import statistics
import sys

GRANDEURS = ["generation_js", "prefill_js", "ensemble_travail_pointe_go", "ensemble_travail_final_go",
             "vram_pointe_mio", "disque_attribuable_go", "disque_par_jeton_genere_go", "cache_succes_pct"]


def nombre(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main():
    entree, sortie = sys.argv[1:3]
    lignes = [l for l in csv.DictReader(open(entree, encoding="utf-8")) if not l["config"].endswith("echauffement")]
    configs = list(dict.fromkeys(l["config"] for l in lignes))
    res = {}
    for c in configs:
        lc = [l for l in lignes if l["config"] == c]
        for g in GRANDEURS:
            v = [nombre(l[g]) for l in lc if nombre(l[g]) is not None]
            if not v:
                continue
            bruits = []
            for p in set(l["palindrome"] for l in lc):
                vp = [nombre(l[g]) for l in lc if l["palindrome"] == p and nombre(l[g]) is not None]
                if len(vp) == 2 and statistics.fmean(vp) != 0:
                    bruits.append(abs(vp[0] - vp[1]) / abs(statistics.fmean(vp)))
            res[(c, g)] = {"n": len(v), "moyenne": statistics.fmean(v), "min": min(v), "max": max(v),
                           "bruit": max(bruits) if bruits else None}
    out = []
    for (c, g), r in res.items():
        out.append({"config": c, "grandeur": g, "n": r["n"], "moyenne": round(r["moyenne"], 4),
                    "min": round(r["min"], 4), "max": round(r["max"], 4),
                    "bruit": None if r["bruit"] is None else round(r["bruit"], 4), "comparaison": ""})
    for a, b in itertools.combinations(configs, 2):
        for g in ("generation_js", "prefill_js"):
            ra, rb = res.get((a, g)), res.get((b, g))
            if not ra or not rb or ra["bruit"] is None or rb["bruit"] is None:
                continue
            d = (rb["moyenne"] - ra["moyenne"]) / ra["moyenne"]
            seuil = max(2 * max(ra["bruit"], rb["bruit"]), 0.03)
            out.append({"config": f"{b} contre {a}", "grandeur": g, "n": "", "moyenne": round(d, 4), "min": "", "max": "",
                        "bruit": round(seuil, 4), "comparaison": "réelle" if abs(d) > seuil else "dans le bruit"})
    with open(sortie, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    for o in out:
        if o["grandeur"] in ("generation_js", "prefill_js", "cache_succes_pct", "disque_par_jeton_genere_go"):
            print(o)


if __name__ == "__main__":
    main()
