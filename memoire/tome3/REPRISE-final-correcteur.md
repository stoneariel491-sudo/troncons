# Tome III : reprise du correcteur final, 2026-10-29

Rôle : corriger le Tome III selon `memoire/tome3/JUGEMENT-final.md` (35dc26a), dans les deux langues à la fois ;
les répétitions ; la table des matières (M15) dans le préambule commun, avec preuve sur les Tomes I et II ;
reconstruire, commiter. Travail dans un arbre de travail séparé (branche avancée depuis `main` à 35dc26a), commits
au nom de Stone, sans trailer. Outils de correction dans le répertoire temporaire de la session (`corriger.py` :
remplacements exacts à compte exigé, sinon rien n'est écrit ; `comparer_pages.py`, `essai.sh`, `pieces.py`).

## État
Fini et commité. `construire.sh tome3` : code 0, 31 min, **FR 300 pages, EN 300 pages**, 0 erreur, 0 renvoi ni
citation indéfinis, biber propre, aucun caractère manquant. Mêmes pièces (3 parties, 121 sections, 106
sous-sections, 50 figures, 99 tableaux, 1 listing, équations aux mêmes numéros ; `.toc`, `.lof`, `.lot`, `.aux`).
Boîtes trop pleines : 0 dans la table des matières ; FR 1, EN 3, toutes sous 1 pt. Outils du juge final relancés :
parité des nombres FR/EN 0 fichier en écart sur 18 ; résumés égaux au caractère ; notations, seul écart celui,
connu, du `\crefrange`.

Commits : e5ce266 (G3, outil), 175735b (annexes regénérées), 3293ba7 (texte), 46d5816 (préambule),
3da79e3 (PDF des Tomes I et II), 4b071d0 (PDF du Tome III), puis cette note.

## Graves
- **G1** : un mot par notion, partout (chapitres, annexes, résumé dans les deux fichiers, notations, légendes des
  figures, rangements de `tome3_annexes.py`) : witness → control (66), synonym mutation/genome → synonymous (47),
  synonymous codon of zero et codon of zero → zero-synonym codon (7), synonymous base → synonym base (1), tracks →
  leads (résumé, annexe B), le juge « it » / « that » (his own, judge who : 15). Même défaut, non listé par le
  juge : le fondu était « merge » au 08 (et 07, 10), « fold » ailleurs et aux notations : « fold » partout. Ligne
  « témoin, cassure / control, break » ajoutée aux notations. Comptage final des formes retirées : 0.
- **G2** : `en/resume.tex`, un groupe autour du Résumé (hors du bloc, qui reste égal au caractère à celui du tome
  français) avec `\sisetup{output-decimal-marker={,}, range-phrase={ à }, list-final-separator={ et }}` ;
  `\num{1.80}\,Go` dans les deux fichiers. Rendu vu : « 3,84 », « 4,05 à 4,37 », « 0,131 8 », « 1,80 Go », « 57,1 % ».
- **G3** : `memoire/outils/tome3_annexes.py` lit tout au commit HEAD (`git ls-tree -r -l -z`, `git cat-file
  --batch`) ; la description passe par le code du Tome I (`annexes.description`) sur le contenu commité ; refus,
  code 1, si un fichier compté diffère du commit (`git diff --name-only HEAD`, contenus normalisés). Éprouvé : il
  tombe sur sa propre copie modifiée avant commit. Refait par un autre chemin : e4b_defauts.py 122 lignes
  (`git show | wc -l`), codon/ 2,4343 Mo (`git ls-tree -l | awk`). Totaux d'aujourd'hui : 332 outils, 49 577
  lignes (= 48 947 du juge + 528 des outils du juge final + 102 de l'outil), 66 dossiers, 2 400 fichiers,
  78,56 Mo. Les annexes B et C disent ce qui a changé (124 → 122 lignes, 2,47 → 2,43 Mo).
  **Conséquence** : dans l'arbre principal, où `outils/mimetisme/humain/e4b_defauts.py` est modifié par une autre
  session, `construire.sh tome3` s'arrête désormais à cet outil, tant que ce fichier n'est pas commité ou rendu.
  C'est voulu (le juge le demandait) ; construire depuis un arbre propre.
- **G4** : annexe B, « Il reste » barré avec ce qui a changé (57db4ce, e5ce266) ; l'étape `tome3_annexes.py`
  ajoutée à la liste de la chaîne, avec renvoi aux quatre tables.

## Mineurs
- M1 : « gives back » (30 endroits : saves, reproduces, recovers, returns, restores, gives up), « before its
  judge » (3), « a trifle… », « gives it again », « brought … down » (3 → overturned), « another move than »,
  « The answer of information theory », « reads one like the other », « published figure », « control that can
  fall » (3 → fail). D'autres calques restent : une relecture de langue d'un seul tenant n'a pas été faite.
- M2 : le pour-cent anglais s'écrit `\,\%` partout (662 « 3.6\% » collés passés à l'espace fine, comme `\SI`).
  Non touchés : deux « 3.4 \% » dans une citation barrée (10, 13), comme leur source.
- M3 : résumé (deux blocs, deux fichiers) « faire du v1.2 le format par défaut des fichiers de la machine
  (décision de Stone) » ; titre du point 1 des travaux futurs du 13, avec renvoi aux fichiers recodés.
- M4 : résumé, « le préchargement à confiance calibrée plutôt du côté de tombe ».
- M5 : « Le juge, en cinq phrases » (02, et l'introduction qui l'annonce) ; « au terme de coupe près » ; la somme
  coupée peut être très légèrement négative (vérifié : `kl_min` −5,6·10⁻⁶ et −2,3·10⁻⁵ dans
  `comparer10-base-contre-recette.json`, non imprimés) ; étendue de k dans l'énoncé de Rényi (11).
- M6 : 03, « interpolation en log de l'erreur … ; en linéaire, 3,07 » (refait depuis
  `graine-mesure-theorie.csv` : 3,0613 et 3,0662). Le 3,06 du tableau du 13 et du résumé n'est pas glosé (place).
- M7 : rien à corriger dans le tome ; pour refaire l'empreinte de 03 de 57db4ce, prendre la copie CRLF
  (`56f1d0bf392c`) ou l'objet git (`6ace323d3a52`) : même contenu.
- M8 (décimales groupées) : **non fait**. `group-minimum-digits=4` est la règle des trois tomes ; la changer
  bougerait des centaines de pages des Tomes I et II. À trancher pour les trois à la fois.
- M9 : `REPRISE-figures.md`, section « Rédaction », mise à jour (barres et ce qui a changé).

## Répétitions (§ 5 du jugement)
- Motif croisé : récit entier au 08 ; au 10, la phrase des quatre rapports (×1,389, ×0,715, ×0,851, ×0,882)
  devient une proposition avec `\cref{t3cod:sec:motif}` ; au 09, l'histoire et les deux rapports retirés, renvoi à
  `t3jug:sec:r1`, le reste gardé.
- KL 0,0262 : au 02, la citation barrée retirée, le fait mesuré gardé, « la synthèse a dû corriger une
  attribution de cette KL à λ = 1 » avec `\cref{t3syn:sec:frontiere}` ; 07, 10, 13 inchangés.
- 64 codons : 02 (une phrase et un renvoi), 03 (renvoi à la place du compte), 05 (seule la position bancale de
  Crick, renvoi) ; introduction, 08 et 09 inchangés.
Aucun chiffre changé ; seuls disparaissent des chiffres redits, gardés à leur place.

## Table des matières (M15)
- Préambule commun : la boîte du numéro de page des parties et des chapitres (tocbasic) remplie par `\hss` au lieu
  de `\hfil`, posée à `\AtBeginDocument`. Témoin dans un document minimal à boîte rétrécie : 4 boîtes trop
  pleines sans, aucune de partie ou de chapitre avec.
- Preuve sur les Tomes I et II : quatre PDF construits avant et après le correctif, `latexmk -outdir` sous
  `memoire/essai/` (ignoré par git) ; rendu page à page à 60 ppp et empreintes : **dans chacun, seules les pages 7
  et 10 changent**, deux pages de la table des matières, texte égal ; deux boîtes trop pleines de moins. Témoin de
  l'outil (un PDF contre lui-même : 0 page) et cassure (une page forcée : 1 page) tenus.
- **À savoir** : les PDF des Tomes I et II commités les 15 et 16 octobre différaient déjà de leur construction
  d'aujourd'hui sans le correctif (Tome I EN 46 pages, FR 52 ; Tome II EN 68, FR 70 ; positions dans les figures
  TikZ, MiKTeX 26.5 et les retouches 7db2673 et 4a9dfb3 du préambule). Les PDF commités maintenant (3da79e3) sont
  ceux d'aujourd'hui : ces écarts viennent avec eux, aucun ne vient du correctif. Pages inchangées : Tome I EN 169,
  FR 173, Tome II EN 233, FR 237.

## Ce qui reste
- M8, règle commune des trois tomes.
- Une relecture de langue anglaise d'un seul tenant (M1 n'est corrigé que sur les exemples et les formes comptées).
- Les figures du mimétisme, vues page par page au rendu anglais (réserve du traducteur EN1).
- L'arbre principal : `outils/mimetisme/humain/e4b_defauts.py` modifié par une autre session bloque désormais
  `construire.sh tome3` là-bas (G3, voulu).

## Ce qui pourrait être faux
- Le choix « control », « fold », « it » est celui du juge ou le mien ; un anglophone pourrait en préférer d'autres.
- La preuve des Tomes I et II compare des rendus à 60 ppp : une différence plus fine que le pixel à cette
  résolution passerait (le texte de chaque page est aussi comparé, égal partout).
- M2 a passé à l'espace fine des pourcentages qui pouvaient être dans des contextes particuliers (citations) ; la
  parité des nombres et la construction ne voient pas la typographie.

## Pièges
- L'arbre séparé est en CRLF : `corriger.py` lit en octets, travaille en LF et réécrit les fins d'origine.
- `tome3_annexes.py` refuse un arbre où un outil compté est modifié : commiter l'outil avant de construire.
- Les blocs du résumé sont comparés de `\chapter*` à `\end{otherlanguage}` : rien de propre au tome anglais
  ne doit y entrer (d'où le groupe autour).
