# Tome III, construction finale : reprise, 2026-10-29

Rôle : construire le Tome III complet en français et en anglais (`memoire/construire.sh tome3`), vérifier que les
deux langues ont les mêmes chapitres, figures, tableaux et équations, corriger ce qui ne compile pas sans changer un
chiffre, commiter les PDF, écrire la section « Rédaction » de `memoire/tome3/REPRISE-figures.md`.

## État
Fini et commité. Deux constructions complètes, code 0 toutes deux (la seconde pour que l'anglais prenne les
retouches) : **FR 300 pages, EN 300 pages**, 0 erreur, 0 renvoi ni citation indéfinis, biber sans erreur ni
avertissement, aucun caractère manquant. `git diff` vide sur `memoire/tome3/annexes/` et `memoire/figures/` après
régénération.

## Contrôles de parité (outils dans le répertoire temporaire de la session, `…/scratchpad/final/`)
- `parite.py` (sources, commentaires ôtés) : par fichier, mêmes nombres de `\chapter`, `\section`, `\subsection`,
  environnements figure, table, tabular(x), equation, align, `\[`, appels `\LegendeFigure`, `\Graphe…`,
  `\Figure…`, `\HorsStyle`, `\input`, listings, `\label`, `\barre`, citations. Premier passage : deux écarts,
  `\[` 0/1 aux 02 et 03 (formules passées hors texte par EN1) ; levés en passant les mêmes formules hors texte en
  français (`hors_texte.py`, forme seule). Second passage : PARITE.
- `parite_pdf.py` (`.toc`, `.lof`, `.lot`, `.lol`, `.aux` construits) : 3 parties, 17 chapitres, 121 sections,
  106 sous-sections, 50 figures, 99 tableaux, 1 listing, 65 équations étiquetées, numéros égaux. Le seul « écart »
  qu'il imprime est un faux : les parties françaises passent par `\FBtocpartname` (babel), I, II, III des deux côtés.

## Décisions
- **Trois phrases devenues fausses**, signalées par `REPRISE-redaction-traducteur-EN2.md` au correcteur, que
  personne n'avait traitées : barrées (`\barre`) en FR et en EN avec ce qui a changé, par `barres.py`
  (remplacement exact, une occurrence exigée, sinon il tombe). 07 « L'expert pont » ; 08 l. 397 et le point du
  « Ce qui pourrait être faux » ; annexe B, « L'outil des annexes ». Les nombres ajoutés (couches 0, 8, 16, 23 ;
  §§ ; 2026-10-29 ; 57db4ce) sont ceux du chapitre 04, des sources barrées et de `git log`, les mêmes dans les
  deux langues. Dans la barre de l'annexe B, `\texttt` et `\fichier` sont ôtés (texte nu sous `\sout`), le
  chemin étant redonné juste après.
- Les formules hors texte : plutôt que défaire la retouche anglaise (qui levait deux boîtes trop pleines), le
  français la suit.
- Rendu relu par pdftotext sur les trois endroits barrés, dans les deux PDF.

## Ce qui reste
Voir `REPRISE-figures.md`, section « Rédaction » : aucun juge du tome anglais ; M15 (table des matières,
préambule commun) ; figures du mimétisme non vues page à page en anglais ; trois boîtes sous 1 pt en anglais
(11, 12) et une en français (11).

## Pièges
- La construction complète dure plus d'une demi-heure (deux langues, quatre passes lualatex pour l'anglais la première
  fois) : la lancer en arrière-plan, et ne pas éditer un fichier pendant que sa langue compile.
- Les fichiers sont en LF dans l'arbre (`git ls-files --eol`) : lire et écrire en octets.
