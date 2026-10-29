#!/usr/bin/env bash
# Construit l'article court, en anglais et en français, et le paquet arXiv de chaque langue.
#   1. les figures : lualatex sur memoire/article/figures/figures-{en,fr}.tex (macros jugées du Tome III,
#      une page par figure), sortie copiée en <langue>/troncons-figures.pdf ;
#   2. l'article : pdflatex, bibtex, puis pdflatex trois fois (le moteur et la chaîne qu'arXiv accepte) ;
#   3. le paquet arXiv : <langue>/arxiv/ = troncons-article.tex, troncons-article.bbl, troncons-figures.pdf,
#      et l'archive arxiv-<langue>.tar.gz (fichiers à plat, sans chemin absolu).
# Usage, depuis n'importe où : bash memoire/article/construire-article.sh [en|fr|tout]
# Code de retour non nul à la première erreur, ou si un renvoi ou une citation reste indéfini.
set -euo pipefail
ICI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QUOI="${1:-tout}"

figures() {
  local l="$1"
  ( cd "$ICI/figures"
    lualatex -interaction=nonstopmode -halt-on-error "figures-$l.tex" > /dev/null
    lualatex -interaction=nonstopmode -halt-on-error "figures-$l.tex" > /dev/null
    cp "figures-$l.pdf" "$ICI/$l/troncons-figures.pdf" )
}

article() {
  local l="$1"
  ( cd "$ICI/$l"
    pdflatex -interaction=nonstopmode -halt-on-error troncons-article.tex > /dev/null
    bibtex troncons-article > /dev/null
    pdflatex -interaction=nonstopmode -halt-on-error troncons-article.tex > /dev/null
    pdflatex -interaction=nonstopmode -halt-on-error troncons-article.tex > /dev/null
    pdflatex -interaction=nonstopmode -halt-on-error troncons-article.tex > /dev/null
    if grep -E "undefined|Citation .* undefined|There were undefined" troncons-article.log; then
      echo "ÉCHEC ($l) : renvoi ou citation indéfini" >&2; exit 1
    fi
    if grep -q "^!" troncons-article.log; then echo "ÉCHEC ($l) : erreur LaTeX" >&2; exit 1; fi
    # Renvois instables après trois passes (jugement de l'article, M17) : le témoin tombe aussi.
    if grep -E "Rerun to get|Label\(s\) may have changed" troncons-article.log; then
      echo "ÉCHEC ($l) : renvois instables après trois passes" >&2; exit 1
    fi
    # Le paquet arXiv : le .bbl est celui que bibtex vient d'écrire (même programme que le PDF).
    # Dans le paquet, \bibliography nomme le .bib à plat (arXiv lit le .bbl et ne lance pas bibtex).
    rm -rf arxiv && mkdir arxiv
    sed 's|\\bibliography{../commun/troncons-article}|\\bibliography{troncons-article}|' troncons-article.tex \
      > arxiv/troncons-article.tex
    cp troncons-article.bbl troncons-figures.pdf arxiv/
    ( cd arxiv && tar -czf "../arxiv-$l.tar.gz" troncons-article.tex troncons-article.bbl troncons-figures.pdf )
    # Témoin : le paquet se compile seul, comme arXiv le fera (pdflatex sans bibtex, autant de passes que
    # les renvois en demandent : AutoTeX relance ; ici trois), et rend le même nombre de pages que l'article
    # construit ici. Il tombe sur un renvoi indéfini ou sur un « Rerun » laissé par la dernière passe (M17).
    local essai; essai="$(mktemp -d)"
    tar -xzf "arxiv-$l.tar.gz" -C "$essai"
    ( cd "$essai" && pdflatex -interaction=nonstopmode -halt-on-error troncons-article.tex > /dev/null \
                  && pdflatex -interaction=nonstopmode -halt-on-error troncons-article.tex > /dev/null \
                  && pdflatex -interaction=nonstopmode -halt-on-error troncons-article.tex > /dev/null )
    if grep -E "There were undefined|Citation .* undefined" "$essai/troncons-article.log"; then
      echo "ÉCHEC ($l) : le paquet arXiv laisse un renvoi indéfini" >&2; exit 1
    fi
    if grep -E "Rerun to get|Label\(s\) may have changed" "$essai/troncons-article.log"; then
      echo "ÉCHEC ($l) : le paquet arXiv laisse des renvois instables après trois passes" >&2; exit 1
    fi
    local p1 p2
    p1="$(pdfinfo troncons-article.pdf | grep Pages)"; p2="$(pdfinfo "$essai/troncons-article.pdf" | grep Pages)"
    [ "$p1" = "$p2" ] || { echo "ÉCHEC ($l) : paquet arXiv $p2, article $p1" >&2; exit 1; }
    rm -rf "$essai"
    echo "$l : $p1 ; paquet arXiv compilé seul : $p2" )
}

case "$QUOI" in
  en|fr) figures "$QUOI"; article "$QUOI" ;;
  tout)  figures en; article en; figures fr; article fr ;;
  *) echo "usage : $0 [en|fr|tout]" >&2; exit 2 ;;
esac
