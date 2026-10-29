"""Piste spectres : le plafond au-delà des échelles de rangée (seuil.md § 7 nonies et § 7 decies).

G_rang = L2_0 − R_KLT(D) : ce que la base propre offerte gagnerait de plus qu'une variance par rangée.
Référence (§ 7 decies) : la même matrice, entrées permutées à l'intérieur de chaque rangée (mêmes
variances de rangée, donc même L2_0 ; toute structure entre rangées détruite).
E_rang = G_rang(réel) − G_rang(permuté par rangée).
~~Référence v1 : le permuté complet~~ (détruit aussi les échelles de rangée ; T-rangées tombait à
−0,562, `plafond-rangee-v1.log`). Elle sert maintenant de cassure (--casser).

Lit `plafond.out` (G du réel et du permuté complet), `levier-v3.out` (L2_0) ; relit chaque matrice du
GGUF, une à la fois, pour sa version permutée par rangée et sa SVD. Second chemin : L2_0 recalculé sur
la matrice relue, égal à celui de `levier-v3.out` à 10⁻⁶.

Utilisation : python -X utf8 plafond_rangee.py [--casser] > plafond-rangee.out 2> plafond-rangee.log
"""
from __future__ import annotations

import commun

import csv
import math
import os
import sys

import numpy as np

import levier
import plafond

D = plafond.D_PRINCIPAL
BLANC = 0.5 * math.log2(1.0 / D)
SEUIL = plafond.SEUIL_LEVIER
M = commun.MESURES
GRAINE = 20261022


def lire(nom):
    with open(os.path.join(M, nom), encoding="utf8") as f:
        return list(csv.DictReader(f))


def l2_0(w: np.ndarray) -> float:
    """Le L2_0 de levier.py : remplissage inverse sur les variances par rangée, cible D · ‖W‖² / n."""
    n = w.shape[1]
    return levier.debit_absolu((w ** 2).mean(axis=1), D * float((w ** 2).sum()) / n)


def g_klt(w: np.ndarray) -> float:
    sig = np.linalg.svd(w, compute_uv=False)
    return plafond.plafond_forme_close(sig ** 2 / max(w.shape), D)


def g_rang(w: np.ndarray) -> tuple[float, float]:
    """(G_rang, L2_0) d'une matrice."""
    l0 = l2_0(w)
    return l0 - (BLANC - g_klt(w)), l0


def triple(w: np.ndarray, rng) -> dict:
    """G_rang du réel, du permuté par rangée et du permuté complet."""
    wr = rng.permuted(w, axis=1)
    wp = rng.permutation(w.ravel()).reshape(w.shape)
    return {"reel": g_rang(w), "rangee": g_rang(wr), "complet": g_rang(wp)}


def plante() -> np.ndarray:
    """T-plante-rang8, par la même suite de tirages que `levier.py --temoin-plante`."""
    n = 2880
    rng = np.random.default_rng(commun.GRAINE + 50)
    a = rng.standard_normal((n, 8)) @ rng.standard_normal((8, n))
    bruit = rng.standard_normal((n, n))
    w0 = a / np.sqrt((a ** 2).mean()) * math.sqrt(0.3) + bruit * math.sqrt(0.7)
    codes, expo = levier.quantifier_mxfp4(w0 * 0.02)
    return commun.K[codes] * np.ldexp(1.0, np.repeat(expo, 32, axis=1) - 128)


def main() -> None:
    commun.priorite_basse()
    casser = "--casser" in sys.argv
    ref = "complet" if casser else "rangee"
    if casser:
        print("[cassure] référence = permuté complet (la référence v1, fausse)", file=sys.stderr)
    commun.attendre_calme()

    # --- témoins ---
    ok = True
    n = 2880
    rng = np.random.default_rng(GRAINE)
    s = np.exp(1.5 * rng.standard_normal(n))
    tr = triple(rng.standard_normal((n, n)) * s[:, None], rng)
    e = tr["reel"][0] - tr[ref][0]
    t1 = abs(e) < SEUIL / 4
    ok &= t1
    print(f"T-rangées : G_rang réel {tr['reel'][0]:+.4f}, par rangée {tr['rangee'][0]:+.4f}, complet "
          f"{tr['complet'][0]:+.4f} ; E_rang {e:+.4f} (attendu |·| < {SEUIL / 4}) : {'TIENT' if t1 else 'ÉCHEC'}",
          file=sys.stderr, flush=True)
    commun.attendre_calme()
    tp = triple(plante(), np.random.default_rng(GRAINE + 1))
    e = tp["reel"][0] - tp[ref][0]
    t2 = e >= SEUIL
    ok &= t2
    print(f"T-plante-rang8 : G_rang réel {tp['reel'][0]:+.4f}, par rangée {tp['rangee'][0]:+.4f}, complet "
          f"{tp['complet'][0]:+.4f} ; E_rang {e:+.4f} (attendu ≥ {SEUIL}) : {'TIENT' if t2 else 'ÉCHEC'}",
          file=sys.stderr, flush=True)
    if not ok:
        print("TÉMOINS EN ÉCHEC : la matrice du modèle n'est pas lue", file=sys.stderr)
        return

    # --- gpt-oss ---
    G = {l["id"]: float(l["G_0.044"]) for l in lire("plafond.out")}
    lv = {l["id"]: float(l["L2_0"]) for l in lire("levier-v3.out") if l["L2_0"] not in ("nan", "")}
    lec = commun.lecteur()
    index = {t.nom: t for t in lec.tenseurs}
    lignes, mini, ecart_l2 = [], 9.0, 0.0
    for k, mat in enumerate(commun.echantillon()):
        commun.attendre_calme()
        i = mat["id"]
        w = commun.matrice(lec, index, mat)
        r_rng = np.random.default_rng(GRAINE + 100 + k)
        g_r, l0 = l2_0(w) - (BLANC - G["reel/" + i]), l2_0(w)
        ecart_l2 = max(ecart_l2, abs(l0 - lv[i]))
        if ref == "rangee":
            g_ref, _ = g_rang(r_rng.permuted(w, axis=1))
        else:
            g_ref = lv[i + ".perm"] - (BLANC - G["perm/" + i])
        couvert = mat["role"] != "attn_q"
        if couvert:
            mini = min(mini, g_r, g_ref)
        lignes.append((i, mat["role"], couvert, l0, G["reel/" + i], g_r, g_ref, g_r - g_ref))
        print(f"{i:22s} L2_0 {l0:.4f}  G blanc {G['reel/' + i]:.4f}  G_rang {g_r:+.4f}  référence {g_ref:+.4f}  "
              f"E_rang {g_r - g_ref:+.4f}" + ("" if couvert else "  (attn_q : non couvert, sans verdict)"),
              file=sys.stderr, flush=True)
        del w
    t3 = mini >= -1e-3
    t4 = ecart_l2 <= 1e-6
    print(f"\nnon-négativité (45 matrices couvertes et références) : min {mini:+.4f} (attendu ≥ −0,001) : "
          f"{'TIENT' if t3 else 'ÉCHEC'}", file=sys.stderr)
    print(f"second chemin de L2_0 (relu contre levier-v3.out) : écart max {ecart_l2:.1e} (attendu ≤ 1e-6) : "
          f"{'TIENT' if t4 else 'ÉCHEC'}", file=sys.stderr)
    if not (t3 and t4):
        print("TÉMOINS EN ÉCHEC : aucun chiffre ne sort", file=sys.stderr)
        return
    ecr = csv.writer(sys.stdout, lineterminator="\n")
    ecr.writerow(["id", "role", "couvert", "L2_0", "G_blanc", "G_rang", "G_rang_ref", "E_rang"])
    fams = {"gate": [], "up": [], "down": [], "attention": []}
    tot = [0.0, 0.0, 0.0]
    for i, role, couvert, l0, gb, g_r, g_ref, e in lignes:
        ecr.writerow([i, role, int(couvert), f"{l0:.6f}", f"{gb:.6f}", f"{g_r:.6f}", f"{g_ref:.6f}", f"{e:.6f}"])
        if couvert:
            fams["attention" if role.startswith("attn") else role].append((e, g_r))
            m, nn = {"attn_k": (512, 2880), "attn_v": (512, 2880), "attn_output": (2880, 4096)}.get(role, (2880, 2880))
            tot[0] += m * nn
            tot[1] += e * m * nn
            tot[2] += g_r * m * nn
    print("", file=sys.stderr)
    for f, l in fams.items():
        e = [x[0] for x in l]
        med = float(np.median(e))
        print(f"famille {f:9s} ({len(e)} matrices) : E_rang médiane {med:+.4f} (min {min(e):+.4f}, max {max(e):+.4f}) ; "
              f"G_rang médian {np.median([x[1] for x in l]):.4f} : {'OUVERT' if med >= SEUIL else 'FERMÉ'} "
              f"au-delà des échelles de rangée", file=sys.stderr)
    print(f"échantillon couvert (pondéré par les poids) : G_rang {tot[2] / tot[0]:.4f}, E_rang {tot[1] / tot[0]:+.4f} "
          f"bit par poids", file=sys.stderr)


if __name__ == "__main__":
    main()
