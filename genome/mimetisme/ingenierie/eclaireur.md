# Éclaireur « ingénierie et informatique existantes » : ce que le monde fait, et ce que troncons peut en prendre

Rôle : éclaireur de la bande « hiérarchies de mémoire et caches, systèmes de fichiers et bases de données,
ordonnancement et files, réseaux et protocoles, compilateurs, codecs, compression, GPU, supercalculateurs,
systèmes distribués, tolérance aux pannes ». Date : 2026-10-26 et 27. Étiquettes : **[mes.]** mesuré ici (outil et
journal commités) ; **[calc.]** calculé sur des mesures commitées ; **[lu]** source dont j'ai lu le texte ou la page ;
**[résumé]** source dont je n'ai lu que le résumé rendu par une recherche (texte intégral non ouvert) ; **[mém.]** de
mémoire, non relu. Seuils déclarés avant toute lecture de trace : `genome/mimetisme/ingenierie/seuils-declares.md`
(commit 2a4c60e, puis deux amendements écrits avant les résultats concernés). Outil : `outils/mimetisme/ingenierie/cache2.py`.
Journaux : `mesures/mimetisme/ingenierie/`.

## 0. En bref

1. **Une piste probable, mesurée.** Le cache tiède RAM de `trc-cache` est *inclusif* : la RAM est rafraîchie sur chaque succès
   VRAM (`moteur/crates/trc-cache/src/lib.rs`, lignes 164 à 166). Quand sa taille R est au plus celle de la VRAM (V = 326
   emplacements), elle contient des experts tous déjà en VRAM : **elle n'apporte aucun succès**. Mesuré : +0,0000 de succès pour
   R = 80 et 160 sur les six traces du 120b (H1). C'est la lecture exacte de l'épreuve J1 : « 1 Go de cache tiède, sans rien rendre
   à la génération » (`mesures/epreuve-J1.md` § 3.4). Le remède vient des hiérarchies de stockage à plusieurs niveaux : le cache
   **exclusif** (Wong et Wilkes, USENIX ATC 2002), où ce que la VRAM évince descend en RAM. Mesuré (H2, seuils tenus) : la part des
   accès qui vont au disque baisse de **10 %** (R = 80, ~1 Go), **30 %** (R = 336, ~4 Go), **48 %** (R = 672, ~8 Go) sur la génération,
   de 13, 41 et 64 % sur la lecture. Rien de ceci n'est une analogie : c'est le simulateur rejoué sur les traces de routage du dépôt.
2. **Quatre politiques d'éviction plus fines que LRU ne gagnent pas là où le moteur travaille.** À 326 emplacements, la fréquence (LFU),
   l'admission de type TinyLFU et l'horloge de couches à la Mockingjay (ETR) gagnent 6 à 9 points sur la lecture (préremplissage jeton
   par jeton) mais **perdent 1 à 9 points sur la génération** : H3 tombe au seuil déclaré. L'écart à l'optimum (Belady) sur la
   génération reste de 10 points : il demande l'avenir, pas une meilleure statistique du passé.
3. **Un avertissement mesuré pour la construction.** Un SLRU dont le segment probatoire fait 20 % de la VRAM (65 emplacements) s'effondre : succès 0,257
   contre 0,738 pour LRU sur la génération, 0,091 contre 0,453 sur `tous.lecture`. C'est la falaise de la proposition 1 de `mesures/gpt-oss.md` § 7,
   appliquée au segment probatoire (65 est sous (L−1)·k = 140). Le SLRU « prévu » (REPRISE-O, point 5) doit avoir un probatoire d'au moins L·k = 144 emplacements, ou une liste fantôme.
4. Sept candidats ci-dessous, classés ; un seul est vraiment neuf *pour troncons* et mesuré (n° 1). Presque tout le reste est déjà vu dans le monde et
   déjà posé dans le dépôt ; je le dis case par case.

## 1. Ce que j'ai lu, et ce que je n'ai pas pu lire

| Source | Adresse | Consultée | Lu |
|---|---|---|---|
| Wong, Wilkes, *My cache or yours? Making storage more exclusive*, USENIX ATC 2002 | https://static.usenix.org/event/usenix02/full_papers/wong/wong_html/index.html | 2026-10-26 | [lu] : les chiffres du candidat 1 viennent de cette page |
| Beckmann, Sanchez, *Talus: a simple way to remove cliffs in cache performance*, HPCA 2015 | https://dspace.mit.edu/handle/1721.1/101043 | 2026-10-26 | [lu] le résumé ; le PDF n'a pas pu être lu (HTTP 429, puis binaire) |
| Cidon, Eisenman, Alizadeh, Katti, *Cliffhanger*, NSDI 2016 | https://people.csail.mit.edu/alizadeh/papers/cliffhanger-nsdi16.pdf | 2026-10-26 | [résumé] |
| Einziger, Friedman, Manes, *TinyLFU*, arXiv 1512.00727 (2015) | https://arxiv.org/abs/1512.00727 | 2026-10-26 | [résumé] |
| Shah, Jain, Lin, *Mockingjay*, HPCA 2022 | https://www.cs.utexas.edu/~lin/papers/hpca22.pdf | 2026-10-26 | [résumé] (le PDF a été refusé : certificat) |
| Jain, Lin, *Back to the Future (Hawkeye)*, ISCA 2016 | https://cs.utexas.edu/~akanksha/isca16.pdf | 2026-10-26 | [résumé] |
| Yang et al., *FIFO queues are all you need for cache eviction (S3-FIFO)*, SOSP 2023 | https://junchengyang.com/publication/sosp23-s3fifo.pdf | 2026-10-26 | [résumé] |
| Qureshi, Patt, *Utility-based cache partitioning*, MICRO 2006 | https://utw10235.utweb.utexas.edu/pub/TR-HPS-2006-009.pdf | 2026-10-26 | [résumé] |
| Cao, Felten, Karlin, Li, *A study of integrated prefetching and caching strategies*, SIGMETRICS 1995 | https://homes.cs.washington.edu/~karlin/papers/sigmetrics.pdf | 2026-10-26 | [résumé] |
| Venkataramani, Kokku, Dahlin, *TCP Nice*, OSDI 2002 | https://usenix.org/conference/osdi-02/tcp-nice-mechanism-background-transfers | 2026-10-26 | [résumé] |
| Shalunov et al., RFC 6817 *LEDBAT*, 2012 | https://datatracker.ietf.org/doc/html/rfc6817 | 2026-10-26 | [résumé] |
| Microsoft, `FILE_IO_PRIORITY_HINT_INFO` | https://learn.microsoft.com/windows/win32/api/winbase/ns-winbase-file_io_priority_hint_info | 2026-10-26 | [résumé] : « hint », l'effet dépend des pilotes ; rien trouvé sur NVMe |
| Haidar, Tomov, Dongarra, Higham, SC18, *Harnessing GPU tensor cores … mixed-precision iterative refinement* | https://icl.utk.edu/node/1264 | 2026-10-26 | [résumé] |
| Zukowski, Héman, Nes, Boncz, *Cooperative scans*, VLDB 2007 | https://ir.cwi.nl/pub/12225 | 2026-10-26 | [résumé] |
| *SpecMD*, arXiv 2602.03921 (2026) | https://arxiv.org/html/2602.03921v1 | 2026-10-26 | [lu] : *Least-Stale*, « collision misses » |
| *Fewer expert transfers without changing routing: expert eviction for MoE offloading*, NeurIPS 2026 | https://neurips.cc/virtual/2026/156996 | 2026-10-26 | [lu] le résumé seul |
| *FlashMoE*, arXiv 2601.17063 (2026) | https://www.arxiv.org/pdf/2601.17063 | 2026-10-26 | métadonnées seulement (PDF binaire) |
| Megiddo, Modha, *ARC*, FAST 2003 | — | — | [mém.] |

## 2. Les mesures de cette passe

### 2.1 Témoins (déclarés avant, cassure comprise)

- **T1 tient** : mon LRU global à un étage (règle de groupe de `trc-cache`) égale les `succes` publiés de `courbes-gpt-oss-120b.csv`
  à **10⁻⁵ près** sur les 6 traces, aux capacités 230 et 461 (`temoins.csv`).
- **T2 tel que déclaré est tombé comme témoin** : retirer l'épinglage du groupe ne déplace le succès que de 0,0005 à 0,0015, sous le seuil 0,002.
  ~~T2 : le simulateur sans épinglage s'écarte de plus de 0,002.~~ Remplacé par **T2b** (amendement n° 1, avant H1 à H3) : une capacité décalée
  de 10 (220 pour 230) s'écarte de 0,005 à 0,018 sur chaque trace : **la cassure tombe, le simulateur voit.**
- **T3 tient** : le LRU à deux étages exclusif égale un LRU unique de V + R emplacements à 0,0007 près (seuil 0,003).
- Cohérence : `lru1` et `politique(…, "lru")` donnent le même succès (0,7379) sur la génération.

### 2.2 H1 : le tiède inclusif n'apporte rien quand R ≤ V [mes.]

Prédite par la lecture du code avant toute mesure, tient : pour V = 326 et R ∈ {80, 160}, succès_VRAM + succès_RAM − succès_VRAM seul = **0,0000**
sur les 6 traces ; à R = V = 326 il vaut +0,0003 à +0,0006 (`h1.csv`). Seuil de rejet 0,002 : non atteint.

### 2.3 H2 : le cache exclusif rend la somme [mes.]

Part des accès qui vont au disque (`h2.csv`), V = 326 :

| Trace | V seul | inclusif R = 80 | exclusif R = 80 | inclusif R = 336 | exclusif R = 336 | inclusif R = 672 | exclusif R = 672 |
|---|---|---|---|---|---|---|---|
| prose-en.generation | 0,2621 | 0,2621 | **0,2352** (−10,3 %) | 0,2573 (−1,8 %) | **0,1845** (−29,6 %) | 0,1830 (−30,2 %) | **0,1368** (−47,8 %) |
| tous.lecture | 0,5472 | 0,5472 | **0,4753** (−13,1 %) | 0,5361 (−2,0 %) | **0,3241** (−40,8 %) | 0,3197 (−41,6 %) | **0,1993** (−63,6 %) |

Seuils déclarés : au moins −8 % à R = 80 et −25 % à R = 336 sur les deux traces. **Tenus** (−10,3 et −13,1 ; −29,6 et −40,8). La ligne inclusive à R = 336 et
R = 672 montre le défaut : le tiède inclusif de R entrées vaut un cache de R entrées, pas de V + R.
~~« −56 % sur la lecture » (message envoyé à la session principale à R = 672)~~ : c'est −64 %, erreur de recopie de ma part, corrigée ici.

**Du disque à la vitesse** [calc., hypothèse : le disque limite seul] : vitesse = 1 / (1 − r) pour une baisse relative r des octets lus, donc ×1,11 (1 Go), ×1,42 (4 Go),
×1,92 (8 Go) appliqués à la génération du 120b. Réserves : la génération du moteur manque la VRAM plus souvent que la trace (0,59 de succès mesuré par le juge contre 0,738 simulé :
la trace de génération est courte, 256 jetons, et en partie dégénérée, `mesures/gpt-oss.md` § 6.2) ; la PCIe (77 à 92 ms par jeton) et le décodage (54 à 58 ms) deviennent le plafond
vers ×2 ; la démotion ajoute une copie VRAM → RAM par éviction.

### 2.4 H3 : politiques d'éviction à 326 emplacements [mes.]

Amendement n° 2 : une seule capacité (326), les cinq premières lignes déjà lues à 230 sont dites dans `seuils-declares.md`. Succès (`h3-a.csv`, `h3-b.csv`) :

| Trace | LRU | LFU | SLRU 20 % | admission | ETR | Belady (plafond) |
|---|---|---|---|---|---|---|
| code.lecture | 0,358 | 0,381 | 0,289 | 0,421 | 0,448 | 0,649 |
| dialogue.lecture | 0,466 | 0,571 | 0,502 | 0,572 | 0,568 | 0,717 |
| prose-en.lecture | 0,464 | 0,540 | 0,128 | 0,552 | 0,559 | 0,715 |
| prose-fr.lecture | 0,514 | 0,575 | 0,556 | 0,600 | 0,608 | 0,745 |
| **tous.lecture** | 0,453 | 0,426 | 0,091 | 0,534 | 0,547 | 0,708 |
| **prose-en.generation** | **0,738** | 0,663 | 0,257 | 0,645 | 0,727 | 0,838 |

Verdict déclaré (au moins +0,03 sur la meilleure des trois simples sur `tous.lecture` ET sur la génération, au moins +0,01 sur les 4 lectures) : ETR gagne +0,094 sur `tous.lecture`,
**perd 0,011 sur la génération** et −0,004 sur dialogue : **H3 tombe.** L'admission gagne +0,081 en lecture et perd 0,094 en génération : tombe aussi. Témoin : Belady ≥ toute autre politique sur chaque trace : tient.
Limite honnête : une seule trace de génération (256 jetons) ; le moteur fait son préremplissage par flux, donc ce sont les lectures jeton par jeton (conversation longue sans flux) que les gains de lecture concerneraient.

### 2.5 Indicatif, non déclaré avant (dit comme tel)

- **Talus** (courbe LRU convexe) : sur les huit points publiés (230 à 1 843 emplacements), la pente du succès décroît à chaque pas pour `tous.lecture`, `code.lecture` et
  `prose-en.generation` : pas de falaise au-dessus de 230, l'enveloppe convexe est la courbe. Talus n'a rien à retirer à nos budgets [calc.]. La falaise de la proposition 1 est sous 140 emplacements.
- **Cache VRAM en forme codée** (+14,7 % d'emplacements, 374 pour 326) : la part de disque passe de 0,2621 à 0,2411 (−8,0 %) sur la génération et de 0,5472 à 0,4985 (−8,9 %) sur `tous.lecture`
  (`indicatif-cache-code.csv`), au prix d'un décodage à chaque succès.

## 3. Les candidats, classés

Classement : gain attendu × certitude. « Neuf » veut dire : absent du dépôt et des études du dépôt ; ce n'est pas un jugement sur la littérature.

### Candidat 1 (neuf pour troncons, mesuré) : le cache tiède exclusif

- **Ce que le monde fait.** Wong et Wilkes (2002) [lu] montrent qu'un tableau de disques et son client, tous deux en LRU, dupliquent les mêmes blocs, si bien que
  « l'agrégat se comporte comme s'il valait seulement le plus grand des deux » ; leur opération DEMOTE (le client envoie au tableau le bloc qu'il évince) rend le cache *exclusif* et
  double la taille efficace à tailles égales ; accélérations rapportées de 0,97 (TPC-H, tableau de 2 Go) à 2,2 (HTTPD) selon les charges réelles, 7,5 en synthétique aléatoire, et un ralentissement (0,55) quand les clients
  partagent beaucoup de blocs (HTTPD à plusieurs clients ; sans objet ici : un seul client).
- **Problème visé.** Octets lus sur le disque par jeton (686,8 Mo sur le 120b v1.2, 59 % de succès VRAM).
- **Traduction.** `Cache::demander` : la RAM reste le niveau « tiède » ; à chaque éviction VRAM, copier l'expert **décodé** (≈ 13 Mo, MXFP4) vers un emplacement RAM (copie déjà asynchrone,
  sens carte → hôte, la PCIe étant duplex) ; sur un défaut VRAM qui trouve l'expert en RAM : copie RAM → VRAM sans décodage, et libérer l'entrée RAM (« lire-et-retirer ») ; ne pas
  rafraîchir la RAM sur un succès VRAM. Une demande de relecture du disque n'écrit plus en RAM : elle vient du tampon d'arrivée.
- **Expérience qui le juge.** Faite sur trace (§ 2.2, 2.3). Suite, dans le moteur : ABBA inclusif contre exclusif, `--ram-tiede` de 1, 4 puis 8 Go, génération de 256 jetons sur wiki-3000,
  verrou de la carte, machine calme, secteur. Seuil à déclarer avant : gain de jetons/s > 2 × max(bruit des deux bras), le bruit du juge de vitesse étant de 0,2 à 5,8 % (JUGEMENT § 6) ; prédiction : ×1,05 à ×1,10 à 1 Go.
- **Données existantes.** Traces `mesures/localite-gpt-oss/traces-120b/traces-120b.tar.xz`, courbes publiées, `moteur/crates/trc-cache/src/lib.rs` (lignes 153 à 190).
- **Gain attendu.** Octets disque −10 % / −30 % / −48 % (1 / 4 / 8 Go) sur la génération simulée ; ×1,11 / ×1,42 / ×1,92 au plus si le disque limite seul [calc.].
- **Déjà fermé.** Le lemme 2 de `moteur/O-pour-le-memoire.md` démontre l'inclusif ; personne n'a posé l'exclusif. Le coût RAM est une décision de Stone (la fenêtre reste bornée et indépendante de la taille du modèle).

### Candidat 2 (déjà vu dans le monde, avantage mesuré en une direction) : l'éviction qui connaît l'avenir proche

- **Ce que le monde fait.** Hawkeye (Jain et Lin, ISCA 2016) [résumé] rejoue l'algorithme de Belady sur les accès passés (OPTgen) et entraîne un prédicteur « ami / hostile au cache » par signature ;
  Mockingjay (HPCA 2022) [résumé] prédit un temps de réutilisation et évince le plus lointain. Côté MoE en 2026 : *Expert eviction* (NeurIPS 2026) [lu, résumé] ne change que la règle d'éviction,
  avec 16 jetons d'avenir : transferts ÷ 2,1 sans perte, 96 % du gain obtenu contre 27 % pour une règle de fréquence sur le passé seul ; SpecMD [lu] introduit *Least-Stale* (deux files, périmés d'abord)
  et les « collision misses » (un expert évincé puis redemandé dans la même passe).
- **Problème visé.** L'écart à Belady, 10 points sur la génération simulée à 326 emplacements (0,738 → 0,838, soit une baisse relative de 38 % des défauts).
- **Traduction.** Une table (couche, expert) → temps de réutilisation estimé, mise à jour à chaque jeton ; la victime est celle dont la réutilisation prévue est la plus lointaine ; l'avenir proche vient du seul
  signal gratuit du moteur : le routeur de la couche suivante (69 % de justesse) ou les jetons de brouillon d'un décodage spéculatif.
- **Expérience.** Mes cinq politiques sans avenir sont déjà jugées (§ 2.4) : elles ne gagnent pas en génération. Reste : OPTgen en ligne (Belady sur la fenêtre passée, par expert) et la version à avenir de 1 couche (prédicteur simulé à 69 %). Ces deux-là demandent au moins deux traces de génération de plus
  (il n'y en a que deux, 256 jetons chacune : `t120b.prose-en.generation.trace`, `w120b.wiki.generation.trace`) : donc un passage du modèle, soumis au verrou de la carte.
- **Données existantes.** Les deux traces de génération et les 4 lectures du 120b ; `rejouer` dans `trc-cache`.
- **Gain attendu.** Au plus l'écart de Belady : −38 % de défauts sur la génération simulée si l'avenir était parfait ; −10 % à −15 % réalistes avec 69 % de justesse [calc., hypothèse].
- **Déjà fermé.** LFU, admission type TinyLFU, ETR (horloge de couches) : fermés ici sur la génération (§ 2.4). Le préchargement par le routeur est tué par REPRISE-O § 9.2 (−11 %) ; seule la **rétention** (pas la lecture) reste ouverte.

### Candidat 3 (déjà vu, avertissement mesuré) : segments avec listes fantômes (ARC, 2Q, S3-FIFO) à dimensionner par L·k

- **Ce que le monde fait.** S3-FIFO (SOSP 2023) [résumé] : trois files FIFO statiques, la petite filtre les objets vus une seule fois, une liste fantôme garde les identifiants évincés ; 6 594 traces, meilleur taux
  moyen sur 10 jeux de données sur 14. ARC (Megiddo et Modha, 2003) [mém.] : listes fantômes qui règlent seules la part récence / fréquence.
- **Problème visé.** Le SLRU prévu au cahier (probatoire 20 %) est mesuré à 0,257 de succès contre 0,738 (§ 2.4) : il tombe sous la falaise de la proposition 1.
- **Traduction.** Un probatoire d'au moins L·k = 144 emplacements, ou une liste fantôme qui garde les identifiants évincés du probatoire et promeut ceux qui reviennent (le correctif de la falaise).
- **Expérience.** Rejouer ARC et S3-FIFO (petite file de 10 % avec fantôme) sur les 6 traces, seuil à déclarer avant : au moins +0,02 sur LRU à 326 sur la génération et sur `tous.lecture`. Le prior est contre : l'ETR et l'admission, qui exploitent plus d'information, ne l'ont pas obtenu en génération.
- **Données existantes.** Les mêmes traces, `cache2.py` (à étendre de 60 lignes).
- **Gain attendu.** Faible à nul sur la génération ; évite surtout un SLRU perdant. **Déjà fermé** : SLRU à 20 % (§ 2.4).

### Candidat 4 (quasi neuf) : le préchargement qui cède (classe « arrière-plan », LEDBAT, TCP Nice)

- **Ce que le monde fait.** TCP Nice (OSDI 2002) [résumé] et LEDBAT (RFC 6817) [résumé] font passer le trafic d'arrière-plan sous le premier plan : avec Nice, un préchargement agressif a amélioré les requêtes à
  la demande d'un facteur 3, alors que le même préchargement les dégradait d'un facteur 6 sous le contrôle de congestion standard. Cao et al. (SIGMETRICS 1995) [résumé] posent quatre propriétés d'un préchargement-cache intégré
  et prouvent un rapport à l'optimal. Windows expose `FILE_IO_PRIORITY_HINT_INFO` (très bas, bas, normal) [résumé] : un *indice*, dont l'effet dépend des pilotes ; rien trouvé sur son effet sur NVMe.
- **Problème visé.** Le préchargement par le routeur a été tué à −11 % (REPRISE-O § 9.2) parce que ses lectures fausses (31 %) retardent les vraies sur un disque saturé. Le moteur ne tire que 1,55 Go/s utiles sur
  1,848 (fondations lemme B2, iv) : 16 % de temps de disque libre.
- **Traduction.** Une file de lectures à deux classes : la demande passe devant, le préchargement n'occupe le disque que s'il est libre et est annulé dès qu'une demande arrive (`CancelIoEx`), avec un tampon d'arrivée hors cache (pas d'éviction d'un expert utile).
- **Expérience.** Sur le journal chronométré `mesures/moteur/O/csv/chronogramme-120b.csv` (1 048 défauts, 8 jetons) : la fraction du temps de jeton où aucune lecture n'est en vol. Je n'ai **pas** fait la mesure : les colonnes `soumis_ms` et `lu_ms` ne semblent pas avoir la même origine que `copie_debut_ms`
  (94 ms contre 4,6 ms au pas 0, couche 0), et je ne devine pas une horloge. Seuil à déclarer : le préchargement qui cède vaut d'être construit si le temps libre dépasse 10 % du temps de jeton. Puis ABBA dans le moteur.
- **Données existantes.** Ce CSV ; journaux de lecture du lot O ; l'outil de `troncons disque`.
- **Gain attendu.** Au plus 16 % × 0,69 (justesse) ≈ 11 % des octets servis d'avance, moins la pollution : **+3 à +8 %** de jetons/s [calc., hypothèse].
- **Déjà fermé.** Le préchargement qui ne cède pas (−11 %, mesuré). Le recouvrement de calcul (f ≈ 0,17) est son plafond.

### Candidat 5 (HPC, avec perte, demande le modèle) : la précision décidée par appel, sur le résidu (raffinement itératif)

- **Ce que le monde fait.** Haidar, Tomov, Dongarra, Higham (SC18) [résumé] résolvent Ax = b en FP64 par un solveur FP16 puis des corrections sur le résidu : jusqu'à ×4 et un facteur 5 d'énergie. Le principe : calculer vite en basse précision, mesurer l'erreur, ne corriger que si elle compte.
- **Problème visé.** Le mode rapide (base 2,64 bits, KL 0,14) et la politique mixte B3 du cahier (probatoire en rapide, promu en exact).
- **Traduction.** Calculer y_base = W_base x (l'expert rapide, déjà lu), puis décider de lire le complément (1,22 bit) d'après des grandeurs *connues après y_base* : poids du routeur, ‖y_base‖ relatif au résidu, marge du routeur de la couche suivante. B3 décide par la récence ; ceci décide par l'appel.
- **Expérience.** Passe KL sur 10 fenêtres, substitution d'un complément à 3 niveaux d'exigence : ne se fait pas tant que le verrou de la carte existe (lecture lourde du GGUF). Seuil à déclarer : au moins 25 % d'appels servis en base pour une KL appariée égale à l'exact à 2 σ.
- **Données existantes.** Fichiers `.rapide.trc`, journaux de capture ; aucune trace de poids du routeur par appel n'est commitée (les journaux de routage ne portent que les experts et la marge).
- **Gain attendu.** Les octets de 25 % des appels réduits de 29 % : ≈ −7 % d'octets [calc.]. Faible.
- **Déjà fermé.** Le plafond φ ≤ 0,5 et le seuil 0,85 de B3 (05 § 4.10) ; la garde tropicale (57 % des bascules pour 10 % des cellules).

### Candidat 6 (petit) : le cache VRAM en forme codée

- **Ce que le monde fait.** Les caches compressés de la mémoire (échange compressé ; Base-Delta-Immediate, Pekhimenko et al., PACT 2012 [mém.]) gagnent de la capacité en échange d'un décodage à chaque lecture.
- **Problème visé.** Capacité de la VRAM (326 emplacements, 7 %).
- **Traduction.** Garder en VRAM le tronçon rANS (3,70 bits) et non le MXFP4 décodé (4,25) : +14,7 % d'emplacements.
- **Expérience.** § 2.5 : −8,0 % de défauts sur la génération simulée, −8,9 % sur `tous.lecture`. Coût : un décodage (≈ 0,85 ms) par succès, environ 144 par jeton, soit ≈ 120 ms de carte par jeton dans un jeton de ≈ 345 ms : tient si la carte reste sous le disque.
- **Données existantes.** Traces ; chronogramme (décodage 0,85 ms).
- **Gain attendu.** −8 % d'octets disque, ×1,08 au mieux ; pris entièrement par le candidat 1 s'il est construit (la RAM exclusive fait déjà mieux).
- **Déjà fermé.** Non ; mais dominé.

### Candidat 7 (fermé par le calcul) : Talus, le cache sans falaise

- **Ce que le monde fait.** Talus (HPCA 2015) [lu, résumé] sépare le flux d'accès en deux partitions pour que le taux de défauts décroisse de façon convexe avec la capacité ; Cliffhanger (NSDI 2016) [résumé] détecte les falaises par deux files fantômes (36,7 % de défauts en moins sur Memcachier).
- **Problème visé.** La falaise du LRU global sous (L−1)·k emplacements (proposition 1).
- **Traduction.** Deux partitions pseudo-aléatoires de la VRAM, de tailles tirées de l'enveloppe convexe de la courbe de défauts.
- **Expérience.** § 2.5 : au-dessus de 230 emplacements la courbe publiée est déjà convexe en défauts ; la falaise est sous 140, loin de 326. Calculé, non déclaré avant.
- **Gain attendu.** Nul à 326 [calc.]. Utile seulement si la VRAM disponible tombait sous 140 emplacements (1,86 Go).
- **Déjà fermé.** Oui, par la courbe publiée.

## 4. Neuf contre déjà vu

| Candidat | Nouveau pour troncons | Nouveau dans le monde |
|---|---|---|
| 1. cache tiède exclusif | oui, et mesuré | non (Wong et Wilkes 2002) ; des MoE à deux niveaux existent (ExpertFlow, FlashMoE [métadonnées]) mais je n'ai pas lu qu'ils traitent l'inclusion |
| 2. éviction à avenir proche | partiellement (posé en point 10 de REPRISE-O, jamais construit) | non (NeurIPS 2026, Hawkeye, Mockingjay) |
| 3. fantômes et dimensionnement | oui pour le dimensionnement par L·k | non |
| 4. préchargement qui cède | quasi (le préchargement a été tué sans la file à deux classes) | non (Nice, LEDBAT) ; son effet sur NVMe Windows est inconnu |
| 5. raffinement sur résidu | non (B3 existe) | non |
| 6. cache codé | oui | non |
| 7. Talus | — fermé | — |

Aucun candidat de cette bande n'est une idée neuve au sens du monde : l'apport de l'ingénierie existante est ici **un diagnostic de défaut** (le tiède inclusif) et des garde-fous mesurés, pas une invention.

## 5. Ce qui pourrait être faux

- Les traces de génération sont deux, de 256 jetons, en partie dégénérées : le niveau absolu de succès du moteur (0,59) n'est pas celui de la trace (0,74). Les **baisses relatives** de H2 sont plus fiables que les niveaux ; elles ne sont pas confirmées dans le moteur.
- Le simulateur ne modélise ni le coût de la démotion, ni la fragmentation de la RAM, ni l'engagement mémoire de Windows (7,9 Go engagés avec 1 Go de tiède, épreuve J1 m3). 8 Go de RAM tiède sur 15,6 est probablement trop ; 1 à 4 Go sont plausibles.
- Dans l'exclusif simulé, l'expert descendu est supposé décodé et gardé tel quel : la RAM tiède du moteur contient aujourd'hui le tronçon *codé* ; la version décodée pèse 13,2 Mo contre ≈ 11,9, soit 11 % d'entrées de moins pour la même RAM (non corrigé ici, R est compté en entrées).
- H3 est jugée à une capacité et sur six traces ; ETR et l'admission ont des paramètres fixés a priori, aucun réglage : un meilleur réglage pourrait changer le verdict. Ce n'est pas une preuve qu'aucun réglage ne gagne.
- Le T2 déclaré est tombé comme témoin (§ 2.1). Le simulateur est validé par T1 (10⁻⁵), T2b et T3, non par T2.
- Les sources marquées [résumé] n'ont pas été lues en entier ; leurs chiffres (par exemple 36,7 % de Cliffhanger, ×3 et ×6 de TCP Nice) sont ceux de leurs résumés.
- Un autre éclaireur du même flux s'occupe d'éviction (commits « Mimétisme physique E3 » et « du vivant E-J » du 2026-10-26) : des recoupements sont possibles, non vérifiés.

## 6. Reprise

- Fait : seuils, simulateur, témoins, H1, H2, H3, indicatifs, ce document. Tout est commité.
- Pas lancé : tout ce qui lit un fichier modèle (verrou de la carte présent), tout ce qui demande un passage du modèle (traces de génération, KL).
- Suivant, dans l'ordre : (a) déclarer puis faire l'ABBA du candidat 1 dans le moteur ; (b) rejouer ARC et S3-FIFO (candidat 3) ; (c) dès que le verrou est rendu, deux traces de génération de plus pour le candidat 2.
