"""Contre-juge : refait les tables engendrées des annexes B et C par un autre chemin (git show, git ls-tree)."""
import re
import subprocess
import sys

depot = sys.argv[1]
BS = "\\"


def git(*a):
    return subprocess.run(["git", "-C", depot, *a], capture_output=True, check=True).stdout


tex = open(f"{depot}/memoire/tome3/annexes/outils-tome3.tex", encoding="utf-8").read()
rangs = re.findall(r"^\\fichier\{([^}]*)\} & .*& \\num\{(\d+)\} \\\\$", tex, re.M)
ecarts = 0
total = 0
for chemin, n in rangs:
    chemin = chemin.replace(BS + "_", "_")
    contenu = git("show", f"HEAD:{chemin}").decode("utf-8", "replace")
    k = len(contenu.splitlines())
    total += k
    if k != int(n):
        ecarts += 1
        print("écart lignes", chemin, n, k)
m = re.search(r"\\EF\{Total\}\{Total\} & \\EF\{(\d+) tools\}.*\\num\{(\d+)\}", tex)
print(f"annexe B : {len(rangs)} outils (table : {m.group(1)}), {total} lignes refaites (table : {m.group(2)}), "
      f"{ecarts} écart")

arbre = {}
for e in git("ls-tree", "-r", "-l", "-z", "HEAD").split(b"\0"):
    if e:
        meta, c = e.split(b"\t", 1)
        arbre[c.decode()] = int(meta.split()[3])
tj = open(f"{depot}/memoire/tome3/annexes/journaux-tome3.tex", encoding="utf-8").read()
rj = re.findall(r"^\\fichier\{([^}]*)\} & \\num\{(\d+)\} & \\num\{([\d.]+)\} \\\\$", tj, re.M)
SRC = (".py", ".rs", ".sh", ".ps1", ".js", ".cu", ".cuh", ".tex")
tn = 0
to = 0
ej = 0
for d, n, mo in rj:
    d = d.replace(BS + "_", "_")
    prof = d.count("/")  # 3 : fichiers directs du dossier ; 4 : tout le sous-arbre
    fs = [c for c in arbre if c.startswith(d) and "__pycache__" not in c
          and ((prof == 3 and c.count("/") == 3) or (prof == 4 and c.count("/") >= 4))]
    # Hors du tome, comme l'annexe C le dit (R6) : le second tirage de P3, en travail ailleurs.
    hors_r6 = [c for c in fs if "/P3/07" in c or "p3_second_tirage" in c or "second-tirage/" in c]
    if hors_r6:
        print("hors du tome (R6) :", ", ".join(hors_r6))
    fs_sans = [c for c in fs if not c.endswith(SRC[:-1]) and c not in hors_r6]
    o = sum(arbre[c] for c in fs_sans)
    tn += len(fs_sans)
    to += o
    if len(fs_sans) != int(n) or f"{o / 1e6:.2f}" != mo:
        ej += 1
        print("écart journaux", d, n, mo, len(fs_sans), f"{o / 1e6:.3f}")
mt = re.search(r"\\EF\{Total\}\{Total\} & \\num\{(\d+)\} & \\num\{([\d.]+)\}", tj)
print(f"annexe C : {len(rj)} dossiers, {tn} fichiers (table : {mt.group(1)}), {to / 1e6:.2f} Mo "
      f"(table : {mt.group(2)}), {ej} écart")
