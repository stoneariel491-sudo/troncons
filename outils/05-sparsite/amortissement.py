"""Amortissement d'une lecture de poids sur plusieurs jetons : le calcul de
l'étude 05, avec son témoin par simulation.

1. Décodage spéculatif en chaîne (Leviathan et al. 2023, arXiv 2211.17192) :
   k jetons proposés, chacun accepté avec la probabilité α (supposée la même et
   indépendante d'une position à l'autre) ; la passe de vérification rend
   toujours un jeton de plus (la correction ou le jeton bonus). Le nombre de
   jetons produits par passe de la cible, donc par lecture complète des poids
   actifs d'un modèle dense, est
        E(α, k) = sum_{i=0..k} α^i = (1 - α^{k+1}) / (1 - α),
   borné par 1/(1-α) quand k -> infini.

2. Modèles à experts (MoE) : la passe de vérification de n = k+1 jetons lit
   l'UNION des experts choisis par ces n jetons. Avec E experts routés par
   couche, t choisis par jeton, choix uniformes et indépendants (hypothèse
   pessimiste : les jetons voisins partagent en vrai une partie de leurs
   experts), l'espérance du nombre d'experts distincts par couche est
        U(n) = E · (1 - (1 - t/E)^n).
   Octets lus par passe : A + R · U(n)/t, où A = poids toujours lus
   (attention, experts partagés, normes...) et R = octets des experts routés
   d'UN jeton. Jetons par octet : E(α,k) / (A + R·U(k+1)/t).

3. Débit sur la machine : temps d'une passe = max ou somme (recouvrement
   parfait ou nul) des octets de chaque étage divisés par son débit, plus k
   passes du brouillon.

Usage :
  python -I amortissement.py temoin [--casser]
  python -I amortissement.py tables SORTIE.json
"""
from __future__ import annotations

import json
import math
import random
import sys

ALPHAS = (0.5, 0.6, 0.7, 0.8, 0.9, 0.95)
KS = (1, 2, 3, 4, 6, 8, 16, 32)

GO = 1e9


def e_chaine(alpha: float, k: int) -> float:
    if alpha >= 1.0:
        return k + 1.0
    return (1.0 - alpha ** (k + 1)) / (1.0 - alpha)


def e_chaine_cassee(alpha: float, k: int) -> float:
    return (1.0 - alpha ** k) / (1.0 - alpha)  # erreur volontaire : oublie le jeton bonus


def union_experts(E: int, t: int, n: int) -> float:
    return E * (1.0 - (1.0 - t / E) ** n)


def simuler_chaine(alpha, k, essais, rng):
    tot = 0
    for _ in range(essais):
        a = 0
        while a < k and rng.random() < alpha:
            a += 1
        tot += a + 1
    return tot / essais


def simuler_union(E, t, n, essais, rng):
    tot = 0
    for _ in range(essais):
        s = set()
        for _ in range(n):
            s.update(rng.sample(range(E), t))
        tot += len(s)
    return tot / essais


def temoin(casser: bool) -> bool:
    """Seuil déclaré : |simulé - formule| < 4 écarts-types de la moyenne
    simulée (probabilité d'un faux échec par cas ~ 6e-5 ; 30 cas)."""
    rng = random.Random(20261015)
    f = e_chaine_cassee if casser else e_chaine
    ok = True
    essais = 20000
    for alpha in (0.5, 0.8, 0.95):
        for k in (1, 4, 16):
            sim = simuler_chaine(alpha, k, essais, rng)
            # variance de la longueur acceptée bornée par k^2/4 ; on prend
            # l'écart-type empirique via une seconde simulation serait plus
            # fin : la borne suffit et reste honnête.
            et = math.sqrt(min(k * k / 4.0, alpha / (1 - alpha) ** 2) / essais)
            bon = abs(sim - f(alpha, k)) < 4 * et + 1e-12
            ok &= bon
            print(f"chaîne α={alpha} k={k:2d} : simulé {sim:.4f} formule {f(alpha, k):.4f} "
                  f"(4σ={4 * et:.4f}) {'ok' if bon else 'ÉCHEC'}")
    for E, t in ((128, 8), (256, 8), (512, 10), (8, 2)):
        for n in (1, 2, 4, 8, 16):
            sim = simuler_union(E, t, n, 4000, rng)
            u = union_experts(E, t, n)
            et = math.sqrt(E / 4.0 / 4000)
            bon = abs(sim - u) < 4 * et
            ok &= bon
            print(f"union E={E} t={t} n={n:2d} : simulé {sim:.2f} formule {u:.2f} {'ok' if bon else 'ÉCHEC'}")
    print("RÉUSSI" if ok else "ÉCHEC", "(mode cassé)" if casser else "")
    return ok


# --- Cas de la machine de Stone -------------------------------------------
# Débits : étiquetés dans le livrable. B_VRAM et B_PCIE mesurés par l'étude 04
# (pcie-1.json : copie carte->carte 169 Go/s lecture+écriture, soit ~2x pour la
# lecture seule bornée à 256 ; hôte->carte épinglé 6,38 Go/s). Le NVMe n'est
# pas encore mesuré : plafond calculé 7,877 Go/s (étude 01) ; on borne entre
# 3 et 7 Go/s.
B_VRAM = 200 * GO      # lecture effective supposée sous le plafond de 256
B_PCIE = 6.38 * GO     # mesuré ici (étude 04)
B_NVME = {"pessimiste": 3.0 * GO, "optimiste": 7.0 * GO}

CAS_DENSES = {
    # nom : (octets lus par passe depuis le NVMe, depuis la RAM, depuis la VRAM)
    # 70B dense en ~4,8 bits (Q4_K_M) : ~42 Go ; RAM utile ~11 Go, VRAM ~7 Go.
    "dense 70B Q4 (42 Go), 7 Go en VRAM, 11 Go en RAM, 24 Go lus du NVMe":
        (24 * GO, 11 * GO, 7 * GO),
    # Le même en 2 bits (~20 Go) : tient presque en RAM + VRAM.
    "dense 70B ~2,3 bits (20 Go), 7 Go VRAM, 11 Go RAM, 2 Go NVMe":
        (2 * GO, 11 * GO, 7 * GO),
    # Qwen3.5-9B Q4_K_M entier en VRAM (5,4 Go de tenseurs, mesuré par l'inventaire).
    "Qwen3.5-9B Q4_K_M entièrement en VRAM (5,67 Go)":
        (0.0, 0.0, 5.67 * GO),
}

# MoE : (A toujours lus en Go, R routés lus par jeton en Go, E, t, part du
# routé servie par le cache RAM/VRAM). Octets d'après le tableau de l'étude 06
# (plafonds-fichiers.md, 2026-10-15) ; A supposé résident (VRAM+RAM).
CAS_MOE = {
    "DeepSeek-V4-Flash Q2_K_XL (96,8 Go)": (6.69, 2.10, 256, 6, 0.12),
    "Qwen3.8-Flash-Next Q2_K_XL (78,9 Go)": (3.54, 0.90, 512, 10, 0.30),
    "gpt-oss-120b MXFP4 (63,4 Go)": (1.69, 1.91, 128, 4, 0.26),
    "Kimi-K2.6 Q2_K_XL (340,5 Go)": (8.52, 6.90, 384, 8, 0.03),
}


# Substitut résident (SubSpec transposé à la machine) : la cible quantifiée vit en
# RAM et passe par le PCIe à chaque passe ; une copie très basse précision de la
# même cible vit en VRAM et sert de brouillon (aucun octet de brouillon ne
# traverse le PCIe). (octets cible en RAM, octets du substitut en VRAM)
CAS_SUBSTITUT = {
    "cible 14B Q4_K_M (8,5 Go) en RAM, substitut ~2,1 bits (3,9 Go) en VRAM": (8.5, 3.9),
    "cible 9B Q4_K_M (5,7 Go) en RAM, substitut ~2,1 bits (2,5 Go) en VRAM": (5.7, 2.5),
}


# Accords gloutons mesurés (same top p contre Q4_K_M, Qwen3.5-4B, étude 02 et
# étude 05) : nom -> (bits par poids du fichier, alpha).
SUBSTITUTS_MESURES = {
    "IQ4_XS": (4.76, 0.919),
    "IQ3_XXS": (3.60, 0.821),
    "IQ2_XXS": (2.91, 0.658),
}


def temps_passe(nvme, ram, vram, b_nvme, recouvrement):
    etages = [nvme / b_nvme if nvme else 0.0, ram / B_PCIE if ram else 0.0, vram / B_VRAM]
    return max(etages) if recouvrement else sum(etages)


def tables():
    out = {"E_chaine": {}, "denses": {}, "moe": {}}
    for a in ALPHAS:
        out["E_chaine"][str(a)] = {str(k): e_chaine(a, k) for k in KS}
        out["E_chaine"][str(a)]["inf"] = 1 / (1 - a)
    # brouillon : temps d'une passe d'un petit modèle résident en VRAM
    # (0,6 Go lus à 200 Go/s = 3 ms, plus ~2 ms de lancement) : ~5 ms.
    t_brouillon = 0.005
    for nom, (nv, ra, vr) in CAS_DENSES.items():
        d = {}
        for hyp, b in B_NVME.items():
            for rec in (True, False):
                T = temps_passe(nv, ra, vr, b, rec)
                ligne = {"T_passe_s": T, "jetons_s_sans_spec": 1 / T}
                for a in (0.6, 0.8, 0.9):
                    meilleurs = max(((e_chaine(a, k) / (T + k * t_brouillon), k) for k in range(1, 65)))
                    ligne[f"alpha={a}"] = {"jetons_s": meilleurs[0], "k_opt": meilleurs[1],
                                           "jetons_par_lecture": e_chaine(a, meilleurs[1])}
                # arbre type SpecExec : 10 à 20 jetons par passe (littérature)
                ligne["arbre_10_par_passe_jetons_s"] = 10 / (T + 10 * t_brouillon)
                d[f"{hyp}, {'recouvrement' if rec else 'sans recouvrement'}"] = ligne
        out["denses"][nom] = d
    out["substitut"] = {}
    for nom, (cible, sub) in CAS_SUBSTITUT.items():
        T = cible * GO / B_PCIE
        t_b = sub * GO / B_VRAM + 0.002
        ligne = {"T_passe_s": T, "t_brouillon_s": t_b, "jetons_s_sans_spec": 1 / T}
        for a in (0.75, 0.85, 0.92):
            meilleurs = max(((e_chaine(a, k) / (T + k * t_b), k) for k in range(1, 65)))
            ligne[f"alpha={a}"] = {"jetons_s": meilleurs[0], "k_opt": meilleurs[1],
                                   "jetons_par_lecture": e_chaine(a, meilleurs[1])}
        ligne["arbre_10_par_passe_jetons_s"] = 10 / (T + 10 * t_b)
        out["substitut"][nom] = ligne
    # Substitut choisi parmi les quantifications mesurées (accord glouton du 4B,
    # étude 02 : bits par poids -> same top p), sous un budget de VRAM.
    out["substitut_mesure"] = {}
    budget_vram = 6.0  # Go laissés au substitut (8 Go moins bureau, cache KV, tampons)
    for n_params in (9e9, 14e9, 20e9, 27e9):
        cible = n_params * 5.19 / 8 / GO  # Go, Q4_K_M
        if cible > 13.0:  # RAM utile ~13 Go
            continue
        T = cible * GO / B_PCIE
        meilleur = None
        for nom_q, (bits, alpha) in SUBSTITUTS_MESURES.items():
            sub = n_params * bits / 8 / GO
            if sub > budget_vram:
                continue
            t_b = sub * GO / B_VRAM + 0.002
            js, k = max(((e_chaine(alpha, k) / (T + k * t_b), k) for k in range(1, 65)))
            if meilleur is None or js > meilleur["jetons_s"]:
                meilleur = {"substitut": nom_q, "go_substitut": sub, "alpha": alpha,
                            "k_opt": k, "jetons_s": js}
        out["substitut_mesure"][f"{n_params / 1e9:.0f}B"] = {
            "go_cible_ram": cible, "T_passe_s": T, "jetons_s_sans_spec": 1 / T,
            "meilleur": meilleur}
    for nom, (A, R, E, t, h) in CAS_MOE.items():
        d = {}
        for hyp, b in B_NVME.items():
            def T(n):
                u = union_experts(E, t, n) / t
                routes = R * GO * u
                # A résident : lu en VRAM (borne optimiste) ; routés : (1-h) du NVMe, h de la RAM.
                return max(A * GO / B_VRAM + h * routes / B_PCIE, (1 - h) * routes / b)
            ligne = {"T_passe_1_s": T(1), "jetons_s_sans_spec": 1 / T(1),
                     "union_experts_par_couche": {str(n): union_experts(E, t, n) for n in (1, 2, 4, 8, 16)},
                     "octets_relatifs_passe": {str(n): T(n) / T(1) for n in (1, 2, 4, 8, 16)}}
            for a in (0.6, 0.8, 0.9):
                best = max(((e_chaine(a, k) / (T(k + 1) + k * t_brouillon), k) for k in range(0, 33)))
                ligne[f"alpha={a}"] = {"jetons_s": best[0], "k_opt": best[1],
                                       "gain_sur_sans_spec": best[0] * T(1)}
            d[hyp] = ligne
        out["moe"][nom] = d
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1] == "temoin":
        sys.exit(0 if temoin("--casser" in sys.argv) else 1)
    if sys.argv[1] == "tables":
        res = tables()
        with open(sys.argv[2], "w", encoding="utf-8") as f:
            json.dump(res, f, indent=1, ensure_ascii=False)
        print(json.dumps(res["E_chaine"], indent=0)[:2000])


if __name__ == "__main__":
    main()
