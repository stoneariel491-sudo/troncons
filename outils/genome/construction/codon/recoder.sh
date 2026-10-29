#!/usr/bin/env bash
# Lot A (codon) : recodage v1.2 et vérification C1 des deux modèles, dans l'ordre.
#   1. témoin d'identité : le 20b recodé SANS --canonique par ce codeur modifié = gpt-oss-20b.trc de
#      F2 octet pour octet (SHA-256 e8bd6ae1…169f, mesures/moteur/F/journaux/identite-20b-2passes.txt),
#      par Get-FileHash (chemin indépendant) ; la copie est ensuite retirée (fichier de ce rôle).
#   2. 20b --canonique → gpt-oss-20b-v12.trc ; verifier ; cassures --casser et --casser-8.
#   3. 120b --canonique → gpt-oss-120b-v12.trc ; verifier.
# Usage : bash outils/genome/construction/codon/recoder.sh [20b|120b|tout]
set -u
R=~/dev/active/troncons
L="powershell -NoProfile -File $R/outils/genome/construction/codon/lancer.ps1"
G=~/dev/modeles/gguf
T=~/dev/modeles/trc
J=~/dev/active/troncons/mesures/genome/construction/codon/journaux
SHA20=27cd6c432c7672cb812a92f611cf3ba7bbc35928262bb1e1253ff4ee6ae35901
SHA120=582bd40f6886200101f4c4ed9f25f3fe80cc14c86e9e2b37746cd8904a0c622d
QUOI=${1:-tout}
mkdir -p $R/mesures/genome/construction/codon/journaux
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a $R/mesures/genome/construction/codon/journaux/recoder.log; }
hache() { powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA256 '$1').Hash.ToLower()"; }
if [ "$QUOI" = 20b ] || [ "$QUOI" = tout ]; then
  mkdir -p $T/temoin-codon
  log "1. identité v1.0 (20b)"
  $L coder-20b-v10-identite coder $G/gpt-oss-20b-MXFP4.gguf $T/temoin-codon/gpt-oss-20b-v10-identite.trc --fils 6 --date 2026-10-15 --sha256-attendu $SHA20 --journal $J/coder-20b-v10-identite.json; log "code $?"
  h=$(hache $T/temoin-codon/gpt-oss-20b-v10-identite.trc); log "SHA-256 recodé v1.0 : $h ; attendu e8bd6ae13288344d0ab29b70dd311e0045769624651b56e943ca39a878c7169f"
  if [ "$h" = e8bd6ae13288344d0ab29b70dd311e0045769624651b56e943ca39a878c7169f ]; then log "identité TIENT"; rm -f $T/temoin-codon/gpt-oss-20b-v10-identite.trc; else log "identité TOMBE (copie gardée)"; fi
  log "2. 20b v1.2"
  $L coder-20b-v12 coder $G/gpt-oss-20b-MXFP4.gguf $T/gpt-oss-20b-v12.trc --canonique --fils 6 --date 2026-10-17 --sha256-attendu $SHA20 --journal $J/coder-20b-v12.json; log "code $?"
  $L verifier-20b-v12 verifier $T/gpt-oss-20b-v12.trc $G/gpt-oss-20b-MXFP4.gguf --fils 6 --journal $J/verifier-20b-v12.json; log "verifier code $?"
  $L verifier-20b-v12-casse verifier $T/gpt-oss-20b-v12.trc $G/gpt-oss-20b-MXFP4.gguf --fils 6 --sans-sha --casser 5 7 --journal $J/verifier-20b-v12-casse.json; log "cassure médiane code $? (0 = exactement l'expert visé)"
  $L verifier-20b-v12-casse-8 verifier $T/gpt-oss-20b-v12.trc $G/gpt-oss-20b-MXFP4.gguf --fils 6 --sans-sha --casser-8 11 3 --journal $J/verifier-20b-v12-casse-8.json; log "cassure −0 code $? (0 = exactement l'expert visé, même valeur, octets faux)"
  h=$(hache $T/gpt-oss-20b-v12.trc); log "SHA-256 gpt-oss-20b-v12.trc : $h"
fi
if [ "$QUOI" = 120b ] || [ "$QUOI" = tout ]; then
  log "3. 120b v1.2"
  $L coder-120b-v12 coder $G/gpt-oss-120b-MXFP4.gguf $T/gpt-oss-120b-v12.trc --canonique --fils 6 --date 2026-10-17 --sha256-attendu $SHA120 --journal $J/coder-120b-v12.json; log "code $?"
  $L verifier-120b-v12 verifier $T/gpt-oss-120b-v12.trc $G/gpt-oss-120b-MXFP4.gguf --fils 6 --journal $J/verifier-120b-v12.json; log "verifier code $?"
  h=$(hache $T/gpt-oss-120b-v12.trc); log "SHA-256 gpt-oss-120b-v12.trc : $h"
fi
log "fin ($QUOI)"
