# Tome III, rédaction : reprise du rédacteur B (2026-10-29)

Rôle : rédacteur B, en français. Chapitres : 06-mimetisme, 11-tropicale, 12-spectres
(`memoire/tome3/fr/chapitres/`). Demande de Stone : « finissons ». Plan : `memoire/tome3/PLAN-redaction.md`.

## Fait (commité sur main, git add et commit restreints à mes fichiers)
- 85dbbbf : chapitre 06 (mimétisme) ; `memoire/sources/tome3-mimetisme.bib` (13 notices relues le 2026-10-29 :
  Crossref, API arXiv, page USENIX, RFC 6817 ; haidar2018mixed recopiée de p6.bib et complétée) ; ajout de ce
  .bib dans `memoire/tome3/commun/bibliographie.tex` (3 lignes). Essai seul : 0 erreur, 37 p.
- af425b5 : chapitre 11 (garde tropicale). Essai seul : 0 erreur, 15 p.
- 086a8cc : chapitre 12 (spectres). Essai seul : 0 erreur, 0 renvoi indéfini, 13 p.
- Renvois indéfinis en essai seul : seulement `t3sno:ch` (ch. 9) et `t3tro:ch` (ch. 11, depuis le ch. 6) ;
  ces étiquettes existent dans les squelettes : elles se résolvent dans le maître.

## Décisions (réponses par délégation du 2026-10-29, réversibles)
- Verdict de chaque piste = celui de son juge ; les phrases que les juges démentent sont barrées (\barre) avec
  ce qui les remplace (P1 « boucle du décodage glouton » ; P5 « seuil soutenu tenu » ; P6 « défauts non corrélés
  aux petits poids » ; tropicale 2Φ, corollaire des 4 %, « plafond de 11 points », « n'apporte rien » ;
  spectres « seul endroit », second chemin v1, témoin Pareto du plafond).
- P3 : seulement ce qui est jugé (étage A, étage B N = 146, N = 238, routeur en ligne). Le témoin β = 0,3
  hors moteur (`resultat-temoin-b0.3.md`) n'a pas de jugement propre : non cité. Second tirage : aucun chiffre.
- Spectres : levier, plafonds, règle α̂ < 2, normalisation étiquetés `\etiq{Signe}{non jugé}` ; pages 3 à 5
  non placées.
- Dérivations ajoutées par la rédaction, dites comme telles : ch. 6, proposition « l'inclusif de RAM R' ≥ V
  vaut F(R') » (explique l'égalité mesurée par le juge de P2, sous une hypothèse sur la règle du moteur) ;
  ch. 11, la distance à la frontière d'un polyèdre (corrige la borne de la note de la piste).
- Une erreur de calcul de note corrigée sans barre (chiffre jamais publié comme résultat) : P1, ρ ≈ 1,19 de la
  note → 1,21 par le calcul posé (dit dans le texte).
- Clés : `belady1966` (commun) au lieu de `belady1966study` (p1.bib) ; `lu2024notallexperts` au lieu de
  `lu2024experts` (p6.bib, non chargé).

## Pièges rencontrés
- L'outil d'édition refuse le dépôt principal (session en worktree) : tout écrit dans le répertoire temporaire,
  puis `cp` ; pour un petit remplacement dans un fichier partagé, un script Python lisant ancien/nouveau texte
  depuis des fichiers (pas de heredoc : les « \ » y sont mangés).
- `memoire/essai/c3b.sh` (nom pris d'abord par moi) a été réécrit par un autre rédacteur (jobname
  essai-t3-C8-fr) : ne pas l'utiliser ; mon script d'essai vit hors dépôt. Pilote à moi : `memoire/essai/essai-t3b-fr.tex`
  (lualatex "\def\CHAP{../tome3/fr/chapitres/NN-nom}\input{essai-t3b-fr}", biber, lualatex ×2).

## Reste (pas à moi)
- Traduction anglaise des trois chapitres (traducteur) ; construction complète `./construire.sh tome3`.
- Juge-correcteur : relire les trois chapitres.
