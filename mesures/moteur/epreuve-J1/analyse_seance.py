"""Analyse de la séance de l'épreuve (pilote_epreuve.py) : verdicts des seuils de seuils-declares.md.

Plancher en série de C5 : la formule du lot O (moteur/REPRISE-O.md, O4), recalculée ici avec les
grandeurs de MA séance : t_disque = octets de tronçons lus par jeton ÷ débit médian de mes D120 ;
t_pcie, t_dec = temps de carte des copies et décodages par jeton (événements du moteur) ;
t_gemv = (A + k·L·emplacement) / 235 Go/s, A = résidents lus par jeton (tous sauf token_embd) ;
T0 = 3,5 ms. Seuil : génération ≥ 0,8 × 1 / somme.
Règle de 06 § 7.5 : une différence est réelle si elle dépasse 2 × le plus grand des deux bruits et
3 % ; bruit d'une configuration = |X1 − X2| / moyenne de ses deux passes.
Commande : python -I -X utf8 analyse_seance.py <seance.json> <verdicts.json> [--csv passes.csv]
"""
import argparse
import json
import statistics



def bruit(xs):
    return abs(xs[0] - xs[1]) / statistics.mean(xs) if len(xs) >= 2 else None


def reel(a, b, ba, bb):
    """La différence entre les moyennes a et b est-elle réelle (06 § 7.5) ?"""
    d = abs(a - b) / min(a, b)
    return d > 2 * max(ba, bb) and d > 0.03, d


def principal():
    ap = argparse.ArgumentParser()
    ap.add_argument("seance")
    ap.add_argument("verdicts")
    ap.add_argument("--csv")
    ap.add_argument("--residents-120b-octets", type=float, default=1.686e9,
                    help="résidents lus par jeton (tous sauf token_embd), 120b")
    a = ap.parse_args()
    s = json.load(open(a.seance, encoding="utf-8"))
    P = s["passes_faites"]
    par = {}
    for p in P:
        par.setdefault(p["nom"], []).append(p)
    v = {"seance": s["seance"], "passes": len(P)}

    # étage disque
    d = [p["programme"]["go_s"] for p in par.get("D120", [])]
    v["D120_go_s"] = d
    d_med = statistics.median(d) if d else None

    # C5
    c5 = []
    for p in par.get("T120", []):
        j = json.load(open(p["commande"][p["commande"].index("--journal") + 1], encoding="utf-8"))
        cg = j["compteurs_generation"]
        pas = cg["pas"]
        m = j["moteur"]
        t_d = cg["octets_lus_troncons"] / pas / (d_med * 1e9)
        t_p = cg["ms_copie_carte"] / pas / 1e3
        t_c = cg["ms_decodage_carte"] / pas / 1e3
        t_g = (a.residents_120b_octets + m["k"] * m["couches"] * m["octets_emplacement"]) / 235e9
        serie = 1 / (t_d + t_p + t_c + t_g + 3.5e-3)
        c5.append({"passe": p["passe"], "gen": j["generation_jetons_s"], "h": cg["h_vram"],
                   "octets_par_jeton": cg["octets_lus_troncons"] / pas,
                   "debit_moteur_go_s": cg["octets_lus_troncons"] / cg["s_lectures"] / 1e9 if cg.get("s_lectures") else None,
                   "t_disque_ms": t_d * 1e3, "t_pcie_ms": t_p * 1e3, "t_dec_ms": t_c * 1e3,
                   "t_gemv_ms": t_g * 1e3, "plancher_serie": serie, "seuil": 0.8 * serie,
                   "tient": j["generation_jetons_s"] >= 0.8 * serie, "texte": j["texte_sha256"],
                   "mur_s": p["mur_s"], "somme_phases_s": (j["moteur"]["ouverture_s"] or 0) + j["prefill_s"] + j["generation_s"]})
    v["C5"] = c5

    def serie_de(nom, cle="gen_jetons_s"):
        return [p.get(cle) for p in par.get(nom, []) if p.get(cle) is not None]

    # vitesse : troncons contre la base, et les deux configurations de la base
    vit = {n: serie_de(n) for n in ("T120", "L120", "L120t10", "T20", "T120tiede1")}
    v["vitesse"] = {n: {"passes": x, "moyenne": statistics.mean(x) if x else None, "bruit": bruit(x)}
                    for n, x in vit.items()}
    if vit["L120"] and vit["L120t10"]:
        r, dd = reel(statistics.mean(vit["L120"]), statistics.mean(vit["L120t10"]),
                     bruit(vit["L120"]), bruit(vit["L120t10"]))
        v["base_t6_contre_t10"] = {"reelle": r, "ecart": dd}
        meilleure = max(("L120", "L120t10"), key=lambda n: statistics.mean(vit[n]))
        mt, mb = statistics.mean(vit["T120"][:2]), statistics.mean(vit[meilleure])
        bt, bb = bruit(vit["T120"][:2]), bruit(vit[meilleure])
        v["C6"] = {"meilleure_base": meilleure, "troncons": mt, "base": mb, "rapport": mt / mb,
                   "seuil_relatif": 2 * max(bt, bb) + 0.03, "tient": (mt / mb - 1) > 2 * max(bt, bb) + 0.03}

    # mémoire
    mem = {}
    for n, ps in par.items():
        if n == "D120":
            continue
        mem[n] = [{"passe": p["passe"],
                   "pointe_et_os_mo": p["memoire_os"]["pointe_ensemble_travail"] / 1e6,
                   "pointe_engagee_os_mo": p["memoire_os"]["pointe_engagee_privee"] / 1e6,
                   "perte_machine_mo": p["perte_machine_mo"], "dispo_repos_mo": p["dispo_repos_mo"],
                   "vram_pointe_mio": p["vram_pointe_mio"], "vram_repos_mio": p["vram_repos_mio"],
                   "pointe_et_programme_mo": (p["programme"].get("memoire") or {}).get("pointe_ensemble_travail", 0) / 1e6
                   if p["sorte"] == "troncons" else None,
                   "texte": p.get("texte_sha256"), "alim": [p["alimentation_avant"], p["alimentation_apres"]],
                   "etrangers": p["etrangers_avant"]} for p in ps]
    v["memoire"] = mem
    t120 = [m["pointe_et_os_mo"] for m in mem.get("T120", [])]
    t20 = [m["pointe_et_os_mo"] for m in mem.get("T20", [])]
    if t120 and t20:
        b = max(max(t120) - min(t120), max(t20) - min(t20))
        ecart = statistics.median(t120) - statistics.median(t20)
        v["C7"] = {"plafond_tient": max(t120) <= 1900, "pointe_120b_max_mo": max(t120),
                   "ecart_120b_20b_mo": ecart, "bruit_mo": b, "borne_mo": 2 * b + 0.5,
                   "ecart_tient": abs(ecart) <= 2 * b + 0.5}
    if mem.get("T120tiede1") and t120:
        voisin = mem["T120"][-1]["pointe_et_os_mo"]
        dt = mem["T120tiede1"][0]["pointe_et_os_mo"] - voisin
        v["tiede_1gio"] = {"ecart_mo": dt, "attendu_mo": 1073.7, "rapport": dt / 1073.7,
                           "tient": 0.9 <= dt / 1073.7 <= 1.1}
    vr = [m["vram_pointe_mio"] for n in ("T120", "T20", "T120tiede1") for m in mem.get(n, [])]
    v["C10"] = {"vram_pointe_max_mio": max(vr) if vr else None, "tient": max(vr) <= 7279 if vr else None}
    textes = {n: sorted({m["texte"] for m in mem.get(n, [])}) for n in mem}
    v["textes"] = textes
    json.dump(v, open(a.verdicts, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if a.csv:
        cols = ["passe", "nom", "gen_jetons_s", "pointe_et_os_mo", "pointe_engagee_os_mo",
                "perte_machine_mo", "vram_pointe_mio", "mur_s"]
        lignes = [",".join(cols)]
        for p in P:
            mo = p.get("memoire_os") or {}
            lignes.append(",".join(str(x) for x in [
                p["passe"], p["nom"], p.get("gen_jetons_s", p["programme"].get("go_s") if p["sorte"] == "disque" else ""),
                mo.get("pointe_ensemble_travail", 0) / 1e6, mo.get("pointe_engagee_privee", 0) / 1e6,
                p["perte_machine_mo"], p["vram_pointe_mio"], round(p["mur_s"], 1)]))
        open(a.csv, "w", encoding="utf-8").write("\n".join(lignes) + "\n")
    print(json.dumps({k: v[k] for k in v if k not in ("memoire",)}, ensure_ascii=False, indent=1)[:6000])


if __name__ == "__main__":
    principal()
