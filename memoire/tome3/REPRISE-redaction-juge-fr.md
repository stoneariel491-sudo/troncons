# Tome III, rédaction : reprise du juge indépendant (français), 2026-10-29

Rôle : juge de la rédaction française du Tome III ; rien écrit de ce qui est jugé. Livrable :
`memoire/tome3/JUGEMENT-redaction-fr.md`. Outils et journaux : `outils/genome/tome3/juge-redaction/`.

## État
- Fait, commité : jugement, outils, journaux ; une correction de chiffre (fichier 13, l. 32 : −0,128 → −0,123,
  référence dite), compilée seule (`memoire/essai/juge-redaction-fr-13/`, ignoré par git).
- Jugé : `HEAD` = `a849d3f` + brouillons du rédacteur A pour 02 à 05 (empreintes dans le jugement et dans
  `journaux/manifeste-brouillon.json`). 02 et 03 : arbre de travail du dépôt (non commités) ; 04 et 05 : seulement
  dans `…/scratchpad/redA/` de la session `<session>`.
- Constructions : `memoire/essai/juge-redaction-fr-brouillon/` (298 p., 0 erreur, 0 indéfini, 24 boîtes),
  `memoire/essai/juge-redaction-fr-tete/` (245 p., 0 erreur, 3 renvois indéfinis : construire.sh tomberait).

## Verdict en une ligne
Juste (71/71 chiffres tirés, 52 refaits, 19 cités ; R1, R3, R4 tenues sauf une fuite au fichier 10 l. 11), pas fini :
7 graves (G1 chapitres 02-05 non commités et tête qui ne construit pas ; G2 débordements des 02-05 ; G3 numéros de
chapitre en dur faux d'un ; G4 KL non définie avant le fichier 07, résumé vide ; G5 notations vides, « R1 » à deux
sens ; G6 fuite R1 ; G7 corrigé), 16 mineurs.

## Pièges rencontrés
- Outil d'écriture refusé dans le dépôt (worktree) : écrire dans le brouillon, `cp`.
- Heredoc et `python -c` mangent les `\\` : écrire les scripts par l'outil d'écriture.
- Deux constructions complètes en parallèle : 31 min pour le brouillon seul, plus lent à deux.
- `barres.py` : un « ~~ » cité dans un jugement ouvre une fausse barre ; borné à un paragraphe et 800 signes.
- Le tirage v1 manquait les `\num{…}` à point : corrigé avant vérification, v1 gardé (`journaux/tirage-v1.csv`).

## Suite (pas à moi)
- Rédacteur A ou orchestrateur : G1 et G2 (recopier, mettre en page, commiter 02 à 05 ; `tome3_annexes.py` dans
  `construire.sh`).
- Flux des figures : G3 (neuf renvois en dur dans huit légendes, par `\cref`).
- Juge-correcteur : G3 (texte), G4, G5, G6, mineurs ; puis reconstruction complète par `construire.sh tome3-fr`.
- Orchestrateur : M13 (corrections à porter dans `genome/duplication.md`, `05-synthese.md`,
  `JUGEMENT-construction.md` § 8).
