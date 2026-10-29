"""Données des figures du chapitre 7 du Tome III (la synthèse de la ronde : frontière commune, erreur
d'expert contre KL, deux parts de la KL, colonnes géantes), tirées des fichiers commités (aucun chiffre
recopié à la main).

Sources :
  mesures/genome/construction/synthese/k10/  frontiere.csv, erreur-contre-kl.csv, colonne-par-tenseur.csv,
      écrits par `outils/genome/synthese/frontiere.py --k10 --sortie mesures/genome/construction/synthese/k10`
      (réserve R4 de l'inventaire : le point de S* vient de la passe K10 à 10 fenêtres) ;
  mesures/genome/etat-de-l-art/journaux/kl-{frontiere,synonyme-d1}-positions.csv et -juge.json (III-7.3) ;
  mesures/genome/genome/csv/colonnes-energie-erreur.csv (III-7.4, un tenseur : blk.8 down, expert 16).

Écrit sous memoire/figures/tome3/donnees/ (virgule, fin de ligne LF) :
  synthese-frontiere-kl.csv       III-7.1 : points jugés à la KL (protocoles P1, P2-10, P3), classés par la
                                  règle déclarée d̄ ± 2σ (classe_regle ; G1 du juge ronde) ;
  synthese-frontiere-sans-kl.csv  III-7.1 : points sans KL, placés sur l'axe des bits seul ;
  synthese-colonne.csv            l'axe sans perte par tenseur (tracé au premier flux dans III-7.1 ; retiré
                                  de III-7.1 au second flux, G10 du juge de design : le lot construction
                                  le reprend dans III-8.5 ; le fichier reste écrit pour lui) ;
  synthese-erreur-kl.csv          III-7.2 ;
  synthese-positions.csv          III-7.3 : KL de la base et du synonyme, position par position, et la
                                  queue (1 : base, 2 : synonyme, 3 : les deux ; les ⌊n/100⌋ plus grandes) ;
  synthese-densite-base.csv, synthese-densite-syn.csv  III-7.3 : densités marginales (log10) ;
  synthese-colonnes.csv           III-7.4 : énergie et erreurs par colonne, rapportées à leur moyenne ;
  synthese-nombres.csv            chaque nombre d'une légende ou d'une annotation (cle, valeur, source).

  python -I -X utf8 memoire/outils/tome3_synthese.py
"""
from __future__ import annotations

import csv
import json
import math
import pathlib
import statistics

RACINE = pathlib.Path(__file__).resolve().parents[2]
K10 = RACINE / "mesures/genome/construction/synthese/k10"
ECL = RACINE / "mesures/genome/etat-de-l-art/journaux"
GEN = RACINE / "mesures/genome/genome/csv"
D = RACINE / "memoire/figures/tome3/donnees"
NOMBRES: list[tuple[str, str, str]] = []
CLASSES: dict[str, str] = {}  # clé de III-7.1 -> classe par la règle (reprise en III-7.2)
SEUIL_COLONNE = 0.015  # règle du lot A : CODES_COL seulement si le gain sur CODES_CTX atteint 0,015 bit
PLANCHER_KL = 1e-5  # une KL mesurée sous ce plancher (bruit d'arrondi, une seule est négative) y est portée


def nombre(cle: str, valeur: float, source: str, chiffres: int = 6) -> float:
    NOMBRES.append((cle, f"{valeur:.{chiffres}g}", source.replace(",", " ;")))  # pgfplotstable ne lit pas les guillemets
    return valeur


def ecrire(nom: str, entete: list[str], lignes: list[list]) -> None:
    with open(D / nom, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=",", lineterminator="\n")
        w.writerow(entete)
        w.writerows(lignes)


def lire_csv(chemin: pathlib.Path) -> list[dict]:
    with open(chemin, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def classe(verdict: str) -> str:
    for prefixe, c in (("référence", "ref"), ("gagne", "gagne"), ("égal", "egal"), ("tombe", "tombe")):
        if verdict.startswith(prefixe):
            return c
    raise ValueError(verdict)


def classe_regle(p: dict) -> tuple[str, str]:
    """La classe d'un point jugé à la KL, par la règle déclarée que la légende de III-7.1 énonce (différence
    appariée d̄ ± σ contre la base du même protocole) : meilleur si d̄ + 2σ < 0, pire si d̄ − 2σ > 0, égal
    sinon. Un point sans différence appariée garde le verdict de sa source (tombé au rapport de KL) ; la
    légende le dit. Décision du second flux (G1 du juge ronde, JUGEMENT-figures-ronde.md § 2), sans
    réécrire frontiere.csv : sa colonne `verdict` classe « gagne » les partitions par κ tenseur par
    tenseur (« 0,911 × les bits, KL égale par la règle ») ; la règle les dit égales en KL.
    Rend (classe, d'où vient la classe : « regle » ou « source »)."""
    if p["verdict"].startswith("référence"):
        return "ref", "source"
    if p["diff_apparie"] and p["diff_apparie_sigma"]:
        d, s = float(p["diff_apparie"]), float(p["diff_apparie_sigma"])
        if d + 2 * s < 0:
            return "gagne", "regle"
        if d - 2 * s > 0:
            return "tombe", "regle"
        return "egal", "regle"
    return classe(p["verdict"]), "source"


# Clé courte de chaque mécanisme (pgfplotstable ne lit pas les guillemets du CSV : les noms longs restent
# dans le CSV source, la figure place ses étiquettes par ces clés).
CLE = {
    "base frontière (07, F1)": "p1-base",
    "mutation synonyme λ = 0, δ* = 1": "p1-syn",
    "base frontière (8 experts, 10 fenêtres)": "p2-base",
    "S* (10 fenêtres)": "p2-sstar",
    "base frontière (12 tenseurs)": "p3-base",
    "partitions par κ, chaque tenseur à l'erreur de la base": "p3-kappat",
    "partitions par κ, erreur moyenne égale": "p3-kappa",
    "hebbien (δ, ligne, colonne)": "p3-hebbdlc",
    "hebbien par e (erreur d'expert égale à la base)": "p3-hebbe",
    "hebbien (e, ligne, colonne)": "p3-hebbelc",
    "partitions par e (remplissage inverse des poids)": "p3-partse",
    "élagage par activité de colonne (e, q)": "p3-elag",
    "mutation synonyme λ = 1, δ* = 1 (KL non mesurée)": "s-lam1",
    "base frontière, mêmes experts que λ = 1": "s-baselam1",
    "brin lu par codons, tourné (critère W, erreur de poids égale)": "s-brin",
    "S* à erreur de sortie d'expert égale": "s-sstar",
    "duplication D2b (parent comme contexte, base inchangée)": "s-d2b",
    "graine + coefficients (SeedLM écrit de zéro)": "s-graine",
    "motifs partagés (dictionnaire commun, RVQ)": "s-motifs",
}


def frontiere() -> None:
    src = "mesures/genome/construction/synthese/k10/frontiere.csv"
    pts = lire_csv(K10 / "frontiere.csv")
    avec, sans = [], []
    n_kl = 0
    desaccords, sans_apparie = [], 0
    for p in pts:
        prot = p["protocole"]
        if prot in ("P1", "P2-10", "P3") and p["rapport_kl"]:
            c, origine = classe_regle(p)
            if c != classe(p["verdict"]):
                desaccords.append((p["mecanisme"], classe(p["verdict"]), c))
            if origine == "source" and c != "ref":
                sans_apparie += 1
            k = CLE[p["mecanisme"]]
            CLASSES[k] = c
            avec.append([prot, f"{float(p['bits_par_poids']):.5f}", f"{float(p['rapport_kl']):.5f}", c, k, origine])
            nombre(f"{k}-bits", float(p["bits_par_poids"]), src)
            nombre(f"{k}-rapport", float(p["rapport_kl"]), src)
            n_kl += 1
        elif prot in ("P1-sorties", "P0-poids", "P2-sorties"):
            k = CLE[p["mecanisme"]]
            sans.append([prot, f"{float(p['bits_par_poids']):.5f}", classe(p["verdict"]), k])
            nombre(f"{k}-bits", float(p["bits_par_poids"]), src)
    ecrire("synthese-frontiere-kl.csv", ["protocole", "bits", "rapport", "classe", "cle", "origine"], avec)
    ecrire("synthese-frontiere-sans-kl.csv", ["protocole", "bits", "classe", "cle"],
           sorted(sans, key=lambda r: float(r[1])))
    # G1 : la règle et la colonne `verdict` de la source ne divergent que sur les partitions par κ tenseur
    # par tenseur (gagne → égal). Toute autre divergence arrête le script : elle demanderait une phrase neuve.
    for d in desaccords:
        print("règle contre source :", d)
    assert [d[0] for d in desaccords] == ["partitions par κ, chaque tenseur à l'erreur de la base"], desaccords
    assert desaccords[0][1:] == ("gagne", "egal"), desaccords
    # III-7.1 trace chaque (protocole, classe) par un addplot filtré : la liste des combinaisons est
    # écrite dans la figure ; une combinaison neuve y manquerait en silence.
    combos = sorted({(r[0], r[3]) for r in avec})
    assert combos == [("P1", "gagne"), ("P1", "ref"), ("P2-10", "egal"), ("P2-10", "ref"),
                      ("P3", "egal"), ("P3", "ref"), ("P3", "tombe")], combos
    nombre("regle-desaccords", len(desaccords), src + " (calculé : règle d̄ ± 2σ contre la colonne verdict)")
    nombre("points-sans-apparie", sans_apparie, src + " (points jugés au rapport de KL seul)")
    nombre("points-kl", n_kl, src)
    nombre("points-sans-kl", len(sans), src)
    nombre("points-total", len(pts), src)
    lossless = {p["mecanisme"]: float(p["bits_par_poids"]) for p in pts if p["protocole"] == "P0"}
    nombre("sans-perte", lossless["frontière sans perte (A_flux, F1)"], src)
    nombre("codon", lossless["codon synonyme du zéro (−0 → +0)"], src)
    nombre("colonne", lossless["zéro fondu + contexte de colonne (κ × q)"], src)
    nombre("d1", lossless["duplication D1 (parent, sans perte)"], src)
    par = {p["mecanisme"]: p for p in pts}
    s10 = par["S* (10 fenêtres)"]
    nombre("sstar-rapport", float(s10["rapport_kl"]), src)
    nombre("sstar-apparie", float(s10["diff_apparie"]), src)
    nombre("sstar-apparie-sigma", float(s10["diff_apparie_sigma"]), src)
    syn = par["mutation synonyme λ = 0, δ* = 1"]
    nombre("syn-rapport", float(syn["rapport_kl"]), src)
    nombre("syn-ecart-bits", float(syn["bits_par_poids"]) - float(par["base frontière (07, F1)"]["bits_par_poids"]),
           src + " (calculé)")
    nombre("seuil-colonne", SEUIL_COLONNE, "cahier de construction, lot A (règle déclarée ; frontiere.py)")
    kt = par["partitions par κ, chaque tenseur à l'erreur de la base"]
    base3 = par["base frontière (12 tenseurs)"]
    nombre("kappa-t-bits", float(kt["bits_par_poids"]), src)
    nombre("kappa-t-part-bits", float(kt["bits_par_poids"]) / float(base3["bits_par_poids"]), src + " (calculé)")
    # Les différences appariées que la règle lit (G1) : κ tenseur par tenseur, et λ = 0.
    for cle, p in (("kappa-t", kt), ("syn", syn)):
        d, s = float(p["diff_apparie"]), float(p["diff_apparie_sigma"])
        nombre(f"{cle}-apparie", d, src)
        nombre(f"{cle}-apparie-sigma", s, src)
        nombre(f"{cle}-apparie-z", d / s, src + " (calculé)")
    # λ = 1 : protocole P1-sorties, sur une partie des experts de P1 (M5 du juge ronde) ; le compte se lit
    # dans la passe elle-même (experts × couches).
    lam1 = par["mutation synonyme λ = 1, δ* = 1 (KL non mesurée)"]
    pl = json.load(open(RACINE / lam1["source"], encoding="utf-8"))
    nombre("lam1-experts", len(pl["experts"]) * len(pl["couches"]), lam1["source"] + " (experts × couches)")
    nombre("lam1-base-bits", float(par["base frontière, mêmes experts que λ = 1"]["bits_par_poids"]), src)
    nombre("rapport-max", max(float(p["rapport_kl"]) for p in pts if p["rapport_kl"]), src)
    # L'axe sans perte, tenseur par tenseur, et la règle des 0,015 bit du cahier de construction.
    col = lire_csv(K10 / "colonne-par-tenseur.csv")
    lignes = []
    for i, r in enumerate(col):
        c, role = r["tenseur"].split(".")[1:3]
        role = role.replace("ffn_", "").replace("_exps", "")
        gain_col = float(r["zero_octet_kappa"]) - float(r["zero_demi_octet_kappa_colonne"])
        lignes.append([i, f"blk.{c} {role}", r["sans_perte"], r["zero_octet_kappa"], r["zero_demi_octet_kappa_colonne"],
                       int(gain_col >= SEUIL_COLONNE)])
    ecrire("synthese-colonne.csv", ["rang", "tenseur", "sans_perte", "zero", "colonne", "colonne_retenue"], lignes)
    moy = lambda k: statistics.fmean(float(r[k]) for r in col)
    assert abs(moy("sans_perte") - lossless["frontière sans perte (A_flux, F1)"]) < 1e-5
    assert abs(moy("zero_octet_kappa") - lossless["codon synonyme du zéro (−0 → +0)"]) < 1e-5
    assert abs(moy("zero_demi_octet_kappa_colonne") - lossless["zéro fondu + contexte de colonne (κ × q)"]) < 1e-5
    nombre("colonne-retenues", sum(l[5] for l in lignes), "colonne-par-tenseur.csv (règle des 0,015 bit, calculé)")
    nombre("colonne-seuil-moyen", statistics.fmean(
        float(r["zero_demi_octet_kappa_colonne"]) if l[5] else float(r["zero_octet_kappa"]) for r, l in zip(col, lignes)),
        "colonne-par-tenseur.csv (calculé)")
    nombre("colonne-perd", sum(1 for r in col if float(r["zero_demi_octet_kappa_colonne"]) > float(r["zero_octet_kappa"])),
           "colonne-par-tenseur.csv (calculé)")


def erreur_kl() -> None:
    src = "mesures/genome/construction/synthese/k10/erreur-contre-kl.csv"
    rows = lire_csv(K10 / "erreur-contre-kl.csv")
    lignes = []
    for r in rows:
        if r["mecanisme"] == "S*":
            etat = "barre"   # 3 fenêtres : barré par 05 § 2 (R4), montré comme tel
        else:
            etat = "tenu"
        nom = r["mecanisme"]
        cle = {"mutation synonyme λ = 0": "syn", "S*": "sstar3", "S* (10 fenêtres)": "sstar10",
               "partitions par κ, erreur moyenne égale": "kappa", "hebbien par e (erreur d'expert égale à la base)": "hebbe",
               "hebbien (e, ligne, colonne)": "hebbelc", "partitions par e (remplissage inverse des poids)": "partse"}[nom]
        nombre(f"ek-{cle}-x", float(r["rapport_erreur_expert"]), src)
        nombre(f"ek-{cle}-y", float(r["rapport_kl"]), src)
        # La classe (remplissage) est celle du même mécanisme dans III-7.1, par la même règle.
        cl = "barre" if etat == "barre" else CLASSES[{"syn": "p1-syn", "sstar10": "p2-sstar"}.get(cle, "p3-" + cle)]
        lignes.append([r["protocole"], r["rapport_erreur_expert"], r["rapport_kl"], etat, cle, cl])
    ecrire("synthese-erreur-kl.csv", ["protocole", "x", "y", "etat", "cle", "classe"], lignes)
    # La bande d'abscisse des trois points à erreur d'expert proche de la base (hors S* à 3 fenêtres).
    bande = [r for r in rows if 0.7 <= float(r["rapport_erreur_expert"]) <= 1.1 and r["mecanisme"] != "S*"]
    nombre("bande-x-min", min(float(r["rapport_erreur_expert"]) for r in bande), src)
    nombre("bande-x-max", max(float(r["rapport_erreur_expert"]) for r in bande), src)
    nombre("bande-y-min", min(float(r["rapport_kl"]) for r in bande), src)
    nombre("bande-y-max", max(float(r["rapport_kl"]) for r in bande), src)
    nombre("bande-n", len(bande), src)


def deux_parts() -> None:
    sb = "mesures/genome/etat-de-l-art/journaux/kl-frontiere-positions.csv"
    ss = "mesures/genome/etat-de-l-art/journaux/kl-synonyme-d1-positions.csv"
    pb, ps = lire_csv(ECL / "kl-frontiere-positions.csv"), lire_csv(ECL / "kl-synonyme-d1-positions.csv")
    assert [(r["fenetre"], r["position"]) for r in pb] == [(r["fenetre"], r["position"]) for r in ps]
    kb = [float(r["kl"]) for r in pb]
    ks = [float(r["kl"]) for r in ps]
    jb = json.load(open(ECL / "kl-frontiere-juge.json", encoding="utf-8"))["resume"]
    js = json.load(open(ECL / "kl-synonyme-d1-juge.json", encoding="utf-8"))["resume"]
    # Témoin : la moyenne recalculée égale celle du juge (comme frontiere.py), sinon rien n'est écrit.
    assert abs(statistics.fmean(kb) - jb["kl_moyenne"]) < 1e-12 and abs(statistics.fmean(ks) - js["kl_moyenne"]) < 1e-12
    # La queue : les ⌊n/100⌋ plus grandes positions de chacun (la convention de « 1 % des positions »,
    # M11 du juge ronde : 25 positions sur 2 550, soit 0,98 %). Une position est marquée si elle est dans
    # la queue de la base, du synonyme, ou des deux (M9 : la queue garde sa forme, pas ses positions).
    n1 = len(kb) // 100
    queue_b = set(sorted(range(len(kb)), key=lambda i: kb[i], reverse=True)[:n1])
    queue_s = set(sorted(range(len(ks)), key=lambda i: ks[i], reverse=True)[:n1])
    def queue(i: int) -> int:
        return (1 if i in queue_b else 0) + (2 if i in queue_s else 0)
    lignes = [[f"{max(b, PLANCHER_KL):.6e}", f"{max(s, PLANCHER_KL):.6e}", r["fenetre"], queue(i)]
              for i, (b, s, r) in enumerate(zip(kb, ks, pb))]
    ecrire("synthese-positions.csv", ["kl_base", "kl_syn", "fenetre", "queue"], lignes)
    # Les deux queues en fichiers à part : un filtre de pgfplots sur 2 550 lignes écrit une note par point
    # écarté et rend la compilation lente.
    ecrire("synthese-queue-base.csv", ["kl_base", "kl_syn"], [l[:2] for l in lignes if l[3] in (1, 3)])
    ecrire("synthese-queue-syn.csv", ["kl_base", "kl_syn"], [l[:2] for l in lignes if l[3] in (2, 3)])
    nombre("n-1pct", n1, "calculé : ⌊positions / 100⌋")
    nombre("n-1pct-part", n1 / len(kb), "calculé : ⌊positions / 100⌋ / positions")
    nombre("queue-communes", len(queue_b & queue_s), "calculé depuis les positions")
    par_fen: dict[str, int] = {}
    for i in queue_b:
        par_fen[pb[i]["fenetre"]] = par_fen.get(pb[i]["fenetre"], 0) + 1
    nombre("queue-base-fenetre-max", max(par_fen.values()), "calculé depuis les positions (queue de la base)")
    nombre("queue-base-fenetres", len(par_fen), "calculé depuis les positions (queue de la base)")
    negatives = [x for x in kb + ks if x < 0]
    # La légende dit « la seule KL sous le plancher est négative » : vrai seulement si les deux comptes
    # désignent la même position.
    sous = [i for i, (b, s_) in enumerate(zip(kb, ks)) if min(b, s_) < PLANCHER_KL]
    assert sous == [i for i, (b, s_) in enumerate(zip(kb, ks)) if min(b, s_) < 0], "une KL sous le plancher n'est pas négative"
    nombre("kl-negatives", len(negatives), sb + ", " + ss)
    nombre("kl-negative", min(kb + ks), sb + ", " + ss)
    nombre("positions", len(kb), sb)
    nombre("fenetres", len({r["fenetre"] for r in pb}), sb)
    nombre("sous-plancher", sum(1 for b, s in zip(kb, ks) if min(b, s) < PLANCHER_KL), sb + ", " + ss)
    nombre("plancher", PLANCHER_KL, "choisi pour l'axe logarithmique")
    nombre("med-base", jb["kl_mediane"], "kl-frontiere-juge.json")
    nombre("med-syn", js["kl_mediane"], "kl-synonyme-d1-juge.json")
    nombre("med-rapport", jb["kl_mediane"] / js["kl_mediane"], "calculé")
    nombre("moy-base", jb["kl_moyenne"], "kl-frontiere-juge.json")
    nombre("moy-syn", js["kl_moyenne"], "kl-synonyme-d1-juge.json")
    nombre("moy-rapport", jb["kl_moyenne"] / js["kl_moyenne"], "calculé")
    nombre("p999-base", jb["kl_p999"], "kl-frontiere-juge.json")
    nombre("p999-syn", js["kl_p999"], "kl-synonyme-d1-juge.json")
    for nom, v in (("base", kb), ("syn", ks)):
        tri = sorted(v, reverse=True)
        nombre(f"part-1pct-{nom}", sum(tri[: len(v) // 100]) / sum(v), "calculé depuis les positions")
        nombre(f"part-10pct-{nom}", sum(tri[: len(v) // 10]) / sum(v), "calculé depuis les positions")
    gagne = sum(1 for b, s in zip(kb, ks) if s < b)
    nombre("positions-gagnees", gagne, "calculé depuis les positions")
    # Densités marginales en log10, 48 cases de 1e-5 à 10 (sommes à 1 sur les positions).
    bornes = [-5 + 6 * i / 48 for i in range(49)]
    for nom, v in (("base", kb), ("syn", ks)):
        h = [0] * 48
        for x in v:
            lx = math.log10(max(x, PLANCHER_KL))
            k = min(47, max(0, int((lx - bornes[0]) / (bornes[1] - bornes[0]))))
            h[k] += 1
        larg = bornes[1] - bornes[0]
        ecrire(f"synthese-densite-{nom}.csv", ["log10_kl", "densite"],
               [[f"{bornes[0] + larg * (k + 0.5):.4f}", f"{h[k] / (len(v) * larg):.6f}"] for k in range(48)])


def colonnes() -> None:
    src = "mesures/genome/genome/csv/colonnes-energie-erreur.csv"
    rows = lire_csv(GEN / "colonnes-energie-erreur.csv")
    cles = ("energie_exacte", "erreur_brin_pondere", "erreur_s_etoile", "erreur_base")
    moy = {k: statistics.fmean(float(r[k]) for r in rows) for k in cles}
    ecrire("synthese-colonnes.csv", ["colonne", "energie", "brin", "sstar", "base"],
           [[r["colonne"]] + [f"{float(r[k]) / moy[k]:.5e}" for k in cles] for r in rows])
    m = max(range(len(rows)), key=lambda i: float(rows[i]["energie_exacte"]))
    nombre("col-massive", int(rows[m]["colonne"]), src)
    nombre("col-n", len(rows), src)
    for k, cle in zip(cles, ("energie", "brin", "sstar", "base")):
        nombre(f"col-{cle}-x", float(rows[m][k]) / moy[k], src + " (calculé : rapport à la moyenne des colonnes)")
    # Les colonnes de rang 0 modulo 64 (bord des morceaux de la rotation) : part de l'erreur du brin.
    bord = [float(r["erreur_brin_pondere"]) for r in rows if int(r["colonne"]) % 64 == 0 and int(r["colonne"]) != m]
    nombre("col-bord-x", statistics.fmean(bord) / moy["erreur_brin_pondere"], src + " (calculé, colonne massive exclue)")
    # Les autres colonnes du morceau de 64 de la rotation qui contient la colonne massive.
    debut = 64 * (m // 64)
    morceau = [float(r["erreur_brin_pondere"]) for r in rows if debut <= int(r["colonne"]) < debut + 64 and int(r["colonne"]) != m]
    nombre("col-morceau-debut", debut, src)
    nombre("col-morceau-fin", debut + 63, src)
    nombre("col-morceau-x", statistics.fmean(morceau) / moy["erreur_brin_pondere"], src + " (calculé, colonne massive exclue)")
    # Troisième passe (N2 du juge ronde du second flux, DN9 du juge de design) : la seconde pointe de l'erreur
    # du brin, la colonne qui en reçoit le plus après la géante, et les moyennes sans elle. Ce n'est pas une
    # constante : le script la cherche, puis dit où elle est (dans le morceau de la géante, sur un bord ou non).
    s = max((i for i in range(len(rows)) if i != m), key=lambda i: float(rows[i]["erreur_brin_pondere"]))
    cs = int(rows[s]["colonne"])
    assert int(rows[m]["colonne"]) == m and cs == s, "les colonnes ne sont pas dans l'ordre naturel"
    nombre("col-second", cs, src + " (la plus grande erreur du brin après la géante)")
    for k, cle in zip(cles, ("energie", "brin", "sstar", "base")):
        nombre(f"col-second-{cle}-x", float(rows[s][k]) / moy[k], src + " (calculé : rapport à la moyenne des colonnes)")
    nombre("col-second-bord", int(cs % 64 == 0), src + " (1 si la seconde pointe est un bord de morceau)")
    nombre("col-second-morceau", int(debut <= cs < debut + 64), src + " (1 si elle est dans le morceau de la géante)")
    autres_bords = [float(r["erreur_brin_pondere"]) for r in rows
                    if int(r["colonne"]) % 64 == 0 and int(r["colonne"]) not in (m, cs)]
    nombre("col-bord-autres-n", len(autres_bords), src)
    nombre("col-bord-autres-x", statistics.fmean(autres_bords) / moy["erreur_brin_pondere"], src + " (calculé, géante et seconde pointe exclues)")
    nombre("col-bord-autres-max-x", max(autres_bords) / moy["erreur_brin_pondere"], src + " (calculé, géante et seconde pointe exclues)")
    sans = [float(r["erreur_brin_pondere"]) for r in rows
            if debut <= int(r["colonne"]) < debut + 64 and int(r["colonne"]) not in (m, cs)]
    nombre("col-morceau-sans-n", len(sans), src)
    nombre("col-morceau-sans-x", statistics.fmean(sans) / moy["erreur_brin_pondere"], src + " (calculé, géante et seconde pointe exclues)")


def main() -> int:
    D.mkdir(parents=True, exist_ok=True)
    frontiere()
    erreur_kl()
    deux_parts()
    colonnes()
    ecrire("synthese-nombres.csv", ["cle", "valeur", "source"], [list(n) for n in NOMBRES])
    for c, v, _ in NOMBRES:
        print(f"{c:22s} {v}")
    print("écrit :", sorted(p.name for p in D.glob("synthese-*.csv")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
