"""Les chiffres du partisan de B (« la contribution d'abord ») : ce que B gagne vraiment
quand on compte le trafic des compléments, et ce que vaut une base lisible par llama.cpp.

Rien n'est mesuré ici, rien n'est lu sur le disque ni sur la carte : l'outil calcule à
partir de deux journaux commités de l'étude 07 (`plafonds.json` pour le modèle et les
débits, `raffinement-mxfp4-gptoss20b.json` pour la couche de base), et réutilise les
fonctions de `outils/07-synthese/plafonds.py`.

Trois questions :

1. Le trafic des compléments. `plafonds.py` calcule B1 (la base seule lue au défaut) et B2
   (la RAM ne garde que des bases) sans compter les octets des compléments qu'il faut lire
   pour qu'un expert redevienne exact. On les compte ici :
   - B1 complété : chaque défaut sert la base, puis son complément est lu pour que
     l'expert entre exact au cache. Octets du disque par jeton = h_s R (b_base + b_compl).
     Le plafond retombe à celui de A (moins le surcoût de la découpe) ; le gain ne vit plus
     que dans la latence (plancher en série), parce que le complément quitte le chemin
     critique ;
   - B1(λ) : une part λ des défauts (les experts de fort poids de routage) attend le
     complément avant de calculer ; le reste est servi par la base ;
   - B3(λ) : la RAM garde des bases (1,44 fois plus d'experts), la VRAM un ensemble chaud
     exact et statique (aucune admission, donc aucun complément pour elle) ; une part λ des
     usages hors VRAM exige l'exactitude et lit le complément du disque.
2. La couche de base, rendue lisible par llama.cpp sans toucher à ses noyaux : chaque
   classe de magnitude est « aimantée » sur une valeur E2M1 existante au lieu de son centre
   de gravité. Le fichier reste un MXFP4 valide, ce qui permet de juger la qualité de B
   avec le juge de l'étude 06 avant tout moteur. L'erreur se calcule exactement à partir
   des énergies par magnitude, retrouvées depuis les centres publiés par l'étude 07.
3. Un ordre de grandeur de la divergence KL de B, par la linéarité de HIGGS, en fonction de
   la part pondérée des usages servis par la base. Hypothèse dite, pas une mesure.

Témoins (seuil déclaré avant : 1e-9 relatif pour T1 et T2, 1e-6 pour T3) :
  T1  B3 avec une « base » égale au code entier (b_base = b_A, b_compl = 0) et la même
      constante de localité pour la VRAM redonne exactement le plafond de A de plafonds.py ;
  T2  B1 sans compter les compléments redonne exactement le B1 de plafonds.py (8,88 dans le
      scénario LRU calé) : la seule différence entre les deux chiffres est le terme ajouté ;
  T3  les énergies par magnitude retrouvées redonnent l'erreur relative des 42 partitions
      publiées (35 à 4 classes, 7 à 2 classes).
Cassure (--casser) : T1 lit la base au lieu du code entier, et l'énergie de la magnitude 3
est faussée de 1 % ; T1 et T3 doivent tomber.

Utilisation (depuis la racine du dépôt) :
  python -I -X utf8 outils/decisions/partisan_b.py [--casser] > decisions/journaux/partisan-b.json
  (écrit aussi decisions/journaux/csv/*.csv pour les figures)
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
J07 = os.path.join(RACINE, "fondations", "journaux", "07-synthese")
SORTIE_CSV = os.path.join(RACINE, "decisions", "journaux", "csv")


def charger_plafonds():
    chemin = os.path.join(RACINE, "outils", "07-synthese", "plafonds.py")
    spec = importlib.util.spec_from_file_location("plafonds", chemin)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["plafonds"] = mod
    spec.loader.exec_module(mod)
    return mod


P = charger_plafonds()

# Magnitudes E2M1 doublées (0 ; 0,5 ; 1 ; 1,5 ; 2 ; 3 ; 4 ; 6), comme dans raffinement_mxfp4.py.
MAG = [0, 1, 2, 3, 4, 6, 8, 12]

# Bits lus par poids (échelles et en-têtes compris).
B_A = 4.25 / P.R_CLASSES[0]  # 3,8545 : sans perte à trois classes d'échelle, gpt-oss-120b [mes. 03]
SURCOUT = 1.003       # en-têtes du rANS [mes. 03], comme dans plafonds.py
ECHELLES = 0.0344     # échelles codées [mes. 03]


# --- 1. Les énergies par magnitude, retrouvées depuis les centres publiés ----------------
def energies_depuis_centres(raf: dict) -> list[float]:
    """Le centre d'une classe de deux magnitudes voisines {m, m+1} vaut
    (W_m MAG_m + W_{m+1} MAG_{m+1}) / (W_m + W_{m+1}) : il donne le rapport W_{m+1} / W_m.
    Les sept rapports voisins se lisent dans les partitions publiées."""
    parts = raf["resultats"]["base_signe_plus_2_bits"]["toutes"] + \
        raf["resultats"]["base_signe_plus_1_bit"]["toutes"]
    rapport = {}
    for p in parts:
        cl = p["classes"]
        for k, c in enumerate(p["centres"]):
            membres = [m for m in range(8) if cl[m] == k]
            if len(membres) == 2:
                a, b = membres
                rapport[a] = (c - MAG[a]) / (MAG[b] - c)   # W_b / W_a
    if sorted(rapport) != list(range(7)):
        raise SystemExit(f"rapports voisins incomplets : {sorted(rapport)}")
    W = [1.0]
    for m in range(7):
        W.append(W[-1] * rapport[m])
    s = sum(W)
    W = [w / s for w in W]
    # Les centres publiés sont arrondis à 4 décimales (écart relatif ≈ 1e-4 sur les
    # rapports) ; les erreurs, elles, sont publiées en pleine précision. On affine donc W
    # par Gauss-Newton sur les 42 erreurs (7 inconnues, 42 équations) : le système est
    # surdéterminé, et le témoin T3 vérifie qu'il est cohérent.
    cibles = [(p["classes"], p["erreur_relative"]) for p in parts]

    def residus(x):
        Wx = [math.exp(v) for v in x]
        out = []
        for cl, e in cibles:
            cs = centres(Wx, cl)
            out.append(erreur(Wx, [cs[cl[mm]] for mm in range(8)]) / e - 1)
        return out

    x = [math.log(w) for w in W]
    for _ in range(30):
        r0 = residus(x)
        Jm = []
        for j in range(1, 8):          # x[0] fixé : l'échelle de W est libre
            xp = list(x)
            xp[j] += 1e-7
            Jm.append([(a - b) / 1e-7 for a, b in zip(residus(xp), r0)])
        # équations normales (7 x 7), résolues par élimination de Gauss
        n = 7
        M = [[sum(Jm[i][k] * Jm[j][k] for k in range(len(r0))) for j in range(n)] for i in range(n)]
        v = [-sum(Jm[i][k] * r0[k] for k in range(len(r0))) for i in range(n)]
        for i in range(n):
            piv = M[i][i]
            for j in range(i + 1, n):
                f = M[j][i] / piv
                for k in range(i, n):
                    M[j][k] -= f * M[i][k]
                v[j] -= f * v[i]
        dx = [0.0] * n
        for i in range(n - 1, -1, -1):
            dx[i] = (v[i] - sum(M[i][k] * dx[k] for k in range(i + 1, n))) / M[i][i]
        for j in range(n):
            x[j + 1] += dx[j]
        if max(abs(t) for t in dx) < 1e-13:
            break
    W = [math.exp(v) for v in x]
    s = sum(W)
    return [w / s for w in W]


def erreur(W: list[float], recon: list[float]) -> float:
    """Erreur quadratique relative quand la magnitude m est reconstruite par recon[m]."""
    e = sum(W[m] * (MAG[m] - recon[m]) ** 2 for m in range(8))
    return e / sum(W[m] * MAG[m] ** 2 for m in range(8))


def centres(W, classes):
    K = max(classes) + 1
    out = []
    for k in range(K):
        sel = [m for m in range(8) if classes[m] == k]
        tot = sum(W[m] for m in sel)
        out.append(sum(W[m] * MAG[m] for m in sel) / tot)
    return out


def base_aimantee(W, classes):
    """Chaque classe reconstruite par la valeur E2M1 (parmi les 8) la plus proche de son
    centre, ce qui minimise l'erreur de la classe parmi les valeurs représentables."""
    cs = centres(W, classes)
    choix = [min(MAG, key=lambda v: abs(v - c)) for c in cs]
    recon = [choix[classes[m]] for m in range(8)]
    return {"classes": classes, "valeurs_e2m1": [v / 2 for v in choix],
            "erreur_relative": erreur(W, recon)}


# --- 2. Le modèle de débit, compléments comptés -----------------------------------------
def etages(m, *, beta_v, beta, M_ram, b_ram, b_def, compl_par_R, compl_critique_par_R,
           D_disque, V=None):
    """Octets par jeton sur chaque étage. b_* : bits par poids lus (sur 4,25 stockés).
    compl_par_R : octets de compléments lus par jeton, en part de R (au taux 4,25) ;
    compl_critique_par_R : la part de ces compléments qui est sur le chemin critique."""
    V = P.CAPACITES["vram_poids"][0] if V is None else V
    A, R, E = m["A"], m["R"], m["E_tot"]
    c_v = max(0.0, V - A) / E
    c_r = M_ram * (4.25 / b_ram) / E
    hv = P.h(c_v, beta_v)
    hvr = max(hv, P.h(min(1.0, c_v + c_r), beta))
    hr, hs = hvr - hv, 1.0 - hvr
    f = R / 4.25                                     # octets d'un « bit par poids » sur R
    disque_def = hs * b_def * f
    disque_compl = compl_par_R(hv, hr, hs) * R
    disque_crit = disque_def + compl_critique_par_R(hv, hr, hs) * R
    Td = (disque_def + disque_compl) / D_disque
    Tp = (hr * b_ram * f + disque_def + disque_compl) / P.d("pcie")
    Tc = (1 - hv) * R / P.d("decodeur_classes") + (A + R) / P.d("gemv")
    t0 = P.T0[0]
    plafond = 1 / (max(Td, Tp, Tc) + t0)
    # Plancher en série : le disque ne travaille que pendant son chemin critique ; les
    # compléments hors chemin critique remplissent son temps libre (PCIe, carte, t0) s'ils
    # y tiennent, sinon l'excédent s'ajoute.
    Td_crit = disque_crit / D_disque
    libre = Tp + Tc + t0
    hors = (disque_compl - (disque_crit - disque_def)) / D_disque
    serie = 1 / (Td_crit + max(0.0, hors - libre) + Tp + Tc + t0)
    return {"h_v": hv, "h_r": hr, "h_s": hs,
            "T_disque_ms": Td * 1e3, "T_pcie_ms": Tp * 1e3, "T_carte_ms": Tc * 1e3,
            "disque_go_par_jeton": (disque_def + disque_compl),
            "jetons_s_plafond": plafond, "jetons_s_serie": serie}


def main():
    casser = "--casser" in sys.argv
    with open(os.path.join(J07, "raffinement-mxfp4-gptoss20b.json"), encoding="utf-8") as f:
        raf = json.load(f)
    m = P.charger_gptoss()
    meil = raf["resultats"]["base_signe_plus_2_bits"]["meilleure"]
    b_base = meil["H_base"] * SURCOUT + ECHELLES
    b_compl = meil["H_code_sachant_base"] * SURCOUT
    b_decoupe = b_base + b_compl
    Dx = P.d("disque_expert")

    # Énergies par magnitude et témoin T3.
    W = energies_depuis_centres(raf)
    if casser:
        W[3] *= 1.01
    parts = raf["resultats"]["base_signe_plus_2_bits"]["toutes"] + \
        raf["resultats"]["base_signe_plus_1_bit"]["toutes"]
    ecarts = []
    for p in parts:
        cs = centres(W, p["classes"])
        e = erreur(W, [cs[p["classes"][mm]] for mm in range(8)])
        ecarts.append(abs(e - p["erreur_relative"]) / p["erreur_relative"])
    T3 = {"partitions": len(parts), "ecart_relatif_max": max(ecarts), "tient": max(ecarts) < 1e-6}

    # Bases aimantées sur E2M1 : la meilleure partition aimantée, et la meilleure partition
    # au centre de gravité aimantée.
    aimantees = [dict(base_aimantee(W, p["classes"]), H_base=p["H_base"],
                      erreur_centre=p["erreur_relative"])
                 for p in raf["resultats"]["base_signe_plus_2_bits"]["toutes"]]
    aimantees.sort(key=lambda x: x["erreur_relative"])
    meil_aim = base_aimantee(W, meil["classes"])

    # Scénarios de localité. Pour la VRAM statique de B3 : le point LFU/statique publié au
    # même budget (59,2 % à 13,4 %, étude 04) dans le scénario LRU calé ; uniforme : 1 ;
    # Belady calé : la constante de Belady (optimiste, aucun point statique publié).
    betas = P.BETAS
    beta_statique = {"uniforme": 1.0,
                     "lru_cale": math.log(0.592) / math.log(0.134),
                     "belady_cale": betas["belady_cale"]}
    zero = lambda hv, hr, hs: 0.0
    res = {}
    for nb, beta in betas.items():
        r = {}
        # A tel que plafonds.py le calcule.
        r["A_plafonds_py"] = P.moe(m, beta=beta, M_ram=11, r_ram=P.R_CLASSES[0],
                                   r_defaut=P.R_CLASSES[0], D_disque=Dx,
                                   D_dec=P.d("decodeur_classes"))
        # A recalculé ici (T1) ; en cassure, la base au lieu du code entier.
        b_t1 = b_base if casser else B_A
        r["A_ici"] = etages(m, beta_v=beta, beta=beta, M_ram=11, b_ram=B_A, b_def=b_t1,
                            compl_par_R=zero, compl_critique_par_R=zero, D_disque=Dx)
        # A lu dans le fichier de B (base + complément, sans conditionnement de classe).
        r["A_dans_fichier_B"] = etages(m, beta_v=beta, beta=beta, M_ram=11, b_ram=b_decoupe,
                                       b_def=b_decoupe, compl_par_R=zero,
                                       compl_critique_par_R=zero, D_disque=Dx)
        # B1 tel que 07 le calcule (aucun complément) : témoin T2.
        r["B1_sans_complements"] = etages(m, beta_v=beta, beta=beta, M_ram=11, b_ram=B_A,
                                          b_def=b_base, compl_par_R=zero,
                                          compl_critique_par_R=zero, D_disque=Dx)
        r["B1_plafonds_py"] = P.moe(m, beta=beta, M_ram=11, r_ram=P.R_CLASSES[0],
                                    r_defaut=4.25 / b_base, D_disque=Dx,
                                    D_dec=P.d("decodeur_classes"))
        # B1(λ) complété : tous les défauts sont complétés ; une part λ attend le complément.
        for lam in (0.0, 0.5, 1.0):
            r[f"B1_complete_lambda_{lam}"] = dict(etages(
                m, beta_v=beta, beta=beta, M_ram=11, b_ram=B_A, b_def=b_base,
                compl_par_R=lambda hv, hr, hs: hs * b_compl / 4.25,
                compl_critique_par_R=lambda hv, hr, hs, l=lam: l * hs * b_compl / 4.25,
                D_disque=Dx))
            x = r[f"B1_complete_lambda_{lam}"]
            x["part_usages_base"] = (1 - lam) * x["h_s"]
        # B3(λ) : RAM de bases, VRAM statique exacte, λ des usages hors VRAM exigent l'exact.
        for lam in (0.0, 0.25, 0.5, 0.75, 1.0):
            x = etages(m, beta_v=beta_statique[nb], beta=beta, M_ram=11, b_ram=b_base,
                       b_def=b_base,
                       compl_par_R=lambda hv, hr, hs, l=lam: l * (1 - hv) * b_compl / 4.25,
                       compl_critique_par_R=lambda hv, hr, hs, l=lam: l * (1 - hv) * b_compl / 4.25,
                       D_disque=Dx)
            x["part_usages_base"] = (1 - lam) * (1 - x["h_v"])
            r[f"B3_lambda_{lam}"] = x
        res[nb] = r

    T1 = {nb: {"attendu": r["A_plafonds_py"]["jetons_s_plafond"],
               "obtenu": r["A_ici"]["jetons_s_plafond"]} for nb, r in res.items()}
    for v in T1.values():
        v["tient"] = abs(v["obtenu"] - v["attendu"]) / v["attendu"] < 1e-9
    T2 = {nb: {"attendu": r["B1_plafonds_py"]["jetons_s_plafond"],
               "obtenu": r["B1_sans_complements"]["jetons_s_plafond"]} for nb, r in res.items()}
    for v in T2.values():
        v["tient"] = abs(v["obtenu"] - v["attendu"]) / v["attendu"] < 1e-9

    # 3. Ordre de grandeur de la KL : KL_B ≈ K_tout × W, W = part des usages servis par la
    # base, pondérée par le carré du poids de routage (s = part de g² que portent les
    # usages servis par la base, à mesurer ; s = 1 : sans politique de routage).
    K_tout = (0.10, 0.25)   # hypothèse dite : tous les experts servis par la base (voir § 5)
    kl = []
    for nom, part in (("B1, LRU calé", res["lru_cale"]["B1_complete_lambda_0.0"]["part_usages_base"]),
                      ("B3 λ=0, LRU calé", res["lru_cale"]["B3_lambda_0.0"]["part_usages_base"])):
        for s in (1.0, 0.5, 0.25, 0.1):
            kl.append({"cas": nom, "part_usages_base": part, "s_part_g2": s,
                       "W": part * s, "KL_bas": K_tout[0] * part * s, "KL_haut": K_tout[1] * part * s})

    sortie = {
        "outil": "outils/decisions/partisan_b.py", "casser": casser,
        "sources": ["fondations/journaux/07-synthese/raffinement-mxfp4-gptoss20b.json",
                    "outils/07-synthese/plafonds.py (fonctions et débits)"],
        "bits": {"A_trois_classes": B_A, "base": b_base, "complement": b_compl,
                 "decoupe_base_plus_complement": b_decoupe,
                 "surcout_decoupe_relatif": b_decoupe / B_A - 1},
        "energies_par_magnitude": W,
        "base_centre_gravite": {"classes": meil["classes"], "erreur_relative": meil["erreur_relative"]},
        "base_aimantee_meilleure_partition": meil_aim,
        "bases_aimantees_classees": aimantees[:6],
        "beta_statique_lru": beta_statique["lru_cale"],
        "architectures": res,
        "kl_ordre_de_grandeur": {"K_tout_hypothese": K_tout, "lignes": kl},
        "temoins": {"T1_A_retrouve": T1, "T2_B1_de_07_retrouve": T2, "T3_energies": T3},
    }
    sortie["temoins_tiennent"] = (all(v["tient"] for v in T1.values())
                                  and all(v["tient"] for v in T2.values()) and T3["tient"])

    if not casser:
        os.makedirs(SORTIE_CSV, exist_ok=True)
        with open(os.path.join(SORTIE_CSV, "b-complements-gptoss120b.csv"), "w", newline="",
                  encoding="utf-8") as f:
            w = csv.writer(f)
            cols = ["h_v", "h_r", "h_s", "T_disque_ms", "T_pcie_ms", "T_carte_ms",
                    "disque_go_par_jeton", "jetons_s_plafond", "jetons_s_serie"]
            w.writerow(["scenario", "variante"] + cols + ["part_usages_base"])
            for nb, r in res.items():
                for k, v in r.items():
                    if k.endswith("plafonds_py"):
                        continue
                    w.writerow([nb, k] + [round(v[c], 4) for c in cols]
                               + [round(v.get("part_usages_base", 0.0), 4)])
        with open(os.path.join(SORTIE_CSV, "b3-lambda-gptoss120b.csv"), "w", newline="",
                  encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["lambda", "plafond_uniforme", "plafond_lru", "plafond_belady",
                        "part_base_lru", "plafond_A_lru"])
            for lam in (0.0, 0.25, 0.5, 0.75, 1.0):
                k = f"B3_lambda_{lam}"
                w.writerow([lam] + [round(res[nb][k]["jetons_s_plafond"], 3)
                                    for nb in ("uniforme", "lru_cale", "belady_cale")]
                           + [round(res["lru_cale"][k]["part_usages_base"], 4),
                              round(res["lru_cale"]["A_ici"]["jetons_s_plafond"], 3)])

    json.dump(sortie, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    main()
