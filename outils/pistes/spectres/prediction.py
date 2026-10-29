"""Piste spectres : l'exposant α̂ prédit-il le levier de rang payé ? (seuil.md § 7 octies)

Règle déclarée : α̂ < 2 ⇒ levier (max_r N_r(16) > 0,05) ; α̂ ≥ 2 ⇒ pas de levier.
1. Témoin de l'outil : sur les 48 anciennes (npz), α̂ égal à `ajustements.out` et N égal à
   `plafond-rang.out` à 10⁻⁶ ; la règle y redonne 6 sur 8 et 2 sur 40.
2. Cassure (--casser) : les α̂ des 48 mélangés entre matrices ; la règle doit échouer à son critère.
3. Échantillon neuf (graine 20261022, couches 3, 9, 21) : 36 matrices lues dans le GGUF, une à la fois.

Utilisation : python -X utf8 prediction.py [--casser] > prediction.out 2> prediction.log
"""
from __future__ import annotations

import commun

import csv
import os
import sys

import numpy as np
from scipy.stats import spearmanr

import csn
import plafond_rang

GRAINE_NEUVE = 20261022
SEUIL_ALPHA = 2.0
SEUIL_LEVIER = 0.05
FORMES = {"attn_q": (4096, 2880), "attn_k": (512, 2880), "attn_v": (512, 2880), "attn_output": (2880, 4096)}


def tirage_neuf():
    rng = np.random.default_rng(GRAINE_NEUVE)
    pool = [c for c in range(1, 23) if c != 12]
    cs = sorted(int(c) for c in rng.choice(pool, 3, replace=False))
    ex = {c: sorted(int(e) for e in rng.choice(32, 4, replace=False)) for c in cs}
    assert cs == [3, 9, 21] and ex == {3: [4, 8, 24, 26], 9: [0, 14, 20, 22], 21: [10, 18, 23, 24]}, (cs, ex)
    sortie = []
    for c in cs:
        for r in ("ffn_gate_exps", "ffn_down_exps"):
            for e in ex[c]:
                sortie.append({"id": f"L{c:02d}.{r.split('_')[1]}.E{e:02d}", "couche": c, "role": r.split("_")[1],
                               "tenseur": f"blk.{c}.{r}.weight", "expert": e})
        for r in commun.ROLES_ATTENTION:
            sortie.append({"id": f"L{c:02d}.{r}", "couche": c, "role": r, "tenseur": f"blk.{c}.{r}.weight",
                           "expert": -1})
    return sortie


def levier(sig, m, n) -> float:
    g = plafond_rang.courbe(sig, m, n)
    return plafond_rang.meilleur(g, 16, m, n)[0]


def juger(alphas, leviers, nom):
    a, l = np.asarray(alphas), np.asarray(leviers)
    bas, haut = l[a < SEUIL_ALPHA], l[a >= SEUIL_ALPHA]
    kb, kh = int((bas > SEUIL_LEVIER).sum()), int((haut > SEUIL_LEVIER).sum())
    if bas.size < 3:
        v = "INDÉCIDABLE (moins de 3 matrices de α̂ < 2)"
    else:
        ok = kb >= 2 * bas.size / 3 and kh <= 0.1 * haut.size
        v = "LA RÈGLE TIENT" if ok else "LA RÈGLE TOMBE"
    rho = spearmanr(a, l)
    print(f"{nom} : α̂ < 2 : {kb} levier sur {bas.size} ; α̂ ≥ 2 : {kh} levier sur {haut.size} ; "
          f"Spearman {rho.statistic:+.3f} (p = {rho.pvalue:.2g}) → {v}", file=sys.stderr, flush=True)
    return v


def main() -> None:
    commun.priorite_basse()
    casser = "--casser" in sys.argv
    out = csv.writer(sys.stdout, lineterminator="\n")
    out.writerow(["echantillon", "id", "role", "couche", "m", "n", "alpha", "n_queue", "N16", "regle", "levier"])

    # --- 1. témoin de l'outil sur les 48 anciennes ---
    z = np.load(os.path.join(commun.MESURES, "valeurs-singulieres.npz"))
    with open(os.path.join(commun.MESURES, "ajustements.out"), encoding="utf8") as f:
        aj = {l["id"]: float(l["alpha"]) for l in csv.DictReader(f)}
    ref_n: dict[str, float] = {}
    with open(os.path.join(commun.MESURES, "plafond-rang.out"), encoding="utf8") as f:
        for l in csv.DictReader(f):
            if l["genre"] == "reel":
                ref_n[l["id"]] = max(ref_n.get(l["id"], -9.0), float(l["N_r_16"]))
    al, lv, ea, en = [], [], 0.0, 0.0
    for mat in commun.echantillon():
        m, n = FORMES.get(mat["role"], (2880, 2880))
        sig = z["reel/" + mat["id"]]
        a = csn.ajuster(sig ** 2)["alpha"]
        nv = levier(sig, m, n)
        ea, en = max(ea, abs(a - aj[mat["id"]]) / aj[mat["id"]]), max(en, abs(nv - ref_n[mat["id"]]))
        al.append(a)
        lv.append(nv)
    print(f"témoin de l'outil : écart relatif max sur α̂ {ea:.1e}, écart max sur N {en:.1e} (attendu ≤ 1e-6) : "
          f"{'TIENT' if ea <= 1e-6 and en <= 1e-6 else 'ÉCHEC'}", file=sys.stderr, flush=True)
    if casser:
        al = list(np.random.default_rng(GRAINE_NEUVE).permutation(al))
        print("[cassure] α̂ des 48 anciennes mélangés entre matrices", file=sys.stderr)
    v_anc = juger(al, lv, "48 anciennes" + (" (cassure)" if casser else ""))
    for mat, a, nv in zip(commun.echantillon(), al, lv):
        out.writerow(["ancien", mat["id"], mat["role"], mat["couche"], *FORMES.get(mat["role"], (2880, 2880)),
                      f"{a:.6f}", "", f"{nv:.6f}", int(a < SEUIL_ALPHA), int(nv > SEUIL_LEVIER)])
    sys.stdout.flush()
    if casser or not (ea <= 1e-6 and en <= 1e-6) or v_anc != "LA RÈGLE TIENT":
        if not casser:
            print("TÉMOIN EN ÉCHEC : l'échantillon neuf n'est pas lu", file=sys.stderr)
        return

    # --- 3. l'échantillon neuf ---
    lec = commun.lecteur()
    index = {t.nom: t for t in lec.tenseurs}
    al2, lv2 = [], []
    for mat in tirage_neuf():
        commun.attendre_calme()
        w = commun.matrice(lec, index, mat)
        m, n = w.shape
        assert (m, n) == FORMES.get(mat["role"], (2880, 2880)), (mat["id"], w.shape)
        sig = np.linalg.svd(w, compute_uv=False)
        r = csn.ajuster(sig ** 2)
        nv = levier(sig, m, n)
        al2.append(r["alpha"])
        lv2.append(nv)
        out.writerow(["neuf", mat["id"], mat["role"], mat["couche"], m, n, f"{r['alpha']:.6f}", r["n_queue"],
                      f"{nv:.6f}", int(r["alpha"] < SEUIL_ALPHA), int(nv > SEUIL_LEVIER)])
        sys.stdout.flush()
        print(f"{mat['id']:20s} α̂ {r['alpha']:6.3f} (n_q {r['n_queue']:4d})  max N(16) {nv:+.4f}  "
              f"prédit {'levier' if r['alpha'] < SEUIL_ALPHA else '—'}  mesuré {'levier' if nv > SEUIL_LEVIER else '—'}",
              file=sys.stderr, flush=True)
        del w
    juger(al2, lv2, "36 neuves")


if __name__ == "__main__":
    main()
