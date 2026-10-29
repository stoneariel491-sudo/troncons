#!/usr/bin/env bash
# Piste spectres : enchaîne les calculs, sans jamais démarrer pendant une séance de vitesse.
# Une séance de vitesse = verrou de la carte de moins de 2 h qui nomme vitesse, abba ou j1.
# Chaque script Python garde en plus la pause entre deux matrices (commun.attendre_calme).
# Utilisation : bash chaine.sh [étape ...]   (étapes : puissance temoins ajuster second levier)
set -u
ICI="$(cd "$(dirname "$0")" && pwd)"
PY=~/dev/lectures/venvs/genome-genome/Scripts/python.exe
M="$ICI/../../../mesures/pistes/spectres"
VERROU=~/dev/verrou-carte.txt

calme() {
  [ -f "$VERROU" ] || return 0
  local age=$(( $(date +%s) - $(stat -c %Y "$VERROU") ))
  [ "$age" -gt 7200 ] && return 0
  sed 's/pas une séance de vitesse//' "$VERROU" | grep -qiE "vitesse|abba|j1" && return 1
  return 0
}

ancien_actif() {   # le levier v1 orphelin écrit-il encore ? (voir commun.processus_ancien_actif)
  [ -n "${TRONCONS_ATTENDRE_ACTIF:-}" ] && [ -f "$TRONCONS_ATTENDRE_ACTIF" ] || return 1
  [ $(( $(date +%s) - $(stat -c %Y "$TRONCONS_ATTENDRE_ACTIF") )) -lt 180 ]
}

attendre() {
  while ! calme || ancien_actif; do sleep 30; done
}

# Le levier v2 (2026-10-22) ne peut pas être arrêté : sa garde attend tant que levier.out a moins de
# 3 min. On le garde endormi en rafraîchissant la date de levier.out (contenu inchangé) pendant le v3.
endormir_v2() {
  rm -f "$M/reveil-v2"
  ( while [ ! -f "$M/reveil-v2" ]; do touch "$M/levier.out"; sleep 60; done ) &
}
reveiller_v2() { : > "$M/reveil-v2"; }

lancer() {   # lancer <nom> <args...>
  local nom="$1"; shift
  attendre
  echo "[$(date +%H:%M:%S)] début $nom" >> "$M/chaine.log"
  (cd "$ICI" && "$PY" -X utf8 "$@" > "$M/$nom.out" 2> "$M/$nom.log")
  echo "[$(date +%H:%M:%S)] fin $nom (code $?)" >> "$M/chaine.log"
}

for e in "${@:-puissance temoins ajuster second levier}"; do
  for etape in $e; do
    case "$etape" in
      puissance) lancer puissance-critere puissance_critere.py ;;
      temoins)   lancer temoins temoins.py ; lancer temoins-casse temoins.py --casser ;;
      ajuster)   lancer ajustements ajuster.py ;;
      second)    lancer second-chemin-v2 second_chemin.py ;;
      levier)    lancer levier-temoin levier.py --temoin-plante ; lancer levier-v2 levier.py ;;
      normalise) lancer normalise normalise.py ;;
      l3)        lancer levier-l3-temoin levier_l3.py --temoin-plante ; lancer levier-l3 levier_l3.py ;;
      levier3)   endormir_v2 ; lancer levier-temoin-v3 levier.py --temoin-plante ; lancer levier-v3 levier.py ; reveiller_v2 ;;
    esac
  done
done
