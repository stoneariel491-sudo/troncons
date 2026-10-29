"""Cassures des témoins unitaires de trc-cache : chaque témoin qui peut tomber est forcé à faux une
fois (SOCLE, « le niveau exigé »), dans une copie jetable de la crate, et l'on vérifie qu'il tombe,
lui, et que la copie restaurée tient.

Chaque cassure : (nom, fichier, texte d'origine, texte faussé, témoins qui DOIVENT tomber). Le texte
d'origine doit apparaître exactement une fois (sinon la cassure est refusée, pas devinée).
Verdict d'une cassure : « tombe comme prévu » si tous les témoins attendus échouent ; les autres
témoins qui tombent en plus sont notés (pas une faute : une même règle peut porter plusieurs
témoins).

Usage : python -I -X utf8 mesures/moteur/O/casser_tests.py --sortie mesures/moteur/O/journaux/tests-casses.txt
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.normpath(os.path.join(ICI, "..", "..", ".."))
CRATE = os.path.join(DEPOT, "moteur", "crates", "trc-cache")
CIBLE = r"~\dev\cibles\troncons-O-casse"

CASSURES = [
    ("épinglage retiré (la victime VRAM peut être un expert de la couche en cours)",
     "src/lib.rs", "            epingles.contains(&id)\n                || ou_vram",
     "            false\n                || ou_vram",
     ["tests::epinglage_tient_les_k_experts_ensemble"]),
    ("emplacement en vol évinçable",
     "src/lib.rs", "matches!(etats[s as usize], Etat::EnVol { .. })", "false",
     ["tests::en_vol_jamais_evince"]),
    ("étage RAM aveugle aux succès VRAM (règle 2 rompue)",
     "src/lib.rs",
     "                if self.ou_ram.contains_key(&id) {\n                    self.ram.acceder(id, t);\n                }\n",
     "",
     ["tests::deux_etages_egalent_deux_caches_a_pile"]),
    ("LRU qui ne remonte pas un succès (devient FIFO)",
     "src/politiques.rs", "        if i != self.queue {", "        if false {",
     ["tests::lru_ordre_et_victime"]),
    ("LRU qui évince le plus récent (devient MRU)",
     "src/politiques.rs",
     "        let mut i = self.tete;\n        while i != NUL {\n            let n = self.noeuds[i as usize];\n"
     "            if !epingle(n.id) {\n                return Some(n.id);\n            }\n            i = n.suiv;",
     "        let mut i = self.queue;\n        while i != NUL {\n            let n = self.noeuds[i as usize];\n"
     "            if !epingle(n.id) {\n                return Some(n.id);\n            }\n            i = n.prec;",
     ["tests::falaise_du_lru_global", "tests::lru_ordre_et_victime"]),
    ("première version de Belady (commit 4965dd4 : prochain usage cherché depuis l'instant du groupe "
     "précédent, le défaut que le témoin O1 a trouvé)",
     "src/politiques.rs", None, "git:4965dd4:moteur/crates/trc-cache/src/politiques.rs",
     ["tests::belady_cas_calcule_a_la_main"]),
    ("Belady qui évince le plus PROCHE (anti-optimum)",
     "src/politiques.rs", "if p > bp || (p == bp && id < bid)", "if p < bp || (p == bp && id < bid)",
     ["tests::belady_jamais_sous_lru", "tests::belady_cas_calcule_a_la_main"]),
    ("trace : nombre d'experts par couche non vérifié",
     "src/trace.rs", "                } else if n_couche != k {", "                } else if false {",
     ["tests::trace_mal_formee_refusee"]),
    ("octets : un défaut RAM compté comme lu du disque",
     "src/lib.rs", "                self.compteurs.succes_ram += 1;\n",
     "                self.compteurs.succes_ram += 1;\n                self.compteurs.octets_disque += octets;\n",
     ["tests::octets_comptes_par_etage"]),
]


def lancer(dossier):
    env = dict(os.environ, CARGO_TARGET_DIR=CIBLE, CARGO_INCREMENTAL="1")
    r = subprocess.run(["cargo", "test", "--offline", "-j", "4", "-p", "trc-cache", "--lib"], cwd=dossier,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    tombes = sorted(set(re.findall(r"^test (\S+)(?: - should panic)? \.\.\. FAILED", r.stdout, re.M)))
    passes = re.search(r"test result: \w+\. (\d+) passed; (\d+) failed", r.stdout)
    return r.returncode, tombes, (passes.groups() if passes else None), r.stderr[-2000:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sortie", required=True)
    a = ap.parse_args()
    lignes = [f"# cassures des témoins de trc-cache, {time.strftime('%Y-%m-%d %H:%M:%S')}",
              f"# commit {subprocess.run(['git', '-C', DEPOT, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()}"]
    echecs = 0
    with tempfile.TemporaryDirectory(prefix="casser-trc-cache-") as tmp:
        ws = os.path.join(tmp, "ws")
        os.makedirs(os.path.join(ws, "crates"))
        with open(os.path.join(ws, "Cargo.toml"), "w", encoding="utf-8") as f:
            f.write('[workspace]\nresolver = "3"\nmembers = ["crates/trc-cache"]\n'
                    '[workspace.package]\nversion = "0.1.0"\nedition = "2024"\nrust-version = "1.98"\n'
                    '[profile.dev]\nopt-level = 1\n')
        copie = os.path.join(ws, "crates", "trc-cache")
        # shutil.copy et non copy2 : garder les dates d'origine ferait croire à cargo que les objets
        # d'une passe précédente (faussée) sont à jour (première passe, 2026-10-15 : la « référence »
        # a tourné sur l'objet de la dernière cassure, mesuré).
        shutil.copytree(CRATE, copie, copy_function=shutil.copy, ignore=shutil.ignore_patterns("target"))
        code, tombes, compte, _ = lancer(ws)
        lignes.append(f"référence (copie intacte) : code {code}, réussis/échoués {compte}, tombés {tombes}")
        if code != 0 or tombes:
            echecs += 1
        for nom, fichier, origine, faux, attendus in CASSURES:
            chemin = os.path.join(copie, fichier)
            texte = open(chemin, encoding="utf-8").read()
            if origine is None:
                # fichier entier remplacé par une version commitée (« git:<commit>:<chemin> »)
                _, commit, source = faux.split(":", 2)
                fausse = subprocess.run(["git", "-C", DEPOT, "show", f"{commit}:{source}"], capture_output=True,
                                        text=True, encoding="utf-8", check=True).stdout
            else:
                n = texte.count(origine)
                if n != 1:
                    lignes.append(f"CASSURE REFUSÉE ({nom}) : le texte d'origine apparaît {n} fois")
                    echecs += 1
                    continue
                fausse = texte.replace(origine, faux)
            open(chemin, "w", encoding="utf-8", newline="\n").write(fausse)
            code, tombes, compte, err = lancer(ws)
            manque = [t for t in attendus if t not in tombes]
            en_plus = [t for t in tombes if t not in attendus]
            verdict = "tombe comme prévu" if not manque and code != 0 else f"NE TOMBE PAS : {manque}"
            if manque or code == 0:
                echecs += 1
            lignes.append(f"- {nom} [{fichier}] : {verdict} ; tombés {tombes}"
                          + (f" ; en plus des attendus : {en_plus}" if en_plus else "")
                          + (f" ; réussis/échoués {compte}" if compte else f" ; compilation : {err.strip()[-300:]}"))
            open(chemin, "w", encoding="utf-8", newline="\n").write(texte)
        code, tombes, compte, _ = lancer(ws)
        lignes.append(f"restaurée : code {code}, réussis/échoués {compte}, tombés {tombes}")
        if code != 0 or tombes:
            echecs += 1
    lignes.append(f"verdict : {'TOUTES LES CASSURES TOMBENT, LA COPIE RESTAURÉE TIENT' if not echecs else f'{echecs} DÉFAUT(S)'}")
    with open(a.sortie, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lignes) + "\n")
    print("\n".join(lignes))
    return 0 if not echecs else 1


if __name__ == "__main__":
    sys.exit(main())
