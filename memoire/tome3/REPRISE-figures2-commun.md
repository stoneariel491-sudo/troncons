# Tome III, figures, second flux : reprise du rôle « commun » (2026-10-27)

Rôle : le commun du Tome III, avant les lots. Ni figure neuve, ni mesure, ni fichier de lot touché.

## Fait
- `memoire/figures/tome3/palette-tome3.tex` : dictionnaire du juge de design (§ 2.1) en noms sémantiques
  `Couleur…` (\colorlet depuis le préambule, aucun HTML tapé) ; styles de série `t3 …` (couleur + trait +
  marque) ; `\NuancierPalette` et `\PaletteNom` pour les pilotes. Gardé par `\PaletteTomeTrois`.
- `memoire/outils/tome3_palette.py` : ΔE des 36 paires par les fonctions de l'outil du juge (exécuté tel
  quel) ; témoins T1 (paire du juge refaite au dixième), T2 (mélanges xcolor = ceux du juge), T3 (gris
  reste gris) tenus ; cassure `--casse-melange` : T2 tombe, comme il le doit. Sorties sous
  `memoire/figures/tome3/donnees/palette-tome3-*`.
- Décisions (ajustements au dictionnaire du juge, chacun pour une paire qui tombait) : frontière (trait)
  SerieF → SerieF!60 ; S* et fenêtres neuves SerieE → SerieE!70 ; v1.0 black!35 → black!25 ; zone gagnante
  Mant!8 → Mant!12 ; hors domaine toujours hachuré ; brin ajouté (Disque) ; catégories de III-7.6 :
  SerieA, SerieC, Encre, SerieE!70. Résultat : 33 paires sur 36 tiennent (27 avant) ; les 3 qui tombent
  sont des fonds pâles, séparés par une forme (hachures, trait du seuil).
- `memoire/figures/tome3/legende-tome3.tex` : convention G9 (`\Titre`, `\Legende`, `\Source`,
  `\LegendeFigure`), provenance `\schema`, `\Pourcent`, `\Dp`, `\Pv` ; styles `t3 graphe`, `t3 encart`,
  `t3 decimales x/y`, `t3 barres`, `t3 points`, `t3 titre panneau`, `t3 titre encart`, `t3 etiquette`
  (halo), `t3 note`, `t3 nombre`, `t3 rappel`, `t3 sans cesure`. Gardé par `\LegendeTomeTrois`.
- Pilote `memoire/essai/pilote-tome3-commun.tex` (ignoré par git) : nuancier, figure d'exemple (les paires
  avant et après), table des paires, essais typographiques. FR et EN : 0 erreur, 0 boîte trop pleine.
- Essai de charge (`memoire/essai/essai-commun-lots.tex`, ignoré) : le commun et les huit fichiers de lots
  se chargent ensemble sans conflit de noms. Essai des styles (`memoire/essai/essai-commun-styles.tex`,
  ignoré) : `t3 barres` corrigé (l'icône de `ybar` revenait en double pastille ; il se pose après `ybar`).
- `memoire/tome3/CONVENTIONS-figures.md` : mode d'emploi en une page, exemple avant et après (III-8.3).

## Reste (aux lots, pas à ce rôle)
- Porter le dictionnaire et la convention dans les huit fichiers de figures des lots (G1, G9, D23 à D30).
- Le flux des pistes (R6) décide seul pour III-11.x et III-12.x.
