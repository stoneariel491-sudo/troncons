#!/usr/bin/env bash
# Les passes de la mutation synonyme, dans l'ordre déclaré (genome/REPRISE-etat-de-l-art.md).
# Chaque passe écrit son journal JSON et son CSV par (couche, expert, rôle) sous
# mesures/genome/etat-de-l-art/ ; une passe déjà écrite n'est pas refaite (reprise après une mort).
# Usage : bash outils/genome/eclaireur/passes.sh [liste de passes « variante:lam:damp » ...]
set -u
ICI="$(cd "$(dirname "$0")" && pwd)"
V=~/dev/lectures/venvs/genome-etat-de-l-art/Scripts/python
M="$ICI/../../../mesures/genome/etat-de-l-art"
mkdir -p "$M/passes"
PASSES=("$@")
if [ ${#PASSES[@]} -eq 0 ]; then
  PASSES=(frontiere:0:0.01 synonyme:0:0.01 frontiere1:0:0.01 synonyme1:0:0.01 ecsq:0.5:0.01 ecsq:1:0.01 ecsq:2:0.01 synonyme:0.5:0.01 synonyme:1:0.01 synonyme:2:0.01 synonyme:0:0.1)
fi
for p in "${PASSES[@]}"; do
  IFS=: read -r var lam damp <<< "$p"
  nom="$var-lam$lam-damp$damp${SYN_EXPERTS:+-e${SYN_EXPERTS//,/_}}"
  if [ -s "$M/passes/$nom.json" ]; then echo "déjà : $nom"; continue; fi
  echo "passe $nom : $(date +%H:%M:%S)"
  OPENBLAS_NUM_THREADS=4 "$V" -I -X utf8 "$ICI/synonyme.py" mesurer --variante "$var" --lam "$lam" --damp "$damp" \
    --csv "$M/passes/$nom.csv" > "$M/passes/$nom.json.tmp" 2> "$M/passes/$nom.log" && mv "$M/passes/$nom.json.tmp" "$M/passes/$nom.json"
done
echo "fini : $(date +%H:%M:%S)"
