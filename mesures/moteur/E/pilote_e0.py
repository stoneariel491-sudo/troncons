"""Pilote des essais E0 du lot E (ARCHITECTURE.md § 6.5) : une séance complète, journalisée.

Conditions vérifiées avant toute mesure (consigne du lot) :
  - la machine est sur secteur : Win32_Battery.BatteryStatus = 2 (relevé par PowerShell, CIM) ;
  - aucun llama-* ni traceur gpt-oss ne tourne sur la carte (tasklist et nvidia-smi) ;
  - le verrou de la carte, ~/dev/verrou-carte.txt : s'il existe et a moins de 2 h, on
    attend et on réessaie ; sinon on le crée (lot, heure) et on le retire à la fin, même sur erreur.

La séance (ordre fixe, chaque journal sous mesures/moteur/E/journaux/<séance>/) :
  a.        essai-a : épingler 0,25 / 1 / 4 / 11 Go sous la marge de RAM déclarée ;
  b-temoin  essai-b : 32 morceaux de 12 Mio, disque → épinglée → VRAM → hôte contre std::fs ;
  b-casse   essai-b --casser : un octet faussé, 1 écart attendu ;
  b-A1, b-B1, b-B2, b-A2 : essai-b, débits, ABBA sur la profondeur de lecture (A = 4, B = 1) ;
  c-*       essai-c : deux charges (0/0 et 50/250 µs), six variantes en ABBA interne ; une passe
            avec le contexte en attente bloquante ; la cassure (sans_synchro).

Usage : python -I -X utf8 mesures/moteur/E/pilote_e0.py [--banc EXE] [--modele GGUF]
        [--seance NOM] [--attendre-min 240] [--sans-verrou-court]
"""

import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time

ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.abspath(os.path.join(ICI, "..", "..", ".."))
VERROU = r"~\dev\verrou-carte.txt"
BANC = r"~\dev\cibles\troncons-E\release\banc-chemin.exe"
MODELE = r"~\dev\modeles\gguf\gpt-oss-20b-MXFP4.gguf"
INTERDITS = ("llama-", "traceur.exe")


def maintenant():
    return datetime.datetime.now().isoformat(timespec="seconds")


def statut_batterie():
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Battery).BatteryStatus"],
        capture_output=True, text=True, errors="replace", timeout=60,
    )
    try:
        return int(r.stdout.strip().splitlines()[0])
    except (ValueError, IndexError):
        return None


def processus_interdits():
    # tasklist écrit dans la page de code OEM (espaces insécables 0xFF dans les tailles) : décodée telle quelle.
    r = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True, text=True, encoding="oem", errors="replace", timeout=60)
    noms = [ligne.split('","')[0].strip('"') for ligne in r.stdout.splitlines() if ligne]
    return sorted({n for n in noms if n.lower().startswith(INTERDITS)})


def carte():
    r = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used,memory.total,utilization.gpu,pstate,pcie.link.gen.current,"
         "pcie.link.width.current,temperature.gpu,clocks.sm", "--format=csv,noheader,nounits"],
        capture_output=True, text=True, errors="replace", timeout=60,
    )
    return r.stdout.strip()


def sha256(chemin):
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def prendre_verrou(attendre_min):
    limite = time.time() + attendre_min * 60
    dernier = None  # dernier état d'attente écrit (une ligne par changement)
    while True:
        if os.path.exists(VERROU):
            age = time.time() - os.path.getmtime(VERROU)
            with open(VERROU, encoding="utf-8", errors="replace") as f:
                contenu = f.read().strip()
            if age < 2 * 3600:
                if time.time() > limite:
                    sys.exit(f"verrou tenu depuis {age / 60:.0f} min ({contenu!r}) : abandon après {attendre_min} min")
                if dernier != ("verrou", contenu):
                    print(f"{maintenant()} verrou tenu ({contenu!r}, {age / 60:.0f} min) : j'attends", flush=True)
                    dernier = ("verrou", contenu)
                time.sleep(20)
                continue
            print(f"{maintenant()} verrou périmé ({age / 3600:.1f} h, {contenu!r}) : je le remplace", flush=True)
        interdits = processus_interdits()
        if interdits:
            if time.time() > limite:
                sys.exit(f"processus sur la carte : {interdits} : abandon après {attendre_min} min")
            if dernier != ("interdits", interdits):
                print(f"{maintenant()} carte occupée par {interdits} : j'attends", flush=True)
                dernier = ("interdits", interdits)
            time.sleep(20)
            continue
        with open(VERROU, "x" if not os.path.exists(VERROU) else "w", encoding="utf-8") as f:
            f.write(f"lot E (essais E0, banc-chemin), pris le {maintenant()}\n")
        return


def rendre_verrou():
    # Lire, fermer, puis effacer : Windows refuse d'effacer un fichier encore ouvert (WinError 32,
    # défaut trouvé le 2026-10-15 : le verrou restait derrière le pilote).
    try:
        with open(VERROU, encoding="utf-8", errors="replace") as f:
            a_nous = f.read().startswith("lot E")
        if a_nous:
            os.remove(VERROU)
    except FileNotFoundError:
        pass


def lancer(banc, dossier, nom, args, seance):
    journal = os.path.join(dossier, f"{nom}.json")
    commande = [banc] + args[:1] + ["--journal", journal] + args[1:]
    avant = {"heure": maintenant(), "carte": carte(), "batterie": statut_batterie(), "interdits": processus_interdits()}
    t0 = time.time()
    r = subprocess.run(commande, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=3600)
    apres = {"heure": maintenant(), "carte": carte(), "batterie": statut_batterie(), "interdits": processus_interdits()}
    with open(os.path.join(dossier, f"{nom}.stderr.txt"), "w", encoding="utf-8") as f:
        f.write(r.stderr)
    seance["passes"].append({"nom": nom, "commande": commande, "code": r.returncode, "secondes": time.time() - t0,
                             "avant": avant, "apres": apres})
    print(f"{maintenant()} {nom} : code {r.returncode}, {time.time() - t0:.1f} s ; batterie {apres['batterie']}", flush=True)
    print("   " + r.stderr.strip().replace("\n", "\n   "), flush=True)
    if apres["batterie"] != 2 or apres["interdits"]:
        seance["avertissements"].append(f"{nom} : batterie {apres['batterie']}, interdits {apres['interdits']}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--banc", default=BANC)
    p.add_argument("--modele", default=MODELE)
    p.add_argument("--seance", default=datetime.datetime.now().strftime("%Y-%m-%d-%H%M"))
    p.add_argument("--attendre-min", type=float, default=240)
    p.add_argument("--seulement", default="", help="liste de préfixes de passes à lancer (vide : toutes)")
    a = p.parse_args()

    dossier = os.path.join(ICI, "journaux", a.seance)
    os.makedirs(dossier, exist_ok=True)
    batterie = statut_batterie()
    if batterie != 2:
        sys.exit(f"Win32_Battery.BatteryStatus = {batterie} : pas sur secteur, aucune mesure de débit (consigne)")
    commit = subprocess.run(["git", "-C", DEPOT, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    seance = {"seance": a.seance, "debut": maintenant(), "batterie_debut": batterie, "commit": commit,
              "banc": a.banc, "banc_sha256": sha256(a.banc), "modele": a.modele, "passes": [], "avertissements": []}

    passes = [
        ("a", ["essai-a"]),
        ("b-temoin", ["essai-b", "--fichier", a.modele, "--morceaux", "32", "--serie", "8", "--repetitions-dma", "4", "--tours-abba", "1"]),
        ("b-casse", ["essai-b", "--fichier", a.modele, "--morceaux", "4", "--serie", "8", "--repetitions-dma", "4", "--tours-abba", "1", "--casser"]),
    ]
    for nom, qd in (("b-A1", 4), ("b-B1", 1), ("b-B2", 1), ("b-A2", 4)):
        passes.append((nom, ["essai-b", "--fichier", a.modele, "--morceaux", "4", "--serie", "128", "--profondeur", str(qd),
                             "--graine", str(20261015 + len(passes)), "--repetitions-dma", "16", "--tours-abba", "2"]))
    variantes = "asynchrone,evenement,sondage,bloquant,boite,boite_sans_vidage"
    passes += [
        ("c-vide", ["essai-c", "--variantes", variantes, "--jetons", "30", "--chauffe", "3", "--tours-abba", "2"]),
        ("c-charge", ["essai-c", "--variantes", variantes, "--jetons", "30", "--chauffe", "3", "--tours-abba", "2",
                      "--ns-routeur", "50000", "--ns-expert", "250000"]),
        ("c-charge-ctx-bloquant", ["essai-c", "--variantes", "asynchrone,evenement,boite", "--jetons", "30", "--chauffe", "3",
                                   "--tours-abba", "2", "--ns-routeur", "50000", "--ns-expert", "250000", "--attente", "bloquante"]),
        ("c-casse", ["essai-c", "--variantes", "asynchrone,sans_synchro", "--jetons", "10", "--chauffe", "1", "--tours-abba", "1",
                     "--ns-routeur", "50000", "--ns-expert", "250000"]),
    ]
    if a.seulement:
        prefixes = tuple(a.seulement.split(","))
        passes = [x for x in passes if x[0].startswith(prefixes)]

    prendre_verrou(a.attendre_min)
    try:
        seance["carte_debut"] = carte()
        for nom, args in passes:
            lancer(a.banc, dossier, nom, args, seance)
    finally:
        rendre_verrou()
        seance["fin"] = maintenant()
        seance["batterie_fin"] = statut_batterie()
        with open(os.path.join(dossier, "seance.json"), "w", encoding="utf-8") as f:
            json.dump(seance, f, ensure_ascii=False, indent=2)
    print(f"{maintenant()} séance {a.seance} finie ; avertissements : {seance['avertissements']}")


if __name__ == "__main__":
    main()
