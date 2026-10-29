"""La suite « sur secteur » : les mesures que la batterie fausse, relancées dès que la machine est
branchée.

Constat qui la motive (2026-10-15, 07:25) : la machine est passée sur batterie pendant les mesures.
Sur batterie, le pilote impose à la carte un plafond de 52,6 W (80 W par défaut, 140 W au plus),
la mémoire de la carte descend à 6 001 MHz (P4) au lieu de 8 001, le lien PCIe retombe en Gen 3 et
le processeur tourne vers 1,5 GHz. Les mesures de RAM, de thermique et de llama.cpp faites ainsi
décrivent le régime batterie, pas la machine.

Ce que fait la suite, après 120 s continues sur secteur (GetSystemPowerStatus, relevé toutes les
10 s) :
  0. disque : quatre cellules du balayage (16 Mio aléa QD 1, 1 Mio séq QD 4, 4 Mio aléa QD 2,
     4 Kio aléa QD 32), en ABBA, puis déchiffrement XTS-AES-128 sur le processeur (aes_xts.py) ;
  1. RAM : memoire.exe verrouillé, 256 Mio, fils 1..16 puis 16..1 (ABBA), 5 passes ;
  2. carte : vram et transfert 64 Mio (Vulkan), pour relier ce passage aux séries de la nuit ;
  3. llama.cpp b11515, Qwen3.5-9B Q4_K_M, ABBA sur 99:none, 99:mmap, 24:mmap, 16:mmap, 16:none, 8:mmap ;
  4. llama.cpp gpt-oss-20b MXFP4 (12,1 Go, plus gros que la VRAM) : 99:mmap:12, 99:mmap:24 (ABBA) ;
  5. thermique réelle : llama-bench -ngl 99, 16 répétitions de 256 jetons, nvidia-smi chaque seconde ;
  6. thermique GEMV q4b 300 s (pilote_thermique.py).
Chaque étape note la source d'alimentation avant et après ; si la machine repasse sur batterie,
l'étape est marquée « batterie » et la suite se remet à attendre.

Bibliothèque standard seulement. Usage :
  python -I -X utf8 outils/banc/suite_secteur.py --sortie fondations/journaux/01-machine/secteur
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import datetime
import os
import subprocess
import sys
import time

ICI = os.path.dirname(os.path.abspath(__file__))
CIBLE = "~/dev/essais/troncons/banc/target/release"
LLAMA = "~/dev/modeles/llama.cpp-b11515"
GGUF = "~/dev/modeles/gguf"


class SPS(ctypes.Structure):
    _fields_ = [("ACLineStatus", ctypes.c_ubyte), ("BatteryFlag", ctypes.c_ubyte), ("BatteryLifePercent", ctypes.c_ubyte),
                ("SystemStatusFlag", ctypes.c_ubyte), ("BatteryLifeTime", wt.DWORD), ("BatteryFullLifeTime", wt.DWORD)]


def secteur():
    s = SPS()
    ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s))
    return int(s.ACLineStatus), int(s.BatteryLifePercent)


def journal(f, texte):
    ligne = f"{datetime.datetime.now().isoformat(timespec='seconds')} {texte}"
    print(ligne, flush=True)
    f.write(ligne + "\n")
    f.flush()


def attendre_secteur(f, duree=120):
    depuis = None
    while True:
        ac, pct = secteur()
        if ac == 1:
            depuis = depuis or time.time()
            if time.time() - depuis >= duree:
                journal(f, f"secteur depuis {duree} s (batterie {pct} %) : départ")
                return
        else:
            if depuis is not None:
                journal(f, f"retour sur batterie ({pct} %) : attente")
            depuis = None
        time.sleep(10)


def etape(f, nom, cmd, sortie):
    ac0 = secteur()
    journal(f, f"DEBUT {nom} secteur={ac0[0]} batterie={ac0[1]} %")
    with open(sortie, "a", encoding="utf-8") as o:
        o.write(f"== {nom} {datetime.datetime.now().isoformat(timespec='seconds')} secteur={ac0[0]}\n")
        o.flush()
        rc = subprocess.run(cmd, stdout=o, stderr=subprocess.STDOUT).returncode
    ac1 = secteur()
    etat = "secteur" if ac0[0] == 1 and ac1[0] == 1 else "batterie"
    journal(f, f"FIN {nom} code={rc} regime={etat} batterie={ac1[1]} %")
    return etat == "secteur"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sortie", required=True)
    a = ap.parse_args()
    os.makedirs(a.sortie, exist_ok=True)
    S = a.sortie
    py = [sys.executable, "-I", "-X", "utf8"]
    test = "~/dev/essais/troncons/banc/test.bin"
    cellules = [("alea", "16M", "1"), ("seq", "1M", "4"), ("alea", "4M", "2"), ("alea", "4K", "32")]
    disque = []
    for i, (acces, bloc, qd) in enumerate(cellules + cellules[::-1]):
        disque.append((f"disque_{'A' if i < len(cellules) else 'B'}_{acces}_{bloc}_qd{qd}",
                       [f"{CIBLE}/disque.exe", "lire", "--fichier", test, "--moteur", "iocp", "--acces", acces,
                        "--bloc", bloc, "--qd", qd, "--duree", "3"], "disque.log"))
    if not os.path.exists(test):
        # Fichier de test effacé (il pèse 32 Gio) : le refaire d'abord, au motif vérifiable.
        disque.insert(0, ("disque_preparer", [f"{CIBLE}/disque.exe", "preparer", "--fichier", test, "--taille", "32G"],
                          "disque.log"))
    etapes = disque + [
        ("aes_xts", py + [f"{ICI}/aes_xts.py", "--cle", "128", "--fils", "1,2,4,8,1", "--passes", "3"], "aes-xts.log"),
        ("ram_A", [f"{CIBLE}/memoire.exe", "--taille", "256M", "--fils", "1,2,4,8,16", "--passes", "5"], "memoire.log"),
        ("ram_B", [f"{CIBLE}/memoire.exe", "--taille", "256M", "--fils", "16,8,4,2,1", "--passes", "5"], "memoire.log"),
        ("vram", [f"{CIBLE}/carte.exe", "vram", "--api", "vulkan", "--passes", "5"], "carte.log"),
        ("transfert", [f"{CIBLE}/carte.exe", "transfert", "--api", "vulkan", "--tailles", "64M", "--passes", "3"], "carte.log"),
        ("llama_9b", py + [f"{ICI}/pilote_llama.py", "--bin", LLAMA, "--modele", f"{GGUF}/Qwen3.5-9B-Q4_K_M.gguf",
                           "--sortie", f"{S}/llama-9b.jsonl", "--n", "48", "--r", "3",
                           "--configs", "99:none,99:mmap,24:mmap,16:mmap,16:none,8:mmap"], "llama.log"),
        ("llama_20b", py + [f"{ICI}/pilote_llama.py", "--bin", LLAMA, "--modele", f"{GGUF}/gpt-oss-20b-MXFP4.gguf",
                            "--sortie", f"{S}/llama-20b.jsonl", "--n", "48", "--r", "3",
                            "--configs", "99:mmap:12,99:mmap:24"], "llama.log"),
        ("thermique_llama", py + [f"{ICI}/pilote_llama.py", "--bin", LLAMA, "--modele", f"{GGUF}/Qwen3.5-9B-Q4_K_M.gguf",
                                  "--sortie", f"{S}/thermique-llama.jsonl", "--n", "256", "--r", "16",
                                  "--configs", "99:none"], "thermique-llama.log"),
        ("thermique_gemv", py + [f"{ICI}/pilote_thermique.py", "--exe", f"{CIBLE}/carte.exe", "--dossier", S], "thermique-pilote.log"),
    ]
    with open(f"{S}/suite.log", "a", encoding="utf-8") as f:
        i = 0
        while i < len(etapes):
            attendre_secteur(f)
            nom, cmd, sortie = etapes[i]
            if nom == "thermique_llama":
                nv = subprocess.Popen(["nvidia-smi", "--query-gpu=timestamp,temperature.gpu,clocks.sm,clocks.mem,power.draw,"
                                       "enforced.power.limit,utilization.gpu,pstate,clocks_throttle_reasons.active,pcie.link.gen.current",
                                       "--format=csv,noheader", "-l", "1"], stdout=open(f"{S}/thermique-llama-nvsmi.csv", "w"))
                ok = etape(f, nom, cmd, f"{S}/{sortie}")
                nv.terminate()
            else:
                ok = etape(f, nom, cmd, f"{S}/{sortie}")
            if ok:
                i += 1
            else:
                journal(f, f"{nom} faussé par la batterie : à refaire")
        if os.path.exists(test):
            os.remove(test)
            journal(f, "fichier de test de 32 Gio effacé")
        journal(f, "suite terminée")


if __name__ == "__main__":
    main()
