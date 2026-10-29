# Jugement : figures du Tome III, lot « ronde » (ch. 1 à 4 et 7)

Juge indépendant des chiffres, 2026-10-27. Je n'ai tracé aucune figure de ce lot. Jugé : les onze figures
rendues par le lot (commits `ef7919a`, `09eb420`, `3ff6670`, `ad27a5f`, note `2fc8a3f`), contre SOCLE
(demande du 2026-10-17 : « la beauté à égalité avec la justesse »), l'inventaire
(`memoire/tome3/INVENTAIRE-figures.md`, réserves R1 à R6) et les notes « pour le mémoire » de
l'éclaireur, du génome, de la duplication et de la synthèse (avec `genome/01-eclaireur.md`,
`genome/05-synthese.md`, `genome/genome.md`, `genome/duplication.md`,
`genome/predictif-elagage-pour-le-memoire.md`). Aucune passe du modèle, aucune carte graphique.
Outils et journaux : `outils/genome/tome3/juge-ronde/`. Étiquettes : [mes.] mesuré ici par un outil
commité, [lu] lu dans une source commitée.

## 0. Verdict

**Le lot tient, avec réserves ; une figure tombe en l'état : III-7.1.** Les chiffres sont justes : sur
282 clés des quatre `*-nombres.csv`, aucune valeur imprimée n'est fausse, hors la borne de III-2.1 que
j'ai corrigée (§ 4) ; une seule dépend d'une convention (la part portée par « 1 % des positions » : 25 ou
26 positions, 31 ou 32 %, M11) ; les 50 CSV du lot se régénèrent au bit par ses scripts ;
un point tiré au hasard dans chacune des 46 séries tracées se retrouve à la source, et chaque série a
le compte de lignes de sa source. R3 et R4 sont respectées. Mais :

- **1 grave** : III-7.1 classe « gagne » les partitions par κ tenseur par tenseur et écrit que « deux
  points seulement passent sous leur base » ; ce point est à 1,103 fois sa base, et la règle que la
  même légende énonce le dit **égal** (§ 2).
- **23 mineurs** : 13 de justesse (un protocole mal dit, un témoin tracé hors de sa couche, une queue
  décrite plus fidèle qu'elle n'est, etc.) et 10 de dessin (une étiquette barrée par un axe dans un
  mémoire où « barré » veut dire retiré, les deux arêtes les plus lourdes de l'arbre cachées sous leurs
  disques, etc.) (§ 3).
- **3 corrections mécaniques faites par moi**, commit `2824930` (§ 4) : une borne inférieure imprimée
  arrondie au-dessus du minimum vrai (III-2.1), des graduations à la virgule dans la version anglaise
  (III-7.1, III-7.2), un zéro final perdu (III-7.3).

| N° | Figure | Verdict | Pourquoi, en une ligne |
|---|---|---|---|
| III-1.1 | Le bloc MXFP4 | **tient** | disposition, valeurs E2M1 et E8M0 vérifiées ; étiquette collée en FR (D3) |
| III-1.2 | La borne distorsion-débit | **tient** | cordes linéaires en D, donc vrai partage du temps ; l'échelle hors borne non dite (M12) |
| III-2.1 | Le signe des zéros | **tient** (après `2824930`) | la borne « ≥ » était arrondie vers le haut ; corrigée |
| III-3.4 | Le brin sur une gaussienne | **tient**, réserve | « 64 rangées » faux pour 6 des 7 formes à l = 16 (32 rangées) (M1) |
| III-3.6 | Débit-distorsion par tenseur | **tient**, réserve | l'échantillon (4 experts, une rangée sur quatre) n'est pas dit (M2) |
| III-4.2 | Le score de parenté | **tient**, réserve | le témoin du hasard vient de la couche 12 et passe sous la couche 0, dont le plancher est commun (M3) |
| III-4.8 | L'arbre des experts | **tient**, réserves | trois moyeux de degré 5, pas un ; les deux arêtes les plus lourdes invisibles (M4) |
| III-7.1 | La frontière commune | **tombe en l'état** | un « gagne » de trop et une phrase fausse (G1) ; plus M5 à M8, D1, D4 |
| III-7.2 | Erreur d'expert contre KL | **tient** (après `2824930`) | R4 respectée au fichier près ; une étiquette en recouvre une autre (D2) |
| III-7.3 | Deux parts de la KL | **tient**, réserves | « le coin haut reste sur la diagonale » vrai en forme, faux position par position (M9) |
| III-7.4 | La colonne géante | **tient** | ×144, ×334, ×14, ×1,05, ×8,9, ×7,6 refaits et recoupés au journal |

## 1. Ce que j'ai fait

1. **Chaque nombre refait par un autre chemin** (`refaire.py`, écrit sans lire `memoire/outils/tome3_*.py`).
   Il relit les journaux sous `mesures/` et ceux qu'ils citent, pas les CSV dérivés quand un chemin plus
   court vers la mesure existe : le coût du signe des zéros refait par p₀·H₂(p₊/p₀) tenseur par tenseur,
   H(V) refait depuis la loi publiée, les rapports de KL de P1 refaits depuis les 2 550 positions, la
   médiane et les parts de la queue depuis les positions, le débit tourné à erreur égale réinterpolé sur
   la courbe elle-même (écart au verdict ≤ 2·10⁻⁵ bit sur les 12 tenseurs), l'arbre refait par mon
   Kruskal et ma MDS (mêmes 31 arêtes, 30,9 %, Spearman 0,61). Règle déclarée avant : égalité à 2·10⁻⁵
   relatif ; sinon, rejugé à la précision où la légende l'imprime (lue dans le `.tex`).
   Témoin : `--casser` multiplie chaque valeur du juge par 1,001 ; toutes les clés non nulles tombent
   au seuil strict (`journaux/refaire-casser.log`) [mes.].
2. **Régénération au bit** (`regenerer.py`) : les quatre scripts du lot relancés tels quels ; les 50
   fichiers `donnees/{eclaireur,synthese,genome,duplication}-*.csv` ont l'empreinte git de leur blob
   commité ; aucun CRLF ; aucun autre fichier du dépôt modifié. Témoin `--casser` (un octet ajouté à une
   copie par lot) : 4 sur 4 tombent. `frontiere.py --k10 --sortie` et `frontiere.py --sortie` (sans
   `--k10`) régénèrent au bit les quatre fichiers de `synthese/k10/` et les quatre fichiers à 3
   fenêtres : l'option `--sortie` est rétrocompatible et les fichiers commités avant ne sont pas
   réécrits (`journaux/k10-regen.csv`) [mes.].
3. **Un point par série** (`echantillon.py`, graine 20261027, la série k tire avec 20261027 + k) :
   46 séries, 46 points retrouvés à la source, 46 comptes de lignes égaux à ceux de la source (par
   exemple : 23 itérés de Blahut-Arimoto dans l'axe, 8 + 15 ; 3 962 et 3 839 points de courbes hors
   « global » ; 496 + 372 + 12 scores). Témoin : la valeur tirée multipliée par 1,01, 46 sur 46 tombent.
4. **Les deux langues** compilées par mes soins (`memoire/essai/juge-ronde/`, lualatex de MiKTeX,
   deux passes) : 14 pages chacune, aucune erreur, aucune boîte trop pleine, environ 20 s par passe (et
   non 2 minutes). Les nombres des légendes FR et EN, extraits du PDF, sont les mêmes un à un. Pages
   lues une à une, détails agrandis.
5. **Les constats** que ce jugement chiffre hors des clés du lot sont refaits par `constats.py`
   (`journaux/constats.txt`), et la dispersion du témoin de la MDS par `refaire.py`
   (`journaux/temoin-mds.csv`).

## 2. Le grave

**G1. III-7.1 : les partitions par κ tenseur par tenseur ne gagnent pas en KL.** La légende dit :
« le remplissage [dit] le verdict de la règle déclarée (différence appariée, d̄ ≤ 2σ : égal) », puis
« Deux points seulement passent sous leur base : la mutation synonyme λ = 0 […] et les partitions par κ
tenseur par tenseur (KL égale pour 0,911× les bits) ». Or [mes., `constats.txt`] :

| point | rapport de KL | d̄ ± σ | par la règle de la légende |
|---|---|---|---|
| mutation synonyme λ = 0 (P1) | 0,7266 | −0,00985 ± 0,00334 (−2,95 σ) | meilleur (d̄ + 2σ < 0) |
| partitions par κ, tenseur par tenseur (P3) | **1,1031** | **+0,00656 ± 0,00531 (+1,24 σ)** | **égal** |

Le point est au-dessus de la ligne 1, hors de la zone teintée « mieux que sa base en KL », et la figure
le remplit comme un gagnant. Le remplissage suit la colonne `verdict` de `frontiere.csv` (« gagne :
0,911 × les bits, KL égale par la règle ») ; mais la synthèse dit trois gagnants, tous synonymes (05 § 0)
et range ce point « égale en KL, 0,911 × les bits » (05 § 2.3). Les deux lectures ne vont pas ensemble
dans une seule figure dont la légende fixe la règle du remplissage.

**Tranché** (le lot me le demandait) : λ = 0 reste « gagne » (meilleur par la règle ; +0,011 bit, ce que
la légende dit) ; les partitions par κ tenseur par tenseur passent à « égal » ; la phrase devient, par
exemple : « Un seul point passe sous sa base en KL : la mutation synonyme λ = 0 (×0,73, à +0,011 bit) ;
les partitions par κ tenseur par tenseur rendent une KL égale par la règle (+0,0066 ± 0,0053) pour
0,911 × les bits. » Les nombres existent déjà dans `synthese-nombres.csv` sauf l'appariée de κ
(`mesures/genome/predictif-elagage/kl/comparer-base-ecsq_kappa_t-f5-9.json`). Ce n'est pas mécanique (une
classe et une phrase) : je ne l'ai pas corrigé.

## 3. Les mineurs

### 3.1 Justesse (13)

- **M1. III-3.4, « 64 rangées de 2 880 valeurs ».** Six des sept formes à l = 16 sont mesurées sur
  **32 rangées** (92 160 valeurs) ; seule (2, 1) à l = 16 l'est sur 64 (`gauss-balayage.jsonl`,
  `constats.txt`). La source le dit mal aussi (genome.md § 3.2 : « 64 rangées »). Le CSV du lot porte la
  bonne colonne `rangees` ; la légende doit le dire.
- **M2. III-3.6, l'échantillon n'est pas dit.** Les courbes et le losange de la base sont mesurés sur
  l'échantillon du critère W : experts 0, 8, 16, 24 de chaque tenseur, une rangée sur quatre, 2 880
  rangées par tenseur (genome.md § 2 et § 5.2, « erreur de la base (échantillon) »). « Douze tenseurs »
  se lit comme des tenseurs entiers. L'erreur tracée est aussi Σ(w − ŵ)²/Σw² (relative quadratique) :
  III-3.4 dit « erreur quadratique relative », III-3.6 « erreur de poids (%) » pour la même grandeur.
- **M3. III-4.2, le témoin du hasard tracé hors de sa couche.** La ligne à 0,0016 vient de la couche 12
  (2 paires) ; la couche 23 en donne autant (8 paires, `arbre-c23.json`), et le maximum ×27 est en
  couche 23 (enfant (23, 0), parent (23, 22)) : le « ×27 » tient. Mais la ligne traverse la couche 0,
  où les 124 candidats de même couche ont tous un cos de down de 0,232 à 0,305 et un score de 0,0153 à
  0,0341 [mes.] : un plancher commun à la couche (la statistique de colonne d'entrée ; un parent de
  hasard y rend 88 à 94 % du gain D1, duplication § 0.8 a), pas une parenté dix fois au-dessus du
  hasard. Dire en légende la couche du témoin et ce plancher.
- **M4. III-4.8, « l'expert 31 est le moyeu, 5 arêtes ».** Les experts 22, 29 et 31 ont tous trois le
  degré 5 (trois disques de même taille) ; 31 est le moyeu par le poids (0,335 bit d'arêtes, les quatre
  plus lourdes ; 22 : 0,116 ; 29 : 0,025) [mes.]. Dire « le moyeu par le poids ».
- **M5. III-7.1, « λ = 1 appartient au protocole P1 à 32 experts ».** La passe λ = 1 porte sur 16 de ces
  32 experts (0, 8, 16, 24 de chaque couche ; protocole `P1-sorties`, sa propre base à 2,6415 bits)
  [mes.]. R3 reste respectée : aucun point à 768 experts n'est tracé, rien ne relie les protocoles.
- **M6. III-7.1, « il perd sur 6 des 12 ».** Vrai contre le codon en octets, la comparaison de la règle
  des 0,015 bit. Mais ces pertes viennent presque toutes de l'alphabet en demi-octets (+0,003 à
  +0,005 bit) ; contre les demi-octets sans colonne, le contexte de colonne ne perd que sur blk.0 down
  (+0,0006), ce que dit 05 § 2.1 [mes.]. Dire « CODES_COL perd contre le codon en octets sur 6 tenseurs ».
- **M7. III-7.1, la règle et les promesses.** Deux perdants n'ont pas de différence appariée (partitions
  par e, élagage (e, q)) : leur « tombe » vient du rapport (×4,85, ×4,26), pas de la règle que la légende
  énonce. Et la « promesse » de deux perdants était une erreur d'expert **prédite**, pas mesurée :
  hebbien (e, ℓ, c), prédit 4,33 %, mesuré 9,23 % ; élagage (e, q), dont la promesse (« 1,695 bit (× 0,644)
  à erreur égale ») est **barrée** dans sa source (predictif-elagage § 0 point 7 : « Prédit seulement »).
  La flèche la montre rompue, ce qui est fidèle ; la légende doit dire « promesse mesurée ou prédite »
  pour ne pas lui rendre le statut d'une mesure.
- **M8. III-7.1, un point de la frontière manque sans être dit** : la duplication D1 sans perte
  (3,8442 bits, tombe ; P0) est dans `frontiere.csv` mais ni sur l'axe sans perte ni dans « ce que la
  figure ne montre pas ».
- **M9. III-7.3, « Le coin haut reste sur la diagonale ».** Vrai pour la forme de la queue (99,9ᵉ
  centile 1,59 → 1,70) et au tout extrême (KL > 1 : 6 positions communes sur 9, rapport médian 0,93) ;
  faux position par position dès 0,3 : 53 positions de la base au-dessus de 0,3, 40 du synonyme, 17
  seulement en commun ; Spearman des 100 plus grandes −0,25 ; pour les positions de la base au-dessus
  de 0,3, le synonyme est plus bas d'un facteur médian 2,7 (10^0,43), comme la masse (10^0,35)
  [mes.]. La queue garde sa forme, pas ses positions : c'est ce qu'il faut écrire (et c'est ce
  qu'attendent des bascules qui changent de positions).
- **M10. III-7.3, deux précisions.** « 1 KL sous 10⁻⁵ (bruit d'arrondi, l'une négative) » : la seule
  est négative (−6,9·10⁻⁶), « l'une » est faux. « la preuve par le routage imposé est au chapitre 11 » :
  l'intervention (88 % de la KL retirée en imposant le routage) est au Tome II, lot R, expérience B
  (05 § 2.2) ; le chapitre 11 la cite.
- **M11. III-7.3, l'étiquette [mes.] couvre une lecture.** « La part lisse, que l'erreur d'expert suit »
  et la queue « de bascules de routage » sont la lecture de 05 § 2.2, qui la dit « hypothèse de travail »
  (appuyée par l'intervention du lot R). Et « 1 % des positions » compte 25 positions (0,98 %) : avec 26,
  la part de la base est 32 % et non 31 % ; dire la convention.
- **M12. III-1.2, ce que la borne ne compte pas.** R(D) est la borne des codes **sachant l'échelle**
  (0,0375 bit par poids d'échelles non comptés, borne_rd.py) ; la frontière à 2,6441 bits les compte (et
  son contexte κ). Avec H₀ seul (2,6415, codes sans échelles) l'écart est 0,473 bit au lieu de 0,476 :
  la conclusion ne change pas, mais la légende doit le dire. Et la lecture « chaque itéré est
  atteignable » a été posée **après** la passe 3, la règle déclarée avant ne publiant que des points
  convergés (01 § 3 le dit) : la légende peut le dire en une proposition.
- **M13. « Aucun chiffre recopié à la main » est vrai des mesures, pas des constantes de protocole.**
  Écrits en dur dans les légendes : 90 blocs et 2 880 poids (III-1.1), 32 et 768 et 736 experts
  (III-7.3), 8 experts et 12 tenseurs (III-7.1), couche 8, down, expert 16, 64, trois exceptions
  (III-7.4), couches et fenêtre l = 12, morceaux de 64 (III-3.6). Je les ai tous vérifiés aux sources :
  tous justes, sauf « λ = 1 … 32 experts » (M5).

### 3.2 Dessin (10)

- **D1. III-7.1, bande du bas : « S\* (erreur d'expert) » et « sa base ; D2b » sont traversés par l'axe
  des bits.** Ils se lisent barrés, dans un mémoire où une étiquette barrée veut dire « retiré »
  (III-7.2 barre à dessein « S\*, 3 fenêtres »). À déplacer au-dessus de la bande ou à décaler.
- **D2. III-7.2 : l'étiquette « y = x » recouvre « hebbien (e, ℓ, c) »** (les deux deviennent illisibles).
- **D3. III-1.1, version française : « échelle » et « qs[16] : … » se touchent** (« échelleqs[16] »).
- **D4. III-7.1 : un triangle plein (« gagne ») hors de la zone verte** ; se règle avec G1.
- **D5. III-4.8 : les deux arêtes les plus lourdes sont invisibles.** (17, 31) mesure 0,46 cm sur la page
  et (5, 31) 0,47 cm, quand les rayons de leurs disques font 0,48 et 0,50 cm : elles sont entièrement
  sous les disques ; c'est pourtant « la seule trace d'une famille » (duplication § 5) [mes.]. Un encart
  agrandi de l'amas 5-15-17-25-31 (le lot le proposait) est nécessaire, pas seulement utile.
- **D6. III-7.3 : la couleur par fenêtre ne montre pas le groupement qu'elle annonce.** Dix teintes à
  0,55 d'opacité dans un cœur dense ; le groupement de la queue par fenêtre est réel mais modéré (8 des
  26 plus grandes positions de la base dans la fenêtre 5, [mes.]) et se démontre par l'écart-type par
  blocs de fenêtres (05 § 1.3), pas par l'image. Marquer les 1 % de la queue, ou un petit panneau de la
  KL par fenêtre. La densité de droite n'a pas son étiquette (« synonyme »).
- **D7. Couleurs d'un même objet d'une figure à l'autre** : la base frontière est rouge et le brin bleu en
  III-3.6 ; en III-7.4 la base est grise et le brin rouge. Dans deux chapitres voisins, un lecteur suit
  les couleurs.
- **D8. Typographie anglaise** : espaces françaises devant « : » et « ; » dans la version anglaise (« whole
  model : », « planted control (…) : », « smooth part : », « F1 : », « … ; script ») ; et
  `frontiere.py --k10` imprimé « frontiere.py--k10 » (l'espace est mangée dans `\fichier`).
- **D9. III-3.4, panneau du bas : l'étiquette « (5,2) » chevauche la courbe.**
- **D10. III-4.2 : « couche voisine » dans la légende du dessin, « couche précédente » dans le texte**
  (l'anglais dit « previous layer » aux deux endroits) : « voisine » suggère les deux côtés.

### 3.3 Négligeables (dits pour mémoire)

- Les écarts en dB du balayage gaussien sont calculés avec la borne arrondie à six décimales du journal
  (0,003906 pour 2⁻⁸) : 1,6582 dB au lieu de 1,6579 à 4 bits ; invisible, imprimé 1,66 dans les deux cas.
- Le témoin de la MDS (0,11) est un seul tirage ; sur 200 permutations (graine 20261027) : moyenne 0,003,
  écart-type 0,084, 5 % à 95 % de −0,117 à 0,154. Le Spearman de 0,61 est à environ 7 écarts-types : la
  légende pourrait donner la loi plutôt qu'un tirage.
- 57 clés des `*-nombres.csv` ne sont imprimées nulle part (inoffensif).

## 4. Ce que j'ai corrigé moi-même (commit `2824930`)

Trois erreurs mécaniques de nombres imprimés, rien d'autre :

1. **III-2.1** : « H(signe | zéro) ≥ 0,9999995 bit dans chaque tenseur » (20b) pour un minimum vrai de
   0,99999949611, et « ≥ 0,9999996 » (120b) pour 0,99999955044 : arrondie au plus proche, une borne
   inférieure était **au-dessus** du minimum, donc fausse. Imprimée à 9 décimales : ≥ 0,999999496 et
   ≥ 0,99999955, toutes deux sous le minimum vrai.
2. **III-7.1 et III-7.2** : graduations écrites en dur avec la virgule (`0{,}7`, `1{,}5`, `0{,}25`,
   `0{,}5`), donc « 0,7 » et « 1,5 » dans la version anglaise ; passées par `\EF`.
3. **III-7.3** : le 99,9ᵉ centile du synonyme imprimé « 1,7 » au lieu de « 1,70 » (`fixed` sans
   `zerofill`, le piège que la note de reprise du lot signale) ; les deux centiles ont désormais
   `fixed zerofill`. `zeros.py` vérifie qu'aucun autre nombre imprimé ne perd de zéro final.

Pilote recompilé en français et en anglais après correction : sans erreur ni boîte trop pleine.

## 5. Les réserves de l'inventaire, et les phrases barrées

- **R1** (le J1 en ABBA) et **R2** (Tome II) ne concernent pas ce lot.
- **R3 tient** : aucun point à 768 experts dans III-7.1 ni III-7.2 ; λ = 1 sur l'axe des bits seul ;
  aucun trait entre protocoles. Seule réserve : M5 (16 experts, pas 32).
- **R4 tient** : S\* de III-7.1 et III-7.2 vient de K10 (1,01764 ; appariée +0,000363 ± 0,001856) ; le
  point à 3 fenêtres (1,3349) est montré creux et barré, avec la flèche de la correction ; les fichiers
  à 3 fenêtres sont inchangés (régénérés au bit) ; `--sortie` est rétrocompatible.
- **R6 tient** : rien d'écrit par le lot dans `genome/pistes/`, `mesures/pistes/`, `outils/pistes/`,
  `genome/mimetisme/P3/` (listes de fichiers des cinq commits).
- **Phrases barrées** : j'ai relevé les 37 passages barrés de 05, predictif-elagage, duplication,
  JUGEMENT-construction, construction-synonyme et 07, et cherché leurs nombres dans les légendes et les
  `*-nombres.csv`. Aucune ne revit, sauf la promesse barrée de l'élagage (e, q), que III-7.1 dessine
  rompue (M7). « λ = 1 : KL 0,0262 contre 0,0360 » (barré) : ces deux nombres sont dans
  `synthese-nombres.csv` (`moy-syn`, `moy-base`), correctement rattachés à λ = 0, et non imprimés.
  « S\* garde la médiane (×1,09) et épaissit la queue » (barré) : absent.
- **Aucun trailer, aucune adresse** dans les cinq commits du lot ; tout est au nom de Stone.

## 6. Le design

- **Palette** : le préambule est suivi partout (SerieA à SerieE, Accent, Encre, Signe, Fond) ; dans
  III-7.1 la teinte dit l'équipe à gauche comme à droite (le codon vient de l'éclaireur, bleu ; la
  colonne de prédictif-élagage, rouge) : cohérent. La faute est entre figures (D7).
- **Lisibilité** : bonne pour III-1.2, III-2.1, III-3.6, III-7.2 et III-7.4 ; quatre collisions
  d'étiquettes (D1, D2, D3, D9), dont une qui change le sens (D1).
- **Une idée par figure** : tenu, sauf III-7.1, qui porte trois choses (le plan à la KL, la bande sans
  KL, l'axe sans perte) ; elles servent la même idée (la frontière commune) et le titre le dit.
- **Les deux figures « d'espace »** (III-4.8, III-7.3) disent leur fidélité (30,9 % de variance,
  Spearman 0,61 ; protocole P1, 32 experts sur 768) : c'est ce que demandait l'inventaire. Leur défaut
  est ce qu'elles cachent ou n'arrivent pas à montrer (D5, D6), pas ce qu'elles prétendent.
- **Beauté** : III-1.1, III-1.2 et III-7.4 sont au niveau de la demande du 2026-10-17 ; III-4.8
  le sera avec l'encart.

## 7. Ce qui reste (au lot, ou au second flux)

1. G1 (classe et phrase de III-7.1), puis M1 à M13 et D1 à D10, dans cet ordre.
2. Ce que le lot listait et que je confirme : III-7.4 pour les autres tenseurs (état C) et la bande des
   classes de colonne de blk.0 gate ; les `\cite` au chapitre (OCP MX v1.0, llama.cpp, Blahut 1972,
   Kruskal 1956, Shannon 1959) ; les bascules position par position de III-7.3 n'existent pas dans les
   CSV de l'éclaireur (pas de colonne de routage) : M9 dit ce qu'on peut écrire sans elles.
3. Le pilote complet compile en environ 20 s par passe ici (pas 2 minutes).

## 8. Ce qui pourrait être faux

- **Mes chemins indépendants ne le sont pas tous.** Pour les bits et les rapports lus tels quels dans un
  journal (bits_H0_sym, bits_reels, kl_moyenne de `resume-12.csv`, le débit 2,64 de S\*, 2,6441 écrit en
  dur par `frontiere.py`), j'ai seulement relu le même nombre au même endroit : je vérifie la
  recopie, pas la mesure. Sont vraiment refaits : le coût des zéros, H(V), les cordes, les rapports et
  quantiles de P1 depuis les positions, les gains par réinterpolation des courbes, l'arbre, la MDS, les
  rapports de colonnes.
- **G1 tranche entre deux sources du projet** (la colonne `verdict` de `frontiere.csv` contre 05 § 0 et
  § 2.3). Un autre juge pourrait garder « gagne » au sens « gagne sur l'axe des bits à KL égale » ; il
  devrait alors changer la règle écrite dans la légende et la phrase « passent sous leur base », qui
  restent fausses telles quelles.
- **M9 dépend de seuils que j'ai choisis** (0,1 ; 0,3 ; 1) après avoir vu les données ; le Spearman des
  100 plus grandes (−0,25) et les comptes au-dessus de 0,3 vont dans le même sens, mais ce n'est pas un
  test déclaré avant.
- **M3** suppose que le plancher de la couche 0 est commun (et non une parenté) parce que les 124
  candidats y sont uniformément hauts et que D1 au hasard y rend 88 à 94 % du gain ; aucun témoin du
  hasard n'a été mesuré sur le score de la couche 0 lui-même (il faudrait une passe sur les poids, hors
  de ce flux).
- **Le jugement du dessin est le mien** : D6, D7 et le classement des figures « au niveau de la
  demande » sont des goûts argumentés, pas des mesures. Les PDF ont été lus à l'écran à l'échelle de la
  page et agrandis aux endroits cités, pas imprimés.
- **La lecture des PDF par extraction de texte** (comparaison des nombres FR et EN) dépend de l'ordre
  d'extraction de MuPDF ; les différences restantes (numéros de figure, ensemble {0,1,…,12} lu comme
  décimaux en français, groupes de milliers) ont été vérifiées à la main.

## 9. Reproduire

Depuis la racine du dépôt :

```
python -I -X utf8 outils/genome/tome3/juge-ronde/refaire.py        # et --casser (témoin)
python -I -X utf8 outils/genome/tome3/juge-ronde/regenerer.py      # et --casser (témoin)
python -I -X utf8 outils/genome/tome3/juge-ronde/echantillon.py    # et --casser (témoin)
python -I -X utf8 outils/genome/tome3/juge-ronde/zeros.py
python -I -X utf8 outils/genome/tome3/juge-ronde/constats.py
```

Journaux : `outils/genome/tome3/juge-ronde/journaux/` (`refaire-<lot>.csv` clé par clé, `regenerer.csv`,
`k10-regen.csv`, `echantillon.csv`, `constats.txt`, `temoin-mds.csv`, et les sorties `*.log`, témoins
compris). Pilote : `memoire/essai/juge-ronde/pilote-juge-ronde.tex` (dossier ignoré par git ; même
source que celui du lot ; anglais par `-jobname=pilote-juge-ronde-en "\def\ANGLAIS{1}\input{…}"`).
