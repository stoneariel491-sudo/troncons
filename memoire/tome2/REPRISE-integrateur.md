# Reprise : intégrateur du Tome II

Rôle : les maîtres `memoire/tome2/{en,fr}/troncons-tome2-{en,fr}.tex`, la page de titre, les notations,
les annexes (protocoles et outils du moteur), l'extension de `memoire/construire.sh`, la construction
des deux PDF (latexmk -lualatex, biber) : zéro erreur, zéro référence ou citation manquante, zéro figure
absente. Corriger ce qui casse sans réécrire le fond ; unifier notations et renvois au Tome I.
Aucun calcul sur la carte. Aucune question (délégation, marquée).

Fichiers à moi : `memoire/tome2/{en,fr}/troncons-tome2-*.tex`, `memoire/tome2/commun/*`,
`memoire/tome2/{en,fr}/annexes/*`, `memoire/outils/tome2_annexes.py`, `memoire/construire.sh`
(partie Tome II), cette note, les deux PDF.

## Journal
- 2026-10-16 : départ. Aucune note d'intégrateur avant moi : rien à reprendre. Arbre propre
  (seuls des __pycache__ non suivis). Lu SOCLE, les quatre REPRISE des rédacteurs, maître et
  préambule du Tome I.
- Constats à corriger au maître :
  - `\Racine`, `\Depot` en `\newcommand` dans le préambule commun : passés en `\providecommand`
    (le maître du Tome II les pose à `../..` et `../../..` avant de le charger ; Tome I inchangé).
  - `\DonneesTomeDeux` : deux sens. graphes/architecture.tex le pose à `figures/donnees/tome2`,
    cache.tex et reference.tex à `figures/tome2/donnees` ; le premier chargé gagne (01 avant 05) :
    les CSV t2r-*, t2o-* seraient introuvables. Renommé dans graphes/architecture.tex
    (`\DonneesTdArch`).
  - Clés en double (biber « Duplicate », construire.sh tombe) : belady1966 (commun, moteur-O),
    duda2013ans et giesen2014interleaved (03-entropie, moteur-F), kullback1951 (tome2-reference-cache,
    tome2-resultats). mesures-gpt-oss.bib et moteur-epreuve-J1.bib ne sont pas chargés : aucune clé
    citée qui n'existe ailleurs (wilson1927 seul, dans moteur-R).
- 2026-10-16, reprise après l'arrêt propre (batterie). Arbre propre sauf `troncons-tome2-fr.synctex(busy)`,
  fichier de verrou de SyncTeX commité par erreur à la sauvegarde : retiré du suivi, motif ajouté à
  `memoire/.gitignore`.
- État trouvé : maître FR, notations, page de titre, bibliographie, fin, annexes A et B (EN et FR)
  écrits ; doublons de clés retirés (belady1966, duda2013ans, giesen2014interleaved, kullback1951) ;
  `\DonneesTdArch` en place. Manquaient : maître EN, construire.sh, construction complète.
- Maître EN écrit (`tome2/en/troncons-tome2-en.tex`), miroir du FR : `\anglaistrue`, parties
  « The program », « The truth and the memory », « The judgement ».
- `construire.sh` étendu : cibles `tome2`, `tome2-en`, `tome2-fr`, `tome1` ; sans argument, les
  quatre PDF ; les cinq outils tome2_*.py avant la construction (chacun tombe au premier écart) ;
  latexmkrc en chemin relatif (latexmk est un programme Windows, un /c/… de Git Bash ne lui parle
  pas) ; contrôle ajouté des fichiers ou figures absents dans le journal. Makefile : mêmes cibles.
- Défaut trouvé par la construction : le témoin des options de `tome2_annexes.py` lisait
  `\option{nom}` dans l'en-tête en commentaire de B-outils.tex (« option en trop : nom / name »),
  et la sortie en erreur était cachée par un `| tail` à mon premier essai. Corrigé : les commentaires
  TeX sont retirés avant la lecture. Témoin : tient (0 écart, 35 options) ; cassure `--casser` : tombe
  (code 1).
- Première construction complète : FR 235 pages, EN 231 pages ; 0 erreur, 0 référence ou citation
  indéfinie, 0 fichier absent, biber sans doublon (un seul avertissement : xiao2024sinks porte year
  et date, moteur-K.bib, sans effet sur la sortie). « No driver for 'standard' » : repli générique de
  biblatex pour ieee754-2019, l'entrée s'imprime (même cas que ieee2008xts au Tome I).
- Lignes trop larges, rattachées à leur fichier par un analyseur du journal (pile des fichiers) :
  corrigées, mise en page seule : bibliographie 37 à 51 pt (empreinte hexadécimale, \sloppy dans
  fin.tex) ; annexe A, critères des étapes 8 pt (colonnes) ; table des outils 2 pt (générateur) ;
  ch. 01 6 pt (\allowbreak après « HoteEpingle:: », EN et FR) ; ch. 05 23 pt (figure KV à deux
  panneaux, largeur 0,52 → 0,48, figures/tome2/reference.tex). Restent < 5 pt : deux numéros de page
  de la table des matières (xvii, 139), « <journal>.erreur.json » au ch. 01 (2,6 pt), le tableau des
  blocs du ch. 05 EN (4,6 pt). Laissés : invisibles à l'impression.
- Notations unifiées : l'échelle E8M0 vaut 2^(e-127) (OCP) et les ch. 04 et 05 écrivent K[c]·2^(e-128)
  avec K doublé ; la table des notations dit maintenant les deux. Vérifiés contre les chapitres :
  u16 = 2^-11, M = 4 096, L = 2^16, N = 256 macro-pas. Renvois au Tome I : numéros de chapitres et
  d'annexes de la table de correspondance vérifiés contre le maître du Tome I ; aucun numéro de
  chapitre du Tome II écrit en dur dans le texte (seulement dans des commentaires).
- Notations changées : reconstruction complète des quatre PDF par `./construire.sh` sans argument
  (2026-10-16) : code 0. Tome I EN 171 pages, FR 173 ; Tome II EN 231, FR 235. Second chemin :
  pdfinfo donne les mêmes nombres de pages ; pdftotext : 0 « ?? » dans les deux PDF du Tome II.
  Table des matières : introduction, parties I à III, chapitres 2 à 10, conclusion, annexes A et B,
  bibliographie, dans le même ordre en EN et en FR.
- À porter à l'orchestrateur : construire le Tome I régénère ses annexes engendrées
  (`memoire/annexes/journaux.tex`, `outils.tex`) depuis l'état du dépôt (mesures/moteur/ : 118 → 1 078
  fichiers ; 96 → 101 outils ; EN 169 → 171 pages). Ce n'est pas du Tome II : je n'ai rien commité du
  Tome I, ses quatre fichiers ont été remis à HEAD (écrits par git show, pas checkout). Décider si le
  Tome I se fige à sa date (outil d'annexes au commit du 15 octobre) ou suit le dépôt.
- Hors de mon rôle, vus en passant : `outils/__pycache__/*.pyc` commités par la sauvegarde fdf550a
  (la racine n'ignore pas __pycache__) ; __pycache__ non suivis sous mesures/moteur/{E,O,R,epreuve-J1}.
