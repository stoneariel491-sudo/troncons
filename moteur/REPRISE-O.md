# Reprise du lot O (cache, ordonnanceur, modèle, programme, espace de travail)

## 2026-10-15, étape O1 : FINIE

- Fait : `moteur/Cargo.toml` (espace de travail, membres par motif `crates/*`, `bins/*`, couture D
  aux versions exactes du cache cargo), `moteur/Cargo.lock`, `moteur/crates/trc-cache` (cache à deux
  étages, `Lru`, `Belady`, `lire_trace`, `rejouer`, binaire `rejouer`), `moteur/bins/troncons`
  (squelette ; generer/evaluer/mesurer rendent « pas encore construit »).
- Témoin O1 : TIENT, 508 comparaisons à l'unité, 0 écart (étude 04 par couche, global gpt-oss, deux
  étages, 12 traces réelles de 20b et taux publiés). Cassure (politique faussée) : TOMBE, 390 écarts.
  Journaux : `mesures/moteur/O/journaux/temoin-o1.json`, `temoin-o1-casse.json`,
  `temoin-o1-passe1-belady-faux.json` (passe 1, Belady faux, gardée).
- Témoins unitaires : 13 (`cargo test -p trc-cache`) ; 9 cassures, toutes tombent
  (`mesures/moteur/O/journaux/tests-casses.txt`, outil `casser_tests.py`).
- Courbes : `mesures/moteur/O/csv/succes-20b-rejouer.csv`, `falaise-20b-dense.csv`.
- Mémoire : `moteur/O-pour-le-memoire.md` (3 lemmes démontrés), `memoire/sources/moteur-O.bib`.

## 2026-10-15, étapes O2 et O3 : critères déclarés avant leur lancement (22 h 10, heure locale)

Construit (commits a3b69fe, 3b25c00) : `trc-modele` (gpt-oss sur la carte), `trc-ordo` (le moteur J1,
à la demande), `troncons generer|evaluer|mesurer`. Premier essai (20b, 5 jetons d'invite, 16
produits) : « Paris. » ; mode témoin 546 experts sur 546 égaux à l'empreinte du répertoire.

### Témoin O2 (la passe avant de trc-modele, contre la chaîne du lot K)
- Outil `mesures/moteur/O/temoin-o2/` (hors de l'espace du moteur, comme `temoin-k3`), 20b, les
  160 premiers jetons de la fenêtre 0 de `processeur-bis.kld` (ceux du lot K), référence f64
  (`Reference::evaluer`, même GGUF) refaite dans l'outil.
- Chemin **T** : le moteur entier (`trc-ordo`, fichier codé, jeton par jeton, cache et décodeur de
  la carte). Chemin **G** : `trc-modele` seul, experts tirés du GGUF d'origine et posés en
  emplacement SoA par l'hôte (sans `trc-ordo` ni décodeur), sur les 16 premières positions.
- Mesure : par position, KL(référence ‖ chemin) par la formule de `chaine.rs`, premier choix de la
  référence et du chemin, écart relatif des logits ; écrits en `{:e}` (plus courte écriture exacte
  d'un f64).
- **Seuil : égalité exacte, ligne pour ligne**, avec `mesures/moteur/K/k3/k3-chaine-gptoss20b.csv`
  (160 lignes pour T, 16 pour G), et KL moyenne de T égale à 7.2794050122285915e-3 (journal K).
  Raison : mêmes noyaux, mêmes entrées, même ordre (règle de déterminisme, § 5.6) ⇒ logits égaux
  au bit ⇒ mêmes chiffres. L'ordre couche par couche de K et l'ordre jeton par jeton du moteur ne
  diffèrent que par l'ordre des lancements, pas par leurs entrées (attention causale, anneau).
- Cassures (chacune doit faire différer au moins une ligne) : T `--casser position` (le moteur reçoit
  la position p + 1 : faute d'un décalage de position) ; G `--casser experts` (à la couche 5, les
  emplacements des experts 0 et 1 échangés : faute d'appariement experts / poids).

### O3 (le moteur sur gpt-oss-20b, M = 0) : C3, C4 et le compte du cache
- **C3** : `troncons evaluer` sur les 10 fenêtres de 512 jetons de `ref-openai-20b.kld` (5 120
  pas), une fois sur `gpt-oss-20b.trc` (codé), une fois sur `gpt-oss-20b-brut.trc` (brut, même
  moteur, `copier_brut` au lieu du décodeur). Seuil : **0 pas différent** : l'empreinte64 des
  logits f32 de chacun des 5 120 pas égale entre les deux (CSV), et les deux `.kld` égaux octet
  pour octet (second chemin). Cassure : la copie corrompue du lot E (`gpt-oss-20b-casse-E2.trc`, 12
  bits retournés, `casser-copie.json`) : en production, une erreur fatale nommée ou des logits
  différents ; en mode témoin, l'empreinte de l'expert touché tombe.
- **C4** : `juge comparer --verite ref-openai-20b.kld --a troncons-20b.kld --b carte_cmoe.kld`
  (outil du lot R) ; seuil littéral du § 7.1 : KL moyenne de troncons ≤ celle de llama.cpp carte et
  premier choix de troncons ≥ (intervalles de Wilson) ; le verdict statistique du lot R est publié
  à côté, sans le remplacer.
- **Compte du cache** : le moteur écrit sa trace (`--trace`) ; `rejouer --trace … --emplacements N`
  (même N, même politique) doit rendre les mêmes succès, défauts et évictions **à l'unité**.
  Cassure : `rejouer --casser` (LRU faussé) : écart.
- Sur secteur (noté), carte libre (nvidia-smi : aucun llama-*) ; le verrou de la carte pour les
  passes longues de C3.

### O4 = J1 (gpt-oss-120b) : critères du § 7.1, déclarés le 2026-10-15 à 22 h 30, avant toute passe 120b
- Séance `pilote_o4.py` : six processus neufs, A120 D Y20 Y20 D A120 (A120 : `troncons mesurer`
  120b, invite wikitext de 06 § 7.2 (SHA-256 eadbe87e…eff), 256 jetons gloutons, mode A0 ; D :
  `troncons disque`, 1 500 tronçons tirés, mêmes longueurs, profondeur 4 ; Y20 : la même mesure sur
  le 20b). Secteur et absence de llama-* vérifiés avant chaque passe ; verrou toute la séance.
- **C5** : pour chaque A120, jetons/s de la génération ≥ 0,8 × le plancher en série recalculé avec
  les quantités de la même séance : t_disque = octets de tronçons lus par jeton (compteur du moteur,
  génération) ÷ débit de D (médiane des deux D) ; t_pcie et t_dec = temps de carte des copies et des
  décodages par jeton (événements du moteur) ; t_gemv = (A + R)/235 Go/s (A = résidents lus par
  jeton, R = k · L emplacements ; 235 : K2 [mes. K, autre séance]) ; T0 = 3,5 ms (07 § 1.1).
  série = 1 / (t_disque + t_pcie + t_dec + t_gemv + T0). 0,8 = 1 − 2 × 10 % (§ 7.1).
- **C7** : ensemble de travail de pointe (`PeakWorkingSetSize`, mémoire épinglée comprise) des A120
  ≤ **1,9 Go** ; |médiane(A120) − médiane(Y20)| ≤ 2 × bruit + 0,5 Mo, bruit = le plus grand écart
  entre les deux passes d'un même modèle.
- **C8** : |octets PDH − octets lus par le moteur (résidents, lignes, tronçons)| ≤ repos × durée +
  100 Mo (repos : débit de repos du disque mesuré 10 s avant la passe).
- **C10** : VRAM de pointe (nvidia-smi, 250 ms) ≤ 8 188 − 909 = 7 279 Mio.
- **C3, C11, C12 sur le 120b** : même protocole que sur le 20b (évaluation des 10 fenêtres codé
  contre brut, empreintes des 5 120 pas ; PPL égale ; 256 jetons du texte égaux), avec
  `gpt-oss-120b-brut.trc` codé par `trc-codeur coder --brut` (outil du lot F, ≈ 63 Go).
- **C4 sur le 120b** : le `.kld` de troncons est écrit ; le jugement attend la référence f64 du 120b
  et la base llama.cpp du 120b (lot R, « reste »). Non jugé par le lot O.
- Publié, non jugé : un texte au format harmony de gpt-oss produit par le 120b (§ 8, point 6).

### Résultats O2 et O3 (2026-10-15, 22 h 10 à 22 h 35, secteur, carte libre, verrou du lot O pour C3)
- **O2 TIENT** (`journaux/o2/temoin-o2-gptoss20b.*`) : chemin T (moteur entier, `.trc` codé) **160
  lignes sur 160 égales** à la chaîne K3, KL moyenne 7.2794050122285915e-3 = K3 au chiffre près ;
  chemin G (trc-modele seul, experts du GGUF) 16 sur 16. Cassures : `position` 0/160, `experts`
  0/16 : tombent. Conséquence : la passe avant du moteur est, au bit, celle que K a validée.
- **C3 TIENT sur 20b** (`journaux/o3/o3-2026-10-15-s1-*`) : 5 120 pas, **0 empreinte de logits
  différente** codé contre brut ; `.kld` égaux octet pour octet ; **C11** : PPL des positions
  notées 461,978277060145 des deux côtés. Les deux passes n'avaient pas le même nombre
  d'emplacements (362 contre 361 : tampons d'arrivée du brut plus grands) : le cache n'entre pas
  dans le calcul, comme attendu.
- **Compte du cache = rejouer à l'unité** : 454 210 succès VRAM, 37 310 défauts, 36 948 évictions
  des deux côtés (h = 0,924 sur 20b, 362 emplacements) ; cassure (LRU faussé) : 427 984 / 63 536.
- **Cassures de C3** : copie du lot E (12 bits) : erreur fatale nommée « couche 2, expert 19 : 32
  voies hors de L, 1 pointeur de tuile faux » en production, empreinte nommée en témoin ; médiane
  faussée (`casser_mediane.py`, couche 0, expert 30, ligne 100, 121 → 122 ; invisible au décodeur) :
  la production ne s'arrête pas mais **64 pas sur 64** ont des logits différents, le témoin nomme
  l'expert. Copie : `~/dev/modeles/trc/casse/gpt-oss-20b-casse-O3.trc` (11,2 Go, à
  libérer quand Stone le veut).
- **C4 TIENT sur 20b** (`journaux/o3/c4-20b-comparer.*`, `juge comparer` du lot R, A = llama.cpp
  carte_cmoe, B = troncons) : KL(réf ‖ troncons) **0,003679 ± 0,00046** contre 0,022606 ± 0,0017
  pour llama.cpp ; premier choix **97,18 %** [96,46 ; 97,75] contre 89,61 % [88,36 ; 90,73] ; les
  quatre verdicts (littéraux et statistiques) tiennent. troncons est six fois plus près de la
  vérité f64 que llama.cpp (dont la rampe de YaRN de llama.cpp : 0,0145 des 0,0226, lot R ; ajout de
  la ronde de corrections, constat m5 de l'épreuve).
- Vitesse (informative, 20b) : 12,7 pas/s en évaluation.

### Résultats de la séance O4 `2026-10-15-s1` (22 h 40 à 23 h 03, secteur à chaque passe, aucun llama-*, VRAM 346 Mio avant chaque passe)
`journaux/o4/verdicts-2026-10-15-s1.json`, `csv/o4-2026-10-15-s1-passes.csv`.
- **C5 TIENT** : 120b, génération **2,186 et 2,182 jetons/s** (h = 0,591, 326 emplacements) ≥ seuil
  1,505 (plancher en série 1,881 : disque 382,7 ms à 1,848 Go/s médian de D, PCIe 75,8, décodage
  54,2, GEMV 15,3, T0 3,5). Le moteur dépasse même le plancher « en série » (les copies et décodages
  d'une couche recouvrent les lectures des autres défauts de la même couche). Préremplissage 1,64 j/s.
- **C7** : plafond **TIENT** (ensemble de travail de pointe 384,2 Mo ≤ 1,9 Go, cinq fois sous le
  plafond ; llama.cpp `fit` : 10,9 Go, mesures/gpt-oss.md) ; écart 120b − 20b **TOMBE** : 3,70 Mo
  contre la borne déclarée 0,66 Mo (bruit 82 Ko). Le terme de 0,5 Mo ne comptait que le répertoire ;
  le moteur tient d'autres structures qui croissent avec le modèle (1,28 Mo de fenêtre épinglée :
  12 tampons à la taille du plus grand tronçon, qui diffère d'un modèle à l'autre ; tables,
  répertoire en double, événements et contrôles par couche). La pointe est atteinte en fin de passe
  (fin 384,17 Mo) : ce n'est pas un transitoire. Diagnostic déclaré ci-dessous.
- **C8** : passes 1, 3, 4 TIENNENT ; **passe 6 TOMBE** de 54 Mo (écart 286 Mo, borne 233 Mo : repos
  du disque très bas avant cette passe) ; passe 1 : écart 2,39 Go sous une borne de 4,2 Go (repos
  7,5 Mo/s). Le moteur ne compte que ses lectures par `trc-es` ; les lectures tamponnées de
  l'ouverture (MÉTA, tables, répertoire : ≈ 15 Mo), le vocabulaire chargé par llama.dll (13 Mo) et
  les DLL ne sont pas comptées. Non corrigé (le seuil reste celui déclaré).
- **C10 TIENT** : VRAM de pointe 6 520 à 6 532 Mio ≤ 7 279.
- Les deux passes A120 ont la même trace et **le même texte** (déterminisme de bout en bout).
- **C6 (J1+), lu sur J1 sans préchargement** : 2,184 j/s contre la meilleure base llama.cpp mesurée
  sur le même texte et les mêmes 256 jetons, `fit` 0,568 j/s (0,50 – 0,63, bruit 9,5 %,
  mesures/gpt-oss.md) : ~~× 3,85~~, au-delà de 2 × 9,5 % + 3 % (barré par la ronde de corrections : la
  base était sous-réglée ; meilleure base mesurée `fit -t 16`, 0,884 j/s : × 2,22, C6 tient encore). Le préremplissage de llama.cpp (par lots,
  3,63 j/s) reste au-dessus du nôtre (1,64 : boucle de pas, § 5.8).

### C3, C11 et compte du cache sur le 120b (2026-10-15 23 h 03 à 00 h 53, secteur au début et à la fin, verrou du lot O)
`journaux/o3/o3-120b-2026-10-15-s1-*`. **C3 TIENT** : 5 120 pas, **0 empreinte de logits
différente** codé contre brut ; `.kld` égaux octet pour octet (SHA-256 5b212fe9…bcd7be des deux
côtés). **C11 TIENT** : PPL des positions notées 422,20558522791305 des deux côtés. Compte du cache
= `rejouer` à l'unité (334 608 succès, 402 672 défauts, 402 346 évictions ; 326 emplacements,
h = 0,454) ; cassure : 289 788 / 447 492. 1,54 pas/s en évaluation (codé), 1,58 (brut, 325
emplacements). Le `.kld` du 120b attend la référence f64 du 120b pour C4 :
`~/dev/essais/troncons/lot-O/o3-120b-2026-10-15-s1-code.kld`.

### Diagnostic C7 et variante L12, déclarés le 2026-10-15 à 23 h 15, avant leur mesure
- **D-C7** : l'ensemble de travail relevé après chaque étape de l'ouverture (`etapes_memoire` du
  journal : fichier, contexte, noyaux, modèle, LUT, fenêtre, emplacements et cache) et en fin de
  passe, 120b et 20b, série A120 Y20 Y20 A120, `generer` 1 jeton. Publié : la part de chaque étape
  dans l'écart ; aucun seuil (diagnostic).
- **L12** (proposition du lot E, point de l'arbitre « longueur des lectures ») : chaque tronçon lu en
  une requête de 12 Mio (12 582 912 o ≥ plus grand tronçon, 12 251 136 o sur le 120b) au lieu de
  `longueur0` ; les octets en plus ne sont ni copiés ni décodés. Série A B B A sur le 120b
  (A : J1 tel quel ; B : `--longueur-lecture 12582912`), `mesurer`, même invite, 256 jetons.
  Prédiction : disque seul 1,85 → ≈ 2,8 Go/s (carte du lot E), génération ≈ 2,2 → ≈ 3,0 j/s.
  Seuil (règle de 06 § 7.5) : B vaut si sa génération dépasse A de plus de 2 × le plus grand
  bruit d'une paire et de 3 %. Témoins : le texte de B égal à celui de A (les logits ne dépendent pas
  de la lecture) ; C7-bis : avec des fenêtres de même taille (12 Mio pour les deux modèles), l'écart
  120b − 20b doit perdre le terme de la fenêtre (≈ 1,28 Mo).

### Résultats D-C7 et témoin F (seconde séance `2026-10-16-s2`, 00 h 54 à 00 h 58, secteur, verrou)
`journaux/j1plus/2026-10-16-s2-0[1-8]-dc7*`, `csv/o-memoire-etapes.csv`.
- **D-C7** (1 jeton, ensemble de travail en fin de passe ; 120b, 20b, 20b, 120b) : 381,02 / 380,98
  contre 377,81 / 377,59 Mo, écart **3,30 Mo**. Par étape (120b − 20b, moyennes des paires) :
  fenêtre et tampons épinglés **+2,10 Mo** ; modèle (471 allocations de résidents contre 314, table)
  **+0,37 Mo** ; emplacements, cache, événements **+0,22 Mo** ; LUT **+0,06 Mo** ; fichier ouvert
  0,00 ; contexte CUDA et noyaux : bruit de ± 1 Mo d'une passe à l'autre, pas un terme du modèle.
- **C7-bis** (fenêtres de même taille, `--longueur-lecture 12582912`) : 382,93 / 382,88 contre
  381,97 / 381,84 Mo : écart **0,99 Mo** (le terme de la fenêtre a disparu : 153,10 Mo des deux
  côtés), bruit 0,13 Mo, borne déclarée 2 × 0,13 + 0,5 = 0,76 Mo : **tombe encore de 0,23 Mo** ; ce
  qui reste est nommé ci-dessus (allocations des résidents, cache et événements par couche).
- **Témoin F TIENT** : `evaluer --flux` sur les 10 fenêtres du 20b : 5 120 empreintes égales ligne
  pour ligne à la boucle de pas, `.kld` égal octet pour octet ; en 1 min 55 s au lieu de 6 min 40 s.
  Cassure (médiane faussée) : 512 lignes sur 512 différentes.

### Résultats J1+ (séances `2026-10-16-s2` et `-s3`, 00 h 54 à 02 h 08, secteur à chaque passe, aucun llama-*, verrou du lot O)
`journaux/j1plus/pilote-2026-10-16-s2.json`, `pilote-2026-10-16-s3.json`, `csv/o-jetons-s.csv`.
Tous les textes des 120b de ces séances (15 passes, codé, brut, flux, L12, préchargement ; 17 avec la séance 1) ont la
même empreinte e4c6dbacb63a… que la séance 1 : le moteur est déterministe de bout en bout.
- **Disque plus lent qu'à la séance 1** : la passe A (J1 tel quel) fait 1,75 j/s (lectures 460 ms
  par jeton contre 363) puis 2,18 ; [hyp. : chauffe du NVMe après 3 h de lectures continues ; la
  température n'est pas lisible sans droits d'administrateur]. Les séries ABBA comparent dans la
  séance, jamais d'une séance à l'autre.
- **FLUX (préremplissage par flux) VAUT** : préremplissage des 708 jetons 1,46 et 1,65 j/s → **26,9
  et 27,4 j/s** (× 17,5 ; 26 s au lieu de 7 min 50 s), textes égaux. Au-dessus de llama.cpp (`fit`,
  par lots : 3,63 j/s) d'un facteur 7,5. Retenu.
- **L12 (lectures de 12 Mio), avec le flux des deux côtés** : génération A 2,179 et 2,182, B 2,613 et
  3,073 j/s : +30 % en médiane, chaque passe B au-dessus de chaque passe A, mais la dispersion de B
  (21 %) fait la règle de 06 § 7.5 (gain > 2 × bruit) **tomber** : non retenu tel que déclaré. À
  rejuger sur une série plus longue (6 passes) quand l'arbitre aura tranché la longueur des lectures.
- **PF (préchargement par le routeur de ℓ + 1) NE VAUT PAS : −11 %** (A 2,158 et 2,178 ; B 1,935 et
  1,924 ; bruit 1 %) : 69,2 % des lectures anticipées servent (11 529 sur 16 670), les autres
  ajoutent 34 % d'octets lus (953 Mo par jeton contre 710) sur un disque qui limite déjà ; le calcul
  qu'elles recouvrent (≈ 80 ms par jeton) vaut moins que ce qu'elles coûtent. Idée tuée par les
  nombres sur cette machine (disque chiffré à 1,8 Go/s) ; elle reviendrait avec un prédicteur
  plus juste ou un disque qui ne limite pas. Défaut trouvé en chemin et corrigé (achèvement de la
  couche en cours récolté pendant le vidage des préchargements, passe 21 de la séance 2).
- **C12 TIENT** : le texte de 256 jetons du 120b sur le fichier **brut** (`--brut --flux`) a la même
  empreinte que sur le fichier codé (e4c6dbacb63a…) ; texte : `journaux/o4/2026-10-15-s1-1-A120.txt`.
- **Conversation harmony du 120b, publiée** (§ 8, point 6) : 136 jetons d'invite, 1 024 produits
  (limite atteinte avant `<|return|>`), 1,46 j/s en génération, préremplissage par flux 6,9 j/s,
  mémoire de pointe 384 Mo, VRAM 6 537 Mio ; texte :
  `journaux/j1plus/2026-10-16-s3-06-harmonie.txt`. Défaut d'affichage : les caractères dont les
  octets UTF-8 sont coupés entre deux jetons sortent en « � », parce que `trc-jetons::texte` décode
  chaque jeton seul (`from_utf8_lossy`) ; besoin pour le lot R : une fonction qui rend les octets
  bruts d'un jeton (`Jetons::octets`), pour assembler le texte avant de le décoder. L'empreinte
  C12 n'en dépend pas (même transformation des deux côtés).
- **Configuration retenue pour le 120b** : J1 + préremplissage par flux.

### J1+ : préchargement, déclaré le 2026-10-15 à 23 h 25, avant sa première exécution
- Construit (non encore lancé) : `Config::prechargement` (`--prechargement`). Après l'attention
  de la couche ℓ, le moteur applique le routeur de ℓ + 1 (sa norme d'après attention, son
  `ffn_gate_inp`) au résidu courant (`Modele::predire`, tampons à part, seconde boîte aux
  lettres) et lit d'avance les tronçons prédits absents de la VRAM dans 2 · k tampons épinglés. Le
  cache n'en sait rien : un défaut de ℓ + 1 dont le tronçon est lu d'avance prend ce tampon comme
  source au lieu d'une lecture. Mode A0 seulement.
- Témoins (seuil : égalité) : le texte des 256 jetons égal à celui sans préchargement (les logits
  ne dépendent pas des lectures) ; le compte du cache égal à `rejouer` sur la trace (le
  préchargement ne touche pas le cache).
- Mesure : série A B B A sur le 120b, A = la meilleure configuration J1 de la série L12, B = la même
  plus `--prechargement` ; publiés : jetons/s, part des prédictions servies (pf_utiles / pf_emis),
  octets lus en plus. Seuil (06 § 7.5) : B vaut s'il bat A de plus de 2 × le plus grand bruit d'une
  paire et de 3 %. Prédiction : au plus +19 % (le temps de calcul hors disque, 457 − 383 ms, est ce
  que le recouvrement peut cacher) plus ce que la file plus profonde rend au disque.

### J1+ : préremplissage par flux, déclaré le 2026-10-15 à 23 h 40, avant sa première exécution
- Construit (`Moteur::preremplir`, `--flux`) : couche par couche, toutes les positions de l'invite
  passent l'attention et le routeur, puis chaque expert demandé est lu, copié, décodé une fois et
  appliqué à toutes les positions qui l'ont choisi, puis chaque position combine ses k sorties.
  C'est l'ordre de la chaîne K3 ; la proposition 5 le rend égal au bit à la boucle de pas.
- **Témoin F** (seuil : égalité) : `evaluer --flux` sur les 10 fenêtres du 20b codé : les 5 120
  empreintes de logits égales ligne pour ligne à celles de la passe en boucle de pas
  (`o3-2026-10-15-s1-code-empreintes.csv`), et le `.kld` égal octet pour octet. Cassure : la même
  évaluation par flux sur la copie à médiane faussée (`gpt-oss-20b-casse-O3.trc`) doit différer.
- **Mesure** : série A B B A sur le 120b (A : meilleure configuration retenue ; B : A + `--flux`),
  préremplissage des 708 jetons de l'invite ; publiés : jetons/s de préremplissage, texte (doit être
  égal), octets lus. Seuil (06 § 7.5) sur le préremplissage. Prédiction : chaque couche lit au plus
  E tronçons au lieu de 708 · (1 − h) · k : de l'ordre de 55 Go au lieu de ≈ 680 Go pour l'invite,
  soit un préremplissage de l'ordre de 30 à 60 s au lieu de 430 s.

### Ordre de la seconde séance, changé le 2026-10-15 à 23 h 45, avant toute mesure de cette séance
Le préremplissage par flux, s'il tient (témoin F), divise le temps d'une passe du 120b par ≈ 3 ;
l'ordre devient : D-C7, témoin F (20b), série FLUX (A : J1 tel quel, B : `--flux`), série L12 (A :
la meilleure retenue, B : A + 12 Mio), série PF (A : la meilleure retenue, B : A +
`--prechargement`), C12 brut, conversation harmony. Une configuration n'est retenue que si sa série
la fait valoir (06 § 7.5) **et** que les quatre textes de la série sont égaux. Les seuils déclarés
plus haut ne changent pas ; seule la configuration de référence (A) de L12 et PF change (« la
meilleure retenue » au lieu de « J1 tel quel ») : ~~A = la meilleure configuration J1 de la série
L12~~ pour PF devient A = la meilleure retenue après FLUX et L12.

## Commandes

```
set CARGO_TARGET_DIR=~\dev\cibles\troncons-O & set CARGO_INCREMENTAL=1
cd moteur && cargo test --offline -j 4 -p trc-cache -p troncons
cargo build --offline -j 4 --release -p trc-cache
python -I -X utf8 mesures/moteur/O/temoin_o1.py --rejouer <cible>/release/rejouer.exe --sortie mesures/moteur/O/journaux/temoin-o1.json --csv mesures/moteur/O/csv/succes-20b-rejouer.csv [--casser]
python -I -X utf8 mesures/moteur/O/casser_tests.py --sortie mesures/moteur/O/journaux/tests-casses.txt
python -I -X utf8 mesures/moteur/O/courbe_dense.py --rejouer <exe> --csv mesures/moteur/O/csv/falaise-20b-dense.csv
```
Rien sur la carte graphique à cette étape (pas de verrou pris).

## Pour l'arbitre (spécification incomplète ou à préciser ; choix prudents, réversibles, marqués)

Chacun : réponse par délégation du 2026-10-15, réversible.
1. **§ 5.7 écrit `pub struct Lru;`** (structure unité) : un LRU a un état. Fait : structure à champs
   privés, `Lru::default()` / `Lru::nouveau()`. Rien d'autre ne change dans l'API.
2. **§ 5.7 ne dit pas la sémantique de l'étage RAM.** Choisi : inclusif, il voit tous les accès
   (succès VRAM compris), une entrée ne naît que d'une lecture du disque. Raison : c'est le modèle
   « deux étages » qui a fixé les plafonds et les seuils de J1 ; démontré égal pour LRU (lemme 2).
3. **§ 5.7 ne dit pas l'ordre d'éviction dans un groupe.** Choisi : tout le groupe épinglé d'abord,
   une éviction par défaut. Démontré équivalent aux deux simulateurs Python (lemme 1).
4. **`Compteurs::evictions`** : ambigu (VRAM ou RAM ?). Choisi : VRAM ; RAM dans
   `Cache::evictions_ram()` (extension).
5. **Octets** : `Cache::nouveau` ne reçoit pas les tailles. Extension `Cache::fixer_tailles(f)` ;
   sans elle, octets = 0 (`rejouer` compte en accès). Pour O3 : le moteur la pose depuis le
   répertoire (`longueur0 + longueur1`).
6. **Témoin O1 « = le simulateur de 04 »** : 04 est un cache PAR COUCHE, `Cache` est global. Résolu
   en jugeant les deux : projection couche par couche contre l'étude 04, et cache global contre
   `gptoss_localite.py`.
7. **Extensions ajoutées** (rien d'existant ne change, § 6.2) : `Belady`, `impl Politique for Box<P>`,
   `rejouer_dans`, `Cache::{etat, occupant, emplacement_de, tiede_de, epingles, evictions_ram,
   fixer_tailles}`, `Trace::{groupe, acces, depuis_texte}`, `Compteurs::acces`, `ErreurTrace`.
8. **Espace de travail par motif** : cargo refuse TOUT l'espace tant qu'un dossier sous `crates/` ou
   `bins/` n'a pas de `Cargo.toml` (mesuré : arrivé une fois avec `crates/trc-noyaux` à 12 h 41).
   Règle écrite en tête de `moteur/Cargo.toml` : écrire le `Cargo.toml` d'une crate en premier.
   À porter dans les consignes des lots.
9. **`Cargo.lock`** est au lot O mais toute construction de tout lot le réécrit ; les versions
   exactes de `[workspace.dependencies]` le rendent déterministe. Je le recommite quand il change.
10. **Trouvé pour J1+ (pas une couture)** : la falaise du LRU global (N ≤ (L − 1)·k ⇒ 0 succès,
    démontré, mesuré sur 20b) et un plateau au-delà de L·k (96 → 120 : +0,12 point pour LRU,
    +6,8 pour Belady). Pour le 120b, la falaise est à 140 emplacements = 1,86 Go de VRAM. Le SLRU
    prévu ne la traite pas ; une politique qui connaît le cycle déterministe des couches (que LRU
    ignore, 04 l'avait noté) devrait le faire. Proposé comme sujet de J1+, non construit.

## Pour l'arbitre, étapes O2 à O4 (spécification incomplète ou à préciser ; choix prudents, réversibles, marqués)

Chacun : réponse par délégation du 2026-10-15, réversible.
11. **§ 7.1 C7, terme « 0,5 Mo »** : faux d'un facteur 7 (mesuré 3,70 Mo, bruit 82 Ko). La fenêtre
    épinglée est dimensionnée sur le plus grand tronçon, qui dépend du modèle (1,28 Mo d'écart) ;
    le répertoire est tenu deux fois (fichier ouvert, tailles du cache) ; d'autres structures
    croissent avec L (événements, contrôles, tables). Proposé : borne = d · k · |Δ lal| + 2 × 56 o
    · Δ(L · E) + 2 × bruit + 0,5 Mo, ou une fenêtre de taille fixe (12 Mio, L12) ; le verdict
    déclaré reste « tombe ».
12. **§ 7.1 C8** : le moteur ne compte que ses lectures sans tampon ; l'ouverture lit MÉTA, tables et
    répertoire par des lectures tamponnées (≈ 15 Mo), llama.dll lit le vocabulaire (13 Mo), le
    système charge les DLL. Proposé : borne + taille de ces fichiers, ou les lire par `trc-es`.
13. **§ 7.1 C5, « plancher en série recalculé »** : la formule n'est pas écrite au § 7 ; je l'ai prise
    de 07 § 1.1 (somme des étages + T0) avec les quantités de la séance, sauf la GEMV (K2, autre
    séance). Le moteur fait mieux que cette somme (recouvrement à l'intérieur d'une couche).
14. **§ 5.8 `Config::brut`** : sens non dit ; tenu pour une assertion (doit égaler le drapeau du
    fichier, sinon refus).
15. **§ 5.1 boîte aux lettres** : lue après l'événement du routeur (variante « evenement » de E0 c,
    la plus rapide sous charge), la séquence servant de témoin ; pas de sondage actif.
16. **§ 5.10 `troncons mesurer --serie ABBA`** : une série ABBA veut des processus neufs ; la série
    est menée par un pilote Python (`pilote_o4.py`, `pilote_j1plus.py`), `mesurer` est une passe ;
    ajout de `troncons disque` (l'étage disque seul, passe B de C5).
17. **C4, sens de la KL** : appliqué comme le propose le lot R (KL(référence ‖ moteur), `juge
    comparer`, A = llama.cpp, B = troncons).
18. **J1+ préchargement** : construit comme une lecture anticipée **hors du cache** (le cache ne
    voit que les demandes du routeur) : le compte du moteur reste égal à `rejouer`, et les logits
    ne changent pas. Une insertion « EnVol » dans le cache (§ 5.7, règle 5) changerait le compte.
19. **Contexte et ligne d'enchâssement** : la lecture alignée de 8 Kio (§ 4.5) est faite pour chaque
    jeton par le même lecteur que les tronçons ; en mode A0 elle coûte une requête de plus par jeton.
20. **Préremplissage** : J1 en boucle de pas fait 1,64 j/s sur le 120b contre 3,63 pour llama.cpp
    (par lots). Le préremplissage par flux (J1+) est construit ; voir la seconde séance.

## Suite

- **Fait** : O2 (TIENT), O3 sur 20b (C3, C4, compte du cache : TIENNENT), O4 = J1 sur 120b (C3, C5,
  C10, C11, C12 TIENNENT ; C7 plafond TIENT, écart TOMBE ; C8 tombe sur une passe sur quatre ; C4
  attend la référence f64 du 120b), J1+ en partie (flux retenu ; L12 non établi ; préchargement
  tué).
- **Reste** :
  1. C4 sur le 120b : `juge comparer --verite <référence f64 du 120b> --a <llama.cpp carte 120b> --b
     ~/dev/essais/troncons/lot-O/o3-120b-2026-10-15-s1-code.kld` dès que le lot R a
     ses deux `.kld` (mêmes fenêtres, jetons de `ref-openai-20b.kld`).
  2. C7 : décision de l'arbitre sur le terme de tolérance (point 11) ; sinon réduire les termes
     nommés (fenêtre fixe, répertoire tenu une fois, tables des résidents libérées).
  3. L12 : série plus longue après la décision sur la longueur des lectures (lot E, arbitre).
  4. Préchargement : un meilleur prédicteur (le routeur de ℓ + 1 sur le résidu de ℓ ne voit juste
     que 69 % du temps) ou rien ; ne pas le remettre sans une mesure qui le fasse valoir.
  5. Slru (§ 5.7) et la politique consciente du cycle des couches (point 10) : non construits.
  6. Épreuve indépendante (§ 8) : un juge qui n'a pas écrit le lot.
  7. Disque à libérer quand Stone le veut (rien effacé) : `~/dev/modeles/trc/gpt-oss-20b-brut.trc`
     (12,1 Go), `gpt-oss-120b-brut.trc` (63,4 Go), `casse/gpt-oss-20b-casse-O3.trc` (11,2 Go), et
     les `.kld` sous `~/dev/essais/troncons/lot-O/` (≈ 2 Go chacun).

## Recettes (pour RECETTES.md)

| Recette | Marche ? | Raison |
|---|---|---|
| Juger le simulateur Rust contre les outils Python importés tels quels, à l'unité | oui | 0 écart sur 508 ; un défaut réel de Belady trouvé que les tests Rust ne voyaient pas |
| Belady : prochain usage cherché depuis le « maintenant » de la politique au moment de la victime | **échec** | le cache choisit la victime avant d'insérer ; au premier défaut d'un groupe, « maintenant » est encore le groupe précédent ; 10 à 6 646 succès de moins ; corrigé : prochain usage calculé à l'accès |
| Témoin d'épinglage sur six couches dans quatre emplacements | **échec** | aucun succès possible, la cassure ne tombait pas ; une couche, puis le nombre de succès connu (|S_t ∩ S_{t−1}|) |
| Témoin d'épinglage par le seul contenu final | **échec** | sans épinglage, l'expert évincé avant son tour est relu : le contenu final reste juste ; il faut compter les succès |
| Copier une crate par `shutil.copytree` (copy2) pour la casser | **échec** | les dates d'origine font croire à cargo que l'objet d'une passe faussée est à jour : la « référence » a tourné sur la cassure précédente ; `copy_function=shutil.copy` |
| Membres de l'espace de travail par motif | oui, avec une règle | un dossier sans manifeste bloque tous les lots ; un motif sans correspondance aussi |
| Lire les traces `.tar.xz` par `tarfile` de Python plutôt qu'une dépendance Rust | oui | aucune dépendance hors couture D ; `rejouer` lit le texte |
| Reprendre l'ordre des noyaux de la chaîne K3 tel quel, puis exiger l'égalité ligne pour ligne de ses KL | oui | O2 : 160/160 ; un témoin qui compare deux implémentations sans regarder les logits eux-mêmes, grâce au déterminisme |
| Juger C3 par l'empreinte64 des logits f32 de chaque pas plutôt qu'en gardant les logits | oui | 5 120 empreintes de 8 o au lieu de 4 Go de logits ; second chemin : les `.kld` octet pour octet |
| Le cache dimensionné automatiquement sur la VRAM libre | oui | le fichier brut a eu 361 emplacements au lieu de 362 : la preuve, gratuite, que le cache n'entre pas dans le calcul |
| Une copie corrompue au hasard (lot E) comme seule cassure de C3 | **insuffisant** | le moteur tombe sur une erreur fatale nommée au premier expert touché ; il a fallu une médiane faussée (invisible au décodeur) pour montrer des logits faux |
| Lire la boîte aux lettres après l'événement du routeur (variante « evenement » de E0 c) | oui | 0 séquence fausse sur plus de 10⁶ couches servies ; 0,15 % du temps d'un jeton |
| Préremplissage par flux (l'ordre de la chaîne K3) | oui, × 17,5 | 26 s au lieu de 7 min 50 s pour 708 jetons ; égal au bit à la boucle de pas (témoin F) |
| Préchargement par le routeur de ℓ + 1 appliqué au résidu de ℓ | **échec, −11 %** | 69 % de prédictions justes ; les 31 % fausses coûtent plus de disque que le recouvrement ne rend |
| `vider_ensemble` qui refuse tout achèvement étranger | **échec, corrigé** | les lectures de la couche en cours finissent pendant le vidage ; gardées de côté |
| Lectures de 12 Mio (L12) | prometteur, non établi | +30 % en médiane, mais dispersion de 21 % : 2 × le bruit n'est pas franchi en quatre passes |
| `cargo build` du binaire pendant qu'un pilote le lance deux fois (codé puis brut) | **à ne pas faire** | les deux passes de C3 doivent tourner sur le même binaire ; construire dans une autre cible (`troncons-O-diag`) |
| Assembler un texte en décodant chaque jeton seul | **échec (affichage)** | les caractères UTF-8 coupés entre deux jetons sortent en « � » ; il faut les octets bruts |
| Reconvertir un taux Python en entier en vérifiant `n / accès == taux` au bit | oui | comparaison à l'unité sans toucher aux outils d'origine |

## 2026-10-16, ronde de corrections après l'épreuve J1 (mesures/epreuve-J1.md)

Propriétaire, pour cette ronde seulement, des fichiers des autres lots qu'elle touche (liste tenue
ci-dessous). Seuils : `mesures/moteur/O/corrections/seuils-declares.md` (commité avant chaque passe).
Binaire d'avant la ronde gardé : `~/dev/cibles/troncons-O/avant-7b288a6/troncons.exe`.

- **G1, G2 : FAIT** (c5a2f8c). Témoin `corrections/temoin_sortie.py` : ancien binaire tombe sur les
  trois cas (absent, corrompu, tué : tuyaux tenus 90 s par un nvidia-smi orphelin), nouveau tient.
  Cause probable de G1 trouvée en lisant le code : au préremplissage par flux, une lecture pouvait
  prendre un tampon d'arrivée qui portait encore une lecture en vol (tourniquet de d·k = 12 tampons,
  jusqu'à 8 en vol, achèvements dans le désordre sous charge) ; corrigé, conflits comptés
  (`flux_conflits_evites`). Reste : rejouer sous la charge de l'épreuve (numpy 120b + `evaluer
  --flux --brut`) pour lire l'erreur et compter les conflits.
- Fichiers d'autres lots touchés : `trc-juge/src/compteurs.rs`, `trc-juge/Cargo.toml` (lot R) ;
  `trc-format/src/lib.rs` (lot F, extension `octets_lus_a_l_ouverture`).
- PID 13652 (nvidia-smi orphelin du lot O, 01 h 38) : laissé ; je ne l'ai pas lancé (règle du SOCLE).
- **m2 : FAIT** (build.rs appelle nvcc directement ; avec et sans vcvars, images égales).
- **M1 : FAIT** (garde de production, `trc-ordo/src/garde.rs`) ; témoins 20b tiennent (copie O3 :
  erreur nommée couche 0, expert 30) ; coût 120b : −12 % en moyenne mais sous le seuil de la règle
  (bruit 11-12 % : le disque variait de 1,51 à 1,95 Go/s) ; à disque égal (passes 4 et 5) −1,7 % ;
  attente au chemin critique 5,3 ms par jeton ; ouverture +0,95 s ; C5 tient sur chaque passe.
- **M5 : MESURÉ** (option `--kv-f32`, hors couture N) : KV f32 = vérité f64 au format près (KL
  −0,00048, 100 % premiers choix, 0,69 pas au plus, routage 100 %, premier jeton 1008). Coût :
  314 emplacements au lieu de 326 (h de l'invite 0,459 → 0,442 par `rejouer`, +3,2 % de défauts) ;
  la génération de C12 n'est pas comparable (autre texte : 72304d85…, h 0,435 contre 0,590).
- **M3 : instrument fait** (compteurs d'E/S du processus dans le journal ; compte du moteur corrigé :
  les résidents étaient comptés deux fois dans `octets_comptes_moteur` du binaire de la séance) ; écart
  processus − moteur constant à 19,9 Mo sur 8 passes 120b.
- Fichiers d'autres lots touchés (suite) : `trc-noyaux/build.rs`, `noyaux/passe.cuh`, `src/lib.rs`,
  `tests/passe.rs` (lot K).
- En cours : G1 sous charge (nouveau binaire : fini en 358 s, 0 conflit), ancien binaire sous charge,
  puis base llama.cpp balayée (bloc 6).

### Pour l'arbitre, ronde de corrections (spécification fausse ou incomplète ; choix prudents, réversibles, marqués)

Chacun : réponse par délégation du 2026-10-16, réversible.
21. **Couture N (§ 5.6, cache KV en f16)** : mesuré, l'arrondi f16 porte tout l'écart mesurable du
    moteur à la vérité f64 (KV f32 : KL au plancher du format, 100 % de premiers choix, routage égal,
    premier jeton de C12 = 1008). Coût : +155,7 Mo de VRAM au contexte de 4 096, 12 emplacements
    (326 → 314), ≈ +3,2 % d'octets lus par jeton sur la trace de l'invite. Proposé : KV f32 par défaut
    (C4 et C12 deviennent « égaux à la vérité au format près »), f16 en option. Fait ici : l'option
    `--kv-f32` (noyaux ajoutés, rien d'existant changé) ; **le défaut reste f16** tant que tu n'as pas
    tranché.
22. **C4 (§ 7.1)** : ajouter le critère de queue du juge (part des positions de KL > 0,1, KL au 99ᵉ
    centile, jugés aussi au-delà de 512 positions). Chiffres pour le fixer : f16 0,39 % et 0,075
    (fenêtre 0), 2,05 % et 0,196 (positions 512 à 706) ; f32 : 0 et ≈ 0.
23. **C12 (§ 7.1)** : publier à côté du texte la suite gloutonne de la vérité f64. Non faite : la passe
    numpy du juge refait tout le préfixe à chaque jeton (≈ 20 min par position sur le 120b, soit des
    jours pour 256 jetons) [calc.] ; la suite en KV f32 (72304d85…) en est le meilleur substitut
    mesuré (premier jeton égal, 708 / 708 argmax de l'invite égaux).
24. **C8 (§ 7.1)** : juger par `GetProcessIoCounters` (ReadTransferCount) contre le compte du moteur
    (lecteur + ouverture), borne = vocabulaire + 100 Mo ; le PDH publié, non jugé. Mesuré : écart
    constant de 19,92 Mo.
25. **C7 (§ 7.1, terme de 0,5 Mo)** : borne à termes nommés posée (O-pour-le-memoire § 13.6) : 2,05 Mo
    de termes nommés contre 2,94 mesurés ; non fermée. Proposé : juger l'écart à fenêtre fixe contre
    termes hors fenêtre + 2 × bruit + 0,5 Mo. Verdict « tombe » d'ici là.
26. **C5 (formule, REPRISE-O point 13)** : une passe D d'échauffement jetée en tête de séance (fait
    dans la séance vitesse-2026-10-16). Proposé : l'écrire au § 7.1.
27. **§ 4.12 (contrôles en production)** : la garde de production (empreinte des octets utiles de
    chaque tronçon lu, et des lignes d'enchâssement) est construite, active par défaut (`--sans-garde`
    pour mesurer). Proposé : l'écrire au § 4.12 (« En production, chaque partie lue est comparée à
    `empreinte_niveau` avant que le pas ne rende son jeton ») ; C2 devient vrai en production.
28. **m4 (§ 4.3, § 4.5, § 4.9.2), trois phrases proposées** : (a) § 4.3, champ sections : « longueur =
    octets utiles de la section, bourrage non compris » ; (b) § 4.5 : « l'empreinte64 de la table est
    aux 8 derniers octets de la section » au lieu de « après la zone de données » ; (c) § 4.9.2 : « à
    la fin de la tuile t, p = début[t + 1] (contrôle permis, non exigé) ».
29. **m6 (§ 8.7)** : le verdict est dans `mesures/epreuve-J1.md` (consigne du juge) ; à trancher.
30. **§ 2.2 et SOCLE (m2)** : le `build.rs` marche maintenant avec et sans vcvars ; la recette du SOCLE
    redevient vraie telle qu'écrite (rien à changer).
31. **Prévenir les lots (G2)** : tout outil qui lance un enfant avec `std::process::Command` sous un
    pilote à tuyaux doit soit rendre ses poignées standard non héritables
    (`trc_juge::compteurs::poignees_standard_non_heritables`), soit placer l'enfant dans une tâche
    tuée à la fermeture ; sinon un enfant survivant fige le pilote.
32. **PID 13652** (nvidia-smi orphelin, 01 h 38, d'une passe du lot O) : laissé vivant (je ne l'ai pas
    lancé, règle du SOCLE) ; à arrêter par Stone ou l'orchestrateur.

### Ronde de corrections : état final (2026-10-16, 10 h 15)

- **Fait et témoigné** : G1 (sortie sans destruction, erreur écrite d'abord, battements, tampons
  d'arrivée du flux), G2 (enfant nvidia-smi), M1 (garde de production), m2 (build.rs), m5 (phrase
  requalifiée), M2 (base balayée : `fit -t 16` 0,884 j/s ; C6 × 2,22, tient ; × 3,85 barré dans
  O-pour-le-memoire, REPRISE-O, et note dans mesures/gpt-oss.md § 3.2).
- **Mesuré, décision à l'arbitre** : M5 (KV f32 = vérité au format près ; option `--kv-f32`, défaut
  f16), M3 (C8 par le processus, écart constant 19,92 Mo), M4 (borne à termes nommés, non fermée),
  m1 (D d'échauffement jetée), m3 (engagée 6,92 à 6,97 Go, perte machine 0,47 à 0,63 Go), m4, m6.
- **Non établi** : la cause première de G1 (deux rejeux sous la charge de l'épreuve, nouveau et
  ancien binaires : les deux finissent ; 0 conflit d'arrivée observé).
- Verrou de la carte pris à 06 h 41, renouvelé à 07 h 21, 08 h 13 et 09 h 14, rendu à 10 h 06.
- Disque : `~/dev/essais/troncons/lot-O/ronde/` (3,5 Go : `.kld`, `.npz`), cibles
  `troncons-O-vcvars` et `-sans-vcvars` (41 Mo), à libérer quand Stone le veut.
- Fichiers des autres lots touchés : lot R `trc-juge/src/compteurs.rs`, `trc-juge/Cargo.toml` ; lot F
  `trc-format/src/lib.rs` ; lot K `trc-noyaux/build.rs`, `noyaux/passe.cuh`, `src/lib.rs`,
  `tests/passe.rs` ; documents `mesures/gpt-oss.md` (§ 3.2, ajout).

### Recettes de la ronde (pour RECETTES.md)

| Recette | Marche ? | Raison |
|---|---|---|
| Rejouer un constat avec le binaire d'avant (copie figée) avant de corriger | oui | G1, G2, m2 reproduits d'abord ; la cassure du témoin, c'est l'ancien binaire |
| Témoin de sortie qui attend la fermeture des tuyaux (comme les pilotes) | oui, après deux défauts | passe 1 : tué avant la naissance de l'enfant ; passe 2 : tuyaux non vidés, l'enfant se bloquait sur sa sortie d'erreur pleine ; deux fils de lecture |
| Tâche Windows « tuer à la fermeture » pour un enfant | oui | couvre la mort du parent par TerminateProcess, que `Drop` ne voit pas |
| Poignées standard rendues non héritables | oui | `bInheritHandles = TRUE` donne à l'enfant toutes les poignées héritables, dont les tuyaux du pilote |
| `TerminateProcess` sur soi après l'erreur | oui | aucune destruction du contexte CUDA, aucun `DllMain` de sortie |
| `cmd /C ""nvcc" …"` par `Command::arg` | **échec** | `arg` protège les guillemets par des barres obliques inverses, que cmd ne lit pas ; appeler nvcc directement |
| Garde : hacher en parallèle, vérifier avant de rendre le jeton | oui, −1,7 % à disque égal | le hachage (1,1 Go/s par fil) se cache derrière le disque ; seul le dernier tronçon d'un pas reste au chemin critique (5 ms) |
| Garde vérifiée avant la GEMV (au lieu de la fin du pas) | non essayée | calculée : ≈ 6 ms × ≈ 30 couches par pas, −40 % |
| Table des empreintes des lignes lue dans la fenêtre d'arrivée | oui | 1,6 Mo de plus seulement ; `token_embd` vérifié entier au passage |
| Cache KV en f32 | oui pour la justesse | KL au plancher du format, routage égal sur 36 × 708 ; coût 12 emplacements |
| Comparer des vitesses de génération sur des textes différents | **à ne pas faire** | le texte f32 ne boucle pas : h 0,435 contre 0,590 ; le coût du KV se mesure par `rejouer` sur une même trace |
| Compter le chargement des résidents à part du lecteur | **échec, corrigé** | le lecteur le compte déjà : +1,69 Go dans le total |
| Balayer `-t` de llama.cpp sous mmap | oui | +54 % de 6 à 16 fils : une base mal réglée gonflait C6 |
| Un heredoc bash avec des guillemets typographiques et des barres obliques inverses | **échec** | deux fois « unexpected EOF » ; écrire le texte par l'outil d'écriture puis `cat >>` |
