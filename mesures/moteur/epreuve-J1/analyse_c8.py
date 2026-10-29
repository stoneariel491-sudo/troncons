"""C8 refait par le juge, deux instruments.

(1) PDH (l'instrument du § 7.1, compteur global du disque, intégré par le moteur lui-même) contre
    les octets comptés par le moteur (compteurs_total.octets_lus, chargement des résidents compris :
    vérifié, total = préremplissage + génération + chargement) ; borne déclarée : repos × durée + 100 Mo.
(2) Compteurs d'E/S du processus (GetProcessIoCounters lu par le pilote sur la poignée après la
    sortie ; témoin : temoin_compteurs_es.py), qui ne voient que les ReadFile du processus.
Commande : python -I -X utf8 analyse_c8.py <seance.json> [<seance.json> …] > journal.json
"""
import json
import sys

sortie = []
for chemin in sys.argv[1:]:
    s = json.load(open(chemin, encoding="utf-8"))
    for p in s["passes_faites"]:
        if p["sorte"] not in ("troncons", "evaluer"):
            continue
        cmd = p["commande"]
        j = json.load(open(cmd[cmd.index("--journal") + 1], encoding="utf-8"))
        c = j.get("compteurs_total") or j["compteurs"]
        moteur = c["octets_lus"]
        r = {"seance": s["seance"], "passe": p["passe"], "moteur_octets": moteur}
        d = j.get("disque")
        if d:
            rep = d["repos_octets_s"] or 0.0
            r["pdh_octets"] = d["octets_lus_pdh"]
            r["pdh_moins_moteur_mo"] = (d["octets_lus_pdh"] - moteur) / 1e6
            r["borne_mo"] = (rep * d["duree_s"] + 100e6) / 1e6
            r["pdh_tient"] = abs(d["octets_lus_pdh"] - moteur) <= rep * d["duree_s"] + 100e6
        if p.get("es_os"):
            r["processus_octets"] = p["es_os"]["octets_lus"]
            r["processus_moins_moteur_mo"] = (p["es_os"]["octets_lus"] - moteur) / 1e6
            r["processus_tient_100mo"] = abs(p["es_os"]["octets_lus"] - moteur) <= 100e6
        sortie.append(r)
print(json.dumps(sortie, ensure_ascii=False, indent=1))
