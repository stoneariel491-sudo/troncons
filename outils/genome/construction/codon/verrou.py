"""Le verrou de la carte pour le lot A (codon) : prendre, rendre, état.

Protocole des autres lots (pilote_o4.py, r0_ecart.py) : ~/dev/verrou-carte.txt ; s'il
existe et a moins de 2 h, on attend ; on écrit son nom, l'heure et son pid ; on ne retire que son
propre verrou.

  python -I -X utf8 outils/genome/construction/codon/verrou.py prendre "<raison>"
  python -I -X utf8 outils/genome/construction/codon/verrou.py rendre
  python -I -X utf8 outils/genome/construction/codon/verrou.py etat
"""
import datetime as dt
import os
import pathlib
import sys
import time

VERROU = pathlib.Path("~/dev/verrou-carte.txt")
MARQUE = "lot A (codon)"


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "etat"
    if cmd == "etat":
        print(VERROU.read_text(encoding="utf-8", errors="replace").strip() if VERROU.exists() else "libre")
        return 0
    if cmd == "prendre":
        raison = sys.argv[2] if len(sys.argv) > 2 else ""
        while VERROU.exists() and MARQUE not in VERROU.read_text(encoding="utf-8", errors="replace") and time.time() - VERROU.stat().st_mtime < 2 * 3600:
            print(f"verrou tenu : {VERROU.read_text(encoding='utf-8', errors='replace').strip()!r} ; attente 60 s", flush=True)
            time.sleep(60)
        VERROU.write_text(f"{MARQUE}, {dt.datetime.now():%Y-%m-%d %H:%M:%S}, {raison}, pid {os.getpid()}\n", encoding="utf-8")
        print("pris")
        return 0
    if cmd == "rendre":
        if VERROU.exists() and MARQUE in VERROU.read_text(encoding="utf-8", errors="replace"):
            VERROU.unlink()
            print("rendu")
        else:
            print("pas à moi ou absent : rien fait")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
