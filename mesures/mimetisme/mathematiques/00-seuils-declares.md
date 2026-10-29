# Seuils déclarés avant toute lecture de données (éclaireur « mathématiques et théorie de l'information »)

Écrit le 2026-10-26, commité avant que tout outil de ce rôle ait lu une trace. Deux mesures, toutes
deux sur des fichiers déjà commités (`mesures/localite-gpt-oss/traces-120b/traces-120b.tar.xz`,
extraits dans le répertoire temporaire de la session), sans carte graphique, un seul fil, priorité
sous la normale, aucun fichier modèle ouvert.

Données : sept traces de lecture du 120b (code, dialogue, prose-en, prose-fr, wiki : 10 669 jetons) et
deux traces de génération (wiki, prose-en : 256 jetons chacune). Une ligne = un jeton ; 36 couches
séparées par « | » ; 4 experts par couche sur 128. Modèle de cache = celui du projet
(`outils/gptoss_localite.py` : un cache global de N emplacements (couche, expert), groupes de 4
accès, éviction après le groupe, le groupe courant protégé).

## M1 : un prédicteur causal par compression/prédiction (Vitter et Krishnan) mène-t-il un cache plus
près de Belady que LRU et LFU ?

**Grandeur** : taux de succès global à N = 323 emplacements (7 %, le budget de la base llama.cpp) et
N = 922 (20 %), politique PB (« Belady prédit ») : éviction du plus grand
`d + 36·(1 − p)/p`, où d = nombre d'accès avant la prochaine occasion d'usage de l'élément et p la
probabilité prédite qu'il soit demandé à cette occasion. `p` vient d'une régression logistique sur
des moyennes mobiles exponentielles des demandes passées de (couche, expert) à demi-vies 1, 3, 8, 24,
96 jetons, ajustée sur **deux traces d'apprentissage seulement** (prose-en lecture, code lecture) et
évaluée sur **cinq traces jamais vues à l'ajustement** (dialogue, prose-fr, wiki en lecture ; wiki et
prose-en en génération). Aucun paramètre n'est réglé sur les traces de test.

**Référence honnête (généreuse pour la base)** : `max(LRU, LFU)` avec, pour LFU, la meilleure demi-vie
de {2, 8, 32, 128} jetons *choisie sur la trace de test elle-même*.

**Seuil de décision** (dérivé de l'écart Belady − LFU mesuré par le projet sur 120b : 0,685 − 0,480 =
0,205 point à 323 emplacements, `cache-base-contre-optimum.json`) :
- **PROBABLE** : Δ = h(PB) − référence ≥ **+0,05** en moyenne sur les trois traces de lecture de test,
  à N = 323, ET ≥ **+0,03** sur chacune d'elles. Un point de succès vaut 1/(1 − h) ≈ 2 % de jetons par
  seconde au plafond disque ; +0,05 ≈ 10 % de jetons par seconde. En dessous, le gain se noie dans le
  bruit de disque de 1 à 5 % que le projet mesure.
- **Neutre** : Δ < +0,02. **Intermédiaire** : entre les deux.

**Témoins** (réponse connue d'avance) :
- T1 : mon chemin d'appel des politiques du projet (LRU, LFU demi-vie 8, statique oracle, Belady)
  redonne à 10⁻⁹ près les quatre nombres de `cache-base-contre-optimum.json` pour le 120b
  (0,39201 ; 0,48036 ; 0,49973 ; 0,68446) sur `w120b.wiki.generation.trace`, N = 323.
- T2 (l'instrument sait voir un gros gain quand l'information existe) : PB avec `p` = l'indicateur
  vrai du prochain jeton (oracle de un jeton) doit dépasser la référence de **au moins +0,10**.
- T3 (cassure) : l'ordre des jetons de chaque trace de test est mélangé (graine 20261026) ; Δ doit
  tomber sous **+0,01**. Si T3 ne tombe pas, l'avantage vient d'autre chose que de l'ordre.

**Prédiction écrite avant la lecture** : Δ entre +0,01 et +0,04 (il manque à PB le contenu du jeton
courant ; la récence est déjà dans LFU à demi-vie 8) ; la piste ne passe probablement pas.

## M2 : l'union des experts sur T jetons consécutifs plafonne-t-elle la vérification groupée
(décodage spéculatif, brouillon gratuit et parfait) ?

**Grandeur** : par couche, `u(T) = E|U_T| / (4T)`, avec U_T l'ensemble des experts choisis par T jetons
consécutifs (fenêtres glissantes sur les sept traces de lecture), et le plafond de gain
`G(T) = 4T / E|U_T| = 1/u(T)` : le nombre d'octets lus par jeton validé, sans cache, divisé par celui
d'une vérification groupée de T jetons, si le brouillon était gratuit et accepté à 100 %. Avec cache
et acceptation partielle le gain réel est plus bas : G(T) est un plafond.

**Seuil de décision** : la voie « vérification groupée » est **tuée pour tout brouillon, même gratuit**
si G(4) < **1,5** ou G(8) < **2,0** (en dessous, le brouillon le plus parfait ne rend pas ce que le
projet a déjà obtenu d'autres leviers, ×1,28 du mode rapide ; au-dessus, elle reste ouverte et c'est
le brouillon qui décide).

**Témoins** : W1 routage uniforme i.i.d. (4 sur 128) : `E|U_T| = 128·(1 − (1 − 4/128)^T)` à 3
écarts-types ; W2 routage figé (même ensemble à chaque jeton) : G(T) = T exactement ; W3 cassure :
ordre des jetons mélangé → G(T) doit rejoindre la courbe uniforme à popularité réelle (calculée par
tirage), sans quoi l'instrument ne voit pas l'ordre.

**Prédiction écrite avant la lecture** : G(4) ≈ 1,4 à 1,6 ; G(8) ≈ 1,7 à 2,1 (réutilisation adjacente
0,50 mesurée sur le 20b) : près des seuils, sans certitude.

## Amendement du 2026-10-26 (écrit après la première ligne de résultats de M1, avant les suivantes)

Le témoin T2 tel que déclaré (PB avec `p` = indicateur vrai du prochain jeton, et rien d'autre) **est
tombé à la première trace** : 0,5334 contre une référence de 0,5745 (dialogue, N = 323). Ce n'est pas un
défaut du cache, c'est un défaut du témoin : un oracle d'un seul jeton ne dit rien de la popularité des
éléments qui ne sont pas demandés au jeton suivant, et PB les range alors au hasard, là où LFU a une
information. T2 n'a donc pas montré que l'instrument voit un grand gain ; il a montré que mon oracle
était mal posé. Remplacement, déclaré maintenant : **T2bis** = PB avec `p` = le prédicteur appris,
relevé à 1 − 10⁻³ pour tout élément réellement demandé à l'occasion suivante (oracle d'un jeton qui
garde la popularité du prédicteur). Seuil de T2bis : au moins **+0,05** sur la référence, dialogue,
N = 323. S'il tombe sous +0,05, l'instrument ne sait pas voir un gain de cet ordre avec un jeton
d'avance, et le verdict de M1 (Δ de PB) devient « non concluant » et non « neutre ». T2 (oracle seul)
est conservé dans le journal, marqué tombé.

## M3 (descriptive, ajoutée le 2026-10-27 avant lecture, aucun verdict)

Sur les journaux de routage du 20b (`mesures/moteur/R/r1/routage/ref-openai-bis-20b.bin`, 24 couches ×
5 110 positions, marge entre le 4e et le 5e logit biaisé) : la part des (couche, position) de marge
inférieure à β pour β ∈ {0,01 ; 0,03 ; 0,1 ; 0,3}. Sert uniquement à borner, pour le routage conditionné
par le cache (MoCE), le gain de succès qu'un échange du 4e expert contre le 5e peut rendre :
`gain ≤ part(β)/4` points de succès (un seul des quatre accès d'une cellule change). Aucun seuil de
décision : c'est une borne de calcul, elle ne dit pas la perte de qualité.
