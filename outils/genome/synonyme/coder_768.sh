#!/usr/bin/env bash
# Lot B, pas S1 : la mutation synonyme (λ = 1, δ* = 1) et la base frontière des 768 experts de
# gpt-oss-20b, par l'outil de l'éclaireur tel quel (outils/genome/eclaireur/synonyme.py ecrire-sym).
# Trois processus de couches (0-7, 8-15, 16-23), 4 fils OpenBLAS chacun. Une relance reprend : un
# fichier .sym déjà écrit est sauté par ecrire-sym.
# Usage : bash outils/genome/synonyme/coder_768.sh [synonyme|frontiere|renfort|synonyme-l0|renfort-l0]
# renfort (ajouté le 2026-10-17 vers 10 h 55, la passe KL frontière finie) : trois processus de plus,
# couches et experts descendants, qui rejoignent les trois premiers par l'autre bout ; un fichier
# déjà écrit est sauté. Mêmes 4 fils OpenBLAS (condition de la reproduction au bit, W1).
set -u
ICI="$(cd "$(dirname "$0")" && pwd)"
V=~/dev/lectures/venvs/genome-etat-de-l-art/Scripts/python
S="$ICI/../eclaireur/synonyme.py"
J="$ICI/../../../mesures/genome/construction/synonyme/codage"
D=~/dev/essais/troncons/genome/synonyme/sym
mkdir -p "$J" "$D"
quoi="${1:-synonyme}"
if [ "$quoi" = renfort ] || [ "$quoi" = renfort-l0 ]; then
  INV=$(seq -s, 31 -1 0)
  lam=1; [ "$quoi" = renfort-l0 ] && lam=0
  for g in "7,6,5,4" "15,14,13,12" "23,22,21,20"; do
    n="${g%%,*}"
    OPENBLAS_NUM_THREADS=4 "$V" -I -X utf8 "$S" ecrire-sym --variante synonyme --lam $lam --damp 1 --sortie "$D/synonyme-l$lam-d1" --couches "$g" --experts "$INV" 2>> "$J/synonyme-renfort-l$lam-$n.log" &
  done
  wait
  exit 0
fi
if [ "$quoi" = synonyme-l0 ]; then
  # λ = 0, δ* = 1 (B2 entre les deux λ, ajouté le 2026-10-17 après B0) : trois processus montants.
  for g in "0,1,2,3,4,5,6,7" "8,9,10,11,12,13,14,15" "16,17,18,19,20,21,22,23"; do
    n="${g%%,*}"
    OPENBLAS_NUM_THREADS=4 "$V" -I -X utf8 "$S" ecrire-sym --variante synonyme --lam 0 --damp 1 --sortie "$D/synonyme-l0-d1" --couches "$g" 2>> "$J/synonyme-l0-groupe-$n.log" &
  done
  wait
  exit 0
fi
if [ "$quoi" = frontiere ]; then
  OPENBLAS_NUM_THREADS=4 "$V" -I -X utf8 "$S" ecrire-sym --variante frontiere --sortie "$D/frontiere" 2> "$J/frontiere.log"
  exit $?
fi
for g in "0,1,2,3,4,5,6,7" "8,9,10,11,12,13,14,15" "16,17,18,19,20,21,22,23"; do
  n="${g%%,*}"
  OPENBLAS_NUM_THREADS=4 "$V" -I -X utf8 "$S" ecrire-sym --variante synonyme --lam 1 --damp 1 \
    --sortie "$D/synonyme-l1-d1" --couches "$g" 2>> "$J/synonyme-groupe-$n.log" &
done
wait
