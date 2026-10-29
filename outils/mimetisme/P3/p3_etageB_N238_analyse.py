"""P3 étage B à N = 238 : second chemin (numpy depuis le CSV par position de `juge kl`) et verdict aux deux lectures de 03-critere-marge-declare.md.

Usage : python -X utf8 p3_etageB_N238_analyse.py
Entrées : etage-B/N238/juge-kl-p3-N238-b<β>.csv (une ligne par position notée) ; marge de la référence = colonne marge_ref du CSV du juge
(mesures/mimetisme/P3/juge/etage-B/kl-b0.06-positions.csv), propre à la position et indépendante de la passe testée (recoupée ensuite par le lecteur .kld).
Rien n'est ajusté après lecture : les seuils sont ceux de 03- et de 00-seuils-declares.md.
"""
import csv
import json
import pathlib

import numpy as np

DEPOT = pathlib.Path(__file__).resolve().parents[3]
N238 = DEPOT / "mesures/mimetisme/P3/etage-B/N238"
MARGES = DEPOT / "mesures/mimetisme/P3/juge/etage-B/kl-b0.06-positions.csv"
ENS = json.load(open(DEPOT / "mesures/mimetisme/P3/ensembles-N238.json", encoding="utf-8"))
SEUIL_KL_TIENT, SEUIL_KL_MORT, SEUIL_PC, SEUIL_MARGE = 0.038, 0.07, 0.95, 0.3
BETAS = ["0.041", "0.05"]
rng = np.random.default_rng(20261027)


def lire(p):
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def boot(valeurs, fen, poids=None, tirages=20000):
    """Moyenne par rééchantillonnage des 10 fenêtres (blocs) ; poids : sous-ensemble booléen (quotient de deux sommes)."""
    f = np.unique(fen)
    num = np.array([valeurs[fen == k].sum() if poids is None else valeurs[(fen == k) & poids].sum() for k in f])
    den = np.array([len(valeurs[fen == k]) if poids is None else (poids & (fen == k)).sum() for k in f])
    idx = rng.integers(0, len(f), size=(tirages, len(f)))
    m = num[idx].sum(1) / den[idx].sum(1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


mr_csv = lire(MARGES)
marge = np.array([float(x["marge_ref"]) for x in mr_csv])
cle_marge = [(x["fenetre"], x["position"]) for x in mr_csv]
d0 = ENS["defauts_beta0"]
res = {"seuils": {"kl_tient": SEUIL_KL_TIENT, "kl_mort": SEUIL_KL_MORT, "premier_choix": SEUIL_PC, "marge": SEUIL_MARGE}, "passes": {}}
for b in BETAS:
    L = lire(N238 / f"juge-kl-p3-N238-b{b}.csv")
    assert [(x["fenetre"], x["position"]) for x in L] == cle_marge, "positions différentes de la grille des marges"
    kl = np.array([float(x["kl"]) for x in L])
    fen = np.array([int(x["fenetre"]) for x in L])
    pb = np.array([int(x["premier_base"]) for x in L])
    pt = np.array([int(x["premier_test"]) for x in L])
    mp = np.array([int(x["meme_premier"]) for x in L], bool)
    mp2 = pb == pt                                   # recalculé, sans la colonne du juge
    assert (mp == mp2).all(), "meme_premier du juge différent de premier_base == premier_test"
    fort = marge >= SEUIL_MARGE
    var = ENS["lignes"][b]["variation"]
    lit, pond = mp2.mean(), mp2[fort].mean()
    r = {
        "n": len(L), "defauts": ENS["lignes"][b]["defauts"], "variation_defauts": var,
        "kl_moyenne": float(kl.mean()), "kl_mediane": float(np.median(kl)), "kl_p99": float(np.percentile(kl, 99)),
        "kl_par_fenetre": [float(kl[fen == k].mean()) for k in range(10)],
        "kl_bootstrap_fenetres_95": boot(kl, fen),
        "premier_choix_litteral": float(lit), "desaccords_litteral": int((~mp2).sum()),
        "premier_choix_litteral_bootstrap_95": boot(mp2.astype(float), fen),
        "positions_marge>=0.3": int(fort.sum()), "part_positions_marge>=0.3": float(fort.mean()),
        "premier_choix_pondere": float(pond), "desaccords_pondere": int((~mp2[fort]).sum()),
        "premier_choix_pondere_bootstrap_95": boot(mp2.astype(float), fen, poids=fort),
        "pondere_par_fenetre": [float(mp2[(fen == k) & fort].mean()) for k in range(10)],
        "meme_premier_si_marge>=0.1": float(mp2[marge >= 0.1].mean()),
        "desaccords_marge<0.1": float((marge[~mp2] < 0.1).mean()), "desaccords_marge<0.3": float((marge[~mp2] < 0.3).mean()),
        "marge_mediane_des_desaccords": float(np.median(marge[~mp2])),
    }
    res["passes"][b] = r
# verdicts : β₁ = 0.041 décide ; β₂ = 0.05 pour la pente et la condition « aucun β à −5 % »
def verdict(lect):
    cle = "premier_choix_pondere" if lect == "pondere" else "premier_choix_litteral"
    p1, p2 = res["passes"]["0.041"], res["passes"]["0.05"]
    ok_defauts = p1["variation_defauts"] <= -0.10
    if ok_defauts and p1["kl_moyenne"] <= SEUIL_KL_TIENT and p1[cle] >= SEUIL_PC:
        v = "tient (partiel : N = 238 seul)"
        borne = p1[cle + "_bootstrap_95"][0]
        if borne < SEUIL_PC:
            v += ", à l'estimation ponctuelle ; borne basse de l'intervalle %.4f sous 95 %%" % borne
        return v
    if p1["kl_moyenne"] > SEUIL_KL_MORT or all(p["kl_moyenne"] > SEUIL_KL_TIENT for p in (p1, p2)):
        return "tombe"
    return "non concluant"
res["verdict_pondere"] = verdict("pondere")
res["verdict_litteral"] = verdict("litteral")
res["rapport_kl_sur_part_changee"] = {b: res["passes"][b]["kl_moyenne"] / ENS["lignes"][b]["stats"]["part_cellules_changees"] for b in BETAS}
# triangulaire grossière : sqrt(KL(β₁‖ref)) + ... n'est pas disponible sans KL(β₁‖β₂) ; on rapporte seulement la monotonie
res["monotone_kl_beta"] = res["passes"]["0.041"]["kl_moyenne"] <= res["passes"]["0.05"]["kl_moyenne"]
(N238 / "analyse-N238.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(res, ensure_ascii=False, indent=1))
