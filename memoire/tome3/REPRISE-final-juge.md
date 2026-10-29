# Tome III : reprise du juge final, 2026-10-29

Rôle : juge final indépendant du Tome III (rien écrit de ce qui est jugé). Livrable :
`memoire/tome3/JUGEMENT-final.md`. Outils et journaux : `outils/genome/tome3/juge-final/`.

## État
- Fait, commité : jugement, outils, journaux, cette note. Jugé : `9db456b` (main).
- Tome anglais reconstruit par `construire.sh tome3-en` dans un arbre de travail séparé (avancé à `9db456b`) :
  code 0, 300 pages, 0 erreur, 0 indéfini, 7 boîtes (4 table des matières, 3 sous 1 pt). Texte égal au PDF
  commité sauf 12 lignes des annexes B et C (G3).
- Aucun chiffre corrigé (aucun mal recopié). Aucun fichier du tome touché.

## Verdict en une ligne
Juste, mêmes chiffres dans les deux langues (parité 18/18, 73 chiffres neufs refaits égaux, listing au bit,
Rényi tient, R1 tenue partout), pas tout à fait fini : 4 graves de forme ou d'outil, 9 mineurs, 3 répétitions.
- G1 : deux vocabulaires anglais (witness / control, synonym / synonymous, lead / track, his / it).
- G2 : Résumé français du tome anglais composé à l'anglaise (3.84 et ×1,44 dans une phrase ; GB).
- G3 : `tome3_annexes.py` lit l'arbre de travail. Annexe B : e4b_defauts.py 124 lignes (commit : 122, modif.
  non commitée d'une autre session) ; annexe C : tailles selon les fins de ligne (autocrlf).
- G4 : annexe B, « Il reste à mettre l'outil des annexes dans construire.sh » non barré (fr l. 10, en l. 12) ;
  étape absente de la liste de la chaîne.

## Suite (pas à moi)
- Correcteur ou traducteur : G1, G2, G4, M1 à M6, puis les répétitions (§ 5 du jugement), dans les deux
  langues ; reconstruire `construire.sh tome3`.
- Propriétaire de `memoire/outils/tome3_annexes.py` : G3 (git ls-tree / git show ; refus d'un arbre sale).
- `REPRISE-figures.md` § « Rédaction », « Ce qui reste » : « aucun juge n'a relu le tome anglais » est levé par
  ce jugement (M9) ; à mettre à jour par son propriétaire.
- M15 (table des matières) et M8 (décimales groupées) : préambule commun, pour les trois tomes à la fois.

## Pièges
- `core.autocrlf=true` : un arbre neuf est en CRLF ; les outils de données réécrivent en LF, `git status` montre
  ~200 fichiers « modifiés » sans changement de contenu (`git diff --stat` : seulement les annexes B, C et le PDF).
- L'empreinte de 03 citée par `57db4ce` est celle de la copie CRLF (`56f1d0bf392c`) ; l'objet git (LF) a
  `6ace323d3a52`, même contenu.
- Heredoc et `python -c` mangent les `\` : outils écrits en fichiers.
- La construction de l'anglais seul : 21 min.
