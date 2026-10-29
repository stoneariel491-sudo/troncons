# Seuils déclarés avant toute lecture de données : éclaireur du vivant

Écrit le 2026-10-26, commité avant que mon code ait ouvert une trace. Ce que j'ai vu des traces
avant d'écrire : la première ligne de `t20b.code.lecture.trace` et de son fichier `.poids` (le format),
rien d'autre. Les données lues : les traces de routage de `mesures/localite-gpt-oss/` (20b : 24 couches,
32 experts ; 120b : 36 couches, 128 experts ; k = 4), cinq genres en « lecture » (code, dialogue,
prose-en, prose-fr, wiki), poids de mélange à quatre décimales. Aucun fichier de modèle n'est ouvert
(le verrou de la carte est posé : séance de disque en cours).

Étiquettes : [mes.] mesuré, [calc.] calculé. Une seule grandeur de référence pour tous les gains en
octets : le **taux de défaut** (1 − succès) d'un cache d'experts, parce que, sur le disque limitant
(2,82 Go/s), les octets lus par jeton valent défauts × 13,25 Mo et le débit en jetons par seconde leur
est inversement proportionnel (`mesures/gpt-oss.md` § 0, plafond du disque).

## Règle de décision commune (dérivée de la règle de vitesse de 06-modeles.md § 7.5)

Une différence de vitesse n'est réelle que si elle dépasse 2 × le bruit et 3 %. Un mécanisme de cache
qui n'ajoute que 3 % de défauts en moins ne paie pas son coût (état du prédicteur, calcul, risque).
**Seuil : au moins 10 % de défauts en moins, en valeur relative, contre le meilleur des deux
politiques connues et gratuites (LRU, LFU à demi-vie de 8 jetons) au même budget**, soit plus de
trois fois la règle des 3 %, marge pour les coûts non modélisés. Le gain doit être de même signe sur
au moins 4 genres sur 5.

## E-A : politiques de remplacement inspirées de la mémoire (par couche, budget C par couche)

Simulateur à moi, même sémantique que `outils/chargement_localite.py` (insertion sur défaut, on n'évince
jamais un expert demandé par le jeton courant, démarrage à froid compté).

Politiques jugées :
- **ACT-R** (Anderson et Schooler 1991, analyse rationnelle de la mémoire) : activation de base
  B(e) = ln Σ_j (t − t_j + 1)^(−d), on évince la plus basse ; **d = 0,5 fixé avant** (valeur de la
  littérature, pas ajustée sur nos traces) ; d = 0,3 et d = 0,8 rapportés comme sensibilité seulement.
- **ASSOC** (anticipation apprise, Mitchell et al. 2009 ; Hebb) : score(e) = Σ_{e' ∈ S_t} (N[e'][e] +
  p0(e)) / (n[e'] + 1), N comptant en ligne, dans la couche, les paires (e' dans S_{t−1}, e dans S_t)
  déjà vues, p0 la fréquence à demi-vie 8 ; on évince le score le plus bas. Aucun paramètre ajusté.

Budgets : 120b, C = 13 et 26 (10 % et 20 % des 128 experts) ; 20b, C = 6 et 10.

**Verdict « passe »** pour une politique et un modèle : sur les deux budgets, la médiane sur les 5
genres du gain relatif de défauts contre le meilleur de {LRU, LFU8} est ≥ 10 %, et le gain est
positif sur ≥ 4 genres. Sinon « tombe ». Pour ASSOC, condition en plus : **témoin de cassure** (ordre
des jetons mélangé) : le gain doit s'effondrer à moins du tiers de sa valeur ; sinon ASSOC ne lit pas
la séquence, il relit la popularité.

Témoins (réponse connue, déclarés avant) :
- W1 : mon LRU égale `cache_lru` de l'instrument, mon LFU8 égale `cache_lfu`, à 10⁻¹², sur chaque trace
  et chaque budget ; mon Belady égale `cache_belady`.
- W2 : la politique « score = dernier instant d'usage » égale LRU exactement.
- W3 (causalité) : les décisions des politiques sur la moitié d'une trace sont identiques à celles de la
  trace entière sur cette moitié (le prédicteur ne voit pas l'avenir).
- W4 (peut tomber) : on remplace la trace par une trace synthétique de routage uniforme i.i.d. : ACT-R
  et ASSOC doivent égaler LRU à ± 4 écarts-types (rien à apprendre) ; si l'un « gagne », mon code fuit.

## E-B : allocation des emplacements entre couches par valeur marginale (Charnov 1976)

Budget total N = L × C0 emplacements (C0 comme ci-dessus), un LRU par couche de taille C_ℓ ≥ 4,
C_ℓ choisi par gain marginal glouton des courbes de défauts LRU de chaque couche, **courbes apprises
sur les quatre autres genres** (jamais sur le genre testé), évaluées sur le genre testé contre l'allocation
uniforme C0. **Verdict « passe »** : médiane sur les genres de la réduction relative de défauts ≥ 10 %,
positive sur ≥ 4 genres, aux deux budgets. Témoins : (i) si toutes les courbes sont identiques,
l'allocation est uniforme exactement ; (ii) courbes permutées au hasard entre couches : le gain doit
tomber à moins du tiers du gain réel ; (iii) le total d'emplacements est conservé à l'unité.

## E-C : lecture graduée selon le poids de mélange (fovéation) : borne, pas verdict

Sans exécuter le modèle, aucune KL n'est mesurable. La mesure ici est une **borne sur la masse
abandonnée** : pour chaque (jeton, couche), on abandonne (saute ou lit en précision réduite) les
experts de plus faible poids tant que la masse abandonnée reste ≤ τ ; on rapporte la part des experts
**manqués** (défauts de LRU au budget ci-dessus) qui est abandonnable, pour τ = 1, 2 et 5 %. **Seuil
pour mériter une passe KL sur le moteur** : au moins 15 % des défauts abandonnables à τ = 2 % (15 %
parce qu'une passe KL coûte des heures de processeur et que le gain de vitesse est le même 1/(1 − 0,15)
= +18 %). Témoins : poids égaux (0,25 × 4) → 0 % abandonnable à τ = 2 % ; poids (0,97 ; 0,01 ; 0,01 ;
0,01) → 3 experts sur 4 abandonnables à τ = 3 %.

## E-D : synergies de routage (Tresch, Cheung, d'Avella 2006 ; Bernstein)

Matrice jetons × (couches × experts) des indicateurs de routage. Dimension effective : le plus petit
nombre K50 de composantes SVD (matrice centrée par colonne) qui portent 50 % de l'énergie. Contre un
**nul** qui garde les fréquences de chaque (couche, expert) mais tire les couches indépendamment l'une
de l'autre. **Verdict « synergies »** : K50(nul) / K50(réel) ≥ 2. Témoins : nul contre nul → rapport
dans [0,8 ; 1,25] ; matrice synthétique à 3 synergies plantées → ~~K50 = 3~~ **rang centré = 3** (correction écrite avant tout calcul : trois synergies de poids égaux donnent K50 = 2, pas 3 ; ce qui doit valoir 3 est le nombre de valeurs propres non nulles).

## E-E : queue des experts au préremplissage (Pareto)

Fenêtres de P = 128 et 512 jetons ; par couche, les experts touchés au moins une fois ; « queue » =
touchés par ≤ 2 jetons. **Seuil pour mériter une passe KL** : la queue pèse ≥ 20 % des experts lus
pour ≤ 2 % des affectations (jeton, expert). Témoin : routage uniforme i.i.d. (P = 512, E = 128,
k = 4 : moyenne 16 par expert) → queue vide.

## E-F : union des experts sur γ jetons consécutifs (décodage spéculatif), descriptif

U(γ)/(γ·k) par couche pour γ = 1 … 8 ; pas de seuil, c'est le ρ du lemme B2. Témoin : routage figé
→ U = k ; i.i.d. → U ≈ E (1 − (1 − k/E)^γ).

## Ce que je n'ai pas le droit de conclure d'une passe sur traces

Une politique qui « passe » ici passe sur des traces de lecture de 5 textes, pas sur la génération
de l'utilisateur, et sans coût d'état ; elle mérite alors une passe sur le simulateur du moteur
(Tome II), pas une construction. Le débit en jetons par seconde ne se déduit pas du taux de défaut
sans le modèle de plafond de `gptoss_localite.py`.

## Ajout du 2026-10-27 (avant tout calcul de E-G ; E-C était déjà lancé, voir `ec.log`)

### E-G : résidence partielle, « polymérase en pause » (Core et Adelman 2019)

Un gène « poised » garde sa transcription amorcée et suspendue ; on libère le reste au signal. Traduction :
garder en RAM la **base** (2,64 bit par poids, soit r = 2,64 / 3,68 = 0,717 de l'expert) de tous les experts
qui tiennent, et ne lire sur le disque que le **complément** quand l'expert est appelé. Octets lus par
accès, en unités d'expert plein, au budget X (en experts pleins par couche) : A (experts entiers) =
1 − h(X) ; B (bases) = (1 − h(X / r)) + h(X / r) × (1 − r), h = courbe de succès LRU par couche
mesurée (moyenne des couches). **Passe** si B ≤ 0,9 × A pour au moins un budget de C0 sur ≥ 4 genres.
**Prédiction écrite avant le calcul : tombe** (si h est concave, l'échange est neutre au mieux : ce
qu'on gagne en taux de succès, on le reperd en complément à lire).

### E-H : modulation neuromodulatrice de la précision (Yu et Dayan 2005), déclaré le 2026-10-27 avant tout calcul

Yu et Dayan : une incertitude « inattendue » (surprise) fait basculer le cortex en mode attentif. Traduction :
choisir par jeton entre le mode exact (3,68 bits, KL 0) et le mode rapide (2,64 bits, KL perdue) d'après
un signal **gratuit et déjà connu avant le jeton** : la surprise du jeton précédent sous le modèle qui
tourne (`nll_q` à la position i − 1), ou sa moyenne glissante sur 4 positions. Données : les deux fichiers de
KL par position du mode rapide sur le 20b, commités (`mesures/genome/construction/juge/kl/` :
`kl-r1-synonyme-l0-768-positions.csv` (R1) et `kl-neuf-moteur-rapide-l0-positions.csv` (fenêtres neuves)),
colonnes `kl`, `nll_q`. Seul regard avant d'écrire : les deux premières lignes de chacun (le format).
**Passe** si, dans les deux fichiers : (a) rho de Spearman entre kl_i et le signal ≥ 0,30 ; (b) les 20 %
de positions au plus fort signal portent ≥ 40 % de la KL totale (le double du hasard ; gain
correspondant : à octets égaux, 20 % de jetons exacts, KL de 0,60 de celle du tout-rapide contre 0,80 par
tirage au hasard) ; (c) même signe sur ≥ 8 fenêtres sur 10. Témoins : signal mélangé → part des 20 % dans
[15 % ; 25 %] ; signal = kl lui-même → part maximale (calculée) ; cassure : signal décalé de 100
positions → la part retombe vers 20 %.

### E-I : puissance prédictive d'un modèle de synergies appris hors ligne, déclaré le 2026-10-27 avant calcul

But : savoir si un prédicteur appris sur d'autres textes (donc livrable avec troncons) devine les experts
du jeton t + 1 mieux que ce que savent déjà LFU et l'association en ligne. Mesure : **rappel@C**, par
(jeton, couche) la part des 4 experts vrais du jeton t + 1 présents dans les C premiers du classement
prédit à la fin du jeton t, aux budgets C de E-A. Prédicteurs : P0 popularité statique (4 autres
genres) ; P1 popularité à décroissance (demi-vie 8, en ligne) ; P3 association de même couche (comptes
appris sur les 4 autres genres puis mis à jour en ligne) ; **P4 synergies** : état de routage complet du
jeton t (toutes couches, 0/1) projeté sur ses K = 64 premières composantes (ACP des 4 autres genres),
régression ridge (alpha = 1 sur la variance totale) vers l'état du jeton t + 1 de toutes les couches,
appris sur les 4 autres genres seulement ; **P4m** : P4 + P1 (somme des rangs). Test sur le genre laissé
de côté. **Passe** si, aux deux budgets de chaque modèle, max(P4, P4m) − max(P1, P3) ≥ 0,05 en rappel
(5 points absolus ≈ le tiers à la moitié de l'écart LFU–Belady au budget de 20 % sur le 120b, soit ≥ 10 %
de défauts en moins) pour une médiane de 5 genres et ≥ 4 genres positifs. Témoins : ordre des jetons
mélangé à l'apprentissage (paires (t, t+1) tirées au hasard) → le gain de P4 doit s'effondrer sous le
tiers ; P4 avec K = 1 doit être inférieur à K = 64 ; causalité par construction (apprentissage sur d'autres
genres, jamais sur le genre testé).

### E-J : éviction pilotée par le prédicteur de synergies à deux jetons, déclaré le 2026-10-27 avant calcul

**Ce que j'avais vu avant d'écrire E-J** : les résultats de E-I sur le 20b et le début du 120b (le
prédicteur appris sur d'autres genres bat la popularité en ligne sur 4 genres sur 5, et s'effondre sur
le code). Le seuil ci-dessous est celui de E-A, déclaré avant tout calcul de E-J.

Le rappel@C de E-I mesure la qualité d'un ensemble recalculé à chaque jeton, pas des octets. Les octets
sont des défauts de cache. E-J met le prédicteur au travail dans le simulateur de E-A. Contrainte de
causalité : au moment d'une éviction pendant le jeton t', l'ensemble S_{t'}(couche) est connu, donc le
score d'un candidat doit parler du jeton t' + 1. On n'a alors de complet que l'état X_{t'−1} de toutes
les couches : le prédicteur est appris pour le **pas de deux jetons** (X_t vers X_{t+2}, mêmes K = 64
composantes, même ridge, mêmes 4 autres genres). Politique **SYN2** : on évince le candidat de plus petit
rang-somme de (score du prédicteur appliqué à X_{t'−1}, popularité à décroissance P1 jusqu'à t'). Autres
politiques : P1 seule (même popularité, mon implémentation), LRU et LFU8 (instrument). Budgets de E-A.
**Passe** : médiane des 5 genres du gain relatif de défauts contre le meilleur de {LRU, LFU8, P1 seule} ≥ 10 %
et gain positif sur ≥ 4 genres, aux deux budgets de chaque modèle. Témoins : apprentissage sur paires
mélangées → gain sous le tiers ; score du prédicteur remplacé par une constante → SYN2 = P1 seule (écart
< 10⁻⁹) ; causalité (moitié de trace contre trace entière, mêmes décisions).

### E-J2 : même éviction, popularité de demi-vie réglée, déclaré le 2026-10-27 avant son calcul

Après le contrôle de demi-vie (ablation-demivie.json : un LFU de demi-vie 32 à 128 jetons, choisie sur les
autres genres, égale ACT-R et retire 12,5 à 21,4 % des défauts contre LRU), la bonne question n'est plus
« SYN2 bat-il le LFU de demi-vie 8 », c'est « le prédicteur de synergies ajoute-t-il quelque chose à un
LFU bien réglé ». E-J2 relance E-J avec la popularité P1 de demi-vie **64** (valeur la plus fréquemment
choisie ailleurs) pour P1 seule et pour SYN2. Même seuil : médiane des 5 genres ≥ 10 % de défauts en moins
contre le meilleur de {LRU, LFU8, P1(64) seule}, ≥ 4 genres positifs, aux deux budgets de chaque modèle.
**Prédiction écrite avant calcul : tombe** (le prédicteur ajoute au plus quelques points).

### E-K : mémoire épisodique clairsemée, la mouche (Dasgupta, Stevens, Navlakha 2017), déclaré le 2026-10-27 avant calcul

Le circuit de la mouche donne à chaque odeur une étiquette clairsemée (expansion 40 fois, le gagnant prend
tout) dont le recouvrement approche la ressemblance, pour retrouver des odeurs semblables. Traduction :
retrouver, **dans la session elle-même**, les jetons passés dont l'état de routage (toutes couches, 0/1)
ressemble à celui du jeton courant, et lire ce qui les a suivis. Le calcul testé est l'objet que l'étiquette
approche, la similarité cosinus exacte (une borne favorable à toute version hachée). Politique **KNN** :
pour la fin du jeton t, voisins = les k = 8 jetons j ≤ t − 1 de plus fort cosinus entre X_j et X_t (k fixé
avant) ; score de (couche, expert) = somme pondérée par le cosinus de X_{j+1} ; **KNNm** = KNN + popularité à
décroissance de demi-vie 64 (somme des rangs, comme P4m). Mesure : rappel@C de E-I, mêmes budgets, même
test. Rien n'est appris sur d'autres genres : c'est ce qui doit aider le code, que le prédicteur hors ligne
rate. **Passe** : max(KNN, KNNm) − max(P1(64), P3) ≥ 0,05 en médiane des 5 genres, ≥ 4 genres positifs, aux
deux budgets de chaque modèle. Témoins : successeurs mélangés (voisins gardés, X_{j+1} tiré au hasard) → le
gain s'effondre sous le tiers ; k = 1 doit donner un rappel inférieur à k = 8 ; causalité par construction
(j ≤ t − 1).

### E-L : éviction pilotée par la mémoire épisodique, déclaré le 2026-10-27 avant calcul

E-K (rappel@C) a montré, à l'oeil, un avantage aux petits budgets (+4 à +7 points) et plus rien à 20 % des
experts. La monnaie des octets est le défaut de cache : E-L met KNN dans le simulateur, comme E-J. Pas de
deux jetons pour la causalité (le jeton courant n'est connu que par la couche en cours) : pour l'éviction
pendant le jeton t', score d'un candidat de la couche ℓ = somme, sur les k = 8 jetons j ≤ t' − 3 de plus fort
cosinus avec X_{t'−1}, de cos × X_{j+2}[ℓ] (j + 2 ≤ t' − 1 : tout est passé ; on n'utilise que la tranche de
la couche ℓ). Politique **EPI** : on évince le plus petit rang-somme de (score épisodique, popularité à
demi-vie 64). Comparée à LRU, LFU8 et P1(64) seule. **Passe** : médiane des 5 genres ≥ 10 % de défauts en
moins contre le meilleur de ces trois, ≥ 4 genres positifs, aux deux budgets de chaque modèle. **Prédiction
écrite avant calcul : tombe** (au plus 3 à 5 %). Témoins : successeurs tirés au hasard → gain sous le tiers ;
score constant → EPI = P1(64) seule (écart < 10⁻⁹) ; k = 1 inférieur à k = 8 ; causalité par construction
(j + 2 ≤ t' − 1).
