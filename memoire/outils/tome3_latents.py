"""Données des figures du lot « espaces latents » du Tome III (III-7.6, III-9.1 (d), III-9.7), tirées des
fichiers commités de mesures/genome/tome3/latents/ (écrits par outils/genome/tome3/latents_*.py), de
mesures/genome/construction/synonyme/figures/spectre-L08-E00-gate.csv (lot B) et, pour un témoin et deux
nombres de l'espace d'origine, de outils/genome/tome3/juge-latents/juge-etats-marges.json (juge du premier
flux). Aucun chiffre recopié à la main : chaque nombre des légendes et des annotations est une macro de
latents-chiffres.tex, écrite ici. Aucune passe du modèle : tout se tire des fichiers commités.

Second flux (2026-10-27) : la palette et la légende du Tome III (palette-tome3.tex, legende-tome3.tex), et
les graves du juge de design G1 (couleurs du dictionnaire), G2 (III-7.6 en petits multiples, la taille
remplacée par la marge z(1) − z(2), celle de la couleur) et D20 (III-9.7 lu par la fonction d'appui).

Écrit sous memoire/figures/tome3/donnees/ (virgule, fin de ligne LF, lisible par pgfplots) :
  latents-etats-acp.csv, latents-etats-tsne.csv : x, y, groupe (g1 à g8 : les huit experts premiers les
                       plus fréquents, rangés par fréquence ; « autres »), marge (« petite » si la marge
                       z(1) − z(2) est sous son 10e centile, « autre » sinon) ; les petites en dernier ;
  latents-etats-tsne-g1.csv … g8.csv : les états d'un expert premier dans le plan t-SNE (x, y, marge) ;
  latents-etats-reperes.csv : pour chaque groupe, l'expert, sa part, et la place de son nom dans les deux
                       plans : l'ancre (l'état du groupe le plus entouré des siens : moyenne minimale des
                       distances à ses 30 plus proches voisins du même groupe) et l'étiquette (l'ancre, écartée
                       des autres noms s'ils se recouvrent) ;
  latents-rangee.csv, latents-rangee-change.csv, latents-rangee-garde.csv : la rangée de 32 poids
                       (tous, puis ceux dont le symbole change, puis ceux dont il ne change pas) ;
  latents-rangee-niveaux.csv : les huit niveaux ± centres de la base ;
  latents-appui-{frontiere,synonyme}-{12,13}.csv : la fonction d'appui θ ↦ ‖ΔW v(θ)‖ dans les plans
                       (u1, u2) et (u1, u3), en coordonnées cartésiennes (x = h cos θ, y = h sin θ) ;
  latents-rose-{12,13}.csv : la rose des directions des entrées (une barre radiale par tranche de 3°, en
                       anneau entre les deux courbes ; sa place radiale n'a pas d'unité) ;
  latents-barres.csv : axe k, λ_k, rapport synonyme / frontière de ‖ΔW u_k‖ ;
  latents-barres-entrees.csv : (troisième passe) le même rapport sur les entrées réelles entières, médiane et
                       étendue, lues dans le journal du juge latents du second flux (témoin E1, voir
                       entrees_reelles()) ;
  latents-chiffres.tex : les nombres, en macros bilingues \\EF{anglais}{français} ;
  latents-temoins.json : les témoins de ce script (bord des états, fonction d'appui) et leurs cassures.

La fonction d'appui. Le lot a commité, pour chaque base et chaque plan, 181 points de l'image du cercle unité
par F·M^{1/2}, M = Bᵀ ΔWᵀ ΔW B (B = [u_a u_b]). Ces points vérifient pᵀ M⁻¹ p = 1 pour p = point / F ; M se
retrouve donc par moindres carrés (trois inconnues, 181 équations), et la fonction d'appui de l'ellipse est
h(v) = √(vᵀ M v) = ‖ΔW v‖ : l'erreur de sortie pour une entrée unité de direction v. Témoin A1 : la diagonale de
M redonne e_1, e_2 (plan 12) et e_1, e_3 (plan 13) du JSON du lot, et ses demi-axes les demi-axes bruts du même
JSON ; cassure (--casse-appui) : F faux de 1 %, le témoin tombe.

Le bord des états. Bord d'un état : part de ses 10 plus proches voisins (dans le plan t-SNE, distance
euclidienne, l'état exclu) dont l'expert premier diffère du sien. Témoin B1 : par classe de marge z(1) − z(2)
(sous le 10e centile, jusqu'à la médiane, au-delà), il redonne les trois valeurs « bord_tsne » du juge ;
cassure (--casse-bord) : 9 voisins au lieu de 10, le témoin tombe.

  python -I -X utf8 memoire/outils/tome3_latents.py [--casse-appui] [--casse-bord]
"""
from __future__ import annotations

import csv
import json
import math
import pathlib
import sys

import numpy as np

RACINE = pathlib.Path(__file__).resolve().parents[2]
M = RACINE / "mesures/genome/tome3/latents"
SPECTRE = RACINE / "mesures/genome/construction/synonyme/figures/spectre-L08-E00-gate.csv"
JUGE_MARGES = RACINE / "outils/genome/tome3/juge-latents/juge-etats-marges.json"
# Troisième passe (GN1 du juge latents du second flux) : le rapport synonyme / frontière sur les entrées réelles
# entières (2 880 dimensions), refait par ce juge depuis le GGUF, les .sym et les captures ; lu ici, et relié au
# spectre commité du lot B par un témoin (voir nuage()).
JUGE2_NUAGE = RACINE / "outils/genome/tome3/juge2-latents/journaux/juge2-nuage-rangee.json"
CASSE_ENTREES = "--casse-entrees" in sys.argv   # cassure du témoin E1 : un λ du spectre faux de 1 %
D = RACINE / "memoire/figures/tome3/donnees"
NOMS = ["Un", "Deux", "Trois", "Quatre", "Cinq", "Six", "Sept", "Huit"]
CASSE_APPUI = "--casse-appui" in sys.argv
CASSE_BORD = "--casse-bord" in sys.argv
CASSE_F = 0.01                        # la cassure de la fonction d'appui : F faux de 1 %
K_BORD_JUGE, K_BORD_CASSE = 10, 9    # le juge : 10 voisins ; la cassure : 9
K_BORD = K_BORD_CASSE if CASSE_BORD else K_BORD_JUGE
K_REPERE = 30                         # voisins du même groupe pour placer le nom d'un expert
ECART_NOMS = (0.10, 0.075)            # boîte d'un nom (largeur, hauteur), en fraction de l'étendue du plan
PAS_ROSE = 3.0                        # degrés par tranche de la rose
MARGE = {1: "petite", 0: "autre"}      # classe de la marge z(1) − z(2) : sous son 10e centile, ou non
TEMOINS: dict = {}


def ecrivain(nom: str, entete: list[str]):
    f = open(D / nom, "w", newline="", encoding="utf-8")
    w = csv.writer(f, delimiter=",", lineterminator="\n")
    w.writerow(entete)
    return f, w


def lire(nom: str) -> list[dict]:
    with open(M / nom, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def nombre(x: float, dec: int) -> tuple[str, str]:
    """(anglais, français) : point ou virgule décimale, espace fine des milliers."""
    s = f"{x:,.{dec}f}"
    ent, _, fr = s.partition(".")
    ent = ent.replace(",", "\\,")
    if ent.startswith("-"):
        ent = "\\ensuremath{-}" + ent[1:]
    return (ent + ("." + fr if fr else ""), ent + ("{,}" + fr if fr else ""))


class Chiffres:
    def __init__(self):
        self.l = ["% Écrit par memoire/outils/tome3_latents.py : ne pas modifier à la main.",
                  "% Nombres des figures du lot « espaces latents » (III-7.6, III-9.1 (d), III-9.7)."]

    def __call__(self, nom: str, x, dec: int = 0, pc: bool = False):
        en, fr = nombre(100 * x if pc else x, dec)
        self.l.append(f"\\providecommand{{\\Lat{nom}}}{{\\EF{{{en}}}{{{fr}}}}}")

    def sci(self, nom: str, x: float):
        """x en notation scientifique, une décimale : 1.8 × 10^-12."""
        e = math.floor(math.log10(abs(x)))
        m = x / 10 ** e
        en, fr = nombre(m, 1)
        self.l.append(f"\\providecommand{{\\Lat{nom}}}{{\\EF{{${en}\\times10^{{{e}}}$}}{{${fr}\\times10^{{{e}}}$}}}}")

    def brut(self, nom: str, x: float, dec: int = 4):
        """Nombre brut (point décimal), pour une coordonnée de TikZ ou de pgfplots."""
        self.l.append(f"\\expandafter\\providecommand\\csname Lat{nom}\\endcsname{{{x:.{dec}f}}}")

    def texte(self, nom: str, s: str):
        self.l.append(f"\\providecommand{{\\Lat{nom}}}{{{s}}}")

    def ecrire(self):
        (D / "latents-chiffres.tex").write_text("\n".join(self.l) + "\n", encoding="utf-8", newline="\n")


# ------------------------------------------------------------------------------------------------------
# III-7.6
def voisins(xy: np.ndarray, k: int, bloc: int = 512) -> np.ndarray:
    """Indices des k plus proches voisins de chaque point (lui-même exclu), par blocs : jamais n × n."""
    n = len(xy)
    sortie = np.empty((n, k), dtype=np.int64)
    n2 = (xy ** 2).sum(1)
    for a in range(0, n, bloc):
        b = min(n, a + bloc)
        d2 = n2[a:b, None] + n2[None, :] - 2.0 * xy[a:b] @ xy.T
        d2[np.arange(b - a), np.arange(a, b)] = np.inf
        idx = np.argpartition(d2, k, axis=1)[:, :k]
        sortie[a:b] = idx
    return sortie


def etats(ch: Chiffres):
    j = json.loads((M / "etats-c23.json").read_text(encoding="utf-8"))
    rows = lire("etats-c23.csv")
    cpt = j["comptes_premier"]
    rang = sorted(range(32), key=lambda e: (-cpt[e], e))[:8]
    groupe = {e: f"g{i + 1}" for i, e in enumerate(rang)}
    n = j["etats"]
    q12 = j["marge12_quantiles"]
    q10, q50 = q12["0.1"], q12["0.5"]

    def classe(m):
        return 0 if m < q10 else (1 if m < q50 else 2)

    premier = np.array([int(r["premier"]) for r in rows])
    marge = np.array([float(r["marge12"]) for r in rows])
    cl = np.array([classe(m) for m in marge])
    fragile = (cl == 0).astype(int)
    ordre = sorted(range(len(rows)), key=lambda i: (fragile[i], int(rows[i]["position"])))
    paires = [("acp", "acp1", "acp2")]
    if j["tsne_gardee"]:
        paires.append(("tsne", "tsne1", "tsne2"))
    coords = {}
    for nom, cx, cy in paires:
        coords[nom] = np.array([[float(r[cx]), float(r[cy])] for r in rows])
        g, w = ecrivain(f"latents-etats-{nom}.csv", ["x", "y", "groupe", "marge"])
        for i in ordre:
            r = rows[i]
            w.writerow([r[cx], r[cy], groupe.get(int(r["premier"]), "autres"), MARGE[fragile[i]]])
        g.close()
    if not j["tsne_gardee"]:
        for p in D.glob("latents-etats-tsne*.csv"):
            p.unlink()
    else:
        for e, gnom in groupe.items():
            g, w = ecrivain(f"latents-etats-tsne-{gnom}.csv", ["x", "y", "marge"])
            for i in ordre:
                if premier[i] == e:
                    w.writerow([rows[i]["tsne1"], rows[i]["tsne2"], MARGE[fragile[i]]])
            g.close()
    # où poser le nom de chaque expert : l'état du groupe le plus entouré des siens, dans chaque plan
    # (l'ancre) ; puis l'étiquette, écartée de l'ancre si deux noms se recouvrent (répulsion simple, en
    # fraction de l'étendue du plan) : un trait de rappel va de l'étiquette à l'ancre.
    ancres = {}
    for nom in coords:
        pts = []
        for e in groupe:
            xy = coords[nom][premier == e]
            d = np.sqrt(((xy[:, None, :] - xy[None, :, :]) ** 2).sum(-1))
            kk = min(K_REPERE, len(xy) - 1)
            s_ = np.sort(d, axis=1)[:, 1:kk + 1].mean(1)
            pts.append(xy[int(np.argmin(s_))])
        ancres[nom] = np.array(pts)
    etiq = {}
    for nom, A in ancres.items():
        etendue = coords[nom].max(0) - coords[nom].min(0)
        boite = np.array(ECART_NOMS) * etendue      # deux noms se recouvrent si |dx| < bx et |dy| < by
        P = A.copy()
        for _ in range(400):
            bouge = False
            for i in range(len(P)):
                for k in range(i + 1, len(P)):
                    dx, dy = P[k] - P[i]
                    px, py = boite[0] - abs(dx), boite[1] - abs(dy)
                    if px > 0 and py > 0:
                        # écarter le long de l'axe où le recouvrement est le plus court (en fraction de la boîte)
                        if px / boite[0] < py / boite[1]:
                            s_ = (1.0 if dx >= 0 else -1.0) * (px / 2 + 1e-6)
                            P[i][0] -= s_
                            P[k][0] += s_
                        else:
                            s_ = (1.0 if dy >= 0 else -1.0) * (py / 2 + 1e-6)
                            P[i][1] -= s_
                            P[k][1] += s_
                        bouge = True
            if not bouge:
                break
        etiq[nom] = P
    g, w = ecrivain("latents-etats-reperes.csv", ["groupe", "expert", "acpx", "acpy", "acplx", "acply",
                                                  "tsnex", "tsney", "tsnelx", "tsnely"])
    for i, (e, gnom) in enumerate(groupe.items()):
        lig = [gnom, e]
        for nom in ("acp", "tsne"):
            if nom not in coords:
                lig += ["nan"] * 4
                continue
            a_, l_ = ancres[nom][i], etiq[nom][i]
            lig += [f"{a_[0]:.6f}", f"{a_[1]:.6f}", f"{l_[0]:.6f}", f"{l_[1]:.6f}"]
        w.writerow(lig)
    g.close()
    # le bord des états (plan t-SNE), par classe de marge z(1) − z(2) ; témoin B1 contre le juge
    if "tsne" in coords:
        vois = voisins(coords["tsne"], K_BORD)
        bord = (premier[vois] != premier[:, None]).mean(1)
        par_classe = [float(bord[cl == c].mean()) for c in range(3)]
        juge = json.loads(JUGE_MARGES.read_text(encoding="utf-8"))
        ref = juge["marge12"]["bord_tsne"]
        ecart = max(abs(a - b) for a, b in zip(par_classe, ref))
        TEMOINS["B1_bord_tsne"] = {"k": K_BORD, "ici": par_classe, "juge": ref, "ecart_max": float(ecart),
                                   "tient": bool(ecart < 1e-12)}
        ch("BordFragile", par_classe[0], 2)
        ch("BordMoyen", par_classe[1], 2)
        ch("BordLarge", par_classe[2], 2)
        bo = juge["marge12"]["bord_origine"]
        ch("BordOrigFragile", bo[0], 2)
        ch("BordOrigLarge", bo[2], 2)
        ch("BordRhoOrig", juge["marge12"]["spearman_marge_bord_origine"], 2)
        ch("BordQuatreCinq", juge["marge45"]["bord_origine"][0], 2)
        # troisième passe (N7 du juge latents) : le terme de comparaison, au-delà de la médiane
        ch("BordQuatreCinqLarge", juge["marge45"]["bord_origine"][2], 2)
    # chiffres
    ch("Etats", n)
    ch("Dim", j["d_modele"])
    ch("Couche", j["couche"])
    v = j["acp_part_variance"]
    ch("AcpVarUn", v[0], 1, pc=True)
    ch("AcpVarDeux", v[1], 1, pc=True)
    ch("AcpVarPlan", j["acp_part_variance_plan"], 1, pc=True)
    for nom, cle in (("Acp", "acp"), ("Tsne", "tsne")):
        f = j["fidelite"][cle]
        ch(f"{nom}T", f["T"], 3)
        ch(f"{nom}C", f["C"], 3)
        ch(f"{nom}Rho", f["spearman"], 2)
        ch(f"{nom}Gardes", f["voisins_gardes"], 1, pc=True)
        ch(f"{nom}Accord", f["accord_premier_plan"], 1, pc=True)
    ch("TsneGainT", j["fidelite"]["tsne"]["T"] - j["fidelite"]["acp"]["T"], 3)
    ch("TsneGainC", j["fidelite"]["tsne"]["C"] - j["fidelite"]["acp"]["C"], 3)
    ch("AccordHaut", j["accord_premier_espace_origine"], 1, pc=True)
    ch("AccordHasard", j["accord_premier_hasard"], 1, pc=True)
    ch("K", j["k_fidelite"])
    ch("Paires", j["paires_spearman"])
    ch.texte("Graine", str(j["graine"]))
    ch("TemoinPermuteT", j["temoin_W1_fidelite"]["cassure_plan_permute_T"], 3)
    ch("WzeroEnsembles", j["temoin_W0_routeur"]["ensembles_egaux"])
    ch("WzeroCassure", j["temoin_W0_routeur"]["cassure_sans_biais_ensembles_egaux"])
    ch("TsnePerplexite", j["tsne_parametres"]["perplexite"])
    ch("TsnePas", j["tsne_parametres"]["pas"])
    ch("TsneKL", j["tsne_journal"][-1]["kl"], 2)
    ch("TsneGardee", 1 if j["tsne_gardee"] else 0)
    for i, e in enumerate(rang):
        ch(f"Groupe{NOMS[i]}", e)
        ch(f"Groupe{NOMS[i]}Part", cpt[e] / n, 1, pc=True)
    part8 = sum(cpt[e] for e in rang) / n
    ch("GroupesPart", part8, 1, pc=True)
    ch("PremiersDistincts", j["experts_premiers_distincts"])
    ch("AutresExperts", j["experts_premiers_distincts"] - 8)
    ch("MargeQuantile", 0.1, 0, pc=True)
    ch("MargeDouzeDix", q10, 4)
    ch("MargeDouzeMed", q50, 3)
    ch("Fragiles", int(fragile.sum()))
    ch("KRepere", K_REPERE)
    ch("KBord", K_BORD)
    ch("KBordCasse", K_BORD_CASSE)


# ------------------------------------------------------------------------------------------------------
# III-9.1 (d)
def rangee(ch: Chiffres):
    j = json.loads((M / "rangee-L08-E00-gate.json").read_text(encoding="utf-8"))
    rows = lire("rangee-L08-E00-gate.csv")

    def s(sym):
        sym = int(sym)
        return ("−" if sym & 4 else "+") + str(sym & 3)

    ent = ["j", "exact", "frontiere", "synonyme", "code", "sf", "ss", "change"]
    g1, w1 = ecrivain("latents-rangee.csv", ent)
    g2, w2 = ecrivain("latents-rangee-change.csv", ent)
    g3, w3 = ecrivain("latents-rangee-garde.csv", ent)
    for r in rows:
        lig = [r["j"], r["exact"], r["frontiere"], r["synonyme"], f"{int(r['code']):X}", s(r["sym_frontiere"]),
               s(r["sym_synonyme"]), r["change"]]
        w1.writerow(lig)
        (w2 if r["change"] == "1" else w3).writerow(lig)
    g1.close()
    g2.close()
    g3.close()
    c = j["centres_E2M1"]["frontiere"]
    assert c == j["centres_E2M1"]["synonyme-l1-d1"]
    g, w = ecrivain("latents-rangee-niveaux.csv", ["k", "y"])
    for k, x in enumerate(c):
        w.writerow([k, f"{x:.6f}"])
        w.writerow([k, f"{-x:.6f}"])
    g.close()
    ch("RangLigne", j["ligne"])
    ch("RangBloc", j["bloc"])
    ch("RangColA", j["colonnes"][0])
    ch("RangColB", j["colonnes"][1])
    ch("RangExposant", j["exposant_e8m0"])
    ch("RangExpoRel", j["exposant_e8m0"] - 127)
    ch("RangChanges", j["changes_dans_le_bloc"])
    ch("RangMediane", j["changes_par_bloc_mediane"])
    ch("RangMoyenne", j["changes_par_bloc_moyenne"], 2)
    ch("RangPartMatrice", j["part_symboles_changes_matrice"], 1, pc=True)
    ch("RangCandidats", j["blocs_candidats"])
    ch.texte("RangGraine", str(j["graine"]))
    ch.sci("RangTemoin", max(r["ecart_relatif"] for r in j["temoin_R0"].values()))
    ch("RangCassure", min(r["cassure_expert1_ecart_relatif"] for r in j["temoin_R0"].values()), 0)
    ch("RangErrF", j["erreur_bloc_unites_s_b2"]["frontiere"], 2)
    ch("RangErrS", j["erreur_bloc_unites_s_b2"]["synonyme-l1-d1"], 2)
    # Troisième passe (N1 du juge latents du second flux) : la tête disait que le synonyme « éloigne ces poids de
    # leur valeur exacte » ; c'est faux pour l'un des quatre (le zéro négatif de j = 11 change de signe à la même
    # distance). Le script compte, parmi les symboles changés, ceux qui s'éloignent et ceux qui restent à la même
    # distance (à 1e-9 près), et s'arrête s'il en trouve un qui se rapproche (la tête ne le dirait pas).
    eloignes = meme = rapproches = 0
    meme_zero = True
    for r in rows:
        if r["change"] != "1":
            continue
        df = abs(float(r["frontiere"]) - float(r["exact"]))
        ds = abs(float(r["synonyme"]) - float(r["exact"]))
        if abs(ds - df) <= 1e-9:
            meme += 1
            meme_zero = meme_zero and float(r["exact"]) == 0.0
        elif ds > df:
            eloignes += 1
        else:
            rapproches += 1
    # la tête dit « l'autre, un zéro » : un seul symbole à même distance, et c'est un zéro
    assert eloignes + meme == j["changes_dans_le_bloc"] and rapproches == 0 and meme == 1 and meme_zero, \
        (eloignes, meme, rapproches)
    ch("RangEloignes", eloignes)
    ch("RangMemeDistance", meme)
    for k, x in enumerate(c):
        ch(f"Centre{NOMS[k]}", x, 3)
    # (a)(b) de III-9.1, depuis le CSV du lot B : énergie de l'erreur et erreur de sortie
    with open(SPECTRE, encoding="utf-8") as f:
        sp = list(csv.DictReader(f))
    ef = sum(float(r["e_frontiere"]) for r in sp)
    es = sum(float(r["e_synonyme"]) for r in sp)
    cf = sum(float(r["lambda_calib"]) * float(r["e_frontiere"]) for r in sp)
    cs = sum(float(r["lambda_calib"]) * float(r["e_synonyme"]) for r in sp)
    vf = sum(float(r["lambda_eval_rayleigh"]) * float(r["e_frontiere"]) for r in sp)
    vs = sum(float(r["lambda_eval_rayleigh"]) * float(r["e_synonyme"]) for r in sp)
    ch("SpecEnergieF", ef, 2)
    ch("SpecEnergieS", es, 2)
    ch("SpecEnergieHausse", es / ef - 1, 0, pc=True)
    ch("SpecCalibF", cf, 2)
    ch("SpecCalibS", cs, 2)
    ch("SpecCalibRapport", cf / cs, 1)
    ch("SpecEvalF", vf, 2)
    ch("SpecEvalS", vs, 2)
    ch("SpecEvalRapport", vf / vs, 2)


# ------------------------------------------------------------------------------------------------------
# III-9.7
def matrice_ellipse(pts: np.ndarray) -> np.ndarray:
    """M (2 × 2) telle que les points vérifient pᵀ M⁻¹ p = 1, par moindres carrés sur (a, b, c) de
    a x² + 2 b x y + c y² = 1."""
    x, y = pts[:, 0], pts[:, 1]
    A = np.stack([x * x, 2 * x * y, y * y], axis=1)
    a, b, c = np.linalg.lstsq(A, np.ones(len(pts)), rcond=None)[0]
    return np.linalg.inv(np.array([[a, b], [b, c]]))


def nuage(ch: Chiffres):
    j = json.loads((M / "nuage-L08-E00-gate.json").read_text(encoding="utf-8"))
    pts = lire("nuage-L08-E00-gate-points.csv")
    ell = lire("nuage-L08-E00-gate-ellipses.csv")
    F = j["facteur_F"] * (1 + CASSE_F if CASSE_APPUI else 1.0)
    e = {"frontiere": j["e_1_3"]["frontiere"], "synonyme": j["e_1_3"]["synonyme-l1-d1"]}
    axes = {"12": (0, 1), "13": (0, 2)}
    th = np.radians(np.arange(0, 361, 1.0))
    v = np.stack([np.cos(th), np.sin(th)], axis=1)
    mats, ecarts = {}, []
    hmax, hfmin, hsmax = 0.0, math.inf, 0.0
    for courbe in ("frontiere", "synonyme"):
        for p in ("12", "13"):
            q = np.array([[float(r["x"]), float(r["y"])] for r in ell
                          if r["courbe"] == courbe and r["plan"] == p]) / F
            Mx = matrice_ellipse(q)
            mats[(courbe, p)] = Mx
            # témoin A1 : diagonale = e_k du lot ; demi-axes = demi-axes bruts du lot
            ia, ib = axes[p]
            diag = [e[courbe][ia], e[courbe][ib]]
            ecarts += [abs(Mx[0, 0] / diag[0] - 1), abs(Mx[1, 1] / diag[1] - 1)]
            cle = ("synonyme-l1-d1" if courbe == "synonyme" else "frontiere") + "-" + p
            da = sorted(np.sqrt(np.linalg.eigvalsh(Mx)), reverse=True)
            ecarts += [abs(a / b - 1) for a, b in zip(da, j["demi_axes_bruts"][cle])]
            h = np.sqrt(np.einsum("ti,ij,tj->t", v, Mx, v))
            hmax = max(hmax, float(h.max()))
            if courbe == "frontiere":
                hfmin = min(hfmin, float(h.min()))
            else:
                hsmax = max(hsmax, float(h.max()))
            g, w = ecrivain(f"latents-appui-{courbe}-{p}.csv", ["theta", "h", "x", "y"])
            for t, hh, (cx, cy) in zip(np.degrees(th), h, v):
                w.writerow([f"{t:.0f}", f"{hh:.6f}", f"{hh * cx:.6f}", f"{hh * cy:.6f}"])
            g.close()
    TEMOINS["A1_appui"] = {"F": F, "ecart_relatif_max": float(max(ecarts)), "tient": bool(max(ecarts) < 1e-6),
                           "regle": "diag(M) = e_k du JSON et demi-axes = demi_axes_bruts, à 1e-6 relatif"}
    # la rose des directions des entrées, posée en anneau entre la courbe synonyme et la courbe frontière
    # (sa place radiale n'a pas d'unité : seule sa direction et sa longueur relative se lisent)
    r0 = 1.35 * hsmax
    longueur = 0.85 * hfmin - r0
    c = np.array([[float(r["c1"]), float(r["c2"]), float(r["c3"])] for r in pts])
    bords = np.arange(-180.0, 180.0 + PAS_ROSE, PAS_ROSE)
    cone_max = 0.0
    for p, (ia, ib) in axes.items():
        ang = np.degrees(np.arctan2(c[:, ib], c[:, ia]))
        cpt, _ = np.histogram(ang, bins=bords)
        g, w = ecrivain(f"latents-rose-{p}.csv", ["theta", "n", "x0", "y0", "dx", "dy"])
        for a, b, nb in zip(bords[:-1], bords[1:], cpt):
            if nb == 0:
                continue
            t = math.radians((a + b) / 2)
            L = longueur * nb / cpt.max()
            w.writerow([f"{(a + b) / 2:.1f}", int(nb), f"{r0 * math.cos(t):.6f}", f"{r0 * math.sin(t):.6f}",
                        f"{L * math.cos(t):.6f}", f"{L * math.sin(t):.6f}"])
        g.close()
        # le cône des entrées : 90 % des directions à moins de ±θ90 de u1 ; le plus grand rapport
        # synonyme / frontière dans ce cône
        t90 = float(np.quantile(np.abs(ang), 0.9))
        tt = np.radians(np.linspace(-t90, t90, 2001))
        vv = np.stack([np.cos(tt), np.sin(tt)], axis=1)
        hs = np.sqrt(np.einsum("ti,ij,tj->t", vv, mats[("synonyme", p)], vv))
        hf = np.sqrt(np.einsum("ti,ij,tj->t", vv, mats[("frontiere", p)], vv))
        nomp = "Douze" if p == "12" else "Treize"
        ch(f"NuageCone{nomp}", t90, 0)
        ch(f"NuageConeRapport{nomp}", float((hs / hf).max()), 3)
        cone_max = max(cone_max, float((hs / hf).max()))
    ch("NuageConeRapport", cone_max, 3)
    ch("NuageRosePas", PAS_ROSE, 0)
    ch("NuageConeQuantile", 0.9, 0, pc=True)
    ch.brut("NuageRose", r0, 6)
    ch.brut("NuageRoseFin", r0 + longueur, 6)
    ch.brut("NuageHmax", hmax, 6)
    ch.brut("NuageRayon", 1.10 * hmax, 6)
    # les barres : rapport le long de u1, u2, u3
    g, w = ecrivain("latents-barres.csv", ["k", "lambda", "rapport"])
    for k in range(3):
        w.writerow([k + 1, f"{j['lambda_1_3'][k]:.4f}", f"{math.sqrt(e['synonyme'][k] / e['frontiere'][k]):.6f}"])
    g.close()
    ch("NuageN", j["n_entrees"])
    for k, x in enumerate(j["lambda_1_3"]):
        ch(f"NuageLambda{NOMS[k]}", x, 1)
    with open(SPECTRE, encoding="utf-8") as f:
        dim = sum(1 for _ in csv.DictReader(f))
    ch("NuageAutresDirections", dim - 3)
    ch.sci("NuageTemoin", max(j["temoin_N0"]["ecarts_relatifs_max"].values()))
    ch("NuageCassure", j["temoin_N0"]["cassure_ecart_relatif"], 1, pc=True)
    ch("NuagePartTrace", j["part_trace_3_axes"], 1, pc=True)
    ch("NuageMoyUn", j["moyenne_c"][0], 1)
    ch("NuageEcartUn", j["ecart_type_c"][0], 2)
    ch("NuageEcartDeux", j["ecart_type_c"][1], 2)
    ch("NuageMoyCarre", j["moyenne_c"][0] ** 2, 0)
    ef, es = e["frontiere"], e["synonyme"]
    for k in range(3):
        ch(f"NuageRapport{NOMS[k]}", math.sqrt(es[k] / ef[k]), 3)
        ch(f"NuageErrF{NOMS[k]}", math.sqrt(ef[k]), 3)
        ch(f"NuageErrS{NOMS[k]}", math.sqrt(es[k]), 4)
    ch.sci("NuageAppuiTemoin", TEMOINS["A1_appui"]["ecart_relatif_max"])
    ch("NuageCasseF", CASSE_F, 0, pc=True)
    ch("NuageEllipsePoints", sum(1 for r in ell if r["courbe"] == "frontiere" and r["plan"] == "12"))
    entrees_reelles(ch, j)


def entrees_reelles(ch: Chiffres, j: dict):
    """Troisième passe (GN1 du juge latents du second flux) : la tête de III-9.7 parlait des projections des
    entrées comme des entrées. Sur les 1 329 entrées réelles entières, le rapport ‖ΔW_s x‖ / ‖ΔW_f x‖ va de 0,49
    à 0,81 ; ce rapport vient du journal du juge (relu du GGUF, des .sym et des captures, pas recopié à la main).

    Témoin E1, qui relie ce journal aux fichiers commités que lit ce script : son rapport quadratique pondéré
    par g² égale √(Σ λ_k e_k(synonyme) / Σ λ_k e_k(frontière)) tiré du spectre du lot B, et sa part de la norme
    pondérée dans les trois premiers axes égale part_trace_3_axes du JSON du lot (à 1e-9 près). Cassure
    (--casse-entrees) : le plus grand λ du spectre faux de 1 % ; E1 tombe."""
    jj = json.loads(JUGE2_NUAGE.read_text(encoding="utf-8"))["entrees_reelles"]
    with open(SPECTRE, encoding="utf-8") as f:
        sp = list(csv.DictReader(f))
    lam = [float(r["lambda_calib"]) for r in sp]
    if CASSE_ENTREES:
        k = max(range(len(lam)), key=lambda i: lam[i])
        lam[k] *= 1.01
    cf = sum(l * float(r["e_frontiere"]) for l, r in zip(lam, sp))
    cs = sum(l * float(r["e_synonyme"]) for l, r in zip(lam, sp))
    e1a = abs(math.sqrt(cs / cf) - jj["rapport_quadratique_pondere_g2"])
    e1b = abs(j["part_trace_3_axes"] - jj["part_de_norme2_dans_u1_u2_u3_ponderee_g2"])
    pf, ps = jj["erreur_ponderee_frontiere"], jj["erreur_ponderee_synonyme"]
    e1c = abs(pf["u1_a_u3"] + pf["autres"] - cf) / cf + abs(ps["u1_a_u3"] + ps["autres"] - cs) / cs
    TEMOINS["E1_entrees_reelles"] = {"ecart_rapport": e1a, "ecart_part_trois_axes": e1b, "ecart_relatif_sommes": e1c,
                                     "tient": bool(e1a < 1e-9 and e1b < 1e-9 and e1c < 1e-9),
                                     "regle": "journal du juge 2 contre spectre du lot B et JSON du lot, à 1e-9"}
    r = jj["rapport_par_entree_2880_dimensions"]
    ch("NuageEntreesMin", r["min"], 2)
    ch("NuageEntreesMed", r["mediane"], 2)
    ch("NuageEntreesMax", r["max"], 2)
    ch.brut("NuageEntreesMaxBrut", r["max"], 4)
    ch("NuageEntreesSousTete", jj["part_des_entrees_sous_le_seuil_de_la_tete"], 0, pc=True)
    ch("NuageHorsTrois", 1 - j["part_trace_3_axes"], 0, pc=True)
    ch("NuageAngleMed", jj["angle_entree_plan_u1_u2_deg"]["mediane"], 0)
    ch("NuageAutresF", pf["autres"], 2)
    ch("NuageAutresS", ps["autres"], 2)
    ch("NuageAutresPartGain", (pf["autres"] - ps["autres"]) / (cf - cs), 0, pc=True)
    # la quatrième barre de (c) : la médiane des entrées réelles et leur étendue
    g, w = ecrivain("latents-barres-entrees.csv", ["k", "rapport", "bas", "haut"])
    w.writerow([4.25, f"{r['mediane']:.6f}", f"{r['mediane'] - r['min']:.6f}", f"{r['max'] - r['mediane']:.6f}"])
    g.close()


def main() -> int:
    global D
    if CASSE_APPUI or CASSE_BORD or CASSE_ENTREES:
        # une cassure n'écrit rien sous donnees/ : ses fichiers vont dans un dossier jetable
        import tempfile
        D = pathlib.Path(tempfile.mkdtemp(prefix="latents-casse-"))
    D.mkdir(parents=True, exist_ok=True)
    ch = Chiffres()
    for nom, f in (("etats-c23.json", etats), ("rangee-L08-E00-gate.json", rangee), ("nuage-L08-E00-gate.json", nuage)):
        if (M / nom).exists():
            f(ch)
        else:
            print(f"absent : {nom} (figure sautée)")
    casse = CASSE_APPUI or CASSE_BORD or CASSE_ENTREES
    if not casse:
        ch.ecrire()
        (D / "latents-temoins.json").write_text(json.dumps(TEMOINS, ensure_ascii=False, indent=1) + "\n",
                                                encoding="utf-8", newline="\n")
    print(json.dumps(TEMOINS, ensure_ascii=False, indent=1))
    tient = all(t["tient"] for t in TEMOINS.values())
    print("témoins :", "tiennent" if tient else "TOMBENT", "(cassure demandée)" if casse else "")
    if not casse:
        print("écrit :", sorted(p.name for p in D.glob("latents-*")))
    return 0 if tient or casse else 1


if __name__ == "__main__":
    raise SystemExit(main())
