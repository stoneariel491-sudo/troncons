# Tome III : les conventions communes des figures

Écrit le 2026-10-27 par le rôle « commun » du second flux des figures, d'après le juge de design
(`JUGEMENT-figures-design.md` : dictionnaire § 2.1, G9, § 2.3, § 2.4, D23 à D30). Deux fichiers les portent :
`memoire/figures/tome3/palette-tome3.tex` (les couleurs) et `memoire/figures/tome3/legende-tome3.tex` (la légende
et les styles `t3`, qui charge la palette). Le pilote `memoire/essai/pilote-tome3-commun.tex` les montre.

## 1. Ce qu'un lot fait

1. En tête de son `*-figures.tex`, dans sa garde : `\input{\Racine/figures/tome3/legende-tome3}`.
2. **Couleurs** : jamais `SerieA`… `SerieF` pour une entité du dictionnaire, toujours son nom (`CouleurSynonyme`,
   `CouleurFrontiere`…), et de préférence son style, qui porte couleur, trait et marque ensemble :
   `\addplot[t3 synonyme]`, `\addplot[only marks, t3 run point]`, `\fill[t3 hors domaine]`. Une couleur hors
   dictionnaire reste permise dans une seule figure, si la légende la dit.
3. **Légende** : pour chaque figure `<Nom>`, trois définitions, puis l'appel au chapitre :
   `\Titre{<Nom>}{en}{fr}`, `\Legende{<Nom>}{provenance}{tête en}{tête fr}{texte en}{texte fr}`,
   `\Source{<Nom>}{fichiers}` ; le chapitre écrit `\LegendeFigure{<Nom>}`, qui rend
   `\caption[\Titre<Nom>]{\Legende<Nom>\sourcefig{\Source<Nom>}}` et s'arrête si une pièce manque. La tête est
   l'idée de la figure, en une phrase ; la provenance la suit (`\mes`, `\calc`, `\litt`, `\schema`, ou
   `\mes\,\calc`), jamais tapée.
4. **Dessin** : `t3 graphe` (ou `t3 encart`) sur chaque axe ; `t3 decimales x=2` (ou `y`) sur toute graduation
   décimale ; `t3 barres` pour des barres (après `ybar` ou `xbar`, qui remplace l'icône), `t3 points` pour des points seuls ; `t3 titre panneau` (« (a) » puis
   des minuscules) et `t3 titre encart` ; `t3 etiquette` (halo blanc) pour tout texte posé dans un graphe,
   `t3 nombre=<couleur>` pour un nombre contre sa série, `t3 rappel` pour un trait de rappel. Corps plancher
   `\scriptsize` : jamais `\tiny`. Les styles de nœud interdisent la césure.
5. **Anglais** : dans un texte commun aux deux langues, `\Dp` et `\Pv` au lieu de « : » et « ; » ; `\Pourcent{5.6}`
   donne « 5.6% » et « 5,6 % ». Dans une branche de `\EF`, la ponctuation de la langue.

## 2. Le dictionnaire, et ce qui a changé

Chiffré par `memoire/outils/tome3_palette.py` (fonctions de l'outil du juge, exécuté tel quel ; témoins tenus,
cassure tombée) : `donnees/palette-tome3-paires.csv`. Une paire tient si ΔE ≥ 5 en gris et ≥ 10 en deutéranope
(seuils du juge, § 2.2). **33 paires sur 36 tiennent, 27 avec le dictionnaire du juge.** Les écarts à son § 2.1,
chacun pour une paire qui tombait (gris / deutéranope, avant → après) :

| Entité | Juge | Commun | Paire qui tombait |
|---|---|---|---|
| base frontière, trait | `SerieF` | `SerieF!60` (plus clair, 1,3 pt) | frontière / λ = 0 : 0,9 / 27,6 → 19,6 / 31,0 |
| S\* | `SerieE` | `SerieE!70` | S\* / synonyme : 4,3 / 7,3 → 21,4 / 27,2 |
| fenêtres neuves | `SerieE` | `SerieE!70` | R1 / neuves : 4,3 / 7,3 → 21,4 / 27,2 |
| v1.0 | `black!35` | `black!25` | v1.0 / v1.2 : 4,6 / 66,1 → 13,8 / 67,1 |
| brin du génome (ajouté, D7 du juge ronde) | (`SerieB` en III-7.4) | `Disque` | brin / S\* : 2,1 / 85,0 → 16,9 / 66,7 |
| catégories de III-7.6 (G2) | A, D, Encre, E | A, C, Encre, `SerieE!70` | A / D : 4,3 / 7,3 → 21,4 / 27,2 |
| zone gagnante | `Mant!8` | `Mant!12`, bord en `t3 seuil` | contre le papier : 3,8 / 4,0 → 5,8 / 6,1 |
| hors domaine | `black!6` | `black!6` + hachures `black!22` | contre la zone gagnante : 1,4 / 1,4 → 0,6 / 1,5 (la teinte n'y peut rien ; les hachures séparent) |

Les trois paires qui tombent encore sont des fonds pâles (zone gagnante, hors domaine, papier) : aucune teinte ne
les sépare sans cacher les données. Elles se séparent par la forme (hachures contre papier : 19,8 / 19,8 ; contre
la zone gagnante : 14,0 / 13,8). Une paire neuve se vérifie en l'ajoutant à `PAIRES` dans le script, puis en le
relançant (`python -I -X utf8 memoire/outils/tome3_palette.py`). Frontière / Q2_0 baisse en gris (12,9 → 7,6),
mais tient.

## 3. Un exemple, avant et après (III-8.3, `codon-figures.tex`, non modifié ici)

Avant :
```latex
\newcommand{\TitreCodonTheoreme}{\EF{The gain theorem, tensor by tensor}{Le théorème du gain, tenseur par tenseur}}
\newcommand{\LegendeCodonTheoreme}{\EF{The gain theorem, tensor by tensor: the measured gain ... (\fichier{mesures/
  genome/construction/codon/tailles-par-tenseur.csv}). ...}{Le théorème du gain, tenseur par tenseur : ...}}
\begin{axis}[memoire, ..., xticklabel style={/pgf/number format/fixed, /pgf/number format/precision=2}, ...]
\addplot[only marks, mark=*, mark size=1.5pt, SerieA, ...] ...;
\addplot[only marks, mark=diamond*, mark size=1.9pt, SerieB, ...] ...;
\node[font=\sffamily\scriptsize, anchor=south east, align=right, text=black!70] at (...) {...};
% au chapitre : \caption[\TitreCodonTheoreme]{\LegendeCodonTheoreme}
```
Après :
```latex
\Titre{CodonTheoreme}{The gain theorem, tensor by tensor}{Le théorème du gain, tenseur par tenseur}
\Legende{CodonTheoreme}{\mes\,\calc}
  {The expert tensors of both models follow the diagonal the corollary predicts, to the stated gap.}
  {Les tenseurs d'experts des deux modèles suivent la diagonale que prédit le corollaire, à l'écart indiqué près.}
  {Measured gain of the fold (bits per expert weight, coded chunks) against twice the share of $-0$ codes, ...}
  {Gain mesuré du fondu (bits par poids d'expert, tronçons codés) contre deux fois la part des codes $-0$, ...}
\Source{CodonTheoreme}{\fichier{mesures/genome/construction/codon/tailles-par-tenseur.csv}}
\begin{axis}[t3 graphe, t3 points, t3 decimales x=2, t3 decimales y=2, ...]
\addplot[t3 seuil, domain=0.108:0.245, samples=2, forget plot] {x};   % la diagonale prédite
\addplot[only marks, t3 vingtb point] ...;
\addplot[only marks, t3 centvingtb point] ...;
\node[t3 etiquette, anchor=south east, align=right] at (...) {...};
% au chapitre : \begin{figure}\centering\GrapheCodonTheoreme\LegendeFigure{CodonTheoreme}\label{...}\end{figure}
```
Ce qui change : le titre court sort de la légende, l'idée ouvre la légende en gras, la provenance suit, le fichier
passe sur la ligne « Données », les couleurs disent « 20b » et « 120b » par leur nom, les décimales sont fixes et
la note a son halo.

## 4. Ce qui pourrait être faux

- Les seuils (5 et 10) sont ceux du juge, posés après lecture des rendus simulés ; la simulation de Machado est une
  dichromatie complète. Les ajustements valent pour ces seuils, pas pour un lecteur réel.
- La liste des 36 paires vient des figures du premier flux et des graves du juge ; une figure redessinée par un lot
  peut faire côtoyer deux couleurs que la liste ne contient pas.
- La frontière plus claire (`SerieF!60`) se lit moins sur fond `CouleurGagne` ; elle compte sur ses 1,3 pt. Le
  nuancier et la figure d'exemple compilent en FR et EN sans erreur, mais aucune figure d'un lot n'a encore été
  redessinée avec ces styles.
