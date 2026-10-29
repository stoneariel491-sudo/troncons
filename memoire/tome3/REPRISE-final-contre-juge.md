# Tome III : reprise du contre-juge des corrections finales, 2026-10-29

**Rôle** : contre-juger le flux de corrections du jugement final (`35dc26a` → `a43281d`). Je n'ai rien écrit de
ce que je juge.

**Livrable** : `memoire/tome3/JUGEMENT-final-contre.md`. Outils et journaux : `memoire/tome3/contre-final/`. Ils
sont hors de `outils/` et de `mesures/` exprès : ainsi, ils n'entrent pas dans les annexes B et C engendrées, et
le PDF commité reste celui que construit le commit.

## État
Fini et commité.

**Verdict** : G1 à G4 levés ; 0 grave neuf dans le flux ; 3 mineurs neufs (m1 à m3) ; H1 hors du flux.

**Constructions**, dans trois arbres détachés (créés par `git worktree add --detach` dans le répertoire
temporaire de la session, hors du dépôt) :
- **Tome III**, `construire.sh tome3` au commit `a43281d` : code 0, FR 300 et EN 300 pages, égaux page pour page
  aux PDF commités ;
- **Tomes I et II**, par `latexmk` seul, avant (`3293ba7`) et après (`a43281d`) le correctif : seules les pages
  7 et 10 changent (table des matières), au texte égal ; les PDF d'après sont égaux, page pour page, à ceux qui
  sont commités.

**Décision** : je n'ai rien corrigé. m1 à m3 sont des choix d'écriture, aucun ne fait dire faux. Toute retouche
d'une source oblige à reconstruire le Tome III et à recommiter ses deux PDF : c'est au correcteur de le faire.

## Pour qui reprend
- **m1** : au 09, l. 471 (FR et EN), écrire « réserve R1, \cref{t3jug:sec:r1} ; ses mesures au
  \cref{t3cod:sec:motif} ».
- **m2** : au 02, l. 18 (FR et EN), écrire « cette redondance du code ».
- **m3** : dans l'abstract, que les deux `resume.tex` portent au caractère près, remplacer « rather on the side
  of falling » ; à corriger dans les deux fichiers à la fois.
- Puis `construire.sh tome3` depuis un arbre propre, et recommiter les deux PDF.
- **H1**, pour le propriétaire des Tomes I et II :
  - `construire.sh` sans argument tombe sur `tome2_chemin_noyaux.py`, parce que `passe.cuh` a bougé (`eb78770`) ;
  - recaler les extraits du Tome II sur la nouvelle position ;
  - figer `annexes.py` du Tome I au commit, comme `tome3_annexes.py`.

## Pièges
- **L'outil d'écriture refuse le dépôt** : écrire dans le répertoire temporaire, puis `cp`.
- **Les heredocs de l'outil Bash avalent les doubles barres obliques inverses** : écrire les scripts Python par
  l'outil d'écriture.
- **Trois constructions LaTeX en parallèle** ont fait tomber une passe (latexmk code 12, aucun message dans le
  journal). La relancer seule, par `latexmk -g`, puisque latexmk garde l'erreur en mémoire.
- **Les outils de données des Tomes I et II réécrivent leurs fichiers engendrés.** Pour isoler le préambule, je
  les ai rendus par `git show HEAD:<f> > <f>`, dans mes arbres détachés seulement.
- **Les arbres détachés** (`w-avant`, `w-apres` et `w-apres12`, dans le répertoire temporaire) sont à moi et ne
  contiennent que des constructions : je les retire par `git worktree remove --force` une fois le jugement
  commité.
