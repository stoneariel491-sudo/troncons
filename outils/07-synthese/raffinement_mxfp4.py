"""Raffinement exact d'un format MXFP4 natif : ce que coûte et ce que vaut une couche de base.

Question (étude 07, architecture B) : on range chaque code E2M1 (4 bits : signe,
exposant 2 bits, mantisse 1 bit) en deux couches, une **base** B = f(code) qui donne
une reconstruction grossière, et un **complément** qui rend le code exact. Comme B
est une fonction du code, H(code) = H(B) + H(code | B) : la somme des deux couches
ne coûte rien de plus que le codage sans perte d'un seul tenant (à l'écart près
entre le codeur réel et l'entropie). Un défaut de lecture peut alors ne lire que
la base, et un expert résident lit les deux.

Ce que l'outil mesure, sur les experts MXFP4 réels d'un GGUF gpt-oss :
  - la loi conjointe (échelle E8M0, code) de chaque tenseur, comptée exactement ;
  - pour toute partition des 8 magnitudes E2M1 en 2 classes (base = signe + 1 bit)
    ou en 4 classes (base = signe + 2 bits) : H(B), H(code | B), et l'erreur
    quadratique relative de la reconstruction par la base (centre de gravité de
    chaque classe, pondéré par le carré de l'échelle, donc optimal dans le domaine
    réel) ; on garde la meilleure partition, et la troncature des bits de poids
    faible (le geste des codes « Matryoshka ») pour comparaison ;
  - une référence : l'erreur relative du MXFP4 lui-même sur une source gaussienne
    (blocs de 32, échelle de la spécification OCP), pour dire l'ordre de grandeur du
    bruit que le format porte déjà.

Témoins :
  - identité de la chaîne : H(B) + H(code | B) doit égaler H(code) à 1e-9 près ;
  - la partition « identité » (8 classes) doit donner une erreur nulle ;
  - cassure (--casser) : la reconstruction lit la mauvaise classe (décalage d'une
    classe) ; la partition identité ne rend alors plus une erreur nulle et le témoin
    doit tomber.

Utilisation :
  python -I -X utf8 outils/07-synthese/raffinement_mxfp4.py [--casser] > journal.json
"""
from __future__ import annotations

import importlib.util
import itertools
import json
import math
import os
import sys

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
LECTEUR = os.path.join(ICI, "..", "03-entropie", "gguf_lecture.py")
FICHIER = "~/dev/modeles/gguf/gpt-oss-20b-MXFP4.gguf"
COUCHES = (0, 8, 16, 23)  # quatre profondeurs ; les trois rôles de chacune
ROLES = ("ffn_gate_exps", "ffn_up_exps", "ffn_down_exps")

# Magnitudes E2M1 doublées, par indice m = code & 7 (ggml : kvalues_mxfp4).
MAG = np.array([0, 1, 2, 3, 4, 6, 8, 12], dtype=np.float64)


def charger_lecteur():
    spec = importlib.util.spec_from_file_location("gguf_lecture", LECTEUR)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gguf_lecture"] = mod
    spec.loader.exec_module(mod)
    return mod


def compter(octets: np.ndarray) -> np.ndarray:
    """Compte C[e, q] : blocs MXFP4 (17 octets : e, puis 16 octets de demi-octets)."""
    blocs = octets.reshape(-1, 17)
    e = blocs[:, 0].astype(np.int64)
    qs = blocs[:, 1:]
    codes = np.concatenate([qs & 15, qs >> 4], axis=1).astype(np.int64)  # (n, 32)
    cle = (e[:, None] * 16 + codes).ravel()
    return np.bincount(cle, minlength=256 * 16).reshape(256, 16).astype(np.float64)


def entropie(p: np.ndarray) -> float:
    p = p[p > 0]
    p = p / p.sum()
    return float(-(p * np.log2(p)).sum())


def evaluer(C: np.ndarray, classes: list[int], casser: bool = False) -> dict:
    """classes[m] = indice de classe de la magnitude m (0..7). Le signe est gardé."""
    emax = int(np.nonzero(C.sum(axis=1))[0].max())
    w = 4.0 ** (np.arange(256) - emax)              # carré relatif de l'échelle
    Wq = (C * w[:, None]).sum(axis=0)                # poids pondérés par code q
    Wm = Wq[:8] + Wq[8:]                             # par magnitude (signe confondu)
    nq = C.sum(axis=0)                               # comptes par code
    K = max(classes) + 1
    cls = np.array(classes)
    centres = np.zeros(K)
    for k in range(K):
        sel = cls == k
        tot = Wm[sel].sum()
        centres[k] = (Wm[sel] * MAG[sel]).sum() / tot if tot > 0 else 0.0
    lus = (cls + 1) % K if casser else cls          # cassure : mauvaise classe
    err = float((Wm * (MAG - centres[lus]) ** 2).sum())
    energie = float((Wm * MAG ** 2).sum())
    # Symbole de base : (signe, classe).
    base = np.zeros(2 * K)
    for q in range(16):
        base[(q >> 3) * K + classes[q & 7]] += nq[q]
    h_code = entropie(nq)
    h_base = entropie(base)
    # H(code | base) calculé directement, pour vérifier la chaîne.
    h_cond = 0.0
    total = nq.sum()
    for s in range(2):
        for k in range(K):
            qs = [q for q in range(16) if (q >> 3) == s and classes[q & 7] == k]
            n = nq[qs].sum()
            if n > 0:
                h_cond += n / total * entropie(nq[qs])
    return {"classes": classes, "centres": [round(float(c), 4) for c in centres],
            "erreur_relative": float(err / energie), "H_code": h_code, "H_base": h_base,
            "H_code_sachant_base": h_cond, "ecart_chaine": float(h_base + h_cond - h_code)}


def partitions(K: int):
    """Partitions des 8 magnitudes ordonnées en K intervalles contigus."""
    for coupes in itertools.combinations(range(1, 8), K - 1):
        bornes = (0,) + coupes + (8,)
        cl = []
        for k in range(K):
            cl += [k] * (bornes[k + 1] - bornes[k])
        yield cl


def reference_gaussienne(n_blocs: int = 1 << 16, graine: int = 1) -> dict:
    """Erreur relative du MXFP4 sur une gaussienne (OCP MX v1.0 : échelle 2^(floor(log2 amax) - 2))."""
    rng = np.random.default_rng(graine)
    x = rng.standard_normal((n_blocs, 32))
    amax = np.abs(x).max(axis=1, keepdims=True)
    echelle = 2.0 ** (np.floor(np.log2(amax)) - 2)
    y = np.abs(x) / echelle
    niveaux = MAG / 2                                  # 0 .. 6
    idx = np.abs(y[..., None] - niveaux).argmin(axis=-1)
    q = np.sign(x) * niveaux[idx] * echelle
    return {"blocs": n_blocs, "erreur_relative_mxfp4": float(((x - q) ** 2).sum() / (x ** 2).sum())}


def main():
    casser = "--casser" in sys.argv
    mod = charger_lecteur()
    lec = mod.LecteurGGUF(FICHIER)
    noms = {f"blk.{c}.{r}.weight" for c in COUCHES for r in ROLES}
    C_tot = np.zeros((256, 16))
    par_tenseur = []
    for t in lec.tenseurs:
        if t.nom not in noms:
            continue
        if t.nom_type != "MXFP4":
            raise SystemExit(f"{t.nom} n'est pas en MXFP4 ({t.nom_type})")
        C = compter(np.asarray(lec.octets(t)))
        C_tot += C
        meill2 = min((evaluer(C, cl) for cl in partitions(2)), key=lambda d: d["erreur_relative"])
        par_tenseur.append({"nom": t.nom, "poids": int(C.sum()),
                            "H_code": meill2["H_code"],
                            "base_1bit_meilleure": meill2})
    resultats = {}
    for K, nom in ((2, "base_signe_plus_1_bit"), (4, "base_signe_plus_2_bits")):
        toutes = [evaluer(C_tot, cl) for cl in partitions(K)]
        meilleure = min(toutes, key=lambda d: d["erreur_relative"])
        resultats[nom] = {"meilleure": meilleure,
                          "toutes": sorted(toutes, key=lambda d: d["erreur_relative"])}
    troncature = {
        "sans_mantisse (signe + exposant, 8 niveaux)": evaluer(C_tot, [0, 0, 1, 1, 2, 2, 3, 3]),
        "sans_mantisse_ni_bit_bas_exposant (4 niveaux)": evaluer(C_tot, [0, 0, 0, 0, 1, 1, 1, 1]),
    }
    identite = evaluer(C_tot, list(range(8)), casser=casser)
    temoins = {
        "chaine_exacte": bool(max(abs(r["meilleure"]["ecart_chaine"]) for r in resultats.values()) < 1e-9),
        "identite_erreur_nulle": bool(identite["erreur_relative"] < 1e-12),
    }
    sortie = {
        "etude": "07-synthese", "fichier": FICHIER, "couches": COUCHES, "roles": ROLES,
        "casser": casser, "poids_comptes": int(C_tot.sum()),
        "H_code_total": entropie(C_tot.sum(axis=0)),
        "resultats": resultats, "troncature": troncature, "identite": identite,
        "temoins": temoins,
        "temoins_tiennent": all(temoins.values()),
        "reference_gaussienne": reference_gaussienne(),
        "par_tenseur": par_tenseur,
    }
    json.dump(sortie, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    main()
