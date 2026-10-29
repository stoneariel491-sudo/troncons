"""Écran de parenté : chaque neurone d'un expert a-t-il un « gène parent » ailleurs dans le modèle ?

Hypothèse (duplication de gènes, idees/biomimetisme-genome-des-poids.md § 5 bis) : un expert est né
d'une copie d'un autre, puis a muté ; il resterait alors, pour chacun de ses neurones, un neurone
parent très corrélé dans un autre expert de la même couche ou de la couche voisine.

Ce que l'outil mesure, sans hypothèse sur l'ordre des neurones (donc à toute permutation près, et
même sans exiger qu'elle soit une bijection — c'est une BORNE HAUTE de ce qu'une parenté d'expert à
expert peut rendre) :
  pour chaque rangée cible x (rangée de gate, rangée de up, colonne de down : un « gène »), le
  meilleur parent p dans un dictionnaire D, ρ = max_p |cos(x, p)| ;
  le gain en bits d'un codage de x comme mutation de α·p plutôt que seul, pour une source gaussienne
  à distorsion égale (théorème de Shannon, D(R) = σ² 2^(−2R)) :  g(ρ) = −½ log₂(1 − ρ²) bit par poids ;
  la part d'énergie expliquée ρ².
Dictionnaires :
  intra    : les rangées de même rôle des 31 autres experts de la couche ;
  voisine  : les rangées de même rôle des 32 experts de la couche précédente ;
  meme     : l'expert de même indice dans la couche précédente (sans permutation : neurone i contre i).
Témoin de hasard (le bruit de l'estimateur) : le même dictionnaire, ses dimensions d'entrée
permutées au hasard (sa géométrie interne intacte, son lien avec la cible détruit). Tout ρ au
niveau du témoin n'est pas une parenté : c'est le maximum de N corrélations fortuites.
Témoin qui doit tomber (--planter) : la cible est remplacée par un descendant fabriqué,
x' = ρ₀ · P(parent) + √(1 − ρ₀²) · bruit (même énergie par rangée), P une permutation au hasard,
parent pris dans le dictionnaire intra ; l'écran doit rendre ρ ≈ ρ₀ et un gain ≈ g(ρ₀).

Utilisation :
  python -I -X utf8 ecran_parente.py --couches 0-23 --cibles 2 --rangees 960 [--planter 0.9]
         [--modele 20b|120b] > journal.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import experts as X  # noqa: E402


def normer(a: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(a, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return a / n


def rangees(ex: X.Experts, couche: int, role: str, expert: int) -> np.ndarray:
    """Les « gènes » d'un expert pour un rôle : rangées (gate, up) ou colonnes (down), (d_ff, ·)."""
    w = ex.poids(couche, role, expert)
    return w if role != "down" else np.ascontiguousarray(w.T)


def max_cos(cible: np.ndarray, dico: np.ndarray, paquet: int = 480) -> np.ndarray:
    m = np.empty(cible.shape[0], dtype=np.float32)
    for i in range(0, cible.shape[0], paquet):
        m[i:i + paquet] = np.abs(cible[i:i + paquet] @ dico.T).max(axis=1)
    return m


def resume(rho: np.ndarray) -> dict:
    r2 = np.minimum(rho.astype(np.float64) ** 2, 1 - 1e-12)
    g = -0.5 * np.log2(1 - r2)
    return {"rho_moyen": float(rho.mean()), "rho_median": float(np.median(rho)),
            "rho_p99": float(np.quantile(rho, 0.99)), "rho_max": float(rho.max()),
            "part_energie_expliquee": float(r2.mean()), "gain_bits_par_poids": float(g.mean()),
            "part_rangees_rho_sup_0_5": float((rho > 0.5).mean()),
            "part_rangees_rho_sup_0_9": float((rho > 0.9).mean())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--couches", default="0-23")
    ap.add_argument("--cibles", type=int, default=2, help="experts cibles par couche (tirés au hasard)")
    ap.add_argument("--rangees", type=int, default=960, help="rangées cibles par expert (tirées au hasard)")
    ap.add_argument("--planter", type=float, default=None, help="témoin : descendant fabriqué de corrélation ρ₀")
    ap.add_argument("--modele", default="20b")
    ap.add_argument("--graine", type=int, default=20261016)
    a = ap.parse_args()
    ex = X.Experts(X.FICHIER_20B if a.modele == "20b" else X.FICHIER_120B)
    if "-" in a.couches:
        d, f = a.couches.split("-")
        couches = list(range(int(d), int(f) + 1))
    else:
        couches = [int(c) for c in a.couches.split(",")]
    rng = np.random.default_rng(a.graine)
    sortie = {"outil": "ecran_parente.py", "modele": a.modele, "arguments": vars(a),
              "experts_par_couche": ex.nb_experts, "d_ff": ex.d_ff, "resultats": []}
    t0 = time.time()
    for L in couches:
        cibles = sorted(rng.choice(ex.nb_experts, size=a.cibles, replace=False).tolist())
        for role in X.ROLES:
            tous = [rangees(ex, L, role, e) for e in range(ex.nb_experts)]
            prec = [rangees(ex, L - 1, role, e) for e in range(ex.nb_experts)] if L > 0 else None
            perm_entree = rng.permutation(tous[0].shape[1])
            for c in cibles:
                sel = np.sort(rng.choice(tous[c].shape[0], size=min(a.rangees, tous[c].shape[0]), replace=False))
                dico_intra = normer(np.concatenate([tous[e] for e in range(ex.nb_experts) if e != c]))
                cible = tous[c][sel]
                if a.planter is not None:
                    # Descendant fabriqué : parent = un autre expert de la couche, neurones permutés.
                    autre = (c + 1) % ex.nb_experts
                    P = rng.permutation(tous[autre].shape[0])
                    parent = tous[autre][P][sel]
                    bruit = rng.standard_normal(parent.shape).astype(np.float32)
                    bruit *= np.linalg.norm(parent, axis=1, keepdims=True) / np.linalg.norm(bruit, axis=1, keepdims=True)
                    cible = a.planter * parent + math.sqrt(1 - a.planter ** 2) * bruit
                cible = normer(cible)
                ligne = {"couche": L, "role": role, "expert": c, "rangees": int(len(sel))}
                ligne["intra"] = resume(max_cos(cible, dico_intra))
                ligne["intra_temoin_hasard"] = resume(max_cos(cible, dico_intra[:, perm_entree]))
                del dico_intra
                if prec is not None:
                    dico_v = normer(np.concatenate(prec))
                    ligne["voisine"] = resume(max_cos(cible, dico_v))
                    ligne["voisine_temoin_hasard"] = resume(max_cos(cible, dico_v[:, perm_entree]))
                    del dico_v
                    meme = normer(prec[c][sel])
                    rho_meme = np.abs((cible * meme).sum(axis=1))
                    ligne["meme_indice_sans_permutation"] = resume(rho_meme)
                sortie["resultats"].append(ligne)
                print(f"couche {L} {role} expert {c} : intra ρ̄ {ligne['intra']['rho_moyen']:.3f} "
                      f"(hasard {ligne['intra_temoin_hasard']['rho_moyen']:.3f}) gain "
                      f"{ligne['intra']['gain_bits_par_poids']:.4f} b ; {time.time() - t0:.0f} s",
                      file=sys.stderr, flush=True)
            del tous, prec
    # Agrégats : moyenne sur toutes les lignes, par dictionnaire.
    agg = {}
    for cle in ("intra", "intra_temoin_hasard", "voisine", "voisine_temoin_hasard", "meme_indice_sans_permutation"):
        lignes = [r[cle] for r in sortie["resultats"] if cle in r]
        if lignes:
            agg[cle] = {k: float(np.mean([l[k] for l in lignes])) for k in lignes[0]}
    sortie["agregats"] = agg
    if a.planter is not None:
        attendu = -0.5 * math.log2(1 - a.planter ** 2)
        ok = abs(agg["intra"]["rho_moyen"] - a.planter) < 0.02 and abs(agg["intra"]["gain_bits_par_poids"] - attendu) < 0.1
        sortie["temoin_planter"] = {"rho0": a.planter, "gain_attendu": attendu, "retrouve": ok}
    sortie["duree_s"] = time.time() - t0
    print(json.dumps(sortie, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
