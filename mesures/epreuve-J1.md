# Épreuve indépendante du jalon J1

Juge : l'épreuve indépendante de `decisions/ARCHITECTURE.md` § 8, tenue le 2026-10-16 de 02 h 12 à
06 h 10 (heure locale) par un agent qui n'a écrit ni la spécification ni une ligne du code jugé.
Outils, journaux et CSV : `mesures/moteur/epreuve-J1/` (tout est commité) ; sorties lourdes hors du
dépôt : `~/dev/essais/troncons/epreuve-J1/`.

Étiquettes : **[mes.]** mesuré ici, outil et journal commités ; **[calc.]** calculé par un outil
commité ; **[hyp.]** hypothèse dite ; **[est.]** estimation non mesurée ; **[lot X]** chiffre d'un lot,
non refait.

Le rapport va dans `mesures/epreuve-J1.md`, comme le dit la consigne ; le § 8.7 disait
`decisions/epreuve-J1.md`, qui reste à l'arbitre (constat m6).

---

## 0. Le verdict en bref

1. **La spécification est vraie** (§ 8.1). Mon décodeur Python, écrit depuis le seul § 4, redonne au
   bit près **20 tronçons sur 20** tirés au hasard dans `gpt-oss-120b.trc` (graine 20261016), et 20 sur
   20 dans `gpt-oss-20b.trc`. Les 471 tenseurs résidents du 120b et les 315 du 20b égalent le GGUF
   octet pour octet. L'en-tête, MÉTA, TABLES, RÉPERTOIRE et les compagnons `.vocab.gguf` sont
   conformes champ par champ. Quatre cassures de mon décodeur tombent sur le seul tronçon visé.
2. **C3 et C11 tiennent sur le 120b**, refaits par ma propre construction depuis un clone propre, sur
   les **10 fenêtres (5 120 pas)** : 0 empreinte de logits différente entre codé et brut, `.kld`
   identiques, PPL 422,20558522791305 des deux côtés. Mieux : mes `.kld`, faits par le préremplissage
   par flux, égalent **octet pour octet** ceux du lot O, faits par boucle de pas (SHA-256 5b212fe9…).
   Le témoin F n'existait que sur le 20b ; il tient donc aussi sur le 120b, et d'une construction à
   l'autre.
3. **La référence f64 est juste, par un troisième calcul.** J'ai écrit une passe avant de gpt-oss en
   numpy f64, depuis la forme publiée par OpenAI, sans rien lire du lot R. Sur les 255 positions
   notées de la fenêtre 0 du 20b, la référence du lot R l'égale à **0,504 pas de quantification du
   format près**, c'est-à-dire à l'arrondi seul, avec 100 % de premiers choix identiques.
4. **C4 tient sur le 20b et, pour la première fois, sur le 120b**, contre cette vérité
   indépendante (fenêtre 0, 255 positions). Sur le 120b : KL 0,00308 et 95,7 % de premiers choix pour
   troncons, contre 0,0607 et 80,4 % pour llama.cpp carte. Différence appariée −0,0576 ± 0,0120 ;
   intervalles de Wilson disjoints.
5. **Vitesse, mémoire, VRAM** (séance ABBA, secteur à chaque passe). C5 tient (1,90 à 2,17 j/s,
   contre un seuil recalculé de 1,43 à 1,48). C7 : le plafond tient (pointe 384,4 Mo, tenue par le
   système), l'écart 120b − 20b **tombe** encore (2,94 Mo pour une borne de 0,78 Mo). C10 tient
   (6 574 Mio). Le cache tiède d'1 Go apparaît bien dans l'instrument (+994 Mo).
6. **La base n'était pas la meilleure possible** (§ 8.4). llama.cpp `fit` à 10 fils fait
   **0,702 j/s**, contre 0,627 à 6 fils dans la même séance, un écart réel de 12 %. C6 tient quand même
   (× 2,79), mais **le × 3,85 publié est à barrer**.
7. **Ce que personne n'avait vu, et qui compte** : (a) une passe peut **se figer sans rien dire**. Le
   moteur quitte en pleine fenêtre, très probablement sur une erreur, puis sa destruction tourne dans
   `nvcuda64.dll` (35 min et plus, jusqu'à ce que je la tue), et aucun message n'est jamais écrit. (b) Après toute erreur, le moteur laisse un
   `nvidia-smi` **orphelin** qui garde ses tuyaux ouverts ; le parent attend sans fin. L'un d'eux, né
   d'une passe du lot O à 01 h 38, tourne encore. (c) La production ne vérifie pas les flux bruts d'un
   tronçon : une médiane ou un biais corrompus passent sans erreur, et sur la copie corrompue du lot O
   le texte produit est même **identique** à celui du fichier sain.
8. **Le premier jeton du texte de C12 est faux pour le modèle exact** : la vérité f64 dit « ... »
   (log p = −1,46), troncons dit « am » (log p vrai = −10,03), après une cascade de 20 bascules de
   routage sur 36 couches. **La vérité, avec le seul cache KV arrondi en f16 (couture N), fait la
   même erreur** ; ce seul arrondi porte environ 70 à 77 % des bascules de routage du 120b (constat
   M5).
9. **C8 tel que spécifié n'est pas un instrument du moteur.** Le PDH tombe sur 2 passes sur 6 (+2,37 Go
   sur la première, à froid). Les compteurs d'E/S du processus, eux, montrent que le compte du moteur
   est exact à 22,8 Mo près.

---

## 1. Les conditions

- **Machine** : secteur à chaque passe (Win32_Battery BatteryStatus = 2, avant et après, dans chaque
  journal) ; carte libre au départ (346 Mio, aucun llama-* ni troncons) ; verrou
  `~/dev/verrou-carte.txt` pris à 02 h 26 et rendu à 04 h 44 ; aucun autre verrou
  pendant ce temps.
- **Charge étrangère, notée** : un `find` lancé à 21 h 52 par un autre agent (≈ un cœur en continu),
  non touché ; un `nvidia-smi -lms 500` d'une surveillance qui tourne depuis le 2026-10-15 à 08 h 34 ;
  un `nvidia-smi -lms 250` orphelin né à 01 h 38 (constat G2), non touché.
- **Construction** : `git clone` du dépôt au commit 527dff5 dans
  `~/dev/essais/troncons/epreuve-J1/clone`, construit dans
  `~/dev/cibles/troncons-epreuve` par `mesures/moteur/epreuve-J1/construire.bat`
  (`--offline -j 4`, CUDA 13.1.2). La recette du SOCLE (vcvars d'abord) casse la construction
  (constat m2) ; sans vcvars, elle passe en 21 s.
- **Ce que j'ai lu** : SOCLE.md, ARCHITECTURE.md en entier, le code et les journaux. Je n'ai ouvert
  `trc-format` ni `trc-codec` qu'**après** le geste 1, et le décodeur n'en a jamais rien pris.
- **Disque** : il ne reste que **128 Go libres** sur C: (797 Go occupés), à signaler à Stone. Les
  fichiers que les lots proposent de libérer en totalisent environ 120 Go. L'épreuve a ajouté, hors du
  dépôt et rien d'effacé : `~/dev/essais/troncons/epreuve-J1/` (4,9 Go : clone, `.kld`,
  `.npz`), `~/dev/cibles/troncons-epreuve` (275 Mo) et `troncons-epreuve-vcvars` (14 Mo),
  à libérer quand Stone le veut.

---

## 2. Geste 1 : la spécification est-elle vraie ? (§ 8.1)

### 2.1 Ce que fait l'outil

`mesures/moteur/epreuve-J1/decodeur_s4.py` (Python 3.13, numpy, bibliothèque standard) :
- un lecteur GGUF v3 écrit depuis la spécification publique (`ggml/docs/gguf.md`) ;
- l'en-tête du § 4.3 champ par champ (magie, versions, drapeaux connus, alignement, taille du
  fichier contre la taille réelle, SHA-256 et taille du source, géométrie, zéros réservés de 264 à
  4 088, empreinte) ;
- MÉTA (§ 4.4) contre les paires du GGUF, octet pour octet ; RÉSIDENTS (§ 4.5) contre les tenseurs du
  GGUF (noms, ordre, type, forme, taille, décalage multiple de 256, et avec `--residents-complets`
  chaque tenseur octet pour octet et son empreinte) ; TABLES (§ 4.6 : somme 4 096 de chaque table,
  empreinte) ; RÉPERTOIRE (§ 4.7 : ordre, alignements, contiguïté des tronçons, empreinte) ;
- par tronçon : l'en-tête de partie et la table des flux (§ 4.8), le rANS du § 4.9.2 **vectorisé sur
  les tuiles** (elles sont indépendantes par construction : 127 tuiles × 32 voies en parallèle,
  1 024 pas séquentiels par flux, 0,8 s par expert), la table par voie du § 4.9.3,
  la reconstruction du § 4.11. L'expert reconstruit est comparé (a) à l'empreinte d'origine du
  répertoire, (b) aux octets du GGUF au décalage du § 4.11 ; s'y ajoutent les voies à L, l'empreinte
  de la partie, et deux contrôles que le décodeur n'exige pas : médiane = `tri[B/2]`, et fin de
  chaque tuile = début de la suivante.

### 2.2 Résultats [mes.]

| | gpt-oss-120b | gpt-oss-20b |
|---|---|---|
| Tronçons tirés (graine 20261016), égaux au GGUF au bit près | **20 / 20** | **20 / 20** |
| Voies hors de L ; tuiles dont la fin ≠ début suivant | 0 ; 0 | 0 ; 0 |
| Médianes égales à `tri[B/2]` | 172 800 / 172 800 lignes | idem |
| Résidents octet pour octet (et empreinte) | **471 / 471** | **315 / 315** |
| MÉTA : paires du GGUF octet pour octet, + 3 clés du codeur | oui (39 = 36 + 3) | oui |
| TABLES : 432 tables, toutes de somme 4 096 ; empreinte | oui | 288 ; oui |
| RÉPERTOIRE : 4 608 entrées contiguës, du début de TRONÇONS à la fin du fichier | oui | 768 ; oui |
| En-tête : empreinte, taille, SHA-256 du source = registre des téléchargements | oui (582bd40f…) | oui (27cd6c43…) |
| Compagnon `.vocab.gguf` : GGUF v3, 0 tenseur, 36 paires du source octet pour octet | oui | oui |

Journaux : `journaux/s4-gptoss120b-20.json`, `s4-gptoss20b-20.json`, `vocab.jsonl`.

### 2.3 Le témoin du décodeur tombe-t-il ?

Chaque cassure est appliquée en mémoire au premier tronçon tiré du 120b (couche 12, expert 54). Le
second (couche 25, expert 109) doit tenir :

| Cassure | Voies hors de L | Octets faux | Le second tient |
|---|---|---|---|
| un bit retourné dans les mots de CODES_CTX | 32 (une tuile) | 31 122 | oui |
| deux fréquences d'une table échangées | 4 064 | 3 624 195 | oui |
| une médiane changée d'une unité | **0** | 90 (une ligne d'échelles) | oui |
| une fente de LUT corrompue | 4 032 | 3 262 607 | oui |

La médiane faussée laisse toutes les voies sur L : seule l'empreinte de l'expert la voit (constat M1).

### 2.4 Les copies corrompues des lots E et O, passées à mon décodeur

Sur `casse/gpt-oss-20b-casse-E2.trc` (12 bits retournés par le lot E), **les 12 tronçons touchés sont
détectés**, et un tronçon sain tient. Le détail dit qui voit quoi : 6 par les voies hors de L, 2 par
une erreur de format (un flux introuvable, un nombre de tuiles incohérent), 2 par l'en-tête de partie
(magie, numéro d'expert : leurs octets décodés égalent pourtant le GGUF), et **2 seulement par
l'empreinte de l'expert** : couche 23, expert 4, un octet de MEDIANES, et couche 21, expert 24, un
octet de BIAIS. Ces deux-là gardent toutes leurs voies sur L. Sur la copie à médiane faussée du lot O
(couche 0, expert 30), l'expert est faux et les voies sont sur L. Journaux :
`s4-gptoss20b-copie-E2.json`, `s4-gptoss20b-copie-O3.json`.

### 2.5 Ce que l'écriture du décodeur a appris sur le § 4

Rien n'a manqué pour décoder au bit près. Trois imprécisions, qui n'ont trompé personne mais qu'un
second implémenteur devra deviner (constat m4) :
1. Les longueurs de section de l'en-tête sont les longueurs **utiles**, sans le bourrage (MÉTA :
   12 980 522 o, pas un multiple de 4 096) ; le § 4.3 ne le dit pas.
2. L'empreinte de la table des résidents est « après la zone de données » ; elle est en fait aux 8
   derniers octets de la section. Ici, la fin du dernier tenseur est alignée sur 256, et les trois
   lectures possibles coïncident.
3. « La fin de la tuile t est le début de la tuile t + 1 » est vrai sur 100 % des tuiles décodées. Ce
   contrôle gratuit n'est pas normatif.

---

## 3. Les chiffres se reproduisent-ils ? (§ 8.3), critère par critère

### 3.1 Tableau

| Critère | Seuil (§ 7) | Publié par le lot | Refait par le juge | Verdict du juge |
|---|---|---|---|---|
| **C1** | 0 faux sur 4 608 | 0 [lot F, deux chemins] | 40 tronçons tirés + 13 nommés par un 3ᵉ décodeur, 0 faux ; 3 394 décodages vérifiés par le témoin du moteur | **TIENT** (sur ce que j'ai tiré) |
| **C2** | 0 écart, 100 % des corruptions détectées | 0 sur 4 608 [lot E] | mode témoin, 120b : **3 394 / 3 394** décodages égaux à l'empreinte (préremplissage par flux, 3 060 experts distincts) ; copie E2 : erreur fatale nommée ; copie O3 : témoin nommé | **TIENT en mode témoin** ; en production, les flux bruts ne sont pas gardés (M1) |
| **C3** | 0 bit différent, 5 120 pas | 0 [lot O] | **0 / 5 120**, `.kld` égaux, = lot O octet pour octet | **TIENT** |
| **C4** | KL et premier choix au moins aussi bons que llama.cpp | 20b : 0,00368 contre 0,0226 [lot O] ; 120b : non jugé | vérité numpy f64 indépendante, fenêtre 0 : 20b 0,00174 contre 0,0261 ; **120b 0,00308 contre 0,0607** | **TIENT** (20b et 120b, une fenêtre) |
| **C5** | ≥ 0,8 × plancher en série | 2,186 / 2,182 ≥ 1,505 [lot O] | 2,011 / 1,904 / 2,173 ≥ 1,47 / 1,43 / 1,48 (D chaud) | **TIENT** ; reproduit (écart 7,4 %, sous 2 × 5,5 %) |
| **C6** (J1+) | > 2 × bruit + 3 % sur la meilleure base | × 3,85 sur 0,568 [lot O] | **× 2,79** sur la meilleure base mesurée (0,702, à 10 fils) | **TIENT** ; le × 3,85 est à barrer (M2) |
| **C7** plafond | ≤ 1,9 Go | 384,2 Mo [lot O] | **384,4 Mo** (pointe tenue par le système) | **TIENT** |
| **C7** écart | ≤ 2 × bruit + 0,5 Mo | 3,70 Mo, tombe [lot O] | **2,94 Mo** pour une borne de 0,78 Mo | **TOMBE** (M4) |
| **C8** | ≤ repos × durée + 100 Mo | tombe sur 1 passe sur 4 [lot O] | PDH : tombe sur **2 / 6** ; compteurs du processus : **22,8 Mo** d'écart | instrument faux (M3) ; le moteur compte juste |
| **C10** | ≤ 7 279 Mio | 6 520 à 6 537 [lot O] | pointe 6 574 Mio | **TIENT** |
| **C11** | PPL égales | 422,20558522791305 [lot O] | 422,20558522791305 (codé et brut) | **TIENT** |
| **C12** | 256 jetons égaux, codé et brut | e4c6dbac… sur 17 passes [lot O] | e4c6dbac… sur mes 4 passes 120b (dont le cache tiède) | **TIENT** ; mais son premier jeton n'est pas celui du modèle exact (§ 6.1, M5) |

### 3.2 C3 et C11, en détail

`troncons evaluer --flux` sur les 10 fenêtres de `ref-openai-20b.kld`, `.trc` codé puis brut (passes
de 289 et 287 s). Un tour à 3 fenêtres (1 536 pas) avait d'abord donné le même verdict. Outil :
`comparer_c3.py`. Journaux : `journaux/c3-120b-3fenetres.json`, `c3-120b-10fenetres.json`.

| | Juge, codé (flux) | Juge, brut (flux) | Lot O, codé (boucle) | Lot O, brut (boucle) |
|---|---|---|---|---|
| SHA-256 du `.kld` (10 fenêtres) | 5b212fe9… | 5b212fe9… | 5b212fe9… | 5b212fe9… |
| Empreintes de logits différentes du codé du juge | — | 0 / 5 120 | 0 / 5 120 | — |
| PPL des positions notées | 422,20558522791305 | idem | idem | idem |

Une égalité au bit entre deux constructions, deux ordres de préremplissage (flux et boucle) et deux
jours confirme la règle de déterminisme sur toute la chaîne. Le témoin F du lot O ne l'avait montrée
que sur le 20b.

### 3.3 C4 et la référence, par un troisième calcul

`gptoss_numpy.py` : une passe avant f64, en numpy, écrite depuis la forme du modèle publiée par OpenAI
(implémentation de référence `gpt_oss/torch/model.py`, Apache-2.0 ; rien n'est copié). Elle comprend :
l'enchâssement Q8_0 ; RMSNorm ; les projections et leurs biais ; RoPE par moitiés, avec la rampe de
YaRN réelle et la concentration 0,1 ln 32 + 1 sur cos et sin ; l'attention à 64 têtes q et 8 têtes kv,
une échelle 1/8, le puits par tête au dénominateur et une fenêtre de 128 clés sur les couches paires ;
le routeur top-4 puis le softmax sur les 4 ; la SwiGLU bornée à 7 ; les experts MXFP4 déquantifiés
exactement ; la tête de sortie. Elle lit le GGUF par mon lecteur. Les bornes de rampe qu'elle trouve,
8,09278 et 17,39802, égalent celles du lot R. Durée : 6 min (20b) et 17 min (120b) pour 511 positions.

**La référence f64 du lot R contre ma passe** (20b, fenêtre 0, 255 positions, 201 088 jetons chacune) :
écart maximal des log-probabilités au-dessus du plancher du format **0,000123 nat = 0,504 pas** de
quantification (pas médian 2,44·10⁻⁴), soit l'arrondi à 16 bits seul ; 255 positions sur 255 sous
un pas ; 100 % de premiers choix identiques. La rampe de llama.cpp, elle, s'écarte jusqu'à 6,5 nat
(`journaux/ecart-logp-20b-f0.json`).

**C4 contre cette vérité** (`comparer_kld.py`, `verdict_c4.py` ; `csv/c4-numpy-20b-f0.csv`,
`csv/c4-numpy-120b-f0.csv`) [mes.] :

| Fenêtre 0, 255 positions | KL moyenne | même premier choix [Wilson 95 %] | d̄ apparié (troncons − llama) |
|---|---|---|---|
| 20b, troncons | 0,00174 | 96,5 % [93,4 ; 98,1] | −0,0243 ± 0,0053 |
| 20b, llama.cpp carte (`carte_cmoe.kld`) | 0,0261 | 87,1 % [82,4 ; 90,6] | |
| 20b, référence à la rampe llama.cpp | 0,0143 | 93,3 % | |
| 20b, référence sans l'échelle de YaRN (cassure du lot R) | 0,227 | 61,2 % | |
| **120b, troncons** (`o3-120b-…-code.kld`) | **0,00308** | **95,7 %** [92,4 ; 97,6] | **−0,0576 ± 0,0120** |
| **120b, llama.cpp carte** (mon `05-K120.kld`, configuration `carte_cmoe` du lot R) | **0,0607** | **80,4 %** [75,1 ; 84,8] | |

Les KL sont mesurées contre une vérité exacte, sur des fichiers à 16 bits. Le plancher du format (tout
logit sous max − 16 reçoit le code 0, environ 85 000 jetons sur 201 088) donne aux distributions lues
une masse en trop de 0,2 % (`journaux/normalisation-kld-20b-f0.json`), commune à tous les fichiers ;
c'est pourquoi la KL de la référence est légèrement négative (−4,8·10⁻⁴). Cela ne change aucun ordre.

**Lecture.** Sur la fenêtre 0, la rampe de YaRN seule explique 0,0143 des 0,0261 de llama.cpp (55 %) ;
le lot R l'avait mesuré sur les 10 fenêtres (0,0145). Le « six fois plus près de la référence » du
lot O est vrai, mais il porte surtout sur un choix de modélisation, celui d'OpenAI
(`"truncate": false`), validé ici par un calcul indépendant. La précision des noyaux n'en est pas la
cause principale (constat m5).

### 3.4 Vitesse, mémoire et VRAM : la séance `s1-2026-10-16`

Pilote `pilote_epreuve.py`, ordre déclaré avant toute passe (`seuils-declares.md`, commit 4832184),
processus neufs, palindrome. Mon instrument est indépendant : pointes tenues par le système (lues sur
la poignée après la sortie), mémoire disponible de toute la machine (100 ms), VRAM (250 ms),
alimentation avant et après. CSV : `csv/s1-2026-10-16-passes.csv` ; verdicts :
`journaux/verdicts-s1-2026-10-16.json`.

| Passe | Génération (j/s) | Préremplissage (j/s) | Pointe ET (Mo) | Engagée (Mo) | Perte machine (Mo) | VRAM (Mio) | Texte |
|---|---|---|---|---|---|---|---|
| 00 D120 (disque seul) | 0,725 Go/s | — | 190 | 281 | 213 | 438 | — |
| 01 T120 | 2,011 | 27,1 | 384,4 | 6 934 | 481 | 6 574 | e4c6dbac |
| 02 L120 `fit -t 6` | 0,618 | 3,94 | 11 211 | 6 810 | 6 288 | 6 026 | 45a1f638 |
| 03 L120 `fit -t 10` | 0,704 | 3,99 | 11 456 | 6 811 | 11 436 | 6 026 | 45a1f638 |
| 04 L120 `fit -t 10` | 0,700 | 3,90 | 11 475 | 6 809 | 11 594 | 6 032 | 45a1f638 |
| 05 L120 `fit -t 6` | 0,637 | 3,94 | 11 357 | 6 810 | 11 373 | 6 027 | 45a1f638 |
| 06 T120 | 1,904 | 27,1 | 384,4 | 6 931 | 726 | 6 574 | e4c6dbac |
| 07 D120 | 1,822 Go/s | — | 189 | 280 | 214 | 438 | — |
| 08 T20 | 10,62 | 68,6 | 381,3 | 6 937 | 478 | 6 568 | 1b14e44a |
| 09 T20 | 10,71 | 69,1 | 381,5 | 6 914 | 457 | 6 568 | 1b14e44a |
| 10 T120, cache tiède 1 Go | 1,901 | **12,5** | 1 378,5 | 7 932 | 1 593 | 6 574 | e4c6dbac |
| 11 T120 | 2,173 | 26,9 | 384,3 | 6 935 | 541 | 6 574 | e4c6dbac |

T = `troncons mesurer --flux`, A0, invite wikitext (708 jetons, SHA-256 eadbe87e…), 256 jetons ;
L = llama.cpp, commande de la base telle quelle ; ET = ensemble de travail ; « engagée » = mémoire
privée engagée de pointe ; « perte machine » = repos médian moins minimum de la mémoire physique
disponible de toute la machine pendant la passe. Les textes égalent ceux du lot O (e4c6dbac…,
1b14e44a…) et de la base (45a1f638…).

- **C5** [calc.] : plancher en série par la formule du lot O, avec mes grandeurs. Avec la médiane de
  mes deux D (1,27 Go/s), les seuils sont 1,10 à 1,13 j/s. Avec la seule passe D chaude (1,822 Go/s),
  ils sont **1,43 à 1,48 j/s** (t_disque 389,7 ms, PCIe 76,8 à 92,0, décodage 53,7 à 57,6, GEMV 15,3,
  T0 3,5). Les trois T120 tiennent dans les deux cas. La première D (0,725 Go/s, 90ᵉ centile 172 ms
  pour 12 Mo) était un transitoire à froid : le moteur lisait à 1,79 Go/s la minute suivante
  (constat m1).
- **Reproduction** (règle de 06 § 7.5) : T120 moyen 2,03 j/s contre 2,18 (lot O, séance 2, avec
  flux), écart 7,4 % sous 2 × 5,5 % de bruit : **reproduit**. llama.cpp `fit -t 6` 0,627 contre 0,568
  publiés, écart 10,4 % sous 2 × 9,5 % : **reproduit**.
- **C7** : 384,38 Mo au plus pour le 120b ; l'instrument du moteur dit 384,36 Mo, à 0,02 Mo près. Écart
  120b − 20b : 2,94 Mo, bruit 0,14 Mo, borne 0,78 Mo : **tombe**, comme pour le lot O (3,70 Mo ; 0,99 à
  fenêtre fixe).
- **§ 8.5, la fenêtre est-elle visible ?** Avec 1 Go de cache tiède, la pointe gagne **994,2 Mo**
  (0,994 × 10⁹ o, ou 0,926 Gio, dans la fourchette déclarée) : l'instrument voit la fenêtre.
- **Ce que la machine perd** (mesure neuve) : 0,46 à 0,73 Go pour troncons (ensemble de travail
  0,38 Go), contre 6,3 à 11,6 Go pour llama.cpp. Le seuil déclaré pour un constat (2 × ET + 200 Mo =
  0,97 Go) n'est pas franchi. En revanche, la mémoire **engagée** de troncons vaut 6,93 Go, l'ordre de
  ses allocations de VRAM : C7 ne la mesure pas (constat m3).
- **Le cache tiède** [mes., une passe, à confirmer] : il divise par 2,2 le préremplissage par flux
  (27,1 → 12,5 j/s) sans rien rendre à la génération (1,90 j/s). Personne ne l'avait mesuré.

### 3.5 C8 refait

`analyse_c8.py` → `journaux/c8-juge.json`. Les compteurs d'E/S du processus sont témoignés par
`temoin_compteurs_es.py` : des lectures sans tampon de 4 Kio à 64 Mio, comptées à l'octet près.

| Passe | PDH − moteur | Borne déclarée | PDH | Processus − moteur |
|---|---|---|---|---|
| s1 01 T120 (première passe 120b) | **+2 372,8 Mo** | 100,8 | tombe | — |
| s1 06 T120 | +314,9 Mo | 244,2 | tombe | — |
| s1 08, 09 T20 | +96,5 ; +39,7 | 103,5 ; 121,3 | tient | — |
| s1 10 T120 tiède | +241,9 | 2 689,4 | tient | — |
| s1 11 T120 | +125,4 | 154,4 | tient | — |
| c3 E120c ; E120b (3 fenêtres) | — | — | — | **+22,8 ; +22,6 Mo** |

Le moteur compte juste : le processus lit 22,8 Mo de plus, soit les lectures tamponnées de
l'ouverture que le lot O avait nommées (MÉTA, tables, répertoire ≈ 13,5 Mo) et environ 9 Mo d'autres.
Les gros écarts du PDH sont hors du processus. Ma première passe a +2,37 Go, presque les +2,39 Go de la
première passe du lot O : ce sont vraisemblablement les images des DLL (CUDA, llama), chargées à froid
par fautes de page, que le PDH voit et que `ReadFile` ne compte pas [hyp.].

---

## 4. Les témoins tombent-ils ? (§ 8.2)

| Cassure rejouée par le juge | Attendu | Observé |
|---|---|---|
| mon décodeur : mot, table, médiane, fente de LUT (§ 2.3) | le tronçon visé tombe, l'autre tient | oui, 4 / 4 |
| mon décodeur sur la copie E2 (12 bits) et la copie O3 (médiane) | 13 / 13 détectés | oui |
| moteur, production, copie E2 (`XE2`) | erreur fatale nommée | « couche 2, expert 19 : décodage faux (32 voies hors de L, 0 erreurs de format, 1 pointeurs de tuile faux) » |
| moteur, production, copie O3 (`XO3`) | rien en production | le moteur va au bout, et son texte de 32 jetons **égale celui du fichier sain** (48f70a45…) |
| moteur, témoin, copie O3 (`XO3t`) | empreinte nommée | « témoin : couche 0, expert 30 : empreinte 2e3544c4… au lieu de c9f614cc… » |
| C7 : 1 Go de cache tiède | ≈ +1 Go | +994 Mo |
| mon instrument C8 (`temoin_compteurs_es.py`) | lectures comptées | oui, après une correction (voir § 9) |

Non rejouées par le juge : les cassures de K1, K2, K3 (noyaux), R0 et R1 (référence), O1 (cache) et
E0 et E2 (chemin des octets). Leurs journaux existent chez les lots ; je ne les ai pas refaites.

---

## 5. La base est-elle honnête ? (§ 8.4)

La meilleure configuration publiée (`fit`, `-t 6 -c 2048`) et une autre de mon choix (`fit -t 10`)
ont tourné en palindrome dans la même séance. Ma raison, déclarée avant : sous mmap, chaque fil en
faute de page est une lecture en vol, donc plus de fils, c'est une file plus profonde sur le disque.

| | passes | moyenne | bruit |
|---|---|---|---|
| `fit -t 6` | 0,618 ; 0,637 | 0,627 | 3,0 % |
| `fit -t 10` | 0,704 ; 0,700 | **0,702** | 0,6 % |

L'écart, 11,9 %, dépasse 2 × 3,0 % et 3 % : il est **réel**. Les deux textes sont égaux (45a1f638…).
La base publiée sous-estimait llama.cpp d'environ 12 %. C6 tient contre la meilleure base (× 2,79 sur
la première paire T120, × 2,89 sur les trois), mais **le × 3,85 doit être barré** (constat M2). Je n'ai
balayé ni `-t 12` ni `-t 16`, ni `--n-cpu-moe` : la base peut être meilleure encore.

---

## 6. Le texte est-il juste ? (§ 8.6)

- **C12, 256 jetons gloutons du 120b** (`journaux/programme/s1-2026-10-16/01-T120.txt`). Le texte
  commence par « am », puis un résumé cohérent et exact du texte d'invite (Robert Boulter, The Bill
  en 2000, Herons au Royal Court en 2001, Judge John Deed…). Après une centaine de jetons, il tombe dans
  une boucle (« Here is a summary » raccourci jusqu'à « Here » répété). La sortie gloutonne de llama.cpp
  sur la même invite boucle elle aussi, sur des appels d'outil simulés. C'est le comportement du
  décodage glouton de ce modèle, pas un défaut visible du moteur.
- **Le premier jeton diffère entre les deux moteurs** : troncons dit « am », llama.cpp « ... ». Ma passe
  numpy f64 du 120b sur les 708 jetons de l'invite tranche (§ 6.1).
- **La conversation harmony du 120b** (lot O, `2026-10-16-s3-06-harmonie.txt`, publiée, non jugée) :
  une réponse en français, structurée en tableaux, sur l'inférence MoE avec déchargement. Le canal
  `analysis` précède `final`, conformément au format harmony. Le fond contient des approximations du
  modèle (« k = 2 généralement », « 1 à 2 M de paramètres par expert »), pas du moteur. Les caractères
  coupés entre deux jetons sortent en « � » (défaut d'assemblage connu du lot O).

### 6.1 Le premier jeton de C12, tranché par la vérité f64 [mes.]

J'ai passé les 708 jetons de l'invite (ceux de `llama-tokenize` ; 708 comme dans les deux moteurs,
sans BOS) à ma passe numpy f64 du 120b, avec l'argmax de chaque position et la trace de routage. Le
moteur a rejoué les mêmes jetons par `evaluer` sur un `.kld` d'une seule fenêtre de 708
(`base_kld_invite.py`), par flux et en boucle avec `--trace`. Les deux chemins sont égaux au bit, et
la position 707 redonne bien le jeton 313 de `generer`.

| Position 707 (le premier jeton produit) | argmax | log p vrai de 313 (« am ») | log p vrai de 1008 (« ... ») |
|---|---|---|---|
| vérité f64 | **1008** | −10,03 | −1,46 |
| llama.cpp | 1008 | | |
| troncons | **313** | | |
| vérité f64 **avec le seul cache KV arrondi en f16** | **313** | −1,47 (sous l'imitation) | −3,84 (sous l'imitation) |

- **Ce n'est pas une rupture à 512.** Les 512 premiers jetons de l'invite sont la fenêtre 0 (logits du
  moteur égaux au bit à sa passe de la fenêtre 0). Les PPL des positions 354 à 706 sont 1 200,3 pour
  troncons et **1 221,8 pour la vérité** : ce passage est difficile pour le modèle lui-même. Sur le
  20b, rien ne change au-delà de 512 (KL 0,0030 puis 0,0038 ; même argmax final, 5310). Deux
  invariances le confirment sur le 120b : `--contexte 1024` et `--emplacements 200` laissent les 708
  empreintes inchangées.
- **C'est une cascade de bascules de routage.** À la position 707, 20 couches sur 36 routent
  autrement que la vérité, à partir de la couche 12 ; à la position 706, aucune. Sur tout le 120b,
  l'accord de routage avec la vérité baisse avec la profondeur (0,87 à 0,93 dans les couches 27 à 35
  dès les positions 256 à 511 ; 0,81 à 0,86 au-delà de 512). Sur le 20b, il reste à environ 0,97 et
  plus. La KL du 120b croît avec la position : 0,0040 (354 à 511), 0,0064 (512 à 639), 0,0158 (640
  à 706).
- **Le cache KV en f16 en est la cause suffisante, et la cause principale** (expérience déclarée
  avant sa passe, `seuils-declares.md`). La vérité f64, avec k et v arrondis en f16 et rien d'autre,
  choisit 313 à la position 707, avec la même cascade de 20 couches. Troncons est bien plus près de
  cette vérité-là : routage égal à 99,3 % (positions 0 à 511) et 97,9 % (512 et au-delà), contre 96,9
  % et 93,1 % face à la vérité exacte ; argmax égaux à 696 sur 708, contre 687. L'arrondi du KV porte
  donc environ 77 % des bascules avant 512 et 70 % après. llama.cpp, lui aussi en KV f16, tombe juste
  à 707 : ses autres approximations le mènent ailleurs, et ses 80 % de premiers choix sur la fenêtre 0
  disent qu'il bascule davantage ailleurs (§ 3.3).
- **Ce que cela dit de C12** : le texte publié (e4c6dbac…) est juste au sens du § 7.1 (C3 et C4
  tiennent), mais ce n'est pas la suite gloutonne du modèle exact : celle-ci commence par « ... ».
  Constat M5.

Journaux : `journaux/premier-jeton-c12-120b.json`, `premier-jeton-kvf16-120b.json`,
`invite-120b-par-position.json`, `invite-20b-par-position.json`, `routage-120b-invite.json`,
`routage-20b-invite.json`, `np-120b-invite-*.json`.

---

## 7. Ce que personne n'avait mesuré

1. Un **troisième décodeur**, depuis le seul § 4, sur le fichier de production du 120b (§ 2).
2. Une **troisième passe avant f64** : la référence du lot R confirmée à l'arrondi près (§ 3.3).
3. **C4 sur le 120b**, pour la première fois, contre une vérité exacte (§ 3.3).
4. **L'égalité au bit flux = boucle sur le 120b**, et d'une construction à l'autre (§ 3.2).
5. **La base à 10 fils** : +12 % pour llama.cpp (§ 5).
6. **Ce que la machine perd** pendant une passe, et la **mémoire engagée** (§ 3.4).
7. **C8 par les compteurs du processus** : le moteur compte juste à 22,8 Mo près (§ 3.5).
8. Le **blocage à la destruction** et l'**orphelin `nvidia-smi`** (constats G1 et G2).
9. Le **cache tiède qui divise par deux le préremplissage par flux** (une passe, § 3.4).
10. La **corruption silencieuse jusqu'au texte** en production (§ 4, constat M1).
11. **Le coût du cache KV en f16** : à lui seul, il fait basculer le premier jeton de C12 et porte
    70 à 77 % des bascules de routage du 120b (§ 6.1, constat M5).

---

## 8. Constats

Gravités : bloquant, grave, moyen, mineur. Chaque constat donne où, ce qui est constaté, la preuve et
la correction proposée. Toute correction est une proposition. Les coutures (format, API) ne changent
que par l'arbitre.

### G1 (grave) : une passe peut se figer sans fin et sans message après une erreur

- **Où** : `moteur/bins/troncons/src/main.rs` (le `Moteur` est détruit avant que l'erreur ne remonte
  jusqu'à son affichage), et sa destruction (`trc-ordo` → `trc-cuda`, `impl Drop for Evenement` /
  `Interne` : `cuEventDestroy`, `cuDevicePrimaryCtxRelease`).
- **Constat** : la passe `evaluer --flux --brut` des 10 fenêtres du 120b, lancée à 03 h 33 pendant
  que ma passe numpy lisait 61 Go et occupait le processeur, n'a jamais fini. Au bout de 35 min : 0
  lecture de plus en 10 s (1 863 lectures, 18,06 Go), carte à 0 %, fil principal à 100 %, `.kld`
  réduit à son en-tête, **aucune ligne sur la sortie d'erreur** (pas même « fenêtre 1/10 »).
  Relancée seule à 04 h 12, la même commande finit en 287 s.
- **Preuve** : `journaux/blocage-E120b-fil-principal.json` (300 échantillons du pointeur d'instruction
  sur 300 dans `nvcuda64.dll`) ; `journaux/blocage-E120b-pile.json` (pile nommée par dbghelp et le
  PDB : `troncons::principal` → `drop_glue<trc_ordo::Moteur>` →
  `Arc<trc_cuda::Interne>::drop_slow` → `drop_glue<Vec<[trc_cuda::Evenement; 2]>>` →
  `trc_cuda::impl$12::drop` → nvcuda) ; `journaux/seances/c3-10-2026-10-16.json` ;
  `journaux/programme/c3brut-2026-10-16/`. Outils : `echantillonner_fil.py`, `pile_fil.py`.
- **Ce que je ne sais pas** : l'erreur d'origine, jamais écrite. Hypothèse : une erreur pendant que
  du travail restait en file sur la carte, après quoi la destruction du contexte attend ce travail
  [hyp.].
- **Correction proposée** : (1) écrire l'erreur **avant** de détruire le moteur, puis sortir par
  `std::process::exit(1)` sans détruire le contexte CUDA (le pilote libère tout à la sortie du
  processus) ; (2) un battement sur la sortie d'erreur à chaque couche du préremplissage par flux,
  pour dater un blocage ; (3) rejouer la passe sous la même charge (numpy sur le 120b) avec (1) en
  place, pour lire enfin l'erreur. Coût : quelques lignes, aucune couture touchée.

### G2 (grave pour l'exploitation, moyen pour les résultats) : après une erreur, un `nvidia-smi` orphelin bloque le parent

- **Où** : `moteur/crates/trc-juge/src/compteurs.rs`. `Echantillonneur::demarrer` lance
  `nvidia-smi … -lms 250` ; seul `arreter()` le tue ; aucun `Drop` ne le fait.
- **Constat** : toute erreur entre `demarrer` et `arreter` laisse l'enfant vivant. Il hérite des
  poignées du moteur, donc de ses tuyaux de sortie : le parent qui attend la fin des sorties attend
  aussi longtemps que l'orphelin vit, c'est-à-dire toujours. Mes passes XE2 et XO3t ont fini en
  quelques secondes et n'ont « rendu la main » qu'après 518 et 630 s, quand j'ai tué leurs orphelins.
  **Un orphelin identique, né à 01 h 38 min 41 s d'un processus disparu (l'heure de la passe 21 du lot
  O, tombée sur une erreur), tourne encore** (PID 13652 à 04 h 40) ; il n'est pas à moi, je n'y ai pas
  touché.
- **Preuve** : `journaux/seances/complements-2026-10-16.json` (mur 518 et 630 s) ; relevé
  Win32_Process de 04 h 40 (parents disparus, lignes de commande `-lms 250`).
- **Correction proposée** : `impl Drop for Echantillonneur` qui tue et attend l'enfant ; stdin, stdout
  et stderr de l'enfant non hérités (`Stdio::null()` pour stdin) ; et le dire aux lots, dont les
  pilotes peuvent se figer de la même façon. Stone ou le lot O peuvent arrêter le PID 13652.

### M1 (moyen) : la production ne garde pas les flux bruts d'un tronçon

- **Où** : § 4.12 (« en production, chaque tuile décodée vérifie le retour des voies à L ») et
  `trc-ordo` (seul le mode `--temoin` refait l'empreinte).
- **Constat** : MEDIANES et BIAIS, environ 43 Ko sur 12 Mo par tronçon (0,36 %), ne sont pas codés par
  rANS : aucune voie ne les garde. En mode A0, la ligne d'enchâssement lue sur le disque à chaque jeton
  n'est pas gardée non plus. Une corruption de ces octets donne un expert faux **sans erreur**. Sur la
  copie du lot O, le texte gloutonne produit est identique à celui du fichier sain : la corruption
  est invisible jusque dans la sortie. C2 (« 100 % des corruptions injectées détectées ») n'est donc
  vrai qu'en mode témoin.
- **Preuve** : copie E2, tronçons 21:24 (un octet de BIAIS) et 23:4 (un octet de MEDIANES) : voies sur
  L, expert faux (`journaux/s4-gptoss20b-copie-E2.json`) ; XO3 (`journaux/seances/complements-…`) ;
  lot O, `o3-casse-mediane-production.*` (64 pas sur 64 aux logits faux, sans erreur).
- **Correction proposée**, sans couture changée : à chaque achèvement de lecture, un fil de travail
  hache les octets utiles du tronçon et les compare à `empreinte_niveau[0]` (déjà dans le
  répertoire). SHA-256 avec les instructions SHA va de l'ordre de 2 Go/s par cœur [est.], soit
  l'ordre du disque (1,8 Go/s) : un seul cœur suffit, en parallèle de la copie et du décodage ; une
  différence devient une erreur fatale nommée avant la GEMV, ou à la fin de la couche. Variante
  moins chère, pour la v1.1 (décision de l'arbitre) : une empreinte du seul préfixe brut (en-tête,
  table des flux, MEDIANES, BIAIS), environ 2,5 Mo hachés par jeton du 120b [calc. : 59 défauts × 43
  Ko].

### M2 (moyen) : la base de C6 était mal réglée ; le × 3,85 est à barrer

- **Où** : `mesures/gpt-oss.md` § 3.2 (base `fit`, `-t 6`) ; `moteur/O-pour-le-memoire.md` § 8
  (C6 : « × 3,85 ») ; le résumé de l'équipe.
- **Constat** : `fit -t 10` fait 0,702 j/s contre 0,627 à `-t 6` dans la même séance, un écart réel
  de 11,9 %. C6 tient (× 2,79), mais contre une base plus forte que celle publiée.
- **Preuve** : § 5 ; `journaux/verdicts-s1-2026-10-16.json` (`base_t6_contre_t10`, `C6`).
- **Correction proposée** : barrer ~~× 3,85~~ et écrire × 2,8 à 2,9 contre `fit -t 10` (séance du
  juge) ; avant tout chiffre de J1+, une série de la base qui balaie `-t` (6, 10, 12, 16) et
  `--n-cpu-moe`, la meilleure retenue par la règle de 06 § 7.5.

### M3 (moyen) : C8 tel que spécifié mesure la machine, pas le moteur

- **Où** : § 7.1, C8 (compteur PDH global, intégré par le moteur lui-même).
- **Constat** : le PDH tombe sur 2 passes sur 6 de ma séance, dont +2,37 Go sur la première, où le lot
  O avait +2,39 Go. Les compteurs d'E/S du processus montrent que le compte du moteur est exact à
  22,8 Mo près, soit les lectures tamponnées de l'ouverture. L'explication du lot O (lectures non
  comptées) n'en couvre donc que 23 Mo ; le reste est hors du processus.
- **Preuve** : § 3.5 ; `journaux/c8-juge.json`, `journaux/temoin-compteurs-es.json`.
- **Correction proposée** (décision de l'arbitre) : juger C8 par `GetProcessIoCounters`
  (ReadTransferCount, lu sur la poignée après la sortie), contre une borne de 100 Mo, ou de la taille
  des lectures tamponnées de l'ouverture plus 100 Mo ; garder le PDH comme mesure publiée, non jugée.

### M4 (moyen) : C7, l'écart 120b − 20b tombe encore

- **Où** : § 7.1, C7 (terme de 0,5 Mo).
- **Constat** : 2,94 Mo d'écart pour une borne de 0,78 Mo (bruit 0,14 Mo). Cela confirme le lot O
  (3,70 Mo ; 0,99 Mo à fenêtre fixe). Le plafond, lui, tient avec une marge de cinq.
- **Preuve** : § 3.4 ; `verdicts-s1-2026-10-16.json` (`C7`).
- **Correction proposée** : l'une des bornes du point 11 de REPRISE-O (termes nommés), ou une fenêtre de
  taille fixe ; décision de l'arbitre. Le verdict reste « tombe » tant qu'elle n'est pas prise.

### M5 (moyen) : le cache KV en f16 décide du premier jeton de C12 sur le 120b

- **Où** : § 5.6, couture N (« cache KV : f16 ») ; le texte de C12 (§ 7.1).
- **Constat** : à la position 707 de l'invite, la vérité f64 choisit 1008 (« ... », log p = −1,46),
  troncons 313 (« am », log p vrai = −10,03). La vérité avec le seul KV en f16 choisit 313, avec la même
  cascade de 20 couches. Sur tout le 120b, cet arrondi porte 70 à 77 % des bascules de routage du
  moteur. C3 et C4 tiennent : c'est le prix de la couture, pas un défaut du code ; mais il n'avait
  jamais été mesuré, et C4 (une moyenne, sur des positions < 512) ne pouvait pas le voir.
- **Preuve** : § 6.1 ; `journaux/premier-jeton-kvf16-120b.json` et ses voisins ; déclaration dans
  `seuils-declares.md` (commit 549b38b, avant la passe).
- **Correction proposée** (décision de l'arbitre, couture N) : (1) mesurer sur la carte un cache KV en
  f32 : 2 × 512 × 4 o par position et par couche ; les 18 couches pleines gardent 4 096 positions, les
  18 couches à fenêtre un anneau de 128, soit ≈ 312 Mo au lieu de ≈ 156 Mo sur le 120b au contexte de
  4 096 [calc. : 18 × (4 096 + 128) × 2 048 o en f16]. Cela fait environ 12 emplacements d'experts de
  moins sur 326 (−3,6 %), pour un gain à juger par la KL et par les bascules (~~604 Mo au lieu de
  302 Mo, −7 %~~ : premier calcul, qui oubliait l'anneau des couches à fenêtre) ; (2) ajouter à C4 un critère de queue (part des positions de KL > 0,1, et
  KL au 99ᵉ centile), jugé aussi au-delà de 512 positions ; (3) publier C12 avec la suite gloutonne de
  la vérité f64 à côté.

### m1 (mineur) : le seuil de C5 dépend d'une passe disque à froid

- **Où** : la formule de C5 (REPRISE-O, O4 : médiane des deux passes D).
- **Constat** : ma première D faisait 0,725 Go/s (90ᵉ centile 172 ms par lecture), la seconde 1,822 ;
  la médiane des deux déplace le seuil de 25 % (1,12 au lieu de 1,47). C5 tient dans les deux cas.
- **Correction proposée** : une passe D d'échauffement jetée, ou la médiane d'au moins trois D, ou le
  rejet d'une D dont le 90ᵉ centile dépasse cinq fois la médiane.

### m2 (mineur) : la recette de construction du SOCLE casse `trc-noyaux`

- **Où** : SOCLE (« lancer `vcvars64.bat` … ») et `moteur/crates/trc-noyaux/build.rs`.
- **Constat** : avec vcvars, le `build.rs` échoue (« '\"\"C:\…\nvcc.exe\" … n'est pas reconnu en tant
  que commande interne », `build.rs:75`) ; sans vcvars, la construction passe. Le lot E l'avait
  noté dans un commentaire de son script, pas dans le SOCLE.
- **Preuve** : `mesures/moteur/epreuve-J1/journaux/construire-avec-vcvars.log` (échec reproduit par
  `construire-avec-vcvars.bat`, la seule crate `trc-noyaux`, cible à part) ; `journaux/construire.log`
  (la construction sans vcvars, réussie) ; `construire.bat`.
- **Correction proposée** : un `build.rs` qui marche dans les deux cas (appel direct de nvcc, sans
  passer par `cmd`), ou une recette du SOCLE corrigée (« sans vcvars »).

### m3 (mineur) : C7 ne voit pas la mémoire engagée

- **Constat** : la mémoire privée engagée de troncons vaut 6,93 Go (7,93 avec 1 Go de cache tiède),
  l'ordre de ses allocations de VRAM et de sa mémoire épinglée ; c'est 18 fois l'ensemble de travail.
  Elle ne prend pas de RAM physique (la machine ne perd que 0,46 à 0,73 Go), mais elle compte contre
  la limite d'engagement (RAM + fichier d'échange).
- **Correction proposée** : publier à côté de C7 la mémoire engagée et la perte de mémoire disponible
  de la machine ; ne pas les juger avant une décision.

### m4 (mineur) : trois imprécisions du § 4

Voir le § 2.5 ; correction : trois phrases dans le § 4.3, le § 4.5 et le § 4.9.2.

### m5 (mineur) : « six fois plus près » demande sa raison

- **Constat** : le gros de l'écart entre troncons et llama.cpp vient de la rampe de YaRN, un choix de
  modélisation (OpenAI, `truncate: false`). Le lot R l'a documenté (R-pour-le-memoire § 2.8), mais
  le résumé de l'équipe ne le dit pas.
- **Correction proposée** : partout où « six fois » est écrit, dire « dont la rampe de YaRN, 0,0145
  des 0,0226 de llama.cpp ».

### m6 (mineur) : où va le verdict de l'épreuve

Le § 8.7 dit `decisions/epreuve-J1.md`, la consigne dit `mesures/epreuve-J1.md`. J'ai suivi la consigne
(choix prudent : `decisions/` reste à l'arbitre). À trancher par l'arbitre.

---

## 9. Ce que je n'ai pas pu vérifier

- **C1 sur les 4 608 experts** par mon décodeur : 40 tirés, 13 nommés, 3 394 décodages vérifiés par
  le témoin du moteur. Le reste repose sur le lot F (deux chemins).
- **C2 de bout en bout** par le banc E2 du lot E (disque → mémoire épinglée → DMA → décodeur) : non
  relancé ; j'ai le témoin du moteur sur 3 394 décodages.
- **C4 sur les 10 fenêtres du 120b** : ni la référence f64 du 120b (lot R) ni une base llama.cpp de
  10 fenêtres n'existent ; mon jugement porte sur une fenêtre (255 positions), plus les 353 positions
  notées de l'invite (§ 6.1).
- **Le cache KV en f32 sur la carte** (M5) : mesuré seulement dans ma passe numpy, pas dans le moteur.
- **La cause de G1** : l'erreur d'origine n'est jamais écrite.
- Les cassures des lots K, R, O1 et E (§ 4).
- **La séance de vitesse est une seule séance** : trois T120, deux de chaque base. La règle de 06 § 7.5
  ne se juge qu'à l'intérieur.

## 10. Ce qui pourrait être faux

- **Ma passe numpy et la référence du lot R lisent le même GGUF.** Une erreur de déquantification
  commune aux deux (ordre des demi-octets, échelle E8M0) passerait. Garde-fous : mon décodeur MXFP4
  suit `dequantize_row_mxfp4` de ggml (demi-octets bas = éléments 0 à 15), et C3 comme les textes
  relient tout le reste au bit ; la convention du format, elle, n'est jugée que par l'accord avec
  llama.cpp (KL 0,026, premiers choix 87 %), pas par OpenAI.
- **Ma passe et la référence suivent la même lecture du modèle** (rampe réelle, puits, fenêtre de
  128). Si OpenAI entraînait avec une autre convention, les deux se tromperaient ensemble. Le
  `config.json` d'OpenAI et son implémentation de référence sont les seules sources de cette lecture.
- **C4 sur le 120b repose sur une fenêtre** ; les intervalles sont disjoints, mais une fenêtre n'est
  pas dix.
- **La perte de mémoire de la machine est globale** : d'autres processus la font bouger. Elle est
  propre dans la séance s1, et souillée dans E120c (10,5 Go, ma passe numpy en même temps), que je
  n'utilise pas.
- **Mon instrument a eu deux défauts, trouvés et corrigés avant tout verdict** :
  (1) `GetCurrentProcess()` passé en entier de 32 bits par ctypes, d'où un témoin des compteurs qui
  rendait 0 ; corrigé avant d'interpréter quoi que ce soit, et le pilote n'était pas touché (sa
  poignée vient d'`OpenProcess`). (2) Un premier calcul de C8 ajoutait le chargement des résidents
  à un total qui le contenait déjà, d'où « le moteur compte 1,4 Go de trop » ; refait juste
  (`analyse_c8.py`), non publié.
- **Le préremplissage de mes T120 est par flux** (J1+), alors que C5 vise J1. La génération est la
  même boucle de pas, et le lot O a mesuré les deux (2,18 dans les deux cas). Le h du cache au début de
  la génération peut différer (0,590 ici).
- **L'heure des seuils déclarés** porte « 02 h 40 » dans `seuils-declares.md`. Le commit 4832184 est
  de 02 h 26 min 05 s, avant l'essai du pilote (02 h 26 min 35 s) et la première passe de la séance
  (02 h 27 min 40 s) : ~~02 h 40~~ 02 h 26. Les seuils ont bien été déclarés avant toute passe ; seule
  l'heure écrite était fausse.

## 11. Réponses par délégation de l'épreuve

Chacune : « réponse par délégation du 2026-10-16, réversible ».
1. **Rapport dans `mesures/epreuve-J1.md`** plutôt que `decisions/` : la consigne le dit, et
   `decisions/` est à l'arbitre.
2. **C3 par le préremplissage par flux** plutôt que par la boucle : 287 s au lieu de 55 min ; la
   comparaison au lot O (boucle) en fait un second chemin.
3. **La base à 10 fils** : la seule autre configuration que la séance permettait, choisie par le
   mécanisme de mmap.
4. **Le processus bloqué tué** (PID 10368, lancé par moi), après le relevé de sa pile, pour rendre la
   carte ; les orphelins `nvidia-smi` de mes passes tués ; ceux des autres laissés.

## 12. Commandes et journaux

```
construire.bat                                           (clone propre, cible troncons-epreuve)
python -I -X utf8 decodeur_s4.py <m.trc> <m.gguf> <journal> --n 20 --graine 20261016 [--residents-complets] [--casser mot|table|mediane|lut] [--cibles c:e,…]
python -I -X utf8 verifier_vocab.py <m.vocab.gguf> <m.gguf>
python -I -X utf8 pilote_epreuve.py --seance s1-2026-10-16                     (vitesse, mémoire, base)
python -I -X utf8 pilote_epreuve.py --seance c3-10-2026-10-16 --ordre c3       (C3, C11 ; le brut refait par --ordre c3brut)
python -I -X utf8 pilote_epreuve.py --seance complements-2026-10-16 --ordre complements
python -I -X utf8 analyse_seance.py journaux/seances/s1-2026-10-16.json journaux/verdicts-s1-2026-10-16.json --csv csv/s1-2026-10-16-passes.csv
python -I -X utf8 analyse_c8.py journaux/seances/s1-2026-10-16.json journaux/seances/c3-2026-10-16.json
python -I -X utf8 comparer_c3.py …                                             (voir l'en-tête de l'outil)
python -I -X utf8 gptoss_numpy.py <m.gguf> ref-openai-20b.kld <sortie.npz> --fenetre 0 --positions 511 [--jetons invite-ids.txt --dernieres 1]
python -I -X utf8 comparer_kld.py <vérité.npz> <journal> --csv <csv> --fichier nom=chemin.kld …
python -I -X utf8 ecart_logp.py | normalisation_kld.py | verdict_c4.py …
python -I -X utf8 echantillonner_fil.py <pid> <tid> 300 ; pile_fil.py <pid> <tid> troncons.exe <dossier du pdb>
```
