# Éclaireur Terre, climat et cosmos : seuils déclarés avant toute lecture de données

Écrit le 2026-10-26, avant que le moindre fichier de traces soit lu par un outil de ce rôle. Seules les
valeurs publiées du dépôt (`mesures/gpt-oss.md` § 6) ont été lues. Le verrou de la carte existe
(`dev/verrou-carte.txt`, séance du juge de placement) : cet éclaireur ne lit aucun fichier de modèle ;
il travaille sur les traces de routage commitées (`mesures/localite-gpt-oss/traces-*`), 2 fils au plus.

## Ce qui est jugé

Deux mécanismes, sur le cache d'experts global (un seul cache de N emplacements pour toutes les
couches, flux des accès dans l'ordre du calcul, comme `outils/gptoss_localite.py`, module importé tel
quel pour les politiques de base) :

- **M-A, allocation par utilité marginale entre couches** (inspirée de la géométrie hydraulique des
  rivières, Leopold et Maddock 1953, et du partage de cache par utilité marginale, Qureshi et Patt 2006) :
  un LRU par couche, avec n_l emplacements, Σ n_l = N, n_l ≥ k, choisis par programmation dynamique
  sur les courbes de succès par couche **calculées sur d'autres genres de texte** que celui qui est jugé.
- **M-B, score de réutilisation à noyau en loi de puissance** (Omori-Utsu, sismologie ; mémoire à
  plusieurs échelles de temps, Hasselmann 1976) : on évince l'expert de plus petit score
  S(x, t) = Σ_i (t − t_i + c)^(−p), t en jetons (fractionnaires : indice du groupe / L), sur les
  M = 32 derniers accès de x.

## Protocole

- Données : traces « lecture » de gpt-oss-20b (E = 32, k = 4, L = 24) et de gpt-oss-120b (E = 128, k = 4,
  L = 36), quatre genres (code, dialogue, prose-en, prose-fr).
- **Validation croisée par genre** : pour chaque genre G jugé, les paramètres (p, c pour M-B ; la demi-vie
  de la LFU de comparaison ; les courbes de M-A) sont réglés sur les **trois autres genres** ; le cache
  est vide au début de G. Aucun réglage ne voit le genre jugé.
- Budgets : f ∈ {0,10 ; 0,15 ; 0,20 ; 0,30} du nombre total d'experts, N = max(k, round(f·L·E)).
- Grille de M-B : p ∈ {0,5 ; 1 ; 1,5}, c ∈ {0,5 ; 2} jetons. Grille de la LFU de comparaison, pour qu'elle
  soit réglée aussi bien que M-B : demi-vie ∈ {2, 4, 8, 16, 32} jetons.
- Comparaison : taux de succès en accès (= en octets, experts de même taille), différence appariée par
  genre.

## Seuil de décision (dérivé d'une grandeur mesurée)

Les octets lus sur disque sont proportionnels au taux de défaut 1 − h. Le lot A, le plus gros gain
sans perte construit, vaut 3,4 % d'octets (juge de la construction § 6). À f = 0,20, 1 − h vaut
0,31 (20b, LFU) et 0,22 (120b, LRU) [mes., gpt-oss.md § 6] : **un point de succès retire 3,2 à 4,5 %
des octets**, l'échelle du lot A. D'où :

- **M-B passe** si, à f = 0,20 **et** f = 0,30, sur les **deux** modèles, sa différence moyenne
  appariée contre la **meilleure LFU réglée sur les autres genres** est ≥ +1,0 point de succès, et
  qu'elle est positive sur au moins 3 genres sur 4.
- **M-A passe** si, aux mêmes budgets et sur les deux modèles, sa différence moyenne appariée contre le
  **meilleur de {LRU global, LFU globale réglée, LRU par couche uniforme}** est ≥ +1,0 point, positive sur
  au moins 3 genres sur 4.
- Sinon la piste **tombe**, et le chiffre est publié tel quel. Prédiction écrite avant la lecture :
  M-A +1 à +4 points (les couches profondes n'ont besoin que de 14 experts sur 32 pour 95 % des accès,
  la couche 0 de 29 : une allocation uniforme gaspille) ; M-B +0 à +2 points (la LFU exponentielle
  réglée prend déjà l'essentiel de la popularité et de la récence).

## Témoins (capables de tomber)

- **T1, reproduction** : sur la trace « quatre genres » en ordre, 20b, f = 0,20, LRU, LFU (demi-vie 8) et
  Belady rendent 0,601, 0,684 et 0,814 à ± 0,002 (valeurs publiées, gpt-oss.md § 6.1). Si non, l'outil est
  faux et rien n'est publié.
- **T2, ordre mélangé** (cassure) : les jetons de chaque genre sont mélangés ; toute avance de M-B sur
  la LFU réglée doit alors tomber dans ± 0,5 point (plus de structure temporelle à lire). Une avance
  restante serait une fuite d'information : l'outil serait faux. M-A, qui lit la structure par couche
  et non l'ordre, peut garder son avance (il est dit comme tel).
- **T3, invariant** : Belady ≥ toutes les politiques à chaque budget et chaque genre.
- **T4, second chemin** pour M-B : une réimplémentation en Python pur, boucles explicites, sur le genre
  « code » du 20b à f = 0,20, qui doit rendre le même nombre de succès, au succès près.
- **T5, politique nulle** de M-A : une allocation uniforme (n_l = N/L) passée par le même code de DP doit
  redonner exactement le LRU par couche uniforme.

## Ce que cet éclaireur ne fait pas

Aucune mesure qui demande les poids ou l'état caché : elles sont décrites avec leur expérience dans
`eclaireur.md`, pour après la levée du verrou.

---

## Addendum du 2026-10-27, déclaré avant que la politique M-C ait tourné

Lecture faite entre-temps : SpecMD (Hoang, Jaiswal, Samragh, Cho, arXiv 2602.03921, 2026-02-03) mesure
qu'un LRU d'experts subit des « collisions » (un expert évincé puis redemandé dans le même passage
avant-arrière) et y répond par une éviction qui connaît la position de la couche. Cela rejoint un fait
déjà mesuré ici (le LRU partagé n'a aucun succès sous (L − 1)·k emplacements, gpt-oss.md § 7).

- **M-C, éviction par temps estimé jusqu'à la prochaine utilisation** (théorie du renouvellement avec un
  forçage périodique, par analogie avec les marées : la demande est périodique de période L groupes à
  l'intérieur d'un jeton). Pour un expert x de la couche l_x, avec le taux q̂_x (probabilité d'être choisi
  à un jeton, compteur décroissant de demi-vie h jetons, comme la LFU) et la couche courante l_c :
  τ_x = φ_x + L·(1/q̂_x − 1), φ_x = ((l_x − l_c − 1) mod L) + 1 groupes. On évince le plus grand τ_x
  (hors groupe courant). Demi-vie réglée sur les trois autres genres, même grille que la LFU.
- **Seuil** : le même que M-B (≥ +1,0 point contre la meilleure LFU réglée, à f = 0,20 et 0,30, sur les
  deux modèles, positive sur au moins 3 genres sur 4). Prédiction écrite : +1 à +5 points aux budgets
  serrés (0,10 et 0,15), +0 à +2 à 0,20 et 0,30 ; elle peut donc tomber au seuil déclaré tout en gagnant
  aux petits budgets, ce qui sera dit.
- **Témoin T6** : M-C avec φ_x remplacé par une constante doit redonner la LFU de même demi-vie à
  ± 0,002 de succès (même classement). **Cassure** : M-C avec φ_x calculé avec le mauvais sens
  (l_c − l_x) doit perdre contre M-C : si elle gagne autant, la phase ne sert à rien et l'outil le dit.
- Les mesures de M-A et M-B déjà lancées ne changent pas ; M-C n'a pas encore été exécutée.

---

## Addendum 2 du 2026-10-27 : eau-filling par l'usage (déclaré avant son exécution)

Dérivation écrite avant toute lecture [calc.]. Un expert x est lu sur le disque m_x fois (défauts de
cache) parmi p_x accès, à R_x bits par poids ; la qualité perdue est D = Σ p_x · σ² · 2^(−2 R_x) (distorsion
quadratique à haute résolution, pondérée par l'usage). On minimise les octets lus Σ m_x R_x à D fixée
(multiplicateur de Lagrange). Solution : 2^(−2 R_x) ∝ m_x / p_x. Contre un débit uniforme R₀ à même D,
le gain en bits par poids lu vaut **Δ = ½ · KL(m̂ ‖ p̂)** (en bits), où m̂ = m/Σm et p̂ = p/Σp sont la loi
des défauts et la loi des accès sur les experts (couche, indice). Les experts rarement en cache (m/p
grand) reçoivent moins de bits.

- **Mesure** : sur les traces (20b et 120b, quatre genres), cache global à f = 0,20, LRU et LFU de
  demi-vie 8, m_x et p_x comptés ; (i) Δ dans l'échantillon ; (ii) Δ **réalisé en validation croisée par
  genre** : la forme de l'allocation R_x vient des trois autres genres (lissage de Laplace +1 sur m et p),
  bornée à [1 ; 8] bits, décalée d'un scalaire pour retrouver la même D sur le genre jugé, puis
  Σ m'_x R_x comparé à R₀·Σ m'_x.
- **Seuil** : le gain réalisé doit valoir au moins **0,126 bit par poids lu** (le gain du lot A,
  3,8549 → 3,7292 bits, juge de la construction) sur les deux modèles, à f = 0,20, pour LRU et LFU.
- **Témoin** : un routage i.i.d. uniforme synthétique (tous les experts équiprobables) doit donner
  Δ ≈ 0 (à 0,01 bit près) ; la cassure est l'ordre des experts mélangé entre p et m (Δ doit alors tomber
  à zéro ou devenir négatif).
- **Limite écrite d'avance** : le modèle D ∝ 2^(−2R) est celui de la théorie débit-distorsion à haute
  résolution ; les mesures du projet disent que l'erreur d'expert ne prédit pas la KL (05 § 2.1 c). Un
  Δ qui passe le seuil est donc une borne haute à confirmer par une KL de bout en bout avec les poids,
  après la levée du verrou ; il ne vaut pas un résultat de qualité. Prédiction : Δ réalisé entre 0,05 et
  0,25 bit.
