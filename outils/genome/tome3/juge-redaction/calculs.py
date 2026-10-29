# Juge de la rédaction du Tome III (français) : refait les calculs neufs des rédacteurs (étiquetés \calc,
# qu'aucune source n'avait posés), par un second chemin, et les compare au texte à l'arrondi imprimé.
# Chaque ligne : chapitre, ce que le texte imprime, ce que je trouve, verdict.
import math
import sys

CAS = [
    # (chapitre et ligne, imprimé, valeur refaite, décimales)
    ("04 l. 138 log2(2880!) par lgamma", "28948,6", math.lgamma(2881) / math.log(2), 1),
    ("04 l. 138 Stirling, premier terme f log2 f", "33096,5", 2880 * math.log2(2880), 1),
    ("04 l. 138 Stirling, f log2 e", "4155,0", 2880 * math.log2(math.e), 1),
    ("04 l. 138 Stirling, ½ log2(2πf)", "7,1", 0.5 * math.log2(2 * math.pi * 2880), 1),
    ("04 l. 138 par poids, 28948,6/(3·2880²) ×10³", "1,163", 1e3 * (math.lgamma(2881) / math.log(2)) / (3 * 2880 ** 2), 3),
    ("04 l. 140 768×16/8294400 ×10³", "1,48", 1e3 * 768 * 16 / 8294400, 2),
    ("04 l. 140 192×16/8294400 ×10⁴", "3,70", 1e4 * 192 * 16 / 8294400, 2),
    ("01 gain de pavage ½ log2(πe/6), bit", "0,254", 0.5 * math.log2(math.pi * math.e / 6), 3),
    ("01 gain de pavage en dB, 10 log10(πe/6)", "1,53", 10 * math.log10(math.pi * math.e / 6), 2),
    ("02 l. 312 Wilson, borne basse (p = 0,8714, n = 2550)", "0,8578", None, 4),
    ("02 l. 312 Wilson, borne haute", "0,8838", None, 4),
    ("10 l. 428 0,95^32", "19", 100 * 0.95 ** 32, 0),
    ("10 l. 428 0,95^64 (le texte : 3,7 %)", "3,7", 100 * 0.95 ** 64, 1),
    ("12 l. 44 √(512/2880)", "0,4216", math.sqrt(512 / 2880), 4),
    ("12 l. 44 (1 − √q)² (le texte : 0,334)", "0,334", (1 - math.sqrt(512 / 2880)) ** 2, 3),
    ("12 l. 44 (1 + √q)²", "2,021", (1 + math.sqrt(512 / 2880)) ** 2, 3),
    ("12 l. 216 G_Pareto(2,5) premier terme ½ log2((α−1)/(α−2))", "0,7925", 0.5 * math.log2(1.5 / 0.5), 4),
    ("12 l. 216 G_Pareto(2,5) second terme 1/(2(α−1) ln 2)", "0,4809", 1 / (2 * 1.5 * math.log(2)), 4),
    ("11 l. 275 5087/122640 en %", "4,148", 100 * 5087 / 122640, 3),
    ("11 l. 329 ⌊0,10 × 12264⌋", "1226", math.floor(0.10 * 12264), 0),
    ("08 l. 349 2,890/1,988", "1,454", 2.890 / 1.988, 3),
    ("08 l. 351 12 × (12251136 − 11878400)", "4472832", 12 * (12251136 - 11878400), 0),
    ("08 l. 272 1/0,96751 − 1 en %", "3,36", 100 * (1 / 0.96751 - 1), 2),
    ("08 l. 272 1/0,96688 − 1 en %", "3,43", 100 * (1 / 0.96688 - 1), 2),
    ("10 l. 231 (32 − 1)/254", "0,12", 31 / 254, 2),
    ("10 l. 306 686,8/468,5", "1,47", 686.8 / 468.5, 2),
    ("10 l. 306 2,00 × (1 − 2 × 0,058)", "1,769", 2.00 * (1 - 2 * 0.058), 3),
    ("06 l. 281 1,09/3,01", "0,362", 1.09 / 3.01, 3),
    ("06 l. 421 1/(1 − 0,10)", "1,11", 1 / 0.9, 2),
    ("06 l. 421 1/(1 − 0,161)", "1,19", 1 / (1 - 0.161), 2),
    # Valeurs non arrondies (kl-frontiere-juge.json, kl-synonyme-d1-juge.json) : 0,0360/0,0262 arrondis
    # donneraient 1,374 ; le texte imprime le quotient exact.
    ("07 l. 243 0,0360138/0,0261684", "1,38", 0.03601376394818165 / 0.026168395169990054, 2),
    ("02 l. 151 1/(1 − 0,0356) − 1 en %", "3,7", 100 * (1 / (1 - 0.0356) - 1), 1),
]


def wilson(p, n, z=1.96):
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return c - h, c + h


def main():
    w = wilson(0.8713725490196078, 2550)
    faux = 0
    for nom, txt, v, d in CAS:
        if v is None:
            v = w[0] if "basse" in nom else w[1]
        cible = float(txt.replace(",", "."))
        ok = round(v, d) == round(cible, d)
        faux += not ok
        print(f"{'égal' if ok else 'DIFFÉRENT':<10} {txt:>10}  {v:.6f}  {nom}")
    print(f"{len(CAS)} calculs, {faux} différents à l'arrondi imprimé")
    return 0


if __name__ == "__main__":
    sys.exit(main())
