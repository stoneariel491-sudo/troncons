"""Juge du lot « espaces latents » : compare au bit les fichiers régénérés par les scripts du lot (dans une
racine de brouillon, jamais dans le dépôt) aux fichiers commités.

Écrit pour troncons le 2026-10-27. La racine de brouillon se prépare ainsi (rien du dépôt n'est
réécrit, les scripts du lot écrivent sous leur propre RACINE) :

  git archive <commit> outils/03-entropie outils/genome/tome3 memoire/outils/tome3_latents.py \\
      mesures/genome/construction/synonyme/figures | tar -x -C <brouillon>/racine
  cd <brouillon>/racine
  python -I -X utf8 outils/genome/tome3/latents_rangee.py
  python -I -X utf8 outils/genome/tome3/latents_nuage.py
  python -I -X utf8 outils/genome/tome3/latents_etats.py      # environ 22 min, un fil
  python -I -X utf8 memoire/outils/tome3_latents.py           # depuis les mesures régénérées

Puis : python -I -X utf8 juge_regen.py <brouillon>/racine [--casser]  (JSON sur la sortie standard).
--casser : témoin du comparateur, le dernier octet de chaque fichier régénéré est inversé en mémoire et
un champ de chaque JSON changé ; toutes les comparaisons doivent tomber.
CSV et .tex : égalité octet par octet (SHA-256). JSON : égalité de tous les champs sauf `duree_s`
(et sauf les champs qui nomment un chemin absolu de la racine, s'il y en a).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

DEPOT = "~/dev/active/troncons"
MES = "mesures/genome/tome3/latents"
DON = "memoire/figures/tome3/donnees"
OCTETS = [f"{MES}/{f}" for f in ("etats-c23.csv", "rangee-L08-E00-gate.csv", "nuage-L08-E00-gate-points.csv",
                                 "nuage-L08-E00-gate-ellipses.csv")]
OCTETS += [f"{DON}/{f}" for f in ("latents-chiffres.tex", "latents-etats-acp.csv", "latents-etats-tsne.csv",
                                  "latents-rangee.csv", "latents-rangee-change.csv", "latents-rangee-garde.csv",
                                  "latents-rangee-niveaux.csv", "latents-nuage-12.csv", "latents-nuage-13.csv",
                                  "latents-ellipse-frontiere-12.csv", "latents-ellipse-frontiere-13.csv",
                                  "latents-ellipse-synonyme-12.csv", "latents-ellipse-synonyme-13.csv")]
JSONS = [f"{MES}/{f}" for f in ("etats-c23.json", "rangee-L08-E00-gate.json", "nuage-L08-E00-gate.json")]


def empreinte(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def sans_duree(x):
    if isinstance(x, dict):
        return {k: sans_duree(v) for k, v in x.items() if k != "duree_s"}
    if isinstance(x, list):
        return [sans_duree(v) for v in x]
    return x


def differences(a, b, chemin=""):
    if type(a) is not type(b):
        return [f"{chemin} : types {type(a).__name__} / {type(b).__name__}"]
    if isinstance(a, dict):
        d = []
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                d.append(f"{chemin}/{k} : absent d'un côté")
            else:
                d += differences(a[k], b[k], f"{chemin}/{k}")
        return d
    if isinstance(a, list):
        if len(a) != len(b):
            return [f"{chemin} : longueurs {len(a)} / {len(b)}"]
        d = []
        for i, (u, v) in enumerate(zip(a, b)):
            d += differences(u, v, f"{chemin}[{i}]")
        return d
    return [] if a == b else [f"{chemin} : {a!r} / {b!r}"]


def main():
    racine = sys.argv[1]
    casser = "--casser" in sys.argv[2:]
    out = {"outil": "outils/genome/tome3/juge-latents/juge_regen.py", "racine_regeneree": "brouillon (hors dépôt)",
           "casser": casser, "octets": {}, "json": {}}
    for f in OCTETS:
        a, b = os.path.join(DEPOT, f), os.path.join(racine, f)
        if not os.path.exists(b):
            out["octets"][f] = "non régénéré"
            continue
        ea, eb = empreinte(a), empreinte(b)
        if casser:
            # témoin du comparateur : le dernier octet du fichier régénéré inversé en mémoire (rien n'est
            # écrit) ; chaque comparaison doit tomber
            with open(b, "rb") as fb:
                o = bytearray(fb.read())
            o[-1] ^= 1
            eb = hashlib.sha256(bytes(o)).hexdigest()
        out["octets"][f] = {"egal_au_bit": ea == eb, "sha256_commite": ea, "sha256_regenere": eb}
    for f in JSONS:
        a, b = os.path.join(DEPOT, f), os.path.join(racine, f)
        if not os.path.exists(b):
            out["json"][f] = "non régénéré"
            continue
        ja = sans_duree(json.load(open(a, encoding="utf-8")))
        jb = sans_duree(json.load(open(b, encoding="utf-8")))
        if casser:
            jb["graine"] = jb.get("graine", 0) + 1     # témoin : un champ changé doit être vu
        d = differences(ja, jb)
        out["json"][f] = {"egal_hors_duree": not d, "differences": d}
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
