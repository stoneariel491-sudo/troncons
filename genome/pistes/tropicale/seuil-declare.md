# La garde tropicale : seuils et protocole, déclarés avant la lecture

Écrit le 2026-10-21 à 23 h 25, **avant toute lecture des journaux de routage par les outils de cette
piste**, et commité avant elle. Ce qui était déjà publié et lu : le résumé commité de `bascules.py`
(`mesures/moteur/R/r1/bascules-openai-llamacpp-20b.json`, repris dans 05 § 2.2 et § 3.1 : 5 087
bascules, quantiles des marges). Rien d'autre.

Source de la piste : 05 § 3.1 (idée de Stone, § 5 quinquies). Seuil de décision repris tel quel de
05 § 3.1, où il est dérivé du coût : un défaut d'expert exact sur 10 % des cellules coûte au plus
10 % des octets du mode exact.

## 1. Les données (toutes commitées par le lot R, commit `21453da`)

| Rôle | Fichier | SHA-256 |
|---|---|---|
| A, la rampe d'OpenAI (référence du juge) | `mesures/moteur/R/r1/routage/ref-openai-bis-20b.bin` | `f0a19c1182a3db507c7ade3d49734f765372bd6d1e101e3f4d0cb9be785b8d3c` |
| B, la rampe de llama.cpp (le calcul perturbé) | `mesures/moteur/R/r1/routage/ref-llamacpp-bis-20b.bin` | `07a9d4f974fd00ea8e56330865021f139025741fd63afe5b45c562336fd549d0` |
| C, la rampe de llama.cpp, routage de A imposé | `mesures/moteur/R/r1/routage/ref-llamacpp-routage-openai-20b.bin` | `3e77be12bed8bc8be6123bdc81ccd654ca1169494dab27ae79307c2bd9a0f609` |
| D, contrôle croisé : moteur de la carte contre la référence (K3 d1, 160 positions) | `mesures/moteur/K/k3/k3-chaine-d1-gptoss20b-marges.csv` | `30947e5f58dbe8ad3d6ab3be1107f3e483f346bf5634ea9442bc0456925575d7` |

Format (tête de `bascules.py`) : u32 couches, u32 positions aplaties (fenêtre × 511 + position),
puis, couche par couche et position par position, 4 × u8 experts et f32 marge (4e − 5e logit
biaisé du routeur). gpt-oss-20b : 24 couches, 32 experts, top-4 ; 10 fenêtres de 512 jetons.

## 2. Les définitions

- **Cellule** : un couple (couche, position). 24 × 5 110 = 122 640 cellules.
- **Bascule** : une cellule où l'ensemble des quatre experts de A diffère de celui de B.
- **Marge de garde** : la marge **de B**. Raison : la garde tourne dans le calcul rapide et ne voit
  que sa propre marge ; dans le couple du juge (`juge-kl-ref-llamacpp-20b-contre-ref-openai-20b`),
  A est la référence et B le calcul qui s'en écarte.
- **Garde au seuil τ** : elle signale la cellule si la marge de B y est < τ.
- **Part des cellules** c(τ) = (cellules signalées) / 122 640 ; **part des bascules** b(τ) =
  (bascules signalées) / (bascules).
- Grille : τ de 10⁻⁴ à 10⁻¹, 61 points espacés en logarithme (10 par décade), plus le point
  exact τ₁₀ = le seuil qui signale 10 % des cellules (le décile de la marge de B).

## 3. Le seuil de décision

**La garde vaut d'être construite si b(τ₁₀) ≥ 80 %**, c'est-à-dire s'il existe un τ qui attrape au
moins 80 % des bascules en signalant au plus 10 % des cellules. Sinon elle tombe sur ce critère.

Chemin principal : lecture vectorisée (numpy). **Second chemin**, indépendant, pour le point
principal : la lecture en Python pur de `bascules.py` (`lire`, écrite par le lot R, autre code),
comptage par boucles, tri sans numpy. Les deux doivent rendre le même nombre de cellules et de
bascules signalées à τ₁₀, à l'unité ; sinon aucun chiffre ne sort.

## 4. Les témoins, chacun prouvé capable de tomber

- **T1, la lecture** : le chemin principal redonne exactement le résumé commité de `bascules.py`
  (5 087 bascules ; quantiles 0,01 / 0,1 / 0,5 / 0,9 des marges de A, toutes et aux bascules, au
  dernier chiffre de f32). Cassure : une copie de B dont un octet d'expert est changé doit donner
  5 087 ± 1 ou plus (le compte bouge) ; une lecture au mauvais pas (7 octets au lieu de 8) doit
  être refusée par la vérification de taille.
- **T2, la réponse connue d'avance** : A contre C (routage de A imposé à C) : **0 bascule**
  attendue. Cassure : la même comparaison sur une copie de C dont un expert est changé doit en
  trouver une.
- **T3, l'instrument discrimine** : (i) marges de B permutées au hasard entre cellules (graine
  fixée) : b(τ₁₀) doit tomber à 10 % ± 2 points (la garde n'attrape plus que le hasard) ; (ii)
  marges oracles (0 sur les bascules, marge de B ailleurs) : b doit valoir 100 % pour c ≤ 4,2 %.
  Si (i) ou (ii) manque, l'instrument est mort et aucun verdict ne sort.

## 5. Ce qui se mesure en plus, sans décider

- b(τ) et c(τ) par couche ; avec la marge de A, et avec min(A, B) (oracle, non déployable) ; sur les
  seules positions notées par le juge (seconde moitié de chaque fenêtre) ; contrôle croisé sur D
  (marge de la référence, 22 bascules : trop peu pour juger, assez pour contredire).
- **La loi de la marge par couche** : quantiles, densité près de zéro, ajustement exponentiel,
  gamma, demi-normal, log-normal (distance de Kolmogorov-Smirnov).
- **La corrélation des marges d'une couche à la suivante**, même position : Spearman par couple de
  couches, contre la permutation des positions (999 tirages).
- **La loi de bascule** P(bascule | marge) : ajustement d'un modèle de perturbation gaussienne de
  l'écart (P = 2 Φ(−m / σ_ℓ)) ; extrapolation, par ce modèle, de b(τ₁₀) quand σ grandit (le mode
  rapide perturbe plus que deux rampes exactes). C'est un modèle, et il sera dit tel.
- **La marge comme priorité de préchargement**, deux lectures, toutes deux sur ces journaux :
  (P1) la marge de la couche ℓ prédit-elle l'absence de bascule à la couche ℓ + 1 (même position) ?
  (P2) la marge de (ℓ, p) prédit-elle que la position p + 1 garde le même ensemble à la couche ℓ ?
  Seuil déclaré pour chacune : la marge est **une priorité utile** si son aire sous la courbe ROC
  dépasse à la fois 0,60 et le 99,9e centile des aires obtenues sur 999 permutations des marges.
  La lecture « routeur ℓ + 1 appliqué à l'état de la couche ℓ » demande les états cachés, qui ne
  sont pas journalisés : elle n'est pas faite ici et sera dite manquante.

## 6. La prédiction, écrite avant

D'après le résumé déjà publié (décile des marges de A : 0,0124 ; médiane des marges aux bascules :
0,0095), b(τ₁₀) devrait se trouver vers 55 à 65 % : **je prédis que la garde tombe** au critère
80 / 10. Une prédiction n'est pas une mesure ; elle est écrite pour qu'on voie si la mesure la
contredit.

## 7. Ce que ce protocole ne peut pas dire

La perturbation des journaux est l'écart entre deux calculs exacts (les deux rampes de position),
pas l'erreur du mode rapide. Si la garde tombe ici, l'extrapolation du § 5 dira si elle tombe a
fortiori sous une perturbation plus forte ; si elle passe, le verdict est nécessaire, non suffisant,
et demande un journal de routage du mode rapide.

## 8. La cohabitation

Aucun calcul sur la carte, verrou de la carte jamais pris ; processus en priorité « sous la
normale », un fil (`OMP_NUM_THREADS=1`) ; les journaux font 1 Mo chacun.
