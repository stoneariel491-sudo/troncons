# Tome III, version anglaise : reprise du traducteur EN1, 2026-10-29

Rôle : traduire en anglais, fidèlement, les chapitres `00-introduction` à `06-mimetisme` et le résumé, de
`memoire/tome3/fr/` (tel que corrigé, commit `f3cea48`) vers `memoire/tome3/en/` ; mêmes noms de fichiers,
mêmes étiquettes, mêmes macros ; aucun chiffre changé ; essai des chapitres seuls ; commit. Les chapitres 07 à
13 et les annexes sont à d'autres traducteurs (07 et 08 déjà commités en `2583f24`) : je n'y ai pas touché.

## État
- Fini et commité (voir le commit « Tome III EN, chapitres 0 à 6 et résumés… »).
- Fichiers : `memoire/tome3/en/chapitres/00-introduction.tex` … `06-mimetisme.tex`, `memoire/tome3/en/resume.tex`.
- Essai des sept chapitres seuls avec les résumés, préambule et figures du maître anglais (`\anglaistrue`) :
  **120 pages, 0 erreur, 0 caractère manquant** ; les seuls renvois indéfinis visent les chapitres 7 à 13 et
  l'annexe A, absents de l'essai. Boîtes trop pleines : voir le dernier essai ci-dessous.
- Non fait : la construction complète du tome anglais (`construire.sh tome3-en`) ; elle attend les autres
  traducteurs (09 à 13 et annexes en cours dans l'arbre de travail au moment du commit).

## Ce que j'ai décidé
- **Nombres** : virgule décimale → point ; les séparateurs de milliers restent `\,` (c'est la règle de
  `\sisetup` pour l'anglais dans `memoire/commun/preambule.tex`, `group-separator={\,}`) ; `{,}` en mode
  mathématique → `.`. Les `\num`, `\SI`, `\numrange` sont gardés tels quels (le préambule rend le point). Le
  pourcentage s'écrit `3.56\%` sans espace fine (usage anglais).
- **Contrôle mécanique** (outil `compare.py`, dans le répertoire temporaire de la session, `outilsEN1/`) :
  pour chaque chapitre, multiensembles égaux FR/EN des nombres normalisés (hors commentaires, étiquettes,
  renvois et noms de fichiers), des citations, des `\fichier`, des `\barre`, des appels de figure ; étiquettes
  égales (ensembles triés). Seule différence admise : `\cref` → `\Cref` en début de phrase. Une différence
  trouvée et corrigée (06 : « diviser $N$ par 2 », que j'avais rendu par « halving »). Un diff ordonné
  (`ordre.py`) sert à localiser une différence.
- **Phrases barrées** : toutes gardées barrées, traduites (14 `\barre` sur les sept chapitres, même compte
  qu'en français). La phrase du 04 « substituer n'est jamais meilleur que retirer l'expert » et sa correction
  sont traduites telles quelles. L'attribution du ×1,44 du J1 (réserve R1) est rendue mot pour mot : « through
  the pattern of its read requests, specific to this disk, never from the state of the file ».
- **Mots de Stone** : cités en français, fautes comprises, avec une traduction entre parenthèses (00, 01, 03,
  04) ; même choix que le traducteur des chapitres 7 et 8.
- **Figures** : macros communes (`\Graphe…`, `\LegendeFigure`) inchangées, bilingues par `\EF`. Figures du
  mimétisme (`\FigureHorsStyle`) : incluses telles quelles ; leurs légendes, écrites dans le chapitre, sont
  traduites ; quand la légende française cite un mot de la figure (titre d'origine « finissent en boucle » de
  P1), il est gardé en français avec sa traduction. L'étiquette « KL a priori 0.037 » de la figure de P3 est
  citée avec un point décimal, puisque le dernier point du « Ce qui pourrait être faux » du 06 dit que ces
  figures ont des décimales à point (je ne l'ai pas vu au rendu).
- **Mise en page** (seuls écarts de forme au français, dits) : au 03, le problème du remplissage inverse
  (démonstration de la proposition `t3gen:prop:remplissage`) passe en équation hors texte ; au 02 et au 05, deux
  phrases sont réordonnées pour couper une ligne trop longue, sans rien changer au sens ; au 06, le tableau
  `t3mim:tab:p3-quasi` reçoit `\tabcolsep` de 4 pt ; au 03, le paragraphe « Mesuré sur le processeur »
  s'intitule « Measured on the CPU ».
- **Résumés** : `en/resume.tex` reprend au caractère près les deux blocs de `fr/resume.tex` (l'Abstract y était
  déjà écrit par le correcteur), dans l'ordre du tome anglais : Abstract d'abord, puis le Résumé (outil
  `resume_en.py`). Je n'ai pas réécrit l'Abstract.
- **Vocabulaire** : Tome → Volume ; piste → lead ; éclaireur → scout ; témoin → witness ; cassure → break ;
  juge → judge ; « tient / tombe / ouvert » → « holds / fails / open » ; « à la limite » → « borderline » ;
  défaut (de cache) → miss ; emplacement → slot ; brin → strand ; frontière → frontier ; mode rapide → fast
  mode ; réserve R1 → reserve R1 ; lot → lot ; préremplissage → prefill ; descente (P2) → demotion.

## Essais
- Pilote : `memoire/essai/essai-t3-en1.tex` (ignoré par git), lancé par `outilsEN1/cen1.sh` (lualatex,
  biber, lualatex ×2).

## Ce qui pourrait être faux
- Le contrôle des nombres est un multiensemble : un nombre déplacé d'une phrase à l'autre ne le ferait pas
  tomber ; le diff ordonné l'aurait vu (seules inversions trouvées : des ordres de mots anglais).
- La qualité de la langue n'est jugée par personne d'autre que moi ; aucun juge n'a relu la traduction.
- Je n'ai pas vu les figures du mimétisme au rendu anglais page par page ; seules la compilation et les
  contrôles ont tourné.
