"""Place chaque mécanisme mesuré sur le plan débit × erreur (la figure de synthèse du mémoire).

Lit `mesures/genome/etat-de-l-art/passes/*.json` et les journaux du codon du zéro ; écrit
`mesures/genome/etat-de-l-art/frontiere.csv` : une ligne par passe, avec le débit (H0 des symboles
plus les échelles, et H(symbole | κ) plus les échelles), l'erreur relative sur les poids (moyenne des
trois rôles), l'erreur de sortie des matrices et des experts sur l'évaluation, par moitié, et la
part des couches où l'erreur d'expert est sous celle de la frontière du même sous-ensemble.

Utilisation : python -I -X utf8 frontiere_csv.py
"""
import csv
import glob
import json
import os

ICI = os.path.dirname(os.path.abspath(__file__))
M = os.path.join(ICI, "..", "..", "..", "mesures", "genome", "etat-de-l-art")
ECHELLES = 0.0347 + 0.0028


def main():
    passes = {}
    for f in sorted(glob.glob(os.path.join(M, "passes", "*.json"))):
        passes[os.path.basename(f)[:-5]] = json.load(open(f, encoding="utf-8"))
    lignes = []
    for nom, j in passes.items():
        sous = nom.split("-e")[1] if "-e" in nom.split("damp")[1] else None
        ref = "frontiere-lam0-damp0.01" + (f"-e{sous}" if sous else "")
        jr = passes.get(ref)
        mieux = None
        if jr:
            c = [(j["err_sortie_expert_par_couche"][l][m] < jr["err_sortie_expert_par_couche"][l][m])
                 for l in j["err_sortie_expert_par_couche"] for m in ("m1", "m2")]
            mieux = sum(c) / len(c)
        lignes.append({
            "passe": nom, "variante": j["variante"], "lam": j["lam"], "damp": j["damp"],
            "experts": " ".join(str(e) for e in j["experts"]),
            "bits_H0_plus_echelles": round(j["bits_H0_sym"] + ECHELLES, 5),
            "bits_kappa_plus_echelles": round(j["bits_H_sym_kappa"] + ECHELLES, 5),
            "H_code_sachant_sym": round(j["H_code_sachant_sym"], 5),
            "err_poids": round(sum(j["err_poids"].values()) / 3, 6),
            "err_sortie_matrices": round(sum(j["err_sortie_matrice_eval"].values()) / 3, 6),
            "err_sortie_expert": round(j["err_sortie_expert_eval"], 6),
            "err_sortie_expert_m1": round(j["err_sortie_expert_moities"][0], 6),
            "err_sortie_expert_m2": round(j["err_sortie_expert_moities"][1], 6),
            "reference": ref if jr else "", "part_couches_moities_sous_frontiere": mieux,
        })
    # le codon du zéro (sans perte de valeur) et la frontière sans perte, au codeur réel
    for f, nom in (("zero-temoin-sans-drapeau.json", "sans perte F1 (A_ctx)"), ("zero-canonique.json", "codon synonyme du zero (A_ctx)")):
        p = os.path.join(M, "journaux", f)
        if os.path.exists(p):
            j = json.load(open(p, encoding="utf-8"))
            lignes.append({"passe": nom, "variante": "sans perte", "bits_H0_plus_echelles": j["bpp"]["a_ctx"],
                           "err_poids": 0.0, "err_sortie_matrices": 0.0, "err_sortie_expert": 0.0})
    cles = sorted({k for r in lignes for k in r}, key=lambda k: list(lignes[0]).index(k) if k in lignes[0] else 99)
    with open(os.path.join(M, "frontiere.csv"), "w", newline="", encoding="utf-8") as fo:
        w = csv.DictWriter(fo, fieldnames=cles)
        w.writeheader()
        w.writerows(lignes)
    for r in lignes:
        print(r)


if __name__ == "__main__":
    main()
