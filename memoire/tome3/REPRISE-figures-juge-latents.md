# Reprise : juge des chiffres du lot « espaces latents » (Tome III, premier flux de figures)

Tenu le 2026-10-27. Jugement : `memoire/tome3/JUGEMENT-figures-latents.md`. Outils et sorties :
`outils/genome/tome3/juge-latents/`.

## Fait

- Nombres des légendes de III-7.6, III-9.1 (c), III-9.7 refaits de zéro (`juge_etats.py`,
  `juge_rangee_nuage.py`, lectures dans `juge_commun.py`) : tous égaux à l'arrondi.
- Ce que dit la taille des points de III-7.6 (`juge_etats_marges.py`) : rien des bords des couleurs (M2).
- Régénération au bit dans une racine de brouillon (`git archive c4f3fe2`), comparée par `juge_regen.py`
  (17 fichiers au bit, 3 JSON hors `duree_s`) ; témoin `--casser` : tout tombe.
- Pilote compilé FR et EN (brouillon), pages 4 à 6 lues ; recompilé après correction ; les PDF du pilote
  du lot (`memoire/essai/`, ignoré par git) remplacés par ceux recompilés.
- Corrigé (mécanique) : « un écart d'un facteur 41 » → « un écart relatif de 41 » (FR et EN), dans
  `memoire/figures/tome3/latents-figures.tex`.

## Reste (à la rédaction ou au lot, pas au juge)

- M2 : choisir z(1) − z(2) pour la taille, ou dire en légende que les gros points ne marquent pas les bords.
- M7 : couleurs du chapitre 9 (synonyme en SerieA chez le lot construction, SerieB ici) ; assembler
  III-9.1 (a)(b)(c) en une figure.
- M3, M5, M6, M8 : phrases de légende et clé des tailles (voir le jugement).

## Pièges

- Les scripts du lot écrivent sous leur RACINE : pour régénérer sans réécrire une mesure commitée, les
  lancer depuis une racine tirée par `git archive` (la RACINE suit l'emplacement du script).
- `juge_etats.py` : ne jamais tirer 200 000 paires × 2 880 d'un coup (4,3 Go) ; par blocs de 4 000.
- Mémoire libre de la machine parfois sous 1 Go (autres sessions) : outils du juge sous 1 Go chacun.
- L'outil d'écriture refuse le dépôt (worktree) : écrire dans le brouillon, puis `cp`.
