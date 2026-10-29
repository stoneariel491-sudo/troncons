"""Données des figures du juge de la construction pour le Tome III (III-8.8, III-10.1, III-10.3), tirées des
fichiers commités sous mesures/genome/construction/juge/ (aucun chiffre recopié à la main).

Écrit sous memoire/figures/tome3/donnees/ (virgule, LF) :
  juge-codon-experts.csv : III-8.8, les 96 experts tirés et décodés en v1.2 par le juge : modèle, couche,
                           expert, part des −0 du GGUF (en %), demi-octets 8 dans le décodé ;
  juge-codon-fichiers.csv : III-8.8, les quatre fichiers : taille (Go), bits par poids alignés ;
  juge-grille.csv        : III-10.1, la grille 24 × 32 des experts du 20b : appels sur R1 et sur les fenêtres
                           neuves, sorte (0 aucune, 1 R1 seul, 2 neuves seules, 3 les deux) et la valeur de
                           couleur m = 10 × sorte + 9,99 × log10(1 + appels) / log10(1 + max) ;
  juge-kl-fenetres.csv   : III-10.3, KL moyenne par fenêtre : R1 (référence substituée) et neuves (moteur),
                           une colonne par variante, x = rang de la fenêtre (R1 0 à 9, neuves 11 à 20) ;
  juge-nombres.tex       : les nombres des légendes (macros \\JconsN…).

  python -I -X utf8 memoire/outils/tome3_juge.py
"""
from __future__ import annotations

import csv
import json
import math
import pathlib
import statistics

RACINE = pathlib.Path(__file__).resolve().parents[2]
JU = RACINE / "mesures/genome/construction/juge"
D = RACINE / "memoire/figures/tome3/donnees"


def ecrivain(nom: str, entete: list[str]):
    f = open(D / nom, "w", newline="", encoding="utf-8")
    w = csv.writer(f, delimiter=",", lineterminator="\n")
    w.writerow(entete)
    return f, w


def lire_csv(chemin: pathlib.Path) -> list[dict]:
    with open(chemin, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def lire_json(chemin: pathlib.Path):
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


class Nombres:
    def __init__(self) -> None:
        self.lignes: list[str] = []

    def __call__(self, nom: str, valeur, chiffres: int | None = None, source: str = "") -> None:
        assert nom.isalpha(), nom
        texte = f"{valeur:.{chiffres}f}" if isinstance(valeur, float) and chiffres is not None else str(valeur)
        self.lignes.append(f"\\def\\{nom}{{{texte}}}% {source}")

    def ecrire(self, nom: str, titre: str) -> None:
        with open(D / nom, "w", encoding="utf-8", newline="\n") as f:
            f.write(f"% {titre}\n% Écrit par un script de memoire/outils/ : ne pas modifier à la main.\n")
            f.write("\n".join(self.lignes) + "\n")


def codon(N: Nombres) -> None:
    lignes = lire_csv(JU / "J-T1-echantillon.csv")
    tailles = lire_json(RACINE / "mesures/genome/construction/codon/tailles.json")["totaux"]
    g, w = ecrivain("juge-codon-experts.csv", ["modele", "taille", "couche", "expert", "part", "huit", "x"])
    n = {"20b": 0, "120b": 0}
    huit = 0
    tient = 0
    for r in lignes:
        if r["version"] != "v12":
            continue
        part = 100 * int(r["moins_zero_gguf"]) / int(r["demi_octets"])
        # x : profondeur relative (couche / (L − 1)), pour mettre les deux modèles sur un axe
        L = 24 if r["modele"] == "20b" else 36
        w.writerow([r["modele"], r["modele"].rstrip("b"), r["couche"], r["expert"], f"{part:.4f}", r["huit_dans_le_decode"],
                    f"{int(r['couche']) / (L - 1):.4f}"])
        n[r["modele"]] += 1
        huit += int(r["huit_dans_le_decode"])
        tient += int(r["tient"])
    g.close()
    # Second flux (G2 du juge des chiffres) : l'axe vertical de III-8.8 se tire des parts, au point entier
    # près vers l'extérieur ; la règle : aucun expert hors du cadre, sinon le script s'arrête.
    parts = [(100 * int(r["moins_zero_gguf"]) / int(r["demi_octets"]), r) for r in lignes if r["version"] == "v12"]
    pmin, pmax = min(p for p, _ in parts), max(p for p, _ in parts)
    ymin, ymax = math.floor(pmin - 1), math.ceil(pmax + 0.3)
    assert ymin < pmin and pmax < ymax
    haut = max(parts, key=lambda x: x[0])
    N("JconsNPartAxeMin", ymin, None, "J-T1-echantillon.csv (borne calculée)")
    N("JconsNPartAxeMax", ymax, None, "J-T1-echantillon.csv (borne calculée)")
    N("JconsNPartMax", haut[0], 2, "J-T1-echantillon.csv")
    N("JconsNPartMaxModele", haut[1]["modele"], None, "J-T1-echantillon.csv")
    N("JconsNPartMaxCouche", haut[1]["couche"], None, "J-T1-echantillon.csv")
    N("JconsNPartMaxExpert", haut[1]["expert"], None, "J-T1-echantillon.csv")
    temoins = sum(1 for r in lignes if r["version"] == "v10")
    temoins_tient = sum(int(r["tient"]) for r in lignes if r["version"] == "v10")
    N("JconsNExpertsVingt", n["20b"], None, "J-T1-echantillon.csv")
    N("JconsNExpertsCent", n["120b"], None, "J-T1-echantillon.csv")
    N("JconsNExperts", n["20b"] + n["120b"], None, "J-T1-echantillon.csv")
    N("JconsNExpertsTient", tient, None, "J-T1-echantillon.csv")
    N("JconsNHuit", huit, None, "J-T1-echantillon.csv")
    N("JconsNTemoins", temoins, None, "J-T1-echantillon.csv")
    N("JconsNTemoinsTient", temoins_tient, None, "J-T1-echantillon.csv")
    N("JconsNPartVingt", 100 * tailles["20b"]["part_moins_zero"], 2, "codon/tailles.json")
    N("JconsNPartCent", 100 * tailles["120b"]["part_moins_zero"], 2, "codon/tailles.json")
    f = lire_json(JU / "J-T0-fichiers.json")
    g, w = ecrivain("juge-codon-fichiers.csv", ["rang", "fichier", "go", "bits"])
    for i, cle in enumerate(("20b-v10", "20b-v12", "120b-v10", "120b-v12")):
        x = f["fichiers"][cle]
        w.writerow([i, cle, f"{x['taille_disque'] / 1e9:.4f}", f"{x['bits_par_poids_alignes']:.5f}"])
        assert x["taille_disque"] == x["taille_declaree"] and not x["fautes"]
    g.close()
    N("JconsNGainVingt", f["gain_20b"]["bits_alignes"], 5, "J-T0-fichiers.json")
    N("JconsNGainCent", f["gain_120b"]["bits_alignes"], 5, "J-T0-fichiers.json")
    N("JconsNOctetsVingt", f["gain_20b"]["octets_fichier"], None, "J-T0-fichiers.json")
    N("JconsNOctetsCent", f["gain_120b"]["octets_fichier"], None, "J-T0-fichiers.json")
    N("JconsNGoVingtA", f["fichiers"]["20b-v10"]["taille_disque"] / 1e9, 2, "J-T0-fichiers.json")
    N("JconsNGoVingtB", f["fichiers"]["20b-v12"]["taille_disque"] / 1e9, 2, "J-T0-fichiers.json")
    N("JconsNGoCentA", f["fichiers"]["120b-v10"]["taille_disque"] / 1e9, 2, "J-T0-fichiers.json")
    N("JconsNGoCentB", f["fichiers"]["120b-v12"]["taille_disque"] / 1e9, 2, "J-T0-fichiers.json")
    N("JconsNSeuilCdeux", tailles["20b"]["A_C2_seuil_bits"], 2, "codon/tailles.json")
    N("JconsNTablesSansFente", f["fichiers"]["120b-v12"]["tables"]["codes_ctx_avec_fente_pour_un_8"], None, "J-T0-fichiers.json")


def grille(N: Nombres) -> None:
    lignes = lire_csv(JU / "figures/routage-grille.csv")
    assert len(lignes) == 24 * 32
    appels = [int(r["appels_r1"]) + int(r["appels_neuf"]) for r in lignes]
    plus = max(appels)
    g, w = ecrivain("juge-grille.csv", ["couche", "expert", "appels_r1", "appels_neuf", "sorte", "m"])
    comptes = [0, 0, 0, 0]
    for r, a in zip(lignes, appels):
        r1, nf = int(r["appels_r1"]), int(r["appels_neuf"])
        sorte = (1 if r1 > 0 else 0) + (2 if nf > 0 else 0)
        comptes[sorte] += 1
        m = 10 * sorte + (9.99 * math.log10(1 + a) / math.log10(1 + plus) if sorte else 0.0)
        w.writerow([r["couche"], r["expert"], r1, nf, sorte, f"{m:.4f}"])
    g.close()
    N("JconsNVides", comptes[0], None, "routage-grille.csv")
    # Troisième passe (GN1 du juge des chiffres de la construction, second flux) : ces experts jamais routés
    # n'ont pas eu de mesure de KL, mais leur décodage est vérifié en valeur (C1 : le vérificateur du lot A a
    # décodé tous les experts du v1.2 du 20b et les a trouvés égaux en valeur). Le compte vient de tailles.json ;
    # le script s'arrête s'il ne couvre pas toute la grille.
    t20 = lire_json(RACINE / "mesures/genome/construction/codon/tailles.json")["totaux"]["20b"]
    assert t20["C1_v12"] is True and t20["experts_exacts_v12"] == t20["experts"] == len(lignes), t20
    N("JconsNExpertsDecodes", t20["experts_exacts_v12"], None, "codon/tailles.json (experts_exacts_v12, C1)")
    N("JconsNExpertsTous", t20["experts"], None, "codon/tailles.json (experts)")
    N("JconsNRunSeul", comptes[1], None, "routage-grille.csv")
    N("JconsNNeufSeul", comptes[2], None, "routage-grille.csv")
    N("JconsNDeux", comptes[3], None, "routage-grille.csv")
    N("JconsNAppelsMax", plus, None, "routage-grille.csv")
    N("JconsNAppelsRun", sum(int(r["appels_r1"]) for r in lignes), None, "routage-grille.csv")
    N("JconsNAppelsNeuf", sum(int(r["appels_neuf"]) for r in lignes), None, "routage-grille.csv")
    # Second flux (D21 du juge de design) : le compte des experts jamais routés, couche par couche, en marge.
    g, w = ecrivain("juge-grille-marge.csv", ["couche", "vides"])
    for c in range(24):
        w.writerow([c, sum(1 for r in lignes if int(r["couche"]) == c
                           and int(r["appels_r1"]) == 0 and int(r["appels_neuf"]) == 0)])
    g.close()
    # M12 : un appel est un jeton routé ; les jetons d'une fenêtre comptent son contexte non noté. Appels d'un
    # jeu = fenêtres × couches × k × jetons par fenêtre, k = 4 experts actifs (en-tête du .trc, J-T0) ; les
    # positions notées par fenêtre viennent des fichiers par position (2 550 sur 10 fenêtres).
    k = lire_json(JU / "J-T0-fichiers.json")["fichiers"]["20b-v12"]["k"]
    run = sum(int(r["appels_r1"]) for r in lignes)
    jetons, reste = divmod(run, 10 * 24 * k)
    assert reste == 0, reste
    notees = len(lire_csv(RACINE / "mesures/genome/construction/synonyme/kl/kl-frontiere-768-positions.csv")) // 10
    N("JconsNJetonsFenetre", jetons, None, "routage-grille.csv (appels / (10 × 24 × k))")
    N("JconsNNotees", notees, None, "kl-frontiere-768-positions.csv (positions notées par fenêtre)")
    N("JconsNContexte", jetons - notees, None, "calculé")
    N("JconsNAppelsMaxUnJeu", max(max(int(r["appels_r1"]), int(r["appels_neuf"])) for r in lignes), None,
      "routage-grille.csv (le plus grand d'un seul jeu)")


def fenetres(N: Nombres) -> None:
    lignes = lire_csv(JU / "figures/kl-par-fenetre.csv")
    v = {}
    for r in lignes:
        v[(r["jeu"], r["chemin"], r["variante"], int(r["fenetre"]))] = float(r["kl"])
    colonnes = [("frontiere", "f64-substituee", "frontiere"), ("lambda1", None, "lambda1"),
                ("lambda0", None, "lambda0"), ("exact", "moteur", "exact")]
    # R1, mode exact : la KL du moteur exact contre la référence f64, par position (lot O, C4), moyennée ici
    # par fenêtre ; kl-par-fenetre.csv du juge ne la porte que pour les fenêtres neuves.
    c4 = lire_csv(RACINE / "mesures/moteur/O/journaux/o3/c4-20b-comparer.csv")
    for f in range(10):
        vals = [float(r["kl_b"]) for r in c4 if int(r["fenetre"]) == f]
        assert len(vals) == 255
        v[("r1", "moteur", "exact", f)] = statistics.fmean(vals)
    g, w = ecrivain("juge-kl-fenetres.csv", ["x", "jeu", "fenetre", "frontiere", "lambda1", "lambda0", "exact"])
    for jeu, x0, chemin in (("r1", 0, "f64-substituee"), ("neuf", 11, "moteur")):
        if jeu == "neuf":  # une ligne vide à x = 10 : les courbes ne relient pas R1 aux fenêtres neuves
            w.writerow([10, "coupure", -1, "nan", "nan", "nan", "nan"])
        for f in range(10):
            ligne = [x0 + f, jeu, f]
            for nom, ch, var in colonnes:
                c = ch or chemin
                val = v.get((jeu, c, var, f))
                ligne.append(f"{val:.6f}" if val is not None else "nan")
            w.writerow(ligne)
    g.close()
    # écart des fenêtres : rapport du max au min de la frontière, R1 ; σ_f contre σ_n (note du juge § 1.4)
    fr = [v[("r1", "f64-substituee", "frontiere", f)] for f in range(10)]
    N("JconsNFrontMin", min(fr), 3, "kl-par-fenetre.csv")
    N("JconsNFrontMax", max(fr), 3, "kl-par-fenetre.csv")
    ex = [v[(j, "moteur", "exact", f)] for j in ("r1", "neuf") for f in range(10)]
    N("JconsNExactMin", min(ex), 4, "kl-par-fenetre.csv")
    N("JconsNExactMax", max(ex), 4, "kl-par-fenetre.csv")
    N("JconsNSigmaF", statistics.stdev(fr) / math.sqrt(10), 4, "kl-par-fenetre.csv")
    # Second flux (M13 du juge des chiffres) : de combien les deux chemins (référence f64 substituée, moteur)
    # diffèrent dans les valeurs tracées, là où une même variante est passée par les deux. R1, frontière : le
    # moteur par le lot B (synonyme/moteur/), la référence substituée par kl-par-fenetre.csv ; neuves, λ = 0 :
    # les deux dans kl-par-fenetre.csv.
    # Troisième passe (N4 du même juge, second flux) : sur R1, les TROIS variantes sont passées par les deux
    # chemins (le lot B a les fichiers moteur de la frontière, de λ = 1 et de λ = 0), pas la frontière seule.
    # Écart = moteur moins référence substituée, par fenêtre ; la fourchette écrite borne les trois.
    ecarts_r1 = {}
    for var, fichier in (("frontiere", "frontiere"), ("lambda1", "synonyme"), ("lambda0", "synonyme-l0")):
        par = {}
        for r in lire_csv(RACINE / f"mesures/genome/construction/synonyme/moteur/kl-moteur-{fichier}-positions.csv"):
            par.setdefault(int(r["fenetre"]), []).append(float(r["kl"]))
        assert sorted(par) == list(range(10)), var
        ecarts_r1[var] = [statistics.fmean(par[f]) - v[("r1", "f64-substituee", var, f)] for f in range(10)]
    ecart_r1 = ecarts_r1["frontiere"]
    tous_r1 = [x for e in ecarts_r1.values() for x in e]
    ecart_nf = [v[("neuf", "moteur", "lambda0", f)] - v[("neuf", "f64-substituee", "lambda0", f)] for f in range(10)]
    N("JconsNCheminRunMoy", statistics.fmean(ecart_r1), 4, "synonyme/moteur, kl-par-fenetre.csv")
    N("JconsNCheminRunMoyUn", statistics.fmean(ecarts_r1["lambda1"]), 4, "synonyme/moteur, kl-par-fenetre.csv")
    N("JconsNCheminRunMoyZero", statistics.fmean(ecarts_r1["lambda0"]), 4, "synonyme/moteur, kl-par-fenetre.csv")
    N("JconsNCheminRunMin", min(tous_r1), 4, "synonyme/moteur, kl-par-fenetre.csv (les trois variantes)")
    N("JconsNCheminRunMax", max(tous_r1), 4, "synonyme/moteur, kl-par-fenetre.csv (les trois variantes)")
    N("JconsNCheminNeufMoy", statistics.fmean(ecart_nf), 4, "kl-par-fenetre.csv")
    N("JconsNCheminNeufAbsMax", max(abs(x) for x in ecart_nf), 4, "kl-par-fenetre.csv")


def main() -> int:
    D.mkdir(parents=True, exist_ok=True)
    N = Nombres()
    codon(N)
    grille(N)
    fenetres(N)
    N.ecrire("juge-nombres.tex", "Nombres des figures du juge de la construction, Tome III (tome3_juge.py).")
    print("écrit :", sorted(p.name for p in D.glob("juge-*")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
