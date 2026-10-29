"""Cassures des gardes neuves de la troisième passe des figures du Tome III (SOCLE : « tout témoin neuf doit pouvoir
échouer »). Chaque garde est forcée à faux, une à une, et doit arrêter son script :
  1. GN2 (III-8.5) : colonne-par-tenseur.csv ne recopie plus le codec réel (un débit faux de 1e-3 relatif) ;
  2. N2 (III-8.6 bis) : une passe J5 lit 1 199 tronçons au lieu de 1 200 ;
  3. GN1 (III-10.1) : tailles.json ne dit plus les 768 experts décodés (767) ;
  4. G7 (III-9.6) : l'ancienne règle de cadre (marge 0,04 bit au pas de 0,02) fait tomber la garde des 50 %.
Les autres gardes neuves ont leur propre cassure : tome3_latents.py --casse-entrees (témoin E1), et la règle des
valeurs d'arête de tome3_duplication.py, tombée d'elle-même au premier essai (jeu −0,096 cm). Les scripts cassés
écrivent dans un dossier jetable (D remplacé), jamais sous memoire/figures/tome3/donnees/.

  python -I -X utf8 memoire/outils/tome3_cassures.py      (quatre lignes « la garde tombe » attendues)
"""
import importlib.util
import pathlib
import tempfile
import traceback

O = pathlib.Path(__file__).resolve().parent


def charger(nom):
    spec = importlib.util.spec_from_file_location(nom + "_casse", O / f"{nom}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.D = pathlib.Path(tempfile.mkdtemp(prefix=nom + "-casse-"))
    return m


def essai(titre, nom, alterer, appel):
    m = charger(nom)
    alterer(m)
    try:
        appel(m)
        print(f"{titre} : la garde TIENT (elle n'est pas tombée) -- ÉCHEC du témoin")
    except AssertionError as e:
        last = traceback.extract_tb(e.__traceback__)[-1]
        print(f"{titre} : la garde tombe (assert ligne {last.lineno} de {nom}.py) -- témoin bon")


def lire_csv_altere(m, fichier, colonne, facteur):
    orig = m.lire_csv

    def f(chemin):
        lignes = orig(chemin)
        if pathlib.Path(chemin).name == fichier:
            lignes = [dict(r) for r in lignes]
            lignes[0][colonne] = str(float(lignes[0][colonne]) * facteur)
        return lignes
    m.lire_csv = f


# 1. GN2 (III-8.5) : colonne-par-tenseur.csv ne recopie plus le codec réel (un débit faux de 1e-3 relatif)
essai("GN2 codec réel", "tome3_codon",
      lambda m: lire_csv_altere(m, "colonne-par-tenseur.csv", "zero_demi_octet_kappa_colonne", 1.001),
      lambda m: m.colonne(m.Nombres()))


# 2. N2 (III-8.6 bis) : une passe J5 lit un autre nombre de tronçons
def j5(m):
    orig = m.lire_json

    def f(chemin):
        d = orig(chemin)
        if pathlib.Path(chemin).name == "J5-01-C120.json":
            d = dict(d)
            d["n"] = 1199
        return d
    m.lire_json = f


essai("N2 tronçons de J5", "tome3_codon", j5, lambda m: m.j1(m.Nombres()))

# 3. GN1 (III-10.1) : tailles.json ne dit plus tous les experts décodés
def c1(m):
    orig = m.lire_json

    def f(chemin):
        d = orig(chemin)
        if pathlib.Path(chemin).name == "tailles.json":
            import copy
            d = copy.deepcopy(d)
            d["totaux"]["20b"]["experts_exacts_v12"] = 767
        return d
    m.lire_json = f


essai("GN1 décodage C1", "tome3_juge", c1, lambda m: m.grille(m.Nombres()))


# 4. G7 (III-9.6) : l'ancienne règle de cadre (marge 0,04 au pas de 0,02) doit faire tomber la garde des 50 %
def g7(m):
    import math
    src = (O / "tome3_synonyme.py").read_text(encoding="utf-8")
    assert "MARGE_BITS, PAS_BITS, PART_MIN = 0.02, 0.01, 0.5" in src
    src = src.replace("MARGE_BITS, PAS_BITS, PART_MIN = 0.02, 0.01, 0.5", "MARGE_BITS, PAS_BITS, PART_MIN = 0.04, 0.02, 0.5")
    code = compile(src, "tome3_synonyme_casse", "exec")
    exec(code, m.__dict__)
    m.D = pathlib.Path(tempfile.mkdtemp(prefix="syno-casse-"))


essai("G7 part du cadre", "tome3_synonyme", g7, lambda m: (m.D.mkdir(exist_ok=True), m.variantes(m.Nombres())))
