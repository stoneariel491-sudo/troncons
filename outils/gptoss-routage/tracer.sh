#!/usr/bin/env bash
# Relève les traces de routage de gpt-oss (20b ou 120b) sur le corpus en quatre genres, puis sur
# l'invite fixée de la base (étude 06) avec la même génération gloutonne que la base, pour le témoin
# G5 (taux de succès publié par le cache d'experts de llama.cpp contre notre simulation).
#
# Configuration : toutes les couches en carte, experts dans un tampon de l'hôte (mmap), cache
# d'experts de llama.cpp de 4 096 Mio en VRAM : la configuration « cache » de la base.
# Lecture par lots de 1 024 jetons (sortie de tous les jetons, voir traceur.cpp) ; pour l'invite
# de la base, lots de 512 jetons, la taille de micro-lot par défaut de llama-completion.
#
# Usage : [OPTS="--sans-op-offload"] [GENRES="prose-en prose-fr dialogue code"] [GENERER=256]
#         [ETAPES="corpus wiki"] tracer.sh 20b|120b <dossier de sortie>
# (GENRES, GENERER, ETAPES ajoutés le 2026-10-15 pour la reprise de 120b : la génération de prose-fr
#  s'est enlisée plus de deux heures sous la pression mémoire d'autres programmes ; la reprise relève
#  dialogue et code en lecture seule, GENERER=0, puis l'invite de la base)
# (120b : --sans-op-offload, sinon chaque lot de 1 024 jetons copie les 61 Go d experts vers la carte
#  par fautes de page à ~170 Mo/s, 12 min par lot mesurées le 2026-10-15)
set -euo pipefail
taille=$1
sortie=$2
DLL="~/dev/modeles/llama.cpp-b11515"
export PATH="~/dev/modeles/llama.cpp-b11515:$PATH"
EXE="~/dev/essais/troncons/gpt-oss/construction/traceur.exe"
MOD="~/dev/modeles/gguf/gpt-oss-${taille}-MXFP4.gguf"
CORPUS="$(cd "$(dirname "$0")/../../mesures/localite-gpt-oss/corpus" && pwd)"
INVITE="~/dev/essais/troncons/modeles/donnees/invite-wiki-3000.txt"
GENRES=${GENRES:-prose-en prose-fr dialogue code}
GENERER=${GENERER:-256}
ETAPES=${ETAPES:-corpus wiki}
args_textes=()
for g in $GENRES; do args_textes+=(--texte "$g=$CORPUS/$g.txt"); done
mkdir -p "$sortie"
echo "alimentation : $(powershell -NoProfile -Command '(Get-CimInstance Win32_Battery).BatteryStatus') (2 = secteur) $(date '+%F %T')"
if [[ " $ETAPES " == *" corpus "* ]]; then
  "$EXE" --dll-dir "$DLL" --modele "$MOD" --prefixe "$sortie/t$taille" --ctx 4096 --lot 1024 --ngl 99 \
    --cpu-moe --moe-cache-mib 4096 --threads 6 ${OPTS:-} --invite 256 --generer "$GENERER" \
    "${args_textes[@]}" 2>&1 | grep --line-buffered -v "^load:"
  echo "alimentation : $(powershell -NoProfile -Command '(Get-CimInstance Win32_Battery).BatteryStatus') $(date '+%F %T')"
fi
if [[ " $ETAPES " == *" wiki "* ]]; then
  "$EXE" --dll-dir "$DLL" --modele "$MOD" --prefixe "$sortie/w$taille" --ctx 2048 --lot 512 --ngl 99 \
    --cpu-moe --moe-cache-mib 4096 --threads 6 ${OPTS:-} --invite 100000 --generer 256 \
    --texte wiki="$INVITE" 2>&1 | grep --line-buffered -v "^load:"
  echo "alimentation : $(powershell -NoProfile -Command '(Get-CimInstance Win32_Battery).BatteryStatus') $(date '+%F %T')"
fi
