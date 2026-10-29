# Tome III, rédaction : reprise du rédacteur D (2026-10-29)

Rôle : rédacteur D, en français. Chapitres : 09-synonyme, 10-juge, 00-introduction, 13-discussion ; annexes A, B, C.
Demande de Stone, 2026-10-29 : « finissons ». Plan : `memoire/tome3/PLAN-redaction.md`.

## Fait (tout commité)
- 09-synonyme (72376c4, retouches da065e3) et 10-juge (2906db1), rédigés en entier.
- Annexes A, B, C (938dd1a) et l'outil `memoire/outils/tome3_annexes.py`, qui engendre
  `memoire/tome3/annexes/{outils,journaux,seuils,figures}-tome3.tex` depuis git ls-files et git log : 314 outils,
  64 dossiers, 35 fichiers de seuils, 29 figures ; témoin (fichiers des lignes « Données » présents) tient ;
  cassure `--casser` tombe (code 1) ; second tirage de P3 exclu des trois tables (R6).
- 00-introduction (80cb736) et 13-discussion (5fcdcec).
- Essais (`memoire/essai/essai-t3D.tex`, `cD.sh`) : les sept fichiers ensemble, 0 erreur, 84 pages ; puis 13 et B
  après retouches : 0 erreur, 0 boîte trop pleine. Renvois indéfinis : seulement vers les chapitres des autres
  rédacteurs (définis dans le maître).

## Décisions (réponses par délégation du 2026-10-29, réversibles)
- Essai : `\CHAPS` = liste séparée par des virgules ; une passe avec les figures des ch. 9 et 10 prend ~7 min.
- ch. 9 : tableau des différences appariées fenêtre par fenêtre tiré des CSV commités, en plus de la forêt.
- ch. 10 : effet de plan posé comme proposition (grappes, ρ intra) ; ρ ≈ 0,12 [calc.] ; plan ABRRBA démontré (et
  la médiane équilibrée sous une dérive monotone).
- R1 partout : « le motif des requêtes de lecture du format, propre à ce disque » ; attributions anciennes barrées.
- Intro et discussion écrites depuis les livrables, les jugements et les chapitres commités à 03 h 55 (01, 06, 08,
  11, 12) ; les chapitres 02, 03, 04, 05, 07 n'étaient pas encore commités : seuls leurs \cref de chapitre sont
  utilisés, et leurs chiffres cités viennent de genome/05-synthese.md (§ 0, § 2.3 à 2.5) et des livrables.

## À faire par d'autres
- Ajouter `python -I -X utf8 "$ici/outils/tome3_annexes.py"` à la cible tome3 de `memoire/construire.sh`, avant
  latexmk (rôle d'ossature ou juge-correcteur ; ce rôle n'avait pas le droit de modifier ce script).
- Le juge-correcteur : relire 00 et 13 contre les chapitres 02 à 05 et 07 une fois commités (aucun chiffre neuf
  n'y est attendu, mais un verdict reformulé par un chapitre doit l'être aussi dans le tableau des verdicts).
- Le traducteur : 00, 09, 10, 13, A, B, C. Les tables engendrées sont déjà bilingues (\EF).

## Pièges
- L'outil d'écriture refuse le dépôt : écrire dans le scratchpad, puis `cp`.
- `sed` de Git Bash change `\t` en tabulation : jamais de sed sur du LaTeX ; outil Edit.
- Une formule dans un titre de section (λ, →) casse les signets : `\texorpdfstring`.
- Dans `\fichier{…}` (nolinkurl), écrire `_` nu, pas `\_`.
- `\texttt` long sans coupure (noms de drapeaux, listes entre accolades) : boîtes trop pleines.
