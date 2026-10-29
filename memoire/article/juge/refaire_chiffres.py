"""Juge de l'article court : chaque chiffre de l'article refait depuis son fichier commité, par un chemin propre.

Ce script ne lit ni medianes_j1.py ni parite_nombres.py ni les sorties du rédacteur (medianes_j1.json). Il relit
les journaux commités (tailles, tenseurs, comptes des zéros, passes du J1, étage disque, séance du juge de la
construction, motif croisé du juge du placement, tables, en-têtes des GGUF, débits de la machine), recalcule chaque
nombre, l'écrit au format de l'article, et vérifie que cette écriture figure dans le corps de l'article anglais
ET dans celui de l'article français (séparateur décimal et groupes de chiffres normalisés).

Usage, depuis la racine du dépôt : python -I -X utf8 memoire/article/juge/refaire_chiffres.py
Sortie : une ligne par chiffre (« tient » ou « TOMBE ») ; code 0 si tout tient, 1 sinon.
Témoin : --casser fausse une source (la médiane B du J1 relue × 1,001) ; au moins un chiffre doit alors tomber.
Les « relevés » (écrits par le juge avant les corrections, sur l'article d'avant) disaient ce que l'article
devait corriger. Depuis les corrections (2010c97) et les mineurs du contre-jugement (N1 à N8), chaque relevé
vérifie que la correction est dans le texte, dans les deux langues (et, le cas échéant, que l'ancienne écriture
n'y est plus) ; ils sont comptés à part des chiffres, et un relevé qui tombe fait aussi sortir en code 1.
La section 12 refait depuis leurs fichiers commités les chiffres neufs des mineurs N2 à N4.
"""
import csv
import json
import re
import statistics
import sys
from pathlib import Path

CASSER = "--casser" in sys.argv
R = Path(".")
C = R / "mesures/genome/construction/codon"


def lire(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def corps(chemin, francais):
    t = Path(chemin).read_text(encoding="utf-8").split(r"\begin{document}", 1)[1]
    t = "\n".join(re.sub(r"(?<!\\)%.*", "", l) for l in t.splitlines())
    t = re.sub(r"\\num\{([^}]*)\}", r"\1", t)
    t = t.replace("{,}", ".") if francais else t
    if francais:
        t = re.sub(r"(\d),(\d)", r"\1.\2", t)
    t = t.replace(r"\,", "")  # groupes de chiffres et espaces fines (« 3.26\,\% » devient « 3.26\% »)
    return t


EN = corps("memoire/article/en/troncons-article.tex", False)
FR = corps("memoire/article/fr/troncons-article.tex", True)
# Le texte entier, préambule compris (les titres des tomes et \NoteTome y sont définis), sans normalisation.
EN_TOUT = Path("memoire/article/en/troncons-article.tex").read_text(encoding="utf-8")
FR_TOUT = Path("memoire/article/fr/troncons-article.tex").read_text(encoding="utf-8")
resultats, releves = [], []


def verifier(nom, valeur, texte):
    """`texte` est l'écriture attendue dans l'article (point décimal, sans groupes)."""
    present = (texte in EN, texte in FR)
    ok = all(present)
    resultats.append(ok)
    etat = "tient" if ok else f"TOMBE (EN {present[0]}, FR {present[1]})"
    print(f"{etat:30} {nom} = {valeur!r} -> « {texte} »")


def verifier2(nom, valeur, en, fr):
    """Comme `verifier`, quand l'unité s'écrit autrement dans chaque langue (GB / Go, MiB / Mio)."""
    present = (en in EN, fr in FR)
    ok = all(present)
    resultats.append(ok)
    etat = "tient" if ok else f"TOMBE (EN {present[0]}, FR {present[1]})"
    print(f"{etat:30} {nom} = {valeur!r} -> « {en} » / « {fr} »")


def une_valeur(xs, fmt):
    """L'écriture commune de plusieurs passes à l'arrondi de l'article, ou un texte qui ne peut figurer nulle part."""
    s = {fmt.format(x) for x in xs}
    return s.pop() if len(s) == 1 else "<passes en désaccord à cet arrondi>"


def relever(nom, valeur, en, fr, absents=(), tout=False):
    """Une correction demandée par le jugement ou le contre-jugement : `en` doit figurer dans l'article anglais et
    `fr` dans le français (corps normalisé comme pour les chiffres, ou texte brut entier si `tout`) ; chaque paire
    de `absents` (ancienne écriture anglaise, française) ne doit plus y figurer."""
    a, b = (EN_TOUT, FR_TOUT) if tout else (EN, FR)
    ok = en in a and fr in b and all(x not in a and y not in b for x, y in absents)
    etat = "corrigé" if ok else f"TOMBE (EN {en in a}, FR {fr in b})"
    releves.append((ok, f"{etat:10} {nom} : recalculé {valeur} ; l'article écrit « {en} » / « {fr} »"))


# ---------- 1. Tailles (tailles.json, écrit par analyse_codon.py depuis les journaux verifier/coder) ----------
T = lire(C / "tailles.json")["totaux"]
for m in ("20b", "120b"):
    t = T[m]
    for cle in ("poids_experts", "octets_troncons_v10", "octets_troncons_v12", "fichier_v10", "fichier_v12",
                "troncon_max_v10", "troncon_max_v12", "moins_zero_fondus"):
        verifier(f"{m} {cle}", t[cle], str(t[cle]))
    verifier(f"{m} octets en moins", t["octets_troncons_v10"] - t["octets_troncons_v12"],
             str(t["octets_troncons_v10"] - t["octets_troncons_v12"]))
    gain = (t["octets_troncons_v10"] - t["octets_troncons_v12"]) * 8 / t["poids_experts"]  # refait, pas relu
    verifier(f"{m} gain sur les tronçons (bit/poids)", gain, f"{gain:.5f}")
    verifier(f"{m} bits par poids v1.0 (flux)", t["bpp_total_03_v10"], f"{t['bpp_total_03_v10']:.5f}")
    verifier(f"{m} bits par poids v1.2 (flux)", t["bpp_total_03_v12"], f"{t['bpp_total_03_v12']:.5f}")
    verifier(f"{m} part des -0 (7 déc.)", t["part_moins_zero"], f"{t['part_moins_zero']:.7f}")
    verifier(f"{m} part des -0 (%)", t["part_moins_zero"], f"{100 * t['part_moins_zero']:.3f}\\%")
    verifier(f"{m} prédiction 2 x part", 2 * t["part_moins_zero"], f"{2 * t['part_moins_zero']:.5f}")
    if m == "120b":
        verifier("120b gain / bits v1.0 (%)", gain / t["bpp_total_03_v10"], f"{100 * gain / t['bpp_total_03_v10']:.2f}\\%")
        rap = t["octets_troncons_v12"] / t["octets_troncons_v10"]
        verifier("120b rapport des tronçons", rap, f"{rap:.5f}")
        verifier("120b part des octets de tronçons (%)", 1 - rap, f"{100 * (1 - rap):.2f}\\%")
        verifier("120b toit des octets (%)", 1 / rap - 1, f"{100 * (1 / rap - 1):.1f}\\%")
        go = (t["octets_troncons_v10"] - t["octets_troncons_v12"]) / 1e9
        verifier("120b octets en moins (Go)", go, f"{go:.2f}")
        ecart_flux = t["bpp_total_03_v10"] - t["bpp_total_03_v12"]
        verifier("120b différence des deux lignes de flux (valeurs non arrondies)", ecart_flux, f"{ecart_flux:.5f}")
        relever("120b, différence des deux lignes « bits par poids » du tableau 2 (flux ; jugement M7, N5)",
                f"{ecart_flux:.5f}",
                f"their difference, from the unrounded values, is {ecart_flux:.5f} bit on the 120b",
                f"leur différence, depuis les valeurs non arrondies, vaut {ecart_flux:.5f} bit sur le 120b")
    assert t["experts_exacts_v12"] == t["experts"], m
    verifier(f"{m} experts exacts", t["experts_exacts_v12"], str(t["experts_exacts_v12"]))

# ---------- 2. Le théorème, tenseur par tenseur (tailles-par-tenseur.csv) ----------
lignes = list(csv.DictReader(open(C / "tailles-par-tenseur.csv", encoding="utf-8")))
NOMS = {"0": "gate", "1": "up", "2": "down"}  # ordre des matrices : decodeur_juge.py, ("gate", "up", "down")
ecarts = [float(l["gain_bits"]) - 2 * float(l["part_moins_zero"]) for l in lignes]
verifier("tenseurs", len(lignes), str(len(lignes)))
verifier("écart minimal", min(ecarts), f"{min(ecarts):.5f}")
verifier("écart maximal", max(ecarts), f"+{max(ecarts):.5f}")
verifier("écart moyen", statistics.mean(ecarts), f"+{statistics.mean(ecarts):.5f}")
verifier("écart en 1e-4 (résumé)", max(abs(e) for e in ecarts), f"{1e4 * max(abs(e) for e in ecarts):.1f} \\times 10^{{-4}}")
lo = min(lignes, key=lambda l: float(l["gain_bits"]))
hi = max(lignes, key=lambda l: float(l["gain_bits"]))
verifier(f"gain minimal ({lo['modele']}, couche {lo['couche']}, {NOMS[lo['matrice']]})", float(lo["gain_bits"]),
         f"{float(lo['gain_bits']):.3f}")
verifier(f"gain maximal ({hi['modele']}, couche {hi['couche']}, {NOMS[hi['matrice']]})", float(hi["gain_bits"]),
         f"{float(hi['gain_bits']):.3f}")
verifier("part des -0 au gain maximal (%)", float(hi["part_moins_zero"]), f"{100 * float(hi['part_moins_zero']):.1f}\\%")
assert (lo["modele"], lo["couche"], NOMS[lo["matrice"]]) == ("120b", "26", "up"), lo
assert (hi["modele"], hi["couche"], NOMS[hi["matrice"]]) == ("120b", "0", "up"), hi
poids = {m: sum(int(l["poids"]) for l in lignes if l["modele"] == m) for m in ("20b", "120b")}
for m in ("20b", "120b"):
    flux = sum(float(l["gain_bits"]) * int(l["poids"]) for l in lignes if l["modele"] == m) / poids[m]
    relever(f"{m}, gain pondéré des tenseurs (flux de codes, base de la figure 3 ; jugement M7)", f"{flux:.5f}",
            "code streams of each tensor", "flux de codes de chaque tenseur")

# ---------- 3. La pièce (zero-compte-20b.json) ----------
Z = lire("mesures/genome/etat-de-l-art/journaux/zero-compte-20b.json")
verifier("poids d'experts du 20b (compte des zéros)", int(Z["poids"]), str(int(Z["poids"])))
verifier("part de +0 (%)", Z["p_plus0"], f"{100 * Z['p_plus0']:.4f}\\%")
verifier("part de -0 (%)", Z["p_moins0"], f"{100 * Z['p_moins0']:.4f}\\%")
verifier("H(S | V = 0)", Z["H_signe_sachant_zero"], f"{Z['H_signe_sachant_zero']:.10f}")
verifier("H(codes)", Z["H_code"], f"{Z['H_code']:.4f}")
verifier("H(valeurs)", Z["H_valeur"], f"{Z['H_valeur']:.4f}")
verifier("coût du signe", Z["H_code"] - Z["H_valeur"], f"{Z['H_code'] - Z['H_valeur']:.4f}")
epais = (0.4 + 44 * (Z["p_plus0"] + Z["p_moins0"])) / (0.4 + 44 * Z["p_plus0"])
verifier("épaississement du rayon du zéro (figure 1)", epais, f"\\times {epais:.2f}")

# ---------- 4. Le J1, séance s2 (j1-s2-passes.csv) : médianes par ma fonction ----------
P = list(csv.DictReader(open(C / "j1-s2-passes.csv", encoding="utf-8")))


def med(f, col):
    v = sorted(float(p[col]) for p in P if p["fichier"] == f)
    m = (v[1] + v[2]) / 2
    return m * 1.001 if (CASSER and f == "B" and col == "jetons_s") else m


for p in P:
    verifier(f"passe {p['passe']} {p['fichier']}", float(p["jetons_s"]), f"{float(p['jetons_s']):.3f}")
mA, mB = med("A", "jetons_s"), med("B", "jetons_s")
A = [float(p["jetons_s"]) for p in P if p["fichier"] == "A"]
sig = statistics.stdev(A) / statistics.mean(A)
verifier("médiane A", mA, f"{mA:.3f}")
verifier("médiane B", mB, f"{mB:.3f}")
verifier("r", mB / mA, f"r = {mB / mA:.3f}")
verifier("sigma A (%)", sig, f"\\sigma = {100 * sig:.1f}\\%")
verifier("2 sigma", 2 * sig, f"2\\sigma = {2 * sig:.3f}")
par = {int(p["passe"]): float(p["jetons_s"]) for p in P}
apparies = [par[2] / par[1], par[3] / par[4], par[6] / par[5], par[7] / par[8]]
for x in apparies:
    verifier("rapport apparié", x, f"{x:.3f}")
oA, oB = med("A", "octets_troncons_par_jeton"), med("B", "octets_troncons_par_jeton")
verifier("octets par jeton A", oA, str(round(oA)))
verifier("octets par jeton B", oB, str(round(oB)))
verifier("rapport des octets", oB / oA, f"{oB / oA:.4f}")
verifier("toit des octets", oA / oB, f"{oA / oB:.3f}")
verifier("1/rapport (cascade)", oB / oA, f"1/{oB / oA:.4f}")
for col, fmt, ech in (("defauts_par_jeton", "{:.2f}", 1), ("h_vram", "{:.4f}", 1), ("s_lectures_par_jeton", "{:.3f}", 1),
                      ("debit_lecture_go_s", "{:.2f}", 1), ("ms_decodage_par_jeton", "{:.1f}", 1),
                      ("ms_copie_par_jeton", "{:.1f}", 1), ("pointe_ensemble_travail", "{:.2f}", 1e-6)):
    for f in "AB":
        v = med(f, col) * ech
        verifier(f"{col} {f}", v, fmt.format(v))
dm = (med("A", "pointe_ensemble_travail") - med("B", "pointe_ensemble_travail")) / 1e6
verifier("mémoire, écart (Mo)", dm, f"{dm:.2f}")
tampons = 12 * (T["120b"]["troncon_max_v10"] - T["120b"]["troncon_max_v12"])
verifier("tampons d'arrivée", tampons, str(tampons))
reste_mo = dm - tampons / 1e6
relever("mémoire non expliquée (s2 ; jugement M8)", f"{reste_mo:.2f} Mo",
        f"about {reste_mo:.1f}MB are not explained", f"environ {reste_mo:.1f}Mo ne sont pas expliqués",
        absents=(("about 1.9", "environ 1.9"),))
tl = med("B", "s_lectures_par_jeton") / med("A", "s_lectures_par_jeton")
print(f"{'tient':30} temps de lecture B/A = {tl:.3f} (« baisse d'un tiers » : {100 * (1 - tl):.0f} %)")

# ---------- 5. L'étage disque de s2 (disque-s2.json) ----------
D = lire(C / "disque-s2.json")["go_s"]
for f in "ABC":
    for x in D[f]:
        verifier(f"disque s2 {f}", x, f"{x:.3f}")

# ---------- 6. La séance du juge de la construction (analyse-120b.json, analyse-20b.json) ----------
J = lire("mesures/genome/construction/juge/vitesse/analyse-120b.json")
J20 = lire("mesures/genome/construction/juge/vitesse/analyse-20b.json")
gA, gB = statistics.median(J["generation"]["A"]), statistics.median(J["generation"]["B"])
verifier("juge, médiane A", gA, f"{gA:.3f}")
verifier("juge, médiane B", gB, f"{gB:.3f}")
verifier("juge, r(B/A)", gB / gA, f"{gB / gA:.3f}")
sj = statistics.stdev(J["generation"]["A"]) / statistics.mean(J["generation"]["A"])
verifier("juge, sigma A", sj, f"\\sigma = {100 * sj:.1f}\\%")
dk = sum(J["disque_go_s"]["B"]) / sum(J["disque_go_s"]["A"])
verifier("juge, étage disque B/A", dk, f"{dk:.2f}")
reste = (gB / gA) * (oB / oA)
verifier("reste après le toit des octets", reste, f"{reste:.3f}")
rRB = statistics.median(J["generation"]["R"]) / gB
verifier("mode rapide r(R/B), 120b", rRB, f"{rRB:.3f}")
verifier("mode rapide r(R/B), 20b", J20["r_R_sur_B"], f"{J20['r_R_sur_B']:.3f}")
for m_, s_ in (("120b", J["J_V2_ou_V3"]["seuil"]), ("20b", J20["J_V2_ou_V3"]["seuil"])):
    verifier(f"seuil déclaré du mode rapide, {m_} (r(R/B) ≥ g(1 − 2σ))", s_, f"\\ge {s_:.3f}")
relever("seuils déclarés du mode rapide (r(R/B) ≥ g(1 − 2σ) ; jugement M16)",
        f"{J['J_V2_ou_V3']['seuil']:.3f} (120b) et {J20['J_V2_ou_V3']['seuil']:.3f} (20b)",
        "announced gain $\\times (1 - 2\\sigma)$", "gain annoncé $\\times (1 - 2\\sigma)$")

# ---------- 7. Le motif croisé (journaux Jb3 du juge du placement) ----------
cas = {}
for j in sorted(Path("mesures/disque/placement/juge/seance").glob("Jb3-*.json")):
    d = lire(j)
    cle = j.stem.split("-", 2)[2]  # A20-natif, A20-croise, ...
    cas.setdefault(cle, []).append(d["go_s"])
meds = {k: statistics.median(v) for k, v in cas.items()}
for k, v in cas.items():
    for x in v:
        verifier(f"Jb3 {k}", x, f"{x:.3f}")
    verifier(f"Jb3 {k} médiane", meds[k], f"{meds[k]:.3f}")
verifier("A20 croisé / natif (médianes non arrondies)", meds["A20-croise"] / meds["A20-natif"],
         f"{meds['A20-croise'] / meds['A20-natif']:.3f}")
arr = round(meds["A20-croise"], 3) / round(meds["A20-natif"], 3)
verifier("A20 croisé / natif (médianes arrondies)", arr, f"{arr:.3f}")
verifier("B20 croisé / natif", meds["B20-croise"] / meds["B20-natif"], f"{meds['B20-croise'] / meds['B20-natif']:.3f}")

# ---------- 8. Les tables (tables-octets.json) ----------
B = lire(C / "tables-octets.json")["bilan"]
n10 = B["20b v1.0"]["tables_codes"] + B["120b v1.0"]["tables_codes"]
verifier("tables CODES_CTX lues (v1.0)", n10, str(n10))
assert B["20b v1.2"]["tables_avec_fente_pour_un_8"] + B["120b v1.2"]["tables_avec_fente_pour_un_8"] == 0
masse = (B["20b v1.0"]["masse_des_octets_8_sur_4096"]["moyenne"] * 216 + B["120b v1.0"]["masse_des_octets_8_sur_4096"]["moyenne"] * 324) / 540 / 4096
verifier("masse moyenne des octets portant un 8 (%)", masse, f"{100 * masse:.0f}\\%")
relever("les 540 tables (jugement M6)",
        f"{B['20b v1.0']['tables_codes']} + {B['120b v1.0']['tables_codes']} = toutes les couches (24 × 9 et 36 × 9)",
        f"Over all {n10} CODES\\_CTX tables of both models", f"Sur l'ensemble des {n10} tables CODES\\_CTX des deux modèles",
        absents=(("of layers 0, L/2", "des couches 0, L/2"),))

# ---------- 9. La machine et le modèle ----------
M = lire("fondations/journaux/01-machine/debits-mesures.json")
verifier("débit du disque (Tome I)", M["disque"]["go_s"], f"{M['disque']['go_s']:.2f}")
G = lire("mesures/localite-gpt-oss/octets-gpt-oss.json")  # en-têtes des GGUF locaux (témoin de fin de fichier tenu)
g120, g20 = G["gpt-oss-120b-MXFP4.gguf"], G["gpt-oss-20b-MXFP4.gguf"]
verifier("GGUF 120b (octets)", g120["taille_octets"], str(g120["taille_octets"]))
verifier("GGUF 20b (octets)", g20["taille_octets"], str(g20["taille_octets"]))
verifier("GGUF 120b (Go)", g120["taille_octets"] / 1e9, f"{g120['taille_octets'] / 1e9:.1f}")
verifier("experts du 120b", g120["couches"] * g120["experts"], str(g120["couches"] * g120["experts"]))
verifier("experts du 120b (Go)", g120["experts_total_octets"] / 1e9, f"{g120['experts_total_octets'] / 1e9:.2f}")
verifier("toujours lus du 120b (Go)", g120["toujours_lus_octets"] / 1e9, f"{g120['toujours_lus_octets'] / 1e9:.2f}")
verifier("lectures de tables à l'ouverture", 36 * 3 * 3 * 31, str(36 * 3 * 3 * 31))
verifier("octets qui restent", 256 - 31, "225")



# ---------- 10. Le motif borné (J9, J10, J11) et la fragmentation de C120 (J5, J6) ----------
def seance(motif, ecarter=()):
    v = {}
    for j in sorted(Path("mesures/disque/placement/juge/seance").glob(motif)):
        d = lire(j)
        if "go_s" not in d:
            continue  # témoin de contenu (J10-temoin.json), pas une passe
        if round(d["go_s"], 3) in ecarter:
            continue  # passe écartée par le juge (disque lu / demandé hors de [0,98 ; 1,02], § 5.6)
        v.setdefault(j.stem.split("-", 2)[2], []).append(d["go_s"])
    return {k: statistics.median(x) for k, x in v.items()}


j9 = seance("Jb9-*.json", ecarter=(2.319,))
verifier("J9, A20 raccourci / natif", j9["A20-raccourci"] / j9["A20-natif"], f"{j9['A20-raccourci'] / j9['A20-natif']:.3f}")
verifier("J9, B20 allongé / natif", j9["B20-allonge"] / j9["B20-natif"], f"{j9['B20-allonge'] / j9['B20-natif']:.3f}")
j10, j11 = seance("J10-*.json"), seance("J11-*.json")
verifier("J10, moitiés q = 8 / natif", j10["A20-moities"] / j10["A20-natif"], f"{j10['A20-moities'] / j10['A20-natif']:.3f}")
verifier("J11, moitiés q = 4 / natif", j11["A20-moities-q4"] / j11["A20-natif"], f"{j11['A20-moities-q4'] / j11['A20-natif']:.3f}")
j5 = statistics.median(lire(j)["go_s"] for j in Path("mesures/disque/placement/juge/seance").glob("J5-*.json"))
j6 = seance("J6-*.json", ecarter=(1.531,))  # J6-12, finie sur batterie (§ 5.10)
verifier("J5/J6, C120 un extent / tiré", j6["C120"] / j5, f"{j6['C120'] / j5:.2f}")
verifier("J6, C[U] / A[U]", j6["C120"] / j6["A120"], f"{j6['C120'] / j6['A120']:.3f}")

# ---------- 11. Les pistes qui tombent ----------
Tr = lire("mesures/pistes/tropicale/juge/juge.json")
pp = Tr["point_principal"]
for cle in ("bascules_attrapees", "cellules_signalees"):
    verifier(f"garde tropicale, {cle}", pp[cle], str(pp[cle]))
verifier("garde tropicale, bascules", Tr["bascules_ensemble"], str(Tr["bascules_ensemble"]))
verifier("garde tropicale, cellules", Tr["cellules"], str(Tr["cellules"]))
verifier("garde tropicale, part attrapée (%)", pp["part_bascules"], f"{100 * pp['part_bascules']:.1f}\\%")
verifier("garde tropicale, coût de 80 % (%)", Tr["cout_80"]["part_cellules"], f"{100 * Tr['cout_80']['part_cellules']:.1f}\\%")
Kd = lire("mesures/genome/construction/juge/kl/apparie-neuf-sub-l0-contre-frontiere.json")
verifier("mutation synonyme contre frontière, d", Kd["d_moyenne"], f"{Kd['d_moyenne']:.4f}")
verifier("... sigma par fenêtres", Kd["sigma_par_fenetres"], f"{Kd['sigma_par_fenetres']:.4f}")
verifier("... en sigma", -Kd["d_sur_sigma"], f"{-Kd['d_sur_sigma']:.1f}")
P3 = lire("mesures/mimetisme/P3/routeur-ligne/analyse.json")["passes"]["B0.041"]
verifier("routeur conditionné, KL (contre le moteur sans biais)", P3["B_lecteur"]["kl_moyenne"], f"{P3['B_lecteur']['kl_moyenne']:.4f}")
verifier("routeur conditionné, borne haute par fenêtres", P3["B_lecteur"]["kl_bootstrap_fenetres_95"][1],
         f"{P3['B_lecteur']['kl_bootstrap_fenetres_95'][1]:.4f}")
kl3 = P3["B_lecteur"]["kl_moyenne"]
relever("routeur conditionné : variation des défauts (jugement M14)",
        f"{100 * P3['variation_defauts']:.2f} % (gpt-oss-20b, 238 emplacements ; KL contre le même moteur sans biais)",
        f"about {abs(100 * P3['variation_defauts']):.0f}\\% of the misses for a KL divergence of {kl3:.4f} against the same engine without the bias",
        f"environ {abs(100 * P3['variation_defauts']):.0f}\\% des défauts pour une divergence KL de {kl3:.4f} contre le même moteur sans le biais")

# ---------- 12. Les mineurs du contre-jugement (JUGEMENT-article-contre.md, N1 à N8) ----------
# Chiffres neufs, refaits depuis leurs fichiers commités : la séance de l'épreuve indépendante du Tome II
# (s1-2026-10-16 : T120 troncons, L120 llama.cpp « fit -t 6 », la configuration publiée de mesures/gpt-oss.md
# § 3.2 ; pointe de mémoire engagée privée lue par le système, en octets / 1e6 ; pointe de la carte entière lue
# par nvidia-smi, en Mio) et la KL de la fenêtre 0 du 120b avec un cache KV en f32 (verdicts de la ronde).
S1 = list(csv.DictReader(open("mesures/moteur/epreuve-J1/csv/s1-2026-10-16-passes.csv", encoding="utf-8")))
engT = une_valeur([float(p["pointe_engagee_os_mo"]) / 1000 for p in S1 if p["nom"] == "T120"], "{:.2f}")
engL = une_valeur([float(p["pointe_engagee_os_mo"]) / 1000 for p in S1 if p["nom"] == "L120"], "{:.2f}")
verifier2("N3, mémoire engagée privée de troncons (120b, les trois passes T120, Go)", engT, f"{engT}GB", f"{engT}Go")
verifier2("N3, mémoire engagée privée de llama.cpp (les deux passes L120, Go)", engL,
          f"llama.cpp: {engL}GB", f"llama.cpp : {engL}Go")
vT = une_valeur([int(p["vram_pointe_mio"]) for p in S1 if p["nom"] == "T120"], "{}")
vL = sorted(int(p["vram_pointe_mio"]) for p in S1 if p["nom"] == "L120")
verifier2("N4, pointe de la carte entière sous troncons (les trois passes T120, Mio)", vT,
          f"{vT}MiB under troncons", f"{vT}Mio sous troncons")
verifier2("N4, pointe de la carte entière sous llama.cpp (les deux passes L120, Mio)", vL,
          f"{vL[0]} and {vL[1]}MiB under llama.cpp", f"{vL[0]} et {vL[1]}Mio sous llama.cpp")
KV = lire("mesures/moteur/O/corrections/journaux/verdicts-kv-2026-10-16.json")["f0_120b"]["comparer_kld"]["f32"]
assert KV["n"] == 255, KV["n"]
verifier("N2, KL de troncons, 120b, fenêtre 0, cache KV en f32", KV["kl_moyenne"], f"{KV['kl_moyenne']:.5f}")

relever("N1, BitMoD cité avant NxFP ; « trois formats »", "arXiv:2411.11745",
        "BitMoD replaces the redundant zero of FP3 and FP4 variants by a special value \\citep{chen2024bitmod}",
        "BitMoD remplace le zéro redondant de variantes FP3 et FP4 par une valeur spéciale \\citep{chen2024bitmod}",
        absents=(("Both are new, lossy formats", "Ce sont deux formats neufs"),))
relever("N2, le plancher est celui des fichiers de logits", f"{KV['kl_moyenne']:.5f}",
        "at the resolution floor of the logit files themselves", "au plancher de résolution des fichiers de logits eux-mêmes",
        absents=(("the floor of the file format", "au plancher du format de fichier"),))
relever("N3, la mémoire engagée privée à côté de la pointe", f"{engT} Go",
        "troncons's private committed memory", "la mémoire engagée privée de troncons")
relever("N4, l'empreinte de llama.cpp sur la carte, et ce qu'elle dit", f"{vT} et {vL} Mio",
        "the large gap between the two engines lies in the host working set",
        "le grand écart entre les deux moteurs est dans l'ensemble de travail de l'hôte")
relever("N6, ce qu'aucun calcul ne fait du signe (résumé, introduction, § 3.2, conclusion)", "",
        "no computation of the engines considered depends on it", "aucun calcul des moteurs considérés n'en dépend",
        absents=(("no computation ever reads it", "aucun calcul ne le lit"), ("that no computation reads", "qu'aucun calcul ne lit"),
                 ("a sign that nothing reads", "un signe que rien ne lit")))
relever("N7, les flux FP4 uniformes de Heilper et Singer, et l'entropie des codes de gpt-oss-20b", f"{Z['H_code']:.4f}",
        f"the entropy of the codes is {Z['H_code']:.4f} bits per weight, not 4",
        f"l'entropie des codes vaut {Z['H_code']:.4f} bits par poids, et non 4")
relever("N8, la référence du Tome I nomme le tome", "",
        "the measured foundations (Volume~I)}", "les fondations mesurées (Tome~I)}", tout=True)
relever("N8, la note des tomes commence par une majuscule après un point", "",
        "\\newcommand{\\NoteTome}{English and French versions", "\\newcommand{\\NoteTome}{Versions anglaise et française",
        absents=(("\\newcommand{\\NoteTome}{english", "\\newcommand{\\NoteTome}{versions"),), tout=True)

print()
print("Relevés (corrections demandées par le jugement et le contre-jugement, cherchées dans le texte des deux langues) :")
for _, r in releves:
    print("  -", r)
n, ok = len(resultats), sum(resultats)
nr, okr = len(releves), sum(o for o, _ in releves)
print(f"\n{ok} chiffres sur {n} tiennent (présents dans EN et FR, égaux à leur recalcul).")
print(f"{okr} relevés sur {nr} corrigés (présents dans EN et FR, l'ancienne écriture absente).")
sys.exit(0 if ok == n and okr == nr else 1)
