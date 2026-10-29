#!/usr/bin/env bash
# Lot B, pas S2 : la KL de bout en bout d'un dossier de .sym substitués (768 experts), sur les 10
# fenêtres de R1, par la référence f64 (genome-capture kl), puis `juge kl` contre la référence.
# Usage : bash outils/genome/synonyme/kl_passe.sh <nom> <dossier .sym> [fils]
set -u
ICI="$(cd "$(dirname "$0")" && pwd)"
J="$ICI/../../../mesures/genome/construction/synonyme/kl"
C=~/dev/cibles/troncons-synonyme/release
K=~/dev/essais/troncons/genome/synonyme/kl
REF=~/dev/essais/troncons/lot-R/r1/ref-openai-20b.kld
mkdir -p "$J" "$K"
nom="$1"; sub="$2"; fils="${3:-4}"
if [ ! -s "$J/kl-$nom.json" ]; then
  "$C/genome-capture.exe" kl --gguf ~/dev/modeles/gguf/gpt-oss-20b-MXFP4.gguf --kld "$REF" \
    --sub "$sub" --sortie "$K/$nom.kld" --fils "$fils" > "$J/kl-$nom.json.tmp" 2> "$J/kl-$nom.log" \
    && mv "$J/kl-$nom.json.tmp" "$J/kl-$nom.json" || exit 1
fi
"$C/juge.exe" kl --base "$REF" --test "$K/$nom.kld" --json "$J/kl-$nom-juge.json" --csv "$J/kl-$nom-positions.csv" > /dev/null 2> "$J/kl-$nom-juge.log"
sha256sum "$K/$nom.kld" > "$J/kl-$nom.sha256"
echo "fini $nom"
