# Juge de la troisième passe : régénère les données des figures du Tome III par les scripts commités, dans une copie
# tirée par « git -c core.autocrlf=false archive HEAD » hors du dépôt, dossier des données vide au départ, et compare
# chaque fichier écrit au blob commité (SHA-256). Témoin du comparateur (--casser) : un octet ajouté à une copie de
# chaque fichier écrit ; chaque comparaison doit tomber. Une garde forcée à faux (--garde NOM) change une donnée de
# la copie, relance le seul script concerné, et vérifie qu'il s'arrête (code non nul) sans rien écrire sous les
# données du dépôt.
# Usage : python -I -X utf8 regenerer3.py BROUILLON [--casser] [--garde NOM]
import hashlib, io, json, shutil, subprocess, sys, tarfile
from pathlib import Path

DEPOT = Path(__file__).resolve().parents[4]
brouillon = Path(sys.argv[1]).resolve()
CASSER = "--casser" in sys.argv
GARDE = sys.argv[sys.argv.index("--garde") + 1] if "--garde" in sys.argv else None
CHEMINS = ["memoire/outils", "memoire/commun/preambule.tex", "memoire/figures/tome3", "mesures/genome",
           "mesures/disque/placement", "mesures/moteur/O/journaux/o3", "outils/genome/tome3"]
SCRIPTS = ["eclaireur", "genome", "duplication", "synthese", "codon", "synonyme", "juge", "latents", "palette"]
DON = "memoire/figures/tome3/donnees"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def empreintes_depot() -> dict:
    return {p.name: sha(p.read_bytes()) for p in (DEPOT / DON).iterdir() if p.is_file()}


avant = empreintes_depot()
if brouillon.exists():
    shutil.rmtree(brouillon)
brouillon.mkdir(parents=True)
tar = subprocess.run(["git", "-C", str(DEPOT), "-c", "core.autocrlf=false", "archive", "--format=tar", "HEAD", *CHEMINS],
                     capture_output=True, check=True).stdout
with tarfile.open(fileobj=io.BytesIO(tar)) as t:
    t.extractall(brouillon, filter="data")
commites = {}
for p in (brouillon / DON).iterdir():
    commites[p.name] = sha(p.read_bytes())
shutil.rmtree(brouillon / DON)
(brouillon / DON).mkdir()

# --- les gardes forcées à faux : une donnée changée dans la copie, le script concerné doit s'arrêter -----------------
GARDES = {
    # GN2 (III-8.5) : un débit du journal du codec réel faux de 1e-3 relatif
    "gn2": ("codon", "mesures/genome/predictif-elagage/taux-reel-colonne-12-gptoss20b.json",
            lambda t: t.replace('"bpp_total_nib_kappa_colonne": 3.46569', '"bpp_total_nib_kappa_colonne": 3.46916', 1)),
    # GN1 (III-10.1) : 767 experts décodés au lieu de 768
    "gn1": ("juge", "mesures/genome/construction/codon/tailles.json",
            lambda t: t.replace('"experts_exacts_v12": 768', '"experts_exacts_v12": 767', 1)),
    # G7 (III-9.6) : les bits de λ = 1 rapprochés de la frontière (les variantes couvrent moins de la moitié)
    "g7": ("synonyme", "mesures/genome/construction/synonyme/figures/variantes-768.csv",
           lambda t: t.replace("synonyme-l1,2.5860536493162725", "synonyme-l1,2.6260536493162725", 1)),
    # J5/J6 (III-8.6 bis) : une passe J6 qui lit 799 tronçons
    "j6": ("codon", "mesures/disque/placement/juge/seance/J6-01-C120.json",
           lambda t: t.replace('"n": 800', '"n": 799', 1)),
    # compagnon (III-8.6 bis) : une fenêtre du proxy perdue (neuf fenêtres)
    "compagnon": ("codon", "mesures/genome/construction/synonyme/proxy/proxy-120b-exact-contre-rapide-frontiere.csv",
                  lambda t: "\n".join(l for l in t.splitlines() if not l.startswith("9,")) + "\n"),
    # j = 11 (III-9.1 (c)) : le zéro exact de j = 11 déplacé de 0,01 (voir forcer())
    "j11": ("latents", "mesures/genome/tome3/latents/rangee-L08-E00-gate.csv", None),
    # E1 (III-9.7) : le journal du juge 2 dont le rapport quadratique pondéré est faux de 1e-6
    "e1": ("latents", "outils/genome/tome3/juge2-latents/journaux/juge2-nuage-rangee.json",
           lambda t: t.replace('"rapport_quadratique_pondere_g2": 0.6106872658272865',
                               '"rapport_quadratique_pondere_g2": 0.6106878658272865', 1)),
    # seconde pointe (III-7.4) : la colonne 960 ramenée sous la colonne 961 (la pointe n'est plus un bord)
    "pointe": ("synthese", "mesures/genome/genome/csv/colonnes-energie-erreur.csv", None),
    # DN7 (III-4.8) : impossible par une donnée sans changer le dessin ; voir le jugement (forcé par la géométrie)
}


def forcer(nom: str):
    script, chemin, f = GARDES[nom]
    p = brouillon / chemin
    t = p.read_text(encoding="utf-8")
    if nom == "j11":
        # le zéro de j = 11 : exact −0 mis à −0,01 ; les deux bases restent ±c0 ; il s'éloigne alors aussi (4 sur 4),
        # et la tête « l'autre, un zéro, à la même distance » deviendrait fausse : la garde doit tomber
        t2 = t.replace("11,1675,8,-0.000000,", "11,1675,8,-0.010000,", 1)
    elif nom == "pointe":
        lignes = t.splitlines()
        tete = lignes[0].split(",")
        i = tete.index("erreur_brin_pondere")
        out = [lignes[0]]
        for l in lignes[1:]:
            c = l.split(",")
            if c[0] == "961":
                c[i] = "9.5e+03"   # la colonne 961 dépasse la 960 (9,26e3) : la seconde pointe n'est plus un bord
            out.append(",".join(c))
        t2 = "\n".join(out) + "\n"
    else:
        t2 = f(t)
    assert t2 != t, f"la garde {nom} n'a rien changé"
    p.write_text(t2, encoding="utf-8", newline="")
    return script


journal = {"brouillon": str(brouillon), "commites": len(commites), "scripts": {}}
liste = SCRIPTS
if GARDE:
    liste = [forcer(GARDE)]
for s in liste:
    r = subprocess.run([sys.executable, "-I", "-X", "utf8", str(brouillon / f"memoire/outils/tome3_{s}.py")],
                       cwd=brouillon, capture_output=True)
    err = r.stderr.decode("utf-8", "replace").strip().splitlines()
    journal["scripts"][s] = {"code": r.returncode, "erreur": err[-1][:300] if err else ""}
ecrits = {p.name: sha(p.read_bytes()) for p in (brouillon / DON).iterdir() if p.is_file()}
if not GARDE:
    egaux = sorted(n for n in ecrits if commites.get(n) == ecrits[n])
    differents = sorted(n for n in ecrits if n in commites and commites[n] != ecrits[n])
    en_trop = sorted(n for n in ecrits if n not in commites)
    manquants = sorted(n for n in commites if n not in ecrits)
    journal.update({"ecrits": len(ecrits), "egaux": len(egaux), "differents": differents, "en_trop": en_trop,
                    "manquants": manquants})
    if CASSER:
        tombe = 0
        for n in ecrits:
            b = (brouillon / DON / n).read_bytes() + b"x"
            tombe += sha(b) != commites.get(n)
        journal["casse_tombent"] = f"{tombe} sur {len(ecrits)}"
else:
    journal["garde"] = GARDE
    journal["tombe"] = journal["scripts"][liste[0]]["code"] != 0
journal["depot_intact"] = empreintes_depot() == avant
print(json.dumps(journal, ensure_ascii=False, indent=1))
