# Tome III, rédaction française : reprise du correcteur, 2026-10-29

Rôle : corriger le Tome III français selon `memoire/tome3/JUGEMENT-redaction-fr.md` (graves G1 à G6, mineurs),
écrire le résumé en dernier, construire le tome français complet, commiter. Brouillons et outils de correction
dans le répertoire temporaire de la session (`…/scratchpad/corrFR/`), copiés par `cp` (l'outil d'écriture refuse
le dépôt depuis le worktree). Commits par pathspec, au nom de Stone, sans trailer.

## État
- Fini et commité. `bash memoire/construire.sh tome3-fr` (huit outils de données : fichiers régénérés égaux,
  aucun changement dans git ; figures des spectres ; `tome3_annexes.py` ; latexmk) : code 0, **300 pages**,
  0 erreur, 0 renvoi ni citation indéfinis, biber sans avertissement, aucun caractère manquant. Boîtes trop
  pleines : 4 dans la table des matières (1,5 à 5,1 pt, M15, préambule commun) et 1 au chapitre 11 (0,57 pt) ;
  0 dans les chapitres 02 à 05. Liste des listings : 1 entrée. PDF commité.
- Vu au rendu : le tableau 6.6 tient dans la page (essai), le listing 9.1 (accents et « − » rendus), le résumé
  (page iii).

## Ce qui est fait, grave par grave
- **G1** : `04-duplication.tex` et `05-predictif.tex` recopiés de `scratchpad/redA/` ; les quatre empreintes
  vérifiées égales à celles du jugement (a017b826d506, 56f1d0bf392c, ee9b9774f7ba, 7b12095fc686) ; 02 à 05
  commités **tels que jugés** (57db4ce), avant toute retouche. `memoire/construire.sh` : la cible tome3 lance
  `tome3_annexes.py` avant latexmk (même commit).
- **G2** : quinze tableaux des 02 à 05 en `tabularx` sur `\linewidth`, `\footnotesize`, `tabcolsep` 3 pt (outil
  `tableaux.py`, qui ne touche aucune cellule) ; tableau des zéros (02) resserré sans tabularx ; les deux formules
  du 04 en équations hors texte ; `zero_compte.py` coupable (`\allowbreak`) ; « genome frontiere » (03) écrit en
  deux `\texttt` séparés par une espace normale. Essai des quatre chapitres : 0 erreur, **0 boîte trop pleine**
  (56c385c).
- **G3** : tous les numéros de chapitre écrits en dur sont des renvois.
  - Légendes jugées (`legendes.py`, nombre de remplacements attendu par ligne, sinon l'outil tombe) : neuf renvois
    dans huit légendes, FR et EN (eclaireur l. 134-135, 185-186, 227-228 ; genome l. 133-134 ; synthese l. 178-179 ;
    codon l. 410 et 426 ; synonyme l. 350 et 360 ; juge l. 149 et 158). Aucun nombre ni trait changé. C'est une
    retouche hors du rôle des figures, faite parce que le jugement la classe grave ; le flux des figures peut la
    relire.
  - Ajouté hors de la liste du juge, même défaut : `latents-figures.tex`, six « III-9.1 » (numéro d'inventaire, qui
    ne s'imprime pas) → `\cref{fig:t3-syno-base-propre}`.
  - Texte : 01 (deux), 06 (« chapitres 3 à 5, 12 »), 07, 10, annexe A (cinq titres et une phrase, dont trois que le
    juge n'avait pas listés : « ch. 3 à 5, 7 », « ch. 8 à 10 », « ch. 11 et 12 »), 04 (« III-4.8 » → `\cref`).
  - `memoire/outils/tome3_annexes.py` : les rangements « Ch. 1 et 2 » … « Ch. 12 » de l'annexe B étaient faux
    d'une unité aussi ; ils s'écrivent `Ch.~\ref{t3que:ch}`, etc. (26 chaînes).
  - Les renvois vers les Tomes I et II (« Tome~I, chapitre 3 », « Tome~II, chapitre 2 ») ne sont pas touchés :
    leur numérotation est celle de ces tomes, non vérifiée ici.
- **G4** : au 02, avant « Le protocole (P1 de la ronde) », un paragraphe « Le juge, en quatre phrases » : la KL
  d'une position (équation `t3ecl:eq:kl`), la coupe log p > −16 (e^−16 ≈ 1,1·10^−7, calculé), la moyenne sur les
  2 550 positions de R1 (255 par fenêtre), le renvoi à `t3syn:def:kl`. À l'introduction, un paragraphe « Le juge :
  la KL » qui y renvoie. Résumé et abstract écrits (voir plus bas).
- **G5** : table « Les noms du travail » remplie (29 lignes, FR et EN par `\EF`, chacune avec son renvoi au texte
  qui la fonde). R1 : l'introduction dit la convention (« la réserve R1 » pour la réserve, « R1 » seul pour les
  fenêtres) ; quatre « (R1) » qui désignaient la réserve deviennent « (réserve R1) » (10 l. 378 ; 13, trois fois).
- **G6** : 10 l. 11 réécrit (LaTeX : réécrit, pas barré, consigne) : « qu'il refuse lui-même d'attribuer au format »
  devient « qu'il n'attribuait pas lui-même au format (…) ; le juge du placement l'a depuis attribué au format v1.2,
  par le motif de ses requêtes de lecture, propre à ce disque (la réserve R1, …) ».
- **G7** : déjà corrigé par le juge ; gardé.

## Les mineurs
- M1 : 01, ½ log₂(πe/6) 0,254 → **0,2546** (trois endroits du chapitre).
- M2 : 10, 0,95⁶⁴ « 3,7 % » → **≈ 3,75 %**, avec « la source écrit 3,7 %, un arrondi trop bas ».
- M3 : 12, (1 − √q)² 0,334 → **0,3345**.
- M4 : 10, seuil « 2,00 × (1 − 2 × 0,058) = 1,769 » → « 2,00 × (1 − 2σ) = 1,769, σ = 0,05764 (arrondi à 5,8 % dans
  le jugement ; `mesures/genome/construction/juge/vitesse/analyse-120b.json`, seuil 1,76942) ».
- M5 : 06, le zéro de la RAM cite aussi `mesures/mimetisme/P2/grille.csv` (mode inclusif, 0,0 à R = 80 et 160,
  relu).
- M6 : 13, « KL de l'ordre de 0,03 » → 0,0314 au routeur en ligne (β₁ = 0,041 ; JUGEMENT-routeur-ligne), 0,0209 et
  0,0239 à l'étage B (β = 0,06 et 0,07 ; JUGEMENT-etage-B).
- M7 : 03, « rapport 1,335 » → `\barre{1,335}` avec l'incise « un rapport à trois fenêtres, que la passe K10 ramène
  à 1,018 (0,02093/0,02057, calculé) », comme au 07.
- M8 : `fig:t3-mim-p6` appelée au paragraphe « La courbe KL(f) » (06) ; `fig:t3-codon-format` appelée avant
  « L'expert canonique » (08).
- M9 : introduction, le codon donné en A\_flux (3,8434 → 3,7064) et en A\_ctx (3,8431 → 3,7061), les deux nommés.
- M11 : 02, une phrase avant le premier tableau glose `trc-reference`, « fourche » et YaRN (`peng2023yarn`).
- M12 : 11, le lemme de Rényi a sa démonstration (absence de mémoire, récurrence sur les espacements) ; le « Ce qui
  pourrait être faux » du chapitre le dit, et rappelle que les 32 logits ne sont pas i.i.d.
- M13 (hors du tome, Markdown : barré, avec ce qui a changé) : `genome/duplication.md` § 0 point 6 et
  `genome/05-synthese.md` (§ 0 et § 3.2), « substituer n'est jamais meilleur que retirer l'expert » barré, avec les
  comptes 4/32, 5/32, 25/31, 21/31 ; `genome/JUGEMENT-construction.md` § 8, « pour les fichiers, pas pour le
  format » barré, avec l'attribution du juge du placement.
- M14 : 12, Cover et Thomas cités par `cover2006` (entrée commune) ; Everett (03), Schuchman, Zamir et Feder, Gray
  et Markel (12) étaient déjà dits de seconde main dans le texte : rien de plus.
- M16 : un listing au 08, « Le fondu −0 → +0 dans le code » (`t3cod:lst:fondu`) : `trc-format/src/lib.rs`
  l. 67-77 et `trc-codec/src/lib.rs` l. 317-327, tirés au bit par `listing.py`, et vérifiés ligne à ligne (23
  lignes, égales). Langage `t3Rust` défini au chapitre (le Tome II définit le sien dans ses figures, non chargées).

## Non fait, et pourquoi
- M10 (récits répétés : motif croisé, KL 0,0262, 64 codons) : non resserrés. Chaque chapitre doit se lire seul, et
  couper un paragraphe jugé demande un nouveau jugement de ce qui reste ; à faire par une relecture de forme.
- M15 (numéros de page en gras qui dépassent dans la table des matières) : dans `memoire/commun/preambule.tex`,
  commun aux Tomes I et II ; non touché.
- Le résumé anglais du tome anglais (`memoire/tome3/en/resume.tex`) : au traducteur. L'abstract du tome français
  est écrit ici, traduction du résumé, mot pour mot dans les nombres.
- Les légendes des figures (G3) restent à relire par le flux des figures s'il le souhaite.

## Pièges
- Heredoc et `python -c` mangent les `\\` ; un TSV de remplacements (`remplacer.py`, nombre d'occurrences exigé)
  avec « ⏎ » pour un saut de ligne a marché sans perte.
- L'essai d'un chapitre lit les brouillons : ne pas les éditer pendant qu'il tourne.
