#!/bin/sh
# Passe K du sujet genome : la base et la recette S* (pondérée, exceptions 0,1 %, 2,64 bits) substituées aux experts 0 et 16
# des couches 0, 8, 16, 23 dans la référence f64 ; 10 fenêtres (K10) ; puis `juge comparer`.
K=~/dev/cibles/troncons-genome-kl/release/genome-recette-kl.exe
JU=~/dev/cibles/troncons-R/release/juge.exe
G=~/dev/modeles/gguf/gpt-oss-20b-MXFP4.gguf
REF=~/dev/essais/troncons/lot-R/r1/ref-openai-20b.kld
J=~/dev/active/troncons/mesures/genome/genome/kl
E=~/dev/essais/troncons/genome/genome
F=10
for quoi in base-8 recette-ponderee-exc-264; do
  if [ ! -s $J/passe10-$quoi.json ]; then
    $K kl --gguf $G --kld $REF --sub $E/kl-sub/$quoi --sortie $E/kl10-$quoi.kld --fenetres $F --fils 12 > $J/passe10-$quoi.json 2> $J/passe10-$quoi.log
  fi
done
for quoi in base-8 recette-ponderee-exc-264; do
  $JU kl --base $REF --test $E/kl10-$quoi.kld --fenetres $F > $J/kl10-$quoi.json 2>&1
done
$JU comparer --verite $REF --a $E/kl10-base-8.kld --b $E/kl10-recette-ponderee-exc-264.kld --fenetres $F --json $J/comparer10-base-contre-recette.json --csv $J/comparer10-base-contre-recette.csv > $J/comparer10-base-contre-recette.txt 2>&1
echo kl10-fini
