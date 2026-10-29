"""Différence appariée de deux passes KL (lot B, génome synonyme ; règle déclarée dans
mesures/genome/construction/synonyme/00-seuils-declares.md).

Écrit pour troncons, rôle « synonyme » de la construction, le 2026-10-17, sur la méthode de
outils/genome/synthese/frontiere.py (écart-type par blocs de fenêtres), refaite ici pour deux passes
quelconques de `juge kl` (CSV par position : fenetre, position, kl, meme_premier, nll_test, nll_base).

Pour chaque position i : d(i) = KL_b(i) − KL_a(i) ; e(i) = premier_b(i) − premier_a(i).
- σ naïf = écart-type de d / √n ;
- σ par fenêtres = écart-type des 10 moyennes par fenêtre / √10 (les positions d'une fenêtre
  partagent leur passé, donc leurs bascules ; R1 § 2.10).
Verdict (règle du lot R, critère B2 (i)) : b meilleure si d̄ + 2σ_fenêtres < 0 ; égale si
|d̄| ≤ 2σ_fenêtres ; pire si d̄ > 2σ_fenêtres.

Témoin : la KL moyenne de chaque CSV égale celle de son journal `juge kl` ~~à 1e-12~~ à 1e-9 en
valeur relative. Corrigé le 2026-10-17 à 11 h 35, après une chute sans cause (écarts de 9e-13 et
1,2e-12 sur des KL de 0,26 et 0,15) : le CSV du juge écrit 10 chiffres significatifs (%.9e), donc
chaque valeur porte une erreur relative d'au plus 5e-10, et la moyenne aussi ; le seuil absolu de
1e-12 ne valait que pour des KL de l'ordre de 0,03 (celles de l'éclaireur). La cassure (une ligne
retirée) déplace la moyenne de l'ordre de 1e-4 en relatif : elle tombe toujours.
Cassure (--casser) : le CSV de a amputé de sa première ligne ; le témoin doit tomber.

Usage : python -I -X utf8 apparier.py A.csv A-juge.json B.csv B-juge.json [--casser] > sortie.json
         [--csv-fenetres f.csv]  (moyennes par fenêtre, pour la figure)
"""
from __future__ import annotations

import csv
import json
import math
import sys

sys.stdout.reconfigure(encoding="utf-8")


def lire(chemin):
    with open(chemin, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def moy(v):
    return sum(v) / len(v)


def quantile(v, q):
    s = sorted(v)
    i = q * (len(s) - 1)
    a = int(math.floor(i))
    b = min(a + 1, len(s) - 1)
    return s[a] + (s[b] - s[a]) * (i - a)


def main():
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    casser = "--casser" in sys.argv
    csv_fen = sys.argv[sys.argv.index("--csv-fenetres") + 1] if "--csv-fenetres" in sys.argv else None
    if csv_fen:
        args.remove(csv_fen)
    ca, ja, cb, jb = args[:4]
    pa, pb = lire(ca), lire(cb)
    if casser:
        pa = pa[1:]
    ka = [float(r["kl"]) for r in pa]
    kb = [float(r["kl"]) for r in pb]
    juge_a = json.load(open(ja, encoding="utf-8"))["resume"]["kl_moyenne"]
    juge_b = json.load(open(jb, encoding="utf-8"))["resume"]["kl_moyenne"]
    temoin = {"kl_a_recalculee": moy(ka), "kl_a_juge": juge_a, "kl_b_recalculee": moy(kb), "kl_b_juge": juge_b}
    temoin["tient"] = abs(moy(ka) / juge_a - 1) < 1e-9 and abs(moy(kb) / juge_b - 1) < 1e-9
    if not temoin["tient"]:
        print(json.dumps({"temoin": temoin, "cassure": casser, "cassure_tombe": casser}, ensure_ascii=False, indent=1))
        sys.exit(0 if casser else 1)
    if casser:
        print(json.dumps({"temoin": temoin, "cassure": True, "cassure_tombe": False, "message": "l'instrument ne sait pas tomber"}, ensure_ascii=False, indent=1))
        sys.exit(1)
    cles = [(r["fenetre"], r["position"]) for r in pa]
    assert cles == [(r["fenetre"], r["position"]) for r in pb], "positions non alignées"
    n = len(ka)
    d = [y - x for x, y in zip(ka, kb)]
    dm = moy(d)
    sd = math.sqrt(sum((x - dm) ** 2 for x in d) / (n - 1))
    fen = sorted({r["fenetre"] for r in pa}, key=int)
    par_fen = []
    for f in fen:
        idx = [i for i, r in enumerate(pa) if r["fenetre"] == f]
        par_fen.append({"fenetre": int(f), "positions": len(idx), "kl_a": moy([ka[i] for i in idx]), "kl_b": moy([kb[i] for i in idx]),
                        "d": moy([d[i] for i in idx])})
    mf = [x["d"] for x in par_fen]
    sd_fen = math.sqrt(sum((x - moy(mf)) ** 2 for x in mf) / (len(mf) - 1)) / math.sqrt(len(mf))
    ta = [int(r["meme_premier"]) for r in pa]
    tb = [int(r["meme_premier"]) for r in pb]
    e = [y - x for x, y in zip(ta, tb)]
    em = moy(e)
    se = math.sqrt(sum((x - em) ** 2 for x in e) / (n - 1)) / math.sqrt(n)
    nll = lambda p, k: moy([float(r[k]) for r in p])
    verdict = "meilleure" if dm + 2 * sd_fen < 0 else ("pire" if dm > 2 * sd_fen else "égale")
    q = lambda v: {"mediane": quantile(v, 0.5), "p90": quantile(v, 0.9), "p99": quantile(v, 0.99), "p999": quantile(v, 0.999), "max": max(v)}
    sortie = {
        "outil": "outils/genome/synonyme/apparier.py", "a": ca, "b": cb, "positions": n, "temoin": temoin,
        "kl_a": moy(ka), "kl_b": moy(kb), "rapport_b_sur_a": moy(kb) / moy(ka),
        "quantiles_a": q(ka), "quantiles_b": q(kb),
        "d_moyenne_b_moins_a": dm, "ecart_type_naif": sd / math.sqrt(n), "ecart_type_par_fenetres": sd_fen, "fenetres": len(fen),
        "positions_ou_b_a_moins_de_kl": sum(1 for x in d if x < 0),
        "premier_a": moy(ta), "premier_b": moy(tb), "premier_difference_b_moins_a": em, "premier_ecart_type": se,
        "ppl_a": math.exp(nll(pa, "nll_test")), "ppl_b": math.exp(nll(pb, "nll_test")), "ppl_reference": math.exp(nll(pa, "nll_base")),
        "regle": "b meilleure si d̄ + 2σ_fenêtres < 0 ; égale si |d̄| ≤ 2σ_fenêtres ; pire sinon",
        "verdict_b_contre_a": verdict, "par_fenetre": par_fen,
    }
    if csv_fen:
        with open(csv_fen, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["fenetre", "positions", "kl_a", "kl_b", "d"])
            w.writeheader()
            w.writerows(par_fen)
    print(json.dumps(sortie, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
