#!/bin/sh
# Chaîne du sujet genome après les passes de poids : sortie des experts sur entrées réelles (et
# écriture des experts reconstruits), puis KL contre la référence f64, base contre recette.
B=~/dev/cibles/troncons-genome/release/genome-recette.exe
K=~/dev/cibles/troncons-genome-kl/release/genome-recette-kl.exe
JU=~/dev/cibles/troncons-R/release/juge.exe
G=~/dev/modeles/gguf/gpt-oss-20b-MXFP4.gguf
REF=~/dev/essais/troncons/lot-R/r1/ref-openai-20b.kld
J=~/dev/active/troncons/mesures/genome/genome
E=~/dev/essais/troncons/genome/genome
F=6
mkdir -p $E/kl-sub/vide $J/kl
if [ ! -s $J/sortie-tourne.json ]; then
  $B sortie --norme tourne --experts 0,8,16,24 --couches 0,8,16,23 --positions 512 \
    --csv $J/csv/codons-tourne-l12-rangees.csv --ecrire $E/kl-sub > $J/sortie-tourne.json 2> $J/sortie-tourne.log
fi
# témoin de la fourche : aucun expert substitué, une fenêtre ; la KL contre la référence doit être nulle
if [ ! -s $J/kl/temoin-vide.json ]; then
  $K kl --gguf $G --kld $REF --sub $E/kl-sub/vide --sortie $E/kl-vide.kld --fenetres 1 --fils 12 > $J/kl/temoin-vide-passe.json 2> $J/kl/temoin-vide.log
  $JU kl --base $REF --test $E/kl-vide.kld --fenetres 1 > $J/kl/temoin-vide.json 2>> $J/kl/temoin-vide.log
fi
for quoi in base recette recette-relatif; do
  if [ ! -s $J/kl/passe-$quoi.json ]; then
    $K kl --gguf $G --kld $REF --sub $E/kl-sub/$quoi --sortie $E/kl-$quoi.kld --fenetres $F --fils 12 > $J/kl/passe-$quoi.json 2> $J/kl/passe-$quoi.log
  fi
done
for quoi in recette recette-relatif; do
  $JU comparer --verite $REF --a $E/kl-base.kld --b $E/kl-$quoi.kld --fenetres $F --json $J/kl/comparer-base-contre-$quoi.json --csv $J/kl/comparer-base-contre-$quoi.csv > $J/kl/comparer-base-contre-$quoi.txt 2>&1
done
echo chaine-finie
