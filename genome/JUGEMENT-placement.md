# Le jugement du placement disque (08)

Juge indépendant de `genome/08-placement-disque.md`, de sa note de reprise, de sa note pour le mémoire, de ses outils
`outils/disque/placement/` et de ses mesures `mesures/disque/placement/` (commits 09f87a3 à 5838195). Je n'ai rien écrit
de l'enquête. Mes seuils : `mesures/disque/placement/juge/00-seuils-declares.md` (commit c34d836, 2026-10-22 à 12 h 45,
avant tout recalcul et toute mesure ; amendements §§ 5 et 6 commités avant les séances qu'ils jugent). Mes outils :
`outils/disque/placement/juge/` (rien d'importé de `lire.py`, `carte.py`, `seance.py`, `commun.py`, `analyse.py`).

Marques : [mes.] mesuré ici ; [calc.] calculé sur des mesures ; [litt.] littérature, non reproduite ; [hyp.] hypothèse ;
[lu] lu dans un document du projet.

## 0. En bref

**Verdict.** Les mesures de 08 sont honnêtes et se redonnent : seuils déclarés avant chaque passe, aucun retouché,
tous les rapports recalculés au dernier chiffre, cartes égales au bit. **Son explication centrale tombe** : l'écart de
× 1,4 entre les fichiers v1.0 et v1.2 n'est ni « l'état physique des données » ni « un état du disque du 17 » ; il suit
~~**la longueur des requêtes de lecture que le format impose**~~ **le motif des requêtes de lecture que le format impose
(leurs frontières et leurs longueurs)** [ce qui a changé : J10 et J11, 27 oct. 3 h 15-3 h 21 : deux requêtes de 6 Mo par tronçon v1.0 vont × 0,85 à q = 8 et × 0,88 à q = 4 ; la longueur seule ne décide pas]. Un même fichier lu avec les frontières de l'autre format
change de vitesse : A20 au motif de B20 va comme B20 (× 1,389), B20 au motif de A20 va comme A20 (× 0,715) ; A20 lu avec
des requêtes raccourcies de 3,5 % va comme B20 (× 1,421), B20 lu avec des requêtes allongées de 3,5 % va comme A20
(× 0,713). Les requêtes d'environ 12,0 Mo du v1.0 sont lentes sur ce disque, celles d'environ 11,6 Mo du v1.2 et de
8,3 Mo des compagnons rapides ne le sont pas ; mais couper chaque tronçon v1.0 en deux requêtes de 6 Mo ne le rend pas
rapide (× 0,85 à 0,88, J10, J11) : la variable exacte (où tombent les frontières des requêtes par rapport au motif v1.0)
n'est pas isolée.

| conclusion publiée | verdict du juge |
|---|---|
| (a) à contenu égal, un fichier jusqu'à × 1,42 plus vite (B20 / A20) ; ni position, ni ordre, ni cache, ni température, ni âge seul, ni extents de 5 à 233 | **le rapport tient** (1,398 par mon chemin) ; **les exclusions tiennent** ; **l'attribution tombe** : c'est ~~la longueur~~ le motif des requêtes du format (G1 ; la longueur seule ne décide pas, J10, J11). B20 et A20 n'ont pas le même contenu (v1.2 contre v1.0) : à contenu égal au bit, l'écart ne se voit qu'entre une copie fraîche et la même copie deux heures plus tard |
| (a') à contenu égal au bit, C120 non coupé 1,6 × plus vite que A120 | **tombe** : artefact de la file (G2) ; seul dans la file, C120 = A120 (0,980) |
| (b) une copie fraîche est rapide puis retombe au niveau de A20 en moins de 2 h ; H5 b tient ; la rapidité des fichiers du 17 reste inexpliquée | **le frais rapide tient** ; « retombe au niveau de A20 » se lit « au niveau du motif v1.0 » ; **« état du 17 » tombe** : R20, écrit le 22, va comme B20 cinq jours après (G1) |
| (c) C120, 267 473 extents ; t(n) = 17,0 ms + (n − 1) × 0,37 ms | **les extents tiennent** (au bit) ; **le modèle tombe** pour le moteur : c'est celui de `lire.py` (t₁ = 34 ms, τ = 9 à 11 µs par le chemin du moteur) ; son contrôle « à 1 % » n'a pas de puissance (G3, M1) |
| (d) réécrire un fichier contigu ne rend rien de bout en bout (9,380 contre 9,398) | **tient** (redonné) ; la copie gardait le motif v1.0 |
| (e) plus de profondeur ne cache rien ; q = 2 plus rapide que q = 4, sous le seuil ; p6 tuée par les nombres | **tient** pour les deux premiers (q8 / q4 0,97 et 0,91 ; q2 / q4 1,116 et 1,163) ; **« tuée par les nombres » tombe** : sous-puissance, pas mort (M2) |
| (f) arrêts de 15 à 25 s sur A120 lu en entier, liés au temps | **tient** comme phénomène ; ils frappent aussi A20 et R20 (trois de 15 à 18 s) ; A120 lu en entier le 27 : aucun (M8) |
| (g) seul levier restant : la défragmentation de C120, × 1,43 prédit | **prédit, non mesuré, et surestimé** : × 1,26 au chemin du moteur ; ~~**un autre levier, sans rien réécrire : couper les requêtes** (§ 5.7, J10)~~ couper les requêtes en deux ne marche pas (J10 × 0,85, J11 × 0,88) ; le levier de lecture reste à trouver (§ 12) |

~~**Ce qui reste à faire en premier** : mesurer de bout en bout, sur le 20b v1.0, le moteur avec des requêtes de lecture
plafonnées sous ~11,7 Mo (J9 l'a montré à l'étage disque en raccourcissant les requêtes ; J10, déclaré, le mesure en
coupant chaque tronçon en deux requêtes, mêmes octets) ; porter la consigne dans `trc-es` si elle tient.~~ [ce qui a changé : J10 et J11, 27 oct. 3 h 15-3 h 21 : deux requêtes de 6 Mo par tronçon v1.0 vont × 0,85 à q = 8 et × 0,88 à q = 4 ; la longueur seule ne décide pas]

**Ce qui reste à faire en premier** : isoler, à l'étage disque, ce qui rend lent le motif v1.0 (requête qui touche les
derniers ~420 Ko d'un tronçon v1.0 ? requêtes jointives ? frontière à une position donnée ?), par des motifs déclarés
avant (§ 12) ; un levier de lecture n'est à mesurer de bout en bout qu'une fois trouvé. À défaut, recoder les v1.0 en
v1.2 rend le × 1,38 à l'étage disque (le J1 du lot A le mesure de bout en bout : × 1,44 sur le 120b).

## D'où on part, où on va

08 a cherché ce qui fait le débit d'un fichier `.trc` sur ce NVMe (Samsung MZVMA1T0HCLD, derrière Intel RST VMD, sous
BitLocker), à la demande de Stone du 2026-10-22 (« essaye de voir une correlation exploite entre la fragmentation ,
position du fichier et de meilleurs résultat et exploitons le tout »). Il a tué la position, l'ordre, le cache, la
température, l'âge seul et la fragmentation modérée ; il a mesuré le coût de la fragmentation extrême de C120 ; il a
conclu que l'écart de 1,4 tenait à l'état physique des données et que les fichiers du 17 étaient rapides pour une raison
qu'il ne savait pas reproduire. `genome/JUGEMENT-construction.md` (§§ 6, 11) avait déjà mesuré cet écart à l'étage disque
et l'avait attribué, après 08, à « l'état physique des fichiers ». Ce jugement refait 08 par un autre chemin, le lit
contre ses journaux, et trouve la variable qui manquait.

## 1. Ce que j'ai refait, et par quel chemin

| chiffre publié (08) | mon chemin | résultat | verdict |
|---|---|---|---|
| seuils déclarés avant chaque passe | `git show` du § 2 à chaque commit ; heures des commits contre les débuts de séance | §§ 2.1-2.4 inchangés depuis 09f87a3 ; amendements commités avant leurs séances | **tient** |
| tous les rapports (p2a à p5, p3) | `juge/recalcul.py` sur les JSON et CSV commités | redonnés au dernier chiffre (§ 3.1) | **tient** |
| C120 267 473 extents ; A120 65, B120 233, A20 33, B20 29 | `juge/carte_juge.py` (FSCTL par ctypes, RÉPERTOIRE relu par moi), témoin fsutil et cassure | égaux au bit aux cartes commitées | **tient** |
| B20 / A20 = 1,423 | lecteur à port de complétion (une poignée chevauchée, comme `trc-es`), ABBA ×4, témoins et cassures | 1,398 (− 1,8 %, tolérance 6,1 %) | **tient** |
| « l'état physique, pas le format » | motif croisé A20 ↔ B20 (J3, J-bis) ; longueurs ×0,965 / ×1,035 (J9) ; tronçons coupés en deux (J10, J11) | la vitesse suit le motif des requêtes ; ~~la longueur des requêtes~~ (la longueur seule ne décide pas : J10, J11) | **tombe** (G1) |
| « un état du disque du 17 » | R20 (écrit le 22) contre A20 et B20, à + 12 h et + 5 jours | R20 / B20 = 0,981 ; R20 / A20 = 1,379 | **tombe** (G1) |
| C120 non coupé 1,6 × plus vite que A120 | composition de la file dans les CSV de 08 (J0-c) ; tronçons d'un seul extent lus seuls (J6) | 0,43-0,45 Go/s par lecture entourées de non coupées ; C[U] / A[U] = 0,980 | **tombe** (G2) |
| t(n) = 17,0 ms + (n − 1) × 0,37 ms | 1 200 tronçons de C120 tirés par ma graine 1618033, chemin du moteur (J5) | t₁ = 34,2 ms, τ = 8,6 et 10,8 µs | **tombe** pour le moteur (G3) |
| « le modèle rend le débit à 1 % » | même critère appliqué à un modèle constant | le constant passe aussi (0,970 ; 0,982) | **sans puissance** (M1) |
| défragmentation de C120 × 1,43 | C120 tiré (J5) contre ses tronçons non coupés seuls (J6), chemin du moteur | × 1,26 | **surestimé** (G3) |
| q2 / q4 × 1,125 et × 1,080 (A20) ; × 1,133 et × 1,147 (B20) ; q8 / q4 0,958 et 0,921 | mon lecteur, 4 passes par cas (J-bis J7) | q2 / q4 1,116 et 1,163 ; q8 / q4 0,969 et 0,906 | **tient** |
| p6 « tuée par les nombres » (gain prédit 1,05-1,09 sous S) | bruit des séries de bout en bout commitées (J0-f) | 0,8 % à 4,6 % ; un gain de 5 % se tranche à 1,6 % | **tombe** (M2) |
| arrêts de 15-25 s, liés au temps | débit par seconde des CSV de 08 ; mes passes | plages de 19, 19, 18 s redonnées ; trois de 15-18 s chez moi, sur A20 et R20 | **tient**, plus large (M8) |
| 9,380 contre 9,398 jetons/s, mêmes jetons, mêmes octets | recalcul des huit JSON de p3 | 1,0019, un texte, 29 684 199 424 octets | **tient** |
| σ des calculs de seuil | e_soi, S, S_b recalculés ; σ_inter de B20 / A20 sur sept séances | σ_inter = 3,04 % | **tient** |

## 2. Les seuils avant les passes : ce que dit git

J'ai extrait le § 2 de 08 à chaque commit de l'enquête et comparé les textes.

| déclaration | commit (heure) | séance qu'elle juge (début) | avant ? |
|---|---|---|---|
| §§ 2.1 à 2.4 : S, S_b, H1 à H6, protocole | 09f87a3 (22 oct., 1 h 33) | p2a (2 h 18) | oui ; **texte inchangé jusqu'à 5838195** |
| § 2.5 : F20 écrit comme le codeur | 29d4c1a (5 h 59) | p2b-F (7 h 15), p2b-Fb2 (12 h 21) | oui |
| § 2.6 : H7, profondeur, règle du levier | 4ed6a08 (6 h 16) | p4 (10 h 22) | oui (le texte dit « 6 h 30 » : heure fausse, sans conséquence) |
| § 2.7 : p5 et p6 | 301a2c0 et b55169c (10 h 30) | p5 (10 h 35) | oui |
| § 2.8 : test du retrim (G20a, G20b) | bcae307 (26 oct., 23 h 49) | p7 (27 oct., 0 h 45) | oui (hors de mon périmètre de commits ; lu, § 7.5) |

**Aucun seuil n'a été tiré ni retouché après coup**, et chaque amendement dit ce qui l'appelle. p3 a été lancée après
que D20 fut retombé, alors que le § 2.3 la réservait au cas où une cause tiendrait au seuil : elle a confirmé un résultat
nul, sans rien fausser.

## 3. J0 : les journaux de 08 recalculés par mon script [calc. sur mes. commitées]

`outils/disque/placement/juge/recalcul.py` → `mesures/disque/placement/juge/J0-recalcul.{json,log}`.

### 3.1 Ce qui se redonne au dernier chiffre

p2a B20 / A20 = 1,4229 (S 11,8 %) ; p2b-D D20 / A20 = 1,1845, D20 / B20 = 0,8579 ; p2b-D2 D20 / A20 = 1,0106 (S 12,35 %) ;
p2b-F F20 / A20 = 1,2378, F20 / B20 = 0,8945 ; p2b-Fb2 F20 / A20 = 1,0287, F20 / B20 = 0,7616 (S 18,3 %) ; p4 q2 / q4 :
A20 1,125, B20 1,133 ; q8 / q4 0,958 et 0,921 ; p5 q2 / q4 : A20 1,080, B20 1,147 ; q1 / q4 1,035 et 1,055 ; p3 9,380
contre 9,398 jetons/s (1,0019), un seul texte (1b14e44a6a10…), 29 684 199 424 octets de tronçons dans les huit passes ;
H1 t₁ = 16,955 et 17,246 ms, τ = 364,95 et 367,55 µs, un morceau / dix et plus = 5,745 et 5,565 ; ρ(débit, LCN) = 0,009 et
− 0,0105 dans A120, bandes 1,006 et 0,979 ; H4 trié / aléatoire sur B120 = 1,028 ; températures des passes A20 et B20 de
p2a à 2 °C près ; ρ entre passes 0,0116 (A120) et 0,6794 (C120) ; plages d'arrêt de 19, 19 et 18 s sous 0,5 Go/s.
**Tous les rapports publiés se redonnent.** σ_inter de r(B20 / A20) sur sept séances : 3,04 % (r de 1,351 à 1,479).

### 3.2 Le critère de H1 n'a pas de puissance

| modèle | somme des impaires prédite / mesurée (critère de 08) | erreur de la médiane par classe de morceaux 1 ; 2-9 ; 10-99 ; ≥ 100 (p2a-17) |
|---|---|---|
| 08 : t₁ + (n − 1) τ | 0,980 ; 0,991 : passe | + 7 % ; + 12 % ; + 22 % ; − 11 % |
| **constant** (moyenne des paires, aucun effet des morceaux) | **0,970 ; 0,982 : passe aussi** | + 140 % ; + 146 % ; + 40 % ; − 79 % |
| τ × 0,5 / τ × 2 | 0,707 / 1,526 : tombent | |

Une droite des moindres carrés passe par le point moyen, et deux moitiés tirées du même ensemble ont la même moyenne : le
critère déclaré accepte le modèle nul. « Le modèle rend le débit de C120 à 1 % près » applique la loi de Little à cette
même moyenne : le modèle constant le rend aussi. H1 tient pour C120 par son autre critère (un morceau contre dix et plus),
qui a de la puissance. Mon critère par classe (tolérance déclarée 10 %) rejette le constant, et aussi le linéaire.

### 3.3 La composition de la file fausse la comparaison « par lecture »

Pour chaque lecture non coupée de C120 (p2a-17, p2a-18), j'ai mesuré la part de sa durée pendant laquelle ses voisines en
vol étaient des lectures coupées (d'après `debut_us`, `fin_us`) :

| part des voisines coupées | lectures (p2a-17 ; p2a-18) | débit par lecture médian, Go/s |
|---|---|---|
| < 0,25 | 15 ; 33 | **0,431 ; 0,446** (A120 : 0,421 ; 0,402) |
| 0,25 à 0,75 | 1 549 ; 1 545 | 0,668 ; 0,657 |
| > 0,75 | 1 841 ; 1 827 | **0,874 ; 0,879** |

ρ(part, débit) = 0,70 et 0,71 ; témoins B120 et A120 (presque sans lectures coupées) : aucune lecture à part > 0,75, ρ
proche de 0. Une lecture entière va plus vite quand ses voisines dans la file sont des lectures coupées en petits
morceaux. Quatre lectures non coupées à 0,763 Go/s feraient 3,05 Go/s, plus que ce disque n'a jamais rendu à quatre en vol.

### 3.4 La puissance de p6

Gain de bout en bout prédit par la formule de 08 (T = 27,17 s, L = 17,225 s de lectures, médianes de p3) : × 1,049
(k = 1,080), × 1,076 (k = 1,125), × 1,088 (k = 1,147). Bruit des séries de bout en bout commitées (e_soi des jetons/s
de génération) : p3 A20 2,8 %, D20 4,3 % ; juge de la construction A20 0,8 %, B20 0,44 %, R20 1,2 % ; lot B A20 4,6 %.
2 × 0,8 % = 1,6 % : une série calme tranche un gain de 5 %.

## 4. Les instruments du juge, et leurs témoins

- **Carte** (`carte_juge.py`) : FSCTL_GET_RETRIEVAL_POINTERS sur une poignée à FILE_READ_ATTRIBUTES seul ; RÉPERTOIRE
  relu par mon analyseur (empreinte64 vérifiée) ; ordre de `troncons disque` recalculé par mon xorshift64*, égal à celui
  des journaux de 08 (552, 87, 721, 717…). Témoins : couverture des grappes ; égalité à `fsutil file queryextents`.
  Cassure : un extent retiré, les deux tombent.
- **Lecteur** (`lecteur.py`) : une poignée `FILE_FLAG_NO_BUFFERING | FILE_FLAG_OVERLAPPED`, un port de complétion, au plus
  q requêtes confiées au système, une requête par tronçon — le chemin de `trc-es`, et non les quatre fils synchrones de
  `lire.py`. Témoins (J2) : contre `troncons disque` du lot A dans la même séance, 0,945 (A20) et 0,977 (B20) : tient ;
  cassure (frein de 10 ms avant chaque remise) : 0,540, tombe. SHA-256 de 16 lectures égal à une lecture tamponnée :
  16/16 sur A20 et sur B20 ; cassure (+ 4 096 octets) : 0/16. SMART : le disque lit 0,99996 à 1,0020 fois ce qui est
  demandé (63 passes de la séance principale) ; deux passes de J-bis à 1,031 et 1,036 (un autre lecteur) sont écartées par
  ce témoin.
- **Machine** (`machine.py`) : verrou, calme (5 % d'un cœur ou 8 Mo lus en 3 s), secteur, SMART par mon propre appel.

## 5. Mes mesures [mes.]

Deux séances, sous le verrou, machine calme, sur secteur, par mes outils (`outils/disque/placement/juge/`) :
- **séance principale**, 2026-10-22 de 12 h 56 à 13 h 13, journaux `mesures/disque/placement/juge/seance/J1-* à J6-*` ;
  arrêtée proprement à J6-12 : le portable est passé sur batterie (J6-12 écartée, J8 non faite, verrou rendu) ;
- **séance J-bis** (amendement § 5 de mes seuils, déclaré à 13 h 19 le 22 avant toute autre mesure), 2026-10-26 à
  partir de 23 h 47, fichiers `Jb3-*` à `Jb9-*`, après la pause demandée par Stone du 22 au 26. **Quatre jours** séparent
  les deux séances : A20 a 11 jours, B20 9, R20 5. **Stone a fait une réoptimisation (retrim) de C: terminée le
  2026-10-26 à 23 h 46 min 44 s** (journal Defrag, événement 258) : toutes les passes de J-bis sont postérieures (la
  première finit à 23 h 47 min 37 s), dans l'heure qui suit le retrim ; aucune passe n'a été prise avant lui ce jour-là.
  La comparaison « avant / après le retrim » se fait donc contre la séance principale du 22.
- Séance principale : aucune passe sous charge ; disque lu / demandé de 0,99996 à 1,0020 (SMART, 63 passes). J-bis : une
  passe sous charge (Jb4-12, un autre flux a démarré pendant elle) et deux passes où le disque a lu 1,031 et 1,036 fois
  la demande (un autre lecteur), toutes trois écartées. Aucune transition thermique ; températures de 48 à 69 °C ;
  l'hôte n'a écrit que 0 à 9 Mo par passe.

### 5.1 J1 : les cartes, par mon outil

| fichier | extents | tronçons coupés | égale à la carte commitée de 08 | fsutil |
|---|---|---|---|---|
| A20 | 33 | 27 / 768 | au bit | égale |
| B20 | 29 | 17 / 768 | au bit | égale |
| R20 | 78 | 61 / 768 | (pas de carte dans 08) | égale |
| A120 | 65 | 52 / 4 608 | au bit | égale |
| B120 | 233 | 226 / 4 608 | au bit | égale |
| **C120** | **267 473** | 1 203 / 4 608 | **au bit** (0,47 s) | (trop long) |

Témoins : couverture des grappes juste pour les six ; liste égale à celle de `fsutil file queryextents` pour les cinq
de moins de 1 000 extents ; cassure (un extent retiré) : la couverture et l'égalité à fsutil **tombent** toutes deux.
RÉPERTOIRES de A120 et C120 égaux au SHA-256 (même contenu, même motif). **(c) « 267 473 extents » : redonné.**

### 5.2 J2 : ABBA A20 / B20 et les témoins du lecteur

A B B A A B B A, motif du moteur (768 lectures, ordre de `troncons disque --graine 20261017`, q = 4) : A20 1,762 ;
1,759 ; 1,779 ; 1,745 Go/s ; B20 2,481 ; 2,459 ; 2,461 ; 2,418. e_soi 1,9 % et 2,6 %, S_j = 11,8 %.
**B20 / A20 = 1,398, « diffèrent »** ; écart à 1,423 : − 1,8 %, sous T_a = max(2 × 3,04 %, 5,9 %) = 6,1 % :
**(a) redonné**.
- Témoin `troncons disque` (binaire du lot A) dans la même séance : A20 1,862, B20 2,518 ; mon lecteur / lui = 0,945 et
  0,977, dans ± 5,9 % : **tient** (le Python coûte 2 à 5 %). Cassure (frein de 10 ms avant chaque remise) : 1,005 Go/s,
  0,540 de `troncons disque` : **le témoin tombe** comme il doit.
- Contenu : 16 lectures sans tampon égales au SHA-256 à 16 lectures tamponnées, sur A20 et sur B20 (16/16) ; décalage
  faussé de 4 096 octets : 0/16 : **tombe**.
- SMART : le disque lit 1,0000 à 1,0020 fois ce qui est demandé.

### 5.3 J3 : le motif croisé — la lenteur suit le motif

| | séance principale (22 oct.) | J-bis (26 oct., après le retrim) |
|---|---|---|
| A20, motif natif (v1.0) | 1,779 ; ~~0,439~~ (arrêt de 17 s) | 1,792 ; 1,793 ; 1,813 ; 1,809 (médiane 1,801) |
| A20, motif de B20 | 2,445 ; 2,449 | 2,509 ; 2,493 ; 2,483 ; 2,564 (médiane 2,501) |
| B20, motif natif (v1.2) | 2,458 ; 2,457 | 2,511 ; 2,487 ; 2,556 ; 2,545 (médiane 2,528) |
| B20, motif de A20 | 1,788 ; 1,806 | 1,811 ; 1,829 ; 1,805 ; 1,774 (médiane 1,808) |

Séance principale : sans verdict au seuil (l'arrêt de J3-08 porte S_j à 242 %). **J-bis, aux seuils déclarés**
(e_soi ≤ 3,2 %, S_j = 11,8 %, aucune passe à arrêt) : A20 croisé / natif = **1,389** (> 1 + S_j), B20 croisé / natif =
**0,715** (< 1 − S_j) : **« la lenteur suit le motif »**. Ma prédiction (« elle suit le fichier ») est tombée.
Mêmes octets du même fichier, lus avec d'autres frontières de lecture : × 1,39. Et B20, le fichier « du 17 », lu avec
les frontières de v1.0, va comme A20 (1,808 contre 1,801).

### 5.4 J4 : R20, écrit le 22, rapide cinq jours après

| | séance principale (R20 à + 12 h) | J-bis (R20 à + 5 jours) |
|---|---|---|
| A20 | 1,757 ; 1,811 ; 1,792 ; 1,804 | 1,789 ; 1,816 ; 1,821 ; ~~1,827~~ (sous charge) (médiane 1,816) |
| R20 | 2,437 ; 2,447 ; 2,099 ; ~~0,343~~ (arrêt de 18 s) | 2,486 ; 2,563 ; 2,523 ; 2,468 (médiane 2,505) |
| B20 | 2,439 ; 2,457 ; 2,463 ; 2,442 | 2,557 ; 2,569 ; 2,550 ; 2,500 (médiane 2,554) |

J-bis, aux seuils déclarés (S_j = 11,8 %) : **R20 / A20 = 1,379, « diffèrent » ; R20 / B20 = 0,981, « égaux »**. Un fichier
écrit le 2026-10-22 à 0 h 46 par l'écrivain du codeur (60 ou 110 Go libres selon les relevés, § 7.1), va comme B20 cinq jours après :
**« un état du disque du 17 » tombe**, et « la manière d'écrire n'est pas la cause » ne vaut que pour la copie de
`placer.py`, qui gardait le motif v1.0.

### 5.5 Le retrim du 26 change-t-il A20 et B20 ?

A20 au motif natif : 1,745 à 1,811 le 22 (médianes 1,760 en J2, 1,798 en J4) ; 1,789 à 1,821 le 26 après le retrim
(médianes 1,801 en J3, 1,816 en J4) : + 1 à + 3 %. B20 : 2,418 à 2,481 le 22 (médianes 2,460, 2,449) ; 2,487 à 2,569 le 26
(2,528, 2,554) : + 3 à + 4 %. Les deux montent ensemble de quelques pour cent, sous S_j / 2 ; **le rapport B20 / A20 ne
bouge pas** (1,398 et 1,362 le 22 ; 1,404 et 1,406 le 26). On n'attend pas d'un retrim qu'il change des données déjà
écrites, et rien ne change ici ; ce qu'il ferait aux données écrites **après** lui, seuls p7 (§ 7.5) et le test du § 7.4
le diront.

### 5.6 J9 : ce qui, dans le motif, fait la lenteur — la longueur des requêtes

Les deux RÉPERTOIRES ne diffèrent ni par l'alignement des décalages (mêmes proportions alignées sur 8, 16, 32 et 64 Kio),
ni par les écarts entre tronçons (bout à bout dans les deux), ni par un niveau 1 (absent des deux) : seulement par les
longueurs (A20 11,84 à 12,14 Mo, médiane 12,02 ; B20 11,16 à 11,76, médiane 11,63) et, par elles, par le pas de la
fenêtre de destination. J-bis (amendement § 5) :

| cas | longueurs | passes, Go/s | médiane | rapport au natif |
|---|---|---|---|---|
| A20 natif | 11,84-12,14 Mo | 1,789 ; 1,766 ; 1,758 ; 1,676 | 1,762 | |
| **A20 raccourci** (× 0,965) | 11,42-11,72 Mo | 2,421 ; 2,536 ; 2,529 ; 2,480 | 2,504 | **× 1,421** |
| B20 natif | 11,16-11,76 Mo | 2,465 ; 2,503 ; 2,531 (~~2,319~~ : disque lu / demandé 1,036, écartée) | 2,503 | |
| **B20 allongé** (× 1,035) | 11,55-12,17 Mo | 1,776 ; 1,793 ; 1,758 ; 1,799 | 1,785 | **× 0,713** |
| A20, pas de fenêtre 12 Mio | natives | 1,744 ; 1,459 | 1,601 | × 0,909 |
| B20, pas de fenêtre de A20 | natives | 2,423 ; 2,492 | 2,457 | × 0,982 |

Lecture par sous-test, comme l'amendement les déclare (chacun son ordre) : **J9-L**, S_j = 12,9 % : A « diffèrent »
(+ 42,1 %), B « diffèrent » (− 28,7 %) : **à décalages fixes, une variation de 3,5 % de la longueur fait basculer la
vitesse** (verdict déclaré : « la longueur décide » ; J10 et J11 le restreignent, § 5.7). **J9-P**, S_j = 35,6 % (la passe à
1,459 n'a pas d'arrêt de 3 s, elle reste) : « égaux » pour les deux : **le pas de la fenêtre ne décide pas**. Lu comme
une seule série (S_j = 35,6 %), A passe encore (+ 42 %) et B est « entre deux » (− 28,7 %) : je le dis, et la lecture par
sous-test est celle du texte déclaré. ~~La frontière se trouve entre ~11,7 et ~11,9 Mo par requête ; dans les passes natives
de A20, les lectures de 11,7 à 11,9 Mo durent déjà moins que celles de 12,0 à 12,1 (24,0 contre 27,2 ms médianes). Elle
n'est pas localisée plus finement, et son mécanisme n'est pas observable d'ici : [hyp.] une limite par requête dans la
pile de stockage (filtre BitLocker `fvevol`, pilote VMD `iaStorVD`) ou dans le contrôleur (tampon de lecture, table de
correspondance dans la mémoire de l'hôte), au-delà de laquelle une requête se sert en deux temps une fois les données
repliées hors de la SLC (le frais de D20 et F20 allait vite au même motif).~~ [ce qui a changé : J10 et J11, 27 oct. 3 h 15-3 h 21 : deux requêtes de 6 Mo par tronçon v1.0 vont × 0,85 à q = 8 et × 0,88 à q = 4 ; la longueur seule ne décide pas] : une limite de taille par
requête ne survit pas à J10 et J11. Ce qui sépare les motifs lents des rapides, dans mes huit cas : sont **lentes** les
requêtes qui finissent exactement à une fin de tronçon v1.0 (A20 natif, A20 en moitiés, B20 au motif de A20) ou qui
débordent de 3,5 % une fin de tronçon v1.2 (B20 allongé) ; sont **rapides** celles qui s'arrêtent 3,5 % avant une fin de
tronçon v1.0 (A20 raccourci), qui finissent à une fin de tronçon v1.2 (B20 natif, A20 au motif de B20) ou de compagnon
(R20). Cette description n'est pas un mécanisme ; elle se teste (§ 12). Le frais de D20 et F20 allait vite au motif v1.0 :
le phénomène n'apparaît qu'une fois les données repliées hors de la SLC [hyp. pour la cause].

### 5.7 J10 et J11 : couper chaque requête en deux, sans rien réécrire — le levier tombe

**J10, déclaré avant** (amendement § 6, commit a735439, 0 h 48) : chaque tronçon de A20 lu en deux requêtes (mêmes
octets au bit), q = 8, contre le motif natif à q = 4. Une première tentative à 1 h 08 n'a pas trouvé le calme (flux
« mimétisme » et « pistes », 0,3 à 1,3 cœur par processus) : arrêtée avant toute passe, verrou rendu. Faite le 27 de
3 h 15 à 3 h 17, dans le créneau calme d'après la relecture p7-2 de l'enquête. Témoin : les deux moitiés lues sans
tampon égales au SHA-256 aux mêmes moitiés lues tamponnées, 16/16 ; cassure (seconde moitié 4 096 octets plus loin) :
0/16.

| | passes, Go/s | médiane |
|---|---|---|
| A20 natif, q = 4 | 1,804 ; 1,774 ; 1,782 ; 1,700 | 1,778 |
| A20 en deux requêtes par tronçon, q = 8 | 1,517 ; 1,513 ; 1,512 ; 1,502 | 1,513 |

S_j = 11,8 % : **× 0,851, « diffèrent », dans le mauvais sens : le levier ne tient pas.** Ma prédiction (« il tient »)
est tombée. J10 mêlait deux changements (des requêtes de 6 Mo, et huit en vol) ; **J11**, déclaré avant (amendement § 7,
commit 37b31bd, 3 h 17), garde q = 4 :

| | passes, Go/s | médiane |
|---|---|---|
| A20 natif, q = 4 | 1,737 ; 1,821 ; 1,766 ; 1,763 | 1,764 |
| A20 en deux requêtes par tronçon, q = 4 | 1,520 ; 1,582 ; 1,547 ; 1,565 | 1,556 |

S_j = 11,8 % : **× 0,882, « moins vite »**. Couper les requêtes ne rend pas au v1.0 la vitesse du v1.2 ; cela la dégrade.
**La longueur seule n'est pas la variable** : des requêtes de 6 Mo sont lentes quand elles couvrent bout à bout les
tronçons v1.0, et des requêtes de 11,6 Mo sont rapides quand elles s'arrêtent avant leur fin (J9).

### 5.8 J7 : la profondeur (J-bis)

| | q = 2 | q = 4 | q = 8 |
|---|---|---|---|
| A20 | 1,969 ; 1,969 ; 1,975 (~~1,872~~ : disque lu / demandé 1,031) | 1,753 ; 1,762 ; 1,768 ; 1,768 | 1,693 ; 1,728 |
| B20 | 2,940 ; 2,963 ; 2,951 ; 2,938 | 2,504 ; 2,552 ; 2,529 ; 2,536 | 2,300 ; 2,291 |

S_j = 11,8 %. q2 / q4 : **A20 1,116** (« entre deux »), **B20 1,163** (« diffèrent ») ; q8 / q4 : 0,969 et 0,906. **(e)
redonné** : plus de profondeur ne cache rien, moins va plus vite, et sur A20 sous le seuil, comme 08 (1,125 et 1,080 ;
1,133 et 1,147). La séance principale (sans verdict, arrêt dans J7-01) donnait 1,100 et 1,144. Le gain de q = 2 (× 1,12 sur
A20) est bien plus petit que celui du motif v1.2 (× 1,39) : la profondeur n'est pas la bonne variable.

### 5.9 J5 : le modèle (c) par le chemin du moteur

1 200 tronçons de C120 tirés par ma graine (885 d'un morceau, 121 de 2 à 9, 61 de 10 à 99, 133 de cent et plus), deux
passes : **1,383 et 1,372 Go/s**. Ajustement sur mes positions paires : **t₁ = 34,16 et 34,25 ms, τ = 8,6 et 10,8 µs**.

| | 08 (`lire.py`, p2a-17) | moi (chemin du moteur, J5-01) |
|---|---|---|
| durée médiane, 1 morceau | 15,7 ms | 30,7 ms |
| 2 à 9 morceaux | 15,7 ms | 30,8 ms |
| 10 à 99 | 27,2 ms | 35,4 ms |
| 100 et plus | 168,4 ms (moyenne 221) | 41,8 ms (moyenne 45) |
| durée moyenne | 38,5 ms | 34,7 ms |
| débit de la passe | 1,245 Go/s | 1,383 Go/s |

**(c) non redonné** : t₁ hors de T_t (+ 100 %), τ hors de T_τ (− 97 %). Le critère par classe rejette les deux modèles,
linéaire et constant ; le critère de 08 (somme des impaires) les accepte tous deux (1,003 et 1,000). Sur le chemin du
moteur, la fragmentation de C120 coûte peu à chaque lecture coupée et beaucoup à toutes : la file est occupée par des
centaines de petites requêtes. Ce qu'elle coûte en tout : C120 tiré 1,378 contre ses tronçons non coupés seuls 1,731
(J6) : **× 1,26**.

### 5.10 J6 : C120 non coupé, seul dans la file

U = 800 tronçons d'un seul extent de C120 (ma carte, ma graine), lus seuls sur C120 et sur A120 (mêmes indices, même
contenu, même motif) ; V = 800 tronçons d'un seul extent de B120. C120 1,751 ; 1,705 ; 1,731 (~~1,531~~, J6-12, finie sur
batterie) ; A120 1,750 ; 1,733 ; 1,795 ; 1,780 ; B120 2,452 ; 2,468 ; 2,255 ; 2,472. S_j = 18,0 %.
**C[U] / A[U] = 0,980 : « égaux »** ; B[V] / A[U] = 1,394. **« C120 non coupé va plus vite que A120 à contenu égal »
tombe** (G2) ; C120 et A120 sont au motif v1.0, B120 au motif v1.2.

### 5.11 J8 : A120 lu en entier

Le 2026-10-27 à 0 h 44, les 4 608 tronçons de A120 dans l'ordre de ma graine : **1,702 Go/s en 32,6 s**, débit par seconde
de 1,57 à 1,74, **aucun arrêt** (aucune plage de 3 s sous 0,5 Go/s). 08 avait lu A120 en entier à 1,146 et 0,848 (p2a,
arrêts de 19 et 37 s). **(f) n'est pas redonné dans J8** ; il l'est ailleurs : trois arrêts de 15 à 18 s dans la séance
principale, sur A20 et R20. Les arrêts sont des événements du disque, pas une propriété de A120.

## 6. La lecture de 08, phrase à phrase contre ses journaux

J'ai lu 08, la note de reprise et la note pour le mémoire en regard des journaux commités, et refait chaque
chiffre du § 0 (J0, tableau du § 1). Les constats sont classés selon ce qu'ils changent pour la suite.

### Graves

**G1. La cause de l'écart de 1,4 est mal attribuée (08 § 0, puce 3 ; § 3.4 ; § 4.5 ; § 6, point 1 ; § 12).** 08
conclut : « Ce qui fait l'écart de 1,4 entre le v1.0 et le v1.2, c'est l'état physique des données sur le disque,
pas le format », et, après F20, que la rapidité des fichiers du 17 « tient à un état du disque du 17 que je ne sais
pas reproduire ». Trois mesures la font tomber :
- **le motif croisé (J3, refait en J-bis aux seuils déclarés)** : le même fichier A20, lu avec les décalages et les
  longueurs du RÉPERTOIRE de B20, va comme B20 (2,501 contre 1,801 Go/s, × 1,389) ; B20 lu avec ceux de A20 va comme
  A20 (1,808 contre 2,528, × 0,715). **La lenteur suit le motif de lecture, pas le fichier** ;
- **R20**, écrit le 2026-10-22 à 0 h 46 par l'écrivain du codeur, va comme B20 à + 6 h (juge de la construction),
  à + 12 h (séance principale) et à + 5 jours (J-bis : R20 / A20 = 1,379, R20 / B20 = 0,981) ;
- **C120**, écrit le 17 dans la même fenêtre que B20 et B120 : ses tronçons d'un seul extent, lus seuls, vont comme
  ceux de A120 (J6, C[U] / A[U] = 0,980).
Le « format » que 08 écarte parce qu'il ne retire que 3,3 % des octets agit par **les frontières et les longueurs
de ses lectures**, pas par ses octets. Ce que cela change : le levier n'est pas dans la manière d'écrire ni dans
l'état du disque, mais dans le motif des lectures (§ 5.6, J9).

**G2. Le « résultat central » de p2a est un artefact de la file (08 § 3.4 ; § 0, puce 3 ; § 6, point 1).**
« Les lectures non coupées de C120 vont aussi vite que celles de B120 … et bien plus vite que celles de A120 …
à octets égaux, le fichier écrit le 2026-10-17 se lit 1,6 fois plus vite » compare des **débits par lecture** pris
dans des files différentes. Quatre lectures non coupées de C120 à 0,763 Go/s chacune feraient 3,05 Go/s, plus que le
disque n'en a jamais rendu à quatre en vol. Dans les journaux mêmes de 08 (J0-c), les lectures non coupées de C120
dont les voisines en vol sont surtout coupées vont à 0,874 et 0,879 Go/s par lecture, celles dont les voisines sont
surtout non coupées à 0,431 et 0,446, **le niveau de A120** (0,421 et 0,402 ; 0,431 hors des arrêts) ; ρ(part des
voisines coupées, débit) = 0,70. Mesuré directement (J6), file homogène de tronçons d'un seul extent : C120 1,731,
A120 1,765 Go/s (0,98, « égaux »). Ma prédiction (« il tient ») est tombée.

**G3. Le modèle (c) est celui de l'instrument de 08, pas du moteur (08 § 0, puce 2 ; § 3.4 ; note pour le mémoire
§§ 1.2-1.3).** t(n) = 17,0 ms + (n − 1) × 0,37 ms est tiré de `lire.py` (quatre fils, `ReadFile` synchrones). Par
le chemin du moteur (une poignée chevauchée, un port de complétion, comme `trc-es`), sur 1 200 tronçons de C120
tirés par ma graine, je mesure **t₁ = 34,2 ms et τ = 8,6 puis 10,8 µs par morceau de plus** (J5), hors des
tolérances déclarées (T_t = 14,4 %, T_τ = 25,7 %). Sur ce chemin, une lecture coupée en cent morceaux et plus dure
41,8 à 44,6 ms au lieu de 30,7 à 31,1 pour une non coupée (×1,4), et non 168 ms au lieu de 15,7 (× 10,7) comme
dans `lire.py` : le coût des morceaux se répartit sur toutes les lectures en vol (§ 5.9). Le moteur lit C120 à 1,33-1,38 Go/s
(`troncons disque` du lot A, 1,356 et 1,331 ; J5, 1,383 et 1,372), et non à 1,24 (`lire.py`) : le témoin de
`lire.py` (2 à 4 % sous `troncons disque`) n'avait été tenu que sur A20 et B20, presque sans coupure ; sur C120 son
écart est de 7 à 9 %. **Ce qui change** : le gain prédit de la défragmentation logique de C120 (08 § 6 « × 1,43 »,
note § 1.3) repose sur le 1,24 de `lire.py` et sur le 1,78 de A20 réécrit ; au chemin du moteur, C120 contigu dans
son état d'aujourd'hui lirait comme ses tronçons non coupés seuls, **1,731 / 1,378 = × 1,26** [calc. sur mes., J5 et
J6], et ce levier n'est toujours pas mesuré par une réécriture.

### Mineurs

- **M1. Le critère de H1 n'a pas de puissance** (§ 2.2 ; § 3.4 : « prédit la durée totale des impaires à 0,980 et
  0,991 ») : il accepte le modèle constant (0,970 et 0,982 ; 1,000 et 0,998 sur mes passes). « Le modèle rend son
  débit à 1 % près » (§ 0 ; note § 1.2) est l'identité de Little appliquée à une droite qui passe par la moyenne :
  ce n'est pas une preuve. H1 tient pour C120 par son autre critère (un morceau contre dix et plus), qui en a.
- **M2. « p6 tuée par les nombres » (§ 4.4 ; § 0, puce 5) manque de puissance, elle n'est pas tuée.** Le gain prédit
  (× 1,049 à × 1,088 par la formule de 08) est jugé contre le plancher S = 11,8 %, tiré du bruit de l'étage disque du
  120b. Le bruit des séries de bout en bout commitées va de 0,8 % (juge de la construction, A20, e_soi) à 4,6 % (lot B,
  A20) ; 2 × 0,8 % = 1,6 % : une série calme aurait tranché un gain de 5 %. De plus la formule sous-estime : pour
  k = 1,38 et 3,4 % d'octets en moins, elle donne × 1,23 quand le juge de la construction a mesuré × 1,296 de bout en
  bout (B20 contre A20). « Trop petit pour qu'une série ABBA le tranche » est faux en général ; vrai seulement au
  plancher choisi. 08 § 12 le dit à moitié (« une série plus longue dirait si … »).
- **M3. Citations hors médiane (§ 6, « Conséquence pour les autres mesures »).** « exact = A120, 1,87-1,88 j/s » : ce
  sont les deux passes basses de quatre (2,080 ; 1,870 ; 2,117 ; 1,882 ; médiane 1,981). « A120 1,78 et 2,01 » au juge
  de la construction : la plus basse et une autre de quatre (1,995 ; 1,785 ; 2,013 ; 2,019 ; médiane 2,004). Le sens du
  propos tient (l'écart ne vient pas du contenu des fichiers) ; les nombres cités le grossissent.
- **M4. « exactement » et « en moins de deux heures » (§ 0, § 4.2, § 4.5).** D20 relu égale A20 (1,011) ; F20 à
  + 2 h 08 est au-dessus de A20 dans les 16 paires de passes sur 16 (+ 2,9 %, p = 0,029 au test exact à quatre contre
  quatre) : pas « exactement » retombé. Les relectures ont eu lieu à + 2 h 14 et + 2 h 08 : la descente est bornée par
  « au plus 2 h 14 », pas « moins de 2 h ».
- **M5. « Le levier qui tient » (§ 6)** pour une défragmentation que personne n'a mesurée : c'est un levier prédit
  (et, G3, à × 1,26 et non × 1,43).
- **M6. § 9 périmé** : « sans F2 concluant » alors que F2 est fait (§ 4.5) ; et § 9 ne dit rien de la file (G2), ni du
  chemin de `lire.py` (G3).
- **M7. Heure d'un amendement** : § 2.6 « déclaré … à 6 h 30 » et commité à 6 h 16 (4ed6a08) ; sans conséquence (p4 à
  10 h 22). Je l'ai fait moi aussi (§ 5 de mes seuils : « 13 h 40 » écrit d'avance, commit à 13 h 19, barré).
- **M8. Les arrêts ne sont pas propres à A120 ni aux « vieilles données »** (§ 3.5 : « aucun arrêt n'apparaît sur …
  A20 » ; [hyp.] « travail de fond … déclenché par la lecture de vieilles données ») : la séance principale en a pris
  sur A20 (J3-08, J7-01) et sur R20 (J4-11), un fichier de 12 h. Ils sont liés au temps, comme 08 le dit, et frappent ce
  qu'on lit à ce moment.
- **M9. BitLocker et VMD** (§ 6 : « le contenu (chiffré par BitLocker, donc aléatoire pour le disque) ») : la protection
  est active (propriété Shell, vérifiée sans administrateur), mais le chiffrement logiciel (fvevol) ou matériel n'est
  pas vérifiable sans administrateur ; sur la puce, les données sont de toute façon brouillées. Le contenu ne peut pas
  expliquer l'écart, et J3 le confirme d'une autre façon (même contenu, deux vitesses selon le motif). Le pilote
  Intel RST VMD empêche aussi de lire l'identité NVMe (DRAM ou tampon dans l'hôte) sans administrateur (§ 7.6).

### Ce que j'ai vérifié et qui tient

- **Les seuils avant les passes** (§ 2) : aucun tiré après coup ; les amendements disent ce qui les appelle.
- **Tous les rapports publiés se redonnent** au dernier chiffre par mon script (§ 3.1), et les cartes au bit (§ 5.1).
- **(a) B20 / A20 = 1,42** : je mesure 1,398 par mon chemin (J2), dans la tolérance déclarée (− 1,8 % contre
  T_a = 6,1 %) ; σ_inter = 3,0 % sur sept séances commitées. L'écart existe ; c'est son attribution qui tombe (G1).
- **H2 (position LCN), H4 (ordre, sur B120), H5 a (cache de Windows), H6 (température)** tombent comme 08 le dit :
  ρ = 0,009 et − 0,011 dans A120, bandes 1,006 et 0,979, trié / aléatoire 1,028, disque lu / demandé 0,99996 à 1,0020 sur
  mes 63 passes, aucune transition thermique, températures des passes A et B à 2 °C près.
- **(b) H5 b, le frais rapide** : D20 frais 2,345 puis 2,18 contre 1,78 à + 2 h 14 (× 1,32, × 1,22 > S) tient. Mais
  « retombe au niveau de A20 » se lit maintenant « retombe au niveau **du motif v1.0** ».
- **(d) réécrire un fichier contigu ne rend rien de bout en bout** : 9,380 contre 9,398 jetons/s (1,0019), un seul
  texte, 29 684 199 424 octets dans les huit passes : redonné. Le motif de D20 était celui de A20 : ce résultat est
  cohérent avec G1, et ne dit rien d'une réécriture au motif v1.2.
- **(f) les arrêts de 15 à 25 s**, liés au temps (ρ entre passes 0,012) : redonnés (plages de 19, 19 et 18 s dans les
  journaux ; trois de 15 à 18 s dans ma séance principale, sur A20 et R20) ; A120 lu en entier le 27 n'en a eu aucun (J8).
- **La recette « relever `troncons disque` par fichier avant une séance de vitesse »** tient, et G1 la précise :
  deux fichiers au même format se comparent ; deux formats différents ne se comparent pas sans le motif croisé.

## 7. L'hypothèse de la session « relais » : le retrim et la disposition dans la NAND

### 7.1 Ce qu'elle dit, et ses faits

Transmise par l'orchestrateur le 2026-10-22, **hypothèse, non un fait établi** : la vitesse suivrait la disposition
physique des données dans la NAND, que NTFS ne voit pas. Après un grand effacement, une réoptimisation (retrim) et du
repos, le disque aurait des blocs effacés contigus ; les données repliées de la SLC vers la TLC y seraient réparties en
superblocs sur toutes les puces ; dans un espace libre haché, le repli les disperserait — d'où « rapide juste après
l'écriture, puis lent en moins de deux heures ».

Ses faits, et ce que j'en ai vérifié :
- défragmentation et réoptimisation de C: terminées le 2026-10-15 à 22 h 52 min 03 s ; « shrink estimation » le 16 à
  21 h 25 : **vérifié** (journal Application, Microsoft-Windows-Defrag, événements 258, lecture seule) ;
- ≈ 230 Go effacés le 16 vers 21 h, redémarrage à 21 h 30, ≈ 200 Go libres le 17 au matin, 28 Go le soir du 17, 94 à
  110 Go lors des copies du 22 : **non vérifiés par moi**. La place libre lors de l'écriture de R20 (22 oct., 0 h 46) est
  donnée à 60 Go par la reprise de 08 (relevé de 1 h 20) et à ≈ 110 Go par 08 § 2.8 : les deux ne s'accordent pas ;
- l'ordre des écritures, **vérifié** par les horodatages NTFS : A20 (15 oct., 13 h 05-13 h 22) et A120 (15 h 50-16 h 10)
  **avant** le retrim du 15 ; B20, B120, R20-λ1, C120, R120 le 17 entre 8 h 53 et 13 h 16, **après** ; R20-λ0 le 22 à
  0 h 46-0 h 51 ; D20 le 22 vers 3 h 40, F20 vers 7 h 15 et 10 h 10.
- Le 2026-10-26, **Stone a fait un retrim de C: terminé à 23 h 46 min 44 s** (événement 258, relevé par l'orchestrateur ;
  les défragmentations planifiées du 23 au 26 avaient toutes été annulées, événement 264).

### 7.2 Confrontée aux mesures

| fait mesuré | ce qu'elle prédit | compatible ? |
|---|---|---|
| A20, A120 (écrits le 15, avant le retrim du 15) lents ; B20, B120 (le 17, après) rapides | oui | oui |
| D20 et F20 (22 oct., espace rendu par morceaux) rapides frais, lents à + 2 h | oui | oui |
| **C120** (écrit le 17 de 11 h 45 à 12 h 25, dans la « bonne » fenêtre), tronçons d'un seul extent lus seuls : comme A120 (J6, 0,980) | rapide comme B120 | **non** |
| **R20-λ0** (écrit le 22 à 0 h 46, espace haché) : comme B20 à + 6 h, + 12 h et + 5 jours (J-bis, 0,981) | lent après le repli | **non** |
| **A20 lu au motif de B20 va comme B20 ; B20 lu au motif de A20 va comme A20** (J-bis J3) ; **A20 en requêtes raccourcies va comme B20, B20 en requêtes allongées comme A20** (J9) | la vitesse suit le fichier, quel que soit le motif | **non** |
| A20 et B20 dans l'heure qui suit le retrim du 26 (J-bis) contre le 22 : + 1 à + 4 % tous deux, B20 / A20 inchangé (1,40) | rien pour des données écrites avant | oui (rien n'est prédit) |

Les trois faits qui la départagent d'une explication par le motif des requêtes la contredisent. Les deux premiers
s'accordent aussi avec « le motif v1.0 est lent une fois les données repliées ». **Je la tiens pour très
improbable** comme cause de l'écart A / B ; elle peut rester vraie comme effet secondaire (le frais, la vitesse du repli).

### 7.3 Ce qu'elle prédit de mesurable

Une copie écrite après un grand effacement, un retrim et un repos reste rapide au-delà de 2 h **sous tous les motifs de
requête** ; une copie écrite dans l'état ordinaire retombe **sous tous les motifs**. L'explication par le motif
prédit au contraire que les deux copies, à + 2 h, sont lentes au motif v1.0 et rapides au motif v1.2 (ou en requêtes
raccourcies), et ne diffèrent pas entre elles.

### 7.4 Le protocole exact, et le seuil à déclarer avant d'écrire

**Ce que Stone fait lui-même** (administrateur, réglage du système ; aucun agent ne le fait) : libérer d'un coup au
moins 150 Go (fichiers qu'il choisit, rien sous `~/dev/modeles/`) ; lancer
`Optimize-Volume -DriveLetter C -ReTrim -Verbose` dans un PowerShell administrateur ; vérifier l'événement 258
« réoptimisation » dans le journal Application ; laisser le disque au repos 45 min sur secteur. Le retrim du 26 a été
fait **sans** la libération préalable de 150 Go (94 Go libres relevés à 23 h 47 par 08 § 2.8) : c'est une version faible
du geste.

**Ce que fait l'agent** (sans administrateur, sous le verrou, machine calme, sur secteur) :
1. **R1** puis **R2** : deux copies de A20 écrites comme le codeur (`placer.py copier --mode filet --debit-mo-s 30`)
   juste après le repos, SHA-256 égal à e8bd6ae1…169f ; **N1** : une troisième copie, même commande, écrite **avant** le
   geste de Stone (dans l'état ordinaire, ou au moins 2 h avant), gardée jusqu'à la lecture ;
2. à **+ 2 h 30 au moins** après R2 : A20, R1, R2, N1, B20, lus par le lecteur du moteur à q = 4 **à deux motifs** : le
   natif (requêtes d'environ 12,0 Mo) et le motif de B20 (environ 11,6 Mo), ordre A R1 R2 N1 B B N1 R2 R1 A deux fois
   (quatre passes par fichier et par motif) ; passes à arrêt ou à témoin SMART hors de [0,98 ; 1,02] écartées ;
3. R1, R2 et N1 effacés après la séance.

**Seuil**, S = max(2 × max e_soi de la série, 11,8 %) :
- témoin : |R1 / R2 − 1| < S / 2 aux deux motifs, sinon la séance ne conclut pas ;
- **elle tient** si, au motif natif, R1 / N1 − 1 > S et |R1 / B20 − 1| < S / 2 ;
- **elle tombe** si, au motif natif, |R1 / N1 − 1| < S / 2 ;
- **la longueur décide aussi pour les copies** si, au motif de B20, R1, R2 et N1 sont égaux à B20 à S / 2 près.

### 7.5 Le test p7 de l'enquête, que je juge sans le faire

08 § 2.8 (commit bcae307, 26 oct. à 23 h 49, avant toute écriture) déclare G20a et G20b, deux copies écrites comme le
codeur après le retrim, relues à + 2 h par `troncons disque` (motif natif seulement), seuil S = max(2 × max e_soi,
18,3 %) ; « tient » si G20a et G20b dépassent A20 de plus de S et égalent B20 à S près ; « tombe » si elles égalent A20 à
S / 2. Ce que j'en dis :
- **le seuil est déclaré avant, le témoin à deux copies est là** : le test est recevable ;
- **il ne lit qu'au motif natif** : s'il « tombe », il ne départage pas un repli dispersé d'une requête trop longue ; s'il
  « tient », il contredirait J3 et J9 et devra se refaire au motif de B20 (mon § 7.4, point 2) ;
- **il n'a pas de copie témoin écrite avant le retrim** : il compare à A20 (écrit le 15) et non à une copie du même jour
  dans l'état ordinaire ; un « tient » mêlerait le retrim et la fraîcheur relative ;
- ma prédiction : **il tombe** (G20a et G20b au niveau de A20 au motif natif), parce qu'elles gardent le motif de lecture de
  A20.

**Le résultat** (08 § 4.6, commit ae97379 ; p7-2 le 27 de 3 h 06 à 3 h 13, 2 h 06 après G20b, machine calme), recalculé
par moi sur ses journaux : A20 1,764 ; 1,759 ; 1,709 ; 0,437 (arrêt) ; G20a 1,772 ; 1,783 ; 1,777 ; 1,779 ; G20b 1,785 ;
1,787 ; 1,756 ; 1,770 ; B20 2,530 ; 2,532 ; 2,482 ; 2,482. **G20a / A20 = 1,0254, G20b / A20 = 1,0252, G20a / B20 = 0,7094,
témoin G20b / G20a = 0,9998** : redonnés au dernier chiffre. Au seuil déclaré pris à la lettre, l'arrêt de la dernière
passe de A20 porte S à 187 % : « tombe » y est vrai mais vide (« tient » était impossible) ; l'enquête le dit elle-même et
donne la vue sans cette passe (S = 18,3 %), où 2,5 % < S / 2 : **l'hypothèse tombe**, ma prédiction et la sienne tiennent.
Ce verdict se lit avec ce que le test ne mesure pas : les copies n'ont été lues qu'au motif v1.0, et elles ont été effacées
avant toute lecture au motif v1.2. Les copies post-retrim lisent comme A20, exactement ce que prédit l'explication par le
motif ; le relais prédisait l'inverse.

### 7.6 Le disque a-t-il de la DRAM ?

Pas lisible sans administrateur ici : derrière Intel RST VMD, la commande NVMe Identify Controller (champs HMPRE et
HMMIN, qui disent si le contrôleur demande un tampon dans la RAM de l'hôte) rend des zéros par la propriété du disque et
ERROR_INVALID_FUNCTION par celle de l'adaptateur (`outils/disque/placement/juge/identifier.py`). L'identification au
PM9C1a, annoncé sans DRAM, reste « probable, pas prouvée » [lu : `fondations/01-machine.md` § 2.5 ; litt., non
reproduit]. La trancher demande un geste sous administrateur : c'est à Stone de choisir s'il le fait.

**Réponse par délégation du 2026-10-22, réversible** : le juge n'écrit aucune copie et ne lance aucun geste système ; il
déclare le protocole et juge celui de l'enquête. Justification : la consigne (lecture seule pour le juge) et les mots de
l'orchestrateur du 26 (« Toi, tu le juges : n'écris pas de copie »).

## 8. Ce qui tient selon le juge, et ce qui est barré

### Ce qui tient

- La méthode : seuils tirés d'un bruit nommé et déclarés avant ; témoins qui peuvent tomber ; ABBA ; journaux commités ;
  amendements datés. Tous les rapports publiés se redonnent, et les cartes au bit.
- L'écart lui-même : B20 / A20 = 1,40 à 1,42 à l'étage disque (sept séances commitées et mes deux) ; R20 et B120 au niveau
  de B20 ; A120 et C120 (tronçons d'un seul extent) au niveau de A20.
- Ce qui ne fait pas le débit : la position LCN, l'ordre de lecture, le cache de Windows, la température, l'âge seul, la
  fragmentation modérée (5 à 233 extents), le contenu.
- Le frais rapide (H5 b), la fragmentation extrême qui coûte (C120 : × 1,26 au chemin du moteur), la profondeur
  (q = 8 et 16 ne cachent rien ; q = 2 un peu plus rapide), « réécrire un fichier contigu au même format ne rend rien »
  (1,002 de bout en bout), les arrêts liés au temps.
- La recette « relever l'étage disque de chaque fichier avant une séance de vitesse ».

### Ce qui est barré dans 08 (porté dans le texte, avec ce qui a changé)

| où | phrase barrée | ce qui l'a fait tomber |
|---|---|---|
| § 0, puce 2 | « le modèle … rend son débit (1,24 Go/s) à 1 % près » | critère sans puissance (le constant passe) ; modèle de `lire.py` ; le moteur lit C120 à 1,33-1,38 (G3, M1) |
| § 0, puce 3 | « c'est l'état physique des données sur le disque, pas le format » ; « à contenu égal au bit, C120 non coupé va plus vite que A120 » ; « il tient à un état du disque du 17 que je ne sais pas reproduire » | J3, J9 : la longueur des requêtes ; J6 : 0,980 ; R20 : 0,981 de B20 (G1, G2) |
| § 0, puce 4 | « manière d'écrire (… retombent tous deux au débit de A20) » parmi les tués | les copies gardaient le motif v1.0 ; R20, écrit par l'écrivain du codeur, ne retombe pas (G1) |
| § 0, puce 5 | « trop petit pour qu'une série ABBA le tranche » | bruit de bout en bout 0,8 % (M2) |
| § 3.4, deux derniers alinéas | « Mais les lectures non coupées de C120 vont aussi vite que celles de B120 … C'est le résultat central … c'est l'état physique des données que la FTL a rangées. » | G2 |
| § 4.4 | « La mesure de bout en bout (p6) n'est pas lancée, tuée par les nombres … une série ABBA de huit passes ne peut pas le trancher » | M2 |
| § 4.5 | « La manière d'écrire n'est pas la cause … elle tient à un état du disque de ce jour-là » | G1 |
| § 6, point 1 | « L'état physique des données dans le disque, qui dépend de quand et comment elles ont été écrites » ; « C120 non coupé (17 oct.) va plus vite que B120 » | G1, G2 |
| § 6 | « Le levier qui tient : la défragmentation logique » ; « Gain prédit sur C120 : 1,24 → 1,78 Go/s, × 1,43 » | prédit, non mesuré, × 1,26 au chemin du moteur (G3, M5) |
| § 6 | « Aucun levier de l'écriture ne le donne sur cette machine aujourd'hui » | ~~le levier est dans la lecture (J9, J10)~~ la cause est dans le motif de lecture (J3, J9) ; couper les requêtes ne la répare pas (J10, J11) ; recoder en v1.2 la répare |
| § 6 | « 1,87-1,88 j/s » ; « A120 1,78 et 2,01 » | médianes 1,981 et 2,004 (M3) |

Et dans la note pour le mémoire : § 1.2 « le modèle rend le débit de C120 au pour cent près » et § 1.3 « gain prédit
1,78 / 1,24 = 1,43 ».

## 9. Ce qui pourrait être faux (dans ce jugement)

- **Le mécanisme n'est pas vu.** J3 et J9 montrent que le motif des requêtes décide, à fichier égal ; J10 et J11, que la
  longueur seule ne décide pas. ~~« La longueur » est la variable que j'ai manipulée~~ : la description du § 5.6 (où
  finissent les requêtes par rapport aux tronçons v1.0) n'est qu'une description de huit cas ; elle peut être fausse au
  neuvième.
- **Raccourcir ne lit pas les mêmes octets** : A20 raccourci laisse 3,5 % de chaque tronçon ; B20 allongé relit 3,5 % du
  suivant. Une plage de décalages lue lentement ne suffit pas à l'expliquer : B20 natif lit toutes les plages de son
  fichier, bout à bout, et va vite ; ce qui compte semble être où les requêtes finissent. Le test du § 12, point 2 (i),
  le tranche.
- **Quatre jours et un retrim séparent mes deux séances** (22 et 26-27 octobre). A20 et B20 ont monté de 1 à 4 % ensemble ;
  le rapport n'a pas bougé. Les verdicts de J3, J4, J7 et J9 sont tous pris dans J-bis, une seule séance, dans l'heure qui
  suit le retrim, pendant laquelle le disque a pu travailler ; les comparaisons sont internes à la séance, en ABBA.
- **Mon lecteur est en Python** : 2 à 5 % sous `troncons disque` (témoin) ; il compare des motifs dans une même passe, ce
  qui annule ce biais, mais ses débits absolus sont un peu bas. Il reproduit le chemin de `trc-es` (une poignée chevauchée,
  un port de complétion) ; le moteur, lui, lit dans une mémoire épinglée par CUDA, pas dans `VirtualAlloc` : J9-P montre
  que le pas de la fenêtre ne compte pas, pas que le type de mémoire ne compte pas.
- **La règle des arrêts** (amendement § 5) est venue après la séance principale ; je ne juge pas sur la séance principale
  pour J3, J4 et J7, mais l'exclusion des passes à témoin SMART hors de [0,98 ; 1,02] (deux passes de J-bis) applique un
  témoin déclaré au § 2 dont je n'avais pas écrit qu'il écartait la passe : je le dis ; les verdicts ne changent pas si on
  les garde (B20 natif J9 : 2,484 au lieu de 2,503 ; A20 q2 J7 : 1,969 au lieu de 1,969).
- **J9 se lit par sous-test** (S_j = 12,9 % pour J9-L) ; lu comme une seule série, B allongé est « entre deux ».
- **R20 n'est qu'un fichier** écrit le 22 et resté rapide ; c'est aussi un autre format (requêtes de 8,3 Mo), ce qui est
  justement ce que G1 dit : il ne prouve pas à lui seul qu'un fichier v1.0 écrit le 22 aurait été rapide.
- **La part des voisines coupées** (J0-c) ne compte que 15 et 33 lectures dans la classe « < 0,25 » ; J6 le confirme
  directement (800 lectures, quatre passes).
- L'identité du disque (DRAM ou non) n'est pas lue ; toute explication physique reste une hypothèse.

## 10. Recettes (pour RECETTES.md)

- **Croiser les motifs** avant d'attribuer un écart de vitesse entre deux formats : lire chaque fichier avec les
  décalages et longueurs de l'autre. Huit passes, une minute et demie, ont renversé la conclusion de 08.
- **Manipuler la longueur des requêtes** à décalages égaux (raccourcir / allonger de 3,5 %) : fait basculer la vitesse ;
  ~~isole la variable~~ ne suffit pas à isoler la variable (J10, J11 : couper en deux à longueur totale égale ne rend rien).
- Essayé et sans effet, voire nuisible : **couper chaque tronçon v1.0 en deux requêtes** (× 0,85 à q = 8, × 0,88 à q = 4).
- **Ne jamais comparer des débits « par lecture » pris dans des files de composition différente** ; comparer des passes
  homogènes en débit agrégé.
- **Mesurer avec le chemin du moteur** (poignée chevauchée, port de complétion) : quatre fils synchrones changent le coût
  de la fragmentation d'un facteur 10 par lecture, et le débit de C120 de 9 %.
- **Un témoin de modèle doit pouvoir échouer** : tester le critère contre le modèle nul (constant) ; la somme des impaires
  d'une régression ne le fait pas.
- **Le SMART par passe** (unités lues par l'hôte) détecte un autre lecteur que le relevé des processus ne voit pas (deux
  passes de J-bis à 1,031 et 1,036).
- **Un plancher de seuil se tire du bruit de la grandeur jugée** : le 11,8 % de l'étage disque du 120b ne vaut pas pour des
  jetons/s de bout en bout.
- Essayé et sans effet : le pas de la fenêtre de destination (J9-P) ; le retrim sur des données déjà écrites (§ 5.5).

## 11. Réponses par délégation de ce jugement

- **Refaire J3, J4 et J7 en J-bis** plutôt que de juger sur les passes sans arrêt de la séance principale : réponse par
  délégation du 2026-10-22, réversible (une exclusion décidée après avoir vu les nombres serait un seuil tiré après coup).
- **Ajouter J9, J10 et J11** au plan, déclarés avant : réponse par délégation des 2026-10-22 et 2026-10-27, réversible (J3 a
  désigné la variable ; la tester est gratuit et répond à « exploitons le tout »).
- **Ne rien écrire et ne lancer aucun geste système** pour l'hypothèse de relais : réponse par délégation du 2026-10-22,
  réversible (lecture seule du juge ; consigne de l'orchestrateur du 26).
- **Barrer dans 08 et dans sa note pour le mémoire, pas dans 06 ni dans JUGEMENT-construction** : réponse par délégation du
  2026-10-27, réversible (mon périmètre est 08 ; la conséquence pour les autres documents est dite au § 12 pour
  l'orchestrateur).

## 12. Ce qui reste

1. ~~**De bout en bout** : `troncons mesurer` sur le 20b v1.0 avec des requêtes plafonnées (chaque tronçon en deux requêtes,
   ou un plafond vers 11,5 Mo dans `trc-es`), A Q Q A A Q Q A, mêmes 256 jetons et mêmes octets exigés, seuil tiré du bruit
   de la série (0,8 % au juge de la construction). Gain prédit par la formule de 08 pour k = 1,39 : × 1,22 ; la formule a
   sous-estimé de 5 % le seul cas mesuré (B20 contre A20, × 1,296).~~ [ce qui a changé : J10 et J11, 27 oct. 3 h 15-3 h 21 : deux requêtes de 6 Mo par tronçon v1.0 vont × 0,85 à q = 8 et × 0,88 à q = 4 ; la longueur seule ne décide pas]
2. ~~**Localiser la frontière** de longueur (11,6 à 12,0 Mo par pas de 64 Kio) et voir si elle bouge avec q, avec la
   fraîcheur des données (le frais de D20 n'y était pas sensible), et sur le 120b.~~
   **Isoler la variable du motif**, à l'étage disque, par des motifs déclarés avant : (i) A20, chaque tronçon en une requête
   de 0,965 × l puis une requête de la fin (≈ 420 Ko) — si cela rend tout lent, ce sont les requêtes qui finissent à une fin
   de tronçon v1.0 qui sont lentes ; (ii) A20 raccourci par le début (décalage + 0,035 × l) ; (iii) A20 au motif
   de B20 décalé de 64 Kio ; (iv) les mêmes sur A120 et C120. Un levier de lecture se mesure ensuite de bout en bout, avec
   un seuil tiré du bruit de la série (0,8 % au juge de la construction).
2 bis. **Le levier sûr, déjà mesuré par d'autres** : recoder les fichiers v1.0 en v1.2 (le J1 du lot A : × 1,44 de bout en
   bout sur le 120b ; l'étage disque : × 1,38). Ce n'est pas un levier de placement ; c'est celui qui marche aujourd'hui.
3. **Conséquence hors de 08, pour l'orchestrateur** : `genome/06-codon-v1-2.md` § 8 et `genome/JUGEMENT-construction.md`
   §§ 6 et 11 attribuent le × 1,44 du v1.2 sur le v1.0 à « l'état du fichier ». Sur ce disque, il vient du format, par le
   motif de ses tronçons (frontières et longueurs ; ~~la longueur de ses tronçons (11,6 contre 12,0 Mo)~~, J10, J11), pas de
   ses 3,3 % d'octets : le J1 du lot A est un gain du format, propre à cette machine. Les comparaisons du mode rapide (R contre B, toutes deux sous la frontière) gardent leurs verdicts.
4. Le test du retrim de l'enquête (p7, § 7.5), à relire au motif de B20 s'il « tient ».
5. L'identité NVMe du disque (DRAM ou tampon dans l'hôte) : un geste sous administrateur, au choix de Stone.
6. Porter les recettes du § 10 dans RECETTES.md et ce jugement dans le mémoire (Tome II, « L'étage disque ») : figures
   proposées, tirées des CSV commités sous `mesures/disque/placement/juge/seance/` : (i) le motif croisé, quatre barres
   (A natif, A au motif B, B natif, B au motif A) avec les passes en points et la bande S ; (ii) le débit en fonction de la
   longueur médiane des requêtes (A natif, A raccourci, B natif, B allongé, R20) ; (iii) durée d'une lecture selon le
   nombre de morceaux, `lire.py` contre le chemin du moteur (C120) ; (iv) débit par lecture des non coupées de C120 selon
   la part des voisines coupées.
