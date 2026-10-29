#!/usr/bin/env bash
# Construit les Tomes I et II par latexmk seul, sur les fichiers engendrés tels que commités.
w="$1"
for c in "en|troncons-memoire-en|../latexmkrc" "fr|troncons-memoire-fr|../latexmkrc" "tome2/en|troncons-tome2-en|../../latexmkrc" "tome2/fr|troncons-tome2-fr|../../latexmkrc"; do
  IFS='|' read -r d m rc <<< "$c"
  (cd "$w/memoire/$d" && latexmk -r "$rc" "$m.tex" >/dev/null 2>&1); echo "$d/$m code $?"
  grep -oE "Output written on .*\(([0-9]+) pages" "$w/memoire/$d/$m.log" | grep -oE "[0-9]+ pages"
  grep -cE "undefined|Undefined" "$w/memoire/$d/$m.log"
  grep -c "^! " "$w/memoire/$d/$m.log"
done
