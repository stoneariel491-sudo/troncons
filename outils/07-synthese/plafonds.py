"""L'équation du jeton, appliquée aux architectures candidates de troncons.

Étude 07 (synthèse). Chaque débit vient d'un journal commité des études 01 à 06 ;
chaque modèle, d'un en-tête GGUF lu ici ou par l'étude 06. Rien n'est mesuré par cet
outil : il calcule. Ses sorties sont des plafonds (recouvrement parfait des étages)
et des planchers sans recouvrement (somme des étages), jamais des prévisions.

Le temps d'un jeton (proposition 1 de l'étude 01, étendue) :
    t_max = max(T_disque, T_pcie, T_carte) + t0        (étages recouverts)
    t_sum = T_disque + T_pcie + T_carte + t0           (étages en série)
avec, pour un MoE dont une part h_v des experts lus est en VRAM, h_r en RAM et
h_s = 1 - h_v - h_r sur le disque :
    T_disque = h_s R / (r_d D_disque)
    T_pcie   = ((1 - h_v) R / r_p + debord) / D_pcie
    T_carte  = (1 - h_v) R / D_decodeur + (A + R) / D_gemv
r_d, r_p : facteurs de compression des octets qui traversent le disque et la PCIe.

Le succès du cache suit un modèle à une constante, h(c) = c^beta (c : part des
octets d'experts que le cache contient), calé sur un seul point publié ; c'est une
hypothèse dite, pas une loi : beta = 1 est le routage uniforme (pire cas).

Témoins (seuil déclaré : 1 % sur chaque valeur) :
  T1  gpt-oss-120b, placement de l'étude 01 (§ 7.3), r = 1, recouvert : 1,98 jeton/s ;
  T2  Qwen3.5-9B tout sur le disque, architecture B de l'étude 01, r = 16 : 8,85 ;
  T3  le même placement avec le débit du lien (7,877 Go/s) redonne les 5,6 jetons/s de
      l'étude 06 (§ 5.2, le chiffre que l'étude 01 a corrigé).
Cassure : --casser remplace le débit mesuré du disque par celui du lien ; T1 doit
tomber.

Utilisation :
  python -I -X utf8 outils/07-synthese/plafonds.py [--casser] > journal.json
  (écrit aussi les CSV des figures sous fondations/journaux/07-synthese/csv/)
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", ".."))
J = os.path.join(RACINE, "fondations", "journaux")

# --- Les débits, chacun avec son journal (Go/s, 1 Go = 1e9 octets) -------------
DEBITS = {
    "disque": (2.82, "mesuré ici", "01-machine/debits-mesures.json : 16 Mio aléatoire QD 1"),
    "disque_expert": (2.58, "mesuré ici", "01-machine/disque-analyse.md : 4 Mio aléatoire QD 4 (une matrice d'expert gpt-oss = 4,2 Mio)"),
    "disque_lien": (7.877, "calculé", "plafond du lien PCIe 4.0 x4 (étude 01) ; témoin T3 et cassure seulement"),
    "pcie": (12.2, "mesuré ici", "01-machine/debits-mesures.json : DMA hôte vers carte, 64 Mio, au calme"),
    "vram": (251.3, "mesuré ici", "01-machine/debits-mesures.json : lecture de VRAM par shader"),
    "gemv": (209.4, "mesuré ici", "03-entropie/gemv-gptoss20b-secteur.json : GEMV MXFP4 brut, Vulkan"),
    "decodeur": (70.0, "mesuré ici", "03-entropie/rans-gptoss20b-secteur.json : rANS v4 Vulkan, octets de codes produits"),
    "decodeur_classes": (41.6, "mesuré ici", "03-entropie.md § 8 : décodage puis réassemblage des trois flux de classe"),
    "cpu_ram": (15.6, "mesuré ici (chargé)", "01-machine/memoire.log : lecture 1 fil, premier passage"),
    "mmap_4k": (0.22, "mesuré ici", "01-machine : 4 Kio aléatoire, QD >= 16"),
    "mmap_1m": (1.307, "mesuré ici", "01-machine : 1 Mio aléatoire, QD 1"),
}
T0 = (0.0035, "calculé sur mesure", "02 § 5.1 passe 3 : Qwen3.5-4B Q4_K_M, 14,4 ms mesurés contre 10,9 ms à 251 Go/s")
CAPACITES = {"vram_poids": (6.5, "hypothèse dite", "06 § 5.1"),
             "ram_poids": (11.0, "hypothèse dite", "06 § 5.1")}

# Taux sans perte des experts MXFP4 de gpt-oss-120b (mesurés et décodés exactement).
R_UNE_TABLE = (1.0887, "mesuré ici", "03-entropie/taux-mxfp4-gptoss120b.json")
R_CLASSES = (1.1026, "mesuré ici", "03-entropie/taux-mxfp4-classes-gptoss120b.json")

# Modèle de succès : un point publié (LRU 65,9 % à 13,4 % du budget, Qwen3-30B-A3B,
# « Cacheable by design ? », arXiv 2608.18261) et l'optimum hors ligne au même point
# (Belady 79,1 %). beta = ln h / ln c.
BETAS = {
    "uniforme": 1.0,
    "lru_cale": math.log(0.659) / math.log(0.134),
    "belady_cale": math.log(0.791) / math.log(0.134),
}


def d(nom: str) -> float:
    return DEBITS[nom][0]


def h(c: float, beta: float) -> float:
    if c <= 0:
        return 0.0
    return min(1.0, c ** beta)


def charger_gptoss() -> dict:
    with open(os.path.join(J, "07-synthese", "inventaire-gptoss.json"), encoding="utf-8") as f:
        inv = json.load(f)
    m = {x["modele"]: x for x in inv["modeles"]}["gpt-oss-120b"]
    return {"nom": "gpt-oss-120b MXFP4", "A": m["A_octets_toujours_lus"] / 1e9,
            "R": m["R_octets_experts_par_jeton"] / 1e9,
            "E_tot": m["octets_tous_experts"] / 1e9, "bits_stockes": 4.25,
            "source": "07-synthese/inventaire-gptoss.json (en-tête lu sur le disque de la machine)"}


def charger_raffinement() -> dict:
    with open(os.path.join(J, "07-synthese", "raffinement-mxfp4-gptoss20b.json"), encoding="utf-8") as f:
        raf = json.load(f)
    b2 = raf["resultats"]["base_signe_plus_2_bits"]["meilleure"]
    b1 = raf["resultats"]["base_signe_plus_1_bit"]["meilleure"]
    echelles = 0.0344  # bits/poids des échelles codées (03 : gpt-oss-120b, 0,034)
    surcout = 1.003    # en-têtes du rANS (03 : 0,40 % de tuile ; arrondi)
    sortie = {}
    for nom, b in (("base_2b", b2), ("base_1b", b1)):
        bits = b["H_base"] * surcout + echelles
        sortie[nom] = {"bits_par_poids": bits, "r_base": 4.25 / bits,
                       "erreur_relative": b["erreur_relative"], "classes": b["classes"],
                       "H_complement": b["H_code_sachant_base"]}
    sortie["erreur_relative_mxfp4_gaussienne"] = raf["reference_gaussienne"]["erreur_relative_mxfp4"]
    return sortie


# --- Les architectures ---------------------------------------------------------
def moe(m: dict, *, beta: float, M_ram: float, r_ram: float, r_defaut: float,
        D_disque: float, D_dec: float, V: float = None, t0: float = None,
        D_gemv: float = None, carte: bool = True, lossy_ram: bool = False) -> dict:
    """Un MoE servi par la carte seule : VRAM = experts décodés ; RAM = cache codé au taux
    r_ram ; disque = experts codés, lus au taux r_defaut (r_defaut > r_ram : la couche de
    base seule est lue au défaut, architecture B)."""
    V = CAPACITES["vram_poids"][0] if V is None else V
    t0 = T0[0] if t0 is None else t0
    D_gemv = d("gemv") if D_gemv is None else D_gemv
    A, R, E = m["A"], m["R"], m["E_tot"]
    debord = max(0.0, A - V)                 # toujours-lus qui ne tiennent pas sur la carte
    c_v = max(0.0, V - A) / E
    c_r = max(0.0, M_ram - debord) * r_ram / E
    hv = h(c_v, beta)
    hvr = h(min(1.0, c_v + c_r), beta)
    hr, hs = hvr - hv, 1.0 - hvr
    T_disque = hs * R / r_defaut / D_disque
    T_pcie = (hr * R / r_ram + hs * R / r_defaut + debord) / d("pcie")
    T_carte = ((1 - hv) * R / D_dec if D_dec else 0.0) + ((A + R) / D_gemv if carte else 0.0)
    etages = {"disque": T_disque, "pcie": T_pcie, "carte": T_carte}
    t_max = max(etages.values()) + t0
    t_sum = sum(etages.values()) + t0
    return {"h_v": hv, "h_r": hr, "h_s": hs, "c_v": c_v, "c_r": c_r,
            "T_disque_ms": T_disque * 1e3, "T_pcie_ms": T_pcie * 1e3, "T_carte_ms": T_carte * 1e3,
            "etage_limitant": max(etages, key=etages.get),
            "jetons_s_plafond": 1 / t_max, "jetons_s_serie": 1 / t_sum,
            "disque_go_par_jeton": hs * R / r_defaut,
            "part_avec_perte": (1 - hv) if lossy_ram else (hs if r_defaut > r_ram + 1e-9 else 0.0),
            "ram_pointe_go": M_ram + 2 * hs * R / r_defaut + 0.5,
            "vram_pointe_go": min(V, A) + max(0.0, V - A) + 1.0}


def base_llamacpp(m: dict, *, beta: float, D_mmap: float) -> dict:
    """Estimation (non mesurée) de llama.cpp -ngl 99 --cpu-moe en mmap : experts calculés
    par le processeur depuis le cache de pages ; défauts lus par fautes de page ; pas de
    recouvrement entre couches (somme)."""
    A, R, E = m["A"], m["R"], m["E_tot"]
    hr = h(CAPACITES["ram_poids"][0] / E, beta)
    t = A / d("gemv") + hr * R / d("cpu_ram") + (1 - hr) * R / D_mmap + T0[0]
    return {"h_r": hr, "jetons_s": 1 / t, "D_mmap": D_mmap}


def dense_speculatif(octets_passe: float, E_par_passe: float, *, V_cible: float,
                     M_ram: float, D_disque: float, t_brouillon: float) -> dict:
    """Dense lu à chaque passe ; la passe de vérification rend E jetons (chaîne ou arbre)."""
    o_v = min(V_cible, octets_passe)
    o_r = min(M_ram, octets_passe - o_v)
    o_d = octets_passe - o_v - o_r
    T_disque = o_d / D_disque
    T_pcie = (o_r + o_d) / d("pcie")
    T_carte = octets_passe / d("gemv")
    T = max(T_disque, T_pcie, T_carte)
    Ts = T_disque + T_pcie + T_carte
    return {"T_passe_s": T, "T_passe_serie_s": Ts, "disque_go": o_d,
            "jetons_s_plafond": E_par_passe / (T + t_brouillon),
            "jetons_s_serie": E_par_passe / (Ts + t_brouillon)}


def E_chaine(alpha: float, k: int) -> float:
    return (1 - alpha ** (k + 1)) / (1 - alpha)


# --- Les témoins -----------------------------------------------------------------
def temoins(m: dict, casser: bool) -> dict:
    D = d("disque_lien") if casser else d("disque")
    # T1 : placement de l'étude 01 (routage uniforme, r = 1, aucun décodeur, VRAM 251,3, sans t0).
    t1 = moe(m, beta=1.0, M_ram=11.0, r_ram=1.0, r_defaut=1.0, D_disque=D, D_dec=0.0,
             t0=0.0, D_gemv=d("vram"))
    # T2 : 9B tout sur le disque, r = 16, architecture B (disque et PCIe portent B/r).
    B9 = 5.10
    t2 = 1 / max(B9 / 16 / d("disque"), B9 / 16 / d("pcie"))
    t3 = moe(m, beta=1.0, M_ram=11.0, r_ram=1.0, r_defaut=1.0, D_disque=d("disque_lien"),
             D_dec=0.0, t0=0.0, D_gemv=d("vram"))
    res = {
        "T1_gptoss120b_etude01": {"attendu": 1.98, "obtenu": t1["jetons_s_plafond"]},
        "T2_9b_r16_etude01": {"attendu": 8.85, "obtenu": t2},
        # 06 § 5.2 publie 5,6 (plafond optimiste) ; 01 § 7.3 écrit « 5,5 » pour 1/0,18 = 5,56.
        "T3_lien_etude06": {"attendu": 5.6, "obtenu": t3["jetons_s_plafond"]},
    }
    for v in res.values():
        v["tient"] = abs(v["obtenu"] - v["attendu"]) / v["attendu"] <= 0.01 + 0.005 / v["attendu"]
    return res


def main():
    casser = "--casser" in sys.argv
    m = charger_gptoss()
    raf = charger_raffinement()
    tem = temoins(m, casser)
    Dx = d("disque_expert")
    sortie = {"etude": "07-synthese", "casser": casser, "modele": m,
              "debits": DEBITS, "t0": T0, "capacites": CAPACITES,
              "betas": BETAS, "raffinement": raf, "temoins": tem,
              "temoins_tiennent": all(v["tient"] for v in tem.values())}

    # 1. Les architectures sur gpt-oss-120b, par scénario de localité.
    archis = {}
    for nb, beta in BETAS.items():
        a = {}
        a["base_llamacpp_4k"] = base_llamacpp(m, beta=beta, D_mmap=d("mmap_4k"))
        a["base_llamacpp_1m"] = base_llamacpp(m, beta=beta, D_mmap=d("mmap_1m"))
        a["A_brut_r1"] = moe(m, beta=beta, M_ram=11, r_ram=1.0, r_defaut=1.0, D_disque=Dx, D_dec=0.0)
        a["A_sans_perte"] = moe(m, beta=beta, M_ram=11, r_ram=R_CLASSES[0], r_defaut=R_CLASSES[0],
                                D_disque=Dx, D_dec=d("decodeur_classes"))
        a["A0_sans_ram"] = moe(m, beta=beta, M_ram=0.0, r_ram=R_CLASSES[0], r_defaut=R_CLASSES[0],
                               D_disque=Dx, D_dec=d("decodeur_classes"))
        rb2, rb1 = raf["base_2b"]["r_base"], raf["base_1b"]["r_base"]
        a["B1_base2b_aux_defauts"] = moe(m, beta=beta, M_ram=11, r_ram=R_CLASSES[0], r_defaut=rb2,
                                         D_disque=Dx, D_dec=d("decodeur_classes"))
        a["B2_base2b_hors_vram"] = moe(m, beta=beta, M_ram=11, r_ram=rb2, r_defaut=rb2,
                                       D_disque=Dx, D_dec=d("decodeur_classes"), lossy_ram=True)
        a["B2_base1b_hors_vram"] = moe(m, beta=beta, M_ram=11, r_ram=rb1, r_defaut=rb1,
                                       D_disque=Dx, D_dec=d("decodeur_classes"), lossy_ram=True)
        a["A_sans_perte_disque_non_chiffre_6"] = moe(m, beta=beta, M_ram=11, r_ram=R_CLASSES[0],
                                                     r_defaut=R_CLASSES[0], D_disque=6.0,
                                                     D_dec=d("decodeur_classes"))
        a["B1_base2b_disque_non_chiffre_6"] = moe(m, beta=beta, M_ram=11, r_ram=R_CLASSES[0],
                                                  r_defaut=rb2, D_disque=6.0,
                                                  D_dec=d("decodeur_classes"))
        archis[nb] = a
    sortie["gptoss120b"] = archis
    os.makedirs(os.path.join(J, "07-synthese", "csv"), exist_ok=True)
    with open(os.path.join(J, "07-synthese", "csv", "architectures-gptoss120b.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "architecture", "h_v", "h_r", "h_s", "T_disque_ms", "T_pcie_ms",
                    "T_carte_ms", "jetons_s_plafond", "jetons_s_serie", "part_avec_perte", "ram_pointe_go"])
        for nb, a in archis.items():
            for k, v in a.items():
                if "jetons_s_plafond" in v:
                    w.writerow([nb, k] + [round(v[c], 4) for c in ("h_v", "h_r", "h_s", "T_disque_ms",
                               "T_pcie_ms", "T_carte_ms", "jetons_s_plafond", "jetons_s_serie",
                               "part_avec_perte", "ram_pointe_go")])
                else:
                    w.writerow([nb, k, "", round(v["h_r"], 4), "", "", "", "", round(v["jetons_s"], 4),
                                round(v["jetons_s"], 4), 0, ""])

    # Effet du taux sans perte sur le cache (comparé à l'étude 03, § 6 point 8).
    u1 = moe(m, beta=1.0, M_ram=11, r_ram=1.0, r_defaut=1.0, D_disque=d("disque"), D_dec=0.0, t0=0.0)
    u2 = moe(m, beta=1.0, M_ram=11, r_ram=R_CLASSES[0], r_defaut=R_CLASSES[0], D_disque=d("disque"),
             D_dec=0.0, t0=0.0)
    sortie["gain_taux_sur_cache_uniforme"] = u1["disque_go_par_jeton"] / u2["disque_go_par_jeton"] - 1

    # 2. Balayage du succès total (h_v fixé par la carte) : figure « jetons/s contre h_s ».
    os.makedirs(os.path.join(J, "07-synthese", "csv"), exist_ok=True)
    chemin = os.path.join(J, "07-synthese", "csv", "plafond-gptoss120b-contre-hs.csv")
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["h_s", "A_brut", "A_sans_perte", "B1_base2b", "B2_base1b"])
        A_, R_ = m["A"], m["R"]
        for i in range(2, 101, 2):
            hs = i / 100
            ligne = [hs]
            for r_def in (1.0, R_CLASSES[0], raf["base_2b"]["r_base"], raf["base_1b"]["r_base"]):
                # carte : h_v = 0,59 (scénario LRU calé) ; reste en RAM.
                hv = h(max(0.0, 6.5 - A_) / m["E_tot"], BETAS["lru_cale"])
                hr = max(0.0, 1 - hv - hs)
                Td = hs * R_ / r_def / Dx
                Tp = (hr * R_ / R_CLASSES[0] + hs * R_ / r_def) / d("pcie")
                Tc = (1 - hv) * R_ / d("decodeur_classes") + (A_ + R_) / d("gemv")
                ligne.append(round(1 / (max(Td, Tp, Tc) + T0[0]), 3))
            w.writerow(ligne)

    # 3. Balayage du budget de RAM (architecture A sans perte, scénario LRU calé).
    chemin = os.path.join(J, "07-synthese", "csv", "plafond-gptoss120b-contre-ram.csv")
    balayage = []
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ram_cache_go", "jetons_s_lru", "jetons_s_uniforme", "jetons_s_belady", "ram_pointe_lru"])
        for g in [0, 0.5, 1, 2, 3, 4, 6, 8, 11]:
            r_ = [moe(m, beta=BETAS[b], M_ram=g, r_ram=R_CLASSES[0], r_defaut=R_CLASSES[0],
                      D_disque=Dx, D_dec=d("decodeur_classes")) for b in ("lru_cale", "uniforme", "belady_cale")]
            w.writerow([g] + [round(x["jetons_s_plafond"], 3) for x in r_] + [round(r_[0]["ram_pointe_go"], 2)])
            balayage.append({"ram_cache_go": g, "lru": r_[0]["jetons_s_plafond"],
                             "uniforme": r_[1]["jetons_s_plafond"], "belady": r_[2]["jetons_s_plafond"],
                             "ram_pointe": r_[0]["ram_pointe_go"]})
    sortie["balayage_ram"] = balayage

    # 4. Architecture C : dense Llama-3.3-70B, vérification d'une chaîne ou d'un arbre.
    with open(os.path.join(J, "07-synthese", "tailles-hf-denses.json"), encoding="utf-8") as f:
        tailles = json.load(f)["bartowski/Llama-3.3-70B-Instruct-GGUF"]["fichiers"]
    enchassement = 1.05e9 * 4.5 / 8 / 1e9  # une ligne lue par jeton : la table sort du compte (hyp.)
    brouillon_go = 0.807694464                # Llama-3.2-1B Q4_K_M (API HF)
    V_cible = CAPACITES["vram_poids"][0] - brouillon_go - 0.5   # brouillon + arbre et cache KV
    t_brouillon = 12 * (brouillon_go / d("gemv") + T0[0])        # 12 pas de brouillon par passe
    cas_E = {"sans_speculation": 1.0, "chaine_a08_k4": E_chaine(0.8, 4),
             "chaine_a08_borne": 5.0, "arbre_specexec_rtx4060": 9.7, "arbre_10": 10.0}
    dense = {}
    for fichier in ("Llama-3.3-70B-Instruct-Q4_K_M.gguf", "Llama-3.3-70B-Instruct-IQ3_XXS.gguf",
                    "Llama-3.3-70B-Instruct-IQ2_M.gguf", "Llama-3.3-70B-Instruct-IQ2_XXS.gguf"):
        octets = tailles[fichier][0] / 1e9 - enchassement
        dense[fichier] = {"octets_par_passe_go": octets, "cas": {
            k: dense_speculatif(octets, E, V_cible=V_cible, M_ram=CAPACITES["ram_poids"][0],
                                D_disque=d("disque"), t_brouillon=t_brouillon)
            for k, E in cas_E.items()}}
    sortie["dense_C"] = {"V_cible_go": V_cible, "t_brouillon_s": t_brouillon, "cas_E": cas_E,
                         "fichiers": dense}

    # 5. Spéculation sur un MoE avec réutilisation : condition alpha > 1 - rho (k = 1).
    sortie["moe_speculation_condition_k1"] = {
        "formule": "E(alpha,1) = 1 + alpha > U(2)/t = 2 - rho  <=>  alpha > 1 - rho",
        "rho_publies": {"Qwen3-30B-A3B (0,444)": 1 - 0.444, "Qwen3.6-35B-A3B (~0,25)": 0.75,
                        "independant gpt-oss-120b (4/128)": 1 - 4 / 128}}

    json.dump(sortie, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    main()
