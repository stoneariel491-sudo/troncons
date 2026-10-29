"""Données des figures des chapitres « Le chemin des octets » et « Les noyaux sur la carte » (Tome II).

Lit les CSV et journaux commités des lots E, K et O et écrit, sous memoire/figures/tome2/donnees/,
des tables numériques prêtes pour pgfplots (une colonne par série, aucune chaîne à filtrer). Rien
n'est mesuré ici : chaque valeur est recopiée ou réordonnée depuis le fichier source nommé.
Bibliothèque standard seule. Usage : python -I -X utf8 memoire/outils/tome2_chemin_noyaux.py
"""

import subprocess
import csv
import json
import statistics
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
E = RACINE / "mesures" / "moteur" / "E"
K = RACINE / "mesures" / "moteur" / "K"
O = RACINE / "mesures" / "moteur" / "O"
SORTIE = RACINE / "memoire" / "figures" / "tome2" / "donnees"


def lire(chemin):
    with open(chemin, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def ecrire(nom, entetes, lignes):
    SORTIE.mkdir(parents=True, exist_ok=True)
    with open(SORTIE / nom, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(entetes)
        for l in lignes:
            w.writerow([("%.6g" % v) if isinstance(v, float) else v for v in l])


def vrai(s):
    return 1 if str(s).strip().lower() == "true" else 0


# --- Chapitre « chemin » ---------------------------------------------------------------------

def sync():
    """E0 (c) : coût d'une synchronisation (µs) par variante, à vide et sous charge."""
    d = json.loads((E / "journaux" / "2026-10-15-seance3" / "resume.json").read_text(encoding="utf-8"))["verdicts"]
    ordre = ["evenement", "sondage", "boite", "boite_sans_vidage", "bloquant"]
    lignes = []
    for i, v in enumerate(ordre):
        lignes.append([i, d["c-vide"]["variantes"][v]["cout_us_par_synchro"],
                       d["c-charge"]["variantes"][v]["cout_us_par_synchro"],
                       d["c-vide"]["variantes"][v]["bruit_miroir"] * d["c-vide"]["variantes"][v]["cout_us_par_synchro"],
                       d["c-charge"]["variantes"][v]["bruit_miroir"] * d["c-charge"]["variantes"][v]["cout_us_par_synchro"]])
    ecrire("t2c-sync.csv", ["i", "vide_us", "charge_us", "err_vide", "err_charge"], lignes)


def dma():
    """E0 (b) : débit de chaque copie DMA, 12 Mio et 64 Mio, dans l'ordre de la série ABBA."""
    r = lire(E / "csv" / "2026-10-15-seance3-b-dma.csv")
    p12 = [float(l["go_s"]) for l in r if l["octets"] == "12582912"]
    p64 = [float(l["go_s"]) for l in r if l["octets"] == "67108864"]
    ecrire("t2c-dma.csv", ["k", "go12", "go64"], [[k, a, b] for k, (a, b) in enumerate(zip(p12, p64))])


def e1():
    """E1 : chaque passe du lecteur (séances 1 et 3), et le second chemin de Little."""
    little = []
    for s, nom in [(1, "e1-2026-10-15-seance1-lecteur-passes.csv"), (3, "e1-2026-10-15-seance3-lecteur-passes.csv")]:
        r = lire(E / "csv" / nom)
        lignes = []
        for k, l in enumerate(r):
            lignes.append([k, int(l["profondeur"]), float(l["go_s"]), vrai(l["propre"]), float(l["go_s_etrangers"]),
                           float(l["go_s_little"])])
            little.append([float(l["go_s"]), float(l["go_s_little"]), s, int(l["profondeur"])])
        ecrire(f"t2c-e1-s{s}.csv", ["k", "qd", "go_s", "propre", "etrangers", "little"], lignes)
    for l in lire(E / "csv" / "2026-10-15-seance3-b-disque.csv"):
        little.append([float(l["go_s"]), float(l["go_s_little"]), 2, int(l["profondeur"])])
    ecrire("t2c-little.csv", ["mur", "little", "groupe", "qd"], little)


def e2():
    """E2 : passes A (production) et B (disque seul), lecture de longueur0 (N) et de 12 Mio (V)."""
    for lettre, nom in [("n", "e2-2026-10-15-seance1-passes.csv"), ("v", "e2-2026-10-15-v12-passes.csv")]:
        r = lire(E / "csv" / nom)
        ecrire(f"t2c-e2-{lettre}.csv", ["k", "a", "servis", "troncons", "lecture_ms"],
               [[k, 1 if l["lettre"] == "A" else 0, float(l["go_s_servis"]), float(l["go_s_troncons"]),
                 float(l["lecture_us_mediane"]) / 1000.0] for k, l in enumerate(r)])
    r = lire(E / "csv" / "e2-nvvn-2026-10-15-nvvn.csv")
    ecrire("t2c-nvvn.csv", ["k", "v", "servis"],
           [[k, 1 if l["lettre"] == "V" else 0, float(l["go_s_servis"])] for k, l in enumerate(r)])
    # Les trois étages, en Go/s de tronçons : disque seul (médiane des passes B), DMA, décodage.
    lignes = []
    for lettre, passes, etages in [("n", "e2-2026-10-15-seance1-passes.csv", "e2-2026-10-15-seance1-etages.csv"),
                                   ("v", "e2-2026-10-15-v12-passes.csv", "e2-2026-10-15-v12-etages.csv")]:
        b = statistics.median(float(l["go_s_troncons"]) for l in lire(E / "csv" / passes) if l["lettre"] == "B")
        a = statistics.median(float(l["go_s_troncons"]) for l in lire(E / "csv" / passes) if l["lettre"] == "A")
        et = lire(E / "csv" / etages)
        dmav = statistics.mean(float(l["dma_go_s"]) for l in et)
        dec = statistics.mean(float(l["decodage_go_s"]) for l in et)
        lignes.append([lettre, a, b, dmav, dec])
    ecrire("t2c-etages.csv", ["lecture", "a", "disque", "dma", "decodage"], [[0 if l[0] == "n" else 1] + l[1:] for l in lignes])


def l12():
    """L12 dans le moteur (lot O, séance 2026-10-16-s2, série A B B A) : génération et préremplissage."""
    r = lire(O / "csv" / "o-jetons-s.csv")
    noms = ["2026-10-16-s2-15-l12-A", "2026-10-16-s2-16-l12-B", "2026-10-16-s2-17-l12-B", "2026-10-16-s2-18-l12-A"]
    lignes = []
    for k, n in enumerate(noms):
        l = next(x for x in r if x["passe"] == n)
        lignes.append([k, 1 if n.endswith("B") else 0, float(l["generation_jetons_s"]), float(l["prefill_jetons_s"])])
    ecrire("t2c-l12.csv", ["k", "b", "generation", "preremplissage"], lignes)


def couche():
    """Le chronogramme du moteur (lot O, --chronogramme, 120b) : pas 8, couches 0 et 1, une ligne
    par défaut, numérotée dans l'ordre de soumission (y = 0, 1, … de haut en bas)."""
    r = [l for l in lire(O / "csv" / "chronogramme-120b.csv") if l["pas"] == "8" and l["couche"] in ("0", "1")]
    r.sort(key=lambda l: float(l["soumis_ms"]))
    champs = ["soumis_ms", "lu_ms", "copie_debut_ms", "copie_fin_ms", "dec_debut_ms", "dec_fin_ms", "routeur_ms",
              "fin_couche_ms"]
    ecrire("t2c-couche.csv", ["y", "couche", "expert"] + [c[:-3] for c in champs],
           [[y, int(l["couche"]), int(l["expert"])] + [float(l[c]) for c in champs] for y, l in enumerate(r)])


# --- Chapitre « noyaux » ---------------------------------------------------------------------

def k1():
    """K1 : débit du décodeur (Go/s de codes) par passe. Codes : 0 A, 1 B (copie brute), 2 C (lot de
    4), 3 D (DELTA en tuiles de 32), 4 D + lot. Dans les journaux D*, la variante « A » est D et « C »
    est D + lot."""
    r = lire(K / "csv" / "k1-debit-passes.csv")
    lignes = []
    vus = {}
    for l in r:
        proc = l["journal"].split("-")[2]  # A1, A2, D1, D2
        v = l["variante"]
        if proc.startswith("D"):
            code = {"A": 3, "B": 1, "C": 4}[v]
        else:
            code = {"A": 0, "B": 1, "C": 2}[v]
        cle = (code, proc)
        vus[cle] = vus.get(cle, -1) + 1
        lignes.append([code * 10 + int(proc[1]), code, int(proc[1]), vus[cle], float(l["go_s_codes"])])
    ecrire("t2n-k1.csv", ["serie", "code", "proc", "passe", "go_s"], lignes)
    # Médianes et pires passes par variante (tableau du chapitre).
    resume = []
    for code in range(5):
        for p in (1, 2):
            v = [x[4] for x in lignes if x[1] == code and x[2] == p]
            if v:
                resume.append([code, p, statistics.median(v), min(v), len(v)])
    ecrire("t2n-k1-resume.csv", ["code", "proc", "mediane", "pire", "passes"], resume)


def k2():
    r = lire(K / "csv" / "k2-debit-passes.csv")
    lignes = []
    vus = {}
    for l in r:
        proc = int(l["journal"].split("-")[2])
        code = 0 if l["variante"] == "A" else 1
        vus[(code, proc)] = vus.get((code, proc), -1) + 1
        lignes.append([code * 10 + proc, code, proc, vus[(code, proc)], float(l["go_s_equiv"])])
    ecrire("t2n-k2.csv", ["serie", "code", "proc", "passe", "go_s"], lignes)


def marges():
    """K3 : marge de chaque noyau à seuil (seuil / pire écart), 20b et 120b."""
    r = [l for l in lire(K / "csv" / "k3-par-noyau.csv") if l["essai"] == "temoin" and l["marge"]]
    noms = []
    for l in r:
        if l["noyau"] not in noms:
            noms.append(l["noyau"])
    lignes = []
    for i, n in enumerate(noms):
        m20 = next(float(l["marge"]) for l in r if l["noyau"] == n and l["modele"] == "gpt-oss-20b")
        m120 = next(float(l["marge"]) for l in r if l["noyau"] == n and l["modele"] == "gpt-oss-120b")
        lignes.append([i, m20, m120])
    ecrire("t2n-marges.csv", ["i", "m20", "m120"], lignes)
    print("ordre des noyaux à seuil :", ", ".join(noms))


def routage():
    """K3, D1 : marge de la référence à chaque décision de routage, et bascule (ensemble différent)."""
    r = lire(K / "k3" / "k3-chaine-d1-gptoss20b-marges.csv")
    ecrire("t2n-routage.csv", ["position", "couche", "marge", "bascule"],
           [[int(l["position"]), int(l["couche"]), max(float(l["marge_reference"]), 1e-9),
             int(l["ensemble_different"])] for l in r])


def kv():
    """Ronde M5 : KL par position, cache KV f16 contre f32, fenêtre 0 du 120b."""
    r = [l for l in lire(O / "corrections" / "csv" / "kv-f16-f32-par-position.csv") if l["cas"] == "f0-120b"]
    lignes, s16, s32 = [], 0.0, 0.0
    for n, l in enumerate(r, 1):
        a, b = float(l["kl_f16"]), float(l["kl_f32"])
        s16 += a
        s32 += b
        # KL par position, et moyenne courante depuis la première position notée.
        lignes.append([int(l["position"]), a, b, s16 / n, s32 / n])
    ecrire("t2n-kv-120b.csv", ["position", "kl_f16", "kl_f32", "moy_f16", "moy_f32"], lignes)


# --- Extraits de code des listings ---------------------------------------------------------------
# (commit, fichier source, première ligne, dernière ligne, marqueur que la première ligne doit
#  contenir, nom de l'extrait). Chaque extrait se lit au commit que sa légende cite dans le chapitre
# (« lignes a à b, commit c »), et non dans l'arbre de travail : le moteur continue d'évoluer
# (passe.cuh : routeur biaisé de P3, eb78770 ; gemv.cuh : gemv_base du lot B, 0be464a), le listing
# reste celui que le texte décrit. Le marqueur fait encore tomber le script si le couple commit et
# lignes ne désigne plus le même code : l'extrait est alors à recaler, jamais à recopier de mémoire.
# Changé le 2026-10-29 : avant, la lecture se faisait dans l'arbre de travail et la chaîne tombait
# sur passe.cuh:527 depuis eb78770.
EXTRAITS = [
    ("014bd11", "moteur/crates/trc-es/src/lib.rs", 170, 263, "Soumet une lecture", "trc-es-lecteur.rs"),
    ("014bd11", "moteur/crates/trc-cuda/src/api.rs", 60, 76, "unsafe fn charger", "trc-cuda-charger.rs"),
    ("94ac4c4", "moteur/bins/banc-chemin/noyaux/essais.cu", 45, 64, "Le routeur simulé", "essais-routeur.cu"),
    ("1cca7f3", "moteur/bins/banc-chemin/src/disque.rs", 46, 63, "Octets lus sur le disque", "disque-cumul.rs"),
    ("82a84e3", "moteur/crates/trc-noyaux/noyaux/commun.cuh", 197, 227, "pas_octet(EtatVoie", "pas-octet.cuh"),
    ("a64740c", "moteur/crates/trc-noyaux/noyaux/decodeur.cuh", 172, 206, "for (uint32_t t = warp", "corps-codes.cuh"),
    ("4473050", "moteur/crates/trc-noyaux/noyaux/gemv.cuh", 25, 55, "2^(e − 128) en f32", "gemv-bloc.cuh"),
    ("c09551e", "moteur/crates/trc-noyaux/noyaux/passe.cuh", 527, 542, "résidu[i] +=", "combiner.cuh"),
    ("c09551e", "moteur/crates/trc-noyaux/noyaux/passe.cuh", 145, 167, "inv_freq de la paire i", "rope-yarn.cuh"),
    ("c09551e", "moteur/crates/trc-noyaux/noyaux/passe.cuh", 325, 371, "// 1. scores", "attention.cuh"),
    ("c09551e", "moteur/crates/trc-noyaux/noyaux/passe.cuh", 461, 514, "float v[8];", "routeur-topk.cuh"),
]


def source_au_commit(commit, source):
    # Le fichier tel qu'il est dans le commit, fins de ligne normalisées (core.autocrlf peut rendre
    # l'arbre de travail en CRLF ; git show rend l'objet commité).
    r = subprocess.run(["git", "-C", str(RACINE), "show", f"{commit}:{source}"], capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"{commit}:{source} introuvable : " + r.stderr.decode("utf-8", "replace").strip())
    return r.stdout.decode("utf-8").replace("\r\n", "\n")


def extraits():
    dest = RACINE / "memoire" / "listings" / "tome2"
    dest.mkdir(parents=True, exist_ok=True)
    for commit, source, debut, fin, marqueur, nom in EXTRAITS:
        lignes = source_au_commit(commit, source).splitlines()
        if marqueur not in lignes[debut - 1]:
            raise SystemExit(f"{commit}:{source}:{debut} ne contient pas « {marqueur} » : extrait {nom} à recaler")
        texte = "\n".join(lignes[debut - 1:fin]) + "\n"
        # Six caractères des commentaires que la police à chasse fixe du mémoire n'a pas : rendus en
        # ASCII (le code lui-même n'en contient aucun ; le chapitre le dit).
        for a, b in (("⌊", "floor("), ("⌋", ")"), ("⌈", "ceil("), ("⌉", ")"), ("Σ", "sum"), ("ᵀ", "^T")):
            texte = texte.replace(a, b)
        (dest / nom).write_text(texte, encoding="utf-8")


if __name__ == "__main__":
    extraits()
    sync()
    dma()
    e1()
    e2()
    l12()
    couche()
    k1()
    k2()
    marges()
    routage()
    kv()
    print("écrit :", ", ".join(sorted(p.name for p in SORTIE.glob("t2*.csv"))))
