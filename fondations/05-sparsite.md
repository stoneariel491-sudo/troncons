# Étude 05 : lire moins d'octets par jeton (sparsité, prédiction, décodage spéculatif)

Troncons, fondations. Rédigé le 2026-10-15. Toutes les sources ont été consultées le
2026-10-15 ; leur date de publication (v1) et de dernière révision est donnée au § 11.
Chaque chiffre porte son étiquette : **[litt.]** littérature (éditeur, non reproduit),
**[calc.]** calculé ici, **[mes.]** mesuré ici sur la machine de Stone.
Outils : `outils/05-sparsite/`. Journaux : `fondations/journaux/05-sparsite/`.

---

## 0. En bref

- **Le levier décisif quand le disque est le plafond n'est pas de lire moins, c'est de
  lire moins souvent.** Une passe de la cible sur `n` jetons lit les poids une fois. Si
  `n` jetons sont proposés et que la cible en garde en moyenne `E`, chaque lecture
  complète des poids actifs rend `E` jetons. En chaîne, avec un taux d'acceptation `α`
  par position et `k` jetons proposés :
  `E(α, k) = (1 − α^(k+1)) / (1 − α)` [calc., témoin par simulation réussi], borné par
  `1/(1 − α)`. Pour `α = 0,8` : 1,8 (k=1), 3,36 (k=4), 4,33 (k=8), 5 au plus. Pour
  `α = 0,9` : 4,1 (k=4), 6,1 (k=8), 10 au plus. Les arbres (SpecExec) dépassent la borne
  de la chaîne : 10 à 20 jetons par passe en régime déchargé [litt.].
- **La vérification de centaines de jetons est gratuite en calcul quand les poids
  arrivent par le PCIe ou le NVMe.** Le coude où le calcul rattrape la lecture est à
  `n* ≈ F·b / (2·B)` jetons : ≈ 30 si les poids sont en VRAM (200 Go/s), ≈ 900 s'ils
  passent par le PCIe mesuré (6,38 Go/s), ≈ 1 200 depuis un NVMe à 5 Go/s [calc., F =
  20 TFLOP/s ordre de grandeur, b = 0,6 octet/poids]. C'est la raison physique des grands
  arbres.
- **Sur la machine de Stone**, un modèle dense de 70 B en 4,8 bits (42 Go) dont 24 Go
  viennent du NVMe à chaque passe : 0,12 à 0,29 jeton/s sans spéculation, 0,6 à 1,4
  jeton/s en chaîne à `α = 0,8`, 1,2 à 2,9 jetons/s avec un arbre qui rend 10 jetons par
  passe [calc.]. Le même modèle en ~2,3 bits (20 Go, presque tout en RAM + VRAM) :
  0,4 à 0,6 jeton/s seul, 4 à 5,6 jetons/s avec l'arbre [calc.].
- **Les MoE à experts fins tuent la spéculation en régime disque.** La passe de
  vérification lit l'union des experts de ses `n` jetons. Avec un routage indépendant,
  256 experts dont 6 par jeton (DeepSeek-V4-Flash), l'union de 4 jetons pèse 3,86 fois
  celle d'un seul ; le `k` optimal est **0** pour tous les MoE du tableau de l'étude 06
  [calc.]. Il faut `α > 0,98` pour qu'un seul jeton proposé paie. Les méthodes 2026 qui
  bornent l'ensemble d'experts de la vérification (MoE-Spec, AcceptMoE : ×2,06 en
  déchargement, −0,27 point de précision) achètent ce gain par une petite perte [litt.].
- **La sparsité des activations par jeton ne survit pas à la vérification.** Mesuré sur
  SmolLM2-135M (SwiGLU) [mes.] : à 50 % de sparsité par jeton, l'union des masques de 4
  jetons consécutifs couvre 89,5 % des poids des blocs, celle de 8 jetons 97,6 %
  (l'indépendance prédirait 93,8 % et 99,6 % : la corrélation entre jetons voisins est
  faible). Forcer un **masque commun au bloc vérifié** garde les octets mais coûte la
  qualité : perplexité ×3,5 (bloc de 2) et ×17 (bloc de 4) à 50 %, +11 % et +34 % à
  25 %, contre +2 % (25 %) et +52 % (50 %) pour des masques par jeton [mes.]. Sur ce
  modèle, sparsité et spéculation ne se composent pas.
- **Les brouillons mesurés sur la famille de Stone** [mes.] : Qwen3.5-4B → 9B, accord
  glouton 76,8 % (au plus 4,3 jetons par passe en chaîne) ; copies quantifiées du 4B
  contre son Q4_K_M : 91,9 % (4,76 bits), 82,1 % (3,60), 65,8 % (2,91) ; une copie Q2_K
  naïve du 9B (sans imatrix) tombe à 34 %. Sur 8 Go de VRAM, le substitut résident
  (SubSpec) d'une cible de 14 B lue de la RAM rend ×2,5 (1,75 jeton/s) [calc. sur mes.] :
  **la qualité par octet à 2–3 bits devient le facteur limitant du brouillon**.
- **Les modèles hybrides de 2026 (Gated DeltaNet) rendent les arbres chers** : 48 Mio
  d'état récurrent par nœud gardé pour Qwen3.5-9B, 12 Gio pour un arbre de 256 nœuds
  [calc.].
- **Pas de loi de puissance des neurones chauds dans un modèle SwiGLU.** Pour couvrir
  80 % des sélections à 50 % de sparsité, il faut 74 % des canaux de `down` [mes.].
  PowerInfer et LLM in a flash reposent sur des modèles à ReLU (OPT, ReLU-Llama,
  TurboSparse) ; sur un modèle récent non « reluifié », leurs caches de neurones chauds
  rendent peu.
- **Ce qui manque dans le monde** (§ 9) : (1) aucune mesure publiée de spéculation avec
  des poids lus du NVMe quand la RAM est plus petite que le modèle (SpecExec et SubSpec
  avaient 128 à 192 Go de RAM) ; (2) le seul moteur qui tourne sous Windows sans boîte à
  outils CUDA (llama.cpp, Vulkan) ne vérifie que des chaînes, donc plafonne à
  `1/(1 − α)` jetons par lecture, là où les arbres en donnent 2 à 4 fois plus ;
  (3) les courbes d'union d'experts réelles des MoE fins de 2026 sur des jetons de
  brouillon ne sont publiées pour aucun modèle que la machine peut faire tourner ;
  (4) aucune vérification en arbre publiée pour les hybrides à règle delta (Qwen3.5 à
  3.8) ; (5) l'optimum du partage de 8 Go de VRAM entre brouillon et cible.

---

## 1. Le cadre : le juge est la physique

### 1.1 Le coût d'une passe

Une passe de la cible sur `n` jetons (un lot de vérification) coûte, si les étages sont
parfaitement recouverts :

    T(n) = max( O_disque(n) / B_disque , O_RAM(n) / B_PCIe , O_VRAM(n) / B_VRAM , C(n) / F )

et, sans aucun recouvrement, la somme des mêmes termes. `O_x(n)` est le nombre
d'octets de poids que la passe lit depuis l'étage `x`, `C(n) ≈ 2·n·N_actifs` le nombre
d'opérations, `F` le débit de calcul effectif. Pour un modèle **dense**, `O_x(n)` ne
dépend pas de `n` : c'est tout l'intérêt. Pour un **MoE** ou un modèle **à activations
creuses**, `O_x(n)` croît avec `n`, parce que la passe lit l'union de ce que chacun des
`n` jetons demande (§ 4, § 5).

Débits de la machine retenus ici :

| Étage | Débit | Étiquette |
|---|---:|---|
| VRAM GDDR6 128 bits | plafond 256 Go/s ; copie carte→carte 169 Go/s lecture + écriture | [calc.] plafond ; [mes.] étude 04 (`pcie-1.json`) |
| PCIe hôte → carte, mémoire épinglée, 256 Mio | 6,38 Go/s (plafond du lien 4.0 ×8 : 15,75) | [mes.] étude 04 |
| NVMe PCIe 4.0 ×4 | plafond 7,877 Go/s ; mesure en cours à l'étude 01 | [calc.] ; ici borné entre 3 et 7 Go/s |
| RAM DDR5 un seul module | plafond 41,6 Go/s | [calc.] étude 01 |

### 1.2 Le levier, en une ligne

Le débit de jetons est `E / (T(n) + T_brouillon)`, où `E` est le nombre de jetons
acceptés par passe. Tout ce que cette étude examine agit sur l'un des trois termes :

- **réduire `O(n)`** : sparsité des activations (Deja Vu, CATS, TEAL, R-Sparse),
  neurones chauds en mémoire rapide (PowerInfer, LLM in a flash), saut de couches,
  prédiction des experts ;
- **augmenter `E`** pour un `T(n)` presque inchangé : décodage spéculatif sous toutes
  ses formes ;
- **cacher `T_brouillon` dans `T(n)`** : recouvrir le brouillon et le chargement
  (ShadowSpec).

Quand les poids viennent du disque, `T(n)` se compte en secondes et `T_brouillon` en
millisecondes : le second levier écrase les deux autres, à une condition, que `O(n)`
reste plat en `n`. Toute la suite chiffre cette condition.

### 1.3 Le coude du calcul

La vérification de `n` jetons reste « gratuite » tant que `C(n)/F < O/B`, soit

    n < n* = F · b / (2 · B)

avec `b` les octets par poids et `B` le débit de l'étage d'où viennent les poids.
Avec `F ≈ 20 TFLOP/s` (ordre de grandeur des cœurs tenseurs FP16 d'une RTX 4060
Laptop ; la valeur exacte n'est pas mesurée ici, et la déquantification la fait
baisser), `b = 0,6` octet par poids (≈ 4,8 bits) [calc.] :

| Poids lus depuis | `B` | `n*` |
|---|---:|---:|
| VRAM | 200 Go/s | ≈ 30 |
| RAM par PCIe | 6,38 Go/s [mes.] | ≈ 940 |
| NVMe | 5 Go/s | ≈ 1 200 |

Ce tableau dit pourquoi SpecExec vérifie des arbres de 1 024 à 2 048 jetons en régime
déchargé, et pourquoi EAGLE sur une carte qui tient le modèle s'arrête à quelques
dizaines : ce n'est pas un choix, c'est `n*`.

---

## 2. Décodage spéculatif : le mécanisme exact

### 2.1 La règle de vérification (sans perte)

Leviathan, Kalman, Matias (arXiv 2211.17192, ICML 2023) et Chen et al. (arXiv
2302.01318, DeepMind, 2023) posent la même règle. Un brouillon `q` propose
`x₁…x_k` ; la cible `p` calcule en une passe `p(·|préfixe, x₁…x_i)` pour `i = 0…k`.
Chaque `x_i` est accepté avec la probabilité `min(1, p(x_i)/q(x_i))` ; au premier refus,
on tire un jeton dans la loi résiduelle `norm(max(0, p − q))` ; si tout est accepté, on
tire un `(k+1)`-ième jeton dans `p`. La sortie suit **exactement** la loi de la cible
(en glouton : un jeton est accepté s'il est l'argmax de la cible). Le taux d'acceptation
d'une position est `α = 1 − ½‖p − q‖₁ = Σ_x min(p(x), q(x))`.

### 2.2 Combien de jetons par lecture des poids

Si chaque position est acceptée avec la même probabilité `α`, indépendamment :

    E(α, k) = Σ_{i=0..k} α^i = (1 − α^{k+1}) / (1 − α)

Le terme `i = 0` est le jeton que la passe rend toujours (correction ou bonus).
Outil : `outils/05-sparsite/amortissement.py`. Témoin : simulation de 20 000 chaînes
par cas, écart < 4 σ dans les 9 cas ; mode cassé (formule sans le jeton bonus) : 7 cas
sur 9 tombent (`temoin-amortissement*.log`) [calc.].

**Jetons produits par lecture complète des poids actifs** [calc.] :

| α \ k | 1 | 2 | 3 | 4 | 6 | 8 | 16 | ∞ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 0,5 | 1,50 | 1,75 | 1,88 | 1,94 | 1,98 | 2,00 | 2,00 | 2 |
| 0,6 | 1,60 | 1,96 | 2,18 | 2,31 | 2,43 | 2,47 | 2,50 | 2,5 |
| 0,7 | 1,70 | 2,19 | 2,53 | 2,77 | 3,06 | 3,20 | 3,33 | 3,33 |
| 0,8 | 1,80 | 2,44 | 2,95 | 3,36 | 3,95 | 4,33 | 4,89 | 5 |
| 0,9 | 1,90 | 2,71 | 3,44 | 4,10 | 5,22 | 6,13 | 8,33 | 10 |
| 0,95 | 1,95 | 2,85 | 3,71 | 4,52 | 6,03 | 7,40 | 11,64 | 20 |

Trois lectures de ce tableau :

1. **La borne `1/(1 − α)` arrive vite.** À `α = 0,8`, k = 8 donne déjà 87 % de la
   borne. Au-delà, une chaîne plus longue ne sert plus : seul un meilleur brouillon
   (α plus grand) ou un **arbre** (plusieurs candidats par position) fait monter `E`.
2. **Quand la passe coûte des secondes, le `k` optimal est grand.** Avec `T(n)` = 8 s et
   un brouillon de 5 ms par jeton, le `k` qui maximise `E/(T + k·t_b)` vaut 25 à
   `α = 0,8` et 48 à `α = 0,9` [calc.] : on va jusqu'à la borne.
3. **L'hypothèse « α constant et indépendant » est optimiste en fin de chaîne** :
   l'acceptation réelle décroît avec la position (EAGLE, Medusa le montrent par leurs
   longueurs d'acceptation mesurées). Les chiffres de ce tableau sont des plafonds ; la
   mesure de `α` par position sur les modèles de Stone est au § 6.3.

### 2.3 Arbres

Avec un arbre de `K` nœuds, la passe vérifie toutes les branches à la fois (masque
d'attention en arbre) et garde le plus long chemin accepté. SpecInfer (arXiv
2305.09781) échantillonne les branches ; Sequoia (arXiv 2402.12374) construit l'arbre
optimal par programmation dynamique sous un budget ; SpecExec (arXiv 2406.02532) garde
les `K` continuations les plus probables du brouillon (recherche du meilleur d'abord
parallèle sur les log-probabilités cumulées) — c'est la variante faite pour le régime
déchargé. Sa propriété décisive : `E` n'est plus borné par `1/(1 − α)` mais par la
« couverture » de l'arbre ; elle croît avec `log K` tant que le brouillon classe bien.

Chiffres de SpecExec [litt.] (cible Llama 2 70B, poids en RAM, A100 par PCIe 4.0 ×16) :
jusqu'à 20,6 jetons acceptés par passe (budget 2 048, t = 0,6), 3,1 jetons/s en 16 bits ;
en GPTQ 4 bits, 12 à 13 jetons par passe (budget 128 à 256), 6 jetons/s ; **sur une
RTX 4060 (de bureau, RAM non précisée), 70B GPTQ : 9,7 jetons par passe, 3,28 jetons/s,
×4,6**. Sequoia : Llama 2 70B déchargé sur L40, 0,56 s/jeton contre 5,6 s pour leur
déchargement optimisé (×9,96) [litt.].

---

## 3. Les variantes, une par une

Pour chacune : ce qui sert de brouillon, ce que cela gagne en octets par jeton, ce que
cela coûte, si cela tourne sous Windows sans boîte à outils CUDA, sa maturité.
« llama.cpp » désigne la b11515 installée chez Stone et le dépôt au commit e467e5b
(lu le 2026-10-15, licence MIT) ; ses types `--spec-type` : `draft-simple`,
`draft-eagle3`, `draft-mtp`, `draft-dflash`, `draft-dspark`, `ngram-*`. Ils sont dans le
code commun (`common/speculative.cpp`), indépendants du moteur de calcul : ils tournent
donc aussi sous Vulkan. **Tous vérifient des chaînes, pas des arbres** : la lecture de
`common/speculative.cpp` montre un brouillon par séquence, et le paramètre
`--spec-draft-p-split` n'y est utilisé nulle part.

### 3.1 Brouillon par un petit modèle (Leviathan 2023, Chen 2023)

- **Mécanisme** : un modèle de la même famille et du même tokeniseur, 10 à 50 fois plus
  petit, propose `k` jetons ; § 2.1.
- **Octets par jeton** : ceux de la cible divisés par `E`, plus ceux du brouillon
  (`k` passes du petit modèle, lus en VRAM s'il y loge).
- **Coût** : aucune perte de qualité ; VRAM du brouillon et de son cache KV ; `α`
  modeste (0,6 à 0,8 en glouton entre modèles d'une même famille [litt.,
  ordre de grandeur]).
- **Windows / Vulkan** : oui (`draft-simple`). **Maturité** : production.
- **Chez Stone** : Qwen3.5-4B (2,7 Go) comme brouillon de Qwen3.5-9B n'a pas de sens
  quand le 9B tient en VRAM (le brouillon pèse la moitié de la cible) ; il en a un pour
  une cible de 30 à 70 B lue du disque. Mesure de `α` 4B → 9B : § 6.3.

### 3.2 Medusa (arXiv 2401.10774, 2024)

- **Mécanisme** : `K` têtes supplémentaires sur le dernier état caché de la cible ;
  la tête `i` prédit le jeton `t + i + 1` ; les top-k de chaque tête forment un arbre
  vérifié avec attention en arbre.
- **Gain** : ×2,2 (Medusa-1, cible gelée) à ×2,3–3,6 (Medusa-2, ajustée) [litt.].
- **Coût** : têtes entraînées par modèle ; les têtes ignorent les jetons intermédiaires,
  donc `α` chute vite avec la position.
- **Windows / Vulkan** : pas dans llama.cpp. **Maturité** : dépassé par EAGLE et le MTP.

### 3.3 EAGLE, EAGLE-2, EAGLE-3

- **Mécanisme** : un brouillon d'**une couche** qui lit les états cachés de la cible
  (EAGLE-3 : un mélange de couches basse, moyenne et haute, entraîné « en situation
  d'inférence », arXiv 2503.01840) ; EAGLE-2 (arXiv 2406.16858) fait croître l'arbre
  selon la confiance du brouillon.
- **Gain** : EAGLE-2 ×3,05–4,26 ; EAGLE-3 jusqu'à ×6,5, ×1,4 sur EAGLE-2 [litt.].
- **Coût** : une couche par modèle cible (quelques centaines de Mo) ; sans perte.
- **Windows / Vulkan** : `draft-eagle3` dans llama.cpp, **en chaîne** (pas l'arbre
  dynamique qui fait la moitié du gain d'EAGLE-2/3). Brouillons publiés pour Llama 3.x,
  Qwen3, gpt-oss, Gemma 4 ; **aucun pour Qwen3.5** dans la liste de `docs/speculative.md`.
- **Maturité** : production dans vLLM et SGLang ; partielle dans llama.cpp.
- **Licence** : dépôt SafeAILab/EAGLE, Apache-2.0 (fichier LICENSE lu).

### 3.4 MTP natif des modèles récents

- **Mécanisme** : le modèle est entraîné avec un ou plusieurs modules de prédiction
  multi-jetons (Gloeckle et al., arXiv 2404.19737 ; DeepSeek-V3, arXiv 2412.19437, une
  profondeur `D = 1`). Le module MTP (une couche de transformeur qui combine l'état
  caché et le plongement du jeton suivant, partageant plongements et tête) sert de
  brouillon gratuit. DeepSeek-V3 annonce une acceptation du second jeton de 85 à 90 %
  et ×1,8 en jetons/s [litt. ; chiffre de la section 5.4.3 du rapport, que je n'ai pu
  relire que partiellement : à vérifier].
- **Qui l'a** : Qwen3.5 (`"mtp_num_hidden_layers": 1` dans `config.json` de
  Qwen/Qwen3.5-9B), Qwen3.6, Qwen3.8, GLM-4.5 à 5.3, DeepSeek-V3 à V4 ; 17 des 29
  dépôts de l'inventaire de l'étude 06 (`inventaire-3.json`) déclarent un MTP ; ni
  Kimi-K2.x, ni gpt-oss, ni Qwen3-235B n'en ont.
- **Octets** : un bloc de plus (≈ 1/32 du 9B), lu `k` fois par passe. Pour un modèle
  lu du disque, **le module MTP doit être résident en VRAM** pour que le brouillon ne
  relise rien du disque : c'est le brouillon le moins cher qui existe.
- **Chez Stone** : les GGUF Unsloth de Qwen3.5 installés **n'ont aucun tenseur MTP**
  (inventaire, pas 1). Unsloth publie `unsloth/Qwen3.5-9B-MTP-GGUF` (Q4_K_M : 5,87 Go,
  Apache-2.0, 2026-05-16) : téléchargement à demander.
- **Windows / Vulkan** : `draft-mtp` dans llama.cpp. **Maturité** : récente, en production
  dans SGLang/vLLM pour DeepSeek et Qwen.

### 3.5 Brouillons par blocs : DFlash, DSpark

- **DFlash** (arXiv 2602.06036, ICML 2026) : un petit modèle de diffusion par blocs,
  conditionné sur les états cachés de la cible, propose un **bloc entier en une passe**.
  Plus de ×6 sans perte, jusqu'à 2,5 fois le gain d'EAGLE-3 [litt.]. Dépôt z-lab/dflash,
  MIT.
- **DSpark** (DeepSeek ; brouillons LFM2.5 de Liquid AI) : DFlash plus une « tête de
  Markov » de faible rang qui réinjecte le jeton précédent dans chaque position du bloc
  (description de `docs/speculative.md` de llama.cpp). Les chiffres publiés sont ceux
  de l'éditeur (×3,18 sur H100) [litt., blog éditeur, à prendre comme tel].
- **Intérêt pour le régime disque** : le brouillon coûte une passe par bloc, pas une par
  jeton ; mais en régime disque `T_brouillon` est déjà négligeable devant `T(n)`. Ce qui
  compte est `α` par position et la longueur de bloc ; DFlash est borné à son bloc
  d'entraînement (15 pour Qwen3-4B).
- **Windows / Vulkan** : `draft-dflash`, `draft-dspark` dans llama.cpp. Un brouillon
  DFlash pour Qwen3.5-9B existe : `AtomicChat/Qwen3.5-9B-DFlash-GGUF` (Q8_0, 1,38 Go,
  Apache-2.0, 2026-07-22).

### 3.6 Sans modèle : lookahead, n-grammes, recherche dans le contexte

- **Lookahead** (arXiv 2402.02057) : itérations de Jacobi qui produisent des n-grammes
  candidats, vérifiés en parallèle ; ×1,8 sur MT-Bench, ×4 en code multi-GPU [litt.].
- **Recherche dans le contexte** (prompt lookup, dépôt apoorvumang/prompt-lookup-decoding,
  sans licence déclarée ; `ngram-simple`, `ngram-map-k`, `ngram-mod`, `ngram-cache` de
  llama.cpp) : on cherche le dernier n-gramme dans l'historique et l'on propose ce qui
  le suivait. Coût du prédicteur nul (16 Mo pour `ngram-mod`).
- **Gain** : énorme sur la réécriture (code, résumé, réponse qui recopie un
  raisonnement), presque nul sur la prose libre. C'est le complément gratuit de tout le
  reste : llama.cpp donne la priorité au n-gramme quand il est combiné à un brouillon.
- **Windows / Vulkan** : oui. **Maturité** : production.

### 3.7 Auto-spéculation : la cible se sert de brouillon

- **Saut de couches / sortie anticipée** : LayerSkip (arXiv 2404.16710, ACL 2024 ;
  dépôt sous CC BY-NC 4.0, donc inutilisable au-delà de la lecture) entraîne le modèle
  à sortir tôt, puis vérifie avec les couches restantes : ×1,82 à ×2,16 [litt.].
  Draft & Verify, SWIFT, Kangaroo font de même sans réentraîner ou avec un adaptateur.
  **En régime disque**, le brouillon par sortie anticipée lit les premières couches,
  donc relit du disque : il ne vaut que si ces couches sont résidentes.
- **QSpec** (arXiv 2410.11305, EMNLP 2025) : brouillon en W4A4, vérification en W4A16,
  mêmes poids et même cache : ×1,64 sans perte [litt.].
- **SubSpec** (arXiv 2509.18344, NeurIPS 2025 ; dépôt NYCU-EDgeAi/subspec, Apache-2.0) :
  **le plus proche de notre problème**. Les couches déchargées de la cible sont
  remplacées, pour le brouillon, par des **substituts 4 bits résidents en VRAM** (HQQ,
  groupes de 64) ; le cache KV est partagé. Le brouillon ressemble tant à la cible que
  la longueur d'acceptation moyenne atteint 27 à 35 jetons par passe (arbre top-6 ×
  profondeur 48 = 288 jetons vérifiés) ; **Qwen2.5-7B sous 8 Go de VRAM : 2,68 →
  27,1 jetons/s (×10,1)** ; Qwen2.5-32B sous 24 Go : 0,52 → 6,5 jetons/s [litt. ; RTX
  4090, PCIe 4.0 ×16, 128 Go de RAM].
- **ShadowSpec** (ICML 2026, atelier AdaptFM) : fait croître l'arbre de SubSpec pendant
  que les poids de la cible se chargent ; +17 à 54 % sur SubSpec [litt.].

### 3.8 Les arbres en régime déchargé : SpecExec, Sequoia, TriForce, Dovetail, SpecOffload

- **SpecExec** et **Sequoia** : § 2.3. Dépôts yandex-research/specexec et
  Infini-AI-Lab/Sequoia : **aucune licence déclarée** (API GitHub et racine du dépôt
  lues) : lecture seulement.
- **TriForce** (arXiv 2404.11912, COLM 2024) : spéculation hiérarchique pour le long
  contexte (le cache KV est ce qui se lit) ; 0,108 s/jeton en déchargement sur deux RTX
  4090 pour Llama2-7B-128K [litt.].
- **Dovetail** (arXiv 2412.18934) : brouillon sur la carte, cible sur le processeur ;
  ×1,79 à ×10,1 sur des modèles 13B [litt.].
- **SpecOffload** (arXiv 2505.10259) : loge et exécute le brouillon dans la VRAM laissée
  libre par le déchargement ; ×2,54 en débit [litt.].

### 3.8 bis Le piège des modèles hybrides (Gated DeltaNet) : l'état à remonter

Qwen3.5, Qwen3.6, Qwen3.8 et Qwen3-Next mêlent des couches d'attention complète et des
couches d'attention linéaire à règle delta (Gated DeltaNet), dont l'état est une
matrice par tête, mise à jour à chaque jeton. Un jeton de brouillon refusé ne se
« retire » pas d'un état récurrent : il faut avoir gardé l'état d'avant, ou recalculer.
Pour Qwen3.5-9B (métadonnées GGUF : 32 têtes de valeur, `ssm.state_size` = 128, largeur
interne 4 096, donc 128 × 128 par tête ; 24 couches linéaires sur 32) [calc.] :

    état par couche = 32 × 128 × 128 = 524 288 valeurs = 2 Mio en FP32
    état du modèle   = 24 × 2 Mio = 48 Mio par position gardée

Une chaîne de `k` jetons demande `k` instantanés (768 Mio à k = 16) si l'on garde tout ;
un **arbre** de `K` nœuds en demande `K` : 12 Gio à K = 256, impossible sur 8 Go. Le
dépôt llama.cpp vient d'ajouter le retour en arrière partiel des couches GDN pour la
spéculation en chaîne (commit « allow partial seq_rm for GDN models », relevé par
recherche, non lu). **STree** (arXiv 2505.14969, 2025-05-20 ; 2025-10-27, NeurIPS 2025)
fait de la vérification en arbre pour les SSM et hybrides en exploitant la structure des
matrices de transition cumulées ; son résumé ne dit pas s'il couvre la règle delta, dont
la transition `α_t (I − β_t k_t k_tᵀ)` n'est pas diagonale. Un embranchement non
officiel de llama.cpp (Leechael/llama.cpp-dflash-ggml, DDTree) vérifie des arbres de
DFlash, en un seul flux, « chaîne seulement » pour la validation exacte (relevé par
recherche, non lu).

### 3.9 MoE et spéculation (2025-2026)

Le problème est posé par Cascade (arXiv 2506.20675) : « la spéculation est inefficace
pour les MoE », les jetons de brouillon activent 2 à 3 fois plus de poids, jusqu'à
1,5 fois plus lent [litt.]. MoESD (arXiv 2505.19645, NeurIPS 2025) montre l'inverse à
lot moyen (×2,29 sur Qwen2-57B-A14B) : à lot moyen, l'union des experts est déjà presque
complète, donc les jetons de brouillon ne coûtent rien de plus. **Le régime de Stone
(lot de 1, poids sur le disque) est exactement celui de Cascade.** Les réponses de 2026 :

- **MoE-Spec** (arXiv 2602.16052) : un budget fixe d'experts par couche pendant la
  vérification ; +10 à 30 % sur EAGLE-3 « à qualité comparable » [litt.].
- **AcceptMoE** (arXiv 2608.02989) : le budget se choisit seul par bloc, et **en
  déchargement l'éligibilité est conditionnée aux experts déjà en cache** : ×2,06 sur
  EAGLE-3, −73,6 à −77,1 % de trafic hôte → carte, −0,27 point de précision moyenne
  [litt.]. Change la loi de sortie (avec perte).
- **EcoSpec** (arXiv 2607.12696) : le choix des chemins du brouillon tient compte du coût
  marginal des experts qu'ils activent ; sans perte ; jusqu'à ×1,62 sur Qwen3-235B
  [litt.].
- **EVICT** (arXiv 2605.00342) : tronque l'arbre avant vérification pour ne garder que
  le préfixe rentable (bénéfice estimé par le brouillon, coût de vérification profilé
  hors ligne) ; sans perte ; jusqu'à ×2,35 sur l'autorégressif, ×1,21 sur EAGLE-3
  [litt.].
- **DraftExpert** (arXiv 2607.24434) : régime embarqué, experts chargés à la demande
  (CPU → carte, ou Flash → NPU) ; un expert de brouillon distillé par couche, résident ;
  ×1,45, acceptation 84–87 %, préchargement juste à 86–88 % (DeepSeek-V2-Lite,
  Moonlight-16B) [litt.].
- **Mixture of Cache-Conditional Experts** (arXiv 2412.00099, TMLR 2025) : routage qui
  favorise les experts déjà en DRAM, sans réentraîner ; ×2 sur mobile [litt.].

Le calcul du § 6.2 montre pourquoi ces méthodes sont nécessaires et pas optionnelles
quand les experts viennent du disque.

---

## 4. Prédire les experts (MoE)

- **Mixtral offloading** (Eliseev et Mazur, arXiv 2312.17238) : cache LRU d'experts et
  chargement spéculatif des experts de la couche suivante à partir de l'état caché
  courant [litt., le détail n'est pas dans le résumé].
- **ProMoE** (arXiv 2410.22134) : prédicteur d'experts sur les résultats intermédiaires,
  préchargement hors du chemin critique ; décodage ×2,07 en moyenne, jusqu'à ×5,02
  [litt.].
- **Pre-gated MoE**, **MoE-Infinity**, **HOBBIT**, **fMoE** : variantes du même geste
  (prédire, précharger, ou remplacer un expert manquant par une copie basse précision).
- **Ce que ça gagne en octets** : rien. Prédire un expert ne réduit pas les octets
  lus, il **cache la latence** du chargement derrière le calcul. En régime disque, où le
  disque est occupé en permanence, le préchargement ne rend que le recouvrement
  (le passage de la somme au max du § 1.1). Seuls le cache (RAM, VRAM) et la
  substitution avec perte réduisent les octets venus du disque.

---

## 5. Sparsité des activations

### 5.1 Les méthodes et leurs chiffres

| Méthode | Ce qui est creux | Prédicteur | Gain publié [litt.] | Perte publiée [litt.] |
|---|---|---|---|---|
| Deja Vu (arXiv 2310.17157, ICML 2023) | têtes d'attention et neurones du FFN, par jeton | petits MLP par couche, lancés une couche en avance | OPT-175B : ×2 sur FasterTransformer | « sans perte » sur OPT (ReLU) |
| PowerInfer (arXiv 2312.12456, SOSP 2024) | neurones du FFN ; chauds sur la carte, froids sur le CPU | prédicteurs par couche (repris de Deja Vu) | jusqu'à ×11,69 sur llama.cpp, RTX 4090 | modèles ReLU (ReLU-Llama, ProSparse) |
| PowerInfer-2 (arXiv 2406.06282) | idem, sur téléphone, poids en Flash | idem | 47B à 11,68 jetons/s sur téléphone | TurboSparse-Mixtral (dReLU) |
| LLM in a flash (arXiv 2312.11514, ACL 2024) | neurones du FFN ; fenêtre glissante des neurones récents en DRAM ; « row-column bundling » | prédicteur de faible rang | modèles deux fois la DRAM ; ×4–5 CPU, ×20–25 GPU sur le chargement naïf | OPT, Falcon « reluifié » |
| ReLU Strikes Back (arXiv 2310.04564) | reluifier pour rendre creux | aucun | jusqu'à ×3 en calcul | réentraînement |
| CATS (arXiv 2404.08763) | entrée de `down` : seuil sur `|SiLU(gate)|` | aucun (seuil) | +15 % de latence de génération | à 1–2 % des tâches à 50 % de sparsité |
| TEAL (arXiv 2408.14690, ICLR 2025) | entrée de **toutes** les matrices, seuil de magnitude par tenseur | aucun | ×1,53 à 40 %, ×1,8 à 50 % | « minimale » à 40–50 % (Llama 2/3, Mistral, 7–70B) |
| R-Sparse (arXiv 2504.19449, ICLR 2025) | canaux d'entrée + composantes singulières | aucun | +43 % de bout en bout | comparable à 50 % |
| Polar Sparsity (arXiv 2505.14884, NeurIPS 2025) | têtes d'attention, qui restent creuses en lot | routeurs de têtes | ×2,2 en lot | — |
| TurboSparse (arXiv 2406.05955) | dReLU, réentraîné | prédicteurs | ×2–5 ; 2,5 Md de paramètres actifs pour un Mistral | réentraînement |

Lecture du code de TEAL (dépôt FasterDecoding/TEAL, MIT, commit fb7373c) : les seuils
viennent d'histogrammes par tenseur (`grab_acts.py`), répartis entre couches par un
algorithme glouton (`greedyopt.py`) ; le noyau `splitk_sparse_gemv` (Triton, donc CUDA)
**exige des poids rangés par colonnes** (`assert weight.stride(1) > 1`) : une composante
nulle de l'entrée saute une colonne contiguë. C'est la condition pour que la sparsité
devienne des octets non lus, en VRAM comme sur le disque.

### 5.2 Ce qu'il faut pour qu'un zéro devienne un octet non lu

- **En VRAM** : poids par colonnes, noyau qui ne charge que les colonnes vivantes.
  Aucun noyau de ce type n'existe dans llama.cpp (ni CUDA ni Vulkan) : ses types
  quantifiés sont rangés par lignes, en blocs de 32 ou 256 poids d'une même ligne.
- **Sur le disque** : la granularité est la page (4 Kio) et, pour atteindre le débit
  séquentiel, des lectures de dizaines de Kio (LLM in a flash : « row-column bundling »,
  qui range ensemble la ligne `i` de `up`/`gate` et la colonne `i` de `down`, pour lire
  un neurone d'un seul tenant). Pour Qwen3.5-9B en ~4,5 bits, un neurone du FFN
  (3 vecteurs de 4 096) pèse ≈ 6,9 Kio [calc.] : deux pages, sous le seuil où un NVMe
  donne son débit séquentiel. La mesure du débit en lectures aléatoires de 4 à 64 Kio
  revient à l'étude 01.

### 5.3 Mesures ici : unions, fenêtre, neurones chauds (SmolLM2-135M)

**Instrument.** `outils/05-sparsite/llama_numpy.py` : passe avant numpy d'un modèle
« llama » F16 lu dans le GGUF, écrite de zéro, avec un crochet sur l'entrée de chaque
projection (`attn_in` → Wq,Wk,Wv ; `o_in` → Wo ; `ffn_in` → Wgate,Wup ; `down_in` →
Wdown). Modèle : SmolLM2-135M-Instruct F16 (Apache-2.0), 30 couches, SwiGLU, 576 / 1 536.
Texte : WikiText-2 brut, tokenisé par `llama-tokenize` b11515.

**Témoin.** La perplexité de la passe numpy doit retrouver celle de `llama-perplexity`
(fenêtres de 512, seconde moitié notée) à moins de 0,5 % (seuil déclaré dans
`temoin_passe_avant.py` avant le lancement, avec sa raison) : 10,4272 contre 10,4086
(0,18 %) et 16,8477 contre 16,8298 (0,11 %) sur les deux premières fenêtres, et
**22,6768 contre 22,6739 (0,013 %) sur les 16 fenêtres déclarées**, écart maximal
0,18 % (fenêtre 1) [mes., `temoin-passe-avant.log`]. **Le témoin tombe quand on le casse** :
avec la rotation RoPE par moitiés au lieu des paires voisines, 232,8 contre 10,4
(`temoin-passe-avant-casse.log`).

**Mesure.** 2 048 jetons (4 fenêtres de 512), masque « top-k par jeton » (les
`(1 − s)·D` composantes de plus grande valeur absolue ; c'est TEAL à densité fixe).
Journal : `stats-smol.json`.

**Union des masques de `n` jetons consécutifs** (fraction des colonnes qu'une passe
de vérification de `n` jetons doit lire si chacun garde son masque), moyenne des 30
couches, entrée de `down` [mes.] :

| sparsité par jeton | n=1 | 2 | 4 | 8 | 16 | 32 |
|---|---:|---:|---:|---:|---:|---:|
| 25 % | 0,750 | 0,923 | 0,991 | 1,000 | 1,000 | 1,000 |
| 50 % | 0,500 | 0,718 | 0,899 | 0,982 | 0,999 | 1,000 |
| (indépendance, 50 %) | 0,500 | 0,750 | 0,938 | 0,996 | 1,000 | 1,000 |
| 70 % | 0,300 | 0,475 | 0,686 | 0,870 | 0,967 | 0,995 |
| 90 % | 0,100 | 0,173 | 0,286 | 0,447 | 0,635 | 0,803 |

Pondérée par les octets des quatre entrées (Wq,Wk,Wv 15,6 % ; Wo 9,4 % ; Wgate,Wup
50,0 % ; Wdown 25,0 % des poids d'un bloc), à 50 % de sparsité par jeton, l'union vaut
**0,895 à n = 4 et 0,976 à n = 8** [calc. sur mes.]. L'entrée de Wo est la plus
corrélée (0,786 à n = 4), mais elle pèse peu.

**Lecture.** La corrélation entre jetons voisins existe (l'union est sous
l'indépendance), mais elle est faible : à 50 % par jeton, une vérification de 4 jetons
ne lit que 10,5 % de moins qu'une passe dense. **Composée naïvement avec la
spéculation, la sparsité par jeton s'évanouit.** C'est le phénomène que Deja Vu appelle
« union contextual sparsity » et que PowerInfer-2 chiffre pour les lots (moins de 1 % à
75 % de neurones très activés de 1 à 32 [litt.]) ; je l'ai mesuré pour la fenêtre
consécutive d'une vérification, sur un modèle SwiGLU sans réentraînement.

**Fenêtre glissante (le « windowing » de LLM in a flash).** Fraction des composantes du
masque du jeton `t` absentes des masques des `w` jetons précédents, entrée de `down`,
50 % de sparsité [mes.] : 0,218 (w=1), 0,116 (w=2), 0,038 (w=4), 0,006 (w=8). Mais le
cache qui permet cela contient l'union des `w` masques : 72 % des colonnes à w=1, 90 % à
w=4. **La fenêtre réduit le trafic disque au prix d'une RAM qui tient presque toute la
matrice** : à RAM égale (72 % des colonnes), un cache statique dense laisse 28 % des
octets au disque par jeton, la fenêtre w=1 en laisse 21,8 % [calc. sur mes.]. Gain :
×1,28, pour une sparsité de 50 % qui coûte en qualité (§ 5.5).

**Neurones chauds.** Part des canaux qui portent 80 % des sélections, à 50 % de
sparsité [mes.] : 74 % (`down_in`), 76 % (`ffn_in`), 74 % (`attn_in`), 64 % (`o_in`).
À 90 % de sparsité : 55 % (`down_in`). **Pas de loi de puissance** : un cache des
neurones chauds de 74 % des canaux de `down` laisse encore 20 % des sélections au
disque, soit 0,2 × 0,5 = 10 % des octets de `down` par jeton, contre 26 % pour un cache
dense de même taille (×2,6) [calc. sur mes.]. Le facteur ×11,69 de PowerInfer suppose
une sparsité de ReLU (plus de 90 % de neurones inactifs) et une loi de puissance que
SwiGLU ne donne pas.

### 5.4 Composer sparsité et spéculation : un masque commun au bloc vérifié

La seule manière de garder les octets de la sparsité sous la vérification est que les
`n` jetons d'un bloc **partagent un même masque**. Règle mesurée ici (`bloc:n:s`) : pour
chaque bloc de `n` jetons consécutifs, on garde les `(1 − s)·D` canaux d'énergie
`Σ_i v_ij²` la plus grande, et le même masque s'applique aux `n` jetons. Variante
`blocw` : énergie pondérée par `‖W[:, j]‖²` (la norme de la colonne qu'on renonce à lire :
l'erreur sur la sortie est `Σ_j v_ij W[:, j]`). La passe de `n` jetons lit alors
exactement `(1 − s)` des colonnes, quel que soit `n`. Ce geste existe pour les experts
(MoE-Spec, AcceptMoE) et en esprit pour les neurones (vérification creuse,
arXiv 2512.21911, sans chiffres dans son résumé) ; la mesure qui suit le chiffre pour
un FFN SwiGLU dense.

**Mise en garde sur le régime de la mesure.** Je mesure la perplexité sur un texte où le
bloc est le texte réel ; dans la vraie vérification, le bloc est le brouillon, et un
masque commun dégrade la distribution de la cible **qui décide de l'acceptation** :
la spéculation reste exacte par rapport à la cible creusée, pas par rapport à la cible
dense. La perte est donc celle de la perplexité mesurée ; elle n'est pas rattrapée par
la vérification.

### 5.5 Coût en qualité, mesuré

SmolLM2-135M, WikiText-2 test, 4 fenêtres de 512 (1 020 positions notées, les mêmes
pour toutes les règles : les écarts sont appariés). Journal `ppl-smol.json` [mes.] :

| Règle | Colonnes lues par passe de n jetons | Perplexité | Écart |
|---|---|---:|---:|
| aucune (dense) | 100 % | 17,86 | — |
| top-k par jeton, s = 25 % | 75 % à n = 1 ; ≈ 99 % à n = 4 (union) | 18,24 | +2,1 % |
| top-k par jeton, s = 40 % | 60 % à n = 1 | 21,22 | +18,8 % |
| top-k par jeton, s = 50 % | 50 % à n = 1 ; 89,5 % à n = 4 | 27,09 | +51,6 % |
| top-k par jeton pondéré par ‖W[:,j]‖, s = 50 % | 50 % à n = 1 | 26,41 | +47,8 % |
| masque commun, bloc de 2, pondéré, s = 25 % | 75 % pour tout n ≤ 2 | 19,84 | +11,0 % |
| masque commun, bloc de 4, pondéré, s = 25 % | 75 % pour tout n ≤ 4 | 23,96 | +34,1 % |
| masque commun, bloc de 2, pondéré, s = 50 % | 50 % pour tout n ≤ 2 | 62,87 | ×3,52 |
| masque commun, bloc de 4, pondéré, s = 50 % | 50 % pour tout n ≤ 4 | 301,0 | ×16,9 |
| masque commun, bloc de 16, s = 50 % | 50 % pour tout n ≤ 16 | 3 673 | ×206 |
| masque commun, bloc de 16, pondéré, s = 50 % | 50 % pour tout n ≤ 16 | 4 276 | ×239 |
| masque commun, bloc de 16, pondéré, s = 25 % | 75 % pour tout n ≤ 16 | 53,40 | ×2,99 |

À octets égaux par passe de vérification de 2 jetons : chaque jeton avec son masque
à 25 % lit l'union, 92 % des colonnes, pour +2,1 % ; un masque commun lit 75 % pour
+11 %. À 4 jetons : l'union lit 99 % (aucun gain), le masque commun 75 % pour +34 %.

**Diagnostic** (`energie-smol.json`, une fenêtre, masques appliqués un par un sans
propagation) : part de l'énergie `Σ_j v_ij²` d'un jeton gardée à densité 0,5 —
top-k par jeton 0,956 à 0,986 selon l'entrée ; masque commun de bloc 2 : 0,913 à 0,967 ;
bloc 4 : 0,869 à 0,950 ; bloc 16 : 0,805 à 0,918 ; masque aléatoire (témoin) : 0,499 à
0,502, comme attendu. L'énergie perdue passe de 1,4–4,4 % à 8–20 % ; composée sur
30 couches et 4 entrées par couche, elle fait exploser la perplexité.

**Conclusion pour ce modèle** : sur un SwiGLU dense sans réentraînement, **la
sparsité des activations et la vérification spéculative ne se composent pas** : chaque
jeton garde son masque et la passe lit presque tout (union 0,90 à n = 4), ou les jetons
partagent un masque et la qualité s'effondre (×17 à n = 4, s = 50 %). Le coût
d'ignorer la sparsité, en régime disque avec spéculation, est donc d'environ 10 % des
octets à n = 4 et s = 50 %, pour une perte de qualité de +52 % sur ce modèle : on
l'ignore. **Réserve** : 135 M paramètres ; TEAL rapporte des pertes bien plus faibles à
7–70 B, et la corrélation entre jetons voisins peut y être plus forte. La même mesure
sur un modèle de 7 B et plus est le pas suivant ; ma passe numpy ne lit pas les
hybrides DeltaNet (Qwen3.5).

---

## 6. Le calcul pour la machine de Stone

Outil : `amortissement.py tables` ; journal : `amortissement-tables.json`.
Brouillon supposé résident en VRAM, 5 ms par jeton proposé (0,6 Go à 200 Go/s plus le
lancement) [calc., hypothèse].

### 6.1 Modèles denses

| Cas | NVMe | `T(n)` | sans spéc. | chaîne α=0,6 | α=0,8 | α=0,9 | arbre 10/passe |
|---|---|---:|---:|---:|---:|---:|---:|
| 70B Q4 (42 Go) : 7 Go VRAM, 11 Go RAM, 24 Go NVMe | 3 Go/s, sans recouvrement | 9,76 s | 0,10 | 0,25 | 0,50 | 0,99 | 1,02 |
| idem | 7 Go/s, recouvrement parfait | 3,43 s | 0,29 | 0,72 | 1,40 | 2,72 | 2,87 |
| 70B ~2,3 bits (20 Go) : 7 Go VRAM, 11 Go RAM, 2 Go NVMe | 3 Go/s, sans recouvrement | 2,43 s | 0,41 | 1,01 | 1,96 | 3,76 | 4,04 |
| idem | recouvrement parfait | 1,72 s | 0,58 | 1,40 | 2,72 | 5,15 | 5,64 |
| Qwen3.5-9B Q4_K_M tout en VRAM (5,67 Go) | — | 28 ms | 35 | 51 (k=2) | 70 (k=4) | 90 (k=7) | — |

(jetons/s ; `k` optimal pour la chaîne entre 9 et 50 dans les cas disque [calc.].)

Ce que dit ce tableau :

1. **Dans les cas disque, la spéculation multiplie le débit par `E` presque
   exactement** (k optimal grand, brouillon négligeable) : ×2,5 à `α = 0,6`, ×5 à
   `α = 0,8`, ×10 à `α = 0,9`. C'est le seul levier de l'étude qui ait cette pente.
2. **La quantification et la spéculation se multiplient** : passer de 4,8 à ~2,3 bits
   fait passer `T(n)` de 3,4–9,8 s à 1,7–2,4 s parce que le modèle sort presque du
   disque ; la spéculation multiplie ensuite par `E`. Le coût de qualité est celui de la
   quantification (étude 02), la spéculation n'en ajoute aucun.
3. **Pour un modèle qui tient en VRAM, `k` optimal est petit** (2 à 7) : `T(n)` est
   court, le brouillon pèse. SpecExec GPTQ le dit aussi : en 4 bits le gain tombe de
   ×18,7 à ×8,9 parce que la passe raccourcit [litt.].

### 6.1 bis Le substitut résident, transposé à la machine de Stone

SubSpec loge en VRAM une copie 4 bits de la cible et fait passer la cible 16 bits par le
PCIe depuis 128 Go de RAM. Chez Stone, la RAM (16 Go) impose une cible déjà quantifiée
(~4,8 bits) et la VRAM (8 Go) un substitut très bas (~2 bits). Cas calculés
(`amortissement.py`, `CAS_SUBSTITUT` ; PCIe 6,38 Go/s mesuré ; brouillon = octets du
substitut à 200 Go/s + 2 ms) [calc.] :

| Cas | `T(n)` | brouillon / jeton | sans spéc. | chaîne α=0,75 | α=0,85 | α=0,92 | arbre 10/passe |
|---|---:|---:|---:|---:|---:|---:|---:|
| cible 14B Q4_K_M (8,5 Go) en RAM, substitut ~2,1 bits (3,9 Go) en VRAM | 1,33 s | 21,5 ms | 0,75 | 2,48 | 3,73 | 5,92 | 6,46 |
| cible 9B Q4_K_M (5,7 Go) en RAM, substitut 2,5 Go en VRAM | 0,89 s | 14,5 ms | 1,12 | 3,69 | 5,56 | 8,82 | 9,63 |

Tout dépend de `α` entre la cible 4 bits et son substitut 2 bits. L'étude 02 mesure le
« same top p » (accord des argmax, donc `α` glouton sous forçage par le texte) de
Qwen3.5-4B IQ4_XS contre Q4_K_M : **91,9 ± 0,3 %** [mes., étude 02,
`echelle-4B/qwen35-4B-IQ4_XS-kld.log`] ; la mesure IQ2_XXS est en cours chez elle.
(Le cas 9B n'a de sens que pour un 9B qui ne tiendrait pas en VRAM ; il sert d'étalon.)

**Avec les accords mesurés** (§ 6.3 : IQ4_XS 91,9 %, IQ3_XXS 82,1 %, IQ2_XXS 65,8 %,
mesurés sur le 4B et supposés valoir pour la famille), un budget de 6 Go de VRAM pour le
substitut et une cible Q4_K_M en RAM (`substitut_mesure` dans le journal) [calc.] :

| Cible (Q4_K_M en RAM) | `T(n)` | sans spéc. | meilleur substitut qui loge | α | k opt. | jetons/s |
|---|---:|---:|---|---:|---:|---:|
| 14B (9,1 Go) | 1,42 s | 0,70 | IQ2_XXS (5,1 Go) | 0,66 | 7 | **1,75** (×2,5) |
| 20B (13,0 Go) | 2,03 s | 0,49 | aucun sous 6 Go | — | — | — |

Le substitut résident est donc borné, sur 8 Go de VRAM, par **la qualité par octet de la
quantification à ~2–3 bits** : à 2,9 bits l'accord tombe à 66 % et la chaîne ne rend que
2,9 jetons par passe au plus. Un substitut à 2 bits qui garderait 85 % d'accord
(ce que promettent les codes en treillis de l'étude 02, non mesuré ici) porterait le 14B
à ≈ 3,6 jetons/s [calc.]. **C'est le point exact où l'étude 02 et l'étude 05 se
multiplient** : la quantification extrême ne sert plus seulement à lire moins, elle
fabrique le brouillon.

### 6.2 MoE dont les experts viennent du disque

Hypothèses (étude 06, `plafonds-fichiers.md`) : `A` = poids toujours lus, supposés
résidents ; `R` = octets des experts routés d'un jeton ; une part `h` des experts
servie par le cache (hypothèse « succès uniforme » de l'étude 06) ; routage uniforme et
indépendant (pessimiste) [calc.] :

| Modèle | `A` / `R` (Go) | E / t | union de n=4 jetons (÷ n=1) | jetons/s sans spéc. (3–7 Go/s) | `k` optimal, α = 0,9 |
|---|---|---|---:|---:|---:|
| DeepSeek-V4-Flash Q2_K_XL (96,8 Go) | 6,69 / 2,10 | 256 / 6 | 3,86 | 1,6 – 3,8 | **0** |
| Qwen3.8-Flash-Next Q2_K_XL (78,9 Go) | 3,54 / 0,90 | 512 / 10 | 3,88 | 4,8 – 11,1 | **0** |
| gpt-oss-120b MXFP4 (63,4 Go) | 1,69 / 1,91 | 128 / 4 | 3,82 | 2,1 – 5,0 | **0** |
| Kimi-K2.6 Q2_K_XL (340,5 Go) | 8,52 / 6,90 | 384 / 8 | 3,88 | 0,45 – 1,05 | **0** |

**Condition de rentabilité.** Avec `k = 1`, la passe lit `U(2)/t ≈ 2 − t/E` fois les
experts d'un jeton et rend `1 + α` jetons : il faut `α > 1 − t/E`, soit `α > 0,977`
(DeepSeek-V4-Flash) ou `α > 0,98` (Qwen3.8-Flash-Next) [calc.]. Aucun brouillon n'y est.
La spéculation ne paie donc, pour un MoE fin lu du disque, que si **l'union réelle est
très en dessous de l'indépendance** (les jetons voisins partagent leurs experts) ou si
**l'ensemble d'experts de la vérification est borné** (AcceptMoE, MoE-Spec : avec perte).
L'union réelle des experts sur des jetons de brouillon n'est publiée, à ma
connaissance, pour aucun de ces modèles (§ 9).

**Forme générale** [calc.] : quand les octets venus du disque sont dominés par les
experts routés, la spéculation paie si et seulement si

    E(α, k) > U(k + 1) / t

c'est-à-dire si le nombre de jetons rendus par passe dépasse le facteur de croissance
de l'union. À la limite des experts fins (`t·(k+1) ≪ E`), `U(k+1)/t → k + 1 > E(α, k)`
pour tout `α < 1` : **la spéculation ne paie jamais** sans réutilisation d'experts.

### 6.3 Mesures de α et de la courbe c(n) sur la carte

**Courbe c(n) : temps d'une passe de `n` jetons, Qwen3.5-4B Q4_K_M tout en VRAM.**
`llama-bench -p n -n 0 -ngl 99 -r 5`, quatre séries ABBA (ordre croissant, décroissant,
décroissant, croissant). Seuil déclaré avant lecture (`resume_cn.py`) : écart-type
relatif < 10 % par série. **Il n'est atteint pour aucun `n`** : la carte était partagée
avec un `llama-perplexity` d'un autre agent (4 Go de VRAM pris, utilisation 0 à 42 %
relevée avant et après chaque série) et le processeur à 100 %. Les chiffres qui suivent
sont **indicatifs** (médiane des 4 séries, journal `cn/resume-4B-ngl99.txt`) [mes.,
bruité] :

| n | 1 | 2 | 4 | 8 | 16 | 32 | 64 | 128 | 256 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| T(n) (ms) | 30,3 | 31,1 | 30,6 | 40,3 | 41,0 | 38,4 | 48,4 | 77,2 | 139,5 |
| T(n)/T(1) | 1,00 | 1,03 | 1,01 | 1,33 | 1,35 | 1,27 | 1,60 | 2,55 | 4,60 |

Ce que la mesure dit malgré le bruit : jusqu'à 32 jetons, une passe coûte au plus
~1,3 fois une passe d'un jeton ; le coude est entre 32 et 128, ce que prévoit
`n* ≈ 30` du § 1.3 pour des poids en VRAM. À refaire sur une machine au repos.

**`α` glouton entre Qwen3.5-4B et Qwen3.5-9B (brouillon par petit modèle).** Mesure
par `llama-perplexity --kl-divergence` : le « same top p » est la part des positions où
l'argmax du 4B égale celui du 9B, le texte (WikiText-2) servant de préfixe. C'est le
taux d'acceptation glouton de la première position proposée ; en génération réelle, le
préfixe est le texte de la cible elle-même, en général plus prévisible : la mesure est
plutôt une borne basse.

| Brouillon → cible | same top p (α glouton, 1re position) | KLD moyenne | E(α, 4) | E(α, 8) | borne 1/(1−α) | Journal |
|---|---:|---:|---:|---:|---:|---|
| témoin : Qwen3.5-4B Q4_K_M contre lui-même | **100,000 %** | 0,000000 | — | — | — | `temoin-alpha-4B-contre-lui-meme.log` |
| Qwen3.5-4B Q4_K_M → Qwen3.5-9B Q4_K_M | **76,8 ± 0,9 %** | 0,279 | 3,16 | 3,91 | 4,31 | `alpha-4B-contre-9B-kld.log` |
| Qwen3.5-4B IQ4_XS (4,76 bits) → Qwen3.5-4B Q4_K_M (5,19 bits) | 91,9 ± 0,3 % | 0,029 | 4,25 | 6,57 | 12,35 | étude 02 |
| Qwen3.5-4B IQ3_XXS (3,60 bits) → 4B Q4_K_M | 82,1 ± 0,4 % | 0,148 | 3,50 | 4,64 | 5,59 | étude 02 ; relancé ici : identique au dernier chiffre (`alpha-4B-IQ3_XXS-reproduction-8fen.log` ; en mode KL, llama-perplexity prend les 40 fenêtres du fichier de base et ignore `--chunks` : c'est une preuve de déterminisme, pas un second chemin) |
| Qwen3.5-4B IQ2_XXS (2,91 bits) → 4B Q4_K_M | 65,8 ± 0,5 % | 0,608 | 2,56 | 2,86 | 2,92 | étude 02 |
| Qwen3.5-9B Q2_K (3,41 bits, requantifié du Q4_K_M, **sans imatrix**) → 9B Q4_K_M | **34,0 ± 1,0 %** | 2,60 | 1,51 | 1,52 | 1,52 | `alpha-9B-Q2_K-contre-9B-kld.log` |

[mes. ; E calculé sous l'hypothèse α constant.] 8 fenêtres de 512 jetons, seconde moitié
(2 048 positions) pour 4B → 9B ; perplexités 10,15 (4B) contre 8,47 (9B) sur ces
fenêtres. Le témoin tombe à 100 % exactement quand la cible est le brouillon : l'outil
mesure bien l'accord. **Lecture** : un brouillon de la même famille, 2 fois plus petit,
rend au plus 4,3 jetons par passe en chaîne ; une copie quantifiée de la cible elle-même
(substitut) s'accorde bien mieux (91,9 % à ~4,3 bits), d'où la longueur d'acceptation de
SubSpec. **Le substitut naïf à ~3,4 bits s'effondre** : Q2_K de llama.cpp, requantifié
depuis le Q4_K_M sans matrice d'importance, fait passer la perplexité de 8,47 à 105
(×12,4) et l'accord à 34 % [mes.] ; il ne rend que 1,5 jeton par passe. Ce n'est pas
la limite de 2 bits (l'étude 02 mesure IQ2_XXS avec imatrix), c'est la preuve qu'un
substitut se fabrique avec la meilleure quantification disponible, pas la plus simple :
le § 6.1 bis ne vaut qu'avec un substitut dont l'accord dépasse ~85 %.

---

## 7. Comment chaque technique se compose avec la quantification et le déchargement

| Technique | × quantification (étude 02) | × déchargement / disque | Perte | Sous Vulkan aujourd'hui |
|---|---|---|---|---|
| Spéculation, dense | se multiplient ; une cible plus petite raccourcit `T(n)` et baisse un peu `k` optimal | **le meilleur cas** : `n*` ≈ 1 000, arbres gratuits | aucune | chaîne seulement |
| Spéculation, MoE fin | idem | **nulle ou négative** sans budget d'experts | aucune ; avec budget : faible | chaîne, sans budget |
| Substituts quantifiés résidents (SubSpec) | **c'est** de la quantification, au service du brouillon | conçu pour lui : τ ≈ 29 | aucune | non (PyTorch + CUDA) |
| MTP natif | le module MTP se quantifie comme le reste | doit être résident | aucune | oui (`draft-mtp`) |
| n-grammes | indépendant | gratuit | aucune | oui |
| Sparsité par jeton (TEAL, CATS) | compatible si les poids sont rangés par colonnes ; la quantification par blocs de lignes l'empêche | ne survit pas à la vérification (union 0,90 à n=4) | 1–2 % à 50 % [litt.] ; § 5.5 | non |
| Masque commun au bloc | idem | survit : lit `(1 − s)` pour tout `n` | § 5.5 | non |
| Neurones chauds (PowerInfer) | compatible | demande une loi de puissance (ReLU) | réentraînement pour reluifier | non (CUDA) |
| Prédiction d'experts | indépendant | cache la latence, ne réduit pas les octets | aucune | partiel (déchargement d'experts dans llama.cpp, sans prédicteur) |

---

## 8. Ce que je recommande de construire (pour l'arbitre)

1. **Le brouillon le moins cher et le plus juste est la cible elle-même, quantifiée
   très bas et résidente** (SubSpec), ou son module MTP. Sur la machine de Stone, une
   copie à 2–3 bits d'un 70B pèse 18 à 26 Go et ne loge pas ; pour un 14B elle loge
   (5,1 Go en IQ2_XXS) mais n'accorde que 66 % [mes. sur le 4B]. Le budget de VRAM
   impose donc : **MTP natif** (un bloc, quelques centaines de Mo) pour les grands
   modèles, substitut quantifié pour les modèles de 10 à 15 B, et la meilleure
   quantification à 2 bits possible (étude 02) pour ce substitut. Ce compromis n'est
   publié nulle part (SubSpec avait toute la RAM voulue). Premier pas mesurable :
   l'accord du MTP natif de Qwen3.5-9B (téléchargement demandé).
2. **Vérifier des arbres, pas des chaînes.** C'est ce qui manque à llama.cpp. Une
   chaîne plafonne à `1/(1 − α)` (5 à `α = 0,8`) ; les arbres de SpecExec rendent 10 à
   20 jetons par passe, et même contre un autre arbre (SpecInfer, échantillonné) le
   choix des continuations les plus probables gagne ×1,9 à ×3,2 [litt., tableaux 1–2].
3. **Pour les MoE, ne vérifier que dans les experts déjà en mémoire** (AcceptMoE), et
   mesurer la perte.
4. **Ne pas investir dans la sparsité des activations par jeton** pour le régime disque
   sur des modèles SwiGLU : mesurée ici, elle s'évanouit sous la vérification et n'a pas
   de neurones chauds à mettre en cache.

---

## 9. Ce que je crois manquer dans le monde

1. **La spéculation avec des poids lus du NVMe quand la RAM est plus petite que le
   modèle.** SpecExec (RAM 140–192 Go), SubSpec (128 Go), Sequoia, TriForce lisent les
   poids depuis la RAM par le PCIe ; LLM in a flash lit le Flash mais sans spéculation ;
   DraftExpert lit le Flash d'un téléphone avec des MoE de 16 B. Sur 16 Go de RAM et un
   NVMe à 3–7 Go/s, le calcul du § 6.1 donne 0,1–0,3 jeton/s pour un 70B Q4 seul et
   1,2–2,9 jetons/s avec un arbre de 10 jetons par passe : **un facteur 10 non mesuré**.
2. **Des arbres sous Windows sans CUDA.** llama.cpp (Vulkan) vérifie des chaînes : à
   `α = 0,8`, au plus 5 jetons par lecture ; SpecExec en obtient 10 à 20 sur la même
   cible. Le facteur ×2 à ×4 que l'arbre apporte précisément quand le disque est le
   plafond n'est disponible que sous PyTorch + CUDA.
3. **Les courbes d'union d'experts réelles des MoE fins de 2026 (256–512 experts,
   6–10 par jeton) sur des jetons de brouillon.** La rentabilité dépend entièrement de
   l'écart entre l'union réelle et `E(1 − (1 − t/E)^n)` ; Cascade le mesure sur Mixtral
   (2 sur 8), AcceptMoE et EcoSpec en déduisent des gains, aucun ne publie la courbe
   `U(n)` pour un modèle que la machine de Stone peut lire.
4. **Le compromis VRAM du brouillon contre VRAM de la cible.** Chaque Go donné au
   brouillon (substituts, EAGLE, MTP, cache KV du brouillon) est un Go de la cible qui
   repart sur le PCIe ou le disque. Sur 8 Go, l'optimum de ce partage n'est publié par
   personne : SubSpec fixe le plafond de VRAM, il ne l'optimise pas.
5. **Des arbres de vérification pour les hybrides à règle delta.** Les modèles que
   Stone peut faire tourner en 2026 (Qwen3.5/3.6/3.8) sont des hybrides Gated DeltaNet ;
   un arbre de 256 nœuds y demande 12 Gio d'états intermédiaires si on les garde
   (Qwen3.5-9B, 48 Mio par nœud) [calc.]. STree résout le cas des SSM ; je n'ai trouvé
   aucune vérification en arbre publiée pour la règle delta.
6. **La sparsité des activations sans reluification ne survit pas à la vérification**
   (union 0,895 à n = 4, 50 % par jeton, mesuré ici) ; la mesure de la qualité d'un
   masque commun au bloc pour un FFN dense est au § 5.5.

---

## 10. Ce qui pourrait être faux

- **Le modèle de mesure de la sparsité est petit** (135 M). Les grands modèles sont
  plus creux (TEAL le dit pour 70B) ; la corrélation entre jetons voisins peut y être
  plus forte. Les unions mesurées sont celles d'un modèle SwiGLU de 135 M, pas de
  Qwen3.5-9B (architecture hybride DeltaNet), que ma passe numpy ne sait pas lire.
- **Le masque « top-k par jeton » n'est pas exactement TEAL** (seuils calibrés, densité
  variable par jeton, répartition gloutonne entre couches) ; il a la même densité
  moyenne.
- **L'hypothèse α constant et indépendant** surestime `E` pour les longues chaînes.
- **Le routage indépendant** est pessimiste pour les MoE ; si les jetons voisins
  partagent beaucoup d'experts, la conclusion « k optimal = 0 » tombe.
- **`F = 20 TFLOP/s`** n'est pas mesuré ; `n*` est un ordre de grandeur.
- **Le NVMe n'est pas encore mesuré** (étude 01) ; 3 et 7 Go/s sont des bornes.
- **Le chiffre DeepSeek-V3 (85–90 %, ×1,8)** vient de ma mémoire du rapport ; je n'ai
  pas pu relire la section 5.4.3 en entier. À vérifier avant de le citer ailleurs.
- **« Same top p » n'est pas exactement `α`** : c'est l'accord des argmax sous forçage
  par un texte de WikiText-2, pas sur le texte que la cible génère elle-même ; il ne
  mesure que la première position ; et il ne dit rien de l'échantillonnage à
  température non nulle. L'accord en génération réelle est en général plus haut
  (texte plus prévisible), donc mes `E` sont plutôt des bornes basses, mais je ne l'ai
  pas mesuré.
- **Les accords des substituts IQ viennent du 4B** ; un 14B se quantifie en général
  mieux à bits égaux : le ×2,5 du § 6.1 bis est plutôt pessimiste.
- **Le Q2_K du 9B est requantifié depuis un Q4_K_M sans imatrix** : son effondrement
  (34 %) mesure ce chemin-là, pas ce que vaut 2 bits bien faits.
- **Les machines étaient partagées** : d'autres agents faisaient tourner
  `llama-quantize`, `llama-perplexity` et des scripts Python pendant mes mesures (CPU à
  100 %, 1,3 Go de RAM libre, 4 à 7 Go de VRAM pris). Les perplexités ne dépendent pas
  de la charge ; les temps, si.

---

## 11. Sources (consultées le 2026-10-15)

Articles (v1 ; dernière révision) :
- Leviathan, Kalman, Matias, *Fast Inference from Transformers via Speculative Decoding*, https://arxiv.org/abs/2211.17192 (2022-11-30 ; 2023-05-18), ICML 2023.
- Chen et al., *Accelerating Large Language Model Decoding with Speculative Sampling*, https://arxiv.org/abs/2302.01318 (2023-02-02), Chinchilla 70B ×2–2,5.
- Cai et al., *Medusa*, https://arxiv.org/abs/2401.10774 (2024-01-19 ; 2024-06-14).
- Li et al., *EAGLE-2*, https://arxiv.org/abs/2406.16858 (2024-06-24 ; 2024-06-30).
- Li et al., *EAGLE-3*, https://arxiv.org/abs/2503.01840 (2025-03-03 ; 2025-04-23).
- Gloeckle et al., *Better & Faster LLMs via Multi-token Prediction*, https://arxiv.org/abs/2404.19737 (2024-04-30), jusqu'à ×3 en inférence avec 4 jetons prédits.
- DeepSeek-AI, *DeepSeek-V3 Technical Report*, https://arxiv.org/abs/2412.19437 (2024-12-27 ; 2025-02-18).
- Chen, Liang, Liu, *DFlash*, https://arxiv.org/abs/2602.06036 (2026-02-05 ; 2026-05-28), ICML 2026.
- Fu et al., *Lookahead Decoding*, https://arxiv.org/abs/2402.02057 (2024-02-03).
- Elhoushi et al., *LayerSkip*, https://arxiv.org/abs/2404.16710 (2024-04-25 ; 2024-10-18), ACL 2024.
- Zhao et al., *QSpec*, https://arxiv.org/abs/2410.11305 (2024-10-15 ; 2025-10-02), EMNLP 2025.
- Wang et al., *SubSpec*, https://arxiv.org/abs/2509.18344 (2025-09-22 ; 2025-10-08), NeurIPS 2025 ; HTML v2 lu pour les tableaux.
- Chan et al., *ShadowSpec*, https://icml.cc/virtual/2026/75131 (ICML 2026, atelier AdaptFM).
- Wu et al., *STree*, https://arxiv.org/abs/2505.14969 (2025-05-20 ; 2025-10-27), NeurIPS 2025.
- Svirschevski et al., *SpecExec*, https://arxiv.org/abs/2406.02532 (2024-06-04 ; 2024-11-30) ; HTML v3 lu pour les tableaux.
- Chen et al., *Sequoia*, https://arxiv.org/abs/2402.12374 (2024-02-19 ; 2025-07-05).
- Sun et al., *TriForce*, https://arxiv.org/abs/2404.11912 (2024-04-18 ; 2024-08-04), COLM 2024.
- Zhang et al., *Dovetail*, https://arxiv.org/abs/2412.18934 (2024-12-25 ; 2025-09-09).
- Zhuge et al., *SpecOffload*, https://arxiv.org/abs/2505.10259 (2025-05-15 ; 2025-05-21).
- Saxena et al., *Utility-Driven Speculative Decoding for MoE (Cascade)*, https://arxiv.org/abs/2506.20675 (2025-06-17).
- Huang et al., *MoESD*, https://arxiv.org/abs/2505.19645 (2025-05-26 ; 2026-02-16), NeurIPS 2025.
- McDanel et al., *MoE-Spec*, https://arxiv.org/abs/2602.16052 (2026-02-17).
- Liang et al., *AcceptMoE*, https://arxiv.org/abs/2608.02989 (2026-08-04).
- Xie et al., *EcoSpec (Less Experts, Faster Decoding)*, https://arxiv.org/abs/2607.12696 (2026-07-14).
- Pan et al., *EVICT (Making Every Verified Token Count)*, https://arxiv.org/abs/2605.00342 (2026-05-01 ; 2026-09-05).
- Han, *DraftExpert*, https://arxiv.org/abs/2607.24434 (2026-07-27).
- Skliar et al., *Mixture of Cache-Conditional Experts*, https://arxiv.org/abs/2412.00099 (2024-11-27 ; 2025-06-24), TMLR.
- Eliseev, Mazur, *Fast Inference of MoE LMs with Offloading*, https://arxiv.org/abs/2312.17238 (2023-12-28).
- Song et al., *ProMoE*, https://arxiv.org/abs/2410.22134 (2024-10-29 ; 2025-09-01).
- Liu et al., *Deja Vu*, https://arxiv.org/abs/2310.17157 (2023-10-26), ICML 2023.
- Song et al., *PowerInfer*, https://arxiv.org/abs/2312.12456 (2023-12-16 ; 2024-12-12), SOSP 2024.
- Xue et al., *PowerInfer-2*, https://arxiv.org/abs/2406.06282 (2024-06-10 ; 2024-12-12).
- Alizadeh et al., *LLM in a flash*, https://arxiv.org/abs/2312.11514 (2023-12-12 ; 2024-07-30), ACL 2024.
- Mirzadeh et al., *ReLU Strikes Back*, https://arxiv.org/abs/2310.04564 (2023-10-06).
- Lee et al., *CATS*, https://arxiv.org/abs/2404.08763 (2024-04-12 ; 2024-11-03).
- Liu et al., *TEAL*, https://arxiv.org/abs/2408.14690 (2024-08-26 ; 2025-02-25), ICLR 2025.
- Zhang et al., *R-Sparse*, https://arxiv.org/abs/2504.19449 (2025-04-28), ICLR 2025.
- Shrestha et al., *Polar Sparsity*, https://arxiv.org/abs/2505.14884 (2025-05-20 ; 2025-11-11), NeurIPS 2025.
- Song et al., *Turbo Sparse*, https://arxiv.org/abs/2406.05955 (2024-06-10 ; 2024-06-11).
- Wang et al., *Accelerate Speculative Decoding with Sparse Computation in Verification*, https://arxiv.org/abs/2512.21911 (2025-12-26).

Dépôts lus (licence vérifiée par l'API GitHub et le fichier à la racine, 2026-10-15) :
- ggml-org/llama.cpp — MIT — commit e467e5b (2026-10-15) : `common/speculative.cpp`, `docs/speculative.md`.
- NYCU-EDgeAi/subspec — Apache-2.0 — commit 25366ac (2026-08-11).
- yandex-research/specexec — aucune licence déclarée — commit c7f24b3 (2024-11-05).
- FasterDecoding/TEAL — MIT — commit fb7373c (2025-02-14) : `kernels/sparse_gemv.py`, `teal/greedyopt.py`.
- SafeAILab/EAGLE — Apache-2.0 (LICENSE lu). z-lab/dflash — MIT. FasterDecoding/Medusa — Apache-2.0.
  hao-ai-lab/LookaheadDecoding — Apache-2.0. ScalingIntelligence/CATS — MIT.
  Tiiny-AI/PowerInfer (anciennement SJTU-IPADS) — MIT. facebookresearch/LayerSkip — CC BY-NC 4.0.
  FMInference/DejaVu, Infini-AI-Lab/Sequoia, Infini-AI-Lab/TriForce, VITA-Group/R-Sparse,
  apoorvumang/prompt-lookup-decoding — aucune licence déclarée (lecture seulement).

Modèles : Qwen/Qwen3.5-9B `config.json` (https://huggingface.co/Qwen/Qwen3.5-9B) ;
unsloth/Qwen3.5-9B-MTP-GGUF (2026-05-16) ; AtomicChat/Qwen3.5-9B-DFlash-GGUF (2026-07-22) ;
SmolLM2-135M-Instruct F16 (Apache-2.0, métadonnées GGUF).
