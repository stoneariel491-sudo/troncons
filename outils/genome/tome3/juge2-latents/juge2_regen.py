"""Juge des chiffres du lot « espaces latents », second flux : la régénération au bit des données de figure.

Écrit pour troncons le 2026-10-27, rôle « juge indépendant des chiffres du lot latents après corrections ».

Ce que fait cet outil :
  1. Tire du commit jugé (326969f par défaut), par `git archive`, dans une racine de brouillon hors du dépôt :
     le script du lot (memoire/outils/tome3_latents.py) et ses seules entrées commitées
     (mesures/genome/tome3/latents/, le CSV du spectre du lot B, le JSON du juge du premier flux). Les
     données de figure commitées (memoire/figures/tome3/donnees/latents-*) vont dans une seconde racine,
     « reference », qui n'est jamais réécrite.
  2. Lance le script dans la racine de brouillon (il écrit sous sa propre racine : rien dans le dépôt).
  3. Compare, fichier par fichier, l'empreinte SHA-256 de chaque latents-* régénéré à celle du fichier
     commité ; liste les fichiers en trop ou manquants (les six retirés par le lot ne doivent pas revenir).
  4. Lance les deux cassures du lot (--casse-appui, --casse-bord) : le témoin visé doit tomber, et aucun
     fichier des données régénérées ne doit changer (une cassure écrit dans un dossier jetable ; le dossier
     temporaire est redirigé dans le brouillon par TMP/TEMP).
  5. Témoin du comparateur (--casser) : un octet inversé en mémoire dans chaque fichier régénéré ; chaque
     comparaison doit tomber.

  python -I -X utf8 juge2_regen.py <brouillon> [--casser] [--commit 326969f] > juge2-regen.json
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tarfile

DEPOT = pathlib.Path("~/dev/active/troncons")
ENTREES = [
    "memoire/outils/tome3_latents.py",
    "mesures/genome/tome3/latents",
    "mesures/genome/construction/synonyme/figures/spectre-L08-E00-gate.csv",
    "outils/genome/tome3/juge-latents/juge-etats-marges.json",
]
DONNEES = "memoire/figures/tome3/donnees"


def extraire(commit: str, chemins: list[str], dest: pathlib.Path) -> None:
    # core.autocrlf=false : sinon `git archive` rend les fins de ligne CRLF de la copie de travail de Windows,
    # et ni la référence ni les entrées ne sont plus les octets du commit.
    tar = subprocess.run(["git", "-C", str(DEPOT), "-c", "core.autocrlf=false", "-c", "core.eol=lf",
                          "archive", "--format=tar", commit, "--", *chemins],
                         check=True, capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(tar)) as t:
        t.extractall(dest, filter="data")


def empreintes(dossier: pathlib.Path, casser: bool = False) -> dict[str, str]:
    out = {}
    for p in sorted(dossier.glob("latents-*")):
        b = bytearray(p.read_bytes())
        if casser and b:
            b[len(b) // 2] ^= 0x01          # un bit inversé, en mémoire seulement
        out[p.name] = hashlib.sha256(bytes(b)).hexdigest()
    return out


def lancer(racine: pathlib.Path, tmp: pathlib.Path, *args: str) -> tuple[int, str]:
    env = dict(os.environ, TMP=str(tmp), TEMP=str(tmp), TMPDIR=str(tmp), OPENBLAS_NUM_THREADS="1",
               OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(racine / "memoire/outils/tome3_latents.py"), *args],
                       capture_output=True, text=True, encoding="utf-8", env=env, cwd=str(racine))
    return r.returncode, r.stdout + r.stderr


def temoins_imprimes(sortie: str) -> dict:
    """Le script imprime le JSON de ses témoins, puis une ligne « témoins : … »."""
    debut = sortie.index("{")
    fin = sortie.index("\ntémoins :")
    return json.loads(sortie[debut:fin])


def main() -> int:
    args = [a for a in sys.argv[1:]]
    casser = "--casser" in args
    commit = "326969f"
    if "--commit" in args:
        commit = args[args.index("--commit") + 1]
    brouillon = pathlib.Path([a for a in args if not a.startswith("--") and a != commit][0]).resolve()
    if DEPOT.resolve() in brouillon.parents or brouillon == DEPOT.resolve():
        raise SystemExit("le brouillon doit être hors du dépôt")
    racine, ref, tmp = brouillon / "racine", brouillon / "reference", brouillon / "tmp"
    for d in (racine, ref, tmp):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    extraire(commit, ENTREES, racine)
    extraire(commit, [DONNEES], ref)
    (racine / DONNEES).mkdir(parents=True, exist_ok=True)
    rc, sortie = lancer(racine, tmp)
    regen = empreintes(racine / DONNEES, casser)
    refe = empreintes(ref / DONNEES)
    comparaisons = {}
    for nom in sorted(set(regen) | set(refe)):
        if nom not in regen:
            comparaisons[nom] = "manquant dans la régénération"
        elif nom not in refe:
            comparaisons[nom] = "en trop (absent du commit)"
        else:
            comparaisons[nom] = "égal au bit" if regen[nom] == refe[nom] else "DIFFÉRENT"
    egaux = sum(v == "égal au bit" for v in comparaisons.values())
    res = {
        "outil": "outils/genome/tome3/juge2-latents/juge2_regen.py",
        "commit": commit,
        "casser_comparateur": casser,
        "script_code_retour": rc,
        "fichiers_commit": len(refe),
        "fichiers_regeneres": len(regen),
        "egaux_au_bit": egaux,
        "comparaisons": comparaisons,
        "empreintes_reference": refe,
    }
    if not casser:
        avant = empreintes(racine / DONNEES)
        cassures = {}
        for drapeau, cle in (("--casse-appui", "A1_appui"), ("--casse-bord", "B1_bord_tsne")):
            rc2, s2 = lancer(racine, tmp, drapeau)
            t = temoins_imprimes(s2)
            cassures[drapeau] = {"code_retour": rc2, "temoin": cle, "tient": t[cle]["tient"],
                                 "ecart": t[cle].get("ecart_max", t[cle].get("ecart_relatif_max")),
                                 "autres_tiennent": {k: v["tient"] for k, v in t.items() if k != cle}}
        apres = empreintes(racine / DONNEES)
        res["cassures"] = cassures
        res["cassures_tombent"] = all(not c["tient"] for c in cassures.values())
        res["donnees_intactes_apres_cassures"] = avant == apres
        jetables = sorted(p.name for p in tmp.iterdir())
        res["dossiers_jetables_des_cassures"] = jetables
        res["verdict"] = ("tient" if egaux == len(refe) == len(regen) and rc == 0 and res["cassures_tombent"]
                          and res["donnees_intactes_apres_cassures"] else "TOMBE")
    else:
        res["verdict_comparateur"] = ("le comparateur tombe sur chaque fichier" if egaux == 0 and len(regen) == len(refe)
                                      else "LE COMPARATEUR NE TOMBE PAS")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
