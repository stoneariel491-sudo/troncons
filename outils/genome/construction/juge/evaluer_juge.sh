#!/usr/bin/env bash
# Juge de la construction : les passes `troncons evaluer --flux` sur les fenêtres neuves (J-C1 et J-K,
# chemin du moteur), sous le verrou de la carte et sur secteur. Seuils : 00-seuils-declares.md (1f5fe0f).
# Usage : bash outils/genome/construction/juge/evaluer_juge.sh <nom> <fichier.trc> [options du moteur…]
#   écrit $K/moteur-<nom>.kld, mesures/…/juge/logits/evaluer-<nom>.{json,log,csv}
set -u
ICI="$(cd "$(dirname "$0")" && pwd)"
J="$ICI/../../../../mesures/genome/construction/juge/logits"
K=~/dev/essais/troncons/genome/juge
T=~/dev/cibles/troncons-juge/release
BASE=~/dev/essais/troncons/genome/juge/base-juge-20b.kld
PY=~/dev/lectures/venvs/genome-genome/Scripts/python.exe
mkdir -p "$J"
nom="$1"; f="$2"; shift 2
"$PY" -I -X utf8 "$ICI/verrou_juge.py" prendre "évaluations du juge (logits au bit, KL ; pas une séance de vitesse), evaluer_juge.sh $nom" > /dev/null
al=$(powershell -NoProfile -Command "(Get-CimInstance Win32_Battery).BatteryStatus" | tr -d '\r')
[ "$al" = "2" ] || { echo "pas sur secteur ($al)"; exit 2; }
fen=10
for a in "$@"; do [ "$a" = "--une-fenetre" ] && fen=1; done
args=()
for a in "$@"; do [ "$a" != "--une-fenetre" ] && args+=("$a"); done
debut=$(date +%s)
"$T/troncons.exe" evaluer --flux --modele "$f" --base "$BASE" --fenetres "$fen" --sortie "$K/moteur-$nom.kld" \
  --empreintes "$J/evaluer-$nom.csv" --journal "$J/evaluer-$nom.json" "${args[@]}" > "$J/evaluer-$nom.log" 2>&1
code=$?
echo "$nom : code $code, $(( $(date +%s) - debut )) s (alimentation $al)"
exit $code
