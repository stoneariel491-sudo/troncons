# Note de reprise : l'article court (porte d'entrée des trois tomes, pour arXiv)

Rôle : rédacteur de l'article court. 2026-10-29. Style télégraphique.

## État

- **Fait** : article anglais `en/troncons-article.tex` puis version française fidèle `fr/troncons-article.tex` ;
  mêmes sections, figures, tableaux, nombres (parité vérifiée par outil, ci-dessous). Construits sans erreur :
  EN 13 pages, FR 14 pages ; 0 erreur, 0 avertissement (ni renvoi ni citation indéfinis, ni boîte trop pleine),
  BibTeX sans avertissement ; toutes les polices Libertinus, incorporées.
- **Construction** : `bash memoire/article/construire-article.sh [en|fr|tout]` (code non nul à la première erreur
  ou à un renvoi indéfini). Étapes : figures (lualatex), article (pdflatex, bibtex, pdflatex, pdflatex), paquet arXiv
  `<langue>/arxiv-<langue>.tar.gz` (à plat : `troncons-article.tex`, `.bbl`, `troncons-figures.pdf`), puis
  **témoin du paquet** : l'archive est dépliée dans un dossier temporaire et compilée seule comme arXiv le fera
  (pdflatex deux fois, sans bibtex) ; même nombre de pages exigé. Tenu pour les deux langues.
- **Commité** : sources, PDF, `.bbl` (forcé par `memoire/article/.gitignore`, car `memoire/.gitignore` ignore
  `*.bbl`), PDF des figures, archives arXiv, outils et leur sortie.

## Décisions (réponses par délégation du 2026-10-29, réversibles)

- **Moteur TeX : pdflatex + BibTeX (natbib, unsrtnat / unsrtnat-fr).** Pages d'aide d'arXiv lues le 2026-10-29 :
  https://info.arxiv.org/help/submit_tex.html (« arXiv fully supports and automatically recognizes PDFLaTeX » ;
  le .bbl est utilisé s'il est présent, son nom doit égaler celui du .tex ; pour biblatex sous TeX Live 2025, seul le
  format de .bbl 3.3) et https://info.arxiv.org/help/faq/texlive.html (TeX Live 2023 et 2025, 2025 par défaut ;
  processeurs : tex, pdftex, latex, pdflatex, xelatex depuis novembre 2025 ; **LuaLaTeX n'y figure pas**). Raison en
  une ligne : les tomes sont en lualatex + biber, qu'arXiv ne prend pas ; BibTeX évite le couplage de version du
  .bbl de biblatex. `\pdfoutput=1` en première ligne.
- **Figures autonomes** : aucune figure neuve. Les cinq figures jugées du Tome III (III-8.1 roue des codons, III-8.2
  carte des 256 octets, III-8.3 théorème, III-8.6 J1, III-8.6 bis J1 refait : motif croisé et cascade) sont tirées
  telles quelles de `memoire/figures/tome3/codon-figures.tex` par `figures/figures-corps.tex` (lualatex, préambule
  commun des tomes, paquet `preview` : une page par figure, dans une boîte de 156 mm, la largeur où les juges les
  ont vues), une fois par langue (`figures-en.tex`, `figures-fr.tex`, qui posent `\ifanglais`). Le PDF devient
  `<langue>/troncons-figures.pdf`, inclus par `\includegraphics[page=…]`. Seule la taille change : 0,8 ; 0,9 ;
  0,78 ; 1 ; 0,92 de 156 mm. Les légendes de l'article sont réécrites, plus courtes, depuis les légendes jugées.
- **Polices** : Libertinus en pdflatex (`libertinus`, `libertinust1math`), comme les figures (Libertinus par
  fontspec).
- **Auteur** : « Stone », rien d'autre (page de titre des tomes). Date : 29 octobre 2026.
- **Catégorie arXiv proposée** : cs.LG en principal, cs.DC en liste croisée (un format sans perte et un moteur ;
  la vitesse est un résultat de système). Choix, compte et parrainage : Stone.
- **Disponibilité** : `\Emplacement` = « [location to be filled in] » / « [emplacement à remplir] », défini une fois
  dans chaque .tex et repris par la bibliographie (les trois tomes en rapport technique). Aucune adresse inventée.
- **Bibliographie** : `commun/troncons-article.bib`, 28 entrées (toutes citées) reprises des .bib du projet (fichier d'origine en
  commentaire au-dessus de chaque entrée), réécrites de biblatex en BibTeX ; aucune source neuve. La date de
  consultation passe par `\Consulte{…}`, défini dans la langue de l'article.
- **Étiquettes du français** : `sec-…`, `fig-…` au lieu de `sec:…` (babel/french rend « : » actif, et `\cref` sur une
  étiquette à deux-points tombait : « Missing \endcsname »). natbib chargé avant babel, comme french le demande.

## Chiffres de la consigne, contrôlés contre les fichiers (et ce qui a changé)

- **« −3,56 % de bits » ne vaut pas pour le 120b dans le format.** −3,56 % est la mesure de l'éclaireur sur 12
  tenseurs de référence du 20b, contexte compris (`genome/01-eclaireur.md` l. 23 et 211 : 3,843137 → 3,706142). Dans
  le format v1.2, sur le 120b : 3,85456 → 3,72892 bits par poids d'expert (**−3,26 %**), tronçons ×0,96751 (−3,25 %),
  fichier 57 730 662 400 → 55 930 175 488 octets (−3,12 %) (`mesures/genome/construction/codon/tailles.json`,
  `genome/06-codon-v1-2.md` § 6). L'article écrit 3,26 % et 1,80 Go (1 800 486 912 octets).
- **×1,389 du motif croisé** : 1,389 dans `genome/JUGEMENT-placement.md` (médianes arrondies 2,501 / 1,801) ;
  1,388 depuis les médianes non arrondies (`memoire/figures/tome3/donnees/codon-j1-motif.csv`, 2,5011 / 1,8014), et
  c'est 1,388 que la figure jugée affiche. L'article écrit ×1,39 et dit les deux, une fois.
- **×1,44** : r = 1,454 (lot A, s2, `j1-s2-verdicts.json`) et 1,442 (juge de la construction, § 6.2) ; ×0,715 et
  les autres nombres de la consigne se retrouvent dans leurs fichiers.
- Le moteur (Tome II) : 384,19 Mo de pointe, 1,965 jeton/s avec la garde, ×2,22 contre 0,884 (llama.cpp
  `fit -t 16`), KL 0,00308 contre 0,0607 : `memoire/tome2/en/chapitres/07-resultats.tex` et ses sources
  (`mesures/moteur/O/`, `mesures/moteur/epreuve-J1/`).

## Outils de cet article (commités)

- `outils/medianes_j1.py` → `outils/medianes_j1.json` : médianes par fichier des passes du J1 s2 (tableau 3 :
  temps de lecture 0,391 / 0,259 s, décodage 62,1 / 42,7 ms, copie 96,2 / 68,2 ms, débit vu 1,81 / 2,65 Go/s).
  Témoin : médianes de jetons/s égales à `j1-s2-verdicts.json` ; cassé (verdict faussé de 0,01) → code 1. Tenu.
- `outils/parite_nombres.py` : mêmes nombres, autant de fois, dans EN et FR (corps, commentaires retirés,
  décimales normalisées). Résultat : 274 nombres distincts, 876 occurrences de part et d'autre, **parité tient** ;
  `--casser` (un nombre ajouté au FR) → tombe, code 1.
- Correction du message du commit f22889e, dite et non effacée : il écrit « parité des nombres EN/FR tenue (276
  témoins de l'outil…) » ; ~~276 témoins~~ : l'outil compte 274 nombres distincts et 876 occurrences de part et
  d'autre (sortie ci-dessus). Le reste du message tient.

## Ce qui pourrait être faux

- Le compte de pages d'arXiv peut différer d'une page : TeX Live 2025 d'arXiv contre MiKTeX 26.5 ici (versions de
  libertinus-type1, natbib, microtype). Le témoin du paquet ne le prouve que pour MiKTeX.
- Les PDF de figures sont produits par LuaTeX (PDF 1.5, polices OpenType incorporées) ; arXiv accepte les PDF
  inclus, mais ne les régénère pas : toute retouche d'une figure passe par `construire-article.sh`.
- Les phrases sur les travaux liés résument des articles cités par leur résumé (comme les .bib du projet le
  disent) ; aucune n'a été relue dans le texte intégral pour cet article.
- La reprise des chiffres a été faite à la main depuis les fichiers cités ; seuls le tableau 3 et la parité EN/FR
  sont recalculés par outil. Un juge de l'article (SOCLE, « la barre ») devrait refaire chaque nombre par son
  chemin.
- Le travail est commité sur la branche de cet arbre de travail (`stone/goofy-feynman-9939ea`), pas sur `main` :
  la session tournait dans un arbre de travail ; la fusion revient à l'orchestrateur.

## Ce qui reste

- Relecture par un juge qui n'a pas écrit l'article (chiffres, traduction, conformité arXiv).
- Remplir `\Emplacement` (deux .tex) quand Stone aura choisi où publier le code et les tomes ; reconstruire.
- Soumission : décision et geste de Stone (compte, catégorie, parrainage, licence de l'article).
