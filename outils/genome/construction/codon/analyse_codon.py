"""Analyse du lot A (codon) : tailles v1.2 contre v1.0, et verdicts du J1 ABBA.

Tout chiffre vient des journaux commités ; rien n'est recopié à la main.

  python -I -X utf8 outils/genome/construction/codon/analyse_codon.py tailles
      Lit les journaux `verifier` du lot F (v1.0 : mesures/moteur/F/journaux/verifier-{20b,120b}.json) et
      du lot A (v1.2 : mesures/genome/construction/codon/journaux/verifier-{20b,120b}-v12.json) ; écrit
      mesures/genome/construction/codon/tailles-par-tenseur.csv (une ligne par modèle, couche, matrice :
      bits par poids des codes en v1.0 et v1.2, gain, part des −0) et tailles.json (totaux, gain par poids
      d'expert sur les octets de tronçons, fichier, critère A-C2 ≥ 0,12 bit, prédiction du cahier).
      Témoin : la somme des octets de codes par tenseur égale le total du journal (deux chemins).
  python -I -X utf8 outils/genome/construction/codon/analyse_codon.py j1 --seance s1 [--phase j1|j1-copie]
      Lit les 8 passes `mesurer` de la phase ; écrit <phase>-<seance>-passes.csv et -verdicts.json selon
      les seuils déclarés dans pilote_codon.py (j1 : v1.0 d'origine contre v1.2 ; j1-copie : copie neuve du
      v1.0 contre v1.2).
  python -I -X utf8 outils/genome/construction/codon/analyse_codon.py disque --seance s1
      Lit les 6 passes `disque` (A B C C B A) ; écrit disque-<seance>.csv et .json (Go/s par fichier).
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import statistics
import sys

RACINE = pathlib.Path(__file__).resolve().parents[4]
F = RACINE / "mesures/moteur/F/journaux"
J = RACINE / "mesures/genome/construction/codon/journaux"
SORTIE = RACINE / "mesures/genome/construction/codon"


def charger(p: pathlib.Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def tailles(casser: bool) -> int:
    lignes, totaux = [], {}
    for m in ("20b", "120b"):
        v10 = charger(F / f"verifier-{m}.json")
        v12 = charger(J / f"verifier-{m}-v12.json")
        c12 = charger(J / f"coder-{m}-v12.json")
        assert v12["canonique"] is True and v10.get("version", [1, 0]) == [1, 0], m
        fondus = {(d["couche"], d["matrice"]): d["fondus"] for d in c12["demi_octets_8_fondus"]["par_tenseur"]}
        t10 = {(d["couche"], d["matrice"]): d for d in v10["par_tenseur"]}
        somme10 = somme12 = 0
        for d in v12["par_tenseur"]:
            k = (d["couche"], d["matrice"])
            a = t10[k]
            if casser and k == (0, 0):
                d = dict(d, octets_codes=d["octets_codes"] + 1)
            somme10 += a["octets_codes"]
            somme12 += d["octets_codes"]
            lignes.append({"modele": m, "couche": k[0], "matrice": k[1], "poids": d["poids"],
                           "bpp_codes_v10": a["bpp_codes"], "bpp_codes_v12": d["octets_codes"] * 8 / d["poids"],
                           "gain_bits": (a["octets_codes"] - d["octets_codes"]) * 8 / d["poids"],
                           "part_moins_zero": fondus[k] / d["poids"], "bpp_delta": d["bpp_delta"]})
        # Témoin à deux chemins : somme par tenseur = total du journal.
        assert somme10 == v10["taux"]["octets_flux"]["codes"], (m, "v1.0")
        if somme12 != v12["taux"]["octets_flux"]["codes"]:
            print(f"témoin des sommes TOMBE ({m}) : {somme12} contre {v12['taux']['octets_flux']['codes']}", file=sys.stderr)
            return 1
        poids = sum(x["poids"] for x in lignes if x["modele"] == m)
        tr10, tr12 = v10["troncon_octets"]["total"], v12["troncon_octets"]["total"]
        totaux[m] = {
            "poids_experts": poids,
            "bpp_total_03_v10": v10["taux"]["bpp_total_03"], "bpp_total_03_v12": v12["taux"]["bpp_total_03"],
            "gain_bpp_flux": v10["taux"]["bpp_total_03"] - v12["taux"]["bpp_total_03"],
            "octets_troncons_v10": tr10, "octets_troncons_v12": tr12,
            "gain_bpp_troncons": (tr10 - tr12) * 8 / poids, "gain_octets_troncons": tr10 - tr12,
            "rapport_troncons": tr12 / tr10,
            "fichier_v10": v10["taille_trc"], "fichier_v12": v12["taille_trc"], "gain_fichier": v10["taille_trc"] - v12["taille_trc"],
            "troncon_max_v10": v10["troncon_octets"]["max"], "troncon_max_v12": v12["troncon_octets"]["max"],
            "moins_zero_fondus": c12["demi_octets_8_fondus"]["total"], "part_moins_zero": c12["demi_octets_8_fondus"]["part_des_poids"],
            "moins_zero_du_gguf_verifier": v12.get("demi_octets_8_du_gguf"),
            "C1_v12": v12["C1"], "experts_exacts_v12": v12["experts_exacts"], "experts": v12["experts"],
            "A_C2_seuil_bits": 0.12, "A_C2": (tr10 - tr12) * 8 / poids >= 0.12,
        }
    with open(SORTIE / "tailles-par-tenseur.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0].keys()))
        w.writeheader()
        w.writerows(lignes)
    (SORTIE / "tailles.json").write_text(json.dumps({"outil": "outils/genome/construction/codon/analyse_codon.py tailles", "totaux": totaux}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(totaux, ensure_ascii=False, indent=1))
    return 0


def disque(seance: str) -> int:
    lignes = []
    for i, l in enumerate(["A", "B", "C", "C", "B", "A"], 1):
        d = charger(J / f"{seance}-disque-{i}-{l}.json")
        lignes.append({"passe": i, "fichier": l, "go_s": d["go_s"], "octets": d["octets"], "secondes": d["secondes"],
                       "duree_us_mediane": d["duree_us_mediane"], "duree_us_p90": d["duree_us_p90"], "chemin": d["fichier"]})
    with open(SORTIE / f"disque-{seance}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0].keys()))
        w.writeheader()
        w.writerows(lignes)
    par = {l: [x["go_s"] for x in lignes if x["fichier"] == l] for l in "ABC"}
    ecart_paire = max(max(v) - min(v) for v in par.values())
    v = {"seance": seance, "go_s": par, "moyennes": {l: statistics.mean(x) for l, x in par.items()}, "ecart_max_d_une_paire": ecart_paire,
         "A_plus_lent_que_C": statistics.mean(par["C"]) - statistics.mean(par["A"]) > 2 * ecart_paire,
         "B_egal_C": abs(statistics.mean(par["B"]) - statistics.mean(par["C"])) <= 2 * ecart_paire}
    (SORTIE / f"disque-{seance}.json").write_text(json.dumps(v, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(v, ensure_ascii=False, indent=1))
    return 0


def j1(seance: str, phase: str) -> int:
    plan = ["A", "B", "B", "A", "A", "B", "B", "A"]
    passes = []
    for i, l in enumerate(plan, 1):
        d = charger(J / f"{seance}-{phase}-{i}-{l}.json")
        g = d["compteurs_generation"]
        passes.append({"passe": i, "fichier": l, "jetons_s": d["generation_jetons_s"], "prefill_jetons_s": d.get("prefill_jetons_s"),
                       "octets_troncons_par_jeton": g["octets_lus_troncons"] / g["pas"], "defauts_par_jeton": g["defauts_disque"] / g["pas"],
                       "h_vram": g["h_vram"], "emplacements": g["emplacements"], "s_lectures_par_jeton": g["s_lectures"] / g["pas"],
                       "ms_decodage_par_jeton": g["ms_decodage_carte"] / g["pas"],
                       "debit_lecture_go_s": g["octets_lus_troncons"] / g["s_lectures"] / 1e9 if g["s_lectures"] else None, "ms_copie_par_jeton": g["ms_copie_carte"] / g["pas"],
                       "pointe_ensemble_travail": d["memoire"]["pointe_ensemble_travail"], "vram_pointe_mio": d["vram"]["pointe_mio"], "octets_pdh": d["disque"]["octets_lus_pdh"],
                       "jetons": d["jetons"], "texte_sha256": d["texte_sha256"]})
    with open(SORTIE / f"{phase}-{seance}-passes.csv", "w", newline="", encoding="utf-8") as f:
        cles = [k for k in passes[0] if k != "jetons"]
        w = csv.DictWriter(f, fieldnames=cles)
        w.writeheader()
        for p in passes:
            w.writerow({k: p[k] for k in cles})
    A = [p for p in passes if p["fichier"] == "A"]
    B = [p for p in passes if p["fichier"] == "B"]
    mA, mB = statistics.median(p["jetons_s"] for p in A), statistics.median(p["jetons_s"] for p in B)
    sigma = statistics.stdev(p["jetons_s"] for p in A) / statistics.mean(p["jetons_s"] for p in A)
    r = mB / mA
    paires = [(1, 2), (3, 4), (5, 6), (7, 8)]
    rap = []
    for x, y in paires:
        px, py = passes[x - 1], passes[y - 1]
        a, b = (px, py) if px["fichier"] == "A" else (py, px)
        rap.append(b["jetons_s"] / a["jetons_s"])
    oA = statistics.median(p["octets_troncons_par_jeton"] for p in A)
    oB = statistics.median(p["octets_troncons_par_jeton"] for p in B)
    memA = [p["pointe_ensemble_travail"] for p in A]
    memB = [p["pointe_ensemble_travail"] for p in B]
    bruit_mem = max(max(memA) - min(memA), max(memB) - min(memB))
    v = {
        "seance": seance, "phase": phase,
        "jetons_egaux_8_passes": all(p["jetons"] == passes[0]["jetons"] for p in passes),
        "texte_sha256": sorted({p["texte_sha256"] for p in passes}),
        "jetons_s_mediane_A": mA, "jetons_s_mediane_B": mB, "r": r, "sigma_A": sigma,
        "pas_de_regression": r >= 1 - 2 * sigma, "gain_annonce": (r - 1) > 2 * sigma,
        "rapports_apparies": rap, "rapport_apparie_moyen": statistics.mean(rap), "rapport_apparie_ecart_type": statistics.stdev(rap),
        "octets_par_jeton_A": oA, "octets_par_jeton_B": oB, "rapport_octets": oB / oA,
        "memoire_mediane_A": statistics.median(memA), "memoire_mediane_B": statistics.median(memB), "bruit_memoire": bruit_mem,
        "memoire_tient": abs(statistics.median(memB) - statistics.median(memA)) <= 2 * bruit_mem + 0.5e6,
        "emplacements": sorted({p["emplacements"] for p in passes}),
        "h_vram": sorted({round(p["h_vram"], 6) for p in passes}),
    }
    (SORTIE / f"{phase}-{seance}-verdicts.json").write_text(json.dumps(v, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(v, ensure_ascii=False, indent=1))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("quoi", choices=["tailles", "j1", "disque"])
    ap.add_argument("--seance", default="s1")
    ap.add_argument("--phase", default="j1")
    ap.add_argument("--casser", action="store_true", help="tailles : fausse un octet d'un tenseur ; le témoin des sommes doit tomber")
    a = ap.parse_args()
    if a.quoi == "tailles":
        return tailles(a.casser)
    return j1(a.seance, a.phase) if a.quoi == "j1" else disque(a.seance)


if __name__ == "__main__":
    sys.exit(main())
