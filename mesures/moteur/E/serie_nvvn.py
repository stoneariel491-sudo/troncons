"""Série N V V N du lot E (déclarée dans moteur/REPRISE-E.md avant la mesure) : `banc-chemin chemin`
tel que spécifié (N, lecture de `longueur0`) contre la variante E2-V (V, `--longueur-lecture`), en
alternance dans une même fenêtre, sous le verrou de la carte, conditions du pilote d'E1 vérifiées
avant. Le gain est réel si l'écart des médianes A dépasse 2 × le plus grand bruit et 3 % (06 § 7.5).

Usage : python -I -X utf8 mesures/moteur/E/serie_nvvn.py --dossier <journaux/...> [--longueur 12582912]
"""

import argparse
import json
import os
import statistics
import subprocess
import sys
import time

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import pilote_e0 as p0  # noqa: E402
import pilote_e1 as p1  # noqa: E402
import pilote_e2 as p2  # noqa: E402


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--dossier", required=True)
    a.add_argument("--longueur", type=int, default=12582912)
    a.add_argument("--graine", type=int, default=20261415)
    a.add_argument("--fichier", default=p2.FICHIER)
    a.add_argument("--lettres", default="NVVN")
    a.add_argument("--tours", type=int, default=2)
    o = a.parse_args()
    os.makedirs(o.dossier, exist_ok=True)
    for _ in range(90):
        r = p1.conditions()
        if r is None:
            break
        print(f"{p0.maintenant()} j'attends : {r}", flush=True)
        time.sleep(20)
    else:
        sys.exit("machine jamais prête")
    if not p2.prendre_verrou(f"série {o.lettres} sur {os.path.basename(o.fichier)}"):
        sys.exit("verrou pris par un autre")
    lignes = []
    try:
        for k, x in enumerate(o.lettres):
            journal = os.path.join(o.dossier, f"{k + 1}-{x}.json")
            cmd = [p0.BANC, "chemin", "--journal", journal, "--fichier", o.fichier, "--graine", str(o.graine + 100 * k),
                   "--tours-abba", str(o.tours), "--residents", "48"]
            if x == "V":
                cmd += ["--longueur-lecture", str(o.longueur)]
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=3600)
            with open(os.path.join(o.dossier, f"{k + 1}-{x}.stderr.txt"), "w", encoding="utf-8") as f:
                f.write(r.stderr)
            j = json.load(open(journal, encoding="utf-8"))["resultat"]
            a_ = [p["passe"] for p in j["passes"] if p["lettre"] == "A"]
            b_ = [p["passe"] for p in j["passes"] if p["lettre"] == "B"]
            propres = sum(1 for p in a_ if p["go_s_etrangers"] is not None and p["go_s_etrangers"] * 1e9 <= p1.SEUIL_ETRANGERS
                          and p["processeur"]["autres"] <= p1.SEUIL_PROCESSEUR_AUTRES)
            l = {"rang": k, "lettre": x, "code": r.returncode, "a_go_s_servis": [p["go_s_servis"] for p in a_],
                 "b_go_s_lus": [p["go_s_troncons"] for p in b_], "a_propres": propres,
                 "mediane_a_servis": statistics.median(p["go_s_servis"] for p in a_),
                 "c2_tient": not j["temoin"]["temoin"]["origines_fausses"] and not j["temoin"]["temoin"]["parties_fausses"]
                 and not j["temoin"]["controle"]["experts_non_nuls"] and j["temoin"]["temoin"]["verifies"] == j["experts"],
                 "experts": j["experts"],
                 "heure_fin": j["machine_fin"]["heure"], "batterie_apres": p0.statut_batterie()}
            lignes.append(l)
            print(f"{k + 1} {x} : médiane A {l['mediane_a_servis']:.3f} Go/s servis, A propres {propres}/{len(a_)}, C2 {l['c2_tient']}", flush=True)
    finally:
        p2.rendre_verrou()
    med = {x: statistics.median([v for l in lignes if l["lettre"] == x for v in l["a_go_s_servis"]]) for x in "NV"}
    bruit = {x: abs(lignes[i]["mediane_a_servis"] - lignes[j]["mediane_a_servis"]) / max(lignes[i]["mediane_a_servis"], lignes[j]["mediane_a_servis"])
             for x, (i, j) in {"N": (0, 3), "V": (1, 2)}.items() if len(lignes) == 4}
    bruit = bruit or {"N": 0.0, "V": 0.0}  # série N V sans miroir : pas de bruit mesuré, distincts non jugé
    ecart = abs(med["V"] - med["N"]) / max(med.values())
    sortie = {"lignes": lignes, "medianes_a_servis": med, "bruit_miroir": bruit, "ecart_relatif": ecart,
              "distincts": (ecart > max(2 * max(bruit.values()), 0.03)) if len(lignes) == 4 else None, "gain_v_sur_n": med["V"] / med["N"]}
    with open(os.path.join(o.dossier, "serie.json"), "w", encoding="utf-8") as f:
        json.dump(sortie, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in sortie.items() if k != "lignes"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
