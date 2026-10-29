# Partisan de A : l'exactitude et l'ingénierie d'abord

Plaidoyer pour l'arbitre de troncons, rédigé le 2026-10-15 par le partisan de l'architecture A
(fondations/07-ce-qui-manque.md § 4.1) : tout par la carte, octets codés sans perte de bout en bout,
cache d'experts en VRAM, lectures à la taille d'un expert. Le rôle demande de plaider A au mieux et
d'en chiffrer honnêtement le prix. Les deux sont faits ci-dessous, avec les mêmes nombres.

Étiquettes (celles de l'étude 07) : **[mes.]** mesuré sur la machine de Stone, outil et journal
commités ; **[calc.]** calculé par un outil commité ; **[litt.]** littérature, non reproduite. Un
chiffre repris d'une étude garde son numéro (« [mes. 01] »). **[expl.]** marque l'exploration de
l'agent qui mesure gpt-oss, qu'il n'a pas retenue lui-même (une passe, pas d'ABBA) : elle sert
d'ordre de grandeur, jamais de juge.

Outil : `outils/decisions/partisan_a.py`. Il ne mesure rien, ne lit ni le disque ni la carte : il
importe tel quel `outils/07-synthese/plafonds.py` (l'équation du jeton) et calcule. Journaux :
`decisions/journaux/partisan-a/partisan-a.json`, `partisan-a-casse.json`, CSV des figures sous
`csv/`. Les sections du journal sont citées « S1 » à « S19 ».

Ce que je n'ai pas fait, volontairement : rien sur la carte graphique (un autre agent mesure),
aucune lecture lourde du disque (ses séries ABBA en dépendent), et je n'ai pas lu
`decisions/partisan-B.md`, pour que les deux plaidoyers restent indépendants. En listant
`outils/decisions/`, j'ai vu l'en-tête de `partisan_b.py` ; je le dis au § 3.4, là où j'en parle.

**État de la mesure dont tout dépend.** À l'heure où j'écris (11 h), `mesures/gpt-oss.md` n'est pas
commité : la courbe `h(c)`, ρ et la base llama.cpp mesurée en ABBA ne sont pas rendues. Le § 6 dit ce
qui, dans ce plaidoyer, tombe ou tient selon ce qu'elle donnera.

---

## 0. En bref

1. **A n'est pas une alternative à B, c'est son plancher et son juge.** C'est un plancher par le code :
   B est A plus quatre modules, et B qui sert tous ses défauts exacts *est* A. C'est un juge par la
   mesure : le seuil de qualité que l'étude 07 pose pour B est une divergence KL **contre A** (même
   moteur, même étage), sous 0,0055. Or 0,0055, c'est aussi l'écart mesuré entre deux moteurs justes
   [mes. 06]. Sans un A prouvé exact au bit, une erreur de moteur ordinaire mange tout le budget de
   qualité de B. Avec lui, la résolution de la mesure passe de 0,0055 au plancher de l'instrument
   (99,9e centile 0,000055, maximum 0,000068 [mes. 06]) : **81 fois plus fine**.
2. **Ce que mon camp sacrifie, en vitesse** [calc., S2] : A plafonne à **70 % de B1 dans les trois
   scénarios de localité** (2,05 contre 2,93 ; 6,24 contre 8,88 ; 10,34 contre 14,62 jetons/s), et à
   57-62 % de B2. Sur un disque non chiffré, 14,1 contre 19,4 (LRU calé). Le rapport A/B1 ne dépend
   presque pas de la localité : tant que le disque tient le maximum, il ne dépend que des bits lus
   au défaut (3,85 contre 2,68).
3. **Ce qu'il sacrifie en science** : sa nouveauté est un assemblage (le trou I1 de l'étude 07), pas un
   mécanisme. Le seul mécanisme neuf de la carte des trous est R1, et il appartient à B. Je le
   concède sans détour : un A seul ferait un bon rapport d'ingénierie, pas un article de recherche.
4. **Si la localité est mauvaise, A tient, B se dégrade.** Au routage uniforme, A garde 2,05 jetons/s
   (plancher en série 1,47), soit 4,2 fois (3,0 fois) l'exploration de la base llama.cpp sur
   gpt-oss-120b (0,49 jeton/s [expl.]) [calc., S14]. B garde son gain de ×1,43, mais la part des
   usages d'experts servie par sa base passe de 14 % (Belady) à **72 %**, et l'erreur moyenne ajoutée
   de 0,45 à **2,3 fois le bruit propre du MXFP4** [calc., S15] : le gain de B est fixe, son risque
   croît d'un facteur 5 quand `h` empire.
5. ~~**Le contre-argument que je dois au lecteur** : B1 bat A dès que plus de **4,2 %** des défauts sont
   servis par la base~~ (barré par l'arbitre le 2026-10-15 : f* suppose les compléments gratuits ;
   comptés, le disque lit 3,906 bits au défaut contre 3,855 et B1 ne bat A qu'en série ;
   `decisions/ARCHITECTURE.md` § 1.7) (point d'égalité f* = 0,958, le même dans les trois scénarios, car il ne dépend
   que des bits) ; à mi-chemin (la moitié des défauts servis exacts), B1 gagne encore **+17 %**
   [calc., S13]. B n'est donc pas un pari « tout ou rien » : s'il tient même à moitié, il paie.
6. **Faire B d'abord coûte A entier, plus quatre modules dont un décodeur jamais mesuré, et une mesure
   de qualité sans référence exacte.** Préparer B dans le format de A ne coûte rien : je propose un
   conteneur où les flux d'un tronçon sont rangés par niveau de raffinement, de sorte qu'**une lecture
   de préfixe donne un niveau inférieur**. La v1 y range le codage sans perte à trois classes, mesuré
   (r = 1,1026, décodeur à 41,6 Go/s [mes. 03]) ; B y ajoutera ses deux flux sans toucher au lecteur,
   au cache ni à l'ordonnanceur. Le recodage du fichier, le jour où B arrive, coûte de l'ordre de
   **47 minutes de processeur, une fois** [mes. 03, S16]. Je m'écarte ici de l'étude 07 § 4.4, qui
   mettait base et complément dans A dès la v1 : raisons et coût au § 4.3.
7. **La fenêtre de travail est trois fois plus petite que celle publiée.** Avec des tampons de
   quelques couches au lieu de deux jetons entiers, A0 sert gpt-oss-120b avec **0,64 Go de RAM de
   pointe** (1,26 Go si la table d'enchâssement reste en RAM), contre 1,9 Go dans l'étude 07 [calc.,
   S12]. Et comme gpt-oss-20b et 120b ont la même taille d'expert, le même k et la même table
   d'enchâssement, **leur RAM de pointe doit être la même à 0,5 Mo près** : c'est le témoin direct de
   « la mémoire ne dépend plus de la taille du modèle ».
8. **La première version exacte** (§ 4) : dix modules, un format au champ près, neuf étapes chacune
   avec son témoin et sa cassure, onze critères de réussite déclarés maintenant et dérivés de
   grandeurs mesurées, quatre critères d'abandon. Aucun téléchargement.

Réponse par délégation du 2026-10-15, réversible : **construire A d'abord, dans le conteneur à
préfixes qui prépare B ; mesurer la qualité de B en parallèle, sans moteur, dès que possible ;
faire entrer B dans le moteur quand A a passé son témoin d'exactitude.** Justification en une ligne :
A ne coûte rien que B n'ait à payer aussi, il est la seule référence qui rende la qualité de B
mesurable, et il tient même dans le pire scénario de localité.

---

## D'où on part, où on va

**Au départ** : l'étude 07 a posé l'équation du jeton, chiffré trois architectures sur les débits
mesurés de la machine et recommandé « A d'abord, dans un format qui prépare B ». Elle a laissé
ouvertes : la localité réelle de gpt-oss-120b, la base llama.cpp mesurée, la forme exacte du format,
la fenêtre de travail minimale, et ce que B coûte vraiment à A.

**Ce que ce plaidoyer établit** : le prix de A face à B, chiffré dans les trois scénarios et sur deux
disques ; le point d'égalité entre B1 et A (f* = 0,958) et sa forme close ; la fenêtre de travail
minimale (0,64 Go) et un témoin d'indépendance de la mémoire qui peut tomber ; le budget de VRAM
poste par poste (414 emplacements d'experts, +2,7 % de plafond sur l'hypothèse de 6,5 Go) ; le
budget de la carte (le décodeur peut être 7,4 fois plus lent avant que la carte ne prenne le
maximum) ; un format de fichier au champ près ; un ordre de construction avec témoins ; des
critères de réussite et d'abandon déclarés avant toute construction.

**Ce qui reste** : la mesure de localité (en cours, autre agent), puis la construction elle-même ; la
qualité de B ; et le jugement de l'arbitre entre ce plaidoyer et celui de B.

---

## 1. La thèse

### 1.1 A est le plancher de B, dans le code

Écrivons ce que chaque architecture exige (fondations/07 § 4.1 et § 4.2) :

| Brique | A | B |
|---|---|---|
| Passe avant de gpt-oss en Vulkan (attention à puits et fenêtre, RoPE YaRN, routeur, SwiGLU bornée, biais) | oui | oui, la même |
| Lecteur sans tampon de la taille d'un expert, file IOCP | oui | oui, le même |
| Mémoire hôte visible de la carte, DMA | oui | oui, la même |
| Décodeur rANS v4 et réassemblage des classes | oui | oui, plus un second |
| Cache d'experts décodés en VRAM, cache codé en RAM | oui | oui, plus un niveau par entrée |
| Codeur hors ligne GGUF → tronçons | sans perte | base + complément, production d'un codeur aujourd'hui en Python de mesure |
| Décodeur du complément, avec une table choisie par le symbole de base | — | **neuf, jamais mesuré** |
| Ordonnancement des compléments sur le temps libre du disque | — | neuf |
| Politique de défaut (servir la base, attendre, re-router) | — | neuve (R3) |
| Juge de qualité contre une référence exacte | témoin au bit | KL contre A |

B contient A. Et B qui lit le complément de chaque défaut sur le chemin critique (f = 1) lit
`2,684 + 1,222 = 3,906` bits par poids au défaut, contre 3,855 pour A : il est A, un peu plus lent
(6,16 contre 6,24 jetons/s, LRU calé) [calc., S3]. Le chemin le plus court vers un B qui marche
passe donc par un A qui marche ; la seule question est l'ordre dans lequel on *vérifie*.

### 1.2 A est le juge de B, dans la mesure

Le seuil de B, déclaré par l'étude 07 avant toute mesure, est « KL moyenne contre A (même moteur,
même étage) sous 0,0055, premier choix identique au-dessus de 95,96 % ». Ces deux nombres sont
l'écart mesuré entre deux moteurs justes sur les mêmes poids (Qwen3.5-4B, processeur seul contre
carte [mes. 06]). Deux conséquences :

- **Sans A exact, le budget de B est déjà consommé par le bruit du moteur.** Un moteur à nous, neuf,
  qui différerait de llama.cpp autant que llama.cpp diffère de lui-même entre deux étages, produirait
  à lui seul une KL de 0,0055. Mesurer B contre llama.cpp, ou contre un moteur non prouvé, confond la
  perte de la base et l'erreur d'implémentation, dans des proportions inconnues.
- **Avec A exact, la référence a un bruit nul par construction.** Le témoin de A (§ 4.7, C3) est
  l'égalité au bit des logits entre le chemin codé et le chemin brut du même moteur. Le plancher de
  l'instrument est alors celui de l'étude 06 : KL moyenne nulle, 99,9e centile 0,000055, maximum
  0,000068 [mes. 06]. La plus petite perte de B que l'on puisse distinguer passe de 0,0055 à
  ≈ 0,000068 : **un facteur 81** (`0,0055 / 0,000068`).

Le principe, dit en une phrase : **on n'introduit pas une perte dans une chaîne qu'on n'a pas encore
prouvée exacte.** C'est la même règle que les témoins du SOCLE, appliquée à l'architecture.

### 1.3 A ne demande rien de neuf à la physique

Chaque maillon de A est mesuré sur cette machine, avec témoins et ABBA : la lecture de 4 Mio (2,58
Go/s), la DMA depuis la mémoire hôte (12,2), le décodeur à trois classes (41,6), la GEMV MXFP4 brute
(209,4) [mes. 01, 03]. Les inconnues de A sont des inconnues d'intégration, pas de physique :
l'import de mémoire hôte sous Vulkan par wgpu, le coût d'une synchronisation par couche pour lire le
routeur, la latence réelle d'un défaut. Chacune a sa mesure préalable (§ 4.6, étape 0) et son repli
chiffré (S6, § 4.5).

### 1.4 A répond à la lettre de Stone

« sans ram ni rien » se lit, dans le SOCLE, comme « la mémoire occupée ne dépend plus de la taille du
modèle ». A0 en est la forme extrême, et le § 4.4 montre qu'elle est plus petite que publiée :
**0,64 Go de RAM pour un modèle de 63,4 Go**, à 3,6 jetons/s de plafond dans le scénario LRU calé
[calc., S12, S2]. B a besoin de la RAM pour être B (B2 n'existe que par elle) ; A la rend réglable.

---

## 2. Ce que mon camp sacrifie

### 2.1 Le plafond

[calc., S2, `csv/sacrifice-a-contre-b.csv`] gpt-oss-120b, RAM 11 Go (A0 : 0), VRAM 6,5 Go pour les
poids (hypothèse de 06 ; le budget réel est au § 4.4), décodeur 41,6 Go/s, GEMV 209,4, PCIe 12,2.

**Disque chiffré, lecture de 4 Mio à 2,58 Go/s [mes. 01]**

| Scénario | A : plafond / série | A0 | B1 : plafond / série | B2 | A / B1 | A / B2 |
|---|---|---|---|---|---|---|
| uniforme (β = 1) | 2,05 / 1,47 | 1,61 / 1,23 | 2,93 / 2,00 | 3,33 / 2,22 | **0,70** | 0,62 |
| LRU calé (β = 0,207) | **6,24** / 3,93 | 3,59 / 2,68 | **8,88** / 5,09 | 10,89 / 5,94 | **0,70** | 0,57 |
| Belady calé (β = 0,117) | 10,34 / 6,17 | 5,70 / 4,15 | 14,62 / 7,83 | 18,04 / 9,11 | **0,71** | 0,57 |

**Disque non chiffré à 6,0 Go/s (annonce de Samsung, borne haute [litt. 01])**

| Scénario | A | B1 | B2 | Étage limitant de B1 | A / B1 |
|---|---|---|---|---|---|
| uniforme | 4,72 | 6,73 | 7,62 | disque | 0,70 |
| LRU calé | 14,11 | 19,39 | 22,74 | **PCIe** | 0,73 |
| Belady calé | 22,95 | 29,50 | 30,84 | **PCIe** | 0,78 |

Lecture : sur le disque chiffré, A perd 30 % du plafond de B1 dans tous les scénarios ; le rapport est
constant parce que, le disque tenant le maximum, `jetons/s ≈ r · D_disque / (h_s · R)` et seul `r`
change (1,1026 contre 1,584 au défaut). Sur un disque rapide, l'écart se resserre (0,73 à 0,78) :
B1 bute sur la PCIe, A pas encore.

### 2.2 La nouveauté scientifique

Je ne peux pas plaider que A est une contribution de recherche au même titre que B :
- ce qu'A a de neuf est l'assemblage I1 (la chaîne complète sous Vulkan et Windows), les lectures à
  la taille d'un expert (I2), le régime batterie chiffré (I5) et le coût de BitLocker pour un flux de
  poids (I8) : de l'ingénierie mesurée, que l'étude 07 range elle-même sous « ingénierie » ;
- R1, le raffinement exact d'un format 4 bits natif lié à l'étage, est le seul mécanisme de la carte
  des trous ; il est à B.

Ce qu'A peut publier quand même, et qui n'existe pas ailleurs à ma connaissance (études 04 et 07) :
le **rendement physique mesuré** d'une chaîne disque → VRAM en octets codés sur un portable grand
public chiffré, dans les deux régimes d'alimentation ; la **fenêtre de travail bornée**, énoncée
(annexe A.1) et prouvée par le témoin 20b contre 120b ; et, en sous-produit, la courbe de succès
d'un cache *réel* sur gpt-oss-120b, comparée à son simulateur. Une nuance, contre B cette fois : la
nouveauté de R1 n'est pas acquise non plus (SliceMoE et TRACE n'ont été lus qu'au résumé, 07 § 6).

### 2.3 Si la localité est mauvaise

**Le plafond de A contre la part lue du disque** (`h_v` fixé à 0,590, scénario LRU calé pour la carte ;
[calc., S9, `csv/a-contre-hs.csv`]) :

| h_s | 0,05 | 0,10 | 0,15 | 0,20 | 0,234 | 0,30 | 0,40 | 0,50 | 0,60 | 0,723 |
|---|---|---|---|---|---|---|---|---|---|---|
| Plafond de A | 16,2 | 14,2 | 9,60 | 7,26 | 6,23 | 4,88 | 3,68 | 2,95 | 2,46 | 2,05 |
| Plancher en série | 7,63 | 6,07 | 5,04 | 4,31 | 3,93 | 3,35 | 2,73 | 2,24 | 1,90 | 1,59 |

Sous h_s ≈ 0,09, ce n'est plus le disque qui tient le maximum mais la PCIe (58 ms par jeton, qui
porte tous les experts hors VRAM, h_r + h_s = 0,41) : la courbe s'aplatit (16,2 à 0,05).

**Contre la base** (exploration de l'autre agent, [expl.] : llama.cpp b11515, `-ngl 99 --cpu-moe`,
0,49 jeton/s en génération sur gpt-oss-120b, 295 Go lus en 761 s, soit 0,39 Go/s ; 7,69 jetons/s sur
gpt-oss-20b avec `--moe-cache-mib 4096`) [calc., S14] :

| | Plafond / base | Série / base |
|---|---|---|
| A, uniforme | 4,2 | 3,0 |
| A, LRU calé | 12,7 | 8,0 |
| A, Belady calé | 21,1 | 12,6 |
| A0, uniforme | 3,3 | 2,5 |
| A0, LRU calé | 7,3 | 5,5 |
| A0 sur gpt-oss-20b, LRU calé, contre 7,69 | 2,1 | **1,44** |

Ce que cela dit :
- **A survit au pire scénario** : même uniforme et en série, il resterait 3 fois au-dessus de cette
  exploration. Pour que A perde contre la base sur le 120b, il faudrait que la base mesurée en ABBA
  triple, ou que notre moteur reste sous un tiers de son propre plancher.
- **Sur le jumeau 20b, la marge est mince** (×1,44 en série) : ce modèle tient presque en RAM, et
  llama.cpp le sert déjà bien. Le 20b est un banc de développement pour A, pas une vitrine.
- **B, lui, voit son risque grandir quand h empire** [calc., S15] :

| | Part servie par la base | Erreur relative moyenne ajoutée | Rapport au bruit propre du MXFP4 (1,33 %) | Gain sur A |
|---|---|---|---|---|
| B1, Belady calé | 14 % | 0,60 % | 0,45 | ×1,41 |
| B1, LRU calé | 23 % | 1,00 % | 0,76 | ×1,42 |
| B1, uniforme | **72 %** | **3,10 %** | **2,34** | ×1,43 |
| B2, LRU calé | 41 % | 1,76 % | 1,32 | ×1,74 |
| B2, uniforme | 92 % | 3,95 % | 2,98 | ×1,62 |

(erreur ajoutée = part × 4,29 %, par la linéarité de HIGGS, ordre de grandeur seulement [litt. 02].)

### 2.4 Ce que A ne fait pas

- La qualité ne gagne rien : A est exactement gpt-oss-120b, ni mieux ni moins bien.
- Le processeur reste presque inactif : il lit le disque et tient les files. C'est un choix chiffré
  (07 § 3.3 : calculer les experts tièdes sur le processeur n'aide pas un étage qui ne limite pas).
- Il faut écrire une douzaine de noyaux neufs et les témoigner (§ 4.2), dont l'attention à puits.

---

## 3. Ce que coûte de faire B d'abord

### 3.1 En code

B d'abord, c'est écrire tout A (§ 1.1), plus :
1. un codeur de production base + complément (aujourd'hui une mesure en Python, `raffinement_mxfp4.py`) ;
2. **un décodeur du complément jamais mesuré** : la table de chaque code dépend du symbole de base à la
   même position, et l'alphabet du complément a 1 à 3 symboles par classe ({0 ; 0,5} : 2 ; {1 ; 1,5 ;
   2} : 3 ; {3 ; 4} : 2 ; {6} : 1). La v4 gagne son débit en décodant l'octet entier (deux codes par
   pas) ; un complément par code fait au moins deux fois plus de pas par poids. Le budget le
   permettrait sans doute : le décodeur peut descendre à **5,6 Go/s** avant que la carte ne prenne le
   maximum (disque chiffré, LRU calé ; 15,6 Go/s sur disque non chiffré) [calc., S5], contre 41,6
   mesurés. Mais c'est une marge calculée sur un noyau qui n'existe pas ;
3. l'ordonnancement des compléments sur le temps libre du disque, et un filtre d'admission ;
4. la politique de défaut (R3), qui n'a de sens qu'avec une mesure de qualité par défaut.

### 3.2 En mesure

Le § 1.2 : sans A exact, la perte de B se mesure contre un bruit de moteur qui a la taille de son
seuil. Concrètement, si B d'abord donnait une KL de 0,004, on ne saurait pas dire si la base coûte
0,004, 0, ou 0,008 compensés par une erreur de moteur de signe opposé.

### 3.3 En risque

Les deux échecs ne laissent pas la même chose derrière eux :
- **A d'abord, puis B échoue sur la qualité** : il reste un programme exact qui sert un modèle 3,6 fois
  plus gros que la RAM à 2 à 10 jetons/s de plafond selon la localité, et un format où B pourra
  revenir sous une autre base.
- **B d'abord, et sa qualité échoue** : il reste un moteur jamais prouvé exact, dont il faut retirer la
  base pour retrouver A, puis prouver A, c'est-à-dire refaire le chemin de A d'abord, avec retard.

Et le cas où B *réussit* ne pénalise pas A d'abord : le format de A garde la place de B (§ 4.3), et
passer de A à B coûte un recodage du fichier, de l'ordre de 47 minutes de processeur (le codeur de
l'étude 03 a codé *et* décodé exactement les 108 tenseurs d'experts du 120b, en deux variantes, en
2 831 s, machine partagée [mes. 03, S16]).

### 3.4 Ce que A d'abord ne retarde pas

La question scientifique de B, « que coûtent 23 à 72 % d'usages servis par la base ? », n'a pas besoin
de notre moteur pour recevoir une première réponse. En listant `outils/decisions/`, j'ai vu dans
l'en-tête de `partisan_b.py` l'idée d'une base « aimantée » sur des valeurs E2M1 existantes, qui
laisse le fichier en MXFP4 valide et se juge avec le juge de l'étude 06 sur llama.cpp. Je ne l'ai pas
évaluée ; si elle tient, elle donne à B sa mesure de qualité **en parallèle de la construction de A**,
sans rien lui retirer. C'est l'ordre que je recommande : A dans le moteur, la qualité de B hors du
moteur, puis B dans le moteur une fois A prouvé.

---

## 4. La première version exacte de A

### 4.1 Le périmètre de la v1

- **Modèles** : gpt-oss-20b pour le développement, réglé à M = 0 pour qu'il exerce le disque (avec
  4 Go de cache tiède il ne lirait presque plus rien du disque : h_s = 0,012 [calc., S8]) ;
  gpt-oss-120b pour le jugement. Aucun téléchargement.
- **Régime** : décodage par lot de 1, glouton ; le préremplissage de la v1 est une boucle de décodage
  (simple, exact ; son débit se publie à part et n'est pas un critère).
- **Contexte** : 4 096 jetons (cache KV de 0,16 Go en f16). À 131 072 jetons il prendrait 4,8 Go,
  presque tout le cache d'experts [calc., S10] : le long contexte est hors de la v1, et il se dit.
- **Moteur** : la route 1 de l'étude 07 (Rust, wgpu, Vulkan), qui réutilise nos briques mesurées
  (`outils/03-entropie/rans/src/decodeur.wgsl`, `gemv.wgsl`, `bin/taux_mxfp4.rs`).
- **Ce qui vient de llama.cpp (MIT), comme dépendance et non comme copie** : le découpage du texte en
  jetons, par `llama.dll` b11515 (déjà sur la machine, son API publique sert déjà au traceur de
  l'autre agent), et la base de comparaison.

### 4.2 Les modules

Un espace de travail Rust `moteur/` à la racine du dépôt.

| Module | Rôle | Brique existante (à nous) | Neuf | Témoin propre |
|---|---|---|---|---|
| `format` | structures du fichier, lecture et écriture des en-têtes, empreintes | lecteur GGUF de `taux_mxfp4.rs` | tout le conteneur | aller-retour écriture → lecture identique ; en-tête faussé refusé |
| `codeur` (exécutable) | GGUF → fichier de tronçons, puis décodage processeur de chaque tronçon et comparaison | codeur rANS v4 à trois classes (`taux_mxfp4.rs --classes`) | découpe par expert, alignement, répertoire | 100 % des tronçons égaux à la source ; taux égal à 1,1026 (120b) et 1,1037 (20b) à 0,1 % |
| `lecteur` | lectures sans tampon (`FILE_FLAG_NO_BUFFERING`, IOCP), file de profondeur 4, destination = mémoire hôte visible de la carte | banc `outils/banc` (`disque.rs`) | file pilotée par l'ordonnanceur | octets lus = octets sur le disque ; débit ≤ plafond du lien |
| `transport` | mémoire hôte importée dans Vulkan, copies vers la VRAM, barrières | `carte.exe transfert` (`outils/banc`) | import de mémoire hôte par interopérabilité wgpu-hal | aller-retour octet pour octet ; débit ≤ 15,754 Go/s |
| `decodeur` | rANS v4 et réassemblage des trois classes, à l'arrivée du tronçon, une fois | `decodeur.wgsl` (v4, 41,6 Go/s avec réassemblage) | écriture directe dans l'emplacement du cache | empreinte de chaque tronçon en mode témoin ; table corrompue → faux |
| `cache` | emplacements d'experts décodés en VRAM (414 de 13,25 Mo, § 4.4) ; cache codé en RAM (M Go) ; politique LRU puis SLRU ; un champ « niveau » par entrée, inutilisé en v1, prêt pour B | `chargement_localite.py` (simulateur, 04) | tout le cache réel | compte de succès du moteur = compte du simulateur sur la même trace, à l'unité |
| `ordonnanceur` | par couche : routeur → succès et défauts → lectures, DMA, décodage → GEMV ; v1 à la demande, v1.1 avec prédiction | — | tout | chronogramme horodaté ; aucun expert calculé avant son décodage |
| `passe_avant` | les noyaux WGSL de gpt-oss | `gemv.wgsl` (MXFP4 brut, 209,4 Go/s) | une douzaine de noyaux (liste ci-dessous) | logits contre llama.cpp (C4) puis contre le chemin brut au bit (C3) |
| `juge` | logits, KL, compteurs (disque par PDH, mémoire, VRAM), séries ABBA | `modeles-base.py`, `modeles-juge.sh` (06) | sortie des logits au format du juge | instrument contre lui-même : KL nulle ; contre un autre modèle : nette |
| `simulateur` | rejoue une trace de routage sur la politique du cache, donne h pour chaque M | `gptoss_localite.py` (autre agent), `chargement_localite.py` (04) | branchement sur la politique réelle (même code que `cache`) | égalité avec le moteur (ci-dessus) |

**Les noyaux de la passe avant** (décodage, lot de 1 ; la forme du calcul a été lue dans llama.cpp
b11515, MIT, en particulier `swiglu_oai` de `ggml/src/ggml-cpu/ops.cpp` pour la SwiGLU bornée, rien
copié) : ligne d'enchâssement Q8_0 ; RMSNorm ; GEMV Q8_0 (q, k, v, sortie de l'attention, routeur,
tête) avec biais ; RoPE YaRN ; ajout au cache KV ; attention de décodage avec puits, pleine ou à
fenêtre de 128 une couche sur deux ; routeur top-4 et softmax ; GEMV MXFP4 avec biais (existante) ;
SwiGLU bornée ; somme pondérée des experts et résidu ; norme finale, tête et argmax. Plus le
décodeur, existant. Soit douze noyaux neufs et deux existants.

### 4.3 Le format du fichier de tronçons

**Principe.** Un fichier par modèle, réécrit une fois depuis le GGUF d'origine. Un **tronçon** est un
expert entier (ses trois matrices et ses biais), d'un seul tenant, aligné sur 4 Kio : un défaut coûte
une lecture. À l'intérieur d'un tronçon, les flux sont **rangés par niveau de raffinement
croissant** ; tout préfixe qui s'arrête à la fin d'un niveau est décodable seul. A lit le tronçon
entier ; B lira un préfixe au défaut et le suffixe plus tard.

**Disposition** (entiers petit-boutistes ; « o » = octets) :

```
 fichier .trc
 ┌──────────────────────────────────────────────────────────────────────────────────────────┐
 │ en-tête fixe                              4 096 o                                        │
 │ métadonnées du GGUF d'origine (copie)     variable, alignée 4 Kio                        │
 │ tables rANS (par tenseur et par flux)     36 x 3 x 4 x 16 Kio = 7,1 Mo (120b)            │
 │ section résidente (A : Q8_0 et F32, copie) 1,686 Go (120b), alignée 4 Kio               │
 │ table d'enchâssement (Q8_0, copie)        0,615 Go                                       │
 │ répertoire des tronçons                   L x E x 128 o (0,59 Mo pour le 120b)           │
 │ tronçons, dans l'ordre (couche, expert)   L x E x 12,04 Mo (55,5 Go pour le 120b)        │
 └──────────────────────────────────────────────────────────────────────────────────────────┘
```

**En-tête fixe (4 096 o)**

| Champ | Taille | Contenu |
|---|---|---|
| magie | 8 o | `TRONCONS` |
| version du format | 2 o | 1 |
| drapeaux | 2 o | bit 0 : tronçons alignés 4 Kio ; autres à 0 |
| alignement | 4 o | 4 096 |
| empreinte du GGUF source | 32 o | SHA-256 (déjà vérifiée au téléchargement) |
| couches L, experts E, actifs k | 3 × 2 o | 36, 128, 4 (120b) |
| poids par matrice, matrices par expert | 4 o + 1 o | 8 294 400 ; 3 |
| décalage et longueur de chaque section | 6 × (8 + 8) o | |
| nombre de sortes de flux connues du codeur | 1 o | 4 en v1 |
| empreinte de l'en-tête | 8 o | xxh3-64 des octets qui précèdent |
| réservé | reste | zéros (vérifiés à la lecture) |

**Entrée du répertoire (128 o par tronçon)**

| Champ | Taille | Contenu |
|---|---|---|
| couche, expert | 2 + 2 o | |
| décalage du tronçon | 8 o | multiple de 4 096 |
| longueur lue | 4 o | multiple de 4 096 |
| nombre de niveaux | 1 o | 1 en v1 |
| fin de chaque niveau | 4 × 4 o | décalage, dans le tronçon, de la fin du niveau j (longueur d'un préfixe) |
| nombre de flux | 1 o | 12 en v1 |
| empreinte des octets décodés | 8 o | xxh3-64 de l'expert MXFP4 d'origine (codes, échelles, biais), pour le mode témoin |
| empreinte des octets codés | 8 o | xxh3-64 du tronçon sur le disque |
| réservé | reste | |

**Un tronçon (v1, 12 038 144 o pour un expert de gpt-oss, 13 253 760 o à l'origine)**

```
 ┌───────────────┬────────────────┬─────────────────────┬──── niveau 0 (exact en v1) ───────────────────────┐
 │ en-tête 256 o │ biais f32      │ médianes de ligne   │ par matrice (gate, up, down) :                     │
 │ table des flux│ 3 x 11 520 o   │ 3 x 2 880 o (en     │  flux δ des échelles │ codes classe < │ = │ >     │
 │ (sorte, niveau│                │ clair, 1 o/ligne)   │  (rANS v4)           │ (rANS v4, une table par    │
 │ décalage,     │                │                     │                      │  tenseur et par classe)    │
 │ longueur,     │                │                     │                                                    │
 │ table)        │                │                     │                                                    │
 └───────────────┴────────────────┴─────────────────────┴────────────────────────────────────────────────────┘
   chaque flux = suite de tuiles v4 : 32 voies x 256 macro-pas (32 Kio produits), en-tête de tuile 32 états
   + 1 décalage (0,40 %) [mes. 03] ; fin du tronçon complétée de zéros jusqu'à 4 Kio
```

Sortes de flux de la v1 : 0 = brut MXFP4 (chemin de référence du témoin C3, jamais servi en
production), 1 = δ des échelles, 2 = codes d'une classe d'échelle. Sortes réservées pour B :
16 = base (signe et classe de magnitude), 17 = complément. **En v1, un seul niveau ; en B, la base et
les échelles passent au niveau 0, le complément au niveau 1.** Le lecteur, le cache et l'ordonnanceur
ne connaissent que « lire jusqu'à la fin du niveau j » ; seuls le codeur et le décodeur changent.

**Tailles** [calc., S7, S19] : tronçon de 12,04 Mo (codes et échelles à 3,8545 bits par poids
[mes. 03], plus biais, médianes et en-tête) ; fichier de **57,8 Go pour le 120b** (63,4 à
l'origine) et 11,2 Go pour le 20b (12,1).

**Pourquoi un tronçon par expert et non par matrice.** Le GGUF range déjà chaque matrice d'expert
d'un seul tenant (4,2 Mio [mes. 07]) : trois lectures de 4,2 Mio suffiraient. Une seule lecture de
12 Mio se ferait à 2,82 Go/s (16 Mio, QD 1, bruit 1 %) au lieu de 2,58 (4 Mio, QD 4, bruit 10 %)
[mes. 01] : +9 %, **sous le seuil de la règle de décision** (2 fois le plus grand bruit, soit 20 %).
Je ne revendique donc pas de gain de débit. Je choisis le tronçon par expert pour la simplicité : une
requête, une complétion, une empreinte, un emplacement de cache. Réponse par délégation du
2026-10-15, réversible.

**Pourquoi la v1 ne coupe pas encore base et complément (écart à 07 § 4.4).** L'étude 07 proposait
de ranger, dès A, chaque code en base et complément. Trois raisons de ne pas le faire en v1 :
1. **un coût de taux** : à l'ordre 0, base plus complément font 3,906 bits par poids contre 3,855 pour
   les trois classes, soit 1,3 % de taux et **1,7 à 1,9 % de plafond** [calc., S4]. C'est une borne :
   conditionner aussi base et complément sur la classe d'échelle rendrait, par la règle de la chaîne,
   presque tout le taux à trois classes, mais la v4 encaisse une part de son gain en décodant l'octet
   entier, ce qu'un complément code par code ne fait pas ; le vrai chiffre est entre les deux, et il
   n'est pas mesuré ;
2. **un noyau non mesuré sur le chemin critique** du premier livrable (§ 3.1, point 2) ;
3. **rien à gagner à l'avance** : le recodage coûte de l'ordre de 47 minutes, une fois (S16), et le
   conteneur à préfixes garde la place.
Le prix que je paie pour cela : B ne pourra pas commencer sur le fichier de la v1 ; il lui faudra le
recoder. Réponse par délégation du 2026-10-15, réversible.

### 4.4 Le budget de mémoire

**VRAM, poste par poste** (gpt-oss-120b) [calc., S18] :

| Poste | Go |
|---|---|
| Carte | 8,586 (8 188 Mio) |
| Occupé par l'affichage et les applications (relevé par l'autre agent, 10 h 15) | 0,953 |
| A, résident | 1,686 |
| Cache KV, 4 096 jetons, f16 | 0,156 |
| Tampons de décodage (4 couches × 4 tronçons codés) | 0,193 |
| Tables rANS | 0,007 |
| Activations (hypothèse dite, à mesurer) | 0,100 |
| **Cache d'experts décodés** | **5,49, soit 414 emplacements** |

Contre l'hypothèse de 6,5 Go de l'étude 06 (363 emplacements), le budget réel donne `h_v` de 0,590 à
0,607 et **+2,7 % de plafond** dans le scénario LRU calé (6,24 → 6,41). Petit, parce que l'élasticité
du plafond à `h_v` est faible tant que le disque limite ; je le donne pour qu'aucun chiffre ne repose
sur une hypothèse quand un relevé existe.

**RAM : la fenêtre de travail minimale** [calc., S12]. L'étude 07 compte, pour les tampons d'arrivée,
deux jetons entiers de défauts (`2 h_s R / r`). Un ordonnancement couche par couche n'a besoin que de
`d` couches d'avance, chacune d'au plus k tronçons tous en défaut, où `d` suit la règle du double
tampon (04 § 5.1) : `d ≥ ⌈latence / temps d'une couche⌉`, plus une couche en DMA et une en décodage.
Avec la latence médiane d'une lecture de 16 Mio (5,6 ms [mes. 01]) et le temps d'une couche au
plafond (4,5 à 17 ms selon le scénario), il faut 3 à 5 couches de tampons, soit 0,14 à 0,24 Go.

| | RAM de pointe, étude 07 | RAM de pointe, fenêtre minimale | avec la table d'enchâssement en RAM |
|---|---|---|---|
| A0, LRU calé | 1,92 | **0,64** | 1,26 |
| A0, uniforme | 3,69 | 0,64 | 1,26 |
| A, M = 11 Go, LRU calé | 12,31 | 11,69 | 12,31 |

Le « + 0,5 Go » de processus est l'hypothèse de l'étude 07, gardée ; la table d'enchâssement (une
ligne de 3 Ko lue par jeton) peut aussi rester sur le disque, une lecture alignée par jeton, cachée
par la file. **La fenêtre ne dépend que de k, de la taille d'un expert et de la profondeur du
pipeline, jamais du nombre total d'experts** (annexe A.1).

**Le témoin qui en sort.** gpt-oss-20b et gpt-oss-120b ont la même taille d'expert (13 253 760 o),
le même k = 4 et la même table d'enchâssement (615 329 280 o) [mes. 07, inventaire] ; leurs
répertoires diffèrent de 0,49 Mo (4 608 contre 768 entrées). À M = 0, **leur RAM de pointe doit être
la même à 0,5 Mo et au bruit de mesure près**, pour un modèle 5,2 fois plus gros. Cassure : donner
1 Go de cache tiède à l'un des deux ; l'écart doit apparaître (≈ 1 Go).

**Le repli si la mémoire hôte visible de la carte est refusée** [calc., S6]. Si le cache tiède doit
vivre en mémoire paginable, chaque succès en RAM passe par une copie du processeur (7,5 Go/s sur
secteur, 1,25 sur batterie [mes. 01]) : 41 ms par jeton sur secteur (LRU calé), sous les 157 ms du
disque, donc sans effet ; **244 ms sur batterie, au-dessus du disque**, donc le régime batterie
tomberait de 6,2 à ≈ 4 jetons/s de plafond. L'import de mémoire hôte n'est pas nécessaire sur
secteur ; il l'est sur batterie.

### 4.5 Le budget de la carte

[calc., S5] Ce que la carte peut se permettre avant de prendre le maximum (cible = l'étage le plus lent
des deux autres) :

| | Débit minimal du décodeur | Ralentissement permis des noyaux de la passe avant | Part de la carte dans le plancher en série |
|---|---|---|---|
| Disque chiffré, uniforme | 3,8 Go/s | 25,8 fois | 9 % |
| Disque chiffré, LRU calé | **5,6 Go/s** (mesuré : 41,6) | **8,0 fois** | 14 % |
| Disque chiffré, Belady calé | 6,4 Go/s | 4,7 fois | 18 % |
| Disque non chiffré, LRU calé | 15,6 Go/s | 2,8 fois | 22 % |

Conséquence pour l'ordre de construction : **la v1 n'a pas besoin de noyaux rapides**, elle a besoin
de noyaux justes. Huit fois plus lents que la GEMV mesurée, ils ne changeraient pas le plafond sur le
disque chiffré ; ils coûteraient au plancher en série (14 % de carte), ce que la prédiction (v1.1)
recouvre. La vitesse des noyaux redevient un levier sur un disque non chiffré (marge 1,9 sur le
maximum) : c'est là, et seulement là, qu'elle se travaille.

### 4.6 L'ordre de construction

Chaque étape a son témoin (un cas dont la réponse est connue), sa cassure (le témoin forcé à faux doit
tomber) et son seuil, déclarés ici, avant. Chaque étape se commite quand elle tient.

| Étape | Livrable | Témoin | Cassure | Seuil déclaré |
|---|---|---|---|---|
| **0a** | essai : lecture sans tampon dans une mémoire hôte importée par Vulkan (`VK_EXT_external_memory_host` par l'interopérabilité wgpu-hal), puis DMA vers la VRAM | octets arrivés égaux à ceux du disque ; débit ≤ 15,754 Go/s | un octet faussé dans la source | DMA ≥ 11,0 Go/s, soit 12,2 [mes. 01] moins 10 % ; sinon repli paginable (§ 4.4) et le régime batterie se dit perdu |
| **0b** | essai : coût d'une lecture du routeur par la carte (une synchronisation par couche, 36 par jeton) | horodatages de la carte et du mur cohérents | synchronisation retirée → le résultat lu est faux | 36 synchronisations ≤ 10 % du temps disque d'un jeton (15,7 ms, LRU calé) ; au-dessus, l'ordonnanceur passe aux répartitions indirectes sur la carte |
| **1** | `format` et `codeur` ; fichier du 20b puis du 120b | chaque tronçon décodé par le processeur égale l'expert d'origine (100 %) ; taux à 0,1 % de 1,1037 et 1,1026 | une médiane de ligne faussée → inexact | 0 tronçon faux |
| **2** | `lecteur`, `transport`, `decodeur` : tous les experts du 20b, disque → VRAM décodés, sans modèle | empreinte de chaque tronçon décodé égale à celle du répertoire | un bit retourné dans une copie du fichier → détecté | 0 écart ; débit de bout en bout ≤ min des étages et ≥ 0,8 × 2,58 × 1,1037 = 2,28 Go/s d'experts servis |
| **3** | `passe_avant` sur le 20b, experts lus en sorte « brut » (chemin de référence) | KL contre llama.cpp dans l'écart entre deux configurations de llama.cpp (C4) | logits d'un autre modèle → KL nette | C4 |
| **4** | experts codés, `cache`, ordonnanceur à la demande, 20b à M = 0 | **logits identiques au bit à l'étape 3** (C3) ; succès du cache égaux au simulateur | un tronçon corrompu sur le disque → empreinte et logits faux | 0 bit différent sur 2 560 jetons |
| **5** | gpt-oss-120b, v1 à la demande ; ABBA contre la base | C3 refait sur le 120b ; compteur disque du système contre octets comptés (C8) | — | C5, C7, C8, C10 |
| **6** | v1.1 : prédiction (routeur de ℓ+1 sur le résidu de ℓ), SLRU | C3 tient toujours ; part des défauts prédits juste publiée | prédiction forcée au hasard → plus lent que v1 | C6 |
| **7** | A0 (M = 0) sur les deux modèles | témoin de la fenêtre (C7) | M = 1 Go sur l'un → écart ≈ 1 Go | C7 |
| **8** | régime batterie, mesuré et publié | — | — | publié, pas jugé (I5) |

Estimation honnête de l'effort, en ordre de grandeur et sans engagement : les étapes 0 à 2 réutilisent
presque tout (un à deux pas d'agent chacune) ; l'étape 3 est le long pôle (douze noyaux à écrire et à
amener dans l'écart de llama.cpp, plusieurs pas, avec le risque principal de l'attention à puits et
de la RoPE YaRN) ; l'étape 4 est le cœur de la contribution et sa preuve. Je ne donne pas de durée en
jours : aucun chiffre ne la fonde.

### 4.7 Les critères de réussite (déclarés le 2026-10-15, avant toute construction)

| Critère | Mesure | Seuil | D'où vient le seuil |
|---|---|---|---|
| C1 format exact | tronçons décodés par le processeur contre la source | 0 faux | sans perte par définition |
| C2 transport exact | empreinte xxh3 de chaque tronçon décodé, relu en mode témoin | 0 écart, et 100 % des corruptions injectées détectées | idem |
| **C3 moteur exact** | logits du chemin codé (cache, préchargement) contre le chemin brut du même moteur | **0 bit différent** sur 10 fenêtres de 256 jetons (le plan de KL de 06) | mêmes octets décodés, mêmes noyaux, même ordre de sommation : l'égalité au bit est attendue, pas tolérée |
| C4 moteur juste | KL moyenne et premier choix du chemin brut contre llama.cpp | sous l'écart G entre deux configurations justes de llama.cpp sur gpt-oss-20b (`--cpu-moe` contre `--fit`), mesuré à l'étape 3 avant notre moteur ; si G tombe dans le plancher de l'instrument, seuil 0,0055 (écart entre moteurs [mes. 06]) | 06 § 7.3 : un moteur juste se compare à l'écart entre moteurs justes |
| C5 vitesse de la v1 | jetons/s du 120b, ABBA | ≥ **0,8 ×** le plancher en série recalculé avec le h compté par le moteur et les débits de la même séance | 0,8 = 1 − 2 × 10 %, le bruit de la lecture de 4 Mio en QD 4 [mes. 01] ; la v1 n'a pas de prédiction, elle doit atteindre son plancher, pas son plafond |
| **C6 vitesse contre la base** | v1.1 contre la meilleure configuration mesurée de llama.cpp | au-dessus de plus de 2 fois le plus grand bruit et de 3 % | règle de décision de 06 § 7.5, telle quelle |
| C7 fenêtre bornée | RAM de pointe, A0, 120b contre 20b | écart ≤ 2 × le bruit de passe à passe de la RAM de pointe + 0,5 Mo ; et RAM de pointe du 120b ≤ 1,9 Go | annexe A.1 ; 1,9 Go est le chiffre publié par 07, que la fenêtre minimale doit battre |
| C8 octets lus | compteur du système (PDH) contre octets comptés par le moteur | écart ≤ charge de repos mesurée × durée + 100 Mo | résolution de l'instrument [mes. 06] |
| C9 rendement physique | mesuré ÷ plafond (h mesuré) | publié, pas jugé | 06 § 7.5 |
| C10 VRAM | pointe relevée | ≤ 8 188 − 909 Mio, aucune éviction du pilote | relevé de 10 h 15 |
| C11 sans perte | perplexité et tâches du juge de 06 | identiques au chiffre près à ceux du chemin brut | conséquence de C3 |

### 4.8 Les critères d'abandon

- **K1** : C3 ne tient pas et la cause n'est pas trouvée. Alors ni A ni B ne sont jugeables ; on
  s'arrête et on cherche, on ne passe pas à B.
- **K2** : C6 tombe sur le 120b avec la prédiction. A n'est pas une contribution de vitesse ; il reste
  la référence exacte de B, et l'effort passe à B ou à C. C'est le critère qui peut tuer mon camp.
- **K3** : l'étape 0a échoue (aucune mémoire hôte importable à ≥ 11 Go/s). A continue sur secteur par
  le repli paginable (sans effet sur le plafond, S6) ; le régime batterie se publie comme perdu.
- **K4** : l'étape 0b dépasse son seuil et les répartitions indirectes ne le ramènent pas sous lui.
  `t0` devient un étage ; le plafond se recalcule avec le `t0` mesuré, et C5 avec lui.

### 4.9 Les témoins, rassemblés

Format (C1), transport (C2), exactitude au bit (C3), justesse contre llama.cpp (C4), simulateur contre
cache réel à l'unité (étape 4), fenêtre bornée 20b contre 120b (C7), octets lus contre le compteur du
système (C8), débit de bout en bout sous le plus lent des étages (étape 2), synchronisation retirée
(0b), prédiction forcée au hasard (étape 6). Chacun a sa cassure dans le tableau du § 4.6.

---

## 5. Les chiffres de ce plaidoyer, et leurs témoins

`partisan_a.py` refait quatre chiffres publiés par l'étude 07 (seuil déclaré : 1 % sur chaque valeur) :

| Témoin | Attendu | Obtenu | Tient | Avec `--casser` (taux sans perte remis à 1) |
|---|---|---|---|---|
| A, LRU calé | 6,24 | 6,241 | oui | 5,424 : **tombe** |
| A0, LRU calé | 3,59 | 3,592 | oui | 3,262 : **tombe** |
| A, uniforme | 2,05 | 2,048 | oui | 1,813 : **tombe** |
| B1, LRU calé | 8,88 | 8,879 | oui | 8,879 : tient (B1 ne dépend pas du taux de A) |

La cassure fait tomber exactement les témoins qui dépendent du taux de A, et pas celui de B1
(`partisan-a-casse.json`).

---

## 6. Ce qui dépend de la mesure en cours (`mesures/gpt-oss.md`)

Non commitée à l'heure où j'écris. Ce qu'elle décidera, point par point :

| Si elle donne… | Alors, pour A | Pour ce plaidoyer |
|---|---|---|
| h(c) proche du scénario LRU ou meilleur | A à 6 à 10 jetons/s de plafond, 4 à 6 en série | inchangé |
| h(c) proche de l'uniforme | A à 2,05 (1,47 en série) | la thèse tient (A reste 3 à 4 fois au-dessus de l'exploration) ; B devient plus risqué (72 % d'usages par la base) |
| une base llama.cpp en ABBA bien au-dessus de 0,49 | le rapport A / base baisse d'autant | K2 se rapproche ; si la base dépasse le plancher en série de A au h mesuré, K2 est probable |
| ρ grand (α > 1 − ρ atteignable) | la spéculation entre dans A comme dans B (hors v1) | aucune différence entre A et B |
| des écarts de localité entre genres de texte | le cache doit s'adapter (SLRU, filtre d'admission) | étape 6 renforcée |
| les octets lus par llama.cpp sur le 120b | second chemin pour C8 | instrument mieux calé |

Ce qui n'en dépend pas : le § 1 (plancher et juge), le rapport A / B1 sur disque chiffré (0,70, il ne
dépend que des bits), f* = 0,958, la fenêtre minimale, le budget de VRAM et le format.

---

## 7. Réponses par délégation

Chacune : « réponse par délégation du 2026-10-15, réversible », avec sa raison en une ligne.

1. **A d'abord, B ensuite, qualité de B en parallèle hors du moteur.** Raison : A est le plancher et le
   juge de B, et sa construction ne retarde pas la question de qualité de B (§ 3.4).
2. **Route 1, moteur à nous (Rust, wgpu, Vulkan).** Raison : l'ordonnancement couche par couche est le
   cœur de la contribution, et nos briques les plus chères existent et sont mesurées (07 § 4.1).
3. **Un tronçon par expert, flux rangés par niveau, préfixe décodable.** Raison : une requête par
   défaut, et la place de B gardée sans rien coûter à A (§ 4.3).
4. **La v1 code les experts à trois classes (r = 1,1026), sans couper base et complément.** Raison :
   pas de noyau non mesuré sur le chemin critique du premier livrable, un recodage ne coûte que de
   l'ordre de 47 minutes (§ 4.3).
5. **Découpage en jetons par `llama.dll` (MIT), en dépendance.** Raison : ce n'est pas le levier, et
   l'écrire nous-mêmes ajouterait une source d'écart contre la base.
6. **Cache LRU global en v1, SLRU en v1.1.** Raison : le plus simple à témoigner contre le simulateur ;
   le gain du SLRU (+8 à 15 points [litt. 04, communautaire]) se mesure ensuite contre lui.
7. **Le 20b se développe à M = 0.** Raison : avec 4 Go de cache tiède il ne lit presque plus le disque
   (h_s = 0,012, S8) et n'exercerait pas le chemin qu'on construit.
8. **Contexte de 4 096 jetons en v1.** Raison : à 131 072 jetons le cache KV prendrait 4,8 Go sur les
   5,5 du cache d'experts (S10).

---

## 8. Ce qui pourrait être faux

- **Tous les plafonds dépendent du modèle de succès `h(c) = c^β`**, calé sur un seul point publié
  (Qwen3-30B-A3B) ; la mesure en cours peut tout décaler d'un facteur 5 (07 § 6). Ce qui n'en dépend
  pas est listé au § 6.
- **La base de comparaison est une exploration** (une passe, pas d'ABBA, non retenue par l'agent qui
  l'a faite). Les rapports « ×3 à ×21 » du § 2.3 sont des ordres de grandeur.
- **f* = 0,958 suppose que le disque tient le maximum** et ignore le trafic des compléments admis au
  cache sur le temps libre du disque. Si ce trafic n'est pas libre, B1 est plus près de A que je ne le
  dis ; si la PCIe limite (disque non chiffré), f* change.
- **La qualité de B est estimée par la linéarité de HIGGS**, valable pour de petites erreurs ; 4,29 %
  par expert n'est pas petit. Le § 2.3 peut donc sous-estimer ou surestimer le risque de B.
- **Le témoin C3 (égalité au bit) suppose que le chemin brut et le chemin codé exécutent les mêmes
  noyaux dans le même ordre.** Si l'ordonnancement change l'ordre des sommes (par exemple la somme
  pondérée des experts selon l'ordre d'arrivée des défauts), l'égalité tombera sans erreur réelle.
  Parade, déclarée : la somme des experts se fait toujours dans l'ordre de l'indice de routage, jamais
  dans l'ordre d'arrivée.
- **L'import de mémoire hôte par wgpu-hal** n'a pas été essayé : wgpu ne l'expose pas, et ouvrir
  l'extension à la création du périphérique peut demander une interopérabilité plus profonde que
  prévu. Le repli est chiffré (S6), pas son coût d'ingénierie.
- **La fenêtre minimale suppose que la latence d'une lecture reste à sa médiane** (5,6 ms) ; la queue
  de distribution (machine partagée) peut demander une couche de plus (+48 Mo).
- **Les 909 Mio occupés par l'affichage et les applications** sont un relevé d'un instant ; ils varient.
- **Le tronçon de 12,04 Mo** est calculé avec le taux moyen ; par tenseur, le taux va de 1,0987 à
  1,1177 [mes. 03] : les tronçons auront des longueurs différentes, ce que le répertoire porte.
- **Le préremplissage par boucle de décodage** rendra le premier jeton lent ; si l'arbitre juge aussi
  le temps du premier jeton, la v1 perd sur ce critère.
- **Je n'ai pas lu le plaidoyer de B.** Des arguments qu'il avance peuvent n'avoir ici aucune réponse ;
  c'est le prix de l'indépendance, et c'est à l'arbitre de croiser.

---

## 9. Recettes (essayées dans ce plaidoyer, avec leur raison)

| Recette | Marche ? | Raison |
|---|---|---|
| Importer `plafonds.py` de l'étude 07 tel quel plutôt que recopier l'équation | oui | les quatre témoins redonnent 07 à 0,1 % ; un seul code pour l'équation |
| Cassure par le taux de A remis à 1 | oui | elle fait tomber les trois témoins de A et laisse tenir celui de B1 : le témoin discrimine |
| Marge de 1,5 sur le disque pour le budget de la carte | **échec, retirée** | posée au jugé par un premier jet, sans grandeur mesurée ; remplacée par « sous le plus lent des deux autres étages » |
| RAM de pointe du jumeau 20b avec M entier | **faux, corrigé** | `plafonds.py` compte M même quand le cache tiède n'a plus rien à garder ; borné à ce qu'il peut contenir |
| Point d'égalité B1 = A par dichotomie | oui | 60 pas ; il redonne la forme close de l'annexe A.2 (0,958) |
| Fenêtre minimale par la règle du double tampon de 04 | oui | 3 à 5 couches de tampons ; trois fois moins que les deux jetons entiers de 07 |
| Budget de VRAM poste par poste plutôt que l'hypothèse de 6,5 Go | oui | +0,7 Go d'emplacements, +2,7 % de plafond : petit, mais fondé sur un relevé |
| Juger le tronçon par expert par la règle de décision de 06 | oui | +9 % sous le seuil de 20 % : pas de gain revendiqué |

---

## 10. Outils, journaux, sources

- `outils/decisions/partisan_a.py` → `decisions/journaux/partisan-a/partisan-a.json`,
  `partisan-a-casse.json` ; CSV : `csv/sacrifice-a-contre-b.csv`, `csv/b1-contre-part-exacte.csv`,
  `csv/a-contre-hs.csv`.
- Commande, depuis la racine du dépôt :
  `python -I -X utf8 outils/decisions/partisan_a.py [--casser] > decisions/journaux/partisan-a/<journal>.json`.
- Sources : les études 01 à 07 du dépôt et leurs journaux (cités par section) ;
  `mesures/REPRISE-gpt-oss.md` pour l'exploration de la base et l'occupation de la carte ;
  llama.cpp b11515 (MIT, licence vérifiée par l'étude 06), lu dans
  `~/dev/lectures/troncons/gpt-oss/llama.cpp-b11515` le 2026-10-15, rien copié.
  Aucune source extérieure nouvelle : pas de fichier BibTeX propre à ce plaidoyer, les références
  sont celles de `memoire/sources/`.

---

## Annexe A. Les dérivations

**A.1 La fenêtre de travail bornée.**
*Proposition.* Soit un MoE de L couches à E experts dont k sont actifs par couche, chaque expert
codé tenant en au plus `ê` octets, servi par un ordonnancement couche par couche de profondeur d. Si
le cache tiède en RAM est borné par M, la RAM de pointe des poids d'experts vérifie
`RAM ≤ M + d · k · ê + c_rép · L · E`, où `c_rép` est la taille d'une entrée du répertoire.
*Démonstration.* Un expert n'entre en RAM que par une lecture lancée pour l'une des d couches en vol ;
chacune en lance au plus k ; une lecture dont la couche est servie libère son tampon ou entre dans le
cache tiède, borné par M. Le répertoire est la seule structure indexée par tous les experts. ∎
*Application.* gpt-oss-120b, LRU calé, M = 0 : d = 3 (S12), k = 4, ê = 12,04 Mo :
`3 × 4 × 12,04 = 144 Mo` ; `c_rép · L · E = 128 × 4 608 = 0,59 Mo`. gpt-oss-20b : mêmes d, k et ê,
`128 × 768 = 0,10 Mo`. L'écart attendu entre les deux est 0,49 Mo, pour des experts totaux de 61,1
contre 10,2 Go. Le terme `c_rép · L · E` est le seul qui croît avec le modèle : 128 o par expert,
soit 1 Mo pour un modèle de 8 000 experts.

**A.2 Le point d'égalité de B1 et de A.** Tant que le disque tient le maximum,
`jetons/s ≈ D_disque / (h_s · R · b_lus / 4,25)` où `b_lus` est le nombre de bits lus par poids au
défaut. B1 lit `b_base + f · b_compl`, A lit `b_A`. Ils sont égaux pour
`f* = (b_A − b_base) / b_compl = (3,8545 − 2,6839) / 1,2219 = 0,958`,
indépendamment de `h_s`, donc du scénario : c'est pourquoi la dichotomie de S13 rend la même valeur
dans les trois. ~~B1 bat A tant que plus de `1 − f* = 4,2 %` des défauts sont servis par la base.~~
Barré par l'arbitre le 2026-10-15 : ce calcul omet la lecture du complément de tout défaut admis au
cache ; voir `decisions/ARCHITECTURE.md` § 1.7.

**A.3 Le gain de B1 à mi-chemin.** f = 0,5 : `b = 2,6839 + 0,6109 = 3,2948` ;
`3,8545 / 3,2948 = 1,170`, soit **+17 %** (S3, S13 : +16,3 à +16,8 % selon le scénario, l'écart venant
de `t0` et de la PCIe).

**A.4 La résolution de la mesure de B.** Écart entre deux moteurs justes : KL moyenne 0,005516
[mes. 06]. Plancher de l'instrument, même moteur contre ses propres logits : maximum 0,000068,
99,9e centile 0,000055, moyenne nulle [mes. 06]. `0,0055 / 0,000068 = 81`.

**A.5 Le seuil de vitesse de la v1.** Le plancher en série est `1 / (T_disque + T_pcie + T_carte + t0)`.
Le disque y pèse 62 % (157 sur 254 ms, LRU calé). Le bruit de passe à passe de la lecture de 4 Mio en
QD 4 est 10 % [mes. 01, `disque-analyse.md`] ; la règle de décision de 06 § 7.5 ne tient pour réelle
qu'une différence au-delà de 2 fois le plus grand bruit. D'où `C5 : mesuré ≥ (1 − 2 × 0,10) ×
plancher = 0,8 × plancher`, soit 3,15 jetons/s dans le scénario LRU calé, 1,18 à l'uniforme, 4,94
à Belady [calc., S17], à recalculer avec le h mesuré.

**A.6 Le budget du décodeur.** La carte ne prend pas le maximum tant que
`(1 − h_v) · R / D_dec + (A + R) / D_g ≤ max(T_disque, T_pcie)`. LRU calé, disque chiffré :
`(1 − 0,590) × 1,909 / D_dec + 3,595 / 209,4 ≤ 0,1567` donne `D_dec ≥ 0,7826 / 0,1395 = 5,6 Go/s`
[calc., S5].
