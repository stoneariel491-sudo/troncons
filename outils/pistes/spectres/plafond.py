"""Piste spectres : le plafond spectral (seuil.md § 7 quinquies), sur les valeurs singulières sauvées.

Pour chaque spectre σ₁ … σ_p (p = min(m, n), q = max(m, n)), λⱼ = σⱼ² / q, à l'erreur relative D :
  remplissage inverse  Σⱼ min(θ, λⱼ) = D · Σⱼ λⱼ ,   R_KLT = (1/p) Σⱼ max(0, ½ log₂(λⱼ / θ)),
  plafond              G(D) = ½ log₂(1/D) − R_KLT(D)   (bits par poids, base propre offerte).
Premier chemin : θ par dichotomie. Second chemin : θ en forme close (valeurs triées, sommes
cumulées). Témoin analytique : G de la loi de Marchenko-Pastur de rapport c = p / q, par quadrature
de sa densité, comparé aux T-MP tirés. Aucune lecture du modèle : `valeurs-singulieres.npz` seul.

Témoin positif (seuil.md § 7 sexies) : T-plante-rang8 de `levier.py`, régénéré à l'identique, contre
sa version aux entrées permutées (même permutation que `levier.py`) : E ≥ 0,05 attendu. T-Pareto est
rapporté sans attente (~~excès sur T-MP ≥ 0,05~~ : attente mal posée, § 7 sexies).
Aucune ligne de gpt-oss n'est écrite tant que les témoins ne tiennent pas.

Utilisation : python -X utf8 plafond.py [--casser] > plafond.out 2> plafond.log
"""
from __future__ import annotations

import commun

import csv
import math
import os
import sys

import numpy as np
from scipy.integrate import quad

D_PRINCIPAL = 0.044
D_COURBE = (0.01, 0.02, 0.044, 0.1)
SEUIL_LEVIER = 0.05          # seuil.md § 7
TOL_MP = 0.005               # seuil.md § 7 quinquies : le dixième du seuil de levier
TOL_CHEMINS = 1e-9


# --- premier chemin : dichotomie -----------------------------------------------------------
def plafond_dichotomie(lam: np.ndarray, d: float) -> float:
    lam = lam[lam > 0]
    p = lam.size
    cible = d * lam.sum()
    lo, hi = 0.0, float(lam.max())
    for _ in range(200):
        th = 0.5 * (lo + hi)
        if np.minimum(th, lam).sum() > cible:
            hi = th
        else:
            lo = th
    th = 0.5 * (lo + hi)
    actif = lam > th
    r = float(np.sum(0.5 * np.log2(lam[actif] / th))) / p
    return 0.5 * math.log2(1.0 / d) - r


# --- second chemin : forme close -----------------------------------------------------------
def plafond_forme_close(lam: np.ndarray, d: float) -> float:
    """θ = (cible − Σ_{j>k} λⱼ) / k pour le k tel que λ_{k+1} ≤ θ < λ_k (λ triées décroissantes)."""
    s = np.sort(lam[lam > 0])[::-1]
    p = s.size
    cible = d * s.sum()
    queue = s.sum() - np.cumsum(s)                 # queue[k−1] = Σ_{j>k} λⱼ
    k = np.arange(1, p + 1)
    th = (cible - queue) / k
    suivant = np.append(s[1:], 0.0)
    ok = (th < s) & (th >= suivant)
    i = int(np.argmax(ok))
    if not ok[i]:
        raise RuntimeError("aucun k ne convient")
    r = float(np.sum(0.5 * np.log2(s[: i + 1] / th[i]))) / p
    return 0.5 * math.log2(1.0 / d) - r


# --- Marchenko-Pastur, par quadrature ------------------------------------------------------
def plafond_mp(c: float, d: float) -> tuple[float, float, float]:
    """G(D) pour la loi MP de rapport c ∈ (0, 1], variance 1. x = a + (b − a) sin² t.

    ρ(x) dx = (b − a)² sin² t cos² t / (π c x) dt sur t ∈ [0, π/2] (densité lisse en t).
    Rend (G, masse, moyenne) : masse et moyenne doivent valoir 1 (contrôle de la quadrature).
    """
    a, b = (1 - math.sqrt(c)) ** 2, (1 + math.sqrt(c)) ** 2

    def x_de(t):
        return a + (b - a) * math.sin(t) ** 2

    def poids(t):
        x = x_de(t)
        if c == 1.0:                                  # a = 0 : ρ dx = b cos² t / π dt
            return b * math.cos(t) ** 2 / math.pi
        return (b - a) ** 2 * math.sin(t) ** 2 * math.cos(t) ** 2 / (math.pi * c * x)

    def integrale(f, coupure=None):
        pts = [coupure] if coupure is not None else None
        v, _ = quad(lambda t: f(t) * poids(t), 0.0, math.pi / 2, points=pts, limit=400,
                    epsabs=1e-13, epsrel=1e-12)
        return v

    masse = integrale(lambda t: 1.0)
    moyenne = integrale(x_de)

    def t_de(th):
        if th <= a:
            return 0.0
        if th >= b:
            return math.pi / 2
        return math.asin(math.sqrt((th - a) / (b - a)))

    lo, hi = 0.0, b
    for _ in range(100):
        th = 0.5 * (lo + hi)
        if integrale(lambda t: min(th, x_de(t)), t_de(th)) > d * moyenne:
            hi = th
        else:
            lo = th
    th = 0.5 * (lo + hi)
    r = integrale(lambda t: max(0.0, 0.5 * math.log2(x_de(t) / th)), t_de(th)) / masse
    return 0.5 * math.log2(1.0 / d) - r, masse, moyenne


def spectres_plante() -> tuple[np.ndarray, np.ndarray]:
    """T-plante-rang8 et son permuté, par la même suite de tirages que `levier.py --temoin-plante`."""
    import levier
    n = 2880
    rng = np.random.default_rng(commun.GRAINE + 50)
    a = rng.standard_normal((n, 8)) @ rng.standard_normal((8, n))
    bruit = rng.standard_normal((n, n))
    w0 = a / np.sqrt((a ** 2).mean()) * math.sqrt(0.3) + bruit * math.sqrt(0.7)
    codes, expo = levier.quantifier_mxfp4(w0 * 0.02)
    w = commun.K[codes] * np.ldexp(1.0, np.repeat(expo, 32, axis=1) - 128)
    rng.permutation(codes.size // 32)                  # le témoin T-blocs de levier.py (tirage consommé)
    wp = rng.permutation(w.ravel()).reshape(w.shape)
    del a, bruit, w0
    return np.linalg.svd(w, compute_uv=False), np.linalg.svd(wp, compute_uv=False)


def lam_de(sig: np.ndarray, q: int) -> np.ndarray:
    return sig.astype(np.float64) ** 2 / q


def main() -> None:
    commun.priorite_basse()
    casser = "--casser" in sys.argv
    z = np.load(os.path.join(commun.MESURES, "valeurs-singulieres.npz"))
    spectres = {k: z[k] for k in z.files}
    commun.attendre_calme()
    spectres["plante"], spectres["plante.perm"] = spectres_plante()
    if casser:
        spectres["plante"], spectres["plante.perm"] = spectres["plante.perm"], spectres["plante"]
        spectres["mp/2880x2880"], spectres["mp/4096x2880"] = spectres["mp/4096x2880"], spectres["mp/2880x2880"]
        print("[cassure] planté et son permuté échangés ; T-MP 2 880 × 2 880 et 4 096 × 2 880 échangés",
              file=sys.stderr)

    formes = {}                                         # id -> (m, n)
    for m in commun.echantillon():
        if m["expert"] >= 0:
            formes[m["id"]] = (2880, 2880)
        else:
            formes[m["id"]] = {"attn_q": (4096, 2880), "attn_k": (512, 2880), "attn_v": (512, 2880),
                               "attn_output": (2880, 4096)}[m["role"]]
    for k in ("512x2880", "2880x2880", "2880x4096", "4096x2880"):
        a, b = k.split("x")
        formes["mp/" + k] = (int(a), int(b))
    formes["pareto"] = (2880, 2880)
    formes["plante"] = formes["plante.perm"] = (2880, 2880)

    ecr = csv.writer(sys.stdout, lineterminator="\n")
    ecr.writerow(["id", "genre", "p", "q"] + [f"G_{d}" for d in D_COURBE] + ["G2_0.044", "ecart_chemins"])
    G = {}
    ecart_max = 0.0
    lignes = []
    for cle, sig in spectres.items():
        if cle == "pareto_plante":
            continue
        ident = cle.split("/", 1)[1] if cle.startswith(("reel/", "perm/")) else cle
        genre = cle.split("/", 1)[0] if "/" in cle and not cle.startswith("mp/") else ("mp" if cle.startswith("mp/") else cle)
        m, n = formes[ident if not cle.startswith("mp/") else cle]
        p, q = min(m, n), max(m, n)
        if sig.size != p:
            raise RuntimeError(f"{cle} : {sig.size} valeurs pour p = {p}")
        lam = lam_de(sig, q)
        g = {d: plafond_dichotomie(lam, d) for d in D_COURBE}
        g2 = plafond_forme_close(lam, D_PRINCIPAL)
        ec = abs(g2 - g[D_PRINCIPAL])
        ecart_max = max(ecart_max, ec)
        G[cle] = g
        lignes.append([cle, genre, p, q] + [f"{g[d]:.6f}" for d in D_COURBE] + [f"{g2:.9f}", f"{ec:.2e}"])

    # --- témoins ---
    ok_tout = True
    print(f"second chemin (forme close) : écart max {ecart_max:.2e} (attendu ≤ {TOL_CHEMINS:g}) : "
          f"{'TIENT' if ecart_max <= TOL_CHEMINS else 'ÉCHEC'}", file=sys.stderr)
    ok_tout &= ecart_max <= TOL_CHEMINS
    mp_ana = {}
    for k in ("2880x2880", "4096x2880", "512x2880", "2880x4096"):
        a, b = (int(x) for x in k.split("x"))
        c = min(a, b) / max(a, b)
        if c not in mp_ana:
            mp_ana[c] = {d: plafond_mp(c, d) for d in D_COURBE}
        ga, masse, moy = mp_ana[c][D_PRINCIPAL]
        ge = G["mp/" + k][D_PRINCIPAL]
        tient = abs(ge - ga) <= TOL_MP
        ok_tout &= tient
        print(f"T-MP {k:10s} c = {c:.4f} : G tiré {ge:.4f}, G analytique {ga:.4f} (masse {masse:.6f}, "
              f"moyenne {moy:.6f}), écart {ge - ga:+.4f} : {'TIENT' if tient else 'ÉCHEC'}", file=sys.stderr)
    ex_p = G["pareto"][D_PRINCIPAL] - G["mp/2880x2880"][D_PRINCIPAL]
    print(f"T-Pareto (rapporté sans attente, § 7 sexies) : G {G['pareto'][D_PRINCIPAL]:.4f}, "
          f"écart à T-MP 2 880 × 2 880 {ex_p:+.4f}", file=sys.stderr)
    e_pl = G["plante"][D_PRINCIPAL] - G["plante.perm"][D_PRINCIPAL]
    tient = e_pl >= SEUIL_LEVIER
    ok_tout &= tient
    print(f"T-plante-rang8 : G {G['plante'][D_PRINCIPAL]:.4f}, G permuté {G['plante.perm'][D_PRINCIPAL]:.4f}, "
          f"E {e_pl:+.4f} (attendu ≥ {SEUIL_LEVIER} ; prédit ≈ 0,25 à haut débit) : {'TIENT' if tient else 'ÉCHEC'}",
          file=sys.stderr)
    print("T-plante-rang8, E par D : " + ", ".join(
        f"{d} : {G['plante'][d] - G['plante.perm'][d]:+.4f}" for d in D_COURBE), file=sys.stderr)
    print(f"courbe MP analytique (c : G par D {D_COURBE}) : " +
          "; ".join(f"{c:.4f} : " + ", ".join(f"{mp_ana[c][d][0]:.4f}" for d in D_COURBE) for c in mp_ana),
          file=sys.stderr)
    if not ok_tout:
        print("TÉMOINS EN ÉCHEC : aucun chiffre du plafond ne sort", file=sys.stderr)
        for l in lignes:
            if not l[0].startswith(("reel/", "perm/")):
                ecr.writerow(l)
        return
    for l in lignes:
        ecr.writerow(l)
    sys.stdout.flush()

    # --- lecture par famille (seuil § 7 quinquies) ---
    print("", file=sys.stderr)
    fams = {"gate": [], "up": [], "down": [], "attention": []}
    tot_w = tot_g = tot_e = 0.0
    for m in commun.echantillon():
        f = "attention" if m["role"].startswith("attn") else m["role"]
        mm, nn = formes[m["id"]]
        gr = G["reel/" + m["id"]][D_PRINCIPAL]
        gp = G["perm/" + m["id"]][D_PRINCIPAL]
        c = min(mm, nn) / max(mm, nn)
        gmp = mp_ana[c][D_PRINCIPAL][0]
        fams[f].append((m["id"], gr, gp, gr - gp, gp - gmp))
        tot_w += mm * nn
        tot_g += gr * mm * nn
        tot_e += (gr - gp) * mm * nn
        print(f"{m['id']:22s} G réel {gr:.4f}  G permuté {gp:.4f}  E {gr - gp:+.4f}  permuté − MP {gp - gmp:+.4f}",
              file=sys.stderr)
    print("", file=sys.stderr)
    for f, l in fams.items():
        e = np.array([x[3] for x in l])
        med = float(np.median(e))
        print(f"famille {f:9s} : E médiane {med:+.4f} (min {e.min():+.4f}, max {e.max():+.4f}) ; "
              f"G réel médian {np.median([x[1] for x in l]):.4f} : plafond {'OUVERT' if med >= SEUIL_LEVIER else 'FERMÉ'}",
              file=sys.stderr)
    print(f"échantillon (pondéré par les poids) : G {tot_g / tot_w:.4f}, E {tot_e / tot_w:+.4f} bit par poids",
          file=sys.stderr)


if __name__ == "__main__":
    main()
