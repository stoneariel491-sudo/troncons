# troncons : l'architecture qui fait loi

Décision de l'arbitre, rédigée le 2026-10-15 après lecture complète de `SOCLE.md`, de
`fondations/07-ce-qui-manque.md`, de `decisions/partisan-A.md` et de `decisions/partisan-B.md`,
et des études 01 à 06 là où la décision en dépend. Ce document est la spécification que suivent les
ingénieurs. Il se change par une décision écrite et datée, jamais en silence : une phrase fausse se
barre (~~…~~) et l'on dit ce qui a changé.

Étiquettes du projet : **[mes.]** mesuré sur la machine de Stone, outil et journal commités ;
**[calc.]** calculé par un outil commité ; **[litt.]** littérature, non reproduite ; **[hyp.]**
hypothèse dite ; **[est.]** estimation d'ingénierie, non mesurée. Un chiffre repris garde la source
de l'étude (« [mes. 03] »).

Ce que l'arbitre a fait lui-même (rien sur la carte graphique, qu'un autre agent occupe) :
- **un second chemin des plafonds** (`outils/arbitre/verif_plafonds.py`) qui refait, sans importer
  aucun outil d'un autre, les sept chiffres dont la décision dépend ; les sept tiennent à 1 % et la
  cassure fait tomber exactement celui qu'elle vise ;
- **la mesure F1** (`outils/arbitre/decoupe/`), sur le processeur, avec le codeur rANS réel de
  l'étude 03 et un décodage exact : ce que coûtent, en octets réellement écrits, la découpe base +
  complément contre le flux unique de A, et une variante neuve du flux de A (la table choisie par
  voie) qui supprime le réassemblage. Résultats au § 3.

**État de la mesure dont une partie dépend.** `mesures/gpt-oss.md` (la courbe `h(c)`, ρ et la base
llama.cpp de gpt-oss-120b mesurée en ABBA) n'est pas commité à l'heure où j'écris ; la série 20b de
l'autre agent tournait. Le § 9 dit ce qui en dépend et ce qui n'en dépend pas.

---

## 0. En bref

1. **La décision** (réponse par délégation du 2026-10-15, réversible ; raison : le critère de Stone,
   § 1.1) : on construit **troncons**, un moteur à nous, en **Rust avec des noyaux CUDA** lancés par
   l'API du pilote. Son **premier jalon J1** est l'architecture **A** : gpt-oss-120b (63,4 Go) servi
   **exactement** par la carte, experts codés sans perte de bout en bout, lus du disque à la taille
   d'un expert, avec une fenêtre de mémoire bornée qui ne dépend pas de la taille du modèle. **La
   contribution B avance dès le premier jour, en parallèle et sans moteur** (banc de qualité Q0 sur
   llama.cpp, mesure F1 faite ici) ; **B entre dans le moteur au jalon J2**, si ses portes de
   qualité tiennent. C n'est pas construit.
2. **Pourquoi pas B d'abord, en un chiffre** : une fois les compléments comptés, B1 ne gagne plus
   rien au plafond (**6,16 contre 6,24 jetons/s** pour A, LRU calé) ; son gain est en latence
   (+23 % en série). Le vrai gain de débit de B est B3 (**×1,74**, ×1,78 avec les bits mesurés par F1), au prix de **48,5 %** d'usages
   d'experts servis par la base, pour une KL estimée de 0,05 à 0,12 contre un seuil de 0,0055. Et B
   contient A dans le code : B d'abord, c'est A plus quatre modules, sans un jour gagné sur le premier
   programme qui marche. Chiffres refaits ici par un second chemin (§ 1.3).
3. **Pourquoi pas A seul** : A est un assemblage. Stone demande aussi « une contribution qui n'existe
   pas encore ». Le seul mécanisme neuf de la carte des trous est R1 (B). Il garde donc un lot, un
   format réservé au bit près, des portes datées et des critères de mort.
4. **Le ×1,42 de l'étude 07 est barré** (dans 07 et dans ce document) : il omettait le trafic des
   compléments ; le point d'égalité f* = 0,958 du partisan de A l'omettait aussi et tombe avec lui.
5. **Pourquoi CUDA et pas Vulkan pour J1** (§ 2) : le décodeur est 14,9 % plus rapide sous CUDA
   (80,8 et 82,1 contre 70,2 et 71,6 Go/s, ABBA [mes. 03]) ; le recouvrement copie-calcul (part cachée
   0,98 à 1,01) et la mémoire épinglée (+21 %) n'ont été mesurés que par des flux CUDA [mes. 04] ;
   wgpu n'offre ni import de mémoire hôte ni seconde file, deux choses dont le chemin des octets a
   besoin. Le prix, dit : le programme ne tourne que sur une carte NVIDIA ; les noyaux WGSL mesurés
   restent le second chemin, et un portage Vulkan s'ouvre après J2.
6. **Le format `.trc`** (§ 4) : un fichier autonome par modèle, aligné sur 4 Kio, un **tronçon par
   expert**, des flux rangés par **niveau de raffinement** (tout préfixe de niveau est décodable seul).
   En J1, un seul niveau ; les sortes de flux de B (base, complément) sont spécifiées dès maintenant.
   Codage : le rANS v4 de l'étude 03, avec **la table choisie par voie selon la classe d'échelle du
   bloc** (mesuré ici : même taux que les trois flux de classe de 03, 3,8431 contre 3,8434 bits
   par poids, sans réassemblage ni somme préfixe). Empreintes : SHA-256 du GGUF source, empreinte 64 bits (préfixe
   de SHA-256) de chaque section, de chaque tronçon codé et de chaque expert décodé.
7. **La mesure F1** (§ 3) : la table choisie par voie égale les flux de classe (3,8431 contre 3,8434 bits par
   poids, S2 tient) et entre dans la v1.0 ; la découpe base + complément conditionnée par la classe
   d'échelle coûte **+0,41 %** (S1 tombe de 0,01 point) ; avec un contexte plus riche pour le
   complément (classe du demi-octet voisin, complément faible déjà décodé), **+0,31 %** (S1bis
   tient) : **la v1.1 à deux niveaux devient le format unique de J2**, et A y perd 0,3 % au plus. Le
   complément codé par rANS fait 0,966 fois son empaquetage brut (S3 tient). L'erreur de la base
   (4,2920 %) et celle de la base aimantée (5,913 %) sont retrouvées par un second chemin. Tous les
   flux décodés exactement, toutes les voies sur L.
8. **J1 réussit si** (§ 7, chaque seuil dérivé d'une mesure nommée) : logits du chemin codé
   **identiques au bit** à ceux du chemin brut du même moteur ; le moteur au moins aussi près des
   mathématiques exactes du modèle (référence f64) que llama.cpp ; **RAM de pointe ≤ 1,9 Go** en
   mode A0, égale à 0,5 Mo près entre gpt-oss-20b et 120b ; VRAM sous 8 188 − 909 Mio ; **jetons/s ≥
   0,8 × le plancher en série** recalculé avec le `h` compté par le moteur (repères : 0,99 / 2,15 /
   3,32 jetons/s selon la localité, mode A0) ; puis, au jalon J1+ (préchargement), au-dessus de la
   meilleure base llama.cpp mesurée par la règle de 06 § 7.5.
9. **L'équipe** (§ 6) : cinq lots aux fichiers disjoints (F format et codeur ; E chemin des octets ;
   K noyaux ; R référence, juge et banc Q0 ; O cache, ordonnanceur, moteur), coutures gelées dans ce
   document, chaque lot fini par un témoin, sa cassure et un seuil déclaré. Repli à 3 ou 4
   ingénieurs donné.
10. **L'épreuve indépendante** (§ 8) commence par un geste qui dit si cette spécification est vraie :
    un juge qui ne l'a pas écrite code un décodeur Python **à partir du seul § 4** et doit redonner,
    au bit près, des tronçons tirés au hasard du fichier produit par le lot F.

---

## D'où on part, où on va

**Au départ** : l'étude 07 a posé l'équation du jeton, chiffré trois architectures (A, B, C) sur les
débits mesurés de la machine et recommandé « A d'abord, dans un format qui prépare B ». Les deux
partisans ont plaidé, chacun avec son outil et ses témoins : A comme plancher et juge de B ; B comme
seule contribution de recherche, avec une correction du chiffre de 07 et un banc de qualité sans
moteur.

**Ce que ce document établit** : la décision et ce qu'elle écarte, chiffrés ; la correction du
partisan de B vérifiée par un second chemin ; la mesure F1 qui tranche le désaccord sur le format ;
la langue et les noyaux ; le format au bit près ; les modules et leurs interfaces ; les lots ; les
critères du premier jalon ; l'épreuve indépendante ; ce que le mémoire demandera.

**Ce qui reste** : la mesure de localité (autre agent), puis la construction de J1 par les lots, le
banc Q0, et le jalon J2.

---

## 1. La décision et sa raison

### 1.1 Le critère

Les mots de Stone (SOCLE, 2026-10-15) : « produire et d'implémenter une vrai solution pour prendre un
modele ultra lourd quelcoque d'une ai le faire tourner proprement », et « je ne veux pas que des
recherches déja existante […] si ce qu'on cherche n,existe pas alors tant mieux creer le ». Le
2026-10-09, il a ajouté « je pense qu'on doit avancer » et trouvé le rythme lent.

J'en tire trois exigences, que la décision doit remplir ensemble :
- **E1, une solution qui marche** : un programme qui fait tourner un modèle bien plus gros que la
  mémoire de la machine, proprement (sortie juste, mémoire bornée, vitesse au-dessus de la base) ;
- **E2, une contribution** : un mécanisme ou un assemblage qui n'existe pas encore, prouvé par la
  mesure ;
- **E3, vite un premier programme qui marche**, sans fermer la porte à E2.

### 1.2 La décision

Réponse par délégation du 2026-10-15, réversible. Justification en une ligne : c'est le seul ordre
qui livre E1 par le chemin le plus court (E3) sans retarder d'un jour la mesure qui décide d'E2.

| Jalon | Contenu | Ce qu'il prouve | Porte d'entrée |
|---|---|---|---|
| **J1** | A exact sur gpt-oss-120b : format `.trc` v1.0, lecture IOCP à la taille d'un expert, DMA depuis la mémoire épinglée, décodage rANS sur la carte, cache d'experts en VRAM (LRU), ordonnanceur à la demande, passage avant complet de gpt-oss en CUDA ; modes A0 (aucun cache en RAM) et A (cache tiède en RAM) | E1 (exact, fenêtre bornée) | aucune |
| **J1+** | préchargement (routeur de ℓ+1 sur le résidu de ℓ), SLRU, préremplissage par flux | E1 (vitesse contre la base) | J1 |
| **Q0** (en parallèle dès le premier jour) | qualité de B **sans moteur**, par fichiers statiques jugés par llama.cpp ; frontière des requantifications | la question qui décide d'E2 | la carte libre 2 à 4 h, la trace de routage |
| **J2** | B dans le moteur : format v1.1 à deux niveaux, B1 (gain de latence), B3 (gain de débit, politique λ selon le poids du routeur) | E2 | J1 tient (C3) et Q0 n'a pas tué B |
| J3 (ouvert, non planifié) | disque non chiffré, spéculation si ρ le permet, portage Vulkan | — | décision future |

### 1.3 Pourquoi pas B d'abord (chiffré)

Le partisan de B a montré que `plafonds.py` (07) calcule B1 sans les octets des compléments : sous
LRU, tout défaut entre au cache, donc tout défaut finit par lire son complément. Je l'ai refait par un
chemin indépendant (`verif_plafonds.py`, formules écrites depuis 07 § 1.2 et l'annexe A.1 de
partisan-B.md, aucun import) [calc.] :

| gpt-oss-120b, disque 2,58 Go/s, RAM 11 Go, VRAM 6,5 Go | Plafond (jetons/s) | Série | Part des usages servis par la base | Témoin |
|---|---|---|---|---|
| A, LRU calé | 6,241 | 3,932 | 0 | W1 tient (attendu 6,24) |
| A0, LRU calé | 3,592 | 2,685 | 0 | W2 tient (3,59) |
| A, uniforme | 2,048 | 1,474 | 0 | W3 tient (2,05) |
| ~~B1 de 07, sans compléments, LRU~~ | ~~8,879~~ | ~~5,085~~ | ~~23,4 %~~ | W4 tient (8,88) : le chiffre de 07 est bien reproduit, et il est faux |
| **B1 complété, λ = 0, LRU** | **6,161** | **4,827** | 23,4 % | W5 tient (6,16 et 4,83) |
| **B3, λ = 0, LRU** | **10,886** | 5,583 | **48,5 %** | W6 tient (10,89) |
| B3, λ = 0, uniforme / Belady | 3,327 / 18,037 | 2,217 / 9,115 | 92,1 % / 25,6 % | — |

Cassure (`--casser`, compléments remis à zéro dans B1 complété) : W5 tombe (8,879 au lieu de 6,16),
les six autres tiennent (`verif-plafonds-casse.json`). La correction du partisan de B est donc
juste, et **elle retire à B1 tout gain de débit**.

Ce qui reste à B, et pourquoi cela ne le met pas en premier :
- **B1 est un gain de latence** (+23 % en série) : il paie près du plancher, là où tournent les
  moteurs publiés (18 à 45 % de leur borne [litt. 04]). C'est un raffinement d'un moteur qui marche,
  pas un moteur.
- **B3 est le gain de débit** (×1,74 sur A, LRU), mais il sert 48,5 % des usages d'experts par une
  base à 4,29 % d'erreur relative ; l'ordre de grandeur de sa KL (linéarité de HIGGS, hypothèse du
  partisan de B, § 3.2) est **0,05 à 0,12**, soit **9 à 22 fois** le seuil de 07 (0,0055). Sa
  politique λ rend de l'exactitude au prix du gain : à λ = 0,5, il reste ×1,12.
- **B contient A** (partisan-A.md § 1.1, que le partisan de B ne conteste pas : « le moteur de B
  commence par être A ») : passe avant, lecteur, DMA, décodeur, cache. B d'abord, c'est A, plus un
  codeur base + complément, un décodeur du complément, un automate de cache à cinq états et une
  politique. Le partisan de B l'estime lui-même à +5 à 10 % avant un premier programme exact et +25
  à 35 % avant un premier mode B [est.].
- **La seule partie de B qui n'a pas besoin du moteur, sa qualité, ne l'attend pas** : Q0 (§ 6, lot
  R) la mesure sur llama.cpp par fichiers statiques, en parallèle de J1. C'était l'argument le plus
  fort du partisan de B (« la mesure qui décide de B repoussée derrière un moteur complet ») ; cet
  ordre le désarme.

### 1.4 Pourquoi pas A seul

Le partisan de A le concède (§ 2.2) : « un A seul ferait un bon rapport d'ingénierie, pas un article
de recherche ». E2 exige un mécanisme. B reste donc dans le plan, avec :
- son format réservé **au bit près** dès maintenant (§ 4.10 et § 4.11), pour que J2 ne change ni le
  lecteur, ni le cache, ni l'ordonnanceur ;
- un lot (R) qui mesure sa qualité dès le premier jour ;
- la mesure F1 faite ici, qui fixe ce que coûte sa découpe (§ 3) ;
- des critères de mort déclarés (§ 7.4), repris du partisan de B sans les desserrer.

### 1.5 Pourquoi pas C

Llama-3.3-70B IQ3_XXS lu du disque, vérifié en arbre : plafond **2,50 jetons/s** (série 1,68) avec
l'arbre de SpecExec [litt. 05], contre 6,24 pour A dans le scénario LRU et 2,05 au pire ; il demande
28,3 Go de téléchargement et un moteur de vérification en arbre qui n'existe dans aucun moteur
portable ; Llama 3 se quantifie mal (+76 % de perplexité à 2,07 bits [litt. 02]). Écarté pour ce
cycle ; la spéculation sur un MoE revient en J3 si la trace donne `α > 1 − ρ` atteignable (07 § 1.5).

### 1.6 Ce qui est écarté, chiffré

| Écarté | Le nombre qui l'écarte | Source |
|---|---|---|
| B d'abord | B1 complété 6,16 contre A 6,24 au plafond ; B3 ×1,74 au prix de 48,5 % d'usages par la base, KL estimée 0,05 à 0,12 contre 0,0055 | § 1.3 [calc.] |
| A seul, sans B | E2 non rempli ; R1 est le seul mécanisme neuf de la carte des trous | 07 § 3.2 |
| C | 2,50 contre 6,24 jetons/s ; 28,3 Go à télécharger | 07 § 4.3 [calc.] |
| Route 2 (fournisseur d'experts dans llama.cpp) | graphe statique : une synchronisation après chaque routeur, ordonnancement non maîtrisé, pas de choix de table expert par expert pour B | 07 § 4.1, partisan-B § 6.1 |
| Vulkan (wgpu) pour J1 | décodeur −13 % ; pas d'import de mémoire hôte ; une seule file ; recouvrement non mesuré | § 2 [mes. 03, 04] |
| DirectX 12 par wgpu | q4 à 32 Go/s contre 122 ; ni f16 ni sous-groupes | 01 § 5.3 [mes.] |
| Décoder dans la GEMV (fusion) | 3,7 fois plus lent que le brut, pas plus rapide que deux passes | 03 § 4.5 [mes.] |
| Décoder sur le processeur | 0,075 Go/s par fil | 03 § 4.4 [mes.] |
| Calculer les experts tièdes sur le processeur | la PCIe (58 ms) ne limite pas (disque 157 ms) | 07 § 3.3 [calc.] |
| Noyaux rapides avant noyaux justes | élasticité du plafond nulle tant que le disque limite ; le décodeur peut descendre à 5,6 Go/s | 07 § 1.7, partisan-A § 4.5 [calc.] |
| Fautes de page (mmap) | 0,22 Go/s à 4 Kio contre 2,58 à 4 Mio | 01 [mes.] |
| IoRing au lieu d'IOCP | écart 0 à 5 %, sous le bruit | 01 [mes.] |
| Trois flux de classe réassemblés (format de 03) | même taux que la table par voie (3,8434 contre 3,8431 bits par poids) et un réassemblage en plus (41,6 contre 70 Go/s mesurés pour le décodage seul [mes. 03]) | § 3 [mes.] |
| Base à 1 bit de magnitude | 16,4 % d'erreur, 12 fois le bruit propre du format | 07 [mes.] |
| Sparsité des activations sous vérification | union de 4 jetons : 89,5 % des poids | 05 [mes.] |
| Long contexte en J1 | à 131 072 jetons, le cache KV prendrait 4,8 Go sur 5,5 de cache d'experts | partisan-A § 4.1 [calc.] |

### 1.7 Les corrections que l'arbitre porte

- **07, ×1,42 et ×1,75** (§ 0 point 5, § 3.2 R1, § 4.2, § 4.5) : barrés dans le fichier de 07, avec
  renvoi ici. Le bon chiffre : B1 complété 6,16 (série 4,83) ; B3 (λ = 0) 10,89 à 48,5 % d'usages
  par la base.
- **partisan-A, f* = 0,958** (« B1 bat A dès que plus de 4,2 % des défauts sont servis par la base »,
  § 0 point 5, annexe A.2) : barré ; il supposait, comme 07, des compléments gratuits. Comptés, B1
  ne bat jamais A au plafond (le disque lit base + complément = 3,906 bits contre 3,855) ; il ne le
  bat qu'en série.
- **07, I1 « sous Vulkan »** : la chaîne de J1 sera sous CUDA ; ce qui reste neuf est « sous Windows,
  sur un portable grand public à disque chiffré, octets codés de bout en bout » (§ 2.3).

---

## 2. Le programme : nom, langue, noyaux

### 2.1 Le nom

**troncons** : l'exécutable `troncons.exe`, l'espace de travail Rust `moteur/` à la racine du dépôt,
le format de fichier `.trc`. Le nom vient du projet (un tronçon : la part d'un modèle qu'on lit,
décode, sert et oublie, les « chunks » de Stone).

### 2.2 La langue : Rust, noyaux CUDA

- **Hôte** : Rust 1.98.1, édition 2024 (installé, SOCLE). Raisons : les briques mesurées du projet
  sont en Rust (codeur et décodeur rANS processeur, banc disque IOCP, lecteur GGUF) ; mémoire sûre
  pour un programme qui jongle avec des tampons alignés, des files d'E/S et des pointeurs de carte.
- **Noyaux** : CUDA C++, compilés **à la construction** par `nvcc` 13.1 (`-arch=sm_89`, image
  cubin plus PTX), embarqués dans le binaire (`include_bytes!`), chargés par l'**API du pilote**
  (`nvcuda.dll`, `cuModuleLoadData`, `cuLaunchKernel`) depuis une interface Rust écrite à la main.
  Aucune DLL d'exécution de CUDA n'est livrée : le pilote 591.91 (CUDA 13.1) suffit à l'exécution.
  Pas de cuBLAS (aucune GEMM en J1), pas de NVRTC.
- **Construction** : `build.rs` du crate des noyaux appelle `nvcc` dans l'environnement de
  `vcvars64.bat`, `CUDA_PATH = ~/dev/outils/cuda-13.1.2` (recette éprouvée, SOCLE ;
  `outils/03-entropie/cuda/construire.bat`). Si `nvcc` est absent, la construction échoue avec un
  message qui dit quoi poser.

### 2.3 Pourquoi CUDA plutôt que Vulkan, par les mesures

| Question | Vulkan (wgpu 30) | CUDA 13.1 | Source |
|---|---|---|---|
| Décodeur rANS v4, même flux, ABBA | 70,2 et 71,6 Go/s | **80,8 et 82,1 Go/s** (+14,9 %) | 03 § 4.1 ter [mes.] |
| GEMV 4 bits scalaire en VRAM | 249 Go/s (passe 3) | 231 à 237 Go/s (carte partagée) | 02 § 2.2 et 2.3 [mes.] : à égalité, dans le bruit d'une carte partagée |
| GEMV MXFP4 brute | 209,4 Go/s | non mesurée (seuil de portage : § 6.5, lot K) | 03 § 4.5 [mes.] |
| Recouvrement copie / calcul | non mesuré | part cachée 0,98 à 1,01, VRAM ralentie de 5,6 % | 04 § 5.2 [mes.] |
| Mémoire épinglée | tampon `MAP_READ` du pilote, 12,2 Go/s | `cuMemHostAlloc` ; +21 % sur la paginable | 01 § 4.2, 04 § 5.2 [mes.] |
| Lecture sans tampon directement dans la mémoire que lit la DMA | impossible sans import de mémoire hôte, que wgpu n'expose pas (étape 0a et critère K3 du partisan de A) | mémoire allouée par `cuMemHostAlloc`, alignée sur la page, donnée telle quelle à `ReadFile` | partisan-A § 4.6 ; API |
| Copie et calcul sur deux files | wgpu donne une seule file par périphérique | flux CUDA et moteurs de copie | API |
| Lecture du routeur par le processeur, une fois par couche | `map_async` et attente | événement + mémoire projetée | non mesuré des deux côtés : étape E0 (§ 6.5) |

Le maximum de l'équation du jeton (07 § 1.1) suppose que le disque, la PCIe et la carte travaillent
en même temps. Le seul chemin où ce recouvrement est mesuré sur cette machine est CUDA. Avec une seule
file, la PCIe et la carte s'additionnent : sans effet tant que le disque chiffré limite (157 ms contre
58 + 36), mais une perte dès qu'il ne limite plus (07 § 4.2, disque non chiffré).

**Ce que le choix coûte, chiffré et dit** : la portabilité (une carte NVIDIA est exigée) ; la phrase
« sous Vulkan » de la nouveauté I1 (§ 1.7). **Ce qu'il garde** : les noyaux WGSL mesurés (décodeur
v4, GEMV MXFP4) restent le second chemin des noyaux CUDA (mêmes flux, mêmes octets ; § 6.5) ; le
format `.trc` ne dépend d'aucune API ; un lot « portage Vulkan » est ouvert après J2.

### 2.4 Dépendances (toutes dans le cache cargo de la machine, construction `--offline`)

| Crate | Version | Licence | Où |
|---|---|---|---|
| rayon | 1.12.0 | MIT ou Apache-2.0 | codeur, référence |
| sha2 | 0.10.9 | MIT ou Apache-2.0 | empreintes (SHA-256 et son préfixe de 64 bits) |
| windows-sys | 0.61.2 | MIT ou Apache-2.0 | IOCP, `VirtualAlloc`, PDH, mémoire du processus |
| half | 2.7.1 | MIT ou Apache-2.0 | f16 dans la référence processeur |
| libloading | (cache) | ISC | chargement de `llama.dll` pour le découpage en jetons |
| serde, serde_json | (cache), 1.0.151 | MIT ou Apache-2.0 | journaux |
| anyhow, thiserror | (cache) | MIT ou Apache-2.0 | erreurs |
| llama.dll b11515 | — | MIT (vérifiée par 06) | découpage en jetons seulement, par son API publique ; base de comparaison |

Aucune autre dépendance sans décision écrite. Pas de xxHash : il n'est pas dans le cache, et le
préfixe de SHA-256 (accéléré par les instructions SHA du processeur) suffit à un usage de témoin.

---

## 3. La mesure F1 de l'arbitre : ce que coûte la découpe, en octets réels

### 3.1 La question

Les deux partisans s'opposent sur le format : le partisan de A veut un flux unique en v1 (la découpe
coûte +1,33 % à l'ordre 0, et son décodeur n'est pas mesuré) ; le partisan de B veut la découpe comme
seul format, en pariant que la conditionner par la classe d'échelle rendra l'écart. Ni l'un ni
l'autre ne l'a mesuré avec un codeur réel. Les chiffres ne suffisaient pas : j'ai mesuré.

### 3.2 La méthode

`outils/arbitre/decoupe/` (Rust, processeur seul ; la bibliothèque rANS de l'étude 03 incluse par
chemin, sans copie). Les 12 tenseurs de l'étude 07 (gpt-oss-20b, couches 0, 8, 16, 23 × gate, up,
down ; 3 185 049 600 poids), **expert par expert**, comme le format les rangera (tables par tenseur,
tuiles qui recommencent à chaque matrice d'expert), chaque flux **décodé et comparé octet à octet**.
Comptabilité du format : en-têtes de flux et de tuile, états, mots, alignement, tables, médianes.

Variantes :
- **A_flux** : le format mesuré par 03 (trois flux de codes, un par classe d'échelle, réassemblés) ;
- **A_ctx** : un flux de codes, **la table choisie par voie** selon la classe d'échelle du bloc dont
  la voie produit le mot (le décodeur connaît δ avant les codes ; un bloc = 4 mots). Même entropie ;
  plus de réassemblage, plus de somme préfixe ;
- **B_cond** : base (signe + classe de magnitude, en demi-octet à la place du code) en un flux à
  table par voie ; complément en un flux à 8 symboles par mot, la table choisie **par symbole**
  selon (classe d'échelle, classe de magnitude lue dans la base) ; la classe {6} ne coûte aucun pas ;
- **B_mag** : complément conditionné par la seule classe de magnitude (proposition du partisan de B) ;
- **B_riche** (ajoutée après la première passe, qui donnait +0,41 % sur les codes ; seuil identique,
  déclaré avant la seconde) : le contexte du complément ajoute la classe du demi-octet voisin du même
  octet et, pour le demi-octet fort, le complément faible déjà décodé par la même voie ;
- **brut** : le complément empaqueté sans entropie (1 bit, trits par 5 dans un octet, rien).

Seuils déclarés avant le lancement (en tête de l'outil) : **S1** la découpe devient le format unique
si elle coûte ≤ 1,004 × A_ctx (0,40 % = le coût d'en-tête d'un flux de plus [mes. 03]) ; **S2**
A_ctx remplace A_flux s'il coûte ≤ A_flux ; **S3** le complément est codé par rANS s'il fait ≤ 0,99 ×
le brut ; **S4** l'erreur de la base retrouve celle de 07 (0,042919745) à 10⁻⁶ relatif. Témoins :
décodage exact de tous les flux, toutes les voies finissent sur L ; identité de la chaîne par tenseur
à 10⁻⁹. Cassure : le décodeur du complément lit une table où deux fréquences sont échangées.

Conditions : priorité de processus « inactive », 2 fils, pendant la série ABBA de l'autre agent sur
gpt-oss-20b (heures de début et de fin dans le journal, pour qu'il puisse écarter une passe
recouverte) ; 1,7 Go lus du fichier qu'il utilisait.

### 3.3 Résultats

Journaux : `decisions/journaux/arbitre/decoupe-gptoss20b-passe1.json` (passe 1, outil avant l'ajout
de B_riche) et `decoupe-gptoss20b.json` (passe 2, 12:12 à 12:21 ; les variantes communes aux deux
passes rendent exactement les mêmes octets, témoin de reproductibilité) ; cassure :
`decoupe-gptoss20b-casse.json` ; CSV : `csv/f1-par-tenseur.csv`, `csv/f1-totaux.csv`.

Bits par poids, 12 tenseurs, échelles (δ 0,0347), médianes (0,0028) et tables comprises [mes.] :

| Variante | Total | Codes ou base | Complément | Rapport à A_ctx | Exact |
|---|---|---|---|---|---|
| A_flux (format de 03) | 3,8434 | 3,8059 | — | 1,00008 | oui |
| **A_ctx (table par voie)** | **3,8431** | 3,8056 | — | 1 | oui |
| B_cond (complément selon κ et la classe) | 3,8591 | 2,6066 | 1,2149 | 1,00414 | oui |
| B_mag (complément selon la classe seule) | 3,8733 | 2,6066 | 1,2291 | 1,00785 | oui |
| **B_riche** | **3,8550** | 2,6066 | **1,2107** | **1,00308** | oui |
| complément brut (sans entropie) | — | — | 1,2527 | — | — |

- **Niveau 0 de B** (base + δ + médianes) : **2,6441** bits par poids, contre 2,684 dans le calcul de
  07 (qui partait de H(base) à l'ordre 0, sans la classe d'échelle). Rapporté au 120b : 2,652 bits.
- **Seuils** : S1 (B_cond ≤ 1,004) **tombe** (1,00414) ; S1bis (B_riche ≤ 1,004, déclaré avant la
  passe 2) **tient** (1,00308) ; S2 **tient** ; S3 **tient** (B_riche : 1,2107 / 1,2527 = 0,966) ;
  S4 **tient** (0,042919745125 contre 0,042919745124980 publié par 07).
- **Témoins** : tous les flux décodés et comparés octet à octet, 0 voie hors de L ; identité de la
  chaîne à 8,9·10⁻¹⁶. Cassure (table du complément faussée) : sur le premier tenseur, B_cond devient inexact et 130 047 voies finissent hors de L, tandis que A_flux, A_ctx, B_mag et B_riche restent exacts : le témoin tombe là où il doit, et seulement là.
- **D'où vient le reste de l'écart (0,31 %)** : les en-têtes d'un flux de plus par matrice (≈ 0,4 %
  de tuile sur le seul complément, soit ≈ 0,13 % du total) et la dépendance entre demi-octets que
  l'alphabet octet de A capte et que le complément, décodé symbole par symbole, ne capte qu'en partie.
- **Erreur de la base, par tenseur** (`csv/f1-par-tenseur.csv`) : 4,05 à 4,80 % avec les centres
  communs ; des centres propres à chaque tenseur ne gagnent que 0,00 à 0,06 point (4,00 à 4,74 %) ;
  base aimantée sur E2M1 : 5,57 à 7,12 % (5,913 % en tout, le chiffre du partisan de B).
- **Tailles de tronçon** (20b, alignées sur 4 096, en-têtes compris) : niveau unique de A
  11 990 368 o en moyenne (11 837 440 à 12 144 640) ; B : niveau 0, 8 261 120 o, niveau 1,
  3 780 864 o (B_cond ; B_riche ≈ 0,35 % de moins).
- **Ce que F1 change aux plafonds de B** (`verif-plafonds.json`, section `avec_F1`, bits de F1
  rapportés au 120b) [calc.] : B1 complété **6,22** jetons/s (série 4,87) contre 6,24 pour A ; B3
  (λ = 0) **11,10** (×1,78), toujours à 48,5 % d'usages servis par la base (LRU calé).

### 3.4 Ce que F1 décide

1. **v1.0 (J1) : CODES_CTX** (table par voie). Même taux que les flux de classe, un noyau plus
   simple (le décodeur v4 dont seule l'adresse de la LUT change par voie) et aucun réassemblage. La
   sorte 0x05 (flux de classe) reste réservée comme repli si le noyau à table par voie manque son
   seuil sur la carte (K1, § 6.5).
2. **v1.1 (J2) : deux niveaux, BASE_CTX et COMPL_CTX à contexte riche, format unique.** A lit les deux
   niveaux d'une seule requête et paie 0,31 % d'octets, sous le bruit de la lecture (10 %) et sous le
   seuil déclaré ; il n'y aura pas deux fichiers par modèle. Le passage de v1.0 à v1.1 demande de
   recoder le fichier une fois (de l'ordre de 47 minutes de processeur, partisan-A § 3.3 [mes. 03]).
3. **Pourquoi J1 ne prend pas déjà la v1.1**, alors qu'elle ne coûte que 0,31 % : son décodeur du
   complément (table par symbole, sauts) n'existe que sur le processeur ; le mettre sur le chemin
   critique du premier programme serait contraire à E3. Le partisan de A avait raison sur l'ordre, le
   partisan de B sur le format final.
4. **Le complément est codé par rANS** (S3) ; l'empaquetage brut n'est pas spécifié.

---

## 4. Le format de fichier `.trc`, au bit près

### 4.1 Principes

1. **Un fichier autonome par modèle**, écrit une fois depuis le GGUF d'origine par `trc-codeur`. Il
   contient tout ce que le moteur lit : métadonnées, tenseurs toujours lus (copiés tels quels), tables
   entropiques, répertoire, tronçons. Un fichier compagnon `<nom>.vocab.gguf` (§ 4.13) porte le
   vocabulaire pour `llama.dll`. Le GGUF d'origine peut alors être effacé sans rien perdre (ce n'est
   pas fait sans Stone). Raison (réponse par délégation, réversible) : un instrument général
   (« un modele ultra lourd quelcoque ») a un seul artefact par modèle ; le coût est de 2,3 Go de
   disque (les toujours-lus et l'enchâssement recopiés).
2. **Petit-boutiste** partout ; chaînes en UTF-8 ; tailles en octets.
3. **Alignement de 4 096 octets** pour toute section et tout ce que lit une lecture sans tampon
   (`FILE_FLAG_NO_BUFFERING` exige décalage, longueur et adresse multiples du secteur ; 4 096 couvre
   le NVMe de la machine).
4. **Un tronçon = un expert** (ses trois matrices et leurs biais), d'un seul tenant : un défaut coûte
   une requête. Le gain de débit d'une lecture de 12 Mio sur trois de 4,2 Mio (+9 %) est sous le seuil
   de décision (20 %) : le choix est fait pour la simplicité (une requête, une complétion, une
   empreinte, un emplacement), pas pour la vitesse (partisan-A § 4.3).
5. **Niveaux de raffinement** : un tronçon est la suite de ses parties de niveau 0, 1, … ; chaque
   partie est alignée sur 4 096 ; tout préfixe qui s'arrête à la fin d'une partie se décode seul. Le
   lecteur, le cache et l'ordonnanceur ne connaissent que « lire jusqu'à la fin du niveau j ».
6. **Rien ne se devine** : toute structure porte sa taille, son nombre d'entrées et son empreinte ;
   un lecteur refuse une version majeure, une sorte de flux ou un drapeau inconnus.

### 4.2 Disposition générale

```
 fichier gpt-oss-120b.trc                                         décalage        longueur (120b)
 ┌──────────────────────────────────────────────────────────┐
 │ EN-TÊTE FIXE                                               │ 0               4 096
 ├──────────────────────────────────────────────────────────┤
 │ MÉTA : les paires clé-valeur du GGUF, recopiées            │ 4 096           ≈ 13 Mo (vocabulaire compris)
 ├──────────────────────────────────────────────────────────┤
 │ RÉSIDENTS : table + données des tenseurs toujours lus      │ aligné 4 Kio    ≈ 2,301 Go (A 1,686 + enchâssement 0,615)
 ├──────────────────────────────────────────────────────────┤
 │ TABLES : fréquences rANS (et centres de B en v1.1)         │ aligné 4 Kio    ≈ 0,2 Mo (v1.0)
 ├──────────────────────────────────────────────────────────┤
 │ RÉPERTOIRE : une entrée de 64 o par (couche, expert)       │ aligné 4 Kio    4 608 × 64 = 294 912 o + 8
 ├──────────────────────────────────────────────────────────┤
 │ TRONÇONS, dans l'ordre (couche, expert)                    │ aligné 4 Kio    4 608 × ≈ 11,99 Mo
 └──────────────────────────────────────────────────────────┘
```

### 4.3 L'en-tête fixe (4 096 octets)

| Décalage | Taille | Type | Champ | Valeur (gpt-oss-120b, v1.0) |
|---|---|---|---|---|
| 0 | 8 | u8[8] | magie | `TRONCONS` (54 52 4F 4E 43 4F 4E 53) |
| 8 | 2 | u16 | version majeure | 1 |
| 10 | 2 | u16 | version mineure | 0 (J1) ; 1 (J2, deux niveaux) |
| 12 | 4 | u32 | drapeaux | bit 0 = 1 (tronçons alignés sur 4 096) ; bit 1 : au moins deux niveaux ; bit 2 : fichier **brut** (flux non codés, chemin de référence du témoin C3) ; bits 3 à 31 : 0 |
| 16 | 4 | u32 | alignement | 4 096 |
| 20 | 4 | u32 | taille de l'en-tête | 4 096 |
| 24 | 8 | u64 | taille du fichier `.trc` | (vérifiée à l'ouverture : un fichier tronqué est refusé) |
| 32 | 32 | u8[32] | SHA-256 du GGUF source | celle de `telechargements.json` |
| 64 | 8 | u64 | taille du GGUF source | 63 387 346 208 |
| 72 | 2 | u16 | L, couches | 36 |
| 74 | 2 | u16 | E, experts par couche | 128 |
| 76 | 2 | u16 | k, experts actifs | 4 |
| 78 | 2 | u16 | matrices par expert | 3 (0 = gate, 1 = up, 2 = down) |
| 80 | 16 | u32[4] | lignes de la matrice j | 2 880, 2 880, 2 880, 0 |
| 96 | 16 | u32[4] | colonnes de la matrice j | 2 880, 2 880, 2 880, 0 |
| 112 | 4 | u32 | poids par bloc | 32 |
| 116 | 4 | u32 | octets par bloc d'origine | 17 |
| 120 | 1 | u8 | type ggml des experts | 39 (MXFP4) |
| 121 | 1 | u8 | nombre de niveaux | 1 (v1.0) ; 2 (v1.1) |
| 122 | 1 | u8 | classes d'échelle | 3 |
| 123 | 1 | u8 | réservé | 0 |
| 124 | 8 | u8[8] | partition des magnitudes : classe de la magnitude m = code & 7 | v1.0 : 0 ×8 (inutilisée) ; v1.1 : 0 0 1 1 1 2 2 3 |
| 132 | 4 | u32 | réservé | 0 |
| 136 | 128 | (u64, u64)[8] | sections : (décalage, longueur) ; 0 MÉTA, 1 RÉSIDENTS, 2 TABLES, 3 RÉPERTOIRE, 4 TRONÇONS, 5 à 7 réservées | décalages multiples de 4 096 ; réservées à (0, 0) |
| 264 | 3 824 | — | réservé | zéros (vérifiés à la lecture) |
| 4 088 | 8 | u64 | empreinte64 des octets [0, 4 088) | § 4.12 |

### 4.4 Section MÉTA

```
u64  n_paires
puis n_paires paires, chacune exactement au format GGUF v3 :
     u64 longueur de la clé, octets de la clé, u32 type, valeur
```
Les paires du GGUF sont recopiées octet pour octet, dans leur ordre ; le codeur ajoute à la fin
`troncons.codeur.version` (chaîne), `troncons.codeur.date` (chaîne AAAA-MM-JJ) et
`troncons.source.nom` (chaîne, nom du fichier source). La section se termine par l'empreinte64 de
tout ce qui précède (8 octets), puis des zéros jusqu'à 4 096. Le moteur y lit les hyperparamètres
(`gpt-oss.block_count`, `…embedding_length`, `…attention.head_count` = 64, `…head_count_kv` = 8,
`…key_length` = 64, `…rope.freq_base` = 150 000, `…rope.scaling.*` (YaRN, facteur 32, contexte
d'origine 4 096, β rapide 32, β lent 1), `…attention.sliding_window` = 128,
`…layer_norm_rms_epsilon`, `…expert_count`, `…expert_used_count`), relevés sur le fichier de la
machine le 2026-10-15.

### 4.5 Section RÉSIDENTS

```
u32  n_tenseurs                (120b : 471 = 687 − 36 × 6 ; 20b : 315)
u32  réservé (0)
n_tenseurs entrées de 128 o :
  0   u8[64]  nom, UTF-8, complété de zéros (nom GGUF, ex. « blk.0.attn_q.weight »)
  64  u32     type ggml (0 F32, 8 Q8_0, …)
  68  u32     n_dims
  72  u64[4]  ne[0..4] (1 au-delà de n_dims)
  104 u64     décalage des données, depuis le début de la zone de données (multiple de 256)
  112 u64     octets
  120 u64     empreinte64 des octets
zéros jusqu'à un multiple de 4 096 depuis le début de la section : début de la zone de données
zone de données : chaque tenseur recopié tel quel du GGUF (disposition ggml), aligné sur 256
u64  empreinte64 de la table (les 8 + 128 · n premiers octets), après la zone de données
```
Tenseurs résidents : tous ceux du GGUF sauf `blk.*.ffn_{gate,up,down}_exps.{weight,bias}`. Pour
gpt-oss-120b : par couche `attn_norm`, `attn_q/k/v` (+ biais), `attn_output` (+ biais),
`attn_sinks`, `post_attention_norm`, `ffn_gate_inp` (routeur F32, 2 880 × 128, + biais) ; et
`token_embd` (Q8_0, 0,615 Go), `output_norm`, `output` (Q8_0, 0,615 Go). `token_embd` n'est
**jamais** monté en VRAM : le moteur en lit une ligne par jeton (3 060 o dans une lecture alignée de
8 Kio), depuis la RAM s'il l'y garde (`--enchassement-en-ram`), depuis le disque sinon (mode A0).

### 4.6 Section TABLES

```
u32  n_enregistrements
u32  réservé (0)
enregistrements, à la suite :
  0  u16  couche
  2  u8   matrice (0, 1, 2)
  3  u8   sorte du flux qu'elle sert (§ 4.10)
  4  u8   contexte
  5  u8   type de charge : 1 = 16 fréquences u16 (32 o) ; 2 = 256 fréquences u16 (512 o) ;
          3 = 4 centres f32 (16 o)
  6  u16  réservé (0)
  8  charge
u64  empreinte64 de tout ce qui précède dans la section
```
Une fréquence est un entier de 0 à 4 096 ; la somme des fréquences d'une table vaut exactement
4 096 ; 0 marque un symbole absent. Les tables sont **par (couche, matrice, sorte, contexte)**,
communes à tous les experts de la couche (une table par tenseur, comme en 03). Le moteur les monte en
VRAM au démarrage sous forme de LUT de 4 096 mots (§ 4.9) : 36 × 3 × 4 × 16 Kio = 6,9 Mo pour le 120b
en v1.0.

Enregistrements de la v1.0, pour chaque (couche, matrice) : DELTA contexte 0 (charge 2) ; CODES_CTX
contextes 0, 1, 2 (charge 2). La v1.1 ajoute : BASE_CTX contextes 0, 1, 2 (charge 2) ; COMPL_CTX,
un enregistrement par contexte utile (charge 1, § 4.9.3) ; CENTRES contexte 0 (charge 3 : les 4
valeurs de reconstruction de la base, en unités E2M1, centres de gravité du tenseur pondérés par le
carré de l'échelle).

### 4.7 Section RÉPERTOIRE

L · E entrées de 64 octets, dans l'ordre (couche, expert), puis l'empreinte64 de la section.

| Décalage | Type | Champ |
|---|---|---|
| 0 | u64 | décalage absolu du tronçon dans le fichier (multiple de 4 096) |
| 8 | u32 | longueur de la partie de niveau 0 (multiple de 4 096) |
| 12 | u32 | longueur de la partie de niveau 1 (multiple de 4 096 ; 0 en v1.0) |
| 16 | u32 | octets utiles du niveau 0 (avant bourrage) |
| 20 | u32 | octets utiles du niveau 1 |
| 24 | u64 | empreinte64 de l'expert **d'origine** (§ 4.12) |
| 32 | u64 | empreinte64 des octets utiles du niveau 0 |
| 40 | u64 | empreinte64 des octets utiles du niveau 1 (0 si absent) |
| 48 | u16 | couche |
| 50 | u16 | expert |
| 52 | u32 | réservé (0) |
| 56 | u64 | réservé (0) |

La partie de niveau 1 suit immédiatement celle de niveau 0 : le mode exact lit les deux en une seule
requête (`longueur0 + longueur1`), le mode B lit la première au défaut.

### 4.8 Une partie de tronçon

```
 ┌─ en-tête de partie, 64 o ────────────────────────────────────────────────────────────────┐
 │ 0  u32 magie : 0x30435254 (« TRC0 ») au niveau 0, 0x31435254 (« TRC1 ») au niveau 1       │
 │ 4  u16 couche   6 u16 expert   8 u8 niveau   9 u8 n_matrices (3)   10 u16 n_flux           │
 │ 12 u32 octets utiles de la partie (en-tête compris)   16..63 réservé (zéros)              │
 ├─ table des flux, n_flux × 16 o ─────────────────────────────────────────────────────────────┤
 │ 0 u8 sorte   1 u8 matrice   2 u8 contexte fixe (0xFF : aucun)   3 u8 réservé               │
 │ 4 u32 décalage du flux depuis le début de la partie (multiple de 16)                        │
 │ 8 u32 longueur du flux (octets)   12 u32 octets produits par son décodage                   │
 ├─ flux, chacun aligné sur 16 ────────────────────────────────────────────────────────────────┤
 │ v1.0, niveau 0, pour j = 0, 1, 2 : MEDIANES_j, BIAIS_j, DELTA_j, CODES_CTX_j (12 flux)     │
 │ v1.1, niveau 0 : MEDIANES_j, BIAIS_j, DELTA_j, BASE_CTX_j (12 flux)                         │
 │ v1.1, niveau 1 : COMPL_CTX_j (3 flux)                                                       │
 │ fichier brut (drapeau bit 2) : MEDIANES_j inutilisées absentes ; ECHELLES_BRUTES_j,         │
 │ CODES_BRUTS_j, BIAIS_j (9 flux)                                                             │
 └─ zéros jusqu'à un multiple de 4 096 ────────────────────────────────────────────────────────┘
```

### 4.9 Le flux rANS (v4 de l'étude 03, étendu aux contextes)

#### 4.9.1 Sérialisation

```
 0   u32  octets produits P (multiple de 128 ; bourrage de zéros au codage si nécessaire)
 4   u16  macro-pas par tuile N (256)
 6   u8   géométrie : 1 = octet, 4 sous-pas par mot (v4) ; 2 = demi-octet, 8 sous-pas par mot (v1)
 7   u8   réservé (0)
 8   u32  n_tuiles T = ⌈(P / 128) / N⌉
 12  u32  n_mots W (mots de 16 bits du flux partagé)
 16  u32  début[T] : indice, dans mots[], du premier mot de chaque tuile
     u32  états[32 · T] : état initial de chaque voie de chaque tuile
     u16  mots[W]
     zéros jusqu'à un multiple de 16
```

#### 4.9.2 Le décodage (normatif)

Constantes : probabilités sur 12 bits (M = 4 096), état x sur 32 bits, borne basse L = 2¹⁶, mots de
16 bits. Une tuile t couvre les macro-pas `t·N … min((t+1)·N, P/128) − 1`. La voie l (0 à 31) du
macro-pas m produit le **mot de sortie de 32 bits d'indice w = m · 32 + l** (128 octets contigus par
macro-pas). Ses sous-pas k = 0, 1, … produisent, du poids faible au poids fort, l'octet k (géométrie
1, k < 4) ou le demi-octet k (géométrie 2, k < 8) de ce mot.

LUT d'une table (fréquences f[s], cumul c[s] = Σ_{u<s} f[u]) : pour chaque fente
`i ∈ [c[s], c[s] + f[s])`,
- géométrie 1 : `lut[i] = s | ((f[s] − 1) << 8) | ((i − c[s]) << 20)` ;
- géométrie 2 : `lut[i] = s | (f[s] << 4) | ((i − c[s]) << 17)`.

Pour chaque tuile, `p ← début[t]` ; `x[l] ← états[32 t + l]` ; pour chaque macro-pas, pour chaque
sous-pas k, **pour l = 0 à 31 dans l'ordre** :
```
 si le symbole de (w, k) est sauté (§ 4.9.3) : sortie 0, rien d'autre
 sinon :
   e   ← lut_ctx[x & 4095]                     (table du contexte de ce symbole)
   s   ← e & 0xFF          | e & 0xF            (géométrie 1 | 2)
   f   ← ((e >> 8) & 0xFFF) + 1 | (e >> 4) & 0x1FFF
   b   ← e >> 20           | e >> 17
   y   ← f · (x >> 12) + b
   si y < L : x ← (y << 16) | mots[p] ; p ← p + 1      sinon : x ← y
   écrire s
```
Fin de tuile : **chaque voie doit finir sur x = L** (contrôle gratuit du flux et de l'état ; il ne
garde pas la table : 03 § 3.3, d'où l'empreinte des tables au chargement). Le codeur parcourt les
symboles dans l'ordre exactement inverse (macro-pas, sous-pas, voies décroissants), émet
`x mod 2¹⁶` puis `x ← ⌊x / 2¹⁶⌋` si `x ≥ f · 2²⁰`, puis `x ← ⌊x/f⌋ · 4 096 + (x mod f) + c[s]`,
part de x = L sur chaque voie, et renverse sa pile de mots. (Format démontré exact par deux
décodeurs en deux langages, 03 § 4.1 ter [mes.].)

#### 4.9.3 Les contextes

Notation pour une matrice de R lignes et B = C/32 blocs par ligne : bloc `β = r · B + b`, δ[β] l'écart
d'échelle (§ 4.11), et la **classe d'échelle** `κ(β) = 0 si δ[β] < 128, 1 si δ[β] = 128, 2 si
δ[β] > 128` (l'échelle sous, à, au-dessus de la médiane de sa ligne).

| Sorte | Géométrie | Contexte du symbole | Sauts |
|---|---|---|---|
| DELTA | 1 | 0 (une table) | aucun |
| CODES_CTX, BASE_CTX | 1 | **par voie** : le mot w appartient au bloc ⌊w/4⌋ (16 octets = 4 mots) ; contexte = κ(⌊w/4⌋) | aucun |
| COMPL_CTX | 2 | **par symbole** : le demi-octet n (octet ⌊n/2⌋, faible si n pair) appartient au bloc ⌊n/32⌋ ; avec g(n) la classe de magnitude lue dans la base décodée (3 bits bas du demi-octet de base), contexte = `((κ(⌊n/32⌋) · 4 + g(n)) · 4 + g(n xor 1)) · 4 + (n impair ? 1 + c(n − 1) : 0)`, où
c(n − 1) est le complément du demi-octet faible du même octet, décodé par la même voie au sous-pas
précédent (variante B_riche de F1 ; au plus 3 · 4 · 4 · 4 = 192 contextes, seules les tables des
contextes rencontrés sont stockées) | si la classe g(n) n'a qu'une magnitude (classe {6}) : aucun pas, symbole 0 |

Le décodeur décode toujours DELTA avant CODES_CTX ou BASE_CTX (il lui faut κ), et BASE_CTX avant
COMPL_CTX (il lui faut g).

### 4.10 Les sortes de flux

| Code | Sorte | Contenu, octets produits pour une matrice R × C | Niveau |
|---|---|---|---|
| 0x01 | MEDIANES | brut : R octets, la médiane E8M0 de chaque ligne (`tri[B/2]` des B échelles, tri croissant) | 0 |
| 0x02 | BIAIS | brut : R × f32, le biais de la matrice pour cet expert | 0 |
| 0x03 | DELTA | rANS, géométrie 1 : R · B octets, `δ = (e − médiane + 128) mod 256` | 0 |
| 0x04 | CODES_CTX | rANS, géométrie 1, table par voie : R · B · 16 octets, les `qs` des blocs MXFP4 dans l'ordre β | 0 (v1.0) |
| 0x05 | (réservé) | trois flux de classe réassemblés (format de 03) : non produit, non lu | — |
| 0x06 | CODES_BRUTS | brut : R · B · 16 octets (fichier brut seulement) | 0 |
| 0x07 | ECHELLES_BRUTES | brut : R · B octets E8M0 (fichier brut seulement) | 0 |
| 0x10 | BASE_CTX | rANS, géométrie 1, table par voie : R · B · 16 octets ; chaque demi-octet = `(code & 8) \| classe(code & 7)` | 0 (v1.1) |
| 0x11 | COMPL_CTX | rANS, géométrie 2, table par symbole : R · B · 32 symboles (P = R · B · 16 octets de demi-octets) ; symbole = rang de la magnitude dans sa classe (ordre croissant) | 1 (v1.1) |
| 0x12 | CENTRES | (sorte de table seulement : les 4 valeurs de reconstruction de la base) | — |

### 4.11 La reconstruction exacte d'un expert (normative)

Pour chaque matrice j (R lignes, C colonnes, B = C/32) :
1. lire MEDIANES_j → `méd[r]` ; BIAIS_j → `biais[r]` ;
2. décoder DELTA_j → `δ[β]` ; `e[β] = (méd[r] + δ[β] − 128) mod 256` ; `κ(β)` ;
3. niveau 0 de la v1.0 : décoder CODES_CTX_j (table par voie κ) → `qs[16 β … 16 β + 15]` ;
   v1.1 : décoder BASE_CTX_j → `base` ; en mode exact, décoder COMPL_CTX_j (contexte du § 4.9.3) →
   `c[n]`, puis `code(n) = (base(n) & 8) | membre[classe(base(n) & 7)][c[n]]`, où `membre[k]` liste
   les magnitudes de la classe k en ordre croissant ; en mode base, le demi-octet de base est servi
   tel quel avec la table de valeurs des centres (§ 5.6) ;
4. écrire l'emplacement de la carte (disposition SoA, § 5.6) : codes, échelles, biais.

L'expert d'origine, au sens des empreintes, est la suite, pour j = 0, 1, 2, des R · B blocs MXFP4 de
17 octets `[e[β], qs[16 β … 16 β + 15]]` (ordre β, la disposition exacte du GGUF), puis, pour
j = 0, 1, 2, des R biais f32. **Équivalence au GGUF** (témoin C1) : le bloc β de l'expert x de la
matrice j se trouve dans le GGUF au décalage `(x · R + r) · B + b` blocs du tenseur
`blk.ℓ.ffn_{gate,up,down}_exps.weight`.

### 4.12 Les empreintes

- **SHA-256** du GGUF source (32 octets, en-tête).
- **empreinte64(octets)** = les 8 premiers octets de SHA-256(octets), lus comme un u64
  petit-boutiste. Usages : en-tête (sur [0, 4 088)), fin de MÉTA, de RÉSIDENTS (table), de TABLES, de
  RÉPERTOIRE ; chaque tenseur résident ; chaque partie de tronçon (octets utiles) ; chaque expert
  d'origine.
- **À l'ouverture**, le moteur vérifie l'en-tête, les tables, le répertoire et la taille du fichier
  (coût : quelques Mo hachés). **En production**, chaque tuile décodée vérifie le retour des voies à
  L ; une voie hors de L est une erreur fatale nommée (couche, expert, matrice, tuile). **En mode
  témoin** (`--temoin`), chaque expert décodé est recopié vers l'hôte, remis dans la disposition
  d'origine et comparé à son empreinte64.

### 4.13 Le compagnon `<nom>.vocab.gguf`

Un GGUF v3 valide : magie, version 3, `n_tenseurs = 0`, toutes les paires clé-valeur du source,
aucune donnée. `llama.dll` le charge avec `vocab_only = true`. Témoin (lot R) : les identifiants de
jetons du corpus du juge sont identiques par le compagnon et par le GGUF d'origine.

### 4.14 Les tailles

[calc. sur mes. F1] Tronçon de niveau unique (v1.0) : **11 990 368 o en moyenne** sur les 384
matrices-experts mesurées du 20b (11 837 440 à 12 144 640), contre 13 253 760 o à l'origine
(rapport 1,105). Le taux du 120b (1,1026 [mes. 03]) étant à 0,3 % de celui du 20b, le tronçon du 120b
sera de l'ordre de 12,0 Mo ; la taille exacte est celle que le codeur écrit dans le répertoire.

| | gpt-oss-20b | gpt-oss-120b |
|---|---|---|
| Source GGUF | 12,11 Go | 63,39 Go |
| Résidents (A + enchâssement) | 1,917 Go | 2,301 Go |
| Tronçons v1.0 | 768 × 11,99 Mo = 9,21 Go | 4 608 × ≈ 12,0 Mo ≈ 55,3 à 55,4 Go |
| **Fichier `.trc` v1.0** | **≈ 11,1 Go** | **≈ 57,6 à 57,7 Go** |
| Fichier `.trc` v1.1 (+0,31 % sur les tronçons) | ≈ 11,2 Go | ≈ 57,8 à 57,9 Go |
| Plus grand tronçon (tampon d'arrivée) | 12 144 640 o | à relever par le codeur |

### 4.15 Versions

- **1.0** (J1) : un niveau, CODES_CTX. **1.1** (J2) : deux niveaux, BASE_CTX et COMPL_CTX.
  **1.2** (lot A de la construction, 2026-10-17) : le codon synonyme du zéro (§ 4.16).
- Un lecteur 1.x lit toute version 1.y ≤ la sienne ; il refuse 2.x, une sorte inconnue, un drapeau
  inconnu.
- Toute modification du format passe par une décision écrite dans ce document (§ 6.3, couture F).

### 4.16 La version 1.2 : le codon synonyme du zéro (décision du lot A, 2026-10-17)

Source : genome/05-synthese.md §§ 4.1 à 4.6 (le cahier), réduit ici à ce qui tient sans risque ;
mesures et preuve : genome/06-codon-v1-2.md.

**Ce qui change, et rien d'autre** :
- en-tête, version mineure (décalage 10) = **2** ; drapeaux (décalage 12) : **bit 3 CANONIQUE** =
  aucun flux de codes ne contient le demi-octet 8, et l'expert décodé est l'expert canonique.
  Refusé si la version mineure est < 2, sur un fichier brut (bit 2 : le chemin de référence garde
  les octets du GGUF), sur un fichier à deux niveaux (la v1.2 ne définit pas la forme canonique de
  BASE_CTX ni de COMPL_CTX) ;
- RÉPERTOIRE (§ 4.7) : le champ réservé de 8 octets au décalage 56 devient **`empreinte_canonique`**
  (u64), l'empreinte64 de l'expert canonique : la suite d'octets de l'expert d'origine (§ 4.11), où
  chaque demi-octet 8 des `qs` est remplacé par 0. Vaut 0 sans le bit 3 (refusé sinon).
  `empreinte_origine` (décalage 24) reste celle des octets du GGUF : la provenance ne se perd pas ;
- TABLES (§ 4.6) : inchangées en forme (DELTA et CODES_CTX × 3, charge 2) ; construites sur les
  codes canoniques. **Invariant vérifié à l'ouverture** sur un fichier canonique : toute table
  CODES_CTX donne la fréquence 0 aux 31 octets qui portent un demi-octet 8 (un flux ne peut alors
  produire aucun 8, ni sur le processeur ni sur la carte, qui montent les mêmes tables) ;
- les flux, leur sérialisation, le décodage (§ 4.9) et les noyaux du décodeur sont **inchangés** ;
- le mode témoin (§ 4.12) compare l'expert décodé à `empreinte_canonique` quand le bit 3 est posé.

**Ce qui reste hors de la v1.2** (réponse par délégation du 2026-10-17, réversible ; raison : la
consigne dit « le contexte de colonne s'il tient dans le format sans risque », et le chiffre ne paie
pas le risque) : le contexte de la colonne d'entrée (sorte CODES_COL, bit 4 COLONNES, octet 123,
carte des colonnes, LUT compacte). Sur gpt-oss-20b, il ne passe le seuil de 0,015 bit par poids qu'à
la couche 0 (gate −0,142, up −0,128 sur les 12 tenseurs mesurés ; ailleurs ≤ 0,010) : de l'ordre de
0,004 bit par poids sur le modèle entier (≈ 9 Mo sur 11,2 Go), contre un noyau de décodage neuf
(géométrie 2, douze contextes, LUT compacte), un montage de LUT neuf dans l'ordonnanceur et un
second décodeur indépendant à étendre. Le cahier de 05 § 4.3 et 4.4 reste la spécification si un
modèle le fait payer ; le bit 4 et la sorte 0x13 restent inconnus de ce lecteur (refusés).

**Proposition A1** (05 § 4.2) : la GEMV du moteur rend les mêmes bits sur un code 8 et sur un code 0 ;
mesurée sur la carte par `trc-noyaux/tests/carte.rs::gemv_lit_le_code_8_comme_0` (2 486 216
demi-octets fondus, 8 640 lignes, 0 différente ; cassure vue).

**Le codeur** : `trc-codeur coder … --canonique` écrit la v1.2 ; sans l'option, il écrit la v1.0
octet pour octet comme avant (réponse par délégation du 2026-10-17, réversible : garder le témoin
d'identité du 20b recodé et le fichier brut de référence). `trc-codeur verifier` contrôle, sur un
fichier canonique, le décodé contre les tranches du GGUF canonisées par un second chemin, les deux
empreintes, l'absence de 8 et l'égalité **en valeur** de chaque poids (C1 de la v1.2).

---

## 5. Les modules et leurs interfaces

### 5.0 L'espace de travail

```
moteur/
  Cargo.toml                 espace de travail : membres, [workspace.dependencies] (§ 2.4)
  crates/
    trc-format/              structures du fichier, lecture, écriture, empreintes        (lot F)
    trc-codec/               rANS processeur (codeur, décodeur), reconstruction d'un expert  (lot F)
    trc-cuda/                API du pilote CUDA : contexte, flux, événements, mémoire, copies (lot E)
    trc-es/                  lecteur sans tampon par IOCP                               (lot E)
    trc-noyaux/              noyaux .cu, build.rs, enveloppes Rust                      (lot K)
    trc-cache/               cache d'experts, politiques, simulateur                     (lot O)
    trc-ordo/                ordonnanceur de couche, préchargement                       (lot O)
    trc-modele/              gpt-oss : hyperparamètres, tampons, passe avant             (lot O)
    trc-reference/           passe avant de référence sur le processeur (f64)            (lot R)
    trc-jetons/              découpage en jetons par llama.dll                           (lot R)
    trc-juge/                logits, KL, compteurs, séries ABBA                          (lot R)
  bins/
    trc-codeur/              GGUF → .trc (+ .vocab.gguf), vérification                   (lot F)
    banc-chemin/             disque → VRAM décodé, sans modèle                          (lot E)
    troncons/                le programme : générer, évaluer, mesurer                    (lot O)
```

### 5.1 Le chemin d'un jeton (schéma à dessiner pour le mémoire, figure M1)

```
                ┌──────────────── processeur (fil d'ordonnancement) ────────────────┐
                │  lit la boîte aux lettres du routeur ℓ → cache.demander → requêtes │
                └───────┬─────────────────────────────┬────────────────────────────┘
                        │ IOCP, 1 requête = 1 tronçon │ copie asynchrone (flux de copie)
 disque (C:) ──────────►│ mémoire épinglée (fenêtre)  ├──────────────► VRAM : tampons d'arrivée
 2,58 Go/s              │ + cache tiède codé (M Go)   │  12,2 Go/s          │ décodeur (flux de décodage)
                        └─────────────────────────────┘                     ▼
                                                              emplacements d'experts décodés (cache)
                                                                            │
 flux de calcul : attn ℓ → routeur ℓ → [attend « prêt » des défauts] → GEMV experts → combiner → ℓ+1
```

Trois flux CUDA : **calcul** (priorité haute), **copie**, **décodage**. Le flux de calcul attend, par
événement, que chaque expert manquant soit décodé ; il ne lit jamais un emplacement en cours
d'écriture.

### 5.2 Le chronogramme d'une couche (figure M2)

```
 calcul  : |attn ℓ|rout ℓ|·attente·|G ℓ,0|G ℓ,1|G ℓ,2|G ℓ,3|comb|attn ℓ+1|rout ℓ+1|...
 ordo    :         ▲ lit les 4 indices (événement), succès → emplacement ; défauts → requêtes
 disque  :         |==== tronçon (défaut 1) ====|==== défaut 2 ====|  (J1+ : défauts de ℓ+1 prédits, en avance)
 copie   :                     |== DMA d1 ==|          |== DMA d2 ==|
 décodage:                                  |dec d1|              |dec d2|
```
J1 (à la demande) vit près du plancher en série ; J1+ (préchargement) vise le plafond.

### 5.3 `trc-format` (lot F)

```rust
pub const MAGIE: [u8; 8] = *b"TRONCONS";
pub const ALIGNEMENT: u64 = 4096;

#[repr(u8)] pub enum Sorte { Medianes = 1, Biais = 2, Delta = 3, CodesCtx = 4,
    CodesBruts = 6, EchellesBrutes = 7, BaseCtx = 0x10, ComplCtx = 0x11, Centres = 0x12 }

pub struct Section { pub decalage: u64, pub longueur: u64 }
pub struct Entete { pub version: (u16, u16), pub drapeaux: u32, pub taille_fichier: u64,
    pub sha256_source: [u8; 32], pub taille_source: u64, pub couches: u16, pub experts: u16,
    pub k: u16, pub matrices: u16, pub lignes: [u32; 4], pub colonnes: [u32; 4],
    pub niveaux: u8, pub classes_echelle: u8, pub partition: [u8; 8], pub sections: [Section; 8] }
pub struct EntreeRepertoire { pub decalage: u64, pub longueur: [u32; 2], pub utiles: [u32; 2],
    pub empreinte_origine: u64, pub empreinte_niveau: [u64; 2], pub couche: u16, pub expert: u16 }
pub struct DescFlux { pub sorte: Sorte, pub matrice: u8, pub contexte: u8,
    pub decalage: u32, pub longueur: u32, pub produits: u32 }
pub struct Partie<'a> { pub couche: u16, pub expert: u16, pub niveau: u8,
    pub flux: Vec<DescFlux>, pub octets: &'a [u8] }
pub enum Charge { Freq16([u16; 16]), Freq256(Box<[u16; 256]>), Centres([f32; 4]) }
pub struct Table { pub couche: u16, pub matrice: u8, pub sorte: Sorte, pub contexte: u8, pub charge: Charge }
pub struct TenseurResident { pub nom: String, pub type_ggml: u32, pub ne: [u64; 4],
    pub n_dims: u32, pub decalage: u64, pub octets: u64, pub empreinte: u64 }

pub struct Fichier { /* en-tête, méta brute, résidents, tables indexées, répertoire */ }
impl Fichier {
    pub fn ouvrir(chemin: &std::path::Path) -> Result<Fichier, ErreurFormat>; // tout vérifie
    pub fn entete(&self) -> &Entete;
    pub fn meta(&self) -> &[u8];                                 // paires GGUF brutes
    pub fn residents(&self) -> &[TenseurResident];
    pub fn debut_donnees_residentes(&self) -> u64;               // absolu
    pub fn tables(&self, couche: u16, matrice: u8) -> &[Table];
    pub fn entree(&self, couche: u16, expert: u16) -> &EntreeRepertoire;
}
pub fn lire_partie(octets: &[u8]) -> Result<Partie<'_>, ErreurFormat>;
pub fn empreinte64(octets: &[u8]) -> u64;
pub struct Ecrivain { /* écrit section par section, aligne, calcule les empreintes */ }
```

### 5.4 `trc-codec` (lot F)

Le codeur et le décodeur processeur du § 4.9, et **le décodeur de référence d'un expert** : l'oracle
que le décodeur de la carte doit égaler octet pour octet.
```rust
pub struct TableRans { pub freq: Vec<u16>, pub cumul: Vec<u32>, pub lut: Vec<u32>, pub geometrie: u8 }
impl TableRans { pub fn depuis_comptes(c: &[u64], geometrie: u8) -> Self;
                 pub fn depuis_frequences(f: &[u16], geometrie: u8) -> Result<Self, ErreurCodec>; }
pub fn coder(source: &[u8], geometrie: u8, contexte: &dyn Fn(usize) -> Option<u8>,
             tables: &[TableRans]) -> Vec<u8>;              // flux sérialisé (§ 4.9.1)
pub fn decoder(flux: &[u8], contexte: &mut dyn FnMut(usize, &[u8]) -> Option<u8>,
               tables: &[TableRans]) -> Result<Vec<u8>, ErreurCodec>; // voies hors de L : erreur
pub struct MatriceDecodee { pub codes: Vec<u8>, pub echelles: Vec<u8>, pub biais: Vec<f32> }
pub struct ExpertDecode { pub matrices: [MatriceDecodee; 3] }
impl ExpertDecode { pub fn octets_origine(&self) -> Vec<u8>; pub fn empreinte(&self) -> u64; }
pub fn reconstruire(fichier: &Fichier, couche: u16, expert: u16, parties: &[&[u8]],
                    exact: bool) -> Result<ExpertDecode, ErreurCodec>;
```
(`contexte(n)` rend `None` pour un symbole sauté.)

### 5.5 `trc-cuda` et `trc-es` (lot E)

```rust
// trc-cuda : l'API du pilote, enveloppée ; aucune autre crate n'appelle nvcuda.dll.
pub struct Contexte;  impl Contexte { pub fn nouveau(ordinal: u32) -> Result<Self>;
    pub fn memoire(&self) -> (u64 /*libre*/, u64 /*totale*/); }
pub struct Flux;      impl Flux { pub fn nouveau(c: &Contexte, priorite_haute: bool) -> Result<Self>;
    pub fn attendre(&self, e: &Evenement) -> Result<()>; pub fn synchroniser(&self) -> Result<()>; }
pub struct Evenement; impl Evenement { pub fn nouveau(c: &Contexte, horodate: bool) -> Result<Self>;
    pub fn enregistrer(&self, f: &Flux) -> Result<()>; pub fn fini(&self) -> Result<bool>;
    pub fn attendre(&self) -> Result<()>; pub fn ms_depuis(&self, debut: &Evenement) -> Result<f32>; }
#[derive(Clone, Copy)] pub struct VueCarte { pub adresse: u64, pub octets: usize }
pub struct MemoireCarte; impl MemoireCarte { pub fn allouer(c: &Contexte, octets: usize) -> Result<Self>;
    pub fn vue(&self, decalage: usize, octets: usize) -> VueCarte; }
pub struct HoteEpingle; impl HoteEpingle {
    pub fn allouer(c: &Contexte, octets: usize, projetee: bool) -> Result<Self>; // aligné 4 096
    pub fn tranche(&self) -> &[u8]; pub fn tranche_mut(&mut self) -> &mut [u8];
    pub fn adresse_carte(&self) -> Option<u64>; }                         // si projetée
pub fn copier_vers_carte(dst: VueCarte, src: &HoteEpingle, decalage: usize, octets: usize, f: &Flux) -> Result<()>;
pub fn copier_vers_hote(dst: &mut HoteEpingle, decalage: usize, src: VueCarte, f: &Flux) -> Result<()>;
pub struct Module;    impl Module { pub fn charger(c: &Contexte, image: &[u8]) -> Result<Self>;
    pub fn fonction(&self, nom: &std::ffi::CStr) -> Result<Fonction>; }
pub struct Fonction;  impl Fonction { pub unsafe fn lancer(&self, grille: [u32; 3], bloc: [u32; 3],
    partagee: u32, f: &Flux, args: &mut [*mut std::ffi::c_void]) -> Result<()>; }

// trc-es : lectures sans tampon (FILE_FLAG_NO_BUFFERING | FILE_FLAG_OVERLAPPED), port IOCP.
pub struct Requete { pub jeton: u64, pub decalage: u64, pub longueur: u32, pub destination: *mut u8 }
pub struct Achevement { pub jeton: u64, pub octets: u32, pub erreur: Option<u32>, pub duree_us: u32 }
pub struct Lecteur; impl Lecteur {
    pub fn ouvrir(chemin: &std::path::Path, profondeur: usize) -> Result<Self>;
    pub fn soumettre(&self, r: Requete) -> Result<()>;   // décalage, longueur, destination : multiples de 4 096
    pub fn recolter(&self, attente_ms: u32, sortie: &mut Vec<Achevement>) -> Result<()>;
    pub fn en_vol(&self) -> usize; pub fn octets_lus(&self) -> u64; }
```

### 5.6 `trc-noyaux` (lot K) : l'interface binaire des noyaux

**Disposition des tampons de la carte** (couture K, gelée) :
- activations : f32 contigus ; cache KV : f16, `[couche][position][tête_kv][64]` pour K et V ; les
  couches à fenêtre gardent un anneau de 128 positions ;
- tenseurs Q8_0 : la disposition ggml (blocs de 34 o : f16 d, 32 × i8), lignes contiguës ;
- **emplacement d'expert** (disposition SoA, écrite par le décodeur, lue par la GEMV) : pour chaque
  matrice j, `codes` (R · B · 16 o, ordre β), puis `échelles` (R · B o) au décalage
  `al256(R·B·16)`, puis `biais` (R × f32) au décalage `al256(al256(R·B·16) + R·B)` ; pas de matrice
  `al256(décalage des biais + 4R)` ; pour gpt-oss : 4 418 048 o par matrice, **13 254 144 o par
  emplacement** (`al256(x)` = x arrondi au multiple de 256 supérieur) ;
- valeur d'un poids MXFP4 : `k[code] · 2^(e − 128)` avec `k = {0, 1, 2, 3, 4, 6, 8, 12}` signés par le
  bit 3 (grandeurs doublées ; 03-derivations § 1.2) ; en mode base (J2), `k` est remplacé par les
  deux fois les centres de la couche (table de 16 valeurs choisie par emplacement).
- **invariant (v1.2, § 4.16)** : tout lecteur de codes lit le code 8 comme zéro (ggml : `kvalues_mxfp4`
  = 0 pour le code 8). La GEMV le fait par construction (proposition A1 : −0 et +0 rendent les mêmes
  bits) ; tout noyau neuf qui lit des codes (préremplissage par lots, GEMM) doit le garder, et son
  témoin compare un expert à sa copie canonisée.

| Noyau | Rôle | Entrées → sorties | Témoin (contre `trc-reference` ou `trc-codec`) |
|---|---|---|---|
| `decoder_matrice` | rANS v4 à table par voie, médianes + δ → échelles, codes en place | flux codés en VRAM, LUT, → emplacement | octets égaux à `trc-codec::reconstruire` ; voies hors de L comptées |
| `copier_brut` | chemin brut (fichier brut) | flux bruts → emplacement | octets égaux |
| `gemv_mxfp4` | y = W x + b | emplacement, x f32 → y f32 | écart relatif ≤ 10⁻⁵ à une référence f64 ; exact au bit sur entiers (03 § 4.5) |
| `gemv_q8_0` | y = W x (+ b) | Q8_0, x → y | idem |
| `gemv_f32` | routeur | F32 2 880 × 128, x → logits + biais | idem |
| `rmsnorm` | x · w / √(moyenne(x²) + ε) | → | ≤ 10⁻⁶ relatif |
| `rope_yarn` | rotation de q et k, YaRN (facteur 32, contexte d'origine 4 096, β 32 / 1, base 150 000), échelle d'attention de YaRN | q, k, position → | ≤ 10⁻⁶ |
| `ecrire_kv` | ajoute k, v au cache (f16) | → | octets égaux |
| `attention` | décodage, 64 têtes q, 8 têtes kv, dimension 64, puits appris par tête dans le dénominateur du softmax, fenêtre de 128 sur les couches à fenêtre | q, cache, puits → sortie 4 096 | ≤ 10⁻⁵ |
| `routeur_topk` | top-4 des logits biaisés, softmax sur les 4 retenus ; ordre : score décroissant, puis indice croissant | logits → indices u32[4], poids f32[4], **copiés dans la boîte aux lettres projetée** | égal à la référence (indices) ; poids ≤ 10⁻⁶ |
| `swiglu_oai` | `g ← min(g, 7)` ; `u ← clamp(u, −7, 7)` ; `g · σ(1,702 g) · (u + 1)` | gate, up → | ≤ 10⁻⁶ |
| `combiner` | résidu += Σ_{i=0..3} poids_i · sortie_i, **dans l'ordre i = 0, 1, 2, 3** | → | exact au bit contre la même somme sur l'hôte en f32 |
| `ligne_q8_0` | ligne d'enchâssement → f32 | → | octets égaux |
| `argmax` | jeton glouton ; égalité : plus petit indice | logits → u32 | égal |

**Règle de déterminisme** (couture K) : aucun noyau n'utilise d'addition atomique en virgule
flottante ; toute réduction suit un arbre fixe qui ne dépend que des tailles. Sans cette règle, le
témoin C3 (égalité au bit) n'aurait pas de sens.

Les formes du calcul de gpt-oss (attention à puits, alternance des couches à fenêtre, YaRN,
SwiGLU bornée, routeur après top-k) se lisent dans llama.cpp b11515 (MIT) et dans la carte du modèle
publiée par OpenAI ; rien n'est copié ; **`trc-reference` les implémente la première et le juge les
valide contre llama.cpp** (§ 7, R1), avant qu'un noyau ne soit jugé contre elle.

### 5.7 `trc-cache` (lot O)

```rust
pub type Id = (u16 /*couche*/, u16 /*expert*/);
#[derive(Clone, Copy)] pub enum Niveau { Base = 0, Exact = 1 }      // Base inutilisé avant J2
pub enum Etat { Libre, EnVol { niveau: Niveau }, Present { niveau: Niveau } }
pub enum Decision {
    Succes { emplacement: u32 },
    DefautRam { emplacement: u32, tiede: u32 },     // tronçon codé déjà en mémoire épinglée
    DefautDisque { emplacement: u32, tiede: Option<u32> } }
pub trait Politique { fn acceder(&mut self, id: Id, t: u64); fn inserer(&mut self, id: Id, t: u64);
    fn retirer(&mut self, id: Id); fn victime(&mut self, epingle: &dyn Fn(Id) -> bool) -> Option<Id>; }
pub struct Lru; pub struct Slru { /* probatoire, protégé ; J1+ */ }
pub struct Cache<P: Politique> { /* emplacements VRAM, entrées tièdes RAM, états, compteurs */ }
impl<P: Politique> Cache<P> {
    pub fn nouveau(emplacements: u32, tiedes: u32, vram: P, ram: P) -> Self;
    pub fn demander(&mut self, couche: u16, experts: &[u16], t: u64) -> Vec<Decision>;
    pub fn pret(&mut self, emplacement: u32);                 // décodage terminé
    pub fn liberer(&mut self, couche: u16);                   // fin des GEMV de la couche : désépingle
    pub fn compteurs(&self) -> Compteurs; }
pub struct Compteurs { pub succes_vram: u64, pub succes_ram: u64, pub defauts_disque: u64,
    pub octets_disque: u64, pub octets_copies: u64, pub evictions: u64 }
pub fn rejouer<P: Politique>(trace: &Trace, emplacements: u32, tiedes: u32, vram: P, ram: P) -> Compteurs;
pub fn lire_trace(chemin: &std::path::Path) -> Result<Trace>; // format de outils/chargement_localite.py
```
Un expert demandé par la couche en cours est **épinglé** jusqu'à `liberer` ; la victime n'est jamais
épinglée. Le **simulateur est le même code** que le cache réel (`rejouer`), ce qui rend le témoin
« compte du moteur = compte du simulateur à l'unité » possible.

### 5.8 `trc-ordo` et `trc-modele` (lot O)

```rust
pub struct Config { pub fichier: PathBuf, pub ram_tiede_go: f64, pub enchassement_en_ram: bool,
    pub profondeur_es: usize, pub couches_d_avance: usize, pub prechargement: bool,
    pub contexte: u32, pub temoin: bool, pub brut: bool }
pub struct Moteur { /* fichier, contexte CUDA, flux, noyaux, cache, lecteur, fenêtre épinglée */ }
impl Moteur {
    pub fn nouveau(c: &Config) -> Result<Self>;
    pub fn pas(&mut self, jeton: u32, position: u32, logits: Option<&mut [f32]>) -> Result<u32>; // glouton
    pub fn compteurs(&self) -> CompteursMoteur;      // h compté, octets, temps par étage, défauts prédits
    pub fn reinitialiser(&mut self); }
```
La fenêtre épinglée : `d · k` tampons d'arrivée de la taille du plus grand tronçon (d = couches
d'avance, 3 par défaut, partisan-A § 4.4), plus le cache tiède codé (`ram_tiede_go`), plus une ligne
d'enchâssement. Le préremplissage de J1 est une boucle de `pas` ; J1+ ajoute un préremplissage par
flux (chaque expert d'une couche lu une fois pour tous les jetons de l'invite qui le demandent).

### 5.9 `trc-reference`, `trc-jetons`, `trc-juge` (lot R)

```rust
// trc-reference : la passe avant de gpt-oss en f64 sur le processeur, lue dans le GGUF d'origine
// (pas dans le .trc : chemin indépendant), experts lus à la demande, aucun cache.
pub struct Reference; impl Reference { pub fn ouvrir(gguf: &Path) -> Result<Self>;
    pub fn pas(&mut self, jeton: u32, position: u32) -> Vec<f64>;          // logits
    pub fn noyau_*(…);   /* chaque opération exposée seule, pour les témoins du lot K */ }
// trc-jetons : llama.dll (libloading), vocab_only.
pub struct Jetons; impl Jetons { pub fn ouvrir(dll: &Path, vocab: &Path) -> Result<Self>;
    pub fn decouper(&self, texte: &str, special: bool) -> Vec<u32>; pub fn texte(&self, jeton: u32) -> String; }
// trc-juge : fenêtres de 512 jetons de wikitext-2 test, logits de la base llama.cpp
// (fichier --kl-divergence-base, format lu dans tools/perplexity), KL, premier choix, PPL,
// compteurs (PDH « PhysicalDisk(_Total)\Disk Read Bytes/sec », mémoire du processus, VRAM),
// séries ABBA et règle de décision de 06 § 7.5.
```

### 5.10 `troncons` (lot O)

```
troncons generer   --modele m.trc --vocab m.vocab.gguf --invite fichier.txt -n 256 [--ram-tiede 0] [--temoin]
troncons evaluer   --modele m.trc --vocab … --base base.kld --fenetres 10   (KL, premier choix, PPL)
troncons mesurer   --modele m.trc … --serie ABBA                            (jetons/s, RAM, VRAM, octets lus, h)
```
Sortie : le texte, et un journal JSON (commande, date, alimentation, compteurs, empreinte du texte).

---

## 6. Les lots

### 6.1 Les cinq lots

| Lot | Mission | Fichiers possédés (seul propriétaire) | Carte ? |
|---|---|---|---|
| **F** format et codeur | le format § 4, le codec processeur, le codeur GGUF → `.trc`, le compagnon vocab ; en J2, la v1.1 | `moteur/crates/trc-format/**`, `moteur/crates/trc-codec/**`, `moteur/bins/trc-codeur/**` | non |
| **E** chemin des octets | CUDA (contexte, flux, mémoire épinglée, copies), lecteur IOCP, banc de bout en bout | `moteur/crates/trc-cuda/**`, `moteur/crates/trc-es/**`, `moteur/bins/banc-chemin/**` | oui |
| **K** noyaux | tous les noyaux et leurs enveloppes, leurs bancs | `moteur/crates/trc-noyaux/**` | oui |
| **R** référence, juge, qualité de B | passe avant f64, jetons, juge, base llama.cpp, écart entre moteurs, **banc Q0** | `moteur/crates/trc-reference/**`, `moteur/crates/trc-jetons/**`, `moteur/crates/trc-juge/**`, `outils/q0/**` | Q0 et la base seulement |
| **O** moteur | cache et simulateur, ordonnanceur, modèle, programme, intégration, espace de travail | `moteur/Cargo.toml`, `moteur/Cargo.lock`, `moteur/crates/trc-cache/**`, `moteur/crates/trc-ordo/**`, `moteur/crates/trc-modele/**`, `moteur/bins/troncons/**` | oui |

Chaque lot tient sa note de reprise (`moteur/REPRISE-<lot>.md`, à lui seul) et ses journaux
(`mesures/moteur/<lot>/**`, à lui seul). `decisions/ARCHITECTURE.md` reste à l'arbitre.

### 6.2 Les coutures gelées (version 1, 2026-10-15)

| Couture | Ce qui est gelé | Entre | Où |
|---|---|---|---|
| F | le format `.trc` au bit près | F → E, K, O, R | § 4 |
| C | l'API de `trc-cuda` | E → K, O | § 5.5 |
| N | l'interface binaire des noyaux, la disposition des tampons, la règle de déterminisme | K → O | § 5.6 |
| A | l'API de `trc-cache` et le format de trace | O ↔ R (simulateur) | § 5.7 |
| J | le format des journaux de mesure (champs de `modeles-base.py`, plus `h`, octets par étage) | O, E → R | § 5.9 |
| D | les dépendances et leurs versions | tous | § 2.4 |

Changer une couture : le lot qui en a besoin l'écrit dans sa note de reprise, l'orchestrateur la
porte à l'arbitre, l'arbitre décide ici par une ligne datée ; aucune couture ne change dans un
commit de code. Une couture peut s'**étendre** (fonction ajoutée) sans décision si rien d'existant ne
change.

### 6.3 L'ordre

```
 semaine de travail (ordre, pas durées) →
 F : F1 format+codec ─► F2 codeur 20b ─► F3 codeur 120b ─────────────────────────► F4 v1.1 (J2)
 E : E0 essais (épinglée, synchro, IOCP→épinglée→DMA) ─► E1 trc-cuda, trc-es ─► E2 banc-chemin (attend K1)
 K : K1 décodeur ─► K2 GEMV MXFP4 ─► K3 passe avant (attend R1 pour ses témoins) ─► K4 mode base (J2)
 R : R0 écart entre moteurs (llama.cpp) ─► R1 référence f64 ─► R2 juge ─► Q0 (carte libre, trace) ─► Q (J2)
 O : O1 cache + simulateur (attend la trace) ─► O2 modèle (attend K3) ─► O3 moteur 20b ─► O4 120b = J1 ─► J1+
```
Dépendances dures : E2 attend K1 ; K3 attend R1 ; O3 attend F2, E1, K3 ; O4 attend F3 ; J2 attend
J1 (C3) et Q0.

### 6.4 Repli à 3 ou 4 ingénieurs

- **4** : R et F fusionnent (deux lots processeur ; Q0 a la priorité dès que la carte se libère).
- **3** : {F, R} ; {E, O} ; {K}. Le lot K reste seul : la passe avant est le long pôle (partisan-A
  § 4.6).

### 6.5 Critères de fin de chaque étape (témoin, cassure, seuil déclaré)

| Étape | Livrable | Témoin | Cassure | Seuil (et sa source) |
|---|---|---|---|---|
| **F1** | `trc-format`, `trc-codec` | aller-retour écriture → lecture identique ; décodeur processeur = flux de `decoupe-arbitre` | un octet d'en-tête faussé → refus ; table faussée → décodage faux | 0 écart |
| **F2/F3** | `gpt-oss-20b.trc`, `gpt-oss-120b.trc`, compagnons | **C1** : 100 % des experts décodés par le processeur égaux à l'original (empreinte et octet à octet) ; taux à 0,1 % de F1 (20b) et de 1,1026 (120b) | une médiane faussée dans une copie → inexact détecté | 0 expert faux |
| **E0** | essais | (a) `cuMemHostAlloc` de 0,25 / 1 / 4 / 11 Go ; (b) `ReadFile` sans tampon dans cette mémoire puis DMA, octets égaux ; (c) 36 synchronisations par jeton (événement + boîte aux lettres) | octet faussé dans la source | (b) DMA ≥ 11,0 Go/s (12,2 [mes. 01] − 10 %) ; (c) ≤ 15,7 ms par jeton (10 % du temps disque d'un jeton, LRU calé ; partisan-A étape 0b) |
| **E2** | `banc-chemin` : tous les experts du 20b, disque → VRAM décodés | **C2** : empreinte de chaque expert égale au répertoire ; débit de bout en bout ≤ min des étages | un bit retourné dans une copie du fichier → détecté | ≥ 0,8 × 2,58 × r(F1) Go/s d'experts servis (0,8 = 1 − 2 × 10 % de bruit [mes. 01]) |
| **K1** | décodeur CUDA à table par voie | sortie = `trc-codec` sur les 108 tenseurs du 120b ; voies à L | une fente de LUT corrompue → sortie fausse | débit ≥ 0,8 × 41,6 Go/s (la variante mesurée qu'il remplace, [mes. 03]) ; sinon repli décidé ici |
| **K2** | GEMV MXFP4 | exact au bit sur entiers ; 10⁻⁵ sur réels | référence décalée de 1 % → tombe | ≥ 0,8 × 209,4 Go/s ([mes. 03], même règle) |
| **K3** | passe avant (12 noyaux) | chaque noyau contre `trc-reference` | chaque témoin forcé à faux | seuils du § 5.6 |
| **R0** | écart entre moteurs sur gpt-oss-20b : llama.cpp `--cpu-moe` contre `--fit`, et processeur seul (`CUDA_VISIBLE_DEVICES=-1`) contre carte | plancher de l'instrument (même configuration deux fois) | autre modèle → KL nette | publié : `G_cfg` et `G_moteurs` |
| **R1** | référence f64 | KL(référence ‖ llama.cpp carte) ≤ max(G_moteurs, 7·10⁻⁵) sur 10 fenêtres de 512 | une erreur injectée (YaRN sans son échelle) → tombe | idem |
| **O1** | cache, simulateur | `rejouer` = le simulateur de 04 sur les traces synthétiques à l'unité | politique faussée → écart | 0 écart |
| **O3** | moteur sur 20b, M = 0 | C3, C4 sur 20b ; compte du cache = `rejouer` sur la trace du moteur | tronçon corrompu → empreinte et logits faux | § 7 |
| **O4** | **J1** | § 7 | § 7 | § 7 |

---

## 7. Le premier jalon : critères de réussite

### 7.1 J1 : gpt-oss-120b, exact, fenêtre bornée (déclarés le 2026-10-15, avant toute construction)

| Critère | Mesure | Seuil | D'où vient le seuil |
|---|---|---|---|
| **C1 format exact** | experts décodés par le processeur contre le GGUF | 0 faux sur 4 608 | sans perte par définition |
| **C2 transport exact** | empreinte de chaque expert décodé sur la carte (`--temoin`) | 0 écart ; 100 % des corruptions injectées détectées | idem |
| **C3 moteur exact** | logits du `.trc` codé contre le `.trc` brut, même moteur | **0 bit différent** sur 10 fenêtres de 512 jetons (5 120 pas) | mêmes octets, mêmes noyaux, même ordre (règle de déterminisme) : l'égalité est attendue, pas tolérée |
| **C4 moteur juste** | KL(troncons ‖ référence f64) et KL(llama.cpp carte ‖ référence f64), mêmes fenêtres | la première ≤ la seconde, et premier choix de troncons ≥ celui de llama.cpp (intervalles binomiaux) ; les logits de troncons passent par la même quantification à 16 bits par logit que le fichier de base de llama.cpp, pour que l'instrument soit le même des deux côtés | « au moins aussi près des mathématiques exactes du modèle que la base » ; contourne le fait que deux moteurs justes diffèrent de 0,0055 [mes. 06] ; la référence f64 sur le 120b demande de l'ordre d'une à trois heures de processeur pour 5 120 pas [est.] |
| **C5 vitesse (à la demande)** | jetons/s du 120b, mode A0, séries ABBA | ≥ **0,8 × le plancher en série** recalculé avec le `h` compté par le moteur et les débits mesurés dans la même séance | 0,8 = 1 − 2 × 10 % (bruit de la lecture de 4 Mio en QD 4 [mes. 01]) ; repères (`verif-plafonds.json`, `seuils_J1`) : **0,99 / 2,15 / 3,32 jetons/s** (uniforme / LRU calé / Belady calé) |
| **C7 fenêtre bornée** | RAM de pointe (ensemble de travail de pointe du processus, mémoire épinglée comprise), A0, 120b et 20b | 120b ≤ **1,9 Go** ; écart 120b − 20b ≤ 2 × bruit de passe à passe + 0,5 Mo | 1,9 Go : A0 publié par 07, que la fenêtre minimale (0,64 Go, partisan-A § 4.4) doit battre ; 0,5 Mo : le répertoire, seul terme qui croît avec le modèle (annexe A.1 du partisan de A) |
| **C8 octets lus** | compteur PDH contre octets comptés par le moteur | écart ≤ charge de repos × durée + 100 Mo | résolution de l'instrument [mes. 06] |
| **C10 VRAM** | pointe (nvidia-smi, 250 ms) | ≤ 8 188 − 909 Mio, aucune éviction du pilote | relevé de 10 h 15 (mesures/REPRISE-gpt-oss.md) |
| **C11 sans perte** | perplexité et tâches du juge | égales au chiffre près au chemin brut | conséquence de C3 |
| **C12 texte** | 256 jetons gloutons sur l'invite wikitext de 06 § 7.2 | publiés, et identiques entre `.trc` codé et brut | « texte juste » = C3 + C4 ; l'égalité avec llama.cpp n'est pas exigée (06 § 7.3 : deux moteurs justes bifurquent) |

### 7.2 J1+ : la vitesse contre la base

| Critère | Seuil | Source |
|---|---|---|
| **C6** | jetons/s de troncons (préchargement, SLRU, meilleure RAM tiède admise par E0) au-dessus de la meilleure configuration mesurée de llama.cpp sur le 120b, de plus de 2 × le plus grand bruit et de 3 % | 06 § 7.5, telle quelle ; base : `mesures/gpt-oss.md` (exploration : 0,49 jeton/s [expl.], non retenue par son auteur) |
| **C9** | rendement physique (mesuré ÷ plafond au `h` mesuré) | publié, pas jugé |

### 7.3 J2 : B dans le moteur (portes et seuils du partisan de B, repris sans les desserrer)

- **Q-instrument** : la ré-expression exacte (Q8_0) retombe à KL ≤ 7·10⁻⁵, premier choix 100 % ;
  sinon le banc Q0 est faux.
- **Q1 indiscernable** : KL de B contre le mode exact du même moteur ≤ **0,0055** et premier choix
  ≥ 95,96 % ; ce seuil (Qwen3.5-4B) sera **barré et remplacé au grand jour** par `G_moteurs` mesuré
  sur gpt-oss en R0, jamais en silence.
- **Q2 contribution** : le point (KL, Go lus par jeton) de B passe sous la frontière des
  requantifications uniformes (Q0.d) d'au moins deux erreurs-types.
- **Vitesse** : un mode B vaut s'il bat le mode exact du même moteur de plus de 2 × le bruit et 3 %.
- **Format** : v1.1 à deux niveaux, format unique (F1, S1bis : +0,31 %). Si le codeur de
  production du 120b dépasse 1,004 × le niveau unique, l'arbitre redécide (deux fichiers ou contexte
  plus riche), par une ligne datée ici.

### 7.4 Critères d'abandon

- **K1** (partisan de A) : C3 ne tient pas et la cause n'est pas trouvée : ni A ni B ne sont
  jugeables ; on cherche, on ne passe pas à B.
- **K2** : C6 tombe avec le préchargement : A n'est pas une contribution de vitesse ; il reste la
  référence exacte, et l'effort passe à B.
- **K3** : E0(a, b) échoue (aucune mémoire épinglée importante ou DMA < 11 Go/s) : repli paginable
  (sans effet sur secteur, partisan-A § 4.4) ; le régime batterie se publie comme perdu.
- **K4** : E0(c) dépasse 15,7 ms par jeton : `t0` devient un étage ; on recalcule C5.
- **Mort de B3 sans politique** : Q0.c au-dessus de la frontière et `K_tout` > 0,25.
- **Mort de B avec perte** : aucun mode B ne passe Q2 en J2 ; B1 reste comme gain de latence s'il
  passe Q1, sinon le format revient au niveau unique.

---

## 8. Le protocole d'épreuve indépendante

Le juge est un agent qui n'a écrit ni ce document ni le code. Il travaille depuis un clone propre
du dépôt, sur secteur (noté), carte libre, et ne lit que ce document, le code et les journaux.

1. **La spécification est-elle vraie ?** Il écrit un décodeur Python (numpy) **à partir du seul
   § 4**, sans lire `trc-format` ni `trc-codec`, et décode 20 tronçons tirés au hasard (graine
   publiée) dans `gpt-oss-120b.trc` ; chaque expert doit égaler le GGUF au bit près (§ 4.11). Un
   échec est un défaut de la spécification ou du codeur, à trancher ici.
2. **Les témoins tombent-ils ?** Il rejoue chaque cassure du § 6.5 et du § 7, et vérifie que chaque
   témoin tombe, puis tient une fois restauré.
3. **Les chiffres se reproduisent-ils ?** Il refait C3, C4, C5, C7, C8, C10 en séries ABBA (au moins
   deux), avec ses propres commandes ; une différence avec le journal du lot n'est réelle que selon
   la règle de 06 § 7.5.
4. **La base est-elle honnête ?** Il relance la meilleure configuration de llama.cpp publiée et une
   autre qu'il choisit (par exemple `--n-cpu-moe` réglé autrement), pour vérifier que C6 ne gagne pas
   contre une base mal réglée.
5. **La fenêtre est-elle bornée ?** Il mesure la RAM de pointe du 120b et du 20b, puis donne 1 Go de
   cache tiède à l'un : l'écart doit apparaître (≈ 1 Go), sinon l'instrument ne voit rien.
6. **Le texte est-il juste ?** Il lit les 256 jetons de C12 et une conversation au format harmony de
   gpt-oss (publiée, non jugée).
7. Il écrit son verdict (`decisions/epreuve-J1.md`) : ce qui tient, ce qui tombe, ce qu'il n'a pas pu
   vérifier, et sa propre section « Ce qui pourrait être faux ».

---

## 9. Ce qui dépend de `mesures/gpt-oss.md` (non commité à l'heure où j'écris)

| Si elle donne… | Pour J1 | Pour la décision |
|---|---|---|
| `h(c)` proche du scénario LRU ou meilleur | C5 vers 2,15 jetons/s ou plus en A0 | inchangée |
| `h(c)` proche de l'uniforme | C5 vers 0,99 en A0 ; A reste 3 à 4 fois au-dessus de l'exploration de la base | inchangée pour A ; B3 sert alors 92 % des usages par la base : Q0 décide seul |
| une base llama.cpp ABBA bien au-dessus de 0,49 | C6 plus difficile | K2 se rapproche ; la décision A d'abord tient (A reste la référence exacte de B) |
| ρ grand | — | la spéculation entre en J3 |
| les poids de mélange g | — | `s`, la part de Σ g² servie par la base : l'ordre de grandeur de la KL de B1 et B3 (partisan-B § 3.2), et la règle de la politique λ |
| la fréquence de chaque expert | l'ensemble chaud de Q0.c (sur un corpus distinct du texte de jugement) | — |

**Ce qui n'en dépend pas** : la correction du ×1,42 (le rapport B1/A ne dépend que des bits lus, § 1.3),
l'ordre des jalons, le choix de CUDA, le format, F1, les lots et les critères (leurs seuils se
recalculent avec le `h` mesuré).

---

## 10. Ce qui pourrait être faux

- **Tous les plafonds dépendent de `h(c) = c^β`**, calé sur un seul point publié ; la mesure en cours
  peut les décaler d'un facteur 5. Les critères de J1 sont écrits pour s'y recalculer, pas pour s'y
  fier.
- **La qualité de B est estimée, pas mesurée** : linéarité de HIGGS, `K_tout ∈ [0,10 ; 0,25]` par
  analogie. Si Q0 la trouve bien meilleure, B aurait pu passer en premier ; le coût de mon ordre est
  alors le délai entre Q0 et J2, que la construction de J1 occupe de toute façon.
- **Le choix de CUDA repose sur une mesure du décodeur (+14,9 %) et sur l'absence de deux fonctions
  dans wgpu**, pas sur une mesure du chemin complet sous Vulkan ; un Vulkan sans wgpu (ash, avec
  `VK_EXT_external_memory_host` et une file de transfert) aurait peut-être fait aussi bien. Je ne l'ai
  pas mesuré ; je le tiens pour un portage futur, pas pour une erreur exclue.
- **La latence d'une synchronisation par couche sous WDDM** n'est mesurée nulle part ; E0(c) la
  mesure ; si elle est forte, `t0` devient un étage (K4).
- **La mémoire épinglée de plusieurs Go** sous WDDM sur une machine de 16 Go partagée peut être
  refusée ou dégrader le reste de la machine ; E0(a) la mesure ; A0 n'en a besoin que de 0,2 Go.
- **F1 est mesuré sur 12 tenseurs de gpt-oss-20b**, pendant qu'un autre agent mesurait (machine
  chargée : sans effet sur des octets, possible sur le temps) ; le 120b peut différer d'un millième
  de bit (03 a mesuré 0,0001 d'écart de taux entre les deux).
- **Le décodeur à table par voie n'est mesuré que sur le processeur** : sur la carte, trois LUT de
  16 Kio en mémoire partagée (48 Kio) réduisent l'occupation ; 03 a montré que l'occupation n'était
  pas le plafond de la v4 (la v3 compacte n'a rien gagné), mais c'est un autre noyau. Repli déclaré
  (K1) : les trois flux réassemblés, sorte 0x05 réservée.
- **Le témoin C4** suppose que la référence f64 est juste ; R1 la valide contre llama.cpp à
  `G_moteurs` près, ce qui laisse passer une erreur plus petite que l'écart entre deux moteurs.
- **La règle de déterminisme** peut coûter de la vitesse à quelques noyaux (réductions sans
  atomiques) ; le budget de la carte le permet (8 fois de marge sur le disque chiffré, partisan-A
  § 4.5).
- **Le préremplissage par boucle de décodage** rend J1 lent sur une longue invite (708 jetons à
  2 jetons/s : six minutes) ; c'est pourquoi le préremplissage par flux est dans J1+.
- **Le compagnon `.vocab.gguf` sans tenseurs** n'a pas été essayé avec `llama.dll` b11515 ; si le
  chargement le refuse, le moteur garde le GGUF d'origine pour le seul découpage en jetons.
- **Les estimations d'effort** des partisans (+5 à 10 %, +25 à 35 %) sont des estimations ; aucune
  durée n'est donnée ici, faute de mesure qui la fonde.
- **SliceMoE, HOBBIT et TRACE** : les deux premiers lus en entier par le partisan de B (rendu HTML),
  TRACE au résumé seulement ; la nouveauté de B peut encore se réduire avant publication.

---

## 11. Pour le mémoire (LaTeX, anglais et français)

**Dérivations à écrire en entier**
1. L'équation du jeton et ses deux bornes (max, somme), avec le terme des compléments (partisan-B
   A.1, A.2) ; le calcul pas à pas de A, B1 complété et B3 dans le scénario LRU (§ 1.3).
2. Pourquoi B1 ne gagne qu'en latence : disque = `R h_s (b_base + b_compl)/4,25` ≥ celui de A dès que
   `b_base + b_compl ≥ b_A` ; condition du gain en série (complément sur le temps libre du disque).
3. La règle de la chaîne `H(X) = H(B) + H(X|B)` pour une base fonction du code ; **le coût réel de la
   découpe** : l'information perdue entre demi-octets d'un même octet, `I(c_lo ; c_hi, g_hi | g_lo,
   κ)` et sa part rendue par le contexte riche (F1, § 3.3).
4. **Le rANS à contexte connu du décodeur** (table par voie, table par symbole, sauts) : preuve que
   le décodage reste exact et sans branche divergente, et que le taux égale la somme des entropies
   conditionnelles à l'en-tête près.
5. La fenêtre bornée (proposition A.1 du partisan de A), et le témoin 20b contre 120b.
6. Les seuils de J1 : 0,8 = 1 − 2 × bruit ; C4 comme comparaison à la vérité mathématique plutôt
   qu'à un autre moteur.

**Schémas à dessiner (TikZ)** : M1 le chemin d'un jeton (§ 5.1) ; M2 le chronogramme d'une couche,
J1 et J1+ (§ 5.2) ; M3 le fichier `.trc` (§ 4.2) et un tronçon à deux niveaux (§ 4.8) ; M4 la tuile
rANS et la table par voie (un bloc = quatre voies d'un macro-pas) ; M5 l'automate du cache (Libre,
En vol, Présent ; en J2 avec les niveaux) ; M6 la carte des lots et des coutures (§ 6) ; M7 l'arbre
de décision des jalons et des portes (§ 1.2, § 7).

**Données à produire (CSV, par les lots)** : F1 par tenseur (`decoupe-gptoss20b.json` → CSV, outil
de l'arbitre) ; plafonds A, A0, B1, B3 contre `h_s` (`verif-plafonds.json`) ; débits du décodeur
CUDA contre Vulkan (K1) ; chronogrammes horodatés d'un jeton (O3) ; jetons/s, RAM, VRAM, octets lus en
ABBA (J1) ; courbe de succès réelle du cache contre le simulateur (O3, trace) ; frontière KL contre
octets (Q0.d) ; points B (J2).

**Tableaux** : écartés et leurs nombres (§ 1.6) ; CUDA contre Vulkan (§ 2.3) ; F1 (§ 3.3) ; champs du
format (§ 4.3 à 4.8) ; critères (§ 7).

---

## 12. Réponses par délégation de ce document

Chacune : « réponse par délégation du 2026-10-15, réversible ».
1. **A d'abord (J1), B en parallèle hors moteur (Q0), B dans le moteur en J2.** Raison : seul ordre
   qui livre E1 vite sans retarder la mesure qui décide d'E2 (§ 1).
2. **Rust + CUDA (API du pilote).** Raison : décodeur +14,9 %, recouvrement et mémoire épinglée
   mesurés seulement sous CUDA, fonctions absentes de wgpu (§ 2.3).
3. **Fichier autonome `.trc` + compagnon vocab.** Raison : un artefact par modèle pour un instrument
   général ; 2,3 Go de disque (§ 4.1).
4. **Un tronçon par expert, niveaux préfixes.** Raison : une requête par défaut ; la place de B
   gardée sans rien coûter à A (§ 4.1).
5. **Table par voie plutôt que flux de classe réassemblés.** Raison : F1 (§ 3).
6. **Empreinte64 = préfixe de SHA-256.** Raison : déjà dans le cache cargo, assez pour un témoin.
7. **Préremplissage par boucle en J1, par flux en J1+.** Raison : le plus simple à prouver exact
   d'abord.
8. **Contexte de 4 096 jetons en J1.** Raison : le cache KV en prendrait 4,8 Go à 131 072.
9. **C4 contre une référence f64 plutôt que contre llama.cpp seul.** Raison : deux moteurs justes
   diffèrent de 0,0055 [mes. 06] ; la vérité mathématique ne diffère de rien.
10. **v1.1 à deux niveaux comme format unique de J2, complément à contexte riche.** Raison :
   F1, +0,31 % sous le seuil déclaré de 0,4 % ; un seul fichier par modèle.

---

## 13. Recettes (essayées par l'arbitre, avec leur raison)

| Recette | Marche ? | Raison |
|---|---|---|
| Second chemin des plafonds sans importer l'outil contesté | oui | sept témoins reproduits à 1 % ; la cassure fait tomber le seul visé ; le désaccord se tranche sur le terme, pas sur l'opinion |
| `start /low` de cmd depuis Git Bash pour baisser la priorité | **échec** | « Accès refusé » et une attente de 17 minutes sans que l'outil ne démarre ; remplacé par `Start-Process` puis `PriorityClass = 'Idle'` en PowerShell |
| Inclure la bibliothèque rANS de 03 par `#[path]` plutôt que comme dépendance | oui | code identique sans copie ni compilation de wgpu |
| Mesurer la découpe expert par expert, au format | oui | les tailles de tronçon sortent de la même passe que les taux |
| Table d'histogramme de la base dimensionnée à 8 symboles | **échec, corrigé** | le demi-octet de base vaut jusqu'à 11 (bit de signe) ; panique au premier tenseur ; 16 |
| Table choisie par voie au lieu de flux réassemblés | oui | même taux (−0,008 %), décodeur plus simple ; le contexte connu du décodeur rend la règle de la chaîne sans déplacer un octet |
| Complément conditionné par la seule classe de magnitude (proposition du partisan de B) | non retenu | +0,78 % sur A ; la classe d'échelle rend 0,37 point |
| Complément conditionné par la classe d'échelle | presque | +0,41 %, à 0,01 point du seuil |
| Contexte riche (classe voisine, complément faible décodé) | oui | +0,31 % ; ajouté après la passe 1, seuil inchangé déclaré avant la passe 2 |
| Rejouer la passe 1 avec l'outil modifié | oui | les variantes communes rendent les mêmes octets : la mesure est déterministe | | |

---

## 14. Outils, journaux, sources

- `outils/arbitre/verif_plafonds.py` → `decisions/journaux/arbitre/verif-plafonds.json`,
  `verif-plafonds-casse.json`. Commande : `python -I -X utf8 outils/arbitre/verif_plafonds.py
  [--casser] > decisions/journaux/arbitre/<journal>.json`.
- `outils/arbitre/decoupe/` (Rust ; `cargo build --release --offline`) →
  `decisions/journaux/arbitre/decoupe-gptoss20b.json`, `decoupe-gptoss20b-casse.json`. Commande :
  `decoupe-arbitre <gpt-oss-20b-MXFP4.gguf> <journal.json> --fils 2 [--casser]`, priorité inactive.
- `outils/arbitre/vers_csv.py` → `decisions/journaux/arbitre/csv/` (`f1-par-tenseur.csv`, `f1-totaux.csv`,
  `plafonds-arbitre.csv`, `seuils-j1.csv`), les données des figures du mémoire.
- Sources : les études 01 à 07, les deux plaidoyers et leurs journaux, cités par section ; llama.cpp
  b11515 (MIT, licence vérifiée par 06) pour les formes du calcul de gpt-oss ; aucune source
  extérieure nouvelle, donc pas de fichier BibTeX propre à ce document (`memoire/sources/`).
