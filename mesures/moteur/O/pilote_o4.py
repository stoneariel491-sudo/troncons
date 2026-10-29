"""Pilote de l'étape O4 = J1 du lot O : vitesse (C5), fenêtre bornée (C7), octets lus (C8), VRAM (C10).

Critères déclarés avant le lancement : moteur/REPRISE-O.md, « O4 ».

Une séance = six passes, chacune un processus neuf, dans cet ordre :
    A120  D  Y20  Y20  D  A120
  A120 : `troncons mesurer` sur gpt-oss-120b.trc (invite wikitext de 06 § 7.2, 256 jetons gloutons,
         mode A0 : aucune RAM tiède, enchâssement lu du disque) ;
  D    : `troncons disque` sur gpt-oss-120b.trc (l'étage disque seul, mêmes longueurs de lecture) ;
  Y20  : `troncons mesurer` sur gpt-oss-20b.trc (mêmes options).
Les sous-séries A120 D D A120 (C5) et A120 Y20 Y20 A120 (C7) sont chacune symétriques dans le temps
(ABBA). Avant chaque passe : alimentation (Win32_Battery BatteryStatus = 2), aucun llama-* ; le
verrou de la carte est tenu toute la séance.

Usage (depuis la racine du dépôt) :
  python -I -X utf8 mesures/moteur/O/pilote_o4.py --seance <nom> [--n 256] [--longueur-lecture X]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
import time

RACINE = pathlib.Path(__file__).resolve().parents[3]
TRONCONS = pathlib.Path("~/dev/cibles/troncons-O/release/troncons.exe")
MODELES = pathlib.Path("~/dev/modeles/trc")
INVITE = pathlib.Path("~/dev/essais/troncons/modeles/donnees/invite-wiki-3000.txt")
INVITE_SHA256 = "eadbe87e3d3ce6c81035a2a4d83f898d887ce7d76bd4336555d615ee0522ceff"
VERROU = pathlib.Path("~/dev/verrou-carte.txt")
JOURNAUX = RACINE / "mesures/moteur/O/journaux/o4"


def maintenant() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ps(cmd: str) -> str:
    return subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True).stdout.strip()


def alimentation() -> str:
    return ps("(Get-CimInstance Win32_Battery).BatteryStatus")


def llama() -> list[str]:
    s = ps("Get-Process | Where-Object { $_.ProcessName -like 'llama*' } | ForEach-Object { $_.ProcessName + ':' + $_.Id }")
    return [x for x in s.splitlines() if x.strip()]


def vram_mio() -> int:
    s = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True).stdout
    return int(s.strip().splitlines()[0])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seance", required=True)
    ap.add_argument("--n", type=int, default=256)
    ap.add_argument("--longueur-lecture", type=int, default=None)
    ap.add_argument("--disque-n", type=int, default=1500)
    a = ap.parse_args()
    import hashlib
    if hashlib.sha256(INVITE.read_bytes()).hexdigest() != INVITE_SHA256:
        print("invite : empreinte inattendue", file=sys.stderr)
        return 2
    JOURNAUX.mkdir(parents=True, exist_ok=True)
    fj = open(JOURNAUX / f"pilote-{a.seance}.log", "a", encoding="utf-8")

    def journal(m: str) -> None:
        ligne = f"[{maintenant()}] {m}"
        print(ligne, flush=True)
        fj.write(ligne + "\n")
        fj.flush()

    while VERROU.exists() and time.time() - VERROU.stat().st_mtime < 2 * 3600:
        journal(f"verrou présent : {VERROU.read_text(encoding='utf-8', errors='replace').strip()!r} ; attente")
        time.sleep(60)
    VERROU.write_text(f"lot O, {maintenant()}, pilote_o4.py, pid {os.getpid()}\n", encoding="utf-8")
    resume = {"seance": a.seance, "debut": maintenant(), "passes": []}
    plan = [("A120", "mesurer", "gpt-oss-120b"), ("D", "disque", "gpt-oss-120b"), ("Y20", "mesurer", "gpt-oss-20b"),
            ("Y20", "mesurer", "gpt-oss-20b"), ("D", "disque", "gpt-oss-120b"), ("A120", "mesurer", "gpt-oss-120b")]
    try:
        for i, (lettre, cmd, modele) in enumerate(plan, 1):
            al, ll, vr = alimentation(), llama(), vram_mio()
            journal(f"passe {i}/{len(plan)} {lettre} : alimentation {al}, llama {ll}, VRAM {vr} Mio avant")
            if al != "2":
                journal("pas sur secteur : arrêt")
                return 2
            nom = f"{a.seance}-{i}-{lettre}"
            js = JOURNAUX / f"{nom}.json"
            c = [str(TRONCONS), cmd, "--modele", str(MODELES / f"{modele}.trc"), "--journal", str(js)]
            if cmd == "mesurer":
                c += ["--vocab", str(MODELES / f"{modele}.vocab.gguf"), "--invite", str(INVITE), "-n", str(a.n),
                      "--sortie", str(JOURNAUX / f"{nom}.txt"), "--trace", str(JOURNAUX / f"{nom}.trace"), "--repos", "10"]
            else:
                c += ["--n", str(a.disque_n), "--graine", str(i), "--repos", "5"]
            if a.longueur_lecture:
                c += ["--longueur-lecture", str(a.longueur_lecture)]
            t0 = time.time()
            with open(JOURNAUX / f"{nom}.log", "w", encoding="utf-8") as f:
                r = subprocess.run(c, stdout=f, stderr=subprocess.STDOUT)
            p = {"passe": i, "lettre": lettre, "commande": c, "code": r.returncode, "secondes": time.time() - t0,
                 "alimentation_avant": al, "llama_avant": ll, "vram_avant_mio": vr, "alimentation_apres": alimentation(), "journal": str(js)}
            resume["passes"].append(p)
            journal(f"passe {i} {lettre} : code {r.returncode}, {p['secondes']:.0f} s")
            if r.returncode != 0:
                return 1
        resume["fin"] = maintenant()
        return 0
    finally:
        try:
            if VERROU.exists() and "pilote_o4.py" in VERROU.read_text(encoding="utf-8", errors="replace"):
                VERROU.unlink()
        except OSError:
            pass
        (JOURNAUX / f"pilote-{a.seance}.json").write_text(json.dumps(resume, ensure_ascii=False, indent=1), encoding="utf-8")
        fj.close()


if __name__ == "__main__":
    sys.exit(main())
