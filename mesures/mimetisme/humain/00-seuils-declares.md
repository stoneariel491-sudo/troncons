# Seuils déclarés avant toute lecture (éclaireur « systèmes humains »), 2026-10-26

Écrit et commité avant que l'outil `outils/mimetisme/humain/` ait lu une trace. Ce que j'avais vu avant :
les courbes publiées du dépôt (succès de LRU/LFU/Belady, `mesures/localite-gpt-oss/figures/succes-*.csv`) et
la première ligne d'un fichier `.poids` (quatre poids qui somment à 1). Rien d'autre.

Données : traces de routage de lecture du dépôt (`traces-20b.tar.xz`, `traces-120b.tar.xz`), préfixes t20b et
t120b, flux global (jeton, couche, expert) dans l'ordre du calcul, comme `gptoss_localite.py`. Pas de modèle
lu, pas de carte, un seul fil.

## E1. Politique « mémoire humaine » (Anderson et Schooler 1991, ACT-R)

Score d'un expert i à l'instant t (en jetons) : B_i(t) = ln Σ_j (t − t_j + 1)^(−d), somme sur ses usages passés
(historique gardé aussi hors du cache, 32 derniers usages). Éviction : le score le plus bas parmi les résidents
hors du groupe courant. d = 0,5 fixé a priori (valeur canonique d'ACT-R) ; grille {0,2 ; 0,3 ; 0,5 ; 0,7 ; 1,0}
choisie sur le 20b seul, puis appliquée telle quelle au 120b (aucun réglage sur le 120b).

Référence à battre : LFU à demi-vie 8 jetons (publié : 0,47044 à 10 % sur le 20b pooled).

**Critère de succès (tout ensemble)** : (a) ACT-R moins LFU ≥ +0,020 à au moins 3 budgets sur 4 (10, 15, 20, 30 %)
sur chacun des deux modèles (trace pooled « tous.lecture ») ; (b) le signe est positif sur au moins 3 des 4 genres
pris seuls, à 15 et 20 %, sur le 20b ; (c) la vitesse plafond ∝ 1/(1 − h) : on rapporte le gain relatif.
Sinon : la piste tombe pour « gain sous 2 points » et c'est dit.

**Prédiction écrite avant** : gain entre 0 et +2 points ; je m'attends à ce que (a) échoue.

**Témoins** (déclarés, chacun doit pouvoir tomber) :
- W1 : mon pipeline rend LRU, LFU(hl 8) et Belady du CSV publié `succes-gpt-oss-20b-lecture.csv` à 1e-5 près
  (cassure : demi-vie 9 au lieu de 8, le témoin doit tomber).
- W2 : ACT-R restreint au dernier usage seul (historique de longueur 1) rend exactement le LRU (même taux
  de succès au succès près).
- W3 : Belady ≥ ACT-R à chaque budget (invariant).
- W4 (cassure) : ordre des jetons mélangé (graine 20261026) : l'écart ACT-R − LFU doit passer sous 0,010 en valeur
  absolue ; sinon l'avantage vient d'autre chose que de l'ordre et il est rejeté.

## E2. Tri par poids de mélange (triage médical), proxy de masse

Données : fichiers `.poids` appariés aux traces (softmax sur les 4 experts choisis, somme 1). Cache global LFU
(hl 8) à 20 % (budget atteignable pour le 120b) ; un « défaut » est un accès hors cache.

Mesure : (i) poids médian des défauts contre poids médian des succès ; (ii) politique « ne pas charger un défaut
de poids < θ » (sa masse est perdue, non renormalisée) ; courbe (part des défauts évités, masse moyenne perdue par
(jeton, couche)) pour θ de 0,01 à 0,3 ; (iii) base de hasard : mêmes nombres de défauts évités tirés au hasard.

**Critère « prometteur »** : à masse moyenne perdue ≤ 0,03 par (jeton, couche), au moins 25 % des octets de défauts
évités, ET le poids médian des défauts ≤ 0,8 × celui des succès. Un tel résultat ne dit rien de la qualité du texte
(la masse n'est pas la KL ; la queue de bascules, 05 § 2.2, peut tout défaire) : il désigne seulement la passe KL à faire.

**Témoin** : somme des poids de chaque ligne = 1 à 1e-3 (4 décimales) ; cassure : poids mélangés entre lignes,
le poids médian des défauts doit redevenir égal à celui des succès (à 0,02 près).

---

# Amendement du 2026-10-26 (après E1 lancée, avant toute lecture par les outils E3, E4, E5)

À ce moment, seules E1 (tournant) et les témoins W1, W2 de E1 avaient lu des traces ; E2 est écrite, non lancée.
Les trois mesures suivantes sont déclarées ici, avant que leur outil n'existe.

## E3. Allocation marginale par couche (METRIC, Sherbrooke 1968 ; partition à utilité, Qureshi et Patt 2006)

Courbes de défauts par couche en LRU (distances de pile de Mattson, exactes). Apprentissage sur trois genres, test
sur le quatrième (quatre découpes, moyenne). Allocation gloutonne de N emplacements entre les L couches par gain
marginal, plancher k = 4 par couche. Évaluation sur le genre de test : LRU par couche aux tailles allouées.
Comparés : (i) LRU par couche à tailles égales ; (ii) LFU (demi-vie 8) global publié, recalculé sur le même genre de test.
**Critère** : allocation − max((i), (ii)) ≥ +0,020 à au moins 2 budgets sur 3 (10, 15, 20 % ; 10 % pour le 120b
n'est pas évalué si N < L·k) sur chacun des deux modèles. Prédiction écrite : elle bat (i), pas (ii).
Témoin : taux de LRU par couche à tailles égales = celui de `chargement_localite.cache_lru` (1e-9) ; cassure :
allocation apprise sur le genre de test lui-même (doit être ≥ celle apprise ailleurs : sinon l'instrument est faux).

## E4. Précédent : prédiction des experts d'une couche lointaine par les voisins de chemin (raisonnement par cas)

Pour un jeton de test et une couche d'observation l0, on connaît les ensembles d'experts des couches 0 à l0. On prédit
les 4 experts de la couche l0 + d (d = 1, 2, 4) par vote pondéré des K = 20 jetons d'apprentissage les plus proches
(similarité = recouvrement cumulé des ensembles sur les couches 0 à l0). l0 = 3, 8, 14 (20b) ; 4, 12, 22 (120b).
Deux régimes : « autre genre » (apprentissage sur trois genres) et « en ligne » (jetons antérieurs du même texte,
hors le précédent). Rappel = |prédits ∩ vrais| / 4. Bases : (b1) les 4 experts les plus populaires de la couche (train) ;
(b2) l'ensemble du jeton précédent dans la même couche (réutilisation).
**Critère** : rappel(d = 2) ≥ max(b1, b2) + 0,15, moyenne sur l0 et genres, sur les deux modèles et dans le régime
« en ligne ». Prédiction écrite : il bat b1 de beaucoup, b2 de peu ; critère probablement manqué à d = 4.
Témoin : voisins tirés au hasard → rappel ≈ b1 (à 0,03 près) ; si non, instrument faux.
Précision : la prédiction n'utilise aucun état caché ; elle ne dit rien du prédicteur « routeur de la couche suivante » (non mesuré).

## E5. Classes ABC des experts (analyse ABC des stocks) et leur stabilité entre genres

Par couche, part des accès portée par les 50 % d'experts les moins utilisés (courbe de Lorenz) ; stabilité : corrélation
de rang de Spearman de la fréquence par expert entre genres (moyenne sur couches et paires de genres).
**Critère** (pour qu'une précision par classe d'usage vaille d'être jugée à la KL) : les 50 % d'experts les moins
utilisés portent ≤ 20 % des accès ET la corrélation de rang entre genres ≥ 0,7. Prédiction écrite : la part est de 25 à
35 % (échec), la stabilité entre 0,3 et 0,6 (échec) ; les mesures de localité ont déjà montré qu'un épinglage ne voyage pas
d'un genre à l'autre. Témoin : routage uniforme synthétique → part 50 %, Spearman ≈ 0 ; cassure : trace mélangée expert par expert.

---

# Amendement du 2026-10-27 : E6, arrêt séquentiel de groupe pour les juges de KL (O'Brien et Fleming 1979)

Déclaré avant l'écriture de l'outil. Données : les sept séries de différences appariées par fenêtre déjà commitées
(`mesures/genome/construction/juge/kl/apparie-*-par-fenetre.csv`, 10 fenêtres chacune), prises dans l'ordre des fenêtres.
Règle d'arrêt : regards après k = 4, 6, 8, 10 fenêtres ; statistique t_k = moyenne / (écart-type / √k) des k premières
fenêtres ; frontière c·√(10/k) (forme d'O'Brien-Fleming) ; la constante c est calibrée une fois par Monte-Carlo sur des
différences gaussiennes indépendantes (200 000 tirages, graine 20261027) pour que la probabilité de franchir à un regard
quelconque sous l'hypothèse nulle soit 0,05 (deux côtés). Témoin : sous nulle fraîche (autre graine), le taux de
franchissement est dans [0,03 ; 0,07] ; cassure : c divisé par 2 doit faire monter ce taux au-dessus de 0,15.
**Critère** : sur les séries dont le verdict à 10 fenêtres franchit la frontière finale, le nombre moyen de fenêtres
consommées est ≤ 7 sur 10 (au moins 30 % de fenêtres économisées), avec le même signe de verdict dans tous les cas.
Prédiction écrite : le critère est manqué ; seules les séries les plus nettes s'arrêtent avant 10.
Limite dite d'avance : les fenêtres ne sont pas indépendantes dans le temps de calcul réel (une fenêtre = une passe
du modèle) ; l'économie se compte en passes de référence évitées, pas en positions.
