"""Analyse d'une séance E0 (journaux de banc-chemin) : verdicts contre les seuils déclarés, CSV.

Seuils déclarés avant la première séance (moteur/REPRISE-E.md, ARCHITECTURE.md § 6.5) :
  E0(b)  DMA hôte → carte depuis la mémoire épinglée ≥ 11,0 Go/s (12,2 [mes. 01] − 10 %), jugée sur
         la médiane des passes à la taille d'un tronçon (12 Mio) ;
  E1     débit du lecteur sans tampon, morceaux de 12 Mio, profondeur 4 ≥ 0,8 × 2,58 = 2,064 Go/s,
         jugé sur la médiane des passes A (profondeur 4) **propres** (octets étrangers ≤ 0,26 Go/s,
         règle déclarée le 2026-10-15 à 15 h 20, avant toute passe mesurée) ; moins de 2 passes A
         propres : « non jugé ». Ici dans la mémoire épinglée ; la mesure principale de E1 est
         `banc-chemin lecteur` (analyse_e1.py), celle-ci en est la seconde ;
  E0(c)  coût de 36 synchronisations par jeton ≤ 15,7 ms, coût = médiane(variante) −
         médiane(asynchrone), même journal ; la variante retenue est la moins chère parmi celles
         dont tous les témoins tiennent (la variante « sans vidage » est exclue : elle dépend d'un
         comportement non documenté du pilote).
Règle de différence (06 § 7.5) : deux variantes ne diffèrent que si l'écart dépasse 2 × le plus grand
bruit (écart entre passes miroirs d'une même variante) et 3 %.

Usage : python -I -X utf8 mesures/moteur/E/analyse_e0.py mesures/moteur/E/journaux/<séance>
Écrit : <séance>/resume.json et mesures/moteur/E/csv/<séance>-*.csv
"""

import csv
import glob
import json
import os
import statistics
import sys

SEUIL_DMA = 11.0
SEUIL_DISQUE = 0.8 * 2.58
SEUIL_SYNCHRO_MS = 15.7
SEUIL_ETRANGERS = 0.26
SEUIL_PROCESSEUR_AUTRES = 0.40  # règle 2 du lot E, déclarée le 2026-10-15 à 15 h 43 (REPRISE-E.md)
ICI = os.path.dirname(os.path.abspath(__file__))


def lire(chemin):
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


def ecrire_csv(chemin, lignes):
    if not lignes:
        return
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0].keys()))
        w.writeheader()
        w.writerows(lignes)


def bruit_miroir(valeurs):
    """Plus grand écart relatif entre passes miroirs (1re et dernière, 2e et avant-dernière...)."""
    n = len(valeurs)
    if n < 2:
        return None
    m = statistics.mean(valeurs)
    return max(abs(valeurs[i] - valeurs[n - 1 - i]) for i in range(n // 2)) / m


def main():
    seance = sys.argv[1].rstrip("/\\")
    nom = os.path.basename(seance)
    j = {os.path.splitext(os.path.basename(p))[0]: lire(p) for p in glob.glob(os.path.join(seance, "*.json"))
         if not p.endswith(("seance.json", "resume.json"))}
    resume = {"seance": nom, "verdicts": {}}
    csvd = os.path.join(ICI, "csv")

    # ---- (a) -----------------------------------------------------------------------------
    if "a" in j:
        lignes = []
        for t in j["a"]["resultat"].get("tailles", []):
            lignes.append({k: t.get(k) for k in ("octets", "tentee", "reussie", "duree_allocation_ms", "duree_liberation_ms",
                                                 "ram_disponible_avant_o", "ram_disponible_apres_allocation_o", "dma_fin_go_s",
                                                 "dma_fin_ecarts", "raison", "erreur")})
        ecrire_csv(os.path.join(csvd, f"{nom}-a.csv"), lignes)
        resume["a"] = lignes
        reussies = [l["octets"] for l in lignes if l.get("reussie")]
        resume["verdicts"]["a"] = {"plus_grande_reussie_o": max(reussies) if reussies else None,
                                   "non_tentees": [l["octets"] for l in lignes if not l["tentee"]],
                                   "refusees": [l["octets"] for l in lignes if l["tentee"] and not l.get("reussie")],
                                   "ecarts_dma": sum(l.get("dma_fin_ecarts") or 0 for l in lignes)}

    # ---- (b) -----------------------------------------------------------------------------
    if "b-temoin" in j:
        r = j["b-temoin"]["resultat"]["justesse"]
        resume["verdicts"]["b_temoin"] = {"morceaux": len(r["morceaux"]), "ecarts_disque": r["ecarts_disque"],
                                          "ecarts_chemin": r["ecarts_chemin"],
                                          "tient": r["ecarts_disque"] == 0 and r["ecarts_chemin"] == 0}
    if "b-casse" in j:
        r = j["b-casse"]["resultat"]["justesse"]
        resume["verdicts"]["b_cassure"] = {"ecarts_chemin": r["ecarts_chemin"], "tombe_comme_attendu": r["ecarts_chemin"] == 1}
    disque, dma = [], []
    for cle in sorted(k for k in j if k.startswith("b-") and k[2] in "AB"):
        r = j[cle]["resultat"]
        if "disque" not in r:
            continue
        d = r["disque"]
        disque.append({"passe": cle, "profondeur": d["profondeur"], "lectures": d["lectures"], "octets": d["octets"],
                       "secondes": d["secondes"], "go_s": d["go_s"], "duree_us_p10": d["duree_us_p10"],
                       "duree_us_mediane": d["duree_us_mediane"], "duree_us_p90": d["duree_us_p90"], "erreurs": d["erreurs"],
                       "ecarts_justesse": r["justesse"]["ecarts_chemin"],
                       "octets_systeme": d.get("octets_systeme"), "go_s_etrangers": d.get("go_s_etrangers"),
                       "processeur_autres": (d.get("processeur") or {}).get("autres"),
                       "propre": d.get("go_s_etrangers") is not None and d["go_s_etrangers"] <= SEUIL_ETRANGERS
                       and (d.get("processeur") or {}).get("autres", 1.0) <= SEUIL_PROCESSEUR_AUTRES})
        for p in r["dma"]["passes"]:
            dma.append({"passe": cle, "tour": p["tour"], "rang": p["rang"], "lettre": p["lettre"], "octets": p["octets"],
                        "copies": p["copies"], "ms": p["ms"], "go_s": p["go_s"],
                        "mur_ms": p.get("mur_ms"), "go_s_mur": p.get("go_s_mur")})
    for x in disque:
        # Second chemin (loi de Little, X = q·b/R) : débit prédit par la profondeur, la taille et la
        # latence médiane d'une lecture ; à comparer au débit mesuré par le mur.
        x["go_s_little"] = x["profondeur"] * (x["octets"] / x["lectures"]) / (x["duree_us_mediane"] * 1e-6) / 1e9
    if disque:
        ecrire_csv(os.path.join(csvd, f"{nom}-b-disque.csv"), disque)
        ordre = ["b-A1", "b-B1", "b-B2", "b-A2"]
        par = {x["passe"]: x["go_s"] for x in disque}
        a_vals = [par[k] for k in ("b-A1", "b-A2") if k in par]
        b_vals = [par[k] for k in ("b-B1", "b-B2") if k in par]
        bruit = max(abs(v[0] - v[1]) / statistics.mean(v) for v in (a_vals, b_vals) if len(v) == 2) if len(a_vals) == 2 else None
        a_propres = [x["go_s"] for x in disque if x["passe"] in ("b-A1", "b-A2") and x["propre"]]
        med_a = statistics.median(a_propres) if len(a_propres) >= 2 else None
        resume["verdicts"]["disque_E1"] = {
            "go_s_profondeur_4": a_vals,
            "little_go_s": {x["passe"]: x["go_s_little"] for x in disque}, "go_s_profondeur_1": b_vals, "mediane_profondeur_4": med_a,
            "mediane_profondeur_1": statistics.median(b_vals) if b_vals else None, "bruit_abba_relatif": bruit,
            "passes_a_propres": len(a_propres),
            "temoin_compteur_tient": all(x["octets_systeme"] is not None and x["octets_systeme"] >= x["octets"] for x in disque),
            "seuil": SEUIL_DISQUE, "etat": "non jugé" if med_a is None else ("tient" if med_a >= SEUIL_DISQUE else "tombe"),
            "ordre": [k for k in ordre if k in par]}
    if dma:
        ecrire_csv(os.path.join(csvd, f"{nom}-b-dma.csv"), dma)
        v = {}
        for t in sorted({x["octets"] for x in dma}):
            vals = [x["go_s"] for x in dma if x["octets"] == t]
            murs = [x["go_s_mur"] for x in dma if x["octets"] == t and x.get("go_s_mur")]
            v[str(t)] = {"n": len(vals), "mediane": statistics.median(vals), "min": min(vals), "max": max(vals),
                         "bruit_miroir_relatif": bruit_miroir(vals),
                         # second chemin : horloge de l'hôte ; témoin : jamais au-dessus des événements
                         "mediane_mur": statistics.median(murs) if murs else None,
                         "mur_au_dessus_des_evenements": sum(1 for x in dma if x["octets"] == t and x.get("go_s_mur")
                                                             and x["go_s_mur"] > x["go_s"] * 1.001)}
        petit = str(min(int(k) for k in v))
        resume["verdicts"]["dma_E0b"] = {"par_taille": v, "seuil": SEUIL_DMA, "juge_sur_octets": int(petit),
                                         "tient": v[petit]["mediane"] >= SEUIL_DMA}

    # ---- (c) -----------------------------------------------------------------------------
    lignes_c, jetons_c = [], []
    for cle in sorted(k for k in j if k.startswith("c-")):
        r = j[cle]["resultat"]
        if "passes" not in r:
            continue
        par_var = {}
        for p in r["passes"]:
            par_var.setdefault(p["variante"], []).append(p)
            lignes_c.append({"journal": cle, "rang": p["rang"], "variante": p["variante"], "ns_routeur": r["ns_routeur"],
                             "ns_expert": r["ns_expert"], "attente": r["attente_effective"],
                             "mur_ms_moyenne": p["mur_ms_moyenne"], "mur_ms_mediane": p["mur_ms_mediane"],
                             "carte_ms_moyenne": p["carte_ms_moyenne"], "faux_hote": p["faux_hote"],
                             "sequences_absentes": p["sequences_absentes"], "boites_expirees": p["boites_expirees"],
                             "erreurs_carte": p["erreurs_carte"], "carte_au_dessus_du_mur": p["carte_au_dessus_du_mur"]})
            for k, (m, c) in enumerate(zip(p["mur_ms"], p["carte_ms"])):
                jetons_c.append({"journal": cle, "rang": p["rang"], "variante": p["variante"], "jeton": k, "mur_ms": m, "carte_ms": c})
        base = statistics.median(x["mur_ms_moyenne"] for x in par_var.get("asynchrone", [])) if "asynchrone" in par_var else None
        bruit_base = bruit_miroir([x["mur_ms_moyenne"] for x in par_var.get("asynchrone", [])])
        verdict = {"ns_routeur": r["ns_routeur"], "ns_expert": r["ns_expert"], "attente": r["attente_effective"],
                   "asynchrone_ms": base, "bruit_asynchrone": bruit_base, "variantes": {}}
        for v, ps in par_var.items():
            if v == "asynchrone":
                continue
            med = statistics.median(x["mur_ms_moyenne"] for x in ps)
            temoins = all(x["faux_hote"] == 0 and x["sequences_absentes"] == 0 and x["erreurs_carte"] == 0
                          and x["carte_au_dessus_du_mur"] == 0 for x in ps)
            cout = med - base if base is not None else None
            bruit = bruit_miroir([x["mur_ms_moyenne"] for x in ps])
            plus_grand_bruit = max(b for b in (bruit, bruit_base) if b is not None) if (bruit or bruit_base) else 0.0
            verdict["variantes"][v] = {
                "mediane_ms": med, "cout_ms_par_jeton": cout, "cout_us_par_synchro": cout * 1000 / 36 if cout is not None else None,
                "bruit_miroir": bruit, "temoins_tiennent": temoins,
                "faux_hote": sum(x["faux_hote"] for x in ps), "erreurs_carte": sum(x["erreurs_carte"] for x in ps),
                "boites_expirees": sum(x["boites_expirees"] for x in ps),
                "cout_distinct_du_bruit": (cout is not None and abs(cout) > 2 * plus_grand_bruit * base and abs(cout) > 0.03 * base),
                "tient_seuil": cout is not None and cout <= SEUIL_SYNCHRO_MS and temoins}
        robustes = {v: x for v, x in verdict["variantes"].items()
                    if v not in ("boite_sans_vidage", "sans_synchro") and x["temoins_tiennent"]}
        if robustes:
            ret = min(robustes, key=lambda v: robustes[v]["cout_ms_par_jeton"])
            verdict["retenue"] = ret
            verdict["tient"] = robustes[ret]["cout_ms_par_jeton"] <= SEUIL_SYNCHRO_MS
        if "sans_synchro" in par_var:
            ps = par_var["sans_synchro"]
            verdict["cassure"] = {"faux_hote": sum(x["faux_hote"] for x in ps), "erreurs_carte": sum(x["erreurs_carte"] for x in ps),
                                  "tombe_comme_attendu": all(x["faux_hote"] > 0 and x["erreurs_carte"] > 0 for x in ps)}
        resume["verdicts"][cle] = verdict
    # Témoin du modèle D2 (E-pour-le-memoire.md § 3) : le coût d'une synchronisation ne devrait
    # pas dépendre de la durée des noyaux ; on compare le coût sous charge (50/250 µs) au coût à vide.
    v, c = resume["verdicts"].get("c-vide"), resume["verdicts"].get("c-charge")
    if v and c:
        modele = {}
        for var in sorted(set(v["variantes"]) & set(c["variantes"])):
            cv, cc = v["variantes"][var]["cout_us_par_synchro"], c["variantes"][var]["cout_us_par_synchro"]
            modele[var] = {"cout_us_vide": cv, "cout_us_charge": cc, "rapport_charge_sur_vide": cc / cv if cv else None}
        resume["verdicts"]["modele_D2"] = {"variantes": modele,
                                           "asynchrone_ms_vide": v["asynchrone_ms"], "asynchrone_ms_charge": c["asynchrone_ms"],
                                           "us_par_lancement_vide": v["asynchrone_ms"] * 1000 / 72}
    ecrire_csv(os.path.join(csvd, f"{nom}-c-passes.csv"), lignes_c)
    ecrire_csv(os.path.join(csvd, f"{nom}-c-jetons.csv"), jetons_c)

    with open(os.path.join(seance, "resume.json"), "w", encoding="utf-8") as f:
        json.dump(resume, f, ensure_ascii=False, indent=2)
    print(json.dumps(resume["verdicts"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
