#!/usr/bin/env bash
# Échelle de quantification llama.cpp sur un modèle : imatrix, requantification vers
# chaque type, bits par poids réels, divergence KL et perplexité contre la base.
#
# Usage : quant-echelle.sh <base.gguf> <nom> <dossier_essais> <journal_dir> [types...]
#
# La base sert de référence pour la divergence KL (logits sauvegardés sur KLD_CHUNKS
# morceaux de 512 jetons du jeu de test wikitext-2). L'imatrix se calcule sur le jeu
# d'entraînement wikitext-2 (disjoint du test, même domaine : biais optimiste déclaré).
# Si la base est déjà quantifiée (Q4_K_M), la requantification exige
# --allow-requantize : l'erreur mesurée est celle de base -> type, pas BF16 -> type.
set -u
BIN=~/dev/modeles/llama.cpp-b11515
OUTILS=$(cd "$(dirname "$0")" && pwd)
DONNEES=~/dev/essais/troncons/quantification/donnees/wikitext-2-raw
BASE=$1; NOM=$2; ESS=$3; JOUR=$4; shift 4
TYPES=("$@")
KLD_CHUNKS=${KLD_CHUNKS:-40}
IMAT_CHUNKS=${IMAT_CHUNKS:-128}
NGL=${NGL:-99}
mkdir -p "$ESS" "$JOUR"

horodate() { date +%s.%N; }

IMAT="$ESS/$NOM-imatrix.gguf"
if [ ! -f "$IMAT" ]; then
  t0=$(horodate)
  "$BIN/llama-imatrix.exe" -m "$BASE" -f "$DONNEES/wiki.train.raw" --chunks "$IMAT_CHUNKS" \
    -ngl "$NGL" -o "$IMAT" > "$JOUR/$NOM-imatrix.log" 2>&1
  t1=$(horodate)
  echo "imatrix $NOM secondes $(python -I -c "print(round($t1-$t0,1))")" >> "$JOUR/$NOM-durees.txt"
fi

KLB="$ESS/$NOM-base.kld"
if [ ! -f "$KLB" ]; then
  "$BIN/llama-perplexity.exe" -m "$BASE" -f "$DONNEES/wiki.test.raw" --chunks "$KLD_CHUNKS" \
    -ngl "$NGL" --kl-divergence-base "$KLB" > "$JOUR/$NOM-base-ppl.log" 2>&1
fi

for T in "${TYPES[@]}"; do
  Q="$ESS/$NOM-$T.gguf"
  if [ ! -f "$Q" ]; then
    t0=$(horodate)
    "$BIN/llama-quantize.exe" --allow-requantize --imatrix "$IMAT" "$BASE" "$Q" "$T" 16 \
      > "$JOUR/$NOM-$T-quantize.log" 2>&1 || { echo "ECHEC quantize $T"; continue; }
    t1=$(horodate)
    echo "quantize $NOM $T secondes $(python -I -c "print(round($t1-$t0,1))")" >> "$JOUR/$NOM-durees.txt"
  fi
  python -I "$OUTILS/quant-gguf-bits.py" "$Q" > "$JOUR/$NOM-$T-bits.json"
  if [ ! -f "$JOUR/$NOM-$T-kld.log" ]; then
    "$BIN/llama-perplexity.exe" -m "$Q" -f "$DONNEES/wiki.test.raw" --chunks "$KLD_CHUNKS" \
      -ngl "$NGL" --kl-divergence-base "$KLB" --kl-divergence > "$JOUR/$NOM-$T-kld.log" 2>&1
  fi
done
echo "fini $NOM"
