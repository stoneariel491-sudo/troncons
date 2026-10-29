#!/bin/sh
# Passe K du sujet genome : la base et la recette S* (pondérée, exceptions 0,1 %, 2,64 bits) substituées aux experts 0 et 16
# des couches 0, 8, 16, 23 dans la référence f64 ; 3 fenêtres ; puis `juge comparer`.
K=~/dev/cibles/troncons-genome-kl/release/genome-recette-kl.exe
JU=~/dev/cibles/troncons-R/release/juge.exe
G=~/dev/modeles/gguf/gpt-oss-20b-MXFP4.gguf
REF=~/dev/essais/troncons/lot-R/r1/ref-openai-20b.kld
J=~/dev/active/troncons/mesures/genome/genome/kl
E=~/dev/essais/troncons/genome/genome
F=3
for quoi in base-8 recette-ponderee-exc-264; do
  if [ ! -s $J/passe-$quoi.json ]; then
    $K kl --gguf $G --kld $REF --sub $E/kl-sub/$quoi --sortie $E/kl-$quoi.kld --fenetres $F --fils 12 > $J/passe-$quoi.json 2> $J/passe-$quoi.log
  fi
done
for quoi in base-8 recette-ponderee-exc-264; do
  $JU kl --base $REF --test $E/kl-$quoi.kld --fenetres $F > $J/kl-$quoi.json 2>&1
done
$JU comparer --verite $REF --a $E/kl-base-8.kld --b $E/kl-recette-ponderee-exc-264.kld --fenetres $F --json $J/comparer-base-contre-recette.json --csv $J/comparer-base-contre-recette.csv > $J/comparer-base-contre-recette.txt 2>&1
echo kl-fini
