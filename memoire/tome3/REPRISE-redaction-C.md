# Tome III, rédaction : reprise du rédacteur C (chapitres 07 et 08, français), 2026-10-29

Rôle : rédacteur C du Tome III. Chapitres : `memoire/tome3/fr/chapitres/07-synthese.tex`, `08-codon.tex`. Rien d'autre.

## Fait
- 07 « La synthèse de la ronde » écrit en entier : protocoles, différence appariée et incertitude par fenêtres
  (posée) ; frontière commune (table des 14 points jugés à la KL, K10) ; trois propriétés ; quantiles ; KL au second
  ordre (proposition, démonstration en 5 pas, reste borné par (max δ − min δ)³/24) ; hypothèse de la part de bascule ;
  routeur tropical (polyèdres, marge et distance : précise une phrase de 05 § 3.1) ; tableau mécanisme par mécanisme ;
  S* ; chaîne du contexte CODES_COL (posée, avec exemple) ; cahier : A1 (démonstration avec l'argument de grille
  2^-149, qui précise celui de 05), A2, B2 et corollaires ; pistes ; faux. Figures III-7.1, 7.2, 7.3, 7.4, 7.6.
- 08 « Un codon synonyme dans le format » écrit en entier : E2M1, pièce du signe ; proposition du gain et corollaire
  (2 × part des −0), remarque alphabet octet (31 octets, 225) ; lecteurs ; corollaire f64 (hypothèse de non
  sous-dépassement, ajoutée et dite) ; lemme des tables ; format v1.2 ; colonne hors format ; fichiers et témoins ;
  tailles (calculs posés) ; logits ; juge J-T/J-C1 ; J1 s1, s2, barre de l'attribution « état du fichier »,
  motif croisé (R1), cascade 1,034 × 1,394 ; ce qui reste ; faux. Figures III-8.1 à 8.8 (8.6 bis comprise).
- Essais seuls : 07 → 25 p., 0 erreur, 0 boîte trop large ; 08 → 23 p., 0 erreur, une boîte de 2 pt (origine) ; seuls renvois indéfinis : vers les autres chapitres. Commits bdd7815 (08) et suivant (07).
- Essai : `memoire/essai/essai-t3-C-fr.tex` et `c3.sh` (ignorés par git) :
  `bash c3.sh ../tome3/fr/chapitres/07-synthese 6` (le 2e argument : numéro du chapitre − 1).

## Décisions (réversibles)
- Clés uniques : `zhang2018tropical`, `martin2018implicit` (première de chaque paire, comme le plan le propose).
- Gain de colonne : 0,1416 / 0,1231 (contre le flux octet, référence de la décision du lot A) ; 05 mêlait les deux.
- A6 : le décodeur du juge de la construction tient lieu de second décodeur pour la v1.2 (dit au § « Ce qui reste »).
- Les chiffres du lot R (bascules, 88 %) sont cités d'après 05 § 2.2, non refaits depuis les journaux du Tome II (dit).

## Pièges
- `\barre` (ulem) casse sur `\textsuperscript` : l'entourer de `\mbox{}`.
- Une construction d'essai d'un chapitre prend plus de 10 min (toutes les figures du tome se chargent) : en arrière-plan.

## Reste
- Traduction anglaise (rôle du traducteur).
- L'outil Bash mange un `\` sur deux dans un heredoc ou un `python -` : une fin de ligne `\` d'align est devenue `\` (boîte trop large). Corriger par l'outil d'édition.
