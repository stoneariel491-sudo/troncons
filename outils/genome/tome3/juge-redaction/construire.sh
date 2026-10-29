#!/usr/bin/env bash
# Juge de la rédaction du Tome III (français) : construit le tome assemblé par assembler.py, comme
# memoire/construire.sh tome3-fr le construit (même latexmkrc, même maître, mêmes contrôles du journal),
# mais dans memoire/essai/juge-redaction-fr-<état>/ (ignoré par git) : rien n'est écrit sous
# memoire/tome3/. Les huit outils de données des figures ne sont pas relancés (ils écrivent des fichiers
# commités qui ne sont pas au juge ; leur régénération au bit est jugée par JUGEMENT-figures3.md § 4.3) ;
# le PDF des spectres est celui que construire.sh a déjà compilé sous memoire/tome3/pistes/.
# Usage : bash construire.sh brouillon|tete
set -uo pipefail
ici="$(cd "$(dirname "$0")" && pwd)"
depot="$(cd "$ici/../../../.." && pwd)"
etat="${1:?état : brouillon ou tete}"
d="$depot/memoire/essai/juge-redaction-fr-$etat"
m="troncons-tome3-fr"
[[ -f "$d/$m.tex" ]] || { echo "rien d'assemblé dans $d" >&2; exit 2; }
[[ -f "$depot/memoire/tome3/pistes/spectres-figures.pdf" ]] || { echo "PDF des spectres absent" >&2; exit 2; }
cd "$d"
rm -f "$m.fdb_latexmk" "$m.aux" "$m.bbl" "$m.bcf" "$m.toc" "$m.lof" "$m.lot" "$m.lol" "$m.run.xml"
debut=$(date +%s)
latexmk -r ../../latexmkrc "$m.tex" > latexmk-sortie.txt 2>&1
code=$?
fin=$(date +%s)
echo "latexmk : code $code, $(( fin - debut )) s" | tee resultat.txt
{
  echo "== erreurs (lignes « ! » et « :NN: » du journal)"
  grep -nE "^!|^[^ ]+\.tex:[0-9]+:" "$m.log" | head -40
  echo "== renvois et citations indéfinis"
  grep -E "undefined|Undefined|There were undefined references|Citation .* undefined|Reference .* undefined" "$m.log" | sort | uniq -c
  echo "== fichiers ou figures absents"
  grep -E "File .* not found|Package pgfplots Error|could not be found" "$m.log"
  echo "== biber"
  grep -E "^ERROR|WARN" "$m.blg"
  echo "== boîtes trop pleines"
  grep -c "^Overfull" "$m.log"
  echo "== pages"
  grep -oE "Output written on .*\(([0-9]+) pages" "$m.log"
} >> resultat.txt 2>&1
cat resultat.txt
exit $code
