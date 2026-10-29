"""Juge de la garde tropicale : deux contrôles du théorème du nombre de garde, par quadrature seule.

1. Ce que le modèle homogène (marge exponentielle, perturbation gaussienne, un seul κ) prédit au taux
   de bascule MESURÉ (5 087 / 122 640 = 4,148 %) : b(c = 10 %) au κ qui rend ce taux.
2. Le corollaire « une garde à marge ne tient 80 / 10 que si moins de 4,03 % des cellules basculent »
   est-il vrai hors du modèle homogène ? Contre-exemple construit : un mélange de couches à échelles
   de marge différentes (ce que sont les 24 couches réelles, κ_ℓ de 0,016 à 0,48 d'après la piste),
   garde à seuil global.

Aucune donnée lue ; priorité « sous la normale », un fil.
"""

import ctypes
import json
import math
import os

SORTIE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..",
                                      "mesures", "pistes", "tropicale", "juge"))


def baisser_priorite():
    if os.name == "nt":
        k32 = ctypes.windll.kernel32
        k32.GetCurrentProcess.restype = ctypes.c_void_p
        k32.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        k32.SetPriorityClass(k32.GetCurrentProcess(), 0x00004000)


def phi_bar(x):
    return 0.5 * math.erfc(x / math.sqrt(2))


def simpson(f, a, b, n=20000):
    h = (b - a) / n
    s = f(a) + f(b)
    for j in range(1, n):
        s += (4 if j % 2 else 2) * f(a + j * h)
    return s * h / 3


def couche(mu, sigma, tau):
    """Une population : marge ~ Exp(moyenne mu), P(bascule | m) = Φ(−m/σ).
    Rend (part des cellules sous τ, P(B), P(B et m < τ))."""
    haut = min(40 * mu, mu * 40 + 40 * sigma)
    f = lambda m: math.exp(-m / mu) / mu * phi_bar(m / sigma)
    pB = simpson(f, 0.0, haut)
    pBt = simpson(f, 0.0, min(tau, haut)) if tau > 0 else 0.0
    return 1 - math.exp(-tau / mu), pB, pBt


def melange(pops, c_cible=0.10):
    """pops : liste de (poids, mu, sigma). Seuil global τ tel que la part des cellules sous τ vaille c."""
    def part(tau):
        return sum(w * (1 - math.exp(-tau / mu)) for w, mu, _ in pops)
    lo, hi = 0.0, 1.0
    while part(hi) < c_cible:
        hi *= 2
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if part(mid) < c_cible else (lo, mid)
    tau = (lo + hi) / 2
    pB = pBt = 0.0
    for w, mu, s in pops:
        _, a, b = couche(mu, s, tau)
        pB += w * a
        pBt += w * b
    return {"tau": tau, "part_cellules": part(tau), "P_B": pB, "b": pBt / pB}


def main():
    baisser_priorite()
    res = {"outil": "outils/pistes/tropicale/juge/juge_modele.py"}

    # 1. Le modèle homogène au taux mesuré.
    taux = 5087 / 122640
    lo, hi = 0.01, 1.0
    for _ in range(80):
        k = (lo + hi) / 2
        pB = 0.5 - math.exp(k * k / 2) * phi_bar(k)
        lo, hi = (k, hi) if pB < taux else (lo, k)
    kap = (lo + hi) / 2
    r = melange([(1.0, 1.0, kap)])
    res["homogene_au_taux_mesure"] = {"taux_mesure": taux, "kappa": kap, **r, "b_mesure": 2905 / 5087}

    # Témoin : au κ* déclaré par la piste, le modèle homogène doit rendre b = 80 %, P(B) = 4,03 %.
    res["temoin_kappa_etoile"] = melange([(1.0, 1.0, 0.1079)])

    # 2. Contre-exemple au corollaire : 2 couches sur 24 à marges serrées et fortement perturbées,
    #    22 couches à marges larges et faiblement perturbées ; garde à seuil global.
    pops = [(2 / 24, 1e-4, 1e-3), (22 / 24, 0.1, 0.004)]
    r2 = melange(pops)
    res["contre_exemple_melange"] = {"populations": [{"poids": w, "moyenne_marge": mu, "sigma": s,
                                                     "kappa": s / mu} for w, mu, s in pops], **r2,
                                     "tient_80_10": r2["b"] >= 0.80, "taux_au_dessus_de_4_03": r2["P_B"] > 0.0403}

    os.makedirs(SORTIE, exist_ok=True)
    with open(os.path.join(SORTIE, "juge-modele.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
