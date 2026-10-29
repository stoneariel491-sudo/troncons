"""Juge des chiffres du second flux, lot « construction » : refait chaque nombre NEUF ou DÉPLACÉ des trois
fichiers *-nombres.tex (codon, synonyme, juge) depuis les fichiers commités sous mesures/, par un code écrit
ici, sans appeler les scripts du lot (memoire/outils/tome3_*.py) ni lire leurs CSV dérivés.

Là où un second fichier existe, il est pris de préférence à celui que lit le lot :
  - l'axe sans perte : taux-reel-colonne-12-gptoss20b.json (le codec réel), pas colonne-par-tenseur.csv ;
  - les parts de la roue : l'histogramme des 72 tenseurs, recoupé par zero-compte-20b.json ;
  - la voie « référence substituée » sur R1 : les fichiers par position du lot B, pas kl-par-fenetre.csv ;
  - les centiles et les médianes : les positions, pas les résumés JSON.
Conventions : médiane et centile de numpy (interpolation linéaire) ; σ par fenêtres = écart-type (ddof = 1)
des dix moyennes de fenêtre divisé par √10. Comparaison : la valeur du juge écrite avec autant de décimales
que la chaîne du lot ; une valeur à moins de 1e-6 relatif d'une demi-unité du dernier chiffre est signalée
« frontière d'arrondi » (les deux arrondis sont alors défendables).

Témoin : chaque bloc a une valeur connue d'avance (une somme, un compte, un total d'un autre fichier).
Cassure (--casser) : les KL de la frontière sur R1 multipliées par 1,01 ; des nombres doivent tomber.

    python -I -X utf8 refaire.py [--casser] [--sortie journaux/refaire.csv]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import pathlib
import re
import sys

import numpy as np

RACINE = pathlib.Path(__file__).resolve().parents[4]
MES = RACINE / "mesures"
CO = MES / "genome/construction"
DON = RACINE / "memoire/figures/tome3/donnees"
CASSER = False


def lc(p: pathlib.Path) -> list[dict]:
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def lj(p: pathlib.Path):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def nombres_du_lot() -> dict[str, str]:
    d = {}
    for nom in ("codon", "synonyme", "juge"):
        for m in re.finditer(r"\\def\\(\w+)\{([^}]*)\}", (DON / f"{nom}-nombres.tex").read_text(encoding="utf-8")):
            d[m.group(1)] = m.group(2)
    return d


def kl_positions(p: pathlib.Path, colonne: str = "kl") -> np.ndarray:
    v = np.array([float(r[colonne]) for r in lc(p)])
    return v


def par_fenetre(p: pathlib.Path, colonne: str = "kl", facteur: float = 1.0) -> np.ndarray:
    """Moyenne des KL de chaque fenêtre (0 à 9), lue position par position."""
    s, n = np.zeros(10), np.zeros(10)
    for r in lc(p):
        f = int(r["fenetre"])
        s[f] += float(r[colonne]) * facteur
        n[f] += 1
    assert (n == 255).all(), n
    return s / n


def sig_f(d: np.ndarray) -> float:
    return float(np.std(d, ddof=1) / math.sqrt(len(d)))


# ------------------------------------------------------------------------------------------------- codon
def codon(V: dict) -> None:
    # III-8.2 : la table CODES_CTX (κ = 1) du 120b, couche 18, matrice 1 (up), avant et après.
    fr = {"1.0": np.zeros(256, int), "1.2": np.zeros(256, int)}
    for r in lc(CO / "codon/tables-octets.csv"):
        if r["modele"] == "120b" and r["couche"] == "18" and r["matrice"] == "1" and r["kappa"] == "1":
            fr[r["version"]][int(r["octet"])] = int(r["frequence"])
    for v, nom in (("1.0", "A"), ("1.2", "B")):
        assert fr[v].sum() == 4096  # témoin : une table rANS somme à 4 096
        V[f"CodonNOctetsSymboles{nom}"] = int((fr[v] > 0).sum())
        V[f"CodonNOctetsNuls{nom}"] = ",".join(f"{o & 15}/{o >> 4}" for o in range(256) if fr[v][o] == 0)
    V["CodonNOctetsVmax"] = max(math.log10(1 + f) for v in fr for f in fr[v])
    # le compte attendu de la v1.2 : ligne et colonne 8 éteintes, 16 + 16 − 1 = 31 octets
    assert 256 - V["CodonNOctetsSymbolesB"] == 31

    # III-8.1 : la roue sur les 72 tenseurs ; recoupée par zero-compte-20b.json (autre outil, même GGUF).
    z = np.load(MES / "genome/predictif-elagage/histo-toutes-gptoss20b.npz")
    comptes = np.zeros(16, dtype=np.int64)
    for t in range(z["comptes"].shape[0]):  # tenseur par tenseur, sans sommer d'un coup
        comptes += z["comptes"][t].astype(np.int64).reshape(-1, 16).sum(axis=0)
    total = int(comptes.sum())
    zc = lj(MES / "genome/etat-de-l-art/journaux/zero-compte-20b.json")
    assert total == int(zc["poids"]) and len(z["noms"]) == zc["tenseurs"]
    p0, p8 = comptes[0] / total, comptes[8] / total
    assert abs(p0 - zc["p_plus0"]) < 1e-12 and abs(p8 - zc["p_moins0"]) < 1e-12, (p0, p8)
    taille = lj(CO / "codon/tailles.json")["totaux"]["20b"]
    assert int(comptes[8]) == taille["moins_zero_fondus"]
    V["CodonNRoueTenseurs"] = len(z["noms"])
    V["CodonNRouePoids"] = total
    V["CodonNRoueZeroPlus"] = 100 * p0
    V["CodonNRoueZeroMoins"] = 100 * p8
    # l'épaisseur dessinée : 0,4 pt + 44 pt × part (lu dans codon-figures.tex, pas dans le script)
    tex = (RACINE / "memoire/figures/tome3/codon-figures.tex").read_text(encoding="utf-8")
    m = re.search(r"\\pgfmathsetmacro\\CodonL\{([\d.]+)\+([\d.]+)\*\\CodonP\}", tex)
    a, b = float(m.group(1)), float(m.group(2))
    V["CodonNRoueEpaisseur"] = (a + b * (p0 + p8)) / (a + b * p0)
    V["_roue_valeurs_ocp"] = None  # contrôlées par points.py

    # III-8.5 (c) : l'axe sans perte, par le codec réel (taux_reel), pas par colonne-par-tenseur.csv.
    tr = lj(MES / "genome/predictif-elagage/taux-reel-colonne-12-gptoss20b.json")
    ts = tr["tenseurs"]
    assert len(ts) == 12 and len({t["poids"] for t in ts}) == 1  # tailles égales : moyenne = total
    sp = np.array([t["bpp_total_identite"] for t in ts])
    ze = np.array([t["bpp_total_zero_fondu"] for t in ts])
    co = np.array([t["bpp_total_nib_kappa_colonne"] for t in ts])
    assert abs(sp.mean() - tr["bpp"]["total_identite"]) < 5e-6
    assert abs(co.mean() - tr["bpp"]["total_nib_kappa_colonne_zero"]) < 5e-6
    assert all(t["exacts"] for t in ts) and tr["temoins"]["tous_exacts"]  # codés puis décodés exactement
    V["CodonNSansPerteFun"], V["CodonNSansPerteZero"], V["CodonNSansPerteColonne"] = sp.mean(), ze.mean(), co.mean()
    V["CodonNSansPertePerd"] = int((co > ze).sum())
    tous = np.concatenate([sp, ze, co])
    V["_sanspert_min"], V["_sanspert_max"] = float(tous.min()), float(tous.max())

    # III-8.6 bis, encart : séance J5 et J6 du juge du placement, passes valides seulement.
    S = MES / "disque/placement/juge/seance"
    def valides(motif: str) -> list[float]:
        out = []
        for p in sorted(S.glob(motif)):
            j = lj(p)
            if j.get("arret_s") or j.get("sous_charge") or j.get("secteur_apres") is False:
                continue
            out.append(j["go_s"])
        return out
    j5c, j6c, j6a = valides("J5-*-C120.json"), valides("J6-*-C120.json"), valides("J6-*-A120.json")
    V["CodonNEncartPassesJcinq"], V["CodonNEncartPassesJsix"] = len(j5c), len(j6c)
    V["CodonNEncartCtire"] = float(np.median(j5c))
    V["CodonNEncartCun"], V["CodonNEncartAun"] = float(np.median(j6c)), float(np.median(j6a))
    V["CodonNEncartCsurA"] = float(np.median(j6c) / np.median(j6a))
    V["CodonNEncartCsurAMoy"] = float(np.mean(j6c) / np.mean(j6a))
    V["CodonNEncartFrag"] = float(np.median(j6c) / np.median(j5c))
    V["_j5_n_troncons"] = {lj(p)["n"] for p in S.glob("J5-*-C120.json")}
    V["_j6_a_passes"] = len(j6a)

    # III-8.6 bis (d) : l'étage disque seul du 120b dans la séance du juge de la construction, B/A des médianes,
    # relu dans les journaux de passe (vitesse/120b-disque-*.json), pas dans disque-passes.csv.
    go = {"A": [], "B": []}
    for p in sorted((CO / "juge/vitesse").glob("120b-disque-*.json")):
        lettre = p.stem.split("-")[-1]
        if lettre in go:
            j = lj(p)
            go[lettre].append(j.get("go_s", j.get("debit_go_s")))
    if any(x is None for l in go.values() for x in l) or not go["A"]:
        dp = [r for r in lc(CO / "juge/figures/disque-passes.csv") if r["modele"] == "120b"]
        go = {x: [float(r["go_s"]) for r in dp if r["lettre"] == x] for x in "AB"}
        V["_disque_source"] = "disque-passes.csv"
    else:
        V["_disque_source"] = "vitesse/120b-disque-*.json"
    V["CodonNCascDisqueBA"] = float(np.median(go["B"]) / np.median(go["A"]))


# ------------------------------------------------------------------------------------------------- juge
def juge(V: dict) -> None:
    # III-8.8 : la part des −0 de chaque expert tiré (v1.2), son maximum et les bornes de l'axe.
    lignes = [r for r in lc(CO / "juge/J-T1-echantillon.csv") if r["version"] == "v12"]
    parts = [(100 * int(r["moins_zero_gguf"]) / int(r["demi_octets"]), r) for r in lignes]
    assert len(parts) == 96
    p_min = min(p for p, _ in parts)
    p_max, r_max = max(parts, key=lambda x: x[0])
    V["JconsNPartMax"], V["JconsNPartMaxModele"] = p_max, r_max["modele"]
    V["JconsNPartMaxCouche"], V["JconsNPartMaxExpert"] = int(r_max["couche"]), int(r_max["expert"])
    V["_part_min"], V["_part_max"] = p_min, p_max
    # le second plus haut : la note « la plus haute » ne doit pas cacher une égalité
    V["_part_second"] = sorted(p for p, _ in parts)[-2]

    # III-10.1 : la marge (jamais routés par couche), les jetons par fenêtre, le plus grand d'un seul jeu.
    g = lc(CO / "juge/figures/routage-grille.csv")
    vides = [0] * 24
    for r in g:
        if int(r["appels_r1"]) == 0 and int(r["appels_neuf"]) == 0:
            vides[int(r["couche"])] += 1
    V["_marge"] = vides
    assert sum(vides) == 11
    k = lj(CO / "juge/J-T0-fichiers.json")["fichiers"]["20b-v10"]["k"]
    run = sum(int(r["appels_r1"]) for r in g)
    neuf = sum(int(r["appels_neuf"]) for r in g)
    assert run == neuf and run % (10 * 24 * k) == 0
    V["JconsNJetonsFenetre"] = run // (10 * 24 * k)
    pos = lc(CO / "synonyme/kl/kl-frontiere-768-positions.csv")
    par_f = {}
    for r in pos:
        par_f.setdefault(int(r["fenetre"]), []).append(int(r["position"]))
    assert all(len(v) == 255 for v in par_f.values()) and len(par_f) == 10
    premiere = {min(v) for v in par_f.values()}
    derniere = {max(v) for v in par_f.values()}
    V["JconsNNotees"] = 255
    V["JconsNContexte"] = premiere.pop()  # positions 0 … 255 non notées : 256 jetons de contexte
    V["_derniere_position"] = derniere.pop()
    V["JconsNAppelsMaxUnJeu"] = max(max(int(r["appels_r1"]), int(r["appels_neuf"])) for r in g)

    # III-10.3, M13 : écart des deux chemins, par les fichiers par position (moteur − référence substituée).
    fr_sub = par_fenetre(CO / "synonyme/kl/kl-frontiere-768-positions.csv", facteur=1.01 if CASSER else 1.0)
    fr_mot = par_fenetre(CO / "synonyme/moteur/kl-moteur-frontiere-positions.csv")
    e = fr_mot - fr_sub
    V["JconsNCheminRunMoy"], V["JconsNCheminRunMin"], V["JconsNCheminRunMax"] = e.mean(), e.min(), e.max()
    l0n = par_fenetre(CO / "juge/kl/kl-neuf-moteur-rapide-l0-positions.csv") - par_fenetre(CO / "juge/kl/kl-neuf-sub-l0-positions.csv")
    V["JconsNCheminNeufMoy"], V["JconsNCheminNeufAbsMax"] = l0n.mean(), np.abs(l0n).max()
    # les autres variantes passées par les deux chemins sur R1 (la légende ne cite que la frontière)
    for nom, a, b in (("lambda1", "kl-moteur-synonyme-positions.csv", "kl-synonyme-768-positions.csv"),
                      ("lambda0", "kl-moteur-synonyme-l0-positions.csv", "kl-synonyme-l0-768-positions.csv")):
        d = par_fenetre(CO / "synonyme/moteur" / a) - par_fenetre(CO / "synonyme/kl" / b)
        V[f"_chemin_r1_{nom}"] = (float(d.mean()), float(d.min()), float(d.max()))
    # témoin : la voie substituée de R1 relue par position redonne kl-par-fenetre.csv
    kpf = {(r["jeu"], r["chemin"], r["variante"], int(r["fenetre"])): float(r["kl"])
           for r in lc(CO / "juge/figures/kl-par-fenetre.csv")}
    if not CASSER:
        assert max(abs(fr_sub[f] - kpf[("r1", "f64-substituee", "frontiere", f)]) for f in range(10)) < 1e-8


# ------------------------------------------------------------------------------------------------- synonyme
def synonyme(V: dict) -> None:
    S = CO / "synonyme"
    # III-9.1 : aires, sur-apprentissage, amortissement.
    sp = lc(S / "figures/spectre-L08-E00-gate.csv")
    lc_ = np.array([float(r["lambda_calib"]) for r in sp])
    le = np.array([float(r["lambda_eval_rayleigh"]) for r in sp])
    ef = np.array([float(r["e_frontiere"]) for r in sp])
    es = np.array([float(r["e_synonyme"]) for r in sp])
    assert len(lc_) == 2880
    def part(lam, e):
        c = np.cumsum(lam * e)
        return c / c[-1]
    V["SynoNAireS"] = float(np.mean(part(lc_, es) - part(le, es)))
    V["SynoNAireF"] = float(np.mean(part(lc_, ef) - part(le, ef)))
    V["SynoNSurF"] = float((le * ef).sum() / (lc_ * ef).sum())
    V["SynoNSurS"] = float((le * es).sum() / (lc_ * es).sum())
    # témoin : les coûts redonnent 16,50 / 6,15 / 16,09 / 10,28 (premier flux, inchangés)
    assert f"{(lc_ * ef).sum():.2f}" == "16.50" and f"{(le * es).sum():.2f}" == "10.28"
    moy = float(lc_.mean())  # tr H / n
    V["SynoNAmorti"], V["SynoNAmortiDessus"] = moy, int((lc_ > moy).sum())
    V["_aire_moitie_sans_rang"] = None

    # III-9.2 : la queue.
    fichiers = {"q2_0": S / "repere/kl-q2_0-positions.csv", "frontiere": S / "kl/kl-frontiere-768-positions.csv",
                "lambda1": S / "kl/kl-synonyme-768-positions.csv", "lambda0": S / "kl/kl-synonyme-l0-768-positions.csv"}
    kl = {n: kl_positions(p) for n, p in fichiers.items()}
    if CASSER:
        kl["frontiere"] = kl["frontiere"] * 1.01
    V["SynoNSurvieGauche"] = 100 * max(float((v <= 0.01).mean()) for v in kl.values())
    V["_survie_gauche_par_serie"] = {n: round(100 * float((v <= 0.01).mean()), 3) for n, v in kl.items()}
    V["_max_par_serie"] = {n: float(v.max()) for n, v in kl.items()}
    med = {n: float(np.median(v)) for n, v in kl.items()}
    V["SynoNDivUn"], V["SynoNDivZero"] = med["frontiere"] / med["lambda1"], med["frontiere"] / med["lambda0"]
    p999 = {n: float(np.percentile(v, 99.9)) for n, v in kl.items()}
    dessus = {n: int((v > p999[n]).sum()) for n, v in kl.items()}
    assert len(set(dessus.values())) == 1
    V["SynoNQueueDessus"] = dessus["frontiere"]
    J = CO / "juge/kl"
    nf = {"frontiere": kl_positions(J / "kl-neuf-sub-frontiere-positions.csv"),
          "lambda1": kl_positions(J / "kl-neuf-moteur-rapide-l1-positions.csv"),
          "lambda0": kl_positions(J / "kl-neuf-moteur-rapide-l0-positions.csv"),
          "lambda0_sub": kl_positions(J / "kl-neuf-sub-l0-positions.csv")}
    q = {n: float(np.percentile(v, 99.9)) for n, v in nf.items()}
    V["SynoNQueueUnRun"] = 100 * (1 - p999["lambda1"] / p999["frontiere"])
    V["SynoNQueueZeroRun"] = 100 * (1 - p999["lambda0"] / p999["frontiere"])
    V["SynoNQueueUnNeuf"] = 100 * (1 - q["lambda1"] / q["frontiere"])
    V["SynoNQueueZeroNeuf"] = 100 * (1 - q["lambda0"] / q["frontiere"])
    V["_queue_zero_neuf_meme_chemin"] = 100 * (1 - q["lambda0_sub"] / q["frontiere"])
    V["_p999_neuf"] = q

    # III-9.3 : les bornes communes, et le mélange de chemins.
    sub = {n: par_fenetre(fichiers[n]) for n in ("frontiere", "lambda1", "lambda0")}
    if CASSER:
        sub["frontiere"] = sub["frontiere"] * 1.01
    neuf = {n: par_fenetre(J / f) for n, f in (("frontiere", "kl-neuf-sub-frontiere-positions.csv"),
                                                 ("lambda1", "kl-neuf-moteur-rapide-l1-positions.csv"),
                                                 ("lambda0", "kl-neuf-moteur-rapide-l0-positions.csv"),
                                                 ("lambda0_sub", "kl-neuf-sub-l0-positions.csv"))}
    d = {"un-frontiere": (sub["lambda1"] - sub["frontiere"], neuf["lambda1"] - neuf["frontiere"]),
         "zero-un": (sub["lambda0"] - sub["lambda1"], neuf["lambda0"] - neuf["lambda1"]),
         "zero-frontiere": (sub["lambda0"] - sub["frontiere"], neuf["lambda0_sub"] - neuf["frontiere"])}
    tout = []
    for r1, nv in d.values():
        for x in (r1, nv):
            m, s = x.mean(), sig_f(x)
            tout += list(x) + [m - 2 * s, m + 2 * s]
    V["_foret_min"], V["_foret_max"] = min(tout), max(tout)
    V["_foret_r1_fen7_zero_un"] = float(d["zero-un"][0][7])
    V["SynoNForUnFNeufZ"] = abs(d["un-frontiere"][1].mean()) / sig_f(d["un-frontiere"][1])
    V["SynoNForZeroUnRunZ"] = abs(d["zero-un"][0].mean()) / sig_f(d["zero-un"][0])
    mot = {n: par_fenetre(S / "moteur" / f) for n, f in (("frontiere", "kl-moteur-frontiere-positions.csv"),
                                                          ("lambda1", "kl-moteur-synonyme-positions.csv"))}
    melange = (mot["lambda1"] - sub["frontiere"]).mean()
    seul_sub = (sub["lambda1"] - sub["frontiere"]).mean()
    seul_mot = (mot["lambda1"] - mot["frontiere"]).mean()
    V["SynoNForMelange"] = max(abs(melange - seul_sub), abs(melange - seul_mot))
    V["_melange"] = (float(melange), float(seul_sub), float(seul_mot))

    # III-9.6 : bits du moteur exact, cadre, rapports σ_f / σ_n.
    t0 = lj(CO / "juge/J-T0-fichiers.json")["fichiers"]["20b-v10"]
    V["SynoNExactBits"] = t0["somme_octets_utiles"] * 8 / t0["poids_experts"]  # bits utiles, recalculés
    var = {r["variante"]: r for r in lc(S / "figures/variantes-768.csv")}
    pos = {"frontiere": fichiers["frontiere"], "synonyme-l1": fichiers["lambda1"],
           "synonyme-l0": fichiers["lambda0"], "llama-q2_0": fichiers["q2_0"]}
    rap, sf = {}, {}
    for v, p in pos.items():
        m = par_fenetre(p)
        sf[v] = sig_f(m)
        assert abs(m.mean() - float(var[v]["kl"])) < 1e-6  # témoin : la moyenne de 07 redonnée
        rap[v] = sf[v] / float(var[v]["kl_incertitude"])
    V["SynoNSigmaRapportMin"], V["SynoNSigmaRapportMax"] = min(rap.values()), max(rap.values())
    V["_rapports_sigma"] = rap
    trois = ("frontiere", "synonyme-l1", "synonyme-l0")
    V["_var_bits"] = (min(float(var[v]["bits_par_poids"]) for v in trois), max(float(var[v]["bits_par_poids"]) for v in trois))
    V["_var_kl"] = (min(float(var[v]["kl"]) - 2 * sf[v] for v in trois), max(float(var[v]["kl"]) + 2 * sf[v] for v in trois))
    V["_q2_0"] = (float(var["llama-q2_0"]["bits_par_poids"]), float(var["llama-q2_0"]["kl"]))
    ex = lc(MES / "moteur/O/journaux/o3/c4-20b-comparer.csv")
    V["_exact_kl"] = float(np.mean([float(r["kl_b"]) for r in ex]))


def decimales(s: str) -> int | None:
    s = s.strip()
    if re.fullmatch(r"-?\d+", s):
        return 0
    m = re.fullmatch(r"-?\d+\.(\d+)", s)
    return len(m.group(1)) if m else None


def frontiere_arrondi(v: float, d: int) -> bool:
    x = abs(v) * 10 ** d
    return abs((x - math.floor(x)) - 0.5) < 1e-6 * max(1.0, x)


def main() -> int:
    global CASSER
    ap = argparse.ArgumentParser()
    ap.add_argument("--casser", action="store_true")
    ap.add_argument("--sortie", default=None)
    a = ap.parse_args()
    CASSER = a.casser
    V: dict = {}
    codon(V)
    juge(V)
    synonyme(V)
    lot = nombres_du_lot()
    lignes, ecarts = [], 0
    for nom, v in V.items():
        if nom.startswith("_"):
            continue
        s = lot.get(nom)
        if s is None:
            lignes.append((nom, "", repr(v), "absent du lot"))
            ecarts += 1
            continue
        if isinstance(v, str):
            ok = v == s
            moi = v
        else:
            d = decimales(s)
            if d is None:
                moi, ok = repr(v), False
            elif d == 0 and isinstance(v, int):
                moi = str(v)
                ok = moi == s
            else:
                moi = f"{v:.{d}f}"
                ok = moi == s or (moi == "-0.0000" and s == "0.0000")
                if ok and frontiere_arrondi(v, d):
                    lignes.append((nom, s, f"{v!r}", "tient, frontière d'arrondi"))
                    continue
        lignes.append((nom, s, moi if ok else f"{moi} ({v!r})", "tient" if ok else "ÉCART"))
        ecarts += 0 if ok else 1
    largeur = max(len(l[0]) for l in lignes)
    for l in lignes:
        print(f"{l[0]:<{largeur}}  lot {l[1]:<14} juge {l[2]:<28} {l[3]}")
    print()
    for nom, v in V.items():
        if nom.startswith("_") and v is not None:
            print(f"{nom} = {v}")
    print(f"\n{len(lignes)} nombres refaits, {ecarts} écart(s){' (cassure)' if CASSER else ''}")
    if a.sortie:
        p = pathlib.Path(a.sortie)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["nom", "lot", "juge", "statut"])
            w.writerows(lignes)
            for nom, v in V.items():
                if nom.startswith("_") and v is not None:
                    w.writerow([nom, "", repr(v), "lecture"])
    return 1 if ecarts else 0


if __name__ == "__main__":
    sys.exit(main())
