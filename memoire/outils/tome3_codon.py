"""Données des figures du chapitre 8 du Tome III (lot A, le codon synonyme du zéro), tirées des fichiers
commités (aucun chiffre recopié à la main).

Écrit sous memoire/figures/tome3/donnees/ (séparateur virgule comme le reste du mémoire, fin de ligne LF,
lisible par pgfplots) :
  codon-theoreme-20b.csv, codon-theoreme-120b.csv : un point par tenseur : x = 2 × part des −0, y = gain
                       mesuré (bits par poids), couche, matrice (F3) ;
  codon-octets-v10.csv, codon-octets-v12.csv : la table CODES_CTX (κ = 1) de gpt-oss-120b, couche 18,
                       matrice up, en grille 16 × 16 : x = demi-octet faible, y = demi-octet fort,
                       v = log10(1 + fréquence) (fréquence sur 4 096 ; 0 = octet absent) (F2) ;
  codon-j1-v10.csv, codon-j1-v12.csv : passe, jetons/s, Mo de tronçons par jeton, de la séance J1 s2
                       (machine calme, 2026-10-22) si elle est commitée, sinon de s1 (sous charge) ;
  codon-roue.csv     : III-8.1, les seize codes E2M1 : valeur (ggml et OCP), angle sur la roue avant et après
                       le fondu, part de chaque code dans les 72 tenseurs d'experts du 20b
                       (mesures/genome/predictif-elagage/histo-toutes-gptoss20b.npz ; second flux, M1) ;
  codon-colonne.csv  : III-8.5, gain du contexte de colonne par tenseur (colonne-par-tenseur.csv de la
                       synthèse : zero_octet_kappa − zero_demi_octet_kappa_colonne, bits par poids) ;
  codon-sans-perte.csv : III-8.5 (c), l'axe sans perte tenseur par tenseur (F1, codon du zéro, colonne),
                       reçu de III-7.1 au second flux ;
  codon-j1-passes.csv : III-8.6 (a)(b), les huit passes de s2 (passe, lettre, jetons/s, Mo par jeton) ;
  codon-j1-iso.csv   : III-8.6 (b), la courbe « vitesse si seuls les octets comptaient » :
                       jetons/s = médiane(A) × octets(A) / octets ;
  codon-j1-motif.csv : III-8.6 (c), le motif croisé du juge du placement (séance J-bis, Jb3-*) : quatre
                       cas, les passes retenues (ni arrêt, ni charge, ni batterie, disque lu ≤ 1,01 × demandé)
                       et leur médiane ;
  codon-j1-encart.csv : III-8.6 (c), encart : A120 et C120 (v1.0 égaux au bit) à l'étage disque de s2, et
                       C120 sur ses seuls tronçons d'un extent (juge du placement, J6) ;
  codon-j1-cascade.csv : III-8.6 (d), la cascade du 120b (séance du juge de la construction, trois fichiers) ;
  codon-nombres.tex  : les nombres des légendes et des annotations, en macros \\CodonN… (valeurs brutes,
                       à passer à \\num).

  python -I -X utf8 memoire/outils/tome3_codon.py
"""
from __future__ import annotations

import csv
import json
import math
import pathlib
import statistics

import numpy as np

RACINE = pathlib.Path(__file__).resolve().parents[2]
M = RACINE / "mesures/genome/construction/codon"
D = RACINE / "memoire/figures/tome3/donnees"
SEANCE_PLACEMENT = RACINE / "mesures/disque/placement/juge/seance"
JUGE = RACINE / "mesures/genome/construction/juge"

# E2M1 : v(c) = (−1)^{c₃} K[c & 7] (ARCHITECTURE § 5.6 ; 06 § 1).
K = (0, 1, 2, 3, 4, 6, 8, 12)


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
    """Les nombres des légendes : une macro par nombre, valeur brute (point décimal)."""

    def __init__(self) -> None:
        self.lignes: list[str] = []

    def __call__(self, nom: str, valeur, chiffres: int | None = None, source: str = "") -> None:
        assert nom.isalpha(), nom
        if isinstance(valeur, float) and chiffres is not None:
            texte = f"{valeur:.{chiffres}f}"
        else:
            texte = str(valeur)
        self.lignes.append(f"\\def\\{nom}{{{texte}}}% {source}")

    def ecrire(self, nom: str, titre: str) -> None:
        with open(D / nom, "w", encoding="utf-8", newline="\n") as f:
            f.write(f"% {titre}\n% Écrit par un script de memoire/outils/ : ne pas modifier à la main.\n")
            f.write("\n".join(self.lignes) + "\n")


def passe_valide(j: dict) -> bool:
    """Les règles du juge du placement (JUGEMENT-placement § 5) : aucune passe à arrêt, sous charge, sur
    batterie, ni où le disque a lu plus de 1 % de plus que demandé."""
    if j.get("arret_s"):
        return False
    if j.get("sous_charge"):
        return False
    if j.get("secteur_apres") is False:
        return False
    return j["smart_ecart"]["octets_lus_disque"] / j["octets"] <= 1.01


def anciennes(N: Nombres) -> None:
    """F3, F2 et les passes du J1 (inchangés depuis le 2026-10-17)."""
    lignes = lire_csv(M / "tailles-par-tenseur.csv")
    for m in ("20b", "120b"):
        # residu : (mesuré − prédit) en 10⁻⁴ bit par poids, le panneau (b) de III-8.3 (D12 du juge de design).
        g, w = ecrivain(f"codon-theoreme-{m}.csv", ["x", "y", "couche", "matrice", "residu"])
        for r in lignes:
            if r["modele"] == m:
                x, y = 2 * float(r["part_moins_zero"]), float(r["gain_bits"])
                w.writerow([f"{x:.6f}", f"{y:.6f}", r["couche"], r["matrice"], f"{1e4 * (y - x):.4f}"])
        g.close()
    rows = [r for r in lire_csv(M / "tables-octets.csv")
            if r["modele"] == "120b" and r["couche"] == "18" and r["matrice"] == "1" and r["kappa"] == "1"]
    vmax = 0.0
    for v, nom in (("1.0", "A"), ("1.2", "B")):
        fr = {int(r["octet"]): int(r["frequence"]) for r in rows if r["version"] == v}
        assert len(fr) == 256 and sum(fr.values()) == 4096, v
        g, w = ecrivain(f"codon-octets-v{v.replace('.', '')}.csv", ["x", "y", "v"])
        for haut in range(16):
            for bas in range(16):
                w.writerow([bas, haut, f"{math.log10(1 + fr[(haut << 4) | bas]):.5f}"])
                vmax = max(vmax, math.log10(1 + fr[(haut << 4) | bas]))
        g.close()
        # Les octets d'effectif nul (D11 : hachurés, pour ne pas les confondre avec les octets rares).
        nuls = [(o & 15, o >> 4) for o in range(256) if fr[o] == 0]
        N(f"CodonNOctetsSymboles{nom}", 256 - len(nuls), None, "tables-octets.csv (120b, couche 18, up, κ = 1)")
        N(f"CodonNOctetsNuls{nom}", ",".join(f"{x}/{y}" for x, y in nuls), None, "tables-octets.csv (x/y des octets nuls)")
    # L'échelle de couleur de III-8.2 s'arrête à log10(1 + f) = 1,8 : aucune case ne doit la dépasser.
    assert vmax <= 1.8, vmax
    N("CodonNOctetsVmax", vmax, 3, "tables-octets.csv")
    j1 = M / "j1-s2-passes.csv"
    if not j1.exists():
        j1 = M / "j1-s1-passes.csv"
    passes = lire_csv(j1)
    for lettre, nom in (("A", "v10"), ("B", "v12")):
        g, w = ecrivain(f"codon-j1-{nom}.csv", ["passe", "jetons_s", "mo_par_jeton"])
        for r in passes:
            if r["fichier"] == lettre:
                w.writerow([r["passe"], f"{float(r['jetons_s']):.5f}", f"{float(r['octets_troncons_par_jeton']) / 1e6:.3f}"])
        g.close()
    # Écart à la diagonale de F3, redonné ici (il était écrit à la main dans la macro).
    ecarts = [float(r["gain_bits"]) - 2 * float(r["part_moins_zero"]) for r in lignes]
    # Le panneau (b) de III-8.3 va de −2,5 à 2,5 (10⁻⁴ bit) : aucun résidu hors du cadre (règle du second flux).
    assert max(abs(e) for e in ecarts) * 1e4 < 2.5, max(abs(e) for e in ecarts)
    # De même, les points de (a) tiennent dans le cadre 0,108–0,245.
    assert all(0.108 < 2 * float(r["part_moins_zero"]) < 0.245 and 0.108 < float(r["gain_bits"]) < 0.245 for r in lignes)
    N("CodonNEcartMin", min(ecarts), 5, "tailles-par-tenseur.csv")
    N("CodonNEcartMax", max(ecarts), 5, "tailles-par-tenseur.csv")
    N("CodonNTenseurs", len(lignes), None, "tailles-par-tenseur.csv")


def roue(N: Nombres) -> None:
    """III-8.1 : les seize codes sur la droite réelle repliée en cercle.

    Second flux (M1 du juge des chiffres) : les parts viennent de l'histogramme des 72 tenseurs d'experts du
    20b (histo-toutes-gptoss20b.npz, commit 5043ca7), et non plus des 12 de histo-12 : la roue et la pièce
    du signe ont alors une seule source de tenseurs. Témoin : le compte du code 8 égale les −0 fondus que
    le codeur du lot A a comptés (tailles.json, moins_zero_fondus), par un autre outil."""
    z = np.load(RACINE / "mesures/genome/predictif-elagage/histo-toutes-gptoss20b.npz")
    comptes = z["comptes"].astype(np.int64).sum(axis=(0, 1, 2))
    assert comptes.shape == (16,)
    total = int(comptes.sum())
    part = comptes / total
    tailles20 = lire_json(M / "tailles.json")["totaux"]["20b"]
    assert int(comptes[8]) == tailles20["moins_zero_fondus"], (int(comptes[8]), tailles20["moins_zero_fondus"])
    assert total == tailles20["poids_experts"], (total, tailles20["poids_experts"])
    valeurs = sorted({(-1) ** (c >> 3) * K[c & 7] for c in range(16)})
    assert len(valeurs) == 15  # ±0 confondus
    pas = 360 / 15
    # valeur : celle de la table de ggml (K, doublée) ; valeur_ocp : celle de la norme OCP (K / 2), que la
    # figure imprime pour concorder avec III-1.1 (D31 et § 2.5 du juge de design).
    g, w = ecrivain("codon-roue.csv", ["code", "bits", "valeur", "angle_avant", "angle_apres",
                                        "part_avant", "part_apres", "apres", "pourcent_avant", "pourcent_apres",
                                        "bit_signe", "bits_magnitude", "sorte", "valeur_ocp"])
    for c in range(16):
        v = (-1) ** (c >> 3) * K[c & 7]
        ocp = ("-" if c >> 3 else "") + (f"{K[c & 7] / 2:g}" if c & 7 else "0")
        rang = valeurs.index(v) - valeurs.index(0)  # −7 … 7, 0 en haut
        angle = 90 - pas * rang  # positifs à droite (sens horaire), négatifs à gauche
        angle_avant = angle + (-4.5 if c == 0 else 4.5 if c == 8 else 0.0)
        pa = float(part[c])
        pp = float(part[0] + part[8]) if c == 0 else (0.0 if c == 8 else pa)
        w.writerow([c, f"{c:04b}", v if c != 8 else "-0", f"{angle_avant:.2f}", f"{angle:.2f}",
                    f"{pa:.6f}", f"{pp:.6f}", 0 if c == 8 else 1, f"{100 * pa:.1f}", f"{100 * pp:.1f}",
                    c >> 3, f"{c & 7:03b}", 0 if c & 7 == 0 else 1 + (c >> 3), ocp])  # sorte : 0 zéro, 1 positif, 2 négatif
    g.close()
    N("CodonNRoueTenseurs", len(z["noms"]), None, "histo-toutes-gptoss20b.npz")
    N("CodonNRouePoids", total, None, "histo-toutes-gptoss20b.npz")
    N("CodonNRoueZeroPlus", 100 * float(part[0]), 2, "histo-toutes-gptoss20b.npz")
    N("CodonNRoueZeroMoins", 100 * float(part[8]), 2, "histo-toutes-gptoss20b.npz")
    # L'épaisseur dessinée d'un rayon est affine en sa part : 0,4 pt + 44 pt × part (codon-figures.tex) ; le
    # rayon du zéro ne double donc pas au fondu : il s'épaissit de ce rapport (M2 du juge des chiffres).
    larg = lambda p: 0.4 + 44 * p  # noqa: E731
    N("CodonNRoueEpaisseur", larg(float(part[0] + part[8])) / larg(float(part[0])), 2, "calculé (épaisseur affine)")
    zc = lire_json(RACINE / "mesures/genome/etat-de-l-art/journaux/zero-compte-20b.json")
    N("CodonNPiece", zc["H_signe_sachant_zero"], 10, "zero-compte-20b.json")
    N("CodonNPiecePlus", 100 * zc["p_plus0"], 4, "zero-compte-20b.json")
    N("CodonNPieceMoins", 100 * zc["p_moins0"], 4, "zero-compte-20b.json")
    N("CodonNHCode", zc["H_code"], 4, "zero-compte-20b.json")
    N("CodonNHValeur", zc["H_valeur"], 4, "zero-compte-20b.json")
    N("CodonNCoutSigne", zc["cout_signe_des_zeros"], 4, "zero-compte-20b.json")
    N("CodonNPieceTenseurs", zc["tenseurs"], None, "zero-compte-20b.json")


def colonne(N: Nombres) -> None:
    """III-8.5 : le gain du contexte de colonne, tenseur par tenseur (20b, 12 tenseurs)."""
    lignes = lire_csv(RACINE / "mesures/genome/construction/synthese/colonne-par-tenseur.csv")
    nom_matrice = {"gate": "g", "up": "u", "down": "d"}
    tailles = lire_json(M / "tailles.json")["totaux"]["20b"]
    poids_par_tenseur = tailles["poids_experts"] / 72
    g, w = ecrivain("codon-colonne.csv", ["rang", "etiquette", "couche", "matrice", "gain", "retenu"])
    somme_retenue = 0.0
    for i, r in enumerate(lignes):
        _, couche, nom, _ = r["tenseur"].split(".")
        matrice = nom.split("_")[1]
        gain = float(r["zero_octet_kappa"]) - float(r["zero_demi_octet_kappa_colonne"])
        # « choix » du CSV est le meilleur sans seuil ; la règle du cahier (05 § 4.3) ne retient la
        # colonne qu'à 0,015 bit par poids ou plus.
        retenu = gain >= 0.015
        assert retenu <= (r["choix"] == "CODES_COL"), r["tenseur"]
        if retenu:
            somme_retenue += gain
        w.writerow([i, f"{couche}{nom_matrice[matrice]}", couche, matrice, f"{gain:.6f}", int(retenu)])
    g.close()
    # Troisième passe (GN2 du juge des chiffres de la construction, second flux) : ces colonnes sont des débits
    # d'un codec réel, pas des entropies d'histogrammes. Témoin : elles recopient, tenseur par tenseur, le
    # journal de outils/genome/predictif-elagage/taux_reel (flux codés par le rANS de l'étude 03 et décodés
    # exactement), et ce journal dit chaque tenseur décodé exactement. Sinon le script s'arrête.
    reel = lire_json(RACINE / "mesures/genome/predictif-elagage/taux-reel-colonne-12-gptoss20b.json")
    assert reel["temoins"]["tous_exacts"] is True and not reel["casser"]
    par_nom = {t["nom"]: t for t in reel["tenseurs"]}
    assert set(par_nom) == {r["tenseur"] for r in lignes}, "les douze tenseurs ne sont pas les mêmes"
    for r in lignes:
        t = par_nom[r["tenseur"]]
        assert t["exacts"] is True and t["valeur_exacte"] is True, r["tenseur"]
        for col, cle in (("sans_perte", "bpp_total_identite"), ("zero_octet_kappa", "bpp_total_zero_fondu"),
                         ("zero_demi_octet_kappa", "bpp_total_nib_kappa"),
                         ("zero_demi_octet_kappa_colonne", "bpp_total_nib_kappa_colonne")):
            assert abs(float(r[col]) - t[cle]) < 1e-6, (r["tenseur"], col, r[col], t[cle])
    # N8 du même juge : ce que le gain écrit en (a) contient. Il mêle le passage de l'alphabet octet à
    # l'alphabet demi-octet (zero_demi_octet_kappa − zero_octet_kappa, un coût) et la colonne elle-même
    # (zero_demi_octet_kappa − zero_demi_octet_kappa_colonne).
    alphabet = [float(r["zero_demi_octet_kappa"]) - float(r["zero_octet_kappa"]) for r in lignes]
    N("CodonNColonneAlphabetMin", min(alphabet), 4, "colonne-par-tenseur.csv (coût de l'alphabet demi-octet)")
    N("CodonNColonneAlphabetMax", max(alphabet), 4, "colonne-par-tenseur.csv (coût de l'alphabet demi-octet)")
    # III-8.5 (c), second flux : l'axe sans perte, reçu de III-7.1 (G10 du juge de design), tenseur par
    # tenseur : la frontière F1 (sans_perte), le codon du zéro (zero_octet_kappa), et avec le contexte de
    # colonne (zero_demi_octet_kappa_colonne), en bits par poids. Témoin : les moyennes des 12 redonnent les
    # trois points sans perte de la frontière commune (k10/frontiere.csv), écrits par un autre outil.
    g, w = ecrivain("codon-sans-perte.csv", ["rang", "etiquette", "sans_perte", "zero", "colonne", "retenu", "perd"])
    sp, ze, co = [], [], []
    for i, r in enumerate(lignes):
        _, couche, nom, _ = r["tenseur"].split(".")
        a, b, c = float(r["sans_perte"]), float(r["zero_octet_kappa"]), float(r["zero_demi_octet_kappa_colonne"])
        sp.append(a), ze.append(b), co.append(c)
        w.writerow([i, f"{couche}{nom_matrice[nom.split('_')[1]]}", f"{a:.6f}", f"{b:.6f}", f"{c:.6f}",
                    int(b - c >= 0.015), int(c > b)])
    g.close()
    fr = {r["mecanisme"]: float(r["bits_par_poids"])
          for r in lire_csv(RACINE / "mesures/genome/construction/synthese/k10/frontiere.csv")}
    for moy, cle in ((statistics.fmean(sp), "frontière sans perte (A_flux, F1)"),
                     (statistics.fmean(ze), "codon synonyme du zéro (−0 → +0)"),
                     (statistics.fmean(co), "zéro fondu + contexte de colonne (κ × q)")):
        assert abs(moy - fr[cle]) < 1e-5, (cle, moy, fr[cle])
    N("CodonNSansPerteFun", statistics.fmean(sp), 4, "colonne-par-tenseur.csv (moyenne des 12)")
    N("CodonNSansPerteZero", statistics.fmean(ze), 4, "colonne-par-tenseur.csv (moyenne des 12)")
    N("CodonNSansPerteColonne", statistics.fmean(co), 4, "colonne-par-tenseur.csv (moyenne des 12)")
    N("CodonNSansPertePerd", sum(1 for b, c in zip(ze, co) if c > b), None, "colonne-par-tenseur.csv (calculé)")
    # N8 : sur ces douze tenseurs (trois de la couche 0), la colonne gagne en moyenne bien plus que sur le
    # modèle entier de (b) ; le rapport des deux est écrit.
    N("CodonNSansPerteGainDouze", statistics.fmean(ze) - statistics.fmean(co), 4, "colonne-par-tenseur.csv (moyenne des 12)")
    N("CodonNSansPerteCouchesZero", sum(1 for r in lignes if r["tenseur"].split(".")[1] == "0"), None,
      "colonne-par-tenseur.csv")
    N("CodonNSansPerteMin", math.floor(min(co) * 50 - 1) / 50, 2, "borne de l'axe (calculée)")
    N("CodonNSansPerteMax", math.ceil(max(sp) * 50 + 1) / 50, 2, "borne de l'axe (calculée)")

    part_modele = somme_retenue * poids_par_tenseur / tailles["poids_experts"]
    N("CodonNColonneModele", part_modele, 4, "colonne-par-tenseur.csv, tailles.json")
    N("CodonNColonneMo", somme_retenue * poids_par_tenseur / 8 / 1e6, 2, "colonne-par-tenseur.csv")
    N("CodonNZeroGain", tailles["gain_bpp_troncons"], 4, "tailles.json")
    N("CodonNColonneSeuil", 0.015, 3, "05 § 4.3 (seuil du cahier)")


def j1(N: Nombres) -> None:
    """III-8.6, la refonte (réserve R1)."""
    passes = lire_csv(M / "j1-s2-passes.csv")
    verdicts = lire_json(M / "j1-s2-verdicts.json")
    g, w = ecrivain("codon-j1-passes.csv", ["passe", "lettre", "jetons_s", "mo_par_jeton"])
    for r in passes:
        w.writerow([r["passe"], r["fichier"], f"{float(r['jetons_s']):.5f}", f"{float(r['octets_troncons_par_jeton']) / 1e6:.4f}"])
    g.close()
    a = [float(r["jetons_s"]) for r in passes if r["fichier"] == "A"]
    b = [float(r["jetons_s"]) for r in passes if r["fichier"] == "B"]
    ma, mb = statistics.median(a), statistics.median(b)
    assert abs(ma - verdicts["jetons_s_mediane_A"]) < 1e-12 and abs(mb - verdicts["jetons_s_mediane_B"]) < 1e-12
    sigma = verdicts["sigma_A"]
    oa, ob = verdicts["octets_par_jeton_A"], verdicts["octets_par_jeton_B"]
    N("CodonNJiMedA", ma, 3, "j1-s2-verdicts.json")
    N("CodonNJiMedB", mb, 3, "j1-s2-verdicts.json")
    N("CodonNJiR", verdicts["r"], 3, "j1-s2-verdicts.json")
    N("CodonNJiSigma", 100 * sigma, 1, "j1-s2-verdicts.json")
    N("CodonNJiBandeBas", ma * (1 - 2 * sigma), 4, "j1-s2-verdicts.json")
    N("CodonNJiBandeHaut", ma * (1 + 2 * sigma), 4, "j1-s2-verdicts.json")
    N("CodonNJiOctets", verdicts["rapport_octets"], 4, "j1-s2-verdicts.json")
    N("CodonNJiToit", 100 * (1 / verdicts["rapport_octets"] - 1), 1, "j1-s2-verdicts.json")
    N("CodonNJiMoA", oa / 1e6, 2, "j1-s2-verdicts.json")
    N("CodonNJiMoB", ob / 1e6, 2, "j1-s2-verdicts.json")
    N("CodonNJiPreditB", ma * oa / ob, 3, "j1-s2-verdicts.json")
    # (b) la courbe iso-octets : la vitesse qu'aurait B si seule la quantité d'octets comptait.
    g, w = ecrivain("codon-j1-iso.csv", ["mo_par_jeton", "jetons_s"])
    for i in range(41):
        mo = 670 + i * 1.25
        w.writerow([f"{mo:.3f}", f"{ma * oa / (mo * 1e6):.5f}"])
    g.close()

    # (c) le motif croisé, séance J-bis du juge du placement (Jb3-01 à Jb3-16).
    cas = {("A20", "natif"): [], ("A20", "croise"): [], ("B20", "natif"): [], ("B20", "croise"): []}
    ecartees = 0
    for f in sorted(SEANCE_PLACEMENT.glob("Jb3-*.json")):
        j = lire_json(f)
        motif = "natif" if j["nom"].endswith("natif") else "croise"
        if passe_valide(j):
            cas[(j["cle"], motif)].append(j["go_s"])
        else:
            ecartees += 1
    # L'ordre de la réserve R1 : A natif, A au motif de B, B natif, B au motif de A.
    ordre = [("A20", "natif"), ("A20", "croise"), ("B20", "natif"), ("B20", "croise")]
    g, w = ecrivain("codon-j1-motif.csv", ["rang", "fichier", "motif", "mediane", "p1", "p2", "p3", "p4", "n"])
    med = {}
    for i, k in enumerate(ordre):
        v = cas[k]
        assert len(v) == 4, (k, v)
        med[k] = statistics.median(v)
        w.writerow([i, k[0], k[1], f"{med[k]:.4f}"] + [f"{x:.4f}" for x in v] + [len(v)])
    g.close()
    N("CodonNMotifAN", med[("A20", "natif")], 3, "Jb3-*.json")
    N("CodonNMotifAC", med[("A20", "croise")], 3, "Jb3-*.json")
    N("CodonNMotifBN", med[("B20", "natif")], 3, "Jb3-*.json")
    N("CodonNMotifBC", med[("B20", "croise")], 3, "Jb3-*.json")
    N("CodonNMotifRA", med[("A20", "croise")] / med[("A20", "natif")], 3, "Jb3-*.json")
    N("CodonNMotifRB", med[("B20", "croise")] / med[("B20", "natif")], 3, "Jb3-*.json")
    N("CodonNMotifEcartees", ecartees, None, "Jb3-*.json")

    # (c) encart : deux v1.0 égaux au bit (A120, C120) ; C120 sur ses tronçons d'un seul extent.
    disque = lire_json(M / "disque-s2.json")
    cartes = lire_json(SEANCE_PLACEMENT / "J1-cartes.json")
    j5 = [lire_json(f) for f in sorted(SEANCE_PLACEMENT.glob("J5-*-C120.json"))]
    j6c = [lire_json(f) for f in sorted(SEANCE_PLACEMENT.glob("J6-*-C120.json"))]
    j6a = [lire_json(f) for f in sorted(SEANCE_PLACEMENT.glob("J6-*-A120.json"))]
    # Second flux (M3 du juge des chiffres) : l'encart dessine toutes les barres dont il écrit les rapports.
    # s2 : A120 et C120 (moyennes de la séance s2 du lot A) ; J5 : C120 sur ~~en entier~~ un tirage de ses
    # tronçons (troisième passe, N2 du juge des chiffres du second flux : n = 1 200 tronçons tirés par la graine du
    # juge du placement, lu dans les journaux) ; J6 : C120 et A120 sur leurs seuls tronçons d'un extent (juge du
    # placement). Les barres s2 viennent de troncons disque, J5 et J6 du lecteur Python du juge du placement. Les rapports écrits sont ceux des médianes ; le
    # juge du placement écrit celui des moyennes (CodonNEncartCsurAMoy), dit en légende.
    c_tire = statistics.median(j["go_s"] for j in j5 if passe_valide(j))
    c_un = statistics.median(j["go_s"] for j in j6c if passe_valide(j))
    a_un = statistics.median(j["go_s"] for j in j6a if passe_valide(j))
    c_un_moy = statistics.fmean(j["go_s"] for j in j6c if passe_valide(j))
    a_un_moy = statistics.fmean(j["go_s"] for j in j6a if passe_valide(j))
    g, w = ecrivain("codon-j1-encart.csv", ["rang", "cas", "go_s"])
    w.writerow([0, "A120-s2", f"{disque['moyennes']['A']:.4f}"])
    w.writerow([1, "C120-s2", f"{disque['moyennes']['C']:.4f}"])
    w.writerow([2, "C120-J5-tire", f"{c_tire:.4f}"])
    w.writerow([3, "C120-J6-un-extent", f"{c_un:.4f}"])
    w.writerow([4, "A120-J6-un-extent", f"{a_un:.4f}"])
    g.close()
    N("CodonNEncartCsurAMoy", c_un_moy / a_un_moy, 3, "J6-*.json (rapport des moyennes)")
    N("CodonNEncartPassesJcinq", sum(1 for j in j5 if passe_valide(j)), None, "J5-*-C120.json")
    N("CodonNEncartPassesJsix", sum(1 for j in j6c if passe_valide(j)), None, "J6-*-C120.json")
    # Combien de tronçons chaque passe lit (N2) : un seul nombre par série, sinon le script s'arrête.
    n5 = {j["n"] for j in j5 if passe_valide(j)}
    n6 = {j["n"] for j in j6c + j6a if passe_valide(j)}
    assert len(n5) == 1 and len(n6) == 1, (n5, n6)
    N("CodonNEncartTiresJcinq", n5.pop(), None, "J5-*-C120.json (n : tronçons tirés)")
    N("CodonNEncartTiresJsix", n6.pop(), None, "J6-*.json (n : tronçons d'un extent)")
    N("CodonNEncartA", disque["moyennes"]["A"], 3, "disque-s2.json")
    N("CodonNEncartC", disque["moyennes"]["C"], 3, "disque-s2.json")
    N("CodonNEncartCun", c_un, 3, "J6-*-C120.json")
    N("CodonNEncartAun", a_un, 3, "J6-*-A120.json")
    N("CodonNEncartCsurA", c_un / a_un, 3, "J6-*.json")
    N("CodonNEncartCtire", c_tire, 3, "J5-*-C120.json")
    N("CodonNEncartFrag", c_un / c_tire, 2, "J5, J6")
    N("CodonNExtentsA", cartes["A120"]["extents"], None, "J1-cartes.json")
    N("CodonNExtentsC", cartes["C120"]["extents"], None, "J1-cartes.json")
    N("CodonNExtentsB", cartes["B120"]["extents"], None, "J1-cartes.json")

    # (d) la cascade du 120b : séance à trois fichiers du juge de la construction.
    vp = [r for r in lire_csv(JUGE / "figures/vitesse-passes.csv") if r["modele"] == "120b" and r["sous_charge"] == "0"]
    v = {x: statistics.median(float(r["generation_jetons_s"]) for r in vp if r["lettre"] == x) for x in "ABR"}
    o = {x: statistics.median(float(r["octets_troncons_par_pas"]) for r in vp if r["lettre"] == x) for x in "ABR"}
    toit_octets = o["A"] / o["B"]
    r_ba = v["B"] / v["A"]
    motif = r_ba / toit_octets
    r_rb = v["R"] / v["B"]
    # Couleurs du dictionnaire du Tome III (palette-tome3.tex) : v1.0, v1.2, compagnon rapide.
    marches = [  # (étape, sorte, bas, haut, couleur)
        ("v10", "mesure", 0.0, v["A"], "CouleurVunZero"),
        ("motif", "facteur", v["A"], v["A"] * motif, "CouleurVunDeux"),
        ("octets", "toit", v["A"] * motif, v["A"] * motif * toit_octets, "CouleurVunDeux"),
        ("v12", "mesure", 0.0, v["B"], "CouleurVunDeux"),
        ("rapide", "facteur", v["B"], v["B"] * r_rb, "CouleurCompagnon"),
        ("compagnon", "mesure", 0.0, v["R"], "CouleurCompagnon"),
    ]
    assert abs(marches[2][3] - v["B"]) < 1e-9
    g, w = ecrivain("codon-j1-cascade.csv", ["rang", "etape", "sorte", "bas", "haut", "couleur"])
    for i, (etape, sorte, bas, haut, couleur) in enumerate(marches):
        w.writerow([i, etape, sorte, f"{bas:.4f}", f"{haut:.4f}", couleur])
    g.close()
    N("CodonNCascA", v["A"], 3, "juge/figures/vitesse-passes.csv")
    N("CodonNCascB", v["B"], 3, "juge/figures/vitesse-passes.csv")
    N("CodonNCascR", v["R"], 3, "juge/figures/vitesse-passes.csv")
    N("CodonNCascRBA", r_ba, 3, "juge/figures/vitesse-passes.csv")
    N("CodonNCascToit", toit_octets, 3, "juge/figures/vitesse-passes.csv")
    N("CodonNCascMotif", motif, 3, "juge/figures/vitesse-passes.csv")
    N("CodonNCascRRB", r_rb, 3, "juge/figures/vitesse-passes.csv")
    N("CodonNCascToitR", o["B"] / o["R"], 3, "juge/figures/vitesse-passes.csv")
    # Le facteur « motif » est un reste, r(B/A) divisé par le toit des octets : une borne basse (M4). L'étage
    # disque seul du 120b, dans la même séance, l'appuie (B/A, médianes de disque-passes.csv, L6 du juge).
    dp = [r for r in lire_csv(JUGE / "figures/disque-passes.csv") if r["modele"] == "120b"]
    dmed = {x: statistics.median(float(r["go_s"]) for r in dp if r["lettre"] == x) for x in "AB"}
    N("CodonNCascDisqueBA", dmed["B"] / dmed["A"], 3, "juge/figures/disque-passes.csv")
    # Troisième passe (N3 du juge des chiffres du second flux) : la KL du compagnon frontière du 120b existe,
    # mais comme proxy, contre le moteur exact du 120b (pas contre la référence f64) : mesures/genome/construction/
    # synonyme/proxy/. Moyenne des dix moyennes de fenêtre et σ par fenêtres (écart-type des dix sur √10), comme
    # en III-9.6 ; témoin : la moyenne redonne kl_moyenne du résumé du juge (les fenêtres ont le même nombre de
    # positions).
    px = RACINE / "mesures/genome/construction/synonyme/proxy/proxy-120b-exact-contre-rapide-frontiere"
    par = {}
    for r in lire_csv(px.with_suffix(".csv")):
        par.setdefault(int(r["fenetre"]), []).append(float(r["kl"]))
    assert len(par) == 10 and len({len(v) for v in par.values()}) == 1
    moy = [statistics.fmean(v) for v in par.values()]
    m_px = statistics.fmean(moy)
    assert abs(m_px - lire_json(px.with_suffix(".json"))["resume"]["kl_moyenne"]) < 1e-9
    N("CodonNCompagnonKL", m_px, 3, "synonyme/proxy/proxy-120b-exact-contre-rapide-frontiere.csv")
    N("CodonNCompagnonDeuxSigma", 2 * statistics.stdev(moy) / math.sqrt(10), 3,
      "synonyme/proxy/proxy-120b-exact-contre-rapide-frontiere.csv (2σ par fenêtres)")


def main() -> int:
    D.mkdir(parents=True, exist_ok=True)
    N = Nombres()
    anciennes(N)
    roue(N)
    colonne(N)
    j1(N)
    N.ecrire("codon-nombres.tex", "Nombres des figures du chapitre 8 du Tome III (tome3_codon.py).")
    print("écrit :", sorted(p.name for p in D.glob("codon-*")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
