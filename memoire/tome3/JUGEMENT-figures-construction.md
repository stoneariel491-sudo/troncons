# Jugement : figures du Tome III, lot « construction » (ch. 8 à 10)

Juge indépendant des chiffres, 2026-10-27. Je n'ai rien tracé. Demande de Stone : « prépare le Tome III :
l'inventaire des figures, puis un flux court avec un juge ». Règles : SOCLE (dont la demande du 2026-10-17,
« la beauté à égalité avec la justesse »), `memoire/tome3/INVENTAIRE-figures.md` (réserves R1 à R6).
Objet jugé : les commits b8f4e85 (ch. 8), a5e3cb9 (ch. 9), 4f8f288 (juge, ch. 8 et 10) et c006ead (note de
reprise) ; leurs fichiers n'ont pas bougé sur `main` jusqu'à 5225cef (vérifié par `git diff`). Quatorze
figures : III-8.1 à III-8.8 (dont III-8.2 et III-8.3, tracées le 17 et légendées par ce lot), III-9.1, 9.2,
9.3, 9.6, III-10.1 et 10.3. Outils du juge : `outils/genome/tome3/juge-construction/` (`recalcul.py`,
`points.py`, `lectures.py`, `regenerer.py`) ; leurs sorties sont commitées sous `journaux/` à côté d'eux.

## 0. Verdict

**Les chiffres tiennent ; quatre figures tombent en l'état par ce qu'elles montrent ou disent.**
- Les **154 nombres** des fichiers `codon-nombres.tex`, `synonyme-nombres.tex` et `juge-nombres.tex` sont
  refaits par un code écrit sans avoir lu les scripts du lot : **154 tiennent** à l'arrondi écrit
  (`journaux/recalcul.txt`). Un seul a demandé une lecture : « au plus 9 331 pour un expert » est le maximum
  des appels **des deux jeux de fenêtres réunis** (un seul jeu : 4 764) ; juste, mais la légende ne le dit pas.
- Les **33 fichiers** de données (`codon-*`, `synonyme-*`, `juge-*`) se régénèrent **au bit** par les trois
  scripts du lot, lancés dans une copie tirée par `git archive` (`journaux/regenerer.txt`).
- **57 points** tirés au hasard (graine 20261027, au moins un par série tracée) sont égaux à la source à
  l'arrondi du CSV (`journaux/points.txt`).
- Le pilote compile en français et en anglais, deux passes, **0 erreur, 0 renvoi manquant**, 17 pages,
  14 figures ; lues : toutes les pages françaises (130 dpi), les pages anglaises 4, 9 et 12, toutes les
  légendes anglaises en texte (PyMuPDF), et des zooms à 300-600 dpi là où il fallait.
- Les trois outils ont leur cassure, et elle tombe : `recalcul.py --casser` 2 écarts, `points.py --casser`
  50 écarts, `regenerer.py --casser` 1 fichier différent (§ 1).

**Graves : 5. Mineurs : 16, dont 2 corrigés par moi** (nombres de légende de III-9.1 en anglais et de III-9.6,
§ 7). Les graves ne sont pas des erreurs de calcul : ce sont des cadres qui cachent des points, une aire
présentée comme le sur-apprentissage alors que la frontière a la même, une queue lue sur trois positions,
et un chemin mêlé dit unique.

| Figure | Tient ou tombe | Pourquoi, en une ligne |
|---|---|---|
| III-8.1 roue des codons | **tient** | nombres justes ; épaisseurs tirées de 12 tenseurs alors que les 72 sont commités (M1, M2) |
| III-8.2 carte des 256 octets | **tient** | points tirés justes, 256 et 225 octets non nuls redonnés |
| III-8.3 théorème | **tient** | écart à la diagonale −0,00017 à +0,00016 redonné sur 180 tenseurs |
| III-8.4 accumulateur (A1) | **tient** | 8 640 et 2 486 216 sont dans 06 § 1 et ARCHITECTURE § 4.16 ; la preuve de 05 § 4.2 couvre le sous-dépassement |
| III-8.5 colonne | **tient** | 0,0037 bit et 8,78 Mo redonnés ; ailleurs −0,0045 à +0,0061 bit |
| III-8.6 J1 (refaite selon R1) | **tient** | R1 respectée, aucune phrase barrée ; encart à deux séances, titre (c) qui chevauche en français (M3 à M5) |
| III-8.7 format v1.2 | **tient** | champs et décalages justes sauf deux cases imprécises (M6) |
| III-8.8 codon par le juge | **tombe en l'état** | un expert sur 96 (120b, couche 0, expert 26, 11,68 %) est hors du cadre (4 à 10 %) : G2 |
| III-9.1 base propre de H | **tombe en l'état** | « l'aire est le sur-apprentissage résiduel » : la frontière a une aire de 0,17 sans sur-apprentissage (G3) |
| III-9.2 queue de la KL | **tombe en l'état** (légende) | la lecture de la queue repose sur 3 positions par courbe et ne se retrouve pas sur les fenêtres neuves (G4) |
| III-9.3 forêt B2 | **tombe en l'état** | 3 points sur 60 hors du cadre, dont la fenêtre 7 de R1 que la légende cite (G1) ; panneau 1 des neuves à deux chemins dit « par le moteur » (G5) |
| III-9.6 variantes à 768 | **tient** (un nombre corrigé) | R3 respectée ; « trois à six fois » devenu « trois à neuf » (M10) |
| III-10.1 experts vus | **tient** | 11 / 2 / 23 / 732 redonnés ; 9 331 et la portée de « ne bougerait aucune KL » à préciser (M12) |
| III-10.3 difficulté des fenêtres | **tient** | 0,136 à 0,459 et σ_f 0,0376 redonnés ; « 0,002 à 0,004 » ambigu (M13) |

« Tombe en l'état » : la figure ne peut pas entrer au mémoire telle qu'elle est compilée ; ses données sont
justes, et chacune se répare par un réglage d'axe ou une phrase de légende (§ 6). Je n'ai corrigé ni axe ni
phrase : seulement deux nombres (§ 7).

## 1. Méthode

1. **Les nombres** (`recalcul.py`). Chaque `\def` des trois fichiers `*-nombres.tex` est refait depuis les
   fichiers commités sous `mesures/`, puis écrit avec autant de décimales que le nombre du lot et comparé
   comme chaîne. Là où un second fichier existe, je l'ai pris plutôt que celui du lot :
   - la pièce du signe des zéros et la part des −0 du 20b : comptées dans
     `mesures/genome/predictif-elagage/histo-toutes-gptoss20b.npz` (72 tenseurs, 19 110 297 600 poids), pas
     lues dans `zero-compte-20b.json` (témoin : les deux s'accordent à 1e-12) ;
   - les gains de fichiers : `juge/J-T0-fichiers.json` (décodeur du juge de la construction), pas
     `codon/tailles.json` ;
   - toutes les KL, médianes, centiles, différences appariées, σ par fenêtres et σ par positions : refaits
     depuis les fichiers **par position** (lot B pour R1, `juge/kl/kl-neuf-*-positions.csv` pour les fenêtres
     neuves, `moteur/O/journaux/o3/c4-20b-comparer.csv` pour le mode exact sur R1), pas lus dans les JSON
     résumés ni dans les CSV par fenêtre.
   Conventions : médiane = moyenne des deux valeurs du milieu ; σ par fenêtres = écart-type (ddof = 1) des
   dix moyennes de fenêtre divisé par √10 ; centile 99,9 = interpolation linéaire de numpy. **Cassure** :
   `--casser` multiplie la part des −0 lue par 1,01 ; l'écart à la diagonale de III-8.3 sort faux (2 écarts,
   `journaux/recalcul-casse.txt`).
2. **La régénération** (`regenerer.py`). `git archive` de HEAD (sans conversion de fins de ligne) des scripts
   et des mesures qu'ils lisent, dans un dossier temporaire ; les trois scripts y écrivent ; SHA-256 de chaque
   fichier écrit contre le blob commité. **33 sur 33 égaux.** **Cassure** : une unité de fréquence déplacée
   d'un octet à l'autre dans la table de III-8.2 (somme gardée à 4 096) : `codon-octets-v10.csv` diffère, seul
   (`journaux/regenerer-casse.txt`). Deux cassures plus grossières sont arrêtées par les gardes du lot
   lui-même avant toute écriture (une passe de `j1-s2-passes.csv` changée : assertion contre
   `j1-s2-verdicts.json` ; une fréquence augmentée seule : somme ≠ 4 096) : les gardes du lot tiennent.
3. **Les points tirés** (`points.py`, graine 20261027). Une ligne tirée par série (57 contrôles sur 22 CSV),
   recalculée à la source. Une valeur propre nulle à l'arrondi est écrite `nan` par le lot (rien à tracer sur
   un axe logarithmique) : le juge applique la même règle (1 551 valeurs, toutes au-delà du rang). **Cassure** :
   valeur recalculée décalée d'un millième relatif : 50 écarts sur 57 (les 7 restants sont des zéros, des
   entiers ou des `nan`).
4. **Les pages.** Pilote du lot copié en `memoire/essai/pilote-juge-construction.tex` (ignoré par git),
   compilé par `lualatex` de MiKTeX, deux passes par langue ; pages rendues par `pdftoppm` et lues.
5. **Les lectures** (`lectures.py`). Chaque question « faux ou trop beau » est chiffrée (L1 à L9 ci-dessous),
   depuis les mêmes fichiers commités.

## 2. Les graves

**G1. III-9.3 : trois points sur soixante sont hors du cadre, dont celui que la légende cite.** Les bornes
des axes (−0,33 à 0,08 ; −0,085 à 0,035 ; −0,36 à 0,08) coupent sans le dire :
- panneau 2 (λ = 0 contre λ = 1), R1, **fenêtre 7 : d = +0,0609** (borne 0,035). C'est la seule fenêtre de R1
  contre λ = 0, celle qui fait de B2 un verdict « de justesse » (2,1 σ), et la légende la nomme (« la
  fenêtre 7 contre ») : la figure montre neuf points négatifs et aucun point contre ;
- panneau 2, fenêtres neuves, fenêtre 2 : d = −0,0922 (borne −0,085) ;
- panneau 1 (λ = 1 contre frontière), R1, fenêtre 7 : d = −0,3453 (borne −0,33).
Les moyennes et les bandes sont justes (elles comptent ces points) ; c'est le dessin qui les retire. Lu à
300 dpi : la rangée 7 du panneau 2 en haut et la rangée 2 du panneau 2 en bas sont vides. Une échelle qui
cache le point contraire rend le verdict plus beau qu'il n'est.

**G2. III-8.8 : un expert sur 96 est hors du cadre.** L'axe vertical va de 4 à 10 % ; l'expert 26 de la
couche 0 du 120b porte **11,68 %** de −0 (`J-T1-echantillon.csv` : 2 906 283 sur 24 883 200). C'est le plus
haut des 96, et la légende parle justement de la variation d'un expert à l'autre (« la première couche du
20b est au-dessus de la moyenne ») : le point le plus au-dessus, celui de la première couche du 120b, n'est
pas dessiné. La conclusion (le gain du fichier ne dépend pas de l'échantillon) ne change pas ; une donnée
retirée sans le dire, si.

**G3. III-9.1 (c) : « l'aire est le sur-apprentissage résiduel » est faux.** L1 (`journaux/lectures.txt`) :
l'aire moyenne entre la part cumulée en calibration et celle vue par l'évaluation vaut **0,318 pour le
synonyme et 0,168 pour la frontière**. Or la frontière ne sur-apprend pas au sens de 07 : son coût de sortie
vu par l'évaluation égale son coût de calibration (16,09 contre 16,50, rapport 0,975), quand celui du synonyme
monte de ×1,67 (6,15 → 10,28). La moitié de l'aire ombrée existe donc sans sur-apprentissage : elle vient de ce
que la part cumulée en calibration atteint 1 au rang 1 329 par construction (λ_k = 0 au-delà), pour toute
variante. Le sur-apprentissage résiduel est ce que 07 § 2 et la note du lot B mesurent : l'écart entre ÷ 2,68
et ÷ 1,57 (la légende le dit juste, en (c)) ; l'annotation dans le dessin le contredit. La note du lot B
(F-S1) proposait cette lecture ; le lot l'a dessinée sans la vérifier contre la frontière, qui est pourtant
tracée dans le même panneau.

**G4. III-9.2 : la lecture de la queue repose sur trois positions et ne se refait pas.** La légende : « le
99,9e centile bouge à peine avec λ = 1 (4,07 → 3,93) et baisse avec λ = 0 (3,37) : la queue est celle des
bascules de routage ». L3 : chaque 99,9e centile de 2 550 positions laisse **3 positions** au-dessus de lui.
Contre la frontière, au 99,9e centile :

| | R1 (la figure) | fenêtres neuves (juge de la construction) |
|---|---|---|
| λ = 1 | −3,4 % | **−20,8 %** |
| λ = 0 | −17,2 % | −15,9 % |

« Bouge à peine avec λ = 1 » ne se retrouve pas sur dix autres fenêtres ; et la juxtaposition 3,93 / 3,37 fait
lire λ = 0 sous λ = 1 dans la queue, la comparaison même que le juge de la construction a **barrée** (M2 :
« un 99,9e centile de 2 550 positions tient à deux ou trois positions » ; 07 § 4.2 quater barré). La phrase
écrite est vraie de R1 ; ce qu'elle fait conclure ne l'est pas. Les courbes, elles, sont justes.

**G5. III-9.3 : le panneau 1 des fenêtres neuves mêle deux chemins, et la légende dit « par le moteur ».** Les
fenêtres neuves n'ont la frontière que par la référence substituée et λ = 1 que par le moteur
(`apparie-par-fenetre.csv`, comparaison `neuf-l1-moteur-contre-frontiere-sub`). Le juge de la construction le
dit (JUGEMENT-construction § 9) : ce mélange « n'est publié qu'à titre indicatif ». La figure en fait une bande
de verdict (« 3,4 σ, 9/10 < 0 ») et la légende écrit « par le moteur pour les deux premiers panneaux ». L4
mesure ce que le mélange déplace, sur R1 où les deux chemins existent pour les deux variantes :

| R1, λ = 1 contre frontière | d̄ | σ_f | z |
|---|---|---|---|
| référence substituée seule (chemin du lot B) | −0,1118 | 0,0296 | 3,78 |
| moteur seul | −0,1103 | 0,0292 | 3,78 |
| λ = 1 moteur contre frontière substituée (le mélange des neuves) | −0,1118 | 0,0297 | 3,76 |

Le nombre tient (0,0015 de d̄) ; c'est le protocole écrit qui est faux, et le statut « indicatif » qui est
perdu.

## 3. Figure par figure

### III-8.1, la roue des seize codons — tient
Nombres : 12 tenseurs, 3 185 049 600 poids, +0 et −0 à 6,85 % chacun (histo-12) ; pièce 0,9999999967 bit,
P(+0) 6,3920 %, P(−0) 6,3929 %, 72 tenseurs — tous redonnés, la pièce par un autre fichier que celui du lot.
Point tiré : code 11, part 0,054595. Réserves : M1, M2. Belle : la plus claire du lot.

### III-8.2 et III-8.3 — tiennent
III-8.2 : points tirés (octets F6 en v1.0, 9A en v1.2) justes ; 256 octets non nuls en v1.0, 225 en v1.2 dans
la table dessinée (120b, couche 18, up, κ = 1) ; lignes 7 et F pâles : codes ±12 à 1,46 % chacun. III-8.3 :
écart à la diagonale de −0,00017 à +0,00016 bit sur 180 tenseurs, redonné ; « couche 0 » marque bien les deux
points du 120b à 0,234 et 0,239.

### III-8.4, l'accumulateur — tient
Les comptes du test A1 (8 640 lignes, 2 486 216 demi-octets 8) ne sont dans aucun journal chiffré : ils sont
dans 06 § 1 et ARCHITECTURE § 4.16, et le journal `essais-espace-2026-10-17-a.log` porte
`test gemv_lit_le_code_8_comme_0 ... ok` (vérifié). La grille de 96 × 90 cases = 8 640 = 3 × 2 880 lignes.
J'ai cherché si −0 peut s'atteindre par sous-dépassement (une somme exacte non nulle arrondie à zéro garde
son signe) : la démonstration de 05 § 4.2 l'exclut, parce que v est entier (|v| ≥ 1, valeurs doublées de
ggml) et x un f32, donc v·x + s est un multiple de 2⁻¹⁴⁹ ; le diagramme est juste. La case rouge de la
cassure fait 0,45 mm à l'impression (M15).

### III-8.5, la colonne — tient
Gain de colonne = `zero_octet_kappa − zero_demi_octet_kappa_colonne` ; seuls 0g (0,1416) et 0u (0,1231)
passent 0,015 ; ramenés au 20b : 0,0037 bit par poids et 8,78 Mo ; ailleurs de −0,0045 à +0,0061 bit
(« quelques millièmes au plus, ou négatif » : juste) ; gain du zéro 0,1279 bit par `J-T0`. Seuil 0,015 :
05 § 4.3 (règle du choix par matrice) et ARCHITECTURE § 4.16.

### III-8.6, le J1 et ce qu'il attribue (refaite selon R1) — tient
Tous les nombres redonnés : médianes 1,988 et 2,890, r 1,454, σ 5,6 %, bande 1,7634 à 2,2116, octets ×0,9671
(+3,4 %), losange 2,055 ; motif croisé J-bis 1,801 / 2,501 / 2,528 / 1,808, ×1,388 et ×0,715, aucune passe
écartée ; encart 1,742 et 1,343 (s2), 1,731 (J6), 0,981, ×1,26, 65 / 267 473 extents ; cascade 2,004,
2,889, 3,711, ×1,442, ≤ ×1,034, ×1,394, ×1,284. Le 1,388 du lot contre le 1,389 du juge du placement :
1,388 est le rapport des médianes exactes (2,50108 / 1,80135), 1,389 celui des médianes arrondies à trois
chiffres (1,38867) ; le lot a raison et le dit. **R1** : les quatre panneaux demandés sont là ; aucune phrase
barrée (« la disposition rend 30 % », « le fichier, pas le format », la cascade F-J2 d'origine, la lecture de
F-S7) n'est dans la légende ; la dernière phrase dit que le gain ne se transporte pas à un autre disque.
Réserves : M3, M4, M5.

### III-8.7, le format v1.2 au bit près — tient
Contre ARCHITECTURE §§ 4.3, 4.7, 4.16 et 05 § 4.3 : magie (0, u8[8]), majeure (8), mineure (10, 0 → 2),
drapeaux (12, u32 ; bits 0 à 5 et « 6 à 31 : 0 »), SHA-256 (32), empreinte64 (4 088) ; entrée du répertoire
de 64 o : 0, 8 (4 × u32), 24, 32 (2 × u64), 48 (2 × u16), 52, 56 (`empreinte_canonique`) ; bit 5 RAPIDE
refusé avec le bit 3 (ARCHITECTURE, tableau du lot B) ; 31 octets à fréquence nulle, 225 octets. Deux cases
imprécises : M6.

### III-8.8, le codon par le décodeur du juge — tombe en l'état (G2)
Nombres redonnés : 32 + 64 = 96 experts, 96 tiennent, 0 demi-octet 8, 40 témoins sur 40 ; parts 6,39 et
6,28 % (par histo-toutes et zero-compte-120b) ; gains 0,12791 et 0,12562 bit ; 305 561 600 et 1 800 486 912
octets ; 11,16 → 10,85 et 57,73 → 55,93 Go ; seuil A-C2 0,12 (05 § 4.6, critères déclarés avant). Point tiré : 120b, couche 5,
expert 120, 6,1794 %. Le cadre coupe l'expert à 11,68 %.

### III-9.1, la mutation synonyme dans la base propre de H — tombe en l'état (G3)
Nombres redonnés : rang 1 329 (saut de 5,8·10⁻³ à 1,6·10⁻¹⁴ entre k = 1 328 et 1 329 ; 1 329 entrées de
calibration : 07 § 2 et duplication.md), Σe_k 40,07 → 48,01 (+20 %), 16,50 → 6,15 (÷2,68), 16,09 → 10,28
(÷1,57), λ_max 279,5, au moins 0,119 vu par l'évaluation au-delà du rang, 54 → 61 % de Σe_k au-delà du rang.
La légende anglaise disait « the 2 880 directions beyond » (au-delà du rang il y en a 1 551 ; le français
« sur 2 880 » était juste) : corrigé (§ 7). L'inquiétude du lot sur la couleur de la légende de (a) est sans
objet : lue à 500 dpi, l'entrée est orange tiretée dans les deux langues (le gris venait d'un rendu à basse
résolution). Réserves : G3, M7, M9.

### III-9.2, la queue de la KL — tombe en l'état (G4, légende)
Médianes 1,314 / 0,163 / 0,061 / 0,056 et 99,9e centiles 6,78 / 4,07 / 3,93 / 3,37 refaits depuis les
positions (même valeur que `juge kl` au dernier chiffre écrit) ; 2 550 positions. Points de survie tirés
justes. « Divise par trois environ » : 2,65 et 2,92.

### III-9.3, le critère B2 fenêtre par fenêtre — tombe en l'état (G1, G5)
Les 30 nombres (moyenne, σ, z, fenêtres négatives, trois comparaisons, deux jeux) sont refaits depuis les
positions et tiennent. Lignes y et étiquettes des fenêtres justes (fenêtre 0 en haut).

### III-9.6, la frontière des variantes à 768 experts — tient (un nombre corrigé)
Bits (compagnons réels : `bits_par_poids_utiles`), KL, σ_f et σ_n redonnés ; λ = 0 achète 0,0204 de KL pour
0,0856 bit ; exact 0,0037. **R3** : seuls des points à 768 experts (et deux repères dits), aucun trait vers la
ronde ; la légende le dit. « Trois à six fois trop petit » : σ_f / σ_n vaut 5,70 (frontière), 3,25 (λ = 1),
3,30 (λ = 0) et **8,88 (Q2_0)**, dont le ± 0,019 est publié dans 07 § 4.1 : corrigé en « de trois à neuf »
(§ 7). Réserves : M11.

### III-10.1, les experts vus — tient
11 jamais routés, 2 R1 seul, 23 neuves seules, 732 les deux ; 490 560 appels par jeu = 10 fenêtres × 24 couches
× 4 experts × 511 jetons ; intensité m = 10 · sorte + 9,99 · log10(1 + appels) / log10(1 + 9 331), redonnée sur
un point tiré. Réserves : M12.

### III-10.3, la difficulté des fenêtres — tient
Frontière de 0,136 à 0,459 sur R1, σ_f 0,0376 ; le mode exact de R1 par le fichier par position du lot O.
Les chemins de chaque série sont dits juste. Réserves : M13.

## 4. Les réserves de l'inventaire

- **R1** : tenue dans III-8.6 (§ 3). La phrase barrée survit **hors de ce flux** : `genome/construction-codon-
  pour-le-memoire.md` § 5 F6 (« elle doit montrer que la disposition du fichier, à contenu égal, en rend
  30 % ») et § 3, dernier point (« un effet de disposition sur le disque d'un ordre de grandeur plus grand que
  l'effet du format ») ; à barrer par son auteur ou l'orchestrateur, pas par moi.
- **R2** : sans objet ici ; « la longueur des requêtes décide » n'est nulle part.
- **R3** : tenue (III-9.6).
- **R4** : sans objet (III-7.2 est au lot « ronde »).
- **Autres phrases barrées** cherchées dans les trois fichiers de figures : G1 et G2 de JUGEMENT-construction
  (×2,00 et ×1,24 comme gains du mode rapide) absents ; la cascade utilise r(R/B) = 1,284 du juge. M2 de
  JUGEMENT-construction : G4.

## 5. Le design (la beauté à égalité avec la justesse)

- **Palette** : celle du préambule, partout. Au ch. 9-10, une table de couleurs tenue d'une figure à l'autre
  (frontière gris SerieF, λ = 1 bleu SerieA, λ = 0 vert SerieC, Q2_0 orange SerieD ; R1 bleu, neuves violet).
  Au ch. 8, le bleu et le rouge veulent dire 20b et 120b en III-8.3 et III-8.8, mais v1.0 et v1.2 en III-8.6
  (M5). Au ch. 9, le bleu est λ = 1 partout sauf en III-9.3 où il est R1 ; et le lot « espaces latents » met
  le synonyme en SerieB (son juge, M7) : à unifier quand III-9.1 sera assemblée.
- **Les plus belles** : la roue (III-8.1), le format (III-8.7), la grille des experts (III-10.1). La base
  propre de H (III-9.1) est la bonne idée de transformation « avant et après » demandée par Stone, à
  condition de corriger ce que dit son aire (G3).
- **Une idée par figure** : III-8.6 en porte cinq (bruit ABBA, octets contre vitesse, motif croisé,
  fragmentation, cascade) et une légende d'une vingtaine de lignes ; R1 a demandé ces panneaux, mais deux
  figures ((a)(b) puis (c)(d)) se liraient mieux.
- **Lisibilité** : en français, le titre du panneau (c) de III-8.6 recouvre le « e » du titre de l'encart
  (« …étage disque)ncart », lu à 400 dpi ; l'anglais, plus court, passe) ; l'annotation de III-9.1 (c) est
  traversée par deux courbes tiretées et se lit comme barrée ; III-9.6 tient cinq points dans un grand plan
  vide ; III-10.3 relie par des traits des fenêtres qui ne se suivent pas.
- **Assemblage** : le lot appelle « (c) » la part cumulée de III-9.1 ; l'inventaire et le lot « espaces
  latents » appellent III-9.1 (c) la rangée de 32 poids. Deux panneaux (c) pour une même figure : à résoudre
  à l'assemblage.

## 6. Ce qu'il faut faire (au lot ou au rédacteur ; je ne l'ai pas fait)

- G1 : bornes de III-9.3 élargies (panneau 1 : −0,36 ; panneau 2 : −0,10 à 0,07), ou chaque point hors cadre
  marqué d'une flèche et de sa valeur ; une règle dans le script : arrêter si un point sort du cadre.
- G2 : III-8.8, ymax 12 (même règle).
- G3 : retirer « l'aire est le sur-apprentissage résiduel » ; écrire : « la frontière garde son coût vu par
  l'évaluation (16,09 contre 16,50) ; celui du synonyme monte de ×1,67 (6,15 → 10,28) : c'est le
  sur-apprentissage résiduel. L'aire ombrée n'en est pas la mesure : la frontière en a une aussi (0,17 contre
  0,32), qui vient du rang de H. » Ombrer, si l'on veut une aire, la différence des deux aires.
- G4 : réécrire la phrase de la queue : trois positions au-dessus de chaque 99,9e centile ; contre la
  frontière, λ = 0 l'abaisse de 17 % sur R1 et de 16 % sur les fenêtres neuves, λ = 1 de 3 % sur R1 mais de
  21 % sur les neuves ; entre λ = 0 et λ = 1, la queue n'est pas comparable à cette taille (barré, M2).
- G5 : légende de III-9.3 : « en bas, panneau 1 : λ = 1 par le moteur contre la frontière par la référence
  substituée (deux chemins, à titre indicatif, JUGEMENT-construction § 9 ; sur R1 le mélange déplace d̄ de
  0,0015) ; panneau 2 par le moteur ; panneau 3 par la référence substituée ».
- Les mineurs : § 7.

## 7. Les mineurs

- **M1. III-8.1, 12 tenseurs au lieu de 72.** La décision du lot (« le seul histogramme des 16 codes
  commité ») est fausse : `histo-toutes-gptoss20b.npz` (commit 5043ca7) a la même forme (72, 256, 17, 16) et
  couvre les 19 110 297 600 poids ; son code 8 compte 1 221 698 587, le `moins_zero_fondus` de `tailles.json`.
  La figure montre donc deux valeurs pour la même part : 6,85 % (rayons, 12 tenseurs dont la couche 0, riche
  en zéros) et 6,39 % (pièce, 72 tenseurs). Les 72 donneraient une figure d'une seule source.
- **M2. III-8.1, valeurs et épaisseurs.** Les valeurs écrites (±1 à ±12) sont celles de ggml, le double des
  valeurs E2M1 de la norme (±0,5 à ±6), le facteur 2 étant dans l'échelle : à dire. Les codes sont rangés par
  valeur à pas égal (24°), pas « placés à leur valeur ». L'épaisseur vaut 0,4 + 44 p pt : affine, pas
  proportionnelle (le rayon du zéro s'épaissit de ×1,88 au fondu, pas ×2).
- **M3. III-8.6, encart à deux séances.** Barres : A120 et C120 de s2 (`troncons disque`), C120 « un
  extent » de J6 (lecteur Python du juge du placement, 2 à 5 % plus lent, JUGEMENT-placement § 5.2). Les
  rapports écrits ne sont pas ceux des barres : 0,981 = C[U] / A[U] de J6 (A[U] = 1,765, non dessiné) et
  ×1,26 = C[U] / C tiré de J5 (1,378, non dessiné) ; lus sur les barres : 0,994 et ×1,29. Et 0,981 (médianes)
  diffère du 0,980 écrit par le juge du placement (moyennes : 0,97985) sans que le lot le dise, comme il l'a
  fait pour 1,388.
- **M4. III-8.6 (d), la cascade.** Le facteur « motif » est un reste, r(B/A) / toit des octets : c'est une
  borne basse (« ≥ ×1,394 »), écrite comme une mesure. L'étage disque seul du 120b, dans la même séance,
  donne B/A = 1,370 (L6) : il pourrait l'appuyer. Le compagnon R est le compagnon **frontière** du 120b (la
  légende dit « le mode rapide ») ; sa KL (proxy 0,14) n'est pas dite.
- **M5. III-8.6, mise en page.** Titres (c) et encart qui se chevauchent en français ; cinq idées ; bleu et
  rouge de sens différent de III-8.3 et III-8.8.
- **M6. III-8.7, deux cases imprécises.** « L, E, k… 64 · 136 · 264 » : au décalage 64 est la taille du GGUF,
  L est à 72. « tailles 16 · 24 » couvre trois champs (16 alignement, 20 taille de l'en-tête, 24 taille du
  fichier). La notation « décalage · x » mêle valeur (« 8 · 1 »), type (« 12 · u32 ») et second décalage.
- **M7. III-9.1, l'amortissement du codeur.** Le H tracé est sans amortissement ; le synonyme a été choisi
  avec H + δ* moy(diag H) I, δ* = 1 (07 § 2), soit **0,41** ajouté à chaque direction (L2) : plus que le poids
  d'évaluation des directions muettes (0,12 à 0,23), et seules 433 valeurs propres le dépassent. « Ne pèsent
  rien en calibration » est vrai de H, pas du coût que le codeur a minimisé : à dire.
- **M8. III-9.1, nombre faux en anglais — corrigé.** « the 2 880 directions beyond (grey) » devient « the
  directions beyond (grey), out of 2 880 » (1 551 sont au-delà ; le français était juste).
- **M9. III-9.1, détails.** L'annotation de (c) est traversée par deux courbes ; l'indice « év » reste
  français dans la légende anglaise de (a).
- **M10. III-9.6, nombre faux — corrigé.** « trois à six fois trop petit » devient « de trois (synonymes) à
  neuf (Q2_0) fois trop petit » (FR et EN) : σ_f / σ_n = 3,25 à 8,88 (L8).
- **M11. III-9.6, repères.** Le point exact est à 3,8506 bits (`bpp_total_03_v10`) alors que les compagnons
  sont à leurs bits utiles ; la même définition donne 3,8618 pour le v1.0 (J-T0). « La seule requantification
  sous 2,6 bits » (07 § 4.1) est contredite par 07 lui-même (recettes : « sous 4 bits, seuls Q2_0 et Q1_0
  passent »). La KL de Q2_0 vient de llama.cpp sur le processeur, un autre chemin que la référence substituée.
- **M12. III-10.1.** « au plus 9 331 pour un expert » : R1 et neuves réunies (un seul jeu : 4 764), à dire.
  Les appels comptent les 511 jetons de chaque fenêtre, dont 256 de contexte non notés. « Un changement confiné
  à eux ne bougerait aucune KL » vaut sous le routage de la référence (les grilles viennent de
  `ref-openai-bis-20b.bin` et `routage-ref-juge-20b.bin`) ; une variante qui bascule peut les appeler.
- **M13. III-10.3.** « les deux chemins diffèrent de 0,002 à 0,004 en KL » : c'est la KL entre les sorties des
  deux chemins (S3-K : 0,0017 et 0,0038) ; leurs KL contre la vérité diffèrent de 0,0014 au plus sur R1
  (frontière ; −0,0076 à +0,0010 par fenêtre) et de 0,0002 sur les neuves (λ = 0). Lu comme écart des valeurs
  tracées, il est dix fois trop grand.
- **M14. Nombres tapés à la main.** Le lot dit n'en avoir tapé que deux (les comptes de A1) ; il y en a
  d'autres (0,002 à 0,004, trois à six, 2,6 bits, 255, 256 jetons, dix fenêtres, (0, 8, 16, 23), 2 880 × 2 880,
  2^±10, les décalages de III-8.7). Je les ai tous cherchés à leur source : deux étaient faux ou ambigus (M10,
  M13).
- **M15. Débordements et petites tailles.** Débordements de 4,4 pt (roue), 2,6 pt (accumulateur, en français,
  non signalé par le lot), 2,0 pt (format), 3,5 pt (forêt) ; la case de la cassure de III-8.4 fait 0,45 mm.
- **M16. La note de reprise du lot** écrit « 17 figures » : le pilote a 14 figures sur 17 pages.

## 8. Ce qui pourrait être faux (dans ce jugement)

- Mes calculs lisent les mêmes fichiers commités que le lot : l'indépendance est celle du code (et, pour la
  pièce, les gains et toutes les KL, celle du fichier lu). Une erreur dans une mesure commitée passerait chez
  les deux ; les mesures elles-mêmes ont leurs juges (JUGEMENT-construction, JUGEMENT-placement).
- Mes conventions (médiane, ddof = 1, centile linéaire de numpy) sont celles du lot ; une autre déplacerait le
  troisième chiffre d'un centile 99,9 et σ_f de 5 %.
- 9 331 : je l'ai d'abord lu comme le maximum d'un seul jeu (écart), puis comme celui des deux jeux réunis
  (juste) ; c'est une lecture de la légende, que je donne comme ambiguë et non comme fausse.
- G3 suppose que « sur-apprentissage » a le sens de 07 (l'écart entre le coût de calibration et celui vu par
  l'évaluation). Si l'aire voulait seulement montrer où va l'erreur, c'est une description, mais alors le mot
  est faux.
- G4 compare, sur les fenêtres neuves, λ = 1 par le moteur à la frontière par la référence substituée (λ = 1
  substitué n'y a pas été passé) : deux chemins encore. Pour λ = 0, les deux chemins donnent 3,61 et 3,51 au
  99,9e ; −21 % pour λ = 1 a peu de chances d'être un effet de chemin, mais ce n'est pas un seul chemin.
- J'ai lu les pages à 130 dpi et zoomé à 300-600 dpi là où je cherchais ; un chevauchement plus petit a pu
  m'échapper. Le jugement de design est le mien, pas celui d'un designer.
- Ma lecture de « tombe en l'état » est sévère pour III-8.8 (un point, un réglage d'axe) ; je la garde parce
  qu'une figure ne retire pas une donnée sans le dire.

## 9. Reproduire

```
cd ~/dev/active/troncons/outils/genome/tome3/juge-construction
python -I -X utf8 recalcul.py --sortie journaux/recalcul.csv   # 154 nombres ; --casser : doit tomber
python -I -X utf8 points.py                                    # 57 points, graine 20261027 ; --casser
python -I -X utf8 lectures.py                                  # L1 à L9
python -I -X utf8 regenerer.py                                 # 33 fichiers au bit ; --casser
```
Mémoire de pointe de chaque outil sous 1 Go. Pilote : `memoire/essai/pilote-juge-construction.tex` (copie du
pilote du lot, ignoré par git) ; `lualatex` deux fois, puis `lualatex -jobname=pilote-juge-construction-en
"\def\ANGLAIS{1}\input{pilote-juge-construction.tex}"` deux fois.
