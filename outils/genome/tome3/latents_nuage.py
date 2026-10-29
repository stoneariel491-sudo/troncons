"""Le nuage des entrées réelles d'un expert sur les trois premiers axes propres de H, et les ellipses de
l'erreur de sortie de la frontière et du synonyme (Tome III, figure III-9.7).

Écrit pour troncons, lot « espaces latents » du premier flux de figures du Tome III, le 2026-10-27.
Processeur seul, mémoire bornée (moins de 600 Mo) ; aucune passe du modèle.

LA MATRICE ET LES ENTRÉES : la même que III-9.1 (gpt-oss-20b, couche 8, expert 0, gate), ses entrées
réelles de calibration (fenêtres 10 à 21 de wiki.test, h après la norme, les positions que le routeur
envoie à l'expert 0) et leurs poids de routeur g. H = Σ g² x xᵀ / Σ g², non amortie, exactement comme
le CSV du lot B (outils/genome/synonyme/donnees_figures.py) ; (λ_k, u_k) ses couples propres par
valeurs décroissantes. Coordonnées d'une entrée : c_k = u_kᵀ x, k = 1, 2, 3. Signe de u_k fixé pour
que la moyenne des c_k soit positive.

L'ELLIPSE DE L'ERREUR D'UNE BASE, dans le plan (u_a, u_b) : ΔW = W − Ŵ (Ŵ servie par la base,
fichiers .sym du lot B, `frontiere` et `synonyme-l1-d1`) ; M = Bᵀ ΔWᵀ ΔW B, B = [u_a u_b] (2 × 2) ;
l'ellipse est l'image du cercle unité par M^{1/2}. Sa fonction d'appui dans une direction unité v du
plan vaut ‖ΔW v‖ : la norme de l'erreur de sortie pour une entrée unité dans cette direction. Ses
demi-axes le long de u_a et u_b ont pour carré M_aa = e_a et M_bb = e_b, les énergies de III-9.1 (b).
Les deux ellipses sont agrandies d'un même facteur F, le même dans les deux panneaux, pour vivre à
l'échelle du nuage (règle déclarée : F = 2 √λ_2 / (plus grand demi-axe de l'ellipse frontière dans
le plan (u_1, u_2))). L'ellipse des entrées (pointillés) : demi-axes 2 √λ_a et 2 √λ_b (H est
diagonale dans sa base propre).

TÉMOIN (doit pouvoir tomber) :
  N0 le même H et les mêmes erreurs que le lot B : λ_1, λ_2, λ_3 égalent `lambda_calib` du CSV
     spectre-L08-E00-gate.csv, et e_1, e_2, e_3 (frontière et synonyme) ses colonnes, à 1e-7 relatif
     (le CSV écrit 10 chiffres) ; cassure : H tiré des entrées d'évaluation (fenêtres 0 à 9),
     λ_1 doit s'écarter de plus de 1e-3.

Sorties (mesures/genome/tome3/latents/) :
  nuage-L08-E00-gate-points.csv   : position, g, c1, c2, c3 ;
  nuage-L08-E00-gate-ellipses.csv : courbe (frontiere, synonyme, entrees), plan (12, 13), i, x, y ;
  nuage-L08-E00-gate.json         : n, λ, e_k, demi-axes, facteur F, témoin et cassure.

  python -I -X utf8 outils/genome/tome3/latents_nuage.py
"""
from __future__ import annotations

import os

for _v in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ[_v] = "1"

import csv  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

import numpy as np  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import latents_commun as lc  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
COUCHE, EXPERT, ROLE = 8, 0, "gate"
SORTIE = os.path.join(lc.RACINE, "mesures/genome/tome3/latents")
PAS = 180
PLANS = {"12": (0, 1), "13": (0, 2)}


def H_de(X, g):
    w = g * g
    return (X * w[:, None]).T @ X / w.sum()


def racine2(M):
    v, Q = np.linalg.eigh(M)
    return Q @ np.diag(np.sqrt(np.maximum(v, 0.0))) @ Q.T, np.sqrt(np.maximum(v, 0.0))


def main() -> int:
    t0 = time.time()
    os.makedirs(SORTIE, exist_ok=True)
    lec, tens = lc.lecteur()
    j_role = lc.ROLES.index(ROLE)
    ex, codes = lc.blocs_expert(lec, tens, COUCHE, ROLE, EXPERT)
    W = lc.matrice_exacte(ex, codes)
    Xc, gc, pos = lc.entrees("calib", COUCHE, EXPERT)
    Hc = H_de(Xc, gc)
    lam, U = np.linalg.eigh(Hc)
    o = np.argsort(lam)[::-1]
    lam, U = lam[o], U[:, o]
    U3 = U[:, :3].copy()
    del U, Hc
    C = Xc @ U3
    for k in range(3):
        if C[:, k].mean() < 0:
            C[:, k] *= -1
            U3[:, k] *= -1
    spec, chemin_spec = lc.lire_spectre(COUCHE, EXPERT, ROLE)
    dWU = {}
    for v in ("frontiere", "synonyme-l1-d1"):
        c, mats, _ = lc.lire_sym(v, COUCHE, EXPERT)
        dWU[v] = (W - lc.matrice_base(ex, mats[j_role], c)) @ U3        # (R, 3)
    e = {v: (dWU[v] ** 2).sum(axis=0) for v in dWU}
    # N0
    ec = {"lambda": np.abs(lam[:3] / spec["lambda_calib"][:3] - 1).max(),
          "frontiere": np.abs(e["frontiere"] / spec["e_frontiere"][:3] - 1).max(),
          "synonyme": np.abs(e["synonyme-l1-d1"] / spec["e_synonyme"][:3] - 1).max()}
    Xe, ge, _ = lc.entrees("eval", COUCHE, EXPERT)
    lam_e = np.linalg.eigvalsh(H_de(Xe, ge))[::-1]
    cass = float(abs(lam_e[0] / spec["lambda_calib"][0] - 1))
    N0 = {"ecarts_relatifs_max": {k: float(x) for k, x in ec.items()}, "tient": bool(max(ec.values()) < 1e-7),
          "cassure_eval_lambda1": float(lam_e[0]), "cassure_ecart_relatif": cass, "cassure_tombe": cass > 1e-3}
    print(f"N0 : {N0}", file=sys.stderr, flush=True)

    # ellipses
    th = np.linspace(0.0, 2 * np.pi, PAS + 1)
    cercle = np.stack([np.cos(th), np.sin(th)])
    racines, demi = {}, {}
    for v in dWU:
        for p, (a, b) in PLANS.items():
            B = dWU[v][:, [a, b]]
            Rm, s = racine2(B.T @ B)
            racines[(v, p)] = Rm
            demi[f"{v}-{p}"] = sorted(s.tolist(), reverse=True)
    F = 2.0 * np.sqrt(lam[1]) / max(demi["frontiere-12"])
    with open(os.path.join(SORTIE, "nuage-L08-E00-gate-ellipses.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["courbe", "plan", "i", "x", "y"])
        for (v, p), Rm in racines.items():
            nom = "frontiere" if v == "frontiere" else "synonyme"
            pts = F * (Rm @ cercle)
            for i in range(PAS + 1):
                w.writerow([nom, p, i, f"{pts[0, i]:.6f}", f"{pts[1, i]:.6f}"])
        for p, (a, b) in PLANS.items():
            for i in range(PAS + 1):
                w.writerow(["entrees", p, i, f"{2 * np.sqrt(lam[a]) * cercle[0, i]:.6f}", f"{2 * np.sqrt(lam[b]) * cercle[1, i]:.6f}"])
    with open(os.path.join(SORTIE, "nuage-L08-E00-gate-points.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["position", "g", "c1", "c2", "c3"])
        for i in range(C.shape[0]):
            w.writerow([int(pos[i]), f"{gc[i]:.6f}", f"{C[i, 0]:.6f}", f"{C[i, 1]:.6f}", f"{C[i, 2]:.6f}"])
    j = {"outil": "outils/genome/tome3/latents_nuage.py", "date": "2026-10-27",
         "matrice": f"blk.{COUCHE}.ffn_{ROLE}_exps.weight, expert {EXPERT} (gpt-oss-20b)",
         "spectre_csv": os.path.relpath(chemin_spec, lc.RACINE).replace("\\", "/"),
         "entrees": "calibration, fenêtres 10 à 21 de wiki.test", "n_entrees": int(C.shape[0]),
         "lambda_1_3": lam[:3].tolist(), "lambda_somme": float(lam.sum()),
         "part_trace_3_axes": float(lam[:3].sum() / lam.sum()),
         "e_1_3": {v: e[v].tolist() for v in e}, "demi_axes_bruts": demi,
         "facteur_F": float(F), "regle_F": "F = 2 √λ_2 / plus grand demi-axe de l'ellipse frontière du plan (u1, u2)",
         "moyenne_c": C.mean(axis=0).tolist(), "ecart_type_c": C.std(axis=0).tolist(),
         "temoin_N0": N0, "duree_s": time.time() - t0}
    with open(os.path.join(SORTIE, "nuage-L08-E00-gate.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(j, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(json.dumps(j, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
