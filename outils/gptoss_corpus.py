"""Corpus de texte réel pour relever le routage des experts de gpt-oss : quatre genres.

Chaque extrait part d'un repère écrit ici (une ligne exacte du texte source), garde au plus
TAILLE octets UTF-8 et s'arrête à la fin de la dernière ligne complète. Les fins de ligne sont
ramenées à « \\n ». Le corpus et les empreintes SHA-256 des sources et des extraits vont dans le
dossier de sortie (corpus.json). Les sources :

  prose-en   wikitext-2-raw, test (CC BY-SA 3.0), déjà sur la machine (étude 06) ; on part de la première ligne
             qui suit les 3 000 premiers octets qui forment l'invite fixée de la base, pour ne pas
             mesurer deux fois le même passage ;
  prose-fr   Victor Hugo, « Les Misérables, tome I : Fantine », Project Gutenberg n° 17489
             (domaine public), à partir de « En 1815, M. Charles-François-Bienvenu Myriel » ;
  dialogue   Oscar Wilde, « The Importance of Being Earnest », Project Gutenberg n° 844
             (domaine public), à partir de « FIRST ACT » : répliques courtes, noms de personnages ;
  code       Lib/functools.py de CPython 3.13.12 (licence PSF), à partir de « __all__ » : l'en-tête
             du fichier porte des adresses électroniques, qui n'entrent pas dans le dépôt (SOCLE).

Pourquoi 11 000 octets : environ 2 500 à 3 200 jetons selon le genre avec le découpeur o200k de
gpt-oss, sous le contexte de 4 096 jetons du traceur, et au moins 2 000 jetons par genre, donc
plus de 8 000 jetons de lecture par modèle (la consigne en demande au moins 2 000).

Usage : python -I gptoss_corpus.py --sortie <dossier> --wikitext <wiki.test.raw>
        --hugo <pg17489.txt> --wilde <pg844.txt> --code <functools.py>
"""
import argparse
import hashlib
import json
import os

TAILLE = 11000


def sha(b):
    return hashlib.sha256(b).hexdigest()


def extrait(brut, repere, depart_octet=0):
    texte = brut.decode("utf-8").replace("\r\n", "\n")
    if repere is not None:
        i = texte.find(repere)
        if i < 0:
            raise SystemExit(f"repère introuvable : {repere!r}")
    else:
        i = len(texte.encode("utf-8")[:depart_octet].decode("utf-8", "ignore"))
        if depart_octet:  # on repart au début de la ligne suivante
            i = texte.find("\n", i) + 1
    morceau = texte[i:].encode("utf-8")[:TAILLE].decode("utf-8", "ignore")
    coupe = morceau.rfind("\n")
    return morceau[: coupe + 1] if coupe > 0 else morceau


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sortie", required=True)
    ap.add_argument("--wikitext", required=True)
    ap.add_argument("--hugo", required=True)
    ap.add_argument("--wilde", required=True)
    ap.add_argument("--code", required=True)
    a = ap.parse_args()
    os.makedirs(a.sortie, exist_ok=True)
    plan = [
        ("prose-en", a.wikitext, None, 3000, "wikitext-2-raw test, CC BY-SA 3.0"),
        ("prose-fr", a.hugo, "En 1815, M. Charles-François-Bienvenu Myriel", 0,
         "Victor Hugo, Les Misérables I, Project Gutenberg 17489, domaine public"),
        ("dialogue", a.wilde, "FIRST ACT", 0,
         "Oscar Wilde, The Importance of Being Earnest, Project Gutenberg 844, domaine public"),
        ("code", a.code, "__all__ = ['update_wrapper'", 0, "CPython 3.13.12 Lib/functools.py, licence PSF"),
    ]
    bilan = {"taille_max_octets": TAILLE, "extraits": []}
    for nom, chemin, repere, depart, origine in plan:
        brut = open(chemin, "rb").read()
        t = extrait(brut, repere, depart)
        b = t.encode("utf-8")
        open(os.path.join(a.sortie, nom + ".txt"), "wb").write(b)
        bilan["extraits"].append({"genre": nom, "source": os.path.basename(chemin), "origine": origine,
                                  "source_sha256": sha(brut), "source_octets": len(brut),
                                  "repere": repere, "depart_octet": depart,
                                  "extrait_octets": len(b), "extrait_sha256": sha(b)})
        print(f"{nom:9s} {len(b):6d} octets  {sha(b)[:16]}")
    json.dump(bilan, open(os.path.join(a.sortie, "corpus.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
