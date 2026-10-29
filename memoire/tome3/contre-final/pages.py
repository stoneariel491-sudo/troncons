"""Contre-juge : compare deux PDF page à page (rendu pdftoppm à 72 ppp, empreinte SHA-256 ; texte par pdftotext).

Usage : python -I -X utf8 pages.py A.pdf B.pdf [--casser]
Témoin : un PDF contre lui-même donne 0 page différente. Cassure (--casser) : l'empreinte de la première page de B
est remplacée par celle de la dernière, et l'outil doit alors compter au moins une page différente (code 1 sinon).
Les rendus sont gardés dans un cache à côté de l'outil, nommé d'après l'empreinte du PDF.
"""
import hashlib
import subprocess
import sys
from pathlib import Path

CACHE = Path(__file__).resolve().parent / "cache-pages"


def pages(pdf):
    sortie = subprocess.run(["pdfinfo", pdf], capture_output=True, check=True).stdout.decode("utf-8", "replace")
    return int(next(l.split()[-1] for l in sortie.splitlines() if l.startswith("Pages:")))


def empreintes(pdf):
    cle = hashlib.sha256(Path(pdf).read_bytes()).hexdigest()[:16]
    dossier = CACHE / cle
    if not (dossier / "fini").exists():
        dossier.mkdir(parents=True, exist_ok=True)
        subprocess.run(["pdftoppm", "-r", "72", "-png", pdf, str(dossier / "p")], check=True)
        (dossier / "fini").write_text("1")
    fichiers = sorted(dossier.glob("p-*.png"), key=lambda p: int(p.stem.split("-")[1]))
    return [hashlib.sha256(f.read_bytes()).hexdigest() for f in fichiers]


def textes(pdf):
    t = subprocess.run(["pdftotext", "-enc", "UTF-8", "-layout", pdf, "-"], capture_output=True, check=True).stdout
    return t.decode("utf-8", errors="replace").split("\f")


def main():
    a, b = sys.argv[1], sys.argv[2]
    casser = "--casser" in sys.argv[3:]
    ea, eb = empreintes(a), list(empreintes(b))
    ta, tb = textes(a), textes(b)
    if casser:
        eb[0] = eb[-1]
    print(f"pages : {len(ea)} / {len(eb)} (pdfinfo {pages(a)} / {pages(b)})")
    diff = [i + 1 for i in range(min(len(ea), len(eb))) if ea[i] != eb[i]]
    dtexte = [i + 1 for i in range(min(len(ta), len(tb))) if ta[i] != tb[i]]
    print(f"pages au rendu différent : {len(diff)} {diff[:40]}")
    print(f"pages au texte différent : {len(dtexte)} {dtexte[:40]}")
    if casser and not diff:
        print("ÉCHEC : la cassure n'a pas fait tomber le témoin")
        sys.exit(1)


main()
