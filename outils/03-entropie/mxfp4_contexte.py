"""Entropie des échelles E8M0 des tenseurs MXFP4, avec et sans contexte.

Pourquoi : dans un bloc MXFP4 (32 poids, 17 octets), l'échelle pèse 0,25 bit par poids.
La première mesure (lot de 32 Mio de gpt-oss-20b) lui trouve 2,27 bits d'entropie sur 8 :
coder l'échelle rend davantage que coder les codes. Reste à savoir combien un contexte
simple prend en plus, et lequel.

Pour chaque tenseur MXFP4 (forme ggml [colonnes, lignes, experts]) :
  - H(e)                      : ordre 0 ;
  - H(e | e_gauche)           : l'échelle du bloc précédent de la même ligne ;
  - H(e | e_haut)             : l'échelle du même bloc dans la ligne précédente ;
  - H(e | e_gauche, e_haut)   : les deux ;
  - H(e | moyenne de ligne)   : l'échelle sachant la médiane des échelles de sa ligne,
                                arrondie (un octet par ligne, coût compté à part) ;
  - H(code | e)               : les codes sachant l'échelle de leur bloc.
Les entropies conditionnelles sont des estimations par fréquences ; le biais
(K-1)/(2 N ln 2) est écrit pour la plus fine (deux contextes).

Témoin : un tenseur dont on remplace les échelles par une permutation aléatoire garde
H(e) et doit perdre tout le gain de contexte (H(e|gauche) ≈ H(e)) ; s'il ne le perd pas,
l'estimateur ment.

Usage : python mesure... mxfp4_contexte.py <fichier.gguf> <sortie.json> [--max-tenseurs N]
"""
from __future__ import annotations

import json
import sys
import time

import numpy as np

from gguf_lecture import LecteurGGUF


def h(cles: np.ndarray) -> float:
    _, n = np.unique(cles, return_counts=True)
    p = n / n.sum()
    return float(-(p * np.log2(p)).sum())


def h_cond(cible: np.ndarray, contexte: np.ndarray) -> float:
    """H(cible | contexte) = H(contexte, cible) - H(contexte), sur des entiers < 2^16."""
    return h(contexte.astype(np.int64) * 65536 + cible) - h(contexte)


def biais(cible: np.ndarray, contexte: np.ndarray) -> float:
    k = np.unique(contexte.astype(np.int64) * 65536 + cible).size
    return (k - 1) / (2 * cible.size * np.log(2))


def mesurer(e: np.ndarray, codes_h: np.ndarray | None) -> dict:
    """e : (lignes, blocs) u8 ; codes_h : histogramme joint (256 échelles × 16 codes) ou None."""
    gauche = e[:, :-1].ravel().astype(np.int64)
    ici_g = e[:, 1:].ravel().astype(np.int64)
    haut = e[:-1, :].ravel().astype(np.int64)
    ici_h = e[1:, :].ravel().astype(np.int64)
    g2 = e[1:, :-1].ravel().astype(np.int64)
    h2 = e[:-1, 1:].ravel().astype(np.int64)
    ici2 = e[1:, 1:].ravel().astype(np.int64)
    med = np.median(e, axis=1).round().astype(np.int64)
    med_b = np.repeat(med, e.shape[1])
    r = {
        "blocs": int(e.size), "lignes": int(e.shape[0]), "blocs_par_ligne": int(e.shape[1]),
        "H_e": h(e.ravel()),
        "H_e_sachant_gauche": h_cond(ici_g, gauche),
        "H_e_sachant_haut": h_cond(ici_h, haut),
        "H_e_sachant_gauche_haut": h_cond(ici2, g2 * 256 + h2),
        "biais_gauche_haut": biais(ici2, g2 * 256 + h2),
        "H_e_sachant_mediane_ligne": h_cond(e.ravel().astype(np.int64), med_b),
        "H_mediane_ligne_par_bloc": h(med) * e.shape[0] / e.size,
        "valeurs_distinctes": int(np.unique(e).size),
    }
    if codes_h is not None:
        joint = codes_h.reshape(256, 16)
        pj = joint[joint > 0] / joint.sum()
        pe = joint.sum(axis=1)
        pe = pe[pe > 0] / pe.sum()
        pc = joint.sum(axis=0)
        pc = pc[pc > 0] / pc.sum()
        r["H_code"] = float(-(pc * np.log2(pc)).sum())
        r["H_code_sachant_e"] = float(-(pj * np.log2(pj)).sum() + (pe * np.log2(pe)).sum())
    return r


def main():
    chemin, sortie = sys.argv[1], sys.argv[2]
    max_t = int(sys.argv[sys.argv.index("--max-tenseurs") + 1]) if "--max-tenseurs" in sys.argv else 10**9
    L = LecteurGGUF(chemin)
    res = []
    t0 = time.time()
    alea = np.random.default_rng(12345)
    temoin_fait = False
    for t in [t for t in L.tenseurs if t.nom_type == "MXFP4"][:max_t]:
        colonnes = t.dims[0]
        blocs_ligne = colonnes // 32
        brut = L.carte[t.decalage: t.decalage + t.nb_octets].reshape(-1, 17)
        e = np.ascontiguousarray(brut[:, 0]).reshape(-1, blocs_ligne)
        # histogramme joint (échelle, code), par paquets
        joint = np.zeros(256 * 16, np.int64)
        for i in range(0, brut.shape[0], 1 << 20):
            b = np.asarray(brut[i: i + (1 << 20)])
            ee = b[:, 0].astype(np.int64)[:, None] * 16
            joint += np.bincount((ee + (b[:, 1:] & 15)).ravel(), minlength=4096)
            joint += np.bincount((ee + (b[:, 1:] >> 4)).ravel(), minlength=4096)
        r = mesurer(e, joint)
        r["nom"] = t.nom
        r["dims"] = list(t.dims)
        res.append(r)
        print(f"{t.nom:30s} H(e)={r['H_e']:.3f} |g={r['H_e_sachant_gauche']:.3f} "
              f"|h={r['H_e_sachant_haut']:.3f} |gh={r['H_e_sachant_gauche_haut']:.3f} "
              f"|med={r['H_e_sachant_mediane_ligne']:.3f}+{r['H_mediane_ligne_par_bloc']:.4f} "
              f"H(c)={r['H_code']:.4f} H(c|e)={r['H_code_sachant_e']:.4f}", flush=True)
        if not temoin_fait:
            ep = alea.permutation(e.ravel()).reshape(e.shape)
            rt = mesurer(ep, None)
            temoin = {"nom": t.nom, "H_e": rt["H_e"], "H_e_sachant_gauche": rt["H_e_sachant_gauche"],
                      "H_e_sachant_gauche_haut": rt["H_e_sachant_gauche_haut"],
                      "biais_gauche_haut": rt["biais_gauche_haut"]}
            tombe = rt["H_e"] - rt["H_e_sachant_gauche"] < 0.01
            temoin["contexte_detruit"] = bool(tombe)
            print(f"témoin (échelles permutées) : H(e)={rt['H_e']:.3f} |g={rt['H_e_sachant_gauche']:.3f} "
                  f"|gh={rt['H_e_sachant_gauche_haut']:.3f} -> contexte détruit : {tombe}", flush=True)
            temoin_fait = True
    tot = sum(r["blocs"] for r in res)
    moy = {k: sum(r[k] * r["blocs"] for r in res) / tot for k in
           ("H_e", "H_e_sachant_gauche", "H_e_sachant_haut", "H_e_sachant_gauche_haut",
            "H_e_sachant_mediane_ligne", "H_mediane_ligne_par_bloc", "H_code", "H_code_sachant_e")}
    print("moyennes pondérées :", {k: round(v, 4) for k, v in moy.items()})
    with open(sortie, "w", encoding="utf-8") as f:
        json.dump({"fichier": chemin, "duree_s": time.time() - t0, "temoin_permutation": temoin,
                   "moyennes_ponderees": moy, "tenseurs": res}, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
