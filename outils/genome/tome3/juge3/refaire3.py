# Juge de la troisième passe : refait, par mon code, chaque nombre neuf ou déplacé des retouches (7a40c54, 6137230,
# 1482dbe), depuis les fichiers commités sous mesures/ (ou le fichier commité que cite la légende), sans lire les
# fonctions des scripts du lot qui les calculent (seulement leur git diff). Compare à la valeur imprimée, à
# l'arrondi imprimé. Règle déclarée (JUGEMENT-figures3.md § 1.2) : égal à l'arrondi imprimé ; un nombre à moins de
# 1e-6 relatif d'une demi-unité de son dernier chiffre est signalé.
# Usage : python -I -X utf8 refaire3.py [--casser]   (--casser : chaque valeur recalculée faussée de 1 %)
import csv, json, math, re, statistics, sys
from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP
from pathlib import Path

DEPOT = Path(__file__).resolve().parents[4]
M = DEPOT / "mesures"
DON = DEPOT / "memoire/figures/tome3/donnees"
CASSER = "--casser" in sys.argv
LIGNES = []


def lire_csv(p):
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def jl(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


# --- valeurs imprimées ------------------------------------------------------------------------------------
IMPR = {}
for f in DON.glob("*-nombres.tex"):
    for m in re.finditer(r"\\def\\(\w+)\{([^}]*)\}", f.read_text(encoding="utf-8")):
        IMPR[m.group(1)] = m.group(2)
for m in re.finditer(r"\\providecommand\{\\(Lat\w+)\}\{\\EF\{([^}]*)\}", (DON / "latents-chiffres.tex").read_text(encoding="utf-8")):
    IMPR[m.group(1)] = m.group(2)
for m in re.finditer(r"csname (Lat\w+)\\endcsname\{([^}]*)\}", (DON / "latents-chiffres.tex").read_text(encoding="utf-8")):
    IMPR[m.group(1)] = m.group(2)
for r in lire_csv(DON / "synthese-nombres.csv"):
    IMPR["synth:" + r[next(iter(r))]] = r[list(r)[1]]


def decimales(s: str) -> int:
    s = s.replace("\\ensuremath{-}", "-").replace("−", "-")
    return len(s.split(".")[1]) if "." in s else 0


def comparer(cle: str, valeur: float, imprime: str | None = None, dec: int | None = None, note: str = "",
             source: str = ""):
    """imprime : la chaîne du fichier de nombres (par défaut IMPR[cle]) ; dec : décimales de l'impression dans la
    légende quand elle diffère de celle du fichier (ex. ×310 pour 310.385)."""
    s = IMPR.get(cle) if imprime is None else imprime
    assert s is not None, f"clé absente : {cle}"
    v = valeur * (1.01 if CASSER else 1.0)
    s_num = float(s.replace("\\ensuremath{-}", "-").replace("−", "-"))
    d = decimales(s) if dec is None else dec
    # arrondi de ma valeur au nombre de décimales imprimées, comparé à l'arrondi de la valeur du fichier
    mien = round(v, d)
    leur = round(s_num, d)
    egal = abs(mien - leur) < 0.5 * 10 ** (-d) * 1e-6 + 1e-12
    q = v * 10 ** d
    # près d'un bord : à moins d'un centième d'unité du dernier chiffre d'une demi-unité (la règle « 1e-6 relatif »
    # du § 1.2 ne dit rien pour un nombre à six décimales : corrigée ici, et dite dans le jugement)
    bord = abs((q - math.floor(q)) - 0.5) < 0.01
    LIGNES.append({"cle": cle, "imprime": s, "decimales": d, "recalcule": repr(v), "egal": egal,
                   "pres_d_un_bord": bord, "note": note, "source": source})


# =========================================================================================================
# III-7.4 (7a40c54) : la seconde pointe, depuis colonnes-energie-erreur.csv
src = M / "genome/genome/csv/colonnes-energie-erreur.csv"
rows = lire_csv(src)
assert len(rows) == 2880
col = [int(r["colonne"]) for r in rows]
assert col == list(range(2880))
E = [float(r["energie_exacte"]) for r in rows]
B = [float(r["erreur_brin_pondere"]) for r in rows]
S = [float(r["erreur_s_etoile"]) for r in rows]
Ba = [float(r["erreur_base"]) for r in rows]
mE, mB, mS, mBa = (statistics.fmean(x) for x in (E, B, S, Ba))
geante = max(range(2880), key=lambda i: E[i])
assert geante == 1011
second = sorted(range(2880), key=lambda i: -B[i])
second = [i for i in second if i != geante][0]
debut = geante // 64 * 64
comparer("synth:col-second", second, source=str(src))
comparer("synth:col-second-energie-x", E[second] / mE, dec=2, note="imprimé ×0,83", source=str(src))
comparer("synth:col-second-brin-x", B[second] / mB, dec=0, note="imprimé ×310", source=str(src))
comparer("synth:col-second-sstar-x", S[second] / mS, dec=2, note="imprimé ×1,04", source=str(src))
comparer("synth:col-second-base-x", Ba[second] / mBa, dec=2, note="imprimé ×0,87", source=str(src))
comparer("synth:col-second-bord", int(second % 64 == 0), source=str(src))
comparer("synth:col-second-morceau", int(debut <= second < debut + 64), source=str(src))
bords = [i for i in range(0, 2880, 64) if i not in (geante, second)]
comparer("synth:col-bord-autres-n", len(bords), source=str(src))
comparer("synth:col-bord-autres-x", statistics.fmean(B[i] for i in bords) / mB, dec=2, note="imprimé ×0,70", source=str(src))
comparer("synth:col-bord-autres-max-x", max(B[i] for i in bords) / mB, dec=2, note="imprimé ×0,87", source=str(src))
sans = [i for i in range(debut, debut + 64) if i not in (geante, second)]
comparer("synth:col-morceau-sans-n", len(sans), source=str(src))
comparer("synth:col-morceau-sans-x", statistics.fmean(B[i] for i in sans) / mB, dec=1, note="imprimé ×4,0", source=str(src))
# ce que la légende dit de l'ancien « bords ×7,6 » : la moyenne des 45 bords, la géante exclue (elle n'en est pas un)
tous_bords = [i for i in range(0, 2880, 64) if i != geante]
comparer("synth:col-bord-x", statistics.fmean(B[i] for i in tous_bords) / mB, dec=1, note="« bords ×7,6 » de la source", source=str(src))

# =========================================================================================================
# III-8.5 (6137230) : le coût de l'alphabet, le gain sur les douze, depuis le journal du codec réel (second fichier)
src = M / "genome/predictif-elagage/taux-reel-colonne-12-gptoss20b.json"
tr = jl(src)
ts = tr["tenseurs"]
assert len(ts) == 12 and tr["temoins"]["tous_exacts"] is True
alph = [t["bpp_total_nib_kappa"] - t["bpp_total_zero_fondu"] for t in ts]
comparer("CodonNColonneAlphabetMin", min(alph), source=str(src))
comparer("CodonNColonneAlphabetMax", max(alph), source=str(src))
gain = [t["bpp_total_zero_fondu"] - t["bpp_total_nib_kappa_colonne"] for t in ts]
comparer("CodonNSansPerteGainDouze", statistics.fmean(gain), source=str(src))
comparer("CodonNSansPerteCouchesZero", sum(1 for t in ts if t["nom"].split(".")[1] == "0"), source=str(src))
# « les barres négatives sont surtout ce coût » : pour chaque barre négative, la part du coût d'alphabet dans |gain|
neg = [(t["nom"], g, a, g + a) for t, g, a in zip(ts, gain, alph) if g < 0]
CONTROLES = {"III-8.5 barres négatives (nom, gain, coût d'alphabet, part de la colonne seule)":
             [(n, round(g, 5), round(a, 5), round(c, 5)) for n, g, a, c in neg]}
# le même gain, recalculé depuis colonne-par-tenseur.csv (le fichier que lit le script) : doit être égal
cpt = {r["tenseur"]: r for r in lire_csv(M / "genome/construction/synthese/colonne-par-tenseur.csv")}
CONTROLES["III-8.5 écart max colonne-par-tenseur.csv contre taux_reel (4 colonnes)"] = max(
    abs(float(cpt[t["nom"]][c]) - t[k]) for t in ts for c, k in
    (("sans_perte", "bpp_total_identite"), ("zero_octet_kappa", "bpp_total_zero_fondu"),
     ("zero_demi_octet_kappa", "bpp_total_nib_kappa"), ("zero_demi_octet_kappa_colonne", "bpp_total_nib_kappa_colonne")))

# =========================================================================================================
# III-8.6 bis (6137230) : J5, J6, compagnon du 120b
seance = M / "disque/placement/juge/seance"
n5 = {jl(f)["n"] for f in seance.glob("J5-*-C120.json")}
n6 = {jl(f)["n"] for f in seance.glob("J6-*.json")}
assert len(n5) == 1 and len(n6) == 1, (n5, n6)
comparer("CodonNEncartTiresJcinq", n5.pop(), source="J5-*-C120.json, toutes passes")
comparer("CodonNEncartTiresJsix", n6.pop(), source="J6-*.json, toutes passes et tous fichiers")
src = M / "genome/construction/synonyme/proxy/proxy-120b-exact-contre-rapide-frontiere.csv"
par = {}
for r in lire_csv(src):
    par.setdefault(int(r["fenetre"]), []).append(float(r["kl"]))
moy = [statistics.fmean(par[k]) for k in sorted(par)]
assert len(moy) == 10
comparer("CodonNCompagnonKL", statistics.fmean(moy), source=str(src))
comparer("CodonNCompagnonDeuxSigma", 2 * statistics.stdev(moy) / math.sqrt(10), source=str(src) + " (2σ par fenêtres)")
CONTROLES["III-8.6 bis : σ naïf du résumé (kl_incertitude), que le juge 2 citait"] = jl(src.with_suffix(".json"))["resume"]["kl_incertitude"]

# =========================================================================================================
# III-10.1 (6137230) : 768 sur 768, par le journal du vérificateur (second fichier) et par tailles.json
src = M / "genome/construction/codon/journaux/verifier-20b-v12.json"
vj = jl(src)
CONTROLES["III-10.1 : clés du journal du vérificateur"] = sorted(vj)[:40]
t20 = jl(M / "genome/construction/codon/tailles.json")["totaux"]["20b"]
comparer("JconsNExpertsDecodes", t20["experts_exacts_v12"], source="tailles.json")
comparer("JconsNExpertsTous", t20["experts"], source="tailles.json")

# =========================================================================================================
# III-10.3 (6137230) : les deux chemins sur R1, les trois variantes, par position
def moy_fen(p):
    d = {}
    for r in lire_csv(p):
        d.setdefault(int(r["fenetre"]), []).append(float(r["kl"]))
    return [statistics.fmean(d[k]) for k in sorted(d)]


SY = M / "genome/construction/synonyme"
ecarts = {}
for var, fm, fs in (("frontiere", "kl-moteur-frontiere-positions.csv", "kl-frontiere-768-positions.csv"),
                    ("lambda1", "kl-moteur-synonyme-positions.csv", "kl-synonyme-768-positions.csv"),
                    ("lambda0", "kl-moteur-synonyme-l0-positions.csv", "kl-synonyme-l0-768-positions.csv")):
    a, b = moy_fen(SY / "moteur" / fm), moy_fen(SY / "kl" / fs)
    assert len(a) == len(b) == 10
    ecarts[var] = [x - y for x, y in zip(a, b)]
comparer("JconsNCheminRunMoy", statistics.fmean(ecarts["frontiere"]), source="synonyme/moteur et synonyme/kl, par position")
comparer("JconsNCheminRunMoyUn", statistics.fmean(ecarts["lambda1"]), source="idem")
comparer("JconsNCheminRunMoyZero", statistics.fmean(ecarts["lambda0"]), source="idem")
tous = [x for v in ecarts.values() for x in v]
comparer("JconsNCheminRunMin", min(tous), source="idem, les trois variantes")
comparer("JconsNCheminRunMax", max(tous), source="idem, les trois variantes")

# =========================================================================================================
# III-9.3 (6137230) : le cadre de la forêt et « au moins 9 fenêtres sur 10 »
r1 = {"frontiere": moy_fen(SY / "kl/kl-frontiere-768-positions.csv"),
      "lambda1": moy_fen(SY / "kl/kl-synonyme-768-positions.csv"),
      "lambda0": moy_fen(SY / "kl/kl-synonyme-l0-768-positions.csv")}
d_r1 = {"un-frontiere": [b - a for a, b in zip(r1["frontiere"], r1["lambda1"])],
        "zero-frontiere": [b - a for a, b in zip(r1["frontiere"], r1["lambda0"])],
        "zero-un": [b - a for a, b in zip(r1["lambda1"], r1["lambda0"])]}
ecart_csv = {}
d_neuf = {}
for cle in d_r1:
    lig = lire_csv(DON / f"synonyme-foret-{cle}.csv")
    r1csv = [float(r["d"]) for r in lig if r["bande"] == "r1"]
    d_neuf[cle] = [float(r["d"]) for r in lig if r["bande"] == "neuf"]
    ecart_csv[cle] = max(abs(x - y) for x, y in zip(r1csv, d_r1[cle]))
CONTROLES["III-9.3 : R1 par position contre le CSV de la figure (écart max par panneau)"] = ecart_csv
CONTROLES["III-9.3 : note, le panneau λ = 0 contre frontière sur R1 du lot lit le fichier du juge"] = \
    "écart ci-dessus à juger"
tout = []
for jeu in (d_r1, d_neuf):
    for v in jeu.values():
        m, s = statistics.fmean(v), statistics.stdev(v) / math.sqrt(len(v))
        tout += v + [m - 2 * s, m + 2 * s]
CONTROLES["III-9.3 : extrêmes (d et bandes)"] = (min(tout), max(tout))
# règle écrite dans le script (lue dans le diff) : marge 0,02, pas 0,02
comparer("SynoNForXmin", math.floor((min(tout) - 0.02) / 0.02) * 0.02, source="per-position R1 + CSV neuves")
comparer("SynoNForXmax", math.ceil((max(tout) + 0.02) / 0.02) * 0.02, source="idem")
gagnes = [sum(1 for x in v if x < 0) for jeu in (d_r1, d_neuf) for k, v in jeu.items() if k != "zero-un"]
CONTROLES["III-9.3 : fenêtres gagnées contre la frontière (R1 un, R1 zéro, neuves un, neuves zéro)"] = gagnes
comparer("SynoNForBatMin", min(gagnes), source="idem")
comparer("SynoNForFenetres", len(d_r1["un-frontiere"]), source="idem")

# =========================================================================================================
# III-9.6 (6137230) : le cadre des variantes, depuis variantes-768.csv (pleine précision)
src = SY / "figures/variantes-768.csv"
vv = {r["variante"]: r for r in lire_csv(src)}
bx = [float(vv[v]["bits_par_poids"]) for v in ("frontiere", "synonyme-l1", "synonyme-l0")]
xmin = math.floor(round((min(bx) - 0.02) / 0.01, 9)) * 0.01
xmax = math.ceil(round((max(bx) + 0.02) / 0.01, 9)) * 0.01
comparer("SynoNVarXmin", xmin, source=str(src))
comparer("SynoNVarXmax", xmax, source=str(src))
comparer("SynoNVarPartLargeur", 100 * (max(bx) - min(bx)) / (xmax - xmin), source=str(src) + " (pleine précision)")
CONTROLES["III-9.6 : part de la largeur, pleine précision ; depuis les bits arrondis à 4 décimales"] = (
    100 * (max(bx) - min(bx)) / (xmax - xmin), 100 * (round(max(bx), 4) - round(min(bx), 4)) / (xmax - xmin))
CONTROLES["III-9.6 : part avec l'ancien cadre 2,54-2,72"] = 100 * (max(bx) - min(bx)) / 0.18

# =========================================================================================================
# III-9.1 (c) (6137230) : 3 s'éloignent, 1 à même distance, depuis la rangée commitée sous mesures/
src = M / "genome/tome3/latents/rangee-L08-E00-gate.csv"
el = meme = rap = 0
zero_ok = True
for r in lire_csv(src):
    if r["change"] != "1":
        continue
    x, f, s = float(r["exact"]), float(r["frontiere"]), float(r["synonyme"])
    df, ds = abs(f - x), abs(s - x)
    if abs(df - ds) < 1e-9:
        meme += 1
        zero_ok &= (x == 0.0)
    elif ds > df:
        el += 1
    else:
        rap += 1
assert rap == 0 and zero_ok
comparer("LatRangEloignes", el, source=str(src))
comparer("LatRangMemeDistance", meme, source=str(src))

# =========================================================================================================
# III-7.6 (6137230) : le terme de comparaison de z(4) − z(5), deux journaux de juges
j1 = jl(DEPOT / "outils/genome/tome3/juge-latents/juge-etats-marges.json")
comparer("LatBordQuatreCinqLarge", j1["marge45"]["bord_origine"][2], source="juge-latents/juge-etats-marges.json")
j2 = jl(DEPOT / "outils/genome/tome3/juge2-latents/journaux/juge2-etats.json")
CONTROLES["III-7.6 : clés du journal du juge 2 (états)"] = sorted(j2)[:30]

# =========================================================================================================
# III-9.7 (6137230) : ce qui se tire du spectre commité du lot B, sans le journal du juge 2
src = M / "genome/construction/synonyme/figures/spectre-L08-E00-gate.csv"
sp = lire_csv(src)
lam = [float(r["lambda_calib"]) for r in sp]
ef = [float(r["e_frontiere"]) for r in sp]
es = [float(r["e_synonyme"]) for r in sp]
cf = sum(l * e for l, e in zip(lam, ef))
cs = sum(l * e for l, e in zip(lam, es))
af = sum(l * e for l, e in list(zip(lam, ef))[3:])
as_ = sum(l * e for l, e in list(zip(lam, es))[3:])
comparer("LatNuageAutresF", af, source=str(src) + " (Σ_{k≥4} λ_k e_k)")
comparer("LatNuageAutresS", as_, source=str(src))
comparer("LatNuageAutresPartGain", 100 * (af - as_) / (cf - cs), source=str(src))
comparer("LatNuageHorsTrois", 100 * (1 - sum(lam[:3]) / sum(lam)), source=str(src) + " (1 − Σλ_1..3 / Σλ)")
CONTROLES["III-9.7 : rapport quadratique pondéré depuis le spectre"] = math.sqrt(cs / cf)
# ce que je ne peux tirer que du journal du juge 2 (ou de la source, voir sources_latents.py)
jj = jl(DEPOT / "outils/genome/tome3/juge2-latents/journaux/juge2-nuage-rangee.json")["entrees_reelles"]
rr = jj["rapport_par_entree_2880_dimensions"]
comparer("LatNuageEntreesMin", rr["min"], source="journal du juge 2 (refait à la source par sources_latents.py)")
comparer("LatNuageEntreesMed", rr["mediane"], source="idem")
comparer("LatNuageEntreesMax", rr["max"], source="idem")
comparer("LatNuageEntreesMaxBrut", rr["max"], source="idem")
comparer("LatNuageEntreesSousTete", 100 * jj["part_des_entrees_sous_le_seuil_de_la_tete"], source="idem")
comparer("LatNuageAngleMed", jj["angle_entree_plan_u1_u2_deg"]["mediane"], source="idem")
CONTROLES["III-9.7 : projections sur (u1, u2), rapport médian, max, part sous 0,135 (journal du juge 2)"] = (
    jj["projection_sur_le_plan_u1_u2"]["rapport_mediane"], jj["projection_sur_le_plan_u1_u2"]["rapport_max"],
    jj["projection_sur_le_plan_u1_u2"]["part_sous_le_seuil"])
# la quatrième barre (latents-barres-entrees.csv) : médiane, médiane − min, max − médiane
bar = lire_csv(DON / "latents-barres-entrees.csv")[0]
for k, v in (("rapport", rr["mediane"]), ("bas", rr["mediane"] - rr["min"]), ("haut", rr["max"] - rr["mediane"])):
    comparer(f"barre-entrees:{k}", v, imprime=bar[k], source="latents-barres-entrees.csv")

# =========================================================================================================
sortie = DEPOT / "outils/genome/tome3/juge3/journaux" / ("refaire3-casse.json" if CASSER else "refaire3.json")
n_egaux = sum(1 for l in LIGNES if l["egal"])
res = {"nombres": len(LIGNES), "egaux": n_egaux, "tombent": [l["cle"] for l in LIGNES if not l["egal"]],
       "pres_d_un_bord": [l["cle"] for l in LIGNES if l["pres_d_un_bord"]], "lignes": LIGNES, "controles": CONTROLES}
sortie.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
print(f"{len(LIGNES)} nombres, {n_egaux} égaux ; tombent : {res['tombent']} ; près d'un bord : {res['pres_d_un_bord']}")
for k, v in CONTROLES.items():
    print("-", k, ":", v)
