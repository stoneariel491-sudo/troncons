"""Le verrou de la carte pour le juge de la construction : prendre, rafraîchir, rendre, état.

Protocole commun des flux (pilotes des lots O, R, A, B, placement) : ~/dev/verrou-carte.txt ;
s'il existe et a moins de 2 h, on attend ; on écrit son nom, l'heure, la raison et son pid ; on ne retire
que son propre verrou. Le mot « vitesse » dans la raison met en pause les flux lents (pistes).

  python -I -X utf8 verrou_juge.py prendre "<raison>"
  python -I -X utf8 verrou_juge.py rafraichir "<raison>"
  python -I -X utf8 verrou_juge.py rendre
  python -I -X utf8 verrou_juge.py etat
"""
import datetime as dt
import os
import pathlib
import sys
import time

VERROU = pathlib.Path("~/dev/verrou-carte.txt")
MARQUE = "juge construction"


def a_moi() -> bool:
    return VERROU.exists() and MARQUE in VERROU.read_text(encoding="utf-8", errors="replace")


def prendre(raison: str, attendre=True) -> None:
    while VERROU.exists() and not a_moi() and time.time() - VERROU.stat().st_mtime < 2 * 3600:
        if not attendre:
            raise RuntimeError("verrou tenu : " + VERROU.read_text(encoding="utf-8", errors="replace").strip())
        print(f"verrou tenu : {VERROU.read_text(encoding='utf-8', errors='replace').strip()!r} ; attente 60 s", flush=True)
        time.sleep(60)
    VERROU.write_text(f"{MARQUE}, {dt.datetime.now():%Y-%m-%d %H:%M:%S}, {raison}, pid {os.getpid()}\n", encoding="utf-8")


def rendre() -> bool:
    if a_moi():
        VERROU.unlink()
        return True
    return False


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "etat"
    if cmd == "etat":
        print(VERROU.read_text(encoding="utf-8", errors="replace").strip() if VERROU.exists() else "libre")
    elif cmd in ("prendre", "rafraichir"):
        prendre(sys.argv[2] if len(sys.argv) > 2 else "")
        print("pris")
    elif cmd == "rendre":
        print("rendu" if rendre() else "pas à moi ou absent : rien fait")
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
