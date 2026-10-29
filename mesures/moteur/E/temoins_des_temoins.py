"""Témoin des témoins de l'étape E1 (lot E) : chaque témoin de trc-cuda et de trc-es doit tomber
quand on force sa condition à faux, puis tenir une fois restauré (SOCLE, « Le niveau exigé »).

Pour chaque cassure nommée, le test qui porte le témoin est relancé seul avec TRC_E_CASSER=<nom> :
il doit échouer, et son message d'échec doit être celui du témoin visé (pas une autre panique).
Puis la suite entière est relancée sans cassure : tout doit tenir.

Usage : python -I -X utf8 mesures/moteur/E/temoins_des_temoins.py > mesures/moteur/E/journaux/e1-temoins/<date>-cassures.json
(cible : CARGO_TARGET_DIR=~/dev/cibles/troncons-E, posé ici.)
"""

import datetime
import json
import os
import subprocess
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.abspath(os.path.join(ICI, "..", "..", ".."))
MANIFESTE = os.path.join(DEPOT, "moteur", "Cargo.toml")

# nom de la cassure → (crate, fichier de test, test, fragment attendu dans le message d'échec)
CASSURES = {
    "aller_retour": ("trc-cuda", "carte", "aller_retour_et_cassure", "aller-retour de"),
    "ordre": ("trc-cuda", "carte", "evenements_et_ordre_entre_flux", "le noyau ordonné doit voir l'aller entier"),
    "module": ("trc-cuda", "carte", "module_lancement_et_memoire_projetee", "sortie du noyau"),
    "projetee": ("trc-cuda", "carte", "module_lancement_et_memoire_projetee", "mémoire projetée"),
    "lecture": ("trc-es", "lecture", "lectures_alignees_profondeur_et_file", "lecture 5"),
    "fin": ("trc-es", "lecture", "derniere_page_partielle_et_refus", "dernière page partielle"),
    "fils": ("trc-es", "lecture", "soumission_et_recolte_concurrentes", "assertion `left == right` failed"),
}


def cargo_test(args, casser=None):
    env = dict(os.environ)
    env["CARGO_TARGET_DIR"] = r"~\dev\cibles\troncons-E"
    env["CARGO_INCREMENTAL"] = "1"
    env.pop("TRC_E_CASSER", None)
    if casser:
        env["TRC_E_CASSER"] = casser
    r = subprocess.run(["cargo", "test", "--offline", "-j", "4", "--manifest-path", MANIFESTE] + args,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=1800)
    return r.returncode, r.stdout + r.stderr


def main():
    sortie = {"outil": "temoins_des_temoins.py", "debut": datetime.datetime.now().isoformat(timespec="seconds"),
              "commit": subprocess.run(["git", "-C", DEPOT, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
              "cassures": []}
    for nom, (crate, fichier, test, fragment) in CASSURES.items():
        code, texte = cargo_test(["-p", crate, "--test", fichier, test, "--", "--exact", "--test-threads=1"], casser=nom)
        message = [l for l in texte.splitlines() if "panicked at" in l or fragment in l]
        tombe = code != 0 and fragment in texte
        sortie["cassures"].append({"cassure": nom, "test": f"{crate}/{fichier}::{test}", "code": code,
                                   "fragment_attendu": fragment, "tombe": tombe, "extrait": message[:4]})
        print(f"{nom:13s} code {code} : {'TOMBE' if tombe else 'NE TOMBE PAS'}", file=sys.stderr, flush=True)
    code, texte = cargo_test(["-p", "trc-cuda", "-p", "trc-es", "--", "--test-threads=1"])
    resultats = [l for l in texte.splitlines() if l.startswith("test result:")]
    sortie["restauree"] = {"code": code, "resultats": resultats, "tient": code == 0}
    sortie["toutes_tombent"] = all(c["tombe"] for c in sortie["cassures"])
    sortie["fin"] = datetime.datetime.now().isoformat(timespec="seconds")
    print(json.dumps(sortie, ensure_ascii=False, indent=2))
    print(f"toutes tombent : {sortie['toutes_tombent']} ; restaurée tient : {sortie['restauree']['tient']}", file=sys.stderr)


if __name__ == "__main__":
    main()
