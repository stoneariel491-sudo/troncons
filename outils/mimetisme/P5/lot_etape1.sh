#!/bin/bash
# Les 8 instances (couches 0,8,16,23 x experts 0,16) pour un amortissement donne. 2 fils, priorite normale.
# usage : lot_etape1.sh DAMP
cd ~/dev/active/troncons
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
DAMP=$1
for l in 0 8 16 23; do for e in 0 16; do
  f=mesures/mimetisme/P5/etape1/L$(printf %02d $l)-E$(printf %02d $e)-d$DAMP.json
  [ -s "$f" ] && continue
  python -I -X utf8 outils/mimetisme/P5/etape1.py une --couche $l --expert $e --lignes 64 --damp $DAMP --lams 0 0.2 --sweeps 40 --trempe 30 > "$f.tmp" 2> "$f.err" && mv "$f.tmp" "$f"
done; done
