# Juge de la rédaction du Tome III (français) : contrôles statiques du tome assemblé, sans compiler.
#
# Pour un dossier assemblé par assembler.py (état tete ou brouillon), lit le maître, les chapitres, les
# annexes, le commun du Tome III et les fichiers de figures chargés, puis rend :
#   - les étiquettes définies deux fois, et les renvois (\ref, \cref, \Cref, \eqref, \autoref, \pageref,
#     \cpageref, \crefrange) vers une étiquette définie nulle part ;
#   - les clés citées (\cite, \textcite, \parencite, \autocite, \footcite, \citeauthor, \citeyear…) absentes
#     des .bib chargés (\addbibresource du préambule commun et de tome3/commun/bibliographie.tex) ;
#   - les \LegendeFigure{Nom} sans \Legende{Nom} et sans \Titre{Nom} dans les fichiers de figures ;
#   - pour chaque environnement figure d'un chapitre : son étiquette, et le nombre de renvois du texte vers
#     elle (une figure jamais appelée est une figure que le texte ne commente pas) ;
#   - par chapitre : présence des environnements origine, enbref, faux ; nombre de \barre.
# Témoin : un renvoi neuf vers une étiquette inexistante, ajouté en mémoire au premier chapitre, doit sortir
# dans la liste des renvois sans cible (--casser le force ; l'outil rend alors le code 1).
#
# Usage : python -I -X utf8 statique.py memoire/essai/juge-redaction-fr-brouillon [--json sortie.json] [--casser]
import argparse
import json
import pathlib
import re
import sys

DEPOT = pathlib.Path(__file__).resolve().parents[4]
MEMOIRE = DEPOT / "memoire"

RE_COMMENT = re.compile(r"(?<!\\)%.*")
RE_LABEL = re.compile(r"\\label\{([^}]+)\}")
RE_REF = re.compile(r"\\(?:ref|cref|Cref|eqref|autoref|pageref|cpageref|Cpageref|labelcref|namecref|nameCref)\*?\{([^}]+)\}")
RE_RANGE = re.compile(r"\\(?:crefrange|Crefrange)\*?\{([^}]+)\}\{([^}]+)\}")
RE_CITE = re.compile(r"\\(?:cite|textcite|parencite|autocite|footcite|citeauthor|citeyear|citetitle|fullcite|Textcite|Parencite|Autocite|citep|citet)\*?(?:\[[^\]]*\]){0,2}\{([^}]+)\}")
RE_BIB = re.compile(r"\\addbibresource\{([^}]+)\}")
RE_BIBKEY = re.compile(r"^\s*@\s*(\w+)\s*\{\s*([^,\s]+)\s*,", re.M)
RE_INPUT = re.compile(r"\\input\{([^}]+)\}")
RE_LEGFIG = re.compile(r"\\LegendeFigure\{([^}]+)\}")
RE_DEF_LEG = re.compile(r"\\Legende\{([^}]+)\}")
RE_DEF_TIT = re.compile(r"\\Titre\{([^}]+)\}")


def sans_commentaires(texte: str) -> str:
    return "\n".join(RE_COMMENT.sub("", l) for l in texte.splitlines())


def resoudre(chemin: str, base: pathlib.Path) -> pathlib.Path:
    c = chemin.replace("\\Racine", str(MEMOIRE)).replace("\\Depot", str(DEPOT))
    p = pathlib.Path(c)
    if not p.is_absolute():
        p = base / p
    if p.suffix not in (".tex", ".bib"):
        p = p.with_suffix(p.suffix + ".tex") if p.suffix else p.with_suffix(".tex")
    return p


def fichiers_du_tome(dossier: pathlib.Path) -> list[pathlib.Path]:
    """Le maître et tout ce qu'il \\input, récursivement (préambule commun exclu de la lecture des renvois)."""
    vus, pile = [], [dossier / "troncons-tome3-fr.tex"]
    while pile:
        f = pile.pop(0)
        if f in vus or not f.exists():
            continue
        vus.append(f)
        texte = sans_commentaires(f.read_text(encoding="utf-8", errors="replace"))
        for m in RE_INPUT.finditer(texte):
            cible = resoudre(m.group(1), dossier)
            if "commun/preambule" in str(cible).replace("\\", "/"):
                continue
            pile.append(cible)
    return vus


def cles_bib(dossier: pathlib.Path) -> dict[str, list[str]]:
    sources = [MEMOIRE / "commun" / "preambule.tex", MEMOIRE / "tome3" / "commun" / "bibliographie.tex"]
    cles: dict[str, list[str]] = {}
    for s in sources:
        for m in RE_BIB.finditer(sans_commentaires(s.read_text(encoding="utf-8"))):
            b = resoudre(m.group(1), dossier)
            for k in RE_BIBKEY.finditer(b.read_text(encoding="utf-8", errors="replace")):
                if k.group(1).lower() in ("comment", "string", "preamble"):
                    continue
                cles.setdefault(k.group(2), []).append(b.name)
    return cles


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("dossier")
    p.add_argument("--json")
    p.add_argument("--casser", action="store_true")
    a = p.parse_args()
    dossier = (DEPOT / a.dossier) if not pathlib.Path(a.dossier).is_absolute() else pathlib.Path(a.dossier)
    fichiers = fichiers_du_tome(dossier)
    textes = {f: sans_commentaires(f.read_text(encoding="utf-8", errors="replace")) for f in fichiers}
    if a.casser:
        premier = next(f for f in fichiers if "chapitres" in str(f))
        textes[premier] += "\n\\cref{t3juge:etiquette-inexistante}\n"
    labels: dict[str, list[str]] = {}
    refs: list[tuple[str, str]] = []
    cites: list[tuple[str, str]] = []
    legfig: list[tuple[str, str]] = []
    def_leg, def_tit = set(), set()
    for f, t in textes.items():
        nom = f.name
        for m in RE_LABEL.finditer(t):
            labels.setdefault(m.group(1).strip(), []).append(nom)
        for m in RE_REF.finditer(t):
            for k in m.group(1).split(","):
                refs.append((nom, k.strip()))
        for m in RE_RANGE.finditer(t):
            refs += [(nom, m.group(1).strip()), (nom, m.group(2).strip())]
        for m in RE_CITE.finditer(t):
            for k in m.group(1).split(","):
                cites.append((nom, k.strip()))
        legfig += [(nom, m.group(1)) for m in RE_LEGFIG.finditer(t)]
        def_leg |= {m.group(1) for m in RE_DEF_LEG.finditer(t)}
        def_tit |= {m.group(1) for m in RE_DEF_TIT.finditer(t)}
    bib = cles_bib(dossier)
    rapport = {
        "dossier": str(dossier),
        "fichiers": [str(f.relative_to(DEPOT)) if DEPOT in f.parents else str(f) for f in fichiers],
        "etiquettes": len(labels),
        "etiquettes_doubles": {k: v for k, v in labels.items() if len(v) > 1},
        "renvois_sans_cible": sorted({(n, k) for n, k in refs if k not in labels}),
        "citations_sans_cle": sorted({(n, k) for n, k in cites if k not in bib}),
        "cles_citees": len({k for _, k in cites}),
        "legendes_sans_definition": sorted({(n, k) for n, k in legfig if k not in def_leg or k not in def_tit}),
        "chapitres": {},
        "figures": [],
    }
    compte_refs: dict[str, int] = {}
    for n, k in refs:
        compte_refs[k] = compte_refs.get(k, 0) + 1
    for f, t in textes.items():
        if f.parent.name not in ("chapitres", "annexes"):
            continue
        rapport["chapitres"][f.name] = {
            "origine": "\\begin{origine}" in t, "enbref": "\\begin{enbref}" in t,
            "faux": "\\begin{faux}" in t, "barres": t.count("\\barre{"),
            "figures": t.count("\\begin{figure}"), "tableaux": t.count("\\begin{table}"),
            "enonces": sum(t.count("\\begin{" + e + "}") for e in
                           ("theoreme", "proposition", "lemme", "corollaire")),
            "demonstrations": t.count("\\begin{proof}"),
            "lignes": t.count("\n"),
        }
        for m in re.finditer(r"\\begin\{figure\*?\}(.*?)\\end\{figure\*?\}", t, re.S):
            corps = m.group(1)
            labs = RE_LABEL.findall(corps)
            leg = RE_LEGFIG.findall(corps)
            rapport["figures"].append({
                "chapitre": f.name, "etiquette": labs[0] if labs else None,
                "legende": leg[0] if leg else ("caption" if "\\caption" in corps else None),
                "renvois": compte_refs.get(labs[0], 0) if labs else 0,
                "hors_style": "\\HorsStyle" in corps,
            })
    sortie = json.dumps(rapport, ensure_ascii=False, indent=1)
    if a.json:
        pathlib.Path(a.json).write_text(sortie, encoding="utf-8")
    print(f"fichiers lus : {len(fichiers)} ; étiquettes : {len(labels)} ; clés citées : {rapport['cles_citees']}")
    print(f"étiquettes doubles : {len(rapport['etiquettes_doubles'])}")
    for k, v in rapport["etiquettes_doubles"].items():
        print(f"   {k} : {v}")
    print(f"renvois sans cible : {len(rapport['renvois_sans_cible'])}")
    for n, k in rapport["renvois_sans_cible"]:
        print(f"   {n} -> {k}")
    print(f"citations sans clé : {len(rapport['citations_sans_cle'])}")
    for n, k in rapport["citations_sans_cle"]:
        print(f"   {n} -> {k}")
    print(f"légendes sans définition : {rapport['legendes_sans_definition']}")
    print("chapitre                 origine enbref faux barres fig tab énoncés preuves lignes")
    for c, v in rapport["chapitres"].items():
        print(f"{c:<24} {v['origine']!s:<7} {v['enbref']!s:<6} {v['faux']!s:<5} {v['barres']:>6} "
              f"{v['figures']:>3} {v['tableaux']:>3} {v['enonces']:>7} {v['demonstrations']:>7} {v['lignes']:>6}")
    sans = [x for x in rapport["figures"] if x["renvois"] == 0]
    print(f"figures : {len(rapport['figures'])} ; jamais appelées par un renvoi : {len(sans)}")
    for x in sans:
        print(f"   {x['chapitre']} : {x['etiquette']} ({x['legende']})")
    sans_lab = [x for x in rapport["figures"] if not x["etiquette"]]
    print(f"figures sans étiquette : {len(sans_lab)}")
    if a.casser:
        return 1 if any(k == "t3juge:etiquette-inexistante" for _, k in rapport["renvois_sans_cible"]) else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
