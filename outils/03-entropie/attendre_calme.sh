#!/usr/bin/env bash
# Lance une commande seulement quand la machine est calme, trois relevés de suite à
# 10 s d'écart.
#   mode « processeur » : charge du processeur sous 20 % et aucun processus llama-*.
#     Le seuil dérive de la charge relevée machine au repos ce jour (9 à 18 %) ; au-dessus,
#     la recopie mémoire d'un fil est tombée de 9 à 0,3 Go/s (journal 03-entropie).
#   mode « carte » : puissance tirée par la carte sous 12 W (nvidia-smi), et aucun des
#     programmes de llama.cpp qui calculent sur la carte (bench, perplexity, cli,
#     completion, server, imatrix). Leçon du 2026-10-15 : un llama-bench lancé par un
#     autre agent pendant la passe « calme » a divisé la recopie de la carte par deux ;
#     la condition d'entrée seule ne suffit pas, d'où le relevé de fin, qui dit si la
#     passe est restée seule. llama-quantize calcule sur le processeur : il ne compte pas.
#     Seuil : d'abord « utilisation sous 5 % ». Barré : au repos (état P8, 210 MHz),
#     l'utilisation affichée oscille de 0 à 20 % (échantillons du 2026-10-15 à 08:34,
#     `echantillons-carte-secteur.csv`), parce qu'elle se rapporte à l'horloge basse ; une
#     passe a attendu plus de 20 min. La puissance ne trompe pas : 5,45 à 5,61 W au repos dans les
#     mêmes échantillons, plus de 40 W pour un llama-bench ou nos bancs. Seuil : 12 W,
#     le double du repos, très au-dessous de tout calcul.
# Le journal note aussi l'alimentation (secteur ou batterie), la limite de puissance de
# la carte et ses horloges, au début et à la fin : sur batterie, la limite tombe de 80 à
# 43 W et l'horloge mémoire de 8001 à 6001 MHz (relevé du 2026-10-15), ce qui change les
# débits sans que rien d'autre ne tourne.
# Usage : attendre_calme.sh <processeur|carte> <journal> <commande...>
mode="$1"; journal="$2"; shift 2
etat_machine() {
  local secteur
  secteur=$(powershell -NoProfile -c "(Get-CimInstance Win32_Battery).BatteryStatus" 2>/dev/null | tr -dc '0-9')
  # BatteryStatus : 1 = décharge (batterie), 2 = sur secteur (classe Win32_Battery)
  case "$secteur" in 1) secteur="batterie" ;; 2) secteur="secteur" ;; *) secteur="inconnu($secteur)" ;; esac
  local carte_etat
  carte_etat=$(nvidia-smi --query-gpu=utilization.gpu,power.limit,clocks.sm,clocks.mem --format=csv,noheader 2>/dev/null | tr -d '\r')
  echo "alimentation=$secteur carte[util,limite,horloge_sm,horloge_mem]=$carte_etat"
}
calmes=0
while [ $calmes -lt 3 ]; do
  charge=$(powershell -NoProfile -c "(Get-CimInstance Win32_Processor).LoadPercentage" 2>/dev/null | tr -dc '0-9')
  llama=$(tasklist 2>/dev/null | grep -c -i "llama-")
  llama_carte=$(tasklist 2>/dev/null | grep -c -i -E "llama-(bench|perplexity|cli|completion|server|imatrix|batched)")
  carte=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>/dev/null | tr -dc '0-9')
  puissance=$(nvidia-smi --query-gpu=power.draw --format=csv,noheader,nounits 2>/dev/null | tr -dc '0-9.' | cut -d. -f1)
  ok=0
  if [ "$mode" = "carte" ]; then
    [ -n "$puissance" ] && [ "$puissance" -lt 12 ] && [ "$llama_carte" -eq 0 ] && ok=1
  else
    [ -n "$charge" ] && [ "$charge" -lt 20 ] && [ "$llama" -eq 0 ] && ok=1
  fi
  if [ $ok -eq 1 ]; then calmes=$((calmes + 1)); else calmes=0; fi
  sleep 10
done
{
  echo "debut $(date '+%F %T') mode=$mode charge=${charge}% carte=${carte}% puissance=${puissance}W llama=${llama} llama_carte=${llama_carte} $(etat_machine)"
  "$@"
  charge=$(powershell -NoProfile -c "(Get-CimInstance Win32_Processor).LoadPercentage" 2>/dev/null | tr -dc '0-9')
  llama_carte=$(tasklist 2>/dev/null | grep -c -i -E "llama-(bench|perplexity|cli|completion|server|imatrix|batched)")
  echo "fin $(date '+%F %T') charge=${charge}% llama=$(tasklist 2>/dev/null | grep -c -i 'llama-') llama_carte=${llama_carte} $(etat_machine)"
} >> "$journal" 2>&1
