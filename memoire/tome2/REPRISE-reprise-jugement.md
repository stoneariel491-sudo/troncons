# Reprise : correction du Tome II après le jugement indépendant

Rôle : corriger chaque objection de `memoire/tome2/JUGEMENT.md` (1 grave, 22 mineures) dans les deux
langues, barrer ce qui était faux quand le lecteur doit le savoir, ajouter au jugement une section
« Reprise » objection par objection, reconstruire les deux PDF (0 erreur, 0 référence manquante),
commiter. Aucun calcul sur la carte. Aucune question (délégation, marquée).

Fichiers à moi : chapitres et résumés touchés par les objections (`memoire/tome2/{en,fr}/…`),
`memoire/figures/tome2/schemas/format.tex` (barre du codeur), `memoire/outils/tome2_reprise.py`,
la section « Reprise » de `JUGEMENT.md`, cette note, les deux PDF.

## Journal
- 2026-10-16 : départ. Arbre propre (seuls des __pycache__ non suivis). HEAD `bb98759` (jugement).
  Lu SOCLE, JUGEMENT, REPRISE-juge, REPRISE-integrateur ; ARCHITECTURE § 7 ; Tome I ch. 03 (table
  du disque, budgets 214 / 926) et ch. 04 (équation du jeton).
- Chaque objection refaite avant correction depuis les CSV (vitesse, base, o-jetons-s, e2-nvvn,
  k1-debit-passes, res-plancher) : toutes confirmées.
- Commits par chapitre (paire EN/FR) : `b0a632b` G1 + ch. 01 ; `2d435da` ch. 02 + figure du
  codeur ; `5942f95` ch. 03 ; `1c087fb` ch. 04 ; `e7a9271` ch. 05 ; `4e24d86` ch. 06 ; `bb80c82`
  ch. 07 (C9 ajouté) ; `bd15eda` ch. 09 ; `cf8ea7e` résumés, annexe A, outil.
- Outil `memoire/outils/tome2_reprise.py` : 35 chiffres refaits, 24 contrôles « faux seulement
  barré » ; témoin `--casser` tombe (8 contrôles).
- Piège rencontré (à retenir) : `\barre` (ulem `\sout`) casse sur `\SI{…}` hors maths (« Extra } »
  au ch. 07) ; écrire la valeur barrée en texte simple ou en `$\num{…}$`.
- Piège d'outillage : un script Python passé par heredoc dans l'outil Bash perd un niveau de
  barres obliques inverses (`\\` → `\`, et `"\num"` devient un saut de ligne) ; écrire les scripts
  avec un fichier, chaînes brutes `r"…"`, puis vérifier le diff (fait : aucun caractère de
  contrôle dans les ajouts ; deux casses réparées, tableau des précisions du ch. 02 et ch. 09).
- Réponses par délégation du 2026-10-16, réversibles (dites aussi dans JUGEMENT.md) : définition
  de C9 (plafond de l'équation du jeton, ℰ = 1, t_lat = 0, termes de `res-plancher.csv`) ;
  arrondis corrigés sans barre, chiffres faux barrés ; déclarations datées non réécrites.

- Construction finale (`./construire.sh tome2`, code 0) : EN 233 pages, FR 237 ; 0 erreur,
  0 référence ou citation indéfinie, 0 « ?? » (pdftotext) ; les phrases corrigées sont dans les
  deux PDF. Section « Reprise » ajoutée à JUGEMENT.md ; commit `90e3945`. Rôle terminé.

## Pour qui reprend
- Si une construction échoue : `./memoire/construire.sh tome2`, puis chercher « Fatal » dans le
  journal ; les `\barre` neufs sont aux ch. 01 à 09 (grep `barre{`).
- Reste ouvert (hors de ce rôle) : série unique troncons contre `fit -t 16` en palindrome ;
  décisions de l'arbitre (couture N, C7, C8, L12, précisions T2 et suivantes).
