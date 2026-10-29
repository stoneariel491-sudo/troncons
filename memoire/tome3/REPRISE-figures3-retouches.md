# Troisième passe des figures : les retouches du Tome III (note de reprise)

Rôle : les retouches du Tome III après les jugements du second flux (`JUGEMENT-figures2-*.md`), dans les seuls
`memoire/figures/tome3/*-figures.tex`, `legende-tome3.tex`, `palette-tome3.tex`, `memoire/outils/tome3_*.py` et leurs
données sous `memoire/figures/tome3/donnees/`. Aucune mesure, aucune carte graphique, aucune passe du modèle.
MiKTeX 26.5 tel quel (préambule réparé par le rôle « préambule », commits 7db2673 et 4a9dfb3).

Piège de l'outil : l'outil d'écriture refuse le dépôt (worktree) ; les fichiers sont édités dans un miroir du
répertoire temporaire, puis recopiés par `cp`. Pas de LaTeX par heredoc ni par `sed` : un `sed` a abîmé une fois
les barres obliques inverses d'une ligne de III-8.5 (vu à la relecture, corrigé avant tout commit).

## État

- [x] Lot ronde (7a40c54) ; lots construction et latents (6137230) ; palette et pilotes (commit suivant).
- [x] Gardes neuves cassées une à une : `python -I -X utf8 memoire/outils/tome3_cassures.py` (quatre « la garde
  tombe ») et `python -I -X utf8 memoire/outils/tome3_latents.py --casse-entrees` (E1 tombe) ; aucune cassure
  n'écrit sous `donnees/` (empreintes MD5 des 120 fichiers égales avant et après).
- [x] Les huit pilotes (quatre lots, FR et EN) compilés dans `memoire/essai/`, deux passes, PDF gardés (§ 4).

## 1. Les trois phrases fausses (graves neufs des juges des chiffres)

| Figure | Ce qui était faux | Ce qui est écrit | D'où vient le nombre |
|---|---|---|---|
| III-8.5 (GN2) | (a) « entropies des histogrammes du tenseur, pas un fichier codé » | « le débit gagné … (codec réel : flux codés par le rANS et décodés exactement ; aucun fichier `.trc` écrit) » | témoin neuf dans `tome3_codon.py` : les quatre colonnes de `colonne-par-tenseur.csv` égalent, tenseur par tenseur, `taux-reel-colonne-12-gptoss20b.json` (à 1e-6), qui dit `tous_exacts` et chaque tenseur `exacts` ; cassure : un débit faux de 1e-3 relatif, le script s'arrête |
| III-10.1 (GN1) | tête : « aucune mesure de la construction ne les a jugés » | « aucune mesure de KL de la construction ne les a appelés (leur décodage, lui, est vérifié en valeur : C1, 768 experts sur 768) » | `tailles.json` (`experts_exacts_v12`, `C1_v12`), lu par `tome3_juge.py`, qui s'arrête si le compte ne couvre pas la grille ; cassure : 767, le script s'arrête |
| III-9.7 (GN1) | tête : « là où pointent les entrées … au plus 0,135 » (vrai des projections) | « Dans les plans des premiers axes de H, où se projettent les entrées …, au plus 0,135 … ; sur les entrées entières, dont 72 % de la norme au carré est hors de ces trois axes, à 0,61 (médiane ; de 0,49 à 0,81) » | `outils/genome/tome3/juge2-latents/journaux/juge2-nuage-rangee.json` (commité), lu par `tome3_latents.py` ; témoin E1 : le rapport quadratique pondéré du journal égale √(Σλe_s/Σλe_f) du spectre commité du lot B (écart 8,9e-12), sa part dans trois axes égale `part_trace_3_axes` (5e-16), ses sommes égalent les coûts du spectre ; cassure (λ₁ faux de 1 %) : E1 tombe |

III-9.7, en plus : le corps dit « directions projetées », « pour une entrée unité de ce cône » ; « Non montrés » dit
l'erreur **sur les poids** et ajoute que l'erreur de sortie pondérée baisse aussi dans les 2 877 autres directions
(11,96 → 6,08), qui portent 57 % du gain ; le panneau (c) reçoit une quatrième barre, « x », à droite d'un filet :
la médiane des entrées réelles (0,61) et leur étendue en moustache (0,49 à 0,81). DN15 : la rose a une icône de
barre dans la clé, et la clé dit l'angle médian d'une entrée au plan (u₁, u₂) : 59°.

## 2. Les mineurs des juges qui étaient des phrases fausses (ou trompeuses)

- III-9.1 (c), N1 du juge latents : « éloigne ces poids » → « en éloigne 3 de leur valeur exacte (l'autre, un zéro,
  change de signe à la même distance) » ; le script compte (3 et 1) et s'arrête si un symbole changé se rapproche
  ou si l'autre n'est pas un zéro. N2 et N12 : la rangée prend la lettre (c), la légende renvoie à (a), (b) et (b′)
  (décision : la suggestion du juge latents ; la part cumulée garde (b′)). N5 : les flèches sont posées à droite
  des marques, sans raccourci au départ ; celle de j = 11 se voit (vérifié à 400 dpi).
- III-8.6, N6 : « ses octets n'en expliquent au plus que 3,4 % » → « ses octets ne lui donneraient que +3,4 % au
  plus ».
- III-8.6 bis, N2 : « que sur tous ses tronçons » → « que sur 1 200 de ses tronçons tirés au hasard (J5) » (et 800
  tronçons d'un extent pour J6), nombres lus dans les journaux, le script s'arrête si les passes n'en lisent pas
  le même nombre ; la ligne du CSV `C120-J5-entier` devient `C120-J5-tire` ; la légende dit le lecteur de chaque
  barre (`troncons disque` pour s2, lecteur Python du juge du placement, 2 à 5 % plus lent, pour J5 et J6). N3 : la
  KL du compagnon frontière du 120b est écrite, 0,140 ± 0,032 (2σ par fenêtres, recalculé du CSV ; la moyenne
  redonne `kl_moyenne` du juge), dite proxy contre le moteur exact ; le renvoi à III-9.6 dit « les variantes du
  20b ». DN19 : panneaux (a) et (b), et « La suite de la figure III-8.6 ».
- III-8.5, N8 : le gain écrit contient le coût de l'alphabet demi-octet (0,0029 à 0,0050 bit) ; les douze tenseurs
  comptent les trois de la couche 0 et la colonne y gagne 0,0220 bit en moyenne, contre 0,0037 pour le modèle.
- III-9.3, N7 : « fenêtre par fenêtre » → « chacun dans au moins 9 fenêtres sur 10 » (nombre tiré par le script).
- III-10.3, N4 : la fourchette couvre les trois variantes passées par les deux chemins sur R1 (−0,0076 à +0,0029 ;
  moyennes −0,0014, +0,0001, −0,0004), signe dit (moteur moins référence substituée), « un seul chemin est tracé ».
- III-7.2, N3 du juge ronde : « (figure suivante) » va à la queue qu'elle ne voit pas ; le routage imposé renvoie au
  Tome II, lot R.
- III-7.4, N2 du juge ronde : la seconde pointe (colonne 960, premier canal du morceau de la géante, ×310) est
  nommée sur le dessin et dans la légende ; les 44 autres bords ×0,70 (au plus ×0,87), les 62 autres colonnes du
  morceau ×4,0 ; « bords ×7,6 » est dit comme une moyenne que porte cette seule colonne. Tête : « une colonne
  géante, et le premier canal de son morceau de rotation ». Le script cherche la pointe, le `.tex` vérifie qu'elle
  est bien un premier canal du morceau.
- III-7.6, N3 : « l'état le plus entouré des siens » → « là où les états du groupe sont le plus serrés (la densité,
  pas la pureté) », le trait de rappel invisible n'est plus annoncé ; N4 : « se tiennent plus souvent aux bords
  (0,70 de voisins d'un autre expert, contre 0,47) » ; N6 : la clé a une pastille par gris ; N7 : « 0,51 sous le
  10e centile comme 0,51 au-delà de la médiane ». N9 : commentaire du script remis sur sa ligne.

## 3. G7, G10, GD1, DN1 et les autres DN

- **G7 (III-9.6)** : le cadre suit une règle écrite dans `tome3_synonyme.py` (marge 0,02 bit au pas de 0,01 : 2,56
  à 2,70) ; les variantes couvrent **61,1 %** de la largeur (seuil déclaré du juge : plus de 50 %), et le script
  s'arrête en dessous (cassure : l'ancienne règle, 47,6 %, le fait tomber). Étiquette de λ = 1 à droite de son
  point, celle de λ = 0 sous la sienne ; celle du moteur exact ne couvre plus la barre de λ = 0 (N1 du juge
  construction). Vu au rendu : aucune étiquette ne touche une barre.
- **G10 (III-7.1)** : le trait de la loupe part du bord droit de la loupe (y = 0,87) et rejoint le bas de l'encart
  à 72 % de sa largeur ; il passe à environ 2 mm de « partitions κ, par tenseur » (vu à 400 dpi). L'étiquette de la
  loupe descend à y = 0,745. DN8 : la clé dit « pire » (« worse »).
- **GD1, le bleu** : `Accent` ne paraît plus dans aucun dessin des huit fichiers (seulement dans un commentaire).
  III-2.1 en trois gris ; III-4.8 arêtes en rampe d'encre, disques de degré ≥ 3 en `black!12` ; III-7.2 bande en
  contour tireté sans aplat (DN11) ; III-8.1 rayons positifs en `Encre!55` ; III-8.2 échelle en gris ; III-8.4 état
  +0 en `black!6` ; III-8.5 colonne en `Encre!60` ; III-8.7 champs changés dans l'orange de la v1.2. Le bleu plein
  ne porte plus que les sens du dictionnaire (synonyme λ = 1, 20b, R1, catégorie A, et l'expert du panneau de
  III-7.6). `palette-tome3.tex` n'est **pas** modifié ; les paires neuves sont chiffrées par
  `tome3_palette.py` (§ 5).
- **DN1** : `\Legende` met la tête en `\bfseries\boldmath` avec `detect-weight` de siunitx, de même les titres de
  panneau. Libertinus Math n'a pas de graisse : `legende-tome3.tex` déclare une version grasse par épaississement
  (`\setmathfont[version=bold, FakeBold=2.2]{Libertinus Math}`, permis seulement dans le préambule, où les pilotes
  chargent ce fichier). Vu au rendu : « λ = 0 » et « ×1,454 » gras dans les têtes.
- **Autres DN faits** : DN3 (octets absents de III-8.2 et de la mini-table de III-8.7 en blanc bordé d'encre ; le bit
  4 refusé en contour tireté), DN4 (plancher de III-4.2 et colonne géante de III-7.4 sans gris de fond), DN5
  (III-8.4 en gris), DN6 (valeurs de III-3.6 au-dessus du milieu de la flèche), DN7 (valeurs de III-4.8 posées par
  le script là où leur boîte ne touche aucun trait, disque ni autre valeur ; la règle s'arrête sinon, et elle est
  tombée d'elle-même au premier essai, jeu −0,096 cm, avant l'élargissement des places candidates ; plus petit jeu
  final 0,035 cm), DN9 (étiquettes de III-7.4 contre le pic, colonne de droite retirée, cadre élargi), DN10, DN12,
  DN13 (anneaux aux états fragiles de III-7.6 (c)), DN15, DN16 (4 mm de plus entre (a) et (b) de III-9.1), DN17
  (la case de la ligne 0 nommée ; je n'ai pas peint une rangée : une case vaut une ligne de sortie, une seule
  diffère), DN18 (marge de III-9.3 à 0,02 : −0,38 à 0,10), DN19, DN21 (rampe `black!5` à `black!20`), DN22.

## 4. Les pilotes (MiKTeX 26.5, `lualatex`, deux passes, dans `memoire/essai/`)

| Pilote | FR | EN |
|---|---|---|
| commun | 0 erreur, 0 boîte trop pleine, 0 renvoi indéfini, 7 pages | idem, 7 pages |
| ronde | idem, 14 pages | idem, 14 pages |
| construction | idem, 18 pages | idem, 18 pages |
| latents | idem, 6 pages | idem, 6 pages |

Le pilote commun passe de 6 à 7 pages : sa figure des paires montre les 46 paires (§ 5). Pages relues : chaque
figure touchée en français (planches à 75-130 dpi, détails à 250-400 dpi : loupe de III-7.1, valeurs de III-4.8,
flèches de III-3.6, j = 11 de III-9.1 (c), têtes grasses de III-7.1 et III-8.6) ; en anglais, III-7.1 et III-9.6
agrandies, légendes de III-9.1 (c) et III-9.7 relues en texte. Une seule boîte trop pleine vue en chemin, corrigée :
la clé de III-9.7 (une ligne de clé trop longue dans sa boîte, 56 pt) et (a)(b) de III-9.1 (6 pt, DN16), réglées
avant la compilation finale. Le commun : la légende de sa figure des paires (dans le pilote, hors de mon rôle) dit
encore que les fonds pâles se séparent « par les hachures et le trait du seuil » ; la paire neuve `black!5` /
papier se sépare par le cadre et la croix.

## 5. La palette

`tome3_palette.py` chiffre dix paires neuves, des expressions des figures (pas des noms du dictionnaire) : 46 paires,
**42 tiennent** (36 avant, avec le bleu). La seule neuve qui tombe est `black!5` contre le papier (III-10.1 : la case
« les deux » la plus pâle contre « jamais routé ») ; elle se sépare par la forme (cadre et croix d'encre). Les trois
autres paires qui tombent sont les fonds pâles du second flux. `CONVENTIONS-figures.md` (hors de mon rôle) dit encore
« 33 paires sur 36 » : à mettre à jour par l'orchestrateur (42 sur 46).

## 6. Ce qui n'est pas fait, et pourquoi

- DN2 (légendes longues) : le juge le renvoie à la rédaction des chapitres.
- DN14 (noms serrés dans l'ACP de III-7.6) et DN20 (III-8.6 plus large) : refonte de mise en page, pas une retouche ;
  non faits.
- III-9.3 : R1 reste bleu sous le titre « λ = 1 contre frontière » (cité au § 6 du juge de design) ; c'est le
  dictionnaire (`CouleurRun` = `SerieA`), et le changer touche la palette de tout le tome : à trancher.
- N5 du juge construction (III-9.2, λ = 0 neuves par un seul chemin, −18,2 %) : rien n'y est faux ; non ajouté.
- N11, N13 (construction), N8 (latents), N5 (ronde) : hors de mes fichiers (notes et reprises).

## 7. Ce qui pourrait être faux

- Les rapports sur les entrées réelles (0,49 / 0,61 / 0,81, 72 %, 59°, 57 %) viennent du journal d'un juge, pas
  d'un outil du lot ; E1 le relie au spectre commité, mais ne refait pas la plage entrée par entrée (il faudrait le
  GGUF et les captures, hors de ce rôle).
- La place des valeurs de III-4.8 dépend d'une boîte estimée (0,70 × 0,30 cm) ; le rendu à 300 dpi ne montre aucun
  contact, mais l'association d'une valeur à son arête reste parfois à lire de près (0,027 près de 12).
- La version grasse des mathématiques est un épaississement (FakeBold), pas une fonte dessinée en gras.
- Les seuils de couleur et de cadre sont ceux des juges ; je ne les ai pas redérivés.
