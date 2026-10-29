# P4 pour le mémoire : calibration conforme du préchargement, simulateur, figures

Tout chiffre vient de `mesures/mimetisme/P4/` ; la figure se régénère par `outils/mimetisme/P4/p4_figures.py`.

## 1. Le problème posé en équations

Un jeton t traverse L couches ; à la couche l il demande un ensemble S(t,l) de k experts. Le cache C(g) (LRU global, g = t L + l) laisse un ensemble de défauts
F(g) = S(g) \ C(g). Une lecture de disque coûte tau = 4,1 ms. Un prédicteur, à la fin du routage de la couche l0, propose pour la couche l = l0 + d une liste ordonnée
de candidats e avec une confiance s(e) dans [0,1] (part pondérée des 20 voisins de chemin qui portent e). Un chargement est un candidat absent du cache avec s >= theta.
Précision p(theta) = P(e dans S | e charge, s >= theta). Couverture u(theta) = E[#chargements justes] / E[#défauts].

## 2. Calibration conforme fendue (la garantie)

Calibration : n(theta) chargements de confiance >= theta, x(theta) justes, sur la moitié de calibration. Borne de Clopper-Pearson unilatérale de niveau 1 - delta :
LB(theta) = B^{-1}(delta ; x, n - x + 1) (quantile de la loi bêta), qui vérifie P(p(theta) >= LB(theta)) >= 1 - delta si les n étiquettes sont indépendantes de loi commune.
On veut p >= 0,9 : on teste H_theta : p(theta) < 0,9 contre LB(theta) >= 0,9, **séquence fixe** du haut vers le bas de la grille (pas de 0,02, départ au plus haut seuil
à n >= 30), arrêt au premier échec. Le contrôle du taux d'erreur de famille d'une séquence fixe fait que la sélection de theta* ne coûte aucune correction de multiplicité (principe
de *Learn then Test*, Angelopoulos, Bates, Candès, Jordan, Lei, arXiv:2110.01052 [lu, résumé]). Hypothèse : échangeabilité. Elle est fausse pour des jetons ordonnés (l'historique de voisins
grandit) ; l'écart va dans le bon sens (précision de test >= précision de calibration dans 4 sessions sur 4 : 0,919 / 0,905 / 0,947 / 0,922 contre 0,911 / 0,904 / 0,918 / 0,914), sans le démontrer.
Cassure mesurée : avec les étiquettes mélangées, aucune calibration ne trouve de seuil (7 sessions sur 7 au 120b).

## 3. Le simulateur et le gain, dérivés

Temps d'une couche (sans prédiction) : t_l = a + (n_d tau + (n_d > 0) q) + c + o, avec n_d le nombre de défauts, q = 1,0 + 0,85 ms (copie, décodage), a + c = w/L = 2,22 ms
(80 ms par jeton), o = -0,137 ms (écart d'étalonnage pour que la base fasse 460 ms). Une lecture de fond ne démarre que dans une fenêtre de calcul, mais finit sa course :
elle retarde la demande suivante de delta = tau - (c + a) = 4,1 - 2,2 = 1,9 ms. Une lecture juste économise tau à la demande ; une lecture fausse ne rapporte rien et coûte delta.
Donc, avec U justes et C chargements par moitié de test :
  économie = U tau - C delta ;  gain = économie / (T_base - économie).
Pour le code : U = 12 770, C = 13 892, T_base = 516,7 ms x 1 271 jetons, soit 4,12 % ; la simulation donne 3,58 %. Quand delta -> 0 on retrouve la formule du tri, qui surestime 2 à 2,4 fois.
Plafond (prédicteur parfait, d = 1, tous les défauts) : x1,1786 dans le simulateur, x1,21 par le calcul de O § 9.2.
La formule de O, gain = f - (1 - p)/p x part_disque, avec p = 0,918, f = 80/460 = 0,174, part_disque = 0,69, donne +10 à +13 % : elle suppose que toute lecture juste se cache
entièrement, ce qui n'est pas le cas quand la fenêtre (2,2 ms) est plus courte que la lecture (4,1 ms).

## 4. Figures et données

- `figures/p4-precision-couverture-gain.png` (deux panneaux). Gauche : **courbe précision-couverture** par session, du test, avec theta* en point ; ce que la figure dit de vrai :
  tenir 0,9 de précision coûte la couverture (8 à 17 %), la pente est la même pour les quatre genres. Droite : gain simulé contre le seuil +5 % et la mort +2 %.
- `figures/p4-precision-couverture.csv` : par session et par theta, n et x de calibration, borne de Clopper-Pearson, n et x de test, précision et couverture.
- `figures/p4-gains-par-session.csv` : tous les gains (P, P purge totale, P FIFO, R), les theta et les octets.
- Espace latent à montrer ensuite, tiré des données commitées : la projection (ACP) des chemins de jetons (vecteur multi-hot des couches 0 à l0, 4 608 dimensions), colorée par
  moitié calibration / test et par confiance du premier candidat ; elle montrerait si les voisins de test tombent dans la région déjà vue (la raison pour laquelle la précision tient en ligne et pas hors texte).
  Non produite ici (pas de temps) ; script à écrire sur `p4.multihot`.
- Chronogramme à tracer : une couche avec et sans lecture de fond (disque, copie-décodage, calcul), montrant le débordement de 1,9 ms ; les événements sont exactement ceux de `p4.des`.

## 5. Sources

Angelopoulos, Bates, *A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification*, arXiv:2107.07511 (2021, v6 2022) ; Angelopoulos, Bates, Candès, Jordan, Lei,
*Learn then Test*, arXiv:2110.01052 (3 octobre 2021) ; Shalunov, Hazel, Iyengar, Kuehlewind, LEDBAT, RFC 6817 (décembre 2012). Lues le 2026-10-27 sur les pages de résumé. BibTeX à ajouter à `memoire/sources/` par le rédacteur.
Clopper et Pearson (1934) [mém.].
