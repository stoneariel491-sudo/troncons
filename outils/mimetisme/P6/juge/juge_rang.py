"""Juge P6 : le mélange par couche (T2 et « les défauts ne sont pas corrélés aux petits poids ») garde le rang.

Les poids d'un (t, l) sont rangés par ordre décroissant (rang 0 = le plus grand). Permuter les vecteurs entre
jetons d'une même couche garde donc « rang s -> poids de rang s ». Si les défauts tombent plus souvent au rang 3,
ce mélange ne peut pas voir la corrélation défaut / petit poids. Contrôle exploratoire, hors seuils déclarés :
taux de défaut par rang, et comptage sans portage (normalisation du rôle de mesure) sous trois mélanges :
vrai, vecteurs par couche (T2), poids permutés à l'intérieur de chaque groupe (rang détruit, loi du groupe gardée).
Usage : python -I -X utf8 juge_rang.py <dossier traces 120b> <sortie.json>
"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import juge_p6 as J

d120, sortie = sys.argv[1:3]
BASES = ["t120b.prose-en.generation", "w120b.wiki.generation", "t120b.code.lecture", "t120b.dialogue.lecture",
         "t120b.prose-en.lecture", "t120b.prose-fr.lecture", "w120b.wiki.lecture"]
TH = 0.20
rng = random.Random(3)
acc_rang = [0] * 4
def_rang = [0] * 4
tot = {"vrai": [0, 0, 0.0], "melange_couche": [0, 0, 0.0], "melange_dans_groupe": [0, 0, 0.0]}
g2_tout = 0.0
for base in BASES:
    ex, wt, E = J.charger(d120, base)
    acc = J.simuler(ex, E, 323)
    T, L = len(wt), len(wt[0])
    mc = [[None] * L for _ in range(T)]
    for l in range(L):
        o = list(range(T))
        rng.shuffle(o)
        for t in range(T):
            mc[t][l] = wt[o[t]][l]
    mg = [[rng.sample(g, len(g)) for g in row] for row in wt]
    for (t, l, s, x, d, sj) in acc:
        acc_rang[s] += 1
        g2_tout += wt[t][l][s] ** 2
        if d:
            def_rang[s] += 1
        for nom, ww in (("vrai", wt), ("melange_couche", mc), ("melange_dans_groupe", mg)):
            if d:
                w = ww[t][l][s]
                tot[nom][0] += 1
                if w < TH:
                    tot[nom][1] += 1
                    tot[nom][2] += w * w
    print(base, "fait", flush=True)
res = {"taux_defaut_par_rang": [def_rang[s] / acc_rang[s] for s in range(4)],
       "part_des_defauts_par_rang": [def_rang[s] / sum(def_rang) for s in range(4)],
       "sans_portage_r": {k: (v[2] / g2_tout) / (v[1] / v[0]) for k, v in tot.items()},
       "part_defauts_sous_theta": {k: v[1] / v[0] for k, v in tot.items()}}
print(json.dumps(res, ensure_ascii=False, indent=1))
with open(sortie, "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
