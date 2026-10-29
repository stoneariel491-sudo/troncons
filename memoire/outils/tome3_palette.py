# Le dictionnaire des couleurs du Tome III, chiffré : pour chaque paire que les figures demandent de
# distinguer, ΔE CIE76 (CIELAB, D65) en vision normale, deutéranope, protanope (Machado, Oliveira,
# Fernandes 2009, sévérité 1) et en gris (luminance relative).
#
# Les distances se calculent par les fonctions de l'outil du juge de design
# (outils/genome/tome3/juge-design/palette.py), exécuté sans être modifié, sortie avalée : c'est le même
# instrument que celui du jugement, pas une copie. Les couleurs ne sont tapées nulle part ici : elles se
# lisent dans le préambule (\definecolor{...}{HTML}{...}) et dans palette-tome3.tex (\colorlet{...}{...}),
# et les mélanges « X!p » et « X!p!Y » se résolvent comme xcolor (sRGB non linéaire).
#
# Critère, déclaré avant la passe : une paire tient si ΔE ≥ 5 en gris ET ΔE ≥ 10 en vision deutéranope.
# Ces deux seuils sont ceux du juge (JUGEMENT-figures-design.md § 2.2), qui les dit posés après lecture des
# rendus simulés ; ils ne sont pas de moi et je ne les règle pas.
#
# Témoins (déclarés avant la passe) :
#   T1. La paire « III-9.2 frontière (SerieF) / λ=0 (SerieC) » du journal du juge (journaux/palette.json)
#       se refait au dixième près, couleurs lues dans le préambule par l'analyseur d'ici.
#   T2. L'analyseur résout les mélanges comme le juge les a écrits dans palette.py :
#       SerieA!50 = 8FAECC, SerieE!50 = C6A2D6, Mant!30 = C0DCCD, black!45 = 8C8C8C.
#   T3. Un gris pur reste gris : son rendu deutéranope a le même code que lui.
# Cassure (--casse-melange) : l'analyseur ignore le « !p » des mélanges ; T2 doit tomber. En cassure,
# rien n'est écrit sous donnees/ ; le journal va dans palette-tome3-journal-casse.json.
#
# Usage (depuis la racine du dépôt) : python -I -X utf8 memoire/outils/tome3_palette.py [--casse-melange]
# Écrit sous memoire/figures/tome3/donnees/ :
#   palette-tome3-couleurs.csv  chaque couleur du dictionnaire : expression, code, gris, deutéranope
#   palette-tome3-paires.csv    chaque paire : ΔE dans les quatre vues, avant (dictionnaire du juge) et
#                               après (palette-tome3.tex), verdict
#   palette-tome3-vues.tex      \definecolor des rendus gris et deutéranope (pour le nuancier)
#   palette-tome3-nombres.tex   les nombres que le pilote et la légende d'exemple écrivent
#   palette-tome3-bascules.tex  les paires qui changent de verdict, groupées par point, et les fonds
#   palette-tome3-journal.json  témoins et résumé
import contextlib
import csv
import io
import json
import re
import runpy
import sys
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[2]
PREAMBULE = RACINE / "memoire/commun/preambule.tex"
PALETTE = RACINE / "memoire/figures/tome3/palette-tome3.tex"
OUTIL_JUGE = RACINE / "outils/genome/tome3/juge-design/palette.py"
JOURNAL_JUGE = RACINE / "outils/genome/tome3/juge-design/journaux/palette.json"
SORTIE = RACINE / "memoire/figures/tome3/donnees"
CASSE = "--casse-melange" in sys.argv

SEUIL_GRIS = 5.0
SEUIL_DEUTER = 10.0

# --- L'instrument du juge, exécuté tel quel (argv neutre : sa propre cassure ne doit pas s'activer) ---
_argv = sys.argv
sys.argv = [str(OUTIL_JUGE)]
with contextlib.redirect_stdout(io.StringIO()):
    JUGE = runpy.run_path(str(OUTIL_JUGE))
sys.argv = _argv
de = JUGE["de"]
lin = JUGE["lin"]
MACHADO = JUGE["MACHADO"]
MODES = JUGE["MODES"]


# --- Les couleurs : préambule, puis dictionnaire ------------------------------------------------------
def lire_preambule():
    base = {"black": (0.0, 0.0, 0.0), "white": (1.0, 1.0, 1.0)}
    for nom, h in re.findall(r"\\definecolor\{(\w+)\}\{HTML\}\{([0-9A-Fa-f]{6})\}", PREAMBULE.read_text(encoding="utf-8")):
        base[nom] = tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return base


def resoudre(expr, table):
    """Une expression xcolor « X », « X!p » ou « X!p!Y » (p en pour cent), en sRGB dans [0, 1]."""
    parts = expr.split("!")
    c = np.array(table[parts[0]])
    i = 1
    while i < len(parts):
        p = float(parts[i]) / 100
        autre = np.array(table[parts[i + 1]]) if i + 1 < len(parts) else np.ones(3)
        if not CASSE:
            c = p * c + (1 - p) * autre
        i += 2
    return tuple(float(x) for x in c)


def code(rgb):
    return "".join("%02X" % int(round(255 * x)) for x in rgb)


def lire_dictionnaire(table):
    texte = PALETTE.read_text(encoding="utf-8")
    dico = {}
    for nom, expr in re.findall(r"^\\colorlet\{(\w+)\}\{([^}]+)\}", texte, flags=re.M):
        table[nom] = resoudre(expr, table)
        dico[nom] = expr
    return dico


# Le dictionnaire du juge tel qu'il l'a écrit (§ 2.1), pour la colonne « avant ». Les expressions sont
# les siennes ; seules diffèrent de palette-tome3.tex celles que le commun a ajustées. Le brin n'est pas
# dans son tableau : III-7.4 le trace en SerieB, que G5 ne change pas.
AVANT = {
    "CouleurFrontiere": "SerieF", "CouleurSetoile": "SerieE", "CouleurNeuves": "SerieE",
    "CouleurVunZero": "black!35", "CouleurGagne": "Mant!8", "CouleurBrin": "SerieB",
    "CouleurCategorieB": "SerieD", "CouleurCategorieD": "SerieE",
}

# Les paires que les figures demandent de distinguer : (a, b, figures où elles se côtoient, forme).
# « forme » : la règle du dictionnaire double déjà la couleur d'une marque, d'un trait, de hachures ou d'un
# bord tracé (dit dans § 2.1 du juge ou dans palette-tome3.tex) ; la paire est chiffrée quand même. Un fond
# pâle ne se sépare jamais du papier par la couleur seule : le hors domaine porte ses hachures (chiffrées
# ici contre le papier et contre la zone gagnante), la zone gagnante son bord (le seuil, en t3 seuil).
PAIRES = [
    ("CouleurFrontiere", "CouleurSynonyme", "III-9.1, III-9.2, III-9.6, III-10.3", "trait"),
    ("CouleurFrontiere", "CouleurLambdaZero", "III-9.2, III-9.6, III-10.3", "trait"),
    ("CouleurSynonyme", "CouleurLambdaZero", "III-7.1, III-7.2, III-9.2, III-9.6, III-10.3", "trait"),
    ("CouleurFrontiere", "CouleurQdeux", "III-9.2, III-9.6", "trait"),
    ("CouleurSynonyme", "CouleurQdeux", "III-9.2, III-9.6", "trait"),
    ("CouleurLambdaZero", "CouleurQdeux", "III-9.2, III-9.6", "trait"),
    ("CouleurFrontiere", "CouleurExact", "III-9.6, III-10.3", "trait"),
    ("CouleurSynonyme", "CouleurExact", "III-9.6, III-10.3", "trait"),
    ("CouleurLambdaZero", "CouleurExact", "III-9.6, III-10.3", "trait"),
    ("CouleurFrontiereMarque", "CouleurSynonyme", "III-7.1, III-7.2", "marque"),
    ("CouleurFrontiereMarque", "CouleurLambdaZero", "III-7.1, III-7.2", "marque"),
    ("CouleurFrontiereMarque", "CouleurSetoile", "III-7.1, III-7.2", "marque"),
    ("CouleurSetoile", "CouleurSynonyme", "III-7.1, III-7.2", "aucune"),
    ("CouleurSetoile", "CouleurLambdaZero", "III-7.1, III-7.2", "aucune"),
    ("CouleurBrin", "CouleurSetoile", "III-7.4", "aucune"),
    ("CouleurBrin", "CouleurFrontiere", "III-7.4", "aucune"),
    ("CouleurBrin", "CouleurExact", "III-7.4", "aucune"),
    ("CouleurSetoile", "CouleurFrontiere", "III-7.4", "aucune"),
    ("CouleurBrin", "CouleurFrontiereMarque", "III-3.6", "marque"),
    ("CouleurVingtB", "CouleurCentVingtB", "III-8.3, III-8.8", "marque"),
    ("CouleurVunZero", "CouleurVunDeux", "III-8.6", "aucune"),
    ("CouleurVunZero", "CouleurCompagnon", "III-8.6", "aucune"),
    ("CouleurVunDeux", "CouleurCompagnon", "III-8.6", "aucune"),
    ("CouleurRun", "CouleurNeuves", "III-9.3, III-10.1, III-10.3", "marque"),
    ("CouleurSigne", "CouleurVunDeux", "III-8.1", "aucune"),
    ("CouleurGagne", "CouleurHorsDomaine", "III-7.1", "hachures"),
    ("CouleurGagne", "blanc", "III-7.1, III-8.5", "bord"),
    ("CouleurHorsDomaine", "blanc", "III-7.1, III-9.1", "hachures"),
    ("CouleurHachures", "blanc", "III-7.1, III-9.1", "aucune"),
    ("CouleurHachures", "CouleurGagne", "III-7.1", "aucune"),
    ("CouleurCategorieA", "CouleurCategorieB", "III-7.6", "marque"),
    ("CouleurCategorieA", "CouleurCategorieC", "III-7.6", "marque"),
    ("CouleurCategorieA", "CouleurCategorieD", "III-7.6", "marque"),
    ("CouleurCategorieB", "CouleurCategorieC", "III-7.6", "marque"),
    ("CouleurCategorieB", "CouleurCategorieD", "III-7.6", "marque"),
    ("CouleurCategorieC", "CouleurCategorieD", "III-7.6", "marque"),
    # Troisième passe (GD1 du juge de design du second flux) : les couleurs qui remplacent le bleu hors
    # dictionnaire. Ce ne sont pas des entrées du dictionnaire mais des expressions xcolor des figures, résolues
    # ici de la même façon ; la colonne « avant » donne la paire que la figure avait avec le bleu (Accent, de même
    # valeur que SerieA), quand il y en avait une.
    ("Encre!55", "CouleurSigne", "III-8.1 (rayons positifs contre négatifs)", "aucune"),
    ("Encre!55", "CouleurVunDeux", "III-8.1 (rayons positifs contre le zéro)", "aucune"),
    ("Encre!60", "CouleurFrontiereMarque", "III-8.5 (c) (colonne contre F1)", "marque"),
    ("Encre!60", "CouleurVunDeux", "III-8.5 (colonne contre codon du zéro)", "marque"),
    ("CouleurVunDeux!15", "blanc", "III-8.7 (champ changé contre champ inchangé)", "bord"),
    ("Encre", "black!55", "III-2.1 (gate contre up)", "aucune"),
    ("black!55", "black!30", "III-2.1 (up contre down)", "aucune"),
    ("Encre", "black!30", "III-2.1 (gate contre down)", "aucune"),
    ("black!5", "blanc", "III-10.1 (« les deux », peu d'appels, contre « jamais routé »)", "bord"),
    ("black!8", "Encre", "III-8.4 (ligne égale contre ligne qui diffère)", "marque"),
]
# Ce que ces expressions remplacent (colonne « avant »), d'après les sources du second flux.
AVANT_EXPR = {
    "Encre!55": "Accent", "Encre!60": "Accent", "CouleurVunDeux!15": "Accent!14",
    "Encre": None, "black!55": None, "black!30": None, "black!5": "black!8", "black!8": "Mant!30",
}
# Les trois barres de III-2.1 avant : gate en catégorie A (SerieA), up en catégorie B (SerieC), down en D (SerieE!70).
AVANT_PAIRE = {
    ("Encre", "black!55"): ("SerieA", "SerieC"), ("black!55", "black!30"): ("SerieC", "SerieE!70"),
    ("Encre", "black!30"): ("SerieA", "SerieE!70"),
}


def vue_rgb(h, mode):
    """Le rendu sRGB d'un code dans une vue : gris (luminance) ou simulation de Machado."""
    l = lin(h)
    if mode == "gris":
        y = float(l @ np.array([0.2126, 0.7152, 0.0722]))
        l = np.array([y, y, y])
    elif mode in MACHADO:
        l = np.clip(np.array(MACHADO[mode]) @ l, 0, 1)
    s = np.where(l <= 0.0031308, 12.92 * l, 1.055 * np.power(l, 1 / 2.4) - 0.055)
    return tuple(float(x) for x in np.clip(s, 0, 1))


def verdict(d):
    return "tient" if d["gris"] >= SEUIL_GRIS and d["deuter"] >= SEUIL_DEUTER else "tombe"


def main():
    table = lire_preambule()
    table["blanc"] = (1.0, 1.0, 1.0)
    dico = lire_dictionnaire(table)
    hexa = {n: code(table[n]) for n in list(dico) + ["blanc"]}

    # Témoins.
    juge = json.loads(JOURNAL_JUGE.read_text(encoding="utf-8"))
    t1_attendu = juge["paires"]["III-9.2 frontière (SerieF) / λ=0 (SerieC)"]
    t1_refait = {m: round(de(code(table["SerieF"]), code(table["SerieC"]), m), 1) for m in MODES}
    t1 = t1_refait == t1_attendu
    t2_attendu = {"SerieA!50": "8FAECC", "SerieE!50": "C6A2D6", "Mant!30": "C0DCCD", "black!45": "8C8C8C"}
    t2_refait = {e: code(resoudre(e, table)) for e in t2_attendu}
    t2 = t2_refait == t2_attendu
    t3 = code(vue_rgb("808080", "deuter")) == "808080"

    # Avant : le dictionnaire du juge.
    table_avant = dict(table)
    for nom, expr in AVANT.items():
        table_avant[nom] = resoudre(expr, table)
    hexa_avant = {n: code(table_avant[n]) for n in hexa}
    # Troisième passe : les expressions des figures (pas des noms du dictionnaire), résolues comme xcolor.
    for a, b, _, _ in PAIRES:
        for e in (a, b):
            if e not in hexa:
                hexa[e] = code(resoudre(e, table))
                hexa_avant[e] = code(resoudre(AVANT_EXPR.get(e) or e, table))

    lignes = []
    for a, b, figs, forme in PAIRES:
        apres = {m: round(de(hexa[a], hexa[b], m), 1) for m in MODES}
        if (a, b) in AVANT_PAIRE:
            xa, xb = (code(resoudre(x, table)) for x in AVANT_PAIRE[(a, b)])
        else:
            xa, xb = hexa_avant[a], hexa_avant[b]
        avant = {m: round(de(xa, xb, m), 1) for m in MODES}
        lignes.append({
            "a": a.replace("Couleur", ""), "b": b.replace("Couleur", ""),
            "figures": figs.replace(", ", " ; "), "forme": forme,
            "code_a": hexa[a], "code_b": hexa[b],
            **{f"{m}": apres[m] for m in MODES},
            **{f"{m}_avant": avant[m] for m in MODES},
            "verdict": verdict(apres), "verdict_avant": verdict(avant),
            "change": int(hexa[a] != hexa_avant[a] or hexa[b] != hexa_avant[b]),
        })

    n = len(lignes)
    tiennent = sum(l["verdict"] == "tient" for l in lignes)
    tiennent_avant = sum(l["verdict_avant"] == "tient" for l in lignes)
    tombent = [f"{l['a']} / {l['b']}" for l in lignes if l["verdict"] == "tombe"]
    tombent_sans_forme = [f"{l['a']} / {l['b']}" for l in lignes if l["verdict"] == "tombe" and l["forme"] == "aucune"]
    journal = {
        "methode": "ΔE CIE76 par les fonctions de outils/genome/tome3/juge-design/palette.py ; "
                   f"tient si gris >= {SEUIL_GRIS} et deutéranope >= {SEUIL_DEUTER}",
        "casse": CASSE,
        "temoins": {"T1_juge_refait": t1, "T1_attendu": t1_attendu, "T1_refait": t1_refait,
                    "T2_melanges": t2, "T2_attendu": t2_attendu, "T2_refait": t2_refait,
                    "T3_gris_reste_gris": t3},
        "paires": n, "tiennent": tiennent, "tiennent_avant": tiennent_avant,
        "tombent": tombent, "tombent_sans_forme": tombent_sans_forme,
    }
    if CASSE:
        (SORTIE / "palette-tome3-journal-casse.json").write_text(
            json.dumps(journal, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(json.dumps(journal["temoins"], ensure_ascii=False))
        return 0 if not t2 else 1
    if not (t1 and t2 and t3):
        print(json.dumps(journal["temoins"], ensure_ascii=False), file=sys.stderr)
        raise SystemExit("témoin tombé : rien n'est écrit")

    with open(SORTIE / "palette-tome3-couleurs.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["nom", "expression", "code", "code_avant", "gris", "deuter"])
        for nom, expr in dico.items():
            w.writerow([nom, expr, hexa[nom], hexa_avant[nom], code(vue_rgb(hexa[nom], "gris")),
                        code(vue_rgb(hexa[nom], "deuter"))])
    with open(SORTIE / "palette-tome3-paires.csv", "w", encoding="utf-8", newline="") as f:
        cles = list(lignes[0])
        w = csv.DictWriter(f, fieldnames=cles, lineterminator="\n")
        w.writeheader()
        w.writerows(lignes)
    with open(SORTIE / "palette-tome3-vues.tex", "w", encoding="utf-8") as f:
        f.write("% Écrit par memoire/outils/tome3_palette.py : rendus en gris et en vision deutéranope\n"
                "% (Machado et al. 2009, sévérité 1) de chaque couleur de palette-tome3.tex. Ne pas éditer.\n")
        for nom in dico:
            f.write(f"\\definecolor{{{nom}Gris}}{{HTML}}{{{code(vue_rgb(hexa[nom], 'gris'))}}}\n")
            f.write(f"\\definecolor{{{nom}Deuter}}{{HTML}}{{{code(vue_rgb(hexa[nom], 'deuter'))}}}\n")
    mins = {m: min(l[m] for l in lignes) for m in ("gris", "deuter")}
    with open(SORTIE / "palette-tome3-nombres.tex", "w", encoding="utf-8") as f:
        f.write("% Écrit par memoire/outils/tome3_palette.py. Ne pas éditer.\n")
        f.write(f"\\def\\PalPaires{{{n}}}\n\\def\\PalTiennent{{{tiennent}}}\n")
        f.write(f"\\def\\PalTiennentAvant{{{tiennent_avant}}}\n")
        f.write(f"\\def\\PalSeuilGris{{{SEUIL_GRIS:g}}}\n\\def\\PalSeuilDeuter{{{SEUIL_DEUTER:g}}}\n")
        f.write(f"\\def\\PalChangees{{{sum(l['change'] for l in lignes)}}}\n")
        f.write(f"\\def\\PalTombent{{{len(tombent)}}}\n")
        f.write(f"\\def\\PalTombentSansForme{{{len(tombent_sans_forme)}}}\n")
        f.write(f"\\def\\PalMinGris{{{mins['gris']}}}\n\\def\\PalMinDeuter{{{mins['deuter']}}}\n")
        bascules = [l for l in lignes if l["verdict"] == "tient" and l["verdict_avant"] == "tombe"]
        f.write(f"\\def\\PalBasculent{{{len(bascules)}}}\n")
    # Pour la figure d'exemple : les paires qui passent de « tombe » à « tient », groupées par point
    # (des paires de mêmes couleurs tombent au même point), rangées par ΔE gris croissant ; puis les
    # paires qui tombent encore (les fonds, séparés par la forme).
    groupes = {}
    for l in bascules:
        cle = (l["gris"], l["deuter"], l["gris_avant"], l["deuter_avant"])
        groupes.setdefault(cle, []).append(l)
    def nommer(l):
        return f"\\PaletteNom{{{l['a']}}}\\,/\\,\\PaletteNom{{{l['b']}}}"
    with open(SORTIE / "palette-tome3-bascules.tex", "w", encoding="utf-8") as f:
        f.write("% Écrit par memoire/outils/tome3_palette.py. Ne pas éditer.\n"
                "% \\PalBascule{rang}{gris avant}{deutéranope avant}{gris}{deutéranope}{paires}\n"
                "% \\PalFond{gris}{deutéranope}{paire}\n")
        for i, (cle, ls) in enumerate(sorted(groupes.items(), key=lambda kv: kv[0][0]), 1):
            noms = "\\\\".join(nommer(l) for l in ls)
            f.write(f"\\PalBascule{{{i}}}{{{cle[2]}}}{{{cle[3]}}}{{{cle[0]}}}{{{cle[1]}}}{{{noms}}}\n")
        for l in lignes:
            if l["verdict"] == "tombe":
                f.write(f"\\PalFond{{{l['gris']}}}{{{l['deuter']}}}{{{nommer(l)}}}\n")
    (SORTIE / "palette-tome3-journal.json").write_text(
        json.dumps(journal, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{tiennent}/{n} paires tiennent (avant : {tiennent_avant}/{n}) ; tombent : {tombent}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
