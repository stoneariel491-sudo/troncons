"""Un expert codé comme mutation de son parent : choix du parent, coût sans perte (D1), coût avec
perte contre le même quantificateur sans parent (D2), mutation tronquée (T), sortie de l'expert sur
entrées réelles (O). Seuils : mesures/genome/duplication/00-seuils-declares.md (commité avant).

Pour chaque enfant (couche L, expert c) :
  1. Parent : le meilleur score d'appariement (paires_arbre.apparier) parmi les 31 autres experts de
     L et les 32 experts de L − 1. La permutation `col` range les neurones du parent dans l'ordre de
     l'enfant : neurone k de l'enfant ↔ neurone col[k] du parent.
  2. D1 (gate, up) : codes E2M1 de l'enfant c_e, du parent apparié c_p (rangées permutées, blocs
     intacts) ; classe d'échelle de l'enfant κ = signe(e − médiane haute de la rangée) + 1 (F1).
     Gain = H(c_e | κ) − H(c_e | κ, c_p) = I(c_e ; c_p | κ), estimateur par comptes exacts (biais
     (K − 1)/(2 N ln 2) ≤ 7·10⁻⁵ bit pour K = 720 cases, N = 8,3·10⁶). Même calcul pour les δ
     d'échelle. Témoins : parent dans un ordre de hasard (gain = biais seul) ; enfant conditionné à
     lui-même (H doit valoir 0 : l'estimateur sait tomber à zéro).
  3. D2 : W enfant, P parent apparié (gate, up : rangées ; down : colonnes) ; α par neurone (moindres
     carrés, puis arrondi sur 8 bits : pas 1/128 dans [−1, 1)) ; résidu R = W − α ⊙ P ; ECSQ : pas Δ
     commun au tenseur, q = round(R / Δ), débit H(q | exposant E8M0 du bloc de l'enfant) ; erreur
     ε = ‖W − α ⊙ P − qΔ‖² / ‖W‖². Témoin d'indépendance : α = 0 (l'ECSQ seule). Témoin de hasard :
     P = parent dans un ordre de hasard. Balayage de Δ ; débit à ε = 4,2920 % par interpolation en
     log ε sur l'enveloppe convexe inférieure des points (débit, log ε).
  4. T : erreur des poids et de la sortie pour W ≈ α ⊙ P (résidu jeté), puis pour le résidu aux pas
     du balayage.
  5. O : entrées réelles (états normés routés vers l'enfant, capture de l'éclaireur : h-Lll.f32 et
     routage-Lll.bin, 511 jetons par fenêtre) ; sortie y = W_down · SwiGLU-oai(W_gate x + b_g,
     W_up x + b_u) + b_d en f64 ; erreur Σ‖y − ŷ‖² / Σ‖y‖² pour : la base de B (4 classes, centres
     0,237 ; 1,424 ; 3,419 ; 6 en unités E2M1), la mutation au pas qui donne ε ≈ 4,29 %, l'ECSQ seule
     au même ε, la mutation tronquée.

Utilisation :
  python -I -X utf8 mutation.py --couche 8 --enfants 0,8,16,24 --capture DOSSIER > journal.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import experts as X  # noqa: E402
from paires_arbre import apparier, gene  # noqa: E402

EPS_BASE = 0.042920
PAS = (1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 6.0, 8.0, 12.0)
CENTRES_BASE = np.array([0.237, 1.424, 3.419, 6.0])           # unités E2M1 (07 § 4.2)
CLASSE_MAG = np.array([0, 0, 1, 1, 1, 2, 2, 3])                # magnitudes 0 ; 0,5 | 1 ; 1,5 ; 2 | 3 ; 4 | 6


def h_cond(sym: np.ndarray, ctx: np.ndarray) -> float:
    """H(sym | ctx) en bits, comptes exacts. sym, ctx : entiers ≥ 0."""
    sym = sym.astype(np.int64).ravel()
    ctx = ctx.astype(np.int64).ravel()
    k = ctx * (int(sym.max()) + 1) + sym
    _, n = np.unique(k, return_counts=True)
    _, nc = np.unique(ctx, return_counts=True)
    N = sym.size
    return float((-(n * np.log2(n)).sum() + (nc * np.log2(nc)).sum()) / N)


def classe_echelle(e: np.ndarray) -> np.ndarray:
    """κ par bloc : signe(e − médiane haute de la rangée) + 1 ; médiane haute = rang 45 des 90."""
    med = np.sort(e, axis=1)[:, e.shape[1] // 2][:, None].astype(np.int32)
    return (np.sign(e.astype(np.int32) - med) + 1).astype(np.int64)


def delta_echelle(e: np.ndarray) -> np.ndarray:
    med = np.sort(e, axis=1)[:, e.shape[1] // 2][:, None].astype(np.int32)
    return (e.astype(np.int32) - med)


def base_b(ex, L, role, c):
    """Reconstruction par la base de B (signe + 4 classes de magnitude), poids f64 (sortie, entrée)."""
    codes, e = ex.codes_echelles(L, role, c)
    mag = CENTRES_BASE[CLASSE_MAG[codes & 7]] * np.where(codes >= 8, -1.0, 1.0)
    ech = np.ldexp(1.0, e.astype(np.int64) - 127)               # E2M1 · 2^(e−127)
    return (mag.reshape(e.shape[0], e.shape[1], 32) * ech[:, :, None]).reshape(codes.shape)


def enveloppe_interp(points, eps_cible):
    """points : (ε, débit). Enveloppe convexe inférieure dans le plan (log ε, débit), interpolée."""
    pts = sorted((math.log(e), r) for e, r in points if e > 0)
    hull = []
    for p in pts:
        while len(hull) >= 2:
            (x1, y1), (x2, y2) = hull[-2], hull[-1]
            if (y2 - y1) * (p[0] - x1) >= (p[1] - y1) * (x2 - x1):
                hull.pop()
            else:
                break
        hull.append(p)
    x = math.log(eps_cible)
    for (x1, y1), (x2, y2) in zip(hull, hull[1:]):
        if x1 <= x <= x2:
            return y1 + (y2 - y1) * (x - x1) / (x2 - x1)
    return None


def ecsq(W, P, alpha, e_blocs, pas_abs):
    """Rend [(Δ, ε, H(q | e))] pour la prédiction alpha ⊙ P (P = None : indépendant)."""
    pred = 0.0 if P is None else alpha * P
    R = W - pred
    E = float((W * W).sum())
    eb = np.repeat(e_blocs, 32, axis=1)
    out = []
    for d in pas_abs:
        q = np.rint(R / d).astype(np.int64)
        err = float(((R - q * d) ** 2).sum()) / E
        qq = q - q.min()
        out.append((float(d), err, h_cond(qq, eb)))
    return out


def ecsq_contexte(W, P, alpha, e_blocs, pas_abs, K=3):
    """Mêmes indices que l'ECSQ indépendante (q = round(W / Δ), donc MÊME erreur au bit), codés par
    leur entropie conditionnelle à l'exposant du bloc ET à la prédiction du parent quantifiée,
    ctx = borne(round(α P / Δ), −K, K). Le gain sur l'indépendante est l'information mutuelle
    I(q ; ctx | e) : la part de l'enfant que le parent dit, sans rien changer à la reconstruction."""
    eb = np.repeat(e_blocs, 32, axis=1).astype(np.int64)
    E = float((W * W).sum())
    out = []
    for d in pas_abs:
        q = np.rint(W / d).astype(np.int64)
        err = float(((W - q * d) ** 2).sum()) / E
        c = np.clip(np.rint(alpha * P / d), -K, K).astype(np.int64) + K
        out.append((float(d), err, h_cond(q - q.min(), eb * (2 * K + 1) + c)))
    return out


def alpha_neurones(W, P, axe):
    """α par neurone (axe 1 : rangées ; axe 0 : colonnes), arrondi sur 8 bits (pas 1/128, [−1, 1))."""
    num = (W * P).sum(axis=axe)
    den = (P * P).sum(axis=axe)
    a = np.where(den > 0, num / np.maximum(den, 1e-300), 0.0)
    a = np.clip(np.rint(a * 128), -128, 127) / 128
    return a[:, None] if axe == 1 else a[None, :]


def lire_capture(dossier, L, d):
    h = np.fromfile(os.path.join(dossier, f"h-L{L:02d}.f32"), dtype=np.float32).reshape(-1, d)
    r = np.fromfile(os.path.join(dossier, f"routage-L{L:02d}.bin"), dtype=np.uint8).reshape(-1, 20)
    choix = r[:, :4]
    return h, choix


def empreinte(chemin):
    s = hashlib.sha256()
    with open(chemin, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            s.update(b)
    return s.hexdigest()


def sortie_expert(x, Wg, Wu, Wd, bg, bu, bd):
    g = x @ Wg.T + bg
    u = x @ Wu.T + bu
    g = np.minimum(g, 7.0)
    u = np.clip(u, -7.0, 7.0)
    a = g / (1.0 + np.exp(-1.702 * g)) * (u + 1.0)
    return a @ Wd.T + bd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--couche", type=int, required=True)
    ap.add_argument("--enfants", default="0,8,16,24")
    ap.add_argument("--capture", default=None)
    ap.add_argument("--max-jetons", type=int, default=2048)
    ap.add_argument("--graine", type=int, default=20261016)
    ap.add_argument("--parent", default=None, help="couche,expert imposé (saute le choix ; un seul enfant)")
    a = ap.parse_args()
    ex = X.Experts()
    rng = np.random.default_rng(a.graine)
    L = a.couche
    enfants = [int(c) for c in a.enfants.split(",")]
    t0 = time.time()
    log = lambda m: print(f"[{time.time() - t0:6.0f} s] {m}", file=sys.stderr, flush=True)
    sortie = {"outil": "mutation.py", "arguments": vars(a), "enfants": []}

    # 1. Choix du parent (poids seuls).
    G_enf = {c: [gene(ex, L, r, c) for r in X.ROLES] for c in enfants}
    candidats = [(L, e) for e in range(ex.nb_experts)] + ([(L - 1, e) for e in range(ex.nb_experts)] if L > 0 else [])
    if a.parent:
        # Parent imposé (par exemple l'arête la plus lourde de l'arbre d'une couche) : un seul candidat.
        candidats = [tuple(int(v) for v in a.parent.split(","))]
    meilleur = {c: (-1.0, None, None, None) for c in enfants}
    scores = {c: [] for c in enfants}
    for (Lp, ep) in candidats:
        Gp = [gene(ex, Lp, r, ep) for r in X.ROLES]
        for c in enfants:
            if (Lp, ep) == (L, c):
                continue
            s, cosr, gr, col = apparier(G_enf[c], Gp)
            scores[c].append({"couche": Lp, "expert": ep, "score_bits": s, "cos_par_role": cosr})
            if s > meilleur[c][0]:
                meilleur[c] = (s, (Lp, ep), col, cosr)
        log(f"candidat ({Lp}, {ep}) fait")
    del G_enf

    for c in enfants:
        s, (Lp, ep), col, cosr = meilleur[c]
        log(f"enfant ({L}, {c}) : parent ({Lp}, {ep}), score {s:.4f} b")
        fiche = {"couche": L, "expert": c, "parent": {"couche": Lp, "expert": ep, "score_bits": s, "cos_par_role": cosr},
                 "scores_candidats": scores[c], "D1": {}, "D2": {}, "T": {}}
        perm_hasard = rng.permutation(ex.d_ff)
        n_poids = 3 * ex.d_ff * ex.d_entree_gate
        bits_perm = math.lgamma(ex.d_ff + 1) / math.log(2) / n_poids
        fiche["bits_permutation_par_poids"] = bits_perm
        mats = {}
        for role in X.ROLES:
            ce, ee = ex.codes_echelles(L, role, c)
            cp, epp = ex.codes_echelles(Lp, role, ep)
            We = ex.poids(L, role, c).astype(np.float64)
            Wp = ex.poids(Lp, role, ep).astype(np.float64)
            # Parent apparié, position par position : gate, up : rangées permutées (blocs intacts) ;
            # down : colonnes permutées (la permutation traverse les blocs, mais conditionner le code
            # de l'enfant en (i, k) au code du parent en (i, col[k]) reste exact et sans perte).
            if role != "down":
                cpa, cph = cp[col], cp[perm_hasard]
                P, Ph = Wp[col], Wp[perm_hasard]
                alpha, alpha_h = alpha_neurones(We, P, 1), alpha_neurones(We, Ph, 1)
            else:
                cpa, cph = cp[:, col], cp[:, perm_hasard]
                P, Ph = Wp[:, col], Wp[:, perm_hasard]
                alpha, alpha_h = alpha_neurones(We, P, 0), alpha_neurones(We, Ph, 0)
            # 2. D1 sans perte, sur les codes.
            kap = np.repeat(classe_echelle(ee), 32, axis=1)
            h_seul = h_cond(ce, kap)
            h_par = h_cond(ce, kap * 16 + cpa)
            h_hasard = h_cond(ce, kap * 16 + cph)
            h_soi = h_cond(ce, kap * 16 + ce)
            fiche["D1"][role] = {"H_code_sachant_kappa": h_seul, "H_code_sachant_kappa_parent": h_par,
                                 "gain_codes": h_seul - h_par, "temoin_hasard_gain": h_seul - h_hasard,
                                 "temoin_soi_H": h_soi}
            if role != "down":
                de, dp = delta_echelle(ee), delta_echelle(epp)
                dd = de - de.min()
                hd_seul = h_cond(dd, np.zeros_like(dd))
                hd_par = h_cond(dd, (dp[col] - dp.min()))
                fiche["D1"][role].update({"H_delta": hd_seul, "H_delta_sachant_parent": hd_par,
                                          "gain_echelles_par_poids": (hd_seul - hd_par) / 32})
            # D2b : les symboles de la base de B (signe + 4 classes), MÊME reconstruction que la base,
            # codés sachant κ et le symbole de base du parent apparié.
            be = (ce >> 3) * 4 + CLASSE_MAG[ce & 7]
            bpa = (cpa >> 3) * 4 + CLASSE_MAG[cpa & 7]
            bph = (cph >> 3) * 4 + CLASSE_MAG[cph & 7]
            hb_seul = h_cond(be, kap)
            fiche["D2b_base"] = fiche.get("D2b_base", {})
            fiche["D2b_base"][role] = {"H_base_sachant_kappa": hb_seul,
                                       "gain_parent": hb_seul - h_cond(be, kap * 8 + bpa),
                                       "gain_hasard": hb_seul - h_cond(be, kap * 8 + bph),
                                       "gain_parent_code_complet": hb_seul - h_cond(be, kap * 16 + cpa)}
            # 3. D2 avec perte.
            s0 = 2.0 ** (float(np.median(ee)) - 128)
            pas_abs = [p * s0 for p in PAS]
            ind = ecsq(We, None, None, ee, pas_abs)
            mut = ecsq(We, P, alpha, ee, pas_abs)
            har = ecsq(We, Ph, alpha_h, ee, pas_abs)
            ctx = ecsq_contexte(We, P, alpha, ee, pas_abs)
            ctx_h = ecsq_contexte(We, Ph, alpha_h, ee, pas_abs)
            bits_alpha = 8.0 / We.shape[1 if role != "down" else 0]
            r_ind = enveloppe_interp([(e, h) for _, e, h in ind], EPS_BASE)
            r_mut = enveloppe_interp([(e, h) for _, e, h in mut], EPS_BASE)
            r_har = enveloppe_interp([(e, h) for _, e, h in har], EPS_BASE)
            r_ctx = enveloppe_interp([(e, h) for _, e, h in ctx], EPS_BASE)
            r_ctx_h = enveloppe_interp([(e, h) for _, e, h in ctx_h], EPS_BASE)
            # Gain du contexte parent pas par pas (même erreur au bit) : sans interpolation.
            gain_ctx_pas = [(d, e1, h1 - h2) for (d, e1, h1), (_, _, h2) in zip(ind, ctx)]
            gain_ctx_h_pas = [(d, e1, h1 - h2) for (d, e1, h1), (_, _, h2) in zip(ind, ctx_h)]
            E = float((We ** 2).sum())
            err_tronque = float(((We - alpha * P) ** 2).sum()) / E
            fiche["D2"][role] = {"independant": ind, "mutation": mut, "hasard": har,
                                 "bits_alpha_par_poids": bits_alpha,
                                 "contexte_parent": ctx, "contexte_hasard": ctx_h,
                                 "gain_contexte_par_pas": gain_ctx_pas, "gain_contexte_hasard_par_pas": gain_ctx_h_pas,
                                 "debit_a_eps_base": {"independant": r_ind, "mutation": r_mut, "hasard": r_har,
                                                      "contexte_parent": r_ctx, "contexte_hasard": r_ctx_h},
                                 "gain_mutation": (None if r_ind is None or r_mut is None else r_ind - r_mut - bits_alpha),
                                 "gain_hasard": (None if r_ind is None or r_har is None else r_ind - r_har - bits_alpha),
                                 "gain_contexte": (None if r_ind is None or r_ctx is None else r_ind - r_ctx - bits_alpha),
                                 "gain_contexte_hasard": (None if r_ind is None or r_ctx_h is None else r_ind - r_ctx_h - bits_alpha)}
            fiche["T"][role] = {"erreur_poids_mutation_tronquee": err_tronque,
                                "energie_expliquee": 1 - err_tronque}
            # Le pas de la mutation et de l'indépendant les plus proches de ε base (pour O).
            def pas_proche(pts):
                return min(pts, key=lambda t: abs(math.log(max(t[1], 1e-12)) - math.log(EPS_BASE)))[0]
            mats[role] = {"W": We, "P": P, "alpha": alpha, "d_mut": pas_proche(mut), "d_ind": pas_proche(ind)}
            log(f"  {role} : D1 gain {fiche['D1'][role]['gain_codes']:.5f} (hasard {fiche['D1'][role]['temoin_hasard_gain']:.5f}) ; "
                f"D2b {fiche['D2b_base'][role]['gain_parent']:.5f} ; "
                f"D2 ind {r_ind} mut {r_mut} ctx {r_ctx} (hasard {r_ctx_h}) ; tronquée {err_tronque:.4f}")
            del ce, cp, Wp
        # 5. O : sortie de l'expert sur entrées réelles.
        if a.capture:
            h, choix = lire_capture(a.capture, L, ex.d_entree_gate)
            pos = np.nonzero((choix == c).any(axis=1))[0][: a.max_jetons]
            x = h[pos].astype(np.float64)
            bg = ex.biais(L, "gate")[c].astype(np.float64)
            bu = ex.biais(L, "up")[c].astype(np.float64)
            bd = ex.biais(L, "down")[c].astype(np.float64)
            ref = sortie_expert(x, mats["gate"]["W"], mats["up"]["W"], mats["down"]["W"], bg, bu, bd)
            Eref = float((ref ** 2).sum())

            def err_sortie(Ws):
                y = sortie_expert(x, Ws["gate"], Ws["up"], Ws["down"], bg, bu, bd)
                return float(((y - ref) ** 2).sum()) / Eref

            def quantifie(m, pred, d):
                R = m["W"] - pred
                return pred + np.rint(R / d) * d
            variantes = {
                "base_B": {r: base_b(ex, L, r, c) for r in X.ROLES},
                "mutation_eps_base": {r: quantifie(mats[r], mats[r]["alpha"] * mats[r]["P"], mats[r]["d_mut"]) for r in X.ROLES},
                "ecsq_seule_eps_base": {r: quantifie(mats[r], 0.0, mats[r]["d_ind"]) for r in X.ROLES},
                "mutation_tronquee": {r: mats[r]["alpha"] * mats[r]["P"] for r in X.ROLES},
                "parent_seul_sans_alpha": {r: mats[r]["P"] for r in X.ROLES},
            }
            O = {"jetons_routes": int(len(pos))}
            for nom, Ws in variantes.items():
                O[nom] = {"erreur_sortie": err_sortie(Ws),
                          "erreur_poids": float(sum(((Ws[r] - mats[r]["W"]) ** 2).sum() for r in X.ROLES)
                                                / sum((mats[r]["W"] ** 2).sum() for r in X.ROLES))}
            # Témoin de l'instrument : les poids exacts rendent une erreur nulle.
            O["temoin_exact"] = err_sortie({r: mats[r]["W"] for r in X.ROLES})
            fiche["O"] = O
            log(f"  O : " + ", ".join(f"{k} {v['erreur_sortie']:.4f}" for k, v in O.items() if isinstance(v, dict)))
        sortie["enfants"].append(fiche)
        del mats
    if a.capture:
        sortie["capture"] = {"dossier": a.capture,
                             "h_sha256": empreinte(os.path.join(a.capture, f"h-L{L:02d}.f32")),
                             "routage_sha256": empreinte(os.path.join(a.capture, f"routage-L{L:02d}.bin"))}
    sortie["duree_s"] = time.time() - t0
    print(json.dumps(sortie, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
