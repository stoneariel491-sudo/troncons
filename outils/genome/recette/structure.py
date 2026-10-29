"""Où est le bruit, où est la structure : trois mesures sur les experts MXFP4 réels de gpt-oss-20b.

1. Spectre : valeurs singulières d'une matrice d'expert (2 880 × 2 880) ; part de l'énergie portée par
   les r premières directions, comparée à la même matrice dont les entrées sont permutées au hasard
   (témoin : la permutation détruit toute structure de rang ; si le spectre réel égale celui de la
   matrice permutée, il n'y a pas de rang faible à exploiter).
2. Dispersion des énergies de rangée : le gain d'allocation de la remplissage inverse (« reverse
   water-filling ») à haut débit vaut ½ log₂(moyenne arithmétique / moyenne géométrique) des variances
   de rangée, en bits par poids (calculé, borne pour une source gaussienne par rangée).
3. La borne de Shannon de la source « gaussienne par rangée » : débit minimal pour atteindre l'erreur
   relative D par remplissage inverse sur les rangées de l'échantillon (CSV de `codons`), à comparer
   à la base (2,64 bits) et à la recette mesurée.

Utilisation :
  python -I -X utf8 structure.py spectre > spectre.json
  python -I -X utf8 structure.py borne CSV ERREUR > borne.json
"""
from __future__ import annotations

import importlib.util
import json
import math
import os
import sys

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
LECTEUR = os.path.join(ICI, "..", "..", "03-entropie", "gguf_lecture.py")
FICHIER = "~/dev/modeles/gguf/gpt-oss-20b-MXFP4.gguf"
COUCHES = (0, 8, 16, 23)
ROLES = ("ffn_gate_exps", "ffn_up_exps", "ffn_down_exps")
K = np.array([0, 1, 2, 3, 4, 6, 8, 12, 0, -1, -2, -3, -4, -6, -8, -12], dtype=np.float64)


def charger_lecteur():
    spec = importlib.util.spec_from_file_location("gguf_lecture", LECTEUR)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gguf_lecture"] = mod
    spec.loader.exec_module(mod)
    return mod


def expert(lec, t, e: int) -> np.ndarray:
    """L'expert e du tenseur t, en f64 exact (lignes × colonnes)."""
    colonnes, lignes, ne = t.dims
    o = np.asarray(lec.octets(t))
    tranche = o.size // ne
    b = o[e * tranche:(e + 1) * tranche].reshape(-1, 17)
    ech = np.ldexp(1.0, b[:, 0].astype(np.int64) - 128)
    qs = b[:, 1:]
    codes = np.concatenate([qs & 15, qs >> 4], axis=1)
    w = K[codes] * ech[:, None]
    return w.reshape(lignes, colonnes)


def part_energie(s: np.ndarray, rangs) -> dict:
    e = s ** 2
    c = np.cumsum(e) / e.sum()
    return {str(r): float(c[r - 1]) for r in rangs}


def spectre():
    mod = charger_lecteur()
    lec = mod.LecteurGGUF(FICHIER)
    index = {t.nom: t for t in lec.tenseurs}
    rng = np.random.default_rng(20261016)
    rangs = (1, 8, 29, 144, 288, 720, 1440)
    sortie = []
    for c in COUCHES:
        for r in ROLES:
            t = index[f"blk.{c}.{r}.weight"]
            w = expert(lec, t, 0)
            s = np.linalg.svd(w, compute_uv=False)
            wp = rng.permutation(w.ravel()).reshape(w.shape)
            sp = np.linalg.svd(wp, compute_uv=False)
            # énergie des rangées : dispersion (gain d'allocation à haut débit)
            er = (w ** 2).mean(axis=1)
            er = er[er > 0]
            gain_alloc = 0.5 * math.log2(er.mean() / math.exp(np.log(er).mean()))
            # dispersion des colonnes (ce qu'une rotation le long des rangées mélange)
            ec = (w ** 2).mean(axis=0)
            gain_col = 0.5 * math.log2(ec.mean() / math.exp(np.log(ec).mean()))
            ligne = {
                "tenseur": t.nom, "expert": 0,
                "part_energie_reel": part_energie(s, rangs),
                "part_energie_permute": part_energie(sp, rangs),
                "sigma_max_sur_moyen": float(s[0] / np.sqrt((s ** 2).mean())),
                "sigma_max_sur_moyen_permute": float(sp[0] / np.sqrt((sp ** 2).mean())),
                "gain_allocation_rangees_bits": gain_alloc,
                "gain_allocation_colonnes_bits": gain_col,
                "kurtosis": float(((w - w.mean()) ** 4).mean() / w.var() ** 2),
            }
            sortie.append(ligne)
            print(json.dumps(ligne), file=sys.stderr)
    print(json.dumps({"rangs": rangs, "tenseurs": sortie}, indent=1))


def borne(csv: str, cible: float):
    """Débit minimal (Shannon, gaussienne par rangée, remplissage inverse) pour l'erreur relative cible."""
    import csv as _csv
    par_t: dict[str, list[float]] = {}
    with open(csv, newline="", encoding="utf8") as f:
        for ligne in _csv.DictReader(f):
            par_t.setdefault(ligne["tenseur"], []).append(float(ligne["energie"]))
    sortie = {}
    tout = []
    for nom, en in par_t.items():
        v = np.array(en) / 2880.0  # variance par poids de chaque rangée
        tout.append(v)
        sortie[nom] = debit_remplissage(v, cible)
    sortie["global"] = debit_remplissage(np.concatenate(tout), cible)
    sortie["global_sans_allocation"] = 0.5 * math.log2(1.0 / cible)
    print(json.dumps({"csv": csv, "erreur_cible": cible, "bits_par_poids": sortie}, indent=1))


def debit_remplissage(v: np.ndarray, cible: float) -> float:
    """Remplissage inverse : D_i = min(θ, v_i), Σ D_i = cible · Σ v_i ; R = moyenne de ½ log₂(v_i / D_i)."""
    total = cible * v.sum()
    lo, hi = 0.0, float(v.max())
    for _ in range(200):
        th = 0.5 * (lo + hi)
        if np.minimum(th, v).sum() > total:
            hi = th
        else:
            lo = th
    d = np.minimum(lo, v)
    return float(np.mean(0.5 * np.log2(v / d)))


if __name__ == "__main__":
    if sys.argv[1] == "spectre":
        spectre()
    elif sys.argv[1] == "borne":
        borne(sys.argv[2], float(sys.argv[3]))
