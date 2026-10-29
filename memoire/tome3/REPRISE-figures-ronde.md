# Reprise : figures du Tome III, lot « ronde » (ch. 1 à 4 et 7)

Flux court du 2026-10-27 (inventaire : `memoire/tome3/INVENTAIRE-figures.md` § 5). Style télégraphique.

## Conventions retenues (décidées ici)

- Un fichier par équipe : `memoire/figures/tome3/{eclaireur,genome,duplication,synthese}-figures.tex`,
  gardé par `\ifdefined` ; styles préfixés `ecl`, `gen`, `dup`, `synth`.
- Pour chaque figure : `\Graphe<Lot><Nom>` (le dessin) et `\Legende<Lot><Nom>` (la légende complète :
  protocole, ce que la figure ne montre pas, `\sourcefig{}`). Le chapitre écrit
  `\begin{figure}\centering\Graphe…\caption[titre court]{\Legende…}\end{figure}`.
- **Aucun chiffre recopié** : chaque nombre d'une légende ou d'une annotation vient de
  `donnees/<lot>-nombres.csv` (cle, valeur, source), écrit par le script ; lu au chargement par
  `\pgfplotstableread`, imprimé par `\eclNombre[format]{cle}` (séparateur décimal de la langue) ou
  `\eclEntier{cle}` ; `\eclVal{cle}` donne la valeur brute pour une coordonnée. Une clé inconnue arrête la
  compilation. Même schéma pour `gen`, `dup`, `synth`.
- Pilote : `memoire/essai/pilote-tome3-ronde.tex` (ignoré par git) ; `\PiloteFigure{Macro}{numéro}` saute
  une figure pas encore définie. PDF : `memoire/essai/pilote-tome3-ronde.pdf` (FR) et
  `pilote-tome3-ronde-en.pdf` (EN).
- `outils/genome/synthese/frontiere.py` prend `--sortie DOSSIER` (ajout rétrocompatible) ; la passe
  `--k10` est écrite sous `mesures/genome/construction/synthese/k10/` ; les fichiers à 3 fenêtres sont
  inchangés (sha256 vérifiées avant et après). Commit `ef7919a`.

## Fait

- III-1.1 `\GrapheEclBloc` : schéma TikZ du bloc MXFP4 (17 octets, zoom E8M0 et octet qs[9], droite des
  16 codes E2M1, ±0 encadrés). Valeurs en fractions (½, 3/2) : neutres pour la langue.
- III-1.2 `\GrapheEclBorne` : courbe `uniforme_precis` (40 points, 25 convergés, marques creuses pour les
  15 autres), frontière 2,6441 (rANS réel, `zero-temoin-sans-drapeau.json`), même base sur code
  canonique 2,5965 (`zero-canonique.json`), deux cordes : ≤ 2,17 bits à 4,29 % (−0,48 bit), ≤ 1,84 %
  à 2,6441 bits (×0,43). Les cordes sont des bornes par partage du temps (dit en légende).
- III-2.1 `\GrapheEclZeros` : coût du signe des zéros par tenseur, 20b et 120b, barres gate/up/down
  par couche, moyenne du modèle en tirets, H(signe | zéro) minimal par tenseur en encart.

- III-7.1 `\GrapheSynthFrontiere` : plan bits × rapport de KL (log) des 12 points jugés à la KL (P1, P2-10,
  P3 ; forme = protocole, remplissage = verdict lu dans la colonne `verdict`), flèches « promesse » (rapport 1
  à erreur intermédiaire égale) vers la KL rendue pour les 6 perdants ; bande des 7 points sans KL sur l'axe
  des bits ; à droite l'axe sans perte en haltères par tenseur (F1 → codon → colonne, colonne pleine si gain
  ≥ 0,015 bit : 2 tenseurs, couche 0). S* pris de K10 (P2-10), le point P2 à 3 fenêtres n'est pas tracé.
  λ = 1 reste un point sans KL (R3 : rien du protocole à 768 experts).
- III-7.2 `\GrapheSynthErreurKL` : nuage log-log, diagonale, zone y < 1, bande d'abscisse 0,75 à 1,02 ;
  S* à 3 fenêtres creux et barré (`\barre`), flèche vers le point K10 (R4).
- III-7.3 `\GrapheSynthDeuxParts` : 2 550 positions, une teinte par fenêtre, densités marginales en log10,
  médianes en pointillés, encart : médiane ÷ 2,3, 1 % des positions porte 31 % / 38 % de la moyenne.
  Une KL négative (−6,9e-6) portée au plancher 1e-5, dit en légende.
- III-7.4 `\GrapheSynthColonnes` : énergie et erreur par colonne (blk.8 down, expert 16, le seul tenseur en
  CSV), rapportées à leur moyenne ; colonne 1011 : ×144, ×334, base ×14, S* ×1,05 ; morceau 960-1023 ×8,9.

Décisions : les étiquettes des points se placent à la main par leurs clés (pgfplotstable ne lit pas les
guillemets d'un CSV) ; les sources de `*-nombres.csv` n'ont plus de virgule (remplacée par « ; »).

- III-3.4 `\GrapheGenGauss` : erreur contre débit des sept formes (l = 12 et 16) contre 2^(−2R), écart en
  dB en dessous (recalculé et comparé au journal à 2e-3 dB) ; à droite, la fenêtre l = 8 à 16 à 2 bits et le
  témoin T1. Les variantes (mélangeur bon marché, Lloyd, q = 6, 10) tombent sur le point l = 12 : dites en
  légende, non tracées. Corrigé en route : la table du balayage n'est PAS apprise (lloyd = 0, quantiles).
- III-3.6 `\GrapheGenCourbes` : 12 panneaux (couches × rôles), brut et tourné, losange de la base, flèche du
  gain à erreur égale (0,20 à 0,60 bit, 0,319 en moyenne) ; couche 8 down : le brut n'atteint pas la base.
- III-4.2 `\GrapheDupParente` : 880 scores en essaims déterministes (rangés par score, sans hasard) par
  couche et par enfant, trois genres ; hasard 0,0016 et témoin planté 0,2075 (retrouvé 0,2077, couche 12).
  « voisine » et « même indice » = couche précédente (vérifié dans `cand_couche`).
- III-4.8 `\GrapheDupArbre` : TikZ pur (lecture des CSV par `\pgfplotstablegetelem`), épaisseur et bleu
  selon s/s_max, disques selon le degré, rouges si degré ≥ 3 ; fidélité dans l'encart et la légende
  (30,9 % ; Spearman 0,61 ; témoin 0,11) ; « une ombre partielle », « pas une généalogie ».

Régénération : les quatre scripts relancés redonnent leurs CSV au bit (vérifié par `git status`).
Pilote : `memoire/essai/pilote-tome3-ronde.pdf` (FR, 14 pages) et `pilote-tome3-ronde-en.pdf` (EN),
sans erreur ni boîte trop pleine.

## Reste (pour le juge, puis le second flux)

- Le juge : refaire chaque `*-nombres.csv` par son propre chemin ; relire les étiquettes posées à la main
  dans III-7.1 (clés `p3-*`, `s-*`) ; vérifier les deux classes « gagne » de III-7.1 (λ = 0 gagne en KL à
  +0,011 bit ; partitions κ par tenseur « égale par la règle » mais classée gagne par sa colonne `verdict`).
- III-7.4 : les autres tenseurs (calcul neuf, état C) et les classes de colonne de blk.0 gate.
- III-4.8 : l'amas 5-15-17-25-31 se chevauche dans le plan ; un encart agrandi serait plus lisible.
- III-7.3 : rien sur les bascules par position (aucune colonne de routage dans les CSV de l'éclaireur).
- Les légendes n'ont pas de `\cite` (les .bib du génome ne sont pas chargés par le préambule commun) :
  le rédacteur les ajoute au chapitre (OCP MX v1.0, llama.cpp, Blahut 1972, Kruskal 1956, Shannon 1959).

## Pièges

- L'outil d'écriture refuse le dépôt (worktree) : écrire dans le répertoire temporaire puis `cp`.
- Jamais de LaTeX par heredoc ni `python -` en heredoc : les `\\` sont mangés (vu : `\\EF` devenu
  `\EF` perdu). Contrôle : un petit script cherche « \\\\ suivi d'une lettre ».
- `\pgfmathprintnumber[fixed, precision=4]` retire les zéros finaux (6,392 au lieu de 6,3920) :
  ajouter `fixed zerofill`.
- Dans un axe logarithmique, ne pas tracer de flèche avec `++(…)` relatif : passer par des
  `\coordinate` nommées.
- Un nom de style contenant « - » (`synth P2-10`) se lit comme une flèche : « Unknown arrow tip kind ».
- `groupplot` décale les panneaux quand leurs étiquettes d'axe n'ont pas la même largeur : deux `axis`
  en `scale only axis`, le second ancré au `south west` du premier.
- `\matrix` dans une macro : esperluettes refusées ; une ligne de légende en `\node` avec des `\tikz` en ligne.
- Pilote complet : plus de 2 minutes de compilation ; lancer avec un délai de 10 minutes.
