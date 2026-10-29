# Lot R : ce que le mémoire doit porter

Lot R : la référence f64, le juge, l'écart entre moteurs (R0, R1, R2 ; le banc Q0 viendra après J1).
Les chiffres viennent des journaux commités sous `mesures/moteur/R/` ; ceux qui manquent encore sont
marqués « à venir ». Étiquettes : [mes.] mesuré ici, [calc.] calculé, [litt.] littérature.

## 1. D'où l'on part, où l'on va

- **Au départ** : l'étude 06 avait montré que deux moteurs justes diffèrent de KL 0,0055 sur
  Qwen3.5-4B (processeur seul contre carte) et que le plancher de l'instrument (même moteur, deux
  fois) est KL ≈ 0 avec un maximum de 6,8·10⁻⁵ [mes. 06]. ARCHITECTURE.md (§ 7.1, C4) en tirait la
  règle : juger troncons non contre llama.cpp mais contre **les mathématiques exactes du modèle**.
- **Ce que le lot établit** : (i) une passe avant de gpt-oss en f64 qui lit le GGUF par un chemin
  indépendant ; (ii) l'écart entre moteurs mesuré **sur gpt-oss** (G_cfg, G_moteurs), qui remplace le
  chiffre de Qwen ; (iii) que llama.cpp b11515 et la définition d'OpenAI **ne calculent pas la même
  rotation YaRN** (bornes de la rampe arrondies), et ce que cela coûte en KL ; (iv) un juge qui lit et
  écrit le format `.kld` de llama.cpp, pour que tous les moteurs passent par le même instrument.
- **Ce qui reste** : R1 sur le 120b (et R1' à routage imposé si l'arbitre le retient), le banc Q0
  (après J1), le jugement C4 de troncons.

## 2. Dérivations à écrire en entier

### 2.1 Exactitude de la déquantification (lemme)

Q8_0 : w = d · q, d en f16 (mantisse 11 bits, exposant de −24 à 15), q ∈ [−128, 127] (7 bits plus le
signe). Le produit a au plus 11 + 7 = 18 bits significatifs et son exposant reste dans l'étendue
normale du f64 : il est représenté exactement. MXFP4 : w = K[c] · 2^(e − 128), K ∈ {0, ±1, ±2, ±3,
±4, ±6, ±8, ±12} (au plus 4 bits significatifs), e ∈ [0, 255] : exposant de −128 à 127, normal en
f64 (−1 022 à 1 023). Donc **la référence voit exactement les poids du fichier** ; toute l'erreur
qu'elle commet vient des sommes et des fonctions transcendantes en f64 (≈ 10⁻¹⁶ relatif par opération).

Le facteur 2^(e − 128) au lieu de 2^(e − 127) : K porte les grandeurs E2M1 doublées (0,5 → 1), d'où
la moitié de l'échelle (ggml : `GGML_E8M0_TO_FP32_HALF`). Ordre des demi-octets : l'octet j du bloc
porte l'élément j (faible) et l'élément j + 16 (fort) ; test `mxfp4_ordre_des_demi_octets`.

### 2.2 Les deux chemins de la référence calculent la même fonction (proposition)

Soit f_ℓ la couche ℓ. Avec un masque causal, la sortie de la position t à la couche ℓ ne dépend que
des entrées des positions ≤ t à la couche ℓ. Par récurrence sur ℓ, calculer f_ℓ pour toutes les
positions puis f_{ℓ+1} rend, position par position, les mêmes valeurs que la boucle jeton par jeton
avec cache KV, **à condition que chaque scalaire soit calculé par la même suite d'opérations** :
c'est le cas ici (le produit scalaire `poids::scalaire` ne dépend que de ses deux vecteurs, jamais du
nombre de positions ni du découpage en fils ; l'attention lit les mêmes clés dans le même ordre ; la
somme des quatre experts est faite dans l'ordre j = 0, 1, 2, 3). D'où le témoin W1 : **égalité au bit**,
pas à une tolérance près.

Ce que le second chemin économise [calc.] : jeton par jeton, chaque expert choisi est relu ; pour 10
fenêtres de 511 positions du 120b : 10 × 511 × 36 couches × 4 experts × 13,254 Mo ≈ 9,75 To lus. Par
couche pour tout le lot, chaque expert est lu au plus une fois par couche : 36 × 128 × 13,254 Mo ≈
61,1 Go, soit 160 fois moins, et le lot entier tient en mémoire (5 110 positions × 2 880 × 8 o =
118 Mo par tableau d'activations).

### 2.3 La rampe de YaRN : la définition d'OpenAI et la forme de llama.cpp

Fréquences d'origine θ_i = b^(−2i/d), i = 0 … d/2 − 1, b = 150 000, d = 64. YaRN « NTK par parties »
(Peng et al. 2023) mélange l'extrapolation θ_i et l'interpolation θ_i / s (s = 32) selon une rampe
sur l'indice de paire :

  r_i = clamp((i − α)/(β − α), 0, 1),  m_i = 1 − r_i,  ω_i = θ_i (m_i + (1 − m_i)/s).

Les bornes sont les paires dont la longueur d'onde 2π/θ_i fait respectivement β_r = 32 et β_l = 1
tours sur le contexte d'origine L₀ = 4 096 :

  2π b^(2i/d) = L₀ / β  ⇔  i(β) = (d/2) · ln(L₀/(2π β)) / ln b.

Calcul posé : ln b = ln 150 000 = 11,9184 ; L₀/(2π · 32) = 20,372, ln = 3,0141 ; L₀/(2π) = 651,90,
ln = 6,4798. Donc α = 32 × 3,0141 / 11,9184 = **8,0928** et β = 32 × 6,4798 / 11,9184 = **17,398**
(test `bornes_de_la_rampe_gpt_oss`).

- OpenAI (`gpt_oss/torch/model.py`, et `"truncate": false` dans `config.json`) garde α et β réels.
- llama.cpp b11515 (`ggml_rope_yarn_corr_dims`) prend ⌊α⌋ = 8 et ⌈β⌉ = 18.

~~Les fréquences ne diffèrent que pour 8 ≤ i ≤ 17.~~ Corrigé le 2026-10-15 par le second chemin
(`rampe_yarn.py`, `r1/rampe-yarn-*.json`) : elles ne diffèrent que pour **9 ≤ i ≤ 17** ; à i = 8 les deux
rampes valent 0 (8 < 8,0928 d'un côté, (8 − 8)/10 = 0 de l'autre), à i = 18 les deux valent 1.
Données de la figure R-M3 : `r1/csv/rampe-yarn.csv` (écrites par `juge rampe`, le code de la
référence ; recalculées par `rampe_yarn.py` à moins d'un ulp, 0,94 au plus ; cassure : rampe
arrondie prise pour celle d'OpenAI, les paires 9 à 17 tombent et elles seules). Ordre de grandeur de l'écart de phase à la
position t [calc.] : i = 17 : θ_17 = b^(−34/64) = 1,78·10⁻³ ; OpenAI : r = 0,957, m = 0,043, ω/θ =
0,0729 ; llama.cpp : r = 0,9, m = 0,1, ω/θ = 0,128 ; Δω = 9,8·10⁻⁵ rad par position, soit 0,05 rad à
t = 500. i = 9 : θ_9 = 0,035 ; Δω ≈ 8,8·10⁻⁵ rad par position. **Petit mais non nul, et il croît avec
la position** : à 131 072 jetons, 12,8 rad, c'est-à-dire une phase sans rapport. Ce qu'il coûte en
KL sur nos fenêtres de 512 : mesure Y de R1 (à venir).

Le facteur de concentration 0,1 ln s + 1 = 1,3466 multiplie cos et sin, donc le produit q · k par
1,8133 ; llama.cpp l'obtient par `yarn_attn_factor` ramené à 1 puis `mscale` dans `rope_yarn` : même
valeur (lu dans `llama-context.cpp`). C'est l'erreur injectée de la cassure de R1.

### 2.4 L'instrument : le codage sur 16 bits et son plancher

llama-perplexity stocke, par position, log p_i ≈ Δ · c_i + log p_min, c_i ∈ [0, 65 535], Δ = (max −
min′)/65 535 avec min′ = max(min, max − 16). Erreur de codage |δ_i| ≤ Δ/2 ≤ 16/131 070 = 1,22·10⁻⁴.
KL contre soi-même : KL = Σ p̂_i (log p̂_i − log p_i) avec log p̂_i = log p_i + δ_i et Σ p̂_i ≠ 1 ;
au premier ordre KL ≈ Σ p_i δ_i, borné par max|δ| ≤ Δ/2 (et pas par δ², parce que les p̂ ne sont pas
renormalisés). D'où le plancher mesuré de l'étude 06 (maximum 6,8·10⁻⁵ ≈ Δ/2 pour un écart max − min
d'environ 9) et le seuil de 7·10⁻⁵. Le test `kl_nulle_contre_soi_meme_et_positive_sinon` a d'abord
eu un seuil posé au jugé (10⁻⁷) ; il est tombé à 5,7·10⁻⁶ : ~~|KL| ≤ 10⁻⁷~~, remplacé par |KL| ≤ Δ.

**Le jugé codé ne se renormalise pas (trouvé le 2026-10-15).** Quand le jugé Q est lui-même un
`.kld` (chemin 2 de R0 et R1, et C4 où troncons passe par le codage), ses valeurs décodées sont
déjà des log-probabilités : log q̂_i = Δ c_i + log p_min, avec log p_min = min′ − max − lse calculé
sur les logits **exacts**. Les renormaliser ajoute à chaque position
  log Σ_i q̂_i = log(Σ_{c_i > 0} q̂_i + N₀ e^{log p_min}) ≈ N₀ e^{log p_min},
où N₀ est le nombre de jetons écrasés sur le code 0 (tous ceux sous max − 16 reçoivent log p_min,
au lieu de leur valeur, bien plus petite). Pour gpt-oss (n_vocab = 201 088, presque tous les
jetons sous la coupe), N₀ e^{−16} ≈ 2·10⁵ × 1,1·10⁻⁷ ≈ 2·10⁻² au pire ; **mesuré : 1,11·10⁻³ en
moyenne** sur les 2 550 positions, pour un fichier jugé contre lui-même (`r2/comparer-temoin-
identite-renormalise-AVANT-CORRECTION.json`), soit 16 fois le seuil de 7·10⁻⁵ : le chemin 2 et le
jugement C4 auraient été aveugles sous 10⁻³. Corrigé (`stats::position_decodee`, sans
renormalisation) : le même fichier contre lui-même donne **0 exactement** (`r2/comparer-temoin-
identite.json`) ; test `entree_decodee_contre_elle_meme` (et sa cassure, la renormalisation, qui
rend > 10⁻⁴). Ce que la correction laisse : un jeton que P juge probable (log p > −16) et que Q a
écrasé reçoit log p_min, une borne haute de sa vraie log-probabilité : le terme est sous-estimé,
jamais infini.

### 2.5 Intervalles

Taux de premier choix identique : intervalle de score de Wilson à 95 % (Wilson 1927) ; incertitude
d'une moyenne de KL : √((⟨x²⟩ − ⟨x⟩²)/(n − 1)), comme llama.cpp. C4 compare deux KL **sur les mêmes
positions** : l'écart-type de la différence appariée est plus petit que la somme des deux ; à porter
dans le jugement C4 (à venir, avec les données par position en CSV).

### 2.6 Le pavage du produit de la référence, et pourquoi il ne change aucun bit (reprise du 2026-10-15)

**Le coût de la première version** [calc.]. `produit` calculait y[p, r] = ⟨W_r, x_p⟩ rangée par
rangée, et pour chaque rangée relisait les n vecteurs d'entrée. Trafic vers la mémoire vive dès que
les n vecteurs ne tiennent plus dans le cache de dernier niveau (24 Mo) :
  T = R · n · C · 8 octets.
R1 sur 10 fenêtres : n = 10 × 511 = 5 110 positions, C = 2 880, donc n · C · 8 = 117,7 Mo. Pour la
matrice de sortie (R = 201 088) : T = 201 088 × 117,7 Mo = 2,37·10¹³ o ≈ 23,7 To ; à 60 Go/s
(ordre de grandeur de la DDR5 de la machine, [hyp.]) : ≈ 3,9·10⁵ s, plus de quatre jours pour une
seule matrice. Le témoin W1 (24 positions, 553 Ko, tenus en cache) ne pouvait pas le voir.

**Le pavage** (cadre : Goto et van de Geijn 2008, `goto2008anatomy`). Positions par paquets de
P_s = 256 (256 × 2 880 × 8 = 5,9 Mo, tenus en L3) ; pour chaque paquet, une tâche par bloc de 32
rangées, déquantifiées une fois (737 Ko, en L2) ; dans la tâche, tuiles de 8 positions (184 Ko) ;
dans la tuile, quatre produits à la fois (2 rangées × 2 positions). Trafic vers la mémoire vive :
les octets quantifiés de W une fois par paquet, ⌈n/P_s⌉ · R · C · b/8 (Q8_0 : b = 8,5 bits par
poids), soit pour la sortie 20 × 0,615 Go = 12,3 Go, et x une fois : ≈ 1,9·10³ fois moins.

**Proposition (égalité au bit).** Soit S(a, b) la suite d'opérations de `scalaire_avx2` : pour
i = 0, 8, 16, … < C₈ = 8⌊C/8⌋, lo ← fma(a[i..i+4], b[i..i+4], lo) et hi ← fma(a[i+4..i+8],
b[i+4..i+8], hi) ; puis s = ((ℓ₀ + h₀) + (ℓ₂ + h₂)) + ((ℓ₁ + h₁) + (ℓ₃ + h₃)) ; puis s ← fma(a_j,
b_j, s) pour j = C₈ … C − 1. Le noyau 2 × 2 exécute, pour chacun des quatre couples (a_u, b_v), la
même suite S(a_u, b_v) sur ses propres accumulateurs (lo_uv, hi_uv), entrelacée avec les trois
autres, et la même fonction de réduction (`reduire_avx2`, écrite une fois). Une FMA IEEE 754 rend
l'arrondi correct de a·b + c, fonction de ses trois opérandes seulement ; deux suites d'opérations
identiques sur des opérandes identiques rendent donc des résultats identiques, quel que soit
l'entrelacement. Le pavage ne change que **quels** produits sont calculés **quand** ; aucun ne
change d'ordre interne. Donc y[p, r] = S(W_r, x_p) au bit, pour toute taille de paquet, de bloc,
de tuile et tout nombre de fils. □

**Témoin et cassures** (`produit_egal_scalaire_au_bit`, réels non dyadiques, bords partout) : tient.
Cassure 1, lo et hi échangés pour le seul couple (a₁, b₁) : le témoin **tient encore**, et c'est la
réduction qui l'explique : échanger les deux moitiés change (ℓ_k + h_k) en (h_k + ℓ_k), égal par
commutativité exacte de l'addition IEEE. Leçon à porter au mémoire : une cassure doit changer la
fonction calculée, pas seulement le texte du code. Cassure 2, les huit termes de (a₁, b₁) sur la
seule chaîne lo : **tombe**, 304 sorties sur 71 × 19 = 1 349 (les autres sont des produits
pairs × pairs ou des bords, servis par le chemin qui n'a pas été faussé). W1 rejoué après le
pavage (`r1/W1-chemins-20b-pavage.log`) : 4 826 112 logits, 0 différent. Durée du chemin par lot
de 24 jetons : 48 s contre 133 s avant (une passe chacune, machine partagée, lecture des experts
comprise : indication, pas mesure ABBA ; à 24 positions le pavage ne change presque rien au trafic,
l'écart vient surtout de la charge de la machine et du cache de fichiers).

### 2.7 Le jugement C4 par différences appariées

A (llama.cpp carte) et B (troncons) sont jugés contre la même vérité V (référence f64) aux mêmes n
positions : x_i = KL(V_i ‖ A_i), y_i = KL(V_i ‖ B_i), d_i = y_i − x_i. Var(d̄) = (σ_x² + σ_y² −
2 ρ σ_x σ_y)/n. Deux moteurs qui se trompent aux mêmes positions difficiles ont ρ proche de 1 :
σ(d̄) est alors bien plus petit que √(σ_x² + σ_y²)/√n, et la comparaison appariée voit une
différence que la comparaison de deux moyennes indépendantes noierait. Estimateur :
σ̂(d̄) = √((⟨d²⟩ − ⟨d⟩²)/(n − 1)). Même chose pour le premier choix, e_i = t_B,i − t_A,i ∈ {−1, 0, 1}.
Verdict statistique (proposé à l'arbitre) : d̄ ≤ 2 σ̂(d̄) et ē ≥ −2 σ̂(ē) ; verdict littéral du
§ 7.1 : ȳ ≤ x̄ et taux_B ≥ taux_A. Données par position : CSV de `juge comparer`.

### 2.8 gpt-oss amplifie les petites erreurs : ce que R1 a mesuré, et ce que cela fait au critère

**Les nombres** [mes., 10 fenêtres de 512, 2 550 positions notées, gpt-oss-20b ; tous les
`.kld` hors du dépôt, empreintes dans les journaux] :

| Base P ‖ jugé Q | KL moyenne | médiane | 99e centile | max | même premier choix |
|---|---|---|---|---|---|
| llama.cpp processeur ‖ référence (rampe OpenAI) | 0,0255 | 0,0027 | 0,47 | 2,27 | 90,4 % |
| llama.cpp processeur ‖ référence (rampe llama.cpp) | 0,0273 | 0,0027 | — | — | 90,4 % |
| llama.cpp processeur ‖ référence (rampe llama.cpp, activations Q8_0 et KV f16 imités) | 0,0220 | 0,0025 | 0,40 | 2,67 | 91,6 % |
| référence OpenAI ‖ référence llama.cpp (la rampe seule change, tout en f64) | 0,0145 | 9,8·10⁻⁴ | 0,29 | 1,05 | 92,5 % |
| référence llama.cpp ‖ la même avec les imitations (seules des erreurs d'arrondi changent) | 0,0290 | 0,0030 | 0,54 | 4,14 | 90,3 % |
| llama.cpp processeur ‖ référence sans échelle de YaRN (cassure) | 0,249 | — | — | — | 57,3 % |

**Ce qu'ils disent.** (1) La médiane est dix fois sous la moyenne et le 99e centile cent fois
au-dessus : la KL n'est pas un bruit réparti, c'est une queue de positions où les deux calculs
divergent franchement. (2) Changer la seule rampe, dont l'effet direct est une phase de l'ordre de
10⁻⁴ rad par position sur neuf paires (§ 2.3), donne déjà 0,0145 ; ajouter seulement des erreurs
d'arrondi de l'ordre de 10⁻³ (Q8_0, f16) donne 0,029, plus que l'écart entre la référence et
llama.cpp lui-même. (3) Imiter les approximations de llama.cpp ne rapproche presque pas : dans un
régime qui amplifie, deux calculs perturbés différemment sont aussi loin l'un de l'autre que de
l'exact. L'hypothèse I (déclarée avant, seuil 2,5·10⁻³) supposait un régime linéaire ; elle est
tombée, et c'est le régime qu'elle a révélé.

**Le mécanisme supposé : les bascules de routage.** Le routeur garde les quatre plus grands de 32
logits (128 pour le 120b) ; la sortie de la couche est une fonction **discontinue** de l'entrée
là où le 4e et le 5e logit sont égaux. Si la marge m = z₍₄₎ − z₍₅₎ est plus petite que la
perturbation δz des logits, l'expert change ; la contribution perdue vaut g₄ (E₄(h) − E₅(h)), avec
g₄ le poids du 4e expert, non nul ; l'écart entre dans le résidu de cette position et, par les
clés et valeurs, dans toutes les positions suivantes. Avec 24 couches × 5 110 positions, même une
probabilité faible de m < δz par (couche, position) fait basculer une part notable des positions.
Expérience B (déclarée avant sa passe) : imposer à la rampe llama.cpp les experts choisis par la
rampe OpenAI ; si la KL tombe sous 10⁻³, les bascules portent l'écart. (Résultat, § 2.9 : 88 %
de la KL retirée, seuil manqué.)

**Ce que cela fait au critère R1 du § 6.5.** « KL(référence ‖ llama.cpp carte) ≤ max(G_moteurs,
7·10⁻⁵) » suppose que la référence juste est plus près de llama.cpp que deux moteurs llama.cpp
entre eux. Dans un régime qui amplifie, la distance de tout calcul approché à l'exact est du même
ordre que la distance entre deux calculs approchés, et la référence peut se trouver un peu au-delà
de G_moteurs sans aucun défaut. Le critère ne départage alors plus « référence juste » et
« référence fausse d'une petite erreur » (la rampe seule fait 0,0145) ; il ne départage qu'une
erreur grossière (la cassure : 0,249). Ce qui départage vraiment : B (routage imposé, régime
linéaire retrouvé), et un critère qui compare des distributions de distances plutôt qu'une
moyenne (porté à l'arbitre, REPRISE-R).

### 2.9 Les expériences D et B (déclarées avant leurs passes)

- **D, déterminisme de la référence** : rejouée (avec le code du journal de routage, ajouté entre
  les deux passes), elle écrit un `.kld` identique octet pour octet (1 Go) : **tient**.
- **B, routage imposé** : la rampe de llama.cpp, les experts de chaque (couche, position) imposés
  depuis la passe à la rampe d'OpenAI, contre la passe à la rampe d'OpenAI [mes.] :

| | KL moyenne | médiane | 99e centile | max | même premier choix |
|---|---|---|---|---|---|
| rampe seule changée, routage libre | 0,0145 | 9,8·10⁻⁴ | 0,29 | 1,05 | 92,5 % |
| rampe seule changée, routage imposé | 0,00168 | 2,2·10⁻⁴ | 0,031 | 0,53 | 97,2 % |

  Seuil déclaré : ≤ 10⁻³. **B tombe** (1,68·10⁻³). Ce qu'elle établit quand même : les bascules
  portent 1 − 0,00168/0,0145 = **88 %** de la KL ; le reste garde une queue (max 0,53) : un second
  amplificateur, non identifié, ou une sensibilité propre à quelques positions. Ce qui pourrait le
  trancher : la même expérience entre deux passes qui ne diffèrent que d'un arrondi (imitations
  seules), où l'effet direct est plus petit que celui de la rampe.

### 2.10 Les bascules, comptées (journaux de routage des deux rampes, `bascules.py`)

[mes. ; `r1/bascules-openai-llamacpp-20b.json`, CSV par position `r1/csv/bascules-openai-llamacpp-20b.csv`]
D tient aussi pour la rampe de llama.cpp (passe rejouée identique au bit). Entre les deux rampes :
- **5 087 bascules sur 122 640 (couche, position) : 4,15 %** ;
- aucune des 2 550 positions notées n'est sans bascule en amont dans sa fenêtre (à partir de la
  position 256, il y a toujours eu une bascule plus tôt) ;
- **1 157 positions basculent elles-mêmes (45 %) et portent 96,5 % de la KL** (moyenne 0,0309) ;
  les 1 393 autres, touchées seulement par le cache KV, ont une KL moyenne de 9,4·10⁻⁴, 33 fois
  moins ;
- marge du routeur (4e − 5e logit) : médiane 0,083 sur toutes les (couche, position), **0,0095
  sur celles qui basculent** ; 1 % des bascules sous 9,6·10⁻⁵.
Lecture : la bascule est locale avant d'être propagée ; la propagation par le cache KV existe
mais pèse peu. Figure à faire : KL par position contre la marge minimale (nuage, axe logarithmique),
deux couleurs (bascule à soi / non).

### 2.11 R0 sur la carte, et le verdict de R1 [mes., 2026-10-15, 19 h 59 à 20 h 20, secteur, carte libre]

| Mesure (base ‖ jugé, chemin 1 = llama-perplexity) | KL moyenne | médiane | max | même premier | chemin 2 (`juge kl`) | Seuil, verdict |
|---|---|---|---|---|---|---|
| T1 plancher : carte_cmoe ‖ carte_cmoe | −0,000000 | −0,000000 | 4,1·10⁻⁵ | 100 % | 0 | ≤ 7·10⁻⁵ et 100 % : **tient** |
| G_cfg : carte_cmoe ‖ carte_fitauto (vrai `--fit`) | 0 | 0 | 4,1·10⁻⁵ | 100 % | 0 | publié : **0 exactement** |
| carte_cmoe ‖ carte_fit (`-ngl 99 --fit on` : ajustement abandonné, tout sur la carte) | 0 | 0 | 4,1·10⁻⁵ | 100 % | 0 | publié |
| **G_moteurs** : carte_cmoe ‖ processeur seul | **0,022741 ± 0,0025** | 0,0024 | 3,64 | 91,57 % | 0,022735 | publié ; T3 (deux chemins) **tient** |
| sens inverse : processeur ‖ carte_cmoe | 0,021268 | 0,0025 | 2,19 | 91,57 % | 0,021260 | T3 **tient** |
| T2 cassure : carte_cmoe ‖ k = 2 experts | 0,4513 | 0,290 | 7,83 | 47,96 % | — | ≥ 7·10⁻³ et < 99 % : **tient** (l'instrument voit) |
| **R1** : référence OpenAI ‖ llama.cpp carte | **0,022612 ± 0,0017** | 0,0029 | 1,97 | 89,61 % | 0,022606 | ≤ max(G_moteurs, 7·10⁻⁵) = 0,022741 : **tient**, de 0,6 % |
| R1 cassure : référence sans échelle ‖ llama.cpp carte | 0,2644 | 0,131 | 12,28 | 57,80 % | 0,26372 | doit tomber : **tombe** |
| mesure Y : référence rampe llama.cpp ‖ llama.cpp carte | 0,022603 | 0,0027 | 1,56 | 89,96 % | 0,022581 | non jugée : indiscernable de R1 |

Déterminisme : les deux passes de chaque configuration (carte_cmoe, carte_fit, carte_fitauto,
processeur) écrivent des `.kld` identiques octet pour octet ; **carte_fit et carte_fitauto sont
identiques au bit à carte_cmoe**. Pourquoi (interprétation, cohérente avec l'option
`--sans-op-offload` du traceur de l'agent gpt-oss) : sur un lot de 512 jetons, llama.cpp exécute
sur la carte les produits dont les poids sont en mémoire de l'hôte, en les y copiant ; quelle que
soit la répartition, ce sont les mêmes noyaux sur les mêmes octets. G_cfg n'est donc pas nul en
génération (lots de 1), seulement en évaluation par lots : à mesurer en génération si J2 en a
besoin.

**Ce que R1 dit, et ce qu'il ne dit pas.** Le critère littéral tient, et la cassure tombe d'un
facteur 12 : la référence n'a pas d'erreur grossière. Mais la rampe de llama.cpp, différente de la
définition d'OpenAI, est aussi près de llama.cpp (0,022603 contre 0,022612) : à 0,02 près, tout
calcul juste ou presque juste est à la même distance de llama.cpp (§ 2.8 à 2.10). La justesse fine
de la référence repose donc sur ses témoins propres (W1, D, les tests unitaires de chaque
opération contre sa définition, le second chemin de la rampe), pas sur R1. **Le seuil Q1 de J2
(0,0055, Qwen3.5-4B)** est à remplacer par G_moteurs de gpt-oss-20b, **0,0227**, quatre fois plus :
c'est à l'arbitre de le barrer (ARCHITECTURE.md § 7.3) ; et la même amplification touche Q1.

### 2.12 Le jugement C4 essayé sur deux moteurs réels (`juge comparer`, `r2/`)

Vérité V = référence OpenAI ; A = llama.cpp carte ; B = llama.cpp processeur seul :
KL(V ‖ A) = 0,022606, KL(V ‖ B) = 0,026470 ; premier choix 89,61 % et 90,39 % ; différences
appariées d̄ = +0,00386 ± 0,00236 (1,6 σ), ē = +0,0078 ± 0,0055. Verdicts : littéral KL **tombe**,
littéral premier choix **tient**, statistiques **tiennent** tous deux. Deux moteurs que rien ne
distingue en justesse reçoivent des verdicts littéraux contraires selon la mesure : c'est le défaut
3 de la spécification, observé. L'écart-type apparié (0,00236) n'est guère plus petit que
√(0,0017² + 0,0025²) = 0,0030 : les bascules des deux moteurs tombent à des positions différentes,
la corrélation est faible. Cassure (B = référence sans échelle) : les quatre verdicts tombent
(d̄ = 0,220 ± 0,008, ē = −0,315 ± 0,010).

## 3. Schémas (TikZ)

- **R-M1** : les deux chemins de la référence (jeton par jeton avec cache KV ; couche par couche pour
  le lot) et le témoin d'égalité au bit entre eux.
- **R-M2** : le chemin de jugement : texte → jetons (llama.dll, trc-jetons, témoin W2) → fenêtres de
  512 → {llama.cpp carte, llama.cpp processeur, référence f64, troncons} → fichiers `.kld` → juge
  (deux chemins : llama-perplexity et `juge kl`).
- **R-M3** : la rampe de YaRN : r_i contre i pour OpenAI (8,09 → 17,40) et llama.cpp (8 → 18), et
  ω_i/θ_i sur les 32 paires (données : `r1/csv/rampe-yarn.csv` ; les deux courbes ne se séparent
  que de i = 9 à 17).
- **R-M5** : le pavage de `produit` (paquets de positions en L3, blocs de rangées en L2, tuiles,
  noyau 2 × 2 et ses huit chaînes de FMA), avec le trafic avant et après.
- **R-M6** : la bascule de routage : les 32 logits du routeur d'une position, le seuil entre le
  4e et le 5e, la marge m ; une perturbation δz > m fait sortir l'expert 4 et entrer l'expert 5 ;
  l'écart g₄ (E₄ − E₅) dans le résidu, puis dans les clés et valeurs des positions suivantes.
- **R-M7** : l'arbre des expériences de R1 (rampe, imitations, routage imposé, déterminisme) avec,
  à chaque feuille, la KL mesurée (tableau du § 2.8 et du § 2.9).
- **R-M4** : l'entrée `.kld` au bit près : f32 Δ, f32 log p_min, n_vocab × u16, bourrage ; nv =
  2⌈n/2⌉ + 4 = 201 092 mots pour gpt-oss.

## 4. Structures

- Le fichier `.kld` (§ R-M4 et `trc-juge/src/kld.rs`).
- Le bloc Q8_0 (34 o) et le bloc MXFP4 (17 o, ordre des demi-octets) tels que la référence les lit.
- `Releve` des compteurs (disque intégré, pointe de l'ensemble de travail tenue par le système,
  VRAM toutes les 250 ms).

## 5. Graphes (pgfplots), données CSV

- KL par position (R0 et R1) : distribution cumulée de la KL pour G_moteurs, G_cfg, le plancher, la
  cassure et R1 (`mesures/moteur/R/r0/juge-kl-*.csv`, `r1/juge-kl-*.csv`), axe logarithmique.
- KL moyenne en fonction de la position dans la fenêtre (256 à 510) pour la référence OpenAI contre
  la variante llama.cpp : l'écart de YaRN doit croître avec la position (§ 2.3).
- Tableau R0 : plancher, G_cfg, G_moteurs, cassure ; par les deux chemins.
- **Distributions cumulées de la KL de R1** (une courbe par ligne des tableaux des § 2.8 et 2.9,
  axe logarithmique) : `r1/juge-kl-*.csv` (colonne `kl`, 2 550 positions chacune). C'est la figure
  qui montre la queue : les courbes se croisent sous la médiane et se séparent au-delà du 90e centile.
- **KL par position contre marge minimale du routeur** (nuage, log-log, deux couleurs : bascule à
  soi ou non) : `r1/csv/bascules-openai-llamacpp-20b.csv`.
- **Marges du routeur** : histogramme de toutes les (couche, position) contre celles qui basculent
  (à tirer de `r1/routage/*.bin`, format en tête de `bascules.py`).
- ~~KL moyenne en fonction de la position dans la fenêtre : l'écart de YaRN doit croître avec la
  position (§ 2.3).~~ Mesuré (§ 2.8) : à peine (0,023 à 256, 0,031 à 480) ; la croissance attendue
  d'un effet de phase est noyée par les bascules ; à refaire sur la passe à routage imposé
  (`r1/juge-kl-ref-llamacpp-routage-openai-20b-contre-ref-openai-20b.csv`).

## 6. Ce qui pourrait être faux

- La référence suppose que le GGUF de ggml-org **est** le modèle : l'attention y est en Q8_0 (le
  modèle d'origine l'a en bf16). La référence juge donc « le modèle tel que stocké dans le fichier
  qu'on sert », pas le point de contrôle d'OpenAI. C'est le bon juge de troncons (mêmes octets), pas
  un juge de la quantification de ggml-org.
- La rampe de YaRN d'OpenAI est tenue pour le modèle sur la foi de deux sources primaires concordantes
  (l'implémentation de référence et `truncate: false`) ; l'entraînement lui-même n'est pas observable.
- Le format `.kld` code le jugé et la base sur 16 bits ; au chemin 2, le jugé est codé aussi, ce qui
  ajoute au plus ~Δ/2 de biais par position.
- **Le régime qui amplifie** (§ 2.8 à 2.10) est mesuré sur gpt-oss-20b, 10 fenêtres de
  wikitext-2 ; sur le 120b (128 experts, marges peut-être plus serrées) la part des bascules peut
  être plus grande. Les chiffres de R1 ne se transportent pas sans être remesurés.
- **Le second amplificateur** (les 12 % de la KL qui restent à routage imposé, queue jusqu'à 0,53)
  n'est pas identifié. Hypothèses non testées : coudes de la SwiGLU bornée (min(g, 7)), positions
  dont la distribution est presque plate, attention presque égale entre deux clés.
- **Les imitations** reproduisent la quantification Q8_0 des activations et le cache KV f16 tels que
  lus dans le code de b11515 ; pas les sommes en f32, ni le noyau répété des poids Q8_0
  (`REPACK = 1` dans le relevé du système), ni ce que fait le chemin de la carte (MMQ, q8_1).
- **ε de RMSNorm** est lu dans le GGUF en f32 (9,999999747·10⁻⁶ au lieu de 10⁻⁵) : écart relatif
  de 2,5·10⁻⁸ sur ε, sans effet mesurable (moyenne des carrés de l'ordre de 1).
- **Le pavage** est prouvé égal au bit par construction et par deux témoins (unitaire ; W1 rejoué,
  et la cassure de W1 rend exactement les mêmes 4 625 024 écarts qu'avant) ; il n'a pas été
  comparé directement, passe contre passe, à l'ancienne version sur 10 fenêtres (elle aurait pris
  des jours).
- **Les passes de la référence (15 h 35 à 17 h 35) ont tourné pendant la série 120b de l'agent
  gpt-oss** (lancée à 16 h 47) : sans effet sur nos logits (D tient), possible sur ses temps ;
  signalé dans la valeur de retour du lot.
- ~~Le témoin disque des compteurs est tombé sous une charge de repos de 0,39 Go/s ; à refaire au
  calme.~~ Refait au calme (repos 0,1 à 0,3 Mo/s) : tient trois fois (1,022 ; 0,999 ; 1,000 des
  octets vus, seuil 0,95), cassure tombe (0,0). Reste vrai : sous charge, il ne résout pas mieux que
  la variation de la charge des autres programmes.
- **G_cfg = 0** ne vaut que pour l'évaluation par lots de 512 ; l'interprétation (déport des
  produits sur la carte) n'est pas vérifiée dans le code de llama.cpp.
- **R1 tient de 0,6 %**, dans le bruit (± 0,0017 et ± 0,0025) : une autre graine de fenêtres pourrait
  le faire tomber sans que la référence change.
