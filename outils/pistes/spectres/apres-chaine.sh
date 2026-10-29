#!/usr/bin/env bash
# Piste spectres : lance le test de prédiction (seuil.md § 7 octies) une fois la chaîne `levier3 normalise`
# finie (« fin normalise » dans chaine.log), pour ne jamais dépasser 2 fils pour cette piste.
set -u
ICI="$(cd "$(dirname "$0")" && pwd)"
PY=~/dev/lectures/venvs/genome-genome/Scripts/python.exe
M="$ICI/../../../mesures/pistes/spectres"
until grep -q "fin normalise" "$M/chaine.log"; do sleep 60; done
echo "[$(date +%H:%M:%S)] début prediction-casse" >> "$M/chaine.log"
(cd "$ICI" && "$PY" -X utf8 prediction.py --casser > "$M/prediction-casse.out" 2> "$M/prediction-casse.log")
echo "[$(date +%H:%M:%S)] fin prediction-casse (code $?)" >> "$M/chaine.log"
echo "[$(date +%H:%M:%S)] début prediction" >> "$M/chaine.log"
(cd "$ICI" && "$PY" -X utf8 prediction.py > "$M/prediction.out" 2> "$M/prediction.log")
echo "[$(date +%H:%M:%S)] fin prediction (code $?)" >> "$M/chaine.log"
