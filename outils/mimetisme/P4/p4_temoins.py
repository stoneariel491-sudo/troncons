"""P4 : témoins du simulateur et de la calibration (déclarés dans mesures/mimetisme/P4/00-seuils-declares.md § 3).

Étapes :
  T0  LRU global (OrderedDict) contre la liste simple, 2 000 accès
  T1  base : défauts simulés au budget 7 % du 120b, surcoût o ajusté pour 460 ms par jeton
  T2  prédicteur parfait (d = 1, priorité) : attendu x1,21 à 2 % ; fenêtre ajustée UNE fois si besoin (étalonnage)
  T3  prédicteur synthétique p = 0,692, couverture 0,76 (octets +34 %), FIFO, d = 1 : attendu -11 % +/- 4 points
Usage : python -I -X utf8 p4_temoins.py <dossier_traces_120b> <sortie.json>
"""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p4  # noqa: E402

LECTURE = ["code.lecture", "dialogue.lecture", "prose-en.lecture", "prose-fr.lecture"]
BUDGET = 0.07
T_BASE_MS = 460.0


def parametres(w_total, o_layer=0.0):
    return {"w_total": w_total, "tail": 1.85, "tr": 4.1, "o": o_layer}


def cadre(L, w_total, o_layer):
    par = parametres(w_total, o_layer)
    par["w_layer"] = w_total / L
    return par


def calibrer_o(data, N, w_total, L):
    """o_layer tel que la moyenne des temps de jeton de base (sur les genres de lecture, pondérée par les jetons) = 460 ms."""
    tot, nt = 0.0, 0
    for nom in LECTURE:
        J, E = data[nom]
        faults, _ = p4.passe_cache(J, E, N, 1)
        r = p4.des(J, E, 1, faults, [[] for _ in range(J.shape[0] * L)], cadre(L, w_total, 0.0))
        tot += r["tok"].sum()
        nt += J.shape[0]
    tm0 = tot / nt
    return (T_BASE_MS - tm0) / L, tm0


def gain_pool(data, N, par, L, charges_fn, mode, d):
    """x = temps de base / temps du bras, groupé sur les genres de lecture ; octets relatifs."""
    tb = ta = 0.0
    dem_b = dem_a = bg_a = 0
    for nom in LECTURE:
        J, E = data[nom]
        T = J.shape[0]
        faults, _ = p4.passe_cache(J, E, N, d)
        vide = [[] for _ in range(T * L)]
        rb = p4.des(J, E, d, faults, vide, par, "prio")
        ch = charges_fn(J, E, faults, d)
        ra = p4.des(J, E, d, faults, ch, par, mode)
        tb += rb["tok"].sum()
        ta += ra["tok"].sum()
        dem_b += rb["dem"].sum()
        dem_a += ra["dem"].sum()
        bg_a += ra["bg"].sum()
    return tb / ta, (dem_a + bg_a) / dem_b - 1.0, dem_b / sum(data[n][0].shape[0] for n in LECTURE)


def main():
    dossier, sortie = sys.argv[1], sys.argv[2]
    t0 = time.time()
    data = p4.charger(dossier)
    J0, E0 = data["code.lecture"]
    T, L, k = J0.shape
    N = 326  # 7 % du 120b tel que le moteur le règle (326 emplacements) ; 0,07 x 4 608 = 322,6
    res = {"N": N, "L": L, "E": E0}
    print("N =", N, "L =", L, flush=True)

    # T0 : LRU global contre liste simple
    acc = [[l * E0 + int(e) for e in J0[t, l]] for t in range(60) for l in range(L)][:2000 // k]
    faults, _ = p4.passe_cache(J0[:60], E0, N, 1)
    d_dict = sum(len(f) for f in faults[:len(acc)])
    d_list = p4.lru_liste(acc, N)
    res["T0_lru_dict"], res["T0_lru_liste"] = d_dict, d_list
    print("T0 défauts dict / liste :", d_dict, d_list, "->", "égal" if d_dict == d_list else "DIFFERENT", flush=True)
    # même test avec un budget étroit pour que l'éviction travaille (N = 60)
    faults, _ = p4.passe_cache(J0[:60], E0, 60, 1)
    d_dict2 = sum(len(f) for f in faults[:len(acc)])
    d_list2 = p4.lru_liste(acc, 60)
    res["T0b_lru_dict"], res["T0b_lru_liste"] = d_dict2, d_list2
    print("T0b N=60 défauts dict / liste :", d_dict2, d_list2, flush=True)

    # T1 : base
    w0 = 80.0
    o, tm0 = calibrer_o(data, N, w0, L)
    res["T1_w0"], res["T1_tm0_sans_o"], res["T1_o_layer"] = w0, tm0, o
    print(f"T1 w={w0} ms/jeton : jeton de base sans o = {tm0:.1f} ms ; o par couche = {o:.3f} ms", flush=True)
    if o < 0:
        print("NOTE o < 0 : la base simulée dépasse 460 ms ; o négatif gardé comme décalage d'étalonnage (dit)", flush=True)

    def parfait(J, E, faults, d):
        T_ = J.shape[0]
        return [list(f) for f in faults]

    def essai_parfait(w):
        o_, _ = calibrer_o(data, N, w, L)
        par = cadre(L, w, o_)
        return gain_pool(data, N, par, L, parfait, "prio", 1), par

    (x, octets, fpt), par = essai_parfait(w0)
    res["T2_x_w0"] = x
    print(f"T2 parfait d=1 priorité, w={w0}: x{x:.4f} (octets {octets:+.3f}, défauts/jeton de base {fpt:.1f})", flush=True)
    w = w0
    # Pas d'étalonnage de la fenêtre : à base figée à 460 ms, agrandir la fenêtre rend le surcoût o négatif (la
    # bissection de la première passe v2 l'a montré : w -> 400 ms, o = -9 ms par couche, x inchangé). L'écart est dit.
    res["T2_etalonnage"] = False
    res["T2_dans_la_tolerance"] = bool(abs(x - 1.21) / 1.21 <= 0.02)
    res["T2_w_final"], res["T2_x_final"], res["T2_o_final"] = w, x, par["o"]
    print(f"T2 fenêtre retenue w = {w:.2f} ms/jeton ; x{x:.4f} ; o = {par['o']:.3f} ms/couche (étalonnage : {res['T2_etalonnage']})", flush=True)

    # T3 : synthétique p = 0,692, couverture 0,76, FIFO, d = 1 (HORS ÉCHANTILLON)
    rng = np.random.default_rng(20261027)

    def synth(J, E, faults, d):
        T_, L_, k_ = J.shape
        nf = np.mean([len(f) for f in faults])
        lam = 0.338 * nf
        ch = [[] for _ in range(T_ * L_)]
        for g in range(T_ * L_):
            t_, l_ = divmod(g, L_)
            s = [e for e in faults[g] if rng.random() < 0.76]
            vrais = set(int(e) for e in J[t_, l_])
            for _ in range(rng.poisson(lam)):
                e = int(rng.integers(E))
                while e in vrais or e in s:
                    e = int(rng.integers(E))
                s.append(e)
            ch[g] = s
        return ch

    xs = []
    for rep in range(2):
        (x3, oct3, _), _ = (gain_pool(data, N, par, L, synth, "fifo", 1), par)
        xs.append((x3, oct3))
    x3 = float(np.mean([a for a, _ in xs]))
    oct3 = float(np.mean([b for _, b in xs]))
    res["T3_x"], res["T3_octets"], res["T3_gain"] = x3, oct3, x3 - 1.0
    res["T3_repetitions"] = xs
    ok3 = abs((x3 - 1.0) - (-0.11)) <= 0.04
    res["T3_dans_la_tolerance"] = bool(ok3)
    print(f"T3 FIFO synthétique : x{x3:.4f} (gain {100*(x3-1):+.1f} %, attendu -11 +/- 4) ; octets {oct3:+.3f} (attendu +0,34) ; "
          f"{'TIENT' if ok3 else 'MANQUE'} ; répétitions {xs}", flush=True)

    # T3b : mêmes chargements synthétiques mais priorité (sensibilité)
    rng = np.random.default_rng(20261027)
    (x3b, oct3b, _) = gain_pool(data, N, par, L, synth, "prio", 1)
    res["T3b_prio_x"], res["T3b_prio_octets"] = x3b, oct3b
    print(f"T3b mêmes chargements en priorité : x{x3b:.4f} ; octets {oct3b:+.3f}", flush=True)

    res["duree_s"] = time.time() - t0
    json.dump(res, open(sortie, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("écrit", sortie, f"({res['duree_s']:.0f} s)")


if __name__ == "__main__":
    main()
