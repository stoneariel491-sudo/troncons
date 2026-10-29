"""Juge des chiffres du lot « espaces latents », second flux : III-7.6 (petits multiples, marge z(1) − z(2),
bords des groupes, noms des experts), refait à la source par un chemin écrit de zéro.

Écrit pour troncons le 2026-10-27. Sources : captures de calibration de la couche 23 (h-L23.f32), routeur de
la couche 23 relu dans le GGUF (blk.23.ffn_gate_inp.weight et .bias), coordonnées commitées de
mesures/genome/tome3/latents/etats-c23.csv (l'ACP et la t-SNE n'ont pas d'autre source : le juge du premier
flux les a régénérées au bit). Comparé à : les données de figure commitées (memoire/figures/tome3/donnees/
latents-etats-*.csv, latents-chiffres.tex, latents-temoins.json) et au JSON du juge du premier flux pour
les bords de l'espace d'origine, que la légende cite.

Chemin du juge :
  - logits z = W h + b relus à la source ; expert premier ; marge z(1) − z(2) ; ses quantiles (interpolation
    linéaire écrite ici) ; les états sous le 10e centile ;
  - bord d'un état (part de ses 10 plus proches voisins d'un autre expert premier) : dans le plan de la
    t-SNE par un arbre k-d (scipy), dans l'espace d'origine (2 880 dimensions) par blocs de distances, sans
    matrice n × n ; par classe de marge (sous le 10e centile, jusqu'à la médiane, au-delà), pour z(1) − z(2)
    et pour z(4) − z(5) ;
  - les noms des experts : l'ancre (l'état du groupe dont la moyenne des distances à ses 30 plus proches
    voisins du même groupe est minimale) refaite ; les boîtes des noms (10 % × 7,5 % de l'étendue) : quelles
    paires se recouvrent aux ancres, et plus après l'écartement ; la pureté autour de chaque ancre (part de ses
    30 plus proches voisins, tous états, qui sont de son groupe) : un nom posé dans une région d'un autre
    groupe tromperait l'œil ;
  - chaque ligne des CSV de figure contrôlée contre la source, et un point tiré par série (graine du juge).

  python -I -X utf8 juge2_etats.py [--casser] > juge2-etats.json      (~3 min, < 1 Go)
"""
from __future__ import annotations

import csv
import json
import math
import pathlib
import re
import sys

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from juge2_lecteurs import CAPT, LecteurGguf, N  # noqa: E402

DEPOT = pathlib.Path("~/dev/active/troncons")
LAT = DEPOT / "mesures/genome/tome3/latents"
DON = DEPOT / "memoire/figures/tome3/donnees"
JUGE1 = DEPOT / "outils/genome/tome3/juge-latents/juge-etats-marges.json"
GRAINE = 2710202602
K = 10
K_REP = 30
BOITE = (0.10, 0.075)


def csv_dicts(p: pathlib.Path) -> list[dict]:
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def macros(p: pathlib.Path) -> dict[str, str]:
    out = {}
    for ligne in p.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\\providecommand\{\\Lat(\w+)\}\{\\EF\{(.*?)\}\{", ligne)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def arrondi_egal(ecrit: str, vrai: float) -> bool:
    s = ecrit.replace("\\,", "").replace("\\ensuremath{-}", "-")
    dec = len(s.split(".")[1]) if "." in s else 0
    return abs(float(s) - round(vrai, dec)) < 10 ** (-dec) / 2 + 1e-12


def quantile_lineaire(x: np.ndarray, q: float) -> float:
    s = np.sort(x)
    r = q * (len(s) - 1)
    i = int(math.floor(r))
    return float(s[i] + (r - i) * (s[min(i + 1, len(s) - 1)] - s[i]))


def voisins_origine(X: np.ndarray, k: int, bloc: int = 256) -> np.ndarray:
    n = len(X)
    n2 = np.einsum("ij,ij->i", X, X)
    out = np.empty((n, k), dtype=np.int64)
    for a in range(0, n, bloc):
        b = min(n, a + bloc)
        d = n2[a:b, None] + n2[None, :] - 2.0 * (X[a:b] @ X.T)
        d[np.arange(b - a), np.arange(a, b)] = np.inf
        idx = np.argpartition(d, k, axis=1)[:, :k]
        out[a:b] = idx
    return out


def bords(vois: np.ndarray, premier: np.ndarray, classe: np.ndarray) -> list[float]:
    b = (premier[vois] != premier[:, None]).mean(1)
    return [float(b[classe == c].mean()) for c in range(3)], b


def rangs(x: np.ndarray) -> np.ndarray:
    o = np.argsort(x, kind="mergesort")
    r = np.empty(len(x))
    r[o] = np.arange(len(x))
    return r


def main() -> int:
    rng = np.random.default_rng(GRAINE)
    R: dict = {"outil": "outils/genome/tome3/juge2-latents/juge2_etats.py", "graine": GRAINE}
    mac = macros(DON / "latents-chiffres.tex")
    j = json.loads((LAT / "etats-c23.json").read_text(encoding="utf-8"))
    rows = csv_dicts(LAT / "etats-c23.csv")
    n = len(rows)
    pos = np.array([int(r["position"]) for r in rows])
    premier_csv = np.array([int(r["premier"]) for r in rows])
    m12_csv = np.array([float(r["marge12"]) for r in rows])
    m45_csv = np.array([float(r["marge45"]) for r in rows])
    acp = np.array([[float(r["acp1"]), float(r["acp2"])] for r in rows])
    tsne = np.array([[float(r["tsne1"]), float(r["tsne2"])] for r in rows])

    # ---------------------------------------------------------------- logits relus à la source
    g = LecteurGguf()
    Wr = g.f32("blk.23.ffn_gate_inp.weight")          # (32, 2 880)
    br = g.f32("blk.23.ffn_gate_inp.bias").reshape(-1)
    h = np.fromfile(f"{CAPT}/h-L23.f32", dtype="<f4").reshape(-1, N).astype(np.float64)
    z = h @ Wr.T + br
    zs = -np.sort(-z, axis=1)
    premier = np.argmax(z, axis=1)
    m12 = zs[:, 0] - zs[:, 1]
    m45 = zs[:, 3] - zs[:, 4]
    R["logits"] = {"forme_routeur": list(Wr.shape), "premier_egal_au_csv": int((premier[pos] == premier_csv).sum()),
                   "marge12_ecart_relatif_max": float(np.max(np.abs(m12[pos] / m12_csv - 1))),
                   "marge45_ecart_relatif_max": float(np.max(np.abs(m45[pos] / m45_csv - 1)))}
    m12, m45, premier = m12[pos], m45[pos], premier[pos]
    Xh = h[pos]
    del h

    q10, q50 = quantile_lineaire(m12, 0.1), quantile_lineaire(m12, 0.5)
    q10j, q50j = j["marge12_quantiles"]["0.1"], j["marge12_quantiles"]["0.5"]
    cl12 = np.where(m12 < q10, 0, np.where(m12 < q50, 1, 2))
    p10, p50 = quantile_lineaire(m45, 0.1), quantile_lineaire(m45, 0.5)
    cl45 = np.where(m45 < p10, 0, np.where(m45 < p50, 1, 2))
    R["marge12"] = {"q10": q10, "q50": q50, "q10_json": q10j, "q50_json": q50j,
                    "sous_q10": int((cl12 == 0).sum()), "effectifs": [int((cl12 == c).sum()) for c in range(3)]}

    # ---------------------------------------------------------------- les groupes et leurs parts
    cpt = np.bincount(premier, minlength=32)
    ordre = sorted(range(32), key=lambda e: (-cpt[e], e))
    huit = ordre[:8]
    grp = {e: f"g{i + 1}" for i, e in enumerate(huit)}
    noms = ["Un", "Deux", "Trois", "Quatre", "Cinq", "Six", "Sept", "Huit"]
    R["groupes"] = {"huit": [(int(e), int(cpt[e]), 100 * cpt[e] / n) for e in huit],
                    "part_huit": 100 * cpt[huit].sum() / n, "distincts": int((cpt > 0).sum()),
                    "hasard_somme_p2": 100 * float(((cpt / n) ** 2).sum())}

    # ---------------------------------------------------------------- bords
    _, vt = cKDTree(tsne).query(tsne, k=K + 1)
    vt = np.array([[v for v in ligne if v != i][:K] for i, ligne in enumerate(vt)])
    b12_t, bt = bords(vt, premier, cl12)
    b45_t, _ = bords(vt, premier, cl45)
    vo = voisins_origine(Xh, K)
    b12_o, bo = bords(vo, premier, cl12)
    b45_o, _ = bords(vo, premier, cl45)
    j1 = json.loads(JUGE1.read_text(encoding="utf-8"))
    tem = json.loads((DON / "latents-temoins.json").read_text(encoding="utf-8"))
    rho_o = float(np.corrcoef(rangs(m12), rangs(bo))[0, 1])
    R["bords"] = {
        "z12_tsne": b12_t, "z12_tsne_lot_B1": tem["B1_bord_tsne"]["ici"],
        "z12_tsne_ecart_au_lot": float(max(abs(a - b) for a, b in zip(b12_t, tem["B1_bord_tsne"]["ici"]))),
        "z12_origine": b12_o, "z12_origine_juge1": j1["marge12"]["bord_origine"],
        "z45_origine": b45_o, "z45_origine_juge1": j1["marge45"]["bord_origine"],
        "z45_tsne": b45_t,
        "spearman_marge12_bord_origine": rho_o,
        "lecture": "la phrase de tête dit : les états de petite marge se tiennent sur les bords des groupes",
    }

    # ---------------------------------------------------------------- les noms des experts
    reps = csv_dicts(DON / "latents-etats-reperes.csv")
    noms_res = {}
    for plan, P, cx, cy, lx, ly in (("acp", acp, "acpx", "acpy", "acplx", "acply"),
                                    ("tsne", tsne, "tsnex", "tsney", "tsnelx", "tsnely")):
        arbre_tous = cKDTree(P)
        ancres, etiq, pur = [], [], []
        for i, e in enumerate(huit):
            Q = P[premier == e]
            d, _ = cKDTree(Q).query(Q, k=min(K_REP, len(Q) - 1) + 1)
            moy = d[:, 1:].mean(1)
            a = Q[int(np.argmin(moy))]
            ancres.append(a)
            r = reps[i]
            assert int(r["expert"]) == e
            etiq.append([float(r[lx]), float(r[ly])])
            _, iv = arbre_tous.query(a, k=K_REP + 1)
            pur.append(float(np.mean(premier[iv[1:]] == e)))
        ancres, etiq = np.array(ancres), np.array(etiq)
        anc_csv = np.array([[float(r[cx]), float(r[cy])] for r in reps])
        et = P.max(0) - P.min(0)
        bx, by = BOITE[0] * et[0], BOITE[1] * et[1]

        def recouvrements(Z):
            out = []
            for a in range(8):
                for b in range(a + 1, 8):
                    if abs(Z[a, 0] - Z[b, 0]) < bx - 1e-9 and abs(Z[a, 1] - Z[b, 1]) < by - 1e-9:
                        out.append((int(huit[a]), int(huit[b])))
            return out
        deplace = [int(huit[i]) for i in range(8) if np.hypot(*(etiq[i] - ancres[i])) > 1e-6]
        noms_res[plan] = {
            "ancres_ecart_max_au_csv": float(np.abs(ancres - anc_csv).max()),
            "paires_qui_se_recouvrent_aux_ancres": recouvrements(ancres),
            "paires_qui_se_recouvrent_apres": recouvrements(etiq),
            "noms_deplaces": deplace,
            "deplacement_en_part_de_l_etendue": {int(huit[i]): float(np.hypot(*((etiq[i] - ancres[i]) / et)))
                                                 for i in range(8)},
            "purete_des_30_voisins_a_l_ancre": {int(huit[i]): pur[i] for i in range(8)},
        }
    R["noms"] = noms_res

    # ---------------------------------------------------------------- les CSV de figure, ligne par ligne
    attendu_classe = {0: "petite"}
    ctl = {}
    for plan, P in (("acp", acp), ("tsne", tsne)):
        f = csv_dicts(DON / f"latents-etats-{plan}.csv")
        cle = {(round(P[i, 0], 6), round(P[i, 1], 6)): i for i in range(n)}
        mal = 0
        vus = set()
        for r in f:
            i = cle[(round(float(r["x"]), 6), round(float(r["y"]), 6))]
            vus.add(i)
            ok = (r["groupe"] == grp.get(int(premier[i]), "autres")
                  and r["marge"] == attendu_classe.get(int(cl12[i]), "autre"))
            mal += not ok
        petites = [r["marge"] == "petite" for r in f]
        it = int(rng.integers(len(f)))
        i = cle[(round(float(f[it]["x"]), 6), round(float(f[it]["y"]), 6))]
        ctl[plan] = {"lignes": len(f), "etats_distincts": len(vus), "lignes_fausses": mal,
                     "petites_en_dernier": all(petites[len(f) - sum(petites):]),
                     "point_tire": {"ligne": it, "csv": f[it], "position": int(pos[i]), "premier": int(premier[i]),
                                    "marge12": float(m12[i])}}
    for k, e in enumerate(huit):
        f = csv_dicts(DON / f"latents-etats-tsne-g{k + 1}.csv")
        cle = {(round(tsne[i, 0], 6), round(tsne[i, 1], 6)): i for i in range(n)}
        ids = [cle[(round(float(r["x"]), 6), round(float(r["y"]), 6))] for r in f]
        it = int(rng.integers(len(f)))
        ctl[f"tsne-g{k + 1}"] = {"expert": int(e), "lignes": len(f), "attendu": int(cpt[e]),
                                 "tous_de_cet_expert": bool(all(premier[i] == e for i in ids)),
                                 "classes_justes": bool(all(r["marge"] == attendu_classe.get(int(cl12[i]), "autre")
                                                            for r, i in zip(f, ids))),
                                 "point_tire": {"ligne": it, "position": int(pos[ids[it]]),
                                                "marge12": float(m12[ids[it]]), "csv": f[it]}}
    R["csv_figure"] = ctl

    # ---------------------------------------------------------------- nombres écrits, nouveaux ou déplacés
    j1e = json.loads((DEPOT / "outils/genome/tome3/juge-latents/juge-etats.json").read_text(encoding="utf-8"))
    v = {"MargeDouzeDix": q10, "MargeDouzeMed": q50, "Fragiles": int((cl12 == 0).sum()),
         "BordFragile": b12_t[0], "BordMoyen": b12_t[1], "BordLarge": b12_t[2],
         "BordOrigFragile": b12_o[0], "BordOrigLarge": b12_o[2], "BordQuatreCinq": b45_o[0],
         "BordRhoOrig": rho_o,
         "TsneGainT": j1e["tsne"]["T"] - j1e["acp"]["T"], "TsneGainC": j1e["tsne"]["C"] - j1e["acp"]["C"],
         "GroupesPart": 100 * cpt[huit].sum() / n, "AutresExperts": int((cpt > 0).sum()) - 8,
         "AccordHasard": 100 * float(((cpt / n) ** 2).sum()), "KRepere": K_REP, "KBord": K, "KBordCasse": K - 1,
         "MargeQuantile": 10}
    for i, e in enumerate(huit):
        v[f"Groupe{noms[i]}"] = int(e)
        v[f"Groupe{noms[i]}Part"] = 100 * cpt[e] / n
    # témoin du comparateur (--casser) : chaque valeur du juge faussée de 1 % ; les nombres écrits doivent tomber
    fac = 1.01 if "--casser" in sys.argv else 1.0
    R["casser"] = "--casser" in sys.argv
    R["nombres"] = {k: {"ecrit": mac[k], "juge": fac * float(x), "egal": arrondi_egal(mac[k], fac * float(x))}
                    for k, x in v.items()}
    R["nombres_qui_tombent"] = sorted(k for k, d in R["nombres"].items() if not d["egal"])
    R["nombres_tous_egaux"] = all(d["egal"] for d in R["nombres"].values())
    print(json.dumps(R, ensure_ascii=False, indent=1, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
