"""Produit les tables des annexes du Tome II depuis le dépôt lui-même, et vérifie l'annexe des outils.

- memoire/tome2/annexes/outils-moteur.tex : chaque outil commité du moteur et de ses mesures
  (pilotes, analyses, témoins sous mesures/moteur/, exécutables et exemples sous moteur/, outils du
  mémoire du Tome II), rangé par lot, avec la première ligne de sa propre description, citée telle
  quelle, et son nombre de lignes ;
- memoire/tome2/annexes/journaux-moteur.tex : chaque dossier de journaux et de CSV commité sous
  mesures/moteur/, son nombre de fichiers et son volume ;
- memoire/tome2/annexes/seuils-dates.tex : chaque fichier de seuils déclarés, avec l'heure du commit
  qui l'a créé et le nombre de commits qui l'ont touché (le seuil se déclare avant la passe : l'heure
  du commit fait foi) ;
- memoire/tome2/annexes/figures-tome2.tex : chaque commande de figure du Tome II qui lit des données,
  et les fichiers qu'elle lit.

Les trois premières tables et le témoin se lisent au commit DEPOT_PUBLIE (git ls-tree, git cat-file,
git log), jamais dans l'arbre de travail ; le volume des journaux vient du relevé VOLUMES (voir plus bas).
La table des figures lit les fichiers de figures du Tome II que la construction compile.

Témoin : toute option que lit `moteur/bins/troncons/src/main.rs` au commit DEPOT_PUBLIE (appels a.a,
a.mot, a.nombre, a.exige) doit figurer dans le tableau des options de l'annexe B, en anglais et en
français ; sinon l'outil sort en erreur. Cassure : --casser retire une option de la liste lue dans
l'annexe, et l'outil doit alors tomber.

Rien n'est écrit à la main : tout vient de git, du relevé VOLUMES et des fichiers.
Bibliothèque standard seule.
Usage : python -I -X utf8 memoire/outils/tome2_annexes.py [--casser]
        python -I -X utf8 memoire/outils/tome2_annexes.py --relever-volumes   (refait VOLUMES, voir plus bas)
"""
import csv
import io
import re
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
from annexes import couper, description_de, echapper, git_arbre, git_contenus, texte_du_blob  # noqa: E402

DEPOT = Path(__file__).resolve().parents[2]
SORTIE = DEPOT / "memoire" / "tome2" / "annexes"
SOURCES = (".py", ".rs", ".cu", ".cuh", ".ps1", ".bat", ".sh")

# Le commit dont les annexes du Tome II décrivent le dépôt. Le Tome II décrit le dépôt tel qu'il était à sa
# publication (2026-10-16) : ses annexes ne suivent pas le moteur ni les outils qui ont changé depuis.
# 90e3945 (2026-10-16 20:58, « Tome II, reprise du jugement… ; annexe des outils régénérée (83 outils) ») est
# le commit qui a écrit outils-moteur.tex, et son arbre la redonne au bit (83 outils, 14 504 lignes) ; les
# trois autres tables, écrites à 072194f, sortent aussi égales de 90e3945 (mesures/moteur/ n'a plus changé
# depuis 072194f, et aucun commit entre les deux ne touche un fichier de seuils).
# Changé le 2026-10-29 : avant, l'outil comptait par git ls-files et lisait l'arbre de travail (contenus,
# lignes, os.stat, main.rs) ; relancé ce jour-là, il réécrivait outils-moteur.tex (main.rs de troncons
# 683 → 699 lignes, trc-codeur 125 → 138, tome2_chemin_noyaux.py 249 → 264 ; total 14 504 → 14 548) et
# sortait en code 1 : le témoin lisait le main.rs d'aujourd'hui, dont les options biais-cache (P3) et rapide
# (lot B) sont venues après le tome, et que son annexe B ne pouvait pas connaître.
DEPOT_PUBLIE = "90e3945"

# Le volume des journaux : la table commitée a été prise par os.stat sur le disque du 2026-10-16, où chaque
# fichier compte les octets que son écrivain y a mis. Sous core.autocrlf=true, git range les fins de ligne
# en LF et ne garde pas celles du disque, qui sont mêlées sous mesures/moteur/ (fichiers en LF, en CRLF, et
# des journaux aux deux sortes de fins de ligne). Éprouvé le 2026-10-29 : au commit, avec la taille du blob,
# 7 volumes sur 22 changent ; avec la taille d'une sortie en CRLF, 9 ; aucune règle par dossier ni par
# extension ne redonne la table. Le relevé VOLUMES garde donc, pour chaque fichier compté, son objet au
# commit, la taille du blob et la taille sur le disque. Il a été pris le 2026-10-29 par --relever-volumes
# sur ce disque, où mesures/moteur/ n'a pas changé depuis 072194f : chaque fichier y a le contenu de son
# objet au commit (fins de ligne normalisées, vérifié fichier par fichier), et la table qu'il donne est
# égale au bit à la table commitée. L'outil vérifie à chaque passe que VOLUMES couvre exactement les
# fichiers comptés au commit, objet pour objet, et tombe sinon.
VOLUMES = SORTIE / "volumes-mesures-moteur.csv"

# Rangement par lot, d'après le chemin (premier motif qui correspond) : (français, anglais).
LOTS = [
    (r"^moteur/bins/troncons/", ("O : le programme troncons", "O: the troncons program")),
    (r"^moteur/bins/trc-codeur/src/main", ("F : le codeur", "F: the coder")),
    (r"^moteur/bins/banc-chemin/src/main", ("E : le banc du chemin", "E: the path bench")),
    (r"^moteur/crates/trc-noyaux/banc/", ("K : le banc des noyaux", "K: the kernel bench")),
    (r"^moteur/crates/trc-cache/src/bin/", ("O : le simulateur du cache", "O: the cache simulator")),
    (r"^moteur/crates/trc-ordo/examples/", ("O : exemples du moteur", "O: engine examples")),
    (r"^moteur/crates/trc-juge/src/bin/", ("R : le programme du juge", "R: the judge program")),
    (r"^mesures/moteur/E/", ("E : mesures du chemin des octets", "E: byte-path measurements")),
    (r"^mesures/moteur/F/", ("F : mesures du format", "F: format measurements")),
    (r"^mesures/moteur/K/", ("K : mesures des noyaux", "K: kernel measurements")),
    (r"^mesures/moteur/O/corrections/", ("O : ronde de corrections", "O: round of corrections")),
    (r"^mesures/moteur/O/", ("O : mesures du moteur", "O: engine measurements")),
    (r"^mesures/moteur/R/", ("R : mesures de la référence", "R: reference measurements")),
    (r"^mesures/moteur/epreuve-J1/", ("Épreuve J1 (le juge indépendant)", "Trial J1 (the independent judge)")),
    (r"^memoire/outils/tome2_", ("Le mémoire du Tome~II", "The thesis, Volume~II")),
]


def lot(chemin):
    for i, (motif, nom) in enumerate(LOTS):
        if re.search(motif, chemin):
            return i, nom
    return None


def ecrire(nom, contenu):
    SORTIE.mkdir(parents=True, exist_ok=True)
    (SORTIE / nom).write_text(contenu, encoding="utf-8", newline="\n")
    return nom


def git_texte(*args):
    return subprocess.run(["git", "-C", str(DEPOT), *args],
                          capture_output=True, text=True, encoding="utf-8", check=True).stdout


def lignes_de(octets):
    """Lignes d'un objet, comptées comme une lecture en texte (fins de ligne universelles)."""
    return sum(1 for _ in io.TextIOWrapper(io.BytesIO(octets), encoding="utf-8", errors="replace"))


def outils():
    groupes = OrderedDict()
    candidats = git_arbre(DEPOT_PUBLIE, "mesures/moteur", "moteur/bins", "moteur/crates", "memoire/outils")
    retenus = [(c, o) for c, o, _ in candidats
               if c.endswith(SOURCES) and "__pycache__" not in c and lot(c) is not None]
    contenus = git_contenus(o for _, o in retenus)
    for c, o in sorted(retenus):
        groupes.setdefault(lot(c), []).append((c, o))
    lignes = ["% Engendré par memoire/outils/tome2_annexes.py : ne pas modifier à la main.",
              r"\begingroup\small",
              r"\begin{longtable}{@{}p{0.39\linewidth}p{0.48\linewidth}r@{}}", r"\toprule",
              r"\EF{Tool}{Outil} & \EF{Its own description (first line, quoted as written, in French)}"
              r"{Sa propre description (première ligne, citée)} & \EF{Lines}{Lignes} \\",
              r"\midrule", r"\endhead"]
    total, total_lignes = 0, 0
    for g in sorted(groupes):
        lignes.append(r"\multicolumn{3}{@{}l}{\textsf{\bfseries\EF{%s}{%s}}} \\" % (g[1][1], g[1][0]))
        for c, o in groupes[g]:
            d = couper(description_de(c, texte_du_blob(contenus[o])))
            n = lignes_de(contenus[o])
            lignes.append(r"\fichier{%s} & {\footnotesize %s} & \num{%d} \\"
                          % (c, echapper(d) if d else r"\textemdash", n))
            total += 1
            total_lignes += n
    lignes += [r"\midrule",
               r"\EF{Total}{Total} & \EF{%d tools}{%d outils} & \num{%d} \\" % (total, total, total_lignes),
               r"\bottomrule", r"\end{longtable}", r"\endgroup", ""]
    return ecrire("outils-moteur.tex", "\n".join(lignes)), total


def journaux_comptes():
    """[(chemin, objet, taille du blob, dossier)] des fichiers que compte la table des journaux, au commit."""
    res = []
    for c, o, t in git_arbre(DEPOT_PUBLIE, "mesures/moteur"):
        parties = PurePosixPath(c).parts
        if "__pycache__" in parties:
            continue
        # mesures/moteur/<lot>/<dossier>/… ; les fichiers posés à la racine d'un lot sont comptés
        # sous « <lot>/ (racine) ».
        if len(parties) >= 5:
            cle = "/".join(parties[:4]) + "/"
        elif len(parties) == 4:
            cle = "/".join(parties[:3]) + "/"
        else:
            continue
        if c.endswith(SOURCES):
            continue  # les outils sont dans l'autre table
        res.append((c, o, t, cle))
    return res


def relever_volumes():
    """Refait VOLUMES depuis le disque : pour chaque fichier compté au commit, sa taille sur le disque,
    après avoir vérifié que le disque porte bien son objet (contenu égal, fins de ligne normalisées)."""
    comptes = journaux_comptes()
    contenus = git_contenus(o for _, o, _, _ in comptes)
    normal = lambda b: b.replace(b"\r\n", b"\n")
    ecarts, rangs = [], []
    for c, o, t, _ in comptes:
        f = DEPOT / c
        disque = f.read_bytes() if f.is_file() else None
        if disque is None or normal(disque) != normal(contenus[o]):
            ecarts.append(c)
            continue
        rangs.append([c, o, t, len(disque)])
    if ecarts:
        for c in ecarts:
            print("ÉCHEC : le disque ne porte pas l'objet du commit pour", c, file=sys.stderr)
        sys.exit(1)
    SORTIE.mkdir(parents=True, exist_ok=True)
    with open(VOLUMES, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["chemin", "objet", "octets_blob", "octets_disque"])
        w.writerows(rangs)
    return VOLUMES.name, len(rangs)


def volumes(comptes):
    """{chemin: octets sur le disque} lus dans VOLUMES, qui doit couvrir exactement les fichiers comptés."""
    with open(VOLUMES, newline="", encoding="utf-8") as f:
        releve = {r["chemin"]: r for r in csv.DictReader(f)}
    attendus = {c: (o, t) for c, o, t, _ in comptes}
    ecarts = sorted(set(attendus) ^ set(releve))
    ecarts += sorted(c for c in set(attendus) & set(releve)
                     if (releve[c]["objet"], int(releve[c]["octets_blob"])) != attendus[c])
    if ecarts:
        for c in ecarts[:20]:
            print("ÉCHEC : le relevé", VOLUMES.name, "ne décrit pas", c, "tel qu'au commit", DEPOT_PUBLIE,
                  file=sys.stderr)
        sys.exit(1)
    return {c: int(r["octets_disque"]) for c, r in releve.items()}


def journaux():
    comptes = journaux_comptes()
    taille = volumes(comptes)
    dossiers = OrderedDict()
    for c, _, _, cle in comptes:
        n, o = dossiers.get(cle, (0, 0))
        dossiers[cle] = (n + 1, o + taille[c])
    lignes = ["% Engendré par memoire/outils/tome2_annexes.py : ne pas modifier à la main.",
              r"\begingroup\small", r"\begin{longtable}{@{}p{0.62\linewidth}rr@{}}", r"\toprule",
              r"\EF{Folder (logs, CSV, notes; tools excluded)}{Dossier (journaux, CSV, notes ; outils exclus)}"
              r" & \EF{Files}{Fichiers} & \EF{Size (MB)}{Volume (Mo)} \\",
              r"\midrule", r"\endhead"]
    nt, ot = 0, 0
    for cle in sorted(dossiers):
        n, o = dossiers[cle]
        nt += n
        ot += o
        lignes.append(r"\fichier{%s} & \num{%d} & \num{%.2f} \\" % (cle, n, o / 1e6))
    lignes += [r"\midrule", r"\EF{Total}{Total} & \num{%d} & \num{%.2f} \\" % (nt, ot / 1e6),
               r"\bottomrule", r"\end{longtable}", r"\endgroup", ""]
    return ecrire("journaux-moteur.tex", "\n".join(lignes))


def git_log(fichier, *options):
    """L'historique du fichier jusqu'au commit DEPOT_PUBLIE."""
    return git_texte("log", *options, DEPOT_PUBLIE, "--", fichier)


def seuils():
    fichiers = [c for c, _, _ in git_arbre(DEPOT_PUBLIE, "mesures/moteur", "decisions")
                if re.search(r"seuils(-declares)?\.md$|00-seuils-declares\.md$", c)]
    lignes = ["% Engendré par memoire/outils/tome2_annexes.py : ne pas modifier à la main.",
              r"\begingroup\small", r"\begin{longtable}{@{}p{0.50\linewidth}lr@{}}", r"\toprule",
              r"\EF{Declared thresholds}{Seuils déclarés} & \EF{Created by commit (local time)}"
              r"{Créé par le commit (heure locale)} & \EF{Commits}{Commits} \\",
              r"\midrule", r"\endhead"]
    for c in sorted(fichiers):
        cree = git_log(c, "--diff-filter=A", "--format=%h %ci").strip().splitlines()
        tous = git_log(c, "--format=%h").strip().splitlines()
        if not cree:
            continue
        h, date, heure = cree[-1].split()[:3]
        lignes.append(r"\fichier{%s} & \texttt{%s}, %s %s & \num{%d} \\" % (c, h, date, heure, len(tous)))
    lignes += [r"\bottomrule", r"\end{longtable}", r"\endgroup", ""]
    return ecrire("seuils-dates.tex", "\n".join(lignes))


def figures():
    """Les commandes de figures du Tome II qui lisent des données, et leurs fichiers.

    Lit l'arbre de travail, et non DEPOT_PUBLIE : cette table décrit les fichiers de figures que la
    construction compile (memoire/figures/tome2/) et vérifie que leurs données existent ; elle redonne au
    bit la table commitée (072194f) le 2026-10-29."""
    base = DEPOT / "memoire" / "figures" / "tome2"
    macros = {r"\DonneesTomeDeux": "memoire/figures/tome2/donnees", r"\DonneesTdArch": "memoire/figures/donnees/tome2",
              r"\Donnees": "memoire/figures/donnees", r"\Racine": "memoire", r"\Depot": "."}
    # Les fichiers de figures définissent aussi leurs propres raccourcis de dossier
    # (\providecommand{\X}{\Depot/…}) : on les relit d'abord.
    for f in sorted(base.rglob("*.tex")):
        for m in re.finditer(r"\\(?:provide|new)command\{(\\[A-Za-z]+)\}\{((?:\\[A-Za-z]+)?/?[^{}#]*)\}",
                             f.read_text(encoding="utf-8")):
            nom, valeur = m.group(1), m.group(2).strip()
            if "/" not in valeur or nom in macros:
                continue
            macros[nom] = valeur
    def resoudre(chemin):
        for _ in range(4):
            for k, v in sorted(macros.items(), key=lambda kv: -len(kv[0])):
                if chemin.startswith(k + "/") or chemin == k:
                    chemin = v + chemin[len(k):]
                    break
            else:
                break
        return chemin.lstrip("./") if chemin.startswith("./") else chemin
    lignes = ["% Engendré par memoire/outils/tome2_annexes.py : ne pas modifier à la main.",
              r"\begingroup\small", r"\begin{longtable}{@{}p{0.37\linewidth}p{0.59\linewidth}@{}}", r"\toprule",
              r"\EF{Figure (command)}{Figure (commande)} & \EF{Data files it reads}{Fichiers de données qu'elle lit} \\",
              r"\midrule", r"\endhead"]
    manquants = []
    n = 0
    for f in sorted(base.rglob("*.tex")):
        texte = f.read_text(encoding="utf-8")
        blocs = re.split(r"\\(?:provide|new)command\{(\\[A-Za-z]+)\}", texte)
        for i in range(1, len(blocs), 2):
            nom, corps = blocs[i], blocs[i + 1]
            fichiers = []
            for m in re.finditer(r"\{((?:\\[A-Za-z]+)(?:/[^{}\s]+)+\.(?:csv|dat|tsv))\}", corps):
                chemin = resoudre(m.group(1))
                if chemin not in fichiers:
                    fichiers.append(chemin)
            if not fichiers:
                continue
            for c in fichiers:
                if not (DEPOT / c).exists():
                    manquants.append((nom, c))
            n += 1
            cellule = r" \newline ".join(r"\fichier{%s}" % c for c in fichiers)
            lignes.append(r"\texttt{\textbackslash %s} & %s \\" % (nom[1:], cellule))
    lignes += [r"\bottomrule", r"\end{longtable}", r"\endgroup", ""]
    return ecrire("figures-tome2.tex", "\n".join(lignes)), n, manquants


def temoin_options(casser):
    """Toute option lue par main.rs au commit DEPOT_PUBLIE figure dans le tableau des options de
    l'annexe B (EN et FR). L'annexe est celle que la construction compile (arbre de travail)."""
    code = texte_du_blob(subprocess.run(
        ["git", "-C", str(DEPOT), "show", f"{DEPOT_PUBLIE}:moteur/bins/troncons/src/main.rs"],
        capture_output=True, check=True).stdout)
    lues = sorted(set(re.findall(r'\ba\.(?:a|mot|nombre|exige)\("([a-z0-9-]+)"', code)))
    ecarts = []
    for langue in ("en", "fr"):
        annexe = (DEPOT / f"memoire/tome2/{langue}/annexes/B-outils.tex").read_text(encoding="utf-8")
        # Les commentaires TeX ne comptent pas : l'en-tête du fichier écrit « \option{nom} » pour
        # dire la forme ; ce n'est pas une option. Un « \% » échappé n'ouvre pas de commentaire.
        annexe = re.sub(r"(?<!\\)%.*", "", annexe)
        ecrites = set(re.findall(r"\\option\{([a-z0-9-]+)\}", annexe))
        if casser and ecrites:
            ecrites.discard(sorted(ecrites)[0])
        for o in lues:
            if o not in ecrites:
                ecarts.append((langue, o))
        for o in sorted(ecrites - set(lues)):
            ecarts.append((langue, "en trop : " + o))
    return lues, ecarts


if __name__ == "__main__":
    if "--relever-volumes" in sys.argv[1:]:
        nom, n = relever_volumes()
        print(nom, n, "fichiers relevés")
        sys.exit(0)
    casser = "--casser" in sys.argv[1:]
    nom, n_outils = outils()
    print(nom, n_outils, "outils")
    print(journaux())
    print(seuils())
    nom, n_fig, manquants = figures()
    print(nom, n_fig, "figures qui lisent des données")
    lues, ecarts = temoin_options(casser)
    print("options lues par main.rs :", len(lues))
    erreur = False
    if manquants:
        erreur = True
        for f, c in manquants:
            print("ÉCHEC : la figure", f, "lit un fichier absent :", c, file=sys.stderr)
    if ecarts:
        erreur = True
        for langue, o in ecarts:
            print("ÉCHEC : annexe B", langue, ": option", o, file=sys.stderr)
    if erreur:
        sys.exit(1)
    print("témoin des options : tient (" + ("cassure demandée et pourtant tient : défaut" if casser else "0 écart") + ")")
    if casser:
        sys.exit(2)
