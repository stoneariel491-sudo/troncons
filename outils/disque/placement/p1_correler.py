"""P1 : corrélation entre la carte des fichiers (carte.py projeter) et les débits déjà mesurés.

Lit, sans rien mesurer de neuf :
- les cartes `mesures/disque/placement/carte-<fichier>.json` (extents, tronçons projetés) ;
- la trace de routage du 120b de l'épreuve J1 (708 jetons, `mesures/moteur/epreuve-J1/journaux/
  programme/invite/t120-boucle.trace`), pour pondérer chaque tronçon par sa fréquence d'appel ;
- tous les journaux `troncons disque` commités (débit de la phase disque, durée médiane et p90 par
  lecture, date) ;
- les journaux du codeur (date et débit d'écriture de chaque fichier).

Écrit `mesures/disque/placement/p1-correlation.json` et `p1-mesures-disque.csv`.

  python -I -X utf8 outils/disque/placement/p1_correler.py
"""
import csv
import datetime as dt
import glob
import json
import os
import pathlib
import statistics

RACINE = pathlib.Path(__file__).resolve().parents[3]
M = RACINE / "mesures/disque/placement"
TRACE120 = RACINE / "mesures/moteur/epreuve-J1/journaux/programme/invite/t120-boucle.trace"
TRACE20 = RACINE / "mesures/moteur/epreuve-J1/journaux/programme/invite/t20-boucle.trace"

FICHIERS = {
    "A120": ("gpt-oss-120b.trc", "mesures/moteur/F/journaux/coder-120b.json"),
    "B120": ("gpt-oss-120b-v12.trc", "mesures/genome/construction/codon/journaux/coder-120b-v12.json"),
    "C120": ("gpt-oss-120b-v10-recode.trc", "mesures/genome/construction/codon/journaux/coder-120b-v10-recode.json"),
    "A20": ("gpt-oss-20b.trc", "mesures/moteur/F/journaux/coder-20b.json"),
    "B20": ("gpt-oss-20b-v12.trc", "mesures/genome/construction/codon/journaux/coder-20b-v12.json"),
}


def lire_trace(p):
    lignes = [l for l in p.read_text(encoding="utf-8").splitlines() if l and not l.startswith("#") and not l.startswith("E=")]
    acces = []
    for l in lignes:
        for c, groupe in enumerate(l.split("|")):
            for x in groupe.split():
                acces.append((c, int(x)))
    return len(lignes), acces


def main():
    sortie = {"fichiers": {}}
    n120, acces120 = lire_trace(TRACE120)
    n20, acces20 = lire_trace(TRACE20)
    for cle, (nom, journal) in FICHIERS.items():
        carte = json.loads((M / f"carte-{nom}.json").read_text(encoding="utf-8"))
        cod = json.loads((RACINE / journal).read_text(encoding="utf-8"))
        lect = {(l[0], l[1]): l for l in carte["lectures"]}
        acces = acces120 if "120" in cle else acces20
        coupes = sum(1 for a in acces if lect[a][4] > 1)
        morceaux = sum(lect[a][4] for a in acces)
        fin = carte["ecriture"]
        debut = fin - cod["duree_s"]
        sortie["fichiers"][cle] = {
            "nom": nom, "extents": carte["extents"], "extent_median_o": carte["extent_median_o"],
            "lcn_moyen_frac": round(carte["lcn_moyen_frac"], 4), "lcn_min_frac": round(carte["lcn_min_frac"], 4), "lcn_max_frac": round(carte["lcn_max_frac"], 4),
            "lectures_coupees_repertoire": carte["lectures_coupees"], "troncons": carte["troncons"],
            "phase_disque_morceaux_par_lecture": round(carte["phase_disque"]["morceaux"] / carte["phase_disque"]["n"], 4),
            "phase_disque_lectures_coupees": carte["phase_disque"]["lectures_coupees"],
            "trace_jetons": n120 if "120" in cle else n20, "trace_acces": len(acces),
            "trace_acces_coupes_frac": round(coupes / len(acces), 4), "trace_morceaux_par_acces": round(morceaux / len(acces), 4),
            "ecrit_debut_local": dt.datetime.fromtimestamp(debut).strftime("%Y-%m-%d %H:%M"),
            "ecrit_fin_local": dt.datetime.fromtimestamp(fin).strftime("%Y-%m-%d %H:%M"),
            "ecriture_mo_s": round(cod["taille_trc"] / cod["duree_s"] / 1e6, 1),
            "octets_lus_par_lecture_moyen": round(carte["octets_lus_par_lecture_moyen"]),
        }
    # Les mesures `troncons disque` commitées (hors ce dossier), dédoublonnées par (fichier, date).
    vus, lignes = set(), []
    for f in sorted(glob.glob(str(RACINE / "mesures/**/*.json"), recursive=True)):
        if "placement" in f:
            continue
        try:
            v = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        pile = [v]
        while pile:
            x = pile.pop()
            if isinstance(x, dict):
                if x.get("outil") == "troncons disque":
                    cle = (x["fichier"], x["date_utc"])
                    if cle not in vus:
                        vus.add(cle)
                        lignes.append({"date_utc": x["date_utc"], "fichier": x["fichier"].split("/")[-1], "n": x["n"], "profondeur": x["profondeur"],
                                       "go_s": round(x["go_s"], 4), "duree_us_mediane": x["duree_us_mediane"], "duree_us_p90": x["duree_us_p90"],
                                       "octets": x["octets"], "journal": os.path.relpath(f, RACINE).replace("\\", "/")})
                pile.extend(x.values())
            elif isinstance(x, list):
                pile.extend(x)
    lignes.sort(key=lambda r: r["date_utc"])
    with open(M / "p1-mesures-disque.csv", "w", newline="", encoding="utf-8") as g:
        w = csv.DictWriter(g, fieldnames=list(lignes[0].keys()))
        w.writeheader()
        w.writerows(lignes)
    # Âge de chaque fichier à chaque mesure, et le débit.
    nom_vers_cle = {v[0]: k for k, v in FICHIERS.items()}
    for r in lignes:
        cle = nom_vers_cle.get(r["fichier"])
        if cle:
            fin = dt.datetime.strptime(sortie["fichiers"][cle]["ecrit_fin_local"], "%Y-%m-%d %H:%M")
            mesure = dt.datetime.strptime(r["date_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc).astimezone().replace(tzinfo=None)
            r["age_h"] = round((mesure - fin).total_seconds() / 3600, 1)
            r["cle"] = cle
    sortie["mesures_disque"] = lignes
    # Bruit d'un fichier à lui-même : écart relatif entre deux passes calmes d'une même séance.
    ecarts = []
    for date_pref in ("2026-10-22", "2026-10-16T10", "2026-10-16T02"):
        par = {}
        for r in lignes:
            if r["date_utc"].startswith(date_pref):
                par.setdefault(r["fichier"], []).append(r["go_s"])
        for fic, v in par.items():
            if len(v) == 2:
                ecarts.append({"seance": date_pref, "fichier": fic, "go_s": v, "ecart_rel": round(abs(v[0] - v[1]) / statistics.mean(v), 4)})
    sortie["bruit_soi_meme"] = ecarts
    sortie["bruit_soi_meme_max"] = max(e["ecart_rel"] for e in ecarts)
    (M / "p1-correlation.json").write_text(json.dumps(sortie, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in sortie["fichiers"].items():
        print(k, json.dumps(v, ensure_ascii=False))
    for r in lignes:
        print(r.get("cle"), r["date_utc"], r["fichier"], r["go_s"], r["duree_us_mediane"], r["duree_us_p90"], r.get("age_h"))
    print("bruit :", ecarts)


if __name__ == "__main__":
    main()
