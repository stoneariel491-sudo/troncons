# Étude 02 : la quantification extrême des poids (avec perte)

Troncons, fondations. Rédigé le 2026-10-15. Toutes les sources ont été consultées le
2026-10-15 ; leur date de publication est donnée à côté de leur adresse (§ 10).
Chaque chiffre porte son étiquette : **[litt.]** littérature (éditeur, non reproduit),
**[calc.]** calculé ici, **[mes.]** mesuré ici sur la machine de Stone.

---

## 0. En bref

- **Le levier.** Quand le modèle ne tient pas en mémoire, chaque jeton doit faire passer
  ses poids actifs par l'étage le plus lent (PCIe ≈ 6 à 8 Go/s mesurés, NVMe ≈ 7 Go/s
  à confirmer,
  contre 256 Go/s pour la VRAM). Le débit maximal est alors
  `jetons/s ≤ débit de l'étage / (N_actifs × b / 8)`, où `b` est le nombre de bits par
  poids. Diviser `b` par deux double le plafond, à n'importe quel étage. Aucun autre
  levier de l'étude n'a cette pente.
- **Ce que vaut la meilleure quantification d'aujourd'hui, mesuré sur la source idéale.**
  À 2 bits par poids, sur une gaussienne i.i.d. (ce que voient les méthodes après
  rotation), j'obtiens [mes.] : scalaire optimal (Lloyd-Max) 0,1175 ; VQ en dimension 8
  0,093 ; treillis à décalage (QTIP, EXL3) 0,068 ; borne de Shannon 0,0625. Le treillis
  ferme 90 % de l'écart entre le scalaire et la borne, la VQ de dimension 8 en ferme
  44 %. **IQ2_XXS de llama.cpp, mesuré sur la même source, vaut exactement le scalaire
  optimal à son débit (0,107 à 2,0625 bits)** : sa grille E8 sert sur des poids non
  tournés, pas après rotation.
- **Le meilleur rapport octets lus / qualité aujourd'hui** est obtenu par les codes en
  treillis après rotation (QTIP, EXL3 en pratique), puis par PV-tuning sur AQLM ou
  QuIP#. Sur Llama 2 (même programme d'évaluation), **un 13B en treillis 2 bits
  (3,3 Go lus par jeton, PPL 5,11) égale un 7B en 4 bits (3,4 Go, 5,17)**, et un 70B en
  2 bits (17 Go, 3,70) bat un 13B en FP16 (26 Go, 4,57) [litt., calc.]. Avec une
  quantification scalaire, le croisement n'a pas lieu. **Depuis septembre-octobre 2026**
  (§ 3.8) : CurveTQ (treillis **sans rotation**, 2,29 bits tout compris) et Tetra (réseau
  de Leech, 2,148 bits lus par poids) tiennent le front ; un Qwen3-8B Tetra à 2,76 Go
  bat au MMLU un Qwen3-4B AWQ 4 bits à 2,67 Go (69,6 contre 68,1) [litt., calc.].
- **Mais aucune de ces méthodes ne se décode en Vulkan** : EXL3 et QTIP exigent CUDA ; les
  types « KT » d'ik_llama.cpp aussi, et lus dans leur code ce ne sont pas des treillis
  (graines indépendantes par groupe de 8 : même MSE qu'une VQ 8 aléatoire [mes.]). Sous
  Vulkan, le meilleur disponible est la famille i-quants de llama.cpp, toutes décodées
  dans le produit matrice-vecteur.
- **J'ai écrit et mesuré un décodeur de treillis à décalage portable** (WGSL, Vulkan et
  DirectX 12) : **124 Go/s équivalents en Vulkan sur la RTX 4060, la vitesse du scalaire
  4 bits pour deux fois moins d'octets**, 18× le débit du PCIe [mes., § 2.3]. Quand les
  poids traversent le PCIe, le décodage est gratuit et seuls comptent les bits ; en VRAM,
  il se paie. D'où la règle de placement et la « règle des 2,6 bits » (§ 7, trou 3) : à
  sensibilité égale, une matrice résidente en VRAM mérite environ 2,6 bits de plus qu'une
  matrice lue par le PCIe.
- **À partir de quelle taille les 2 bits deviennent acceptables** (critère retenu :
  battre, à octets lus égaux, le modèle deux fois plus petit de la même famille en
  4 bits). Llama 2 avec treillis : dès 13B. ~~Familles très entraînées (Llama 3, Qwen3,
  Qwen3.5) : bien plus tard, au-delà de 30B pour la quantification après entraînement~~
  (corrigé à la reprise, § 6.2) : **le seuil dépend du codeur plus que de la taille.**
  Qwen3 avec un code de deuxième génération (Tetra) : dès 8B [litt.]. Qwen3.5 avec
  IQ2_XXS de llama.cpp, le meilleur 2 bits portable : **ni à 4B ni à 9B** — mesuré ici,
  le 9B en IQ2_XXS (2,76 Go lus par jeton) fait 10,61 de perplexité contre 8,72 pour le 4B
  en Q4_K_M (2,73 Go) (§ 5.2). **Le 9B ne rattrape le 4B qu'à partir de ≈ 3,2 bits/poids
  lus** (IQ2_M : 8,61 à 3,16 Go ; IQ3_XXS : 7,91 à 3,49 Go) ; extrapolé (D8), le vrai
  2 bits de llama.cpp ne passe le critère qu'au-delà de 30B. La dégradation croît avec les jetons d'entraînement par
  paramètre (Llama 3 70B : +76 % de perplexité à 2,07 bits, Llama 2 70B : +21 %, même
  méthode [litt.]). Mesuré sur Qwen3.5-4B : IQ4_XS +2,2 %, IQ3_XXS +12 %, IQ2_XXS +78 %
  (§ 5.1).
- **Un treillis « sans multiplication » n'est pas plus rapide sur la carte** (§ 2.4,
  écrit et mesuré ici) : code linéaire par parités, MSE 0,0712 contre 0,0682 pour mul1,
  mais 52 Go/s équivalents en Vulkan contre 121 ; le comptage de bits coûte plus que la
  multiplication entière sur la RTX 4060.
- **Ce qu'il faut construire** (§ 7) : un décodeur Vulkan d'un treillis sans rotation
  (CurveTQ : plus simple que celui mesuré au § 2.3, code mul1), un partage des bits
  selon l'étage qui sert chaque matrice, et un code emboîté (ApexQuant) dont la VRAM lit
  toutes les passes et le PCIe la première seulement.
- **En VRAM, les octets économisés ne deviennent qu'à moitié de la vitesse** (§ 5.1,
  passe 3, machine calme) : du Q4_K_M à l'IQ2_XXS, octets ÷ 1,8, jetons/s × 1,34 (4B :
  69 → 93) et × 1,49 (9B : 42 → 63) ; la part du plafond de 256 Go/s tombe de 74-84 % à
  55-68 %. Hors VRAM, au débit du PCIe, seuls les octets comptent.
- **À 2 bits, la tête de sortie devient le premier poste** pour un petit modèle à grand
  vocabulaire : 29 % des octets lus par jeton dans le « IQ2_XXS » du 4B [mes.].

---

## 1. Le cadre physique

### 1.1 Octets lus par jeton

Pour un modèle dense de `N` paramètres stockés à `b` bits par poids (métadonnées
comprises), un jeton en décodage (lot de 1) lit chaque poids une fois :

    B_jeton = N × b / 8   (+ le cache KV, + les activations, négligeables ici)

Pour un mélange d'experts, `N` devient le nombre de paramètres **actifs** par jeton. Le
plafond de débit sur un étage de bande passante `W` est `W / B_jeton`. Sur la machine
de Stone [mes. par les études 04 et 06, provisoires] : VRAM 256 Go/s théoriques ;
PCIe hôte vers carte 6,4 Go/s mesurés en Gen3 ×8, ≈ 7,6 Go/s sous charge en Gen4 ×8
(plafond théorique 15,75 Go/s) ; NVMe : ≈ 7 Go/s en lecture séquentielle, ordre de
grandeur d'un disque PCIe 4.0, à remplacer par la mesure de l'étude 01.

[calc.] Plafonds de débit, poids lus intégralement depuis l'étage nommé, sans cache :

| Modèle (paramètres actifs) | b = 16 | b = 4,5 (Q4_K) | b = 2,06 (IQ2_XXS) | b = 1,56 (IQ1_S) |
|---|---|---|---|---|
| 9 B dense, depuis la VRAM (256 Go/s) | 14 | 51 | 110 | 146 |
| 9 B dense, depuis le PCIe (7 Go/s) | 0,39 | 1,4 | 3,0 | 4,0 |
| 70 B dense, depuis le PCIe (7 Go/s) | 0,05 | 0,18 | 0,39 | 0,51 |
| MoE 3 B actifs, depuis le PCIe (7 Go/s) | 1,2 | 4,1 | 9,1 | 12 |

Lecture : hors VRAM, seuls les mélanges d'experts deviennent interactifs, et la
quantification multiplie le plafond par 16/b. C'est la raison d'être de cette étude.

### 1.2 Pourquoi la gaussienne est la bonne source d'essai

QuIP# [2402.04396], QTIP [2406.11235], HIGGS [2411.17525], QuaRot [2404.00456] et EXL3
multiplient chaque matrice de poids, à gauche et à droite, par une transformée de
Hadamard à signes aléatoires (« traitement d'incohérence »). Après rotation, les poids
d'une ligne sont presque gaussiens i.i.d. et les valeurs aberrantes ont disparu. La
quantification devient alors un problème de codage de source gaussienne, dont la borne
de Shannon est `D(R) = σ² · 2^(-2R)` (distorsion quadratique au débit de `R` bits par
échantillon). HIGGS ajoute un résultat qui relie cette MSE à la qualité : pour de petites
erreurs, l'augmentation de perplexité est approximativement une somme pondérée, couche par
couche, des MSE relatives (« théorème de linéarité ») [litt.]. Chaque gain de MSE se
traduit donc à peu près linéairement en gain de perplexité.

---

## 2. Le banc théorique, refait ici

Outil : `outils/quant-mse-gaussien.py`. Journaux : `fondations/journaux/02-quantification/`
(`mse-gaussien-passe1-partielle.log` : Lloyd-Max, VQ 8, treillis à 1 bit ;
`mse-treillis-2b.json` et `.log` : treillis à 2 bits ; les deux passes du témoin cassé).

**Témoin.** Lloyd-Max calculé analytiquement (algorithme de Lloyd sur la densité exacte)
contre Monte-Carlo sur 2^20 échantillons, seuil déclaré avant le lancement : 4 erreurs-types.
Valeurs analytiques obtenues : 0,36338 (1 bit), 0,117482 (2 bits), 0,034548 (3 bits) ;
elles égalent les valeurs classiques de Max (1960). Le témoin tient sur les trois.
**Le témoin a d'abord été trop faible** : la première cassure (un seul niveau décalé de
0,05) ne le faisait pas tomber (+0,0008 de MSE à 1 bit, sous le seuil). Cassure renforcée
(tous les niveaux décalés de 0,1) : il tombe à 1 et 2 bits ; à 3 bits le décalage reste
invisible. Les deux journaux sont gardés.

**Résultats** (MSE pour σ² = 1 ; erreur-type de Monte-Carlo entre parenthèses) :

| Quantificateur | bits/poids | MSE [mes.] | MSE publiée [litt.] |
|---|---|---|---|
| Scalaire Lloyd-Max | 2 | 0,1175 (0,0002) | 0,118 (QTIP, tab. 1) |
| VQ dim. 8, livre gaussien aléatoire 2^16 mots | 2 | 0,0935 (0,0004) | — |
| VQ dim. 8, livre calculé façon IQn_KT (graine 16 bits) | 2 | 0,0928 (0,0004) | — |
| QuIP# E8P (réseau E8, dim. 8) | 2 | non refait | 0,089 |
| **IQ2_XXS de llama.cpp** (grille réelle, parité des signes, échelles 4 bits) | 2,0625 | **0,1070 (0,0005)** | — |
| IQ2_XXS sans contrainte de parité (8 bits de signe) | 2,1875 | 0,0940 (0,0009) | — |
| Treillis à décalage L = 16, table aléatoire (RPTC) | 2,0034 | 0,0680 (0,0007) | 0,068 |
| Treillis à décalage L = 16, code « 3INST » | 2,0034 | 0,0687 (0,0007) | 0,069 |
| Treillis à décalage L = 16, code « mul1 » (EXL3) | 2,0034 | 0,0682 (0,0007) | — |
| Borne de Shannon | 2 | 0,0625 [calc.] | 0,063 |

Treillis : 8 suites de 4 096 poids, état initial libre (les 14 bits d'amorce sont
comptés : 2,0034 bits/poids) ; journal `mse-treillis-2b.json`. **Les trois codes du
treillis reproduisent le tableau 1 de QTIP à l'erreur-type près**, par un programme écrit
sans leur code. La VQ de dimension 8, elle, reste à 0,093 : le treillis ferme
(0,1175 − 0,068) / (0,1175 − 0,0625) = **90 % de l'écart** entre le scalaire et la borne,
la VQ 8 en ferme 44 %.

**IQ2_XXS sur la même source** (`outils/quant-mse-iq2xxs.py`, journal `mse-iq2xxs.json`) :
codeur écrit d'après le format (grille de 256 vecteurs lue dans `ggml-common.h`, parité des
signes, sous-échelles de 4 bits), optimal à échelle donnée ; l'échelle de super-bloc est
cherchée sur une grille, optimum intérieur et MSE plate autour (0,1054 à 0,1057 sur le
sous-échantillon ; la passe 1, dont l'optimum tombait au bord de la grille, est gardée).
Témoin : la même machinerie, avec une grille {0,45278 ; 1,51042}^8 sans parité à échelle
fixe, redonne Lloyd-Max (0,1173 ± 0,0009 contre 0,117482) ; cassé (magnitude décalée de
10 %), il tombe (0,1218). **Résultat : 0,107 à 2,0625 bits/poids, soit exactement le
scalaire optimal au même débit** (Lloyd-Max ramené à 2,0625 bits : 0,1175 × 2^(−0,125) =
0,108 [calc.]). Sur une source gaussienne, c'est-à-dire après rotation, la grille E8
d'IQ2_XXS n'apporte rien ; elle a été choisie sur des poids réels non tournés, où elle
gagne. La contrainte de parité coûte autant que le bit qu'elle économise (0,094 à
2,1875 bits contre 0,091 pour le scalaire à ce débit).

### 2.1 Treillis : résultats

Passe 1 (journal `mse-gaussien-passe1-partielle.log`, arrêtée faute de temps : 1 440 s
par combinaison sur un processeur partagé) : à **1 bit**, treillis L = 16 à table
aléatoire, 24 suites de 4 096 poids : **MSE 0,2631 ± 0,0010** [mes.], contre 0,3634 pour
Lloyd-Max et 0,25 pour la borne de Shannon. Le treillis ferme 88 % de l'écart.
Passe 2 à 2 bits (8 suites de 4 096, les trois codes) : tableau ci-dessus.

### 2.2 Le coût du décodage dans le noyau, mesuré sur la RTX 4060

Outil : `outils/quant-gemv-treillis.cu` (CUDA 13.1.2, `-arch=sm_89`), écrit de zéro.
Produit matrice-vecteur 16 384 × 16 384 (268 M poids, bien au-delà des 32 Mio de cache
L2), quatre formats : FP16 ; scalaire 2 bits ; **treillis à décalage 2 bits, code
calculé « mul1 », L = 16, tuile de 256 poids lue circulairement** ; scalaire 4 bits.
Les deux noyaux 2 bits ont la même disposition et le même parcours : l'écart entre eux
est le coût du décodage du treillis. Témoin : 64 lignes recalculées sur le processeur,
erreur relative < 1e-3 déclarée avant ; tient sur les quatre formats (pire 2,2e-5) ;
cassé (constante du code faussée côté processeur seul), il tombe sur le treillis et
seulement sur lui. Séries ABBA, 3 séries × 50 répétitions (`gemv-2.json`).

**La carte était partagée** (l'échelle llama.cpp du § 5 et d'autres agents tournaient) :
des passes de la référence FP16 montent à 20 ms au lieu de 2,2. Je retiens les paires
ABBA où la référence est propre (≈ 2,2 ms) ; le treillis, lui, est stable à ±0,3 %
dans toutes les séries.

| Format | octets de poids | temps (ms) | Go/s équivalents | part de 256 Go/s | accélération / FP16 |
|---|---|---|---|---|---|
| FP16 | 512 Mio | 2,17 – 2,25 | 238 – 247 | 93 – 97 % | 1 |
| scalaire 4 bits | 128 Mio | 0,567 – 0,580 | 231 – 237 | 90 – 93 % | 3,8 |
| scalaire 2 bits | 64 Mio | 0,317 – 0,319 | 211 – 212 | 82 % | 6,9 |
| treillis mul1 2 bits | 64 Mio | 0,430 – 0,433 | 155 – 156 | 61 % | 5,1 |

[mes.] Lecture :
- La VRAM de la carte rend 238 à 247 Go/s sur un flux simple, 93 à 97 % du plafond.
- **Le treillis est limité par le calcul, pas par la mémoire** : environ 10 opérations
  entières par poids (une multiplication, un `dp4a`, des décalages) le plafonnent à
  624 milliards de poids par seconde dans ce noyau naïf ; il coûte 36 % de temps de plus
  que le scalaire 2 bits, et reste 1,33× plus rapide que le 4 bits. Un noyau soigné
  (deux poids par multiplication, `lop3`, comme EXL3) réduirait l'écart ; je ne l'ai pas
  écrit.
- **Hors VRAM, ce coût disparaît.** Quand les poids arrivent par le PCIe à ~7 Go/s, le
  décodeur du treillis va 22× plus vite que le lien. Dans le régime de troncons, le
  décodage est gratuit : seuls comptent les bits, et le treillis en économise
  (§ 7, trou 1). C'est le résultat le plus important de cette mesure.
- Ce banc mesure CUDA ; le § 2.3 refait la mesure en Vulkan et en DirectX 12.
- La passe 1 de ce banc était mal conçue (une voie par tuile, lecture dispersée des
  activations : 14 Go/s quel que soit le format) ; journal gardé
  (`gemv-1-noyau-mal-concu.json`).

### 2.3 Le même décodage en Vulkan et en DirectX 12 (premier treillis portable mesuré)

Outil : `outils/quant-vulkan-gemv` (Rust, wgpu 30.0.1, shaders WGSL écrits de zéro ;
Naga traduit en SPIR-V pour Vulkan et en HLSL pour DirectX 12). Même matrice, même
disposition de tuile, même témoin (64 lignes refaites sur le processeur, < 1e-3 ; tient
sur les quatre formats et les deux API ; cassé, il tombe sur les deux variantes du
treillis et seulement sur elles). Le treillis est décodé de deux façons : somme d'octets
écrite à la main, ou `dot4U8Packed` (l'équivalent WGSL de `dp4a`). Un noyau « lecture
seule » donne le plafond sur la même API. Pilote NVIDIA 591.91, 5 séries ABBA × 50.

Trois passes, gardées toutes les trois : la passe 1 indexait un tableau local par une
variable de boucle (le 2 bits tombait à 44 Go/s, sous le 4 bits) ; la passe 2 le
remplace par des vec4 (2 bits : 158 Go/s) mais chaque ligne relisait tout le vecteur
d'activations dans le cache L2 (1 Gio de trafic L2 pour 64 Mio de poids) ; la passe 3
fait quatre lignes par groupe de 32 voies et lit les activations une fois pour les
quatre. Résultats de la passe 3 (médianes, écart médiane-minimum < 1 %) [mes.] :

| Format | Vulkan ms | Vulkan Go/s équiv. | DX12 ms | DX12 Go/s équiv. |
|---|---|---|---|---|
| lecture seule (plafond) | 0,273 | 246 | 0,275 | 244 |
| scalaire 4 bits | 0,538 | 249 | 0,542 | 248 |
| scalaire 2 bits | 0,312 | 215 | 0,341 | 197 |
| treillis mul1 2 bits, somme à la main | 1,100 | 61 | 0,994 | 68 |
| treillis mul1 2 bits, `dot4U8Packed` | 0,673 | 100 | 1,120 | 60 |
| treillis mul1 2 bits, `dot4U8Packed`, extraction sans sélection (passe 4) | **0,541** | **124** | — | — |

Passe 4 (`vulkan-gemv-4.json`) : refait toute la passe 3 (scalaire 2 bits 214 Go/s contre
215, `dot4` 98,7 contre 100 : la mesure se reproduit à 1 % près) et ajoute une extraction
de la fenêtre de 16 bits sans `select` : un seul mot bas choisi par voie, puis
`((lo >> (b−1)) >> 1 | w1 << (32−b)) & 0xffff` pour les 8 décalages. **Le treillis 2 bits
va alors aussi vite que le scalaire 4 bits (0,541 contre 0,538 ms) en lisant deux fois
moins d'octets.**

Lecture [mes.] :
- **Un treillis à décalage se décode en shader portable**, dans le produit, sans matrice
  intermédiaire : 124 Go/s équivalents en Vulkan (passe 4), 68 en DirectX 12. À ma connaissance,
  aucune mesure de ce genre n'est publiée (§ 7, trou 1).
- `dot4U8Packed` vaut 1,6× en Vulkan (instruction entière native) et rien en DirectX 12
  (où Naga semble l'émuler) : **Vulkan est l'API à viser.**
- Le décodage coûte : en Vulkan, le treillis 2 bits reste 1,7× plus lent que le scalaire
  2 bits (passe 4) et **aussi lent que le scalaire 4 bits** quand les poids sont en VRAM ;
  en CUDA (§ 2.2, une ligne par chaîne) il était 1,33× plus rapide que le 4 bits. Une
  extraction mieux écrite a gagné 1,25× en une passe : le plafond du décodeur n'est pas
  atteint.
- **D'où une règle de placement**, cohérente avec la règle des 2,6 bits du § 7 (trou 3) :
  le treillis pour les poids qui traversent le PCIe (124 Go/s de décodage, 18× le débit
  du lien : gratuit), le scalaire ou les i-quants à plus de bits pour les poids résidents
  en VRAM (où chaque opération de décodage se paie).
- Le scalaire 2 bits atteint 88 % du plafond en Vulkan : à ce débit, les noyaux de
  llama.cpp (IQ2) ont la marge de faire mieux que mon scalaire, pas moins.

### 2.4 Un treillis sans multiplication : code linéaire par parités (reprise, essai)

**Pourquoi.** XOR-Trellis (2610.00432, § 3.8) annonce un décodeur à ≈ 14 portes XOR par
valeur, sans publier ses masques ; CurveTQ montre qu'un treillis sans rotation fait mieux
que QTIP. Question posée ici : un code calculé fait seulement de parités, écrit de zéro,
garde-t-il la MSE des codes de QTIP et d'EXL3, et se décode-t-il plus vite sur la carte ?

**Le code** (`outils/quant-mse-xor.py`). État de 16 bits `s` ; index
`j = Σ_{q=0..3} parité(s & m_q) · 2^q`, fonction linéaire de `s` sur GF(2) ; valeur
`palette[j]`, palette des 16 quantiles gaussiens `Φ⁻¹((j + ½)/16)` renormalisés. Si les
4 masques sont de rang 4, chaque index est atteint par 2^12 états : la loi des valeurs
émises est uniforme sur la palette. 16 jeux de masques tirés au hasard, choisis sur une
suite courte, le meilleur mesuré sur 8 suites de 4 096.

**Témoin** : le code mul1 repassé par la même machinerie redonne **exactement** 0,068236
(même générateur consommé dans le même ordre : mêmes suites que la passe 2) ; décalé de
0,6, il tombe (0,0996). Journaux `mse-xor-P4.json`, `.log`, `mse-xor-temoin-casse.json`.

**Résultat [mes.]** : **MSE 0,0712 ± 0,0009** à 2,0034 bits (masques `0xdfea, 0x30b1,
0xb566, 0x753c`), contre 0,0682 pour mul1 sur les mêmes suites : +4,3 %, soit
½ log₂(0,0712/0,0682) = **0,031 bit** de perte [calc.] ; toujours 0,29 bit devant
IQ2_XXS et 0,20 devant la VQ de dimension 8. ~~Réserve : le gain optimal tombe au bord de
la grille cherchée (1,05) pour les deux codes~~ Vérifié : avec la grille élargie à
0,75-1,40, le gain retenu reste 1,05 pour les deux codes et les MSE sont identiques
(`mse-xor-P4-gain14.json`) : 1,05 est un optimum intérieur. Palette uniforme (valeur
= 2j − 15, sans table) : 0,0842 ± 0,0013 au gain 1,10 (grille élargie ; 0,0854 au bord
1,05 avec la grille étroite) : 0,08 bit derrière la palette des quantiles.

**Vitesse [mes.]** : décodeur `treillis-parite` ajouté au banc wgpu (4 `countOneBits`
vectoriels par groupe de 4 fenêtres, palette de 16 flottants en mémoire partagée ; témoin
64 lignes : tient en Vulkan et en DirectX 12, tombe cassé, `vulkan-parite-temoin-casse.json`).
Passe 5 et 6 (`vulkan-gemv-5.json`, `vulkan-gemv-6-masques-retenus.json`, `dx12-gemv-5.json`) :

| Format | Vulkan ms | Vulkan Go/s équiv. | DX12 ms | DX12 Go/s équiv. |
|---|---|---|---|---|
| scalaire 2 bits | 0,325 | 206 | 0,350 | 192 |
| treillis mul1, `dot4` v2 | 0,554 – 0,563 | 119 – 121 | 1,022 | 66 |
| **treillis par parités** | **1,293 – 1,298** | **52** | 1,265 | 53 |
| scalaire 4 bits | 0,554 | 242 | 0,556 | 242 |

**Lecture.** Sur un GPU, « sans multiplication » ne veut pas dire plus vite : la
multiplication entière 32 bits et `dot4U8Packed` sont des instructions natives, alors que
quatre comptages de bits par valeur et huit lectures en mémoire partagée par voie (avec
conflits de banc probables) coûtent 2,3× plus. L'avantage de XOR-Trellis est pour un
circuit dédié, pas pour une RTX 4060 [mes.]. À 52 Go/s équivalents le décodeur va encore
7× plus vite que le PCIe : dans le régime de troncons il reste gratuit, mais **mul1 reste
le meilleur code à décoder sur cette carte** (même MSE à 0,03 bit près, 2,3× plus rapide
en VRAM). La variante sans table (palette uniforme, valeur = (2j − 15)·c, aucune lecture
en mémoire partagée) va **à la même vitesse** (1,304 ms contre 1,288 en Vulkan, passe 7,
`vulkan-gemv-7.json` ; 1,344 ms en DX12) : ce n'est pas la table qui coûte, ce sont les
quatre comptages de bits par valeur. Elle perd en plus 0,08 bit de MSE : écartée.

---

## 3. Les techniques, une par une

Pour chaque technique : mécanisme, bits par poids réels, perte publiée, coût de la
quantification, décodage dans le noyau, Vulkan, maturité, licence du dépôt (lue dans
le clone, `~/dev/lectures/troncons/quantification/<dépôt>/LICENSE`).

### 3.1 Les rotations : QuaRot, SpinQuant, transformée de Hadamard aléatoire

- **Mécanisme.** `W' = H_g · diag(s) · W · diag(s') · H_d`, où `H` est une matrice de
  Hadamard normalisée et `s` des signes aléatoires ; l'inverse est fusionné dans les
  couches voisines (QuaRot) ou appliqué en ligne par une transformée rapide en
  `O(n log n)` (QuIP#, QTIP, EXL3). SpinQuant apprend la rotation (optimisation sur la
  variété de Stiefel, « Cayley SGD ») au lieu de la tirer au hasard.
- **Ce qu'elle gagne.** Elle ne réduit pas les bits : elle rend la source gaussienne, ce
  qui permet aux codes du § 3.4 d'approcher la borne. Le noyau de Hadamard rapide coûte
  `n log₂ n` additions par vecteur d'activation, négligeable au lot de 1.
- **Où elle sert.** QuaRot et SpinQuant visent surtout W4A4KV4 (poids, activations et
  cache à 4 bits) : SpinQuant annonce un écart de 2,9 points de justesse moyenne au plein
  modèle sur Llama 2 7B en W4A4KV4 [litt., résumé arXiv]. Pour nous (poids seuls, sous
  4 bits), la rotation est une brique, pas une méthode.
- **Vulkan.** ~~Une transformée de Hadamard rapide s'écrit en shader de calcul sans
  difficulté ; aucune version publique n'est intégrée à llama.cpp pour les poids.~~
  Corrigé le 2026-10-15 en relisant le code : llama.cpp (en tête 843e7dc) charge des
  poids « repliés » par une Hadamard par blocs (métadonnées `prism.hadamard.*` de PrismML,
  transformée de Sylvester-Walsh normalisée, blocs de 64 à 512, signes explicites ou
  identité ; `src/llama-model.cpp`) et applique la transformée aux activations par un
  opérateur FWHT, **y compris en Vulkan** (`ggml_vk_can_use_fwht`, pipelines
  `pipeline_fwht_f32` pour 64 à 512, déclenchés par l'indice `GGML_HINT_SRC0_IS_HADAMARD`).
  La brique « rotation » existe donc déjà en Vulkan dans llama.cpp ; manque le codeur
  qui en profite.
- **Licences.** QuaRot : Apache 2.0. SpinQuant : **CC BY-NC 4.0** (non commercial ;
  à ne pas embarquer).

### 3.2 Les quantifications scalaires par groupes (K-quants, EfficientQAT, HIGGS)

- **K-quants de llama.cpp** (lus dans `ggml/src/ggml-common.h`, en tête le 2026-10-15).
  Super-bloc de 256 poids, sous-blocs de 16 ou 32 avec échelle (et minimum) codés sur
  4 à 8 bits, une ou deux échelles fp16 par super-bloc. Bits par poids exacts [calc.
  depuis les `static_assert`] : Q2_K 2,625 ; Q3_K 3,4375 ; Q4_K 4,5 ; Q5_K 5,5 ;
  Q6_K 6,5625. Les fichiers « Q2_K », « Q3_K_M » sont des mélanges (certaines matrices
  montent d'un ou deux crans) : leurs bits réels se lisent dans le fichier (§ 5).
- **imatrix.** `llama-imatrix` accumule, pour chaque colonne d'entrée `j` d'une matrice,
  `I_j = Σ_t x_{t,j}²` sur un texte d'étalonnage ; la quantification minimise alors
  `Σ_j I_j (w_j − q_j)²` au lieu de la MSE brute. C'est l'approximation diagonale du
  Hessien `XᵀX` qu'utilisent GPTQ et QuIP#.
- **EfficientQAT** (2407.11062, ACL 2025, MIT). Scalaire uniforme par groupes (w2g64 :
  2 bits + échelle et zéro par groupe de 64), entraîné par blocs puis de bout en bout sur
  les seules échelles. Llama 2 7B : 5,47 → 6,86 (w2g64, 2,3 Go) ; Llama 2 70B :
  3,32 → 4,52 ; Llama 3 8B : 6,14 → 9,41 ; Llama 3 70B : 2,85 → 6,08 (WikiText-2,
  README du dépôt) [litt.]. Coût : Llama 2 70B en 2 bits sur une A100-80GB en 41 heures
  (résumé arXiv) [litt.].
- **HIGGS** (2411.17525). Hadamard aléatoire puis grille MSE-optimale pour la gaussienne,
  scalaire ou vectorielle (p = 2 ou 4), sans données d'étalonnage ; « HIGGS dynamique »
  choisit les bits par couche par un solveur (CP-SAT) sous budget moyen. Llama 3.1 8B :
  FP16 5,607 ; 3,25 bits → 6,388 (dynamique) ; 4,0 bits → 5,910 [litt., tab. 3]. Noyau
  FLUTE (Apache 2.0, CUDA) : 173 jetons/s à 2 bits contre 57 en FP16 sur RTX 4090
  (Llama 3.1 8B, lot de 1) [litt., tab. 1].
- **Vulkan.** Toutes les K-quants : oui (shaders `mul_mat_vec_q2_k.comp` à
  `mul_mat_vec_q6_k.comp`, décodage en registres dans le produit matrice-vecteur).
  HIGGS/FLUTE : CUDA seulement.

### 3.3 Les codes vectoriels sur réseaux et livres de codes (QuIP#, AQLM, GPTVQ, VPTQ, i-quants)

- **QuIP#** (2402.04396, ICML 2024, GPL-3.0). Hadamard + livre « E8P » : 2^16 vecteurs de
  dimension 8 tirés du réseau E8, construits à partir d'une petite table de base par
  signes et décalage pour tenir en cache (détail non relu ici), plus ajustement fin. MSE gaussienne 0,089 à 2 bits [litt.].
  Llama 2 70B à 2 bits : 3,91 (contexte 4096) [litt., QTIP tab. 5].
- **AQLM** (2401.06118, ICML 2024, Apache 2.0). Quantification additive : chaque groupe de
  8 poids est la somme de `M` mots tirés de `M` livres appris (« 1x16 » : un livre de
  2^16 mots, « 2x8 » : deux livres de 256). Llama 2 7B 1x16 : 5,92 (2,4 Go) ; 70B 1x16 :
  3,83 (18,8 Go) ; avec PV-tuning 7B 1x16g8 : 5,68 [litt., README]. Le livre 1x16 pèse
  2^16 × 8 × 2 octets = 1 Mio par couche : il ne tient pas en mémoire partagée, d'où un
  décodage lent au lot de 1 ; « 2x8 » tient mais perd en qualité (7B : 6,69).
- **PV-tuning** (2405.14852). Ajustement fin de bout en bout d'une représentation
  quantifiée (AQLM ou QuIP#), qui alterne mise à jour des paramètres continus (P) et
  des codes discrets (V) au lieu de l'estimateur « straight-through ». Llama 2 7B :
  5,12 → 5,84 à 2,02 bits ; 70B : 3,12 → 3,78 à 2,07 bits ; **Llama 3 70B : 2,59 → 4,57
  à 2,07 bits** ; Llama 3 8B : 5,54 → 6,99 à 2,01 bits ; et 1,01 bit : 11,17 [litt.,
  tab. 2]. Coût : jusqu'à 2 jours sur 8 GPU (≈ 384 heures de carte) pour le plus long
  passage, 8 jours pour converger [litt.].
- **GPTVQ** (2402.15319). VQ en dimension 1 à 4 avec mise à jour de type GPTQ et livres
  par groupes ; quantification de Llama 2 70B en 3 à 11 heures sur une H100 selon le
  réglage [litt., résumé].
- **VPTQ** (2409.17066, EMNLP 2024, MIT). VQ de dimension 8 ou 12 avec livre de 2^16
  centroïdes, résiduel optionnel, initialisation pondérée par le Hessien. Llama 2 7B
  2,02 bits : 6,13 ; 70B 2,07 bits : 3,93 ; débit 39,9 jetons/s (7B) ; coût 2 h (7B) à
  19 h (70B) de carte [litt., README]. Le débit modeste vient probablement des accès
  indirects dans un livre de 2^16 × 8 (hypothèse, non mesurée).
- **i-quants de llama.cpp** (MIT). Lus dans `ggml-common.h` et les shaders Vulkan
  (`vulkan-shaders/types.glsl`, `mul_mat_vec_iq*.comp`). Ce sont des VQ sur des grilles
  dérivées de points du réseau E8 (magnitudes), avec bits de signe à parité imposée :
  - IQ2_XXS : par 32 poids, 4 index de 8 bits dans une grille de 256 vecteurs de
    dimension 8, 4 × 7 bits de signe (le 8e signe est fixé par la parité), une sous-échelle
    de 4 bits ; échelle fp16 par 256 → **2,0625 bits/poids** [calc.].
  - IQ2_XS (grille de 512, 9 bits) 2,3125 ; IQ2_S (grille de 1024) 2,5625 ;
    IQ3_XXS (grille de 256 vecteurs de dimension 4) 3,0625 ; IQ3_S 3,4375 ;
    IQ1_S (grille de 2048 vecteurs ternaires) 1,5625 ; IQ1_M 1,75 ; IQ4_XS
    (scalaire non uniforme, 16 niveaux) 4,25 ; IQ4_NL 4,5 [calc.].
  - Les grilles (256 à 2048 entrées) sont copiées en **mémoire partagée** au début de
    chaque groupe de travail ; le produit scalaire est fait directement sur les valeurs
    de la grille, signe appliqué, puis multiplié par l'échelle : **aucune matrice
    décompressée n'est écrite en mémoire**. Tous ces types ont un shader
    `mul_mat_vec_*.comp` en Vulkan [lu].
  - Construction de la grille d'IQ2_XXS (PR #4773, 2024-01-04) : 256 points choisis parmi
    les 3 281 points utiles du réseau E8 (magnitudes 1/2, 3/2, 5/2) d'après leur
    fréquence d'emploi sur plusieurs modèles ; la parité des signes est imposée en
    retournant le signe du poids le moins important. Perplexité WikiText-2 (contexte
    4096), même jeu que QTIP : Llama 2 7B 7,067 ; 13B 5,728 ; 70B 4,079 (17,03 Gio)
    [litt., PR]. Contre QTIP à 2 bits avec ajustement fin (5,86 ; 5,11 ; 3,70) et FP16
    (5,12 ; 4,57 ; 3,12) : **+38 % / +25 % / +31 % pour IQ2_XXS, +14 % / +12 % / +19 %
    pour QTIP** [calc. depuis la litt.]. Les deux chiffres ne sortent pas du même
    programme d'évaluation (llama-perplexity contre le script de QTIP) : écart de
    méthode possible, à refaire.
- **SAGE** (2610.14745, 2026-10-10, code annoncé sur GitHub, licence non vérifiée). VQ
  à 2 bits ; Qwen3-30B-A3B garde 95,3 % du score moyen BF16 ; ×2,55 de bout en bout
  contre FP16 avec un noyau CUDA [litt., résumé].
- **Réseau de Leech** (2609.02652, 2026-09-02, prépublication non relue). Code de
  dimension 24 ; l'article mesure qu'un noyau à treillis QTIP lit 2,40× moins d'octets que
  leur disposition servie et va 2,27× plus vite ; coût qualité à 4B : perplexité ×1,38 et
  −14,7 points MMLU, qui diminue avec la taille [litt., résumé].

### 3.4 Les codes en treillis (QTIP, EXL3, CCQ) et le faux treillis d'ik_llama.cpp

- **QTIP** (2406.11235, NeurIPS 2024, GPL-3.0). Quantification par treillis (TCQ) dont le
  treillis est « à décalage » : l'état est une fenêtre de `L` bits du flux codé ; chaque
  poids fait entrer `k` bits (`k` = débit) ; la valeur reconstruite est `f(état)`. Le
  codage cherche le chemin de distorsion minimale par l'algorithme de Viterbi sur des
  suites de 256 poids, avec une contrainte « tail-biting » (l'état final rejoint l'état
  initial) pour que le coût soit exactement `k` bits/poids. Comme `f` ne dépend que de
  `L` bits, la table peut être **calculée** au lieu d'être lue : « 1MAD » (générateur
  congruentiel `a = 34038481, b = 76625530`, somme des 4 octets, `(x − 510)/147,8`) ou
  « 3INST » (générateur `a = 89226354, b = 64248484`, masque et XOR, somme de deux
  demi-flottants) [litt., algorithmes 1 et 2]. MSE à 2 bits : 0,068 à 0,071 [litt.].
  Llama 2 à 2 bits avec ajustement fin : 7B 5,86 ; 13B 5,11 ; 70B 3,70 (contexte 4096)
  [litt., tab. 5]. Débit : 188 jetons/s à 2 bits contre 55,9 en FP16, Llama 2 7B, RTX
  6000 Ada [litt.].
- **EXL3** (exllamav3, MIT, en tête 2026-10-14). « Variante simplifiée de QTIP ». Lu dans
  `exllamav3_ext/quant/exl3_dq.cuh` et `codebook.cuh` : chaque poids est décodé d'un mot
  de 16 bits pris à la position `t·k` du flux de `k·256` bits d'une tuile de 256 poids,
  **lu circulairement** (indice modulo la taille de la tuile : c'est le tail-biting) ;
  le mot passe par un code calculé (« mul1 » par défaut : multiplication par
  `0x83DCD12D`, somme des 4 octets par `dp4a`, mise à l'échelle ; ou « mcg », « 3inst »).
  Bits entiers de 1 à 8 par matrice, débit fractionnaire par mélange de matrices ;
  rotation de Hadamard ; quantification en une passe, « quelques minutes pour les petits
  modèles, quelques heures pour 70B+ sur une carte grand public » (README). **CUDA ≥ 12.4
  (ou ROCm) obligatoire.** Il sait aussi garder la table d'enchâssement quantifiée en RAM
  ou la lire depuis le disque.
- **CCQ** (2507.07145, Baidu). Codes convolutifs (une famille de treillis) avec codage
  hybride et grappes de codes, 2,0 à 2,75 bits/poids, sans table ; ERNIE-4.5-300B-A47B
  ramené à 89 Go et servi sur une seule carte ; DeepSeek-V3 à 184 Go [litt., résumé].
- **IQn_KT d'ik_llama.cpp** (MIT, en tête 2026-10-14). Lu dans
  `ggml/src/iqk/iqk_quantize.cpp` (classe `QuantizerIQKT`) et
  `ggml/src/ggml-cuda/convert.cu` : chaque groupe de 8 poids est décodé d'une graine de
  16 bits **indépendante** (graine + 4096, puis 8 pas de `x ← 0xCBAC1FED·x`, somme des
  4 octets masqués à 6 bits, −126) ; la recherche est un plus proche voisin par
  grappes, pas un Viterbi. **C'est une VQ de dimension 8 à livre calculé, pas un
  treillis** : les états ne se chevauchent pas. Ma mesure (§ 2) la place au niveau d'une
  VQ de dimension 8 aléatoire (0,0928 contre 0,0935), loin d'un vrai treillis. L'auteur
  lui-même écrit que son treillis diffère de celui de QTIP (PR llama.cpp #19726,
  fermée le 2026-02-23). Bits : IQ2_KT 2,125 ; IQ3_KT 3,125 ; IQ4_KT 4,0 ; IQ1_KT 1,75
  [calc. depuis les `static_assert`], plus une échelle par ligne. Moteurs : CPU (AVX2
  obligatoire pour quantifier), CUDA, Metal. **Pas de Vulkan.**

### 3.5 L'ajustement de l'arrondi : YAQA

YAQA (2505.22988, ICML 2026, Tseng et De Sa). Arrondi adaptatif qui préserve la
distribution de sortie du modèle entier (approximation de Kronecker du Hessien de la
divergence KL) au lieu de l'erreur de chaque couche ; environ 30 % d'erreur en moins que
GPTQ et LDLQ [litt., résumé]. Se combine aux codes du § 3.4.

### 3.6 Les modèles natifs en très bas débit (BitNet, ParetoQ, Bonsai, TQ, MXFP4)

- **BitNet b1.58** (2402.17764 ; rapport 2B4T 2504.12285). Poids ternaires {−1, 0, +1}
  par une échelle absmean, entraînés ainsi dès le départ ; 2 milliards de paramètres,
  4 000 milliards de jetons. Moteur bitnet.cpp (MIT) : noyaux CPU I2_S, TL1, TL2 ;
  noyau GPU officiel W2A8 en CUDA (mai 2025) [lu dans le dépôt].
- **ParetoQ** (2502.02631, NeurIPS 2025). Entraînement à la quantification depuis un
  modèle pré-entraîné, de 1 à 4 bits. Transition nette entre 2 et 3 bits : à 3 bits et
  plus le modèle reste proche de sa distribution, à 2 bits et moins il se réorganise.
  Llama 3 8B : 6,15 → 8,0 à 2 bits ; 8,6 en ternaire ; 9,5 à 1 bit (30 milliards de
  jetons d'ajustement) ; le meilleur partage est ≈ 90 % de pré-entraînement plein et
  10 % d'ajustement quantifié [litt.].
- **Bonsai de PrismML et Q1_0 / Q2_0 de llama.cpp.** Q1_0 : signe sur 1 bit et une
  échelle fp16 par 128 poids, **1,125 bits/poids** ; Q2_0 : 2 bits et une échelle par
  64 poids, 2,25 bits/poids [calc. depuis `ggml-common.h`] ; tous deux ont des shaders
  Vulkan. Ce sont des formats pour modèles entraînés en 1 bit ; appliqués à un modèle
  ordinaire, ils détruisent la qualité (§ 5).
- **TQ1_0 / TQ2_0** (llama.cpp). Ternaire empaqueté en base 3 (5 trits par octet) :
  1,6875 bits/poids ; ou 2 bits par trit : 2,0625 [calc.]. Vulkan : oui.
- **MXFP4 et NVFP4.** MX (2310.10537, spécification OCP) : 32 éléments FP4 (E2M1)
  partageant un exposant E8M0, **4,25 bits/poids**. NVFP4 (llama.cpp) : 64 éléments FP4,
  une échelle UE4M3 par 16, **4,5 bits/poids** [calc.]. Pré-entraînement NVFP4 d'un 12B
  sur 10 000 milliards de jetons, qualité « comparable à FP8 » [litt.,
  2509.25149]. Les unités FP4 natives n'existent que sur Blackwell ; sur la RTX 4060
  (Ada), ce sont des formats de stockage décodés dans le shader (llama.cpp a
  `dequant_mxfp4.comp` et `dequant_nvfp4.comp`). Ils ne descendent pas sous 4 bits.

### 3.8 Le front d'octobre 2026 (veille du jour, ajoutée à la reprise)

Recherche du 2026-10-15 par l'API `export.arxiv.org` (tri par date de dépôt), puis lecture
des PDF (`pdftotext`) sous `~/dev/lectures/troncons/quantification/pdf/`.
Tous les chiffres de ce paragraphe sont [litt.], non reproduits.

- **CurveTQ** (2610.09212, 2026-10-06). Treillis **sans rotation** : la diagonale `D` de la
  factorisation LDL du Hessien, que LDLQ calcule déjà sans s'en servir dans la recherche,
  entre dans la métrique de branche du Viterbi (`Σ (w_i − ŵ_i)² / d_i²` au lieu de la
  distance euclidienne). Ils montrent que pondérer dans la base native et tourner sont des
  **substituts**. S'y ajoutent un champ d'échelles factorisé (0,068 bit/poids), une table de
  quantiles fermée, et **un état initial stocké par bloc** (≈ 0,22 bit/poids) au lieu du
  tail-biting. Débit compté avec toute l'information annexe : 2,29 bits/poids. WikiText-2,
  contexte 4096, **sans ajustement fin** : Qwen3-4B FP16 9,72 → **11,50** (QTIP 2,00 bits :
  15,36) ; Llama-3.1-8B 6,67 → 9,16 ; **Qwen3-32B 6,17 → 6,90 (+12 %)** ; Qwen3.6-35B-A3B
  (MoE) 6,12 → 6,76 (+10 %), le premier résultat en treillis sur un mélange d'experts.
  Leur ablation chiffre le tail-biting de QTIP sur blocs de 64 : +4,10 de perplexité et
  −5,1 points en aval contre l'état stocké. Décodeur CUDA (RTX 3090, lot de 1) : Qwen3-4B
  2 bits 160,8 jetons/s contre 153,6 pour QTIP ; la Hadamard côté activations coûte 4 à
  11 % du débit au lot de 1. Code : non trouvé à la date de consultation.
- **Proteus** (Yang et al., ICML 2026, Baidu ; pas de version arXiv trouvée, cité par
  CurveTQ). Code calculé « sans table » par rupture de réseau, garde rotation et recherche
  euclidienne ; Qwen3-4B 2 bits : 14,21.
- **XOR-Trellis** (2610.00432, 2026-09-30). Décodeur de treillis vers une palette FP4 par
  des parités masquées et deux XOR : **≈ 14 portes XOR2 par valeur**, pensé pour suivre le
  débit de la mémoire ; pondération par courbure, sans Hadamard. Llama-3.1-8B (2 bits,
  contexte 4096) : BF16 5,84, QTIP-3INST 8,48, XOR-Trellis sans rotation pondéré 8,00.
  C'est la forme de décodeur la plus proche d'un shader portable : aucune multiplication.
- **Tetra** (2609.35465, 2026-09-28 ; code Apache-2.0, `pjmalandrino/llvq`). Réseau de
  Leech (dimension 24) : 48 bits par bloc de 24 poids, dont un treillis à 64 états du code
  de Golay et une table partagée de 16 Kio ; **2,148 bits lus par poids** dans le produit
  (leur disposition précédente en lisait 4,804). Fichiers complets (enchâssements en
  4 bits, matrices les plus sensibles en int4, échelles de ligne réentraînées 1,7 h sur une
  L40S pour le 4B) : **Qwen3-4B, 8B, 14B à 2,73, 2,70, 2,73 bits par paramètre, modèle
  entier**. MMLU complet : 63,37 / 69,58 / 75,66, contre AWQ 4 bits (5,30 / 5,96 / 5,40 bits
  par paramètre) 68,14 / 73,79 / 78,12 et FP16 70,14 / 75,05 / 78,88. **IQ2_XXS de
  llama.cpp sur Qwen3-4B (2,48 bits par paramètre) : 39,78**, 23,6 points sous Tetra.
  Plan d'expérience préenregistré, prédictions fausses publiées.
- **GSQ** (2604.18556, 2026-04-20 / 2026-05-15 ; code Apache-2.0, `IST-DASLab/GSQ`).
  Scalaire symétrique par groupes de 128 (2,13 et 3,13 bits/poids), affectations à la grille
  apprises par relaxation Gumbel-Softmax. Llama-3.1-8B-Instruct, moyenne zéro-shot à
  2 bits : GSQ 68,55, QTIP 69,88, EfficientQAT 63,79, GPTQ 37,53 ; 70B : GSQ 75,57, QTIP
  77,25, PV-tuning 76,27. **Il se projette dans les formats K-quants de GGUF** : Qwen3-8B
  Q2_K, moyenne AIME25/GPQA/MMLU-Pro 50,03 → 56,28 ; Q3_K_M 60,52 → 61,61. C'est le
  seul gain de l'état de l'art qui arrive **déjà décodable en Vulkan** (même format, mêmes
  shaders).
- **ApexQuant** (2610.07904, 2026-10-06 ; code sans licence déclarée). Code **emboîté** :
  on requantifie le résidu après une nouvelle rotation aléatoire, passe après passe ; chaque
  préfixe des passes est un modèle valide à plus bas débit. Le « prix de l'élasticité » est
  une distance horizontale constante à `D(R) = 2^(−2R)` par passe : 0,45 bit pour un
  scalaire, 0,10 bit pour un treillis (leur proposition 3). C'est la brique d'un modèle
  qu'on charge par couches de précision (§ 7, trou 7).
- **Q-Palette** (2509.20214, NeurIPS 2025 ; code MIT). Répartition des bits entre couches
  par un sac à dos à choix multiples sous budget de **mémoire ou de latence profilée**, avec
  des quantificateurs fractionnaires (treillis, VQ, scalaire). Cela nuance le trou 3 du § 7.
- **BITCOS** (2609.16338, 2026-09-14). Les modèles ternaires réels ont jusqu'à 51,5 % de
  zéros ; un bitmap de présence plus les signes compactés coûte `2 − z` bits par poids, soit
  1,485 bit sur le plus creux des 29 modèles mesurés, contre 1,625 pour l'empaquetage à
  5 trits par octet ; décodage jusqu'à 1,27× plus rapide sur GPU Xe2.
- **Tied Trit-Planes** (2608.08910, 2026-08-09). Code à 9 niveaux (deux plans ternaires
  d'échelles liées dans un rapport 3) replié sans perte en 4,0625 bits/poids, **même octets
  sur le disque, dans le cache d'experts et à l'entrée du noyau** ; experts de
  DeepSeek-V4-Flash (284B-A13B) lus depuis le SSD sur un portable de 64 Go. Ils observent
  une dissociation : erreur de reconstruction et perplexité pires, fidélité à l'API égale.
- **BCJR-QAT** (2605.10655) : relaxation différentiable du Viterbi (somme-produit à
  température `T`) ; −0,084 de perplexité contre QTIP sur Llama-3.2-1B à 2 bits.
- **Universalité métrique** (2602.05790, 2026-02-05 / 2026-06-15) : il existe un livre
  universel presque optimal pour toutes les statistiques d'activations, au prix d'au plus
  **0,11 bit par dimension** (preuve non constructive). Borne utile : un codeur sans données
  d'étalonnage n'est condamné qu'à 0,11 bit de l'optimum adapté.

### 3.9 Les lois d'échelle de la quantification

- « Low-bit quantization favors undertrained LLMs » (2411.17691, ACL 2025) : plus de
  1 500 points Pythia (160M à 12B) ; la dégradation due à la quantification croît avec le
  nombre de jetons d'entraînement par paramètre et décroît avec la taille [litt.].
- « An Empirical Study of Qwen3 Quantization » (2505.02214) : Qwen3 se dégrade plus que
  les générations précédentes à 3 bits et moins ; à 2 bits avec GPTQ (g128), la
  perplexité WikiText-2 passe de 9,71 à 52,1 (8B), de 8,64 à 25,5 (14B), de 7,61 à 38,4
  (32B) [litt., tab. 4]. Avec un meilleur quantificateur, D²Quant (2602.02546) obtient
  14,10 sur Qwen3-8B et 9,71 sur Qwen3-32B à 2 bits [litt., résumé] : +45 % et +28 %.

---

## 4. Tableau de synthèse

Perte publiée : perplexité WikiText-2, FP16 → quantifié, contexte indiqué quand l'article
le donne. « Noyau » : le décodage se fait-il en registres pendant le produit, sans
écrire de matrice décompressée ? Toutes les pertes sont [litt.] sauf mention.

| Technique | bits/poids réels | Perte publiée (exemples) | Coût de quantification | Noyau | Vulkan | Maturité | Licence |
|---|---|---|---|---|---|---|---|
| K-quants llama.cpp (Q2_K…Q6_K) | 2,625 – 6,5625 [calc.] + mélanges | Q2_K : +3,52 PPL sur Llama 3 8B (aide de `llama-quantize`) | minutes, processeur | oui | **oui** | production | MIT |
| i-quants llama.cpp (IQ1_S…IQ4_XS) + imatrix | 1,5625 – 4,25 [calc.] + mélanges | IQ2_XXS ctx 4096 : 7B 5,12→7,07 ; 70B 3,12→4,08 | minutes à heures, processeur | oui | **oui** | production | MIT |
| TQ1_0 / TQ2_0, Q1_0 / Q2_0 | 1,6875 / 2,0625 ; 1,125 / 2,25 [calc.] | pour modèles natifs ternaires ou binaires seulement | — | oui | **oui** | production | MIT |
| EfficientQAT (w2g64) | ≈ 2,25 + échelles | ctx 2048 : L2-7B 5,47→6,86 ; L2-70B 3,32→4,52 ; L3-70B 2,85→6,08 | 41 h d'A100 pour 70B | via noyaux GPTQ/BitBLAS | non | recherche, modèles publiés | MIT |
| HIGGS (+ FLUTE) | 2 – 4,25, sans données | L3.1-8B : 5,607→6,388 à 3,25 bits | minutes, sans données | oui (FLUTE) | non | recherche + intégration Transformers | Apache-2.0 (FLUTE) |
| QuIP# (E8P) | 2, 3, 4 | ctx 4096 : 70B 3,12→3,91 à 2 bits | heures de carte + ajustement fin | oui | non | recherche | GPL-3.0 |
| AQLM (1x16, 2x8) | ≈ 2,0 – 2,3 | 70B 1x16 : 3,83 ; 7B : 5,92 | jours de carte (70B) | oui, lent en 1x16 | non | Transformers, vLLM | Apache-2.0 |
| PV-tuning (sur AQLM/QuIP#) | 1,0 – 2,3 | 2,02 b : L2-7B 5,12→5,84 ; 2,07 b : L3-70B 2,59→4,57 | ≈ 384 h de carte (passage le plus long) | comme AQLM | non | recherche, modèles publiés | Apache-2.0 (AQLM) |
| GPTVQ | 2 – 3 | — | 3 à 11 h H100 pour 70B | oui | non | recherche | — |
| VPTQ | 1,375 – 4 | L2-70B 2,07 b : 3,93 ; 39,9 jetons/s (7B) | 2 h (7B) à 19 h (70B) | oui, accès indirects | non | modèles publiés | MIT |
| QTIP (treillis) | 2, 3, 4 exacts | ctx 4096 : 2 b 7B 5,86, 70B 3,70 ; 3 b 7B 5,28 ; 4 b 7B 5,17 | heures de carte + ajustement fin | oui (188 jetons/s, 7B, 2 b) | non | recherche | GPL-3.0 |
| CurveTQ (treillis sans rotation, 2026-10) | 2,29 / 3,29, tout compris | ctx 4096 sans ajustement : Qwen3-4B 9,72→11,50 ; Qwen3-32B 6,17→6,90 ; 35B-A3B 6,12→6,76 | LDLQ + Viterbi pondéré, heures de carte (non chiffré) | oui, sans Hadamard (160,8 jetons/s Qwen3-4B, RTX 3090) | non (CUDA) | recherche, code non trouvé | — |
| XOR-Trellis (2026-09) | ≈ 2 | ctx 4096 : L3.1-8B 5,84→8,00 (QTIP 8,48) | comme QTIP | oui, ≈ 14 XOR2 par valeur, palette FP4 | non publié ; le plus portable des décodeurs | recherche | — |
| Tetra (Leech, 2026-09) | 2,148 lus/poids ; 2,70–2,73 modèle entier | MMLU Qwen3 4B/8B/14B : 63,4 / 69,6 / 75,7 (FP16 70,1 / 75,1 / 78,9) | échelles de ligne : 1,7 h L40S (4B) | oui, 6 lectures de table par bloc de 24 | non (CUDA) | recherche, préenregistrée | Apache-2.0 |
| GSQ (scalaire Gumbel-Softmax, 2026) | 2,13 / 3,13 (g128) | 0-shot L3.1-8B-Instr. 2 b : 68,55 (QTIP 69,88) ; projetable en Q2_K/Q3_K_M | blocs × 20 époques, 4096 × 4096 jetons d'étalonnage | oui (noyaux scalaires existants) | **oui si projeté en K-quants** | recherche | Apache-2.0 |
| ApexQuant (code emboîté, 2026-10) | P passes × b, chaque préfixe valide | « meilleur bras 2 bits » sans données (leur mesure) | sans données | une passe par préfixe lu | non publié | recherche | non déclarée |
| EXL3 (QTIP simplifié) | 1 – 8 entiers, fractionnaire par mélange | courbes du dépôt (pas de tableau) | minutes à heures, une carte grand public | oui | **non (CUDA, ROCm)** | production (TabbyAPI) | MIT |
| IQn_KT (ik_llama.cpp) | 1,75 / 2,125 / 3,125 / 4,0 + échelle de ligne [calc.] | — (MSE ≈ VQ 8 aléatoire [mes.]) | processeur AVX2 | oui | **non** | fourche active | MIT |
| CCQ (Baidu) | 2,0 – 2,75 | ERNIE-4.5-300B en 89 Go, une carte | — | oui, sans table | non | code publié avec ERNIE | — |
| BitNet b1.58 (natif) | 1,58 (ternaire) | « au niveau » des modèles pleins de taille voisine (2B4T) | pré-entraînement complet | oui (CPU, CUDA W2A8) | via TQ1_0/TQ2_0 de llama.cpp | modèles 2B publiés | MIT |
| ParetoQ (QAT) | 1 – 4 | L3-8B : 6,15→8,0 (2 b), 8,6 (ternaire) | ≈ 30 milliards de jetons d'ajustement | dépend du format | — | recherche, modèles publiés | — |
| MXFP4 / NVFP4 | 4,25 / 4,5 [calc.] | NVFP4 natif : « comparable à FP8 » (12B, 10T jetons) | natif à l'entraînement | oui | **oui (stockage)** ; FP4 matériel : Blackwell seulement | production | — |
| SpinQuant / QuaRot (rotations) | — (brique) | W4A4KV4 : écart de 2,9 points (L2-7B, SpinQuant) | heures (rotation apprise) | Hadamard en ligne | FWHT par blocs dans llama.cpp (`prism.hadamard`) | recherche ; la FWHT en production | CC BY-NC 4.0 / Apache-2.0 |
| YAQA (arrondi) | — (brique) | ≈ 30 % d'erreur en moins que GPTQ/LDLQ | Hessien de Kronecker, coûteux | — | — | recherche (ICML 2026) | — |

---

## 5. Mesuré ici : l'échelle llama.cpp sur Qwen3.5 4B et 9B

**Protocole** (`outils/quant-echelle.sh`, résumé par `outils/quant-resume-echelle.py`,
journaux `fondations/journaux/02-quantification/echelle-4B/` et `echelle-9B/`).
llama.cpp b11515 (CUDA 12.4). Base : les Q4_K_M de la machine (biais déclaré au § 8).
imatrix sur 128 morceaux de 512 jetons de wikitext-2 « train » ; quantification
`--allow-requantize --imatrix` vers chaque type (mélange par défaut de llama.cpp pour ce
type : certaines matrices restent plus haut) ; bits réels lus dans le fichier par
`outils/quant-gguf-bits.py` (témoin : la fin du dernier tenseur tombe sur la fin du
fichier) ; perplexité et divergence KL contre les logits de la base sur 40 morceaux de 512
jetons de wikitext-2 « test ». « Go lus/jeton » : tous les tenseurs, sauf la table
d'enchâssement dont une ligne seulement est lue, **sauf si la sortie lui est liée** (cas
du 4B : la table de 248 320 × 2 560 est alors relue en entier à chaque jeton).

### 5.1 Qwen3.5-4B (base Q4_K_M : 5,19 bits/poids, 2,73 Go lus par jeton, PPL 8,723 ± 0,229)

Sortie de `quant-resume-echelle.py` (journaux `echelle-4B/`), virgules décimales ;
± = erreur-type donnée par llama-perplexity sur les 40 morceaux.

| type | bits/poids (tenseurs) | Go lus/jeton | PPL | PPL / base | KLD moyenne | même 1er jeton (%) | quantif. (s) |
|---|---|---|---|---|---|---|---|
| Q4_K_M (base, fichier d'origine) | 5,193 | 2,730 | 8,723 ± 0,229 | 1 | 0 | 100 | — |
| IQ4_XS | 4,762 | 2,503 | 8,908 ± 0,236 | 1,0218 ± 0,0029 | 0,0295 ± 0,0012 | 91,86 ± 0,27 | 1 146,5 |
| IQ3_XXS | 3,602 | 1,894 | 9,777 ± 0,259 | 1,1215 ± 0,0070 | 0,1477 ± 0,0028 | 82,12 ± 0,38 | non relevé |
| Q2_K | 3,623 | 1,905 | 10,957 ± 0,300 | 1,2568 ± 0,0109 | 0,2543 ± 0,0045 | 77,44 ± 0,41 | 121,8 |
| IQ2_M | 3,292 | 1,731 | 10,956 ± 0,293 | 1,2568 ± 0,0107 | 0,2691 ± 0,0046 | 76,40 ± 0,42 | 387,8 |
| IQ2_XXS | 2,905 | 1,527 | 15,493 ± 0,437 | 1,7772 ± 0,0235 | 0,6080 ± 0,0079 | 65,80 ± 0,47 | 1 072,4 |
| IQ1_S | 2,565 | 1,348 | 48,027 ± 1,467 | 5,5091 ± 0,1207 | 1,7795 ± 0,0152 | 44,73 ± 0,49 | 188,9 |

Les trois dernières lignes (Q2_K, IQ2_M, IQ1_S) viennent de la suite lancée par le
prédécesseur et finie pendant la reprise (08:21-08:33), machine moins chargée : **leurs
temps de quantification sont 3 à 9× plus courts** (Q2_K 122 s, IQ2_M 388 s, contre
1 072 à 1 147 s pour les types quantifiés machine chargée), ce qui confirme que les temps
de la nuit sont des majorants (§ 8).

- **À octets égaux, l'i-quant bat la K-quant de 11 % de perplexité** : IQ3_XXS 9,777 contre
  Q2_K 10,957 pour 1,89-1,91 Go lus par jeton [mes.] (le « Q2_K » de llama.cpp est en fait
  à 3,6 bits/poids : ses matrices sensibles montent en Q3_K-Q4_K).
- **IQ1_S est inutilisable sur un 4B ordinaire** : perplexité ×5,5, premier jeton commun dans
  45 % des cas. Le 1,56 bit ne vaut que pour des modèles entraînés pour (§ 3.6).

(La durée de l'IQ3_XXS manque : le prédécesseur l'a lancée hors du script qui la note ;
journal `echelle-suite2.out`, sans horodatage.)

[mes.] Lecture :
- **IQ4_XS** : perte négligeable (+2,2 % de perplexité, KLD 0,03) pour 8 % d'octets de
  moins que la base.
- **IQ3_XXS** : +12 % de perplexité, KLD 0,15, le premier jeton est le même que la base
  dans 82 % des cas, pour 31 % d'octets de moins.
- **IQ2_XXS** : +78 % de perplexité, KLD 0,61, même premier jeton dans 66 % des cas.
  **Pour un 4B très entraîné, 2 bits ne sont pas acceptables**, conformément à
  l'étude Qwen3 (§ 3.9).
- **Le fichier « IQ2_XXS » n'est pas à 2 bits** : 2,905 bits/poids lus par jeton. La
  table d'enchâssement liée à la sortie (636 M poids, 15 % du modèle) reste en Q5_K et
  pèse 437 Mo, **29 % des octets lus par jeton** ; 32 matrices restent en Q4_K (524 M
  poids, 295 Mo). Pour un petit modèle à grand vocabulaire, la tête de sortie est le
  premier poste d'octets dès qu'on descend sous 3 bits : la quantifier plus bas, ou ne
  lire que les lignes utiles (échantillonnage restreint, étude 05), vaut autant que
  gagner un demi-bit sur tout le reste.
- Temps de quantification : 1 038 s d'imatrix, 1 073 à 1 147 s par type, machine
  partagée (majorants).
- Vitesse de décodage sous llama-bench : **inexploitable**, la référence elle-même
  variait de 30 à 59 jetons/s entre deux passes (carte partagée). Journal gardé
  (`vitesse-4B-1.json`) ; la meilleure passe Q4_K_M donne 59 jetons/s × 2,73 Go =
  161 Go/s, 63 % du plafond.
- Passe 2 (reprise, 07:36, carte libre au lancement, seuil déclaré avant : une paire ABBA
  n'est retenue que si le bruit de la référence est < 5 %) : **rejetée** (bruit 23 %, 7 %
  et 8 %). Elle montre pourtant un fait net [mes.] : **sous charge du processeur** (une
  quantification llama.cpp et le banc rANS de l'étude 03 tournaient), tous les formats
  décodent à la même vitesse, 24 à 31 jetons/s, que le fichier lise 1,53 Go (IQ2_XXS) ou
  2,73 Go (Q4_K_M) par jeton, carte à 11 % d'occupation : le décodage est alors limité par
  le fil qui lance les noyaux, pas par les octets. Une passe 9B lancée ensuite a été
  arrêtée (elle se serait partagé la carte avec la perplexité de l'IQ2_M). Journaux
  `vitesse-4B-2.json` et `.log`. L'étude 01 relève aussi que `-lm mmap` divise par deux
  le débit du 9B (16,5 contre 34,1 jetons/s sans mmap, `01-machine/llama-base.jsonl`) :
  une passe propre doit se faire machine calme et sans mmap.
- **Passe 3 (09:0x, machine calme, `-lm none --prio 2`, 128 jetons × 5, ABBA) : retenue**,
  bruit de la référence 0,1 à 2,8 % (seuil 5 %), carte en P0 à 2 670 MHz avant et après
  (`vitesse-4B-3.json`, `vitesse-9B-3.json`, `vitesse-3-carte-*.txt`). CUDA (llama.cpp
  b11515), tout en VRAM [mes.] :

| Modèle, type | Go lus/jeton | jetons/s | Go/s effectifs | part de 256 Go/s | PPL |
|---|---|---|---|---|---|
| 4B Q4_K_M | 2,730 | 69,3 | 189 | 74 % | 8,72 |
| 4B IQ4_XS | 2,503 | 73,9 | 185 | 72 % | 8,91 |
| 4B IQ3_XXS | 1,894 | 87,1 | 165 | 64 % | 9,78 |
| 4B IQ2_M | 1,731 | 87,7 | 152 | 59 % | 10,96 |
| 4B IQ2_XXS | 1,527 | 92,8 | 142 | 55 % | 15,49 |
| 9B Q4_K_M | 5,097 | 42,0 | 214 | 84 % | 7,17 |
| 9B IQ3_XXS | 3,490 | 56,8 | 198 | 77 % | 7,91 |
| 9B IQ2_M | 3,159 | 56,1 | 177 | 69 % | 8,61 |
| 9B IQ2_XXS | 2,757 | 62,7 | 173 | 68 % | 10,60 |

  Lecture [mes., calc.] :
  - **En VRAM, les octets en moins ne se transforment qu'à moitié en vitesse.** Du Q4_K_M
    à l'IQ2_XXS, les octets lus sont divisés par 1,79 (4B) et 1,85 (9B), la vitesse
    multipliée par 1,34 et 1,49 seulement : la part du plafond tombe de 74-84 % à
    55-68 %. Le décodage des i-quants (grilles en mémoire partagée) et le coût fixe par
    jeton (≈ 400 noyaux, couches récurrentes de Qwen3.5) prennent le reste. C'est la règle
    de placement du § 2.3 vue sur le modèle entier : en VRAM, le bit en moins se paie en
    calcul.
  - **Hors VRAM, le rapport s'inverse** : au débit du PCIe (≈ 7 Go/s), le décodage des
    i-quants (≥ 142 Go/s effectifs mesurés ici) va 20× plus vite que le lien, et seuls
    les octets comptent (D1).
  - **À qualité voisine, en VRAM, le 9B en 3 bits coûte 18 % de vitesse** : 9B IQ3_XXS
    56,8 jetons/s pour 7,91 de perplexité, contre 4B Q4_K_M 69,3 jetons/s pour 8,72.

### 5.2 Qwen3.5-9B (base Q4_K_M : 5,08 bits/poids, 5,10 Go lus par jeton)

PPL de la base sur les mêmes 40 morceaux : 7,174 ± 0,178 (journal `qwen35-9B-base-ppl.log`).

| type | bits/poids (tenseurs) | Go lus/jeton | PPL | PPL / base | KLD moyenne | même 1er jeton (%) | quantif. (s) |
|---|---|---|---|---|---|---|---|
| Q4_K_M (base, fichier d'origine) | 5,066 | 5,097 | 7,174 ± 0,178 | 1 | 0 | 100 | — |
| IQ3_XXS | 3,509 | 3,490 | 7,913 ± 0,198 | 1,1037 ± 0,0060 | 0,1130 ± 0,0027 | 85,01 ± 0,35 | 1 794,6 |
| IQ2_M | 3,213 | 3,159 | 8,612 ± 0,217 | 1,2011 ± 0,0086 | 0,2058 ± 0,0041 | 80,21 ± 0,40 | non valable (veille de la machine pendant le calcul : 14 657 s au mur) |
| IQ2_XXS | 2,761 | 2,757 | 10,605 ± 0,271 | 1,4791 ± 0,0155 | 0,4251 ± 0,0061 | 72,25 ± 0,44 | 1 730,6 |

Les « 2 bits » de llama.cpp ne le sont pas : IQ2_M lit 3,16 Go (3,21 bits/poids : 204
matrices en IQ2_S à 2,5625, 13 en IQ3_S, 32 en Q4_K, la sortie en Q5_K), IQ3_XXS 3,49 Go.

**La comparaison à octets égaux** (le critère du § 6.2) [mes.] :

| Configuration | Go lus/jeton | PPL (40 × 512, wikitext-2 test) |
|---|---|---|
| Qwen3.5-4B Q4_K_M (fichier d'origine) | 2,730 | **8,723 ± 0,229** |
| Qwen3.5-9B IQ2_XXS (requantifié, imatrix) | 2,757 | 10,605 ± 0,271 |

- **Le 4B en 4 bits bat le 9B en 2 bits de 22 % de perplexité, à 1 % d'octets près.** Les
  deux intervalles (± 2 erreurs-types) ne se recouvrent pas. Avec le meilleur 2 bits
  portable d'aujourd'hui, rapetisser vaut mieux que comprimer pour Qwen3.5.
- **Le croisement a lieu vers 3,2 bits/poids, pas à 2** [mes.] : le 9B en IQ2_M (3,16 Go,
  8,612 ± 0,217) égale le 4B en Q4_K_M (2,73 Go, 8,723 ± 0,229) pour 16 % d'octets de plus,
  intervalles confondus ; le 9B en IQ3_XXS (3,49 Go, 7,913 ± 0,198) le bat de 9 % pour
  28 % d'octets de plus, et atteint une perplexité qu'aucune version du 4B ne semble
  pouvoir atteindre : l'IQ4_XS ne perd que 2,2 % sur le Q4_K_M, et si le Q4_K_M perd
  autant sur le BF16, le 4B d'origine est vers 8,5 [calc., estimation non mesurée : pas de
  BF16 sur la machine]. **Au-delà d'environ 3,2 Go
  lus par jeton, le 9B comprimé domine tout le front du 4B ; en dessous, le 4B gagne.** La
  figure Q3 (`memoire/figures/02-quantification-figures.tex`) trace les deux fronts.
- Correction du biais de la base requantifiée (§ 8, ≈ 10 % de la perte) : la perte du 9B
  passerait de +47,9 % à ≈ +43 %, soit une perplexité ≈ 10,3 ; le classement ne change pas.
- La perte relative baisse avec la taille (4B : +77,7 % ; 9B : +47,9 % en IQ2_XXS),
  conformément à la loi d'échelle (§ 3.9) ; mais à ce rythme (≈ −40 % de perte relative par
  doublement), il faudrait encore plusieurs doublements pour que la perte du « 2 bits »
  tombe sous l'écart de qualité entre deux tailles voisines (9B contre 4B : −18 % de
  perplexité ici). Extrapolation par une loi de puissance à deux points
  (`02-quantification-derivations.md`, D8 ; fragile) [calc.] : perte relative
  `ℓ(N) = 0,479 (N/8,95)^(−0,640)` ; elle tombe sous 22 % vers **30 milliards** de
  paramètres, sous 10 % vers 100 milliards. Avec IQ2_XXS, le seuil des 2 bits sur Qwen3.5
  est donc au-delà de 30B, contre 8B pour Qwen3 avec un code de deuxième génération
  (§ 6.1) : le codeur déplace le seuil d'un facteur 4 à 10.
- Comme au 4B, le « IQ2_XXS » n'est pas à 2 bits : 2,76 bits/poids lus. La sortie
  (non liée au 9B) reste en Q5_K et pèse 699 Mo, **25 % des octets lus par jeton** ;
  32 matrices en Q4_K (472 Mo), 4 en Q2_K (66 Mo) ; les matrices vraiment en IQ2_XXS ne
  font que 1 516 Mo sur 2 757. (La table d'enchâssement, en Q2_K, pèse 334 Mo mais une
  seule ligne en est lue par jeton : elle est hors du compte.)

---

## 6. La réponse à la question clé

### 6.1 Le meilleur rapport octets lus par jeton / qualité aujourd'hui

On compare à **octets lus égaux**, car c'est ce que paie chaque jeton. Le seul ensemble
publié où toutes les méthodes et toutes les tailles sortent du même programme est le
tableau de QTIP (Llama 2, WikiText-2, contexte 4096) [litt.] ; j'en tire [calc.] les
octets lus par jeton (N × b / 8, sans la tête) :

| Configuration | Go lus/jeton | PPL | écart au FP16 du même modèle |
|---|---|---|---|
| 7B FP16 | 13,5 | 5,12 | — |
| 7B QTIP 4 bits | 3,4 | 5,17 | +1,0 % |
| **13B QTIP 2 bits** | **3,3** | **5,11** | +11,8 % |
| 7B QTIP 2 bits | 1,7 | 5,86 | +14,5 % |
| 13B QTIP 4 bits | 6,5 | 4,61 | +0,9 % |
| 13B QTIP 3 bits | 4,9 | 4,69 | +2,6 % |
| **70B QTIP 2 bits** | **17,3** | **3,70** | +18,6 % |
| 70B QTIP 3 bits | 26,0 | 3,26 | +4,5 % |
| 13B FP16 | 26,0 | 4,57 | — |

Ce que disent ces nombres :
- **À octets égaux, un modèle deux fois plus grand en treillis 2 bits égale ou bat le
  modèle deux fois plus petit en 4 bits** (13B-2 bits : 5,11 à 3,3 Go contre 7B-4 bits :
  5,17 à 3,4 Go). Et un 70B en 2 bits (17 Go) bat largement un 13B en FP16 (26 Go).
- **Avec une quantification scalaire, c'est l'inverse** : EfficientQAT (même article,
  contexte 2048) donne 13B w2g64 5,96 à 4,0 Go contre 7B w4g128 5,53 à 3,7 Go. Le
  croisement dépend donc de la méthode autant que de la taille.
- **Sur une famille très entraînée (Qwen3), avec les codes de septembre 2026, le
  croisement a lieu dès 8B** [litt. Tetra tab. 3, calc.] : Qwen3-8B Tetra (2,76 Go de
  poids sur la carte, modèle entier) 69,58 au MMLU contre Qwen3-4B AWQ 4 bits (2,67 Go)
  68,14 ; Qwen3-14B Tetra (5,04 Go) 75,66 contre Qwen3-8B AWQ (6,10 Go) 73,79, avec 17 %
  d'octets en moins. Réserve écrite par les auteurs : cette comparaison a été choisie après
  la mesure. Et en perplexité, CurveTQ sans ajustement fin donne Qwen3-32B +12 % à 2,29
  bits ; Qwen3-4B +18 %.
- **Avec les i-quants de llama.cpp, le croisement n'a pas lieu** : mesuré ici, Qwen3.5-9B
  en IQ2_XXS (2,76 Go lus par jeton) a une perplexité de 10,61 contre 8,72 pour Qwen3.5-4B
  en Q4_K_M (2,73 Go) (§ 5.2) ; et Tetra mesure IQ2_XXS de Qwen3-4B 23,6 points de MMLU
  sous son propre fichier à 2,7 bits.
- **Le meilleur rapport aujourd'hui est le treillis à 2–3 bits** (QTIP / EXL3, et depuis
  octobre 2026 CurveTQ, Tetra) :
  3 bits coûtent 2 à 5 % de perplexité, 2 bits 12 à 19 % sur Llama 2. Avec les i-quants
  de llama.cpp (les seuls portables), 2 bits coûtent 25 à 38 % sur les mêmes modèles
  (§ 3.3), et 3 bits ≈ 12 % sur Qwen3.5-4B [mes.].

### 6.2 À partir de quelle taille les 2 bits deviennent acceptables

Définition retenue (réponse par délégation du 2026-10-15, réversible : « acceptable » =
le modèle quantifié à 2 bits est au moins aussi bon qu'un modèle de la même famille, deux
fois plus petit, en 4 bits, à octets lus égaux ; c'est le seul critère qui dit s'il vaut
mieux comprimer ou rapetisser).

- **Llama 2, treillis + ajustement fin** : dès 13B (13B-2 bits ≈ 7B-4 bits) [litt.].
- **Llama 2, scalaire** : pas atteint jusqu'à 70B dans EfficientQAT.
- **Familles très entraînées** (Llama 3, Qwen3, Qwen3.5) : nettement plus tard. Llama 3
  70B perd 76 % de perplexité à 2,07 bits même avec PV-tuning ; Qwen3-32B passe de 7,61 à
  9,71 (+28 %) avec le meilleur PTQ publié (D²Quant). Mesuré ici : Qwen3.5-4B en IQ2_XXS
  +78 % (§ 5.1). Le § 5.2 compare Qwen3.5-9B à 2–3 bits avec Qwen3.5-4B à 4 bits, à
  octets égaux.
- **La loi derrière** : la dégradation croît avec le nombre de jetons d'entraînement par
  paramètre (2411.17691). Le seuil se déplace donc vers le haut à chaque génération ;
  ~~pour les familles de 2025-2026, la littérature et mes mesures placent le seuil
  au-delà de 30B pour la PTQ, et l'entraînement à la quantification (ParetoQ, Bonsai,
  BitNet) reste la seule voie démontrée pour 2 bits sur de petits modèles.~~
  Corrigé à la reprise du 2026-10-15 après lecture des articles de septembre-octobre
  2026 (§ 3.8) : **le seuil dépend du codeur plus que de la taille.**
  - Avec un code de deuxième génération (réseau de Leech ou treillis, échelles de ligne
    réentraînées, enchâssements en 4 bits, ≈ 2,7 bits par paramètre sur tout le modèle),
    Qwen3 franchit le critère **dès 8B** au MMLU (Tetra, § 6.1) [litt., calc.].
  - Avec IQ2_XXS de llama.cpp (le meilleur 2 bits décodable en Vulkan aujourd'hui), le
    critère n'est franchi ni à 4B ni à 9B sur Qwen3.5 [mes., § 5.2] ; extrapolé par la
    loi d'échelle, pas avant plusieurs dizaines de milliards de paramètres actifs. Le 9B
    ne rattrape le 4B en Q4_K_M qu'à ≈ 3,2 bits/poids lus (IQ2_M, à 16 % d'octets de
    plus) et le domine à 3,5 (IQ3_XXS) [mes.] : **avec llama.cpp, à 9B, le bon débit est
    3 à 3,5 bits, pas 2.**
  - **Donc la réponse pour troncons** : 2 bits deviennent acceptables vers 8B **si et
    seulement si** on dispose d'un code de deuxième génération décodable sur la carte ;
    sous Vulkan, ce code n'existe pas encore (§ 7, trou 1), d'où la priorité.

---

## 7. Ce que je crois manquer dans le monde

1. **Aucun décodeur de treillis (classe QTIP / EXL3) en Vulkan ou DirectX 12.** QTIP et
   EXL3 exigent CUDA (ou ROCm) ; les IQn_KT d'ik_llama.cpp ont CUDA, Metal et CPU ; la PR
   qui portait les types d'ik dans llama.cpp a été fermée sans fusion (2026-02-23) et ne
   contenait pas les KT ; le seul brouillon Vulkan signalé (strix-llama.cpp #148) répond
   404. **Enjeu chiffré** : à 2 bits sur source gaussienne, treillis 0,068 contre 0,093
   pour une VQ de dimension 8 et 0,107 pour IQ2_XXS [mes., § 2], soit 27 à 36 % de MSE
   en moins. Converti en bits à qualité égale (D ∝ 2^(−2R)) : **0,23 à 0,33 bit/poids**
   [calc.], soit 260 à 370 Mo de moins par jeton pour un 9B, +12 à +19 % de jetons/s
   quand les poids passent par le PCIe. **Mais en perplexité, sans ajustement fin, le gain
   publié est plus petit** : Llama 2 7B à 2 bits, QTIP 3INST sans ajustement 6,82, IQ2_XXS
   7,07 (FP16 5,12) [litt.] : 13 % de perte en moins seulement. L'essentiel de l'avance de
   QTIP (5,86) vient de l'ajustement fin, qui demande des heures de carte. Un treillis
   Vulkan sans ajustement fin vaut donc ≈ 0,1 à 0,3 bit ; avec ajustement, bien plus.
   Coût du décodage mesuré : 156 Go/s équivalents en CUDA (§ 2.2), **124 Go/s en
   Vulkan avec `dot4U8Packed` dans mon propre shader** (§ 2.3), soit 18× le débit du
   PCIe, et la vitesse du scalaire 4 bits en VRAM. Le trou est réel, chiffré, et le premier pas pour le combler est fait ici.
   La rotation, elle, existe déjà en Vulkan dans llama.cpp (FWHT par blocs de
   `prism.hadamard`, § 3.1) : il ne manque que le codeur en treillis et son décodeur.
   **Mise à jour d'octobre 2026** (§ 3.8) : CurveTQ montre qu'un treillis sans rotation,
   avec la courbure dans la métrique du Viterbi et un état initial stocké par bloc, fait
   mieux que QTIP (Qwen3-4B 2 bits : 11,50 contre 15,36) ; XOR-Trellis montre un décodeur
   à ≈ 14 portes XOR2 par valeur. Le décodeur Vulkan à écrire est donc **plus simple** que
   celui du § 2.3 : pas de FWHT des activations, un état initial lu par bloc (ce qui
   supprime aussi la lecture circulaire), ~~et un code calculé par XOR plutôt que par
   multiplication~~. Corrigé par la mesure du § 2.4 : un code par parités, écrit et mesuré
   ici, garde la MSE (0,031 bit derrière mul1) mais se décode 2,3× plus lentement sur la
   RTX 4060 (le comptage de bits y est plus cher que la multiplication entière) ; **le code
   à porter est mul1 ou 3INST, avec `dot4U8Packed`**. Personne ne l'a encore porté hors de
   CUDA.
2. **Le « treillis » d'ik_llama.cpp n'en est pas un.** Lu dans son code : graines de
   16 bits indépendantes par groupe de 8 poids, plus proche voisin par grappes. Mesuré :
   même MSE qu'une VQ de dimension 8 à livre aléatoire (0,0928 contre 0,0935). Un vrai
   treillis à décalage, au même débit, ferait 27 % de MSE en moins.
3. **Personne n'alloue les bits selon le coût du transfert.** HIGGS dynamique, les
   recettes d'EXL3, `--tensor-type` de llama.cpp minimisent l'erreur sous un budget de
   **stockage**. Or, dans troncons, un octet lu en VRAM coûte 1/256 Go/s et un octet
   amené par le PCIe 1/7 Go/s : 36× plus cher. Dérivation [calc.] : minimiser
   `Σ c_i · 2^(−2 b_i)` (erreur, théorème de linéarité) sous `Σ n_i · b_i / W_i ≤ T`
   (temps par jeton, `n_i` poids de la matrice `i`, `W_i` débit de son étage) donne, par
   le lagrangien, `b_i = ½ log₂(2 ln 2 · c_i · W_i / (λ · n_i))`. À sensibilité égale,
   **une matrice résidente en VRAM reçoit ½ log₂(256/7) ≈ 2,6 bits de plus qu'une
   matrice lue par le PCIe** : résidents en 4 à 5 bits, flux en 1,5 à 2,5 bits. Aucun
   outil publié ne fait ce partage ; c'est une contribution directe pour troncons.
   Nuance (lecture de Q-Palette, 2509.20214, à la reprise) : leur sac à dos à choix
   multiples accepte un coût de **latence profilée** par couche au lieu d'un budget de
   mémoire ; mais le coût y est celui du noyau sur une carte où tout réside, sans variable
   de placement. La forme exacte du trou : une allocation conjointe (bits, étage) où le
   coût d'une matrice dépend de l'étage qui la sert.
4. **Il ne reste presque rien à gagner en compressant sans perte après une bonne
   quantification.** Un code proche de la borne de Shannon émet des bits presque
   uniformes ; l'étude 03 mesure, sur les Q4_K de Qwen3.5-4B, une entropie conditionnelle
   de 4,26 bits pour 4,5 stockés (≈ 5 % de marge, provisoire). Le levier de compression
   est la quantification ; la compression sans perte se joue sur les échelles et les
   métadonnées, pas sur les codes.
5. **Pas de frontière iso-octets publiée pour les familles très entraînées sous 3 bits
   avec des noyaux portables.** Les comparaisons publiées portent surtout sur Llama 2,
   qui se quantifie mieux que Llama 3, Qwen3 ou Qwen3.5 (§ 3.9). Le § 5 en donne un
   premier point pour Qwen3.5 sous llama.cpp.
6. **Quantifier un grand modèle sur la machine de Stone.** QTIP et PV-tuning demandent
   des jours de cartes A100 ; EXL3 tient sur une carte grand public mais exige PyTorch
   CUDA (téléchargement > 500 Mo) ; llama.cpp quantifie sur le processeur (IQ4_XS d'un
   4B : 1 146 s mesurées, machine chargée). Un quantificateur en treillis qui travaille
   matrice par matrice depuis le disque, sur la carte, en Vulkan, n'existe pas.
7. **Aucun code emboîté n'est lié au placement.** ApexQuant (2610.07904) prouve qu'un
   code résiduel à rotations fraîches rend chaque préfixe valide, pour 0,10 bit de perte
   par passe en treillis (0,45 en scalaire) [litt.]. Dans troncons, cela donne un seul
   fichier pour les deux étages : une matrice lue par le PCIe ne lit que sa passe 1
   (≈ 2 bits), une matrice résidente en VRAM lit les passes 1 et 2 (≈ 4 bits) ; quand la
   fenêtre de résidence bouge, rien ne se requantifie. [calc.] Coût : environ 0,10 bit sur
   les résidents (chaque passe paie sa distance à la borne ; deux passes de 2 bits en paient
   une de plus qu'un treillis à 4 bits d'un coup : 4,10 bits pour la qualité d'un 4,00, soit 2,5 % d'octets en VRAM, où l'octet coûte 36× moins
   qu'à travers le PCIe) ; gain contre deux copies séparées (2 + 4 bits) : 1,9 bit/poids de
   disque, 32 % du stockage. C'est exactement la règle des 2,6 bits (trou 3) rendue
   dynamique : la profondeur lue par matrice se choisit à l'exécution selon l'étage. Aucun
   moteur publié ne lit des préfixes de précision selon l'étage de mémoire.
8. **Le meilleur 2 bits décodable en Vulkan est encore une K-quant mal remplie.** GSQ
   (2604.18556) améliore un Q2_K de Qwen3-8B de 50,03 à 56,28 de moyenne (AIME25, GPQA,
   MMLU-Pro) **sans changer de format** [litt.] : tout le gain se décode avec les shaders
   existants de llama.cpp. Mais GSQ exige PyTorch CUDA et des heures d'optimisation par
   blocs : pour la machine de Stone, un Q2_K « bien rempli » reste à produire (téléchargement
   de PyTorch CUDA à demander), et aucun i-quant n'a été optimisé ainsi.

---

## 8. Ce qui pourrait être faux

- **La carte et le processeur étaient partagés** avec trois à cinq autres agents pendant
  toutes les mesures (llama-perplexity, llama-bench, compilations). Les temps de
  quantification (imatrix 1 038 s, IQ4_XS 1 146 s pour un 4B) sont donc des majorants,
  peut-être de 3 à 5×. Les mesures de qualité (perplexité, KLD) n'en dépendent pas. Le
  banc GEMV a des passes de référence perturbées (jusqu'à 20 ms au lieu de 2,2) : je ne
  garde que les paires propres ; le chiffre du treillis est stable à ±0,3 %, celui du
  scalaire 2 bits l'est moins (deux séries perturbées sur trois).
- **Mes modèles de base sont des Q4_K_M, pas des BF16** (aucun BF16 de Qwen3.5 sur la
  machine, et un BF16 de 4B pèse ~8 Go : téléchargement à demander). La requantification
  ajoute l'erreur du Q4_K_M à celle du type visé. Estimation [calc.] : MSE relative d'un
  4,5 bits ≈ 0,01 contre ≈ 0,1 pour un 2 bits ; l'erreur totale à 2 bits est donc
  surestimée d'environ 10 %, ce qui rend mes résultats bas débit **pessimistes**
  d'environ 10 % en perte de perplexité. Et la divergence KL est mesurée contre le
  Q4_K_M, pas contre le modèle d'origine.
- **L'imatrix est calculée sur wikitext-2 « train » et la perplexité sur « test »** :
  même domaine, biais optimiste pour les types qui utilisent l'imatrix (i-quants surtout).
- **40 morceaux de 512 jetons** (20 480 jetons) pour la perplexité et la KLD : les
  erreurs-types sont données ; la perplexité absolue n'est pas comparable aux chiffres
  publiés en contexte 4096.
- **Les chiffres de la littérature viennent de programmes d'évaluation différents**
  (contexte 2048 ou 4096, jeux d'étalonnage, ajustement fin ou non) ; les comparaisons
  entre articles, notamment IQ2_XXS contre QTIP, portent ce biais. Seules les
  comparaisons à l'intérieur d'un même article ou de ma propre échelle sont propres.
- **La MSE sur gaussienne n'est pas la qualité du modèle.** Elle mesure le codeur sur la
  source qu'il vise après rotation. Les i-quants de llama.cpp ne font pas de rotation :
  leur source n'est pas gaussienne, et leur MSE réelle n'est pas celle de la VQ 8 du § 2.
  Le passage MSE → perplexité repose sur le théorème de linéarité de HIGGS, valable pour
  de petites erreurs ; à 2 bits l'erreur n'est plus petite.
- **Le treillis à état initial libre** (pas de tail-biting) a 14 bits d'amorce par suite ;
  je les compte (2,0034 bits/poids), mais sur des tuiles de 256 poids comme dans EXL3 le
  tail-biting coûte un peu de MSE que je n'ai pas mesurée (QTIP la donne petite, tab. 2).
- **Le banc GEMV est un noyau naïf.** Il ne prouve pas ce qu'un noyau optimisé ferait,
  ni ce que ferait Vulkan ; il borne le coût du décodage par le haut.
- **La « règle des 2,6 bits » (§ 7, trou 3)** suppose des erreurs indépendantes et additives
  entre matrices (théorème de linéarité) et une MSE en 2^(−2b), ce qui est faux aux très
  bas débits pour un quantificateur réel ; elle donne la direction et l'ordre de
  grandeur, pas la valeur.
- **Les articles de 2026 (D²Quant, HARP, Leech, SAGE)** n'ont été lus qu'au résumé ;
  le réseau de Leech est une prépublication non relue.
- **Le front d'octobre 2026 (§ 3.8) n'est pas reproduit.** CurveTQ, Tetra, XOR-Trellis,
  ApexQuant et Q-Palette ont été lus en PDF entier (tableaux relevés à la main) ; GSQ en
  partie (la page HTML a été lue jusqu'au caractère 100 000 sur 161 160 : son annexe de
  temps de calcul n'est pas lue) ; les autres au résumé. Tous ont moins de six semaines,
  aucun n'est relu par des pairs sauf Proteus (ICML 2026, cité de seconde main).
- **Le croisement « dès 8B » de Qwen3 repose sur le MMLU, pas sur la perplexité**, et
  les auteurs de Tetra écrivent que cette comparaison a été choisie après la mesure.
  CurveTQ montre au passage que perplexité et justesse en aval divergent à 2 bits (retirer
  sa pondération baisse la perplexité de 0,24 mais coûte 3,3 points en aval). Mon critère
  iso-octets en perplexité (§ 5.2) et le leur en MMLU ne mesurent pas la même chose.
- **L'extrapolation à 30B (§ 5.2, D8)** tient sur deux points (4B, 9B) et une loi de
  puissance supposée ; elle donne un ordre de grandeur, pas un seuil.
- **La proposition 3 de D6** (la fréquence d'usage décide du placement, la sensibilité
  décide des bits) suppose une perte proportionnelle à la fréquence d'usage ; pour un
  expert rare mais décisif, c'est faux.

---

## 9. Recettes (ce qui a marché, ce qui a échoué)

- **A marché** : reproduire un tableau publié par un programme écrit depuis la définition
  mathématique (treillis à décalage + Viterbi en numpy, 60 lignes) : QTIP tab. 1 retrouvé
  à l'erreur-type près. Raison : la MSE gaussienne ne dépend que du codeur.
- **A marché** : Viterbi vectorisé sur 2^16 états en remodelant le vecteur des coûts en
  (2^k, 2^(L−k)) et en prenant le minimum sur l'axe des bits sortants. Raison : les
  prédécesseurs d'un état d'un treillis à décalage sont exactement les 2^k valeurs du
  bit de poids fort.
- **A échoué puis corrigé** : témoin cassé trop faible (un niveau décalé de 0,05) : il ne
  tombait pas. Raison : le plus proche voisin réaffecte les échantillons et absorbe le
  décalage. Leçon : vérifier la sensibilité de l'instrument avant de choisir la cassure.
- **A échoué puis corrigé** : premier noyau GEMV 2 bits (une voie par tuile) : 14 Go/s
  quel que soit le format. Raison : lecture des activations dispersée (pas de
  coalescence). Correction : toute la chaîne sur une tuile, 8 poids par voie, activations
  lues en 16 octets contigus : 211 Go/s.
- **A échoué** : Monte-Carlo du treillis à 24 suites sur un processeur partagé :
  1 440 s par combinaison ; ramené à 8 suites (erreur-type 1 %).
- **A marché** : lire le code plutôt que la documentation pour classer une méthode : le
  « treillis » d'ik_llama.cpp est une VQ à graines indépendantes, ce que le nom cache.
- **A marché** : CUDA 13.1.2 dépaqueté (étude voisine) + `vcvars64.bat` + `nvcc
  -arch=sm_89` : un banc de noyau compilé et exécuté en quelques minutes, sans
  installation.
- **A marché (reprise)** : veille par l'API `https://export.arxiv.org/api/query` triée par
  date de dépôt (l'adresse en `http` répond 301 : il faut `https`), puis lecture des PDF
  par `pdftotext -layout` (Git pour Windows l'a) et `grep` sur les tableaux. Raison : les
  pages HTML d'arXiv manquent pour certains articles (404 sur CurveTQ) et un résumé
  automatique tronque les tableaux.
- **A marché** : un témoin de MSE qui retrouve **exactement** (0,068236) la valeur d'une
  passe antérieure, en consommant le générateur aléatoire dans le même ordre : la
  comparaison entre codes se fait alors sur les mêmes suites, sans bruit de tirage.
- **A échoué (mesure)** : llama-bench pendant qu'une quantification et un banc processeur
  tournent : tous les formats à la même vitesse (≈ 28 jetons/s), carte à 11 %. Raison : le
  fil qui lance les noyaux est privé de processeur. Leçon : mesurer la vitesse de décodage
  machine calme, et lire l'occupation de la carte pendant la mesure.
- **A échoué (mesure)** : une passe Vulkan dont toutes les valeurs sont 10× trop lentes,
  carte en P8 à 375 MHz juste avant (journal `vulkan-gemv-5-perturbee.json`) ; refaite
  aussitôt, elle redonne la passe 4 à 5 % près. Leçon : relever l'état d'horloge de la
  carte avec chaque passe.
- **A échoué (outil)** : `biber` se bloque sur la machine, même pour `--version` (plus de
  300 s) ; les figures se compilent sans lui (`lualatex` seul). À signaler au rédacteur.
- **A échoué (sed en Git Bash)** : remplacements multi-lignes par `sed` ou par heredoc
  Python contenant des apostrophes : motifs non trouvés ou heredoc cassé. Correction : un
  script de correctif écrit dans un fichier, qui vérifie la présence de chaque motif.

---

## 10. Sources

Toutes consultées le 2026-10-15. Dates arXiv relevées par l'API `export.arxiv.org`
(journal `sources-arxiv.tsv`) : première version / dernière version.

**Articles**
- QuIP# — https://arxiv.org/abs/2402.04396 — 2024-02-06 / 2024-06-04 (ICML 2024).
- AQLM — https://arxiv.org/abs/2401.06118 — 2024-01-11 / 2024-09-11 (ICML 2024).
- PV-Tuning — https://arxiv.org/abs/2405.14852 — 2024-05-23 / 2024-05-30.
- QTIP — https://arxiv.org/abs/2406.11235 — 2024-06-17 / 2025-06-18 (NeurIPS 2024).
- VPTQ — https://arxiv.org/abs/2409.17066 — 2024-09-25 / 2024-10-22 (EMNLP 2024).
- HIGGS (théorème de linéarité) — https://arxiv.org/abs/2411.17525 — 2024-11-26.
- GPTVQ — https://arxiv.org/abs/2402.15319 — 2024-02-23 / 2025-06-03.
- EfficientQAT — https://arxiv.org/abs/2407.11062 — 2024-07-10 / 2025-05-19 (ACL 2025).
- SpinQuant — https://arxiv.org/abs/2405.16406 — 2024-05-26 / 2025-02-20 (ICLR 2025).
- QuaRot — https://arxiv.org/abs/2404.00456 — 2024-03-30 / 2024-10-29.
- BitNet b1.58 — https://arxiv.org/abs/2402.17764 — 2024-02-27.
- BitNet b1.58 2B4T — https://arxiv.org/abs/2504.12285 — 2025-04-16 / 2025-04-25.
- bitnet.cpp — https://arxiv.org/abs/2410.16144 — 2024-10-21 / 2024-10-23.
- Microscaling (MX) — https://arxiv.org/abs/2310.10537 — 2023-10-16 / 2023-10-19.
- Pré-entraînement NVFP4 — https://arxiv.org/abs/2509.25149 — 2025-09-29 / 2026-03-04.
- ParetoQ — https://arxiv.org/abs/2502.02631 — 2025-02-04 / 2025-10-13 (NeurIPS 2025).
- CCQ (Baidu) — https://arxiv.org/abs/2507.07145 — 2025-07-09.
- YAQA — https://arxiv.org/abs/2505.22988 — 2025-05-29 / 2026-06-03 (ICML 2026).
- Low-bit favors undertrained — https://arxiv.org/abs/2411.17691 — 2024-11-26 / 2024-11-27 (ACL 2025).
- Scaling Laws for Precision — https://arxiv.org/abs/2411.04330 — 2024-11-07 / 2024-11-30.
- Étude empirique Qwen3 — https://arxiv.org/abs/2505.02214 — 2025-05-04.
- D²Quant — https://arxiv.org/abs/2602.02546 — 2026-01-30 / 2026-02-06.
- HARP — https://arxiv.org/abs/2605.29843 — 2026-05-28 / 2026-09-02.
- Réseau de Leech — https://arxiv.org/abs/2609.02652 — 2026-09-02 (non relu par des pairs).
- SAGE — https://arxiv.org/abs/2610.14745 — 2026-10-10.
- Q-Palette — https://arxiv.org/abs/2509.20214 — 2025-09-24 / 2025-10-22 (NeurIPS 2025) ; code MIT.
- Universalité métrique (0,11 bit) — https://arxiv.org/abs/2602.05790 — 2026-02-05 / 2026-06-15.
- GSQ — https://arxiv.org/abs/2604.18556 — 2026-04-20 / 2026-05-15 ; code Apache-2.0 (`IST-DASLab/GSQ`).
- BCJR-QAT — https://arxiv.org/abs/2605.10655 — 2026-05-11.
- Tied Trit-Planes — https://arxiv.org/abs/2608.08910 — 2026-08-09.
- BITCOS (au-delà de 1,58 bit) — https://arxiv.org/abs/2609.16338 — 2026-09-14.
- Tetra — https://arxiv.org/abs/2609.35465 — 2026-09-28 ; code Apache-2.0 (`pjmalandrino/llvq`).
- XOR-Trellis — https://arxiv.org/abs/2610.00432 — 2026-09-30.
- ApexQuant — https://arxiv.org/abs/2610.07904 — 2026-10-06 ; code sans licence déclarée (`afristrup/ApexQuant`).
- CurveTQ — https://arxiv.org/abs/2610.09212 — 2026-10-06.
- Proteus (Yang et al., ICML 2026) — pas de version arXiv trouvée ; cité d'après CurveTQ.

Licences des dépôts non clonés relevées par l'API GitHub le 2026-10-15. Sources au
format biblatex : `memoire/sources/quantification.bib` (produit par `outils/quant-bib.py`).
Dérivations complètes : `fondations/02-quantification-derivations.md`. Données des figures :
`fondations/journaux/02-quantification/csv/` (produites par `outils/quant-csv-memoire.py`).

**Dépôts lus** (clones `--filter=blob:none` sous `~/dev/lectures/troncons/quantification/`)

| Dépôt | Commit lu (date) | Licence |
|---|---|---|
| ggml-org/llama.cpp | 843e7dc (2026-10-15) | MIT |
| ikawrakow/ik_llama.cpp | ff29e0a (2026-10-14) | MIT |
| turboderp-org/exllamav3 | 058b863 (2026-10-14) | MIT |
| Cornell-RelaxML/qtip | e90c668 (2025-06-21) | GPL-3.0 |
| Cornell-RelaxML/quip-sharp | 1d8f873 (2024-10-29) | GPL-3.0 |
| Vahe1994/AQLM | e79a896 (2026-02-26) | Apache-2.0 |
| microsoft/VPTQ | 942c315 (2025-04-25) | MIT |
| OpenGVLab/EfficientQAT | 39f37f3 (2026-04-10) | MIT |
| spcl/QuaRot | 5008669 (2024-11-26) | Apache-2.0 |
| facebookresearch/SpinQuant | 8f47aa3 (2025-02-14) | CC BY-NC 4.0 |
| microsoft/BitNet | 0b341e5 (2026-07-27) | MIT |
| HanGuo97/flute | 9eb83a1 (2025-04-13) | Apache-2.0 |

**Pages de projet**
- llama.cpp PR #4773 « SOTA 2-bit quants » (IQ2_XXS) — https://github.com/ggml-org/llama.cpp/pull/4773 — ouverte 2024-01-04, fusionnée 2024-01-08.
- llama.cpp PR #19726 (portage des IQ*_K) — https://github.com/ggml-org/llama.cpp/pull/19726 — ouverte 2026-02-19, fermée sans fusion 2026-02-23.
- llama.cpp, publication b11515 — https://github.com/ggml-org/llama.cpp/releases/tag/b11515 — 2026-10-09.
- PrismML, formats Bonsai (Q1_0, Q2_0) — https://docs.prismml.com/download/formats — date non affichée.
- halo-box/strix-llama.cpp PR #148 (treillis Vulkan, brouillon) — https://github.com/halo-box/strix-llama.cpp/pull/148 — **404 le 2026-10-15** : vu seulement dans un résultat de recherche, non vérifié, non compté.
