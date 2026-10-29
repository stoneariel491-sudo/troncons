"""Second chemin de l'arbitre : les plafonds de A, A0, B1 et B3 refaits par des formules écrites ici.

Pourquoi : la décision (decisions/ARCHITECTURE.md) dépend de quatre chiffres publiés par
d'autres (07 § 4, partisan-A.md § 2, partisan-B.md § 2), dont un est contesté : le B1 de
l'étude 07 (8,88 jetons/s, LRU calé) ne compte pas les octets des compléments ; le partisan
de B le corrige à 6,16. Le SOCLE demande de refaire par un chemin indépendant tout chiffre
publié dont on dépend. Cet outil n'importe ni `plafonds.py` ni les outils des partisans : il
réécrit l'équation du jeton depuis 07 § 1.2 et l'annexe A.1 de partisan-B.md, avec les
constantes recopiées des journaux nommés ci-dessous.

Modèle (07 § 1.2) : f = R / 4,25 octets par « bit par poids » des experts d'un jeton ;
  disque = f · (h_s · b_def + C) / D_disque
  pcie   = (f · (h_r · b_ram + h_s · b_def + C) + débord) / D_pcie
  carte  = (1 − h_v) · R / D_dec + (A + R) / D_gemv
  plafond = 1 / (max + t0) ; série = 1 / (somme + t0)
  h(c) = c^β, h_v = h(c_v), h_v + h_r = h(c_v + c_r).
C = octets des compléments lus par jeton, en bits par poids rapportés aux experts d'un jeton.

Témoins (seuil déclaré avant : 1 % relatif sur chaque valeur publiée) :
  W1 A, LRU calé : 6,24 (07)        W2 A0, LRU calé : 3,59 (07)       W3 A, uniforme : 2,05 (07)
  W4 B1 sans compléments, LRU : 8,88 (07)
  W5 B1 complété λ = 0, LRU : plafond 6,16, série 4,83 (partisan B)
  W6 B3 λ = 0, LRU : 10,89 (partisan B)
Cassure (--casser) : b_compl = 0 dans B1 complété ; W5 doit tomber (8,88 au lieu de 6,16),
les autres tenir.

Sortie : JSON sur stdout. Usage, depuis la racine du dépôt :
  python -I -X utf8 outils/arbitre/verif_plafonds.py [--casser] > decisions/journaux/arbitre/verif-plafonds.json
"""
from __future__ import annotations

import json
import math
import sys

# Constantes, chacune avec sa source (Go = 1e9 octets).
A = 1.685668608        # Go toujours lus, 120b (07-synthese/inventaire-gptoss.json)
R = 1.90854144         # Go d'experts lus par jeton, 120b (idem)
E = 61.07332608        # Go de tous les experts (idem)
D_DISQUE = 2.58        # Go/s, 4 Mio QD 4 (01-machine/disque-analyse.md)
D_PCIE = 12.2          # Go/s, DMA au calme (01-machine/debits-mesures.json)
D_GEMV = 209.4         # Go/s, GEMV MXFP4 brute (03-entropie/gemv-gptoss20b-secteur.json)
D_DEC = 41.6           # Go/s, décodage + réassemblage des trois classes (03-entropie § 8)
T0 = 0.0035            # s, coût fixe d'un jeton (07 § 1.1)
V = 6.5                # Go de VRAM pour les poids (hypothèse de 06, gardée pour comparer)
M = 11.0               # Go de RAM pour le cache tiède (hypothèse de 06)
B_A = 4.25 / 1.1026    # bits lus par poids, A (03 : taux à trois classes, 120b)
B_BASE = 2.641541346050036 * 1.003 + 0.0344   # 07 annexe A.4 (H(base) mesuré, en-têtes, échelles)
B_COMPL = 1.218227332822482 * 1.003           # partisan B annexe A.6
BETA = {"uniforme": 1.0,
        "lru_cale": math.log(0.659) / math.log(0.134),
        "belady_cale": math.log(0.791) / math.log(0.134)}
BETA_STATIQUE = math.log(0.592) / math.log(0.134)  # partisan B § 2.3 (LFU/statique 59,2 %)


def h(c: float, beta: float) -> float:
    return 0.0 if c <= 0 else min(1.0, c ** beta)


def chaine(hv, hr, hs, b_ram, b_def, C):
    # R Go à 4,25 bits par poids ; lus à b bits par poids, ils font R · b / 4,25 Go.
    debord = max(0.0, A - V)
    disque = R * (hs * b_def + C) / 4.25 / D_DISQUE
    pcie = (R * (hr * b_ram + hs * b_def + C) / 4.25 + debord) / D_PCIE
    carte = (1 - hv) * R / D_DEC + (A + R) / D_GEMV
    return disque, pcie, carte


def resultat(etages, crit_disque=None, hors=0.0):
    d, p, c = etages
    plafond = 1 / (max(etages) + T0)
    if crit_disque is None:
        serie = 1 / (d + p + c + T0)
    else:  # complément hors du chemin critique, sur le temps libre du disque (partisan B, A.2)
        serie = 1 / (crit_disque + max(0.0, hors - (p + c + T0)) + p + c + T0)
    return {"T_disque_ms": d * 1e3, "T_pcie_ms": p * 1e3, "T_carte_ms": c * 1e3,
            "plafond": plafond, "serie": serie}


def niveaux(beta, M_ram, r_ram, beta_v=None):
    c_v = max(0.0, V - A) / E
    c_r = M_ram * r_ram / E
    hv = h(c_v, beta if beta_v is None else beta_v)
    hvr = h(min(1.0, c_v + c_r), beta)
    hvr = max(hvr, hv)
    return hv, hvr - hv, 1 - hvr


def architectures(casser: bool) -> dict:
    out = {}
    b_compl = 0.0 if casser else B_COMPL
    for sc, beta in BETA.items():
        r_a = 4.25 / B_A
        hv, hr, hs = niveaux(beta, M, r_a)
        out[f"A_{sc}"] = resultat(chaine(hv, hr, hs, B_A, B_A, 0.0)) | {"h": [hv, hr, hs]}
        hv0, hr0, hs0 = niveaux(beta, 0.0, r_a)
        out[f"A0_{sc}"] = resultat(chaine(hv0, hr0, hs0, B_A, B_A, 0.0)) | {"h": [hv0, hr0, hs0]}
        # B1 de 07 : base seule au défaut, aucun complément compté
        out[f"B1_07_{sc}"] = resultat(chaine(hv, hr, hs, B_A, B_BASE, 0.0))
        # B1 complété, λ = 0 : chaque défaut lit la base (chemin critique) puis son complément
        et = chaine(hv, hr, hs, B_A, B_BASE, hs * b_compl)
        crit = R * hs * B_BASE / 4.25 / D_DISQUE
        hors = R * hs * b_compl / 4.25 / D_DISQUE
        out[f"B1_complete_{sc}"] = resultat(et, crit_disque=crit, hors=hors) | {"part_base": hs}
        # B3, λ = 0 : RAM de bases, VRAM statique exacte, tout usage hors VRAM servi par la base
        r_b = 4.25 / B_BASE
        bv = BETA_STATIQUE if sc == "lru_cale" else beta
        hv3, hr3, hs3 = niveaux(beta, M, r_b, beta_v=bv)
        out[f"B3_{sc}"] = resultat(chaine(hv3, hr3, hs3, B_BASE, B_BASE, 0.0)) | {"part_base": 1 - hv3}
    return out


# Bits de la base et du complément mesurés par F1 (decoupe-gptoss20b.json, variante B_riche),
# rapportés au taux de A du 120b par le rapport mesuré sur le 20b (même structure, 03).
F1_A_CTX, F1_BASE, F1_COMPL = 3.843137, 2.644107, 1.210686


def avec_f1() -> dict:
    """B1 complété et B3 (λ = 0) avec les bits de F1 au lieu des entropies d'ordre 0 de 07."""
    out = {}
    bb, bc = B_A * F1_BASE / F1_A_CTX, B_A * F1_COMPL / F1_A_CTX
    for sc, beta in BETA.items():
        hv, hr, hs = niveaux(beta, M, 4.25 / B_A)
        et = chaine(hv, hr, hs, B_A, bb, hs * bc)
        out[f"B1_complete_F1_{sc}"] = resultat(et, crit_disque=R * hs * bb / 4.25 / D_DISQUE,
                                               hors=R * hs * bc / 4.25 / D_DISQUE) | {"part_base": hs}
        bv = BETA_STATIQUE if sc == "lru_cale" else beta
        hv3, hr3, hs3 = niveaux(beta, M, 4.25 / bb, beta_v=bv)
        out[f"B3_F1_{sc}"] = resultat(chaine(hv3, hr3, hs3, bb, bb, 0.0)) | {"part_base": 1 - hv3}
    out["bits"] = {"b_base_120b": bb, "b_compl_120b": bc, "b_A_120b": B_A}
    return out


def seuils_j1() -> dict:
    """Seuils de vitesse du jalon J1 (ARCHITECTURE.md § 7), dans les trois scénarios de
    localité : 0,8 × le plancher en série (v1 à la demande, sans préchargement) ; 0,8 =
    1 − 2 × 10 %, le bruit de la lecture de 4 Mio en QD 4 (01-machine/disque-analyse.md).
    Ce ne sont que des repères : le seuil qui juge se recalcule avec le h compté par le
    moteur et les débits de la même séance."""
    out = {}
    r_a = 4.25 / B_A
    for sc, beta in BETA.items():
        for nom, m_ram in (("A0_M0", 0.0), ("A_M4", 4.0), ("A_M11", 11.0)):
            hv, hr, hs = niveaux(beta, m_ram, r_a)
            res = resultat(chaine(hv, hr, hs, B_A, B_A, 0.0))
            out[f"{nom}_{sc}"] = {"h_v": hv, "h_r": hr, "h_s": hs, "plafond": res["plafond"],
                                  "serie": res["serie"], "seuil_C5": 0.8 * res["serie"]}
    return out


def main():
    casser = "--casser" in sys.argv
    a = architectures(casser)
    attendu = {
        "W1_A_lru": (a["A_lru_cale"]["plafond"], 6.24),
        "W2_A0_lru": (a["A0_lru_cale"]["plafond"], 3.59),
        "W3_A_uniforme": (a["A_uniforme"]["plafond"], 2.05),
        "W4_B1_07_lru": (a["B1_07_lru_cale"]["plafond"], 8.88),
        "W5_B1_complete_lru_plafond": (a["B1_complete_lru_cale"]["plafond"], 6.16),
        "W5_B1_complete_lru_serie": (a["B1_complete_lru_cale"]["serie"], 4.83),
        "W6_B3_lru": (a["B3_lru_cale"]["plafond"], 10.89),
    }
    temoins = {k: {"obtenu": v, "attendu": e, "tient": abs(v - e) / e <= 0.01} for k, (v, e) in attendu.items()}
    json.dump({"outil": "outils/arbitre/verif_plafonds.py", "casser": casser,
               "constantes": {"A": A, "R": R, "E": E, "D_disque": D_DISQUE, "D_pcie": D_PCIE,
                              "D_gemv": D_GEMV, "D_dec": D_DEC, "t0": T0, "V": V, "M": M,
                              "b_A": B_A, "b_base": B_BASE, "b_compl": B_COMPL},
               "architectures": a, "seuils_J1": seuils_j1(), "avec_F1": avec_f1(), "temoins": temoins,
               "temoins_tiennent": all(t["tient"] for t in temoins.values())},
              sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    main()
