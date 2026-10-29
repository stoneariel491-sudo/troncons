# Tome III, figures, second flux : reprise du juge des chiffres du lot « construction » (2026-10-27)

Rôle : juge indépendant des chiffres du lot construction après corrections (commits `3275a6c`, `cadf276`,
`4229a02`). Rien tracé, rien corrigé. Style télégraphique.

## Fait
- Lu : SOCLE, inventaire (R1 à R6), reprise du Tome III, jugements du premier flux (design en entier, construction,
  ronde, latents), reprise du lot, diffs des trois commits.
- Outils `outils/genome/tome3/juge2-construction/` : `refaire.py` (56 nombres neufs ou déplacés, 56 tiennent ;
  cassure 8 tombent), `regenerer.py` (36 fichiers au bit dans une copie `git archive`, dossier de données vide ;
  cassure 1 diffère ; `--temoins` : les 5 témoins neufs du lot forcés à faux, 5 tombent), `points.py` (40
  contrôles, graine 31415, 0 écart ; cassure 24), `cadres.py` (62 séries contre leur cadre, bornes tapées
  comprises, 0 dehors ; cassure 1). Journaux sous `journaux/`.
- Pilote copié en `memoire/essai/pilote-juge2-construction.tex` (ignoré) : FR et EN, deux passes, 0 erreur, 0 boîte
  trop pleine, 0 renvoi indéfini, 18 + 18 pages, toutes lues à 110 dpi ; III-9.6 agrandie à 400 dpi.
- Jugement : `memoire/tome3/JUGEMENT-figures2-construction.md`. G1 à G5 du premier flux levés ; graves de dessin du
  lot (G3, G4, G6, G7, G9) levés pour ce qui touche aux chiffres. **2 graves neufs** : GN1 (III-10.1, tête
  « aucune mesure de la construction ne les a jugés », or C1 a décodé les 768 experts), GN2 (III-8.5 : (a) dit
  « entropies, pas un fichier codé », (c) dit « codec réel », pour les mêmes nombres ; (c) est vrai). **13
  mineurs** (N1 à N13). Note pour le mémoire (`cadf276`) : barre juste.

## Décisions (réponses par délégation du 2026-10-27, réversibles)
- GN1 et GN2 classés graves : une phrase fausse en tête ou une provenance dite à l'envers fait tomber la figure en
  l'état, comme le G5 du premier juge (protocole mal dit). Raison : même mesure que le premier flux.
- Rien corrigé : aucune faute n'est mécanique (ce sont des phrases, pas des nombres mal recopiés) ; les textes de
  remplacement sont écrits dans le jugement.

## Reste (hors de ce rôle)
- Au lot construction : GN1, GN2, N1 à N9, N11, N12 (lettre du panneau de III-9.1, avec le lot latents).
- À l'orchestrateur : N13 (`REPRISE-figures-construction.md`, « 17 figures ») ; la note F-J4 de
  `genome/construction-juge-pour-le-memoire.md` (source de GN1), à barrer par son auteur.
- Au juge de design du second flux : N1 (étiquette sur la barre de λ = 0), N10 (le bleu `Accent` dans quatre
  figures).

## Pièges
- Le dépôt principal a des fichiers non commités d'autres lots (latents, ronde) : `git add` et `commit` par pathspec.
- HEAD bouge pendant le travail (lot ronde `6292203`, lot latents `326969f`, juge ronde `37db22b`) ; les fichiers
  du lot n'ont pas bougé (journaux refaits à `37db22b`).
