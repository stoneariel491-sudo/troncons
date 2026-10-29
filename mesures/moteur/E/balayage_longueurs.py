"""Balayage du débit du lecteur sans tampon contre la longueur d'une lecture (lot E, diagnostic d'E2).

Fait découvert le 2026-10-15 (moteur/REPRISE-E.md, « S M M S » et premier balayage) : à décalages
tirés sur 4 096, même fichier, même profondeur, une lecture de 12 Mio passe à ≈ 3,05 Go/s et une
lecture de 12 013 568 o (la longueur moyenne d'un tronçon) à ≈ 2,07 ; le premier balayage
(12 Mio − g) donne deux régimes (≈ 3,05 et ≈ 1,93) qui ne suivent pas l'alignement de la longueur.

Protocole, déclaré avant (réponse par délégation du 2026-10-15, réversible) : longueurs de 8 à
13 Mio par pas de 0,25 Mio (21 valeurs) plus la longueur moyenne d'un tronçon (12 013 568) et la plus
grande (12 144 640) ; deux répliques, chacune dans un ordre tiré d'une graine publiée (la dérive dans
le temps ne peut pas dessiner une courbe dans les deux ordres à la fois) ; `banc-chemin lecteur
--profondeurs 4,4 --tours-abba 1 --serie 64` ; verrou de la carte pris pendant tout le balayage ;
conditions du pilote d'E1 (secteur, aucun llama-*, disque et processeur calmes) vérifiées avant.
Règle : une longueur est « rapide » si la médiane de ses 4 passes vaut ≥ 0,9 × celle de 12 Mio dans
la même réplique ; la courbe est reproductible si les deux répliques classent chaque longueur de la
même façon.

Usage : python -I -X utf8 mesures/moteur/E/balayage_longueurs.py --dossier <journaux/...> [--graine 20261015]
Écrit : un journal par lecture et <dossier>/balayage.json ; CSV : csv/<dossier>-longueurs.csv
"""

import argparse
import csv
import json
import os
import random
import statistics
import subprocess
import sys
import time

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import pilote_e0 as p0  # noqa: E402
import pilote_e1 as p1  # noqa: E402

FICHIER = r"~\dev\modeles\trc\gpt-oss-20b.trc"
MIO = 1 << 20


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--dossier", required=True)
    a.add_argument("--graine", type=int, default=20261015)
    a.add_argument("--banc", default=p0.BANC)
    a.add_argument("--fichier", default=FICHIER)
    o = a.parse_args()
    os.makedirs(o.dossier, exist_ok=True)
    longueurs = sorted({int(8 * MIO + k * MIO / 4) for k in range(21)} | {12013568, 12144640})
    for _ in range(90):
        r = p1.conditions()
        if r is None:
            break
        print(f"{p0.maintenant()} j'attends : {r}", flush=True)
        time.sleep(20)
    else:
        sys.exit("machine jamais prête")
    if not p1.prendre_verrou():
        sys.exit("verrou pris par un autre")
    # prendre_verrou du pilote d'E1 écrit « lot E (E1 » : on le réécrit pour dire ce qui tourne.
    with open(p0.VERROU, "w", encoding="utf-8") as f:
        f.write(f"lot E (E1, balayage des longueurs de lecture, ~5 min), pris le {p0.maintenant()}\n")
    resultats = []
    try:
        for replique in (1, 2):
            ordre = longueurs[:]
            random.Random(o.graine + replique).shuffle(ordre)
            for k, lon in enumerate(ordre):
                nom = f"r{replique}-{k:02d}-{lon}"
                journal = os.path.join(o.dossier, nom + ".json")
                cmd = [o.banc, "lecteur", "--journal", journal, "--fichier", o.fichier, "--taille", str(lon),
                       "--profondeurs", "4,4", "--serie", "64", "--tours-abba", "1",
                       "--graine", str(o.graine + 1000 * replique + k), "--repos-s", "1", "--verifier", "1"]
                r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
                with open(os.path.join(o.dossier, nom + ".stderr.txt"), "w", encoding="utf-8") as f:
                    f.write(r.stderr)
                j = json.load(open(journal, encoding="utf-8"))["resultat"]
                ps = j["passes"]
                v = [p["go_s"] for p in ps]
                lat = [p["duree_us_mediane"] for p in ps]
                propres = sum(1 for p in ps if p["go_s_etrangers"] is not None and p["go_s_etrangers"] * 1e9 <= p1.SEUIL_ETRANGERS
                              and p["processeur"]["autres"] <= p1.SEUIL_PROCESSEUR_AUTRES)
                resultats.append({"replique": replique, "rang": k, "longueur": lon, "mio": lon / MIO, "go_s_mediane": statistics.median(v),
                                  "go_s": v, "latence_us_mediane": statistics.median(lat), "passes_propres": propres,
                                  "ecarts_justesse": j["justesse"]["ecarts"], "heure": j["machine_fin"]["heure"]})
                print(f"r{replique} {k:2d} {lon:>9} o ({lon / MIO:6.3f} Mio) : {statistics.median(v):.3f} Go/s, "
                      f"latence {statistics.median(lat) / 1e3:.1f} ms, propres {propres}/4", flush=True)
    finally:
        p1.rendre_verrou()
    for rep in (1, 2):
        ref = [x["go_s_mediane"] for x in resultats if x["replique"] == rep and x["longueur"] == 12 * MIO][0]
        for x in resultats:
            if x["replique"] == rep:
                x["rapide"] = x["go_s_mediane"] >= 0.9 * ref
    classes = {}
    for x in resultats:
        classes.setdefault(x["longueur"], []).append(x["rapide"])
    accord = all(len(set(v)) == 1 for v in classes.values())
    sortie = {"fichier": o.fichier, "graine": o.graine, "banc_sha256": p0.sha256(o.banc), "longueurs": longueurs,
              "resultats": resultats, "repliques_d_accord": accord,
              "rapides": sorted(k for k, v in classes.items() if all(v)), "lentes": sorted(k for k, v in classes.items() if not any(v)),
              "batterie_fin": p0.statut_batterie()}
    with open(os.path.join(o.dossier, "balayage.json"), "w", encoding="utf-8") as f:
        json.dump(sortie, f, ensure_ascii=False, indent=1)
    nom = os.path.basename(o.dossier.rstrip("/\\"))
    with open(os.path.join(ICI, "csv", f"{nom}-longueurs.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["replique", "rang", "longueur", "mio", "go_s_mediane", "latence_us_mediane", "passes_propres", "rapide", "heure"])
        w.writeheader()
        for x in resultats:
            w.writerow({k: x[k] for k in w.fieldnames})
    print(f"répliques d'accord : {accord} ; rapides {[round(x / MIO, 3) for x in sortie['rapides']]} ; lentes {[round(x / MIO, 3) for x in sortie['lentes']]}")


if __name__ == "__main__":
    main()
