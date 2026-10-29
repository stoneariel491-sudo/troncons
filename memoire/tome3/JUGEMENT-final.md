# Tome III : le jugement final

Juge final indépendant du Tome III, 2026-10-29. Je n'ai rien écrit de ce que je juge. Objet : le tome tel qu'il
est commité à `9db456b` (main), en français et en anglais (`memoire/tome3/{fr,en}/`, maîtres, chapitres,
annexes, `resume.tex`, `commun/`), et tout ce qui a changé depuis le premier jugement
(`memoire/tome3/JUGEMENT-redaction-fr.md`, commit `99d009d`). Lu avant : `SOCLE.md`,
`memoire/tome3/REPRISE-figures.md` (section « Rédaction »), `JUGEMENT-redaction-fr.md`, les notes
`REPRISE-redaction-*.md`, `PLAN-redaction.md`. Aucune carte graphique, aucune mesure. Mes outils et journaux :
`outils/genome/tome3/juge-final/` ; ma construction : un arbre de travail séparé du dépôt, avancé à `9db456b`.

**Une convention.** Comme le premier juge, je nomme les chapitres par leur fichier (00 à 13) ; dans le PDF,
l'introduction est le chapitre 1, le fichier 07 s'imprime « chapitre 8 ». Les lignes sont celles des fichiers
à `9db456b`.

## 0. Verdict

**Le Tome III dit vrai, et il le dit de même dans les deux langues, chiffre pour chiffre. Il est publiable après
quatre retouches de forme et d'outil, dont aucune ne touche un résultat.**

- **L'anglais est le français.** Sur les 18 fichiers des deux langues, l'outil de parité ne trouve aucun nombre
  changé : 12 865 nombres en français, 12 880 en anglais, mêmes barres (70), mêmes étiquettes dans le même ordre
  (497), mêmes citations, mêmes fichiers cités. Les écarts qu'il relève sont huit, tous lus et expliqués
  (§ 1.2) ; ils font à eux seuls les 15 nombres de plus de l'anglais. Sa cassure fait tomber les 18 fichiers.
- **Le PDF anglais se refait depuis le commit.** `construire.sh tome3-en` : code 0, 21 minutes, **300 pages**,
  0 erreur, 0 renvoi ni citation indéfinis, biber sans erreur, aucun caractère manquant, 7 boîtes trop pleines
  (4 dans la table des matières, de 1,5 à 5,1 pt ; 3 sous 1 pt). Son texte est celui du PDF commité, ligne pour
  ligne, **sauf deux tables engendrées**, qui ne viennent pas du commit (G3).
- **Les pages retouchées sont justes.** 73 chiffres neufs ou déplacés depuis le premier jugement, refaits par mon
  propre chemin depuis leurs fichiers : 73 égaux à l'arrondi imprimé, 0 faux (cassure : les 73 tombent). Le
  listing du fondu est égal au bit aux sources Rust commitées. La démonstration neuve du lemme de Rényi tient,
  ligne à ligne. Les barres de la construction finale disent vrai.
- **La réserve R1 tient partout**, dans les deux langues, légendes comprises : le ×1,44 du J1 est attribué au
  format v1.2 par le motif de ses requêtes de lecture, propre à ce disque ; « l'état du fichier » n'apparaît
  que barré, ou comme ce qui a été démenti. Aucun chiffre barré dans une source ne revient comme valide.
- **Le résumé et l'introduction disent vrai de tout le tome**, à deux nuances près (M3, M4).
- **La langue anglaise** est correcte et lisible, mais elle a deux traducteurs et cela se voit : **deux
  vocabulaires pour les mêmes notions** (G1), des calques réguliers (M1), trois typographies du pour-cent (M2).
  Le résumé français du tome anglais est composé à l'anglaise (G2).

**Graves : 4** (G1 à G4, aucun de fond). **Mineurs : 9.** Répétitions à resserrer : 3 (§ 5). Je n'ai corrigé
aucun chiffre : je n'en ai trouvé aucun mal recopié.

## 1. Le tome anglais

### 1.1 La construction

Construit dans un arbre de travail séparé, avancé à `9db456b`, par `bash memoire/construire.sh tome3-en`
(les huit outils de données des figures, les figures des spectres, `tome3_annexes.py`, latexmk) :
`journaux/construction-en.txt`.

| | valeur |
|---|---|
| code de sortie | 0 (07 h 21 à 07 h 42) |
| pages | 300 |
| erreurs, renvois ou citations indéfinis, caractères manquants | 0, 0, 0 |
| biber | aucune erreur, aucune entrée absente ou double |
| boîtes trop pleines | 7 : table des matières 1,73, 5,08, 1,53, 1,53 pt (M15 du premier jugement, préambule commun) ; 0,61 et 0,55 pt au 11, 0,44 pt au 12 |

`pdftotext` du PDF refait contre celui du PDF commité (`journaux/pdf-en-commite-contre-refait.diff`) : 15 741
lignes de part et d'autre, **12 lignes différentes, toutes dans les tables engendrées des annexes B et C** (G3).
Tout le reste du texte imprimé est égal.

### 1.2 Les nombres, fichier par fichier

`parite_nombres.py` est écrit sans rien reprendre des outils des traducteurs. Il travaille ainsi :
- il ôte les commentaires ;
- il neutralise ce qui ne s'imprime pas comme un nombre du texte : étiquettes, renvois, citations, fichiers,
  entrées, largeurs de colonne, unités de `\SI` ;
- il lit la virgule décimale française et les séparateurs de milliers ;
- puis il compare, fichier par fichier : les multiensembles de nombres, leurs suites dans l'ordre (difflib), les
  fichiers cités, les clés citées, les renvois, le nombre de barres et la suite des étiquettes.

Sa cassure décale le dernier chiffre du premier nombre de chaque fichier anglais : les 18 fichiers tombent
(`journaux/parite-casser.txt`).

| fichier | nombres FR / EN | barres | étiquettes | verdict |
|---|---|---|---|---|
| 00 | 67 / 67 | 1 | 7 | parité ; expliqué : l'exemple `\fichier{comme ceci}` traduit |
| 01, 02, 03, 05, 10, 12, 13, A, B, C | égaux | égales | égales | parité |
| 04 | 963 / 964 | 2 | 28 | parité ; expliqué : `$\{0,1\}$` lu comme un décimal français |
| 06 | 1 968 / 1 969 | 5 | 90 | parité ; expliqué : `$\{0,1\}$`, idem |
| 07 | 1 136 / 1 135 | 12 | 49 | parité ; expliqué : « le terme d'ordre 1 » rendu « first-order term » |
| 08 | 1 098 / 1 105 | 3 | 36 | parité ; expliqué : deux gloses anglaises, celle des commentaires du listing (8, 0) et celle du message de la garde du moteur (couche 0, expert 30, 11 234 960 octets), cité en français puis traduit |
| 09 | 1 271 / 1 273 | 8 | 45 | parité ; expliqué : `$\{0,1,2,3\}$` |
| 11 | 820 / 820 | 9 | 43 | parité ; expliqué : la coupe du routeur dans sa langue (`-fr.png`, `-en.png`) |
| `resume.tex` | 112 / 117 | 0 | 0 | parité ; expliqué : le fichier anglais porte aussi le Résumé français, dont l'outil lit les virgules à l'anglaise |

Les blocs hors d'ordre (au plus 6 par fichier) sont des ordres de mots anglais (« 120b » avant ou après son
nombre). Les deux blocs du résumé sont égaux au caractère près dans `fr/resume.tex` et `en/resume.tex`
(`resumes.py`).

Les fichiers bilingues (`\EF{anglais}{français}`) sont comparés paire par paire par `parite_ef.py` :
- `commun/notations.tex` : 49 paires, 0 écart réel (le seul relevé est un renvoi `\crefrange` écrit
  « chapters~\ref{…} to~\ref{…} » en anglais) ;
- les sept fichiers de légendes touchés par G3, et la table des outils : 0 écart.

Le listing du fondu est le même octet pour octet dans les deux langues (`listing.py`).

### 1.3 Le sens, passage par passage

J'ai lu, en anglais, contre le français :
- l'« In brief » de chaque chapitre, 00 à 12 ;
- au 13, « What this does, for the machine » et la conclusion ;
- au 10, l'ouverture (la fuite G6 du premier jugement, réécrite) et la section de la réserve R1 ;
- au 08, les deux phrases barrées et le point barré du « What could be wrong » ;
- l'ouverture des annexes A, B et C ;
- le résumé entier ;
- et toutes les phrases anglaises qui parlent de l'état des fichiers (R1).

Je n'y ai trouvé aucun contresens, aucune réserve perdue, aucune barre déplacée. Les citations de Stone sont
gardées en français, avec leur traduction.

### 1.4 La langue et la typographie

**La langue est un anglais de traducteur fidèle, pas encore un anglais de mémoire.** La syntaxe est juste et
l'on se lit sans peine. Mais trois choses trahissent le français :
- le vocabulaire change à la moitié du tome (G1) ;
- des tours calqués reviennent (M1) ;
- les phrases gardent l'ordre français (« The answer of information theory is harsh », 01).

**La typographie anglaise** est tenue dans l'essentiel : guillemets ``…'', point décimal, aucune espace avant
« ; : ? ! » hors des formules, `Volume~II`, unités MB et GB. Restent :
- trois écritures du pour-cent (M2) ;
- le Résumé français du tome anglais, composé à l'anglaise (G2).

## 2. Les pages retouchées depuis le premier jugement

**Ce que couvre le diff.** Pour 02 à 05, je pars des octets jugés, `57db4ce`. Pour le reste, je pars de
`99d009d`. J'ai lu tout le diff mot à mot (`git diff --word-diff`) :
- les tableaux et formules des 02 à 05 (G2) ;
- le paragraphe de la KL au 02 et à l'introduction ;
- le 1,335 barré au 03 ;
- la table des notations ;
- les renvois des légendes (G3) ;
- le listing ;
- la preuve de Rényi ;
- les arrondis M1 à M4 ;
- les trois barres de la construction finale ;
- les barres portées dans `genome/` (M13) ;
- `construire.sh` et `tome3_annexes.py` ;
- le résumé.

**Les 02 à 05 commités sont les octets jugés.** Les empreintes de 02, 04 et 05 sont égales à celles du premier
jugement. Celle de 03 diffère :
- l'objet git de `57db4ce` a l'empreinte `6ace323d3a52` (56 192 octets) ;
- le jugement donnait `56f1d0bf392c` (56 650 octets), empreinte de la copie de travail.

La différence est faite des fins de ligne, et d'elles seules : 458 lignes, 458 octets ; la copie était en CRLF
(`core.autocrlf=true`) ; l'objet, mis en CRLF, redonne `56f1d0bf392c`. Le contenu jugé est donc bien celui du
commit (M7).

### 2.1 Les chiffres neufs ou déplacés, refaits

`refaire_neufs.py` lit directement les JSON et les CSV commités et refait chaque nombre. Il ne reprend le code
d'aucun outil, ni celui des rédacteurs, ni celui du premier juge. Un chiffre est juste s'il redonne l'imprimé à
son arrondi. La cassure décale chaque imprimé d'une unité du dernier chiffre : les 73 tombent
(`journaux/refaire.txt`, `refaire-casser.txt`).

| où | imprimé | refait depuis | refait |
|---|---|---|---|
| 02, la KL en quatre phrases | 2 550 positions, 255 par fenêtre, $e^{-16} \approx 1{,}1\cdot10^{-7}$ | `kl-frontiere-positions.csv` ; calcul | 2 550 ; 255 dans chacune des 10 ; 1,125·10⁻⁷ |
| 02, la coupe | ne somme que $\log p_{t,i} > -16$, en nats | `moteur/crates/trc-juge/src/stats.rs` l. 77 | `if lp > -16.0 { kl += lp.exp() * (…) }` |
| notations | R1 : fenêtres 0 à 9 de 512 jetons ; calibration : 10 à 21, 6 132 positions | `capture-eval.json` (5 110 = 10 × 511), `capture-calib.json` | égaux |
| notations | 768, 4 608 experts ; 17 octets par bloc | 24 × 32, 36 × 128, 1 + 16 | égaux |
| 03 | \barre{1,335} → 1,018 $= 0{,}020\,93/0{,}020\,57$ | `kl/comparer10-base-contre-recette.json` | 0,020933 / 0,020570 = 1,0176 |
| 00 | A\_flux 3,8434 → 3,7064 ; A\_ctx 3,8431 → 3,7061 | `zero-canonique.json` | 3,706406 ; 3,706142 |
| 01 | ½ log₂(πe/6) = 0,2546 ; 1,53 dB | calcul | 0,254614 ; 1,5329 |
| 12 | (1 ∓ √(512/2 880))² = 0,3345 et 2,021 | calcul | 0,334504 ; 2,021052 |
| 06 | 0 succès RAM inclusif à R = 80 et 160, 7 traces | `mesures/mimetisme/P2/grille.csv` | 0,0 sur 32 lignes, 7 traces (et leur réunion « tous ») |
| 07, l'expert pont | substituer mieux : 4/32, 5/32, 25/31, 21/31 ; « d'au plus un demi-point » | `duplication/csv/paralogues.csv` | égaux ; écarts moyens −3,32, −4,72, +0,497, +0,024 point |
| 10, J-V2 | σ = 0,05764, seuil 1,769 ; toit 686,8/468,5 = ×1,47 | `juge/vitesse/analyse-120b.json` | 0,0576448 ; 1,769421 ; 1,4657 |
| 10, M2 | $0{,}95^{64} \approx 3{,}75\,\%$ ; $0{,}95^{32} \approx 19\,\%$ | calcul | 3,752 % ; 19,37 % |
| 13, P3 (M6) | 0,0209 et 0,0239 à l'étage B | `P3/juge/etage-B/kl-b0.0{6,7}-positions.csv` | 0,020890 ; 0,023934 |
| 13, P3 (M6) | 0,0314 au routeur en ligne ($\beta_1 = 0{,}041$) | `genome/mimetisme/P3/JUGEMENT-routeur-ligne.md` | 0,031388 (cité, non refait) |
| résumé, 13 | 0,12791 et 0,12562 bit ; 1,80 Go ; 3,3 % d'octets | `codon/tailles.json` ; `analyse-120b.json` (octets par pas B/A) | 0,1279150 ; 0,1256207 ; 1,8005 ; 3,290 % |
| résumé | 0,9999999967 bit | `zero-compte-20b.json` | égal |
| résumé, 09, 13 | KL 0,1318 (λ = 0) et 0,2640 (frontière), 768 experts, R1 ; « divise par deux » ; 0,1522 (λ = 1) | positions de `juge/kl/kl-r1-*-768-positions.csv`, mes moyennes | 0,131753 ; 0,263990 ; 0,4991 ; 0,152155 |
| résumé, 13 | λ = 0 contre λ = 1 : 2,09 σ sur R1, 3,6 σ hors de R1 (−0,0303 ± 0,0084) | mes paires par position, σ par fenêtres | 2,0940 ; 3,6214 (−0,030318 ± 0,008372) |
| résumé, 13 | −0,1565 ± 0,0334, 4,7 σ (J-K1) | mes paires de `kl-neuf-sub-l0` et `kl-neuf-sub-frontiere` | −0,156481 ± 0,033389 ; 4,687 |
| résumé | 2,67 bits | `synonyme/rapide/coder-synonyme-l0.json` | 2,67170 (bits utiles) |
| résumé, 13 | ×0,94 (20b), ×1,28 et ×1,44 (120b) | `analyse-20b.json`, `analyse-120b.json` | 0,9418 ; 1,2843 ; 1,4415 |
| résumé, 13 | +0,0004 ± 0,0019 (S\*, K10) | `comparer10-base-contre-recette.json` | 0,000363 ± 0,001856 |
| résumé, 13 | graine 3,06 bits | `genome/csv/graine-mesure-theorie.csv`, points (12, 4) et (10, 3) | 3,0613 en interpolant en log de l'erreur ; 3,0662 en linéaire (M6) |
| résumé, 13 | recette sans perte 4,05 à 4,37 contre 3,84 | `genome/codons-tourne-l12.json` (12 tenseurs × 5 réglages ; `global`) | 4,0549 à 4,3731 ; 3,84314 |
| résumé, 13 | 0,0034 bit, dont 0,0016 au hasard (net 0,0019, 48 matrices) | `duplication/csv/d1-sans-perte.csv` | 0,003421 ; 0,001552 ; 0,001869 ; 48 |
| résumé, 13 | 57,1 % des bascules pour 10 % ; 80 % coûterait 26,6 % | `pistes/tropicale/garde-resume.json` | 57,106 % (2 905 sur 5 087) ; 26,601 % |
| résumé, 13 | 0 matrice sur 48 au critère principal ; 9 compatibles | `pistes/spectres/juge/juge-csn.csv` (groupe « réel ») | 0 ; 9 sur 48 |

Deux remarques :
- **Le 26,6 % du coût de 80 %** (0,26601 des cellules) n'est pas le 26,6 % de la propagation, que le premier juge
  avait refait (26,646 %). Ce sont deux grandeurs que l'arrondi rend égales, et le texte ne les confond pas.
- **Le 3,3 %** est la baisse des octets lus par pas au J1 (3,290 %). Celle des octets des tronçons est de
  3,249 %, celle du fichier de 3,119 % (`tailles.json`) ; le texte parle bien des octets lus.

### 2.2 Le listing

`listing.py` extrait de `git show main:` les lignes 67 à 77 de `moteur/crates/trc-format/src/lib.rs` et 317 à
327 de `moteur/crates/trc-codec/src/lib.rs`. Les 23 lignes du listing `t3cod:lst:fondu` leur sont égales, au
caractère près, et l'anglais est égal au français. Cassure : un 8 changé en 9 dans l'extrait, et l'outil tombe.

Ce que le code fait est bien ce que le texte en dit :
- `canoniser_demi` rend 0 pour 8 et laisse tout autre code inchangé ;
- `canoniser_octet` canonise les deux demi-octets ;
- `canoniser_qs` compte `((q & 15) == 8) + ((q >> 4) == 8)` par octet avant de le réécrire, soit exactement le
  nombre de demi-octets changés.

### 2.3 La preuve neuve : le lemme de Rényi (11, l. 167 à 169)

Je l'ai suivie ligne à ligne :
1. $Y_j = X_{(n+1-j)}$ range les variables par ordre croissant. $Y_0 = 0$ revient à poser $X_{(n+1)} = 0$, ce
   qui donne un sens à $D_n = X_{(n)}$.
2. $P(Y_1 > y) = \prod_i P(X_i > y) = e^{-n\lambda y}$ : le minimum suit $\mathrm{Exp}(n\lambda)$. Juste.
3. Sachant $Y_1 = y$ et l'indice qui l'atteint, la densité jointe se factorise. Les $n-1$ autres variables sont
   indépendantes, de loi conditionnée par $X > y$, et, par l'absence de mémoire, leurs excès sont
   $\mathrm{Exp}(\lambda)$, indépendants, de loi libre de $y$ et de l'indice. Juste.
4. $Y_2 - Y_1$ est le minimum de ces excès : $\mathrm{Exp}((n-1)\lambda)$, indépendant de $Y_1$. Juste.
5. La récurrence donne les $Y_{j+1} - Y_j$ indépendants, de taux $(n-j)\lambda$. Le texte dit « en
   recommençant ». L'indépendance d'avec tout le passé, et non seulement d'avec $Y_j$, découle du même
   conditionnement : c'est exact, et assez dit pour un lemme classique.
6. $Y_{j+1} - Y_j = X_{(n-j)} - X_{(n-j+1)} = D_{n-j}$, et $k = n - j$ donne le taux $k\lambda$. L'indice est
   juste.

**La preuve tient.** L'usage qui suit tient aussi :
- la pente de $-\ln(1-F)$ est $f/(1-F) = \eta$ ;
- la marge $m = D_4$ ;
- $f_m(0) \approx 1/\E[m]$.

La phrase « la démonstration ne dépend pas de l'article » est vraie. Le « Ce qui pourrait être faux » du
chapitre dit, à juste titre, que les 32 logits ne sont pas i.i.d.

Un détail de forme : l'énoncé ne dit pas l'étendue de $k$. Il faudrait écrire « $k = 1, \dots, n$, avec
$X_{(n+1)} = 0$ », ce que seule la preuve pose (M5).

### 2.4 Les barres de la construction finale

- **07 l. 541, l'expert pont.** La phrase « substituer n'est jamais meilleur que retirer l'expert » est barrée.
  La correction dit : retirer vaut mieux aux couches 0 et 8, et le paralogue fait un peu mieux aux couches 16 et
  23, « d'au plus un demi-point ». Je l'ai refaite : +0,497 et +0,024 point. Les §§ cités sont justes :
  `genome/duplication.md` § 0 point 6 (l. 39) et `genome/05-synthese.md` § 3.2 (l. 383, et aussi le § 0,
  l. 57).
- **08 l. 397 et le point du « Ce qui pourrait être faux ».** La ligne du § 8 de `JUGEMENT-construction.md` est
  bien barrée depuis `800d59e`, avec ce qui a changé.
- **Annexe B, § « L'outil des annexes ».** La barre est juste : l'outil est dans la cible depuis `57db4ce`. Mais
  la même phrase fausse reste sans barre dans l'« Il reste » de la même annexe (G4).
- **Dans `genome/` (M13 du premier jugement).** `duplication.md`, `05-synthese.md` (§§ 0 et 3.2) et
  `JUGEMENT-construction.md` § 8 sont barrés, avec ce qui a changé et les comptes que j'ai refaits.

### 2.5 Les correctifs du premier jugement

| | état |
|---|---|
| G1 | tenu (les 02 à 05 commités sont les octets jugés, à la fin de ligne près ; l'outil des annexes est dans `construire.sh`) |
| G2 | tenu (0 boîte dans 02 à 05, en français comme en anglais) |
| G3 | tenu (aucun numéro de chapitre écrit en dur hors des renvois aux Tomes I et II, dans le texte ni dans les légendes ; l'annexe B engendre des renvois) |
| G4 | tenu (le juge posé au 02 avant son premier usage ; un renvoi depuis l'introduction ; un résumé et un abstract) |
| G5 | tenu (29 lignes de notations ; « la réserve R1 » partout où c'est la réserve) |
| G6 | tenu (réécrit, sans barre, mais avec ce qui a changé et la réserve R1) |
| G7 | gardé |
| M1 à M9, M11 à M14, M16 | tenus |
| M10 (répétitions), M15 (table des matières) | non faits (§ 5 ; préambule commun) |

## 3. Les graves

**G1. Le tome anglais parle deux vocabulaires, un par traducteur.**
- **Où** : les chapitres 00 à 06 et le résumé (EN1), contre les 07 à 13 et les annexes (EN2) ; et les
  notations, communes aux deux.
- **Le constat** : une même notion porte deux noms selon la moitié du tome.

  | notion (français) | dans 00–06, le résumé, les notations | dans 07–13, les annexes |
  |---|---|---|
  | témoin (la règle de SOCLE) | *witness* (62 fois ; `en/chapitres/02-eclaireur.tex` l. 21 : « The instruments and their witnesses ») | *control* (`en/chapitres/07-synthese.tex` l. 72 ; 10 ; A) |
  | mutation synonyme | *synonym mutation* (`commun/notations.tex` l. 48 ; 00 à 06) | *synonymous mutation* (07, 09, 13) |
  | codon synonyme du zéro | *zero-synonym codon* (notations l. 42 ; 00 l. 69 ; 02 l. 12) | *synonymous codon of zero* (07 l. 18, 123, 428 ; 10 l. 20), *codon of zero* (13 l. 59) |
  | génome synonyme | *synonym genome* (résumé) | *synonymous genome* (09, 10) |
  | piste | *lead* (partout) | *track* (`en/resume.tex` l. 15 et 17, quatre fois) |
  | le juge | *his own decoder* (`en/resume.tex` l. 19) | *it* (10, « A judge redoes. It … ») |

  La même phrase française, « son témoin qui sait tomber », devient « its witness that can fail » à la fin de
  l'abstract (`en/resume.tex` l. 19) et « its control that can fall » dans la conclusion
  (`en/chapitres/13-discussion.tex` l. 132). Le lecteur anglais ne peut pas savoir que ce sont les mêmes
  choses ; la table des notations n'a pas de ligne pour le témoin ni pour la cassure.
- **Le correctif** : un seul mot par notion, partout.
  - Proposé : *control* (l'usage expérimental anglais ; *witness* est un calque) ; *synonymous mutation*,
    *synonymous genome* (l'usage de la biologie) ; *zero-synonym codon* ; *lead* ; *it* pour le juge, qui est
    un rôle.
  - Ajouter aux notations une ligne « témoin, cassure / control, break ».
  - Les remplacements sont mécaniques. Ils se vérifient par `parite_nombres.py`, qui doit redonner la parité, et
    par un comptage des mots, qui doit tomber à zéro pour les formes retirées.

**G2. Le Résumé français du tome anglais est composé à l'anglaise.**
- **Où** : `memoire/tome3/en/resume.tex`, bloc français, l. 27 à 37 ; page du Résumé du PDF anglais
  (`journaux/resume-fr-dans-pdf-en.txt`).
- **Le constat** : le bloc est recopié au caractère près du tome français, mais compilé sous `\anglaistrue`.
  `siunitx` y met donc le point décimal et le tiret de l'intervalle, et `\EF` y met l'unité anglaise. Le
  paragraphe imprime :
  - « 3.84 bits par poids », « 4.05–4.37 bits contre 3.84 », « 0.131 8 contre 0.264 0 », « 57.1 % », « 1.80 GB
    de moins » ;
  - et, dans la même phrase, « ×1,44 », « ×1,24 et ×2,00 », écrits en dur avec la virgule.

  Aucun nombre n'est faux, mais la page la plus lue du tome anglais mêle deux typographies dans une phrase
  française.
- **Le correctif** : ouvrir, dans `en/resume.tex`, juste après `\begin{otherlanguage}{french}`, un groupe
  `\sisetup{output-decimal-marker={,}, range-phrase={ à }, list-final-separator={ et }}`. Y écrire
  `\num{1.80}\,Go` au lieu de `\SI{1.80}{\Go}`. Puis vérifier la page par `pdftotext`. Le bloc anglais du tome
  français est écrit en clair et s'imprime juste : rien à y faire.

**G3. Deux tables engendrées des annexes ne viennent pas du commit.**
- **Où** :
  - `memoire/outils/tome3_annexes.py` l. 76 à 80 (`lignes_de`) et l. 140 (`stat().st_size`), qui lisent l'arbre
    de travail ;
  - leurs sorties : `memoire/tome3/annexes/outils-tome3.tex` l. 164 et l. 355, et
    `memoire/tome3/annexes/journaux-tome3.tex` (colonne « Volume (Mo) », l. 13 à 79).
- **Le constat** :
  - **L'annexe B** donne 124 lignes à `outils/mimetisme/humain/e4b_defauts.py`, et un total de 48 949 lignes. Le
    fichier commité en a 122 : les 124 sont celles d'une modification non commitée d'une autre session, présente
    dans l'arbre de travail principal (`git status` : ` M outils/mimetisme/humain/e4b_defauts.py`). Refait
    depuis le commit, le total est de 48 947.
  - **L'annexe C** donne la taille des dossiers de journaux telle qu'elle est sur le disque de l'arbre qui
    construit. Or le dépôt a `core.autocrlf=true` : la taille dépend des fins de ligne de la copie. Pour
    `mesures/genome/construction/codon/` :
    - la table commitée dit 2,47 Mo ;
    - un arbre en CRLF donne 2,53 Mo ;
    - les objets git, 2,43 Mo.

    Au total, 78,97 Mo commités contre 79,50 dans mon arbre.

  La règle « chaque chiffre vient d'un fichier commité » est donc tenue pour le texte, pas pour ces deux tables.
  Le même commit construit deux PDF différents selon la machine (12 lignes de texte, § 1.1).
- **Le correctif** :
  - dans `tome3_annexes.py`, compter les lignes sur `git show HEAD:<chemin>` et les tailles par
    `git ls-tree -r -l HEAD` ;
  - refuser de tourner si `git status --porcelain` signale un fichier suivi modifié parmi ceux qu'il compte ;
  - puis reconstruire les deux langues.

  C'est l'outil d'un autre rôle : je le rapporte, je n'y touche pas.

**G4. Une phrase devenue fausse reste sans barre : celle que le traducteur EN2 avait signalée deux fois.**
- **Où** : `memoire/tome3/fr/annexes/B-outils.tex` l. 10, et `en/annexes/B-outils.tex` l. 12 (l'« Il reste » de
  l'annexe B) ; la liste de la chaîne, fr l. 17 à 19 et en l. 19 à 21.
- **Le constat** : l'origine de l'annexe B dit encore « Il reste à mettre l'outil des annexes dans la cible
  `tome3` de `memoire/construire.sh` ». Il y est depuis `57db4ce`. La construction finale a barré la même phrase
  au paragraphe « L'outil des annexes », mais pas ici, alors que la note du traducteur EN2 nommait les deux
  endroits (« Annexe B, « Il reste » et § « L'outil des annexes » »). La liste des étapes de la chaîne, juste
  après, va des huit outils de données aux figures des spectres sans l'étape `tome3_annexes.py` que
  `construire.sh` exécute entre les deux.
- **Le correctif**, dans les deux langues :
  - barrer l'« Il reste » et dire ce qui a changé : « il y est depuis le 2026-10-29, commit `57db4ce` » ;
  - ajouter à la liste l'item « il engendre ensuite les tables des annexes B et C par
    `memoire/outils/tome3_annexes.py` (\cref{…}) » ;
  - recompiler.

## 4. Les mineurs

- **M1. Les calques de l'anglais.**
  - « gives back » pour « redonne / rend », 25 fois (02, 03…) : écrire *returns*, *recovers*, *reproduces*.
  - « before its judge » (`en/chapitres/06-mimetisme.tex` l. 15 et 21, l'« In brief » de 00) : écrire *under its
    judge*, *survives its judge*.
  - « its control that can fall » (13 l. 132) : écrire *a control that can fail*.
  - « a trifle makes it change quartet » (11, In brief).
  - « a judge that did not build it gives it again » (09, In brief).
  - « brought this reading down » (10 l. 345 ; A l. 131) : écrire *overturned*.
  - « another move than the recipe » (00, In brief).
  - « The answer of information theory » (01, In brief).
  - « the cell reads one like the other » (08, In brief).
  - « a published figure » pour « un chiffre publié » (C, origine), ambigu dans un tome de figures.

  Rien n'y est faux ; c'est la trace du mot à mot que la consigne voulait éviter. Une relecture de langue d'un
  seul tenant, après G1, suffit.
- **M2. Trois écritures du pour-cent dans le tome anglais.**
  - « 3.56\% », collé, aux 00 à 06 ;
  - « 80.8\,\% », avec l'espace fine française, environ 270 fois aux 07, 08 et 11 (61, 38, 169) ;
  - `\SI{…}{\percent}`, qui imprime une espace fine, partout ailleurs.

  En choisir une seule pour l'anglais.
- **M3. Le résumé dit « Restent : recoder les fichiers en v1.2 »** (`fr/resume.tex` l. 24 ; l. 39 pour l'abstract ;
  `en/resume.tex` l. 21 et 36). Les deux fichiers sont recodés et vérifiés (08, § « Les deux fichiers recodés »). Ce qui reste,
  c'est d'en faire les fichiers par défaut et d'effacer les v1.0, ce qui revient à Stone
  (13, § « Travaux futurs », point 1). Écrire « faire du v1.2 le format par défaut des fichiers de la machine
  (décision de Stone) ». Le titre du point 1 du 13 a la même ambiguïté.
- **M4. Le résumé dit que « les six pistes du mimétisme restent ouvertes, ou à la limite »** (`fr/resume.tex` l. 20 et
  35 ; `en/resume.tex` l. 17 et 32). Son juge
  dit P4 « ouvert, plutôt tombe » (13, tableau des verdicts). Ajouter « P4 plutôt du côté de tombe ».
- **M5. Le paragraphe « Le juge, en quatre phrases » (02 l. 309) en a cinq.** Il dit aussi la KL d'une position
  « nulle quand les deux lois sont égales, et sinon égale au surcoût moyen ». Avec la coupe à
  $\log p > -16$ et sans renormalisation, la somme peut être légèrement négative : $-5{,}6\cdot10^{-6}$ et
  $-2{,}3\cdot10^{-5}$ au minimum dans `comparer10-base-contre-recette.json`. Écrire « au terme de coupe près ».
  Au 11, préciser l'étendue de $k$ dans l'énoncé de Rényi (§ 2.3).
- **M6. Le 3,06 de la graine** (03 l. 104 ; résumé ; 13) n'est redonné que par une interpolation en log de
  l'erreur (3,061). Une interpolation linéaire en erreur entre (12, 4) et (10, 3) donne 3,066, soit 3,07. La
  source écrit « ≈ 3,06 » (`genome/genome.md` l. 41). Dire « en interpolant en log de l'erreur ». La conclusion
  ne bouge pas : 3,07 > 2,64.
- **M7. L'empreinte de 03 dans le commit `57db4ce`** est celle de la copie CRLF, pas celle de l'objet (§ 2). La
  note de reprise du correcteur le dit « vérifiée égale » : c'est vrai du contenu. Le dire pour qui voudra la
  refaire par `git show`.
- **M8. Les décimaux groupés.** `\num` groupe les décimales (« 0,131 8 », « 0.003 4 »), l'abstract écrit en
  clair « 0.1318 » : le même nombre s'imprime de deux façons dans un même tome. C'est la règle commune des
  trois tomes (`group-minimum-digits=4` dans le préambule commun), et la changer toucherait les Tomes I et II :
  à décider pour les trois à la fois.
- **M9. Le « Ce qui reste » de `REPRISE-figures.md`** dit « Aucun juge n'a relu le tome anglais » : à mettre à
  jour par ce jugement (fait dans ma note de reprise, pas dans ce fichier, qui n'est pas à moi).

## 5. Les répétitions (M10 du premier jugement) : où garder le récit, où renvoyer

Chaque chapitre doit pouvoir se lire seul, et une phrase de rappel se défend. Ce qui se répète, ce sont des
paragraphes entiers. Mêmes paragraphes dans les deux langues.

**1. Le motif croisé (×1,389 / ×0,715), trois fois.**
- **Garder le récit entier au 08**, `t3cod:sec:motif`, paragraphe « Ce que montre le motif croisé » (fr l. 416) :
  - le tableau Jb3 ;
  - J9, J10 et J11 ;
  - les seuils $e_{\text{soi}}$ et $S_j$ ;
  - la description qui n'est pas un mécanisme.

  C'est le chapitre du J1 et du format.
- **Au 10**, `t3jug:sec:r1` (fr l. 343) : garder la barre et l'histoire de l'erreur du juge, qui est le propos
  de ce chapitre, puis la liste « Ce que cela fixe, pour tout le tome », à laquelle l'introduction et les
  notations renvoient. Remplacer la phrase « A20 lu au motif de B20 … ($\times 0{,}851$ et $\times 0{,}882$) »
  par une proposition : « un même fichier lu avec les frontières de l'autre format change de vitesse
  (\cref{t3cod:sec:motif}) ».
- **Au 09**, paragraphe « Ce qui fait l'étage disque (réserve R1) » (fr l. 471) : retirer les deux premières
  phrases (l'histoire, les ×1,389 et ×0,715). Garder « Pour ce chapitre, cela change le mot, pas les verdicts »
  et la suite (B et R ont un motif rapide, $r(R/B)$ compare deux motifs rapides, ce disque, ce jour-là).
  Commencer par « Sur ce disque, l'écart suit le motif des requêtes de lecture (réserve R1,
  \cref{t3jug:sec:r1}) ».

**2. La KL 0,0262 attribuée à la mauvaise variante, quatre fois.**
- **Garder le récit de la correction au 07**, `t3syn:sec:frontiere`, seconde moitié de « Deux corrections,
  dites » (fr l. 120) : la barre, le journal `kl-synonyme-d1-juge.json` (« d1 », c'est-à-dire $\delta^* = 1$,
  $\lambda = 0$), la conséquence (la mesure B0 du cahier). C'est la synthèse qui avait mal attribué ; c'est elle
  qui corrige.
- **Au 02**, « Quelle variante a été jugée » (l. 321) : garder le fait mesuré, qui est celui de l'éclaireur (la
  passe juge $\lambda = 0$, $\delta^* = 1$, à +0,011 bit ; $\lambda = 1$ n'est jugée qu'à l'erreur de sortie),
  et la conclusion en gras. Retirer la citation barrée de la synthèse, et la remplacer par « la synthèse a dû
  corriger une attribution à $\lambda = 1$ (\cref{t3syn:sec:frontiere}) ».
- **Au 10** (l. 362) : la proposition suffit, garder telle quelle.
- **Au 13** (tableau des barres, l. 73) : garder, c'est le registre des barres.

**3. Les 64 codons pour vingt acides aminés, cinq fois (00, 02, 03, 05, 08 ; et la mutation synonyme au 09).**
- **Garder le récit entier à l'introduction**, `t3int:sec:genome` (l. 40) : le code dégénéré, Crick 1961 et
  1968, Freeland, et le tableau de l'analogie.
- **Au 08**, « En bref » (l. 23) : garder l'exemple concret (GGU, GGC, GGA, GGG pour la glycine), le seul du
  tome, dans le chapitre du codon.
- **Au 02**, « En bref » (l. 18) : remplacer les deux premières phrases par une seule, « Une mutation synonyme
  change un codon sans changer la protéine (\cref{t3int:sec:genome}) ».
- **Au 03**, « En bref » (l. 19) : garder l'image propre au chapitre (le cadre de lecture, le ribosome), mais
  retirer « 64 codons pour 20 acides aminés et l'arrêt ».
- **Au 05**, « Le parallèle biologique, comme image » (l. 25) : ne garder que la position bancale de Crick
  (1966), qui est neuve, et renvoyer à l'introduction pour le reste.
- **Au 09**, « En bref » (l. 18) : garder la phrase sur la mutation synonyme, qui est l'objet du chapitre.

À noter en passant : la définition de la KL est donnée trois fois (02, 07, notations). C'est voulu par G4 et
court ; elle se garde.

## 6. Le résumé et l'introduction, lus comme le premier lecteur

Je les ai lus avant de rouvrir les chapitres, puis vérifiés phrase par phrase contre eux.

**Ils disent vrai de tout le tome.**
- **Les trois synonymes qui gagnent** sont donnés avec leurs nombres : le zéro, la colonne, la mutation
  synonyme.
- **Ce qui tombe** est donné avec ses nombres : la graine, les motifs, la recette, la parenté, la garde, les
  spectres.
- **Le mode rapide** est dit comme il est : il ne tient pas en génération, ×0,94 et ×1,28 contre le v1.2.
- **Le juge et ses fenêtres neuves** sont décrits justement.
- **La réserve R1** est dite dans ses propres mots.
- **Les barres du tome**, rassemblées, sont fidèles au tableau du 13.

Tous les nombres du résumé sont refaits au § 2.1. L'introduction n'annonce rien de plus fort que ses chapitres :
- « divise par deux la KL » : 0,4991 ;
- « aucune des six pistes ne tient franchement » ;
- le gain du format « par le motif de ses requêtes de lecture ».

Elle tient aussi les conventions qu'elle pose :
- les figures sont appelées par leur numéro imprimé (G3 tenu) ;
- « la réserve R1 » partout où c'est la réserve : je n'en ai trouvé aucune autre écriture, légendes comprises ;
- la KL est posée au 02, avant son premier usage.

**Deux nuances, seulement dans le résumé** : « recoder les fichiers » (M3), et P4 (M4). Le premier lecteur du
tome anglais lira aussi un vocabulaire qui change à mi-chemin (G1).

## 7. Ce qui pourrait être faux

- **Je n'ai reconstruit que l'anglais.** Pour le PDF français commité, je m'appuie sur la construction finale
  (`REPRISE-redaction-construction.md`) et sur le premier juge. Son texte n'a pas été comparé, par moi, à une
  reconstruction. Mais il partage avec l'anglais les deux tables de G3, qui sont bilingues : il a donc les mêmes
  12 lignes engendrées hors du commit.
- **L'outil de parité voit les nombres, pas le sens.** Un « tient » rendu par « fails », une négation perdue, ne
  changent aucun nombre. Ce qui les couvre :
  - ma lecture d'un ou deux passages par chapitre (§ 1.3) ;
  - l'égalité des barres et des étiquettes.

  Ce n'est pas une relecture complète de 300 pages.
- **Les huit écarts « expliqués » de la parité** l'ont été par moi, en lisant chaque endroit. Un vrai écart qui
  aurait exactement la forme d'un écart expliqué (un `\{0,1\}` de plus, par exemple) passerait.
- **Le refait couvre les chiffres neufs ou déplacés depuis le premier jugement**, pas tous ceux du tome. Pour le
  reste, je m'appuie sur le tirage du premier juge (71 sur 5 357), avec la réserve qu'il disait lui-même. Le
  0,0314 de P3 est vérifié par sa citation, pas refait.
- **Le jugement de la langue est le mien**, pas celui d'un relecteur de langue maternelle anglaise. Les calques de
  M1 sont des exemples ; il y en a d'autres.
- **Les figures du mimétisme et les PNG** sont les mêmes fichiers dans les deux langues, avec leurs étiquettes
  françaises (réserve R5, dite). Je ne les ai pas vues page par page au rendu anglais.
- **G3 repose sur une inférence.** Je n'ai pas vu l'arbre de travail principal au moment de la construction
  finale. Les 124 lignes sont celles de la modification non commitée qui y est aujourd'hui, et les tailles
  commitées sont celles de cet arbre aujourd'hui (2,466 Mo pour `codon/`) : l'explication est la seule qui
  redonne les deux nombres.
- **Les répétitions sont affaire de jugement.** Le § 5 dit où je couperais, pas une règle.

## 8. Reproduire

Depuis la racine d'un arbre au commit jugé (Git Bash ; Python 3.13, bibliothèque standard ; MiKTeX 26.5 ;
poppler pour `pdftotext`) :

```
J=outils/genome/tome3/juge-final
bash memoire/construire.sh tome3-en                                   # 21 min ; en arrière-plan
python -I -X utf8 $J/parite_nombres.py memoire/tome3                  # --casser : 18 fichiers sur 18 tombent
python -I -X utf8 $J/parite_ef.py memoire/tome3/commun/notations.tex  # 1 écart relevé, le \crefrange du § 1.2
python -I -X utf8 $J/resumes.py memoire/tome3
python -I -X utf8 $J/refaire_neufs.py .                               # --casser : les 73 tombent
python -I -X utf8 $J/listing.py .                                     # --casser : tombe
python -I -X utf8 $J/typo_en.py memoire/tome3                         # relevé, sans verdict
pdftotext -enc UTF-8 memoire/tome3/en/troncons-tome3-en.pdf refait.txt   # puis diff contre le PDF commité
```
