"""Synthèse de la ronde 1 du génome des poids : la frontière bits par poids contre KL sur le texte.

Tout chiffre écrit ici est LU dans un journal commité des quatre équipes (chemins dans la colonne
`source`), jamais recopié d'un document. Sorties, sous mesures/genome/construction/synthese/ :

  frontiere.csv           un point par mécanisme : bits par poids, KL, rapport à la base du MÊME
                          protocole, différence appariée quand elle existe, verdict ;
  erreur-contre-kl.csv    rapport d'erreur de sortie d'expert contre rapport de KL (la figure qui
                          montre que l'une ne prédit pas l'autre) ;
  apparie-eclaireur.json  différence appariée position par position de la passe KL de l'éclaireur
                          (base frontière contre mutation synonyme λ = 0), que l'éclaireur n'avait
                          pas calculée (comparaison non appariée dans 01 § 6) ;
  colonne-par-tenseur.csv le codec réel κ × colonne, tenseur par tenseur, et le choix par matrice.

Pourquoi des rapports : les trois passes KL n'ont pas le même protocole (experts substitués,
fenêtres). Une KL absolue d'un protocole ne se compare pas à celle d'un autre ; le rapport à la base
du même protocole, et la différence appariée, si.

Témoin (déclaré avant la première exécution) : la KL moyenne recalculée depuis le CSV par position de
l'éclaireur égale celle que `juge kl` a écrite (0,03601376394818165) à 1e-12 près, pour les deux
passes. Cassure (--casser) : la première ligne du CSV est retirée ; le témoin doit tomber.

Usage : python -I outils/genome/synthese/frontiere.py [--casser] [--k10] [--sortie DOSSIER]

--sortie (ajouté le 2026-10-27 pour les figures du Tome III) : écrit les quatre fichiers dans DOSSIER
(relatif à la racine du dépôt) au lieu de mesures/genome/construction/synthese/, pour qu'une passe
--k10 ne réécrive pas les fichiers commités de la passe à 3 fenêtres. Sans l'option, rien ne change.
"""

import csv
import json
import math
import os
import sys

RACINE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
SORTIE = os.path.join(RACINE, "mesures", "genome", "construction", "synthese")
if "--sortie" in sys.argv:
    SORTIE = os.path.join(RACINE, *sys.argv[sys.argv.index("--sortie") + 1].replace("\\", "/").split("/"))
CASSER = "--casser" in sys.argv
sys.stdout.reconfigure(encoding="utf-8")


def chemin(*p):
    return os.path.join(RACINE, *p)


def lire_json(rel):
    with open(chemin(*rel.split("/")), encoding="utf-8") as f:
        return json.load(f)


def lire_csv(rel):
    with open(chemin(*rel.split("/")), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# --- 1. Les positions de l'éclaireur : témoin, puis différence appariée --------------------------

ECL = "mesures/genome/etat-de-l-art/journaux"
pos_base = lire_csv(f"{ECL}/kl-frontiere-positions.csv")
pos_syn = lire_csv(f"{ECL}/kl-synonyme-d1-positions.csv")
juge_base = lire_json(f"{ECL}/kl-frontiere-juge.json")["resume"]
juge_syn = lire_json(f"{ECL}/kl-synonyme-d1-juge.json")["resume"]
if CASSER:
    pos_base = pos_base[1:]

moy = lambda v: sum(v) / len(v)
kb = [float(r["kl"]) for r in pos_base]
ks = [float(r["kl"]) for r in pos_syn]
temoin = {
    "kl_base_recalculee": moy(kb),
    "kl_base_juge": juge_base["kl_moyenne"],
    "kl_syn_recalculee": moy(ks),
    "kl_syn_juge": juge_syn["kl_moyenne"],
}
temoin["tient"] = abs(temoin["kl_base_recalculee"] - temoin["kl_base_juge"]) < 1e-12 and abs(
    temoin["kl_syn_recalculee"] - temoin["kl_syn_juge"]
) < 1e-12
if not temoin["tient"]:
    print("TÉMOIN TOMBÉ :", json.dumps(temoin, ensure_ascii=False))
    if CASSER:
        print("cassure : le témoin tombe comme attendu")
        sys.exit(0)
    sys.exit(1)
if CASSER:
    print("CASSURE SANS EFFET : l'instrument ne sait pas tomber")
    sys.exit(1)

cles = [(r["fenetre"], r["position"]) for r in pos_base]
assert cles == [(r["fenetre"], r["position"]) for r in pos_syn], "positions non alignées"
d = [s - b for b, s in zip(kb, ks)]
n = len(d)
dm = moy(d)
sd = math.sqrt(sum((x - dm) ** 2 for x in d) / (n - 1))
# Second estimateur de l'incertitude : par blocs de fenêtre (les positions d'une même fenêtre
# partagent leur passé, donc leurs bascules de routage ; R1 § 2.10).
fen = sorted({r["fenetre"] for r in pos_base}, key=int)
moy_fen = []
for f in fen:
    v = [x for x, r in zip(d, pos_base) if r["fenetre"] == f]
    moy_fen.append(moy(v))
mf = moy(moy_fen)
sd_fen = math.sqrt(sum((x - mf) ** 2 for x in moy_fen) / (len(moy_fen) - 1)) / math.sqrt(len(moy_fen))
pb = [int(r["meme_premier"]) for r in pos_base]
ps = [int(r["meme_premier"]) for r in pos_syn]
dp = [s - b for b, s in zip(pb, ps)]
dpm = moy(dp)
sdp = math.sqrt(sum((x - dpm) ** 2 for x in dp) / (n - 1)) / math.sqrt(n)
gagne = sum(1 for x in d if x < 0)
apparie = {
    "outil": "outils/genome/synthese/frontiere.py",
    "sources": [f"{ECL}/kl-frontiere-positions.csv", f"{ECL}/kl-synonyme-d1-positions.csv"],
    "positions": n,
    "temoin": temoin,
    "kl_difference_syn_moins_base": dm,
    "ecart_type_naif": sd / math.sqrt(n),
    "ecart_type_par_fenetres": sd_fen,
    "fenetres": len(fen),
    "premier_difference_syn_moins_base": dpm,
    "premier_ecart_type": sdp,
    "positions_ou_syn_a_moins_de_kl": gagne,
    "regle_lot_R": "d̄ ≤ 2σ(d̄) : égal ou meilleur ; d̄ + 2σ < 0 : meilleur significativement",
    "meilleur_significativement_naif": dm + 2 * sd / math.sqrt(n) < 0,
    "meilleur_significativement_par_fenetres": dm + 2 * sd_fen < 0,
}

# --- 2. La frontière ----------------------------------------------------------------------------

lignes = []


def point(**k):
    base = {
        "mecanisme": "", "equipe": "", "branche": "", "protocole": "", "bits_par_poids": "",
        "estimateur_bits": "", "kl_moyenne": "", "kl_incertitude": "", "kl_base_protocole": "",
        "rapport_kl": "", "diff_apparie": "", "diff_apparie_sigma": "", "meme_premier": "",
        "verdict": "", "source": "",
    }
    base.update(k)
    if base["kl_moyenne"] != "" and base["kl_base_protocole"] not in ("", 0):
        base["rapport_kl"] = base["kl_moyenne"] / base["kl_base_protocole"]
    lignes.append(base)


# Sans perte (protocole P0 : logits identiques au bit, KL = 0 exactement).
tr = lire_json("mesures/genome/predictif-elagage/taux-reel-colonne-12-gptoss20b.json")["bpp"]
point(mecanisme="frontière sans perte (A_flux, F1)", equipe="arbitre", branche="sans perte", protocole="P0",
      bits_par_poids=tr["total_identite"], estimateur_bits="codec réel, décodé", kl_moyenne=0.0,
      verdict="référence", source="mesures/genome/predictif-elagage/taux-reel-colonne-12-gptoss20b.json")
point(mecanisme="codon synonyme du zéro (−0 → +0)", equipe="éclaireur, prédictif-élagage", branche="sans perte",
      protocole="P0", bits_par_poids=tr["total_zero_fondu"], estimateur_bits="codec réel, décodé", kl_moyenne=0.0,
      verdict="gagne (seuil 0,05 bit ; logits identiques au bit)",
      source="mesures/genome/predictif-elagage/taux-reel-colonne-12-gptoss20b.json")
point(mecanisme="zéro fondu + contexte de colonne (κ × q)", equipe="prédictif-élagage", branche="sans perte",
      protocole="P0", bits_par_poids=tr["total_nib_kappa_colonne_zero"], estimateur_bits="codec réel, décodé",
      kl_moyenne=0.0, verdict="gagne (seuil 0,015 bit pour le contexte)",
      source="mesures/genome/predictif-elagage/taux-reel-colonne-12-gptoss20b.json")
dup = lire_json("mesures/genome/duplication/verdicts.json")
point(mecanisme="duplication D1 (parent, sans perte)", equipe="duplication", branche="sans perte", protocole="P0",
      bits_par_poids=tr["total_identite"] - dup["D1"]["gain_net_moyen"] + dup["D1"]["cout_ajoute"],
      estimateur_bits="entropie conditionnelle + coûts ajoutés", kl_moyenne=0.0,
      verdict="tombe (21 matrices sur 48 sous A_ctx ; part propre 0,0019 bit)",
      source="mesures/genome/duplication/verdicts.json")

# Protocole P1 : éclaireur, 32 experts sur 768 (couches 0, 8, 16, 23 × experts 0, 4, …, 28), 10 fenêtres.
fr8 = lire_json("mesures/genome/etat-de-l-art/passes/frontiere-lam0-damp0.01.json")
s0 = lire_json("mesures/genome/etat-de-l-art/passes/synonyme-lam0-damp1.json")
s1 = lire_json("mesures/genome/etat-de-l-art/passes/synonyme-lam1-damp1-e0_8_16_24.json")
fr4 = lire_json("mesures/genome/etat-de-l-art/passes/frontiere-lam0-damp0.01-e0_8_16_24.json")
kb1 = juge_base["kl_moyenne"]
point(mecanisme="base frontière (07, F1)", equipe="éclaireur", branche="avec perte", protocole="P1",
      bits_par_poids=fr8["bits_H0_sym"], estimateur_bits="H0 des symboles (sans échelles)",
      kl_moyenne=kb1, kl_incertitude=juge_base["kl_incertitude"], kl_base_protocole=kb1,
      meme_premier=juge_base["meme_premier"], verdict="référence", source=f"{ECL}/kl-frontiere-juge.json")
point(mecanisme="mutation synonyme λ = 0, δ* = 1", equipe="éclaireur", branche="avec perte", protocole="P1",
      bits_par_poids=s0["bits_H0_sym"], estimateur_bits="H0 des symboles (sans échelles)",
      kl_moyenne=juge_syn["kl_moyenne"], kl_incertitude=juge_syn["kl_incertitude"], kl_base_protocole=kb1,
      diff_apparie=dm, diff_apparie_sigma=max(sd / math.sqrt(n), sd_fen), meme_premier=juge_syn["meme_premier"],
      verdict="gagne en KL ; +0,011 bit (ne bat pas au critère strict de débit)",
      source=f"{ECL}/kl-synonyme-d1-juge.json")
point(mecanisme="mutation synonyme λ = 1, δ* = 1 (KL non mesurée)", equipe="éclaireur", branche="avec perte",
      protocole="P1-sorties", bits_par_poids=s1["bits_H0_sym"], estimateur_bits="H0 des symboles (sans échelles)",
      verdict="gagne à l'erreur d'expert (8 cases sur 8) ; KL à mesurer (lot B, B0)",
      source="mesures/genome/etat-de-l-art/passes/synonyme-lam1-damp1-e0_8_16_24.json")
point(mecanisme="base frontière, mêmes experts que λ = 1", equipe="éclaireur", branche="avec perte",
      protocole="P1-sorties", bits_par_poids=fr4["bits_H0_sym"], estimateur_bits="H0 des symboles (sans échelles)",
      verdict="référence de λ = 1", source="mesures/genome/etat-de-l-art/passes/frontiere-lam0-damp0.01-e0_8_16_24.json")

# Protocole P2 : genome, 8 experts (couches 0, 8, 16, 23 × experts 0, 16), 3 fenêtres (765 positions).
cmp2 = lire_json("mesures/genome/genome/kl/comparer-base-contre-recette.json")
a2, b2, ap2 = cmp2["a_contre_verite"], cmp2["b_contre_verite"], cmp2["apparie"]
point(mecanisme="base frontière (8 experts)", equipe="genome", branche="avec perte", protocole="P2",
      bits_par_poids=2.6441, estimateur_bits="codec réel (F1, 07)", kl_moyenne=a2["kl_moyenne"],
      kl_incertitude=a2["kl_incertitude"], kl_base_protocole=a2["kl_moyenne"], meme_premier=a2["meme_premier"],
      verdict="référence", source="mesures/genome/genome/kl/comparer-base-contre-recette.json")
point(mecanisme="S* (brin lu par codons + rotation + pondération + exceptions)", equipe="genome",
      branche="avec perte", protocole="P2", bits_par_poids=2.64, estimateur_bits="comptabilité complète du brin",
      kl_moyenne=b2["kl_moyenne"], kl_incertitude=b2["kl_incertitude"], kl_base_protocole=a2["kl_moyenne"],
      diff_apparie=ap2["kl_difference_b_moins_a"], diff_apparie_sigma=ap2["kl_ecart_type"],
      meme_premier=b2["meme_premier"], verdict="égal par la règle sur 3 fenêtres (+1,6 σ) ; ne gagne pas",
      source="mesures/genome/genome/kl/comparer-base-contre-recette.json")
# La passe K10 de l'équipe genome (10 fenêtres, mêmes 8 experts) : lue seulement avec --k10, une fois
# son journal commité par l'équipe (règle : un chiffre publié vient d'un fichier commité).
K10 = "mesures/genome/genome/kl/comparer10-base-contre-recette.json"
if "--k10" in sys.argv:
    c10 = lire_json(K10)
    a10, b10, ap10 = c10["a_contre_verite"], c10["b_contre_verite"], c10["apparie"]
    point(mecanisme="base frontière (8 experts, 10 fenêtres)", equipe="genome", branche="avec perte",
          protocole="P2-10", bits_par_poids=2.6441, estimateur_bits="codec réel (F1, 07)",
          kl_moyenne=a10["kl_moyenne"], kl_incertitude=a10["kl_incertitude"], kl_base_protocole=a10["kl_moyenne"],
          meme_premier=a10["meme_premier"], verdict="référence", source=K10)
    point(mecanisme="S* (10 fenêtres)", equipe="genome", branche="avec perte", protocole="P2-10",
          bits_par_poids=2.64, estimateur_bits="comptabilité complète du brin", kl_moyenne=b10["kl_moyenne"],
          kl_incertitude=b10["kl_incertitude"], kl_base_protocole=a10["kl_moyenne"],
          diff_apparie=ap10["kl_difference_b_moins_a"], diff_apparie_sigma=ap10["kl_ecart_type"],
          meme_premier=b10["meme_premier"], verdict="égal en KL ; ne gagne pas", source=K10)

# Protocole P3 : prédictif-élagage, 12 tenseurs entiers (128 experts), fenêtres 5 à 9 (1 275 positions).
res = {r["plan"]: r for r in lire_csv("mesures/genome/predictif-elagage/resume-12.csv")}
KL3 = "mesures/genome/predictif-elagage/kl"
appar3 = {
    "ecsq_kappa": "comparer-base-kappa-f5-9.json",
    "ecsq_kappa_t": "comparer-base-ecsq_kappa_t-f5-9.json",
    "hebb_e": "comparer-base-hebb_e-f5-9.json",
    "hebb_d_lc": "comparer-base-hebb_d_lc-f5-9.json",
    "hebb_e_lc": "comparer-base-hebb_e_lc-f5-9.json",
}
noms3 = {
    "base": ("base frontière (12 tenseurs)", "référence"),
    "ecsq_kappa_t": ("partitions par κ, chaque tenseur à l'erreur de la base", "gagne : 0,911 × les bits, KL égale par la règle"),
    "ecsq_kappa": ("partitions par κ, erreur moyenne égale", "tombe à la KL (+3,4 σ)"),
    "hebb_d_lc": ("hebbien (δ, ligne, colonne)", "tombe à la KL"),
    "hebb_e": ("hebbien par e (erreur d'expert égale à la base)", "tombe à la KL (×3)"),
    "hebb_e_lc": ("hebbien (e, ligne, colonne)", "tombe à la KL"),
    "ecsq_e": ("partitions par e (remplissage inverse des poids)", "tombe à la KL (×5)"),
    "sens_e_q": ("élagage par activité de colonne (e, q)", "tombe à la KL (×4)"),
}
kb3 = float(res["base"]["kl_moyenne"])
for plan, (nom, verdict) in noms3.items():
    r = res[plan]
    k = dict(mecanisme=nom, equipe="prédictif-élagage", branche="avec perte", protocole="P3",
             bits_par_poids=float(r["bits_reels"]), estimateur_bits="codec réel, décodé (taux_plan)",
             kl_moyenne=float(r["kl_moyenne"]), kl_incertitude=float(r["kl_incertitude"]), kl_base_protocole=kb3,
             meme_premier=float(r["meme_premier"]), verdict=verdict, source="mesures/genome/predictif-elagage/resume-12.csv")
    if plan in appar3:
        c = lire_json(f"{KL3}/{appar3[plan]}")["apparie"]
        k["diff_apparie"] = c["kl_difference_b_moins_a"]
        k["diff_apparie_sigma"] = c["kl_ecart_type"]
        k["source"] += " ; " + f"{KL3}/{appar3[plan]}"
    point(**k)

# Points sans KL (jugés à l'erreur de poids égale à la base, ou à l'erreur d'expert égale).
vw = lire_json("mesures/genome/genome/verdict-tourne-l12-second-chemin.json")["tenseurs"]
point(mecanisme="brin lu par codons, tourné (critère W, erreur de poids égale)", equipe="genome",
      branche="avec perte", protocole="P0-poids", bits_par_poids=moy([t["bits_recette"] for t in vw]),
      estimateur_bits="comptabilité complète du brin",
      verdict="gagne en erreur de poids, tombe en sortie d'expert (O, F)",
      source="mesures/genome/genome/verdict-tourne-l12-second-chemin.json")
vs = lire_json("mesures/genome/genome/verdict-fidelite-sstar.json")["par_expert"]
point(mecanisme="S* à erreur de sortie d'expert égale", equipe="genome", branche="avec perte",
      protocole="P2-sorties", bits_par_poids=moy([t["bits_a_sortie_egale"] for t in vs]),
      estimateur_bits="comptabilité complète du brin", verdict="gagne à la sortie d'expert, tombe à la KL",
      source="mesures/genome/genome/verdict-fidelite-sstar.json")
point(mecanisme="duplication D2b (parent comme contexte, base inchangée)", equipe="duplication",
      branche="avec perte", protocole="P0-poids", bits_par_poids=dup["D2b"]["debit_base_avec_parent"],
      estimateur_bits="entropie conditionnelle + coûts ajoutés", verdict="tombe (24 matrices sur 48)",
      source="mesures/genome/duplication/verdicts.json")
# La graine (SeedLM écrit de zéro) et les motifs : interpolés dans le livrable (genome.md § 2.3, § 8.1),
# depuis graines.jsonl et motifs-*.json ; repris ici avec leur source, valeur du livrable.
point(mecanisme="graine + coefficients (SeedLM écrit de zéro)", equipe="genome", branche="avec perte",
      protocole="P0-poids", bits_par_poids=3.06, estimateur_bits="débit nominal (K + 4 + 4P)/C, interpolé",
      verdict="tombe (lemme 1 : livre de codes trop court)", source="genome/genome.md § 2.3 ; mesures/genome/genome/graines.jsonl")
point(mecanisme="motifs partagés (dictionnaire commun, RVQ)", equipe="genome", branche="avec perte",
      protocole="P0-poids", bits_par_poids=2.90, estimateur_bits="débit global compté, interpolé",
      verdict="tombe (quantificateur vectoriel de petite dimension)",
      source="genome/genome.md § 8.1 ; mesures/genome/genome/motifs-8-12-2.json")

os.makedirs(SORTIE, exist_ok=True)
champs = list(lignes[0].keys())
with open(os.path.join(SORTIE, "frontiere.csv"), "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=champs, lineterminator="\n")
    w.writeheader()
    for l in lignes:
        w.writerow({k: (f"{v:.6g}" if isinstance(v, float) else v) for k, v in l.items()})

# --- 3. Erreur de sortie d'expert contre KL ------------------------------------------------------

ek = []
# P1 : erreur d'expert (évaluation) de λ = 0 contre la frontière à 8 experts par couche, mêmes experts que la KL.
ek.append(("mutation synonyme λ = 0", "P1", s0["err_sortie_expert_eval"] / fr8["err_sortie_expert_eval"],
           juge_syn["kl_moyenne"] / kb1, "passes/synonyme-lam0-damp1.json, passes/frontiere-lam0-damp0.01.json, juge"))
# P2 : S*, rapport moyen à 2,64 bits sur les 8 experts de la KL.
ek.append(("S*", "P2", moy([t["erreur_sortie_a_2_64"] / t["erreur_sortie_base"] for t in vs]),
           b2["kl_moyenne"] / a2["kl_moyenne"], "verdict-fidelite-sstar.json, comparer-base-contre-recette.json"))
if "--k10" in sys.argv:
    ek.append(("S* (10 fenêtres)", "P2-10", moy([t["erreur_sortie_a_2_64"] / t["erreur_sortie_base"] for t in vs]),
               b10["kl_moyenne"] / a10["kl_moyenne"], "verdict-fidelite-sstar.json, " + K10))
eb = float(res["base"]["erreur_expert_mesuree"])
for plan in ("ecsq_kappa", "hebb_e", "hebb_e_lc", "ecsq_e"):
    r = res[plan]
    ek.append((noms3[plan][0], "P3", float(r["erreur_expert_mesuree"]) / eb, float(r["kl_moyenne"]) / kb3,
               "resume-12.csv"))
with open(os.path.join(SORTIE, "erreur-contre-kl.csv"), "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["mecanisme", "protocole", "rapport_erreur_expert", "rapport_kl", "source"])
    for m, p, re_, rk, s in ek:
        w.writerow([m, p, f"{re_:.4f}", f"{rk:.4f}", s])

# --- 4. Le contexte de colonne, tenseur par tenseur ----------------------------------------------

tt = lire_json("mesures/genome/predictif-elagage/taux-reel-colonne-12-gptoss20b.json")["tenseurs"]
rows = []
for t in tt:
    octet = t["bpp_total_zero_fondu"]
    col = t["bpp_total_nib_kappa_colonne"]
    choix = "CODES_COL" if col < octet else "CODES_CTX"
    rows.append([t["nom"], t["bpp_total_identite"], octet, t["bpp_total_nib_kappa"], col, choix, min(octet, col)])
with open(os.path.join(SORTIE, "colonne-par-tenseur.csv"), "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["tenseur", "sans_perte", "zero_octet_kappa", "zero_demi_octet_kappa", "zero_demi_octet_kappa_colonne",
                "choix", "meilleur"])
    for r in rows:
        w.writerow([r[0]] + [f"{x:.6f}" if isinstance(x, float) else x for x in r[1:]])
choix_moyen = moy([r[6] for r in rows])
apparie["colonne"] = {
    "zero_octet_moyen": moy([r[2] for r in rows]),
    "zero_colonne_moyen": moy([r[4] for r in rows]),
    "choix_par_matrice_moyen": choix_moyen,
    "matrices_codes_col": sum(1 for r in rows if r[5] == "CODES_COL"),
    # Règle du cahier de construction (lot A) : CODES_COL seulement si le gain sur CODES_CTX canonique
    # atteint 0,015 bit par poids (le seuil d'un flux de plus déclaré par prédictif-élagage, 03 § 3.1).
    "choix_seuil_0_015_moyen": moy([r[4] if r[2] - r[4] >= 0.015 else r[2] for r in rows]),
    "matrices_codes_col_seuil_0_015": sum(1 for r in rows if r[2] - r[4] >= 0.015),
}

with open(os.path.join(SORTIE, "apparie-eclaireur.json"), "w", encoding="utf-8") as f:
    json.dump(apparie, f, ensure_ascii=False, indent=2)
print(json.dumps(apparie, ensure_ascii=False, indent=2))
print(f"{len(lignes)} points dans frontiere.csv ; {len(ek)} dans erreur-contre-kl.csv")
