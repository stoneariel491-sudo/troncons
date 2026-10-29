"""Juge des chiffres du second flux, lot « construction » : un point tiré au hasard dans chaque série NEUVE
ou CHANGÉE des CSV du lot, recalculé à la source (fichiers commités sous mesures/), par un code écrit ici.

Séries contrôlées (celles que le second flux a ajoutées ou réécrites) :
  codon-roue.csv (parts des 72 tenseurs, valeurs OCP), codon-sans-perte.csv (trois colonnes, retenu, perd),
  codon-theoreme-{20b,120b}.csv (résidu), codon-j1-encart.csv (cinq barres), codon-j1-cascade.csv (couleurs),
  juge-grille-marge.csv, synonyme-cumul-aire-frontiere.csv (aller et retour du polygone),
  synonyme-survie.csv (quatre séries, grille neuve), synonyme-variantes.csv (ligne du moteur exact).
Graine 31415, écrite ici avant tout tirage. Égalité à l'arrondi écrit dans le CSV (demi-unité du dernier
chiffre, plus 1e-12).

Cassure (--casser) : la valeur recalculée décalée d'un millième relatif ; les contrôles non nuls tombent.

    python -I -X utf8 points.py [--casser]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import pathlib
import random
import sys

import numpy as np

RACINE = pathlib.Path(__file__).resolve().parents[4]
MES = RACINE / "mesures"
CO = MES / "genome/construction"
DON = RACINE / "memoire/figures/tome3/donnees"
GRAINE = 31415
E2M1_OCP = [0, 0.5, 1, 1.5, 2, 3, 4, 6]  # norme OCP MX, magnitude des 3 bits bas


def lc(p):
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def lj(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


class Controle:
    def __init__(self, casser: bool):
        self.casser, self.n, self.ecarts, self.lignes = casser, 0, 0, []

    def __call__(self, quoi: str, ecrit: str, vrai: float | str) -> None:
        self.n += 1
        if isinstance(vrai, str):
            ok = ecrit == vrai and not (self.casser and False)
            moi = vrai
        else:
            v = vrai * (1.001 if self.casser else 1.0)
            dec = len(ecrit.split(".")[1]) if "." in ecrit and "e" not in ecrit.lower() else None
            if "e" in ecrit.lower():
                mant = ecrit.lower().split("e")[0]
                d = len(mant.split(".")[1]) if "." in mant else 0
                tol = 0.5 * 10 ** (math.floor(math.log10(abs(float(ecrit)))) - d) if float(ecrit) else 1e-12
            else:
                tol = 0.5 * 10 ** (-(dec or 0))
            ok = abs(float(ecrit) - v) <= tol + 1e-12
            moi = f"{v:.10g}"
        self.ecarts += 0 if ok else 1
        self.lignes.append(f"{'tient ' if ok else 'ÉCART '} {quoi} : CSV {ecrit}, source {moi}")


def par_fenetre(p):
    s, n = np.zeros(10), np.zeros(10)
    for r in lc(p):
        s[int(r["fenetre"])] += float(r["kl"])
        n[int(r["fenetre"])] += 1
    return s / n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--casser", action="store_true")
    a = ap.parse_args()
    rng = random.Random(GRAINE)
    C = Controle(a.casser)

    # codon-roue.csv : un code tiré ; sa part avant et après, sa valeur OCP, depuis l'histogramme des 72 tenseurs.
    z = np.load(MES / "genome/predictif-elagage/histo-toutes-gptoss20b.npz")
    cpt = z["comptes"].astype(np.int64).sum(axis=(0, 1, 2))
    tot = cpt.sum()
    roue = lc(DON / "codon-roue.csv")
    for c in (rng.randrange(16), 0, 8):  # un tiré, plus les deux codes du zéro
        r = roue[c]
        C(f"roue code {c} part_avant", r["part_avant"], float(cpt[c] / tot))
        apres = (cpt[0] + cpt[8]) / tot if c == 0 else (0.0 if c == 8 else cpt[c] / tot)
        C(f"roue code {c} part_apres", r["part_apres"], float(apres))
        ocp = E2M1_OCP[c & 7] * (-1 if c >> 3 else 1)
        C(f"roue code {c} valeur_ocp", r["valeur_ocp"].replace("-0", "0") if c == 8 else r["valeur_ocp"], float(ocp))

    # codon-sans-perte.csv : un tenseur tiré, depuis le codec réel (taux_reel).
    tr = lj(MES / "genome/predictif-elagage/taux-reel-colonne-12-gptoss20b.json")["tenseurs"]
    sp = lc(DON / "codon-sans-perte.csv")
    i = rng.randrange(12)
    t, r = tr[i], sp[i]
    C(f"sans perte {r['etiquette']} F1", r["sans_perte"], t["bpp_total_identite"])
    C(f"sans perte {r['etiquette']} zéro", r["zero"], t["bpp_total_zero_fondu"])
    C(f"sans perte {r['etiquette']} colonne", r["colonne"], t["bpp_total_nib_kappa_colonne"])
    C(f"sans perte {r['etiquette']} retenu", r["retenu"], str(int(t["bpp_total_zero_fondu"] - t["bpp_total_nib_kappa_colonne"] >= 0.015)))
    C(f"sans perte {r['etiquette']} perd", r["perd"], str(int(t["bpp_total_nib_kappa_colonne"] > t["bpp_total_zero_fondu"])))
    lab = f"{t['nom'].split('.')[1]}{t['nom'].split('.')[2].split('_')[1][0]}"
    C(f"sans perte rang {i} étiquette", r["etiquette"], lab)

    # codon-theoreme : le résidu d'un tenseur tiré par modèle, depuis tailles-par-tenseur.csv.
    tpt = lc(CO / "codon/tailles-par-tenseur.csv")
    for m in ("20b", "120b"):
        lignes = [x for x in tpt if x["modele"] == m]
        rows = lc(DON / f"codon-theoreme-{m}.csv")
        j = rng.randrange(len(rows))
        src = lignes[j]
        C(f"théorème {m} ligne {j} résidu", rows[j]["residu"], 1e4 * (float(src["gain_bits"]) - 2 * float(src["part_moins_zero"])))

    # codon-j1-encart.csv : les cinq barres, depuis les journaux de séance (passes valides).
    S = MES / "disque/placement/juge/seance"
    def val(motif):
        out = []
        for p in sorted(S.glob(motif)):
            j = lj(p)
            if not (j.get("arret_s") or j.get("sous_charge") or j.get("secteur_apres") is False):
                out.append(j["go_s"])
        return out
    s2 = lj(CO / "codon/disque-s2.json")
    attendu = [s2["moyennes"]["A"], s2["moyennes"]["C"], float(np.median(val("J5-*-C120.json"))),
               float(np.median(val("J6-*-C120.json"))), float(np.median(val("J6-*-A120.json")))]
    for r in lc(DON / "codon-j1-encart.csv"):
        C(f"encart {r['cas']}", r["go_s"], attendu[int(r["rang"])])

    # codon-j1-cascade.csv : les couleurs du dictionnaire (v1.0, v1.2, compagnon).
    coul = {"v10": "CouleurVunZero", "motif": "CouleurVunDeux", "octets": "CouleurVunDeux", "v12": "CouleurVunDeux",
            "rapide": "CouleurCompagnon", "compagnon": "CouleurCompagnon"}
    for r in lc(DON / "codon-j1-cascade.csv"):
        C(f"cascade {r['etape']} couleur", r["couleur"], coul[r["etape"]])

    # juge-grille-marge.csv : une couche tirée, plus la somme.
    g = lc(CO / "juge/figures/routage-grille.csv")
    marge = lc(DON / "juge-grille-marge.csv")
    c = rng.randrange(24)
    C(f"marge couche {c}", marge[c]["vides"], float(sum(1 for r in g if int(r["couche"]) == c and r["appels_r1"] == "0" and r["appels_neuf"] == "0")))
    C("marge somme", str(sum(int(r["vides"]) for r in marge)), "11")

    # synonyme-cumul-aire-frontiere.csv : un sommet tiré de l'aller (calibration) et son vis-à-vis au retour.
    sp_ = lc(CO / "synonyme/figures/spectre-L08-E00-gate.csv")
    lam = np.array([float(r["lambda_calib"]) for r in sp_])
    lev = np.array([float(r["lambda_eval_rayleigh"]) for r in sp_])
    ef = np.array([float(r["e_frontiere"]) for r in sp_])
    cal, ev = np.cumsum(lam * ef), np.cumsum(lev * ef)
    cal, ev = cal / cal[-1], ev / ev[-1]
    aire = lc(DON / "synonyme-cumul-aire-frontiere.csv")
    n = len(aire) // 2
    j = rng.randrange(n)
    k = int(aire[j]["k"])
    C(f"aire frontière aller k={k}", aire[j]["part"], float(cal[k]))
    r2 = aire[len(aire) - 1 - j]
    C(f"aire frontière retour k={r2['k']}", r2["part"], float(ev[int(r2["k"])]))

    # synonyme-survie.csv : une ligne tirée de la grille neuve, quatre séries, depuis les positions.
    S9 = CO / "synonyme"
    pos = {"q2_0": S9 / "repere/kl-q2_0-positions.csv", "frontiere": S9 / "kl/kl-frontiere-768-positions.csv",
           "lambda1": S9 / "kl/kl-synonyme-768-positions.csv", "lambda0": S9 / "kl/kl-synonyme-l0-768-positions.csv"}
    kl = {s: np.array([float(r["kl"]) for r in lc(p)]) for s, p in pos.items()}
    surv = lc(DON / "synonyme-survie.csv")
    j = rng.randrange(len(surv))
    tt = float(surv[j]["t"])
    for s in kl:
        C(f"survie t={tt:.4g} {s}", surv[j][s], float((kl[s] > tt).mean()))
    C("survie première borne", f"{float(surv[0]['t']):.6g}", "0.01")

    # synonyme-variantes.csv : la ligne du moteur exact (bits utiles, KL, σ par fenêtres).
    ex = next(r for r in lc(DON / "synonyme-variantes.csv") if r["variante"] == "exact")
    t0 = lj(CO / "juge/J-T0-fichiers.json")["fichiers"]["20b-v10"]
    C("variantes exact bits", ex["bits"], t0["somme_octets_utiles"] * 8 / t0["poids_experts"])
    kb = np.zeros(10); nb = np.zeros(10)
    for r in lc(MES / "moteur/O/journaux/o3/c4-20b-comparer.csv"):
        kb[int(r["fenetre"])] += float(r["kl_b"]); nb[int(r["fenetre"])] += 1
    m = kb / nb
    C("variantes exact kl", ex["kl"], float(m.mean()))
    C("variantes exact sigma_f", ex["sigma_f"], float(np.std(m, ddof=1) / math.sqrt(10)))

    for l in C.lignes:
        print(l)
    print(f"\ngraine {GRAINE} : {C.n} contrôles, {C.ecarts} écart(s){' (cassure)' if a.casser else ''}")
    return 1 if C.ecarts else 0


if __name__ == "__main__":
    sys.exit(main())
