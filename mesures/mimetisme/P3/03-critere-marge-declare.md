# P3, étage B à N = 238 : critère pondéré par la marge, déclaré avant toute passe neuve (2026-10-27)

Écrit avant : le calcul des ensembles biaisés à N = 238, toute passe de la référence, toute lecture d'un résultat à N = 238. Aucune KL ni aucun premier choix de N = 238 n'existe au moment où j'écris.

## (a) Ce que ce texte est : une décision prise après lecture

Cette décision est prise **APRÈS avoir lu les résultats de N = 146** (`genome/mimetisme/P3/resultat-etage-B.md` et `JUGEMENT-etage-B.md`) : premier choix identique **88,4 %** (β = 0,06) et **87,6 %** (β = 0,07), contre le seuil littéral de 95 % de `00-seuils-declares.md` § 3. Le juge y a aussi lu, post hoc, que le premier choix remonte à 97,4 % et 97,2 % sur les positions dont la marge de la référence vaut au moins 0,3 logit, et à 93,7 % et 93,2 % au-dessus de 0,1.

Je choisis donc le seuil de marge **en connaissant le chiffre qu'il rendait sur N = 146**. C'est un critère construit pour que la mesure déjà faite ne soit pas jugée sur ses quasi-égalités : il serait malhonnête de le présenter comme un seuil posé à l'aveugle. Le seuil de 95 % lui-même (sur toutes les positions) n'avait pas été dérivé d'une grandeur mesurée (`resultat-etage-B.md` § 1) ; la marge de 0,3 ne l'est pas non plus, sauf par le raisonnement ci-dessous.

Raison de fond, indépendante du chiffre lu : prendre le 2e expert de sortie au lieu du 1er sur un jeton coûte au plus la marge (log p1 − log p2, en nats) en log-probabilité sur ce jeton quand la référence est la vérité ; une bascule à marge < 0,3 est donc une bascule bon marché, et une bascule à marge ≥ 0,3 est la seule qui change visiblement la réponse. Le critère pondéré compte uniquement ces dernières.

## (b) Le critère

Marge d'une position = log p(1er) − log p(2e) de la référence `ref-openai-20b` (la colonne `marge_ref` du juge, égale à l'écart de logits, résolution du codage ≤ 2,5e-4), propre à la position et indépendante de la passe testée. Positions jugées : les 2 550 positions notées (10 fenêtres de 511, 255 non notées par fenêtre), comme à N = 146.

**Lecture pondérée (celle qui décide si elle tient)** : « tient » exige, au même β,
1. au moins 10 % de défauts de cache en moins que β = 0 à N = 238 (journaux imposés rejoués, LRU global à règle de groupe) ;
2. KL excédentaire ≤ 0,038 (inchangé) ;
3. premier choix identique ≥ **95 %** sur les positions dont la marge de la référence est **≥ 0,3 logit** (≈ 63 % des positions : 37,2 % sont sous 0,3, relevé du juge).

**Lecture littérale (rapportée à côté, reste la lecture sévère)** : mêmes conditions 1 et 2, et premier choix identique ≥ 95 % sur **toutes** les positions (`00-seuils-declares.md` § 3, inchangé).

Les deux lectures sont calculées sur les mêmes passes et rapportées avec leur verdict : tient / tombe / non concluant. « Tombe » reste : KL > 0,07 au β à −10 % de défauts, ou aucun β à −5 % avec KL ≤ 0,038 ; je n'invente pas de seuil « tombe » sur le premier choix (un premier choix pondéré sous 95 % avec KL ≤ 0,038 est « non concluant »).

Règles d'application, fixées maintenant :
- la décision porte sur l'estimation ponctuelle (comme tous les seuils du projet) ; l'intervalle par rééchantillonnage des 10 fenêtres (20 000 tirages) est rapporté, et si l'estimation passe 95 % alors que la borne basse de l'intervalle est dessous, le résultat est dit « tient à l'estimation, non établi à l'intervalle » ;
- la marge 0,1 et la proportion de désaccords par tranche de marge sont rapportées pour information, non comme critère ;
- le critère est appliqué au β qui atteint le premier −10 % de défauts (β₁, défini à l'étape suivante) ; l'autre β passé est lu comme pente, non comme second essai de chance : s'il passe et pas β₁, c'est β₁ qui compte pour « tient ».

## (c) Ce que N = 146 ne peut pas établir

Le critère pondéré **ne peut pas être validé par N = 146** : ces passes sont déjà lues et c'est elles qui l'ont inspiré. Les 97,4 % / 97,2 % de N = 146 sont consistants avec lui mais n'ont aucune valeur de test. **Seul N = 238 (passes neuves) compte.** Un « tient » issu de N = 238 seul est dit **partiel** (un seul budget, boucle ouverte, texte de lecture) ; la condition « aux deux budgets » du tri n'est pas satisfaite à la lecture pondérée, puisque N = 146 ne peut pas la porter.

Prédiction écrite avant (à N = 238, β₁ ≈ 0,041, donc une part de cellules changées plus faible qu'à N = 146) : premier choix littéral entre 88 et 95 % ; premier choix pondéré supérieur à 96 % ; KL entre 0,01 et 0,025. Je ne sais pas si les trois tiendront : à N = 146 le rapport KL / part de cellules changées était 0,174, et c'est ce que je rapporterai à la part de cellules changées calculée à l'étape suivante.

## (d) Témoin et cassure

Réutilisés de N = 146 sans les relancer, parce que **leurs fichiers de référence sont identiques** (vérifié ce jour, empreintes SHA-256) :
- Témoin T0 (β = 0) : le journal imposé de β = 0 est le même octet pour octet aux deux budgets (e908eb93…baf6 à N19 et à N31, le routage non biaisé ne dépend pas du budget) ; `ref-openai-20b.kld` = `ref-openai-p3-T0-20b.kld` = d97fc421…2a38 (KL nulle au bit, premier choix 100 %).
- Cassure T1 : `routage-impose-CASSURE-1pct.bin` (23db486b…6046, 1 226 cellules à 4e expert aléatoire) construite sur les ensembles β = 0, donc indépendante du budget ; `ref-openai-p3-T1-20b.kld` = 3f922699…431f, KL 2,08e-3 > 1e-4 déclaré : le témoin tombe comme exigé.
- Ajout propre à N = 238, contrôle de la chaîne d'imposition sur les fichiers neufs : (i) les copies lues par le moteur ont l'empreinte du fichier voulu ; (ii) le routage que chaque passe enregistre porte, cellule par cellule, les quatre experts imposés. Ce contrôle peut échouer : si une cellule diffère, la passe est jugée invalide, non corrigée.

Si l'une des empreintes ci-dessus avait changé, T0 et T1 auraient été relancés ; elles n'ont pas changé.

## (e) Quatre fils, comme avant

Les passes tournent avec `--fils 4` (`FILS = "4"` dans `r1_reference.py`), comme la référence du 15 octobre et les quatre passes de N = 146. Le témoin au bit de N = 146 montre que le nombre de fils ne change pas le résultat. Le cahier comptait « 2 fils » ; je le dis, je ne le change pas.

## Garde-fous de séance (reprise de l'étage B, durcis sur le swap)

Verrou de la carte `~/dev/verrou-carte.txt` écrit avant (« P3 N=238, agent, heure ») et supprimé à la fin ou en cas d'échec ; secteur branché exigé ; C: libre > 30 Go ; RAM de pointe attendue 2,3 Go pour ~3 Go libres ; **arrêt propre si le swap dépasse 4 Go** (nouveau, N = 146 avait atteint 2,25 Go), si la RAM disponible reste sous 0,4 Go pendant 3 relevés, si le secteur est coupé ou si C: tombe sous 30 Go. Deux passes, l'une après l'autre.

## Second chemin

Le chiffre principal (KL, premiers choix littéral et pondéré) est recalculé par un chemin sans `juge kl` : numpy depuis le CSV par position (KL moyenne, accord des premiers choix, jointure avec la marge de référence), et, en plus, relu des `.kld` par le lecteur indépendant du juge (`outils/mimetisme/P3/juge/etageB_juge.py`, écrit sans importer le code de l'étage B).
