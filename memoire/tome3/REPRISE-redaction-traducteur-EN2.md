# Tome III, rédaction : reprise du traducteur EN2 (chapitres 07 à 13, annexes A à C, anglais), 2026-10-29

Rôle : traduire en anglais, fidèlement, `memoire/tome3/fr/chapitres/07-synthese.tex` à `13-discussion.tex` et
`memoire/tome3/fr/annexes/A-protocoles.tex`, `B-outils.tex`, `C-journaux.tex` (français tel que corrigé, après
f3cea48) vers les mêmes noms sous `memoire/tome3/en/`. Rien d'autre : ni le français, ni les figures, ni le
résumé anglais, ni les chapitres 00 à 06 (autre traducteur).

## Fait
- Dix fichiers traduits en entier (squelettes de l'ossature remplacés) : 07, 08, 09, 10, 11, 12, 13, A, B, C.
- Mêmes étiquettes que le français (contrôle `\label` FR = EN, fichier par fichier, ordre compris), mêmes macros
  (`\LegendeFigure`, `\Graphe…`, `\FigureSpectres`, `\FigureTropicaleCoupe`, `\HorsStyle`, `\num`, `\SI`, `\barre`,
  `\fichier`, `\mes`, `\calc`, `\litt`), mêmes `\input` des tables engendrées (bilingues par `\EF`).
- Aucun chiffre changé. Contrôle : script de comparaison des multiensembles de nombres FR/EN (virgule décimale
  convertie), puis ligne à ligne. Seuls écarts : trois gloses ajoutées au 08 (traduction d'une citation de la garde
  du moteur, des commentaires du listing), « le terme d'ordre 1 » rendu « first-order term » (07), et un faux
  positif du script ({0,1,2,3} lu comme 0,1 et 2,3, au 09). Décimaux au point, en texte et en mathématiques ;
  guillemets anglais ``…''.
- Citations de Stone gardées en français, suivies de leur traduction en italique (usage du Tome II anglais) : 07
  (17 octobre), 09 et 13 (« un genre de puissance de raisonnement différent »). Les textes cités d'outils (garde du
  moteur, verrou du juge, noms de fichiers à motif) sont gardés et glosés.
- Listing du fondu (08) : laissé au bit (code et commentaires en français, extrait vérifié des sources), légende
  traduite, et une phrase du texte traduit ses trois commentaires.
- Légendes écrites dans les chapitres (11 tropicale, 12 spectres) traduites ; la coupe du routeur cite
  `coupe-routeur-c12-en.png` (la macro choisit déjà la version anglaise par `\EF`).
- Vocabulaire fixé (réversible) : éclaireur = scout ; témoin = control ; cassure = break ; bascule = flip ;
  frontière = frontier ; brin = strand ; mode rapide = fast mode ; compagnon = companion ; tronçon = chunk ;
  défaut (de cache) = miss ; demi-octet = nibble ; fente = slot ; cahier = specification ; consigne = brief ;
  piste = lead ; juge = judge (« it ») ; réserve R1 = reserve R1 ; étage disque = disk stage ; motif (de
  requêtes) = pattern ; préremplissage = prefill ; graves / mineurs = serious / minor findings.
- Essais seuls (`memoire/essai/essai-t3-en2.tex`, ignoré par git, et `scratchpad/en2/cen2.sh`) :
  07+08 : 48 pages, 0 erreur, 0 boîte trop pleine, 0 caractère manquant ; 09 à 11 : 54 pages, 0 erreur,
  4 boîtes trop pleines (46 pt au 10, une ligne avec `\fichier` insécable ; 8,8 pt au tableau J-V du 120b, libellé
  plus long qu'en français ; 0,55 pt au 11 ; 0,6 pt dans une figure du 11, la même qu'en français, figure en
  lecture seule) : reformulées (même sens, mêmes nombres ; au 10, `\allowbreak` dans
  `Generator(PCG64(20261022))`). Dernier essai, 09 à 13 et annexes A à C : 101 pages, 0 erreur, 0 caractère
  manquant, biber sans erreur ; restent trois boîtes sous 1 pt (0,61 pt figure du 11, la même qu'en français ;
  0,55 pt au 11 ; 0,44 pt au 12), laissées. Le 10, recompilé seul après la dernière retouche : 0 boîte.
- Seuls renvois indéfinis aux essais : vers les chapitres 00 à 06 et vers ceux hors de l'essai.

## Décisions (réversibles)
- Traduction fidèle, y compris de trois phrases françaises que leurs sources ont depuis barrées ou rendues
  fausses (voir « À signaler »). Le traducteur ne corrige pas le fond ; il signale.
- `\etiq{Signe}{non jugé}` rendu `\etiq{Signe}{not judged}` (12).
- Unités : Mo, Go, o, Kio → MB, GB, B, KiB en texte ; les macros `\SI{…}{\Go}` restent (bilingues).

## À signaler au correcteur du français (le texte anglais les suit fidèlement)
1. Chapitre 07, § « L'expert pont » (fr l. 541) : « substituer n'est jamais meilleur que retirer l'expert » est
   affirmé sans barre, alors que `genome/duplication.md` (l. 39) et `genome/05-synthese.md` (l. 58, 383) le
   barrent depuis 800d59e (M13 : faux pour 4/32, 5/32, 25/31, 21/31 experts).
2. Chapitre 08, « Ce qui pourrait être faux » (fr l. 455) : dit qu'une ligne du § 8 de
   `genome/JUGEMENT-construction.md` garde « pour les fichiers, pas pour le format » sans barre ; elle est barrée
   depuis 800d59e (l. 429). Même remarque pour la phrase du § 8.4 du 08 (fr l. 397).
3. Annexe B, « Il reste » et § « L'outil des annexes » : disent que `tome3_annexes.py` n'est pas dans la cible
   `tome3` de `memoire/construire.sh` ; il y est depuis 57db4ce (construire.sh l. 77).

## Reste
- Le résumé anglais (`memoire/tome3/en/resume.tex`), les chapitres anglais 00 à 06 : autres rôles.
- La construction complète `bash memoire/construire.sh tome3-en` : à lancer quand les chapitres 00 à 06 anglais
  seront écrits (sinon renvois indéfinis, et construire.sh s'arrête).
- Une relecture de langue par un second regard : aucune n'a été faite.

## Journal
- 2026-10-29 : 07 et 08 traduits, essai 0 erreur, commit 2583f24. 09, 10, 11 traduits, essai (54 p., 0 erreur,
  4 boîtes, 3 corrigées). 12, 13, A, B, C traduits. Dernier essai : 09 à 13 + annexes, 101 p., 0 erreur ; commit des neuf fichiers et de cette note.
