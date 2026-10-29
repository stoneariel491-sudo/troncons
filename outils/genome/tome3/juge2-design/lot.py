# Juge de design du second flux (Tome III) : couleurs rendues de chaque page de figure des pilotes (français),
# par couleurs.py, et les paires d'entités NOMMÉES (dictionnaire ou préambule, pas les gris de l'encre ni les
# pixels de lissage) qui tombent aux seuils déclarés (gris < 5 ou deutéranope < 10).
# Usage : python -I -X utf8 lot.py DOSSIER_DES_PDF > journaux/rendu-paires.txt ; JSON complet dans journaux/rendu/.
import json, subprocess, sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
E = Path(sys.argv[1])
PAGES = {
    "pilote-tome3-ronde.pdf": {4: "III-1.1", 5: "III-1.2", 6: "III-2.1", 7: "III-3.4", 8: "III-3.6", 9: "III-4.2",
                               10: "III-4.8", 11: "III-7.1", 12: "III-7.2", 13: "III-7.3", 14: "III-7.4"},
    "pilote-tome3-latents.pdf": {4: "III-7.6", 5: "III-9.1 (d)", 6: "III-9.7"},
    "pilote-tome3-construction.pdf": {4: "III-8.1", 5: "III-8.2", 6: "III-8.3", 7: "III-8.4", 8: "III-8.5",
                                      9: "III-8.6", 10: "III-8.6 bis", 11: "III-8.7", 12: "III-8.8", 13: "III-9.1 (a)(b)(b')",
                                      14: "III-9.2", 15: "III-9.3", 16: "III-9.6", 17: "III-10.1", 18: "III-10.3"},
}
GRIS_ENCRE = lambda n: n == "?" or n.startswith("black!")
(ICI / "journaux/rendu").mkdir(parents=True, exist_ok=True)
for pdf, pages in PAGES.items():
    for p, fig in pages.items():
        out = subprocess.run([sys.executable, "-I", "-X", "utf8", str(ICI / "couleurs.py"), "page", str(E / pdf), str(p),
                              "200", "0.05", "0.03", "0.95", "0.62", "--min", "120"], capture_output=True, text=True,
                             encoding="utf-8", check=True).stdout
        (ICI / "journaux/rendu" / f"{fig.replace(' ', '_').replace('(', '').replace(')', '').replace(chr(39), 'p')}.json").write_text(out, encoding="utf-8")
        d = json.loads(out)
        noms = sorted({c["nom"] for c in d["couleurs"] if not GRIS_ENCRE(c["nom"])})
        print(f"== {fig} ({pdf} p. {p}) : entités rendues : {', '.join(noms)}")
        for q in d["paires"]:
            na, nb = q["a"].split()[0], q["b"].split()[0]
            if GRIS_ENCRE(na) or GRIS_ENCRE(nb) or na == nb:
                continue
            if q["verdict"] == "tombe":
                print(f"   tombe : {q['a']} / {q['b']}  gris {q['gris']}  deuter {q['deuter']}  normal {q['normal']}")
