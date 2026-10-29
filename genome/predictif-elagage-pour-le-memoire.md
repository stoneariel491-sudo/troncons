# Codage prédictif et élagage synaptique des poids MXFP4 : ce que le mémoire doit porter

Étude genome/predictif-elagage, 2026-10-16. Chercheur : sujet « predictif-elagage » de l'étude du
génome des poids (idees/biomimetisme-genome-des-poids.md, § 5 bis et 5 ter). Étiquettes :
**[mes.]** mesuré ici (outil et journal commités), **[calc.]** calculé, **[litt.]** littérature.
Outils : `outils/genome/predictif-elagage/` ; journaux et CSV : `mesures/genome/predictif-elagage/` ;
sources : `memoire/sources/genome-predictif-elagage.bib`.

## 0. D'où l'on part, où l'on va

- **Acquis au départ** : sur les 12 tenseurs d'experts de la frontière (gpt-oss-20b, couches 0, 8,
  16, 23 × gate, up, down ; 3 185 049 600 poids), le codage sans perte A_ctx lit **3,8431 bits par
  poids** ; la base de B (signe + 4 classes de magnitude) lit **2,6441 bits** pour **4,2920 %**
  d'erreur quadratique relative (ARCHITECTURE § 3.3, 07 § 4.2). Le contexte d'échelle κ (sous,
  égale, au-dessus de la médiane de la ligne) est déjà dans le format.
- **Ce que l'étude établit** :
  1. **les codons synonymes** : 13,7 % des poids valent ±0, et le signe d'un zéro est à pile ou face ;
     le fondre rend **0,137 bit par poids sans rien changer à la valeur d'aucun poids** [mes.] ;
  2. **le codage prédictif sans perte** au sens strict (prédire chaque code depuis ses voisins, son
     expert parent, la contrainte du maximum de bloc) ne retire presque rien ; un seul prédicteur
     passe le seuil : **la classe d'énergie de la colonne d'entrée** (+0,026 à 0,031 bit) [mes.] ;
  3. **le système sans perte en valeur** (zéro fondu + κ × colonne), codé par le rANS de l'étude 03
     et décodé exactement : **3,6844 bits par poids contre 3,8434** (−4,1 %) [mes.] ;
  4. **la métrique de la frontière est fausse pour juger une perte** : l'erreur globale de 4,2920 %
     est tenue à 91,5 % par un seul tenseur (blk.23.ffn_down) ; un remplissage inverse global
     l'exploite en vidant tout le reste (0,32 bit « à 4,29 % ») [mes.] ;
  5. **l'élagage par magnitude perd** contre la base (1,012 × son débit à erreur égale) ; ce qui gagne,
     c'est le **remplissage inverse** : des partitions de codes choisies par contexte d'échelle
     (2,019 bits, × 0,767), et surtout **l'élagage dépendant de l'activité**, partitions choisies par
     (échelle, activité de la colonne d'entrée mesurée sur des entrées réelles) : **1,695 bit
     (× 0,644)** à erreur de sortie prédite égale, 41 % des poids retirés [mes., idéal] ;
  6. **la mesure à la sortie des experts et la KL contre la référence f64 tranchent** (§ 5, § 6) :
     tout plan qui remplit à travers les échelles absolues (élagage par magnitude ou par activité,
     partitions par e, même à sensibilité hebbienne) perd en KL, de 3 à 5 fois la KL de la base,
     **même quand l'erreur moyenne à la sortie des experts égale celle de la base** (hebbien par e :
     5,70 % contre 5,57 %, KL 0,195 contre 0,064). Seuls les plans relatifs à la ligne tiennent :
     **partitions par κ, chaque tenseur à l'erreur de la base : 2,4079 bits réels (0,911 × la base),
     KL statistiquement égale (appariée +0,0066 ± 0,0053)** [mes.].
  7. ~~L'élagage dépendant de l'activité : 1,695 bit (× 0,644) à erreur égale.~~ Prédit seulement ;
     mesuré, il casse l'expert et la KL (0,271) ; barré le 2026-10-17.
- **Ce qui reste** : § 9.

## 1. Les codons synonymes du E2M1 (sans perte en valeur)

**Le fait** [mes., `histo-12-gptoss20b.npz`]. Loi des 16 codes sur les 12 tenseurs :
P(+0) = 0,06846, P(−0) = 0,06848 ; et plus largement P(+c) = P(−c) à 10⁻⁴ près pour chaque
magnitude. Par tenseur, P(+0) et P(−0) diffèrent de moins de 10⁻⁴ (de 0,059 à 0,098 chacun).

**Pourquoi** : le quantificateur qui a produit le MXFP4 de gpt-oss garde le signe de la valeur
d'origine même quand sa magnitude s'arrondit à zéro. Or E2M1 a deux codes pour zéro, 0b0000 et
0b1000 ; ggml les lit tous deux comme l'entier 0 (`kvalues_mxfp4`), la référence f64 comme +0 et
−0, qui ne changent aucune somme non nulle.

**Proposition (gain exact du fondu).** Soit V = v(C) la valeur d'un code C. Alors
H(C) = H(V) + H(C | V), et H(C | V) = P(V = 0) · H(signe | V = 0), puisque C est déterminé par V
partout ailleurs. *Démonstration* : H(C, V) = H(C) + H(V | C) = H(C) car V est fonction de C ; et
H(C, V) = H(V) + H(C | V). Sachant V ≠ 0, C est connu ; sachant V = 0, C ∈ {0, 8}. ∎
Calcul posé : P(V = 0) = 0,06846 + 0,06848 = 0,13694 ; H(signe | V = 0) = h(0,06846/0,13694) =
h(0,49993) = 1,0000 bit ; gain = **0,13694 bit par poids** [calc.]. Mesuré par l'entropie
conditionnelle (contexte κ, tables par tenseur) : 0,136939 [mes.] ; par le codec réel : **0,1370**
[mes.].

**Le parallèle biologique** : le code génétique a 64 codons pour 21 sens ; les codons synonymes
diffèrent souvent par leur troisième base, la position « bancale » de Crick (1966,
`genome-pe-crick1966wobble`), et une mutation qui passe de l'un à l'autre est silencieuse. Les deux
codes ±0 sont deux codons synonymes ; l'information qui les distingue n'a aucun phénotype. La
canonisation (tout −0 devient +0) avant le codage entropique est l'analogue d'un usage de codons
réduit à un seul codon par sens.

**Mesures réelles** (`taux_reel`, rANS de 03, comptabilité de l'arbitre, A_flux) :

| tenseurs | sans perte au bit | zéro fondu | gain | journal |
|---|---|---|---|---|
| 12 de la frontière (20b) | 3,8434 | **3,7064** | 0,1370 | `taux-reel-12-gptoss20b.json` |
| 72, toutes couches (20b) | 3,8509 | **3,7230** | 0,1280 | `taux-reel-toutes-gptoss20b.json` |
| 108, toutes couches (120b, 60,9 Go) | 3,8549 | **3,7292** | 0,1257 | `taux-reel-toutes-gptoss120b.json` |

Témoins : chaque flux décodé et comparé octet à octet, aucune voie hors de L ; chaque demi-octet
décodé rend la valeur d'origine (d = o, ou o = 8 et d = 0). Cassure (8 envoyé sur 1) : le témoin de
valeur tombe (`taux-reel-12-gptoss20b-casse.json`). La ligne « sans perte au bit » retrouve
exactement A_flux de l'arbitre (3,8434), second chemin du même codec.

**De bout en bout** : la référence f64 à poids reconstruits (crochet `alterer_expert`, sonde) rend,
pour le plan identité, des entrées .kld identiques octet pour octet à la référence (510 entrées) et
`juge kl` = 0 exactement (`kl/identite-2f-octets.json`) ; le plan zéro fondu donne des valeurs
identiques, donc la même sortie.

## 2. Le codage prédictif sans perte : ce que les voisins disent d'un code

**Cadre.** Pour un alphabet discret, « prédire puis coder l'écart » s'écrit exactement : coder le
code avec une loi conditionnée par un contexte que le décodeur connaît. Le gain est l'information
mutuelle I(C ; X | κ) = H(C | κ) − H(C | κ, X). Biais de l'estimateur par fréquences (tables par
tenseur) : (K_X − K_κ)(16 − 1)/(2 N_t ln 2) bit par symbole, N_t = 265 420 800 poids par tenseur.

**Seuil déclaré avant** : 0,015 bit par poids (coût d'en-tête d'un flux de plus, 0,40 % de 3,84 bits,
03 § 3.1).

**Mesuré** (`contextes.py`, `contextes-gptoss20b.json`, 12 tenseurs ; tables comprises) :

| prédicteur (en plus de κ) | H (bits/poids) | gain | verdict |
|---|---|---|---|
| aucun (κ seul) | 3,7923 | — | référence |
| δ exact (±2) | 3,7915 | 0,0007 | écarté |
| octet entier (paire de demi-octets du bloc) | 3,7885 | 0,0037 | dans A_ctx déjà |
| code de gauche | 3,7846 | 0,0076 | écarté |
| code du dessus (ligne précédente) | 3,7831 | 0,0091 | écarté |
| expert parent (même place, expert e − 1) | 3,7879 | 0,0043 | écarté |
| gauche × dessus (867 contextes) | 3,7922 | 0,0000 | écarté (tables) |
| contrainte du maximum de bloc | 3,7921 | 0,0001 | écarté |
| **classe de la colonne d'entrée (quartile)** | **3,7608** | **0,0314** | **retenu** |

Lecture :
- **les voisins ne prédisent presque rien** : un code MXFP4 est, sachant l'échelle de son bloc, un
  tirage presque indépendant ; ce que la littérature appelle la « dépendance spatiale » des poids est
  ici sous 0,01 bit ;
- **l'expert parent ne prédit rien (0,004)** : les experts d'une couche ne sont pas des copies
  mutées les uns des autres au niveau des codes (l'étude de la duplication le chiffre sur les
  valeurs) ;
- **chaque bloc contient au moins un grand code** (|E2M1| ≥ 2) : 0 bloc sur 99 532 800 en est privé ;
  la règle OCP (échelle = 2^(⌊log₂ max⌋ − 2)) est bien suivie, mais la contrainte ne vaut que
  10⁻⁴ bit : un bloc a presque toujours plusieurs grands codes ;
- **la colonne d'entrée porte une structure** : certaines colonnes ont, en moyenne sur toutes les
  lignes et tous les experts d'un tenseur, des poids plus grands relativement à l'échelle de leur
  bloc. Le rapport entre la colonne la plus énergique et la médiane va de 1,11 (blk.0 down) à 2,93
  (blk.23 gate) en racine d'énergie. Les entrées de gate et up sont l'état caché, dont certains
  canaux portent des activations aberrantes ; l'entraînement y a répondu par des poids de taille
  différente. C'est un fait d'entrée, partagé par les 32 experts : une carte de 2 bits par colonne
  et par tenseur (720 octets) suffit.

Témoins : contexte = le code lui-même → H = 0 (tient) ; contexte gauche permuté au hasard → gain
6,33·10⁻⁵ pour un biais attendu de 6,26·10⁻⁵ (tient, `contextes-temoin-corrige.json`).
~~Biais attendu (51 − 1)·15/(2 N ln 2) = 5,4·10⁻⁶ avec N poolé, témoin tombé.~~ Corrigé le
2026-10-16 : les tables sont par tenseur, le biais se calcule avec N_t et (51 − 3) paramètres
ajoutés ; avec l'ancienne formule (cassure du témoin corrigé), le témoin tombe bien.

**Le codec réel κ × colonne** (`taux_reel`, flux de demi-octets séparés par contexte, alphabet 16,
zéro fondu, carte et tables comptées) : **3,6844 bits par poids**, contre 3,7103 pour le même
découpage en κ seul (gain réel de la colonne 0,0259) et 3,7064 pour l'alphabet octet en κ.
Par tenseur, la colonne ne rend rien sur blk.23.ffn_down (3,6744 → 3,6741 : l'entrée de down est
la sortie d'un SwiGLU, sans canal aberrant) et l'essentiel sur gate et up.

## 3. L'élagage et la quantification prédictive bornée : le cadre débit-distorsion

**Le problème.** Remplacer chaque code c, dans un bloc d'échelle e, par une cellule s d'une
partition P_k des 16 codes ordonnés sur la droite réelle (−12 … −1, −0, +0, +1 … +12, en grandeurs
E2M1 doublées K), choisie selon un contexte k que le décodeur connaît, reconstruite par
ŵ = r_{k,s} · 2^(e − 128). Débit : H(s | k), une table par tenseur et par contexte. Distorsion : la
somme des (w − ŵ)².

**Lemme 1 (centre optimal).** Pour une cellule fixée, la reconstruction qui minimise
Σ_i 4^(e_i − 128) (K_i − r)² est le centre de gravité pondéré r* = Σ 4^(e_i) K_i / Σ 4^(e_i), et
l'erreur restante vaut C − B²/A avec A = Σ 4^(e_i), B = Σ 4^(e_i) K_i, C = Σ 4^(e_i) K_i².
*Démonstration* : la fonction est un trinôme en r, de dérivée 2(A r − B), nulle en B/A ; la valeur
au minimum est C − 2rB + r²A = C − B²/A. ∎ (Chou, Lookabaugh et Gray 1989 pour le cas vectoriel.)

**Lemme 2 (programmation dynamique exacte).** Avec un multiplicateur μ, le coût d'une partition en
intervalles est Σ_cellules [D_s/E + μ · n_s (−log₂ n_s / n_k)], somme de termes qui ne dépendent
chacun que de leur cellule. La meilleure partition des 16 positions s'obtient donc exactement par
la récurrence J(j) = min_{i < j} J(i) + c(i, j − 1), J(0) = 0, en 136 évaluations de cellule (au
lieu des 2¹⁵ partitions). C'est la segmentation d'histogramme de Muresan et Effros (2002) et de Wu
et Zhang (1993). ∎

**Proposition (remplissage inverse).** Un μ commun à tous les contextes réalise le minimum de la
distorsion totale sous contrainte de débit total : aux points où chaque contexte est sur sa courbe
D_k(R_k) convexe, la condition de Karush-Kuhn-Tucker est −∂D_k/∂R_k = μ pour tout k actif. Les
contextes de faible énergie (échelle e petite, colonne peu active) atteignent leur débit nul les
premiers : une seule cellule, tout le contexte reconstruit par son centre, presque zéro. C'est le
« reverse water-filling » de Cover et Thomas (2006, th. 10.3.3) transposé à une source discrète.
**L'élagage synaptique y apparaît comme le régime de débit nul du remplissage inverse** : on ne
choisit pas d'élaguer, on choisit un prix du bit, et les synapses qui ne le paient pas disparaissent.

**La métrique.** La première passe utilisait l'erreur globale de la frontière, Σ(w − ŵ)²/Σw² sur les
12 tenseurs. Part de l'énergie par tenseur [mes.] : blk.23.ffn_down 91,5 %, blk.16.ffn_down 8,0 %,
blk.8.ffn_down 0,40 %, les neuf autres ensemble 0,015 %. Un μ commun sous cette métrique vide les
neuf petits tenseurs : 0,32 bit « à 4,29 % » (`ecsq_e_metrique_globale`, pour mémoire), absurde.
**Métrique retenue : la moyenne sur les tenseurs de leur erreur relative propre** (chaque matrice
compte autant). La base y vaut **4,3367 %** (par tenseur de 4,05 à 4,80 %).

**Mesuré** (`debit_distorsion.py`, `debit-distorsion-12.json`, `.csv` ; entropies idéales + échelles
0,0375 + tables ; la base au même instrument : 2,6321, à comparer à 2,6441 réel, écart 0,46 %) :

| famille, à erreur moyenne par tenseur égale à la base (4,337 %) | bits/poids | rapport à la base | part élaguée |
|---|---|---|---|
| base (frontière, même instrument) | 2,632 | 1 | — |
| élagage par magnitude (le reste exact, zéro fondu) | 2,665 | 1,012 | — |
| partitions libres, contexte κ | 2,359 | 0,896 | — |
| partitions libres, δ de ligne borné à ±3 | 2,353 | 0,894 | — |
| zone morte seule, contexte e (élagage lagrangien) | 2,318 | 0,881 | — |
| **partitions libres, contexte e (remplissage inverse)** | **2,019** | **0,767** | 31 % |

**Pourquoi l'élagage par magnitude perd** : élaguer, c'est fondre les petites magnitudes dans le
symbole zéro ; le débit ne baisse que de l'entropie de ces symboles, tandis que tous les autres
codes gardent leurs 3 bits et plus. À erreur égale, il vaut mieux grossir *toutes* les cellules un
peu que d'en vider quelques-unes. Les petites magnitudes portent peu d'énergie mais peu de bits
aussi : 50 % des poids les plus petits d'un tenseur ne portent que 4,3 % de son énergie, et leur
retrait ne retire qu'environ la moitié des bits qu'il faudrait.

## 4. L'élagage dépendant de l'activité (sensibilité mesurée)

**Cadre.** Pour une matrice W et des entrées x de covariance Σ, E‖ΔW x‖² = tr(ΔW Σ ΔWᵀ) ≈
Σ_ij ΔW_ij² Σ_jj (approximation diagonale, exacte en moyenne si les erreurs de colonnes différentes
sont décorrélées). La sensibilité d'un poids est s_j = E[x_j²], l'activité de sa colonne. C'est le
critère de Wanda (|W_ij| · ‖X_j‖, Sun et al. 2023) et le terme diagonal d'OBD (LeCun et al. 1989).
Dans le cerveau en développement, l'élagage synaptique dépend de l'activité (Huttenlocher 1979) :
une synapse peu sollicitée est retirée la première.

**Le système** : les masses du lemme 1 deviennent A = Σ 4^(e) s_j ; le contexte devient (e, q), q le
quartile d'activité de la colonne dans l'expert (carte de 2 bits par colonne et par matrice
d'expert, 0,0007 bit par poids, comptée). Les s_j viennent des fenêtres 0 à 4 du corpus du lot R,
capturées par la référence f64 (entrées de gate et up : l'état normé routé vers l'expert ; entrée de
down : le SwiGLU calculé avec les poids exacts).

**Mesuré, erreur de sortie prédite** (`debit_sensibilite.py`, `plans/debit-sensibilite-12.json`) :

| famille | erreur de sortie prédite | bits/poids | rapport à la base (2,632) |
|---|---|---|---|
| base | 4,489 % | 2,632 | 1 |
| partitions par e (métrique des poids) | 4,494 % | 2,022 | 0,768 |
| partitions par e, masses pondérées par l'activité | 4,461 % | 2,005 | 0,762 |
| **partitions par (e, q)** | **4,487 %** | **1,695** | **0,644** |

À ce point, 40,9 % des poids sont fondus dans la cellule qui contient zéro.

## 5. Les entrées réelles, et l'erreur à la sortie des experts

**Les entrées** [mes.] : la référence f64 (trc-reference, chemin par lots) a tourné sur les 10
fenêtres de 512 jetons du corpus du lot R avec un crochet de capture (`sonde capture`,
`capture-entrees-20b.json`, 2 828 s) : pour les couches 0, 8, 16 et 23, l'état normé après
l'attention de chaque position routée vers chaque expert, 20 440 vecteurs de 2 880 par couche
(235,5 Mo en f32, hors dépôt). Calibration des plans qui lisent les activations : fenêtres 0 à 4 ;
évaluation : fenêtres 5 à 9.

**La mesure** (`sortie_experts.py`) : pour chaque expert, sortie exacte y = Wd·swiglu(Wg x + bg,
Wu x + bu) + bd et sortie reconstruite ŷ (les trois matrices du plan), erreurs relatives sommées sur
les experts (pondération par les jetons) puis moyennées sur les quatre couches.
Témoins : plans identité et zéro fondu, erreur nulle exactement (tient).

| plan | bits réels | gate | up | down seul | **expert entier** | rapport à la base |
|---|---|---|---|---|---|---|
| base (frontière) | 2,6444 | 1,16 % | 2,52 % | 2,72 % | **5,57 %** | 1 |
| partitions par κ | **2,3743** | 1,12 % | 2,70 % | 2,37 % | **5,48 %** | 0,98 |
| zone morte par e | 2,3283 | 1,44 % | 2,15 % | 2,51 % | 34,8 % | 6,2 |
| partitions par e (poids) | 2,0178 | 1,03 % | 2,65 % | 2,38 % | 22,0 % | 4,0 |
| partitions par δ de ligne (±3) | 2,353 (idéal) | 1,14 % | 2,67 % | 2,42 % | 5,48 % | 0,98 |
| **partitions par e, masses hebbiennes** | **2,1815** | 0,92 % | 2,38 % | 2,45 % | **5,70 %** | 1,02 |
| partitions par (e, ligne, colonne), hebbiennes | 1,7556 | 2,36 % | 4,30 % | 6,41 % | 9,23 % | 1,66 |
| partitions par (e, activité de colonne) | 1,6942 | — | — | — | (KL 0,271, § 6) | — |

Par couche, erreur d'expert (0 / 8 / 16 / 23) : base 5,1 / 7,6 / 6,7 / 2,9 % ; κ 6,1 / 7,6 / 6,5 /
1,8 % ; hebbien par e 5,1 / 8,3 / 7,1 / 2,3 % ; hebbien (e, ligne, colonne) 6,4 / 17,8 / 9,5 /
3,2 % (`sortie-experts-12.json`, `sortie-experts-12-hebb.json`, synthèse `resume-12.csv`).

(bits réels : `taux_plan`, décodage exact ; la base y donne 2,6444 contre 2,6441 publié par
l'arbitre, second chemin.)

**Ce que la mesure a révélé.** Les plans qui remplissent à travers les échelles absolues gardent
chaque matrice sous 3 % d'erreur relative, et l'expert entier devient faux à 22 à 35 %. La cause :
la quantité que mesure l'erreur relative d'une matrice n'est pas celle qui compte. Une ligne i de
gate ou de up agit sur la sortie à travers la colonne i de down ; l'entraînement répartit librement
l'échelle entre les deux (le chemin up a une symétrie de réétalonnage, u_i → c·u_i et Wd[:, i] →
Wd[:, i]/c ne changent presque rien), si bien qu'une ligne de petite échelle dans gate peut peser
lourd en sortie. Le remplissage inverse par matrice vide précisément ces lignes.

**La sensibilité hebbienne** (`histo_hebb.py`) répond au premier ordre : E‖Δy‖² ≈ Σ ΔW_ij² r_i s_j,
avec s_j l'activité de l'entrée (présynaptique) et r_i = ‖Wd[:, i]‖² E[(∂a_i/∂g_i)²] (ou ∂u_i)
l'influence de la sortie (postsynaptique) ; le poids d'une synapse est leur produit, le produit de
Hebb.

## 5 bis. L'élagage hebbien : ce qui tient, ce qui sur-ajuste

- **Masses hebbiennes, contexte e seul** (aucune carte envoyée ; r_i et s_j ne servent qu'au
  codeur, pour choisir les partitions et les centres) : **2,1815 bits réels, erreur d'expert 5,70 %**
  contre 5,57 % pour la base à 2,6444 : **0,825 × les bits pour la même erreur à 2 % près**. Le même
  remplissage inverse sans la sensibilité hebbienne cassait l'expert (22 %) : c'est bien la symétrie
  d'échelle gate/up ↔ down qui le cassait, et l'influence postsynaptique qui la répare.
- **Avec cartes de lignes et de colonnes** (16 classes, 9 273 cellules) : prédit 4,33 %, mesuré
  9,23 %, la couche 8 à 17,8 %. La prédiction ne tient pas : les quartiles de r_i et s_j sont
  estimés sur ~320 entrées par expert (fenêtres 0 à 4) et la factorisation E[(∂a/∂g)² x²] ≈
  E[(∂a/∂g)²] E[x²] néglige leur corrélation ; un plan qui donne zéro bit aux classes jugées
  inactives paie au prix fort toute erreur d'estimation. Sur-ajustement mesuré, pas supposé.
- Variante relative à la ligne (δ × ligne × colonne) : 1,9619 bits réels, KL 0,091, appariée
  +0,027 ± 0,004 contre la base (`kl/comparer-base-hebb_d_lc-f5-9.json`) : perd.
- **Hebbien par e, KL** : 0,195 ± 0,009, appariée +0,131 ± 0,007, premier choix −20,8 points
  (`kl/comparer-base-hebb_e-f5-9.json`). À erreur d'expert moyenne égale à la base, trois fois sa
  KL. **L'erreur relative moyenne à la sortie d'un expert, pondérée par ‖y‖², ne suffit pas à
  juger** : elle est tenue par les jetons et les dimensions de grande sortie ; le remplissage inverse
  à travers les échelles concentre l'erreur sur ce qui est petit (blocs et lignes de petite échelle,
  23 % des poids fondus dans zéro), que la norme RMS des couches suivantes ramène à l'échelle et que
  la KL voit. Leçon : à la sortie, il faudrait juger l'erreur relative **par jeton** (ou la KL
  directement), pas l'énergie totale.

## 6. La KL contre la référence f64

Fenêtres 5 à 9 (1 275 positions notées), seules les 12 matrices de la frontière altérées (4 couches
sur 24), sonde `alterer` puis `juge kl` (l'instrument du lot R) contre la tranche de la référence
(`kl_tranche.py`, empreinte dans `kl/tranche-ref-f5-9.json`). Témoin de la chaîne : plan identité,
entrées .kld identiques octet pour octet à la référence, KL = 0 exactement.

| plan | bits réels | KL moyenne | ± | médiane | 99e centile | même premier choix |
|---|---|---|---|---|---|---|
| base (frontière) | 2,6444 | 0,0636 | 0,0050 | 0,0227 | 0,777 | 81,6 % |
| hebbien par e | 2,1815 | 0,195 | 0,009 | 0,075 | 1,54 | 60,8 % |
| hebbien (e, ligne, colonne) | 1,7556 | 0,192 | 0,008 | — | — | 59,4 % |
| hebbien (δ, ligne, colonne) | 1,9619 | 0,091 | 0,005 | — | — | 73,4 % |
| partitions par e (poids) | 2,0178 | 0,309 | 0,011 | 0,209 | 1,83 | 58,5 % |
| partitions par (e, activité de colonne) | 1,6942 | 0,271 | 0,009 | 0,188 | 1,51 | 57,1 % |
| partitions par κ (erreur moyenne égale) | 2,3743 | 0,0804 | 0,0063 | 0,0263 | 1,10 | 78,4 % |
| **partitions par κ, chaque tenseur à l'erreur de la base** | **2,4079** | **0,0702** | 0,0059 | 0,0235 | 0,911 | 79,5 % |

**Comparaison appariée** (`juge comparer`, mêmes 1 275 positions, même vérité) : partitions par κ
contre base, KL plus haute de **0,0167 ± 0,0049** (3,4 σ), premier choix plus bas de 3,2 ± 1,0
points (`kl/comparer-base-kappa-f5-9.json`). **À erreur moyenne égale, le plan κ ne vaut pas la base
en KL** : il déplace l'erreur vers la couche 0 (6,1 % d'erreur d'expert contre 5,1 %), et une erreur
tôt dans le réseau pèse plus dans la KL. D'où le plan « chaque tenseur à l'erreur de la base »
(`plans.py --par-tenseur`, un μ par tenseur : domination tenseur par tenseur), 2,4079 bits réels
(0,911 × la base). Appariée contre la base : KL plus haute de **0,0066 ± 0,0053** (1,2 σ), premier
choix plus bas de 2,1 ± 1,1 points (`kl/comparer-base-ecsq_kappa_t-f5-9.json`) : **statistiquement
égal à la base** (règle du lot R : d̄ ≤ 2σ et ē ≥ −2σ, tiennent), littéralement un peu au-dessus.
**C'est le point avec perte que l'étude retient : 9 % de bits en moins que la base de la frontière,
à KL égale dans le bruit de la mesure.** Lecture prudente : la différence appariée centrale reste
positive ; avec plus de positions elle pourrait devenir significative.

La KL tranche dans le même sens que la sortie des experts : les plans qui cassent l'expert cassent
le modèle, cinq fois la KL de la base.

## 7. Ce qui pourrait être faux

- Les débits avec perte sont des entropies idéales ; l'écart du codec réel mesuré sur la base est de
  0,46 % ; il peut être plus grand pour des tables à beaucoup de contextes (2 077 cellules en e,
  3 808 en (e, q)) et des cellules rares.
- L'approximation diagonale de la sensibilité néglige les corrélations entre colonnes d'entrée ; la
  mesure exacte à la sortie (§ 5) la juge.
- 10 fenêtres de 512 jetons d'un seul corpus ; ~640 entrées par expert et par couche, ~320 pour
  calibrer : les quartiles d'activité d'un expert peu routé sont bruités.
- La KL est mesurée en n'altérant que 4 couches sur 24 (les 12 tenseurs de la frontière).
- Le gain des codons synonymes suppose que tout moteur lise ±0 comme 0 : vrai de ggml (table
  entière) et de la référence ; à vérifier dans les noyaux de troncons (lot K) avant d'activer la
  canonisation dans le codeur.

## 8. Recettes (ce qui a marché, ce qui a échoué, et pourquoi)

- Marche : canoniser les codons synonymes avant le codage entropique (0,13 bit, exact en valeur).
- Marche : contexte de colonne d'entrée (0,026 bit réel) ; ne marche pas : voisins, expert parent,
  contrainte du maximum de bloc (sous 0,01 bit).
- Échoue : élagage par magnitude (1,012 × la base à erreur égale des poids).
- Échoue à la KL : tout remplissage inverse à travers les échelles absolues (partitions par e,
  zone morte, élagage par activité de colonne, sensibilité hebbienne, cartes de lignes et colonnes) :
  KL de 0,09 à 0,31 contre 0,064 ; ils « gagnent » 20 à 36 % de bits sur les métriques de poids.
- Marche : partitions par κ (relatives à la ligne), un μ par tenseur pour qu'aucun tenseur ne soit
  plus abîmé que par la base : 0,911 × les bits, KL égale dans le bruit.
- Piège : l'erreur moyenne à la sortie d'un expert (énergie) ne prédit pas la KL ; juger par jeton
  ou par la KL.
- Piège : une moyenne d'erreurs par tenseur laisse l'optimiseur charger la couche 0 (KL +0,017) ;
  contraindre tenseur par tenseur.
- Piège : une métrique d'erreur globale sur des tenseurs d'énergies très différentes se laisse
  exploiter par tout optimiseur ; normaliser par tenseur.
- Piège : une KL calculée en renormalisant les log-probabilités d'un .kld donne 4,5·10⁻³ pour deux
  sorties identiques au bit ; passer par `juge kl`.
- Piège : PowerShell 5.1 (Get-Content/Set-Content, redirection `>`) abîme l'UTF-8 et ajoute des BOM.

- La KL est mesurée sur 1 275 positions d'un seul corpus ; l'avantage de 9 % du plan κ dominé est
  à KL statistiquement égale, pas meilleure (différence centrale +0,0066).
- Les plans avec perte sont mesurés sur 4 couches altérées sur 24 ; l'effet sur les 24 n'est pas
  mesuré (la KL croîtrait, pour la base comme pour le plan).

## 9. Ce qui reste

- Les noyaux de carte : décodeur à table par (κ, colonne) ou par (e, q), et la reconstruction par
  table de centres (4 à 16 registres) ; branchement dans le codeur trc-codeur.
- La quantification avec retour d'erreur (GPTQ, « codage prédictif en boucle fermée ») sur
  l'alphabet des cellules, avec la hessienne complète des entrées réelles ; et un critère de
  sensibilité jugé par jeton (ou appris contre la KL), puisque l'énergie moyenne a trompé.
- Le plan κ dominé + colonne + zéro fondu sur les 24 couches, et sa KL ; puis gpt-oss-120b.
- La KL sur les 24 couches, et sur gpt-oss-120b.
