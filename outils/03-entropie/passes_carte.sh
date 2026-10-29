#!/usr/bin/env bash
# Passes de carte de l'étude 03, chacune dans sa propre fenêtre calme (attendre_calme.sh).
#   1. banc_gemv sur les codes MXFP4 réels de gpt-oss-20b : brut, fondu, décodage, deux passes ;
#   2. banc_rans, carte seule, sur les demi-octets Q4_K du 4B (débits v1 à v4) ;
#   3. banc_rans, carte seule, sur les codes MXFP4 de gpt-oss-20b (taux réel et débits),
#      limité aux 12 premiers tenseurs MXFP4 : les 72 tiendraient mal dans 16 Go de RAM.
# Usage : passes_carte.sh <suffixe des journaux>
suffixe="${1:-calme}"
racine=~/dev/active/troncons
j=$racine/fondations/journaux/03-entropie
bin=~/dev/essais/troncons/entropie/cible/release
attendre=$racine/outils/03-entropie/attendre_calme.sh
modeles=~/dev/modeles/gguf
bash "$attendre" carte "$j/calme-gemv-gptoss20b-$suffixe.log" \
  "$bin/banc_gemv.exe" "$modeles/gpt-oss-20b-MXFP4.gguf" "$j/gemv-gptoss20b-$suffixe.json" --lot-mo 256 --passes 5
bash "$attendre" carte "$j/calme-rans-4B-$suffixe.log" \
  "$bin/banc_rans.exe" "$modeles/Qwen3.5-4B-Q4_K_M.gguf" "$j/rans-4B-$suffixe.json" --lot-mo 256 --passes 5 --sans-processeur
bash "$attendre" carte "$j/calme-rans-gptoss20b-$suffixe.log" \
  "$bin/banc_rans.exe" "$modeles/gpt-oss-20b-MXFP4.gguf" "$j/rans-gptoss20b-$suffixe.json" --lot-mo 256 --passes 5 --sans-processeur --type 39 --max-tenseurs 12
