"""Pilote du banc disque : témoins, balayage bloc × profondeur de file en ordre ABBA,
comparaison IOCP / IoRing, second chemin par le compteur cumulé du système (CIM).

Bibliothèque standard seulement. Usage :
  python -I outils/banc/pilote_disque.py --exe CHEMIN/disque.exe --fichier CHEMIN/test.bin
         --sortie fondations/journaux/01-machine/disque-balayage.jsonl [--duree 2]

Chaque passe donne une ligne JSON : la ligne RESULTAT de l'outil, l'heure de début et de fin,
et les octets lus selon le compteur du système pendant la fenêtre (tout processus confondu :
l'écart avec l'outil chiffre la charge des autres).
"""

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time

PLAFOND_NVME = 4 * 16e9 * 128 / 130 / 8 / 1e9  # 7,877 Go/s, PCIe 4.0 x4
EN_VOL_MAX = 256 << 20  # octets en vol au plus (qd x bloc) : la RAM libre est maigre


def analyser(ligne):
    d = {}
    for morceau in ligne.split()[1:]:
        if "=" in morceau:
            k, v = morceau.split("=", 1)
            try:
                d[k] = float(v) if any(c in v for c in ".e") or v.lstrip("-").isdigit() else v
            except ValueError:
                d[k] = v
    return d


def lancer(exe, args):
    debut = time.time()
    p = subprocess.run([exe] + args, capture_output=True, text=True, encoding="utf-8")
    fin = time.time()
    res = [l for l in p.stdout.splitlines() if l.startswith("RESULTAT")]
    if p.returncode != 0 or not res:
        raise RuntimeError(f"échec {args}: {p.stdout[-500:]} {p.stderr[-800:]}")
    d = analyser(res[-1])
    d["debut"], d["fin"] = debut, fin
    return d


class Compteur:
    """Second chemin : compteur cumulé du système (Win32_PerfRawData_PerfDisk_PhysicalDisk, _Total,
    DiskReadBytesPersec), relevé deux fois par seconde par un PowerShell persistant. Les noms CIM
    sont anglais quelle que soit la langue de Windows (typeperf, lui, attend les noms traduits)."""

    SCRIPT = (
        "$ErrorActionPreference='Stop'; while ($true) { "
        "$c = Get-CimInstance Win32_PerfRawData_PerfDisk_PhysicalDisk -Filter \"Name='_Total'\"; "
        "$p = Get-CimInstance Win32_PerfRawData_PerfOS_Processor -Filter \"Name='_Total'\"; "
        "$t = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds(); "
        "Add-Content -Path $env:BANC_CSV -Value (\"$t,\" + $c.DiskReadBytesPersec + ',' + $p.PercentProcessorTime + ',' "
        "+ $p.PercentPrivilegedTime + ',' + $p.Timestamp_Sys100NS); Start-Sleep -Milliseconds 500 }"
    )

    def __init__(self, chemin_csv):
        self.chemin = chemin_csv
        env = dict(os.environ, BANC_CSV=chemin_csv)
        self.p = subprocess.Popen(["powershell", "-NoProfile", "-Command", self.SCRIPT], env=env,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3)

    def arreter(self):
        self.p.terminate()
        try:
            self.p.wait(5)
        except subprocess.TimeoutExpired:
            self.p.kill()

    def lire(self):
        echant = []
        with open(self.chemin, encoding="utf-8", errors="replace") as f:
            for ligne in f:
                try:
                    t, v, inactif, noyau, ts = ligne.strip().split(",")
                    echant.append((int(t) / 1000.0, int(v), int(inactif), int(noyau), int(ts)))
                except ValueError:
                    pass
        return echant


def octets_systeme(echant, debut, fin):
    """Octets lus par tout le système entre le dernier relevé avant `debut` et le premier après `fin`."""
    avant = [e for e in echant if e[0] <= debut]
    apres = [e for e in echant if e[0] >= fin]
    if not avant or not apres:
        return None
    a, b = avant[-1], apres[0]
    dts = max(b[4] - a[4], 1)
    # PercentProcessorTime brut = temps inactif cumulé (type PERF_100NSEC_TIMER_INV), moyenne des processeurs.
    return {"octets": b[1] - a[1], "secondes": b[0] - a[0],
            "cpu_occupe": round(1 - (b[2] - a[2]) / dts, 4), "cpu_noyau": round((b[3] - a[3]) / dts, 4)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", required=True)
    ap.add_argument("--fichier", required=True)
    ap.add_argument("--sortie", required=True)
    ap.add_argument("--duree", default="2")
    ap.add_argument("--rapide", action="store_true", help="balayage réduit (essai du pilote)")
    a = ap.parse_args()

    journal = open(a.sortie, "a", encoding="utf-8")

    def noter(genre, d, **extra):
        d = dict(d, genre=genre, **extra)
        journal.write(json.dumps(d, ensure_ascii=False) + "\n")
        journal.flush()
        return d

    base = ["lire", "--fichier", a.fichier, "--duree", a.duree, "--chauffe", "0.5"]
    csv_chemin = a.sortie + ".compteur.csv"
    if os.path.exists(csv_chemin):
        os.remove(csv_chemin)
    cpt = Compteur(csv_chemin)
    verdicts = []
    try:
        # --- Témoins -------------------------------------------------------------------
        d = lancer(a.exe, base + ["--moteur", "iocp", "--acces", "seq", "--bloc", "1M", "--qd", "4", "--fausser"])
        ok = d["pages_fausses"] == d["pages_verifiees"] > 0
        verdicts.append(("temoin_fausser_tombe", ok))
        noter("temoin", d, nom="fausser", reussi=ok)
        d = lancer(a.exe, base + ["--moteur", "iocp", "--acces", "seq", "--bloc", "1M", "--qd", "4"])
        ok = d["pages_fausses"] == 0 and d["erreurs"] == 0 and d["pages_verifiees"] > 0
        verdicts.append(("temoin_contenu", ok))
        noter("temoin", d, nom="contenu", reussi=ok)
        for tour in (1, 2):
            d = lancer(a.exe, ["lire", "--fichier", a.fichier, "--duree", "3", "--chauffe", "0.5", "--moteur", "tampon",
                               "--acces", "seq", "--bloc", "1M", "--qd", "4", "--region", "1G"])
            # Le verdict se rend après coup, contre le compteur du système (voir plus bas).
            noter("temoin", d, nom=f"cache_tour{tour}")

        # --- Balayage ABBA ---------------------------------------------------------------
        blocs = ["4K", "64K", "1M", "16M"] if a.rapide else ["4K", "16K", "64K", "256K", "1M", "4M", "16M"]
        qds = [1, 8, 32] if a.rapide else [1, 2, 4, 8, 16, 32, 64]
        def taille(b):
            return int(b[:-1]) * (1024 if b[-1] == "K" else 1 << 20)
        configs = [(acc, b, q) for acc in ("alea", "seq") for b in blocs for q in qds if taille(b) * q <= EN_VOL_MAX]
        ordre = configs + configs[::-1]
        for rang, (acc, b, q) in enumerate(ordre):
            d = lancer(a.exe, base + ["--moteur", "iocp", "--acces", acc, "--bloc", b, "--qd", str(q)])
            noter("balayage", d, passage="A" if rang < len(configs) else "B")
            sys.stdout.write(f"\r{rang + 1}/{len(ordre)} {acc} {b} qd{q} {d['debit_go_s']:.3f} Go/s   ")
            sys.stdout.flush()
        print()

        # --- IOCP contre IoRing, ABBA, deux fois ----------------------------------------
        for acc, b, q in [("alea", "4K", 1), ("alea", "4K", 32), ("alea", "64K", 16), ("seq", "1M", 8), ("seq", "16M", 4)]:
            for moteur in ["iocp", "ioring", "ioring", "iocp"] * 2:
                d = lancer(a.exe, base + ["--moteur", moteur, "--acces", acc, "--bloc", b, "--qd", str(q)])
                noter("moteurs", d)
    finally:
        time.sleep(1.5)
        cpt.arreter()

    # --- Second chemin : compteur du système --------------------------------------------
    echant = cpt.lire()
    journal.close()
    lignes = [json.loads(l) for l in open(a.sortie, encoding="utf-8")]
    sortie = open(a.sortie, "w", encoding="utf-8")
    hors_plafond = 0
    sans_tampon_vus = []  # rapport octets système / octets outil, lectures sans tampon
    for d in lignes:
        if "debut" in d and d.get("op") == "lire":
            o = octets_systeme(echant, d["debut"], d["fin"])
            d["octets_systeme_fenetre"] = o
            # Octets de l'outil sur toute sa vie (chauffe comprise) : débit x (chauffe + fenêtre), approché.
            outil = d["debit_go_s"] * 1e9 * (d["fenetre_s"] + 0.5)
            if o:
                d["rapport_systeme_sur_outil"] = round(o["octets"] / max(outil, 1), 3)
            if d.get("moteur") != "tampon":
                if d["debit_go_s"] > PLAFOND_NVME:
                    hors_plafond += 1
                if o and d["octets"] > 0:
                    sans_tampon_vus.append(d["rapport_systeme_sur_outil"])
            if d.get("nom") == "cache_tour2" and o:
                # Témoin du cache, version compteur : servi par la RAM, le disque n'a presque rien lu.
                ok = o["octets"] < 0.10 * outil
                d["reussi"] = ok
                verdicts.append(("temoin_cache_visible_compteur", ok))
        sortie.write(json.dumps(d, ensure_ascii=False) + "\n")
    verdicts.append(("aucune_lecture_sans_tampon_au_dessus_du_lien", hors_plafond == 0))
    # Sans tampon, le système doit avoir vu au moins 90 % de nos octets passer par le disque.
    sous = [r for r in sans_tampon_vus if r < 0.90]
    verdicts.append(("sans_tampon_vu_par_le_disque", not sous))
    sortie.write(json.dumps({"genre": "verdicts", "verdicts": verdicts, "releves_compteur": len(echant)}, ensure_ascii=False) + "\n")
    sortie.close()
    for nom, ok in verdicts:
        print(f"{nom}: {'ok' if ok else 'ECHEC'}")


if __name__ == "__main__":
    main()
