"""Données des figures du lot B (génome synonyme) pour le mémoire : la transformation du synonyme vue
dans la base propre de H (avant : frontière ; après : mutation synonyme).

Écrit pour troncons, rôle « synonyme » de la construction, le 2026-10-17. Lit le GGUF (lecteur de
03), les captures de calibration et d'évaluation de l'éclaireur, et les fichiers .sym des deux
variantes ; n'écrit que des CSV (aucun calcul n'entre dans un verdict).

Pour une matrice (couche, expert, rôle) : H = E[g² x xᵀ]/E[g²] sur la calibration (non amortie) et
H_ev sur l'évaluation ; leurs vecteurs propres u_k (valeurs propres décroissantes). Pour chaque
variante, ΔW = W − Ŵ ; l'énergie de l'erreur dans la direction k est e_k = ‖ΔW u_k‖² ; la part de
l'erreur de sortie portée par k est λ_k e_k / Σ λ_j e_j (car tr(ΔW H ΔWᵀ) = Σ_k λ_k ‖ΔW u_k‖²).
La mutation synonyme doit déplacer e_k vers les petites λ_k : c'est ce que la figure montre.

Sorties (mesures/genome/construction/synonyme/figures/) :
  spectre-L{c}-E{e}-{role}.csv : k, lambda_calib, lambda_eval_rayleigh, e_frontiere, e_synonyme
  (lambda_eval_rayleigh = u_kᵀ H_ev u_k : la direction de calibration vue par l'évaluation).

Usage : python -I -X utf8 donnees_figures.py --couche 8 --expert 0 --role gate
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import os
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", "..", ".."))
sys.path.insert(0, ICI)
import verifier_sym as vs  # noqa: E402  (mêmes lectures, écrites de zéro dans ce rôle)

CAPT = "~/dev/essais/troncons/genome/eclaireur"


def entrees(quoi, couche, e):
    h = np.memmap(os.path.join(CAPT, quoi, f"h-L{couche:02d}.f32"), dtype=np.float32, mode="r").reshape(-1, vs.N)
    r = np.fromfile(os.path.join(CAPT, quoi, f"routage-L{couche:02d}.bin"), dtype=np.uint8).reshape(-1, 20)
    choix, g = r[:, :4], r[:, 4:].copy().view(np.float32).reshape(-1, 4)
    p, j = np.nonzero(choix == e)
    return np.asarray(h[p], dtype=np.float64), g[p, j].astype(np.float64)


def H_de(X, g):
    w = g * g
    return (X * w[:, None]).T @ X / w.sum()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--couche", type=int, default=8)
    ap.add_argument("--expert", type=int, default=0)
    ap.add_argument("--role", default="gate", choices=["gate", "up", "down"])
    a = ap.parse_args()
    lec, tens = vs.lecteur()
    j = vs.ROLES.index(a.role)
    W = {}
    for r in vs.ROLES:
        ex, qs = vs.octets_expert(lec, tens, a.couche, r, a.expert)
        W[r] = (ex, vs.matrice_exacte(ex, qs))
    ex, Wj = W[a.role]
    Xc, gc = entrees("calib", a.couche, a.expert)
    Xe, ge = entrees("eval", a.couche, a.expert)
    if a.role == "down":
        b = {r: vs.biais(lec, tens, a.couche, r, a.expert) for r in ("gate", "up")}
        act = lambda X: vs.activation(X @ W["gate"][1].T + b["gate"], X @ W["up"][1].T + b["up"])
        Xc, Xe = act(Xc), act(Xe)
    Hc, He = H_de(Xc, gc), H_de(Xe, ge)
    lam, U = np.linalg.eigh(Hc)
    ordre = np.argsort(lam)[::-1]
    lam, U = lam[ordre], U[:, ordre]
    lam_ev = np.einsum("ik,ij,jk->k", U, He, U)
    err = {}
    for v in ("frontiere", "synonyme-l1-d1"):
        centres, syms = vs.lire_sym(os.path.join(vs.SYM, v, f"L{a.couche:02d}-E{a.expert:02d}.sym"))
        dW = Wj - vs.matrice_base(ex, syms[j], centres)
        err[v] = ((dW @ U) ** 2).sum(axis=0)
    dossier = os.path.join(RACINE, "mesures/genome/construction/synonyme/figures")
    os.makedirs(dossier, exist_ok=True)
    chemin = os.path.join(dossier, f"spectre-L{a.couche:02d}-E{a.expert:02d}-{a.role}.csv")
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["k", "lambda_calib", "lambda_eval_rayleigh", "e_frontiere", "e_synonyme"])
        for k in range(vs.N):
            w.writerow([k, f"{lam[k]:.9e}", f"{lam_ev[k]:.9e}", f"{err['frontiere'][k]:.9e}", f"{err['synonyme-l1-d1'][k]:.9e}"])
    for v in err:
        sortie_c = float((lam * err[v]).sum())
        sortie_e = float((lam_ev * err[v]).sum())
        print(f"{v} : énergie de l'erreur {err[v].sum():.6e}, sortie calib {sortie_c:.6e}, sortie éval {sortie_e:.6e}")
    print(f"écrit : {chemin} ; n_calib {Xc.shape[0]}, n_eval {Xe.shape[0]}")


if __name__ == "__main__":
    main()
