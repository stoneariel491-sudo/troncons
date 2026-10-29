# Éclaireur du domaine « Terre, climat et cosmos » : ce que le monde fait, ce qu'il donne à troncons, ce qui est mesuré

Rôle : éclaireur scientifique, domaine géologie, sédimentation, érosion, réseaux fluviaux, tectonique,
volcans, océans, atmosphère, astrophysique, structures cosmiques, lois de puissance et criticalité
auto-organisée. Écrit le 2026-10-26 et 2026-10-27. Consigne de Stone (2026-10-26) : mimétisme absolu, toute
échelle, et des mécanismes **mesurés sur nos données**, pas une liste d'analogies.

Étiquettes : **[mes.]** mesuré ici, outil et journal commités ; **[calc.]** calculé ici, pas à pas ;
**[litt.]** lu à la source (page ou résumé, dit pour chaque source au § 7) ; **[mém.]** de ma mémoire,
non relu ; **[hyp.]** hypothèse dite. Aucune analogie n'est présentée comme un résultat.

Contraintes tenues : le verrou de la carte existait (`dev/verrou-carte.txt`, séance du juge de placement) :
**aucun fichier de modèle n'a été lu**, tout ce qui est mesuré l'est sur les traces de routage commitées
(`mesures/localite-gpt-oss/traces-*`), 2 fils au plus. Les expériences qui demandent les poids ou l'état
caché sont décrites avec leur seuil pour après la levée du verrou. Seuils et témoins déclarés et commités
**avant** chaque lecture : `seuil-declare.md` (commits `841e914`, `527f05f`, `02ab31c`). Outils :
`outils/mimetisme/terre_cosmos/` ; journaux et JSON : `mesures/mimetisme/terre_cosmos/`.

---

## 0. En bref

1. **Deux résultats mesurés tiennent**, l'un attendu, l'autre neuf pour le projet :
   - **Une LFU à demi-vie 32 jetons retire 14 à 23 % des octets lus sur disque contre le LRU que le moteur
     exporte** (`trc-cache` n'exporte que `Lru` et `Belady`) ; la demi-vie 8 de nos simulations était trop
     courte (§ 3.1). Ce n'est pas une idée neuve dans son genre (le projet a déjà mesuré LFU > LRU), c'est
     une politique non construite et un réglage faux [mes.].
   - **Précision par expert selon l'usage (eau-filling)** : à distorsion pondérée par l'usage égale, donner
     moins de bits aux experts que le cache rate souvent gagne exactement la **demi-divergence de
     Kullback-Leibler entre la loi des défauts et la loi des accès** ; validé sur genre non vu : **0,22 bit par
     poids lu** (LFU, deux modèles), 8 % du fichier rapide (§ 3.2). Seuil déclaré tenu pour la LFU, **non
     tenu pour le LRU du 20b** (0,094 contre 0,126) : dit.
2. **Quatre mécanismes inspirés de la Terre tombent ou ne battent pas la LFU réglée** : le noyau d'Omori
   des séismes (+0,10 à +0,36 point contre +1,0 exigé), l'allocation hydraulique entre couches (−4,0 points ;
   et refaite avec une LFU elle redonne la LFU globale), la phase de marée de la couche (+0,4 à +0,6 point aux
   petits budgets du 20b, +0,12 et +0,04 sur le 120b, positive 4 genres sur 4, mais sous le seuil), la roulette russe de la neutronique (tuée par
   un calcul, § 4.8). **Un témoin a tué une analogie** : la queue en loi de puissance des écarts entre deux
   accès à un même expert, belle à lire comme une loi d'Omori, se retrouve à l'identique en ordre mélangé : c'est
   l'hétérogénéité des taux (un mélange d'exponentielles), pas une mémoire (§ 3.3).
3. **Ce que le domaine ne donne pas** : rien pour les poids eux-mêmes. Les trois propriétés mesurées par
   la ronde 1 (05 § 2.1 : bruit sachant l'échelle, colonnes géantes, erreur d'expert qui ne prédit pas la KL)
   ferment tout ce que la géologie, la sismique et la cosmologie offrent en compression (§ 5).
4. **Candidats non encore mesurés, à lancer après le verrou** : le substitut « climatologie » pour un expert
   absent (§ 4.4, neuf, gain probablement faible aux couches 0 à 16) ; la trajectoire grossière comme oracle
   de routage, à la parareal / COLA / alerte sismique (§ 4.5, déjà vu sous d'autres noms) ; le routage collant
   borné par la marge tropicale (§ 4.6).

---

## D'où on part, où on va

**Acquis au départ** (lu avant de commencer) : les poids sont du bruit sachant l'échelle de bloc et
quelques colonnes géantes portent la structure (05 § 2.1 a, b) ; la KL ne se prédit pas par l'erreur d'expert
(05 § 2.1 c) ; la garde tropicale tombe à 57,1 % pour 10 % (58,6 avec indices multiples) mais attrape
85,2 % des racines de cascade (pistes/tropicale) ; le cache est loin de Belady (`mesures/gpt-oss.md` § 6 :
120b, LRU 0,449 contre Belady 0,706 à 323 emplacements) ; le préchargement cache la latence mais ne retire
aucun octet (fondations/05 § 4) ; la spécification du moteur ne propose que `Lru` et `Belady`.

**Établi ici** : les politiques d'éviction à noyau, à phase ou à partition entre couches ne dépassent pas
une LFU à demi-vie 32 de plus de 0,6 point ; la LFU à demi-vie 32 dépasse le LRU de 1,7 à 9 points de succès
selon le budget ; une allocation de précision par expert guidée par l'usage a un gain en forme close mesuré
à 0,17 à 0,24 bit validé.

**Ce qui reste** : la KL de bout en bout du fichier rapide à débit variable (poids, après le verrou) ;
l'implémentation de la LFU dans `trc-cache` avec le témoin O1 ; les trois candidats de l'item 4 ci-dessus.

---

## 1. Ce que j'ai regardé dans le domaine, et ce qui en sort

Chaque ligne : le phénomène, la source lue, ce que le monde fait **réellement**, l'objet de troncons visé.

| Phénomène | Ce que le monde fait (source) | Objet visé | Sort |
|---|---|---|---|
| Séismes en grappes (Omori, ETAS) | Les répliques décroissent en (t + c)^(−p) ; l'intensité d'un processus ponctuel auto-excité somme ce noyau sur le passé (Ogata 1988 [litt., non ouvert]) | score d'éviction du cache d'experts | **tombe** (§ 3.3, § 4.7) |
| Climat stochastique | Un réservoir lent intègre le forçage rapide et donne un spectre rouge (Hasselmann 1976 [litt., non ouvert]) | mémoire du cache à deux échelles de temps | **gagne** sous forme de demi-vie longue (§ 3.1) |
| Criticalité auto-organisée | Un tas de sable atteint seul un état critique, avalanches en loi de puissance, bruit en 1/f (Bak, Tang, Wiesenfeld 1987 [litt., non ouvert]) | rafales de défauts, cascades de bascules | **sans levier** (§ 5) |
| Géométrie hydraulique | Largeur, profondeur, vitesse d'un cours d'eau sont des puissances du débit (Leopold et Maddock 1953 [litt., page éditeur]) | nombre d'emplacements de cache par couche | **tombe** (§ 3.4) |
| Marées | Une demande périodique se prédit par sa phase [mém.] | éviction qui connaît la couche courante | **gain faible** (§ 3.5) |
| Eaux et réservoirs, allocation | Partage d'une ressource par valeur marginale (Qureshi et Patt 2006 pour les caches [litt., non ouvert]) | partage des emplacements | **déjà fait par la LFU globale** (§ 3.4) |
| Structure à grande échelle, COLA | On résout les grandes échelles par la théorie des perturbations lagrangiennes et on ne simule que le résidu : 10 pas suffisent (Tassev, Zaldarriaga, Eisenstein 2013 [litt., résumé]) | mode rapide + correction exacte | **candidat** (§ 4.5) |
| Parareal | Un propagateur grossier séquentiel, un propagateur fin parallèle en temps, correction par la différence (Lions, Maday, Turinici 2001 [litt., secondaire]) | passe rapide sur toutes les couches puis lectures exactes groupées | **candidat** (§ 4.5) |
| Prévision météorologique : climatologie, analogues | La climatologie est la référence de compétence ; la méthode des analogues cherche dans le passé l'état le plus proche (Murphy 1988, Lorenz 1969 [litt., références]) | substitut d'un expert absent | **candidat** (§ 4.4) |
| Roulette russe (transport de particules) | Tuer les contributions de faible poids avec une probabilité et gonfler celles qui survivent : estimateur sans biais [mém.] | sauter le 4e expert sans biais | **tué par le calcul** (§ 4.8) |
| Friction à vitesse et état (Dieterich, Ruina) | Une faille « colle » : la mémoire de l'état retient le glissement [mém.] | routage collant | **déjà vu** (§ 4.6) |

---

## 2. Les données et les instruments

- Traces « lecture » de gpt-oss-20b (E = 32, k = 4, L = 24) et 120b (E = 128, k = 4, L = 36), quatre genres
  de 2 378 à 2 887 jetons (`mesures/localite-gpt-oss/traces-*`, extraites dans un dossier jetable). Cache
  global, un groupe d'accès = les k experts d'un (jeton, couche), dans l'ordre du calcul.
- Politiques de base importées **telles quelles** de `outils/gptoss_localite.py` (LRU, LFU, Belady).
- Protocole : **validation croisée par genre** (tout réglage sur trois genres, jugement sur le quatrième,
  cache vide au début du genre jugé). Budgets 10, 15, 20, 30 % du nombre d'experts.
- Témoins (`mesures/mimetisme/terre_cosmos/temoins.json`, `temoins-phase.json`, `temoins-eau.json`,
  `t2-melange-t20b.json`) : T1 les valeurs publiées sont redonnées (LRU, LFU 8, Belady : 0,6007, 0,6844,
  0,8141 contre 0,601, 0,684, 0,814, écart ≤ 0,0004) ; T4 second chemin en Python pur pour le noyau d'Omori :
  146 990 succès égaux sur 244 032, cassure p = 0 qui tombe (125 159) ; T5 allocation uniforme par le même
  code égale le LRU par couche (135 061) ; T6 la phase constante redonne la LFU exactement (écart 0,0000) et
  la phase à l'envers perd 1 à 3 points ; témoin i.i.d. de l'eau-filling 0,0001 bit.
- Un fait de méthode : la demi-vie 32 est au bord de la grille déclarée (2 à 32) ; une extension post hoc
  (8 à 1 024) place l'optimum à 32-64 (§ 3.1). Le noyau d'Omori à (p, c) = (0,5 ; 2) est aussi au bord de sa
  grille : un noyau encore plus plat gagnerait peut-être quelques centièmes de point ; il ne peut pas franchir
  1,0 (la LFU est l'autre bord).

---

## 3. Ce qui est mesuré

### 3.1 La mémoire lente : LFU à demi-vie longue contre le LRU du moteur [mes.]

Hasselmann pose qu'un système lent intègre un forçage rapide ; en cache, une LFU à compteurs décroissants
est un tel intégrateur, de constante de temps la demi-vie. La base mesurait 8 jetons. Succès moyen des quatre
genres (`lfu-demivie-*.json`, `mesure-*.json`) :

| Modèle, budget | LRU | LFU 8 | LFU 32 | LFU 64 | Belady | défauts LRU → LFU 32 |
|---|---|---|---|---|---|---|
| 120b, 10 % (461 emplacements) | 0,5631 | 0,6234 | **0,6391** | 0,6368 | 0,7779 | 0,437 → 0,361 (−17,4 %) |
| 120b, 20 % (922) | 0,7744 | 0,7922 | **0,8141** | 0,8147 | 0,8991 | 0,226 → 0,186 (−17,6 %) |
| 120b, 30 % (1 382) | 0,8809 | 0,8849 | **0,8979** | 0,9005 | 0,9487 | 0,119 → 0,102 (−14,3 %) |
| 20b, 15 % (115) | 0,5011 | 0,5908 | **0,5975** | 0,5949 | 0,7318 | 0,499 → 0,403 (−19,3 %) |
| 20b, 20 % (154) | 0,5986 | 0,6829 | **0,6909** | 0,6889 | 0,8129 | 0,401 → 0,309 (−23,0 %) |
| 20b, 30 % (230) | 0,7722 | 0,8160 | **0,8247** | 0,8228 | 0,9051 | 0,228 → 0,175 (−23,0 %) |

Le LRU du 20b à 10 % (77 emplacements) vaut 0 (le théorème du LRU partagé, gpt-oss.md § 7) ; la LFU 32 y
sert 0,4755. Les octets lus sont proportionnels aux défauts ; le plafond disque de jetons par seconde varie en
1/(1 − h) : sur le 120b, ×1,21 à 10 et 20 %, ×1,17 à 30 % ; sur le 20b ×1,30 à 20 % [calc.]. Le choix de la demi-vie
fait en validation croisée tombe sur 16 ou 32 dans tous les plis. Gain de la demi-vie 8 vers 32 : +0,8 point
(20b, 20 %) et +2,2 points (120b, 20 %).

**Ce que cela n'est pas.** (i) Pas une idée neuve : le projet a déjà mesuré LFU > LRU (gpt-oss.md § 6, 0,684
contre 0,601 et 0,794 contre 0,777). Ce qui est nouveau est le réglage de la demi-vie et le constat que le moteur
n'a que `Lru` et `Belady`. (ii) La LFU n'est pas une politique « à pile » : le modèle deux étages du simulateur
(`h_v = h(f_v)`, `h_r = h(f) − h(f_v)`) ne s'applique plus ; il faut mesurer les deux étages. (iii) Pas de
surcoût mesuré (mise à jour des compteurs, tas), ni de test d'invariance du déterminisme du moteur.

### 3.2 L'eau-filling par l'usage [mes. sur traces, calc., modèle à confirmer]

**Dérivation** [calc.]. Un expert x est lu m_x fois sur le disque parmi p_x accès, à R_x bits par poids ; la
qualité perdue est D = Σ p_x σ² 2^(−2 R_x) (théorie débit-distorsion à haute résolution d'une source gaussienne,
Cover et Thomas, chap. 10 [mém. pour la numérotation ; la forme « eau-filling inverse » est vérifiée sur la page du
cours de Berlin cité au § 7]). Minimiser Σ m_x R_x à D fixée (un multiplicateur) donne 2^(−2 R_x) ∝ m_x / p_x et,
contre un débit uniforme R₀ à même D, un gain en bits par poids lu

  Δ = ½ · KL(m̂ ‖ p̂),  m̂ = m / Σ m,  p̂ = p / Σ p,

la demi-divergence de Kullback-Leibler entre la loi des défauts et la loi des accès sur les experts (couche,
indice). Les experts que le cache sert presque toujours (m/p petit) reçoivent plus de bits, les autres moins.

**Mesure** (cache global à 20 %, forme de l'allocation lissée de Laplace (+1), bornée à [1 ; 8] bits,
réglée sur les trois autres genres, décalée d'un scalaire pour retrouver la même D sur le genre jugé, puis
Σ m'_x R_x contre R₀ Σ m'_x ; `eau-usage-*.json`) :

| Modèle, politique | Δ dans l'échantillon | Δ validé (genre non vu) | cassure (forme permutée entre experts) | seuil 0,126 |
|---|---|---|---|---|
| 20b, LRU | 0,171 | 0,094 | −0,078 | **non** |
| 20b, LFU 8 | 0,435 | 0,219 | −0,234 | oui |
| 20b, LFU 32 (post hoc) | 0,535 | 0,239 | −0,293 | oui |
| 120b, LRU | 0,397 | 0,137 | −0,169 | oui |
| 120b, LFU 8 | 0,485 | 0,165 | −0,212 | oui |
| 120b, LFU 32 (post hoc) | 0,695 | 0,224 | −0,308 | oui |

Lecture. Le seuil déclaré (4 cas sur 4, avant lecture) **n'est pas tenu en entier** : le LRU du 20b donne 0,094.
Il est tenu pour la LFU, la politique qu'on déploiera si § 3.1 est suivi. La cassure tombe franchement (une forme
permutée donne un gain négatif, −0,08 à −0,31 bit), le témoin i.i.d. donne 0,0001 bit. La cassure « Δ tombe à zéro en mélangeant »,
écrite dans l'addendum, était mal posée (une demi-KL est positive) : **barrée** ; la cassure retenue est la forme
permutée. 0,22 bit sur les 2,65 bits du fichier rapide font environ 8 % des octets lus aux défauts, du même ordre
que le lot A (0,126 bit). **Limite écrite d'avance et maintenue** : modèle quadratique ; l'erreur d'expert ne
prédit pas la KL (05 § 2.1 c) ; ce gain est une borne haute à confirmer par une KL de bout en bout sur un fichier
rapide à débit variable par expert.

### 3.3 Le témoin qui a tué l'analogie d'Omori [mes.]

L'hypothèse : la mémoire des accès suit une loi d'Omori. Mesure (`gaps-*.json`, 1,0 et 1,5 million d'écarts) :
la fonction de survie de l'écart entre deux accès à un même expert, en jetons, s'ajuste très bien en
log-log (pente −1,17, R² 0,994 pour le 20b ; −0,76, 0,984 pour le 120b) bien mieux qu'en exponentielle
(R² 0,899 ; 0,928). **Mais en ordre mélangé, où il n'y a plus aucune mémoire temporelle, la pente est −1,25
(R² 0,991) et −0,79 (0,978).** La queue vient de l'hétérogénéité des taux : un mélange d'exponentielles de
taux différents donne une loi de puissance (la popularité de gpt-oss est très inégale). La mémoire réelle est
courte : P(écart = 1) vaut 0,504 contre 0,394 au hasard (20b), 0,314 contre 0,200 (120b) ; médiane 1 contre 2
et 4 contre 5. C'est la même structure que celle décrite en gpt-oss.md § 6 (popularité puis récence). Conséquence
chiffrée au § 3.4 : un noyau en loi de puissance n'a rien de plus à lire que la LFU.

### 3.4 Ce qui tombe, avec ses chiffres [mes.]

Seuils déclarés avant la lecture : gain moyen apparié contre la meilleure LFU réglée sur les autres genres
≥ +1,0 point à 20 et 30 % sur les deux modèles, positif sur 3 genres sur 4 (1 point de succès retire 3,2 à
4,5 % des octets, l'échelle du lot A).

| Mécanisme | 20b, 20 % | 20b, 30 % | 120b, 20 % | 120b, 30 % | Verdict |
|---|---|---|---|---|---|
| **M-B** noyau d'Omori (p, c) = (0,5 ; 2) choisi dans la grille | +0,10 (3/4) | +0,17 (4/4) | +0,20 (4/4) | +0,36 (3/4) | **tombe** (sous 1,0) |
| **M-A** allocation par utilité marginale, LRU par couche, contre le meilleur de LRU, LFU, LRU par couche uniforme | −4,03 (0/4) | −4,07 (0/4) | −4,12 (0/4) | −2,23 (0/4) | **tombe** |

- **T2 (ordre mélangé) de M-B** : l'avance disparaît, mais le test n'est pas dans la bande déclarée (±0,5) :
  l'écart devient −1,24 (code) et −0,88 (prose-en) au lieu de +0,26 et +0,09. Le noyau paie la récence qu'il
  ne trouve plus. Le témoin voit bien la mémoire (il a bougé de 1,3 à 1,5 point), mais sa condition écrite n'est
  pas tenue : dit.
- **M-A** bat nettement son propre cadre : contre le LRU par couche uniforme, +2,4 à +5,8 points (20b),
  +0,3 à +1,6 (120b) ; contre le LRU global, +5,1 à +5,8 points (20b, 15 et 20 %), +1,2 (20b, 30 %), de +1,5 à −0,5 (120b). Il tombe parce que le meilleur adversaire est la LFU
  globale. **Post hoc** (hors seuil, `alloc-lfu-t20b.json`), M-A avec une LFU 32 par couche : 0,5860 / 0,6915 / 0,8231
  à 15 / 20 / 30 % contre 0,5975 / 0,6909 / 0,8247 pour la LFU globale (0 à 1 genre sur 4 au-dessus) et
  0,6680 pour la LFU par couche uniforme à 20 % : **la LFU globale fait déjà seule l'allocation par utilité
  marginale**. Une loi de géométrie hydraulique pour le nombre d'emplacements par couche n'a donc rien à
  ajouter ; piste fermée par ce chiffre.

### 3.5 La phase de marée : M-C [mes.]

Éviction par temps estimé jusqu'à la prochaine utilisation, τ_x = φ_x + L (1/q̂_x − 1), où φ_x est la distance en
groupes, dans le cycle d'un jeton, de la couche de x à la couche courante (déclarée dans l'addendum du
2026-10-27 avant exécution). 20b (`mesure-phase-t20b.json`) :

| Budget | LFU réglée | M-C | gain (point) | genres positifs | phase à l'envers (cassure) | phase constante |
|---|---|---|---|---|---|---|
| 10 % | 0,4749 | 0,4795 | +0,46 | 4/4 | 0,4475 | 0,4734 |
| 15 % | 0,5969 | 0,6027 | +0,58 | 4/4 | 0,5847 | 0,5971 |
| 20 % | 0,6900 | 0,6941 | +0,42 | 4/4 | 0,6823 | 0,6894 |
| 30 % | 0,8247 | 0,8253 | +0,06 | 3/4 | 0,8205 | 0,8230 |

Le gain est réel (signe constant, la phase à l'envers perd 0,5 à 3,2 points, la phase constante redonne la LFU), il
persiste en ordre mélangé (+0,42 et +0,34 point : c'est un effet de structure du cycle des couches, pas de
mémoire), mais il est **sous le seuil de 1,0 point** ; la prédiction écrite (+1 à +5 aux petits budgets) était
trop haute : ~~+1 à +5~~ mesuré +0,46 à +0,58. Le résultat du 120b (+0,12 et +0,04 point) : § 3.6. Cousin publié : SpecMD (Apple, 2026)
introduit une éviction « Least-Stale » qui connaît la position de la couche et mesure des « collisions » du LRU ;
leur gain est donné en collisions, pas en succès total [litt.].

### 3.6 M-C sur le 120b (version réduite, écart au protocole dit)

La passe complète du 120b (15 simulations par cas, 150 s par cas) a été arrêtée après 3 cas sur 16 (`runC120b.log`).
Remplacée par une passe réduite, **écart au protocole** : budgets 20 et 30 % seulement (ceux du seuil), demi-vies 16
et 32 seulement (les deux que le 20b a choisies), choix toujours fait sur les trois autres genres
(`phase-120b-reduit.json`, `phase_120b_reduit.py`). Gain de M-C contre la LFU réglée : **+0,12 point à 20 %
(4 genres sur 4) et +0,04 point à 30 % (4 sur 4)**. M-C **tombe** au seuil déclaré sur les deux modèles (+1,0
exigé) ; son gain est réel mais de l'ordre du centième de point sur le 120b, et d'un demi-point sur le 20b aux
petits budgets.

---

## 4. Les candidats, classés

Séparation demandée : **les rares idées neuves pour ce projet** (4.1 à 4.4), puis **les déjà-vues** (4.5 à 4.8).

### 4.1 [neuve pour le projet, mesurée] Précision par expert selon l'usage (eau-filling)

- **Ce que le monde fait** : la répartition de l'eau dans un réseau de réservoirs par valeur marginale ; la
  version mathématique est l'eau-filling inverse de la théorie débit-distorsion (Cover et Thomas [mém.]) avec un
  coût par bit différent par composante (ici le nombre de lectures disque).
- **Problème visé** : octets du fichier rapide lus aux défauts de cache.
- **Traduction** : un fichier rapide `.rapide.trc` dont le pas de quantification δ varie par expert,
  2^(−2R_x) ∝ m_x / p_x, avec p_x et m_x relevés par la politique de cache (comptes décroissants sur les routages).
- **Expérience qui la jugerait** (après le verrou) : mêmes 32 experts sur 768 du protocole P1, fichier rapide
  uniforme contre fichier à débit variable, **à octets lus aux défauts égaux** ; KL appariée sur les fenêtres
  neuves (règle du lot R : meilleure si d̄ + 2σ < 0) ; seuil : pas de perte de KL et ≥ 5 % d'octets en moins.
  Témoin : allocation permutée entre experts (doit perdre) ; allocation uniforme (doit redonner la base).
- **Données existantes** : traces de routage (p, m) ; Hessien de calibration de la mutation synonyme ; moteur
  de KL du juge. Mesuré sur traces seules : § 3.2.
- **Gain attendu, honnête** : Δ validé 0,16 à 0,24 bit par poids lu, soit 6 à 9 % des 2,65 bits ; avec la
  réserve de la KL, **probablement la moitié** en pratique [hyp.].
- **Déjà fermé** : les partitions par κ ou par e et l'élagage par activité (05 § 2.3) allouent par échelle ou
  par colonne ; aucun n'a alloué par **usage de l'expert**.

### 4.2 [déjà vue dans son genre, mesurée, la plus rentable] LFU à demi-vie longue dans `trc-cache`

- **Source** : Hasselmann 1976 (échelles de temps) [litt., non ouvert] ; LRFU (Lee et al., IEEE Trans. Comput. 2001)
  décrit déjà le continuum LRU-LFU par une fonction de poids [litt., résumé].
- **Traduction** : une politique `Lfu { demi_vie }` à compteurs décroissants dans `moteur/crates/trc-cache/src/politiques`,
  à côté de `Lru` et `Belady`.
- **Expérience** : `rejouer` sur les traces avec la nouvelle politique ; témoin O1 (compte du moteur = compte
  du simulateur à l'unité) ; puis mesure des deux étages sans le modèle à pile ; ABBA sur la machine.
- **Gain** : § 3.1, défauts −14 à −23 %, +17 à +30 % de plafond disque à cache égal ; sur la machine, moins
  (recouvrement, étage RAM) [hyp.].
- **Déjà fermé** : le LRU partagé (théorème gpt-oss.md § 7) ; LFU de demi-vie 8 (réglage faux).

### 4.3 [neuve, petit gain] Phase de couche à l'éviction (marée)

Voir § 3.5. À prendre en même temps que 4.2 : la phase se code en dix lignes et ajoute +0,4 à +0,6 point aux
budgets de 10 à 20 % sur le 20b et +0,1 sur le 120b. Cousin publié : SpecMD [litt.]. **Ne pas la poursuivre seule.**

### 4.4 [neuve, non mesurée] La climatologie : substitut moyen pour un expert absent

- **Ce que le monde fait** : en prévision, la climatologie (la moyenne à long terme) est la référence de
  compétence : une prévision qui ne bat pas la moyenne n'apporte rien ; le score de compétence quadratique
  se décompose en corrélation et biais (Murphy 1988 [litt., résumé]). Le krigeage est le meilleur prédicteur linéaire
  sans biais d'une valeur non observée d'après ses voisines [mém.].
- **Problème visé** : l'expert manquant. Le projet a mesuré que substituer un autre expert n'est « jamais meilleur
  que retirer l'expert » (05 § 3.2) ; la barre était le retrait, c'est-à-dire prévoir **zéro**. La moyenne est une
  meilleure « prévision » que zéro dès que la sortie de l'expert a une moyenne non nulle.
- **Traduction** : un vecteur μ_{couche, expert} (2 880 flottants, 5,6 Kio) par expert, toujours en VRAM
  (768 vecteurs, environ 4,3 Mo pour le 20b), servi quand l'expert n'est ni en cache ni lu ; variante : régression
  du μ sur la sortie d'un expert présent (krigeage à un voisin).
- **Expérience** (après le verrou, processeur, 2 fils) : sur les entrées réelles déjà capturées, par couche,
  fraction d'énergie de sortie portée par la moyenne, ‖μ‖² / E‖y‖² ; puis erreur de sortie de couche
  « μ contre retrait » aux couches 0, 8, 16, 23 ; puis KL. Seuil à déclarer avant : au moins 25 % d'erreur de
  sortie de couche en moins que le retrait (13,3 / 9,2 / 7,6 / 3,7 %).
- **Données existantes** : entrées capturées pour la calibration du Hessien ; sorties d'experts f64 du lot duplication.
- **Gain attendu, honnête** : **faible aux couches 0 à 16** [hyp.] : la mesure existante des biais seuls
  (duplication § 4) donne des erreurs voisines de 100 % hors de la couche 23 ; un μ conditionné aux entrées
  ferait mieux, mais ce n'est pas mesuré. Plafond : le retrait coûte déjà peu aux couches profondes.
- **Déjà fermé** : le substitut par paralogue (05 § 3.2). Pas de moyenne.

### 4.5 [déjà vue sous d'autres noms] Trajectoire grossière : COLA, parareal, onde P

- **Ce que le monde fait** : COLA résout les grandes échelles par la théorie des perturbations lagrangiennes
  et ne simule que le résidu, 10 pas au lieu de 30 ou plus (Tassev et al. 2013 [litt., résumé]) ; parareal lance un
  propagateur grossier séquentiel puis un propagateur fin sur toutes les tranches de temps en parallèle, et corrige
  par U^{k+1}_{n+1} = G(U^{k+1}_n) + F(U^k_n) − G(U^k_n) [mém. pour la formule ; la terminaison finie après N sweeps
  est connue mais je ne l'ai pas retrouvée dans les sources lues : non vérifiée] ; une alerte sismique utilise
  l'onde P, rapide et faible, pour annoncer l'onde S destructrice.
- **Problème visé** : routage exact et lectures exactes ; le mode rapide est le propagateur grossier, la profondeur
  est le temps.
- **Traduction** : (1) passe rapide sur les 36 couches (fichier rapide en RAM pour le 20b seulement : 6,3 Go) →
  routage grossier de **toutes** les couches ; (2) lectures exactes triées par adresse disque et envoyées en une
  file profonde ; (3) passe exacte qui consomme ; seuls les ratés de prédiction font une lecture à la demande.
- **Expérience** : journal de routage du mode rapide contre l'exact (outil `juge reference --routage`, 5 110
  positions, déjà écrit pour l'exact) : accord des ensembles par couche, α_route. Seuil à déclarer : ≥ 90 % des
  cellules identiques aux couches 4 à 23 pour que la file profonde vaille ses lectures perdues.
- **Gain attendu** : **aucun octet retiré** (un préchargement cache la latence : fondations/05 § 4) ; le
  gain est le passage de lectures en profondeur 1 à une file profonde triée, dont l'étage disque est sensible
  (juge du placement). Edge0 (2026) mesure que les prédictions du même jeton tombent sous un LRU simple
  [litt., fondations/04 § 3.4] : **faible probabilité**.
- **Déjà fermé** : Pre-gated, ProMoE, HOBBIT, SP-MoE (fondations/04 § 3.4) ; recherche en profondeur « layer
  parallelism » sans prédicteur grossier (arXiv 2502.02790) : rien qui combine parareal et décodage spéculatif
  [litt., résumé du moteur de recherche].

### 4.6 [déjà vue] Routage collant borné par la marge (friction à état)

- **Source** : Skliar et al., *Mixture of Cache-Conditional Experts*, TMLR 2025, routage qui favorise les experts
  présents [litt., résumé]. Cousin : ReMoE (ICML 2026) [litt., aperçu].
- **Apport éventuel de la géométrie** : n'échanger le 4e contre le 5e que si la marge m < τ ; la perte de logit
  est bornée par m [calc.]. Bornes sur le coût de qualité, pas de gain d'octets nouveau.
- **Expérience** : il faut l'identité du 5e expert, que les journaux n'ont pas (marge seule) : relance du juge avec
  `--routage` étendu, après le verrou. Seuil : défauts de cache en moins à KL égale, appariée.
- **Gain attendu** : celui de Skliar (défauts 28 → 7 % sur DeepSeek-V2 [litt.]) restreint à la bande de marge
  étroite, donc **bien plus petit** ; ordre de quelques points de défauts [hyp.]. Change le texte (non exact).

### 4.7 [déjà vue, tombée] Noyau d'Omori et processus auto-excités

LRFU, Hyperbolic Caching (Blankstein, Sen, Freedman, USENIX ATC 2017) et un cache à processus de Hawkes pour la vidéo
(arXiv 2102.00646) occupent déjà ce terrain [litt., résumés]. Mesuré ici : § 3.3 et § 3.4. **Fermé.**

### 4.8 [tuée par le calcul] Roulette russe sur le 4e expert

Sauter le 4e expert avec probabilité 1 − π et gonfler son poids de 1/π donne un estimateur sans biais. Mais avec
X = w₄ f₄ la contribution du 4e expert, l'erreur quadratique vaut X² (1 − π)/π, pour (1 − π) de ses octets
économisés, soit 1/π fois plus d'erreur par octet économisé que de le retirer d'office (π = 0, erreur X²). La KL est
du second ordre en l'erreur : le biais et le bruit coûtent pareil. **Aucun gain**, quelle que soit π [calc.].

---

## 5. Ce que le domaine ne donne pas (pour ne pas le rouvrir)

- **Compression des poids.** Sismique et climat ont de beaux compresseurs à borne d'erreur (SZ, ZFP, MGARD) qui
  tiennent à la **régularité** du champ ; les poids sont du bruit sachant l'échelle (05 § 2.1 a). Fermé.
- **Cosmologie (champ gaussien, pics de BBKS, spectre de puissance)** : la graine, le générateur et le champ gaussien
  sont fermés par (a) ; les colonnes géantes sont déjà le contexte de colonne. Fermé.
- **Lois d'échelle des réseaux fluviaux (Horton, Tokunaga)** : l'arbre de parenté des experts est fermé (duplication
  0,003 bit) ; les cascades de bascules (26,6 % contre 3,4 %, ×7,9) sont déjà caractérisées (pistes/tropicale).
- **Criticalité auto-organisée** : un nombre de défauts par jeton est borné par k = 4 par couche ; aucune
  rafale non bornée à dimensionner. Pas de levier.
- **Théorème de fluctuation-dissipation (Leith 1975)** : prédire une réponse à une perturbation par les
  fluctuations non perturbées est déjà le Hessien H = E[g² x xᵀ] de la mutation synonyme [mém.].
- **Codes de la gravité holographique** : la redondance coûte des octets, la contrainte est l'octet.

---

## 6. Ce qui pourrait être faux

- **La LFU 32 est réglée sur quatre genres courts** (2,4 à 2,9 mille jetons chacun) ; les traces sont des textes
  lus (lecture, pas génération), et la génération est plus locale (0,577 contre 0,503 de réutilisation sur le 20b) :
  le gain en génération peut différer. Le choix de demi-vie, fait par validation croisée, tombe sur 16 ou 32 dans tous
  les plis, mais la grille déclarée s'arrêtait à 32 ; l'extension 8 à 1 024 est post hoc.
- **Le simulateur compte des accès, pas des octets sur la machine** ; tous les experts d'une même taille (13,25 Mo)
  rendent succès en accès = succès en octets pour les experts du 120b, mais pas pour les couches à tailles
  différentes du fichier `.trc`.
- **L'eau-filling suppose D ∝ 2^(−2R) et un poids p_x** ; la ronde 1 a montré que cette famille de métriques
  intermédiaires a trompé le projet trois fois. Le gain est une borne haute à confirmer par la KL. La borne basse
  de R (1 bit) et la haute (8) sont mon choix, non mesuré.
- **Seuil de l'eau-filling non tenu pour le LRU du 20b** (0,094) : le verdict déclaré est donc « partiel », et c'est
  la LFU qui le fait passer.
- **M-C 120b en version réduite** (§ 3.6, écart dit). T2 de M-B hors de la bande déclarée (§ 3.4).
- **Sources.** Plusieurs sont lues par résumé (§ 7) ; les formules que j'ai écrites de mémoire (parareal, Omori,
  hydraulique) sont marquées [mém.] et ne sont pas utilisées dans les calculs : le seul noyau calculé est celui que
  j'ai défini moi-même (`cache_terre.py`).
- **Le SendMessage à la session principale** a annoncé deux pistes (eau-filling, LFU 32) avant la fin de ce rôle,
  avec leurs réserves ; les chiffres y sont ceux de ce document.

---

## 7. Sources (consultées les 2026-10-26 et 2026-10-27)

| Source | Adresse | Date | Lue |
|---|---|---|---|
| Tassev, Zaldarriaga, Eisenstein, *Solving Large Scale Structure in Ten Easy Steps with COLA*, JCAP 06 (2013) 036 | https://arxiv.org/abs/1301.0322 | v1 2013-01-02 | page de l'article, résumé |
| Leopold, Maddock, *The hydraulic geometry of stream channels and some physiographic implications*, USGS PP 252 | https://pubs.usgs.gov/publication/pp252 | 1953 | page éditeur, résumé |
| Hoang, Jaiswal, Samragh, Cho, *SpecMD: A Comprehensive Study On Speculative Expert Prefetching* (Apple) | https://arxiv.org/html/2602.03921v1 | 2026-02-03 | texte (présentation de Least-Stale) |
| Kim et al., *FlashMoE: Reducing SSD I/O Bottlenecks via ML-Based Cache Replacement for MoE Inference on Edge Devices* | https://arxiv.org/html/2601.17063v1 | 2026-01-22 | texte, résumé et méthode |
| Skliar et al., *Mixture of Cache-Conditional Experts for Efficient Mobile Device Inference*, TMLR 06/2025 | https://arxiv.org/abs/2412.00099 | v1 2024-11-27, v2 2025-06-24 | résumé |
| Hasselmann, *Stochastic climate models, Part I: Theory*, Tellus 28 (1976) 473-485 | https://web.lmd.jussieu.fr/~jyg/hasselmann-stochastic_climate_models_theory-tellus-1976.pdf | 1976 | **non ouvert** (échec de connexion) : résumés de moteur de recherche |
| Ogata, *Statistical models for earthquake occurrences and residual analysis for point processes*, JASA 83 (1988) | https://www.ism.ac.jp/~ogata/RM779/as_it_is/main_double.pdf | 1988 | **non lu** (PDF illisible) : descriptions de recherche |
| Bak, Tang, Wiesenfeld, *Self-organized criticality: an explanation of 1/f noise*, PRL 59 (1987) 381 | https://dx.doi.org/10.1103/PhysRevLett.59.381 | 1987-07-27 | résumé par moteur de recherche |
| Qureshi, Patt, *Utility-Based Cache Partitioning*, MICRO 39 (2006) 423-432 | https://utw10235.utweb.utexas.edu/pub/TR-HPS-2006-009.pdf | 2006 | résumés de recherche, **texte non lu** |
| Lee et al., *LRFU: a spectrum of policies that subsumes LRU and LFU*, IEEE Trans. Comput. 50(12), 1352-1361 | https://pure.uos.ac.kr/en/publications/lrfu-a-spectrum-of-policies-that-subsumes-the-least-recently-used/ | 2001-12 | résumé |
| Blankstein, Sen, Freedman, *Hyperbolic Caching*, USENIX ATC 2017 | https://www.usenix.org/conference/atc17/technical-sessions/presentation/blankstein | 2017-07 | résumé |
| Lions, Maday, Turinici, parareal (2001) ; Gander, Vandewalle, SISC 29(2) 556-578 (2007) | https://epubs.siam.org (DOI 10.1137/05064607X) ; synthèse https://en.wikipedia.org/wiki/Parareal | 2001, 2007 | **secondaires seulement** |
| Murphy, *Skill scores based on the mean square error…*, Mon. Wea. Rev. 116 (1988) 2417-2424 | https://glossary.ametsoc.org/wiki/skill/ | 1988 | glossaire et résumés |
| Lorenz, *Atmospheric predictability as revealed by naturally occurring analogues*, J. Atmos. Sci. 26 (1969) 636-646 | DOI 10.1175/1520-0469(1969)26<636:APARBN>2.0.CO;2 | 1969 | références seulement |
| Hawkes et popularité en cache (HRS), arXiv 2102.00646 | https://www.arxiv.org/abs/2102.00646 | 2021 | résumé de recherche |
| Gaussian rate-distortion and reverse waterfilling (cours TU Berlin) | https://commit-web.commit.tu-berlin.de/en/book/ita/chapter/ch06/section/s04 | s. d. | résumé de recherche |
| *Leveraging the True Depth of LLMs*, arXiv 2502.02790 | https://arxiv.org/html/2502.02790v3 | 2025 | résumé de recherche |

Fichiers du dépôt : `genome/mimetisme/terre_cosmos/seuil-declare.md` ; outils `cache_terre.py`, `phase_terre.py`,
`eau_usage.py`, `lfu_demivie.py`, `alloc_lfu.py`, `t2_melange.py` ; mesures
`mesures/mimetisme/terre_cosmos/` (JSON, journaux de passes).
