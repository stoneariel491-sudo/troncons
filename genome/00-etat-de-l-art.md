# 00 · Le génome des poids : l'état de l'art, à la source primaire

Étude « génome des poids » de troncons, rôle de l'éclaireur. Date : 2026-10-16. Toutes les sources
ont été consultées le 2026-10-16 (heure de Toronto) ; leurs métadonnées viennent de l'API d'arXiv
(`export.arxiv.org/api/query`, User-Agent `troncons-recherche/1.0`) ou de l'API de Crossref
(`api.crossref.org/works/<DOI>`), jamais d'un agrégateur. Étiquettes : **littérature (éditeur, non
reproduit)** pour un chiffre lu dans une source, **mesuré ici** pour un chiffre sorti d'un outil commité
de troncons, **calculé** pour un chiffre déduit de chiffres nommés.

Ce qui a été lu : le **résumé** de chaque article (API arXiv ou page de l'éditeur), et pour les
travaux dont le mécanisme compte pour nous (GPTQ, OBC, QMoE, MatGPTQ, SeedLM, Tied Trit-Planes) la
formulation qu'ils publient. Aucun dépôt de code n'a été lu : aucune licence de code n'est donc en
jeu ici (règle du SOCLE, « Le code des autres »). La liste complète, avec adresse, dates et ce qui a
été lu, est dans `mesures/genome/etat-de-l-art/sources.csv` ; le BibTeX des clés neuves dans
`memoire/sources/genome-etat-de-l-art.bib`.

---

## En bref

1. **La physique fixe la question.** Sur la machine de Stone le disque est l'étage le plus lent
   (2,82 Go/s mesurés, fondations/01) ; tout ce qui compte est le nombre de **bits lus par poids**.
   La frontière à battre, mesurée ici sur gpt-oss-20b : **3,84 bits par poids sans perte** (codes
   MXFP4 en rANS, échelles E8M0 en écart à la médiane de ligne, ARCHITECTURE § 3) ; **2,64 bits pour
   la base seule** (signe et quatre classes de magnitude) à **4,29 % d'erreur quadratique relative**
   sur les poids (07 § 4.2, F1).
2. **La propriété des poids qui décide de presque tout** est déjà mesurée (03 § 1.6) : sachant
   l'échelle de leur bloc, les codes MXFP4 de gpt-oss sont **presque indépendants** (le code
   précédent n'apporte que 0,005 bit, le contexte d'échelle 0,035). Or toutes les familles
   « génomiques » de la littérature (graines, hyperréseaux, automates cellulaires, dictionnaires,
   parenté d'experts, codage prédictif) exploitent une **dépendance** entre poids. Sur une source
   i.i.d., aucune ne peut descendre sous la fonction distorsion-débit **de cette source, dans le
   domaine des poids** ; je la calcule dans genome/01-eclaireur.md et elle borne leur gain.
3. **Ce qui échappe à cette borne** n'est pas une meilleure description des poids : c'est **changer
   la distorsion qu'on mesure**. Ce qui compte n'est pas ‖ΔW‖ mais ‖ΔW x‖ sur les entrées que le
   modèle donne vraiment, et ces entrées sont fortement corrélées. La rétroaction d'erreur de
   OBS/OBC/GPTQ exploite exactement cela (littérature, non reproduit : GPTQ quantifie un modèle de
   175 milliards de paramètres en environ quatre heures de carte, à 3 ou 4 bits). Le vivant a le même
   geste : le **code génétique** est rangé pour que les erreurs probables tombent sur des codons
   **synonymes** (Freeland et Hurst 1998 : « un sur un million ») ; le **neurone** code en
   sigma-delta, c'est-à-dire en reportant son erreur (Yoon 2017).
4. **Ce qui n'a jamais été tenté sur un modèle né en 4 bits** (aucune trace dans les recherches
   consignées, § 3) : une base **emboîtée dans le code natif** (le code exact reste récupérable par un
   complément sans perte), **choisie par rétroaction d'erreur sur les entrées réelles** et **sous
   contrainte d'entropie**, avec le **même décodeur** que la base fixe. Les voisins les plus proches :
   MatGPTQ (2026, emboîté et à rétroaction, mais depuis le BF16 et sur une grille entière), Tied
   Trit-Planes (2026, requantifie les experts MXFP4 publiés et les lit sur SSD, mais à 4,06 bits et
   sans emboîtement), Scale-QLoRA (2026, garde le plan des codes MXFP4 intact, mais adapte les
   échelles, ne compresse pas).
5. **Le mécanisme que j'ai conçu et mesuré**, « la mutation synonyme », est décrit et jugé dans
   genome/01-eclaireur.md.

---

## D'où on part, où on va

**Au départ** : l'idée de Stone (idees/biomimetisme-genome-des-poids.md), sa consigne du 2026-10-16
(« le but est de concevoir un systeme fonctionnel »), la découpe base + complément mesurée (07, F1),
le format `.trc` et le moteur du Tome II. Trois autres équipes conçoivent en parallèle : la **recette**
(graine et coefficients), la **duplication de gènes** (parenté d'experts) et le **codage prédictif et
l'élagage**.

**Ce que ce document établit** : ce que chaque famille pose, ce qu'elle a mesuré (chiffres de ses
auteurs), ce qui lui manque pour notre cas, et, chiffre de 03 à l'appui, ce qu'on peut en attendre
sur des poids nés en MXFP4 ; puis la carte de ce qui n'a pas été tenté.

**Ce qui reste** : les mesures des quatre équipes (genome/01 à 04) et la synthèse (genome/05).

---

## 1. La question, posée par la machine et par les poids

**Le toit.** La vitesse maximale d'un jeton vaut le débit du disque divisé par les octets lus par
jeton (Tome I, théorème du toit). Diviser les bits par poids lus par deux double le toit. La carte a
environ 214 opérations libres par octet compressé (fondations/01 ; 926 au débit réel du disque du
moteur, Tome II ch. 09) : tout mécanisme qui coûte moins que cela à la transcription est gratuit.

**La source.** Un poids MXFP4 vaut `± K[m] · 2^(e − 128)` (K = {0, 1, 2, 3, 4, 6, 8, 12}, valeurs
E2M1 doublées, e l'exposant E8M0 partagé par 32 poids). L'étude 03 a mesuré, sur les 72 tenseurs
d'experts de gpt-oss-20b :

| Grandeur | Valeur | Statut |
|---|---|---|
| H(code), ordre 0 | 3,860 bits sur 4 | mesuré ici (07) |
| apport du code précédent | 0,005 bit | mesuré ici (03) |
| apport du contexte d'échelle | ≈ 0,035 bit | mesuré ici (F1 : 2,642 → 2,607 pour la base) |
| échelles E8M0 sachant la médiane de ligne | 1,01 bit pour 32 poids, soit 0,032 bit par poids | mesuré ici (03) |
| sans perte, tout compris | 3,8431 bits par poids | mesuré ici (F1) |
| base seule (signe + 2 bits) | 2,6441 bits, 4,29 % d'erreur relative | mesuré ici (F1, 07) |

**Ce que cela veut dire.** À l'intérieur d'un bloc, les codes se comportent comme des tirages
indépendants d'une même loi. Une source i.i.d. n'a pas d'autre structure que sa loi : **la
description la plus courte d'une suite i.i.d. est son codage entropique**, et aucun générateur,
aucune règle locale, aucun dictionnaire ne fait mieux en moyenne (Shannon 1948 ; le théorème de
codage de source s'applique à toute description, programme générateur compris, au sens de la
complexité de Kolmogorov, dont l'espérance par symbole tend vers l'entropie pour une source
i.i.d. : Cover et Thomas 2006, chapitre 14). C'est le premier filtre de toute idée « génomique » : **quelle dépendance
exploite-t-elle, et a-t-on mesuré cette dépendance sur nos poids ?**

**Le second filtre** : avec perte, la mesure qui compte. Une erreur sur les poids ne coûte que par ce
qu'elle change à la sortie. Pour une matrice W et ses entrées x, l'erreur de sortie vaut
`E‖ΔW x‖² = tr(ΔW H ΔWᵀ)`, `H = E[x xᵀ]`. Si H était proportionnelle à l'identité, l'erreur de sortie
serait l'erreur sur les poids ; elle ne l'est pas (les activations des modèles de langage ont des
canaux dominants, AWQ : « protéger 1 % des poids saillants réduit beaucoup l'erreur », littérature,
non reproduit). Toute la marge d'un mécanisme avec perte est là.

---

## 2. Les familles, chacune à la source

Pour chaque famille : **ce qu'ils posent**, **ce qu'ils mesurent** (chiffres des auteurs, non
reproduits), **ce qui nous manque** pour l'employer, **ce qu'ils n'ont pas**, et le **pronostic** sur
des poids nés en MXFP4.

### 2.1 La recette à graine : SeedLM, PRANC, NOLA, la dimension intrinsèque

- **SeedLM** (Shafipour et al., Apple, arXiv 2410.10714, v2 du 2024-10-16) : chaque bloc de poids est
  approché par une combinaison linéaire de quelques colonnes d'une matrice pseudo-aléatoire engendrée
  par un registre à décalage (LFSR) depuis une graine ; on stocke la graine et des coefficients
  quantifiés. Sans données de calibration. Mesuré par eux : à 3 et 4 bits, meilleure rétention de
  précision que l'état de l'art sur Llama 3 70B ; ×4 de vitesse sur FPGA à 4 bits.
- **PRANC** (Nooralinejad et al., arXiv 2206.08464, v2 du 2023-08-28) : tout un réseau comme
  combinaison linéaire de réseaux aléatoires gelés ; une graine et les coefficients. Compression
  d'environ ×100 sur des classifieurs d'images, **entraînée dans le sous-espace** (pas après coup).
- **NOLA** (Koohpayegani et al., arXiv 2310.02556, v2 du 2024-04-30) : le même geste pour les
  matrices d'une LoRA.
- **La dimension intrinsèque** (Li et al., arXiv 1804.08838, 2018) : entraîner dans un sous-espace
  aléatoire de dimension d trouve des solutions pour d bien plus petit que le nombre de paramètres.

**Ce qui nous manque** : PRANC et NOLA (et la dimension intrinsèque) cherchent les poids **dans** le
sous-espace pendant l'entraînement ; gpt-oss est déjà entraîné hors de tout sous-espace. SeedLM
travaille après coup, mais **avec perte** et sur des poids BF16 : un bloc de C poids approché par k
colonnes aléatoires laisse un résidu d'énergie relative ≈ 1 − k/C si les poids sont i.i.d. (la
projection d'un vecteur aléatoire sur un sous-espace aléatoire de dimension k garde k/C de son
énergie, en moyenne [calculé]). SeedLM rachète cela en choisissant la meilleure graine parmi 2^16 :
un gain de sélection d'environ 16 bits par bloc, pas plus (on ne peut pas gagner plus d'information
que l'index qu'on stocke [calculé]).
**Pronostic sur MXFP4** : pas de gain sans perte possible (source i.i.d.) ; avec perte, borné par la
distorsion-débit de la source dans le domaine des poids (genome/01 § 3). C'est le sujet de l'équipe
« genome ».

### 2.2 Les réseaux qui génèrent les poids : hyperréseaux, HyperNEAT, automates cellulaires

- **HyperNetworks** (Ha, Dai et Le, arXiv 1609.09106, v4 du 2016-12-01) : un petit réseau produit
  les poids d'un grand, **entraînés ensemble**.
- **HyperNEAT** (Stanley, D'Ambrosio et Gauci, *Artificial Life* 15(2), 2009,
  DOI 10.1162/artl.2009.15.2.15202) : les poids comme une fonction de la géométrie des neurones
  (un CPPN évolué) ; de grands réseaux réguliers décrits par de petits génomes.
- **Growing Neural Cellular Automata** (Mordvintsev et al., *Distill*, 2020-02-11,
  DOI 10.23915/distill.00023) : une règle locale apprise fait croître et réparer une forme.
- **HyperNCA** (Najarro, Sudhakaran, Glanois et Risi, arXiv 2204.11674, 2022) : des automates
  cellulaires neuronaux font **croître** les poids de petits réseaux de politique en apprentissage par
  renforcement.

**Ce qui nous manque** : tous génèrent des poids **qu'on entraîne à être générables** (régularité
imposée). Aucun ne décrit après coup les poids d'un modèle de langage entraîné librement.
**Ce qu'ils n'ont pas** : une mesure de la régularité spatiale des poids d'un grand modèle. Le
03 la donne indirectement pour gpt-oss : le voisin n'apporte que 0,005 bit.
**Pronostic** : une règle locale (automate, CPPN) ne peut reproduire une texture i.i.d. qu'en
stockant l'aléa ; elle ne gagne rien sans perte, et avec perte elle ne fait pas mieux qu'une graine.
Écarté pour cette ronde, par ce chiffre.

### 2.3 La parenté et la fusion d'experts des MoE

- **MC-SMoE** (Li et al., arXiv 2310.01334, v2 du 2024-03-14) : fusion d'experts guidée par le
  routage, puis compression basse-rang.
- **Merging Experts into One** (He et al., arXiv 2310.09832, v3 du 2023-11-21) : calcul de plusieurs
  experts en un seul.
- **HC-SMoE** (Chen et al., arXiv 2410.08589, v4 du 2025-10-26) : regroupement hiérarchique d'experts
  selon leurs **sorties**, fusion sans réentraînement.
- **Sub-MoE** (Li et al., arXiv 2506.23266, 2025-06-29) : SVD jointe des experts concaténés, U partagé
  par groupe, V propres fusionnés.
- **D²-MoE** (Gu et al., arXiv 2502.17298, 2025-02-24) : un poids de base partagé (fusion pondérée par
  l'information de Fisher) plus des **deltas** propres compressés par SVD ; « plus de 13 % de gain de
  performance » sur les autres compresseurs à 40-60 % de compression (littérature, non reproduit).
- **MoBE** (Chen et al., arXiv 2508.05257, 2025-08-07) : W = A B, B combinaison de bases partagées par
  la couche ; −24 à −30 % de paramètres pour 1 à 2 % de précision sur Qwen3-235B, DeepSeek-V3, Kimi-K2.
- **OMP-MoE** (Li et al., arXiv 2609.31631, v2 du 2026-09-29) : élagage d'experts comme reconstruction
  parcimonieuse (poursuite orthogonale), testé **sur GPT-OSS** entre autres ; 93,3 % de la performance
  de Qwen3-30B-A3B à 50 % de compression.

**Ce qui nous manque** : tous partent de poids BF16 et mesurent une précision de tâches, pas des bits
par poids ; aucun ne mesure la parenté **sur des codes de 4 bits**, où une différence de deux codes
n'a pas la loi d'une différence de deux réels. **Pronostic** : la parenté se juge par l'information
mutuelle entre experts ; si deux experts ne partagent que leur loi (sans corrélation poids à poids),
le delta coûte autant que l'expert. C'est le sujet de l'équipe « duplication ».

### 2.4 Le codage différentiel des poids

- **BitDelta** (Liu et al., arXiv 2402.10193, v3 du 2024-10-13) : le delta d'un affinage tient en
  **1 bit** par poids (signe et une échelle), sans perte de performance mesurable par eux.
- **Delta-CoMe** (Ping et al., arXiv 2406.08903, v3 du 2024-11-26) : delta en précision mixte selon les
  valeurs singulières.

**Ce qui nous manque** : un parent. Un affinage a un parent naturel (le modèle pré-entraîné) ; un
expert n'en a pas, sauf s'il est né par copie (« upcycling »). gpt-oss ne dit pas comment ses experts
sont nés (carte du modèle, arXiv 2508.10925).

### 2.5 Le codage prédictif et entropique sans perte

- **Le cortex prédictif** (Rao et Ballard, *Nature Neuroscience* 2(1), 1999, DOI 10.1038/4580) : seul
  l'écart à la prédiction remonte.
- **DeepCABAC** (Wiedemann et al., arXiv 1905.08318, 2019) : codage arithmétique binaire adaptatif au
  contexte des poids quantifiés (norme NNC).
- **ZipNN** (Hershcovitch et al., arXiv 2411.05239, v2 du 2025-06-04) : sans perte, sur BF16,
  « souvent 33 % » de gain, exposant séparé.
- **DFloat11** (Zhang et al., arXiv 2504.11651, v3 du 2026-01-01) : codage de longueur variable des
  exposants BF16, −30 %, sorties identiques au bit, décodeur sur la carte.
- **Huff-LLM** (Yubeaton et al., arXiv 2502.00922, 2025) : Huffman de bout en bout jusque dans les
  tampons du processeur.
- **TRACE** (Xie et al., arXiv 2509.03377, v3 du 2026-01-30) : plans de bits par canal, −25,2 % sur les
  poids BF16 sans perte, et modélise GPT-OSS-120B-MXFP4 côté débit.

**Ce qui nous manque** : tous gagnent sur **l'exposant BF16**, très redondant. Un code MXFP4 n'a plus
d'exposant par poids ; il reste 0,14 bit de redondance par code (4 − 3,86) et 0,14 bit sur les
échelles, que troncons prend déjà (3,84 bits, 03, F1). **Pronostic** : le codage prédictif sans perte
ne peut gagner que ce que le code précédent apporte : 0,005 bit mesuré. Avec perte bornée, c'est un
quantificateur en boucle fermée (DPCM) : sur une source i.i.d. il n'a rien à prédire. C'est le sujet
de l'équipe « prédictif-élagage ».

### 2.6 L'élagage, synaptique et expert

- **Huttenlocher** (*Brain Research* 163(2), 1979, DOI 10.1016/0006-8993(79)90349-4) : la densité
  synaptique du cortex frontal humain culmine dans l'enfance puis décroît.
- **Optimal Brain Damage** (LeCun, Denker et Solla, NeurIPS 1989) et **Optimal Brain Surgeon**
  (Hassibi et Stork, NeurIPS 1992) : retirer les poids dont la **perte au second ordre** est la plus
  faible, et (OBS) **compenser** l'erreur sur les poids restants avec l'inverse de la hessienne.
- **Deep Compression** (Han, Mao et Dally, arXiv 1510.00149, v5 du 2016-02-15) : élagage,
  quantification entraînée, Huffman.
- **Not All Experts are Equal** (Lu et al., arXiv 2402.14800, v2 du 2024-05-30) et **ESTS** (Martin et
  al., arXiv 2609.12310, 2026-09-11, **sur GPT-OSS-20B**, experts retirés selon la masse de routage puis
  réaffinés, puis requantifiés en MXFP4) : retirer des experts entiers.

**Le lien avec le mécanisme choisi** : OBS est le premier « report d'erreur » : la compensation par
l'inverse de la hessienne est exactement ce que OBC et GPTQ appliquent à la quantification (§ 2.8).

### 2.7 Les dictionnaires appris et les codes vectoriels

- **Le codage parcimonieux du cortex visuel** (Olshausen et Field, *Nature* 381, 1996,
  DOI 10.1038/381607a0) : un dictionnaire appris sur des images naturelles donne des champs récepteurs
  de cellules simples.
- **AQLM** (Egiazarian et al., arXiv 2401.06118, v4 du 2024-09-11) : quantification additive (somme de
  mots de plusieurs dictionnaires appris), régime de 2 bits.
- **QuIP#** (Tseng et al., arXiv 2402.04396, v2 du 2024-06-04) : incohérence par Hadamard et
  dictionnaire en réseau E8 ; **QTIP** (Tseng et al., arXiv 2406.11235, v4 du 2025-06-18) : codes en
  treillis.
- **HyperQuant** (Domb et al., arXiv 2606.23406, 2026-06-22) : Hadamard aléatoire, réseaux optimaux
  (E8, D4, A2), codage de Rice ; bat HIGGS de 3 à 5 bits.
- **MASA** (Zhussip et al., arXiv 2508.04581, v2 du 2026-02-19) : atomes matriciels partagés entre les
  couches d'attention, −66,7 % de paramètres d'attention, **entraîné**.

**Ce qui nous manque** : ces codes vectoriels **remplacent** la grille : ils partent du BF16. Sur une
source i.i.d., un code vectoriel ne gagne sur un scalaire que le **gain de pavage** (au plus 1,53 dB,
0,254 bit, à haut débit ; Gish et Pierce 1968 pour l'ECSQ ; Marcellin et Fischer 1990 pour le
treillis, qui en reprend environ 1 dB) [littérature, non reproduit]. **Pronostic** : au plus ≈ 0,25
bit à erreur égale **dans le domaine des poids**, et au prix d'un décodeur nouveau.

### 2.8 La rétroaction d'erreur pondérée par les entrées réelles

- **OBC** (Frantar, Singh et Alistarh, arXiv 2208.11580, v2 du 2023-01-08) : réalisation exacte et
  efficace d'OBS pour quantifier et élaguer après coup, avec un peu de données de calibration.
- **GPTQ** (Frantar, Ashkboos, Hoefler et Alistarh, arXiv 2210.17323, v2 du 2023-03-22) : quantifier
  les colonnes l'une après l'autre en reportant l'erreur sur les suivantes par le facteur de
  Cholesky de H⁻¹ ; 175 milliards de paramètres en environ quatre heures de carte, 3 ou 4 bits.
- **QMoE** (Frantar et Alistarh, arXiv 2310.16795, 2023-10-25) : GPTQ sur 1,6 billion de paramètres
  d'un MoE (SwitchTransformer-c2048), ternaire puis **codage entropique sur mesure**, **0,8 bit par
  paramètre**, décodeur dédié sur la carte, < 5 % de surcoût d'exécution (littérature, non reproduit).
- **AWQ** (Lin et al., arXiv 2306.00978, v6 du 2026-04-25) : l'importance d'un canal se lit dans les
  activations, pas dans les poids.
- **MoEQuant** (Hu et al., arXiv 2505.03804, 2025) et **EAQuant** (Fu et al., arXiv 2506.13329, v3 du
  2026-02-01) : la calibration d'un MoE souffre du déséquilibre des échantillons entre experts.
- **Le neurone sigma-delta** (Yoon, *IEEE TNNLS* 28(5), 2017, DOI 10.1109/TNNLS.2016.2526029) : les
  neurones LIF codent un signal en impulsions par une forme de modulation sigma-delta asynchrone,
  c'est-à-dire en **reportant leur erreur de quantification** sur la suite.

**Ce qui nous manque** : un point de départ né en 4 bits (GPTQ et QMoE partent du BF16), une grille
imposée (nos 8 niveaux, emboîtés dans le code), et le **coût en débit** (GPTQ ne code pas
l'entropie ; QMoE oui, mais sur sa propre grille). **Ce qu'ils n'ont pas** : la contrainte qu'un
complément sans perte rende le code exact derrière la base, pour servir l'expert exact quand il le
faut (architecture B).

### 2.9 Les formats emboîtés, et les modèles nés en 4 bits

- **Matryoshka Quantization** (Nair et al., arXiv 2502.06786, v3 du 2025-03-03) : les bits de poids
  fort d'un entier int8 forment un int4 et un int2 ; entraînement conjoint.
- **Any-Precision LLM** (Park et al., arXiv 2402.10517, v4 du 2024-06-21) : un seul modèle lu à 3, 4,
  …, n bits.
- **MatGPTQ** (Kleinegger et al., arXiv 2602.03537, v2 du 2026-09-30) : Matryoshka **après coup** par
  « compensation d'erreur multi-précision » en une passe de calibration ; noyaux dédiés. Le plus
  proche de notre mécanisme : emboîté et à rétroaction. Mais depuis le BF16, sur grille entière, par
  troncature des bits forts (que 07 a mesurée moins bonne que la meilleure partition : 4,47 % pour
  2,91 bits contre 4,29 % pour 2,64).
- **Microscaling** (Rouhani et al., arXiv 2310.10537, 2023) et la spécification OCP MX : le format.
- **Training LLMs with MXFP4** (Tseng et al., arXiv 2502.20586, v3 du 2025-08-26) : entraîner avec des
  produits MXFP4, arrondi stochastique.
- **gpt-oss** (OpenAI, arXiv 2508.10925, 2025-08-08) : les poids des experts publiés en MXFP4.
- **Scale-QLoRA** (Li et al., arXiv 2609.04526, 2026-09-03) : sur un modèle MX natif, n'adapter que
  les échelles et **geler le plan des codes E2M1**, « environ 90 % des octets » ; ils notent qu'un
  modèle déjà sur la grille a pour optimum de reconstruction… lui-même.
- **Tied Trit-Planes** (Grella, arXiv 2608.08910, 2026-08-09) : requantifie **en une passe depuis les
  experts MXFP4 publiés** de DeepSeek-V4-Flash (284B-A13B) vers un code à neuf niveaux de 4,0625 bits
  par poids, **lu sur SSD** sur un portable de 64 Go ; erreur de reconstruction plus haute mais
  fidélité de référence égale à leurs tailles d'évaluation.
- **BitNet b1.58** (Ma et al., arXiv 2402.17764, 2024) : un modèle né ternaire.

### 2.10 L'ADN au sens propre

- **Le calcul par ADN** (Adleman, *Science* 266, 1994, DOI 10.1126/science.7973651) : un problème
  combinatoire résolu par la chimie ; rien qui transpose sur une carte graphique.
- **Le stockage dans l'ADN** (Church, Gao et Kosuri, *Science* 337, 2012, DOI 10.1126/science.1226355 ;
  Goldman et al., *Nature* 494, 2013, DOI 10.1038/nature11875 ; Erlich et Zielinski, *Science* 355,
  2017, DOI 10.1126/science.aaj2038, « DNA Fountain ») : des codes de canal (codes fontaine, contraintes
  d'homopolymères) qui approchent la capacité d'un canal biochimique. **Ce qui ne transpose pas** : ils
  codent des fichiers déjà compressés ; la densité de l'ADN est physique (atomes), pas
  informationnelle (2 bits par base, § 2 de l'idée de Stone).
- **Le code génétique comme code correcteur** (Freeland et Hurst, *J. Mol. Evol.* 47, 1998,
  DOI 10.1007/PL00006381) : parmi un million de codes alternatifs, le code naturel est l'un des
  meilleurs pour **minimiser l'effet des erreurs ponctuelles** sur les propriétés des acides aminés.
- **Le biais d'usage des codons** (Sharp et Li, *Nucleic Acids Research* 15(3), 1987,
  DOI 10.1093/nar/15.3.1281) : les gènes très exprimés emploient de préférence certains codons
  synonymes ; l'indice CAI le mesure.

**Ce qui transpose** : pas l'alphabet, pas la chimie : **l'agencement d'un code pour que l'erreur
tombe là où le phénotype ne la voit pas** (Freeland et Hurst), et **la dépense de précision là où
l'expression est forte** (Sharp et Li). C'est l'origine du mécanisme de genome/01.

### 2.11 L'évolution des codes

- **EvoPress** (Sieberling et al., arXiv 2410.14649, v2 du 2025-07-01) : recherche évolutionnaire du
  profil de compression par couche ; l'hypothèse d'indépendance des couches est fausse (« élaguer
  davantage peut même rétablir la performance »).
- HyperNEAT (§ 2.2) évolue des génomes de réseaux.

**Pour nous** : l'évolution est un **optimiseur**, pas une représentation ; elle cherche une graine
(genome), un arbre de parenté (duplication), un profil (EvoPress). Elle ne crée pas d'information.

### 2.12 Les mémoires réparties et les index

- **Holographic Reduced Representations** (Plate, *IEEE TNN* 6(3), 1995, DOI 10.1109/72.377968) :
  des structures liées par convolution circulaire dans un vecteur de taille fixe.
- **L'index de l'hippocampe** (Teyler et DiScenna, *Behavioral Neuroscience* 100(2), 1986,
  DOI 10.1037/0735-7044.100.2.147) : un index court rappelle un souvenir complet stocké ailleurs.

**Pour nous** : un index court ne rappelle un souvenir complet que si le souvenir est **déjà stocké**
quelque part ; c'est la description d'un cache (déjà construit : le cache d'experts du Tome II), pas
une compression.

---

## 3. Ce qui n'a jamais été tenté sur un modèle né en 4 bits

Recherches consignées (API arXiv, 2026-10-16 ; requêtes et nombre de réponses dans `sources.csv`) :
« MXFP4 ET gpt-oss », « lossless ET MXFP4 », « gpt-oss ET compression », « Matryoshka ET
quantization », « any-precision ET LLM », « DNA ET neural network ET weight compression » (0),
« cellular automata ET weights ET compress » (0), « dictionary learning ET large language model ET
weight ET compression », « genetic code ET error ET quantization » (0).

| Geste | Fait ailleurs | Sur un modèle né en 4 bits ? |
|---|---|---|
| Sans perte sur les codes et les échelles MX | ZipNN, DFloat11, TRACE : sur BF16 | **troncons** (03, F1 : 3,84 bits) ; rien d'autre trouvé |
| Base emboîtée dans le code natif, complément exact | Matryoshka, Any-Precision, MatGPTQ : sur entiers, depuis le BF16 | **troncons** (07, F1 : base fonction du code) |
| Requantifier les experts MXFP4 publiés | Tied Trit-Planes (4,06 bits, SSD), ESTS (après élagage et réaffinage) | jamais **sous** 4 bits avec un complément exact |
| Rétroaction d'erreur sur les entrées réelles | OBC, GPTQ, QMoE, MatGPTQ : depuis le BF16 | **jamais** pour choisir une base emboîtée dans un code MXFP4 |
| Contrainte d'entropie dans la rétroaction | QMoE code l'entropie après coup ; HyperQuant code par Rice | **jamais** dans le choix des symboles d'une base native |
| Graine, hyperréseau, automate, dictionnaire après coup | SeedLM (BF16), MoBE, Sub-MoE, D²-MoE (BF16) | non trouvé ; équipes genome et duplication |

**La case vide que je prends** : les lignes 4 et 5 réunies, dans le cadre des lignes 2 et 3 :
**choisir les symboles de la base emboîtée par rétroaction d'erreur sur les entrées réelles, sous
contrainte d'entropie, sans toucher au décodeur ni au code exact**. Raison du choix, chiffrée : c'est
le seul geste de la liste qui ne parie pas sur une dépendance entre poids que 03 a mesurée absente
(0,005 bit) ; il parie sur une dépendance entre **entrées**, que le moteur peut mesurer.

---

## 4. Ce que la lecture prédit, et que les mesures doivent juger

| Famille | Dépendance exploitée | Mesure de troncons qui la juge | Pronostic |
|---|---|---|---|
| Graine, hyperréseau, automate | régularité des poids | 0,005 bit pour le voisin (03) | aucun gain sans perte ; avec perte ≤ borne D(R) des poids |
| Parenté d'experts, delta | corrélation entre experts | information mutuelle entre experts (équipe duplication) | gain si et seulement si l'IM est grande |
| Prédictif sans perte | dépendance séquentielle | 0,005 bit (03) | ≤ 0,005 bit |
| Élagage | poids inutiles | sensibilité mesurée (équipe prédictif-élagage) | dépend de la sortie, pas des poids |
| Code vectoriel, dictionnaire | forme de la loi | gain de pavage ≤ 0,254 bit | ≤ 0,25 bit, décodeur neuf |
| **Mutation synonyme** | **corrélation des entrées** | **H = E[g² x xᵀ] mesurée sur les entrées réelles (genome/01)** | **le seul qui puisse dépasser la borne des poids** |

---

## Ce qui pourrait être faux

- **Je n'ai lu que des résumés** (et les formulations publiées des méthodes clés) : un chiffre d'un
  résumé est un chiffre d'éditeur, jamais reproduit ici. Un article peut contenir une expérience sur un
  modèle MXFP4 que son résumé ne dit pas : la case « jamais tenté » veut dire « non trouvé par les
  requêtes consignées », pas « inexistant ».
- **La quasi-indépendance des codes** vient de 03 (ordre 1, voisin dans la ligne, contexte d'échelle).
  Une dépendance d'ordre plus élevé, à longue portée ou entre experts n'y est pas mesurée ; les
  équipes duplication et prédictif-élagage la mesurent.
- **L'argument de Kolmogorov** est en moyenne sur la source : un tenseur particulier peut avoir une
  description courte (une graine qui l'a engendré à l'initialisation, par exemple) ; après des
  milliers de pas d'entraînement, rien ne l'indique, et la graine d'origine n'est pas publiée.
- **Le gain de pavage** (0,254 bit) est une borne asymptotique à haut débit ; à 2 à 3 bits il est plus
  petit, ce qui renforce le pronostic.
- **Les recherches** ont été faites sur arXiv et Crossref seulement ; les actes de conférence non
  déposés sur arXiv peuvent manquer.
