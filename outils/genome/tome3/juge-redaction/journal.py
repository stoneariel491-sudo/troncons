# Juge de la rédaction du Tome III (français) : lit le journal de la dernière passe de lualatex du tome
# assemblé et rend, par fichier source, les boîtes trop pleines (avec leur largeur en trop), les renvois et
# citations indéfinis, les erreurs, et le nombre de pages. Le fichier d'une boîte est le dernier chapitre ou
# annexe ouvert avant elle dans le journal (\input les ouvre dans l'ordre ; les fichiers de figures sont
# chargés dans le préambule, avant tout chapitre).
# Usage : python -I -X utf8 journal.py memoire/essai/juge-redaction-fr-brouillon/troncons-tome3-fr.log
import pathlib
import re
import sys

RE_OUVRE = re.compile(r"\((?:\./)?((?:chapitres|annexes)/[\w\-]+\.tex)")
RE_OVER = re.compile(r"^Overfull \\[hv]box \(([\d.]+)pt too (?:wide|high)\) (.*)$")
RE_UNDEF = re.compile(r"(?:Reference|Citation) [`'](.+?)' on page \d+ undefined")


def main():
    log = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
    courant = "préambule"
    boites, indef, erreurs = {}, set(), []
    for l in log.splitlines():
        for m in RE_OUVRE.finditer(l):
            courant = m.group(1)
        m = RE_OVER.match(l)
        if m:
            boites.setdefault(courant, []).append((float(m.group(1)), m.group(2)[:70]))
        m = RE_UNDEF.search(l)
        if m:
            indef.add(m.group(1))
        if l.startswith("!") or re.match(r"^[^ ]+\.tex:\d+: ", l):
            erreurs.append(l[:160])
    pages = re.findall(r"Output written on .*?\((\d+) pages", log)
    print(f"pages : {pages[-1] if pages else '?'} ; erreurs : {len(erreurs)} ; renvois ou citations indéfinis : {len(indef)}")
    for e in erreurs[:10]:
        print("   ", e)
    for k in sorted(indef):
        print("   indéfini :", k)
    n = sum(len(v) for v in boites.values())
    print(f"boîtes trop pleines : {n} (dont {sum(1 for v in boites.values() for w, _ in v if w > 1)} de plus de 1 pt)")
    for f, v in boites.items():
        print(f"   {f:<32} {len(v):>3}  max {max(w for w, _ in v):6.2f} pt  ({v[0][1]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
