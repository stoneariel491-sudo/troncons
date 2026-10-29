# Juge final : le listing du fondu (chapitre 08) contre les sources Rust commitées, par mon propre extrait
# (git show main:..., lignes 67 à 77 et 317 à 327), ligne à ligne ; puis l'anglais contre le français.
# Usage : python -I -X utf8 listing.py <racine du dépôt> [--casser]
import pathlib
import re
import subprocess
import sys

D = pathlib.Path(sys.argv[1])
casser = "--casser" in sys.argv


def lignes(chemin, a, b):
    t = subprocess.run(["git", "-C", str(D), "show", f"main:{chemin}"], capture_output=True, check=True).stdout
    return t.decode("utf-8").split("\n")[a - 1:b]


src = lignes("moteur/crates/trc-format/src/lib.rs", 67, 77) + [""] + lignes("moteur/crates/trc-codec/src/lib.rs", 317, 327)
if casser:
    src[3] = src[3].replace("8", "9")
motif = re.compile(r"\\begin\{lstlisting\}\[[^\n]*\]\n(.*?)\\end\{lstlisting\}", re.S)
fr = motif.search((D / "memoire/tome3/fr/chapitres/08-codon.tex").read_text(encoding="utf-8")).group(1)
en = motif.search((D / "memoire/tome3/en/chapitres/08-codon.tex").read_text(encoding="utf-8")).group(1)
lf = fr.rstrip("\n").split("\n")
print(f"listing FR : {len(lf)} lignes ; extrait des sources : {len(src)} lignes")
ecarts = [(i + 1, a, b) for i, (a, b) in enumerate(zip(lf, src)) if a != b]
for e in ecarts:
    print("  écart ligne", e)
print("FR égal aux sources :", lf == src)
print("EN égal au FR :", en == fr)
sys.exit(0 if (lf == src and en == fr) else 1)
