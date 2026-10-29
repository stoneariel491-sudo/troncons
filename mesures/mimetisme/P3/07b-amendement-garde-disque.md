# P3, second tirage : amendement du 2026-10-27 à `07-second-tirage-declare.md`, garde disque en passe

Écrit avant : toute nouvelle passe du second tirage. Aucune mesure utilisable n'existe sur le nouveau texte (la seule passe lancée, `P0`,
a été arrêtée par mon garde-fou à la fenêtre 9/10 ; son `.kld` partiel a été effacé, sa trace n'existe pas, ses deux journaux sont
conservés sous `second-tirage/P0-tentative1*`).

## Ce qui change

Un seul réglage : **le garde-fou d'espace disque pendant une passe passe de 15 Go à 5 Go** (`P.C_MIN` dans
`outils/mimetisme/P3/p3_second_tirage.py`). Raison : une passe n'écrit qu'environ 1 Go (le `.kld`) ; la première tentative a été
arrêtée parce qu'un autre processus de la machine a écrit environ 13 Go de façon transitoire (C: libre tombé à 12,1 Go, remonté à
22,9 Go quelques minutes après l'arrêt). Le seuil utile est « de quoi finir la passe plus une marge », pas « de quoi satisfaire la
règle de départ ». Ce n'est **pas un seuil de mesure** : il ne touche ni les logits, ni les défauts, ni la KL.

Le message d'arrêt imprimé par le pilote (« C: libre sous 30 Go ») est le texte codé en dur du pilote du premier tirage ; la valeur
appliquée est celle de `P.C_MIN`.

## Ce qui ne change pas

Texte (`base-juge-20b.kld`, SHA-256 `2108487d…50a4`), moteur (commit `eb78770`), 238 emplacements, β₁ = 0,041, cassure β = 0,3,
seuils T1, T2, T3 et bornes décisives (§ 4), règle de lecture (§ 5), témoins et cassures (§ 6), prédictions chiffrées (§ 7), autres
garde-fous du § 8 (C: libre ≥ 25 Go au lancement dans le pilote, 18 Go entre deux passes, swap 4 Go, RAM, secteur). Les passes sont
lancées une fois chacune, sans rejeu pour choisir ; un rejeu n'a lieu que si une passe est coupée par une cause extérieure, et il est dit.
