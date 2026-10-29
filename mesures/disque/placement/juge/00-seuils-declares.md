# Juge du placement disque : plan et seuils, déclarés avant toute mesure et tout recalcul

Déclaré le 2026-10-22 à 12 h 45, par le juge indépendant de `genome/08-placement-disque.md` (qui n'a rien
écrit de l'enquête). À cette heure, **je n'ai rien mesuré et rien recalculé** : j'ai lu 08, la note de
reprise, la note pour le mémoire, les outils `outils/disque/placement/*.py` (pour comprendre, sans les
réutiliser), le moteur (`moteur/bins/troncons/src/main.rs`, fonction `disque` ; `moteur/crates/trc-es`), le
format (`moteur/crates/trc-format/src/lib.rs`, en-tête et RÉPERTOIRE), et les nombres que 08 cite.

## 0. Ce que j'ai vu en lisant, et qui appelle un test (dit avant, pour qu'on sache d'où viennent les tests)

1. **Un fichier écrit le 22 et rapide six heures après.** Le compagnon λ = 0 du 20b,
   `~/dev/essais/troncons/genome/synonyme/trc/gpt-oss-20b-synonyme-l0.rapide.trc` (R20 ci-dessous),
   est créé le 2026-10-22 à 0 h 46 min 45 s et écrit pour la dernière fois à 0 h 51 min 46 s (horodatage NTFS) par
   `trc-rapide coder`, qui écrit avec `trc_format::Ecrivain`, l'écrivain du codeur (8,31 Go en 301 s,
   `mesures/genome/construction/synonyme/rapide/coder-synonyme-l0.json`). Le juge de la construction l'a lu à
   l'étage disque à 6 h 50 (`mesures/genome/construction/juge/vitesse/20b-disque-0[1-6]-*.json`, horodatage UTC
   10 h 49-10 h 51) : R20 2,475 et 2,472 Go/s, B20 2,461 et 2,443, A20 1,786 et 1,775. 08 conclut que « le neuf
   retombe en moins de deux heures » et que la rapidité tient « à un état du disque du 17 ». Test J4.
2. **Les lectures non coupées de C120 vont, par lecture, à 0,763 Go/s à 4 en vol** (08 § 3.4) : quatre telles
   lectures ensemble feraient 3,05 Go/s, plus que tout débit agrégé mesuré à 4 en vol sur ce disque (au plus
   2,72, B20, p4). Soupçon : une lecture entière va plus vite quand ses voisines en vol sont des lectures
   coupées en petits morceaux, servies l'une après l'autre ; la comparaison « par lecture » de C120 non coupé
   à A120 (« 1,6 fois plus vite à contenu égal ») serait alors faussée par la composition de la file. Tests
   J0-c et J6.
3. **Le critère de H1** (« le modèle ajusté sur les lectures paires prédit la durée totale des impaires à 10 %
   près ») et le contrôle « le modèle rend le débit de C120 à 1 % près » passent par la moyenne : une droite des
   moindres carrés passe par le point moyen, et deux moitiés tirées du même ensemble ont la même moyenne. Un
   modèle constant passerait peut-être aussi. Test J0-b.
4. **« p6 tuée par les nombres »** : le gain de bout en bout prédit (1,05 à 1,09) est comparé au plancher
   S = 11,8 %, tiré du bruit de l'étage disque du 120b, et non au bruit des séries de bout en bout (2,8 % et
   4,3 % en p3 ; 0,2 à 0,6 % au juge de la construction). Tests J0-f et J7.

## 1. Les grandeurs nommées et les seuils

- **e_soi** (même définition que 08 § 2.1 et `analyse.py`) : pour un fichier et un réglage d'une séance,
  (max − min) / moyenne de ses passes. **S_j = max(2 × max e_soi de la série, 11,8 %)**, la règle de 08, gardée
  pour que mes verdicts se comparent aux siens ; « diffèrent » si |r − 1| > S_j, « égaux » si |r − 1| < S_j / 2,
  « entre deux » sinon. Le plancher 11,8 % (2 × 5,9 %, B120, s2) est celui de 08.
- **σ_inter** : écart type relatif de r(B20 / A20) entre les sept séances commitées qui ont les deux fichiers à
  la profondeur 4 (p2a, p2b-D, p2b-F, p2b-Fb2, p4 à q = 4, p5 à q = 4, juge de la construction ; p2b-Fb exclue
  pour son arrêt de 21 s, p2b-D2 sans B20). Calculé de tête sur les nombres de 08 : 3,0 % ; il sera recalculé
  par mon script (J0) avant toute mesure. **Tolérance de reproduction T_a = max(2 σ_inter, S_j / 2).**
- **Bruit des sous-ensembles** pour le modèle de C120 : demi-largeur à 95 % de t₁ et de τ ajustés sur des
  sous-échantillons de taille N (ma taille) tirés des profils commités p2a-17 et p2a-18 (200 tirages, ma graine),
  calculée en J0 avant J5. **Tolérance T_τ = max(2 × cette demi-largeur, 10 %)**, de même T_t pour t₁.
- **Bruit par classe de morceaux** : pour les classes n = 1, 2-9, 10-99, ≥ 100, l'écart relatif entre les
  médianes des passes p2a-17 et p2a-18 de la durée ramenée à 12 Mo ; **tolérance par classe
  T_n = max(10 %, 2 × cet écart)** (10 % est la tolérance que 08 a déclarée pour sa prédiction globale).

**Ma graine** : **G = 1618033**. Un tirage de k éléments parmi n se fait en rangeant les indices i par
SHA-256(« juge-placement:1618033:i ») croissant et en gardant les k premiers, dans cet ordre (stable d'une
version de Python à l'autre, sans générateur caché).

## 2. Les instruments (les miens, sous `outils/disque/placement/juge/`)

- **Carte** : FSCTL_GET_RETRIEVAL_POINTERS par ctypes, poignée ouverte avec FILE_READ_ATTRIBUTES seulement,
  RÉPERTOIRE du `.trc` relu par mon propre analyseur (en-tête de 4 096 octets, section 3, entrées de 64 octets,
  empreinte64 = 8 premiers octets du SHA-256 vérifiée). **Témoins** : (i) la somme des grappes des extents égale
  ⌈taille / grappe⌉ pour chaque fichier ; (ii) pour les fichiers de moins de 1 000 extents, la liste égale celle
  de `fsutil file queryextents` (chemin de Windows, indépendant) ; (iii) le nombre d'extents et la liste égalent
  au bit ceux des cartes commitées de 08 (fichiers inchangés depuis le 17). **Cassure** : un extent retiré, (i) et
  (ii) doivent tomber.
- **Lecteur** : le motif du moteur refait par un autre chemin que `lire.py` : **une seule poignée**
  `FILE_FLAG_NO_BUFFERING | FILE_FLAG_OVERLAPPED`, un **port de complétion**, au plus q lectures confiées au
  système, une requête `ReadFile` par tronçon de `longueur[0]` octets au décalage du RÉPERTOIRE, tampons
  alignés (VirtualAlloc), durée de la remise à la récolte (comme `trc-es`) ; débit = octets / (dernière récolte
  − première remise). Ordre « moteur » : celui de `troncons disque --graine 20261017` (Fisher-Yates par
  xorshift64*, écrit par moi d'après `main.rs`). **Témoins** : (i) mêmes séries que `troncons disque` (le
  binaire du lot A, `~/dev/cibles/troncons-codon/release/troncons.exe disque --n 1500 --graine
  20261017`), une passe de chaque dans la série J2 : rapport dans ± S_j / 2 ; (ii) 16 lectures (ma graine) sans
  tampon égales au SHA-256 à une lecture tamponnée ordinaire au même décalage : 16/16 ; (iii) les unités lues par
  l'hôte du journal SMART (mon propre appel IOCTL_STORAGE_QUERY_PROPERTY, page 02h) avancent de 0,98 à 1,02 fois
  les octets demandés. **Cassures** : (ii) décalage tamponné faussé de 4 096 octets : 0/16 attendu ; (i) une
  passe de mon lecteur freinée exprès (10 ms d'attente avant chaque nouvelle remise) : son rapport à
  `troncons disque` doit sortir de ± S_j / 2.

## 3. Les tests et leurs verdicts déclarés

**J0. Recalcul, sur les fichiers commités, par mes scripts** (aucune mesure). Chaque chiffre publié que 08 tire
d'un journal est « redonné » si je trouve le même au dernier chiffre imprimé, « diffère » sinon (et je dis
pourquoi).
- J0-a : médianes, e_soi, S, rapports et verdicts de p2a, p2b-D, p2b-D2, p2b-F, p2b-Fb, p2b-Fb2, p4, p5 ;
  jetons/s, octets et textes de p3 ; σ_inter.
- J0-b : H1 sur p2a-17 et p2a-18 : t₁, τ, prédiction des impaires. **Puissance du critère de 08** : le même
  critère (somme des impaires à 10 %) appliqué à un modèle constant t = moyenne des paires, et à τ × 0,5 et
  τ × 2. Prédiction : il accepte le modèle constant ; s'il l'accepte, **le critère de 08 n'a pas de puissance**.
  Critère puissant à la place : erreur relative de la médiane prédite par classe de morceaux, sous T_n dans
  chaque classe ; il doit rejeter le modèle constant (sinon il n'a pas de puissance non plus, et je le dis).
- J0-c : **composition de la file** dans p2a-17 et p2a-18 : pour chaque lecture non coupée de C120, la part de
  sa durée pendant laquelle les autres lectures en vol sont des lectures coupées (d'après `debut_us` et
  `fin_us`). Prédiction : la médiane du débit par lecture des non coupées dont cette part dépasse 0,75 dépasse
  celle des non coupées dont la part est sous 0,25 de plus de 5 % (le S_b de 08). Si oui, la comparaison
  « par lecture » de 08 § 3.4 est faussée par la file.
- J0-d : A120 lu en entier (p2a-15, p2a-20) : débit par 5 s, plages sous 0,5 Go/s, ρ entre passes.
- J0-e : les nombres que 08 § 6 cite du lot B (s2-120b) et du juge de la construction, contre leurs journaux.
- J0-f : **puissance de p6** : gain de bout en bout prédit par la formule de 08 (G = T / (T − L (1 − 1/k))) avec
  les k publiés, contre le bruit des séries de bout en bout commitées (e_soi de p3 ; σ du juge de la
  construction sur le 20b). Si G − 1 > 2 × max e_soi de p3, « tuée par les nombres » est faux : la série aurait
  pu trancher avec un seuil tiré de son propre bruit.

**J1. Cartes** de A20, B20, C120, A120, B120 et R20, par mon outil, avec ses témoins et sa cassure.
Verdict : (c) « C120, 267 473 extents » redonné si mon nombre est 267 473 ; toute différence dans les six
cartes est expliquée ou portée comme constat.

**J2. ABBA A20 / B20** (motif du moteur, q = 4, tout le fichier, 768 lectures), A B B A A B B A plus une passe
`troncons disque` de chaque, témoins et cassures du § 2. **(a) redonné** si r(B20 / A20) − 1 > S_j et
|r / 1,423 − 1| < T_a.

**J3. Motif croisé** (ce que ni 08 ni le juge de la construction n'ont fait) : A20 lu avec le motif de B20
(décalages et longueurs du RÉPERTOIRE de B20, dans l'ordre moteur de B20, gardés s'ils finissent dans A20) et
B20 lu avec celui de A20 ; ordre An Ax Bn Bx Bx Bn Ax An (n = motif natif, x = motif croisé). **Si la lenteur suit
le fichier** (état physique) : |Ax / An − 1| < S_j / 2 et |Bx / Bn − 1| < S_j / 2. **Si elle suit le motif**
(format, alignement, tailles des lectures) : Ax / An − 1 > S_j et Bx / Bn − 1 < −S_j. Ma prédiction : elle suit
le fichier.

**J4. R20 contre A20 et B20** (motif natif de chacun, q = 4), A R B B R A A R B B R A. Si
**R20 / A20 − 1 > S_j et |R20 / B20 − 1| < S_j / 2** : un fichier écrit le 2026-10-22 par l'écrivain du codeur
est aussi rapide que B20 plus de onze heures après ; **« le neuf retombe en moins de deux heures » ne vaut pas en
général, « un état du disque du 17 » tombe, et « la manière d'écrire n'est pas la cause » ne vaut que pour
`placer.py --mode filet`, pas pour l'écrivain réel**. Si |R20 / A20 − 1| < S_j / 2 : R20 est retombé entre + 6 h et
+ 12 h, et 08 tient sur ce point (sa descente serait plus lente que celle de D20 et F20). Entre deux : je le dis.

**J5. Le modèle (c) de C120** sur N = 1 200 tronçons tirés par ma graine, deux passes dans le même ordre (q = 4).
Ajustement t(n) = t₁ + (n − 1) τ sur mes positions paires, test sur les impaires. **(c) redonné** si
|τ / 0,366 ms − 1| < T_τ et |t₁ / 17,1 ms − 1| < T_t, et si le critère par classe (J0-b) tient. Le critère de 08
est aussi rapporté, avec son modèle constant.

**J6. C120 non coupé seul.** U = 800 tronçons d'un seul extent de C120 (ma carte, ma graine), lus seuls (aucune
lecture coupée dans la file) sur C120 et sur A120 (mêmes indices : même RÉPERTOIRE, contenu égal au bit, vérifié
par l'égalité des deux RÉPERTOIRES) ; V = 800 tronçons d'un seul extent de B120 (ma graine). Ordre C A B B A C C A
B B A C. Comparaison **agrégée** (Go/s de la passe), seule valide quand la file est homogène. « C120 non coupé
plus rapide que A120 à contenu égal » **tient** si C[U] / A[U] − 1 > S_j ; **tombe** si |C[U] / A[U] − 1| < S_j / 2.
Ma prédiction : il tient (C120 est du 17). Ce que vaudrait C120 contigu dans son état d'aujourd'hui :
C[U] / C120(J5) [calc. sur mes.], à comparer au × 1,43 de 08, qui reste prédit et non mesuré.

**J7. Profondeur 2 contre 4** (mon lecteur, motif natif), A20 et B20, A4 A2 B4 B2 B2 B4 A2 A4 deux fois (quatre
passes par cas), plus deux passes à q = 8 par fichier. (e) « q = 2 plus rapide que q = 4 » **tient** si
q2 / q4 − 1 > S_j sur les deux fichiers ; « plus de profondeur ne cache rien » tient si q8 / q4 < 1 + S_j / 2.
**J7 bis** (si le calme et le temps le permettent) : `troncons mesurer` sur A20, `--profondeur 2` contre 4,
A Q Q A A Q Q A, réglages de p3 (invite wiki-3000, 256 jetons, `--repos 10`) ; mêmes jetons et mêmes octets par
pas exigés ; seuil tiré du bruit de la série : **S_e = 2 × max e_soi des jetons/s de génération**, et je
rapporte aussi le verdict à la règle de 08 (S au moins 11,8 %).

**J8. A120 lu en entier une fois** (4 608 tronçons, ordre de ma graine). (f) **redonné** si au moins une plage de
10 s ou plus sous 0,5 Go/s apparaît ; « liés au temps » est cohérent si les lectures prises dans les plages
lentes ne sont pas celles des plages lentes de p2a-15 et p2a-20 plus que le hasard ne le veut. Si aucune plage
n'apparaît : « non redonné dans ma passe ».

## 4. Le protocole

- **Verrou** `~/dev/verrou-carte.txt`, une ligne « juge placement, date, script, pid », attendu
  s'il est pris, rafraîchi avant chaque passe, rendu après chaque séance (même sur erreur).
- **Calme** : avant et après chaque passe, relevé de deux images à 3 s d'écart des processus des autres flux
  (python, trc-*, troncons, cargo, rustc, juge, genome-capture, llama*, hors les miens, blender-mcp et serveurs
  http) ; un processus qui prend plus de 5 % d'un cœur ou lit plus de 8 Mo en 3 s rend la passe **SOUS CHARGE** :
  elle est journalisée et **ne conclut pas**. Départ d'une séance sur deux relevés vides à une minute d'écart. Je
  ne tue aucun processus ; si `levier.py`, `spectres_svd.py` ou `normalise.py` tournent, j'attends.
- **Secteur** à chaque passe (Win32_Battery BatteryStatus = 2) ; sinon arrêt propre, commit, verrou rendu.
- **SMART** avant et après chaque passe : température, unités lues et écrites par l'hôte, transitions TMT.
- Lecture seule : aucune copie, aucun fichier écrit hors de mes journaux et d'un fichier témoin de 16 Mio pour
  la carte (dans `%TEMP%`, effacé après) ; rien sous `~/dev/modeles/` n'est déplacé ni effacé.
- Journaux : `mesures/disque/placement/juge/` (une ligne CSV par lecture, un JSON par passe, le journal de séance).

## 5. Amendement, déclaré le 2026-10-22 à ~~13 h 40~~ 13 h 19 (heure du commit 495ab4b ; « 13 h 40 » était une heure écrite d'avance, fausse), après la séance principale et avant toute autre mesure

**Ce qui l'appelle.** La séance principale (12 h 56 à 13 h 13) s'est arrêtée proprement à J6-12 : le portable est
passé sur batterie (J8 non fait ; J6-12, finie sur batterie, est écartée comme une passe sous charge, règle § 4).
Trois séries contiennent chacune une passe prise dans un **arrêt du disque** (le phénomène de 08 § 3.5, plages
de 15 à 18 s sous 0,5 Go/s, vu ici sur A20 et R20) : J3-08 (A20, 0,439 Go/s), J4-11 (R20, 0,343), J7-01 (A20 à
q = 4, 0,505). Avec S_j = 2 × max e_soi, une seule telle passe porte S_j au-delà de 180 % : la série ne donne
plus de verdict au seuil (comme p2b-Fb pour 08). La règle du § 1 n'avait rien prévu pour ce cas.

**Règle ajoutée.** Une passe est « à arrêt » si son débit par seconde (octets de chaque lecture répartis sur sa
durée) reste sous 0,5 Go/s pendant 3 s de suite ou plus (dernière seconde partielle exclue). Une passe à arrêt
est journalisée, rapportée, et écartée du calcul de e_soi et des médianes. **Les séries J3, J4 et J7 sont
refaites entières** dans une séance J-bis, mêmes fichiers, mêmes motifs, même ordre (J3 en quatre passes par
cas : la séquence de J3 deux fois) ; une passe à arrêt de J-bis est refaite à la fin de sa série (au plus deux
fois par série). **Les verdicts de J3, J4 et J7 se prennent sur J-bis**, aux seuils des §§ 1 et 3 ; les nombres
de la séance principale sont rapportés à côté, « sans verdict au seuil ». J8 se fait dans J-bis.

**J9, ajouté avant mesure** (ce que J3 de la séance principale suggère sans verdict : la lenteur suivrait le
motif de lecture et non le fichier). Deux variables distinguent les motifs de A20 et de B20 dans mon lecteur :
la **longueur des lectures** (A20 11,8 à 12,1 Mo, B20 11,2 à 11,8 Mo) et, par elle, le **pas des places de la
fenêtre de destination** (la plus longue lecture, comme `HoteEpingle::allouer(prof × lal)` du moteur). Leur
alignement et les écarts entre tronçons ne les distinguent pas (tronçons bout à bout, mêmes proportions
alignées sur 8, 16, 32 et 64 Kio dans les deux RÉPERTOIRES, relevé fait avant cet amendement).
- J9-L : A20, ordre et décalages natifs, longueurs × 0,965 arrondies au-dessous à 4 Kio (« raccourci », comme
  B20) ; B20, ordre et décalages natifs, longueurs × 1,035 arrondies au-dessus (« allongé », comme A20, gardées
  dans le fichier). Ordre An Ar Bn Ba Ba Bn Ar An, deux fois (quatre passes par cas). **Si la longueur décide** :
  Ar / An − 1 > S_j et Ba / Bn − 1 < −S_j. **Si elle ne décide pas** : |Ar / An − 1| < S_j / 2 et
  |Ba / Bn − 1| < S_j / 2.
- J9-P : A20 natif avec un pas de fenêtre de 12 Mio (12 582 912 octets) ; B20 natif avec le pas de A20
  (12 144 640). Ordre Ap Bp Bp Ap ; comparé aux An et Bn de J9-L. **Si le pas décide** : Ap / An − 1 > S_j ou
  Bp / Bn − 1 < −S_j ; sinon |r − 1| < S_j / 2 pour les deux.
- Je ne fais pas de prédiction : la mienne pour J3 (« elle suit le fichier ») est tombée dans la séance
  principale, sans verdict au seuil.

**Réponse par délégation du 2026-10-22, réversible** : refaire J3, J4 et J7 plutôt que de juger sur les passes
sans arrêt de la séance principale. Justification : une règle d'exclusion appliquée après avoir vu les nombres
serait un seuil tiré après coup ; la refaire sous une règle écrite avant est gratuit.

## 6. Amendement, déclaré le 2026-10-27 ~~vers 0 h 55~~ à 0 h 48 (commit a735439 ; « 0 h 55 » était écrit d'avance), après J-bis et avant J10

**Ce qui l'appelle.** J-bis J9-L : A20 lu avec ses décalages mais des longueurs × 0,965 va comme B20 (2,504 contre
1,762 Go/s), B20 lu avec des longueurs × 1,035 va comme A20 (1,785 contre 2,503) ; le pas de la fenêtre ne change
rien (J9-P). La longueur des requêtes décide. Raccourcir une lecture n'est pas un levier (on ne lit plus tout le
tronçon) ; **couper chaque tronçon en deux requêtes** en est un, s'il rend la même vitesse, sans rien réécrire.

**J10.** A20, ordre et décalages natifs ; chaque tronçon lu en **deux requêtes** : la première de
⌊l / 2 / 4 096⌋ × 4 096 octets, la seconde du reste, à la suite (mêmes octets que le motif natif, au bit) ; **q = 8**
(autant d'octets en vol que le natif à q = 4). Ordre An Ah Ah An, deux fois (quatre passes par cas). Seuil comme au
§ 1 (S_j = max(2 × max e_soi, 11,8 %)), passes à arrêt ou à témoin SMART hors de [0,98 ; 1,02] écartées (§ 5, § 2).
**Le levier tient** si Ah / An − 1 > S_j ; **il tombe** si |Ah / An − 1| < S_j / 2. Témoin : le SHA-256 de la
concaténation des deux moitiés de 16 tronçons tirés égale celui du tronçon lu d'une requête (16/16) ; cassure : la
seconde moitié lue 4 096 octets plus loin : 0/16. Ma prédiction : il tient (les lectures de 8,3 Mo de R20 vont
comme B20). Si le calme ne revient pas dans les 30 min, J10 n'est pas faite et passe à « ce qui reste ».

## 7. Amendement, déclaré le 2026-10-27 après J10 et avant J11 (heure : celle du commit qui le porte)

**Ce qui l'appelle.** J10 (3 h 15-3 h 17, calme, témoin 16/16, cassure 0/16) : A20 en deux requêtes par tronçon **à
q = 8** va à 1,502-1,517 Go/s contre 1,700-1,804 au motif natif à q = 4 (× 0,85) : ma prédiction est tombée. J10 mêlait
deux changements : des requêtes de 6 Mo, et huit requêtes en vol au lieu de quatre (J7 : q = 8 coûte déjà × 0,97 à
× 0,91 à pleine longueur).

**J11.** Mêmes moitiés que J10, **à q = 4** (deux tronçons en vol) ; ordre An Ah4 Ah4 An, deux fois. Mêmes seuils et
mêmes exclusions que J10. **Le levier tient** si Ah4 / An − 1 > S_j ; il tombe si |Ah4 / An − 1| < S_j / 2 ; « moins
vite » si Ah4 / An − 1 < −S_j. Je ne fais pas de prédiction.
