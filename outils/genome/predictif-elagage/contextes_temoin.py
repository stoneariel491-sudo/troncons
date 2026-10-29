"""Recalcule le témoin « gauche permutée » de contextes.py avec la formule de biais corrigée.

La passe du 2026-10-16 (contextes-gptoss20b.json) a écrit un biais de (51 − 1)·15/(2 N ln 2) avec N
poolé sur les 12 tenseurs ; les tables étant par tenseur, le biais vaut (51 − 3)·15/(2 N_t ln 2).
Cet outil relit le journal et rend le témoin corrigé, sans relancer la passe de 30 minutes.
Seuil : gain du contexte permuté ≤ 1,5 × biais attendu (la dispersion d'un estimateur de biais
sur 12 tables). Cassure (--casser) : le biais attendu est divisé par 12 (l'ancienne formule) ; le
témoin doit tomber.
"""
import json
import math
import sys

j = json.load(open(sys.argv[1], encoding="utf-8"))
r = j["resultats"]
nt = r["temoin_gauche_permute"]["poids"] / len(j["par_tenseur"])
biais = (51 - 3) * 15 / (2 * nt * math.log(2))
if "--casser" in sys.argv:
    biais /= 12
gain = r["temoin_kappa_meme_lot"]["bits_par_poids"] - r["temoin_gauche_permute"]["bits_par_poids"]
print(json.dumps({"biais_attendu": biais, "gain_contexte_permute": gain, "rapport": gain / biais,
                  "temoin_tient": gain <= 1.5 * biais, "casser": "--casser" in sys.argv}, ensure_ascii=False))
