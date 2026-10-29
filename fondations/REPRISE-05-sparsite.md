# Reprise : étude 05, lire moins d'octets par jeton (sparsité, prédiction, spéculation)

Livrable : `fondations/05-sparsite.md` (complet, § 0-11). Outils : `outils/05-sparsite/`
(+ `outils/sparsite-inventaire-gguf.py`). Journaux : `fondations/journaux/05-sparsite/`.
Clones de lecture : `~/dev/lectures/troncons/sparsite/` (llama.cpp creux,
subspec, specexec, TEAL). Essais : `~/dev/essais/troncons/sparsite/` (venv
numpy, SmolLM2-135M F16, test.ids/train.ids, base-9B.kld 1 Go, qwen35-9B-Q2_K.gguf).

## État au 2026-10-15
- Passe avant numpy llama F16 + témoin llama-perplexity (seuil 0,5 %) ; mode cassé tombe.
- `amortissement.py` : E(α,k), unions d'experts, cas machine (dense, MoE, substitut,
  substitut mesuré) ; témoin par simulation, mode cassé tombe.
- Mesuré : unions de masques (stats-smol.json), ppl de 12 règles (ppl-smol.json),
  énergie gardée (energie-smol.json), accords gloutons 4B->9B 76,8 %, 9B Q2_K 34 %,
  témoin 100 % ; c(n) 4B indicative (bruit > seuil, machine partagée).
- Témoin 16 fenêtres de la passe avant : RÉUSSI (22,6768 contre 22,6739, max 0,18 %).

## Suite possible
- Avec accord de Stone : unsloth/Qwen3.5-9B-MTP-GGUF Q4_K_M (5,87 Go) -> accord du MTP
  natif, débit `draft-mtp` ; AtomicChat/Qwen3.5-9B-DFlash-GGUF (1,38 Go) ; un MoE
  (Qwen3.6-35B-A3B UD-Q4_K_M 22,13 Go) pour la courbe d'union d'experts réelle (il faut
  journaliser les top-k du routeur : construire llama-eval-callback CPU depuis la source).
- c(n) à refaire machine au repos (seuil 10 %), et en -ngl 0 (poids par PCIe, lot >= 32).
- imatrix du 9B puis IQ2_XXS/IQ3_XXS du 9B -> accord du substitut sur le 9B lui-même.
