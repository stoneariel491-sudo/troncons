"""Lot B : la table des variantes à 768 experts (figure F-S8), tirée des journaux commités.

Écrit pour troncons, rôle « synonyme » de la construction, le 2026-10-22. Aucune valeur saisie à la main
sauf le débit du repère llama.cpp (2,25 bits, par définition du type Q2_0). L'exact (KL 0,00368, O, C4)
n'est pas dans cette table : son journal est celui du lot O.

Usage : python -I -X utf8 outils/genome/synonyme/tableau_variantes.py > mesures/genome/construction/synonyme/figures/variantes-768.csv
"""
import csv
import json
import pathlib
import sys

R = pathlib.Path(__file__).resolve().parents[3] / "mesures/genome/construction/synonyme"


def j(p):
    return json.loads((R / p).read_text(encoding="utf-8"))


lignes = []
for nom, kl, coder in [("frontiere", "kl/kl-frontiere-768-juge.json", "rapide/coder-frontiere.json"),
                       ("synonyme-l1", "kl/kl-synonyme-768-juge.json", "rapide/coder-synonyme.json"),
                       ("synonyme-l0", "kl/kl-synonyme-l0-768-juge.json", "rapide/coder-synonyme-l0.json")]:
    r = j(kl)["resume"]
    lignes.append([nom, j(coder)["bits_par_poids_utiles"], r["kl_moyenne"], r["kl_incertitude"], r["kl_mediane"], r["kl_p99"],
                   r["kl_p999"], r["meme_premier"], r["ppl_q"], kl])
r = j("repere/kl-q2_0-juge.json")["resume"]
lignes.append(["llama-q2_0", 2.25, r["kl_moyenne"], r["kl_incertitude"], r["kl_mediane"], r["kl_p99"], r["kl_p999"],
               r["meme_premier"], r["ppl_q"], "repere/kl-q2_0-juge.json"])
w = csv.writer(sys.stdout, lineterminator="\n")
w.writerow(["variante", "bits_par_poids", "kl", "kl_incertitude", "mediane", "p99", "p999", "premier", "ppl", "source"])
w.writerows(lignes)
