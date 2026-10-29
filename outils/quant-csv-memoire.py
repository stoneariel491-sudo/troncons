"""Données de l'étude 02 (quantification) en CSV, pour les figures pgfplots du mémoire.

Lit les journaux commités sous fondations/journaux/02-quantification/ et écrit, dans son
sous-dossier csv/ :
  - mse-gaussien.csv    : MSE sur source N(0,1) par quantificateur et débit (mesuré ici),
                          plus la borne de Shannon D(R) = 2^(-2R) (calculée) ;
  - gemv-brut.csv       : chaque passe des bancs GEMV (CUDA, Vulkan, DirectX 12) ;
  - gemv-resume.csv     : médiane, minimum, maximum par (API, passe, format) ;
  - echelle.csv         : l'échelle llama.cpp sur Qwen3.5 4B et 9B (bits réels, Go lus
                          par jeton, perplexité, KLD, accord du premier jeton) ;
  - litt-iso-octets.csv : points publiés utilisés au § 6 (QTIP sur Llama 2, Tetra sur
                          Qwen3, CurveTQ), recopiés à la main depuis les articles, avec
                          leur source (étiquette « litt. », non reproduits).

Témoin : les MSE analytiques de Lloyd-Max relues dans le journal doivent égaler les valeurs
classiques de Max (1960), arrondies à 4 chiffres, à 1e-4 près ; CASSER=1 décale la
valeur de référence à 2 bits de 1e-3 pour vérifier que le témoin tombe, et chaque fichier de banc doit rendre autant de
lignes brutes qu'il a de mesures. Un témoin qui ne tient pas arrête le script (code 1).

Usage : python -I outils/quant-csv-memoire.py
"""
import csv
import glob
import json
import os
import re
import statistics
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOUR = os.path.join(RACINE, "fondations", "journaux", "02-quantification")
SORTIE = os.path.join(JOUR, "csv")

# Valeurs de Max (1960), quantificateur de Lloyd-Max pour N(0,1), 1 à 3 bits.
MAX_1960 = {1: 0.3634, 2: 0.1175, 3: 0.03455}
if os.environ.get("CASSER") == "1":
    MAX_1960[2] += 1e-3


def ecrire(nom, entetes, lignes):
    chemin = os.path.join(SORTIE, nom)
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(entetes)
        w.writerows(lignes)
    print(f"{nom} : {len(lignes)} lignes")


def mse_gaussien():
    lignes = []
    vus = set()
    # Passe 1 (journal en lignes JSON) puis passe 2 (JSON) : la passe 2 prime à débit égal.
    p1 = os.path.join(JOUR, "mse-gaussien-passe1-partielle.log")
    enregistrements = []
    for l in open(p1, encoding="utf-8"):
        l = l.strip()
        if l.startswith("{"):
            enregistrements.append(("passe1", json.loads(l)))
    for r in json.load(open(os.path.join(JOUR, "mse-treillis-2b.json"), encoding="utf-8"))["resultats"]:
        enregistrements.append(("passe2", r))
    temoin_ok = True
    for passe, r in reversed(enregistrements):
        cle = (r["methode"], r["R"])
        if r["methode"] == "borne-shannon" or cle in vus:
            continue
        vus.add(cle)
        if r["methode"] == "lloyd":
            ecart = abs(r["mse_analytique"] - MAX_1960[r["R"]])
            if ecart > 1e-4:
                temoin_ok = False
                print(f"TÉMOIN : Lloyd-Max R={r['R']} {r['mse_analytique']} contre Max {MAX_1960[r['R']]}")
        lignes.append([r["methode"], r["bits_par_poids"], r["mse_monte_carlo"], r["erreur_type"],
                       r.get("mse_analytique", ""), passe, "mesure"])
    iq = json.load(open(os.path.join(JOUR, "mse-iq2xxs.json"), encoding="utf-8"))
    lignes.append(["iq2xxs-llamacpp", iq["iq2xxs"]["bits_par_poids"], iq["iq2xxs"]["mse"],
                   iq["iq2xxs"]["erreur_type"], "", "mse-iq2xxs", "mesure"])
    s = iq["iq2xxs_sans_parite_2_1875_bits"]
    lignes.append(["iq2xxs-sans-parite", 2.1875, s["mse"], s["erreur_type"], "", "mse-iq2xxs", "mesure"])
    for k in range(0, 33):
        R = k / 8
        lignes.append(["shannon", R, 2 ** (-2 * R), 0, 2 ** (-2 * R), "", "calcule"])
    lignes.sort(key=lambda x: (x[0], float(x[1])))
    ecrire("mse-gaussien.csv", ["methode", "bits_par_poids", "mse", "erreur_type", "mse_analytique",
                                "journal", "etiquette"], lignes)
    return temoin_ok


def gemv():
    brut, resume = [], []
    temoin_ok = True
    for chemin in sorted(glob.glob(os.path.join(JOUR, "*gemv-*.json"))):
        nom = os.path.basename(chemin)
        d = json.load(open(chemin, encoding="utf-8"))
        if not isinstance(d, dict) or "mesures" not in d:
            continue
        api = d.get("api", "cuda")
        mesures = d["mesures"]
        n0 = len(brut)
        for m in mesures:
            brut.append([nom, api, m["serie"], m["format"], m["role"], m["ms"], m["go_s"]])
        if len(brut) - n0 != len(mesures):
            temoin_ok = False
        par_format = {}
        for m in mesures:
            par_format.setdefault(m["format"], []).append(m["ms"])
        octets = {}
        for m in mesures:
            octets[m["format"]] = m["go_s"] * m["ms"] * 1e-3  # Go = Go/s × s
        for f, ms in par_format.items():
            med = statistics.median(ms)
            resume.append([nom, api, f, len(ms), round(med, 4), round(min(ms), 4), round(max(ms), 4),
                           round(octets[f] / (med * 1e-3), 1)])
    ecrire("gemv-brut.csv", ["journal", "api", "serie", "format", "role", "ms", "go_s"], brut)
    ecrire("gemv-resume.csv", ["journal", "api", "format", "n", "ms_mediane", "ms_min", "ms_max",
                               "go_s_mediane"], resume)
    return temoin_ok


def lire_kld(chemin):
    t = open(chemin, encoding="utf-8", errors="replace").read()

    def num(motif):
        m = re.search(motif, t)
        return (float(m.group(1)), float(m.group(2))) if m else ("", "")
    return {
        "ppl": num(r"Mean PPL\(Q\)\s*:\s*([\d.]+)\s*±\s*([\d.]+)"),
        "rapport": num(r"Mean PPL\(Q\)/PPL\(base\)\s*:\s*([\d.]+)\s*±\s*([\d.]+)"),
        "kld": num(r"Mean\s+KLD:\s*([\d.]+)\s*±\s*([\d.]+)"),
        "top1": num(r"Same top p:\s*([\d.]+)\s*±\s*([\d.]+)"),
    }


def ppl_base(chemin):
    t = open(chemin, encoding="utf-8", errors="replace").read()
    m = re.search(r"Final estimate: PPL = ([\d.]+) \+/- ([\d.]+)", t)
    return (float(m.group(1)), float(m.group(2))) if m else ("", "")


def echelle():
    lignes = []
    bases = {d["fichier"]: d for d in json.load(open(os.path.join(JOUR, "bits-q4km-locaux.json"),
                                                      encoding="utf-8"))}
    for taille, fichier_base in (("4B", "Qwen3.5-4B-Q4_K_M.gguf"), ("9B", "Qwen3.5-9B-Q4_K_M.gguf")):
        dossier = os.path.join(JOUR, f"echelle-{taille}")
        nom = f"qwen35-{taille}"
        b = bases[fichier_base]
        p, pe = ppl_base(os.path.join(dossier, f"{nom}-base-ppl.log"))
        lignes.append([taille, "Q4_K_M-base", b["bpp_tenseurs"], b["octets_lus_par_jeton"] / 1e9,
                       p, pe, 1, 0, 0, 0, 100, 0])
        for fb in sorted(glob.glob(os.path.join(dossier, f"{nom}-*-bits.json"))):
            typ = os.path.basename(fb)[len(nom) + 1:-len("-bits.json")]
            d = json.load(open(fb, encoding="utf-8"))
            d = d[0] if isinstance(d, list) else d
            fk = os.path.join(dossier, f"{nom}-{typ}-kld.log")
            if not os.path.exists(fk):
                continue
            k = lire_kld(fk)
            lignes.append([taille, typ, d["bpp_tenseurs"], d["octets_lus_par_jeton"] / 1e9,
                           k["ppl"][0], k["ppl"][1], k["rapport"][0], k["rapport"][1],
                           k["kld"][0], k["kld"][1], k["top1"][0], k["top1"][1]])
    ecrire("echelle.csv", ["modele", "type", "bits_par_poids", "go_lus_par_jeton", "ppl", "ppl_et",
                           "ppl_sur_base", "ppl_sur_base_et", "kld", "kld_et", "meme_top1_pct",
                           "meme_top1_et"], lignes)


# Points publiés, recopiés à la main ; chaque ligne porte sa source. Go lus par jeton
# calculés N × b / 8 (sans la tête pour QTIP ; « modèle entier » pour Tetra, où les Go sont
# ceux que l'article donne pour les tampons sur la carte).
LITT = [
    # famille, modele, methode, bits, go, metrique, valeur, source
    ("Llama-2", "7B", "FP16", 16, 13.5, "ppl-wt2-ctx4096", 5.12, "2406.11235 tab. 5"),
    ("Llama-2", "7B", "QTIP-4b", 4, 3.4, "ppl-wt2-ctx4096", 5.17, "2406.11235 tab. 5"),
    ("Llama-2", "7B", "QTIP-2b", 2, 1.7, "ppl-wt2-ctx4096", 5.86, "2406.11235 tab. 5"),
    ("Llama-2", "13B", "FP16", 16, 26.0, "ppl-wt2-ctx4096", 4.57, "2406.11235 tab. 5"),
    ("Llama-2", "13B", "QTIP-4b", 4, 6.5, "ppl-wt2-ctx4096", 4.61, "2406.11235 tab. 5"),
    ("Llama-2", "13B", "QTIP-3b", 3, 4.9, "ppl-wt2-ctx4096", 4.69, "2406.11235 tab. 5"),
    ("Llama-2", "13B", "QTIP-2b", 2, 3.3, "ppl-wt2-ctx4096", 5.11, "2406.11235 tab. 5"),
    ("Llama-2", "70B", "QTIP-3b", 3, 26.0, "ppl-wt2-ctx4096", 3.26, "2406.11235 tab. 5"),
    ("Llama-2", "70B", "QTIP-2b", 2, 17.3, "ppl-wt2-ctx4096", 3.70, "2406.11235 tab. 5"),
    ("Qwen3", "4B", "FP16", 16, 8.04, "mmlu", 70.14, "2609.35465 tab. 3"),
    ("Qwen3", "4B", "AWQ-w4g128", 5.30, 2.67, "mmlu", 68.14, "2609.35465 tab. 3"),
    ("Qwen3", "4B", "Tetra", 2.73, 1.38, "mmlu", 63.37, "2609.35465 tab. 3"),
    ("Qwen3", "4B", "IQ2_XXS-llamacpp", 2.48, 1.25, "mmlu", 39.78, "2609.35465 tab. 3"),
    ("Qwen3", "8B", "FP16", 16, 16.38, "mmlu", 75.05, "2609.35465 tab. 3"),
    ("Qwen3", "8B", "AWQ-w4g128", 5.96, 6.10, "mmlu", 73.79, "2609.35465 tab. 3"),
    ("Qwen3", "8B", "Tetra", 2.70, 2.76, "mmlu", 69.58, "2609.35465 tab. 3"),
    ("Qwen3", "14B", "FP16", 16, 29.54, "mmlu", 78.88, "2609.35465 tab. 3"),
    ("Qwen3", "14B", "AWQ-w4g128", 5.40, 9.98, "mmlu", 78.12, "2609.35465 tab. 3"),
    ("Qwen3", "14B", "Tetra", 2.73, 5.04, "mmlu", 75.66, "2609.35465 tab. 3"),
    ("Qwen3", "4B", "FP16", 16, "", "ppl-wt2-ctx4096", 9.72, "2610.09212 tab. 1"),
    ("Qwen3", "4B", "QTIP-2b", 2.00, "", "ppl-wt2-ctx4096", 15.36, "2610.09212 tab. 1"),
    ("Qwen3", "4B", "CurveTQ-2b", 2.29, "", "ppl-wt2-ctx4096", 11.50, "2610.09212 tab. 1"),
    ("Qwen3", "32B", "FP16", 16, "", "ppl-wt2-ctx4096", 6.17, "2610.09212 tab. 1"),
    ("Qwen3", "32B", "QTIP-2b", 2.00, "", "ppl-wt2-ctx4096", 7.21, "2610.09212 tab. 1"),
    ("Qwen3", "32B", "CurveTQ-2b", 2.29, "", "ppl-wt2-ctx4096", 6.90, "2610.09212 tab. 1"),
    ("Qwen3.6-MoE", "35B-A3B", "FP16", 16, "", "ppl-wt2-ctx4096", 6.12, "2610.09212 tab. 2"),
    ("Qwen3.6-MoE", "35B-A3B", "CurveTQ-2b", 2.29, "", "ppl-wt2-ctx4096", 6.76, "2610.09212 tab. 2"),
]


def litterature():
    ecrire("litt-iso-octets.csv", ["famille", "modele", "methode", "bits_par_poids", "go_lus",
                                   "metrique", "valeur", "source"], [list(x) for x in LITT])


def lire(nom):
    with open(os.path.join(SORTIE, nom), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def etiquette_tex(t):
    return t.replace("_", r"\_")


def series_figures():
    """Une série par fichier fig-*.csv : pgfplots les lit sans filtre ni coordonnée symbolique."""
    mse = lire("mse-gaussien.csv")
    for methode, nom in (("lloyd", "lloyd"), ("vq8-gaussien-aleatoire", "vq8"),
                         ("iq2xxs-llamacpp", "iq2xxs"), ("treillis-rptc", "treillis")):
        ecrire(f"fig-q1-{nom}.csv", ["bits", "mse", "et"],
               [[r["bits_par_poids"], r["mse"], r["erreur_type"]] for r in mse if r["methode"] == methode])
    resume = lire("gemv-resume.csv")
    noms = {"lecture-seule": "lecture seule", "scalaire-4b": "scalaire 4 b", "scalaire-2b": "scalaire 2 b",
            "treillis-mul1-main": "treillis (somme)", "treillis-mul1-dot4": "treillis (dot4)",
            "treillis-mul1-dot4-v2": "treillis (dot4 v2)"}
    for journal, nom in (("vulkan-gemv-4.json", "vulkan"), ("dx12-gemv-3.json", "dx12")):
        lignes = [r for r in resume if r["journal"] == journal]
        lignes.sort(key=lambda r: list(noms).index(r["format"]))
        ecrire(f"fig-q2-{nom}.csv", ["i", "format", "go_s", "ms"],
               [[i, noms[r["format"]], r["go_s_mediane"], r["ms_mediane"]] for i, r in enumerate(lignes)])
    ech = lire("echelle.csv")
    for taille in ("4B", "9B"):
        lignes = sorted((r for r in ech if r["modele"] == taille), key=lambda r: float(r["go_lus_par_jeton"]))
        ecrire(f"fig-q3-{taille}.csv", ["go", "ppl", "et", "etiquette"],
               [[r["go_lus_par_jeton"], r["ppl"], r["ppl_et"], etiquette_tex(r["type"].replace("-base", ""))]
                for r in lignes])
    litt = lire("litt-iso-octets.csv")
    for modele in ("7B", "13B", "70B"):
        ecrire(f"fig-q4-llama2-{modele}.csv", ["go", "ppl", "etiquette"],
               [[r["go_lus"], r["valeur"], etiquette_tex(r["methode"])] for r in litt
                if r["famille"] == "Llama-2" and r["modele"] == modele])
    for methode, nom in (("AWQ-w4g128", "awq"), ("Tetra", "tetra"), ("FP16", "fp16")):
        ecrire(f"fig-q4-qwen3-mmlu-{nom}.csv", ["go", "mmlu", "etiquette"],
               [[r["go_lus"], r["valeur"], r["modele"]] for r in litt
                if r["famille"] == "Qwen3" and r["metrique"] == "mmlu" and r["methode"] == methode])


def vitesse():
    """Passe 3 de llama-bench (retenue) : jetons/s et Go/s effectifs par fichier."""
    lignes = []
    for taille in ("4B", "9B"):
        chemin = os.path.join(JOUR, f"vitesse-{taille}-3.json")
        if not os.path.exists(chemin):
            continue
        d = json.load(open(chemin, encoding="utf-8"))
        rb = d["reference_bilan"]
        lignes.append([taille, "Q4\\_K\\_M", rb["octets_lus_par_jeton"] / 1e9, rb["jetons_s_moyen"],
                       rb["go_s_effectifs"], rb["part_du_plafond_256"]])
        for m in d["mesures"]:
            typ = m["fichier"].split("-")[-1].replace(".gguf", "")
            lignes.append([taille, etiquette_tex(typ), m["octets_lus_par_jeton"] / 1e9, m["jetons_s"],
                           m["go_s_effectifs"], m["part_du_plafond_256"]])
    for taille in ("4B", "9B"):
        ecrire(f"fig-q6-vitesse-{taille}.csv", ["go", "jetons_s", "go_s", "part", "etiquette"],
               [[l[2], l[3], l[4], l[5], l[1]] for l in sorted(lignes, key=lambda l: l[2]) if l[0] == taille])


def main():
    os.makedirs(SORTIE, exist_ok=True)
    vitesse()
    t1 = mse_gaussien()
    t2 = gemv()
    echelle()
    litterature()
    series_figures()
    if not (t1 and t2):
        print("TÉMOIN TOMBÉ")
        sys.exit(1)
    print("témoin : tient")


if __name__ == "__main__":
    main()
