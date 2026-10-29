# Tome III, premier flux de figures : le jugement de design

Juge de design du flux (SOCLE, demande de Stone du 2026-10-17 : « la beauté à égalité avec la justesse », des
figures « dignes de ce travail »). Je n'ai tracé aucune figure et je n'en modifie aucune : ce document dit ce
qu'il faut changer, figure par figure. Les chiffres sont l'affaire des trois juges des chiffres
(`JUGEMENT-figures-construction.md`, `-ronde.md`, `-latents.md`) ; je ne les refais pas, je m'appuie sur leurs
verdicts quand un défaut de dessin rend un chiffre faux à l'œil. Écrit le 2026-10-27.

## 0. Verdict

**Le flux est juste, il n'est pas encore beau d'un bout à l'autre.** Vingt-huit figures dans les pilotes, pour
vingt-sept numéros (III-9.1 est tracée par deux lots) ; les six pilotes (trois lots, deux langues) compilent sans erreur ni
renvoi manquant. Les schémas (III-1.1, III-8.4, III-8.7), la roue des codons (III-8.1), la rangée de 32 poids
(III-9.1 (c)) et les petits multiples de III-3.6 sont déjà au niveau demandé.

**10 graves, 31 mineurs.** Tombent en l'état, pour le dessin : **III-4.8, III-7.1, III-7.4 (anglais),
III-7.6, III-8.6, III-9.1, III-9.2, III-9.3, III-9.6**, et l'**ensemble** pour ses légendes (G9). Aucune ne
tombe pour un défaut sans remède : chaque grave a son correctif, écrit au § 3, et aucun ne demande de mesure
neuve.

Ce que l'ensemble doit gagner avant le mémoire, par ordre de poids :
1. **Un dictionnaire des couleurs du Tome III** (§ 2.1) : aujourd'hui le rouge `SerieB` porte au moins neuf
   sens, et le synonyme est bleu dans un panneau de III-9.1 et rouge dans un autre.
2. **Une seule convention de légende** (G9) : titre court, phrase de tête, étiquette de provenance, ligne
   « Données ». Les trois lots en ont chacun une ; le lot ronde n'a pas de titre court, et sa table des
   figures n'affiche que « III-1.1 », « III-1.2 »…
3. **Le noir et blanc et le daltonisme** : là où la couleur porte seule l'idée (III-7.6, III-9.2, III-10.1),
   la figure s'efface, chiffres du § 2.2 à l'appui.
4. **Une idée par figure** : III-8.6 et III-7.1 en portent deux à quatre. III-9.6 et III-4.8 ont la bonne
   idée, mais il faut la chercher.

## 1. Méthode

- Les trois pilotes du flux (`memoire/essai/pilote-tome3-{construction,ronde,latents}.tex`), copiés tels quels
  sous `memoire/essai/juge-design/` (dossier ignoré par git), compilés par `lualatex` (MiKTeX), deux passes, en
  français et en anglais (`-jobname=…-en "\def\ANGLAIS{1}\input{…}"`). Résultat : 0 erreur et 0 avertissement
  LaTeX dans les six journaux ; 17 + 17, 14 + 14 et 6 + 6 pages. Boîtes trop pleines : 4 en français et 3 en
  anglais, toutes dans le pilote construction (roue 4,4 pt, accumulateur 2,6 pt, format 2,0 pt, ch. 9 3,5 pt).
- Le pilote de la piste tropicale (`outils/pistes/tropicale/pilote-figures.tex`), copié dans le même dossier
  et compilé en français, pour comparer le style. Le flux des pistes reste en lecture seule (R6).
- J'ai lu chaque page des PDF, à 100 dpi pour l'ensemble, puis chaque figure agrandie de 200 à 500 dpi.
  Toutes les pages anglaises ont été lues en planches de deux à quatre pages, et les détails agrandis là où
  le français avait un défaut. Une lecture à 100 dpi m'avait trompé : j'y croyais fausse la légende de
  III-9.2 ; agrandie, elle est juste. Je ne retiens donc que des défauts vus agrandis.
- Le noir et blanc et le daltonisme se lisent sur des rendus simulés. `zoom.py` et `planche.py` rendent une
  page par `pdftoppm` et la convertissent en luminance (`gris`), ou par les matrices de Machado, Oliveira et
  Fernandes (2009), à sévérité 1 (`deuter`, `protan`).
- `palette.py` chiffre les paires de couleurs que les figures demandent de distinguer : ΔE CIE76 dans CIELAB
  (D65), en vision normale, deutéranope, protanope et en gris. Témoins déclarés dans le script avant la
  passe :
  - un gris pur reste gris sous chaque matrice ;
  - la paire rouge-vert `SerieB`/`SerieC` tombe sous la moitié de son ΔE normal en vision deutéranope.

  Les deux tiennent. Cassure (`--casser`, matrices remplacées par l'identité) : le second témoin tombe, comme
  il le doit. Les sorties sont `journaux/palette.json` et `journaux/palette-casse.json`.
- Outils et journaux : `outils/genome/tome3/juge-design/`.

## 2. L'ensemble

### 2.1 La palette : un rouge à neuf sens, un synonyme à deux couleurs

Le préambule donne une palette sobre, de belle tenue : `SerieA` à `SerieF`, plus les couleurs des champs de
bits. Les lots l'emploient bien un par un, mais pas d'un lot à l'autre. `SerieB` (rouge, = `Signe` = `Calcul`)
veut dire successivement :
- le bit de signe et les valeurs négatives (III-1.1, III-8.1, III-8.7) ;
- gpt-oss-120b (III-8.3, III-8.8) ;
- le fichier v1.2 (III-8.6) ;
- la cassure du témoin (III-8.4) ;
- le seuil du cahier (III-8.5) ;
- le protocole P3 (III-7.1, III-7.2) ;
- le témoin planté (III-4.2) ;
- les experts de degré ≥ 3 (III-4.8) ;
- le brin (III-7.4) ;
- le synonyme (III-9.1 (c), III-9.7).

Au chapitre 8, trois figures de suite font dire au rouge trois choses différentes (le négatif, le v1.2,
le 120b).

**Décision (réponse par délégation du 2026-10-27, réversible ; raison : un lecteur apprend une couleur une
fois par tome)** : le dictionnaire suivant s'impose aux figures du Tome III. Une couleur hors dictionnaire est
permise à l'intérieur d'une seule figure, si sa légende la dit.

| Entité récurrente | Couleur | Remarque |
|---|---|---|
| bit de signe, valeur négative | `Signe` (rouge) | **seul** sens du rouge plein |
| base frontière (F1) | `SerieF` (gris bleuté), point en losange gris foncé | III-1.2, III-3.6, III-7.4 : losange rouge → gris foncé |
| synonyme λ = 1 (lot B) | `SerieA` (bleu) | III-9.1 (c) et III-9.7 passent du rouge au bleu |
| synonyme λ = 0 | `SerieC` (vert) | III-7.1, III-7.2 : le point « synonyme λ = 0 » passe en vert |
| llama.cpp Q2_0 | `SerieD` (orange) | déjà ainsi |
| moteur exact, poids exact, référence | `Encre` | déjà ainsi |
| S\* | `SerieE` (violet) | III-7.4 : S\* passe du vert au violet |
| gpt-oss-20b / gpt-oss-120b | `SerieA` / `SerieB`, distingués aussi par la marque (cercle / losange) | seul autre usage permis du rouge, toujours doublé d'une forme |
| v1.0 / v1.2 / compagnon rapide | `black!35` / `Echelle` (orange, la couleur du rayon fondu de III-8.1) / `SerieF` | III-8.6 |
| R1 / fenêtres neuves | `SerieA` / `SerieE`, toujours doublés de la marque (cercle / losange) | III-9.3, III-10.3 |
| seuil ou règle déclarée, témoin, cassure | `Encre` en tirets ; cassure marquée d'une croix noire | plus de rouge pour un seuil |
| « mieux que la base », zone gagnante | `Mant!8` | déjà ainsi |
| hors du domaine mesuré (directions muettes, bande « sans KL ») | `black!6` | le gris de fond ne veut dire que cela |

Aux III-7.1 et III-7.2, le protocole passe à la **forme seule** (P1 cercle, P2 carré, P3 triangle, en `Encre`)
et le verdict au remplissage. La couleur y retrouve son sens de variante. Les deux figures n'ont alors plus
qu'une dimension de couleur à apprendre.

### 2.2 Le noir et blanc et le daltonisme, chiffrés

ΔE CIE76 des paires que la figure demande de séparer (`journaux/palette.json`). En gris, sous 5, deux traits de
même épaisseur ne se séparent plus à l'impression ; en simulation deutéranope, sous 10, de petites marques ne se
séparent plus (seuils lus sur les rendus simulés, voir § 5).

| Paire (figure) | normal | deutéranope | protanope | gris |
|---|---|---|---|---|
| frontière / λ = 0 (III-9.2, III-10.3) | 48,4 | 27,6 | 35,1 | **0,9** |
| R1 seul / neuves seules (III-10.1) | 26,4 | **3,0** | **6,9** | **1,5** |
| expert 24 / expert 4 (III-7.6) | 37,7 | **9,2** | **5,7** | **1,9** |
| expert 12 / expert 21 (III-7.6) ; R1 / neuves (III-9.3) ; l = 12 / l = 16 (III-3.4) | 45,7 | **7,3** | 12,6 | **4,3** |
| brin / S\* (III-7.4) ; v1.2 / compagnon (III-8.6) | 94,8 | 26,7 | 16,8 | 6,9 |
| zéros / négatifs (III-8.1) | 45,7 | 28,2 | 41,9 | 18,9 |
| cassure / grille égale (III-8.4) | 84,3 | 54,2 | 54,1 | 40,7 |

Lecture :
- **III-9.3 et III-3.4 tiennent** malgré un ΔE faible, parce que la marque double la couleur : cercle contre
  losange en III-9.3, plein contre creux en III-3.4.
- **III-9.2, III-10.1 et III-7.6 ne tiennent pas** : la couleur y porte seule la distinction.
- **III-8.4 tient** par la distance, mais la case rouge est trop petite pour être vue (D9).

### 2.3 La typographie et les traits

- **Titres de panneau** : trois styles coexistent.
  - Gras sans empattement : lot construction, `\sffamily\small\bfseries`.
  - Maigre sans empattement : lot latents, III-3.6, III-8.2 ; lot ronde en partie.
  - Corps `\scriptsize` : encarts de III-8.5 et de III-8.6.

  Décision : `\sffamily\small\bfseries` pour un panneau (« (a) » puis une phrase en minuscules), et
  `\sffamily\footnotesize` maigre pour un encart. Sont à aligner : III-2.1, III-3.6, III-7.6, III-8.2, III-9.7,
  et la casse de III-8.7 (« RÉPERTOIRE », « TABLES » contre « en-tête fixe »).
- **Corps** : des graduations `\tiny` (numéros des fenêtres en III-9.3, valeurs dans les barres de III-8.8,
  étiquettes de l'encart de III-8.6) côtoient des étiquettes d'axe en `\small`. Plancher : `\scriptsize` pour
  tout texte d'une figure.
- **Décimales des graduations** : « 0,1 » à côté de « 0,15 » (III-8.5, III-8.8), « 0,2 » à côté de « 0,24 »
  (III-8.3). Il faut `fixed zerofill` partout, comme le fait déjà III-3.6.
- **Graduations du haut qui sortent du cadre** (III-2.1, III-8.5) : `xtick pos=bottom` ou `tick align=inside`,
  comme ailleurs.
- **Étiquettes traversées par un trait** : dans ce mémoire, une phrase barrée veut dire « contredite par une
  mesure » (SOCLE). Une étiquette qu'un trait traverse se lit donc comme une phrase retirée. Cas vus :
  - III-9.1 (c) : « l'aire est le sur-apprentissage résiduel », de plus fausse selon le juge des chiffres, G3 ;
  - III-7.1 : « S\* (erreur d'expert) », « sa base ; D2b » ;
  - III-7.2 : « hebbien (e, ℓ, c) », « partitions κ, moyenne » ;
  - III-8.6 (a), en anglais : « ±2σ of v1.0 », « r = 1.454 ».

  Règle : toute étiquette posée dans un graphe a un halo blanc (`fill=white, fill opacity=0.85, text
  opacity=1, inner sep=1pt`).
- **Césures dans les nœuds** (« ex-pert » en III-8.4, « oc-tets », « fré-quence » en III-8.7) :
  `\hyphenpenalty=10000` ou `align=left` dans le style des nœuds de texte.
- **Épaisseurs** : le style `memoire` donne 0,9 pt aux courbes, et les lots s'y tiennent. Deux sorties :
  - III-7.4 trace ses trois séries à 0,35 pt, et sa légende montre alors trois traits noirs (G5) ;
  - l'icône de légende des barres de III-2.1 hérite de 0,9 pt et dessine des pastilles doubles à halo gris :
    il faut `area legend`.

### 2.4 Les légendes et les deux langues

- **G9** (§ 3).
- **Anglais** :
  - la typographie française survit (« : » et « ; » précédés d'une espace, « 5.6 % ») : D8 du juge ronde,
    étendu ici aux lots construction et latents ;
  - deux nœuds se touchent en III-8.4 (« … 2 486 216 one code 0 → ») et dans l'encart de III-8.6
    (« 267 473 ext. 1-extent chunks ») ;
  - en III-8.7, `empreinte_canonique` est un identifiant du code : il reste tel quel, mais la légende doit le
    dire.
- **Français** : en III-8.6, le titre de (c) chevauche le titre de l'encart (G6).

### 2.5 Ce qui est de trop d'une figure à l'autre

- La pièce du signe des zéros figure trois fois : 0,9999999967 bit dans III-8.1, le même minimum dans III-2.1,
  et le gain par tenseur, qui en découle, dans III-2.1 (coût) puis III-8.3 (gain = 2 × part des −0). Il faut
  la garder dans III-8.1, où elle est belle, et dans III-2.1, où elle est la mesure. Pour III-8.3, voir § 4.
- Les valeurs E2M1 : III-1.1 imprime celles d'OCP (±6), III-8.1 celles de ggml (±12, table doublée). Le
  lecteur voit « 1111 → −12 » au chapitre 8 et « F → −6 » au chapitre 1. Il faut imprimer les valeurs d'OCP
  dans les deux et dire « ×2 dans la table de llama.cpp » dans la légende de III-8.1. Ou bien l'inverse,
  pourvu que les deux figures concordent.
- L'axe sans perte, à droite de III-7.1, refait en plus serré ce que III-8.5 montre. Voir G10.

## 3. Les graves

**G1. III-9.1 : une figure, deux codes de couleur.** Les panneaux (a) et (b), du lot construction, tracent le
synonyme en `SerieA` (bleu) et la frontière en `SerieF`. Le panneau (c), du lot latents, trace le synonyme en
`SerieB` (rouge) et la frontière en `black!50`. III-9.7 fait de même. Assemblée telle quelle, la figure
contredit sa propre clé (M7 du juge latents ; je le classe grave, car le lecteur lit (c) avec la clé de (a)).
**Changer**, dans `latents-figures.tex` :
- `\colorlet{latSynonyme}{SerieA}` et `\colorlet{latFrontiere}{SerieF}` ;
- les colonnes « codon changé » en `SerieA!10` au lieu du rose ;
- la ligne « synonyme » de la table du bas en `SerieA` ;
- en III-9.7, l'ellipse synonyme en `SerieA` et le nuage des entrées en `black!35`, pour qu'il ne se confonde
  pas avec elle.

**G2. III-7.6 : la couleur porte l'idée et s'efface pour un lecteur daltonien** (environ 8 % des hommes ont
une vision des couleurs anormale, littérature, non reproduit).
- Neuf teintes catégorielles sont posées sur 6 132 points qui se recouvrent.
- En vision deutéranope, 24 et 4 tombent à ΔE 9,2, et 12 et 21 à 7,3 : sur huit couleurs, il en reste
  environ quatre (rendu simulé, `z/l4d.png` du pilote).
- En gris, 24 et 4 sont à 1,9.
- La clé des tailles est invisible (pastilles de 0,85 et 0,42 pt, M3 du juge latents).
- La taille suit une marge qui ne marque pas les bords des couleurs (M2 du juge latents).

**Changer** (version légendaire) : des **petits multiples**.
- Une grille de 2 × 4 cartes t-SNE, une par expert premier parmi les huit, l'expert en couleur pleine sur le
  nuage entier en `black!12`.
- Au-dessus, la carte complète en gris, avec les seules frontières de voisinage.
- Chaque case dit son expert et sa part (22,0 %, 20,9 %…).
- L'ACP passe en encart, avec sa fidélité.

Version minimale : ne colorer que quatre experts (12, 24, 31, 23), avec quatre marques (cercle, carré,
triangle, losange) et des couleurs du dictionnaire séparées en vision deutéranope (`SerieA`, `SerieD`,
`Encre`, `SerieE`), le reste en gris.

Dans les deux cas : la taille passe à z(1) − z(2), ou disparaît. Elle ne doit pas rester une troisième
dimension que la légende n'explique pas.

**G3. III-9.3 : trois panneaux, deux échelles, sans le dire, et des points hors du cadre.**
- Les panneaux 1 et 3 vont d'environ −0,35 à +0,08, le panneau 2 d'environ −0,085 à +0,03 : près de quatre
  fois plus serré.
- À l'œil, les trois comparaisons ont la même ampleur. C'est faux : λ = 0 contre λ = 1 est quatre fois plus
  petit.
- La fenêtre 7 de R1 du panneau 2 manque, et c'est celle que la légende cite (G1 du juge construction).

**Changer** :
- un axe commun aux trois panneaux, de −0,36 à +0,08. Le panneau 2 se lit alors petit, et c'est la vérité ;
- si l'on garde deux échelles, un bandeau « échelle × 4 » dans le panneau 2 et la même graduation 0,05 marquée
  dans les trois ;
- `clip mode=individual` et, pour un point hors cadre, une flèche au bord avec sa valeur (« fen. 7 :
  +0,061 → »).

**G4. III-9.2 : en noir et blanc, la frontière et les deux synonymes sont un seul trait.** Le ΔE en gris entre
la frontière et λ = 0 est de 0,9 ; λ = 1 et λ = 0 sont presque superposés. Or l'idée de la figure est l'écart
entre la frontière et les synonymes. De plus, deux décades sur cinq (10⁻⁴ à 10⁻²) sont vides, P = 1 partout :
40 % de la largeur ne montrent rien.

**Changer** :
- la frontière en trait plein de 1,3 pt, λ = 1 en tirets, λ = 0 en tiret-point, Q2_0 en pointillés ;
- l'axe de 10⁻² à 10¹ ;
- les médianes et les 99,9es centiles marqués de la forme de la série, plutôt qu'en points gris foncés communs ;
- un trait de rappel horizontal « ÷ 3 » entre la médiane de la frontière et celle de λ = 1, qui est l'idée ;
- la légende, réécrite selon G4 du juge construction (3 positions).

**G5. III-7.4, en anglais : la légende cache le chiffre de la figure.**
- Le cadre de légende, opaque à 92 %, recouvre « ×334 » dans « strand ×334 ». C'est l'annotation qui porte le
  titre (« la colonne géante aspire l'erreur du brin »).
- Dans les deux langues, les icônes de légende sont des traits de 0,35 pt : à l'impression, les trois séries
  se lisent noires (agrandi à 500 dpi, elles sont bien colorées).
- En vision deutéranope, base et S\* se confondent (ΔE 19,0).
- « S\* ×1,05 » flotte près de 10⁻¹, loin de sa courbe.

**Changer** :
- supprimer la légende et étiqueter chaque courbe à son extrémité droite, avec le halo du § 2.3 ;
- S\* en `SerieE` (dictionnaire) ;
- `legend image post style={line width=1.2pt}` si une légende reste ;
- « ×334 », « ×14 » et « ×1,05 » posés contre le pic, chacun dans la couleur de sa série.

**G6. III-8.6 : quatre idées dans une figure, et deux titres qui se chevauchent.**
- Les quatre panneaux portent deux modèles, deux étages et deux séances :
  - (a) la dispersion ABBA ;
  - (b) les octets n'expliquent pas le gain ;
  - (c) le motif de lecture croisé ;
  - (d) la cascade.
- La légende fait seize lignes. C'est la figure de R1, la plus importante du chapitre 8, et elle ne se lit pas
  du premier coup d'œil.
- En français, « (c) même fichier, autre motif de lecture (20b, étage disque) » chevauche « encart (120b) :
  deux v1.0 égaux au bit ».
- Le fond (motif) et le contour (fichier) de (c) demandent un décodage. Les cercles des quatre passes sont
  presque invisibles.

**Changer** : scinder en deux figures.
- **III-8.6** « Ce que le J1 mesure » : (a) et (b). Un modèle, une séance.
- **III-8.6 bis** « D'où vient le gain » : (c) avec son encart, puis (d).
  - Dans (c), une seule clé : l'abscisse dit le fichier et la couleur le motif, sans contour. Les passes
    passent en marques noires de 1,6 pt.
  - L'encart prend son titre sous son cadre.
  - Dans (d), le motif s'écrit « ≥ ×1,394 » (juge construction) ; les couleurs suivent le dictionnaire
    (v1.0 `black!35`, v1.2 `Echelle`, compagnon `SerieF`).

  Le 20b et le 120b se partagent ainsi la figure par panneau, et la légende le dit en tête.

**G7. III-9.6 : l'idée tient dans 5 % de la largeur.** La frontière, λ = 1 et λ = 0 sont entre 2,58 et
2,67 bits, sur un axe de 2,15 à 3,95 : environ 5 % de la largeur. La flèche « domine » fait 3 mm. Le moteur
exact et Q2_0, simples repères, occupent tout le cadre.

**Changer** : le cadre principal de 2,54 à 2,72 bits et de 0,08 à 0,35 en KL (logarithmique), avec les trois
variantes, leurs barres ±2σ et la flèche « domine sur les deux axes ». Q2_0 et le moteur exact passent en
repères de marge : une flèche au bord de chacun, avec ses bits et sa KL. Ces nombres se tirent du fichier que
le script écrit déjà (`synonyme-nombres.tex`), aucun n'est tapé. À défaut, il faut un encart agrandi.

**G8. III-4.8 : l'arbre ne se lit pas comme un arbre.**
- La MDS (30,9 % de la variance) place les nœuds. Les arêtes de l'arbre couvrant se croisent alors
  (10 → 4, 8 → 9 → 12, 16 → 28).
- Les deux arêtes les plus lourdes sont cachées sous leurs disques (D5 du juge ronde), et l'amas
  5-15-17-25-31 se recouvre.
- L'idée annoncée, « l'ordre de codage le moins cher », demande de suivre un chemin, ce que la projection
  empêche.

**Changer** :
- dessiner l'arbre par une disposition d'arbre, radiale autour du moyeu 31 ou étagée par la profondeur
  depuis 31 ;
- garder l'épaisseur et le bleu des arêtes, mais dessiner les arêtes **au-dessus** des disques, ou réduire les
  disques à 3 pt ;
- la MDS passe en encart, avec sa fidélité (30,9 % ; Spearman 0,61 ; témoin 0,11), pour dire « voici
  l'ombre ».

Le fond `Fond` arrondi est le seul des 28 figures : il faut le retirer.

**G9. L'ensemble : trois conventions de légende.**

| | construction | ronde | latents |
|---|---|---|---|
| titre court (table des figures) | `\Titre…` | **aucun** : la table affiche « III-1.1 » | `\LegendeCourte…` |
| phrase de tête en gras (l'idée) | non | oui | non |
| étiquette de provenance | aucune | « [mes.] » en noir, tapé | `\mes` (vert) |
| sources | dans le texte de la légende | `\sourcefig` dans la légende, aligné | `\sourcefig` hors de la légende, **centré** |

Dans un même chapitre (le 9 réunit les lots construction et latents), deux légendes voisines n'ont ni la
même forme ni la même place pour la source.

**Décision (réponse par délégation du 2026-10-27, réversible ; raison : la phrase de tête est l'idée de la
figure, et la donnée a sa ligne)** : on adopte la forme du lot ronde, en ajoutant le titre court. Chaque
figure définit :
- `\Titre<Lot><Nom>` : le titre court de la table des figures ;
- `\Legende<Lot><Nom>` : la légende ; elle s'ouvre sur sa phrase de tête en gras, qui est l'idée,
  suivie de `\mes`, `\calc` ou `\litt` du préambule, jamais tapés ;
- `\Source<Lot><Nom>` : la source, appelée par `\sourcefig` **dans** le `\caption`, alignée à gauche.

Le chapitre écrit
`\caption[\Titre…]{\Legende…\sourcefig{\Source…}}`. Ce que cela demande :
- au lot ronde, onze titres courts ;
- au lot construction, des phrases de tête et des sources sorties du texte ;
- au lot latents, le renommage de `\LegendeCourte` et la source entrée dans la légende.

**G10. III-7.1 : la figure de synthèse porte deux figures et une clé à deux dimensions.**
- À gauche, la frontière avec perte ; à droite, l'axe sans perte, qui est déjà III-8.5 et III-8.3.
- La légende du haut croise protocole (forme et couleur) et verdict (remplissage) en six entrées. Celle de
  droite en ajoute cinq, posée sous le panneau, loin de lui.
- Les étiquettes se chevauchent : « élagage (e, q) » sur sa flèche, « S\* (erreur d'expert) » coupée par l'axe
  (D1 du juge ronde), « sa base ; D2b » sur une graduation.
- Le point S\* (K10) est caché sous le carré « les trois bases ».
- Le juge ronde fait déjà tomber la figure pour ses verdicts (son G1) ; le dessin la fait tomber aussi.

**Changer** :
- garder la frontière seule, le protocole par la forme et le verdict par le remplissage (§ 2.1), avec une
  légende d'une ligne ;
- l'axe sans perte devient une figure à part, ou rejoint III-8.5, dont il est le pendant tenseur par tenseur ;
- S\* décalé d'un demi-millimètre avec un trait de rappel ;
- la bande « sans KL » passe sous l'axe, avec ses étiquettes au-dessus de leurs losanges et le halo du § 2.3.

## 4. Figure par figure

Pour chaque figure : ce qu'elle dit au premier coup d'œil, ce qu'il faut changer, ce qui manque pour qu'elle
soit « légendaire » et ce qui est de trop. **G** renvoie aux graves (§ 3) ; **D1 à D31** sont les mineurs,
numérotés ici.

### Ch. 1-2 (lot ronde)

**III-1.1, le bloc MXFP4.** Tient : un schéma net, aux couleurs sémantiques du préambule (S, E, M, échelle).
- D1. « échelle » et « qs[16] » se touchent (D3 du juge ronde) : décaler l'accolade de l'échelle de 2 mm.
- D2. Le trait pointillé du zoom traverse le « 1 » de la ligne des octets : faire partir le zoom sous les
  numéros.
- Valeurs OCP contre ggml : voir § 2.5.
- Manque : rien.

**III-1.2, la borne distorsion-débit.** Tient. Les deux flèches (×0,43, −0,48 bit) portent l'idée.
- D3. La base frontière passe en losange gris foncé (dictionnaire) ; les deux flèches gardent `Encre` ; le
  rouge s'en va.

**III-2.1, le signe des zéros.** Tient : l'idée (plat à 0,125, sauf la couche 0) se lit tout de suite.
- D4. Icônes de légende en pastilles doubles à halo (§ 2.3) : `area legend`. Graduations du haut hors du cadre.
- Les titres des deux panneaux passent au style de panneau (§ 2.3).

### Ch. 3-4 (lot ronde)

**III-3.4, le brin sur une gaussienne.** Tient : les panneaux avec résidu (écart en dB sous la courbe) sont le
bon dessin. Bleu et violet sont proches en vision deutéranope (ΔE 7,3), mais le plein et le creux les séparent.
- D5. « (5,2) » touche la courbe (D9 du juge ronde). Le témoin T1, un losange rouge de 2 pt sur un carré
  bleu, ne se voit qu'agrandi : le passer en croix `Encre` décalée, avec son trait de rappel.
- Il faut aussi des titres de panneau (« (a) erreur contre débit », « (b) longueur de fenêtre ») au lieu de
  « à gauche / à droite ».

**III-3.6, débit-distorsion par tenseur.** Tient, et c'est le plus beau graphe de mesure du flux : douze petits
multiples, une flèche par case, l'exception (couche 8, down) visible d'elle-même.
- D6. Les titres de la colonne « down » sont plus bas que les autres : le nœud est ancré au sud et « down »
  n'a pas de jambage. Il faut `text depth=0.25ex` ou une ancre `base`.
- « 3,00 » et « 2,00 » se touchent aux jointures des cases : ne pas imprimer la graduation 3,00 des deux
  premières colonnes.
- Losange de la base en gris foncé (dictionnaire).

**III-4.2, le score de parenté.** Tient : 880 points loin sous le témoin planté, l'idée est immédiate.
- D7. La légende en bas à gauche recouvre la ligne du hasard : la sortir au-dessus du cadre.
- Le témoin du hasard ne se trace que sur la couche où il a été mesuré, la 12 (M3 du juge ronde).
- Le témoin planté passe en `Encre` tiret-point (dictionnaire).

**III-4.8, l'arbre des experts.** **Tombe** : G8.

### Ch. 7 (lots ronde et latents)

**III-7.1, la frontière commune.** **Tombe** : G10.

**III-7.2, l'erreur d'expert ne prédit pas la KL.** Tient : la bande verticale « même erreur d'expert » contre
l'étalement vertical, c'est l'idée en un regard. Le S\* à 3 fenêtres barré, avec sa flèche vers K10, est un
beau geste de vérité.
- D8. Trois étiquettes traversées par un trait (§ 2.3).
- Le protocole passe à la forme seule (§ 2.1).
- L'abscisse 0,25 à 4 est en log 2 : graduer 0,25, 0,5, 1, 2, 4, comme aujourd'hui, mais avec la grille
  mineure retirée.

**III-7.3, deux parts de la KL.** L'idée (la masse passe sous la diagonale, le coin haut y reste) tient, mais
la couleur par fenêtre n'apporte rien : dix teintes sur 2 550 points, ramenées à quatre environ en vision
deutéranope (D6 du juge ronde).
- D9. Points en `black!40` à opacité 0,5 ; seules les positions au-dessus de 0,3 (la queue) restent colorées
  par fenêtre.
- L'encadré « part lisse / queue » se pose hors du nuage (en haut à gauche du cadre, il recouvre des points).
- La clé « fenêtre » remonte sous le titre de l'axe.

**III-7.4, la colonne géante.** **Tombe en anglais** : G5. En français, l'idée se lit, mais la légende a le même
défaut d'épaisseur.

**III-7.6, l'espace latent des états.** **Tombe** : G2.
- C'est la figure où la demande du 2026-10-17 (« des modélisations d'espace latent ») se joue le plus. Les
  petits multiples en feraient la plus belle du tome.

### Ch. 8 (lot construction)

**III-8.1, la roue des seize codons.** Tient, et elle est belle : le pliage de la droite en cercle, l'arc
« synonymes », le rayon fondu deux fois plus épais.
- D10. En vision deutéranope, l'orange des zéros et le rouge des négatifs se rapprochent (ΔE 28 au lieu
  de 46). La position et l'arc sauvent la lecture ; une bordure `Encre` de 0,4 pt sur les deux rayons des
  zéros la rendrait sûre.
- La flèche « 8 → 0 fondu » passe en `Encre` (le rouge est le signe).
- La boîte trop pleine de 4,4 pt se résout par une largeur de 0,97\linewidth.

**III-8.2, la carte des 256 octets.** Tient.
- D11. Il manque l'échelle de couleur, et « absent » (ligne 8 éteinte) a la couleur de « rare » (lignes 7
  et F pâles). Il faut une barre de couleur log₁₀(1 + f) et les cases d'effectif nul hachurées en `black!25`.
- Les titres passent au style de panneau.

**III-8.3, le théorème tenseur par tenseur.** L'idée (sur la diagonale) se lit, mais la diagonale ne montre
que l'identité. La plupart des 180 points s'empilent entre 0,115 et 0,135, et l'écart réel (±0,00017) est
invisible.
- D12. Ajouter, sous le graphe, un panneau de résidus (mesuré − prédit, en 10⁻⁴ bit, contre le prédit). C'est
  là que le théorème se voit tenir.
- `fixed zerofill`.

**III-8.4, l'accumulateur.** Tient : la machine à états est claire, et l'état « −0 » en fantôme est une belle
idée.
- D13. La cassure ne se voit pas : une case rouge de la petite grille, invisible à l'impression. Il faut
  agrandir la petite grille ou peindre toute la ligne 0 en `Encre` avec une croix, et poser l'étiquette
  « la ligne 0 diffère » contre elle.
- Le titre gras du panneau de droite touche l'étiquette de la boucle « ν ≠ 0, somme exacte ≠ 0 » : il faut un
  titre au panneau de gauche aussi (« (a) les états de l'accumulateur », « (b) 8 640 lignes, 0 différente »),
  sur une même ligne de base.
- Les deux nœuds de légende se touchent en anglais.
- Césure dans « ex-pert ».

**III-8.5, pourquoi la colonne reste dehors.** Tient.
- D14. « 0,1279 » chevauche le cadre de l'encart : `clip=false` avec `xmax=0,17`, ou la valeur dans la barre.
- « À la même échelle » est faux à l'œil : mêmes unités, mais pas même longueur (0,15 bit vaut environ 4,2 cm
  à gauche et 3,5 cm dans l'encart, mesurés sur le rendu à 100 dpi). Égaliser les longueurs, ou écrire « dans
  les mêmes unités ».
- Le seuil passe en `Encre` tirets, et la graduation du haut ne doit plus sortir du cadre.

**III-8.6, le J1.** **Tombe** : G6.

**III-8.7, le format v1.2 au bit près.** Tient : un schéma propre, les champs changés surlignés, le chemin d'un
demi-octet.
- D15. Casse des titres (§ 2.3) ; « L, E, k... » et « ... » à écrire « … » ; « bits des drapeaux (6 à 31 : 0) »
  à écrire « bits des drapeaux (6 à 31 nuls) ».
- La mini-table CODES_CTX gagnerait la croix éteinte de la ligne et de la colonne 8 en `black!25`, comme
  III-8.2 corrigée.
- Césures (§ 2.3).

**III-8.8, le codon par le juge.** L'idée (−0 à 6,3 % partout, sans dépendance à la profondeur) tient. Le
titre « avant et après » ne correspond à rien de visible.
- D16. Le point à 11,68 % hors de l'axe (G2 du juge construction) : axe de 4 à 12 %.
- Les deux tirets des parts du fichier (6,39 et 6,28 %), bleu et rouge à 0,1 point d'écart, se confondent en
  gris : en garder un seul par modèle, étiqueté au bout.
- Le texte blanc `\tiny` dans les barres passe sous les barres, en `\scriptsize`.
- L'axe de (b) dit « bit » : il faut « bit/poids ».
- Titre : « Le codon par le décodeur du juge ».

### Ch. 9 (lots construction et latents)

**III-9.1, la base propre de H.** **Tombe** : G1, pour la figure assemblée.
- D17. (a)(b) et (c) n'ont pas le même pas de graduation : 500 en (a) et (b), 200 en (c), soit quinze
  étiquettes. Il faut un pas de 500 partout, et la zone grise « muettes » au même endroit dans les trois
  panneaux.
- L'annotation de (c) est traversée par la courbe pointillée, et elle est fausse (G3 du juge construction) :
  à retirer, ou à réécrire avec le halo.
- Le panneau (c) des latents (la rangée de 32 poids) est la plus belle figure de transformation du flux,
  avant et après d'un seul regard.
- D18. Il faut la notation « ±0 » et les flèches expliquées dans la légende (M6 du juge latents).

**III-9.2, la queue de la KL.** **Tombe** : G4.

**III-9.3, B2 fenêtre par fenêtre.** **Tombe** : G3. Le reste est bien pensé : R1 et neuves en bandes nommées,
cercles contre losanges, bande ± 2σ.
- D19. Les numéros des fenêtres en `\tiny` passent à `\scriptsize`. « fenêtre », au milieu des deux groupes,
  se lit comme une étiquette de groupe : à mettre sur l'axe.

**III-9.6, les variantes à 768 experts.** **Tombe** : G7.

**III-9.7, le nuage des entrées et les ellipses.** Tient pour la justesse, mais se lit mal.
- Les ellipses sont centrées à l'origine et le nuage à u₁ᵀx ≈ 16,5. L'œil compare donc deux choses qui ne sont
  pas au même endroit.
- Le nuage s'étale le long de u₂, là où l'ellipse synonyme s'allonge : on peut lire l'inverse de la légende
  (M8 du juge latents).
- D20. Deux sorties :
  - tracer les ellipses en **fonction d'appui** ‖ΔW v‖ en coordonnées polaires, avec la direction des
    entrées en rayon gris ;
  - ou garder le plan, mais ajouter en sur-impression, sur le nuage, la **direction moyenne** des entrées et
    l'erreur synonyme le long de u₁, u₂ et u₃ en trois barres (0,082 ; 0,217 ; 0,269, rapportées à la
    frontière).
- Couleurs : G1.
- Le petit « 0 » de l'origine est `\tiny`.
- Manque pour « légendaire » : la version 3D (u₁, u₂, u₃, ellipsoïdes) que l'inventaire prévoit. C'est elle
  qui montrerait l'aplatissement d'un seul regard.

### Ch. 10 (lot construction)

**III-10.1, les experts vus.** L'idée (11 experts jamais jugés) est noyée.
- 732 cases sur 768 sont vertes, et leur intensité (log des appels) fait un bruit de fond qui attire l'œil
  plus que les exceptions.
- En vision deutéranope et en gris, « R1 seul » et « neuves seules » se confondent (ΔE 3,0 et 1,5).
- Les croix rouges sur cases blanches sont petites.
- D21. Les cases « les deux » passent en `black!8` à `black!35` selon le log des appels. « R1 seul » et
  « neuves seules » deviennent `SerieA` et `SerieE` pleins, avec un point blanc dans les seconds pour le
  noir et blanc. Les 11 cases vides reçoivent un cadre `Encre` de 0,6 pt et une croix noire.
- Ajouter le compte en marge de chaque ligne (experts non vus par couche).

**III-10.3, la difficulté des fenêtres.** Tient : l'idée (une difficulté commune à toutes les variantes, le mode
exact deux décades plus bas) survit au noir et blanc, même si les trois variantes s'y confondent.
- D22. Des marques distinctes (frontière cercle, λ = 1 carré, λ = 0 losange, mode exact triangle) rendent les
  variantes lisibles en gris.
- Le fond des fenêtres neuves passe en `SerieE!6`, la teinte des neuves en III-9.3, au lieu du gris, qui veut
  dire « hors domaine » (§ 2.1).
- Les lignes qui joignent les fenêtres, catégories sans ordre, sont justifiées par l'idée (parallélisme) :
  les garder à 0,5 pt et le dire dans la légende.

### Mineurs d'ensemble (D23 à D31)

- D23. Dictionnaire des couleurs (§ 2.1) à poser dans un fichier commun du Tome III
  (`memoire/figures/tome3/palette-tome3.tex`, `\colorlet` nommés : `T3Frontiere`, `T3Synonyme`…), chargé
  avant les lots.
- D24. Style des titres de panneau et d'encart (§ 2.3).
- D25. Corps plancher `\scriptsize` (§ 2.3).
- D26. `fixed zerofill` sur toutes les graduations décimales (§ 2.3).
- D27. Graduations du haut hors du cadre (§ 2.3).
- D28. Halo blanc sous toute étiquette posée dans un graphe (§ 2.3).
- D29. Césures interdites dans les nœuds (§ 2.3).
- D30. Typographie anglaise (§ 2.4).
- D31. Valeurs E2M1 cohérentes entre III-1.1 et III-8.1, et la pièce du signe sans redite (§ 2.5).

## 5. Ce qui pourrait être faux

- Le jugement du dessin est le mien. Ce qui est chiffré : les ΔE, les recouvrements vus agrandis, les parts
  d'axe et les échelles. Le reste est un goût argumenté : « plus beau », « légendaire », le choix des petits
  multiples ou de la disposition d'arbre.
- Les seuils de lecture du § 2.2 (ΔE 5 en gris, ΔE 10 en vision deutéranope) ont été posés **après** avoir vu
  les rendus simulés, à la frontière entre les paires que l'œil y séparait et celles qu'il ne séparait plus.
  Ils ne sont pas déclarés d'avance et ne dérivent pas d'une grandeur mesurée sur des lecteurs. Les ΔE
  eux-mêmes ne dépendent pas de ce choix.
- La simulation de Machado est un modèle (sévérité 1, dichromatie complète) ; une vision anormale partielle
  confond moins. Le ΔE CIE76 surestime les écarts des bleus saturés. Les couleurs éclaircies (`!30`, `!50`)
  sont calculées par le mélange de xcolor avec le blanc, en sRGB non linéaire comme xcolor le fait.
- Les III-9.1 (a)(b) et (c) ne sont pas encore assemblées dans une même figure ; G1 juge l'assemblage annoncé
  par l'inventaire et par les légendes (« panneaux (a) et (b) »).
- Les figures déjà tracées par la piste tropicale (III-11.x) ont été compilées et regardées pour la cohérence
  du style. Elles suivent le style `memoire`, avec des titres de panneau maigres et du rouge pour la série
  principale. Elles ne sont pas jugées ici, et le dictionnaire du § 2.1 devra leur être proposé par le flux des
  pistes, qui en est le seul auteur (R6).
- Je n'ai pas compilé un chapitre réel : en `[p]` dans le pilote, une figure a sa page. Dans le texte, les
  figures de pleine largeur et les boîtes trop pleines de 2 à 4 pt peuvent se comporter autrement.
