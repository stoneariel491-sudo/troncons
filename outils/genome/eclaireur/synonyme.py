"""La mutation synonyme : une base de 2 bits choisie là où la sortie ne la voit pas.

Éclaireur du génome des poids (genome/01-eclaireur.md). Écrit de zéro pour troncons, le 2026-10-16.

LE MÉCANISME. La base de B (étude 07, ARCHITECTURE § 3) range chaque code E2M1 d'un poids MXFP4 dans
une classe de magnitude parmi quatre ({0 ; 0,5} {1 ; 1,5 ; 2} {3 ; 4} {6}) et garde son signe : 8
symboles, reconstruits par ± centre[classe] · échelle E8M0 du bloc. C'est une FONCTION du code : la
« frontière » (2,64 bits, 4,29 % d'erreur relative sur les poids). Le code génétique fait mieux
qu'une fonction fixe : il est rangé pour que les erreurs les plus probables tombent sur des codons
synonymes, sans effet sur la protéine (Freeland et Hurst 1998). Ici, le « phénotype » d'une matrice
est sa sortie W x sur les entrées que le modèle lui donne vraiment ; une erreur de poids dans une
direction que ces entrées n'excitent pas est synonyme. La mutation synonyme choisit donc, colonne
après colonne, le symbole de base de chaque poids en reportant l'erreur commise sur les colonnes
suivantes, pondérée par la covariance réelle des entrées H = E[g² x xᵀ] (la rétroaction d'erreur de
OBQ/GPTQ, Frantar et al. 2022, et du neurone sigma-delta), sous une contrainte d'entropie (le coût
d'un symbole est sa longueur de code, −log2 p). Le décodeur ne change pas : mêmes 8 symboles, mêmes
quatre centres, mêmes échelles E8M0 ; tout le mécanisme vit dans le codeur.

VARIANTES MESURÉES (toutes sur les mêmes experts et les mêmes entrées) :
  frontiere        symbole = fonction du code (la base de 07 et de F1) ;
  ecsq(λ)          H = I : choix du symbole le plus proche, contrainte d'entropie λ (sans rétroaction) ;
  synonyme(λ)      H réel (calibration) : rétroaction d'erreur + contrainte d'entropie λ ;
  synonyme1(λ)     idem avec 2 classes de magnitude (4 symboles, la base « signe + 1 bit » de 07).
  frontiere0       (ajoutée le 2026-10-16 après la découverte du codon synonyme du zéro, avant sa
                   passe) : la frontière sur le code CANONIQUE (−0 → +0) ; le signe de la base d'un
                   zéro, qui n'est plus stocké, est tiré d'un hachage de la position (r, c) que le
                   décodeur recalcule sans lire un bit. Seuil déclaré avant sa passe : elle ÉGALE la
                   frontière si son erreur de sortie d'expert est dans l'écart des deux moitiés de
                   l'évaluation autour de celle de la frontière ; son débit est celui que mesure le
                   codeur rANS réel (zero-synonyme --zero-canonique, base_seule + δ + médianes).

SEUILS ET TÉMOINS, DÉCLARÉS AVANT LE LANCEMENT (2026-10-16) :
  T0 second chemin de 07 : l'erreur relative de la base frontière, recalculée poids par poids en f64
     sur les 12 tenseurs entiers (couches 0, 8, 16, 23 × gate, up, down), égale 0,042919745 à 1e-6
     relatif près (07 l'obtenait par comptes de codes) ; --casser : centres permutés, doit tomber.
  T1 connu d'avance : synonyme avec H = I et λ = 0 rend EXACTEMENT les symboles de la frontière
     (0 symbole différent) ; cassure : le même calcul avec le H réel doit en changer (> 0).
  T2 témoin de l'estimateur de débit : H0 des symboles frontière sur les 12 tenseurs entiers = 2,642
     bits (07) à 0,001 près.
  CRITÈRE (déclaré avant) : un mécanisme BAT la frontière si, à débit ≤ celui de la frontière (même
     estimateur, mêmes experts), son erreur relative de SORTIE d'expert (les trois matrices
     remplacées, entrées réelles TENUES À L'ÉCART de la calibration, pondérées par g²) est plus basse
     que celle de la frontière sur CHACUNE des deux moitiés des fenêtres d'évaluation (0-4 et 5-9) et
     dans CHACUNE des quatre couches ; l'accord des moitiés est le bruit de référence. Il l'ÉGALE si
     l'ordre change d'une moitié ou d'une couche à l'autre.
  Amortissement de H : δ = 0,01 · moyenne(diag H) (valeur de GPTQ) ; 0,1 en sensibilité, déclarée.
  Pondération de H : g² (l'expert entre dans le résidu multiplié par son poids de routeur g).
  Experts : couches 0, 8, 16, 23 ; experts 0, 4, …, 28 (8 par couche, 96 matrices, 796 M poids).
  Débit : H0 des symboles par tenseur (couche, rôle) sur les experts mesurés, plus 0,0375 bit
     (échelles δ 0,0347 et médianes 0,0028 de F1) ; et H(symbole | κ), κ = e − médiane(e de la
     ligne) borné à [−3, 1], pour toutes les variantes.

Entrées : captures de genome-capture (calib : fenêtres 10..22 de wiki.test ; eval : 0..10).

Utilisation :
  python -I -X utf8 synonyme.py temoins [--casser]          > journal.json
  python -I -X utf8 synonyme.py mesurer --variante V --lam L [--damp 0.01] --csv f.csv > journal.json
  python -I -X utf8 synonyme.py ecrire-sym --variante V --lam L [--damp δ] --sortie D [--couches a,b] [--experts a,b]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import sys
import time

import numpy as np
from scipy import linalg

ICI = os.path.dirname(os.path.abspath(__file__))
LECTEUR = os.path.join(ICI, "..", "..", "03-entropie", "gguf_lecture.py")
FICHIER = "~/dev/modeles/gguf/gpt-oss-20b-MXFP4.gguf"
CAPTURES = "~/dev/essais/troncons/genome/eclaireur"
COUCHES = (0, 8, 16, 23)
EXPERTS = tuple(range(0, 32, 4))
# Sous-ensemble réduit pour les passes suivantes (déclaré le 2026-10-17 à 1 h, AVANT ces passes : la
# machine partagée rend une passe à rétroaction de 8 experts par couche longue de 4 à 5 h) : la variable
# d'environnement SYN_EXPERTS (ex. « 0,8,16,24 ») remplace la liste ; la frontière est alors
# recalculée sur les mêmes experts (passe frontiere au même SYN_EXPERTS).
if os.environ.get("SYN_EXPERTS"):
    EXPERTS = tuple(int(x) for x in os.environ["SYN_EXPERTS"].split(","))
ROLES = ("gate", "up", "down")
D = 2880
MAG = np.array([0, 1, 2, 3, 4, 6, 8, 12], dtype=np.float64)       # E2M1 doublées (ggml)
CLASSES2 = np.array([0, 0, 1, 1, 1, 2, 2, 3])                      # meilleure partition de 07
CLASSES1 = np.array([0, 0, 0, 0, 1, 1, 1, 1])                      # signe + 1 bit, 07
ERREUR_07 = 0.042919745124980
H_BASE_07 = 2.642
SURCOUT_ECHELLES = 0.0347 + 0.0028


def charger_lecteur():
    spec = importlib.util.spec_from_file_location("gguf_lecture", LECTEUR)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gguf_lecture"] = mod
    spec.loader.exec_module(mod)
    return mod


class Modele:
    def __init__(self):
        self.lec = charger_lecteur().LecteurGGUF(FICHIER)
        self.t = {t.nom: t for t in self.lec.tenseurs}

    def blocs(self, l: int, role: str, e: int | None = None):
        """(exposants (E|1, R, C/32) u8, codes (E|1, R, C) u8) du tenseur d'experts."""
        t = self.t[f"blk.{l}.ffn_{role}_exps.weight"]
        n_e = t.dims[2]
        o = np.asarray(self.lec.octets(t)).reshape(n_e, -1)
        if e is not None:
            o = o[e:e + 1]
        o = o.reshape(o.shape[0], D, D // 32, 17)
        ex = o[..., 0].copy()
        qs = o[..., 1:]
        codes = np.concatenate([qs & 15, qs >> 4], axis=-1).reshape(o.shape[0], D, D)
        return ex, codes

    def biais(self, l: int, role: str, e: int) -> np.ndarray:
        t = self.t[f"blk.{l}.ffn_{role}_exps.bias"]
        o = np.asarray(self.lec.octets(t)).view(np.float32).reshape(t.dims[1], t.dims[0])
        return o[e].astype(np.float64)


def echelle(ex: np.ndarray) -> np.ndarray:
    """2^(e − 128) en f64, exact (e = 255 n'apparaît pas dans gpt-oss : vérifié par 07 et R)."""
    return np.ldexp(1.0, ex.astype(np.int32) - 128)


def dequant(ex, codes) -> np.ndarray:
    s = np.repeat(echelle(ex), 32, axis=-1)
    v = MAG[codes & 7] * s
    return np.where(codes & 8, -v, v)


def signe_hache(R, C) -> np.ndarray:
    """Bit pseudo-aléatoire de la position (r, c) : bit fort du mélangeur splitmix64 appliqué à
    r·C + c (Steele, Lea et Flood 2014). Une suite de Weyl seule (i · φ64) laissait des lignes voisines
    presque identiques : vu au premier essai, d'où le mélangeur."""
    z = np.arange(R, dtype=np.uint64)[:, None] * np.uint64(C) + np.arange(C, dtype=np.uint64)[None, :]
    with np.errstate(over="ignore"):
        z = z + np.uint64(0x9E3779B97F4A7C15)
        z = (z ^ (z >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
        z = (z ^ (z >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
        z = z ^ (z >> np.uint64(31))
    return (z >> np.uint64(63)).astype(np.uint8)


def sym_frontiere(codes, classes=CLASSES2) -> np.ndarray:
    return (((codes >> 3) & 1) << 2 | classes[codes & 7]).astype(np.uint8)


def reconstruire(ex, sym, centres) -> np.ndarray:
    nk = len(centres)
    lev = np.concatenate([centres, -np.asarray(centres)])
    s = np.repeat(echelle(ex), 32, axis=-1)
    k = (sym & 3) + nk * ((sym >> 2) & 1) if nk == 4 else (sym & 1) + 2 * ((sym >> 2) & 1)
    return lev[k] * s


def centres_ponderes(C: np.ndarray, classes) -> np.ndarray:
    """Centres de gravité par classe, pondérés par le carré de l'échelle (07). C[e, code] comptes."""
    emax = int(np.nonzero(C.sum(axis=1))[0].max())
    w = 4.0 ** (np.arange(256) - emax)
    Wq = (C * w[:, None]).sum(axis=0)
    Wm = Wq[:8] + Wq[8:]
    K = int(max(classes)) + 1
    return np.array([(Wm[classes == k] * MAG[classes == k]).sum() / Wm[classes == k].sum() for k in range(K)])


def comptes(ex, codes) -> np.ndarray:
    e = np.repeat(ex.astype(np.int64), 32, axis=-1).ravel()
    return np.bincount(e * 16 + codes.ravel().astype(np.int64), minlength=4096).reshape(256, 16).astype(np.float64)


def entropie(n: np.ndarray) -> float:
    p = n[n > 0] / n.sum()
    return float(-(p * np.log2(p)).sum())


def hist_tenseur(m, l, role, classes) -> np.ndarray:
    """Histogramme des symboles frontière du tenseur entier (32 experts), expert par expert."""
    h = np.zeros(8)
    for e in range(32):
        _, codes = m.blocs(l, role, e)
        h += np.bincount(sym_frontiere(codes, classes).ravel(), minlength=8)
    return h


def kappa(ex) -> np.ndarray:
    med = np.median(ex.astype(np.int32), axis=-1, keepdims=True)
    return np.clip(np.repeat(ex.astype(np.int32) - med.astype(np.int32), 32, axis=-1), -3, 1) + 3


# ---------------------------------------------------------------- entrées réelles

class Entrees:
    def __init__(self, quoi: str, l: int):
        d = os.path.join(CAPTURES, quoi)
        self.h = np.memmap(os.path.join(d, f"h-L{l:02d}.f32"), dtype=np.float32, mode="r").reshape(-1, D)
        r = np.fromfile(os.path.join(d, f"routage-L{l:02d}.bin"), dtype=np.uint8).reshape(-1, 20)
        self.choix = r[:, :4]
        self.g = r[:, 4:].copy().view(np.float32).reshape(-1, 4)
        assert self.h.shape[0] == self.choix.shape[0]

    def expert(self, e: int, positions=None):
        p, j = np.nonzero(self.choix == e)
        if positions is not None:
            m = (p >= positions[0]) & (p < positions[1])
            p, j = p[m], j[m]
        return np.asarray(self.h[p], dtype=np.float64), self.g[p, j].astype(np.float64)


def swiglu(gv, uv):
    g = np.minimum(gv, 7.0)
    u = np.clip(uv, -7.0, 7.0)
    return g / (1.0 + np.exp(-1.702 * g)) * (u + 1.0)


def hessienne(X, g, damp):
    w = g * g
    H = (X * w[:, None]).T @ X / w.sum()
    m = float(np.mean(np.diag(H)))
    H[np.diag_indices_from(H)] += damp * m
    return H


# ---------------------------------------------------------------- le choix des symboles

def facteur_inverse(H):
    """U triangulaire supérieure telle que Uᵀ U = H⁻¹ (le facteur de GPTQ), par une seule
    factorisation : si P H P = L Lᵀ (P renverse l'ordre), alors U = P L⁻¹ P. Démonstration :
    H = P L Lᵀ P = (P L P)(P L P)ᵀ = V Vᵀ avec V = P L P supérieure ; H⁻¹ = V⁻ᵀ V⁻¹ = Uᵀ U avec
    U = V⁻¹ = P L⁻¹ P, supérieure. Coût n³/3 + n³/3 au lieu de n³ + n³/3."""
    n = H.shape[0]
    L = linalg.cholesky(H[::-1, ::-1], lower=True)
    Li = linalg.solve_triangular(L, np.eye(n), lower=True)
    return np.ascontiguousarray(Li[::-1, ::-1])


def choisir(W, ex, centres, H, lam, ell, bloc=32):
    """Rétroaction d'erreur (OBQ/GPTQ) colonne par colonne, contrainte d'entropie.

    W (R, C) f64, ex (R, C/32), centres (K,), H (C, C) ou None (= identité), lam ≥ 0, ell (2K,)
    longueurs de code en bits des symboles (positifs puis négatifs). Rend sym (R, C) u8 : bits 0-1
    la classe, bit 2 le signe négatif.
    Coût d'un choix q pour le poids courant w (après rétroaction) : (|w| − q)² + lam · U_jj² · ℓ(q),
    soit, divisé par U_jj², l'accroissement de tr(ΔW H ΔWᵀ) plus lam bits-équivalents. Le signe du
    symbole suit celui de w (signbit : −0 compte pour négatif, comme le code −0 dans la frontière ;
    T1 l'exige) ; un candidat de signe opposé ne gagne jamais à lam = 0 et n'est pas considéré.
    Disposition transposée (colonnes contiguës) pour la vitesse.
    """
    R, C = W.shape
    K = len(centres)
    lev = np.asarray(centres, dtype=np.float64)
    sT = np.ascontiguousarray(np.repeat(echelle(ex), 32, axis=-1).T)
    WT = np.ascontiguousarray(W.T)
    if H is None:
        U = None
    else:
        U = facteur_inverse(H)
    ellp, elln = np.asarray(ell[:K], dtype=np.float64), np.asarray(ell[K:], dtype=np.float64)
    dl = elln - ellp
    symT = np.empty((C, R), dtype=np.uint8)
    lignes = np.arange(R)
    for i1 in range(0, C, bloc):
        i2 = min(i1 + bloc, C)
        W1 = WT[i1:i2].copy()
        E1 = np.empty((i2 - i1, R))
        for i in range(i2 - i1):
            col = i1 + i
            w = W1[i]
            neg = np.signbit(w)
            wa = np.abs(w)
            cand = sT[col][:, None] * lev[None, :]
            cout = wa[:, None] - cand
            cout *= cout
            if lam > 0:
                d2 = 1.0 if U is None else U[col, col] ** 2
                cout += (lam * d2) * (ellp[None, :] + neg[:, None] * dl[None, :])
            k = cout.argmin(axis=1)
            symT[col] = k | (neg.astype(np.uint8) << 2)
            if U is not None:
                q = cand[lignes, k]
                err = (wa - q) / U[col, col]
                np.negative(err, out=err, where=neg)
                W1[i:] -= np.outer(U[col, col:i2], err)
                E1[i] = err
        if U is not None and i2 < C:
            WT[i2:] -= U[i1:i2, i2:].T @ E1
    return np.ascontiguousarray(symT.T)


def cout_unitaire(W, What, H):
    """Erreur de sortie moyenne par poids (unités de H) : tr(ΔW H ΔWᵀ) / (R C)."""
    dW = W - What
    if H is None:
        return float((dW * dW).mean())
    return float(np.einsum("ij,jk,ik->", dW, H, dW, optimize=True) / dW.size)


def longueurs(hist):
    p = (hist + 0.5) / (hist + 0.5).sum()
    return -np.log2(p)


# ---------------------------------------------------------------- commandes

def temoins(args):
    m = Modele()
    t0 = time.time()
    # T0 et T2 : la frontière sur les 12 tenseurs entiers.
    C = np.zeros((256, 16))
    num = den = 0.0
    hist = np.zeros(8)
    for l in COUCHES:
        for role in ROLES:
            for e in range(32):
                ex, codes = m.blocs(l, role, e)
                C += comptes(ex, codes)
    centres = centres_ponderes(C, CLASSES2)
    cent_lus = centres[[1, 0, 2, 3]] if args.casser else centres
    for l in COUCHES:
        for role in ROLES:
            for e in range(32):
                ex, codes = m.blocs(l, role, e)
                W = dequant(ex, codes)
                sym = sym_frontiere(codes)
                Wh = reconstruire(ex, sym, cent_lus)
                num += float(((W - Wh) ** 2).sum())
                den += float((W * W).sum())
                hist += np.bincount(sym.ravel(), minlength=8)
    err = num / den
    h0 = entropie(hist)
    T0 = abs(err / ERREUR_07 - 1) < 1e-6
    T2 = abs(h0 - H_BASE_07) < 1e-3
    # T1 : H = I, λ = 0 rend la frontière ; cassure : le H réel en change.
    l, role, e = 8, "up", 4
    ex, codes = m.blocs(l, role, e)
    W = dequant(ex, codes)[0]
    sf = sym_frontiere(codes)[0]
    s_id = choisir(W, ex[0], centres, None, 0.0, np.zeros(8))
    diff_id = int((s_id != sf).sum())
    calib = Entrees("calib", l)
    X, g = calib.expert(e)
    s_h = choisir(W, ex[0], centres, hessienne(X, g, 0.01), 0.0, np.zeros(8))
    diff_h = int((s_h != sf).sum())
    j = {"outil": "synonyme.py temoins", "casser": bool(args.casser),
         "centres_doubles": centres.tolist(), "centres_E2M1": (centres / 2).tolist(),
         "T0_erreur_frontiere_12_tenseurs": err, "T0_attendu_07": ERREUR_07, "T0_tient": bool(T0),
         "T2_H0_symboles_frontiere": h0, "T2_attendu_07": H_BASE_07, "T2_tient": bool(T2),
         "T1_symboles_differents_H_identite": diff_id, "T1_tient": diff_id == 0,
         "T1_cassure_symboles_differents_H_reel": diff_h, "T1_cassure_tombe": diff_h > 0,
         "T1_matrice": f"blk.{l}.ffn_{role}_exps expert {e}", "T1_entrees_calib": int(X.shape[0]),
         "duree_s": time.time() - t0}
    print(json.dumps(j, ensure_ascii=False, indent=1))


def centres_globaux(m):
    chemin = os.path.join(ICI, "centres.json")
    if os.path.exists(chemin):
        return {k: np.array(v) for k, v in json.load(open(chemin, encoding="utf-8")).items()}
    C = np.zeros((256, 16))
    for l in COUCHES:
        for role in ROLES:
            for e in range(32):
                ex, codes = m.blocs(l, role, e)
                C += comptes(ex, codes)
    c = {"2": centres_ponderes(C, CLASSES2), "1": centres_ponderes(C, CLASSES1)}
    json.dump({k: v.tolist() for k, v in c.items()}, open(chemin, "w", encoding="utf-8"), indent=1)
    return c


def symboles_variante(variante, lam, W, ex, codes, centres, H, ell):
    """Rend (sym, centres utilisés, H utilisé pour la normalisation)."""
    if variante == "frontiere":
        return sym_frontiere(codes), centres["2"]
    if variante == "frontiere1":
        return sym_frontiere(codes, CLASSES1), centres["1"]
    if variante == "frontiere0":
        sf = sym_frontiere(codes)
        zero = (codes & 7) == 0
        sh = signe_hache(*codes.shape) << 2
        return np.where(zero, (sf & 3) | sh, sf).astype(np.uint8), centres["2"]
    cl = "1" if variante == "synonyme1" else "2"
    cen = centres[cl]
    Hm = None if variante == "ecsq" else H
    # normalisation : λ est relatif à l'erreur moyenne par poids de la frontière, dans les unités de Hm
    sf = sym_frontiere(codes, CLASSES1 if cl == "1" else CLASSES2)
    # dans `choisir`, la somme des erreurs (w − q)²/U_jj² vaut tr(ΔW H ΔWᵀ) : c en est la moyenne
    # par poids pour la frontière, et λ se lit en « fractions de l'erreur moyenne d'un poids par bit »
    c = cout_unitaire(W, reconstruire(ex, sf, cen), Hm) if lam > 0 else 0.0
    return choisir(W, ex, cen, Hm, lam * c, ell), cen


def mesurer(args):
    m = Modele()
    centres = centres_globaux(m)
    t0 = time.time()
    lignes = []
    hist = {}
    joint = {}
    for l in COUCHES:
        calib, ev = Entrees("calib", l), Entrees("eval", l)
        moitie = ev.h.shape[0] // 2
        for e in EXPERTS:
            te = time.time()
            Ws, Whs, exs, Hs = {}, {}, {}, {}
            Xc, gc = calib.expert(e)
            Xe, ge = ev.expert(e)
            pe, _ = np.nonzero(ev.choix == e)
            b = {r: m.biais(l, r, e) for r in ROLES}
            for role in ROLES:
                ex, codes = m.blocs(l, role, e)
                ex, codes = ex[0], codes[0]
                W = dequant(ex, codes)
                if role == "gate":
                    H = hessienne(Xc, gc, args.damp)
                elif role == "up":
                    pass
                else:
                    A = swiglu(Xc @ Ws["gate"].T + b["gate"], Xc @ Ws["up"].T + b["up"])
                    H = hessienne(A, gc, args.damp)
                cle = (l, role)
                if cle not in hist:
                    # longueurs de code : histogramme frontière du tenseur entier (connu avant)
                    cl = CLASSES1 if args.variante in ("synonyme1", "frontiere1") else CLASSES2
                    hist[cle] = hist_tenseur(m, l, role, cl)
                ell = longueurs(hist[cle])
                if args.variante in ("synonyme1", "frontiere1"):
                    ell = ell[[0, 1, 4, 5]]
                sym, cen = symboles_variante(args.variante, args.lam, W, ex, codes, centres, H, ell)
                Wh = reconstruire(ex, sym, cen)
                Ws[role], Whs[role], exs[role], Hs[role] = W, Wh, ex, H
                kap = kappa(ex)
                cj = joint.setdefault(cle, np.zeros((5, 8, 16)))
                idx = kap.ravel().astype(np.int64) * 128 + sym.ravel().astype(np.int64) * 16 + codes.ravel()
                cj += np.bincount(idx, minlength=5 * 128).reshape(5, 8, 16)
            # erreurs de sortie, entrées d'évaluation tenues à l'écart, pondérées par g²
            A_e = swiglu(Xe @ Ws["gate"].T + b["gate"], Xe @ Ws["up"].T + b["up"])
            Ah_e = swiglu(Xe @ Whs["gate"].T + b["gate"], Xe @ Whs["up"].T + b["up"])
            y = A_e @ Ws["down"].T + b["down"]
            yh = Ah_e @ Whs["down"].T + b["down"]
            w2 = ge * ge
            for role in ROLES:
                W, Wh = Ws[role], Whs[role]
                Xin = A_e if role == "down" else Xe
                num = ((Xin @ (W - Wh).T) ** 2).sum(axis=1)
                den = ((Xin @ W.T) ** 2).sum(axis=1)
                Xc_in = Xc if role != "down" else swiglu(Xc @ Ws["gate"].T + b["gate"], Xc @ Ws["up"].T + b["up"])
                numc = ((Xc_in @ (W - Wh).T) ** 2).sum(axis=1)
                denc = ((Xc_in @ W.T) ** 2).sum(axis=1)
                lignes.append({"couche": l, "expert": e, "role": role,
                               "err_poids": float(((W - Wh) ** 2).sum() / (W * W).sum()),
                               "err_sortie_matrice_eval": float((w2 * num).sum() / (w2 * den).sum()),
                               "err_sortie_matrice_calib": float((gc * gc * numc).sum() / (gc * gc * denc).sum())})
            ne = ((yh - y) ** 2).sum(axis=1)
            de = (y * y).sum(axis=1)
            m1 = pe < moitie
            lignes.append({"couche": l, "expert": e, "role": "expert",
                           "n_calib": int(Xc.shape[0]), "n_eval": int(Xe.shape[0]),
                           "num_eval": float((w2 * ne).sum()), "den_eval": float((w2 * de).sum()),
                           "num_m1": float((w2 * ne)[m1].sum()), "den_m1": float((w2 * de)[m1].sum()),
                           "num_m2": float((w2 * ne)[~m1].sum()), "den_m2": float((w2 * de)[~m1].sum()),
                           "err_sortie_expert_eval": float((w2 * ne).sum() / (w2 * de).sum())})
            print(f"couche {l} expert {e} : {time.time() - te:.1f} s, err expert {lignes[-1]['err_sortie_expert_eval']:.5f}", file=sys.stderr, flush=True)
    # débit
    deb = {}
    for cle, cj in joint.items():
        s = cj.sum(axis=(0, 2))
        h0 = entropie(s)
        hk = sum(cj[k].sum() / cj.sum() * entropie(cj[k].sum(axis=1)) for k in range(5) if cj[k].sum() > 0)
        # complément : H(code | symbole)
        hc = sum(cj[:, a, :].sum() / cj.sum() * entropie(cj[:, a, :].sum(axis=0)) for a in range(8) if cj[:, a, :].sum() > 0)
        hcode = entropie(cj.sum(axis=(0, 1)))
        deb[f"{cle[0]}-{cle[1]}"] = {"poids": float(cj.sum()), "H0_sym": h0, "H_sym_kappa": hk, "H_code_sachant_sym": hc, "H_code": hcode}
    P = sum(v["poids"] for v in deb.values())
    moy = lambda k: sum(v[k] * v["poids"] for v in deb.values()) / P
    ex_l = [r for r in lignes if r["role"] == "expert"]
    agg = lambda a, b, sel: sum(r[a] for r in sel) / sum(r[b] for r in sel)
    par_couche = {str(l): {"m1": agg("num_m1", "den_m1", [r for r in ex_l if r["couche"] == l]),
                           "m2": agg("num_m2", "den_m2", [r for r in ex_l if r["couche"] == l]),
                           "tout": agg("num_eval", "den_eval", [r for r in ex_l if r["couche"] == l])} for l in COUCHES}
    pm = lambda role, k: float(np.mean([r[k] for r in lignes if r["role"] == role]))
    j = {"outil": "synonyme.py mesurer", "variante": args.variante, "lam": args.lam, "damp": args.damp,
         "experts": EXPERTS, "couches": COUCHES,
         "bits_H0_sym": moy("H0_sym"), "bits_H_sym_kappa": moy("H_sym_kappa"),
         "bits_lus_H0_plus_echelles": moy("H0_sym") + SURCOUT_ECHELLES,
         "H_code_sachant_sym": moy("H_code_sachant_sym"), "H_code": moy("H_code"),
         "surcout_raffinement_exact": moy("H0_sym") + moy("H_code_sachant_sym") - moy("H_code"),
         "err_poids": {r: pm(r, "err_poids") for r in ROLES},
         "err_sortie_matrice_eval": {r: pm(r, "err_sortie_matrice_eval") for r in ROLES},
         "err_sortie_matrice_calib": {r: pm(r, "err_sortie_matrice_calib") for r in ROLES},
         "err_sortie_expert_eval": agg("num_eval", "den_eval", ex_l),
         "err_sortie_expert_moities": [agg("num_m1", "den_m1", ex_l), agg("num_m2", "den_m2", ex_l)],
         "err_sortie_expert_par_couche": par_couche,
         "debit_par_tenseur": deb, "duree_s": time.time() - t0}
    if args.csv:
        import csv
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            cles = sorted({k for r in lignes for k in r})
            w = csv.DictWriter(f, fieldnames=cles)
            w.writeheader()
            for r in lignes:
                w.writerow(r)
    print(json.dumps(j, ensure_ascii=False, indent=1))


def ecrire_sym(args):
    m = Modele()
    centres = centres_globaux(m)
    os.makedirs(args.sortie, exist_ok=True)
    couches = [int(c) for c in args.couches.split(",")] if args.couches else list(range(24))
    t0 = time.time()
    for l in couches:
        calib = Entrees("calib", l) if args.variante not in ("frontiere", "frontiere1") else None
        hist = {role: hist_tenseur(m, l, role, CLASSES2) for role in ROLES}
        liste = [int(x) for x in args.experts.split(",")] if args.experts else range(32)
        for e in liste:
            chemin = os.path.join(args.sortie, f"L{l:02d}-E{e:02d}.sym")
            if os.path.exists(chemin):
                continue
            parts = []
            Ws = {}
            cen = centres["2"]
            Xc = gc = None
            if calib is not None:
                Xc, gc = calib.expert(e)
            for role in ROLES:
                ex, codes = m.blocs(l, role, e)
                ex, codes = ex[0], codes[0]
                W = dequant(ex, codes)
                Ws[role] = W
                H = None
                if calib is not None and Xc.shape[0] > 0:
                    if role == "down":
                        b = {r: m.biais(l, r, e) for r in ("gate", "up")}
                        A = swiglu(Xc @ Ws["gate"].T + b["gate"], Xc @ Ws["up"].T + b["up"])
                        H = hessienne(A, gc, args.damp)
                    else:
                        H = hessienne(Xc, gc, args.damp)
                if args.variante == "frontiere" or (H is None and args.variante == "synonyme"):
                    sym = sym_frontiere(codes)
                else:
                    sym, cen = symboles_variante(args.variante, args.lam, W, ex, codes, centres, H, longueurs(hist[role]))
                flat = sym.ravel()
                parts.append((flat[0::2] | (flat[1::2] << 4)).astype(np.uint8).tobytes())
            with open(chemin + ".tmp", "wb") as f:
                f.write(b"SYM1")
                f.write(np.asarray(cen, dtype="<f8").tobytes())
                for p in parts:
                    f.write(p)
            os.replace(chemin + ".tmp", chemin)
        print(f"couche {l} : {time.time() - t0:.0f} s", file=sys.stderr, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("commande", choices=["temoins", "mesurer", "ecrire-sym"])
    ap.add_argument("--casser", action="store_true")
    ap.add_argument("--variante", default="frontiere", choices=["frontiere", "frontiere0", "frontiere1", "ecsq", "synonyme", "synonyme1"])
    ap.add_argument("--lam", type=float, default=0.0)
    ap.add_argument("--damp", type=float, default=0.01)
    ap.add_argument("--csv", default=None)
    ap.add_argument("--sortie", default=None)
    ap.add_argument("--couches", default=None)
    ap.add_argument("--experts", default=None)
    a = ap.parse_args()
    {"temoins": temoins, "mesurer": mesurer, "ecrire-sym": ecrire_sym}[a.commande](a)


if __name__ == "__main__":
    main()
