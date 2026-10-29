"""Pilote de l'étape E2 du lot E : le chemin disque → VRAM décodé sur gpt-oss-20b (`banc-chemin chemin`).

Témoins, cassure et seuils déclarés avant toute ligne de code d'E2 (moteur/REPRISE-E.md, « E2 ») :
  - C2 : les 768 experts, chacun décodé sur la carte puis redescendu, ont l'empreinte64 d'origine
    écrite au répertoire ; 0 écart ;
  - cassure : une copie du fichier à 12 bits retournés dans 12 experts (`banc-chemin casser-copie`)
    → les 12 détectés, aucun autre ;
  - débit : médiane des passes A propres ≥ 0,8 × 2,58 × r(F1) = 2,2815 Go/s d'experts servis ;
    médiane des A ≤ 1,10 × le plus petit étage de la séance (disque seul, DMA seule, décodage seul).

Étapes, chacune sous le verrou de la carte et seulement quand la machine est prête (secteur, aucun
llama-*, aucun verrou, disque et processeur calmes : les conditions du pilote d'E1, règle 2) :
  1. `casser-copie` si la copie n'existe pas encore (11,2 Go écrits : sous le verrou aussi, pour
     qu'aucune mesure de débit d'un autre lot ne tombe sur un disque qui écrit) ;
  2. `chemin --temoin-seul --attendus` sur la copie (la cassure) ;
  3. `chemin` sur le vrai fichier : passe témoin (C2), puis A B B A × 2 et les étages seuls.
Une séance de débit dont moins de 2 passes A sont propres est gardée et refaite, au plus
`--tentatives` fois. Rien n'est jeté. Le binaire est construit par `construire.bat e2` ; le commit de
l'instantané des crates des autres lots est journalisé.

Usage : python -I -X utf8 mesures/moteur/E/pilote_e2.py [--seance NOM] [--attendre-min 240] [--tentatives 3]
        [--sans-cassure] [--sans-debit] [--longueur-lecture OCTETS]
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
import time

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import pilote_e0 as p0  # noqa: E402
import pilote_e1 as p1  # noqa: E402

FICHIER = r"~\dev\modeles\trc\gpt-oss-20b.trc"
COPIE = r"~\dev\modeles\trc\casse\gpt-oss-20b-casse-E2.trc"
INSTANTANE = r"~\dev\cibles\troncons-E\instantane\COMMIT.txt"
GRAINE = 20261015
SEUIL_ETRANGERS = p1.SEUIL_ETRANGERS
SEUIL_PROCESSEUR_AUTRES = p1.SEUIL_PROCESSEUR_AUTRES
MARQUE = "lot E (E2"


def prendre_verrou(quoi):
    if p1.verrou_tenu():
        return False
    try:
        if os.path.exists(p0.VERROU):
            os.remove(p0.VERROU)  # périmé (plus de 2 h)
        with open(p0.VERROU, "x", encoding="utf-8") as f:
            f.write(f"{MARQUE}, {quoi}), pris le {p0.maintenant()}\n")
        return True
    except FileExistsError:
        return False


def rendre_verrou():
    try:
        with open(p0.VERROU, encoding="utf-8", errors="replace") as f:
            a_nous = f.read().startswith(MARQUE)
        if a_nous:
            os.remove(p0.VERROU)
    except FileNotFoundError:
        pass


def attendre_la_machine(seance, limite):
    derniere = None
    while time.time() < limite:
        raison = p1.conditions()
        if raison is None:
            return True
        if raison.split(" (")[0] != (derniere or "").split(" (")[0]:
            print(f"{p0.maintenant()} j'attends : {raison}", flush=True)
            seance["attentes"].append({"heure": p0.maintenant(), "raison": raison})
        derniere = raison
        time.sleep(20)
    return False


def lancer(seance, dossier, nom, args, quoi, limite):
    """Attend la machine, prend le verrou, lance le banc, rend le verrou ; rend le journal lu."""
    while True:
        if not attendre_la_machine(seance, limite):
            raise TimeoutError(f"machine jamais prête pour {nom}")
        if prendre_verrou(quoi):
            break
    journal = os.path.join(dossier, f"{nom}.json")
    commande = [seance["banc"], *args, "--journal", journal]
    avant = {"heure": p0.maintenant(), "batterie": p0.statut_batterie(), "carte": p0.carte()}
    t0 = time.time()
    try:
        r = subprocess.run(commande, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=4 * 3600)
    finally:
        rendre_verrou()
    apres = {"heure": p0.maintenant(), "batterie": p0.statut_batterie(), "carte": p0.carte()}
    with open(os.path.join(dossier, f"{nom}.stderr.txt"), "w", encoding="utf-8") as f:
        f.write(r.stderr)
    seance["etapes"].append({"nom": nom, "commande": commande, "code": r.returncode, "secondes": time.time() - t0,
                             "avant": avant, "apres": apres})
    print(f"{p0.maintenant()} {nom} : code {r.returncode}\n   " + r.stderr.strip().replace("\n", "\n   "), flush=True)
    try:
        with open(journal, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def passes_a_propres(j):
    try:
        passes = j["resultat"]["passes"]
    except (KeyError, TypeError):
        return 0
    n = 0
    for x in passes:
        p = x["passe"]
        if x["lettre"] != "A" or p.get("go_s_etrangers") is None:
            continue
        if p["go_s_etrangers"] * 1e9 <= SEUIL_ETRANGERS and p["processeur"]["autres"] <= SEUIL_PROCESSEUR_AUTRES:
            n += 1
    return n


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--banc", default=p0.BANC)
    a.add_argument("--seance", default="e2-" + datetime.datetime.now().strftime("%Y-%m-%d-%H%M"))
    a.add_argument("--attendre-min", type=float, default=240)
    a.add_argument("--tentatives", type=int, default=3)
    a.add_argument("--sans-cassure", action="store_true")
    a.add_argument("--sans-debit", action="store_true")
    a.add_argument("--longueur-lecture", type=int, default=None, help="variante E2-V : longueur fixe de chaque lecture")
    o = a.parse_args()
    dossier = os.path.join(ICI, "journaux", o.seance)
    os.makedirs(dossier, exist_ok=True)
    commit = subprocess.run(["git", "-C", p0.DEPOT, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    try:
        with open(INSTANTANE, encoding="utf-8") as f:
            instantane = f.read().strip()
    except OSError:
        instantane = None
    seance = {"seance": o.seance, "debut": p0.maintenant(), "commit": commit, "instantane_des_crates": instantane,
              "banc": o.banc, "banc_sha256": p0.sha256(o.banc), "fichier": FICHIER, "copie": COPIE,
              "etapes": [], "attentes": []}
    limite = time.time() + o.attendre_min * 60
    try:
        if not o.sans_cassure:
            journal_copie = os.path.join(dossier, "casser-copie.json")
            if not os.path.exists(COPIE):
                lancer(seance, dossier, "casser-copie",
                       ["casser-copie", "--source", FICHIER, "--copie", COPIE, "--graine", str(GRAINE), "--n", "12"],
                       "copie corrompue de 11 Go, ~2 min", limite)
            elif not os.path.exists(journal_copie):
                raise RuntimeError(f"{COPIE} existe sans son journal dans cette séance : passer le journal de la séance qui l'a faite")
            lancer(seance, dossier, "cassure",
                   ["chemin", "--fichier", COPIE, "--temoin-seul", "--attendus", journal_copie, "--graine", str(GRAINE + 7)],
                   "cassure de C2, ~1 min", limite)
        if not o.sans_debit:
            for k in range(1, o.tentatives + 1):
                v = f"-v{o.longueur_lecture}" if o.longueur_lecture else ""
                extra = ["--longueur-lecture", str(o.longueur_lecture)] if o.longueur_lecture else []
                j = lancer(seance, dossier, f"chemin{v}-{k}",
                           ["chemin", "--fichier", FICHIER, "--graine", str(GRAINE + 100 * k), "--tours-abba", "2",
                            "--residents", "48", "--chronogrammes", os.path.join(dossier, f"chrono{v}-{k}"), *extra],
                           "E2, témoin C2 et débit, ~2 min", limite)
                propres = passes_a_propres(j)
                seance["etapes"][-1]["passes_a_propres"] = propres
                print(f"{p0.maintenant()} chemin-{k} : {propres} passe(s) A propre(s)", flush=True)
                if j is not None and propres >= 2:
                    break
                time.sleep(60)
    finally:
        rendre_verrou()
        seance["fin"] = p0.maintenant()
        with open(os.path.join(dossier, "seance.json"), "w", encoding="utf-8") as f:
            json.dump(seance, f, ensure_ascii=False, indent=2)
    print(f"{p0.maintenant()} séance {o.seance} finie")


if __name__ == "__main__":
    main()
