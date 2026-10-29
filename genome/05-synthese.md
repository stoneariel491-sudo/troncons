# 05 · La synthèse de la ronde 1, et le cahier de construction

Étude « génome des poids » de troncons, rôle de la synthèse (après 00, 01, genome, duplication et
prédictif-élagage). Date : 2026-10-17. Étiquettes : **[mes.]** mesuré, outil et journal commités ;
**[calc.]** calculé par un outil commité ou posé ici pas à pas ; **[litt.]** littérature, non
reproduite ; **[hyp.]** hypothèse dite. Les chiffres de ce document sont **lus dans les journaux**
par `outils/genome/synthese/frontiere.py`, qui écrit `mesures/genome/construction/synthese/`
(`frontiere.csv`, `erreur-contre-kl.csv`, `colonne-par-tenseur.csv`, `apparie-eclaireur.json`).

La consigne de Stone pour cette étape, le 2026-10-17 : « vu qu'on a les conclusions je propose
d'avancer avec ce qu'on a on a déja pris beaucoup de temps ». On construit avec les gagnants mesurés.
Rien ici n'est une recherche neuve : une seule grandeur est calculée de plus, la différence appariée
de la passe KL de l'éclaireur, depuis ses propres CSV par position (§ 1.3).

---

## 0. En bref

1. **Trois mécanismes gagnent, et les trois sont des synonymes** au sens du code génétique : une
   différence de code sans différence de phénotype.
   - **Sans perte : le codon synonyme du zéro.** MXFP4 a seize codes pour quinze valeurs ; le signe
     d'un zéro est une pièce de monnaie (H = 0,9999999967 bit) que le calcul ne lit jamais. Le fondre :
     **3,8434 → 3,7064 bits par poids** sur les 12 tenseurs de référence, **3,8549 → 3,7292** sur tout
     gpt-oss-120b, soit **1,80 Go** de moins à lire [mes.] ; logits identiques au bit [mes.], et le
     noyau GEMV du moteur rend les mêmes bits par construction (§ 4.2, proposition A1).
   - **Sans perte : le contexte de la colonne d'entrée** (classe d'énergie de la colonne, 2 bits par
     colonne et par tenseur). Avec le zéro fondu : **3,6844 bits** [mes.]. Le gain de la colonne
     (0,026 bit en moyenne) vient presque tout de la couche 0 (gate −0,142, up −0,128 bit), où l'état
     caché porte des canaux aberrants ; ailleurs il est sous 0,01 bit. Règle retenue pour la
     construction : la colonne seulement là où elle rend au moins 0,015 bit, soit **3,6843 bits** sur
     les 12 tenseurs, 2 matrices sur 12 [calc.].
   - **Avec perte : la mutation synonyme** (choisir les symboles de la base par rétroaction d'erreur
     pondérée par les entrées réelles des experts, même décodeur). Sa KL de bout en bout, sur
     32 experts sur 768, **appariée position par position** : **−0,0098 ± 0,0033** contre la base
     frontière (2,9 σ, par blocs de fenêtres), meilleure sur 2 060 positions sur 2 550, premier choix
     **+3,7 ± 0,6 points** [calc. sur mes.].
2. **Une correction, barrée et dite.** La consigne attribue la KL 0,0262 à la variante λ = 1,
   δ* = 1 (2,563 bits). ~~λ = 1 : KL 0,0262 contre 0,0360.~~ La KL a été mesurée sur la variante
   **λ = 0**, δ* = 1, à **2,649 bits** (+0,011 sur la frontière) ; λ = 1 (−0,078 bit) n'a été jugée
   qu'à l'erreur de sortie d'expert (8 cases sur 8). **Aucune variante de la mutation synonyme n'est
   donc mesurée à la fois sous la frontière en bits et sous elle en KL.** C'est la première mesure du
   lot B (B0), seuil déclaré au § 4.10.
3. **Tout ce qui tombe tombe pour l'une de trois propriétés mesurées des poids** (§ 2) :
   (a) **une fois l'échelle du bloc connue, les poids sont du bruit** (le code voisin n'apporte que
   0,005 bit ; les rangées tournées sont gaussiennes à 1,5 % près ; deux experts appariés ont le cos de
   deux experts tirés au hasard) : la graine, les motifs, la duplication et la recette sans perte n'ont
   rien à prendre ; (b) **quelques colonnes géantes portent la structure** (une colonne à 144 fois
   l'énergie moyenne ; 5 % des directions portent 23 à 68 % de l'énergie ; un tenseur sur douze tient
   91,5 % de l'erreur poolée) : tout ce qui les écrête ou les noie dans une moyenne perd ;
   (c) **l'erreur de sortie d'un expert ne prédit pas la KL** : au même rapport d'erreur d'expert
   (≈ 1), la KL va de ×1,02 à ×3,06 la base ; S\* a 25 % d'erreur d'expert de moins et ~~33 % de KL
   de plus~~ la même KL que la base sur 10 fenêtres (+0,0004 ± 0,0019 ; passe K10, voir § 2.4). La KL a deux parts : une part lisse, que l'erreur d'expert suit, et une **queue de bascules
   de routage**, qui porte l'essentiel de la moyenne et que ni l'erreur moyenne ni la médiane ne voient.
4. **Les pistes ouvertes** (§ 3) : la géométrie tropicale du routeur est la seule que les mesures
   désignent déjà (45 % des positions basculent elles-mêmes et portent 96,5 % de la KL d'un moteur à
   l'autre ; marge médiane 0,083 contre 0,0095 sur celles qui basculent) ; l'expert pont a un chiffre
   de départ (le meilleur paralogue laisse 33 à 84 % de l'énergie de sortie en erreur selon la couche, et le
   ~~substituer n'est jamais meilleur que retirer l'expert~~ : faux, voir § 3.2) ; la fractale
   n'a aucune mesure et un pronostic défavorable pour sa forme « compression ».
5. **Le cahier de construction** (§ 4) : **lot A**, le format `.trc` v1.2 (drapeau « codes
   canoniques », sorte de flux CODES_COL en demi-octets à contexte par symbole, table de la carte des
   colonnes, empreinte de l'expert canonique dans le répertoire) et son décodeur CUDA à **LUT compacte**
   (12 LUT de 32 bits ne tiennent pas dans les 99 Kio de mémoire partagée d'un bloc de la RTX 4060) ;
   **lot B**, le génome synonyme comme second fichier `<nom>.rapide.trc`, le même décodeur que la
   base de B, et ses deux usages chiffrés : servir les défauts de cache, et le brouillon spéculatif,
   dont la rentabilité exige que le brouillon **ne lise pas le disque**, sauf une réutilisation des
   experts entre positions voisines qui n'est pas mesurée (§ 4.11, lemme B2).

---

## D'où on part, où on va

**Au départ** (fichiers commités) : la frontière sans perte du format `.trc` v1.0, 3,8431 bits par
poids (A_ctx) ou 3,8434 (A_flux), et la base de B, 2,6441 bits à 4,29 % d'erreur relative sur les
poids (ARCHITECTURE § 3, F1) ; le moteur du Tome II, exact au bit contre le codage brut (C3, C11) ;
l'idée de Stone (idees/biomimetisme-genome-des-poids.md) et les quatre livrables de la ronde :
genome/00-etat-de-l-art.md et 01-eclaireur.md (l'éclaireur), genome/genome.md (la recette),
genome/duplication.md (la parenté des experts), genome/predictif-elagage-pour-le-memoire.md (le
codage prédictif et l'élagage).

**Ce que ce document établit** : la frontière commune des quatre équipes, placée sur un seul axe de
qualité (la KL sur le texte, rapportée à la base du même protocole) ; la raison de chaque échec,
rattachée à une propriété mesurée ; ce que les mesures disent déjà des pistes non suivies ; et le
cahier, au bit et au fichier près, des deux lots à construire.

**Ce qui reste** : les lots A et B eux-mêmes (§ 4), leurs mesures déclarées, et le Tome III.

---

## 1. La frontière : bits par poids contre KL sur le texte

### 1.1 Pourquoi un seul axe, et pourquoi des rapports

Le juge de la ronde est la **divergence de Kullback-Leibler** de la distribution du jeton suivant,
contre la référence f64, sur wiki.test (l'instrument `juge` du lot R, Tome II ch. 05). La ronde l'a
appris à ses dépens : l'erreur sur les poids, puis l'erreur de sortie d'un expert, ont chacune donné
des gagnants que la KL a fait tomber (§ 2.3).

Les trois passes KL de la ronde **n'ont pas le même protocole** :

| Protocole | Équipe | Experts remplacés | Positions notées | KL de la base |
|---|---|---|---|---|
| P1 | éclaireur | 32 sur 768 (couches 0, 8, 16, 23 × experts 0, 4, …, 28) | 2 550 (10 fenêtres) | 0,0360 ± 0,0029 |
| P2 | genome | 8 sur 768 (couches 0, 8, 16, 23 × experts 0, 16) | 765 (3 fenêtres) | 0,0226 ± 0,0031 |
| P3 | prédictif-élagage | 128 sur 768 (les 12 tenseurs entiers : 4 couches × 32 experts) | 1 275 (fenêtres 5 à 9) | 0,0636 ± 0,0050 |
| P0 | (sans perte) | — | logits identiques au bit | 0 exactement |

Une KL absolue de P3 ne se compare pas à une KL de P1 (quatre fois plus d'experts remplacés). Ce qui
se compare : **le rapport à la base du même protocole**, et, mieux, **la différence appariée**
position par position contre cette base (même vérité, mêmes positions ; règle du lot R :
égal si d̄ ≤ 2σ(d̄), meilleur si d̄ + 2σ(d̄) < 0).

Les débits non plus n'ont pas tous le même estimateur : codec réel décodé (P0, P3, frontière de P2),
entropie des symboles sans échelles (P1 : H0), comptabilité complète du brin (genome). La colonne
`estimateur_bits` du CSV le dit pour chaque point ; à l'intérieur d'un protocole, base et mécanisme
ont le même estimateur. Pour la frontière : le codec réel rend 2,6441 bits ; H0 + échelles donne
2,679 (il ignore le contexte κ que le codec exploite) ; H0 seul 2,6415 (il ignore les échelles, 0,0375
bit) (F1, 01 § 7). Les deux omissions se compensent presque ; à l'intérieur de P1, base et mutation
synonyme sont lues par le même H0.

### 1.2 Les points

`mesures/genome/construction/synthese/frontiere.csv` (23 points ; un par mécanisme et par protocole,
avec sa source). Le tableau ci-dessous en garde les points jugés à la KL ; rapport = KL / KL de la base
du même protocole ; différence appariée en unités de KL, ± un écart-type.

| Mécanisme | Prot. | Bits par poids | KL | Rapport | Appariée | Même premier | Verdict |
|---|---|---|---|---|---|---|---|
| frontière sans perte (A_flux) | P0 | 3,8434 | 0 | — | — | 100 % | référence |
| **codon synonyme du zéro** | P0 | **3,7064** | **0** | — | — | 100 % | **gagne** |
| **zéro + colonne (κ × q)** | P0 | **3,6844** | **0** | — | — | 100 % | **gagne** |
| duplication D1 (parent) | P0 | 3,8442 | 0 | — | — | 100 % | tombe |
| base frontière | P1 | 2,6381 (H0) | 0,0360 | 1 | — | 87,1 % | référence |
| **mutation synonyme λ = 0** | P1 | 2,6488 (H0) | **0,0262** | **0,727** | **−0,0098 ± 0,0033** | **90,9 %** | **gagne en KL, +0,011 bit** |
| base frontière | P2 | 2,6441 | 0,0226 | 1 | — | 91,4 % | référence |
| S\* (brin + rotation + pondération + exceptions) | P2 | 2,64 | 0,0301 | 1,335 | +0,0076 ± 0,0047 | 90,3 % | ~~tombe~~ égal (3 fenêtres) |
| base frontière, 10 fenêtres (K10, non commité) | P2-10 | 2,6441 | 0,0206 | 1 | — | 91,9 % | référence |
| S\*, 10 fenêtres (K10, non commité) | P2-10 | 2,64 | 0,0209 | 1,018 | +0,0004 ± 0,0019 | 91,9 % | **égal** ; ne gagne pas |
| base frontière | P3 | 2,6444 | 0,0636 | 1 | — | 81,6 % | référence |
| **partitions par κ, chaque tenseur à l'erreur de la base** | P3 | **2,4079** | 0,0702 | 1,103 | +0,0066 ± 0,0053 | 79,5 % | **égale par la règle, 0,911 × les bits** |
| partitions par κ, erreur moyenne égale | P3 | 2,3743 | 0,0804 | 1,263 | +0,0167 ± 0,0049 | 78,4 % | tombe |
| hebbien (δ, ligne, colonne) | P3 | 1,9619 | 0,0909 | 1,429 | +0,0273 ± 0,0039 | 73,4 % | tombe |
| hebbien par e | P3 | 2,1815 | 0,1947 | 3,059 | +0,1310 ± 0,0072 | 60,8 % | tombe |
| hebbien (e, ligne, colonne) | P3 | 1,7556 | 0,1917 | 3,012 | +0,1281 ± 0,0067 | 59,4 % | tombe |
| élagage par activité de colonne (e, q) | P3 | 1,6942 | 0,2714 | 4,265 | — | 57,1 % | tombe |
| partitions par e (remplissage inverse) | P3 | 2,0178 | 0,3089 | 4,854 | — | 58,5 % | tombe |

Points sans KL (jugés à erreur de poids ou de sortie d'expert égale ; ils se placent sur l'axe des
bits seulement) : graine + coefficients 3,06 bits ; motifs partagés 2,90 ; duplication D2b 2,6429 ;
brin tourné au critère W 2,3248 (erreur de poids égale) ; S\* à erreur de sortie d'expert égale 2,3595 ;
mutation synonyme λ = 1, 2,5634 (H0, contre 2,6415 pour la frontière sur les mêmes experts).

### 1.3 La différence appariée de l'éclaireur, calculée ici

L'éclaireur avait comparé les deux moyennes sans apparier (01 § 6 : écart de 0,0098 ≈ 3,6 fois
l'incertitude d'une moyenne). Ses CSV par position sont commités ; `frontiere.py` les apparie
(`apparie-eclaireur.json`) [calc. sur mes.] :

- **Témoin**, déclaré avant l'exécution : la KL moyenne recalculée depuis chaque CSV égale celle de
  `juge kl` à 10⁻¹² près : 0,036013763948 contre 0,036013763948 (écart 1,8·10⁻¹³), 0,026168395170
  contre 0,026168395170 ; **tient**. Cassure (première ligne retirée) : 0,036021222 contre
  0,036013764, **tombe** (`frontiere-casse.log`).
- **Différence appariée** (synonyme − base) : **−0,009845** ; écart-type naïf 0,00190 (5,2 σ) ;
  écart-type par blocs de fenêtres, qui respecte la corrélation des positions d'une même fenêtre
  (elles partagent leur passé, donc leurs bascules) : **0,00334 (2,9 σ)**. Meilleure significativement
  par les deux estimateurs.
- 2 060 positions sur 2 550 (80,8 %) ont moins de KL avec la mutation synonyme ; premier choix
  identique : +3,73 ± 0,59 points.

### 1.4 La figure que ces points méritent

Une figure, deux panneaux, tirée de `frontiere.csv` par un script commité (figure F1 de la note du mémoire, § 4) :
- **à gauche**, le plan (bits par poids lus, rapport de KL à la base), axe vertical logarithmique ;
  chaque protocole sa forme de marqueur, chaque équipe sa teinte ; la base de chaque protocole en
  (≈ 2,64 ; 1) ; les gagnants en plein, les perdants en creux ; une flèche de chaque perdant vers sa
  « promesse » à erreur de poids ou de sortie égale (sa position sur l'axe des bits seul), pour
  montrer la distance entre ce que promettait la métrique intermédiaire et ce que la KL a rendu ;
- **à droite**, l'axe sans perte agrandi : 3,8434 → 3,7064 → 3,6843, trois barres empilées par
  tenseur (`colonne-par-tenseur.csv`), qui montrent que la colonne ne vit qu'à la couche 0.

---

## 2. Ce qui gagne, ce qui tombe, et pourquoi

### 2.1 Les trois propriétés mesurées des poids

**(a) Une fois l'échelle du bloc connue, les poids sont du bruit.**

| Mesure | Valeur | Source |
|---|---|---|
| information apportée par le code voisin, sachant l'échelle | 0,005 bit (gauche 0,0076, dessus 0,0091) | 03 § 1.6 ; prédictif-élagage § 2 [mes.] |
| information apportée par l'expert voisin (même place) | 0,0043 bit | prédictif-élagage § 2 [mes.] |
| cos des rangées de deux experts appariés (algorithme hongrois) | 0,04 gate, 0,03 up, 0,07 à 0,11 down ; hasard 0,04 | duplication § 2.2 [mes.] |
| erreur du brin sur les rangées tournées, contre une gaussienne vraie | 0,0739 contre 0,0731 (1,5 % près) ; kurtosis 3,0 | genome § 5.3 [mes.] |
| la graine suit la loi Bêta d'une direction uniforme | mesuré au-dessus de la prédiction du lemme 1 de 0,6 à 2 points (quantification des coefficients) | genome § 2.3 [mes.] |
| signe des zéros | 0,9999999967 bit d'entropie, sans effet sur la valeur | 01 § 2.1 [mes.] |

**(b) Quelques colonnes géantes, et quelques directions, portent la structure.**

| Mesure | Valeur | Source |
|---|---|---|
| énergie des blocs d'exposant 129 et 130 | 74,2 % de l'énergie pour 5,8 % des poids | 01 § 2.2 [mes.] |
| énergie des 5 % premières directions singulières | 23 à 68 % (17 à 19 % pour la même matrice permutée) ; kurtosis des rangées jusqu'à 348 | genome § 6 [mes.] |
| colonne la plus massive (blk.8 down, expert 16, colonne 1011) | 144 fois l'énergie moyenne d'une colonne ; reçoit 334 fois l'erreur moyenne du brin | genome § 8.2 [mes.] |
| part de l'erreur poolée de la frontière tenue par un seul tenseur | 91,5 % (blk.23.ffn_down) | prédictif-élagage § 3 [mes.] |
| rapport de la colonne la plus énergique à la médiane (racine d'énergie) | 1,11 (blk.0 down) à 2,93 (blk.23 gate) | prédictif-élagage § 2 [mes.] |
| gain du contexte de colonne, par tenseur | −0,142 et −0,128 bit (couche 0, gate et up) ; sous 0,01 ailleurs ; +0,0006 sur blk.0 down (la carte coûte plus qu'elle ne rend) | `colonne-par-tenseur.csv` [mes.] |
| part du gain d'un parent que rend un parent de hasard | 46 % en moyenne, 88 à 94 % à la couche 0 | duplication § 0.8 [mes.] |

La dernière ligne et l'avant-dernière disent la même chose par deux chemins indépendants : ce que
les experts d'une couche partagent n'est pas une parenté d'expert à expert, c'est **une statistique
par colonne d'entrée**, commune aux 32 experts parce qu'elle vient de leur entrée commune (l'état
caché, et ses canaux aberrants à la couche 0). La duplication la voyait comme « parenté de hasard » ;
prédictif-élagage l'a prise comme contexte, et c'est le seul contexte qui a passé son seuil.

**(c) L'erreur de sortie d'un expert ne prédit pas la KL.**

`erreur-contre-kl.csv` [calc. sur mes.] :

| Mécanisme | Prot. | Rapport d'erreur d'expert à la base | Rapport de KL à la base |
|---|---|---|---|
| mutation synonyme λ = 0 | P1 | 0,267 | 0,727 |
| S\* | P2 (3 fenêtres) ; P2-10 | 0,747 | ~~1,335~~ ; 1,018 (10 fenêtres) |
| partitions par κ, erreur moyenne égale | P3 | 0,984 | 1,263 |
| hebbien par e | P3 | 1,023 | 3,059 |
| hebbien (e, ligne, colonne) | P3 | 1,656 | 3,012 |
| partitions par e | P3 | 3,951 | 4,854 |

Trois points ont un rapport d'erreur d'expert dans [0,74 ; 1,03] et des rapports de KL de 1,02 à
3,06 ; S\* retire 25 % de l'erreur d'expert et rien de la KL ; le seul gagnant en KL divise l'erreur
d'expert par près de quatre pour un gain de KL de 27 %. La relation n'est ni monotone ni
proportionnelle.

### 2.2 La forme de la KL : une part lisse et une queue de bascules

**Ce que montrent les quantiles** (journaux du juge) [mes.] :

| | base P1 | synonyme λ = 0 P1 | base P2 | S\* P2 | base P2-10 | S\* P2-10 |
|---|---|---|---|---|---|---|
| médiane | 0,0088 | 0,0038 (÷2,3) | 0,00172 | 0,00188 (×1,09) | 0,00184 | 0,00152 (÷1,21) |
| 99e centile | 0,495 | 0,410 | 0,437 | 0,550 | 0,411 | 0,338 |
| 99,9e centile | 1,59 | 1,70 | 0,899 | 1,43 | 1,37 | 1,59 |
| maximum | 4,17 | 3,94 | 1,20 | 2,79 | 3,01 | 3,22 |

(P2-10 : `mesures/genome/genome/kl/comparer10-base-contre-recette.json`, écrit par la passe K10 de l'équipe genome à la fin de ce travail, **non commité par elle à l'heure où j'écris**.)

**Ce que montre le moteur** (Tome II, lot R, § 2.10, deux moteurs exacts l'un contre l'autre) [mes.] :
5 087 bascules de routage sur 122 640 (couche, position), 4,15 % ; les 45 % de positions qui basculent
elles-mêmes portent **96,5 % de la KL** ; la marge du routeur (4e logit − 5e) a pour médiane 0,083 sur
toutes les (couche, position) et **0,0095** sur celles qui basculent. Et la preuve par
l'intervention (expérience B, déclarée avant sa passe, même section § 2.9) : **imposer à l'un des
deux calculs les experts choisis par l'autre retire 88 % de la KL** (0,0145 → 0,00168 ; médiane
9,8·10⁻⁴ → 2,2·10⁻⁴ ; premier choix 92,5 → 97,2 %).

**Lecture** [calc. sur mes., l'interprétation est une hypothèse de travail, § 5] : une perturbation
δh de l'état caché a deux effets sur la KL. (i) **La part lisse** : la distribution de sortie bouge
continûment, au second ordre en δh (la KL est quadratique près de zéro, KL ≈ ½ δzᵀ F δz, F l'information
de Fisher des logits) ; l'erreur de sortie d'expert la suit. (ii) **La part de bascule** : aux
couches suivantes, si δh pousse le score d'un expert au-delà de la marge m = z₍₄₎ − z₍₅₎ du routeur,
l'ensemble des experts change ; la sortie de la couche saute d'une quantité qui ne dépend plus de
‖δh‖ mais de la différence entre deux experts (qui, mesuré par la duplication, ne se ressemblent pas :
33 à 84 % de l'énergie de sortie selon la couche). Cette part est **discontinue** en δh et pèse sur la moyenne par
sa queue. Le synonyme réduit la part lisse (médiane ÷2,3) sans toucher la queue (99,9e centile 1,59 →
1,70) ; ~~S\* garde la médiane (×1,09) et **épaissit la queue** (99e 0,437 → 0,550, maximum 1,20 →
2,79)~~ sur 10 fenêtres, S\* réduit lui aussi la part lisse (médiane ÷1,21, 99e centile 0,411 →
0,338) et épaissit l'extrême de la queue (99,9e 1,37 → 1,59, maximum 3,01 → 3,22) : les deux se
compensent dans la moyenne (+0,0004 ± 0,0019). Sur 3 fenêtres, la queue l'emportait par hasard
d'échantillon. Pour la moyenne, c'est la queue qui décide. D'où la règle de la ronde, maintenant expliquée : seule la
KL sur le texte juge, parce que seule elle voit les bascules.

### 2.3 Chaque mécanisme, et la propriété qui l'a décidé

| Mécanisme | Verdict | Propriété | Le chiffre qui le dit |
|---|---|---|---|
| **codon synonyme du zéro** | **gagne, sans perte** | (a), à l'envers : il retire du bruit pur au lieu d'en chercher la structure | 0,1370 bit ; logits identiques au bit |
| **contexte de colonne** | **gagne, sans perte** (couche 0) | (b) : la seule structure de premier ordre qui reste sachant l'échelle est par colonne d'entrée | −0,142 / −0,128 bit à la couche 0 ; seuil 0,015 |
| **mutation synonyme** | **gagne en KL** ; débit à confirmer (λ = 1) | (c), dans le bon sens : pondérée par H = E[g² x xᵀ], elle range l'erreur dans les directions que les entrées n'excitent pas ; elle réduit la part lisse | appariée −0,0098 ± 0,0033 ; médiane ÷2,3 ; erreur de poids **plus haute** (λ = 0 : 4,7 % contre 4,4 % ; λ = 1 : 4,9 % contre 4,3 %) |
| **partitions par κ, tenseur par tenseur** | égale en KL, 0,911 × les bits | relative à la ligne, elle ne déplace pas de bits d'une échelle à l'autre : elle respecte (b) et (c) | appariée +0,0066 ± 0,0053 (1,2 σ) |
| graine + coefficients | tombe | (a) : un livre de codes aléatoire de dimension 8 à 16 sur des directions uniformes (lemme 1) | 3,06 bits à l'erreur de la base ; ≥ 6,3 % d'erreur prédite à 2,67 bits |
| motifs partagés | tombe | (a) : quantificateur vectoriel de petite dimension ; le partage entre experts ne coûte rien et ne rend rien | 2,90 bits |
| recette + complément exact | tombe (lemme 3) | (a) : l'entropie des codes est déjà atteinte | 4,05 à 4,37 bits contre 3,84 |
| duplication (parent) | tombe | (a) entre experts, et la part qui ressemble à une parenté est (b) | 0,0034 bit dont 0,0016 au hasard ; D2b 2,6429 |
| mutation soustraite (parent) | tombe | la soustraction fait sortir l'enfant de la grille MXFP4 | +0,49 bit |
| brin lu par codons, critère W | gagne en poids, tombe en sortie d'expert | (b) : la table écrête les colonnes massives, dont l'erreur revient sur la colonne par la rotation inverse | colonne 1011 : énergie ×144, erreur ×334 ; sortie 7,63 % contre 6,77 % |
| S\* (le brin + exceptions 0,1 %) | gagne en sortie d'expert, ~~tombe~~ **égal** en KL (10 fenêtres) | (c) : la part lisse baisse, l'extrême de la queue monte | rapport d'erreur 0,747 ; KL appariée +0,0004 ± 0,0019 ; médiane ÷1,21, 99,9e centile +16 % |
| hebbien par e | tombe en KL à erreur d'expert égale | (b) + (c) : le remplissage inverse à travers les échelles concentre l'erreur sur les blocs et lignes de petite échelle, que la norme RMS des couches suivantes ramène à l'échelle | erreur d'expert 1,02 ; KL 3,06 ; médiane ×3,3 |
| élagage par magnitude | tombe | (a) : les petites magnitudes portent peu d'énergie mais aussi peu de bits | 1,012 × la base à erreur égale |
| partitions par e, élagage par activité | tombent | (b) mal utilisée : la métrique par matrice vide les lignes de petite échelle qui pèsent par la symétrie gate/up ↔ down | erreur d'expert 22 à 35 % ; KL ×4,3 à ×4,9 |
| ECSQ sans rétroaction | ne gagne presque rien | la frontière est déjà près de l'ECSQ dans le domaine des poids | 2,615 bits, erreur d'expert pire |

### 2.4 Pourquoi S\* ne gagne pas, dit au plus près

S\* est le cas le plus instructif, parce qu'il gagne tout sauf la KL : erreur de poids, erreur de
sortie (8 experts sur 8 ; de 333 positions gagnées sur 512 à 106 sur 106), et même l'erreur orthogonale
au gain (genome, second chemin Python, commit `0ea2e4c`). ~~Sa KL appariée est **+0,0076 ± 0,0047**
(1,6 σ) : égale par la règle, défavorable en estimation, et sa queue est plus épaisse.~~ Sur 3 fenêtres
(765 positions, commité), sa KL appariée était +0,0076 ± 0,0047 (1,6 σ). **Sur 10 fenêtres
(2 550 positions, passe K10 de l'équipe genome, déclarée avant, fichier non commité par elle à l'heure
où j'écris), elle est de +0,0004 ± 0,0019 : égale à la base**, premier choix égal (91,92 % contre
91,88 %). Ce qui a changé : trois fois plus de positions ; l'écart des 3 premières fenêtres était dans
le bruit, et il s'y est fondu.

Ce que cela dit, et c'est la propriété (c) dans sa forme la plus nette : **25 % d'erreur d'expert en
moins, 0 % de KL en moins.** La part lisse baisse (médiane ÷1,21, 99e centile −18 %), l'extrême de la
queue monte (99,9e centile +16 %, maximum +7 %), et la moyenne ne bouge pas.

Pourquoi l'extrême de la queue monte [hyp., à mesurer] : la rotation de Hadamard répartit l'erreur de
chaque rangée sur 64 colonnes ; la sortie W x = (W Rᵀ)(R x) voit cette erreur à travers R x, où une
activation massive est elle-même répartie sur les 64 positions de son morceau. La pondération de S\*
est **diagonale** (h = diag(R Σ Rᵀ)) : elle ne voit pas la corrélation, dans le domaine tourné, entre
les 64 positions qui portent le même canal massif. La base, elle, rend presque exacts les plus grands
codes de chaque bloc (sa classe {6} est exacte) et laisse la contribution des canaux massifs presque
intacte, ce qui protège les marges du routeur des couches suivantes, qui lisent le même état caché. La
mutation synonyme, qui pondère par le H **complet**, n'a pas ce défaut, et c'est elle qui gagne. La
prédiction qui départagerait : la KL de S\* combiné à la rétroaction par le H complet (genome § 9.3) ;
elle n'est pas mesurée et n'est pas dans les lots.

### 2.5 La leçon, en une phrase par niveau

- Dans le domaine des poids, il n'y a rien à générer : le gain se prend sur ce que le calcul **ne
  lit pas** (le signe d'un zéro) ou sur ce que le codeur **sait déjà** (l'échelle, la colonne).
- Dans le domaine des sorties, la moyenne de l'erreur ne suffit pas : ce qui compte est l'endroit où
  elle tombe. Le synonyme la place là où les entrées ne regardent pas, l'hebbien là où l'énergie est
  faible ; les deux ont une erreur d'expert basse, seul le premier gagne en KL.
- Dans le domaine du texte, ce qui coûte est la **bascule** : une erreur ne vaut que par sa
  probabilité de faire franchir une frontière du routeur à une couche suivante.

---

## 3. Les pistes ouvertes, et ce que les mesures en disent déjà

Aucune de ces pistes n'est dans les lots A et B. Chacune porte ce qui est mesuré, ce qui ne l'est pas,
et la mesure qui la jugerait.

### 3.1 La géométrie tropicale du routeur (priorité, idée de Stone § 5 quinquies)

**Le cadre** [calc.]. Le routeur d'une couche calcule z = W_r h + b_r (32 logits pour le 20b, 128
pour le 120b) et garde les k = 4 plus grands. L'ensemble choisi S(h) est constant sur les régions
{h : z_i(h) ≥ z_j(h) pour tout i ∈ S, j ∉ S}, qui sont des **polyèdres** de l'espace de h
(intersections de demi-espaces) ; leurs frontières sont les hyperplans z_i = z_j. La fonction
h ↦ Σ_{i ∈ S(h)} z_i(h), somme des k plus grands logits, est convexe et linéaire par morceaux : c'est
un **polynôme tropical** du semi-anneau (max, +), et le complexe de ses régions est son hypersurface
tropicale (le lien entre réseaux linéaires par morceaux et géométrie tropicale est celui de Zhang,
Naitzat et Lim, arXiv 1805.07091, v1 du 2018-05-18, seule version, résumé lu le 2026-10-17 : les
réseaux ReLU sont des applications rationnelles tropicales, leurs frontières de décision des
hypersurfaces tropicales [litt.] ; le routeur top-k, qui n'est pas un ReLU, s'y range par la même
algèbre (max, +)). La
**marge** m(h) = z₍₄₎ − z₍₅₎ mesure la distance de h à la frontière la plus proche, en unités de
logit ; la distance euclidienne vaut m / ‖w₍₄₎ − w₍₅₎‖.

**Ce que les mesures en disent déjà** [mes.] :
- les bascules sont la cause dominante de la KL entre deux calculs proches : 88 % de la KL retirée
  par le seul routage imposé (R § 2.9) ; 45 % des positions basculent elles-mêmes et portent 96,5 %
  de la KL (R § 2.10) ;
- la marge prédit la bascule : médiane 0,083 sur toutes les (couche, position), 0,0095 sur celles qui
  basculent, 1 % des bascules sous 9,6·10⁻⁵ ;
- sur le 120b, un seul arrondi (le cache KV en f16) porte 70 à 77 % des bascules et fait tomber le
  premier jeton d'un texte après une cascade de 20 bascules sur 36 couches (épreuve J1, constat M5) ;
- dans la ronde, les gains en part lisse ne touchent pas la queue (§ 2.2).

**Ce qui n'est pas mesuré** : la loi de la marge par couche ; la corrélation des marges d'une même
position d'une couche à la suivante ; la probabilité de bascule à la couche ℓ + 1 sachant la marge et
l'erreur injectée à la couche ℓ.

**La construction qu'elle désigne, « la garde tropicale »** [hyp., chiffrable sur des journaux
existants] : en mode rapide, après les experts rapides de la couche ℓ, le moteur calcule de toute
façon le routeur de la couche ℓ + 1 ; si sa marge est sous un seuil τ, il refait la couche ℓ avec les
experts exacts pour cette position (le défaut d'expert exact est la seule dépense), puis reprend. Le
coût est la part des (couche, position) sous τ ; le gain, la part des bascules évitées. Les deux se
lisent sur les journaux de routage du lot R (`r1/routage/*.bin`, format en tête de `bascules.py`)
**sans nouvelle passe du modèle** : la courbe (part des cellules sous τ, part des bascules sous τ)
pour τ de 10⁻⁴ à 0,1. Seuil de décision, à déclarer avant la lecture : la garde vaut d'être construite
si elle attrape au moins 80 % des bascules pour au plus 10 % des cellules (le coût d'un défaut exact
sur 10 % des cellules est d'au plus 10 % des octets du mode exact). Une seconde lecture : la marge
de la couche ℓ comme **priorité de préchargement** des experts de la couche ℓ + 1 (un état loin de
toute frontière garde probablement ses experts) ; elle se lit sur les mêmes journaux.

### 3.2 L'expert pont (idée de Stone § 5 sexies)

**Ce qui est mesuré** (duplication § 0.6) [mes.] : servir un expert manquant par le meilleur autre
expert résident (le paralogue fonctionnel) laisse **79 / 84 / 66 / 33 %** de l'énergie de sa sortie en
erreur (couches 0 / 8 / 16 / 23 ; hasard 95 / 94 / 72 / 47 %) ; dans la sortie de la couche,
~~**substituer n'est jamais meilleur que retirer l'expert**~~ (16,7 contre 13,3 % ; 13,9 contre 9,2 ;
7,1 contre 7,6 ; 3,7 contre 3,7 %). Corrigé (`duplication.md` § 0 point 6) : refait le 2026-10-29 par expert depuis `mesures/genome/duplication/csv/paralogues.csv` (rédaction du Tome III, chapitre de la duplication ; refait par le juge de la rédaction, `memoire/tome3/JUGEMENT-redaction-fr.md` § 3.3) : substituer fait mieux que retirer pour 4 experts sur 32 (couche 0), 5 sur 32 (8), 25 sur 31 (16) et 21 sur 31 (23) ; en moyenne 0,0707 contre 0,0757 à la couche 16, 0,0368 contre 0,0370 à la 23. La conclusion tient : un paralogue ne vaut pas la base. La mutation tronquée (α ⊙ parent) fait 91 % d'erreur de sortie.
La famille des experts d'une couche n'est pas de rang faible : 90 % de son énergie demande 2 180
directions sur 2 880 (couche 12, gate ; 2 385 pour la famille permutée, `spectre-c12.json`).

**Ce que cela dit** : la barre d'un pont n'est pas l'expert absent, c'est **le retrait de l'expert**
(le routage renormalisé sur les trois présents), qui coûte déjà 13,3 / 9,2 / 7,6 / 3,7 % d'erreur de
sortie de couche. Un pont commun à une couche, de rang faible, ne peut pas imiter 32 experts que rien
ne relie (propriété (a)) ; un pont **par expert** coûte ce qu'il imite. La seule forme qui échappe à
l'argument est un pont qui imite non pas l'expert mais **sa sortie sur la région du routeur où il est
appelé** (les polyèdres du § 3.1) : un petit modèle local ajusté aux moindres carrés sur les entrées
réelles qui routent vers l'expert. La mesure : erreur de sortie de couche et KL, contre le retrait.
Rien n'en est mesuré.

### 3.3 La fractale (idée de Stone § 5 quinquies)

- **(a) Lois de puissance des spectres** : non mesuré. Les données commitées ne donnent que la part
  d'énergie à sept rangs (1, 8, 29, 144, 288, 720, 1 440) pour un expert par tenseur
  (`structure-spectre.json`) : trop peu pour ajuster une pente. Ce qu'elles montrent : l'excès sur le
  hasard (Marchenko-Pastur) est modeste pour gate et up (27 % contre 17 % au rang 144) et fort pour
  down (jusqu'à 68 % contre 19 %). La littérature des spectres à queue lourde des matrices entraînées
  (Martin et Mahoney, arXiv 1810.01075, v1 du 2018-10-02, résumé lu le 2026-10-17 : les densités
  spectrales des matrices des réseaux de l'état de l'art montrent une « auto-régularisation à queue
  lourde » [litt.]) donne l'hypothèse à mesurer, pas la réponse pour gpt-oss. La mesure : les 2 880
  valeurs singulières de chaque matrice (calculées par `structure.py`, non sauvées), pente log-log,
  test contre une loi exponentielle.
- **(b) Compression par systèmes de fonctions itérées** (Barnsley, Jacquin) : une auto-similarité est
  une dépendance entre morceaux du tenseur ; la propriété (a) dit qu'à l'échelle du bloc il n'y en a
  pas (0,005 bit pour le voisin, 0,0043 pour l'expert voisin) ; le pronostic est celui de la graine,
  pour la même raison. Non mesuré.
- **(c) Une courbe de Hilbert pour ranger les experts sur le disque** : un tronçon est un expert
  entier, lu d'une seule requête de 12 Mo (ARCHITECTURE § 4.1, principe 4) ; une lecture de 12 Mio ne
  gagnait que 9 % sur trois de 4,2 Mio [mes., partisan A § 4.3]. À cette granularité, l'ordre des
  tronçons sur le NVMe ne compte presque pas [calc. sur mes.] : piste fermée par ce chiffre, sauf à
  descendre sous le tronçon.

### 3.4 Les suites des équipes, non retenues pour les lots

| Piste | Ce qui est mesuré | Pourquoi pas maintenant |
|---|---|---|
| S\* + rétroaction par le H complet (genome § 9.3) | S\* égal en KL (10 fenêtres) ; le synonyme gagne avec le H complet | seule hypothèse du § 2.4 ; demande une passe KL neuve |
| synonyme à 1 bit de magnitude (01 § 8.5) | 2 experts : 20,5 / 19,5 % d'erreur d'expert contre 25,7 / 25,1 % pour la frontière à 1 bit | passe arrêtée ; à refaire si le mode rapide doit tenir en RAM (§ 4.5) |
| plus d'entrées de calibration, Ledoit-Wolf (01 § 8.3) | écart calibration / évaluation ×3,5 à δ* = 1 | entre dans B1 comme option déclarée, pas comme recherche |
| structure de rang (genome § 6) | ≤ 0,064 bit sur blk.0 down pour 0,011 de coût, rien sur up | gain net ≤ 0,05 bit, avec perte |
| κ dominé + colonne + zéro, 24 couches (prédictif § 9) | 0,911 × les bits à KL égale sur 4 couches | concurrente du synonyme ; le lot B prend le synonyme, meilleur en KL |

---

## 4. Le cahier de construction

Deux lots, dans cet ordre : **A** est sans perte et touche le fichier exact ; **B** ajoute un second
fichier, avec perte, et ne touche pas au premier. Chaque pas a son témoin, sa cassure et son seuil,
**déclarés ici, avant toute construction**. Toute modification du format passe par une décision
écrite dans `decisions/ARCHITECTURE.md` (§ 4.15, couture F) : le premier pas de chaque lot est cette
décision, recopiée de ce cahier.

### 4.1 Lot A : ce qu'il porte, et ce qu'il rend

**Ce qu'il porte** : (1) le codon synonyme du zéro dans tous les flux de codes (le codeur réécrit tout
demi-octet 8 en 0 avant le codage entropique) ; (2) le contexte de la colonne d'entrée, sous la forme
d'une nouvelle sorte de flux CODES_COL, **seulement pour les matrices où il rend au moins 0,015 bit
par poids** (règle du § 0 ; sur les 12 tenseurs mesurés : blk.0 gate et up) ; (3) l'empreinte de
l'expert canonique, sans laquelle le témoin du moteur ne peut plus comparer un expert décodé à son
origine.

**Ce qu'il rend** [calc. sur mes.] :

| | gpt-oss-20b | gpt-oss-120b |
|---|---|---|
| poids d'experts | 19 110 297 600 | 114 661 785 600 |
| sans perte v1.0 (A_flux, tous tenseurs) | 3,8509 bits | 3,8549 bits |
| zéro fondu (A_flux, tous tenseurs) [mes.] | 3,7230 bits (−0,1280) | 3,7292 bits (−0,1257) |
| octets d'experts en moins (zéro seul) | 305,6 Mo | **1 801,2 Mo** |
| colonne en plus (12 tenseurs du 20b seulement) | −0,0221 bit en moyenne sur ces 12 tenseurs, dont tout à la couche 0 | non mesuré |
| fichier `.trc` v1.0 (relevé sur le disque) | 11 157 405 696 o | 57 730 662 400 o |
| fichier `.trc` v1.2 attendu (zéro seul, ± alignement de 4 Kio par tronçon) | ≈ 10,85 Go | **≈ 55,93 Go** |
| toit du débit à disque limitant | +3,4 % (zéro) ; +4,3 % sur les 12 tenseurs avec la colonne | +3,4 % (zéro) |

Calcul du toit : 1 / (1 − 0,1257 / 3,8549) − 1 = 1 / 0,96739 − 1 = 3,37 % ; sur les 12 tenseurs,
1 / (3,6843 / 3,8434) − 1 = 4,32 %. Le relevé du moteur (O § 6.5 : 0,707 Go de tronçons par jeton sur le
120b) donnerait 0,684 Go par jeton avec le zéro seul [calc.]. L'alignement de chaque tronçon sur 4 096
octets coûte au plus 4 608 × 4 096 = 18,9 Mo sur le 120b, soit 0,0013 bit par poids [calc.].

### 4.2 Lot A : la preuve que le moteur rend les mêmes bits

**Proposition A1 (GEMV du moteur).** Le noyau `produit_bloc` (`moteur/crates/trc-noyaux/noyaux/
gemv.cuh`) part de `s = 0.0f` (+0) et accumule `s = fmaf(v, x, s)` dans un ordre fixe, avec
`v = valeur_e2m1x2(c)`, qui vaut −0.0f pour le code 8 et +0.0f pour le code 0. Remplacer le code 8 par
le code 0 ne change aucun bit de `s` à aucun pas.

*Démonstration.* (1) **`s` ne vaut jamais −0**, dans aucun des deux calculs. Au départ `s` = +0.
À un pas, `s' = RN(v·x + s)`, la somme exacte arrondie au plus près. Si v·x + s est exactement nul,
IEEE 754 rend +0 en arrondi au plus près dès que les deux termes ne sont pas tous deux −0 ; or `s` n'est
pas −0 (hypothèse de récurrence) : `s'` = +0. Sinon, `s'` est non nul (|v| ≥ 1 pour un code non nul,
donc |v·x| ≥ |x| ne s'arrondit pas à zéro ; et une somme exacte non nulle de nombres représentables ne
s'arrondit pas à zéro, faute de sous-dépassement en dessous du plus petit sous-normal). (2) **Un pas sur
un code nul est le même dans les deux calculs.** Pour v = ±0, v·x vaut ±0 exactement ; si `s` ≠ 0,
`s'` = `s` ; si `s` = +0, `s'` = +0 par (1). Les pas sur un code non nul ont les mêmes opérandes. Par
récurrence, `s` est identique au bit à chaque pas. ∎
La réduction papillon entre voies (`somme_warp_f32`) ajoute des sommes partielles égales au bit dans
les deux calculs. Le biais est ajouté ensuite. **Conséquence** : la sortie de chaque GEMV d'expert,
donc chaque logit, est identique au bit ; l'éclaireur l'a mesuré sur la référence f64 (0 logit
différent sur 24 jetons ; `.kld` identiques octet pour octet sur 2 550 positions) et le lot A le
mesure sur le moteur (A-C1).

**La table des valeurs E2M1** est lue en un seul endroit des noyaux (`valeur_e2m1x2`,
`gemv.cuh`, ligne 33 au commit `000cef9`) ; `trc-reference` lit le GGUF et n'est pas touchée. Tout
nouveau lecteur de codes (un noyau de préremplissage par lots, une GEMM) doit lire le code 8 comme
zéro : c'est un invariant à écrire dans ARCHITECTURE § 5.6.

### 4.3 Lot A : le format `.trc` v1.2, au bit près

La v1.1 (deux niveaux de B) reste réservée telle quelle ; la v1.2 en est indépendante et s'applique à
un fichier à un niveau. Un lecteur 1.2 lit 1.0, 1.1 et 1.2.

**En-tête fixe** (ARCHITECTURE § 4.3) :

| Décalage | Taille | Champ | v1.0 | v1.2 |
|---|---|---|---|---|
| 10 | u16 | version mineure | 0 | **2** |
| 12 | u32 | drapeaux | bit 0 (aligné) ; bit 1 (niveaux) ; bit 2 (brut) | + **bit 3 CANONIQUE** : aucun flux de codes ne contient le demi-octet 8 ; l'expert décodé se compare à l'empreinte canonique du répertoire. + **bit 4 COLONNES** : au moins une matrice porte un flux CODES_COL et la section TABLES porte sa carte. Bits 3 et 4 refusés si la version mineure est < 2 ; bit 4 sans bit 3 refusé (la v1.2 ne définit pas CODES_COL sur des codes non canoniques) |
| 123 | u8 | réservé → **Q, classes de colonne** | 0 | 4 si bit 4, 0 sinon ; tout autre valeur refusée |

**Section TABLES** (§ 4.6) : un type de charge de plus.

| Type | Charge | Taille |
|---|---|---|
| 1 | 16 fréquences u16 | 32 o |
| 2 | 256 fréquences u16 | 512 o |
| 3 | 4 centres f32 | 16 o |
| **4** | **carte des colonnes** : C_j / 4 octets ; la classe q(c) ∈ {0, 1, 2, 3} de la colonne c occupe les bits 2(c mod 4) et 2(c mod 4) + 1 de l'octet ⌊c / 4⌋ | C_j / 4 o (720 o pour C = 2 880 ; multiple de 8 puisque C est multiple de 32) |

Enregistrements d'une matrice (couche ℓ, matrice j) en v1.2 :
- toujours : DELTA contexte 0 (charge 2) ;
- si la matrice est en CODES_CTX : CODES_CTX contextes 0, 1, 2 (charge 2), tables construites sur les
  codes **canoniques** (les 31 symboles octets dont un demi-octet vaut 8 ont la fréquence 0) ;
- si la matrice est en CODES_COL : CODES_COL contexte **0xFF** (charge 4, la carte), puis CODES_COL
  contextes c ∈ [0, 12) rencontrés (charge 1 ; c = 4κ + q ; le symbole 8 a la fréquence 0). Un contexte
  jamais rencontré n'a pas d'enregistrement et ne peut pas être lu par un flux juste.

**Section RÉPERTOIRE** (§ 4.7) : le champ réservé de 8 octets au décalage 56 devient
**`empreinte_canonique`** (u64) : l'empreinte64 de l'expert canonique, c'est-à-dire de la même suite
d'octets que l'expert d'origine (§ 4.11 : pour j = 0, 1, 2 les R·B blocs de 17 octets `[e, qs]`, puis
les biais), où chaque demi-octet 8 des `qs` est remplacé par 0. Vaut 0 si le bit 3 est absent.
L'empreinte d'origine (décalage 24) reste celle des octets du GGUF : la provenance ne se perd pas.

**Sortes de flux** (§ 4.10) : une de plus.

| Code | Sorte | Contenu, octets produits pour une matrice R × C | Niveau |
|---|---|---|---|
| **0x13** | **CODES_COL** | rANS, **géométrie 2**, table **par symbole** : R·B·32 symboles (P = R·B·16 octets de demi-octets) ; le symbole n est le demi-octet n des `qs` canoniques dans l'ordre β (n pair : demi-octet faible de l'octet ⌊n/2⌋) | 0 (v1.2) |

Une partie de tronçon v1.2 porte, pour chaque matrice j, **exactement un** flux de codes : CODES_CTX_j
ou CODES_COL_j (12 flux par partie, comme en v1.0).

**Le contexte d'un symbole de CODES_COL** (§ 4.9.3), pour B = C/32 blocs par ligne :
- β(n) = ⌊n / 32⌋, le bloc ; κ(β) la classe d'échelle de la v1.0 (δ < 128, = 128, > 128) ;
- u = n mod 32 ; la position du poids dans son bloc est i(u) = ⌊u / 2⌋ + 16 · (u mod 2) (l'octet t d'un
  bloc porte le poids t dans son demi-octet faible et le poids 16 + t dans le fort : disposition de
  `block_mxfp4`, ARCHITECTURE § 5.6) ;
- la colonne est col(n) = (β(n) mod B) · 32 + i(u) ; sa classe q(col) se lit dans la carte ;
- **contexte(n) = 4 · κ(β(n)) + q(col(n))**, dans [0, 12). Aucun saut.
En termes du décodeur (§ 4.9.2), la voie l du macro-pas m produit le mot w = 32m + l ; son sous-pas k
(0 à 7) produit le demi-octet n = 8w + k ; le bloc du mot est ⌊w / 4⌋ (le même pour ses 8 demi-octets,
donc un seul κ par mot, comme en CODES_CTX), et u = 8 (w mod 4) + k.

**La carte des colonnes** (normative pour le codeur seulement : le décodeur lit la carte, il ne la
recalcule pas) : pour le tenseur (couche, matrice) entier, tous experts confondus,
E(c) = Σ_{experts, lignes, blocs b de la colonne c} 4^(δ_b − 128) · K[code & 7]², K = {0, 1, 2, 3, 4, 6,
8, 12} ; t₁, t₂, t₃ les quantiles 0,25, 0,5 et 0,75 des C valeurs E(c) triées (la règle de `quantile`
de `outils/genome/predictif-elagage/taux_reel/src/main.rs`, à recopier dans la décision) ;
q(c) = #{i : t_i < E(c)}. C'est exactement la carte qui a donné 3,6844 bits [mes.].

**La règle du choix par matrice** (normative pour le codeur) : gain(ℓ, j) = Ĥ_CTX − Ĥ_COL, avec Ĥ les
bits par poids estimés par l'entropie des histogrammes du tenseur, tables comprises (CTX : 3 tables
de 512 o ; COL : la carte de C/4 o et ses tables de 32 o) ; CODES_COL si gain ≥ 0,015 bit par poids,
CODES_CTX sinon. Raison du seuil : c'est celui qu'a déclaré prédictif-élagage pour un flux de plus
(0,40 % de 3,84 bits, 03 § 3.1), et une matrice en géométrie 2 coûte deux fois plus de pas rANS par
octet décodé (§ 4.4). Sur les 12 tenseurs : 2 matrices en CODES_COL, 3,6843 bits par poids
(`apparie-eclaireur.json`, champ `colonne`) [calc. sur mes.].

### 4.4 Lot A : le décodeur sur la carte, et la LUT compacte

**Le problème** [calc. ; litt. pour la limite] : la LUT normative d'une table occupe M = 4 096 mots de
32 bits, 16 Kio. CODES_CTX en monte trois par bloc de fils (48 Kio, `decodeur.cuh`, ligne 223), la
limite de la mémoire partagée statique d'un bloc. CODES_COL a douze contextes : 12 × 16 Kio =
192 Kio, au-delà même de la mémoire partagée dynamique d'un bloc sur sm_89 (99 Kio sur option ; guide
de programmation CUDA, tableau des capacités par version ; à relever sur la carte par
`cudaDeviceGetAttribute(cudaDevAttrMaxSharedMemoryPerBlockOptin)` au premier pas du lot).

**La solution : une LUT compacte en demi-octets.** En géométrie 2, le symbole tient sur 4 bits. Pour
chaque contexte c : `sym[c]`, 4 096 symboles rangés deux par octet (2 Kio) ; `f[c][16]` et
`cum[c][16]` en u16 (64 o). Un pas de décodage devient :
```
fente ← x & 4095
s     ← (sym[c][fente >> 1] >> ((fente & 1) · 4)) & 15
y     ← f[c][s] · (x >> 12) + (fente − cum[c][s])
si y < L : x ← (y << 16) | mots[p] ; p ← p + 1      sinon : x ← y
```
Pour 12 contextes : 24 Kio + 768 o, plus la carte de la matrice (720 o) : **≈ 25,5 Kio**, sous la
limite statique, sans option.

**Lemme A2 (la LUT compacte rend la même suite).** Pour toute fente i, la LUT normative donne
(s, f[s], i − c[s]) avec s l'unique symbole tel que c[s] ≤ i < c[s] + f[s] ; la LUT compacte range
le même s en `sym[c][i]` et lit f[s] et c[s] dans les tables du même contexte. Les deux pas calculent
donc le même y et le même renouvellement : la suite des états, des mots lus et des symboles est la
même. ∎ (La LUT est une représentation de la table ; ARCHITECTURE § 4.9.2 la décrit, ce qui est
normatif est la suite des symboles décodés.)

**Le coût** [calc.] : un pas compact fait deux lectures de plus en mémoire partagée et une soustraction
de plus qu'un pas de géométrie 1 ; la géométrie 2 fait 8 pas par mot au lieu de 4. Le décodage d'une
matrice CODES_COL coûte donc environ deux fois et demie celui d'une matrice CODES_CTX. Le moteur
décode aujourd'hui un expert en 0,92 ms (O § 6.5, 54,2 ms par jeton pour 59 défauts sur le 120b).
Si deux matrices sur trois (gate et up) d'une seule couche passent en CODES_COL, un expert de cette
couche coûte ≈ 0,92 × (1 + 2 × 2,5) / 3 ≈ 1,8 ms ; à ≈ 1,6 défaut par jeton dans cette couche
(59 défauts sur 36 couches), c'est ≈ +1,5 ms sur 457 ms par jeton, 0,3 % [calc.], et le décodage se
recouvre déjà avec les lectures (O § 6.5). C'est pour cela que la règle du § 4.3 réserve CODES_COL aux
matrices qui rendent.

### 4.5 Lot A : les fichiers, dans l'ordre

| Pas | Fichier | Ce qui change |
|---|---|---|
| A0 | `decisions/ARCHITECTURE.md` § 4.3, 4.6, 4.7, 4.9.3, 4.10, 4.11, 4.12, 4.15, 5.6 | la décision v1.2, recopiée des §§ 4.2 à 4.4 de ce cahier ; l'invariant « le code 8 se lit comme zéro » |
| A1 | `moteur/crates/trc-format/src/lib.rs` ; `tests/aller_retour.rs` | `VERSION_MINEURE = 2` ; `DRAPEAU_CANONIQUE = 8`, `DRAPEAU_COLONNES = 16` ; `Sorte::CodesCol = 0x13` ; `Charge::Carte(Vec<u8>)` (type 4) ; `Entete::classes_colonne` (décalage 123) ; `EntreeRepertoire::empreinte_canonique` (décalage 56) ; les refus du § 4.3 |
| A2 | `moteur/crates/trc-codec/src/lib.rs` ; `tests/rans.rs` | `canoniser(qs)` ; `carte_colonnes(...)` (codeur) ; `coder_codes_col` et `decoder_codes_col` par `rans::coder_avec` / `decoder_avec` (géométrie 2, contexte par symbole, existants) ; `decoder_partie` choisit selon la sorte présente ; `ExpertDecode::empreinte_canonique` |
| A3 | `moteur/crates/trc-noyaux/noyaux/commun.cuh`, `decodeur.cuh` ; `src/abi.rs` ; `tests/carte.rs` ; `banc/banc_k.cu` | `SORTE_CODES_COL` ; `pas_demi_compact` ; `corps_codes_col` (même découpage de tuiles et même lecture d'avance de κ que `corps_codes`, carte en mémoire partagée) ; le noyau de matrice choisit selon la sorte trouvée dans la table des flux ; `abi::lut_demi_compacte(freq16) → (Vec<u8>, [u16; 16], [u16; 16])` et le bloc de LUT d'une couche ; banc de débit |
| A4 | `moteur/bins/trc-codeur/src/coder.rs`, `verifier.rs`, `main.rs` | une **passe 0** (comptes de toutes les couches, cartes, choix) avant la réservation de TABLES, dont la longueur dépend des choix ; options `--canonique` (défaut en v1.2) et `--seuil-colonnes 0.015` ; `verifier` contrôle les deux empreintes par deux chemins (GGUF canonisé contre décodé) |
| A5 | `moteur/crates/trc-ordo/src/lib.rs` (témoin, lignes 967 et 1318 au commit `000cef9`) ; le montage des LUT de couche | le mode témoin compare à `empreinte_canonique` quand le bit 3 est posé ; les LUT compactes et la carte montées avec les tables de la couche |
| A6 | `mesures/moteur/epreuve-J1/` (le décodeur Python indépendant) | étendu à la v1.2 **par un juge qui n'a écrit ni la décision ni le code** (SOCLE, « la barre ») |

Coût de la passe 0 [calc.] : une lecture de plus des tenseurs d'experts du GGUF, 12,1 Go (20b) et
63,4 Go (120b), soit 7 s et 34 s au débit mesuré du disque (1,848 Go/s, O § 6.5).

### 4.6 Lot A : critères de réussite, déclarés avant

| Code | Mesure | Témoin et cassure | Seuil (et sa source) |
|---|---|---|---|
| A-T1 | aller-retour du format v1.2 | un lecteur 1.1 refuse un fichier 1.2 ; bit 3 avec version 1.1 refusé ; octet 123 non nul en 1.1 refusé ; carte de taille fausse refusée | tous les refus nommés tombent ; tous les fichiers justes passent |
| A-T2 | codec processeur, CODES_COL | décodé = `qs` canoniques octet pour octet, toutes les voies finissent sur L ; cassure : une colonne de la carte changée de classe → le décodage diffère | 0 octet différent ; la cassure tombe |
| A-T3 | décodeur carte = décodeur processeur | 20 tronçons tirés (graine 20261017) de chaque modèle, octet pour octet ; cassure : deux contextes de LUT échangés | 0 octet différent ; la cassure tombe |
| A-T4 | empreintes | empreinte_canonique = empreinte64(canoniser(octets du GGUF)) pour 100 % des tronçons, par `verifier` et par le décodeur indépendant (A6) | 100 % |
| **A-C1** | **logits au bit** | troncons sur v1.2 contre troncons sur v1.0, 10 fenêtres, 20b et 120b, empreintes de logits (l'instrument de C3/C11) ; cassure : un fichier v1.2 dont un demi-octet 0 est changé en 1 | **0 logit différent** (proposition A1) ; la cassure fait différer |
| **A-C2** | **taille** | le fichier écrit, relevé sur le disque | gain sur les octets de tronçons **≥ 0,12 bit par poids d'expert** sur chacun des deux modèles (mesuré : 0,1280 et 0,1257 pour le zéro seul ; 0,12 laisse 0,0013 bit d'alignement et une marge au codeur réel) |
| **A-C3** | **vitesse** | séance ABBA, 4 séries par fichier, 120b, secteur (Win32_Battery), verrou de la carte ; bruit de référence : v1.0 contre v1.0 dans la même séance | **pas de régression** : rapport médian v1.2 / v1.0 ≥ 1 − 2 σ_bruit ; le gain n'est **annoncé** que s'il dépasse 2 σ_bruit (prédit : +3,4 %) |
| A-C4 | coût du décodeur CODES_COL | banc de `trc-noyaux` (ABBA contre CODES_CTX sur la même matrice) | débit de décodage CODES_COL ≥ 10 × le débit du disque mesuré du moteur (≥ 18,5 Go/s d'octets compressés), pour que le décodage ne devienne jamais l'étage lent |

Si A-C4 tombe, la règle du choix se resserre (CODES_COL désactivé : le zéro seul rend déjà 86 % du
gain du lot sur les 12 tenseurs mesurés, 0,1370 sur 0,1591 bit) ; A-C1 et A-C2 ne dépendent pas de la colonne.

### 4.7 Lot B : ce qu'il porte, et la mesure qui manque d'abord

**Ce qu'il porte** : le **génome synonyme** comme second fichier, `<nom>.rapide.trc`, lu à la place du
fichier exact quand le moteur sert un expert en **mode rapide**. Il n'est pas emboîté dans le fichier
exact (le complément exact derrière la base synonyme coûte 1,689 bit au lieu de 1,219 : 01 § 5.4) ; le
disque garde les deux fichiers, le moteur ne lit que l'un des deux par défaut d'expert. C'est le
« mode rapide et mode exact » de Stone (idée, § 5 quater).

**La mesure qui manque** (§ 0, point 2) : la variante qui bat la frontière en bits (λ = 1, 2,563 bits
H0) n'a pas de KL ; celle qui a une KL meilleure (λ = 0) n'est pas sous la frontière en bits. Le lot B
commence donc par **B0**, qui décide de la variante à construire. Ce n'est pas une recherche neuve :
c'est la passe de l'éclaireur (protocole P1, mêmes outils) sur la variante qu'on veut construire.

**Ce qu'il rendrait** [calc. sur mes., à confirmer par B1] :

| | gpt-oss-20b | gpt-oss-120b |
|---|---|---|
| bits par poids lus (λ = 1 ; H(symbole \| κ) + échelles à H0 + échelles) | 2,56 à 2,60 | 2,56 à 2,60 |
| fichier `<nom>.rapide.trc` (experts, biais f32 compris) | ≈ 6,14 à 6,24 Go | ≈ 36,9 à 37,4 Go |
| rapport f des octets d'un tronçon rapide à un tronçon exact v1.2 (3,6843 ou 3,7292 bits) | 0,69 à 0,71 | 0,69 à 0,70 |
| toit du débit en mode rapide, disque limitant | ×1,41 à ×1,45 | ×1,43 à ×1,46 |
| tient en RAM (16 Go, avec les résidents) ? | **oui** (6,2 + 1,9 Go) | **non** |

Le disque a 211 Go libres (relevé du 2026-10-17) : le fichier rapide du 120b y tient.

### 4.8 Lot B : le format du compagnon rapide

Un fichier `.trc` v1.2 ordinaire, avec un drapeau de plus ; tout ce qui n'est pas dit ici est le
format du § 4.3 et d'ARCHITECTURE § 4.

- **En-tête** : **bit 5 RAPIDE** des drapeaux : fichier compagnon de mode rapide, un niveau, flux de
  base synonyme. Refusé si la version mineure est < 2 ; incompatible avec les bits 2 (brut) et 4
  (colonnes). Nombre de niveaux (décalage 121) : 1. Partition des magnitudes (décalage 124) :
  `0 0 1 1 1 2 2 3` (celle de la base de B, ARCHITECTURE § 4.3), pour la provenance seulement : les
  symboles ne sont pas fonction des codes.
- **MÉTA** : les paires du GGUF ne sont pas recopiées (le fichier exact les porte) ; les paires du
  codeur, plus `troncons.rapide.exact` (u64 : l'empreinte64 de l'en-tête du fichier exact apparié ;
  le moteur refuse un compagnon dont l'empreinte ne correspond pas), `troncons.rapide.lambda` (f32),
  `troncons.rapide.amortissement` (f32, δ*), `troncons.rapide.calibration` (chaîne : corpus,
  fenêtres, nombre de positions), `troncons.rapide.variante` (chaîne : « synonyme » ou « frontière »,
  la seconde servant de témoin).
- **RÉSIDENTS** : section vide (décalage et longueur 0), permise par le bit 5 seulement : les résidents
  viennent du fichier exact.
- **TABLES**, par (couche, matrice) : DELTA contexte 0 (charge 2) ; **BASE_CTX** contextes 0, 1, 2
  (charge 2 : alphabet octet de deux demi-octets de base, table par voie κ, exactement la sorte 0x10
  réservée par la v1.1) ; **CENTRES** contexte 0 (charge 3 : c₀ … c₃ en unités E2M1 ; pour la
  variante mesurée, les centres globaux de l'éclaireur, 0,2371657, 1,4242978, 3,4185770, 6,0, la
  moitié des valeurs de `outils/genome/eclaireur/centres.json`).
- **RÉPERTOIRE** : mêmes entrées de 64 octets ; longueur du niveau 1 nulle ; `empreinte_origine` (24)
  = celle de l'expert exact (le lien de provenance) ; décalage 56 : l'empreinte64 de l'**expert rapide**
  (pour j = 0, 1, 2, les R·B blocs `[e, 16 octets de demi-octets de base]`, puis les biais).
- **Partie de tronçon** (magie TRC0, niveau 0) : MEDIANES_j, BIAIS_j, DELTA_j, BASE_CTX_j, pour
  j = 0, 1, 2 (12 flux).
- **Le demi-octet de base** : bit 3 le signe, bits 0 et 1 la classe k ∈ {0, 1, 2, 3}, bit 2 nul (un
  bit 2 posé est une erreur nommée du décodeur). Depuis le symbole de `synonyme.py` (bits 0 et 1 la
  classe, bit 2 le signe) : `n = ((sym >> 2) & 1) << 3 | (sym & 3)`.
- **La valeur servie** : ŵ = (n & 8 ? −1 : +1) · 2 c_{n & 3} · 2^(e − 128), en grandeurs doublées
  comme la GEMV MXFP4 (ARCHITECTURE § 5.6 : « en mode base, k est remplacé par les deux fois les
  centres »). Le signe d'une classe 0 est un vrai choix du codeur (il reconstruit ±0,237 s) : il est
  stocké, il n'est pas haché.

### 4.9 Lot B : le codeur, et ce qu'il calcule exactement

Le codeur rapide reprend **mot pour mot** l'algorithme mesuré (`outils/genome/eclaireur/synonyme.py`,
fonctions `hessienne`, `facteur_inverse`, `choisir`, `symboles_variante`) ; toute différence est une
autre variante et demande sa propre mesure. Pour chaque expert et chaque matrice :

1. **Les entrées** : pour gate et up, les états normés h des positions de calibration routées vers
   l'expert, avec leur poids de routeur g ; pour down, x = SwiGLU-oai(W_gate h + b_gate, W_up h + b_up)
   avec les poids **exacts** (comme mesuré ; la passe séquentielle de 01 § 8.4 est une autre variante).
2. **H** = Σ g² x xᵀ / Σ g², puis H_δ = H + δ* · moyenne(diag H) · I, **δ* = 1** (choisi par validation
   croisée sur la calibration seule, 01 § 5.4).
3. **U**, facteur triangulaire supérieur de H_δ⁻¹ (Uᵀ U = H_δ⁻¹), par une seule factorisation :
   P H_δ P = L Lᵀ (P renverse l'ordre), U = P L⁻¹ P.
4. **Les longueurs** ℓ(s) = −log₂ p(s), p la loi des 8 symboles de la base frontière du tenseur entier
   (32 experts) ; **la normalisation** c̄ = tr(ΔW H ΔWᵀ) / (R C) pour la base frontière de la matrice.
5. **Le choix**, colonne j = 1 … C, par blocs de 32 colonnes : pour le poids courant w (après
   rétroaction), le signe suit w (bit de signe ; −0 compte pour négatif), et la classe k minimise
   (|w| − c_k s_b)² + λ c̄ U_jj² ℓ(±, k), **λ = 1** (ou 0, selon B0) ; l'erreur
   ε = ±(|w| − c_k s_b) / U_jj est reportée sur les colonnes suivantes : w_F ← w_F − ε U_{j,F}.
6. **Le codage** : les demi-octets de base en BASE_CTX (rANS, table par voie κ), tables par tenseur
   comptées sur les 32 experts (passe de comptes, comme `trc-codeur`).

**Témoins du codeur** (ceux de l'éclaireur, repris) : T1, H = I et λ = 0 rendent exactement les
symboles de la frontière (0 différent ; avec le H réel, plus de 0) ; le facteur U par renversement
égale le facteur direct à 10⁻¹² près ; la variante « frontière » écrite par le même codeur redonne
la base de F1 (erreur relative 0,042919745 sur les 12 tenseurs).

**Coût du codage** [mes. ; calc. pour les totaux] : la passe λ = 1 a pris 7 040 s pour 16 experts
(48 matrices, `synonyme-lam1-damp1-e0_8_16_24.json`), mesures de sortie comprises et sous la charge
des autres équipes, soit ≈ 147 s par matrice ; l'éclaireur estime la seule rétroaction à ≈ 10 s par
matrice (01 § 8.7). Le 20b entier (2 304 matrices) demande donc de 6,4 à 94 h en Python, le 120b
(13 824 matrices) de 38 à 565 h. Le cœur
est un produit O(C² R) par matrice (2,4·10¹⁰ opérations en f64) : sur la RTX 4060 en f32 par cuBLAS,
de l'ordre de la dizaine de millisecondes [calc., ordre de grandeur]. **Le codeur de production se
réécrit donc en Rust avec la factorisation et les mises à jour de rang 32 sur la carte** (B1c), et le
codeur Python reste le second chemin sur un échantillon.

### 4.10 Lot B : les pas, les fichiers et les critères, déclarés avant

| Pas | Ce qui se fait | Fichiers | Critère déclaré |
|---|---|---|---|
| **B0** | KL de la variante λ = 1 (et de la frontière canonique à signe haché, `frontiere0`, jamais jugée en KL), protocole P1 (32 experts, 10 fenêtres, mêmes captures) ; comparaison **appariée** à la base frontière | `outils/genome/eclaireur/synonyme.py ecrire-sym` (existant), `outils/genome/eclaireur/capture kl` (existant), `juge comparer` ; journaux sous `mesures/genome/construction/rapide/` | λ = 1 est retenue seule si d̄ + 2 σ_fenêtres < 0 contre la frontière (meilleure significativement) ; si elle n'est qu'égale (|d̄| ≤ 2σ), elle domine encore la frontière (0,078 bit de moins, même KL) mais λ = 0 reste meilleure en KL : les deux sont construites comme deux points du mode rapide et B2 les départage ; si elle est pire (d̄ > 2σ), λ = 0 est retenue ; `frontiere0` devient la base de comparaison si elle égale la frontière (|d̄| ≤ 2σ) |
| **B1** | format du compagnon (§ 4.8) ; empaqueteur 20b depuis les symboles écrits par `ecrire-sym` | `trc-format` (bit 5, MÉTA, RÉSIDENTS vides) ; `trc-codec` (BASE_CTX, CENTRES) ; `trc-codeur rapide --symboles <dossier>` | symboles décodés = symboles écrits, octet pour octet, 100 % des matrices ; débit réel par poids relevé ; cassure : un symbole changé → l'empreinte de l'expert rapide tombe |
| B1c | codeur Rust + carte (§ 4.9) | `trc-codeur rapide --calibrer` | symboles égaux à ceux du Python sur 8 matrices tirées (graine 20261017), ou différences toutes expliquées par l'arrondi (erreur de sortie égale à 10⁻⁶ relatif) |
| **B2** | KL du modèle 20b **entier** en mode rapide (768 experts), 10 fenêtres, contre la référence f64 ; contre la frontière entière écrite par le même empaqueteur ; repère : la meilleure requantification de llama.cpp du même GGUF à bits d'experts égaux ou inférieurs (`llama-quantize --allow-requantize`, outil déjà sur la machine) | `trc-noyaux` : `gemv_base` (valeur par table de 16, même ordre d'opérations que `gemv_mxfp4`) ; `trc-ordo` : `--mode rapide` | (i) **meilleure que la frontière entière** : d̄ + 2 σ_fenêtres < 0 ; (ii) **au niveau de l'outil de référence** : KL ≤ celle de la meilleure requantification llama.cpp à bits égaux ou inférieurs (réponse par délégation ci-dessous) ; (iii) témoin de `gemv_base` : écart relatif ≤ 10⁻⁵ à la référence f64 aux poids substitués |
| **B3** | le mode rapide dans le moteur, et la politique des défauts | `trc-cache` (`Niveau::Base`) ; `trc-ordo` | **avant de construire la politique mixte** : `rejouer` sur les traces du lot O avec un coût à deux niveaux (probatoire en rapide, promu en exact) ; la politique se construit si elle lit ≤ 0,85 × les octets du mode exact avec une part d'appels servis en rapide φ ≤ 0,5 ; vitesse du mode rapide pur : ABBA contre le mode exact, prédit ×1,41 à ×1,45 à disque limitant |
| B4 | 120b : captures de calibration (aucune n'existe pour le 120b) et fichier rapide (≈ 37 Go) | `trc-reference` ou le moteur avec un crochet de capture ; `trc-codeur rapide --calibrer` | B2 (i) refait sur le 120b ; KL du mode rapide publiée avec son premier choix et sa perplexité |
| B5 | le brouillon spéculatif (§ 4.11) | — tant que la condition du lemme B2 n'est pas tenue | **ne se construit pas** avant la mesure de ρ (traces) et de α (accord glouton rapide / exact) ; se construit si α > 1 − ρ + b_d / b_e avec une marge de 2σ |

*Réponse par délégation du 2026-10-17, réversible* : le repère du critère B2 (ii) est la meilleure
requantification que llama.cpp produit du même fichier à débit d'experts égal ou inférieur, parce que
c'est l'outil de référence que Stone utiliserait sans troncons (gratuit, déjà sur la machine) et que
« au top du top » se juge contre l'état de l'art réellement disponible, pas contre notre propre base.

### 4.11 Lot B : les deux usages, chiffrés

**(1) Les défauts de cache.** Une politique « tout défaut en rapide » converge vers le mode rapide pur :
une copie rapide reste en cache aussi longtemps qu'une copie exacte, et tous les experts finissent par
avoir été chargés en rapide. La forme qui garde un sens est **à deux niveaux** : un expert froid
(segment probatoire d'une SLRU, déjà prévue par `trc-cache`) est servi en rapide ; promu (réutilisé),
il est relu en exact. Octets par jeton : défauts probatoires × f + promotions × 1, au lieu de
défauts × 1 ; qualité : la KL avec la part φ des appels servis en rapide. Les deux premiers se
simulent sur les traces existantes par `rejouer` (le même code que le cache réel, O § 5.7) avant toute
construction ; la KL se mesure ensuite au φ simulé. Sur le 120b, le relevé du moteur est de 59 défauts
pour 144 appels par jeton (O § 6.5) : φ ≤ 59/144 = 41 % au plus fort de la politique [calc.].

**(2) Le brouillon spéculatif.** La vérification de k + 1 positions par le modèle exact rend le texte
exact au bit ; le brouillon ne fait que proposer.

**Lemme B2 (le brouillon doit être résident).** En régime limité par le disque, soit b_e les octets
d'experts exacts lus par jeton servi simplement, b_d les octets que le brouillon lit sur le disque par
jeton proposé, α le taux d'acceptation, et U(2) = 2 − ρ le rapport des octets exacts lus par une passe
de vérification de deux positions à ceux d'une seule (ρ ∈ [0, 1] : la part des défauts de la seconde
position déjà payée par la première). Avec un jeton proposé (k = 1), le décodage spéculatif lit moins
d'octets par jeton rendu que le décodage simple **si et seulement si α > 1 − ρ + b_d / b_e**.

*Démonstration.* Un cycle lit b_d + (2 − ρ) b_e et rend en moyenne E(α, 1) = 1 + α jetons
(fondations/05 § 2.2). Il gagne si b_d + (2 − ρ) b_e < (1 + α) b_e, soit α > 1 − ρ + b_d / b_e. ∎

*Corollaires* [calc.]. (i) Comme α ≤ 1, il faut ρ > b_d / b_e : **un brouillon lu du disque doit
être payé par la réutilisation des experts entre positions voisines**. (ii) Brouillon lu au défaut
depuis `<nom>.rapide.trc` : b_d / b_e ≈ f ≈ 0,7 (mêmes défauts, tronçons 0,7 fois plus petits) ; il
faut ρ > 0,7 + (1 − α) : avec α = 0,9, ρ > 0,8. Avec un routage indépendant, l'union des experts de
deux jetons du 120b pèse 2 − t/E = 2 − 4/128 = 1,969 fois celle d'un seul (fondations/05 § 6.2) :
ρ ≈ 0,03, et la condition est loin. Le ρ réel, au cache du moteur, n'est pas mesuré.
(iii) **Brouillon résident en RAM** (b_d = 0) : la condition devient
α > 1 − ρ, celle de Stone (idée, § 5 quater). Sur le 120b, le fichier rapide (≈ 37 Go) ne tient pas
dans 16 Go ; sur le 20b il tient (6,2 Go). Le seul brouillon résident d'un 120b sur cette machine
serait donc **un autre modèle** : le 20b en mode rapide (même vocabulaire o200k), dont l'accord α avec
le 120b n'est pas mesuré. (iv) Le lemme compte des octets. Le temps a un second terme : le moteur ne
tire du disque que 1,55 Go/s utiles sur 1,848 parce qu'il a moins de quatre lectures en vol par couche
(O § 6.5) ; vérifier deux positions double la file. Ce gain est borné par 1,848 / 1,55 = ×1,19 et
ne dépend pas du brouillon [calc. sur mes.] ; le préchargement (J1+) le vise aussi.

**Ce qu'il faut mesurer avant B5** : ρ sur les traces de routage (union des défauts de deux positions
consécutives, au cache du moteur, par `rejouer`) ; α, accord glouton entre le mode rapide du 20b et le
mode exact du 20b, puis entre le 20b rapide et le 120b exact (fondations/05 a mesuré 76,8 % pour
Qwen3.5-4B → 9B et 82,1 % pour une copie à 3,60 bits du même modèle) [litt. interne, mes.].

### 4.12 Ce que les deux lots ne font pas

- Ils ne touchent pas à la référence f64, au juge, ni aux noyaux d'attention.
- Le lot A ne change aucun logit (A-C1) ; le lot B ne change pas le mode exact : un utilisateur qui ne
  demande pas le mode rapide lit le même texte qu'avant.
- Le contexte de colonne n'est pas porté dans le fichier rapide (incompatible par le § 4.8 : la base
  synonyme n'est pas une fonction des codes, et son gain de colonne n'est pas mesuré).
- La garde tropicale (§ 3.1) n'est dans aucun lot : sa mesure sur les journaux de routage vient
  d'abord, et décide.

---

## 5. Ce qui pourrait être faux

- **Trois protocoles, un seul axe.** Les rapports de KL rapprochent des passes qui n'ont ni les mêmes
  experts remplacés, ni les mêmes fenêtres, ni le même nombre de positions (765 à 2 550). Un rapport
  n'est pas invariant au nombre d'experts remplacés (la KL croît avec lui, et pas linéairement, à cause
  des bascules) ; la figure les montre côte à côte, elle ne les fond pas en une courbe.
- **Les débits n'ont pas tous le même estimateur** (codec réel, H0 sans échelles, comptabilité du
  brin). À l'intérieur d'un protocole, base et mécanisme partagent le leur ; entre protocoles, un écart
  de 0,04 bit peut venir de l'estimateur seul.
- **La différence appariée de l'éclaireur** est calculée ici depuis ses CSV ; l'incertitude par blocs
  de fenêtres repose sur 10 blocs (9 degrés de liberté), et les positions d'une fenêtre ne sont pas
  indépendantes. Le verdict (2,9 σ) tient par les deux estimateurs ; une autre découpe (par 256
  positions, par exemple) pourrait l'élargir.
- **La lecture « part lisse et queue de bascules »** (§ 2.2) est une hypothèse de travail. Elle
  s'appuie sur des mesures directes entre deux moteurs exacts (88 % de la KL retirée par le routage
  imposé ; 96,5 % portés par les positions qui basculent) et sur les quantiles de la ronde ; elle n'a
  pas été mesurée **pour les mécanismes de la ronde** par le routage imposé. La mesure qui la jugerait :
  la passe KL de S\* et de la base avec les experts imposés depuis la référence.
- **La passe K10** (S\* égal à la base sur 10 fenêtres) vient d'un fichier que l'équipe genome n'avait
  pas commité quand ce document a été écrit ; ses chiffres sont recopiés ici à la main depuis
  `comparer10-base-contre-recette.json`, et `frontiere.py --k10` les tirera une fois le journal commité.
- **L'explication de ce que S\* ne gagne pas** (§ 2.4, pondération diagonale dans le domaine tourné) est une
  hypothèse ; aucune passe ne la départage.
- **Le contexte de colonne** n'est mesuré que sur 12 tenseurs du 20b (4 couches) ; sur le 120b et sur
  les autres couches, son gain peut être plus grand ou nul. La règle des 0,015 bit le décide matrice
  par matrice, au codage.
- **La proposition A1** couvre le noyau `gemv_mxfp4` tel qu'il est au commit `000cef9` ; tout noyau
  futur qui lirait les codes autrement (une table où −0 ne vaut pas +0 à l'accumulation, une GEMM par
  cuBLAS sur des poids déquantifiés en f16 avec un premier terme −0) doit être revu : c'est l'invariant
  à écrire (§ 4.2).
- **La limite de mémoire partagée** (99 Kio par bloc sur option, 48 Kio en statique) est lue dans la
  documentation de NVIDIA, pas encore relevée sur la carte ; la LUT compacte tient sous 48 Kio, ce qui
  rend le lot indépendant de ce chiffre.
- **Le lot B repose sur une variante dont la KL n'est pas mesurée** (λ = 1) ; B0 peut la faire tomber.
  La variante de repli (λ = 0) est mesurée meilleure en KL à bits égaux à 0,011 près, sur 32 experts
  sur 768 : sur les 768 (B2), l'avantage peut fondre si les bascules dominent.
- **Le lemme B2** suppose α indépendant de la position et ρ constant ; il compte des octets et pas le
  temps (corollaire iv) ; ses chiffres de ρ sont ceux d'un routage indépendant, pas mesurés au cache.
- **Les coûts de codage** du lot B sont une fourchette d'un facteur 15 (10 à 147 s par matrice) ;
  le codeur sur la carte est un ordre de grandeur, pas une mesure.
- **Les mesures de la ronde sont toutes sur wiki.test** (calibration et évaluation sur des fenêtres
  disjointes du même corpus) ; sur du code ou du dialogue, le gain de la mutation synonyme peut baisser
  (01, ce qui pourrait être faux).

## 6. Recettes (pour RECETTES.md)

- **Apparier avant de comparer** : la passe KL de l'éclaireur, non appariée, donnait « 3,6 fois
  l'incertitude » ; appariée par blocs de fenêtres, 2,9 σ, et 2 060 positions sur 2 550 : la
  conclusion tient, et son incertitude est maintenant celle qu'il faut. Marche, et coûte deux secondes.
- **Comparer des KL de protocoles différents par leur rapport à la base du même protocole** : marche ;
  comparer des KL absolues d'un protocole à l'autre : faux (la base va de 0,023 à 0,064 selon le
  nombre d'experts remplacés).
- **Lire les quantiles de la KL, pas seulement sa moyenne** : la médiane dit la part lisse, le 99e
  centile et le maximum disent les bascules ; c'est ce qui a expliqué S\*.
- **Une règle de choix par matrice plutôt qu'un contexte partout** : le contexte de colonne rend 0,142
  bit sur une matrice et 0,0006 de perte sur une autre ; avec un seuil de 0,015, 2 matrices sur 12
  prennent 92 % du gain de la colonne (0,0221 bit sur 0,0239 ; 3,6843 contre 3,6825 en prenant
  toutes les matrices qui gagnent, pour un décodeur deux fois et demie plus cher sur 4 matrices de plus).
- **Une LUT en demi-octets pour un alphabet de 16 symboles à beaucoup de contextes** : 12 contextes
  en 25,5 Kio au lieu de 192 Kio, même suite de symboles (lemme A2). Non construite.
- **Écrire la preuve d'exactitude sur le noyau réel, pas sur le produit scalaire abstrait** : la
  proposition de 01 laissait un cas (le signe d'une somme nulle) que le départ à +0 du noyau règle.
- **Vérifier à quelle variante appartient un chiffre avant de le reprendre** : la consigne prêtait
  à λ = 1 la KL de λ = 0 ; le journal (`kl-synonyme-d1-*.json`, « d1 » = δ* = 1, λ = 0) le dit.
- **Python isolé (`-I`) ignore PYTHONIOENCODING** : sous Windows, la sortie retombe en cp1252 ;
  `sys.stdout.reconfigure(encoding="utf-8")` dans le script règle le cas.
- **Un heredoc bash qui contient des apostrophes et des barres** a échoué dans l'outil ; écrire le
  texte dans un fichier puis l'ajouter par Python : marche.
