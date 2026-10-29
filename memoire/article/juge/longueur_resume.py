"""Longueur du résumé de chaque version, contre la limite d'arXiv (1 920 caractères pour le champ « abstract »,
https://info.arxiv.org/help/prep.html, lue le 2026-10-29).

Compte deux longueurs : le LaTeX brut entre \\begin{abstract} et \\end{abstract}, et un texte approché (sans
\\num, \\texttt, $, espaces fines). Le champ d'arXiv recevra un texte entre les deux.
Usage, depuis la racine du dépôt :
  python -I -X utf8 memoire/article/juge/longueur_resume.py memoire/article/en/troncons-article.tex memoire/article/fr/troncons-article.tex
"""
import re
import sys

LIMITE = 1920
for f in sys.argv[1:]:
    t = open(f, encoding="utf-8").read()
    a = t.split(r"\begin{abstract}")[1].split(r"\end{abstract}")[0].strip()
    p = re.sub(r"\\num\{([^}]*)\}", r"\1", a)
    p = re.sub(r"\\texttt\{([^}]*)\}", r"\1", p)
    p = p.replace(r"\,", " ").replace(r"\%", "%").replace("{,}", ",").replace("$", "")
    print(f"{f} : LaTeX {len(a)}, texte approché {len(p)}, limite {LIMITE} : "
          + ("sous la limite" if len(a) <= LIMITE else "AU-DELÀ"))
