"""Bloc 6 de seuils-declares.md : la base llama.cpp balayée (M2), et C6 recalculé.

Lit la séance « base » (pilote_ronde.py, palindrome t6 t10 t12 t16 m m t16 t12 t10 t6 après une passe
d'échauffement jetée) et la séance « vitesse » (passes T120g de troncons). Règle de 06 § 7.5 : bruit
d'une configuration = |X₁ − X₂| / moyenne ; un écart est réel s'il dépasse 2 × le plus grand des deux
bruits et 3 %. C6 : génération moyenne des T120g ÷ la meilleure base ; tient si le rapport − 1 dépasse
2 × le plus grand bruit (T120g, meilleure base) + 3 %.

Commande : python -I -X utf8 analyse_base.py <base.json> <vitesse.json> <verdicts.json> --csv <c.csv>
"""
import argparse
import json
import statistics


def bruit(xs):
    return abs(xs[0] - xs[1]) / statistics.mean(xs) if len(xs) >= 2 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("vitesse")
    ap.add_argument("verdicts")
    ap.add_argument("--csv")
    a = ap.parse_args()
    b = json.load(open(a.base, encoding="utf-8"))
    passes = [p for p in b["passes_faites"] if p["nom"] != "Lw"]
    par = {}
    for p in passes:
        par.setdefault(p["nom"], []).append(p)
    conf = {}
    for n, ps in par.items():
        g = [p["gen_jetons_s"] for p in ps]
        pf = [p.get("prefill_jetons_s") for p in ps]
        conf[n] = {"commande": " ".join(ps[0]["commande"][1:]), "generation": g, "moyenne": statistics.mean(g), "bruit": bruit(g),
                   "preremplissage": pf, "textes": sorted({p["texte_sha256"][:8] for p in ps}),
                   "vram_pointe_mio": [p["vram_pointe_mio"] for p in ps],
                   "pointe_et_mo": [p["memoire_os"]["pointe_ensemble_travail"] / 1e6 for p in ps],
                   "alim": [[p["alimentation_avant"], p["alimentation_apres"]] for p in ps], "etrangers": [p["etrangers_avant"] for p in ps]}
    meilleure = max(conf, key=lambda n: conf[n]["moyenne"])
    duels = {}
    for n in conf:
        if n == meilleure:
            continue
        d = (conf[meilleure]["moyenne"] - conf[n]["moyenne"]) / conf[n]["moyenne"]
        s = 2 * max(conf[meilleure]["bruit"], conf[n]["bruit"]) + 0.03
        duels[n] = {"ecart_meilleure_sur_elle": d, "seuil": s, "reel": d > s}
    v = json.load(open(a.vitesse, encoding="utf-8"))
    t = [x["gen"] for x in v["passes"] if x["nom"] == "T120g"]
    mt, bt = statistics.mean(t), max(bruit(t[:2]), bruit(t[2:4])) if len(t) >= 4 else bruit(t)
    mb, bb = conf[meilleure]["moyenne"], conf[meilleure]["bruit"]
    r = {"configurations": conf, "meilleure": meilleure, "duels_contre_la_meilleure": duels,
         "C6": {"troncons_T120g": t, "troncons_moyenne": mt, "troncons_bruit": bt, "base": mb, "base_bruit": bb,
                "rapport": mt / mb, "seuil_relatif": 2 * max(bt, bb) + 0.03, "tient": (mt / mb - 1) > 2 * max(bt, bb) + 0.03},
         "C6_contre_fit_t6": mt / conf["L6"]["moyenne"] if "L6" in conf else None,
         "echauffement_jete": [p["gen_jetons_s"] for p in b["passes_faites"] if p["nom"] == "Lw"]}
    json.dump(r, open(a.verdicts, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if a.csv:
        with open(a.csv, "w", encoding="utf-8") as f:
            f.write("passe,nom,generation_j_s,preremplissage_j_s,texte,vram_pointe_mio,pointe_et_mo,mur_s\n")
            for p in b["passes_faites"]:
                f.write(f"{p['passe']},{p['nom']},{p.get('gen_jetons_s')},{p.get('prefill_jetons_s')},{p['texte_sha256'][:16]},"
                        f"{p['vram_pointe_mio']},{p['memoire_os']['pointe_ensemble_travail'] / 1e6:.1f},{p['mur_s']:.1f}\n")
    print(json.dumps({k: r[k] for k in r if k != "configurations"}, ensure_ascii=False, indent=1))
    for n, c in conf.items():
        print(n, round(c["moyenne"], 4), round(c["bruit"], 4), c["textes"])


if __name__ == "__main__":
    main()
