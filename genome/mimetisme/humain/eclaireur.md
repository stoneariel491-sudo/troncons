# Éclaireur « systèmes humains » : ce que le monde des hommes a à dire au disque de troncons

Rôle : éclaireur du domaine économie et marchés, logistique et chaînes d'approvisionnement, villes et transport,
bibliothèques et archives, langues, écriture, musique, droit, éducation, jeux et sports, médecine et triage, assurance,
organisation. Date : 2026-10-26 et 27. Consigne de Stone du 2026-10-26 : « du mimétisme absolu, peu importe les échelles
et les concepts », et des mécanismes dont l'effet est MESURÉ sur nos données.

Étiquettes : **[mes.]** mesuré ici (outil et journal commités) ; **[calc.]** calculé sur des mesures commitées ;
**[lu]** page de résumé d'une source primaire lue ce jour (arXiv, ACL, DSpace), pas le texte intégral ; **[mém.]**
de mémoire, non relu ; **[hyp.]** hypothèse dite. Aucune analogie n'est présentée comme un résultat.

Fichiers : seuils `mesures/mimetisme/humain/00-seuils-declares.md` (commités avant les outils et deux fois amendés avant les
mesures concernées), outils `outils/mimetisme/humain/`, journaux et résultats `mesures/mimetisme/humain/`.
Cohabitation : le verrou de carte existait (`verrou-carte.txt`, séance du juge du placement) ; je n'ai lu aucun fichier
modèle, seulement les traces de routage (8 Mo), leurs poids de mélange, le journal de routage du juge (1 Mo) et des CSV de KL
par fenêtre. Aucune carte. Un fil, sauf pendant quelques minutes où trois processus ont tourné ensemble (j'ai dépassé les deux
fils prévus, de peu et sans conséquence mesurable ; je le dis).

---

## 0. En bref

1. **Le domaine a donné une mesure qui tient son seuil, et une seule** : le raisonnement par cas (la jurisprudence, le filtrage
   « ceux qui ont pris X prennent aussi Y ») transposé en **prédiction des experts d'une couche lointaine par les précédents du
   chemin de routage**, sans état caché ni passe du modèle. Rappel des 4 experts à deux couches d'avance, en ligne : **0,72 (20b)
   et 0,57 (120b)** contre 0,52 et 0,28 pour la meilleure base ; critère déclaré (+0,15) tenu sur les deux modèles. Mais la
   **couverture des défauts de cache** est plus basse que le rappel (51 % sur le 20b, 34 % sur le 120b sans seuil de confiance)
   et coûte 42 à 55 % de chargements inutiles : le gain est un recouvrement, pas des octets en moins (§ 2.4).
2. **Cinq mécanismes d'autres métiers tombent aux seuils déclarés**, chacun pour une raison que le chiffre dit (mémoire à loi de
   puissance, tri par poids de mélange, allocation marginale par couche, classes ABC, routage conscient du cache borné par la
   marge). Ces échecs sont des cartes de ce qui est fermé, pas des analogies perdues (§ 2.1 à 2.3, 2.5, 2.7).
3. **Une idée rare, non mesurée faute de donnée** : un contrôleur de fidélité à tampon sur le modèle des lecteurs vidéo (BOLA).
   Aucune source trouvée ne le relie au déchargement d'experts. Sa mesure attend une courbe KL en fonction de la part d'experts
   servis en mode rapide, qui demande la carte ou le f64 (§ 3, candidat 2).
4. **Une idée de méthode, mesurée sur nos journaux** : l'arrêt séquentiel de groupe (essais cliniques) rejoué sur sept séries de
   KL par fenêtre économise 32 % des fenêtres sur les séries décisives, avec un arrêt précoce faux sur une série (§ 2.6).
5. **Une découverte annexe, la plus rentable pour son prix** : le LFU du dépôt (demi-vie 8 jetons) n'est pas à son optimum. Une demi-vie de 32 jetons rend
   **+2,0 et +2,1 points de succès sur le 120b** (15 et 20 % : 0,7241 → 0,7444 et 0,7942 → 0,8151), dans les quatre genres pris seuls (+0,9 à +3,2 points),
   soit environ 10 % de défauts en moins à 20 % ; +0,6 et +0,7 point sur le 20b (§ 2.1). Réglage post hoc, sur les mêmes traces, mais un seul paramètre et un plateau de 16 à 128.

---

## D'où on part, où on va

**Au départ** (dépôt) : le cache global LRU/LFU/statique/Belady mesuré sur 10 669 jetons par modèle (`mesures/gpt-oss.md` § 6 :
à 20 % Belady 0,81 contre LFU 0,68 sur le 20b, et « il y a 29 points de succès en VRAM à prendre par une meilleure politique ou
un prédicteur ») ; le trou nommé § 10 « mesurer un prédicteur réel » ; la garde tropicale tombée (57,1 % des bascules pour 10 %
des cellules) ; la fermeture du génome des poids (graine, S*, duplication, hebbien, spectres : tout est du bruit une fois
l'échelle connue) ; le routage conscient du cache et HOBBIT connus en littérature (`fondations/04-chargement.md` § 3.4, § 3.6),
jamais mesurés sur gpt-oss.

**Ce que ce document établit** : ce que vaut, sur les traces gpt-oss existantes, chaque mécanisme venu des systèmes humains ;
un seul tient (§ 2.4), un autre est une idée neuve sans mesure possible aujourd'hui (§ 3.2).

**Ce qui reste** : § 5.

---

## 1. Ce que j'ai observé dans le domaine

Parcouru, avec ce qui en sort pour un disque à 2,8 Go/s et des poids qui sont du bruit :

| Terrain | Ce que le monde y fait réellement | Verdict pour troncons |
|---|---|---|
| **Mémoire humaine** (psychologie, apprentissage) | La probabilité qu'une information soit utile suit sa fréquence et sa récence d'usage selon une loi de puissance, et la mémoire humaine a cette forme parce qu'elle est adaptée à l'environnement (Anderson et Schooler 1991 [lu : résumé]). La répétition espacée la met en équation (Settles et Meeder, ACL 2016 : demi-vie estimée par régression [lu : titre, auteurs, lieu ; résumé via recherche]). | **Mesuré, tombe** (E1) : la loi de puissance ne bat pas le LFU à demi-vie. |
| **Commerce et chaînes d'approvisionnement** | Stock de pièces à plusieurs échelons : METRIC (Sherbrooke 1968 [mém.]) alloue les pièces par gain marginal sous budget. Substitution de produit en rupture : on sert l'article proche déjà en rayon. Rangement d'entrepôt par corrélation des commandes : 25 % de déplacement en moins en moyenne (revue de Islam et Uddin 2023 [lu : résumé]). | **Allocation marginale mesurée, tombe** (E3). Rangement par corrélation : fermé par le placement (la position ne dit rien du débit, 08). Substitution : voir routage conscient du cache (E7). |
| **Raisonnement par cas** (droit, médecine) | On décide à partir des précédents les plus proches du cas présent, au lieu d'une règle (jurisprudence ; diagnostic par cas semblables) [mém.]. | **Mesuré, tient** (E4, E4b) : seule mesure qui passe. |
| **Triage médical** | Ressource rare donnée selon la gravité, évaluée par un signal peu coûteux. | **Mesuré, tombe** (E2) : les poids de mélange de gpt-oss sont plats. |
| **Vidéo en continu** (ingénierie des services, pas de la nature) | Un lecteur choisit pour chaque segment un débit parmi une échelle selon le tampon, sans prédire la bande passante, avec garantie : BOLA (Spiteri, Urgaonkar, Sitaraman, INFOCOM 2016, arXiv 1601.06748, v1 2016-01-25, v3 2020-06-18) [lu : résumé]. | **Idée rare, non mesurable aujourd'hui** (§ 3.2). |
| **Essais cliniques** | Les analyses intermédiaires avec frontière d'arrêt permettent de conclure tôt sans gonfler l'erreur : O'Brien et Fleming, Biometrics 35, 1979 [lu : résumé] | **Mesuré sur nos journaux** (E6) : économie réelle, un arrêt faux. |
| **Équilibrage de charge** | Deux choix au hasard et on prend le moins chargé : gain exponentiel (Mitzenmacher, IEEE TPDS 2001 [lu : résumé]). | Mène au routage conscient du cache, borné par la marge (E7). |
| **Inventaire : analyse ABC** | 20 % des références font 80 % du mouvement ; on gère chaque classe autrement. | **Mesuré, tombe** (E5) : la moitié rare ne porte que 9 à 14 % des accès, mais n'est pas la même d'un genre à l'autre. |
| **Langues, écriture, musique, bibliothèques, assurance, jeux** | Zipf (code court aux mots fréquents : déjà l'entropie), abréviation et sténo (briefs : déjà le codage de séquences, le voisin n'apporte que 0,005 bit), courbe de Hilbert de rangement (fermée, 05 § 3.3c), mise en commun des risques (la racine carrée de Eppen 1979 [mém.] : le cache partagé entre couches, déjà mesuré), partitions et ouvertures d'échecs (tables de transposition : mémoïsation, sans objet pour des poids). | Rien de neuf qui ne soit déjà le cadre de l'entropie, du cache ou du placement. Dit pour que personne ne refasse le tour. |

Ce que le tour montre : les systèmes humains sont riches en **politiques de gestion de stock sous incertitude** (quoi garder, quoi
commander d'avance, quand arrêter de chercher) et pauvres en **représentation de l'information** : la représentation, c'est la
nature et les mathématiques qui la fournissent. Pour un goulot disque, c'est le bon étage : les poids sont fermés, les politiques ne le sont pas.

---

## 2. Les mesures

Données : traces de routage de lecture du dépôt, préfixes t20b et t120b (4 genres : code, dialogue, prose anglaise, prose
française ; 2 378 à 2 887 jetons chacun côté 20b ; 24 couches × 32 experts × top-4 ; 36 × 128 × top-4 pour le 120b), leurs poids
de mélange (`.poids`), le journal de routage de la référence f64 du juge (5 110 positions, marge du 4e au 5e logit) et sept séries
de KL par fenêtre du juge. Instruments LRU, LFU et Belady : ceux du dépôt (`gptoss_localite.py`), importés, non recopiés.
Ce que ces traces sont : du **préremplissage** (lecture du texte), pas de la génération ; la localité y diffère peut-être
(`mesures/gpt-oss.md` § 4.3).

### 2.1 E1 : mémoire à loi de puissance (Anderson et Schooler) [mes.]

Score ACT-R B_i(t) = ln Σ_j (t − t_j + 1)^(−d) sur les 32 derniers usages, éviction du plus bas, historique gardé hors du cache.
Seuil déclaré : +0,020 sur le LFU (demi-vie 8) à au moins 3 budgets sur 4, sur les deux modèles. Prédiction écrite : entre 0 et
+2 points, critère manqué.

| 20b, trace poolée | 10 % | 15 % |
|---|---|---|
| LFU (demi-vie 8) | 0,4704 | 0,5924 |
| ACT-R d = 0,2 | 0,4737 (+0,003) | 0,5971 (+0,005) |
| ACT-R d = 0,5 | 0,4671 (−0,003) | 0,5939 (+0,002) |
| ACT-R d = 0,3 / 0,7 / 1,0 (10 % seulement) | 0,4721 / 0,4567 / 0,4229 | n. m. |

**Verdict : tombe.** Arrêtée après deux budgets, le critère (3 sur 4) étant devenu impossible ; les 120b et les budgets 20 et
30 % n'ont pas été lancés (journaux : `e1-20b-arretee.log`, `e1-20b-interrompue.log`).
Témoins : W1 (mon pipeline rend LRU, LFU, Belady du CSV publié à 5·10⁻⁶ près ; cassure par demi-vie 9 : écart 1,7·10⁻³,
tombe) **tient** ; W2 (ACT-R à historique de longueur 1 et temps par accès = LRU) **tient à 0,0**, après qu'un premier essai est
tombé à 8·10⁻⁵ : le départage des égalités par un terme 10⁻¹²·rang était perdu à 4·10⁻¹⁶ dans la virgule flottante, corrigé
par un tri lexicographique exact. **W4 (cassure : ordre des jetons mélangé) tombe, et c'est un fait utile** : l'écart ACT-R moins LFU
devrait passer sous 0,010 ; il vaut +0,001, +0,008, **+0,013**, **+0,024** à 10, 15, 20, 30 % (`e1-20b-melange.json`). L'avantage de
la mémoire longue sur le LFU ne vient donc pas de l'ordre mais d'une meilleure estimation de la popularité : le LFU à demi-vie 8
oublie trop vite. Ce que le balayage post hoc confirme (E1b, non déclaré avant) :

| 20b, LFU selon la demi-vie | 8 | 16 | 32 | 64 |
|---|---|---|---|---|
| poolée, 15 % | 0,5924 | 0,5982 | 0,5979 | 0,5937 |
| poolée, 20 % | 0,6844 | 0,6911 | 0,6912 | 0,6875 |
| dialogue, 20 % | 0,7001 | 0,7094 | 0,7131 | 0,7142 |

| 120b, LFU selon la demi-vie | 8 | 16 | 32 | 64 | 128 |
|---|---|---|---|---|---|
| poolée, 15 % | 0,7241 | 0,7392 | **0,7444** | 0,7420 | 0,7343 |
| poolée, 20 % | 0,7942 | 0,8091 | **0,8151** | 0,8141 | 0,8073 |

Gain de 32 contre 8 genre par genre à 20 % : code +1,2, dialogue +2,9, prose anglaise +2,4, prose française +2,3 points.

**À retenir : le LFU à demi-vie 8 sous-estime les caches de 2 points sur le 120b (+2,0 à 15 %, +2,1 à 20 % avec 32), de 0,6 à 0,7 point sur le 20b.**
Défauts à 20 % sur le 120b : 0,2058 → 0,1849, soit −10 % ; si le disque limite, 1/(1−h) donne +11 % de jetons par seconde [calc.]. Meilleure demi-vie par genre en 120b :
32 (code), 128 (dialogue), 64 (prose anglaise et française) : un réglage en ligne de la demi-vie par genre (le geste de LeCaR ou d'ARC, déjà dans la littérature
des caches) gagnerait encore au plus +0,6 point de plus (dialogue : 0,8418 contre 0,8361), moins ailleurs. Gratuit, mais plafonné par la sélection sur les mêmes traces : à confirmer sur la génération.

### 2.2 E2 : tri par poids de mélange (triage) [mes.]

LFU (demi-vie 8) à 20 %, poids de mélange appariés. Critère déclaré : à masse perdue ≤ 0,03 par (jeton, couche), au moins 25 % des
défauts évités ET poids médian des défauts ≤ 0,8 × celui des succès.

| | 20b | 120b |
|---|---|---|
| poids médian défauts / succès | 0,218 / 0,244 (rapport **0,89**) | 0,222 / 0,241 (**0,92**) |
| part des défauts évités à masse ≤ 0,03 | **11,9 %** (θ = 0,15) | **9,6 %** |
| à θ = 0,2 : défauts évités / masse perdue | 38,6 % / 0,078 | 33,8 % / 0,045 |
| défauts par rang 1, 2, 3, 4 | 23, 28, 33, 42 % | 14, 18, 23, 28 % |

**Verdict : tombe.** Les poids de mélange de gpt-oss sont **plats** (médiane autour de 0,22 à 0,24 pour quatre experts : un
softmax sur quatre logits proches) : aucun expert n'est « peu important » au sens où le triage l'attend, et ce qu'on évite en
écartant les plus petits coûte 0,05 à 0,08 de masse pour un tiers des défauts, au-dessus du seuil. Cela explique pourquoi une idée
qui marche sur Mixtral (deux experts, poids très inégaux : Lu et al., ACL 2024, arXiv 2402.14800 [lu : résumé] ; HOBBIT,
arXiv 2411.01433, v1 2024-11-03 [lu : résumé]) se transfère mal à gpt-oss. Témoins : somme des poids = 1 à 10⁻⁴ ; LFU égal au
dépôt à 0,0 ; cassure (poids mélangés) : rapport des médianes **1,0004**, tombe comme prévu. Limite : la masse n'est pas la KL.

### 2.3 E3 : allocation marginale par couche (METRIC ; partition à utilité) [mes.]

Courbes de défauts par couche en LRU (simulation exacte à chaque capacité), allocation gloutonne par pente de l'enveloppe concave
(plancher 4), apprise sur trois genres, évaluée sur le quatrième. Critère : battre à la fois le LRU par couche à tailles égales et
le LFU global de +0,020. Prédiction écrite : bat le premier, pas le second.

| 20b, moyenne des 4 découpes | allocation | égal | LFU global |
|---|---|---|---|
| 12,5 % (plancher k·L) | 0,5010 | 0,5010 | 0,5358 |
| 15 % | 0,5582 | 0,5453 | 0,5908 |
| 20 % | 0,6498 | 0,6424 | 0,6829 |

**Verdict : tombe** (−0,033 contre le LFU global ; 0 à +1,3 point sur l'égal). Témoin : mon LRU par couche = celui du dépôt
(par construction, il l'appelle). **Cassure : l'allocation apprise sur le genre de test lui-même ne rend que 0,2 à 0,3 point de
plus** (0,5600 contre 0,5582 à 15 %, 0,6526 contre 0,6498 à 20 %), borne haute de ce que l'allocation par couche peut donner :
elle est dans le bruit de ce qu'un bon LFU global donne déjà. Le 120b n'a pas été lancé (critère impossible sur le 20b).

### 2.4 E4 et E4b : le précédent (raisonnement par cas) [mes.]

Pour un jeton de test et une couche d'observation l0 ∈ {3, 8, 14} (20b) ou {4, 12, 22} (120b), on connaît les ensembles d'experts
des couches 0 à l0. On prédit les 4 experts de la couche l0 + d par le vote des 20 jetons antérieurs les plus proches
(recouvrement cumulé des ensembles sur les couches 0 à l0). Deux régimes : « en ligne » (jetons antérieurs du même texte, hors le
précédent, donc causal) et « autre genre » (apprentissage sur trois genres, test sur le quatrième). Bases : b1, les 4 plus
populaires de la couche (calculées sur toute la séquence, donc avantageuses) ; b2, l'ensemble du jeton précédent.
Seuil déclaré : rappel(d = 2) ≥ max(b1, b2) + 0,15 en ligne sur les deux modèles.

Rappel moyen sur genres et l0 (E4) :

| | d | kNN | voisins au hasard | b1 populaires | b2 précédent | marge |
|---|---|---|---|---|---|---|
| 20b en ligne | 1 / 2 / 4 | 0,729 / **0,723** / 0,713 | 0,467 / 0,488 / 0,483 | 0,497 / 0,515 / 0,514 | 0,489 / 0,515 / 0,493 | +0,231 / **+0,208** / +0,199 |
| 120b en ligne | 1 / 2 / 4 | 0,592 / **0,567** / 0,555 | 0,285 / 0,241 / 0,303 | 0,321 / 0,279 / 0,340 | 0,313 / 0,265 / 0,326 | +0,271 / **+0,288** / +0,215 |
| 20b autre genre | 2 | 0,599 | 0,379 | 0,398 | 0,519 | +0,080 |
| 120b autre genre | 2 | 0,398 | 0,133 | 0,154 | 0,267 | +0,131 |

**Verdict : tient, sur les deux modèles** (+0,21 et +0,29 à d = 2 ; la marge ne baisse presque pas de d = 1 à d = 4, de 0,23 à 0,20
et de 0,27 à 0,22). Prédiction écrite fausse sur un point : je prévoyais le critère manqué à d = 4 ; il tient. Hors texte (autre
genre) l'avantage est plus faible mais reste net sur le 120b (+0,13). Témoin : les voisins tirés au hasard retombent vers la
base populaire, **mais 0,035 en dessous** de b1 en moyenne sur le 120b (tolérance déclarée 0,03 : manquée de peu, dite) ; l'écart a
une raison simple : b1 voit le futur de la séquence, les voisins au hasard non. Les bases sont tenues par l'instrument, pas le
kNN : il bat les deux par 0,2.

**E4b (post hoc, dit) : ce que cela donne sur les défauts du LFU à 20 %.** On compare l'ensemble prédit à l'état du cache à la couche
l0 + d : chargements = prédits absents du cache ; utiles = chargements dans les vrais ; défauts = vrais absents. Couverture =
utiles / défauts. Gaspillage = 1 − utiles / chargements. Trafic disque relatif = (défauts non couverts + chargements) / défauts.
Pollution du cache par les chargements : non simulée.

| d = 2, seuil de confiance τ | 0 | 0,5 | 0,6 | 0,7 | 0,9 |
|---|---|---|---|---|---|
| 20b couverture / gaspillage / trafic | 0,51 / 0,42 / 1,37 | 0,41 / 0,29 / 1,17 | **0,34 / 0,22 / 1,09** | 0,28 / 0,15 / 1,05 | 0,15 / 0,05 / 1,01 |
| 120b couverture / gaspillage / trafic | 0,34 / 0,55 / 1,41 | n. r. | **0,15 / 0,24 / 1,05** | 0,11 / 0,17 / 1,02 | n. r. |

Témoin : voisins au hasard (τ = 0) : couverture 0,12, gaspillage 0,83, trafic 1,58 (20b) ; 0,03, 0,95, 1,47 (120b) ; le prédicteur par précédents
fait 4 à 12 fois mieux en couverture. (« n. r. » : non reporté ici ; `e4b-120b.json` a tous les seuils ; le 120b à τ = 0,5 et 0,9 n'est
pas recopié.)

**Lecture honnête.** Sans filtre, le prédicteur gaspille 42 à 55 % de ses chargements ; sur un disque saturé (le disque est
l'étage limitant : 151 ms de disque, 86 ms de PCIe, 10 ms de VRAM par jeton à 20 %, `mesures/gpt-oss.md` § 9), cela coûte 37 à
41 % de trafic de plus. Avec un seuil de confiance de 0,6, le 20b couvre un défaut sur trois pour 9 % de trafic en plus, et le
120b un sur sept pour 5 % de plus : **un préchargement à rapport gain/coût (le calcul coût-bénéfice de l'informed prefetching,
Patterson et al., SOSP 1995 [mém.]) et non un préchargement massif**. Le gain n'est pas des octets, c'est du **recouvrement** : la borne
du recouvrement parfait est t_série / t_recouvert = (151 + 86 + 10) / 151 ≈ 1,64 à 20 % de budget [calc. sur
`mesures/gpt-oss.md` § 9], dont le moteur actuel capture une part que je ne connais pas. Le 120b est moins bon que le 20b parce que
les historiques sont plus courts par rapport au nombre d'experts (128 contre 32, de 2 500 jetons par genre) : sur de longs contextes, le
kNN doit monter. [hyp.]

### 2.5 E5 : classes ABC des experts (analyse ABC des stocks ; MC-MoE) [mes.]

Critère déclaré : les 50 % d'experts les moins utilisés portent ≤ 20 % des accès ET le rang de Spearman de la fréquence entre
genres ≥ 0,7. Prédiction : part de 25 à 35 %, stabilité de 0,3 à 0,6.

| | part des accès des 50 % rares (moyenne ; min–max par couche) | Spearman entre genres | témoin uniforme |
|---|---|---|---|
| 20b | **13,6 %** (3,0–29,0) | **0,47** | part 48,1 %, Spearman −0,30 |
| 120b | **8,8 %** (2,5–20,7) | **0,44** | part 46,2 %, Spearman 0,06 |

**Verdict : tombe** par la stabilité (0,47 et 0,44 sous 0,7). La prédiction sur la part était fausse dans l'autre sens : la moitié
rare est bien plus morte que je ne pensais (9 à 14 % des accès, pas 25 à 35 %). Post hoc, non déclaré : la moitié rare *apprise sur trois
genres* porte **20,5 % (20b) et 22,5 % (120b)** des accès du quatrième genre (jusqu'à 66 à 71 % sur la pire couche d'un genre), au
double de la valeur sur place. Une précision par classe d'usage fixée d'après un corpus ne voyage pas, comme l'épinglage statique
(`mesures/gpt-oss.md` § 9, point 8). MC-MoE (Huang et al., arXiv 2410.06270, ICLR 2025 [lu : résumé]) fait cette allocation de bits
par expert ; ses conditions (calibration sur le corpus d'usage) ne sont pas les nôtres.

### 2.6 E6 : arrêt séquentiel de groupe sur les séries de KL (essais cliniques) [mes.]

Sept séries de différences appariées de KL par fenêtre (10 fenêtres), regards à 4, 6, 8, 10 fenêtres, statistique t, frontière de
forme O'Brien-Fleming c·√(10/k) avec c = 2,840 calibré par Monte-Carlo (200 000 tirages) pour une erreur de 0,05. Témoin : taux de
franchissement sous nulle fraîche **0,0498** (déclaré dans [0,03 ; 0,07]) ; cassure c/2 : **0,315** (> 0,15), tombe.

| série | t aux regards 4, 6, 8, 10 | arrêt | décisive à 10 |
|---|---|---|---|
| neuf, mutation λ=1 moteur contre frontière | −1,94 −2,53 −3,14 −3,44 | 10 | oui |
| neuf, λ=0 contre λ=1 (moteur) | −1,47 −2,09 −2,92 −3,62 | 10 | oui |
| neuf, sub-λ=0 contre frontière | −3,18 −4,08 −4,37 −4,69 | 6 | oui |
| R1, λ=0 contre frontière | −5,77 −7,07 −5,02 −5,64 | 4 | oui |
| R1, λ=1 contre frontière | −5,36 −5,88 −3,11 −3,78 | 4 | oui |
| neuf, moteur contre substituée (égalité) | −0,76 0,72 0,42 0,31 | jamais | non |
| **R1, λ=0 contre λ=1 (la règle B2)** | −5,12 −6,56 −1,50 −2,09 | **4** | **non** |

**Critère déclaré (≤ 7 fenêtres sur 10 en moyenne sur les séries décisives, mêmes signes) : tenu, 6,8.** Ma prédiction (« manqué »)
est fausse. **Mais** : la série R1 λ=0 contre λ=1, celle qui a fondé le choix B2, franchit la frontière à 4 fenêtres (t = −5,1) et
n'est plus décisive à 10 (t = −2,1) ; l'arrêt séquentiel aurait conclu trop tôt sur cette comparaison. Les premières fenêtres de R1
sont très différentes des suivantes (hétérogénéité), ce que la calibration gaussienne ignore. **Verdict : l'économie existe
(environ un tiers des passes de référence sur les séries nettes), la règle telle quelle n'est pas sûre ; il faut un plancher de 6
fenêtres au moins et une calibration par permutation des fenêtres.** Limite dite : l'économie réelle se compte en passes de la
référence f64 (≈ 217 s par fenêtre : 2 168 s pour 10), pas en positions.

### 2.7 E7 : routage conscient du cache, borné par la marge du routeur [mes., post hoc, descriptif]

Mécanisme du monde : substituer à l'expert absent un expert proche déjà présent (Skliar et al., TMLR 2025, arXiv 2412.00099,
v1 2024-11-27, v2 2025-06-24 : défauts de cache réduits de plus de moitié, perplexité +0,1 à 3 % sur de petits MoE [lu : résumé]).
Pour gpt-oss, la substitution qui ne coûte presque rien est celle que le routeur lui-même juge presque indifférente : échanger le
4e expert contre le 5e quand leur marge est sous τ. Borne haute (le 5e est supposé résident) sur le journal de routage du juge
(20b, 5 110 positions, LFU à 20 %, taux de succès 0,670) :

| τ (marge en unité de logit) | part des cellules sous τ | part des défauts évitables au plus |
|---|---|---|
| 0,001 | 0,9 % | **0,3 %** |
| 0,01 (médiane des bascules naturelles : 0,0095) | 8,2 % | **3,1 %** |
| 0,03 | 22,4 % | 8,2 % |
| 0,1 | 56,3 % | 20,0 % |

**Lecture** : dans la zone sûre (τ ≤ 0,01, là où le moteur bascule déjà de lui-même à 4,15 % des cellules), le routage conscient du
cache évite **au plus 3 % des défauts** ; il faut τ = 0,1 (56 % des cellules, loin de toute bascule naturelle) pour en éviter 20 %,
et ces échanges-là sont des changements d'experts, dont la KL n'est pas mesurée (la queue de bascules la domine, 05 § 2.2). Les
rangs 1 à 4 ont 30 812, 35 953, 42 547, 52 792 défauts : le journal range bien les experts par logit décroissant. Fermé dans la zone sûre.

---

## 3. Les candidats, classés

Séparés en **rares** (non vus, ou non vus dans ce rôle) et **déjà vus**. Rang = valeur attendue pour la mission, évidence comprise.

### Rares ou nouvelles pour nos données

**1. Prédiction par précédents + préchargement à seuil de confiance** (E4, E4b). Mesuré. Voir § 2.4.
- *Monde* : raisonnement par cas en droit et en médecine ; filtrage collaboratif du commerce ; informed prefetching (Patterson et
  al. 1995 [mém.]) pour le seuil coût-bénéfice. Voisin MoE : affinité inter-couches (Yao et al., arXiv 2401.08383, 2024-01-16
  [lu : résumé]), préchargeurs de HOBBIT et MoE-SpeQ (arXiv 2511.14102 [lu : résumé via recherche]). Non neuf dans le monde ;
  neuf pour nous, et sans état caché.
- *Problème visé* : préchargement des experts, recouvrement disque / PCIe / calcul.
- *Traduction* : une table des jetons antérieurs du texte courant, indexée par la signature d'experts des couches 0 à l0 (bitmaps de
  32 ou 128 bits par couche), un produit scalaire par jeton et par couche d'observation (quelques milliers de jetons : de l'ordre de la
  microseconde à la milliseconde sur le processeur [hyp.]), un vote sur les 20 plus proches ; chargement de l'ensemble prédit d'une couche
  d'avance si la confiance est ≥ 0,6.
- *Expérience qui la jugerait* : simulateur d'événements discrets alimenté par les traces et par les débits mesurés (disque 2,82 Go/s,
  PCIe 12,2 Go/s, 4,2 ms par expert de 11,8 Mo), avec cache modifié par les chargements (la pollution, non simulée en E4b), contre le
  même simulateur sans préchargement ; puis traces de **génération** (celles de prose-en existent en 120b : `t120b.prose-en.generation.trace`).
- *Données existantes* : traces lecture et génération (`traces-20b/120b`), débits (`fondations/01-machine.md`), journaux de lecture.
  Aucune passe du modèle.
- *Gain attendu* : plafond de recouvrement 1,64 [calc.] à 20 % de budget sur 120b ; la part capturable dépend de la couverture (15 %
  des défauts à +5 % de trafic sur le 120b, 34 % à +9 % sur le 20b, τ = 0,6). Honnêtement : de quelques pourcents à une dizaine de
  pourcents de jetons par seconde, pas un multiple. À confirmer sur de longs contextes où le kNN a plus d'historique.
- *Déjà fermé* : le routeur de la couche suivante sur l'état caché n'est pas mesuré (il demande une passe) ; ce candidat ne le
  remplace pas, il le précède.

**2. Contrôleur de fidélité à tampon, façon BOLA** (non mesuré).
- *Monde* : un lecteur vidéo décide, segment par segment, quel débit demander, en maximisant une utilité sous contrainte de tampon (la
  règle, de mémoire [mém.] : choisir m qui maximise (V·(v_m + γp) − Q) / S_m, v_m = ln(S_m / S_min), Q le tampon) ; garantie : utilité
  moyenne à O(1/V) de l'optimum, sans prévoir la bande passante (Spiteri et al. 2016, ToN 2020 [lu : résumé]). La recherche web du 2026-10-26
  n'a trouvé aucune source reliant le déchargement d'experts MoE à ce cadre.
- *Problème visé* : débit de jetons **stable** quand la lecture du disque a des arrêts (15 à 25 s à 0,2-0,37 Go/s mesurés en 08) ; ordre de lecture
  et fidélité des experts.
- *Traduction* : segment = tronçon d'expert ; échelle = {exact 3,72 bits, rapide λ=0 2,64 bits, retrait} ; S_m = octets ; Q = avance
  de préchargement (nombre de couches) ; décision au moment où un défaut est demandé.
- *Pièges chiffrés* : le rapide du 120b ne tient pas en RAM (≈ 38 Go) ; le servir depuis le disque n'économise que 29 % des octets du défaut,
  pas 100 %. Et E2 dit que les poids sont plats : aucun expert n'est gratuit à dégrader. Le seul levier fort est donc le retrait ou une base
  résidente à ≈ 1 bit (01 § 8.5, passe arrêtée).
- *Expérience* : (1) simulateur sur traces + distribution mesurée des débits disque, deux contrôleurs (tampon contre fixe) : jetons/s p50 et p5.
  (2) La courbe qui manque : KL en fonction de la part f d'experts servis en rapide (f = 0 : 0,0044 ; f = 1 : 0,145 ; le milieu n'existe pas),
  par le moteur sur dix fenêtres, à faire quand le verrou de carte est levé.
- *Données existantes* : traces, KL aux deux bouts, débits. La courbe du milieu est la donnée manquante.
- *Gain attendu* : sur la **régularité** du débit, plus que sur la moyenne ; sur la moyenne, au plus quelques pourcents [hyp.]. Je ne promets rien tant que KL(f) n'est pas mesurée.
- *Déjà fermé* : HOBBIT (précision selon l'importance du jeton) est le voisin ; le contrôleur à tampon avec garantie ne l'est pas.

**3. Arrêt séquentiel de groupe pour les juges de KL** (E6). Mesuré. Voir § 2.6. Rare, et de méthode : il ne touche pas le débit,
il raccourcit les séances de juge (≈ un tiers des passes de référence sur les séries nettes), avec plancher de 6 fenêtres et calibration
par permutation. *Données* : les sept séries commitées. *Gain* : environ 3 fenêtres sur 10 par comparaison décisive. *Fermé* : rien.

### Déjà vus, mesurés ici, à garder comme cartes

**4. Réglage du LFU (demi-vie 32 au lieu de 8)** (E1b). **Le meilleur rapport gain/prix de ce document** : +2,0 à +2,1 points de succès sur le 120b (les quatre genres
d'accord, +0,9 à +3,2), environ −10 % de défauts à 20 %, soit jusqu'à +11 % de jetons par seconde si le disque limite [calc.] ; +0,6 à +0,7 point sur le 20b.
Venu de l'échec de la mémoire à loi de puissance (le témoin W4 a désigné le mauvais réglage). *Données* : traces existantes. *Reste* : le vérifier sur la
génération du 120b et dans le moteur (dont la politique réelle n'est pas un LFU à demi-vie 8 : le gain n'est vrai que contre cette référence). *Fermé* : la loi de
puissance ne fait pas mieux qu'un LFU bien réglé (E1).

**5. Routage conscient du cache borné par la marge** (E7). Au plus 3,1 % des défauts évitables dans la zone sûre. *Fermé*, sauf à accepter des
échanges d'experts au-delà de la marge, dont la KL est à mesurer avec le routage imposé de l'expérience B (R § 2.9).
Mesure qui le jugerait : tracer les logits des 8 premiers experts (le journal n'a que la marge 4e-5e) et imposer le routage à la référence f64.

**6. Tri par poids de mélange** (E2). *Fermé* pour gpt-oss : poids plats. HOBBIT / Lu et al. restent justes pour des modèles à deux experts.

**7. Allocation marginale par couche** (E3, METRIC, Qureshi et Patt MICRO 2006 [lu : résumé]). *Fermé* : −0,033 contre le LFU global, borne haute de l'allocation +0,3 point.

**8. Mémoire à loi de puissance, classes ABC** (E1, E5). *Fermés* : le LFU à demi-vie bien réglée n'est pas battu ; la moitié rare est morte (9 à 14 % des accès) mais
instable d'un genre à l'autre (Spearman 0,44 à 0,47).

---

## 4. Ce qui pourrait être faux

- **Préremplissage, pas génération.** Les traces de lecture sont un texte lu en lot ; les mécanismes de localité peuvent différer en génération
  (`mesures/gpt-oss.md` § 4.3). Les seules traces de génération du dépôt sont 256 jetons par genre en 20b et celles de prose-en en 120b.
- **Traces courtes.** 2 400 à 2 900 jetons par genre pour 128 experts : le kNN du 120b manque d'historique, ses chiffres sont probablement un plancher ; ses
  bases b1 sont calculées sur toute la séquence (avantageuses). Mais aussi : le rappel peut être gonflé par la répétition interne des textes d'essai.
- **Le rappel n'est pas la couverture des défauts**, et la couverture n'est pas la vitesse : la pollution du cache par les chargements et la
  concurrence pour la file du disque ne sont pas simulées (E4b est optimiste sur la couverture, pessimiste sur le coût).
- **Poids de mélange = masse, pas qualité.** E2 ne dit rien de la KL ; la queue de bascules peut défaire ou défaire à l'envers.
- **Un témoin a manqué de peu** (E4, voisins au hasard à 0,035 de b1 pour 0,03 déclaré) ; un autre est tombé pour de bon et s'est avéré informatif (E1 W4).
- **Le LFU « meilleur » est choisi sur les mêmes traces** (E1b est post hoc, non déclaré) : +0,6 point peut être de la sélection ; un test sur la génération du 120b le dirait.
- **E6** : la calibration gaussienne n'est pas sûre ; la série B2 le montre.
- **Sources** : plusieurs sont lues par leur page de résumé, pas par leur texte ; la règle de BOLA et METRIC sont de mémoire.
- J'ai écrit des prédictions avant chaque mesure ; trois sur cinq contenaient une erreur (E4 à d = 4, E5 sur la part, E6), toujours du côté où je sous-estimais
  la structure du routage, pas du côté où je la surestimais.

## 5. Ce qui reste

1. **Simulateur de débit avec préchargement** (candidat 1) sur traces de génération, avec pollution et file disque ; seuil à déclarer : gain de jetons/s ≥ 5 % pour ≤ 5 % de trafic.
2. **Courbe KL(f)** de la part d'experts servis en rapide (candidat 2), séance de carte libre.
3. **Passer la demi-vie du LFU à 32** (ou la régler en ligne par genre) et la vérifier sur la génération du 120b et dans le moteur.
4. **Plancher et calibration par permutation** pour l'arrêt séquentiel du juge, sur les futures séries.
5. Tracer les logits des 8 premiers experts (CPU, 20b, ≈ 4 minutes) pour juger le routage conscient du cache au-delà de la marge.

## 6. Recettes (techniques essayées)

- **Importer les instruments du dépôt par `importlib` plutôt que les recopier** : LRU, LFU et Belady du dépôt servent d'instrument et de témoin (écart ≤ 5·10⁻⁶ au CSV publié).
- **Départage des égalités par un terme additif ε·rang : échoue** (perdu en virgule flottante à 4·10⁻¹⁶) ; **réussit** : tri lexicographique (score, rang).
- **Le témoin « ordre mélangé » (W4)** distingue l'effet d'ordre de l'effet de mémoire longue ; il a révélé le mauvais réglage du LFU.
- **Une série d'ACT-R à 5 valeurs de d sur 4 budgets** coûte plus d'une heure en un fil (≈ 10 min par budget) ; l'arrêt dès que le critère devient impossible est correct et dit.
- **Rejouer sur des CSV existants** (E6) donne une mesure sans relancer un modèle.

## 7. Sources (consultées les 2026-10-26 et 27)

Lues par leur page ou leur résumé ; l'adresse est celle de la page lue.
- J. R. Anderson et L. J. Schooler, « Reflections of the Environment in Memory », *Psychological Science* 2, 396-408, 1991. https://www.psychologicalscience.org/journals/psychological-science/j.1467-9280.1991.tb00174.x/ [lu : résumé via recherche]
- B. Settles et B. Meeder, « A Trainable Spaced Repetition Model for Language Learning », ACL 2016, p. 1848-1858. https://aclanthology.org/P16-1174/ [lu : référence ; résumé non extrait]
- K. Spiteri, R. Urgaonkar, R. K. Sitaraman, « BOLA: Near-Optimal Bitrate Adaptation for Online Videos », INFOCOM 2016 ; IEEE/ACM ToN 2020. https://arxiv.org/abs/1601.06748 (v1 2016-01-25, v3 2020-06-18) [lu : résumé]
- P. Tang et al., « HOBBIT: A Mixed Precision Expert Offloading System for Fast MoE Inference », arXiv 2411.01433, v1 2024-11-03. https://arxiv.org/abs/2411.01433 [lu : résumé]
- A. Skliar et al., « Mixture of Cache-Conditional Experts for Efficient Mobile Device Inference », TMLR 2025, arXiv 2412.00099. https://arxiv.org/abs/2412.00099 [lu : résumé via recherche]
- J. Yao et al., « Exploiting Inter-Layer Expert Affinity for Accelerating Mixture-of-Experts Model Inference », arXiv 2401.08383, 2024-01-16. https://arxiv.org/abs/2401.08383 [lu : résumé]
- W. Huang et al., « Mixture Compressor for Mixture-of-Experts LLMs Gains More », arXiv 2410.06270, ICLR 2025. https://arxiv.org/abs/2410.06270 [lu : résumé]
- X. Lu et al., « Not All Experts are Equal: Efficient Expert Pruning and Skipping for Mixture-of-Experts LLMs », ACL 2024, arXiv 2402.14800. https://aclanthology.org/2024.acl-long.334 [lu : résumé via recherche]
- « MoE-SpeQ: Speculative Quantized Decoding with Proactive Expert Prefetching and Offloading for Mixture-of-Experts », arXiv 2511.14102, 2025-11. https://arxiv.org/abs/2511.14102 [lu : résumé via recherche]
- P. C. O'Brien et T. R. Fleming, « A Multiple Testing Procedure for Clinical Trials », *Biometrics* 35, 549-556, 1979. https://doi.org/10.2307/2530245 [lu : résumé via recherche ; constante de la frontière recalibrée ici, non reprise]
- M. Mitzenmacher, « The Power of Two Choices in Randomized Load Balancing », IEEE TPDS 2001. https://www.eecs.harvard.edu/~michaelm/postscripts/tpds2001.pdf [lu : résumé]
- M. K. Qureshi et Y. N. Patt, « Utility-Based Cache Partitioning », MICRO 2006, p. 423-432. https://utw10235.utweb.utexas.edu/pub/TR-HPS-2006-009.pdf [lu : résumé via recherche]
- D. Lee et al., « LRFU: A Spectrum of Policies that Subsumes the Least Recently Used and Least Frequently Used Policies », IEEE Trans. Computers 50(12), 1352-1361, 2001. https://doi.org/10.1109/TC.2001.970573 [lu : résumé via recherche]
- G. Einziger, R. Friedman, B. Manes, « TinyLFU: A Highly Efficient Cache Admission Policy », arXiv 1512.00727. https://arxiv.org/abs/1512.00727 [lu : résumé via recherche]
- Islam et Uddin, « Correlated storage assignment approach in warehouses: A systematic literature review », J. Industrial Engineering and Management, 2023. https://jiem.org/index.php/jiem/article/view/4850 [lu : résumé via recherche]
- Sherbrooke (METRIC, *Operations Research* 16, 1968), Patterson et al. (SOSP 1995), Eppen (1979) : [mém.], non relus.
