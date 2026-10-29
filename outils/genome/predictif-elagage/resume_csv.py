"""Table de synthèse de l'étude (CSV pour le mémoire), tirée des journaux commités, jamais de mémoire.

Pour chaque plan : bits par poids réels (taux_plan), erreur prédite (instrument du plan), erreur
d'expert mesurée sur les fenêtres 5 à 9 (sortie_experts), KL contre la référence f64 sur les mêmes
fenêtres (juge kl), et le rapport au débit réel de la base.

Utilisation : python -I resume_csv.py DOSSIER_MESURES SORTIE.csv
"""
import csv
import json
import os
import sys


def lire(chemin):
    if not os.path.exists(chemin):
        return None
    with open(chemin, encoding="utf-8-sig") as f:
        return json.load(f)


def main():
    d, sortie = sys.argv[1], sys.argv[2]
    plans = ["identite", "zero", "base", "ecsq_kappa", "ecsq_delta7", "elagage_lagrangien", "ecsq_e",
             "sens_e_q", "ecsq_kappa_t", "hebb_e", "hebb_e_lc", "hebb_d_lc"]
    sorties = {}
    for nom in ("sortie-experts-12.json", "sortie-experts-12-hebb.json"):
        j = lire(os.path.join(d, nom))
        if j:
            for p, r in j["moyenne_des_couches"].items():
                sorties[p.removeprefix("plan-12-")] = r
    base_bits = lire(os.path.join(d, "taux-plan-12-base.json"))["bpp"]["total"]
    lignes = []
    for p in plans:
        t = lire(os.path.join(d, f"taux-plan-12-{p}.json"))
        k = lire(os.path.join(d, "kl", f"kl-12-{p}-f5-9.json"))
        s = sorties.get(p)
        bits = t["bpp"]["total"] if t else None
        lignes.append({
            "plan": p,
            "bits_reels": None if bits is None else round(bits, 4),
            "rapport_base": None if bits is None else round(bits / base_bits, 4),
            "erreur_expert_mesuree": None if s is None else round(s["expert"], 5),
            "erreur_gate": None if s is None else round(s["gate"], 5),
            "erreur_up": None if s is None else round(s["up"], 5),
            "erreur_down_seul": None if s is None else round(s["down_seul"], 5),
            "kl_moyenne": None if k is None else round(k["resume"]["kl_moyenne"], 5),
            "kl_incertitude": None if k is None else round(k["resume"]["kl_incertitude"], 5),
            "meme_premier": None if k is None else round(k["resume"]["meme_premier"], 4),
        })
    with open(sortie, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0]))
        w.writeheader()
        w.writerows(lignes)
    for l in lignes:
        print(l)


if __name__ == "__main__":
    main()
