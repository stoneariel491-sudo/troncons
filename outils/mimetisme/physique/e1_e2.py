"""E1 (noyaux de mémoire du cache) et E2 (nombres d'occupation) : seuils dans
mesures/mimetisme/physique/00-seuils-declares.md (commit 59eb5a2, avant toute lecture).

Usage : python -I -X utf8 e1_e2.py <dossier_traces_extraites> <exe_noyau_cache> <dossier_sortie>

Étapes :
  1. fabrique les noyaux (exponentielle, Omori-Utsu, Kohlrausch, deux temps), les non exponentiels par
     somme d'exponentielles (moindres carrés non négatifs), et écrit l'erreur d'approximation ;
  2. lance le simulateur Rust sur 7 traces, N = 323 ;
  3. W1 : noyau exponentiel de demi-vie 8 contre g_lfu de l'instrument existant, trace par trace ;
  4. W2 : même chose avec l'ordre des jetons mélangé ;
  5. E1 : validation croisée en laissant un genre dehors ; E2 : part des défauts sous eps.
"""
import importlib.util
import json
import math
import os
import subprocess
import sys

import numpy as np
from scipy.optimize import nnls

dossier, exe, sortie = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(sortie, exist_ok=True)
RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

GENRES = ["code", "dialogue", "prose-en", "prose-fr"]
TRACES = {
    "code": "t120b.code.lecture",
    "dialogue": "t120b.dialogue.lecture",
    "prose-en": "t120b.prose-en.lecture",
    "prose-fr": "t120b.prose-fr.lecture",
    "wiki-lecture": "w120b.wiki.lecture",
    "gen-prose-en": "t120b.prose-en.generation",
    "gen-wiki": "w120b.wiki.generation",
}
N = 323
TAUS = [1, 2, 4, 8, 16, 32, 64, 128, 256]
DELTA = np.arange(0, 601)


def prony(f):
    """f(DELTA) normalisé à f(0) = 1 -> somme a_j exp(-DELTA/tau_j), a_j >= 0."""
    cible = f(DELTA.astype(float))
    cible = cible / cible[0]
    base = np.stack([np.exp(-DELTA / t) for t in TAUS], axis=1)
    poids = 1.0 / np.sqrt(DELTA + 1.0)
    a, _ = nnls(base * poids[:, None], cible * poids)
    approx = base @ a
    err_rel = float(np.max(np.abs(approx[:101] - cible[:101]) / cible[:101]))
    err_abs = float(np.max(np.abs(approx - cible)))
    return a, err_rel, err_abs


def ligne(nom, comps):
    return nom + "\t" + ",".join(f"{a:.9g}:{t:.9g}" for a, t in comps)


noyaux, familles, erreurs = [], {}, {}
for h in [2, 4, 8, 16, 32, 64, 128]:
    nom = f"exp_h{h}"
    noyaux.append(ligne(nom, [(1.0, h / math.log(2))]))
    familles[nom] = "exponentielle"
for c in [1, 2, 4, 8]:
    for p in [0.5, 1.0, 1.5]:
        nom = f"omori_c{c}_p{p}"
        a, er, ea = prony(lambda d, c=c, p=p: (d + c) ** (-p))
        noyaux.append(ligne(nom, [(x, t) for x, t in zip(a, TAUS) if x > 0]))
        familles[nom] = "omori"
        erreurs[nom] = (er, ea)
for beta in [0.5, 0.7]:
    for tau in [4, 8, 16, 32]:
        nom = f"kohlrausch_b{beta}_t{tau}"
        a, er, ea = prony(lambda d, b=beta, t=tau: np.exp(-((d / t) ** b)))
        noyaux.append(ligne(nom, [(x, t) for x, t in zip(a, TAUS) if x > 0]))
        familles[nom] = "kohlrausch"
        erreurs[nom] = (er, ea)
for a_ in [0.5, 0.8]:
    for t1 in [2, 4, 8]:
        for t2 in [32, 128, 512]:
            nom = f"deux_temps_a{a_}_t{t1}_{t2}"
            noyaux.append(ligne(nom, [(a_, float(t1)), (1 - a_, float(t2))]))
            familles[nom] = "deux_temps"
open(os.path.join(sortie, "noyaux.txt"), "w", encoding="utf-8").write("\n".join(noyaux) + "\n")
json.dump({"familles": familles, "erreur_approx_prony_(rel_0_100,abs_0_600)": erreurs},
          open(os.path.join(sortie, "noyaux-familles.json"), "w", encoding="utf-8"), indent=1)

# --- simulateur Rust
resultats = {}
for melange in (False, True):
    for cle, base in TRACES.items():
        if melange and cle not in GENRES:
            continue
        fichier_sortie = os.path.join(sortie, f"{cle}{'-melange' if melange else ''}.jsonl")
        cmd = [exe, os.path.join(dossier, base + ".trace"), os.path.join(dossier, base + ".poids"),
               str(N), os.path.join(sortie, "noyaux.txt"), fichier_sortie]
        if melange:
            cmd.append("20261026")
        subprocess.run(cmd, check=True)
        resultats[(cle, melange)] = {
            j["noyau"]: j for j in (json.loads(x) for x in open(fichier_sortie, encoding="utf-8"))}
        print("fait", cle, melange, flush=True)

# --- W1 : exp_h8 contre g_lfu de l'instrument existant
spec = importlib.util.spec_from_file_location("loc", os.path.join(RACINE, "outils", "gptoss_localite.py"))
sys.path.insert(0, os.path.join(RACINE, "outils"))
loc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loc)
w1 = {}
for cle in GENRES + ["wiki-lecture"]:
    jetons, E = loc.cl.lire_trace(os.path.join(dossier, TRACES[cle] + ".trace"))
    g = loc.flux(jetons, E)
    ref = loc.g_lfu(g, N, len(jetons[0]))
    lru = loc.g_lru(g, N)
    bel = loc.g_belady(g, N)
    w1[cle] = {"g_lfu": ref, "noyau_exp_h8": resultats[(cle, False)]["exp_h8"]["taux"],
               "ecart": resultats[(cle, False)]["exp_h8"]["taux"] - ref, "g_lru": lru, "g_belady": bel}
    print("W1", cle, w1[cle], flush=True)
json.dump(w1, open(os.path.join(sortie, "W1-temoin.json"), "w", encoding="utf-8"), indent=1)

# --- E1
def taux(cle, nom, melange=False):
    r = resultats[(cle, melange)][nom]
    return r["hits"], r["total"]


def cv(fam, melange=False):
    """Validation croisée en laissant un genre dehors : réglage choisi sur les 3 autres (moyenne des
    taux), évalué sur le genre laissé dehors. Rend (taux poolé, par genre, réglages choisis)."""
    noms = [n for n, f in familles.items() if f == fam]
    h_tot, t_tot, par, choix = 0, 0, {}, {}
    for dehors in GENRES:
        autres = [g for g in GENRES if g != dehors]
        meilleur = max(noms, key=lambda n: np.mean([taux(g, n, melange)[0] / taux(g, n, melange)[1] for g in autres]))
        h, t = taux(dehors, meilleur, melange)
        h_tot += h
        t_tot += t
        par[dehors] = h / t
        choix[dehors] = meilleur
    return h_tot / t_tot, par, choix


e1 = {"vrai": {}, "melange": {}}
for tag, melange in (("vrai", False), ("melange", True)):
    for fam in ["exponentielle", "omori", "kohlrausch", "deux_temps"]:
        p, par, ch = cv(fam, melange)
        e1[tag][fam] = {"pool": p, "par_genre": par, "choix": ch}
# réservées : réglage choisi sur les 4 genres, évalué sur wiki-lecture et les générations
reserv = {}
for fam in ["exponentielle", "omori", "kohlrausch", "deux_temps"]:
    noms = [n for n, f in familles.items() if f == fam]
    meilleur = max(noms, key=lambda n: np.mean([taux(g, n)[0] / taux(g, n)[1] for g in GENRES]))
    reserv[fam] = {"reglage": meilleur,
                   **{c: taux(c, meilleur)[0] / taux(c, meilleur)[1] for c in ["wiki-lecture", "gen-prose-en", "gen-wiki"]}}
e1["reservees"] = reserv
exp = e1["vrai"]["exponentielle"]
bilan = {}
for fam in ["omori", "kohlrausch", "deux_temps"]:
    gain = e1["vrai"][fam]["pool"] - exp["pool"]
    genres_plus = sum(1 for g in GENRES if e1["vrai"][fam]["par_genre"][g] > exp["par_genre"][g])
    res_plus = sum(1 for c in ["wiki-lecture", "gen-prose-en", "gen-wiki"] if reserv[fam][c] > reserv["exponentielle"][c])
    gain_m = e1["melange"][fam]["pool"] - e1["melange"]["exponentielle"]["pool"]
    bilan[fam] = {"gain_pool": gain, "genres_gagnes_sur_4": genres_plus, "reservees_gagnees_sur_3": res_plus,
                  "gain_pool_melange_W2": gain_m,
                  "passe_seuil": bool(gain >= 0.015 and genres_plus >= 3 and res_plus >= 2)}
e1["bilan"] = bilan
json.dump(e1, open(os.path.join(sortie, "E1-bilan.json"), "w", encoding="utf-8"), indent=1)
print(json.dumps(bilan, indent=1))

# --- E2 : part des défauts sous eps (cache LFU demi-vie 8), et part globale des accès
e2 = {}
for cle in GENRES + ["wiki-lecture"]:
    r = resultats[(cle, False)]["exp_h8"]
    e2[cle] = {"defauts": r["defauts"], "acces": r["total"], "eps": r["eps"],
               "part_defauts_sous_eps": [x / r["defauts"] for x in r["defauts_sous"]],
               "part_acces_sous_eps": [x / r["total"] for x in r["acces_sous"]],
               "masse_ecartee_par_defaut": [m / r["defauts"] for m in r["defauts_masse"]],
               "ecart_somme_poids_max": r["ecart_somme_poids_max"]}
tot_def = sum(e2[c]["defauts"] for c in GENRES)
e2["pool_4_genres"] = {
    "part_defauts_sous_eps": [sum(resultats[(c, False)]["exp_h8"]["defauts_sous"][i] for c in GENRES) / tot_def
                              for i in range(6)],
    "part_acces_sous_eps": [sum(resultats[(c, False)]["exp_h8"]["acces_sous"][i] for c in GENRES)
                            / sum(resultats[(c, False)]["exp_h8"]["total"] for c in GENRES) for i in range(6)],
    "eps": e2["code"]["eps"]}
json.dump(e2, open(os.path.join(sortie, "E2-bilan.json"), "w", encoding="utf-8"), indent=1)
print(json.dumps(e2["pool_4_genres"], indent=1))
