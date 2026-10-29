# Reprise : juge des chiffres du lot « construction » (Tome III, ch. 8 à 10)

Tenu le 2026-10-27. Jugement : `memoire/tome3/JUGEMENT-figures-construction.md`. Outils et sorties :
`outils/genome/tome3/juge-construction/` (sorties sous `journaux/`).

## Fait

- 154 nombres des `*-nombres.tex` refaits sans lire les scripts du lot (`recalcul.py`) : 154 tiennent
  (9 331 = R1 + neuves réunies, à dire en légende). Cassure : 2 écarts.
- 33 fichiers régénérés au bit par les scripts du lot dans une copie `git archive` (`regenerer.py`).
  Cassure : 1 fichier différent ; deux cassures plus grossières arrêtées par les gardes du lot.
- 57 points tirés, graine 20261027 (`points.py`) : tous à la source. Cassure : 50 écarts.
- Lectures chiffrées L1 à L9 (`lectures.py`) : aires de III-9.1 (c), amortissement δ* = 1, 99,9e centile
  sur R1 et neuves, mélange de chemins mesuré sur R1, encart de III-8.6, reste de la cascade, 12 contre 72
  tenseurs, σ_f / σ_n, jetons par fenêtre.
- Pilote copié en `memoire/essai/pilote-juge-construction.tex` (ignoré), FR et EN compilés deux fois,
  0 erreur, 0 renvoi manquant ; pages lues ; recompilé après correction.
- Corrigé (mécanique) dans `memoire/figures/tome3/synonyme-figures.tex` : III-9.1 anglais « the 2 880
  directions beyond » → « the directions beyond (grey), out of 2 880 » ; III-9.6 FR et EN « trois à six fois »
  → « de trois (synonymes) à neuf (Q2_0) fois ».
- Verdict : 5 graves, 16 mineurs (2 corrigés) ; tombent en l'état III-8.8, III-9.1, III-9.2, III-9.3 ;
  tiennent les dix autres.

## Reste (au lot ou au rédacteur, pas au juge)

- G1, G2 : axes de III-9.3 et III-8.8 (points hors cadre) ; une garde dans les scripts.
- G3 : l'annotation « l'aire est le sur-apprentissage résiduel » de III-9.1 (c).
- G4 : la phrase de la queue de III-9.2.
- G5 : le chemin du panneau 1 des neuves de III-9.3.
- M1 à M16 : voir le jugement. Hors de ce flux : la phrase barrée par R1 dans
  `genome/construction-codon-pour-le-memoire.md` § 5 F6 et § 3.
- Assemblage de III-9.1 : deux panneaux (c) (part cumulée ici, rangée de 32 poids au lot « espaces latents »),
  couleur du synonyme (SerieA ici, SerieB là-bas).

## Pièges

- `git archive` sous `core.autocrlf=true` rend des CRLF : comparer aux blobs (`git show`), pas à la copie
  exportée ; `regenerer.py` passe `-c core.autocrlf=false`.
- `sha256sum` écrit « *chemin » en mode binaire : retirer l'étoile avant `git show`.
- Les scripts du lot ont des gardes (assertion contre les verdicts, sommes à 4 096) : une cassure doit les
  passer pour éprouver la comparaison.
- pgfplots coupe sans rien dire un point hors des bornes : vérifier chaque série contre `xmin`/`xmax`/`ymin`/`ymax`.
- L'outil d'édition refuse le dépôt (worktree) : copier dans le brouillon, éditer, recopier par `cp`.
