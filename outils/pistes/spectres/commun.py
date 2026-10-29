"""Piste spectres : ce que partagent les outils (priorité, garde du verrou, lecture des matrices).

Règles de cohabitation (consigne du 2026-10-21) : pas de carte graphique, priorité « sous la
normale », 2 fils BLAS au plus, pause pendant une séance de vitesse de l'autre flux. Ce module doit
être importé AVANT numpy : il pose les variables de fils.
"""
from __future__ import annotations

import ctypes
import importlib.util
import os
import sys
import time

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_v] = "2"

import numpy as np  # noqa: E402

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", "..", ".."))
LECTEUR = os.path.join(RACINE, "outils", "03-entropie", "gguf_lecture.py")
FICHIER = "~/dev/modeles/gguf/gpt-oss-20b-MXFP4.gguf"
VERROU = "~/dev/verrou-carte.txt"
MESURES = os.path.join(RACINE, "mesures", "pistes", "spectres")

GRAINE = 20261021
COUCHES = (0, 12, 23)
ROLES_EXPERTS = ("ffn_gate_exps", "ffn_up_exps", "ffn_down_exps")
ROLES_ATTENTION = ("attn_q", "attn_k", "attn_v", "attn_output")

# E2M1 doublé (la table de structure.py) : l'échelle s'écrit alors 2^(e − 128).
K = np.array([0, 1, 2, 3, 4, 6, 8, 12, 0, -1, -2, -3, -4, -6, -8, -12], dtype=np.float64)


def priorite_basse() -> None:
    """Classe « sous la normale » pour ce processus (Windows), sans rien toucher d'autre."""
    if sys.platform == "win32":
        BELOW_NORMAL = 0x00004000
        h = ctypes.windll.kernel32.GetCurrentProcess()
        ctypes.windll.kernel32.SetPriorityClass(h, BELOW_NORMAL)


def seance_de_vitesse() -> bool:
    """Vrai si le verrou de la carte a moins de 2 h et nomme une séance de vitesse."""
    try:
        if time.time() - os.path.getmtime(VERROU) > 2 * 3600:
            return False
        with open(VERROU, encoding="utf8", errors="replace") as f:
            texte = f.read().lower()
    except OSError:
        return False
    # (version 1 : le simple mot « vitesse » ; faux positif le 2026-10-22 à 04:46 sur un verrou du juge
    # qui écrivait « pas une séance de vitesse »)
    texte = texte.replace("pas une séance de vitesse", "")
    return any(m in texte for m in ("vitesse", "abba", "j1"))


def processus_ancien_actif() -> bool:
    """Vrai si le fichier nommé par TRONCONS_ATTENDRE_ACTIF a été écrit il y a moins de 3 min.

    Sert à ne jamais tourner en même temps qu'un ancien processus de cette piste qu'on ne peut pas
    arrêter (levier v1 du 2026-10-22, qui écrit une ligne par matrice) : 2 fils au plus au total.
    """
    chemin = os.environ.get("TRONCONS_ATTENDRE_ACTIF")
    if not chemin:
        return False
    try:
        return time.time() - os.path.getmtime(chemin) < 180
    except OSError:
        return False


def attendre_calme(journal=sys.stderr) -> None:
    """Met en pause tant qu'une séance de vitesse est en cours (ou qu'un ancien processus écrit)."""
    annonce = False
    while seance_de_vitesse() or processus_ancien_actif():
        if not annonce:
            print(f"[pause] séance de vitesse en cours ({time.strftime('%H:%M:%S')})", file=journal, flush=True)
            annonce = True
        time.sleep(60)
    if annonce:
        print(f"[reprise] {time.strftime('%H:%M:%S')}", file=journal, flush=True)


def lecteur():
    spec = importlib.util.spec_from_file_location("gguf_lecture", LECTEUR)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gguf_lecture"] = mod
    spec.loader.exec_module(mod)
    return mod.LecteurGGUF(FICHIER)


def tirer_experts() -> dict[int, list[int]]:
    """Le tirage déclaré (seuil.md § 1) : 4 experts distincts par couche, couches dans l'ordre."""
    rng = np.random.default_rng(GRAINE)
    return {c: sorted(int(e) for e in rng.choice(32, 4, replace=False)) for c in COUCHES}


def echantillon() -> list[dict]:
    """Les 48 matrices de l'échantillon, dans un ordre fixe."""
    ex = tirer_experts()
    sortie = []
    for c in COUCHES:
        for r in ROLES_EXPERTS:
            for e in ex[c]:
                sortie.append({"id": f"L{c:02d}.{r.split('_')[1]}.E{e:02d}", "couche": c,
                               "role": r.split("_")[1], "tenseur": f"blk.{c}.{r}.weight", "expert": e})
        for r in ROLES_ATTENTION:
            court = r.split("_")[1]
            sortie.append({"id": f"L{c:02d}.attn_{court}", "couche": c, "role": f"attn_{court}",
                           "tenseur": f"blk.{c}.{r}.weight", "expert": -1})
    return sortie


def matrice_mxfp4(lec, t, e: int) -> np.ndarray:
    """L'expert e d'un tenseur MXFP4, f64 exact, (lignes × colonnes) — chemin de structure.py."""
    colonnes, lignes, ne = t.dims
    o = np.asarray(lec.octets(t))
    tranche = o.size // ne
    b = o[e * tranche:(e + 1) * tranche].reshape(-1, 17)
    ech = np.ldexp(1.0, b[:, 0].astype(np.int64) - 128)
    qs = b[:, 1:]
    codes = np.concatenate([qs & 15, qs >> 4], axis=1)
    return (K[codes] * ech[:, None]).reshape(lignes, colonnes)


def codes_mxfp4(lec, t, e: int):
    """Codes de 4 bits (lignes × colonnes) et exposant E8M0 de chaque bloc (lignes × colonnes/32)."""
    colonnes, lignes, ne = t.dims
    o = np.asarray(lec.octets(t))
    tranche = o.size // ne
    b = o[e * tranche:(e + 1) * tranche].reshape(-1, 17)
    qs = b[:, 1:]
    codes = np.concatenate([qs & 15, qs >> 4], axis=1).reshape(lignes, colonnes)
    return codes.astype(np.uint8), b[:, 0].reshape(lignes, colonnes // 32).astype(np.int64)


def matrice_q8_0(lec, t) -> np.ndarray:
    """Tenseur Q8_0 (bloc : f16 d, 32 × int8), f64 exact, (lignes × colonnes)."""
    colonnes, lignes = t.dims
    o = np.asarray(lec.octets(t)).reshape(-1, 34)
    d = o[:, :2].copy().view(np.float16).astype(np.float64)
    q = o[:, 2:].copy().view(np.int8).astype(np.float64)
    return (q * d).reshape(lignes, colonnes)


def matrice(lec, index, m: dict) -> np.ndarray:
    t = index[m["tenseur"]]
    if m["expert"] >= 0:
        return matrice_mxfp4(lec, t, m["expert"])
    return matrice_q8_0(lec, t)
