"""Second chemin du juge technique du Tome II (memoire/tome2/JUGEMENT.md).

Deux instruments, bibliothèque standard seule, rien d'écrit dans le dépôt :

1. Parité des nombres entre les deux langues. Pour chaque chapitre, annexe et résumé, extrait
   tous les nombres du source anglais et du source français (commentaires TeX retirés, renvois
   et noms de fichiers retirés, séparateurs de milliers et virgule décimale normalisés) et
   compare les deux multiensembles. Imprime ce qui n'est que d'un côté.
   Témoin : --casser change un nombre (0.884) du texte anglais du chapitre 08, sans écart sinon, en mémoire ; l'instrument
   doit alors trouver un écart dans ce chapitre (code 1 sinon).

2. Recalculs. Refait depuis les CSV commités les chiffres sur lesquels porte une objection du
   jugement (et quelques confirmations), et les imprime à côté du chiffre publié.

Usage : python -I -X utf8 memoire/outils/tome2_juge.py [--casser]
"""
import collections
import csv
import math
import re
import statistics
import sys
from pathlib import Path

DEPOT = Path(__file__).resolve().parents[2]
T2 = DEPOT / "memoire" / "tome2"
MES = DEPOT / "mesures"


# --------------------------------------------------------------------------------------------
# 1. Parité EN / FR
def nombres(texte, anglais):
    t = texte
    if anglais:  # « 4,096 » ou « 4{,}096 » : séparateur de milliers anglais
        t = re.sub(r"(?<=\d)(?:,|\{,\})(?=\d{3}(?!\d))", "", t)
    t = re.sub(r"(?m)(?<!\\)%.*$", "", t)  # commentaires
    t = re.sub(r"\\(?:label|cref|Cref|ref|eqref|cite|textcite|parencite|input|includegraphics|"
               r"fichier|url|href|lstinputlisting)\{[^}]*\}", " ", t)
    t = t.replace("{,}", ".")
    t = re.sub(r"(?<=\d)(?:\\,|~|\\ |\{\\,\}|\\thinspace )(?=\d{3})", "", t)
    t = re.sub(r"(?<=\d),(?=\d)", ".", t)
    return re.findall(r"\d+(?:\.\d+)?", t)


def parite(casser=False):
    fichiers = (sorted((T2 / "en" / "chapitres").glob("*.tex"))
                + sorted((T2 / "en" / "annexes").glob("*.tex")) + [T2 / "en" / "resume.tex"])
    trouve_casse = False
    for f in fichiers:
        g = T2 / "fr" / f.relative_to(T2 / "en")
        texte_en = f.read_text(encoding="utf-8")
        if casser and f.name == "08-epreuve.tex":
            texte_en = texte_en.replace("0.884", "0.885", 1)
        a = collections.Counter(nombres(texte_en, True))
        b = collections.Counter(nombres(g.read_text(encoding="utf-8"), False))
        d1, d2 = a - b, b - a
        print(f"parité {f.parent.name}/{f.name} : EN {sum(a.values())} nombres, FR {sum(b.values())}")
        if d1:
            print("   seulement EN :", dict(d1))
        if d2:
            print("   seulement FR :", dict(d2))
        if casser and f.name == "08-epreuve.tex" and (d1 or d2):
            trouve_casse = True
    return trouve_casse


# --------------------------------------------------------------------------------------------
# 2. Recalculs
def lire(chemin):
    with open(chemin, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def montrer(nom, refait, publie):
    print(f"recalcul {nom} : refait {refait} ; publié {publie}")


def recalculs():
    corr = MES / "moteur" / "O" / "corrections" / "csv"
    v = {x["passe"]: x for x in lire(corr / "vitesse-2026-10-16-passes.csv")}
    b = lire(corr / "base-2026-10-16-passes.csv")
    garde = [float(v[p]["gen"]) for p in ("02-T120g", "05-T120g", "07-T120g", "08-T120g")]
    t16 = [float(x["generation_j_s"]) for x in b if x["nom"] == "L16"]
    xg, xt = sum(garde) / 4, sum(t16) / 2
    bruit = abs(garde[0] - garde[1]) / ((garde[0] + garde[1]) / 2)
    montrer("C6 rapport garde / fit -t 16", f"{xg:.4f} / {xt:.4f} = {xg / xt:.4f}", "1,965 / 0,884 = 2,22")
    montrer("C6 bruit de la paire 02-05 et seuil", f"{100 * bruit:.2f} % ; 2 × bruit + 3 = {200 * bruit + 3:.2f} %",
            "« 2 × 11,0 + 3 = 24,9 % »")
    attente = [float(v[p]["garde_attente_ms_par_jeton"]) for p in ("02-T120g", "05-T120g", "07-T120g", "08-T120g")]
    montrer("attente de la garde", f"{min(attente):.2f} à {max(attente):.2f} ms",
            "5,2 à 5,4 (ch. 07, 08) ; 5,2 à 5,3 (ch. 01, 03, 06)")
    g05, s04 = float(v["05-T120g"]["gen"]), float(v["04-T120s"]["gen"])
    montrer("coût de la garde à disque égal", f"{100 * (g05 / s04 - 1):.2f} %",
            "−1,6 % (ch. 00, 07, 08) ; −1,7 % (ch. 01, 03, 06)")
    montrer("garde au chemin critique / pas", f"{12.251136 / 1.07:.2f} ms / 457 = {100 * 12.251136 / 1.07 / 457:.2f} %",
            "« 11,4 ms … soit 2,4 % du pas »")
    k = [float(v[p]["gen"]) for p in ("06-T120k", "09-T120k")]
    montrer("KV f32, génération", f"{sum(k) / 2:.3f}", "1,496 ; 1,50")

    # N V V N du lot E : deux lectures du rapport.
    e = lire(MES / "moteur" / "E" / "csv" / "e2-nvvn-2026-10-15-nvvn.csv")
    groupes = collections.defaultdict(list)
    for x in e:
        groupes[(x["rang"], x["lettre"])].append(float(x["go_s_servis"]))
    med = {c: statistics.median(l) for c, l in groupes.items()}
    n = [m for c, m in med.items() if c[1] == "N"]
    w = [m for c, m in med.items() if c[1] == "V"]
    tous_n = [y for c, l in groupes.items() if c[1] == "N" for y in l]
    tous_v = [y for c, l in groupes.items() if c[1] == "V" for y in l]
    montrer("V / N, moyenne des médianes par rang", f"{(sum(w) / 2) / (sum(n) / 2):.4f}", "× 1,335")
    montrer("V / N, médiane des 8 passes A", f"{statistics.median(tous_v) / statistics.median(tous_n):.4f}", "× 1,335")

    # L12 du lot O : le bruit selon la définition du chapitre 07.
    o = {x["passe"]: x for x in lire(MES / "moteur" / "O" / "csv" / "o-jetons-s.csv")}
    b1 = float(o["2026-10-16-s2-16-l12-B"]["generation_jetons_s"])
    b2 = float(o["2026-10-16-s2-17-l12-B"]["generation_jetons_s"])
    montrer("L12, bruit des deux passes B", f"|{b1:.3f} − {b2:.3f}| / moyenne = {100 * abs(b1 - b2) / ((b1 + b2) / 2):.1f} %",
            "« 21 % de dispersion »")

    # K1 : de combien la pire passe manque le seuil.
    for pire in (32.99, 32.92):
        montrer(f"K1, manque de la passe {pire}", f"{100 * (1 - pire / 33.28):.2f} %", "« tombe de 0,9 % »")

    # La rampe de YaRN : écart de fréquence par position aux paires 9 et 17.
    base, s = 150000.0, 32.0
    a = 32 * math.log(4096 / (2 * math.pi * 32)) / math.log(base)
    bb = 32 * math.log(4096 / (2 * math.pi)) / math.log(base)
    for i, publie in ((9, "8,8·10⁻⁵"), (17, "9,8·10⁻⁵")):
        th = base ** (-2 * i / 64)
        r1 = min(max((i - a) / (bb - a), 0.0), 1.0)
        r2 = min(max((i - 8) / 10.0, 0.0), 1.0)
        dw = th * abs(((1 - r2) + r2 / s) - ((1 - r1) + r1 / s))
        montrer(f"Δω à la paire {i}", f"{dw:.3e} rad par position", publie)

    # Le disque du moteur contre le Tome I.
    montrer("disque dans le moteur / Tome I (2,82 Go/s, 16 Mio aléatoire QD 1)",
            f"1,55 / 2,82 = {1.55 / 2.82:.2f} ; 1,85 / 2,82 = {1.85 / 2.82:.2f}", "« le tiers »")
    montrer("seconde lecture du codeur / durée du codage", f"23,6 / 1 153,3 = {100 * 23.6 / 1153.3:.2f} %", "« au plus 2 % »")
    montrer("scores d'attention en f64", f"{64 * 4096 * 64 * 2 / 0.2e12 * 1e3:.3f} ms à 0,2 Tflop/s", "« au plus 0,15 ms »")

    # La pointe de llama.cpp dans la base balayée (non citée par le chapitre 07).
    p16 = [float(x["pointe_et_mo"]) for x in b if x["nom"] == "L16"]
    montrer("pointe de llama.cpp, fit -t 16", f"{sum(p16) / 2 / 1000:.2f} Go", "10,93 Go (fit -t 6, séance du 15)")


if __name__ == "__main__":
    casser = "--casser" in sys.argv[1:]
    trouve = parite(casser)
    if casser:
        print("témoin de la parité :", "tombe (écart trouvé)" if trouve else "NE TOMBE PAS")
        sys.exit(0 if trouve else 1)
    recalculs()
