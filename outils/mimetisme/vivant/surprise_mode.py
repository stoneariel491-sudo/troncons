"""E-H : le signal de surprise prédit-il où le mode rapide perd de la KL ? Seuil : seuil-declare.md (ajout E-H)."""
import csv
import json
import statistics
import sys
from pathlib import Path

import numpy as np

DEPOT = Path(__file__).resolve().parents[3]
KL = DEPOT / "mesures" / "genome" / "construction" / "juge" / "kl"
FICHIERS = {"R1": "kl-r1-synonyme-l0-768-positions.csv", "neuf": "kl-neuf-moteur-rapide-l0-positions.csv"}


def lire(nom):
    with open(KL / nom, newline="") as f:
        lignes = list(csv.DictReader(f))
    return [(int(l["fenetre"]), int(l["position"]), float(l["kl"]), float(l["nll_q"])) for l in lignes]


def rangs(x):
    o = np.argsort(x, kind="stable")
    r = np.empty(len(x))
    r[o] = np.arange(len(x))
    return r


def spearman(a, b):
    ra, rb = rangs(a), rangs(b)
    return float(np.corrcoef(ra, rb)[0, 1])


def part_haut(signal, kl, frac=0.2):
    n = int(round(frac * len(kl)))
    idx = np.argsort(-signal, kind="stable")[:n]
    return float(kl[idx].sum() / kl.sum())


def signaux(lignes):
    """Signal pour la position i : surprise à i-1 ; moyenne des 4 dernières. Positions sans passé dans la fenêtre : écartées."""
    par_fen = {}
    for f, p, kl, nq in lignes:
        par_fen.setdefault(f, []).append((p, kl, nq))
    out = []
    for f, L in par_fen.items():
        L.sort()
        nq = [x[2] for x in L]
        for i in range(4, len(L)):
            out.append((f, L[i][1], nq[i - 1], float(np.mean(nq[i - 4:i]))))
    return out


def analyser(nom, rng):
    lignes = lire(FICHIERS[nom])
    s = signaux(lignes)
    fen = np.array([x[0] for x in s])
    kl = np.array([x[1] for x in s])
    sig1 = np.array([x[2] for x in s])
    sig4 = np.array([x[3] for x in s])
    res = {"n": len(kl), "kl_moyenne": float(kl.mean())}
    for cle, sig in (("surprise_i-1", sig1), ("moyenne_4", sig4)):
        res[cle] = {"spearman": spearman(sig, kl), "part_top20": part_haut(sig, kl)}
        pf = []
        for f in sorted(set(fen)):
            m = fen == f
            pf.append(part_haut(sig[m], kl[m]) > 0.2)
        res[cle]["fenetres_au_dessus_du_hasard"] = int(sum(pf))
        res[cle]["fenetres"] = len(pf)
    # témoins
    melange = rng.permutation(sig1)
    res["temoin_melange_part"] = part_haut(melange, kl)
    res["temoin_signal_egal_kl_part"] = part_haut(kl, kl)
    # cassure : signal décalé de 100 positions (circulaire sur la suite concaténée)
    res["cassure_decalage100_part"] = part_haut(np.roll(sig1, 100), kl)
    return res


if __name__ == "__main__":
    rng = np.random.default_rng(20261027)
    sortie = {nom: analyser(nom, rng) for nom in FICHIERS}
    ok = True
    for nom, r in sortie.items():
        for cle in ("surprise_i-1", "moyenne_4"):
            c = r[cle]
            passe = c["spearman"] >= 0.30 and c["part_top20"] >= 0.40 and c["fenetres_au_dessus_du_hasard"] >= 8
            c["passe"] = passe
    sortie["passe_surprise_i-1"] = all(sortie[n]["surprise_i-1"]["passe"] for n in FICHIERS)
    sortie["passe_moyenne_4"] = all(sortie[n]["moyenne_4"]["passe"] for n in FICHIERS)
    out = DEPOT / "mesures" / "mimetisme" / "vivant" / "eh.json"
    out.write_text(json.dumps(sortie, indent=1), encoding="utf-8")
    print(json.dumps(sortie, indent=1))
