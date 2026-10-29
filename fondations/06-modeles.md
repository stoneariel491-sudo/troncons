# 06 — Les modèles ultra lourds visés, et comment juger

Étude de fondation de troncons, rédigée le 2026-10-15. Toutes les sources ont été consultées ce
jour-là. Chaque chiffre porte son étiquette : **mesuré ici** (sur la machine de Stone ou par nos outils
sur les fichiers publiés), **calculé** (dérivé de chiffres nommés, par une formule écrite ici),
**littérature** (chiffre d'un éditeur ou d'un article, non reproduit).

Outils : `outils/inventaire_modeles.py`, `outils/modeles-*.py`, `outils/modeles_physique.py`,
`outils/modeles-juge.sh`. Journaux : `fondations/journaux/06-modeles/`.

---

## 0. En bref

1. **Ce que « ultra lourd » veut dire ici.** La machine offre environ 6,5 Go de VRAM et 11 Go de RAM
   pour des poids (hypothèses dites, § 5.1), soit ~17,5 Go, et 404 Go de disque libre. Un modèle est
   « ultra lourd » quand son fichier dépasse nettement ces 17,5 Go ; il devient intéressant pour troncons
   quand il en est un multiple (×3 et plus) **et** que ses octets lus par jeton restent petits.
2. **Inventaire mesuré ici sur 49 dépôts officiels** (en-têtes safetensors lus par requêtes Range, aucun
   poids téléchargé). Notre compte de paramètres colle à celui des éditeurs pour 37 des 38 modèles qui
   en publient un (écart total ≤ 2,6 %) ; le 38e (Qwen3.8-Flash-Next, 6,67 G actifs contre « 6B ») tombe
   de 0,07 G sous le seuil déclaré, écart expliqué par la tête de sortie (0,64 G) que nous comptons. Le
   même témoin tombe sur la passe précédente de l'outil (6 échecs, tous de vrais bogues, § 3.2).
3. **Le juge, c'est la physique.** Plafond de débit par jeton (calculé, § 5) pour les fichiers exacts
   candidats, routage supposé uniforme (pire cas du cache) :

   | Fichier candidat | Taille | Toujours lus | Experts lus par jeton | Plafond jetons/s |
   |---|---:|---:|---:|---:|
   | gpt-oss-120b MXFP4 (natif) | 63,4 Go | 1,69 Go | 1,91 Go | 5,1 – 5,6 |
   | Qwen3.8-Flash-Next UD-Q2_K_XL | 78,9 Go | 3,54 Go | 0,90 Go | 10,0 – 12,6 |
   | Qwen3.8-Flash-Next UD-Q4_K_XL | 111,3 Go | 4,83 Go | 1,50 Go | 5,4 – 6,3 |
   | DeepSeek-V4-Flash-0731 UD-Q2_K_XL | 96,8 Go | 6,69 Go | 2,10 Go | 3,7 – 4,3 |
   | Kimi-K2.6 UD-Q2_K_XL (1 T de paramètres) | 340,5 Go | 8,52 Go | 6,90 Go | 1,1 – 1,2 |

   Le levier dominant est le **taux de succès du cache d'experts** : pour gpt-oss-120b, le faire passer
   de 26 % (uniforme) à 60 % porte le plafond de 5,6 à 10,3 jetons/s (calculé, § 5.4).
4. **Trois tendances de 2026 jouent pour troncons** (mesurées ici dans les en-têtes) :
   - des **tables de mémoire à recherche**, conçues pour vivre hors de la carte : Engram de DeepSeek
     V4.1-Flash (196,6 G de paramètres, 26 % du modèle), plongement de n-grammes de Qwen3.8-Flash-Next
     (51,2 G, 28 %) et de LongCat-Flash-Lite (31,4 G, 45 %). Un jeton y lit 16 (Qwen3.8) à 24 (V4.1) lignes, soit
     ~1,4 Kio utiles dans un fichier de 28,8 Go (Qwen3.8, calculé) ;
   - des **poids natifs en 4 bits** (gpt-oss MXFP4, Kimi K2-Thinking et K2.6 INT4, Kimi K3 MXFP4,
     DeepSeek V4 et MiMo V2.6 FP4 pour les experts) : la référence sans perte est déjà en 4 bits ;
   - un **routage par hachage** sur les 3 premières couches de DeepSeek V4 (table `tid2eid`
     [129 280 × 6]) : ces experts sont connus dès que le jeton est connu, avant tout calcul.
5. **Protocole de jugement** (§ 7) : base llama.cpp b11515 en mmap, texte réel fixé, génération
   gloutonne ; mesure des jetons/s, de la mémoire de pointe, de la VRAM et des octets lus sur le disque
   (`outils/modeles-base.py`) ; qualité par perplexité wikitext-2, divergence KL contre la référence,
   HellaSwag, Winogrande, MMLU et ARC (`outils/modeles-juge.sh`), validé ici sur Qwen3.5-4B. Mesure qui
   a corrigé le protocole : sur les **mêmes poids**, llama.cpp sur le processeur seul et llama.cpp sur la
   carte divergent autant qu'un pas de quantification (KL moyenne 0,0055, 99,9e centile 0,187, premier
   choix identique 95,96 %, texte glouton différent dès le 25e jeton), alors que le même moteur contre
   lui-même reste sous 0,000068. **Base et troncons doivent donc calculer sur le même étage**, ou la
   comparaison est noyée par l'écart entre moteurs.
6. **Téléchargements à demander, dans l'ordre** (§ 8) : gpt-oss-20b MXFP4 (12,1 Go, jumeau de
   développement), gpt-oss-120b MXFP4 (63,4 Go, premier ultra lourd), puis Qwen3.8-Flash-Next et
   DeepSeek-V4-Flash. Les deux premiers : 75,5 Go, licence Apache-2.0.

---

## 1. La question, et ce que j'en ai fait

La consigne : les modèles ouverts les plus utiles au-delà de la mémoire de la machine, leur
architecture, leurs tailles, leurs licences, leurs octets lus par jeton ; puis le protocole qui
jugera troncons, et la liste des téléchargements pour un premier modèle ultra lourd.

Deux choix de méthode, chacun avec sa raison :

- **Lire les en-têtes plutôt que les cartes.** Un fichier safetensors commence par 8 octets de
  longueur puis un JSON qui donne le type et la forme de chaque tenseur. Deux requêtes HTTP à plage
  par fragment suffisent : on obtient la forme exacte de chaque tenseur d'un modèle de 2,8 T sans
  télécharger ses poids. Les cartes servent ensuite de **second chemin**, indépendant (§ 3.2).
- **Lire l'en-tête du fichier GGUF exact qu'on téléchargerait.** Les quantifications « dynamiques »
  mélangent les types par tenseur ; seul l'en-tête du fichier dit combien d'octets un jeton lit
  (`outils/modeles-gguf-entete-distant.py`, écrit d'après la spécification publique de GGUF). Son
  témoin intégré : la somme des tailles de tenseurs plus l'en-tête égale la taille du fichier, à
  l'octet (vrai pour les 8 fichiers lus, `gguf-entetes.log`).

## 2. La machine, vue par un modèle

| Étage | Plafond | Statut |
|---|---:|---|
| VRAM GDDR6, 128 bits, 16 Gbit/s | 256 Go/s | calculé (étude 01, seuils déclarés) |
| RAM, un seul module DDR5-5200 (64 bits) | 41,6 Go/s | calculé (étude 01) |
| NVMe PCIe 4.0 ×4 | 7,877 Go/s | calculé (étude 01) |
| PCIe de la carte, hôte → carte, mémoire épinglée, 256 Mio | 6,38 Go/s | mesuré ici (étude 04, `pcie-1.json`) |
| Capacité utile pour des poids : VRAM | ~6,5 Go | hypothèse dite (8 188 Mio moins écran, contexte, cache KV court) |
| Capacité utile pour des poids : RAM | ~11 Go | hypothèse dite (15,6 Go moins système et applications) |
| Disque libre | 404 Go | relevé (SOCLE) |

Une remarque de fond : la RAM n'a qu'un seul module, donc un seul canal de 64 bits. À 41,6 Go/s
elle n'est que 5,3 fois plus rapide que le NVMe. Le gain d'un cache en RAM existe, mais l'écart
entre « en RAM » et « sur disque » est bien plus étroit que sur une machine de bureau à deux canaux.

## 3. L'inventaire : 49 dépôts, lus dans leurs en-têtes

### 3.1 Ce que l'outil compte

Pour chaque tenseur, une catégorie (`outils/inventaire_modeles.py`) :

- **experts routés** : un expert sur E est lu par jeton et par choix du routeur ;
- **toujours lus** : attention, couches denses, experts partagés, routeur, normes, tête de sortie ;
- **plongement** : une ligne lue par jeton, compté à part ;
- **MTP** : couches de prédiction multi-jetons, lues seulement en décodage spéculatif ;
- **recherche** : tables Engram ou de n-grammes, quelques lignes par jeton ;
- **hors texte** : tour de vision ou d'audio.

Paramètres actifs par jeton = toujours lus + Σ_couches (k/E) × experts routés de la couche.
Formats empaquetés reconnus (vérifiés chacun sur un dépôt réel) : MXFP4 en U8 « _blocks » (gpt-oss),
FP4 en I8 avec échelle F8_E8M0 (DeepSeek V4), FP4 en U8 avec une échelle par groupe de 32 (MiMo V2.6,
Kimi K3, détecté par la forme : dernière dimension de l'échelle × 16 = celle du tenseur), INT4 en I32
empaqueté par 8 (Kimi K2-Thinking, K2.6).

### 3.2 Le témoin, et sa cassure

Second chemin : les chiffres publiés par l'éditeur (carte du modèle ou article). Seuils déclarés dans
l'outil avant la première exécution : total à ±3 % (les éditeurs arrondissent à l'entier de
milliards ; 3 % ne laisse passer ni un facteur 2 ni un doublon de fichiers), actifs à
±max(0,6 G ; 10 %). Trois définitions du total sont essayées (texte ; texte + vision ;
texte − MTP), et le journal dit laquelle colle.

- **Passe 3 (la bonne)** : 37 OK sur 38 ; 1 échec, Qwen3.8-Flash-Next, actifs 6,67 G contre « 6B »
  (écart 0,67 G pour une tolérance de 0,60 G). Sans la tête de sortie (0,636 G), on trouve 6,03 G.
  Le seuil reste ce qu'il était : l'échec est écrit, avec sa cause
  (`temoin-inventaire-passe3.txt`).
- **Passe 2 (la cassure)** : le même témoin trouve 6 échecs, et ce sont 6 vrais bogues que la passe 3
  corrige : Mistral-Small-4 et Mistral-Medium-3.5 comptés deux fois (+100 % et +95 % : Mistral publie
  à la racine deux copies des mêmes poids, `consolidated-*` et `model-*`) ; MiMo V2.6 et Kimi K3
  comptés à moitié (−48 % et −49 % : FP4 empaqueté en U8 non reconnu) ; Kimi K3 à 50 experts actifs
  au lieu de 16 (la clé `top_k` de son config est un paramètre d'échantillonnage) ; Step-3.5-Flash à
  196 G actifs (experts fusionnés sous `.moe.` sans le mot « experts ») ; Qwen3.8 à 57,9 G actifs (la
  table de n-grammes comptée comme toujours lue). `temoin-inventaire-passe2.txt`.

~~DeepSeek-V4-Flash : 149,2 G au total, 10,6 G actifs~~ (première passe, prédécesseur : FP4 empaqueté
en I8 non reconnu et nom de la tête « head.weight » manqué). Corrigé : 284,3 G hors MTP, 13,27 G actifs,
contre 284 G et 13 G dans l'article (arXiv 2606.19348).

### 3.3 Les modèles MoE

Lu dans les en-têtes et les config (mesuré ici), sauf mention. L = couches, E = experts routés par
couche, k = experts routés actifs, P = experts partagés.

| Modèle (dépôt, date) | Total texte | Actifs/jeton | Architecture | Format publié | Licence |
|---|---:|---:|---|---|---|
| openai/gpt-oss-120b (2025-08) | 116,8 G | 5,13 G | L 36, E 128, k 4 ; GQA 64/8, fenêtre glissante 128 sur 1 couche sur 2, puits d'attention | experts MXFP4 natifs (60,9 Go) + BF16 | Apache-2.0 |
| openai/gpt-oss-20b (2025-08) | 20,9 G | 3,61 G | L 24, E 32, k 4 ; même schéma | MXFP4 | Apache-2.0 |
| Qwen/Qwen3-Next-80B-A3B (2025-09) | 81,3 G | 3,56 G | L 48, E 512, k 10 + P ; Gated DeltaNet 3 : 1 attention | BF16 | Apache-2.0 |
| Qwen/Qwen3.5-122B-A10B (2026-02) | 124,6 G | 9,01 G | L 48 (36 linéaires, 12 pleines), E 256, k 8 + P, MTP 1 | BF16 | Apache-2.0 |
| Qwen/Qwen3.5-397B-A17B (2026-02) | 402,9 G | 16,33 G | L 60 (45 / 15), E 512, k 10 + P, MTP 1 | BF16 | Apache-2.0 |
| Qwen/Qwen3-235B-A22B-2507 (2025-07) | 235,1 G | 21,57 G | L 94, E 128, k 8 ; GQA 64/4 | BF16 | Apache-2.0 |
| Qwen/Qwen3-Coder-480B-A35B (2025-07) | 480,2 G | 34,54 G | L 62, E 160, k 8 | BF16 | Apache-2.0 |
| Qwen/Qwen3.8-Flash-Next (2026-08) | 179,6 G | 6,67 G | L 48 (36 DeltaNet, 12 attention creuse QSA), E 512, k 10 + P, résiduel à 4 branches ; **table de n-grammes 51,2 G** (couche 2) | BF16 | qwen-community-1.0 |
| Qwen/Qwen3.8-2.4T-A95B (2026-08) | 2 446 G | 93,25 G | L 92 (69 / 23), E 512, k 10 + P | BF16 | qwen3.8-max |
| deepseek-ai/DeepSeek-V3 / R1-0528 (2024-12 / 2025-05) | 684,5 G | 36,63 G | L 61, E 256, k 8 + 1 P, MLA, MTP 1 | FP8 | V3 : licence modèle DeepSeek ; R1 : MIT |
| deepseek-ai/DeepSeek-V3.2 (2025-12) | 685,4 G | 37,48 G | idem + attention creuse (DSA) | FP8 | MIT |
| deepseek-ai/DeepSeek-V4-Flash-0731 (2026-07) | 304,2 G (284,3 hors MTP) | 13,27 G | L 43, E 256, k 6 + 1 P ; 1 tête KV, attention compressée (CSA/HCA, littérature) ; **3 couches routées par hachage** ; hyper-connexions | experts FP4 natifs + FP8 | MIT |
| deepseek-ai/DeepSeek-V4.1-Flash (2026-09) | 762,7 G | 16,13 G | L 40 (encodeur 20 + décodeur 20, « CED », carte du modèle), E 384, k 6 + 1 P ; **Engram 196,6 G** (couches 1 et 14) ; MTP 3 + DSpark ; vision | experts FP4, FP8 | MIT |
| deepseek-ai/DeepSeek-V4-Pro-0813 (2026-08) | 1 650 G | 48,85 G | L 61, E 384, k 6 + 1 P, 3 couches hachées | FP4 / FP8 | MIT |
| moonshotai/Kimi-K2-Instruct-0905 (2025-09) | 1 026 G | 31,69 G | L 61, E 384, k 8 + 1 P, MLA | FP8 | MIT modifiée |
| moonshotai/Kimi-K2-Thinking, K2.6 (2025-11, 2026-04) | 1 026 G | 31,69 G | idem | **INT4 natif (QAT)** | MIT modifiée |
| moonshotai/Kimi-K3 (2026-06) | 2 780 G | 104,19 G | L 93, E 896, k 16 + 2 P ; KDA + MLA, « LatentMoE » | **MXFP4 natif (QAT)** | kimi-k3 |
| zai-org/GLM-4.5-Air (2025-07) | 110,5 G | 12,80 G | L 46, E 128, k 8 + 1 P, GQA 96/8, MTP 1 | BF16 | MIT |
| zai-org/GLM-4.6 / 4.7 (2025-09 / 12) | 357 G | 32,86 G | L 92, E 160, k 8 + 1 P, MTP 1 | BF16 | MIT |
| zai-org/GLM-5.1 / 5.3 (2026-04 / 08) | 754 G | 40,8 / 40,3 G | L 78, E 256, k 8 + 1 P, MLA, MTP 1 | BF16 / FP8 | 5.1 : MIT ; 5.3 : glm-5.3 |
| zai-org/GLM-5.3-Flash (2026-08) | 320,8 G | 16,74 G | L 45 (34 linéaires, 11 DSA), E 288, k 8 + 1 P | FP8 | MIT |
| meta Llama-4-Scout (2025-04) | 107,8 G | 16,14 G | L 48, E 16, k 1 + P | BF16 | Llama 4 Community |
| meta Llama-4-Maverick (2025-04) | 400,7 G | 16,15 G | L 48 (MoE une couche sur deux, littérature ; cohérent avec 13,1 G toujours lus), E 128, k 1 + P | BF16 | Llama 4 Community |
| mistralai/Mixtral-8x7B / 8x22B (2023-12 / 2024-04) | 46,7 / 140,6 G | 12,75 / 38,96 G | E 8, k 2 | BF16 | Apache-2.0 |
| mistralai/Mistral-Small-4-119B (2026-01) | 119,0 G | 6,10 G | L 36, E 128, k 4 + 1 P, MLA | FP8 | Apache-2.0 |
| mistralai/Mistral-Large-3-675B (2025-11) | 673,4 G | 39,02 G | L 61, E 128, k 4 + 1 P, MLA | FP8 | Apache-2.0 |
| MiniMaxAI/MiniMax-M2.7 (2026-04) | 228,7 G | 10,42 G | L 62, E 256, k 8 | FP8 | non commerciale (MiniMax) |
| MiniMaxAI/MiniMax-M3 (2026-06) | 426,4 G | 24,92 G | L 60, E 128, k 4 + 1 P, attention creuse MSA | BF16 | minimax-community |
| XiaomiMiMo/MiMo-V2.6-Flash (2026-09) | 309,8 G | 14,85 G | L 48 (39 fenêtre, 9 globales), E 256, k 8, MTP 5 couches | experts MXFP4 | MIT |
| inclusionAI/Ling-3.0-flash / 3.1-flash (2026-08 / 10) | 127,5 / 572,1 G | 5,10 / 24,25 G | KDA 5 : 1 MLA, E 512, k 8 + 1 P | BF16 / FP8 | MIT |
| nvidia/Nemotron-3-Super / Ultra (2026-03 / 06) | 123,6 / 560,5 G | 12,77 / 56,06 G | hybride Mamba-attention (littérature), E 512, k 22 + 1 P | BF16 | NVIDIA Open Model / OpenMDW-1.1 |
| stepfun-ai/Step-3.5-Flash (2026-02) | 199,4 G | 11,46 G | L 45 (36 fenêtre, 12 pleines), E 288, k 8, MTP 3 | BF16 | Apache-2.0 |
| tencent/Hy3 (2026-07) | 298,8 G | 20,18 G | L 80, E 192, k 8 + 1 P, MTP 1 | BF16 | Apache-2.0 |
| meituan-longcat/LongCat-Flash-Lite (2026-01) | 69,1 G | 4,51 G (2,9 à 4,5 selon le jeton, littérature) | L 14, E 256, k 12, MLA ; **n-grammes 31,4 G** | BF16 | MIT |

### 3.4 Les modèles denses

| Modèle | Total | Architecture | Licence |
|---|---:|---|---|
| Llama-3.3-70B-Instruct (2024-12) | 70,6 G | L 80, d 8192, GQA 64/8 | Llama 3.3 Community |
| Qwen2.5-72B-Instruct (2024-09) | 72,7 G | L 80, d 8192, GQA 64/8 | Qwen (seuil 100 M d'utilisateurs) |
| Mistral-Large-Instruct-2411 (2024-11) | 122,6 G | L 88, d 12288 | Mistral Research License (non commerciale) |
| Mistral-Medium-3.5-128B (2026-03) | 125,0 G (+ vision) | L 88, d 12288, FP8 | MIT modifiée (exclut les sociétés > 20 M$/mois) |
| Llama 3.1 405B (2024-07 ; mesuré sur Hermes-3, même architecture) | 405,9 G | L 126, d 16384, GQA 128/8 | Llama 3.1 Community |

Un dense lit **tous** ses poids à chaque jeton. À 4 bits, Llama-3.3-70B lit 34,8 Go par jeton
(calculé) : ~17,5 Go servis par la carte et la RAM, le reste du disque, soit un plafond de 0,4 à
0,5 jeton/s. Pour troncons, un dense au-delà de la mémoire n'est jugeable que comme cas limite ;
le terrain est le MoE.

### 3.5 Tailles publiées (GGUF), lues dans l'arbre des dépôts

`gguf-tailles.json` (40 dépôts) donne la taille exacte de chaque niveau, sans téléchargement. Quelques
repères (Go, mesuré ici) :

| Modèle | ~1,6 bit | ~2 bits | ~3 bits | ~4 bits | 8 bits |
|---|---:|---:|---:|---:|---:|
| gpt-oss-120b | — | 62,6 (Q2_K) | 62,6 | 62,8 (Q4_K_M) ; **63,4 (MXFP4 natif)** | 63,4 |
| Qwen3.8-Flash-Next | 72,5 (UD-IQ1_S) | 78,9 (UD-Q2_K_XL) | 90,0 | 111,3 (UD-Q4_K_XL) | 188,2 |
| Qwen3.5-122B-A10B | 34,2 (UD-IQ1_M) | 41,8 | 57,0 | 77,0 | 129,9 |
| DeepSeek-V4-Flash-0731 | 82,5 | 96,8 | 128,2 | 155,1 | 161,9 (UD-Q8_K_XL) |
| Qwen3.5-397B-A17B | 106,8 | 123,1 (UD-IQ2_M) | 178,7 | 245,3 | 421,5 |
| Kimi-K2.6 | — | 340,5 | — | 583,7 | 594,5 |
| Kimi-K2-Instruct-0905 | 248,6 (UD-TQ1_0) | 383,6 | 452,3 | 588,1 | 1 091 |

Deux lectures. gpt-oss-120b pèse ~63 Go **quel que soit** le niveau : ses experts restent en MXFP4,
seule l'attention change de type. Et pour les modèles nés en 4 bits (K2.6, V4-Flash), le niveau
« 8 bits » pèse presque autant que le « 4 bits » : il n'y a rien au-dessus du 4 bits natif à garder.

## 4. Octets lus par jeton, à 2, 3 et 4 bits

### 4.1 La formule

Avec A les paramètres toujours lus, R les paramètres d'experts routés lus par jeton, b les bits par
poids des experts :

- **uniforme** : O = (A + R) × b / 8 ;
- **mixte** (le choix réel des quantifications dynamiques : toujours-lus en Q8_0, 8,5 bits) :
  O = A × 8,5/8 + R × b/8.

Le plongement (une ligne), les tables de recherche (quelques lignes) et la MTP (hors décodage
spéculatif) sont exclus. Tableau complet des 49 modèles : `octets-par-jeton.md` (calculé).

### 4.2 Extraits (Go par jeton, calculé)

| Modèle | A (G) | R (G) | Uniforme 2 / 3 / 4 b | Mixte 2 / 3 / 4 b |
|---|---:|---:|---|---|
| gpt-oss-120b | 1,55 | 3,58 | 1,28 / 1,92 / 2,57 | 2,54 / 2,99 / 3,44 |
| Qwen3-Next-80B-A3B | 2,05 | 1,51 | 0,89 / 1,34 / 1,78 | 2,56 / 2,75 / 2,94 |
| Qwen3.8-Flash-Next | 4,31 | 2,36 | 1,67 / 2,50 / 3,34 | 5,17 / 5,47 / 5,76 |
| Ling-3.0-flash | 3,22 | 1,89 | 1,28 / 1,91 / 2,55 | 3,89 / 4,12 / 4,36 |
| Qwen3.5-122B-A10B | 5,38 | 3,62 | 2,25 / 3,38 / 4,50 | 6,63 / 7,08 / 7,53 |
| MiniMax-M2.7 | 3,39 | 7,02 | 2,60 / 3,91 / 5,21 | 5,36 / 6,24 / 7,12 |
| DeepSeek-V4-Flash-0731 | 6,78 | 6,49 | 3,32 / 4,98 / 6,64 | 8,83 / 9,64 / 10,45 |
| Qwen3.5-397B-A17B | 8,78 | 7,55 | 4,08 / 6,12 / 8,17 | 11,22 / 12,16 / 13,11 |
| Llama-4-Maverick | 13,13 | 3,02 | 4,04 / 6,06 / 8,08 | 14,71 / 15,08 / 15,46 |
| Kimi-K2.x | 10,55 | 21,14 | 7,92 / 11,88 / 15,84 | 16,49 / 19,13 / 21,78 |
| DeepSeek-V3.x | 16,19 | 20,43 | 9,16 / 13,73 / 18,31 | 22,31 / 24,87 / 27,42 |
| Llama-3.3-70B (dense) | 69,50 | 0 | 17,38 / 26,06 / 34,75 | idem |

### 4.3 Second chemin : les fichiers exacts

Lu dans les en-têtes GGUF distants (mesuré ici), contre la formule mixte (calculé) :

| Fichier | Toujours lus + experts lus (exact) | Formule mixte | Écart |
|---|---:|---:|---:|
| gpt-oss-120b MXFP4 | 1,69 + 1,91 = 3,60 Go | 3,55 Go (MXFP4 = 4,25 bits) | −1,4 % |
| DeepSeek-V4-Flash UD-Q2_K_XL | 6,69 + 2,10 = 8,79 Go | 8,83 Go | +0,5 % |
| Qwen3.8-Flash-Next UD-Q2_K_XL | 3,54 + 0,90 = 4,44 Go | 5,17 Go | +16 % |
| Kimi-K2.6 UD-Q2_K_XL | 8,52 + 6,90 = 15,42 Go | 16,49 Go | +7 % |

La formule est juste là où les toujours-lus sont vraiment en 8 bits ; elle surestime Qwen3.8 (une part
de ses toujours-lus est en 4 à 6 bits) et se trompe de sens sur Kimi (« 2 bits » y veut dire Q2_K à
2,625 bits pour les experts). Pour décider, on prend donc l'en-tête du fichier, jamais la formule.

## 5. Le juge physique : plafonds de débit par jeton

### 5.1 Le modèle de coût (déclaré dans `outils/modeles_physique.py` avant tout usage)

- Les toujours-lus résident sur la carte s'ils tiennent dans 6,5 Go ; sinon le surplus est lu par le
  processeur en RAM.
- Les experts routés se partagent un cache C = 11 Go de RAM + la VRAM restante, et le disque.
- **Routage supposé uniforme et sans mémoire** : taux de succès h = C / E_octets. C'est le pire cas
  du cache ; toute localité réelle l'améliore, et c'est précisément ce qu'il faut mesurer.
- Experts trouvés en RAM : calculés par le processeur à 41,6 Go/s. Manqués : lus sur le NVMe à
  7,877 Go/s.
- t_opt = max(A/256, h·R/41,6, (1−h)·R/7,877) (étages parfaitement recouverts) ;
  t_pes = la somme (étages en série). Le calcul arithmétique est supposé gratuit.

### 5.2 Les fichiers candidats (calculé, `plafonds-fichiers.md`)

| Fichier | Taille | Experts : total / lus par jeton | Table : totale / lue par jeton | h uniforme | Jetons/s (opt. – pess.) | Tout sur NVMe |
|---|---:|---|---|---:|---|---:|
| gpt-oss-20b MXFP4 | 12,1 Go | 10,2 / 1,27 Go | — | 100 % | 32,7 – 28,0 | 6,0 |
| gpt-oss-120b MXFP4 | 63,4 Go | 61,1 / 1,91 Go | — | 26 % | 5,6 – 5,1 | 4,0 |
| Qwen3.8-Flash-Next UD-Q2_K_XL | 78,9 Go | 46,1 / 0,90 Go | 28,8 Go / 64 Kio | 30 % | 12,6 – 10,0 | 7,8 |
| Qwen3.8-Flash-Next UD-Q4_K_XL | 111,3 Go | 77,0 / 1,50 Go | 28,8 Go / 64 Kio | 16 % | 6,3 – 5,4 | 4,8 |
| DeepSeek-V4-Flash UD-Q2_K_XL | 96,8 Go | 89,8 / 2,10 Go | — | 12 % | 4,3 – 3,7 | 3,4 |
| DeepSeek-V4-Flash UD-Q4_K_XL | 155,1 Go | 147,2 / 3,45 Go | — | 7 % | 2,5 – 2,2 | 2,1 |
| Kimi-K2.6 UD-Q2_K_XL | 340,5 Go | 331,1 / 6,90 Go | — | 3 % | 1,2 – 1,1 | 1,1 |

« Table lue par jeton » : (n − 1) × têtes = 2 × 8 = 16 lignes pour Qwen3.8 (clés GGUF
`ple.ngram_size` = 3 et `ple.heads_per_ngram` = 8 ; même règle dans le code de llama.cpp,
`src/models/qwen4exp.cpp`), comptées à une page de 4 Kio chacune lue sur le disque. Utile : 16 × 90
octets = 1,4 Kio (ligne de 160 valeurs en IQ4_NL). La table de 28,8 Go coûte donc moins d'un millième
du budget disque d'un jeton.

### 5.3 Ce que ces plafonds disent

- **DeepSeek-V4-Flash déborde la carte par ses toujours-lus.** À UD-Q2_K_XL, ils pèsent 6,69 Go
  (attention en Q8_0 : `attn_q_b`, `attn_output_a`, `attn_output_b`, 1,53 Go chacune), au-dessus des
  6,5 Go supposés. Sur 8 Go, il faudra les requantifier (Q4/Q5) ou en laisser une part en RAM.
- **Kimi-K2.6 tient sur le disque (340 Go sur 404) mais plafonne à ~1 jeton/s** : 6,9 Go d'experts par
  jeton contre 7,9 Go/s de disque. C'est la démonstration « 1 T sur un portable », pas un outil.
- **Le meilleur rapport utile/physique est Qwen3.8-Flash-Next UD-Q2_K_XL** (plafond 10 à 12,6
  jetons/s), puis gpt-oss-120b (5 à 5,6), qui a l'avantage décisif d'une référence sans perte.

### 5.4 La sensibilité qui compte

Pour gpt-oss-120b, le temps est dominé par le disque : (1 − h) × 1,91 Go / 7,877 Go/s. Plafond
optimiste en fonction de h (calculé) :

| h | 26 % (uniforme) | 40 % | 60 % | 80 % | 95 % |
|---|---:|---:|---:|---:|---:|
| jetons/s | 5,6 | 6,9 | 10,3 | 20,6 | 22,9 (borné par la RAM : 1,81 Go / 41,6 Go/s) |

Chaque point de succès du cache gagné par la prédiction, la localité ou une compression qui fait
tenir plus d'experts dans 17,5 Go se lit directement en jetons/s. C'est le terrain des études 03, 04
et 05 ; le juge ci-dessous mesure h et les octets réellement lus.

## 6. Ce qui a changé en 2026 et sert troncons

1. **Les tables à recherche, faites pour l'extérieur de la carte.** L'article Engram
   (arXiv 2601.07372, 2026-01-12, v2 2026-07-12) pose le principe : des lignes adressées par un hachage
   déterministe des n-grammes de jetons, donc connues avant le calcul et préchargeables. Il mesure une
   table de 100 G en DRAM hôte sur H800 avec moins de 3 % de perte de débit (littérature, non
   reproduit), et **propose sans le mesurer** un étage NVMe avec cache des n-grammes fréquents (loi de
   Zipf). Trois modèles ouverts portent aujourd'hui une telle table (mesuré ici) : DeepSeek V4.1-Flash
   (Engram, 2 couches, 384 M de lignes de 256 octets FP8 chacune), Qwen3.8-Flash-Next (320 M de lignes
   de 160 valeurs) et LongCat-Flash-Lite (12 tables de 10,2 M de lignes de 256 valeurs).
   llama.cpp sait déjà laisser une telle table sur le disque : son chargeur porte un drapeau
   `TENSOR_READ_LAZY` (« keep PLE / engrams embd tensors on disk, read them on demand »), qui exclut le
   tenseur du préchargement et précharge seulement les lignes demandées (`llama_prefetch_rows`) au
   moment où les entrées du jeton sont posées ; il l'applique à Qwen3.8 (`qwen4exp`) et Gemma 4, et
   seulement aux tenseurs de plus de 4 Gio en mode automatique (lu dans le code, dépôt
   ggml-org/llama.cpp, MIT, commit 843e7dc du 2026-10-15). Il ne connaît pas encore DeepSeek V4.1
   (aucune architecture `deepseek41`, aucun Engram dans `src/`).
2. **Les poids nés en 4 bits.** gpt-oss (MXFP4 sur les experts : 60,9 Go sur 65,2), Kimi K2-Thinking et
   K2.6 (INT4 par entraînement conscient de la quantification), Kimi K3 (MXFP4), DeepSeek V4 et MiMo
   V2.6 (experts FP4). Conséquence pour troncons : sur ces modèles, la seule compression sans perte qui
   reste est un codage entropique des codes de 4 bits et de leurs échelles. Les échelles E8M0 de V4-Flash
   pèsent 9,3 Go pour 148,2 Go de codes FP4 (6,3 %, mesuré ici dans les en-têtes) : une cible chiffrée
   pour l'étude 03.
3. **Le routage par hachage.** DeepSeek V4-Flash et V4-Pro routent leurs 3 premières couches par une
   table jeton → experts (`ffn_gate_tid2eid`, clé GGUF `deepseek4.hash_layer_count` = 3). Ces experts
   (3 couches sur 43, ~7 % des octets d'experts de V4-Flash) sont connus dès que le jeton est tiré. llama.cpp
   les traite comme une simple lecture de lignes dans le graphe (`GGML_OP_GET_ROWS`), sans en tirer de
   préchargement.
4. **La prédiction multi-jetons intégrée** (MTP de DeepSeek, GLM, Qwen ; 5 couches et 7 jetons par
   passe chez MiMo V2.6 ; DSpark chez V4.1). Elle multiplie les jetons par lecture d'experts, à
   condition que les experts des jetons vérifiés ensemble se recouvrent : à mesurer.
5. **L'attention linéaire hybride** (Gated DeltaNet chez Qwen, KDA chez Kimi et Ling) : le cache KV
   cesse d'être une contrainte à contexte court sur 8 Go. Le coût est ailleurs : dans les experts.

## 7. Le protocole de jugement

### 7.1 La base : llama.cpp tel quel

- Binaire : llama.cpp b11515, CUDA 12.4, déjà présent (`~/dev/modeles/llama.cpp-b11515`).
  Il connaît les architectures `gpt-oss`, `qwen4exp` (Qwen3.8), `deepseek4`, `kimi-k3`, `glm5`,
  `minimax-m3`, `mimo2`, `step35` (noms relevés dans `llama.dll`, mesuré ici) et contient la lecture
  paresseuse et le préchargement de lignes.
- Chargement : mmap (défaut sous Windows : `CreateFileMapping` + `MapViewOfFile` de tout le fichier,
  `PrefetchVirtualMemory` sur les parties non paresseuses ; lu dans `src/llama-mmap.cpp`). Pour un
  fichier plus gros que la RAM, mmap est le seul mode qui démarre : le système charge les pages à la
  faute et évince les plus anciennes.
- Répartition : toutes les couches sur la carte (`-ngl 99`) et les experts en RAM/mmap
  (`--cpu-moe`, ou `--n-cpu-moe N` réglé par `--fit on`). On publie les deux points : experts tous en
  mmap, et meilleur `N` trouvé.

### 7.2 Une passe

`outils/modeles-base.py` lance `llama-completion` sur un texte réel fixé (les 3 000 premiers octets de
wikitext-2 test, SHA-256 `eadbe87e…eff`), 256 jetons, glouton (`--temp 0 --seed 1 --ignore-eos`), et
relève :

- jetons/s du préremplissage et de la génération (compteurs internes `--perf`) ;
- mémoire du processus, de pointe et au dernier relevé (ensemble de travail et mémoire engagée, API
  Windows, toutes les 100 ms) ; VRAM de pointe et au repos (nvidia-smi, 250 ms) ;
- octets lus sur le disque : compteur « PhysicalDisk(_Total) / Disk Read Bytes/sec » lu par l'API PDH
  sous son nom anglais, toutes les 0,5 s, intégré ; repos de 10 s avant la passe pour chiffrer la
  charge des autres programmes (le compteur est global). typeperf ne convient pas : sur ce Windows en
  français il refuse le nom anglais du compteur (« aucun compteur valide », mesuré ici) ;
- empreinte SHA-256 du texte produit.

Pourquoi pas llama-bench : sa génération part de jetons sans sens ; pour un MoE hors mémoire, le choix
des experts, donc les octets lus, dépend du contenu.

### 7.3 Les témoins, et ce qu'ils ont déjà appris (mesuré ici, Qwen3.5-4B Q4_K_M)

- **Justesse d'un moteur sans perte.** J'avais d'abord écrit : « troncons doit produire exactement les
  mêmes 256 jetons que llama.cpp ». ~~Le témoin de justesse d'un moteur sans perte est l'égalité des
  jetons gloutons avec llama.cpp.~~ La mesure l'a démenti : llama.cpp lui-même, sur le même fichier,
  produit un texte glouton différent selon le moteur. Sur la carte, deux passes donnent le même texte
  (SHA-256 `ea5a3df3…4168` deux fois) ; avec les couches sur le processeur (`-ngl 0` ; le préremplissage, en lots, reste déchargé sur la carte, la génération jeton par jeton se calcule sur le processeur), le texte bifurque au 25e jeton environ
  (« appeared in the television » contre « appeared on a 2005 episode »). Deux moteurs justes
  divergent donc sur une quasi-égalité de logits. Le témoin retenu :
  - **même moteur, même configuration** : égalité des jetons (vaut pour comparer deux versions de
    troncons entre elles, ou troncons au llama.cpp dont il réutiliserait les noyaux) ;
  - **plancher de l'instrument** (même moteur, la carte contre ses propres logits, 10 fenêtres, 2 560
    jetons notés) : KL moyenne −0,000000 ± 0,000000, 99,9e centile 0,000055, maximum 0,000068, premier
    choix identique 100,000 % (`juge/temoin-meme.kld.log`). Les KL négatives (minimum −0,000056)
    viennent du stockage de la base en 16 bits par logit (pas = (max − min)/65 535, lu dans
    `tools/perplexity/perplexity.cpp`).
    ~~C'est le plancher mesuré entre deux moteurs justes, la carte contre le processeur.~~ Faux : ma
    passe « processeur » (`-ngl 0`) calculait encore sur la carte, parce que llama.cpp décharge par
    défaut les opérations des grands lots vers la carte (`--op-offload`, vrai par défaut) ; elle a donné
    exactement les mêmes chiffres que le témoin ci-dessus
    (`juge/plancher-ngl0-dechargement-contre-carte.kld.log`).
  - **écart entre deux moteurs justes**, mesuré cette fois avec le processeur **seul**
    (`CUDA_VISIBLE_DEVICES=-1`), mêmes poids, contre la base de la carte : KL moyenne 0,005516 ± 0,000257,
    médiane 0,003209, 99e centile 0,036760, 99,9e centile 0,186865, maximum 0,360466, premier choix
    identique 95,961 ± 0,390 %, rapport des perplexités 0,996137 ± 0,002364
    (`juge/plancher-cpu-pur-contre-carte.kld.log`). C'est l'ordre de grandeur d'un pas de quantification :
    le moteur (activations quantifiées en 8 bits sur le processeur, autres chemins sur la carte, état
    récurrent du Gated DeltaNet ; causes supposées, non isolées) pèse autant que la compression qu'on
    voudrait juger.
  Règle qui en découle : un moteur « sans perte » se juge contre une base **du même étage de calcul**
  (carte contre carte), et doit y retomber dans le plancher de l'instrument (KL ≤ ~7e-5, premier choix
  100 %). Si troncons calcule sur un autre étage que la base (par exemple les experts sur le processeur),
  l'écart entre moteurs se mesure d'abord, à part, et la comparaison se fait contre lui. C'est pourquoi
  gpt-oss vient en premier : son MXFP4 est le poids d'origine, donc toute KL au-dessus du plancher du
  même étage est une erreur de troncons, pas un effet de quantification.
- **Justesse de la mesure de qualité** : le même modèle contre ses propres logits retombe dans le
  plancher (ci-dessus) ; un autre modèle de même vocabulaire, Qwen3.5-9B contre la base du 4B, en sort
  nettement : KL moyenne 0,293946 ± 0,008562, 99,9e centile 4,92, premier choix identique 76,863 %
  (`juge/temoin-autre.kld.log`). L'instrument tombe quand il doit tomber. La perplexité est
  déterministe : seconde passe identique, 8,7259 ± 0,22952 (`juge/q35-4b.ppl-bis.log`).
- **Mémoire.** J'attendais un ensemble de travail de pointe plus petit avec les couches sur la carte ;
  ~~sur la carte (`-ngl 99`), nettement moins~~ : faux pour la pointe, qui compte les pages lues une
  fois pour la copie vers la carte (pointe 2,64 à 3,45 Go avec `-ngl 99`, 2,83 Go avec `-ngl 0`, pour un
  fichier de 2,74 Go). Le bon témoin est le **dernier relevé** pendant la génération : 96 Mo avec
  `-ngl 99` (poids sur la carte, pages rendues), contre un ensemble proche de la taille du fichier sur
  le processeur. Le banc relève désormais les deux (`base-q35-4b-*.json`).
- **Disque** (`outils/modeles-temoin-disque.py`, seuils déclarés dans l'outil) : une lecture sans tampon
  de 265 Mo doit se voir à ≥ 95 % au-dessus du repos ; une seconde lecture ordinaire du même fichier
  (servie par le cache) à ≤ 10 %. Trois passes, avec 20 à 27 Mo/s de charge de repos due aux autres
  agents : passe 1, lecture sans tampon vue à 93,6 % (échec) et cache invisible (tient) ; passe 2, les
  deux tiennent (102 % et 3 %) ; passe 3, lecture vue à 111 % mais cache vu à 103 % (échec : une rafale
  d'un autre programme ou une éviction). Lecture : l'instrument voit les lectures, mais la soustraction
  du repos ne résout pas mieux que ~±100 Mo sur quelques secondes quand la machine est partagée. C'est
  suffisant pour des Go lus par jeton (1,9 Go pour gpt-oss-120b) ; le témoin est à refaire au calme
  (`temoin-disque*.json`).

### 7.4 Qualité, légère et sur la machine

`outils/modeles-juge.sh`, identique pour la base et pour troncons :

- perplexité wikitext-2 test (CC BY-SA 3.0), fenêtres de 512, 40 fenêtres (~20 000 jetons) ;
- divergence KL contre les logits de référence (10 fenêtres) : moyenne, 99,9e centile, maximum, taux
  de premier choix identique ;
- HellaSwag (400 tâches, MIT), Winogrande (400, jeu de llama.cpp), MMLU validation (toutes, MIT), ARC
  facile + défi validation (CC BY-SA 4.0) ; jeux de données de 0,15 à 7,8 Mo, empreintes dans
  `juge/donnees-sha256.txt`. llama.cpp tire les tâches avec un générateur à graine fixe
  (`std::mt19937 rng(1)`), donc le même sous-ensemble à chaque passe.

Validation du juge (mesuré ici, Qwen3.5-4B Q4_K_M, carte, 2026-10-15) : perplexité 8,7259 ± 0,2295 ;
HellaSwag 72,50 % [67,93 ; 76,65] ; Winogrande 67,50 ± 2,34. MMLU : passe interrompue à 758 questions
sur manque de mémoire de la carte (d'autres agents l'occupaient), 36,9 % à ce point
(`juge/q35-4b.mmlu.log`) ; ARC non passé. Le juge a donc besoin de la carte libre, ou de `N_MC`
(nombre de questions) réduit.

Ce que confirme une observation plus ancienne de la même séance : la première fenêtre de perplexité
donne 6,0651 avec les produits matriciels déchargés sur la carte et 6,0037 sur le processeur seul. **Le
moteur fait partie de la mesure.**

### 7.5 Décider

- Séries ABBA (A1 B1 B2 A2) répétées au moins deux fois ; bruit = |A1 − A2| / moyenne ; une différence
  n'est réelle que si elle dépasse 2 × le plus grand bruit et 3 % (règle de l'étude 01, reprise telle
  quelle).
- Cache : « tiède » = seconde passe ; « froid » = après lecture complète d'un fichier sans rapport plus
  gros que la RAM (le cache de Windows ne garde pas les deux). Les deux se publient.
- Qualité d'une variante avec perte : pas de seuil arbitraire. On trace KL moyenne contre octets lus
  par jeton pour les quantifications standard de llama.cpp sur le même modèle ; une variante troncons
  gagne si elle passe **sous** cette frontière. Les tâches ne départagent que si les intervalles
  binomiaux ne se recouvrent pas.
- Rendement physique publié avec chaque résultat : jetons/s mesurés ÷ plafond calculé (§ 5).

## 8. Téléchargements à demander à Stone, dans l'ordre

Son accord de principe existe (SOCLE, 2026-10-15) ; l'orchestrateur choisit et note chaque fichier.
Tailles et empreintes SHA-256 lues dans l'API (`telechargements.json`).

1. **gpt-oss-20b, MXFP4** — `ggml-org/gpt-oss-20b-GGUF`, `gpt-oss-20b-MXFP4.gguf`, 12 109 566 624 octets,
   SHA-256 `27cd6c43…5901`, Apache-2.0. *Pourquoi* : même architecture et même format que le 120b, mais
   tient en RAM. On y développe le moteur et l'on compare, jeton pour jeton, la version en mémoire à la
   version en flux.
2. **gpt-oss-120b, MXFP4** — `ggml-org/gpt-oss-120b-GGUF`, `gpt-oss-120b-MXFP4.gguf`, 63 387 346 208
   octets, SHA-256 `582bd40f…622d`, Apache-2.0. *Pourquoi* : 3,6 fois la mémoire utile, 5,1 G actifs,
   poids d'origine (référence sans perte), architecture connue de llama.cpp. C'est **le premier ultra
   lourd**.
3. **Qwen3.8-Flash-Next, UD-Q4_K_XL** — `unsloth/Qwen3.8-Flash-Next-GGUF`, 4 fichiers, 111,33 Go,
   qwen-community-1.0. *Pourquoi* : la table de n-grammes (28,8 Go) et le meilleur plafond utile ; Q4
   plutôt que Q2 pour que la qualité de référence reste proche de l'original. Variante plus légère :
   UD-Q2_K_XL, 3 fichiers, 78,87 Go (plafond doublé, qualité moindre).
4. **DeepSeek-V4-Flash-0731, UD-Q2_K_XL** — `unsloth/DeepSeek-V4-Flash-0731-GGUF`, 3 fichiers,
   96,83 Go, MIT. *Pourquoi* : routage par hachage, experts nés en FP4, 284 G de paramètres.
5. *(Seulement après preuve sur 2)* **Kimi-K2.6, UD-Q2_K_XL** — `unsloth/Kimi-K2.6-GGUF`, 8 fichiers,
   340,48 Go, MIT modifiée. La démonstration à 1 T ; elle occuperait 84 % du disque libre.

Total de 1 + 2 : 75,5 Go ; de 1 à 4 : 283,7 Go sur 404.

## 9. Licences, et leur effet au Canada

Lu dans les fichiers LICENSE des dépôts (empreintes des textes lus : journal de l'étude) ; je ne suis
pas juriste, et ceci n'est pas un avis juridique.

| Licence | Modèles | Ce qui restreint | Pour Stone (recherche personnelle au Canada) |
|---|---|---|---|
| Apache-2.0 | gpt-oss, Qwen3/3.5/3.6/Next, Mixtral, Mistral-Small-4, Mistral-Large-3, Step-3.5, Hy3 | rien (avis et licence à conserver) | libre |
| MIT | DeepSeek R1/V3.1+/V4, GLM-4.5 à 5.1, GLM-5.3-Flash, MiMo, Ling, LongCat | rien | libre |
| MIT modifiée (Kimi K2.x) | Kimi K2, K2-Thinking, K2.6 | afficher « Kimi K2 » au-delà de 100 M d'utilisateurs ou 20 M$/mois | libre |
| kimi-k3 | Kimi K3 | affichage au-delà des mêmes seuils ; accord séparé pour un service de modèle de plus de 20 M$ de revenu sur 12 mois ; usage interne exempté | libre |
| qwen-community-1.0, qwen3.8-max | Qwen3.8-Flash-Next, Qwen3.8-2.4T | affichage au-delà de 100 M / 20 M$ ; licence séparée pour un service de modèle (seuil de 50 M$ pour 3.8-max) ; usage interne exempté | libre |
| glm-5.3 | GLM-5.3 | revue de sécurité de Z.AI pour un service de modèle de plus de 10 G$ de revenu | libre |
| Llama 3.x / 4 Community | Llama 3.3, 3.1 405B, Llama 4 | licence de Meta au-delà de 700 M d'utilisateurs ; « Built with Llama » ; politique d'usage | libre ; aucune exclusion du Canada |
| MiniMax (M2.7 non commerciale ; M3 minimax-community) | MiniMax | M2.7 : usage commercial sur autorisation écrite | recherche personnelle permise |
| Mistral Research License | Mistral-Large-2411 | non commerciale | recherche permise |
| NVIDIA Open Model / OpenMDW-1.1 | Nemotron 3 | conditions propres à NVIDIA (non relues en entier ici) | à relire avant tout usage hors recherche |

Aucune de ces licences n'exclut le Canada ni ne vise un territoire où Stone se trouve. Le projet de loi
fédéral sur l'IA (LIAD, dans C-27) est mort au feuilleton en janvier 2025 (littérature, non revérifié
aujourd'hui) : aucune loi fédérale propre à l'IA ne s'ajoute à ces contrats pour un usage personnel.

## 10. Ce que je crois manquer dans le monde (les trous réels, chiffrés)

1. **Aucune mesure publiée d'une table à recherche servie depuis un NVMe grand public.** L'article
   Engram mesure la DRAM hôte d'un H800 et laisse l'étage SSD à l'état de proposition ; llama.cpp a le
   mécanisme (lecture paresseuse, préchargement de lignes) mais aucun chiffre. Or trois modèles ouverts
   mettent 26 à 45 % de leurs paramètres dans de telles tables. Ce qu'il faut chiffrer : octets lus par
   jeton (attendu ~64 Kio en pages de 4 Kio pour Qwen3.8), succès du cache des n-grammes fréquents, et
   l'éviction des pages d'experts par les pages de table dans le cache de Windows (hypothèse à mesurer).
2. **Aucune donnée de localité du routage à un jeton à la fois, sur texte réel, pour les modèles de 2026**
   (512 experts chez Qwen3.5/3.8 et Ling, 896 chez Kimi K3). C'est le chiffre qui fixe h, donc le débit :
   de 26 % à 60 % de succès, gpt-oss-120b passe de 5,6 à 10,3 jetons/s de plafond (§ 5.4). Le banc de
   § 7 relève les octets lus ; il faut aussi tracer la suite des experts choisis (journal du routeur).
3. **Le routage par hachage de DeepSeek V4 n'est exploité par personne pour précharger.** ~7 % des
   octets d'experts de V4-Flash sont connus une passe complète à l'avance (dès le tirage du jeton).
4. **DeepSeek V4.1-Flash (Engram + CED) n'a pas de base de comparaison locale** : pas d'architecture dans
   llama.cpp au 2026-10-15, pas de GGUF chez unsloth. Une implémentation qui le ferait tourner sur 8 Go
   serait la première ; ses 16 G actifs en décodage le placent, à 2 bits mixtes, à ~10,2 Go par jeton
   (calculé).
5. **Pas de banc standard « hors mémoire »** qui publie octets lus par jeton et rendement physique
   (jetons/s ÷ plafond). Les chiffres de débit publiés pour des modèles sur SSD ne disent ni le disque ni
   le cache. `outils/modeles-base.py` et `modeles_physique.py` en sont une première version.
6. **La compression sans perte des modèles nés en 4 bits** est la seule voie sans perte qui reste sur
   gpt-oss, Kimi K2.6/K3, DeepSeek V4 et MiMo ; les échelles E8M0 seules font 6,3 % des octets d'experts de
   V4-Flash. Le gain réel dépend de l'entropie mesurée par l'étude 03.

## 11. Ce qui pourrait être faux

- **Les deux capacités supposées** (6,5 Go de VRAM, 11 Go de RAM pour des poids) gouvernent h et les
  plafonds. Elles se remplacent par des mesures dès le premier essai.
- **Le calcul n'est pas gratuit.** Le processeur (6 cœurs performants, AVX2, sans AVX-512) ne déquantifie
  peut-être pas du Q2_K à 41,6 Go/s ; si le calcul domine, les plafonds « RAM » sont optimistes.
- **Le NVMe à 7,877 Go/s est un plafond de lien**, pas un débit ; l'étude 01 mesurera le vrai, et les
  lectures d'experts sont des blocs de plusieurs Mo (un expert de gpt-oss-120b : ~4,4 Mo par matrice,
  calculé), ce qui est favorable mais non mesuré.
- **L'hypothèse de routage uniforme** est pessimiste par construction ; elle n'est pas une prévision.
- **La définition des actifs** inclut la tête de sortie et exclut la ligne de plongement et la MTP ;
  d'autres comptes donnent ±0,5 à 1 G.
- **Les miroirs** : Llama 4 lu sur les copies d'unsloth, Llama 3.1 405B sur Hermes-3 (même architecture,
  autres poids). Les cartes et les articles peuvent eux-mêmes se tromper.
- **Les tailles GGUF** : ~~l'expression régulière des niveaux ignore « UD-Q1_0 »~~ corrigé (niveau ajouté,
  tailles relues : UD-Q1_0 de Kimi K3 = 466,4 Go, de Qwen3.8-2.4T = 397,3 Go, aucun des deux ne tient
  dans 404 Go avec le reste). Un niveau inconnu de l'expression régulière reste noté « ? » dans le journal.
- **La validation du juge** porte sur un seul modèle (Qwen3.5-4B) ; MMLU y donne ~38 % au milieu de la
  passe, très en dessous des scores publiés en génération : la mesure par vraisemblance de llama.cpp sans
  gabarit de conversation n'est comparable qu'à elle-même. L'écart entre moteurs (KL 0,0055) est mesuré
  sur un seul modèle, hybride (Gated DeltaNet) ; sur gpt-oss (attention classique) il peut être autre.
- **Les licences** : résumé d'un non-juriste ; NVIDIA et Mistral Research non relues en entier ; le texte
  LICENSE de DeepSeek-V3 et de Llama 3.3 n'était pas lisible à l'adresse essayée (licences prises des
  métadonnées du dépôt).
- **Les modèles « 0731 » et « 0813 »** de DeepSeek sont comparés aux chiffres de l'article d'avril
  (V4-Flash, V4-Pro) ; les révisions ont pu changer l'architecture à la marge (MTP de 19,8 G chez
  V4-Flash-0731 contre 3,4 G chez V4-Flash).

## 12. Sources (consultées le 2026-10-15)

Articles (métadonnées par l'API arXiv, `sources-arxiv.txt`) :

- DeepSeek-V4: Towards Highly Efficient Million-Token Context Intelligence — arXiv 2606.19348, v1
  2026-04-26.
- Conditional Memory via Scalable Lookup (Engram) — arXiv 2601.07372, v1 2026-01-12, v2 2026-07-12.
- DeepSeek-V3 Technical Report — arXiv 2412.19437, 2024-12-27 (v2 2025-02-18).
- DeepSeek-R1 — arXiv 2501.12948, 2025-01-22 (v2 2026-01-04).
- Qwen3 Technical Report — arXiv 2505.09388, 2025-05-14.
- Kimi K2: Open Agentic Intelligence — arXiv 2507.20534, 2025-07-28 (v2 2026-02-03).
- GLM-4.5 — arXiv 2508.06471, 2025-08-08.
- gpt-oss-120b & gpt-oss-20b Model Card — arXiv 2508.10925, 2025-08-08.
- Mixtral of Experts — arXiv 2401.04088, 2024-01-08.
- The Llama 3 Herd of Models — arXiv 2407.21783, 2024-07-31 (v3 2024-11-23).

Dépôts Hugging Face (cartes, config, en-têtes, LICENSE) : les 49 dépôts de `depots.txt`, chacun avec
son empreinte de révision (`sha`) et ses dates dans `inventaire-3.json` ; les 40 dépôts GGUF de
`depots-gguf.txt` (`gguf-tailles.json`). Extraits des cartes : `cartes-revendications.txt`.

Code lu (sans rien copier) : ggml-org/llama.cpp, licence MIT, commit 843e7dc (2026-10-15) —
`src/llama-mmap.cpp`, `src/llama-model-loader.{h,cpp}`, `src/llama-impl.cpp`,
`src/models/qwen4exp.cpp`, `tools/perplexity/perplexity.cpp`. Spécification GGUF : `docs/gguf.md` du
dépôt ggml.

Jeux d'évaluation : wikitext-2-raw (CC BY-SA 3.0) ; HellaSwag (MIT), MMLU (MIT), ARC (CC BY-SA 4.0) et
Winogrande au format de llama.cpp, dépôts `ikawrakow/validation-datasets-for-llama.cpp` (Apache-2.0)
et `ikawrakow/winogrande-eval-for-llama.cpp` ; HellaSwag de `klosax/hellaswag_text_data`.
