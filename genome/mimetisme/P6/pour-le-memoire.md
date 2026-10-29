# P6 pour le mémoire : dérivations, données, figures

Matière écrite en entier pour le rédacteur scientifique. Tous les chiffres viennent de
`mesures/mimetisme/P6/` ; les figures se régénèrent par `outils/mimetisme/P6/figures.py`. Les sources externes
marquées [mém.] n'ont pas été relues à la source : à vérifier avant de les citer.

## 1. Le modèle et ses grandeurs

Un accès a = (t, l, s) appelle l'expert x_a avec le poids de mélange w_a, avec Σ_s w(t,l,s) = 1 (softmax sur les
k = 4 scores retenus). Un **séjour** σ d'un expert dans le cache va de son entrée (un défaut) à son éviction ;
A(σ) est l'ensemble de ses accès, le premier étant le défaut. La politique ne lit pas le niveau, donc les
séjours sont les mêmes pour toutes les règles de fidélité.

Soit φ(σ) ∈ {E, F} le niveau (exact, rapide) d'un séjour, fixé à l'entrée par le portillon φ(σ) = F ⇔ w_{a₀(σ)} < θ.
Coût en octets, en unités d'un expert exact : c(σ) = ρ si F, 1 si E (ρ = 0,718). Énergie perturbée :

  E = Σ_σ 1[φ(σ) = F] Σ_{a ∈ A(σ)} w_a²   (règle « accepter »),   E_tout = Σ_a w_a².

L'hypothèse de travail est que l'écart de sortie de la couche à l'accès a est δ_a = w_a · ε_x, avec ε_x un écart
d'expert de variance commune ; la variance d'écart totale est alors σ_ε² Σ w_a² : l'énergie. **C'est une
hypothèse de petite perturbation, non la KL.**

Octets économisés : S = Σ_σ 1[φ = F](1 − ρ) / |Σ| = (1 − ρ) · f, avec f la part de séjours servis en rapide.
Le tout-rapide (θ > 1) donne S_tout = 1 − ρ = 0,282 et E = E_tout. Donc

  **r(θ) = (E / E_tout) / (S / S_tout) = (E / E_tout) / f.**

**Proposition 1 (cassure par le hasard).** Si φ est tiré indépendamment des poids avec P(F) = f, alors
E[E] = f · E_tout et E[r] = 1. *Preuve.* E = Σ_σ φ(σ)·e(σ) avec e(σ) = Σ_{A(σ)} w² indépendant de φ(σ) :
E[E] = f Σ_σ e(σ) = f · E_tout. ∎ Mesuré : 1,0001 ± 0,023 (50 tirages, 7 traces, θ = 0,20).

**Proposition 2 (la porte seule).** Soit p(θ) = P(w < θ) et Ê(θ) = E[w² ; w < θ] / E[w²] la part d'énergie des
poids sous θ. Pour un comptage sans portage où la sélection est indépendante de l'état du cache,
r₀(θ) = Ê(θ) / p(θ) < 1 dès que la loi de w est non dégénérée (w² croissante). Mesuré : r₀(0,20) = 0,414,
r₀(0,25) = 0,614. Le comptage sans portage, avec les poids mélangés par couche, vaut 0,1855 contre 0,1845 sans
mélange : le défaut n'est pas corrélé au petit poids, et **le gain de la porte vient de la loi de w, non du cache**.

**Décomposition du portage.** E = E_porte + E_suite : E_porte = Σ_σ F · w_{a₀}² (l'accès qui fixe l'étiquette),
E_suite = le reste du séjour. Mesuré à θ = 0,20, génération du 120b : E_porte/E_tout = 0,0476, E_suite/E_tout =
0,1609 ; la suite porte 77 % de l'énergie. La corrélation du poids d'entrée avec le poids moyen des succès suivants
est 0,34 (prose-en) et 0,25 (wiki) : le poids d'entrée prédit mal la suite.

**Règle « remonter à θ' ».** Au premier succès d'un séjour F de poids w ≥ θ', l'exact entier est relu (coût 1), le
séjour passe à E, l'accès est servi exact. Il faut relire l'exact entier : le fichier rapide n'est pas emboîté dans
l'exact. Octets d'un séjour : ρ + 1[∃ a ≥ 2, w_a ≥ θ'] (le défaut à ρ, la relecture à 1). S baisse et r baisse :
r(θ = 0,20, remonter à 0,30 / 0,40 / 0,50) = 0,442 / 0,539 / 0,612 contre 0,688 (accepter), pour S = 7,37 / 8,10 /
8,41 / 8,55 %.

**Borne clairvoyante.** φ*(σ) = F ⇔ max_{a ∈ A(σ)} w_a < θ. Pour un octet donné elle minimise l'énergie parmi
tous les portillons qui servent le séjour entier au même niveau ; elle borne donc toute règle de prédiction.
Mesuré : r* = 0,185 (θ = 0,20, cumul). Écart au portillon causal : un facteur 3,7.

## 2. Variante B : préremplissage par lot

Soit un lot β de n_β jetons, une couche l, un expert x appelé par les jetons J(β, l, x) avec les poids
(w_j)_{j ∈ J}. L'unité de lecture est la clé u = (β, l, x) ; un lot lit chaque clé une fois (pas de cache utile :
4 608 experts, 323 emplacements, et ≈ 90 clés par couche et par lot de 512 jetons). On ordonne les clés par un
score σ_u et on lit en rapide les f plus petites. Trois scores : le maximum m_u = max_j w_j (règle A), la masse
M_u = Σ_j w_j (règle B), l'énergie e_u = Σ_j w_j² (règle C, qui est l'ordre optimal pour l'énergie à f fixé).
Énergie : E = Σ_{u ∈ F} e_u ; r = (E/E_tout)/f.

**Proposition 3.** À f fixé, la règle C (tri par e_u) minimise E parmi toutes les parties de f|U| clés ; elle est
donc une borne inférieure de A et B. *Preuve.* Le choix de f|U| clés minimisant une somme additive est la partie
des f|U| plus petits termes. ∎ Mesuré : r_C ≤ r_B ≤ r_A partout (S = 8 %, 512 : code 0,058 / 0,060 / 0,093).
Le maximum m_u est un mauvais substitut de e_u parce qu'il ignore le nombre d'appels : e_u ≥ m_u² et
e_u ≤ n_u · m_u² ; la masse M_u = n_u · w̄_u compte les appels. L'écart r_B/r_A = 0,64 à 512 jetons (0,70 à 256,
0,74 à 128) croît avec la taille du lot, puisque n_u croît avec elle.

## 3. KL(f) : ce que l'étape 0 donne, et son hypothèse

Extrémités mesurées (juge, 20b, fenêtres neuves) : 0,0044 (tout-exact) et 0,1448 à 0,145 (tout-rapide). Sous
l'hypothèse **[hyp.]** KL(f) − KL(0) = (KL(1) − KL(0)) · E(f)/E_tout, la courbe suit la courbe d'énergie
(`courbe-plan-decodage.csv`, colonne KL_hyp_lineaire). La convexité due aux bascules de routage (96,5 % de la KL
vient d'elles, 05 § 3.1) pourrait la rendre plus favorable (KL(E) sous la droite) ; une saturation la rendrait moins
favorable. À l'étape 1 on mesure les points (f, KL) et on tire la forme.

## 4. Figures (existantes et à faire)

Existantes, tirées des JSON par script : `figures/plan-octets-energie.png` (le plan octets économisés – énergie
perturbée : la diagonale du tout-rapide proportionnel, accepter, remonter à 0,40, la borne clairvoyante,
la masse agrégée au préremplissage ; plus la courbe est basse, moins la perte coûte par octet) ;
`figures/r-selon-theta.png` (r selon θ pour les quatre règles et la borne, barres à 1 sigma).
Données : `courbe-plan-decodage.csv`, `courbe-plan-prefill-B.csv`.

À faire, dans l'esprit « espaces latents, transformations, topologie » :
- **Le simplexe de mélange.** Les quatre poids d'un (t, l) vivent dans le simplexe Δ³ (un tétraèdre) ; la porte
  « w_i < θ » est le demi-espace situé sous la face w_i = θ. Projeter les 36 864 points d'une génération (chaque
  (t, l) est un point de Δ³, triés par rang) dans le tétraèdre, colorer par le niveau servi, montrer les quatre
  plans w_i = 0,20 qui découpent la région « rapide ». C'est la forme de la porte, et elle fait voir que la loi des
  poids est un petit nuage proche du centre (0,25, 0,25, 0,25, 0,25) : d'où le faible écart-type des poids moyens.
- **La transformation d'un séjour** : un diagramme en bandes du temps (jeton) contre l'expert, chaque séjour une
  barre colorée par son niveau, avec les relectures en marque : on voit que les séjours F sont courts (1,9 à
  3,9 accès) et que les remontées frappent les longs.
- **La surface de Fermi** (source physique #3) : l'occupation f(ε) = 1/(e^{(ε−μ)/T}+1) d'un système à quatre
  niveaux est le softmax des scores du routeur ; μ est le niveau de coupure du k-ième score. Une figure
  schématique du softmax comme loi de Fermi-Dirac, avec le seuil θ comme occupation minimale.

## 5. Sources

- Voisines de la même idée (dégrader selon l'importance) : HOBBIT (arXiv 2411.01433) et Lu et al. (arXiv 2402.14800)
  [mém., titres et auteurs non relus à la source] ; fovéation (vision) et raffinement itératif en précision
  mixte (Haidar, Tomov, Dongarra, Higham, SC18) [mém.]. À relire avant citation : `memoire/sources/p6.bib` ne
  contient que les clés à vérifier.
- Seuil, témoins et amendement : `mesures/mimetisme/P6/00-seuils-declares.md`.
- Cahier de l'étape 1 : `resultat.md` § 6.
