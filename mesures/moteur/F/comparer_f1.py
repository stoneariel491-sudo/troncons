"""Juge des taux du lot F contre les seuils déclarés (mesures/moteur/F/00-seuils-declares.md).

- 20b : les 12 tenseurs de F1 (couches 0, 8, 16, 23) comparés à la mesure de l'arbitre
  (decisions/journaux/arbitre/decoupe-gptoss20b.json) : octets des codes et de δ par tenseur
  (au millionième de bit par poids, la précision publiée), total A_ctx (médianes et tables
  comptées comme F1 : 4 tables de 512 octets par tenseur), tailles de tronçon exactes ;
  puis r_03 de tout le modèle contre 1,1037 (étude 03) à 0,1 %.
- 120b : r_03 contre 1,1026 à 0,1 %.

Lit le journal de `trc-codeur verifier` (les octets viennent du fichier .trc lui-même).
Écrit un CSV par tenseur et rend un verdict JSON.

Usage : python -I -X utf8 comparer_f1.py 20b <verifier-20b.json> <sortie.csv>
        python -I -X utf8 comparer_f1.py 120b <verifier-120b.json> <sortie.csv>
"""
import csv, json, sys

RACINE = "~/dev/active/troncons"
ROLES = ["ffn_gate_exps", "ffn_up_exps", "ffn_down_exps"]
R03 = {"20b": 1.1037, "120b": 1.1026}

modele, chemin, sortie = sys.argv[1], sys.argv[2], sys.argv[3]
v = json.load(open(chemin, encoding="utf-8"))
verdict = {"modele": modele, "journal": chemin}
r03 = v["taux"]["r_03"]
verdict["r_03"] = r03
verdict["r_03_reference"] = R03[modele]
verdict["r_03_ecart_relatif"] = r03 / R03[modele] - 1
verdict["r_03_tient"] = abs(r03 / R03[modele] - 1) <= 0.001
lignes = []
if modele == "20b":
    f1 = json.load(open(f"{RACINE}/decisions/journaux/arbitre/decoupe-gptoss20b.json", encoding="utf-8"))
    ref = {t["nom"]: t for t in f1["tenseurs"]}
    couches = f1["couches"]
    s_poids = s_codes = s_delta = s_med = 0
    tous_egaux = True
    for t in v["par_tenseur"]:
        if t["couche"] not in couches:
            continue
        nom = f"blk.{t['couche']}.{ROLES[t['matrice']]}.weight"
        r = ref[nom]
        assert r["poids"] == t["poids"], (nom, r["poids"], t["poids"])
        nous = round(t["octets_codes"] * 8 / t["poids"], 6)
        egal = nous == r["bpp_a_ctx"]
        tous_egaux &= egal
        lignes.append({"tenseur": nom, "poids": t["poids"], "octets_codes": t["octets_codes"], "bpp_codes_trc": f"{nous:.6f}", "bpp_a_ctx_F1": f"{r['bpp_a_ctx']:.6f}", "egal": egal, "octets_delta": t["octets_delta"], "bpp_delta_trc": f"{t['octets_delta'] * 8 / t['poids']:.6f}", "bpp_delta_F1": f"{r['bpp_delta']:.6f}"})
        s_poids += t["poids"]; s_codes += t["octets_codes"]; s_delta += t["octets_delta"]; s_med += t["octets_medianes"]
    bpp = lambda o: round(o * 8 / s_poids, 6)
    a_ctx = bpp(s_delta + s_codes + s_med + 12 * 4 * 512)
    verdict["f1_tenseurs_egaux"] = tous_egaux
    verdict["f1_bpp_delta"] = {"trc": bpp(s_delta), "F1": f1["bpp"]["delta"], "egal": bpp(s_delta) == f1["bpp"]["delta"]}
    verdict["f1_bpp_codes"] = {"trc": bpp(s_codes), "F1": f1["bpp"]["codes_a_ctx"], "egal": bpp(s_codes) == f1["bpp"]["codes_a_ctx"]}
    verdict["f1_bpp_medianes"] = {"trc": bpp(s_med), "F1": f1["bpp"]["medianes"], "egal": bpp(s_med) == f1["bpp"]["medianes"]}
    verdict["f1_bpp_a_ctx_total"] = {"trc": a_ctx, "F1": f1["bpp"]["a_ctx"], "egal": a_ctx == f1["bpp"]["a_ctx"]}
    tc = [t for t in v["troncons_par_couche"] if t["couche"] in couches]
    moy = sum(t["moyen"] for t in tc) / len(tc)
    mn, mx = min(t["min"] for t in tc), max(t["max"] for t in tc)
    att = f1["troncon_niveau_unique_A_octets"]
    verdict["f1_troncons"] = {"trc": {"moyen": moy, "min": mn, "max": mx}, "F1": att, "egal": (moy, mn, mx) == (att["moyen"], att["min"], att["max"])}
    verdict["f1_tient"] = tous_egaux and all(verdict[k]["egal"] for k in ["f1_bpp_delta", "f1_bpp_codes", "f1_bpp_medianes", "f1_bpp_a_ctx_total", "f1_troncons"])
with open(sortie, "w", newline="", encoding="utf-8") as fh:
    if lignes:
        w = csv.DictWriter(fh, fieldnames=list(lignes[0].keys()))
        w.writeheader(); w.writerows(lignes)
    else:
        w = csv.writer(fh)
        w.writerow(["couche", "matrice", "poids", "octets_codes", "octets_delta", "octets_medianes", "bpp_codes", "bpp_delta"])
        for t in v["par_tenseur"]:
            w.writerow([t["couche"], t["matrice"], t["poids"], t["octets_codes"], t["octets_delta"], t["octets_medianes"], f"{t['bpp_codes']:.6f}", f"{t['bpp_delta']:.6f}"])
print(json.dumps(verdict, indent=2, ensure_ascii=False))
