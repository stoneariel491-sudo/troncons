"""Données des chapitres « Architecture » et « Format .trc » du Tome II (memoire/tome2/).

Écrit, sous memoire/figures/donnees/tome2/, des CSV tirés uniquement de fichiers commités :
- caisses.csv : chaque crate et chaque binaire de moteur/, son lot (ARCHITECTURE.md § 6.1), ses
  lignes de code, de témoins et d'outils, ses dépendances internes (lues dans son Cargo.toml) ;
- sections.csv : les cinq sections des deux fichiers .trc (décalage, longueur), lues par le second
  chemin de C1 (mesures/moteur/F/journaux/second-chemin-{20b,120b}.json, champ entete.sections) ;
- flux-moyens.csv : les octets moyens de chaque sorte de flux par matrice d'expert, depuis les
  totaux de la vérification C1 (mesures/moteur/F/journaux/verifier-{20b,120b}.json, taux.octets_flux) ;
- calculs-format.csv : les grandeurs dérivées que cite le chapitre du format (nombre de tuiles,
  mots d'un flux, surcoût d'en-tête), chacune avec sa formule.
Tout se lit au commit DEPOT_PUBLIE (git ls-tree, git cat-file, git show), jamais dans l'arbre de travail.
Bibliothèque standard seule. Usage : python -I -X utf8 memoire/outils/tome2_format.py
"""
import csv
import io
import json
import math
import re
import subprocess
from pathlib import Path, PurePosixPath

DEPOT = Path(__file__).resolve().parents[2]
JF = "mesures/moteur/F/journaux"
SORTIE = DEPOT / "memoire" / "figures" / "donnees" / "tome2"

# Le commit dont ces données décrivent le moteur et ses journaux. Le Tome II décrit le dépôt tel qu'il était
# à sa publication (2026-10-16) ; ses chapitres « Architecture » et « Format .trc » ne suivent pas le moteur
# qui a continué d'évoluer depuis (lot A, codon ; lot B, mode rapide ; P3, routeur biaisé). 283b64c
# (2026-10-16 10:33) est le commit qui a écrit les quatre CSV ; son arbre sous moteur/ est celui de 30d8165,
# et tout commit de 30c6894 à 36cb1c0 exclu redonne caisses.csv au bit (36cb1c0 : trc-reference passe de
# 1 592 à 1 618 lignes). Les journaux de mesures/moteur/F/ que lisent les trois autres CSV n'ont pas changé
# depuis 283b64c.
# Changé le 2026-10-29 : avant, caisses() parcourait moteur/ sur le disque (fichiers non suivis compris) et
# les JSON se lisaient dans l'arbre de travail ; relancé ce jour-là, l'outil réécrivait 9 des 14 lignes de
# caisses.csv (trc-codec, trc-format, trc-noyaux, trc-reference…), donc une figure et une table du Tome II.
DEPOT_PUBLIE = "283b64c"

# Propriétaire de chaque membre de l'espace de travail : ARCHITECTURE.md § 6.1.
LOTS = {
    "trc-format": "F", "trc-codec": "F", "trc-codeur": "F",
    "trc-cuda": "E", "trc-es": "E", "banc-chemin": "E",
    "trc-noyaux": "K",
    "trc-reference": "R", "trc-jetons": "R", "trc-juge": "R",
    "trc-cache": "O", "trc-ordo": "O", "trc-modele": "O", "troncons": "O",
}


def ecrire(nom, entetes, lignes):
    SORTIE.mkdir(parents=True, exist_ok=True)
    with open(SORTIE / nom, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(entetes)
        w.writerows(lignes)


def git(*args, entree=None):
    return subprocess.run(["git", "-C", str(DEPOT), *args], input=entree, capture_output=True, check=True).stdout


def arbre(*prefixes):
    """[(chemin, objet)] des fichiers suivis sous les préfixes, au commit DEPOT_PUBLIE."""
    res = []
    for e in git("ls-tree", "-r", "-z", DEPOT_PUBLIE, "--", *prefixes).split(b"\0"):
        if not e:
            continue
        meta, chemin = e.split(b"\t", 1)
        _, genre, objet = meta.split()
        if genre == b"blob":
            res.append((chemin.decode("utf-8"), objet.decode("ascii")))
    return res


def contenus(objets):
    """{objet: octets} par un seul git cat-file --batch."""
    objets = list(dict.fromkeys(objets))
    brut = git("cat-file", "--batch", entree="".join(o + "\n" for o in objets).encode("ascii"))
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


def lire_json(chemin):
    """Un journal JSON tel qu'il est au commit DEPOT_PUBLIE."""
    return json.loads(git("show", f"{DEPOT_PUBLIE}:{chemin}").decode("utf-8-sig"))


def lignes(octets):
    """Lignes d'un objet, comptées comme une lecture en texte (fins de ligne universelles : un CRLF de la
    copie de travail ne change rien au compte)."""
    return sum(1 for _ in io.TextIOWrapper(io.BytesIO(octets), encoding="utf-8", errors="replace"))


def sorte_de(rel):
    """Code, témoin ou outil, d'après la place du fichier dans la crate."""
    parties = rel.parts
    if parties[0] == "tests" or rel.name == "tests.rs":
        return "temoins"
    if parties[0] in ("banc", "examples") or (len(parties) > 1 and parties[0] == "src" and parties[1] == "bin"):
        return "outils"
    return "code"


def caisses():
    # Chaque membre : un dossier moteur/crates/<nom>/ ou moteur/bins/<nom>/ qui porte un Cargo.toml, au commit.
    fichiers = arbre("moteur/crates", "moteur/bins")
    octets = contenus(o for _, o in fichiers)
    membres = {}
    for c, o in fichiers:
        p = PurePosixPath(c)
        if len(p.parts) > 3:
            membres.setdefault((p.parts[1], p.parts[2]), []).append((PurePosixPath(*p.parts[3:]), o))
    rangs = []
    for groupe in ("crates", "bins"):
        for nom in sorted(n for g, n in membres if g == groupe):
            objets = {str(r): o for r, o in membres[(groupe, nom)]}
            if "Cargo.toml" not in objets:
                continue
            compte = {"code": 0, "temoins": 0, "outils": 0}
            for r, o in membres[(groupe, nom)]:
                if r.suffix in (".rs", ".cu", ".cuh") and "target" not in r.parts:
                    compte[sorte_de(r)] += lignes(octets[o])
            texte = octets[objets["Cargo.toml"]].decode("utf-8").replace("\r\n", "\n")
            internes = sorted(set(re.findall(r"^(trc-[a-z-]+)\s*=\s*\{\s*path", texte, re.M)))
            rangs.append([nom, "binaire" if groupe == "bins" else "crate", LOTS.get(nom, "?"),
                          compte["code"], compte["temoins"], compte["outils"],
                          len(internes), " ".join(internes)])
    ecrire("caisses.csv", ["nom", "sorte", "lot", "code", "temoins", "outils", "n_dep", "dependances"], rangs)
    return rangs


def sections():
    noms = ["MÉTA", "RÉSIDENTS", "TABLES", "RÉPERTOIRE", "TRONÇONS"]
    rangs = []
    for m in ("20b", "120b"):
        d = lire_json(f"{JF}/second-chemin-{m}.json")
        for i, (dec, lg) in enumerate(d["entete"]["sections"]):
            rangs.append([m, i, noms[i], dec, lg, dec + lg])
    ecrire("sections.csv", ["modele", "indice", "section", "decalage", "longueur", "fin"], rangs)
    return rangs


def flux_moyens():
    rangs, par_modele = [], {}
    for m in ("20b", "120b"):
        d = lire_json(f"{JF}/verifier-{m}.json")
        n_mat = 3 * d["experts"]
        o = d["taux"]["octets_flux"]
        moy = {k: o[k] / n_mat for k in ("medianes", "biais", "delta", "codes")}
        par_modele[m] = (d, moy)
        for k, v in moy.items():
            rangs.append([m, k, f"{v:.1f}"])
    ecrire("flux-moyens.csv", ["modele", "sorte", "octets_moyens_par_matrice"], rangs)
    return par_modele


def calculs(par_modele):
    """Grandeurs dérivées pour gpt-oss (R = C = 2 880, B = 90), chacune avec sa formule."""
    R, C = 2880, 2880
    B = C // 32
    n_blocs = R * B
    P_delta = math.ceil(n_blocs / 128) * 128
    P_codes = math.ceil(16 * n_blocs / 128) * 128
    T_delta = math.ceil(P_delta / 128 / 256)
    T_codes = math.ceil(P_codes / 128 / 256)
    rangs = [
        ["blocs_par_matrice", n_blocs, "R·B = 2880·90"],
        ["P_delta", P_delta, "⌈R·B/128⌉·128"],
        ["P_codes", P_codes, "⌈16·R·B/128⌉·128"],
        ["macro_pas_codes", P_codes // 128, "P/128"],
        ["T_delta", T_delta, "⌈(P/128)/256⌉"],
        ["T_codes", T_codes, "⌈(P/128)/256⌉"],
        ["entete_fixe_delta", 16 + 4 * T_delta + 128 * T_delta, "16 + 4T + 128T"],
        ["entete_fixe_codes", 16 + 4 * T_codes + 128 * T_codes, "16 + 4T + 128T"],
        ["entete_partie", 64 + 12 * 16, "64 + 12·16"],
        ["origine_par_expert", 3 * (17 * n_blocs + 4 * R), "3·(17·R·B + 4R)"],
        ["emplacement_par_matrice", None, "al256(al256(16RB)+RB)+4R arrondi à 256"],
    ]
    a = lambda x: (x + 255) // 256 * 256
    rangs[-1][1] = a(a(a(16 * n_blocs) + n_blocs) + 4 * R)
    for m, (d, moy) in par_modele.items():
        for k, nom, T in (("codes", "codes", T_codes), ("delta", "delta", T_delta)):
            fixe = 16 + 4 * T + 128 * T
            mots = (moy[k] - fixe) / 2
            rangs.append([f"mots_moyens_{nom}_{m}", f"{mots:.0f}", "(octets moyens − en-tête fixe)/2, bourrage ≤ 15 o compris"])
            rangs.append([f"part_entete_{nom}_{m}", f"{fixe / moy[k]:.6f}", "en-tête fixe / octets moyens du flux"])
        utiles = sum(3 * v for v in moy.values()) + 64 + 12 * 16
        rangs.append([f"utiles_moyens_{m}", f"{utiles:.0f}", "3·Σ flux moyens + 64 + 192 (bourrage à 16 des flux bruts : 0)"])
        rangs.append([f"troncon_moyen_{m}", f"{d['troncon_octets']['moyen']:.1f}", "verifier-*.json"])
        rangs.append([f"bourrage_moyen_{m}", f"{d['troncon_octets']['moyen'] - utiles:.0f}", "tronçon moyen − utiles moyens"])
        rangs.append([f"bpp_codes_{m}", f"{d['taux']['bpp_codes']:.6f}", "verifier-*.json"])
        rangs.append([f"bpp_total_03_{m}", f"{d['taux']['bpp_total_03']:.6f}", "verifier-*.json"])
        rangs.append([f"r_03_{m}", f"{d['taux']['r_03']:.6f}", "verifier-*.json"])
    n = 4608
    rangs.append(["borne_collision_120b", f"{n * 2.0 ** -64:.3e}", "4608·2^-64"])
    ecrire("calculs-format.csv", ["grandeur", "valeur", "formule"], rangs)
    return rangs


if __name__ == "__main__":
    for r in caisses():
        print("caisse", r)
    for r in sections():
        print("section", r)
    pm = flux_moyens()
    for r in calculs(pm):
        print("calcul", r)
