# Juge final : les deux blocs du résumé (Résumé, Abstract) sont-ils les mêmes, au caractère près, dans
# fr/resume.tex et en/resume.tex ? Usage : python -I -X utf8 resumes.py <racine tome3>
import pathlib
import re
import sys

r = pathlib.Path(sys.argv[1])


def blocs(t):
    out = {}
    for nom in ("Résumé", "Abstract"):
        m = re.search(r"\\chapter\*\{" + nom + r"\}.*?\\end\{otherlanguage\}", t, re.S)
        out[nom] = m.group(0) if m else None
    return out


fr = blocs((r / "fr/resume.tex").read_text(encoding="utf-8"))
en = blocs((r / "en/resume.tex").read_text(encoding="utf-8"))
ok = True
for nom in fr:
    egal = fr[nom] is not None and fr[nom] == en[nom]
    ok &= egal
    print(f"{nom} : {'égal au caractère' if egal else 'DIFFÉRENT'} ({len(fr[nom] or '')} signes)")
sys.exit(0 if ok else 1)
