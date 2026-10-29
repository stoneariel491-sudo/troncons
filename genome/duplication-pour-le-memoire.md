# Duplication de gènes : ce qu'il faut au mémoire

Pour le rédacteur scientifique. Tout chiffre vient d'un fichier commité ; chaque figure se régénère par
`outils/genome/duplication/synthese.py` (CSV) puis pgfplots lit le CSV tel quel.

## Place dans le mémoire

Une section du chapitre du génome des poids (« La duplication de gènes »), EN et FR, après l'état de
l'art (genome/00-etat-de-l-art.md § 2.3) et à côté des sujets genome et predictif-elagage. Longueur
visée : 8 à 12 pages par langue.

Plan proposé :
1. L'hypothèse (Stone, § 5 bis) et son énoncé en bits : I(enfant ; Π parent) contre 3,84.
2. La symétrie : proposition 1 (permutation des neurones), sa démonstration, et ce qu'elle fait aux blocs
   MXFP4 (schéma TikZ ci-dessous).
3. Instruments et témoins : écran, appariement hongrois, spectre de famille ; témoins plantés (0,9 et
   0,5) retrouvés, plancher du hasard calculé (0,092) et mesuré (0,084).
4. Le coût exact : D1, D2, D2b, D2c, avec les coûts ajoutés (log₂ 2880! = 28 948,6 bits) ; tableaux et
   verdicts.
5. La mutation tronquée et la sortie d'expert sur entrées réelles.
6. Les paralogues (substitution fonctionnelle) : tableau et figure.
7. L'arbre le plus économe (couche 23).
8. Pourquoi l'idée échoue : bruit et structure ; où chercher (l'usage, pas la parenté).
9. Ce qui pourrait être faux.

## Les énoncés formels (dérivations entières : genome/duplication-derivations.md)

- **Proposition 1** (invariance par permutation) : § 1 des dérivations.
- **Lemme 2** (gain gaussien d'un parent) : g(ρ) = −½ log₂(1 − ρ²), valable pour D < σ²(1 − ρ²) ; § 2.
- **Lemme 3** (plancher du hasard) : E max_N |cos| ≈ √(2 ln(2N)/n) ; 0,0916 pour N = 89 280, n = 2 880 ; § 2.
- **Proposition 4** (gain sans perte = information mutuelle conditionnelle), biais de Miller
  (K − 1)/(2N ln 2) ≤ 6,7·10⁻⁵ ; coûts ajoutés ; § 3.
- **Proposition 5** (reconstruction identique) : seul le débit change, gain = I(Q ; P′ | ctx) ; § 4.
- **Remarque 6** (pourquoi la prédiction soustraite perd sur une grille discrète) ; § 4.
- **Proposition 7** (arbre le plus économe = arbre couvrant de poids maximal, Kruskal) ; § 5.
- **Lemme 8** (erreur d'un paralogue) : ε = 1 − ρ_f² au β optimal ; § 6.

## Schéma TikZ à dessiner (la permutation et les blocs)

Trois matrices côte à côte : W_g (f × d) et W_u (f × d) avec deux rangées colorées échangées par Π
(flèches), les blocs de 32 tracés le long de chaque rangée (restent entiers) ; W_d (d × f) avec les deux
colonnes correspondantes échangées, les blocs de 32 tracés le long des rangées (traversés). Légende :
« la même Π sur les trois matrices ; la fonction est inchangée (proposition 1) ».

## Les figures (pgfplots, données commitées)

1. **Score de parenté par candidat** — `mesures/genome/duplication/csv/scores-parente.csv` : nuage
   (couche de l'enfant en abscisse, score_bits en ordonnée), trois marques selon `genre` (intra,
   voisine, meme_indice), une ligne horizontale au hasard de l'appariement (0,0016, `paires-temoin-
   planter-0.5.json`, `scores.hasard_moyen`) et une à 0,2075 (témoin planté). Échelle log en ordonnée.
2. **D1 par matrice : parent contre hasard** — `csv/d1-sans-perte.csv` : barres groupées (gain_parent,
   gain_hasard) par (couche, enfant, rôle), ligne du coût ajouté 2,64·10⁻³.
3. **Débit-distorsion d'une matrice** — `csv/rd-points.csv`, filtre couche = 8, enfant = 0, rôle = gate :
   courbes (eps, debit) pour `independant`, `mutation`, `contexte_parent` ; point de la base
   (0,04292 ; 2,6441) ; échelle log en abscisse. Montre la mutation soustraite au-dessus de l'ECSQ seule.
4. **Erreur de sortie** — `csv/t-o-sortie.csv` : barres par enfant (base_sortie, mutation_sortie,
   ecsq_sortie), et à part la mutation tronquée (tronquee_sortie) ; montre « même erreur de poids,
   erreurs de sortie différentes ».
5. **Paralogues par profondeur** — `csv/paralogues.csv` : boîtes de eps_beta et eps_hasard par couche
   (0, 8, 16, 23) ; second panneau : couche_substitue contre couche_retire (nuage, diagonale).
6. **Spectre de famille** (couche 12) — `spectre-c12.json` : R_iso, R_diag, R_klt et témoin par rôle
   (barres).

Exemple pgfplots (figure 2) :

```latex
\begin{tikzpicture}
\begin{axis}[ybar, bar width=2pt, ymode=log, ylabel={bit par poids},
  xlabel={matrice (couche, enfant, rôle)}, xtick=\empty, legend pos=north east]
\addplot table[x expr=\coordindex, y=gain_parent, col sep=comma]
  {mesures/genome/duplication/csv/d1-sans-perte.csv};
\addplot table[x expr=\coordindex, y=gain_hasard, col sep=comma]
  {mesures/genome/duplication/csv/d1-sans-perte.csv};
\draw[dashed] (axis cs:0,0.00264) -- (axis cs:47,0.00264);
\legend{parent apparié, parent de hasard}
\end{axis}
\end{tikzpicture}
```

## Les tableaux

Repris tels quels de `genome/duplication.md` § 2.2, 2.3, 2.4, 3, 4, 6 (et § 5 quand l'arbre est fini).

## Les sources (memoire/sources/genome-duplication.bib, plus les clés existantes)

ainsworth2022rebasin, entezari2021permutation (la symétrie de permutation et l'appariement de poids) ;
komatsuzaki2022upcycling (experts nés par copie : le cas où la duplication existerait) ;
li2023mcsmoe, chen2024hcsmoe (fusion d'experts sur BF16, genome-etat-de-l-art.bib) ;
kuhn1955hungarian, crouse2016assignment (l'affectation) ; kruskal1956 (l'arbre) ;
gu2003duplicate (robustesse des paralogues) ; ohno1970 (tome2-resultats.bib) ;
skliar2024cacheconditional (substitution d'experts selon le cache) ; openai2025gptoss (le modèle) ;
miller1955bias (biais de l'estimateur) ; Gish et Pierce 1968 (03-entropie.bib).

## « Ils posent le problème ainsi ; le terme qui nous manque ; celui qu'ils n'ont pas »

(Résumés de Git Re-Basin, MC-SMoE et Skliar et al. lus à la source, pages arXiv /abs, le 2026-10-17 ;
les articles entiers ne sont pas relus ici.)

- Git Re-Basin et Entezari et al. apparient les neurones de deux RÉSEAUX pour les fusionner ou les
  relier ; MC-SMoE commence par l'alignement des neurones par permutation des experts d'un MoE avant de les fusionner, jugés en
  précision de tâches. Le terme qui nous manquait : le débit, en bits par poids lus, d'un expert codé
  sachant un autre. Celui qu'ils n'ont pas : la mesure sur des codes de 4 bits, où l'information
  mutuelle se compte exactement, et la séparation entre la parenté propre et la structure commune à
  la couche (notre témoin du parent de hasard).
- Le routage conscient du cache (Skliar et al., sans réentraînement) favorise la réutilisation des
  experts déjà en mémoire et se juge en précision de tâches et en vitesse sur mobile ; nous mesurons la borne fonctionnelle de toute substitution
  (le meilleur paralogue, β optimal) et trouvons qu'elle ne fait jamais mieux que retirer l'expert.

## Ce qui pourrait être faux (à reprendre dans le mémoire)

genome/duplication.md § 9.

## Figure 7 (SOCLE du 2026-10-17 : espaces latents) — l'arbre phylogénétique des experts de la couche 23

Données : `mesures/genome/duplication/csv/phylogenie-c23-noeuds.csv` et `-aretes.csv`, outil
`outils/genome/duplication/figure_phylogenie.py`. Les 32 experts placés dans le plan par MDS classique
sur la distance d_ij = log₂(s_max / s_ij) (s : score d'appariement, 496 paires), les 31 arêtes de l'arbre
couvrant maximal tracées par-dessus, épaisseur proportionnelle au score, nœud de taille proportionnelle
au degré (le moyeu 31 au centre de quatre arêtes lourdes). **Fidélité, à écrire dans la légende** : le
plan garde 30,9 % de la variance des distances ; corrélation de Spearman entre distances du plan et
distances vraies 0,61 (témoin : distances permutées, 0,11) (`phylogenie-c23.json`). L'image est une
ombre partielle d'un espace de grande dimension : la légende le dit, et rappelle l'échelle (s_max =
0,089 bit ; hasard 0,0016).

```latex
\begin{tikzpicture}
\begin{axis}[axis equal, hide axis, width=12cm]
\addplot[no marks, line width=0.4pt] table[col sep=comma, x=xi, y=yi]
  {mesures/genome/duplication/csv/phylogenie-c23-aretes.csv}; % segments : une ligne par arête (à
  % tracer arête par arête avec \pgfplotstableforeachcolumnelement, épaisseur = score)
\addplot[only marks, scatter, point meta=\thisrow{degre}, scatter/use mapped color={fill=mapped color},
  visualization depends on={\thisrow{degre} \as \deg}, scatter/@pre marker code/.append style=
  {/tikz/mark size=1.2pt+0.6pt*\deg}] table[col sep=comma, x=x, y=y]
  {mesures/genome/duplication/csv/phylogenie-c23-noeuds.csv};
\end{axis}
\end{tikzpicture}
```
