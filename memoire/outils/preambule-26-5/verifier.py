"""Relit les journaux de compilation : erreurs, renvois et citations manquants, rerun, pages, versions.
Les messages « fichier:ligne: ignored: » (non fatals sous -halt-on-error) se comptent à part.
Usage : python -I -X utf8 verifier.py chemin/vers/a.log [b.log ...]
Mêmes motifs que memoire/construire.sh pour les manques, plus le décompte des erreurs (« ! » en tête de
ligne, ou « fichier:ligne: » de -file-line-error) et le journal de biber (.blg) s'il est à côté."""
import pathlib
import re
import sys

MANQUE = re.compile(r"undefined|Undefined|There were undefined references|Citation .* undefined|Reference .* undefined")
ERREUR = re.compile(r"^! |^[^ ]+\.(tex|sty|cls|def|ltx|cfg|clo):\d+: ")
FATALE = re.compile(r"Fatal error occurred|TeX capacity exceeded|Emergency stop|^\d+: [A-Z].*(Error|exceeded)")
ABSENT = re.compile(r"File .* not found|Package pgfplots Error|could not be found")
RERUN = re.compile(r"Rerun to get|Label\(s\) may have changed|Please \(re\)run Biber")
PAGES = re.compile(r"Output written on .*\((\d+) pages")


def lire(chemin):
    return pathlib.Path(chemin).read_text(encoding="utf-8", errors="replace")


for nom in sys.argv[1:]:
    log = lire(nom)
    lignes = log.splitlines()
    ignorees = [l for l in lignes if ERREUR.search(l) and ": ignored: " in l]
    erreurs = [l for l in lignes if ERREUR.search(l) and ": ignored: " not in l]
    # Une erreur fatale coupée par le retour à la ligne du journal (« fichier.tex:\n35: TeX capacity… »)
    # échappe au motif ci-dessus : elle se compte ici.
    erreurs += [l for l in lignes if FATALE.search(l) and l not in erreurs]
    manques = [l for l in lignes if MANQUE.search(l)]
    absents = [l for l in lignes if ABSENT.search(l)]
    reruns = [l for l in lignes if RERUN.search(l)]
    pleines = sum(1 for l in lignes if l.startswith("Overfull \\hbox") or l.startswith("Overfull \\vbox"))
    pages = PAGES.findall(log)
    tete = lignes[0] if lignes else ""
    noyau = next((l for l in lignes if l.startswith("LaTeX2e <")), "?")
    blg = pathlib.Path(nom).with_suffix(".blg")
    biber = "pas de .blg"
    if blg.exists():
        b = lire(blg)
        biber = f"{len(re.findall(r'^ERROR', b, re.M))} ERROR, " \
                f"{len(re.findall(r'WARN - (?:I didn.t find|Duplicate)', b))} entrée(s) absente(s) ou en double"
    print(f"{pathlib.Path(nom).name} : {len(erreurs)} erreur(s), {len(manques)} manque(s), {len(absents)} absent(s), "
          f"{len(reruns)} rerun, {len(ignorees)} message(s) « ignored », {pleines} boîte(s) trop pleine(s), pages {pages[-1] if pages else '?'} ; "
          f"biber : {biber}")
    print(f"    {tete[:90]} ; {noyau}")
    for l in (erreurs + manques + absents + reruns)[:8]:
        print("    >", l[:150])
