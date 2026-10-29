# Tome III : le plan de rédaction

Écrit le 2026-10-29 par l'ossature du Tome III, à la demande de Stone (« finissons » : un vrai mémoire comme
les Tomes I et II, autour des figures déjà tracées et jugées). Lu avant : `SOCLE.md`, `INVENTAIRE-figures.md`
(§ 0 le plan, § 3 les réserves R1 à R6), `REPRISE-figures.md`, `CONVENTIONS-figures.md`, le Tome II (maîtres,
`commun/`, chapitres 02 et 07, annexes A et B), les en-têtes des huit fichiers de figures, des deux fichiers
des pistes, et les sommaires des livrables et des notes « pour le mémoire » cités ci-dessous.

Ce plan dit **où lire** et **quoi poser** ; il ne donne aucun chiffre à recopier. Chaque nombre du texte se lit
dans le fichier commité qui le porte, au moment d'écrire ; quand une source a barré un chiffre, c'est la
correction qui compte.

## 0. Ce qui vaut pour tous les chapitres

**Le squelette.** Chaque chapitre a son fichier sous `memoire/tome3/fr/chapitres/` (et le même nom sous
`en/chapitres/`) ; en tête, en commentaire : les sources à lire, les sections prévues, les figures à placer
avec leur macro et leur étiquette, les clés bibliographiques. Le rédacteur remplace les commentaires par le
texte ; il garde le `\chapter{…}` et son `\label`.

**La forme (modèle : Tome II, `memoire/tome2/fr/chapitres/02-format.tex`, `07-resultats.tex`).**
1. `\begin{origine}` : **Au départ** (ce qui était acquis), **Ce chapitre établit**, **Il reste** ; puis
   « Sources : » avec les fichiers (`\fichier{…}`).
2. `\begin{enbref}` : le chapitre en un paragraphe, pour un lecteur qui découvre ; une analogie biologique
   s'y dit comme analogie (« comme… », « l'image est… »), jamais comme preuve.
3. Les sections : l'explication d'abord, puis la rigueur (énoncés `theoreme`, `proposition`, `lemme`,
   `corollaire`, `definition`, `hypothese`, `remarque` du préambule ; démonstrations entières, calculs posés
   pas à pas, pas seulement leur résultat).
4. Chaque nombre porte sa provenance (`\mes`, `\calc`, `\litt`) et son fichier ; une phrase démentie se barre
   (`\barre{…}`) avec ce qui l'a remplacée.
5. La dernière section : `\begin{faux}` (« Ce qui pourrait être faux »).

**Les figures.** On cite et on commente les figures jugées ; on n'en dessine aucune dans ce flux. Toutes sont
chargées une fois par `memoire/tome3/commun/figures.tex` :
- au style du Tome III : `\begin{figure}[tbp]\centering\Graphe<Nom>\LegendeFigure{<Nom>}\label{fig:t3-…}\end{figure}`
  (convention G9, `CONVENTIONS-figures.md`) ; la légende est déjà écrite et jugée : le texte la commente, il ne
  la récrit pas ;
- piste tropicale : `\GrapheTropicale…` et `\FigureTropicaleCoupe`, sans légende fournie : le chapitre écrit
  `\caption[titre court]{… \sourcefig{\fichier{…}}}` ;
- spectres : `\FigureSpectres{<page>}` (PDF compilé à part par `construire.sh`) ;
- mimétisme et coupe tropicale (PNG) : `\FigureHorsStyle{<chemin>}`, et `\HorsStyle` dans la légende.

**Les étiquettes.** Chapitres `t3<xxx>:ch` (`t3int`, `t3que`, `t3ecl`, `t3gen`, `t3dup`, `t3pre`, `t3mim`,
`t3syn`, `t3cod`, `t3sno`, `t3jug`, `t3tro`, `t3spe`, `t3dis`), annexes `t3ann:protocoles`, `t3ann:outils`,
`t3ann:journaux` ; sections `t3<xxx>:sec:…`, équations `t3<xxx>:eq:…`. Figures `fig:t3-…` (celles des pilotes).
**Imposées**, parce que des légendes jugées y renvoient par `\cref` : `fig:t3-codon-theoreme`,
`fig:t3-codon-octets`, `fig:t3-codon-colonne`, `fig:t3-codon-jalon`, `fig:t3-codon-jalon-bis`,
`fig:t3-syno-foret`, `fig:t3-syno-variantes`. Mêmes étiquettes en anglais.

**La bibliographie.** `memoire/tome3/commun/bibliographie.tex` charge tous les `.bib` utiles sans doublon de clé
(vérifié clé par clé sur tous les `.bib` commités). Plusieurs œuvres ont **deux clés** dans des fichiers
différents : en choisir une pour tout le tome (proposé : la première) :
`shannon1948` / `genome-shannon1948` ; `shannon1959` / `genome-shannon1959` ; `max1960` / `genome-max1960` ;
`marcellin1990` / `genome-marcellin1990` ; `shafipour2024seedlm` / `genome-seedlm` (à vérifier : même article ?) ;
`zhang2018tropical` / `synth-zhang2018tropical` ; `martin2018implicit` / `synth-martin2018implicit` ;
`skliar2025cacheconditional` / `skliar2024cacheconditional` (années différentes : vérifier à la source laquelle
est juste). `p6.bib` n'est pas chargé (`hobbit2024` en double) : voir l'en-tête de `bibliographie.tex`.
Une source neuve seulement avec son adresse et sa date de consultation.

**Les langues.** Le français d'abord ; l'anglais est la traduction (rôle du traducteur), mot pour mot dans les
nombres ; les fichiers `en/` renvoient au français pour leur plan.

**Construire.** `./construire.sh tome3` (ou `tome3-fr`, `tome3-en`) depuis `memoire/` ; 0 erreur, aucune
référence ni citation manquante. Un chapitre seul : `memoire/REPRISE-memoire.md` (pilotes sous `memoire/essai/`).

## 00. Introduction — rédacteur D

- **Sources** : `SOCLE.md` (les mots de Stone, cités exactement) ; les « En bref » et « D'où on part » de
  `genome/00-etat-de-l-art.md`, `05-synthese.md`, `06-codon-v1-2.md`, `07-genome-synonyme.md`,
  `JUGEMENT-construction.md`, `mimetisme/tri.md`, `pistes/tropicale/garde-tropicale.md`,
  `pistes/spectres/spectres.md` ; modèle : `memoire/tome2/fr/chapitres/00-introduction.tex`.
- **Figures** : aucune propre ; renvois.
- **À poser** : la question du génome (ses mots) ; ce que « génome » veut dire ici (analogie) ; le chemin du
  tome ; ce qui est allé au Tome II (placement disque, `genome/JUGEMENT-placement.md` § 13 point 6) ; comment lire.
- **Réserves** : aucun résultat annoncé plus fort que son chapitre ; le « Ce qui pourrait être faux » du tome est
  au chapitre 13.

## 01. La question du génome

- **Sources** : `genome/00-etat-de-l-art.md` (en entier) ; `genome/etat-de-l-art-pour-le-memoire.md` (§ 1 points
  1, 2 et 4 ; § 2.5 ; § 3 ; § 4) ; `genome/01-eclaireur.md` § 3 ; `mesures/genome/etat-de-l-art/borne-rd.csv`,
  `journaux/borne-rd.json`.
- **Figures** : III-1.1 `EclBloc`, III-1.2 `EclBorne`.
- **Dérivations** : le bloc MXFP4 au bit (valeur d'un code E2M1 sous une échelle E8M0) ; les points de
  Blahut-Arimoto comme **bornes supérieures** de R(D) (note § 2.5) ; le tableau des douze familles (00 § 2) avec
  la mesure qui juge chacune et le pronostic (00 § 4).
- **Réserves** : la courbe de III-1.2 est une borne supérieure (Blahut-Arimoto), sa légende le dit ; le chiffre
  de la frontière se lit dans 00/01, avec ses corrections.

## 02. L'éclaireur

- **Sources** : `genome/01-eclaireur.md` (en entier) ; `genome/etat-de-l-art-pour-le-memoire.md` § 1 (points 3, 5,
  6), § 2.1 à 2.4, § 3 ; `mesures/genome/etat-de-l-art/journaux/` (zero-compte, borne-rd-passe1, diagnostic-L0-E0,
  choix-delta, kl-zero-canonique.sha256, kl-*-juge) ; `memoire/tome3/JUGEMENT-figures3.md` (GJ1).
- **Figures** : III-2.1 `EclZeros`. (III-2.2 et III-2.3 non tracées : tableaux.)
- **Dérivations** (note § 2) : 2.1 exactitude au bit d'un produit scalaire après −0 → +0 ; 2.2 le lemme d'OBS
  pour la quantification ; 2.3 le facteur de Cholesky de H⁻¹ par une seule factorisation ; 2.4 pourquoi la
  mutation synonyme rend la frontière quand H = I.
- **Réserves** : la proposition 2.1 laissait le signe d'une somme partielle nulle ; la proposition A1 du
  chapitre 7/8 la renforce (dire le lien) ; le verdict de 01 § 7 tel qu'il est écrit, avec ses barres.

## 03. Le génome des poids

- **Sources** : `genome/genome.md` (en entier) ; `genome/genome-pour-le-memoire.md` ;
  `mesures/genome/genome/00-seuils-declares.md`, `csv/`, `kl/comparer10-base-contre-recette.json` (K10).
- **Figures** : III-3.4 `GenGauss`, III-3.6 `GenCourbes`. (Les autres III-3.x ne sont pas tracées.)
- **Dérivations** (tableau de la note) : lemme 1 (meilleur de N sous-espaces aléatoires : ρ ~ Bêta, E[min ρ],
  asymptote) et son corollaire ; lemme 2 (prédécesseurs dans le treillis à décalage) ; proposition 1
  (exactitude du Viterbi, Bellman) ; invariance de l'erreur par la rotation ; proposition 2 (Everett) ;
  remplissage inverse et gain de répartition (½ log₂ MA/MG) ; lemme 3 (le complément exact ne rend rien
  gratuitement) ; erreur de sortie attendue et pondération (`src/fidelite.rs`, genome § 8.2) ; comptabilité des
  bits ; coût de transcription.
- **Réserves** : **R4** : le rapport de KL de S\* vient de K10 (10 fenêtres), l'ancien chiffre à 3 fenêtres est
  barré dans 05 § 2 ; l'analogie ARN/ribosome dite comme analogie.

## 04. La duplication de gènes

- **Sources** : `genome/duplication.md` ; `genome/duplication-derivations.md` (§§ 1 à 6) ;
  `genome/duplication-pour-le-memoire.md` ; `mesures/genome/duplication/00-seuils-declares.md`, `csv/`.
- **Figures** : III-4.2 `DupParente`, III-4.8 `DupArbre`.
- **Dérivations** : proposition 1 (invariance par permutation) ; lemme 2 (gain gaussien d'un parent,
  g(ρ) = −½ log₂(1 − ρ²) et son domaine) ; lemme 3 (plancher du hasard) ; proposition 4 (gain sans perte =
  information mutuelle conditionnelle ; biais de Miller) ; proposition 5 (reconstruction identique) ; remarque 6 ;
  proposition 7 (arbre couvrant de poids maximal, Kruskal) ; lemme 8 (erreur d'un paralogue).
- **Réserves** : la fidélité de la projection de III-4.8 est dite dans sa légende (jugée) ; « ils posent le
  problème ainsi » (note) pour l'état de l'art ; l'idée échoue : le dire par les nombres.

## 05. Codage prédictif et élagage synaptique

- **Sources** : `genome/predictif-elagage-pour-le-memoire.md` (en entier) ; `genome/REPRISE-predictif-elagage.md` ;
  `mesures/genome/predictif-elagage/`.
- **Figures** : aucune tracée (III-5.1, III-5.2 proposées, non tracées) : tableaux tirés des CSV.
- **Dérivations** : § 1 codons synonymes du E2M1 (sans perte en valeur) ; § 2 entropies conditionnelles du codage
  prédictif sans perte ; § 3 cadre débit-distorsion de l'élagage et de la quantification prédictive bornée ;
  § 4 sensibilité ; § 5 erreur à la sortie des experts ; § 5 bis hebbien ; § 6 KL.
- **Réserves** : entropies idéales (pas un codec) quand c'est le cas, dit ; le sur-ajustement du hebbien (§ 5 bis).

## 06. Le mimétisme

- **Sources** : `genome/mimetisme/tri.md` ; pour chaque Pk : `resultat.md`, `pour-le-memoire.md`, `JUGEMENT.md`
  (le verdict est celui du juge) ; seuils (`mesures/mimetisme/Pk/00-*`, juges) ; dossiers de domaine pour
  l'origine des idées.
- **Figures** (hors du style commun, `\FigureHorsStyle` + `\HorsStyle`) : III-6.1 à 6.3 (P1, PNG), III-6.4 et 6.5
  (P2, PDF), III-6.7 et 6.8 (P3, PDF : la paroi est un schéma ; la Pareto est l'étage A), III-6.9 (P4, PNG sous
  `mesures/`), III-6.10 à 6.12 (P5, PDF sous `mesures/`), III-6.13 (P6, PNG). Chemins dans le squelette.
- **Dérivations** : P1 (score à décroissance exponentielle comme estimateur de taux ; continuum LRU–LFU ; deux
  réservoirs ; de l'échec du cache à la vitesse) ; P2 (lemme de Mattson et al. ; théorème 1 ; lemme 2 ; modèle de
  coût et seuil de rentabilité) ; P3 (la paroi décalée de β ; la masse de la bande ; le critère de l'étage B en
  une grandeur) ; P4 (calibration conforme fendue ; simulateur et gain) ; P5 (plus proche vecteur, énergie d'un
  verre de spin, mesure de Gibbs) ; P6 (le modèle et ses grandeurs ; variante B ; KL(f)).
- **Réserves** : P1 « ouvert », pas « tombé » (juge P1 § 0) ; P2 : Mattson 1970 à relire à la source, variante
  sélective post hoc ; **P3 : seulement ce qui est jugé ; le second tirage est en travail dans une autre session
  (R6), aucun de ses chiffres** ; P4 « ouvert, plutôt du côté de tombe » ; P5 : poids synthétiques (étape 1), le
  mécanisme annoncé ne tient pas au seuil (grave du juge) ; P6 : le « tient » de B ne pouvait presque pas tomber,
  et « les défauts ne sont pas corrélés aux petits poids » est faux (juge P6 § 0) : barrer ; R5 : figures hors
  style, dites. Vérifier chaque nombre lisible dans une figure hors style contre le jugement de sa piste.

## 07. La synthèse de la ronde

- **Sources** : `genome/05-synthese.md` (en entier, avec ses barres) ; `genome/construction-synthese-pour-le-memoire.md` ;
  `mesures/genome/construction/synthese/` et `k10/` ; `mesures/genome/etat-de-l-art/journaux/kl-*-positions.csv` ;
  `mesures/genome/genome/csv/colonnes-energie-erreur.csv` ; jugements des figures (ronde, latents).
- **Figures** : III-7.1 `SynthFrontiere`, III-7.2 `SynthErreurKL`, III-7.3 `SynthDeuxParts`, III-7.4
  `SynthColonnes`, III-7.6 `LatentsEtats`.
- **Dérivations** (note § 2) : la KL au second ordre, ½ δzᵀ(diag p − ppᵀ)δz (information de Fisher ; développer
  log Σ exp à l'ordre 2, le terme d'ordre 1 s'annule) en entier ; la part de bascule (forme, hypothèse) ; le
  cadre tropical (polyèdres, distance m/‖w₍₄₎ − w₍₅₎‖) ; le contexte d'un symbole de CODES_COL (la chaîne
  (w, k) → n → (β, u) → i(u) → col → contexte) ; proposition A1, lemme A2, lemme B2 et ses corollaires.
- **Réserves** : **R3** : III-7.1 garde le protocole à 32 experts ; rien ne la relie par un trait aux points à 768
  (III-9.6) ; **R4** : S\* par K10 ; III-7.1 ne dit plus « gagne » pour les partitions par κ (G1 du juge ronde,
  levé) ; III-7.3 : 32 experts sur 768 ; III-7.6 : fidélité de la projection dite.

## 08. Un codon synonyme dans le format (lot A)

- **Sources** : `genome/06-codon-v1-2.md` (en entier ; § 8 corrigé) ; `genome/construction-codon-pour-le-memoire.md`
  (§§ 2.1 à 2.3, § 3, barres de cadf276) ; `genome/JUGEMENT-placement.md` §§ 0, 5.3, 5.6, 5.7 ;
  `genome/JUGEMENT-construction.md` §§ 2, 6, 8 ; `mesures/genome/construction/codon/`, `…/juge/`,
  `mesures/disque/placement/juge/seance/`.
- **Figures** : III-8.1 `CodonRoue`, III-8.2 `CodonOctets`, III-8.3 `CodonTheoreme`, III-8.4 `CodonAccumulateur`,
  III-8.5 `CodonColonne`, III-8.6 `CodonJalon`, III-8.6 bis `CodonJalonBis`, III-8.7 `SchemaCodonFormat`
  (légende `CodonFormat`), III-8.8 `JconsCodon`.
- **Dérivations** : le gain exact du fondu (note § 2.1, en entier) ; proposition A1 et son corollaire f64 (§ 2.2) ;
  le lemme de l'invariant des tables (§ 2.3) ; les calculs posés (§ 3).
- **Réserves** : **R1** : le ×1,44 du J1 vient du format v1.2 **par le motif de ses requêtes de lecture**, propre
  à ce disque (A lu au motif de B, B lu au motif de A : JUGEMENT-placement) — jamais « l'état du fichier », ni
  ses octets en moins ; le gain ne se transporte pas à un autre disque sans y être remesuré ; F-J1 et F-J2 sont
  tombées. III-8.5 : la colonne a un codec réel (« pas un fichier codé » était faux : GN2, levé).

## 09. Le génome synonyme, mode rapide (lot B)

- **Sources** : `genome/07-genome-synonyme.md` ; `genome/construction-synonyme-pour-le-memoire.md` (§§ 2.1 à 2.5,
  3, 3 bis) ; `genome/JUGEMENT-construction.md` §§ 3, 5, 6, 7, 8 ; `mesures/genome/construction/synonyme/` ;
  `…/juge/figures/apparie-par-fenetre.csv` ; jugements des figures (construction, latents).
- **Figures** : III-9.1 `SynoBasePropre` et la rangée `LatentsRangee`, III-9.2 `SynoQueue`, III-9.3 `SynoForet`,
  III-9.6 `SynoVariantes`, III-9.7 `LatentsNuage`.
- **Dérivations** : le choix des symboles (01 § 5.2, comme dans le code) ; l'identité de la base propre de H
  (note § 2.2) ; proposition B1 ; proposition B2 ; le format du compagnon au bit (§ 2.5, en tableau).
- **Réserves** : R3 (768 contre 32) ; deux chiffres de vitesse du lot B **tombent comme gains du mode rapide**
  (juge § 7 : barrés) ; « la queue baisse aussi avec λ = 0 » ne se reproduit pas ; les fenêtres neuves viennent de
  wiki.test, le corpus de R1 ; III-9.7 : la borne 0,135 concerne les projections, pas les entrées réelles
  (juge 2 latents, levé) ; la lettre du panneau de la rangée diffère entre deux fichiers ((c) / (d)) : le texte
  renvoie à l'étiquette.

## 10. Le juge de la construction

- **Sources** : `genome/JUGEMENT-construction.md` (avec ses corrections du 2026-10-27) ;
  `genome/construction-juge-pour-le-memoire.md` ; `mesures/genome/construction/juge/00-seuils-declares.md`,
  `figures/` ; `memoire/tome3/JUGEMENT-figures2-construction.md` (III-10.1).
- **Figures** : III-10.1 `JconsExperts`, III-10.3 `JconsFenetres`.
- **Dérivations** (note § 1) : 1.1 le décodage rANS vectorisé est le décodage normatif ; 1.2 ce que prouve le
  témoin v1.0 → v1.2 ; 1.3 la séance à trois fichiers et ce qu'elle sépare ; 1.4 l'incertitude d'une KL moyenne,
  par positions ou par fenêtres ; 1.5 refaire un résultat à 2 σ.
- **Réserves** : III-10.1 : les 11 cases vides ont été décodées par C1 ; il leur manque une KL, pas une mesure ;
  R1 pour toute phrase sur la vitesse.

## 11. La géométrie tropicale du routeur

- **Sources** (lecture seule) : `genome/pistes/tropicale/garde-tropicale.md` ; `pour-le-memoire.md` ;
  `seuil-declare.md`, `seuil-declare-indices.md` ; `JUGEMENT.md` ; `mesures/pistes/tropicale/`.
- **Figures** : III-11.1 à 11.7 (`\GrapheTropicaleCourbe`, `…Couches`, `…Survie`, `…LoiBascule`,
  `…Extrapolation`, `\FigureTropicaleCoupe`, `…Kappa`) ; légendes à écrire par le chapitre.
- **Dérivations** (note § 2) : 2.1 le routeur comme polynôme tropical, la marge comme distance ; 2.2 pourquoi la
  marge est presque exponentielle ; 2.3 la loi de bascule ; 2.4 le théorème du nombre de garde (forme close) ;
  2.5 l'extrapolation (modèle) ; 2.6 les cascades ; l'ajout du 2026-10-26 (indices multiples).
- **Réserves** : le corollaire du « plafond de 4 % » n'est vrai que pour une population homogène et n'explique
  qu'environ 1 point sur ceux qui manquent (juge) ; III-11.5 est un modèle ; la coupe (PNG) est hors du style ;
  la garde des racines de cascade est explorée après le verdict, à présenter comme telle.

## 12. Les spectres des matrices

- **Sources** (lecture seule) : `genome/pistes/spectres/spectres.md` ; `pour-le-memoire.md` ; `seuil.md` (avec son
  amendement avant lecture), `juge-seuil.md` ; `JUGEMENT.md` ; `mesures/pistes/spectres/`.
- **Figures** : `\FigureSpectres{1}` (survie) et `\FigureSpectres{2}` (exposants), seules jugées. Les pages 3
  (levier), 4 et 5 (plafond) ne le sont pas (JUGEMENT § 5) : ne pas les placer.
- **Dérivations** (note §§ 1 à 4, 7, 8) : la densité spectrale empirique ; Marchenko-Pastur ; la méthode de Clauset,
  Shalizi et Newman pas à pas ; le théorème du juge (le critère principal est impossible à toute taille : la loi
  de puissance est le bord de la log-normale tronquée) ; le levier en trois calculs (tramage soustractif,
  Schuchman, Zamir et Feder) ; le plafond spectral (chiffres non jugés, étiquetés).
- **Réserves** : « seul endroit » de la piste est faux (11 matrices sur 48) : barrer ; les références de journal
  de CSN, MP et Vuong sont données de mémoire par la piste : à vérifier à la source ; échantillon de 2 % des
  matrices, 3 couches, poids déquantifiés (limites de la piste) ; le PDF est hors du style commun.

## 13. Discussion — rédacteur D

- **Sources** : les « Ce qui pourrait être faux » des chapitres une fois écrits ; les « Ce qui reste » des
  livrables (05 § 3, 06 § 12, 07 § 8, JUGEMENT-construction § 11, garde-tropicale § 8, spectres § 7, tri § 3 et
  § 7) ; modèle : `memoire/tome2/fr/chapitres/09-discussion.tex`.
- **À poser** : ce que le tome établit ensemble (tableau des verdicts, chacun avec son juge) ; ce qui pourrait être
  faux à l'échelle du tome (échantillons, protocoles 32/768, disque unique, analogies, chiffres non jugés) ; les
  travaux futurs, chiffrés quand ils le sont.

## A. Protocoles : seuils déclarés et témoins

- **Sources** : tous les fichiers de seuils listés dans le squelette (`fr/annexes/A-protocoles.tex`) ; `git log
  --date=iso` pour l'ordre seuil → mesure ; `memoire/outils/tome3_cassures.py`, `JUGEMENT-figures3.md` § 4.4.
- **À poser** : un tableau des seuils (grandeur nommée, d'où il dérive, commit du seuil, commit de la mesure,
  verdict), un tableau des témoins et cassures, les amendements avant lecture, les protocoles des juges.

## B. Outils

- **Sources** : `memoire/construire.sh` ; `memoire/tome3/commun/figures.tex` ; `memoire/outils/tome3_*.py` ;
  `outils/genome/`, `outils/mimetisme/`, `outils/pistes/` (lecture seule).
- **À poser** : la chaîne du tome ; les outils par chapitre ; chaque figure et ses fichiers ; les licences.

## C. Journaux

- **Sources** : `git ls-files` sous `mesures/genome/`, `mesures/mimetisme/`, `mesures/pistes/`,
  `mesures/disque/placement/juge/`, `outils/genome/tome3/*/journaux/` ; les `REPRISE-*.md`.
- **À poser** : les dossiers par chapitre (tableau engendré, sur le modèle de `memoire/annexes/journaux.tex`),
  les séances qui portent un chiffre, les passes coupées ou jetées.

## Décisions de l'ossature (réponses par délégation du 2026-10-29, réversibles)

- **Trois parties** : « La question et la ronde » (1 à 7), « La construction » (8 à 10), « Les pistes et le
  bilan » (11 à 13), comme les trois parties du Tome II. Raison : le chemin du tome, de la mesure au construit.
- **Les figures se chargent une fois**, dans le préambule (`commun/figures.tex`), et non par chapitre comme au
  Tome II : `legende-tome3.tex` demande le préambule, et un seul chargement évite les doubles définitions.
- **Spectres** : `spectres-figures.tex` est un document autonome (`standalone`), qui ne peut pas s'`\input`. Il se
  compile à part, dans son dossier (chemins relatifs), sortie sous `memoire/tome3/pistes/` (ignoré par git) ;
  le chapitre prend ses pages. Raison : l'inclure sans le modifier.
- **`construire.sh`** : cibles `tome3`, `tome3-en`, `tome3-fr` ajoutées ; la cible sans argument et `propre` sont
  inchangées (« sans rien changer aux autres cibles ») ; la cible lance les huit outils de données des lots
  (régénération au bit, juge 3 § 4.3), pas `tome3_palette.py` (CRLF) ni `tome3_cassures.py`.
- **La page de titre** porte un schéma du chemin du tome, sans nombre : les nombres viendront des chapitres jugés.
- **Les notations** n'ont qu'une ligne : aucune définition avant le texte qui la fonde ; les candidats sont listés
  en commentaire.

## Ce qui pourrait être faux

- Les sommaires des livrables et des notes ont été lus, pas chaque dérivation mot à mot : une dérivation « pour le
  mémoire » écrite hors de sa section peut manquer à ce plan ; le rédacteur lit la note en entier.
- Les verdicts cités ici viennent des têtes des jugements ; leurs corps peuvent les nuancer.
- Les paires de clés données comme « même œuvre » n'ont pas été vérifiées à la source (SeedLM, Skliar).
- Les chiffres de la piste des spectres et de P3 bougent peut-être encore (flux non clos) : relire `git log` de
  leurs dossiers avant d'écrire.
