#!/bin/sh
# File des passes du sujet genome, lancées l'une après l'autre (chacune prend tous les fils).
B=~/dev/cibles/troncons-genome-dev/release/genome-recette.exe
J=~/dev/active/troncons/mesures/genome/genome
for cfg in "8 3 16" "12 4 16" "10 3 16" "12 3 16" "14 4 16" "16 5 16" "16 4 16" "12 2 16" "8 1 16"; do
  $B graines $cfg hache 32 >> $J/graines.jsonl 2>> $J/graines.log
done
$B graines 8 3 16 lfsr 32 >> $J/graines.jsonl 2>> $J/graines.log
for cfg in "8 8 3" "8 12 2" "4 10 1"; do
  $B motifs $cfg > $J/motifs-$(echo $cfg | tr ' ' '-').json 2> $J/motifs-$(echo $cfg | tr ' ' '-').log
done
echo file-finie
