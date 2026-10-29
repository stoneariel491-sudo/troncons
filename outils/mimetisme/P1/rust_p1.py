"""P1, second chemin : noyau-p1 (Rust, copie de noyau-cache du rôle physique avec deux changements dits
dans son en-tête) rejoue les politiques de cache_p1.py sur les MÊMES traces et capacités.

Rôles :
  - LRU et LFU(h) : second chemin du chiffre principal, comparé jeton par jeton et au total à 1e-4 ;
  - mélange M(w) : calculé ici (le Python vectorisé coûte plus d'une minute par trace de lecture),
    rangé dans hits-<modèle>-rust.npz, validé par le témoin W3 (M(0) = LFU(8), M(1) = LFU(128)) et par
    un contrôle croisé Python sur gen-prose-en (cache_p1.melange).
Les poids de mélange du Rust sont factices (0,25). Chaîne : fichier concaténé lecture + génération.
Usage : python -I -X utf8 rust_p1.py <modèle> <cap,cap,...>
"""

import json
import math
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cache_p1 as cp  # noqa: E402

EXE = "~/dev/mimetisme-P1-donnees/cible-p1/release/noyau-p1.exe"
TMP = "~/dev/mimetisme-P1-donnees/rust-tmp"


def lignes_donnees(chemin):
    return [l.rstrip("\n") for l in open(chemin, encoding="utf-8") if l.strip() and not l.startswith("#") and not l.startswith("E=")]


def ecrire_trace(nom, fichiers, E):
    L = []
    for f in fichiers:
        L += lignes_donnees(f)
    chemin = f"{TMP}/{nom}.trace"
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(f"E={E}\n" + "\n".join(L) + "\n")
    with open(f"{TMP}/{nom}.poids", "w", encoding="utf-8") as f:
        f.write("\n".join(" | ".join("0.25 0.25 0.25 0.25" for _ in range(len(l.split("|")))) for l in L) + "\n")
    return chemin, f"{TMP}/{nom}.poids"


def noyaux():
    ln2 = math.log(2)
    k = {"lru": "1.0:1e-6"}
    for h in cp.H_GRILLE:
        k["lfu-" + ("inf" if math.isinf(h) else str(h))] = "1.0:1e30" if math.isinf(h) else f"1.0:{h / ln2}"
    for w in cp.W_GRILLE:
        k[f"mix-{w}"] = f"{(1 - w) * ln2 / cp.H_RAPIDE}:{cp.H_RAPIDE / ln2},{w * ln2 / cp.H_LENTE}:{cp.H_LENTE / ln2}"
    k["lfu-8bis"] = f"1.0:{8 / ln2}"  # redondant, inutile : retiré ci-dessous
    del k["lfu-8bis"]
    return k


def lancer(nom, fichiers, E, cap):
    t, p = ecrire_trace(nom, fichiers, E)
    noy = f"{TMP}/noyaux.txt"
    hd = f"{TMP}/hits-{nom}-{cap}"
    os.makedirs(hd, exist_ok=True)
    with open(noy, "w", encoding="utf-8") as f:
        for k, v in noyaux().items():
            f.write(f"{k}\t{v}\n")
    env = dict(os.environ, HITS_DIR=hd)
    subprocess.run([EXE, t, p, str(cap), noy, f"{TMP}/sortie-{nom}.jsonl"], check=True, env=env)
    return {k: np.loadtxt(f"{hd}/{k}.hits", dtype=np.int32) for k in noyaux()}


def main():
    m = sys.argv[1]
    caps = [int(x) for x in sys.argv[2].split(",")]
    os.makedirs(TMP, exist_ok=True)
    d = cp.dossier_modele(m)
    chemin = f"{cp.SORTIE}/hits-{m}-rust.npz"
    out = {}
    if os.path.exists(chemin):
        z = np.load(chemin)
        out = {k: z[k] for k in z.files}
    for g in cp.GENRES[m]:
        lec = f"{d}/{cp.prefixe(m, g)}.lecture.trace"
        E = cp.lire(m, g, "lecture")[1]
        traces = [(f"lecture-{g}", [lec])]
        if g in cp.GEN_DISPO[m]:
            gen = f"{d}/{cp.prefixe(m, g)}.generation.trace"
            traces += [(f"gen-{g}", [gen]), (f"chaine-{g}", [lec, gen])]
        for nom, fichiers in traces:
            for cap in caps:
                r = lancer(nom, fichiers, E, cap)
                for k, h in r.items():
                    out[cp.cle(m, nom, cap, k.replace("lfu-", "lfu:").replace("mix-", "mix:"))] = h
                print(nom, cap, "ok", flush=True)
        np.savez_compressed(chemin, **out)


def comparer(m):
    """Compare, jeton par jeton, les succès de cache_p1.py (lru, lfu) à ceux de noyau-p1."""
    py = np.load(f"{cp.SORTIE}/hits-{m}.npz")
    ru = np.load(f"{cp.SORTIE}/hits-{m}-rust.npz")
    L, K = (36, 4) if m == "120b" else (24, 4)
    lignes, pire, nd_tot, n_tot = [], 0.0, 0, 0
    for k in sorted(set(py.files) & set(ru.files)):
        if "__lru" not in k and "__lfu-" not in k:
            continue
        a, b = py[k], ru[k]
        e = abs(float(a.sum() - b.sum())) / (len(a) * L * K)
        nd = int((a != b).sum())
        pire, nd_tot, n_tot = max(pire, e), nd_tot + nd, n_tot + len(a)
        lignes.append({"cle": k, "succes_python": float(a.sum() / (len(a) * L * K)), "succes_rust": float(b.sum() / (len(a) * L * K)), "ecart": e, "jetons_differents": nd})
    json.dump({"modele": m, "pire_ecart_succes": pire, "jetons_differents": nd_tot, "jetons_compares": n_tot, "n_series": len(lignes), "lignes": lignes},
              open(f"{cp.SORTIE}/rust-{m}.json", "w", encoding="utf-8"), indent=1)
    print(m, "séries", len(lignes), "pire écart de succès", pire, "jetons différents", nd_tot, "sur", n_tot)


if __name__ == "__main__":
    cp.baisser_priorite()
    if sys.argv[1] == "comparer":
        comparer(sys.argv[2])
    else:
        main()
