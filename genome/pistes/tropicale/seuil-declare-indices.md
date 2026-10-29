# La garde à indices multiples : seuil et protocole, déclarés avant tout calcul

Écrit le 2026-10-26 à 23 h 41, **avant** que les indices ci-dessous soient calculés sur les journaux et
commité avant eux. Ce qui est déjà publié et lu : le livrable `garde-tropicale.md` (verdict de la garde
à marge seule : 57,1 % des bascules pour 10 % des cellules, jugé et refait à l'unité par
`JUGEMENT.md`), dont § 9 dit que « seule la marge est journalisée » et que d'autres entrées
« pourraient trier mieux ». Cette note déclare la mesure qui répond à ce § 9 sur les mêmes journaux.

## 1. D'où vient l'idée (le vivant)

Le cortex cingulaire antérieur surveille le **conflit** entre réponses concurrentes et en **accumule**
la trace d'un essai à l'essai suivant (Botvinick, Braver, Barch, Carter, Cohen, « Conflict monitoring
and cognitive control », *Psychological Review* 108 (3), 2001, p. 624-652 ; notice vérifiée le
2026-10-26). Quand le conflit est élevé, le cortex médiofrontal relève le **seuil de décision** avant
d'agir : la puissance thêta médiofrontale, d'un essai à l'autre, suit le seuil du modèle à dérive et
diffusion (Cavanagh, Wiecki, Cohen, Figueroa, Samanta, Sherman, Frank, *Nature Neuroscience* 14 (11),
2011, p. 1462-1467, doi 10.1038/nn.2925 ; notice vérifiée le 2026-10-26). La garde tropicale à marge
seule fait la moitié de cela : elle lit le conflit **instantané** (la marge, petite quand deux experts
se disputent la quatrième place). Le vivant ajoute la **mémoire du conflit**. La mesure : une garde qui
lit en plus le conflit récent trie-t-elle mieux les bascules ?

Cela reste une analogie qui propose une mesure ; elle ne prouve rien d'avance. La mesure décide.

## 2. Les indices (tous lisibles par le calcul rapide seul : marges et experts de B, jamais A)

Pour une cellule (ℓ, p) de la fenêtre w (positions 0 à 510) :
- **f1** = ln m_B(ℓ, p), la marge instantanée (le témoin de la garde actuelle) ;
- **f2** = ln min{ m_B(ℓ', p) : ℓ' < ℓ }, le conflit le plus fort déjà vu plus bas **sur la même
  position** ; pour ℓ = 0, f2 = 0 (marge neutre, grande) ;
- **f3** = ln m_B(ℓ, p − 1), le conflit de la **position précédente à la même couche** (le cache KV
  porte l'erreur d'une position à la suivante) ; pour p = 0, f3 = 0 ;
- **f4** = la part des cellules {(ℓ', p') : ℓ' ≤ ℓ, p − 8 ≤ p' ≤ p − 1, même fenêtre} dont la marge de B
  est sous 0,01241 (le τ₁₀ du verdict, déjà publié) : le conflit **accumulé** sur les huit dernières
  positions ; si l'ensemble est vide (p = 0), f4 = 0 ;
- **f5** = ℓ / 23, la profondeur.

Aucun indice n'utilise l'ensemble d'experts de A, ni la vérité « bascule » : un garde réel n'a pas ce
que la référence a. (Le seul usage de la vérité hors étiquette est le témoin W3, § 5.)

## 3. Les modèles comparés

Régression logistique, pénalité L2 de 1 (indices centrés réduits sur l'entraînement), étiquette y =
« A et B diffèrent d'ensemble ». Entraînement sur 9 fenêtres, test sur la dixième, **dix plis (un par
fenêtre)**.
- **M0** : la garde actuelle, marge seule (rang croissant de m_B), sans modèle ;
- **M1** : f1 seul (doit redonner M0, § 5 W1) ;
- **M2** : f1, f5 et f1·f5 (la profondeur sans mémoire) ;
- **M3** : f1 à f5 et f1·f5 (la garde à indices multiples).

Dans chaque pli, la garde signale **exactement les 10 % de cellules de la fenêtre de test qui ont le
score le plus fort** (coût fixé à 10 % par pli, donc comparable d'un modèle à l'autre). La part des
bascules attrapées b est la somme des attrapées sur les dix plis divisée par 5 087.

## 4. Les seuils de décision (déclarés avant)

- **Seuil du 05, inchangé** : la garde vaut d'être construite si b ≥ 80 % à 10 % de cellules.
- **Seuil d'utilité de la mémoire du conflit** : M3 est jugé utile si **(i)** b(M3) − b(M0) ≥ **5 points**,
  **(ii)** l'intervalle à 95 % de cette différence appariée (rééchantillonnage des dix fenêtres, 10 000
  tirages, graine 20261026) exclut 0, **(iii)** la différence est positive dans au moins **8 fenêtres sur 10**.
  Sinon la mémoire du conflit **n'apporte pas** au-delà de la marge, et c'est un résultat.
- Une garde utile mais sous 80 % n'est pas construite pour ce motif : elle n'ouvre que la mesure G2.

**Prédiction écrite avant la lecture** : M3 gagne entre +1 et +6 points sur M0 (la corrélation de
marge d'une couche à la suivante est de 0,058, ce qui laisse peu à f2 ; f3 et f4 portent la seule
chance : la cascade passe par le cache) ; elle **ne passe pas** 80 %. Si M3 dépasse +10 points, je le
dirai comme une surprise et je le ferai juger avant d'en parler.

## 5. Les témoins, chacun prouvé capable de tomber

- **W1, l'identité** : M1 doit redonner M0 à l'unité près (même classement, les ex aequo départagés
  par l'indice de cellule). Cassure : M1 entraîné sur y mélangé doit s'effondrer vers 10 % ± 2.
- **W2, le faux indice** : f2, f3, f4 permutés au hasard entre les cellules d'une même couche (graine
  20261026) : le gain de M3 sur M0 doit tomber dans ± 1,5 point de 0.
- **W3, l'indice oracle** : f2 remplacé par « il y a une bascule vérifiée à (ℓ − 1, p) » (fuite
  volontaire de la vérité) : le gain doit dépasser **15 points**. Il prouve que cet instrument *voit*
  un indice quand il existe ; sans lui, un gain nul ne voudrait rien dire.
- **W4, l'étiquette mélangée** : y permuté dans les cellules d'entraînement (test intact) : b(M3) =
  10 % ± 2.

## 6. Second chemin, indépendant, pour le chiffre principal b(M3) et b(M0)

- **Comptage** : les scores de test de chaque pli sont écrits en CSV ; un second programme, en Python
  pur (modules `struct` et `csv`, sans numpy, sans le code de la piste), relit les journaux A et B,
  recalcule les étiquettes et les comptes de cellules attrapées par classement explicite des scores
  (comme `juge.py`). Même nombre de bascules attrapées, à l'unité, par pli.
- **Autre classe de modèle** : P(bascule | classes) par comptage, sans régression : f1 en 20 quantiles
  d'entraînement, f2 en 4 quantiles, f4 en 4 classes (0 ; ]0 ; 0,05] ; ]0,05 ; 0,15] ; > 0,15), lissage
  de Laplace (+ 1 bascule, + 20 cellules), mêmes plis. Son gain doit tomber du même côté du seuil
  d'utilité que celui de la logistique et à moins de 3 points d'elle ; sinon **aucun gain ne sort**
  et le désaccord est publié.

## 7. Cohabitation

Priorité « sous la normale », un fil de calcul, jamais la carte, verrou de la carte jamais pris et
respecté (pause tant qu'il annonce abba, j1 ou vitesse). Données : les trois journaux du lot R et les
empreintes de `seuil-declare.md` § 1, vérifiées avant lecture.

## 8. Ce que cette mesure ne dit pas

Elle mesure la perturbation de deux rampes exactes, pas celle du mode rapide ; elle juge la
**détection**, pas la **réparation** ; un gain ici n'est pas un gain là-bas (G2 reste la mesure qui
décide). Les indices ont été choisis pour leur analogie avec le conflit accumulé, pas ajustés sur les
bascules ; aucun n'a été examiné avant cette déclaration.
