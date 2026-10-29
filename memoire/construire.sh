#!/usr/bin/env bash
# Construit les mémoires de troncons : Tome I (les fondations) et Tome II (le système),
# chacun en anglais et en français.
#   ./construire.sh                 régénère les données des figures, puis les quatre PDF
#   ./construire.sh en|fr           Tome I, une seule langue
#   ./construire.sh tome1           Tome I, les deux langues
#   ./construire.sh tome2           Tome II, les deux langues
#   ./construire.sh tome2-en|tome2-fr   Tome II, une seule langue
#   ./construire.sh tome3           Tome III (le génome des poids), les deux langues
#   ./construire.sh tome3-en|tome3-fr   Tome III, une seule langue
#   ./construire.sh propre          efface les fichiers intermédiaires des deux tomes
# Le Tome III n'entre ni dans la construction sans argument ni dans « propre » (ajouté le 2026-10-29 sans
# changer les cibles des Tomes I et II) ; ses fichiers intermédiaires s'effacent par latexmk -C dans
# memoire/tome3/en/ et memoire/tome3/fr/.
# Chaîne : MiKTeX (lualatex, biber, latexmk), Python 3.13 (bibliothèque standard seule).
# Le script échoue (code non nul) à la première erreur, à tout outil de données qui sort en
# erreur (les outils du Tome II refont leurs chiffres par un second chemin et tombent au premier
# écart), à toute référence ou citation manquante, à tout avertissement « undefined » dans les
# journaux, et à toute entrée que biber ne trouve pas ou trouve deux fois.
set -euo pipefail
ici="$(cd "$(dirname "$0")" && pwd)"

# Chaque cible : « dossier|fichier maître sans extension ».
t1=("en|troncons-memoire-en" "fr|troncons-memoire-fr")
t2=("tome2/en|troncons-tome2-en" "tome2/fr|troncons-tome2-fr")
t3=("tome3/en|troncons-tome3-en" "tome3/fr|troncons-tome3-fr")
# latexmkrc en chemin relatif au dossier de compilation (latexmk est un programme Windows : un
# chemin /c/... de Git Bash ne lui parle pas) : ../latexmkrc pour en/, ../../latexmkrc pour tome2/en/.
rcrel() { local d="$1" r=""; IFS=/ read -ra p <<< "$d"; for _ in "${p[@]}"; do r="../$r"; done; echo "${r}latexmkrc"; }

if [[ "${1:-}" == "propre" ]]; then
  for c in "${t1[@]}" "${t2[@]}"; do
    d="${c%%|*}"; m="${c##*|}"; rc="$(rcrel "$d")"
    (cd "$ici/$d" && latexmk -r "$rc" -C "$m.tex" >/dev/null || true)
  done
  exit 0
fi

tome3=0
case "${1:-}" in
  "")      cibles=("${t1[@]}" "${t2[@]}"); tome1=1; tome2=1 ;;
  en)        cibles=("${t1[0]}"); tome1=1; tome2=0 ;;
  fr)        cibles=("${t1[1]}"); tome1=1; tome2=0 ;;
  tome1)     cibles=("${t1[@]}"); tome1=1; tome2=0 ;;
  tome2)     cibles=("${t2[@]}"); tome1=0; tome2=1 ;;
  tome2-en)  cibles=("${t2[0]}"); tome1=0; tome2=1 ;;
  tome2-fr)  cibles=("${t2[1]}"); tome1=0; tome2=1 ;;
  tome3)     cibles=("${t3[@]}"); tome1=0; tome2=0; tome3=1 ;;
  tome3-en)  cibles=("${t3[0]}"); tome1=0; tome2=0; tome3=1 ;;
  tome3-fr)  cibles=("${t3[1]}"); tome1=0; tome2=0; tome3=1 ;;
  *) echo "cible inconnue : $1 (en, fr, tome1, tome2, tome2-en, tome2-fr, tome3, tome3-en, tome3-fr, propre)" >&2; exit 2 ;;
esac

if (( tome1 )); then
  python -I -X utf8 "$ici/outils/donnees_figures.py"
  python -I -X utf8 "$ici/outils/calculs_entropie.py"
  python -I -X utf8 "$ici/outils/annexes.py"
fi
if (( tome2 )); then
  # Données des figures et chiffres refaits du Tome II, puis les tables de ses annexes.
  python -I -X utf8 "$ici/outils/tome2_format.py"
  python -I -X utf8 "$ici/outils/tome2_chemin_noyaux.py"
  python -I -X utf8 "$ici/outils/tome2_reference_cache.py"
  python -I -X utf8 "$ici/outils/tome2_resultats.py"
  python -I -X utf8 "$ici/outils/tome2_annexes.py"
fi
if (( tome3 )); then
  # Données des figures du Tome III : les huit outils des lots (chacun tombe à sa première garde) ; leur
  # régénération redonne les fichiers commités au bit (memoire/tome3/JUGEMENT-figures3.md § 4.3). Ni
  # tome3_palette.py (il réécrit ses fichiers en CRLF, égaux au contenu seulement) ni tome3_cassures.py
  # (il force les gardes à faux) n'ont leur place dans une construction.
  for lot in eclaireur genome duplication synthese codon synonyme juge latents; do
    python -I -X utf8 "$ici/outils/tome3_$lot.py"
  done
  # Les quatre tables des annexes B et C, engendrées depuis git ls-files et git log (l'annexe B le demande ;
  # ajouté le 2026-10-29, grave G1 de memoire/tome3/JUGEMENT-redaction-fr.md).
  python -I -X utf8 "$ici/outils/tome3_annexes.py"
  # Les figures de la piste des spectres sont un document autonome (classe standalone) aux chemins de
  # données relatifs à son dossier, qui est en lecture seule : on le compile dans son dossier, sa sortie
  # sous memoire/tome3/pistes/ (ignoré par git), où le chapitre 12 prend ses pages (\FigureSpectres).
  mkdir -p "$ici/tome3/pistes"
  (cd "$ici/../genome/pistes/spectres/figures" && \
   lualatex -interaction=nonstopmode -halt-on-error -output-directory=../../../../memoire/tome3/pistes \
     spectres-figures.tex >/dev/null) || { echo "ÉCHEC : figures des spectres ($ici/tome3/pistes/spectres-figures.log)" >&2; exit 1; }
fi

for c in "${cibles[@]}"; do
  d="${c%%|*}"; m="${c##*|}"; rc="$(rcrel "$d")"
  echo "== mémoire $d/$m"
  (cd "$ici/$d" && latexmk -r "$rc" "$m.tex")
  journal="$ici/$d/$m.log"
  blg="$ici/$d/$m.blg"
  if grep -E "undefined|Undefined|There were undefined references|Citation .* undefined|Reference .* undefined" "$journal"; then
    echo "ÉCHEC : références ou citations manquantes dans $journal" >&2; exit 1
  fi
  if grep -E "File .* not found|Package pgfplots Error|could not be found" "$journal"; then
    echo "ÉCHEC : figure ou fichier de données absent ($journal)" >&2; exit 1
  fi
  if [[ -f "$blg" ]] && grep -E "^ERROR|WARN - (I didn't find|Duplicate)" "$blg"; then
    echo "ÉCHEC : biber signale une erreur ou une entrée absente ($blg)" >&2; exit 1
  fi
  pages=$(grep -oE "Output written on .*\(([0-9]+) pages" "$journal" | grep -oE "[0-9]+ pages" || true)
  echo "   PDF : $d/$m.pdf ($pages)"
done
