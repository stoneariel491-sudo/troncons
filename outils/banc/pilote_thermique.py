"""Thermique sur 5 minutes : GEMV q4b en boucle (carte.exe thermique) et relevé nvidia-smi chaque
seconde (température, horloges, puissance, raisons de bridage). On n'arrête que les processus que
l'on a lancés soi-même (la machine est partagée).

Usage : python -I -X utf8 outils/banc/pilote_thermique.py --exe CHEMIN/carte.exe --dossier JOURNAUX [--duree 300]
"""
import argparse
import subprocess

ap = argparse.ArgumentParser()
ap.add_argument("--exe", required=True)
ap.add_argument("--dossier", required=True)
ap.add_argument("--duree", default="300")
a = ap.parse_args()
champs = "timestamp,temperature.gpu,clocks.sm,clocks.mem,power.draw,utilization.gpu,pstate,clocks_throttle_reasons.active,pcie.link.gen.current"
with open(f"{a.dossier}/thermique-nvsmi.csv", "w", encoding="utf-8") as f_nv, open(f"{a.dossier}/thermique.log", "w", encoding="utf-8") as f_log:
    nv = subprocess.Popen(["nvidia-smi", f"--query-gpu={champs}", "--format=csv,noheader", "-l", "1"], stdout=f_nv)
    try:
        subprocess.run([a.exe, "thermique", "--api", "vulkan", "--format", "q4b", "--duree", a.duree], stdout=f_log, stderr=subprocess.STDOUT)
    finally:
        nv.terminate()
        nv.wait(10)
print("fini")
