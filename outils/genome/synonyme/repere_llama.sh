#!/usr/bin/env bash
# Lot B, critère B2 (ii) : le repère de l'outil de référence. La requantification llama.cpp b11515
# des seuls tenseurs d'experts en Q2_0 (2,25 bits par poids, groupes de 64 ; les k-quants et IQ, à
# super-blocs de 256, ne divisent pas 2 880), le reste inchangé ; logits des 10 premières fenêtres de
# wiki.test sur le processeur (mêmes options que la base « processeur » de R0), écrits au format .kld,
# puis `juge kl` contre la référence f64.
set -u
ICI="$(cd "$(dirname "$0")" && pwd)"
J="$ICI/../../../mesures/genome/construction/synonyme/repere"
L=~/dev/modeles/llama.cpp-b11515
K=~/dev/essais/troncons/genome/synonyme/llama
REF=~/dev/essais/troncons/lot-R/r1/ref-openai-20b.kld
mkdir -p "$J"
CUDA_VISIBLE_DEVICES=-1 "$L/llama-perplexity.exe" -m "$K/gpt-oss-20b-experts-q2_0.gguf" -ngl 0 -c 512 -b 512 -t 4 --seed 1 --chunks 10 \
  -f ~/dev/essais/troncons/modeles/donnees/wiki.test.raw --kl-divergence-base "$K/q2_0.kld" > "$J/perplexite-q2_0.log" 2>&1 || exit 1
~/dev/cibles/troncons-synonyme/release/juge.exe kl --base "$REF" --test "$K/q2_0.kld" --json "$J/kl-q2_0-juge.json" --csv "$J/kl-q2_0-positions.csv" > /dev/null 2> "$J/kl-q2_0-juge.log"
sha256sum "$K/q2_0.kld" "$K/gpt-oss-20b-experts-q2_0.gguf" > "$J/q2_0.sha256"
echo fini
