# Jugement du second flux : figures du Tome III, lot « construction » (ch. 8 à 10), après corrections

Juge indépendant des chiffres, 2026-10-27. Je n'ai rien tracé. Règles : SOCLE (dont la demande de Stone du
2026-10-17, « la beauté à égalité avec la justesse »), `memoire/tome3/INVENTAIRE-figures.md` (réserves R1 à R6),
les jugements du premier flux (`JUGEMENT-figures-construction.md`, graves G1 à G5 et mineurs M1 à M16 ;
`JUGEMENT-figures-design.md`, dictionnaire § 2.1, G9, graves de dessin du lot G3, G4, G6, G7, mineurs D10 à D22).
Objet jugé : les commits du lot `3275a6c` (figures, scripts, données), `cadf276` (note pour le mémoire) et
`4229a02` (typographie anglaise, réglages). Leurs fichiers n'ont pas bougé jusqu'à `37db22b` (vérifié par
`git diff 4229a02 HEAD` sur les trois `*-figures.tex`, les trois scripts, la palette et la légende communes).
Outils et journaux : `outils/genome/tome3/juge2-construction/`.

## 0. Verdict

**Les cinq graves du premier flux sont levés ; les corrections en ont créé deux autres, deux phrases de
légende, chacune réparable par une phrase.** Les chiffres tiennent tous.

- **56 nombres neufs ou déplacés** des trois `*-nombres.tex` refaits par mon code depuis `mesures/` : **56
  tiennent** à l'arrondi écrit, aucun à la frontière d'un arrondi (`journaux/refaire.txt`).
- **36 fichiers de données** du lot (les 33 du premier flux et les 3 neufs) régénérés **au bit** par les
  scripts du lot dans une copie `git archive`, avec un dossier de données vide au départ (`journaux/regenerer.txt`).
- **40 points tirés** (graine 31415) dans chaque série neuve ou réécrite, recalculés à la source : **0 écart**
  (`journaux/points.txt`).
- **62 séries contre leur cadre**, bornes tapées comprises : **aucun point dehors** ; les deux repères de
  III-9.6 sont bien hors du cadre (`journaux/cadres.txt`).
- **Les 5 témoins neufs du lot**, forcés à faux un par un : **les 5 tombent** (`journaux/temoins-du-lot.txt`).
- Pilote compilé par `lualatex` (MiKTeX), deux passes par langue : **0 erreur, 0 boîte trop pleine, 0 renvoi
  indéfini**, 18 pages en français et 18 en anglais (`journaux/compilation.txt`). J'ai lu chaque page des deux
  langues à 110 dpi, agrandi III-9.6 à 400 dpi, et relu toutes les légendes anglaises en texte.
- **La note pour le mémoire** (`genome/construction-codon-pour-le-memoire.md`, § 3 et § 5 F6) : la barre est
  juste, la correction dit ce qui a changé, et aucune phrase barrée ne survit dans une légende du lot (§ 5).

**Graves neufs : 2.** **Mineurs : 13.** Je n'ai rien corrigé : aucune des fautes trouvées n'est mécanique (ce
sont des phrases qui disent faux, pas des nombres mal recopiés).

| Figure | Verdict | En une ligne |
|---|---|---|
| III-8.1 roue | **tient** | 72 tenseurs, une seule source avec la pièce ; témoin du code 8 tenu ; ×1,88 juste |
| III-8.2 octets | **tient** | 256 et 225 symboles, 31 octets hachurés, échelle à 1,8 > 1,763 |
| III-8.3 théorème | **tient** | panneau de résidus dans son cadre (−1,67 à +1,61 ·10⁻⁴) |
| III-8.4 accumulateur | **tient** | inchangé au fond ; la croix de la cassure se voit |
| III-8.5 colonne | **tombe en l'état** | (a) dit « entropies, pas un fichier codé », (c) dit « codec réel », pour les mêmes nombres : c'est (c) qui est vrai (GN2) |
| III-8.6 J1 | **tient**, réserve | tête ambiguë sur les 3,4 % (N6) |
| III-8.6 bis | **tient**, réserves | J5 dit « tous ses tronçons » (1 200 tirés) ; renvoi au 20b pour le compagnon du 120b (N2, N3) |
| III-8.7 format | **tient** | décalages refaits contre ARCHITECTURE § 4.3 : 64, 72, 80, 96, 136, 264, 4 088 justes (M6 levé) |
| III-8.8 codon par le juge | **tient** | G2 levé : axe 4 à 12, l'expert à 11,68 % dessiné et nommé |
| III-9.1 (a)(b)(b′) | **tient**, réserve | G3 levé ; nommage des panneaux en conflit avec le lot latents (N12) |
| III-9.2 queue | **tient**, réserve | G4 levé ; λ = 0 sur les neuves par le chemin mêlé alors qu'un chemin unique existe (N5) |
| III-9.3 forêt | **tient**, réserve | G1 et G5 levés ; tête « fenêtre par fenêtre » contre 9/10 (N7) |
| III-9.6 variantes | **tient**, réserve | G7 levé ; l'étiquette du moteur exact couvre le bas de la barre de λ = 0 (N1) |
| III-10.1 experts vus | **tombe en l'état** | tête : « aucune mesure de la construction ne les a jugés » ; C1 les a décodés tous les 768 (GN1) |
| III-10.3 fenêtres | **tient**, réserve | M13 levé pour la frontière seule ; λ = 1 sort de l'écart écrit (N4) |

« Tombe en l'état » a le sens du premier flux : la figure ne peut pas entrer au mémoire telle qu'elle est
compilée ; ses données sont justes, et chacune se répare par une phrase (§ 3).

## 1. Méthode

Différence avec le premier juge : j'ai lu le `git diff` des scripts du lot **avant** d'écrire mon code (la
consigne me le demandait, pour savoir ce qui avait changé). Mon indépendance est donc celle du code et, là où je
l'ai pu, celle du fichier lu ; pas celle de la lecture. Je le reprends au § 7.

1. **Les nombres** (`refaire.py`). Chaque `\def` neuf ou déplacé des trois `*-nombres.tex` est refait par mon
   code, écrit avec autant de décimales que la chaîne du lot, et comparé comme chaîne. Un nombre à moins de 1e-6
   relatif d'une demi-unité de son dernier chiffre serait signalé : aucun ne l'est (le seul que je craignais,
   3,2 pour le plus petit rapport σ_f/σ_n, vaut 3,2473). Là où un second fichier existe, je l'ai pris :
   - l'axe sans perte de III-8.5 (c) : `mesures/genome/predictif-elagage/taux-reel-colonne-12-gptoss20b.json`
     (le codec réel, tenseur par tenseur), pas `colonne-par-tenseur.csv` ni `k10/frontiere.csv` ;
   - les parts de la roue : l'histogramme des 72 tenseurs, sommé tenseur par tenseur, recoupé à 1e-12 par
     `zero-compte-20b.json` (autre outil) et au compte près par `tailles.json` (`moins_zero_fondus`) ;
   - le B/A de l'étage disque du 120b : les journaux de passe `juge/vitesse/120b-disque-*.json`, pas
     `disque-passes.csv` ;
   - l'écart des deux chemins de III-10.3 : les fichiers par position (`synonyme/kl/` et `synonyme/moteur/`),
     pas `kl-par-fenetre.csv` (témoin : la voie substituée relue position par position redonne
     `kl-par-fenetre.csv` à 1e-8) ;
   - les bits utiles du moteur exact : `somme_octets_utiles × 8 / poids_experts` de `J-T0-fichiers.json`,
     recalculés, pas le champ `bits_par_poids_utiles`.

   Conventions : médiane et centile de numpy (interpolation linéaire) ; σ par fenêtres = écart-type (ddof = 1)
   des dix moyennes divisé par √10. **Cassure** (`--casser`) : les KL de la frontière sur R1 multipliées par
   1,01 ; **8 nombres tombent** (`journaux/refaire-casse.txt`).
2. **La régénération** (`regenerer.py`). `git archive` de HEAD (sans conversion de fins de ligne) des trois
   scripts et des cinq dossiers de mesures qu'ils lisent, dans un dossier temporaire ; le dossier des données y
   est créé **vide**, pour qu'un fichier que les scripts n'écriraient plus manque au lieu d'être recopié. SHA-256
   de chaque fichier écrit contre le blob commité, et ensemble des fichiers écrits contre ensemble des fichiers
   commités du lot. **36 sur 36 égaux, aucun en trop, aucun en moins.** **Cassure** : un appel déplacé d'un
   expert à son voisin dans `routage-grille.csv` (totaux gardés) : `juge-grille.csv` diffère, seul
   (`journaux/regenerer-casse.txt`).
3. **Les témoins neufs du lot** (`regenerer.py --temoins`). SOCLE : « tout témoin neuf doit pouvoir échouer ».
   Le lot en a posé cinq sans dire s'il les avait cassés. Je les ai forcés à faux un par un dans une copie
   neuve : le code 8 de la roue contre `moins_zero_fondus` (+1), les moyennes sans perte contre
   `k10/frontiere.csv` (3,70639 → 3,70739), le 99,9e centile contre `juge kl` (+0,001), le repère Q2_0 hors du
   cadre (mis à 2,60 bits), les jetons par fenêtre (un appel ajouté) : **les cinq arrêtent le script**.
4. **Les points tirés** (`points.py`, graine 31415). Séries contrôlées : `codon-roue.csv` (un code tiré, plus
   les deux codes du zéro : parts avant et après, valeur OCP), `codon-sans-perte.csv` (un tenseur : les trois
   débits, « retenu », « perd », l'étiquette), le résidu de `codon-theoreme-{20b,120b}.csv`, les cinq barres de
   `codon-j1-encart.csv`, les couleurs de `codon-j1-cascade.csv`, `juge-grille-marge.csv`, un sommet de chaque
   côté du polygone de `synonyme-cumul-aire-frontiere.csv`, une ligne de la grille neuve de
   `synonyme-survie.csv` (quatre séries), la ligne du moteur exact de `synonyme-variantes.csv`. **40 contrôles,
   0 écart.** **Cassure** : valeur recalculée décalée d'un millième relatif : 24 écarts sur 40 (les autres sont
   des chaînes, des zéros ou des uns).
5. **Les cadres** (`cadres.py`). Le second flux a posé une règle : aucun point hors du cadre. Le lot l'applique
   par ses scripts à III-9.3, III-8.8, III-9.6, III-8.3 et III-8.5 (c) ; les autres bornes sont tapées dans les
   `.tex`. L'outil prend les deux : bornes des scripts lues dans les `*-nombres.tex`, bornes tapées recopiées et
   cherchées mot pour mot dans les `.tex` (l'outil s'arrête si l'une a changé). **62 séries, 0 point dehors.**
   **Cassure** : la borne haute de III-8.8 ramenée à 10, celle du premier flux : l'expert à 11,68 % sort.
6. **Les pages.** Pilote du lot copié en `memoire/essai/pilote-juge2-construction.tex` (ignoré par git),
   compilé deux fois par langue ; pages rendues par `pdftoppm` à 110 dpi, toutes lues ; III-9.6 agrandie à
   400 dpi en français et en anglais ; légendes anglaises extraites par PyMuPDF et cherchées pour la
   typographie française (« : », « ; » précédés d'une espace, virgule décimale) : aucune.

## 2. Les graves du premier flux : levés

**G1 (III-9.3, points hors du cadre) : levé.** Un seul axe de −0,36 à 0,08 pour les trois panneaux, tiré des
données. Mes extrêmes : −0,3452 (R1, fenêtre 7, λ = 1 contre frontière) et **+0,0609 (R1, fenêtre 7, λ = 0
contre λ = 1)**, celle que la légende cite ; toutes les bandes ±2σ sont dedans (de −0,2233 à −0,0009). Lu sur la
page : la rangée 7 du panneau 2 porte son point, à droite du zéro. Le panneau 2 se lit petit : c'est la vérité,
et le design le voulait (G3 du juge de design).

**G2 (III-8.8, expert à 11,68 %) : levé.** Axe de 4 à 12, tiré des parts (5,7764 à 11,6797) ; l'expert 26 de la
couche 0 du 120b est dessiné et nommé, et la légende le dit « le plus haut ». Le second est à 8,98 % : pas
d'égalité cachée.

**G3 (III-9.1, l'aire n'est pas le sur-apprentissage) : levé.** La phrase est retirée du dessin. Les deux aires
sont tracées et chiffrées par la définition du premier juge (moyenne sur k de la part en calibration moins la
part vue par l'évaluation) : 0,318 et 0,168, écrites 0,32 et 0,17. Le sur-apprentissage est dit par le rapport
du coût vu par l'évaluation au coût de calibration : ×0,975 (frontière) et ×1,67 (synonyme), refaits. M7 est
fait : 0,41 = tr H / 2 880, 433 valeurs propres au-dessus ; et 0,41 dépasse bien le poids d'évaluation des
directions muettes, qui va de 0,119 à **0,225** (je l'ai vérifié, la légende ne le chiffre pas).

**G4 (III-9.2, la queue sur trois positions) : levé.** La légende dit les trois positions au-dessus de chaque
99,9e centile (le même compte pour les quatre séries, mon code le redonne), les baisses sur R1 et sur les
neuves (3,4 et 20,8 % pour λ = 1, 17,2 et 15,9 % pour λ = 0, refaites), et que la comparaison λ = 0 contre
λ = 1 n'est pas faisable à cette taille. Le dessin suit G4 du juge de design (traits, axe de 10⁻² à 10¹, marques
de série, « ÷ 2,66 »). Les quatre séries tiennent sous 8,5 (maximum 7,96 pour Q2_0) : aucune courbe ne s'arrête
au bord. À gauche de 10⁻² : 0,667 % des positions de λ = 0 au plus, écrit 0,7 %. Réserve : N5.

**G5 (III-9.3, chemins mêlés) : levé.** Le panneau 1 des neuves est dit « deux chemins, indicatif », en losanges
creux, et la légende renvoie à JUGEMENT-construction § 9. Ce que le mélange déplace, sur R1 : d̄ = −0,11178
(mélange), −0,11183 (référence substituée seule), −0,11035 (moteur seul) ; le plus grand écart vaut 0,00143,
écrit 0,0014. Le premier juge l'arrondissait à 0,0015 depuis des valeurs déjà arrondies : le lot a raison.

**Graves de dessin du lot (juge de design).** Vérifiés pour ce qu'ils touchent aux chiffres ; le jugement du
dessin revient au juge de design du second flux.
- G3 (III-9.3) : levé, comme G1 ci-dessus.
- G4 (III-9.2) : levé (traits distincts en gris, médianes et centiles à la marque de leur série).
- G6 (III-8.6) : levé. Scindée en III-8.6 et III-8.6 bis ; dans (c), une seule clé (abscisse = fichier,
  couleur = motif), les seize passes en points noirs, aucune écartée ; titre de l'encart sous son cadre ;
  « ≥ ×1,394 ». M3 fait : les cinq barres de l'encart sont dessinées et leurs rapports refaits (0,981 des
  médianes, 0,980 des moyennes, ×1,26).
- G7 (III-9.6) : levé (cadre 2,54 à 2,72 bits et 0,08 à 0,36 de KL ; trois variantes et leurs barres dedans ;
  Q2_0 et le moteur exact hors du cadre, flèches et nombres tirés du fichier). Réserve : N1.
- G9 (l'ensemble) : les quinze figures ont titre court, tête en gras, provenance et ligne « Données » ; le
  pilote appelle `\LegendeFigure`, qui s'arrête si une pièce manque.

## 3. Les graves neufs

**GN1. III-10.1 : la phrase de tête dit faux.** « 11 experts de gpt-oss-20b n'ont jamais été routés, sur aucun
des deux jeux de fenêtres : **aucune mesure de la construction ne les a jugés**. » La première moitié est juste
(mon compte : couches 9, 11 à 17, 19 et 23 ; 17 en a deux). La seconde ne l'est pas. Le vérificateur du lot A a
décodé **les 768 experts** du v1.2 du 20b et les a trouvés égaux en valeur (C1 : `tailles.json`,
`experts_exacts_v12` = 768 ; 06 § 5, `journaux/verifier-20b-v12.json`, huit contrôles à zéro faute), et le
théorème de III-8.3 est mesuré sur chaque tenseur entier. Ce que ces 11 experts n'ont pas eu, c'est une **mesure
de KL** : aucune des vingt fenêtres ne les appelle sous le routage de la référence. La phrase existait dans le
corps de la légende du premier flux (le premier juge n'en a borné que la fin, M12) ; le second flux l'a promue
en tête, c'est-à-dire en idée de la figure, et elle contredit le résultat central du chapitre 8. Elle vient de
la note du juge de la construction (`genome/construction-juge-pour-le-memoire.md`, F-J4 : « les experts
qu'aucune mesure de la construction n'a jugés »), qui est à barrer par son auteur ou l'orchestrateur, pas par
moi. **À écrire** : « … sur aucun des deux jeux de fenêtres : aucune mesure de KL de la construction ne les a
appelés (leur décodage, lui, est vérifié en valeur : C1, 768 experts sur 768). »

**GN2. III-8.5 : la légende dit deux choses contraires des mêmes nombres.** Le panneau (a) dit le gain de la
colonne « en bits par poids (**entropies des histogrammes du tenseur, pas un fichier codé**) » ; le panneau (c),
neuf, dit l'axe sans perte « **codec réel** ». Ce sont les mêmes colonnes de `colonne-par-tenseur.csv` : le gain
de (a) est `zero_octet_kappa − zero_demi_octet_kappa_colonne`, et (c) trace ces deux débits. C'est (c) qui est
vrai. Ces colonnes recopient `taux-reel-colonne-12-gptoss20b.json`, écrit par
`outils/genome/predictif-elagage/taux_reel` (« codés par le rANS de l'étude 03 et décodés exactement », témoin
`tous_exacts` vrai) ; le script de la synthèse le dit aussi (« colonne-par-tenseur.csv le codec réel κ ×
colonne »), et la légende de III-7.1 classe ces points « codec réel ». La parenthèse de (a) est fausse depuis le
premier flux (son juge ne l'a pas vue). C'est l'ajout de (c) qui la met en contradiction, deux phrases plus
loin. Une mesure dite estimation, c'est la distinction « calculé / mesuré » du SOCLE prise à l'envers. **À
écrire** en (a) : « le débit gagné en ajoutant la classe de la colonne d'entrée au contexte octet κ, en bits par
poids (codec réel : flux codés par le rANS et décodés exactement ; aucun fichier `.trc` écrit) ». Voir aussi N8
sur ce que ce gain contient.

## 4. Les mineurs

- **N1. III-9.6 : une étiquette couvre une donnée** (créé par la correction G7). L'étiquette « moteur exact
  (v1.0), hors du cadre / 3,86 bits, KL 0,0037 » est posée dans le cadre, en bas à droite, avec son halo ; elle
  recouvre le bas de la barre ±2σ de λ = 0 (de 0,10 à 0,0953) et son trait d'extrémité. On le voit agrandi à
  400 dpi, dans les deux langues. La règle du second flux est qu'aucun point ne sort du cadre, et ici une donnée
  est cachée dedans. Remède : poser l'étiquette sous l'axe, à côté de la marque, ou à gauche de x = 2,64.
- **N2. III-8.6 bis : J5 n'est pas « tous ses tronçons ».** La légende dit que C120 se lit « ×1,26 plus vite
  [sur ses tronçons d'un extent] que sur tous ses tronçons (J5 puis J6…) ». J5 lit **1 200 tronçons tirés** par
  la graine du juge du placement (`n` = 1 200 dans les deux journaux ; JUGEMENT-placement § 5.9 : « 1 200
  tronçons de C120 tirés par ma graine »). Le commentaire du script (« J5 : C120 lu en entier ») et le nom de la
  ligne du CSV (`C120-J5-entier`) disent la même chose fausse. L'encart ne dit pas non plus que les barres s2
  viennent de `troncons disque` et les barres J5 et J6 du lecteur Python du juge du placement, plus lent de 2 à
  5 % (son § 5.2). Les rapports écrits restent justes : chacun compare deux barres du même lecteur.
- **N3. III-8.6 bis (d) : le compagnon du 120b renvoie à une figure du 20b.** « Le compagnon frontière du 120b,
  avec perte (\cref{fig:t3-syno-variantes}) » : III-9.6 porte les variantes du **20b**, dont la frontière est à
  KL 0,264 contre la référence f64. Un lecteur y prendra ce nombre pour le compagnon du 120b. Or la KL du
  compagnon du 120b existe, commitée dans le dossier que le script lit déjà :
  `mesures/genome/construction/synonyme/proxy/proxy-120b-exact-contre-rapide-frontiere.json`, **0,1404 ±
  0,0042**. C'est un proxy contre le moteur exact, pas contre la référence (07 § 5, « deux fois moins de KL au
  120b qu'au 20b »). La raison donnée par le lot pour M4 (« aucun fichier commité lu par ce lot ne la
  porte ») ne tient donc pas. M4 n'est levé qu'en partie.
- **N4. III-10.3 : M13 levé pour une seule variante.** « Là où une même variante est passée par les deux chemins,
  les valeurs tracées diffèrent de −0,0014 en moyenne (frontière, R1 ; de −0,0076 à +0,0010 par fenêtre) » ;
  les nombres sont justes. Mais sur R1, les **trois** variantes sont passées par les deux chemins (le lot B a les
  fichiers moteur de la frontière, de λ = 1 et de λ = 0). λ = 1 : +0,0001 en moyenne, de −0,0074 à **+0,0029**
  par fenêtre ; λ = 0 : −0,0004, de −0,0020 à +0,0017. La fourchette écrite ne les borne donc pas. Deux points
  de plus : sur R1 un seul chemin est tracé, ce sont donc les valeurs des deux chemins qui diffèrent, pas « les
  valeurs tracées » ; et le signe n'a pas d'ordre dit (moteur moins référence substituée).
- **N5. III-9.2 : λ = 0 sur les neuves pris au chemin mêlé alors qu'un chemin unique existe.** −15,9 % compare
  λ = 0 par le moteur à la frontière par la référence substituée. Sur les mêmes fenêtres, λ = 0 a aussi été passé
  par la référence substituée (`kl-neuf-sub-l0-positions.csv`) : par un seul chemin, la baisse est de
  **−18,2 %**. La légende dit le chemin, donc rien n'est faux. Mais III-9.3 (panneau 3) prend pour la même
  variante, sur les mêmes fenêtres, la voie substituée : les deux figures voisines ne lisent pas λ = 0 neuves par
  le même chemin. À donner : le nombre du chemin unique, ou les deux.
- **N6. III-8.6 : la tête mesure les 3,4 % sur une autre base.** « … et ses octets n'en expliquent au plus que
  3,4 % » se lit « 3,4 % du gain ». Les octets plafonnent la vitesse à **+3,4 %** (×1,034). Rapporté au gain de
  +45,4 %, c'est 7,5 % (8,9 % en échelle logarithmique). Le corps de la légende est juste (« +3,4 % au plus »).
  À écrire : « … et ses octets ne lui donneraient que +3,4 % au plus ».
- **N7. III-9.3 : « fenêtre par fenêtre ».** La tête dit que les deux synonymes « battent la frontière fenêtre par
  fenêtre ». Sur les neuves, λ = 1 contre la frontière ne gagne que 9 fenêtres sur 10 (la fenêtre 2 est contre),
  et c'est le panneau indicatif. Le reste est 10/10. À écrire : « … sur l'appariement fenêtre par fenêtre ».
- **N8. III-8.5 : ce que mesurent (a) et (c).** (a) Le gain écrit mêle deux choses : le passage de l'alphabet
  octet à l'alphabet demi-octet, qui **coûte** de 0,0029 à 0,0050 bit sur les douze tenseurs, et la colonne
  elle-même, qui gagne 0,008 à 0,010 sur 8g, 8u, 23g et 23u et presque rien ailleurs. Les « négatifs » de (a)
  sont surtout ce coût d'alphabet. (c) Les tirets sont des moyennes sur douze tenseurs, dont trois de la couche 0
  (contre 3 sur 72 dans le modèle). Sur ces douze, la colonne gagne 3,7064 − 3,6844 = 0,022 bit, environ six fois
  le 0,0037 du modèle entier que (b) écrit. La légende ne relie pas (b) et (c), et l'œil compare.
- **N9. La « règle » des cadres ne peut pas tomber là où elle sert le plus.** Le lot dit que ses scripts
  « s'arrêtent si un point sort du cadre ». Pour III-9.3 et III-8.8, les bornes sont calculées depuis les mêmes
  points, avec une marge : l'assertion est vraie par construction, et III-8.5 (c) n'en a pas. Seules trois gardes
  savent tomber : celle de III-8.3 (constantes 0,108–0,245 et ±2,5 recopiées dans le script), celle de l'échelle
  de III-8.2 (1,8) et celle des repères de III-9.6 (je l'ai cassée, § 1). Aucune ne protège d'une borne retapée dans un `.tex`. Les axes aux
  bornes tapées sans garde sont III-8.5 (a)(b), III-8.6 et III-8.6 bis entières, III-8.8 (b), III-9.1, III-9.2
  et III-10.3. Ils sont tous dedans aujourd'hui (`cadres.py`). La garde qui sait tomber lit les bornes dans le
  `.tex`.
- **N10. Le bleu `Accent`, « propre à cette figure », dans quatre figures.** La règle du dictionnaire permet une
  couleur hors dictionnaire **dans une seule figure**, si sa légende la dit. Au chapitre 8, `Accent` (bleu
  1F5C99) porte les valeurs positives en III-8.1, l'échelle des fréquences en III-8.2, le contexte de colonne en
  III-8.5 et les champs changés en III-8.7. III-8.2 et III-8.5 écrivent chacune que ce bleu « n'appartient qu'à
  cette figure ». C'est une règle appliquée de travers. Au juge de design de trancher la couleur.
- **N11. La note pour le mémoire et la figure donnent deux valeurs du même rapport.** Le § 3 corrigé écrit
  ×1,389 (valeur du juge du placement, médianes arrondies), III-8.6 bis écrit ×1,388 (médianes exactes ; le
  premier juge a montré que les deux se défendent). Ni l'une ni l'autre ne dit pourquoi l'autre diffère. Le
  § 5 F5 de la note dit encore « à la même échelle », que D14 a fait corriger dans la figure en « dans les mêmes
  unités ».
- **N12. III-9.1 : les lettres des panneaux ne s'assemblent plus.** Le lot a nommé sa part cumulée (b′) « pour
  laisser (c) » au lot latents. Celui-ci, dans son commit `326969f`, postérieur, nomme sa rangée (d) et écrit
  « la même matrice que les panneaux (a) à (c) ». Assemblée, la figure aurait (a), (b), (b′), (d) et une légende
  qui renvoie à un (c) absent. L'un des deux lots doit changer de lettre ; le plus simple est que (b′) devienne
  (c).
- **N13. M16 toujours ouvert.** `memoire/tome3/REPRISE-figures-construction.md` (premier flux) dit encore
  « 17 figures » ; le pilote du premier flux en avait 14 sur 17 pages. Fichier hors de la liste du lot et de la
  mienne : à barrer par l'orchestrateur.

## 5. La note pour le mémoire (`cadf276`)

Lue contre `genome/JUGEMENT-placement.md` (§ 0, §§ 5.3, 5.6, 5.7, 5.9, 5.10) et la réserve R1 :
- **§ 3** : la phrase « un effet de disposition sur le disque d'un ordre de grandeur plus grand que l'effet du
  format » est barrée, pas retirée, et la correction suit, datée, avec sa source :
  - l'écart B/A suit le motif des requêtes de lecture (×1,389 et ×0,715 au motif croisé) ;
  - la variable exacte du motif n'est pas isolée (×0,851 et ×0,882, J10 et J11, comme R2) ;
  - le toit de 3,37 % ne vaut que pour les octets ;
  - l'écart 1,30 entre A et C vient de la fragmentation de C (267 473 extents ; ×1,26) ;
  - ce qui a changé : le motif croisé.

  Tout est conforme aux sources. Une nuance que la note ne garde pas : le juge du placement écrit que la
  défragmentation de C « n'est toujours pas mesurée par une réécriture ». « Vient de la fragmentation » est sa
  lecture par J5 et J6, pas une réécriture mesurée.
- **§ 5 F6** : le troisième panneau (« la disposition du fichier, à contenu égal, en rend 30 % ») est barré ; la
  correction renvoie à III-8.6 et III-8.6 bis et dit que le gain ne se transporte pas à un autre disque.
- **Les phrases barrées ne reviennent pas** : cherchées dans les trois fichiers de figures (« disposition »,
  « pas le format », « 30 % », « ×2,00 », « ×1,24 », « l'aire est le sur-apprentissage », « bouge à peine »,
  « la longueur des requêtes ») : aucune. « Sur-apprentissage résiduel » reste en III-9.1, mais pour le rapport
  des coûts (×1,67 contre ×0,975), ce que le premier juge demandait.
- Aucune autre phrase de la note ne porte l'ancienne attribution (cherché : « disposition », « 30 % », « état du
  fichier », « fragmentation », « ×1,4 »). Reste N11.

## 6. Ce qui sort du lot

- **III-7.1 et l'axe sans perte** : le lot laissait ce retrait au lot ronde. C'est fait (`6292203` : « l'axe sans
  perte part en III-8.5 »), et la légende de III-7.1 renvoie au chapitre 8. Les deux figures ne le montrent plus
  en double.
- **III-9.1 (d)** du lot latents : hors de mon rôle, sauf l'assemblage (N12).
- **La note F-J4** du juge de la construction porte la phrase de GN1 : à barrer par son auteur.

## 7. Ce qui pourrait être faux (dans ce jugement)

- **Mon indépendance est partielle.** J'ai lu les diffs des scripts du lot avant d'écrire mon code. J'ai aussi
  lu sa fonction `passe_valide` (passes à arrêt, sous charge ou sur batterie écartées), et j'ai appliqué la même
  règle aux journaux J5 et J6. Elle vient de JUGEMENT-placement § 5, mais je ne l'ai pas redérivée. Une erreur de
  définition partagée par le lot et par moi passerait. Là où j'ai pu, j'ai lu un autre fichier (§ 1) ; les
  mesures commitées elles-mêmes ont leurs juges.
- **GN1 dépend du sens de « juger ».** Dans JUGEMENT-construction, « les experts jugés pour la première fois »
  veut dire « appelés par une passe de KL ». Si le mémoire définit « juger » ainsi avant III-10.1, la tête n'est
  qu'ambiguë, et GN1 devient un mineur. Je le classe grave parce qu'une tête se lit seule et qu'elle contredit
  C1 au sens commun.
- **GN2 s'appuie sur l'en-tête de l'outil `taux_reel`** et sur son témoin `tous_exacts`. Je n'ai pas relancé ce
  codage (aucune passe sur le GGUF dans ce flux).
- **Le classement grave ou mineur est le mien.** J'ai suivi la mesure du premier juge, chez qui un protocole mal
  dit est un grave (son G5). GN1 et GN2 se réparent chacun par une phrase.
- **J'ai lu les pages à 110 dpi** et agrandi III-9.6 seulement, là où je cherchais. Un recouvrement plus petit a
  pu m'échapper ailleurs. N1 et N10 sont des remarques de dessin ; le dessin est jugé par le juge de design.
- **`cadres.py` recopie à la main les bornes tapées.** Il vérifie que leur texte est dans le `.tex`, mais pas
  qu'il est sur le bon axe. Une borne répétée sur deux axes pourrait être mal attribuée ; je les ai attribuées en
  lisant les sources.

## 8. Reproduire

```
cd ~/dev/active/troncons/outils/genome/tome3/juge2-construction
python -I -X utf8 refaire.py --sortie journaux/refaire.csv     # 56 nombres ; --casser : 8 tombent
python -I -X utf8 regenerer.py                                 # 36 fichiers au bit ; --casser : 1 diffère
python -I -X utf8 regenerer.py --temoins                       # 5 témoins du lot forcés à faux : 5 tombent
python -I -X utf8 points.py                                    # 40 contrôles, graine 31415 ; --casser
python -I -X utf8 cadres.py                                    # 62 séries contre leur cadre ; --casser
```
Mémoire de pointe de chaque outil sous 1 Go ; aucune passe du modèle, aucune carte. Pilote :
`memoire/essai/pilote-juge2-construction.tex` (copie du pilote du lot, ignorée par git) ; `lualatex` deux fois,
puis `lualatex -jobname=pilote-juge2-construction-en "\def\ANGLAIS{1}\input{pilote-juge2-construction.tex}"`
deux fois.
