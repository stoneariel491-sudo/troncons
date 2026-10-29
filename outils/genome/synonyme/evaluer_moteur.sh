#!/usr/bin/env bash
# Lot B, S3-K et S3-KL : la KL du moteur (carte, f32) sur les 10 fenêtres de R1, sous le verrou de la
# carte et sur secteur ; puis `juge kl` contre la référence f64.
# Usage : bash outils/genome/synonyme/evaluer_moteur.sh <nom> <fichier.trc> [--rapide]
set -u
ICI="$(cd "$(dirname "$0")" && pwd)"
J="$ICI/../../../mesures/genome/construction/synonyme/moteur"
K=~/dev/essais/troncons/genome/synonyme/kl
T=~/dev/cibles/troncons-synonyme/release
REF=~/dev/essais/troncons/lot-R/r1/ref-openai-20b.kld
L=~/dev/verrou-carte.txt
mkdir -p "$J" "$K"
nom="$1"; f="$2"; shift 2
while [ -e "$L" ] && [ $(( $(date +%s) - $(stat -c %Y "$L") )) -lt 7200 ]; do echo "verrou : $(cat $L)"; sleep 60; done
echo "lot B synonyme, $(date '+%F %T'), evaluer_moteur.sh $nom, pid $$" > "$L"
trap 'grep -q "evaluer_moteur.sh" "$L" 2>/dev/null && rm -f "$L"' EXIT
al=$(powershell -NoProfile -Command "(Get-CimInstance Win32_Battery).BatteryStatus" | tr -d '\r')
[ "$al" = "2" ] || { echo "pas sur secteur ($al)"; exit 2; }
"$T/troncons.exe" evaluer --modele "$f" --base "$REF" --fenetres 10 --sortie "$K/moteur-$nom.kld" --journal "$J/evaluer-$nom.json" "$@" > "$J/evaluer-$nom.log" 2>&1 || exit 1
"$T/juge.exe" kl --base "$REF" --test "$K/moteur-$nom.kld" --json "$J/kl-moteur-$nom-juge.json" --csv "$J/kl-moteur-$nom-positions.csv" > /dev/null 2> "$J/kl-moteur-$nom-juge.log"
sha256sum "$K/moteur-$nom.kld" > "$J/moteur-$nom.sha256"
echo "fini $nom (alimentation $al)"
