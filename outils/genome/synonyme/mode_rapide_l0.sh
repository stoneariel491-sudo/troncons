#!/usr/bin/env bash
# Lot B, après B2 (λ = 0 meilleure à 768 experts, 2026-10-21) : le compagnon rapide de la variante λ = 0,
# sa vérification S3-T1 (et sa cassure), la KL du moteur (S3-KL, sous le verrou, evaluer_moteur.sh) et
# S3-K (référence f64 rapide λ = 0 contre moteur rapide λ = 0 ; cassure : référence f64 frontière).
# Mêmes outils et réglages que pour λ = 1 (rapide/coder-synonyme.json). Une étape faite est sautée.
# Usage (racine du dépôt) : bash outils/genome/synonyme/mode_rapide_l0.sh
set -u
ICI="$(cd "$(dirname "$0")" && pwd)"
R="$ICI/../../../mesures/genome/construction/synonyme"
T=~/dev/cibles/troncons-synonyme/release
E=~/dev/essais/troncons/genome/synonyme
EX=~/dev/modeles/trc/gpt-oss-20b.trc
SYM=~/dev/essais/troncons/genome/synonyme/sym/synonyme-l0-d1
RAP=~/dev/essais/troncons/genome/synonyme/trc/gpt-oss-20b-synonyme-l0.rapide.trc
if [ ! -s "$R/rapide/coder-synonyme-l0.json" ]; then
  "$T/trc-rapide.exe" coder --exact "$EX" --symboles "$SYM" --sortie "$RAP" --variante synonyme --lambda 0 --amortissement 1 \
    --calibration "wiki.test fenêtres 10 à 21 (6 132 positions), captures de l'éclaireur" --fils 3 \
    --journal "$R/rapide/coder-synonyme-l0.json" > "$R/rapide/coder-synonyme-l0.log" 2>&1 || { echo "coder : échec"; exit 1; }
fi
if [ ! -s "$R/rapide/verifier-synonyme-l0.json" ]; then
  "$T/trc-rapide.exe" verifier --rapide "$RAP" --exact "$EX" --symboles "$SYM" --fils 3 \
    --journal "$R/rapide/verifier-synonyme-l0.json" > "$R/rapide/verifier-synonyme-l0.log" 2>&1
fi
if [ ! -s "$R/rapide/verifier-synonyme-l0-casse.json" ]; then
  "$T/trc-rapide.exe" verifier --rapide "$RAP" --exact "$EX" --symboles "$SYM" --fils 3 --casser 11 27 \
    --journal "$R/rapide/verifier-synonyme-l0-casse.json" > "$R/rapide/verifier-synonyme-l0-casse.log" 2>&1
fi
grep -q '"tient": true' "$R/rapide/verifier-synonyme-l0.json" || { echo "S3-T1 ne tient pas : arrêt"; exit 1; }
if [ ! -s "$R/moteur/kl-moteur-synonyme-l0-juge.json" ]; then
  bash "$ICI/evaluer_moteur.sh" synonyme-l0 "$RAP" --rapide || { echo "evaluer : échec"; exit 1; }
fi
K=$E/kl
"$T/juge.exe" kl --base "$K/synonyme-l0-768.kld" --test "$K/moteur-synonyme-l0.kld" --json "$R/moteur/S3K-capture-contre-moteur-synonyme-l0.json" \
  --csv "$R/moteur/S3K-capture-contre-moteur-synonyme-l0.csv" > /dev/null 2>&1
"$T/juge.exe" kl --base "$K/frontiere-768.kld" --test "$K/moteur-synonyme-l0.kld" --json "$R/moteur/S3K-casse-capture-frontiere-contre-moteur-synonyme-l0.json" \
  --csv "$R/moteur/S3K-casse-capture-frontiere-contre-moteur-synonyme-l0.csv" > /dev/null 2>&1
echo "fini"
