"""Courbe dense du succès du cache global (LRU et Belady) contre le nombre d'emplacements, sur les
traces réelles de gpt-oss-20b, par `rejouer` (trc-cache) : la figure de la falaise du LRU
(lemme 3 de moteur/O-pour-le-memoire.md : 0 succès exactement pour N ≤ (L − 1)·k = 92).

Données : mesures/localite-gpt-oss/traces-20b/traces-20b.tar.xz (concaténations « tous.lecture » et
« tous.generation » de gptoss_localite.py, préfixe t20b, ordre trié). N = 4, 8, …, 320, plus 92, 93,
95, 96, 97 autour de la falaise. Aucun seuil : c'est une courbe publiée, ses points sont déjà jugés
par le témoin O1 aux budgets de l'outil gpt-oss.

Usage : python -I -X utf8 mesures/moteur/O/courbe_dense.py --rejouer <rejouer.exe> --csv <sortie.csv>
"""
import argparse
import json
import os
import subprocess
import sys
import tarfile
import tempfile

ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.normpath(os.path.join(ICI, "..", "..", ".."))
ARCHIVE = os.path.join(DEPOT, "mesures", "localite-gpt-oss", "traces-20b", "traces-20b.tar.xz")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rejouer", required=True)
    ap.add_argument("--csv", required=True)
    a = ap.parse_args()
    textes = {}
    with tarfile.open(ARCHIVE, "r:xz") as tar:
        for m in tar.getmembers():
            nom = os.path.basename(m.name)
            if m.isfile() and nom.startswith("t20b.") and nom.endswith(".trace"):
                textes[nom] = tar.extractfile(m).read().decode("utf-8")
    Ns = sorted(set(list(range(4, 321, 4)) + [92, 93, 95, 97]))
    lignes = ["trace,emplacements,acces,succes_lru,succes_belady,h_lru,h_belady"]
    with tempfile.TemporaryDirectory(prefix="courbe-o1-") as tmp:
        for mode in ("lecture", "generation"):
            corps, E = [], None
            for nom in sorted(n for n in textes if n.endswith(f".{mode}.trace")):
                for l in textes[nom].splitlines():
                    if l.startswith("E="):
                        E = l
                    elif l.strip() and not l.startswith("#"):
                        corps.append(l)
            chemin = os.path.join(tmp, f"tous.{mode}.trace")
            with open(chemin, "w", encoding="utf-8", newline="\n") as f:
                f.write(f"# t20b, concaténation des traces {mode}\n{E}\n" + "\n".join(corps) + "\n")
            res = {}
            for pol in ("lru", "belady"):
                r = subprocess.run([a.rejouer, "--trace", chemin, "--emplacements", ",".join(map(str, Ns)),
                                    "--politique", pol], capture_output=True, text=True, check=True)
                res[pol] = json.loads(r.stdout)["resultats"]
            for rl, rb in zip(res["lru"], res["belady"]):
                n, acc = rl["emplacements"], rl["acces"]
                lignes.append(f"t20b.tous.{mode},{n},{acc},{rl['succes_vram']},{rb['succes_vram']},"
                              f"{rl['succes_vram'] / acc:.6f},{rb['succes_vram'] / acc:.6f}")
    with open(a.csv, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lignes) + "\n")
    print("\n".join(l for l in lignes if any(f",{x}," in l for x in (88, 92, 93, 96, 100))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
