"""Analyse de la mesure E1 du lot E (débit du lecteur, disque seul) : verdicts contre les seuils
déclarés avant la première passe mesurée (moteur/REPRISE-E.md, « E1, débit du lecteur sur le
disque seul »), CSV des figures.

  - passe propre : octets étrangers / durée ≤ 0,26 Go/s (10 % de 2,58 [mes. 01]) ;
  - témoin du compteur : octets du système ≥ nos octets, à chaque passe ;
  - verdict sur la tentative qui a au moins 2 passes A propres (la première dans l'ordre) :
    médiane des passes A propres ≥ 2,064 Go/s (0,8 × 2,58) ; sinon « non jugé » ;
  - bruit : écart relatif entre passes miroirs d'une même lettre ; QD 4 et QD 1 ne diffèrent que si
    l'écart dépasse 2 × le plus grand bruit et 3 % (06 § 7.5) ;
  - second chemin : loi de Little, X = q · b / R, avec R la latence médiane d'une lecture.

Usage : python -I -X utf8 mesures/moteur/E/analyse_e1.py mesures/moteur/E/journaux/<séance> [--regle 1|2]
Écrit : <séance>/resume.json et mesures/moteur/E/csv/<séance>-lecteur-passes.csv
"""

import csv
import glob
import json
import os
import statistics
import sys

SEUIL_DISQUE = 0.8 * 2.58
SEUIL_ETRANGERS = 0.26
# Règle 2 (déclarée le 2026-10-15 à 15 h 43, après la séance 1 et avant la séance 2) : une passe
# propre demande aussi que les autres programmes occupent ≤ 40 % du processeur pendant elle.
# Raison : BitLocker déchiffre chaque octet lu sur le processeur (01 § 2.7) ; l'étude 01 § 2.3 a vu
# ses gros blocs se reproduire à quelques % sous 35 à 40 % d'occupation et non sous 90 à 100 %.
# La séance 1 a été jugée par la règle 1 (disque seul) ; son verdict reste publié tel quel.
SEUIL_PROCESSEUR_AUTRES = 0.40
ICI = os.path.dirname(os.path.abspath(__file__))


def bruit_miroir(valeurs):
    n = len(valeurs)
    if n < 2:
        return None
    m = statistics.mean(valeurs)
    return max(abs(valeurs[i] - valeurs[n - 1 - i]) for i in range(n // 2)) / m


def main():
    seance = sys.argv[1].rstrip("/\\")
    regle = int(sys.argv[sys.argv.index("--regle") + 1]) if "--regle" in sys.argv else 2
    nom = os.path.basename(seance)
    lignes, tentatives = [], []
    for chemin in sorted(glob.glob(os.path.join(seance, "lecteur-*.json")), key=lambda p: int(p.rsplit("-", 1)[1].split(".")[0])):
        k = int(chemin.rsplit("-", 1)[1].split(".")[0])
        with open(chemin, encoding="utf-8") as f:
            j = json.load(f)
        r = j["resultat"]
        if "passes" not in r:
            tentatives.append({"k": k, "erreur": r.get("erreur")})
            continue
        passes = []
        for p in r["passes"]:
            etr = p["go_s_etrangers"]
            autres = (p.get("processeur") or {}).get("autres")
            propre = etr is not None and etr <= SEUIL_ETRANGERS
            if regle >= 2:
                propre = propre and autres is not None and autres <= SEUIL_PROCESSEUR_AUTRES
            x = {"tentative": k, "tour": p["tour"], "rang": p["rang"], "lettre": p["lettre"], "profondeur": p["profondeur"],
                 "lectures": p["lectures"], "octets": p["octets"], "secondes": p["secondes"], "go_s": p["go_s"],
                 "duree_us_p10": p["duree_us_p10"], "duree_us_mediane": p["duree_us_mediane"], "duree_us_p90": p["duree_us_p90"],
                 "duree_us_max": p["duree_us_max"], "octets_systeme": p["octets_systeme"], "octets_etrangers": p["octets_etrangers"],
                 "go_s_etrangers": etr, "processeur_autres": autres, "propre": propre,
                 "compteur_voit_nos_octets": p["octets_systeme"] is not None and p["octets_systeme"] >= p["octets"],
                 "erreurs": p["erreurs"],
                 "go_s_little": p["profondeur"] * (p["octets"] / p["lectures"]) / (p["duree_us_mediane"] * 1e-6) / 1e9}
            x["little_sur_mur"] = x["go_s_little"] / x["go_s"]
            passes.append(x)
            lignes.append(x)
        a = [x["go_s"] for x in passes if x["lettre"] == "A"]
        b = [x["go_s"] for x in passes if x["lettre"] == "B"]
        a_propres = [x["go_s"] for x in passes if x["lettre"] == "A" and x["propre"]]
        b_propres = [x["go_s"] for x in passes if x["lettre"] == "B" and x["propre"]]
        bruit_a, bruit_b = bruit_miroir(a), bruit_miroir(b)
        plus_grand = max(v for v in (bruit_a, bruit_b) if v is not None) if (bruit_a is not None or bruit_b is not None) else None
        med_a = statistics.median(a_propres) if a_propres else None
        med_b = statistics.median(b_propres) if b_propres else None
        t = {"k": k, "repos": r.get("repos"), "justesse": {"ecarts": r["justesse"]["ecarts"], "casser": r["justesse"]["casser"],
                                                           "tient": r["justesse"]["ecarts"] == (1 if r["justesse"]["casser"] else 0)},
             "passes_a_propres": len(a_propres), "passes_b_propres": len(b_propres),
             "mediane_a_propres_go_s": med_a, "mediane_b_propres_go_s": med_b,
             "toutes_a_go_s": a, "toutes_b_go_s": b, "bruit_miroir_a": bruit_a, "bruit_miroir_b": bruit_b,
             "temoin_compteur_tient": all(x["compteur_voit_nos_octets"] for x in passes),
             "erreurs": sum(x["erreurs"] for x in passes),
             "little_sur_mur": [round(x["little_sur_mur"], 3) for x in passes]}
        if med_a is not None and med_b is not None and plus_grand is not None:
            ecart = (med_a - med_b) / statistics.mean([med_a, med_b])
            t["qd4_contre_qd1"] = {"ecart_relatif": ecart, "plus_grand_bruit": plus_grand,
                                   "distincts": abs(ecart) > 2 * plus_grand and abs(ecart) > 0.03}
        tentatives.append(t)
    jugee = next((t for t in tentatives if t.get("passes_a_propres", 0) >= 2), None)
    verdict = {"regle": regle, "seuil_go_s": SEUIL_DISQUE, "seuil_etrangers_go_s": SEUIL_ETRANGERS,
               "seuil_processeur_autres": SEUIL_PROCESSEUR_AUTRES if regle >= 2 else None}
    if jugee is None:
        verdict.update({"etat": "non jugé", "raison": "aucune tentative avec 2 passes A propres"})
    else:
        verdict.update({"tentative": jugee["k"], "mediane_a_propres_go_s": jugee["mediane_a_propres_go_s"],
                        "etat": "tient" if jugee["mediane_a_propres_go_s"] >= SEUIL_DISQUE else "tombe",
                        "temoins": jugee["justesse"]["tient"] and jugee["temoin_compteur_tient"] and jugee["erreurs"] == 0})
    resume = {"seance": nom, "tentatives": tentatives, "verdict_E1_disque": verdict}
    os.makedirs(os.path.join(ICI, "csv"), exist_ok=True)
    if lignes:
        with open(os.path.join(ICI, "csv", f"{nom}-lecteur-passes.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(lignes[0].keys()))
            w.writeheader()
            w.writerows(lignes)
    with open(os.path.join(seance, "resume.json"), "w", encoding="utf-8") as f:
        json.dump(resume, f, ensure_ascii=False, indent=2)
    print(json.dumps(resume, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
