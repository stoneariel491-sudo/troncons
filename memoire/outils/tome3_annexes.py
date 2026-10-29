"""Produit les tables des annexes du Tome III depuis le commit DEPOT_PUBLIE du dépôt (git ls-tree, git cat-file, git log).

- memoire/tome3/annexes/outils-tome3.tex : chaque outil commité de la quête du génome, du mimétisme, des pistes,
  des juges des figures et du mémoire du Tome III, rangé par chapitre, avec la première ligne de sa propre
  description, citée telle quelle, et son nombre de lignes ;
- memoire/tome3/annexes/journaux-tome3.tex : chaque dossier de journaux et de CSV commité sous mesures/genome/,
  mesures/mimetisme/, mesures/pistes/, mesures/disque/placement/juge/ et outils/genome/tome3/ (outils exclus),
  son nombre de fichiers et son volume ;
- memoire/tome3/annexes/seuils-tome3.tex : chaque fichier de seuils, de critères ou d'amendement déclaré avant
  une mesure, avec le commit qui l'a créé, son heure (locale) et le nombre de commits qui l'ont touché ; le
  second tirage de P3 (fichiers 07*), en travail dans une autre session, n'y est pas (réserve R6) ;
  Les outils et les journaux du second tirage de P3 ne sont pas non plus dans les deux premières tables (R6) ;
- memoire/tome3/annexes/figures-tome3.tex : chaque figure au style du Tome III (\\Source{Nom}{…} des fichiers
  memoire/figures/tome3/*-figures.tex) et les fichiers de données que sa ligne « Données » cite.

Tout se lit au commit DEPOT_PUBLIE, jamais dans l'arbre de travail (corrigé le 2026-10-29, grave G3 de
memoire/tome3/JUGEMENT-final.md) : la liste des fichiers par git ls-tree -r -l, leur volume par la taille
de l'objet git (donc sans dépendre des fins de ligne de la copie, core.autocrlf), leurs lignes et leur
description par le contenu de l'objet (git cat-file --batch). Avant, l'outil comptait les lignes et les octets
de la copie de travail : une modification non commitée d'une autre session, ou une copie en CRLF, changeait les
annexes B et C sans changer le commit. Il a d'abord lu HEAD, avec une garde qui refusait de tourner (code 1)
si un fichier compté différait du commit dans l'arbre de travail ; figé le même jour au commit de publication
du tome (DEPOT_PUBLIE, qui redonne les quatre tables au bit), il ne dépend plus ni de l'arbre de travail ni des
commits postérieurs, et la garde est retirée.

Témoin : tout fichier cité par une ligne « Données » (chemin complet, motifs * et {a,b} permis) existe au
commit DEPOT_PUBLIE ; sinon l'outil sort en erreur. Cassure : --casser ajoute à la première figure un fichier qui
n'existe pas, et l'outil doit alors tomber.

Rien n'est écrit à la main. Bibliothèque standard seule.
Usage : python -I -X utf8 memoire/outils/tome3_annexes.py [--casser]
"""
import fnmatch
import io
import re
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import annexes  # noqa: E402
from annexes import couper, echapper  # noqa: E402

DEPOT = Path(__file__).resolve().parents[2]
SORTIE = DEPOT / "memoire" / "tome3" / "annexes"
SOURCES = (".py", ".rs", ".cu", ".cuh", ".ps1", ".bat", ".sh")
ENTETE = "% Engendré par memoire/outils/tome3_annexes.py : ne pas modifier à la main."

# Rangement des outils par chapitre, d'après le chemin (premier motif qui correspond) : (français, anglais).
CHAPITRES = [
    (r"^outils/genome/eclaireur/", ("Ch.~\\ref{t3que:ch} et~\\ref{t3ecl:ch} : la question, l'éclaireur", "Ch.~\\ref{t3que:ch} and~\\ref{t3ecl:ch}: the question, the scout")),
    (r"^outils/genome/recette", ("Ch.~\\ref{t3gen:ch} : le génome des poids (la recette)", "Ch.~\\ref{t3gen:ch}: the genome of the weights (the recipe)")),
    (r"^outils/genome/duplication/", ("Ch.~\\ref{t3dup:ch} : la duplication de gènes", "Ch.~\\ref{t3dup:ch}: gene duplication")),
    (r"^outils/genome/predictif-elagage/", ("Ch.~\\ref{t3pre:ch} : codage prédictif et élagage", "Ch.~\\ref{t3pre:ch}: predictive coding and pruning")),
    (r"^outils/mimetisme/P[1-6]/juge/", ("Ch.~\\ref{t3mim:ch} : le mimétisme, les juges", "Ch.~\\ref{t3mim:ch}: mimicry, the judges")),
    (r"^outils/mimetisme/P[1-6]/", ("Ch.~\\ref{t3mim:ch} : le mimétisme, les six pistes", "Ch.~\\ref{t3mim:ch}: mimicry, the six leads")),
    (r"^outils/mimetisme/", ("Ch.~\\ref{t3mim:ch} : le mimétisme, les éclaireurs de domaine", "Ch.~\\ref{t3mim:ch}: mimicry, the domain scouts")),
    (r"^outils/genome/synthese/", ("Ch.~\\ref{t3syn:ch} : la synthèse de la ronde", "Ch.~\\ref{t3syn:ch}: the synthesis of the round")),
    (r"^outils/genome/construction/codon/", ("Ch.~\\ref{t3cod:ch} : le codon (lot A)", "Ch.~\\ref{t3cod:ch}: the codon (lot A)")),
    (r"^outils/genome/synonyme/", ("Ch.~\\ref{t3sno:ch} : le génome synonyme (lot B)", "Ch.~\\ref{t3sno:ch}: the synonymous genome (lot B)")),
    (r"^outils/genome/construction/juge/", ("Ch.~\\ref{t3jug:ch} : le juge de la construction", "Ch.~\\ref{t3jug:ch}: the judge of the construction")),
    (r"^outils/pistes/tropicale/", ("Ch.~\\ref{t3tro:ch} : la géométrie tropicale", "Ch.~\\ref{t3tro:ch}: tropical geometry")),
    (r"^outils/pistes/spectres/", ("Ch.~\\ref{t3spe:ch} : les spectres", "Ch.~\\ref{t3spe:ch}: the spectra")),
    (r"^outils/genome/tome3/", ("Les figures : espaces latents et juges des figures", "Figures: latent spaces and figure judges")),
    (r"^memoire/outils/tome3_", ("Le mémoire du Tome~III", "The thesis, Volume~III")),
]

# Les fichiers de seuils, critères et amendements déclarés avant une mesure.
MOTIF_SEUIL = re.compile(r"(seuil|critere|declare)[^/]*\.(md|json)$")
RACINES_SEUILS = ("mesures/genome", "mesures/mimetisme", "mesures/pistes", "mesures/disque/placement/juge",
                  "genome/mimetisme", "genome/pistes")
# Le second tirage de P3, en travail dans une autre session (réserve R6) : ni ses seuils, ni ses outils, ni ses
# journaux n'entrent dans les tables du tome.
EXCLUS_SEUILS = re.compile(r"^mesures/mimetisme/P3/07")
EXCLUS_R6 = re.compile(r"P3/(07|p3_second_tirage|second-tirage/)")

# Le commit dont le Tome III décrit le dépôt (figé le 2026-10-29, comme annexes.py, tome2_format.py et
# tome2_annexes.py) : lire HEAD faisait dépendre les annexes de chaque commit postérieur au tome, et la garde
# « arbre propre » refusait de tourner dès qu'une autre session laissait un fichier compté non commité.
# Lu à ce commit, l'arbre de travail n'entre plus dans les tables ; la garde est devenue sans objet.
DEPOT_PUBLIE = "4b071d0"
RACINES_JOURNAUX = ("mesures/genome", "mesures/mimetisme", "mesures/pistes", "mesures/disque/placement/juge",
                    "outils/genome/tome3")


def ecrire(nom, contenu):
    SORTIE.mkdir(parents=True, exist_ok=True)
    (SORTIE / nom).write_text(contenu, encoding="utf-8", newline="\n")
    return nom


def git_octets(*args, entree=None):
    return subprocess.run(["git", "-C", str(DEPOT), *args], input=entree, capture_output=True, check=True).stdout


# Le commit lu : {chemin: (objet, taille en octets de l'objet)}, rempli une fois par arbre_head().
ARBRE = {}
# Contenus des objets déjà lus : {chemin: octets}.
CONTENUS = {}


def arbre_head():
    """Tous les fichiers du commit DEPOT_PUBLIE (git ls-tree -r -l -z) : leur objet et sa taille."""
    if not ARBRE:
        for entree in git_octets("ls-tree", "-r", "-l", "-z", DEPOT_PUBLIE).split(b"\0"):
            if not entree:
                continue
            meta, chemin = entree.split(b"\t", 1)
            _, genre, objet, taille = meta.split()
            if genre == b"blob":
                ARBRE[chemin.decode("utf-8")] = (objet.decode("ascii"), int(taille))
    return ARBRE


def fichiers_head(*prefixes):
    """Les chemins du commit DEPOT_PUBLIE sous ces dossiers, comme git ls-files les donnerait pour ce commit."""
    return sorted(c for c in arbre_head() if any(c == p or c.startswith(p.rstrip("/") + "/") for p in prefixes))


def charger(chemins):
    """Lit d'un coup (git cat-file --batch) le contenu au commit DEPOT_PUBLIE des chemins pas encore lus."""
    a_lire = [c for c in chemins if c not in CONTENUS]
    if not a_lire:
        return
    sortie = git_octets("cat-file", "--batch", entree="".join(arbre_head()[c][0] + "\n" for c in a_lire).encode())
    i = 0
    for c in a_lire:
        fin = sortie.index(b"\n", i)
        objet, genre, taille = sortie[i:fin].split()
        assert objet.decode() == arbre_head()[c][0] and genre == b"blob", (c, sortie[i:fin])
        debut = fin + 1
        CONTENUS[c] = sortie[debut:debut + int(taille)]
        i = debut + int(taille) + 1


def lignes_de(chemin):
    """Nombre de lignes du fichier au commit DEPOT_PUBLIE (fins de ligne universelles, comme une lecture en texte)."""
    charger([chemin])
    return sum(1 for _ in io.StringIO(CONTENUS[chemin].decode("utf-8", errors="replace"), newline=None))


class _FichierDuCommit:
    def __init__(self, chemin):
        self.chemin = chemin

    def read_text(self, encoding="utf-8", errors="strict"):
        if self.chemin not in arbre_head():
            raise OSError(self.chemin)
        charger([self.chemin])
        return CONTENUS[self.chemin].decode(encoding, errors)


class _Commit:
    """Pris par annexes.description à la place du dossier du dépôt : (_Commit() / chemin).read_text() rend le
    contenu du fichier au commit DEPOT_PUBLIE. La description est ainsi celle du commit, par le code même du Tome I."""
    def __truediv__(self, chemin):
        return _FichierDuCommit(str(chemin))


annexes.DEPOT = _Commit()
description = annexes.description


def chapitre(chemin):
    for i, (motif, nom) in enumerate(CHAPITRES):
        if re.search(motif, chemin):
            return i, nom
    return None


def liste_outils():
    """Les outils comptés par l'annexe B : sources du commit DEPOT_PUBLIE, rangées par un chapitre."""
    return [c for c in fichiers_head("outils/genome", "outils/mimetisme", "outils/pistes", "memoire/outils")
            if c.endswith(SOURCES) and "__pycache__" not in c and not EXCLUS_R6.search(c)
            and chapitre(c) is not None]


def liste_journaux():
    """Les fichiers de journaux comptés par l'annexe C (au moins trois niveaux de dossier), au commit DEPOT_PUBLIE."""
    return [c for c in fichiers_head(*RACINES_JOURNAUX)
            if "__pycache__" not in Path(c).parts and not c.endswith(SOURCES) and not EXCLUS_R6.search(c)
            and len(Path(c).parts) >= 4]


def liste_figures():
    """Les fichiers de légendes des figures au style du Tome III, au commit DEPOT_PUBLIE."""
    return [c for c in fichiers_head("memoire/figures/tome3") if re.fullmatch(r"memoire/figures/tome3/[^/]*-figures\.tex", c)]


def outils():
    groupes = OrderedDict()
    for c in liste_outils():
        r = chapitre(c)
        groupes.setdefault(r, []).append(c)
    lignes = [ENTETE, r"\begingroup\small",
              r"\begin{longtable}{@{}p{0.40\linewidth}p{0.47\linewidth}r@{}}",
              r"\caption[\EF{The committed tools of Volume~III}{Les outils commités du Tome~III}]"
              r"{\EF{The committed tools of Volume~III, by chapter, each with the first line of its own description}"
              r"{Les outils commités du Tome~III, par chapitre, chacun avec la première ligne de sa propre description}"
              r" (\fichier{memoire/outils/tome3_annexes.py}).}\label{t3ann:tab:outils}\\",
              r"\toprule",
              r"\EF{Tool}{Outil} & \EF{Its own description (first line, quoted as written, in French)}"
              r"{Sa propre description (première ligne, citée)} & \EF{Lines}{Lignes} \\",
              r"\midrule", r"\endfirsthead", r"\toprule",
              r"\EF{Tool}{Outil} & \EF{Its own description}{Sa propre description} & \EF{Lines}{Lignes} \\",
              r"\midrule", r"\endhead"]
    total, total_lignes = 0, 0
    for g in sorted(groupes):
        lignes.append(r"\multicolumn{3}{@{}l}{\textsf{\bfseries\EF{%s}{%s}}} \\" % (g[1][1], g[1][0]))
        for c in groupes[g]:
            d = couper(description(c), 160)
            n = lignes_de(c)
            lignes.append(r"\fichier{%s} & {\footnotesize %s} & \num{%d} \\"
                          % (c, echapper(d) if d else r"\textemdash", n))
            total += 1
            total_lignes += n
    lignes += [r"\midrule",
               r"\EF{Total}{Total} & \EF{%d tools}{%d outils} & \num{%d} \\" % (total, total, total_lignes),
               r"\bottomrule", r"\end{longtable}", r"\endgroup", ""]
    return ecrire("outils-tome3.tex", "\n".join(lignes)), total


def journaux():
    dossiers = OrderedDict()
    for c in liste_journaux():
        parties = Path(c).parts
        if len(parties) >= 5:
            cle = "/".join(parties[:4]) + "/"
        elif len(parties) == 4:
            cle = "/".join(parties[:3]) + "/"
        else:
            continue
        taille = arbre_head()[c][1]  # taille de l'objet git : celle du commit, quelles que soient les fins de ligne
        n, o = dossiers.get(cle, (0, 0))
        dossiers[cle] = (n + 1, o + taille)
    lignes = [ENTETE, r"\begingroup\small", r"\begin{longtable}{@{}p{0.62\linewidth}rr@{}}",
              r"\caption[\EF{The log folders of Volume~III}{Les dossiers de journaux du Tome~III}]"
              r"{\EF{The committed log folders of Volume~III (logs, CSV, notes; tools excluded)}"
              r"{Les dossiers de journaux commités du Tome~III (journaux, CSV, notes ; outils exclus)}"
              r" (\fichier{memoire/outils/tome3_annexes.py}).}\label{t3ann:tab:journaux}\\",
              r"\toprule",
              r"\EF{Folder}{Dossier} & \EF{Files}{Fichiers} & \EF{Size (MB)}{Volume (Mo)} \\",
              r"\midrule", r"\endfirsthead", r"\toprule",
              r"\EF{Folder}{Dossier} & \EF{Files}{Fichiers} & \EF{Size (MB)}{Volume (Mo)} \\",
              r"\midrule", r"\endhead"]
    nt, ot = 0, 0
    for cle in sorted(dossiers):
        n, o = dossiers[cle]
        nt += n
        ot += o
        lignes.append(r"\fichier{%s} & \num{%d} & \num{%.2f} \\" % (cle, n, o / 1e6))
    lignes += [r"\midrule", r"\EF{Total}{Total} & \num{%d} & \num{%.2f} \\" % (nt, ot / 1e6),
               r"\bottomrule", r"\end{longtable}", r"\endgroup", ""]
    return ecrire("journaux-tome3.tex", "\n".join(lignes)), len(dossiers)


def git_log(fichier, *options):
    return subprocess.run(["git", "-C", str(DEPOT), "log", *options, DEPOT_PUBLIE, "--", fichier],
                          capture_output=True, text=True, encoding="utf-8", check=True).stdout


def seuils():
    fichiers = [c for c in fichiers_head(*RACINES_SEUILS)
                if MOTIF_SEUIL.search(c) and not EXCLUS_SEUILS.search(c)]
    lignes = [ENTETE, r"\begingroup\small", r"\begin{longtable}{@{}p{0.56\linewidth}lr@{}}",
              r"\caption[\EF{The declared thresholds of Volume~III, dated by git}{Les seuils déclarés du Tome~III,"
              r" datés par git}]{\EF{The files of thresholds, criteria and amendments declared before a measurement,"
              r" with the commit that created them (local time) and the number of commits that touched them}"
              r"{Les fichiers de seuils, de critères et d'amendements déclarés avant une mesure, avec le commit qui les"
              r" a créés (heure locale) et le nombre de commits qui les ont touchés} (\fichier{memoire/outils/"
              r"tome3_annexes.py}).}\label{t3ann:tab:seuils-dates}\\",
              r"\toprule",
              r"\EF{Declared before}{Déclaré avant} & \EF{Created by commit}{Créé par le commit} & \EF{Commits}{Commits} \\",
              r"\midrule", r"\endfirsthead", r"\toprule",
              r"\EF{Declared before}{Déclaré avant} & \EF{Created by commit}{Créé par le commit} & \EF{Commits}{Commits} \\",
              r"\midrule", r"\endhead"]
    lus = []
    for c in sorted(fichiers):
        cree = git_log(c, "--diff-filter=A", "--format=%h %ci").strip().splitlines()
        tous = git_log(c, "--format=%h").strip().splitlines()
        if not cree:
            continue
        h, date, heure = cree[-1].split()[:3]
        lus.append((date + " " + heure, c, h, len(tous)))
    # Rangés par heure de création : l'ordre des déclarations est celui de la quête.
    for quand, c, h, n in sorted(lus):
        lignes.append(r"\fichier{%s} & \texttt{%s}, %s & \num{%d} \\" % (c, h, quand[:16], n))
    lignes += [r"\bottomrule", r"\end{longtable}", r"\endgroup", ""]
    return ecrire("seuils-tome3.tex", "\n".join(lignes)), len(lus)


def accolades(motif):
    """Développe les motifs {a,b} (un seul niveau), comme le fait le shell."""
    m = re.search(r"\{([^{}]*)\}", motif)
    if not m:
        return [motif]
    return [x for v in m.group(1).split(",") for x in accolades(motif[:m.start()] + v + motif[m.end():])]


def argument(texte, debut):
    """Le groupe {…} qui commence à texte[debut] (accolades équilibrées) : (contenu, fin)."""
    assert texte[debut] == "{"
    profondeur = 0
    for i in range(debut, len(texte)):
        if texte[i] == "{":
            profondeur += 1
        elif texte[i] == "}":
            profondeur -= 1
            if profondeur == 0:
                return texte[debut + 1:i], i + 1
    raise ValueError("accolade non fermée")


def figures(casser=False):
    connus = set(fichiers_head("mesures", "memoire", "genome", "outils"))
    entrees = []
    for f in liste_figures():
        charger([f])
        texte = CONTENUS[f].decode("utf-8")
        for m in re.finditer(r"\\Source\{([A-Za-z]+)\}", texte):
            contenu, _ = argument(texte, m.end())
            cites = []
            for brut in re.findall(r"\\fichier\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}", contenu):
                cites.append(brut.replace(r"\_", "_").replace(r"\{", "{").replace(r"\}", "}"))
            entrees.append((Path(f).name, m.group(1), cites))
    if casser and entrees:
        nom, fig, cites = entrees[0]
        entrees[0] = (nom, fig, cites + ["mesures/genome/n-existe-pas.csv"])
    manquants = []
    lignes = [ENTETE, r"\begingroup\small", r"\begin{longtable}{@{}p{0.28\linewidth}p{0.68\linewidth}@{}}",
              r"\caption[\EF{Each figure and the files it reads}{Chaque figure et les fichiers qu'elle lit}]"
              r"{\EF{Each figure in the style of Volume~III (its \texttt{\textbackslash Source}) and the data files"
              r" its ``Data'' line cites}{Chaque figure au style du Tome~III (son \texttt{\textbackslash Source}) et"
              r" les fichiers de données que cite sa ligne « Données »} (\fichier{memoire/outils/tome3_annexes.py} ;"
              r" un nom sans dossier se lit dans le dossier du précédent).}\label{t3ann:tab:figures}\\",
              r"\toprule",
              r"\EF{Figure (file, name)}{Figure (fichier, nom)} & \EF{Data}{Données} \\",
              r"\midrule", r"\endfirsthead", r"\toprule",
              r"\EF{Figure (file, name)}{Figure (fichier, nom)} & \EF{Data}{Données} \\",
              r"\midrule", r"\endhead"]
    for nom, fig, cites in entrees:
        for c in cites:
            if "/" not in c or not c.startswith(("mesures/", "memoire/", "genome/", "outils/")):
                continue  # nom relatif au précédent, ou dossier hors des racines : non vérifiable seul
            motifs = accolades(c)
            for mo in motifs:
                if mo.endswith("/"):
                    ok = any(k.startswith(mo) for k in connus)
                elif "*" in mo or "?" in mo:
                    ok = any(fnmatch.fnmatchcase(k, mo) for k in connus)
                else:
                    ok = mo in connus
                if not ok:
                    manquants.append((fig, mo))
        donnees = ", ".join(r"\fichier{%s}" % c for c in cites) if cites else r"\textemdash"
        lignes.append(r"\texttt{%s}, \texttt{%s} & %s \\" % (echapper(nom.replace("-figures.tex", "")), fig, donnees))
    lignes += [r"\bottomrule", r"\end{longtable}", r"\endgroup", ""]
    if manquants:
        for fig, mo in manquants:
            print(f"ÉCHEC : la figure {fig} cite {mo}, absent de git ls-files", file=sys.stderr)
        sys.exit(1)
    return ecrire("figures-tome3.tex", "\n".join(lignes)), len(entrees)


def main():
    casser = "--casser" in sys.argv[1:]
    if casser:
        figures(casser=True)
        print("ÉCHEC attendu non survenu : la cassure n'a pas fait tomber le témoin", file=sys.stderr)
        sys.exit(2)
    (f1, n1), (f2, n2), (f3, n3), (f4, n4) = outils(), journaux(), seuils(), figures()
    print(f"{f1} : {n1} outils ; {f2} : {n2} dossiers ; {f3} : {n3} fichiers de seuils ; {f4} : {n4} figures ;"
          " témoin des données : tient")


if __name__ == "__main__":
    main()
