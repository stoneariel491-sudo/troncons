# Le génome des poids : de la graine au brin lu par codons

*Sujet « genome » de l'étude biomimétique de troncons (idees/biomimetisme-genome-des-poids.md § 5 ter),
2026-10-16. Processeur seul (la consigne ne donnait pas la carte). Tout chiffre ci-dessous vient d'un
fichier commité sous `mesures/genome/genome/`, produit par un outil commité sous `outils/genome/recette/`.*

---

## 0. En bref

**La consigne de Stone** : « le but est de concevoir un systeme fonctionnel et si il ne voye rien de
convaincaint vers l'ADN au terme ils recherche le moyen biomimétique le plus prométeur jusqu'à
trouver ».

**Ce qui est trouvé, conçu, construit et mesuré sur gpt-oss-20b** : un système, **S\***, qui **bat la
frontière** à la fois en erreur sur les poids et, ce qui compte, en **fidélité de la sortie des experts
sur des entrées réelles**.

- **Le mécanisme** : chaque rangée d'une matrice d'expert est stockée comme un **brin de bits** ; une
  fenêtre de 12 bits glisse le long du brin, avance de `kb` bits à chaque pas et rend `v` poids par une
  **table de 256 valeurs dégénérée** (le « code génétique » du tenseur, appris sur ses poids). C'est la
  lecture d'un ARN par le ribosome, codon après codon, transposée bit pour bit. Le brin qui reproduit
  le mieux une rangée se trouve exactement par l'algorithme de Viterbi. Avant le codage, chaque rangée
  passe par une **rotation de Hadamard** par morceaux de 64 (l'information de chaque poids répartie sur
  64 positions, comme dans une mémoire holographique) ; les bits se répartissent entre rangées ; le
  Viterbi est pondéré par l'énergie des entrées réelles ; et les **3 poids les plus grands de chaque
  rangée restent exacts, à part** (0,1 %), comme le vivant garde certains gènes hors du brassage.
- **En erreur sur les poids (critère W, déclaré avant)** : le brin seul lit **0,20 à 0,60 bit de moins
  par poids que la base de B** sur chacun des 12 tenseurs (7,7 à 22,4 %), **0,319 bit en moyenne**
  (2,32 bits au lieu de 2,64), 99,5 millions de poids, toutes les côtes du format comptées ; 12 sur 12.
- **Mais l'erreur sur les poids trompe** : au même point, l'erreur de **sortie** du brin seul est plus
  grande que celle de la base (couche 0, expert 0 : 7,63 % contre 6,77 %) ; même à 2,64 bits, le brin
  seul perd sur 4 experts sur 6 (non pondéré) et sur 1 sur 5 (pondéré) : les critères O et F, déclarés
  avant, **tombent**. Le diagnostic,
  mesuré : la table écrête les **colonnes massives** (une colonne ×144 l'énergie moyenne reçoit ×334
  l'erreur moyenne), et ces colonnes lisent justement les entrées qui pèsent.
- **S\* (déclaré avant sa passe) tient** : sur 8 experts entiers (couches 0, 8, 16, 23), à 2,64 bits,
  l'erreur de sortie de S\* est sous celle de la base **8 fois sur 8** (rapport moyen 0,747) ; à erreur
  de sortie égale, S\* lit **2,09 à 2,58 bits, 2,36 en moyenne, contre 2,64** : **0,28 bit de moins**
  (10,8 %), donc ×1,12 jeton par seconde au toit du disque pour les experts lus au niveau 0.
- **La graine seule (SeedLM écrit de zéro) ne bat pas la frontière** (≈ 3,06 bits à l'erreur de la
  base) ; la théorie (loi Bêta du meilleur de 2^16 sous-espaces aléatoires) le prédisait avant la mesure
  et dit pourquoi : un livre de codes aléatoire de dimension 8 à 16 est trop court. Le brin lu par codons
  est la **même idée** (un livre de codes pseudo-aléatoire indexé par des bits) portée à une dimension
  illimitée et rendue cherchable par la programmation dynamique. Les **motifs partagés** (dictionnaires
  communs aux experts, combinés) ne la battent pas non plus (2,90 bits).
- **Où est le bruit, où est la structure** : après la rotation, les rangées sont gaussiennes (kurtosis
  3,0 ; erreur à 2 bits 0,0739 contre 0,0731 sur une gaussienne vraie) : aucune recette « courte » ne
  les engendre. Le gain vient (a) du **pavage** de l'espace par le treillis, que la base scalaire n'a pas
  (0,14 à 0,18 bit), (b) de la **dispersion des énergies** de rangée et de colonne (structure du second
  ordre : 5 % des directions portent 23 à 68 % de l'énergie), que la base ignore.
- **La transcription** coûte 15 opérations par poids (le quart du budget de 62 à 2,32 bits) et va, sur
  le processeur, aussi vite que la déquantification MXFP4 du même expert.
- **Sans perte**, aucune recette ne bat 3,84 (lemme 3 ; recette + complément exact : 4,05 à 4,37).

Ce document dit ce qui était acquis, ce qui est conçu, construit et mesuré, et ce qui reste (§ 9).

---

## D'où on part, où on va

**Acquis au départ** (fichiers commités) :
- Sans perte : **3,8431 bits par poids** (A_ctx, F1, `decisions/journaux/arbitre/decoupe-gptoss20b.json`).
- Base seule de B : **2,6441 bits par poids** à **4,2920 %** d'erreur quadratique relative (07 § 4.2,
  F1 S4), sur les 12 tenseurs de F1 (couches 0, 8, 16, 23 × gate, up, down de gpt-oss-20b).
- Les codes MXFP4 sachant l'échelle de leur bloc sont presque indépendants (03 § 1.6 : le code voisin
  n'apporte que 0,005 bit) : aucune recette sans perte ne peut descendre sous 3,84 sans une structure
  que ce contexte ne voit pas.
- La machine : le disque est l'étage le plus lent (2,82 Go/s, 01) ; la carte a ≈ 214 opérations libres
  par octet compressé (01 ; le Tome II l'a corrigé à 926 au débit du disque, m12).

**Établi ici** : § 0. **Ce qui reste** : § 9.

---

## 1. La question et son juge

Le gain se lit dans le théorème du toit du mémoire : la vitesse maximale vaut le débit du disque divisé
par les octets lus par jeton. Une recette « marche » si elle lit **moins de bits par poids sur le disque
à erreur égale**. Les seuils sont dans `mesures/genome/genome/00-seuils-declares.md`, commités avant
toute mesure d'une recette (commit `e777d6d`, puis la précision de l'échantillon, `2698ccd`, avant la
première passe).

**Le critère W** : sur l'échantillon (experts 0, 8, 16, 24 de chacun des 12 tenseurs ; une rangée sur
quatre, 720 rangées entières par expert, 34 560 rangées, 99,5 millions de poids), à l'erreur relative de
la base **mesurée sur les mêmes rangées**, la recette lit moins de bits que la frontière F1 du même
tenseur, **sur chacun des 12 tenseurs** (une recette sans effet passerait les 12 avec la probabilité
2⁻¹² ≈ 2,4·10⁻⁴), et en global.

**L'erreur** : e = Σ (w − ŵ)² / Σ w², dans le domaine réel des poids (échelle E8M0 comprise), cumulée
sur les rangées du tenseur. C'est la mesure de la frontière (07 § 4.2).

---

## 2. La graine : la recette littérale, et pourquoi elle ne peut pas suffire

### 2.1 Le mécanisme (écrit de zéro)

Un bloc de C poids w ∈ ℝ^C est approché par ŵ = U(g) · t, où U(g) est une matrice C × P tirée d'un
générateur pseudo-aléatoire par une graine g de K bits, et t ∈ ℝ^P des coefficients quantifiés (entiers
de 4 bits en complément à deux, un exposant partagé de 4 bits). L'encodeur essaie les 2^K graines,
projette w sur chaque sous-espace (pseudo-inverse précalculée par Cholesky), quantifie, garde la
meilleure. Débit : (K + 4 + 4P)/C bits par poids. C'est la forme du problème de SeedLM (Shafipour et
al., arXiv 2410.10714v2) ; rien n'en est copié. Deux générateurs : un LFSR de Galois de 16 bits
(x^16 + x^14 + x^13 + x^11 + 1, période 65 535 vérifiée par le témoin `periode_maximale`) et un
mélangeur de bits compteur (un élément = un mélange (graine, rang)).

Témoin T3 : un bloc engendré exactement par une graine et des coefficients quantifiables se retrouve à
erreur nulle (`bloc_engendre_retrouve_exactement`, deux chemins du codeur).

### 2.2 Ce que la théorie permet, avant toute mesure

**Lemme 1 (le meilleur de N sous-espaces aléatoires).** Soit w une direction uniforme sur la sphère de
ℝ^C et V un sous-espace aléatoire uniforme de dimension P. La part d'énergie hors de V,
ρ = ‖P_V⊥ w‖² / ‖w‖², suit la loi Bêta(a, b), a = (C − P)/2, b = P/2.

*Démonstration.* Par invariance par rotation, on peut fixer V = vect(e₁ … e_P) et prendre w = z/‖z‖,
z gaussien standard. Alors ρ = Σ_{i>P} z_i² / Σ_i z_i² = X/(X + Y), X ~ χ²_{C−P}, Y ~ χ²_P
indépendants, ce qui est la définition de Bêta((C−P)/2, P/2). ∎

**Corollaire.** Pour N = 2^K sous-espaces indépendants, E[min ρ] = ∫₀¹ (1 − F(ε))^N dε, F la fonction de
répartition de Bêta(a, b). Comme F(ε) ≈ ε^a / (a B(a, b)) près de 0,
E[min ρ] ≈ Γ(1 + 1/a) · (a B(a, b) / N)^{1/a}.

Calcul exact par quadrature (`outils/genome/recette/graine_theorie.py`, `graine-theorie.json`), avant
quantification des coefficients (qui ne peut qu'ajouter de l'erreur) :

| (C, P, K) | débit (bits/poids) | résidu minimal attendu | borne de Shannon au même débit |
|---|---|---|---|
| (8, 3, 16) | 4,00 | 0,79 % | 0,39 % |
| (12, 4, 16) | 3,00 | 3,82 % | 1,56 % |
| (12, 3, 16) | 2,67 | **6,32 %** | 2,48 % |
| (14, 4, 16) | 2,57 | 7,07 % | 2,83 % |
| (16, 5, 16) | 2,50 | 7,84 % | 3,13 % |
| (16, 4, 16) | 2,25 | 10,74 % | 4,42 % |
| (8, 1, 16) | 3,00 | 5,35 % | 1,56 % |

**Ce que cela dit, avant la mesure** : autour de 2,64 bits, la graine laisse **au moins 6,3 %** d'erreur
sur une source isotrope, quand la base en laisse 4,29 %. Pour atteindre 4,29 %, il lui faut près de
3 bits. La recette littérale **ne peut pas** battre la frontière sur des poids qui ressemblent à du
bruit ; il faudrait que les blocs de poids soient beaucoup plus concentrés que des directions
uniformes, ce que la mesure de structure (§ 6) dément.

**Pourquoi** : les K bits de la graine achètent un livre de codes aléatoire de 2^K sous-espaces dans
une dimension C ≤ 16. Shannon (1959) prouve que le livre de codes aléatoire atteint la fonction
débit-distorsion, mais **quand la dimension tend vers l'infini** ; à C = 8 ou 12, l'écart à la borne
est un facteur 2,5 en erreur. Et les 4P + 4 bits des coefficients décrivent une position fine dans un
sous-espace choisi au hasard : ils paient une précision que le choix grossier du sous-espace a déjà
perdue.

### 2.3 La mesure

`genome graines C P K GEN 32` (`graines.jsonl`, `graines.log`) : expert 0 de chacun des 12 tenseurs,
32 rangées réparties sur toute la hauteur, rangées entières (360 blocs de 8, 240 de 12…) ; l'erreur de
la base est mesurée sur les mêmes poids (4,559 % sur cet échantillon).

| (C, P, K), générateur | débit | erreur mesurée | prédiction du lemme 1 (sans quantifier t) |
|---|---|---|---|
| (8, 3, 16), mélangeur | 4,00 | 1,41 % | 0,79 % |
| (8, 3, 16), LFSR | 4,00 | 1,58 % | 0,79 % |
| (10, 3, 16) | 3,20 | 3,89 % | 2,98 % |
| (12, 4, 16) | 3,00 | 4,89 % | 3,82 % |
| (8, 1, 16) (forme-gain) | 3,00 | 7,34 % | 5,35 % |
| (12, 3, 16) | 2,67 | 7,51 % | 6,32 % |
| (14, 4, 16) | 2,57 | 8,24 % | 7,07 % |
| (16, 5, 16) | 2,50 | 9,10 % | 7,84 % |
| (12, 2, 16) | 2,33 | 11,76 % | 9,99 % |
| (16, 4, 16) | 2,25 | 12,15 % | 10,74 % |

- **Le lemme 1 tient sur les vrais poids** : la mesure suit la prédiction, plus la quantification des
  coefficients (0,6 à 2 points). Les blocs de poids réels se comportent, pour la graine, comme des
  directions uniformes : aucune concentration que le meilleur de 2^16 sous-espaces aurait pu saisir.
- **Verdict** : à l'erreur de la base (4,559 % sur cet échantillon), la graine demande **3.06 bits par
  poids** (interpolation entre (12, 4) et (10, 3)), contre 2,64 pour la base : **elle ne bat pas la
  frontière**, de 0.42 bit. Elle ne bat même pas le sans-perte à 4 bits (1,4 % d'erreur pour
  4 bits, quand 3,84 bits rendent les poids exacts).
- Le générateur ne compte pas : LFSR et mélangeur rendent 1,58 % et 1,41 % (l'écart vient de la
  corrélation des états successifs d'un LFSR, qui décalent les mêmes bits d'un cran).

---

## 3. La graine qui pousse : le brin lu par codons

### 3.1 L'idée

Si le défaut de la graine est sa dimension, il faut une graine **aussi longue que la rangée**, et un
moyen de la chercher. Le vivant en donne la forme : l'ARN messager est lu par le ribosome **trois bases
à la fois, à partir d'un point fixe, sans virgule** (Crick, Barnett, Brenner et Watts-Tobin, Nature 192,
1961), et chaque codon se traduit par une **table fixe et dégénérée**, 64 codons pour 20 acides aminés et
l'arrêt (Crick, J. Mol. Biol. 38, 1968).

Transposé :
- le **brin** : une suite de bits stockée sur le disque, une par rangée de matrice ;
- la **fenêtre de lecture** : l bits ; elle avance de kb bits à chaque pas et rend v poids ; deux pas
  voisins partagent l − kb bits (les codons se chevauchent, c'est là que le brin diffère de l'ARN) ;
- le **code génétique** : la fenêtre s ∈ {0 … 2^l − 1} se traduit en v valeurs par
  `table[hache(s, j) >> (32 − q)]`, j < v : un mélangeur de bits choisit une case d'une table de 2^q
  valeurs ; 2^l fenêtres pour 2^q sens, donc un code **dégénéré** comme le vrai ;
- l'**adaptation de l'organisme** : la table est apprise sur les poids du tenseur (Lloyd : chaque case
  prend la moyenne pondérée des poids qu'elle sert), comme le code génétique est fixe pour une espèce.

Débit : kb / v bits par poids, plus la première fenêtre (l bits par rangée).

C'est un **code en treillis** : le treillis « à décalage » de Mao et Gray (DCC 2010), repris avec des
codes calculés par QTIP (Tseng et al., arXiv 2406.11235v4) ; la quantification en treillis remonte à
Marcellin et Fischer (IEEE Trans. Commun. 38(1), 1990). Ils posent le problème ainsi pour une source
gaussienne i.i.d. après une rotation aléatoire ; ce qui nous manquait, et que nous dérivons ici, c'est
(a) son emploi sur un modèle **né en 4 bits** contre une base déjà emboîtée dans le format, (b) la
répartition des bits entre rangées par leur énergie, mesurée et décomposée, (c) la comptabilité
complète contre la frontière F1 du format `.trc`. Le code est écrit ici de zéro
(`outils/genome/recette/src/codons.rs`).

### 3.2 Le meilleur brin : Viterbi, et pourquoi il est exact

État au pas p : la fenêtre s_p (l bits). Transition permise s → s′ si et seulement si les l − kb bits
forts de s′ sont les l − kb bits faibles de s, c'est-à-dire s′ = ((s ≪ kb) | b) mod 2^l, b < 2^kb.

**Lemme 2 (structure des prédécesseurs).** Les prédécesseurs de s′ sont exactement les
s = (t ≪ (l − kb)) | u, t < 2^kb, avec u = s′ ≫ kb. Ils ne dépendent de s′ que par u.

*Démonstration.* s′ ≫ kb = s mod 2^{l−kb} (les bits faibles de s, décalés), donc u fixe les l − kb bits
faibles de s, et ses kb bits forts t sont libres. ∎

**Proposition 1 (exactitude).** Soit C_p(s) le coût minimal Σ_{i≤p} Σ_j ω (x − x̂)² d'un brin dont la
fenêtre au pas p est s. Alors C_0(s) = d_0(s) et C_p(s′) = M_p(s′ ≫ kb) + d_p(s′), avec
M_p(u) = min_t C_{p−1}((t ≪ (l − kb)) | u) et d_p(s′) = Σ_j ω_{p,j} (x_{p,j} − table[hache(s′, j)])².
Le brin de coût minimal s'obtient en gardant l'argmin t de chaque M_p(u) et en remontant depuis
argmin_s C_{P−1}(s).

*Démonstration.* Le coût est additif par pas et ne dépend que de la fenêtre de chaque pas
(principe d'optimalité de Bellman) ; le lemme 2 donne l'ensemble exact des prédécesseurs. ∎

**Coût** : par pas, 2^l comparaisons (le minimum sur t, par tranches contiguës de 2^{l−kb}) et 2^l · v
évaluations ; mémoire de retour : 2^{l−kb} octets par pas. Pour l = 12 : 4 096 états, environ
2,3·10⁵ poids par seconde et par forme sur les 16 fils du i7-13620H (mesuré pendant la passe).

**Témoin T2 (comptabilité des bits)** : le brin écrit (`ecrire_brin`) puis relu par le seul décodeur
(`lire_brin`, qui ne connaît que le brin et la table) rend exactement la reconstruction dont l'erreur
est comptée (tests `brin_ecrit_puis_lu_*`, v = 1 et v = 2, poids non uniformes).

**Témoin T1 (source connue)** : sur 128 rangées gaussiennes i.i.d., l = 12, kb = 2, v = 1, q = 8,
table gaussienne sans apprentissage, l'erreur vaut **0,07305** (`gauss-T1.json`), dans l'intervalle
déclaré [0,0625 ; 0,080] ; QTIP publie 0,0733 pour le même débit (tableau 2). Cassure (table nulle) :
**0,996**, le témoin tombe (`gauss-T1-casse.json`).

**Le balayage gaussien** (`gauss-balayage.jsonl`, 64 rangées) donne la courbe du brin seul :

| forme (kb, v) | débit | l = 12 | l = 16 | borne de Shannon 2^(−2R) |
|---|---|---|---|---|
| (1, 1) | 1 | 0,2778 | 0,2672 | 0,2500 |
| (2, 1) | 2 | 0,0728 | 0,0675 | 0,0625 |
| (7, 3) | 2,33 | 0,0522 | 0,0449 | 0,0394 |
| (5, 2) | 2,5 | 0,0394 | 0,0351 | 0,0313 |
| (8, 3) | 2,67 | 0,0358 | 0,0292 | 0,0248 |
| (3, 1) | 3 | 0,0198 | 0,0177 | 0,0156 |
| (4, 1) | 4 | 0,0057 | 0,0050 | 0,0039 |

Fenêtre l = 8, 10, 12, 14, 16 à 2 bits : 0,0880 ; 0,0785 ; 0,0728 ; 0,0694 ; 0,0675. Le mélangeur bon
marché (4 opérations) rend 0,0721 contre 0,0728 pour le fort : il suffit. La taille de la table compte
peu (q = 6 : 0,0732 ; q = 10 : 0,0728).

### 3.3 La rotation : répartir l'information de chaque poids

Une rangée w (2 880 poids) est tournée par morceaux de 64 : y = (1/8) H₆₄ D w, D = diag(±1) tirée d'une
graine (aucun bit stocké). R étant orthogonale, W x = (W Rᵀ)(R x) : on stocke les rangées tournées et
l'on tourne l'activation **une fois par jeton** (64 · 6 additions par morceau, soit 6 additions par
élément d'entrée, partagées par les 2 880 rangées de toutes les matrices qui lisent cette entrée).
L'erreur est invariante : ‖W − Ŵ‖_F = ‖(W − Ŵ) Rᵀ‖_F ; l'outil la mesure néanmoins dans le domaine
d'origine, après la rotation inverse (`detourner`), comme second chemin de cette identité.

Pourquoi : un poids aberrant (une échelle E8M0 très au-dessus de la médiane de sa rangée) ne peut être
atteint par le brin qu'en sacrifiant ses voisins, qui partagent sa fenêtre. Après rotation, il est
réparti sur 64 positions ; la source devient gaussienne, ce pour quoi le treillis est fait. C'est le
geste de la **mémoire holographique** de la liste de Stone (§ 5 ter) : l'information de chaque élément
répartie sur tous.

Chaque rangée tournée est divisée par son écart-type σ (gardé sur 16 bits) : la source codée est
x = y / σ, de variance 1.

### 3.4 La répartition des bits entre rangées

Une rangée r a, pour chaque forme k, une erreur D_r(k) et un coût R_r(k) (bits du brin, première fenêtre,
3 bits d'indice de forme, 16 bits de σ). On minimise Σ_r D_r(k_r) sous Σ_r R_r(k_r) ≤ R.

**Proposition 2 (Everett, 1963).** Pour tout λ ≥ 0, le choix k_r(λ) = argmin_k D_r(k) + λ R_r(k), fait
rangée par rangée, est optimal pour le budget R(λ) = Σ_r R_r(k_r(λ)) qu'il dépense.

*Démonstration.* Si un autre choix k′ dépensait au plus R(λ) avec une erreur plus petite, alors
Σ D_r(k′_r) + λ Σ R_r(k′_r) < Σ D_r(k_r) + λ Σ R_r(k_r), contredisant la minimalité de chaque terme. ∎

La courbe débit-distorsion de la recette est l'ensemble des points (R(λ), D(λ)) pour 400 valeurs de λ ;
les bits à erreur égale se lisent par interpolation linéaire en log(erreur) entre deux points voisins.

**Ce que cela vaut, en théorie** : pour des rangées gaussiennes de variances σ_r², la répartition
optimale à haut débit (remplissage inverse) gagne ½ log₂(moyenne arithmétique des σ_r² / moyenne
géométrique) bits par poids sur une répartition uniforme. La base de B n'en prend rien : elle met
2,64 bits partout.

---

## 4. La comptabilité, au bit près

Tout ce que la recette lit sur le disque, par tenseur (`outils/genome/recette/analyse.py`) :

| poste | bits | par poids |
|---|---|---|
| brin d'une rangée de n poids | l + (n/v − 1) · kb | ≈ kb / v |
| indice de forme de la rangée | 3 | 0,0010 |
| σ de la rangée (« tourne ») | 16 | 0,0056 |
| tables : 5 formes × 256 valeurs × 16 bits, pour 32 experts | 20 480 | 0,00008 |
| échelles E8M0 (« brut » seulement) : δ de F1 + 8/2 880 de médianes | | 0,036 à 0,043 |
| alignement de chaque matrice d'expert sur 4 096 octets, au pire | 32 768 | 0,0040 |
| exceptions de S\* : compte (8 bits) + 3 × (colonne 12 + code 4 + échelle 8) par rangée | 80 | 0,028 |

La frontière F1 de chaque tenseur est lue dans `f1-par-tenseur.csv` : base + δ + 8/2 880 + 0,00007.

*Une sous-comptabilité, dite* : le journal Rust (`codons-*-l12.json`) ne compte qu'**une** table par
tenseur au lieu de cinq (0,00006 bit par poids de moins) ; le second chemin Python (`analyse.py`) compte
les cinq, et c'est lui qui fait le verdict. Les deux diffèrent de moins de 0,0002 bit par tenseur.

---

## 5. Les résultats sur les poids réels

### 5.1 Témoin S0 : la frontière refaite

`genome frontiere` recompte les 12 tenseurs entiers (3 185 049 600 poids), recalcule les centres de
classe (0,237166 ; 1,424298 ; 3,418577 ; 6,0 en unités E2M1) et retrouve l'erreur publiée
**0,042919745124980** à **5,8·10⁻¹⁵** près (`frontiere.json`). Cassure (chaque classe lit le centre de
la suivante) : 1,2128, écart ×27, le témoin tombe (`frontiere-casse.json`).

### 5.2 Le verdict W

Lecture par codons, l = 12, q = 8, 2 itérations de Lloyd sur les 48 premières rangées échantillonnées de
chaque expert ; formes (kb, v) = (2, 1), (7, 3), (5, 2), (8, 3), (3, 1). Second chemin :
`verdict-*-l12-second-chemin.json` (Python), égal au journal Rust à 10⁻⁴ bit près.

**Source tournée (« tourne »)** — le critère W **tient** :

| tenseur | erreur de la base (échantillon) | frontière (bits) | recette à erreur égale | gain (bits) | gain |
|---|---|---|---|---|---|
| blk.0.ffn_gate | 4,394 % | 2,6234 | 2,4005 | 0,223 | 8,5 % |
| blk.0.ffn_up | 4,389 % | 2,6422 | 2,4291 | 0,213 | 8,1 % |
| blk.0.ffn_down | 4,137 % | 2,6558 | 2,0604 | 0,595 | 22,4 % |
| blk.8.ffn_gate | 4,022 % | 2,6597 | 2,2410 | 0,419 | 15,7 % |
| blk.8.ffn_up | 4,068 % | 2,6424 | 2,4391 | 0,203 | 7,7 % |
| blk.8.ffn_down | 4,631 % | 2,6445 | 2,4130 | 0,231 | 8,8 % |
| blk.16.ffn_gate | 4,227 % | 2,6569 | 2,2660 | 0,391 | 14,7 % |
| blk.16.ffn_up | 4,089 % | 2,6653 | 2,3905 | 0,275 | 10,3 % |
| blk.16.ffn_down | 4,203 % | 2,6302 | 2,2920 | 0,338 | 12,9 % |
| blk.23.ffn_gate | 4,323 % | 2,6406 | 2,2203 | 0,420 | 15,9 % |
| blk.23.ffn_up | 4,254 % | 2,6256 | 2,3768 | 0,249 | 9,5 % |
| blk.23.ffn_down | 4,260 % | 2,6434 | 2,3691 | 0,274 | 10,4 % |
| **moyenne des 12** | | **2,6442** | **2,3248** | **0,319** | **12,1 %** |

12 tenseurs sur 12. En global (une seule λ pour les 34 560 rangées, erreur cumulée 4,257 %) : 2,049 bits
contre 2,644, 0,595 bit ; ce chiffre global est dominé par les rangées de grande énergie et se lit avec
le § 5.4 ; la moyenne par tenseur est le chiffre à retenir.

**Source brute (« brut », échelles E8M0 gardées, sans rotation)** — 11 tenseurs sur 12 :
gains de 0,15 à 0,57 bit, **mais blk.8.ffn_down tombe** : même à 3 bits partout, la recette y laisse
**6,43 %** d'erreur, quand la base en laisse 4,63 % à 2,64 bits. Ses rangées portent des blocs dont
l'échelle est très au-dessus de la médiane ; le brin ne peut les atteindre qu'en sacrifiant leurs
voisins. La rotation (§ 3.3) règle exactement ce cas (0,231 bit gagné sur ce tenseur). Le critère W
tombe donc pour « brut » et tient pour « tourne » ; c'est ce qui a décidé de la rotation.

### 5.3 D'où vient le gain : pavage contre répartition

Les formes fixes (toutes les rangées à la même forme, sans répartition) donnent, par interpolation
entre formes voisines, le gain du **seul pavage** (`codons-tourne-l12.json`, champ `fixes`) :
0,14 à 0,18 bit sur 11 tenseurs (moyenne des 12 : 0,135), et **−0,14 bit** sur blk.8.ffn_down, où la
répartition est indispensable. La répartition entre rangées apporte le reste : de 0,03 bit (blk.0.ffn_up)
à 0,43 bit (blk.0.ffn_down).

Les erreurs des formes fixes sur les poids tournés (0,0739 ; 0,0529 ; 0,0402 ; 0,0364 ; 0,0201 pour
blk.0.ffn_gate) sont celles du brin sur une **gaussienne vraie** (0,0728 ; 0,0522 ; 0,0394 ; 0,0358 ;
0,0198) à 1,5 % près : **après rotation, les poids sont, pour le brin, indiscernables d'un bruit
gaussien**.

### 5.4 La sortie des experts sur des entrées réelles

Voir § 8.2 (sortie) et § 8.3 (KL).

---

## 6. Où est le bruit, où est la structure

`outils/genome/recette/structure.py`, `structure-spectre.json` (expert 0 de chaque tenseur, valeurs
singulières de la matrice 2 880 × 2 880 en f64 exact) ; témoin : la même matrice dont les entrées sont
permutées au hasard (toute structure de rang détruite, loi de Marchenko-Pastur).

| tenseur | énergie des 144 premières directions (5 %) : réel / permuté | 1re direction : réel / permuté | kurtosis | gain de répartition par rangées (haut débit, calculé) |
|---|---|---|---|---|
| blk.0.ffn_gate | 27,4 % / 17,2 % | 0,81 % / 0,14 % | 4,0 | 0,019 bit |
| blk.0.ffn_up | 23,2 % / 17,2 % | 0,29 % / 0,14 % | 3,8 | 0,009 |
| blk.0.ffn_down | 67,7 % / 18,9 % | 8,48 % / 0,38 % | 347,7 | 1,272 |
| blk.8.ffn_gate | 45,2 % / 17,3 % | 1,62 % / 0,14 % | 12,9 | 0,572 |
| blk.8.ffn_up | 30,0 % / 17,2 % | 0,41 % / 0,14 % | 4,9 | 0,111 |
| blk.8.ffn_down | 43,1 % / 18,5 % | 7,00 % / 0,44 % | 343,2 | 0,250 |
| blk.16.ffn_gate | 54,2 % / 18,1 % | 4,60 % / 0,39 % | 182,9 | 0,645 |
| blk.16.ffn_up | 30,4 % / 17,2 % | 0,72 % / 0,14 % | 6,3 | 0,160 |
| blk.16.ffn_down | 43,3 % / 17,4 % | 1,54 % / 0,21 % | 42,0 | 0,343 |
| blk.23.ffn_gate | 42,0 % / 17,3 % | 2,27 % / 0,14 % | 17,2 | 0,426 |
| blk.23.ffn_up | 33,5 % / 17,2 % | 1,01 % / 0,14 % | 7,9 | 0,130 |
| blk.23.ffn_down | 33,3 % / 17,7 % | 3,45 % / 0,19 % | 79,7 | 0,089 |

**Lecture.**
- **Le bruit** : à l'intérieur d'une rangée, une fois la rangée tournée et normalisée, il n'y a rien à
  prendre au-delà de la variance : le brin y fait exactement ce qu'il fait sur une gaussienne vraie
  (§ 5.3, à 1,5 % près), les codes MXFP4 voisins ne partagent que 0,005 bit (03 § 1.6), et la graine de
  dimension 8 à 16 trouve ce qu'elle trouverait dans du bruit (§ 2.3). **Aucune recette courte
  n'engendre ces poids** : c'est la réponse à la question « recettables ? » de l'idée (§ 6 de l'idée).
- **La structure** est au second ordre, et elle est grande : l'énergie se concentre sur quelques
  directions (5 % des directions portent 23 à 68 % de l'énergie, contre 17 à 19 % pour la même matrice
  permutée ; une seule direction en porte jusqu'à 8,5 %, ×22 le hasard), et donc sur certaines rangées
  (kurtosis jusqu'à 348, gain de répartition calculé jusqu'à 1,27 bit). C'est elle que la répartition
  des bits entre rangées encaisse (§ 5.3), et que la base de B, qui met le même nombre de bits partout,
  laisse sur la table.
- **Ce qui reste à prendre** : la borne gaussienne avec répartition idéale entre rangées
  (`borne-shannon-par-tenseur.json`, débit-distorsion de Shannon sur les variances de rangée mesurées)
  vaut 1,07 à 2,25 bits à l'erreur de la base ; la recette mesurée est à 0,19 à 0,99 bit au-dessus.
  L'écart vient (a) du brin à l = 12, à 0,3 à 0,8 dB de la borne (§ 3.2), (b) de la plus petite forme,
  2 bits : le remplissage idéal donnerait 0 ou 1 bit aux rangées les plus faibles (blk.0.ffn_down : borne
  1,07 bit), ce que la recette ne sait pas faire. La forme « zéro » (rangée non stockée) a été chiffrée sur
  les mêmes CSV : elle ferait tomber le débit global à 0,36 bit **à erreur cumulée égale**, ce qui montre
  surtout que l'erreur cumulée sur les poids se laisse tromper par la répartition (une poignée de
  rangées de très grande énergie la dominent). Elle n'est pas retenue : c'est la sortie des experts et la
  KL qui jugent la répartition (§ 5.4).
- **La structure de rang** (quelques directions dominantes) n'est pas exploitée ici. Le calcul de ce
  qu'elle vaut : stocker r directions (u, v en f16) coûte r · 5 760 · 16 / 8 294 400 = 0,011 · r bit par
  poids ; pour blk.0.ffn_down, la première direction (8,5 % de l'énergie) rendrait ½ log₂(1/0,915) =
  0,064 bit à erreur égale pour 0,011 bit de coût ; pour les tenseurs « up » (0,3 à 1 %), rien. C'est une
  piste, chiffrée, au § 9.

---

## 7. La recette combinée à la découpe base + complément

**Lemme 3 (le complément exact ne rend rien gratuitement).** Soit X les codes MXFP4 d'un tenseur et Y
les bits de la recette, fonction déterministe de X (l'encodeur est déterministe). Alors
H(X) = H(Y) + H(X | Y), et pour tout codage du complément qui conditionne chaque code X_i sur une
fonction Z_i de Y :
R_Y + Σ_i H(X_i | Z_i) ≥ H(Y) + H(X | Y) = H(X).

*Démonstration.* H(X, Y) = H(X) + H(Y | X) = H(X) puisque Y est fonction de X ; H(X, Y) = H(Y) + H(X | Y).
Puis H(X | Y) ≤ Σ_i H(X_i | Y) ≤ Σ_i H(X_i | Z_i) (le conditionnement réduit l'entropie, et Z_i est
fonction de Y), et R_Y ≥ H(Y). ∎

La recette suivie d'un complément exact ne peut donc pas descendre sous l'entropie des codes ; ce
qu'elle perd est (R_Y − H(Y)) + (Σ H(X_i | Z_i) − H(X | Y)) : l'information sur X que les bits du brin
portent **ensemble** et qu'un contexte poids par poids ne voit pas.

**Mesuré** (`codons-*-l12.json`, champ `H_code_sachant_recette` : Z_i = la reconstruction de la recette
ramenée à l'échelle du bloc, en 65 cases de 0,375) : recette + complément + échelles = **4,05 à 4,37
bits par poids** pour la source tournée (4,09 à 4,90 pour la brute) selon la forme et le tenseur, contre
3,80 à 3,83 sans perte pour les mêmes tenseurs. La perte, 0,21 à 0,53 bit en « tourne », est le second
terme. Le critère L (déclaré) tombe, comme le lemme l'annonçait.

**Ce que la combinaison donne quand même** : dans l'architecture B, le niveau 0 est lu à chaque défaut
de cache et le complément seulement pour les experts admis. Remplacer la base par la recette au niveau 0
divise les octets d'un défaut par 2,644 / 2,325 = **1,14** à erreur égale, ou, au même débit
(le débit de la frontière de chaque tenseur), rend une erreur plus petite : **2,07 à 3,82 %** au lieu
de 4,02 à 4,63 % (interpolé sur `courbes-tourne-l12.csv`) ; le complément qui suit coûte alors 0,21 à
0,53 bit de plus qu'avec la base.
Le choix dépend de la part des usages servis par le niveau 0 (h_s de 07 § 4.2) : il se chiffre au § 9.

---

## 8. Mesures complémentaires

### 8.1 Les motifs partagés, combinés (le « pool de gènes »)

`genome motifs D B M` (`motifs-*.json`) : un bloc de d poids (source brute, valeurs E2M1 doublées, erreur
pondérée par 4^(e − 128)) est la somme de M motifs, chacun tiré d'un dictionnaire de 2^b motifs
**partagé par les 32 experts** du tenseur, appris par k-moyennes pondérées sur les 48 premières rangées
échantillonnées de chaque expert, étage par étage sur le reste (quantification résiduelle). Témoin :
le quantificateur scalaire à 4 niveaux d'une gaussienne rend 0,1175 (Max 1960), test
`lloyd_max_deux_bits_gaussien`. Même échantillon que le § 5 (34 560 rangées).

| (d, b, M) | débit global (échelles et dictionnaires compris) | erreur cumulée |
|---|---|---|
| (8, 8, 1) / (8, 8, 2) / (8, 8, 3) | 1,04 / 2,04 / 3,04 | 34,2 % / 12,3 % / 4,56 % |
| (8, 12, 1) / (8, 12, 2) | 1,54 / 3,05 | 18,2 % / 3,65 % |
| (4, 10, 1) | 2,54 | 5,17 % |

À l'erreur de la base (4,257 %), les motifs demandent **2,90 bits** au mieux (interpolation entre les
deux points de (8, 12)) : **ils ne battent pas la frontière**. Pourquoi : un dictionnaire appris en
dimension 4 à 8 est un quantificateur vectoriel de petite dimension ; même le meilleur réseau de
dimension 8 (E8, 0,089 à 2 bits sur une gaussienne, QTIP tableau 1) reste loin du brin (0,073), et
l'étage résiduel glouton perd encore sur le meilleur dictionnaire conjoint. Partager le dictionnaire
entre experts ne coûte rien (0,002 bit) et ne rend rien de plus : les experts n'ont pas de motifs propres
que le dictionnaire commun manquerait, ce qui est cohérent avec le bruit du § 6.

### 8.2 La sortie des experts sur des entrées réelles

**Les entrées** : les états normalisés (entrée des experts) et le routage de la référence f64, capturés
par l'éclaireur (`outils/genome/eclaireur/capture`) ; « calib » = fenêtres 10 à 21 de wiki.test (réglage
seulement), « eval » = fenêtres 0 à 9, celles du .kld de R1 (mesure seulement). Pour l'expert e de la
couche l, les 512 premières positions routées vers lui (moins si l'expert est rare). Sortie de l'expert :
y = W_down · SwiGLU-oai(W_gate h + b, W_up h + b) + b, en f64, poids exacts, base ou recette ; erreur
relative Σ‖y − ŷ‖² / Σ‖y‖².

**Premier constat : au point W, la recette perd en sortie.** Couche 0, expert 0 (499 positions) : erreur
de poids 4,25 % (base 4,27 %) mais erreur de sortie **7,63 %** contre **6,77 %** pour la base
(`sortie-tourne-point-W-interrompu.log`) ; le critère O, déclaré à ce point, **tombe**. **L'erreur
quadratique sur les poids ne mesure pas la fidélité** : à erreur de poids égale, l'erreur de la base
fait moins de dégâts en sortie que celle du brin.

**La fidélité en fonction du débit** (passe F, `fidelite.log`, `verdict-fidelite.json`,
`csv/fidelite.csv`) : chaque expert codé entier à 2,0 ; 2,2 ; 2,4 ; 2,64 ; 2,9 bits par poids,
« uniforme » (brin non pondéré) et « pondérée » (Viterbi pondéré par h = diag(R Σ Rᵀ), Σ estimée sur
« calib »). Arrêtée après 5 experts et demi, le verdict étant acquis :

| couche, expert (positions) | base | uniforme à 2,64 b | pondérée à 2,64 b | bits à sortie égale (uniforme / pondérée) |
|---|---|---|---|---|
| 0, 0 (499) | 6,77 % | 5,25 % | 5,18 % | 2,41 / 2,38 |
| 0, 16 (512) | 5,13 % | 3,88 % | 3,82 % | 2,38 / 2,39 |
| 8, 0 (512) | 8,30 % | 8,80 % | 7,91 % | 2,68 / 2,60 |
| 8, 16 (131) | 7,45 % | 8,93 % | 9,41 % | 2,87 / > 2,9 |
| 16, 0 (127) | 5,72 % | 6,02 % | 5,40 % | 2,68 / 2,58 |
| 16, 16 (150) | 4,81 % | 11,04 % | — | > 2,9 / — |

**Le verdict F tombe** : la pondération gagne sur 4 experts sur 5 et l'uniforme sur 2 sur 6 ; deux
experts perdent dans les deux variantes.

**Pourquoi** (`erreur_colonnes.py`, `erreur-colonnes-ponderee-264.json`) : l'erreur du brin ne se répartit
pas sur les colonnes comme celle d'un bruit blanc. Dans blk.8.ffn_down (expert 16), la colonne 1011 porte
**144 fois** l'énergie moyenne d'une colonne, et reçoit **334 fois** l'erreur moyenne ; les colonnes de
rang 0 modulo 64 en reçoivent 7,6 fois leur part. Le mécanisme : une colonne massive se répartit, par la
rotation, en 64 valeurs grandes dans chaque rangée ; la table (256 valeurs, quantiles de la source) les
écrête ; les erreurs d'écrêtage, de même signe dans toutes les rangées, reviennent par la rotation inverse
**sur la colonne massive**. Or une colonne massive de down lit une unité de l'activation intermédiaire, et
une colonne massive de gate ou up un canal d'entrée : là où l'erreur fait le plus de mal. La base, elle,
rend presque exacts les plus grands poids de chaque bloc (sa classe {6} est exacte). Sur les 15 matrices
analysées (5 experts × 3), 5 ont une colonne dont l'erreur dépasse 10 fois la moyenne ; dans 4 d'entre
elles c'est la colonne la plus énergétique de la matrice ; la cinquième (gate, couche 16, expert 0,
colonne 2 744, ×29,9) est la colonne la plus énergétique de la matrice up du même expert, qui lit la même
entrée.

**Le remède, et le système S\*** : garder **à part, exacts**, les 3 poids de plus grande magnitude de chaque
rangée (0,1 % ; 8 + 3 × 24 bits par rangée, 0,028 bit par poids, comptés) : ce sont, rangée après
rangée, les entrées des colonnes massives. Couche 8, expert 16, uniforme : l'erreur de sortie passe de
8,93 % à **6,20 %** (base 7,45 %), l'erreur de poids de 4,63 % à 3,16 % (`fidelite-exceptions.log`). Le
brin, la rotation, la pondération et ces exceptions forment **S\***, mesuré sur les 8 experts ci-dessous.

**S\*, mesuré** (`fidelite-sstar.log`, `fidelite-sstar.json`, `verdict-fidelite-sstar.json`,
`csv/fidelite-sstar.csv` ; déclaré avant sa passe ; les experts de la couche 16 expert 16 et de la
couche 23 n'avaient servi à aucun choix) :

| couche, expert (positions) | base | S\* à 2,64 b | positions où S\* gagne | S\* à 2,4 b | bits de S\* à sortie égale |
|---|---|---|---|---|---|
| 0, 0 (499) | 6,77 % | **5,09 %** | 440 / 499 | 6,56 % | 2,37 |
| 0, 16 (512) | 5,13 % | **3,65 %** | 432 / 512 | 4,74 % | 2,34 |
| 8, 0 (512) | 8,30 % | **7,79 %** | 333 / 512 | 10,05 % | 2,58 |
| 8, 16 (131) | 7,45 % | **6,72 %** | 93 / 131 | 8,50 % | 2,54 |
| 16, 0 (127) | 5,72 % | **4,57 %** | 122 / 127 | 5,92 % | 2,43 |
| 16, 16 (150) | 4,81 % | **3,26 %** | 149 / 150 | 4,30 % | 2,30 |
| 23, 0 (150) | 5,68 % | **3,15 %** | 148 / 150 | 4,10 % | 2,09 |
| 23, 16 (106) | 3,97 % | **2,56 %** | 106 / 106 | 3,36 % | 2,23 |
| **moyenne** | | **rapport 0,747** | | | **2,36** |

**Le verdict F(S\*) tient** : à 2,64 bits, S\* fait moins d'erreur de sortie que la base sur **8 experts
sur 8** (test du signe, 2⁻⁸ ≈ 0,004), et sur chaque expert la majorité des positions le confirme (de
333 sur 512 à 106 sur 106 ; la loi binomiale donne p < 10⁻⁵ pour chacun). À erreur de sortie égale,
S\* lit **2,09 à 2,58 bits, 2,36 en moyenne, contre 2,64** : 0,28 bit de moins par poids lu sur le
disque (10,8 %). C'est moins que les 0,32 bit du critère W : l'erreur de poids exagérait le gain, la
sortie le juge.

### 8.3 La divergence KL contre la référence

(Rempli par `chaine.sh`.)

### 8.4 La transcription : opérations par poids et débit du décodeur

**Le décodeur d'un poids** (forme v = 1 ; `lire_brin`, et le même geste dans une GEMV sur la carte) :

| étape | opérations |
|---|---|
| fenêtre : registre de 64 bits décalé de kb, bits neufs insérés, masque de l bits | 3 |
| mélangeur fort (xor, puis trois fois multiplication et décalage-xor) | 9 (le court : 3) |
| indice de table (décalage) | 1 |
| lecture de la table (256 valeurs en mémoire partagée) | 1 |
| multiplication-addition avec l'activation tournée | 1 |
| **total par poids** | **15** (le court : **9**) |

Par rangée : une multiplication par σ (négligeable sur 2 880 poids). Pour v = 2 ou 3, la fenêtre se
partage entre les v poids du pas : (3 + v · 12) / v opérations par poids avec le mélangeur fort.
Par jeton, la rotation de l'activation : 6 additions et un changement de signe par élément d'entrée,
partagés par les 2 880 rangées qui le lisent, soit 0,002 opération par poids.

**Le budget** (01-machine) : 214 opérations libres par octet compressé lu, 926 au débit du disque selon
la correction du Tome II (m12). À 2,32 bits par poids (la moyenne du verdict W), un poids coûte
0,29 octet, donc **62 opérations** de budget (269 au débit du disque) : le décodeur en prend 15, soit
**le quart** (6 % au débit du disque). Pour comparaison, le décodeur rANS v4 de l'étude 03 coûte environ
25 opérations entières par pas d'un octet, soit environ 12 par code de 4 bits (03 § 4.2, calculé) : le
brin coûte du même ordre que le décodeur sans perte déjà mesuré à 130 milliards d'octets par seconde sur
la carte (03 § 4.1). La transcription ne limite pas ; elle reste à mesurer dans un noyau.

**Mesuré sur le processeur** (`genome decoder`, `decodeur-*.json`) : un expert entier (8 294 400 poids,
blk.16.ffn_up, expert 0) relu depuis ses 2 880 brins par le seul décodeur, en séries ABBA de 8 contre la
déquantification MXFP4 du même expert par le même chemin (une rangée par tâche, 16 fils), machine
chargée par les trois autres équipes :

| forme, mélangeur | brin (poids/s, médiane) | MXFP4 (poids/s, médiane) | rapport |
|---|---|---|---|
| (5, 2), fort | 9,6·10⁷ | 10,2·10⁷ | 0,94 |
| (5, 2), court | 7,5·10⁷ | 6,3·10⁷ | 1,20 |
| (2, 1), fort | 6,9·10⁷ | 7,1·10⁷ | 0,97 |

Le décodeur du brin va **aussi vite que la déquantification du format natif** sur le même chemin
(rapport 0,94 à 1,20 ; la dispersion des passes sous la charge, 0,05 à 0,17 s, est de l'ordre de
l'écart). Les débits absolus ne valent rien sous cette charge ; seul le rapport compte. Sur la carte, la
mesure reste à faire (§ 9).

---

## 9. Ce qui reste

1. **Le noyau sur la carte** : une GEMV qui lit le brin (fenêtre glissante dans un registre de 64 bits,
   mélangeur, table de 256 valeurs en mémoire partagée), tourne l'activation par morceaux de 64 et
   accumule ; à mesurer contre les 2,82 Go/s du disque et contre le noyau MXFP4 du moteur (lot K). La
   consigne de ce sujet ne donnait pas la carte.
2. **Le format** : une sorte de flux « BRIN » dans `.trc` (ARCHITECTURE § 4.10) : par matrice, l'indice de
   forme (3 bits) et σ (16 bits) de chaque rangée, puis les brins bout à bout (le décalage d'une rangée
   est la somme des longueurs précédentes, calculée une fois) ; les tables (5 × 256 × 16 bits) par
   tenseur, résidentes ; la graine de la rotation est une constante du format.
3. **La fidélité, plus loin** : S\* protège les colonnes massives par les exceptions et pondère par la
   diagonale ; le terme qui manque encore est la **rétroaction d'erreur entre colonnes** (LDLQ de
   QuIP/QTIP, ou la « mutation synonyme » de l'éclaireur) combinée au brin : quantifier par blocs de
   colonnes en reportant l'erreur sur les suivantes par la hessienne Σ. C'est la suite la plus
   prometteuse : le brin a gagné le pavage et la répartition, les exceptions les colonnes massives, la
   rétroaction gagnerait la corrélation des entrées. Une table plus large (queues gaussiennes jusqu'à
   6σ) attaquerait l'écrêtage à la racine.
4. **La fenêtre l = 16** (et des formes plus fines, (9, 4) = 2,25 bits) : 0,03 à 0,08 bit de plus sur
   une gaussienne (§ 3.2), au prix d'un codage 16 fois plus lent (hors ligne, une fois).
5. **La structure de rang** : 1 à 8 directions dominantes stockées à part (§ 6), jusqu'à 0,05 bit net
   sur les « down » ; à mesurer.
6. **gpt-oss-120b** : refaire W et F sur ses tenseurs.
7. **La KL du modèle entier** : la passe K ne substitue que 8 experts sur 768 ; la KL de tous les experts
   codés demande de coder 19,1 milliards de poids : à 2,3·10⁵ poids par seconde et par forme (l = 12),
   ≈ 23 h de processeur pour une forme par rangée, ≈ 115 h pour les cinq ; ou un codeur sur la carte.

---

## 10. Ce qui pourrait être faux

- **L'erreur sur les poids n'est pas la qualité.** Le critère W est déclaré en erreur cumulée sur les
  poids, comme la frontière ; § 6 montre que cette mesure se laisse tromper par une répartition qui
  sacrifie les rangées faibles. La répartition retenue (cinq formes de 2 à 3 bits, aucune rangée sous
  2 bits) limite ce biais sans l'exclure : la sortie des experts et la KL (§ 5.4, § 8) le jugent.
- **L'échantillon** : 4 experts sur 32, une rangée sur 4, 12 tenseurs sur 72, gpt-oss-20b seul. Le
  gain par tenseur varie de 0,20 à 0,60 bit ; le 120b n'est pas mesuré (les entropies des deux modèles
  diffèrent de 0,001 bit sur les codes, 03, ce qui rend un écart grand improbable, sans le prouver).
- **Les tables sont apprises sur l'échantillon** (48 rangées par expert) et évaluées aussi sur ces
  rangées ; leur coût est compté, mais un léger sur-apprentissage est possible. La sortie (§ 5.4) les
  applique à des experts entiers et à des entrées qu'elles n'ont jamais vues.
- **L'interpolation en log(erreur)** entre deux points de la courbe lagrangienne suppose la courbe
  localement exponentielle ; les points sont serrés (400 valeurs de λ), l'erreur d'interpolation est
  sous 10⁻³ bit.
- **La frontière F1** est mesurée par un codeur réel (en-têtes, tuiles) ; la recette est comptée bit à
  bit sans en-tête de tuile autre que l'alignement au pire. Si le format `.trc` impose des tuiles plus
  fines au brin, il faut ajouter leurs en-têtes (≈ 0,4 % de tuile pour un flux rANS, 03 ; le brin, à
  débit fixe, n'a ni table de fréquences ni état final à stocker).
- **La transcription n'est pas mesurée sur la carte** (la consigne ne la donnait pas) : le coût en
  opérations par poids est compté, le débit est mesuré sur le processeur (§ 8) ; un noyau CUDA reste à
  écrire et à mesurer contre les 2,82 Go/s du disque.
- **La rotation impose de tourner l'activation** : 6 additions par élément d'entrée et par jeton ; pour
  la projection down, l'entrée diffère par expert et doit être tournée pour chaque expert actif. Calculé
  négligeable, pas mesuré dans le moteur.
- **S\* a été choisi après avoir vu 5 experts sur 8** (les deux remèdes viennent des échecs mesurés) ;
  les 3 autres (couche 16 expert 16, couche 23 experts 0 et 16) n'avaient servi à rien et gagnent aussi
  (3,26 % contre 4,81 % ; 3,15 contre 5,68 ; 2,56 contre 3,97). Le risque d'avoir réglé S\* sur ses
  propres juges reste : la KL (§ 8.3) et un autre jeu d'experts le diront.
- **Peu de positions pour certains experts** (106 à 150 aux couches 16 et 23, 131 pour la couche 8
  expert 16) : chaque verdict par expert reste significatif par la loi binomiale (93 sur 131 :
  p ≈ 10⁻⁶), mais la taille de l'effet est moins précise.
- **La pondération est estimée sur « calib »** (au plus 1 024 positions routées) : pour un expert rare,
  h est bruitée (couche 8 expert 16 : la pondération seule y faisait pire).
- **SeedLM et QTIP** sont lus à la source (arXiv, versions et dates dans la bibliographie) ; les chiffres
  qu'ils publient sur Llama ne sont pas reproduits ici et ne servent que de repère (QTIP : 0,069 à 2 bits
  sur une gaussienne, retrouvé à 0,0675 pour l = 16 et 0,0731 pour l = 12).

---

## 11. Recettes (essayées, avec leur raison)

| Recette | Marche ? | Raison |
|---|---|---|
| Graine + coefficients (SeedLM écrit de zéro), C = 8 à 16, P = 1 à 5, K = 16 | **non** | un livre de codes aléatoire de dimension 8 à 16 est trop court (lemme 1) : ≥ 6,3 % d'erreur autour de 2,64 bits, mesuré au-dessus (§ 2.3) |
| LFSR de 16 bits contre mélangeur compteur comme générateur | pareil | la qualité ne dépend pas du générateur (§ 2.3) ; le mélangeur se calcule en parallèle |
| Brin lu par codons (treillis à décalage, code génétique haché, table apprise) | **oui** | dimension illimitée, recherche exacte par Viterbi ; à 1,5 % de l'erreur d'une gaussienne vraie |
| Même brin sur la source brute (échelles E8M0 gardées) | non sur 1 tenseur sur 12 | les poids aberrants (kurtosis 343) ne s'atteignent qu'en sacrifiant leurs voisins |
| Rotation de Hadamard par 64 avant le brin | **oui** | répartit chaque aberrant sur 64 positions : la source devient gaussienne |
| Répartition des bits entre rangées (lagrangien, 5 formes) | oui en erreur de poids | encaisse la dispersion des énergies de rangée (structure du second ordre) ; jugée sur la sortie au § 5.4 |
| Forme « zéro » (rangée non stockée) | non retenue | trompe la mesure d'erreur cumulée (0,36 bit global à erreur égale) |
| Recette + complément exact (H(code \| recette)) | non | lemme 3 : 4,05 à 4,37 bits contre 3,84 sans perte |
| Mélangeur bon marché (4 opérations) au lieu du fort (10) | oui | 0,0721 contre 0,0728 sur une gaussienne |
| Fenêtre l = 16 au lieu de 12 | meilleur, 16 fois plus lent à coder | 0,0675 contre 0,0728 à 2 bits ; surtout pour v = 3 (0,0449 contre 0,0522 à 2,33 bits) |
| Table de 2^6 ou 2^10 valeurs au lieu de 2^8 | pareil | 0,0732 et 0,0728 contre 0,0728 |
| Codeur de la graine bloc par bloc, allocations par appel | trop lent (×8) | boucle extérieure sur les graines, blocs en cache : ×8 |
| Interrompre une file de passes par le gestionnaire de tâches de l'outil | ne tue pas l'enfant | arrêter le `sh` et son enfant par leur numéro (processus lancés par moi) |
| Juger la recette par l'erreur de poids seule | **non** | au point W, l'erreur de sortie est pire que celle de la base (7,63 % contre 6,77 %) : la mesure de poids ne voit pas où l'erreur tombe |
| Répartition « relative » (chaque rangée à erreur relative égale) | non | 10,05 % de sortie au même débit : elle retire des bits aux rangées qui comptent |
| Pondérer le Viterbi par diag(R Σ Rᵀ) | en partie | gagne 4 experts sur 5 au lieu de 2 sur 6, mais ne protège pas une colonne précise après la rotation |
| Source brute pondérée par diag(Σ), sans rotation | non (arrêtée) | 11,2 % de sortie à 2,64 bits (couche 8, expert 0) : les poids aberrants reviennent |
| Exceptions seules (0,1 %, sans pondération) | en partie | couche 8, expert 16 : 8,93 % → 6,20 % ; expert 0 : sans effet |
| **S\* = rotation + pondération + exceptions 0,1 %** | **oui** | 8 experts sur 8 sous la base à 2,64 bits ; 2,36 bits à sortie égale |
