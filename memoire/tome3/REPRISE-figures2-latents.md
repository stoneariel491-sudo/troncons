# Tome III, figures, second flux : reprise du rôle « latents » (2026-10-27)

Rôle : corriger le lot « espaces latents » (III-7.6, III-9.1 (c) devenue (d), III-9.7) d'après les juges du premier
flux. Fichiers du rôle, et eux seuls : `memoire/figures/tome3/latents-figures.tex`, `memoire/outils/tome3_latents.py`,
`memoire/figures/tome3/donnees/latents-*`, cette note ; en plus, deux phrases barrées dans la note du lot du premier
flux (`REPRISE-figures-latents.md`, M2 et M9 du juge des chiffres). Aucune passe du modèle, aucune carte : tout se
tire des fichiers commités.

## Fait
- **Commun porté** : `latents-figures.tex` charge `legende-tome3.tex` (donc la palette) ; plus aucune `SerieX` ni
  `latRose` ; couleurs par leur nom (`CouleurSynonyme`, `CouleurFrontiere`, `CouleurFrontiereMarque`, `CouleurExact`,
  `CouleurCategorieA`, `CouleurAutres`) et styles `t3` (`t3 frontiere`, `t3 synonyme`, `t3 frontiere point`,
  `t3 synonyme point`, `t3 graphe`, `t3 encart`, `t3 barres`, `t3 etiquette`, `t3 nombre`, `t3 titre panneau`,
  `t3 titre encart`, `t3 decimales y`). Légendes en G9 : `\Titre`, `\Legende` (tête en gras = l'idée, puis `\mes` ou
  `\mes\,\calc`), `\Source` ; le pilote appelle `\LegendeFigure{Latents…}`. `\LegendeCourteLatents*`,
  `\LegendeLatents*` « à l'ancienne » et `\LatPv` retirés (`\Pv`, `\LatPc` = « % » sans espace en anglais).
  Plus aucun `\tiny` (D25) ; halo sur toute étiquette posée dans un graphe (D28) ; césure interdite (D29).
- **G1 (III-9.1 (d), III-9.7)** : synonyme en `CouleurSynonyme` (SerieA, bleu), frontière en `CouleurFrontiere`
  (trait) et `CouleurFrontiereMarque` (losange gris foncé), exact en triangle `CouleurExact` ; colonnes « codon
  changé » en `CouleurSynonyme!10` ; la ligne « synonyme » de la bande en bleu ; niveaux ±c_k en tirets de la
  couleur frontière. Marques du dictionnaire (losange frontière, rond synonyme, triangle exact).
- **III-9.1 : le panneau du lot devient (d)** (décision : le lot synonyme a déjà (a), (b), (c) = part cumulée ; deux
  « (c) » pour une figure, relevé par le juge construction). Titre de panneau dessiné, légende « Panneau (d) de
  III-9.1 … panneaux (a) à (c) ». D18/M6 : la légende dit la notation de la bande (« +k », « −k » = niveau ±c_k, pas
  un zéro signé) et les flèches (de la valeur frontière à la valeur synonyme) ; les étiquettes de ligne disent
  « frontière ±k », « synonyme ±k ».
- **G2 (III-7.6), version « légendaire » du juge** : (a) ACP et (b) t-SNE en gris, les numéros des huit experts
  posés sur l'état de leur groupe le plus entouré des siens (moyenne des distances aux 30 plus proches voisins du
  groupe) ; (c) petits multiples 2 × 4 sur la t-SNE, un expert premier par panneau, ses états en `CouleurCategorieA`
  sur le nuage entier en `CouleurAutres`, « expert, part » dans le coin du panneau ; dans (a) et (b), deux noms
  qui se recouvrent sont écartés (boîtes de 10 % × 7,5 % de l'étendue, trait de rappel : dans l'ACP, 24 et 4, 31 et 27
  se cachaient). La couleur ne porte plus rien seule (la place dit
  l'expert) : le défaut deutéranope et gris disparaît. **La taille disparaît** ; à sa place, la marge de la couleur,
  z(1) − z(2) (M2 du juge, sortie (a)) : les 614 états sous son 10e centile (0,0155) en encre, dans toutes les
  cartes. Clé des tailles (M3) sans objet.
- **Le bord, mesuré deux fois** (`tome3_latents.py`, témoin B1) : part des 10 voisins (plan t-SNE) d'un autre expert
  premier, par classe de z(1) − z(2) : 0,700 / 0,627 / 0,474, **égale au dernier chiffre** à `bord_tsne` du juge
  (`outils/genome/tome3/juge-latents/juge-etats-marges.json`) ; cassure à 9 voisins : écart 0,0087, le témoin tombe.
  Les chiffres de l'espace d'origine (0,67 contre 0,43) sont lus dans le JSON du juge et dits « juge du premier
  flux » en légende.
- **D20 / M8 (III-9.7), fonction d'appui** : (a) plan (u1, u2), (b) plan (u1, u3) : courbes h(v) = ‖ΔW v‖ (frontière
  en trait, synonyme en tirets remplis), la rose des directions des 1 329 entrées (tranches de 3°) en anneau entre les
  deux courbes ; (c) barres du rapport synonyme / frontière le long de u1, u2, u3 (0,082 ; 0,217 ; 0,269), λ_k sous
  chaque barre, la frontière en trait à 1. Tête : « là où pointent les entrées, le synonyme ramène l'erreur à au plus
  0,135 de celle de la frontière » (90 % des entrées à ±30° de u1 en (a), ±24° en (b) ; rapport maximal dans ce cône
  0,133 et 0,135). F et la « règle déclarée » (M10) disparaissent avec les ellipses agrandies. M8 : « le long de u1,
  l'axe où les entrées pèsent le plus (leur moyenne) », et λ1 doit l'essentiel à la moyenne (16,5² ≈ 272).
- **Témoin A1 (fonction d'appui)** : M est retrouvée des 181 points commités de chaque ellipse (moindres carrés sur
  a x² + 2bxy + c y² = 1, points ÷ F) ; diag(M) = e_k du JSON et demi-axes = `demi_axes_bruts`, écart max 2,2e-7
  (seuil 1e-6 : les points sont écrits à 6 décimales) ; cassure `--casse-appui` (F faux de 1 %) : écart 0,0197, tombe.
  Une cassure n'écrit rien sous `donnees/` (dossier jetable). Journal : `donnees/latents-temoins.json`.
- **M4, M5** : « 12,2 % au hasard (somme des carrés des parts) » ; « un seuil que son initialisation par l'ACP
  atteint déjà : elle le dépasse de 0,155 et de 0,042 » (différences tirées du JSON).
- **Nombres** : tout nombre écrit vient de `latents-chiffres.tex` (y compris 9 voisins, 1 %, 181 points, 30
  voisins, 3°) ; seules les graduations (0,05 ; 0,10 ; 0 ; 0,5 ; 1) sont des choix d'axe.
- **Données** : neuves `latents-etats-tsne-g1…g8.csv`, `latents-etats-reperes.csv`, `latents-appui-*`,
  `latents-rose-*`, `latents-barres.csv`, `latents-temoins.json` ; `latents-etats-{acp,tsne}.csv` changent de
  colonnes (x, y, groupe, marge) ; retirées (plus tracées) `latents-nuage-{12,13}.csv`,
  `latents-ellipse-{frontiere,synonyme}-{12,13}.csv`. Les mesures sous `mesures/genome/tome3/latents/` ne bougent pas.
- **Ancienne note** : deux phrases barrées dans `REPRISE-figures-latents.md` (« dessinent les frontières », faux pour
  z(4) − z(5) ; « 25 experts premiers distincts », 27).

## Pilote
`memoire/essai/pilote-tome3-latents.tex` (ignoré par git) : PDF `pilote-tome3-latents.pdf` et
`pilote-tome3-latents-en.pdf`, deux passes chacun.

## Pas fait, et pourquoi
- 3D (Blender) : hors de ce flux (consigne).
- D17 (« même pas de graduation » 500 dans (a)(b)(c) de III-9.1) et l'annotation traversée de la part cumulée (G3 du
  juge construction) : ils portent sur les panneaux du lot synonyme (axe k de 0 à 2 880), pas sur la rangée, qui n'a
  pas d'axe k. Au lot synonyme. La rangée n'a aucune annotation traversée (halo partout).
- L'assemblage de III-9.1 en une seule figure (a)–(d) : aux chapitres ; la rangée garde sa propre légende, qui se
  dit « panneau (d) ».
- `juge_regen.py` du juge des latents comparait 13 fichiers `latents-*` : quatre sont retirés et deux changent ; à
  refaire par le juge du second flux sur la nouvelle liste.

## Pièges (en plus de ceux de la note du premier flux)
- Sous le style `memoire`, `draw=none` est ignoré pour les marques : le contour sort en noir, épais (0,9 pt). Mettre
  contour et fond de la même couleur, contour de 0,1 pt.
- `scatter/classes` à noms numériques « 0 », « 1 » : rester sur des noms en lettres (« petite », « autre »).
- Le brouillon (scratchpad) est partagé avec les autres rôles du flux : travailler dans un sous-dossier propre.
- `sed` avec `\L…` : passe en minuscules (déjà dit) ; l'édition se fait en Python à chaînes brutes (r"…").
