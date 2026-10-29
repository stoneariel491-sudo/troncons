#!/bin/sh
# L'échantillon de D1, D2, D2b, D2c, T, O (seuils : mesures/genome/duplication/00-seuils-declares.md).
# Couche par couche, un processus à la fois (mémoire sous 6 Go).
P=~/dev/lectures/venvs/genome-duplication/Scripts/python
J=~/dev/active/troncons/mesures/genome/duplication
O=~/dev/active/troncons/outils/genome/duplication
CAPTURE=${CAPTURE:-~/dev/essais/troncons/genome/eclaireur/calib}
for L in "$@"; do
  $P -I -X utf8 $O/mutation.py --couche $L --enfants 0,8,16,24 --capture $CAPTURE > $J/mutation-c$L.json 2> $J/mutation-c$L.log
  echo "couche $L : code $?"
done
