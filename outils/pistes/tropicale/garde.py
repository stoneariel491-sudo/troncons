"""La courbe de la garde tropicale : (part des cellules sous τ, part des bascules sous τ).

Chemin principal (numpy) du point de décision b(τ₁₀) déclaré dans seuil-declare.md § 3, et les
mesures qui ne décident pas (§ 5) : par couche, marge de A, min(A, B), positions notées seules, K3 d1.

Usage : python -I -X utf8 garde.py
Écrit, sous mesures/pistes/tropicale/ : garde-resume.json, courbe-garde.csv (toutes variantes,
τ de 1e-4 à 1e-1), courbe-garde-par-couche.csv, decile-par-couche.csv.
"""

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import routage as R  # noqa: E402

import numpy as np  # noqa: E402


def point_decile(m, bas, part=0.10):
    t = R.tau_decile(m, part)
    nc = int(np.sum(m < t))
    nb = int(np.sum(m[bas] < t))
    return {"tau": t, "cellules_signalees": nc, "part_cellules": nc / m.size,
            "bascules_signalees": nb, "part_bascules": nb / int(bas.sum())}


def cout_de(m, bas, cible=0.80):
    """Le plus petit τ qui attrape `cible` des bascules, et la part des cellules qu'il signale."""
    s = np.sort(m[bas])
    k = int(np.ceil(cible * s.size)) - 1
    t = float(np.nextafter(s[k], np.float32(np.inf)))  # τ juste au-dessus de la k-ième marge de bascule
    return {"tau": t, "part_bascules": float(np.mean(m[bas] < t)), "part_cellules": float(np.mean(m < t))}


def main():
    R.sous_la_normale()
    R.attendre_calme()
    ea, ma = R.lire(R.A)
    eb, mb = R.lire(R.B)
    L, N = mb.shape
    bas = R.bascules(ea, eb)
    taus = R.grille()

    # positions notées par le juge : celles du CSV de KL (fenêtre, position)
    kl = list(csv.DictReader(open(R.DEPOT / "mesures/moteur/R/r1/juge-kl-ref-llamacpp-20b-contre-ref-openai-20b.csv", encoding="utf-8")))
    notees = np.zeros(N, dtype=bool)
    for r in kl:
        notees[int(r["fenetre"]) * R.LONG + int(r["position"])] = True

    variantes = {
        "marge_B": (mb, bas),
        "marge_A": (ma, bas),
        "min_AB_oracle": (np.minimum(ma, mb), bas),
        "marge_B_positions_notees": (mb[:, notees], bas[:, notees]),
    }
    res = {"outil": "outils/pistes/tropicale/garde.py", "cellules": int(L * N), "bascules": int(bas.sum()),
           "part_bascules": float(bas.mean()), "positions_notees": int(notees.sum()), "variantes": {}}
    lignes = []
    for nom, (m, b) in variantes.items():
        c, bb, nc, nb = R.courbe(m, b, taus)
        res["variantes"][nom] = {
            "decile": point_decile(m, b),
            "cout_de_80_pour_cent": cout_de(m, b),
            "auc_marge_contre_bascule": R.auc(m, b),
            "cellules": int(m.size), "bascules": int(b.sum()),
        }
        for t, x, y, u, v in zip(taus, c, bb, nc, nb):
            lignes.append([nom, f"{t:.6e}", f"{x:.6f}", f"{y:.6f}", int(u), int(v)])
    with open(R.SORTIE / "courbe-garde.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["variante", "tau", "part_cellules", "part_bascules", "cellules_sous_tau", "bascules_sous_tau"])
        w.writerows(lignes)

    # par couche, marge de B
    par = []
    dec = []
    for l in range(L):
        c, bb, nc, nb = R.courbe(mb[l], bas[l], taus)
        for t, x, y, u, v in zip(taus, c, bb, nc, nb):
            par.append([l, f"{t:.6e}", f"{x:.6f}", f"{y:.6f}", int(u), int(v)])
        tg = res["variantes"]["marge_B"]["decile"]["tau"]  # le τ global, appliqué à la couche
        dec.append([l, int(bas[l].sum()), f"{bas[l].mean():.6f}",
                    f"{np.mean(mb[l] < tg):.6f}", f"{(np.mean(mb[l][bas[l]] < tg) if bas[l].any() else float('nan')):.6f}",
                    f"{np.median(mb[l]):.6e}", f"{(np.median(mb[l][bas[l]]) if bas[l].any() else float('nan')):.6e}",
                    f"{R.auc(mb[l], bas[l]):.4f}"])
    with open(R.SORTIE / "courbe-garde-par-couche.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["couche", "tau", "part_cellules", "part_bascules", "cellules_sous_tau", "bascules_sous_tau"])
        w.writerows(par)
    with open(R.SORTIE / "decile-par-couche.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["couche", "bascules", "taux_bascule", "part_cellules_sous_tau10_global",
                    "part_bascules_sous_tau10_global", "marge_mediane", "marge_mediane_aux_bascules", "auc"])
        w.writerows(dec)

    # contrôle croisé K3 d1 : moteur de la carte contre la référence, marge de la référence
    k3 = list(csv.DictReader(open(R.K3, encoding="utf-8")))
    mk = np.array([float(r["marge_reference"]) for r in k3], dtype=np.float32)
    bk = np.array([r["ensemble_different"] == "1" for r in k3])
    res["K3_d1"] = {"cellules": int(mk.size), "bascules": int(bk.sum()), "decile": point_decile(mk, bk),
                    "auc_marge_contre_bascule": R.auc(mk, bk), "marges_aux_bascules": sorted(float(x) for x in mk[bk])}

    # le verdict, selon le seuil déclaré
    p = res["variantes"]["marge_B"]["decile"]
    res["seuil_declare"] = "b(tau10) >= 0,80 avec la marge de B, toutes cellules (seuil-declare.md § 3)"
    res["verdict"] = "LA GARDE PASSE" if p["part_bascules"] >= 0.80 else "LA GARDE TOMBE"
    (R.SORTIE / "garde-resume.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("cellules", "bascules", "verdict")}, ensure_ascii=False))
    for nom, v in res["variantes"].items():
        d, c8 = v["decile"], v["cout_de_80_pour_cent"]
        print(f"{nom:28s} tau10={d['tau']:.5f} c={d['part_cellules']:.4f} b={d['part_bascules']:.4f}"
              f"  | 80 % des bascules : tau={c8['tau']:.2e} c={c8['part_cellules']:.4f}  | AUC={v['auc_marge_contre_bascule']:.4f}")
    k = res["K3_d1"]
    print(f"K3 d1 : {k['bascules']} bascules / {k['cellules']} ; b(tau10)={k['decile']['part_bascules']:.3f} ; AUC={k['auc_marge_contre_bascule']:.3f}")
    for r in dec:
        print("couche", *r)


if __name__ == "__main__":
    main()
