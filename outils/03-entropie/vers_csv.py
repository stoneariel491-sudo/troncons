"""Tire des journaux de l'étude 03 les CSV des figures du mémoire.

Rien n'est recopié à la main : chaque CSV se régénère depuis les journaux commités.
Les journaux absents sont sautés (et dits). Sortie : fondations/journaux/03-entropie/csv/.

  entropie-par-tenseur-<modele>.csv    une ligne par tenseur quantifié
  histogramme-codes-<modele>.csv       histogramme global des codes, par type
  debits-carte.csv                     décodeurs rANS et recopies, toutes les passes
  debits-carte-series.csv              chaque mesure de chaque série (barres d'erreur)
  debits-cuda.csv, debits-cuda-series.csv   second chemin CUDA du décodeur v4
  gemv.csv                             produit matrice-vecteur : brut, fondu, deux passes
  gemv-series.csv                      chaque mesure
  rd-proxy.csv                         ECSQ contre quantification à débit fixe
  flux-octets.csv                      codeur d'octets par champ des blocs K
  mxfp4-echelles-contexte.csv          entropie des échelles E8M0 selon le contexte
  taux-mxfp4.csv                       taux réel du codage MXFP4 par champs

Usage : python vers_csv.py   (depuis n'importe où ; chemins relatifs au dépôt)
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

DEPOT = Path(__file__).resolve().parents[2]
J = DEPOT / "fondations" / "journaux" / "03-entropie"
SORTIE = J / "csv"


def charger(nom: str):
    p = J / nom
    if not p.exists():
        print(f"absent, sauté : {nom}")
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def ecrire(nom: str, entetes: list[str], lignes: list[list]):
    SORTIE.mkdir(parents=True, exist_ok=True)
    with open(SORTIE / nom, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(entetes)
        w.writerows(lignes)
    print(f"{nom} : {len(lignes)} lignes")


def entropies():
    for modele, fichier in [("4B", "entropie-4B.json"), ("9B", "entropie-9B.json"),
                            ("gptoss20b", "entropie-gptoss20b.json"),
                            ("gptoss120b", "entropie-gptoss120b.json")]:
        d = charger(fichier)
        if d is None:
            continue
        lignes, histos = [], {}
        for t in d["tenseurs"]:
            if t["type"] == "F32":
                continue
            c = t.get("compresseurs", {})
            lignes.append([
                t["nom"], t["type"], t["role"], t["poids"], t["octets"],
                round(t["bits_par_poids_stockes"], 6), round(t["H0_code"], 6),
                round(t["H_code_sachant_precedent"], 6),
                round(t.get("H_code_sachant_echelle", float("nan")), 6),
                round(t["L_huffman_code"], 6), round(t["bits_ideaux_ordre0_par_poids"], 6),
                round(t["taux_ideal_ordre0"], 6),
                round(c.get("zstd3", {}).get("taux", float("nan")), 6),
                round(c.get("lz4", {}).get("taux", float("nan")), 6)])
            h = histos.setdefault(t["type"], [0] * len(t["histogramme_code"]))
            for i, v in enumerate(t["histogramme_code"]):
                h[i] += v
        ecrire(f"entropie-par-tenseur-{modele}.csv",
               ["nom", "type", "role", "poids", "octets", "bits_stockes_par_poids", "H0_code",
                "H_code_sachant_precedent", "H_code_sachant_echelle", "L_huffman_code",
                "bits_ideaux_ordre0_par_poids", "taux_ideal_ordre0", "taux_zstd3", "taux_lz4"],
               lignes)
        hl = []
        for typ, h in histos.items():
            tot = sum(h)
            hl += [[typ, i, v, v / tot] for i, v in enumerate(h)]
        ecrire(f"histogramme-codes-{modele}.csv", ["type", "code", "compte", "frequence"], hl)


CONDITIONS = {
    "rans-4B-premier-essai.json": "contention (llama sur la carte)",
    "rans-4B-contention-v1-v2.json": "contention forte (3 llama-perplexity)",
    "rans-4B-essai-v4.json": "carte peu chargée, alimentation non relevée",
    "rans-4B-contention-llama-bench.json": "batterie, llama-bench d'un autre agent",
    "rans-4B-calme.json": "batterie, carte seule",
    "rans-4B-B1-secteur.json": "secteur, carte seule (B1 de A B B A)",
    "rans-4B-B2-secteur.json": "secteur, carte seule (B2 de A B B A)",
    "rans-gptoss20b-secteur.json": "secteur, carte seule, codes MXFP4",
}


def cuda():
    lignes, series = [], []
    for fichier in sorted(p.name for p in J.glob("cuda-*.json")):
        d = charger(fichier)
        for var, v in d["debits"].items():
            lignes.append([fichier, var, v["go_s_mediane"], v["go_s_meilleure"], v["dispersion"], v["lancements"],
                           d["verification"]["exact"], d["temoin_casse"]["exact"]])
            for i, t in enumerate(v["temps_s"]):
                series.append([fichier, var, i, t, d["octets_sortie"] / t / 1e9])
    ecrire("debits-cuda.csv", ["journal", "variante", "go_s_mediane", "go_s_meilleure", "dispersion_relative",
                               "lancements_par_mesure", "exact", "temoin_casse_exact"], lignes)
    ecrire("debits-cuda-series.csv", ["journal", "variante", "mesure", "temps_s", "go_s"], series)


def debits():
    lignes, series = [], []
    for fichier, condition in CONDITIONS.items():
        d = charger(fichier)
        if d is None or not d.get("carte") or not d["carte"].get("debits"):
            continue
        for var, v in d["carte"]["debits"].items():
            lignes.append([fichier, condition, var, v["go_s_sortie_mediane"],
                           v["go_s_sortie_meilleure"], v["dispersion"], v["lancements_par_mesure"]])
            octets = d["carte"]["octets_sortie"]
            for i, t in enumerate(v["temps_s"]):
                series.append([fichier, var, i, t, octets / t / 1e9])
    ecrire("debits-carte.csv", ["journal", "condition", "variante", "go_s_mediane",
                                "go_s_meilleure", "dispersion_relative", "lancements_par_mesure"], lignes)
    ecrire("debits-carte-series.csv", ["journal", "variante", "mesure", "temps_s", "go_s"], series)


def gemv():
    lignes, series = [], []
    for fichier in sorted(p.name for p in J.glob("gemv-*.json")):
        d = charger(fichier)
        for chemin, v in d["chemins"].items():
            lignes.append([fichier, chemin, v["temps_median_s"], v["milliards_poids_s"],
                           v["go_s_poids_mxfp4_equivalents"], v["go_s_meilleure"], v["dispersion"]])
            for i, t in enumerate(v["temps_s"]):
                series.append([fichier, chemin, i, t])
    ecrire("gemv.csv", ["journal", "chemin", "temps_median_s", "milliards_poids_s",
                        "go_s_poids_equivalents", "go_s_meilleure", "dispersion_relative"], lignes)
    ecrire("gemv-series.csv", ["journal", "chemin", "mesure", "temps_s"], series)


def rd():
    d = charger("rd-proxy-4B.json")
    if d is None:
        return
    lignes = [[t["tenseur"], t["type_source"], t["kurtosis"], t["KQ4"]["mse_rel"], t["KQ4"]["H_codes"],
               t["MM4_g32"]["mse_rel"], t["MM4_g64"]["mse_rel"], t["ECSQ_meme_erreur"]["bits_par_poids"],
               t["ECSQ_meme_erreur"]["gain_bits_par_poids"], t["ECSQ_meme_debit"]["gain_dB"],
               t["borne_gauss_par_bloc_bits"]] for t in d]
    ecrire("rd-proxy.csv", ["tenseur", "type_source", "kurtosis", "KQ4_mse_rel", "KQ4_H_codes",
                            "MM4g32_mse_rel", "MM4g64_mse_rel", "ECSQ_bits_par_poids_meme_erreur",
                            "gain_bits_par_poids", "gain_dB_meme_debit", "borne_gauss_bits"], lignes)


def flux():
    lignes = []
    for modele in ("4B", "9B"):
        d = charger(f"flux-octets-{modele}.json")
        if d is None:
            continue
        for typ, v in d.items():
            if not isinstance(v, dict) or "flux" not in v:
                continue
            for champ, f in v["flux"].items():
                lignes.append([modele, typ, champ, f["octets_par_bloc"], f["H0_bits_par_octet"]])
    ecrire("flux-octets.csv", ["modele", "type", "champ", "octets_par_bloc", "H0_bits_par_octet"], lignes)


def mxfp4():
    for modele in ("gptoss20b", "gptoss120b"):
        d = charger(f"mxfp4-contexte-{modele}.json")
        if d is not None:
            ecrire(f"mxfp4-echelles-contexte-{modele}.csv",
                   ["nom", "blocs", "H_e", "H_e_gauche", "H_e_haut", "H_e_gauche_haut",
                    "H_e_mediane_ligne", "H_mediane_par_bloc", "H_code", "H_code_sachant_e"],
                   [[t["nom"], t["blocs"], t["H_e"], t["H_e_sachant_gauche"], t["H_e_sachant_haut"],
                     t["H_e_sachant_gauche_haut"], t["H_e_sachant_mediane_ligne"],
                     t["H_mediane_ligne_par_bloc"], t["H_code"], t["H_code_sachant_e"]]
                    for t in d["tenseurs"]])
        d = charger(f"taux-mxfp4-{modele}.json")
        if d is not None:
            ecrire(f"taux-mxfp4-{modele}.csv",
                   ["nom", "poids", "octets_stockes", "octets_codes", "octets_echelles",
                    "bits_par_poids", "taux", "exact"],
                   [[t["nom"], t["poids"], t["octets_stockes"], t["octets_codes"], t["octets_echelles"],
                     t["bits_par_poids"], t["taux"], t["exact"]] for t in d["tenseurs"]])


if __name__ == "__main__":
    entropies()
    debits()
    cuda()
    gemv()
    rd()
    flux()
    mxfp4()


# ---- CSV prêts pour les figures pgfplots du mémoire (memoire/figures/03-entropie/) ----

def figures():
    sortie = []
    med = {}
    for fichier, cle in [("rans-4B-calme.json", "batterie"), ("rans-4B-B1-secteur.json", "secteur_b1"),
                         ("rans-4B-B2-secteur.json", "secteur_b2")]:
        d = charger(fichier)
        if d is None:
            continue
        for var, v in d["carte"]["debits"].items():
            med.setdefault(var, {})[cle] = v["go_s_sortie_mediane"]
    noms = {"decoder_v1": "v1", "decoder": "v2", "decoder_v3": "v3", "decoder_v4": "v4",
            "recopie": "recopie", "recopie_vec4": "recopie vec4"}
    for var, nom in noms.items():
        m = med.get(var, {})
        if "batterie" in m and "secteur_b1" in m:
            sortie.append([nom, m["batterie"], 0.5 * (m["secteur_b1"] + m.get("secteur_b2", m["secteur_b1"]))])
    ecrire("fig-debits-decodeur.csv", ["variante", "batterie", "secteur"], sortie)

    lignes = []
    db, ds = charger("gemv-gptoss20b-calme.json"), charger("gemv-gptoss20b-secteur.json")
    if db and ds:
        for chemin, nom in [("brut", "brut"), ("fusionne", "fondu"), ("decodage_v4", "decodage seul"),
                            ("deux_passes", "deux passes")]:
            lignes.append([nom, db["chemins"][chemin]["go_s_poids_mxfp4_equivalents"],
                           ds["chemins"][chemin]["go_s_poids_mxfp4_equivalents"]])
    ecrire("fig-gemv.csv", ["chemin", "batterie", "secteur"], lignes)

    d = charger("mxfp4-contexte-gptoss20b.json")
    if d:
        ecrire("fig-echelles-gptoss20b.csv", ["indice", "couche", "role", "H_e", "H_e_gauche", "H_e_mediane"],
               [[i, int(t["nom"].split(".")[1]), t["nom"].split(".")[2].replace("_exps", ""), t["H_e"],
                 t["H_e_sachant_gauche"], t["H_e_sachant_mediane_ligne"] + t["H_mediane_ligne_par_bloc"]]
                for i, t in enumerate(d["tenseurs"])])

    h9, h20 = charger("entropie-9B.json"), charger("entropie-gptoss20b.json")
    if h9 and h20:
        def histo(d, typ):
            h = [0] * 16
            for t in d["tenseurs"]:
                if t["type"] == typ:
                    for i, v in enumerate(t["histogramme_code"]):
                        h[i] += v
            tot = sum(h)
            return [v / tot for v in h]
        a, b = histo(h9, "Q4_K"), histo(h20, "MXFP4")
        ecrire("fig-histogramme-codes.csv", ["code", "q4k_9B", "mxfp4_gptoss20b"],
               [[i, a[i], b[i]] for i in range(16)])


if __name__ == "__main__":
    figures()
