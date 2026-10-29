# Juge de la rédaction du Tome III (français) : assemble le tome à juger dans un dossier d'essai.
#
# Le maître memoire/tome3/fr/troncons-tome3-fr.tex se compile deux niveaux sous memoire/ (\Racine = ../..,
# \Depot = ../../..). Le dossier d'essai memoire/essai/juge-redaction-fr-<état>/ est à la même profondeur :
# le maître, le résumé, les chapitres et les annexes y sont recopiés tels quels, sans un octet changé, et
# tout le reste (préambule, figures, bibliographie, données) se lit dans le dépôt par les mêmes chemins.
#
# Deux états :
#   tete       : chaque fichier tel qu'il est commité (git show HEAD:chemin) ;
#   brouillon  : HEAD, sauf les chapitres passés par --remplacer chapitre=chemin (les brouillons non
#                commités du rédacteur A : 02 et 03 dans l'arbre de travail, 04 et 05 dans son brouillon).
# Le manifeste (manifeste.json) donne, pour chaque fichier recopié, sa provenance et son SHA-256 : le
# jugement porte sur ces octets-là, et seulement sur eux.
#
# Usage : python -I -X utf8 assembler.py --etat brouillon --remplacer 04-duplication=/chemin/04.tex ...
import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

DEPOT = pathlib.Path(__file__).resolve().parents[4]
FR = "memoire/tome3/fr"
CHAPITRES = ["00-introduction", "01-question", "02-eclaireur", "03-genome", "04-duplication",
             "05-predictif", "06-mimetisme", "07-synthese", "08-codon", "09-synonyme", "10-juge",
             "11-tropicale", "12-spectres", "13-discussion"]
ANNEXES = ["A-protocoles", "B-outils", "C-journaux"]


def git_show(chemin: str) -> bytes:
    return subprocess.run(["git", "-C", str(DEPOT), "show", f"HEAD:{chemin}"],
                          check=True, capture_output=True).stdout


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--etat", choices=["tete", "brouillon"], required=True)
    p.add_argument("--remplacer", action="append", default=[],
                   help="chapitre=chemin (état brouillon seulement)")
    a = p.parse_args()
    remplace = {}
    for r in a.remplacer:
        c, _, chemin = r.partition("=")
        if c not in CHAPITRES or not chemin:
            print(f"remplacement invalide : {r}", file=sys.stderr)
            return 2
        remplace[c] = pathlib.Path(chemin)
    if a.etat == "tete" and remplace:
        print("l'état tete ne prend aucun remplacement", file=sys.stderr)
        return 2
    sortie = DEPOT / "memoire" / "essai" / f"juge-redaction-fr-{a.etat}"
    (sortie / "chapitres").mkdir(parents=True, exist_ok=True)
    (sortie / "annexes").mkdir(parents=True, exist_ok=True)
    tete = subprocess.run(["git", "-C", str(DEPOT), "rev-parse", "HEAD"], check=True,
                          capture_output=True, text=True).stdout.strip()
    manifeste = {"etat": a.etat, "HEAD": tete, "fichiers": []}
    fichiers = [("troncons-tome3-fr.tex", f"{FR}/troncons-tome3-fr.tex"),
                ("resume.tex", f"{FR}/resume.tex")]
    fichiers += [(f"chapitres/{c}.tex", f"{FR}/chapitres/{c}.tex") for c in CHAPITRES]
    fichiers += [(f"annexes/{x}.tex", f"{FR}/annexes/{x}.tex") for x in ANNEXES]
    for dest, chemin in fichiers:
        nom = pathlib.Path(dest).stem
        if nom in remplace:
            octets = remplace[nom].read_bytes()
            prov = str(remplace[nom])
        else:
            octets = git_show(chemin)
            prov = f"HEAD:{chemin}"
        (sortie / dest).write_bytes(octets)
        manifeste["fichiers"].append({"fichier": dest, "provenance": prov,
                                      "sha256": hashlib.sha256(octets).hexdigest(),
                                      "octets": len(octets)})
    (sortie / "manifeste.json").write_text(json.dumps(manifeste, ensure_ascii=False, indent=1),
                                           encoding="utf-8")
    for f in manifeste["fichiers"]:
        print(f"{f['sha256'][:12]}  {f['octets']:>7}  {f['fichier']:<32} {f['provenance']}")
    print(f"-> {sortie}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
