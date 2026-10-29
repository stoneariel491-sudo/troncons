"""Produit les tables des annexes B et C du mémoire depuis le dépôt lui-même.

- memoire/annexes/outils.tex : chaque outil commité sous outils/, rangé par étude, avec la
  première ligne de sa propre description (docstring ou commentaire d'en-tête), citée telle quelle ;
- memoire/annexes/journaux.tex : chaque dossier de journaux commité, son nombre de fichiers et
  son volume ;
- memoire/annexes/figures.tex : chaque graphe du mémoire et les fichiers de données qu'il lit.

Rien n'est écrit à la main : tout vient de git (git ls-tree et git cat-file au commit DEPOT_PUBLIE
pour les deux premières tables) et des fichiers. Bibliothèque standard seule.
Usage : python -I -X utf8 memoire/outils/annexes.py
"""
import re
import subprocess
from collections import OrderedDict
from pathlib import Path

DEPOT = Path(__file__).resolve().parents[2]
SORTIE = DEPOT / "memoire" / "annexes"

# Le commit dont les tables des outils et des journaux décrivent le dépôt. Le Tome I décrit le dépôt
# tel qu'il était à sa publication (2026-10-15) ; ses annexes B et C ne suivent pas le dépôt qui a
# grandi depuis. b8af154 (2026-10-15 15:51, « Lot F : note pour le mémoire… ») est le premier commit
# dont l'arbre redonne les deux tables commitées (outils.tex de 8d67046, journaux.tex de 9d20a81,
# 96 outils, 15 dossiers aux mêmes nombres de fichiers) ; l'arbre est le même sous outils/,
# fondations/journaux/, decisions/journaux/ et mesures/ jusqu'à 6d00f3d, et diffère dès d68beaf
# (mesures/moteur/R/r1, 122 fichiers au lieu de 118).
# Changé le 2026-10-29 : avant, l'outil comptait par git ls-files et lisait l'arbre de travail
# (contenus, os.stat) ; relancé ce jour-là, il réécrivait outils.tex (452 outils au lieu de 96) et
# journaux.tex (8 lignes de mesures/), donc les PDF du Tome I.
DEPOT_PUBLIE = "b8af154"

# Le volume des journaux : la table commitée a été prise par os.stat sur le disque du 2026-10-15, où
# un fichier compte les octets que son écrivain y a mis, et non ceux du blob (core.autocrlf=true :
# git range les fins de ligne en LF). Ce disque n'est pas dans git. La règle qui redonne les 15
# volumes commités (au centième de Mo publié) : un fichier texte compte un octet de plus par fin de
# ligne LF (la taille qu'il a une fois sorti par git en CRLF, ou écrit en mode texte sous Windows),
# sauf sous les dossiers ci-dessous, dont les fichiers étaient écrits en LF par les outils du
# moteur et comptent la taille de leur blob. Éprouvé le 2026-10-29 : tout au blob, 7 volumes sur 15
# changent ; tout en CRLF, mesures/moteur/ passe de 0,88 à 0,91 Mo ; avec la règle, 0 écart.
JOURNAUX_EN_LF = ("mesures/moteur/",)

SOURCES = (".py", ".rs", ".cu", ".cpp", ".c", ".h", ".wgsl", ".hlsl", ".sh", ".ps1", ".bat", ".toml")

# Rangement par étude, d'après le chemin (premier motif qui correspond).
ETUDES = [
    (r"^outils/banc/", ("01 machine", "01 machine")),
    (r"^outils/quant", ("02 quantification", "02 quantization")),
    (r"^outils/03-entropie/", ("03 entropie", "03 entropy")),
    (r"^outils/chargement", ("04 chargement", "04 loading")),
    (r"^outils/(05-sparsite/|sparsite)", ("05 sparsité", "05 sparsity")),
    (r"^outils/(modeles|inventaire_modeles)", ("06 modèles", "06 models")),
    (r"^outils/creer-disque", ("06 modèles", "06 models")),
    (r"^outils/07-synthese/", ("07 synthèse", "07 synthesis")),
    (r"^outils/(decisions|arbitre)/", ("décisions", "decisions")),
    (r"^outils/(gptoss|gptoss-routage)", ("mesures gpt-oss", "gpt-oss measurements")),
]


def git_arbre(commit, *prefixes):
    """[(chemin, objet, taille du blob)] des fichiers suivis sous les préfixes, au commit donné."""
    sortie = subprocess.run(["git", "-C", str(DEPOT), "ls-tree", "-r", "-l", "-z", commit, "--", *prefixes],
                            capture_output=True, check=True).stdout
    res = []
    for e in sortie.split(b"\0"):
        if not e:
            continue
        meta, chemin = e.split(b"\t", 1)
        _, genre, objet, taille = meta.split()
        if genre == b"blob":
            res.append((chemin.decode("utf-8"), objet.decode("ascii"), int(taille)))
    return res


def git_contenus(objets):
    """{objet: octets} par un seul git cat-file --batch."""
    objets = list(dict.fromkeys(objets))
    entree = "".join(o + "\n" for o in objets).encode("ascii")
    brut = subprocess.run(["git", "-C", str(DEPOT), "cat-file", "--batch"], input=entree,
                          capture_output=True, check=True).stdout
    res, i = {}, 0
    for o in objets:
        fin = brut.index(b"\n", i)
        tete = brut[i:fin].split()
        if len(tete) != 3 or tete[0].decode("ascii") != o:
            raise SystemExit(f"git cat-file : réponse inattendue pour {o} : {brut[i:fin]!r}")
        n = int(tete[2])
        res[o] = brut[fin + 1:fin + 1 + n]
        i = fin + 1 + n + 1
    return res


def taille_crlf(octets):
    """Taille d'un blob sorti par git sous core.autocrlf=true (règles « auto » de convert.c) :
    un octet de plus par LF seul, sauf pour un fichier binaire (NUL, CR seul, trop de caractères de
    contrôle) ou qui porte déjà des CRLF."""
    crlf = octets.count(b"\r\n")
    cr_seul = octets.count(b"\r") - crlf
    lf_seul = octets.count(b"\n") - crlf
    if cr_seul or crlf or b"\0" in octets or not lf_seul:
        return len(octets)
    imprimables = non_imprimables = 0
    dernier = len(octets) - 1
    for k, c in enumerate(octets):
        if c in (10, 13):
            continue
        if c == 127 or (c < 32 and c not in (8, 9, 12, 27) and not (c == 26 and k == dernier)):
            non_imprimables += 1
        else:
            imprimables += 1
    if (imprimables >> 7) < non_imprimables:
        return len(octets)
    return len(octets) + lf_seul


def echapper(t):
    rep = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
           "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(rep.get(c, c) for c in t)


def texte_du_blob(octets):
    """Le contenu d'un objet git en texte, fins de ligne normalisées en LF."""
    return octets.decode("utf-8-sig", errors="replace").replace("\r\n", "\n")


def description(chemin):
    """Première ligne non vide de la description propre du fichier, lu sous DEPOT. Gardée telle
    quelle pour memoire/outils/tome3_annexes.py, qui remplace DEPOT par son commit HEAD."""
    try:
        texte = (DEPOT / chemin).read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""
    return description_de(chemin, texte)


def description_de(chemin, texte):
    """Première ligne non vide de la description propre d'un fichier, depuis son texte."""
    lignes = texte.splitlines()
    if chemin.endswith(".py"):
        m = re.search(r'^\s*(?:#![^\n]*\n)?(?:#[^\n]*\n)*\s*[rRbBuU]?("""|\'\'\')(.*?)\1', texte, re.S)
        if m:
            # Premier paragraphe de la docstring, lignes jointes.
            paragraphe = []
            for l in m.group(2).strip().splitlines():
                if not l.strip():
                    break
                paragraphe.append(l.strip())
            if paragraphe:
                return " ".join(paragraphe).replace("`", "")
    marques = ("//!", "///", "//", "#", "::", "REM ", "rem ", "--")
    morceaux = []
    for l in lignes[:40]:
        s = l.strip()
        if s.startswith("#!") or s.startswith("@echo") or s.startswith("[") or s.startswith("<#"):
            continue
        marque = next((m for m in marques if s.startswith(m)), None)
        if marque is None and s.startswith("/*"):
            marque = "/*"
        if marque is None:
            if morceaux:
                break
            continue
        t = s[len(marque):].strip(" -=*/")
        if not t:
            if morceaux:
                break
            continue
        if t.lower().startswith(("encoding", "-*-", "requires")):
            continue
        morceaux.append(t)
    return " ".join(morceaux).replace("`", "")


def couper(d, n=190):
    """Coupe à la fin d'une phrase si possible, sinon à un mot, avant n caractères."""
    if len(d) <= n:
        return d
    tete = d[:n]
    fin = max(tete.rfind(". "), tete.rfind(" ; "), tete.rfind(" : "))
    if fin > n // 2:
        return tete[:fin + 1].rstrip(" ;:") + " …"
    return tete.rsplit(" ", 1)[0] + " …"


def etude(chemin):
    for motif, nom in ETUDES:
        if re.search(motif, chemin):
            return nom
    return ("divers", "miscellaneous")


def ecrire(nom, contenu):
    SORTIE.mkdir(parents=True, exist_ok=True)
    (SORTIE / nom).write_text(contenu, encoding="utf-8", newline="\n")
    return nom


def outils():
    retenus = [(c, o) for c, o, _ in git_arbre(DEPOT_PUBLIE, "outils")
               if c.endswith(SOURCES) and "__pycache__" not in c]
    contenus = git_contenus(o for _, o in retenus)
    groupes = OrderedDict()
    for c, o in sorted(retenus):
        groupes.setdefault(etude(c), []).append((c, o))
    ordre = sorted(groupes, key=lambda g: g[0])
    lignes = ["% Engendré par memoire/outils/annexes.py : ne pas modifier à la main.",
              r"\begingroup\small", r"\begin{longtable}{@{}p{0.43\linewidth}p{0.53\linewidth}@{}}", r"\toprule",
              r"\EF{Tool}{Outil} & \EF{Its own description (first line, quoted)}{Sa propre description (première ligne, citée)} \\",
              r"\midrule", r"\endhead"]
    total = 0
    for g in ordre:
        lignes.append(r"\multicolumn{2}{@{}l}{\textsf{\bfseries\EF{%s}{%s}}} \\" % (g[1], g[0]))
        for c, o in groupes[g]:
            d = couper(description_de(c, texte_du_blob(contenus[o])))
            lignes.append(r"\fichier{%s} & {\footnotesize %s} \\" % (c, echapper(d) if d else r"\textemdash"))
            total += 1
    lignes += [r"\bottomrule", r"\end{longtable}", r"\endgroup", ""]
    lignes.insert(1, "%% %d outils" % total)
    return ecrire("outils.tex", "\n".join(lignes))


def journaux():
    racines = ["fondations/journaux", "decisions/journaux", "mesures"]
    dossiers = OrderedDict()
    for r in racines:
        fichiers = git_arbre(DEPOT_PUBLIE, r)
        contenus = git_contenus(o for c, o, _ in fichiers if not c.startswith(JOURNAUX_EN_LF))
        for c, o, taille_blob in fichiers:
            p = Path(c)
            # Dossier de premier niveau sous la racine (ex. fondations/journaux/01-machine).
            profondeur = len(Path(r).parts) + 1
            cle = "/".join(p.parts[:profondeur]) if len(p.parts) > profondeur else p.parent.as_posix()
            taille = taille_blob if c.startswith(JOURNAUX_EN_LF) else taille_crlf(contenus[o])
            n, v = dossiers.get(cle, (0, 0))
            dossiers[cle] = (n + 1, v + taille)
    lignes = ["% Engendré par memoire/outils/annexes.py : ne pas modifier à la main.",
              r"\begingroup\small", r"\begin{longtable}{@{}p{0.6\linewidth}rr@{}}", r"\toprule",
              r"\EF{Log folder}{Dossier de journaux} & \EF{Files}{Fichiers} & \EF{Size (MB)}{Volume (Mo)} \\",
              r"\midrule", r"\endhead"]
    for cle in sorted(dossiers):
        n, v = dossiers[cle]
        lignes.append(r"\fichier{%s} & \num{%d} & \num{%.2f} \\" % (cle + "/", n, v / 1e6))
    lignes += [r"\bottomrule", r"\end{longtable}", r"\endgroup", ""]
    return ecrire("journaux.tex", "\n".join(lignes))


def figures():
    # Lit l'arbre de travail, et non DEPOT_PUBLIE : cette table décrit les graphes que la construction
    # compile (memoire/figures/graphes/), qui sont ceux de l'arbre ; elle redonne au bit la table
    # commitée (9d20a81) le 2026-10-29.
    base = DEPOT / "memoire" / "figures" / "graphes"
    macros = {r"\Donnees": "memoire/figures/donnees", r"\CsvQuant": "fondations/journaux/02-quantification/csv",
              r"\CsvMachine": "fondations/journaux/01-machine", r"\CsvSynthese": "fondations/journaux/07-synthese/csv",
              r"\CsvDecisions": "decisions/journaux/csv", r"\Depot": "."}
    lignes = ["% Engendré par memoire/outils/annexes.py : ne pas modifier à la main.",
              r"\begingroup\small", r"\begin{longtable}{@{}p{0.37\linewidth}p{0.59\linewidth}@{}}", r"\toprule",
              r"\EF{Graph (command)}{Graphe (commande)} & \EF{Data files it reads}{Fichiers de données qu'il lit} \\",
              r"\midrule", r"\endhead"]
    for f in sorted(base.glob("*.tex")):
        texte = f.read_text(encoding="utf-8")
        blocs = re.split(r"\\newcommand\{(\\[A-Za-z]+)\}", texte)
        for i in range(1, len(blocs), 2):
            nom, corps = blocs[i], blocs[i + 1]
            fichiers = []
            for m in re.finditer(r"\{((?:\\[A-Za-z]+)(?:/[^{}\s]+)+\.(?:csv|dat|tsv))\}", corps):
                chemin = m.group(1)
                for k, v in sorted(macros.items(), key=lambda kv: -len(kv[0])):
                    if chemin.startswith(k + "/"):
                        chemin = v + chemin[len(k):]
                        break
                chemin = chemin.lstrip("./")
                if chemin not in fichiers:
                    fichiers.append(chemin)
            if not fichiers:
                continue
            cellule = r" \newline ".join(r"\fichier{%s}" % c for c in fichiers)
            lignes.append(r"\texttt{\textbackslash %s} & %s \\" % (nom[1:], cellule))
    lignes += [r"\bottomrule", r"\end{longtable}", r"\endgroup", ""]
    return ecrire("figures.tex", "\n".join(lignes))


if __name__ == "__main__":
    for f in (outils, journaux, figures):
        print(f())
