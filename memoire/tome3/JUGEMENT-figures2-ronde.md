# Jugement : figures du Tome III, lot « ronde », second flux (après corrections)

Juge indépendant des chiffres, 2026-10-27. Je n'ai rien tracé ni corrigé dans ce lot. Jugé : le commit `6292203`
(seul commit du second flux sur les fichiers du lot : les quatre `*-figures.tex`, les quatre `tome3_*.py`, les
données `eclaireur-*`, `genome-*`, `duplication-*`, `synthese-*`, la note `REPRISE-figures2-ronde.md`), contre
SOCLE (« la beauté à égalité avec la justesse »), l'inventaire (réserves R1 à R6), le jugement du premier flux de ce
lot (`JUGEMENT-figures-ronde.md`, G1, M1 à M13, D1 à D10) et celui du juge de design pour ce lot (G5, G8, G9, G10,
D1 à D9, D23 à D31). Le commun (`palette-tome3.tex`, `legende-tome3.tex`) n'est jugé que par ce que le lot en fait.
Aucune passe du modèle, aucune carte graphique. Outils et journaux : `outils/genome/tome3/juge2-ronde/` (commit
`37db22b`). Étiquettes : [mes.] mesuré ici par un outil commité, [lu] lu dans une source commitée.

## 0. Verdict

**Le lot tient.** Les quatre graves du premier flux qui le concernaient sont levés : G1 du juge ronde (III-7.1 classée
par sa propre règle), et G10, G5, G8 du juge de design (III-7.1 réduite à la frontière, III-7.4 étiquetée
directement, III-4.8 dessinée en arbre). La part du lot dans G9 est faite : onze titres courts dans la table des
figures, une tête, une provenance, une ligne « Données » par figure. **Aucun grave neuf.** Aucune figure ne tombe.

- **Les chiffres sont justes.** 69 nombres neufs ou déplacés, refaits par un autre chemin depuis les fichiers commités
  sous `mesures/` : 65 égaux à 2·10⁻⁵ relatif près, 4 égaux à la précision imprimée, aucun écart (§ 1). Les classes
  de III-7.1 et III-7.2, refaites par la règle depuis les journaux du juge (`juge comparer`) et depuis les 2 550
  positions de P1 : aucun désaccord avec le lot.
- **Les 54 fichiers de données du lot se régénèrent au bit** par ses scripts, deux fois, dans une copie tirée par
  `git archive` ; aucun fichier en trop ni en moins, aucun CRLF.
- **Les séries neuves** (dessin radial, deux queues, colonne « queue », classes et origine) sont retrouvées point par
  point à la source ; le dessin radial, refait par mon code d'après la phrase de la légende, donne les mêmes
  positions à 5·10⁻⁵ près, et **aucune arête n'en croise une autre** (0 croisement sur 31 arêtes).
- **Les deux langues** compilent (lualatex de MiKTeX, deux passes chacune) : 14 pages, 0 erreur, 0 boîte trop
  pleine, 0 avertissement LaTeX ; les nombres des pages françaises et anglaises sont les mêmes un à un ; aucune
  espace française devant « : » ou « ; » dans l'anglais. Pages lues une à une, détails agrandis de 220 à 500 dpi.
- **Aucune phrase barrée ne revient** dans une légende (102 passages barrés relevés sous `genome/` et
  `memoire/tome3/`).

**5 mineurs neufs**, aucun ne change une conclusion (§ 4) :

| N° | Figure | Genre | En une ligne |
|---|---|---|---|
| N1 | III-7.1 | dessin | le trait qui relie la loupe à l'encart traverse l'étiquette « partitions κ, par tenseur » (FR et EN) : le point de G1 se lit barré |
| N2 | III-7.4 | justesse | la colonne 960 reçoit ×310 l'erreur du brin, presque autant que la géante, sans être nommée ; « les bords des morceaux ×7,6 » est cette seule colonne (les 44 autres : ×0,70) |
| N3 | III-7.2 | justesse | « appuyée par le routage imposé (figure suivante) » : la figure suivante dit qu'elle ne refait pas ce routage (Tome II, lot R) |
| N4 | III-4.8 | dessin | quatre valeurs de lien sont posées sur une arête (0,043 coupe 22–0, 0,024 coupe 17–18, 0,023 couvre l'arête courte 14–16, 0,035 le départ de 22–29) |
| N5 | (lot construction) | justesse | la correction de `construction-codon-pour-le-memoire.md` § 3 écrit « A lu au motif de B ×1,389 » sans dire que ce croisement est mesuré sur le 20b (A20, B20), dans un paragraphe sur le J1 du 120b |

N2 n'est pas né du second flux (données et phrase inchangées depuis le premier, et la source `genome/genome.md` le dit
ainsi) ; le dessin de G5 rend seulement visible, sans nom, une seconde pointe aussi haute que celle qu'il nomme.

| N° | Figure | Verdict | Pourquoi, en une ligne |
|---|---|---|---|
| III-1.1 | Le bloc MXFP4 | **tient** | D31 : valeurs OCP dessus, table doublée de llama.cpp dessous, vérifiées code par code ; D1, D2 réglés |
| III-1.2 | La borne distorsion-débit | **tient** | M12 : 0,0375, 2,6415, 16 et 0,473 refaits (H₀ par les 12 tenseurs, corde par l'enveloppe convexe des 40 itérés) |
| III-2.1 | Le signe des zéros | **tient** | aucun nombre neuf ; la borne à 9 décimales du premier juge est restée |
| III-3.4 | Le brin sur une gaussienne | **tient** | M1 : 64 rangées à l = 12, 32 à l = 16 sauf (2, 1) sur 64, refaits ; D9 réglé |
| III-3.6 | Débit-distorsion par tenseur | **tient** | M2 : experts 0, 8, 16, 24 ; 2 880 rangées = 4 × 2 880 / 4 ; 5 formes |
| III-4.2 | Le score de parenté | **tient** | M3 : témoin de la couche 23 (moyenne de ses 8 paires) tracé sur sa couche ; ×27,26 ; plancher de la couche 0 refait |
| III-4.8 | L'arbre des experts | **tient** (G8 levé) | arbre refait par Kruskal, moyeu par le poids, dessin refait, 0 croisement ; N4 |
| III-7.1 | La frontière commune | **tient** (G1, G10 levés) | classes refaites par la règle, un seul point sous sa base ; N1 |
| III-7.2 | Erreur d'expert contre KL | **tient** | mêmes classes que III-7.1, S* à 3 fenêtres barré ; N3 |
| III-7.3 | Deux parts de la KL | **tient** | queues refaites : 25 positions, 10 communes, 9 fenêtres, au plus 7 ; −6,9·10⁻⁶ seule négative |
| III-7.4 | La colonne géante | **tient** (G5 levé), réserve | ×334, ×14, ×1,05 contre le pic, sans cadre ; N2 |

## 1. Ce que j'ai fait

Règle déclarée avant chaque comparaison : égalité à 2·10⁻⁵ relatif (2·10⁻⁹ absolu près de zéro) ; sinon, rejugée à
la précision où le `.tex` imprime le nombre (formats relevés par `cles.py`). Chaque outil a son témoin, et il tombe.

1. **L'inventaire de ce qui a changé** (`cles.py`, `journaux/cles.csv`). Les quatre `*-nombres.csv` et les quatre
   `*-figures.tex` du parent de `6292203` contre HEAD, macros à paramètres développées sur chacun de leurs appels
   (`\SynthPromesse{p3-kappa}` donne `p3-kappa-bits` et `p3-kappa-rapport`, `\GenPanneau{0}{gate}` donne
   `v-0-gate-*`, etc.) : **62 clés neuves, 1 valeur changée** (`s-sur-hasard`, 27,1584 → 27,2632 : le rapport se
   prend désormais contre le témoin de la couche 23), **4 clés imprimées pour la première fois** (`d1`,
   `p3-kappat-rapport`, `p3-partse-rapport`, `p3-elag-rapport`), **2 formats neufs** (`ecart-bits`,
   `p1-syn-rapport`), **3 coordonnées neuves** ; 196 clés inchangées, déjà refaites par le premier juge.
2. **Chaque nombre neuf ou déplacé, par un autre chemin** (`refaire2.py`, écrit sans lire `memoire/outils/tome3_*.py` ;
   `journaux/refaire2.csv`). Ce qui est vraiment refait, et non relu au même endroit :
   - H₀ de la base de λ = 1 : moyenne des 12 tenseurs pondérée par leurs poids (2,6415039832, égale au total écrit) ;
     le nombre d'experts : Σ poids / (3 rôles × 2 880²) = 16 ; la corde à l'erreur de la frontière : enveloppe
     convexe inférieure des 40 itérés de `borne-rd.json` (2,16831), d'où 2,6415 − 2,1683 = 0,473 ;
   - les rangées de la gaussienne : les 21 lignes de `gauss-balayage.jsonl`, groupées par fenêtre et par forme ;
     les 2 880 rangées de l'échantillon W : recoupées par 4 experts × 2 880 rangées / 4 ;
   - le témoin de la couche 23 : la moyenne de ses 8 paires (0,0015590), pas le champ `hasard_moyen` ; le plus
     haut score (enfant 0, parent 22) retrouvé aussi parmi les 496 paires de `arbre-c23.json` ;
   - l'arbre : mon Kruskal sur les 496 paires redonne les 31 arêtes du journal et du CSV ; degrés, poids des
     experts en pleine précision (moyeu 31 : 0,33482 ; 22 : 0,11603), les 4 arêtes les plus lourdes au moyeu ;
   - P1 : d̄ et σ refaits depuis les 2 550 positions (d̄ = −0,00984537 ; σ naïf 0,00190, σ par fenêtres 0,00334 ;
     la source retient le plus grand) ; les rapports de P3 depuis les journaux `juge kl` (`kl-12-*-f5-9.json`) ;
   - les queues, la part des 25 plus grandes, les KL négatives : depuis les positions.

   Relus au même endroit (je vérifie la recopie, pas la mesure) : `echelles-bits` (lus − H₀, la même différence
   dans la passe λ = 1), d̄ et σ de P3 (`comparer-base-*-f5-9.json`), D1 sans perte (la formule de `frontiere.py`
   sur `taux-reel-colonne-12-gptoss20b.json` et `verdicts.json` : 3,84421).
   **Résultat : 69 clés, 65 égales au seuil strict, 4 égales à l'impression** : `a-second-poids` (0,11602 contre
   0,11603 : le lot somme des scores arrondis à 5 décimales), et les trois rapports de P3 (×1,10308 contre
   ×1,10315 : le lot lit `resume-12.csv`, je lis les journaux `juge kl` ; imprimés ×1,103, ×4,85, ×4,26 des deux
   côtés). **Aucun écart.** Les six clés de l'inventaire hors de ces 69 se vérifient par elles :
   `ecart-bits` = 2,64411 − 2,16831 ; trois coordonnées lues dans `frontiere.csv` ; `regle-desaccords` = 1 et
   `points-sans-apparie` = 2 par le point 3. Témoin `--casser` (chaque valeur ×1,001, σ de κ tenseur par tenseur
   divisé par 2) : 66 clés sur 69 tombent (les 3 autres valent 0), et la classe de κ tombe.
3. **Les classes, par la règle** (`journaux/classes2.csv`) :

   | point | d̄ | σ | z | classe du juge | III-7.1 | III-7.2 |
   |---|---|---|---|---|---|---|
   | synonyme λ = 0 (P1) | −0,00985 | 0,00334 | −2,95 | meilleur | meilleur | meilleur |
   | S\* à 10 fenêtres (P2-10) | +0,00036 | 0,00186 | +0,20 | égal | égal | égal |
   | κ tenseur par tenseur (P3) | +0,00656 | 0,00531 | +1,24 | **égal** | égal | — |
   | κ, erreur moyenne (P3) | +0,01673 | 0,00490 | +3,41 | tombe | tombe | tombe |
   | hebbien (δ, ℓ, c) | +0,02729 | 0,00395 | +6,91 | tombe | tombe | — |
   | hebbien par e | +0,13102 | 0,00720 | +18,2 | tombe | tombe | tombe |
   | hebbien (e, ℓ, c) | +0,12806 | 0,00670 | +19,1 | tombe | tombe | tombe |
   | partitions par e | — | — | rapport ×4,85 | tombe (source) | tombe | tombe |
   | élagage (e, q) | — | — | rapport ×4,26 | tombe (source) | tombe | — |

   La colonne `origine` de `synthese-frontiere-kl.csv` vaut « regle » exactement pour les sept points qui ont une
   différence appariée. `frontiere.csv` n'a pas été réécrit (régénéré au bit, point 4).
4. **La régénération au bit** (`regenerer2.py`, `journaux/regenerer2.csv`). `git -c core.autocrlf=false archive`
   des quatre scripts et des mesures qu'ils lisent, dans un dossier temporaire hors du dépôt ; chaque script y est
   lancé ; l'empreinte git de chaque fichier écrit est comparée au blob commité. **54 fichiers sur 54 égaux, deux
   passes, aucun fichier écrit et non commité, aucun commité et non écrit, aucun CRLF**, aucun fichier du dépôt
   touché. Témoin : un octet ajouté à une copie par lot, 4 sur 4 tombent.
5. **Un point par série neuve, puis chaque ligne** (`series2.py`, graine 20261027, la série k tire avec 20261027 + k ;
   `journaux/series2.txt`). Dessin radial : 32 experts (positions, profondeurs, degrés, moyeu), 31 arêtes (sens
   parent → enfant, score à 5 décimales contre la pleine précision, s/s_max) ; les deux queues (25 lignes chacune,
   égales aux 25 plus grandes positions de chacun) ; la colonne `queue` (2 550 lignes) ; les classes et l'origine
   des 12 points de III-7.1 et des 7 de III-7.2. Témoin : une position déplacée de 0,01, une ligne de queue retirée,
   une classe changée : les trois contrôles concernés tombent.
6. **Les deux langues** (`memoire/essai/juge2-ronde/`, dossier ignoré par git ; même pilote que le lot, anglais par
   `-jobname=…-en "\def\ANGLAIS{1}\input{…}"`) : `journaux/compilation.txt`. `langues.py` compare les nombres des
   deux PDF page par page (765 nombres en français) : les seules différences sont des artefacts d'extraction
   (l'ensemble {0,1,2,…} et les formes (1,1) lus comme décimaux en français, un nom de fichier coupé autrement).
   Pages lues à 100 dpi, puis détails agrandis : III-7.1 (plan, encart, bande, à 220-500 dpi), III-4.8 (centre,
   encart, branche de droite, 300-400 dpi), III-7.4 (panneau b, 260 dpi), dans les deux langues pour III-7.1.
7. **Les phrases barrées** (`barrees.py`, `journaux/barrees.txt`). 102 passages barrés sous `genome/` (hors
   `genome/pistes/`) et `memoire/tome3/` ; leurs nombres distinctifs cherchés dans le texte du PDF français :
   21 rencontres, toutes relues à la main, aucune ne fait revivre une phrase barrée (« 120 » de 120b, « 768 »
   experts dans un autre protocole, « +1,24 σ » de κ contre « 1,24 Go/s », le 99,9ᵉ centile qui **monte** avec λ = 0
   en P1, ce qui va dans le sens des barres de 07 et de JUGEMENT-construction). Témoin : un passage barré fabriqué
   (« 0,476 ») est trouvé.

## 2. Les graves du premier flux : levés

**G1 du juge ronde (III-7.1) : levé.** `classe_regle` de `tome3_synthese.py` applique la règle que la légende énonce
(meilleur si d̄ + 2σ < 0, pire si d̄ − 2σ > 0, égal sinon ; sans appariée, le verdict de la source), et s'arrête si
un autre désaccord que κ tenseur par tenseur apparaît. Ma règle, sur mes d̄ et σ, rend les mêmes classes partout
(§ 1.3). La tête dit « un seul mécanisme de la ronde passe sous sa base : la mutation synonyme λ = 0 » : c'est le
seul rapport sous 1 (0,7266) et le seul « meilleur ». La légende dit que la colonne `verdict` de la source appelle κ
« gagnantes » et que la figure suit la règle : c'est la lecture que je proposais. Le triangle de κ est demi-plein
(Encre à 30 %), au-dessus de la ligne 1 : D4 du premier flux est réglé. Robustesse : d̄ de κ est positif, il ne
peut être « meilleur » sous aucune convention de σ ; il ne passerait « pire » que si σ valait moins de 0,00328,
soit 1,6 fois moins que celui de `juge comparer`.

**G10 du juge de design (III-7.1) : levé.** La figure ne porte plus que la frontière ; la forme dit le protocole, le
remplissage le verdict, la couleur la variante ; la clé tient en une ligne de six entrées. L'encart sépare S\*
(×1,018), la base de P1 et les bases de P2-10 et P3, qui se cachaient l'une sous l'autre. La bande sans KL est sous
l'axe, ses étiquettes ont un trait de rappel et aucune n'est traversée (D1 du premier flux réglé ; la barre grise
de la base de λ = 1 traverse le losange creux de D2b, à 0,0014 bit de distance, ce qui est la vérité). L'axe sans
perte est bien parti en III-8.5 (c) (`codon-figures.tex`, lignes 353 à 407), et la légende y renvoie avec ses quatre
nombres, dont D1 = 3,8442 (M8).

**G5 du juge de design (III-7.4) : levé.** Plus de cadre de légende ; « brin ×334 », « base ×14 » et « S\* ×1,05 »
sont contre le pic, chacun dans sa couleur, lisibles en anglais comme en français ; S\* est violet ; les traits de
la clé de droite font 1,2 pt. Les étiquettes « directes » sont une colonne de clé à droite du cadre, à hauteur fixe
(120, 20, 3,4), pas au bout des courbes : c'est lisible, et c'est au juge de design d'en dire plus.

**G8 du juge de design (III-4.8) : levé.** L'arbre est dessiné par sa structure : moyeu 31 au centre, cercles de
profondeur 1 à 6, secteurs proportionnels aux feuilles plus une. **0 croisement** ; la plus petite distance d'une
arête à un disque qu'elle ne touche pas est 0,33 cm sur la page, entre deux arêtes disjointes 0,57 cm ; les quatre
arêtes les plus lourdes, cachées sous leurs disques au premier flux (D5 : 0,46 cm pour des rayons de 0,48 cm), sont
visibles sur 1,04 à 1,08 cm. La MDS est en encart avec sa fidélité (30,9 %, Spearman 0,61, témoin 0,11), le fond
arrondi est retiré. La légende dit que le dessin est « un calcul de dessin, pas une mesure » : c'est exact.

**G9 (part du lot) : fait.** La table des figures montre les onze titres courts ; chaque légende s'ouvre sur sa tête
en gras, suivie de `\mes`, `\calc` ou `\schema`, et finit par sa ligne « Données ». Les têtes neuves sont des
affirmations : je les ai toutes confrontées aux nombres (III-3.4 : écart maximal 1,66 dB, et de 1,49 à 0,34 dB de
l = 8 à 16 ; III-7.2 : de ×1,02 à ×3,06 dans la bande ; III-7.3 : 10 positions sur 25 communes) ou à leur source
(III-1.2 : « Ce gain n'est pas dans une structure des poids : il est dans la forme du quantificateur »,
`genome/01-eclaireur.md` lignes 162 à 165, non barré). Celle de III-4.8 (« une étoile autour de l'expert 31, puis des
branches minces ») est une lecture : les 5 arêtes du moyeu portent 0,335 des 0,679 bit de l'arbre (49 %), les 4 plus
lourdes sont à lui ; elle tient, la légende nommant les deux autres experts de degré 5.

## 3. Graves neufs : aucun

Cherchés : une légende qui ne dit plus vrai (chaque phrase neuve confrontée à ses nombres, § 1 et § 2), une règle
appliquée de travers (§ 1.3), une série qui ne vient plus de sa source (§ 1.5), un fichier de mesure réécrit
(`frontiere.csv` et les fichiers à 3 fenêtres sont intacts : régénération au bit, et le lot n'a écrit que sous
`memoire/`), une phrase barrée revenue (§ 1.7), un protocole mêlé (R3 : aucun trait entre protocoles ; λ = 1 reste
sur l'axe des bits, « 16 des 32 experts de P1 », P1 étant les experts 0, 4, …, 28 des couches 0, 8, 16, 23,
`genome/01-eclaireur.md` § 6), le point de S\* (R4 : K10, ×1,018). R6 : le commit ne touche aucun fichier de
`genome/pistes/`, `mesures/pistes/`, `outils/pistes/`, `genome/mimetisme/P3/`. Aucun trailer, aucune adresse
électronique dans le message du commit ni dans ses fichiers ; son auteur est la configuration git de la machine,
au nom de Stone.

## 4. Les mineurs neufs

### 4.1 Justesse (3)

- **N2. III-7.4, la colonne 960.** [mes., sur `colonnes-energie-erreur.csv`] La colonne 960, premier canal du morceau
  de rotation de la géante (960 = 15 × 64), d'énergie ordinaire (×0,83), reçoit **×310** l'erreur moyenne du brin,
  presque autant que la colonne 1011 (×334) ; la base lui laisse ×0,87 et S\* ×1,04. La légende ne la nomme pas, et
  ses deux moyennes en dépendent presque entièrement : « les bords des morceaux ×7,6 » est la moyenne de 45 bords
  dont un à ×310 et 44 à ×0,70 en moyenne (au plus ×0,87) ; « les autres colonnes de son morceau ×8,9 » tombe à
  ×4,0 sans elle. La précision « la géante exclue » ne retire rien (1011 n'est pas un bord). Depuis G5, la pointe de
  960 se voit aussi haute que celle de 1011, sans étiquette. Ce n'est pas né du second flux (données et phrase
  inchangées, et `genome/genome.md` l. 528 écrit « les colonnes de rang 0 modulo 64 en reçoivent 7,6 fois leur
  part ») ; le premier juge avait refait ×7,6 sans le décomposer. À écrire, par exemple : « la colonne 960, bord de
  son morceau, reçoit ×310 ; les 44 autres bords ×0,70 », et étiqueter la pointe. Le mécanisme possible (une
  composante commune des erreurs d'écrêtage, si la table n'est pas symétrique, revient sur le premier canal du
  morceau, que la première rangée de Hadamard porte) est une hypothèse de ma part, non mesurée.
- **N3. III-7.2, un renvoi qui porte sur la mauvaise chose.** La légende finit sur « c'est son hypothèse de travail,
  appuyée par le routage imposé (figure suivante) ». La figure suivante (III-7.3) dit justement qu'elle ne refait
  pas cette intervention (Tome II, lot R, expérience B). Au premier flux, « (figure suivante) » renvoyait aux deux
  parts ; la phrase réécrite pour M11 l'a accroché au routage. À écrire : « … qu'elle ne voit pas (figure suivante) ;
  c'est son hypothèse de travail, appuyée par le routage imposé (Tome II, lot R) ».
- **N5. Lot construction, la correction de `genome/construction-codon-pour-le-memoire.md` § 3** (voir § 6) : « A lu
  au motif de B va comme B (×1,389), B lu au motif de A va comme A (×0,715) » est mesuré sur le 20b (A20, B20,
  `JUGEMENT-placement.md` § 0 et § 5.3), dans un paragraphe dont le J1 (r = 1,454) est sur le 120b. Le juge du
  placement porte lui-même la conclusion au 120b (§ 0 et § 12 point 3 : « le J1 du lot A est un gain du format,
  propre à cette machine ») ; il manque seulement « (sur le 20b) ».

### 4.2 Dessin (2)

- **N1. III-7.1, le trait de l'encart barre le point de G1.** Le trait de rappel qui va du coin de la loupe
  (2,658 ; 1,09) au coin bas gauche de l'encart est tracé après les étiquettes ; il traverse « par » de « partitions
  κ, par tenseur » en français et « per » de « κ partitions, per tensor » en anglais (agrandi à 400-500 dpi). Dans ce
  mémoire, une étiquette traversée se lit retirée (D28 du juge de design), et c'est le point que G1 vient de
  reclasser. Remèdes : tracer le trait avant les étiquettes (sous leur halo), ou le faire partir du haut gauche de
  la loupe, ou poser l'étiquette de κ autrement (à gauche du triangle, elle croiserait la flèche de « hebbien par
  e » à 2,18 : il faut choisir).
- **N4. III-4.8, des valeurs posées sur leur arête.** La note du lot dit les valeurs « posées à côté de l'arête ».
  Agrandi : « 0,043 » est posé sur l'arête 22–0 et la coupe en deux ; « 0,024 » coupe 17–18 ; « 0,023 » couvre
  presque toute l'arête courte 14–16 ; « 0,035 » couvre le départ de 22–29 ; « 0,089 » (31–5) et « 0,069 » entaillent
  leur arête. Les nombres restent lisibles (le halo cache le trait, aucun n'est barré), mais une arête coupée ou
  cachée sous sa propre valeur ne se suit plus. Remède : écart perpendiculaire plus grand pour les arêtes obliques,
  ou valeur au bout extérieur de l'arête.

### 4.3 Négligeables (pour mémoire)

- III-4.8 : « contre 0,116 pour l'expert 22 » compare le moyeu aux autres experts de degré 5 ; les experts 17
  (0,148) et 5 (0,121) pèsent plus que 22. Vrai tel quel ; « contre 0,148 pour le suivant (17) » serait plus net.
- III-4.8 : « si bien qu'aucune arête n'en croise une autre » : les secteurs proportionnels ne le garantissent pas
  en général (un secteur de plus de 180°, comme celui du sous-arbre de 17, peut laisser sortir une arête) ; ici c'est
  vrai, vérifié sur les coordonnées.
- III-4.8 : les cercles de profondeur, très pâles, passent sous la note de l'encart (« plan : 30,9 % … »), qui n'a
  pas de halo.
- III-7.1 : la légende nomme les couleurs vert, violet, gris et encre ; le brun du brin et le bleu de λ = 1 de la
  bande ne sont dits que par leurs étiquettes.
- III-3.4 : les rangées des points l = 8, 10 et 14 du panneau (b) (64) ne sont pas dites ; l'axe de III-3.6 dit
  « erreur relative (%) » pour la grandeur que la légende appelle « erreur quadratique relative ».
- III-2.1 : dans les titres de panneau en gras, les nombres (72, 19 110 297 600) sont en maigre ; la ligne
  « Données » de III-1.1 est justifiée avec de grands blancs (une boîte trop creuse, la seule des deux journaux).
- `a-second-poids` et les rapports de P3 diffèrent au cinquième chiffre selon le fichier lu (§ 1.2), sans effet
  imprimé.

## 5. Les mineurs du premier flux

| | état | contrôle |
|---|---|---|
| M1 | levé | 64 / 32 / (2, 1) sur 64, refaits sur les 21 lignes du balayage |
| M2 | levé | échantillon W dit (experts lus dans `codons-tourne-l12.json`), « erreur quadratique relative » dans la légende |
| M3 | levé | témoin de la couche 23 sur sa couche, plancher de la couche 0 en bande, chiffré, dit sans témoin |
| M4 | levé | trois experts de degré 5, 31 moyeu par le poids, les 4 plus lourdes à lui |
| M5 | levé | « 16 des 32 experts de P1 », sous-ensemble vérifié |
| M6 | sans objet ici | l'axe sans perte est en III-8.5 (lot construction, non jugé ici) |
| M7 | levé | deux verdicts dits « de la source, tirés du rapport » ; promesse « mesurée ou seulement prédite » |
| M8 | levé | D1 = 3,8442 dans « ce que la figure ne montre pas » |
| M9 | levé | « garde sa forme, pas ses positions » ; 10 sur 25 |
| M10 | levé | « la seule KL sous 10⁻⁵ est négative » ; routage imposé au Tome II, lot R (mais voir N3 pour III-7.2) |
| M11 | levé | 25 = ⌊2 550/100⌋, 0,98 % ; « hypothèse de travail » |
| M12 | levé | échelles non comptées par la borne, 0,473 contre H₀, lecture datée de la passe 3 |
| M13 | levé | constantes neuves écrites à la main vérifiées : P1 32 experts, P2-10 8 experts et 10 fenêtres (`passe10-base-8.json`), P3 12 tenseurs, 736 = 768 − 32, couches 0, 8, 16, 23 |
| D1 à D10 | levés | D1 (bande), D2 (y = x), D3 (accolades), D4 (G1), D5 (G8), D6 (queues marquées), D7 (brin brun partout, base en losange gris), D8 (aucune espace française en anglais, `langues.py`), D9, D10 |

## 6. Le lot construction : la barre et la correction dans `genome/construction-codon-pour-le-memoire.md`

Commit `cadf276` [lu]. **La barre et la correction tiennent.** Au § 3, la phrase « L'écart de vitesse entre fichiers
est donc un effet de disposition sur le disque d'un ordre de grandeur plus grand que l'effet du format (06 § 8) »
est barrée, et suivie de « Corrigé le 2026-10-27 », des sources (`JUGEMENT-placement.md` § 0, §§ 5.3, 5.6, 5.7,
§ 12 point 3, tous présents) et de « ce qui a changé » (le motif croisé). Au § 5 (F6), le « troisième panneau » est
barré de même et la correction renvoie à R1 et à III-8.6 / III-8.6 bis. Les nombres de la correction sont ceux du
juge du placement : ×1,389 et ×0,715 (§ 0, l. 19, et § 5.3, l. 212-213), ×0,851 et ×0,882 (§ 5.7), 267 473 extents
(§ 0 et § 5.1), ×1,26 (J5 et J6, § 5.9-5.10). Aucune autre phrase du fichier ne garde l'ancienne attribution
(recherche de « disposition », « 30 % », « 1,30 », « 1,44 »). Seule réserve : N5.

## 7. Ce qui pourrait être faux

- **Mes chemins ne sont pas tous indépendants.** Le coût des échelles, d̄ et σ de P3 et la formule de D1 sont relus
  au même endroit que le lot les lit ; je vérifie la recopie, pas la mesure. Le dessin radial est refait d'après la
  même description que le script : l'égalité des positions prouve que le CSV est ce que la légende dit, pas que la
  disposition est la meilleure.
- **σ de P1** : la source prend le plus grand de σ naïf et σ par fenêtres ; avec le seul σ naïf, λ = 0 serait plus
  significatif encore (−5,2 σ) ; aucune convention ne changerait sa classe ni celle de κ (§ 2).
- **N1 et N4** sont lus à l'écran, agrandis de 300 à 500 dpi ; l'estimation de contact de `series2.py` (boîte de
  0,52 × 0,26 cm autour de chaque valeur) est grossière et ne sert qu'à désigner les endroits à regarder.
- **N2** : les nombres (×310, ×0,70, ×4,0) sont refaits sur le CSV commité du lot, égal au journal de la mesure ; la
  cause que je propose n'est pas mesurée. Un autre juge pourrait tenir « ×7,6 » pour une moyenne honnête, puisqu'elle
  est arithmétiquement juste et que la source l'écrit ainsi.
- **Je n'ai pas refait les simulations en gris et en deutéranope** des figures redessinées (le lot ne les a pas
  refaites non plus) : c'est au juge de design du second flux. Les jugements de dessin (N1, N4, négligeables) sont
  des goûts argumentés, sauf les distances chiffrées du § 2.
- **La lecture des PDF par extraction de texte** dépend de l'ordre de MuPDF ; les trois différences restantes entre
  les langues ont été vérifiées à la main.

## 8. Reproduire

Depuis la racine du dépôt (les PDF du pilote se compilent sous `memoire/essai/juge2-ronde/`, dossier ignoré par git,
avec le pilote du lot copié tel quel) :

```
python -I -X utf8 outils/genome/tome3/juge2-ronde/cles.py
python -I -X utf8 outils/genome/tome3/juge2-ronde/refaire2.py        # et --casser
python -I -X utf8 outils/genome/tome3/juge2-ronde/regenerer2.py --fois 2   # et --casser
python -I -X utf8 outils/genome/tome3/juge2-ronde/series2.py         # et --casser (après refaire2.py)
python -I -X utf8 outils/genome/tome3/juge2-ronde/langues.py memoire/essai/juge2-ronde/pilote-juge2-ronde.pdf memoire/essai/juge2-ronde/pilote-juge2-ronde-en.pdf
python -I -X utf8 outils/genome/tome3/juge2-ronde/barrees.py memoire/essai/juge2-ronde/pilote-juge2-ronde.pdf   # et --casser
```

Journaux : `outils/genome/tome3/juge2-ronde/journaux/` (`cles.csv`, `refaire2.csv`, `classes2.csv`,
`regenerer2.csv`, `series2.txt`, `langues.txt`, `barrees.txt`, `compilation.txt`, les sorties `*.log` et les
témoins `*-casser.*`).
