"""La borne distorsion-débit des poids MXFP4 de gpt-oss, dans le domaine des poids.

Éclaireur du génome des poids (genome/01-eclaireur.md § 3). Écrit de zéro pour troncons, 2026-10-16.

QUESTION. Si, sachant l'échelle de leur bloc, les codes MXFP4 sont des tirages indépendants d'une même
loi (03 : le voisin n'apporte que 0,005 bit), alors AUCUN codeur qui ne regarde que les poids (graine,
dictionnaire, code vectoriel, automate, parenté sans corrélation) ne peut, en moyenne, faire mieux que
la fonction distorsion-débit R(D) de cette source, l'échelle étant connue (elle est déjà payée :
0,0375 bit par poids). Ce script calcule cette borne et y place la frontière (base de 07).

MODÈLE. Poids w = s · v, v ∈ ±K (K = {0,1,2,3,4,6,8,12}, unités E2M1 doublées), v i.i.d. de loi p
(comptée sur les 12 tenseurs de 07), s = 2^(e−128) connue. Distorsion relative
D = Σ s² (v − v̂)² / Σ s² v². Les blocs d'exposant e ont le poids π_e 4^e : la meilleure allocation
du débit entre exposants est le « remplissage inverse » à pente égale (Cover et Thomas, § 10.3) :
chaque classe e prend le point de la courbe R(D) de v de pente −μ · 4^(e − e_max). La courbe R(D) de
la source discrète v se calcule par l'algorithme de Blahut-Arimoto (Blahut 1972) sur une grille de
reproduction fine. Deux courbes : allocation optimale entre exposants (la borne), et allocation
uniforme (même pente pour tous, comme un quantificateur unique).

TÉMOINS, DÉCLARÉS AVANT :
  B1 à pente nulle, R = 0 et D = 1 (rien n'est transmis, reproduction 0 optimale si E[v] = 0 ;
     ici D → Var(v)/E[v²] ≈ 1) ; à pente très grande, R → H(v) (à 0,01 bit) et D → 0 ;
  B2 sur une source gaussienne discrétisée finement (σ = 1), la courbe calculée suit 2^(−2R) à 0,05
     bit près pour R ∈ [1, 3] (borne de Shannon, exacte pour la gaussienne) ;
  cassure (--casser) : la grille de reproduction privée de ses points intérieurs (seulement ±12) : B2
     doit tomber.
  RÉSULTAT DE LA PREMIÈRE PASSE (2026-10-16, journaux/borne-rd.json) : B1 TOMBE à son bout bas
     (pente 1e-6 : D = 3,88 E[v²] au lieu de ≤ 1) ; B2 tient (écart 1e-5 bit), sa cassure tombe.
     Raison : à pente β, Blahut-Arimoto demande de l'ordre de 1/β itérations pour concentrer la loi de
     reproduction ; à β = 1e-6, 3 000 itérations n'y suffisent pas (le point n'est pas convergé, il
     n'est pas faux au sens d'une borne : il est simplement sous-optimal). Correction, déclarée APRÈS
     cette chute : (1) chaque point rend son drapeau de convergence ; (2) un point de distorsion
     supérieure à E[v²] est remplacé par le point de débit nul (reproduire 0 coûte 0 bit et donne
     Var(v) ≤ E[v²]) ; (3) B1bis : au bout bas, β = 1e-3 avec 200 000 itérations au plus, D ≤ E[v²] ;
     au bout haut inchangé.
  RÉSULTAT DE LA DEUXIÈME PASSE : B1bis et B2 tiennent, mais seuls 243 points sur 1 619 ont convergé à
     1e-12, et la courbe « allocation optimale » se lit hors de son domaine (μ trop petit pour les
     petits exposants : débit maximal atteint < 2,64 bits, l'interpolation extrapole). Elle n'est PAS
     publiée comme borne. Ajout, déclaré avant la troisième passe : `uniforme_precis`, 40 pentes de
     0,5 à 200, 200 000 itérations au plus, tolérance 1e-11, chaque point avec son drapeau ; seuls des
     points convergés servent aux deux nombres publiés (débit à 4,29 %, distorsion à 2,642 bits).

Utilisation : python -I -X utf8 borne_rd.py [--casser] > journal.json  (CSV écrit à côté si --csv f)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import synonyme as S  # noqa: E402


CONVERGES = []


def blahut_arimoto(x, p, y, beta, iters=3000, tol=1e-12):
    """Point de R(D) de pente −beta (bits par unité de distorsion) : rend (R bits, D)."""
    conv = False
    d = (x[:, None] - y[None, :]) ** 2
    q = np.full(len(y), 1.0 / len(y))
    A = np.exp(-beta * np.log(2) * (d - d.min(axis=1, keepdims=True)))
    for _ in range(iters):
        Qn = A * q[None, :]
        Qn /= Qn.sum(axis=1, keepdims=True)
        qn = p @ Qn
        if np.abs(qn - q).max() < tol:
            q = qn
            conv = True
            break
        q = qn
    Q = A * q[None, :]
    Q /= Q.sum(axis=1, keepdims=True)
    D = float((p[:, None] * Q * d).sum())
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(Q > 0, Q * np.log2(Q / q[None, :]), 0.0)
    R = float((p[:, None] * r).sum())
    CONVERGES.append(conv)
    ev2 = float((p * x * x).sum())
    if D > ev2:
        return 0.0, ev2
    return R, D


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--casser", action="store_true")
    ap.add_argument("--csv", default=None)
    a = ap.parse_args()
    m = S.Modele()
    C = np.zeros((256, 16))
    for l in S.COUCHES:
        for role in S.ROLES:
            for e in range(32):
                ex, codes = m.blocs(l, role, e)
                C += S.comptes(ex, codes)
    vals = np.concatenate([S.MAG, -S.MAG])
    nq = C.sum(axis=0)
    # ±0 se confondent en valeur : on fusionne pour la source (le signe d'un zéro ne porte rien)
    x = np.array(sorted(set(vals.tolist())))
    p = np.array([nq[[i for i in range(16) if vals[i] == v]].sum() for v in x])
    p /= p.sum()
    y = np.linspace(-13, 13, 1041)
    if a.casser:
        y = np.array([-12.0, 12.0])
    Ev2 = float((p * x * x).sum())
    pe = C.sum(axis=1)
    es = np.nonzero(pe)[0]
    emax = es.max()
    poids_e = pe[es] * 4.0 ** (es - emax)                  # π_e 4^(e − e_max), non normalisé
    # témoins
    R0, D0 = blahut_arimoto(x, p, y, 1e-3, iters=200000)
    Rinf, Dinf = blahut_arimoto(x, p, y, 400.0)
    Hv = float(-(p * np.log2(p)).sum())
    xg = np.linspace(-5, 5, 401)
    pg = np.exp(-xg ** 2 / 2)
    pg /= pg.sum()
    yg = np.linspace(-5, 5, 801) if not a.casser else np.array([-5.0, 5.0])
    ecarts = []
    for beta in (1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0):
        R, D = blahut_arimoto(xg, pg, yg, beta)
        if 1.0 <= R <= 3.0:
            ecarts.append(abs(R - 0.5 * np.log2(1.0 / D)))
    B1 = abs(R0) < 1e-3 and abs(D0 / Ev2 - 1) < 1e-2 and abs(Rinf - Hv) < 0.01 and Dinf / Ev2 < 1e-3
    B2 = len(ecarts) > 0 and max(ecarts) < 0.05
    # courbes
    lignes = []
    for mu in np.geomspace(0.05, 3000, 70):
        # optimale : pente par exposant ∝ 4^(e − e_max)
        Rs, Ds = [], []
        for e, w in zip(es, 4.0 ** (es - emax)):
            R, D = blahut_arimoto(x, p, y, mu * w)
            Rs.append(R)
            Ds.append(D)
        Rs, Ds = np.array(Rs), np.array(Ds)
        R_opt = float((pe[es] * Rs).sum() / pe[es].sum())
        D_opt = float((poids_e * Ds).sum() / (poids_e * Ev2).sum())
        R_u, D_u = blahut_arimoto(x, p, y, mu * 0.25)
        lignes.append({"mu": float(mu), "bits_optimale": R_opt, "D_optimale": D_opt, "bits_uniforme": R_u, "D_uniforme": D_u / Ev2})
    precis = []
    for beta in np.geomspace(0.5, 200, 40):
        n0 = len(CONVERGES)
        R, D = blahut_arimoto(x, p, y, beta, iters=200000, tol=1e-11)
        precis.append({"beta": float(beta), "bits": R, "D": D / Ev2, "converge": bool(CONVERGES[n0])})
    ok = [r for r in precis if r["converge"]]
    def interp_precis(cle_x, cle_y, v, log_y=False, log_x=False):
        pts = sorted((r[cle_x], r[cle_y]) for r in ok)
        xs = np.array([a for a, _ in pts])
        ys = np.array([b for _, b in pts])
        xs = np.log(xs) if log_x else xs
        vv = np.log(v) if log_x else v
        if not (xs.min() <= vv <= xs.max()):
            return None
        r = np.interp(vv, xs, np.log(ys) if log_y else ys)
        return float(np.exp(r) if log_y else r)

    def bits_a(D, cle_b, cle_d):
        pts = sorted((r[cle_d], r[cle_b]) for r in lignes)
        ds, bs = np.array([u for u, _ in pts]), np.array([v for _, v in pts])
        return float(np.interp(np.log(D), np.log(ds), bs))
    def D_a(b, cle_b, cle_d):
        pts = sorted((r[cle_b], r[cle_d]) for r in lignes)
        bs, ds = np.array([u for u, _ in pts]), np.array([v for _, v in pts])
        return float(np.exp(np.interp(b, bs, np.log(ds))))
    j = {"outil": "borne_rd.py", "casser": a.casser, "H_v_bits": Hv, "E_v2": Ev2,
         "loi_v": dict(zip([float(v) for v in x], [float(q) for q in p])),
         "exposants": {int(e): float(c) for e, c in zip(es, pe[es])},
         "B1": {"R0": R0, "D0_rel": D0 / Ev2, "Rinf": Rinf, "Dinf_rel": Dinf / Ev2, "tient": bool(B1)},
         "B2": {"ecarts_bits": ecarts, "tient": bool(B2)},
         "frontiere_07": {"bits_base": 2.642, "erreur": 0.042919745},
         "borne_bits_a_4_29pct": bits_a(0.042919745, "bits_optimale", "D_optimale"),
         "borne_uniforme_bits_a_4_29pct": bits_a(0.042919745, "bits_uniforme", "D_uniforme"),
         "borne_D_a_2_642_bits": D_a(2.642, "bits_optimale", "D_optimale"),
         "borne_uniforme_D_a_2_642_bits": D_a(2.642, "bits_uniforme", "D_uniforme"),
         "points_converges": int(sum(CONVERGES)), "points": len(CONVERGES),
         "uniforme_precis": precis,
         "uniforme_precis_bits_a_4_29pct": interp_precis("D", "bits", 0.042919745, log_x=True),
         "uniforme_precis_D_a_2_642_bits": interp_precis("bits", "D", 2.642, log_y=True),
         "uniforme_precis_points_converges": len(ok),
         "courbe": lignes}
    if a.csv:
        import csv
        with open(a.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(lignes[0]))
            w.writeheader()
            w.writerows(lignes)
    print(json.dumps(j, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
