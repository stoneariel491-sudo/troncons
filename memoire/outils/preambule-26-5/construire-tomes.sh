#!/usr/bin/env bash
# Construit les tomes complets avec le préambule réparé, sans toucher les PDF commités :
# sorties sous memoire/essai/construction-tomes/<nom><suffixe>/, nom de travail distinct de celui du maître
# (LuaTeX efface le PDF du nom de travail dans le dossier courant malgré -outdir : le PDF commité ne porte
# pas ce nom).
# Usage : construire-tomes.sh langue (fr|en) [suffixe] [ordre]   ordre : « t1 t2 » (défaut) ou « t2 t1 ».
set -u
M=~/dev/active/troncons/memoire
L="$1"
SUF="${2:-}"
ORDRE="${3:-t1 t2}"
for tome in $ORDRE; do
  case "$tome" in
    t1) dossier="$M/$L"; rc=../latexmkrc; maitre="troncons-memoire-$L" ;;
    t2) dossier="$M/tome2/$L"; rc=../../latexmkrc; maitre="troncons-tome2-$L" ;;
  esac
  nom="$tome-$L"
  sortie="$M/essai/construction-tomes/$nom$SUF"
  rel=$(python -I -c "import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]).replace(os.sep,'/'))" "$sortie" "$dossier")
  mkdir -p "$sortie"
  debut=$(date +%s)
  echo "== $nom$SUF : début $(date '+%H:%M:%S'), dossier $dossier, sortie $rel"
  (cd "$dossier" && latexmk -r "$rc" -lualatex -outdir="$rel" -jobname="$nom" "$maitre.tex" > "$sortie.latexmk.txt" 2>&1)
  code=$?
  fin=$(date +%s)
  echo "== $nom$SUF : fin $(date '+%H:%M:%S'), code $code, $(( (fin-debut)/60 )) min $(( (fin-debut)%60 )) s"
done
