# Reprise : le mémoire (rédacteur scientifique)

Rôle : squelette du mémoire et premiers chapitres, en anglais et en français. Pas de carte
graphique, aucune mesure (donc pas de relevé Win32_Battery à faire : rien n'est mesuré ici).
Sources des chiffres : `fondations/0[1-6]*.md` et leurs journaux commités. 03-entropie est à un
autre agent : ne rien modifier sous `fondations/*03*`, `memoire/figures/03-entropie/`,
`memoire/sources/03-entropie.bib`.

## Plan
1. Ossature : `memoire/commun/` (préambule commun), `memoire/en/`, `memoire/fr/`,
   `memoire/figures/` (schemas/, graphes/, donnees/), `memoire/sources/*.bib`,
   `memoire/outils/donnees_figures.py`, `memoire/construire.sh`, `Makefile`, `latexmkrc`.
2. Plan : I le problème (intro, état de l'art, machine, formulation) ; II les leviers mesurés
   (quantification, chargement, sparsité/spéculation, modèles) ; III vers le système (à venir,
   discussion, travaux futurs) ; annexes (protocoles, outils, journaux, licences).
3. Chapitres rédigés FR puis EN, un commit par paire.
4. Construction des deux PDF (latexmk -lualatex, biber), zéro erreur, zéro référence manquante.

## Journal
- 2026-10-15 10:20 : lecture SOCLE + 01, 02 (+ dérivations), 04, 05, 06 ; 03 survolée.
  biber répond (2.21) : le blocage signalé par 02 ne se reproduit pas.
  Pas de `make` sur la machine : construire.sh (Git Bash) fait foi, Makefile pour qui a make.
- 12:05 reprise (prédécesseur mort en plein pas) : arbre sale = chapitres 06, 07, 08 rédigés FR+EN,
  intro et état de l'art complétés, graphes/schémas chargement, sparsité, modèles ; une construction
  orpheline tournait (construire.sh, PID non à moi, laissée finir). EN construit 114 p. sans erreur.
  FR : échec à l'impression de la bibliographie (« _ » nu de 03-entropie.bib, note ZipServ) : .bbl
  d'une passe antérieure à la carte de biber ; refait en effaçant .fdb_latexmk/.bbl/.bcf : 118 p.
  Commits aa616ae (chapitres) et 7dcc8df (PDF).
- Piège latexmk : après une erreur, il renomme .bbl/.bcf en *-SAVE-ERROR et refuse ensuite
  (« gave an error in previous invocation ») : effacer .fdb_latexmk, .bbl, .bcf de la langue.
- Essai rapide d'un seul chapitre (25 s au lieu de 15 min) : memoire/essai/ (ignoré par git),
  lualatex "\def\CHAP{../fr/chapitres/04-formulation}\input{essai-fr}".
- 12:50 chapitre 04 « Formulation » FR+EN commité (7442507) : équation du jeton, prop. des temps
  d'étage, hyp. c^β, problème (def:probleme), élasticités (prop + corollaire ornement), exemple
  A.3, fenêtre, α > 1 − ρ, témoins. \argmax ajouté au préambule. CSV archi-* déjà tirés pour 09.
- Prochain : 09 (architectures candidates A, B, C ; correction du partisan B : B1 8,88 barré →
  6,16 ; B3 ; mesures provisoires gpt-oss-20b), puis 10, 11, annexes A, B, C, construction, PDF.
- 13:00-14:00 : 09 « Architecture » FR+EN (candidates, prop:raffinement, B1 barré, B3/λ, débat,
  décision finale de l'arbitre f0b0fea, F1 passes 1 et 2, format .trc, mesures provisoires 20b :
  base llama.cpp, localité, ρ = 0,577) ; 10 « Discussion » ; 11 « Travaux futurs » ; annexes A
  (protocoles), B (outils), C (journaux) ; tables B et C engendrées par outils/annexes.py (appelé
  par construire.sh). Résumés corrigés (2,6 bits barré). Bibliographies 07-synthese et
  decisions-partisan-b ajoutées au préambule.
- PIÈGE de l'outil Bash ici : « \ » devient « \ » dans la commande (heredoc, sed, python -c) ;
  pour tout texte LaTeX, écrire le script avec l'outil d'écriture de fichier, ou éditer en place.
- Construction complète lancée (build3) ; prochain : vérifier zéro erreur/référence, commiter PDF.
- 15:10 reprise (nouvel agent). build3 avait fini : EN 142 p., FR 146 p., zéro erreur ; PDF commités (6ae8a27).
- 03-entropie finie (REPRISE-03 : « livrable complet », dernier commit f75d2cc) : chapitre « Compression sans
  perte » écrit (FR d'abord). Chapitres renumérotés : 06-entropie, 07-chargement, 08-sparsite, 09-modeles,
  10-a-venir, 11-discussion, 12-travaux-futurs (git mv). Figures : graphes/entropie.tex, schemas/entropie.tex ;
  CSV : donnees_figures.py (entropie_*), calculs_entropie.py (entropie d'un min-max, calcul exact et
  Monte-Carlo, seuils) appelé par construire.sh et Makefile ; listings/rans-v4.wgsl (extrait vérifié par diff).
- Corrections portées (barrées dans le chapitre, à signaler à l'orchestrateur) : 03 § 6 « plage ≈ dix fois σ
  pour 1 bit » faux (calcul exact : jamais en min-max, 31-34 σ en symétrique) ; 03 § 4.2 « 130 milliards de pas,
  moitié du plafond » : la v4 fait un pas par octet (65 G pas/s, quart du plafond, borne de latence probable).
- Piège cleveref : les listings sont du type « listing » → \crefname{listing} ajouté (sinon « liste »).
- Prochain : chapitre EN 06-entropy, essai, puis intro/état de l'art enrichis, notations, construction complète.
- 16:30 chapitre 06 EN écrit (fbd0bcd) ; état de l'art enrichi FR+EN (b963a3c : chronologie, fenêtre de
  Denning et textures virtuelles, tableau des leviers ; sources/etat-de-l-art.bib, Denning relu par Crossref) ;
  intro, contributions, plan et résumés complétés (55e1a16). Construction complète lancée (build4).
- PIÈGE index partagé : d'autres agents committent l'index entier ; toujours `git add F && git commit -- F`
  dans la même commande (pathspec), jamais de fichiers indexés laissés en attente.
- Prochain : vérifier build4 (zéro erreur, zéro référence manquante), commiter les PDF.
- 16:20 build5 : EN 169 p., FR 173 p., zéro erreur, zéro référence/citation manquante, biber sans
  avertissement (9d20a81). build4 avait échoué : styles TikZ « etage »/« flux » de schemas/entropie.tex
  écrasaient ceux de schemas/machine.tex (même nom, chargés après) → renommés entetage/entflux/entmot.
  RÈGLE : préfixer tout style TikZ par son chapitre. Construction complète : 18 min.
- ÉTAT : rien en cours. Restes possibles : Tome II (notes moteur/*-pour-le-memoire.md) après J1 ;
  boîtes trop larges préexistantes (annexe C l. 76, notations l. 49) ; signaler à 03 les deux corrections.
- 2026-10-29 chaîne des Tomes I et II réparée (fd462d4) : chaque outil lit le dépôt au commit de sa
  publication (constante en tête) : annexes.py b8af154, tome2_format.py 283b64c, tome2_annexes.py 90e3945,
  tome2_chemin_noyaux.py commit de chaque légende. Volumes des journaux : Tome I par règle (CRLF sauf
  mesures/moteur/ au blob), Tome II par le relevé memoire/tome2/annexes/volumes-mesures-moteur.csv
  (disque mêlé LF/CRLF, aucune règle ne tient ; refaire par tome2_annexes.py --relever-volumes, qui vérifie
  que le disque porte l'objet du commit). Les tables des figures lisent toujours l'arbre (texte compilé).
- Preuve : 8 outils en code 0, sorties égales au bit au commit ; construire.sh code 0 en 20 min,
  EN 169, FR 173, Tome II EN 233, FR 237 ; texte page par page égal aux PDF commités, seules
  creationDate et modDate changent. PDF reconstruits laissés non commités (décision de Stone).
- PIÈGE : annexes.description(chemin) est prise par tome3_annexes.py (qui remplace annexes.DEPOT) : ne
  pas changer sa signature.
- Reste : les annexes B (FR, EN) du Tome I disent « elle suit le dépôt » ; c'est désormais le dépôt à sa
  publication (texte des tomes non touché).
