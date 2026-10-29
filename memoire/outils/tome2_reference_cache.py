"""Données des figures et chiffres refaits des chapitres « La référence exacte et le juge » et
« Le cache, l'ordonnanceur et le moteur » du Tome II.

Lit seulement des fichiers commités (journaux et CSV des lots R et O, de l'épreuve J1 et de la
mesure gpt-oss) et écrit sous memoire/figures/tome2/donnees/ :
  t2r-kl-repartition.csv      fonctions de répartition de la KL par position (20b, 2 550 positions)
  t2r-bascules-soi.csv        positions qui basculent elles-mêmes : marge minimale, KL
  t2r-bascules-autres.csv     positions touchées seulement par le cache KV : marge minimale, KL
  t2r-kv-glissant.csv         KL(vérité ‖ troncons) en moyenne glissante, KV f16 contre f32
  t2o-prop1.csv             la proposition du LRU partagé, vérifiée sur les 17 traces réelles
  t2o-chrono-couche.csv     une couche du 120b dont les quatre experts manquent (pas 8, couche 0)
  t2-verif-reference-cache.json  les chiffres du texte refaits par ce second chemin, et leurs écarts

Bibliothèque standard seule. Lancement : python -I -X utf8 memoire/outils/tome2_reference_cache.py
Le programme s'arrête (code 1) si un chiffre refait s'écarte du chiffre publié de plus que sa
tolérance déclarée ci-dessous (TOLERANCES) : c'est son témoin. --casser fausse un chiffre publié
(la part des bascules portée par le KV f16) pour vérifier que le témoin tombe.
"""
import csv
import json
import math
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.normpath(os.path.join(ICI, "..", ".."))
SORTIE = os.path.join(DEPOT, "memoire", "figures", "tome2", "donnees")
PLANCHER_LOG = 1e-7  # les KL ≤ 1e-7 (y compris négatives, plancher du format) sont tracées à 1e-7


def chemin(*p):
    return os.path.join(DEPOT, *p)


def lire_csv(*p):
    with open(chemin(*p), encoding="utf8", newline="") as f:
        lignes = [l for l in f if not l.startswith("#")]
    return list(csv.DictReader(lignes))


def lire_json(*p):
    with open(chemin(*p), encoding="utf8") as f:
        return json.load(f)


def moyenne(v):
    v = list(v)
    return sum(v) / len(v)


def quantile(tries, f):
    p = f * (len(tries) - 1)
    i = int(p)
    r = p - i
    j = min(i + 1, len(tries) - 1)
    return (1 - r) * tries[i] + r * tries[j]


def ecrire(nom, entetes, lignes):
    os.makedirs(SORTIE, exist_ok=True)
    with open(os.path.join(SORTIE, nom), "w", encoding="utf8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(entetes)
        for l in lignes:
            w.writerow(l)


def fmt(x):
    return f"{x:.6e}"


verif = {}
ecarts = []

# Tolérances déclarées avant le calcul : un chiffre publié avec n chiffres significatifs doit être
# retrouvé à une demi-unité de son dernier chiffre (arrondi), sauf mention.
TOLERANCES = {}


def comparer(nom, refait, publie, tol):
    TOLERANCES[nom] = tol
    ok = abs(refait - publie) <= tol
    verif[nom] = {"refait": refait, "publie": publie, "tolerance": tol, "tient": ok}
    if not ok:
        ecarts.append(nom)


casser = "--casser" in sys.argv

# ---------------------------------------------------------------- 1. KL par position, 20b, R0 et R1
R0 = ("mesures", "moteur", "R", "r0")
R1 = ("mesures", "moteur", "R", "r1")
series = {
    "plancher": R0 + ("juge-kl-carte_cmoe-bis-contre-carte_cmoe.csv",),
    "gmoteurs": R0 + ("juge-kl-processeur-contre-carte_cmoe.csv",),
    "r1": R0 + ("juge-kl-llama-carte_cmoe-contre-ref-openai-20b.csv",),
    "rampe": R1 + ("juge-kl-ref-llamacpp-20b-contre-ref-openai-20b.csv",),
    "impose": R1 + ("juge-kl-ref-llamacpp-routage-openai-20b-contre-ref-openai-20b.csv",),
    "imite": R1 + ("juge-kl-ref-llamacpp-imite-q8-kv16-20b-contre-ref-llamacpp-20b.csv",),
    "cassure": R0 + ("juge-kl-llama-carte_cmoe-contre-ref-openai-sans-echelle-20b.csv",),
}
kl = {n: [float(r["kl"]) for r in lire_csv(*p)] for n, p in series.items()}
c4 = lire_csv("mesures", "moteur", "O", "csv", "o-c4-20b.csv")
kl["troncons"] = [float(r["kl_b"]) for r in c4]
kl["llama_c4"] = [float(r["kl_a"]) for r in c4]
for n, v in kl.items():
    assert len(v) == 2550, (n, len(v))
moy = {n: moyenne(v) for n, v in kl.items()}
comparer("kl_gmoteurs_chemin2", moy["gmoteurs"], 0.022735, 5e-7)
comparer("kl_r1_chemin2", moy["r1"], 0.022606, 5e-7)
comparer("kl_rampe_seule", moy["rampe"], 0.0145, 5e-5)
comparer("kl_routage_impose", moy["impose"], 0.00168, 5e-6)
# publié à deux chiffres significatifs (0,029, R-pour-le-memoire § 2.8) : demi-unité de 0,001
comparer("kl_imitations", moy["imite"], 0.029, 5e-4)
comparer("kl_cassure_chemin2", moy["cassure"], 0.26372, 5e-6)
comparer("kl_troncons_c4_20b", moy["troncons"], 0.003679, 5e-7)
comparer("kl_llama_c4_20b", moy["llama_c4"], 0.022606, 5e-7)
part_bascules = 1 - moy["impose"] / moy["rampe"]
comparer("part_kl_retiree_routage_impose", part_bascules, 0.88, 5e-3)
verif["rapport_llama_sur_troncons_20b"] = moy["llama_c4"] / moy["troncons"]

fractions = [i / 200 for i in range(201)]
ordre = ["plancher", "gmoteurs", "r1", "rampe", "impose", "imite", "troncons", "cassure"]
tries = {n: sorted(max(x, PLANCHER_LOG) for x in kl[n]) for n in ordre}
ecrire("t2r-kl-repartition.csv", ["f"] + ordre,
       [[f"{f:.3f}"] + [fmt(quantile(tries[n], f)) for n in ordre] for f in fractions])
verif["mediane_kl"] = {n: quantile(sorted(kl[n]), 0.5) for n in ordre}
verif["p99_kl"] = {n: quantile(sorted(kl[n]), 0.99) for n in ordre}

# ---------------------------------------------------------------- 2. Les bascules (20b, R1)
b = lire_csv(*R1, "csv", "bascules-openai-llamacpp-20b.csv")
soi = [r for r in b if int(r["couches_basculees"]) > 0]
autres = [r for r in b if int(r["couches_basculees"]) == 0]
ecrire("t2r-bascules-soi.csv", ["marge", "kl"],
       [[fmt(float(r["marge_min"])), fmt(max(float(r["kl"]), PLANCHER_LOG))] for r in soi])
ecrire("t2r-bascules-autres.csv", ["marge", "kl"],
       [[fmt(float(r["marge_min"])), fmt(max(float(r["kl"]), PLANCHER_LOG))] for r in autres])
kl_tot = sum(float(r["kl"]) for r in b)
comparer("positions_basculant_elles_memes", len(soi), 1157, 0)
comparer("part_kl_portee_par_elles", sum(float(r["kl"]) for r in soi) / kl_tot, 0.965, 5e-4)
comparer("kl_moyenne_autres", moyenne(float(r["kl"]) for r in autres), 9.4e-4, 5e-6)
jb = lire_json(*R1, "bascules-openai-llamacpp-20b.json")
verif["bascules_json"] = {"part": jb["part_bascules"], "marges_toutes": jb["marges_toutes_quantiles"],
                         "marges_bascules": jb["marges_des_bascules_quantiles"]}
# Ordre de grandeur de la perturbation de la marge (texte, § des bascules) : f_m(0) estimée par la
# pente de la répartition des marges entre 0 et son 1er centile, puis E|δ| ≈ part / f_m(0).
q01 = jb["marges_toutes_quantiles"]["0.01"]
q10 = jb["marges_toutes_quantiles"]["0.1"]
f0_a, f0_b = 0.01 / q01, 0.1 / q10
verif["densite_marge_en_zero"] = [f0_a, f0_b]
verif["perturbation_moyenne_de_marge"] = [jb["part_bascules"] / f0_a, jb["part_bascules"] / f0_b]

# ---------------------------------------------------------------- 3. Le KV f16 contre f32
kv = lire_csv("mesures", "moteur", "O", "corrections", "csv", "kv-f16-f32-par-position.csv")
cas = {}
for r in kv:
    cas.setdefault(r["cas"], []).append(r)
def glisser(v, w=16):
    return [moyenne(v[max(0, i - w + 1):i + 1]) for i in range(len(v))]
f0_120 = cas["f0-120b"]
f0_20 = cas["f0-20b"]
g = {
    "f0_120b_f16": glisser([float(r["kl_f16"]) for r in f0_120]),
    "f0_120b_f32": glisser([float(r["kl_f32"]) for r in f0_120]),
    "f0_20b_f16": glisser([float(r["kl_f16"]) for r in f0_20]),
    "f0_20b_f32": glisser([float(r["kl_f32"]) for r in f0_20]),
}
pos = [int(r["position"]) for r in f0_120]
assert pos == [int(r["position"]) for r in f0_20]
ecrire("t2r-kv-glissant.csv", ["position"] + list(g),
       [[p] + [fmt(g[n][i]) for n in g] for i, p in enumerate(pos)])
inv16 = [r for r in cas["invite-f16"]]
inv32 = [r for r in cas["invite-f32"]]
ecrire("t2r-kv-invite-glissant.csv", ["position", "invite_f16", "invite_f32"],
       [[int(a["position"]), fmt(x), fmt(y)] for a, x, y in zip(
           inv16, glisser([float(r["kl_f16"]) for r in inv16]), glisser([float(r["kl_f32"]) for r in inv32]))])
comparer("kv_f16_120b_f0", moyenne(float(r["kl_f16"]) for r in f0_120), 0.00308, 5e-6)
comparer("kv_f32_120b_f0", moyenne(float(r["kl_f32"]) for r in f0_120), -0.00048, 5e-6)
comparer("kv_f16_20b_f0", moyenne(float(r["kl_f16"]) for r in f0_20), 0.00174, 5e-6)
comparer("kv_f32_20b_f0", moyenne(float(r["kl_f32"]) for r in f0_20), -0.00048, 5e-6)
tard16 = [float(r["kl_f16"]) for r in inv16 if int(r["position"]) >= 512]
tard32 = [float(r["kl_f32"]) for r in inv32 if int(r["position"]) >= 512]
comparer("kv_f16_invite_512_plus", moyenne(tard16), 0.00963, 5e-6)
comparer("kv_f32_invite_512_plus", moyenne(tard32), -0.00054, 5e-6)
# Part des bascules de routage portée par le seul arrondi f16 du KV (épreuve J1, § 6.1).
accord_vrai = {"avant_512": 0.969, "apres_512": 0.931}
accord_imite = {"avant_512": 0.993, "apres_512": 0.979}
if casser:
    accord_imite["avant_512"] = 0.975
parts = {t: 1 - (1 - accord_imite[t]) / (1 - accord_vrai[t]) for t in accord_vrai}
comparer("part_bascules_kv_avant_512", parts["avant_512"], 0.77, 5e-3)
comparer("part_bascules_kv_apres_512", parts["apres_512"], 0.70, 5e-3)

# ---------------------------------------------------------------- 4. La proposition du LRU partagé
lignes = []
max_ecart = 0.0
for modele, L, k in (("20b", 24, 4), ("120b", 36, 4)):
    d = lire_json("mesures", "localite-gpt-oss", modele, f"localite-gpt-oss-{modele}.json")
    assert d["L"] == L and d["k"] == k
    # Les traces sont nommées « genre.régime » (code.lecture, tous.generation…).
    for nom, v in d["traces"].items():
        trace, regime = nom.split(".")
        if "seuil_lru_partage" in v:
            s = v["seuil_lru_partage"]
            a, bb = s[str((L - 1) * k)], s[str(L * k)]
            borne = v["seuil_borne_ii"]
            max_ecart = max(max_ecart, abs(bb - borne))
            lignes.append([len(lignes) + 1, modele, trace, regime, f"{a:.6f}", f"{bb:.6f}", f"{borne:.6f}",
                           f"{s[str(L * k + 1)]:.6f}"])
ecrire("t2o-prop1.csv", ["i", "modele", "trace", "regime", "lru_Lm1k", "lru_Lk", "borne", "lru_Lk1"], lignes)
comparer("traces_prop1", len(lignes), 17, 0)
comparer("zero_sous_le_seuil", max(float(l[4]) for l in lignes), 0.0, 0.0)
comparer("egalite_iii_ecart_max", max_ecart, 0.0, 1e-12)

# La falaise dense (lot O) : le plateau = r̄ (T − 1)/T de la proposition, sur les quatre lectures.
fal = lire_csv("mesures", "moteur", "O", "csv", "falaise-20b-dense.csv")
lect = {int(r["emplacements"]): r for r in fal if r["trace"] == "t20b.tous.lecture"}
comparer("falaise_lru_92", float(lect[92]["h_lru"]), 0.0, 0.0)
comparer("plateau_96", float(lect[96]["h_lru"]), 0.5026, 5e-5)
comparer("plateau_120", float(lect[120]["h_lru"]), 0.5037, 5e-5)
comparer("belady_92", float(lect[92]["h_belady"]), 0.664, 5e-4)

# ---------------------------------------------------------------- 5. Une couche, chronogramme mesuré
ch = lire_csv("mesures", "moteur", "O", "csv", "chronogramme-120b.csv")
couche = [r for r in ch if r["pas"] == "8" and r["couche"] == "0"]
ecrire("t2o-chrono-couche.csv",
       ["rang", "expert", "soumis", "lu", "copie_debut", "copie_fin", "dec_debut", "dec_fin", "routeur", "fin_couche"],
       [[i, r["expert"], r["soumis_ms"], r["lu_ms"], r["copie_debut_ms"], r["copie_fin_ms"], r["dec_debut_ms"],
         r["dec_fin_ms"], r["routeur_ms"], r["fin_couche_ms"]] for i, r in enumerate(couche)])
dur_lect = [float(r["lu_ms"]) - float(r["soumis_ms"]) for r in couche]
verif["chrono_couche_lectures_ms"] = dur_lect

# ---------------------------------------------------------------- 6. Préchargement et C6
js = lire_csv("mesures", "moteur", "O", "csv", "o-jetons-s.csv")
def gen(prefixe):
    return [float(r["generation_jetons_s"]) for r in js if r["passe"].startswith(prefixe)]
pfA = gen("2026-10-16-s3-01-pf-A") + gen("2026-10-16-s3-04-pf-A")
pfB = gen("2026-10-16-s3-02-pf-B") + gen("2026-10-16-s3-03-pf-B")
gain_pf = moyenne(pfB) / moyenne(pfA) - 1
bruit_pf = max(abs(pfA[0] - pfA[1]) / moyenne(pfA), abs(pfB[0] - pfB[1]) / moyenne(pfB))
comparer("prechargement_gain", gain_pf, -0.11, 5e-3)
verif["prechargement_bruit"] = bruit_pf
vit = lire_csv("mesures", "moteur", "O", "corrections", "csv", "vitesse-2026-10-16-passes.csv")
garde = [float(r["gen"]) for r in vit if r["nom"] == "T120g"]
base = lire_csv("mesures", "moteur", "O", "corrections", "csv", "base-2026-10-16-passes.csv")
t16 = [float(r["generation_j_s"]) for r in base if r["nom"] == "L16"]
comparer("troncons_garde_moyenne", moyenne(garde), 1.965, 5e-4)
comparer("base_t16_moyenne", moyenne(t16), 0.884, 5e-4)
comparer("c6_rapport", moyenne(garde) / moyenne(t16), 2.22, 5e-3)
bruit_garde = (max(garde) - min(garde)) / moyenne(garde)
verif["c6"] = {"passes_troncons_garde": garde, "passes_base_t16": t16, "bruit_troncons_etendue": bruit_garde,
               "seuil_regle": 2 * 0.110 + 0.03}

# Barres de la figure C6 : moyenne, plus petite et plus grande passe de chaque configuration. Les
# deux séances (base de 08 h 13 à 10 h 06, vitesse de la ronde) sont du même jour, sur secteur.
barres = []
for nom, fr, en, passes in (
        ("L6", "llama.cpp fit -t 6", "llama.cpp fit -t 6", [float(r["generation_j_s"]) for r in base if r["nom"] == "L6"]),
        ("L10", "llama.cpp fit -t 10", "llama.cpp fit -t 10", [float(r["generation_j_s"]) for r in base if r["nom"] == "L10"]),
        # « -\/- » : deux traits d'union que TeX ne fond pas en tiret.
        ("Lm", "llama.cpp -\\/-n-cpu-moe 34", "llama.cpp -\\/-n-cpu-moe 34", [float(r["generation_j_s"]) for r in base if r["nom"] == "Lm"]),
        ("L12", "llama.cpp fit -t 12", "llama.cpp fit -t 12", [float(r["generation_j_s"]) for r in base if r["nom"] == "L12"]),
        ("L16", "llama.cpp fit -t 16", "llama.cpp fit -t 16", t16),
        # Pas de virgule dans les étiquettes : pgfplots lit le CSV sans guillemets.
        ("T120k", "troncons : garde et KV f32", "troncons: guard and f32 KV", [float(r["gen"]) for r in vit if r["nom"] == "T120k"]),
        ("T120g", "troncons : garde", "troncons: guard", garde),
        ("T120s", "troncons : sans garde", "troncons: no guard", [float(r["gen"]) for r in vit if r["nom"] == "T120s"])):
    m = moyenne(passes)
    barres.append([len(barres), nom, fr, en, f"{m:.4f}", f"{m - min(passes):.4f}", f"{max(passes) - m:.4f}", len(passes)])
ecrire("t2o-c6.csv", ["i", "nom", "etiquette_fr", "etiquette_en", "moyenne", "moins", "plus", "passes"], barres)

verif["ecarts"] = ecarts
verif["casser"] = casser
with open(os.path.join(SORTIE, "t2-verif-reference-cache.json"), "w", encoding="utf8") as f:
    json.dump(verif, f, ensure_ascii=False, indent=1)
if ecarts:
    print("ÉCART entre chiffre refait et chiffre publié :", ", ".join(ecarts), file=sys.stderr)
    sys.exit(1)
print(f"tome2_reference_cache : {len(TOLERANCES)} chiffres refaits, 0 écart")
