"""Synthèse de l'échantillon de la duplication : CSV pour le mémoire et verdicts contre les seuils déclarés.

Lit mesures/genome/duplication/mutation-c{0,8,16,23}.json et écrit :
  csv/d1-sans-perte.csv     : par matrice, H(code | κ), gain du parent, gain du parent de hasard ;
  csv/d2-avec-perte.csv     : par matrice, débits à ε = 4,292 % : ECSQ seule, mutation soustraite,
                              contexte parent, contexte hasard ; base de la frontière ;
  csv/d2b-base.csv          : par matrice, gain du parent et du hasard sur les symboles de la base ;
  csv/t-o-sortie.csv        : par enfant, erreurs de poids et de sortie (base, mutation, ECSQ, tronquée) ;
  csv/rd-points.csv         : tous les points (pas, ε, débit) des balayages, pour les figures ;
  verdicts.json             : D1, D2, D2b, O, contre les seuils de 00-seuils-declares.md.
Témoin (--casser) : le gain du parent est remplacé par celui du hasard + 1 bit ; D1 doit alors
« marcher » partout, ce qui prouve que le verdict lit bien les colonnes qu'il juge.
"""
from __future__ import annotations

import argparse
import csv
import json
import os

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
J = os.path.normpath(os.path.join(ICI, "..", "..", "..", "mesures", "genome", "duplication"))
A_CTX = 3.8431
BASE = 2.6441
EPS_BASE = 0.042920
COUT_PERM = 0.0011634
COUT_TABLES_D1 = 48 * 16 * 16 / (2880 * 2880)      # κ × code parent × code, comptes de 16 bits
COUT_TABLES_D2B = 0.00037037


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--couches", default="0,8,16,23")
    ap.add_argument("--casser", action="store_true")
    a = ap.parse_args()
    os.makedirs(os.path.join(J, "csv"), exist_ok=True)
    fiches = []
    for L in [int(x) for x in a.couches.split(",")]:
        chemin = os.path.join(J, f"mutation-c{L}.json")
        if os.path.exists(chemin):
            fiches += json.load(open(chemin, encoding="utf-8"))["enfants"]
    d1, d2, d2b, to, rd = [], [], [], [], []
    for f in fiches:
        L, c, p = f["couche"], f["expert"], f["parent"]
        for role in ("gate", "up", "down"):
            x = f["D1"][role]
            gain = x["gain_codes"] if not a.casser else x["temoin_hasard_gain"] + 1.0
            d1.append([L, c, role, p["couche"], p["expert"], x["H_code_sachant_kappa"], gain,
                       x["temoin_hasard_gain"], gain - x["temoin_hasard_gain"], x["temoin_soi_H"]])
            y = f["D2"][role]
            r = y["debit_a_eps_base"]
            d2.append([L, c, role, r["independant"], r["mutation"], r["contexte_parent"], r["contexte_hasard"],
                       y["bits_alpha_par_poids"], y["gain_mutation"], y["gain_contexte"], y["gain_contexte_hasard"]])
            for nom in ("independant", "mutation", "contexte_parent", "contexte_hasard", "hasard"):
                for pas, eps, deb in y[nom]:
                    rd.append([L, c, role, nom, pas, eps, deb])
            z = f["D2b_base"][role]
            d2b.append([L, c, role, z["H_base_sachant_kappa"], z["gain_parent"], z["gain_hasard"],
                        z["gain_parent"] - z["gain_hasard"], z["gain_parent_code_complet"]])
        if "O" in f:
            o = f["O"]
            to.append([L, c, p["couche"], p["expert"], o["jetons_routes"]] +
                      [o[k][m] for k in ("base_B", "mutation_eps_base", "ecsq_seule_eps_base", "mutation_tronquee",
                                         "parent_seul_sans_alpha") for m in ("erreur_poids", "erreur_sortie")] +
                      [o["temoin_exact"]])

    def ecrire(nom, entete, lignes):
        with open(os.path.join(J, "csv", nom), "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(entete)
            w.writerows(lignes)
    ecrire("d1-sans-perte.csv", ["couche", "enfant", "role", "parent_couche", "parent_expert", "H_code_kappa",
                                 "gain_parent", "gain_hasard", "gain_net", "H_soi"], d1)
    ecrire("d2-avec-perte.csv", ["couche", "enfant", "role", "R_ecsq_seule", "R_mutation", "R_contexte_parent",
                                 "R_contexte_hasard", "bits_alpha", "gain_mutation", "gain_contexte",
                                 "gain_contexte_hasard"], d2)
    ecrire("d2b-base.csv", ["couche", "enfant", "role", "H_base_kappa", "gain_parent", "gain_hasard", "gain_net",
                            "gain_parent_code_complet"], d2b)
    ecrire("t-o-sortie.csv", ["couche", "enfant", "parent_couche", "parent_expert", "jetons",
                              "base_poids", "base_sortie", "mutation_poids", "mutation_sortie", "ecsq_poids",
                              "ecsq_sortie", "tronquee_poids", "tronquee_sortie", "parent_brut_poids",
                              "parent_brut_sortie", "temoin_exact"], to)
    ecrire("rd-points.csv", ["couche", "enfant", "role", "variante", "pas", "eps", "debit"], rd)

    # Scores de parenté de tous les candidats (figure : distribution intra, voisine, même indice).
    sc = []
    for f in fiches:
        for x in f["scores_candidats"]:
            genre = "intra" if x["couche"] == f["couche"] else ("meme_indice" if x["expert"] == f["expert"] else "voisine")
            sc.append([f["couche"], f["expert"], x["couche"], x["expert"], genre, x["score_bits"]] + x["cos_par_role"])
    ecrire("scores-parente.csv", ["couche", "enfant", "cand_couche", "cand_expert", "genre", "score_bits",
                                  "cos_gate", "cos_up", "cos_down"], sc)
    # Paralogues.
    pa = []
    for L in [int(x) for x in a.couches.split(",")]:
        chemin = os.path.join(J, f"paralogues-c{L}.json")
        if os.path.exists(chemin):
            for r_ in json.load(open(chemin, encoding="utf-8"))["par_expert"]:
                pa.append([L, r_["expert"], r_["jetons"], r_["meilleur_paralogue"], r_["eps_paralogue_beta"],
                           r_["eps_paralogue_beta_1"], r_["eps_hasard"], r_["eps_5e_choix"],
                           r_["couche_substitue"], r_["couche_retire"]])
    ecrire("paralogues.csv", ["couche", "expert", "jetons", "paralogue", "eps_beta", "eps_beta1", "eps_hasard",
                              "eps_5e", "couche_substitue", "couche_retire"], pa)

    # Verdicts.
    v = {"matrices": len(d1)}
    marge = COUT_PERM + COUT_TABLES_D1
    v["D1"] = {"cout_ajoute": marge,
               "matrices_sous_A_ctx": int(sum(1 for r in d1 if r[6] > marge)),
               "gain_moyen": float(np.mean([r[6] for r in d1])), "gain_hasard_moyen": float(np.mean([r[7] for r in d1])),
               "gain_net_moyen": float(np.mean([r[8] for r in d1]))}
    v["D1"]["marche"] = v["D1"]["matrices_sous_A_ctx"] == len(d1)
    g_h = [r[10] for r in d2 if r[10] is not None]
    sd_h = float(np.std(g_h)) if g_h else None
    ok2 = [r for r in d2 if r[3] is not None and r[9] is not None]
    v["D2"] = {"ecart_type_gain_hasard": sd_h,
               "ecsq_seule_sous_base": int(sum(1 for r in ok2 if r[3] + 0.0344 < BASE)),
               "mutation_soustraite_gain_moyen": float(np.mean([r[8] for r in ok2 if r[8] is not None])),
               "contexte_gain_moyen": float(np.mean([r[9] for r in ok2])),
               "contexte_bat_hasard_de_plus_d_un_ecart_type": int(sum(1 for r in ok2 if r[9] - (r[10] or 0) > (sd_h or 0)))}
    v["D2"]["marche"] = (v["D2"]["contexte_bat_hasard_de_plus_d_un_ecart_type"] == len(d2)
                         and v["D2"]["ecsq_seule_sous_base"] == len(d2))
    marge_b = COUT_PERM + COUT_TABLES_D2B
    v["D2b"] = {"cout_ajoute": marge_b,
                "matrices_gain_sup_cout_et_hasard": int(sum(1 for r in d2b if r[4] > marge_b and r[4] > r[5])),
                "gain_moyen": float(np.mean([r[4] for r in d2b])), "gain_hasard_moyen": float(np.mean([r[5] for r in d2b])),
                "gain_net_moyen": float(np.mean([r[6] for r in d2b])),
                "debit_base_avec_parent": BASE - float(np.mean([r[4] for r in d2b])) + marge_b}
    v["D2b"]["marche"] = v["D2b"]["matrices_gain_sup_cout_et_hasard"] == len(d2b)
    if to:
        v["O"] = {"base_sortie_moyenne": float(np.mean([r[6] for r in to])),
                  "mutation_sortie_moyenne": float(np.mean([r[8] for r in to])),
                  "ecsq_sortie_moyenne": float(np.mean([r[10] for r in to])),
                  "tronquee_sortie_moyenne": float(np.mean([r[12] for r in to])),
                  "mutation_sous_base": int(sum(1 for r in to if r[8] <= r[6])), "enfants": len(to)}
    v["casser"] = a.casser
    print(json.dumps(v, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
