# Reprise : étude 02, quantification extrême des poids (avec perte)

Livrable : `fondations/02-quantification.md`. Outils : `outils/` (préfixe `quant-`).
Journaux : `fondations/journaux/02-quantification/`.
Clones de lecture : `~/dev/lectures/troncons/quantification/`.
Essais : `~/dev/essais/troncons/quantification/` (venv, gguf requantifiés, jamais dans le dépôt).

## Plan
1. Squelette du livrable + note. 
2. Lecteur GGUF maison (bits par poids réels, métadonnées comprises) sur les Q4_K_M locaux ; témoin = taille du fichier.
3. Échelle llama.cpp sur Qwen3.5-4B (et 9B) : imatrix, requantification depuis Q4_K_M (biais déclaré), perplexité wikitext-2, vitesse llama-bench, débit effectif vs 256 Go/s.
4. Reproduction indépendante des MSE publiés (QTIP tableau 1 : Lloyd-Max, E8, treillis) sur gaussienne i.i.d.
5. Lecture des sources primaires + code (licences), Vulkan oui/non par lecture des shaders.

## 2026-10-15
- Pas 1 : note de reprise posée.
- Reprise 01:13 (prédécesseur mort après pas 2). quant-echelle.sh commité (830a3ef).
- Pas 4 : outils/quant-mse-gaussien.py, témoin Lloyd-Max tient ; 1re cassure trop faible (journal gardé), 2e tombe. Passe complète en cours (treillis lent, numpy 1 fil).
- Pas 3 lancé : échelle 4B (imatrix 1038 s, carte partagée avec d'autres agents ; je gêne aussi l'étude 04).
- Lecture code : i-quants Vulkan oui (mul_mat_vec_iq*.comp, grilles en mémoire partagée) ; EXL3 vrai treillis CUDA seul ; IQn_KT d'ik = VQ dim 8 à graine 16 bits, pas un treillis, pas de Vulkan.
- Brouillon du livrable écrit (§ 0-3), § 4-10 à remplir après mesures.
- Vulkan llama.cpp b11515 (33 Mo) non téléchargé : mis en demande (exécutable).
- 02:10 : MSE treillis 2 bits refaite (0,068, = QTIP tab. 1). GEMV CUDA passe 2 : treillis 156 Go/s équiv., scalaire 2b 211, FP16 247 (carte partagée, paires propres).
- Échelle 4B relancée réduite (IQ2_XXS IQ3_XXS IQ2_M IQ1_S Q2_K IQ1_M Q2_0) puis 9B (IQ2_XXS IQ3_XXS IQ2_M IQ1_S IQ4_XS), sortie essais/.../echelle-suite.out. IQ4_XS 4B fait.
- Banc Vulkan/DX12 (wgpu) écrit : outils/quant-vulkan-gemv, cible essais/.../vulkan-target. Compilation en cours.
- Reste : vitesse llama-bench (quant-vitesse.py) en fin, § 4-6 et § 0 à finir avec les mesures.
- 03:05 : Vulkan passe 4 : treillis 124 Go/s équiv. (= 4 bits). FWHT Vulkan existe déjà dans llama.cpp (prism.hadamard) : phrase barrée.
- 4B fait : IQ4_XS, IQ3_XXS, IQ2_XXS. 9B imatrix 693 s ; IQ2_XXS, IQ2_M, IQ3_XXS en cours ; puis 4B IQ2_M, IQ1_S, Q2_K.
- 07:24 reprise (prédécesseur mort vers 04:07 ; machine probablement en veille entre-temps). llama-quantize 9B IQ2_M (pid 30544, lancé par le prédécesseur via quant-echelle.sh, pid bash 35704) vivant et progresse : laissé tourner, IQ3_XXS suivra. RAM libre ~0,5-1,2 Go (banc_rans de 03, carte de 01 thermique jusqu'à ~07:30).
- TABLE4B rempli. Reste : TABLE9B + § 5.2 quand IQ2_M/IQ3_XXS 9B finis ; vitesse llama-bench carte libre ; CSV + .bib + dérivations pour le mémoire ; veille sources oct. 2026.
- 07:30-08:30 : veille oct. 2026 (§ 3.8 : CurveTQ, Tetra, GSQ, XOR-Trellis, ApexQuant, Q-Palette...), § 0/6/7 corrigés (seuil 2 bits dépend du codeur ; trous 7-8). § 5.2 9B IQ2_XXS + IQ2_M (8,612 à 3,16 Go). Dérivations D1-D8 (02-quantification-derivations.md), CSV + figures pgfplots (memoire/figures, compilées lualatex OK), .bib (memoire/sources/quantification.bib ; biber se bloque sur la machine même pour --version : signalé).
- Vitesse passe 2 rejetée (seuil 5 %) : sous charge CPU tous les formats à ~28 t/s. À refaire machine calme, sans mmap (-mmp 0).
- Treillis par parités (sans multiplication) : outils/quant-mse-xor.py (témoin mul1 = 0,068236 exact, cassé tombe) en cours -> mse-xor-P4.json ; décodeur Vulkan/DX12 « treillis-parite » écrit, témoins tiennent ; mesure de vitesse à faire carte libre (--formats treillis-parite,treillis-mul1-dot4-v2).
- 9B IQ3_XXS : quantification finie ~08:2x, perplexité en cours ; puis TABLE9B-SUITE à remplacer.
- 08:20-09:00 : 9B complet (IQ3_XXS 7,91 à 3,49 Go ; croisement 4B/9B à 3,14 Go = 3,16 bits/poids lu), 4B complet (Q2_K, IQ2_M, IQ1_S). Treillis par parités : MSE 0,0712 (mul1 0,0682), Vulkan 52 Go/s contre 121 (comptage de bits domine ; sans table pareil). § 2.4 écrit. En cours : MSE à grille de gain élargie (mse-xor-P4-gain14, uniforme-gain16 : le gain optimal tombait au bord 1,05) ; vitesse passe 3 (-lm none --prio 2) -> vitesse-4B-3/9B-3.
- 09:20 ÉTAT : livrable complet (§ 0-10, § 2.4 et § 3.8 neufs), dérivations D1-D8, CSV + 6 figures pgfplots compilées, .bib. Vitesse passe 3 retenue. Gain du treillis vérifié intérieur.
- Restes possibles : base BF16 de Qwen3.5-4B (≈ 8 Go, à demander) pour ôter le biais de requantification ; vitesse en Vulkan de llama.cpp (exécutable b11515 Vulkan, 33 Mo, à demander) ; décodeur Vulkan à état initial par bloc (CurveTQ) ; essai du partage des bits selon l'étage (D6) sur un vrai modèle ; biber bloqué sur la machine.
- Livrable : § 0-4, 6-10 écrits ; § 5 a deux marqueurs TABLE4B / TABLE9B à remplacer par la sortie de quant-resume-echelle.py, et § 5.2 à écrire (iso-octets 9B-2/3 bits contre 4B-4 bits).
