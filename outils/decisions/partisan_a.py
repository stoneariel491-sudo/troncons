"""Les chiffres du partisan de l'architecture A (« l'exactitude et l'ingénierie d'abord »).

Rôle : chiffrer, avec l'équation du jeton de l'étude 07 (outils/07-synthese/plafonds.py,
chargé tel quel, rien n'est recopié), ce que l'architecture A sacrifie face à B, ce que
coûte de préparer B dans le format de A, et les budgets que la première version de A
doit tenir. Rien n'est mesuré ici : tout est calculé sur des mesures commitées.

Ce que l'outil calcule :
  S1  témoins : refaire quatre chiffres publiés par l'étude 07 (seuil déclaré : 1 %) ;
  S2  le sacrifice : A, A0, B1, B2 par scénario de localité, disque chiffré (2,58 Go/s)
      et non chiffré (6,0, annonce) ; la part des usages servie par la base et l'erreur
      relative moyenne qu'elle ajoute (linéarité de HIGGS, ordre de grandeur) ;
  S3  le gain de B1 quand une part f des défauts doit être servie exacte (complément lu
      sur le chemin critique) ;
  S4  le coût, pour A, d'un format coupé en base et complément dès la v1 (borne sans
      conditionnement : entropies d'ordre 0 mesurées sur gpt-oss-20b) ;
  S5  les budgets de la carte : débit minimal du décodeur et ralentissement maximal des
      noyaux de la passe avant pour que la carte ne prenne pas le maximum ;
  S6  le repli en mémoire paginable (cache tiède copié par le processeur) ;
  S7  un tronçon par expert (trois matrices d'un seul tenant) : la taille d'une lecture ;
  S8  le jumeau gpt-oss-20b : à quel budget de RAM il exerce encore le disque, et le
      témoin « la mémoire de pointe ne dépend pas du modèle » ;
  S9  le plafond de A contre la part lue du disque (table de décision pour la trace) ;
  S10 le cache KV de gpt-oss-120b (métadonnées lues dans l'en-tête GGUF) ;
  S11 le temps de lecture d'une réécriture du fichier ;
  S12 la fenêtre de travail minimale (tampons de d couches au lieu de deux jetons entiers) ;
  S13 la part f de défauts exacts au-delà de laquelle B1 ne dépasse plus A ;
  S14 A contre la base exploratoire de l'autre agent (à remplacer par mesures/gpt-oss.md) ;
  S15 le risque de B selon la localité (part servie par la base, rapportée au bruit du format) ;
  S16 ce que coûte une réécriture du fichier (codeur de l'étude 03, mesuré) ;
  S17 les seuils de la première version, dérivés de grandeurs mesurées.

Cassure : --casser remet le taux sans perte de A à 1 (octets non codés) ; les témoins
qui en dépendent (A, A0) doivent tomber, celui de B1 tenir.

Utilisation (depuis la racine du dépôt) :
  python -I -X utf8 outils/decisions/partisan_a.py [--casser] > decisions/journaux/partisan-a/partisan-a.json
  (écrit aussi les CSV sous decisions/journaux/partisan-a/csv/ quand --casser est absent)
"""
from __future__ import annotations

import csv
import importlib.util
import json
import math
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", ".."))
SORTIE_CSV = os.path.join(RACINE, "decisions", "journaux", "partisan-a", "csv")


def charger_plafonds():
    chemin = os.path.join(RACINE, "outils", "07-synthese", "plafonds.py")
    spec = importlib.util.spec_from_file_location("plafonds", chemin)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["plafonds"] = mod
    spec.loader.exec_module(mod)
    return mod


P = charger_plafonds()
d, moe, BETAS, R_CLASSES = P.d, P.moe, P.BETAS, P.R_CLASSES

# Mesures reprises (chacune avec son journal) ------------------------------------
MEMCPY = {"secteur": (7.5, "mesuré ici [01]", "copie processeur vers tampon d'envoi, cité par 07 § 6"),
          "batterie": (1.25, "mesuré ici [01]", "idem, sur batterie")}
DISQUE_16M_QD1 = (2.819, "mesuré ici [01]", "01-machine § 2.4 : 16 Mio aléatoire QD 1, bruit 1 %")
DISQUE_4M_QD1 = (2.314, "mesuré ici [01]", "01-machine § 2.4 : 4 Mio aléatoire QD 1")
DISQUE_NON_CHIFFRE = (6.0, "littérature (Samsung, non reproduit)", "07 § 4.2 : borne haute")
# Entropies d'ordre 0 de la base et du complément (07, raffinement-mxfp4-gptoss20b.json),
# et le sans-perte à trois classes de gpt-oss-120b (03).
BITS_ECHELLES = 0.0344
SURCOUT_TUILE = 1.003
BITS_SANS_PERTE_C3 = 4.25 / R_CLASSES[0]           # 3,8545 bits/poids, échelles comprises


def charger_inventaire() -> dict:
    with open(os.path.join(RACINE, "fondations", "journaux", "07-synthese", "inventaire-gptoss.json"),
              encoding="utf-8") as f:
        inv = json.load(f)
    sortie = {}
    for x in inv["modeles"]:
        sortie[x["modele"]] = {"nom": x["modele"], "A": x["A_octets_toujours_lus"] / 1e9,
                               "R": x["R_octets_experts_par_jeton"] / 1e9,
                               "E_tot": x["octets_tous_experts"] / 1e9,
                               "e_expert": x["e_octets_par_expert"],
                               "matrice": x["matrice_contigue_par_expert_octets"][0],
                               "biais": x["biais_contigu_par_expert_octets"][0],
                               "couches": x["couches"], "E": x["experts_par_couche_E"],
                               "taille_fichier": x["taille_fichier_octets"]}
    return sortie


def archis(m, beta, *, D_disque, r_A, raf, M_ram=11.0, D_dec=None, D_gemv=None):
    D_dec = d("decodeur_classes") if D_dec is None else D_dec
    rb2 = raf["base_2b"]["r_base"]
    kw = dict(beta=beta, D_disque=D_disque, D_dec=D_dec, D_gemv=D_gemv)
    return {
        "A": moe(m, M_ram=M_ram, r_ram=r_A, r_defaut=r_A, **kw),
        "A0": moe(m, M_ram=0.0, r_ram=r_A, r_defaut=r_A, **kw),
        "B1": moe(m, M_ram=M_ram, r_ram=R_CLASSES[0], r_defaut=rb2, **kw),
        "B2": moe(m, M_ram=M_ram, r_ram=rb2, r_defaut=rb2, lossy_ram=True, **kw),
    }


def main():
    casser = "--casser" in sys.argv
    inv = charger_inventaire()
    m120, m20 = inv["gpt-oss-120b"], inv["gpt-oss-20b"]
    raf = P.charger_raffinement()
    err_base = raf["base_2b"]["erreur_relative"]
    r_A = 1.0 if casser else R_CLASSES[0]
    Dx = d("disque_expert")
    out = {"outil": "outils/decisions/partisan_a.py", "casser": casser,
           "repris": {"plafonds": "outils/07-synthese/plafonds.py (importé)",
                      "memcpy": MEMCPY, "disque_16M_QD1": DISQUE_16M_QD1,
                      "disque_4M_QD1": DISQUE_4M_QD1, "disque_non_chiffre": DISQUE_NON_CHIFFRE}}

    # S1. Témoins : quatre chiffres de l'étude 07 (fondations/07-ce-qui-manque.md § 4).
    lru = BETAS["lru_cale"]
    a_lru = archis(m120, lru, D_disque=Dx, r_A=r_A, raf=raf)
    a_uni = archis(m120, 1.0, D_disque=Dx, r_A=r_A, raf=raf)
    tem = {"A_lru_6_24": (6.24, a_lru["A"]["jetons_s_plafond"]),
           "A0_lru_3_59": (3.59, a_lru["A0"]["jetons_s_plafond"]),
           "B1_lru_8_88": (8.88, a_lru["B1"]["jetons_s_plafond"]),
           "A_uniforme_2_05": (2.05, a_uni["A"]["jetons_s_plafond"])}
    out["S1_temoins"] = {k: {"attendu": a, "obtenu": o,
                             "tient": abs(o - a) / a <= 0.01 + 0.005 / a} for k, (a, o) in tem.items()}
    out["S1_temoins_tiennent"] = all(v["tient"] for v in out["S1_temoins"].values())
    if casser:
        json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
        print()
        return

    # S2. Le sacrifice, par scénario et par disque.
    s2 = {}
    lignes = []
    for disque, D in (("chiffre_2_58", Dx), ("non_chiffre_6_0", DISQUE_NON_CHIFFRE[0])):
        for nb, beta in BETAS.items():
            a = archis(m120, beta, D_disque=D, r_A=r_A, raf=raf)
            cas = {}
            for k, v in a.items():
                part = v["part_avec_perte"]
                cas[k] = {"plafond": v["jetons_s_plafond"], "serie": v["jetons_s_serie"],
                          "etage_limitant": v["etage_limitant"], "part_servie_par_la_base": part,
                          "erreur_relative_moyenne_ajoutee": part * err_base,
                          "ram_pointe_go": v["ram_pointe_go"],
                          "T_ms": [v["T_disque_ms"], v["T_pcie_ms"], v["T_carte_ms"]]}
                lignes.append([disque, nb, k, round(v["jetons_s_plafond"], 3), round(v["jetons_s_serie"], 3),
                               v["etage_limitant"], round(part, 4), round(part * err_base, 5)])
            cas["A_sur_B1"] = a["A"]["jetons_s_plafond"] / a["B1"]["jetons_s_plafond"]
            cas["A_sur_B2"] = a["A"]["jetons_s_plafond"] / a["B2"]["jetons_s_plafond"]
            s2[f"{disque}/{nb}"] = cas
    out["S2_sacrifice"] = {"erreur_relative_de_la_base": err_base, "cas": s2}
    os.makedirs(SORTIE_CSV, exist_ok=True)
    with open(os.path.join(SORTIE_CSV, "sacrifice-a-contre-b.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["disque", "scenario", "architecture", "plafond", "serie", "etage_limitant",
                    "part_base", "erreur_rel_moyenne"])
        w.writerows(lignes)

    # S3. B1 quand une part f des défauts doit être servie exacte.
    bits_base = raf["base_2b"]["bits_par_poids"]                     # 2,684, échelles comprises
    bits_comp = raf["base_2b"]["H_complement"] * SURCOUT_TUILE        # 1,222
    s3 = []
    for f_ in (0.0, 0.25, 0.5, 0.75, 1.0):
        r_eff = 4.25 / (bits_base + f_ * bits_comp)
        ligne = {"f_defauts_exacts": f_, "bits_lus_par_poids_au_defaut": bits_base + f_ * bits_comp,
                 "r_defaut": r_eff}
        for nb, beta in BETAS.items():
            v = moe(m120, beta=beta, M_ram=11, r_ram=R_CLASSES[0], r_defaut=r_eff, D_disque=Dx,
                    D_dec=d("decodeur_classes"))
            ligne[nb] = v["jetons_s_plafond"]
        s3.append(ligne)
    out["S3_B1_contre_part_exacte"] = {"bits_base": bits_base, "bits_complement": bits_comp, "lignes": s3}
    with open(os.path.join(SORTIE_CSV, "b1-contre-part-exacte.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["f", "bits_lus", "uniforme", "lru_cale", "belady_cale"])
        for x in s3:
            w.writerow([x["f_defauts_exacts"], round(x["bits_lus_par_poids_au_defaut"], 4),
                        round(x["uniforme"], 3), round(x["lru_cale"], 3), round(x["belady_cale"], 3)])

    # S4. Le format coupé dès la v1 : taux de A s'il lit base + complément (ordre 0).
    bits_coupe = bits_base + bits_comp
    r_coupe = 4.25 / bits_coupe
    s4 = {"bits_coupe_ordre0": bits_coupe, "r_coupe": r_coupe, "bits_C3": BITS_SANS_PERTE_C3,
          "r_C3": R_CLASSES[0], "perte_relative_taux": 1 - r_coupe / R_CLASSES[0], "plafonds": {}}
    for nb, beta in BETAS.items():
        a3 = moe(m120, beta=beta, M_ram=11, r_ram=R_CLASSES[0], r_defaut=R_CLASSES[0], D_disque=Dx,
                 D_dec=d("decodeur_classes"))
        ac = moe(m120, beta=beta, M_ram=11, r_ram=r_coupe, r_defaut=r_coupe, D_disque=Dx,
                 D_dec=d("decodeur_classes"))
        s4["plafonds"][nb] = {"A_C3": a3["jetons_s_plafond"], "A_coupe": ac["jetons_s_plafond"],
                              "ecart": ac["jetons_s_plafond"] / a3["jetons_s_plafond"] - 1}
    out["S4_format_coupe_des_v1"] = s4

    # S5. Budgets de la carte.
    s5 = {}
    for disque, D in (("chiffre_2_58", Dx), ("non_chiffre_6_0", DISQUE_NON_CHIFFRE[0])):
        for nb, beta in BETAS.items():
            v = moe(m120, beta=beta, M_ram=11, r_ram=r_A, r_defaut=r_A, D_disque=D,
                    D_dec=d("decodeur_classes"))
            Td, Tp = v["T_disque_ms"] / 1e3, v["T_pcie_ms"] / 1e3
            hv = v["h_v"]
            octets_dec = (1 - hv) * m120["R"]
            t_gemv = (m120["A"] + m120["R"]) / d("gemv")
            # La carte ne doit pas prendre le maximum : son temps doit rester sous celui de
            # l'étage le plus lent des deux autres. Aucune marge au jugé (une première
            # version mettait 1,5 sur le disque chiffré, sans grandeur mesurée qui la fonde :
            # retirée). Ce que la carte coûte au plancher en série se lit à part (élasticité).
            cible = max(Td, Tp)
            reste = cible - t_gemv
            s5[f"{disque}/{nb}"] = {
                "T_disque_ms": Td * 1e3, "T_pcie_ms": Tp * 1e3, "cible_carte_ms": cible * 1e3,
                "D_decodeur_min_go_s": octets_dec / reste if reste > 0 else None,
                "ralentissement_max_noyaux": (cible - octets_dec / d("decodeur_classes")) / t_gemv,
                "T_carte_mesures_actuelles_ms": v["T_carte_ms"],
                # part de la carte dans le plancher en série : ce que coûte 10 % de carte en plus
                "part_carte_dans_serie": v["T_carte_ms"] / (1e3 / v["jetons_s_serie"]),
                "marge_carte_sur_max": cible * 1e3 / v["T_carte_ms"]}
    out["S5_budgets_carte"] = s5

    # S6. Repli en mémoire paginable : chaque succès en RAM passe par une copie du processeur.
    s6 = {}
    for nb, beta in BETAS.items():
        v = moe(m120, beta=beta, M_ram=11, r_ram=r_A, r_defaut=r_A, D_disque=Dx, D_dec=d("decodeur_classes"))
        o_ram = v["h_r"] * m120["R"] / r_A
        o_disque = v["h_s"] * m120["R"] / r_A
        s6[nb] = {"T_disque_ms": v["T_disque_ms"],
                  # succès RAM copiés ; défauts lus directement dans un tampon visible (cas 1)
                  # ou lus en paginable puis copiés aussi (cas 2).
                  "T_cpu_secteur_ms_cas1": o_ram / MEMCPY["secteur"][0] * 1e3,
                  "T_cpu_secteur_ms_cas2": (o_ram + o_disque) / MEMCPY["secteur"][0] * 1e3,
                  "T_cpu_batterie_ms_cas1": o_ram / MEMCPY["batterie"][0] * 1e3,
                  "T_cpu_batterie_ms_cas2": (o_ram + o_disque) / MEMCPY["batterie"][0] * 1e3}
    out["S6_repli_paginable"] = s6

    # S7. Un tronçon par expert.
    poids_matrice = m120["matrice"] * 32 // 17          # 17 octets par bloc de 32 poids
    octets_codes = 3 * poids_matrice * BITS_SANS_PERTE_C3 / 8
    biais = 3 * m120["biais"]
    medianes = 3 * 2880
    entete = 4096
    brut = octets_codes + biais + medianes + entete
    aligne = math.ceil(brut / 4096) * 4096
    out["S7_troncon_par_expert"] = {
        "poids_par_matrice": poids_matrice, "octets_expert_origine": m120["e_expert"],
        "octets_expert_code_estime": aligne, "octets_matrice_origine": m120["matrice"],
        "rapport_lecture_16M_QD1_sur_4M_QD4": DISQUE_16M_QD1[0] / Dx,
        "rapport_lecture_16M_QD1_sur_4M_QD1": DISQUE_16M_QD1[0] / DISQUE_4M_QD1[0],
        "lectures_par_defaut": {"par_matrice": 3, "par_expert": 1}}

    # S8. Le jumeau 20b : budget de RAM et témoin d'indépendance de la mémoire.
    r20 = 1.1037  # 03 : gpt-oss-20b, trois classes (taux-mxfp4-classes-gptoss20b.json)
    s8 = {"M_ou_tout_tient_en_ram_go": m20["E_tot"] / r20, "lignes": []}
    for M in (0.0, 2.0, 4.0, 6.0, 8.0, 11.0):
        v20 = moe(m20, beta=lru, M_ram=M, r_ram=r20, r_defaut=r20, D_disque=Dx, D_dec=d("decodeur_classes"))
        v120 = moe(m120, beta=lru, M_ram=M, r_ram=r_A, r_defaut=r_A, D_disque=Dx, D_dec=d("decodeur_classes"))
        # plafonds.py compte M entier dans la RAM de pointe même quand le cache tiède n'a
        # plus rien à garder (tout le modèle tient déjà en VRAM + RAM) : on borne M à ce
        # qu'il peut réellement contenir.
        c_v20 = max(0.0, 6.5 - m20["A"]) / m20["E_tot"]
        M_eff20 = min(M, max(0.0, 1 - c_v20) * m20["E_tot"] / r20)
        s8["lignes"].append({"M_go": M, "20b_h_s": v20["h_s"], "20b_plafond": v20["jetons_s_plafond"],
                             "20b_ram_pointe": v20["ram_pointe_go"],
                             "20b_M_utile_go": M_eff20,
                             "20b_ram_pointe_corrigee": v20["ram_pointe_go"] - M + M_eff20,
                             "120b_h_s": v120["h_s"],
                             "120b_plafond": v120["jetons_s_plafond"], "120b_ram_pointe": v120["ram_pointe_go"],
                             "ecart_ram_pointe_go": v120["ram_pointe_go"] - v20["ram_pointe_go"]})
    out["S8_jumeau_20b"] = s8

    # S9. Plafond de A contre h_s (h_v fixé par la carte, scénario LRU calé).
    hv = P.h(max(0.0, 6.5 - m120["A"]) / m120["E_tot"], lru)
    s9 = []
    for hs in (0.05, 0.10, 0.15, 0.20, 0.234, 0.30, 0.40, 0.50, 0.60, 0.723):
        hr = max(0.0, 1 - hv - hs)
        R = m120["R"]
        Td = hs * R / r_A / Dx
        Tp = (hr * R / r_A + hs * R / r_A) / d("pcie")
        Tc = (1 - hv) * R / d("decodeur_classes") + (m120["A"] + R) / d("gemv")
        s9.append({"h_s": hs, "plafond_A": 1 / (max(Td, Tp, Tc) + P.T0[0]),
                   "serie_A": 1 / (Td + Tp + Tc + P.T0[0])})
    out["S9_A_contre_hs"] = {"h_v": hv, "lignes": s9}

    # S10. Cache KV de gpt-oss-120b (en-tête GGUF : 36 couches, 8 têtes KV de 64, fenêtre
    # glissante de 128 une couche sur deux, motif lu dans llama.cpp b11515).
    kv = {}
    for ctx in (4096, 32768, 131072):
        for nom, o in (("f16", 2), ("f32", 4)):
            par_couche_jeton = 2 * 8 * 64 * o
            kv[f"{ctx}_{nom}"] = (18 * ctx + 18 * min(ctx, 128)) * par_couche_jeton / 1e9
    out["S10_cache_kv_go"] = kv

    # S11. Réécriture : temps de lecture du GGUF au plateau du disque.
    out["S11_reecriture"] = {"octets": m120["taille_fichier"],
                             "minutes_lecture_2_58": m120["taille_fichier"] / 2.58e9 / 60,
                             "minutes_lecture_2_82": m120["taille_fichier"] / 2.819e9 / 60,
                             "ecriture": "non mesurée (01 : seule une écriture synchrone QD 1 à 0,10 Go/s, chemin choisi)"}

    with open(os.path.join(SORTIE_CSV, "a-contre-hs.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["h_s", "plafond_A", "serie_A"])
        for x in s9:
            w.writerow([x["h_s"], round(x["plafond_A"], 3), round(x["serie_A"], 3)])

    # S12. La fenêtre de travail minimale. plafonds.py compte, pour les tampons d'arrivée,
    # deux jetons entiers de défauts (2 h_s R / r) ; un ordonnancement couche par couche n'a
    # besoin que de d couches d'avance, chacune d'au plus k tronçons (tous en défaut).
    # d se tire de la règle du double tampon (04 § 5.1) : d >= ceil(latence / temps d'une
    # couche), plus une couche en DMA et une en décodage.
    p50_16M_qd1_s = 5585e-6           # 01, disque-analyse.md : p50 d'une lecture de 16 Mio, QD 1
    p50_4M_qd1_s = 1737e-6            # idem, 4 Mio, QD 1
    troncon_go = out["S7_troncon_par_expert"]["octets_expert_code_estime"] / 1e9
    s12 = {"troncon_go": troncon_go, "k": 4, "lignes": []}
    for nb, beta in BETAS.items():
        for M in (0.0, 11.0):
            v = moe(m120, beta=beta, M_ram=M, r_ram=r_A, r_defaut=r_A, D_disque=Dx, D_dec=d("decodeur_classes"))
            t_couche = (1 / v["jetons_s_plafond"]) / m120["couches"]
            d_lat = math.ceil(p50_16M_qd1_s / t_couche)
            prof = d_lat + 2
            tampons = prof * 4 * troncon_go
            s12["lignes"].append({
                "scenario": nb, "M_go": M, "t_couche_ms": t_couche * 1e3,
                "couches_pour_la_latence": d_lat, "profondeur_couches": prof,
                "tampons_go": tampons,
                "ram_pointe_07_go": v["ram_pointe_go"],
                "ram_pointe_fenetre_go": M + tampons + 0.5,
                "ram_pointe_fenetre_avec_table_enchassement_go": M + tampons + 0.5 + 0.615329280})
    # La fenêtre ne dépend que de k et de la taille d'un expert, identiques pour 20b et 120b ;
    # ce qui diffère : le répertoire des tronçons (36 x 128 contre 24 x 32 entrées).
    entree_repertoire = 128  # octets par tronçon dans l'en-tête proposé (decisions/partisan-A.md § 5)
    s12["ecart_attendu_120b_moins_20b_mo"] = (36 * 128 - 24 * 32) * entree_repertoire / 1e6
    s12["p50_lecture_4M_qd1_ms"] = p50_4M_qd1_s * 1e3
    s12["p50_lecture_16M_qd1_ms"] = p50_16M_qd1_s * 1e3
    out["S12_fenetre_minimale"] = s12

    # S13. Le point où B1 retombe sur A : la part f des défauts servis exacts au-delà de
    # laquelle B1 (base + complément lus au défaut pour une part f) ne dépasse plus A.
    s13 = {}
    for nb, beta in BETAS.items():
        a = moe(m120, beta=beta, M_ram=11, r_ram=R_CLASSES[0], r_defaut=R_CLASSES[0], D_disque=Dx,
                D_dec=d("decodeur_classes"))["jetons_s_plafond"]

        def b1(f_):
            return moe(m120, beta=beta, M_ram=11, r_ram=R_CLASSES[0],
                       r_defaut=4.25 / (bits_base + f_ * bits_comp), D_disque=Dx,
                       D_dec=d("decodeur_classes"))["jetons_s_plafond"]
        lo, hi = 0.0, 1.0
        if b1(1.0) >= a:
            fstar = None
        else:
            for _ in range(60):
                mid = (lo + hi) / 2
                if b1(mid) > a:
                    lo = mid
                else:
                    hi = mid
            fstar = (lo + hi) / 2
        s13[nb] = {"A": a, "B1_f0": b1(0.0), "B1_f1": b1(1.0), "f_etoile": fstar,
                   "gain_B1_a_f_0_5": b1(0.5) / a - 1}
    out["S13_B1_retombe_sur_A"] = s13

    # S14. Contre la base : exploration de l'autre agent (non retenue par lui, à remplacer
    # par mesures/gpt-oss.md). llama.cpp b11515, -ngl 99 --cpu-moe (120b) ; cpu-moe et cache
    # VRAM de 4 096 Mio (20b) ; génération, jetons/s (mesures/REPRISE-gpt-oss.md, 10:20-10:45).
    base_explo = {"gpt-oss-120b_cpu_moe": 0.49, "gpt-oss-20b_cpu_moe_cache4096": 7.69}
    s14 = {"source": "mesures/REPRISE-gpt-oss.md (exploration non retenue, une passe, pas d'ABBA)",
           "base": base_explo, "rapports_120b": {}}
    for nb, beta in BETAS.items():
        for nom, M in (("A", 11.0), ("A0", 0.0)):
            v = moe(m120, beta=beta, M_ram=M, r_ram=r_A, r_defaut=r_A, D_disque=Dx, D_dec=d("decodeur_classes"))
            s14["rapports_120b"][f"{nom}/{nb}"] = {
                "plafond": v["jetons_s_plafond"], "serie": v["jetons_s_serie"],
                "plafond_sur_base": v["jetons_s_plafond"] / base_explo["gpt-oss-120b_cpu_moe"],
                "serie_sur_base": v["jetons_s_serie"] / base_explo["gpt-oss-120b_cpu_moe"]}
    v20 = moe(m20, beta=lru, M_ram=0.0, r_ram=r20, r_defaut=r20, D_disque=Dx, D_dec=d("decodeur_classes"))
    s14["20b_A0_lru"] = {"plafond": v20["jetons_s_plafond"], "serie": v20["jetons_s_serie"],
                         "plafond_sur_base": v20["jetons_s_plafond"] / base_explo["gpt-oss-20b_cpu_moe_cache4096"],
                         "serie_sur_base": v20["jetons_s_serie"] / base_explo["gpt-oss-20b_cpu_moe_cache4096"]}
    # Octets lus pendant l'exploration 120b : 295 Go en 761 s (même source).
    s14["exploration_120b_debit_disque_go_s"] = 295 / 761
    out["S14_contre_base_exploratoire"] = s14

    # S15. Le risque de B grandit quand h est mauvais : part servie par la base et erreur
    # moyenne ajoutée, rapportées au bruit propre du MXFP4 sur une gaussienne.
    bruit_format = raf["erreur_relative_mxfp4_gaussienne"]
    s15 = {"bruit_propre_mxfp4": bruit_format, "lignes": {}}
    for nb in BETAS:
        for k in ("B1", "B2"):
            c = s2[f"chiffre_2_58/{nb}"][k]
            s15["lignes"][f"{k}/{nb}"] = {"part_base": c["part_servie_par_la_base"],
                                          "erreur_ajoutee": c["erreur_relative_moyenne_ajoutee"],
                                          "rapport_au_bruit_du_format": c["erreur_relative_moyenne_ajoutee"] / bruit_format,
                                          "gain_sur_A": c["plafond"] / s2[f"chiffre_2_58/{nb}"]["A"]["plafond"]}
    out["S15_risque_de_B_contre_h"] = s15

    # S16. Ce que coûte une réécriture du fichier (pour passer de A à B plus tard) :
    # le codeur de l'étude 03 a codé ET décodé exactement les 108 tenseurs de gpt-oss-120b,
    # deux variantes (une table, trois classes), en 2 831 s, machine partagée
    # (fondations/journaux/03-entropie/taux-mxfp4-classes-gptoss120b.log, ligne TOTAL).
    out["S16_cout_reecriture"] = {"secondes_codage_et_decodage_deux_variantes": 2831,
                                  "minutes": 2831 / 60,
                                  "lecture_du_gguf_a_2_82_s": m120["taille_fichier"] / 2.819e9,
                                  "ecriture": "non mesurée sur cette machine"}

    # S17. Seuils dérivés, déclarés avant toute construction.
    bruit_disque_4M_qd4 = 0.10        # 01, disque-analyse.md : 2,581 Go/s [10 %]
    s17 = {"bruit_disque_4M_qd4": bruit_disque_4M_qd4,
           "facteur_v1_sur_plancher_serie": 1 - 2 * bruit_disque_4M_qd4,
           "v1_plancher_serie_par_scenario": {nb: s2[f"chiffre_2_58/{nb}"]["A"]["serie"] for nb in BETAS},
           "v1_seuil_par_scenario": {nb: (1 - 2 * bruit_disque_4M_qd4) * s2[f"chiffre_2_58/{nb}"]["A"]["serie"]
                                     for nb in BETAS},
           "decodeur_min_go_s_lru_chiffre": s5["chiffre_2_58/lru_cale"]["D_decodeur_min_go_s"],
           "decodeur_mesure_go_s": d("decodeur_classes")}
    out["S17_seuils_derives"] = s17

    # S18. Le budget de VRAM de la v1, poste par poste, contre l'hypothèse de 6,5 Go (06).
    # 8 188 Mio de carte ; 909 Mio occupés par l'affichage et les applications relevés par
    # l'autre agent à 10:15 (mesures/REPRISE-gpt-oss.md) ; cache KV à 4 096 jetons en f16 (S10) ;
    # tampons de décodage : profondeur 4 couches x 4 tronçons codés (S12) ; tables rANS :
    # 36 couches x 3 matrices x 4 tables (delta + 3 classes) x 16 Kio ; activations : 0,1 Go
    # (hypothèse dite, à mesurer).
    Mi = 1024 ** 2
    vram = 8188 * Mi / 1e9
    occupe = 909 * Mi / 1e9
    postes = {"A_resident": m120["A"], "cache_kv_4096_f16": kv["4096_f16"],
              "tampons_decodage": 4 * 4 * troncon_go, "tables_rans": 36 * 3 * 4 * 16384 / 1e9,
              "activations_hypothese": 0.1}
    reste = vram - occupe - sum(postes.values())
    V_eff = m120["A"] + reste
    s18 = {"vram_go": vram, "occupe_par_les_autres_go": occupe, "postes_go": postes,
           "cache_experts_go": reste, "emplacements_de_13_25_Mo": int(reste * 1e9 // m120["e_expert"]),
           "V_poids_equivalent_go": V_eff, "plafonds": {}}
    for nb, beta in BETAS.items():
        v65 = moe(m120, beta=beta, M_ram=11, r_ram=r_A, r_defaut=r_A, D_disque=Dx, D_dec=d("decodeur_classes"))
        vv = moe(m120, beta=beta, M_ram=11, r_ram=r_A, r_defaut=r_A, D_disque=Dx, D_dec=d("decodeur_classes"), V=V_eff)
        s18["plafonds"][nb] = {"V_6_5": v65["jetons_s_plafond"], "V_budget": vv["jetons_s_plafond"],
                               "h_v_6_5": v65["h_v"], "h_v_budget": vv["h_v"],
                               "gain": vv["jetons_s_plafond"] / v65["jetons_s_plafond"] - 1}
    out["S18_budget_vram_v1"] = s18

    # S19. Taille du fichier de tronçons (S7) : experts codés + section résidente + table
    # d'enchâssement, contre le GGUF d'origine.
    out["S19_taille_fichier"] = {
        m["nom"]: {"troncons": m["couches"] * m["E"], "octets_experts_codes": m["couches"] * m["E"] * int(troncon_go * 1e9),
                   "octets_total_estime": m["couches"] * m["E"] * int(troncon_go * 1e9) + int(m["A"] * 1e9) + 615329280,
                   "octets_gguf": m["taille_fichier"]}
        for m in (m120, m20)}

    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    main()
