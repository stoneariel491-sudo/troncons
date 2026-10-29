# Note de reprise : le correcteur de l'article court

Rôle : corriger l'article (`memoire/article/{en,fr}/troncons-article.tex`) selon `JUGEMENT-article.md` (commit
0e4dac8), dans les deux langues : les trois graves, puis les mineurs faisables proprement. 2026-10-29. Style
télégraphique. Branche de l'arbre de travail `stone/goofy-feynman-9939ea` (pas `main` ; fusion : orchestrateur).

## État

- **Fait** : G1, G2, G3 levés dans les deux langues ; mineurs M1 à M18 faits (détail ci-dessous). Aucune mesure
  neuve : texte, bibliographie et script de construction seulement.
- **Construit** : `bash memoire/article/construire-article.sh tout`, code 0. **EN 14 pages, FR 14 pages** (avant :
  13 et 14 ; les ajouts de G1 à G3 et de M12 à M16 font la page de plus en anglais). 0 erreur, 0 renvoi ou citation
  indéfini, 0 « Rerun », 0 boîte trop pleine ou creuse, BibTeX 0 avertissement. Paquets arXiv refaits et compilés
  seuls (pdflatex trois fois, sans bibtex) : 14 et 14 pages, égales à l'article.
- **Vérifié** (journal : `memoire/article/correcteur/verifications.txt`) :
  - `refaire_chiffres.py` (juge) : 156 chiffres sur 156 tiennent, présents dans EN et FR.
  - `parite_nombres.py` (rédacteur) : 287 nombres distincts, 926 occurrences de part et d'autre, parité tient ;
    `--casser` tombe, code 1.
  - `parite_structure.py` (juge) : structure 58/58, citations 33/33 dans le même ordre, provenance 32/32, figures
    5/5, `\barre` 1/1, `\textbf` 39/39, `\emph` 10/10 ; nombres dans l'ordre 877/877, mêmes quatre écarts d'ordre
    des mots qu'au jugement (« RTX 4060 de 8 Go », « KL de 0,00308 contre », « 1.0 », « 3,5 ») : multiensemble égal.
  - `longueur_resume.py` : EN 1 808 (LaTeX brut) / 1 746 (approché) ; FR 1 875 / 1 805 ; limite 1 920. Le français
    avait 16 caractères de marge, il en a 45 : le résumé a été resserré dans les deux langues pour faire place à G3
    et M1 (« décodeur et noyaux inchangés » ; la méthode en trois mots : « juges indépendants »).
  - `chemins_cites.py` : 4 « absents » dans chaque langue, les mêmes qu'au jugement (noms courts relatifs au
    chemin cité juste avant) ; le seul chemin neuf est écrit en entier (`genome/pistes/spectres/spectres.md`).
  - Témoin neuf du script (M17) éprouvé : le paquet anglais compilé en une seule passe laisse « Label(s) may have
    changed », le grep du script le voit (il ferait sortir en code 1) ; après trois passes, 0.

## Les graves

- **G1, nouveauté.** Trois sources neuves lues à leur page arXiv le 2026-10-29 (résumé, et la section utile en HTML) :
  - NxFP (Lo, Wei, Brooks), arXiv:2412.19821 v1 2024-12-15, § 4.3 « Code Recycling » et figure 6 : le code 1000
    (−0) remappé à la moitié du plus petit niveau, appliqué à MxFP4 ; aucune fréquence de −0 mesurée.
  - RaZeR (Chen et al.), arXiv:2501.04052 v1 2025-01-06, v3 2026-01-31 : NVFP4, le zéro redondant remappé à des
    niveaux de plus via le bit de signe libre de l'échelle FP8 ; format avec perte ; MXFP4 seulement en base de
    comparaison ; ni fréquence des −0 ni information du signe.
  - Heilper et Singer, arXiv:2508.19263 v1 2025-08-20, § 3.4 : pour le FP4, « targets only the scaling factors and
    stores the quantized values uncompressed ».
  - Ce qui change dans le texte : la phrase « We know of no prior work… » remplacée par le texte du jugement (§ 5),
    **précisé par ma lecture** : Heilper et Singer ne compressent, en FP4, que les échelles (le jugement écrivait
    « étendu au FP4 » sans le dire). Phrase neuve dans l'introduction : pourquoi on ne réaffecte pas le code (on garde
    le modèle tel que publié, chaque poids à sa valeur). Contribution 1 réécrite : la mesure d'abord, l'énoncé dit
    « élémentaire ». Trois entrées au `.bib` (commentaire : source neuve, lue le 2026-10-29).
- **G2, exactitude du moteur.** (a) introduction, (b) travaux liés, (c) conclusion : les reformulations du jugement,
  mot pour mot à l'ordre près. (d) § 3.1 : « sur la fenêtre 0 (255 positions) avec un cache KV en f16 » ; phrase
  neuve : l'écart de llama.cpp, sur le 20b, vient surtout de son arrondi de la rampe YaRN ; en KV f32, troncons au
  plancher du format. Lu dans `memoire/tome2/en/chapitres/07-resultats.tex` (tableau C4, « Six times closer,
  requalified », 55 % sur la fenêtre 0 du 20b). Citation `peng2023yarn` ajoutée (reprise de
  `memoire/sources/moteur-R.bib`, comme le Tome II la cite).
- **G3, la carte.** Résumé : « host working set of 384 MB and a GPU footprint set by the card, not by the model
  (about 6.3 GB of its 8 GB) » ; § 3.1 : « pinned memory included », « of host memory » pour llama.cpp, les deux
  moteurs se servent de la carte, troncons 6 317 303 600 octets (Tome II, § C10, lu) ; conclusion idem ; « Memory no
  longer follows… » devient « Host memory… ».

## Les mineurs (tous faits, deux langues)

- M1 résumé et contribution 4 : « on gpt-oss-20b, at the disk stage ».
- M2 ×2,22 : « two sessions of the same morning, Volume II » (Tome II, 07 l. 256).
- M3 remarque : « fair coins, independent of everything else ».
- M4 « a fair coin that neither the scale class nor the other nibble of its byte predicts ».
- M5 proposition A1 : version de `gemv.cuh` du commit 4473050 (celle de l'arbre à 000cef9) ; limites : 0be464a,
  noyau d'aujourd'hui, lecteur des valeurs en paramètre de patron, mêmes `fmaf` en mode exact, et c'est la version
  de l'arbre quand le témoin des 8 640 lignes a été commité (a50c380, 08 h 47, après 0be464a, 08 h 31). Vérifié :
  `git log` de `gemv.cuh` n'a que ces deux commits ; `git diff 4473050 0be464a` relu.
- M6 légende de la figure 2 : « Over all 540 CODES_CTX tables of both models ». La figure elle-même (Tome III) n'est
  pas touchée ; H1 reste au Tome III.
- M7 tableau 2 : ligne « stream bits per weight » / « bits de flux par poids », et la ligne de source dit ce que
  compte chaque ligne (0,12563 en flux sur le 120b, `tailles.json`, `gain_bpp_flux`) ; figure 3 (a) : « code streams
  of each tensor ». Le 3,26 % reste (juste à l'arrondi, jugement M7).
- M8 « about 2.0 MB » (deux endroits).
- M9 « none of the 36 passes of the judge's two sessions (120b and 20b) ».
- M10 « (Translated from the French original.) » en anglais ; « (Texte d'origine, en français.) » en français.
- M11 les requêtes rapides : 3,5 % avant une fin de tronçon v1.0, ou exactement à une fin de tronçon v1.2
  (`JUGEMENT-placement.md` § 5.6, relu).
- M12 la garde : hétérogénéité des couches (8 à 23 : 38 à 60 %) et bascules secondaires ; la cascade verticale
  stricte, un quart (`genome/pistes/tropicale/JUGEMENT.md` §§ 4.2 et 12, relus).
- M13 spectres : « What holds, and was judged : 48 of 48 » ; la queue aux lignes géantes et l'échelle par ligne
  dites exploratoires, ni déclarées ni jugées (`spectres.md` § 4.3, relu).
- M14 (i) 0,0314 « against the same engine without the bias » (`JUGEMENT-routeur-ligne.md` : base P0) ; (ii) cinq
  pistes ouvertes (P1, P2, P4, P5, P6, d'après leurs jugements et le chapitre 6 du Tome III), l'étage inclusif
  devient un résultat de côté (« n'ajoute rien tant qu'il n'est pas plus grand que le cache en VRAM »,
  `P2/resultat.md` l. 57) ; (iii) tableau 5 : seuils « declared per lead (Volume III, chapter 6) ».
- M15 « the announced gains of the fast mode » ; compagnon du 120b = frontière, mutation jamais écrite
  (`07-genome-synonyme.md` l. 37) ; « paired difference ΔKL = −0.1565 ± 0.0334 ».
- M16 tableau 5 : « r(R/B) ≥ 1.769 (120b) and ≥ 1.227 (20b): announced gain × (1 − 2σ) » (`JUGEMENT-construction.md`
  l. 303 et 327).
- M17 `construire-article.sh` : pdflatex trois fois après bibtex ; l'article et le paquet tombent sur « Rerun to
  get » ou « Label(s) may have changed » ; le paquet est compilé trois fois.
- M18 titres des tomes : `\TitreTomeI`, `\TitreTomeII`, `\TitreTomeIII` définis dans chaque `.tex`, dans sa langue,
  depuis les pages de titre (Tome I : titre et sous-titre de `memoire/commun/page-titre.tex`) ; le `.bib` les appelle
  entre doubles accolades, la casse ne bouge plus.

## Décisions (réponses par délégation du 2026-10-29, réversibles)

- Le texte de G1 suit le jugement, mais ce que j'ai lu le précise (Heilper et Singer : échelles seulement) : on écrit
  ce que la source dit, pas plus.
- Pas de second disque, pas de séance v1.2 contre llama.cpp, pas de second modèle : ce sont des mesures, hors de mon
  rôle (consigne : pas de mesure). Écrit dans « ce qui reste ».
- Le jargon (J1, s2, A-C2) et « trois histoires dans le résumé » (§ 3 du jugement, hors des graves et des mineurs) :
  laissés ; le résumé est seulement resserré.
- Aucun trailer, aucune adresse dans les commits ni les fichiers (SOCLE, « La langue et le nom », règle de Stone ;
  les commits précédents la suivent). Aucune mention d'IA dans les fichiers ; la déclaration d'usage demandée par
  arXiv revient à Stone, rien n'est écrit.

## Ce qui pourrait être faux

- Les trois sources neuves ont été lues par un outil qui résume les pages (arXiv abs et HTML), pas dans leur PDF
  entier. La citation de Heilper et Singer (§ 3.4) est celle que l'outil a rendue. La recherche des travaux
  antérieurs reste celle du juge (deux recherches) ; d'autres travaux peuvent exister.
- NxFP § 4.3 ne nomme pas les formats ; « appliqué à MXFP4 » vient de sa figure 6 et de son § 7.6 (lecture de l'outil).
- Compilations sous MiKTeX, pas sous le TeX Live 2025 d'arXiv : une page d'écart reste possible.
- Le « 6,3 Go de ses 8 Go » : 6 317 303 600 octets = 6,32 Go décimaux, la carte a 8 188 Mio (8,59 Go) ; « 8 Go » est
  la capacité nominale, comme le titre et l'introduction la disent.
- Les chiffres de M12, M14, M16 sont lus dans les jugements cités, pas recalculés depuis les journaux bruts (sauf
  ceux que `refaire_chiffres.py` recalcule déjà : 1,769, 1,227, 0,0314).
- Un écart de méthode à dire : les trois entrées neuves du `.bib` et le passage des titres en macros ont été écrits
  par un script Python lu sur l'entrée standard, ce que les consignes déconseillent pour du LaTeX ; le résultat est
  relu (`git diff`), BibTeX ne dit rien, les deux bibliographies rendent les bons titres.

## Ce qui reste avant soumission

1. Contre-jugement de ces corrections par un juge qui ne les a pas écrites (SOCLE, « la barre »).
2. À Stone seul : l'emplacement public du code, des journaux et des tomes (`\Emplacement` est encore « [location to
   be filled in] » : sans lui l'article renvoie à un dépôt introuvable) ; la forme du nom d'auteur (arXiv demande
   « Prénom Nom ») ; la forme bilingue (une soumission ou deux) ; compte, parrainage, catégorie (cs.LG, cs.DC
   proposé), licence ; la déclaration d'usage d'outils qu'arXiv demande.
3. À la soumission : choisir pdflatex explicitement ; déposer `memoire/article/{en,fr}/arxiv-{en,fr}.tar.gz`.
4. Ce qu'un relecteur demandera et qui demande des mesures (hors de ce rôle) : un second disque ou une seconde
   machine pour le ×1,44 (à défaut, le § 4.5 se lit comme une étude de cas) ; la v1.2 contre llama.cpp dans une même
   séance ; un second modèle MXFP4.
5. H1 (Tome III, « 540 tables des couches 0, L/2, L−1 ») : à l'orchestrateur ; non touché.

## Fichiers

- Sources : `memoire/article/{en,fr}/troncons-article.tex`, `memoire/article/commun/troncons-article.bib`,
  `memoire/article/construire-article.sh`.
- Construits : `memoire/article/en/troncons-article.pdf`, `memoire/article/fr/troncons-article.pdf`, leurs `.bbl`,
  `troncons-figures.pdf` (refaits par lualatex, même source), `arxiv-en.tar.gz`, `arxiv-fr.tar.gz`.
- Journal : `memoire/article/correcteur/verifications.txt`.
