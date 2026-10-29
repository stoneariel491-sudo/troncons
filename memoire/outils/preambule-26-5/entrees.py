"""Quelles entrées d'une construction (fichier .fls) ont changé dans git depuis le commit du PDF commité ?
Usage : python -I -X utf8 entrees.py <fichier.fls> <dossier de compilation> <chemin du PDF commité>"""
import os
import pathlib
import subprocess
import sys

R = pathlib.Path("~/dev/active/troncons").resolve()
fls, dossier, pdf = sys.argv[1], pathlib.Path(sys.argv[2]), sys.argv[3]


def git(*a):
    return subprocess.run(["git", "-C", str(R), *a], capture_output=True, text=True, encoding="utf-8").stdout


base = git("log", "-1", "--format=%H", "--", pdf).strip()
entrees = set()
for ligne in pathlib.Path(fls).read_text(encoding="utf-8", errors="replace").splitlines():
    if not ligne.startswith("INPUT "):
        continue
    p = pathlib.Path(ligne[6:].strip())
    if not p.is_absolute():
        p = dossier / p
    try:
        rel = pathlib.Path(os.path.normpath(p)).resolve().relative_to(R)
    except ValueError:
        continue  # hors du dépôt (MiKTeX)
    if "essai" in rel.parts:
        continue
    entrees.add(rel.as_posix())
print(f"base {base[:7]} ({git('log', '-1', '--format=%ad', '--date=iso', base).strip()}), {len(entrees)} entrées du dépôt")
changees = git("diff", "--name-only", base, "HEAD", "--", *sorted(entrees)).split()
sales = git("diff", "--name-only", "--", *sorted(entrees)).split()
for f in changees:
    n = git("log", "--oneline", f"{base}..HEAD", "--", f).splitlines()
    print(f"  changé : {f} ({len(n)} commit(s) ; dernier : {n[0][:110] if n else '?'})")
for f in sales:
    print(f"  non commité dans l'arbre : {f}")
