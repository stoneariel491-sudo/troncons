"""Le juge physique du chargement : octets lus par jeton, étage par étage, divisés par le débit
de chaque étage. Décodage, un jeton à la fois (lot 1), modèle MoE ou dense.

Grandeurs (toutes « calculées » à partir de l'inventaire des modèles, étude 06) :
  A  = octets toujours lus par jeton : attention, experts partagés, routeurs, normes, tête ;
  e  = octets d'un expert routé = params_expert / (E * L_moe) * bpp / 8 ;
  R  = octets routés par jeton = k * L_moe * e.
Placement des experts routés : une part h_v des octets routés est servie depuis la VRAM, une
part h_r depuis la RAM, le reste h_s = 1 - h_v - h_r est lu sur le disque à chaque jeton.

Stratégies :
  hybride : A et les succès VRAM calculés sur la carte ; experts en RAM calculés par le
            processeur (KTransformers, llama.cpp -ncmoe, Fiddler) ; un défaut disque est lu
            vers la RAM puis calculé par le processeur. Le lien PCIe ne porte que des
            activations (négligées : 2 x hidden x 2 o par couche).
  carte   : tout se calcule sur la carte ; un expert absent de la VRAM traverse le PCIe
            (depuis la RAM, ou depuis le disque via la RAM) (Mixtral-offloading, MoE-Infinity,
            HOBBIT, ProMoE, --moe-cache-mib de llama.cpp).
  unifie  : mémoire unifiée (GB10, Apple) : VRAM = RAM, défauts lus sur le disque.
  cpu     : tout sur le processeur (moe-stream, llama.cpp sans carte).
Temps par étage t_i = octets_i / débit_i. Deux bornes : « recouvrement parfait »
1 / max(t_i), et « en série » 1 / somme(t_i). Une mesure publiée doit être sous la borne
de recouvrement parfait ; sinon le juge est faux (ou la mesure, ou ses hypothèses).

h minimal impliqué : pour une mesure publiée de d jetons/s, la part de défaut disque ne peut
pas dépasser h_s,max = (débit_disque / d) / R (l'étage disque seul doit tenir dans 1/d) :
la mesure prouve un taux de succès d'au moins 1 - h_s,max. C'est ce qu'une mesure publiée
dit de la localité, sans trace de routage.

Témoins (--temoins) : cinq mesures publiées, chacune avec sa machine. Toutes doivent
tomber sous leur borne. --casser divise tous les débits par 10 : au moins une doit alors
dépasser sa borne, sinon le témoin ne prouve rien.

Usage :
  python -I outils/chargement_juge.py --temoins [--casser] [--sortie J.json]
  python -I outils/chargement_juge.py --machine stone --sortie J.json   (tableau des modèles visés)
"""

import argparse
import json
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
INVENTAIRE = os.path.join(ICI, "..", "fondations", "journaux", "06-modeles", "inventaire-3.json")


def forme(nom, inventaire):
    v = inventaire[nom]
    c = v["config"]
    E, k, L = c["experts_routes_cfg"], c["experts_par_jeton"], v["couches_moe"]
    return {
        "nom": nom,
        "params_total": v["params_texte_total"],
        "params_toujours": v["params_toujours_actifs"],
        "params_expert_total": v["params"]["expert"],
        "E": E, "k": k, "L_moe": L,
    }


def octets(f, bpp, bpp_toujours=None):
    bpp_toujours = bpp if bpp_toujours is None else bpp_toujours
    e = f["params_expert_total"] / (f["E"] * f["L_moe"]) * bpp / 8
    A = f["params_toujours"] * bpp_toujours / 8
    R = f["k"] * f["L_moe"] * e
    total = f["params_expert_total"] * bpp / 8 + A
    return {"A": A, "e": e, "R": R, "total": total}


def juger(o, m, strategie, h_v, h_r):
    """o : octets ; m : machine (débits en o/s) ; renvoie les temps par étage et les bornes."""
    h_s = max(0.0, 1.0 - h_v - h_r)
    A, R = o["A"], o["R"]
    t = {}
    if strategie == "hybride":
        t["carte"] = (A + h_v * R) / m["vram"]
        t["processeur"] = (h_r + h_s) * R / m["ram"]
        t["disque"] = h_s * R / m["disque"]
    elif strategie == "carte":
        t["carte"] = (A + R) / m["vram"]
        t["pcie"] = (h_r + h_s) * R / m["pcie"]
        t["disque"] = h_s * R / m["disque"]
    elif strategie == "unifie":
        t["memoire"] = (A + (h_v + h_r + h_s) * R) / m["vram"]
        t["disque"] = h_s * R / m["disque"]
    elif strategie == "cpu":
        t["processeur"] = (A + R) / m["ram"]
        t["disque"] = h_s * R / m["disque"]
    else:
        raise ValueError(strategie)
    pire = max(t.values())
    return {"temps_s": t, "h_s": h_s, "octets_disque": h_s * R,
            "borne_recouvrement": 1.0 / pire, "borne_serie": 1.0 / sum(t.values()),
            "etage_limitant": max(t, key=t.get)}


def h_min_implique(o, m, mesure_tok_s, etage="disque"):
    """etage : l'étage que traverse un défaut (« disque », ou « pcie » quand les experts absents
    de la carte sont en RAM, comme dans Mixtral-offloading)."""
    h_s_max = (m[etage] / mesure_tok_s) / o["R"]
    return max(0.0, 1.0 - h_s_max)


GO = 1e9
GIO = 1 << 30

# Machines des mesures publiées (débits « littérature (éditeur, non reproduit) » sauf mention).
MACHINES = {
    # arXiv 2608.18261 : RTX 3070 ~448 Go/s, DDR4 32 Go ~50 Go/s, SN530 ~2,4 Go/s à froid.
    "rtx3070_sn530": {"vram": 448 * GO, "ram": 50 * GO, "disque": 2.4 * GO, "pcie": 15.75 * GO,
                      "vram_cap": 8 * GO, "ram_cap": 32 * GO},
    # PR llama.cpp #25294 : GB10, 128 Go unifiés ; LPDDR5X 8533 MT/s sur 256 bits = 273 Go/s
    # (calculé) ; disque PCIe 4.0 : plafond x4 7,877 Go/s (calculé, borne haute).
    "gb10": {"vram": 273 * GO, "ram": 273 * GO, "disque": 7.877 * GO, "pcie": 273 * GO,
             "vram_cap": 128 * GO, "ram_cap": 128 * GO},
    # moe-stream : Ryzen 5 7430U, DDR4-3200 deux canaux = 51,2 Go/s (calculé, borne haute),
    # lectures aléatoires à la taille d'un expert 1,496 Go/s (publié par l'auteur).
    "ryzen7430u": {"vram": 51.2 * GO, "ram": 51.2 * GO, "disque": 1.496 * GO, "pcie": 51.2 * GO,
                   "vram_cap": 0, "ram_cap": 15.4 * GO},
    # arXiv 2312.17238 : RTX 3060 12 Go, 360 Go/s ; PCIe 4.0 x16 = 31,5 Go/s (calculé, borne haute).
    "rtx3060": {"vram": 360 * GO, "ram": 50 * GO, "disque": 3 * GO, "pcie": 31.5 * GO,
                "vram_cap": 12 * GO, "ram_cap": 64 * GO},
    # La machine de Stone. vram : 227 Go/s lecture+écriture mesuré ici (pcie-2, copie 256 Mio,
    # carte partagée) ; on prend 220 Go/s en lecture. pcie : 6,4 Go/s mesuré ici (lien en Gen3,
    # pcie-1) ; « pcie_gen4 » 12 Go/s hypothèse (80 % de 15,754). ram : 41,6 Go/s plafond
    # calculé (un seul module DDR5-5200, journal 01-machine) x 0,85 = 35 Go/s, hypothèse à
    # remplacer par la mesure de l'étude 01. disque : 7,877 Go/s plafond calculé x 0,85 =
    # 6,7 Go/s, hypothèse à remplacer par la mesure de l'étude 01 à la taille d'un expert.
    # Capacités utiles aux poids : VRAM 8 Gio moins ~1,5 Gio (contexte, tampons, affichage
    # sur l'iGPU donc rien) = 6,5 Go ; RAM 15,6 Gio moins ~5,5 Gio (système, autres) = 10 Go.
    "stone": {"vram": 220 * GO, "ram": 35 * GO, "disque": 6.7 * GO, "pcie": 6.4 * GO,
              "pcie_gen4": 12 * GO, "vram_cap": 6.5 * GO, "ram_cap": 10 * GO},
}

TEMOINS = [
    {"source": "arXiv 2608.18261 (Suram, 2026-08-18), Qwen3-235B Q4_K_M, -ngl 99 -ncmoe 94, à froid",
     "modele": "Qwen/Qwen3-235B-A22B-Instruct-2507", "taille": 134e9, "machine": "rtx3070_sn530",
     "strategie": "hybride", "mesure": 0.128, "cache": "capacite"},
    {"source": "arXiv 2608.18261, même montage, à chaud", "modele": "Qwen/Qwen3-235B-A22B-Instruct-2507",
     "taille": 134e9, "machine": "rtx3070_sn530", "strategie": "hybride", "mesure": 0.441, "cache": "un"},
    {"source": "PR llama.cpp #25294 (2026-07-04), GLM-5.2 UD-Q2_K_XL ~254 Go, 90 emplacements, 79 % de succès "
               "(forme de GLM-5.1 prise pour GLM-5.2, absente de l'inventaire)",
     "modele": "zai-org/GLM-5.1", "taille": 254e9, "machine": "gb10", "strategie": "unifie",
     "mesure": 2.20, "cache": 0.79},
    {"source": "moe-stream (Wok3b, 2026), Qwen3.6-35B-A3B UD-Q4_K_M 20,6 Gio, budget 6 Go, processeur seul",
     "modele": "Qwen/Qwen3.6-35B-A3B", "taille": 20.6 * GIO, "machine": "ryzen7430u", "strategie": "cpu",
     "mesure": 5.05, "cache": "un"},
    {"source": "arXiv 2312.17238 (Eliseev et Mazur, 2023-12-28), Mixtral-8x7B experts 2 bits, RTX 3060",
     "modele": "mistralai/Mixtral-8x7B-Instruct-v0.1", "bpp": 2.25, "bpp_toujours": 4.25,
     "machine": "rtx3060", "strategie": "carte", "mesure": 2.278, "cache": "zero", "etage_defaut": "pcie"},
]


def taux(cache, o, m, strategie):
    """Renvoie (h_v, h_r) selon la règle du témoin."""
    if cache == "un":  # borne absolue : tout servi depuis la mémoire
        return (1.0, 0.0) if strategie in ("unifie", "carte") else (0.0, 1.0)
    if cache == "zero":
        return 0.0, 1.0 if strategie == "carte" else 0.0
    if cache == "capacite":  # sans localité : la part servie = la part qui tient
        reste_v = max(0.0, m["vram_cap"] - o["A"])
        h_v = min(1.0, reste_v / (o["total"] - o["A"]))
        h_r = min(1.0 - h_v, m["ram_cap"] / (o["total"] - o["A"]))
        return h_v, h_r
    if isinstance(cache, float):
        return (cache, 0.0)
    raise ValueError(cache)


def lancer_temoins(inventaire, casser):
    lignes, echecs = [], []
    for w in TEMOINS:
        f = forme(w["modele"], inventaire)
        bpp = w.get("bpp") or w["taille"] * 8 / f["params_total"]
        o = octets(f, bpp, w.get("bpp_toujours"))
        m = dict(MACHINES[w["machine"]])
        if casser:
            for cle in ("vram", "ram", "disque", "pcie"):
                m[cle] /= 10
        h_v, h_r = taux(w["cache"], o, m, w["strategie"])
        j = juger(o, m, w["strategie"], h_v, h_r)
        ok = w["mesure"] <= j["borne_recouvrement"] * (1 + 1e-9)
        hmin = h_min_implique(o, m, w["mesure"], w.get("etage_defaut", "disque"))
        lignes.append({"source": w["source"], "bpp": bpp, "octets": o, "h_v": h_v, "h_r": h_r, **j,
                       "mesure": w["mesure"], "sous_la_borne": ok, "h_min_implique": hmin})
        if not ok:
            echecs.append(w["source"])
        print(f"{'ok ' if ok else 'NON'} mesure {w['mesure']:.3f} <= borne {j['borne_recouvrement']:.3f} "
              f"(série {j['borne_serie']:.3f}, limite {j['etage_limitant']}) ; R={o['R'] / GO:.2f} Go, "
              f"A={o['A'] / GO:.2f} Go, bpp={bpp:.2f}, succès impliqué >= {hmin:.2f} | {w['source'][:70]}")
    return lignes, echecs


VISES = [
    ("Qwen/Qwen3-30B-A3B", 4.85), ("Qwen/Qwen3.6-35B-A3B", 4.85), ("openai/gpt-oss-120b", 4.25),
    ("zai-org/GLM-4.5-Air", 4.85), ("Qwen/Qwen3-Next-80B-A3B-Instruct", 4.85),
    ("Qwen/Qwen3.5-122B-A10B", 4.85), ("Qwen/Qwen3.8-Flash-Next", 4.85),
    ("deepseek-ai/DeepSeek-V4-Flash", 4.5), ("Qwen/Qwen3-235B-A22B-Instruct-2507", 4.56),
    ("Qwen/Qwen3.5-397B-A17B", 4.85), ("Qwen/Qwen3-235B-A22B-Instruct-2507", 2.7),
    ("zai-org/GLM-5.1", 2.7),
]


def tableau_stone(inventaire, disque=None):
    m = dict(MACHINES["stone"])
    if disque:
        m["disque"] = disque
    sortie = []
    print("modèle | bpp | total Go | A Go | R Go | e Mo | part tenable | borne sans localité (hyb.) | "
          "h pour 5 tok/s | h pour 10 tok/s | plafond h=1 (hyb.) | plafond h_v=1 (carte)")
    for nom, bpp in VISES:
        f = forme(nom, inventaire)
        o = octets(f, bpp)
        h_v, h_r = taux("capacite", o, m, "hybride")
        sans = juger(o, m, "hybride", h_v, h_r)
        plaf = juger(o, m, "hybride", 0.0, 1.0)
        plaf_v = juger(o, m, "carte", 1.0, 0.0)

        def h_pour(d):
            # disque seul : h_s R / disque <= 1/d ; processeur : R / ram <= 1/d (indépendant de h)
            if o["R"] / m["ram"] + o["A"] / m["vram"] > 1 / d and False:
                return None
            return max(0.0, 1 - (m["disque"] / d) / o["R"])
        ligne = {"modele": nom, "bpp": bpp, "octets": o, "part_tenable": h_v + h_r,
                 "sans_localite": sans, "h_pour_5": h_pour(5), "h_pour_10": h_pour(10),
                 "plafond_hybride_h1": plaf["borne_recouvrement"], "plafond_carte_hv1": plaf_v["borne_recouvrement"]}
        sortie.append(ligne)
        print(f"{nom.split('/')[1][:26]:26s} | {bpp:.2f} | {o['total'] / GO:6.1f} | {o['A'] / GO:5.2f} | "
              f"{o['R'] / GO:5.2f} | {o['e'] / 1e6:6.2f} | {h_v + h_r:4.2f} | "
              f"{sans['borne_recouvrement']:5.2f} ({sans['etage_limitant']}) | {h_pour(5):.2f} | {h_pour(10):.2f} | "
              f"{plaf['borne_recouvrement']:5.1f} | {plaf_v['borne_recouvrement']:5.1f}")
    return sortie


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--temoins", action="store_true")
    ap.add_argument("--casser", action="store_true")
    ap.add_argument("--machine")
    ap.add_argument("--disque-go-s", type=float, default=None,
                    help="remplace le débit disque de la machine (par exemple une mesure de l'étude 01)")
    ap.add_argument("--inventaire", default=INVENTAIRE)
    ap.add_argument("--sortie")
    a = ap.parse_args()
    # Les trois passes de l'inventaire (étude 06) se complètent : la plus récente prime.
    inventaire = {}
    for nom in ("inventaire.json", "inventaire-2.json", "inventaire-3.json"):
        chemin = os.path.join(os.path.dirname(a.inventaire), nom)
        if os.path.exists(chemin):
            with open(chemin, encoding="utf-8") as f:
                for cle, v in json.load(f).items():
                    if isinstance(v, dict) and "config" in v and v.get("params"):
                        inventaire[cle] = v
    journal = {"outil": "chargement_juge.py", "machines": MACHINES}
    code = 0
    if a.temoins:
        lignes, echecs = lancer_temoins(inventaire, a.casser)
        journal.update({"mode": "temoins", "casser": a.casser, "temoins": lignes, "echecs": echecs,
                        "verdict": "INSTRUMENT VALIDE" if not echecs else "TEMOIN TOMBE"})
        print(journal["verdict"])
        code = 0 if not echecs else 2
    if a.machine == "stone":
        journal["stone"] = tableau_stone(inventaire, a.disque_go_s * GO if a.disque_go_s else None)
        journal["disque_go_s"] = a.disque_go_s
    if a.sortie:
        os.makedirs(os.path.dirname(a.sortie) or ".", exist_ok=True)
        with open(a.sortie, "w", encoding="utf-8") as f:
            json.dump(journal, f, ensure_ascii=False, indent=1, default=float)
    return code


if __name__ == "__main__":
    sys.exit(main())
