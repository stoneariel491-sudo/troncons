"""Une rangée de 32 poids, avant et après la mutation synonyme (Tome III, figure III-9.1 (c)).

Écrit pour troncons, lot « espaces latents » du premier flux de figures du Tome III, le 2026-10-27.
Processeur seul, mémoire bornée (moins de 400 Mo) ; aucune passe du modèle.

LA MATRICE : la même que `mesures/genome/construction/synonyme/figures/spectre-L08-E00-gate.csv`
(panneaux (a) et (b) de III-9.1) : gpt-oss-20b, couche 8, expert 0, gate. Les poids exacts viennent du
GGUF (MXFP4) ; les deux bases viennent des fichiers .sym que le lot B a écrits et dont il a tiré ce CSV
(outils/genome/synonyme/donnees_figures.py) : `frontiere` (le symbole est une fonction du code) et
`synonyme-l1-d1` (mutation synonyme, λ = 1, amortissement δ* = 1). Rien n'est recalculé du choix des
symboles : la figure montre les symboles servis.

LE BLOC MONTRÉ, règle déclarée avant le tirage (2026-10-27) : on compte, pour chacun des 2 880 × 90
blocs de 32 poids de la matrice, les symboles que la mutation synonyme change (symbole synonyme ≠
symbole frontière) ; m est la médiane de ce compte sur les blocs ; le bloc montré est tiré, graine
écrite, parmi les blocs dont le compte vaut exactement m. Le bloc est donc typique par construction,
ni le plus spectaculaire ni le plus calme ; la distribution des comptes est écrite au JSON.

UNITÉS : chaque valeur est divisée par l'échelle du bloc s_b = 2^(e − 127) : les poids exacts tombent
sur la grille E2M1 {0 ; ±0,5 ; ±1 ; ±1,5 ; ±2 ; ±3 ; ±4 ; ±6}, les reconstructions sur les ± quatre
centres de la base.

TÉMOIN (doit pouvoir tomber) :
  R0 les .sym lus sont ceux du CSV du lot B : ‖W − Ŵ‖²_F (en unités brutes) égale Σ_k e_k du CSV
     (les u_k sont orthonormés, donc Σ_k ‖ΔW u_k‖² = ‖ΔW‖²_F), pour la frontière et pour le
     synonyme, à 1e-6 relatif ; cassure : les .sym de l'expert 1 à la place de l'expert 0, l'écart
     doit dépasser 1e-3.

Sorties (mesures/genome/tome3/latents/) :
  rangee-L08-E00-gate.csv  : j (0 à 31), colonne, code MXFP4, exact, symbole et valeur frontière,
                             symbole et valeur synonyme, change (1 si le symbole change) ;
  rangee-L08-E00-gate.json : graine, ligne et bloc tirés, exposant, centres, comptes par bloc,
                             erreurs du bloc, témoin et cassure.

  python -I -X utf8 outils/genome/tome3/latents_rangee.py
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import latents_commun as lc  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
COUCHE, EXPERT, ROLE = 8, 0, "gate"
GRAINE = 20261027
SORTIE = os.path.join(lc.RACINE, "mesures/genome/tome3/latents")


def main() -> int:
    t0 = time.time()
    os.makedirs(SORTIE, exist_ok=True)
    lec, tens = lc.lecteur()
    j_role = lc.ROLES.index(ROLE)
    ex, codes = lc.blocs_expert(lec, tens, COUCHE, ROLE, EXPERT)
    W = lc.matrice_exacte(ex, codes)
    spec, chemin_spec = lc.lire_spectre(COUCHE, EXPERT, ROLE)
    sym, Wb, cen, chem = {}, {}, {}, {}
    R0 = {}
    for v, col in (("frontiere", "e_frontiere"), ("synonyme-l1-d1", "e_synonyme")):
        c, mats, chemin = lc.lire_sym(v, COUCHE, EXPERT)
        sym[v], cen[v], chem[v] = mats[j_role], c, chemin
        Wb[v] = lc.matrice_base(ex, sym[v], c)
        e_f = float(((W - Wb[v]) ** 2).sum())
        attendu = float(spec[col].sum())
        _, mats1, _ = lc.lire_sym(v, COUCHE, EXPERT + 1)
        e_c = float(((W - lc.matrice_base(ex, mats1[j_role], c)) ** 2).sum())
        R0[v] = {"norme2_erreur": e_f, "somme_e_k_csv": attendu, "ecart_relatif": abs(e_f / attendu - 1),
                 "cassure_expert1_ecart_relatif": abs(e_c / attendu - 1)}
    tient = all(r["ecart_relatif"] < 1e-6 for r in R0.values())
    tombe = all(r["cassure_expert1_ecart_relatif"] > 1e-3 for r in R0.values())
    print(f"R0 : {R0}", file=sys.stderr, flush=True)

    change = sym["frontiere"] != sym["synonyme-l1-d1"]
    cpt = change.reshape(lc.N, lc.NB, 32).sum(axis=2)          # (R, NB)
    m = int(np.median(cpt))
    cand = np.argwhere(cpt == m)
    rng = np.random.default_rng(GRAINE)
    ligne, bloc = (int(x) for x in cand[rng.integers(0, len(cand))])
    cols = np.arange(32 * bloc, 32 * bloc + 32)
    e = int(ex[ligne, bloc])
    s_b = float(np.ldexp(1.0, e - 127))
    hist = np.bincount(cpt.ravel(), minlength=33)
    with open(os.path.join(SORTIE, "rangee-L08-E00-gate.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["j", "colonne", "code", "exact", "sym_frontiere", "frontiere", "sym_synonyme", "synonyme", "change"])
        for jj, c in enumerate(cols):
            w.writerow([jj, int(c), int(codes[ligne, c]), f"{W[ligne, c] / s_b:.6f}",
                        int(sym["frontiere"][ligne, c]), f"{Wb['frontiere'][ligne, c] / s_b:.6f}",
                        int(sym["synonyme-l1-d1"][ligne, c]), f"{Wb['synonyme-l1-d1'][ligne, c] / s_b:.6f}",
                        int(change[ligne, c])])
    err_bloc = {v: float(((W[ligne, cols] - Wb[v][ligne, cols]) ** 2).sum() / s_b ** 2) for v in Wb}
    j = {"outil": "outils/genome/tome3/latents_rangee.py", "date": "2026-10-27", "graine": GRAINE,
         "matrice": f"blk.{COUCHE}.ffn_{ROLE}_exps.weight, expert {EXPERT} (gpt-oss-20b)",
         "sym": chem, "spectre_csv": os.path.relpath(chemin_spec, lc.RACINE).replace("\\", "/"),
         "regle": "bloc tiré (graine) parmi ceux dont le nombre de symboles changés égale la médiane sur les blocs",
         "ligne": ligne, "bloc": bloc, "colonnes": [int(cols[0]), int(cols[-1])], "exposant_e8m0": e,
         "echelle_bloc": s_b, "centres_E2M1": {v: (cen[v] / 2).tolist() for v in cen},
         "changes_dans_le_bloc": int(change[ligne, cols].sum()),
         "changes_par_bloc_mediane": m, "changes_par_bloc_moyenne": float(cpt.mean()),
         "part_symboles_changes_matrice": float(change.mean()),
         "histogramme_changes_par_bloc": hist.tolist(), "blocs_candidats": int(len(cand)),
         "erreur_bloc_unites_s_b2": err_bloc,
         "temoin_R0": R0, "R0_tient": bool(tient), "R0_cassure_tombe": bool(tombe),
         "duree_s": time.time() - t0}
    with open(os.path.join(SORTIE, "rangee-L08-E00-gate.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(j, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(json.dumps({k: j[k] for k in ("ligne", "bloc", "exposant_e8m0", "changes_dans_le_bloc", "changes_par_bloc_mediane",
                                        "changes_par_bloc_moyenne", "part_symboles_changes_matrice", "erreur_bloc_unites_s_b2",
                                        "R0_tient", "R0_cassure_tombe", "duree_s")}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
