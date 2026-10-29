#!/usr/bin/env bash
# Passes de carte de l'étude 03, machine sur secteur (relevé à 08:33 le 2026-10-15 :
# Win32_Battery = 2, horloges 2 250 / 8 101 MHz), chacune dans sa fenêtre calme.
#
# Ordre ABBA au niveau des processus, pour comparer deux chemins indépendants du même
# décodeur v4 sur le même flux :
#   A = rans_v4.exe (CUDA, événements de la carte)    B = banc_rans.exe (Vulkan, wgpu)
#   A B B A, puis banc_gemv (GEMV MXFP4), puis banc_rans sur les codes MXFP4 de gpt-oss-20b.
# Un échantillonneur nvidia-smi (toutes les 500 ms) tourne pendant toute la chaîne :
# utilisation, horloges, puissance, état. Ses relevés disent, après coup, si une passe
# est restée seule et à quelle horloge elle a tourné.
# Usage : passes_secteur.sh <suffixe>
suffixe="${1:-secteur}"
racine=~/dev/active/troncons
j=$racine/fondations/journaux/03-entropie
bin=~/dev/essais/troncons/entropie/cible/release
cuda=~/dev/essais/troncons/entropie/cuda/rans_v4.exe
flux=~/dev/essais/troncons/entropie/flux-4B
attendre=$racine/outils/03-entropie/attendre_calme.sh
modeles=~/dev/modeles/gguf
nvidia-smi --query-gpu=timestamp,utilization.gpu,clocks.sm,clocks.mem,power.draw,pstate \
  --format=csv -lms 500 > "$j/echantillons-carte-$suffixe.csv" &
echantillonneur=$!
bash "$attendre" carte "$j/calme-cuda-A1-$suffixe.log" "$cuda" "$flux" 5 "$j/cuda-4B-A1-$suffixe.json"
bash "$attendre" carte "$j/calme-rans-4B-B1-$suffixe.log" \
  "$bin/banc_rans.exe" "$modeles/Qwen3.5-4B-Q4_K_M.gguf" "$j/rans-4B-B1-$suffixe.json" --lot-mo 256 --passes 5 --sans-processeur
bash "$attendre" carte "$j/calme-rans-4B-B2-$suffixe.log" \
  "$bin/banc_rans.exe" "$modeles/Qwen3.5-4B-Q4_K_M.gguf" "$j/rans-4B-B2-$suffixe.json" --lot-mo 256 --passes 5 --sans-processeur
bash "$attendre" carte "$j/calme-cuda-A2-$suffixe.log" "$cuda" "$flux" 5 "$j/cuda-4B-A2-$suffixe.json"
bash "$attendre" carte "$j/calme-gemv-gptoss20b-$suffixe.log" \
  "$bin/banc_gemv.exe" "$modeles/gpt-oss-20b-MXFP4.gguf" "$j/gemv-gptoss20b-$suffixe.json" --lot-mo 256 --passes 5
bash "$attendre" carte "$j/calme-rans-gptoss20b-$suffixe.log" \
  "$bin/banc_rans.exe" "$modeles/gpt-oss-20b-MXFP4.gguf" "$j/rans-gptoss20b-$suffixe.json" --lot-mo 256 --passes 5 --sans-processeur --type 39 --max-tenseurs 12
kill $echantillonneur
