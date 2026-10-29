"""Les bascules de routage entre deux passes de la référence (lot R, R1, reprise du 2026-10-15).

Entrées : deux journaux de routage écrits par `juge reference --routage` (u32 couches, u32
positions aplaties, puis pour chaque couche et chaque position 4 × u8 experts et f32 marge entre le
4e et le 5e logit biaisé du routeur), et le CSV par position de `juge kl` entre les deux passes.

Ce que le script publie (mesure, non jugée) :
  - la part des (couche, position) dont l'ensemble des quatre experts diffère (« bascule ») ;
  - par position notée : la première couche qui bascule à cette position, et si une position
    antérieure de la même fenêtre a basculé (l'écart se propage aussi par le cache KV) ;
  - la KL moyenne des positions notées selon trois classes : aucune bascule jusqu'à elle dans sa
    fenêtre, bascule seulement à des positions antérieures, bascule à elle-même ;
  - la distribution des marges du routeur (quantiles) et la marge des (couche, position) qui
    basculent ; un CSV par position pour la figure.
Le seuil qui juge l'hypothèse des bascules est celui de l'expérience B (r1_reference.py) ; ce
script en donne la description, pas le verdict.

Usage : python -I -X utf8 bascules.py <routage_a.bin> <routage_b.bin> <kl.csv> <n_ctx> <sortie.csv>
"""

import csv
import json
import struct
import sys


def lire(chemin):
    o = open(chemin, "rb").read()
    couches, n = struct.unpack_from("<II", o, 0)
    assert len(o) == 8 + couches * n * 8, chemin
    experts, marges = [], []
    for l in range(couches):
        el, ml = [], []
        for p in range(n):
            d = 8 + (l * n + p) * 8
            el.append(frozenset(o[d:d + 4]))
            ml.append(struct.unpack_from("<f", o, d + 4)[0])
        experts.append(el)
        marges.append(ml)
    return couches, n, experts, marges


def quantiles(v, fs=(0.01, 0.1, 0.5, 0.9)):
    s = sorted(v)
    return {str(f): s[min(len(s) - 1, int(f * (len(s) - 1)))] for f in fs} if s else {}


def main():
    ra, rb, kl_csv, n_ctx, sortie = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
    ca, na, ea, ma = lire(ra)
    cb, nb, eb, mb = lire(rb)
    assert (ca, na) == (cb, nb)
    long_seq = n_ctx - 1  # positions évaluées par fenêtre (0 … n_ctx − 2)
    bascule = [[ea[l][p] != eb[l][p] for p in range(na)] for l in range(ca)]
    n_bascules = sum(sum(b) for b in bascule)
    marges_bascule = [ma[l][p] for l in range(ca) for p in range(na) if bascule[l][p]]
    toutes_marges = [ma[l][p] for l in range(ca) for p in range(na)]
    lignes = list(csv.DictReader(open(kl_csv, encoding="utf-8")))
    classes = {"aucune": [], "anterieure_seulement": [], "a_elle_meme": []}
    out = []
    for r in lignes:
        s, t, kl = int(r["fenetre"]), int(r["position"]), float(r["kl"])
        p = s * long_seq + t
        ici = [l for l in range(ca) if bascule[l][p]]
        avant = any(bascule[l][s * long_seq + u] for l in range(ca) for u in range(t))
        classe = "a_elle_meme" if ici else ("anterieure_seulement" if avant else "aucune")
        classes[classe].append(kl)
        marge_min = min(ma[l][p] for l in range(ca))
        out.append([s, t, kl, len(ici), ici[0] if ici else -1, int(avant), marge_min])
    with open(sortie, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["fenetre", "position", "kl", "couches_basculees", "premiere_couche", "bascule_anterieure", "marge_min"])
        w.writerows(out)
    total = sum(sum(v) for v in classes.values())
    print(json.dumps({
        "outil": "bascules.py",
        "entrees": [ra, rb, kl_csv],
        "couches_positions": ca * na,
        "bascules": n_bascules,
        "part_bascules": n_bascules / (ca * na),
        "positions_notees": len(lignes),
        "classes": {k: {"n": len(v), "kl_moyenne": (sum(v) / len(v)) if v else None,
                        "part_de_la_kl_totale": (sum(v) / total) if total else None} for k, v in classes.items()},
        "marges_toutes_quantiles": quantiles(toutes_marges),
        "marges_des_bascules_quantiles": quantiles(marges_bascule),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
