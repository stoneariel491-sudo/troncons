#!/bin/bash
# Addendum 3 : variation de N. usage : lot_regime.sh REGIME
cd ~/dev/active/troncons
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
R=$1
mkdir -p mesures/mimetisme/P5/etape1-regime
for l in 0 8 16 23; do for e in 0 16; do
  f=mesures/mimetisme/P5/etape1-regime/$R-L$(printf %02d $l)-E$(printf %02d $e).json
  [ -s "$f" ] && continue
  python -I -X utf8 outils/mimetisme/P5/etape1.py une --couche $l --expert $e --lignes 64 --damp 1 --regime $R --lams 0 --sweeps 0 --trempe 30 > "$f.tmp" 2> "$f.err" && mv "$f.tmp" "$f"
done; done
