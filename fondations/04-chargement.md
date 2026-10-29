# Étude 04 : le chargement à la demande, le déchargement et le recouvrement

Fondations de troncons, 2026-10-15. Lire `SOCLE.md` d'abord.

Cette étude répond à une seule question : quand un modèle ne tient pas dans la mémoire, où sont
ses poids à l'instant où un calcul en a besoin, combien d'octets faut-il déplacer par jeton, par
quel étage, et quelle part de ce déplacement peut se cacher derrière le calcul. Elle passe en
revue tout ce qui fait tourner un modèle plus gros que la mémoire, du « couche par couche »
de 2022 aux moteurs de 2026 qui lisent les experts d'un MoE sur le disque, et elle juge chaque
technique avec la même règle : les octets lus par jeton, divisés par le débit de chaque étage
de la machine de Stone.

Étiquettes : **[lit.]** littérature (éditeur, non reproduit) ; **[calc.]** calculé ;
**[mes.]** mesuré ici. Toutes les sources ont été consultées le 2026-10-15 ; leurs dates de
publication sont au § 10.

Outils et journaux de cette étude :
- `outils/chargement_pcie.py` : banc RAM → PCIe → VRAM par le runtime CUDA de llama.cpp,
  lien lu par NVML ; journaux `fondations/journaux/04-chargement/pcie-*.json`.
- `outils/chargement_localite.py` : localité des experts sur une trace de routage, et succès
  des caches LRU, LFU, statiques et Belady ; témoins synthétiques ; journaux `localite-*.json`.
- `outils/chargement_juge.py` : le juge physique (octets par jeton et par étage), validé sur
  cinq mesures publiées ; journaux `juge-*.json`, `juge-stone.txt`.

---

## 0. En bref

1. **Le décodage d'un jeton est un problème d'octets, pas de calcul.** Tous les systèmes lus
   le disent et leurs chiffres le confirment : FlexGen passe plus de 99,5 % de son temps à
   transférer des poids [lit., cité par PowerInfer] ; HOBBIT mesure 80 ms pour charger une
   couche de Mixtral contre 3 ms pour la calculer sur une RTX 4090 [lit.]. Le juge
   `octets ÷ débit` suffit à borner chaque technique, et il tient sur cinq mesures publiées
   (aucune ne le dépasse ; divisés par 10, les débits le font tomber sur quatre sur cinq) [calc.].
2. **La machine de Stone a deux étages lents de même débit, et un troisième plus lent qu'on ne
   le croit.** Disque NVMe : plafond 7,877 Go/s [calc.]. PCIe de la carte : 6,4 Go/s mesurés
   pour une copie seule, parce que **le lien redescend en Gen3 quand la carte ne calcule pas**
   (relevé NVML et nvidia-smi : Gen1 au repos, Gen3 pendant les copies, Gen4 sous charge) [mes.].
   RAM : **un seul module DDR5-5200, 41,6 Go/s de plafond** [calc., relevé de l'étude 01],
   soit 5 fois moins que la VRAM (169 à 227 Go/s lecture + écriture mesurés selon l'état de
   performance, plafond 256) [mes.].
3. **Pour un MoE, le cache n'est utile que parce que les experts se répètent d'un jeton au
   suivant, et ils se répètent peu.** Réutilisation adjacente publiée : Mixtral 14 à 28 % du
   premier choix contre 12,5 % au hasard ; Qwen3-30B-A3B 0,444 contre 0,223 « au hasard » ;
   Qwen3.6-35B-A3B « environ un quart » de l'ensemble d'une couche [lit.]. Un expert reste en
   cache 5 jetons (Mixtral) à 26 jetons (Qwen1.5-MoE) sous LRU [lit.]. Un cache LRU de 13,4 %
   des experts sert 65,9 % des demandes sur Qwen3-30B (Belady, l'optimum : 79,1 %) [lit.].
4. **Ce que cela donne sur la machine de Stone** (juge, débits RAM et disque encore
   supposés en attendant l'étude 01) [calc.] :
   - ~~Qwen3-Next-80B-A3B en Q4_K_M (48 Go) : environ **11 jetons/s sans aucune localité** ;~~
   - ~~Qwen3.8-Flash-Next (180 Go de paramètres) : 5,8 jetons/s sans localité, 10 jetons/s
     dès 53 % de succès du cache ;~~
   - ~~Qwen3-235B-A22B : 0,9 jeton/s sans localité, 5 jetons/s exigent 83 % de succès avec
     9 % du modèle en mémoire rapide, au-delà de Belady mesuré à 13,4 % sur un modèle voisin.~~

   Barré le 2026-10-15 : ces trois lignes supposaient un disque à 6,7 Go/s. Les premières
   lectures du banc de l'étude 01 (journal `01-machine/disque-balayage.jsonl`, provisoire, non
   commité, machine chargée par d'autres agents) donnent **2,4 Go/s en lecture aléatoire de
   1 Mio et 3,0 Go/s à 4 Mio**, 3,8 Go/s au mieux en séquentiel, 0,22 Go/s à 4 Kio. Avec
   2,4 Go/s (`juge-stone-disque-2.4.txt`) :
   - Qwen3-Next-80B-A3B en Q4_K_M (48 Go) : **3,9 jetons/s sans localité**, 10 jetons/s
     exigent 74 % de succès ;
   - Qwen3.8-Flash-Next (180 Go de paramètres) : 2,1 jetons/s sans localité, 5 jetons/s
     dès 66 % de succès ;
   - Qwen3-235B-A22B : 0,33 jeton/s sans localité, 5 jetons/s exigent 94 % de succès avec
     9 % du modèle en mémoire rapide, très au-delà de Belady mesuré à 13,4 % sur un modèle
     voisin (79,1 %).

   Le disque de cette machine est donc l'étage qui décide, et sa vitesse à la taille d'un
   expert est la première mesure à fixer.
   Le levier n'est donc pas un seul : c'est le produit **succès du cache × octets par expert
   × débit disque effectif à la taille d'un expert**, et la part de la latence que la
   prédiction cache.
5. **Ce qui manque dans le monde** (détail au § 7) : aucun moteur publié ne lit les experts
   sur le disque sous Windows jusque dans la VRAM ; aucune publication ne tient compte de
   l'état du lien PCIe d'un portable (un facteur 2 sur les stratégies qui en dépendent) ;
   aucune courbe « succès en fonction du budget » n'existe pour les MoE fins de 2026 aux
   budgets d'un portable (5 à 20 % des experts) ; personne ne se sert du report d'expert
   (KTransformers) pour absorber un défaut de lecture au lieu d'attendre ; personne n'a réuni
   dans un même moteur les quatre réponses à un défaut (attendre, reporter, substituer une
   copie basse précision, re-router vers un expert présent) sous un budget de qualité mesuré.

---

## 1. Le cadre : la loi du chargement

### 1.1 Octets par jeton et débits

Au décodage (lot 1), chaque jeton lit chaque poids actif une fois. Pour un étage i de débit
B_i qui doit livrer O_i octets par jeton, le temps est t_i = O_i / B_i. Si les étages
travaillent en parallèle (recouvrement parfait), le débit en jetons par seconde est borné par

    d ≤ 1 / max_i (O_i / B_i)                      (borne de recouvrement)

et, s'ils se suivent sans recouvrement,

    d = 1 / Σ_i (O_i / B_i)                         (borne en série)

La « part cachée par le recouvrement » d'un système se lit entre ces deux bornes :
part = (Σ t_i − t_mesuré) / (Σ t_i − max t_i).

### 1.2 Le MoE en trois grandeurs

Pour un MoE de L couches MoE, E experts routés par couche, k experts par jeton, bpp bits par
poids, j'écris [calc., outil `chargement_juge.py`] :

    A = octets toujours lus (attention, experts partagés, routeurs, normes, tête)
    e = octets d'un expert routé = P_experts / (E · L) · bpp / 8
    R = octets routés par jeton = k · L · e

Une part h_v des octets routés vient de la VRAM, h_r de la RAM, h_s = 1 − h_v − h_r du
disque. Le disque doit livrer h_s · R octets par jeton : c'est presque toujours l'étage
limitant, et **h (le taux de succès du cache) est la grandeur qui décide de tout**. À
l'inverse, une mesure publiée de d jetons/s prouve un succès d'au moins

    h_min = 1 − (B_disque / d) / R

ce qui permet de lire la localité dans une mesure qui ne la publie pas (§ 4.3).

### 1.3 La granularité

Un étage n'atteint son débit qu'au-delà d'une taille de requête et d'une profondeur de file.
Chiffres publiés : flash du M1 Max, plus de 6 Gio/s en lecture linéaire, lectures aléatoires
« de 32 Kio ou plus sur plusieurs fils » nécessaires [lit., LLM in a flash] ; UFS 4.0,
450 Mo/s à 4 Kio contre 4 Go/s à 512 Kio [lit., PowerInfer-2] ; le cache de pages du
système livre 148 Mo/s là où le même disque donne 1 496 Mo/s en lectures explicites à la
taille d'un expert, avec 25 000 à 50 000 défauts de page par jeton [lit., moe-stream] ; dans
un GGUF, les trois matrices d'un expert sont rangées dans trois tenseurs différents, d'où
6 912 pages touchées par expert contre 192 après regroupement [lit., llama.cpp #27149].
Sur la carte, un transfert synchrone coûte une latence fixe d'environ 33 µs (64 Kio passent
à 1,5 Go/s, 256 Mio à 6,4 Go/s) [mes., pcie-1 ; inclut l'appel Python].

### 1.4 Les étages de la machine de Stone

| Étage | Plafond | Mesuré | Source |
|---|---|---|---|
| Disque NVMe (PCIe 4.0 ×4) | 7,877 Go/s | provisoire (étude 01, non commité, machine chargée) : aléatoire 2,4 Go/s à 1 Mio, 3,0 à 4 Mio, 0,76 à 64 Kio, 0,22 à 4 Kio ; séquentiel 3,8 au mieux | [calc.] ; [mes. par l'étude 01] |
| RAM (1 module DDR5-5200, 64 bits) | 41,6 Go/s | à venir (étude 01) | [calc.] |
| PCIe carte, Gen4 ×8 | 15,754 Go/s | 6,38 Go/s H2D épinglé à 256 Mio, lien en Gen3 | [mes., pcie-1] |
| PCIe carte, Gen3 ×8 (état réel des copies seules) | 7,877 Go/s | 81 % de ce plafond | [mes.] |
| PCIe carte, sous charge (Gen4 vu par NVML) | 15,754 Go/s | 7,6 Go/s, carte partagée avec un autre programme : plancher | [mes., pcie-2] |
| Mémoire paginable au lieu d'épinglée | | −21 % (5,07 contre 6,38 Go/s) | [mes.] |
| VRAM GDDR6 128 bits | 256 Go/s | 169 Go/s (horloge mémoire 6 001 MHz) ; 227 Go/s en P0 | [mes.] |
| Cache L2 | 32 Mio (lu sur la carte) | copies de 16 Mio à 719 Go/s | [mes.] |
| Copie PCIe pendant un trafic VRAM | | H2D inchangé (6,42 → 6,41), VRAM −5,6 % | [mes., pcie-1] |

**Découverte de cette étude** [mes.] : sur ce portable, l'état de performance de la carte
règle à la fois la génération du lien PCIe et l'horloge de la VRAM. Pendant une passe de
copies seules, nvidia-smi a relevé le lien en Gen1 (12 relevés), Gen2 (66), Gen3 (119) et
Gen4 (15 seulement), l'horloge mémoire passant de 405 à 8 001 MHz
(`lien-nvidia-smi-passe-1b.csv`). Les passes de copies seules donnent 6,4 Go/s (Gen3) et
167 à 169 Go/s de VRAM, ce qui correspond vraisemblablement à l'horloge de 6 001 MHz relevée
(12 Gbit/s × 128 bits = 192 Go/s de plafond, 88 % atteints) ; la passe faite en P0 (une autre
charge tenait la carte haute) donne 227 Go/s. Un
pipeline qui ne fait que copier laisse donc le lien en Gen3 : **il faut que la carte calcule
pendant qu'on copie**, ce qui tombe bien, c'est le but du recouvrement. Aucune publication
lue ne mentionne cet effet ; toutes calculent avec le débit nominal du lien.

Limite dite : les passes 2 et suivantes ont eu lieu pendant que d'autres agents calculaient
sur la carte (llama-imatrix, llama-perplexity, occupation relevée à 93 %). Le journal
`pcie-2-carte-partagee-l2-faux.json` le porte ; il avait aussi un L2 mal lu (attribut 89 au
lieu de 38, corrigé dans l'outil). Une passe propre reste à faire quand la carte sera libre.

---

## 2. Modèles denses : couche par couche et déchargement des poids

### 2.1 AirLLM (couche par couche)

- **Mécanisme.** Le modèle est découpé en un fichier par couche ; à chaque passe avant, la
  couche ℓ est lue du disque, copiée sur la carte, calculée, libérée ; un fil prépare la
  couche ℓ+1 pendant le calcul de ℓ (`air_llm/airllm/airllm_base.py`, `ThreadPoolExecutor`
  à un fil, mémoire épinglée bornée). Depuis 2026, un crochet par expert ne lit que les
  experts routés d'un MoE (« Kimi K3 » : environ 1 Go touché par couche sur environ 55 Go).
- **Ce qu'il publie.** De la mémoire, pas de vitesse : « 70B sur une carte de 4 Go »,
  « DeepSeek-V3 671B sur environ 12 Go », « Kimi K3 en 3,72 Go » [lit., README 2026-09]. Le
  préchargement d'une couche y est crédité de « 10 % » de gain (2023-12-18) [lit.].
- **Ce que dit le juge.** Un 70B dense en FP16 lit 140 Go par jeton ; à 7,877 Go/s, au mieux
  **17,8 s par jeton** sur la machine de Stone [calc.]. AirLLM résout la mémoire de pointe et
  rien d'autre : c'est exactement la lecture littérale de « sans ram ni rien », et c'est
  pourquoi elle ne suffit pas.
- **Windows sans CUDA.** PyTorch avec CUDA ; tourne sous Windows. Licence Apache-2.0.
  Maturité : paquet PyPI répandu, sans mesure de vitesse publiée.

### 2.2 DeepSpeed ZeRO-Inference

- **Mécanisme.** Poids épinglés en RAM ou sur NVMe, chaque couche diffusée vers la carte au
  moment du calcul, une ou quelques couches résidentes, ce qui libère la carte pour de grands
  lots [lit., blog 2022-09-09]. Le billet de 2023 annonce « 20× » par quantification des
  poids et déchargement du cache KV [lit., titre seul lisible].
- **Chiffres.** FlexGen mesure ZeRO-Inference à 0,01 jeton/s sur OPT-175B (T4, lot 1) [lit.].
- **Windows.** Linux en pratique. Maturité : maintenu, orienté débit par lot.

### 2.3 FlexGen (ICML 2023)

- **Mécanisme.** Ordonnancement en zigzag par blocs : on garde une couche le temps de la
  passer sur tout un bloc de lots, ce qui amortit la lecture des poids sur bls séquences.
  Modèle de coût par couche avec recouvrement parfait de cinq flux :
  `T_gen = max(ctog, gtoc, dtoc, ctod, comp)`, le terme disque valant
  `dtoc = ((8h₁² + 4h₁h₂)·w_d + 4·bls·(s + n/2)·h₁·c_d + 2·bls·h₁·h_d) / B_disque`
  (w_d, c_d, h_d : parts des poids, du cache KV et des activations sur disque) ; la
  politique (11 variables) est choisie par programmation linéaire [lit.].
- **Chiffres.** T4 16 Go, 208 Go de RAM, SSD 1,5 To (environ 2 Go/s en lecture), lien
  carte–RAM 12 Go/s. Débit de génération (jetons/s, invite 512) : OPT-175B 0,69 (1,12 en
  4 bits), OPT-30B 7,32, contre 0,01 et 0,60 pour DeepSpeed [lit., tableau 2]. Le jeton/s
  sur OPT-175B s'obtient avec un lot effectif de 144 et 4 000 s de latence [lit.].
- **Ce qu'il gagne.** Les octets par jeton divisés par la taille du lot. **Ce qu'il coûte.**
  Une latence de plusieurs milliers de secondes : rien pour un usage interactif à lot 1.
- **Windows.** PyTorch CUDA. Dépôt `FMInference/FlexLLMGen`, Apache-2.0, dernier commit
  2024-10-27 : recherche, non maintenu.

### 2.4 llama.cpp : mmap, `-ngl`, et ce qui est arrivé en 2026

Lu dans le dépôt officiel au commit `843e7dc` (2026-10-15), licence MIT.
- **mmap** : le fichier GGUF est projeté en mémoire ; sous Windows, `PrefetchVirtualMemory`
  demande au système de précharger des plages (`src/llama-mmap.cpp`). Le système remplit et
  vide le cache de pages à sa guise : c'est le chargement à la demande le plus simple qui
  soit, et le plus mal granulé (§ 1.3, 148 Mo/s contre 1 496 Mo/s [lit.]).
- **`-ngl N`** : les N dernières couches vont en VRAM, le reste est calculé par le
  processeur depuis la RAM. Le temps par jeton est la somme des deux parties (pas de
  recouvrement entre couches) : `t = O_carte/B_vram + O_ram/B_ram` [calc.].
- **`-ot`, `-cmoe`, `-ncmoe N`, `-ncffn N`** : placer les experts (ou les FFN denses) de N
  couches en RAM, calculés par le processeur, l'attention restant sur la carte. C'est la
  stratégie « hybride » de KTransformers rendue ordinaire.
- **`--load-mode none|mmap|mlock|dio`** : `dio` = lecture directe sans cache système.
- **Lecture paresseuse** : les tenseurs de plus de 4 Gio (en mode auto) ne sont pas lus au
  chargement ; `llama_prefetch_rows` ne précharge que les lignes demandées (la table
  d'enchâssement, typiquement) (`src/llama-model-loader.cpp`, `src/llama-impl.cpp`).
- **`--moe-cache-mib N`** (EXPÉRIMENTAL dans `include/llama.h`) : un cache en VRAM des
  experts gardés en RAM. Un billet secondaire le date d'octobre 2026 (PR #29887, non vérifiée
  à la source) ; l'option est bien dans le code du jour.
- **Ce qui n'y est pas** : la lecture des experts sur le disque avec un cache explicite
  (PR #25294, ouverte, § 3.5), la prédiction d'experts, le report.
- **Windows.** Oui, binaires CUDA 12.4, Vulkan, CPU. Maturité : la plus haute de tout ce
  document.

### 2.5 « LLM in a flash » (Apple, ACL 2024)

- **Mécanisme.** (1) Prédicteur de rang faible des neurones actifs de la FFN (rang 128,
  1 024 pour les 4 dernières couches d'OPT-6.7B ; environ 5 % de faux négatifs) ; (2)
  **fenêtrage** : on garde en DRAM les neurones actifs des k derniers jetons et on ne lit que
  les nouveaux (Falcon 7B, fenêtre de 4 jetons : 33 % de la FFN en DRAM, 3,1 % des neurones
  lus par jeton) ; (3) **regroupement lignes-colonnes** : la colonne i de la projection
  montante et la ligne i de la descendante sont contiguës, une lecture de 2·d_model au lieu
  de deux (32 Kio pour OPT en 32 bits) ; (4) gestion mémoire préallouée, suppression en
  O(c·d_model) par écrasement [lit.].
- **Chiffres** (ms par jeton, I/O / mémoire / calcul / total, OPT-6.7B) : naïf processeur
  2 196 / 0 / 986 / 3 182 ; complet 105 / 58 / 506 / 669 ; sur RTX 4090, naïf 2 218, complet
  84, avec spéculation 60 [lit., tableau 3]. Débit de flash effectif : 1,25 Go/s en lectures
  éparses, 2,25 Go/s avec regroupement, 6,10 Go/s en dense [lit., tableau 2]. DRAM : environ
  la moitié du modèle (52,1 % pour OPT).
- **Ce qu'il gagne.** 20 à 25× sur la carte contre le chargement naïf. **Ce qu'il coûte.**
  Il exige la parcimonie d'activation des ReLU ; sur les SwiGLU modernes elle est faible
  (l'étude 05 la traite) ; il garde la moitié du modèle en DRAM.
- **Windows.** Pas de code publié par Apple. Maturité : article.

### 2.6 PowerInfer (SOSP 2024) et PowerInfer-2

- **Mécanisme.** Les neurones « chauds » (une petite part qui s'active pour presque toutes
  les entrées : 26 % des neurones MLP d'OPT-30B couvrent 80 % des activations) sont placés
  sur la carte, les « froids » sont **calculés par le processeur au lieu d'être transférés**,
  parce que sous un lot de 32 transférer coûte plus que calculer sur place ; prédicteurs par
  couche (6 à 9 % des paramètres, plus de 95 % de justesse) [lit.].
- **Chiffres.** RTX 4090, i9-13900K, 192 Go de RAM à 67,2 Go/s : moyenne 8,32 jetons/s en
  FP16, jusqu'à 11,69× llama.cpp ; OPT-30B 12,0 contre 1,1 jeton/s [lit.]. PowerInfer-2
  (OnePlus 12, 24 Go, UFS 4.0) : TurboSparse-Mixtral-47B de 2,13 jetons/s avec 7 Go à 11,68
  avec 19 Go ; cache de neurones en trois régions, 3,5 % de défauts en moyenne (18,9 % au
  99e centile) ; sur Bamboo-7B, 86,3 % du temps en calcul et 13,7 % en I/O, contre 23,3 / 76,7
  pour LLM in a flash [lit.].
- **Ce qu'il coûte.** Des modèles ReLU-isés (Bamboo, TurboSparse) : la technique dépend de la
  parcimonie, pas des poids. **Windows** : PowerInfer compile sous Windows (base llama.cpp,
  MIT, dernier commit 2026-05-11) ; PowerInfer-2 n'a pas de code public complet.

### 2.7 PIPO (2025)

Pipeline fin de déchargement sur un portable à RTX 3060 6 Go : occupation de la carte de
moins de 40 % à plus de 90 %, jusqu'à 3,1× de débit [lit., résumé seul]. Pas de chiffres
absolus ni de modèles nommés dans le résumé.

---

## 3. Modèles MoE : déchargement, prédiction et cache d'experts

### 3.1 Mixtral-offloading (Eliseev et Mazur, 2023-12-28)

- **Mécanisme.** Experts quantifiés (HQQ 2 ou 3 bits, attention 4 bits) en RAM épinglée ;
  cache LRU de k experts par couche en VRAM (k = 2 sur RTX 3060, 4 ailleurs) ; chargement
  spéculatif : on applique le routeur de la couche ℓ+1 à l'état caché de la couche ℓ (le
  résidu change peu) et on précharge 1 ou 2 experts (`src/expert_cache.py` :
  `OrderedDict` par groupe d'éviction, l'élément le plus ancien est évincé) [lit. + code lu].
- **Chiffres** (jetons/s, experts 2 bits) : A100 3,061 ; RTX 3080 Mobile 2,655 ; RTX 3060
  2,278 ; T4 2,092 ; sans cache ni préchargement 1,547 sur 3060 ; déchargement naïf 0,919
  [lit., tableau 2]. Gain du cache LRU et du préchargement : ×1,47 sur 3060.
- **Windows.** PyTorch + Triton (Triton sous Windows : non officiel). MIT. Dernier commit
  2024-01-05 : article figé.

### 3.2 MoE-Infinity (2024-2025)

- **Mécanisme.** Matrice d'activation des experts par requête (couches × experts), traces
  représentatives retenues, cache et préchargement guidés par la trace la plus proche.
- **Chiffres.** « Moins de 5 % des experts sont activés de façon répétée » par requête sur
  les modèles à une centaine d'experts, environ 25 % pour Mixtral ; DeepSeek-V2-Lite sur
  RTX A5000 : 155 ms par jeton contre 485 (vLLM), 1 250 (Mixtral-offloading), 2 590
  (Ollama) [lit.]. Le résumé dit 3,1 à 16,7×, la conclusion 2,7 à 13,7× : l'article se
  contredit.
- **Windows.** Extension C++/CUDA, Linux. Apache-2.0, actif (commit 2026-10-12).

### 3.3 Calculer l'expert là où il est : Fiddler, KTransformers, DALI

- **Fiddler** (ICLR 2025). Un expert absent de la carte est calculé par le processeur si
  c'est moins cher que de le transférer ; la règle du code est
  `coût_cpu = n_jetons × 7` contre `coût_carte = 70` (constantes codées en dur, « TODO »,
  `src/fiddler/mixtral.py`, lignes 38-39 et 567-568) : sur leur machine, transférer un
  expert de Mixtral coûte dix calculs d'un jeton sur le processeur [code lu]. Gain publié :
  1,26× à lot 1 [lit.]. Apache-2.0, figé en 2024.
- **KTransformers** (SOSP 2025). Experts en RAM calculés par des noyaux AMX/AVX-512,
  attention et experts partagés sur la carte, graphes CUDA (l'appel de la carte passe de
  plus de 20 % du temps à presque rien). **Report d'expert** : les experts au-delà des
  meilleurs (par exemple 2 immédiats + 6 reportés pour DeepSeek-V3 quantifié) voient leur
  sortie ajoutée à la couche ℓ+2 au lieu de ℓ+1, ce qui laisse le processeur calculer
  pendant l'attention suivante. Formellement O_k = I_k + S_k(I_k) + R_imm,k(I_k) et la part
  reportée R_def,k(I_k) entre dans I_{k+2}. Coût mesuré : au plus 2 points sur HumanEval,
  MBPP, GSM8K, StrategyQA ; gain jusqu'à 45 % de plus [lit.]. Machine : deux Xeon 8452Y,
  220 Go/s par socle, A100 40 Go ou RTX 4080 16 Go, PCIe 4.0 [lit.]. Apache-2.0, actif.
  Sous Windows : non (AMX, Linux).
- **DALI** (2026-02). Affectation dynamique des experts entre processeur et carte (0-1
  résolu gloutonnement), préchargement par le résidu, remplacement selon la charge ; RTX
  3090 + EPYC 7532 : 3,97× llama.cpp, 2,16× KTransformers, 1,48× MoE-Lightning, 1,32×
  HybriMoE au décodage [lit., chiffres absolus seulement dans les figures].
- **Ce que dit le juge sur la machine de Stone** [calc.] : calculer un expert de Qwen3-30B
  (2,86 Mo en Q4_K_M) sur le processeur coûte 82 µs à 35 Go/s ; le transférer coûte
  33 µs + 448 µs à 6,4 Go/s, soit **5,9× plus** ; mais le calculer sur la carte depuis la
  VRAM coûte 13 µs. Avec une RAM à un seul canal, la règle de Fiddler reste vraie (calculer
  sur place plutôt que transférer), mais l'écart avec la carte est grand : chaque expert
  qu'on peut garder en VRAM vaut six fois un expert gardé en RAM.

### 3.4 Prédire et précharger : Pre-gated, ProMoE, HOBBIT, AdapMoE, ExpertFlow et suivants

| Système | Prédiction | Justesse publiée | Gain publié | Machine |
|---|---|---|---|---|
| Mixtral-offloading | routeur ℓ+1 sur l'état ℓ | (figure seulement) | ×1,47 avec LRU | RTX 3060 |
| Pre-gated MoE (2023-24) | porte de ℓ+1 entraînée à la couche ℓ | – | (résumé sans chiffres) | 1 carte |
| ProMoE (2024-25) | prédicteur appris | 84,7 % (contre 66,9 % routeur décalé, 58,3 % par jeton) | décodage 2,07× (jusqu'à 5,02×) | RTX 4090, PCIe mesuré 23,9 Go/s |
| HOBBIT (2024) | routeur ℓ+1, ℓ+2, ℓ+3 | 96 % à ℓ+1, environ 90 % à ℓ+2/ℓ+3 (top-1) | jusqu'à 9,93× ; 3,21× Mixtral-offloading sur 4090 | RTX 4090 ; Jetson Orin |
| AdapMoE (2024) | + porte adaptative (−25 % d'experts) | – | 1,35× | bords |
| ExpertFlow (2024, DAC'26) | prédicteur transformeur de tout le chemin | – | jusqu'à 10× ; −93,72 % de mémoire carte | 1 carte |
| SP-MoE (2025) | brouillon de décodage spéculatif | – | 1,07 à 3,5× TPOT | – |
| CommitMoE (AAAI 2026) | s'engage sur la prédiction, sans retour | – | 1,3 à 9,4× | – |
| SeqMoE (2026-09) | séquence multi-pas, multi-couches ; Belady probabiliste | succès 96,97 % à 45 % de résidence | 80,22 % de la vitesse « tout en mémoire » | – |
| Edge0 (2026-09) | « prérouteur » entraîné, un jeton d'avance, **la prédiction est le routage** | – | +80 à +84 % au décodage | Mac mini M4 Pro 24 Go |
| moe-stream (2026) | routeur ℓ+1 sur l'état ℓ | top-8 exact 84 % (OLMoE) | – | Ryzen 5 7430U |

[toutes lit.] Deux enseignements pèsent pour la suite :
- **HOBBIT** remplace un expert absent par sa copie basse précision (FP16 → Int4 sur 4090,
  Int8 → Int2 sur Orin ; pour Mixtral 67 % haute précision, 30 % basse, 3 % sautés) pour au
  plus 1 point de perte ; il mesure aussi que le chargement des experts fait 85,5 % du temps
  sur 4090 et 94,5 % sur Orin [lit.].
- **Edge0** mesure que la prédiction **à la couche** (Pre-gated) coûte, dans son moteur, une
  synchronisation par couche de 30 à 100 ms par pas, plus que ce qu'elle cache, et que toutes
  ses variantes « même jeton » tombent sous un simple LRU ; seule une avance **d'un jeton
  entier** paie. Le temps bloqué sur les lectures tombe de 244,0 à 101,9 ms par pas à K = 4,
  à octets presque égaux : la prédiction ne supprime pas d'octets, elle retire la latence du
  chemin critique (« conservation, pas qualité de prédiction ») [lit.]. Edge0 obtient
  20,4 jetons/s en 2,9 Gio sur Qwen3.6-35B-A3B, mais **en réduisant le top-k à 4** et avec un
  adaptateur de récupération ; écart moyen 3,9 points sur cinq bancs [lit.].

### 3.5 Lire les experts sur le disque (2026)

- **PR llama.cpp #25294** (2026-07-04, ouverte). Cache d'emplacements en mémoire de la carte
  par couche, remappage des identifiants après le top-k, défauts lus par un pool de fils
  (`pread`, option O_DIRECT), éviction « chaleur décroissante + LRU », pré-remplissage par
  vagues. GB10 128 Go, GLM-5.2 Q2_K_XL (254 Go) : 90 emplacements (79 Go) donnent 79 % de
  succès et environ 2,20 jetons/s ; 64 emplacements, 73 % et 1,83 ; contre 0,87 jeton/s en
  mmap + `--cpu-moe` [lit.]. Pas de Windows (une PR séparée, #26542, ajoute les lectures
  positionnelles sans tampon sous Windows).
- **moe-stream** (2026, MIT). Cache explicite verrouillé, lectures directes sur un pool,
  disposition regroupée (un expert = une lecture), LFU à demi-vie de 8 jetons, prédiction par
  le routeur suivant. Processeur seul, 16 Go : Qwen3.6-35B-A3B avec 6 Go de budget,
  0,82 jeton/s en mmap contre 5,05 ; sans limite, 3,53 contre 6,79 [lit.]. Mesuré pour
  moitié sous Windows (`build.ps1`).
- **SSD-LLaMA** (2026-09-16). SSD, RAM et VRAM gérés comme une seule hiérarchie, lectures
  io_uring par lots bornés, une requête O_DIRECT alignée par expert (12,75 Mio pour
  DeepSeek-V4-Flash), LRU pondéré par la fréquence, **compression des experts** (trafic
  disque de 8,89 à 5,93 Go par jeton, −33,2 % ; décompression après transfert 0,54 s contre
  0,93 s de lecture). RTX 5090 32 Go, 16 ou 32 Go de RAM, SSD 9 Gio/s (77,7 % atteints contre
  43,2 % pour le meilleur concurrent), PCIe 5.0 ×16 : Kimi-K2.7-Code (1T, 543,6 Gio) à
  1,03 jeton/s ; DeepSeek-V4-Flash à environ 6,72 jetons/s avec 22 Gio de cache VRAM (80,1 %
  de succès) [lit.]. Linux.
- **Edge0** (2026-09-17) : § 3.4. macOS/MLX.
- **FlashMoE** (2026-01, révisé 2026-10-05). Remplacement appris combinant récence et
  fréquence : succès jusqu'à +51 % sur LRU/LFU, 2,6× [lit., résumé].
- **« Cacheable by design ? »** (2026-08-18, un seul auteur, résultat négatif pré-enregistré).
  Qwen3-235B Q4_K_M (134 Go) sur RTX 3070 8 Go + 32 Go DDR4 + SSD SN530 (2,4 Go/s à froid),
  llama.cpp `-ngl 99 -ncmoe 94` : 0,128 jeton/s à froid, 0,441 à chaud ; les lots s'effondrent
  à 32 (thrash du cache de pages). Entraîner le routeur pour la localité réduit les défauts
  jusqu'à 60 % mais rate toujours la porte de ≤ 1 % de perplexité [lit.]. L'article contient
  des incohérences internes (débit « retrouvé » de 2,4 Go/s contre 5,3 Go/s impliqués ; écarts
  « à 6 % » qui sont de 14 %) : à citer avec prudence.
- **SmallThinker** (2025-07). Le contre-pied : un modèle **conçu** pour le local, routeur
  placé avant l'attention pour que les experts se lisent pendant l'attention, équilibrage
  des charges relâché pour favoriser la spécialisation ; plus de 20 jetons/s sur processeur en
  Q4_0 avec 1 et 8 Go de mémoire [lit., résumé]. Il prouve qu'on peut acheter la localité à
  l'entraînement ; il ne s'applique pas à un modèle existant.

### 3.6 Les caches d'experts : LRU, LFU, appris

| Politique | Résultat publié | Source |
|---|---|---|
| LRU | 65,9 % à 13,4 % du budget (Qwen3-30B, couche 24, code) | Cacheable by design [lit.] |
| LFU | 60,1 % (même point) ; LFU 84,6 % plus rapide que LRU sur A6000 (Mixtral, cache 4) | idem ; Lin et al. 2025 [lit.] |
| Épinglage statique | 59,2 % (même point) | idem [lit.] |
| Belady (optimum hors ligne) | 79,1 % (même point) | idem [lit.] |
| SLRU + filtre d'admission | +8 à 15 points sur LRU (GPT-OSS-120B) | llama.cpp #20757 [lit., communautaire] |
| LFU cumulatif, 88/128 experts par couche | 98,84 % (Qwen3-30B-A3B Q4_K_M, simulation) | llama.cpp #20757 [lit., communautaire] |
| « Least-Stale » | 88-92 % de succès à 1 % de capacité ; défauts de collision ÷ 85 contre LRU | SpecMD (Apple, 2026-02) [lit.] |
| Appris (récence + fréquence) | +51 % de succès sur LRU/LFU | FlashMoE [lit.] |
| Routage conscient du cache (sans entraînement) | défauts DeepSeek-V2 28 % → 7 %, Qwen1.5-MoE 35 % → 16 %, Mixtral 40 % → 21 % ; perplexité +0,1 à 3 % | Skliar et al., TMLR 2025 [lit.] |

SpecMD soutient que l'accès aux experts « n'est pas récent mais séquentiel par couche » et
que LRU/LFU s'y trompent ; d'autres (fMoE, « Adaptive Expert Split ») soutiennent le
contraire. Les deux constats tiennent ensemble : la localité temporelle existe (§ 4) mais
elle est faible, et l'ordre déterministe des couches est une information que LRU ignore.

---

## 4. La localité des experts d'un jeton au suivant

### 4.1 Ce qui est mesuré

| Modèle (E, k) | Réutilisation adjacente | « Au hasard » | Source |
|---|---|---|---|
| Mixtral-8x7B (8, 2) | premier choix répété 13,6-14,9 % (couche 0), 24,6-28,4 % (couche 15), 19,7-26,3 % (couche 31) | 12,5 % | Mixtral, tableau 5 [lit.] |
| Mixtral-8x7B | premier ou second choix 44,5-67,0 % | environ 46 % | idem [lit.] |
| Qwen3-30B-A3B (128, 8) | 0,444 | 0,223 (définition non donnée) | Cacheable by design [lit.] |
| Qwen3.6-35B-A3B (256, 8) | « environ un quart » de l'ensemble d'une couche | 8/256 = 3,1 % [calc.] | Edge0 [lit.] |
| Qwen1.5-MoE, DeepSeek-V2, Phi-3.5, Mixtral | résidence moyenne en cache 26, 19, 22, 5 jetons | – | Skliar et al. [lit.] |
| ~100 experts (DeepSeek, Qwen-MoE…) | < 5 % des experts réactivés de façon répétée par requête | – | MoE-Infinity [lit.] |
| OLMoE-1B-7B (64, 8) | 38 experts sur 64 couvrent 80 % des choix | – | moe-stream [lit.] |
| Qwen3.5-122B | 10 % des experts prennent environ 80 % des succès ; 99 % simulés à 69 % de budget | – | llama.cpp #24528 [lit., communautaire] |
| Qwen3-30B (4 domaines) | 52,5 % des experts portent 95 % du trafic ; recouvrement code/autres 0,11-0,16 | – | Cacheable by design [lit.] |

Le « hasard » de 0,223 publié pour Qwen3-30B ne peut pas être k/E = 0,0625 ; c'est
vraisemblablement le recouvrement attendu à popularité réelle, que mon outil calcule comme
Σ π_e² / k (π_e : fréquence d'inclusion de l'expert e). Je ne peux pas le vérifier sans
trace.

### 4.2 Ce qu'il faut en retenir

- **La localité existe et elle est faible.** Pour les MoE fins de 2025-2026, un jeton reprend
  environ un quart à 44 % des experts du jeton précédent, deux à huit fois le hasard. Elle
  est plus forte au milieu du réseau qu'aux extrémités (Mixtral : 28 % à la couche 15 contre
  14 % à la couche 0).
- **Les MoE fins sont plus « cachables » que les gros grains** : résidence 19-26 jetons
  contre 5 pour Mixtral [lit.].
- **La popularité compte autant que la récence** : 52,5 % des experts font 95 % du trafic ;
  10 % font 80 % des succès sur Qwen3.5-122B. D'où la force d'un épinglage statique pour la
  part chaude, et d'un LRU/LFU pour la part tiède.
- **Le domaine change l'ensemble chaud** (code contre prose : recouvrement 0,11-0,16) : un
  épinglage calibré sur un domaine se trompe sur un autre.

### 4.3 La localité lue dans les mesures publiées (juge, h minimal impliqué) [calc.]

| Mesure publiée | Part du modèle en mémoire rapide | Succès impliqué au moins |
|---|---|---|
| Qwen3-235B à chaud, 0,441 jeton/s, SSD 2,4 Go/s | environ 25-30 % | 33 % |
| GLM-5.2, 2,20 jetons/s, SSD ≤ 7,877 Go/s | 79 Go sur 254 (31 %) | 53 % (publié : 79 %) |
| moe-stream Qwen3.6-35B-A3B, 5,05 jetons/s, 6 Go de budget | 6 sur 19,5 Go d'experts (31 %) | 53 % |

Le témoin GLM est cohérent (53 % ≤ 79 % publiés). Le cas moe-stream montre, sans trace,
qu'un cache tenant 31 % des experts sert au moins 53 % des octets : **la localité vaut au
moins un facteur 1,7 sur la capacité** pour ce modèle.

### 4.4 L'instrument est prêt, la trace manque

`outils/chargement_localite.py` mesure, sur une trace de routage réelle, la réutilisation
adjacente, ses deux références de hasard, les distances de réutilisation, et les succès de
LRU, LFU (demi-vie), épinglage calibré et oracle, Belady, pour chaque budget. Ses témoins
synthétiques (`localite-temoins.json`) : routage uniforme (réutilisation 0,0613 pour 0,0625
attendu, tolérance 4σ = 0,0027 ; LRU = C/E à chaque budget), routage figé (réutilisation 1 ;
succès 0,9998), routage collant ρ = 0,6 (0,604 mesuré), Belady jamais dépassé. Avec
`--casser` (ordre des jetons mélangé), la réutilisation du routage collant tombe à 0,0635 et
le témoin échoue : l'instrument voit l'ordre (`localite-temoins-casse.json`). Deux erreurs
de ma première passe sont corrigées et dites dans le code : l'attendu du témoin collant
(j'avais écrit ρ + (1 − ρ)k/E, faux puisque les tirages évitent l'ensemble courant) et
l'inclusion de l'épinglage statique dans l'invariant de Belady (il dispose de C + k places
et ne paie pas de défaut de démarrage).

Sur le routage collant (ρ = 0,6, E = 128, k = 8), l'instrument montre déjà la forme du
problème : LRU 0,630 / Belady 0,720 à C = 16 ; 0,789 / 0,908 à C = 64 [calc., synthétique].
L'écart LRU–Belady est de 9 à 13 points : c'est la marge qu'une prédiction parfaite
pourrait reprendre.

---

## 5. Les pipelines disque → RAM → carte avec double tampon

### 5.1 La règle du double tampon

Avec deux tampons, la lecture du morceau i+1 se fait pendant le calcul du morceau i ; le
temps par morceau devient max(L_i, C_i) au lieu de L_i + C_i, plus un remplissage initial.
La profondeur d de préchargement nécessaire pour masquer une latence λ est
d ≥ ⌈λ / C_couche⌉ couches. Pour Qwen3-235B à 1 jeton/s sur la machine de Stone, une couche
dure 10,6 ms et la lecture d'un expert (10,76 Mo) 1,6 ms à 6,7 Go/s [calc.] : une couche
d'avance suffit à masquer la latence d'un défaut, mais pas le débit si huit experts manquent
(12,9 ms > 10,6 ms). Le double tampon cache la latence, jamais le volume.

Chiffres publiés du double tampon : AirLLM « 10 % » ; llama.cpp #27149 : 2,97 Go/s en
lecture séquentielle de couches de 286 Mo, 6,06 Go/s en double tampon (×2,09) ; PowerInfer-2,
×1,29 sur Bamboo-7B ; Edge0, temps bloqué divisé par 2,4 à 3,3 [lit.].

### 5.2 Ce que la machine de Stone donne au pipeline [mes.]

- Une copie H2D se recouvre presque parfaitement avec un trafic VRAM sur un autre flux : part
  cachée 0,98 à 1,01, VRAM ralentie de 5,6 % (pcie-1). Les moteurs de copie sont donc libres
  pendant que la carte travaille.
- La mémoire épinglée vaut 21 % de débit de plus que la paginable.
- Le lien n'atteint sa génération 4 que si la carte est en état de performance haut (§ 1.4).

### 5.3 Les chemins de Windows

- **Lectures sans tampon** (`FILE_FLAG_NO_BUFFERING`) par IOCP ou **IoRing** (Windows 11) :
  l'étude 01 les mesure (banc `outils/banc`, `disque.rs`). C'est l'équivalent d'io_uring +
  O_DIRECT de SSD-LLaMA et de la PR #25294.
- **DirectStorage** : lecture du NVMe vers une ressource D3D12 avec décompression sur la
  carte. GDeflate sur la carte depuis la version 1.1 ; 1.3 (2025-07-01) ajoute
  `EnqueueRequests` et une destination « plage de sous-ressources » ; **1.4 (2026-03-11,
  préversion ; 1.4.0-preview2 du 2026-06-16 sur NuGet)** ajoute **Zstandard décompressé sur
  la carte**, avec un nuanceur de calcul publié comme base (`microsoft/DirectStorage`,
  branche `development/zstd`), « optimisé pour des morceaux de 256 Ko ou moins » [lit.]. Le
  billet ne donne ni débit de décompression ni chemin exact des données (il passe, à ma
  connaissance, par une mémoire de transit côté hôte : à vérifier par la mesure). C'est le
  seul chemin disque → VRAM avec décompression sur la carte qui existe sous Windows sans
  CUDA. Aucun moteur d'inférence lu ne s'en sert.
- **CUDA** : depuis ce matin, CUDA 13.1.2 est dépaqueté sur la machine (SOCLE corrigé) ; les
  copies asynchrones par flux, la mémoire épinglée et les graphes CUDA sont disponibles sans
  installation.

---

## 6. Le juge appliqué à la machine de Stone

`outils/chargement_juge.py --machine stone` (journal `juge-stone.txt`). Débits : VRAM
220 Go/s [mes., arrondi] ; PCIe 6,4 Go/s [mes.] ; **RAM 35 Go/s et disque 6,7 Go/s =
85 % des plafonds calculés, hypothèses** à remplacer par les mesures de l'étude 01
(réponse par délégation du 2026-10-15, réversible : on avance avec 85 % des plafonds parce
que c'est l'ordre de ce que les bancs publiés atteignent, et chaque chiffre sera barré et
corrigé quand la mesure arrivera). Capacités utiles aux poids : VRAM 6,5 Go, RAM 10 Go
(hypothèses dites dans l'outil).

| Modèle (bpp) | Total Go | A Go | R Go | Expert Mo | Part qui tient | Borne sans localité (j/s) | Succès pour 5 j/s | pour 10 j/s | Plafond, tous les experts en RAM, calcul processeur | Plafond, tous en VRAM, calcul carte |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-30B-A3B (4,85) | 18,3 | 0,75 | 1,10 | 2,86 | 0,90 | 47 (processeur) | 0 | 0,39 | 31,9 | 119 |
| Qwen3.6-35B-A3B (4,85) | 20,7 | 1,18 | 0,61 | 1,91 | 0,78 | 51 | 0 | 0 | 57 | 123 |
| gpt-oss-120b (4,25) | 61,8 | 0,82 | 1,90 | 13,2 | 0,26 | 4,7 | 0,30 | 0,65 | 18 | 81 |
| GLM-4.5-Air (4,85) | 64,4 | 3,99 | 3,78 | 10,5 | 0,21 | 2,2 | 0,65 | 0,82 | 9,3 | 28 |
| Qwen3-Next-80B-A3B (4,85) | 48,1 | 1,25 | 0,92 | 1,91 | 0,33 | 10,9 | 0 | 0,27 | 38 | 102 |
| Qwen3.5-122B-A10B (4,85) | 73,6 | 3,26 | 2,20 | 5,72 | 0,19 | 3,8 | 0,39 | 0,70 | 16 | 40 |
| Qwen3.8-Flash-Next (4,85) | 75,8 | 2,61 | 1,43 | 2,98 | 0,19 | 5,8 | 0,06 | 0,53 | 25 | 54 |
| DeepSeek-V4-Flash (4,5) | 82,0 | 4,11 | 1,83 | 7,08 | 0,16 | 4,4 | 0,27 | 0,63 | 19 | 37 |
| Qwen3-235B-A22B (4,56) | 133,6 | 4,20 | 8,09 | 10,8 | 0,09 | 0,9 | 0,83 | 0,92 | 4,3 | 18 |
| Qwen3.5-397B-A17B (4,85) | 239,7 | 5,32 | 4,58 | 7,63 | 0,05 | 1,5 | 0,71 | 0,85 | 7,6 | 22 |
| Qwen3-235B-A22B (2,7) | 79,1 | 2,49 | 4,79 | 6,37 | 0,18 | 1,7 | 0,72 | 0,86 | 7,3 | 30 |
| GLM-5.1 (2,7) | 250,7 | 6,14 | 7,64 | 12,7 | 0,04 | 0,9 | 0,82 | 0,91 | 4,6 | 16 |

**Le même tableau avec le disque à 2,4 Go/s** (première lecture provisoire de l'étude 01,
`juge-stone-disque-2.4.txt`) ; les colonnes qui ne dépendent pas du disque ne changent pas :

| Modèle (bpp) | Borne sans localité (j/s) | Succès pour 5 j/s | pour 10 j/s |
|---|---|---|---|
| Qwen3-30B-A3B (4,85) | 21 | 0,56 | 0,78 |
| Qwen3.6-35B-A3B (4,85) | 18 | 0,21 | 0,61 |
| gpt-oss-120b (4,25) | 1,7 | 0,75 | 0,87 |
| GLM-4.5-Air (4,85) | 0,8 | 0,87 | 0,94 |
| Qwen3-Next-80B-A3B (4,85) | 3,9 | 0,48 | 0,74 |
| Qwen3.5-122B-A10B (4,85) | 1,4 | 0,78 | 0,89 |
| Qwen3.8-Flash-Next (4,85) | 2,1 | 0,66 | 0,83 |
| DeepSeek-V4-Flash (4,5) | 1,6 | 0,74 | 0,87 |
| Qwen3-235B-A22B (4,56) | 0,33 | 0,94 | 0,97 |
| Qwen3.5-397B-A17B (4,85) | 0,55 | 0,90 | 0,95 |
| Qwen3-235B-A22B (2,7) | 0,61 | 0,90 | 0,95 |
| GLM-5.1 (2,7) | 0,33 | 0,94 | 0,97 |

[calc.] « Borne sans localité » : le cache sert exactement la part du modèle qui tient
(aucune localité) ; le recouvrement est supposé parfait. Lectures :

1. ~~**Les MoE à experts fins et à peu d'octets routés (R ≤ 1,5 Go) sont déjà jouables sans
   localité** : Qwen3-Next-80B (11 j/s), Qwen3.8-Flash-Next (5,8 j/s).~~ Barré : vrai à
   6,7 Go/s de disque, faux à 2,4 Go/s (3,9 et 2,1 j/s). Ce qui reste vrai : ce sont les
   modèles à faible R (≤ 1,5 Go routés par jeton), 3 à 5 fois plus gros que la mémoire de la
   machine, qui sont à portée ; ils demandent 50 à 75 % de succès pour 5 à 10 j/s.
2. **Les gros MoE à experts épais (R ≥ 4,5 Go) exigent un succès de 70 à 85 % pour 5 j/s**,
   avec 4 à 9 % du modèle en mémoire rapide. Le seul point publié comparable (Qwen3-30B,
   LRU 65,9 %, Belady 79,1 % à 13,4 %) dit que les politiques de cache seules n'y arrivent
   pas : il faut réduire R (quantification, étude 02 ; codage, étude 03), ou changer le
   routage (cache-conscient, report, substitution).
3. **Avec un seul canal de RAM, la carte vaut 5 à 6 fois le processeur** pour un expert
   présent (colonnes « tout en RAM » contre « tout en VRAM ») : à l'inverse de KTransformers
   (440 Go/s de RAM sur deux Xeon), la VRAM est le cache qui compte ; la RAM sert de tampon
   de lecture et de cache tiède.
4. ~~**Disque (6,7 Go/s) et PCIe (6,4 Go/s) ont le même débit** : faire passer un défaut disque
   par la RAM puis par le PCIe double le coût d'un octet manqué.~~ Barré : avec le disque
   provisoirement mesuré à 2,4 Go/s, le saut PCIe ajoute 2,4 / 6,4 = 37 % au coût d'un octet
   manqué s'il se fait en série, et rien s'il se recouvre. Un défaut disque doit être soit
   calculé par le processeur depuis son tampon de lecture, soit lu directement vers la VRAM
   (DirectStorage), et la copie, si elle a lieu, recouverte.

---

## 7. Ce que je crois manquer dans le monde

Chaque trou est chiffré sur la machine de Stone par le juge [calc.] ou par une mesure.

1. **Aucun moteur publié ne lit les experts sur le disque sous Windows jusqu'à la VRAM.**
   SSD-LLaMA (io_uring), la PR #25294 (pread/O_DIRECT, Windows « non revendiqué »), Edge0
   (MLX) et KTransformers (Linux) n'y sont pas ; moe-stream tourne sous Windows mais sur le
   processeur seul. Windows a pourtant IoRing et DirectStorage 1.4 (Zstd et GDeflate
   décompressés sur la carte). ~~Coût de l'ignorer : sur cette machine, le PCIe n'a pas plus de
   débit que le disque ; un défaut copié deux fois (disque → RAM, RAM → carte) coûte
   2 × e / 6,5 Go/s au lieu de e / 6,5 Go/s, soit **la moitié du débit des défauts perdue**.~~
   Barré (disque provisoirement à 2,4 Go/s, pas 6,7) : une double copie non recouverte coûte
   +37 % par octet manqué. Le coût dominant de l'ignorer est ailleurs : les moteurs existants
   lisent par le cache de pages ou en petits morceaux, et ce disque donne 0,22 Go/s à 4 Kio
   contre 2,4 à 3,0 Go/s à 1-4 Mio (×11 à ×14) [mes. par l'étude 01, provisoire] ; sans
   lecture explicite, regroupée, à la taille d'un expert, on perd un ordre de grandeur.
2. **L'état du lien PCIe d'un portable n'est dans aucune publication.** Mesuré ici : 6,4 Go/s
   en Gen3 pendant des copies seules, contre 15,75 Go/s de plafond Gen4 ; l'horloge VRAM
   descend avec (169 contre 227 Go/s). Une stratégie « carte » limitée par le PCIe gagne
   **jusqu'à ×2** si l'on garde la carte en état haut pendant les copies (à confirmer par une
   passe propre, la passe sous charge n'a donné que 7,6 Go/s, carte partagée).
3. **Pas de courbe « succès selon le budget » pour les MoE de 2026 aux budgets d'un
   portable.** Publié : un seul point exact (LRU 65,9 % à 13,4 %, une couche, un domaine,
   Qwen3-30B), des résidences pour des modèles de 2024, « environ un quart » pour Qwen3.6.
   Il faut 5 à 20 % de budget pour la machine de Stone, et la différence entre 66 % et 85 %
   de succès vaut **×2,3 de débit** sur Qwen3-235B (0,34 contre 0,15 · R lu sur le disque).
   L'instrument (`chargement_localite.py`) est prêt ; il manque la trace.
4. **Le report d'expert n'a jamais servi à absorber un défaut de lecture.** KTransformers
   reporte des experts présents pour occuper le processeur (≤ 2 points de perte pour 6
   experts sur 8 reportés d'une couche) ; Edge0 montre que dans un moteur réel le temps
   bloqué sur les lectures (101,9 à 575,0 ms par pas) dépasse de loin le temps où le disque
   travaille (au plus 12 % du pas) : **la latence domine, pas le volume**. Reporter d'une
   couche l'expert qui manque, au lieu d'attendre, retire cette latence du chemin critique
   sans prédiction et sans changer les octets. Gain borné par le juge : de la borne en série à
   la borne de recouvrement, soit par exemple ~~0,75 → 0,92 j/s (+23 %)~~ 0,30 → 0,33 j/s
   (+9 %) pour Qwen3-235B sans localité (barré : le premier chiffre supposait 6,7 Go/s de
   disque ; à 2,4 Go/s le disque écrase les autres étages et le recouvrement entre étages
   rapporte moins). Le gain du report n'est pas là : il est dans la latence de chaque lecture,
   que le juge par débits ne voit pas, et qui fait chez Edge0 un écart de +80 % entre lecture
   à la demande et lecture avancée.
5. **Personne n'a réuni les quatre réponses à un défaut sous un budget de qualité mesuré** :
   attendre (tous), reporter (KTransformers, pour une autre raison), substituer une copie
   basse précision (HOBBIT, ≤ 1 point), re-router vers un expert présent (Skliar et al.,
   défauts ÷ 2 à ÷ 4 pour +0,1 à 3 % de perplexité). MoE-PolicyLang choisit entre « attendre »
   et « calculer sur le processeur » ; CommitMoE s'engage sur la prédiction. Le choix, défaut
   par défaut, selon le score de routage de l'expert manquant (HOBBIT : 3 % des experts de
   Mixtral ont un score assez bas pour être sautés) est le terme qui manque.
6. **La compression dans la boucle de lecture n'est publiée que sur une machine à PCIe 5.0
   ×16 et RTX 5090** (SSD-LLaMA, −33 % de trafic disque). Sur la machine de Stone, où le
   disque est l'étage limitant, chaque point de compression sans perte des experts est un
   point de débit si la décompression tient dans le temps du calcul ; l'étude 03 donne
   l'entropie réelle des champs Q4_K, cette étude donne le prix : décompresser R · h_s
   octets par jeton, par exemple 2,7 Go/jeton pour Qwen3-235B à 66 % de succès.

---

## 8. Proposition d'assemblage (pour l'arbitre, à ne pas confondre avec une décision)

Ce que la lecture de l'état de l'art et le juge suggèrent pour la machine de Stone, sous la
forme d'hypothèses testables, chacune avec son témoin :
- **Placement** : attention, experts partagés, routeurs et un cache d'experts chauds en VRAM
  (calcul sur la carte) ; RAM = tampons de lecture épinglés + cache tiède ; disque = tous les
  experts, réécrits un expert par bloc contigu aligné sur 4 Kio (un défaut = une lecture),
  éventuellement codés sans perte (étude 03).
- **Lecture** : IoRing sans tampon à profondeur de file ≥ 16 vers la mémoire épinglée, ou
  DirectStorage vers la VRAM avec décompression sur la carte ; choix par la mesure.
- **Prédiction** : une avance d'un jeton (le routage du jeton t aux couches ℓ+1…ℓ+d, plus le
  routeur de ℓ+1 appliqué au résidu de ℓ), sans entraîner de tête d'abord.
- **Politique de défaut** : attendre / calculer sur le processeur depuis le tampon / reporter
  d'une couche / substituer une copie 2 bits gardée en RAM / re-router, choisi par le score
  de routage et un budget de perplexité déclaré avant la mesure.
- **Tenir le lien en Gen4** : lancer les copies pendant que la carte calcule.
- **Mesure** : jetons/s, perplexité (et une tâche), mémoire de pointe, contre llama.cpp
  `-ncmoe` + `--moe-cache-mib` sur la même machine, séries ABBA.

---

## 9. Ce qui pourrait être faux

1. **Les débits RAM et disque du juge sont des hypothèses** (85 % des plafonds). ~~Si la RAM
   ne donne que 25 Go/s et le disque 5 Go/s, toutes les bornes du § 6 baissent de 25 à 30 %.~~
   La première lecture du disque par l'étude 01 (2,4 Go/s à 1 Mio, provisoire) est 2,8 fois
   sous l'hypothèse : les bornes limitées par le disque baissent d'autant (second tableau du
   § 6). Cette lecture peut elle-même être basse (autres agents sur le disque) : le disque
   (Samsung MZVMA1T0HCLD) est à confirmer au repos, et la RAM reste à mesurer.
2. **Le juge suppose un recouvrement parfait** pour sa borne haute et ignore le cache KV, les
   activations, le préremplissage, la latence par requête et le coût de remappage des
   identifiants. Il borne, il ne prédit pas. Les mesures publiées tombent à 31 % (Qwen3-235B à
   froid), 45 % (GLM-5.2), 18 % (moe-stream, borne « tout en RAM ») et 23 % (Mixtral-offloading)
   de leur borne.
3. **La forme de GLM-5.1 a servi pour GLM-5.2** (absent de l'inventaire), et les bpp moyens
   (4,85 pour Q4_K_M, 2,7 pour Q2_K_XL) appliquent la même précision aux experts et au reste,
   ce qui est faux en détail (Q6_K sur certaines matrices).
4. **Les mesures de PCIe sont partielles** : la passe propre (pcie-1) a tourné avec le lien en
   Gen3 ; la passe en Gen4 (pcie-2) a tourné pendant qu'un autre programme calculait sur la
   carte. Le débit H2D réel en Gen4 sur cette carte est inconnu entre 7,6 et 15,75 Go/s. Les
   latences de petits transferts incluent l'appel Python par ctypes.
5. **Plusieurs chiffres de la littérature viennent de dépôts et de discussions
   communautaires** (llama.cpp #20757, #24528, #27149, moe-stream), non relus par des pairs ;
   deux articles se contredisent eux-mêmes (MoE-Infinity, Cacheable by design). Je les ai
   étiquetés, pas écartés.
6. **La réutilisation « 0,444 contre 0,223 » de Qwen3-30B** dépend d'une définition du hasard
   que l'article ne donne pas ; « environ un quart » pour Qwen3.6 n'est pas un chiffre exact.
7. **Le trou n° 4 (report pour absorber un défaut)** n'a pas été mesuré : son effet sur la
   qualité quand l'expert reporté est un des deux meilleurs est inconnu (KTransformers garde
   toujours au moins deux experts immédiats). Il se peut que quelqu'un l'ait fait sous un autre
   nom ; ma recherche (2026-10-15) ne l'a pas trouvé.
8. **`--moe-cache-mib` de llama.cpp** est dans le code du jour, mais sa date et son numéro de
   PR ne viennent que d'un billet secondaire ; je n'ai pas lu son implémentation.
9. **L'effet de l'état de performance sur le lien** est mesuré sur cette carte et ce pilote
   (591.91) ; un autre pilote ou un réglage d'alimentation peut le changer.

---

## 10. Sources (consultées le 2026-10-15)

| Source | Adresse | Publication |
|---|---|---|
| FlexGen, Sheng et al., ICML 2023 | https://arxiv.org/abs/2303.06865 | v1 2023-03-13, v2 2023-06-12 |
| LLM in a flash, Alizadeh et al., ACL 2024 | https://arxiv.org/abs/2312.11514 | v1 2023-12-12, v3 2024-07-30 |
| PowerInfer, Song et al., SOSP 2024 | https://arxiv.org/abs/2312.12456 | v1 2023-12-16, v2 2024-12-12 |
| PowerInfer-2, Xue et al. | https://arxiv.org/abs/2406.06282 | v1 2024-06-10, v3 2024-12-12 |
| Mixtral-offloading, Eliseev et Mazur | https://arxiv.org/abs/2312.17238 | 2023-12-28 |
| Mixtral of Experts (tableau 5) | https://arxiv.org/abs/2401.04088 | 2024-01-08 |
| MoE-Infinity, Xue et al. | https://arxiv.org/abs/2401.14361 | v1 2024-01-25, v3 2025-03-12 |
| Fiddler, Kamahori et al., ICLR 2025 | https://arxiv.org/abs/2402.07033 | v1 2024-02-10, v3 2025-05-01 |
| ProMoE, Song et al. | https://arxiv.org/abs/2410.22134 | v1 2024-10-29, v3 2025-09-01 |
| HOBBIT, Tang et al. | https://arxiv.org/abs/2411.01433 | v1 2024-11-03, v2 2024-11-06 |
| AdapMoE, Zhong et al. | https://arxiv.org/abs/2408.10284 | 2024-08-19 |
| ExpertFlow, He et al., DAC'26 | https://arxiv.org/abs/2410.17954 | v1 2024-10-23, v2 2026-04-02 |
| Pre-gated MoE, Hwang et al. | https://arxiv.org/abs/2308.12066 | v1 2023-08-23, v3 2024-04-27 |
| MoE-Lightning, Cao et al. | https://arxiv.org/abs/2411.11217 | 2024-11-18 |
| PIPO, Liu et al. | https://arxiv.org/abs/2504.03664 | v1 2025-03-15, v2 2025-06-13 |
| MoBiLE, Zhao et al., ASP-DAC 2026 | https://arxiv.org/abs/2510.12357 | 2025-10-14 |
| SP-MoE, Chen et al. | https://arxiv.org/abs/2510.10302 | v1 2025-10-11, v2 2025-11-06 |
| KTransformers, Chen et al., SOSP 2025 | https://madsys.cs.tsinghua.edu.cn/publication/ktransformers-unleashing-the-full-potential-of-cpu/gpu-hybrid-inference-for-moe-models/SOSP25-chen.pdf (DOI 10.1145/3731569.3764843) | 2025-10 |
| DALI, Zhu et al. | https://arxiv.org/abs/2602.03495 | 2026-02-03 |
| SeqMoE, Wang et al. | https://arxiv.org/abs/2609.12978 | 2026-09-11 |
| SpecMD, Hoang et al. (Apple) | https://arxiv.org/abs/2602.03921 | 2026-02-03 |
| Mixture of Cache-Conditional Experts, Skliar et al., TMLR | https://arxiv.org/abs/2412.00099 | v1 2024-11-27, v2 2025-06-24 |
| In-depth analysis on caching and pre-fetching, Lin et al. | https://arxiv.org/abs/2511.05814 | 2025-11-08 |
| Cacheable by Design?, Suram | https://arxiv.org/abs/2608.18261 | 2026-08-18 |
| SSD-LLaMA, Liang et al. | https://arxiv.org/abs/2609.18110 | 2026-09-16 |
| The Other Half of the Memory Wall (Edge0), Lin et al. | https://arxiv.org/abs/2609.18063 | v2 2026-09-17 |
| FlashMoE, Kim et al. | https://arxiv.org/abs/2601.17063 | v1 2026-01-22, v2 2026-10-05 |
| SmallThinker | https://arxiv.org/abs/2507.20984 | 2025-07 |
| CommitMoE, Li et al., AAAI 2026 | https://ojs.aaai.org/index.php/AAAI/article/view/39454 | 2026-03-14 |
| ZeRO-Inference (blogs DeepSpeed) | https://www.deepspeed.ai/2022/09/09/zero-inference.html ; https://www.deepspeed.ai/2023/09/12/ZeRO-Inference.html | 2022-09-09 ; 2023-09-12 |
| DirectStorage 1.4 (Zstd) | https://devblogs.microsoft.com/directx/directstorage-1-4-release-adds-support-for-zstandard/ | 2026-03-11 |
| DirectStorage 1.3 | https://devblogs.microsoft.com/directx/directstorage-1-3-is-now-available | 2025-07-01 |
| llama.cpp PR #25294 (experts lus sur le disque) | https://github.com/ggml-org/llama.cpp/pull/25294 | 2026-07-04, ouverte |
| llama.cpp #20757 (cache à deux étages) | https://github.com/ggml-org/llama.cpp/issues/20757 | 2026-03-19 |
| llama.cpp #24528 (cache VRAM d'experts chauds) | https://github.com/ggml-org/llama.cpp/discussions/24528 | 2026-06-12 |
| llama.cpp #27149 (lecture des experts actifs) | https://github.com/ggml-org/llama.cpp/discussions/27149 | 2026-08-15 |
| moe-stream | https://github.com/Wok3b/moe-stream | 2026 (date du dernier commit non affichée) |

Dépôts lus (clones sous `~/dev/lectures/troncons/chargement/`), licences
vérifiées dans leur fichier LICENSE : FlexLLMGen (Apache-2.0, `004ffef`, 2024-10-27),
MoE-Infinity (Apache-2.0, `96a9552`, 2026-10-12), PowerInfer (MIT, `8bd56d6`, 2026-05-11),
airllm (Apache-2.0, `0f679cc`, 2026-10-14), fiddler (Apache-2.0, `227715b`, 2024-04-28),
ktransformers (Apache-2.0, `a02efe3`, 2026-10-12), llama.cpp (MIT, `843e7dc`, 2026-10-15),
mixtral-offloading (MIT, `ce54518`, 2024-01-05). moe-stream : MIT d'après sa page (non cloné).
Rien n'en a été copié.

---

## 11. Recettes (techniques essayées dans cette étude)

- **Appeler le runtime CUDA livré avec llama.cpp par ctypes** (cudart64_12.dll) : mesure des
  copies sans compiler. Marche. Raison : aucune boîte à outils n'était là au départ.
- **Lire l'état du lien par NVML** (`nvml.dll` du pilote) avant et après chaque mesure. Marche,
  et a révélé la descente en Gen3. Raison : un débit sans l'état du lien ne s'interprète pas.
- **Lire L2 par `cudaDeviceGetAttribute`** : l'attribut est 38, pas 89 (erreur de la passe 2,
  L2 lu 0). Raison de la recette : vérifier un identifiant d'attribut contre une valeur connue.
- **Séparer le régime L2 du régime VRAM** (n ≥ 2 × L2) : sinon le témoin VRAM tombe à tort
  (719 Go/s à 16 Mio).
- **Ne pas tuer nvidia-smi par son nom** : j'ai lancé `nvidia-smi -lms` en fond et l'ai arrêté
  par `taskkill /IM`, ce qui aurait pu arrêter une instance d'un autre agent. Échec de méthode :
  borner la durée (`-c`/compte) ou relever par NVML dans le processus.
- **Clone `--filter=blob:none` + `git grep HEAD`** : chaque blob se télécharge à la demande et
  `git gc` se déclenche ; une recherche sur tout le dépôt prend plusieurs minutes. Mieux :
  `git -c gc.auto=0`, et chemins ciblés.
- **Extraire le texte des PDF avec pypdf** quand l'outil web ne lit pas le PDF : marche
  (FlexGen, KTransformers, Edge0).
- **Témoins synthétiques pour un instrument de cache** : routage uniforme (succès = C/E),
  figé (succès → 1), collant (réutilisation = ρ), et mélange de l'ordre comme cassure. Marche ;
  deux attendus faux de ma première passe trouvés par eux.
- **Juge validé sur des mesures publiées** (bornes ≥ mesures ; débits ÷ 10 → échec). Marche.
- **« Succès impliqué »** par une mesure publiée : marche, donne la localité sans trace.

## 12. Téléchargements à demander (aucun fait)

1. **OLMoE-1B-7B-0924 en GGUF Q4_K_M** (environ 4,2 Go ; Allen AI, Apache-2.0 ; données
   d'entraînement ouvertes) : produire une première trace de routage réelle pour
   `chargement_localite.py` (64 experts, top-8).
2. **Qwen3.6-35B-A3B UD-Q4_K_M** (22,13 Go ; `unsloth/Qwen3.6-35B-A3B-GGUF`, Apache-2.0) : MoE fin
   de 2026 (256 experts, top-8), le modèle d'Edge0 et de moe-stream, donc comparable ; plus
   gros que la RAM de la machine (premier essai « plus gros que la mémoire ») ; trace de routage
   et mesure de bout en bout contre llama.cpp `-ncmoe` + `--moe-cache-mib`.
3. Plus tard, selon l'étude 06 : **Qwen3-Next-80B-A3B Q4_K_M** (48,51 Go,
   `unsloth/Qwen3-Next-80B-A3B-Instruct-GGUF`, Apache-2.0), le premier modèle 3× plus gros que
   la mémoire que le juge donne jouable sans localité (borne 10,9 j/s).
Pour vider le routage, il faut un llama.cpp compilé avec un rappel d'évaluation (le paquet
b11515 n'a pas `llama-eval-callback`) : CUDA 13.1.2 et MSVC sont là, aucune installation à
demander.
