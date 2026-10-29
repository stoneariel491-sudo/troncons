"""P3, routeur biaisé en ligne : pilote du SECOND TIRAGE (autre texte que R1).

Déclaration : mesures/mimetisme/P3/07-second-tirage-declare.md (commitée avant toute passe).
Réutilise le pilote du premier tirage (p3_routeur_ligne.py : mêmes garde-fous, même moteur, même commande) en changeant seulement le
fichier de base (dix fenêtres neuves de wiki.test, base-juge-20b.kld), les dossiers de sortie, le seuil d'espace disque libre (5 Go en
passe, amendement 07b ; le départ exige 25 Go) et le texte attendu dans le verrou.

Usage (SANS -I, psutil est un paquet utilisateur) :
    python -X utf8 p3_second_tirage.py P0 B0.041 P0b B0.3
Le verrou de la carte est posé par l'appelant et doit contenir « P3 second tirage ».
"""
import pathlib
import shutil
import sys
import time

import psutil

ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import p3_routeur_ligne as P  # noqa: E402

DEPOT = ICI.parents[2]
P.SORTIE = DEPOT / "mesures/mimetisme/P3/second-tirage"
P.LOURDS = pathlib.Path("~/dev/essais/troncons/mimetisme/P3/second-tirage")
P.BASE = pathlib.Path("~/dev/essais/troncons/genome/juge/base-juge-20b.kld")
P.C_MIN = 5 * P.GO           # garde-fou pendant une passe (surveiller() lit P.C_MIN) ; 15 Go avant l'amendement 07b (2026-10-27)
DEPART_C_MIN = 25 * P.GO     # exigence au lancement de la séance (déclaration § 8), première passe
ENTRE_C_MIN = 18 * P.GO      # entre deux passes de la même séance (chacune écrit un .kld de 1 Go)
RAM_DEPART = 2.5 * P.GO      # attendre que la machine se libère avant de lancer une passe
ATTENTE_RAM_S = 30 * 60      # au plus 30 min d'attente, puis arrêt


def main(noms):
    bat = psutil.sensors_battery()
    if bat is not None and not bat.power_plugged:
        raise SystemExit("secteur débranché")
    if not P.VERROU.exists() or "P3 second tirage" not in P.VERROU.read_text(encoding="utf-8", errors="replace"):
        raise SystemExit("le verrou « P3 second tirage » doit être posé par l'appelant")
    for i, nom in enumerate(noms):
        libre = shutil.disk_usage("C:/").free
        seuil = DEPART_C_MIN if i == 0 else ENTRE_C_MIN
        if libre < seuil:
            raise SystemExit(f"C: libre {libre / P.GO:.1f} Go < {seuil / P.GO:.0f} Go avant {nom} : arrêt")
        t_attente = time.time()
        while psutil.virtual_memory().available < RAM_DEPART:
            if time.time() - t_attente > ATTENTE_RAM_S:
                raise SystemExit(f"RAM disponible < 2,5 Go depuis 30 min avant {nom} : arrêt")
            time.sleep(30)
        bat = psutil.sensors_battery()
        if bat is not None and not bat.power_plugged:
            raise SystemExit("secteur débranché")
        print(f"{nom} : C: libre {libre / P.GO:.1f} Go, RAM disponible {psutil.virtual_memory().available / P.GO:.2f} Go (attente {time.time() - t_attente:.0f} s), "
              f"swap {psutil.swap_memory().used / P.GO:.2f} Go", flush=True)
        res = P.passe(nom, 10)
        if res["code"] != 0 or res["arret"]:
            print("passe en échec ou arrêtée, séance interrompue :", res["arret"], flush=True)
            break


if __name__ == "__main__":
    main(sys.argv[1:])
