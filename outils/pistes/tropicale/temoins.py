"""Témoins T1, T2, T3 de la garde tropicale (genome/pistes/tropicale/seuil-declare.md § 4).

T1 : la lecture numpy redonne le résumé commité de bascules.py ; cassures : un octet d'expert changé
     fait bouger le compte d'une unité ; une lecture au mauvais pas est refusée.
T2 : A contre C (routage de A imposé à C) : 0 bascule ; cassure : un expert changé dans C en fait une.
T3 : marges permutées : b(τ₁₀) ≈ 10 % ± 2 points ; marges oracles : b = 100 % pour c ≤ 4,2 %.

Usage : python -I -X utf8 temoins.py   (écrit mesures/pistes/tropicale/temoins.json)
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import routage as R  # noqa: E402

import numpy as np  # noqa: E402


def copie_cassee(source, couche, position, n_par_couche, nouvel_expert):
    """Écrit une copie du journal dont le premier expert de (couche, position) est remplacé."""
    o = bytearray(Path(source).read_bytes())
    d = 8 + (couche * n_par_couche + position) * 8
    o[d] = nouvel_expert
    f = tempfile.NamedTemporaryFile(delete=False, suffix=".bin")
    f.write(o)
    f.close()
    return Path(f.name)


def expert_absent(ens):
    return next(x for x in range(32) if x not in set(int(v) for v in ens))


def main():
    R.sous_la_normale()
    R.attendre_calme()
    res = {"outil": "outils/pistes/tropicale/temoins.py"}
    ea, ma = R.lire(R.A)
    eb, mb = R.lire(R.B)
    ec, mc = R.lire(R.C)
    L, N = ma.shape
    for nom, e in (("A", ea), ("B", eb), ("C", ec)):
        doublons = int(np.sum(np.any(e[:, :, 1:] == e[:, :, :-1], axis=2)))
        res[f"cellules_a_expert_double_{nom}"] = doublons  # 0 attendu : l'ensemble trié vaut le frozenset

    # T1, la lecture contre le résumé commité de bascules.py
    publie = json.loads((R.DEPOT / "mesures/moteur/R/r1/bascules-openai-llamacpp-20b.json").read_text(encoding="utf-8"))
    bas = R.bascules(ea, eb)
    q_toutes = R.quantiles_bascules_py(ma.ravel())
    q_bas = R.quantiles_bascules_py(ma[bas])
    t1_egal = (int(bas.sum()) == publie["bascules"] and L * N == publie["couches_positions"]
               and q_toutes == publie["marges_toutes_quantiles"] and q_bas == publie["marges_des_bascules_quantiles"])
    # cassure 1 : un expert changé dans une cellule sans bascule
    ll, pp = map(int, np.argwhere(~bas)[0])
    cas = copie_cassee(R.B, ll, pp, N, expert_absent(eb[ll, pp]))
    eb_c, _ = R.lire(cas)
    n_casse = int(R.bascules(ea, eb_c).sum())
    cas.unlink()
    # cassure 2 : mauvais pas
    try:
        R.lire(R.B, pas=7)
        pas_refuse = False
    except ValueError:
        pas_refuse = True
    res["T1"] = {
        "bascules_lues": int(bas.sum()), "bascules_publiees": publie["bascules"],
        "quantiles_toutes_lus": q_toutes, "quantiles_bascules_lus": q_bas,
        "egal_au_resume_publie": t1_egal,
        "cassure_octet_expert": {"cellule": [ll, pp], "bascules": n_casse, "attendu": int(bas.sum()) + 1,
                                 "tombe": n_casse == int(bas.sum()) + 1},
        "cassure_mauvais_pas_refusee": pas_refuse,
        "tient": bool(t1_egal and n_casse == int(bas.sum()) + 1 and pas_refuse),
    }

    # T2, la réponse connue d'avance : routage imposé
    n_ac = int(R.bascules(ea, ec).sum())
    cas = copie_cassee(R.C, 7, 1000, N, expert_absent(ec[7, 1000]))
    ec_c, _ = R.lire(cas)
    n_ac_c = int(R.bascules(ea, ec_c).sum())
    cas.unlink()
    res["T2"] = {"bascules_A_contre_C": n_ac, "attendu": 0,
                 "cassure_un_expert_change": {"cellule": [7, 1000], "bascules": n_ac_c, "attendu": 1},
                 "ecart_des_marges_B_contre_C_mediane": float(np.median(np.abs(mb - mc))),
                 "tient": n_ac == 0 and n_ac_c == 1}

    # T3, l'instrument discrimine
    tau10 = R.tau_decile(mb)
    rng = np.random.default_rng(20261021)
    perm = rng.permutation(mb.ravel()).reshape(mb.shape)
    tau10_p = R.tau_decile(perm)
    _, b_perm, nc_p, _ = R.courbe(perm, bas, np.array([tau10_p]))
    oracle = np.where(bas, 0.0, mb).astype(np.float32)
    tau_o = np.nextafter(np.float32(0), np.float32(1))  # le plus petit τ > 0
    c_o, b_o, _, _ = R.courbe(oracle, bas, np.array([tau_o]))
    res["T3"] = {
        "permutees": {"graine": 20261021, "tau10": tau10_p, "part_cellules": float(nc_p[0] / mb.size),
                      "part_bascules": float(b_perm[0]), "attendu": "0,10 ± 0,02",
                      "tient": abs(float(b_perm[0]) - 0.10) <= 0.02},
        "oracles": {"part_cellules": float(c_o[0]), "part_bascules": float(b_o[0]),
                    "attendu": "b = 1 pour c ≤ 0,042", "tient": float(b_o[0]) == 1.0 and float(c_o[0]) <= 0.042},
    }
    res["T3"]["tient"] = res["T3"]["permutees"]["tient"] and res["T3"]["oracles"]["tient"]
    res["tous_tiennent"] = bool(res["T1"]["tient"] and res["T2"]["tient"] and res["T3"]["tient"]
                                and all(res[f"cellules_a_expert_double_{n}"] == 0 for n in "ABC"))
    R.SORTIE.mkdir(parents=True, exist_ok=True)
    (R.SORTIE / "temoins.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
