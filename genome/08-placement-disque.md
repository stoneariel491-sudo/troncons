# 08 · Ce qui fait le débit d'un fichier sur ce NVMe, et comment l'exploiter

La demande de Stone (2026-10-22, ses mots) : « ok essaye de voir une correlation exploite entre la
fragmentation , position du fichier et de meilleurs résultat et exploitons le tout ».

Marques : [mes.] mesuré ici ; [calc.] calculé sur des mesures ; [litt.] littérature, non reproduite ;
[hyp.] hypothèse.

## 0. En bref

- **La position d'un fichier sur le volume ne dit rien de son débit** [mes.] : à l'intérieur du v1.0 du
  120b (de 6 % à 97 % du volume), ρ(débit, LCN) = 0,009 ; la bande où se trouve le v1.2 rapide se lit comme
  la bande basse (1,006).
- **La fragmentation compte seulement quand elle est extrême** [mes.] : le v1.0 recodé du lot A (C120,
  267 473 extents de 8 Kio en médiane) ~~perd un facteur 5,7 sur ses lectures coupées ; le modèle
  t(n) = 17,0 ms + (n − 1) × 0,37 ms rend son débit (1,24 Go/s) à 1 % près~~. À 5-233 extents, rien.
  [juge, `genome/JUGEMENT-placement.md` G3, M1 : ce facteur et ce modèle sont ceux de `lire.py` (quatre fils synchrones) ; par le chemin
  du moteur (une poignée chevauchée, un port de complétion), t₁ = 34 ms et τ = 9 à 11 µs par morceau, C120 se lit à
  1,33-1,38 Go/s, et sa fragmentation coûte × 1,26 en tout ; le contrôle « à 1 % » passe aussi pour un modèle
  constant.]
- ~~**Ce qui fait l'écart de 1,4 entre le v1.0 et le v1.2, c'est l'état physique des données sur le disque,
  pas le format** [mes.]~~ : le 20b le reproduit (B20 / A20 = 1,42) ; ~~à contenu égal au bit, C120 non coupé
  va plus vite que A120~~ ; une copie neuve de A20 (D20) se lit 2,35 Go/s une minute après l'écriture, puis
  retombe en deux heures **exactement** au débit de A20 (1,78 contre 1,76). ~~Les fichiers écrits le 17 (B20,
  B120, C120) restent, eux, rapides cinq jours après~~ ; **F20, écrit exactement comme le codeur, retombe lui
  aussi** (1,831 contre 1,780 à + 2 h, égaux) : ~~ni la manière d'écrire ni le format ne font cet écart ; il
  tient à un état du disque du 17 que je ne sais pas reproduire (§ 4.5)~~.
  [juge, `genome/JUGEMENT-placement.md` G1, G2, mesures du 26-27 octobre : **l'écart suit ~~la longueur~~ le motif des requêtes de lecture
  du format** (frontières et longueurs ; la longueur seule ne décide pas : couper les tronçons v1.0 en deux requêtes les
  ralentit, × 0,85 à 0,88, J10 et J11), pas le fichier ni le jour d'écriture. A20 lu avec les décalages et longueurs de B20 va comme B20
  (× 1,389), B20 lu avec ceux de A20 va comme A20 (× 0,715) ; A20 en requêtes raccourcies de 3,5 % va comme B20
  (× 1,421), B20 en requêtes allongées de 3,5 % comme A20 (× 0,713) : les requêtes de ~12,0 Mo du v1.0 sont lentes,
  celles de ~11,6 Mo du v1.2 et de 8,3 Mo des compagnons rapides ne le sont pas. C120 n'est pas plus rapide que
  A120 (seuls dans la file, ses tronçons non coupés vont à 0,980 de ceux de A120 : la comparaison « par lecture »
  était faussée par la composition de la file) ; R20, écrit le 22 à 0 h 46, va comme B20 cinq jours après
  (0,981). D20 et F20 « retombent » au niveau du motif v1.0, qu'ils gardaient. F20 à + 2 h 08 est au-dessus de A20
  dans 16 paires de passes sur 16 (+ 2,9 %) : pas « exactement ».]
- **Tués par les nombres** : position, ordre de lecture (1,028), cache de Windows (le disque lit
  1,000-1,006 fois ce qu'on demande), température (écart gardé à ± 2 °C, aucune transition thermique),
  âge seul, nombre d'extents pour A contre B, ~~manière d'écrire (D20 d'une traite et F20 comme le codeur
  retombent tous deux au débit de A20)~~, profondeur de file plus grande (q = 8 et 16 : 0,92 à 0,96).
  [juge, `genome/JUGEMENT-placement.md` G1 : les deux copies gardaient le motif de lecture v1.0 ; R20, écrit par l'écrivain du
  codeur le 22, ne retombe pas : la manière d'écrire n'est pas jugée par ces copies.]
- **La profondeur 2 va plus vite que 4** à l'étage disque (A20 × 1,08 à 1,125 ; B20 × 1,13 à 1,15),
  reproduit deux fois, mais sous le seuil déclaré sur A20 : levier non retenu, et son gain de bout en bout
  prédit (1,05 à 1,09) ~~est trop petit pour qu'une série ABBA le tranche~~.
  [juge, `genome/JUGEMENT-placement.md` M2 : le bruit des séries de bout en bout commitées va de 0,8 % (juge de la construction,
  e_soi de A20) à 4,6 % ; un gain de 5 % se tranche avec un seuil tiré de ce bruit ; il ne se tranche pas au
  plancher de 11,8 %, tiré de l'étage disque du 120b.]
- **Découvert** : le v1.0 du 120b, lu en entier, a des arrêts de 15 à 25 s à 0,2-0,37 Go/s, liés au temps
  et non à la région ; l'échantillon de 1 500 tronçons de la phase disque les cachait.
- **Le levier** : `carte.py` (diagnostic : extents, lectures coupées, en moins d'une seconde sans droit
  d'administrateur) et `placer.py` (réécriture contiguë à taille réservée, empreinte vérifiée). Il répare la
  fragmentation logique (prédit × 1,43 sur C120, commande écrite pour Stone : 103 Go libres demandés) ; il
  ne rend **rien** sur un fichier déjà contigu : **de bout en bout sur le 20b, 9,380 contre 9,398 jetons/s
  (1,002), mêmes 256 jetons, mêmes octets par jeton**.
- **L'hypothèse de relais (retrim, repos, disposition dans la NAND) tombe** au seuil déclaré : G20a et G20b,
  écrites juste après le retrim de Stone du 26, à + 2 h 06 : 1,778 et 1,778 Go/s contre A20 1,734 et B20
  2,506 (1,025 × A20 ; témoin G20b / G20a 0,9998 ; § 4.6).
- **Pour tout le projet** : une comparaison de vitesse entre deux `.trc` écrits à des moments différents
  mesure d'abord leur état sur le disque (lot A, lot B, juge). Relever `troncons disque` par fichier
  avant toute séance de vitesse.

## D'où on part, où on va

Le lot A (`genome/06-codon-v1-2.md` § 8) a mesuré, machine calme, que l'étage disque seul
(`troncons disque --n 1500 --graine 20261017`, lectures sans tampon d'un tronçon entier, 4 en vol)
lit trois fichiers du 120b à des débits très différents : le v1.0 d'origine (A) 1,742 et 1,741 Go/s, le
v1.2 (B) 2,254 et 2,391, le v1.0 recodé (C, **identique à A au bit**) 1,356 et 1,331. Le format ne peut
rendre que les 3,3 % d'octets qu'il retire. Le nombre de fragments relevé (A 65, B 233, C des dizaines
de milliers) n'ordonne pas les débits : B a plus de fragments que A et va plus vite. Ce document cherche
ce qui explique le débit, le prouve par la mesure, et l'exploite.

## 1. P1 : la carte des fichiers, sans lecture lourde [mes.]

Outil : `outils/disque/placement/carte.py` (FSCTL_GET_RETRIEVAL_POINTERS par ctypes, lecture seule, sans
droit d'administrateur ; RÉPERTOIRE du `.trc` lu et son empreinte64 vérifiée ; ordre de la phase disque
recalculé par le même xorshift64* que `moteur/bins/troncons/src/main.rs`). Témoin : un fichier de 16 Mio
écrit d'une traite, somme des grappes des extents = ⌈taille / 4 096⌉ et projection d'une lecture du
fichier entier = autant de morceaux que d'extents ; cassure : un extent retiré de la liste, le témoin de
couverture **tombe** (journal de la commande `carte.py temoin`). Cartes complètes :
`mesures/disque/placement/carte-<fichier>.json` (chaque extent : VCN, grappes, LCN ; chaque tronçon :
décalage, longueur lue, morceaux, LCN). Corrélation : `p1_correler.py` → `p1-correlation.json`,
`p1-mesures-disque.csv` (les 18 passes `troncons disque` commitées, avec l'âge du fichier à la mesure).

Volume C: : 242 283 857 grappes de 4 096 octets.

| | A120 v1.0 d'origine | B120 v1.2 | C120 v1.0 recodé | A20 v1.0 | B20 v1.2 |
|---|---|---|---|---|---|
| extents (relevé complet) | 65 | 233 | **267 473** | 33 | 29 |
| extent médian | 315 Mo | 134 Mo | **8 Kio** | 397 Mo | 175 Mo |
| LCN moyen (fraction du volume) | 0,637 | 0,822 | 0,521 | 0,411 | 0,806 |
| tronçons coupés par une frontière (répertoire) | 52 / 4 608 | 226 / 4 608 | 1 203 / 4 608 | 27 / 768 | 17 / 768 |
| morceaux par lecture, phase disque (1 500 lectures) | 1,009 | 1,051 | **60,0** | 1,035 (768) | 1,022 (768) |
| morceaux par appel, trace J1 (708 jetons) | 1,015 | 1,061 | 56,4 | 1,040 | 1,024 |
| écrit (heure locale) | 10-15 15 h 50-16 h 10 | 10-17 9 h 14-9 h 38 | 10-17 11 h 45-12 h 25 | 10-15 13 h 05-13 h 22 | 10-17 8 h 53-8 h 59 |
| débit d'écriture du codeur | 50,1 Mo/s | 40,1 Mo/s | 23,9 Mo/s | 11,1 Mo/s | 30,1 Mo/s |

Tous les cinq ont été écrits par le **même écrivain** (`trc-codeur`, `trc_format::Ecrivain` : un fil,
`BufWriter` de 8 Mio sur un `File::create`, écriture tamponnée par le cache de Windows, fichier qui croît
sans taille réservée ; `moteur/crates/trc-format/src/lib.rs` l. 1149-1220), à 11 à 50 Mo/s : le codage
borne l'écriture, le disque n'est jamais pressé. La copie de s1 (`copie_temoin.sh`, `cp` de Git Bash) a
écrit à 54 Mo/s pendant que d'autres équipes écrivaient (289 545 fragments).

Les débits déjà mesurés, par fichier et par âge [mes., `p1-mesures-disque.csv`] :

| fichier | âge à la mesure | Go/s | durée médiane d'une lecture (4 en vol) |
|---|---|---|---|
| A120 | 6,7 h | 1,862 ; 1,834 | 25,1 ; 24,6 ms |
| A120 | 14,5 h | 1,874 ; 1,893 | 24,2 ; 24,0 ms |
| A120 | 43 h (s1, autres équipes actives) | 1,644 ; 1,548 | 28,8 ; 30,0 ms |
| A120 | 152 h (s2, calme) | 1,742 ; 1,741 | 27,2 ; 27,6 ms |
| B120 | 1,9 h (s1) | 2,578 ; 2,309 | 16,2 ; 19,4 ms |
| B120 | 110 h (s2, calme) | 2,254 ; 2,391 | 20,4 ; 19,4 ms |
| C120 | 108 h (s2, calme) | 1,356 ; 1,331 | 32,6 ; 32,9 ms |

**Le bruit d'un fichier à lui-même** (deux passes d'une même séance calme) : 0,03 % à **5,9 %** (B120,
s2) ; c'est la grandeur nommée d'où dérivent les seuils du § 2.

**Ce que la carte tue déjà, par les nombres** [calc.] :
- **le nombre d'extents n'explique pas A contre B** : A a 1,009 morceau par lecture et B 1,051 ; si les
  coupures coûtaient, B serait le plus lent ; il est le plus rapide de 29 %. Il ne peut expliquer que C
  (60 morceaux par lecture en moyenne, 405 lectures coupées sur 1 500, jusqu'à 2 925 morceaux pour une
  seule lecture de 12 Mo) ;
- **l'âge seul n'explique pas A contre B** : A à 6,7 h d'âge (1,86 Go/s) était déjà plus lent que B à
  110 h (2,25 à 2,39). Reste ouvert un effet d'âge qui se fixerait dans les premières heures (repli de
  l'antémémoire SLC vers la TLC, par exemple), et la dérive lente de A lui-même : 1,86-1,89 le 16 contre
  1,74 le 22, soit −7 %, au-delà de son propre bruit (≤ 1,5 %) ;
- **la position LCN moyenne** sépare A (0,64) de B (0,82), et A20 (0,41) de B20 (0,81) : elle reste à
  départager (H2), mais A s'étend lui-même de 0,06 à 0,97 du volume, ce qui permet de la tester à
  l'intérieur d'un même fichier, sans rien écrire.

La température du disque est lisible sans droit d'administrateur : le journal SMART / santé NVMe
(IOCTL_STORAGE_QUERY_PROPERTY, StorageDeviceProtocolSpecificProperty, page 02h) rend la température
composite (55 °C au relevé de 1 h 33), les compteurs d'unités lues et écrites par l'hôte et les
transitions de gestion thermique. Il servira de témoin indépendant des octets lus (§ 2, H5) et de relevé
thermique (H6).

## 2. Le plan, déclaré avant toute mesure (2026-10-22, 1 h 45)

### 2.1 Les grandeurs et les seuils

- **e_soi** : pour chaque fichier d'une série, l'écart relatif |x₁ − x₂| / moyenne entre ses deux
  passes de la même séance (ABBA : chaque fichier passe deux fois). **Seuil de séparation entre deux
  fichiers : S = max(2 · max e_soi de la séance, 11,8 %)**, où 11,8 % = 2 × 5,9 %, le plus grand bruit
  à soi-même déjà commité en séance calme (B120, s2). Deux fichiers « diffèrent » si leurs médianes
  diffèrent de plus de S ; ils « sont égaux » si elles diffèrent de moins de S / 2.
- **Comparaisons à l'intérieur d'un fichier** (bandes de LCN, lectures coupées ou non) : sur le débit
  par lecture (octets / durée de la lecture, 4 en vol), rapport des médianes de deux groupes. Bruit de
  référence : le même rapport entre deux moitiés tirées au hasard du même ensemble de lectures (200
  tirages, graine 20261022) ; **seuil S_b = max(2 × le 95e centile de |r − 1| des tirages, 5 %)**.
- Une passe n'est valable que machine calme (§ 2.3) ; une passe sous charge ne conclut pas.

### 2.2 Les hypothèses et leurs prédictions chiffrées

- **H1, taille et nombre d'extents, lectures coupées.** Une lecture sans tampon coupée par des frontières
  d'extent part en autant de requêtes que de morceaux. Prédiction : sur C120, le débit par lecture des
  lectures d'un seul morceau dépasse celui des lectures de ≥ 10 morceaux de plus de S_b, et un modèle
  t(n) = t₁ + (n − 1) τ ajusté sur les lectures paires prédit le débit des lectures impaires à 10 % près.
  Pour A contre B, H1 est déjà tuée (§ 1). Ma prédiction : H1 tient pour C et seulement pour C.
- **H2, position LCN.** Sur NVMe, la correspondance logique-physique passe par la FTL ; le LBA ne dit rien
  de l'emplacement sur la puce. Prédiction : à l'intérieur de A120 (LCN de 0,06 à 0,97) et de B120, le
  rapport des débits par lecture entre la bande LCN > 0,75 et la bande LCN < 0,5 reste dans ±S_b, et
  |ρ de Spearman| (débit par lecture contre LCN) < 0,2. Si, dans A120, la bande haute va à la vitesse
  de B120 et la basse à celle de A120, H2 tient. Ma prédiction : elle tombe.
- **H3, manière d'écrire.** La FTL range les pages physiques dans l'ordre d'arrivée des écritures ; un
  fichier écrit en filet, mêlé à d'autres écrivains, n'a pas la même disposition physique qu'un fichier
  écrit d'une traite. Test sur le 20b (§ 2.4) : D20 = copie neuve de A20, taille réservée d'avance, une
  seule écriture séquentielle sans tampon par morceaux de 8 Mio ; E20 = copie neuve de A20, taille
  réservée, écrite par morceaux de 64 Kio entrelacés avec des écritures de 64 Kio dans un fichier de
  brouillage de 256 Mio réécrit en boucle (même NTFS contigu, autre flux vers la FTL). Prédictions :
  si H3 tient, D20 dépasse E20 de plus de S ; et si A20 est lent comme A120, D20 dépasse A20 de plus de
  S (réécrire d'une traite répare).
- **H4, ordre de lecture du moteur contre ordre physique.** Mêmes 1 500 tronçons, lus dans l'ordre de la
  phase disque (aléatoire) puis triés par décalage. Prédiction : |r − 1| < S / 2 (lectures de 12 Mo,
  aucun intérêt du séquentiel à cette taille sur NVMe ; le tableau de `fondations/01-machine.md` § 2.4
  donne 16 Mio aléatoire QD 1 = 2,82 Go/s, au niveau du séquentiel). Ma prédiction : elle tombe.
- **H5, caches.** (a) Le cache de Windows : `FILE_FLAG_NO_BUFFERING` le contourne par construction ;
  témoin : les unités lues par l'hôte du journal SMART (unités de 512 000 octets) avancent, pendant une
  passe, d'au moins 98 % des octets demandés (si un cache servait, le disque lirait moins). (b)
  L'antémémoire SLC : D20 lu dans les 10 min qui suivent son écriture, puis après au moins 60 min sans
  écriture de ma part ; si les données fraîches se lisent depuis la SLC, la première lecture dépasse la
  seconde de plus de S. Ma prédiction : (a) tombe par construction ; (b) faible (B120 à 1,9 h et à
  110 h ne diffèrent pas au-delà de son bruit).
- **H6, âge des données et thermique.** L'âge seul est tué pour A contre B (§ 1). Thermique : la
  température composite SMART est relevée avant et après chaque passe ; prédiction : dans une série ABBA,
  l'écart A/B se garde quand les passes A et B sont à moins de 3 °C l'une de l'autre, et aucune transition
  de gestion thermique (compteurs TMT1/TMT2) ne survient pendant les passes.

### 2.3 Le protocole

- **Verrou** : `~/dev/verrou-carte.txt`, attendu s'il existe depuis moins de 2 h, pris par
  une ligne « placement disque, date, séance de vitesse ABBA <nom>, script, pid » (le flux des pistes se
  met en pause sur « vitesse »), rafraîchi avant chaque passe, rendu à la fin de chaque séance.
- **Calme** : avant et après chaque passe, relevé des processus des autres flux (python, trc-*, cargo,
  rustc, juge, genome-capture, troncons ; hors serveurs http et blender-mcp, hors mes processus) qui
  prennent plus de 5 % d'un cœur ou lisent plus de 8 Mo en 3 s ; départ sur deux relevés vides à une
  minute d'écart ; passe marquée « SOUS CHARGE » sinon. Secteur à chaque passe (Win32_Battery
  BatteryStatus = 2). Unités écrites par l'hôte (SMART) avant et après : un autre écrivain se voit.
- **Instruments** : `troncons disque` (l'instrument du lot A, inchangé) pour les débits par fichier, et
  `outils/disque/placement/lire.py` (mes lectures : même motif, sans tampon, 4 fils, une poignée par fil,
  durée de chaque lecture journalisée avec son décalage et son LCN) pour les profils. Témoin de `lire.py` :
  sur la même série, son débit égale celui de `troncons disque` à S / 2 près ; les octets lus de 16
  lectures tirées égalent, au SHA-256, ceux d'une lecture tamponnée indépendante ; cassure : décalage
  faussé de 4 096 octets pour la comparaison, le témoin doit tomber.
- **Séance P2-a (lecture seule)** : ABBA `troncons disque` sur A20, B20 (A B B A A B B A) ; puis profils
  complets `lire.py` (chaque tronçon une fois, ordre tiré) sur A120, B120, C120, A20, B20 ; puis H4 sur
  A120 et B120 (aléatoire, trié, trié, aléatoire).
- **Séance P2-b (écriture)** : avant chaque copie, place libre ≥ taille + 45 Go ; une seule copie de
  ≤ 11,2 Go à la fois, sous `~/dev/essais/troncons/placement/` ; SHA-256 de la copie (lecture
  sans tampon) égal à celui de l'original publié par le codeur (`recoder.log`, e8bd6ae1…169f pour A20) ;
  extents relevés ; ABBA `troncons disque` A20 / D20 (puis E20) ; profil ; H5(b) ; copie effacée.
- **P3 (levier)**, seulement si une cause tient au seuil : outil de placement qui réécrit un `.trc` d'une
  traite (et, si H4 tenait, dans l'ordre du moteur), empreinte vérifiée ; gain de bout en bout mesuré sur
  le 20b en ABBA (`troncons mesurer`, mêmes jetons, octets lus par jeton inchangés), sous le verrou.

### 2.4 Ce qui serait une surprise

- Que A20 et B20 ne diffèrent pas : le 20b ne reproduirait pas l'écart du 120b, et H3 se jugerait sur
  D20 contre A20 seulement.
- Que D20, réécrit d'une traite, reste aussi lent que A20 : la cause ne serait alors ni la disposition
  NTFS, ni la manière d'écrire, mais quelque chose que le contenu ou l'emplacement physique porte.

### 2.5 Amendement, déclaré le 2026-10-22 à 6 h 10, avant toute mesure de F20

Ce qui l'appelle (§ 4.2) : D20, copie de A20 écrite d'une traite, rendait 2,35 Go/s une minute après son
écriture, 2,18 trois minutes après, et **1,78 deux heures après, à égalité avec A20 (1,76)**. Réécrire
d'une traite ne répare pas : le neuf rapide redevient lent en moins de deux heures. Or B20, B120 et C120,
écrits le 2026-10-17 par le codeur, restent rapides cinq jours après. Ce qui les distingue de D20 et ce qui
se reproduit sans geste interdit : la **manière d'écrire du codeur** (écriture tamponnée par le cache de
Windows, morceaux de 8 Mio, fichier qui croît, ~30 Mo/s).

- **F20** = copie de A20 écrite comme le codeur (`placer.py copier --mode filet --debit-mo-s 30`).
  Séance p2b-F : écriture, lecture à + 1 min, empreinte, carte, `troncons disque` A F B B F A. Séance
  p2b-F2, **au moins 2 h** après la fin de l'écriture : A F B B F A A F B B F A.
- **Prédiction et seuil** (S comme au § 2.1) : si la manière d'écrire du codeur fait le débit de B, alors à
  + 2 h, F20 / A20 > 1 + S et |F20 / B20 − 1| < S / 2 ; si F20 retombe comme D20 (|F20 / A20 − 1| < S / 2),
  la manière d'écrire n'est pas la cause, et la rapidité des fichiers du 17 tient à un état du disque de
  ce jour-là que je ne sais pas reproduire.
- **E20 (entrelacée) est abandonnée**, avec sa raison chiffrée : son test (E20 plus lente que D20 de plus de
  S) n'a plus d'objet, D20 étant déjà retombé au niveau de A20 ; elle ne peut pas fournir de levier. Les
  12 Go de place temporaire vont à F20.

### 2.6 Amendement, déclaré le 2026-10-22 à 6 h 30, avant toute mesure : H7, la profondeur de file

Si la lenteur de A20 tient à des lectures plus longues de la puce (réessais, par exemple) et non à un
débit plafonné, plus de lectures en vol la cacheraient : c'est un levier du moteur (`--profondeur`, 4 par
défaut). Séance p4 : `troncons disque --profondeur q`, q = 4, 8, 16, 2, 2, 16, 8, 4, chaque q sur A20 et
B20 (ordre alterné). **Prédiction** (`fondations/01-machine.md` § 2.4 : le plateau des gros blocs ne
dépend pas de la profondeur) : |débit(q = 8) / débit(q = 4) − 1| < S / 2 sur les deux fichiers. **Levier
retenu** si, sur A20, débit(q) / débit(4) > 1 + S pour un q, la même profondeur ne dégradant pas B20 de
plus de S / 2.

### 2.7 Amendement, déclaré le 2026-10-22 à 10 h 35, après p4 et avant p5

p4 (§ 4.4) a montré, sans que ce fût prédit, que **q = 2 va plus vite que q = 4** sur les deux fichiers
(A20 × 1,125, B20 × 1,133), mais sous le seuil S = 14,6 % de la séance (le bruit de B20 à q = 4 y vaut
7,3 %) : « entre deux », pas de levier au sens déclaré. Séance p5 : q = 1, 2, 4 seulement, **quatre passes
par (fichier, q)** pour serrer le bruit (ordre 4 2 1 1 2 4 4 2 1 1 2 4, A et B alternés), mêmes seuils et même
règle du levier (§ 2.6). Si q* (1 ou 2) tient : séance p6, bout en bout, `troncons mesurer --profondeur q*`
contre `--profondeur 4` sur A20, A Q Q A A Q Q A ; levier retenu si le rapport des médianes de jetons/s
dépasse 1 + S (S de la séance, au moins 11,8 %), mêmes 256 jetons et mêmes octets par jeton exigés.

### 2.8 Amendement, déclaré le 2026-10-26 à 23 h 49 (commit bcae307), avant toute écriture : l'hypothèse de relais, après le retrim

**L'hypothèse** (de la session relais, non prouvée) : la vitesse de lecture suit la disposition physique
dans la NAND. Après un grand effacement, un retrim et du repos, le SSD dispose de blocs effacés contigus ;
les données repliées de la SLC vers la TLC y sont réparties en superblocs sur tous les dies et restent
rapides ; sur un espace libre haché, elles sont dispersées. Ses faits : retrim et défragmentation complets
le 15 à 22 h 52, ≈ 230 Go effacés d'un coup le 16 vers 21 h, redémarrage à 21 h 30, fichiers rapides écrits
le 17 entre 9 h et 12 h 25 sur ≈ 200 Go libres. Contre-faits : D20 (22 oct., ≈ 110 Go libres) et F20 (22 oct.,
≈ 90 Go libres) sont retombés ; R20 (compagnon λ = 0 du lot B, écrit le 22 vers 0 h 50) était encore rapide
à + 6 h (relevé du juge).

**Le geste de Stone** (pas le mien) : retrim du volume C:, terminé le 2026-10-26 à 23 h 46 min 44 s (journal
Application, Microsoft-Windows-Defrag, événement 258). Place libre relevée à 23 h 47 : 94 Go.

**Le protocole** :
1. Repos : aucune écriture lourde de ma part avant 0 h 20 (30 min après le retrim) ; le juge peut lire, le
   flux des pistes peut tourner ; ils sont relevés (relevé des autres flux, unités écrites SMART).
2. Séance p7, sous le verrou, machine calme : G20a puis G20b, deux copies de A20 écrites l'une après l'autre
   comme le codeur (`placer.py --mode filet`, tamponné, 8 Mio, 30 Mo/s) ; SHA-256 de chacune égal à
   e8bd6ae1…169f ; carte de chacune ; lecture fraîche ; `troncons disque` A Ga Gb B B Gb Ga A. Place :
   22,4 Go à moi pour ce pas (dérogation à la règle des 12 Go, accordée pour avoir deux copies du même
   état), au moins 45 Go libres après chaque copie.
3. Séance p7-2, au moins 2 h après la fin de l'écriture de G20b : `troncons disque` en deux tours A Ga Gb
   B B Gb Ga A (chaque fichier quatre fois, comparé à lui-même), profils complets de G20a et G20b,
   témoin SHA-256 de lire.py et sa cassure (décalage faussé de 4 096 octets).
4. **Seuil** : S = max(2 · max e_soi de p7-2, 18,3 %), où 18,3 % est le S de la séance p2b-Fb2 (bruit de
   B20 9,2 %), le plus grand déjà mesuré dans ce protocole ; je prends le plus sévère des deux.
5. **Verdicts** (médianes de p7-2) : l'hypothèse **tient** si G20a / A20 > 1 + S et G20b / A20 > 1 + S, et
   |G20a / B20 − 1| ≤ S et |G20b / B20 − 1| ≤ S ; elle **tombe** si |G20a / A20 − 1| < S / 2 et
   |G20b / A20 − 1| < S / 2 ; sinon, « entre deux ». **Témoin** : |G20a / G20b − 1| ≤ S, sinon la séance
   ne juge pas. **Cassure** : lire.py avec `--casser` doit rendre 0 lecture égale sur 16.
6. Si elle tient : séance p8, `troncons mesurer` A20 contre G20a, A G G A A G G A, mêmes 256 jetons et mêmes
   octets par jeton exigés, levier si le rapport des médianes de jetons/s dépasse 1 + S(p8).
7. G20a et G20b effacés à la fin.

**Ma prédiction, écrite avant** : **elle tombe** (G20a et G20b à + 2 h dans ±9 % de A20), avec une
confiance modeste (≈ 60 %). Raisons : D20 et F20 sont retombés à 90-118 Go libres sur ce même disque ; un
retrim ne remet pas à zéro ce que la FTL sait déjà des blocs libres (Windows lui envoie déjà les TRIM à
chaque effacement), et 94 Go libres d'aujourd'hui sont moins que les ≈ 200 Go du 17. Ce qui me ferait
avoir tort : R20, écrit lui aussi à environ 110 Go libres, encore rapide à + 6 h.

## 3. P2-a : la séance de lecture seule (2026-10-22, 2 h 18 à 2 h 33) [mes.]

`seance.py p2a` (32 passes, verrou pris à 2 h 18 après celui du lot B, départ sur deux relevés vides à
2 h 20), analyse `analyse.py p2a` → `mesures/disque/placement/p2a/analyse.json`, profils
`p2a/*-lire-tout-*.csv`, fenêtres de 256 Mio `p2a/profil-*.csv`. **Aucune passe sous charge** ; secteur
à chaque passe ; **aucune transition de gestion thermique** (compteurs TMT1 et TMT2 du journal SMART
inchangés dans les 32 passes) ; température composite de 53 à 74 °C.

### 3.1 Les témoins

- **lire.py contre troncons disque** (mêmes 768 tronçons, même ordre, même profondeur) : rapport des
  médianes 0,976 (A20) et 0,959 (B20), sous S / 2 = 5,9 % : **tient**. lire.py rend le même étage disque
  que l'instrument du lot A, à 2 à 4 % près (le fil Python coûte un peu).
- **Contenu** : 16 lectures sans tampon égales, au SHA-256, à 16 lectures tamponnées indépendantes
  (16/16) ; cassure, décalage faussé de 4 096 octets : 0/16, **le témoin tombe** comme il doit.
- **H5 (a), le cache de Windows** : dans chaque passe, les unités lues par l'hôte du journal SMART
  avancent de **1,0000 à 1,0057 fois les octets demandés**. Le disque lit tout ce qu'on demande ; aucun
  cache ne sert les données. **H5 (a) tombe**, comme prévu par construction.

### 3.2 Le 20b reproduit l'écart

`troncons disque`, A B B A A B B A : A20 1,823 ; 1,846 ; 1,848 ; 1,825 Go/s ; B20 2,592 ; 2,632 ; 2,537 ;
2,631. e_soi 1,4 % et 3,7 % ; S = max(2 × 3,7 %, 11,8 %) = 11,8 %. **B20 / A20 = 1,423 : ils diffèrent**
(0,42 > S). Les octets demandés ne diffèrent que de 3,3 %. Températures des passes A et B à moins de
2 °C les unes des autres : **l'écart se garde à température égale ; H6 thermique tombe**.

### 3.3 La position (H2) tombe

Profils complets (chaque tronçon une fois, ordre tiré, deux passes par fichier) :

| fichier | Go/s (2 passes) | débit par lecture médian | ρ(débit, LCN) | bande LCN > 0,75 / bande < 0,5 | S_b |
|---|---|---|---|---|---|
| A120 | 1,146 ; 0,848 | 0,421 ; 0,402 | 0,009 ; −0,011 | 1,006 ; 0,979 | 5 % |
| B120 | 2,473 ; 2,433 | 0,629 ; 0,616 | 0,049 ; 0,037 | 0,997 ; 0,991 | 5 % |
| C120 | 1,245 ; 1,238 | 0,723 ; 0,721 | 0,267 ; 0,284 | 1,131 ; 1,149 | 5 % |
| A20 | 1,802 ; 1,809 | 0,461 ; 0,463 | 0,001 ; 0,012 | (aucune lecture > 0,75) | 5 % |
| B20 | 2,540 ; 2,494 | 0,650 ; 0,634 | 0,012 ; −0,051 | 1,016 ; 0,979 | 7,4 % ; 5,7 % |

À l'intérieur de A120, qui s'étend de 0,06 à 0,97 du volume, les lectures de la bande haute (là où est
B120) vont exactement comme celles de la bande basse (1,006 et 0,979, dans ±5 %) et |ρ| < 0,02.
**H2 tombe, comme prédit** : la position logique ne dit rien du débit. La seule corrélation avec le LCN
(C120, ρ = 0,27) suit la fragmentation (ρ(débit, morceaux) = −0,46 ; les régions basses du volume y
sont plus morcelées).

### 3.4 Les extents (H1) : ils expliquent C, et seulement C

Dans C120, les 3 405 lectures d'un seul morceau vont à **0,763 et 0,759 Go/s** par lecture (médiane),
les 722 lectures de 10 morceaux ou plus à 0,133 et 0,136 : rapport **5,75 et 5,57**, très au-delà de
S_b = 5 % : **H1 tient pour C**. Le modèle t(n) = t₁ + (n − 1) τ, ajusté sur les lectures paires, prédit la
durée totale des impaires à 0,980 et 0,991 (dans les 10 % déclarés) : **t₁ = 17,0 et 17,2 ms** pour 12 Mo
à 4 en vol, **τ = 365 et 368 µs par morceau de plus** [calc. sur mes.]. Une lecture de 12 Mo coupée en 220
morceaux coûte donc ≈ 17 + 219 × 0,37 ≈ 97 ms au lieu de 17.

~~Mais **les lectures non coupées de C120 vont aussi vite que celles de B120** (0,76 par lecture contre
0,62-0,63 ; t₁ 17,0 ms contre 19,4) **et bien plus vite que celles de A120** (0,42 ; ≈ 28 ms hors des
arrêts), alors que **C et A ont le même contenu au bit**. C'est le résultat central de la séance : à
octets égaux, le fichier écrit le 2026-10-17 se lit 1,6 fois plus vite que celui du 2026-10-15, dès que
NTFS ne le coupe pas. Ni le format, ni le contenu, ni la position logique ne font le débit : c'est
l'état physique des données que la FTL a rangées.~~

[juge, `genome/JUGEMENT-placement.md` G2 : un débit « par lecture » dépend des voisines en vol. Dans ces journaux mêmes, les
lectures non coupées de C120 entourées surtout de lectures coupées vont à 0,874 et 0,879 Go/s, celles entourées
surtout de non coupées à 0,431 et 0,446, le niveau de A120 ; quatre lectures à 0,763 feraient 3,05 Go/s, plus que le
disque n'a jamais rendu. Lus seuls, les tronçons d'un seul extent de C120 vont à 0,980 de ceux de A120.]

### 3.5 Une surprise : les arrêts de A120

Lu en entier, A120 rend 1,146 puis 0,848 Go/s, alors que ses 1 500 tronçons de la phase disque se lisent
à 1,742 et 1,727 dans la même séance. Le débit par tranches de 5 s le montre : des **plages de 15 à 25 s
à 0,2-0,37 Go/s** entre des plages à 1,72-1,75 (passe 15 : 1,72 1,73 1,74 1,73 1,72 **0,37 0,30 0,31
0,30** 1,16 ; passe 20 : 1,72 **0,36 0,30 0,20 0,30** 1,69 1,75 1,20 **0,22 0,30 0,30** 1,01 1,61). Les deux
passes lisent les tronçons dans le **même ordre**, mais les arrêts n'y tombent pas aux mêmes lectures :
ρ(débit par lecture de la passe 15, de la passe 20) = **0,012** pour A120 (0,68 pour C120, dont la
lenteur est attachée aux régions morcelées). **Les arrêts sont liés au temps, pas à la région** ;
pendant un arrêt, une lecture va 5,7 fois moins vite (0,075 contre 0,431 Go/s). Aucun arrêt n'apparaît
sur B120, C120, B20 ni A20 (passes de 4 à 45 s), ni pendant les passes courtes (10 s) de A120 ; aucun
compteur thermique ne bouge ; le disque n'écrit pour l'hôte que 1 à 22 Mo pendant ces passes. Ce
n'était pas déclaré : c'est une observation, pas un verdict. [hyp.] Un travail de fond du contrôleur
déclenché par la lecture de vieilles données (relecture avec réessais, rafraîchissement ou recopie de
blocs dont le taux d'erreur corrigé monte), qui ralentit tout le disque le temps qu'il dure ; elle se
teste par le même chemin que H3 : une copie neuve de A20 doit perdre et la lenteur de base et les arrêts.

### 3.6 L'ordre de lecture (H4) tombe pour B ; il ne se juge pas sur A

B120, mêmes 1 500 tronçons : aléatoire 2,438 et 2,452, trié par décalage 2,510 et 2,516 Go/s ; rapport
**1,028 < S / 2 : égaux**, H4 tombe comme prédit. Sur A120, le trié rend 1,256 et 1,054 contre 1,742 et
1,727, mais la première passe triée va à 1,76 puis 1,66 Go/s avant de tomber dans un arrêt (§ 3.5) : la
différence vient des arrêts, pas de l'ordre ; H4 ne se juge pas sur A.

### 3.7 Où on en est après P2-a

| hypothèse | verdict | par quels nombres |
|---|---|---|
| H1 extents | tient pour C120, tuée pour A contre B | C : 5,7 × entre 1 et ≥ 10 morceaux ; A 1,009 morceau/lecture < B 1,051 |
| H2 position LCN | **tombe** | ρ = 0,009 / −0,011 dans A120 ; bandes 1,006 / 0,979 |
| H3 manière d'écrire | à juger (P2-b) | C (17 oct.) non coupé 1,6 × plus rapide que A (15 oct.), même contenu |
| H4 ordre | tombe (B) | trié / aléatoire 1,028 |
| H5 (a) cache Windows | tombe | disque lu / demandé 1,0000-1,0057 |
| H5 (b) SLC | à juger (P2-b) | |
| H6 thermique | tombe | écart 1,42 à ±2 °C ; aucun TMT |
| H6 âge seul | tuée (§ 1) | A à 6,7 h plus lent que B à 110 h |

## 4. P2-b : réécrire d'une traite (H3, H5 b) [mes.]

### 4.1 La copie D20 (séance p2b-D, 2026-10-22, 3 h 40 à 3 h 45)

`placer.py copier --mode traite` : A20 lu sans tampon et récrit dans
`~/dev/essais/troncons/placement/D20.trc`, taille réservée d'avance, une seule écriture
séquentielle sans tampon et à écriture directe (`FILE_FLAG_WRITE_THROUGH`), morceaux de 8 Mio : **11,157 Go
en 35,1 s (318 Mo/s)**, le disque a écrit 11,171 Go pour l'hôte (SMART), **5 extents** (contre 33 pour A20),
LCN moyen 0,781. **SHA-256 de D20 = e8bd6ae1…169f**, celui que Get-FileHash a publié pour A20 le 2026-10-15
(chemin indépendant) : même contenu au bit. Place libre avant : 118,5 Go ; règle des 45 Go tenue.

`troncons disque` A D B B D A (machine calme, aucune passe sous charge) :

| fichier | Go/s (2 passes) | médiane |
|---|---|---|
| A20 (écrit le 15, en filet) | 1,819 ; 1,862 | 1,841 |
| D20 (même contenu, écrit d'une traite aujourd'hui) | 2,186 ; 2,174 | 2,180 |
| B20 (v1.2, écrit le 17, en filet) | 2,572 ; 2,511 | 2,541 |

e_soi ≤ 2,4 % ; S = 11,8 %. **D20 / A20 = 1,185 : ils diffèrent** — réécrire le même contenu le rend
18 % plus rapide à l'étage disque. Mais **D20 / B20 = 0,858 : ils diffèrent aussi** : le neuf d'une traite
ne rattrape pas le v1.2 écrit en filet deux jours plus tôt, alors que les octets lus ne diffèrent que
de 3,3 %. Lu une première fois **1 min après la fin de l'écriture** par lire.py (plan disque), D20 rendait
2,345 Go/s, puis 2,186, 2,174, et ses profils complets 2,095 et 2,124 : il ralentit dans les minutes qui
suivent l'écriture. [hyp.] Le repli de l'antémémoire SLC vers la TLC, que le contrôleur fait pendant que
nous lisons ; c'est ce que juge la relecture après au moins 60 min sans écriture (p2b-D2, § 4.2).

### 4.2 D20 relu deux heures après (séance p2b-D2, 5 h 55 à 5 h 58) : H5 (b) tient

Le verrou a été tenu par le juge de 3 h 56 à 5 h 20, puis le calme a manqué jusqu'à 5 h 54 (un calcul de
KL du juge sur 4 cœurs) : la relecture a eu lieu **2 h 14 après l'écriture**. A D D A A D D A :

| fichier | Go/s | médiane |
|---|---|---|
| A20 | 1,722 ; 1,760 ; 1,760 ; 1,831 | 1,760 |
| D20 | 1,746 ; 1,767 ; 1,796 ; 1,791 | 1,779 |

e_soi(A20) = 6,2 % ; S = 12,4 %. **D20 / A20 = 1,011 : égaux.** Le profil complet de D20 rend 1,779 Go/s.
**H5 (b) tient** au seuil déclaré : D20 lu frais (2,345, puis 2,18) dépasse D20 relu après deux heures
(1,78) de 32 % et 22 %, plus que S. Le contenu de A20, récrit d'une traite, se lit vite tant qu'il est
frais, puis revient en moins de deux heures exactement au débit de A20. **La disposition NTFS (5 extents
contre 33) n'y change rien** ; la manière d'écrire « d'une traite » non plus.

Ce que cela veut dire pour B : les fichiers du 2026-10-17 (B20, B120, C120) sont restés rapides cinq jours.
Ce n'est donc pas « frais contre vieux » au sens de D20. L'amendement du § 2.5 teste la seule différence
reproductible.

### 4.3 F20, écrit comme le codeur (séance p2b-F, 7 h 15 à 7 h 25)

`placer.py copier --mode filet --debit-mo-s 30` : 11,157 Go en 371,9 s (30 Mo/s), **95 extents**, SHA-256
égal à e8bd6ae1…169f. Frais (+ 0 à 4 min) : `troncons disque` A20 1,758 et 1,784 ; **F20 2,195 et 2,189** ;
B20 2,442 et 2,459 ; F20 / A20 = 1,238 (diffèrent), F20 / B20 = 0,895 (entre deux). Frais, F20 se comporte
comme D20 frais. ~~**La relecture à + 2 h, qui seule juge l'amendement du § 2.5, n'a pas eu lieu** : le
portable est passé sur batterie à 8 h 19 (BatteryStatus 1) et n'est pas revenu sur secteur ; à
10 h 03, F20 a été effacé pour ne pas laisser 11 Go derrière moi. L'amendement reste ouvert.~~
Ce qui a changé : le secteur est revenu à 10 h 07 ; F20 a été réécrit à l'identique et relu à + 2 h (§ 4.5).

### 4.5 F20 réécrit (p2b-Fb, 10 h 10 à 10 h 20) et relu deux heures après (p2b-Fb2, 12 h 24 à 12 h 29) [mes.]

F20 réécrit comme le codeur : 11,157 Go en 371,9 s (30 Mo/s), 91 extents, SHA-256 égal à e8bd6ae1…169f.
**Frais** : lire.py à + 0 min 2,366 Go/s ; `troncons disque` F20 2,032 et 2,100 ; B20 2,438 et 2,566 ; A20
1,814 puis **0,439** (un arrêt de 21 s, le premier vu sur A20 : la séance p2b-Fb ne sert donc pas à un
verdict, son e_soi(A20) vaut 122 %). Lu en entier, F20 2,070 et 2,101 contre A20 1,824 et 1,820.

**À + 2 h 08** (A F B B F A A F B B F A, aucune passe sous charge) :

| fichier | Go/s | médiane |
|---|---|---|
| A20 | 1,786 ; 1,758 ; 1,774 ; 1,800 | 1,780 |
| F20 | 1,831 ; 1,827 ; 1,832 ; 1,863 | 1,831 |
| B20 | 2,350 ; 2,250 ; 2,468 ; 2,459 | 2,405 |

e_soi(B20) = 9,2 % ; S = 18,3 %. **F20 / A20 = 1,029 : égaux** (sous S / 2) ; F20 / B20 = 0,762 : ils
diffèrent. **L'amendement du § 2.5 tranche** : écrit comme le codeur (tamponné, 8 Mio, 30 Mo/s, fichier qui
croît), le contenu de A20 retombe en deux heures au débit de A20, comme D20 écrit d'une traite. ~~**La
manière d'écrire n'est pas la cause** de la rapidité des fichiers du 17 ; elle tient à un état du disque
de ce jour-là, que je ne sais pas reproduire.~~ [juge, `genome/JUGEMENT-placement.md` G1 : F20 gardait le motif de lecture v1.0, qui est
lent une fois les données repliées ; la rapidité des fichiers v1.2 vient ~~de la longueur de leurs requêtes (11,6 Mo
contre 12,0)~~ du motif de leurs requêtes (J10, J11 : pas de la longueur seule) ; R20, écrit le 22, est rapide cinq jours après.]

### 4.4 La profondeur de file (H7 ; séances p4, 10 h 22, et p5, 10 h 35 à 10 h 41) [mes.]

Le portable est revenu sur secteur à 10 h 07 ; aucune passe sous charge. `troncons disque --profondeur q`,
`analyse_qd.py` → `p4/analyse-qd.json`, `p5/analyse-qd.json`.

| | q = 1 | q = 2 | q = 4 (défaut) | q = 8 | q = 16 |
|---|---|---|---|---|---|
| A20, p4 (2 passes) | | 1,983 ; 2,003 | 1,798 ; 1,746 | 1,701 ; 1,693 | 1,693 ; 1,719 |
| B20, p4 | | 2,954 ; 2,983 | 2,716 ; 2,525 | 2,444 ; 2,386 | 2,467 ; 2,377 |
| A20, p5 (4 passes) | 1,895 ; 1,897 ; 1,815 ; 1,876 | 1,946 ; 1,964 ; 1,985 ; 1,971 | 1,821 ; 1,842 ; 1,824 ; 1,767 | | |
| B20, p5 | 2,739 ; 2,722 ; 2,768 ; 2,741 | 3,026 ; 2,978 ; 2,929 ; 2,981 | 2,621 ; 2,573 ; 2,668 ; 2,546 | | |

- **La prédiction déclarée tient** : plus de profondeur ne cache rien ; q = 8 / q = 4 = 0,958 (A20) et
  0,921 (B20), q = 16 de même. La lenteur de A20 n'est pas une latence que la file masquerait.
- **Moins de profondeur va plus vite**, ce qui n'était pas prédit : q = 2 / q = 4 = **1,125 et 1,080** sur
  A20 (p4, p5), **1,133 et 1,147** sur B20 ; q = 1 est entre les deux (A20 1,035, B20 1,055). Reproduit
  dans deux séances, de même signe sur les deux fichiers.
- **Au seuil déclaré, le levier n'est pas retenu** : la règle (§ 2.6) exige sur A20 un gain supérieur à
  S (14,6 % en p4, 11,8 % en p5) ; A20 donne 12,5 % puis 8,0 % (« entre deux »). Sur B20 seul, p5 passe le
  seuil (14,7 % > 11,8 %), mais la règle portait sur A20.
- **La mesure de bout en bout (p6) n'est pas lancée**, ~~tuée par les nombres~~ : à l'étage disque, q = 2
  rendrait au moteur du 20b, qui passe 17,2 s de ses 27,2 s de génération à lire, au plus
  27,2 / (27,2 − 17,2 × (1 − 1/1,08)) = **1,05** sur A20 et ≈ 1,09 sur un fichier comme B20 [calc.] :
  sous S = 11,8 %, ~~une série ABBA de huit passes ne peut pas le trancher~~ [juge, `genome/JUGEMENT-placement.md` M2 : au
  plancher de 11,8 % non ; avec un seuil tiré du bruit de bout en bout (0,8 à 4,6 %), oui : p6 est sous-puissante,
  pas tuée]. [hyp.] Le pilote iaStor ou le
  disque servent mieux deux grosses requêtes que quatre (moins de mélange entre les 12 Mo de deux tronçons) ;
  à confirmer par une série plus longue sur un fichier de type B, ou par des requêtes de 24 Mo à q = 2.

### 4.6 L'hypothèse de relais, après le retrim : elle tombe (séances p7 et p7-2, 2026-10-27) [mes.]

**Repos** (`journaux/repos-retrim.log`) : retrim de Stone fini le 26 à 23 h 46 min 44 s ; amendement déclaré à
23 h 49 (commit bcae307) ; aucune écriture de ma part avant 0 h 47 ; le juge a lu (séances jbis, j10).

**p7** (0 h 47 à 1 h 08) : G20a puis G20b, copies de A20 écrites comme le codeur, l'une après l'autre :
G20a 143 extents, écrite sur 99,3 Go libres ; G20b 117 extents, sur 88,2 Go libres ; **SHA-256 des deux
égaux à e8bd6ae1…169f**. Les 16 passes fraîches sont toutes **sous charge** (flux « mimétisme » et juges des
pistes, 0,3 à 1,3 cœur chacun, sans lecture du disque) : elles ne concluent pas (B20 lui-même y rend 2,36
puis 1,79).

**p7-2** (3 h 06 à 3 h 13, **2 h 06 après la fin de G20b**, 2 h 12 après G20a ; créneau calme réservé par la
session relais ; **aucune passe sous charge**, secteur à chaque passe), A Ga Gb B B Gb Ga A, deux tours :

| fichier | Go/s (4 passes) | médiane |
|---|---|---|
| A20 | 1,764 ; 1,759 ; 1,709 ; **0,437** (arrêt de 21 s) | 1,734 |
| G20a | 1,772 ; 1,783 ; 1,777 ; 1,779 | 1,778 |
| G20b | 1,785 ; 1,787 ; 1,756 ; 1,770 | 1,778 |
| B20 | 2,530 ; 2,532 ; 2,482 ; 2,482 | 2,506 |

Profils complets : G20a 1,788, G20b 1,786 Go/s. **Témoin** : G20b / G20a = 0,9998 (≤ S) : la séance juge.
**Cassure** de lire.py (décalage faussé) : 0 lecture égale sur 16 (16 sur 16 sans cassure).

**Le seuil, au sens littéral** : la dernière passe de A20 tombe dans un arrêt (0,437) ; e_soi(A20) vaut alors
93,7 % et S = max(2 × 93,7 %, 18,3 %) = 187 %, un seuil sans pouvoir pour « tient ». Sans cette passe (vue
indicative, non déclarée), e_soi(A20) = 3,1 %, le plus grand des autres 2,0 % (B20), et S = 18,3 % (plancher
déclaré). **Les deux lectures donnent le même verdict** : G20a / A20 = **1,025**, G20b / A20 = **1,025**, sous
S / 2 : **l'hypothèse tombe** ; G20a / B20 = G20b / B20 = **0,709**. La prédiction écrite avant (elle tombe)
tient. p8 (bout en bout) n'est pas due.

**Ce que ce test juge, à la lumière du juge** (`genome/JUGEMENT-placement.md` G1, § 5.6, § 7.3) : G20a et G20b
n'ont été lues qu'au motif de lecture v1.0 (requêtes de ~12,0 Mo), que le juge a trouvé lent quel que soit le
fichier. Le test départage quand même dans un sens : l'hypothèse de relais prédit une copie post-retrim
rapide **sous toutes les longueurs de requête** (§ 7.3 du jugement) ; lente au motif v1.0 à + 2 h, elle la
contredit. Il ne mesure pas, en revanche, la copie au motif v1.2 ni en requêtes raccourcies (G20a et G20b
étaient effacées quand j'ai lu le jugement) : c'est le geste qui manque pour l'écrire aussi dans l'autre
sens. Le retrim du 26 est la version faible du geste (94 Go libres, sans libération de 150 Go d'un coup).
G20a et G20b effacés à 3 h 15 ; le dossier `essais/troncons/placement/` est retiré.

## 5. P3 : le levier « réécrire d'une traite », mesuré de bout en bout [mes.]

Séance p3 (2026-10-22, 5 h 58 à 6 h 14, 3 h 17 à 3 h 33 après l'écriture de D20, machine calme, aucune
passe sous charge) : `troncons mesurer --modele <A20 | D20> --invite invite-wiki-3000.txt -n 256 --repos 10`
(configuration par défaut du moteur : 362 emplacements, profondeur 4), A D D A A D D A. Journaux
`mesures/disque/placement/p3/`.

| passe | 1 A | 2 D | 3 D | 4 A | 5 A | 6 D | 7 D | 8 A |
|---|---|---|---|---|---|---|---|---|
| jetons/s (génération) | 9,377 | 9,390 | 9,056 | 9,383 | 9,486 | 9,456 | 9,406 | 9,221 |
| s de lectures du moteur (255 pas) | 17,38 | 17,19 | 17,54 | 17,25 | 17,20 | 17,11 | 17,12 | 17,43 |

- **mêmes 256 jetons dans les huit passes** (empreinte du texte 1b14e44a6a10…, identique) ;
- **octets lus par jeton identiques** : 29 684 199 424 octets de tronçons pour 255 pas, 2 472 défauts,
  dans chaque passe (même contenu, même routage, même cache) ; les logits sont ceux d'un fichier égal au
  bit (SHA-256 vérifié, § 4.1) ;
- médianes **A20 9,380, D20 9,398 jetons/s : rapport 1,002**, e_soi 2,8 % et 4,3 % : **aucun gain**.

Le moteur, sur le 20b, passe 17,2 s de ses 27,2 s de génération à lire (1,73 Go/s vus par lui) : il est
lié au disque, et un disque 1,42 fois plus rapide (le débit de B20) lui rendrait, à calcul égal,
27,2 / (27,2 − 17,2 × (1 − 1/1,42)) = **1,23 fois plus de jetons par seconde** [calc.]. C'est ce
qu'il y aurait à gagner ; la réécriture d'une traite ne le donne pas, parce que le neuf retombe au débit
du vieux en moins de deux heures (§ 4.2).

## 6. Ce qui explique le débit, et ce qui s'exploite

**Ce qui fait le débit d'un fichier sur ce NVMe**, dans l'ordre de ce qui pèse :

1. ~~**L'état physique des données dans le disque, qui dépend de quand et comment elles ont été écrites**
   [mes.]~~ [juge, `genome/JUGEMENT-placement.md` G1 : **~~la longueur~~ le motif des requêtes de lecture que le format impose** (~12,0 Mo en v1.0 :
   lentes ; ~11,6 Mo en v1.2, 8,3 Mo en compagnon rapide : rapides ; mais deux requêtes de 6 Mo par tronçon v1.0 sont lentes
   aussi, J10, J11), une fois les données repliées ; le frais va vite quel que soit le motif]. À contenu égal au bit : A20 (15 oct.) 1,76-1,85 Go/s ; D20 (réécrit aujourd'hui) 2,35 à + 1 min,
   2,18 à + 3 min, **1,78 à + 2 h** ; ~~C120 non coupé (17 oct.) va plus vite que B120 ; B20 et B120 (17 oct.)
   restent à 2,4-2,6 cinq jours après~~ [juge, G2 : C120 non coupé = A120 (0,980)]. ~~Ni le format (3,3 % d'octets)~~
   [juge : le format agit par ~~ses longueurs~~ le motif de ses lectures, pas par ses octets], ni le contenu (chiffré par
   BitLocker, donc aléatoire pour le disque), ni la position logique, ni l'ordre de lecture, ni la
   température, ni le cache de Windows ne l'expliquent (§ 3, § 4). Le mécanisme interne n'est pas
   observable d'ici ; [hyp.] le passage des données de l'antémémoire SLC à la TLC et ce que la FTL fait
   des blocs ensuite.
2. **La fragmentation NTFS, quand elle est extrême** [mes.] : C120 (267 473 extents, médiane 8 Kio) ~~perd
   un facteur 5,7 sur ses lectures coupées en 10 morceaux ou plus ; le modèle t(n) = 17,0 ms + (n − 1) ×
   0,37 ms rend son débit à 1 % près~~ [juge, `genome/JUGEMENT-placement.md` G3 : au chemin du moteur, × 1,26 en tout (C120 tiré 1,378
   contre ses tronçons non coupés seuls 1,731 Go/s), t₁ = 34 ms, τ = 9 à 11 µs]. En dessous de quelques centaines d'extents (A, B, D, F : 5 à 233), elle
   ne compte pour rien (1,009 à 1,06 morceau par lecture).
3. **Des arrêts du disque pendant les longues lectures de A120** [mes.] : plages de 15 à 25 s à 0,2-0,37
   Go/s, liées au temps et non à la région (ρ entre passes 0,012), sans transition thermique. Non vus
   ailleurs. [hyp.] travail de fond du contrôleur sur de vieilles données.

**Tué par les nombres** : H2 position LCN (ρ = 0,009 dans A120, bandes 1,006 et 0,979) ; H4 ordre (trié /
aléatoire 1,028 sur B120) ; H5 (a) cache de Windows (le disque lit 1,0000-1,0057 fois les octets
demandés) ; H6 thermique (écart 1,42 gardé à ± 2 °C, aucun TMT) ; H6 âge seul (A à 6,7 h plus lent que B à
110 h) ; H1 pour A contre B (A 1,009 morceau par lecture, B 1,051) ; « réécrire d'une traite répare »
(D20 retombe à A20 en 2 h ; bout en bout 1,002).

~~**Le levier qui tient**~~ **Un levier prédit, non mesuré** [juge, `genome/JUGEMENT-placement.md` M5] **: la défragmentation logique par réécriture contiguë**, pour les fichiers morcelés
comme C120. `carte.py projeter` la diagnostique (morceaux par lecture, lectures coupées) ; `placer.py
copier --mode traite` la répare (taille réservée : 5 extents pour 11,2 Go ; empreinte vérifiée). Gain
prédit sur C120 : ~~**1,24 → 1,78 Go/s, × 1,43**~~ **× 1,26** au chemin du moteur [juge, `genome/JUGEMENT-placement.md` G3 : le 1,24 est
celui de `lire.py` ; le moteur lit C120 à 1,33-1,38 et ses tronçons non coupés à 1,73] [calc., note pour le mémoire § 1.3], non mesuré sur le 120b
(copie interdite). Il ne rend rien sur un fichier déjà contigu (p3 : 1,002).

**Ce qui ne s'exploite pas encore** : l'écart de 1,4 entre les fichiers du 17 et les autres. Il vaut
1,23 fois plus de jetons par seconde au moteur sur le 20b [calc.] et 1,45 sur le 120b (06 § 8), mais je ne
sais pas le produire à la demande : D20, écrit d'une traite, retombe ; F20, écrit comme le codeur,
retombe aussi (§ 4.5). ~~Aucun levier de l'écriture ne le donne sur cette machine aujourd'hui.~~ [juge, `genome/JUGEMENT-placement.md` :
~~le levier est dans la lecture : des requêtes plus courtes que ~11,7 Mo rendent au v1.0 la vitesse du v1.2 à
l'étage disque (§ 5.6 et 5.7 du jugement), sans rien réécrire ; non mesuré de bout en bout.~~ la cause est dans le motif
de lecture du v1.0 ; couper ses requêtes en deux ne la répare pas (× 0,85 à 0,88, J10, J11) ; recoder en v1.2 la répare
(× 1,38 à l'étage disque, × 1,44 de bout en bout au J1 du lot A).]

**Conséquence pour les autres mesures du projet** (à dire aux lots) : toute comparaison de vitesse entre
deux fichiers `.trc` écrits à des jours ou de manières différentes mesure d'abord leur état sur le disque.
Le lot A l'a vu (06 § 8 : « le gain suit le fichier ») ; la séance de vitesse s2-120b du lot B (exact =
A120, ~~1,87-1,88 j/s~~ 1,981 j/s en médiane de 2,080, 1,870, 2,117, 1,882, contre son compagnon écrit plus tard, 3,97 j/s) et la séance du juge (A120 ~~1,78 et
2,01~~ 2,004 en médiane de 1,995, 1,785, 2,013, 2,019, contre v1.2 2,89) le portent aussi [juge, `genome/JUGEMENT-placement.md` M3 : valeurs basses citées au lieu
des médianes ; et l'écart suit le motif de lecture, G1]. Règle proposée : **avant toute comparaison, `troncons disque` sur
chaque fichier (10 s) ; si leurs débits diffèrent de plus de S, l'écart de vitesse n'est pas attribuable
au contenu**.

## 9. Ce qui pourrait être faux

- L'identification du disque au PM9C1a (sans DRAM, mémoire tampon de l'hôte) est probable, pas prouvée
  (`fondations/01-machine.md` § 2.5) ; BitLocker est actif et le pilote est Intel RST VMD : tout ce qui
  est mesuré l'est à travers fvevol et iaStor.
- Les extents NTFS sont ceux du volume ; la correspondance LCN → LBA est linéaire sous BitLocker, mais
  LBA → page physique est cachée par la FTL : aucune mesure ici ne voit la puce. Toute explication
  physique (SLC, réessais, rafraîchissement) est une hypothèse.
- La descente de D20 n'a que trois points (+ 1 min, + 3 min, + 2 h 14) ; elle peut être plus rapide ou
  avoir un palier. Elle a eu lieu pendant que d'autres flux travaillaient (le juge a lu le disque entre
  3 h 56 et 5 h 54) : « retomber » peut dépendre de l'activité du disque, pas seulement du temps.
- Les arrêts de A120 n'ont été vus que dans deux passes complètes ; leur cause et leur fréquence pendant le
  J1 ne sont pas mesurées (les passes J1 du lot A sur A120 ont un σ de 5,6 %, ce qui les borne dans ces
  conditions-là).
- Le gain de la défragmentation logique sur C120 est calculé, pas mesuré, et suppose que C120 réécrit
  retomberait au niveau de A20 réécrit.
- Les fichiers du 17 sont peut-être rapides pour une raison liée à ce jour-là (état du disque, place
  libre, activité des autres flux) ; sans F2 concluant, je ne peux pas la nommer.
- `lire.py` va 2 à 4 % moins vite que `troncons disque` (témoin) ; ses profils comparent des fichiers entre
  eux dans une même passe, ce qui annule ce biais, mais ses débits absolus sont un peu bas.

## 10. Recettes (pour RECETTES.md)

- **FSCTL_GET_RETRIEVAL_POINTERS par ctypes** donne la carte complète d'un fichier en moins d'une seconde,
  même pour 267 473 extents, sans droit d'administrateur ; `fsutil file queryextents` avait mis plus de
  30 min sans finir (lot A). À garder.
- **Le journal SMART du NVMe est lisible sans administrateur** (IOCTL_STORAGE_QUERY_PROPERTY,
  StorageDeviceProtocolSpecificProperty, page 02h, sur PhysicalDrive0 ouvert sans droit d'accès) :
  température, unités lues et écrites, transitions thermiques. Témoin gratuit des octets réellement lus
  et de l'activité d'écriture des autres pendant une passe. À mettre dans tous les bancs.
- **Comparer deux fichiers par leur vitesse sans relever leur état sur le disque est une erreur** : même
  contenu, 1,0 à 1,6 fois d'écart. Relever `troncons disque` par fichier avant toute séance de vitesse.
- **Le débit d'un fichier frais n'est pas son débit** : relire au moins 2 h après l'écriture.
- **Lire un fichier entier, pas seulement un échantillon** : les 1 500 tronçons de la phase disque
  cachaient les arrêts de A120 (1,74 contre 0,85-1,15 en entier).
- **Réserver la taille avant d'écrire** (FileAllocationInfo) : 5 extents pour 11,2 Go dans un volume à
  90 % plein, contre 95 pour la même copie écrite en croissant.
- **Défragmenter un fichier morcelé par réécriture** : prédit × 1,43 sur C120 ; essayé « réécrire un
  fichier déjà contigu » : rien (1,002 de bout en bout).
- Essayé et sans effet : trier les lectures par décalage (1,028), choisir la position (ρ ≈ 0).

## 11. Réponses par délégation de ce document

- **E20 (écriture entrelacée) abandonnée au profit de F20 (écriture comme le codeur)** : réponse par
  délégation du 2026-10-22, réversible. Justification : D20 retombé, le test de E20 n'avait plus d'objet,
  et la place temporaire (12 Go) ne permet qu'une copie à la fois.
- **Tester la profondeur de file (H7)** en plus du plan : réponse par délégation du 2026-10-22, réversible.
  Justification : c'est le seul levier du moteur (`--profondeur`) qui pourrait cacher une lecture lente.
- **Ne pas défragmenter le 120b** : la consigne l'interdit (aucune copie du 120b, aucune défragmentation
  système) ; la commande est écrite au § 12 pour Stone.

## 12. Ce qui reste

- ~~**F2, le test qui reste décisif**~~ : fait (§ 4.5), F20 retombe ; l'écart des fichiers du 17 reste
  inexpliqué. Ce qui le chercherait : relever chaque jour `troncons disque` et SMART sur A20, B20 et un
  fichier neuf, pour voir si B20 retombe un jour, et à quelle date.
- Hypothèse de relais : tuée au § 4.6 au motif v1.0 ; la relire, si Stone refait le geste fort (150 Go libérés
  d'un coup, retrim, repos), avec les deux motifs (v1.0 et v1.2 ou raccourci), selon § 7.4 du jugement.
- H7 : q = 2 donne + 8 à + 15 % à l'étage disque (§ 4.4), sous le seuil sur A20 ; une série de bout en
  bout plus longue (16 passes ou plus) sur un fichier de type B dirait si `--profondeur 2` vaut d'être le défaut.
- **Pour Stone, la défragmentation logique de C120** (le v1.0 recodé, 267 473 extents ; fichier du lot A) :
  il faut ≈ 57,7 Go de place pour la copie, plus 45 Go de marge, soit ≈ 103 Go libres :
  `python -I -X utf8 outils/disque/placement/placer.py copier ~/dev/modeles/trc/temoin-codon/gpt-oss-120b-v10-recode.trc ~/dev/essais/troncons/placement/C120-contigu.trc --mode traite --plafond-go 60`,
  puis `placer.py empreinte <copie> --attendu 6c7b5f1d09429ecf4339a206ca86da9ccb5d1f1b7b15c6d354b0a0409720dcce`,
  puis, deux heures plus tard, `troncons disque` en ABBA sur C120 et C120-contigu (prédit : 1,24 → 1,78).
  Le lot A peut aussi simplement effacer C120, qui ne sert plus de témoin.
- Les arrêts de A120 : les chercher pendant un J1 (débit par seconde du moteur), et voir si A120 récrit
  (≈ 103 Go libres, même commande) les perd.
- Comprendre pourquoi les fichiers du 17 restent rapides : relever SMART et débit chaque jour sur A, B, F
  (si F reste rapide) ; c'est le seul gain de 1,4 qui reste sur la table.
- Juge indépendant de ce document (SOCLE, « la barre »).
