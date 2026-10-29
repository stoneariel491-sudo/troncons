# P5 : recuit et échange de répliques sur les symboles synonymes — seuils de l'étape 1, déclarés avant toute lecture

Déclaré le 2026-10-27, avant que mon code ait ouvert un seul octet de `calib/` ou `eval/` (je n'ai lu que les
documents, `synonyme.py` et la taille des fichiers). Les seuils de la piste (succès, mort) sont ceux de
`mesures/mimetisme/tri/00-seuils-declares.md` § P5 (commit ec124f5) ; ce fichier les applique à l'étape 1
(poids synthétiques) et fixe les détails que le tri laissait ouverts.

## Ce que l'étape 1 peut et ne peut pas conclure

Poids **synthétiques** gaussiens, H **réel**. Elle ne peut pas établir le succès de la piste (le succès
exige les poids réels, la KL, étape 2). Elle peut : (1) dire si l'instrument peut tomber ; (2) borner par le haut
le gain de l'optimiseur (si le gain sur la **calibration** est sous 3 %, la piste est morte : il n'y a rien à
prendre) ; (3) mesurer le sur-ajustement (calibration contre évaluation tenue à l'écart) ; (4) autoriser ou non
l'étape 2.

## Grandeur

- Instances : 8 couples (couche, expert) = couches {0, 8, 16, 23} × experts {0, 16} ; H d'entrée de gate/up
  construit comme `synonyme.py::hessienne` (pondération g², amortissement δ·moyenne(diag H)) sur les entrées
  de calibration (fenêtres 10-22) ; erreur d'évaluation = (w − q)ᵀ H_eval (w − q) avec H_eval construit sur les
  entrées d'évaluation (fenêtres 0-9) de **ce même expert**, sans amortissement, normalisé par w ᵀ H_eval w
  (erreur relative de sortie). 256 rangées synthétiques par instance (réduit si le témoin de durée l'impose, dit).
- Poids : gaussiens i.i.d. par rangée, quantifiés MXFP4 (échelle de bloc 2^(⌊log2 amax⌋ − 3) en grandeurs
  doublées, code le plus proche parmi {0,1,2,3,4,6,8,12}) : c'est la matrice W que la mutation voit.
- Grille de choix : les 8 niveaux ±c_k · échelle, c = (0,4743 ; 2,8486 ; 6,8372 ; 12), centres de `centres.json`.
- Optimiseurs : Babai = `synonyme.py::choisir` (la rétroaction actuelle, signe fixé par w) ; descente cyclique de
  coordonnées (CD) partant de Babai, 8 niveaux dont les deux signes ; échange de répliques (PT) à 8
  températures, bain thermique, partant de Babai, puis trempe à T = 0 du meilleur état.
- **Débit** : entropie d'ordre zéro H0 des symboles de la matrice (le même estimateur que 07), longueurs de
  code ℓ fixées par l'histogramme de la frontière. **À débit égal** = comparaison sur la courbe (H0, erreur)
  balayée en λ, au H0 du point Babai λ = 0 du même H, tolérance ±0,005 bit ; interpolation linéaire, jamais
  d'extrapolation (si le point cible est hors de la courbe de la méthode, la ligne est « non comparable »).
- Amortissement : δ = 1 (le réglage de la mutation déployée) ; sensibilité à δ = 0,1 (plus de rang libre, plus de
  sur-ajustement attendu), déclarée.

## Seuils de l'étape 1 (dérivés des seuils de la piste)

- **Autorise l'étape 2** : gain de l'évaluation tenue à l'écart ≥ 10 % (à débit égal ±0,005 bit) sur ≥ 6 des 8
  instances, pour PT ou CD. C'est le seuil de succès de la piste appliqué aux instances synthétiques.
- **Piste morte à l'étape 1** : gain sur la calibration < 3 % (médiane des 8 instances) ; ou gain de
  l'évaluation tenue à l'écart < 3 % en médiane, ou négatif sur ≥ 4 instances (sur-ajustement).
- **Ouvert** : entre les deux ; on le dit, avec le cahier de l'étape 2.
- **Rapport de sur-ajustement** r = (gain calibration) / (gain évaluation), rapporté tel quel, sans seuil.

## Témoins (tous déclarés avant d'être lancés)

- **W1, force brute** : 10 poids × 5 niveaux ({−2, −1, 0, 1, 2}·Δ, w gaussien), 5^10 = 9 765 625 états par
  instance, énumérés en entier (code Rust, second énumérateur en Python sur 20 instances). Parmi 1 000 H
  corrélés (spectre log-uniforme sur 3 décades, base orthogonale aléatoire) : (a) le PT retrouve l'optimum exact
  (énergie égale à 1e-9 près) sur **toutes** les instances (si une seule échoue, le PT est réglé trop court pour
  être crédité en dimension 2 880, dit tel quel) ; (b) il existe **au moins une** instance où Babai ne trouve
  pas l'optimum (sinon l'instrument ne peut pas tomber et la piste s'arrête là) ; on rapporte combien.
- **W2, cassures** : (i) PT à 0 balayage doit rendre Babai exactement (énergie égale à 1e-12) ; (ii) PT à
  températures gelées (T = 1e-9) pendant les mêmes balayages doit échouer sur au moins une des instances
  où Babai échoue (il ne doit pas retrouver l'optimum partout) ; (iii) H permuté (colonnes mélangées) : l'énergie
  de l'état trouvé sous le vrai H doit être strictement plus haute que l'optimum.
- **W3, second chemin** : décodage par sphère (Fincke-Pohst, énumération exhaustive bornée par le rayon de Babai)
  à n = 16 sur dix instances avec les 8 niveaux réels et un sous-bloc 16 × 16 réel de H : le PT doit retrouver
  l'énergie du décodeur par sphère (1e-9 relatif). Le chiffre principal (gain d'évaluation) est aussi recalculé
  par un second chemin : erreur calculée à partir des entrées X directement (Σ_i g_i² ‖(W − Ŵ) x_i‖²), non par
  la forme quadratique de H ; les deux doivent s'accorder à 1e-6 relatif.
- **W4, identité de Babai** : mon Babai générique (écrit pour les témoins) rend les mêmes symboles que
  `synonyme.py::choisir` sur une instance de 256 colonnes (0 symbole différent).

## Ce qui arrête l'étape 2

Le verrou `~/dev/verrou-carte.txt` existait à 00 h 45 (séance disque ABBA du juge de placement).
L'étape 2 lit ~100 Mo de fichier modèle et demande l'accord de l'orchestrateur : elle ne se lance pas sous le
verrou. Si le verrou est présent à la fin de l'étape 1, je rends le cahier de l'étape 2.

## Addendum du 2026-10-27 (avant le premier lancement sur les 8 instances ; après les témoins W1-W4, un pilote de 16 rangées sur L8-E0 et W3)

Ce que le pilote (L8, expert 0, 16 rangées, δ = 1) m'a appris et qui change des détails, pas les seuils :
la machinerie tourne (erreur du noyau = erreur de numpy à 1e-15 ; Babai ÷1,65 contre la frontière, accord avec
l'÷1,57 de 07 § 2) ; la précision de débit : λ (unité 07) déplace H0 de moins de 0,01 bit entre 0 et 0,4, donc le
débit égal ±0,005 bit est tenu directement à λ = 0 ou 0,2 ; le PT à 8 températures échange à 12-22 %.
- **Mesure de l'étape 1** : 64 rangées par instance (au lieu de 256 : le PT coûte ~70 ms par rangée-balayage), PT à
  40 balayages, 8 températures de 0,02 à 1,0 fois l'erreur moyenne par poids de Babai, trempe à T = 0 sur le
  meilleur état ; CD = descente cyclique depuis Babai jusqu'à ne plus changer (≤ 30 balayages).
- **Point de comparaison du chiffre principal** : Babai à λ = 0 (ce que le fichier déployé est) contre CD et PT à
  λ = 0 puis à λ = 0,2 ; est « à débit égal » toute paire dont |H0(méthode) − H0(Babai λ = 0)| ≤ 0,005 bit
  (rapporté ligne à ligne ; une paire hors tolérance est notée non comparable et ne compte pas). Chiffre
  principal = le meilleur des deux points λ de la méthode, tous deux à débit égal.
- **Sensibilité à l'amortissement** : δ = 1 (tête de série, c'est le réglage déployé), δ = 0,3 et δ = 0,1 (lignes
  de sensibilité ; le seuil de succès ne se lit que sur δ = 1 ; on rapporte en plus, pour chaque méthode, le δ
  qui minimise l'erreur d'évaluation moyenne sur les 8 instances, pour dire si un meilleur optimiseur change le
  meilleur δ).
- **Seuils inchangés.** Autorise l'étape 2 : gain d'évaluation ≥ 10 % sur ≥ 6 instances sur 8 (δ = 1). Mort :
  médiane < 3 % ou négatif sur ≥ 4. Pilote de 16 rangées : gain d'évaluation CD 8,1 à 9,6 %, PT 8,9 à 9,6 % ; il n'entre
  pas dans le verdict (échantillon de 16 rangées, une instance), il sert à régler la durée.
- **W3** (décodage par sphère n = 16, 10 instances) a été lancé avant ce passage : PT = sphère sur 10/10, Babai non
  optimal sur 6/10 (amortissement 0,01 pour que le bloc soit mal conditionné) : `W3-sphere-n16.json`.

## Addendum 2 du 2026-10-27 (après le verdict de l'étape 1, avant ce lancement) : exploration hors verdict, cible de l'amortissement

Constat de l'étape 1 à δ = 1 (verdict déclaré : OUVERT, gain d'évaluation CD 5,5 %, PT 6,8 %, 0 et 1 instance sur 8
au-dessus de 10 %) : la calibration baisse de ~52 à 55 % et l'évaluation de 5 à 7 % ; l'erreur d'évaluation vit dans le
noyau de la calibration (rang ≤ 762 à 1 329 sur 2 880). L'amortissement isotrope δ·moy(diag H)·I y met le même poids
partout ; les colonnes géantes (05 § 2.1 b) y pèsent pourtant bien plus. Exploration, **hors du verdict de P5** (elle
ne change pas l'optimiseur) : remplacer la cible isotrope par la cible diagonale, H_train = H_calib + δ·diag(H_calib),
δ ∈ {0,3 ; 1 ; 3}, Babai et CD (λ = 0, 64 rangées, mêmes 8 instances, mêmes poids synthétiques que l'étape 1).
- Grandeur : erreur d'évaluation / erreur d'évaluation de Babai à δ isotrope = 1 (le déployé), à débit égal ±0,005 bit.
- Seuil (le même que le succès de P5, appliqué à ce levier) : gain médian ≥ 10 % sur ≥ 6 instances sur 8 pour Babai
  seul (sans nouvel optimiseur) = le levier est l'amortissement, pas l'optimiseur ; sous 3 % ou en hausse = fermé.
- Témoin : δ → ∞ avec cible diagonale rend l'erreur d'une quantification sans corrélation (H = diag), donc ≥ la
  frontière pondérée ; cassure : cible diagonale permutée (mauvaises colonnes) doit être pire que l'isotrope.

## Addendum 3 du 2026-10-27 (avant ce lancement) : le mécanisme du sur-ajustement, testé en faisant varier N

Résultat de l'addendum 2 (cible diagonale) : fermé (Babai −2,3 % à δ = 1, CD +5,4 % au mieux, 0 instance sur 8 ≥ 10 % ;
la cassure à cible permutée donne −0,5 % : la diagonale ne vaut pas mieux qu'un tirage). Ce qui reste comme explication de
l'écart calibration/évaluation (52 % contre 5,5 %) : le rang du H de calibration (N = 762 à 1 329 entrées pour n = 2 880).
Test causal bon marché avec les captures existantes : **plus d'entrées d'entraînement, même test**.
- Régimes (mêmes 8 instances, mêmes poids synthétiques, δ = 1 isotrope, Babai et CD seulement, 64 rangées) :
  « test2 » : entraînement = calibration, test = seconde moitié des positions d'évaluation (fenêtres 5-9) ;
  « plus » : entraînement = calibration + première moitié des positions d'évaluation (fenêtres 0-4), même test.
- Grandeur : gain de CD contre Babai du même régime sur le test (à débit égal ±0,005), et erreur du test de chaque
  méthode rapportée à Babai « test2 ».
- Seuil : le mécanisme « le gain ne se transfère pas parce que N < n » est **soutenu** si le gain médian de CD sur le
  test monte d'au moins **2 points** de « test2 » à « plus » et monte sur ≥ 6 instances sur 8 ; **non soutenu** si la
  montée est < 0,5 point ou si elle baisse. Entre les deux : non tranché.
- Témoin : la cassure « test = une partie de l'entraînement » (test inclus dans l'entraînement) doit donner un gain de
  test proche du gain de calibration, ≥ 20 %.
