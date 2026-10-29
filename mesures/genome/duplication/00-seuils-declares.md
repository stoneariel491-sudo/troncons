# Seuils déclarés avant la mesure (sujet duplication, 2026-10-16)

Écrits et commités **avant** toute mesure de débit (bits lus) d'un expert codé comme mutation de son
parent. Mesures faites avant ce fichier, qui ne jugent aucun codage : l'écran de parenté
(`ecran_parente.py`, en cours) et ses témoins, le témoin de l'appariement (`paires_arbre.py --planter`),
le spectre de famille de la couche 12 (`spectre_famille.py`), et une sonde ECSQ d'un seul expert
(couche 12, expert 3 ; journal de session, non retenue : le sujet predictif-elagage porte l'ECSQ).

## La frontière (rappel, fichiers commités par d'autres)

- Sans perte : A_ctx, **3,8431** bits par poids (F1, `decisions/journaux/arbitre/decoupe-gptoss20b.json`).
- Base seule : **2,6441** bits par poids lus à **4,2920 %** d'erreur quadratique relative (07 § 4.2), sur
  les 12 tenseurs de F1 (couches 0, 8, 16, 23 × gate, up, down de gpt-oss-20b).

## L'échantillon

Enfants : experts 0, 8, 16, 24 de chacune des couches 0, 8, 16, 23 (16 enfants, 48 matrices). Parent de
chaque enfant : le meilleur par le score d'appariement (`paires_arbre.py`) parmi les 31 autres experts de
sa couche et les 32 experts de la couche précédente (pour la couche 0 : sa couche seulement). Le choix du
parent ne lit que les poids ; il est fait avant le codage et n'est pas retouché ensuite.

## D1, sans perte sur les codes MXFP4 (gate et up seulement)

Pour gate et up, la permutation des neurones permute des rangées entières : les blocs de 32 restent
intacts et le code de l'enfant peut se conditionner exactement au code du parent apparié. ~~Pour down, la
permutation traverse les blocs : pas de version sans perte (dit, non mesuré).~~ Corrigé le 2026-10-16,
avant la mesure de l'échantillon : conditionner le code de l'enfant en (i, k) au code du parent en
(i, col[k]) ne demande pas que les blocs restent entiers ; D1 se mesure donc aussi sur down (même seuil,
48 matrices au lieu de 32).

Bits de l'enfant = H(code_enfant | code_parent apparié, classe d'échelle de F1) + échelles de F1 (δ et
médianes, inchangées) + permutation (⌈log₂ 2880!⌉ bits par expert, partagés par ses 3 matrices) + tables
(16 × 16 × 3 comptes de 16 bits par paire). **D1 marche** si ces bits sont sous A_ctx du même tenseur sur
**chacune** des 32 matrices gate et up (test du signe : 2⁻³² sous l'hypothèse nulle) et en global.
Attendu, et écrit avant : il ne marche pas. L'écran donne un cos moyen apparié de 0,04 pour gate et up
contre 0,04 pour le témoin de hasard, soit une information mutuelle de l'ordre de 10⁻³ bit par poids.

## D2, avec perte (les trois rôles)

Enfant reconstruit par ŷ = α ⊙ P(parent) + Q(résidu), α une échelle par rangée (16 bits par rangée,
comptés), Q un quantificateur uniforme de pas Δ commun au tenseur, codé par son entropie conditionnelle à
l'exposant E8M0 du bloc de l'enfant (échelles de F1 comptées). Le même quantificateur sans parent (α = 0)
est le **témoin d'indépendance** : il dit ce que vaut l'ECSQ seule, sans duplication.
**D2 marche** si, à l'erreur quadratique relative de la base (4,2920 %, interpolation en log de l'erreur
entre deux pas voisins), les bits lus sont sous 2,6441 sur chaque matrice ET sous le témoin
d'indépendance de la même matrice de plus que l'écart-type, entre matrices, du gain mesuré sur des parents
de hasard (enfant apparié à un expert dont les dimensions d'entrée sont permutées). Sans la seconde
condition, le gain reviendrait à l'ECSQ, pas à la parenté.

## T, la mutation tronquée

Enfant servi par α ⊙ P(parent) seul (résidu jeté) puis par le résidu à des pas de plus en plus grossiers :
erreur relative sur les poids et sur la sortie de l'expert. Aucun seuil de réussite : c'est la mesure de
ce que coûte la troncature, demandée par la consigne.

## O, la sortie d'une couche d'experts sur entrées réelles

Entrées : les états normalisés réellement routés vers chaque expert de l'échantillon, capturés par la
référence f64. Erreur relative de la sortie de l'expert (down, biais compris) Σ‖y − ŷ‖² / Σ‖y‖² sur les
jetons routés vers lui. Au point de fonctionnement retenu, D2 doit faire **au plus** l'erreur de sortie de
la base, couche par couche (4 sur 4).

## K, la divergence KL (si mesurée)

KL(référence ‖ enfants substitués) moyenne sur les positions, appariée contre KL(référence ‖ base
substituée) aux mêmes couches : la mutation doit faire moins, test du signe sur les positions (p < 0,01).

## L'arbre

Gain d'une couche codée par son arbre couvrant de poids maximal sur les scores d'appariement, en bits par
poids, comparé au même calcul sur des paires de hasard. Aucun seuil : c'est la mesure du « plus économe ».

## Addendum, déclaré le 2026-10-16 après l'essai sur un seul enfant et avant l'échantillon

L'essai (`essai-mutation-c8-e0.*`, couche 8, expert 0, parent (8, 31)) a montré deux faits qui
changent la lecture de D2, sans toucher aux seuils écrits plus haut :
- la prédiction soustraite (α ⊙ P puis ECSQ du résidu) coûte **plus** que l'ECSQ seule (gate : 1,91
  contre 1,50 bit à ε = 4,29 %) : la soustraction rend continu un résidu dont l'enfant était sur la
  grille MXFP4, et l'ECSQ seule profite de cette grille ;
- l'ECSQ à pas commun bat la frontière sur les poids (≈ 1,5 à 1,7 bit à 4,29 %) mais rend une erreur de
  **sortie** de 29,3 % contre 8,3 % pour la base, à erreur de poids voisine (5,1 % contre 4,7 %) : le pas
  commun efface les blocs de petite échelle. L'erreur sur les poids n'est donc pas un juge suffisant ici.

D'où deux mesures de plus, déclarées avant l'échantillon :
- **D2c** (même reconstruction que l'ECSQ seule, au bit) : les indices de l'ECSQ seule codés sachant
  l'exposant ET la prédiction du parent quantifiée (borne(round(αP/Δ), −3, 3)). Gain = I(q ; parent | e).
- **D2b** (même reconstruction que la base de B, au bit, donc même erreur de poids et de sortie) : les
  symboles de la base (signe + 4 classes) codés sachant κ ET le symbole de base du parent apparié.
  **D2b marche** si, sur chacune des 48 matrices, le gain dépasse les informations ajoutées (permutation,
  ⌈log₂ 2880!⌉ / (3 · 2880²) ≈ ~~3,5·10⁻⁴~~ **1,16·10⁻³** bit par poids, et les tables, 8 × 8 × 3 comptes de 16 bits par
  matrice, ~~1,2·10⁻⁴~~ **3,7·10⁻⁴**), et le gain du parent de hasard de la même matrice. Elle bat alors la frontière de
  2,6441 bits à la même erreur exacte. Attendu, écrit avant : le gain sera de l'ordre de 10⁻³ à 10⁻²
  bit, la frontière tombera d'autant au plus.

Correction du 2026-10-16, avant toute lecture de l'échantillon : les deux coûts de l'addendum étaient
faux d'un facteur 3 ; refaits par `math.lgamma` (log₂ 2880! = 28 948,6 bits, sur 24 883 200 poids) et
192 × 16 / 8 294 400. Le seuil de D2b monte d'autant (1,53·10⁻³ bit par poids en tout).
