# Juge final du Tome III : compare, fichier par fichier, les nombres du français et de l'anglais.
# Chemin propre au juge (aucun outil des traducteurs repris) : on ôte les commentaires, on neutralise les
# arguments qui ne s'impriment pas comme des nombres du texte (étiquettes, renvois, citations, fichiers,
# entrées, images, unités), on normalise la virgule décimale française et les séparateurs de milliers, puis
# on compare (1) les multiensembles de nombres, (2) leurs suites dans l'ordre (difflib), (3) les ensembles
# de fichiers cités, de clés citées, de barres et d'étiquettes.
# Usage : python -I -X utf8 parite_nombres.py <racine tome3> [--casser]
#   --casser : change un chiffre dans une copie en mémoire de chaque fichier anglais ; l'outil doit tomber
#              sur chaque fichier (témoin de l'instrument).
import collections
import difflib
import pathlib
import re
import sys

PRINCIPAL = __name__ == "__main__"
casser = "--casser" in sys.argv
if PRINCIPAL:
    racine = pathlib.Path(sys.argv[1])
    FICHIERS = sorted(p.relative_to(racine / "fr") for p in (racine / "fr").rglob("*.tex")
                      if p.parent.name in ("chapitres", "annexes") or p.name == "resume.tex")
else:
    FICHIERS = []


def sans_commentaires(t):
    lignes = []
    for l in t.split("\n"):
        # un % non échappé ouvre un commentaire
        m = re.search(r"(?<!\\)%", l)
        lignes.append(l[:m.start()] if m else l)
    return "\n".join(lignes)


def arg_equilibre(t, i):
    """t[i] == '{' ; rend l'indice après l'accolade fermante appariée."""
    prof = 0
    j = i
    while j < len(t):
        c = t[j]
        if c == "\\":
            j += 2
            continue
        if c == "{":
            prof += 1
        elif c == "}":
            prof -= 1
            if prof == 0:
                return j + 1
        j += 1
    return len(t)


NEUTRES = ["label", "cref", "Cref", "crefrange", "Crefrange", "ref", "eqref", "pageref", "autoref",
           "parencite", "cite", "textcite", "autocite", "citep", "citet", "fullcite", "nocite",
           "fichier", "input", "include", "includegraphics", "FigureHorsStyle", "LegendeFigure", "url",
           "href", "lstinputlisting", "FigureSpectres", "Depot", "Racine", "nameref", "hyperref",
           "begin", "end", "setlength", "arraystretch", "renewcommand"]


def extraire(t, commande):
    """Rend la liste des arguments (premier argument) de \\commande{...}, avec option [..] ignorée."""
    sortie = []
    for m in re.finditer(r"\\" + commande + r"\*?(\[[^\]]*\])?\s*\{", t):
        i = m.end() - 1
        j = arg_equilibre(t, i)
        sortie.append(t[i + 1:j - 1])
    return sortie


def neutraliser(t):
    for c in NEUTRES:
        while True:
            m = re.search(r"\\" + c + r"\*?(\[[^\]]*\])*\s*\{", t)
            if not m:
                break
            i = m.end() - 1
            j = arg_equilibre(t, i)
            t = t[:m.start()] + " " + t[j:]
    # largeurs de colonnes et longueurs : p{0.27\linewidth}, 3pt, 0.5em, \tabcolsep
    t = re.sub(r"\d+(?:[.,]\d+)?\s*\\(?:linewidth|textwidth|columnwidth|hsize|baselineskip)", " ", t)
    t = re.sub(r"\d+(?:[.,]\d+)?\s*(?:pt|em|ex|mm|cm)\b", " ", t)
    # \SI{nombre}{unité} : on garde le nombre, on ôte l'unité
    t = re.sub(r"\\SI\{([^{}]*)\}\{[^{}]*\}", r" \1 ", t)
    return t


def normaliser(t, francais):
    # séparateurs de milliers : \, ~ espaces insécables entre groupes de chiffres
    for _ in range(3):
        t = re.sub(r"(\d)(?:\{\\,\}|\\,|\\thinspace\s*|~|\u202f|\u2009|\u00a0)(\d{3})(?!\d)", r"\1\2", t)
    if francais:
        t = re.sub(r"(\d)\{,\}(\d)", r"\1.\2", t)
        t = re.sub(r"(\d),(\d)", r"\1.\2", t)
    else:
        t = re.sub(r"(\d)\{\.\}(\d)", r"\1.\2", t)
    return t


def nombres(t):
    return re.findall(r"\d+(?:\.\d+)?", t)


def analyse(chemin, francais, casser_ici=False):
    brut = chemin.read_text(encoding="utf-8")
    t = sans_commentaires(brut)
    if casser_ici:
        # change le premier chiffre 7 du texte (hors commentaires) en 8
        k = t.find("7")
        t = t[:k] + "8" + t[k + 1:]
    info = {
        "fichiers": collections.Counter(extraire(t, "fichier")),
        "citations": collections.Counter(k.strip() for a in
                                         extraire(t, "parencite") + extraire(t, "cite") + extraire(t, "textcite")
                                         for k in a.split(",")),
        "barres": len(extraire(t, "barre")),
        "etiquettes": extraire(t, "label"),
        "renvois": collections.Counter(k.strip() for a in extraire(t, "cref") + extraire(t, "Cref")
                                       + extraire(t, "ref") for k in a.split(",")),
    }
    n = nombres(normaliser(neutraliser(t), francais))
    if casser_ici and n:
        # et le dernier chiffre du premier nombre extrait, décalé d'une unité
        x = n[0]
        n[0] = x[:-1] + str((int(x[-1]) + 1) % 10)
    info["nombres"] = n
    return info


# Écarts lus un par un dans les sources et expliqués (aucun n'est un chiffre changé). Clé : fichier ; valeur :
# (nombres seulement FR, nombres seulement EN, fichiers cités seulement FR, seulement EN, raison).
C = collections.Counter
EXPLIQUES = {
    "chapitres/00-introduction.tex": (C(), C(), C({"comme ceci": 1}), C({"like this": 1}),
                                      "exemple de \\fichier{comme ceci} traduit"),
    "chapitres/04-duplication.tex": (C({"0.1": 1}), C({"0": 1, "1": 1}), C(), C(),
                                     "$\\{0,1\\}$ lu comme décimal français par l'outil"),
    "chapitres/06-mimetisme.tex": (C({"0.1": 1}), C({"0": 1, "1": 1}), C(), C(), "$\\{0,1\\}$, idem"),
    "chapitres/07-synthese.tex": (C({"1": 1}), C(), C(), C(), "« le terme d'ordre 1 » rendu « first-order term »"),
    "chapitres/08-codon.tex": (C(), C({"8": 1, "0": 4, "30": 1, "11234960": 1}), C(), C(),
                               "deux gloses anglaises : les commentaires du listing (8, 0) et le message de la "
                               "garde du moteur (couche 0, expert 30, 11 234 960 octets), cité en français puis traduit"),
    "chapitres/09-synonyme.tex": (C({"0.1": 1, "2.3": 1}), C({"0": 1, "1": 1, "2": 1, "3": 1}), C(), C(),
                                  "$\\{0,1,2,3\\}$ lu comme deux décimaux français"),
    "chapitres/11-tropicale.tex": (C(), C(), C({"mesures/pistes/tropicale/figures/coupe-routeur-c12-fr.png": 1}),
                                   C({"mesures/pistes/tropicale/figures/coupe-routeur-c12-en.png": 1}),
                                   "la coupe du routeur dans sa langue"),
    "resume.tex": (C({"1.44": 1, "1.24": 1, "2.00": 1, "0.94": 1, "1.28": 1}),
                   C({"0": 1, "1": 3, "44": 1, "24": 1, "2": 1, "00": 1, "94": 1, "28": 1}), C(), C(),
                   "le fichier anglais porte aussi le Résumé français, dont les virgules ne sont pas lues à "
                   "l'anglaise par l'outil (×1,44, ×1,24, ×2,00, ×0,94, ×1,28)"),
}

ecarts_total = 0
for rel in FICHIERS:
    fr = racine / "fr" / rel
    en = racine / "en" / rel
    if not en.exists():
        print(f"{rel} : ABSENT en anglais")
        ecarts_total += 1
        continue
    a = analyse(fr, True)
    b = analyse(en, False, casser_ici=casser)
    ca, cb = collections.Counter(a["nombres"]), collections.Counter(b["nombres"])
    seul_fr = ca - cb
    seul_en = cb - ca
    ecarts = []
    cle_rel = str(rel).replace("\\", "/")
    xf, xe, ff, fe, raison = EXPLIQUES.get(cle_rel, (C(), C(), C(), C(), ""))
    fich_fr, fich_en = a["fichiers"] - b["fichiers"], b["fichiers"] - a["fichiers"]
    explique = (seul_fr == xf and seul_en == xe and fich_fr == ff and fich_en == fe
                and (seul_fr or seul_en or fich_fr or fich_en))
    if explique:
        print(f"  (expliqué : {raison})")
        a["fichiers"] = b["fichiers"]
    elif seul_fr or seul_en:
        ecarts.append(f"  nombres seulement FR : {dict(seul_fr)}\n  nombres seulement EN : {dict(seul_en)}")
    # ordre : opcodes de difflib sur les suites
    sm = difflib.SequenceMatcher(a=a["nombres"], b=b["nombres"], autojunk=False)
    deplaces = [op for op in sm.get_opcodes() if op[0] != "equal"]
    for cle in ("fichiers", "citations", "renvois"):
        if a[cle] != b[cle]:
            ecarts.append(f"  {cle} : FR-EN {dict(a[cle] - b[cle])} ; EN-FR {dict(b[cle] - a[cle])}")
    if a["barres"] != b["barres"]:
        ecarts.append(f"  barres : FR {a['barres']} EN {b['barres']}")
    if a["etiquettes"] != b["etiquettes"]:
        ecarts.append("  étiquettes : différentes (ordre ou ensemble)")
    etat = "PARITÉ" if not ecarts else "ÉCART"
    print(f"{rel} : {etat} ; {len(a['nombres'])} nombres FR, {len(b['nombres'])} EN ; "
          f"{a['barres']} barres ; {len(a['etiquettes'])} étiquettes ; {sum(a['fichiers'].values())} fichiers ; "
          f"{len(deplaces)} blocs hors d'ordre")
    for e in ecarts:
        print(e)
    for op, i1, i2, j1, j2 in deplaces:
        print(f"    ordre {op} FR[{i1}:{i2}]={a['nombres'][i1:i2]} EN[{j1}:{j2}]={b['nombres'][j1:j2]}")
    ecarts_total += bool(ecarts)
if PRINCIPAL:
    print(f"fichiers en écart : {ecarts_total} sur {len(FICHIERS)}")
    sys.exit(1 if ecarts_total else 0)
