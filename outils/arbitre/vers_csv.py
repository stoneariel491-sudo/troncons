"""Données des figures du mémoire tirées des journaux de l'arbitre (rien n'est recalculé ici).

Entrées : decisions/journaux/arbitre/decoupe-gptoss20b.json (mesure F1),
          decisions/journaux/arbitre/verif-plafonds.json (second chemin des plafonds).
Sorties : decisions/journaux/arbitre/csv/f1-par-tenseur.csv
          decisions/journaux/arbitre/csv/f1-totaux.csv
          decisions/journaux/arbitre/csv/plafonds-arbitre.csv
          decisions/journaux/arbitre/csv/seuils-j1.csv

Usage, depuis la racine du dépôt : python -I -X utf8 outils/arbitre/vers_csv.py
"""
from __future__ import annotations

import csv
import json
import os

ICI = os.path.dirname(os.path.abspath(__file__))
J = os.path.normpath(os.path.join(ICI, "..", "..", "decisions", "journaux", "arbitre"))
SORTIE = os.path.join(J, "csv")


def ecrire(nom: str, entetes: list[str], lignes: list[list]) -> None:
    with open(os.path.join(SORTIE, nom), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(entetes)
        w.writerows(lignes)


def main() -> None:
    os.makedirs(SORTIE, exist_ok=True)
    with open(os.path.join(J, "decoupe-gptoss20b.json"), encoding="utf-8") as f:
        d = json.load(f)
    err = {e["nom"]: e for e in d["erreurs_par_tenseur"]}
    lignes = []
    for t in d["tenseurs"]:
        e = err[t["nom"]]
        lignes.append([t["nom"], t["poids"], t["bpp_delta"], t["bpp_a_flux"], t["bpp_a_ctx"], t["bpp_base"],
                       t["bpp_compl_cond"], t["bpp_compl_mag"], t["bpp_compl_riche"], t["bpp_compl_brut"],
                       e["centres_communs_07"], e["centres_du_tenseur"], e["aimantes_e2m1"]])
    ecrire("f1-par-tenseur.csv",
           ["tenseur", "poids", "delta", "codes_a_flux", "codes_a_ctx", "base", "compl_cond", "compl_mag",
            "compl_riche", "compl_brut", "erreur_base_centres_communs", "erreur_base_centres_tenseur",
            "erreur_base_aimantee"], lignes)
    b = d["bpp"]
    r = d["b_riche"]
    ecrire("f1-totaux.csv", ["variante", "bits_par_poids", "rapport_a_ctx"], [
        ["A_flux", b["a_flux"], b["a_flux"] / b["a_ctx"]],
        ["A_ctx", b["a_ctx"], 1.0],
        ["B_cond", b["b_cond"], b["b_cond"] / b["a_ctx"]],
        ["B_mag", b["b_mag"], b["b_mag"] / b["a_ctx"]],
        ["B_riche", r["bpp_total"], r["bpp_total"] / b["a_ctx"]],
    ])
    with open(os.path.join(J, "verif-plafonds.json"), encoding="utf-8") as f:
        v = json.load(f)
    lignes = [[k, a["plafond"], a["serie"], a["T_disque_ms"], a["T_pcie_ms"], a["T_carte_ms"],
               a.get("part_base", 0.0)] for k, a in v["architectures"].items()]
    ecrire("plafonds-arbitre.csv", ["architecture_scenario", "plafond_jetons_s", "serie_jetons_s",
                                    "T_disque_ms", "T_pcie_ms", "T_carte_ms", "part_base"], lignes)
    lignes = [[k, s["h_v"], s["h_r"], s["h_s"], s["plafond"], s["serie"], s["seuil_C5"]]
              for k, s in v["seuils_J1"].items()]
    ecrire("seuils-j1.csv", ["mode_scenario", "h_v", "h_r", "h_s", "plafond", "serie", "seuil_C5"], lignes)


if __name__ == "__main__":
    main()
