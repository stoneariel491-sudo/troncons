"""Données des figures et tableaux du lot K pour le mémoire (CSV), tirées des journaux commités.

Usage : python -I -X utf8 mesures/moteur/K/vers_csv.py
Écrit sous mesures/moteur/K/csv/ :
  k1-justesse-par-couche.csv   témoin 120b (banc, codeur indépendant), une ligne par couche et version
  k1-trc-par-couche.csv        témoin sur le vrai fichier du lot F (gpt-oss-20b.trc), par couche
  k1-debit-passes.csv          débit du décodeur par passe (A expert par expert, B brut, C lot), G-K1
  k1-decomposition.csv         temps médians de DELTA, CODES_CTX et du trou entre experts, G-K2
  k2-debit-passes.csv          débit de la GEMV par passe (A lot de 12, B une matrice), G-K3
  k2-ecarts-reels.csv          écart relatif de la GEMV sur poids réels, G-K4
Un journal absent est sauté (dit sur la sortie d'erreur), jamais inventé.
"""
import csv
import glob
import json
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
SORTIE = os.path.join(ICI, "csv")


def lire(chemin):
    try:
        with open(chemin, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        print(f"saute {os.path.basename(chemin)} : {e}", file=sys.stderr)
        return None


def ecrire(nom, entetes, lignes):
    os.makedirs(SORTIE, exist_ok=True)
    with open(os.path.join(SORTIE, nom), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(entetes)
        w.writerows(lignes)
    print(f"{nom} : {len(lignes)} lignes", file=sys.stderr)


def justesse():
    lignes = []
    for version, nom in [("v1", "k1-justesse-gptoss120b.json"), ("v2", "k1-justesse-v2-gptoss120b.json")]:
        j = lire(os.path.join(ICI, nom))
        if not j:
            continue
        for c in j["couches"]:
            lignes.append([version, c["couche"], c["experts"], c["experts_faux"], c["experts_faux_brut"],
                           c["voies_hors_L"], c["erreurs_format"], c["taux_origine_sur_partie"],
                           c["bits_par_poids_entropie_tables"]])
    # v3 (noyaux finaux) : deux passes (couches 0-4 interrompue, JSON non fermé ; 5-35), lues dans
    # leurs journaux texte, une ligne par couche.
    import re
    motif = re.compile(r"couche (\d+) : (\d+) experts, faux (\d+) \(brut (\d+)\), hors L (\d+), format (\d+), taux ([0-9.]+)")
    for nom in ["k1-justesse-v3-gptoss120b-c0-4-partiel.log", "k1-justesse-v3-gptoss120b-c5-35.log"]:
        try:
            texte = open(os.path.join(ICI, nom), encoding="utf-8-sig", errors="replace").read()
        except OSError as e:
            print(f"saute {nom} : {e}", file=sys.stderr)
            continue
        for m in motif.finditer(texte):
            c, n, faux, brut, hl, fmt, taux = m.groups()
            lignes.append(["v3", int(c), int(n), int(faux), int(brut), int(hl), int(fmt), float(taux), ""])
    ecrire("k1-justesse-par-couche.csv", ["version", "couche", "experts", "faux", "faux_brut", "hors_L", "format",
                                          "taux_origine_sur_partie", "bits_par_poids"], lignes)


def trc():
    j = lire(os.path.join(ICI, "k1-trc-gptoss20b.json"))
    if not j:
        return
    lignes = [[c["couche"], c["experts"], c["experts_faux_contre_trc_codec"], c["experts_faux_contre_repertoire"],
               c["voies_hors_L"], c["lot"]["experts_faux_contre_trc_codec"], c["octets_parties"],
               c["octets_emplacements"]] for c in j["couches"]]
    ecrire("k1-trc-par-couche.csv", ["couche", "experts", "faux_trc_codec", "faux_repertoire", "hors_L", "faux_lot",
                                     "octets_parties", "octets_emplacements"], lignes)


def debit_k1():
    lignes, decomp = [], []
    for chemin in sorted(glob.glob(os.path.join(ICI, "journaux", "k1-debit-*.json"))):
        j = lire(chemin)
        if not j:
            continue
        nom = os.path.basename(chemin)
        oc = j["octets_codes_par_expert"]
        for q in ("A", "B"):
            for i, t in enumerate(j["temps_s_par_expert"][q]):
                lignes.append([nom, q, i, t, oc / t / 1e9])
        for i, t in enumerate(j.get("temps_s_par_expert_C", [])):
            lignes.append([nom, "C", i, t, oc / t / 1e9])
        d = j.get("decomposition_s_medianes", {})
        decomp.append([nom, d.get("decoder_echelles"), d.get("decoder_codes"), d.get("trou_entre_experts"),
                       j["mediane_s_par_expert"]["A"]])
    ecrire("k1-debit-passes.csv", ["journal", "variante", "passe", "s_par_expert", "go_s_codes"], lignes)
    ecrire("k1-decomposition.csv", ["journal", "s_delta", "s_codes", "s_trou", "s_par_expert_A"], decomp)


def reference_03():
    """Le chemin que K1 remplace, remesuré dans la même séance : décodeur v4 de 03 (CUDA) puis
    réassemblage des trois flux de classe ; le composé 1 / (1/v4 + 1/réassemblage) est l'analogue
    CUDA du 41,6 Go/s de 03 (qui composait le v4 sous Vulkan, 70 Go/s)."""
    lignes = []
    for chemin in sorted(glob.glob(os.path.join(ICI, "journaux", "k1-ref03-v4-*.json"))):
        v = lire(chemin)
        r = lire(chemin.replace("-v4-", "-reassemblage-"))
        if not v or not r:
            continue
        gv = v["debits"]["decoder_v4_cuda"]["go_s_mediane"]
        gr = r["debits"]["dispersion"]["go_s_ecrits_mediane"]
        lignes.append([os.path.basename(chemin), gv, gr, 1.0 / (1.0 / gv + 1.0 / gr), 1.0 / (1.0 / 70.0 + 1.0 / 102.4)])
    ecrire("k1-reference-03.csv", ["journal", "v4_cuda_go_s", "reassemblage_go_s", "compose_go_s", "compose_publie_03_go_s"], lignes)


def debit_k2():
    lignes = []
    for chemin in sorted(glob.glob(os.path.join(ICI, "journaux", "k2-debit-*.json"))):
        j = lire(chemin)
        if not j:
            continue
        oe = j["octets_equiv_par_groupe"]
        for q in ("A", "B"):
            for i, t in enumerate(j["temps_s_par_groupe"][q]):
                lignes.append([os.path.basename(chemin), q, i, t, oe / t / 1e9])
    ecrire("k2-debit-passes.csv", ["journal", "variante", "passe", "s_par_groupe", "go_s_equiv"], lignes)
    j = lire(os.path.join(ICI, "k2-justesse-gptoss120b.json"))
    if j:
        ecrire("k2-ecarts-reels.csv", ["expert", "matrice", "ecart_relatif", "max_y"],
               [[r["expert"], r["matrice"], r["ecart_relatif"], r["max_y"]] for r in j["reels"]])


if __name__ == "__main__":
    justesse()
    trc()
    debit_k1()
    reference_03()
    debit_k2()
