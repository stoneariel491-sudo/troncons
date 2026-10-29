"""Compare deux PDF page à page, mot à mot (pdftotext sans mise en page ; pages séparées par saut de page).
Usage : python -I -X utf8 comparer.py a.pdf b.pdf [--sans CARACTÈRES]
Écrit : le nombre de pages de chacun, les pages dont la suite de mots diffère, et pour les trois premières le
premier écart. --sans retire des caractères avant de comparer (par exemple « ■ », que l'extraction de 26.5
rend et pas celle de 26.2)."""
import subprocess
import sys

a, b = sys.argv[1], sys.argv[2]
sans = sys.argv[sys.argv.index("--sans") + 1] if "--sans" in sys.argv else ""


def pages(pdf):
    t = subprocess.run(["pdftotext", "-enc", "UTF-8", pdf, "-"], capture_output=True).stdout.decode("utf-8", "replace")
    for c in sans:
        t = t.replace(c, " ")
    return [p.split() for p in t.split("\f")]


pa, pb = pages(a), pages(b)
print(f"pages : {len(pa) - 1} et {len(pb) - 1} ; mots : {sum(map(len, pa))} et {sum(map(len, pb))}")
diff = [i for i in range(max(len(pa), len(pb))) if (pa[i] if i < len(pa) else None) != (pb[i] if i < len(pb) else None)]
print(f"pages dont les mots diffèrent : {len(diff)}" + (f" ({', '.join(str(i + 1) for i in diff[:30])}{' …' if len(diff) > 30 else ''})" if diff else ""))
for i in diff[:3]:
    x, y = (pa[i] if i < len(pa) else []), (pb[i] if i < len(pb) else [])
    k = next((j for j in range(min(len(x), len(y))) if x[j] != y[j]), min(len(x), len(y)))
    print(f"  page {i + 1}, mot {k} : « {' '.join(x[max(0, k - 4):k + 6])} »  contre  « {' '.join(y[max(0, k - 4):k + 6])} »")
