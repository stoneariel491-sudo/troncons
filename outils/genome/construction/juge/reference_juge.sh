#!/usr/bin/env bash
# Juge de la construction : la référence f64 des fenêtres neuves, puis la référence f64 substituée
# (le chemin des lots, genome-capture kl --sub) pour λ = 0, la frontière et λ = 1, dans cet ordre.
# Processeur seulement. Se met en pause tant qu'un autre flux tient le verrou pour une séance de vitesse.
# Seuils : 00-seuils-declares.md (1f5fe0f). Usage : bash reference_juge.sh [reference|sub-l0|sub-frontiere|sub-l1 …]
set -u
ICI="$(cd "$(dirname "$0")" && pwd)"
J="$ICI/../../../../mesures/genome/construction/juge/kl"
K=~/dev/essais/troncons/genome/juge
T=~/dev/cibles/troncons-juge/release
G=~/dev/modeles/gguf/gpt-oss-20b-MXFP4.gguf
SYM=~/dev/essais/troncons/genome/synonyme/sym
V=~/dev/verrou-carte.txt
FILS=6
mkdir -p "$J"
pause_vitesse() {
  while [ -e "$V" ] && grep -q "vitesse" "$V" && ! grep -q "juge construction" "$V" && [ $(( $(date +%s) - $(stat -c %Y "$V") )) -lt 7200 ]; do
    echo "[$(date '+%F %T')] pause : $(cat "$V")"; sleep 60
  done
}
for etape in "$@"; do
  pause_vitesse
  debut=$(date +%s)
  case "$etape" in
    reference)
      "$T/juge.exe" reference --gguf "$G" --jetons-de "$K/base-juge-20b.kld" --sortie "$K/ref-juge-20b.kld" --fenetres 10 \
        --yarn openai --fils "$FILS" --journal "$J/ref-juge-20b.json" --kl-contre-base --routage "$J/routage-ref-juge-20b.bin" \
        > "$J/ref-juge-20b.log" 2>&1 ;;
    sub-l0|sub-frontiere|sub-l1)
      d=$( [ "$etape" = sub-l0 ] && echo synonyme-l0-d1 || { [ "$etape" = sub-l1 ] && echo synonyme-l1-d1 || echo frontiere; } )
      "$T/genome-capture.exe" kl --gguf "$G" --kld "$K/ref-juge-20b.kld" --sub "$SYM/$d" --sortie "$K/$etape.kld" --fils "$FILS" \
        > "$J/$etape.json.tmp" 2> "$J/$etape.log" && mv "$J/$etape.json.tmp" "$J/$etape.json" ;;
    *) echo "étape inconnue $etape"; exit 2 ;;
  esac
  code=$?
  echo "[$(date '+%F %T')] $etape : code $code, $(( $(date +%s) - debut )) s"
  [ $code -eq 0 ] || exit $code
done
