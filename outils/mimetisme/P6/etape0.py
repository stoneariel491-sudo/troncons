"""P6 étape 0 : la mesure, après les témoins. Seuils : mesures/mimetisme/P6/00-seuils-declares.md.
Usage : python -I -X utf8 etape0.py <t120> <t20> <cache_dir> <sortie>
Écrit <sortie>/etape0.json (tous les chiffres) et <sortie>/etape0.log."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import tiers

d120, d20, cdir, sortie = sys.argv[1:5]
os.makedirs(cdir, exist_ok=True)
os.makedirs(sortie, exist_ok=True)
RHO = 0.718
THETAS = [0.10, 0.15, 0.20, 0.25, 0.30]
REGLES = [("accepter", None), ("remonter", 0.30), ("remonter", 0.40), ("remonter", 0.50)]
G120 = {"gen-prose-en": "t120b.prose-en.generation", "gen-wiki": "w120b.wiki.generation"}
L120 = {"code": "t120b.code.lecture", "dialogue": "t120b.dialogue.lecture", "prose-en": "t120b.prose-en.lecture",
        "prose-fr": "t120b.prose-fr.lecture", "wiki-lecture": "w120b.wiki.lecture"}
G20 = {f"20b-gen-{k}": f"{p}20b.{k}.generation" for k, p in
       [("code", "t"), ("dialogue", "t"), ("prose-en", "t"), ("prose-fr", "t"), ("wiki", "w")]}
L20 = {f"20b-lec-{k}": f"{p}20b.{k}.lecture" for k, p in
       [("code", "t"), ("dialogue", "t"), ("prose-en", "t"), ("prose-fr", "t"), ("wiki", "w")]}
journal = open(os.path.join(sortie, "etape0.log"), "w", encoding="utf-8")


def dire(*a):
    m = " ".join(str(x) for x in a)
    print(m, flush=True)
    journal.write(m + "\n")
    journal.flush()


def charger(d, base):
    return tiers.charger(os.path.join(d, base + ".trace"), os.path.join(d, base + ".poids"))


def cache_memo(cle, ex, E, N, pol="lfu", h=8.0):
    f = os.path.join(cdir, f"{cle}-N{N}-{pol}{h:g}.npz")
    if os.path.exists(f):
        z = np.load(f)
        return z["defaut"], z["sejour"]
    t0 = time.time()
    df, sj = tiers.cache(ex, E, N, pol, h)
    np.savez_compressed(f, defaut=df, sejour=sj)
    dire(f"  cache {cle} N={N} {pol}{h:g} : {time.time() - t0:.1f} s, taux de succès {1 - df.mean():.4f}")
    return df, sj


def evalue(cle, w, df, sj, rho=RHO, thetas=THETAS, regles=REGLES, tirages=2000):
    """Rend {theta: {regle: bilan}} et la liste des blocs pour le cumul."""
    sortie_ = {}
    blocs = {}
    for th in thetas:
        for nom, tp in regles:
            if nom == "remonter" and tp <= th:
                continue
            e, b, ts = tiers.regle(df, sj, w, th, nom, rho, tp)
            nm = nom if tp is None else f"{nom}{tp:.2f}"
            blocs[(th, nm)] = tiers.blocs_trace(e, b, ts, w, df)
            sortie_.setdefault(f"{th:.2f}", {})[nm] = tiers.bilan_blocs([blocs[(th, nm)]], rho, tirages)
    return sortie_, blocs


def oracle(w, df, sj, thetas=THETAS, rho=RHO):
    m = tiers.max_par_sejour(df, sj, w)
    out, bl = {}, {}
    for th in thetas:
        F = m < th
        F[0] = False
        e, b, ts = tiers.regle_etiquette(df, sj, w, F, rho)
        bl[th] = tiers.blocs_trace(e, b, ts, w, df)
        out[f"{th:.2f}"] = tiers.bilan_blocs([bl[th]], rho, 500)
    return out, bl


def hasard(w, df, sj, theta, rho=RHO, tirages=50, graine=7):
    """T3 : même nombre de séjours F que le portillon à theta, tirés sans regarder w ; règle 'accepter'."""
    rng = np.random.default_rng(graine)
    w_s, d_s, t_s, debut = tiers._prelude(df, sj, w)
    nF = int((w_s[debut][d_s] < theta).sum())
    n = int(sj.max())
    res = []
    for _ in range(tirages):
        F = np.zeros(n + 1, dtype=bool)
        F[1 + rng.choice(n, size=nF, replace=False)] = True
        e, b, ts = tiers.regle_etiquette(df, sj, w, F, rho)
        res.append(tiers.blocs_trace(e, b, ts, w, df))
    return res


def melange_par_couche(w, graine):
    """T2 : permute les vecteurs de poids (les K poids d'un (t, l)) entre les jetons d'une même couche."""
    rng = np.random.default_rng(graine)
    w2 = w.copy()
    for l in range(w.shape[1]):
        w2[:, l, :] = w[rng.permutation(w.shape[0]), l, :]
    return w2


R = {"rho": RHO, "thetas": THETAS}
t_debut = time.time()

# ---------------------------------------------------------------- 120b
donnees = {}
for cle, base in {**G120, **L120}.items():
    donnees[cle] = charger(d120, base)
    dire("chargé", cle, donnees[cle][0].shape)
caches = {}
for cle in donnees:
    ex, w, E = donnees[cle]
    caches[cle] = cache_memo("120-" + cle, ex, E, 323)

R["120b"] = {}
pool_blocs = {}
for cle in G120:
    ex, w, E = donnees[cle]
    df, sj = caches[cle]
    ev, bl = evalue(cle, w, df, sj)
    orc, orc_bl = oracle(w, df, sj)
    R["120b"][cle] = {"portillon": ev, "oracle": orc, "defauts": int(df.sum()), "acces": int(df.size),
                      "taux_succes": float(1 - df.mean())}
    for k, v in bl.items():
        pool_blocs.setdefault(k, []).append(v)
    for k, v in orc_bl.items():
        pool_blocs.setdefault(("oracle", k), []).append(v)
    dire(cle, "theta 0.20:", {k: (round(v["S"], 4), round(v["E_rel"], 4), round(v["r"], 3))
                              for k, v in ev["0.20"].items()},
         "oracle", {k: (round(v["S"], 4), round(v["r"], 3)) for k, v in orc.items() if k == "0.20"})

# cumul des deux générations (verdict)
R["120b"]["cumul_generation"] = {"portillon": {}, "oracle": {}}
for k, lst in pool_blocs.items():
    if k[0] == "oracle":
        R["120b"]["cumul_generation"]["oracle"][f"{k[1]:.2f}"] = tiers.bilan_blocs(lst, RHO, 2000)
    else:
        th, nm = k
        R["120b"]["cumul_generation"]["portillon"].setdefault(f"{th:.2f}", {})[nm] = tiers.bilan_blocs(lst, RHO, 2000)
dire("cumul génération theta 0.20", {k: (round(v["S"], 4), round(v["r"], 3), round(v["sigma_r"] or 0, 3))
                                      for k, v in R["120b"]["cumul_generation"]["portillon"]["0.20"].items()})

# lectures, jeton par jeton (secondaire)
R["120b"]["lecture_par_jeton"] = {}
pool_lec = {}
for cle in L120:
    ex, w, E = donnees[cle]
    df, sj = caches[cle]
    ev, bl = evalue(cle, w, df, sj, thetas=[0.20, 0.25], tirages=500)
    R["120b"]["lecture_par_jeton"][cle] = ev
    for k, v in bl.items():
        pool_lec.setdefault(k, []).append(v)
R["120b"]["lecture_par_jeton"]["cumul"] = {}
for (th, nm), lst in pool_lec.items():
    R["120b"]["lecture_par_jeton"]["cumul"].setdefault(f"{th:.2f}", {})[nm] = tiers.bilan_blocs(lst, RHO, 1000)
dire("lecture cumul theta 0.20", {k: (round(v["S"], 4), round(v["r"], 3))
                                  for k, v in R["120b"]["lecture_par_jeton"]["cumul"]["0.20"].items()})

# ---------------------------------------------------------------- témoins T0, T2, T3
t = {}
for cle in G120:
    ex, w, E = donnees[cle]
    df, sj = caches[cle]
    e, b, ts = tiers.regle(df, sj, w, 0.0, "accepter", RHO)
    b0 = tiers.bilan_blocs([tiers.blocs_trace(e, b, ts, w, df)], RHO, 10)
    e, b, ts = tiers.regle(df, sj, w, 1.0001, "accepter", RHO)
    b1 = tiers.bilan_blocs([tiers.blocs_trace(e, b, ts, w, df)], RHO, 10)
    t.setdefault("T0", {})[cle] = {"theta0_E": b0["E_rel"], "theta0_S": b0["S"], "theta1_E_moins_1": b1["E_rel"] - 1,
                                   "theta1_S_moins_(1-rho)": b1["S"] - (1 - RHO), "theta1_r_moins_1": b1["r"] - 1}
t["T0_tient"] = bool(all(v["theta0_E"] == 0 and v["theta0_S"] == 0 and abs(v["theta1_E_moins_1"]) < 1e-12
                         and abs(v["theta1_S_moins_(1-rho)"]) < 1e-12 and abs(v["theta1_r_moins_1"]) < 1e-9
                         for v in t["T0"].values()))
dire("T0 tient:", t["T0_tient"])

# T2 : mélange, T3 : hasard, sur le cumul des 7 traces du 120b, 'accepter', theta 0.20 et 0.25
cum_vrai, cum_mel, cum_hasard = {}, {}, {}
r0 = {}
for th in (0.20, 0.25):
    vrai, mel, has = [], [], []
    e_marg_num = e_marg_den = n_sous = n_tot = 0.0
    sp_vrai = [0, 0.0, 0.0]
    sp_mel = [0, 0.0, 0.0]
    for cle in donnees:
        ex, w, E = donnees[cle]
        df, sj = caches[cle]
        e, b, ts = tiers.regle(df, sj, w, th, "accepter", RHO)
        vrai.append(tiers.blocs_trace(e, b, ts, w, df))
        wm = melange_par_couche(w, 20261027)
        e, b, ts = tiers.regle(df, sj, wm, th, "accepter", RHO)
        mel.append(tiers.blocs_trace(e, b, ts, wm, df))
        has.append(hasard(w, df, sj, th))
        e_marg_num += float((w[w < th] ** 2).sum())
        e_marg_den += float((w ** 2).sum())
        n_sous += float((w < th).sum())
        n_tot += w.size
        for lst, ww in ((sp_vrai, w), (sp_mel, wm)):
            sp = tiers.sans_portage(df, ww, th)
            lst[0] += sp["defauts"]
            lst[1] += sp["defauts_sous"]
            lst[2] += sp["g2_defauts_sous"]
    # sans portage : r = (E_sans_portage / E_tout) / (part des défauts sous theta) ; ici octets proportionnels
    g2t = e_marg_den
    r_sp_vrai = (sp_vrai[2] / g2t) / (sp_vrai[1] / sp_vrai[0])
    r_sp_mel = (sp_mel[2] / g2t) / (sp_mel[1] / sp_mel[0])
    r0[f"{th:.2f}"] = (e_marg_num / e_marg_den) / (n_sous / n_tot)
    cum_vrai[f"{th:.2f}"] = tiers.bilan_blocs(vrai, RHO, 1000)
    cum_mel[f"{th:.2f}"] = tiers.bilan_blocs(mel, RHO, 1000)
    rs = []
    for i in range(len(has[0])):
        rs.append(tiers.bilan_blocs([h[i] for h in has], RHO, 10)["r"])
    cum_hasard[f"{th:.2f}"] = {"r_moyen": float(np.mean(rs)), "r_min": float(np.min(rs)), "r_max": float(np.max(rs)),
                               "sigma": float(np.std(rs))}
    t.setdefault("sans_portage", {})[f"{th:.2f}"] = {"r_vrai": r_sp_vrai, "r_melange": r_sp_mel, "r0_marginal": r0[f"{th:.2f}"]}
t["T2_accepter_cumul_7_traces"] = {"vrai": cum_vrai, "melange": cum_mel}
t["T3_hasard_accepter_cumul_7_traces"] = cum_hasard
t["T2_tient"] = bool(all(0.90 <= cum_mel[k]["r"] <= 1.10 for k in cum_mel))
t["T3_tient"] = bool(all(0.93 <= cum_hasard[k]["r_moyen"] <= 1.07 for k in cum_hasard))
dire("T2 (mélange, accepter)", {k: round(v["r"], 3) for k, v in cum_mel.items()}, "vrai", {k: round(v["r"], 3) for k, v in cum_vrai.items()},
     "tient", t["T2_tient"])
dire("T3 (hasard)", cum_hasard, "tient", t["T3_tient"])
dire("sans portage", t["sans_portage"])
R["temoins"] = t

# ---------------------------------------------------------------- sensibilités (générations 120b, theta 0.20)
sens = {}
for nom, (N, pol, h, rho) in {"N326": (326, "lfu", 8.0, RHO), "N922": (922, "lfu", 8.0, RHO),
                              "LRU": (323, "lru", 8.0, RHO), "demi-vie32": (323, "lfu", 32.0, RHO),
                              "rho0.70": (323, "lfu", 8.0, 0.70), "rho0.766": (323, "lfu", 8.0, 0.766)}.items():
    lst = {}
    for cle in G120:
        ex, w, E = donnees[cle]
        df, sj = cache_memo("120-" + cle, ex, E, N, pol, h)
        ev, bl = evalue(cle, w, df, sj, rho=rho, thetas=[0.20], tirages=200)
        for k, v in bl.items():
            lst.setdefault(k[1], []).append(v)
    sens[nom] = {nm: tiers.bilan_blocs(v, rho, 1000) for nm, v in lst.items()}
    dire("sensibilité", nom, {k: (round(v["S"], 4), round(v["r"], 3)) for k, v in sens[nom].items()})
R["sensibilites_120b_generation_theta0.20"] = sens

# ---------------------------------------------------------------- courbe énergie(f), octets(f), KL(f) hypothétique
courbe = []
for th in [round(x, 2) for x in np.arange(0.0, 0.61, 0.02)] + [1.0001]:
    lst = {nm: [] for nm in ("accepter", "remonter0.40")}
    fr = []
    for cle in G120:
        ex, w, E = donnees[cle]
        df, sj = caches[cle]
        for nom, tp in (("accepter", None), ("remonter", 0.40)):
            if nom == "remonter" and tp <= th:
                continue
            e, b, ts = tiers.regle(df, sj, w, th, nom, RHO, tp)
            lst[nom if tp is None else f"{nom}{tp:.2f}"].append(tiers.blocs_trace(e, b, ts, w, df))
        w_s, d_s, t_s, debut = tiers._prelude(df, sj, w)
        fr.append(((w_s[debut][d_s] < th).sum(), d_s.sum()))
    f = sum(a for a, b in fr) / sum(b for a, b in fr)
    row = {"theta": th, "f_defauts_servis_rapide": float(f)}
    for nm, v in lst.items():
        if v:
            b = tiers.bilan_blocs(v, RHO, 50)
            row[nm] = {"S": b["S"], "E_rel": b["E_rel"], "r": b["r"],
                       "KL_hyp_lineaire": 0.0044 + (0.145 - 0.0044) * b["E_rel"]}
    courbe.append(row)
R["courbe_f"] = courbe

# ---------------------------------------------------------------- 20b (secondaire)
R["20b"] = {}
pool20 = {}
for groupe, dic in (("generation", G20), ("lecture", L20)):
    for cle, base in dic.items():
        ex, w, E = charger(d20, base)
        df, sj = cache_memo(cle, ex, E, 54)
        ev, bl = evalue(cle, w, df, sj, thetas=[0.20, 0.25], tirages=500)
        R["20b"][cle] = ev
        for k, v in bl.items():
            pool20.setdefault((groupe, k), []).append(v)
R["20b"]["cumul"] = {}
for (groupe, (th, nm)), lst in pool20.items():
    R["20b"]["cumul"].setdefault(groupe, {}).setdefault(f"{th:.2f}", {})[nm] = tiers.bilan_blocs(lst, RHO, 1000)
dire("20b cumul génération theta 0.20", {k: (round(v["S"], 4), round(v["r"], 3))
                                         for k, v in R["20b"]["cumul"]["generation"]["0.20"].items()})
dire("20b cumul lecture theta 0.20", {k: (round(v["S"], 4), round(v["r"], 3))
                                      for k, v in R["20b"]["cumul"]["lecture"]["0.20"].items()})

R["duree_s"] = time.time() - t_debut
json.dump(R, open(os.path.join(sortie, "etape0.json"), "w", encoding="utf-8"), indent=1, default=float)
dire("fini en", round(R["duree_s"]), "s")
