#!/usr/bin/env bash
# Juge de la troisième passe : construit les Tomes I et II tels que commités (préambule réparé), sous
# MiKTeX tel qu'installé, sans toucher les PDF commités. Sorties sous memoire/essai/juge3/tomes/<nom>/ ;
# nom de travail « j3-tN-L », distinct de celui du maître (LuaTeX efface le PDF du nom de travail dans le
# dossier courant malgré -outdir).
# Usage : construire_tomes.sh "t1-fr t1-en t2-fr t2-en"
set -u
M=~/dev/active/troncons/memoire
LISTE="${1:-t1-fr t1-en t2-fr t2-en}"
for nom in $LISTE; do
  tome="${nom%-*}"; L="${nom#*-}"
  case "$tome" in
    t1) dossier="$M/$L"; rc=../latexmkrc; maitre="troncons-memoire-$L"; rel="../essai/juge3/tomes/j3-$nom" ;;
    t2) dossier="$M/tome2/$L"; rc=../../latexmkrc; maitre="troncons-tome2-$L"; rel="../../essai/juge3/tomes/j3-$nom" ;;
    *) echo "nom inconnu : $nom"; exit 2 ;;
  esac
  mkdir -p "$M/essai/juge3/tomes/j3-$nom"
  debut=$(date +%s)
  echo "== j3-$nom : début $(date '+%H:%M:%S')"
  (cd "$dossier" && latexmk -r "$rc" -lualatex -outdir="$rel" -jobname="j3-$nom" "$maitre.tex" \
     > "$M/essai/juge3/tomes/j3-$nom.latexmk.txt" 2>&1)
  code=$?
  fin=$(date +%s)
  echo "== j3-$nom : fin $(date '+%H:%M:%S'), code $code, $(( (fin-debut)/60 )) min $(( (fin-debut)%60 )) s"
done
