"""Données des figures du lot F, tirées des journaux de `trc-codeur verifier` (les octets viennent
des fichiers .trc eux-mêmes) : bits par poids par tenseur, tailles de tronçon par couche, et le
résumé des deux modèles.

Usage : python -I -X utf8 mesures/moteur/F/vers_csv.py
Écrit sous mesures/moteur/F/csv/.
"""
import csv, json, os

D = "~/dev/active/troncons/mesures/moteur/F"
os.makedirs(f"{D}/csv", exist_ok=True)
ROLES = ["gate", "up", "down"]
resume = []
for m in ["20b", "120b"]:
    p = f"{D}/journaux/verifier-{m}.json"
    if not os.path.exists(p):
        continue
    v = json.load(open(p, encoding="utf-8"))
    with open(f"{D}/csv/taux-par-tenseur-{m}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["couche", "matrice", "poids", "octets_codes", "octets_delta", "octets_medianes", "bpp_codes", "bpp_delta", "bpp_medianes", "bpp_total_03"])
        for t in v["par_tenseur"]:
            tot = (t["octets_codes"] + t["octets_delta"] + t["octets_medianes"]) * 8 / t["poids"]
            w.writerow([t["couche"], ROLES[t["matrice"]], t["poids"], t["octets_codes"], t["octets_delta"], t["octets_medianes"], f"{t['bpp_codes']:.6f}", f"{t['bpp_delta']:.6f}", f"{t['bpp_medianes']:.6f}", f"{tot:.6f}"])
    with open(f"{D}/csv/troncons-par-couche-{m}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["couche", "min_octets", "moyen_octets", "max_octets", "origine_octets"])
        for t in v["troncons_par_couche"]:
            w.writerow([t["couche"], t["min"], f"{t['moyen']:.1f}", t["max"], v["troncon_octets"]["origine_par_expert"]])
    tx = v["taux"]
    resume.append([m, v["experts"], v["experts_exacts"], v["experts_faux"], v["C1"], v["taille_trc"], f"{tx['r_03']:.6f}", f"{tx['bpp_total_03']:.6f}", f"{tx['bpp_avec_tables']:.6f}", f"{tx['r_troncons']:.6f}", v["troncon_octets"]["min"], f"{v['troncon_octets']['moyen']:.1f}", v["troncon_octets"]["max"]])
with open(f"{D}/csv/resume-c1.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["modele", "experts", "exacts", "faux", "C1", "taille_trc_octets", "r_03", "bpp_total_03", "bpp_avec_tables", "r_troncons", "troncon_min", "troncon_moyen", "troncon_max"])
    w.writerows(resume)
print("\n".join(",".join(map(str, r)) for r in resume))

# Pointes de l'ensemble de travail (relevées par lancer.ps1 toutes les 0,5 s), une passe contre
# deux passes, 20b et 120b.
import re
POINTES = [
    ("coder", "20b", "une passe", "coder-20b"),
    ("verifier", "20b", "une passe", "verifier-20b"),
    ("coder", "20b", "deux passes", "coder-20b-2passes"),
    ("verifier", "20b", "deux passes", "verifier-20b-borne"),
    ("coder", "120b", "deux passes", "coder-120b"),
    ("verifier", "120b", "deux passes", "verifier-120b"),
]
with open(f"{D}/csv/pointes-memoire.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["outil", "modele", "version", "journal", "pointe_octets", "debut", "fin", "code"])
    for outil, m, version, nom in POINTES:
        p = f"{D}/journaux/{nom}.cadre.txt"
        if not os.path.exists(p):
            continue
        t = open(p, encoding="utf-8-sig").read()
        deb = re.search(r"debut (\S+ \S+)", t)
        fin = re.search(r"fin (\S+ \S+) alimentation \d+ code (\S*) pointe_ensemble_de_travail_octets (\d+)", t)
        if not fin:
            continue
        w.writerow([outil, m, version, nom, fin.group(3), deb.group(1) if deb else "", fin.group(1), fin.group(2)])
print(open(f"{D}/csv/pointes-memoire.csv", encoding="utf-8").read())

# Second chemin de C1 (second_chemin_c1.py) : une ligne par passe, passes de référence et cassures.
lignes = []
for n in ["20b", "20b-casse", "20b-casse-decalage", "120b", "120b-casse", "120b-casse-decalage"]:
    p = f"{D}/journaux/second-chemin-{n}.json"
    if not os.path.exists(p):
        continue
    j = json.load(open(p, encoding="utf-8"))
    cf = j["controles_faux"]
    res = j.get("residents") or {}
    lignes.append([n, j["experts_lus"], j["experts_faux"], cf["empreinte_origine"], cf["biais"], cf["medianes"],
                   cf["empreinte_partie"], cf["structure"], len(j["llama_cpp_ecarts"]), len(j["pavage_ecarts"]),
                   j.get("sha256_egale_attendue"), res.get("n", ""), len(res.get("faux", [])) if res else "",
                   ";".join(f"{f['c']}-{f['x']}" for f in j["faux"][:5]) + (";…" if j["experts_faux"] > 5 else ""),
                   j["verdict"], j["alimentation_debut"], j["alimentation_fin"]])
with open(f"{D}/csv/second-chemin-c1.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["passe", "experts_lus", "experts_faux", "faux_empreinte_origine", "faux_biais", "faux_medianes",
                "faux_empreinte_partie", "faux_structure", "ecarts_llama_cpp", "ecarts_pavage", "sha256_egale",
                "residents", "residents_faux", "experts_faux_nommes", "verdict", "alim_debut", "alim_fin"])
    w.writerows(lignes)
