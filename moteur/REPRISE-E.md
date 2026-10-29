# Reprise du lot E (chemin des octets)

Lot E : `moteur/crates/trc-cuda/**`, `moteur/crates/trc-es/**`, `moteur/bins/banc-chemin/**`,
journaux et outils sous `mesures/moteur/E/**`. Spécification : `decisions/ARCHITECTURE.md` § 5.5
(couture C), § 6.1, § 6.5 (E0, E2).

## Critères déclarés avant tout lancement (2026-10-15)

### E1 (`trc-cuda`, `trc-es`) — le § 6.5 n'en donne pas ; déclarés ici, réversibles

Spécification incomplète : le tableau du § 6.5 n'a pas de ligne E1. Réponse par délégation du
2026-10-15, réversible ; raison : chaque étape finit par témoin, cassure et seuil (SOCLE).

| Témoin | Cassure | Seuil |
|---|---|---|
| aller-retour hôte → carte → hôte, 4 tailles non rondes, décalages non nuls : octets égaux | un octet de la VRAM retourné entre les deux copies → exactement 1 écart | 0 écart |
| deux flux ordonnés par un événement : le retour voit l'aller entier | sans l'attente, la course se voit au moins 1 fois sur 20 | 0 écart avec l'attente |
| noyau PTX écrit à la main, chargé par `Module`, lancé par `Fonction` : sortie = `a·i + b` ; le même noyau écrit dans une mémoire hôte projetée | (la sortie est comparée à un attendu recalculé ; un PTX faux est refusé avec son journal) | 0 écart |
| `Lecteur` : 12 lectures de 1 Mio, profondeur 2 (file interne), page par page égales au motif ; dernière page partielle ; refus des requêtes non alignées ; abandon en vol sans faute ; soumission et récolte sur deux fils | attendu décalé d'une page → > 99 % d'octets faux ; un octet faussé → exactement 1 écart | 0 écart |
| débit du `Lecteur` sur le GGUF de gpt-oss-20b, lectures de la taille d'un tronçon (12 Mio), QD 4 | — | ≥ 0,8 × 2,58 = **2,06 Go/s** (2,58 : 4 Mio aléatoire QD 4 [mes. 01] ; 0,8 = 1 − 2 × 10 % de bruit, règle du § 6.5) ; mesure sur secteur, verrou de la carte non nécessaire (disque seul) |

### E1, débit du lecteur sur le disque seul (`banc-chemin lecteur`), déclaré le 2026-10-15 à ~~15 h 25~~ 15 h 20 (commit 1cca7f3), avant toute passe mesurée

Raison : la carte est tenue depuis 12 h 09 par `traceur.exe` (autre agent) ; le débit du lecteur ne
touche pas la carte, il se mesure sans elle (mémoire `VirtualAlloc` ; une lecture sans tampon
verrouille elle-même ses pages). Réponse par délégation du 2026-10-15, réversible.

| Grandeur | Seuil | Source du seuil |
|---|---|---|
| débit, 12 Mio, QD 4 (passes A), 128 lectures par passe, ABBA × 2 (A = QD 4, B = QD 1) | médiane des passes A **propres** ≥ **2,064 Go/s** | 0,8 × 2,58 [mes. 01], règle du § 6.5 |
| passe **propre** | octets étrangers (compteur brut PDH de toute la machine − nos octets) ≤ **0,26 Go/s** pendant la passe | 10 % de 2,58 : le bruit de lecture admis [mes. 01] ; au-delà, un autre programme prend une part du disque plus grande que le bruit |
| verdict | « tient » / « tombe » seulement sur au moins **2 passes A propres** ; sinon « non jugé » (jamais « tombe » sur une machine chargée) | — |
| témoin du compteur | octets du système ≥ nos octets, à chaque passe | nos lectures sans tampon vont au disque : le compteur doit les voir |
| témoin de justesse | 4 lectures égales à `std::fs` octet pour octet ; cassure `--casser` : exactement 1 écart | 0 écart |
| bruit | écart relatif entre passes miroirs (A1 / A2, B1 / B2) | règle de 06 § 7.5 pour comparer QD 4 à QD 1 |
| second chemin | loi de Little, X = q · b / R (profondeur, taille, latence médiane) | doit tomber à 10 % du débit du mur, ou dire pourquoi |

Essais de justesse courts faits à ~~15 h 22~~ 15 h 18 (machine chargée, chiffres non publiables) : justesse 0 écart,
cassure 1 écart ; repos de la machine sans nous : **0,64 à 0,98 Go/s** ; le compteur voit toujours
au moins nos octets (8 passes sur 8).

**Séance 1 (`e1-2026-10-15-seance1`, 15 h 39, une tentative, règle 1) : E1 TOMBE sous la règle
déclarée.** Passes A (QD 4) : 0,846 / 1,407 / 1,548 / 1,506 Go/s ; trois propres au sens de la
règle 1 (octets étrangers 0,125 / 0,231 / 0,102 Go/s ; la deuxième, 0,362, est sale) ; médiane des
propres **1,506 Go/s < 2,064**. Passes B (QD 1) : 1,105 / 1,137 / 1,241 / 1,037. Témoins : justesse
0 écart, compteur ≥ nos octets 8/8, 0 erreur. Bruit miroir des A : 50 % (A1 lente, première
passe). Repos de la machine sans nous : 0,136 Go/s lus. Ce que la règle 1 ne regardait pas : le
processeur. Relevé juste après (~~15 h 50~~ 15 h 40) : **69 à 84 %** de la machine occupée (juge f64 du lot R
355 %, traceur 186 %, Defender 161 %, lualatex) ; BitLocker déchiffre chaque octet lu sur le
processeur (01 § 2.7). Le verdict reste publié tel quel ; il dit que **sous cette charge** le lecteur
ne tient pas 2,06 Go/s, pas qu'il ne le tient pas au calme. Le pilote est mort après la tentative 1
sur l'effacement du verrou (fichier encore ouvert : WinError 32) ; le verrou restant (le nôtre) a été
retiré à la main à 15 h 40 ; défaut corrigé dans les deux pilotes.

**Règle 2, déclarée le 2026-10-15 à ~~15 h 55~~ 15 h 43 (commit a34774f), avant la séance 2** (réponse par délégation,
réversible) : une passe est propre si, en plus, les autres programmes occupent **≤ 40 %** du
processeur pendant elle (`GetSystemTimes` − `GetProcessTimes` du banc ; le pilote attend aussi un
processeur ≤ 40 % sur 3 s par le compteur brut `Win32_PerfRawData_PerfOS_Processor`). Source du
seuil : 01 § 2.3, gros blocs reproductibles à quelques % sous 35 à 40 % d'occupation, bruits de 50 à
130 % sous 90 à 100 %. Le reste de la règle 1 ne change pas.

### E0 (les trois essais du § 6.5), seuils du § 6.5 recopiés tels quels

- **(a)** `cuMemHostAlloc` de 0,25 / 1 / 4 / 11 Go. **Choix prudent** (réponse par délégation du
  2026-10-15, réversible ; raison : cinq lots compilent sur 16 Go, une épingle de 11 Go ferait
  paginer les autres) : une taille n'est tentée que si la RAM disponible (GlobalMemoryStatusEx)
  dépasse la taille + 1,5 Go ; sinon elle est journalisée « non tentée » avec la RAM disponible.
  Journal : succès, durée d'allocation, durée de libération, RAM disponible avant et après.
- **(b)** `ReadFile` sans tampon (`trc-es`) dans la mémoire épinglée, puis DMA vers la VRAM, retour
  vers l'hôte : octets égaux à une lecture indépendante du même intervalle (`std::fs`, avec le cache
  de Windows). Cassure : un octet faussé dans la mémoire épinglée après la lecture → détecté.
  Seuil : DMA ≥ **11,0 Go/s** (12,2 [mes. 01] − 10 %), série ABBA (12 Mio, taille d'un tronçon, et
  64 Mio, taille de la mesure de 01), verrou de la carte, sur secteur.
- **(c)** 36 synchronisations par jeton (événement + boîte aux lettres projetée) : coût ≤ **15,7 ms
  par jeton** (10 % du temps disque d'un jeton, LRU calé ; partisan-A étape 0b). Coût = temps par
  jeton de la chaîne synchronisée − temps de la même chaîne sans attente de l'hôte. Témoins : les
  indices lus par l'hôte égaux à l'attendu (et revérifiés par la carte) ; temps de la carte ≤ temps
  du mur. Cassure : lecture de la boîte sans attendre → indices faux comptés.

### E2 (`banc-chemin chemin`, § 6.5 E2 et critère C2 du § 7.1), déclaré le 2026-10-15 à ~~20 h 50~~ 20 h 43 (commit 6b59ff3 ; heure d'abord écrite de tête, corrigée), avant toute ligne de code d'E2 et toute passe

Le chemin mesuré est celui du § 5.1 : lecture IOCP sans tampon d'un tronçon entier (`longueur0`,
une requête) dans la fenêtre épinglée, DMA sur le flux de copie vers un tampon d'arrivée en VRAM,
attente par événement, décodage K1 (`Noyaux::decoder_expert_grilles`, grilles lues dans la partie)
sur le flux de décodage dans un emplacement SoA. Profondeur 4 (k de gpt-oss), 6 emplacements
(profondeur + 2 : les lectures restent 4 en vol pendant que deux emplacements sont à la carte).
Ordre : une permutation des 768 experts tirée d'une graine publiée, nouvelle à chaque passe
(accès aléatoire à la taille d'un expert, comme le moteur).

| Grandeur | Témoin | Cassure | Seuil (et sa source) |
|---|---|---|---|
| **C2, transport exact** (passe témoin : chaque emplacement redescend vers l'hôte) | pour **les 768 experts** : empreinte64 de l'expert remis dans la disposition d'origine (§ 4.11) = `empreinte_origine` du répertoire ; en plus, empreinte64 des octets utiles arrivés dans la fenêtre épinglée = `empreinte_niveau[0]` (le transport disque seul) ; compteurs de contrôle de la carte nuls (voies hors de L, format, pointeurs) | **une copie du fichier où 12 bits sont retournés dans 12 experts tirés d'une graine** (`banc-chemin casser-copie`), un par sorte de région : MEDIANES, BIAIS, mots, états et débuts de tuile de DELTA et de CODES_CTX, en-tête du flux CODES_CTX (P), table des flux (sorte), magie et identité (couche, expert) de l'en-tête de partie | **0 écart** sur le vrai fichier ; sur la copie : **les 12 experts détectés (100 %), aucun autre** (« détecté » = au moins un des contrôles du témoin tombe ; chaque contrôle est publié à part, et ce qu'en voit le mode de production, qui n'a que les compteurs de la carte) |
| **débit de bout en bout** (passes A : production, aucun retour vers l'hôte, compteurs relus en fin de passe et nuls) | « débit ≤ min des étages » : médiane des A ≤ **1,10 ×** le plus petit des trois étages mesurés dans la même séance (disque seul : passes B, mêmes lectures, même fenêtre ; DMA seule : 768 copies des longueurs réelles, événements ; décodage seul : 768 décodages de parties résidentes en VRAM, événements) ; 1,10 = 1 + 10 % de bruit de la lecture [mes. 01] ; au-delà, l'instrument est faux (cache, horloge) | — (la cassure de ce témoin est la passe B elle-même : un A au-dessus de 1,10 × B tomberait) | médiane des passes A **propres** ≥ **0,8 × 2,58 × r(F1) = 2,2815 Go/s d'experts servis**, comptés à la taille d'origine (13 253 760 o par expert) sur le temps du mur, de la première soumission à la fin du dernier décodage ; r(F1) = 13 253 760 / 11 990 368 = 1,10537 (§ 4.14) ; 0,8 = 1 − 2 × 10 % [mes. 01] (§ 6.5) |
| série | A (bout en bout) B (disque seul) B A, × 2 tours ; chaque passe sert les 768 experts (9,23 Go de tronçons) | — | — |
| passe propre | règle 2 d'E1, telle quelle : octets étrangers ≤ 0,26 Go/s et processeur des autres ≤ 40 % pendant la passe | — | verdict « tient » / « tombe » sur **au moins 2 passes A propres**, sinon « non jugé » |

Ce que le fichier réel change au seuil, dit avant : ses tronçons font 12 013 664 o en moyenne
(répertoire, relu juste avant ce commit), soit r = 1,10322 et non 1,10537 ; le seuil reste celui de la
spécification (2,2815 Go/s servis), ce qui revient à 2,068 Go/s de tronçons lus, 0,2 % au-dessus
du seuil d'E1 (2,064). Prédiction écrite avant la mesure, non jugée : le disque limite (≈ 4,9 ms
par tronçon contre ≈ 1 ms de DMA et ≈ 0,35 ms de décodage), d'où A / B entre 0,95 et 1,00 et
≈ 2,44 × 1,103 ≈ 2,7 Go/s servis si la machine est aussi calme qu'à 20 h 40.

Conditions : secteur (BatteryStatus = 2, relevé avant et après), aucun llama-*, verrou de la carte
pris par le pilote, processeur et disque calmes (comme le pilote d'E1).

## État

- 2026-10-15 : `trc-cuda` et `trc-es` écrits, construits dans un espace privé
  (`~/dev/cibles/troncons-E/miroir`, dépendances par chemin) parce que l'espace commun
  tombe tant qu'un dossier d'un autre lot n'a pas son Cargo.toml.
- Machine relevée à 12 h 40 : **sur batterie** (BatteryStatus = 1), 245 Mo de RAM libre, carte
  occupée par `traceur.exe` (gpt-oss, autre agent, 7,5 Gio de VRAM). Aucune mesure de débit possible.
- 2026-10-15 13 h : essais de justesse courts (sans verrou, sur batterie puis secteur, machine
  chargée ; chiffres NON publiables, seulement des preuves que l'instrument marche) : (c) toutes les
  variantes rendent 0 indice faux, la cassure `sans_synchro` en rend 855 sur 864 ; (b) 0 écart sur
  4 morceaux, la cassure rend exactement 1 écart ; (a) rien tenté (0,78 Go disponibles).
- Fait de la machine [mes.] : `ASYNC_ENGINE_COUNT` = 1 (un seul moteur de copie sous WDDM). Premier
  témoin d'ordre (copie aller contre copie retour) n'a jamais vu la course : même file FIFO. Refait
  avec un noyau qui lit la VRAM : la cassure tombe (66 393 069 octets faux sur 67 108 864).
- Séance E0 complète : `pilote_e0.py --seance 2026-10-15-seance1` lancé en arrière-plan à 12 h 54, il
  attend que la carte se libère (llama-perplexity et traceur.exe d'autres agents).

- 15 h 06 (reprise par un nouvel agent) : prédécesseur mort après 13 h 25 ; son pilote E0
  (seance1) mort avec lui, sans journal (dossier vide). Arbre propre côté lot E. Carte tenue par
  `traceur.exe` (gpt-oss-120b, depuis 12 h 09, 7,4 Gio de VRAM), `llama-perplexity` d'un autre
  agent, 0,5 Go de RAM libre, disque lu à 0,2 à 1,0 Go/s par les autres. Secteur (2).
- 15 h 08 : construction commune tombait sur le build.rs de banc-chemin (`file!()` relatif à la
  racine de l'espace de travail, chemin doublé) ; corrigé, l'espace commun construit banc-chemin.
- 15 h 11 : **E1, témoins** : 10 tests sur 10 tiennent (journal `e1-temoins/2026-10-15-1510.txt`) ;
  **témoin des témoins** (`temoins_des_temoins.py`, `TRC_E_CASSER`) : 7 cassures sur 7 tombent sur
  le message du témoin visé, la suite restaurée tient (`e1-temoins/2026-10-15-cassures.json`).
- ~~15 h 25~~ 15 h 20 : `banc-chemin lecteur` (E1 débit, disque seul, sans la carte) + compteur brut PDH des
  octets de toute la machine (aussi dans l'essai b) ; seuils et règle de propreté déclarés plus haut
  avant toute passe mesurée ; essais de justesse (0 écart, cassure 1, compteur ≥ nos octets 8/8).
- 15 h 24 : deux pilotes lancés en arrière-plan : `pilote_e1.py --seance e1-2026-10-15-seance1`
  (attend secteur, aucun llama-*, aucun verrou, disque calme) et `pilote_e0.py --seance
  2026-10-15-seance2` (attend le verrou, aucun llama-* ni traceur). Sorties :
  `mesures/moteur/E/journaux/pilote-e{0,1}-*.sortie.txt`. Analyse : `analyse_e1.py`, `analyse_e0.py`.

- 15 h 46 : heures corrigées dans cette note (barrées) : j'avais écrit des heures estimées, pas
  lues ; les bonnes sont celles des commits. Aucune mesure n'en dépend (l'ordre « déclaré avant
  lancement » tient : 1cca7f3 à 15 h 20 avant la séance 1 à 15 h 39 ; a34774f à 15 h 43 avant la
  séance 2). Pilotes relancés à 15 h 43 : `pilote_e1.py --seance e1-2026-10-15-seance2` (règle 2) et
  `pilote_e0.py --seance 2026-10-15-seance3` (la séance 2 d'E0 a été arrêtée par moi en attente, sans
  rien mesurer, pour recharger le correctif du verrou).

- **16 h 46 à 16 h 48 : séance E0 complète (`2026-10-15-seance3`)**, sur secteur (2 du début à la
  fin), aucun llama-* ni traceur (traceur fini vers 16 h 45), verrou pris par le pilote à 16 h 46 47
  (celui du lot K, pris à 16 h 46 34, avait été rendu à 16 h 46 46 : pas de recouvrement, vérifié
  dans `mesures/moteur/K/.../interrompu-20261015-1646/attente-pilote.log`), VRAM 439 Mio avant
  chaque passe. Analyse : `journaux/2026-10-15-seance3/resume.json`, CSV `csv/2026-10-15-seance3-*`.
  - **(a) TIENT jusqu'à 4 Go, 11 Go NON TENTÉ** : 0,25 / 1 / 4 Go épinglés en 96 / 343 / 1 331 ms,
    libérés en 46 / 133 / 594 ms (≈ 0,33 s par Go à l'allocation), DMA depuis la fin de chaque
    allocation 10,36 / 10,93 / 11,00 Go/s (une copie de 64 Mio, sans chauffe), 0 écart ; 11 Go non
    tenté : 8,29 Go disponibles < 11 + 1,5 (la marge déclarée). K3 (abandon) ne se déclenche pas.
  - **(b) TIENT** : justesse 32 morceaux de 12 Mio, 0 écart disque, 0 écart disque → VRAM → hôte ;
    cassure 1 écart (attendu 1). **DMA 12 Mio : médiane 12,495 Go/s** (16 passes ABBA, 12,33 à
    12,67, bruit miroir 1,4 %) ≥ 11,0 ; 64 Mio : 12,517 (bruit 1,6 %) ; second chemin (horloge de
    l'hôte) 12,45 et 12,51, jamais au-dessus des événements (0 sur 32). À 2,6 % du 12,2 de 01 :
    les deux tailles ne diffèrent pas (règle 06 § 7.5).
  - **(c) TIENT, marge ×23** : sous charge (routeur 50 µs, expert 250 µs), variante retenue
    `evenement` : **0,666 ms par jeton** (18,5 µs par synchronisation) ≤ 15,7 ; `sondage` 0,692,
    `boite` 0,750, `bloquant` (événement à attente bloquante) 3,12 ; contexte en attente
    bloquante : `evenement` 0,630. À vide : `boite` 0,158, `evenement` 0,183. Témoins : 0 indice
    faux, 0 séquence absente, 0 boîte expirée, temps de la carte ≤ mur, dans toutes les variantes ;
    cassure `sans_synchro` : 3 141 indices faux (attendu > 0). K4 ne se déclenche pas.
  - **Le témoin du modèle D2 TOMBE** (coût indépendant de la charge) : le coût sous charge est
    3,6 à 4,8 fois le coût à vide (`modele_D2` du résumé). Lecture (hyp.) : à vide, la base
    asynchrone est elle-même bornée par les lancements (11,5 µs par lancement, 72 par jeton), qui
    absorbent `d_lanc` ; sous charge la carte attend vraiment l'hôte, et le coût vaut
    `d_sig + d_hôte + d_lanc` ≈ 5 + 11,5 ≈ 16,5 µs contre 18,5 mesurés (`evenement`). D2 corrigé
    dans E-pour-le-memoire.md (D2 bis) ; le seuil se juge sur la charge, le cas réaliste.
  - Disque dans l'essai b (second chemin de E1) : QD 4 2,673 / 2,445, QD 1 2,378 / 2,264 Go/s,
    octets étrangers ≤ 0,025 Go/s, mais processeur des autres 44 à 54 % : **non jugé** (règle 2).

- 16 h 48 à 19 h 54 : pilote E1 séance 2 (règle 2) en attente, **rien mesuré** : la série
  `llama-completion` sur 120b d'un autre agent (depuis 16 h 48), disque lu par les autres à 0,3 à
  2,2 Go/s, processeur à 46-90 %. Arrêté par moi à 19 h 55 avant de rendre la main (sortie gardée :
  `journaux/pilote-e1-seance2.sortie.txt` ; aucun verrou laissé).

- 20 h 37 (reprise par un nouvel agent, vague 2) : arbre propre côté lot E ; secteur (2), carte
  libre (338 Mio, aucun llama-*, aucun verrou), processeur à 21 %, 9,07 Go de RAM libre.
- **20 h 40 : E1, débit du disque au calme (`e1-2026-10-15-seance3`, règle 2) : TIENT.** Passes A
  (12 Mio, QD 4) : 2,453 / 2,335 / 2,666 / 2,426 Go/s, les quatre propres (octets étrangers ≤
  0,145 Go/s, processeur des autres 15 à 32 %) ; **médiane 2,439 Go/s ≥ 2,064**. Passes B (QD 1) :
  2,328 / 2,285 / 2,224 / 2,383. Repos sans nous 0,064 Go/s. Témoins : justesse 0 écart (4
  lectures), compteur ≥ nos octets 8/8, 0 erreur ; secteur après la passe (2). Bruit miroir A
  13,4 %, B 2,7 % ; QD 4 et QD 1 non distincts (5,6 % < 2 × 13,4 %, règle 06 § 7.5). Loi de
  Little sur le mur : 1,08 à 1,23 (le second chemin surestime de 8 à 23 % : la latence médiane
  n'est pas la moyenne, queue longue au p90). Banc du 15 h 42 (sha256 5cb47c93…). La séance 1
  (1,506, sous charge) reste publiée telle quelle, avec sa raison.

- **21 h 13 à 21 h 15 : E2, séance 1 (`e2-2026-10-15-seance1`, pilote_e2.py, verrou du lot E,
  secteur partout, processeur des autres 6 à 12 %, octets étrangers ≤ 0,001 Go/s : les 8 passes
  propres).** Instantané des crates : ~~e85cdfa~~ 81e275b (lu dans `seance.json` ; K3 du lot K venait d'être commité, le décodeur K1 n'y change pas : `decodeur.cuh` et `commun.cuh` identiques à 7b6588a) ; banc construit à 20 h 52.
  - **C2 TIENT** : 768 experts sur 768, empreinte d'origine refaite depuis l'emplacement redescendu
    = répertoire, empreinte des octets arrivés dans la fenêtre = répertoire, 0 compteur de la carte,
    0 erreur de lecture.
  - **Cassure : le témoin TOMBE comme il faut** : copie à 12 bits retournés (graine 20261015,
    copie de 11,16 Go en 64 s), **12 détectés sur 12, aucun en trop**. Par contrôle : empreinte de
    partie 12/12 ; empreinte d'origine 11/12 (l'identité couche/expert de l'en-tête de partie ne
    change pas la sortie : D14 le prédisait) ; compteurs de la carte 9/12 en témoin et en
    production (ni MEDIANES, ni BIAIS, ni l'identité : D14 le prédisait).
  - **Débit : TOMBE** au seuil déclaré : passes A 2,120 / 2,092 / 2,186 / 2,215 Go/s servis,
    **médiane 2,153 < 2,2815** (5,6 % sous le seuil ; pire 2,092). Le verdict est celui-là.
  - **Témoin « débit ≤ min des étages » TIENT** : médiane A 1,951 Go/s de tronçons, étages : disque
    seul (B) 1,921, DMA 12,66, décodage 34,27 (0,350 ms par expert) ; A / min = 1,016 ≤ 1,10. A et
    B ne diffèrent pas (1,6 % pour un bruit de 1,6 % : règle 06 § 7.5) ; la prédiction A / B ∈
    [0,95 ; 1,00] tombe de 1,6 % par excès, dans le bruit. **Le chemin ne coûte rien au disque ;
    c'est le disque lui-même qui lit ce fichier à 1,92 Go/s**, contre 2,44 pour le GGUF 34 minutes
    plus tôt (E1, séance 3).
- **~~21 h 20~~ 21 h 16 (commit c0cfa0d ; heure écrite de tête, corrigée), hypothèses déclarées avant la mesure qui les départage** (réponse par délégation,
  réversible ; raison : tuer une idée par les nombres) : H1, le fichier `.trc` se lit plus lentement
  que le GGUF (disposition sur le disque : fragments) ; H2, le disque a ralenti entre 20 h 40 et
  21 h 14 (la copie de 11 Go écrite à 21 h 12 juste avant, travail interne du NVMe après une grosse
  écriture). Mesure : `banc-chemin lecteur` (l'outil d'E1, mêmes options que la séance 3 d'E1) en
  ABBA sur les fichiers, G T T G (G = GGUF, T = .trc), verrou, secteur. Règle : deux fichiers
  diffèrent si l'écart des médianes QD 4 dépasse 2 × le plus grand bruit miroir et 3 % (06 § 7.5).
  H1 tient si T < G ainsi ; H2 tient si G retombe sous 2,064 avec T. Second chemin de H1 : nombre
  de fragments de chaque fichier (`fsutil file queryextents`). Ce diagnostic ne change pas le
  verdict d'E2, publié tel quel.

- **~~21 h 17 à 21 h 19~~ 21 h 16 min 35 s à 21 h 17 min 10 s (heures des journaux), G T T G (`journaux/e2-diag-2026-10-15/`)** : `lecteur` QD 4, médianes des
  quatre passes : G 2,571 et 2,591 Go/s ; **T 3,039 et 3,023 Go/s** (p90 17 ms contre 22 à 28 pour
  G) ; tout propre, secteur. **H1 tombe, et à l'envers** : le .trc se lit 17 % plus vite que le
  GGUF. Second chemin : le GGUF a 2 737 fragments, le .trc 33, la copie 2 (`extents-*.txt`) ; le
  sens (moins de fragments, plus vite, latence plus serrée) est celui de l'écart. **H2 tombe**
  (G reste à 2,6 ≥ 2,064), mais ~~3 minutes~~ 1 min 30 s après la fin de la séance 1 (21 h 15 min 09 s), 3 min 30 s après la fin de la copie. Or `chemin` en mode
  disque seul lisait ce même .trc à 1,92 : l'écart est propre au chemin d'E2, pas au fichier.
- Hypothèses suivantes, déclarées avant (réponse par délégation, réversible) : H2 bis, le disque
  était encore ralenti à 21 h 14 par la copie de 21 h 12 et ne l'est plus ; H3, la manière dont E2
  lit (tronçons entiers à leur place, longueurs de 11,8 à 12,1 Mo, mémoire épinglée, un seul
  passage par tronçon) coûte au disque. Mesure dans la même fenêtre : L C C L (L = `lecteur` sur le
  .trc, C = `chemin` complet, seule sa médiane des passes B compte ici). H2 bis tient si C-B remonte
  à moins de 2 × bruit + 3 % de L ; H3 tient si C-B reste sous L de plus que cela.

- **21 h 18 min 12 s à 21 h 20 min 53 s, L C C L** : L1 3,04 à 3,09 Go/s ; C2, passes B (disque seul
  du chemin) 1,93 / 1,93 / 1,97 / 2,04, propres ; C3 et L4 chargés par un autre programme (L4 :
  processeur des autres 42 à 62 %, étrangers jusqu'à 0,29 Go/s : sale). **H2 bis tombe** (C2-B reste
  36 % sous L1, adjacent et propre) ; **H3 tient**.
- H3 décomposée, déclarée avant (réponse par délégation, réversible) : H3a la longueur des lectures
  (11,8 à 12,1 Mo, pas un multiple de 1 Mio, contre 12 Mio) ; H3b la destination (`cuMemHostAlloc`
  contre `VirtualAlloc`) ; H3c l'ordre (chaque tronçon une fois, à sa place, contre des décalages
  tirés avec remise). Première mesure, H3a : `lecteur` sur le .trc, longueur 12 582 912 (S) puis
  12 013 568 (moyenne des tronçons arrondie à 4 096 : M), S M M S ; même règle de différence.

- **~~21 h 21 à 21 h 23~~ 21 h 21 min 27 s à 21 h 22 min 03 s, S M M S (`smms-*`)** : même fichier, mêmes décalages tirés, QD 4 ;
  **S (12 582 912 o) 3,00 à 3,09 Go/s, latence médiane 16,3 ms ; M (12 013 568 o) 2,06 à 2,11 Go/s,
  latence 23,4 ms** pour moins d'octets ; tout propre. **H3a TIENT : la seule longueur de la lecture
  coûte 32 % au disque.** Les décalages étant tirés sur 4 096 dans les deux cas, ni le début ni la fin
  n'ont à être alignés plus finement : c'est la longueur qui compte.
- Balayage déclaré avant (réponse par délégation, réversible) : longueurs 12 Mio − g, g = 4, 8, 16,
  32, 64, 128, 256, 512 Kio, 1 et 2 Mio (multiples de g, pas de 2g), encadrées par S au début et à la
  fin ; `lecteur --profondeurs 4,4 --tours-abba 1 --serie 64`. Une longueur est « rapide » si sa
  médiane QD 4 ≥ 0,9 × la médiane de S. Le grain est le plus petit g dont la longueur est rapide et
  au-delà duquel toutes le sont.

- **~~21 h 23 à 21 h 25~~ 21 h 22 min 30 s à 21 h 23 min 06 s, premier balayage (`grain-*`, 12 Mio − g)** : rapides (≈ 3,0 à 3,1 Go/s,
  ≈ 16 ms) g = 0 à 128 Kio et g = 1 Mio (11 Mio) ; lentes (≈ 1,92 à 1,96 Go/s, 22 à 26 ms) g = 256
  Kio, 512 Kio, 2 Mio (10 Mio) ; 12 Mio refait à la fin : rapide. **Ma règle (« un grain ») tombe** :
  il n'y a pas de grain ; deux régimes, qui ne suivent pas l'alignement de la longueur.
- Second balayage, déclaré avant (`balayage_longueurs.py`, protocole et règle en tête du script) :
  8 à 13 Mio par 0,25 Mio, plus 12 013 568 et 12 144 640, deux répliques en ordres tirés.

- **~~21 h 24 à 21 h 28~~ 21 h 24 min 37 s à 21 h 26 min 42 s, second balayage (`journaux/e2-balayage-2026-10-15/`, CSV
  `csv/e2-balayage-2026-10-15-longueurs.csv`)** : 23 longueurs × 2 répliques en ordres tirés, 4
  passes chacune, propres (sauf 2 passes sur 184). **Deux régimes, fonction de la seule longueur** :
  rapides (2,87 à 3,36 Go/s) 8 ; 8,25 ; 8,75 ; 9 ; 9,75 ; 10,25 ; 10,5 ; 11 ; 11,25 ; 12 ; 12,25 ;
  12,75 ; 13 Mio ; lentes (1,80 à 2,10 Go/s, latence ×1,5) 8,5 ; 9,25 ; 10 ; 10,75 ; 11,457 ; 11,5 ;
  11,582 ; 11,75 ; 12,5 Mio. Répliques d'accord sur 22 longueurs sur 23 ; la règle déclarée
  (« d'accord sur toutes ») tombe sur 9,5 Mio, entre les deux régimes (2,71 puis 2,99 pour un seuil
  de 2,77). **Les tronçons du 20b (11,29 à 11,58 Mio) tombent tous dans une bande lente ; 12 Mio
  est rapide (3,07 deux fois).** Le mécanisme n'est pas trouvé ([hyp.] découpe des transferts par
  le pilote du contrôleur ou par BitLocker, qui ne se voit pas d'ici) ; la carte est mesurée, pas
  expliquée.
- Variante E2-V12, déclarée avant (réponse par délégation, réversible ; elle ne remplace pas le
  verdict d'E2, qui reste « tombe ») : chaque tronçon est lu en une requête de **12 582 912 o**
  depuis son début (les octets en trop, au plus 0,75 Mio, appartiennent au tronçon suivant et ne
  sont pas lus par le décodeur ; la dernière lecture s'arrête à la fin du fichier, ce que
  `trc-es` admet) ; même séance, même seuil (2,2815 Go/s servis), mêmes témoins. Prédiction :
  ≈ 3,07 × 12 013 664 / 12 582 912 × 1,103 ≈ 3,2 Go/s servis.

- **E2-V12 (`e2-2026-10-15-v12`, 21 h 28 min 54 s à 21 h 29 min 48 s)** : C2 tient (768/768) ; passes A 2,827 / 2,718 / 2,840 / 2,843 Go/s
  servis, **médiane 2,834 ≥ 2,2815 : la variante tient** ; disque seul (B) 2,68 à 2,77 Go/s lus ;
  A / B dans le bruit. Prédiction 3,2 trop haute : 2,7 Go/s lus contre 3,07 au `lecteur` (décalages
  tirés) : l'écart restant n'est pas cherché. Pour juger le gain par l'ABBA et non sur deux séances à
  14 minutes l'une de l'autre, déclaré avant : série N V V N (N = `chemin` tel que spécifié, V =
  `--longueur-lecture 12582912`), mêmes conditions ; gain réel si l'écart des médianes A dépasse
  2 × le plus grand bruit et 3 %.

- **21 h 30 min 45 s à 21 h 34 min 47 s (journaux), série N V V N (`journaux/e2-nvvn-2026-10-15/`, `serie_nvvn.py`, CSV
  `csv/e2-nvvn-2026-10-15-nvvn.csv`)** : médianes A, N 2,126 et 2,142 ; V 2,811 et 2,853 Go/s
  servis ; 16 passes A propres sur 16 ; C2 tient aux quatre. **V / N = ×1,335**, écart 25 % pour un
  bruit miroir ≤ 1,5 % : distincts. N retombe sous le seuil (2,135), V le passe (2,851).
  Tronçons du 120b (répertoire relu) : 11 763 712 à 12 251 136 o (≤ 11,69 Mio) : 12 Mio les couvre
  aussi ; le balayage n'a été fait que sur le fichier du 20b.

- **E2 sur le 120b, déclaré avant** (réponse par délégation, réversible ; hors du § 6.5, qui juge E2
  sur le 20b ; utile au critère C2 de J1, défini sur le 120b) : série N V (`serie_nvvn.py --fichier
  gpt-oss-120b.trc --lettres NV --tours 1`), chacune une passe témoin puis A B B A. C2 : 4 608 sur
  4 608, 0 écart. Débit : publié contre le même seuil (2,2815), non jugé (une seule séance, pas de
  miroir N/V). Prédiction : N ≈ 2,1 et V ≈ 2,8 Go/s servis, comme le 20b (mêmes longueurs de
  tronçon, 11,22 à 11,68 Mio).

- **21 h 38 min 50 s à 21 h 47 min 09 s, E2 sur le 120b (`journaux/e2-120b-2026-10-15/`)** :
  **C2 TIENT sur les 4 608 experts, aux deux passes témoin** (empreinte d'origine, empreinte de
  partie, 0 compteur) ; N : A 2,107 / 2,019 Go/s servis (médiane 2,063), B 1,96 Go/s lus ; V12 : A
  2,892 / 2,862 (médiane 2,877), B 2,64 à 2,74 ; **V / N = ×1,39** ; décodage 0,353 ms par expert,
  DMA 11,07 Go/s ; les 4 passes A propres (le « 2/4 » de l'écran du script compte sur 4 ce qui ne
  fait que 2 passes A par séance d'un tour). Non jugé (une séance, pas de miroir), comme déclaré.
  La prédiction (N ≈ 2,1, V ≈ 2,8) tient.

### En bref (E2, pour la valeur de retour)

| Critère | Mesuré | Seuil | Verdict |
|---|---|---|---|
| C2, transport exact, vrai fichier | 20b : 768 / 768 ; 120b : 4 608 / 4 608 (deux passes) ; 20b : (empreinte d'origine, empreinte de partie, compteurs nuls), à chacune des 8 passes témoin de la soirée | 0 écart | **tient** |
| Cassure de C2 (copie à 12 bits) | 12 détectés sur 12, 0 en trop ; production : 9 sur 12 | 100 %, 0 en trop | **tombe comme il faut** |
| Débit, tel que spécifié (lecture de `longueur0`) | médiane des A propres 2,153 Go/s servis (séance 1) ; 2,135 (N V V N) | ≥ 2,2815 | **tombe** (−5,6 %) |
| Témoin « débit ≤ min des étages » | A / disque seul = 1,016 ; DMA 12,66, décodage 34,27 Go/s | ≤ 1,10 | tient |
| Variante E2-V12 (lectures de 12 Mio) | 2,834 (séance V12) ; 2,851 (N V V N) | ≥ 2,2815 | tient (publiée à côté, ne remplace pas le verdict) |

### Reste (lot E)

1. ~~**E1 débit du disque, au calme**~~ : fait à 20 h 40, tient (2,439 Go/s).
2. **E0 (a) à 11 Go** : `pilote_e0.py --seance <nom> --seulement a` quand ≥ 12,5 Go sont disponibles
   (marge déclarée) ; jusqu'ici 8,29 Go au mieux (9,07 Go libres à 20 h 37).
3. ~~E2 (vague 2)~~ : fait (ci-dessus). Reste d'E2 : **décision de l'arbitre** sur la longueur des
   lectures (point 9 ci-dessous) ; si elle est adoptée, le verdict d'E2 se rejuge sur une nouvelle
   déclaration (le présent reste « tombe »).
4. ~~**E2 sur le 120b**~~ fait à 21 h 47 (C2 tient, 4 608 / 4 608) ; reste le balayage des longueurs sur ce fichier. Texte d'origine : **E2 sur le 120b** (non demandé par § 6.5, utile à O4) : `banc-chemin chemin --fichier
   gpt-oss-120b.trc` (4 608 experts, 55,4 Go par passe : ≈ 20 s par passe au disque) ; le banc n'a
   rien de propre au 20b. Et le balayage des longueurs sur ce fichier.
5. Le mécanisme des deux régimes du disque n'est pas trouvé ; les 12 % qui restent entre E2-V12
   (2,7 Go/s lus aux décalages des tronçons) et le `lecteur` (3,07 aux décalages tirés) non plus.
6. **Disque à libérer quand Stone le veut** (hors dépôt, rien effacé par moi) :
   `~/dev/modeles/trc/casse/gpt-oss-20b-casse-E2.trc` (11,16 Go, la copie à 12 bits de
   la cassure ; son journal est `journaux/e2-2026-10-15-seance1/casser-copie.json`).
7. Figures du mémoire (E-G8 à E-G12) à tracer depuis les CSV par le rédacteur (E-pour-le-memoire.md).

## Pour l'orchestrateur et l'arbitre (coutures, spécification)

1. **§ 6.5 n'a pas de ligne E1** : critères déclarés ci-dessus (réponse par délégation, réversible).
2. **La carte n'a qu'un moteur de copie** : le « flux de copie » du § 5.1 porte aussi toute copie
   carte → hôte. Le mode `--temoin` (§ 4.12, chaque expert recopié vers l'hôte) partage la file des
   tronçons : il ne se chronomètre pas. Les logits complets d'un pas (≈ 0,8 Mo) attendent derrière
   les tronçons en vol (≤ 4 × 1,1 ms). La boîte aux lettres projetée échappe à la file (bon choix
   du § 5.6). À dire aux lots O et K ; aucune couture ne change.
3. **Signatures sûres pour des écritures asynchrones** (`Lecteur::soumettre`, `copier_vers_hote`) :
   gardées telles que gelées, contrat documenté ; proposition (non appliquée) : les marquer `unsafe`
   à la prochaine révision de la couture C.
4. **`Contexte::memoire` sans `Result`** : rend (0, 0) sur erreur du pilote ; documenté.
5. **Extensions de la couture C** (ajouts, rien d'existant changé, permis par § 6.2) :
   `Contexte::nouveau_avec(Attente)`, `attente_effective`, `attribut(Attribut)`, `synchroniser`,
   `nom`, `version_pilote` ; `Flux::fini`, `priorite` ; `Evenement::nouveau_bloquant` ;
   `MemoireCarte::tout`, `octets`, `remplir` ; `HoteEpingle::pointeur`, `octets`,
   `lire_volatil_u32` ; `copier_carte_carte` ; `Fonction::partagee_max` (plus de 48 Kio de mémoire
   partagée : le décodeur K1 à trois LUT de 16 Kio y touche) ; `Lecteur::taille`, `profondeur`.
   `Lecteur` : au-delà de `profondeur`, les requêtes attendent dans une file interne (choix
   documenté ; `en_vol` compte confiées + en attente).
6. **L'espace de travail commun tombe** chaque fois qu'un dossier de `crates/` ou `bins/` n'a pas
   encore son Cargo.toml (ou ses sources) : le lot E construit dans un espace privé hors dépôt
   (`~/dev/cibles/troncons-E/miroir`, dépendances par chemin ; `construire.bat miroir`).
7. **Construire banc-chemin exige nvcc** (son build.rs compile `noyaux/essais.cu`) : une
   construction de tout l'espace de travail se fait dans l'environnement de `vcvars64.bat` avec
   `CUDA_PATH` (comme pour trc-noyaux).
8. ~~**E2 aura besoin**~~ fait : banc-chemin prend `trc-format` et `trc-noyaux` par chemin (pas
   `trc-codec` : C2 se juge contre le répertoire, et le lot K a déjà comparé le décodeur à trc-codec
   sur les 768 experts). **`moteur/Cargo.lock` (lot O)** : les deux lignes qu'entraîne ce
   Cargo.toml ont été écrites par la construction d'un autre lot, puis commitées par moi avec lui
   (d6ff09f ; réponse par délégation du 2026-10-15, réversible ; raison : ne pas laisser l'arbre sale
   pour tous). Le banc d'E2 se construit hors de l'espace commun (`construire.bat e2` :
   `mesures/moteur/E/miroir/`, crates des autres lots prises dans un instantané `git archive HEAD`).
9. **Spécification à revoir (§ 4.7, § 5.5, § 5.8, § 6.5 E2, C5) : la longueur d'une lecture.** Sur
   cette machine, le débit d'une lecture sans tampon a deux régimes qui dépendent de la seule
   longueur (balayage de 23 longueurs en deux ordres tirés : ≈ 3,1 contre ≈ 1,9 Go/s), et **toutes
   les longueurs de tronçon du 20b sont dans une bande lente** ; le seuil d'E2 (et le plancher de C5,
   et les plafonds de 07) supposent 2,58 Go/s mesurés en blocs de 4 Mio, une longueur rapide. Lire
   `longueur0` comme le dit le § 4.7 coûte 25 % des experts servis (N V V N). **Proposition**, la plus
   prudente et réversible : le lecteur arrondit chaque requête à une **longueur rapide calibrée sur
   la machine** (ici 12 Mio couvre tous les tronçons du 20b et du 120b) ; aucun octet du format ne
   change ; coût : une fenêtre épinglée de 12 Mio par tampon au lieu de 11,58 (+3,6 %) et ≤ 0,75 Mio
   lus en trop par tronçon, déjà comptés dans le ×1,335. Autre voie, non retenue : bourrer les
   tronçons à une longueur rapide au codeur (couture F, +4,7 % de fichier, et la table rapide
   dépend de la machine). Le calibrage (`balayage_longueurs.py`) serait un pas d'installation du
   moteur. À trancher par l'arbitre ; à dire au lot O (ordonnanceur, C5).
10. **Ce que le mode de production ne voit pas** (cassure d'E2, D14) : un bit des MEDIANES ou des BIAIS
    (flux bruts) et l'identité (couche, expert) de l'en-tête de partie. Le dernier est un vrai trou :
    un répertoire qui pointerait vers le tronçon d'un autre expert serait décodé sans erreur.
    Proposition (gratuite, côté hôte, lot O ou E) : comparer les 4 octets (couche, expert) de
    l'en-tête de la partie arrivée dans la fenêtre épinglée à l'entrée demandée, avant la DMA.
11. **Défaut du build.rs de trc-noyaux (lot K)** : quand `cl.exe` est déjà dans le PATH (construction
    lancée depuis `vcvars64.bat`), il passe la commande nvcc à `cmd /C` par `Command::arg`, qui
    échappe les guillemets par des barres obliques inverses que cmd ne comprend pas (« n'est pas
    reconnu en tant que commande interne », relevé à 20 h 50 sur 81e275b). Hors de vcvars, il
    appelle vcvars lui-même et marche. Le build.rs de banc-chemin fait désormais de même ;
    `construire.bat e2` construit hors de vcvars.

## Recettes (essayées, avec leur raison)

| Recette | Marche ? | Raison |
|---|---|---|
| Charger nvcuda.dll à l'exécution (LoadLibraryExW System32 + GetProcAddress, noms `_v2` de cuda.h 13.1) | oui | aucune bibliothèque CUDA liée ; un symbole absent est nommé au chargement |
| Contexte primaire plutôt que `cuCtxCreate` | oui | `cuCtxCreate` est devenu `_v4` en CUDA 13 ; le primaire n'a pas changé |
| Champ nommé `gen` | **échec, corrigé** | mot réservé en édition 2024 ; renommé `generation` |
| Témoin d'ordre entre flux par deux copies de sens opposés | **échec, corrigé** | un seul moteur de copie : la course ne se voit jamais ; remplacé par un noyau qui lit la VRAM |
| PTX écrit à la main pour les témoins de trc-cuda | oui | témoins sans nvcc ; le pilote compile à la volée (PTX 8.0, sm_89) |
| Construire dans l'espace de travail commun | **échec, contourné** | il tombe dès qu'un autre lot crée un dossier sans Cargo.toml ; espace privé par chemins |
| `tasklist` lu en UTF-8 par le pilote Python | **échec, corrigé** | sortie en page de code OEM (0xFF dans les tailles) ; `encoding="oem"` |
| Sortie d'un essai coupée par `| head` | **échec** | le processus meurt de SIGPIPE avant d'écrire son journal ; toujours lire le journal, pas l'écran |
| Attente active par `%globaltimer` (ns) dans les noyaux d'essai | oui | durée indépendante de l'horloge du moment de la puce |
| `file!()` dans un build.rs pour trouver un source voisin | **échec, corrigé** | relatif à la racine de l'espace de travail, pas au paquet : chemin doublé ; `CARGO_MANIFEST_DIR` |
| Témoin des témoins par variable d'environnement (`TRC_E_CASSER=<nom>`) | oui | chaque témoin forcé à faux un par un, l'échec vérifié sur son propre message ; 7 sur 7 |
| Octets étrangers par le compteur PDH **brut** (différence de deux cumuls) | oui | exact sur l'intervalle, sans intégrer ; témoin gratuit (le système voit au moins nos octets, 20 passes sur 20) |
| Juger le disque sur les seuls octets étrangers (règle 1) | **insuffisant** | le processeur chargé (BitLocker déchiffre sur lui) borne le disque : 1,5 Go/s sous 69-84 % ; règle 2 ajoute le processeur |
| `os.remove` d'un fichier encore ouvert par `with open` | **échec, corrigé** | Windows refuse (WinError 32) ; lire, fermer, puis effacer |
| Heures écrites de tête dans la note | **échec, corrigé** | décalées de 5 à 12 min ; les heures se lisent sur les commits ou les journaux |
| Mesurer la synchronisation à vide seulement | **trompeur** | à vide la base est bornée par les lancements (11,5 µs) : coût 4 fois plus bas que sous charge ; juger sous charge |
| `boite_sans_vidage` (sondage sans `cuStreamQuery`) | marche ici (0 expiration) | ordonnancement matériel de WDDM actif (`HwSchMode` = 2, relevé dans le registre le 2026-10-15) : le lancement n'est pas retenu ; non documenté, jamais retenu |
| Un banc de bout en bout qui mesure dans la même séance le disque seul (mêmes lectures, même fenêtre) | oui | il a isolé le disque en une passe : A / B = 1,016, le chemin ne coûtait rien et le défaut était ailleurs |
| Témoin « débit ≤ min des étages » (loi d'une chaîne d'étages) | oui | borne qu'aucune mesure juste ne dépasse ; tenu à 1,016 |
| Copie corrompue à un bit par sorte de région, un expert par bit | oui | la table des détections (contrôle par contrôle) a confirmé D14 et trouvé le trou de l'identité de la partie en production |
| Chercher la lenteur du disque dans le fichier (fragments) | **échec** | H1 tombe à l'envers : le .trc (33 fragments) se lit plus vite que le GGUF (2 737) |
| Chercher un « grain » d'alignement de la longueur | **échec** | deux régimes, sans grain ; seule une carte des longueurs mesurée le dit |
| Balayage des longueurs en deux ordres tirés | oui | la dérive dans le temps ne dessine pas la même courbe dans deux ordres ; 22 longueurs sur 23 d'accord |
| Lire une longueur rapide fixe (12 Mio) au lieu de `longueur0` | oui | ×1,335 d'experts servis en N V V N ; ≤ 0,75 Mio lus en trop |
| Construire le banc sur un instantané `git archive HEAD` des crates des autres lots | oui | les autres lots éditaient trc-noyaux en même temps ; le banc mesure un code commité, nommé dans le journal |
| Construire trc-noyaux depuis l'environnement de vcvars | **échec** | son build.rs casse les guillemets de cmd quand cl.exe est dans le PATH ; construire hors de vcvars |
| Heures écrites de tête dans la note (encore, quatre fois ce soir) | **échec, corrigé** | décalées de 1 à 7 min ; corrigées d'après les commits et les journaux, barrées |
