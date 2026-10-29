#!/bin/sh
# J5 (demi-calibration) puis PT numpy descriptif, sequentiels (2 fils au plus).
cd "$(dirname "$0")"
M=../../../../mesures/mimetisme/P5/juge
mkdir -p $M/j5 $M/pt
for L in 0 8 16 23; do for E in 0 16; do
  t=$(printf "L%02d-E%02d" $L $E)
  [ -s $M/j5/demi-$t.json ] || python -I -X utf8 juge_p5.py --couche $L --expert $E --graine 1 --regime demi > $M/j5/demi-$t.json 2> $M/j5/demi-$t.json.err
done; done
echo j5 fini
for c in "0 16" "8 0" "16 16" "23 0" "0 0" "8 16" "16 0" "23 16"; do
  set -- $c; t=$(printf "L%02d-E%02d" $1 $2)
  [ -s $M/pt/$t.json ] || python -I -X utf8 juge_pt.py --couche $1 --expert $2 > $M/pt/$t.json 2> $M/pt/$t.json.err
  echo pt $t
done
echo fini
