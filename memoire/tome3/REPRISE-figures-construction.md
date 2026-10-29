# Reprise : figures du Tome III, lot « construction » (ch. 8 à 10)

Premier flux de figures du Tome III (inventaire : `memoire/tome3/INVENTAIRE-figures.md` § 5). Style télégraphique.

## Fait

- **Ch. 8, `memoire/figures/tome3/codon-figures.tex`** (script `memoire/outils/tome3_codon.py`, données
  `memoire/figures/tome3/donnees/codon-*.csv` et `codon-nombres.tex`) :
  - III-8.1 `\GrapheCodonRoue` (roue des seize codons, avant et après, pièce du signe) ;
  - III-8.4 `\GrapheCodonAccumulateur` (machine à états de A1, 8 640 lignes, cassure) ;
  - III-8.5 `\GrapheCodonColonne` (gain de colonne par tenseur, seuil 0,015, encart modèle entier) ;
  - III-8.6 `\GrapheCodonJalon` **refaite selon R1** : (a) ABBA s2 et bande ± 2σ, (b) octets par jeton contre
    jetons/s avec la courbe « si seuls les octets comptaient », (c) motif croisé J-bis (Jb3) en quatre barres,
    encart A120/C120 (fragmentation, ×1,26), (d) cascade du 120b refaite (motif, toit des octets, mode rapide) ;
    ancien troisième panneau « la disposition rend 30 % » abandonné (barré par R1) ;
  - III-8.7 `\SchemaCodonFormat` (en-tête, drapeaux bit à bit, entrée du répertoire, table CODES_CTX, chemin
    d'un demi-octet) ;
  - titres et légendes `\TitreCodon…`, `\LegendeCodon…` pour toutes, y compris F2 (`\GrapheCodonOctets`) et F3
    (`\GrapheCodonTheoreme`), dont l'annotation « écart à la diagonale » vient maintenant de `codon-nombres.tex`.
- Pilote : `memoire/essai/pilote-tome3-construction.tex` (ignoré par git) ; PDF
  `memoire/essai/pilote-tome3-construction.pdf` (FR) et `pilote-tome3-construction-en.pdf` (EN).

## Décisions (réponses par délégation du 2026-10-27, réversibles)

- **Légendes dans les fichiers de figures** : chaque figure a `\Titre…` (court, liste des figures) et `\Legende…`
  (longue, bilingue) ; le rédacteur les appelle par `\caption[\Titre…]{\Legende…}`. Raison : la consigne veut une
  légende qui dise protocole, source et limite ; la mettre à côté du dessin garde le chiffre et sa phrase ensemble.
- **Les nombres des légendes et annotations viennent d'un fichier écrit par le script** (`codon-nombres.tex`,
  macros `\CodonN…`, valeurs brutes passées à `\num`) : aucun nombre de légende tapé à la main, sauf les comptes
  du test A1 (8 640 lignes, 2 486 216 demi-octets), qui ne sont que dans 06 § 1 et ARCHITECTURE § 4.16 (pas dans
  un journal chiffré) ; la légende cite ces deux documents et le journal `essais-espace-2026-10-17-a.log` (test
  `ok`).
- **Étiquettes** `fig:t3-<lot>-<nom>` (ex. `fig:t3-codon-jalon`) : posées par le pilote ; les chapitres reprennent
  les mêmes, les `\cref` des légendes en dépendent.
- **III-8.6 (c), le rapport A20** : 1,388 recalculé des huit fichiers Jb3 (médianes 2,5011 / 1,8014) ; le juge du
  placement écrit 1,389 (rapport de médianes arrondies à trois chiffres). La figure garde 1,388, la valeur des
  fichiers. B20 : 0,715 dans les deux.
- **III-8.6, deux modèles dans une figure** : (a)(b)(d) et l'encart sont le 120b, (c) le 20b (seule séance du motif
  croisé) ; la légende le dit en tête.
- **III-8.5** : la colonne `choix` de `colonne-par-tenseur.csv` est le meilleur sans seuil ; la figure applique la
  règle du cahier (≥ 0,015 bit), ce qui redonne les deux seuls tenseurs retenus et 0,0037 bit sur le modèle.
- **III-8.1** : épaisseurs tirées de l'histogramme des 12 tenseurs de prédictif-élagage (le seul histogramme des 16
  codes commité) ; la pièce, des 72 tenseurs (`zero-compte-20b.json`). Les deux sources sont dites.

- **Ch. 9, `memoire/figures/tome3/synonyme-figures.tex`** (script `memoire/outils/tome3_synonyme.py`, données
  `synonyme-*.csv`, `synonyme-nombres.tex`) :
  - III-9.1 (a)(b) `\GrapheSynoBasePropre` en trois panneaux : (a) le spectre de H (calibration et vu par
    l'évaluation) ; (b) e_k lissé par paquets de 60 directions, frontière contre synonyme ; (c) part cumulée de
    l'erreur de sortie, calibration contre évaluation, l'aire ombrée = sur-apprentissage. Fait découvert en traçant :
    H de calibration est de rang 1 329 (le nombre d'entrées de calibration), 1 551 valeurs propres sont nulles à
    l'arrondi près ; le synonyme pousse l'erreur vers ces directions muettes (54 % → 61 % de Σ e_k). Zone grisée.
  - III-9.2 `\GrapheSynoQueue` (survie log-log, Q2_0, frontière, λ = 1, λ = 0, 768 experts ; médianes et 99,9e centiles) ;
  - III-9.3 `\GrapheSynoForet` (forêt B2 fusionnée : R1 par le lot B, fenêtres neuves par le juge, trois
    comparaisons, moyenne ± 2σ par fenêtres, z et nombre de fenêtres négatives) ;
  - III-9.6 `\GrapheSynoVariantes` (frontière des variantes à 768 experts, barres ± 2σ par fenêtres, Q2_0 et
    moteur exact en repères ; R3 dit en légende, aucun point à 32 experts).
- **Ch. 8 et 10, `memoire/figures/tome3/juge-figures.tex`** (script `memoire/outils/tome3_juge.py`, données
  `juge-*.csv`, `juge-nombres.tex`) :
  - III-8.8 `\GrapheJconsCodon` (part des −0 des 96 experts tirés, contre la part du fichier ; gain par poids des
    deux modèles contre A-C2, tailles des quatre fichiers) ;
  - III-10.1 `\GrapheJconsExperts` (grille 24 × 32, couleur = qui a routé, intensité = log des appels, 11 cases
    jamais routées barrées) ;
  - III-10.3 `\GrapheJconsFenetres` (KL par fenêtre, frontière, λ = 1, λ = 0, mode exact ; R1 et neuves).
- Pilote complet : 17 figures (dont F2 et F3 déjà tracées), FR et EN compilés sans erreur, deux passes, aucun
  renvoi manquant ; débordements résiduels de 1 à 4,4 pt (roue, format, forêt).

## Décisions de la seconde moitié (réponses par délégation du 2026-10-27, réversibles)

- **III-9.3, sources** : R1 par les fichiers du lot B (`apparie-*-768-par-fenetre.csv`), neuves par le juge ;
  témoin dans le script : le recalcul du juge sur R1 redonne ceux du lot B à 1e-6 près (sinon il s'arrête).
  λ = 0 contre frontière sur R1 n'existe que chez le juge (même chemin, référence substituée) : pris là.
- **III-9.6, barres** : σ par fenêtres recalculé des fichiers par position (le `kl_incertitude` de
  `variantes-768.csv` est le σ naïf par positions, trois à six fois trop petit, note du juge § 1.4). Moteur exact :
  KL de `c4-20b-comparer.json` (lot O) et bits du v1.0 du 20b (`tailles.json`).
- **III-10.3, mode exact sur R1** : absent de `kl-par-fenetre.csv` ; pris du fichier par position du lot O
  (`c4-20b-comparer.csv`, colonne `kl_b`, moyenne par fenêtre) ; la légende dit les chemins de chaque série.
- **III-8.8 (b)** : le gain en bits par poids plutôt que les tailles en barres (11 Go et 57 Go sur un axe
  écraseraient la différence) ; les tailles sont écrites dans les barres.
- **Couleurs du ch. 9** : frontière SerieF, λ = 1 SerieA, λ = 0 SerieC, Q2_0 SerieD ; R1 SerieA, neuves SerieE.

## Reste (pour un flux suivant ou le juge)

- Le juge du flux : refaire chaque nombre des `*-nombres.tex` par son propre chemin, régénérer les CSV et comparer
  au bit, relire les légendes contre R1 à R4 et les phrases barrées, juger le design.
- `genome/construction-codon-pour-le-memoire.md` § 5 F6 garde la phrase du troisième panneau « la disposition du
  fichier en rend 30 % », barrée par R1 ; le dossier `genome/` n'est pas à ce flux : à barrer par son auteur.
- Débordements de 1 à 4 pt (roue, format, forêt) à resserrer si le rédacteur les voit dans le mémoire.
- La légende de la courbe d'évaluation de III-9.1 (a) s'affiche en gris pointillé dans la légende alors que la
  courbe est orange : à vérifier dans le PDF du mémoire.

## Pièges

- L'outil d'écriture refuse le dépôt (worktree) : écrire sous le répertoire temporaire de la session, puis `cp`.
- Les blocs « heredoc » du shell avalent les barres obliques inverses doublées : écrire tout script Python ou
  LaTeX par l'outil d'écriture, jamais par heredoc.
- pgfplots diffère les `\draw` d'un axe : une couleur posée par `\colorlet` dans une boucle est celle de la
  dernière itération au moment du dessin ; passer la couleur littérale (colonne `couleur` du CSV + `\edef`).
- `xtick=data` prend les abscisses du premier `\addplot` seulement.
- `fill between` de pgfplots sort de la boîte englobante de la figure : la légende chevauche le dessin. Tracer
  l'aire comme un polygone écrit par le script (`synonyme-cumul-aire.csv`, `\closedcycle`).
- Un style qui finit par `error bars/.cd` (`erreurs`) envoie les clés suivantes dans `error bars/` : le mettre en
  dernier.
- Dans un nœud TikZ, le saut de ligne `\\` à l'intérieur de `\textcolor{…}{…}` casse : passer `text=…` au nœud.
