"""Juge indépendant de la garde à indices multiples (la mémoire du conflit).

Refait le chiffre principal de genome/pistes/tropicale/seuil-declare-indices.md (b(M0), b(M3), le gain,
son IC, les fenêtres positives) par un chemin écrit à partir de la seule déclaration, sans une ligne de
indices.py, second_chemin_indices.py, indices_complements.py ni bascules.py.

Ce qui diffère du chemin de la piste (autant que la déclaration le permet) :
- lecture des journaux par numpy.frombuffer sur un type structuré (4 × u8, f32), après vérification des
  empreintes SHA-256 déclarées dans seuil-declare.md § 1 ;
- indices calculés sur des tableaux (couche, fenêtre, position) : f2 par minimum cumulé décalé, f4 par
  sommes cumulées en deux dimensions (couches, puis positions), et vérifiés contre une boucle explicite
  sur un échantillon de cellules ;
- régression logistique par Newton exact (hessienne pleine, 7 inconnues au plus), pénalité 1/2 · ||w||²
  sur les poids (constante non pénalisée), indices centrés réduits sur l'entraînement ; une variante sans
  pénalité est rapportée pour montrer que la convention de « pénalité L2 de 1 » ne change pas le verdict ;
- dans chaque fenêtre de test on garde les k premières cellules du classement par score décroissant,
  ex aequo départagés par l'indice de cellule (ℓ, p) ; k = floor(0,1 × 12 264) = 1 226, et k = 1 227 en
  sensibilité ;
- IC : 10 000 tirages avec remise des dix fenêtres, numpy.random.default_rng(20261026), gain = rapport des
  sommes rééchantillonnées.

Témoins du juge (chacun doit pouvoir tomber) :
- J-W4 : étiquettes mélangées à l'entraînement, M3 doit tomber vers 10 % ;
- J-W2 : f2, f3, f4 permutés dans chaque couche, le gain doit tomber vers 0 ;
- J-OR : un indice oracle (bascule vérifiée en (ℓ − 1, p)) doit faire monter b nettement ;
- J-ID : M1 (f1 seul) doit redonner M0 à l'unité.

Cohabitation : priorité « sous la normale », un fil (variables posées avant numpy), aucune carte, aucun
verrou pris ; si le verrou de la carte annonce une séance de vitesse, le script attend sa fin.
"""

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_v] = "1"

import ctypes
import hashlib
import json
import sys
import time

import numpy as np

RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
ROUTAGE = os.path.join(RACINE, "mesures", "moteur", "R", "r1", "routage")
JOURNAUX = {
    "A": ("ref-openai-bis-20b.bin", "f0a19c1182a3db507c7ade3d49734f765372bd6d1e101e3f4d0cb9be785b8d3c"),
    "B": ("ref-llamacpp-bis-20b.bin", "07a9d4f974fd00ea8e56330865021f139025741fd63afe5b45c562336fd549d0"),
}
SORTIE = os.path.join(RACINE, "mesures", "pistes", "tropicale", "juge")
VERROU = r"~\dev\verrou-carte.txt"
TAU10 = 0.01241
NF, NP = 10, 511
GRAINE = 20261026


def sous_la_normale():
    if os.name == "nt":
        k32 = ctypes.windll.kernel32
        k32.SetPriorityClass(k32.GetCurrentProcess(), 0x00004000)


def attendre_verrou():
    while os.path.exists(VERROU):
        try:
            texte = open(VERROU, encoding="utf-8", errors="replace").read().lower()
        except OSError:
            texte = ""
        if not any(m in texte for m in ("abba", "j1", "vitesse")):
            return
        print("verrou de la carte : séance de vitesse en cours, attente", flush=True)
        time.sleep(30)


def lire(nom, empreinte):
    brut = open(os.path.join(ROUTAGE, nom), "rb").read()
    h = hashlib.sha256(brut).hexdigest()
    if h != empreinte:
        raise SystemExit(f"empreinte fausse pour {nom} : {h}")
    nl, npos = np.frombuffer(brut[:8], dtype="<u4")
    t = np.dtype([("e", "u1", (4,)), ("m", "<f4")])
    if len(brut) != 8 + int(nl) * int(npos) * t.itemsize:
        raise SystemExit("taille incohérente")
    c = np.frombuffer(brut[8:], dtype=t).reshape(int(nl), int(npos))
    return int(nl), int(npos), c["e"], c["m"].astype(np.float64)


def indices(mB, nl):
    """mB de forme (nl, NF, NP). Rend f1..f5 de même forme."""
    lm = np.log(mB)
    f1 = lm
    # f2 : ln du minimum des marges aux couches strictement plus basses, même position ; 0 en ℓ = 0
    cummin = np.minimum.accumulate(mB, axis=0)
    f2 = np.zeros_like(lm)
    f2[1:] = np.log(cummin[:-1])
    # f3 : ln de la marge en (ℓ, p − 1), même fenêtre ; 0 en p = 0
    f3 = np.zeros_like(lm)
    f3[:, :, 1:] = lm[:, :, :-1]
    # f4 : part des cellules ℓ' ≤ ℓ, p − 8 ≤ p' ≤ p − 1 sous τ₁₀
    bas = (mB < TAU10).astype(np.float64)
    cl = np.cumsum(bas, axis=0)  # somme sur ℓ' ≤ ℓ
    cp = np.concatenate([np.zeros((nl, NF, 1)), np.cumsum(cl, axis=2)], axis=2)  # cp[..., j] = somme p' < j
    p = np.arange(NP)
    debut = np.maximum(p - 8, 0)
    num = cp[:, :, p] - cp[:, :, debut]
    nb_pos = (p - debut).astype(np.float64)
    den = (np.arange(nl)[:, None, None] + 1.0) * nb_pos[None, None, :]
    f4 = np.where(den > 0, num / np.where(den > 0, den, 1.0), 0.0)
    f5 = np.broadcast_to((np.arange(nl) / 23.0)[:, None, None], lm.shape).copy()
    return f1, f2, f3, f4, f5


def verifier_indices(mB, F, nl, n=4000):
    """Boucle explicite sur un échantillon de cellules : doit redonner f2, f3, f4."""
    rng = np.random.default_rng(1)
    pire = 0.0
    for _ in range(n):
        l, w, p = int(rng.integers(nl)), int(rng.integers(NF)), int(rng.integers(NP))
        f2 = 0.0 if l == 0 else float(np.log(min(mB[q, w, p] for q in range(l))))
        f3 = 0.0 if p == 0 else float(np.log(mB[l, w, p - 1]))
        ens = [(q, r) for q in range(l + 1) for r in range(max(p - 8, 0), p)]
        f4 = 0.0 if not ens else sum(1 for q, r in ens if mB[q, w, r] < TAU10) / len(ens)
        for v, f in ((f2, F[1]), (f3, F[2]), (f4, F[3])):
            pire = max(pire, abs(v - float(f[l, w, p])))
    return pire


def newton(X, y, lam):
    """Logistique : min somme log-perte + lam/2 ||w||² (constante libre), Newton exact."""
    n, d = X.shape
    Xc = np.hstack([np.ones((n, 1)), X])
    w = np.zeros(d + 1)
    P = np.eye(d + 1) * lam
    P[0, 0] = 0.0
    for it in range(100):
        z = Xc @ w
        pr = 1.0 / (1.0 + np.exp(-z))
        g = Xc.T @ (pr - y) + P @ w
        H = (Xc * (pr * (1 - pr))[:, None]).T @ Xc + P
        pas = np.linalg.solve(H, g)
        w -= pas
        if np.max(np.abs(pas)) < 1e-10:
            break
    return w


def colonnes(F, nom):
    f1, f2, f3, f4, f5 = F
    if nom == "M1":
        return [f1]
    if nom == "M2":
        return [f1, f5, f1 * f5]
    if nom == "M3":
        return [f1, f2, f3, f4, f5, f1 * f5]
    raise ValueError(nom)


def attrapees(score, y, ident, k):
    """k premières cellules par score décroissant, ex aequo départagés par l'indice croissant."""
    ordre = np.lexsort((ident, -score))
    return int(y[ordre[:k]].sum())


def plis(F, Y, ident, nom, k, lam=1.0, melange=None):
    """Rend la liste des bascules attrapées par fenêtre de test."""
    cols = colonnes(F, nom)
    nl = Y.shape[0]
    out = []
    for t in range(NF):
        tr = [w for w in range(NF) if w != t]
        Xtr = np.stack([c[:, tr, :].ravel() for c in cols], axis=1)
        ytr = Y[:, tr, :].ravel().astype(np.float64)
        if melange is not None:
            ytr = melange.permutation(ytr)
        mu, sd = Xtr.mean(0), Xtr.std(0)
        sd[sd == 0] = 1.0
        w = newton((Xtr - mu) / sd, ytr, lam)
        Xte = np.stack([c[:, t, :].ravel() for c in cols], axis=1)
        s = np.hstack([np.ones((Xte.shape[0], 1)), (Xte - mu) / sd]) @ w
        out.append(attrapees(s, Y[:, t, :].ravel(), ident[:, t, :].ravel(), k))
    return out


def m0(mB, Y, ident, k):
    return [attrapees(-mB[:, t, :].ravel(), Y[:, t, :].ravel(), ident[:, t, :].ravel(), k) for t in range(NF)]


def ic_gain(a, b, nb):
    a, b, nb = map(np.asarray, (a, b, nb))
    rng = np.random.default_rng(GRAINE)
    idx = rng.integers(0, NF, size=(10000, NF))
    g = 100.0 * (a[idx].sum(1) - b[idx].sum(1)) / nb[idx].sum(1)
    return [float(np.percentile(g, 2.5)), float(np.percentile(g, 97.5))]


def resume(nom, att, ref, nb):
    tot = sum(nb)
    d = [x - y for x, y in zip(att, ref)]
    return {
        "modele": nom,
        "par_fenetre": att,
        "attrapees": sum(att),
        "b_pct": 100.0 * sum(att) / tot,
        "gain_points": 100.0 * (sum(att) - sum(ref)) / tot,
        "ic95": ic_gain(att, ref, nb),
        "fenetres_positives": sum(1 for x in d if x > 0),
        "ecarts_par_fenetre": d,
    }


def main():
    sous_la_normale()
    attendre_verrou()
    t0 = time.time()
    nl, npos, eA, mA = lire(*JOURNAUX["A"])
    nl2, npos2, eB, mB_plat = lire(*JOURNAUX["B"])
    assert (nl, npos) == (nl2, npos2) == (24, NF * NP)
    bascule = np.any(np.sort(eA, axis=2) != np.sort(eB, axis=2), axis=2)  # (nl, npos)
    Y = bascule.reshape(nl, NF, NP).astype(np.int64)
    mB = mB_plat.reshape(nl, NF, NP)
    ident = (np.arange(nl)[:, None, None] * npos + np.arange(npos).reshape(NF, NP)[None]).astype(np.int64)
    nb = [int(Y[:, t, :].sum()) for t in range(NF)]
    assert (mB > 0).all(), "marge nulle ou négative : ln indéfini"
    F = indices(mB, nl)
    ecart_boucle = verifier_indices(mB, F, nl)
    tau10_mesure = float(np.quantile(mB_plat.ravel(), 0.10))

    res = {"bascules": int(Y.sum()), "bascules_par_fenetre": nb, "ecart_boucle_indices": ecart_boucle,
           "tau10_recalcule": tau10_mesure, "k": {}}
    for k in (1226, 1227):
        r = {}
        a0 = m0(mB, Y, ident, k)
        r["M0"] = resume("M0", a0, a0, nb)
        for nom in ("M1", "M2", "M3"):
            r[nom] = resume(nom, plis(F, Y, ident, nom, k), a0, nb)
        res["k"][str(k)] = r
        print(k, {n: (r[n]["attrapees"], round(r[n]["b_pct"], 3), round(r[n]["gain_points"], 3)) for n in r},
              flush=True)

    k = 1226
    a0 = res["k"]["1226"]["M0"]["par_fenetre"]
    sans_pen = plis(F, Y, ident, "M3", k, lam=0.0)
    res["M3_sans_penalite"] = resume("M3 lam=0", sans_pen, a0, nb)
    res["M3_penalite_forte"] = resume("M3 lam=1e4", plis(F, Y, ident, "M3", k, lam=1e4), a0, nb)

    # témoins du juge
    t = {}
    t["J-W4_etiquettes_melangees_M3"] = resume("W4", plis(F, Y, ident, "M3", k, melange=np.random.default_rng(7)), a0, nb)
    rng = np.random.default_rng(11)
    Fp = list(F)
    for j in (1, 2, 3):
        g = F[j].copy()
        for l in range(nl):
            plat = g[l].ravel()
            g[l] = rng.permutation(plat).reshape(NF, NP)
        Fp[j] = g
    t["J-W2_f2f3f4_permutes"] = resume("W2", plis(tuple(Fp), Y, ident, "M3", k), a0, nb)
    oracle = np.zeros_like(mB)
    oracle[1:] = Y[:-1]
    Fo = list(F)
    Fo[1] = oracle
    t["J-OR_oracle_l_moins_1"] = resume("OR", plis(tuple(Fo), Y, ident, "M3", k), a0, nb)
    res["temoins"] = t
    res["duree_s"] = time.time() - t0

    os.makedirs(SORTIE, exist_ok=True)
    with open(os.path.join(SORTIE, "juge-indices.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps({kk: v for kk, v in res.items() if kk != "k"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.exit(main())
