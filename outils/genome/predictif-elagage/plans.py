"""Plans de reconstruction : pour une famille et une erreur visée, la table T[ctx][code] de chaque tenseur.

Une table donne, pour chaque contexte connu du décodeur et chaque code MXFP4, la valeur reconstruite
en grandeurs E2M1 doublées (K) : ŵ = T[ctx][code] · 2^(e − 128). Le multiplicateur μ commun est
cherché par dichotomie pour que l'erreur relative moyenne par tenseur égale la cible (celle de la
base, calculée par le même instrument).

Familles : base (la frontière, centres communs, signe gardé, contexte sans objet), identite (le
format, T = K : témoin, KL nulle attendue), ecsq_kappa, ecsq_delta7, ecsq_e, elagage_lagrangien.

Sorties : PLAN.npz (pour sortie_experts.py) et PLAN.bin (pour la sonde Rust, format du sous-
commande `alterer` : b"PEPL", u32 n, puis par tenseur u32 couche, u32 rôle, u32 mode (0 : δ de
ligne borné, 1 : e absolu), i32 a, i32 b, u32 n_col = 1, puis f64 × (b − a + 1) × 16).

Option --par-tenseur : un μ par tenseur, cherché pour que l'erreur relative de CHAQUE tenseur égale
celle de la base sur ce tenseur (domination tenseur par tenseur, au lieu d'une moyenne). Raison
(2026-10-17) : à erreur moyenne égale, ecsq_kappa abîme plus la couche 0 que la base (6,1 % contre
5,1 % d'erreur d'expert) et sa KL est plus haute de 0,0167 ± 0,0049 (appariée) : les couches ne
pèsent pas pareil dans la KL, une moyenne laisse l'optimiseur déplacer l'erreur vers les premières.

Utilisation : python -I -X utf8 plans.py HISTO.npz FAMILLE [--cible ERR | --mu MU | --par-tenseur] SORTIE_SANS_EXTENSION
"""
from __future__ import annotations

import json
import struct
import sys

import numpy as np

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import debit_distorsion as dd  # noqa: E402

ROLES = {"ffn_gate_exps": 0, "ffn_up_exps": 1, "ffn_down_exps": 2}
CTX = {"ecsq_kappa": (dd.ctx_kappa, "kappa"), "ecsq_delta7": (dd.ctx_delta7, "delta7"),
       "ecsq_e": (dd.ctx_e, "e"), "elagage_lagrangien": (dd.ctx_e, "e")}


def zone_morte(i, j):
    return i == j or (dd.VAL_O[i] <= 0 <= dd.VAL_O[j] and -dd.VAL_O[i] == dd.VAL_O[j]) or (i, j) == (7, 8)


def tables_depuis_plan(plan, mode, T):
    """plan : liste (t, k, [(i, j, r)]) → par tenseur, dict ctx → 16 valeurs (ordre des codes)."""
    out = [dict() for _ in range(T)]
    for (t, k, cellules) in plan:
        v = np.zeros(16)
        for (i, j, r) in cellules:
            for pos in range(i, j + 1):
                v[dd.ORDRE[pos]] = r
        out[t][k] = v
    return out


def binaire(noms, tables, mode, chemin):
    o = bytearray(b"PEPL")
    o += struct.pack("<I", len(noms))
    for nom, tab in zip(noms, tables):
        _, couche, role, _ = nom.split(".")
        couche = int(couche)
        if mode == "e":
            a, b, m = min(tab), max(tab), 1
        elif mode == "kappa":
            a, b, m = -1, 1, 0          # δ borné à ±1 : sous, égal, au-dessus = κ
        elif mode == "delta7":
            a, b, m = -3, 3, 0
        else:                            # base, identite, zero : un seul contexte
            a, b, m = 0, 0, 0
        o += struct.pack("<IIIiiI", couche, ROLES[role], m, a, b, 1)
        for c in range(a, b + 1):
            if mode == "kappa":
                v = tab[c + 1]
            elif mode in ("base", "identite", "zero"):
                v = tab[0]
            else:
                v = tab.get(c, np.zeros(16))   # contexte absent du tenseur : jamais lu
            o += np.asarray(v, dtype="<f8").tobytes()
    with open(chemin, "wb") as f:
        f.write(bytes(o))


def main():
    histo, famille, sortie = sys.argv[1], sys.argv[2], sys.argv[-1]
    z = np.load(histo)
    comptes = z["comptes"]
    noms = [str(s) for s in z["noms"]]
    T = comptes.shape[0]
    base = dd.base_frontiere(comptes)
    info = {"histogramme": histo, "famille": famille, "base": {k: base[k] for k in ("erreur", "erreur_globale", "bits_total")}}
    if famille in ("base", "identite", "zero"):
        if famille == "base":
            c = np.array(base["centres_E2M1"]) * 2
            cl = np.array([0, 0, 1, 1, 1, 2, 2, 3])
            v = np.concatenate([c[cl], -c[cl]])
            info.update({"erreur": base["erreur"], "bits_total": base["bits_total"]})
        else:
            v = dd.VAL.copy()
            if famille == "zero":
                v[8] = 0.0            # −0 → +0 : le codon synonyme fondu (valeur identique)
            info.update({"erreur": 0.0})
        tables = [{0: v} for _ in range(T)]
        mode = famille
    else:
        ctxf, mode = CTX[famille]
        src = dd.Source(comptes, ctxf)
        aut = zone_morte if famille == "elagage_lagrangien" else None
        if "--par-tenseur" in sys.argv:
            src.cel = [dd.cellules(n, A, B, C) for (t, k, n, A, B, C) in src.stats]
            plan_tot, bits_tot, errs, mus = [], 0.0, [], []
            for t in range(T):
                sous = dd.Source.__new__(dd.Source)
                idx = [i for i, st in enumerate(src.stats) if st[0] == t]
                sous.stats = [src.stats[i] for i in idx]
                sous.cel = [src.cel[i] for i in idx]
                sous.Et, sous.T, sous.E, sous.metrique = src.Et, 1, src.E, "par_tenseur"
                sous.N = float(sum(st[2].sum() for st in sous.stats))
                cible_t = base["erreur_par_tenseur"][t]
                lo, hi = 1e-16, 1e-4
                for _ in range(60):
                    mu_t = (lo * hi) ** 0.5
                    if dd.evaluer_famille(sous, mu_t, aut)["erreur"] > cible_t:
                        hi = mu_t
                    else:
                        lo = mu_t
                r_t = dd.evaluer_famille(sous, lo, aut, garder=True)
                plan_tot += r_t.pop("plan")
                bits_tot += r_t["bits_codes"] * sous.N
                errs.append(r_t["erreur"])
                mus.append(lo)
            r = {"bits_codes": bits_tot / src.N, "bits_total": bits_tot / src.N + dd.FIXES,
                 "erreur": float(np.mean(errs)), "erreur_par_tenseur": errs, "mu_par_tenseur": mus,
                 "plan": plan_tot}
            tables = tables_depuis_plan(r.pop("plan"), mode, T)
            info.update(r)
            mu = None
        elif "--mu" in sys.argv:
            mu = float(sys.argv[sys.argv.index("--mu") + 1])
        else:
            cible = float(sys.argv[sys.argv.index("--cible") + 1]) if "--cible" in sys.argv else base["erreur"]
            lo, hi = 1e-14, 1e-6
            for _ in range(60):
                mu = (lo * hi) ** 0.5
                r = dd.evaluer_famille(src, mu, aut)
                if r["erreur"] > cible:
                    hi = mu
                else:
                    lo = mu
            mu = lo
            info["cible"] = cible
        if mu is not None:
            r = dd.evaluer_famille(src, mu, aut, garder=True)
            tables = tables_depuis_plan(r.pop("plan"), mode, T)
            info.update(r)
    np.savez_compressed(sortie + ".npz", noms=np.array(noms), mode=np.array(mode),
                        **{f"t{t}_ctx": np.array(sorted(tables[t]), dtype=np.int64) for t in range(T)},
                        **{f"t{t}_val": np.array([tables[t][k] for k in sorted(tables[t])]) for t in range(T)})
    binaire(noms, tables, mode, sortie + ".bin")
    with open(sortie + ".json", "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=1, default=float)
    print(json.dumps(info, ensure_ascii=False, default=float))


if __name__ == "__main__":
    main()
