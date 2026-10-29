"""P3, routeur biaisé en ligne, SECOND TIRAGE : analyse et verdict aux seuils de 07-second-tirage-declare.md.

Deux temps (jamais pendant une passe du moteur : lecture de plusieurs Go de .kld) :
    python -X utf8 p3_second_tirage_analyse.py ab      # chemins A (`juge kl`) et B (lecteur de l'étage B), défauts par trois chemins,
                                                       # cellules changées, T0 ; reprend p3_routeur_ligne_analyse.py (premier tirage)
    python -X utf8 p3_second_tirage_analyse.py juge    # chemin C (lecteur du juge), intervalles par fenêtres et par blocs de 51,
                                                       # robustesse des défauts, cellules par couche, verdict
Sortie : mesures/mimetisme/P3/second-tirage/{analyse.json, analyse-juge.json, verdict.json, juge-kl-*.{json,csv}}.
Rien n'est ajusté après lecture : seuils = ceux de 07-second-tirage-declare.md § 4 et § 5.
"""
import json
import pathlib
import sys

ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
DEPOT = ICI.parents[2]
SORTIE = DEPOT / "mesures/mimetisme/P3/second-tirage"
LOURDS = pathlib.Path("~/dev/essais/troncons/mimetisme/P3/second-tirage")
REF_F64 = pathlib.Path("~/dev/essais/troncons/genome/juge/ref-juge-20b.kld")
S_DEF, S_KL, S_KL_MORT, S_PC, S_MARGE = 0.10, 0.038, 0.07, 0.95, 0.3


def ab():
    import p3_routeur_ligne_analyse as A
    A.SORTIE, A.LOURDS, A.BASE_F64 = SORTIE, LOURDS, REF_F64
    A.main(avec_ref=True)


def juge():
    sys.path.insert(0, str(ICI / "juge" / "routeur-ligne"))
    import juge_routeur_ligne as JJ            # pose deux fils avant numpy
    import numpy as np

    JJ.MES, JJ.KLD = SORTIE, LOURDS
    out_dir = SORTIE
    P0 = JJ.Kld(LOURDS / "P0.kld")
    tests = {"B0.041": JJ.Kld(LOURDS / "B0.041.kld")}
    if (LOURDS / "B0.3.kld").exists():
        tests["B0.3"] = JJ.Kld(LOURDS / "B0.3.kld")
    tests["ref"] = JJ.Kld(REF_F64)
    for nom, x in tests.items():
        assert (x.n_ctx, x.n_vocab, x.n_fen) == (P0.n_ctx, P0.n_vocab, P0.n_fen), nom
        assert (x.jetons == P0.jetons).all(), nom
    n = P0.n
    R = {"i1": np.zeros(n, np.int64), "marge": np.zeros(n), "somme": np.zeros(n)}
    S = {nom: {"kl16": np.zeros(n), "i1": np.zeros(n, np.int64)} for nom in tests}
    S["ref"]["kl_ref_P0"] = np.zeros(n)
    i = 0
    while i < n:
        k = min(JJ.PAQUET, n - i)
        lp = P0.lire(k)
        p = np.exp(lp)
        i1, mg = JJ.deux(lp)
        sl = slice(i, i + k)
        R["i1"][sl], R["marge"][sl], R["somme"][sl] = i1, mg, p.sum(1)
        for nom, x in tests.items():
            lq = x.lire(k)
            S[nom]["kl16"][sl] = np.where(lp > -16.0, p * (lp - lq), 0.0).sum(1)
            S[nom]["i1"][sl] = lq.argmax(1)
            if nom == "ref":
                q = np.exp(lq)
                S[nom]["kl_ref_P0"][sl] = np.where(lq > -16.0, q * (lq - lp), 0.0).sum(1)
        i += k
        if i % 400 == 0:
            print("positions", i, flush=True)
    pf = P0.par_fen
    fen = np.arange(n) // pf
    blocs = np.arange(n) // 51
    nb = n // 51
    msk = R["marge"] >= S_MARGE
    res = {"n": n, "par_fenetre": pf, "positions_marge>=0.3": int(msk.sum()), "somme_p_P0_min_max": [float(R["somme"].min()), float(R["somme"].max())],
           "passes": {}}
    for nom in tests:
        acc = R["i1"] == S[nom]["i1"]
        k16 = S[nom]["kl16"]
        d = {"kl": float(k16.mean()), "litteral": float(acc.mean()), "desaccords": int((~acc).sum()),
             "pondere": float(acc[msk].mean()), "desaccords_ponderes": int((~acc & msk).sum()),
             "kl_mediane": float(np.median(k16)), "kl_p99": float(np.quantile(k16, 0.99))}
        d["kl_ic_fenetres"], vk = JJ.boot(k16, np.ones(n), fen)
        d["pondere_ic_fenetres"], vp = JJ.boot((acc & msk).astype(float), msk.astype(float), fen)
        d["litteral_ic_fenetres"], _ = JJ.boot(acc.astype(float), np.ones(n), fen)
        d["kl_ic_blocs51"], vkb = JJ.boot(k16, np.ones(n), blocs, nfen=nb)
        d["pondere_ic_blocs51"], vpb = JJ.boot((acc & msk).astype(float), msk.astype(float), blocs, nfen=nb)
        d["litteral_ic_blocs51"], _ = JJ.boot(acc.astype(float), np.ones(n), blocs, nfen=nb)
        d["part_tirages_fenetres_kl>0.038"] = float((vk > S_KL).mean())
        d["part_tirages_fenetres_pondere<0.95"] = float((vp < S_PC).mean())
        d["part_tirages_blocs51_kl>0.038"] = float((vkb > S_KL).mean())
        d["part_tirages_blocs51_pondere<0.95"] = float((vpb < S_PC).mean())
        hi = [JJ.boot(k16, np.ones(n), fen, graine=g)[0][1] for g in range(1, 21)]
        lo = [JJ.boot((acc & msk).astype(float), msk.astype(float), fen, graine=g)[0][0] for g in range(1, 21)]
        hib = [JJ.boot(k16, np.ones(n), blocs, nfen=nb, graine=g)[0][1] for g in range(1, 21)]
        lob = [JJ.boot((acc & msk).astype(float), msk.astype(float), blocs, nfen=nb, graine=g)[0][0] for g in range(1, 21)]
        d["graines_fenetres"] = {"kl_borne_haute_min_max": [min(hi), max(hi)], "graines_kl_au_dessus_0.038": int(sum(x > S_KL for x in hi)),
                                 "pondere_borne_basse_min_max": [min(lo), max(lo)], "graines_pondere_sous_95": int(sum(x < S_PC for x in lo))}
        d["graines_blocs51"] = {"kl_borne_haute_min_max": [min(hib), max(hib)], "graines_kl_au_dessus_0.038": int(sum(x > S_KL for x in hib)),
                                "pondere_borne_basse_min_max": [min(lob), max(lob)], "graines_pondere_sous_95": int(sum(x < S_PC for x in lob))}
        d["kl_par_fenetre"] = [float(k16[fen == w].mean()) for w in range(P0.n_fen)]
        d["pondere_par_fenetre"] = [float(acc[(fen == w) & msk].mean()) if (msk & (fen == w)).any() else None for w in range(P0.n_fen)]
        if nom == "ref":
            d["kl_ref_vers_P0"] = float(S["ref"]["kl_ref_P0"].mean())
        res["passes"][nom] = d
        print(nom, {k: v for k, v in d.items() if not isinstance(v, (list, dict))}, flush=True)
    b = tests.get("B0.041")
    z = np.array(S["B0.041"]["i1"])
    res["cassure_decalage_1_pondere"] = float((R["i1"][1:] == z[:-1])[msk[1:]].mean())
    res["sensibilite_marge"] = {}
    for s in (0.1, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5):
        m_ = R["marge"] >= s
        res["sensibilite_marge"][str(s)] = {nom: float((R["i1"] == S[nom]["i1"])[m_].mean()) for nom in tests if nom != "ref"} | {"n": int(m_.sum())}
    # --- défauts : mon LRU (judge), conventions compatibles, puis informatif
    tr = {nom: JJ.trace(nom) for nom in ("P0", "B0.041") + (("B0.3",) if "B0.3" in tests else ())}
    D = {}
    d0, d1 = JJ.lru(tr["P0"])[0], JJ.lru(tr["B0.041"])[0]
    D["service/vide"] = {"P0": d0, "B0.041": d1, "variation": d1 / d0 - 1, "marge": 0.9 * d0 - d1}
    print("defauts service", D["service/vide"], flush=True)
    for ordre, init, reinit in [("inverse", "vide", False), ("indice", "vide", False), ("hasard", "vide", False), ("service", "chaud", False),
                                ("service", "premiers", False), ("service", "vide", True)]:
        for gr in (range(5) if ordre == "hasard" else (0,)):
            cle = f"{ordre}/{init}" + ("/reinit-fenetre" if reinit else "") + (f"/graine{gr}" if ordre == "hasard" else "")
            p0 = JJ.lru(tr["P0"], ordre=ordre, init=init, reinit_fenetre=reinit, graine=gr)[0]
            b1 = JJ.lru(tr["B0.041"], ordre=ordre, init=init, reinit_fenetre=reinit, graine=gr)[0]
            D[cle] = {"P0": p0, "B0.041": b1, "variation": b1 / p0 - 1, "marge": 0.9 * p0 - b1, "compatible_protocole": not reinit}
            print(cle, D[cle], flush=True)
    D["service/vide"]["compatible_protocole"] = True
    res["defauts_conventions"] = D
    res["defauts_budgets_voisins_info"] = {str(m): {"P0": JJ.lru(tr["P0"], m)[0], "B0.041": JJ.lru(tr["B0.041"], m)[0]} for m in (230, 234, 242, 246)}
    for v in res["defauts_budgets_voisins_info"].values():
        v["variation"] = v["B0.041"] / v["P0"] - 1
    rng = np.random.default_rng(31)
    tp = tr["P0"].copy()
    for c in rng.choice(tp.shape[0] * JJ.L, 1000, replace=False):
        t, l = divmod(int(c), JJ.L)
        tp[t, l] = rng.choice(JJ.E, JJ.K, replace=False)
    res["cassures_lru"] = {"1000_cellules_au_hasard_P0": JJ.lru(tp)[0], "budget_237_P0": JJ.lru(tr["P0"], 237)[0], "P0_budget_238": d0}
    if "B0.3" in tr:
        res["defauts_B0.3"] = {"moi": JJ.lru(tr["B0.3"])[0]}
    # --- défauts par fenêtre de 512 pas (LRU service/vide, le cache traverse les fenêtres) : bootstrap par fenêtres
    def par_pas(trace):
        T = trace.shape[0]
        g = trace.astype(np.int64) + (np.arange(JJ.L, dtype=np.int64) * JJ.E)[None, :, None]
        stamp = np.full(JJ.L * JJ.E, -1, np.int64)
        resid = np.zeros(JJ.L * JJ.E, bool)
        occ, h, grand = 0, 0, np.iinfo(np.int64).max
        out = np.zeros(T, np.int64)
        for t in range(T):
            for l in range(JJ.L):
                grp = g[t, l]
                for x in grp:
                    if not resid[x]:
                        out[t] += 1
                        if occ >= JJ.N:
                            s = np.where(resid, stamp, grand)
                            s[grp] = grand
                            v = int(s.argmin())
                            resid[v] = False
                            occ -= 1
                        resid[x] = True
                        occ += 1
                    stamp[x] = h
                    h += 1
        return out
    pp0, pp1 = par_pas(tr["P0"]), par_pas(tr["B0.041"])
    assert int(pp0.sum()) == d0 and int(pp1.sum()) == d1, (pp0.sum(), d0, pp1.sum(), d1)
    f0 = np.bincount(np.arange(len(pp0)) // 512, weights=pp0)
    f1 = np.bincount(np.arange(len(pp1)) // 512, weights=pp1)
    rg = np.random.default_rng(1)
    idx = rg.integers(0, len(f0), size=(20000, len(f0)))
    var = f1[idx].sum(1) / f0[idx].sum(1) - 1
    res["defauts_par_fenetre"] = {"P0": f0.tolist(), "B0.041": f1.tolist(), "variation_par_fenetre": (f1 / f0 - 1).tolist(),
                                  "ic95_bootstrap_fenetres": [float(np.percentile(var, 2.5)), float(np.percentile(var, 97.5))],
                                  "part_tirages_au_dessus_de_-10pct": float((var > -S_DEF).mean())}
    # --- cellules changées par couche (ensembles) et rapport KL / part changée
    cell = {}
    for nom in tr:
        if nom == "P0":
            continue
        chg = JJ.ensembles_differents(tr[nom], tr["P0"])
        cell[nom] = {"part": float(chg.mean()), "n": int(chg.sum()), "par_couche": chg.mean(0).tolist(),
                     "meme_ensemble_autre_ordre": float(((tr[nom] != tr["P0"]).any(-1) & ~chg).mean())}
        cell[nom]["kl_sur_part"] = res["passes"][nom]["kl"] / cell[nom]["part"]
    res["cellules"] = cell
    (out_dir / "analyse-juge.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    verdict(res)


def verdict(res):
    b = res["passes"]["B0.041"]
    D = res["defauts_conventions"]
    compat = {k: v for k, v in D.items() if v.get("compatible_protocole")}
    t1_est = D["service/vide"]["variation"] <= -S_DEF
    t1_borne = all(v["marge"] >= 0 for v in compat.values())
    t2_est = b["kl"] <= S_KL
    t2_borne = b["kl_ic_blocs51"][1] <= S_KL
    t3_est = b["pondere"] >= S_PC
    t3_borne = b["pondere_ic_blocs51"][0] >= S_PC
    est = t1_est and t2_est and t3_est
    borne = t1_borne and t2_borne and t3_borne
    if b["kl"] > S_KL_MORT:
        v = "TOMBE"
    elif est and borne:
        v = "TIENT (robuste)"
    elif est:
        v = "TIENT à l'estimation seulement"
    else:
        v = "NON CONCLUANT"
    out = {"B0.041": {"T1_defauts": {"variation": D["service/vide"]["variation"], "estimation": t1_est, "borne_decisive": t1_borne,
                                     "marge_min_conventions_compatibles": min(x["marge"] for x in compat.values())},
                      "T2_kl": {"valeur": b["kl"], "estimation": t2_est, "borne_haute_blocs51": b["kl_ic_blocs51"][1], "borne_decisive": t2_borne,
                                "borne_haute_fenetres_info": b["kl_ic_fenetres"][1]},
                      "T3_pondere": {"valeur": b["pondere"], "estimation": t3_est, "borne_basse_blocs51": b["pondere_ic_blocs51"][0], "borne_decisive": t3_borne,
                                     "borne_basse_fenetres_info": b["pondere_ic_fenetres"][0]},
                      "litteral_info": b["litteral"], "verdict": v}}
    if "B0.3" in res["passes"]:
        c = res["passes"]["B0.3"]
        dv = res.get("defauts_B0.3", {}).get("moi")
        out["cassure_B0.3"] = {"kl": c["kl"], "pondere": c["pondere"], "litteral": c["litteral"],
                               "defauts": dv, "variation_defauts": (dv / D["service/vide"]["P0"] - 1) if dv else None,
                               "la_porte_tombe": bool(c["kl"] > S_KL or c["pondere"] < S_PC)}
    (SORTIE / "verdict.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    print(json.dumps(out, indent=1, ensure_ascii=False, default=float))


if __name__ == "__main__":
    {"ab": ab, "juge": juge}[sys.argv[1]]()
