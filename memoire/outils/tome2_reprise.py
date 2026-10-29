"""Reprise du jugement du Tome II : refait, depuis les CSV commités, chaque chiffre que la reprise
publie ou corrige (objections G1 et m1 à m21 de memoire/tome2/JUGEMENT.md), et vérifie dans les
sources LaTeX des deux langues que les chiffres corrigés y sont et que les chiffres faux n'y restent
que barrés.

Usage :
    python -I -X utf8 memoire/outils/tome2_reprise.py            # code 0 si tout tient
    python -I -X utf8 memoire/outils/tome2_reprise.py --casser   # témoin : doit dire « tombe »

Le témoin (--casser) fausse une entrée de 1 % (la génération de la passe 05 de la séance de
vitesse) : le coût de la garde, le bruit de C6 et le rendement C9 de cette passe doivent alors
sortir de leur tolérance, et l'outil doit le voir. Bibliothèque standard seule.
"""
import csv
import math
import re
import statistics as st
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
O = RACINE / "mesures/moteur/O"
CASSER = "--casser" in sys.argv


def lire(chemin):
    with open(chemin, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


ecarts = []


def verifier(nom, calcule, publie, tol):
    """Compare un chiffre refait à celui que le texte publie, à la tolérance de son arrondi."""
    ok = abs(calcule - publie) <= tol
    print(f"{'tient ' if ok else 'ECART '} {nom:58s} refait {calcule:.6g}  publié {publie:g}")
    if not ok:
        ecarts.append(nom)


# --- La séance de vitesse de la ronde (garde, C6, m1, m2, m21) ---------------------------------
vit = {r["passe"][:2]: r for r in lire(O / "corrections/csv/vitesse-2026-10-16-passes.csv")}
gen = {k: float(r["gen"]) for k, r in vit.items()}
if CASSER:
    gen["05"] *= 1.01
garde = (gen["05"] / gen["04"] - 1) * 100
verifier("m1  coût de la garde à disque égal (%)", garde, -1.6, 0.05)
attentes = [float(r["garde_attente_ms_par_jeton"]) for r in vit.values()
            if r["garde"] == "true" and r["kv_f32"] == "false"]
verifier("m1  attente de la garde, minimum (ms)", min(attentes), 5.2, 0.05)
verifier("m1  attente de la garde, maximum (ms)", max(attentes), 5.4, 0.05)


def bruit(a, b):
    return abs(a - b) / ((a + b) / 2) * 100


b_garde = bruit(gen["02"], gen["05"])
verifier("m2  bruit de la paire gardée 02-05 (%)", b_garde, 10.97, 0.005)
verifier("m2  seuil de C6, 2 β + 3 (%)", 2 * b_garde + 3, 24.9, 0.05)
b_sans = bruit(gen["03"], gen["04"])
serie = ((gen["02"] + gen["05"]) / (gen["03"] + gen["04"]) - 1) * 100
verifier("m21 série déclarée, écart (%)", serie, -12.3, 0.05)
verifier("m21 série déclarée, bruit (%)", max(b_garde, b_sans), 11.9, 0.05)
verifier("m21 série déclarée, seuil (%)", 2 * max(b_garde, b_sans) + 3, 26.8, 0.05)

# --- La base balayée (C6, m18) -------------------------------------------------------------------
base = lire(O / "corrections/csv/base-2026-10-16-passes.csv")
t16 = [r for r in base if r["nom"] == "L16"]
x16 = st.mean(float(r["generation_j_s"]) for r in t16)
xg = st.mean(gen[k] for k in ("02", "05", "07", "08"))
verifier("C6  rapport garde comprise contre fit -t 16", xg / x16, 2.22, 0.005)
pointe16 = st.mean(float(r["pointe_et_mo"]) for r in t16) / 1000
verifier("m18 pointe de fit -t 16 (Go)", pointe16, 11.42, 0.005)
verifier("m18 rapport de mémoire contre 384,19 Mo", pointe16 / 0.38419, 29.7, 0.05)

# --- Les passes L12 et le préremplissage par flux (m7, m19) -------------------------------------
jet = {r["passe"]: r for r in lire(O / "csv/o-jetons-s.csv")}
g = lambda p, c="generation_jetons_s": float(jet["2026-10-16-" + p][c])
bB = bruit(g("s2-16-l12-B"), g("s2-17-l12-B"))
verifier("m7  bruit des passes B de L12 (%)", bB, 16.2, 0.05)
verifier("m7  seuil de la règle (%)", 2 * bB + 3, 35.4, 0.05)
gain = (st.mean([g("s2-16-l12-B"), g("s2-17-l12-B")]) / st.mean([g("s2-15-l12-A"), g("s2-18-l12-A")]) - 1) * 100
verifier("m7  gain en médiane (%)", gain, 30.4, 0.05)
pA = st.mean([g("s2-11-flux-A", "prefill_jetons_s"), g("s2-14-flux-A", "prefill_jetons_s")])
pB = st.mean([g("s2-12-flux-B", "prefill_jetons_s"), g("s2-13-flux-B", "prefill_jetons_s")])
verifier("m19 rapport des débits de préremplissage", pB / pA, 17.5, 0.05)
verifier("m19 durée par flux (s)", 708 / pB, 26, 0.5)
verifier("m19 durée par la boucle (s)", 708 / pA, 7 * 60 + 36, 0.5)

# --- E2, la série N V V N (m8) -------------------------------------------------------------------
e2 = lire(RACINE / "mesures/moteur/E/csv/e2-nvvn-2026-10-15-nvvn.csv")
med = {L: st.median(float(r["go_s_servis"]) for r in e2 if r["lettre"] == L) for L in "NV"}
verifier("m8  médiane des huit passes A, V (Go/s)", med["V"], 2.851, 0.0005)
verifier("m8  médiane des huit passes A, N (Go/s)", med["N"], 2.135, 0.0005)
verifier("m8  V / N", med["V"] / med["N"], 1.335, 0.0005)
verifier("m8  gain de V sur N (%)", (med["V"] / med["N"] - 1) * 100, 33.5, 0.05)

# --- K1 (m6) -------------------------------------------------------------------------------------
k1 = lire(RACINE / "mesures/moteur/K/csv/k1-debit-passes.csv")
for j, publie in (("k1-debit-A1-20261015-2024.json", 0.9), ("k1-debit-A2-20261015-2024.json", 1.1)):
    pire = min(float(r["go_s_codes"]) for r in k1 if r["journal"] == j and r["variante"] == "A")
    verifier(f"m6  K1 sous 33,28 Go/s, {j[9:11]} (%)", (1 - pire / 33.28) * 100, publie, 0.05)

# --- Calculs posés (G1, m4, m5, m15, m16) ---------------------------------------------------------
verifier("G1  borne des bascules, 0,00308 / 8 192 (nat)", 0.00308 / 8192, 3.8e-7, 0.05e-7)
verifier("m4  seconde lecture, 23,6 / 1 153,3 (%)", 23.6 / 1153.3 * 100, 2.05, 0.005)
th9 = 150000 ** (-18 / 64)
r9 = (9 - 8.0928) / (17.398 - 8.0928)
dw = th9 * abs(((1 - r9) + r9 / 32) - (0.9 + 0.1 / 32))
verifier("m5  Δω à la paire 9 (rad par position)", dw, 8.5e-5, 0.05e-5)
verifier("m15 hachage du dernier tronçon (ms)", 12251136 / 1.07e9 * 1e3, 11.4, 0.05)
verifier("m15 part du pas de 457 ms (%)", 12251136 / 1.07e9 / 0.457 * 100, 2.5, 0.05)
verifier("m16 scores d'attention en f64 (ms)", 64 * 4096 * 64 * 2 / 0.2e12 * 1e3, 0.17, 0.005)

# --- C9, le rendement physique (m13) --------------------------------------------------------------
# Plafond de l'équation du jeton du Tome I (E = 1, t_lat = 0) : max des étages + T0.
pl = {r["passe"]: r for r in lire(RACINE / "memoire/figures/tome2/donnees/res-plancher.csv")}
if CASSER:
    pl["05-garde"]["mesure"] = str(float(pl["05-garde"]["mesure"]) / 1.01)
rend = {}
for p, r in pl.items():
    f = {k: float(r[k]) for k in ("disque", "pcie", "dec", "gemv", "t0", "mesure")}
    plafond = max(f["disque"], f["pcie"], f["dec"] + f["gemv"]) + f["t0"]
    rend[p] = plafond / f["mesure"]
verifier("C9  rendement, J1 passe 1", rend["J1 1"], 0.84, 0.005)
verifier("C9  rendement, J1 passe 6", rend["J1 6"], 0.84, 0.005)
ronde = [v for p, v in rend.items() if not p.startswith("J1")]
verifier("C9  rendement de la ronde, minimum", min(ronde), 0.64, 0.005)
verifier("C9  rendement de la ronde, maximum", max(ronde), 0.82, 0.005)
verifier("C9  rendement, passe 05 de la ronde", rend["05-garde"], 0.72, 0.005)
verifier("C9  plafond de J1 passe 1 (jetons/s)", 1000 / (rend["J1 1"] * float(pl["J1 1"]["mesure"])), 2.589, 0.0005)

# --- Les textes : chiffres faux seulement barrés, chiffres justes présents dans les deux langues --
T2 = RACINE / "memoire/tome2"


def hors_barre(texte, motif):
    """Occurrences de motif qui ne sont pas à l'intérieur d'un \\barre{...}."""
    zones, i = [], 0
    while (i := texte.find("\\barre{", i)) >= 0:
        j, prof = i + 7, 1
        while prof:
            prof += {"{": 1, "}": -1}.get(texte[j], 0)
            j += 1
        zones.append((i, j))
        i = j
    return [m.start() for m in re.finditer(motif, texte)
            if not any(a <= m.start() < b for a, b in zones)]


INTERDITS = [  # (chapitre, motif d'un chiffre faux qui ne doit survivre que barré)
    ("04-noyaux", r"5\\cdot10\^\{-11\}"), ("07-resultats", r"\\num\{5e-11\}"),
    ("01-architecture", r"5,2 à 5,3|5\.2 to 5\.3"), ("03-chemin", r"5,2 à 5,3|5\.2 to 5\.3"),
    ("06-cache-moteur", r"5,2 à 5,3|5\.2 to 5\.3"), ("06-cache-moteur", r"7\\,min\\,50"),
    ("07-resultats", r"\\SI\{7\}\{\\minute\}\\,\\SI\{50\}|7\\,min\\,50"), ("05-reference", r"8[{.,}]+8\\cdot10\^\{-5\}"),
    ("03-chemin", r"écart de 25|25\\,\\% gap"), ("09-discussion", r"le tiers de|a third of"),
    ("02-format", r"séquentiel du disque|disk's sequential"), ("04-noyaux", r"au plus 0[,.]15"),
]
for langue in ("fr", "en"):
    for chap, motif in INTERDITS:
        texte = (T2 / langue / "chapitres" / f"{chap}.tex").read_text(encoding="utf-8")
        reste = hors_barre(texte, motif)
        ok = not reste
        print(f"{'tient ' if ok else 'ECART '} {langue} {chap}: « {motif} » hors barre : {len(reste)}")
        if not ok:
            ecarts.append(f"{langue} {chap} {motif}")

if CASSER:
    tombe = bool(ecarts)
    print("témoin :", "tombe" if tombe else "NE TOMBE PAS")
    sys.exit(0 if tombe else 1)
print(f"{len(ecarts)} écart(s)")
sys.exit(1 if ecarts else 0)
