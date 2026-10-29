#!/usr/bin/env bash
# Témoin de la disposition sur le disque (lot A, codon) : copie neuve du v1.0 du 120b, SHA-256 des deux
# fichiers par Get-FileHash (chemin indépendant), puis les phases disque et j1-copie du pilote.
set -u
R=~/dev/active/troncons
J=$R/mesures/genome/construction/codon/journaux
SRC=~/dev/modeles/trc/gpt-oss-120b.trc
DST=~/dev/essais/troncons/codon/gpt-oss-120b-copie-v10.trc
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a $J/copie-temoin.log; }
hache() { powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA256 '$1').Hash.ToLower()"; }
log "copie de $SRC vers $DST"
t0=$(date +%s); cp "$SRC" "$DST"; log "copie code $? en $(( $(date +%s) - t0 )) s"
a=$(hache "$SRC"); b=$(hache "$DST"); log "SHA-256 origine $a ; copie $b"
if [ "$a" != "$b" ]; then log "copie DIFFÉRENTE : arrêt"; exit 1; fi
log "copie égale ; phases disque et j1-copie"
cd $R && python -I -X utf8 outils/genome/construction/codon/pilote_codon.py --phases disque,j1-copie --seance s1; log "pilote code $?"
