#!/bin/bash
# Exploration (addendum 2) : cible diagonale de l'amortissement, Babai et CD seulement. usage : lot_diag.sh CIBLE DAMP
cd ~/dev/active/troncons
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
C=$1; DAMP=$2
mkdir -p mesures/mimetisme/P5/etape1-diag
for l in 0 8 16 23; do for e in 0 16; do
  f=mesures/mimetisme/P5/etape1-diag/$C-L$(printf %02d $l)-E$(printf %02d $e)-d$DAMP.json
  [ -s "$f" ] && continue
  python -I -X utf8 outils/mimetisme/P5/etape1.py une --couche $l --expert $e --lignes 64 --damp $DAMP --cible $C --lams 0 --sweeps 0 --trempe 30 > "$f.tmp" 2> "$f.err" && mv "$f.tmp" "$f"
done; done
