"""Juge du lot « espaces latents » : les nombres de III-9.1 (c) (la rangée) et de III-9.7 (le nuage),
refaits de zéro depuis le GGUF, les .sym du lot B, les captures de l'éclaireur et le CSV commité
mesures/genome/construction/synonyme/figures/spectre-L08-E00-gate.csv.

Écrit pour troncons le 2026-10-27, sans lire outils/genome/tome3/latents_*.py ni
memoire/outils/tome3_latents.py. Écrit un JSON (sortie standard) : chaque nombre recalculé, en regard
du nombre du lot (lu dans memoire/figures/tome3/donnees/latents-chiffres.tex et dans les CSV et JSON
commités), et les contrôles de points tirés au hasard (graine 27102026, écrite ici).

Usage : python -I -X utf8 juge_rangee_nuage.py > juge-rangee-nuage.json
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import juge_commun as jc  # noqa: E402

GRAINE_JUGE = 27102026
COUCHE, EXPERT = 8, 0
NOM = f"blk.{COUCHE}.ffn_gate_exps.weight"
LAT = os.path.join(jc.DEPOT, "mesures/genome/tome3/latents")
DON = os.path.join(jc.DEPOT, "memoire/figures/tome3/donnees")
SPECTRE = os.path.join(jc.DEPOT, "mesures/genome/construction/synonyme/figures/spectre-L08-E00-gate.csv")


def rel(a, b):
    return abs(a - b) / abs(b)


def rangee(g, out, rng):
    codes, ex = g.expert_mxfp4(NOM, EXPERT)                       # (2880, 2880), (2880, 90)
    exact_u = jc.valeur_e2m1(codes)                                 # en unités de s_b
    echelle = np.repeat(np.ldexp(1.0, ex - 127), 32, axis=1)         # s_b par poids
    cf, sf = jc.lire_sym(os.path.join(jc.SYM, "frontiere", f"L{COUCHE:02d}-E{EXPERT:02d}.sym"))
    cs, ss = jc.lire_sym(os.path.join(jc.SYM, "synonyme-l1-d1", f"L{COUCHE:02d}-E{EXPERT:02d}.sym"))
    sf, ss = sf[0], ss[0]                                           # gate
    o = {"centres_frontiere": cf.tolist(), "centres_synonyme": cs.tolist(),
         "centres_egaux": bool(np.array_equal(cf, cs))}
    # le symbole frontière est-il une fonction du code ?
    fonction = {}
    for c in range(16):
        u = np.unique(sf[codes == c])
        fonction[c] = u.tolist()
    o["frontiere_symboles_par_code"] = fonction
    o["frontiere_fonction_du_code"] = all(len(v) <= 1 for v in fonction.values())
    # changements par bloc
    ch = (sf != ss).reshape(jc.N, jc.N // 32, 32).sum(axis=2)
    hist = np.bincount(ch.ravel(), minlength=33)
    med = float(np.median(ch))
    o["histogramme_changes"] = hist.tolist()
    o["mediane_changes"] = med
    o["moyenne_changes"] = float(ch.mean())
    o["part_symboles_changes"] = float((sf != ss).mean())
    o["blocs_candidats"] = int((ch == med).sum())
    # le bloc tracé
    lot = jc.lire_csv(os.path.join(LAT, "rangee-L08-E00-gate.csv"))
    meta = json.load(open(os.path.join(LAT, "rangee-L08-E00-gate.json"), encoding="utf-8"))
    i, b = meta["ligne"], meta["bloc"]
    cols = np.arange(32 * b, 32 * b + 32)
    o["bloc"] = {"ligne": i, "bloc": b, "colonnes": [int(cols[0]), int(cols[-1])],
                 "exposant": int(ex[i, b]), "s_b": float(np.ldexp(1.0, int(ex[i, b]) - 127)),
                 "changes": int(ch[i, b]), "candidat": bool(ch[i, b] == med)}
    ef = float(((exact_u[i, cols] - jc.valeur_sym(sf[i, cols], cf)) ** 2).sum())
    es = float(((exact_u[i, cols] - jc.valeur_sym(ss[i, cols], cs)) ** 2).sum())
    o["bloc"]["erreur_s_b2"] = {"frontiere": ef, "synonyme": es}
    # chaque ligne du CSV commité contre la source
    pires = 0.0
    egaux = True
    for r in lot:
        j = int(r["j"]); c = cols[j]
        egaux &= int(r["colonne"]) == c and int(r["code"]) == int(codes[i, c])
        egaux &= int(r["sym_frontiere"]) == int(sf[i, c]) and int(r["sym_synonyme"]) == int(ss[i, c])
        egaux &= int(r["change"]) == int(sf[i, c] != ss[i, c])
        pires = max(pires, abs(float(r["exact"]) - exact_u[i, c]),
                    abs(float(r["frontiere"]) - jc.valeur_sym(sf[i, c], cf)),
                    abs(float(r["synonyme"]) - jc.valeur_sym(ss[i, c], cs)))
    o["csv_rangee_egal_source"] = {"entiers_egaux": bool(egaux), "ecart_max_reels": pires}
    # l'erreur sur la matrice entière, en unités réelles, contre Σ e_k du lot B
    W = exact_u * echelle
    spec = jc.lire_csv(SPECTRE)
    lam = np.array([float(r["lambda_calib"]) for r in spec])
    lev = np.array([float(r["lambda_eval_rayleigh"]) for r in spec])
    e_f = np.array([float(r["e_frontiere"]) for r in spec])
    e_s = np.array([float(r["e_synonyme"]) for r in spec])
    nf = float(((W - jc.valeur_sym(sf, cf) * echelle) ** 2).sum())
    ns = float(((W - jc.valeur_sym(ss, cs) * echelle) ** 2).sum())
    o["R0"] = {"norme2_frontiere": nf, "somme_e_frontiere": float(e_f.sum()), "ecart_rel_f": rel(nf, e_f.sum()),
               "norme2_synonyme": ns, "somme_e_synonyme": float(e_s.sum()), "ecart_rel_s": rel(ns, e_s.sum())}
    # cassure : les .sym de l'expert 1 sur la matrice de l'expert 0
    c1f, s1f = jc.lire_sym(os.path.join(jc.SYM, "frontiere", f"L{COUCHE:02d}-E01.sym"))
    c1s, s1s = jc.lire_sym(os.path.join(jc.SYM, "synonyme-l1-d1", f"L{COUCHE:02d}-E01.sym"))
    xf = float(((W - jc.valeur_sym(s1f[0], c1f) * echelle) ** 2).sum())
    xs = float(((W - jc.valeur_sym(s1s[0], c1s) * echelle) ** 2).sum())
    o["R0_cassure"] = {"frontiere_rapport": xf / e_f.sum(), "frontiere_ecart_rel": rel(xf, e_f.sum()),
                       "synonyme_rapport": xs / e_s.sum(), "synonyme_ecart_rel": rel(xs, e_s.sum())}
    del s1f, s1s
    o["spectre"] = {
        "somme_e_f": float(e_f.sum()), "somme_e_s": float(e_s.sum()), "hausse_pct": 100 * (e_s.sum() / e_f.sum() - 1),
        "calib_f": float((lam * e_f).sum()), "calib_s": float((lam * e_s).sum()),
        "calib_rapport": float((lam * e_f).sum() / (lam * e_s).sum()),
        "eval_f": float((lev * e_f).sum()), "eval_s": float((lev * e_s).sum()),
        "eval_rapport": float((lev * e_f).sum() / (lev * e_s).sum())}
    out["rangee"] = o
    return W, jc.valeur_sym(sf, cf) * echelle, jc.valeur_sym(ss, cs) * echelle, lam, e_f, e_s


def nuage(W, Wf, Ws, lam_csv, e_f_csv, e_s_csv, out, rng):
    o = {}
    h, experts, poids = jc.captures("calib", COUCHE)
    p, slot = np.nonzero(experts == EXPERT)
    X = np.asarray(h[p], dtype=np.float64)
    gg = poids[p, slot]
    o["n_entrees"] = int(p.size)
    o["positions_distinctes"] = int(np.unique(p).size)
    w2 = gg * gg
    H = (X * w2[:, None]).T @ X / w2.sum()
    lam, U = np.linalg.eigh(H)
    lam, U = lam[::-1], U[:, ::-1]
    o["lambda_1_3"] = lam[:3].tolist()
    o["part_trace_3"] = float(lam[:3].sum() / lam.sum())
    o["rang_numerique"] = int((lam > lam[0] * 1e-12).sum())
    o["spectre_egal_csv_ecart_rel_max_top100"] = float(np.max(np.abs(lam[:100] / lam_csv[:100] - 1)))
    C = X @ U[:, :3]
    # orientation : u1 tourné vers la moyenne des entrées (le lot l'a choisie ainsi, à vérifier)
    for k in range(3):
        if C[:, k].mean() < 0 and k == 0:
            C[:, k] *= -1; U[:, k] *= -1
    o["moyenne_c"] = C.mean(axis=0).tolist()
    o["ecart_type_c_pop"] = C.std(axis=0).tolist()
    o["ecart_type_c_ech"] = C.std(axis=0, ddof=1).tolist()
    dF, dS = W - Wf, W - Ws
    ef = ((dF @ U[:, :3]) ** 2).sum(axis=0)
    es = ((dS @ U[:, :3]) ** 2).sum(axis=0)
    o["e_1_3_frontiere"] = ef.tolist(); o["e_1_3_synonyme"] = es.tolist()
    o["N0_ecart_rel"] = {"lambda": float(np.max(np.abs(lam[:3] / lam_csv[:3] - 1))),
                         "e_f": float(np.max(np.abs(ef / e_f_csv[:3] - 1))),
                         "e_s": float(np.max(np.abs(es / e_s_csv[:3] - 1)))}
    o["rapports_sqrt_e"] = np.sqrt(es / ef).tolist()
    # ellipses
    axes = {}
    Ms = {}
    for nom, (a, b) in {"12": (0, 1), "13": (0, 2)}.items():
        B = U[:, [a, b]]
        for var, d in (("frontiere", dF), ("synonyme", dS)):
            M = (d @ B).T @ (d @ B)
            ev = np.linalg.eigvalsh(M)[::-1]
            axes[f"{var}-{nom}"] = np.sqrt(ev).tolist()
            Ms[f"{var}-{nom}"] = M
    o["demi_axes"] = axes
    F = 2 * np.sqrt(lam[1]) / axes["frontiere-12"][0]
    o["F"] = float(F)
    o["F_variante_max_deux_plans"] = float(2 * np.sqrt(lam[1]) / max(axes["frontiere-12"][0], axes["frontiere-13"][0]))
    # points tirés au hasard : coordonnées du CSV commité contre la source
    pts = jc.lire_csv(os.path.join(LAT, "nuage-L08-E00-gate-points.csv"))
    o["points_csv"] = len(pts)
    tires = rng.choice(len(pts), size=5, replace=False)
    ctl = []
    for t in tires:
        r = pts[int(t)]
        pos = int(r["position"])
        k = np.nonzero(p == pos)[0]
        c_src = C[k[0]] if k.size else None
        ctl.append({"ligne_csv": int(t), "position": pos, "g_csv": float(r["g"]),
                    "g_source": float(gg[k[0]]) if k.size else None,
                    "c_csv": [float(r["c1"]), float(r["c2"]), float(r["c3"])],
                    "c_source_aux_signes_pres": [float(v) for v in c_src] if c_src is not None else None})
    o["points_tires"] = ctl
    # tous les points, aux signes près de u2 et u3
    pos_csv = np.array([int(r["position"]) for r in pts])
    Ccsv = np.array([[float(r["c1"]), float(r["c2"]), float(r["c3"])] for r in pts])
    o["positions_csv_egales_source"] = bool(np.array_equal(pos_csv, p))
    if np.array_equal(pos_csv, p):
        sg = np.sign((Ccsv * C).sum(axis=0))
        o["signes_axes_lot_contre_juge"] = sg.tolist()
        o["points_ecart_max"] = float(np.max(np.abs(Ccsv - C * sg)))
    else:
        sg = np.ones(3)
    # les ellipses du CSV commité, avec les signes d'axes du lot : chaque point y doit vérifier
    # (y/F)ᵀ M⁻¹ (y/F) = 1, M = Bᵀ ΔWᵀ ΔW B recalculée ici (B aux signes du lot)
    ell = jc.lire_csv(os.path.join(LAT, "nuage-L08-E00-gate-ellipses.csv"))
    pires, par_courbe = {}, {}
    for r in ell:
        if r["courbe"] not in ("frontiere", "synonyme"):
            continue
        cle = f"{r['courbe']}-{r['plan']}"
        b = 1 if r["plan"] == "12" else 2
        S = np.diag([sg[0], sg[b]])
        Mi = np.linalg.inv(S @ Ms[cle] @ S)
        y = np.array([float(r["x"]), float(r["y"])]) / F
        q = float(y @ Mi @ y)
        pires[cle] = max(pires.get(cle, 0.0), abs(q - 1))
        par_courbe.setdefault(cle, []).append((int(r["i"]), q))
    o["ellipses_csv_sur_l_ellipse_ecart_max"] = pires
    tire = {}
    for k, v in sorted(par_courbe.items()):
        i, q = v[int(rng.integers(0, len(v)))]
        tire[k] = {"i": i, "forme_quadratique": q}
    o["ellipses_un_point_tire_par_serie"] = tire
    o["courbes_csv"] = sorted({r["courbe"] for r in ell})
    # cassure N0 : la H des entrées d'évaluation
    he, xe, pe = jc.captures("eval", COUCHE)
    q, sl = np.nonzero(xe == EXPERT)
    Xe = np.asarray(he[q], dtype=np.float64)
    w2e = pe[q, sl] ** 2
    He = (Xe * w2e[:, None]).T @ Xe / w2e.sum()
    l1e = float(np.linalg.eigvalsh(He)[-1])
    o["cassure_eval"] = {"n_eval": int(q.size), "lambda1_eval": l1e, "ecart_rel": rel(l1e, lam[0])}
    out["nuage"] = o


def main():
    rng = np.random.default_rng(GRAINE_JUGE)
    out = {"outil": "outils/genome/tome3/juge-latents/juge_rangee_nuage.py", "graine_juge": GRAINE_JUGE}
    g = jc.Gguf()
    W, Wf, Ws, lam, e_f, e_s = rangee(g, out, rng)
    nuage(W, Wf, Ws, lam, e_f, e_s, out, rng)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
