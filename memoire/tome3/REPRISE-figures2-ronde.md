# Tome III, figures, second flux : reprise du lot « ronde » (2026-10-27)

Rôle : corriger les onze figures du lot ronde (ch. 1 à 4 et 7) selon les juges du premier flux
(`JUGEMENT-figures-ronde.md`, `JUGEMENT-figures-design.md`) et porter le commun (`palette-tome3.tex`,
`legende-tome3.tex`, `CONVENTIONS-figures.md`). Ni figure neuve, ni mesure, ni carte. Style télégraphique.

## Fait
- **Commun porté partout** : chaque `*-figures.tex` du lot charge `legende-tome3.tex` ; chaque figure a
  `\Titre`, `\Legende` (tête en gras = l'idée, provenance `\mes`, `\calc` ou `\schema`, jamais tapée),
  `\Source` ; le pilote appelle `\LegendeFigure{<Nom>}`. Les onze titres courts remplissent la table des
  figures (G9). Couleurs par nom (`CouleurBrin`, `CouleurFrontiere(Marque)`, `CouleurLambdaZero`,
  `CouleurSetoile`, `CouleurSynonyme`, `CouleurCategorieA..D`, `CouleurGagne`, `CouleurSigne`) ; aucun
  `SerieX` ni `\tiny` ne reste ; `t3 graphe`, `t3 etiquette` (halo), `t3 decimales`, `t3 barres`, titres de
  panneau ; `\Dp`, `\Pv` et `\EF{\%}{\,\%}` pour la typographie anglaise (D8, D30).
- **G1 (juge ronde)** : `tome3_synthese.py` classe les points de III-7.1 par la règle déclarée
  (`classe_regle` : meilleur si d̄ + 2σ < 0, égal si |d̄| ≤ 2σ, pire sinon ; sans appariée, verdict de la
  source). Un seul désaccord avec la colonne `verdict` de `frontiere.csv` (κ tenseur par tenseur : gagne →
  égal), affirmé par le script (toute autre divergence l'arrête). `frontiere.csv` non réécrit. Phrase
  « deux points seulement passent sous leur base » remplacée : un seul (λ = 0, −2,95 σ) ; κ par tenseur
  égal (×1,103 ; +0,0066 ± 0,0053 ; +1,24 σ) pour 0,911 × les bits ; la légende dit que la figure suit la
  règle et non la colonne.
- **G10** : III-7.1 ne porte plus que la frontière ; protocole par la forme, verdict par le remplissage,
  couleur par la variante ; légende d'une ligne ; encart agrandi de la frontière à 2,64 bits (S* ne se
  cache plus sous les bases) ; bande sans KL sous l'axe, étiquettes au-dessus ou au-dessous de leurs
  losanges avec trait de rappel (D1) ; la base de λ = 1 en trait gris (sinon cachée sous D2b). L'axe sans
  perte est retiré (III-8.5, lot construction) ; ses quatre nombres (dont D1 = 3,8442, M8) restent dans
  « ce que la figure ne montre pas ». `synthese-colonne.csv` reste écrit pour le lot construction.
- **G5** : III-7.4 sans cadre de légende ; étiquettes directes à droite (traits de 1,2 pt) ; base gris
  bleuté, brin brun (`CouleurBrin`), S* violet ; ×334, ×14, ×1,05 contre le pic, dans la couleur de leur
  série ; la bande de la colonne 1011 passe du rouge (le signe) au gris ; titres (a), (b).
- **G8** : III-4.8 en disposition d'arbre radiale autour du moyeu (calcul de dessin dans
  `tome3_duplication.py`, fichiers `duplication-radial-*.csv` : profondeur depuis le moyeu, secteur
  proportionnel aux feuilles + 1, enfants par score décroissant, aucune arête ne croise) ; cercles de
  profondeur ; arêtes visibles (premier cercle à rayon 2) ; valeurs des liens > s_max/4 posées à côté de
  l'arête ; moyeu à l'encre ; la MDS en encart avec sa fidélité ; fond `Fond` retiré.
- **Mineurs du juge ronde** : M1 (rangées par fenêtre et l'exception (2, 1) à l = 16, comptées par le
  script), M2 (échantillon du critère W lu dans `codons-tourne-l12.json` ; « erreur quadratique
  relative » partout), M3 (témoin du hasard de la couche 23 tracé sur sa couche, `arbre-c23.json` ;
  plancher de la couche 0 en bande grise, chiffré ; ×27 pris contre le témoin de sa couche), M4 (trois
  experts de degré 5 ; 31 moyeu par le poids, 0,335 contre 0,116 ; les 4 plus lourdes le touchent), M5
  (λ = 1 : 16 des 32 experts, lu dans la passe), M6 (sans objet : l'axe sans perte est parti), M7
  (verdict au rapport pour deux perdants ; promesse « mesurée ou seulement prédite »), M8, M9 (queues
  marquées : 10 positions sur 25 communes ; « garde sa forme, pas ses positions »), M10 (la seule KL sous
  10⁻⁵ est négative, −6,9·10⁻⁶ ; routage imposé au Tome II, lot R), M11 (25 = ⌊2 550/100⌋, 0,98 % ;
  lecture dite hypothèse de travail), M12 (échelles non comptées par la borne : 0,0375 bit ; écart 0,473
  contre H₀ au lieu de 0,476 ; lecture « itérés atteignables » posée après la passe 3).
- **Dessin** : D1 à D10 du juge ronde, D1 à D9 et D23 à D31 du juge de design pour ce lot (III-1.1 : valeurs
  OCP au-dessus de l'axe, table doublée de llama.cpp dessous, en le disant, pour concorder avec III-8.1 ;
  zoom sous les numéros ; accolades sans contact. III-3.4 : formes (k_b, v) en haut du panneau du bas,
  témoin T1 en anneau à l'encre ; III-3.6 : graduation 3,00 retirée, titres alignés ; III-4.2 : légende
  hors du cadre, « couche précédente » ; III-7.3 : points gris, queues marquées, encadré hors du nuage,
  étiquette « synonyme » de la densité de droite).
- Scripts : régénération au bit vérifiée (deux passes, mêmes empreintes) ; aucun CRLF.
- Pilote `memoire/essai/pilote-tome3-ronde.tex` : `\LegendeFigure`, option `\SEULE{<Nom>}` pour essayer
  une figure. FR et EN, deux passes chacun : 0 erreur, 0 boîte trop pleine, 0 avertissement LaTeX ;
  14 pages chacun, chaque page relue (planches à 70 dpi, détails à 220-300 dpi).

## Décisions (réponses par délégation du 2026-10-27, réversibles)
- Tête de III-7.2 : « de l'égalité à plusieurs fois la base » (pas « trois fois », qui serait un chiffre
  tapé) ; tête de III-7.4 : « la base la contient » (×14 n'est pas « petit »).
- Les bases de III-7.1 en gris clair plein, bord gris foncé : un gris foncé plein se lisait « meilleur ».
- Les trois genres de candidats de III-4.2 et les trois rôles de III-2.1 prennent les catégories A, B, C
  ou A, B, D du dictionnaire (vérifiées deux à deux par le commun) ; l'orange (Q2_0) et le rouge (signe)
  ne servent plus.
- La borne de III-1.2 à l'encre (un calcul, pas une variante) ; la base frontière en losange gris foncé.

## Pièges vus
- `t3 decimales x/y` laisse le chemin des clés dans `/pgf/number format` : une clé `font=` posée après lui
  dans le même `xticklabel style` est refusée. La poser avant (fait dans III-3.6). À dire au commun.
- `\pgfmathtruncatemacro{…}{\genVal{…}}` (le `\ifcsname` des macros de nombres) casse : `\edef` pour un
  entier.
- Encart pgfplots qui retrace tous les points : `clip=false` y place des marques à 200 cm (boîte trop
  pleine de 6 500 pt). L'encart garde `clip=true`.
- Un `x filter` sur 2 550 lignes écrit une note par point écarté : compilation de plusieurs minutes. Les
  queues de III-7.3 ont leurs propres fichiers.
- Le pilote complet compile en environ une minute par passe et par langue.

## Reste (hors de ce rôle, ou pour un juge)
- Un juge des chiffres et un juge de design qui relisent seulement ce qui a changé.
- III-7.4 pour les autres tenseurs (état C) et les classes de colonne de blk.0 gate (déjà listé).
- Les `\cite` au chapitre (OCP MX v1.0, llama.cpp, Blahut 1972, Kruskal 1956, Shannon 1959).
