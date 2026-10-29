# Juge final : dans un fichier bilingue (\EF{anglais}{français}), compare les nombres et les renvois de
# chaque paire. Usage : python -I -X utf8 parite_ef.py <fichier.tex> [--casser]
import re
import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
from parite_nombres import arg_equilibre, sans_commentaires, neutraliser, normaliser, nombres, extraire  # noqa: E402

t = sans_commentaires(open(sys.argv[1], encoding="utf-8").read())
casser = "--casser" in sys.argv
paires = []
for m in re.finditer(r"\\EF\s*\{", t):
    i = m.end() - 1
    j = arg_equilibre(t, i)
    k = j
    while k < len(t) and t[k] in " \n":
        k += 1
    if k >= len(t) or t[k] != "{":
        continue
    l = arg_equilibre(t, k)
    paires.append((t[i + 1:j - 1], t[k + 1:l - 1]))
ecarts = 0
for n, (en, fr) in enumerate(paires):
    a = nombres(normaliser(neutraliser(en), False))
    b = nombres(normaliser(neutraliser(fr), True))
    if casser and n == 0 and a:
        a[0] = a[0] + "1"
    ra = sorted(extraire(en, "cref") + extraire(en, "ref") + extraire(en, "crefrange"))
    rb = sorted(extraire(fr, "cref") + extraire(fr, "ref") + extraire(fr, "crefrange"))
    if sorted(a) != sorted(b) or ra != rb:
        ecarts += 1
        print(f"paire {n} : EN {a} {ra}\n         FR {b} {rb}\n   « {en[:90]} »")
print(f"{len(paires)} paires, {ecarts} en écart")
sys.exit(1 if ecarts else 0)
