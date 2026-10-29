"""Débit-distorsion des codes MXFP4 réels : élagage synaptique et quantification prédictive bornée.

Tout se calcule sur la loi conjointe exacte (tenseur, e, δ de ligne, code) d'histogramme.py.

Le cadre (dérivation complète dans genome/predictif-elagage-pour-le-memoire.md § 2) :
  - un poids vaut w = K[c] · 2^(e − 128) ; on le remplace par ŵ = r_{k,s} · 2^(e − 128), où
    s = cellule du code c dans la partition P_k de son contexte k (un intervalle de la suite
    ordonnée des 16 codes −12 … −1, −0, +0, +1 … +12), et r_{k,s} le centre de gravité de la
    cellule, pondéré par 4^e (optimal pour l'erreur quadratique dans le domaine réel) ;
  - le débit est l'entropie conditionnelle H(s | k), une table par tenseur et par contexte
    (décodage rANS à table choisie par contexte, le geste d'A_ctx) ; les échelles coûtent
    0,0347 + 0,0028 bit par poids (δ et médianes, ARCHITECTURE § 3.3), comptés pareil partout ;
  - l'erreur est l'erreur quadratique relative globale Σ(w − ŵ)² / Σw², la métrique de la
    frontière (raffinement_mxfp4.py) ;
  - pour un multiplicateur μ, chaque (tenseur, contexte) choisit sa partition qui minimise
    D/E + μ · bits, par programmation dynamique exacte sur les 2^15 partitions en intervalles
    (le coût d'une cellule ne dépend que d'elle : n_s · (−log2 n_s / n_k) bits et
    A_s·Σ(K − r)² d'erreur). Un μ commun à tous les contextes est la condition d'optimalité du
    remplissage inverse (« reverse water-filling ») : les contextes de faible énergie reçoivent
    des cellules grossières, jusqu'à la cellule unique qui élague tout le contexte.

Familles :
  - base : la frontière, partition fixe {0 ; 0,5} {1 ; 1,5 ; 2} {3 ; 4} {6} avec signe, centres
    communs, contexte κ ; doit redonner 4,2920 % et H(code) = 3,860 (témoins) ;
  - sans_perte_valeur : chaque code seul, mais −0 et +0 fondus (même valeur, donc exact en
    valeur ; le signe d'un zéro ne porte rien) ;
  - elagage_magnitude : seuil global t dans le domaine réel, |w| < t mis à zéro, le reste exact
    (l'emplacement des zéros est payé par l'entropie du symbole zéro, contexte e) ;
  - elagage_lagrangien : par contexte e, une zone morte [−a, +a] choisie par μ, le reste exact ;
  - ecsq_kappa, ecsq_delta7, ecsq_e : partitions libres par contexte (κ ; δ borné à ±3 ;
    échelle absolue e).

Seuils déclarés avant la mesure :
  - avec perte : une famille bat la frontière si, à erreur égale à celle de la base (moyenne des
    erreurs relatives par tenseur, la base y vaut ≈ 4,4 % ; la globale de 4,2920 % est tenue à 91,5 %
    par blk.23.ffn_down, constat de la première passe du 2026-10-16), son débit (idéal + mêmes
    coûts fixes + tables) est ≤ 0,99 × celui de la base calculé par le même instrument (1 % :
    marge pour l'écart entre entropie et codeur réel, à vérifier sur la base) ;
  - sans perte en valeur : gain ≥ 0,015 bit par poids (coût d'en-tête d'un flux, 03 § 3.1).
Témoins : base à 4,2920 % (à 1e-6 relatif) et chaîne H(code) ; partition identité : erreur 0 ;
cassure (--casser) : les centres de la base sont pris sans la pondération 4^e ; l'erreur de base
ne retrouve plus 4,2920 % et le témoin tombe.

Utilisation : python -I -X utf8 debit_distorsion.py HISTO.npz SORTIE.json CSV_COURBES [--casser]
"""
from __future__ import annotations

import csv
import json
import math
import sys

import numpy as np

# Ordre des 16 codes sur la droite réelle : −12 … −1, −0, +0, +1 … +12.
ORDRE = np.array([15, 14, 13, 12, 11, 10, 9, 8, 0, 1, 2, 3, 4, 5, 6, 7])
MAG = np.array([0, 1, 2, 3, 4, 6, 8, 12], dtype=np.float64)
VAL = np.concatenate([MAG, -MAG])
VAL_O = VAL[ORDRE]
FIXES = 0.0347 + 0.0028           # échelles (δ) et médianes, bits par poids [mes. ARCHITECTURE § 3.3]
ERREUR_BASE_07 = 0.042919745124980
SEUIL_PERTE = 0.99
SEUIL_SANS_PERTE = 0.015
BITS_TABLE = 12                   # une fréquence de table


def entropie_bits(n):
    n = n[n > 0].astype(np.float64)
    s = n.sum()
    return float(-(n * np.log2(n / s)).sum())


class Source:
    """Les statistiques par (tenseur, contexte) dans l'ordre ORDRE : comptes, masse, moments.

    metrique = "globale" : Σ(w − ŵ)² / Σw² sur tous les tenseurs (celle de la frontière, que
    blk.23.ffn_down tient à 91,5 % : un remplissage inverse global l'exploite en vidant les autres) ;
    metrique = "par_tenseur" : moyenne sur les tenseurs de leur erreur relative propre (chaque
    matrice compte autant ; c'est elle que l'étude retient pour juger)."""

    def __init__(self, comptes, contexte, metrique="par_tenseur"):
        T = comptes.shape[0]
        e = np.arange(256)
        ef = comptes.sum(axis=(0, 2, 3))
        self.emax = int(np.nonzero(ef)[0].max())
        poids = 4.0 ** (e - self.emax)                              # 4^(e − emax)
        self.N = float(comptes.sum(dtype=np.float64))
        self.E = float((comptes.sum(axis=2).astype(np.float64) * poids[None, :, None]
                        * (VAL ** 2)[None, None, :]).sum())
        self.Et = (comptes.sum(axis=2).astype(np.float64) * poids[None, :, None]
                   * (VAL ** 2)[None, None, :]).sum(axis=(1, 2))
        self.metrique = metrique
        self.stats = []  # liste de (t, k, n[16], A[16], B[16], C[16]) dans l'ordre ORDRE
        for t in range(T):
            ct = comptes[t].astype(np.float64)                         # (256, 17, 16)
            cles = contexte(ct)                                       # dict k -> (256, 16) comptes
            for k, nek in cles.items():
                n = nek.sum(axis=0)[ORDRE]
                if n.sum() == 0:
                    continue
                m = (nek * poids[:, None]).sum(axis=0)[ORDRE]
                self.stats.append((t, k, n, m, m * VAL_O, m * VAL_O ** 2))
        self.T = T


def ctx_kappa(ct):
    d = np.arange(17) - 8
    return {0: ct[:, d < 0, :].sum(axis=1), 1: ct[:, d == 0, :].sum(axis=1), 2: ct[:, d > 0, :].sum(axis=1)}


def ctx_delta7(ct):
    out = {}
    for i in range(17):
        k = int(np.clip(i - 8, -3, 3))
        out[k] = out.get(k, 0) + ct[:, i, :]
    return out


def ctx_e(ct):
    tot = ct.sum(axis=1)                                             # (256, 16)
    out = {}
    for e in np.nonzero(tot.sum(axis=1))[0]:
        z = np.zeros_like(tot)
        z[e] = tot[e]
        out[int(e)] = z
    return out


def ctx_rien(ct):
    return {0: ct.sum(axis=1)}


def cellules(n, A, B, C):
    """Pour toutes les cellules [i, j] (i ≤ j < 16) : (comptes, erreur absolue, centre, élagués),
    l'erreur en unités 4^(e − emax) ; « élagués » = codes non nuls d'une cellule qui contient 0."""
    cn, cA, cB, cC = (np.concatenate([[0.0], np.cumsum(x)]) for x in (n, A, B, C))
    nz = np.where(VAL_O != 0, n, 0.0)
    cz = np.concatenate([[0.0], np.cumsum(nz)])
    out = {}
    for i in range(16):
        for j in range(i, 16):
            nn = cn[j + 1] - cn[i]
            a = cA[j + 1] - cA[i]
            if a > 0:
                b = cB[j + 1] - cB[i]
                d = max(cC[j + 1] - cC[i] - b * b / a, 0.0)
                r = b / a
            else:
                d, r = 0.0, 0.0
            el = (cz[j + 1] - cz[i]) if VAL_O[i] <= 0 <= VAL_O[j] else 0.0
            out[(i, j)] = (float(nn), float(d), float(r), float(el))
    return out


def dp_partition(cel, nk, E, mu, autorise=None):
    """Partition en intervalles minimisant Σ D/E + μ · n_s (−log2 n_s/n_k). Rend (bits, D, élagués, coupes)."""
    L = 16
    meilleur = [0.0] + [math.inf] * L
    arriere = [0] * (L + 1)
    for j in range(1, L + 1):
        for i in range(j):
            if autorise is not None and not autorise(i, j - 1):
                continue
            nn, d, _, _ = cel[(i, j - 1)]
            bits = 0.0 if nn == 0 else -nn * math.log2(nn / nk)
            v = meilleur[i] + d / E + mu * bits
            if v < meilleur[j]:
                meilleur[j] = v
                arriere[j] = i
    coupes = []
    j = L
    bits_tot = d_tot = el_tot = 0.0
    while j > 0:
        i = arriere[j]
        nn, d, _, el = cel[(i, j - 1)]
        bits_tot += 0.0 if nn == 0 else -nn * math.log2(nn / nk)
        d_tot += d
        el_tot += el
        if nn > 0:
            coupes.append((i, j - 1))
        j = i
    return bits_tot, d_tot, el_tot, coupes[::-1]


def evaluer_famille(src, mu, autorise=None, garder=False):
    bits = 0.0
    D = 0.0
    Dg = 0.0
    tables = 0
    zero = 0.0
    nz0 = 0.0
    plan = []
    if not hasattr(src, "cel"):
        src.cel = [cellules(n, A, B, C) for (t, k, n, A, B, C) in src.stats]
    for (t, k, n, A, B, C), cel in zip(src.stats, src.cel):
        norme = src.E if src.metrique == "globale" else src.Et[t] * src.T
        b, d, el, coupes = dp_partition(cel, n.sum(), norme, mu, autorise)
        bits += b
        D += d / norme
        Dg += d
        tables += len(coupes)
        zero += el
        nz0 += n[7] + n[8]
        if garder:
            plan.append((t, k, [(i, j, cel[(i, j)][2]) for (i, j) in coupes]))
    bpp = bits / src.N + tables * BITS_TABLE / src.N
    r = {"mu": mu, "bits_codes": bpp, "bits_total": bpp + FIXES, "erreur": D, "erreur_globale": Dg / src.E,
         "part_nulle": zero / src.N, "part_nulle_origine": nz0 / src.N, "cellules": tables}
    if garder:
        r["plan"] = plan
    return r


def base_frontiere(comptes, casser=False):
    """La base de 07 : centres communs pondérés par 4^e (ou non, cassure), débit H(base | κ)."""
    T = comptes.shape[0]
    e = np.arange(256)
    ef = comptes.sum(axis=(0, 2, 3))
    emax = int(np.nonzero(ef)[0].max())
    w = np.ones(256) if casser else 4.0 ** (e - emax)
    Ceq = comptes.sum(axis=(0, 2)).astype(np.float64)               # (256, 16)
    Wq = (Ceq * w[:, None]).sum(axis=0)
    Wm = Wq[:8] + Wq[8:]
    classes = np.array([0, 0, 1, 1, 1, 2, 2, 3])
    centres = np.array([(Wm[classes == k] * MAG[classes == k]).sum() / Wm[classes == k].sum() for k in range(4)])
    w4 = 4.0 ** (e - emax)
    Wq4 = (Ceq * w4[:, None]).sum(axis=0)
    Wm4 = Wq4[:8] + Wq4[8:]
    err = float((Wm4 * (MAG - centres[classes]) ** 2).sum() / (Wm4 * MAG ** 2).sum())
    # Erreur relative propre de chaque tenseur (mêmes centres communs), et leur moyenne.
    par_t = []
    for t in range(T):
        Ct = comptes[t].sum(axis=1).astype(np.float64)
        Wt = (Ct * w4[:, None]).sum(axis=0)
        Wmt = Wt[:8] + Wt[8:]
        par_t.append(float((Wmt * (MAG - centres[classes]) ** 2).sum() / (Wmt * MAG ** 2).sum()))
    bits = 0.0
    for t in range(T):
        for k, nek in ctx_kappa(comptes[t].astype(np.float64)).items():
            nq = nek.sum(axis=0)
            base = np.zeros(8)
            for q in range(16):
                base[(q >> 3) * 4 + classes[q & 7]] += nq[q]
            bits += entropie_bits(base)
    N = float(comptes.sum(dtype=np.float64))
    tables = T * 3 * 8
    h_code = entropie_bits(comptes.sum(axis=(0, 1, 2)).astype(np.float64)) / N
    return {"erreur_globale": err, "erreur": float(np.mean(par_t)), "erreur_par_tenseur": par_t,
            "bits_codes": bits / N + tables * BITS_TABLE / N,
            "bits_total": bits / N + tables * BITS_TABLE / N + FIXES,
            "centres_E2M1": [float(c) / 2 for c in centres], "H_code": h_code}


def elagage_magnitude(comptes, seuils):
    """Élagage par magnitude : dans chaque tenseur, |K| · 2^(e − emax_t) < 2^lt → 0, le reste exact ;
    débit H(code' | e), une table par (tenseur, e) ; ±0 fondus (codons synonymes) ; erreur relative
    moyenne par tenseur (et globale pour mémoire)."""
    T = comptes.shape[0]
    e = np.arange(256)
    ef = comptes.sum(axis=(0, 2, 3))
    emax = int(np.nonzero(ef)[0].max())
    w = 4.0 ** (e - emax)
    tot = comptes.sum(axis=2).astype(np.float64)                     # (T, 256, 16)
    N = float(tot.sum())
    Et = (tot * w[None, :, None] * VAL[None, None, :] ** 2).sum(axis=(1, 2))
    lignes = []
    for lt in seuils:
        bits = 0.0
        D = 0.0
        Dg = 0.0
        elag = 0.0
        tables = 0
        for t in range(T):
            es = np.nonzero(tot[t].sum(axis=1))[0]
            emax_t = es.max()
            Dt = 0.0
            for ee in es:
                n = tot[t, ee].copy()
                mag = np.abs(VAL) * 2.0 ** (ee - emax_t)
                coupe = (mag < 2.0 ** lt) & (np.abs(VAL) > 0)
                Dt += float((n[coupe] * w[ee] * VAL[coupe] ** 2).sum())
                elag += float(n[coupe].sum())
                n2 = n.copy()
                n2[0] += n2[coupe].sum() + n2[8]
                n2[8] = 0
                n2[coupe] = 0
                bits += entropie_bits(n2)
                tables += int((n2 > 0).sum())
            D += Dt / Et[t] / T
            Dg += Dt
        lignes.append({"log2_seuil_rel": lt, "bits_codes": bits / N + tables * BITS_TABLE / N,
                       "bits_total": bits / N + tables * BITS_TABLE / N + FIXES,
                       "erreur": D, "erreur_globale": Dg / Et.sum(), "part_elaguee": elag / N})
    return lignes


def interpoler(courbe, d_cible):
    """Débit à l'erreur d_cible, par interpolation linéaire sur la courbe triée par erreur."""
    pts = sorted((c["erreur"], c["bits_total"]) for c in courbe)
    for (d0, b0), (d1, b1) in zip(pts, pts[1:]):
        if d0 <= d_cible <= d1 and d1 > d0:
            return b0 + (b1 - b0) * (d_cible - d0) / (d1 - d0)
    return None


def main():
    histo, sortie_json, sortie_csv = sys.argv[1], sys.argv[2], sys.argv[3]
    casser = "--casser" in sys.argv
    z = np.load(histo)
    comptes = z["comptes"]
    base = base_frontiere(comptes, casser)
    res = {"histogramme": histo, "noms": [str(s) for s in z["noms"]], "casser": casser,
           "base": base, "seuils": {"perte_rapport_max": SEUIL_PERTE, "sans_perte_gain_min": SEUIL_SANS_PERTE},
           "couts_fixes_echelles": FIXES}
    mus = [0.0] + list(np.geomspace(1e-13, 1e-6, 120))
    familles = {}
    courbes_csv = []
    for nom, ctx in (("ecsq_kappa", ctx_kappa), ("ecsq_delta7", ctx_delta7), ("ecsq_e", ctx_e)):
        src = Source(comptes, ctx)
        familles[nom] = [evaluer_famille(src, mu) for mu in mus]
    # Élagage lagrangien : zone morte [−a, +a] autour de zéro, le reste en codes seuls.
    src_e = Source(comptes, ctx_e)

    def zone_morte(i, j):
        return i == j or (VAL_O[i] <= 0 <= VAL_O[j] and -VAL_O[i] == VAL_O[j]) or (i, j) == (7, 8)
    familles["elagage_lagrangien"] = [evaluer_famille(src_e, mu, zone_morte) for mu in mus]
    # Sans perte en valeur : seules les cellules {−0, +0} fondues ; identité stricte en témoin.
    src_k = Source(comptes, ctx_kappa)
    ident = evaluer_famille(src_k, 0.0, lambda i, j: i == j)
    fondu = evaluer_famille(src_k, 0.0, lambda i, j: i == j or (i, j) == (7, 8))
    src_ee = Source(comptes, ctx_e)
    ident_e = evaluer_famille(src_ee, 0.0, lambda i, j: i == j)
    fondu_e = evaluer_famille(src_ee, 0.0, lambda i, j: i == j or (i, j) == (7, 8))
    res["sans_perte"] = {"identite_kappa": ident, "zero_fondu_kappa": fondu,
                         "identite_e": ident_e, "zero_fondu_e": fondu_e,
                         "gain_zero_fondu_kappa": ident["bits_codes"] - fondu["bits_codes"],
                         "gain_contexte_e_sur_kappa": ident["bits_codes"] - ident_e["bits_codes"]}
    familles["elagage_magnitude"] = elagage_magnitude(comptes, list(np.linspace(-9, 1, 81)))
    # Pour mémoire : la même famille e sous la métrique globale de la frontière (ce qu'elle permet).
    src_g = Source(comptes, ctx_e, metrique="globale")
    mus_g = [0.0] + list(np.geomspace(1e-13, 1e-5, 120))
    familles["ecsq_e_metrique_globale"] = [evaluer_famille(src_g, mu) for mu in mus_g]
    res["familles"] = familles
    verdicts = {}
    for nom, courbe in familles.items():
        if nom.endswith("metrique_globale"):
            b = interpoler(courbe, base["erreur_globale"])
            verdicts[nom] = {"bits_total_a_erreur_globale_de_base": b, "pour_memoire": True}
            continue
        b = interpoler(courbe, base["erreur"])
        verdicts[nom] = {"bits_total_a_erreur_de_base": b,
                         "rapport_a_la_base": None if b is None else b / base["bits_total"],
                         "bat_la_base": None if b is None else bool(b <= SEUIL_PERTE * base["bits_total"])}
    res["verdicts_a_erreur_de_base"] = verdicts
    temoins = {
        "base_retrouve_07": bool(abs(base["erreur_globale"] / ERREUR_BASE_07 - 1) < 1e-6),
        "H_code_3_860": bool(abs(base["H_code"] - 3.860) < 5e-4),
        "identite_erreur_nulle": bool(ident["erreur"] < 1e-15),
    }
    res["temoins"] = temoins
    res["temoins_tiennent"] = all(temoins.values())
    with open(sortie_json, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    with open(sortie_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["famille", "parametre", "bits_total", "bits_codes", "erreur_relative_moyenne_par_tenseur",
                    "erreur_relative_globale", "part_elaguee"])
        for nom, courbe in familles.items():
            for c in courbe:
                w.writerow([nom, c.get("mu", c.get("log2_seuil_rel")), f"{c['bits_total']:.6f}",
                            f"{c['bits_codes']:.6f}", f"{c['erreur']:.8f}", f"{c['erreur_globale']:.8f}",
                            f"{c.get('part_nulle', c.get('part_elaguee', 0)):.6f}"])
        w.writerow(["base", "", f"{base['bits_total']:.6f}", f"{base['bits_codes']:.6f}", f"{base['erreur']:.8f}",
                    f"{base['erreur_globale']:.8f}", ""])
    print(json.dumps({"base": base, "verdicts": verdicts, "sans_perte": res["sans_perte"], "temoins": temoins},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
