# Tome III, figures, second flux : reprise du juge de design (2026-10-27)

Rôle : juger le dessin du second flux (commun + lots construction, ronde, latents) contre le premier jugement de
design. Ne modifie aucune figure. Style télégraphique.

## Fait
- Lu : SOCLE, INVENTAIRE (R1 à R6), REPRISE-figures, les quatre jugements du premier flux, les trois jugements
  des chiffres du second flux, les reprises des lots et du commun, palette-tome3.tex, legende-tome3.tex.
- Seuils et critères déclarés avant toute lecture de rendu : `JUGEMENT-figures2-design.md` § 1 (commit ed00bb1).
- Pilotes copiés et compilés dans `memoire/essai/juge2-design/` (ignoré) : 8 PDF, deux passes, 0 erreur propre
  aux figures, 0 boîte trop pleine, 0 renvoi indéfini ; 6 erreurs du préambule (MiKTeX 26.5, thmtools) partout.
- Lecture : planches 70-85 dpi, chaque figure FR en couleur / gris / deutéranope (110-200 dpi), détails 300-400 dpi.
- Outils `outils/genome/tome3/juge2-design/` : vues.py, couleurs.py (témoins TD1-TD3 tenus, cassure tombe),
  lot.py (paires rendues des 29 pages), cadres.py (G8 : 0 croisement ; G7 : 47,6 % ; témoin croix tenu, cassure
  tombe), tetes.py (têtes et longueurs). Journaux sous `journaux/`.
- Jugement : 8 graves levés sur 10 ; G7 et G10 non levés au critère (un réglage chacun) ; grave neuf GD1 (le bleu
  à douze sens, `Accent` = synonyme sous un autre nom) ; 22 mineurs DN1 à DN22.

## Décisions (réponses par délégation du 2026-10-27, réversibles)
- Seuils du premier juge gardés (5 gris, 10 deutéranope) pour comparer, mais déclarés avant ; mesure nominale et
  rendue ; second canal par la forme.
- G7 compté non levé à 47,6 % (seuil déclaré > 50 %), même si l'idée se lit : le seuil était déclaré.
- D11 (hachures pour « absent » en III-8.2) retiré : les hachures gardent le seul sens « hors domaine ».

## Reste (aux lots, pas à ce rôle)
- GD1 (sept fichiers de réglage), G7, G10, DN1 (une ligne du commun), puis les mineurs ; DN2 aux chapitres.

## Pièges
- Écrire dans le brouillon, puis `cp`. Python : `python -I -X utf8`. Heredoc : pas de `\` dans du Python
  (passer par l'outil d'écriture).
- LuaTeX efface le PDF sur erreur fatale : compiler dans une copie, jamais sur les PDF des lots.
- Le pilote construction compile en ~10 min pour deux langues et deux passes ; ronde ~4 min.
