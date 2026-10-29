"""Analyse des séances du placement disque, aux seuils déclarés (08 § 2.1).

  python -I -X utf8 outils/disque/placement/analyse.py <seance> [<seance> …]

Pour chaque séance : les passes `troncons disque` (médianes par fichier, e_soi, S, verdicts deux à deux),
les passes lire.py (débit, octets lus par le disque selon SMART sur octets demandés, température), et pour
les profils complets (plan « tout ») : débit par lecture le long du fichier, par bande de LCN (H2), par
nombre de morceaux (H1), seuil S_b par moitiés tirées au hasard (200 tirages, graine 20261022).
Écrit mesures/disque/placement/<seance>/analyse.json et <seance>/profil-<fichier>.csv (débit par
fenêtre de 256 Mio du fichier, pour les figures).
"""
import csv
import json
import pathlib
import random
import re
import statistics
import sys

R = pathlib.Path(__file__).resolve().parents[3]
OUT = R / "mesures/disque/placement"
S_HIST = 0.118  # 2 × 5,9 % (B120, s2) : plancher déclaré de S


def rangs(v):
    o = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
            j += 1
        for k in range(i, j + 1):
            r[o[k]] = (i + j) / 2
        i = j + 1
    return r


def spearman(x, y):
    rx, ry = rangs(x), rangs(y)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else 0.0


def seuil_b(debits, n_tirages=200, graine=20261022):
    rnd = random.Random(graine)
    ecarts = []
    for _ in range(n_tirages):
        v = debits[:]
        rnd.shuffle(v)
        m = len(v) // 2
        ecarts.append(abs(statistics.median(v[:m]) / statistics.median(v[m:]) - 1))
    ecarts.sort()
    return max(2 * ecarts[int(0.95 * len(ecarts)) - 1], 0.05)


def cle_de(fichier):
    nom = fichier.split("/")[-1]
    return {"gpt-oss-120b.trc": "A120", "gpt-oss-120b-v12.trc": "B120", "gpt-oss-120b-v10-recode.trc": "C120",
            "gpt-oss-20b.trc": "A20", "gpt-oss-20b-v12.trc": "B20", "D20.trc": "D20", "E20.trc": "E20", "F20.trc": "F20", "G20a.trc": "G20a", "G20b.trc": "G20b"}.get(nom, nom)


def lire_csv(p):
    with open(p, newline="", encoding="utf-8") as f:
        return [{k: (float(v) if k in ("lcn_frac", "debut_us", "fin_us") else int(v)) for k, v in r.items()} for r in csv.DictReader(f)]


def profil(lignes):
    """H1, H2 et le débit le long du fichier, sur un profil complet."""
    for l in lignes:
        l["debit"] = l["longueur"] / (l["fin_us"] - l["debut_us"]) / 1e3  # Go/s (octets / µs / 1e3)
    d = [l["debit"] for l in lignes]
    sb = seuil_b(d)
    haut = [l["debit"] for l in lignes if l["lcn_frac"] > 0.75]
    bas = [l["debit"] for l in lignes if l["lcn_frac"] < 0.5]
    un = [l["debit"] for l in lignes if l["morceaux"] == 1]
    dix = [l["debit"] for l in lignes if l["morceaux"] >= 10]
    r = {"lectures": len(lignes), "debit_par_lecture_median": statistics.median(d), "S_b": sb,
         "rho_lcn": spearman([l["lcn_frac"] for l in lignes], d),
         "rho_decalage": spearman([l["decalage"] for l in lignes], d),
         "rho_morceaux": spearman([l["morceaux"] for l in lignes], d),
         "bande_haute_n": len(haut), "bande_basse_n": len(bas),
         "rapport_haute_sur_basse": (statistics.median(haut) / statistics.median(bas)) if haut and bas else None,
         "un_morceau_n": len(un), "dix_morceaux_ou_plus_n": len(dix),
         "rapport_un_sur_dix": (statistics.median(un) / statistics.median(dix)) if un and dix else None}
    # H1 : t(n) = t1 + (n − 1) τ, moindres carrés sur les lectures paires, prédiction des impaires.
    pts = [((l["morceaux"] - 1), (l["fin_us"] - l["debut_us"]) / l["longueur"] * 12e6) for l in lignes]  # durée ramenée à 12 Mo
    pair, impair = pts[0::2], pts[1::2]
    if len({x for x, _ in pair}) > 1:
        mx, my = statistics.mean(x for x, _ in pair), statistics.mean(y for _, y in pair)
        tau = sum((x - mx) * (y - my) for x, y in pair) / sum((x - mx) ** 2 for x, _ in pair)
        t1 = my - tau * mx
        pred = sum(t1 + tau * x for x, _ in impair)
        mes = sum(y for _, y in impair)
        r.update({"h1_t1_us_12mo": t1, "h1_tau_us_par_morceau": tau, "h1_prediction_impaires_sur_mesure": pred / mes})
    # le long du fichier : fenêtres de 256 Mio
    fen = {}
    for l in lignes:
        fen.setdefault(l["decalage"] >> 28, []).append(l)
    r["fenetres"] = [{"debut_gio": k / 4, "n": len(v), "debit_median": statistics.median(x["debit"] for x in v),
                      "lcn_median": statistics.median(x["lcn_frac"] for x in v), "morceaux": sum(x["morceaux"] for x in v)}
                     for k, v in sorted(fen.items())]
    return r


def main():
    tout = {}
    for seance in sys.argv[1:]:
        d = OUT / seance
        res = json.loads((d / f"seance-{seance}.json").read_text(encoding="utf-8"))
        passes = res["passes"]
        a = {"seance": seance, "debut": res["debut"], "fin": res.get("fin"), "sous_charge": [p["nom"] for p in passes if p["sous_charge"]]}
        # troncons disque
        td = {}
        for p in passes:
            if re.search(r"-\d\d-disque-", p["nom"]):
                j = json.loads((d / f"{p['nom']}.json").read_text(encoding="utf-8"))
                td.setdefault(cle_de(j["fichier"]), []).append({"go_s": j["go_s"], "nom": p["nom"], "charge": p["sous_charge"],
                                                               "temp": (p["smart_avant"].get("temperature_c"), p["smart_apres"].get("temperature_c")),
                                                               "disque_sur_demande": (p["smart_ecart"] or {}).get("octets_lus_disque", 0) / j["octets"],
                                                               "mediane_us": j["duree_us_mediane"], "p90_us": j["duree_us_p90"]})
        if td:
            e_soi = {k: (max(x["go_s"] for x in v) - min(x["go_s"] for x in v)) / statistics.mean(x["go_s"] for x in v) for k, v in td.items()}
            S = max(2 * max(e_soi.values()), S_HIST)
            med = {k: statistics.median(x["go_s"] for x in v) for k, v in td.items()}
            paires = {}
            cles = sorted(med)
            for i, x in enumerate(cles):
                for y in cles[i + 1:]:
                    r = med[y] / med[x]
                    paires[f"{y}/{x}"] = {"rapport": r, "verdict": "diffèrent" if abs(r - 1) > S else ("égaux" if abs(r - 1) < S / 2 else "entre deux")}
            a["troncons_disque"] = {"passes": td, "mediane_go_s": med, "e_soi": e_soi, "S": S, "paires": paires}
        # lire.py
        lp = {}
        for p in passes:
            if "-lire-" in p["nom"]:
                jp = d / f"{p['nom']}.json"
                if not jp.exists():
                    continue
                j = json.loads(jp.read_text(encoding="utf-8"))
                lp.setdefault((j["plan"], cle_de(j["fichier"])), []).append(
                    {"nom": p["nom"], "go_s": j["go_s"], "charge": p["sous_charge"], "disque_sur_demande": j.get("octets_disque_sur_demandes"),
                     "temp": (j["smart_ecart"] or {}).get("temp_avant"), "temoin": j.get("temoin"), "n": j["n"]})
        a["lire"] = {f"{k[0]}:{k[1]}": v for k, v in lp.items()}
        # témoin de lire.py contre troncons disque (même série, plan disque)
        if td:
            a["temoin_lire_contre_troncons"] = {k: statistics.median(x["go_s"] for x in lp[("disque", k)]) / a["troncons_disque"]["mediane_go_s"][k]
                                               for k in a["troncons_disque"]["mediane_go_s"] if ("disque", k) in lp}
        # H4 : trié contre aléatoire
        h4 = {}
        for (plan, k), v in lp.items():
            if plan == "trie" and ("disque", k) in lp:
                h4[k] = statistics.median(x["go_s"] for x in v) / statistics.median(x["go_s"] for x in lp[("disque", k)])
        a["h4_trie_sur_aleatoire"] = h4
        # profils
        prof = {}
        for p in passes:
            if "-lire-tout-" in p["nom"]:
                k = p["nom"].split("-lire-tout-")[1]
                c = d / f"{p['nom']}.csv"
                if c.exists():
                    prof.setdefault(k, []).append((p["nom"], profil(lire_csv(c))))
        a["profils"] = {}
        for k, v in prof.items():
            a["profils"][k] = [{"nom": n, **{x: y for x, y in r.items() if x != "fenetres"}} for n, r in v]
            with open(d / f"profil-{k}.csv", "w", newline="", encoding="utf-8") as g:
                w = csv.writer(g)
                w.writerow(["passe", "debut_gio", "n", "debit_median_go_s", "lcn_median", "morceaux"])
                for n, r in v:
                    for f in r["fenetres"]:
                        w.writerow([n, f["debut_gio"], f["n"], round(f["debit_median"], 4), round(f["lcn_median"], 5), f["morceaux"]])
        (d / "analyse.json").write_text(json.dumps(a, ensure_ascii=False, indent=1), encoding="utf-8")
        tout[seance] = a
        print("sous charge :", a["sous_charge"])
        if "troncons_disque" in a:
            t = a["troncons_disque"]
            print("troncons disque, médianes :", {k: round(v, 3) for k, v in t["mediane_go_s"].items()}, "e_soi", {k: round(v, 4) for k, v in t["e_soi"].items()}, "S", round(t["S"], 4))
            for k, v in t["paires"].items():
                print("  ", k, round(v["rapport"], 4), v["verdict"])
            print("témoin lire/troncons :", {k: round(v, 4) for k, v in a.get("temoin_lire_contre_troncons", {}).items()})
        for k, v in a["lire"].items():
            print("lire", k, [round(x["go_s"], 3) for x in v], "disque/demande", [round(x["disque_sur_demande"] or 0, 4) for x in v], [x["temoin"] for x in v if x["temoin"]])
        print("H4 trié/aléatoire :", {k: round(v, 4) for k, v in a["h4_trie_sur_aleatoire"].items()})
        for k, v in a["profils"].items():
            for x in v:
                print("profil", k, {y: (round(z, 4) if isinstance(z, float) else z) for y, z in x.items()})


if __name__ == "__main__":
    main()
