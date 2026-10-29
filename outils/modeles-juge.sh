#!/usr/bin/env bash
# Juge de qualité léger, identique pour tous les modèles et tous les moteurs.
# Usage : modeles-juge.sh <modèle.gguf> <étiquette> <dossier-sortie> [base-logits.kld]
#   Sans 4e argument : écrit les logits de référence (base) dans <sortie>/<étiquette>.kld.
#   Avec : mesure la divergence KL contre cette base (même texte, mêmes fenêtres).
# Variables : LLAMA (dossier des binaires), DONNEES (textes fixés), NGL (couches sur la carte,
# 0 par défaut), THREADS, CHUNKS_PPL (40), CHUNKS_KLD (10), N_TACHES (400), N_MC (0 = toutes les
# questions MMLU et ARC). Mesuré ici le 2026-10-15 : la perplexité dépend du moteur (processeur seul
# contre produits matriciels déchargés sur la carte) ; NGL et le moteur se figent pour une série.
# Seuils et textes déclarés dans fondations/06-modeles.md, section « Protocole de jugement ».
set -euo pipefail
M="$1"; ETQ="$2"; OUT="$3"; BASE="${4:-}"
LLAMA="${LLAMA:-~/dev/modeles/llama.cpp-b11515}"
DONNEES="${DONNEES:-~/dev/essais/troncons/modeles/donnees}"
NGL="${NGL:-0}"; THREADS="${THREADS:-6}"
CHUNKS_PPL="${CHUNKS_PPL:-40}"; CHUNKS_KLD="${CHUNKS_KLD:-10}"; N_TACHES="${N_TACHES:-400}"; N_MC="${N_MC:-0}"
MC=(); if [ "$N_MC" != "0" ]; then MC=(--multiple-choice-tasks "$N_MC"); fi
mkdir -p "$OUT"
P="$LLAMA/llama-perplexity.exe"
COMMUN=(-m "$M" -ngl "$NGL" -t "$THREADS" -c 512 -b 512 --seed 1)
journal() { echo "== $(date '+%F %T') $*" | tee -a "$OUT/$ETQ.resume.txt"; }

sha256sum "$M" "$DONNEES"/* >> "$OUT/$ETQ.empreintes.txt"
journal "perplexité wikitext-2 test, c=512, $CHUNKS_PPL fenêtres"
"$P" "${COMMUN[@]}" -f "$DONNEES/wiki.test.raw" --chunks "$CHUNKS_PPL" > "$OUT/$ETQ.ppl.log" 2>&1
grep -E "Final estimate" "$OUT/$ETQ.ppl.log" | tee -a "$OUT/$ETQ.resume.txt"

if [ -z "$BASE" ]; then
  journal "logits de référence, $CHUNKS_KLD fenêtres"
  "$P" "${COMMUN[@]}" -f "$DONNEES/wiki.test.raw" --chunks "$CHUNKS_KLD" \
      --kl-divergence-base "$OUT/$ETQ.kld" > "$OUT/$ETQ.kldbase.log" 2>&1
else
  journal "divergence KL contre $BASE"
  "$P" "${COMMUN[@]}" --kl-divergence-base "$BASE" --kl-divergence > "$OUT/$ETQ.kld.log" 2>&1
  grep -E "Mean    KLD|Maximum KLD|99.9%   KLD|Same top p|Mean    PPL\(Q\)|Mean ln\(PPL\(Q\)/PPL\(base\)\)" \
      "$OUT/$ETQ.kld.log" | tee -a "$OUT/$ETQ.resume.txt"
fi

journal "HellaSwag, $N_TACHES tâches"
"$P" "${COMMUN[@]}" -f "$DONNEES/hellaswag_val_full.txt" --hellaswag --hellaswag-tasks "$N_TACHES" \
    > "$OUT/$ETQ.hellaswag.log" 2>&1
grep -E "^$N_TACHES\s" "$OUT/$ETQ.hellaswag.log" | tail -1 | tee -a "$OUT/$ETQ.resume.txt"

journal "Winogrande, $N_TACHES tâches"
"$P" "${COMMUN[@]}" -f "$DONNEES/winogrande-debiased-eval.csv" --winogrande --winogrande-tasks "$N_TACHES" \
    > "$OUT/$ETQ.winogrande.log" 2>&1
grep -E "Final Winogrande score" "$OUT/$ETQ.winogrande.log" | tee -a "$OUT/$ETQ.resume.txt"

journal "MMLU validation (choix multiples, toutes les questions)"
"$P" "${COMMUN[@]}" -bf "$DONNEES/mmlu-validation.bin" --multiple-choice "${MC[@]}" \
    > "$OUT/$ETQ.mmlu.log" 2>&1
grep -E "Final result" "$OUT/$ETQ.mmlu.log" | tee -a "$OUT/$ETQ.resume.txt"

journal "ARC (facile + défi) validation"
"$P" "${COMMUN[@]}" -bf "$DONNEES/arc-combined-validation.bin" --multiple-choice "${MC[@]}" \
    > "$OUT/$ETQ.arc.log" 2>&1
grep -E "Final result" "$OUT/$ETQ.arc.log" | tee -a "$OUT/$ETQ.resume.txt"
journal "fin"
