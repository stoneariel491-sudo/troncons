# Juge final du Tome III : refait, par mon propre chemin (lecture directe des JSON et CSV commités), les
# chiffres neufs ou déplacés depuis memoire/tome3/JUGEMENT-redaction-fr.md (commit 99d009d).
# Chaque ligne : identifiant, imprimé (tel que le texte l'écrit), refait, verdict à l'arrondi imprimé.
# Usage : python -I -X utf8 refaire_neufs.py <racine du dépôt> [--casser]
#   --casser : décale chaque valeur imprimée d'une unité de son dernier chiffre ; tous doivent tomber.
import csv
import json
import math
import pathlib
import statistics
import sys
from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP

D = pathlib.Path(sys.argv[1])
casser = "--casser" in sys.argv
resultats = []


def j(chemin):
    return json.loads((D / chemin).read_text(encoding="utf-8"))


def c(chemin):
    with open(D / chemin, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def decaler(imprime):
    """Décale le dernier chiffre de la chaîne imprimée d'une unité."""
    s = imprime
    for k in range(len(s) - 1, -1, -1):
        if s[k].isdigit():
            return s[:k] + str((int(s[k]) + 1) % 10) + s[k + 1:]
    return s


def egal(ident, imprime, refait, note=""):
    """Juste si refait, arrondi au nombre de décimales de l'imprimé, redonne l'imprimé (moitié vers le haut ou
    vers le pair : les deux sont acceptés et le dit)."""
    imp = decaler(imprime) if casser else imprime
    dec = len(imp.split(".")[1]) if "." in imp else 0
    q = Decimal(1).scaleb(-dec)
    r_up = Decimal(repr(refait)).quantize(q, rounding=ROUND_HALF_UP)
    r_ev = Decimal(repr(refait)).quantize(q, rounding=ROUND_HALF_EVEN)
    ok = (str(r_up) == imp) or (str(r_ev) == imp)
    resultats.append((ident, imp, f"{refait:.8g}", "égal" if ok else "FAUX", note))


# --- 02, le juge en quatre phrases -------------------------------------------------------------------
pos = c("mesures/genome/etat-de-l-art/journaux/kl-frontiere-positions.csv")
egal("02 positions de R1", "2550", float(len(pos)))
par_fen = {}
for x in pos:
    par_fen[x["fenetre"]] = par_fen.get(x["fenetre"], 0) + 1
egal("02 positions par fenêtre (toutes égales)", "255", float(min(par_fen.values())),
     f"{len(par_fen)} fenêtres, max {max(par_fen.values())}")
egal("02 e^-16 (mantisse ×1e7)", "1.1", math.exp(-16) * 1e7)
# --- notations : calibration, R1 ---------------------------------------------------------------------
cal = j("mesures/genome/etat-de-l-art/journaux/capture-calib.json")
egal("notations calibration, positions", "6132", float(cal["positions"]), f"fenêtres {cal['fenetres']} (borne haute exclue)")
ev = j("mesures/genome/etat-de-l-art/journaux/capture-eval.json")
egal("notations R1, jetons par fenêtre (positions/10 + 1)", "512", ev["positions"] / 10 + 1, f"fenêtres {ev['fenetres']}")
egal("notations 20b, experts", "768", 24 * 32.0)
egal("notations 120b, experts", "4608", 36 * 128.0)
egal("notations bloc MXFP4, octets", "17", 1 + 32 * 4 / 8)
# --- 03, S* : 1,018 ----------------------------------------------------------------------------------
k10 = j("mesures/genome/genome/kl/comparer10-base-contre-recette.json")
a, b = k10["a_contre_verite"]["kl_moyenne"], k10["b_contre_verite"]["kl_moyenne"]
egal("03 KL base K10", "0.02057", a)
egal("03 KL S* K10", "0.02093", b)
egal("03 rapport S*/base K10", "1.018", b / a)
egal("résumé, 13 : appariée S* K10", "0.0004", k10["apparie"]["kl_difference_b_moins_a"])
egal("résumé, 13 : σ appariée S* K10", "0.0019", k10["apparie"]["kl_ecart_type"])
# --- 00 : codon du zéro en A_flux et A_ctx -----------------------------------------------------------
zc = j("mesures/genome/etat-de-l-art/journaux/zero-canonique.json")
egal("00 codon A_flux après", "3.7064", zc["bpp"]["a_flux"])
egal("00 codon A_ctx après", "3.7061", zc["bpp"]["a_ctx"])
fr = c("mesures/genome/construction/synthese/k10/frontiere.csv")
egal("00 frontière A_flux, 2,6441 : nombre de lignes de frontiere.csv (25)", "25", float(len(fr)))
# --- 01, 12 : arrondis du correcteur -------------------------------------------------------------------
egal("01 ½ log2(πe/6)", "0.2546", 0.5 * math.log2(math.pi * math.e / 6))
egal("01 10 log10(πe/6) dB", "1.53", 10 * math.log10(math.pi * math.e / 6))
q = 512 / 2880
egal("12 (1 − √q)²", "0.3345", (1 - math.sqrt(q)) ** 2)
egal("12 (1 + √q)²", "2.021", (1 + math.sqrt(q)) ** 2)
egal("12 √q", "0.4216", math.sqrt(q))
# --- 06 : RAM inclusive à R = 80 et 160 ------------------------------------------------------------------
g = c("mesures/mimetisme/P2/grille.csv")
sel = [x for x in g if x["mode"] == "inclusif" and x["R"] in ("80", "160")]
traces = sorted({x["trace"] for x in sel})
egal("06 succès RAM inclusif, R = 80 et 160 (maximum)", "0", max(float(x["succes_ram"]) for x in sel),
     f"{len(sel)} lignes, {len(traces)} traces")
egal("06 traces (hors la réunion « tous »)", "7", float(len([x for x in traces if not x.startswith("tous")])))
# --- 07 : l'expert pont ---------------------------------------------------------------------------------
p = c("mesures/genome/duplication/csv/paralogues.csv")
for couche, n_att, tot in (("0", "4", "32"), ("8", "5", "32"), ("16", "25", "31"), ("23", "21", "31")):
    lignes = [x for x in p if x["couche"] == couche and x["couche_substitue"] and x["couche_retire"]]
    mieux = sum(float(x["couche_substitue"]) < float(x["couche_retire"]) for x in lignes)
    egal(f"07 couche {couche} : substituer < retirer", n_att, float(mieux), f"sur {len(lignes)}")
    egal(f"07 couche {couche} : experts", tot, float(len(lignes)))
    ms = statistics.mean(float(x["couche_substitue"]) for x in lignes)
    mr = statistics.mean(float(x["couche_retire"]) for x in lignes)
    resultats.append((f"07 couche {couche} : moyennes substituée / retirée, écart en points", "",
                      f"{ms:.5f} / {mr:.5f} ; {100 * (mr - ms):+.3f}", "lu", ""))
# --- 10 : σ et seuil du J-V2, 0,95^64 -------------------------------------------------------------------
v = j("mesures/genome/construction/juge/vitesse/analyse-120b.json")
egal("10 σ (A, 120b)", "0.05764", v["sigma"])
egal("10 seuil J-V2", "1.769", v["J_V2_ou_V3"]["seuil"])
egal("10 seuil J-V2 refait 2(1 − 2σ)", "1.769", 2 * (1 - 2 * v["sigma"]))
egal("10 r(R/B)", "1.284", v["r_R_sur_B"])
egal("10 toit 686,8/468,5", "1.47", v["octets_par_pas"]["B"] / v["octets_par_pas"]["R"])
egal("10 0,95^64 en %", "3.75", 100 * 0.95 ** 64)
egal("10 0,95^32 en %", "19", 100 * 0.95 ** 32)
# --- résumé : codon, tailles -----------------------------------------------------------------------------
t = j("mesures/genome/construction/codon/tailles.json")["totaux"]
egal("résumé gain 20b (bits/poids)", "0.12791", t["20b"]["gain_bpp_troncons"])
egal("résumé gain 120b (bits/poids)", "0.12562", t["120b"]["gain_bpp_troncons"])
egal("résumé octets en moins 120b (Go)", "1.80", t["120b"]["gain_octets_troncons"] / 1e9)
egal("résumé 3,3 % d'octets par pas (J1 120b, B/A)", "3.3", 100 * (1 - v["octets_B_sur_A"]))
resultats.append(("  (pour mémoire : octets du fichier, 1 − v1.2/v1.0, en %)", "", f"{100 * (1 - t['120b']['rapport_troncons']):.3f}", "lu", ""))
zc20 = j("mesures/genome/etat-de-l-art/journaux/zero-compte-20b.json")
egal("résumé H(signe | zéro)", "0.9999999967", zc20["H_signe_sachant_zero"])
# --- résumé : la mutation synonyme à 768 experts, le juge ---------------------------------------------------
K = "mesures/genome/construction/juge/kl/"


def kl_positions(nom):
    return {(x["fenetre"], x["position"]): float(x["kl"]) for x in c(K + nom)}


l0 = kl_positions("kl-r1-synonyme-l0-768-positions.csv")
l1 = kl_positions("kl-r1-synonyme-768-positions.csv")
fr768 = kl_positions("kl-r1-frontiere-768-positions.csv")
egal("résumé KL λ = 0, 768, R1", "0.1318", statistics.mean(l0.values()))
egal("13 KL λ = 1, 768, R1", "0.1522", statistics.mean(l1.values()))
egal("résumé KL frontière, 768, R1", "0.2640", statistics.mean(fr768.values()))
egal("résumé λ = 0 divise par deux (rapport)", "0.50", statistics.mean(l0.values()) / statistics.mean(fr768.values()))


def apparier(a, b):
    """d moyen et σ par fenêtres : écart-type (n − 1) des 10 moyennes de fenêtre, divisé par √10."""
    cles = sorted(a)
    assert set(cles) == set(b)
    d = [a[k] - b[k] for k in cles]
    fen = {}
    for k, x in zip(cles, d):
        fen.setdefault(k[0], []).append(x)
    moy = [statistics.mean(v) for v in fen.values()]
    return statistics.mean(d), statistics.stdev(moy) / math.sqrt(len(moy))


dm, s = apparier(l0, l1)
egal("résumé λ = 0 contre λ = 1 sur R1, z", "2.09", -dm / s)
n0 = kl_positions("kl-neuf-moteur-rapide-l0-positions.csv")
n1 = kl_positions("kl-neuf-moteur-rapide-l1-positions.csv")
dm, s = apparier(n0, n1)
egal("résumé λ = 0 contre λ = 1, fenêtres neuves, z", "3.6", -dm / s)
egal("10 d̄ λ0 − λ1 fenêtres neuves", "0.0303", -dm)
egal("10 σ λ0 − λ1 fenêtres neuves", "0.0084", s)
sl0 = kl_positions("kl-neuf-sub-l0-positions.csv")
sfr = kl_positions("kl-neuf-sub-frontiere-positions.csv")
dm, s = apparier(sl0, sfr)
egal("résumé J-K1 d̄ (λ = 0 − frontière, neuves)", "0.1565", -dm)
egal("résumé J-K1 σ par fenêtres", "0.0334", s)
egal("résumé J-K1 z", "4.7", -dm / s)
cs = j("mesures/genome/construction/synonyme/rapide/coder-synonyme-l0.json")
egal("résumé bits du compagnon λ = 0 (utiles)", "2.67", cs["bits_par_poids_utiles"])
egal("résumé, 13 : ×0,94 (20b, r(R/B))", "0.94", j("mesures/genome/construction/juge/vitesse/analyse-20b.json")["r_R_sur_B"])
egal("résumé, 13 : ×1,28 (120b, r(R/B))", "1.28", v["r_R_sur_B"])
egal("résumé ×1,44 (J1, r(B/A) du juge)", "1.44", v["r_B_sur_A"])
tj = j("mesures/genome/construction/juge/J-T0-fichiers.json")
resultats.append(("résumé 3,86 : clés de J-T0-fichiers.json", "", ",".join(list(tj)[:10]), "lu", ""))
# --- résumé : la ronde -------------------------------------------------------------------------------------
gm = c("mesures/genome/genome/csv/graine-mesure-theorie.csv")
p12 = next(x for x in gm if (x["c"], x["p"], x["generateur"]) == ("12", "4", "Hache"))
p10 = next(x for x in gm if (x["c"], x["p"], x["generateur"]) == ("10", "3", "Hache"))
e0 = float(p12["erreur_base"])
lin = float(p12["debit"]) + (float(p10["debit"]) - float(p12["debit"])) * (float(p12["erreur"]) - e0) / (float(p12["erreur"]) - float(p10["erreur"]))
lg = float(p12["debit"]) + (float(p10["debit"]) - float(p12["debit"])) * (math.log(float(p12["erreur"])) - math.log(e0)) / (math.log(float(p12["erreur"])) - math.log(float(p10["erreur"])))
egal("résumé graine, interpolation en log de l'erreur", "3.06", lg)
resultats.append(("  (graine, interpolation linéaire en erreur)", "", f"{lin:.4f}", "lu", "imprimé 3,06 : seule la lecture en log le redonne"))
ct = j("mesures/genome/genome/codons-tourne-l12.json")
tous = [f["sans_perte_total"] for x in ct["tenseurs"] for f in x["fixes"]]
egal("résumé recette sans perte, minimum (12 tenseurs × 5 réglages)", "4.05", min(tous))
egal("résumé recette sans perte, maximum (12 tenseurs × 5 réglages)", "4.37", max(tous))
egal("résumé sans perte de référence (global)", "3.84", ct["global"]["bits_sans_perte"])
d1 = c("mesures/genome/duplication/csv/d1-sans-perte.csv")
egal("résumé D1 gain moyen du parent", "0.0034", statistics.mean(float(x["gain_parent"]) for x in d1))
egal("résumé D1 gain du hasard", "0.0016", statistics.mean(float(x["gain_hasard"]) for x in d1))
egal("04 D1 gain net", "0.0019", statistics.mean(float(x["gain_net"]) for x in d1))
egal("04 D1 matrices", "48", float(len(d1)))
# --- résumé : pistes --------------------------------------------------------------------------------------
gr = j("mesures/pistes/tropicale/garde-resume.json")["variantes"]["marge_B"]
egal("résumé garde : part des bascules au décile", "57.1", 100 * gr["decile"]["part_bascules"])
egal("résumé garde : coût de 80 %", "26.6", 100 * gr["cout_de_80_pour_cent"]["part_cellules"])
sp = [x for x in c("mesures/pistes/spectres/juge/juge-csn.csv") if x["groupe"] == "réel"]
egal("résumé spectres : matrices réelles", "48", float(len(sp)))
egal("résumé spectres : loi de puissance au critère principal", "0",
     float(sum(x["verdict"] == "loi de puissance" for x in sp)))
egal("13 spectres : compatibles au critère amendé", "9", float(sum(x["compatible"] == "True" for x in sp)))
# --- 13 : P3 ------------------------------------------------------------------------------------------------
for nom, imp in (("mesures/mimetisme/P3/juge/etage-B/kl-b0.06-positions.csv", "0.0209"),
                 ("mesures/mimetisme/P3/juge/etage-B/kl-b0.07-positions.csv", "0.0239")):
    egal(f"13 P3 étage B {nom[-18:-14]}", imp, statistics.mean(float(x["kl"]) for x in c(nom)))

w = max(len(r[0]) for r in resultats)
for r in resultats:
    print(f"{r[0]:<{w}} | {r[1]:>8} | {r[2]:>22} | {r[3]} {r[4]}")
faux = sum(r[3] == "FAUX" for r in resultats)
print(f"{len([r for r in resultats if r[3] != 'lu'])} chiffres refaits, {faux} faux")
sys.exit(1 if faux else 0)
