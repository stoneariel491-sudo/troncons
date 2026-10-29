# Tome III (français) : le jugement de la rédaction

Juge indépendant de la rédaction française du Tome III, 2026-10-29. Je n'ai rien écrit de ce que je juge. Objet :
les chapitres 00 à 13 et les annexes A à C de `memoire/tome3/fr/`, tels que les quatre rédacteurs (A, B, C, D) les
ont laissés, contre `SOCLE.md`, `memoire/tome3/PLAN-redaction.md`, `INVENTAIRE-figures.md` (§ 0, réserves R1 à R6),
`CONVENTIONS-figures.md`, `REPRISE-figures.md`, et le Tome II comme modèle de forme. Aucune mesure, aucune carte
graphique. Mes outils et journaux : `outils/genome/tome3/juge-redaction/` ; mes constructions :
`memoire/essai/juge-redaction-fr-{brouillon,tete}/` (dossier ignoré par git).

**Une convention de lecture.** Je nomme les chapitres par leur fichier (00 à 13). Dans le PDF, l'introduction est
le chapitre 1, si bien que le fichier 07 s'imprime « chapitre 8 », le fichier 13 « chapitre 14 » : c'est l'objet du
grave G3.

**Ce qui est jugé, au bit.** Le dépôt est à `a849d3f` (main), et rien n'y a été commité pendant ce jugement. Les
chapitres 02 à 05 du rédacteur A **ne sont pas commités** : à `HEAD`, ce sont les squelettes de l'ossature (2 299 à
2 966 octets). Je juge donc deux états, assemblés par `assembler.py`, qui recopie chaque fichier sans en changer un
octet et écrit son SHA-256 (`journaux/manifeste-tete.json`, `journaux/manifeste-brouillon.json`) :

- **tête** : chaque fichier tel qu'il est commité (`git show HEAD:…`) ;
- **brouillon** : la tête, sauf les quatre chapitres du rédacteur A, pris là où il les a laissés :

| chapitre | provenance | SHA-256 (12 premiers) | octets |
|---|---|---|---|
| 02-eclaireur | arbre de travail de `memoire/tome3/fr/chapitres/` (modifié, non commité) | `a017b826d506` | 46 661 |
| 03-genome | arbre de travail (modifié, non commité ; égal au brouillon corrigé `\mathrm{Beta}`) | `56f1d0bf392c` | 56 650 |
| 04-duplication | brouillon du rédacteur A, `…/scratchpad/redA/04-duplication.tex` | `ee9b9774f7ba` | 41 950 |
| 05-predictif | brouillon du rédacteur A, `…/scratchpad/redA/05-predictif.tex` | `7b12095fc686` | 37 417 |

Ce que je dis des chapitres 02 à 05 vaut pour ces octets-là ; le commit qui les portera doit avoir ces empreintes,
ou être rejugé sur ce qui a changé.

## 0. Verdict

**Le tome rédigé est juste. Ses 71 chiffres tirés au hasard sont tous exacts, ses réserves R1, R3 et R4 tiennent
presque partout, et il se construit en entier : 298 pages, 0 erreur, 0 renvoi ni citation indéfinis. Mais ce n'est
pas encore un mémoire fini, et le tome commité ne se construit pas.**

**À `HEAD`, quatre chapitres sur quatorze sont des squelettes, et `construire.sh tome3-fr` tombe sur trois renvois
indéfinis (G1). Les quatre chapitres non commités débordent de la page : 19 boîtes trop pleines, jusqu'à 149 pt, et
une colonne de tableau imprimée hors de la feuille (G2). Huit légendes jugées (neuf renvois) et cinq phrases
écrivent en dur des numéros de chapitre faux d'une unité dans le PDF (G3). Le résumé est vide, la table des notations
n'a qu'une ligne, et la KL, le juge de tout le tome, n'est définie qu'au fichier 07 (G4, G5). Enfin, l'ouverture du
chapitre 10 redit sans barre l'attribution du ×1,44 que R1 a fait tomber (G6).**

- **La construction (§ 2).** État brouillon : latexmk rend son code 0 en 1 849 s, 298 pages, 0 erreur, 0 renvoi ni
  citation indéfinis, biber sans avertissement. Les 24 boîtes trop pleines se répartissent ainsi : 19 dans les
  chapitres 02 à 05, 4 dans la table des matières (1,5 à 5,1 pt) et 1 dans le chapitre 11 (0,57 pt). État tête :
  latexmk rend son code 0 en 1 137 s, 245 pages, 0 erreur, mais **3 renvois indéfinis**, que `construire.sh` refuse ;
  3 boîtes trop pleines (au plus 1,7 pt).
- **Les chiffres (§ 3).** Le tirage porte la graine 20261029, à raison de 5 nombres par chapitre et 2 par annexe,
  parmi 5 357 candidats. Sur 76 tirages, 5 ne sont pas des chiffres ; restent **71**.
  - **52 sont refaits par mon calcul** depuis leur journal ou leur CSV, **tous égaux à l'arrondi imprimé** ; décalés
    d'une unité du dernier chiffre, ils tombent tous.
  - **19 sont portés, dans la même phrase, par la source qu'ils citent.**
  - **0 faux.**
  - En plus du tirage, 32 calculs neufs des rédacteurs, refaits par un second chemin : 28 égaux, **4 arrondis faux
    au dernier chiffre** (M1 à M4).
  - La correction neuve du chapitre 04 (« substituer n'est jamais meilleur que retirer » est faux) **tient**.
- **R1 (§ 4.1).** La réserve tient dans les chapitres 08, 09, 10 (le corps), 13, dans l'introduction et dans
  l'annexe A. **Une fuite**, à l'ouverture du chapitre 10 (G6).
- **Les chiffres barrés (§ 4.2).** **Aucun chiffre barré ne revient comme valide.** Le tableau des verdicts du
  chapitre 13 recopiait de `genome/05-synthese.md` une paire de gains mêlée (−0,142 ; −0,128), que le chapitre 07
  dit fausse : **corrigé par moi** (G7, § 8). Le 1,335 de S\* est barré au chapitre 07 et ne l'est pas au chapitre 03 (M7).
- **R3 (§ 4.3).** Tenue.
- **Les figures (§ 4.4).** Les 29 figures au style du tome sont toutes placées, avec les étiquettes imposées. Huit
  commentaires relus contre leur légende jugée tiennent. **Deux figures ne sont appelées par aucun renvoi** (M8).
- **La lecture (§ 5).** La forme du Tome II est tenue partout, et les dérivations sont posées : 67 énoncés, dont 64
  suivis de leur démonstration. Ce qui manque au lecteur qui découvre, c'est le vocabulaire : la KL, les fenêtres
  R1, le lot R, F1, A\_ctx et A\_flux, P0 à P3, J1.

**Graves : 7, dont un (G7) corrigé par moi. Mineurs : 16.**

## 1. Méthode, et ce qui était déclaré avant

Les critères sont ceux de la consigne et de SOCLE, fixés avant toute lecture des chapitres. Je ne les ai pas commités
à part avant de lire : ce ne sont pas des seuils que j'aurais pu régler, et le tirage, lui, a sa graine écrite.
- **La construction** : aucune erreur, aucun renvoi ni citation indéfinis (les contrôles de `construire.sh`).
- **Un chiffre calculé** est juste s'il est égal, à l'arrondi imprimé, à ce que je refais depuis le fichier commité
  qui le porte.
- **Une citation** est juste si la source citée porte le nombre dans la même phrase.
- **Une phrase barrée** dans une source ne revient pas comme valide.
- **Une figure** est placée par sa macro, et son commentaire ne contredit pas sa légende jugée.

**Le tirage.** `tirage.py` tire avec la graine 20261029 (la date) 5 nombres par chapitre et 2 par annexe, fichier
après fichier, dans l'ordre des fichiers. Un candidat est un décimal, ou un entier d'au moins trois chiffres qui n'est
pas une année. Il est pris dans le texte, hors commentaires et hors commandes de fichier, de renvoi et de citation.

**Une correction de méthode, faite avant toute vérification.** La première version de l'extracteur avait trois
défauts :
- elle ne prenait pas les décimaux écrits `\num{0.1446}`, que siunitx imprime pourtant avec une virgule (fichiers
  00, 09, 10, 13) ;
- elle lisait 399.5 comme l'entier 399 ;
- elle comptait une graine (20261026) comme un chiffre.

Je l'ai corrigée et j'ai retiré avec la même graine. Le premier tirage est gardé, non utilisé
(`journaux/tirage-v1.csv`). Le second prend encore cinq choses qui ne sont pas des chiffres : quatre largeurs de
colonne `p{0.27\linewidth}` et « §§ 5.9 et 5.10 ». Je les écarte en le disant, sans retirer.

**Le refait.** `refaire.py` ne reprend le code d'aucun outil : il lit les JSON et les CSV et refait le nombre (une
entropie depuis la loi, une médiane depuis les positions, un σ par fenêtres depuis les 2 550 KL par position, un
rapport de deux journaux, un compte de lignes, etc.). Pour une citation, il cherche le nombre dans la phrase de la
source citée. Sa cassure (`--casser`) décale chaque valeur imprimée d'une unité du dernier chiffre : les 52 calculs
tombent.

## 2. La construction

`construire.sh` (ce dossier) fait ce que fait `memoire/construire.sh tome3-fr` : même `latexmkrc`, même maître, mêmes
contrôles du journal. Il travaille dans `memoire/essai/juge-redaction-fr-<état>/`, à la même profondeur que
`memoire/tome3/fr/`, si bien que `\Racine` et `\Depot` y désignent les mêmes fichiers. Rien n'est écrit sous
`memoire/tome3/`. `journal.py` range ensuite chaque boîte trop pleine par fichier.

| état | latexmk | pages | erreurs | renvois / citations indéfinis | boîtes trop pleines |
|---|---|---|---|---|---|
| brouillon | code 0, 1 849 s | 298 | 0 | 0 / 0 | 24 |
| tête | code 0, 1 137 s | 245 | 0 | **3** / 0 | 3 |

**Les boîtes trop pleines de l'état brouillon** (`journaux/journal-brouillon.txt`) :

| fichier | boîtes | la plus large | où |
|---|---|---|---|
| table des matières | 4 | 5,1 pt | numéros de page xvii, xxiii, 135, 197 |
| 02-eclaireur | 5 | 65,6 pt | tableaux, l. 37 (`zero_compte.py`), 52–61, 129–141, 225–238, 274–292 |
| 03-genome | 5 | 39,6 pt | tableaux, l. 204–217, 272–291, 334–346, 356–372 ; paragraphe l. 225–226 (`\texttt`) |
| 04-duplication | 3 | 42,5 pt | formules, l. 34–35 et 139–140 ; tableau, l. 166–184 |
| 05-predictif | 6 | 149,0 pt | tableaux, l. 43–52, 137–149, 167–177, 191–205, 233–247, 253–264 |
| 11-tropicale | 1 | 0,57 pt | l. 154–155 |

Vu au rendu : à la page 74 du PDF (physique 98), le tableau 6.6 (fichier 05, l. 233–247, « La KL contre la
référence f64 ») sort de la feuille, et sa dernière colonne, « même premier choix », n'est imprimée qu'à moitié. À la
page 29 (physique 53), le tableau 3.5 (fichier 02, l. 225–238) passe dans la marge sans rien perdre. Les
chapitres 06 à 13 et les annexes, que leurs rédacteurs ont compilés seuls jusqu'au bout, n'en ont aucune au-delà de
0,6 pt.

## 3. Les chiffres

### 3.1 Le tirage (`journaux/tirage.csv`, `journaux/refaire.csv`)

| id | fichier, ligne | imprimé | refait (ou source) | verdict |
|---|---|---|---|---|
| 00-01 | 00 l. 28 | 2,82 Go/s | Tome I, ch. 3 : $W_{\text{disque}} = 2{,}82$ | source |
| 00-03 | 00 l. 69 | 768 | 24 × 32 | égal |
| 00-04 | 00 l. 79 | 3,8434 | 3,84343 (`k10/frontiere.csv`, A\_flux) | égal |
| 00-05 | 00 l. 79 | 3,6844 | 3,68441 | égal |
| 01-06 | 01 l. 58 | H(V) = 3,7228 | −Σ p log₂ p sur `loi_v` (`borne-rd-passe1.json`) : 3,722829 | égal |
| 01-07 | 01 l. 68 | 8,602 % | `loi_v[−1]` : 8,6024 | égal |
| 01-08 | 01 l. 100 | 4,29 % | `frontiere_07.erreur` : 4,2920 | égal |
| 01-09 | 01 l. 153 | 2,607 | 00 § 1 « 2,642 → 2,607 » | source |
| 01-10 | 01 l. 176 | 3,86 | `zero-compte-20b-12.json`, H\_code 3,85977 | égal |
| 02-11 | 02 l. 57 | 3,7228 | H\_valeur 3,722829 | égal |
| 02-12 | 02 l. 256 | 4,40 % | `frontiere-lam0-damp0.01.json`, err\_poids.gate 4,3951 | égal |
| 02-13 | 02 l. 258 | ×0,26 | 0,006477 / 0,025300 = 0,2560 | égal |
| 02-14 | 02 l. 323 | 0,0088 | médiane des 2 550 KL de `kl-frontiere-positions.csv` : 0,008762 | égal |
| 02-15 | 02 l. 351 | 2,6441 | 01-eclaireur § 7 | source |
| 03-16 | 03 l. 245 | 4,022 % | `verdict-par-tenseur.csv` : 4,0216 | égal |
| 03-17 | 03 l. 278 | 0,29 % | `structure-spectre.json` : 0,2892 | égal |
| 03-18 | 03 l. 283 | 0,39 % | 0,3862 | égal |
| 03-19 | 03 l. 285 | 17,4 % | 17,4135 | égal |
| 03-20 | 03 l. 364 | 127 | `fidelite-sstar.csv` | égal |
| 04-21 | 04 l. 140 | 192 | 3 × 8 × 8 | égal |
| 04-22 | 04 l. 173 | 0,0004 | moyenne (8, gate) de `d1-sans-perte.csv` : 0,000405 | égal |
| 04-23 | 04 l. 220 | 4,5 | `t-o-sortie.csv` (0, 16) : 4,531 | égal |
| 04-24 | 04 l. 231 | 3,8 | (23, 8) : 3,831 | égal |
| 04-25 | 04 l. 325 | 768 | 24 × 32 | égal |
| 05-26 | 05 l. 74 | 0,0037 | 3,792250 − 3,788512 (`contextes-gptoss20b.json`) | égal |
| 05-27 | 05 l. 149 | 2,6321 | `debit-distorsion-12-resume.json` : 2,632135 | égal |
| 05-28 | 05 l. 185 | 235,5 Mo | 20 440 × 2 880 × 4 o = 235,47 Mo | égal |
| 05-29 | 05 l. 198 | 2,0178 | `resume-12.csv` | égal |
| 05-30 | 05 l. 200 | 1,02 | 0,05699 / 0,05572 = 1,0228 | égal |
| 06-31 | 06 l. 269 | 662 | 326 + 336 | égal |
| 06-32 | 06 l. 269 | 160 | `grille.csv` : succès RAM inclusif nul à R = 80 et 160, 7 traces | égal |
| 06-33 | 06 l. 421 | ×1,29 | 1/(1 − 0,2256) = 1,2913 | égal |
| 06-34 | 06 l. 448 | 84,3 % | `JUGEMENT-etage-B.md` | source |
| 06-35 | 06 l. 498 | 7,38 | `JUGEMENT-routeur-ligne.md` | source |
| 07-36 | 07 l. 93 | 90,9 % | k10 : 0,908627 | égal |
| 07-37 | 07 l. 96 | 0,0206 | `comparer10-base-contre-recette.json` : 0,020570 | égal |
| 07-38 | 07 l. 102 | 0,0072 | k10, σ : 0,007204 | égal |
| 07-39 | 07 l. 245 | 3,01 | `comparer10`, kl\_max : 3,0084 | égal |
| 07-40 | 07 l. 503 | 6,2 Go | 05 § 4.7 | source |
| 08-41 | 08 l. 94 | 540 tables | 216 + 324 (`tables-octets.json`) | égal |
| 08-42 | 08 l. 206 | 0,0037 | (0,1416 + 0,1231) × 265 420 800 / 19 110 297 600 = 0,003676 | égal |
| 08-43 | 08 l. 272 | 10,85 Go | 06 § 8 | source |
| 08-44 | 08 l. 349 | σ = 5,6 % | `j1-s2-verdicts.json` : 5,638 | égal |
| 09-46 | 09 l. 238 | 0.0203 (σ par fenêtres, λ = 1) | refait sur `kl-synonyme-768-positions.csv` : 0,020274 | égal |
| 09-47 | 09 l. 239 | 0.0055 (σ naïf, λ = 0) | 0,005527 | égal |
| 09-48 | 09 l. 363 | 2.6593 | `rapide/coder-frontiere.json` | égal |
| 09-49 | 09 l. 447 | ×1,31 | 07 § 4.4 (décomposition du lot B) | source |
| 09-50 | 09 l. 447 | ×1,24 | 07 § 4.4 « 1,241 » | source |
| 10-51 | 10 l. 231 | σ\_n = 0.0066 | refait sur `kl-frontiere-768-positions.csv` : 0,006596 | égal |
| 10-52 | 10 l. 248 | z = 3.62 | `apparie-neuf-moteur-l0-contre-l1.json` : 3,6214 | égal |
| 10-53 | 10 l. 306 | 1.74 Go/s | médiane de jetons/s × octets/pas des passes R : 1,7386 | égal |
| 10-54 | 10 l. 307 | ×1,31 | R/A de `disque-passes.csv` : 1,3093 | égal |
| 10-55 | 10 l. 428 | 1.8 % | 96 / 5 376 | égal |
| 11-56 | 11 l. 13 | 26,6 % | `propagation.csv`, pondéré par les comptes : 26,646 | égal |
| 11-57 | 11 l. 215 | 38 415 | `propagation.csv` | égal |
| 11-58 | 11 l. 222 | ×7,9 | 26,646 / 3,371 = 7,905 | égal |
| 11-59 | 11 l. 275 | 0,48 | κ maximal (σ phi\_mv) de `theoreme-par-couche.csv` : 0,4838 | égal |
| 11-60 | 11 l. 329 | 0,10 | seuil déclaré 80/10 | source |
| 12-61 | 12 l. 44 | 0,4216 | √(512/2880) = 0,421637 | égal |
| 12-62 | 12 l. 194 | 3,7 | JUGEMENT de la piste, § 2 | source |
| 12-63 | 12 l. 218 | 0,216 | `spectres.md` | source |
| 12-64 | 12 l. 222 | 0,755 | `spectres.md` | source |
| 12-65 | 12 l. 222 | 2,254 | `spectres.md` (½ log₂(1/D) = 2,2535) | source |
| 13-66 | 13 l. 36 | +0.0066 | k10 : 0,006564 | égal |
| 13-67 | 13 l. 50 | KL « de l'ordre de 0.03 » | `JUGEMENT-routeur-ligne.md` : 0,031388 | source |
| 13-68 | 13 l. 58 | 3.86 | `J-T0-fichiers.json` : 3,86177 | égal |
| 13-69 | 13 l. 75 | ×0,94 | JUGEMENT-construction § 6 | source |
| 13-70 | 13 l. 80 | 5.26 % | JUGEMENT de la piste tropicale, § 4.1 | source |
| A-72 | A l. 101 | 10.0 % | `temoins.json`, T3 : 10,045 | égal |
| C-75 | C l. 36 | ×2,00 | 07 § 4.4 (barré comme gain du mode) | source |
| C-76 | C l. 37 | 1.442 | JUGEMENT-construction § 6 | source |

Écartés, parce qu'ils ne sont pas des chiffres : 00-02, A-71, B-73 et B-74 (largeurs de colonne), 08-45 (« §§ 5.9 et
5.10 »).

Ce que le tirage ne couvre pas :
- les nombres des légendes jugées (déjà refaits par les juges des figures) ;
- les entiers de moins de trois chiffres ;
- la cohérence d'un chapitre à l'autre, lue aux §§ 4 et 5.

Une source citée peut se tromper avec le texte : pour 19 nombres, j'ai vérifié la citation, pas la mesure qui est
derrière.

### 3.2 Les calculs neufs des rédacteurs (`journaux/calculs.txt`)

Les rédacteurs ont posé eux-mêmes 32 calculs (étiquetés `\calc`), que j'ai refaits :
- log₂ 2 880!, par lgamma (28 948,6) et par Stirling (33 096,5 − 4 155,0 + 7,1) ;
- les coûts ajoutés de la duplication ;
- l'intervalle de Wilson [0,8578 ; 0,8838] ;
- le gain de pavage en dB ;
- les bornes de Marchenko-Pastur et G\_Pareto(2,5) ;
- le toit des octets, 3,36 et 3,43 % ;
- les tampons, 4 472 832 octets ;
- ρ ≈ 0,12 ;
- le seuil 0,362 de P2 et les conversions de P3 ;
- 686,8/468,5 et 1/(1 − 0,0356) − 1.

**Quatre arrondis sont faux au dernier chiffre** (M1 à M4). Aucun ne change une conclusion. Le rapport 1,38 du
fichier 07 (l. 243), écrit « 0,0360/0,0262 », vaut 1,374 avec ces deux nombres arrondis et 1,376 avec les valeurs du
journal. Le texte imprime le quotient exact : c'est juste.

### 3.3 La correction neuve du fichier 04

Le rédacteur A a démenti une phrase de deux livrables (`genome/duplication.md` § 0 point 6, `genome/05-synthese.md`
§ 3.2) : « substituer n'est jamais meilleur que retirer l'expert ». Je l'ai refaite par `paralogues.py`, qui compte
par couche les experts où `couche_substitue` < `couche_retire` et donne les deux moyennes :

| couche | substituer fait mieux que retirer | moyenne substituée | moyenne retirée |
|---|---|---|---|
| 0 | 4 experts sur 32 | — | — |
| 8 | 5 sur 32 | — | — |
| 16 | **25 sur 31** | 0,0707 | 0,0757 |
| 23 | **21 sur 31** | 0,0368 | 0,0370 |

**La correction tient**, et la phrase juste du chapitre aussi. Les deux livrables restent à corriger par
l'orchestrateur : ils ne sont ni au rédacteur ni à moi (M13).

## 4. Les vérifications transversales

### 4.1 R1, l'attribution du ×1,44

J'ai lu, dans les dix-sept fichiers, toutes les occurrences de 1,44, 1,45, 1,442 et 1,454, et des mots « attribu »,
« état du fichier », « pas le format », « disposition physique ».

**R1 tient** :
- **fichier 08** : le J1 séance par séance, l'ancienne attribution barrée avec ce qui a changé, le motif croisé
  ×1,389 / ×0,715, la cascade, « ne se transporte pas à un autre disque » ;
- **fichier 09** : le paragraphe « Ce qui fait l'étage disque » ;
- **fichier 10** : le paragraphe R1, le tableau des barres, J-V1 à J-V3 ;
- **fichier 13** : « parce que le motif de ses requêtes de lecture est rapide là où celui du v1.0 ne l'est pas » ;
- **l'introduction** (§ Les réserves) et **l'annexe A**.

Le fichier 08 signale lui-même que `JUGEMENT-construction.md` § 8 garde une ligne non barrée (« pour les fichiers,
pas pour le format ») ; le texte ne la reprend pas.

**Une fuite**, à l'ouverture du fichier 10 (l. 11, « Au départ ») : « un J1 du 120b 1,45 fois plus rapide en v1.2,
qu'il refuse lui-même d'attribuer au format ». C'est l'attribution que R1 a fait tomber, dite sans barre et sans ce
qui a changé, à l'endroit où le lecteur forme son cadre (G6).

### 4.2 Aucun chiffre barré revenu

`barres.py` relève chaque passage `~~…~~` des sources et chaque `\barre{…}` des chapitres. Les sources lues sont :
genome/, le mimétisme, les pistes et les jugements des figures. Un passage ne franchit pas une ligne vide. Une
première version prenait un « ~~ » cité dans `JUGEMENT-figures-latents.md` (l. 49) pour l'ouverture d'une barre de
150 lignes ; je l'ai corrigée avant de lire ses résultats.

L'outil en tire 95 nombres barrés et rend les 401 endroits où l'un d'eux revient hors barre
(`journaux/barres.txt`). Ce n'est pas un verdict : un nombre barré dans une phrase peut être juste dans une autre.
J'ai lu toutes les occurrences des nombres qui portent une correction :

- **0,0262** (8 fois) : toujours la KL de λ = 0, jamais attribuée à λ = 1.
- **×1,24 et ×2,00** (8 et 12 fois) : toujours la comparaison de deux fichiers, jamais un gain du mode rapide.
  « Deux gains de vitesse », à l'ouverture du fichier 10, décrit ce que publiait le lot B.
- **1,695** (fichier 05) : dans un tableau titré « erreur de sortie prédite », suivi de sa phrase barrée.
- **1,296** (fichier 10) : le nombre est juste ; dans la source, la barre portait sur une prédiction de l'écart.
- **1,335** (fichier 03, l. 382) : c'est le rapport de S\* à 3 fenêtres. Il est imprimé sans barre dans le
  paragraphe « Ce qui a été publié, et ce qui l'a remplacé », où sa conclusion est barrée mais pas lui. Le fichier
  07 le barre (`\barre{1,335}`). Ce n'est pas un chiffre revenu comme valide, mais le même nombre reçoit deux
  traitements (M7).
- **Le 4 % de la garde, 2Φ, « seul endroit » des spectres** : barrés là où ils sont cités (fichiers 11, 12 et 13).
- **−0,142 et −0,128** : cette paire de 05 § 0, que le fichier 07 (l. 177 et 557) dit mêlée (gate mesuré contre le
  flux octet, up contre le flux demi-octet), revenait dans le tableau des verdicts du fichier 13. Corrigé (G7, § 8).

### 4.3 R3, les protocoles

Aucune phrase ne place une KL à 32 experts (0,0360 ou 0,0262, protocole P1) à côté d'une KL à 768 experts (0,2640,
0,1522 ou 0,1318) sans dire les deux protocoles : la recherche, phrase par phrase, n'a trouvé aucun cas. Les deux
comparaisons voulues sont dites comme telles :
- fichier 09, l. 249 : « sept fois celle de 32 experts substitués (0,036, protocole de l'éclaireur) » ;
- fichier 09, l. 274, et fichier 13, l. 103 : « à 768, λ = 1 bat la frontière de 42 % » (1 − 0,1522/0,2640 =
  42,3 %).

La figure III-7.1 garde les protocoles P1, P2-10 et P3, la III-9.6 porte les 768 experts, et aucun trait ne relie
les unes aux autres. R4 (S\* par K10) tient aux fichiers 03, 07 (le tableau et la III-7.2) et 13.

### 4.4 Les figures, appelées et commentées

Selon `statique.py`, le tome assemblé compte 50 environnements `figure`, **tous étiquetés** :
- 29 au style du tome, par `\LegendeFigure` ;
- 12 du mimétisme, portant 13 figures hors style, par `\FigureHorsStyle` et `\HorsStyle` ;
- 7 de la piste tropicale, dont les légendes sont écrites par le chapitre ;
- 2 pages des spectres.

Les 29 `\Legende` définies dans `memoire/figures/tome3/` sont **toutes placées**, aux étiquettes que le plan impose.
**Deux figures ne sont appelées par aucun renvoi** : `fig:t3-mim-p6` (III-6.13) et `fig:t3-codon-format` (III-8.7)
(M8).

J'ai relu huit commentaires contre la légende jugée et ses nombres (`memoire/figures/tome3/donnees/*-nombres.*`),
sans trouver d'écart :
- **III-1.2** : la borne supérieure, Blahut-Arimoto, les cordes ;
- **III-4.8** : 30,9 % de la variance, Spearman 0,61 contre 0,11, le moyeu 31, les quatre arêtes les plus lourdes,
  16 feuilles ;
- **III-7.2** : la bande d'erreur de 0,75 à 1,02, la KL de 1,02 à 3,06, S\* placé par K10, le point à 3 fenêtres
  barré ;
- **III-8.5** : le codec réel ; la phrase fausse « pas un fichier codé » est dite et corrigée ;
- **III-8.6** : R1 ;
- **III-9.6** : R3 ;
- **III-9.7** : la borne 0,135 porte sur les projections ; sur les entrées, 0,61 en médiane, aucune sous 0,135 ;
- **III-10.1** : 732 + 2 + 23 + 11 = 768 et 465 appels sur 490 560, refaits sur `routage-grille.csv`.

Les légendes écrites par les fichiers 06, 11 et 12 disent leur provenance, et `\HorsStyle` pour les figures hors
style. Ce que je n'ai pas vérifié pour chaque légende, c'est l'accord de ses renvois écrits en dur (« chapitre 7 »)
avec la numérotation du PDF : voir G3.

## 5. La lecture, comme un lecteur qui découvre

**Ce qui est là.**
- **La forme du Tome II** est tenue partout : l'origine en trois temps, un « En bref » où l'analogie est dite comme
  telle (« une image qui guide, pas un argument »), et des sections qui expliquent avant de démontrer.
- **Les nombres** portent leur provenance (`\mes`, `\calc`, `\litt`), et les phrases barrées disent ce qui a changé.
- **Chaque fichier a son « Ce qui pourrait être faux »** (1,6 à 4,1 ko par chapitre, 0,6 à 1,2 ko par annexe),
  sauf l'introduction, qui renvoie au fichier 13.
- **Les dérivations des notes « pour le mémoire » sont posées.** `enonces.py` compte 67 énoncés, dont 64 suivis d'une
  démonstration. Les trois autres sont :
  - le corollaire de la bande de pile (06), mesuré juste après ;
  - le gain attendu par poids (08), conséquence directe de la proposition ;
  - la représentation de Rényi (11), citée et dite « article non relu ».

Le tome est riche, et ses chiffres sont justes.

**Ce qui ne s'explique pas.**
- **La KL.** Le juge du tome est la divergence de Kullback-Leibler contre la référence f64, moyennée sur les 2 550
  positions notées de R1. Elle tranche dès l'introduction (« divise par deux la KL »), puis aux fichiers 02 (§ le
  protocole P1), 03, 05 et 06. Sa définition, KL\_t = Σ\_i p\_{t,i} log(p\_{t,i}/q\_{t,i}), en nats, coupée à
  log p > −16, n'arrive qu'au fichier 07 (l. 33). Un lecteur qui découvre lit six chapitres sans savoir ce que mesure
  le nombre qui décide (G4).
- **Le vocabulaire du projet.** « R1 » a deux sens : les dix fenêtres d'évaluation du lot R (« sur R1 », fichiers
  09, 10 et 13) et la réserve R1 de l'inventaire (fichiers 08, 10, 13 et l'introduction). Les autres noms viennent
  des Tomes I et II ou de la ronde, et ne sont posés qu'en passant, ou jamais :
  - lot R, F1, « l'arbitre », J1, K10, ABBA ;
  - A\_ctx (posé au fichier 01, l. 81) et A\_flux ;
  - P0 à P3 et P2-10 (posés au fichier 07 seulement).

  La table des notations n'a qu'une ligne (« troncons ») ; le plan la réservait au juge-correcteur (G5).
- **Le premier tableau du fichier 02** (l. 31) nomme « YaRN », « fourche » et `trc-reference` sans les gloser (M11).
- **Deux références pour un même résultat.** L'introduction donne le codon du zéro en A\_flux (3,8434 → 3,7064) ;
  les fichiers 01 et 02 le donnent en A\_ctx (3,8431 → 3,7061) ; l'introduction ne dit pas lequel (M9).
- **Le PDF ne parle pas comme le texte.** Une légende dit « la frontière commune du chapitre 7 » sous la figure 9.6 ;
  la synthèse est imprimée chapitre 8 (G3, vu au rendu, page 147).

**Ce qui se répète.** Chaque chapitre doit pouvoir se lire seul, et une répétition courte se défend ; ici, ce sont
des paragraphes (M10) :
- le motif croisé du juge du placement (×1,389 / ×0,715), raconté trois fois (fichiers 08, 09 et 10) ;
- l'histoire de la KL 0,0262 attribuée à la mauvaise variante, quatre fois (02, 07, 10 et 13) ;
- l'image des 64 codons pour vingt acides aminés, quatre fois (00, 02, 03 et 09).

**Ce qui manque au regard de SOCLE.**
- Le résumé, français et anglais, est vide : la page iii ne porte que son titre (G4).
- Les chapitres 02 à 05 ne sont pas commités (G1).
- L'outil des annexes n'est pas dans `construire.sh` (G1).
- Quelques sources sont nommées sans entrée biblatex (M14).
- Aucun listing de code commenté, et une liste des listings vide (M16).

## 6. Les graves

**G1. Quatre chapitres ne sont pas dans le dépôt, et le tome commité ne se construit pas.**
- **Où** : fichiers 02 à 05 (rédacteur A).
- **Le constat** : à `HEAD`, ce sont les squelettes de l'ossature. Le fichier 01, commité, renvoie à
  `t3ecl:sec:bruit`, `t3gen:sec:graine` et `t3gen:sec:transcription`, qui n'existent que dans les brouillons. Ce sont
  trois renvois indéfinis, et `construire.sh tome3-fr` tombe à son contrôle des références. La construction de
  l'état tête le montre : ces trois renvois, et eux seuls, restent indéfinis après quatre passes
  (`journaux/construction-tete.txt`), comme `statique.py` l'avait prédit sans compiler
  (`journaux/statique-tete.json`).
- **Le risque** : les brouillons existent et sont bons pour leurs chiffres (§ 3), mais les fichiers 04 et 05 ne sont
  que dans le répertoire temporaire de la session, où ils peuvent disparaître.
- **Le correctif** :
  1. recopier `redA/04-duplication.tex` et `redA/05-predictif.tex` dans `memoire/tome3/fr/chapitres/` ;
  2. vérifier, par les empreintes du tableau d'en-tête, que ce sont bien les octets jugés ;
  3. corriger G2 : seule la mise en page change, et tout autre changement est à rejuger ;
  4. `git add`, puis `git commit -- <les quatre fichiers>`, au nom de Stone, sans trailer.

  Dans la même passe, ajouter `python -I -X utf8 "$ici/outils/tome3_annexes.py"` à la cible `tome3` de
  `memoire/construire.sh`, avant latexmk (l'annexe B le demande).

**G2. Les quatre chapitres non commités débordent de la page.**
- **Où** : fichiers 02 à 05.
- **Le constat** : 19 boîtes trop pleines, dont 18 de plus de 10 pt et une de 149 pt (§ 2). Le tableau 6.6 (fichier
  05, l. 233–247) sort de la feuille, et sa colonne « même premier choix » est coupée au rendu, ce qui fait perdre
  des données à l'impression. Le rédacteur A n'avait pas fini ses essais.
- **Le correctif** :
  - pour les tableaux (fichier 02, l. 52–61, 129–141, 225–238, 274–292 ; fichier 03, l. 204–217, 272–291, 334–346,
    356–372 ; fichier 04, l. 166–184 ; fichier 05, l. 43–52, 137–149, 167–177, 191–205, 233–247, 253–264) : passer en
    `tabularx` sur `\linewidth`, avec les colonnes de texte en `X`, en `\footnotesize`, et `\setlength{\tabcolsep}{3pt}`
    quand il le faut, comme le font les fichiers 06 à 10 ;
  - pour les deux formules du fichier 04 (l. 34–35 et 139–140) : un `multline` ou une coupure ;
  - pour la cellule `zero_compte.py` (fichier 02, l. 37) et la commande `genome frontiere …` en `\texttt` du
    paragraphe « Témoin S0 » (fichier 03, l. 225–226) : les couper par `\allowbreak`.

  Puis recompiler jusqu'à 0 boîte de plus de 1 pt.

**G3. Les numéros de chapitre écrits en dur sont faux d'une unité dans le PDF.**
- **Où** : huit légendes jugées (neuf renvois) et cinq phrases.
- **Le constat** : l'introduction est un chapitre numéroté (comme au Tome II). Le fichier 07 s'imprime donc
  « chapitre 8 », le 08 « chapitre 9 », etc. Les légendes et le texte qui écrivent un numéro en dur suivent les
  fichiers et l'inventaire, pas l'impression.
- **Dans les légendes** (FR ; les mêmes en EN) :

  | fichier, ligne | écrit | désigne | s'imprime |
  |---|---|---|---|
  | `eclaireur-figures.tex` l. 135 (deux fois) | « chapitre 8 » | le codon | chapitre 9 |
  | `eclaireur-figures.tex` l. 186 | « chapitre 7 » | la synthèse | chapitre 8 |
  | `eclaireur-figures.tex` l. 228 | « chapitre 8 » | le codon | chapitre 9 |
  | `genome-figures.tex` l. 134 | « chapitre 7 » | la synthèse | chapitre 8 |
  | `synthese-figures.tex` l. 179 | « chapitre 8 » | le codon | chapitre 9 |
  | `codon-figures.tex` l. 426 (III-8.5) | « chapitre~7 » | la synthèse | chapitre 8 |
  | `synonyme-figures.tex` l. 360 (III-9.6) | « (ch.~7) » | la synthèse | chapitre 8 |
  | `juge-figures.tex` l. 158 (III-10.1) | « des chapitres 8 à 10 » | 08 à 10 | chapitres 9 à 11 |

- **Dans le texte** :

  | fichier, ligne | écrit | s'imprime |
  |---|---|---|
  | 01 l. 218 | « Les chapitres 2 à 5 » | chapitres 3 à 6 |
  | 07 l. 177 | « le chapitre~8 » (le codon) | chapitre 9 |
  | 10 l. 142 | « des chapitres 8 à 10 » | chapitres 9 à 11 |
  | annexe A l. 45 | « (ch. 6) » | chapitre 7 |
  | annexe A l. 139 | « le chapitre 6 » | chapitre 7 |

  Le numéro de figure de l'inventaire, cité dans le texte comme « III-4.8 » (fichier 04, l. 269), est aussi différent
  de celui qui s'imprime (« Figure 5.x ») ; les notations le disent.
- **Le correctif** : remplacer chaque numéro par son renvoi : `\cref{t3cod:ch}`, `\cref{t3syn:ch}`,
  `\crefrange{t3cod:ch}{t3jug:ch}`, `\crefrange{t3ecl:ch}{t3pre:ch}`, `\cref{t3mim:ch}`. Les légendes appartiennent au
  flux des figures : leur correction est une retouche de neuf renvois, sans changer un nombre ni un trait. Dans le
  texte, écrire `\cref{fig:t3-dup-arbre}` au lieu de « III-4.8 ». L'autre voie, une introduction non numérotée,
  changerait la forme du Tome II et laisserait la question des numéros de figure : je ne la recommande pas.

**G4. Le juge du tome n'est pas défini avant d'être utilisé, et le résumé est vide.**
- **Où** : fichiers 00 à 06, et `memoire/tome3/fr/resume.tex`.
- **Le constat** : la KL décide dès l'introduction, mais sa définition est au fichier 07 (l. 33). Le résumé est un
  gabarit vide : la page iii ne porte que le mot « Résumé », et la page v que le mot « Abstract ».
- **Le correctif pour la KL** : au fichier 02, au paragraphe « Le protocole (P1 de la ronde) » (l. 308), poser en
  quatre phrases :
  - ce qu'est la KL d'une position ;
  - ce qu'est sa moyenne sur R1 : dix fenêtres de wiki.test, 2 550 positions notées (255 par fenêtre), contre la
    référence f64 du lot R ;
  - la convention de coupe.

  Renvoyer ensuite à la dérivation du fichier 07 et à la théorie du juge du Tome II, et mettre dans l'introduction un
  renvoi vers ce paragraphe.
- **Le correctif pour le résumé** : écrire les cinq paragraphes du gabarit du Tome II, chaque nombre repris d'un
  chapitre, le tableau des verdicts du fichier 13 donnant la matière : d'où l'on part ; ce que le tome donne ; les
  résultats en nombres, avec ce qui a été barré ; le juge ; ce qui reste.

**G5. Le vocabulaire du projet n'a pas de table, et « R1 » a deux sens.**
- **Où** : `memoire/tome3/commun/notations.tex` et tous les chapitres.
- **Le correctif** : remplir la table « Les noms du travail » avec :
  - la KL et sa moyenne ;
  - les fenêtres R1 et les fenêtres neuves du juge ;
  - les lots R, A et B ; F1 et l'arbitre ;
  - la frontière : sans perte, 3,8431 bits en A\_ctx et 3,8434 en A\_flux ; la base, 2,6441 ;
  - A\_ctx et A\_flux ; κ, λ, δ\* et S\* ;
  - les protocoles P0, P1, P2, P2-10 et P3 (le tableau du fichier 07, l. 40, en est la source) ;
  - J1, ABBA et r(B/A) ;
  - v1.0, v1.2 et le compagnon rapide ;
  - 20b et 120b ; MXFP4, E2M1 et E8M0.

  Puis lever l'ambiguïté de R1 : écrire partout « la réserve R1 » pour la réserve, ou la renommer (« réserve V1 »,
  pour la vitesse), et garder « R1 » pour les fenêtres.

**G6. L'ancienne attribution du ×1,44, sans barre.**
- **Où** : fichier 10, l. 11.
- **Le constat** : « un J1 du 120b 1,45 fois plus rapide en v1.2, qu'il refuse lui-même d'attribuer au format
  (\cref{t3cod:ch}) ».
- **Le correctif** : « un J1 du 120b 1,45 fois plus rapide en v1.2, \barre{qu'il refuse lui-même d'attribuer au
  format} que le juge du placement a depuis attribué au format v1.2, par le motif de ses requêtes de lecture, propre
  à ce disque (réserve R1, \cref{t3jug:sec:…}) ».

**G7 (corrigé par moi). Une valeur mêlée de deux références, dans le tableau des verdicts.**
- **Où** : fichier 13, l. 32.
- **Le constat** : le texte donnait « −0,142 et −0,128 bit à la couche 0 » pour le contexte de colonne. C'est la
  paire de `05-synthese.md` § 0, que le fichier 07 (l. 177 et 557) dit mêlée : gate mesuré contre le flux octet
  (3,607307 − 3,465690 = 0,1416), up contre le flux demi-octet (3,620534 − 3,492399 = 0,1281). Contre la même
  référence, le flux octet (celle de la décision du lot A et du fichier 08), up vaut 3,615530 − 3,492399 = **0,1231**
  (`mesures/genome/construction/synthese/colonne-par-tenseur.csv`).
- **La correction** : « −0,142 et −0,123 bit à la couche 0 (gate et up, contre le flux octet) » (§ 8).

## 7. Les mineurs

**Des arrondis faux au dernier chiffre.**
- **M1.** Fichier 01, l. 145 : ½ log₂(πe/6) vaut 0,25461, imprimé 0,254. Arrondi juste : 0,255, ou 0,2546. La source
  00 écrit aussi 0,254 ; la valeur classique s'écrit souvent ainsi, tronquée.
- **M2.** Fichier 10, l. 428 : 0,95⁶⁴ vaut 3,752 %, imprimé 3,7 %. Arrondi juste : 3,8 %. Le nombre est recopié
  fidèlement de `JUGEMENT-construction.md` (l. 480), qui porte la même erreur.
- **M3.** Fichier 12, l. 44 : (1 − √(512/2880))² vaut 0,33450, imprimé 0,334. Arrondi juste : 0,335, ou 0,3345.
- **M4.** Fichier 10, l. 306 : « seuil 2,00 × (1 − 2 × 0,058) = 1,769 » ; avec 0,058, le produit vaut 1,768. Le
  1,769 de la source vient du σ non arrondi : écrire « σ = 0,0578 », ou « ≈ ».

**Des sources et des nombres à préciser.**
- **M5.** Fichier 06, l. 269 : « 0 de succès RAM à R = 80 et 160 sur les 7 traces » cite `t1bord.csv`, qui n'a que
  R = 326. Le zéro est dans `grille.csv`, où je l'ai refait (0,0 sur les 7 traces, aux deux R). Ajouter `grille.csv`.
- **M6.** Fichier 13, l. 50 : « une KL de l'ordre de 0.03 » pour P3. La KL jugée vaut 0,0314 en ligne
  (β₁ = 0,041), 0,0209 et 0,0239 à l'étage B : dire laquelle.
- **M7.** Fichier 03, l. 382 : le rapport 1,335 de S\* à 3 fenêtres est imprimé sans barre, alors que le fichier 07
  le barre. Le barrer comme sa conclusion, ou dire en une incise qu'il n'est donné qu'à titre d'historique.
- **M9.** Introduction, l. 79 : préciser « A\_flux » pour 3,8434 → 3,7064, puisque les fichiers 01 et 02 donnent
  3,8431 → 3,7061 (A\_ctx).
- **M14.** Des sources nommées sans entrée biblatex : Everett (1963) au fichier 03 ; Cover et Thomas, Gray et Markel,
  Schuchman, Zamir et Feder au fichier 12, « cités d'après la note de la piste ». `cover2006` existe déjà dans
  `commun.bib`, et le fichier 01 la cite. Ajouter les autres avec leur adresse et leur date de consultation, ou dire
  au lecteur qu'elles sont de seconde main.

**De la lecture et de la forme.**
- **M8.** Fichiers 06 et 08 : les figures III-6.13 (`fig:t3-mim-p6`) et III-8.7 (`fig:t3-codon-format`) sont placées
  et légendées, mais aucun `\cref` du texte ne les appelle. Ajouter l'appel au paragraphe qui les commente : pour P6,
  « La courbe KL(f) » ; au fichier 08, le paragraphe sur le format v1.2 au bit.
- **M10.** Les répétitions du § 5 : le motif croisé (08, 09 et 10), l'histoire de la KL 0,0262 (02, 07, 10 et 13) et
  les 64 codons (00, 02, 03 et 09). Garder le récit complet à un endroit (le 08 pour le motif, le 07 pour la KL) et
  renvoyer ailleurs.
- **M11.** Fichier 02, l. 31, premier tableau : « YaRN », « fourche » et `trc-reference` arrivent sans glose. Une
  phrase avant le tableau suffit.
- **M12.** Fichier 11 : le lemme de Rényi est énoncé sans démonstration (cité, article non relu, et c'est dit). Une
  démonstration tient en cinq lignes (espacements d'exponentielles i.i.d., absence de mémoire) et rendrait le
  chapitre autonome.
- **M15.** Quatre boîtes trop pleines dans la table des matières (1,5 à 5,1 pt) : des numéros de page en gras qui
  dépassent. C'est le même gabarit que le Tome II ; à régler dans `memoire/commun/preambule.tex` seulement si les
  Tomes I et II n'en bougent pas.

- **M16.** Le tome n'a aucun listing (`.lol` vide : 0 entrée, contre 50 figures et 99 tableaux), et pourtant le
  maître imprime une « Liste des listings » vide (page xxi). SOCLE demande « le code commenté des mécanismes clés en
  listings ». Deux voies : ajouter deux ou trois extraits vérifiés par diff, comme au Tome I (la réécriture −0 → +0
  du codeur, le choix des symboles de la mutation synonyme, le décodage rANS vectorisé du juge) ; ou retirer
  `\lstlistoflistings` du maître.

**À porter hors du tome.**
- **M13.** L'orchestrateur doit porter deux corrections dans les sources, que le tome cite :
  - celle du fichier 04, dans `genome/duplication.md` (§ 0 point 6) et dans `genome/05-synthese.md` (§ 3.2) ;
  - la ligne non barrée de `genome/JUGEMENT-construction.md` § 8.

## 8. Ce que j'ai corrigé

J'ai corrigé un seul chiffre, mal recopié, comme la consigne le permet : dans
`memoire/tome3/fr/chapitres/13-discussion.tex` (l. 32), « $-\num{0.128}$ » devient « $-\num{0.123}$ », suivi de
« (gate et up, contre le flux octet) » pour dire la référence (G7). Le diff tient en une ligne. Le chapitre corrigé,
compilé seul avec le préambule, la bibliographie et les figures du maître (`essai-13.tex`, trois passes et biber),
rend 0 erreur, 0 boîte trop pleine et 5 pages ; ses seuls renvois indéfinis visent les autres chapitres. Mes deux
constructions complètes (§ 2) portent sur le fichier d'avant la correction. Rien d'autre n'est touché. Les graves G1 à G6 et
les mineurs sont rapportés, pas corrigés : ils touchent des fichiers d'autres rôles (les brouillons non commités du
rédacteur A, les légendes jugées) ou demandent d'écrire, ce qui n'est pas mon rôle.

## 9. Ce qui pourrait être faux

- **Le tirage ne voit pas tout.** 71 chiffres sur 5 357 candidats, cinq par chapitre : un chapitre peut porter des
  erreurs que cinq tirages ne touchent pas. Si 2 % des 400 nombres d'un chapitre étaient faux, cinq tirages les
  manqueraient tous avec une probabilité de 0,98⁵ ≈ 90 %. Le tirage dit que les erreurs ne sont pas fréquentes, pas
  qu'il n'y en a pas. Les calculs neufs du § 3.2, que j'ai refaits sans tirage, en ont donné quatre au dernier
  chiffre.
- **J'ai changé mon extracteur après un premier tirage**, avant toute vérification, pour une raison dite (§ 1). Le
  premier tirage reste dans `journaux/tirage-v1.csv` : qui veut le refaire le peut.
- **19 nombres ne sont vérifiés que par leur citation.** Si la source est fausse, le texte l'est avec elle. C'est le
  rôle des juges de ces sources ; je ne l'ai pas refait.
- **La lecture n'est pas une relecture ligne à ligne.** J'ai lu :
  - l'introduction, les origines, les « En bref » et les « Ce qui pourrait être faux » ;
  - les paragraphes qui entourent chaque chiffre tiré et chaque figure relue ;
  - tout ce que les recherches du § 4 ont fait sortir.

  Je n'ai pas lu chaque démonstration mot à mot : une dérivation fausse, dans un passage que je n'ai pas lu, peut
  m'avoir échappé.
- **Les brouillons peuvent changer avant leur commit.** Ce jugement porte sur les empreintes du tableau d'en-tête.
- **`barres.py` donne une liste, pas un verdict.** Sur 401 occurrences, je n'ai lu que les familles qui portent une
  correction. Un nombre barré ailleurs, pour une raison que je ne connais pas, peut revenir dans une des autres.
- **La construction est celle de latexmk dans un dossier d'essai, pas `construire.sh` lui-même.** Je n'ai pas relancé
  les huit outils de données : ils écrivent des fichiers commités qui ne sont pas à moi, et leur régénération au bit
  est jugée par `JUGEMENT-figures3.md` § 4.3. Le PDF des spectres est celui que `construire.sh` avait déjà compilé.
  Les contrôles du journal sont ceux de `construire.sh`, recopiés.
- **G3 se discute.** Si l'on préfère une introduction non numérotée, ce sont les renvois au Tome II et la forme
  commune des tomes qui bougent, et non les légendes. J'ai jugé que la numérotation du Tome II fait foi.

## 10. Reproduire

Depuis la racine du dépôt (Git Bash ; Python 3.13, bibliothèque standard ; MiKTeX 26.5) :

```
J=outils/genome/tome3/juge-redaction
python -I -X utf8 $J/assembler.py --etat tete
python -I -X utf8 $J/assembler.py --etat brouillon --remplacer 02-eclaireur=<02> --remplacer 03-genome=<03> \
    --remplacer 04-duplication=<04> --remplacer 05-predictif=<05>
bash $J/construire.sh brouillon ; bash $J/construire.sh tete          # chacun 30 min environ
python -I -X utf8 $J/journal.py memoire/essai/juge-redaction-fr-brouillon/troncons-tome3-fr.log
python -I -X utf8 $J/statique.py memoire/essai/juge-redaction-fr-brouillon     # --casser : code 1
python -I -X utf8 $J/tirage.py memoire/essai/juge-redaction-fr-brouillon --graine 20261029 --par 5 \
    --sortie $J/journaux/tirage.csv
python -I -X utf8 $J/refaire.py                                                 # --casser : les 52 tombent
python -I -X utf8 $J/calculs.py
python -I -X utf8 $J/paralogues.py                                              # --casser : comptes inversés
python -I -X utf8 $J/barres.py memoire/essai/juge-redaction-fr-brouillon       # --casser : code 1
python -I -X utf8 $J/typographie.py memoire/essai/juge-redaction-fr-brouillon
python -I -X utf8 $J/enonces.py memoire/essai/juge-redaction-fr-brouillon
```

`typographie.py` répond à une question que je me suis posée en lisant. Les fichiers 00, 09, 10 et 13 écrivent leurs
décimaux `\num{0.1522}`, que siunitx rend avec une virgule en français. Hors de `\num` et `\SI`, aucun décimal à
point ne s'imprime : les 18 relevés sont des numéros de version (1.2) et des `\arraystretch`.
