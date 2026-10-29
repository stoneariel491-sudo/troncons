"""P5 etape 2 : poids REELS (gpt-oss-20b), un expert a la fois (13 Mo de lecture : gate, up, down).

Meme mesure que l'etape 1 (Babai = synonyme.py::choisir, CD, PT), sur les vraies matrices : trois roles, H d'entree
pour gate et up, H sur la sortie swiglu pour down (comme synonyme.py::mesurer). R rangees tirees par matrice
(les rangees sont des problemes independants qui partagent H). Debit = H0 des symboles regroupes des trois
matrices ; erreur d'evaluation = energie de sortie ponderee g^2 sur les entrees des fenetres 0-9, tenues a
l'ecart, sommee sur les trois roles (absolue, donc ponderee par l'energie de chaque role) ;
gain = 1 - E(methode)/E(Babai lam=0), par rangee, donc sur le meme echantillon.

NE SE LANCE PAS sous le verrou ~/dev/verrou-carte.txt (le script refuse).
  python -I -X utf8 etape2.py --couche 8 --expert 0 --lignes 256 --pt-lignes 64 --damp 1 --lams 0 0.2 --sweeps 40
"""
import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p5lib as P  # noqa: E402
import etape1 as E1  # noqa: E402

syn = P.syn
CEN, C8 = E1.CEN, E1.C8
VERROU = "~/dev/verrou-carte.txt"
ROLES = ("gate", "up", "down")


def numerateur_par_rangee(W, Wh, X, g):
    """Pour chaque rangee r : sum_i g_i^2 ((W - Wh)_r . x_i)^2 ; idem pour le denominateur avec W."""
    w2 = g * g
    a = X @ (W - Wh).T
    b = X @ W.T
    return (w2[:, None] * a * a).sum(axis=0), (w2[:, None] * b * b).sum(axis=0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--couche", type=int, required=True)
    ap.add_argument("--expert", type=int, required=True)
    ap.add_argument("--lignes", type=int, default=256)
    ap.add_argument("--pt-lignes", type=int, default=64)
    ap.add_argument("--damp", type=float, default=1.0)
    ap.add_argument("--lams", type=float, nargs="+", default=[0.0, 0.2])
    ap.add_argument("--sweeps", type=int, default=40)
    ap.add_argument("--nt", type=int, default=8)
    ap.add_argument("--tlo", type=float, default=0.02)
    ap.add_argument("--thi", type=float, default=1.0)
    ap.add_argument("--trempe", type=int, default=30)
    ap.add_argument("--fils", type=int, default=2)
    ap.add_argument("--graine", type=int, default=20261027)
    ap.add_argument("--forcer", action="store_true", help="ignore le verrou (interdit sauf accord)")
    a = ap.parse_args()
    if os.path.exists(VERROU) and not a.forcer:
        print(json.dumps({"refus": "verrou-carte.txt present", "contenu": open(VERROU, encoding="utf-8", errors="replace").read()}))
        sys.exit(3)
    t0 = time.time()
    rng = np.random.default_rng(a.graine + 131 * a.couche + a.expert)
    m = syn.Modele()
    calib, ev = syn.Entrees("calib", a.couche), syn.Entrees("eval", a.couche)
    Xc, gc = calib.expert(a.expert)
    Xe, ge = ev.expert(a.expert)
    b = {r: m.biais(a.couche, r, a.expert) for r in ROLES}
    Ws, exs, codes_full = {}, {}, {}
    for role in ROLES:
        ex, codes = m.blocs(a.couche, role, a.expert)
        ex, codes = ex[0], codes[0]
        Ws[role], exs[role], codes_full[role] = syn.dequant(ex, codes), ex, codes
    Ac = syn.swiglu(Xc @ Ws["gate"].T + b["gate"], Xc @ Ws["up"].T + b["up"])
    Ae = syn.swiglu(Xe @ Ws["gate"].T + b["gate"], Xe @ Ws["up"].T + b["up"])
    entrees = {"gate": (Xc, Xe), "up": (Xc, Xe), "down": (Ac, Ae)}
    sortie = dict(couche=a.couche, expert=a.expert, damp=a.damp, lignes=a.lignes, pt_lignes=a.pt_lignes,
                  n_calib=int(Xc.shape[0]), n_eval=int(Xe.shape[0]), reglage=vars(a), roles={})
    # resultats par (methode, lam) : symboles et numerateurs par rangee pour chaque role
    cles = []
    acc = {}
    for role in ROLES:
        rows = np.sort(rng.choice(P.D, a.lignes, replace=False))
        W, ex, codes = Ws[role][rows], exs[role][rows], codes_full[role][rows]
        S = np.repeat(syn.echelle(ex), 32, axis=-1)
        sf = syn.sym_frontiere(codes)
        sf_full = syn.sym_frontiere(codes_full[role])
        ell = syn.longueurs(np.bincount(sf_full.ravel(), minlength=8).astype(np.float64))
        Xc_r, Xe_r = entrees[role]
        Htr = syn.hessienne(Xc_r, gc, a.damp)
        cfront = syn.cout_unitaire(W, syn.reconstruire(ex, sf, CEN), Htr)
        # le cache de U : H change par role
        E1._cache.clear()
        resultats = {}
        resultats[("frontiere", 0.0)] = P.sym_vers_niveau(sf)
        babai_lam0 = None
        for lam in a.lams:
            lamp = lam * cfront
            tb = time.time()
            Qb = P.sym_vers_niveau(syn.choisir(W, ex, CEN, Htr, lamp, ell))
            if lam == 0.0:
                babai_lam0 = Qb
            resultats[("babai", lam)] = Qb
            tb = time.time() - tb
            Wh = C8[Qb] * S
            err_b = float(np.einsum("ij,jk,ik->", W - Wh, Htr, W - Wh, optimize=True)) / W.size
            tc = time.time()
            Qc, _ = P.pt(Htr, W, S, C8, ell, lamp, Qb, np.array([1.0]), 0, trempe=a.trempe, seed=a.graine, fils=a.fils)
            resultats[("cd", lam)] = Qc
            tc = time.time() - tc
            if a.pt_lignes > 0:
                n = a.pt_lignes
                temps = E1.temperatures(err_b, a.nt, a.tlo, a.thi)
                tp = time.time()
                Qp, stp = P.pt(Htr, W[:n], S[:n], C8, ell, lamp, Qb[:n], temps, a.sweeps, every=1, trempe=a.trempe,
                               seed=a.graine, fils=a.fils)
                resultats[("pt", lam)] = Qp
                tp = time.time() - tp
                sortie["roles"].setdefault(role, {}).setdefault("pt", []).append(dict(lam=lam, t_s=tp, taux_echange=float(stp[:, 4].mean())))
            sortie["roles"].setdefault(role, {}).setdefault("temps", []).append(dict(lam=lam, babai_s=tb, cd_s=tc))
        for (meth, lam), Q in resultats.items():
            n = len(Q)
            Wh = C8[Q] * S[:n]
            num_e, den_e = numerateur_par_rangee(W[:n], Wh, Xe_r, ge)
            num_c, den_c = numerateur_par_rangee(W[:n], Wh, Xc_r, gc)
            acc.setdefault((meth, lam), {})[role] = dict(Q=Q, num_e=num_e, den_e=den_e, num_c=num_c, den_c=den_c)
    # agregation : par (methode, lam), sur les trois roles. Les methodes PT portent n = pt_lignes rangees par role ;
    # Babai et CD sont aussi evaluees sur ces memes premieres rangees pour la comparaison (cle "...@pt").
    lignes = []
    nref = a.pt_lignes if a.pt_lignes > 0 else a.lignes
    for (meth, lam), par_role in acc.items():
        for portee, n in (("toutes", None), ("pt", nref)):
            if meth == "pt" and portee == "toutes":
                continue
            if n is not None and meth == "frontiere":
                pass
            Ne = Ce = De = Dc = Nc = 0.0
            Qtout = []
            for role in ROLES:
                d = par_role[role]
                k = len(d["num_e"]) if n is None else min(n, len(d["num_e"]))
                Ne += d["num_e"][:k].sum(); De += d["den_e"][:k].sum()
                Nc += d["num_c"][:k].sum(); Dc += d["den_c"][:k].sum()
                Qtout.append(d["Q"][:k].ravel())
            Q = np.concatenate(Qtout)
            lignes.append(dict(methode=meth, lam=lam, portee=portee, bits_H0=P.entropie_symboles(Q),
                               err_eval=Ne / De, err_calib=Nc / Dc, num_eval=Ne, den_eval=De))
    sortie["lignes_res"] = lignes
    sortie["duree_s"] = time.time() - t0
    print(json.dumps(sortie, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
