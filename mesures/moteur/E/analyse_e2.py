"""Analyse de l'étape E2 du lot E : verdicts contre les critères déclarés avant toute ligne de code
d'E2 (moteur/REPRISE-E.md, « E2 », commit 6b59ff3), CSV des figures du mémoire.

  - C2 : passe témoin du vrai fichier : 768 experts vérifiés, 0 empreinte d'origine fausse, 0 partie
    fausse, 0 compteur de la carte non nul, 0 erreur de lecture ;
  - cassure : sur la copie à 12 bits retournés, les 12 experts détectés et aucun autre ;
  - débit : passe propre (règle 2 d'E1 : octets étrangers ≤ 0,26 Go/s et processeur des autres
    ≤ 40 %) ; sur au moins 2 passes A propres, médiane des Go/s servis ≥ 0,8 × 2,58 × r(F1) ;
  - témoin du débit : médiane des A (Go/s de tronçons) ≤ 1,10 × le plus petit des étages de la
    même séance (médiane des B, DMA seule, décodage seul) ;
  - prédiction (non jugée) : A / B entre 0,95 et 1,00 ;
  - bruit : écart relatif des passes miroirs ; A et B ne diffèrent que si l'écart dépasse 2 × le plus
    grand bruit et 3 % (06 § 7.5).

Usage : python -I -X utf8 mesures/moteur/E/analyse_e2.py mesures/moteur/E/journaux/<séance>
Écrit : <séance>/resume.json et mesures/moteur/E/csv/<séance>-{passes,etages,cassure}.csv
"""

import csv
import glob
import json
import os
import statistics
import sys

R_F1 = 13253760 / 11990368
SEUIL_SERVIS = 0.8 * 2.58 * R_F1
SEUIL_ETRANGERS = 0.26
SEUIL_PROCESSEUR_AUTRES = 0.40
MARGE_ETAGES = 1.10
N_EXPERTS = 768


def lire(chemin):
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


def propre(p):
    e = p.get("go_s_etrangers")
    return e is not None and e <= SEUIL_ETRANGERS and p["processeur"]["autres"] <= SEUIL_PROCESSEUR_AUTRES


def bruit_miroir(passes, lettre, cle):
    """Écart relatif entre les passes miroirs (rang 0 et 3 pour A, 1 et 2 pour B) de chaque tour."""
    rangs = (0, 3) if lettre == "A" else (1, 2)
    ecarts = []
    for tour in sorted({x["tour"] for x in passes}):
        v = [x["passe"][cle] for x in passes if x["tour"] == tour and x["rang"] in rangs]
        if len(v) == 2:
            ecarts.append(abs(v[0] - v[1]) / max(v))
    return max(ecarts) if ecarts else None


def c2(temoin):
    t = temoin["temoin"]
    return {
        "verifies": t["verifies"],
        "origines_fausses": t["origines_fausses"],
        "parties_fausses": t["parties_fausses"],
        "compteurs_non_nuls": temoin["controle"]["experts_non_nuls"],
        "erreurs_lecture": temoin["erreurs_lecture"],
        "grilles_refusees": temoin["grilles_refusees"],
        "tient": t["verifies"] == N_EXPERTS and not t["origines_fausses"] and not t["parties_fausses"]
        and not temoin["controle"]["experts_non_nuls"] and not temoin["erreurs_lecture"],
    }


def main():
    seance = sys.argv[1].rstrip("/\\")
    nom = os.path.basename(seance)
    dossier_csv = os.path.join(os.path.dirname(os.path.abspath(__file__)), "csv")
    os.makedirs(dossier_csv, exist_ok=True)
    resume = {"seance": nom, "seuils": {"servis_go_s": SEUIL_SERVIS, "r_F1": R_F1, "etrangers_go_s": SEUIL_ETRANGERS,
                                        "processeur_autres": SEUIL_PROCESSEUR_AUTRES, "marge_etages": MARGE_ETAGES}}

    # ---- Cassure ----------------------------------------------------------------------------
    jc = os.path.join(seance, "cassure.json")
    jcc = os.path.join(seance, "casser-copie.json")
    if os.path.exists(jc) and os.path.exists(jcc):
        c = lire(jc)["resultat"]
        corr = lire(jcc)["resultat"]["corruptions"]
        t = c["temoin"]
        prod = c["passes"][0]["passe"] if c["passes"] else None
        lignes = []
        for k in corr:
            i = k["indice"]
            lignes.append({
                "indice": i, "couche": k["couche"], "expert": k["expert"], "region": k["region"], "matrice": k["matrice"],
                "decalage_partie": k["decalage_partie"], "bit": k["bit"],
                "temoin_partie_fausse": i in t["temoin"]["parties_fausses"],
                "temoin_origine_fausse": i in t["temoin"]["origines_fausses"],
                "temoin_compteurs_carte": i in t["controle"]["experts_non_nuls"],
                "temoin_grilles_refusees": i in t["grilles_refusees"],
                "temoin_detecte": i in t["detectes"],
                "production_compteurs_carte": prod is not None and i in prod["controle"]["experts_non_nuls"],
                "production_detecte": prod is not None and i in prod["detectes"],
            })
        with open(os.path.join(dossier_csv, f"{nom}-cassure.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(lignes[0].keys()))
            w.writeheader()
            w.writerows(lignes)
        cas = c["cassure"]
        resume["cassure"] = {
            "corrompus": len(corr), "manques": cas["manques"], "en_trop": cas["en_trop"],
            "tombe_comme_il_faut": len(corr) == 12 and not cas["manques"] and not cas["en_trop"],
            "vus_par_le_controle_d_origine": sum(x["temoin_origine_fausse"] for x in lignes),
            "vus_par_l_empreinte_de_partie": sum(x["temoin_partie_fausse"] for x in lignes),
            "vus_par_la_production": sum(x["production_detecte"] for x in lignes),
            "compteurs_carte_temoin": t["controle"], "compteurs_carte_production": prod["controle"] if prod else None,
            "detail": lignes,
        }

    # ---- Séances de débit (chemin-k) --------------------------------------------------------
    resume["tentatives"] = []
    rangees_passes, rangees_etages = [], []
    for jk in sorted(glob.glob(os.path.join(seance, "chemin*-*.json"))):
        k = os.path.basename(jk)[len("chemin"):-len(".json")].lstrip("-")
        r = lire(jk).get("resultat")
        if not r or "temoin" not in r:
            resume["tentatives"].append({"k": k, "erreur": "journal sans résultat"})
            continue
        passes = r["passes"]
        for x in passes:
            p = x["passe"]
            rangees_passes.append({
                "tentative": k, "tour": x["tour"], "rang": x["rang"], "lettre": x["lettre"], "mode": p["mode"],
                "secondes": p["secondes"], "go_s_troncons": p["go_s_troncons"], "go_s_servis": p["go_s_servis"],
                "experts_par_s": p["experts_par_s"], "lecture_us_mediane": p["lecture_us_mediane"],
                "lecture_us_p90": p["lecture_us_p90"], "copie_ms_mediane": p["copie_ms_mediane"],
                "decodage_ms_mediane": p["decodage_ms_mediane"], "go_s_etrangers": p["go_s_etrangers"],
                "processeur_autres": p["processeur"]["autres"], "processeur_nous": p["processeur"]["nous"],
                "propre": propre(p), "compteurs_non_nuls": len(p["controle"]["experts_non_nuls"]),
                "secteur_debut": p["machine_debut"]["secteur"], "secteur_fin": p["machine_fin"]["secteur"],
            })
        for e in r["etages"]:
            rangees_etages.append({"tentative": k, "tour": e["tour"], "dma_go_s": e["dma"]["go_s_troncons"],
                                   "dma_go_s_mur": e["dma"]["go_s_troncons_mur"],
                                   "decodage_go_s": e["decodage"]["go_s_troncons"],
                                   "decodage_ms_par_expert": e["decodage"]["ms_par_expert"],
                                   "decodage_controle_non_nul": e["decodage"]["controle_non_nul"]})
        a = [x["passe"] for x in passes if x["lettre"] == "A"]
        b = [x["passe"] for x in passes if x["lettre"] == "B"]
        a_propres = [p for p in a if propre(p)]
        b_propres = [p for p in b if propre(p)]
        med = lambda v: statistics.median(v) if v else None  # noqa: E731
        med_a_servis = med([p["go_s_servis"] for p in a_propres])
        med_a_tr = med([p["go_s_troncons"] for p in a])
        med_b_tr = med([p["go_s_troncons"] for p in b])
        dma = med([e["dma"]["go_s_troncons"] for e in r["etages"]])
        dec = med([e["decodage"]["go_s_troncons"] for e in r["etages"]])
        plus_petit = min(v for v in (med_b_tr, dma, dec) if v is not None)
        bruit_a = bruit_miroir(passes, "A", "go_s_troncons")
        bruit_b = bruit_miroir(passes, "B", "go_s_troncons")
        grand_bruit = max(v for v in (bruit_a, bruit_b) if v is not None)
        ecart_ab = abs(med_a_tr - med_b_tr) / max(med_a_tr, med_b_tr)
        t = {
            "k": k,
            "C2": c2(r["temoin"]),
            "temoin_passe_go_s_servis": r["temoin"]["go_s_servis"],
            "r_reel": r["r_reel"],
            "passes_a_propres": len(a_propres), "passes_b_propres": len(b_propres),
            "toutes_a_go_s_servis": [p["go_s_servis"] for p in a],
            "toutes_b_go_s_troncons": [p["go_s_troncons"] for p in b],
            "compteurs_production_non_nuls": sum(len(p["controle"]["experts_non_nuls"]) for p in a),
            "decodage_seul_controle_non_nul": sum(e["decodage"]["controle_non_nul"] for e in r["etages"]),
            "mediane_a_propres_go_s_servis": med_a_servis,
            "pire_a_propre_go_s_servis": min((p["go_s_servis"] for p in a_propres), default=None),
            "verdict_debit": ("non jugé" if len(a_propres) < 2 else ("tient" if med_a_servis >= SEUIL_SERVIS else "tombe")),
            "etages_go_s_troncons": {"disque_seul_mediane_B": med_b_tr, "dma": dma, "decodage": dec, "plus_petit": plus_petit},
            "mediane_a_go_s_troncons": med_a_tr,
            "temoin_debit_le_min": {"rapport_a_sur_min": med_a_tr / plus_petit, "tient": med_a_tr <= MARGE_ETAGES * plus_petit},
            "a_sur_b": med_a_tr / med_b_tr,
            "prediction_a_sur_b_0_95_a_1": 0.95 <= med_a_tr / med_b_tr <= 1.0,
            "bruit_miroir_a": bruit_a, "bruit_miroir_b": bruit_b,
            "a_contre_b": {"ecart_relatif": ecart_ab, "plus_grand_bruit": grand_bruit,
                           "distincts": ecart_ab > max(2 * grand_bruit, 0.03)},
            "secteur_partout": all(p["machine_debut"]["secteur"] and p["machine_fin"]["secteur"] for p in a + b),
        }
        resume["tentatives"].append(t)
    for nom_csv, rangees in ((f"{nom}-passes.csv", rangees_passes), (f"{nom}-etages.csv", rangees_etages)):
        if rangees:
            with open(os.path.join(dossier_csv, nom_csv), "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(rangees[0].keys()))
                w.writeheader()
                w.writerows(rangees)
    # ---- Série N V V N (serie_nvvn.py), si la séance en est une ------------------------------
    js = os.path.join(seance, "serie.json")
    if os.path.exists(js):
        sv = lire(js)
        with open(os.path.join(dossier_csv, f"{nom}-nvvn.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["rang", "lettre", "passe_a", "go_s_servis"])
            for l in sv["lignes"]:
                for i, v in enumerate(l["a_go_s_servis"]):
                    w.writerow([l["rang"], l["lettre"], i, v])
        resume["nvvn"] = {k: v for k, v in sv.items() if k != "lignes"}
    jugees = [t for t in resume["tentatives"] if t.get("passes_a_propres", 0) >= 2]
    if jugees:
        t = jugees[0]
        resume["verdict_E2"] = {"tentative": t["k"], "C2": "tient" if t["C2"]["tient"] else "tombe",
                                "cassure": resume.get("cassure", {}).get("tombe_comme_il_faut"),
                                "debit": t["verdict_debit"], "mediane_a_propres_go_s_servis": t["mediane_a_propres_go_s_servis"],
                                "seuil_go_s_servis": SEUIL_SERVIS, "temoin_debit_le_min": t["temoin_debit_le_min"]["tient"]}
    with open(os.path.join(seance, "resume.json"), "w", encoding="utf-8") as f:
        json.dump(resume, f, ensure_ascii=False, indent=1)
    print(json.dumps(resume.get("verdict_E2", resume), ensure_ascii=False, indent=1)[:4000])


if __name__ == "__main__":
    main()
