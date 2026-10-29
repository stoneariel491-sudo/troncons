"""Juge des chiffres du lot « espaces latents », second flux : III-9.7 (fonction d'appui, rose, cône, barres)
et III-9.1 (d) (la rangée, sa bande, sa phrase de tête), refaits à la source par un chemin écrit de zéro.

Écrit pour troncons le 2026-10-27. Sources : le GGUF de gpt-oss-20b (blk.8.ffn_gate_exps.weight, expert 0),
les .sym du lot B (frontiere, synonyme-l1-d1 ; L08-E01 pour la cassure du lecteur), les captures de
calibration de la couche 8 (h-L08.f32, routage-L08.bin). Comparé à : les fichiers commités du lot
(mesures/genome/tome3/latents/nuage-*, rangee-*), ses données de figure (memoire/figures/tome3/donnees/
latents-appui-*, -rose-*, -barres.csv, -rangee*.csv, latents-chiffres.tex) et le spectre du lot B
(mesures/genome/construction/synonyme/figures/spectre-L08-E00-gate.csv).

Chemin du juge, indépendant de celui du lot :
  - ΔW = W − Ŵ relu à la source, H = Σ g² x xᵀ / Σ g² sur les entrées de l'expert 0 relues dans les
    captures, ses axes propres u_k (signe : moyenne de u_kᵀx positive, la convention dite par le lot) ;
  - M = Bᵀ ΔWᵀ ΔW B calculée depuis ΔW (le lot la retrouve de ses ellipses commitées par moindres carrés) ;
    et, pour un second contrôle, M estimée des ellipses commitées par leurs moments d'ordre deux
    (M = 2 · moyenne(p pᵀ) / F² sur les 180 points distincts, à paramètre régulier) ;
  - la fonction d'appui h(v) = ‖ΔW B v‖ comparée aux 361 angles de chaque CSV ; un angle tiré par série ;
  - la rose (tranches de 3°) recomptée sur mes propres coordonnées, le cône à 90 %, son plus grand rapport ;
  - **l'erreur de sortie des entrées réelles**, ‖ΔW_s x‖ / ‖ΔW_f x‖, entrée par entrée, dans les 2 880
    dimensions, et la même chose pour leur projection sur le plan (u1, u2) : c'est ce que la phrase de tête
    de III-9.7 affirme (« là où pointent les entrées… au plus 0,135 »).
Témoin du lecteur : ‖W − Ŵ‖²_F = Σ_k e_k du spectre commité du lot B (frontière et synonyme) ; cassure :
les .sym d'un autre expert (L08-E01), l'égalité doit tomber.

  python -I -X utf8 juge2_nuage_rangee.py [--casser] > juge2-nuage-rangee.json      (~1 min, < 1,5 Go)
"""
from __future__ import annotations

import csv
import json
import math
import pathlib
import re
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from juge2_lecteurs import SYM, LecteurGguf, VALEUR_CODE, captures, lire_sym, poids, reconstruit  # noqa: E402

DEPOT = pathlib.Path("~/dev/active/troncons")
LAT = DEPOT / "mesures/genome/tome3/latents"
DON = DEPOT / "memoire/figures/tome3/donnees"
SPECTRE = DEPOT / "mesures/genome/construction/synonyme/figures/spectre-L08-E00-gate.csv"
GRAINE = 2710202602            # graine du juge du second flux
TENSEUR = "blk.8.ffn_gate_exps.weight"


def csv_dicts(p: pathlib.Path) -> list[dict]:
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def macros(p: pathlib.Path) -> dict[str, str]:
    """Les macros \\LatX de latents-chiffres.tex : valeur anglaise (ou brute)."""
    out = {}
    for ligne in p.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\\providecommand\{\\Lat(\w+)\}\{\\EF\{(.*?)\}\{", ligne)
        if m:
            out[m.group(1)] = m.group(2)
            continue
        m = re.match(r"\\expandafter\\providecommand\\csname Lat(\w+)\\endcsname\{(.*)\}", ligne)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def num(s: str) -> float:
    s = s.replace("\\,", "").replace("\\ensuremath{-}", "-").replace("$", "")
    m = re.match(r"([-\d.]+)\\times10\^\{(-?\d+)\}", s)
    if m:
        return float(m.group(1)) * 10 ** int(m.group(2))
    return float(s)


def arrondi_egal(ecrit: str, vrai: float) -> bool:
    """Le nombre écrit est-il l'arrondi de la valeur vraie à ses décimales écrites ?"""
    s = ecrit.replace("\\,", "").replace("\\ensuremath{-}", "-")
    if "times10" in s:
        m = re.match(r"\$?([-\d.]+)\\times10\^\{(-?\d+)\}", s)
        mant, ex = m.group(1), int(m.group(2))
        dec = len(mant.split(".")[1]) if "." in mant else 0
        return abs(float(mant) - round(vrai / 10 ** ex, dec)) < 1e-9
    dec = len(s.split(".")[1]) if "." in s else 0
    return abs(float(s) - round(vrai, dec)) < 10 ** (-dec) / 2 + 1e-12


def main() -> int:
    rng = np.random.default_rng(GRAINE)
    R: dict = {"outil": "outils/genome/tome3/juge2-latents/juge2_nuage_rangee.py", "graine": GRAINE}
    mac = macros(DON / "latents-chiffres.tex")
    jn = json.loads((LAT / "nuage-L08-E00-gate.json").read_text(encoding="utf-8"))
    sp = csv_dicts(SPECTRE)
    lam_sp = np.array([float(r["lambda_calib"]) for r in sp])
    ef_sp = np.array([float(r["e_frontiere"]) for r in sp])
    es_sp = np.array([float(r["e_synonyme"]) for r in sp])

    # ---------------------------------------------------------------- la matrice et ses deux bases
    g = LecteurGguf()
    codes, ex = g.expert_mxfp4(TENSEUR, 0)
    W = poids(codes, ex)
    cf, symf = lire_sym(f"{SYM}/frontiere/L08-E00.sym")
    cs, syms = lire_sym(f"{SYM}/synonyme-l1-d1/L08-E00.sym")
    dWf = W - reconstruit(cf, symf, ex)
    dWs = W - reconstruit(cs, syms, ex)
    # témoin du lecteur : l'énergie de l'erreur égale Σ e_k du spectre commité du lot B
    tl = {"frontiere": (float((dWf ** 2).sum()), float(ef_sp.sum())),
          "synonyme": (float((dWs ** 2).sum()), float(es_sp.sum()))}
    ecart_l = max(abs(a / b - 1) for a, b in tl.values())
    c1, sym1 = lire_sym(f"{SYM}/frontiere/L08-E01.sym")
    casse = float(((W - reconstruit(c1, sym1, ex)) ** 2).sum())
    R["temoin_lecteur"] = {"energie_ici_contre_spectre": tl, "ecart_relatif_max": ecart_l,
                           "tient": ecart_l < 1e-9,
                           "cassure_sym_expert1_energie": casse,
                           "cassure_ecart_relatif": abs(casse / tl["frontiere"][1] - 1),
                           "cassure_tombe": abs(casse / tl["frontiere"][1] - 1) > 1e-3}
    del c1, sym1

    # ---------------------------------------------------------------- III-9.1 (d) : la rangée
    jr = json.loads((LAT / "rangee-L08-E00-gate.json").read_text(encoding="utf-8"))
    ligne, (ca, cb) = jr["ligne"], jr["colonnes"]
    blocr = ca // 32
    sb = math.ldexp(1.0, int(ex[ligne, blocr]) - 127)
    rang = []
    for j in range(32):
        col = ca + j
        code = int(codes[ligne, col])
        x = VALEUR_CODE[code]
        f_, s_ = int(symf[ligne, col]), int(syms[ligne, col])
        vf = (-1 if f_ & 4 else 1) * cf[f_ & 3]
        vs = (-1 if s_ & 4 else 1) * cs[s_ & 3]
        rang.append({"j": j, "code": code, "exact": x, "sf": f_, "ss": s_, "vf": vf, "vs": vs, "change": f_ != s_})
    fig = csv_dicts(DON / "latents-rangee.csv")
    ecarts_fig = []
    for r, q in zip(rang, fig):
        nota = lambda s: ("−" if s & 4 else "+") + str(s & 3)
        ok = (int(q["j"]) == r["j"] and q["code"] == f"{r['code']:X}" and q["sf"] == nota(r["sf"])
              and q["ss"] == nota(r["ss"]) and int(q["change"]) == int(r["change"])
              and abs(float(q["exact"]) - r["exact"]) < 1e-6 and abs(float(q["frontiere"]) - r["vf"]) < 1e-6
              and abs(float(q["synonyme"]) - r["vs"]) < 1e-6)
        ecarts_fig.append(ok)
    changes = [r for r in rang if r["change"]]
    eloigne = [{"j": r["j"], "exact": r["exact"], "frontiere": round(r["vf"], 6), "synonyme": round(r["vs"], 6),
                "ecart_frontiere": round(abs(r["vf"] - r["exact"]), 6),
                "ecart_synonyme": round(abs(r["vs"] - r["exact"]), 6),
                "s_eloigne": abs(r["vs"] - r["exact"]) > abs(r["vf"] - r["exact"])} for r in changes]
    jt = int(rng.integers(32))
    R["rangee"] = {
        "s_b": sb, "exposant": int(ex[ligne, blocr]),
        "lignes_du_csv_de_figure_egales_a_la_source": int(sum(ecarts_fig)),
        "symboles_changes": len(changes), "macro_RangChanges": mac["RangChanges"],
        "tete_eloigne_de_l_exact": eloigne,
        "tete_vraie_pour_chacun": all(e["s_eloigne"] for e in eloigne),
        "erreur_bloc_s_b2": {"frontiere": float(sum((r["vf"] - r["exact"]) ** 2 for r in rang)),
                             "synonyme": float(sum((r["vs"] - r["exact"]) ** 2 for r in rang))},
        "centres": {"frontiere": cf.tolist(), "synonyme": cs.tolist()},
        "niveaux_csv_egaux": all(abs(float(q["y"]) - s * cf[int(q["k"])]) < 1e-6
                                 for q, s in zip(csv_dicts(DON / "latents-rangee-niveaux.csv"), [1, -1] * 4)),
        "point_tire_de_la_bande": {"j": jt, "source": {k: (v if not isinstance(v, np.floating) else float(v))
                                                       for k, v in rang[jt].items()},
                                   "csv_figure": fig[jt], "egal": ecarts_fig[jt]},
    }

    # ---------------------------------------------------------------- III-9.7 : les entrées et H
    h, experts, wts = captures(8)
    sel = np.where((experts == 0).any(1))[0]
    gk = np.array([wts[i][list(experts[i]).index(0)] for i in sel], dtype=np.float64)
    X = h[sel].astype(np.float64)
    del h
    w2 = gk ** 2
    H = (X * w2[:, None]).T @ X / w2.sum()
    lam, U = np.linalg.eigh(H)
    lam, U = lam[::-1], U[:, ::-1].copy()
    C = X @ U[:, :3]
    for k in range(3):
        if C[:, k].mean() < 0:
            U[:, k] *= -1
            C[:, k] *= -1
    pts = csv_dicts(LAT / "nuage-L08-E00-gate-points.csv")
    pos_csv = np.array([int(r["position"]) for r in pts])
    Ccsv = np.array([[float(r["c1"]), float(r["c2"]), float(r["c3"])] for r in pts])
    R["entrees"] = {
        "n": int(len(sel)), "json_n": jn["n_entrees"],
        "positions_egales": bool(np.array_equal(pos_csv, sel)),
        "c_ecart_max_au_csv": float(np.abs(C - Ccsv).max()),
        "lambda_1_3": lam[:3].tolist(), "json_lambda_1_3": jn["lambda_1_3"],
        "lambda_ecart_relatif_max": float(np.max(np.abs(lam[:3] / np.array(jn["lambda_1_3"]) - 1))),
        "trace": float(lam.sum()), "json_lambda_somme": jn["lambda_somme"],
        "spectre_100_ecart_relatif_max": float(np.max(np.abs(lam[:100] / lam_sp[:100] - 1))),
        "rang_H": int((lam > lam[0] * 1e-12).sum()),
    }

    # ---------------------------------------------------------------- e_k, M, fonction d'appui
    DUf, DUs = dWf @ U[:, :3], dWs @ U[:, :3]
    ek = {"frontiere": (DUf ** 2).sum(0), "synonyme": (DUs ** 2).sum(0)}
    jE = jn["e_1_3"]
    R["e_k"] = {"frontiere": ek["frontiere"].tolist(), "synonyme": ek["synonyme"].tolist(),
                "ecart_relatif_max_au_json": float(max(np.max(np.abs(ek["frontiere"] / np.array(jE["frontiere"]) - 1)),
                                                       np.max(np.abs(ek["synonyme"] / np.array(jE["synonyme-l1-d1"]) - 1))))}
    Mx = {}
    for nomb, DU in (("frontiere", DUf), ("synonyme", DUs)):
        G = DU.T @ DU
        Mx[(nomb, "12")] = G[np.ix_([0, 1], [0, 1])]
        Mx[(nomb, "13")] = G[np.ix_([0, 2], [0, 2])]
    ell = csv_dicts(LAT / "nuage-L08-E00-gate-ellipses.csv")
    F = jn["facteur_F"]
    appui = {}
    for (nomb, p), M in Mx.items():
        q = np.array([[float(r["x"]), float(r["y"])] for r in ell if r["courbe"] == nomb and r["plan"] == p]) / F
        ferme = bool(np.allclose(q[0], q[-1], atol=1e-6))
        q_ = q[:-1] if ferme else q
        Mmom = 2.0 * (q_.T @ q_) / len(q_)          # moments d'ordre deux, paramètre régulier
        csvp = csv_dicts(DON / f"latents-appui-{nomb}-{p}.csv")
        th = np.radians(np.array([float(r["theta"]) for r in csvp]))
        v = np.stack([np.cos(th), np.sin(th)], 1)
        hh = np.sqrt(np.einsum("ti,ij,tj->t", v, M, v))
        hc = np.array([float(r["h"]) for r in csvp])
        xc = np.array([float(r["x"]) for r in csvp])
        yc = np.array([float(r["y"]) for r in csvp])
        it = int(rng.integers(len(csvp)))
        appui[f"{nomb}-{p}"] = {
            "points_ellipse": len(q), "ellipse_fermee": ferme,
            "M_depuis_dW": M.tolist(), "M_moments_ellipses": Mmom.tolist(),
            "M_ecart_relatif_max": float(np.abs(Mmom - M).max() / np.abs(M).max()),
            "h_ecart_relatif_max_361_angles": float(np.max(np.abs(hc / hh - 1))),
            "xy_ecart_max": float(max(np.abs(xc - hh * v[:, 0]).max(), np.abs(yc - hh * v[:, 1]).max())),
            "angle_tire": {"theta": float(np.degrees(th[it])), "h_csv": float(hc[it]), "h_juge": float(hh[it])},
        }
    R["appui"] = appui

    # ---------------------------------------------------------------- la rose et le cône
    rose = {}
    cone = {}
    for p, (ia, ib) in {"12": (0, 1), "13": (0, 2)}.items():
        ang = np.degrees(np.arctan2(C[:, ib], C[:, ia]))
        tranche = np.floor((ang + 180.0) / 3.0).astype(int)
        compte = np.bincount(tranche, minlength=120)
        csvr = csv_dicts(DON / f"latents-rose-{p}.csv")
        ok = all(compte[int(math.floor((float(r["theta"]) + 180.0) / 3.0))] == int(r["n"]) for r in csvr)
        nonvides = int((compte > 0).sum())
        a = np.sort(np.abs(ang))
        rgx = 0.9 * (len(a) - 1)
        t90 = a[int(rgx)] + (rgx - int(rgx)) * (a[int(rgx) + 1] - a[int(rgx)])
        tt = np.radians(np.linspace(-t90, t90, 20001))
        vv = np.stack([np.cos(tt), np.sin(tt)], 1)
        hs = np.sqrt(np.einsum("ti,ij,tj->t", vv, Mx[("synonyme", p)], vv))
        hf = np.sqrt(np.einsum("ti,ij,tj->t", vv, Mx[("frontiere", p)], vv))
        tout = np.radians(np.linspace(-180, 180, 36001))
        va = np.stack([np.cos(tout), np.sin(tout)], 1)
        ra = (np.sqrt(np.einsum("ti,ij,tj->t", va, Mx[("synonyme", p)], va))
              / np.sqrt(np.einsum("ti,ij,tj->t", va, Mx[("frontiere", p)], va)))
        rose[p] = {"tranches_non_vides": nonvides, "lignes_csv": len(csvr), "comptes_egaux": ok,
                   "entrees_comptees": int(compte.sum())}
        nomp = "Douze" if p == "12" else "Treize"
        cone[p] = {"t90_deg": float(t90), "macro": mac[f"NuageCone{nomp}"],
                   "rapport_max_dans_le_cone": float((hs / hf).max()),
                   "macro_rapport": mac[f"NuageConeRapport{nomp}"],
                   "rapport_min_et_max_sur_tout_le_plan": [float(ra.min()), float(ra.max())],
                   "entrees_a_moins_de_t90": float(np.mean(np.abs(ang) <= t90))}
    R["rose"] = rose
    R["cone"] = cone
    # la rose est-elle bien dans l'anneau ? (sa place radiale : entre la courbe synonyme et la courbe frontière)
    r0, rfin = float(mac["NuageRose"]), float(mac["NuageRoseFin"])
    hs_max = max(math.sqrt(max(np.linalg.eigvalsh(Mx[("synonyme", p)]))) for p in ("12", "13"))
    hf_min = min(math.sqrt(min(np.linalg.eigvalsh(Mx[("frontiere", p)]))) for p in ("12", "13"))
    R["anneau"] = {"r0": r0, "r_fin": rfin, "h_synonyme_max": hs_max, "h_frontiere_min": hf_min,
                   "dans_l_anneau": hs_max < r0 < rfin < hf_min}

    # ---------------------------------------------------------------- (c) les barres
    bar = csv_dicts(DON / "latents-barres.csv")
    rap = np.sqrt(ek["synonyme"] / ek["frontiere"])
    R["barres"] = {"rapport_juge": rap.tolist(), "csv": [float(b["rapport"]) for b in bar],
                   "ecart_max": float(np.max(np.abs(rap - np.array([float(b["rapport"]) for b in bar])))),
                   "lambda_csv_egal": all(abs(float(b["lambda"]) - lam[k]) < 6e-5 for k, b in enumerate(bar)),
                   "err_frontiere": np.sqrt(ek["frontiere"]).tolist(), "err_synonyme": np.sqrt(ek["synonyme"]).tolist()}

    # ---------------------------------------------------------------- l'erreur des entrées réelles
    yf = X @ dWf.T                      # (n, 2 880) : ΔW_f x, entrée par entrée
    ys = X @ dWs.T
    nf, ns = np.linalg.norm(yf, axis=1), np.linalg.norm(ys, axis=1)
    rr = ns / nf
    rms = math.sqrt(float((w2 * ns ** 2).sum() / (w2 * nf ** 2).sum()))
    calf = float((lam_sp * ef_sp).sum())
    cals = float((lam_sp * es_sp).sum())
    P12 = X @ U[:, :2] @ U[:, :2].T
    pf, ps = np.linalg.norm(P12 @ dWf.T, axis=1), np.linalg.norm(P12 @ dWs.T, axis=1)
    rp = ps / pf
    nx2 = (X ** 2).sum(1)
    part12 = (C[:, 0] ** 2 + C[:, 1] ** 2) / nx2
    part3 = (C ** 2).sum(1) / nx2
    angle_plan = np.degrees(np.arccos(np.sqrt(np.clip(part12, 0, 1))))
    angle_u1 = np.degrees(np.arccos(np.clip(C[:, 0] / np.sqrt(nx2), -1, 1)))
    seuil = float(num(mac["NuageConeRapport"]))
    lamef = lam_sp * ef_sp
    lames = lam_sp * es_sp
    R["entrees_reelles"] = {
        "phrase_jugee": "Là où pointent les entrées de l'expert, le synonyme ramène l'erreur de sortie à au plus "
                        f"{mac['NuageConeRapport']} de celle de la frontière",
        "rapport_par_entree_2880_dimensions": {"min": float(rr.min()), "q10": float(np.quantile(rr, 0.1)),
                                               "mediane": float(np.median(rr)), "q90": float(np.quantile(rr, 0.9)),
                                               "max": float(rr.max())},
        "part_des_entrees_sous_le_seuil_de_la_tete": float(np.mean(rr <= seuil)),
        "rapport_quadratique_pondere_g2": rms,
        "meme_rapport_depuis_le_spectre_commite": math.sqrt(cals / calf),
        "erreur_calibration_spectre": {"frontiere": calf, "synonyme": cals},
        "projection_sur_le_plan_u1_u2": {"rapport_mediane": float(np.median(rp)), "rapport_max": float(rp.max()),
                                         "part_sous_le_seuil": float(np.mean(rp <= seuil))},
        "part_de_norme2_dans_le_plan_u1_u2": {"mediane": float(np.median(part12)),
                                              "ponderee_g2": float((w2 * C[:, 0] ** 2 + w2 * C[:, 1] ** 2).sum()
                                                                   / (w2 * nx2).sum())},
        "part_de_norme2_dans_u1_u2_u3_ponderee_g2": float((w2[:, None] * C ** 2).sum() / (w2 * nx2).sum()),
        "angle_entree_plan_u1_u2_deg": {"min": float(angle_plan.min()), "mediane": float(np.median(angle_plan))},
        "angle_entree_u1_deg_mediane": float(np.median(angle_u1)),
        "erreur_ponderee_frontiere": {"u1_a_u3": float(lamef[:3].sum()), "autres": float(lamef[3:].sum())},
        "erreur_ponderee_synonyme": {"u1_a_u3": float(lames[:3].sum()), "autres": float(lames[3:].sum())},
        "energie_non_ponderee": {"frontiere_u1_a_u3": float(ef_sp[:3].sum()), "synonyme_u1_a_u3": float(es_sp[:3].sum()),
                                 "frontiere_totale": float(ef_sp.sum()), "synonyme_totale": float(es_sp.sum())},
    }

    # ---------------------------------------------------------------- les nombres écrits (nouveaux ou déplacés)
    v = {
        "NuageConeDouze": cone["12"]["t90_deg"], "NuageConeTreize": cone["13"]["t90_deg"],
        "NuageConeRapportDouze": cone["12"]["rapport_max_dans_le_cone"],
        "NuageConeRapportTreize": cone["13"]["rapport_max_dans_le_cone"],
        "NuageConeRapport": max(cone["12"]["rapport_max_dans_le_cone"], cone["13"]["rapport_max_dans_le_cone"]),
        "NuageRapportUn": rap[0], "NuageRapportDeux": rap[1], "NuageRapportTrois": rap[2],
        "NuageErrFUn": math.sqrt(ek["frontiere"][0]), "NuageErrFDeux": math.sqrt(ek["frontiere"][1]),
        "NuageErrFTrois": math.sqrt(ek["frontiere"][2]),
        "NuageErrSUn": math.sqrt(ek["synonyme"][0]), "NuageErrSDeux": math.sqrt(ek["synonyme"][1]),
        "NuageErrSTrois": math.sqrt(ek["synonyme"][2]),
        "NuageLambdaUn": lam[0], "NuageLambdaDeux": lam[1], "NuageLambdaTrois": lam[2],
        "NuageMoyUn": C[:, 0].mean(), "NuageEcartUn": C[:, 0].std(), "NuageEcartDeux": C[:, 1].std(),
        "NuageMoyCarre": C[:, 0].mean() ** 2, "NuageN": len(sel), "NuagePartTrace": 100 * lam[:3].sum() / lam.sum(),
        "NuageAutresDirections": 2880 - 3, "NuageEllipsePoints": len(q),
        "NuageRosePas": 3, "NuageConeQuantile": 90, "NuageCasseF": 1,
        "SpecCalibRapport": calf / cals,
    }
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
