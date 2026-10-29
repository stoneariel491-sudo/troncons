# Le tri du mimétisme : six pistes à mesurer, le reste écarté, et la carte monde vers pipeline

Rôle : tri des candidats des six éclaireurs (physique, mathématiques, vivant, Terre et cosmos,
systèmes humains, ingénierie). Date : 2026-10-27. Seuils : `mesures/mimetisme/tri/00-seuils-declares.md`
(commit ec124f5, avant ce document). Aucune mesure lancée par moi : un tri ne mesure pas.

Étiquettes : **[mes.]** mesuré par un éclaireur, journal commité ; **[calc.]** calculé ici ou par un
éclaireur à partir de mesures commitées ; **[rel.]** relayé de la consigne, non relu à la source par moi ;
**[hyp.]** hypothèse dite. Les sources externes citées sont celles des éclaireurs ; je ne les ai pas
rouvertes (titre, auteurs, année, adresse : dans leurs `eclaireur.md`).

Ce que j'ai vérifié moi-même dans les fichiers : le tableau des politiques de `h3-a.csv` et `h2.csv`,
la définition du « lfu » de `cache2.py`, le code de `trc-cache/src/lib.rs` (lignes 150 à 260), le
passage O § 9.2, les JSON de marges M3 et E7, l'emplacement des captures d'entrées
(`~/dev/essais/troncons/genome/eclaireur/{calib,eval}/h-Lll.f32`, 1,6 Go).

---

## 0. En bref

1. **Six pistes retenues** : P1 mémoire du cache à deux échelles jugée en génération ; P2 cache
   exclusif VRAM vers RAM ; P3 routage conditionné par le cache, borné par la marge ; P4 préchargement
   et rétention à confiance calibrée, qui cède à la demande ; P5 recuit et échange de répliques sur
   les symboles synonymes (verre de spin) ; P6 fidélité décidée par appel (portillon de poids, cache
   à niveaux).
2. **Le plus fort signal de dédoublonnage** : le LFU à mémoire longue sort de **quatre** éclaireurs
   en positif (vivant, Terre et cosmos, humain, ingénierie) et de deux en négatif (physique : la forme du noyau
   ne compte pas ; mathématiques : un prédicteur appris n'ajoute que +0,012).
   Mais **toutes ses mesures sont faites sur des traces de lecture (préremplissage)**. Le LFU
   à décroissance n'a jamais été mesuré sur une trace de génération, qui est la charge réelle.
   Le « LFU −0,075 en génération » d'ingénierie n'est pas le contre-exemple qu'il paraît :
   son « lfu » est **sans décroissance** (`cache2.py` : le compteur monte, seule la politique
   « adm » le divise par deux). Les deux faits laissent la question ouverte, d'où P1.
3. **Trois des six touchent le goulot sans passer par la qualité** (P1, P2, P4 : octets lus, pour
   la même sortie au bit) ; trois le touchent en échangeant de la qualité (P3, P5, P6) et se jugent
   à la KL, donc après la levée du verrou de la carte pour leur étape finale.
4. **Une incohérence entre éclaireurs, tranchée** : mathématiques fixe pour le routage conscient
   du cache « +10 points de succès pour au plus 25 % de cellules échangées », et humain borne
   l'échange 4e/5e à 8,2 % des défauts à τ = 0,03 (borne optimiste). Les deux ne se contredisent que
   si l'on s'en tient au seul échange 4e/5e ; le biais sur tous les résidents peut en changer
   davantage. P3 mesure exactement cela, et sa rangée « 4e/5e seul » doit respecter la borne E7.
5. **Une barre commune** : P3 et P6 se jugent contre la même pente, la KL du mode rapide par octet
   économisé. P6 fournit la courbe KL(f) (part f des défauts servis en rapide) qui manquait.

---

## D'où on part, où on va

**Au départ** : trois gains tenus (codon du zéro, contexte de colonne, mutation synonyme), la garde
tropicale globale fermée, la graine, le duplicata, l'hebbien, les spectres fermés (05 § 2, § 3), et le
cache LRU partagé dans le moteur (`trc-cache` n'exporte que `Lru` et `Belady`). Six éclaireurs ont
rendu 45 candidats ; une bonne partie a déjà un verdict mesuré (fermés), le reste est ouvert ou non mesuré.

**Ce que ce document établit** : lesquels valent une mesure, avec quel protocole, quel seuil, quel
témoin, et lesquels sont écartés avec leur raison.

**Ce qui reste** : lancer les six protocoles, dans l'ordre du § 3.

---

## 1. Dédoublonnage : les mêmes mécanismes sous des noms de domaines différents

| Mécanisme commun | Éclaireurs et noms d'origine | Étiquette de signal |
|---|---|---|
| LFU à demi-vie longue | vivant #1 (ACT-R, loi de puissance de la mémoire), Terre #1 (Hasselmann, deux réservoirs), humain #1 et #8 (Anderson et Schooler, ACT-R), ingénierie #2 (rétention informée), physique #4 (Omori-Utsu, Kohlrausch, deux temps), Terre #7 (Omori), Terre #4 (marée, horloge de couches) | six domaines, un seul levier : une demi-vie plus longue que 8 jetons |
| Routage qui favorise les experts résidents | mathématiques #1 (cache-conditionnel), Terre #6 (faille collante, friction à vitesse et état), humain #5 (substitution d'article, puissance de deux choix) | trois domaines |
| Prédire les experts à venir | mathématiques #2 (prédiction conforme), humain #2 (jurisprudence, raisonnement par cas), vivant #2 (circuit olfactif de la mouche, mémoire épisodique), vivant #4 (synergies motrices), Terre #5 (parareal, COLA, onde P), ingénierie #2 (OPTgen) | six domaines |
| Préchargement subordonné à la demande | ingénierie #4 (TCP Nice, LEDBAT), humain #3 (BOLA des lecteurs vidéo), mathématiques #2 | trois |
| Choisir la fidélité à la lecture | physique #3 (occupation de Fermi), vivant #5 et #7a (fovéation), humain #6 (triage), ingénierie #6 (raffinement itératif en précision mixte), humain #3 (BOLA), vivant #3 (queue de Pareto) | six |
| Cache exclusif | ingénierie #1, et par domination ingénierie #5 (cache compressé) | un seul, mais mesuré |
| Plafond de la vérification groupée | mathématiques #5, vivant #6 | deux, fermé |
| Courbe sans falaise | mathématiques #8, ingénierie #7 (Talus) | deux, fermé |
| Allocation des emplacements entre couches | vivant #7b (Charnov), Terre #8 (hydraulique), humain #7 (METRIC) | trois, fermé |

---

## 2. Les six pistes retenues

Critère de classement : gain attendu × nouveauté × faisabilité sur données existantes sans carte
graphique, avec priorité au goulot réel (octets lus par mot, bascules du routage, préchargement).
Le gain est écrit pour ce qu'il est : un ordre de grandeur calculé, pas une prévision.

Contraintes communes de tous les protocoles : pas de carte graphique ; `OMP_NUM_THREADS=2` ; processus
sous priorité normale ; RAM visée **≤ 1,5 Go** (4,7 Go libres au moment du tri, 2 Go quand d'autres flux
tournent) ; si `~/dev/verrou-carte.txt` existe, aucune lecture lourde de fichier modèle
(il existe aujourd'hui, séance disque du juge de placement) ; `git add` ciblé, commit après chaque pas.

### P1. Mémoire du cache à deux échelles, jugée en génération

**Source du mécanisme.** Un réservoir lent intègre le forçage rapide (modèle de climat stochastique de
Hasselmann, 1976 [rel., Terre #1]) ; la mémoire humaine oublie en loi de puissance (Anderson et
Schooler 1991, ACT-R [rel.]) ; le LRFU (Lee et al., 2001 [rel.]) en est la version cache. Domaines
d'origine : climat et psychologie.

**Pourquoi elle passe devant.** C'est le seul candidat qui a déjà un gain mesuré sur les traces et
que quatre éclaireurs ont retrouvé, mais seulement en lecture : à 20 % du 120b, −17,6 % de défauts
contre le LRU (Terre #1), −10 % contre le LFU de demi-vie 8 (humain #1) [mes.]. Le moteur n'a pas de
LFU. Si le gain existe en génération, c'est le changement le moins cher du projet (un compteur par
cellule, 4 608 flottants). S'il n'existe pas, il faut le savoir avant de le construire.

**Protocole.**
- Données : `mesures/localite-gpt-oss/traces-120b/traces-120b.tar.xz` (7 traces : code, dialogue,
  prose-en, prose-fr en lecture ; wiki en lecture ; prose-en et wiki en génération, 256 jetons chacune)
  et `traces-20b/traces-20b.tar.xz`. À extraire dans un dossier neuf hors dépôt.
- Grandeur : taux de succès global, règle de groupe de `trc-cache`, 326 et 922 emplacements (120b) ;
  politiques : LRU, LFU(h) pour h dans {8, 32, 64, 128, infini}, mélange de deux demi-vies
  (rapide 8, lente 128, poids choisi en validation croisée), horloge de couches (ETR).
- Plan de jugement : (a) h choisi sur les 5 traces de lecture **hors** du genre jugé ; (b) génération
  seule ; (c) chaîne : cache chauffé par la lecture du même genre, puis génération (c'est le cas
  réel d'un invite suivie d'une réponse ; le texte diffère, c'est dit).
- Seuil : succès LFU(h*) − LRU ≥ +0,02 sur les **deux** générations et la chaîne, > 2 σ ; mort sous
  +0,005 sur l'une des deux. Vitesse attendue si tenu : ×1,083 (disque seul borne) [calc.].
- Témoins : demi-vie → 0 redonne le LRU (0,7379 ; 0,45279) ; demi-vie infinie redonne le LFU sans
  décroissance (0,66268 ; 0,42632) ; cassure : décroissance inversée, doit tomber sous le LRU.
- Second chemin : `outils/mimetisme/physique/noyau-cache` (Rust) contre le Python de
  `outils/mimetisme/ingenierie/cache2.py`.
- Durée et mémoire : 70 exécutions de 10 à 30 s en Python, soit 30 à 60 min sur un fil ; RAM < 1 Go [calc.
  d'ordre de grandeur sur la taille des boucles, à mesurer au premier témoin].
- Suite si tenue : quatre traces de génération de plus (passe moteur, après levée du verrou), puis ABBA
  dans le moteur avec la politique dans `trc-cache`.

**Ce qui pourrait être faux.** 256 jetons de génération sur un cache vide sont peu : le taux simulé
(0,74) dépasse le taux mesuré par le moteur (0,59). Un résultat « non concluant » est probable et
sera dit comme tel.

### P2. Cache exclusif VRAM vers RAM

**Source du mécanisme.** Hiérarchies de stockage : quand le niveau haut évince, il descend le bloc
dans le niveau bas au lieu de le dupliquer (Wong et Wilkes, « My cache or yours? », USENIX ATC 2002
[rel., lu par l'éclaireur ingénierie]). Domaine : stockage et systèmes.

**Pourquoi elle passe devant.** La lecture du code le confirme : dans `Cache::demander` la RAM est
remplie à **chaque défaut disque** (`entree_tiede_pour`) et rafraîchie à chaque succès VRAM ; elle
contient donc les R experts les plus récents, déjà tous en VRAM quand R ≤ V. La simulation de
l'éclaireur le dit sans appel : inclusif avec R ≤ V ajoute **0,0000** de succès [mes., `h1.csv`] et
avec 1 Go de RAM tiède le moteur ne rend rien à la génération (épreuve J1 § 3.4, rel.). Exclusif :
part disque 0,2621 → 0,2352 / 0,1845 / 0,1368 pour R = 80 / 336 / 672 [mes., `h2.csv`], soit −10 / −30 /
−48 %. C'est le plus grand gain chiffré de toute la ronde sur le goulot. Le coût est réel et se dit :
R = 336 engage 4,45 Go de RAM de 15,6.

**Protocole.**
- Données : mêmes 7 traces du 120b ; code : `moteur/crates/trc-cache/src/lib.rs` (lecture seule).
- Grandeur : part des octets lus sur le disque, exclusif contre inclusif, R dans {80, 160, 336, 672,
  1 344}, VRAM en LRU puis en LFU(h*) si P1 tient ; en plus le temps estimé par défaut converti :
  4,1 ms (disque) contre 1,09 ms (RAM décodée, 13,25 Mo à 12,2 Go/s) ou 1,8 ms (RAM encodée, avec
  le décodage de 0,85 ms) [calc.] ; et le trafic VRAM vers RAM (13,25 Mo par éviction, environ 38
  évictions par jeton en LRU, soit 41 ms par jeton, 12 % d'un jeton de 345 ms) [calc.].
- Seuil : réduction relative de la part disque ≥ 15 % à R = 336 sur les deux générations ET trafic de
  descente ≤ 25 % du temps de jeton ; mort sous 5 % sur l'une des deux.
- Témoins : R = 0 redonne le LRU seul ; inclusif à R ≤ V ajoute 0 ; exclusif à R égale le LRU de V + R à
  7e-4 près ; cassure : démotion supprimée, doit redonner l'inclusif.
- Second chemin : implémentation indépendante (Rust, hors `cache2.py`), égale à 1e-4 sur les 7 traces.
- Durée et mémoire : 140 exécutions de ~10 s, 30 min sur un fil ; RAM < 1 Go.
- Suite : ABBA dans le moteur avec `--ram-tiede` à 1, 4, 8 Go (carte nécessaire : après levée du
  verrou) ; la décision d'engager la RAM est à Stone.

**Ce qui pourrait être faux.** Le gain simulé est celui d'un LRU de capacité V + R : la preuve est
que le témoin le redonne à 7e-4. Il suppose que la copie RAM vers VRAM et la descente VRAM vers RAM
se recouvrent avec le calcul (PCIe duplex), ce qui n'est pas mesuré. Windows engage déjà 7,9 Go avec
1 Go de tiède (rel.).

### P3. Routage conditionné par le cache, borné par la marge

**Source du mécanisme.** Dissiper des quasi-égalités : un biais de logit vers les experts résidents
avant le top-k (Skliar et al., « Mixture of Cache-Conditional Experts », TMLR 2025, arXiv 2412.00099
[rel.]). Trois éclaireurs y arrivent par la faille qui colle (friction à vitesse et état), la
substitution d'article en rupture et la puissance de deux choix. Domaines : sismologie, commerce, files
d'attente.

**Pourquoi.** Elle change le **flux de demandes** et non la politique : Belady est optimal pour un
flux fixé, et la politique ne bouge plus (écart du meilleur prédicteur au LFU réglé : +0,011 à +0,013,
mathématiques M1 [mes.]). C'est la seule piste qui agit sur les **bascules de routage** par le bon
bout : elle dépense les marges au lieu de les protéger (la garde tropicale est fermée à 57,1 % des
bascules pour 10 % des cellules). Elle est aussi la plus risquée : une bascule voulue coûte comme une
bascule subie (26,6 % de propagation à la couche suivante, 96,5 % de la KL sur les positions qui
basculent [mes.], 05 § 2.2).

**Protocole.**
- Données : **insuffisantes aujourd'hui** (les journaux `r1/routage/*.bin` ne gardent que les 4
  experts et la marge 4e-5e). Il faut une passe CPU du 20b qui journalise les 8 meilleurs
  (expert, logit) par couche et par jeton sur les 5 110 positions de R1 (humain l'estime à ~4 min ;
  à confirmer). **Après levée du verrou.** Modèle : `~/dev/modeles/trc/gpt-oss-20b-v12.trc`.
- Grandeur : par β dans {0 ; 0,01 ; 0,03 ; 0,1 ; 0,3} : défauts évités (cache global du 20b, budgets
  19 % et 31 %), part des cellules dont l'ensemble change, puis KL excédentaire par l'expérience B
  du lot R (routage imposé à la référence f64, `mesures/moteur/R/r1_reference.py`).
- Seuil : ∃ β avec ≥ 10 % de défauts en moins pour une KL excédentaire ≤ 0,038 (pente du mode rapide,
  0,13 pour −34 %, linéarisée) et un premier choix ≥ 95 % ; mort si au β à −10 % de défauts la KL
  dépasse 0,07.
- Témoins : β = 0 redonne le modèle exact au bit ; β négatif doit augmenter les défauts ; la rangée
  « échange 4e/5e seul » doit rester sous la borne E7 (3,1 % à τ = 0,01 ; 8,2 % à τ = 0,03).
- Second chemin : rejeu du cache sur les ensembles biaisés par `cache2.py`, indépendant du tracé.
- Durée et mémoire : tracé ~4 min [rel.] ; rejeu minutes ; quatre passes de référence f64 à ~2 168 s
  chacune [mes., JUGEMENT § 3], soit ~2,5 h sur 2 fils ; RAM de pointe de ces passes à relever dans
  leurs journaux (non connue de moi). Arrêt séquentiel (voir § 5) pour réduire les passes.

**Ce qui pourrait être faux.** Le gain publié (plus de 50 % de défauts en moins) vient d'autres
modèles ; avec k = 4 sur 128 grands experts il peut être bien plus petit. La borne E7 donne moins de
10 % de défauts évitables dans la zone sûre (hypothèse optimiste d'un 5e résident).

### P4. Préchargement et rétention à confiance calibrée, qui cède à la demande

**Source du mécanisme.** Deux emprunts : la prédiction conforme et la maîtrise conforme du risque
(Angelopoulos et Bates, arXiv 2107.07511 ; Angelopoulos, Bates, Fisch, Lei, Schuster, ICLR 2024
[rel.]) donnent un sous-ensemble de prédictions dont la précision est garantie sans hypothèse de loi ;
le trafic d'arrière-plan qui n'occupe que la ressource libre et recule à la demande (TCP Nice, OSDI 2002 ;
LEDBAT, RFC 6817 [rel.]). Domaines : statistique et réseaux. Le prédicteur est le raisonnement par
cas : les 20 jetons antérieurs du même texte les plus proches par recouvrement des ensembles
d'experts votent (humain E4, E4b [mes.]).

**Pourquoi.** Le préchargement du projet est tué par la **précision** (p = 0,692, +34 % d'octets,
−11 % de vitesse, O § 9.2), et O écrit lui-même qu'il ne reviendrait qu'avec p > 0,9. La prédiction
conforme est faite pour cela ; l'annulation à l'arrivée d'une demande retire le deuxième défaut du
mécanisme (les lectures fausses retardent les vraies). Le bras R (épingler en VRAM les experts prédits
sans rien lire de plus) n'a **aucun coût en octets** : seul le bras de lecture d'avance en a un.
Mesure de départ : rappel en ligne à d = 2 de 0,72 (20b) et 0,57 (120b) contre 0,52 et 0,28 pour la
meilleure base populaire [mes., humain E4], mais chute à +0,08 et +0,13 hors du texte : la
calibration doit donc se faire dans la session.

**Protocole.**
- Données : traces de lecture et de génération des deux modèles (chemins de P1) ;
  `outils/mimetisme/humain/e4b_defauts.py` (attention : ce fichier est modifié et non commité par
  un autre agent au moment du tri, ne pas l'écraser ; en recopier la logique) ; débits de
  `fondations/01-machine.md`.
- Grandeur : par seuil de confiance θ, précision et couverture ; puis gain de vitesse simulé à événements
  discrets (disque 2,82 Go/s, PCIe 12,2 Go/s, 4,1 ms par défaut, recouvrement f = 0,17) pour les deux
  bras.
- Seuil : ≥ +5 % de vitesse simulée pour ≤ 5 % d'octets de plus, 3 genres de lecture sur 4 et la
  génération, précision réalisée ≥ 0,85 sur la moitié de test ; mort sous +2 % ou sous 0,8 de précision.
  Plafond : ×1,21 [calc.].
- Témoins : θ = 0 sans annulation redonne le −11 % du moteur à ±4 points ; prédicteur parfait redonne
  ×1,21 à 2 % ; cassure : étiquettes mélangées → précision au hasard.
- Second chemin : formule fermée gain ≈ f − (1 − p)/p × part disque contre la simulation.
- Durée et mémoire : ~1 h ; RAM < 1,5 Go (bitmaps de 4 608 bits par jeton).
- Suite : la version à état caché (routeur de la couche suivante sur le résidu) demande le moteur ;
  elle est déjà prévue par J1+.

**Ce qui pourrait être faux.** Le gain est un recouvrement, pas moins d'octets : le plafond est ×1,21 et
l'éclaireur calcule ×1,03 à ×1,08 de réaliste. Le prédicteur par précédents ignore la génération
(les traces de génération sont courtes).

### P5. Recuit et échange de répliques sur le choix des symboles synonymes

**Source du mécanisme.** Choisir pour chaque poids un niveau de la grille en minimisant
(w − q)ᵀ H (w − q) est le problème du vecteur le plus proche, donc l'énergie d'un **verre de spin** ;
la rétroaction de la mutation synonyme est un passage glouton (l'algorithme de Babai : Chen et
al., arXiv 2507.18553, ICLR 2026 [rel., page lue par l'éclaireur]). Le recuit simulé (Kirkpatrick,
Gelatt, Vecchi 1983) et l'échange de répliques (Hukushima et Nemoto 1996) traversent les minima locaux
où le glouton s'arrête [mém. des éclaireurs]. Domaine : **physique statistique de la matière
désordonnée**, le plus éloigné du calcul de tous les candidats retenus. Aucun recuit ni échange de
répliques appliqué à la quantification de LLM n'a été trouvé par l'éclaireur.

**Pourquoi.** La mutation synonyme est le seul gain avec perte qui ait passé la KL (−0,0098 ± 0,0033).
Son optimiseur est un seul passage glouton ; l'optimiseur est le seul étage non essayé.
Chiffre de départ : si l'erreur pondérée baisse de 20 % à débit égal, la haute résolution
(D ∝ 2^(−2R)) donne 0,16 bit par poids, soit 6 % du débit du mode rapide [calc., hyp. de l'éclaireur].

**Protocole.**
- Étape 1 (aujourd'hui, sans fichier modèle) : le H réel construit depuis les captures
  `~/dev/essais/troncons/genome/eclaireur/calib/h-L{00,08,16,23}.f32` et
  `routage-Lll.bin` (en `memmap`, une couche à la fois), avec des poids **synthétiques**
  gaussiens sur la grille ; mesurer l'écart Babai / descente / échange de répliques et le sur-ajustement
  calibration contre évaluation (`.../eval/`).
- Étape 2 (poids réels, ~100 Mo de lecture : accord de l'orchestrateur ; **pas sous le verrou**) : 8 experts
  du 20b (couches 0, 8, 16, 23 × experts 0 et 16) lus par le lecteur GGUF de
  `outils/genome/construction/juge/decodeur_juge.py` ; 256 rangées tirées par matrice (les rangées
  sont des problèmes indépendants qui partagent H).
- Grandeur : (w − q)ᵀ H (w − q) + λ × débit à débit égal ±0,005 bit, sur l'évaluation tenue à
  l'écart ; puis KL appariée sur 10 fenêtres (après la levée du verrou).
- Seuil : baisse tenue ≥ 10 % sur 6 experts sur 8, puis KL appariée ≤ −0,005 contre λ = 0 ;
  mort sous 3 % ou en hausse.
- Témoins : 10 poids × 5 niveaux, force brute (5^10 = 9 765 625) ; il doit exister une instance où
  Babai échoue (sinon l'instrument ne peut pas tomber et la piste s'arrête) ; cassure : un seul pas de
  température doit retomber sur Babai ; second chemin : décodage par sphère (Fincke-Pohst) à n = 16.
- Durée et mémoire : étape 1 environ 30 min ; étape 2 de quelques heures sur 2 fils (une passe de
  Babai prend ~54 s par expert, le recuit cent fois plus de balayages sur 256 rangées : à mesurer au
  témoin, non connu) ; RAM ~1 Go (H en f64 : 66 Mo, plus le facteur de Cholesky).

**Ce qui pourrait être faux.** Le sur-ajustement est le risque central : 766 entrées de calibration
pour 2 880 dimensions donnent un H de rang ≤ 766 (avant la régularisation δ*), un grand sous-espace
où l'erreur est libre ; un optimiseur plus fort l'exploite et l'évaluation tenue à l'écart le
punit (l'écart calibration/évaluation vaut déjà ×3,5 à δ* = 1). Le gain littéraire (jusqu'à 30 %
d'erreur relative en moins, QuantEase [rel., non reproduit]) vient de grilles entières et sera
plus petit sur la grille MXFP4 emboîtée.

### P6. Fidélité décidée par appel : portillon de poids et cache à niveaux

**Source du mécanisme.** Les poids de mélange sont des nombres d'occupation (softmax sur 4 niveaux
d'un système) ; une occupation faible pèse peu dans la sortie de couche (physique #3 : surface de
Fermi). Voisins pour la même idée de dégrader selon l'importance : HOBBIT (arXiv 2411.01433 [rel.]),
Lu et al. (ACL 2024, arXiv 2402.14800 [rel.]), la fovéation de l'œil (vivant #5), le raffinement
itératif en précision mixte (Haidar, Tomov, Dongarra, Higham, SC18 [rel.]).

**Pourquoi.** Elle donne la courbe qui manque à tout le lot B : **la KL en fonction de la part f
des défauts servis en rapide** (extrémités mesurées : 0,0044 à f = 0 ; 0,145 à f = 1 ; milieu
inexistant). Gain d'octets mesuré sur les traces du 120b : 8,6 % à θ = 0,20, 19,5 % à θ = 0,25 [mes.,
`mesures/mimetisme/physique/e2/portillon-de-poids.json`] ; l'énergie perturbée (somme des w²) serait de
5,5 % à 18,3 % de celle du tout-rapide [calc.], soit 0,44 à 0,65 de la perturbation par octet économisé.
Ne rouvre pas la porte fermée par physique E2 (retrait total : 0,09 % des défauts sous 0,05) : ici
l'expert n'est pas retiré, il est lu en rapide.

Deux pièges déjà vus et inclus : (a) un expert inséré au niveau rapide puis rappelé avec un poids
fort doit être remonté, ce qui coûte 3,72 bits ; le fichier rapide n'est pas emboîté dans l'exact (le
compagnon synonyme choisit ses symboles par rétroaction), donc la remontée relit l'exact entier ;
mathématiques #3 note que coder l'exact conditionnellement au rapide coûterait au mieux 1,05 bit
de plus, d'où une raison chiffrée, non mesurée, de ce format emboîté ; (b) le gain de vitesse du mode
rapide a déjà été barré par le juge (×1,28 au 120b, ×0,94 au 20b), donc l'étape 0 compte des
octets, jamais des jetons par seconde.

**Protocole.**
- Étape 0 (traces et fichiers `.poids`, sans carte) : les `.poids` de
  `traces-120b.tar.xz` et `traces-20b.tar.xz` ; simulation d'un cache à niveaux (exact / rapide), LFU(h*)
  de P1 si P1 tient, sinon LFU 8 ; règles de remontée « accepter » et « remonter à θ' ».
  Variante B, préremplissage : masse agrégée d'un expert dans le lot (somme des poids des jetons qui
  l'appellent) au lieu du poids d'un seul appel ; vivant #3 mesure que 14 % des experts touchés d'un
  préremplissage de 512 jetons du 120b ne portent que 1,2 % des affectations (≈ 7,5 Go, ≈ 2,7 s) [mes.].
- Étape 1 (après levée du verrou) : KL de bout en bout au 20b, 10 fenêtres, θ = 0,20 et 0,25, avec
  le fichier `<nom>.rapide.trc` du lot B (8,31 Go) et la substitution f64 (`juge reference`) ou le
  moteur ; l'arrêt séquentiel (§ 5) réduit les passes.
- Seuil : étape 0 : r(θ) ≤ 0,7 à θ = 0,20 avec ≥ 8 % d'octets économisés, remontées comprises ;
  étape 1 : KL excédentaire ≤ 0,022 pour ≥ 8 % d'octets en moins ; mort si r > 0,9 ou KL > 0,040.
- Témoins : θ = 0 redonne le tout-exact, θ = 1 le tout-rapide (−28 % d'octets) ; cassure : poids
  mélangés entre positions, r(θ) monte à environ 1 ; second chemin : la mesure d'octets de physique
  redonnée à 1e-3 par la nouvelle simulation sans remontée.
- Durée et mémoire : étape 0 ~30 min, RAM < 1 Go ; étape 1 : 10 fenêtres × 2 θ, au moins ~1 h
  de processeur par passe selon la voie.

**Ce qui pourrait être faux.** « La masse n'est pas la KL » (humain E2). La proportionnalité KL ∝ g²
est une hypothèse ; si les poids plats (0,349 / 0,253 / 0,211 / 0,187 par rang) ne portent aucune
information d'importance, le portillon ne vaut pas un tirage au hasard et r(θ) le dira dès l'étape 0.

---

## 3. Ordre de lancement conseillé

| Ordre | Piste | Pourquoi ici | Besoin de la carte ou du verrou levé |
|---|---|---|---|
| 1 | P1 | décide si le LFU entre dans le moteur ; sa réponse alimente P2 et P6 | non |
| 2 | P2 | le plus grand gain chiffré ; indépendant de P1 mais mieux avec | étape moteur seule |
| 3 | P4 (traces) | passe sur les mêmes traces, simulateur réutilisable | non |
| 4 | P6 étape 0 | mêmes traces, `.poids` | non |
| 5 | P5 étape 1 | captures sur disque, sans modèle | non |
| 6 | P3, P5 étape 2, P6 étape 1 | les trois qui se jugent à la KL | oui |

---

## 4. Écartés, et pourquoi

| Candidat | Éclaireur | Raison de l'écart |
|---|---|---|
| Noyaux de mémoire physiques (Omori-Utsu, Kohlrausch, deux temps) | physique #4, Terre #7, humain #8 | **Fermé par la mesure** E1 (+0,0051 / +0,0028 / +0,0044 contre +0,015) ; la forme ne compte pas, la demi-vie compte (gardé dans P1) |
| Barrière de nucléation, admission par seuil | physique #5 | Fermé par E3 (−0,0012) |
| Coupure de Fermi (retrait de l'expert de poids faible) | physique #6 | Fermé par E2 (0,09 % des défauts sous 0,05) ; le portillon vers la base est P6 |
| Réseaux de tenseurs, jauge de permutation, holographie, Landauer, criticité | physique #7 | Gains nuls ou sous 0,015 bit en tous les cas chiffrés ; propriété (a). Le test de Van Loan sur 13 Mo n'est pas fait : à greffer sur la lecture des 8 experts de P5 si elle a lieu, sans compter comme piste |
| Métrique de sortie par les routeurs aval (K-FAC côté sortie) | physique #2 | Utile comme proxy de KL (Spearman 0,94 déjà par l'erreur brute) ; instrument, pas piste. À greffer sur P5 si le juge KL est trop lent |
| Prédicteur de compression, éviction à prochain usage prédit | mathématiques #4 | Mesuré : +0,0124 contre le meilleur LFU réglé, sous le seuil PROBABLE de +0,05 ; l'oracle d'un jeton ne rend que +0,0469 |
| Vérification groupée, brouillon sous-modulaire | mathématiques #5, vivant #6 | **Tuée** : G(4) = 1,44, G(8) = 1,84 pour un brouillon gratuit ; au coût du mode rapide, gain calculé sous 1 |
| Lissage de Maslov du top-k | mathématiques #6 | Plancher de 0,73 sur l'énergie d'erreur de bascule ; neutre au mieux |
| Codes à effacement contre les retards du disque | mathématiques #7 | octets × n/k sur un goulot de bande passante |
| Talus, convexification | mathématiques #8, ingénierie #7 | falaise franchie au budget de la base (Proposition 1) |
| Raffinement successif emboîté (Slepian-Wolf trivial) | mathématiques #3 | Valeur basse après M2 ; **repris dans P6** comme motif du format emboîté, mesure de H(exact | rapide) sur 2 à 3 experts réservée à qui touchera au format |
| Mémoire épisodique clairsemée (circuit olfactif) | vivant #2 | Rappel +7,2 points au seul 20b/6, plus rien à 20 % ; éviction pilotée 0,2 à 1,4 % de défauts de plus qu'un LFU réglé. Le prédicteur sert de variante à P4 |
| Queue de Pareto du préremplissage | vivant #3 | **Repris dans P6** (variante B) : même pipeline KL |
| Synergies motrices | vivant #4 | n'ajoute rien à un LFU réglé et perd 4 à 15 % sur le code |
| Fovéation par poids, Charnov, polymérase en pause, modulation par la surprise | vivant #5, #7 | quatre tués par les nombres (§ 7 de vivant) ; la fovéation par poids vit dans P6 |
| Eau-filling inverse par l'usage | Terre #2 | **Écartée de justesse** : gain réalisé 0,094 bit en LRU 20b contre un seuil de 0,126, 0,16 à 0,24 bit en LFU, et la moitié probable après la KL ; elle utilise la même chaîne KL que P5 et P6 et s'y greffe après eux. Reste la meilleure piste de compression non retenue |
| Climatologie (vecteur moyen par expert) | Terre #3 | Probabilité de passer faible (les biais exacts laissent déjà ~100 % d'erreur) ; test gratuit si P5 lit déjà les 8 experts, sinon laissé |
| Phase de marée | Terre #4 | +0,4 à +0,6 point au 20b, +0,1 au 120b ; sous +1,0 ; entre comme comparateur ETR dans P1 |
| COLA, parareal, onde P | Terre #5 | Aucun octet retiré ; le préchargement cache la latence (plafond de P4) |
| Allocation hydraulique, METRIC, Charnov | Terre #8, humain #7, vivant #7b | Fermé : la LFU globale fait déjà l'allocation par utilité marginale |
| BOLA (contrôle de fidélité à tampon) | humain #3 | Non mesurable avant que P6 fournisse KL(f) ; à reprendre alors. Il n'existe aucune source reliant ce cadre au déchargement d'experts, ce qui le rend à garder en vue |
| Arrêt séquentiel O'Brien-Fleming | humain #4 | **Instrument**, pas piste ; recommandé pour toutes les passes KL de P3, P5, P6 (§ 5) |
| Routage conscient borné par la marge (humain) | humain #5 | Fusionné dans P3 |
| Tri par poids | humain #6 | Fermé pour gpt-oss (poids plats) ; sa forme « vers le rapide » est P6 |
| ACT-R, classes ABC | humain #8, vivant #1 | La loi de puissance ne bat pas un LFU réglé ; les classes d'usage ne voyagent pas d'un genre à l'autre |
| Éviction qui connaît l'avenir proche | ingénierie #2 | Le prédicteur d'avenir est celui de P4 ; la rétention guidée est le bras R de P4 |
| Segments avec listes fantômes (ARC, S3-FIFO) | ingénierie #3 | Le SLRU à probatoire de 20 % s'effondre (0,257 contre 0,738) ; prior contre ; à reprendre seulement si P1 est non concluant |
| Cache en forme codée | ingénierie #5 | Dominé par P2 (−8 % d'octets pour 120 ms de carte par jeton) |
| Précision décidée par appel sur le résidu | ingénierie #6 | Fusionné dans P6 |

---

## 5. Instruments partagés

- **Arrêt séquentiel de groupe** (humain E6, constante c = 2,840 calibrée par Monte-Carlo ; O'Brien et
  Fleming, Biometrics 35, 1979 [rel.]) : 6,8 fenêtres sur 10 en moyenne sur cinq séries décisives
  [mes.], un tiers des passes de référence évitées. À utiliser avec un **plancher de 6 fenêtres** :
  R1 λ = 0 contre λ = 1 franchissait la frontière à 4 fenêtres (t = −5,1) et n'était plus décisive à 10
  (t = −2,1).
- **Règle d'appariement du lot R** : meilleure si d̄ + 2σ(d̄) < 0, σ par blocs de fenêtres.
- **Séparer préremplissage et génération dans tout jugement de cache.** Les politiques d'admission
  gagnent en lecture (+0,081) et perdent en génération (−0,094) (ingénierie H3 [mes.]) ; c'est le piège
  commun.

---

## 6. Carte monde vers pipeline (pour le Tome III)

Étages du pipeline : **F** format `.trc` et codage entropique ; **Q** choix des symboles et quantification ;
**K** cache d'experts ; **R** routage ; **L** lecture, ordonnancement, préchargement ; **J** juge et méthode.
Verdict : **retenu** (piste), **mesuré tenu**, **fermé** (par la mesure citée), **non mesuré**.

| Concept du monde | Échelle ou domaine | Étage | Verdict | Preuve |
|---|---|---|---|---|
| Réservoir lent et rapide (climat stochastique, Hasselmann) | climat | K | retenu P1 | vivant `lfu-longue-memoire-contre-lru.json` ; Terre `lfu-demivie-*.json` |
| Oubli en loi de puissance (ACT-R) | psychologie | K | retenu P1 (demi-vie), forme fermée | humain `e1b-*.json` |
| Répliques sismiques (Omori-Utsu), processus de Hawkes | sismologie | K | fermé | physique `e1/`, Terre `gaps-*.json` |
| Marées, phase périodique de la couche | géophysique | K | petit gain, comparateur de P1 | Terre `phase-120b-reduit.json` |
| Hiérarchie exclusive (démotion) | stockage | K | retenu P2 | ingénierie `h1.csv`, `h2.csv` |
| Cache compressé | architecture | K | dominé par P2 | ingénierie `indicatif-cache-code.csv` |
| Nucléation, barrière de germe | thermodynamique | K | fermé | physique `e3/` |
| Talus, enveloppe convexe | systèmes | K | fermé | ingénierie `temoins.csv`, mathématiques `m1_m2.json` |
| Segments, listes fantômes (ARC, S3-FIFO) | systèmes | K | non mesuré, prior contre | ingénierie `h3-*.csv` |
| Allocation par utilité marginale (Charnov, hydraulique, METRIC) | écologie, hydrologie, logistique | K | fermé | Terre `alloc-lfu-t20b.json` ; humain `e3-20b.json` |
| Admission par fréquence (TinyLFU) | systèmes | K | fermé en génération | ingénierie `h3-*.csv` |
| Faille collante, friction à vitesse et état | sismologie | R | retenu P3 | mathématiques `m3_marges_20b.json` |
| Substitution d'article, deux choix | commerce, files | R | retenu P3 | humain `e7-marge-20b.json` |
| Hypersurface tropicale, marge de top-k | mathématiques | R | garde globale fermée ; marge comme bande dans P3 | 05 § 3.1, JUGEMENT |
| Lissage de Maslov | mathématiques | R | fermé | mathématiques `maslov_jouet.json` |
| Cascades de branchement (ratio 0,59, Galton-Watson) | probabilités | R | descriptif, non actionnable | physique, calcul sur `garde-tropicale.md` |
| Prédiction conforme | statistique | L | retenu P4 | humain `e4-*.json`, `e4b-*.json` |
| Jurisprudence, raisonnement par cas | droit | L | retenu P4 (prédicteur) | humain `e4-*.json` |
| Circuit olfactif de la mouche | neurosciences | L | variante de P4 | vivant `ek-verdict.json`, `el-verdict.json` |
| Synergies motrices | neurosciences | L | fermé | vivant `ed-verdict.json`, `ej-verdict.json` |
| Trafic d'arrière-plan qui cède (TCP Nice, LEDBAT) | réseaux | L | retenu P4 | ingénierie, non mesuré |
| Parareal, COLA, onde P | simulation, séismes | L | fermé (aucun octet) | Terre `eclaireur.md` |
| Vérification groupée, union des experts | information | L | fermé | mathématiques `plafond_speculatif.json` |
| Codes à effacement | information | L | fermé | calcul |
| Contrôle à tampon (BOLA) | vidéo | L | non mesuré, après P6 | humain `eclaireur.md` |
| Occupation de Fermi, portillon | physique | R, L | retenu P6 | physique `e2/portillon-de-poids.json` |
| Fovéation, triage, queue de Pareto | vision, médecine, économie | L | P6 (variante B) | vivant `ee-verdict.json` |
| Raffinement itératif en précision mixte | calcul scientifique | Q, L | P6 | ingénierie |
| Verre de spin, recuit, échange de répliques | physique des désordres | Q | retenu P5 | physique `eclaireur.md` (non mesuré) |
| Eau-filling inverse par l'usage | théorie du débit-distorsion | Q | non retenu, à greffer | Terre `eau-usage-t*.json`, `temoins-eau.json` |
| Climatologie, krigeage | météorologie, géostatistique | Q | non mesuré | Terre `eclaireur.md` |
| Réseaux de tenseurs, holographie, Landauer | matière condensée, thermodynamique | F, Q | défavorable, fermé | physique `annexe-poids-jauge-landauer.json` |
| Raffinement successif (Equitz et Cover) | théorie de l'information | F | non retenu (valeur basse) | mathématiques `eclaireur.md` |
| Graine, génome, duplication, hebbien, spectres | biologie | F, Q | fermé (05 § 2) | 05-synthese |
| Arrêt séquentiel de groupe | essais cliniques | J | instrument | humain `e6-sequentiel.json` |

---

## 7. Ce qui pourrait être faux

- **Je n'ai pas relu les sources externes**, seulement les rapports des éclaireurs et les fichiers
  nommés au début. Une affirmation marquée [rel.] vaut ce que vaut son relais.
- **Mon classement n'est pas mesuré.** « Gain × nouveauté × faisabilité » est un jugement d'ordre ; deux
  pistes que j'écarte (eau-filling inverse, BOLA) pourraient valoir plus que P4 ou P5 une fois chiffrées.
- **Les traces de génération sont deux, de 256 jetons.** P1, P2 et P4 en dépendent ; leur seuil de
  mort est écrit pour qu'une réponse « non concluant » soit possible et dite.
- **Un facteur commun possible** : les taux de succès simulés (0,74 en génération) dépassent le taux
  mesuré du moteur (0,59). Tout gain simulé est à lire comme borne haute avant l'ABBA dans le moteur.
- **L'ordre de P6 contre P3** : l'une fournit la pente (KL par octet) que l'autre utilise comme barre.
  Si P6 échoue, P3 perd sa barre et il faudra en poser une autre avant de lancer ses passes lourdes.
- Le verrou de la carte empêche aujourd'hui toute lecture lourde de fichier modèle : les durées des
  étapes qui en dépendent sont des estimations d'éclaireur, non des mesures.
