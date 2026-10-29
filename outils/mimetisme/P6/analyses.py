"""P6 étape 0 : analyses exploratoires, hors verdict (étiquetées telles dans resultat.md).
 1. décomposition de E en énergie du défaut qui fixe l'étiquette (la « porte ») et énergie portée par les succès suivants ;
 2. prédicteur statique : poids moyen d'appel de chaque expert, appris sur les traces de lecture, jugé sur les générations ;
 3. stabilité d'un expert d'un séjour à l'autre : la corrélation entre le poids d'entrée et le poids moyen des succès.
Usage : python -I -X utf8 analyses.py <t120> <cache_dir> <sortie.json>"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import tiers

d120, cdir, sortie = sys.argv[1:4]
RHO = 0.718
G = {"gen-prose-en": "t120b.prose-en.generation", "gen-wiki": "w120b.wiki.generation"}
LEC = {"code": "t120b.code.lecture", "dialogue": "t120b.dialogue.lecture", "prose-en": "t120b.prose-en.lecture",
       "prose-fr": "t120b.prose-fr.lecture", "wiki-lecture": "w120b.wiki.lecture"}


def charge(base):
    return tiers.charger(os.path.join(d120, base + ".trace"), os.path.join(d120, base + ".poids"))


def cache(cle):
    z = np.load(os.path.join(cdir, f"120-{cle}-N323-lfu8.npz"))
    return z["defaut"], z["sejour"]


R = {}
gen = {k: charge(b) for k, b in G.items()}
lec = {k: charge(b) for k, b in LEC.items()}
cg = {k: cache(k) for k in G}

# ------------------------------------------------------------ 1. décomposition de E (accepter)
dec = {}
for th in (0.20, 0.25):
    num_porte = num_suite = tot = nmiss = 0.0
    for k in G:
        ex, w, E = gen[k]
        df, sj = cg[k]
        w_s, d_s, t_s, debut = tiers._prelude(df, sj, w)
        F = w_s[debut] < th
        porte = np.where(d_s & F, w_s ** 2, 0.0).sum()
        suite = np.where((~d_s) & F, w_s ** 2, 0.0).sum()
        num_porte += porte
        num_suite += suite
        tot += (w ** 2).sum()
        nmiss += d_s.sum()
    dec[f"{th:.2f}"] = {"E_porte_rel": num_porte / tot, "E_suite_rel": num_suite / tot,
                        "part_de_E_portee_par_les_succes_suivants": num_suite / (num_porte + num_suite)}
R["decomposition_E_accepter_cumul_generation"] = dec
print("décomposition", dec, flush=True)

# ------------------------------------------------------------ 2. prédicteur statique
L, E_ = 36, 128
somme = np.zeros(L * E_)
cnt = np.zeros(L * E_)
for k, (ex, w, E) in lec.items():
    items = (np.arange(L)[None, :, None] * E_ + ex).reshape(-1)
    np.add.at(somme, items, w.reshape(-1))
    np.add.at(cnt, items, 1.0)
mglob = somme.sum() / cnt.sum()
m = np.where(cnt >= 5, somme / np.maximum(cnt, 1), mglob)
R["predicteur_statique"] = {"poids_moyen_global": mglob, "ecart_type_des_m_x_(cnt>=5)": float(m[cnt >= 5].std()),
                            "experts_avec_>=5_appels": int((cnt >= 5).sum()), "m_min": float(m[cnt >= 5].min()),
                            "m_max": float(m[cnt >= 5].max())}
print(R["predicteur_statique"], flush=True)


def evalue_porte(portes, th_label, gens=gen):
    """portes : fonction (w0, m_x) -> bool (F). Règle accepter. Rend le bilan cumulé des deux générations."""
    blocs = []
    for k in G:
        ex, w, E = gens[k]
        df, sj = cg[k]
        w_s, d_s, t_s, debut = tiers._prelude(df, sj, w)
        items = (np.arange(L)[None, :, None] * E_ + ex).reshape(-1)
        ordre = np.argsort(sj.reshape(-1), kind="stable")
        mx = m[items[ordre]]
        F = portes(w_s[debut], mx[debut])
        energie = np.where(F, w_s ** 2, 0.0)
        octets = np.where(d_s, np.where(F, RHO, 1.0), 0.0)
        blocs.append(tiers.blocs_trace(energie, octets, t_s, w, df))
    return tiers.bilan_blocs(blocs, RHO, 500)


essais = []
for th in (0.20, 0.25, 0.30, 1.01):
    for thm in (0.22, 0.24, 0.25, 0.26, 0.28, 9.0):
        b = evalue_porte(lambda w0, mx, th=th, thm=thm: (w0 < th) & (mx < thm), "")
        essais.append({"type": "w0<theta ET m_x<theta_m", "theta": th, "theta_m": thm, **{k: b[k] for k in ("S", "E_rel", "r", "sigma_r")}})
for thm in (0.22, 0.23, 0.24, 0.25, 0.26, 0.27, 0.28):
    b = evalue_porte(lambda w0, mx, thm=thm: mx < thm, "")
    essais.append({"type": "m_x<theta_m seul", "theta": None, "theta_m": thm, **{k: b[k] for k in ("S", "E_rel", "r", "sigma_r")}})
R["predicteur_statique"]["essais"] = essais
R["predicteur_statique"]["nombre_d_essais"] = len(essais)
for e in essais:
    print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in e.items()})

# ------------------------------------------------------------ 3. le poids d'entrée prédit-il les poids suivants ?
corr = {}
for k in G:
    ex, w, E = gen[k]
    df, sj = cg[k]
    w_s, d_s, t_s, debut = tiers._prelude(df, sj, w)
    suite = ~d_s
    w0 = w_s[debut][suite]
    wn = w_s[suite]
    corr[k] = {"corr_poids_defaut_poids_succes": float(np.corrcoef(w0, wn)[0, 1]),
               "poids_moyen_succes": float(wn.mean()), "poids_moyen_defaut": float(w_s[d_s].mean()),
               "poids_moyen_defaut_si_<0.20": float(w_s[d_s][w_s[d_s] < 0.20].mean()),
               "poids_moyen_succes_si_defaut_<0.20": float(wn[w0 < 0.20].mean()),
               "poids_moyen_succes_si_defaut_>=0.20": float(wn[w0 >= 0.20].mean()),
               "acces_par_sejour_moyen": float(len(w_s) / d_s.sum())}
R["entree_contre_suite"] = corr
print(corr)
json.dump(R, open(sortie, "w", encoding="utf-8"), indent=1, default=float)
