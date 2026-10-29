# Tome III, second flux de figures : le jugement de design

Juge de design du second flux (SOCLE, demande de Stone du 2026-10-17 : « la beauté à égalité avec la justesse »).
Je n'ai tracé aucune figure et je n'en modifie aucune. Je relis ce que le second flux a changé : le commun
(`palette-tome3.tex`, `legende-tome3.tex`, `CONVENTIONS-figures.md`) et les trois lots (construction, ronde,
latents), contre le premier jugement de design (`JUGEMENT-figures-design.md` : dictionnaire § 2.1, G1 à G10,
D1 à D31). Les chiffres sont l'affaire des trois juges des chiffres du second flux ; je m'appuie sur leurs
verdicts quand un défaut de dessin rend un chiffre faux à l'œil.

**État jugé** : `main` à 3f92adc (figures à 326969f, 6292203, 4229a02 ; commun à e1b89f5).

**Ce document est écrit en deux temps.** Le premier commit ne porte que le § 1 (les seuils et les critères,
déclarés avant toute lecture des rendus). Le verdict et le reste suivent dans un commit séparé.

## 1. Seuils et critères, déclarés avant la lecture des rendus

Déclarés le 2026-10-27, avant d'avoir compilé un pilote ni regardé une page rendue du second flux. Je n'ai lu
jusqu'ici que les sources Markdown (jugements, reprises, conventions), `palette-tome3.tex`, `legende-tome3.tex`,
les quatre pilotes en source et le CSV des paires du commun.

### 1.1 Les seuils de couleur

- **Distance** : ΔE CIE76 dans CIELAB (D65), comme le premier juge et le commun, pour que les tableaux se
  comparent. Vues : gris (luminance relative), deutéranope (Machado, Oliveira et Fernandes 2009, sévérité 1).
  Le protanope est chiffré, mais ne décide pas.
- **Seuils** : une paire de couleurs que la figure demande de séparer **tient par la couleur** si
  **ΔE ≥ 5 en gris** et **ΔE ≥ 10 en vision deutéranope**.
  - D'où ils viennent : ce sont les seuils du premier juge (§ 2.2), lus par lui sur 17 paires rendues en
    simulation, à la frontière entre les paires que l'œil séparait et celles qu'il ne séparait plus. Le
    commun les a repris pour ajuster la palette. Les garder rend mes verdicts comparables aux leurs.
  - Ce qui est neuf : ils sont déclarés ici **avant** ma lecture ; le premier juge les avait posés après.
  - Leur borne basse : le seuil de discrimination couramment donné pour ΔE CIE76 est de 2,3 (littérature,
    non reproduit) ; 5 en vaut un peu plus du double, pour des traits et des marques d'un millimètre, plus
    durs à séparer qu'un aplat. C'est une raison, pas une dérivation : aucun lecteur n'a été mesuré.
- **Deux mesures, pas une.**
  - **Nominale** : les couleurs que les sources nomment, résolues comme le fait xcolor (fonctions de l'outil du
    premier juge, `outils/genome/tome3/juge-design/palette.py`, appelées sans modification).
  - **Rendue** : les couleurs lues dans les pixels des pages rendues (cœur des traits et des aplats, après
    lissage), par un outil écrit pour ce jugement. Un trait fin ou une opacité partielle rapprochent deux
    couleurs ; c'est la valeur rendue qui décide quand les deux diffèrent.
- **Le second canal.** Une paire qui tombe aux seuils **tient quand même** si la figure la sépare par un second
  canal visible sur le rendu en gris à 300 dpi : une marque différente, un trait différent (tirets contre
  plein), une étiquette directe posée contre la série, ou la place (panneau, position). Elle **tombe** si la
  couleur porte seule la distinction.
- **Témoins** (déclarés avant, chacun doit pouvoir tomber) :
  - TD1 : un gris pur reste gris sous la matrice deutéranope (|a\*|, |b\*| < 0,5) ;
  - TD2 : la paire rouge-vert `Signe` / `SerieC` tombe sous la moitié de son ΔE normal en vision deutéranope ;
  - TD3 : l'outil de rendu retrouve, sur une page rendue du nuancier du commun, la couleur nominale d'au moins
    un aplat à ΔE < 2 (vision normale), et ses vues gris et deutéranope à ΔE < 2 des vues nominales ;
  - cassure : matrices remplacées par l'identité ; TD2 doit tomber, et TD3 en deutéranope aussi.

### 1.2 Les autres seuils de lecture

- **Lecture** : chaque page des huit PDF (quatre pilotes, deux langues), en planches à 70 à 100 dpi, puis chaque
  figure agrandie de 200 à 400 dpi, en couleur, en gris et en deutéranope. Je ne retiens qu'un défaut vu
  agrandi (leçon du premier juge).
- **Chevauchement** : une étiquette traversée par un trait qui n'est pas le sien, ou qui en touche une autre, est
  un défaut (une phrase barrée veut dire « contredite », SOCLE). Vu à 300 dpi au moins.
- **Corps** : aucun texte de figure sous `\scriptsize` (plancher D25), vérifié dans les sources (`\tiny`) et à
  l'œil.
- **Compilation** : 0 erreur propre aux figures, 0 boîte trop pleine, 0 renvoi indéfini, dans les deux langues.
  Les 6 erreurs du préambule commun sous MiKTeX 26.5 (thmtools, relevées par le juge latents) sont hors des
  figures ; elles se comptent à part et ne font tomber aucune figure.

### 1.3 Ce qui lève chaque grave du premier jugement

| Grave | Levé si |
|---|---|
| G1 (III-9.1, III-9.7) | le synonyme est `CouleurSynonyme` et la frontière `CouleurFrontiere`/`…Marque` dans tous les panneaux, en source et au rendu |
| G2 (III-7.6) | en gris et en deutéranope, l'identité de chaque expert se lit sans la couleur (place, panneau, nom) ; la taille a disparu ou est dite |
| G3 (III-9.3) | les trois panneaux ont la même échelle, ou un écart d'échelle dit dans la figure ; aucun point hors du cadre |
| G4 (III-9.2) | frontière, λ = 1, λ = 0 et Q2_0 se séparent sur le rendu en gris par le trait ; les décades vides sont retirées |
| G5 (III-7.4) | en anglais comme en français, aucun nombre caché ; icônes ou étiquettes directes lisibles ; S\* violet |
| G6 (III-8.6) | la figure est scindée ; aucun titre ne chevauche un autre, dans les deux langues |
| G7 (III-9.6) | l'étendue des trois variantes (barres ± 2σ comprises) couvre plus de la moitié de la largeur du cadre, mesurée sur la source et sur le rendu |
| G8 (III-4.8) | 0 croisement d'arêtes ; arêtes visibles hors des disques ; la MDS en encart avec sa fidélité ; fond `Fond` retiré |
| G9 (ensemble) | chaque figure des pilotes passe par `\LegendeFigure` (titre court, tête en gras, provenance par macro, source dans le `\caption`) ; la table des figures montre les titres courts |
| G10 (III-7.1) | la frontière seule ; une clé d'une ligne ; aucune étiquette chevauchée ; S\* visible |

Un grave levé dans une langue et pas dans l'autre n'est pas levé.

### 1.4 Le dictionnaire et la convention, « tenus partout »

- **Dictionnaire** : dans les huit fichiers `*-figures.tex`, aucune `SerieA` à `SerieF`, aucune valeur HTML ni
  couleur nommée de xcolor (`red`, `blue`…) pour une entité du dictionnaire ; une couleur hors dictionnaire est
  permise dans une seule figure si sa légende la dit. Une même entité a la même couleur et la même marque d'une
  figure à l'autre, au rendu.
- **Convention** : chaque axe en `t3 graphe` ou `t3 encart` ; graduations décimales à précision fixe ; toute
  étiquette posée dans un graphe avec halo ; titres de panneau au style `t3 titre panneau`.

### 1.5 « Légendaire »

Ce qui reste au-delà des graves et des mineurs est un goût argumenté, dit comme tel : une idée par figure, lue
au premier regard ; l'œil conduit vers ce que dit la tête de légende ; rien de trop. Ce jugement ne fait tomber
aucune figure à lui seul.

## 2. Verdict

**Le second flux a fait le gros du chemin : huit graves sur dix sont levés, et le Tome III a désormais une
seule langue de légende. Il n'est pas encore « légendaire » d'un bout à l'autre : deux graves restent ouverts
pour un défaut mécanique chacun, et un grave neuf d'ensemble est apparu, le bleu.**

- **Levés (8)** : G1, G2, G3, G4, G5, G6, G8, G9.
- **Non levés au critère déclaré (2)**, chacun pour un seul défaut, que règle un réglage :
  - **G7** (III-9.6) : les trois variantes couvrent 47,6 % de la largeur du cadre, pour un seuil déclaré de
    plus de 50 %. C'était 5 % au premier flux, et la hauteur est couverte à 84,3 % : l'idée se lit. Mais le
    seuil était déclaré, et il tombe ;
  - **G10** (III-7.1) : en français, le trait de la loupe barre « partitions κ, par tenseur ». C'est le seul
    reste de G10 : la frontière est seule, la clé tient sur une ligne et S\* est visible.
- **Grave neuf (1)** : **GD1, le bleu à douze sens.** Le premier jugement avait vu un rouge à neuf sens ; le
  dictionnaire l'a réglé, mais le même bleu `1F5C99` porte maintenant douze sens, dont six dans les huit figures
  du chapitre 8 (§ 4).
- **Mineurs neufs : 22** (DN1 à DN22, § 5).
- **Tombent en l'état, pour le dessin** : III-9.6 (G7), III-7.1 en français (G10), et l'**ensemble** pour le
  bleu (GD1). Aucune ne demande de mesure neuve. S'y ajoutent les figures que les juges des chiffres font tomber
  pour une phrase : III-8.5 et III-10.1 (juge construction, GN2 et GN1) et III-9.7 (juge latents, GN1). Le
  dessin de III-9.7 a sa part dans la sienne (DN15).
- **Le dictionnaire est tenu dans les sources** : aucune `SerieA` à `SerieF`, aucune valeur HTML, aucun
  `\tiny` dans les huit fichiers de figures. Il **ne l'est pas dans l'esprit** : la couleur `Accent` du
  préambule, de même valeur que `CouleurSynonyme`, entre dans sept figures sous son propre nom (GD1).
- **La convention de légende est tenue partout** : les 29 figures passent par `\LegendeFigure`, et les tables
  des figures montrent les titres courts. Il reste deux défauts d'ensemble : les nombres et les symboles
  mathématiques de 12 têtes sur 29 ne sont pas en gras (DN1), et les légendes sont longues, avec une médiane de
  239 mots (DN2).
- **Compilation** : les huit PDF (quatre pilotes, deux langues) compilent en deux passes, avec 0 erreur propre
  aux figures, 0 boîte trop pleine et 0 renvoi indéfini. Pages : 6, 14, 6 et 18 dans chaque langue. Chaque
  journal porte les 6 erreurs du préambule commun sous MiKTeX 26.5 (thmtools, `\c@proposition already
  defined`, relevées par le juge latents), hors des figures.

Le tableau des graves (§ 3), le grave neuf (§ 4), les mineurs (§ 5) et le figure par figure (§ 6) donnent le
détail.

## 2 bis. Méthode, et ce qui a été mesuré

- **Compilation** : les quatre pilotes ont été copiés tels quels sous `memoire/essai/juge2-design/` (dossier
  ignoré par git), pour ne pas toucher aux PDF des lots, puis compilés par `lualatex`, deux passes, en français
  et en anglais.
- **Lecture** : chaque page des huit PDF, en planches de 70 à 85 dpi. Chaque figure française en trois vues
  côte à côte (couleur, gris, deutéranope) de 110 à 200 dpi. Les détails agrandis de 300 à 400 dpi : III-1.1,
  III-3.6, III-4.2, III-4.8, III-7.1 (français et anglais), III-7.4 (anglais), III-7.6, III-8.4, III-8.6,
  III-9.1 (a)(b) et (d). Les pages anglaises sont lues en planches, puis agrandies là où le français avait un
  défaut.
- **Outils** : `outils/genome/tome3/juge2-design/`. Chaque outil appelle les fonctions de l'outil du premier
  juge (`juge-design/palette.py`) sans les modifier.
  - `vues.py` : les trois vues d'une zone de page ;
  - `couleurs.py` : les couleurs rendues d'une page et leurs distances. Témoins TD1 à TD3 tenus ; à la
    cassure, TD2 et TD3 tombent (`journaux/temoins.json`, `temoins-casse.json`). TD3 retrouve dans les pixels du
    nuancier l'aplat du signe, à ΔE 0,0, et ses vues gris et deutéranope, à ΔE 0,0 ; à la cassure, la vue
    deutéranope s'en écarte de 58,0 ;
  - `lot.py` : les paires rendues des 29 pages de figures (`journaux/rendu-paires.txt`, JSON par figure sous
    `journaux/rendu/`) ;
  - `cadres.py` : G8, les croisements d'arêtes, et G7, la part du cadre. Témoin : une croix fabriquée donne
    1 croisement ; à la cassure, elle en donne 0, et le témoin tombe (`journaux/cadres*.json`) ;
  - `tetes.py` : les têtes de légende qui portent un nombre ou un symbole hors du gras, et la longueur des
    légendes (`journaux/tetes.txt`).
- **Ce que disent les paires rendues.** Les couleurs rendues égalent les couleurs nominales, à ΔE < 3 pour chaque
  entité du dictionnaire. Aucune paire de séries que la figure demande de séparer ne tombe par la couleur seule,
  sauf trois :
  - la clé de III-9.7 : frontière contre rose des entrées, 3,0 en gris et 6,5 en deutéranope (DN15) ;
  - la bande « même erreur d'expert » de III-7.2 contre la zone gagnante : 1,1 en gris (DN11) ;
  - λ = 0 contre Q2_0 en III-9.6 : 3,0 en gris, séparés par la place et l'étiquette (tient).

  Les autres paires qui tombent sont des fonds pâles, des grilles et des gris de l'encre, que la figure ne
  demande pas de séparer.

## 3. Les graves du premier jugement

| Grave | Figure | Verdict | Ce qui le dit |
|---|---|---|---|
| G1 | III-9.1, III-9.7 | **levé** | synonyme en `CouleurSynonyme`, frontière en `CouleurFrontiere`/`…Marque` dans (a), (b), (b′), (d) et dans III-9.7, en source et au rendu (bleu `1F5C99` et gris `A7AFB8`/`363D44` relevés dans les pixels) |
| G2 | III-7.6 | **levé** | petits multiples : l'expert se lit par son panneau et son nom, sans la couleur ; la taille a disparu au profit de la marge, dite dans la clé. En gris, l'expert (`5A5A5A`) et les états fragiles (`1A1A1A`) restent séparés (ΔE ≈ 28), mais voir DN13 |
| G3 | III-9.3 | **levé** | un seul axe, de −0,36 à 0,08, dans les trois panneaux ; la fenêtre 7 de R1 est dessinée, mais sur le bord du cadre (DN18) |
| G4 | III-9.2 | **levé** | sur le rendu en gris, frontière en trait plein de 1,3 pt, λ = 1 en tirets, λ = 0 en tiret-point, Q2_0 en pointillés : quatre traits distincts ; axe de 10⁻² à 10¹ ; rappel « ÷ 2,66 » |
| G5 | III-7.4 | **levé** | en anglais, « strand ×334 » est visible, et aucun cadre de légende ne reste ; « ×334 », « ×14 », « ×1,05 » dans la couleur de leur série ; S\* violet ; traits de 1,2 pt dans les étiquettes. Voir DN9 |
| G6 | III-8.6 | **levé** | scindée en III-8.6 et III-8.6 bis ; aucun titre ne chevauche un autre, en français comme en anglais ; une seule clé dans (c) |
| G7 | III-9.6 | **non levé au seuil** | 47,6 % de la largeur (seuil : plus de 50 %), 84,3 % de la hauteur en échelle log (`journaux/cadres.json`). Correctif : `xmin` = 2,56 (53,5 %) ou 2,57 et `xmax` = 2,70 (65,8 %), étiquette de λ = 1 à droite de son point |
| G8 | III-4.8 | **levé** | 0 croisement sur les 31 arêtes (mon code, `cadres.py`, témoin tenu) ; arêtes visibles hors des disques ; MDS en encart avec sa fidélité ; fond `Fond` retiré. Voir DN7 |
| G9 | ensemble | **levé** | 29 figures sur 29 passent par `\LegendeFigure` ; titres courts dans les quatre tables des figures ; provenance par macro ; source dans le `\caption`. Restent DN1 et DN2 |
| G10 | III-7.1 | **non levé au critère** | en français, le trait de la loupe traverse « partitions κ, par tenseur », entre « par » et « tenseur » (vu à 400 dpi ; N1 du juge ronde). En anglais, le halo le cache. Correctif : partir du coin haut droit du rectangle de loupe, ou poser l'étiquette sous son triangle |

## 4. Le grave neuf

**GD1. Le bleu à douze sens.** Le dictionnaire donne au bleu `SerieA` (`1F5C99`) quatre sens, chacun doublé
d'une forme : synonyme λ = 1, gpt-oss-20b, fenêtres R1, catégorie A. Les lots y ont ajouté, par la couleur
`Accent` du préambule, qui a **la même valeur**, et par `CouleurCategorieA`, huit sens de plus :

| Figure | Ce que dit le bleu |
|---|---|
| III-2.1 | les tenseurs gate (catégorie A) |
| III-4.8 | les arêtes de parenté (`Accent!…`) |
| III-7.2 | la bande « même erreur d'expert » (`Accent!8`, texte `Accent!80!black`) |
| III-8.1 | les valeurs positives (rayons en `Accent`) |
| III-8.2 | la fréquence des octets (échelle `Accent`) |
| III-8.4 | l'état s = +0 (`Accent!8`) |
| III-8.5 | le contexte de colonne (`Accent`) |
| III-8.7 | les champs changés (`Accent!14`) |
| III-7.6, III-8.3, III-8.8, III-9.1 à III-9.7, III-9.3, III-10.1 | les sens du dictionnaire : expert du panneau, 20b, synonyme, R1 |

C'est le défaut que le premier jugement plaçait en tête (§ 2.1 : « un lecteur apprend une couleur une fois par
tome »), déplacé du rouge au bleu. Au chapitre 8, six figures sur huit font dire au bleu six choses : positif,
fréquence, +0, colonne, champ changé, 20b (III-8.1, III-8.2, III-8.4, III-8.5 et III-8.7 ; le 20b en III-8.3 et III-8.8). Au chapitre 9, le bleu dit λ = 1 en III-9.2 et R1 en III-9.3, dont
le premier panneau s'intitule « λ = 1 contre frontière » et trace R1 en bleu. La règle du dictionnaire (« une
couleur hors dictionnaire est permise à l'intérieur d'une seule figure ») est tournée : `Accent` n'est pas hors
dictionnaire, c'est le synonyme sous un autre nom.

**Correctif (aucune mesure).** Le bleu plein ne garde que les sens du dictionnaire. Les autres usages prennent
une teinte qui a déjà ce sens, ou l'encre :
- III-8.7 : les champs changés en `CouleurVunDeux!15`. Ce qui change, c'est la v1.2, et l'orange est sa couleur ;
- III-8.1 : les rayons positifs en `Encre!55`, les négatifs restant rouges (le signe) ;
- III-8.2 : l'échelle de fréquence en gris (`white` → `Encre`), comme une densité ;
- III-8.4 : l'état +0 en `black!6` ;
- III-4.8 : les arêtes en rampe d'encre (`Encre!25` à `Encre`) ; le bleu n'y désigne rien ;
- III-7.2 : la bande en contour tireté `Encre!45` sans aplat, ou en `black!6` sans hachures ;
- III-8.5 : la colonne en `Encre!60` (le codon du zéro garde l'orange) ;
- III-2.1 : gate, up et down en trois gris (`Encre`, `black!55`, `black!30`). La figure dit « plat sauf la
  couche 0 », pas « gate contre down ».

Un usage de plus que le bleu ne peut pas éviter se dit en légende. La paire neuve s'ajoute à `PAIRES` dans
`memoire/outils/tome3_palette.py` du commun.

## 5. Les mineurs neufs (DN1 à DN22)

D'ensemble :
- **DN1. Têtes en gras, nombres et symboles maigres.** 6 têtes portent un nombre écrit par une macro (`\num`,
  `\dupEntier`, macros de nombres) : III-8.2, III-8.3, III-8.6, III-4.8, III-8.8, III-10.1. 7 portent un symbole
  mathématique (λ, S\*, ±0) : III-1.1, III-8.1, III-8.6, III-9.3, III-9.6, III-7.1, III-7.4. Cela fait 12 têtes,
  III-8.6 ayant les deux. Au rendu, « ×1,454 »
  et « 3,4 % » sont maigres au milieu de la tête grasse de III-8.6, de même « 32 », « 23 » et « 31 » dans celle
  de III-4.8 (`journaux/tetes.txt`, vu à 350 dpi). Correctif dans `legende-tome3.tex` : `\boldmath` dans le
  `\textbf` de la tête, et `detect-weight` pour siunitx.
- **DN2. Les légendes sont longues.** En français, la médiane est de 239 mots, de 97 à 512 ; 9 légendes sur 29
  dépassent 300 mots, et celle de III-7.1 en compte 512. La convention a mis l'idée en tête, mais la légende
  porte encore la dérivation, les témoins et « ce que la figure ne montre pas ». Une légende « légendaire » dit
  l'idée, la clé de lecture, la provenance et la source ; le reste va au texte du chapitre, que la légende cite.
  À trancher au moment de rédiger les chapitres, pas avant.
- **DN3. Les hachures ont trois sens** : hors du domaine mesuré (III-9.1, dictionnaire), fréquence nulle
  (III-8.2, mini-table de III-8.7 ; c'était ma demande D11 au premier flux) et « refusé » (le bit 4 COLONNES de
  III-8.7). Je retire D11 : un octet absent est une mesure, pas un hors domaine. III-8.2 doit dire « absent » par
  une case blanche bordée d'encre, et III-8.7 « refusé » par un contour tireté (pas par un texte barré, qui
  veut dire « contredit »).
- **DN4. Un gris de fond sans hachures sert de surlignage** : la colonne 1 011 en III-7.4, le plancher de la
  couche 0 en III-4.2. Le dictionnaire réserve le gris de fond au hors domaine, toujours hachuré. Avec la règle
  des hachures, la confusion reste faible, mais un lecteur qui a appris « gris = hors domaine » hésite.
- **DN5. Le vert a trois sens** : λ = 0, « mieux que la base » (`Mant!12`) et, en III-8.4, « égal au bit »
  (`Mant!30`). Les deux derniers sont proches (« bon »), le premier ne l'est pas. Pour III-8.4 : `black!8`.

Figure par figure (le § 6 les situe) :
- **DN6. III-3.6** : le halo des valeurs (« −0,22 », « −0,21 »…) recouvre la pointe de la flèche qu'elles
  nomment. Il faut poser la valeur au-dessus du milieu de la flèche.
- **DN7. III-4.8** : les valeurs de lien sont posées sur leur arête (« 0,043 », « 0,024 », « 0,035 », N4 du juge
  ronde). « 0,036 » touche le disque 10, et « 0,023 » se lit entre deux arêtes (14–16 et 14–22). Il faut les
  poser à côté de l'arête, du côté extérieur.
- **DN8. III-7.1** : la clé dit « tombe » (« falls » en anglais), la légende dit « pire » (« worse »). Il faut un
  seul mot ; « falls » n'est pas de l'anglais pour ce sens.
- **DN9. III-7.4** : les étiquettes sont en colonne à droite, dans l'ordre brin, base, S\*, alors qu'à droite du
  cadre les courbes sont dans l'ordre inverse (S\* en haut, brin en bas). L'œil cherche une correspondance de
  place qui n'existe pas. Il faut poser chaque étiquette à la hauteur de la fin de sa courbe. Et deux pics bruns
  de même hauteur se voient, dont un seul est nommé (colonne 960 à ×310, N2 du juge ronde) : la tête dit « une
  colonne géante », l'œil en voit deux.
- **DN10. III-7.2** : l'étiquette « synonyme λ = 0 (P1) » déborde du cadre à gauche, et son halo coupe le trait
  du cadre. La virgule de « (e,ℓ,c) » est serrée, alors qu'en III-7.1 on lit « (e, ℓ, c) ».
- **DN11. III-7.2** : la bande « même bande d'erreur d'expert » (`Accent!8`) et la zone « meilleur en KL » sont
  au même gris (ΔE rendu 1,1). Leur recouvrement, en bas de la bande, ne se lit qu'à l'étiquette. Voir GD1.
- **DN12. III-7.3** : la dernière ligne de la clé, « communes aux deux : 10 sur 25 », laisse « 25 » seul sur sa
  ligne. Il faut une espace insécable.
- **DN13. III-7.6 (c)** : la tête dit que les états de petite marge « se tiennent sur les bords des groupes ».
  Dans les petits multiples, les points noirs de 0,6 pt se répartissent aussi au cœur des groupes bleus, et
  la tendance (0,70 contre 0,47, N4 du juge latents) ne se voit pas. En gris, à 130 dpi, le bleu et le noir de
  si petits points se fondent. Il faut un anneau noir autour des points fragiles, plutôt qu'un point plein.
- **DN14. III-7.6 (a)** : les numéros sont posés sur la région la plus dense : « 4 », « 24 », « 13 » d'une part,
  « 27 », « 31 » d'autre part, s'empilent, avec un halo gris sur un nuage gris (N3 du juge latents).
- **DN15. III-9.7** : dans la clé, « frontière » et « directions des 1 329 entrées » ont la même icône, un trait
  gris (ΔE rendu 3,0 en gris, 6,5 en deutéranope, 6,4 en vision normale). La rose doit avoir une icône de
  barre. Les cercles font environ 3 cm, sur une page à moitié vide. Surtout, le dessin dans le plan (u₁, u₂)
  porte la tête fausse (GN1 du juge latents) : la rose et les deux courbes montrent les projections, et rien ne
  dit que 72 % de la norme des entrées est hors des trois axes. La tête corrigée doit venir avec un dessin qui le
  montre, par exemple une barre « hors du plan » à côté de la rose.
- **DN16. III-9.1 (b)** : le titre de l'axe vertical, « e_k = ‖ΔW u_k‖² (moyenne par 60) », touche le cadre de
  (a). Il faut 4 mm de plus entre les panneaux. Les lettres (a), (b), (b′) ici et (d) dans le pilote latents,
  sans (c), restent à assembler (N12 du juge construction).
- **DN17. III-8.4** : D13 n'est qu'à moitié fait. La cassure a sa croix, mais la ligne 0 qui diffère ne se voit
  pas : la petite grille est uniformément verte. Il faut peindre la ligne 0 en `Encre`.
- **DN18. III-9.3** : la fenêtre 7 de R1 (−0,35) est dessinée sur le trait du cadre (`xmin` = −0,36) : la moitié
  du disque est sous le trait. Il faut `xmin` = −0,38, tiré des données comme aujourd'hui, avec une marge.
- **DN19. III-8.6 bis** : une figure à part dont les panneaux s'appellent (c) et (d). Il faut recommencer à (a)
  et (b), et dire « figure III-8.6 » pour le renvoi.
- **DN20. III-8.6** : deux petits panneaux sur une demi-hauteur de page. C'est la figure de R1 : elle gagnerait
  à occuper la largeur, (a) à 60 % et (b) à 40 %.
- **DN21. III-10.1** : la marbrure des 732 cases « les deux » (`black!8` à `black!35`) attire encore l'œil
  autour des 11 croix. Il faut resserrer la rampe à `black!5`–`black!20`.
- **DN22. III-3.4** : les formes (« (7,3) », « (5,2) », « (8,3) ») sont écrites à la verticale et se serrent.
  Il faut les écrire à l'horizontale, en deux rangs alternés.

## 6. Figure par figure : ce qui reste pour être « légendaire »

Chaque entrée dit le verdict de dessin, ce qui reste, puis, après « Légendaire », ce qui ferait la différence.
« Tient » veut dire : ni grave ouvert ni défaut qui trompe l'œil.

### Lot ronde (ch. 1 à 4 et 7)

- **III-1.1, le bloc MXFP4. Tient.** D1 et D2 faits (accolades, zoom sous les numéros), D31 fait (OCP
  au-dessus, llama.cpp ×2 dessous). Légendaire : déjà.
- **III-1.2, la borne. Tient.** D3 fait (losange gris foncé, flèches à l'encre). Légendaire : la clé en cadre
  pourrait céder la place à des étiquettes directes, comme en III-7.4.
- **III-2.1, le signe des zéros. Tient.** D4 fait (icônes simples, graduations dans le cadre). Reste GD1
  (gate en bleu). Légendaire : un seul gris pour les trois matrices ; la figure dit « plat ».
- **III-3.4, le brin sur une gaussienne. Tient.** D5 fait (témoin en anneau, titres (a), (b)). Reste DN22.
- **III-3.6, débit-distorsion par tenseur. Tient**, et reste le plus beau graphe de mesure du tome. D6 fait.
  Reste DN6.
- **III-4.2, le score de parenté. Tient.** D7 fait (clé hors du cadre, témoin de hasard sur sa couche).
  Reste DN4 (le plancher en gris non hachuré).
- **III-4.8, l'arbre des experts. Tient** : G8 levé. L'idée, une étoile autour de 31, se lit d'un regard.
  Restent DN7 et GD1 (arêtes bleues). Légendaire : il l'est presque. Avec des arêtes en rampe d'encre, le moyeu
  noir en serait le centre de gravité.
- **III-7.1, la frontière commune. Tombe en français pour G10** (un trait sur une étiquette). Reste DN8. La
  légende a 512 mots (DN2). Légendaire : la figure de synthèse du tome est à un réglage près.
- **III-7.2, l'erreur d'expert ne prédit pas la KL. Tient.** D8 fait (halos, forme seule). Restent DN10 et
  DN11.
- **III-7.3, deux parts de la KL. Tient.** D9 fait (nuage gris, queues marquées, encadré hors du nuage). Reste
  DN12.
- **III-7.4, la colonne géante. Tient** : G5 levé. Reste DN9, qui compte double : l'œil voit deux pics.

### Lot latents

- **III-7.6, l'espace latent des états. Tient** : G2 levé. Les petits multiples en font la figure d'espace
  latent que demandait Stone. Restent DN13 et DN14. Légendaire : un anneau aux états fragiles, et la figure
  dirait son second message aussi bien que le premier.
- **III-9.1 (d), la rangée de 32 poids. Tient** : G1 levé, notation ±k dite. Le synonyme couvre la frontière
  là où les deux sont égaux : seuls les coins du losange dépassent du disque, ce qui se lit « égaux » et tient.
  Légendaire : déjà, une fois assemblée avec (a) à (c).
- **III-9.7, l'erreur de sortie dans les directions des entrées. Tient pour le dessin** (G1 levé), **tombe pour
  sa tête** (juge latents, GN1), et le dessin y contribue (DN15).

### Lot construction (ch. 8 à 10)

- **III-8.1, la roue des codons. Tient**, toujours belle. D10 fait. Reste GD1 (rayons positifs en bleu).
- **III-8.2, la carte des 256 octets. Tient.** D11 fait (barre d'échelle, hachures), mais voir DN3 et GD1.
- **III-8.3, le théorème. Tient.** D12 fait (panneau de résidus) : c'est là que le théorème se voit tenir.
  Reste DN1.
- **III-8.4, l'accumulateur. Tient.** Titres (a), (b) faits, césures réglées. Restent DN17 et DN5.
- **III-8.5, la colonne. Tient pour le dessin** : D14 fait, l'encart est « dans les mêmes unités », (c) reçoit
  l'axe sans perte. Reste GD1 (la colonne en bleu). Elle **tombe pour une phrase** (juge construction, GN2).
- **III-8.6, ce que le J1 mesure. Tient** : G6 levé. Restent DN1 et DN20.
- **III-8.6 bis, d'où vient le gain. Tient.** La cascade (d) est nette. Reste DN19.
- **III-8.7, le format v1.2. Tient.** D15 fait pour l'essentiel. Restent DN3 et GD1 (le surlignage en orange
  dirait « v1.2 » par sa couleur même).
- **III-8.8, le codon par le juge. Tient** : D16 fait (axe à 12 %, valeurs dans les barres avec halo). Reste
  DN1.
- **III-9.1 (a)(b)(b′), la base propre de H. Tient** : G1 levé, D17 fait (pas de 500). Reste DN16.
- **III-9.2, la queue de la KL. Tient** : G4 levé. Légendaire : déjà.
- **III-9.3, B2 fenêtre par fenêtre. Tient** : G3 levé. Restent DN18 et GD1 (R1 en bleu sous un titre
  « λ = 1 contre frontière »).
- **III-9.6, les variantes à 768 experts. Tombe pour G7**, à 2,4 points du seuil. La flèche « domine sur les
  deux axes » et les repères de marge sont justes.
- **III-10.1, les experts vus. Tient pour le dessin** : D21 fait (R1 seul et neuves seules séparées en gris et
  en deutéranope par le point blanc ; croix encadrées ; compte en marge). Reste DN21. Elle **tombe pour sa tête**
  (juge construction, GN1).
- **III-10.3, la difficulté des fenêtres. Tient** : D22 fait, avec les marques du commun, pas celles de D22
  (décision du commun, que je tiens pour juste). Le fond des neuves est teinté. Légendaire : déjà.

### Le commun

- **Nuancier et figure des paires (pilote commun). Tiennent.** Ils ne vont pas au mémoire. Le nuancier montre
  ce que GD1 contredit : la palette est bonne, c'est son usage qui fuit.

## 7. Ce qu'il faut faire, par ordre de poids

1. **GD1** : rendre le bleu au dictionnaire, en sept fichiers de réglage, aucune mesure (§ 4).
2. **G7 et G10** : un cadre (III-9.6) et un trait (III-7.1).
3. **DN1** : `\boldmath` et `detect-weight` dans `legende-tome3.tex`. Une ligne du commun, effet sur 12 figures.
4. Les mineurs de lecture qui trompent : DN9 (deux pics, un nommé), DN15 (avec la tête de III-9.7), DN13,
   DN17.
5. Les autres mineurs.
6. Au moment des chapitres : DN2 (légendes à raccourcir) et l'assemblage de III-9.1.

## 8. Ce qui pourrait être faux

- **Les seuils** (5 en gris, 10 en deutéranope) sont ceux du premier juge, déclarés cette fois avant la lecture.
  Ils restent tirés d'une lecture de rendus simulés, pas d'une mesure sur des lecteurs. Le seuil de G7 (plus de
  50 % de la largeur) est le mien, déclaré avant ; à 47,6 %, l'idée de III-9.6 se lit. Je fais tomber G7 parce
  que le seuil était déclaré, pas parce que la figure trompe.
- **Les couleurs rendues** sont lues sur des rendus de `pdftoppm` à 200 dpi. Une couleur ne compte que si elle
  couvre au moins 120 pixels, et son nom est celui de la couleur nommée la plus proche, à ΔE < 3. Deux
  entités de même valeur (synonyme, 20b, R1, `Accent`) portent donc le même nom : c'est ce qui rend GD1 visible
  à l'outil, mais l'outil ne dit pas laquelle est dessinée. Le tableau de GD1 vient des sources.
- **GD1 est un jugement de lecture** : aucune figure ne contredit sa propre clé. Je le classe grave parce que
  c'est le défaut que le premier jugement mettait en tête, déplacé et non résolu, et qu'il touche six des huit figures
  du chapitre 8.
- **DN1** est vu au rendu dans deux têtes (III-8.6 et III-4.8). Les 10 autres sont déduites des sources, par
  `tetes.py`. Une macro qui compose son nombre en gras m'aurait échappé dans un sens ; une macro de texte qui ne
  compose pas de nombre, dans l'autre.
- **La lecture** des pages anglaises est faite en planches. Seules III-7.1, III-7.4 et III-8.6 sont agrandies en
  anglais, là où le français avait un défaut ou un grave du premier flux.
- **Je n'ai pas compilé un chapitre réel** : en `[p]`, chaque figure a sa page. DN20 (III-8.6 petite) peut
  changer dans le texte.
- **Les 6 erreurs du préambule** (MiKTeX 26.5) laissent `lualatex` continuer en mode `nonstopmode`. Je n'ai pas
  vérifié qu'un préambule réparé rend les mêmes pages au pixel près.

## 9. Comment refaire

```
# compiler (depuis memoire/essai/juge2-design/, copies des pilotes) : FR puis EN, deux passes
lualatex -interaction=nonstopmode pilote-tome3-<lot>.tex
lualatex -interaction=nonstopmode -jobname=pilote-tome3-<lot>-en "\def\ANGLAIS{1}\input{pilote-tome3-<lot>.tex}"
# depuis la racine du dépôt
python -I -X utf8 outils/genome/tome3/juge2-design/couleurs.py temoins memoire/essai/juge2-design/pilote-tome3-commun.pdf 4 [--casser]
python -I -X utf8 outils/genome/tome3/juge2-design/lot.py memoire/essai/juge2-design
python -I -X utf8 outils/genome/tome3/juge2-design/cadres.py [--casser]
python -I -X utf8 outils/genome/tome3/juge2-design/tetes.py memoire/figures/tome3
python -I -X utf8 outils/genome/tome3/juge2-design/vues.py PDF PAGE DPI x0 y0 x1 y1 sortie.png [couleur,gris,deuter]
```
