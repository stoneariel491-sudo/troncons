# Reprise : rédacteur « chemin-noyaux » (Tome II)

Rôle : chapitres « Le chemin des octets » et « Les noyaux sur la carte », EN et FR.
Fichiers à moi seul : `memoire/tome2/{en,fr}/chapitres/03-chemin.tex`, `04-noyaux.tex` ;
`memoire/figures/tome2/chemin-figures.tex`, `noyaux-figures.tex`, `chemin-noyaux-commun.tex` ;
`memoire/figures/tome2/donnees/t2c-*.csv`, `t2n-*.csv` ; `memoire/outils/tome2_chemin_noyaux.py` ;
`memoire/listings/tome2/*` ; cette note. Aucun calcul sur la carte. Aucune question.

## État : livrable complet (2026-10-16)
- 03-chemin (≈ 28 p. par langue) et 04-noyaux (≈ 28 p.) écrits en FR et EN, fidèles l'un à l'autre ;
  6 schémas, 10 graphes, 4 tableaux pour 03 ; 6 schémas, 9 graphes, 7 tableaux pour 04 ; 11 listings ;
  32 énoncés (3 théorèmes, 5 lemmes, 21 propositions, 1 corollaire, 2 définitions), 29 démonstrations ;
  sections « Ce qui pourrait être faux » et barrés.
- Construits seuls et ensemble dans `memoire/essai/` (deux-fr.tex, deux-en.tex) : zéro erreur,
  zéro citation manquante, références croisées 03 <-> 04 résolues.

## Pour le fichier maître du Tome II (à qui l'assemble)
- `\Racine` = memoire/ et `\Depot` = racine du dépôt, relatifs au dossier de compilation
  (memoire/tome2/<langue>/ : `../..` et `../../..`). Mes figures ne lisent que par eux.
- Les fichiers de figures se chargent depuis les chapitres eux-mêmes, gardés par `\ifdefined`
  (`\GrapheChmSync`, `\GrapheNoyDecodeur`, `\TdeuxChmNoyCommun`) : rien à ajouter au maître.
- Bibliographies citées : moteur-E, moteur-K, moteur-R (peng2023yarn), moteur-O, moteur-epreuve-J1
  (higham2002, ieee754-2019). Doublons entre fichiers (biber « Duplicate » fait tomber
  construire.sh) : `wilson1927` (moteur-R et moteur-epreuve-J1), `belady1966`, `mattson1970`
  (moteur-O et mesures-gpt-oss), `merity2016wikitext` (moteur-R et mesures-gpt-oss).
- Labels : `ch:t2-chemin`, `ch:t2-noyaux` (cités par 00-introduction) ; tous les autres préfixés
  `t2c-` / `t2n-`. Styles TikZ préfixés `chm`, `noy` ; style de listing `tdeux`.

## Corrections faites hors de mes fichiers (minimes, nécessaires à l'impression)
- moteur-K.bib : « __ballot_sync » etc. échappés (`\_\_`) ; « 2^-127 », « 2^-128 » en
  `\textsuperscript`. moteur-O.bib : « 2^-11 », « 2^-24 » de même. Sans cela lualatex tombe à
  l'impression de la bibliographie (« Missing $ »). Réponse par délégation du 2026-10-16,
  réversible ; raison : le texte ne change pas, seul son échappement.

## Constats portés dans les chapitres (à l'orchestrateur)
- E0(c) : rapport charge/vide 3,6 à 4,8 pour quatre variantes, 8,7 pour `boite_sans_vidage`
  (resume.json) : la phrase de la note E est précisée et barrée.
- L12 au préremplissage par flux : 27,44 / 27,39 contre 34,55 / 34,33 j/s (o-jetons-s.csv),
  +25,6 % très au-delà du bruit ; publié comme observation non déclarée, pas comme verdict.
- Note E : « lecture en 12 Mio ≈ 16 ms » est la latence du lecteur ; sur le chemin, 18,6 ms : barré.
- Commentaire de `pas_octet` (« avance tous les ≈ 8 pas ») contre le calcul de K § 2.2 (4,2 pour
  CODES_CTX, 30 pour DELTA) : écart dit, non mesuré.
- La garde de la ronde ferme le trou de D14 (identité de partie invisible en production) : déduit.
- Listings : six caractères des commentaires (⌊ ⌋ ⌈ ⌉ Σ ᵀ) absents de Libertinus Mono ; le
  `literate` de listings ne s'applique pas aux caractères > 255 sous LuaTeX : rendus en ASCII par
  le script d'extraction, dit dans le chapitre 04.

## Recettes (pour RECETTES.md)
- Extraits de code recopiés par script avec un marqueur exigé sur la première ligne : un décalage
  de la source fait tomber le script au lieu de citer une mauvaise ligne (marche).
- Gantt pgfplots par barres d'erreur horizontales (`x error expr`) lues dans le CSV brut (marche).
- Filtrer deux colonnes à la fois par `restrict expr to domain={\thisrow{a}*10+\thisrow{b}}` (marche).
- `\foreach` dans un `axis` : \x indéfini (échec) ; écrire les `\draw` à la main.
- `bar width` dans les options d'un `groupplot` : clé inconnue (échec) ; la mettre dans `\nextgroupplot`.
- L'outil Bash mange les « \\ » (sed, heredoc, python -c) : éditer le LaTeX par Edit ou par un
  script Python écrit avec Write (marche).
- Listings flottants en nombre : rejetés en fin de chapitre ; listings en ligne et `[!htbp]` (marche).

## Journal
- 39fe498 : 03 FR + figures + script ; fb43fb6 : 03 EN ; a5cb457 : 04 FR + EN.
- Essai : `memoire/essai/c.sh <chap> <fr|en>` (lualatex, biber, lualatex ×2 ; 10 à 20 min par langue
  sur la machine chargée : le lancer en arrière-plan).
- 2026-10-16, après-midi (reprise) : passe de mise en page. Lignes trop larges retirées : noms de tests
  longs sécables (`\allowbreak`) et graphes à 0,95 `\linewidth` dans 04 (EN et FR), tableau K3 en
  `\footnotesize` ; trois lignes de 03 FR (lemme de l'exclusion, abandon du lecteur, lemme PDH) reformulées
  à l'identique de sens ; `Bytes/\allowbreak sec` aussi en EN. Essai FR de 12 h 27 : zéro erreur, zéro
  ligne trop large dans 04, trois dans 03 (celles corrigées ici).
- Fidélité EN/FR vérifiée par script (scratchpad, `fidelite.py`) : labels, citations, renvois,
  environnements, listings, marqueurs \mes/\calc et tous les nombres identiques entre langues, pour 03
  et 04 (seul écart : « top-1 » contre « premier choix », mot et non chiffre).
- PIÈGE : la machine n'a pas de fichier d'échange ; mémoire virtuelle libre 0,3 Go à 15 h 15, lualatex
  tombe au chargement (« not enough memory for buffer allocation »). Ne pas lancer FR et EN en parallèle ;
  attendre qu'il reste plus de 1,5 Go de mémoire virtuelle libre.
- 2026-10-16, soir (reprise après la coupure ; l'orchestrateur avait sauvé la passe en abe91e5) :
  l'essai FR de 15 h 18 avait été coupé. Refait : il restait une ligne trop large (énoncé du lemme de
  l'exclusion, FR), reformulé à l'identique de sens (36ead29). Essai EN : un `.aux` tronqué à 32 Kio
  (passe coupée) faisait tomber `\begin{document}` ; le supprimer avant de relancer. Une passe EN est
  tombée en « TeX capacity exceeded [token memory] » avec 22 Mo de mémoire virtuelle libre : même piège
  que plus haut, pas une erreur du texte. Deux lignes trop larges en EN (`--longueur-lecture` en 03,
  `swiglu_oai` en 04) : points de coupure ajoutés dans les deux langues.
- État vérifié : essais FR et EN des chapitres 03 et 04 ensemble, zéro erreur, zéro renvoi ou citation
  indéfini, zéro ligne trop large dans mes chapitres, 55 pages par langue. Seule ligne trop large
  restante (4 pt, EN) : la note de l'entrée CUDA Driver API de `moteur-E.bib` (« Gestion de la
  mémoire : cuMemHostAlloc… »), fichier qui n'est pas à moi ; laissée, signalée.
- Fidélité refaite par script après ces retouches : labels, citations, renvois, environnements,
  listings, marqueurs identiques ; nombres identiques ligne par ligne (écart de comptage seulement
  par « top-1 » contre « premier choix »).

## Reste
- Rien d'obligatoire. Si l'arbitre tranche (longueur des lectures, repli du décodeur, KV f32),
  mettre à jour les phrases « décision non prise » de 03 § regimes et de 04 § débits et § kv.
