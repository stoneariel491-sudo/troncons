"""Second chemin du lot B (génome synonyme) : relire les fichiers .sym et recalculer, sans le code
qui les a écrits, ce que l'éclaireur a publié ; puis le débit des 72 tenseurs.

Écrit de zéro pour troncons, rôle « synonyme » de la construction, le 2026-10-17. Ne réutilise ni
`choisir`, ni `reconstruire`, ni `dequant` de outils/genome/eclaireur/synonyme.py : seul le lecteur
GGUF de 03 (outils/03-entropie/gguf_lecture.py) est partagé, parce qu'il ne fait que donner les
octets bruts.

LE FICHIER .sym (écrit par `synonyme.py ecrire-sym`) : « SYM1 », 4 centres f64 (grandeurs E2M1
doublées, celles de ggml), puis pour gate, up, down les R·C symboles d'une matrice 2 880 × 2 880,
deux par octet (le symbole d'indice pair dans le demi-octet faible). Un symbole : bits 0-1 la classe
k, bit 2 le signe négatif. Valeur servie : ±centre[k] · 2^(e − 128), e l'exposant E8M0 du bloc de
32 poids de la ligne (même convention de grandeurs doublées que ggml : MAG = 0, 1, 2, 3, 4, 6, 8, 12).

COMMANDES
  verifier [--casser]   W2 (seuil déclaré dans mesures/genome/construction/synonyme/00-seuils-declares.md) :
                        experts 0, 8, 16, 24 des couches 0, 8, 16, 23 ; erreur relative sur les
                        poids de chaque matrice et erreur de sortie d'expert sur l'évaluation
                        (fenêtres 0-9, pondérées par g²), comparées au CSV de l'éclaireur à 1e-9
                        relatif. --casser : le bit de classe 0 de la ligne 0 de gate est inversé
                        avant la reconstruction ; le témoin doit tomber.
  debit --dossier D [--dossier2 D2] [--csv comptes.csv]
                        H0 et H(symbole | κ) des symboles par tenseur (24 couches × 3 rôles, les
                        32 experts), moyennés à poids égal ; κ = e − médiane des e de la ligne,
                        borné à [−3, 1] (définition de l'éclaireur, 01 § 5.3).
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import sys
import time

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", "..", ".."))
GGUF = "~/dev/modeles/gguf/gpt-oss-20b-MXFP4.gguf"
EVAL = "~/dev/essais/troncons/genome/eclaireur/eval"
SYM = "~/dev/essais/troncons/genome/synonyme/sym"
CSV_ECLAIREUR = os.path.join(RACINE, "mesures/genome/etat-de-l-art/passes/synonyme-lam1-damp1-e0_8_16_24.csv")
N = 2880
NB = N // 32
ROLES = ("gate", "up", "down")
MAG2 = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0])


def lecteur():
    spec = importlib.util.spec_from_file_location("gguf_lecture", os.path.join(RACINE, "outils/03-entropie/gguf_lecture.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gguf_lecture"] = mod
    spec.loader.exec_module(mod)
    lec = mod.LecteurGGUF(GGUF)
    return lec, {t.nom: t for t in lec.tenseurs}


def octets_expert(lec, tens, couche, role, e):
    """Les 2 880 × 90 blocs [e, 16 octets] de l'expert e : (exposants (R, NB), qs (R, NB, 16))."""
    t = tens[f"blk.{couche}.ffn_{role}_exps.weight"]
    o = np.asarray(lec.octets(t)).reshape(t.dims[2], N, NB, 17)[e]
    return o[..., 0].astype(np.int32), o[..., 1:]


def matrice_exacte(ex, qs):
    """Déquantification MXFP4, écrite ici : poids t du bloc dans le demi-octet faible de l'octet t,
    poids 16 + t dans le fort."""
    codes = np.concatenate([qs & 15, qs >> 4], axis=-1)            # (R, NB, 32)
    v = MAG2[codes & 7] * np.ldexp(1.0, ex - 128)[..., None]
    v[(codes & 8) != 0] *= -1.0
    return v.reshape(N, N)


def lire_sym(chemin):
    o = np.fromfile(chemin, dtype=np.uint8)
    if bytes(o[:4]) != b"SYM1":
        raise ValueError(f"{chemin} : magie")
    centres = o[4:36].view("<f8").copy()
    corps = o[36:]
    if corps.size != 3 * N * N // 2:
        raise ValueError(f"{chemin} : taille {corps.size}")
    mats = []
    for j in range(3):
        b = corps[j * N * N // 2:(j + 1) * N * N // 2]
        s = np.empty(N * N, dtype=np.uint8)
        s[0::2] = b & 15
        s[1::2] = b >> 4
        mats.append(s.reshape(N, N))
    return centres, mats


def matrice_base(ex, sym, centres):
    v = centres[sym & 3] * np.repeat(np.ldexp(1.0, ex - 128), 32, axis=1)
    return np.where((sym & 4) != 0, -v, v)


def biais(lec, tens, couche, role, e):
    t = tens[f"blk.{couche}.ffn_{role}_exps.bias"]
    return np.asarray(lec.octets(t)).view(np.float32).reshape(t.dims[1], t.dims[0])[e].astype(np.float64)


def activation(g, u):
    """SwiGLU de gpt-oss : porte bornée à 7, linéaire bornée à ±7, α = 1,702, + 1 sur la linéaire."""
    g = np.minimum(g, 7.0)
    u = np.clip(u, -7.0, 7.0)
    return g * (1.0 / (1.0 + np.exp(-1.702 * g))) * (u + 1.0)


def entrees_eval(couche, e):
    h = np.memmap(os.path.join(EVAL, f"h-L{couche:02d}.f32"), dtype=np.float32, mode="r").reshape(-1, N)
    r = np.fromfile(os.path.join(EVAL, f"routage-L{couche:02d}.bin"), dtype=np.uint8).reshape(-1, 20)
    choix, poids = r[:, :4], r[:, 4:].copy().view(np.float32).reshape(-1, 4)
    p, j = np.nonzero(choix == e)
    return np.asarray(h[p], dtype=np.float64), poids[p, j].astype(np.float64)


def verifier(a):
    lec, tens = lecteur()
    ref = {}
    with open(CSV_ECLAIREUR, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            ref[(int(r["couche"]), int(r["expert"]), r["role"])] = r
    t0 = time.time()
    lignes, pire = [], 0.0
    for couche in (0, 8, 16, 23):
        for e in (0, 8, 16, 24):
            centres, syms = lire_sym(os.path.join(SYM, "synonyme-l1-d1", f"L{couche:02d}-E{e:02d}.sym"))
            if a.casser and couche == 0 and e == 0:
                syms[0] = syms[0].copy()
                syms[0][0] ^= 1
            W, Wb = {}, {}
            for j, role in enumerate(ROLES):
                ex, qs = octets_expert(lec, tens, couche, role, e)
                W[role] = matrice_exacte(ex, qs)
                Wb[role] = matrice_base(ex, syms[j], centres)
                ep = float(((W[role] - Wb[role]) ** 2).sum() / (W[role] ** 2).sum())
                attendu = float(ref[(couche, e, role)]["err_poids"])
                ecart = abs(ep / attendu - 1)
                pire = max(pire, ecart)
                lignes.append({"couche": couche, "expert": e, "role": role, "err_poids": ep, "eclaireur": attendu, "ecart_relatif": ecart})
            X, g = entrees_eval(couche, e)
            b = {r: biais(lec, tens, couche, r, e) for r in ROLES}
            y = activation(X @ W["gate"].T + b["gate"], X @ W["up"].T + b["up"]) @ W["down"].T + b["down"]
            yb = activation(X @ Wb["gate"].T + b["gate"], X @ Wb["up"].T + b["up"]) @ Wb["down"].T + b["down"]
            w2 = g * g
            es = float((w2 * ((yb - y) ** 2).sum(axis=1)).sum() / (w2 * (y * y).sum(axis=1)).sum())
            attendu = float(ref[(couche, e, "expert")]["err_sortie_expert_eval"])
            ecart = abs(es / attendu - 1)
            pire = max(pire, ecart)
            lignes.append({"couche": couche, "expert": e, "role": "expert", "err_sortie_expert_eval": es, "eclaireur": attendu, "ecart_relatif": ecart})
            print(f"L{couche} E{e} : sortie {es:.6f} contre {attendu:.6f}", file=sys.stderr, flush=True)
    tient = pire < 1e-9
    print(json.dumps({"outil": "verifier_sym.py verifier", "casser": bool(a.casser),
                      "seuil_declare": "toutes les erreurs égales au CSV de l'éclaireur à 1e-9 relatif",
                      "ecart_relatif_max": pire, "tient": bool(tient), "lignes": lignes,
                      "duree_s": time.time() - t0}, ensure_ascii=False, indent=1))


def entropie(n):
    n = n[n > 0]
    p = n / n.sum()
    return float(-(p * np.log2(p)).sum())


def kappa_blocs(ex):
    med = np.median(ex, axis=1, keepdims=True).astype(np.int32)   # même définition que l'éclaireur
    return np.clip(ex - med, -3, 1) + 3                              # (R, NB) dans [0, 4]


def debit(a):
    lec, tens = lecteur()
    dossiers = [a.dossier] + ([a.dossier2] if a.dossier2 else [])
    res = {d: {} for d in dossiers}
    t0 = time.time()
    for couche in range(24):
        joint = {d: {r: np.zeros((5, 8)) for r in ROLES} for d in dossiers}
        for e in range(32):
            kap = {r: np.repeat(kappa_blocs(octets_expert(lec, tens, couche, r, e)[0]), 32, axis=1) for r in ROLES}
            for d in dossiers:
                _, syms = lire_sym(os.path.join(SYM, d, f"L{couche:02d}-E{e:02d}.sym"))
                for j, r in enumerate(ROLES):
                    idx = kap[r].ravel().astype(np.int64) * 8 + syms[j].ravel()
                    joint[d][r] += np.bincount(idx, minlength=40).reshape(5, 8)
        for d in dossiers:
            for r in ROLES:
                cj = joint[d][r]
                h0 = entropie(cj.sum(axis=0))
                hk = sum(cj[k].sum() / cj.sum() * entropie(cj[k]) for k in range(5) if cj[k].sum() > 0)
                res[d][f"{couche}-{r}"] = {"H0": h0, "H_kappa": hk, "histogramme": cj.sum(axis=0).tolist(), "joint_kappa_symbole": cj.tolist()}
        print(f"couche {couche} : {time.time() - t0:.0f} s", file=sys.stderr, flush=True)
    sortie = {"outil": "verifier_sym.py debit", "duree_s": time.time() - t0}
    for d in dossiers:
        v = res[d]
        sortie[d] = {"H0_moyen": float(np.mean([x["H0"] for x in v.values()])),
                     "H_kappa_moyen": float(np.mean([x["H_kappa"] for x in v.values()])),
                     "par_tenseur": v}
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["variante", "couche", "role", "kappa", "symbole", "compte"])
            for d in dossiers:
                for cle, v in res[d].items():
                    couche, r = cle.split("-")
                    for k in range(5):
                        for sy in range(8):
                            w.writerow([d, couche, r, k, sy, int(v["joint_kappa_symbole"][k][sy])])
    print(json.dumps(sortie, ensure_ascii=False, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("commande", choices=["verifier", "debit"])
    ap.add_argument("--casser", action="store_true")
    ap.add_argument("--dossier", default="synonyme-l1-d1")
    ap.add_argument("--dossier2", default=None)
    ap.add_argument("--csv", default=None)
    a = ap.parse_args()
    {"verifier": verifier, "debit": debit}[a.commande](a)


if __name__ == "__main__":
    main()
