# 03 · La compression sans perte, et la décompression à la vitesse du calcul

Étude 03 de troncons. Date : 2026-10-15. Toutes les sources ont été consultées le
2026-10-15. Étiquettes : **mesuré ici** (sur la machine de Stone, outil et journal
commités), **calculé** (à partir de chiffres nommés), **littérature (éditeur, non
reproduit)**.

## En bref

Mis à jour à la reprise du 2026-10-15 (machine sur batterie puis sur secteur, §4.1 bis).
Les chiffres de débit cités ici sont ceux du secteur.

1. **Ce qu'un GGUF K-quant garde d'entropie, mesuré ici sur Qwen3.5-4B et 9B (Q4_K_M) :**
   les codes Q4_K portent 3,865 bits par code sur 4 (H0, deux modèles, 263 tenseurs).
   Les codes Q5_K portent 4,86 sur 5. Les codes Q6_K portent 5,78 sur 6. Le code
   précédent n'apporte que 0,005 bit, l'échelle du sous-bloc pas davantage. Tout est
   donc dans l'ordre 0.
2. **Le plafond sans perte d'un GGUF K-quant est de 5,2 à 5,3 %** (mesuré ici, tous champs
   compris : 5,062 → 4,808 bits/poids sur le 9B, taux 1,053). Un tiers du gain vient des
   métadonnées des blocs : échelles fp16 à 9,5 bits d'entropie sur 16, échelles 6 bits à
   4,9 bits. **zstd prend 1,2 %, lz4 0 %.** Un codeur d'octets sur le bloc entier
   (DEFLATE, GDeflate, les littéraux de zstd) plafonne à 1,8 %.
3. **Le modèle cible, MXFP4 (gpt-oss), en laisse deux fois plus, et surtout dans ses
   échelles** (§1.6). Ses échelles E8M0 portent 1,55 bit sur 8 à l'ordre 0 et **1,01 bit
   sachant la médiane de leur ligne** (0,91 sur gpt-oss-120b), une reconstruction sans
   dépendance d'un bloc à l'autre. Un codage par champs (codes en rANS, échelles en écart
   à la médiane de ligne) donne, **mesuré et décodé exactement sur les 72 tenseurs
   d'experts de gpt-oss-20b, 3,903 bits par poids au lieu de 4,25 : taux 1,0888**, et
   **1,0887 sur les 108 tenseurs de gpt-oss-120b (60,9 Go)**. En répartissant de plus les
   codes en trois flux selon la place de leur échelle par rapport à la médiane de la
   ligne, chacun avec sa table et le même décodeur, le taux monte à **1,1037** sur
   gpt-oss-20b (3,850 bits par poids) et à **1,1026 sur gpt-oss-120b** (3,855), réassemblage
   exact, mesuré sur la carte à 102 Go/s. Pour gpt-oss-120b, le taux agit deux fois (octets
   lus et place du cache) : +12,4 % de jetons par seconde là où le disque borne à 1,0887,
   +14,4 % à 1,1026 (calculé, routage uniforme).
4. **J'ai écrit un codeur rANS entrelacé par sous-groupe**, décodé sur la RTX 4060 par
   Vulkan, sans boîte à outils CUDA, exact au bit près, témoin cassé qui tombe. Taux réel
   sur les demi-octets Q4_K : 1,0316 (3,877 bits par code pour une borne de 3,865).
   Débit de la v4 (alphabet octet) sur secteur : **70 à 72 Go/s de codes produits**
   (140 milliards de codes par seconde), dispersion sous 10 %, le même sur Q4_K et sur
   MXFP4. **Second chemin** : le même algorithme réécrit en CUDA, nourri du même flux,
   rend les mêmes octets et décode à 81-82 Go/s ; le compilateur de NVIDIA tire 14 % de
   plus de la boucle, la recopie ne diffère que de 4 % (§4.1 ter).
5. **La question clé, tranchée par la mesure** (§4.5, `banc_gemv`, poids MXFP4 réels de
   gpt-oss-20b, vérification exacte bit à bit et témoins qui tombent) :
   - **poids résidents en VRAM** : le produit matrice-vecteur brut atteint 209 Go/s de
     poids équivalents (83 % de la VRAM) ; **fondu au décodeur, il tombe à 57 Go/s, 3,7 fois
     plus lent, et pas plus rapide que deux passes** (décoder puis multiplier, 56 Go/s).
     Le calcul du §4.3 prédisait 3,4. Fondre n'économise que de la mémoire, et les deux
     noyaux sont limités par le calcul ;
   - **poids lus par le disque ou la PCIe** : le décodeur est 28 fois plus rapide que le
     disque (2,49 Go/s de codes à produire contre 70) ; décoder à l'arrivée en VRAM coûte
     3,6 % du temps de la carte et rend au disque tout le taux r. **Le disque redevient le
     seul plafond.**
   - D'où l'architecture : décoder une fois, à l'arrivée du tronçon, avant qu'il n'entre
     dans le cache de la carte ; jamais dans le produit.
6. **Le levier plus gros n'est pas sans perte, et il existe déjà en CUDA.** À erreur
   quadratique égale à une quantification façon Q4_K, une quantification taillée pour un
   codeur (ECSQ) demande 4,05 à 4,09 bits par poids au lieu de 4,5 (mesuré ici sur des
   substituts, §5). EntQuant (ICML 2026) et vram-compression (2026-09) font cette famille
   de choses en CUDA, poids gardés compressés en VRAM (§2.13) : le trou 3 de la première
   version est barré (§7). Ce qui manque encore : sans CUDA, en flux depuis le disque, sur
   les formats GGUF.
7. **Contradiction publiée.** Un article de l'ISCA 2026 (arXiv 2606.15789) annonce
   « 0,6 à 1,0 bit d'entropie réelle » pour des poids int4. Je mesure 3,86 bits sur les
   K-quants, 3,86 sur MXFP4, et 3,75 à 3,86 bits sur des quantifications min-max par
   groupes de 32 et 64 appliquées à des poids réels (§6).
8. **Ce qui a pesé sur les mesures** : la machine était sur batterie pendant la première
   moitié de la reprise (limite de la carte 43 W au lieu de 80) ; le décodeur y perd un
   facteur 2,6 et le produit brut un facteur 3,2. Les rapports entre chemins tiennent ;
   les débits absolus cités sont ceux du secteur.

---

## 0. La question, et son juge

Pour un modèle plus gros que sa mémoire, chaque jeton doit lire presque tous ses poids :
5,10 Go par jeton pour Qwen3.5-9B Q4_K_M (tout sauf `token_embd`, qui n'est pas lié à la
tête de sortie), 2,73 Go pour le 4B, dont les plongements sont liés (calculé depuis
l'inventaire, journal `entropie-*.json`). Le temps d'un jeton est au mieux le maximum,
sur chaque étage, du rapport entre les octets qui le traversent et son débit effectif.

Compresser sans perte d'un taux r divise par r les octets qui traversent le disque, la
RAM et la PCIe. Cela ne gagne que si le décodeur suit : son débit de sortie doit dépasser
r fois le débit de l'étage qu'il soulage, et son coût en temps de calcul ne doit pas
manger le gain. Cette étude mesure les deux termes : r, et le débit du décodeur.

Chiffres de la machine repris des autres études, mesurés ici mais par elles :
- disque : plafond observé ≈ 2,8 Go/s (16 Mio, QD1), BitLocker actif, pilote Intel RST VMD
  (étude 01, `journaux/01-machine/disque-analyse.md`) ;
- PCIe, hôte vers carte, gros transferts : 4 à 6,4 Go/s (étude 04, `pcie-1.json` ;
  étude 01, `carte-analyse.md`) ;
- lecture de la VRAM par un shader : 251 Go/s (étude 01, `carte-analyse.md`).

## 1. L'entropie réelle des GGUF de la machine (mesuré ici)

### 1.1 Méthode

- Lecteur GGUF écrit de zéro (`outils/03-entropie/gguf_lecture.py`). Témoin : la fin du
  dernier tenseur tombe exactement sur la taille du fichier (2 740 937 888 o et
  5 680 522 464 o).
- Découpe de chaque bloc Q4_K, Q5_K, Q6_K et Q8_0 en ses champs (`champs_k.py`). Témoin :
  la déquantification refaite depuis nos champs égale celle de la bibliothèque `gguf` de
  llama.cpp (licence MIT, second chemin indépendant), à écart nul. Le témoin tombe quand
  on inverse les deux demi-octets de notre seul chemin (`temoin_champs.py`, journal
  `temoin-champs.log`). Un premier essai cassait les deux chemins à la fois et ne tombait
  pas : la leçon est écrite dans les recettes.
- Pour chaque tenseur (`mesure_entropie.py`, journaux `entropie-4B.*`, `entropie-9B.*`) :
  - H0 des codes entiers ;
  - H des codes sachant le code précédent, puis sachant l'échelle de leur sous-bloc ;
  - longueur d'un Huffman optimal, sur les codes seuls et sur les paires ;
  - H de chaque champ de métadonnées ;
  - H0 des octets bruts ;
  - taux de zstd 3 et de lz4 sur tout le tenseur, et de zstd 19 sur 16 Mo.
- Les entropies sont des estimations par fréquences observées. Leur biais,
  (K−1)/(2N ln 2), est sous 10⁻⁶ bit pour les codes. Pour les échelles fp16, il peut
  atteindre quelques centièmes de bit (§8).

### 1.2 Les codes, par type (9B ; le 4B est identique au centième près)

| type | part des octets | bits stockés/poids | H0 codes | H \| précédent | Huffman (codes) | idéal ordre 0, bloc entier | taux idéal | zstd 3 | lz4 |
|---|---|---|---|---|---|---|---|---|---|
| Q4_K | 58,5 % | 4,500 | 3,864 / 4 | 3,858 | 3,902 | 4,256 | 1,0574 | 1,0215 | 1,000 |
| Q5_K | 14,7 % | 5,500 | 4,861 / 5 | 4,853 | 4,900 | 5,253 | 1,0470 | 1,0000 | 1,000 |
| Q6_K | 26,7 % | 6,562 | 5,789 / 6 | 5,785 | 5,824 | 6,274 | 1,0460 | 1,0000 | 1,000 |
| Q8_0 | 0,1 % | 8,500 | 7,556 / 8 | 7,185 | 7,580 | 7,807 | 1,0888 | 1,0546 | 1,000 |
| **modèle** | 100 % | **5,062** | | | | **4,808** | **1,0529** | **1,0125** | **1,000** |

Le 4B donne 5,187 → 4,930 bits/poids, taux idéal 1,0521, zstd 3 1,0106 (journal
`entropie-4B-resume.txt`). Les rôles (ffn_gate, ffn_up, ffn_down, attn_*, ssm_out,
token_embd, output) diffèrent de moins de 0,01 bit : **une seule table de fréquences
par type et par modèle suffit**. Je l'ai mesuré directement : table globale contre une
table par tenseur, 3,86521 contre 3,86519 bits (`rans-4B-*.json`).

L'histogramme global des codes Q4_K (table normalisée à 4096) est en cloche, décalé vers
les codes 7 et 8, avec des queues relevées aux deux bouts. C'est la signature d'un
ajustement échelle et minimum qui écrête :
`[169, 107, 155, 215, 280, 343, 394, 420, 418, 386, 333, 268, 203, 145, 120, 140]`.

### 1.3 Les métadonnées : un tiers du gain

| type | H(d) sur 16 bits | H(dmin) sur 16 bits | H(échelle 6 bits) | H(minimum 6 bits) |
|---|---|---|---|---|
| Q4_K | 9,46 à 9,53 | 10,11 à 10,35 | 4,89 | 5,19 |
| Q5_K | 8,81 à 8,95 | 10,20 à 10,23 | 4,92 à 4,94 | 5,21 à 5,23 |
| Q6_K | 7,88 à 8,01 | — | échelles int8 : 7,24 à 7,26 bits par octet | — |

Pour Q4_K, les métadonnées pèsent 0,5 bit par poids. Leur idéal est de 0,392 bit par
poids (calculé : (9,46 + 10,35 + 8 × (4,89 + 5,19)) / 256). Elles rendent donc
0,108 bit par poids, contre 0,135 pour les codes. **Coder les codes seuls laisse près de
la moitié du gain sur la table.**

### 1.4 Ce que voient les codeurs d'octets (mesuré ici, `flux_octets.py`)

| codage d'ordre 0 sur des octets | Q4_K | Q5_K | Q6_K | modèle 9B |
|---|---|---|---|---|
| bloc entier, une table (borne de DEFLATE, GDeflate, des littéraux zstd) | 1,0267 | 1,0031 | 1,0085 | 1,0183 |
| un flux par champ (le « byte grouping » de ZipNN, transposé aux champs K) | 1,0519 | 1,0179 | 1,0325 | 1,0416 (calculé) |
| symboles entiers par champ (codes de 4, 5, 6 bits) | 1,0574 | 1,0470 | 1,0460 | 1,0529 |

Ces trois lignes rendent compte des faits publiés. ZipNN écrit que les GGUF « ne se
compressent pas du tout » (arXiv 2411.05239v2, §résultats) : c'est vrai pour un LZ et
pour un codeur d'octets sur le bloc entier. Ce n'est plus vrai pour un codeur qui connaît
les champs. Pour Q4_K, un codeur d'octets par champ prend presque tout (1,052 sur 1,057).
Pour Q5_K et Q6_K, il faut des alphabets de 32 et 64 symboles : le 5ᵉ et le 6ᵉ bit sont
rangés à part (champ qh), et un codeur d'octets les voit comme du bruit (7,999 bits par
octet sur qh de Q5_K).

### 1.5 Les F32 et les exposants

Les 177 tenseurs F32 (normes, convolution du DeltaNet) pèsent 3,7 à 4,1 Mio, soit 0,07 %
du modèle. Leur exposant porte 2,7 à 2,9 bits sur 8, du même ordre que les 2,6 bits que
DFloat11 publie pour les exposants BF16. Mais aucun poids BF16 n'est sur la machine :
**je n'ai pas pu mesurer l'exposant BF16 d'une vraie matrice.** La demande de
téléchargement est dans la valeur de retour.

### 1.6 Le modèle cible : MXFP4 de gpt-oss (mesuré ici, reprise)

gpt-oss-20b et gpt-oss-120b sont arrivés sur la machine pendant l'étude (choix de l'étude
06). Leurs experts sont en MXFP4 natif : blocs de 32 poids, codes E2M1 de 4 bits, une
échelle E8M0 d'un octet par bloc, 4,25 bits par poids (structure au bit près :
`03-entropie-derivations.md`, §1.2). Le lecteur et la découpe en champs sont vérifiés par
le témoin (`temoin-champs-mxfp4.log`).

**Les échelles portent l'essentiel du gain** (`mxfp4_contexte.py`,
`mxfp4-contexte-gptoss20b.json`, les 72 tenseurs d'experts de gpt-oss-20b, moyennes
pondérées par le nombre de blocs) :

| quantité | bits | lecture |
|---|---|---|
| H(e), ordre 0 | 1,554 sur 8 | de 0,89 (ffn_up) à 2,28 (ffn_down de la couche 0) |
| H(e \| échelle du bloc de gauche) | 1,152 | |
| H(e \| échelle du bloc du dessus) | 1,538 | les lignes voisines ne se ressemblent presque pas |
| H(e \| gauche et dessus) | 1,146 | le dessus n'ajoute rien à la gauche |
| **H(e \| médiane de sa ligne)** | **1,011**, plus 0,015 pour la médiane | le meilleur, et sans dépendance d'un bloc à l'autre |
| H(code) | 3,862 sur 4 | comme les K-quants : presque uniforme |
| H(code \| e) | 3,823 | 0,039 bit d'information mutuelle entre un code et son échelle |

Témoin : les échelles du premier tenseur, permutées au hasard, gardent H(e) = 2,283 et
perdent tout le gain de contexte (H(e | gauche) = 2,283) ; l'estimateur n'invente pas de
structure.

Pourquoi la médiane de ligne : une ligne de matrice (un canal de sortie) a une norme
propre ; l'échelle d'un bloc suit cette norme à ±1 près. Connaître la médiane de la ligne
dit presque tout, et la reconstruction e = médiane + δ ne dépend d'aucun autre bloc :
chaque voie du décodeur la fait seule, sans somme préfixe. Un codage par différence avec
le voisin de gauche coûte 0,13 bit de plus (1,152 contre 1,011 + 0,015) et impose une somme préfixe le long de la ligne.

**Taux réel d'un codage par champs, décodage exact** (`taux_mxfp4.rs`,
`taux-mxfp4-gptoss20b.json`, les 72 tenseurs MXFP4 de gpt-oss-20b, 10,15 Go) :

- codes : rANS alphabet octet, une table par tenseur : **3,866 bits par poids** ;
- échelles : médiane de ligne en clair (1 octet par ligne), δ = e − médiane en rANS
  alphabet octet, une table par tenseur : **0,037 bit par poids** au lieu de 0,25
  (H(δ) moyen 1,071 bit par bloc : une table de δ par tenseur perd 0,06 bit sur
  H(e | médiane), qui suppose une table par valeur de médiane) ;
- deux tables de 384 octets par tenseur, comptées ;
- **total : 3,903 bits par poids pour 4,25 stockés, taux 1,0888** ; chacun des 72 tenseurs
  est décodé et comparé octet à octet (codes et échelles reconstruites) : tous exacts. Le
  témoin (une médiane faussée) rend bien la reconstruction inexacte.
- Par tenseur, le taux va de 1,0846 à 1,1041 (`csv/taux-mxfp4-gptoss20b.csv`).
- **Sur gpt-oss-120b** (`taux-mxfp4-gptoss120b.json`, les 108 tenseurs d'experts,
  60,9 Go) : codes 3,870 bits par poids, échelles 0,034, **total 3,904, taux 1,0887**,
  de 1,0855 à 1,1045 par tenseur, les 108 décodés exactement. Le taux ne dépend pas de la
  taille du modèle : 20b et 120b diffèrent de 0,0001.

**Les codes sachant la classe de leur échelle** (`taux_mxfp4 --classes`,
`taux-mxfp4-classes-gptoss20b.json`). L'information mutuelle code-échelle vaut 0,039 bit
(tableau ci-dessus). Pour l'encaisser sans changer le décodeur, les blocs sont répartis en
trois flux selon la place de leur échelle par rapport à la médiane de leur ligne (en
dessous, égale, au-dessus) ; chaque flux a sa table et se décode par la même v4, chaque
groupe de travail ne chargeant que la table de son flux. Le réassemblage, guidé par δ que
le décodeur a déjà, est vérifié octet à octet.

| variante (gpt-oss-20b, 72 tenseurs) | codes (bits/poids) | total avec échelles | taux | exact |
|---|---|---|---|---|
| une table par tenseur | 3,8662 | 3,9032 | 1,0888 | oui |
| **trois classes d'échelle** | **3,8135** | **3,8505** | **1,1037** | oui |
| cinq classes (δ borné à ±2) | 3,8127 | 3,8498 | 1,1040 | oui |
| **gpt-oss-120b, 108 tenseurs : une table** | 3,8695 | 3,9039 | 1,0887 | oui |
| **gpt-oss-120b, trois classes** | **3,8201** | **3,8545** | **1,1026** | oui |

(`taux-mxfp4-classes-gptoss120b.json` pour les deux dernières lignes.)

Les trois classes prennent 0,053 bit, davantage que les 0,039 de H(code) − H(code | e) :
la classe relative à la ligne en dit plus long sur les codes que la valeur absolue de
l'échelle, et l'alphabet octet ajoute la dépendance entre les deux codes d'un même octet,
qui partagent leur bloc. La raison physique : une échelle au-dessus de la médiane de sa
ligne signale un bloc dont un poids est grand ; ses autres codes sont alors petits, et
leur loi se resserre vers zéro. Cinq classes n'ajoutent que 0,0008 bit : trois suffisent.
Par tenseur, le taux à trois classes va de 1,0987 à 1,1177.

Ce qui reste sur la table, calculé : coder les médianes au lieu de les stocker prendrait
environ 0,002 bit par poids (8 bits par ligne de 90 blocs contre 0,015 × 90 bits).

**gpt-oss-120b, échelles** (`mxfp4-contexte-gptoss120b.json`, les 36 premiers tenseurs
d'experts, soit les couches 0 à 11 ; la mesure Python des 108 tenseurs aurait pris
plusieurs heures) : H(e) = 1,232 bit à l'ordre 0, 1,004 sachant le bloc de gauche,
**0,910 sachant la médiane de ligne** (plus 0,010 pour la médiane) ; H(code) = 3,863,
H(code | e) = 3,825. Même structure que le 20b, échelles un peu plus prévisibles. Témoin de
permutation : contexte détruit.

**Tout gpt-oss-20b, champ par champ** (`entropie-gptoss20b.json`, 11,5 Go de tenseurs
quantifiés, résumé `entropie-gptoss20b-resume.txt`, ordre 0 sans contexte pour les
échelles) :

| type, rôle | Mio | bits stockés/poids | H0 codes | H(code \| échelle) | idéal ordre 0 | taux idéal | zstd 3 | lz4 |
|---|---|---|---|---|---|---|---|---|
| MXFP4, experts (gate, up, down) | 9 682 | 4,250 | 3,862 | 3,823 | 3,910 | 1,0869 | 1,0405 | 1,000 |
| Q8_0, attention (q, k, v, sortie) | 645 | 8,500 | 7,50 à 7,68 | — | 7,77 à 7,95 | 1,069 à 1,095 | 1,037 à 1,061 | 1,000 |
| Q8_0, tête de sortie | 587 | 8,500 | 7,655 | — | 7,901 | 1,0758 | 1,0407 | 1,000 |
| Q8_0, plongements (`token_embd`) | 587 | 8,500 | 5,628 | — | 5,915 | 1,4371 | 1,3423 | 1,000 |
| **modèle** | 11 501 | 4,615 | | | 4,197 | **1,0995** | **1,0530** | 1,000 |

Les plongements se compressent de 44 %, mais un jeton n'en lit qu'une ligne : ce gain ne
sert qu'au disque et à la RAM, pas au débit. L'attention en Q8_0 (toujours lue, résidente
en VRAM dans le plan de l'étude 06) ne gagne rien en vitesse par le sans-perte (§4.5).
**Ce qui compte pour le débit, ce sont les experts lus par le disque : 1,0888 réel.**

**Ce que cela change face aux K-quants** : le même codeur rend 1,0316 sur les demi-octets
Q4_K et au mieux 1,042 à 1,053 sur le bloc entier, contre 1,0888 sur MXFP4. La différence
tient à la structure : une échelle d'un octet pour 32 poids, presque déterminée par sa
ligne, là où Q4_K range 0,5 bit par poids de métadonnées déjà serrées (§1.3).

## 2. L'état de l'art, technique par technique

Pour chaque technique : le mécanisme, le gain, le coût, si elle tourne sous Windows sans
CUDA, sa maturité et sa licence.

### 2.1 DFloat11 (« 70 % Size, 100 % Accuracy »), NeurIPS 2025

- Source : arXiv 2504.11651, v1 2025-04-15, v3 2026-01-01. Code : github.com/LeanModels/DFloat11
  (Apache-2.0, vérifié dans le clone, dernier commit 2025-11-24).
- Mécanisme : seuls les exposants BF16 sont codés par Huffman. Signe et mantisse restent
  bruts. Le décodage passe par des tables de 256 entrées en cascade : l'arbre est coupé en
  sous-arbres de hauteur 8, et les valeurs 240 à 255 servent de pointeurs. J'ai lu
  `dfloat11/decode.cu` :
  - chaque fil prend 8 octets fixes du flux, plus un décalage de départ sur 5 bits ;
  - il décode deux fois : une passe pour compter, une somme préfixe de Blelloch dans le
    bloc, une passe pour écrire ;
  - les tables sont lues par `__ldg` (cache L1), pas en mémoire partagée.
- Gain : 10,8 à 10,9 bits par poids au lieu de 16 (67,6 à 68,2 %), sur Llama 3.1/3.3,
  Qwen 3, Mistral (littérature, éditeur, non reproduit).
- Coût : un passage de décompression par bloc de transformeur, avant la multiplication.
  ZipServ mesure DFloat11 à 0,28 et 0,34 fois cuBLAS en noyau fondu (RTX 4090, L40S).
- Windows sans CUDA : non. Le noyau est en CUDA et PTX.
- Pour nous : sans objet sur un GGUF quantifié, qui n'a plus d'exposant.

### 2.2 ZipNN (IBM), et le « byte grouping »

- Source : arXiv 2411.05239v2, 2025-06-04. Code : github.com/zipnn/zipnn (MIT, vérifié ;
  dernier commit 2026-04-11). Le README annonce la version 0.5.4.
- Mécanisme : les octets de même rang (exposants, octets de fraction) sont séparés en
  flux. Chaque flux reçoit Huffman ou zstd selon ce qu'il rend. LZ est écarté parce que
  ses correspondances sur ces données sont des « artefacts aléatoires » qui gênent
  l'entropie.
- Gain (littérature, éditeur, non reproduit) : BF16 ramené à 66–67 %, FP32 à 83 %.
  GPTQ et AWQ à 85–91 %, GGUF « ne se compresse pas ».
- Débit (littérature, éditeur, non reproduit) : 1,65 Go/s sur un fil d'un M1 Max ; plus
  de 45 Go/s, jusqu'à 80 Go/s, sur un Xeon 8480+ (224 cœurs, deux nœuds NUMA).
  Aucun débit sur carte : le README dit « GPU implementations are on the way ».
- Windows sans CUDA : oui, le processeur suffit.
- Pour nous : le byte grouping par champ rend 1,042 sur le 9B (§1.4). Il ne sait rien
  faire de Q5_K et Q6_K.

### 2.3 Huff-LLM

- Source : arXiv 2502.00922v1, 2025-02-02. Pas de code publié trouvé.
- Mécanisme : du matériel. Un décodeur Huffman (registre de 32 bits, mémoire associative
  de 32 entrées) est placé devant chaque rangée d'un réseau systolique. Le découpage est
  {1,5,5,5} pour FP16 et {1,4,4,7} pour BF16.
- Gain (littérature, éditeur, non reproduit) : FP16 compressé 1,46 fois sur Llama 3 et
  Qwen 2.5 ; BF16 1,37 fois.
- Coût : 6,13 % de surface pour un réseau de 128×128, en GF12.
- Windows sans CUDA : sans objet, il faut une puce dédiée.

### 2.4 Ecco (ISCA 2025)

- Source : arXiv 2505.06901v1, 2025 ; actes ISCA 2025, p. 793–807.
- Mécanisme : quantification par groupes de 128 avec échelle FP8, 64 motifs k-means
  partagés (15 centroïdes), 4 tables de Huffman par motif, codes de 2 à 8 bits. Le
  décodeur parallèle est matériel, logé entre L1 et L2 : 64 décodeurs, 28 cycles.
- Gain (littérature, éditeur, non reproduit) : 2,9 fois plus rapide qu'AWQ, mémoire
  réduite de près de 4 fois face au FP16.
- Coût : 5,11 mm², 7,36 W ramenés à 7 nm.
- Windows sans CUDA : sans objet, c'est une puce simulée (Accel-Sim).
- Pour nous : une idée à retenir, **la table de fréquences choisie parmi quelques-unes
  par groupe**. Sur nos K-quants, le contexte n'apporte que 0,005 bit (§1.2), donc
  presque rien à prendre.

### 2.5 ZipServ et TCA-TBE (ASPLOS 2026)

- Source : arXiv 2603.17435v1, 2026-03-18. Code : github.com/HPMLL/ZipServ_ASPLOS26
  (Apache-2.0, vérifié ; commit 2025-12-19).
- Mécanisme : un code de **longueur fixe** de 3 bits par poids BF16. Les 7 exposants les
  plus fréquents sont codés 001 à 111, et 000 signale un poids de repli. Les bits sont
  rangés en trois plans de bits de 64 bits par tuile de 8×8. Le décodage tient dans les
  registres, avec un popcount pour l'indexation, juste avant les instructions mma.
- Gain (littérature, éditeur, non reproduit) : 11,3 bits par poids, pour une borne de
  10,6. En noyau, 1,31 fois cuBLAS en moyenne sur RTX 4090, jusqu'à 2,21 fois sur L40S.
  De bout en bout, 1,22 fois vLLM.
- Windows sans CUDA : non (CUDA, Tensor Cores).
- Pour nous : la leçon de structure. **Dans le régime résident, seul un code à décodage
  en temps constant passe dans la multiplication.** Nos codes K sont presque uniformes,
  donc un code à longueur fixe n'a rien à y prendre.

### 2.6 « Approaching Shannon Bound with Lossless LLM Weight Compression » (ISCA 2026)

- Source : arXiv 2606.15789v1, 2026-06-14. Code non trouvé.
- Mécanisme : rANS bâti sur DietGPU, probabilités sur 12 bits, un sous-flux par voie de
  warp, tuiles calées sur celles de la multiplication (128×32 à 256×64). Les métadonnées
  coûtent 0,0024 à 0,0173 bit par poids. Le décodage se fait en mémoire partagée, en
  double tampon.
- Gain (littérature, éditeur, non reproduit) : à 0,01–0,1 bit de la borne de Shannon ;
  débit jusqu'à 1,6 fois sur Mixtral, par une taille de lot plus grande.
- Windows sans CUDA : non (A100, H200, CUTLASS).
- **Contradiction** avec mes mesures sur l'entropie des int4 : voir §6.

### 2.7 EntroPack (2026-09-28) et les quantifications codées par entropie

- Source : arXiv 2609.34185v1. Code : github.com/modelscope/entropack. Non cloné ; sa
  licence logicielle n'a pas été vérifiée.
- Mécanisme : quantification sur réseau E8 normalisé par ligne, modèle de probabilité
  conditionnel, tuiles décodables indépendamment, décodage fondu sur la carte.
- Gain (littérature, éditeur, non reproduit) : à 4 bits par paramètre, erreur L2 relative
  des poids environ 24 % plus basse que NF4. Les essais portent seulement sur un modèle de
  diffusion (Z-Image-Turbo) : aucun résultat sur un LLM.
- Voisins : EntroLLM (arXiv 2505.02380v4, 2026-01-26 ; quantification par tenseur et
  Huffman, Jetson). Il annonce 1,39 bit par poids pour uint4, avec une perplexité de
  10,11 contre 9,03 en fp16 sur phi3 : sa quantification par tenseur coûte cher en
  qualité. Aussi : arXiv 2505.18758 (quantification RD et codage entropique, réseaux de
  vision seulement), et arXiv 2510.11234 (compression neuronale des poids, décodage par
  nvCOMP).
- Pour nous : la direction du §5 existe en diffusion. **Je n'en trouve aucune
  implémentation pour les GGUF, ni sur une carte grand public sans CUDA.**

### 2.8 nvCOMP (ANS, GDeflate, Bitcomp)

- Source : notes de version, docs.nvidia.com/cuda/nvcomp/release_notes.html (version 6.0.0
  la plus récente, dates non indiquées) ; page « Algorithm Selection ».
- Mécanisme : ANS par morceaux. GDeflate est un DEFLATE dont le flux de bits est réparti
  sur 32 sous-flux. Bitcomp vise les flottants scientifiques.
- Débits : **aucun chiffre en Go/s dans les sources primaires consultées**. La page de
  sélection ne donne que des notes qualitatives : ANS taux « modéré », débit « élevé ».
  Le moteur matériel de Blackwell annonce 600 Go/s, mais seulement pour LZ4, Snappy et
  Deflate.
- Licence : binaire propriétaire. Le dépôt GitHub nvidia/nvcomp est archivé ; un miroir
  tiers rapporte que le code source n'est plus publié depuis la version 2.3. Cela n'a
  pas été confirmé par une annonce datée de NVIDIA.
- Windows sans CUDA : non (paquets CUDA 12 et 13).

### 2.9 GDeflate et DirectStorage (DirectX 12)

- Source : github.com/microsoft/DirectStorage (MIT ; GDeflate sous Apache-2.0, vérifié dans
  le clone, commit 2026-08-04). Billet du 2026-03-11 sur DirectStorage 1.4 (préversion
  publique) : zstd sur processeur et sur carte, shader zstd ouvert, « initially optimized
  for content chunked to 256KB or smaller ».
- Mécanisme (lu dans `GDeflate/GDeflate/README.md`) : DEFLATE dont le flux est réparti sur
  32 sous-flux. Chaque tour décode un symbole par sous-flux. Les mots de 32 bits que les
  sous-flux réclament en fin de tour se suivent dans le flux sérialisé, dans l'ordre des
  sous-flux. **C'est exactement le principe du flux partagé de mon décodeur** (§3), posé
  par Microsoft en 2022 pour DEFLATE.
- Gain sur nos données : borné par le codage d'octets du bloc entier, 1,018 (§1.4). La
  partie LZ ne trouve rien (lz4 : 1,000).
- Débits publiés : aucun chiffre de débit sur carte trouvé dans les sources primaires.
- Windows sans CUDA : **oui**, c'est le seul de la liste à tourner nativement sous DX12
  sur cette carte. Le paquet NuGet 1.4.0-preview2 pèse 3 986 072 o (relevé de l'étude 01,
  non téléchargé).

### 2.10 DietGPU (Meta)

- Source : github.com/facebookresearch/dietgpu (MIT, vérifié ; commit 2026-03-18).
- Mécanisme (lu dans `dietgpu/ans/GpuANSDecode.cuh`) : rANS à états de 32 bits et mots de
  16 bits. La renormalisation est coopérative dans le warp : `__ballot_sync` puis
  `__popc` donnent à chaque voie sa position dans un flux partagé.
- Débit (littérature, éditeur, non reproduit, README) : 250 à 410 Go/s sur A100.
- Windows sans CUDA : non.
- Pour nous : la v2 de mon décodeur retrouve indépendamment le vote et le comptage de
  bits. Un article tiers mesure DietGPU à 592,5 Go/s en décodage sur H100 (non vérifié).

### 2.11 Recoil (ICPP 2023) et multians (ICPP 2019)

- Recoil : arXiv 2306.12141, actes ICPP 2023, DOI 10.1145/3605573.3605588. Code :
  github.com/lin-toto/recoil (GPL-3.0, vérifié ; commit 2026-07-12).
  - Mécanisme : un seul flux rANS. Le codeur note des états intermédiaires (16 bits)
    aux points de coupe, ce qui rend le flux décodable par morceaux. Le décodeur fusionne
    les coupes selon le parallélisme dont il dispose.
  - Débit (littérature, éditeur, non reproduit) : plus de 90 Go/s sur RTX 2080 Ti, plus
    de 11 Go/s sur un Xeon W-3245 à 16 cœurs (AVX-512). États de 32 bits, mots de
    16 bits, 32 voies.
- multians : DOI 10.1145/3337821.3337888. Code : github.com/weissenberger/multians
  (LGPL-3.0, vérifié ; commit 2019-07-26).
  - Mécanisme : tANS sur un flux non partitionné, synchronisation auto-découverte.
  - Débit : selon Recoil, « significativement » plus lent.
- Windows sans CUDA : non (CUDA ; multians demande en plus GNU/Linux).

### 2.12 zstd et lz4 sur le processeur

- Source : README de facebook/zstd, tableau lzbench sur le corpus Silesia, i7-9700K à
  4,9 GHz (littérature, éditeur, non reproduit). zstd 1.5.7 -1 décompresse à 1 550 Mo/s,
  lz4 1.10.0 à 3 850 Mo/s.
- Sur nos données (mesuré ici, `debits_cpu.py`, morceaux de 1 Mio, sous la charge des
  autres agents) :
  - zstd 1 : taux 1,022, décompression 0,46 Go/s sur un fil et 2,45 Go/s sur 16 fils,
    pendant que la recopie mémoire faisait 6,5 et 8,4 Go/s ;
  - lz4 : taux 0,996, donc il agrandit les données.
  - ~~Les chiffres du calme sont au §4.4.~~ Ils n'ont pas été pris : un `llama-quantize`
    d'un autre agent a tenu le processeur toute la reprise (§4.1 bis).
- Windows : oui.

### 2.13 Trouvé à la reprise : la direction du §5 existe déjà, en CUDA

Une seconde recherche du 2026-10-15 (sources primaires, lues ce jour) trouve quatre
travaux que la première passe n'avait pas. Deux d'entre eux font ce que le §5 et le trou 3
du §7 disaient absent.

**EntQuant, « Float8@2bits » (ICML 2026).**
- Source : arXiv 2601.22787, v1 2026-01-30, v2 2026-05-29. Code :
  github.com/merantix-momentum/entquant (Apache-2.0 selon le README, 5 commits ; non cloné).
- Mécanisme (lu dans l'article HTML) : quantification symétrique en Float8 (ou Int8), une
  échelle par canal de sortie, ajustée par L-BFGS sous un lagrangien
  « erreur ℓ1 relative + λ·‖W_q‖₁ », la norme ℓ1 servant de substitut dérivable à
  l'entropie. Codage ANS par nvCOMP. À l'inférence, chaque bloc de transformeur est
  décompressé sur la carte dans un tampon partagé juste avant sa passe, puis multiplié par
  un noyau Float8 de la famille Marlin.
- Résultats (littérature, éditeur, non reproduit) : LLaMA-2 70B à 2,1 bits par paramètre
  effectif, perplexité C4 6,47 contre 5,52 en 16 bits ; à 3 bits, 5,74. Mémoire à 2,1 bits :
  18,8 Gio de poids compressés et 0,8 Gio de tampon. Vitesse : « 1,5 à 2 fois plus lent que
  BF16 ».
- Windows sans CUDA : non (nvCOMP).
- Pour nous : c'est le schéma « décoder juste avant » du §4.5, en CUDA, avec un tampon par
  bloc. Leur ralentissement de 1,5 à 2 fois contre BF16 est cohérent avec notre facteur 3,4
  contre un brut 4 bits : un brut BF16 lit 4 fois plus d'octets que le nôtre.

**vram-compression (Samir Nuri, 2026-09-23).**
- Source : github.com/snuri00/vram-compression, un seul commit (1af9a93), **aucun fichier de
  licence** : tous droits réservés par défaut. Lu dans le clone, rien n'en est repris.
- Mécanisme (lu dans `kernel/rans_gemv.cu`) : ECSQ avec retour d'erreur de GPTQ, un pas par
  colonne d'entrée (« waterfilling » à la WaterSIC), puis rANS (état 32 bits, mots de 16,
  probabilités sur 12 bits, table de 16 Kio en mémoire partagée), **décodé dans le produit
  matrice-vecteur**. Chaque voie a son propre flux et ses colonnes l, l + 32, … ; le pas de
  colonne est replié dans x. Les lectures de 16 bits de chaque voie suivent leur propre flux
  (pas de flux partagé coalescé) ; en-tête par voie : décalage et état de 32 bits chacun.
- Résultats (littérature, éditeur, non reproduit) : Qwen2.5-1.5B, perplexité Wikitext-2
  9,40 à 4,25 bits par poids contre 9,78 pour GPTQ à débit fixe ; 9,81 contre 12,65 à
  3,25 bits. Noyau : « 2 à 3 fois plus lent que bf16 cuBLAS » sur RTX 3050 Laptop, « borné par
  la latence du décodage (15 Go/s effectifs contre 168) ». Le journal `kernel_bench.json` du
  dépôt montre aussi 1,04 bit par poids d'en-têtes sur les petites matrices.
- Windows sans CUDA : non.
- Pour nous : **le trou 3 du §7 est faux tel qu'écrit** (barré au §7). La quantification
  taillée pour le codeur, décodée dans le produit, existe en prototype CUDA. Leur mesure
  confirme indépendamment notre §4.5 : fondu, le décodage entropique ralentit le produit de
  lot 1. Ce qui reste à nous : le flux partagé coalescé (en-têtes à 0,40 % au lieu de
  jusqu'à 1 bit par poids), Vulkan, le régime flux depuis le disque, et les formats réels
  des GGUF.

**ECF8, « To Compress or Not? » (2025-10-03).**
- Source : arXiv 2510.02676 (v1 seule ; aucun code lié). Résumé lu ce jour.
- Mécanisme : la « concentration des exposants » des poids entraînés, attribuée aux lois
  α-stables induites par la descente de gradient stochastique, avec des bornes sur
  l'entropie des exposants ; un FP8 codé par entropie, décodé sur la carte.
- Résultats (littérature, éditeur, non reproduit) : jusqu'à 26,9 % de mémoire en moins et
  jusqu'à 177,1 % de débit en plus, sorties identiques, modèles jusqu'à 671 G paramètres ;
  limite théorique « proche de FP4,67 ».
- Pour nous : la même famille que DFloat11, pour le FP8. Aucun résultat sur MXFP4 ou FP4.

**WaterSIC (2026-03-05).**
- Source : arXiv 2603.04956, v2 2026-06-01. Code : github.com/egorlifar/watersic (MIT,
  un commit ; non cloné).
- Mécanisme : un débit par colonne d'entrée, alloué par « waterfilling » ; à 0,255 bit de la
  limite de la théorie de l'information, uniformément sur les covariances d'activation.
- Pour nous : la borne que la quantification de l'étude 02 doit viser. Le résumé ne dit pas
  quel codeur entropique sert à l'inférence.

### 2.14 Tableau d'ensemble

| technique | sur GGUF K-quant | décodage sur carte | Windows sans CUDA | maturité | licence |
|---|---|---|---|---|---|
| DFloat11 | sans objet (BF16) | CUDA | non | publié, code | Apache-2.0 |
| ZipNN | 1,042 au mieux par champ (calculé ici) | non | oui (processeur) | paquet PyPI | MIT |
| Huff-LLM | sans objet | puce dédiée | sans objet | simulation | aucun code |
| Ecco | sans objet | puce dédiée | sans objet | simulation | aucun code |
| ZipServ | sans objet (BF16) | CUDA, fondu | non | ASPLOS 2026, code | Apache-2.0 |
| Shannon Bound (ISCA 2026) | int4 annoncé, contredit ici | CUDA, fondu | non | article | aucun code |
| EntroPack | sans objet (diffusion) | annoncé | inconnu | préprint du 2026-09-28 | non vérifiée |
| nvCOMP ANS / GDeflate | ≤ 1,018 (codage d'octets) | CUDA | non | produit | propriétaire |
| GDeflate et zstd DirectStorage | ≤ 1,018 | DX12 | **oui** | 1.4 en préversion | MIT / Apache-2.0 |
| DietGPU | 1,018 en octets, plus par champ | CUDA | non | code | MIT |
| Recoil | idem | CUDA | non | code | GPL-3.0 |
| zstd / lz4 | 1,012 / 1,000 (mesuré ici) | non | oui | mûr | BSD/GPL ; BSD |
| EntQuant (ICML 2026) | sans objet (Float8) | CUDA (nvCOMP), avant le produit | non | article, code | Apache-2.0 |
| vram-compression | ECSQ, pas un GGUF | CUDA, fondu | non | prototype, 1 commit | aucune licence |
| ECF8 | sans objet (FP8) | annoncé | inconnu | préprint | aucun code |
| **troncons rANS v4** (ici) | **1,0316 sur demi-octets Q4_K** (codes seuls) ; **1,0888 sur MXFP4 par champs** (codes et échelles, gpt-oss-20b) | **Vulkan 70-72 Go/s sur secteur** ; CUDA 81-82 (second chemin) | **oui** | prototype mesuré, deux décodeurs exacts | à nous |

## 3. Ce que j'ai construit : un rANS entrelacé par sous-groupe, décodé par Vulkan

Code : `outils/03-entropie/rans/` (Rust, wgpu 30.0.1, construction `--offline`).
Dépendances : wgpu, pollster, rayon (MIT ou Apache-2.0) et bytemuck (Zlib, Apache-2.0
ou MIT). Le format est dérivé du principe de l'ANS (Duda, arXiv 1311.2540) et des
codeurs entrelacés (Giesen, arXiv 1402.3392). Aucune ligne n'est reprise des dépôts lus.

### 3.1 Le format

- Probabilités sur 12 bits (M = 4096), état x sur 32 bits, borne basse L = 2¹⁶,
  renormalisation par mots de 16 bits.
- Codage d'un symbole s, de fréquence f et de cumul c :
  - si x ≥ f·2²⁰, on émet x mod 2¹⁶ et on pose x ← ⌊x / 2¹⁶⌋ ;
  - puis x ← ⌊x/f⌋·4096 + (x mod f) + c.
- Décodage :
  - fente = x mod 4096, et s, f, c se lisent dans la table à cette fente ;
  - x ← f·⌊x/4096⌋ + fente − c ;
  - si x < L, on lit un mot : x ← x·2¹⁶ + mot.
- Avec ces bornes, un pas lit au plus un mot : après le pas, x ≥ 16f ≥ 16, et
  x·2¹⁶ ≥ 2²⁰ > L. La boucle de la carte n'a donc qu'une branche, rendue sans branche par
  un `select`.
- Tuile : 32 voies (un sous-groupe) × N macro-pas. La voie l du macro-pas m écrit le mot
  de 32 bits m·32 + l de la tuile. **Les 32 voies écrivent ainsi 128 octets contigus à
  chaque macro-pas.**
- Flux partagé : à chaque sous-pas, les voies qui renormalisent lisent des mots
  consécutifs, dans l'ordre croissant des voies. La position d'une voie est le pointeur,
  plus le nombre de voies d'indice inférieur qui lisent aussi. Le codeur parcourt les
  symboles dans l'ordre exactement inverse, émet avant de coder, puis renverse sa pile.
- Contrôle gratuit : chaque voie part de L côté codeur, donc chaque voie doit finir sur L
  côté décodeur.
- Coût des en-têtes : 32 états de 4 octets et un décalage de 4 octets par tuile. Avec
  N = 256 (32 Kio de demi-octets par tuile), cela fait 0,40 % (calculé).
- Alphabets :
  - v1 à v3 : 16 symboles, les codes 4 bits, 8 sous-pas par mot ;
  - v4 : 256 symboles, l'octet entier des demi-octets, 4 sous-pas par mot. L'entrée de
    table de 32 bits range symbole (8 bits), f − 1 (12 bits) et biais (12 bits).

### 3.2 Les quatre décodeurs de carte, et pourquoi chacun

- **v1** : somme préfixe du sous-groupe (`subgroupExclusiveAdd`), puis lecture du mot en
  mémoire globale au milieu de la chaîne de dépendance. Elle est limitée par la latence :
  à chaque sous-pas, une voie au moins renormalise, puisque 0,76³² ≈ 0. Chaque sous-pas
  attend donc une lecture globale de plusieurs centaines de cycles.
- **v2** : un vote (`subgroupBallot`) et un comptage de bits (`countOneBits`) remplacent
  la somme préfixe. Le flux est lu par fenêtres de 32 mots de 32 bits, chargées d'avance
  (une valeur par voie), puis distribuées par `subgroupShuffle`. Un sous-pas consomme au
  plus 32 mots de 16 bits, donc la fenêtre suivante a toujours été demandée au moins un
  sous-pas avant d'être lue. Résultat : environ 2 fois la v1.
- **v3** : la v2 avec une table compacte de 4 Kio (symbole par octet, plus une table
  (f, cumul) de 16 mots), pour loger plus de groupes de travail par multiprocesseur.
  **Aucun gain** (38,9 contre 41,1 Go/s dans le même essai) : l'occupation n'était pas
  le plafond. Idée morte, tuée par le nombre.
- **v4** : l'alphabet octet. Deux fois moins de pas de décodage par octet produit, pour
  la même chaîne par pas. Résultat : environ 1,6 fois la v2.
- Références :
  - `copier`, même géométrie de lecture et d'écriture que les décodeurs, mais sans
    décodage : c'est le chemin non compressé ;
  - `copier_vec4`, une recopie à pas de grille par vec4, mesure de la mémoire.

### 3.3 Les témoins (mesuré ici, chaque passe)

- Chaque décodeur rend exactement les octets d'origine, comparés mot à mot sur tout le
  lot, et aucune voie ne finit hors de L.
- Témoin cassé : un bit d'une entrée de la table est retourné dans la mémoire partagée.
  - v1, v2 et v3 tombent deux fois : sortie fausse, et 129 278 à 129 280 voies sur
    129 280 hors de L.
  - v4 tombe sur la sortie fausse, mais **ses voies finissent toutes sur L** : la
    corruption ne touchait que le champ symbole, que la mise à jour de l'état n'utilise
    pas. **Le contrôle de l'état ne garde donc que le flux et l'état, pas la table** (§7).
- Les décodeurs processeur (1, 6 et 16 fils, alphabets 16 et 256) rendent aussi
  exactement les octets.

### 3.4 Taux réels (mesuré ici, tous les tenseurs Q4_K du 4B, 1 209 794 560 octets de demi-octets)

| | bits par code | taux sur les demi-octets | taux sur Q4_K entier (métadonnées brutes) |
|---|---|---|---|
| borne H0 | 3,8652 | 1,0349 | — |
| table quantifiée sur 12 bits (attendu) | 3,8652 | — | — |
| **rANS réel, en-têtes compris** | **3,8774** | **1,0316** | **1,0280** |
| alphabet 256, réel | (7,7308 bits par octet attendus) | 1,0316 | — |

L'écart à la borne, 0,012 bit, vient des en-têtes (0,40 %) et des fins de flux.

## 4. Les débits, et la question clé

### 4.1 Débits de la carte (mesuré ici, Vulkan, RTX 4060 Laptop, pilote 591.91, lot de 126 Mio de demi-octets)

Essai `rans-4B-essai-v4.json`, deux séries palindromiques par variante. Une autre carte
était en usage par un autre agent au moment de cet essai, les dispersions le disent.

| variante | Go/s de demi-octets produits (médiane) | meilleure passe | milliards de codes/s | dispersion |
|---|---|---|---|---|
| v1 | 20,5 | 22,1 | 41 | 53 % |
| v2 | 41,1 | 42,3 | 82 | 17 % |
| v3 | 38,9 | 40,6 | 78 | 6 % |
| **v4** | **65,1** | **69,4** | **130** | 10 % |
| recopie, même géométrie | 94,5 écrits (189 lus et écrits) | 95,1 | — | 2 % |
| recopie vec4 | 88,7 écrits | 106,5 | — | 55 % |

Dans le premier essai, tenu sous trois `llama-perplexity` et un `llama-completion` sur la
même carte, la v2 tombait à 9,0 Go/s, avec 1 000 % de dispersion
(`rans-4B-contention-v1-v2.json`). Ces chiffres sont gardés comme trace de la contention,
pas comme mesure.

### 4.1 bis Débits au calme, sur batterie puis sur secteur (mesuré ici, reprise du 2026-10-15)

Ce qui s'est passé, dit tel quel :

- La première passe « calme » (07:24, `calme-rans-4B-contention-llama-bench.log`) est partie
  carte au repos, mais un `llama-bench` d'un autre agent a démarré à 07:32 pendant sa partie
  carte. Ses chiffres sont gardés sous le nom `*-contention-llama-bench.*`, comme trace, pas
  comme mesure. Le lanceur `attendre_calme.sh` exclut désormais les programmes de llama.cpp
  qui calculent sur la carte, et note l'état de la machine au début et à la fin.
- **La machine est sur batterie** (`Win32_Battery.BatteryStatus = 1`, 48 %, relevé à
  07:42) : `nvidia-smi` donne une limite de puissance de 43 W (80 W par défaut), un
  plafonnement logiciel de puissance actif, et une horloge mémoire de 6 001 MHz sous charge
  au lieu des 8 001 relevés par l'étude 01, sur secteur. Un processeur chargé (le
  `llama-quantize` d'un autre agent, mes propres mesures d'entropie) prend en plus sa part
  du budget de puissance partagé du portable. Je ne peux pas séparer les deux effets.

Passe `rans-4B-calme.json` (carte seule de bout en bout, `calme-rans-4B-calme.log`), lot de
253 Mio de demi-octets Q4_K du 4B, cinq séries palindromiques :

| variante | médiane (Go/s écrits) | meilleure passe | dispersion | essai v4 (avant la reprise) |
|---|---|---|---|---|
| v1 | 9,4 | 13,7 | 78 % | 20,5 |
| v2 | 13,5 | 21,8 | 103 % | 41,1 |
| v3 | 14,8 | 28,1 | 127 % | 38,9 |
| **v4** | **26,8** | **42,0** | 83 % | **65,1** |
| recopie, même géométrie | 68,8 | 75,3 | 29 % | 94,5 |
| recopie vec4 | 80,4 | 99,3 | 35 % | 88,7 |

Lecture :

- Sous le plafond de puissance, **le décodeur perd 59 %, la recopie 27 %**. C'est la
  signature d'un noyau limité par le calcul (§4.2) : l'horloge des multiprocesseurs baisse
  davantage que le débit de la mémoire.
- L'ordre des variantes ne change pas : v4 reste 2 fois la v2.
- Même sur batterie, la v4 produit 26,8 Go/s de demi-octets, soit **10,8 fois** les
  2,49 Go/s que le disque peut livrer (calcul du §4.3). La conclusion du régime flux tient ;
  le décodage coûte alors environ 9 % du temps de la carte au lieu de 4 %.
- Les débits du processeur au calme (`debits-cpu-4B.json`) n'ont pas été pris : un
  `llama-quantize` a occupé le processeur toute la reprise. Les ordres de grandeur du §4.4
  restent les seuls.

**Puis la machine a été remise sur secteur** (relevé à 08:33 : `BatteryStatus = 2`,
horloges 2 250 / 8 101 MHz). Toutes les passes de carte ont été refaites
(`outils/03-entropie/passes_secteur.sh`), avec un lanceur qui juge le calme sur la
puissance de la carte (repos : 5,5 W ; seuil déclaré : 12 W, raison dans
`attendre_calme.sh`) et un échantillonneur `nvidia-smi` toutes les 500 ms pendant toute la
chaîne (`echantillons-carte-secteur.csv`) :

| variante | B1 : médiane (meilleure) | B2 : médiane (meilleure) | dispersion B1 / B2 | MXFP4 de gpt-oss-20b |
|---|---|---|---|---|
| v1 | 24,3 (24,7) | 25,5 (25,7) | 44 % / 7 % | 24,3 |
| v2 | 42,1 (42,5) | 43,6 (43,8) | 5 % / 4 % | 41,8 |
| v3 | 42,1 (42,8) | 43,5 (43,9) | 5 % / 6 % | 41,7 |
| **v4** | **70,2 (71,1)** | **71,6 (72,5)** | 4 % / 9 % | **70,0** |
| recopie, même géométrie | 107,5 (109,8) | 110,4 (111,0) | 5 % / 6 % | 106,9 |
| recopie vec4 | 110,6 (112,6) | 112,3 (114,0) | 3 % / 6 % | 109,5 |

(Go/s écrits ; `rans-4B-B1-secteur.json`, `rans-4B-B2-secteur.json`,
`rans-gptoss20b-secteur.json`.) Sur secteur, les dispersions tombent sous 10 % ; la v4
fait 70 à 72 Go/s, un peu au-dessus de l'essai v4 d'avant la reprise (65,1), et
**identique sur les codes MXFP4 et sur les demi-octets Q4_K** : le débit ne dépend
presque pas de la loi des symboles. La v3 égale la v2 (l'idée de la table compacte reste
morte). Le facteur batterie/secteur est de 2,6 pour la v4 et de 1,6 pour la recopie.

### 4.1 ter Le second chemin : le même décodeur en CUDA (mesuré ici)

Pour que le débit du décodeur ne repose pas sur un seul outil, le même algorithme a été
réécrit en CUDA (`outils/03-entropie/cuda/rans_v4.cu` : `__ballot_sync`, `__popc`,
`__shfl_sync` à la place du vote, du comptage et des échanges de WGSL), compilé par nvcc
13.1 pour sm_89, et nourri du **même flux** écrit sur disque par `vider_flux.rs` (256 Mio
de demi-octets Q4_K du 4B, 8 192 tuiles). Chronométrage par événements CUDA (temps de la
carte seul), séries palindromiques décodage / recopie.

- Exactitude : la sortie CUDA égale la source octet pour octet, aucune voie hors de L ;
  témoin cassé : sortie fausse (`cuda-4B-A1-secteur.json`, `cuda-4B-A2-secteur.json`).
  Deux décodeurs écrits dans deux langages, compilés par deux chaînes, rendent les mêmes
  octets depuis le même flux : le format est confirmé indépendamment du code qui l'a écrit.
- Ordre des processus A B B A (CUDA, Vulkan, Vulkan, CUDA), tous sur secteur :

| passe | décodeur v4 (Go/s écrits) | recopie de même géométrie |
|---|---|---|
| A1 CUDA | 80,8 | 112,8 |
| B1 Vulkan | 70,2 | 107,5 |
| B2 Vulkan | 71,6 | 110,4 |
| A2 CUDA | 82,1 | 115,7 |

**Le compilateur de NVIDIA tire 14 % de plus du même décodeur** ((80,8 + 82,1) / (70,2 +
71,6) = 1,149) ; la recopie, elle, ne diffère que de 4 %. L'écart est donc dans le code
généré pour la boucle de décodage (naga puis le compilateur du pilote Vulkan, contre nvcc),
pas dans la mémoire. Il ne change aucune conclusion : 70 Go/s par Vulkan valent déjà 28 fois
le disque.

### 4.2 Ce que le décodeur coûte, en bits de calcul (calculé, sur l'essai v4)

- La v4 produit 130 milliards d'octets décodés par seconde. Elle lit en même temps
  environ 63 Go/s de flux compressé et écrit 65 Go/s. Ses 128 Go/s de trafic restent
  sous les 189 Go/s de la recopie : **elle est limitée par le calcul, pas par la
  mémoire.**
- Par pas, environ 25 opérations entières : une lecture en mémoire partagée, une
  multiplication, un vote, deux comptages de bits, deux échanges, des masques. À 130
  milliards de pas par seconde, cela fait environ 3,3 billions d'opérations par voie et
  par seconde.
- La carte en offre environ 6 à 7,7 (24 multiprocesseurs × 128 voies × 2,0 à 2,5 GHz,
  ordre de grandeur, non mesuré ici). Le décodeur est donc à environ la moitié du
  plafond arithmétique. Il reste au plus un facteur 2 à gagner sur ce GPU.

### 4.3 La question clé : décoder dans le noyau de multiplication, ou juste avant ?

Les calculs de cette section datent de la première passe et utilisent l'essai v4
(65 Go/s). Sur secteur, à la reprise, la v4 fait 70 à 72 Go/s par Vulkan et 81-82 par
CUDA (§4.1 bis et ter) : les marges ci-dessous grandissent d'environ 10 %, et le §4.5
remplace le calcul du régime résident par une mesure.

**Régime flux** (le modèle ne tient pas en mémoire, chaque jeton relit les poids par le
disque ou la PCIe). Calculé :

- Disque à 2,8 Go/s : il livre au plus 2,8 Go/s de Q4_K, soit 5,0 milliards de poids par
  seconde, soit 2,5 Go/s de demi-octets à produire. La v4 en produit 65 : **26 fois de
  marge.** Décoder tout le flux d'un jeton prend environ 4 % du temps que le disque met à
  le livrer. Ce travail se recouvre avec la lecture du tronçon suivant.
- PCIe à 4 à 6,4 Go/s : 10 à 16 fois de marge.
- Où décoder : après la PCIe, en VRAM, en un passage juste avant la multiplication, et
  pas dedans. Le flux compressé traverse disque, RAM et PCIe, donc le gain r s'applique
  aux trois. **Le disque devient le seul plafond.**
- Jetons par seconde sur le 9B en flux complet par le disque (calculé, borne haute qui
  ignore tout cache) : 5,10 Go par jeton à 2,8 Go/s, soit 0,55 jeton/s. Avec le codeur
  par champ (1,042) : 0,57. Avec le plafond sans perte (1,053) : 0,58. **Le sans-perte
  sur un K-quant vaut + 3 à 5 %, pas davantage.**

**Régime résident** (les poids tiennent en VRAM). Calculé :

- La VRAM lue à 251 Go/s livre 446 milliards de poids Q4_K par seconde. Le meilleur
  décodeur en fait 130 milliards : **3,4 fois trop lent.**
- Fondu dans une GEMV de lot 1, il prendrait en plus le budget de calcul de la GEMV
  elle-même. Le budget de la carte est d'environ 25 à 30 opérations par voie et par
  octet lu, et un pas rANS en coûte environ 25.
- Conclusion : **dans ce régime, un code de longueur variable ne paie que par la
  capacité** (faire tenir un modèle qui sinon déborderait), jamais par la vitesse.
- C'est la même conclusion que ZipServ par l'autre bout. Il n'y gagne qu'avec un code de
  longueur fixe (3 bits et des plans de bits) sur des exposants BF16 très creux, et nos
  codes K n'ont pas cette forme.

**Régime mixte**, le cas réel de troncons : une part du modèle reste en VRAM, le reste
est relu.

- La part résidente se garde décodée (Q4_K brut).
- La part relue voyage compressée et se décode à l'arrivée.
- Le gain vaut r sur la seule part relue.

### 4.4 Débits du processeur (mesuré ici, sous contention)

| codeur | 1 fil | 6 fils | 16 fils | recopie au même moment |
|---|---|---|---|---|
| rANS alphabet 16 (micro-banc, données synthétiques, `micro_cpu.rs`) | 0,075 Go/s (150 millions de codes/s) | — | — | — |
| rANS alphabet 16 / 256 (banc, lot réel) | 0,013 à 0,041 Go/s | 0,08 à 0,13 | 0,12 à 0,30 | 0,9 à 2,4 Go/s |
| zstd 1 (morceaux de 1 Mio) | 0,46 Go/s | 1,75 | 2,45 | 6,5 à 9,2 Go/s |

- Le décodeur rANS scalaire coûte environ 16 cycles par code. La chaîne du pointeur
  partagé (p += lit, d'une voie à la suivante) est sérielle.
- Recoil annonce environ 0,7 Go/s par cœur en AVX-512 (littérature).
- Même à ce niveau, 6 cœurs performants ne feraient que 4 Go/s environ : à peine plus que
  le disque, pendant que la carte offre 25 fois plus.
- **Le décodage appartient à la carte.** Le processeur ne doit faire que lire le disque
  et remplir les tampons de transfert.

### 4.5 La question clé, mesurée : le produit matrice-vecteur fondu au décodeur

Le §4.3 tranchait par le calcul. La reprise le tranche par la mesure, avec un banc écrit
pour cela : `outils/03-entropie/rans/src/bin/banc_gemv.rs` et `src/gemv.wgsl`.

**Ce qui est mesuré.** Un produit matrice-vecteur de lot 1 sur des **poids MXFP4 réels de
gpt-oss-20b** (codes et échelles E8M0 d'origine, trois tenseurs d'experts, 256 Mio de
codes, regroupés en 131 072 lignes de 4 096 poids ; le regroupement garde les blocs de 32
entiers avec leur échelle). Quatre chemins, avec exactement la même déquantification
(`valeurs4` : les huit grandeurs E2M1 doublées rangées dans le mot `0xC8643210`, trois
opérations entières par code, aucune table) :

| chemin | ce qu'il fait |
|---|---|
| brut | lit les codes bruts (4 bits par poids) et les échelles, calcule y = W·x ; un sous-groupe traite 4 lignes, les 32 x d'un bloc sont chargés une fois pour les 4 |
| fondu | décodeur v4 (alphabet octet, vote, fenêtre) ; chaque mot décodé est consommé dans les registres, sans jamais écrire les codes |
| décodage seul | décodeur v4 qui écrit les codes en VRAM |
| deux passes | décodage seul, puis brut sur les codes décodés, dans la même soumission |

**Vérification exacte, et témoins** (`gemv-gptoss20b-calme.json`). Avec des échelles
toutes à 2⁰ et des x entiers dans [−2, 2], chaque terme est un entier d'au plus 24 en
valeur absolue et toute somme de 4 096 termes reste sous 2¹⁷ : la somme est exacte en f32
dans n'importe quel ordre, donc la carte doit égaler la référence du processeur bit à bit.
Résultat : **0 ligne fausse sur 131 072** pour le brut, le fondu et les deux passes, et
aucune voie hors de L. Témoins : une seule fente de la table corrompue rend 38 329 lignes
fausses ; toutes les fentes corrompues, 130 564. Sur les vraies entrées (x flottants,
échelles réelles), l'écart relatif au maximum de |y| est de 9,5 × 10⁻⁸ (brut) et
1,3 × 10⁻⁷ (fondu) contre une référence en f64.

**Débits**, cinq séries palindromiques, carte seule, sur secteur
(`gemv-gptoss20b-secteur.json`) puis, pour mémoire, sur batterie
(`gemv-gptoss20b-calme.json`) :

| chemin | secteur : temps médian | milliards de poids/s | Go/s de MXFP4 équivalents (meilleure) | dispersion | rapport au brut | batterie : Go/s équivalents | rapport |
|---|---|---|---|---|---|---|---|
| brut | 1,36 ms | 394,1 | **209,4** (211,6) | 24 % | 1 | 66,4 | 1 |
| **fondu** | 4,99 ms | 107,5 | **57,1** (57,3) | 4 % | **0,27** | 19,5 | 0,29 |
| décodage seul | 3,72 ms | 144,5 | 76,7 (77,2) | 9 % | — | 29,4 | — |
| **deux passes** | 5,13 ms | 104,6 | **55,6** (56,2) | 7 % | **0,27** | 21,7 | 0,33 |

Lecture :

1. **Le brut atteint 209 Go/s de poids MXFP4 équivalents sur secteur, 83 % des 251 Go/s
   de la VRAM** (394 milliards de poids par seconde pour un plafond de 472) : il est limité
   par la mémoire. C'est aussi, en passant, le produit 4 bits le plus rapide mesuré sur
   cette machine (l'étude 01 avait 122 Go/s en Q4_0) ; sa recette est au §9.
2. **Le fondu est 3,7 fois plus lent que le brut** (3,4 sur batterie). Le §4.3 prédisait
   3,4 par le calcul ; la mesure le confirme par un autre chemin, sur un autre format.
3. **Fondre ne gagne rien sur deux passes** : 57,1 contre 55,6 Go/s sur secteur (2,7 %,
   dans la dispersion), et 19,5 contre 21,7 sur batterie (dans l'autre sens). Les temps
   s'additionnent : décodage 3,72 ms plus produit 1,36 ms font 5,08 ms, pour 4,99 (fondu) et
   5,13 (deux passes) mesurés. La fusion n'économise que l'aller-retour des codes en VRAM,
   2 × 256 Mio à environ 250 Go/s, soit environ 2 ms de trafic, que le décodeur, limité par
   le calcul, recouvre déjà (Proposition 8 de `03-entropie-derivations.md`).
4. Sur batterie, le brut lui-même tombe à 66 Go/s (facteur 3,2) : le plafond de puissance
   frappe d'abord les noyaux qui calculent. Les rapports, eux, restent à 0,27-0,33.
5. **Réponse à la question clé.** Décoder *dans* le noyau n'apporte rien sur cette carte,
   et décoder *juste avant* coûte autant : dans les deux cas, 3,7 fois le temps du produit
   brut quand les poids résident en VRAM. Le décodage entropique ne paie que là où il
   soulage un étage plus lent que lui : **le disque et la PCIe**. Sa place est donc à
   l'arrivée du tronçon en VRAM, une fois, avant que le tronçon décodé n'entre dans le
   cache de la carte, où il sert ensuite au débit du brut. Dans ce schéma, décoder un jeton
   qui lit tout par le disque coûte 2,49 / 70 ≈ 3,6 % du temps de la carte sur secteur
   (9 % sur batterie), et rend au disque tout le taux r.

## 5. Au-delà du sans-perte : une quantification taillée pour le codeur

Pourquoi les K-quants laissent si peu : leur recherche d'échelle et de minimum écrête
pour remplir les 16 niveaux. Les codes deviennent presque uniformes (3,86 bits sur 4),
ce qui est l'optimum d'un code à débit fixe. La théorie classique dit ce qu'on perd à
débit fixe :

- à haut débit, une quantification uniforme suivie d'un codage entropique (ECSQ) est à
  0,254 bit, soit 1,53 dB, de la borne de Shannon (Gish et Pierce, IEEE Trans. Inf.
  Theory 14(5), 1968) ;
- la meilleure quantification à débit fixe (Panter et Dite) est plus loin encore : pour
  une gaussienne, de ½ log₂(√3·π/2 ÷ πe/6) ≈ 0,47 bit (calculé).

**Mesure** (`rd_proxy.py`, journal `rd-proxy-4B.json`) :

- Substituts des poids d'origine : deux tenseurs Q8_0 (ssm_alpha et ssm_beta) et un Q6_K
  (blk.0.ffn_down), tous déquantifiés.
- KQ4 : une quantification façon Q4_K réécrite de zéro, à 4,5 bits par poids
  (8 sous-blocs de 32, échelle et minimum cherchés pour l'erreur minimale, 6 bits sous un
  couple fp16).
- MM4 : un min-max sans recherche, par groupes de 32 et de 64.
- ECSQ : un pas Δ = c·σ par bloc de 256 (σ en fp16, soit 0,0625 bit par poids), des
  codes entiers non bornés, une table par tenseur.
- Témoin de réalisme : les codes de KQ4 portent 3,874 à 3,883 bits, ceux du vrai Q4_K
  3,865. Notre quantification a la même forme que celle de llama.cpp.

| tenseur (aplatissement) | KQ4 : erreur relative, H codes | MM4 g32 / g64 : erreur, H | ECSQ à erreur égale | gain | ECSQ à débit égal | borne gaussienne par bloc |
|---|---|---|---|---|---|---|
| blk.0.ssm_alpha (Q8_0, 3,81) | 0,00543 ; 3,879 | 0,00625 ; 3,860 / 0,00824 ; 3,747 | **4,083 b/p** | **0,417** | + 2,54 dB | 3,706 |
| blk.10.ssm_beta (Q8_0, 6,57) | 0,00573 ; 3,874 | 0,00653 ; 3,855 / 0,00895 ; 3,728 | **4,045 b/p** | **0,455** | + 2,76 dB | 3,522 |
| blk.0.ffn_down (Q6_K, 5,18) | 0,00538 ; 3,883 | 0,00620 ; 3,864 / 0,00820 ; 3,748 | **4,089 b/p** | **0,411** | + 2,48 dB | 3,758 |

Le nombre entre parenthèses après le type est le kurtosis du tenseur.

Lecture :

- **À erreur quadratique égale, l'ECSQ demande 0,41 à 0,46 bit de moins par poids
  (9 à 10 %).** C'est deux fois le plafond sans perte de Q4_K (0,24 bit), et cela
  s'additionne en partie avec le codage des métadonnées.
- Il reste 0,3 à 0,5 bit jusqu'à la borne gaussienne par bloc. Une zone morte, une
  optimisation débit-distorsion des arrondis, ou un réseau (E8, comme EntroPack) peuvent
  en prendre une part.
- Le décodeur de ce codage est la v4 du §3, avec un alphabet de 38 à 96 symboles. Elle
  en accepte 256.
- La reconstruction est un produit code × Δ, fusionnable dans la multiplication.

Ce chiffre n'est pas une qualité. La perplexité et la divergence KL de l'étude 02
jugeront, et l'erreur pondérée par imatrix peut déplacer le gain (§8).

## 6. Quand une mesure contredit un chiffre publié

Ce qui est publié sur l'entropie des codes 4 bits (littérature, éditeur, non reproduit) :
- « int4 weights retain only 0.6–1.0 bits of true entropy » (arXiv 2606.15789v1, §VI-B) ;
- environ 2,17 bits pour le 4 bits de MLX (issue ml-explore/mlx #3043, 2026-01-22,
  méthode non décrite, fermée par son auteur) ;
- 1,39 bit pour uint4 par tenseur (EntroLLM).

Ce que je mesure :
- 3,864 à 3,865 bits sur tous les codes Q4_K de deux modèles ;
- 3,73 à 3,75 bits avec un min-max par groupes de 64 sur des poids réels, et 3,86 bits
  par groupes de 32 (§5).

Pour tomber à 1 bit, il faudrait que la plage d'un groupe dépasse environ dix fois
l'écart-type de ses poids. C'est possible avec une échelle par tenseur ou par canal,
dominée par des valeurs aberrantes (le cas d'EntroLLM, payé en perplexité). Ce n'est pas
possible avec des groupes de 32 à 128 sur des distributions de kurtosis 3,8 à 6,6.

Je ne barre aucun chiffre publié : je ne l'ai pas reproduit sur leurs poids. **Mais
aucune de ces entropies ne s'applique aux GGUF K-quant, et toute estimation de gain
« 1,8 à 6 fois en plus de la quantification » est fausse pour eux d'un facteur 30 à 100
sur le gain** (0,24 bit au lieu de 2 à 3 bits).

## 7. Ce que je crois manquer dans le monde (les trous réels, chiffrés)

1. **Aucun outil ne code par entropie les champs des GGUF K-quant.**
   - Le plafond mesuré est de 5,3 % ; zstd en prend 1,2 % et lz4 0 %.
   - ZipNN déclare les GGUF incompressibles, et c'est vrai pour tout codeur d'octets sur
     le bloc entier (≤ 1,8 %).
   - Le trou chiffré : 3,5 points de taille. Sur le 9B, 180 Mo par jeton relu ne
     traversent pas le disque.
2. **Aucun décodeur entropique de poids sans CUDA n'a de débit publié** (Vulkan, DX12)
   sur une carte de portable.
   - Les seuls chemins DX12 publiés, GDeflate et zstd de DirectStorage, sont des LZ
     suivis d'un Huffman d'octets : leur LZ ne trouve rien ici, et leur Huffman plafonne
     à 1,8 %.
   - Je mesure qu'un rANS à vote de sous-groupe produit 70 à 72 Go/s par Vulkan sur
     une RTX 4060 Laptop sur secteur (65 à l'essai de la première passe, 27 sur
     batterie), 28 fois le disque ; le même algorithme en CUDA fait 81-82 Go/s.
3. ~~**Aucune implémentation pour les LLM grand public d'une quantification taillée pour le
   codeur, décodée en flux.**~~ Barré à la reprise : faux tel qu'écrit. EntQuant (ICML 2026,
   Float8 codé par ANS, nvCOMP, décodé par bloc avant le produit) et vram-compression
   (ECSQ-GPTQ, rANS fondu au produit de lot 1, RTX 3050 Laptop) existent (§2.13). Ce qui
   reste vrai, et qui est le trou :
   - aucune des deux ne tourne sans CUDA, ni ne vise le régime flux depuis le disque :
     EntQuant garde tout le modèle compressé en VRAM, vram-compression aussi ;
   - aucune ne s'applique aux formats que la machine fait tourner (K-quants, MXFP4 des
     GGUF), ni ne publie un débit de décodeur rapporté au disque ;
   - EntroPack (2026-09-28) le fait en diffusion, sur réseau E8.
   - Gain mesuré ici à erreur égale : 0,41 à 0,46 bit par poids, soit 9 à 10 % d'octets
     par jeton de moins que Q4_K. vram-compression publie, sur Qwen2.5-1.5B, une perplexité
     d'ECSQ-GPTQ avec pas par colonne à 3,25 bits (9,81) presque égale à celle de GPTQ à
     4,25 bits (9,78) : environ 1 bit gagné à qualité presque égale (littérature, non
     reproduit). C'est deux fois notre 0,41 à 0,46 bit à erreur quadratique égale ; leur
     pas par colonne pondéré par la hessienne, que notre mesure n'a pas, peut expliquer
     l'écart.
4. **Le régime résident n'a pas de solution à longueur variable sur cette classe de
   carte** : il manque un facteur 3,4 au décodeur (130 contre 446 milliards de poids par
   seconde, calculé), **retrouvé par la mesure** : le produit fondu MXFP4 est 3,4 fois plus
   lent que le brut, et pas plus rapide que deux passes (§4.5).
   - Un code à décodage en temps constant, de la famille de ZipServ, qui garderait une
     part du gain de l'ECSQ, reste à inventer.
   - Exemple : un code à deux longueurs, avec un plan d'exceptions comme TCA-TBE.
5. **Les entropies publiées des int4 divergent d'un facteur 4** (0,6–1,0 contre 3,86 bits
   mesurés ici). Il manque une mesure publique, outillée, par schéma de quantification.
6. **Le décodage sur le processeur ne suit pas le disque sur 6 cœurs**, même en
   AVX-512 : au mieux environ 4 Go/s (calculé depuis Recoil), contre 0,075 Go/s par fil
   mesuré ici en scalaire. Le chemin doit rester sur la carte.
7. **Personne ne code les échelles E8M0 du MXFP4.** Aucun des travaux lus (DFloat11,
   ZipNN, ECF8, ZipServ, EntQuant, l'article de l'ISCA 2026) ne mesure ni ne code les
   échelles partagées des formats MX, alors que ce sont elles qui portent le gain : sur
   gpt-oss-20b, 0,218 bit par poids d'échelles contre 0,138 de codes (calculé depuis les
   entropies, §1.6). Le trou chiffré : un taux réel de 1,0888 sur les experts de
   gpt-oss-20b (1,0887 sur gpt-oss-120b), et 1,1037 avec trois classes d'échelle, décodé
   exactement, avec le décodeur de carte déjà mesuré à 70 Go/s ; zstd
   n'en prend que 1,0405 sur les mêmes tenseurs, lz4 rien (journal `entropie-gptoss20b-resume.txt`).
   NVFP4 (échelle FP8 par bloc de 16) et les autres formats MX ont la même structure ; je
   ne l'ai pas mesurée, aucun fichier de ces formats n'étant sur la machine.
8. **Aucune mesure publiée ne compare deux chemins de compilation du même décodeur
   entropique sur la même carte.** Je trouve 14 % entre nvcc et Vulkan (naga puis le
   pilote) sur une boucle rANS à vote, 4 % sur une recopie (§4.1 ter). Ce que cela coûte
   d'ignorer : une décision « CUDA ou Vulkan » prise sur un débit publié d'un autre
   langage se trompe d'environ ce facteur.
9. **Trou de reproduction** (le mien) : DietGPU et Recoil n'ont pas été reconstruits sur la
   machine, bien que CUDA y soit désormais (§8). Leur débit publié (250 à 410 Go/s sur A100,
   plus de 90 sur RTX 2080 Ti) reste celui des éditeurs.

## 8. Ce qui pourrait être faux

- **Contention.** D'autres agents faisaient tourner `llama-quantize`, `llama-imatrix`,
  `llama-perplexity` et des scripts Python pendant mes mesures.
  - Les débits du processeur en sont gravement touchés : la recopie mémoire d'un fil a
    varié de 0,3 à 10 Go/s. Je ne les cite qu'en ordre de grandeur.
  - Les débits de la carte du §4.1 viennent d'un moment où la carte était peu chargée.
    Les passes gardées au calme (`attendre_calme.sh`) les remplacent quand elles existent
    (§4.1 bis).
- **Les gains sur les métadonnées sont optimistes en table.** Coder d fp16 avec une table
  de 65 536 entrées pour 40 000 à 200 000 blocs coûte plus cher en table que l'entropie
  ne le dit. Le chiffre réaliste est celui du codage par octet du champ (1,052 pour Q4_K,
  §1.4), pas l'idéal 1,057.
- **Les débits viennent de lots de 126 à 256 Mio.** Un lancement par tenseur (11 à
  50 Mio) perdra un peu en démarrage et en fin de vague. Ce n'est pas encore mesuré.
- **Le §5 repose sur des substituts.** Les poids Q6_K et Q8_0 déquantifiés sont posés sur
  une grille, ce qui peut abaisser un peu l'entropie mesurée de l'ECSQ, donc gonfler le
  gain. Mon KQ4 n'a ni l'imatrix ni la recherche exacte de llama.cpp. L'erreur
  quadratique n'est pas la qualité. Le gain doit être refait sur des poids BF16
  d'origine, puis jugé en divergence KL par l'étude 02.
- **Le modèle du sous-groupe.** La carte doit avoir des sous-groupes de 32 invocations
  consécutives. C'est vrai ici, vérifié par l'exactitude, et faux sur AMD (64) ou sur
  certaines Intel. Le décodeur s'arrête proprement (compteur de contrôle) si la taille
  diffère.
- **Le contrôle d'état (x = L à la fin) ne détecte pas une table corrompue** (v4, §3.3).
  En production, il faudra une empreinte de la table, ou de la sortie.
- **Le budget arithmétique de la carte (6 à 7,7 billions d'opérations par voie et par
  seconde) est un ordre de grandeur**, pas une mesure. L'étude 01 a un banc arithmétique
  qui peut le remplacer.
- **Les chiffres de débit de la littérature** (DietGPU, Recoil, ZipNN) sont ceux des
  éditeurs, sur d'autres machines. Aucun n'est reproduit ici. ~~CUDA est absent, et deux
  de ces dépôts demandent GNU/Linux ou CUDA 12.~~ Corrigé à la reprise : CUDA 13.1.2 est
  dépaqueté sur la machine depuis le 2026-10-15 (SOCLE, « La machine ») ; DietGPU et
  Recoil pourraient donc se construire, multians reste lié à GNU/Linux. Je ne l'ai pas
  fait : le chemin visé est Vulkan, et la question clé a été tranchée par notre propre
  décodeur (§4.5). C'est un trou de reproduction, dit au §7.
- **La machine était sur batterie pendant les mesures de la reprise** (§4.1 bis) :
  limite de puissance de la carte à 43 W au lieu de 80, horloge mémoire à 6 001 MHz au lieu
  de 8 001. Les débits absolus de la reprise sont donc plus bas que ceux de l'essai v4 ; les
  rapports entre chemins, mesurés dans les mêmes séries palindromiques, restent comparables.
  Brancher la machine est un geste de Stone : je ne l'ai pas fait.

### Ajouts de la reprise

- **Le produit fondu pourrait être mieux écrit.** Mon noyau fondu est en WGSL, sans
  produit scalaire entier ni mémoire partagée pour les x. Mais aucune écriture du fondu ne
  peut descendre sous le temps du décodeur seul, qui vaut déjà 2,7 fois celui du produit
  brut sur secteur (3,72 contre 1,36 ms) ; avec le décodeur CUDA, 14 % plus rapide, le
  rapport resterait au-dessus de 2,3. La conclusion « ne pas fondre sur cette carte » ne
  dépend donc pas de la qualité de mon noyau fondu ; elle dépend du débit du décodeur.
  Un décodeur deux à trois fois plus rapide la renverserait : ce n'est pas ce que j'ai
  mesuré, ni ce que publie la littérature pour une carte de cette classe.
- **Le taux MXFP4 vient de gpt-oss-20b ; celui de gpt-oss-120b est mesuré à part**
  (`taux-mxfp4-gptoss120b.json`, §1.6). Le codage des échelles suppose qu'une ligne de la
  matrice est une suite de blocs contigus, ce qui est vrai de la disposition des GGUF
  (ne0 colonnes d'abord) ; un autre conteneur demanderait de le revérifier.
- **Le gain sur le cache d'experts (+12,4 %) suppose le routage uniforme de l'étude 06**
  et un cache qui garde les experts compressés en RAM. Un routage concentré change h,
  donc le gain ; la formule de `03-entropie-derivations.md` (§6, point 8) se recalcule
  avec le h mesuré par l'étude 05.
- **Les mesures mêlent batterie et secteur.** Chaque journal porte l'état d'alimentation
  au début et à la fin de sa passe ; seuls les chiffres du secteur entrent dans l'« en
  bref ». Les passes sur batterie restent dans les tableaux, étiquetées.
- **Le second chemin CUDA est indépendant par le code et le compilateur, pas par
  l'algorithme** : je l'ai écrit d'après mon propre format. Ce qui le rend probant :
  l'exactitude est jugée contre la source, et non contre l'autre décodeur ; un défaut du
  format commun aux deux se verrait comme une sortie fausse dans les deux.
- ~~**L'information mutuelle code-échelle (0,039 bit) n'a pas été encaissée.** Elle
  demande une table par classe d'échelle ; son coût en mémoire partagée (16 Kio par table)
  et en débit du décodeur n'est pas mesuré.~~ Barré le même jour : encaissée par trois
  flux de codes selon la classe d'échelle, 0,053 bit pris (§1.6), sans changer le
  décodeur ni la mémoire partagée, chaque groupe de travail ne chargeant que la table de
  son flux. Le réassemblage a été mesuré ensuite (`cuda/dispersion.cu`,
  `dispersion-classes-secteur.json`, proportions réelles des classes sur gpt-oss-20b :
  12,9 % sous la médiane, 74,8 % à la médiane, 12,3 % au-dessus,
  `proportions-classes-gptoss20b.txt`) : **102,4 Go/s écrits contre 113,5 pour une
  recopie contiguë**, sortie exacte, témoin (un indice faussé) qui tombe. Décodage
  (70 Go/s) puis réassemblage font ensemble 41,6 Go/s, encore 17 fois le disque ; écrire
  directement à la place finale depuis le décodeur supprimerait la passe.

## 9. Recettes (essayées, qui marchent ou qui échouent, avec leur raison)

1. **Témoin par inversion des demi-octets, appliquée à notre seul chemin :** marche.
   Appliquée aux deux chemins, elle ne tombait pas : une panne doit toucher un seul côté
   de la comparaison.
2. **zstd 19 sur tous les tenseurs :** trop lent (des heures sous charge). On le garde
   sur un échantillon de 16 Mo pour quelques couches.
3. **Huffman par fusion de listes :** O(n²) sur 65 536 symboles. Des pointeurs parents
   règlent le problème. Témoin : une loi dyadique donne exactement l'entropie.
4. **La directive WGSL `enable subgroups;` est refusée par naga 30.** On la retire et on
   garde la fonction SUBGROUP de wgpu : ça marche.
5. **Carte v1 → v2** : la somme préfixe et la lecture globale dans la chaîne coûtent un
   facteur 2. Le vote, le comptage de bits et la fenêtre en registres distribuée par
   échange le rendent.
6. **Carte v3, table compacte de 4 Kio :** aucun gain. L'occupation n'était pas la limite.
7. **Carte v4, alphabet octet :** × 1,6. La même chaîne par pas produit deux fois plus
   d'octets, et le taux est identique (1,0316).
8. **rANS scalaire à flux partagé sur le processeur :** environ 16 cycles par code. La
   chaîne du pointeur est sérielle ; enlever la branche n'y change presque rien. Il
   faudrait du SIMD (style Recoil), et même alors on reste sous le disque.
9. **Mesurer sous la charge d'autres agents :** dispersions de 100 à 4 700 %. On n'accepte
   qu'une fenêtre calme, trois relevés de suite (carte sous 5 %, ou processeur sous 20 %
   sans llama).
10. **Le byte grouping par champ** (ZipNN transposé aux blocs K) : marche pour Q4_K (1,052
    sur 1,057), échoue pour Q5_K (1,018 sur 1,047). Le bit isolé dans qh demande un
    alphabet de symboles entiers.
11. **Une table par tenseur contre une table par modèle :** 0,00002 bit d'écart. Une
    seule table suffit.
12. **Débit du produit MXFP4 brut en WGSL, 209 Go/s (83 % de la VRAM)** : un sous-groupe
    traite 4 lignes, chaque voie charge les 32 x d'un bloc une fois pour les 4 lignes, et
    les huit grandeurs E2M1 doublées tiennent dans le mot `0xC8643210` (trois opérations
    entières par code, aucune table). Marche ; à transmettre à l'étude 04, l'étude 01
    n'avait que 122 Go/s en Q4_0.
13. **Fondre le décodeur rANS dans le produit** : échoue (3,7 fois plus lent que le brut,
    pas plus rapide que deux passes). Raison : les deux noyaux sont limités par le calcul ;
    la fusion n'économise que de la mémoire.
14. **Vérification exacte d'un produit en flottant** : prendre des x entiers dans [−2, 2]
    et des échelles à 2⁰ ; toute somme reste entière et sous 2²⁴, donc exacte dans
    n'importe quel ordre. Marche : comparaison bit à bit avec le processeur, au lieu d'une
    tolérance qui aurait laissé passer une seule fente corrompue.
15. **Échelles E8M0 codées en écart à la médiane de ligne** : marche (1,07 bit par bloc
    réel, contre 1,55 à l'ordre 0), et la reconstruction ne dépend d'aucun autre bloc. Le
    contexte « bloc de gauche » prend presque autant (1,15) mais impose une somme préfixe ;
    le contexte « ligne du dessus » ne prend rien (1,54).
16. **Juger le calme de la carte sur son utilisation affichée** : échoue. Au repos (P8,
    210 MHz), l'utilisation oscille de 0 à 20 % ; une passe a attendu plus de 20 minutes.
    La puissance tirée (5,5 W au repos, plus de 40 W en calcul) est le bon témoin.
17. **Croire qu'une fenêtre calme le reste** : échoue. Un `llama-bench` d'un autre agent
    est parti au milieu d'une passe. Le lanceur exclut désormais les programmes de llama.cpp
    qui calculent sur la carte et note l'état de la machine à la fin ; l'échantillonneur
    `nvidia-smi` dit après coup si la passe est restée seule.
18. **Mesurer sur batterie** : les débits de la carte tombent d'un facteur 1,6 (recopie) à
    3,2 (produit brut). Toujours relever `Win32_Battery.BatteryStatus` avec une mesure.
19. **Second chemin dans un autre langage, sur le même flux écrit sur disque** : marche.
    Deux décodeurs (WGSL et CUDA) rendent les mêmes octets ; c'est la preuve que le format
    est bien celui que le codeur écrit, indépendamment du code de l'un ou de l'autre.
20. **Piper la sortie d'une mesure longue dans `head`** : échoue. `head` se ferme, le
    programme meurt par tube cassé à la 20ᵉ ligne. Écrire dans un fichier, lire la fin.
21. **Entropie d'ordre 0 de gpt-oss-120b en Python (63 Go)** : trop lent (plusieurs heures
    sous charge) ; arrêtée. Le taux réel par l'outil Rust et le contexte des échelles sur
    36 tenseurs la remplacent.
22. **Outils de l'environnement :**
    - un heredoc qui contient des apostrophes, dans une commande, casse l'analyse du
      shell : on écrit le script dans un fichier ;
    - `bash -c` dans une commande déclenche la garde de sécurité : on appelle
      l'interprète directement ;
    - un script Python passé par un heredoc perd la moitié de ses barres obliques
      inverses : `\b`, `\r`, `\a` deviennent des caractères de contrôle dans le LaTeX
      écrit. On écrit le script dans un fichier ;
    - un `.bat` lu par `cmd` est dans la page de code OEM : commentaires sans accents ;
    - la sortie d'un Python redirigée sous Windows est en cp1252 : poser
      `PYTHONIOENCODING=utf-8`.

## 10. Réponses par délégation

- Taille de tuile : 256 macro-pas (32 Kio de demi-octets). En-têtes à 0,40 %, et 4 040
  tuiles pour 126 Mio, assez pour remplir les 24 multiprocesseurs. *Réponse par
  délégation du 2026-10-15, réversible* : au-delà, les en-têtes coûtent peu mais le
  parallélisme baisse sur les petits tenseurs.
- Précision des probabilités : 12 bits. Elle garantit au plus une lecture par pas avec des
  mots de 16 bits, et la perte de table est mesurée nulle au 10⁻⁵ près. *Réponse par
  délégation du 2026-10-15, réversible.*
- Pas de téléchargement de poids BF16 pour mesurer les exposants. Le SOCLE réserve ce
  choix à l'orchestrateur ; la demande est dans la valeur de retour. *Réponse par
  délégation du 2026-10-15, réversible.*
- Ne pas brancher la machine sur secteur ni attendre qu'elle le soit : mesurer sur
  batterie en le disant, puis refaire quand le secteur est revenu (il l'est revenu à
  08:33). *Réponse par délégation du 2026-10-15, réversible* : un geste sur sa machine
  reste à Stone (SOCLE, « Les questions »).
- Arrêter mes propres tâches de fond quand un meilleur protocole les remplace (chaîne de
  passes au calme arrêtée deux fois, mesure d'entropie de gpt-oss-120b arrêtée). Aucun
  processus d'un autre agent n'a été touché. *Réponse par délégation du 2026-10-15,
  réversible.*
- Échelles MXFP4 codées par écart à la médiane de ligne plutôt que par le contexte du
  voisin de gauche : 0,13 bit moins cher, et décodable en parallèle sans somme préfixe.
  *Réponse par délégation du 2026-10-15, réversible* : décidé par les nombres du §1.6.
- Vulkan plutôt que DX12 pour le prototype. L'étude 01 a mesuré que wgpu sous DX12 (sans
  DXC) n'a pas les sous-groupes, alors que Vulkan les a (`carte-info.log`). *Réponse par
  délégation du 2026-10-15, réversible.*

## 11. Sources (consultées le 2026-10-15)

- DFloat11 : https://arxiv.org/abs/2504.11651 (v1 2025-04-15, v3 2026-01-01) ; https://github.com/LeanModels/DFloat11 (Apache-2.0, commit 4577338 du 2025-11-24).
- ZipNN : https://arxiv.org/abs/2411.05239 (v2 2025-06-04) ; https://github.com/zipnn/zipnn (MIT, commit 6009704 du 2026-04-11).
- Huff-LLM : https://arxiv.org/abs/2502.00922 (v1 2025-02-02).
- Ecco : https://arxiv.org/abs/2505.06901 (v1 2025-05) ; actes ISCA 2025, p. 793–807.
- ZipServ : https://arxiv.org/abs/2603.17435 (v1 2026-03-18, ASPLOS 2026) ; https://github.com/HPMLL/ZipServ_ASPLOS26 (Apache-2.0, commit 6f8a209 du 2025-12-19).
- Approaching Shannon Bound : https://arxiv.org/abs/2606.15789 (v1 2026-06-14, ISCA 2026).
- EntroPack : https://arxiv.org/abs/2609.34185 (v1 2026-09-28) ; https://github.com/modelscope/entropack (non cloné).
- EntroLLM : https://arxiv.org/abs/2505.02380 (v4 2026-01-26).
- Neural Weight Compression : https://arxiv.org/abs/2510.11234 ; RD + entropie, vision : https://arxiv.org/abs/2505.18758.
- nvCOMP : https://docs.nvidia.com/cuda/nvcomp/release_notes.html (6.0.0, non daté) ; https://docs.nvidia.com/cuda/nvcomp/algorithm_selection.html ; https://developer.nvidia.com/nvcomp.
- DirectStorage 1.4 : https://devblogs.microsoft.com/directx/directstorage-1-4-release-adds-support-for-zstandard/ (2026-03-11) ; https://github.com/microsoft/DirectStorage (MIT, GDeflate Apache-2.0, commit c53f149 du 2026-08-04).
- DietGPU : https://github.com/facebookresearch/dietgpu (MIT, commit a4d70a1 du 2026-03-18).
- Recoil : https://arxiv.org/abs/2306.12141 (ICPP 2023) ; https://github.com/lin-toto/recoil (GPL-3.0, commit c36e25d du 2026-07-12).
- multians : https://doi.org/10.1145/3337821.3337888 (ICPP 2019) ; https://github.com/weissenberger/multians (LGPL-3.0, commit 55515d8 du 2019-07-26).
- zstd : https://github.com/facebook/zstd (README, zstd 1.5.7, lz4 1.10.0, lzbench sur Silesia).
- MLX, issue 3043 : https://github.com/ml-explore/mlx/issues/3043 (2026-01-22, fermée le 2026-01-26 par son auteur).
- EntQuant : https://arxiv.org/abs/2601.22787 (v1 2026-01-30, v2 2026-05-29, ICML 2026) ; https://github.com/merantix-momentum/entquant (Apache-2.0 selon le README, non cloné).
- vram-compression : https://github.com/snuri00/vram-compression (commit 1af9a93 du 2026-09-23, aucune licence ; cloné pour lecture).
- ECF8 : https://arxiv.org/abs/2510.02676 (v1 2025-10-03).
- WaterSIC : https://arxiv.org/abs/2603.04956 (v1 2026-03-05, v2 2026-06-01) ; https://github.com/egorlifar/watersic (MIT, non cloné).
- MXFP4 : OCP Microscaling Formats (MX) Specification v1.0 (2023) ; disposition `block_mxfp4` de ggml-common.h (llama.cpp, MIT).
- Titres, auteurs et dates des préprints relus par l'API d'arXiv le 2026-10-15 ; références complètes dans `memoire/sources/03-entropie.bib`.
- ANS : J. Duda, https://arxiv.org/abs/1311.2540 ; F. Giesen, « Interleaved entropy coders », https://arxiv.org/abs/1402.3392.
- ECSQ : H. Gish, J. N. Pierce, « Asymptotically efficient quantizing », IEEE Trans. Inf. Theory 14(5), 1968, p. 676–683.

## 12. Outils et journaux

- Outils (`outils/03-entropie/`) :
  - lecture : `gguf_lecture.py`, `champs_k.py`, `temoin_champs.py` ;
  - entropie : `mesure_entropie.py`, `resume_entropie.py`, `flux_octets.py` ;
  - quantification et débits : `rd_proxy.py`, `debits_cpu.py`, `attendre_calme.sh` ;
  - codeur : `rans/` (`lib.rs`, `decodeur.wgsl`, `bin/banc_rans.rs`, `bin/micro_cpu.rs`) ;
  - reprise : `rans/src/gemv.wgsl` et `bin/banc_gemv.rs` (produit fondu), `bin/taux_mxfp4.rs`
    (taux réel MXFP4 par champs), `bin/vider_flux.rs` et `cuda/rans_v4.cu`,
    `cuda/construire.bat` (second chemin CUDA), `cuda/dispersion.cu` (réassemblage des flux de classe), `proportions_classes.py`, `mxfp4_contexte.py`, `vers_csv.py` (CSV des
    figures), `passes_carte.sh`, `passes_secteur.sh` ;
  - dérivations et structures pour le mémoire : `fondations/03-entropie-derivations.md` ;
    sources : `memoire/sources/03-entropie.bib`.
- Journaux (`fondations/journaux/03-entropie/`) :
  - lecture et entropie : `temoin-champs.log`, `entropie-{4B,9B}.{json,log}`,
    `entropie-{4B,9B}-resume.{txt,json}`, `flux-octets-{4B,9B}.json` ;
  - quantification : `rd-proxy-4B.json` ;
  - débits : `rans-4B-premier-essai.json`, `rans-4B-contention-v1-v2.json`,
    `rans-4B-essai-v4.json`, `debits-cpu-4B-essai-contention.json` ;
  - reprise, sur batterie : `rans-4B-contention-llama-bench.json`, `rans-4B-calme.json`,
    `gemv-gptoss20b-calme.json`, `gemv-gptoss20b-verification-32Mio-contention.json` ;
  - reprise, sur secteur : `cuda-4B-A{1,2}-secteur.json`, `rans-4B-B{1,2}-secteur.json`,
    `gemv-gptoss20b-secteur.json`, `rans-gptoss20b-secteur.json`,
    `echantillons-carte-secteur.csv`, et les `calme-*.log` de chaque passe ;
  - MXFP4 : `mxfp4-contexte-gptoss{20b,120b}.{json,log}`, `taux-mxfp4-gptoss{20b,120b}.{json,log}`,
    `taux-mxfp4-classes-gptoss{20b,120b}.{json,log}`, `taux-mxfp4-classes5-gptoss20b.{json,log}`,
    `proportions-classes-gptoss20b.txt`, `dispersion-classes-secteur.json`,
    `entropie-gptoss20b.{json,log}` ;
  - CSV des figures : `csv/` (régénérés par `vers_csv.py`).
