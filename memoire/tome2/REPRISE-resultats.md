# Reprise : rédacteur « résultats » (Tome II)

Rôle : résumé, introduction du Tome II, chapitres « Résultats du jalon J1 », « L'épreuve
indépendante et la ronde de corrections », « Discussion, limites et travaux futurs » (avec la
conclusion), EN et FR. Aucun calcul sur la carte. Aucune question (délégation, marquée).

Fichiers à moi seul : `memoire/tome2/{en,fr}/chapitres/00-introduction.tex`, `07-resultats.tex`,
`08-epreuve.tex`, `09-discussion.tex` ; `memoire/tome2/{en,fr}/resume.tex` ;
`memoire/figures/tome2/resultats-figures.tex` ; `memoire/figures/tome2/donnees/res-*` ;
`memoire/outils/tome2_resultats.py` ; `memoire/sources/tome2-resultats.bib` ; cette note.
Essais (ignorés par git) : `memoire/essai/essai-t2res.tex`, `essai-t2res-tout.tex`, `t2res-*`.

## Conventions (réponse par délégation du 2026-10-16, réversible ; alignées sur les autres rédacteurs)
- Chapitres `ch:t2-intro`, `ch:t2-resultats`, `ch:t2-epreuve`, `ch:t2-discussion` ; étiquettes
  préfixées `t2res-` (résultats ; `t2r-` est pris par la référence), `t2e-`, `t2d-`, `t2i-` ; styles
  TikZ préfixés `res` ; langage de listings `RustRes` (d'autres définissent `Rust` à leur façon).
- Seule l'introduction renvoie aux chapitres des autres (`t2arch:ch`, `t2fmt:ch`, `ch:t2-chemin`,
  `ch:t2-noyaux`, `ch:t2-reference`, `ch:t2-cache`), tous présents dans l'arbre à 11 h.
- Figures chargées depuis le chapitre, gardées par \ifdefined\GrapheResVitesse.
- Données : `memoire/outils/tome2_resultats.py` relit les CSV et journaux commités, écrit
  `res-*.csv` et `res-chiffres.json`, et sort en erreur si un recalcul s'écarte d'un chiffre publié.
  À lancer avant la construction (bibliothèque standard seule).
- `resume.tex` d'une langue : son résumé d'abord, puis celui de l'autre (convention du Tome I) ;
  le maître l'appelle par \input{resume} après la page de titre. La conclusion est un \chapter*
  à la fin de 09-discussion.tex.
- Bibliographie à charger par le maître : `tome2-resultats.bib` (clés neuves), et pour mes citations
  `moteur-E.bib` (little1961), `moteur-R.bib` (wilson1927, peng2023yarn, openai2025gptossref),
  `moteur-O.bib` (higham2002, fips180-4, ms-terminateprocess, ms-jobobject-limit, ms-createprocess,
  openai2025harmony).

## PIÈGES pour le maître (constatés, pas corrigés : fichiers d'autres lots)
- `ieee754-2019` (moteur-O.bib et moteur-epreuve-J1.bib) a une note « u = 2^-11 » : un « ^ » nu en
  mode texte arrête lualatex (« Missing $ inserted ») dès que l'entrée est imprimée. Je ne la cite
  pas ; quiconque la cite doit corriger la note (ou ajouter une règle \DeclareSourcemap pour « ^ »).
- Doublons de clés entre .bib (déjà notés par les autres rédacteurs).
- \ulem (\barre) dans une cellule tabularx : ni \num ni \SI ni \texttt dans l'argument (« Extra } »).
- Bash ici réduit « \\ » à « \ » : éditer les .tex par Edit/Write ou par un script écrit avec Write.
- Le dossier scratchpad est partagé avec d'autres rédacteurs : noms de scripts propres (`*-res*`).

## État de la ronde (attente demandée par la consigne)
- 10 h 12 : `moteur/REPRISE-O.md`, commit 30d8165 (10 h 09), « Ronde de corrections : état final
  (2026-10-16, 10 h 15) ». Lue comme close ; écrit avec l'état commité 30d8165.

## Constats en relisant (portés dans le texte)
- Coût de la garde : −12,3 % = série ABBA déclarée (02/05 contre 03/04), non réel (seuil 26,8 %) ;
  avec les quatre passes gardées (07, 08 comprises, qui sont le A de la série KV) −4,3 % ; à disque
  égal (05/04) −1,6 % (−1,7 % publié sur valeurs arrondies).
- Règle « 2 × bruit + 3 % » additive dans les verdicts de la ronde ; « 2 × bruit et 3 % » à
  l'épreuve : même verdict partout.
- C6 croise deux séances (vitesse 06 h 41–07 h 19 ; base 08 h 13–10 h 06) : dit dans 07 et 09.
- Bruit de C6 : règle (plus grand bruit d'une paire) 11,0 %, seuil 24,9 % ; étendue des quatre passes
  21,8 %, seuil 46,6 % : × 2,22 tient dans les deux lectures.
- KL f16 de troncons sur la fenêtre 0 du 120b : 124 positions sur 255 ≤ 0 (plancher du format),
  165 sous 10⁻⁴ ; graphe log dessiné avec une ligne de plancher, comptes dans la légende.

## Journal
- 10 h 10 : lectures (SOCLE, REPRISE, ARCHITECTURE § 0, 1, 7–14, épreuve, notes O, E F K R, gpt-oss,
  biomimétisme, Tome I : préambule, résumés, chap. 1, 10, 11, 12).
- 10 h 16 : script de données (848ab03). Sources neuves relues à la source (arXiv, Crossref, NeurIPS).
- Chapitre 07 FR + EN commité (9629de4) ; 08 (9ee228a) ; 09 + conclusion (3202ab6) ; 00 + résumés
  (1c85024).
- Essai d'ensemble (`essai-t2res-tout.tex`, résumé + 00 + 07 + 08 + 09) : FR 54 p., EN 50 p., zéro
  erreur ; seules références manquantes : les chapitres des autres rédacteurs (absents de l'essai) ;
  fidélité EN/FR vérifiée par les ensembles de \label, \cite, \cref et \barre (égaux, à la majuscule
  de \Cref près en début de phrase anglaise).
- Boîte trop large restante (pas à moi) : l'entrée `ms-jobobject-limit` de moteur-O.bib (nom de
  structure Windows insécable, ≈ 100 pt) ; au maître : \sloppy ou \emergencystretch avant
  \printbibliography, ou une note coupable.

## État : livrable complet
Rien en cours. Restes possibles : si le maître du Tome II numérote autrement (00 = chapitre 1), les
textes renvoient par \cref, rien à changer.
