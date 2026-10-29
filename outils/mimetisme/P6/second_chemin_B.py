"""Second chemin de la variante B : boucles en dictionnaires, tri de Python, sans numpy dans le calcul de r.
Usage : python -I -X utf8 second_chemin_B.py <dossier traces> <sortie.json>
Compare à r(masse) et r(max) de etape0_B.py (lots de 512, S = 8 %) ; ex æquo départagés par la clé."""
import json, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tiers
d, sortie = sys.argv[1:3]
RHO, S, TAILLE = 0.718, 0.08, 512
res = {}
for genre, base in {"code": "t120b.code.lecture", "dialogue": "t120b.dialogue.lecture",
                    "prose-en": "t120b.prose-en.lecture", "prose-fr": "t120b.prose-fr.lecture"}.items():
    ex, w, E = tiers.charger(f"{d}/{base}.trace", f"{d}/{base}.poids")
    T, L, K = ex.shape
    masse, mx, e2 = defaultdict(float), defaultdict(float), defaultdict(float)
    for t in range(T):
        for l in range(L):
            for s in range(K):
                cle = (t // TAILLE, l, int(ex[t, l, s]))
                x = float(w[t, l, s])
                masse[cle] += x
                mx[cle] = max(mx[cle], x)
                e2[cle] += x * x
    n = len(masse)
    k = round(S / (1 - RHO) * n)
    tot = sum(e2.values())
    out = {"cles": n, "k": k}
    for nom, sc in (("masse", masse), ("max", mx)):
        choisis = sorted(sc, key=lambda c: (sc[c], c))[:k]
        out[nom] = (sum(e2[c] for c in choisis) / tot) / (k / n)
    res[genre] = out
    print(genre, out, flush=True)
json.dump(res, open(sortie, "w", encoding="utf-8"), indent=1)
