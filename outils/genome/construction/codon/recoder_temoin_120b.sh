#!/usr/bin/env bash
# Séance s2 du lot A (codon) : le v1.0 du 120b recodé aujourd'hui par trc-codeur (témoin d'identité du
# codeur modifié sur le 120b, et témoin de disposition pour le J1), ses fragments, puis le pilote.
set -u
R=~/dev/active/troncons
J=$R/mesures/genome/construction/codon/journaux
G=~/dev/modeles/gguf
DST=~/dev/modeles/trc/temoin-codon/gpt-oss-120b-v10-recode.trc
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a $J/recode-temoin-120b.log; }
mkdir -p ~/dev/modeles/trc/temoin-codon
log "recodage v1.0 du 120b vers $DST"
powershell -NoProfile -File $R/outils/genome/construction/codon/lancer.ps1 coder-120b-v10-recode coder $G/gpt-oss-120b-MXFP4.gguf $DST --fils 6 --date 2026-10-15 --sha256-attendu 582bd40f6886200101f4c4ed9f25f3fe80cc14c86e9e2b37746cd8904a0c622d --journal $J/coder-120b-v10-recode.json; log "code $?"
h=$(powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA256 '$DST').Hash.ToLower()"); log "SHA-256 recodé : $h ; v1.0 d'origine 6c7b5f1d09429ecf4339a206ca86da9ccb5d1f1b7b15c6d354b0a0409720dcce"
if [ "$h" != 6c7b5f1d09429ecf4339a206ca86da9ccb5d1f1b7b15c6d354b0a0409720dcce ]; then log "identité 120b TOMBE : arrêt"; exit 1; fi
log "identité 120b TIENT"
n=$(fsutil file queryextents "$(cygpath -w $DST)" | wc -l); log "fragments du recodé : $n"
cd $R && python -I -X utf8 outils/genome/construction/codon/pilote_codon.py --phases disque,j1-copie --seance s2 --fichier-c $DST; log "pilote code $?"
