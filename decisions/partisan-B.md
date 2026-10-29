# Partisan de B : la contribution d'abord

Plaidoyer pour l'arbitre de troncons, rédigé le 2026-10-15 par le partisan de « la contribution
d'abord ». Mon rôle est de faire de **B** (la précision selon l'étage : une base et un complément
tirés du code MXFP4 natif, la base seule servie aux défauts de cache, le complément pour rendre
exact) le cœur du premier livrable. Je le plaide au mieux, mais je chiffre ce que mon camp
sacrifie, et j'ai corrigé un chiffre de B qui l'avantageait à tort (§ 2).

Lu en entier avant d'écrire : `SOCLE.md` et `fondations/07-ce-qui-manque.md`. Lu là où mon argument
en dépend : 02 (§ 0, § 5, D7, trou 7), 03 (§ 1.6, § 3), 04 (§ 3.4, trou 5), 06 (§ 7), l'outil
`raffinement_mxfp4.py` et `plafonds.py` de l'étude 07, et le balayage du disque de 01. Lus en entier
à la source, ce jour, parce que la nouveauté de B en dépend : le corps de SliceMoE et celui de HOBBIT
(07 n'en avait lu que les résumés).

Étiquettes du projet : **[mes.]** mesuré ici ; **[calc.]** calculé par un outil commité ;
**[litt.]** littérature (éditeur, non reproduit) ; **[hyp.]** hypothèse dite ; **[est.]** estimation
d'ingénierie, non mesurée.

Outil de ce plaidoyer : `outils/decisions/partisan_b.py`. Il ne lit ni le disque ni la carte (un autre
agent mesure sur les deux) : il calcule depuis deux journaux commités de 07 et réutilise les fonctions
de `plafonds.py`. Journaux : `decisions/journaux/partisan-b.json`, `partisan-b-casse.json`, et
`decisions/journaux/csv/` pour les figures. Témoins : trois, seuils déclarés dans l'outil avant le
lancement, tous tiennent ; la cassure fait tomber les deux qui doivent tomber (§ 6.6).

**Mesures en cours chez un autre agent** (`mesures/gpt-oss.md`, pas encore commitée à l'heure où
j'écris ; seul son outillage l'est, commit `fce4519`) : la courbe de succès `h(c)`, la réutilisation ρ
et la base llama.cpp sur gpt-oss-120b. Tout ce qui suit et qui dépend d'elles est marqué, et le § 7
dresse la liste.

---

## 0. En bref

1. **B est le seul des trois mécanismes qui n'existe pas encore, et c'est ce que Stone demande** :
   « je ne veux pas que des recherches déja existante […] si ce qu'on cherche n,existe pas alors
   tant mieux creer le ». A est un assemblage (Linux en a déjà trois, § 5) ; C est un arbre de
   SpecExec rendu portable. B a désormais deux voisins lus en entier : SliceMoE (tranches de bits par
   troncature d'un INT, choix selon le score du routeur, simulateur d'accélérateur) et HOBBIT (deux
   copies séparées, FP16 et Int4, choix selon le poids du routeur). **Ce qui reste neuf** : une base
   qui est une *fonction* du code natif FP4 (aucune copie, aucun octet stocké en plus), choisie par
   sa distorsion et non par troncature (0,27 bit de moins à erreur égale [mes. 07]), codée par
   entropie avec son complément pour un total égal au sans-perte, rendue exacte par lecture du seul
   complément, sur une vraie machine grand public (NVMe chiffré, PCIe, Vulkan, Windows), jugée sur un
   modèle *entraîné* en 4 bits, où la couche exacte est l'original lui-même.
2. **J'ai corrigé un chiffre de 07 qui gonflait B.** `plafonds.py` calcule B1 sans compter les octets
   des compléments qu'il faut lire pour qu'un expert entre exact au cache. Comptés, **le plafond de B1
   retombe à celui de A** (6,16 contre 6,24 jetons/s, scénario LRU calé) au lieu de 8,88 ; son gain ne
   vit plus que dans le **plancher en série** : 3,93 → **4,83** jetons/s (+23 %), parce que le
   complément quitte le chemin critique [calc.]. ~~×1,42 sur le plafond (B1 : 8,88 contre 6,24
   jetons/s, LRU calé)~~ (07 § 3.2 R1 et § 0 point 3, à barrer par l'arbitre dans le fichier de 07).
3. **Le gain de débit de B existe, mais il a un prix en qualité qu'on peut régler** : si la RAM garde
   des bases (1,44 fois plus d'experts tièdes) et la VRAM un ensemble chaud exact (variante B3), le
   plafond vaut **10,9 jetons/s (×1,74 sur A)** quand tout usage hors VRAM est servi par la base
   (48 % des usages d'experts), **8,5** quand un quart de ces usages exige l'exact, **7,0** à la
   moitié, et rejoint A vers λ ≈ 0,67 [calc., LRU calé]. Le bouton λ est la politique de défaut
   selon le poids du routeur : le mécanisme de B, c'est aussi ce bouton.
4. **La qualité est l'inconnue qui décide de B, et elle se mesure en quelques jours, sans moteur.**
   La base peut être « aimantée » sur des valeurs E2M1 existantes (0 ; 1,5 ; 3 ; 6) : le fichier reste
   un MXFP4 valide que llama.cpp lit tel quel, à **5,91 %** d'erreur relative au lieu de 4,29 % au
   centre de gravité [calc. exact sur les énergies mesurées]. Et la variante B3 la plus perdante
   (ensemble chaud exact, tout le reste en base) est un *fichier statique* : sa qualité se juge avec
   le juge de l'étude 06, avant d'écrire une ligne de moteur.
5. **Ordre de grandeur honnête de la qualité** (linéarité de HIGGS, hypothèse) : B1 sans politique de
   routage, KL ≈ 0,023 à 0,058 ; avec une politique qui ne sert la base qu'aux experts portant un
   dixième de l'énergie de routage, 0,002 à 0,006 ; B3 sans politique, 0,05 à 0,12 [hyp.]. **Le seuil
   de 07 (KL ≤ 0,0055) est donc probablement manqué par B3 tel quel**, et atteignable par B1 avec une
   politique de routage stricte. Je ne bouge pas ce seuil ; j'en ajoute un second, celui de la
   frontière de l'étude 06 (§ 6.4).
6. **Ce que mon camp sacrifie** (§ 4) : l'exactitude d'une part réglable des usages (0 à 48 %) ; un
   risque qualité réel ; +1,33 % d'octets en mode exact tant que la découpe n'est pas conditionnée
   par la classe d'échelle (A lu dans le fichier de B : 6,12 au lieu de 6,24) ; trois noyaux et un
   automate de cache à cinq états de plus (≈ +20 % de noyaux, +25 à 35 % de travail jusqu'au premier
   mode B [est.]) ; une session et quelques heures de carte avant le moteur.
7. **Ce que coûte A d'abord** (§ 5) : un premier livrable qui est un assemblage déjà publié sous Linux ;
   un cache et un ordonnanceur pensés pour l'exact, à reprendre pour cinq états ; et surtout la
   mesure qui décide de B repoussée après un moteur complet, alors qu'elle ne demande qu'un fichier.
8. **Ma proposition** (réponse par délégation du 2026-10-15, réversible) : le premier livrable est
   **le mécanisme B mesuré**, dans cet ordre : (Q0) qualité de B sur llama.cpp par fichiers statiques,
   et frontière des requantifications uniformes ; (F) le format à deux flux, seul format du projet ;
   (M) le moteur, construit d'abord en mode exact (ε = 0, qui *est* A) ; (B) le mode B et sa
   politique. A n'est pas sacrifié : c'est B avec un budget de perte nul. Si Q0 tue B, on le sait en
   quelques jours et le moteur continue en A sans rien avoir perdu d'autre que la découpe (réversible,
   le codeur est à nous).

---

## D'où on part, où on va

**Au départ** : la synthèse 07 recommande « A d'abord, dans le format qui prépare B ; B dès que A tourne
et que la trace donne `h` » ; elle chiffre B1 à ×1,42 sur A et pose un seuil de qualité (KL ≤ 0,0055).

**Ce que ce plaidoyer établit** : le ×1,42 ne tient pas quand on compte les compléments ; le vrai gain
de B est soit en latence (B1), soit en débit au prix d'une part réglable d'usages servis par la base
(B3) ; la qualité de B, seule inconnue qui le décide, se mesure sans moteur ; la nouveauté restante de
B, après lecture des corps de SliceMoE et HOBBIT, est plus étroite et plus précise que ne le disait 07.

**Ce qui reste** : les mesures Q0 (carte libre nécessaire), la trace de routage avec les poids de
mélange (en cours, autre agent), et l'arbitrage.

---

## 1. Pourquoi B est le cœur

### 1.1 Ce que Stone demande

Ses mots, tels quels : « je ne veux pas que des recherches déja existante je veux que tu fasse une vrai
recherche de spécialiste puis tu implémente la solution fonctionnelle […] si ce qu'on cherche n,existe
pas alors tant mieux creer le ». Et, à l'origine (relais, 2026-10-02) : « une nouvelle facon de
compreser les données et en sommes elles apparaisse directement lorsqu'on a en besoin et disparaisse
apr;es ».

Le SOCLE lit : « l'état de l'art se lit à fond, mais le livrable est une contribution : un assemblage
ou un mécanisme qui n'existe pas encore, prouvé par la mesure, et un programme qui marche ». A remplit
la première moitié (« un assemblage ») ; B est la seconde (« un mécanisme »), et c'est la seule qui
réponde mot pour mot à « une nouvelle façon de compresser » : une même donnée, deux précisions, l'une
servie à l'instant du défaut, l'autre qui la rend exacte quand l'expert reste.

### 1.2 Ce que les voisins font vraiment (corps lus ce jour)

**SliceMoE** (arXiv 2512.12990, v5 du 2026-09-08, HTML lu) [litt.] :
- poids d'experts en INT asymétrique par groupes de 32 ; la tranche haute s'obtient par décalage à
  droite du code et du point zéro (« AMAT »), la tranche basse est le reste : **une troncature** ;
- experts « critiques » ou non selon la netteté des scores du routeur ; les non critiques ne demandent
  que la tranche haute ; « MSB-only computation is used otherwise » ;
- les tranches basses ont la priorité la plus faible et sont évincées vite ; rien n'est dit d'un
  raffinement ultérieur ; **aucun codage entropique** ;
- modèle entier en flash UFS 3.1, cache en LPDDR4, accélérateur **simulé** ; DeepSeek-V2-Lite et
  Qwen1.5-MoE ; à 2 bits, la tranche tronquée fait 10,18 de perplexité contre 9,46 pour un 2 bits
  dédié sur DeepSeek-V2-Lite (et mieux que lui sur Qwen1.5-MoE).

**HOBBIT** (arXiv 2411.01433, v2, HTML lu) [litt.] :
- deux **copies séparées** de chaque expert (FP16 et Int4 sur RTX 4090 ; Int8 et Int2 sur Orin),
  toutes en mémoire du processeur ;
- règle de choix : les k experts choisis sont triés par poids ; « l'inimportance » d'un expert est la
  somme des poids de ceux qui le précèdent ; ≤ 0,6 → haute précision, ≤ 0,9 → basse, au-delà sauté
  (Mixtral : 67 / 30 / 3 %) ; le premier expert est toujours en haute précision ;
- Mixtral-8x7B et Phi-MoE ; perte ≤ 1 point (GSM8K 0,52 → 0,51 sur Mixtral) ; bâti sur llama.cpp.

**Ce que cela retire de la nouveauté de B** : le choix de la précision selon le poids du routeur
(HOBBIT, SliceMoE) et la lecture partielle par tranches (SliceMoE) existent. Je ne les revendique pas.

**Ce qui reste, et que personne ne fait** (le terme qui leur manque) :

| | HOBBIT | SliceMoE | TRACE (résumé) | **B** |
|---|---|---|---|---|
| Base | copie Int4 séparée | tranche haute d'un INT (troncature) | plans de bits | **fonction du code FP4 natif, partition optimale** |
| Octets stockés en plus | +25 % (FP16 + Int4) | 0 | 0 | **0** |
| Codage entropique | non | non | oui (matériel) | **oui, base et complément** |
| Raffinement exact | non (recharge la copie FP16) | non décrit | — | **lecture du seul complément (1,22 bit)** |
| Format natif 4 bits | non | non | BF16 | **MXFP4 (gpt-oss)** |
| Machine | 4090, Orin, Linux | simulateur | contrôleur CXL | **portable Windows, Vulkan, NVMe chiffré** |

La troncature est mesurablement mauvaise sur E2M1 : à 4 classes, elle coûte 2,907 bits de base pour
4,47 % d'erreur, la partition optimale 2,642 bits pour 4,29 % [mes. 07] : **0,27 bit par poids de
moins à erreur un peu meilleure**, parce que les niveaux E2M1 ne sont pas uniformes. SliceMoE n'y
échappe pas : son propre tableau montre la tranche tronquée sous un 2 bits dédié sur un des deux
modèles.

### 1.3 La proposition qui porte B

Si `B = f(X)`, alors `H(X) = H(B) + H(X | B)` (07 § 4.2, démontrée). La base et le complément ne
coûtent ensemble, en entropie, que le sans-perte d'un seul tenant. Ce que j'ajoute : **en pratique la
découpe coûte +1,33 %** tant que les deux flux ne sont pas conditionnés par la classe d'échelle comme
l'est le flux unique de A (3,906 bits contre 3,8545 [calc.]). L'écart vient de là : H(base) a été
mesurée à l'ordre 0 (2,642), alors que le flux unique de A encaisse 0,053 bit d'information
code-échelle par ses trois classes [mes. 03]. Comme la classe d'échelle dit surtout la *magnitude* des
autres codes du bloc, l'essentiel de ce gain doit passer dans la base. C'est à mesurer (étape F1), avec
un seuil déclaré au § 6.4.

---

## 2. Ce que B gagne vraiment : les compléments comptés

### 2.1 L'erreur du calcul de 07

`plafonds.py` (07) calcule B1 avec `r_defaut = 4,25 / 2,684` et un cache RAM exact, et B2 avec une RAM
de bases et une VRAM exacte admise en LRU, **sans aucun octet de complément**. Or :
- en B1, un expert servi par sa base puis admis au cache tiède *exact* doit lire son complément ;
- en B2, chaque admission en VRAM d'un expert exact doit lire son complément depuis le disque (la RAM
  ne garde que la base).

Le disque étant l'étage limitant et occupé en permanence (07 § 4.1, chronogramme), le complément ne
trouve pas de « temps libre » au plafond. Le témoin T2 montre que mon outil redonne exactement le
8,88 de 07 quand on retire le terme des compléments : la seule différence est ce terme.

### 2.2 Les trois familles, chiffrées (`partisan-b.json`, gpt-oss-120b, disque 2,58 Go/s) [calc.]

Notations : `b_A = 3,8545` bits par poids lus (A, trois classes) ; `b_base = 2,684` ; `b_compl =
1,222` ; λ = part des usages concernés qui exige l'exact (la politique de routage).

- **B1 complété(λ)** : RAM exacte (codée), VRAM exacte en LRU, chaque défaut lit la base puis le
  complément ; une part λ des défauts (les plus forts poids de routage) attend le complément avant de
  calculer, le reste est servi par la base.
- **B3(λ)** : RAM de bases (11 Go en contiennent 1,44 fois plus), VRAM = ensemble chaud **statique**
  exact (aucune admission, donc aucun complément pour elle) ; une part λ des usages hors VRAM exige
  l'exact et lit son complément.

| Scénario LRU calé | Plafond (j/s) | Plancher en série | Go lus du disque / jeton | Part des usages servis par la base |
|---|---|---|---|---|
| A (07) | 6,24 | 3,93 | 0,404 | 0 |
| A lu dans le fichier de B (découpe non conditionnée) | 6,12 | 3,87 | 0,412 | 0 |
| ~~B1 de 07, sans compléments~~ | ~~8,88~~ | ~~5,09~~ | ~~0,282~~ | ~~23 %~~ |
| **B1 complété, λ = 0** | 6,16 | **4,83** | 0,410 | 23,4 % |
| B1 complété, λ = 0,5 | 6,16 | 4,31 | 0,410 | 11,7 % |
| B1 complété, λ = 1 (exact) | 6,16 | 3,89 | 0,410 | 0 |
| **B3, λ = 0** | **10,89** | 5,58 | 0,228 | 48,5 % |
| B3, λ = 0,25 | 8,50 | 4,75 | 0,294 | 36,3 % |
| B3, λ = 0,5 | 6,97 | 4,14 | 0,361 | 24,2 % |
| B3, λ = 0,75 | 5,91 | 3,67 | 0,427 | 12,1 % |
| B3, λ = 1 (exact) | 5,13 | 3,29 | 0,494 | 0 |

Les deux autres scénarios (même fichier, `b-complements-gptoss120b.csv`, `b3-lambda-gptoss120b.csv`) :

| | uniforme : plafond / série / part base | Belady calé : plafond / série / part base |
|---|---|---|
| A | 2,05 / 1,47 / 0 | 10,34 / 6,17 / 0 |
| B1 complété, λ = 0 | 2,02 / **1,88** / 72 % | 10,21 / **7,46** / 14 % |
| B3, λ = 0 | **3,33** / 2,22 / 92 % | **18,04** / 9,11 / 26 % |
| B3, λ = 0,5 | 2,51 / 1,76 / 46 % | 12,09 / 7,01 / 13 % |
| λ où B3 rejoint A | ≈ 0,95 | ≈ 0,75 |

### 2.3 Ce que ce tableau dit

1. **B1 est un mécanisme de latence, pas de débit.** Au plafond il ne gagne rien (−1,3 %, la
   découpe). En série, il gagne +23 % (LRU) à +28 % (uniforme), parce que la base, 69 % des octets
   d'un expert, est seule sur le chemin critique. Les moteurs publiés tournent à 18-45 % de leur borne
   [litt. 04] : c'est-à-dire près du plancher, là où B1 paie. Sa perte de qualité est la plus douce
   qui soit : un expert n'est approché que pour **un seul usage**, celui du défaut, puis il est exact.
2. **B3 est le mécanisme de débit.** ×1,74 sur A au plafond (LRU), ×1,62 (uniforme), ×1,74 (Belady),
   en servant par la base tout ce que la VRAM ne tient pas. La politique de routage (λ) rend une part
   de cette perte, au prix du gain : la moitié des usages hors VRAM rendue exacte ne laisse que ×1,12.
3. **Le coût caché de B3 est sa VRAM statique** : `h_v` tombe de 0,590 à 0,515 (j'ai calé un cache
   statique sur le seul point publié, LFU/statique 59,2 % au même budget [litt. 04]) [hyp.]. Une
   admission en VRAM qui lirait le complément seulement pour les experts devenus fréquents (filtre
   d'admission) récupérerait une partie de cet écart ; c'est un réglage à mesurer, pas à supposer.
4. **Le terme qui décide est `s`**, la part de l'énergie de routage (Σ g²) que portent les usages
   servis par la base. Elle se lit dans la trace de routage en cours (le traceur écrit les poids de
   mélange, `outils/gptoss-routage/traceur.cpp`, ligne 38 de son en-tête) ; elle ne se suppose pas.

---

## 3. La qualité : ce qu'on sait, ce qu'on ne sait pas, et comment le savoir vite

### 3.1 L'erreur de la base, exacte

L'outil retrouve les énergies par magnitude `W_m` (la somme des carrés des poids réels de chaque
magnitude E2M1, pondérée par l'échelle) à partir des 42 partitions publiées par 07 : rapports voisins
lus dans les centres, puis affinage par Gauss-Newton sur les 42 erreurs publiées en pleine précision
(7 inconnues, 42 équations). Témoin T3 : les 42 erreurs reproduites à 3,9·10⁻¹⁶ près [calc.].

| magnitude E2M1 | 0 | 0,5 | 1 | 1,5 | 2 | 3 | 4 | 6 |
|---|---|---|---|---|---|---|---|---|
| part de l'énergie de comptage `W_m` | 0,230 | 0,207 | 0,184 | 0,106 | 0,122 | 0,079 | 0,057 | 0,015 |

(`W_m` est la masse de comptage pondérée par le carré de l'échelle du bloc ; la part de l'énergie des
poids est `W_m · m²`.)

| Base (signe + 2 bits) | Valeurs de reconstruction | H(base) | Erreur relative |
|---|---|---|---|
| centre de gravité, meilleure partition {0 ; 0,5} {1 ; 1,5 ; 2} {3 ; 4} {6} | 0,237 ; 1,424 ; 3,419 ; 6 | 2,642 | **4,29 %** [mes. 07] |
| **la même partition aimantée sur E2M1** | **0 ; 1,5 ; 3 ; 6** | 2,642 | **5,91 %** [calc.] |
| autre partition aimantée {0 ; 0,5 ; 1} {1,5 ; 2} {3 ; 4} {6} | 0,5 ; 2 ; 3 ; 6 | 2,609 | 5,97 % [calc.] |
| *référence : MXFP4 sur une gaussienne* | | | *1,33 %* [mes. 07] |

L'aimantation coûte 1,62 point d'erreur (×1,38 en erreur quadratique), mais elle donne **un fichier
MXFP4 valide** : llama.cpp le lit avec ses propres noyaux. C'est un mandataire *pessimiste* de B, qui
permet de juger B tout de suite.

### 3.2 L'ordre de grandeur, et pourquoi le seuil de 07 sera dur

Une sortie de MoE vaut `y = Σ g_i E_i(x)` ; une erreur `δ_i` sur la sortie d'un expert y entre comme
`g_i δ_i`. Avec des erreurs indépendantes et la linéarité de HIGGS (perte ≈ somme pondérée des MSE
relatives [litt. 02]), l'excès de KL de B vaut `KL_B ≈ K_tout · W`, où `K_tout` est la KL du modèle
dont *tous* les experts sont servis par la base, et `W = (part des usages servis par la base) × s`
[calc. sous hypothèses].

`K_tout` n'est pas mesuré. Analogue le plus proche sur la machine : une requantification de Qwen3.5
vers ≈ 3,5 bits (IQ3_XXS depuis Q4_K_M) donne une KL de 0,113 (9B) à 0,148 (4B) [mes. 02] ; la base de
B ajoute 4,3 % d'erreur relative sur les seuls experts (l'attention reste exacte en Q8_0). Je pose
`K_tout ∈ [0,10 ; 0,25]` [hyp.] : la mesure Q0.b le remplacera.

| Cas (LRU calé) | Part servie par la base | s = 1 | s = 0,5 | s = 0,25 | s = 0,1 |
|---|---|---|---|---|---|
| B1 complété, λ = 0 | 23,4 % | 0,023 – 0,058 | 0,012 – 0,029 | **0,006 – 0,015** | **0,002 – 0,006** |
| B3, λ = 0 | 48,5 % | 0,048 – 0,121 | 0,024 – 0,061 | 0,012 – 0,030 | 0,005 – 0,012 |

Lecture honnête : contre le seuil de 07 (0,0055, l'écart entre deux moteurs justes), **B3 sans
politique est 9 à 22 fois trop haut ; B1 n'y entre qu'avec une politique qui laisse à la base
au plus un dixième de l'énergie de routage**. Chez HOBBIT, la règle 0,6 / 0,9 sur Mixtral (top-2)
laisse 30 % des experts en basse précision ; gpt-oss a 4 experts actifs, dont les deux derniers
portent, si le routage est net, une petite part de Σ g². C'est mesurable dans la trace en cours.

### 3.3 Le banc Q0 : la qualité de B sans moteur

Le point qui fait basculer mon plaidoyer : **la variante la plus perdante de B, B3 à λ = 0, est un
fichier statique** (un ensemble chaud par couche, exact ; tous les autres experts en base). Elle se
juge avec llama.cpp b11515 et le juge de l'étude 06 (`outils/modeles-juge.sh`), sans moteur :

- **Q0.a — tout en base aimantée** (gpt-oss-20b, MXFP4, même taille que l'original) : borne pessimiste
  de `K_tout`.
- **Q0.b — tout en base au centre** : experts réécrits en Q8_0 (blocs de 32, échelle F16, choisie
  bloc par bloc). Un bloc exact `2^e · {0 ; 0,5 ; … ; 6}` s'y écrit exactement avec `d = 2^(e−1)` et
  des entiers ≤ 12 ; un bloc de base, avec `d = 6 · 2^e / 127`, à au plus `d / 2`, soit 0,39 % du
  maximum du bloc, de ses centres [calc.]. Condition à vérifier par l'outil d'écriture : que chaque
  `d` tienne dans un F16 (exposants E8M0 du fichier entre 2⁻²⁴ et 2¹⁵). Donne `K_tout` pour le noyau
  de B (table de 4 centres).
- **Q0.c — B3, λ = 0, statique** : l'ensemble chaud de chaque couche (les experts les plus fréquents
  d'une trace faite sur un corpus *distinct* du texte de jugement, à la taille de la VRAM : 362
  experts pour le 120b [07]) exact, le reste au centre (Q8_0).
- **Q0.d — la frontière** : les experts requantifiés uniformément par `llama-quantize
  --allow-requantize` (IQ4_XS, Q3_K, IQ3_XXS, Q2_K, à vérifier que l'outil accepte une source MXFP4),
  pour tracer la frontière KL contre octets lus par jeton que demande l'étude 06 (§ 7.5).
- **Témoin du banc** : les experts exacts réécrits en Q8_0 (même chemin d'écriture, aucune base)
  doivent retomber dans le plancher de l'instrument (KL ≤ 7·10⁻⁵, premier choix 100 % [mes. 06]) ;
  forcé à faux (une base glissée dans un seul expert d'une seule couche), il doit en sortir.

Sur gpt-oss-20b d'abord (12,1 Go ; en Q8_0 ≈ 20 Go, place libre suffisante) ; le 120b ensuite, en
Q0.a seulement (même taille que l'original). Il faut la carte libre quelques heures, et le disque au
calme pour écrire les fichiers : c'est à l'orchestrateur de placer ces fenêtres, pas à moi (un autre
agent mesure aujourd'hui).

B1 et B3 à λ > 0 dépendent de l'état du cache à chaque usage : ils demandent le moteur (étape B2 du
§ 6.3), ou un rejeu de la trace dans un banc dédié.

---

## 4. Ce que mon camp sacrifie, chiffré

| Sacrifice | Chiffre | Source | Rattrapable ? |
|---|---|---|---|
| Exactitude d'une part des usages | 0 à 48,5 % des usages d'experts selon λ (LRU) ; 0 en mode ε = 0 | [calc.] | oui : ε = 0 est A |
| Risque qualité | KL estimée 0,002 à 0,12 selon la variante ; seuil de 07 probablement manqué par B3 | [hyp.] § 3.2 | se mesure en Q0, en jours |
| Octets en mode exact | +1,33 % (3,906 contre 3,8545 bits) ; A lu dans le fichier de B : 6,12 au lieu de 6,24 j/s (−1,9 %) | [calc.] | probablement, par le conditionnement de classe (F1) |
| Débit de B1 au plafond | aucun gain (6,16 contre 6,24) | [calc.] | non : B1 est un gain de latence |
| VRAM statique de B3 | `h_v` 0,590 → 0,515 | [hyp.] | partiellement, par un filtre d'admission |
| Lectures plus petites | complément d'une matrice : 1,27 Mo, où le disque donne 2,2 Go/s (1 Mio, QD 2-4) au lieu de 2,6-2,9 (4 Mio) | [mes. 01] | oui : grouper les flux par expert (base 8,3 Mo, complément 3,8 Mo, § 6.2) |
| Complexité | +3 noyaux sur ≈ 15 (réassemblage de la base, raffinement, contrôle d'intégrité) ; automate de cache à 5 états au lieu de 3 ; un module de politique | [est.] | — |
| Délai avant un premier programme exact | +5 à 10 % (découpe et table de reconstruction par expert seulement sur le chemin critique) | [est.] | — |
| Délai avant un premier mode B | +25 à 35 % sur le travail de A seul | [est.] | — |
| Temps de carte avant le moteur | une session d'agent et 2 à 4 h de carte pour Q0 (8 à 10 passes du juge sur le 20b) | [est.] | — |
| Disque | 20 à 40 Go de fichiers de banc ; 63 Go réécrits pour le 120b au format F | [calc.] | supprimables |

**Ce que je ne sacrifie pas** : la possibilité d'un programme exact. Le mode ε = 0 lit base et
complément avant tout calcul ; ses logits doivent être identiques au bit à ceux d'un flux unique
(témoin du § 6.6). Si Q0 tue B, le moteur continue en A.

---

## 5. Ce que coûte de faire A d'abord

1. **Le premier livrable serait un assemblage déjà publié ailleurs.** SSD-LLaMA (disque → RAM → VRAM
   avec compression des experts, RTX 5090), la PR llama.cpp #25294 (experts lus sur le disque, cache)
   et Edge0 existent [litt. 04]. A les dépasse sur un terrain précis (Windows, Vulkan, disque chiffré,
   octets codés de bout en bout), ce qui est une vraie valeur d'ingénierie, mais ce n'est pas ce que
   Stone a dit vouloir en premier.
2. **La mesure qui décide de B serait repoussée derrière un moteur complet** (07 § 4.1, étapes 3 à 7 :
   format, lecteur IOCP, passage avant Vulkan de gpt-oss, cache, 120b), alors qu'elle ne demande que
   des fichiers statiques et le juge existant. Le risque concret : la session se termine sur A, et B,
   la seule contribution de recherche, n'a jamais été mesuré.
3. **Le moteur serait pensé pour l'exact.** Un cache à trois états (absent, en vol, présent) et une
   GEMV à table fixe ; B demande cinq états (absent, base en vol, base, complément en vol, exact), une
   table de reconstruction par expert, et une politique par défaut au moment où le routeur parle. Les
   ajouter après coup reprend le cache et l'ordonnanceur [est. : 30 à 50 % de ces deux modules].
4. **Le format de 07 « qui prépare B » coûte déjà la découpe** (+1,33 %) à A : si A adopte deux flux,
   il paie le prix de B sans en avoir le bénéfice ; s'il n'en adopte qu'un, B demandera une réécriture
   (63 Go pour le 120b, de l'ordre d'une heure de disque [est.]).
5. **A n'est pas sans risque** : son risque principal est la localité réelle, ×3,0 entre les scénarios
   uniforme et LRU sur son plafond [calc. 07]. B ne le supprime pas, mais B3 l'amortit : à la
   localité uniforme, B3 (λ = 0) donne 3,33 j/s là où A donne 2,05.

Ce que A d'abord a pour lui, et que je reconnais : il se juge exactement, sans seuil discutable ; il
ne demande aucune mesure de qualité ; un programme qui marche arrive par le chemin le plus court.
Mon ordre ne le retarde que de 5 à 10 % (§ 4), parce que le moteur de B commence par être A.

---

## 6. La première version exacte

Nom de travail : **troncons v1, « B d'abord »**. Réponses par délégation du 2026-10-15, réversibles,
chacune avec sa raison.

### 6.1 Les modules (Rust, wgpu sur Vulkan, route 1 de 07)

Raison de la route 1 (un moteur à nous plutôt qu'un fournisseur d'experts dans llama.cpp) : la
politique de défaut doit agir *entre* le routeur d'une couche et la GEMV de ses experts, avec une
lecture de l'état du cache ; un graphe statique de llama.cpp demande une synchronisation après chaque
routeur et ne laisse pas choisir la table de reconstruction expert par expert.

| Module | Rôle | Témoin propre |
|---|---|---|
| `trc-format` | écrire le fichier `.trc` depuis le GGUF (CPU) ; lire sa table | chaque tronçon décodé sur le processeur redonne les 17 octets de chaque bloc d'origine ; un bit retourné est détecté |
| `trc-codec` | rANS v4 de 03 (codeur et décodeur processeur), étendu aux flux de base et de complément ; table des centres par tenseur | identité `H(base) + H(compl \| base) = H(code)` sur chaque tenseur ; taux réel contre entropie |
| `trc-es` | lectures sans tampon par IOCP, alignées sur 4 Kio, file de profondeur 4, vers la RAM épinglée | débit de bout en bout ≤ celui de chaque étage ; octets égaux à l'empreinte |
| `trc-carte` | noyaux Vulkan : décodeur v4 (03), réassemblage des classes, **réassemblage de la base en demi-octets**, **raffinement** (base + complément → code E2M1), **contrôle CRC32**, GEMV MXFP4 **à table de 16 valeurs choisie par expert**, et le passage avant de gpt-oss (attention à puits et fenêtre glissante une couche sur deux, RoPE YaRN, normes, routeur top-4, SwiGLU bornée, biais) | chaque noyau contre une référence processeur ; le passage avant contre llama.cpp dans l'écart entre moteurs |
| `trc-cache` | VRAM (emplacements de 13,25 Mo, état par expert : absent, base en vol, base, complément en vol, exact) ; RAM (bases codées, ou experts exacts codés selon la variante) ; admission (LRU, SLRU, statique) | le compte des usages servis par la base, rejoué depuis le journal du moteur par un simulateur indépendant, doit être égal |
| `trc-politique` | décision à chaque défaut, au moment où le routeur donne les poids g : attendre l'exact, servir la base ; budget de perte ε déclaré | ε = 0 : zéro usage servi par la base ; ε = ∞ : tous les usages hors VRAM |
| `trc-moteur` | l'ordonnancement par couche (routeur → défauts → file du disque → décodage → GEMV), préchargement de ℓ+1 par le routeur de ℓ+1 sur le résidu de ℓ, échantillonnage | rendement physique publié (mesuré ÷ plafond) |
| `trc-juge` | vidage des logits, KL, premier choix, perplexité ; tâches par le juge de 06 | même modèle contre lui-même : KL nulle ; autre modèle : KL nettement positive (les deux témoins de 06) |

La GEMV de la base ne coûte rien de plus que celle du MXFP4 : la base est réassemblée en demi-octets
`(signe << 3) | classe`, et le même noyau lit une autre table de 16 valeurs (± les 4 centres, mis à
l'échelle E8M0 comme d'habitude). Le raffinement réécrit le demi-octet en place et bascule la table de
l'expert vers celle du MXFP4.

### 6.2 Le format `.trc`, au bit près

Un fichier compagnon du GGUF d'origine (qui garde les toujours-lus, A = 1,686 Go, lus une fois au
démarrage) ; il ne contient que les experts. Raison : ne pas dupliquer 1,7 Go, et garder le GGUF comme
seule source de vérité, désignée par son empreinte.

**En-tête** (aligné sur 4 Kio, petit-boutiste) :

| Champ | Type | Contenu |
|---|---|---|
| magie | 4 octets | `TRNC` |
| version | u16 | 1 |
| drapeaux | u16 | bit 0 : complément codé par rANS (sinon empaqueté brut, § 6.4 F1) ; bit 1 : flux de base conditionnés par la classe d'échelle |
| empreinte du GGUF source | 32 octets | SHA-256 |
| couches, experts, actifs, rôles | u16, u16, u8, u8 | 36, 128, 4, 3 pour le 120b |
| lignes, blocs par ligne | u32, u32 | 2 880, 90 |
| partition | 8 × u8 | classe de chaque magnitude E2M1 : `0 0 1 1 1 2 2 3` |
| décalage des tables, de l'index | u64, u64 | |

**Tables par (couche, rôle)** : 4 centres de classe en f32 (calculés sur ce tenseur, ce qui ne peut
qu'abaisser les 4,29 % mesurés sur un jeu de centres commun aux 12 tenseurs) ; table rANS des écarts
d'échelle δ ; 3 tables de base (une par classe d'échelle, alphabet de 64 : une paire de codes de base
de 3 bits par symbole, dans le décodeur v4 à alphabet octet) ; tables de complément par classe de
magnitude (si le drapeau 0 est levé).

**Index** : une entrée de 32 octets par expert et par couche (4 608 entrées pour le 120b, 147 Kio) :
décalage u64, longueur de la partie base u32, longueur de la partie complément u32, CRC32 de la partie
base, CRC32 des blocs MXFP4 d'origine des trois matrices (l'empreinte de l'exact), réserve.

**Un expert** (les trois matrices et leurs biais), deux parties contiguës, chacune alignée sur 4 Kio :

```
 partie BASE (≈ 8,3 Mo, une seule lecture au défaut)              partie COMPLÉMENT (≈ 3,8 Mo)
 ┌───────────────┬─────────────────────────────────────────────┐  ┌────────────────────────────────┐
 │ en-tête 16 o  │ pour gate, up, down :                       │  │ pour gate, up, down :          │
 │ (magie, tailles│  médianes de ligne (2 880 o, en clair)      │  │  classe {0 ; 0,5}  : 1 bit     │
 │  des flux)    │  biais (2 880 × f32, en clair)              │  │  classe {1;1,5;2}  : 1 trit    │
 │               │  δ d'échelle (tuiles rANS v4)               │  │  classe {3 ; 4}    : 1 bit     │
 │               │  base, 3 flux de classe d'échelle (rANS v4) │  │  classe {6}        : rien      │
 └───────────────┴─────────────────────────────────────────────┘  └────────────────────────────────┘
   bits par poids : 2,684 (base, échelles comprises)                1,222
```

Raison du groupement par expert plutôt que par matrice : le complément d'une seule matrice ferait
1,27 Mo, taille où le disque donne 2,2 Go/s (1 Mio, QD 2 à 4) au lieu de 2,6 à 2,9 Go/s à 4 Mio et
plus [mes. 01, `disque-balayage.csv`]. Groupés, la base se lit en 8,3 Mo et le complément en 3,8 Mo.

Le complément de chaque classe de magnitude forme son propre flux, ordonné comme les codes de cette
classe ; le décodeur, qui a déjà la base, sait à quel flux puiser : c'est le même geste que les trois
classes d'échelle de 03, dont le réassemblage est mesuré à 41,6 Go/s [mes. 03].

### 6.3 L'ordre de construction

Chaque étape a son témoin, et rien ne passe à la suivante sans lui.

| Étape | Contenu | Témoin | Carte ? |
|---|---|---|---|
| **Q0** | banc de qualité sans moteur (§ 3.3) : Q0.a à Q0.d sur gpt-oss-20b, Q0.a sur le 120b | ré-expression exacte en Q8_0 dans le plancher de l'instrument ; cassure qui en sort | oui, 2 à 4 h |
| **F1** | `trc-codec` : base et complément, conditionnés par la classe d'échelle ; complément rANS contre empaqueté brut | identité de la chaîne par tenseur ; décodage exact des 108 tenseurs du 120b | non |
| **F2** | `trc-format` : écrire le `.trc` du 20b puis du 120b | chaque expert décodé sur le processeur égale ses blocs d'origine (CRC et comparaison octet à octet) | non |
| **E1** | `trc-es` + DMA + décodeur v4 + réassemblage de la base + raffinement | octets exacts à l'arrivée ; débit de bout en bout sous chaque étage | oui |
| **M1** | passage avant Vulkan de gpt-oss-20b, experts exacts en RAM non codés | KL contre llama.cpp dans l'écart entre moteurs (à remesurer sur gpt-oss) | oui |
| **M2** | experts lus du `.trc`, cache, préchargement, **mode ε = 0** (c'est A) | logits identiques au bit à M1 ; **premier programme qui marche** | oui |
| **B1** | mode B1 (base au défaut, complément en arrière-plan), politique par poids de routage | ε = 0 → identique au bit à M2 ; compte des usages servis par la base égal au rejeu | oui |
| **B2** | mode B3 (RAM de bases, VRAM statique ou filtrée), balayage de ε | idem ; part servie par la base égale au rejeu | oui |
| **G** | gpt-oss-120b : jetons/s, RAM et VRAM de pointe, octets lus (compteur PDH), qualité, rendement physique, pour A (ε = 0), B1 et B3 | ABBA, bruit de référence, règle 2 × bruit et 3 % (06 § 7.5) | oui |

Q0 est en tête parce qu'il ne dépend de rien d'autre que du juge existant, et parce qu'il décide si
B2 a une raison d'exister. F1 et F2 se font sur le processeur pendant que la carte sert à d'autres.

### 6.4 Les critères de qualité, seuils déclarés avant toute mesure

Réponse par délégation du 2026-10-15, réversible. Raison générale : un seuil dérive d'une grandeur
mesurée qu'on nomme (SOCLE) ; je reprends ceux de 06 et 07 sans les desserrer, et j'en ajoute un qui
dit si B est une contribution même quand il n'est pas indiscernable.

- **Q-instrument** : la ré-expression exacte (Q8_0) d'un modèle retombe à KL moyenne ≤ 7·10⁻⁵ et
  premier choix 100 % (plancher mesuré en 06) ; sinon le banc est faux et rien n'est publié.
- **Q1, « indiscernable »** (le seuil de 07, inchangé) : KL moyenne de B contre le mode exact du même
  moteur ≤ **0,0055** et premier choix identique ≥ **95,96 %**, sur 10 fenêtres de 512 jetons de
  wikitext-2 test (06 § 7.4). Si Q1 tient, B est activé par défaut.
- **Q2, « contribution »** : le point de B (KL moyenne, Go lus du disque par jeton) passe **sous** la
  frontière des requantifications uniformes des experts (Q0.d), interpolée linéairement en log(KL)
  entre les deux points voisins, d'au moins deux erreurs-types de la KL (celles que rend
  llama-perplexity). Si Q2 tient et Q1 non, B est publié comme mode à budget déclaré, désactivé par
  défaut.
- **Q3, tâches** : HellaSwag (400), Winogrande (400), ARC et MMLU par le juge de 06 ; une différence
  n'est réelle que si les intervalles binomiaux ne se recouvrent pas. Q1 exige aucune baisse réelle
  contre le mode exact ; Q2 se compare au point de la frontière de même octets.
- **Perplexité** : publiée (rapport et erreur-type), non décisive (06 a montré que le moteur seul la
  déplace de 0,4 %).
- **F1, la découpe** : le conditionnement par classe d'échelle est adopté s'il ramène la découpe à
  moins de **0,4 %** au-dessus du flux unique de A (le coût des en-têtes d'un flux de plus, 0,40 % de
  tuile [mes. 03]). Le complément est codé par rANS seulement s'il économise au moins **1 %** de la
  partie complément contre l'empaquetage brut (1 bit, 1,6 bit par trit en paquets de 5, 0) ; sinon
  brut, pour un noyau plus simple.
- **Vitesse** : un mode B ne vaut que s'il bat le mode exact du même moteur de plus de deux fois le
  bruit de référence et de 3 % en jetons/s mesurés, à RAM et VRAM égales (06 § 7.5).

**Critères de mort**, déclarés eux aussi :
- si Q0.c (B3, λ = 0, statique) est au-dessus de la frontière Q0.d **et** si Q0.b donne `K_tout` >
  0,25, la variante B3 sans politique est morte ; B3 ne survit qu'avec une politique, à prouver en B2 ;
- si aucun mode B ne passe Q2 en G, B avec perte est mort : on garde B1 comme gain de latence
  seulement s'il passe Q1, sinon le fichier revient au flux unique (on récupère les 1,33 %) ;
- si F1 laisse la découpe au-dessus de 1 % et que B est mort, le format revient au flux unique.

### 6.5 Les seuils de Q1 et Q2, et ce qui pourrait les déplacer

Le seuil 0,0055 vient de Qwen3.5-4B (processeur seul contre carte) ; l'écart entre deux moteurs justes
sur gpt-oss n'est pas mesuré. Je ne le remplace pas par un chiffre de gpt-oss avant de l'avoir : si la
mesure de M1 donne un autre écart, le seuil Q1 sera barré et remplacé au grand jour, jamais en
silence.

### 6.6 Les témoins

De ce plaidoyer (`partisan_b.py`, seuils déclarés dans l'outil avant le lancement) :

| Témoin | Seuil | Obtenu | Cassure (`--casser`) |
|---|---|---|---|
| T1 : B3 avec une « base » égale au code entier redonne A de `plafonds.py`, trois scénarios | 1·10⁻⁹ relatif | tient (écart ≤ 1·10⁻¹⁵) | lit la base au lieu du code entier : 8,88 au lieu de 6,24, **tombe** |
| T2 : B1 sans compléments redonne le B1 de 07 | 1·10⁻⁹ relatif | tient | non concerné (déclaré tel) |
| T3 : les énergies retrouvées redonnent les 42 erreurs publiées | 1·10⁻⁶ relatif | tient (3,9·10⁻¹⁶) | `W_3` faussée de 1 % : 2,8·10⁻³, **tombe** |

Premier passage barré : ~~T1 et T2 tiennent du premier coup~~ ; ils sont d'abord tombés à 10⁻⁵ près,
parce que j'avais écrit `b_A = 3,8545` arrondi quand `plafonds.py` utilise `4,25 / 1,1026` ; et T3
est d'abord tombé à 8,7·10⁻⁵, parce que les centres publiés par 07 sont arrondis à quatre décimales.
Corrigé en prenant le taux exact et en affinant les énergies sur les erreurs publiées en pleine
précision ; les seuils n'ont pas bougé.

Du premier livrable, en plus de ceux du § 6.1 :
- **exactitude du raffinement** : chaque expert raffiné égale, au bit, ses blocs d'origine (CRC32 sur
  la carte contre l'index, puis comparaison processeur sur un échantillon) ; un bit du complément
  retourné doit être détecté ;
- **ε = 0 est A** : logits identiques au bit au même moteur lisant un flux unique ;
- **la base sur la carte égale la base au processeur** : GEMV à table de centres contre une référence
  f64, écart relatif ≤ 1·10⁻⁵ (accumulation f32) ;
- **la politique compte juste** : la part des usages servis par la base, comptée par le moteur, égale
  celle d'un simulateur de cache indépendant rejouant le journal de routage ;
- **le juge tombe quand il doit** : les deux témoins de 06 (même modèle, autre modèle).

---

## 7. Ce qui dépend de `mesures/gpt-oss.md` (en cours chez un autre agent)

| Grandeur attendue | Ce qu'elle décide ici |
|---|---|
| `h(c)` réel de gpt-oss-120b (LRU, et si possible statique) | tous les plafonds du § 2 ; le coût de la VRAM statique de B3 (0,590 → 0,515 supposé) ; le λ où B3 rejoint A |
| ρ, la réutilisation d'un jeton au suivant | l'ensemble chaud de Q0.c ; la pertinence d'un filtre d'admission qui rendrait B3 moins statique |
| **les poids de mélange g** (le traceur les écrit) | **s**, la part de Σ g² que portent les usages servis par la base, donc l'ordre de grandeur de la KL de B1 et B3 (§ 3.2), et la règle de la politique |
| la fréquence de chaque expert par couche | l'ensemble chaud de Q0.c (trace sur un corpus distinct du texte de jugement) |
| la base llama.cpp mesurée | les rapports entre B et la base ; elle ne change pas le rapport entre B et A |

Si cette étude montre une localité proche de l'uniforme, B3 devient plus utile (×1,62 sur A) mais sert
92 % des usages par la base : la qualité tranchera seule.

---

## 8. Ce qui pourrait être faux

- **Le modèle de débit reste celui de 07** (`h(c) = c^β` calé sur un point, recouvrement parfait au
  plafond) ; mes corrections portent sur les octets, pas sur ces hypothèses.
- **Le plancher en série de B1 suppose que les compléments tiennent dans le temps libre du disque**
  pendant la PCIe et la carte. C'est vrai dans les trois scénarios avec ces débits ; un moteur réel,
  plus proche du plafond, verra un gain plus petit que +23 %.
- **La VRAM statique de B3** est calée sur un point LFU publié pour Qwen3-30B-A3B ; elle peut être
  meilleure (gpt-oss a peut-être des experts très chauds) ou pire.
- **`K_tout ∈ [0,10 ; 0,25]` est une analogie**, pas une mesure ; tout le tableau de KL en dépend
  linéairement. La linéarité de HIGGS vaut pour de petites erreurs ; 4,3 à 5,9 % par expert n'en est
  pas une. L'indépendance des erreurs entre experts et la pondération par g² sont des hypothèses.
- **La base est mesurée sur 12 tenseurs de gpt-oss-20b** avec un jeu de centres commun ; des centres
  par tenseur feront mieux, le 120b peut différer (peu probable : entropies égales à 0,001 bit [03]).
- **Les énergies `W_m` sont retrouvées, pas recomptées** : le système est surdéterminé et cohérent à
  10⁻¹⁶, mais il ne voit que la loi globale des 12 tenseurs ; l'erreur aimantée par tenseur peut
  varier.
- **Q0.b suppose que llama.cpp calcule une matrice Q8_0 d'experts comme une MXFP4** à la précision
  près ; si le chemin de calcul diffère (autre noyau, autre accumulation), l'écart entre chemins
  s'ajoute à la mesure. Le témoin de ré-expression exacte le détecte.
- **`llama-quantize` peut refuser une source MXFP4** pour Q0.d ; il faudrait alors écrire la
  requantification nous-mêmes (déquantifier, puis quantifier par les fonctions de ggml).
- **Les estimations de délai et de complexité (§ 4, § 5) sont des estimations** ([est.]) : aucun
  moteur n'existe encore pour les vérifier.
- **SliceMoE et HOBBIT ont été lus en HTML par un outil de lecture** qui résume ; les chiffres cités
  ont été relevés dans ce rendu, pas dans le PDF. TRACE, MatGPTQ, AnyBCQ et Drop-by-Drop restent lus
  au résumé seulement (07) : l'un d'eux peut encore réduire la part neuve de B.
- **Le CRC32 sur la carte** n'est pas un contrôle cryptographique ; il suffit contre la corruption
  accidentelle, pas contre une falsification (hors sujet ici).

---

## 9. Recettes (essayées dans ce plaidoyer, avec leur raison)

| Recette | Marche ? | Raison |
|---|---|---|
| Recompter les octets d'une architecture terme à terme, pas son plafond | oui | a révélé le trafic des compléments absent de B1 et B2 dans `plafonds.py` |
| Témoin « la même formule sans le terme ajouté redonne l'ancien chiffre » (T2) | oui | prouve que l'écart vient du seul terme ajouté, et pas d'une autre divergence de code |
| Réutiliser `plafonds.py` par `importlib` avec inscription dans `sys.modules` | oui | même piège que 07 (dataclass) ; aucun débit recopié à la main |
| Prendre `b_A` arrondi (3,8545) | échec | T1 tombe à 10⁻⁵ : le taux publié est 4,25 / 1,1026 ; toujours dériver d'une seule source |
| Retrouver les énergies par magnitude depuis les centres arrondis | échec partiel | centres à 4 décimales : 8,7·10⁻⁵ d'écart ; corrigé par Gauss-Newton sur les erreurs en pleine précision (42 équations, 7 inconnues) |
| Aimanter la base sur des valeurs E2M1 | oui | rend la base lisible par llama.cpp sans toucher à ses noyaux ; coût 1,62 point d'erreur |
| Lire le corps des voisins avant d'écrire « neuf » | oui, et la frontière a bougé | HOBBIT et SliceMoE font le choix selon le routeur ; il reste à B la base fonction du code, le codage entropique et le raffinement exact |
| Ne lancer aucune lecture de disque ni de carte | choisi | un autre agent mesure sur les deux ; tout ici se calcule depuis des journaux commités |

---

## 10. Sources (consultées le 2026-10-15)

- SliceMoE: Bit-Sliced Expert Caching under Miss-Rate Constraints for Efficient MoE Inference —
  https://arxiv.org/html/2512.12990 — v5 du 2026-09-08 ; corps lu (HTML).
- HOBBIT: A Mixed Precision Expert Offloading System for Fast MoE Inference —
  https://arxiv.org/html/2411.01433v2 — v2 du 2024-11-06 ; corps lu (HTML).
- Les sources des études 01 à 07 (HIGGS, ApexQuant, études d'Equitz et Cover, Edge0, SSD-LLaMA,
  PR llama.cpp #25294…) sont dans leurs fichiers et dans `memoire/sources/*.bib`.

Références biblatex : `memoire/sources/decisions-partisan-b.bib`.

---

## Annexe A. Les dérivations

**A.1 Octets d'une architecture, compléments comptés.** Avec `f = R / 4,25` (octets d'un bit par poids
sur les experts d'un jeton) :

    disque = f · [ h_s · b_def + C ]          PCIe = f · [ h_r · b_ram + h_s · b_def + C ]

où `C` est la part des compléments lus par jeton, en bits par poids rapportés aux experts d'un jeton :
- A : `b_def = b_ram = b_A`, `C = 0` ;
- B1 complété : `b_ram = b_A`, `b_def = b_base`, `C = h_s · b_compl` ; disque = `f · h_s · (b_base +
  b_compl)` = `f · h_s · b_découpe`, d'où le plafond de A au surcoût de découpe près ;
- B3(λ) : `b_ram = b_def = b_base`, `C = λ · (1 − h_v) · b_compl`.

`T_carte` est celui de 07. Plafond : `1 / (max(T_disque, T_pcie, T_carte) + t0)`.

**A.2 Le plancher en série avec un complément hors du chemin critique.** Le disque ne travaille, en
série, que pendant son chemin critique ; il est libre pendant `T_pcie + T_carte + t0`. Les compléments
hors chemin critique (B1 : `(1 − λ) h_s b_compl f`) y tiennent si leur temps de lecture n'excède pas ce
temps libre ; sinon l'excédent s'ajoute :

    t_série = T_disque,crit + max(0, T_compl,hors − (T_pcie + T_carte + t0)) + T_pcie + T_carte + t0

LRU calé, B1, λ = 0 : `T_disque,crit = 0,234 × 1,9085 × 2,684 / 4,25 / 2,58 = 0,1093 s` ;
`T_compl,hors = 0,234 × 1,9085 × 1,222 / 4,25 / 2,58 = 0,0497 s` ≤ `0,0586 + 0,0360 + 0,0035` ;
`t_série = 0,1093 + 0,0586 + 0,0360 + 0,0035 = 0,207 s` → 4,83 jetons/s.

**A.3 Le λ où B3 rejoint A.** Le plafond de B3 décroît avec λ (le disque limite) ; entre λ = 0,5
(6,97) et λ = 0,75 (5,91), il croise A (6,24) à `0,5 + 0,25 × (6,97 − 6,24) / (6,97 − 5,91) ≈ 0,67`
(interpolation linéaire, LRU calé).

**A.4 La pondération par g².** `y = Σ_i g_i E_i(x)` ; si `Ê_i = E_i + δ_i` avec des `δ_i` indépendants
et centrés, `E‖ŷ − y‖² = Σ_i g_i² E‖δ_i‖²`. Sous la linéarité de HIGGS, l'excès de perte est
proportionnel à cette somme rapportée à son maximum (tous les experts approchés), d'où
`KL_B ≈ K_tout · Σ_{usages servis par la base} g² / Σ_{tous les usages} g² = K_tout · W`.

**A.5 L'erreur d'une base aimantée.** Pour une classe `k` de magnitudes, l'erreur
`Σ_{m ∈ k} W_m (m − v)²` est un trinôme en `v` minimal au centre de gravité `c_k` ; parmi les valeurs
E2M1, la meilleure est donc la plus proche de `c_k` (le trinôme est symétrique autour de `c_k`).
Partition {0 ; 0,5} {1 ; 1,5 ; 2} {3 ; 4} {6} : centres 0,237 ; 1,424 ; 3,419 ; 6 → valeurs 0 ; 1,5 ;
3 ; 6 ; erreur relative 5,913 % contre 4,292 %.

**A.6 Le surcoût de la découpe.** `b_base = 2,6415 × 1,003 + 0,0344 = 2,6839` ; `b_compl = 1,2182 ×
1,003 = 1,2219` ; `b_découpe = 3,9057` ; `b_A = 4,25 / 1,1026 = 3,8545` ; `3,9057 / 3,8545 − 1 =
1,33 %`.

## Annexe B. Outils et journaux

- `outils/decisions/partisan_b.py` → `decisions/journaux/partisan-b.json`,
  `decisions/journaux/partisan-b-casse.json`, `decisions/journaux/csv/b-complements-gptoss120b.csv`,
  `decisions/journaux/csv/b3-lambda-gptoss120b.csv`.
- Commandes, depuis la racine du dépôt :
  `python -I -X utf8 outils/decisions/partisan_b.py > decisions/journaux/partisan-b.json` et
  `python -I -X utf8 outils/decisions/partisan_b.py --casser > decisions/journaux/partisan-b-casse.json`.
