"""Données des figures du mémoire pour les étapes O2 à O4 du lot O, tirées des journaux commités.

Écrit sous mesures/moteur/O/csv/ :
  o-jetons-s.csv        jetons/s (génération, préremplissage), mémoire et VRAM de pointe, par passe :
                        troncons (séances O4 et J1+) et llama.cpp (mesures/base-gpt-oss, même invite) ;
  o-memoire-taille.csv  mémoire de pointe contre taille du modèle (thèse de la fenêtre bornée) ;
  o-c4-20b.csv          KL par position contre la référence f64, troncons et llama.cpp (20b) ;
  o-memoire-etapes.csv  ensemble de travail après chaque étape de l'ouverture (D-C7), si présent.

Usage : python -I -X utf8 mesures/moteur/O/vers_csv_o.py
"""
from __future__ import annotations

import json
import pathlib
import shutil

RACINE = pathlib.Path(__file__).resolve().parents[3]
O = RACINE / "mesures/moteur/O"
CSV = O / "csv"
BASE = RACINE / "mesures/base-gpt-oss"


def charger(p: pathlib.Path):
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    CSV.mkdir(parents=True, exist_ok=True)
    lignes = ["moteur,configuration,modele,passe,generation_jetons_s,prefill_jetons_s,ram_pointe_o,vram_pointe_mio,taille_modele_o"]
    tailles = {"gpt-oss-120b": 63387346208, "gpt-oss-20b": 12109566624}
    for dossier in ("journaux/o4", "journaux/j1plus"):
        for p in sorted((O / dossier).glob("*.json")):
            if p.name.startswith(("pilote", "verdicts", "codeur")):
                continue
            j = charger(p)
            if j.get("outil") not in ("troncons generer",) or "generation_jetons_s" not in j:
                continue
            m = j["moteur"]
            modele = "gpt-oss-120b" if "120b" in m["fichier"] else "gpt-oss-20b"
            conf = ("brut" if m["brut"] else "code") + ("+L12" if m.get("longueur_lecture") else "") + ("+pf" if m.get("prechargement") else "")
            if j["jetons_produits"] < 16:
                conf += "+court"
            lignes.append(f"troncons,{conf},{modele},{p.stem},{j['generation_jetons_s']:.6f},{j['prefill_jetons_s']:.6f},"
                          f"{j['memoire']['pointe_ensemble_travail']},{j['vram']['pointe_mio']},{tailles[modele]}")
    for p in sorted(BASE.glob("*/*.json")):
        j = charger(p)
        if "generation" not in j:
            continue
        modele = "gpt-oss-120b" if p.parent.name == "120b" else "gpt-oss-20b"
        conf = j["etiquette"].split("-")[1]
        lignes.append(f"llama.cpp,{conf},{modele},{j['etiquette']},{j['generation']['jetons_s']},{j['prefill']['jetons_s']},"
                      f"{j['memoire_pointe']['ensemble_travail_octets']},{j['vram_mio']['pointe']},{tailles[modele]}")
    (CSV / "o-jetons-s.csv").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    # mémoire contre taille : une ligne par (moteur, modèle), le maximum des passes de 256 jetons
    pts = {}
    for l in lignes[1:]:
        c = l.split(",")
        if "+court" in c[1] or c[1].startswith(("cache",)):
            continue
        cle = (c[0], c[2])
        pts[cle] = max(pts.get(cle, 0), int(c[6]))
    t = ["moteur,modele,taille_modele_o,ram_pointe_max_o"] + [f"{m},{mod},{tailles[mod]},{v}" for (m, mod), v in sorted(pts.items())]
    (CSV / "o-memoire-taille.csv").write_text("\n".join(t) + "\n", encoding="utf-8")
    c4 = O / "journaux/o3/c4-20b-comparer.csv"
    if c4.exists():
        shutil.copyfile(c4, CSV / "o-c4-20b.csv")
    et = ["passe,modele,longueur_lecture,etape,ensemble_travail_o"]
    for p in sorted((O / "journaux/j1plus").glob("*dc7*.json")):
        j = charger(p)
        m = j["moteur"]
        for e in m.get("etapes_memoire", []):
            et.append(f"{p.stem},{'120b' if '120b' in m['fichier'] else '20b'},{m.get('longueur_lecture') or 0},{e['etape']},{e['ensemble_travail']}")
        et.append(f"{p.stem},{'120b' if '120b' in m['fichier'] else '20b'},{m.get('longueur_lecture') or 0},fin,{j['memoire']['fin_ensemble_travail']}")
    (CSV / "o-memoire-etapes.csv").write_text("\n".join(et) + "\n", encoding="utf-8")
    print("\n".join(t))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
