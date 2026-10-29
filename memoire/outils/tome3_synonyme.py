"""Données des figures du chapitre 9 du Tome III (lot B, le génome synonyme), tirées des fichiers commités
(aucun chiffre recopié à la main).

Écrit sous memoire/figures/tome3/donnees/ (virgule, LF) :
  synonyme-spectre.csv     : III-9.1 (a), le spectre de H de L8 E0 gate : k, λ_k en calibration, u_kᵀ H_ev u_k ;
  synonyme-energie.csv     : III-9.1 (b), e_k = ‖ΔW u_k‖² lissé par paquets de 60 directions consécutives
                             (λ moyen, e moyen, frontière et synonyme) ;
  synonyme-cumul.csv       : III-9.1 (c), part cumulée de l'erreur de sortie Σ_{j≤k} λ_j e_j / Σ λ_j e_j, en
                             calibration et vue par l'évaluation, frontière et synonyme (une ligne sur 8) ;
  synonyme-survie.csv      : III-9.2, P(KL > t) sur les 2 550 positions de R1 : Q2_0 de llama.cpp, frontière,
                             λ = 1, λ = 0, tous à 768 experts substitués (référence f64) ;
  synonyme-quantiles.csv   : III-9.2, médiane et 99,9e centile de chaque série (marques) ;
  synonyme-foret-*.csv     : III-9.3, différences appariées par fenêtre : R1 (lot B, référence substituée) et
                             fenêtres neuves (juge de la construction), trois comparaisons ;
  synonyme-variantes.csv   : III-9.6, bits par poids (compagnon réel) et KL de bout en bout à 768 experts, avec
                             l'écart-type par fenêtres σ_f (s des dix moyennes de fenêtre / √10) ;
  synonyme-nombres.tex     : les nombres des légendes (macros \\SynoN…).

  python -I -X utf8 memoire/outils/tome3_synonyme.py
"""
from __future__ import annotations

import csv
import json
import math
import pathlib
import statistics

import numpy as np

RACINE = pathlib.Path(__file__).resolve().parents[2]
SY = RACINE / "mesures/genome/construction/synonyme"
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


def sigma_fenetres(lignes: list[dict], col: str = "kl") -> tuple[float, float, int]:
    """Moyenne des positions et σ par fenêtres (JUGEMENT-construction, note pour le mémoire § 1.4)."""
    par = {}
    for r in lignes:
        par.setdefault(int(r["fenetre"]), []).append(float(r[col]))
    moy = [statistics.fmean(v) for _, v in sorted(par.items())]
    tout = [float(r[col]) for r in lignes]
    return statistics.fmean(tout), statistics.stdev(moy) / math.sqrt(len(moy)), len(moy)


def spectre(N: Nombres) -> None:
    lignes = lire_csv(SY / "figures/spectre-L08-E00-gate.csv")
    k = np.array([int(r["k"]) for r in lignes])
    lc = np.array([float(r["lambda_calib"]) for r in lignes])
    le = np.array([float(r["lambda_eval_rayleigh"]) for r in lignes])
    ef = np.array([float(r["e_frontiere"]) for r in lignes])
    es = np.array([float(r["e_synonyme"]) for r in lignes])
    assert np.all(np.diff(lc) <= 0), "λ_k doit décroître"
    # H de calibration est de rang au plus le nombre d'entrées de calibration : au-delà, ses valeurs propres
    # sont nulles à l'arrondi près (|λ| < 1e-10 λ_max) ; on les écrit « nan » pour l'axe logarithmique.
    rang = int((lc > 1e-10 * lc[0]).sum())
    assert np.all(np.abs(lc[rang:]) < 1e-10 * lc[0])
    g, w = ecrivain("synonyme-spectre.csv", ["k", "lambda_calib", "lambda_eval"])
    for i in range(len(k)):
        w.writerow([k[i], f"{lc[i]:.6e}" if i < rang else "nan", f"{le[i]:.6e}"])
    g.close()
    N("SynoNRang", rang, None, "spectre-L08-E00-gate.csv")
    paquet = 60
    g, w = ecrivain("synonyme-energie.csv", ["k_milieu", "lambda", "e_frontiere", "e_synonyme"])
    for d in range(0, len(k), paquet):
        s = slice(d, d + paquet)
        w.writerow([d + paquet // 2, f"{lc[s].mean():.6e}", f"{ef[s].mean():.6e}", f"{es[s].mean():.6e}"])
    g.close()
    cf_cal, cs_cal = np.cumsum(lc * ef), np.cumsum(lc * es)
    cf_ev, cs_ev = np.cumsum(le * ef), np.cumsum(le * es)
    g, w = ecrivain("synonyme-cumul.csv", ["k", "frontiere_calib", "frontiere_eval", "synonyme_calib", "synonyme_eval"])
    rangs = list(range(0, len(k), 8)) + [len(k) - 1]
    for i in rangs:
        w.writerow([k[i], f"{cf_cal[i] / cf_cal[-1]:.5f}", f"{cf_ev[i] / cf_ev[-1]:.5f}",
                    f"{cs_cal[i] / cs_cal[-1]:.5f}", f"{cs_ev[i] / cs_ev[-1]:.5f}"])
    g.close()
    # Les polygones entre la part cumulée en calibration et vue par l'évaluation, synonyme puis frontière.
    # Second flux (G3 du juge des chiffres) : l'aire n'est PAS le sur-apprentissage ; la frontière, qui ne
    # sur-apprend pas (coût vu par l'évaluation ≈ coût de calibration), en a une aussi, qui vient du rang de
    # H (la part cumulée en calibration atteint 1 au rang, par construction). Les deux aires sont tracées.
    for nom, ccal, cev in (("synonyme-cumul-aire.csv", cs_cal, cs_ev),
                           ("synonyme-cumul-aire-frontiere.csv", cf_cal, cf_ev)):
        g, w = ecrivain(nom, ["k", "part"])
        for i in rangs:
            w.writerow([k[i], f"{ccal[i] / ccal[-1]:.5f}"])
        for i in reversed(rangs):
            w.writerow([k[i], f"{cev[i] / cev[-1]:.5f}"])
        g.close()
    # Aire = moyenne sur k de (part en calibration − part vue par l'évaluation) : la définition du juge (L1).
    aire_s = float((cs_cal / cs_cal[-1] - cs_ev / cs_ev[-1]).mean())
    aire_f = float((cf_cal / cf_cal[-1] - cf_ev / cf_ev[-1]).mean())
    N("SynoNAireS", aire_s, 2, "spectre-L08-E00-gate.csv (calculé)")
    N("SynoNAireF", aire_f, 2, "spectre-L08-E00-gate.csv (calculé)")
    # Le sur-apprentissage résiduel (07 § 2) : le coût vu par l'évaluation rapporté au coût de calibration.
    N("SynoNSurF", float(cf_ev[-1] / cf_cal[-1]), 3, "spectre-L08-E00-gate.csv (calculé)")
    N("SynoNSurS", float(cs_ev[-1] / cs_cal[-1]), 2, "spectre-L08-E00-gate.csv (calculé)")
    # M7 : le codeur a minimisé tr(ΔW (H + δ* moy(diag H) I) ΔWᵀ), δ* = 1 (07 § 2) ; moy(diag H) = tr(H)/n.
    moy_diag = float(lc.sum() / len(lc))
    N("SynoNAmorti", moy_diag, 2, "spectre-L08-E00-gate.csv (tr H / 2880)")
    N("SynoNAmortiDessus", int((lc > moy_diag).sum()), None, "spectre-L08-E00-gate.csv (calculé)")
    N("SynoNDirections", len(k), None, "spectre-L08-E00-gate.csv")
    N("SynoNPaquet", paquet, None, "tome3_synonyme.py")
    N("SynoNEnergieF", float(ef.sum()), 2, "spectre-L08-E00-gate.csv")
    N("SynoNEnergieS", float(es.sum()), 2, "spectre-L08-E00-gate.csv")
    N("SynoNEnergieHausse", 100 * float(es.sum() / ef.sum() - 1), 0, "spectre-L08-E00-gate.csv")
    N("SynoNCalibF", float(cf_cal[-1]), 2, "spectre-L08-E00-gate.csv")
    N("SynoNCalibS", float(cs_cal[-1]), 2, "spectre-L08-E00-gate.csv")
    N("SynoNCalibRapport", float(cf_cal[-1] / cs_cal[-1]), 2, "spectre-L08-E00-gate.csv")
    N("SynoNEvalF", float(cf_ev[-1]), 2, "spectre-L08-E00-gate.csv")
    N("SynoNEvalS", float(cs_ev[-1]), 2, "spectre-L08-E00-gate.csv")
    N("SynoNEvalRapport", float(cf_ev[-1] / cs_ev[-1]), 2, "spectre-L08-E00-gate.csv")
    N("SynoNLambdaMax", float(lc[0]), 1, "spectre-L08-E00-gate.csv")
    N("SynoNLambdaEvalMin", float(le.min()), 3, "spectre-L08-E00-gate.csv")
    # part de l'énergie d'erreur (e_k) au-delà du rang, frontière et synonyme
    N("SynoNPartNulleF", 100 * float(ef[rang:].sum() / ef.sum()), 0, "spectre-L08-E00-gate.csv")
    N("SynoNPartNulleS", 100 * float(es[rang:].sum() / es.sum()), 0, "spectre-L08-E00-gate.csv")


def survie(N: Nombres) -> None:
    series = [
        ("q2_0", SY / "repere/kl-q2_0-positions.csv", "repere/kl-q2_0-juge.json"),
        ("frontiere", SY / "kl/kl-frontiere-768-positions.csv", "kl/kl-frontiere-768-juge.json"),
        ("lambda1", SY / "kl/kl-synonyme-768-positions.csv", "kl/kl-synonyme-768-juge.json"),
        ("lambda0", SY / "kl/kl-synonyme-l0-768-positions.csv", "kl/kl-synonyme-l0-768-juge.json"),
    ]
    valeurs = {}
    for nom, chemin, juge in series:
        v = np.array([float(r["kl"]) for r in lire_csv(chemin)])
        assert len(v) == 2550, (nom, len(v))
        resume = lire_json(SY / juge)["resume"]
        assert abs(v.mean() - resume["kl_moyenne"]) < 1e-6, nom  # témoin : la moyenne du juge kl
        valeurs[nom] = v
    # Second flux (G4 du juge de design) : l'axe part de 10⁻² ; à gauche, P(KL > t) vaut presque 1 partout.
    # La part des positions sous 10⁻² est écrite (la plus grande des quatre séries) pour le dire en légende.
    T_GAUCHE = 1e-2
    grille = np.logspace(math.log10(T_GAUCHE), math.log10(8.5), 121)
    g, w = ecrivain("synonyme-survie.csv", ["t"] + [n for n, _, _ in series])
    for t in grille:
        w.writerow([f"{t:.6e}"] + [f"{(valeurs[n] > t).mean():.6f}" for n, _, _ in series])
    g.close()
    N("SynoNSurvieGauche", 100 * max(float((valeurs[n] <= T_GAUCHE).mean()) for n, _, _ in series), 1,
      "kl-*-positions.csv (part des positions sous 0,01, la plus grande des quatre)")
    # La médiane : la frontière divisée par chaque synonyme (le « ÷ » du rappel de la figure).
    med = {n: lire_json(SY / j)["resume"]["kl_mediane"] for n, _, j in series}
    N("SynoNDivUn", med["frontiere"] / med["lambda1"], 2, "kl-*-768-juge.json (rapport des médianes)")
    N("SynoNDivZero", med["frontiere"] / med["lambda0"], 2, "kl-*-768-juge.json (rapport des médianes)")
    # La queue (G4 du juge des chiffres) : combien de positions au-dessus du 99,9e centile, et ce que
    # devient l'écart à la frontière sur les dix fenêtres neuves du juge (chemins : frontière par la
    # référence substituée ; λ = 1 et λ = 0 par le moteur, λ = 1 substitué n'y a pas été passé).
    p999 = {n: float(np.percentile(valeurs[n], 99.9)) for n in valeurs}
    for n in valeurs:  # témoin : le centile numpy redonne celui de « juge kl »
        assert abs(p999[n] - lire_json(SY / dict((a, c) for a, _, c in series)[n])["resume"]["kl_p999"]) < 1e-6, n
    dessus = {int((valeurs[n] > p999[n]).sum()) for n in valeurs}
    assert len(dessus) == 1, dessus
    N("SynoNQueueDessus", dessus.pop(), None, "kl-*-positions.csv (positions au-dessus du 99,9e centile)")
    neuf = {n: np.array([float(r["kl"]) for r in lire_csv(JU / "kl" / f)]) for n, f in
            (("frontiere", "kl-neuf-sub-frontiere-positions.csv"),
             ("lambda1", "kl-neuf-moteur-rapide-l1-positions.csv"),
             ("lambda0", "kl-neuf-moteur-rapide-l0-positions.csv"))}
    for n, v in neuf.items():
        assert len(v) == 2550, (n, len(v))
    q = {n: float(np.percentile(v, 99.9)) for n, v in neuf.items()}
    # Écrites en baisse (positive) : la légende dit « l'abaisse de … » ; une hausse arrêterait le script.
    baisses = {"SynoNQueueUnRun": 1 - p999["lambda1"] / p999["frontiere"],
               "SynoNQueueZeroRun": 1 - p999["lambda0"] / p999["frontiere"],
               "SynoNQueueUnNeuf": 1 - q["lambda1"] / q["frontiere"],
               "SynoNQueueZeroNeuf": 1 - q["lambda0"] / q["frontiere"]}
    for nom, b in baisses.items():
        assert b > 0, (nom, b)
        N(nom, 100 * b, 1, "kl-*-768-positions.csv, juge/kl/kl-neuf-*-positions.csv (baisse au 99,9e centile)")
    g, w = ecrivain("synonyme-quantiles.csv", ["serie", "mediane", "p_mediane", "p999", "p_p999"])
    for n, _, juge in series:
        resume = lire_json(SY / juge)["resume"]
        med, p999 = resume["kl_mediane"], resume["kl_p999"]
        w.writerow([n, f"{med:.6e}", f"{(valeurs[n] > med).mean():.6f}", f"{p999:.6e}", f"{(valeurs[n] > p999).mean():.6f}"])
        nom = {"q2_0": "Q", "frontiere": "F", "lambda1": "Un", "lambda0": "Zero"}[n]
        N(f"SynoNMed{nom}", med, 3, juge)
        N(f"SynoNQueue{nom}", p999, 2, juge)
    N("SynoNPositions", 2550, None, "kl-*-positions.csv")


def foret(N: Nombres) -> None:
    juge = lire_csv(JU / "figures/apparie-par-fenetre.csv")

    def du_juge(comp: str) -> list[float]:
        v = [(int(r["fenetre"]), float(r["d"])) for r in juge if r["comparaison"] == comp]
        assert len(v) == 10, comp
        return [d for _, d in sorted(v)]

    def du_lot(nom: str) -> list[float]:
        return [float(r["d"]) for r in sorted(lire_csv(SY / "kl" / nom), key=lambda r: int(r["fenetre"]))]

    comparaisons = {
        # (fichier, [(bande, chemin, valeurs)])
        "un-frontiere": [("r1", "lot B, référence substituée", du_lot("apparie-768-par-fenetre.csv")),
                         ("neuf", "juge, moteur", du_juge("neuf-l1-moteur-contre-frontiere-sub"))],
        "zero-un": [("r1", "lot B, référence substituée", du_lot("apparie-l1-contre-l0-768-par-fenetre.csv")),
                    ("neuf", "juge, moteur", du_juge("neuf-moteur-l0-contre-l1"))],
        "zero-frontiere": [("r1", "juge, référence substituée", du_juge("r1-l0-contre-frontiere")),
                           ("neuf", "juge, référence substituée", du_juge("neuf-sub-l0-contre-frontiere"))],
    }
    # Témoin : le juge redonne les différences du lot B sur R1 (même chemin, autre outil).
    for a, b in ((du_lot("apparie-l1-contre-l0-768-par-fenetre.csv"), du_juge("r1-l0-contre-l1")),
                 (du_lot("apparie-768-par-fenetre.csv"), du_juge("r1-l1-contre-frontiere"))):
        assert max(abs(x - y) for x, y in zip(a, b)) < 1e-6
    # Second flux (G1 du juge des chiffres, G3 du juge de design) : un seul axe pour les trois panneaux, tiré
    # des données (bornes arrondies au pas de 0,02 vers l'extérieur, avec une marge de 0,01) ; la règle :
    # aucun point ni aucune bande ±2σ ne sort du cadre, sinon le script s'arrête.
    tout = [d for b in comparaisons.values() for _, _, v in b for d in v]
    bandes = []
    for b in comparaisons.values():
        for _, _, v in b:
            m, s = statistics.fmean(v), statistics.stdev(v) / math.sqrt(len(v))
            bandes += [m - 2 * s, m + 2 * s]
    # Troisième passe (DN18 du juge de design) : la marge passe de 0,01 à 0,02, la fenêtre 7 de R1 (−0,345) était
    # dessinée sur le trait du cadre (−0,36) ; elle en est maintenant à plus d'une marque de distance.
    MARGE_FORET = 0.02
    xmin = math.floor((min(tout + bandes) - MARGE_FORET) / 0.02) * 0.02
    xmax = math.ceil((max(tout + bandes) + MARGE_FORET) / 0.02) * 0.02
    assert all(xmin + MARGE_FORET <= d + 1e-12 and d <= xmax - MARGE_FORET + 1e-12 for d in tout + bandes)
    N("SynoNForXmin", xmin, 2, "synonyme-foret-*.csv (borne commune)")
    N("SynoNForXmax", xmax, 2, "synonyme-foret-*.csv (borne commune)")
    # G5 : le panneau 1 des neuves mêle deux chemins (λ = 1 par le moteur, frontière par la référence
    # substituée). Ce que le mélange déplace, mesuré sur R1 où les deux chemins existent pour les deux
    # variantes (L4 du juge) : d̄ du mélange contre d̄ de chacun des deux chemins seuls.
    def kl_fen(chemin: pathlib.Path) -> list[float]:
        par = {}
        for r in lire_csv(chemin):
            par.setdefault(int(r["fenetre"]), []).append(float(r["kl"]))
        return [statistics.fmean(par[f]) for f in sorted(par)]
    sub_f, sub_u = kl_fen(SY / "kl/kl-frontiere-768-positions.csv"), kl_fen(SY / "kl/kl-synonyme-768-positions.csv")
    mot_f = kl_fen(SY / "moteur/kl-moteur-frontiere-positions.csv")
    mot_u = kl_fen(SY / "moteur/kl-moteur-synonyme-positions.csv")
    dbar = lambda b, a: statistics.fmean(x - y for x, y in zip(b, a))  # noqa: E731
    melange, seul_sub, seul_mot = dbar(mot_u, sub_f), dbar(sub_u, sub_f), dbar(mot_u, mot_f)
    N("SynoNForMelange", max(abs(melange - seul_sub), abs(melange - seul_mot)), 4,
      "synonyme/kl, synonyme/moteur (R1, d̄ du mélange contre chaque chemin seul)")
    noms = {"un-frontiere": "UnF", "zero-un": "ZeroUn", "zero-frontiere": "ZeroF"}
    for cle, bandes in comparaisons.items():
        g, w = ecrivain(f"synonyme-foret-{cle}.csv", ["bande", "fenetre", "y", "d"])
        for ib, (bande, _, v) in enumerate(bandes):
            for f, d in enumerate(v):
                # y : rang vertical, R1 en haut (fenêtres 0 à 9), neuves en dessous, trois rangs de blanc entre
                w.writerow([bande, f, 23 - f if bande == "r1" else 10 - f, f"{d:.6f}"])
        g.close()
        g, w = ecrivain(f"synonyme-foret-{cle}-moyennes.csv", ["bande", "y", "moyenne", "deux_sigma", "z", "negatives"])
        for bande, _, v in bandes:
            m = statistics.fmean(v)
            s = statistics.stdev(v) / math.sqrt(len(v))
            y = 18.5 if bande == "r1" else 5.5
            w.writerow([bande, y, f"{m:.6f}", f"{2 * s:.6f}", f"{abs(m) / s:.2f}", sum(1 for d in v if d < 0)])
            p = noms[cle] + ("Run" if bande == "r1" else "Neuf")
            N(f"SynoNFor{p}Moy", m, 4, f"synonyme-foret-{cle}")
            N(f"SynoNFor{p}Sig", s, 4, f"synonyme-foret-{cle}")
            N(f"SynoNFor{p}Z", abs(m) / s, 1, f"synonyme-foret-{cle}")
            N(f"SynoNFor{p}Neg", sum(1 for d in v if d < 0), None, f"synonyme-foret-{cle}")
        g.close()
    # Troisième passe (N7 du juge des chiffres de la construction, second flux) : la tête ne dit plus « fenêtre par
    # fenêtre » sans réserve ; elle dit dans combien de fenêtres au moins, sur chaque jeu, chaque synonyme bat la
    # frontière (λ = 1 contre frontière sur les neuves : 9 sur 10, la fenêtre 2 contre).
    contre_f = [sum(1 for d in v if d < 0) for cle in ("un-frontiere", "zero-frontiere") for _, _, v in comparaisons[cle]]
    n_fen = {len(v) for b in comparaisons.values() for _, _, v in b}
    assert n_fen == {10}, n_fen
    N("SynoNForBatMin", min(contre_f), None, "synonyme-foret-*-frontiere (le moins de fenêtres gagnées)")
    N("SynoNForFenetres", n_fen.pop(), None, "synonyme-foret-* (fenêtres par jeu)")


def variantes(N: Nombres) -> None:
    table = {r["variante"]: r for r in lire_csv(SY / "figures/variantes-768.csv")}
    pos = {
        "frontiere": SY / "kl/kl-frontiere-768-positions.csv",
        "synonyme-l1": SY / "kl/kl-synonyme-768-positions.csv",
        "synonyme-l0": SY / "kl/kl-synonyme-l0-768-positions.csv",
        "llama-q2_0": SY / "repere/kl-q2_0-positions.csv",
    }
    g, w = ecrivain("synonyme-variantes.csv", ["variante", "bits", "kl", "sigma_f", "deux_sigma_f", "sigma_n"])
    for v, chemin in pos.items():
        m, s, n = sigma_fenetres(lire_csv(chemin))
        assert n == 10 and abs(m - float(table[v]["kl"])) < 1e-6, v
        w.writerow([v, f"{float(table[v]['bits_par_poids']):.4f}", f"{m:.6f}", f"{s:.6f}", f"{2 * s:.6f}",
                    f"{float(table[v]['kl_incertitude']):.6f}"])
    # Le moteur exact (lot O, C4) : KL contre la référence f64, mêmes 10 fenêtres de R1 ; bits du v1.0 du 20b.
    exact = lire_csv(RACINE / "mesures/moteur/O/journaux/o3/c4-20b-comparer.csv")
    m, s, n = sigma_fenetres(exact, "kl_b")
    c4 = lire_json(RACINE / "mesures/moteur/O/journaux/o3/c4-20b-comparer.json")
    assert abs(m - c4["b_contre_verite"]["kl_moyenne"]) < 1e-9
    # Second flux (M11) : les bits du moteur exact suivent la définition des compagnons (bits utiles du
    # fichier, décodeur du juge, J-T0-fichiers.json), et non plus bpp_total_03 de tailles.json (3,8506).
    bits_exact = lire_json(JU / "J-T0-fichiers.json")["fichiers"]["20b-v10"]["bits_par_poids_utiles"]
    w.writerow(["exact", f"{bits_exact:.4f}", f"{m:.6f}", f"{s:.6f}", f"{2 * s:.6f}",
                f"{c4['b_contre_verite']['kl_incertitude']:.6f}"])
    g.close()
    N("SynoNAchatKL", float(table["synonyme-l1"]["kl"]) - float(table["synonyme-l0"]["kl"]), 4, "variantes-768.csv")
    N("SynoNAchatBits", float(table["synonyme-l0"]["bits_par_poids"]) - float(table["synonyme-l1"]["bits_par_poids"]), 4, "variantes-768.csv")
    N("SynoNExactBits", bits_exact, 2, "juge/J-T0-fichiers.json (bits utiles du v1.0 du 20b)")
    N("SynoNExactKL", m, 4, "c4-20b-comparer.json")
    # G7 du juge de design : le cadre principal ne tient que les trois variantes (frontière, λ = 1, λ = 0) et
    # leurs barres ±2σ ; Q2_0 et le moteur exact passent en repères de marge. Bornes tirées des données
    # (bits : marge 0,04 arrondie au pas de 0,02 ; KL, logarithmique : ×0,85 et ×1,04 arrondis au centième).
    trois = [r for r in csv.DictReader(open(D / "synonyme-variantes.csv", encoding="utf-8"))
             if r["variante"] in ("frontiere", "synonyme-l1", "synonyme-l0")]
    bx = [float(r["bits"]) for r in trois]
    bas = [float(r["kl"]) - float(r["deux_sigma_f"]) for r in trois]
    haut = [float(r["kl"]) + float(r["deux_sigma_f"]) for r in trois]
    # Troisième passe (G7 du juge de design, second flux) : avec une marge de 0,04 bit arrondie au pas de 0,02, les
    # variantes ne couvraient que 47,6 % de la largeur du cadre (2,54 à 2,72), sous le seuil de plus de 50 % que le
    # juge avait déclaré avant de lire. La marge passe à 0,02 bit, arrondie au pas de 0,01 (2,56 à 2,70 ici) ; la
    # règle est vérifiée ici : si les variantes couvrent la moitié du cadre ou moins, le script s'arrête.
    MARGE_BITS, PAS_BITS, PART_MIN = 0.02, 0.01, 0.5
    xmin = math.floor(round((min(bx) - MARGE_BITS) / PAS_BITS, 9)) * PAS_BITS
    xmax = math.ceil(round((max(bx) + MARGE_BITS) / PAS_BITS, 9)) * PAS_BITS
    ymin, ymax = math.floor(0.85 * min(bas) * 100) / 100, math.ceil(1.04 * max(haut) * 100) / 100
    assert all(xmin < b < xmax for b in bx) and ymin < min(bas) and max(haut) < ymax
    part_largeur = (max(bx) - min(bx)) / (xmax - xmin)
    assert part_largeur > PART_MIN, f"les variantes couvrent {part_largeur:.1%} de la largeur du cadre"
    N("SynoNVarPartLargeur", 100 * part_largeur, 1, "synonyme-variantes.csv (part de la largeur du cadre, %)")
    # Les deux repères sont bien hors du cadre (sinon ils devraient y être dessinés).
    q = next(r for r in csv.DictReader(open(D / "synonyme-variantes.csv", encoding="utf-8")) if r["variante"] == "llama-q2_0")
    assert float(q["bits"]) < xmin and float(q["kl"]) > ymax and bits_exact > xmax and m < ymin
    N("SynoNVarXmin", xmin, 2, "synonyme-variantes.csv (cadre)")
    N("SynoNVarXmax", xmax, 2, "synonyme-variantes.csv (cadre)")
    N("SynoNVarYmin", ymin, 2, "synonyme-variantes.csv (cadre)")
    N("SynoNVarYmax", ymax, 2, "synonyme-variantes.csv (cadre)")
    rapports = []
    for v in pos:
        _, ss, _ = sigma_fenetres(lire_csv(pos[v]))
        rapports.append(ss / float(table[v]["kl_incertitude"]))
    # σ par fenêtres sur σ par positions (publié dans 07) : « de trois à neuf fois » n'est plus tapé (M14).
    N("SynoNSigmaRapportMin", min(rapports), 1, "positions par fenêtre, variantes-768.csv")
    N("SynoNSigmaRapportMax", max(rapports), 1, "positions par fenêtre, variantes-768.csv")
    for v, nom in (("frontiere", "F"), ("synonyme-l1", "Un"), ("synonyme-l0", "Zero"), ("llama-q2_0", "Q")):
        mm, ss, _ = sigma_fenetres(lire_csv(pos[v]))
        N(f"SynoNVar{nom}Bits", float(table[v]["bits_par_poids"]), 4, "variantes-768.csv")
        N(f"SynoNVar{nom}KL", mm, 4, "variantes-768.csv")
        N(f"SynoNVar{nom}Sf", ss, 4, "positions par fenêtre")
        N(f"SynoNVar{nom}Sn", float(table[v]["kl_incertitude"]), 4, "variantes-768.csv")


def main() -> int:
    D.mkdir(parents=True, exist_ok=True)
    N = Nombres()
    spectre(N)
    survie(N)
    foret(N)
    variantes(N)
    N.ecrire("synonyme-nombres.tex", "Nombres des figures du chapitre 9 du Tome III (tome3_synonyme.py).")
    print("écrit :", sorted(p.name for p in D.glob("synonyme-*")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
