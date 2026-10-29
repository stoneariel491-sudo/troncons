"""Analyse de la séance « vitesse » de la ronde de corrections (blocs 3 et 5 de seuils-declares.md).

- C5 pour chaque passe T120* : la formule du lot O (REPRISE-O, O4) recalculée avec les grandeurs de la
  séance, comme le juge (`analyse_seance.py`), à une différence près, la correction du constat m1 :
  la première passe D (échauffement) est **jetée**, le débit du disque est celui des D gardées.
- Garde (bloc 3) : T120g contre T120s ; KV f32 (bloc 5) : T120k contre les T120g de la même moitié
  de séance. Règle de 06 § 7.5 : réelle si l'écart dépasse 2 × le plus grand bruit et 3 %.

Commande : python -I -X utf8 analyse_ronde.py <seance.json> <verdicts.json> --csv <passes.csv>
"""
import argparse
import json
import statistics


def bruit(xs):
    return abs(xs[0] - xs[1]) / statistics.mean(xs) if len(xs) >= 2 else None


def comparer(a, b):
    ma, mb = statistics.mean(a), statistics.mean(b)
    ba, bb = bruit(a), bruit(b)
    d = (mb - ma) / ma
    return {"A": a, "B": b, "moyenne_A": ma, "moyenne_B": mb, "bruit_A": ba, "bruit_B": bb, "ecart_B_sur_A": d,
            "seuil": 2 * max(ba, bb) + 0.03 if ba is not None and bb is not None else None,
            "reel": abs(d) > 2 * max(ba, bb) and abs(d) > 0.03 if ba is not None and bb is not None else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seance")
    ap.add_argument("verdicts")
    ap.add_argument("--csv")
    ap.add_argument("--residents-120b-octets", type=float, default=1.686e9)
    a = ap.parse_args()
    s = json.load(open(a.seance, encoding="utf-8"))
    P = s["passes_faites"]
    D = [p for p in P if p["nom"] == "D120"]
    d_gardees = [p["programme"]["go_s"] for p in D[1:]]
    v = {"seance": s["seance"], "exe_sha256": s.get("exe_sha256"), "D120_go_s_toutes": [p["programme"]["go_s"] for p in D],
         "D120_jetee": D[0]["programme"]["go_s"] if D else None, "D120_gardees": d_gardees,
         "D120_p90_ms": [p["programme"]["duree_us_p90"] / 1e3 for p in D]}
    d_med = statistics.median(d_gardees)
    lignes = []
    for p in P:
        if p["sorte"] != "troncons":
            continue
        j = json.load(open(p["commande"][p["commande"].index("--journal") + 1], encoding="utf-8"))
        cg, m = j["compteurs_generation"], j["moteur"]
        pas = cg["pas"]
        t_d = cg["octets_lus_troncons"] / pas / (d_med * 1e9)
        t_p = cg["ms_copie_carte"] / pas / 1e3
        t_c = cg["ms_decodage_carte"] / pas / 1e3
        t_g = (a.residents_120b_octets + m["k"] * m["couches"] * m["octets_emplacement"]) / 235e9
        serie = 1 / (t_d + t_p + t_c + t_g + 3.5e-3)
        ct = j["compteurs_total"]
        lignes.append({
            "passe": p["passe"], "nom": p["nom"], "gen": j["generation_jetons_s"], "prefill": j["prefill_jetons_s"],
            "ouverture_s": m["ouverture_s"], "h": cg["h_vram"], "emplacements": m["emplacements"],
            "octets_vram_moteur": m["octets_vram_moteur"], "garde": m.get("garde"), "kv_f32": m.get("kv_f32"),
            "garde_attente_ms_par_jeton": cg.get("garde_attente_s", 0) / pas * 1e3,
            "garde_go_par_jeton": cg.get("garde_octets", 0) / pas / 1e9,
            "garde_troncons_generation": cg.get("garde_troncons"), "lectures_troncons_generation": cg.get("lectures_troncons"),
            "garde_lignes_total": ct.get("garde_lignes"), "garde_octets_ouverture": ct.get("garde_octets_ouverture"),
            "t_disque_ms": t_d * 1e3, "t_pcie_ms": t_p * 1e3, "t_dec_ms": t_c * 1e3, "t_gemv_ms": t_g * 1e3,
            "plancher_serie": serie, "seuil_C5": 0.8 * serie, "C5_tient": j["generation_jetons_s"] >= 0.8 * serie,
            "texte": j["texte_sha256"], "pointe_et_os_mo": p["memoire_os"]["pointe_ensemble_travail"] / 1e6,
            "pointe_engagee_os_mo": p["memoire_os"]["pointe_engagee_privee"] / 1e6, "perte_machine_mo": p["perte_machine_mo"],
            "vram_pointe_mio": p["vram_pointe_mio"], "es_os_octets_lus": (p.get("es_os") or {}).get("octets_lus"),
            "octets_comptes_moteur": (j["disque"].get("octets_comptes_moteur") or {}).get("total"),
            "pdh_octets": j["disque"].get("octets_lus_pdh"), "alim": [p["alimentation_avant"], p["alimentation_apres"]],
            "etrangers": p["etrangers_avant"], "mur_s": p["mur_s"]})
    v["passes"] = lignes
    par = {}
    for x in lignes:
        par.setdefault(x["nom"], []).append(x)
    g = par.get("T120g", [])
    v["garde"] = comparer([x["gen"] for x in g[:2]], [x["gen"] for x in par.get("T120s", [])])
    v["garde_preremplissage"] = comparer([x["prefill"] for x in g[:2]], [x["prefill"] for x in par.get("T120s", [])])
    v["garde_ouverture_s"] = {"garde": [x["ouverture_s"] for x in g[:2]], "sans": [x["ouverture_s"] for x in par.get("T120s", [])]}
    v["kv_f32"] = comparer([x["gen"] for x in g[2:4]], [x["gen"] for x in par.get("T120k", [])])
    v["kv_f32_preremplissage"] = comparer([x["prefill"] for x in g[2:4]], [x["prefill"] for x in par.get("T120k", [])])
    v["kv_f32_memoire"] = {"emplacements_f16": sorted({x["emplacements"] for x in g}), "emplacements_f32": sorted({x["emplacements"] for x in par.get("T120k", [])}),
                           "octets_vram_moteur_f16": sorted({x["octets_vram_moteur"] for x in g}),
                           "octets_vram_moteur_f32": sorted({x["octets_vram_moteur"] for x in par.get("T120k", [])}),
                           "h_f16": [x["h"] for x in g], "h_f32": [x["h"] for x in par.get("T120k", [])]}
    v["C5_tous_tiennent"] = all(x["C5_tient"] for x in lignes)
    v["C5_garde"] = [{"passe": x["passe"], "gen": x["gen"], "seuil": x["seuil_C5"], "tient": x["C5_tient"]} for x in g]
    v["textes"] = {n: sorted({x["texte"] for x in xs}) for n, xs in par.items()}
    v["C10_vram_max_mio"] = max(x["vram_pointe_mio"] for x in lignes)
    json.dump(v, open(a.verdicts, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if a.csv:
        cols = list(lignes[0].keys())
        with open(a.csv, "w", encoding="utf-8") as f:
            f.write(",".join(cols) + "\n")
            for x in lignes:
                f.write(",".join(json.dumps(x[c], ensure_ascii=False).replace(",", ";") for c in cols) + "\n")
    print(json.dumps({k: v[k] for k in v if k != "passes"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
