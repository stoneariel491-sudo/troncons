# P3, routeur biaisé en ligne : SECOND TIRAGE sur un autre texte, déclaré avant toute passe (2026-10-27)

Écrit avant : toute passe du moteur sur le nouveau texte. Au moment où j'écris, aucune trace, aucun compte de défauts, aucune
KL, aucun `.kld` du moteur sur ces fenêtres n'existe. Ce qui est lu pour fixer ceci : `SOCLE.md`, `06-routeur-ligne-declare.md`,
`genome/mimetisme/P3/resultat-routeur-ligne.md`, `JUGEMENT-routeur-ligne.md` (G1, § 3.2 à 3.3, mineurs), le pilote
`p3_routeur_ligne.py`, l'analyse `p3_routeur_ligne_analyse.py`, le juge `juge/routeur-ligne/juge_routeur_ligne.py`.

## 0. Pourquoi un second tirage

Le juge a reproduit le premier tirage au dernier chiffre, puis a montré (G1) que « tient » ne vaut qu'à l'estimation d'**un**
tirage : une série de 10 fenêtres (R1), un budget (238), un texte. Aucune des trois conditions ne tenait à sa borne par fenêtres
(KL haute > 0,038 pour 20 graines sur 20, pondéré bas sous 95 % pour 14 sur 20, 31 défauts de marge). Le levier ne peut servir
de brique que si un **second tirage sur un autre texte** le confirme. Ce document fixe ce tirage.

## 1. Le texte, disjoint de R1

- **Fichier de base** : `~/dev/essais/troncons/genome/juge/base-juge-20b.kld` (1 025 589 700 octets), SHA-256
  `2108487dfb63cc6099b69cec6962893bf8964a9e7a769231b2774bb7e81a50a4` (relevé aujourd'hui, égal à celui de
  `mesures/genome/construction/juge/fenetres-fondre.json`, commit `af77cd6`). Format du `.kld` de `llama-perplexity` (mêmes
  `n_ctx = 512`, 10 fenêtres, 5 120 pas, 2 550 positions notées, vocabulaire 201 088 : même géométrie que R1, donc même banc).
- **Origine** : « fenêtres neuves du juge » du dossier de construction (`mesures/genome/construction/juge/00-seuils-declares.md`,
  `outils/genome/construction/juge/fenetres_juge.py`) : dix extraits de `wiki.test.raw` (SHA-256 `173c87a5…dd08`, 1 290 590 octets),
  chacun tiré à un début de paragraphe **au-delà des 120 000 premiers octets**, à plus de 12 000 octets les uns des autres
  (débuts à 358 205, 421 030, 511 976, 615 155, 767 283, 854 814, 1 098 980, 1 148 495, 1 228 294, 1 240 966), 9 000 octets
  prolongés jusqu'à la fin de ligne, une fenêtre de 512 jetons par extrait. Tirage commité avant toute passe du moteur sur eux
  (graine 20261023).
- **Disjoint de R1 [mes., relevé aujourd'hui sur les en-têtes des deux fichiers]** : les 120 000 premiers octets comptent 27 680 jetons
  et couvrent R1 (jetons 0 à 5 119) et la calibration du génome (jetons 5 120 à 11 263) ; aucun jeton de R1 n'est dans un octet
  ≥ 358 205. Test sur les jetons : **0 fenêtre égale** entre les 10 fenêtres de R1 et les 10 nouvelles, **0 8-gramme de jetons
  commun** (5 001 8-grammes dans le nouveau texte) ; 74 3-grammes communs sur 4 634 et 407 jetons distincts communs (1 503 contre
  1 848) : du vocabulaire de wikipédia partagé, aucune phrase.
- **Référence f64 de ce texte** : elle **existe** (`.../genome/juge/ref-juge-20b.kld`, SHA-256 `a84cb11c…a639`, construite par le
  juge du dossier de construction avec l'appel de R1 ; jetons égaux à ceux de la base, relevé aujourd'hui). Pour rester identique
  au premier tirage, **la base de comparaison reste le même moteur sans biais (`P0`)** (grandeur = effet du biais, pas écart du
  moteur à la référence) ; la KL contre la référence f64 est rapportée à titre d'information, comme au premier tirage.
- **Différence de nature avec R1, à lire avant les chiffres** : R1 est un texte continu (10 fenêtres consécutives) ; ce texte est
  fait de dix paragraphes pris à dix endroits du corpus (le moteur réinitialise le KV à chaque fenêtre dans les deux cas ; le cache
  d'experts, lui, traverse les fenêtres dans les deux cas). C'est voulu (autre texte), et c'est une différence de plus entre les
  deux tirages que je ne pourrai pas séparer d'un effet de texte.

## 2. Ce qui est identique au premier tirage (rien n'est réglé pour ce texte)

Moteur construit au commit `eb78770` (binaire `~/dev/cibles/troncons-P3/release/troncons.exe`, inchangé), `gpt-oss-20b.trc`,
carte graphique, **238 emplacements**, LRU, quatre fils, secteur, `--fenetres 10 --positions 512`, **β₁ = 0,041** (la valeur du
premier tirage, **non réajustée** : elle a été choisie sur R1 ; ici elle est transférée telle quelle, c'est l'objet de l'épreuve),
cassure β = 0,3. Un tirage par β, **aucun rejeu pour choisir le meilleur** ; une passe qui s'arrête par garde-fou est relancée à
l'identique et le dit.

## 3. Passes (ordre, un seul processus à la fois, jamais d'analyse pendant une passe)

1. `P0` : sans le drapeau (base de comparaison).
2. `B0.041` : `--biais-cache 0,041` (décisif).
3. `P0b` : `--biais-cache 0` (témoin T0).
4. `B0.3` : `--biais-cache 0,3` (cassure), si le temps et le disque le permettent.

Non faites dans ce tirage, dites d'avance : β₂ = 0,05 (pente), cassure de signe, préfixe P-1 (le défaut n'a pas bougé : même binaire
que le premier tirage, déjà prouvé), vitesse (le premier tirage n'a conclu à aucun gain ; rien de nouveau à mesurer en séance non
calme).

## 4. Grandeurs et seuils (ceux de P3, repris tels quels ; aucun nouveau)

| # | grandeur | seuil | estimation | borne décisive |
|---|---|---|---|---|
| T1 | défauts de cache, `defauts_disque` de `B0.041` contre `P0` | ≤ −10 % | compteur du moteur, recoupé par `rejouer` et par un LRU Python | marge ≥ 0 défaut sous **chacune** des conventions de comptage compatibles avec le protocole (ordre de service, inverse, par indice, au hasard 5 graines, cache chaud, cache plein au départ), rejeu sur la trace comme dans le jugement |
| T2 | KL excédentaire `KL(P0 ‖ B0.041)`, moyenne des 2 550 positions notées | ≤ 0,038 | `juge kl` (chemin A), lecteur de l'étage B (chemin B), lecteur du juge (chemin C), égaux à 1e-6 | borne **haute** de l'intervalle par **blocs de 51 positions** (50 blocs ; 255 positions par fenêtre = 5 blocs exacts par fenêtre), 95 %, 20 000 tirages |
| T3 | premier choix identique, **pondéré** (positions où la marge logit 1er − 2e de `P0` ≥ 0,3) | ≥ 95 % | argmax de `B0.041` = argmax de `P0` | borne **basse** de l'intervalle par **blocs de 51 positions**, mêmes réglages |

Rapportés à côté, **sans décider** : intervalles par **fenêtres** (10 fenêtres, 20 000 tirages, graine 1 puis 20 graines : combien
de graines mettent la borne du mauvais côté du seuil), premier choix **littéral** (≥ 95 % : lecture sévère, « non concluant » au
premier tirage à 88,55 %, llama.cpp lui-même à 92,55 %), sensibilité du pondéré au seuil de marge (0,1 à 0,5, post hoc),
défauts « cache vidé à chaque fenêtre » et aux budgets voisins 230, 234, 242, 246 (fil de rasoir du premier tirage), bascule des
défauts par fenêtre de 512 pas (bootstrap par fenêtres), KL contre la référence f64, part de cellules à ensemble changé par couche,
rapport KL / part changée.

## 5. Règle de lecture (écrite avant)

Pour ce tirage :

- **TIENT (robuste)** : T1, T2, T3 tiennent à l'estimation **et** aux bornes décisives du § 4.
- **TIENT à l'estimation seulement** : T1, T2, T3 tiennent à l'estimation, au moins une borne décisive est du mauvais côté.
- **NON CONCLUANT** : au moins une des trois conditions échoue à l'estimation, avec KL ≤ 0,07.
- **TOMBE** : KL > 0,07 à β₁.

Pour le verdict de P3 (deux tirages) : « tient » **seulement si les deux tirages sont TIENT (robuste)** (le premier l'est aux seuils de
ce document : bornes par blocs de 51 [0,0264 ; 0,0370] et [95,21 ; 97,40], marge de défauts ≥ 4,6 sous les conventions
compatibles, JUGEMENT-routeur-ligne § 3.2 et 3.3). Si le second tirage est « TIENT à l'estimation seulement », P3 reste « tient,
à la limite, non robuste » ; **si le second tirage tombe sous un seuil à l'estimation, le verdict de P3 devient NON CONCLUANT (ou
TOMBE si KL > 0,07)** et le levier n'est pas utilisé tel quel. Un seul tirage de plus ne montre pas une loi : la conclusion ne
dépasse pas « confirmé / non confirmé sur un second texte de même taille ».

## 6. Témoins et cassures

- **T0 (β = 0 au bit)** : `P0b` égale `P0` sur les **5 120 empreintes64 de logits** (CSV), la **trace**, et le **`.kld`** (SHA-256
  relevé par le pilote à la fin de chaque passe ; le fichier de `P0b` est effacé ensuite parce qu'égal à celui de `P0`, l'empreinte
  reste dans le journal). Cassure de l'instrument de comparaison : `B0.041` contre `P0` doit différer sur presque toutes les lignes
  d'empreintes (au premier tirage : 5 118 sur 5 121).
- **Cassure du critère (β = 0,3)** : la porte doit tomber. Prédiction (§ 7) : KL entre 0,07 et 0,12, pondéré < 95 %, défauts plus
  forts que −35 %. Si elle ne tombe pas, l'instrument est dit aveugle et rien ne tient.
- **Cassure de mon LRU Python** (chacune doit changer le compte) : 1 000 cellules tirées au hasard dans la trace de `P0` ; budget 237.
- **Cassure du lecteur** : décalage d'une position du test contre la base, le pondéré doit s'effondrer (14 % au premier tirage).
- Second chemin : trois lecteurs de KL et de premier choix (chemin A `juge kl`, chemin B lecteur de l'étage B, chemin C lecteur du juge
  `juge_routeur_ligne.Kld`), trois comptes de défauts (moteur, `rejouer` sur la trace, LRU Python à règle de groupe).

## 7. Prédictions chiffrées, écrites avant toute passe

Point de départ : le premier tirage (défauts −10,03 %, KL 0,0314, pondéré 96,36 %, cellules changées 12,86 %) et ses dispersions
(KL par fenêtre de 0,0146 à 0,0502, pondéré par fenêtre de 92,7 à 100 %, bornes par fenêtres [0,0245 ; 0,0384] et [95,00 ; 97,68]).
Je suppose le texte neuf semblable à R1 en difficulté (PPL du moteur sur R1 : 462 ; sur ce texte, la PPL de la base llama.cpp vaut 392,5 d'après
`mesures/genome/construction/juge/kl/juge-kl-neuf-moteur-exact-20b.json`).

| grandeur à β₁ = 0,041 | centre | bande (≈ 80 %) |
|---|---|---|
| défauts de `P0` par pas | 21 | 18 à 25 |
| variation des défauts | **−10,0 %** | −7,5 à −12,5 % (écart d'un texte à l'autre de l'ordre de un point : **T1 a environ une chance sur deux**) |
| cellules à ensemble changé | 12,9 % | 10 à 16 % |
| **KL excédentaire** | **0,031** | **0,020 à 0,045** (écart-type attendu du texte ≈ 0,006 ; sous 0,038 avec probabilité ≈ 75 à 80 %) |
| premier choix pondéré | 96,3 % | 94,3 à 98,0 % (≥ 95 % avec probabilité ≈ 80 %) |
| premier choix littéral | 88,5 % | 86 à 91 % |
| KL contre la référence f64 (info) | 0,035 | 0,022 à 0,050 |
| KL(réf. f64 ‖ `P0`) (info) | 0,004 | 0,002 à 0,009 |
| rapport KL / part changée | 0,24 | 0,18 à 0,30 |
| bornes par blocs de 51 | KL haute 0,037, pondéré bas 95,2 % | bien plus étroites que par fenêtres ; la KL haute passe sous 0,038 avec probabilité ≈ 55 %, le pondéré bas au-dessus de 95 % avec probabilité ≈ 65 % |

Les trois conditions sont liées (plus d'échanges retirent plus de défauts et coûtent plus de KL) ; en les croyant à moitié
indépendantes, **la probabilité que le second tirage soit TIENT à l'estimation est d'environ 35 %, TIENT (robuste) d'environ
15 à 20 %**. Le plus probable est que T1 (défauts) ou T2 (KL) tombe du mauvais côté de justesse : je m'attends à un résultat « à la
limite » une seconde fois, ce qui serait lui-même l'information (le levier est un fil de rasoir à 238 emplacements).

Cassure β = 0,3 : défauts −45 à −58 % (centre −53 %), KL 0,07 à 0,12 (centre 0,09), pondéré 85 à 92 %, littéral 74 à 80 %.

## 8. Garde-fous de séance

Verrou de la carte `~/dev/verrou-carte.txt` posé avant (« P3 second tirage, agent, heure »), libre vérifié, supprimé à la
fin ou en cas d'échec. Secteur branché. **C: libre ≥ 25 Go au lancement, sinon arrêt et dit** (relevé de départ : 24,1 puis 21,3 Go
libres ; libéré ensuite 4 Go en effaçant quatre doublons de fichiers de R0 vérifiés égaux octet pour octet à leur original par
SHA-256, voir la note de reprise). Pendant une passe : arrêt propre si le secteur est coupé 3 relevés de suite, si C: libre tombe
sous 15 Go, si le swap dépasse 4 Go, si la RAM disponible reste sous 0,4 Go trois relevés de suite ; RAM disponible ≈ 3 Go
souhaitée avant chaque passe (pointe du moteur ≈ 2,3 Go), j'attends que la machine se libère plutôt que de lancer sur une machine
saturée. Passes séquentielles, quatre fils pour tout ce qui est hôte. Aucun processus que je n'ai pas lancé n'est touché.
