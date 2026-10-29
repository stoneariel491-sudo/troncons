"""Produit les CSV des figures du mémoire (memoire/figures/donnees/) depuis les journaux commités.

Aucun nombre n'est écrit à la main ici : chaque CSV est lu ou dérivé d'un journal de
fondations/journaux/ (nommé dans le commentaire de sa fonction). Les seules constantes sont
les plafonds calculés d'après les fiches techniques, chacune avec sa dérivation.
Bibliothèque standard seule. Usage : python -I -X utf8 memoire/outils/donnees_figures.py
"""
import csv
import json
import re
from pathlib import Path

DEPOT = Path(__file__).resolve().parents[2]
J = DEPOT / "fondations" / "journaux"
SORTIE = DEPOT / "memoire" / "figures" / "donnees"

# Plafonds calculés (fondations/01-machine.md § 0) :
PLAFOND_NVME = 7.877    # PCIe 4.0 x4 : 4 voies x 16 GT/s x 128/130 / 8
PLAFOND_RAM = 41.6      # un module DDR5 à 5 200 MT/s x 8 octets
PLAFOND_PCIE = 15.754   # PCIe 4.0 x8
PLAFOND_VRAM = 256.0    # GDDR6 128 bits à 16 Gbit/s


def ecrire(nom, entetes, lignes):
    SORTIE.mkdir(parents=True, exist_ok=True)
    with open(SORTIE / nom, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(entetes)
        for l in lignes:
            w.writerow(l)
    return nom


def lire_jsonl(chemin):
    with open(chemin, encoding="utf-8-sig") as f:
        return [json.loads(l) for l in f if l.strip()]


def lire_json(chemin):
    with open(chemin, encoding="utf-8-sig") as f:
        return json.load(f)


def champs(ligne):
    return dict(re.findall(r"(\w[\w+]*)=([^\s]+)", ligne))


# --------------------------------------------------------------------------- 01 machine
def disque():
    """01-machine/disque-balayage.csv : débit par bloc et profondeur, passages A et B (ABBA).
    Erreur = demi-écart |A - B| / 2 (le bruit ABBA de l'étude)."""
    faits = []
    with open(J / "01-machine" / "disque-balayage.csv", encoding="utf-8") as f:
        lignes = list(csv.DictReader(f))
    for acces in ("alea", "seq"):
        for qd in ("1", "4", "16", "64"):
            sel = [l for l in lignes if l["acces"] == acces and l["qd"] == qd]
            if not sel:
                continue
            rangs = [(int(l["bloc_o"]) / 1024, float(l["go_s_moy"]),
                      abs(float(l["go_s_A"]) - float(l["go_s_B"])) / 2) for l in sel]
            rangs.sort()
            faits.append(ecrire(f"machine-disque-{acces}-qd{qd}.csv", ["bloc_kio", "go_s", "err"],
                                [(f"{b:g}", f"{g:.4f}", f"{e:.4f}") for b, g, e in rangs]))
    return faits


def aes():
    """01-machine/aes-xts-batterie.log : déchiffrement XTS-AES par CNG, médiane, min, max.
    La première ligne RESULTAT suit le témoin forcé à faux (--fausser) : écartée."""
    lignes = (J / "01-machine" / "aes-xts-batterie.log").read_text(encoding="utf-8-sig").splitlines()
    series = {"128": [], "256": []}
    temoin_ok = False
    for l in lignes:
        if l.startswith("TEMOIN vecteur"):
            temoin_ok = l.strip().endswith("=ok")
        if l.startswith("RESULTAT") and temoin_ok:
            c = champs(l)
            cle = "128" if "128" in c["op"] else "256"
            m, a, b = float(c["go_s_mediane"]), float(c["go_s_min"]), float(c["go_s_max"])
            series[cle].append((int(c["fils"]), m, m - a, b - m))
    return [ecrire(f"machine-aes-{k}.csv", ["fils", "go_s", "moins", "plus"],
                   [(f, f"{m:.3f}", f"{a:.3f}", f"{b:.3f}") for f, m, a, b in v]) for k, v in series.items()]


def ram_latence():
    """01-machine/memoire-batterie-verrou.log, bloc « latence selon la taille » : chasse de
    pointeurs (cycle de Sattolo), médiane, min, max en ns."""
    texte = (J / "01-machine" / "memoire-batterie-verrou.log").read_text(encoding="utf-8-sig")
    bloc = texte.split("== latence selon la taille", 1)[1].split("==", 1)[0]
    rangs = []
    for l in bloc.splitlines():
        if l.startswith("RESULTAT op=latence"):
            c = champs(l)
            m, a, b = float(c["ns_mediane"]), float(c["ns_min"]), float(c["ns_max"])
            rangs.append((int(c["taille"]) / 2**20, m, m - a, b - m))
    return [ecrire("machine-ram-latence.csv", ["taille_mio", "ns", "moins", "plus"],
                   [(f"{t:g}", f"{m:.1f}", f"{a:.1f}", f"{b:.1f}") for t, m, a, b in rangs])]


def thermique():
    """01-machine/thermique-secteur-charge.csv et thermique-batterie.csv : débit de la GEMV q4b
    par tranche de 5 s pendant 5 min. Recopiés (en-têtes normalisés) pour les figures."""
    faits = []
    for src, nom in (("thermique-secteur-charge.csv", "machine-thermique-secteur.csv"),
                     ("thermique-batterie.csv", "machine-thermique-batterie.csv")):
        with open(J / "01-machine" / src, encoding="utf-8") as f:
            rangs = [(l["t_s"], l["go_s"]) for l in csv.DictReader(f)]
        faits.append(ecrire(nom, ["t_s", "go_s"], rangs))
    return faits


def pcie_generation():
    """01-machine/carte-lien-pcie.csv (nvidia-smi, sans en-tête) : horodatage, génération du
    lien, largeur, occupation, horloges SM et mémoire, puissance, état P."""
    rangs = []
    t0 = None
    with open(J / "01-machine" / "carte-lien-pcie.csv", encoding="utf-8") as f:
        for l in csv.reader(f):
            if len(l) < 6:
                continue
            h = l[0].strip().split(" ")[1]
            hh, mm, ss = h.split(":")
            t = int(hh) * 3600 + int(mm) * 60 + float(ss)
            t0 = t if t0 is None else t0
            mem = float(l[5].strip().split(" ")[0])
            rangs.append((f"{t - t0:.2f}", l[1].strip(), f"{mem:g}"))
    return [ecrire("machine-pcie-generation.csv", ["t_s", "gen", "mem_mhz"], rangs)]


def etages():
    """Plafonds calculés contre débits mesurés : 01-machine/debits-mesures.json (disque, PCIe,
    VRAM) et memoire.log (RAM, lecture un fil, premier passage au témoin tenu)."""
    d = lire_json(J / "01-machine" / "debits-mesures.json")
    ram = None
    for l in (J / "01-machine" / "memoire.log").read_text(encoding="utf-8-sig").splitlines():
        if l.startswith("RESULTAT op=lecture fils=1") and "temoin=ok" in l:
            ram = float(champs(l)["go_s_mediane"])
            break
    rangs = [
        (0, "NVMe → RAM", "NVMe → RAM", PLAFOND_NVME, d["disque"]["go_s"]),
        (1, "RAM (processeur)", "RAM (CPU)", PLAFOND_RAM, ram),
        (2, "hôte → carte", "host → device", PLAFOND_PCIE, d["pcie"]["go_s"]),
        (3, "VRAM (shader)", "VRAM (shader)", PLAFOND_VRAM, d["vram"]["go_s"]),
    ]
    return [ecrire("machine-etages.csv", ["i", "etage_fr", "etage_en", "plafond", "mesure", "rendement"],
                   [(i, fr, en, p, m, f"{m / p:.3f}") for i, fr, en, p, m in rangs])]


def gemv_machine():
    """01-machine/carte.jsonl et carte-complement.jsonl : GEMV sur la RTX 4060 (Vulkan), meilleure
    médiane (horodatages de la carte) par configuration, témoin tenu seulement."""
    meilleurs = {}
    for src in ("carte.jsonl", "carte-complement.jsonl"):
        for x in lire_jsonl(J / "01-machine" / src):
            if x.get("op") != "gemv" or x.get("api") != "vulkan" or x.get("temoin") != "ok":
                continue
            cle = (x["format"], x["residence"], int(x["lot"]))
            meilleurs[cle] = max(meilleurs.get(cle, 0.0), float(x["go_s_carte_mediane"]))
    ordre = [(("f16", "carte", 1), "f16 VRAM", "f16 VRAM"),
             (("q4", "carte", 1), "q4 naïf VRAM", "q4 naive VRAM"),
             (("q4b", "carte", 1), "q4b VRAM", "q4b VRAM"),
             (("q4", "bar", 1), "q4 BAR", "q4 BAR"),
             (("q4", "hote", 1), "q4 RAM hôte", "q4 host RAM"),
             (("f16", "carte", 8), "f16 lot 8", "f16 batch 8"),
             (("q4", "carte", 8), "q4 lot 8", "q4 batch 8")]
    rangs = [(i, fr, en, f"{meilleurs[c]:.2f}") for i, (c, fr, en) in enumerate(ordre) if c in meilleurs]
    return [ecrire("machine-gemv.csv", ["i", "noyau_fr", "noyau_en", "go_s"], rangs)]


def toit_placements():
    """01-machine/toit-placements.csv : plafond (recouvert) et plancher (en série) pour les trois
    MoE en architecture A, r = 1, 2, 4,33."""
    with open(J / "01-machine" / "toit-placements.csv", encoding="utf-8") as f:
        lignes = list(csv.DictReader(f))
    noms = {"gpt-oss-120b MXFP4": "gpt-oss-120b", "Qwen3.8-Flash-Next UD-Q2_K_XL": "Qwen3.8-Flash-Next",
            "Kimi-K2.6 UD-Q2_K_XL": "Kimi-K2.6"}
    rangs = []
    for i, (long, court) in enumerate(noms.items()):
        sel = {round(float(l["r"]), 2): l for l in lignes if l["modele"] == long}
        rangs.append((i, court, sel[1.0]["js_recouvert"], sel[1.0]["js_serie"], sel[2.0]["js_recouvert"],
                      sel[2.0]["js_serie"], sel[4.33]["js_recouvert"], sel[4.33]["js_serie"]))
    return [ecrire("machine-toit-placements.csv",
                   ["i", "modele", "r1_rec", "r1_ser", "r2_rec", "r2_ser", "r433_rec", "r433_ser"], rangs)]


# --------------------------------------------------------------------------- 02 quantification
def gemv_quant():
    """02-quantification/csv/fig-q2-*.csv : GEMV 16 384 x 16 384, passes 3 et 4. Étiquettes
    traduites pour la version anglaise ; valeurs inchangées."""
    traduction = {"lecture seule": "read only", "scalaire 4 b": "scalar 4 b", "scalaire 2 b": "scalar 2 b",
                  "treillis (somme)": "trellis (sum)", "treillis (dot4)": "trellis (dot4)",
                  "treillis (dot4 v2)": "trellis (dot4 v2)"}
    faits = []
    for api in ("vulkan", "dx12"):
        with open(J / "02-quantification" / "csv" / f"fig-q2-{api}.csv", encoding="utf-8") as f:
            rangs = [(l["i"], l["format"], traduction[l["format"]], l["go_s"], l["ms"]) for l in csv.DictReader(f)]
        faits.append(ecrire(f"quant-gemv-{api}.csv", ["i", "format_fr", "format_en", "go_s", "ms"], rangs))
    return faits


# --------------------------------------------------------------------------- 04 chargement
def juge():
    """04-chargement/juge-stone-disque-2.4.json (étude 04) et juge-stone-disque-2.82.json (même
    outil, outils/chargement_juge.py --disque-go-s 2.82, le débit mesuré par l'étude 01) :
    succès du cache exigé pour 5 et 10 jetons/s, borne sans localité."""
    a = lire_json(J / "04-chargement" / "juge-stone-disque-2.4.json")["stone"]
    b = lire_json(SORTIE / "juge-stone-disque-2.82.json")["stone"]
    courts = {"Qwen/Qwen3-30B-A3B": "Qwen3-30B-A3B", "Qwen/Qwen3.6-35B-A3B": "Qwen3.6-35B-A3B",
              "openai/gpt-oss-120b": "gpt-oss-120b", "zai-org/GLM-4.5-Air": "GLM-4.5-Air",
              "Qwen/Qwen3-Next-80B-A3B-Instruct": "Qwen3-Next-80B", "Qwen/Qwen3.5-122B-A10B": "Qwen3.5-122B",
              "Qwen/Qwen3.8-Flash-Next": "Qwen3.8-Flash-Next", "deepseek-ai/DeepSeek-V4-Flash": "DeepSeek-V4-Flash",
              "Qwen/Qwen3.5-397B-A17B": "Qwen3.5-397B", "zai-org/GLM-5.1": "GLM-5.1"}
    rangs = []
    for i, (x, y) in enumerate(zip(a, b)):
        assert x["modele"] == y["modele"] and x["bpp"] == y["bpp"]
        nom = courts.get(x["modele"], x["modele"].split("/")[-1].replace("-Instruct-2507", ""))
        if x["modele"].startswith("Qwen/Qwen3-235B"):
            nom = f"Qwen3-235B ({x['bpp']:g} b)"
        rangs.append((i, nom, x["bpp"], f"{x['octets']['R'] / 1e9:.2f}",
                      f"{x['sans_localite']['borne_recouvrement']:.2f}", f"{y['sans_localite']['borne_recouvrement']:.2f}",
                      f"{x['h_pour_5']:.3f}", f"{y['h_pour_5']:.3f}", f"{x['h_pour_10']:.3f}", f"{y['h_pour_10']:.3f}",
                      f"{x['part_tenable']:.3f}"))
    return [ecrire("charge-juge.csv", ["i", "modele", "bpp", "R_go", "borne_24", "borne_282", "h5_24", "h5_282",
                                       "h10_24", "h10_282", "part_tenable"], rangs)]


def sensibilite_h():
    """Plafond de gpt-oss-120b en fonction du succès h du cache (modèle de coût de l'étude 06,
    outils/modeles_physique.py : t = max(A/256, h R/41,6, (1-h) R/W_disque)), avec A et R lus
    dans 01-machine/debits-mesures.json (fichier exact, en-tête GGUF) ; W_disque = plafond du lien
    (hypothèse de 06) et débit mesuré (01)."""
    d = lire_json(J / "01-machine" / "debits-mesures.json")
    m = next(x for x in d["modeles"] if x["nom"].startswith("gpt-oss-120b"))
    A, R = m["toujours_go"], m["experts_go"]
    rangs = []
    for i in range(0, 101):
        h = i / 100
        t_lien = max(A / PLAFOND_VRAM, h * R / PLAFOND_RAM, (1 - h) * R / PLAFOND_NVME)
        t_mes = max(A / PLAFOND_VRAM, h * R / PLAFOND_RAM, (1 - h) * R / d["disque"]["go_s"])
        rangs.append((f"{h:.2f}", f"{1 / t_lien:.3f}", f"{1 / t_mes:.3f}"))
    return [ecrire("charge-sensibilite-h.csv", ["h", "jps_lien", "jps_mesure"], rangs)]


def localite():
    """04-chargement/localite-temoins.json, témoin T3 (routage collant rho = 0,6, E = 128,
    k = 8) : succès LRU, LFU, statique calibré et Belady par budget C."""
    t3 = lire_json(J / "04-chargement" / "localite-temoins.json")["rapport"]["T3_caches"]
    rangs = [(c, f"{v['lru']:.4f}", f"{v['lfu']:.4f}", f"{v['statique_calibre']:.4f}", f"{v['belady']:.4f}")
             for c, v in sorted(t3.items(), key=lambda kv: int(kv[0]))]
    return [ecrire("charge-localite-collant.csv", ["C", "lru", "lfu", "statique", "belady"], rangs)]


# --------------------------------------------------------------------------- 05 sparsité
def amortissement():
    """05-sparsite/amortissement-tables.json : E(alpha, k) par la formule, k de 1 à 32."""
    t = lire_json(J / "05-sparsite" / "amortissement-tables.json")["E_chaine"]
    faits = []
    for a, ligne in t.items():
        rangs = [(k, f"{v:.4f}") for k, v in ligne.items() if k != "inf"]
        faits.append(ecrire(f"sparse-E-{int(round(float(a) * 100))}.csv", ["k", "E"], rangs))
    return faits


def unions():
    """05-sparsite/stats-smol.json : union des masques top-k de n jetons consécutifs, entrée de
    down (SmolLM2-135M), et la même union si les masques étaient indépendants."""
    e = lire_json(J / "05-sparsite" / "stats-smol.json")["entrees"]["down_in"]
    faits = []
    for s, v in e.items():
        pct = int(round(float(s) * 100))
        faits.append(ecrire(f"sparse-union-s{pct}.csv", ["n", "union", "independant"],
                            [(n, f"{u:.4f}", f"{v['union_si_independant'][n]:.4f}") for n, u in v["union"].items()]))
    return faits


def courbe_cn():
    """05-sparsite/cn/resume-4B-ngl99.txt : temps d'une passe de n jetons, Qwen3.5-4B Q4_K_M,
    médiane et étendue des quatre séries ABBA (indicatif : seuil de bruit non atteint)."""
    rangs = []
    for l in (J / "05-sparsite" / "cn" / "resume-4B-ngl99.txt").read_text(encoding="utf-8").splitlines()[1:]:
        m = re.match(r"\s*(\d+)\s+([\d.]+)\s+([\d.]+).*\[([^\]]+)\]", l)
        if not m:
            continue
        series = [float(x) for x in m.group(4).split(",")]
        med = float(m.group(2))
        rangs.append((m.group(1), f"{med:.1f}", f"{med - min(series):.1f}", f"{max(series) - med:.1f}", m.group(3)))
    return [ecrire("sparse-cn.csv", ["n", "ms", "moins", "plus", "rapport"], rangs)]


# --------------------------------------------------------------------------- 06 modèles
def moe():
    """06-modeles/octets-par-jeton.json : paramètres totaux (texte) et actifs par jeton des 49
    modèles inventoriés dans leurs en-têtes ; MoE seulement (experts routés non nuls)."""
    # Étiquettes affichées sur la figure (les autres points restent anonymes, pour la lisibilité).
    nommes = {"gpt-oss-20b": "gpt-oss-20b", "gpt-oss-120b": "gpt-oss-120b",
              "Qwen3-Next-80B-A3B-Instruct": "Qwen3-Next-80B", "Qwen3.8-Flash-Next": "Qwen3.8-Flash-Next",
              "DeepSeek-V4-Flash-0731": "DeepSeek-V4-Flash", "Kimi-K2.6": "Kimi-K2.6", "Kimi-K3": "Kimi-K3",
              "Qwen3.8-2.4T-A95B": "Qwen3.8-2.4T", "Mixtral-8x7B-Instruct-v0.1": "Mixtral-8x7B",
              "Llama-4-Maverick-17B-128E-Instruct": "Llama-4-Maverick", "Qwen3-235B-A22B-Instruct-2507": "Qwen3-235B",
              "LongCat-Flash-Lite": "LongCat-Flash-Lite", "DeepSeek-V4.1-Flash": "DeepSeek-V4.1-Flash"}
    rangs = []
    for x in lire_json(J / "06-modeles" / "octets-par-jeton.json"):
        if x.get("experts_G", 0) <= 0:
            continue
        nom = x["depot"].split("/")[-1]
        rangs.append((nom, f"{x['total_texte_G']:.2f}", f"{x['actifs_G']:.2f}",
                      f"{x['actifs_G'] / x['total_texte_G']:.4f}", nommes.get(nom, "")))
    rangs.sort(key=lambda r: float(r[1]))
    return [ecrire("modeles-moe.csv", ["modele", "total_g", "actifs_g", "part_active", "etiquette"], rangs)]


# --------------------------------------------------------------------------- 07 synthèse, décisions, mesures
DEC = DEPOT / "decisions" / "journaux"
MES = DEPOT / "mesures"

# Point publié qui cale β (fondations/04-chargement.md, Qwen3-30B-A3B, une couche) : budget de 13,4 %
# des octets d'experts. Les succès (LRU 65,9 %, Belady 79,1 %) ne sont pas réécrits : ils se
# retrouvent par h = 0,134^β avec les β de plafonds.json.
BUDGET_CALAGE = 0.134


def localite_hypotheses():
    """07-synthese/plafonds.json, « betas » : h(c) = c^β pour les trois scénarios (uniforme, LRU calé,
    Belady calé), c de 0,005 à 1. Second fichier : le point de calage de chaque β."""
    b = lire_json(J / "07-synthese" / "plafonds.json")["betas"]
    cs = [0.005 * i for i in range(1, 201)]
    courbes = ecrire("form-localite.csv", ["c", "uniforme", "lru", "belady"],
                     [(f"{c:.3f}", f"{c ** b['uniforme']:.5f}", f"{c ** b['lru_cale']:.5f}",
                       f"{c ** b['belady_cale']:.5f}") for c in cs])
    points = ecrire("form-localite-calage.csv", ["c", "h", "politique"],
                    [(BUDGET_CALAGE, f"{BUDGET_CALAGE ** b['lru_cale']:.4f}", "LRU"),
                     (BUDGET_CALAGE, f"{BUDGET_CALAGE ** b['belady_cale']:.4f}", "Belady")])
    return [courbes, points]


def localite_mesuree_20b():
    """mesures/localite-gpt-oss/20b/courbes-gpt-oss-20b.csv (agent de mesure, étude non rendue au
    moment où ce mémoire est construit) : succès simulé sur les traces de routage de gpt-oss-20b,
    trace « tous.generation », LRU et Belady, cache par couche et cache global, selon le budget
    (part des octets d'experts). « nan » là où la simulation n'a pas de point (cache par couche
    sous un expert par couche)."""
    with open(MES / "localite-gpt-oss" / "20b" / "courbes-gpt-oss-20b.csv", encoding="utf-8") as f:
        lignes = [l for l in csv.DictReader(f) if l["trace"] == "tous.generation"]
    budgets = sorted({int(l["budget_pct"]) for l in lignes})
    def val(bud, portee, pol):
        for l in lignes:
            if int(l["budget_pct"]) == bud and l["portee"] == portee and l["politique"] == pol:
                return l["succes"]
        return "nan"
    return [ecrire("archi-localite-20b.csv",
                   ["c", "lru_couche", "belady_couche", "lru_globale", "belady_globale"],
                   [(f"{b / 100:.2f}", val(b, "couche", "lru"), val(b, "couche", "belady"),
                     val(b, "globale", "lru"), val(b, "globale", "belady")) for b in budgets])]


def architectures():
    """07-synthese/csv/architectures-gptoss120b.csv (base estimée, A, A0, B1 sans compléments, B2)
    et decisions/journaux/csv/b-complements-gptoss120b.csv (B1 complété et B3 à λ = 0 : la
    correction du partisan de B, refaite par l'arbitre). Plafond par scénario de localité et
    plancher en série du scénario LRU calé, en jetons/s."""
    with open(J / "07-synthese" / "csv" / "architectures-gptoss120b.csv", encoding="utf-8") as f:
        a07 = list(csv.DictReader(f))
    with open(DEC / "csv" / "b-complements-gptoss120b.csv", encoding="utf-8") as f:
        adec = list(csv.DictReader(f))
    def ligne(table, cle, nom, scen):
        for l in table:
            if l["scenario"] == scen and l[cle] == nom:
                return l
        raise KeyError((nom, scen))
    choix = [  # (table, colonne, nom dans le journal, étiquette fr, étiquette en)
        (a07, "architecture", "base_llamacpp_4k", "base llama.cpp : fautes de 4 Kio (estimée)", "llama.cpp baseline: 4 KiB faults (est.)"),
        (a07, "architecture", "base_llamacpp_1m", "base llama.cpp : lectures de 1 Mio (estimée)", "llama.cpp baseline: 1 MiB reads (est.)"),
        (a07, "architecture", "A0_sans_ram", "A0 (sans cache en RAM)", "A0 (no RAM cache)"),
        (a07, "architecture", "A_sans_perte", "A (sans perte)", "A (lossless)"),
        (adec, "variante", "B1_complete_lambda_0.0", "B1 (compléments comptés)", "B1 (complements counted)"),
        (a07, "architecture", "B1_base2b_aux_defauts", "B1 sans compléments (barré)", "B1 without complements (struck)"),
        (adec, "variante", "B3_lambda_0.0", "B3 (λ = 0 : bases en RAM)", "B3 (λ = 0: bases in RAM)"),
    ]
    # Aucune virgule dans les étiquettes : pgfplots ne lit pas les champs CSV entre guillemets.
    assert not any("," in fr or "," in en for _, _, _, fr, en in choix)
    rangs = []
    for i, (t, cle, nom, fr, en) in enumerate(choix):
        u, l, b = (float(ligne(t, cle, nom, s)["jetons_s_plafond"]) for s in ("uniforme", "lru_cale", "belady_cale"))
        serie = float(ligne(t, cle, nom, "lru_cale")["jetons_s_serie"])
        rangs.append((i, fr, en, f"{u:.3f}", f"{l:.3f}", f"{b:.3f}", f"{serie:.3f}"))
    return [ecrire("archi-plafonds.csv", ["i", "archi_fr", "archi_en", "uniforme", "lru", "belady", "serie_lru"],
                   rangs)]


def base_20b():
    """mesures/base-gpt-oss/20b/resume.csv (agent de mesure, séries ABBA sur secteur) : génération et
    préremplissage de llama.cpp b11515 sur gpt-oss-20b, trois configurations, moyenne, min, max."""
    noms = {"cmoe": ("experts sur le processeur", "experts on the CPU"),
            "fit": ("placement ajusté (fit)", "fitted placement (fit)"),
            "cache": ("cache d'experts de 4 096 Mio", "expert cache of 4096 MiB")}
    with open(MES / "base-gpt-oss" / "20b" / "resume.csv", encoding="utf-8") as f:
        lignes = list(csv.DictReader(f))
    rangs = []
    for i, cfg in enumerate(noms):
        for l in lignes:
            if l["config"] == cfg and l["grandeur"] == "generation_js":
                m, a, b = float(l["moyenne"]), float(l["min"]), float(l["max"])
                rangs.append((i, noms[cfg][0], noms[cfg][1], l["n"], f"{m:.3f}", f"{m - a:.3f}", f"{b - m:.3f}"))
    return [ecrire("archi-base-20b.csv", ["i", "config_fr", "config_en", "n", "generation_js", "moins", "plus"],
                   rangs)]


def f1_decoupe():
    """decisions/journaux/arbitre/decoupe-gptoss20b.json (mesure F1 de l'arbitre, passe 2, 12 tenseurs
    de gpt-oss-20b, codeur rANS réel, décodage exact ; les variantes communes aux deux passes rendent
    les mêmes octets) : bits par poids de chaque variante du format, en trois parts empilées (codes ou
    base, complément, métadonnées : écarts d'échelle, médianes, tables). B_riche : complément à
    contexte riche, ajouté avant la passe 2."""
    j = lire_json(DEC / "arbitre" / "decoupe-gptoss20b.json")
    b, riche = j["bpp"], j["b_riche"]
    meta_a = b["delta"] + b["medianes"] + b["tables_a"]
    meta_b = b["delta"] + b["medianes"] + b["tables_b"]
    rangs = [
        (0, "A : trois flux de classe", "A: three class streams", b["codes_a_flux"], 0.0, meta_a, b["a_flux"]),
        (1, "A : table par voie", "A: table per lane", b["codes_a_ctx"], 0.0, meta_a, b["a_ctx"]),
        (2, "B : complément selon classe et échelle", "B: complement by class and scale", b["base_seule"],
         b["niveau1_compl_cond"], meta_b, b["b_cond"]),
        (3, "B : complément selon la classe seule", "B: complement by class only", b["base_seule"],
         b["compl_mag"], meta_b, b["b_mag"]),
        (4, "B : complément à contexte riche (retenu)", "B: rich-context complement (kept)", b["base_seule"],
         riche["bpp_compl"], b["delta"] + b["medianes"] + riche["bpp_tables"], riche["bpp_total"]),
    ]
    return [ecrire("archi-f1.csv", ["i", "variante_fr", "variante_en", "codes", "complement", "meta", "total"],
                   [(i, fr, en, f"{c:.6f}", f"{k:.6f}", f"{m:.6f}", f"{t:.6f}") for i, fr, en, c, k, m, t in rangs])]


# --------------------------------------------------------------------------- 03 entropie
CSV03 = J / "03-entropie" / "csv"


def _mediane(v):
    v = sorted(v)
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def entropie_debits():
    """03-entropie/csv/debits-carte-series.csv et debits-cuda-series.csv (régénérés par
    outils/03-entropie/vers_csv.py depuis rans-4B-calme.json, rans-4B-B{1,2}-secteur.json,
    rans-gptoss20b-secteur.json, cuda-4B-A{1,2}-secteur.json) : débit écrit de chaque décodeur,
    médiane de toutes les mesures de la série, barres de la plus lente à la plus rapide. Les
    séries B1 et B2 (Vulkan, secteur) et A1 et A2 (CUDA, secteur) sont mises en commun."""
    with open(CSV03 / "debits-carte-series.csv", encoding="utf-8") as f:
        vk = list(csv.DictReader(f))
    with open(CSV03 / "debits-cuda-series.csv", encoding="utf-8") as f:
        cu = list(csv.DictReader(f))
    noms = {"decoder_v1": "v1", "decoder": "v2", "decoder_v3": "v3", "decoder_v4": "v4",
            "recopie": "recopie", "recopie_vec4": "recopie4", "decoder_v4_cuda": "v4",
            "recopie_cuda": "recopie"}
    series = {
        "batterie": (vk, {"rans-4B-calme.json"}),
        "secteur": (vk, {"rans-4B-B1-secteur.json", "rans-4B-B2-secteur.json"}),
        "mxfp4": (vk, {"rans-gptoss20b-secteur.json"}),
        "cuda": (cu, {"cuda-4B-A1-secteur.json", "cuda-4B-A2-secteur.json"}),
    }
    faits = []
    for cle, (lignes, journaux) in series.items():
        par = {}
        for l in lignes:
            if l["journal"] in journaux:
                par.setdefault(noms[l["variante"]], []).append(float(l["go_s"]))
        rangs = []
        for v in ("v1", "v2", "v3", "v4", "recopie", "recopie4"):
            if v in par:
                m = _mediane(par[v])
                rangs.append((v, f"{m:.3f}", f"{m - min(par[v]):.3f}", f"{max(par[v]) - m:.3f}", len(par[v])))
        faits.append(ecrire(f"entropie-debits-{cle}.csv", ["variante", "go_s", "moins", "plus", "n"], rangs))
    return faits


def entropie_gemv():
    """03-entropie/csv/gemv-series.csv et gemv.csv (depuis gemv-gptoss20b-{calme,secteur}.json) :
    produit matrice-vecteur MXFP4 de gpt-oss-20b, quatre chemins, en Go/s de poids MXFP4
    équivalents. Le volume équivalent d'un passage est le même pour les quatre chemins ; il se
    déduit de la ligne résumée (débit médian × temps médian) et convertit chaque temps de la série."""
    with open(CSV03 / "gemv.csv", encoding="utf-8") as f:
        res = list(csv.DictReader(f))
    with open(CSV03 / "gemv-series.csv", encoding="utf-8") as f:
        ser = list(csv.DictReader(f))
    ordre = [("brut", "brut", "raw"), ("fusionne", "fondu", "fused"), ("decodage_v4", "décodage seul", "decode only"),
             ("deux_passes", "deux passes", "two passes")]
    faits = []
    for journal, cle in (("gemv-gptoss20b-secteur.json", "secteur"), ("gemv-gptoss20b-calme.json", "batterie")):
        octets = {l["chemin"]: float(l["go_s_poids_equivalents"]) * float(l["temps_median_s"])
                  for l in res if l["journal"] == journal}
        rangs = []
        for i, (ch, fr, en) in enumerate(ordre):
            v = [octets[ch] / float(l["temps_s"]) for l in ser if l["journal"] == journal and l["chemin"] == ch]
            m = _mediane(v)
            rangs.append((i, fr, en, f"{m:.3f}", f"{m - min(v):.3f}", f"{max(v) - m:.3f}", len(v)))
        faits.append(ecrire(f"entropie-gemv-{cle}.csv", ["i", "chemin_fr", "chemin_en", "go_s", "moins", "plus", "n"],
                            rangs))
    return faits


def entropie_taux():
    """03-entropie/taux-mxfp4-classes-gptoss{20b,120b}.json : taux sans perte réel de chaque tenseur
    d'experts, une table par tenseur (champ taux) et trois classes d'échelle
    (octets_stockes / (octets_codes_par_classe + octets_echelles)), décodage exact vérifié."""
    faits = []
    for mod in ("20b", "120b"):
        j = lire_json(J / "03-entropie" / f"taux-mxfp4-classes-gptoss{mod}.json")
        par_role = {}
        for i, t in enumerate(j["tenseurs"]):
            m = re.match(r"blk\.(\d+)\.ffn_(\w+)_exps", t["nom"])
            couche, role = int(m.group(1)), m.group(2)
            t3 = t["octets_stockes"] / (t["octets_codes_par_classe"] + t["octets_echelles"])
            par_role.setdefault(role, []).append((couche, f"{t['taux']:.5f}", f"{t3:.5f}", t["exact"]))
        for role, rangs in par_role.items():
            faits.append(ecrire(f"entropie-taux-{mod}-{role}.csv", ["couche", "taux1", "taux3", "exact"], rangs))
    return faits


def entropie_echelles():
    """03-entropie/csv/mxfp4-echelles-contexte-gptoss120b.csv et fig-echelles-gptoss20b.csv
    (vers_csv.py, depuis mxfp4-contexte-gptoss{20b,120b}.json) : entropie des échelles E8M0 de chaque
    tenseur, à l'ordre 0, sachant le bloc de gauche, sachant la médiane de la ligne (coût de la médiane
    compris pour le 120b ; il vaut 0,015 bit en moyenne sur le 20b)."""
    faits = []
    with open(CSV03 / "fig-echelles-gptoss20b.csv", encoding="utf-8") as f:
        l20 = list(csv.DictReader(f))
    faits.append(ecrire("entropie-echelles-20b.csv", ["i", "H0", "gauche", "mediane"],
                        [(l["indice"], l["H_e"], l["H_e_gauche"], l["H_e_mediane"]) for l in l20]))
    with open(CSV03 / "mxfp4-echelles-contexte-gptoss120b.csv", encoding="utf-8") as f:
        l120 = list(csv.DictReader(f))
    faits.append(ecrire("entropie-echelles-120b.csv", ["i", "H0", "gauche", "mediane"],
                        [(i, l["H_e"], l["H_e_gauche"],
                          f"{float(l['H_e_mediane_ligne']) + float(l['H_mediane_par_bloc']):.6f}")
                         for i, l in enumerate(l120)]))
    return faits


if __name__ == "__main__":
    faits = []
    for f in (disque, aes, ram_latence, thermique, pcie_generation, etages, gemv_machine, toit_placements,
              gemv_quant, juge, sensibilite_h, localite, amortissement, unions, courbe_cn, moe,
              localite_hypotheses, localite_mesuree_20b, architectures, base_20b, f1_decoupe,
              entropie_debits, entropie_gemv, entropie_taux, entropie_echelles):
        faits += f()
    print(f"{len(faits)} fichiers écrits sous {SORTIE.relative_to(DEPOT)}")
