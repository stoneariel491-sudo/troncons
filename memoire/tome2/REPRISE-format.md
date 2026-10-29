# Reprise : rédacteur « format » du Tome II

Rôle : chapitres « Architecture et structure du programme » (01) et « Le format .trc au bit près » (02),
EN et FR. Fichiers à moi seul :
- `memoire/tome2/{en,fr}/chapitres/01-architecture.tex`, `02-format.tex` ;
- `memoire/figures/tome2/schemas/{architecture,format}.tex`, `memoire/figures/tome2/graphes/{architecture,format}.tex` ;
- `memoire/outils/tome2_format.py` → `memoire/figures/donnees/tome2/{caisses,sections,flux-moyens,calculs-format}.csv` ;
- `memoire/sources/tome2-architecture-format.bib` ;
- essais : `memoire/essai/essai-t2fmt.tex`, `fmt-*.tex`, `arch-figs.tex` (dossier ignoré par git).
Pas de carte graphique, aucune mesure.

## Ce que le maître du Tome II doit faire pour mes chapitres (je ne l'écris pas)
- `\Racine` et `\Depot` relatifs à `memoire/tome2/<langue>/` : `../..` et `../../..` (le préambule commun les fixe
  à `..` et `../..`, valables pour `memoire/<langue>/`).
- `\addbibresource` : `moteur-E.bib`, `moteur-F.bib`, `moteur-K.bib`, `moteur-O.bib`, `moteur-epreuve-J1.bib`,
  `tome2-architecture-format.bib`. ATTENTION : clés en double entre bibs (`duda2013ans`, `giesen2014interleaved`
  dans moteur-F et 03-entropie ; `belady1966`, `mattson1970`, `wilson1927`, `merity2016wikitext` ailleurs) :
  biber écrit « Duplicate » et construire.sh échoue ; à régler au maître (ne charger qu'une fois, ou dédoublonner).
- Mes chapitres chargent eux-mêmes leurs figures (`\input` des quatre fichiers, commandes en `\providecommand`).
- Libellés préfixés `t2arch:` et `t2fmt:` ; styles TikZ `t2a`, `t2f` ; commandes `\TdArch…`, `\TdFmt…`, `\tdCarte`.
- Lancer `python -I -X utf8 memoire/outils/tome2_format.py` avant la construction (CSV de `donnees/tome2/`).

## Journal
- 2026-10-16 10 h : lu SOCLE, ARCHITECTURE.md en entier, F (notes, dérivations, verdicts, seuils, CSV,
  journaux), E, K, O, épreuve (rapport § 0-2, M1, m4-m6, § 9-12, decodeur_s4.py), R (début). Code relu pour
  les listings (rans.rs, trc-codec lib.rs, coder.rs, trc-ordo Config, build.rs).
- Trouvé en relisant : l'en-tête de `moteur/bins/trc-codeur/src/coder.rs` dit encore « de l'ordre de 25 minutes
  de disque de plus » (même erreur d'unité que celle barrée dans derivations.md § 8 : ≈ 24 s). Fichier du lot F :
  pas touché, à signaler à l'orchestrateur ; le chapitre le dit, barré.
- Figures du format et de l'architecture écrites et compilées en essai (lualatex sans erreur).
- PIÈGE : Bash ici réduit « \\ » à « \ » dans les heredocs et python -c ; éditer les .tex avec Edit/Write.
- PIÈGE : variables de \foreach : jamais \l \v \k \j \b \i \a \c (accents de LaTeX) ; préfixe \f…
- PIÈGE : un style TikZ à argument défini dans un \providecommand s'écrit ##1.
- 10 h 45 : chapitre 01 FR+EN commité (a33a870), 17 p. chacun en essai, zéro référence manquante
  hors `t2fmt:sec:emplacement` (défini au 02).
- 11 h 30 : chapitre 02 FR+EN écrit ; FR seul : 23 p., zéro avertissement. Corrections portées dans
  le texte (barrées) : « ≈ 0,47 Go » de la proposition 7 du lot F = 0,47 Gio (0,50 Go, 502 252 544 o) ;
  « 25 minutes » du commentaire de coder.rs (≈ 24 s).
- Essais : la machine est partagée par 4 lualatex d'autres rédacteurs ; une construction peut dépasser
  10 min : la lancer en tâche de fond. `\{…\}` dans `\fichier` imprime les barres : écrire `{…}`.
- 12 h : chapitre 02 FR+EN commité (3f3ef61) ; figure MÉTA ajoutée ; identifiants longs en
  \nolinkurl. Essai des deux chapitres ensemble : FR 39 p., EN 39 p. (bibliographie comprise), zéro
  erreur, zéro référence ou citation manquante ; restent deux boîtes trop larges de 6 et 2,6 pt
  (tableaux du chapitre 01), sans effet visible.
- ÉTAT : livrable complet. Rien en cours. À porter par l'orchestrateur : (1) à l'arbitre, les douze
  précisions du format (tableau t2fmt:tab:precisions) ; (2) au lot F, le commentaire « 25 minutes »
  de coder.rs, et « 0,47 Go » de derivations.md § 8 (= 0,47 Gio) ; (3) au maître du Tome II, la
  liste « Ce que le maître doit faire » ci-dessus (chemins, bibs, clés en double).
