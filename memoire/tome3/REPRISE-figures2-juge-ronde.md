# Tome III, figures, second flux : reprise du juge des chiffres du lot « ronde » (2026-10-27)

Rôle : juge indépendant des chiffres du lot ronde après corrections (commit du lot `6292203`). Rien tracé, rien
corrigé dans le lot. Style télégraphique.

## Fait
- Lu : SOCLE, INVENTAIRE (R1 à R6), REPRISE-figures, les quatre jugements du premier flux (design en entier),
  CONVENTIONS-figures, REPRISE-figures2-ronde ; diff de `6292203` sur les fichiers du lot.
- Outils `outils/genome/tome3/juge2-ronde/` (commit `37db22b`) : `cles.py` (inventaire des clés neuves ou
  déplacées), `refaire2.py` (69 nombres par un autre chemin + classes par la règle), `regenerer2.py` (54 fichiers au
  bit, deux passes, copie `git archive` sans CRLF), `series2.py` (séries neuves, dessin radial refait, croisements,
  distances), `langues.py` (nombres FR contre EN), `barrees.py` (102 passages barrés). Chaque témoin `--casser` tombe.
- Pilote copié tel quel sous `memoire/essai/juge2-ronde/` (ignoré par git), FR et EN, deux passes : 14 pages,
  0 erreur, 0 boîte trop pleine ; pages lues, détails agrandis (PyMuPDF, `zoom` dans le brouillon).
- Jugement écrit : `memoire/tome3/JUGEMENT-figures2-ronde.md`.

## Verdict
- Le lot tient. G1 (ronde), G10, G5, G8 (design) levés ; part du lot dans G9 faite. Aucun grave neuf.
- 5 mineurs neufs : N1 trait de l'encart qui barre « partitions κ, par tenseur » (III-7.1, FR et EN) ; N2 colonne
  960 à ×310 non nommée, « bords ×7,6 » = cette seule colonne (III-7.4, pré-existant) ; N3 « (figure suivante) »
  accroché au routage imposé (III-7.2) ; N4 valeurs de lien posées sur leur arête (III-4.8) ; N5 « A lu au motif de
  B » sans « sur le 20b » (note construction-codon § 3).
- Lot construction : barre et correction de `construction-codon-pour-le-memoire.md` § 3 et § 5 (F6) tiennent.

## Décisions (réponses par délégation du 2026-10-27, réversibles)
- Aucune correction mécanique faite : N3 est un renvoi mal accroché, pas un nombre ; le reste est du dessin ou une
  phrase à réécrire par le lot. Raison : la règle du rôle (« le reste, tu le rapportes »).
- N2 classé mineur et non grave : la conclusion de la figure (la géante aspire l'erreur, la base la contient, S*
  l'efface) reste vraie à la colonne 960 aussi (base ×0,87, S* ×1,04).

## Pièges vus
- `git archive` sous `core.autocrlf=true` : passer `-c core.autocrlf=false`, sinon les entrées prennent des CRLF.
- Sorties `print` de Python sous Windows : CRLF dans les `.log` ; passées en LF avant le commit.
- Normaliser les groupes de milliers en retirant toutes les espaces recolle des nombres voisins (faux « 0,0360 ») :
  ne recoller qu'une espace fine entre chiffres.

## Reste (hors de ce rôle)
- Au lot ronde : N1 à N4 ; à l'auteur de `genome/genome.md` l. 528 : la même phrase que N2.
- Au juge de design du second flux : les simulations en gris et en deutéranope des figures redessinées (ni le lot ni
  moi ne les avons refaites), et la clé de droite de III-7.4 (colonne de clé, pas des étiquettes en bout de courbe).
