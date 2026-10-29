#!/bin/sh
# Lot du juge P5 : J1 (graine 1), J2 (graine 2026), J3 (regimes), temoins T1-T3, lambda 0,2 (graine 1).
cd "$(dirname "$0")"
M=../../../../mesures/mimetisme/P5/juge
mkdir -p $M/j1 $M/j2 $M/j3 $M/temoins $M/lam02
run() { out=$1; shift; [ -s "$out" ] || python -I -X utf8 juge_p5.py "$@" > "$out" 2> "$out.err"; }
for L in 0 8 16 23; do for E in 0 16; do
  t=$(printf "L%02d-E%02d" $L $E)
  run $M/j1/$t-g1.json --couche $L --expert $E --graine 1 --j0
  run $M/j2/$t-g2026.json --couche $L --expert $E --graine 2026
  run $M/temoins/zero-$t.json --couche $L --expert $E --graine 1 --temoin zero
  run $M/temoins/perm-$t.json --couche $L --expert $E --graine 1 --temoin perm
  for R in test2 plus inclus; do run $M/j3/$R-$t.json --couche $L --expert $E --graine 1 --regime $R; done
  run $M/lam02/$t-g1.json --couche $L --expert $E --graine 1 --lam 0.2
done; done
echo fini
