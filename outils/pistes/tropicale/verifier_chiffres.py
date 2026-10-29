"""Relit les chiffres principaux de garde-tropicale.md contre les fichiers commités qui les portent.
Chaque ligne : le texte attendu dans le livrable, et la valeur recalculée depuis le JSON ou le CSV.
Usage : python -I -X utf8 verifier_chiffres.py   (sort en erreur si un chiffre manque ou diffère)
"""

import json
import sys
from pathlib import Path

DEPOT = Path(__file__).resolve().parents[3]
M = DEPOT / "mesures/pistes/tropicale"
doc = (DEPOT / "genome/pistes/tropicale/garde-tropicale.md").read_text(encoding="utf-8")
g = json.loads((M / "garde-resume.json").read_text(encoding="utf-8"))
c = json.loads((M / "cascades.json").read_text(encoding="utf-8"))
lo = json.loads((M / "lois-resume.json").read_text(encoding="utf-8"))
th = json.loads((M / "theoreme.json").read_text(encoding="utf-8"))
sc = json.loads((M / "second-chemin.json").read_text(encoding="utf-8"))


def pc(x, n=1):
    return f"{100 * x:.{n}f}".replace(".", ",") + " %"


def fr(x, n):
    return f"{x:.{n}f}".replace(".", ",")


vb = g["variantes"]["marge_B"]
attendus = [
    (pc(vb["decile"]["part_bascules"]), "b(τ₁₀)"),
    (f"{vb['decile']['bascules_signalees']:,}".replace(",", " ") + " sur " + f"{g['bascules']:,}".replace(",", " "), "2 905 sur 5 087"),
    (pc(vb["cout_de_80_pour_cent"]["part_cellules"]), "coût de 80 %"),
    (fr(vb["cout_de_80_pour_cent"]["tau"], 4), "τ de 80 %"),
    (pc(g["variantes"]["min_AB_oracle"]["decile"]["part_bascules"]), "oracle"),
    (pc(g["variantes"]["marge_A"]["decile"]["part_bascules"]), "marge A"),
    (pc(g["variantes"]["marge_B_positions_notees"]["decile"]["part_bascules"]), "positions notées"),
    (pc(c["b_tau10_primaires"]), "racines"),
    (pc(c["b_tau10_secondaires"]), "secondaires"),
    (pc(lo["propagation"]["p_bascule_sachant_bascule_avant"]), "propagation"),
    (fr(lo["prechargement"]["P1_couche_suivante"]["auc"], 3), "P1"),
    (fr(lo["prechargement"]["P2_jeton_suivant"]["auc"], 3), "P2"),
    (fr(lo["correlation_couches"]["spearman_groupe"], 3), "Spearman groupé"),
    (fr(th["kappa_critique_80_10"], 3), "κ*"),
    (pc(th["p_bascule_au_kappa_critique"], 2), "P(B) critique"),
    (fr(sc["tau10"], 5), "τ₁₀"),
]
ok = True
for texte, nom in attendus:
    present = texte in doc
    ok &= present
    print(f"{'ok ' if present else 'MANQUE'}  {nom:22s} « {texte} »")
print("second chemin égal :", sc["egal_au_chemin_principal"])
ok &= sc["egal_au_chemin_principal"]
sys.exit(0 if ok else 1)
