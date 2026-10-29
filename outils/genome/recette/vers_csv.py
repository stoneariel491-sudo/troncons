"""Les CSV des figures du mémoire (sujet genome), régénérés depuis les journaux commités.

Sorties sous mesures/genome/genome/csv/ :
  gauss-brin.csv           forme, l, débit, erreur du brin sur une gaussienne, borne de Shannon
  graine-mesure-theorie.csv  (C, P, K), débit, erreur mesurée, résidu prédit (lemme 1)
  verdict-par-tenseur.csv  tenseur, erreur de la base, bits frontière, bits recette (brut, tourne)
  spectre.csv              tenseur, part d'énergie des r premières directions (réel, permuté)
  sortie-experts.csv       couche, expert, erreurs de poids et de sortie (base, recette énergie, relatif)

Utilisation : python -I -X utf8 vers_csv.py
"""
import csv
import json
import os

J = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "mesures", "genome", "genome")
C = os.path.join(J, "csv")


def ecrire(nom, tete, lignes):
    with open(os.path.join(C, nom), "w", newline="", encoding="utf8") as f:
        w = csv.writer(f)
        w.writerow(tete)
        w.writerows(lignes)


def main():
    lignes = []
    for l in open(os.path.join(J, "gauss-balayage.jsonl"), encoding="utf8"):
        d = json.loads(l)
        lignes.append([f"{d['kb']}/{d['v']}", d["l"], d["q"], d["melangeur"], d["lloyd"], f"{d['debit']:.4f}", d["mse"], d["borne_shannon"]])
    for nom in ("gauss-T1.json",):
        # le journal porte aussi la sortie de `time` après la ligne JSON
        d = json.loads(open(os.path.join(J, nom), encoding="utf8").readline())
        lignes.append([f"{d['kb']}/{d['v']}", d["l"], d["q"], d["melangeur"], d["lloyd"], f"{d['debit']:.4f}", d["mse"], d["borne_shannon"]])
    ecrire("gauss-brin.csv", ["forme", "l", "q", "melangeur", "lloyd", "debit", "erreur", "borne_shannon"], lignes)

    theo = {(d["c"], d["p"], d["k"]): d for d in json.load(open(os.path.join(J, "graine-theorie.json"), encoding="utf8"))}
    lignes = []
    for l in open(os.path.join(J, "graines.jsonl"), encoding="utf8"):
        d = json.loads(l)
        t = theo.get((d["c"], d["p"], d["k"]))
        lignes.append([d["c"], d["p"], d["k"], d["generateur"], f"{d['debit']:.4f}", d["erreur"], d["erreur_base"], t["residu_attendu"] if t else ""])
    ecrire("graine-mesure-theorie.csv", ["c", "p", "k", "generateur", "debit", "erreur", "erreur_base", "residu_predit"], lignes)

    vb = json.load(open(os.path.join(J, "verdict-brut-l12-second-chemin.json"), encoding="utf8"))
    vt = json.load(open(os.path.join(J, "verdict-tourne-l12-second-chemin.json"), encoding="utf8"))
    b = {t["tenseur"]: t for t in vb["tenseurs"]}
    lignes = []
    for t in vt["tenseurs"]:
        lignes.append([t["tenseur"], t["erreur_base_echantillon"], t["bits_frontiere"], b[t["tenseur"]]["bits_recette"], t["bits_recette"], t["gain_bits"]])
    ecrire("verdict-par-tenseur.csv", ["tenseur", "erreur_base", "bits_frontiere", "bits_brut", "bits_tourne", "gain_tourne"], lignes)

    sp = json.load(open(os.path.join(J, "structure-spectre.json"), encoding="utf8"))
    lignes = []
    for t in sp["tenseurs"]:
        for r in sp["rangs"]:
            lignes.append([t["tenseur"], r, t["part_energie_reel"][str(r)], t["part_energie_permute"][str(r)]])
    ecrire("spectre.csv", ["tenseur", "rang", "part_reel", "part_permute"], lignes)

    chemin = os.path.join(J, "sortie-tourne.json")
    if os.path.exists(chemin) and os.path.getsize(chemin) > 0:
        d = json.load(open(chemin, encoding="utf8"))
        lignes = []
        for c in d["couches"]:
            for e in c["experts"]:
                pts = {p["repartition"]: p for p in e["points"]}
                lignes.append([c["couche"], e["expert"], e["positions"], e["erreur_poids_base"], e["erreur_sortie_base"],
                               pts["energie"]["bits"], pts["energie"]["erreur_poids"], pts["energie"]["erreur_sortie"], pts["energie"]["positions_ou_la_recette_gagne"],
                               pts["relatif"]["bits"], pts["relatif"]["erreur_poids"], pts["relatif"]["erreur_sortie"], pts["relatif"]["positions_ou_la_recette_gagne"]])
        ecrire("sortie-experts.csv", ["couche", "expert", "positions", "poids_base", "sortie_base", "bits_energie", "poids_energie", "sortie_energie", "gagne_energie",
                                      "bits_relatif", "poids_relatif", "sortie_relatif", "gagne_relatif"], lignes)


if __name__ == "__main__":
    main()
