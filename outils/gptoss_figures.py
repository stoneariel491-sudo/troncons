"""Données et figures pgfplots du mémoire pour les mesures sur gpt-oss (localité et base).

Lit les CSV commités de outils/gptoss_localite.py et de outils/gptoss_base_serie.py, écrit des CSV
« larges » (une colonne par série, lisibles par pgfplots sans filtre) et un fichier LaTeX autonome
(standalone) qui trace :
  1. le succès du cache global selon le budget (5 à 40 % des experts), cinq politiques, trace
     « tous.lecture » ; la diagonale « sans localité » (épinglage d'un ensemble fixe sous routage
     uniforme : succès = budget) ;
  2. la réutilisation d'un jeton au suivant, couche par couche, contre ses deux hasards ;
  3. le plafond de jetons/s selon le budget (LRU, Belady, épinglage oracle), avec les débits mesurés,
     et les points mesurés de la base llama.cpp (génération, moyenne des passes).
Le PDF se construit par « lualatex figures-gpt-oss.tex » dans le dossier de sortie.

Usage : python -I gptoss_figures.py --localite <dossier mesures/localite-gpt-oss> --base <dossier
        mesures/base-gpt-oss> --sortie <dossier>
"""
import argparse
import csv
import os
import statistics

POL = ["lru", "lfu", "statique_calibre", "statique_oracle", "belady"]
# part des experts en VRAM de chaque configuration de la base (abscisse de ses points sur la figure des
# plafonds) : cmoe aucune ; fit, les couches entières mises en carte par llama-fit-params (20b : 0 à 9
# sur 24 ; 120b : 0 et 1 sur 36 ; plus une partie de la suivante, non comptée) ; cache, ses 323
# emplacements (42,1 % et 7,0 %, journal de llama.cpp)
BUDGET_BASE = {("gpt-oss-20b", "cmoe"): 0.0, ("gpt-oss-20b", "fit"): round(100 * 10 / 24, 1),
               ("gpt-oss-20b", "cache"): 42.1, ("gpt-oss-20b", "cachelv4"): 42.1,
               ("gpt-oss-120b", "cmoe"): 0.0, ("gpt-oss-120b", "fit"): round(100 * 2 / 36, 1),
               ("gpt-oss-120b", "cache"): 7.0}
NOM_SCEN = {"ram": "RAM", "deux_etages": r"deux \'etages"}


def lire(chemin):
    return list(csv.DictReader(open(chemin, encoding="utf-8")))


def ecrire(chemin, champs, lignes):
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(champs)
        w.writerows(lignes)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--localite", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--sortie", required=True)
    a = ap.parse_args()
    os.makedirs(a.sortie, exist_ok=True)
    modeles = []
    for m, scen in (("gpt-oss-20b", "ram"), ("gpt-oss-120b", "deux_etages")):
        d = os.path.join(a.localite, m.replace("gpt-oss-", ""))
        cc = os.path.join(d, f"courbes-{m}.csv")
        if not os.path.exists(cc):
            continue
        modeles.append((m, scen))
        courbes = lire(cc)
        budgets = sorted({int(l["budget_pct"]) for l in courbes})
        for trace in ("tous.lecture", "tous.generation"):
            lignes = []
            for b in budgets:
                v = {l["politique"]: l["succes"] for l in courbes
                     if l["trace"] == trace and l["portee"] == "globale" and int(l["budget_pct"]) == b}
                if v:
                    lignes.append([b] + [v[p] for p in POL] + [b / 100])
            ecrire(os.path.join(a.sortie, f"succes-{m}-{trace.split('.')[1]}.csv"), ["budget"] + POL + ["sans_localite"], lignes)
        couches = [l for l in lire(os.path.join(d, f"couches-{m}.csv")) if l["trace"] == "tous.lecture"]
        ecrire(os.path.join(a.sortie, f"reutilisation-{m}.csv"), ["couche", "reutilisation", "hasard_popularite", "hasard_uniforme"],
               [[l["couche"], l["reutilisation"], l["hasard_popularite"], l["hasard_uniforme"]] for l in couches])
        pl = lire(os.path.join(d, f"plafonds-{m}.csv"))
        lignes = []
        for b in budgets:
            ligne = [b]
            for p in ("lru", "belady", "statique_oracle"):
                # la lecture, résultat principal (mesures/gpt-oss.md, § 4.3) : changé le 2026-10-15, la
                # génération de 120b n'est qu'une trace de 256 jetons, en partie dégénérée
                r = [l for l in pl if l["trace"] == "tous.lecture" and l["politique"] == p and int(l["budget_pct"]) == b]
                cle = f"{scen}_serie" if r and r[0].get(f"{scen}_serie") else "disque_serie"
                cle2 = cle.replace("_serie", "_recouvert")
                ligne += [r[0][cle], r[0][cle2]] if r else ["nan", "nan"]
            lignes.append(ligne)
        ecrire(os.path.join(a.sortie, f"plafonds-{m}.csv"),
               ["budget", "lru_serie", "lru_recouvert", "belady_serie", "belady_recouvert", "statique_serie", "statique_recouvert"], lignes)
        # points mesurés de la base : génération moyenne par configuration
        pc = os.path.join(a.base, m.replace("gpt-oss-", ""), "passes.csv")
        if os.path.exists(pc):
            pas = [l for l in lire(pc) if not l["config"].endswith("echauffement") and l["generation_js"]]
            confs = list(dict.fromkeys(l["config"] for l in pas))
            lignes_b = []
            for i, c in enumerate(confs):
                v = [float(l["generation_js"]) for l in pas if l["config"] == c]
                moy = statistics.fmean(v)
                lignes_b.append([c, i, BUDGET_BASE[(m, c)], round(moy, 3), min(v), max(v),
                                 round(max(v) - moy, 3), round(moy - min(v), 3)])
            ecrire(os.path.join(a.sortie, f"base-{m}.csv"),
                   ["config", "rang", "budget", "generation_js", "min", "max", "err_plus", "err_moins"], lignes_b)
    tex = [r"\documentclass[border=4pt]{standalone}", r"\usepackage{pgfplots}", r"\pgfplotsset{compat=1.18}",
           r"\usepackage[T1]{fontenc}", r"\begin{document}", r"\begin{tabular}{@{}c@{}}"]
    style = {"lru": "blue, mark=*", "lfu": "orange, mark=square*", "statique_calibre": "gray, mark=triangle*",
             "statique_oracle": "black, mark=diamond*", "belady": "red, mark=x"}
    nom_pol = {"lru": "LRU", "lfu": "LFU (demi-vie 8)", "statique_calibre": "statique calibr\\'e",
               "statique_oracle": "statique oracle", "belady": "Belady (optimum)"}
    for m, scen in modeles:
        tex += [r"\begin{tikzpicture}", r"\begin{axis}[width=8cm, height=6cm, xlabel={budget (\% des experts)},",
                r"ylabel={succ\`es du cache global}, ymin=0, ymax=1, xmin=0, xmax=45, grid=major,",
                f"title={{{m} : succ\\`es selon le budget (lecture, 4 genres)}}, legend pos=outer north east, legend style={{font=\\tiny}}]"]
        for p in POL:
            tex.append(f"\\addplot[{style[p]}] table[x=budget, y={p}, col sep=comma] {{succes-{m}-lecture.csv}};")
            tex.append(f"\\addlegendentry{{{nom_pol[p]}}}")
        tex += [f"\\addplot[dashed, gray] table[x=budget, y=sans_localite, col sep=comma] {{succes-{m}-lecture.csv}};",
                r"\addlegendentry{ensemble fixe, routage uniforme}", r"\end{axis}", r"\end{tikzpicture}", r"\\"]
        tex += [r"\begin{tikzpicture}", r"\begin{axis}[width=8cm, height=5cm, xlabel={couche}, ylabel={r\'eutilisation $|S_t\cap S_{t-1}|/k$},",
                f"ymin=0, ymax=1, grid=major, title={{{m} : r\\'eutilisation d'un jeton au suivant}}, legend pos=north east, legend style={{font=\\tiny}}]",
                f"\\addplot[blue, mark=*] table[x=couche, y=reutilisation, col sep=comma] {{reutilisation-{m}.csv}};",
                r"\addlegendentry{mesur\'ee}",
                f"\\addplot[black, dashed] table[x=couche, y=hasard_popularite, col sep=comma] {{reutilisation-{m}.csv}};",
                r"\addlegendentry{hasard \`a popularit\'e r\'eelle}",
                f"\\addplot[gray, dotted, thick] table[x=couche, y=hasard_uniforme, col sep=comma] {{reutilisation-{m}.csv}};",
                r"\addlegendentry{hasard uniforme $k/E$}", r"\end{axis}", r"\end{tikzpicture}", r"\\"]
        tex += [r"\begin{tikzpicture}", r"\begin{axis}[width=8cm, height=6cm, xlabel={budget (\% des experts)}, ylabel={jetons/s (plafond)},",
                f"ymode=log, log ticks with fixed point, xmin=-2, xmax=48, grid=major, title={{{m} : plafond, lecture (d\\'ebits mesur\\'es, sc\\'enario {NOM_SCEN[scen]})}}, legend pos=north west, legend style={{font=\\tiny}}]",
                f"\\addplot[blue, mark=*] table[x=budget, y=lru_serie, col sep=comma] {{plafonds-{m}.csv}};", r"\addlegendentry{LRU, \'etages en s\'erie}",
                f"\\addplot[blue, dashed] table[x=budget, y=lru_recouvert, col sep=comma] {{plafonds-{m}.csv}};", r"\addlegendentry{LRU, recouverts}",
                f"\\addplot[red, mark=x] table[x=budget, y=belady_serie, col sep=comma] {{plafonds-{m}.csv}};", r"\addlegendentry{Belady, s\'erie}",
                f"\\addplot[black, mark=diamond*] table[x=budget, y=statique_serie, col sep=comma] {{plafonds-{m}.csv}};", r"\addlegendentry{statique oracle, s\'erie}",
                r"\addplot[only marks, mark=square*, mark size=2.5pt, green!50!black, error bars/.cd, y dir=both, y explicit] "
                f"table[x=budget, y=generation_js, y error plus=err_plus, y error minus=err_moins, col sep=comma] {{base-{m}.csv}};",
                r"\addlegendentry{base llama.cpp, mesur\'ee (min--max)}",
                r"\addplot[only marks, mark=none, nodes near coords, point meta=explicit symbolic, "
                r"every node near coord/.append style={font=\tiny, anchor=west}] "
                f"table[x=budget, y=generation_js, meta=config, col sep=comma] {{base-{m}.csv}};",
                r"\end{axis}", r"\end{tikzpicture}", r"\\"]
    tex += [r"\end{tabular}", r"\end{document}"]
    open(os.path.join(a.sortie, "figures-gpt-oss.tex"), "w", encoding="utf-8").write("\n".join(tex) + "\n")
    print("figures écrites :", a.sortie)


if __name__ == "__main__":
    main()
