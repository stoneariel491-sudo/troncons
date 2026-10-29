# Tome III, rédaction : reprise de l'ossature (2026-10-29)

Rôle : l'ossature du Tome III, avant les rédacteurs. Demande de Stone le 2026-10-29 : « finissons ».

## Fait
- Maîtres `memoire/tome3/fr/troncons-tome3-fr.tex`, `memoire/tome3/en/troncons-tome3-en.tex` : même classe,
  préambule commun, `latexmkrc`, `\Racine` = `../..`, `\Depot` = `../../..` que le Tome II ; trois parties.
- `memoire/tome3/commun/` : `page-titre.tex` (« Tome III : le génome des poids », schéma du chemin, aucun
  nombre), `notations.tex` (conventions ; tableau à une ligne, candidats en commentaire), `bibliographie.tex`
  (tous les .bib utiles, aucun doublon ; p6.bib, mesures-gpt-oss.bib, moteur-epreuve-J1.bib non chargés, dit),
  `fin.tex`, `figures.tex` (légende et palette, les huit `*-figures.tex`, `figures-tropicale.tex` par `\Depot`,
  `\FigureSpectres`, `\FigureHorsStyle`, `\HorsStyle`).
- Résumés vides `memoire/tome3/{fr,en}/resume.tex` (au juge-correcteur, en dernier).
- Squelettes : 14 chapitres (00 à 13) et 3 annexes (A, B, C), FR (sources, sections, figures avec macro et
  étiquette, clés) et EN (titre, renvoi au français).
- `memoire/tome3/PLAN-redaction.md` : par chapitre, sources, figures, dérivations, réserves ; décisions.
- `memoire/construire.sh` : cibles `tome3`, `tome3-en`, `tome3-fr` (huit outils de données, figures des spectres
  compilées à part sous `memoire/tome3/pistes/`, ignoré par `memoire/tome3/.gitignore`) ; autres cibles inchangées.
- Construction `./construire.sh tome3` : 0 erreur, FR et EN, 56 pages chacun ; aucun avertissement de référence
  ou de citation ; restent « Empty bibliography » (aucune citation encore) et ceux que le Tome II a aussi
  (`\FBtocpartname` des parties en français, petite hauteur d'en-tête). Les huit outils de données ont réécrit
  leurs fichiers à l'identique (aucun changement dans `git status`). La compilation à part des spectres prend
  environ 1 min 45 la première fois.
- Pages de titre FR et EN regardées en image : rien ne déborde.

## Piège rencontré
- L'outil d'édition refuse d'écrire dans `~/dev/active/troncons` (session en worktree) : tout est
  écrit dans le répertoire temporaire puis copié par `cp`.

## Non à moi, laissé tel quel
- Fichiers non suivis trouvés sous `memoire/tome3/` à l'arrivée (`avant.sha`, `borne-axe.txt`, `compile.sh`,
  `*-figures.tex`, `pilote-tome3-ronde.tex`, `frontiere.py`, `tome3_*.py`, `verifie_tex.py`) : restes d'un autre
  agent ; ni ajoutés ni effacés.

## Suite
- Les rédacteurs, chapitre par chapitre, d'après `PLAN-redaction.md` ; D pour 00 et 13 ; puis le traducteur ;
  puis le juge-correcteur (résumés, notations, page de titre).
