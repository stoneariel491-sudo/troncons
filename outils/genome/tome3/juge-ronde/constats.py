"""Juge du lot « ronde » : les nombres des constats du jugement qui ne sont pas des clés du lot.

Écrit par le juge le 2026-10-27. Chaque bloc refait, depuis les fichiers commités sous mesures/, un
nombre que memoire/tome3/JUGEMENT-figures-ronde.md cite pour dire qu'une légende est fausse, incomplète
ou juste. Sortie : journaux/constats.txt (aussi sur la sortie standard).

Usage : python -I -X utf8 constats.py
"""
from __future__ import annotations

import collections
import csv
import json
import math
import os
import sys

import numpy as np
from scipy.stats import spearmanr

ICI = os.path.dirname(os.path.abspath(__file__))
R = os.path.normpath(os.path.join(ICI, "..", "..", "..", ".."))
sys.stdout.reconfigure(encoding="utf-8")
LIGNES = []


def dire(*a):
    s = " ".join(str(x) for x in a)
    LIGNES.append(s)
    print(s)


def lc(*p):
    with open(os.path.join(R, *p), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def lj(*p):
    with open(os.path.join(R, *p), encoding="utf-8") as f:
        return json.load(f)


E = ("mesures", "genome", "etat-de-l-art", "journaux")

# G1. III-7.1 : le verdict des partitions par κ tenseur par tenseur, par la règle que la légende énonce
dire("== G1. III-7.1, règle appariée (égal si d ≤ 2σ ; meilleur si d + 2σ < 0)")
F = {r["mecanisme"]: r for r in lc("mesures", "genome", "construction", "synthese", "k10", "frontiere.csv")}
for nom in ("mutation synonyme λ = 0, δ* = 1", "S* (10 fenêtres)", "partitions par κ, chaque tenseur à l'erreur de la base",
            "partitions par κ, erreur moyenne égale", "hebbien (δ, ligne, colonne)", "hebbien par e (erreur d'expert égale à la base)",
            "hebbien (e, ligne, colonne)", "partitions par e (remplissage inverse des poids)", "élagage par activité de colonne (e, q)"):
    r = F[nom]
    if r["diff_apparie"]:
        d, s = float(r["diff_apparie"]), float(r["diff_apparie_sigma"])
        v = "meilleur" if d + 2 * s < 0 else ("égal" if d <= 2 * s else "tombe")
        dire(f"  {nom} : rapport {float(r['rapport_kl']):.4f}, d = {d:+.5f} ± {s:.5f} ({d / s:+.2f} σ) -> {v} ; colonne verdict « {r['verdict']} »")
    else:
        dire(f"  {nom} : rapport {float(r['rapport_kl']):.4f}, pas de différence appariée ; colonne verdict « {r['verdict']} »")

# M1. III-3.4 : les rangées de chaque point du balayage
dire("== M1. III-3.4, rangées par point du balayage gaussien")
for l in open(os.path.join(R, "mesures", "genome", "genome", "gauss-balayage.jsonl"), encoding="utf-8"):
    if l.strip():
        d = json.loads(l)
        dire(f"  l = {d['l']:2d} ({d['kb']},{d['v']}) {d['melangeur']:5s} q = {d['q']:2d} Lloyd {d['lloyd']} : {d['rangees']} rangées, {d['poids']} poids")

# M3. III-4.2 : le plancher commun de la couche 0
dire("== M3. III-4.2, scores et cos de down des candidats de même couche, par couche")
S = lc("mesures", "genome", "duplication", "csv", "scores-parente.csv")
for c in ("0", "8", "16", "23"):
    cd = np.array([float(r["cos_down"]) for r in S if r["couche"] == c and r["genre"] == "intra"])
    sc = np.array([float(r["score_bits"]) for r in S if r["couche"] == c and r["genre"] == "intra"])
    dire(f"  couche {c:>2s} : {len(sc)} candidats, cos_down {cd.min():.3f} / {np.median(cd):.3f} / {cd.max():.3f}, score {sc.min():.4f} / {np.median(sc):.4f} / {sc.max():.4f} (min / médiane / max)")
t12 = lj("mesures", "genome", "duplication", "paires-temoin-planter-0.5.json")
t23 = lj("mesures", "genome", "duplication", "arbre-c23.json")
dire(f"  témoin du hasard : couche {t12['arguments']['couche']}, {len(t12['temoin_hasard'])} paires, {np.mean([p['score_bits'] for p in t12['temoin_hasard']]):.6f} ; "
     f"couche {t23['arguments']['couche']}, {len(t23['temoin_hasard'])} paires, {np.mean([p['score_bits'] for p in t23['temoin_hasard']]):.6f}")
m = max(S, key=lambda r: float(r["score_bits"]))
dire(f"  score maximal {float(m['score_bits']):.6f} : enfant ({m['couche']}, {m['enfant']}) parent ({m['cand_couche']}, {m['cand_expert']})")

# M4. III-4.8 : les degrés dans l'arbre
dire("== M4. III-4.8, degrés dans l'arbre de la couche 23")
A = lc("mesures", "genome", "duplication", "csv", "phylogenie-c23-aretes.csv")
deg = collections.Counter()
poids = collections.Counter()
for a in A:
    for k in (a["i"], a["j"]):
        deg[int(k)] += 1
        poids[int(k)] += float(a["score"])
dmax = max(deg.values())
dire(f"  degré maximal {dmax} : experts {sorted(k for k, v in deg.items() if v == dmax)} ; somme des arêtes : " +
     ", ".join(f"{k} {poids[k]:.4f}" for k in sorted(k for k, v in deg.items() if v == dmax)))
N = {int(r["expert"]): (float(r["x"]), float(r["y"])) for r in lc("mesures", "genome", "duplication", "csv", "phylogenie-c23-noeuds.csv")}
for a in sorted(A, key=lambda a: -float(a["score"]))[:4]:
    i, j = int(a["i"]), int(a["j"])
    dist = math.dist(N[i], N[j]) * 2.95
    dire(f"  arête ({i}, {j}) {a['score']} bit : longueur sur la page {dist:.2f} cm (disques de 0,30 + 0,045 × degré cm)")

# M5. III-7.1 : les experts de λ = 1
dire("== M5. III-7.1, experts de la passe λ = 1 et de P1")
for f in ("synonyme-lam1-damp1-e0_8_16_24.csv", "synonyme-lam0-damp1.csv"):
    rr = lc("mesures", "genome", "etat-de-l-art", "passes", f)
    ex = sorted({(int(r["couche"]), int(r["expert"])) for r in rr if r["expert"] != ""})
    dire(f"  {f} : {len(ex)} experts, par couche {sorted(collections.Counter(c for c, e in ex).items())}, experts {sorted({e for c, e in ex})}")

# M6. III-7.1 : ce que la colonne perd, contre l'octet ou contre le demi-octet
dire("== M6. III-7.1, colonne contre codon en octets et contre demi-octets sans colonne")
for r in lc("mesures", "genome", "construction", "synthese", "k10", "colonne-par-tenseur.csv"):
    o, n, c = float(r["zero_octet_kappa"]), float(r["zero_demi_octet_kappa"]), float(r["zero_demi_octet_kappa_colonne"])
    dire(f"  {r['tenseur']:28s} colonne − octet {c - o:+.6f} ; colonne − demi-octet {c - n:+.6f} ; demi-octet − octet {n - o:+.6f}")

# M9. III-7.3 : la queue, position par position
dire("== M9. III-7.3, la queue position par position")
pb = lc(*E, "kl-frontiere-positions.csv")
ps = lc(*E, "kl-synonyme-d1-positions.csv")
kb = np.array([float(r["kl"]) for r in pb])
ks = np.array([float(r["kl"]) for r in ps])
fen = np.array([int(r["fenetre"]) for r in pb])
for s in (0.1, 0.3, 1.0):
    hb, hs = kb > s, ks > s
    dire(f"  seuil {s} : base {hb.sum()}, synonyme {hs.sum()}, communes {(hb & hs).sum()}, base seule {(hb & ~hs).sum()}, synonyme seul {(hs & ~hb).sum()}")
top = np.argsort(-(kb + ks))[:100]
dire(f"  Spearman des 100 plus grandes (somme) {spearmanr(kb[top], ks[top]).statistic:+.3f} ; Spearman global {spearmanr(kb, ks).statistic:+.3f}")
for nom, msk in (("base > 0,3", kb > 0.3), ("synonyme > 0,3", ks > 0.3), ("base < 0,01", kb < 0.01), ("base > 1", kb > 1)):
    d = np.log10(np.maximum(ks[msk], 1e-5) / kb[msk])
    dire(f"  {nom} : {msk.sum()} positions, log10(syn/base) médiane {np.median(d):+.3f}, part sous la diagonale {np.mean(d < 0):.3f}")
for nom, k in (("base", kb), ("synonyme", ks)):
    t = np.argsort(-k)[:26]
    dire(f"  26 plus grandes de la {nom}, par fenêtre : {sorted(collections.Counter(fen[t].tolist()).items())}")
    tri = np.sort(k)[::-1]
    dire(f"  part de la somme : 25 positions {tri[:25].sum() / k.sum():.4f}, 26 positions {tri[:26].sum() / k.sum():.4f}")
dire(f"  KL < 1e-5 : base {(kb < 1e-5).sum()}, synonyme {(ks < 1e-5).sum()} (dont négatives {(ks < 0).sum()}, min {ks.min():.3e})")

# M12. III-1.2 : l'écart compté sans les échelles
dire("== M12. III-1.2, écart à la borne avec et sans le coût des échelles")
b = lj(*E, "borne-rd.json")
P = sorted((q["D"], q["bits"]) for q in b["uniforme_precis"])
zc = lj(*E, "zero-canonique.json")
corde = float(np.interp(zc["erreur_base_commune"], [a for a, _ in P], [c for _, c in P]))
P_ = sorted((q["D"], q["bits"]) for q in b["uniforme_precis"] if q["D"] > 0)
logi = float(np.interp(math.log(zc["erreur_base_commune"]), [math.log(a) for a, _ in P_], [c for _, c in P_]))
fr8 = lj("mesures", "genome", "etat-de-l-art", "passes", "frontiere-lam0-damp0.01.json")
dire(f"  corde (linéaire en D) {corde:.5f} bits ; interpolation en log D {logi:.5f} bits (le trait tracé)")
zt = lj(*E, "zero-temoin-sans-drapeau.json")
dire(f"  rANS réel avec échelles {zt['bpp']['niveau0_base']:.5f} -> écart {zt['bpp']['niveau0_base'] - corde:.4f} ; H0 seul (05 § 1.1 : 2,6415) -> écart {2.6415 - corde:.4f}")

# N2. III-4.8 : le témoin de la projection, sur 200 permutations
dire("== N2. III-4.8, témoin de la MDS : voir journaux/temoin-mds.csv (refaire.py)")

with open(os.path.join(ICI, "journaux", "constats.txt"), "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(LIGNES) + "\n")
