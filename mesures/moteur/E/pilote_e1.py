"""Pilote de la mesure E1 du lot E : débit du lecteur sans tampon, disque seul (`banc-chemin lecteur`).

Seuils et règle de propreté déclarés avant toute passe mesurée (moteur/REPRISE-E.md, « E1, débit du
lecteur sur le disque seul ») : médiane des passes A propres (12 Mio, QD 4) ≥ 2,064 Go/s ; une
passe est propre si les octets étrangers y restent ≤ 0,26 Go/s ; au moins 2 passes A propres pour
juger.

Conditions, vérifiées avant chaque tentative :
  - sur secteur (Win32_Battery.BatteryStatus = 2) ;
  - aucun llama-* (une série chronométrée d'un autre agent serait faussée par nos 13 Go de lecture) ;
  - pas de verrou de la carte de moins de 2 h, de quelque lot qu'il soit, le nôtre compris (une
    mesure de débit est en cours, peut-être l'essai E0 de ce lot) ; pendant ses ~30 s de lecture,
    ce pilote prend lui-même le verrou, pour qu'aucune mesure de débit ne démarre sur le disque
    qu'il charge ;
  - disque calme : la machine lit ≤ 0,26 Go/s sur deux fenêtres de 5 s de suite (compteur brut
    Win32_PerfRawData_PerfDisk_PhysicalDisk, chemin indépendant de celui du banc) ;
  - processeur calme (règle 2, ajoutée le 2026-10-15 à 15 h 43 après la séance 1) : ≤ 40 % de la
    machine occupée sur 3 s (compteur brut Win32_PerfRawData_PerfOS_Processor) ; BitLocker déchiffre
    chaque octet lu sur le processeur (01 § 2.7), un processeur chargé borne le disque.
Une tentative dont moins de 2 passes A sont propres est gardée (journal) et refaite, au plus
`--tentatives` fois. Rien n'est jamais jeté : chaque tentative a son journal.

Usage : python -I -X utf8 mesures/moteur/E/pilote_e1.py [--seance NOM] [--attendre-min 240] [--tentatives 6]
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
import pilote_e0 as p0  # noqa: E402  (fonctions communes : batterie, processus, verrou, empreinte)

SEUIL_ETRANGERS = 0.26e9
SEUIL_PROCESSEUR_AUTRES = 0.40  # règle 2, déclarée le 2026-10-15 à 15 h 43 (REPRISE-E.md)


def disque_lu_par_seconde(fenetre_s=5.0):
    """Octets/s lus par toute la machine sur `fenetre_s` secondes (compteur brut, deux relevés)."""
    cmd = ("$a = Get-CimInstance Win32_PerfRawData_PerfDisk_PhysicalDisk -Filter \"Name='_Total'\"; "
           f"Start-Sleep -Milliseconds {int(fenetre_s * 1000)}; "
           "$b = Get-CimInstance Win32_PerfRawData_PerfDisk_PhysicalDisk -Filter \"Name='_Total'\"; "
           "\"$($b.DiskReadBytesPersec - $a.DiskReadBytesPersec) $($b.Timestamp_Sys100NS - $a.Timestamp_Sys100NS)\"")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, errors="replace", timeout=120)
    try:
        octets, cent_ns = (int(x) for x in r.stdout.split())
        return octets / (cent_ns * 1e-7)
    except ValueError:
        return None


def processeur_occupe(fenetre_s=3.0):
    """Part occupée de tous les fils logiques sur `fenetre_s` s (compteur brut du temps inactif)."""
    cmd = ("$a = Get-CimInstance Win32_PerfRawData_PerfOS_Processor -Filter \"Name='_Total'\"; "
           f"Start-Sleep -Milliseconds {int(fenetre_s * 1000)}; "
           "$b = Get-CimInstance Win32_PerfRawData_PerfOS_Processor -Filter \"Name='_Total'\"; "
           "\"$($b.PercentProcessorTime - $a.PercentProcessorTime) $($b.Timestamp_Sys100NS - $a.Timestamp_Sys100NS)\"")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, errors="replace", timeout=120)
    try:
        inactif, total = (int(x) for x in r.stdout.split())
        return 1.0 - inactif / total
    except (ValueError, ZeroDivisionError):
        return None


def verrou_tenu():
    if not os.path.exists(p0.VERROU):
        return None
    age = time.time() - os.path.getmtime(p0.VERROU)
    with open(p0.VERROU, encoding="utf-8", errors="replace") as f:
        contenu = f.read().strip()
    return contenu if age < 2 * 3600 else None


def prendre_verrou():
    """Crée le verrou s'il est absent ou périmé ; False si un autre l'a pris entre-temps."""
    if verrou_tenu():
        return False
    try:
        if os.path.exists(p0.VERROU):
            os.remove(p0.VERROU)  # périmé (plus de 2 h)
        with open(p0.VERROU, "x", encoding="utf-8") as f:
            f.write(f"lot E (E1, débit du disque, ~1 min), pris le {p0.maintenant()}\n")
        return True
    except FileExistsError:
        return False


def rendre_verrou():
    # Lire, fermer, puis effacer : Windows refuse d'effacer un fichier encore ouvert (WinError 32,
    # défaut trouvé le 2026-10-15 : le verrou restait derrière le pilote).
    try:
        with open(p0.VERROU, encoding="utf-8", errors="replace") as f:
            a_nous = f.read().startswith("lot E (E1")
        if a_nous:
            os.remove(p0.VERROU)
    except FileNotFoundError:
        pass


def conditions():
    """None si la machine est prête ; sinon la raison d'attendre."""
    b = p0.statut_batterie()
    if b != 2:
        return f"batterie {b}"
    llama = [n for n in p0.processus_interdits() if n.lower().startswith("llama-")]
    if llama:
        return f"llama en cours {llama}"
    v = verrou_tenu()
    if v:
        return f"verrou tenu ({v!r})"
    for _ in range(2):
        d = disque_lu_par_seconde()
        if d is None or d > SEUIL_ETRANGERS:
            return f"disque chargé ({'?' if d is None else f'{d / 1e9:.3f} Go/s'})"
    c = processeur_occupe()
    if c is None or c > SEUIL_PROCESSEUR_AUTRES:
        return f"processeur chargé ({'?' if c is None else f'{c * 100:.0f} %'})"
    return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--banc", default=p0.BANC)
    p.add_argument("--modele", default=p0.MODELE)
    p.add_argument("--seance", default="e1-" + datetime.datetime.now().strftime("%Y-%m-%d-%H%M"))
    p.add_argument("--attendre-min", type=float, default=240)
    p.add_argument("--tentatives", type=int, default=6)
    a = p.parse_args()
    dossier = os.path.join(ICI, "journaux", a.seance)
    os.makedirs(dossier, exist_ok=True)
    commit = subprocess.run(["git", "-C", p0.DEPOT, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    seance = {"seance": a.seance, "debut": p0.maintenant(), "commit": commit, "banc": a.banc, "banc_sha256": p0.sha256(a.banc),
              "modele": a.modele, "tentatives": [], "attentes": []}
    limite = time.time() + a.attendre_min * 60
    derniere_raison = None
    try:
        while len(seance["tentatives"]) < a.tentatives and time.time() < limite:
            raison = conditions()
            if raison:
                if raison.split(" (")[0] != (derniere_raison or "").split(" (")[0]:
                    print(f"{p0.maintenant()} j'attends : {raison}", flush=True)
                    seance["attentes"].append({"heure": p0.maintenant(), "raison": raison})
                derniere_raison = raison
                time.sleep(20)
                continue
            derniere_raison = None
            if not prendre_verrou():
                continue
            k = len(seance["tentatives"]) + 1
            journal = os.path.join(dossier, f"lecteur-{k}.json")
            commande = [a.banc, "lecteur", "--journal", journal, "--fichier", a.modele, "--serie", "128", "--tours-abba", "2",
                        "--graine", str(20261015 + 1000 * k), "--repos-s", "3", "--verifier", "4"]
            t0 = time.time()
            try:
                r = subprocess.run(commande, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=3600)
            finally:
                rendre_verrou()
            with open(os.path.join(dossier, f"lecteur-{k}.stderr.txt"), "w", encoding="utf-8") as f:
                f.write(r.stderr)
            propres_a = 0
            try:
                with open(journal, encoding="utf-8") as f:
                    passes = json.load(f)["resultat"]["passes"]
                propres_a = sum(1 for x in passes if x["lettre"] == "A" and x["octets_etrangers"] is not None
                                and x["octets_etrangers"] / x["secondes_mur"] <= SEUIL_ETRANGERS
                                and x.get("processeur", {}).get("autres", 1.0) <= SEUIL_PROCESSEUR_AUTRES)
            except (OSError, KeyError, ValueError):
                pass
            seance["tentatives"].append({"k": k, "heure": p0.maintenant(), "commande": commande, "code": r.returncode,
                                         "secondes": time.time() - t0, "passes_a_propres": propres_a,
                                         "batterie_apres": p0.statut_batterie()})
            print(f"{p0.maintenant()} tentative {k} : code {r.returncode}, {propres_a} passe(s) A propre(s)\n   "
                  + r.stderr.strip().replace("\n", "\n   "), flush=True)
            if r.returncode == 0 and propres_a >= 2:
                break
            time.sleep(60)
    finally:
        rendre_verrou()
        seance["fin"] = p0.maintenant()
        with open(os.path.join(dossier, "seance.json"), "w", encoding="utf-8") as f:
            json.dump(seance, f, ensure_ascii=False, indent=2)
    print(f"{p0.maintenant()} séance {a.seance} finie : {len(seance['tentatives'])} tentative(s)")


if __name__ == "__main__":
    main()
