"""Le nombre de garde κ = σ / E[m] : forme close de la courbe de la garde sous deux hypothèses
(marge exponentielle de taux λ, bascule si la perturbation gaussienne de l'écart δ ~ N(0, σ²) passe
sous −m), et sa vérification par quadrature (second chemin) puis contre les couches mesurées.

  c(τ) = 1 − e^{−λτ} ;  P(bascule) = ½ − e^{κ²/2} Φ(−κ) ;
  b(τ) = [½ − e^{−λτ} Φ(−τ/σ) − e^{κ²/2} (Φ(τ/σ + κ) − Φ(κ))] / P(bascule),   κ = λσ.

Calcul léger (aucune lecture de journal : il lit deux petits CSV de résultats) : il ne prend pas la
pause du verrou, il garde la priorité basse.
Usage : python -I -X utf8 theoreme.py
"""

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import routage as R  # noqa: E402

import numpy as np  # noqa: E402
from scipy import integrate, optimize, stats  # noqa: E402

Phi = stats.norm.cdf


def _ek(k, x):
    """e^{κ²/2} Φ(−x), stable pour κ grand (par le logarithme de la queue normale)."""
    return np.exp(k * k / 2 + stats.norm.logsf(x))


def p_bascule(k):
    return 0.5 - _ek(k, k)


def b_forme_close(k, c):
    lt = -np.log1p(-c)          # λτ
    t = lt / k                  # τ/σ
    # Φ(t + κ) − Φ(κ) = Φ(−κ) − Φ(−(t + κ))
    num = 0.5 - np.exp(-lt) * Phi(-t) - (_ek(k, k) - _ek(k, t + k))
    return num / p_bascule(k)


def b_quadrature(k, c):
    lam, sig = 1.0, k            # λ = 1, σ = κ
    tau = -np.log1p(-c) / lam
    f = lambda m: lam * np.exp(-lam * m) * Phi(-m / sig)  # noqa: E731
    num = integrate.quad(f, 0, tau, epsabs=1e-13, epsrel=1e-11)[0]
    den = integrate.quad(f, 0, np.inf, epsabs=1e-13, epsrel=1e-11)[0]
    return num / den


def main():
    R.sous_la_normale()
    res = {"outil": "outils/pistes/tropicale/theoreme.py"}
    # second chemin : quadrature contre forme close
    ecarts = [abs(b_forme_close(k, c) - b_quadrature(k, c)) for k in (0.01, 0.05, 0.1, 0.3, 1.0, 3.0) for c in (0.01, 0.1, 0.3)]
    res["ecart_max_forme_close_quadrature"] = float(max(ecarts))
    pb_q = integrate.quad(lambda m: np.exp(-m) * Phi(-m / 0.2), 0, np.inf)[0]
    res["p_bascule_k02_forme_close_contre_quadrature"] = [float(p_bascule(0.2)), float(pb_q)]
    # le seuil critique : b(κ*, 10 %) = 80 %
    k_etoile = optimize.brentq(lambda k: b_forme_close(k, 0.10) - 0.80, 1e-4, 10)
    res["kappa_critique_80_10"] = float(k_etoile)
    res["p_bascule_au_kappa_critique"] = float(p_bascule(k_etoile))
    # courbe κ → (P(bascule), b(10 %))
    lignes = [[f"{k:.5f}", f"{p_bascule(k):.6f}", f"{b_forme_close(k, 0.10):.5f}"] for k in np.logspace(-3, 1, 81)]
    with open(R.SORTIE / "theoreme-kappa.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["kappa", "p_bascule", "b_a_10_pour_cent"])
        w.writerows(lignes)
    # contre les couches : κ_ℓ = σ̂_ℓ (vraisemblance de Φ) / E[m_ℓ] ; c_ℓ = part des cellules de la couche
    # sous le τ₁₀ global (decile-par-couche.csv) ; prédiction de b_ℓ et de P(bascule)_ℓ
    lois = json.loads((R.SORTIE / "lois-resume.json").read_text(encoding="utf-8"))
    dec = {int(r["couche"]): r for r in csv.DictReader(open(R.SORTIE / "decile-par-couche.csv", encoding="utf-8"))}
    par = []
    for d in lois["loi_marge"]:
        l = d["couche"]
        for nom, sig in (("phi_mv", lois["loi_bascule"][str(l)]["sigma_phi"]), ("delta_robuste", lois["loi_bascule"][str(l)]["sigma_delta_robuste"])):
            k = sig / d["moyenne"]
            c = float(dec[l]["part_cellules_sous_tau10_global"])
            par.append([l, nom, f"{k:.4f}", f"{c:.4f}", f"{p_bascule(k):.5f}", dec[l]["taux_bascule"],
                        f"{b_forme_close(k, c):.4f}", dec[l]["part_bascules_sous_tau10_global"]])
    with open(R.SORTIE / "theoreme-par-couche.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["couche", "sigma", "kappa", "c_couche", "p_bascule_predite", "p_bascule_mesuree", "b_predit", "b_mesure"])
        w.writerows(par)
    (R.SORTIE / "theoreme.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=2))
    for r in par:
        print(*r)


if __name__ == "__main__":
    main()
