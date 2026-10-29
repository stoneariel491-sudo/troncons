# Lot B, le génome synonyme : ce qu'il faut au mémoire (Tome III)

Rôle « synonyme » de la construction, 2026-10-17. Livrable : genome/07-genome-synonyme.md. Les
chiffres viennent des journaux commités sous `mesures/genome/construction/synonyme/` ; aucun n'est
recopié de mémoire. Étiquettes : [mes.], [calc.], [litt.], [hyp.].

## 1. Place dans le chapitre

D'où on part : la mutation synonyme mesurée sur 32 experts sur 768 (01 § 5-6 ; 05 § 1.3). Ce que
l'étape établit : la même variante sur **les 768 experts**, sa KL de bout en bout, et le mode rapide
servi par le moteur (fichier compagnon, noyau, option). Ce qui reste : voir 07, § « Ce qui reste ».

## 2. Dérivations à porter en entier

### 2.1 Le choix des symboles (rappel, 01 § 5.2, mot pour mot dans le code)

Pour une ligne w ∈ ℝ^C d'une matrice et H = E[g² x xᵀ]/E[g²] (+ δ* moy(diag H) I, δ* = 1), le
coût de sortie d'une reconstruction q est (w − q)ᵀ H (w − q). Avec U triangulaire supérieure,
Uᵀ U = H⁻¹ (obtenue par une seule factorisation : P H P = L Lᵀ, U = P L⁻¹ P), la colonne j choisit

  k_j = argmin_k (|w̃_j| − c_k s_b)² + λ c̄ U_jj² ℓ(±, k),   ℓ = −log₂ p (loi de la frontière du tenseur),

puis reporte ε_j = ±(|w̃_j| − c_k s_b)/U_jj sur les colonnes suivantes : w̃_F ← w̃_F − ε_j U_{j,F}.
c̄ = tr(ΔW_F H ΔW_Fᵀ)/(R C) pour la frontière de la même matrice : λ se lit en « fractions de l'erreur
moyenne d'un poids par bit ». λ = 1.

### 2.2 L'identité qui fait la figure F-S1 (base propre de H)

tr(ΔW H ΔWᵀ) = Σ_k λ_k ‖ΔW u_k‖², (u_k, λ_k) les couples propres de H. Démonstration : H = Σ λ_k u_k u_kᵀ,
donc tr(ΔW H ΔWᵀ) = Σ_k λ_k tr(ΔW u_k u_kᵀ ΔWᵀ) = Σ_k λ_k ‖ΔW u_k‖². ∎ La mutation synonyme abaisse
Σ λ_k e_k en **déplaçant** l'énergie e_k = ‖ΔW u_k‖² vers les petites λ_k, au prix d'une énergie
totale Σ e_k plus grande (erreur sur les poids plus haute). Mesuré sur L8 E0 gate
(`figures/spectre-L08-E00-gate.csv`) [mes.] : Σ e_k 40,07 → 48,01 (+20 %), Σ λ_k e_k en calibration
16,50 → 6,15 (÷2,7), avec la loi de l'évaluation (u_kᵀ H_ev u_k) 16,09 → 10,28 (÷1,57) : l'écart entre
÷2,7 et ÷1,57 est le sur-apprentissage résiduel (01 § 5.4 : « le synonyme d'un échantillon n'est pas
le synonyme de la loi »).

### 2.3 Proposition B1 (le mode rapide ne touche pas le mode exact)

Le noyau `gemv_4_lignes` est paramétré par le lecteur des valeurs V (`gemv.cuh`). Pour
V = ValeurE2M1, la suite des fmaf (opérandes et ordre) est celle d'avant l'ajout : même valeur
`valeur_e2m1x2(c)` pour chaque demi-octet, même ordre (mot t, octet k, faible puis fort), même
réduction papillon. Les sorties du mode exact sont donc identiques au bit (témoin de carte : mode
exact avant et après un passage en mode rapide, mêmes octets ; test
`gemv_base_exacte_au_bit_et_mode_exact_inchange`). Le décodeur rANS ne lit pas les valeurs des
symboles (ARCHITECTURE § 4.9) : un fichier rapide se décode par le même noyau, les mêmes LUT, la même
grille.

### 2.4 Proposition B2 (gemv_base est déterministe et exact sur un témoin)

Même découpage et même ordre que `gemv_mxfp4` ; la valeur v(c) = ±c_{c & 3} est choisie par
sélections (aucune lecture indexée, aucune divergence de mémoire). Témoin : centres multiples de 0,5,
échelles dans [2^-11, 2^-5], x ∈ {−2, …, 2} : chaque terme est un multiple de 2^-12 d'au plus 0,75 ;
une ligne de 2 880 termes reste sous 2 160 < 2^12 ; 12 + 12 = 24 bits : la somme est exacte en f32
dans tout ordre, la carte doit égaler la référence f64 au bit. Mesuré : 0 ligne différente sur 2 880.

### 2.5 Le format du compagnon (au bit près)

Voir 07 § 3 (tableau des champs). Points à dessiner : l'en-tête (drapeaux bit 0 ALIGNÉ + bit 5
RAPIDE, version 1.2), la section TABLES (DELTA, CODES_CTX × 3, CENTRES par (couche, matrice)), le
demi-octet de base (bit 3 signe, bit 2 nul, bits 1-0 classe), la correspondance colonne → demi-octet
dans un bloc MXFP4 (octet t : colonnes 32b + t et 32b + 16 + t).

## 3. CSV et journaux pour les figures

- `figures/spectre-L08-E00-gate.csv` : k, λ_k (calibration), u_kᵀ H_ev u_k, e_k frontière, e_k synonyme.
- `kl/kl-{frontiere,synonyme,synonyme-l0}-768-positions.csv` (par position : fenetre, position, kl, meme_premier, nll) et `kl/apparie-768-par-fenetre.csv`, `kl/apparie-l1-contre-l0-768-par-fenetre.csv` (moyennes par fenêtre, les deux verdicts B2) ; `kl/B2-*.json`, `kl/apparie-*.json` (quantiles, σ par fenêtres).
- `repere/kl-q2_0-*.{json,csv}` : la requantification llama.cpp.
- `vitesse/pilote-s1.json` (sous charge, non concluante) et `vitesse/pilote-s2.json` (machine calme,
  relevés de charge par passe) ; `vitesse/s2-*.json` : par passe, jetons/s de préremplissage et de
  génération, compteurs du moteur (octets lus, défauts, h_vram, ms de copie et de décodage).
- `rapide/coder-synonyme-l0.json` (débit réel du compagnon λ = 0), `moteur/*synonyme-l0*` (S3-K, KL).

## 3 bis. Les résultats à porter (tous commités ; 07 § 0)

| Grandeur (768 experts, 10 fenêtres de R1) | frontière | λ = 1 | λ = 0 | journal |
|---|---|---|---|---|
| bits par poids (compagnon réel) | 2,6593 | 2,5861 | 2,6717 | `rapide/coder-*.json` |
| KL (référence f64 substituée) | 0,2640 | 0,1522 | 0,1318 | `kl/kl-*-768-juge.json` |
| KL du moteur rapide (carte) | 0,2626 | 0,1522 | 0,1313 | `moteur/kl-moteur-*-juge.json` |
| premier choix | 47,8 % | 67,5 % | 69,9 % | idem |
| 99,9e centile | 4,07 | 3,93 | 3,37 | idem |

Appariées (σ par fenêtres) : λ = 1 contre frontière −0,1118 ± 0,0296 ; λ = 0 contre λ = 1
−0,0204 ± 0,0097 (de justesse). Vitesse, machine calme : ~~20b ×1,24 (λ = 0), 120b ×2,00 (frontière)~~
*(barré par le juge comme gains du mode rapide, JUGEMENT-construction § 6 : rapports redonnés contre le
v1.0 d'origine, mais contre le v1.2, que l'étage disque lit à la même vitesse que les compagnons, ×0,94 (20b) et ×1,28 (120b) ; le
facteur ×1,31 de la proposition B3 est l'état physique du fichier v1.0, mesuré à l'étage disque)*.
120b : proxy KL(moteur exact ‖ rapide frontière) 0,1404 (validé sur le 20b à 0,002 près).

**Proposition B3 (à porter, calculée)** : le rapport des vitesses se décompose exactement en
v_B / v_A = (o_A / o_B) · (d_B / d_A), o les octets lus par pas de génération et d le débit par octet
(octets lus divisés par le temps de génération). Sur le 120b : 1,524 × 1,31 = 2,00 ; sur le 20b :
1,010 × 1,24 = 1,25 (médianes : 1,24). C'est la décomposition qu'il faut montrer en F-S7 : sur le 20b
le gain est tout entier dans d, sur le 120b il est d'abord dans o.

## 4. Les figures que ce travail mérite (belles et vraies)

1. **F-S1, « le synonyme dans la base propre de H »** (deux panneaux, axe des λ_k logarithmique) :
   à gauche, e_k en fonction de λ_k pour la frontière (gris) et le synonyme (couleur), lissés par
   déciles de k : la masse de l'erreur glisse vers la droite du spectre (les directions muettes) ;
   à droite, la part cumulée de l'erreur de sortie Σ_{j≤k} λ_j e_j / Σ λ_j e_j, en calibration (trait
   plein) et vue par l'évaluation (tirets) : l'aire entre les deux est le sur-apprentissage.
   Transformation avant/après au sens de la consigne de Stone (2026-10-17).
2. **F-S2, la queue de la KL** : fonction de survie P(KL > t) sur les 2 550 positions, échelle log-log,
   pour la référence llama.cpp Q2_0, la frontière à 768 experts et les deux synonymes (λ = 1, λ = 0) à 768 experts ; la
   médiane (part lisse) et le 99,9e centile (bascules) marqués.
3. **F-S3, la différence appariée par fenêtre** : dix barres d(fenêtre) avec ± 2σ_fenêtres, et la
   moyenne ; c'est la figure du verdict. Deux panneaux depuis le 2026-10-22 : synonyme λ = 1 contre la
   frontière (dix barres négatives, verdict franc, 3,8 σ) et λ = 0 contre λ = 1 (neuf négatives, la
   fenêtre 7 positive, verdict de justesse, 2,1 σ) : la même règle, deux marges très différentes ; la
   figure doit montrer les deux bandes ± 2σ, pas seulement les barres.
4. **F-S4, l'alphabet** : histogrammes des 8 symboles de base (frontière contre synonyme) par classe
   d'échelle κ, avec H0 et H(symbole | κ) en légende : où la contrainte d'entropie prend ses bits.
5. **F-S5, le chemin des octets en mode rapide** : le chronogramme du moteur (disque → DMA → décodeur →
   gemv_base), même figure que le Tome II, tronçons de taille f ≈ 0,7.
7. **F-S7, la vitesse et sa cause** (deux panneaux, séance s2) : à gauche les huit passes dans l'ordre
   A B B A A B B A (jetons/s, la bande ± 2σ des A, la première passe B froide marquée) ; à droite, pour
   chaque passe, octets lus par pas de génération contre débit par octet : les deux nuages A et B ont
   presque la même abscisse et des ordonnées séparées. C'est la figure qui empêche de lire ×1,24 comme
   « moins d'octets par jeton ».
8. **F-S8, la frontière des variantes** : plan (bits par poids du compagnon réel, KL de bout en bout à 768
   experts) avec frontière (2,659 ; 0,264), λ = 1 (2,586 ; 0,152), λ = 0 (2,672 ; 0,132), Q2_0 de
   llama.cpp (2,25 ; 1,597) et l'exact (3,85 ; 0,0037), barres ± 2σ par fenêtres : λ = 1 domine la
   frontière sur les deux axes, λ = 0 achète 0,020 de KL avec 0,086 bit.
6. **F-S6 (3D, si la carte et Blender le permettent)** : le nuage des entrées réelles d'un expert
   projeté sur les trois premières directions propres de H, avec les ellipsoïdes de l'erreur de sortie
   de la frontière et du synonyme : l'erreur synonyme est aplatie le long des axes que les entrées
   occupent.

## 5. Sources

Aucune source extérieure nouvelle : OBS (Hassibi et Stork 1992), GPTQ (Frantar et al. 2022, arXiv
2210.17323), déjà au BibTeX de l'éclaireur (`memoire/sources/`). llama.cpp b11515 (MIT), type Q2_0 lu
dans l'aide de `llama-quantize` du binaire présent sur la machine (« 2.25 bpw quantization (group
64) »).
