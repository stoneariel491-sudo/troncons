"""Verdicts de la séance O4 = J1 (C5, C7, C8, C10) depuis les journaux de pilote_o4.py.

Critères déclarés avant la séance : moteur/REPRISE-O.md, « O4 ». Écrit un JSON de verdicts et deux
CSV pour les figures du mémoire (passes, plancher en série par étage).

Usage : python -I -X utf8 mesures/moteur/O/analyse_o4.py --seance <nom>
"""
from __future__ import annotations

import argparse
import json
import pathlib
import statistics

RACINE = pathlib.Path(__file__).resolve().parents[3]
JOURNAUX = RACINE / "mesures/moteur/O/journaux/o4"
CSV = RACINE / "mesures/moteur/O/csv"
D_GEMV = 235.0e9   # o/s, K2 : lot de 12 matrices, 235,35 / 235,41 Go/s [mes. K, séance du 2026-10-15 20 h 24]
T0 = 0.0035        # s, coût fixe d'un jeton (07 § 1.1)
PLAFOND_VRAM = 8188 - 909  # Mio (C10)
PLAFOND_RAM = 1.9e9        # o (C7)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seance", required=True)
    a = ap.parse_args()
    pil = json.loads((JOURNAUX / f"pilote-{a.seance}.json").read_text(encoding="utf-8"))
    passes = []
    for p in pil["passes"]:
        j = json.loads(pathlib.Path(p["journal"]).read_text(encoding="utf-8"))
        passes.append((p, j))
    d_debits = [j["go_s"] * 1e9 for p, j in passes if p["lettre"] == "D"]
    d_disque = statistics.median(d_debits)
    out = {"seance": a.seance, "debit_disque_D_o_s": d_debits, "debit_disque_median_o_s": d_disque, "passes": []}
    lignes = ["passe,lettre,modele,jetons_s_generation,h_vram,octets_troncons_par_jeton,t_disque_ms,t_pcie_ms,t_dec_ms,t_gemv_ms,t0_ms,serie_jetons_s,seuil_C5,ram_pointe_o,vram_pointe_mio,octets_pdh,octets_moteur,ecart_C8,borne_C8"]
    ram = {"A120": [], "Y20": []}
    verdicts = {"C5": [], "C7": None, "C8": [], "C10": []}
    for p, j in passes:
        if p["lettre"] == "D":
            continue
        g = j["compteurs_generation"]
        n = g["pas"]
        m = j["moteur"]
        octets_jeton = g["octets_lus_troncons"] / n
        t_disque = octets_jeton / d_disque
        t_pcie = g["ms_copie_carte"] / n / 1e3
        t_dec = g["ms_decodage_carte"] / n / 1e3
        a_res = m["chargement"]["octets_tenseurs"]
        r_exp = m["k"] * m["couches"] * m["octets_emplacement"]
        t_gemv = (a_res + r_exp) / D_GEMV
        serie = 1.0 / (t_disque + t_pcie + t_dec + t_gemv + T0)
        seuil = 0.8 * serie
        js = j["generation_jetons_s"]
        rp = j["memoire"]["pointe_ensemble_travail"]
        vr = j["vram"]["pointe_mio"]
        # C8 : octets lus par le moteur (résidents par le lecteur, lignes, tronçons) contre le PDH.
        om = j["compteurs_total"]["octets_lus"]
        pdh = j["disque"]["octets_lus_pdh"]
        repos = j["disque"]["repos_octets_s"] or 0.0
        borne = repos * j["disque"]["duree_s"] + 100e6
        ecart = abs(pdh - om)
        ram[p["lettre"]].append(rp)
        if p["lettre"] == "A120":
            verdicts["C5"].append({"passe": p["passe"], "jetons_s": js, "serie": serie, "seuil": seuil, "tient": js >= seuil})
        verdicts["C8"].append({"passe": p["passe"], "pdh": pdh, "moteur": om, "ecart": ecart, "borne": borne, "tient": ecart <= borne})
        verdicts["C10"].append({"passe": p["passe"], "vram_pointe_mio": vr, "plafond": PLAFOND_VRAM, "tient": vr is not None and vr <= PLAFOND_VRAM})
        out["passes"].append({"passe": p["passe"], "lettre": p["lettre"], "jetons_s_generation": js, "h": g["h_vram"],
                              "t_ms": {"disque": t_disque * 1e3, "pcie": t_pcie * 1e3, "dec": t_dec * 1e3, "gemv": t_gemv * 1e3, "t0": T0 * 1e3},
                              "serie": serie, "seuil_C5": seuil, "ram_pointe": rp, "vram_pointe_mio": vr, "texte_sha256": j["texte_sha256"]})
        lignes.append(f"{p['passe']},{p['lettre']},{m['fichier'].split('/')[-1]},{js:.6f},{g['h_vram']:.6f},{octets_jeton:.0f},{t_disque*1e3:.4f},{t_pcie*1e3:.4f},{t_dec*1e3:.4f},{t_gemv*1e3:.4f},{T0*1e3:.4f},{serie:.6f},{seuil:.6f},{rp},{vr},{pdh:.0f},{om},{ecart:.0f},{borne:.0f}")
    bruit = max(max(v) - min(v) for v in ram.values() if len(v) >= 2)
    m120, m20 = statistics.median(ram["A120"]), statistics.median(ram["Y20"])
    verdicts["C7"] = {"pointes_120b": ram["A120"], "pointes_20b": ram["Y20"], "max_120b": max(ram["A120"]), "plafond": PLAFOND_RAM,
                      "ecart_medianes": m120 - m20, "bruit": bruit, "borne_ecart": 2 * bruit + 0.5e6,
                      "tient_plafond": max(ram["A120"]) <= PLAFOND_RAM, "tient_ecart": abs(m120 - m20) <= 2 * bruit + 0.5e6}
    verdicts["C7"]["tient"] = verdicts["C7"]["tient_plafond"] and verdicts["C7"]["tient_ecart"]
    textes = {x["texte_sha256"] for x in out["passes"] if x["lettre"] == "A120"}
    out["textes_120b_identiques"] = len(textes) == 1
    out["verdicts"] = verdicts
    (JOURNAUX / f"verdicts-{a.seance}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    CSV.mkdir(parents=True, exist_ok=True)
    (CSV / f"o4-{a.seance}-passes.csv").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print(json.dumps(verdicts, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
