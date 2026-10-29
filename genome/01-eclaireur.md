# 01 · L'éclaireur : deux mécanismes synonymes, conçus et mesurés sur les poids de gpt-oss

Étude « génome des poids » de troncons, rôle de l'éclaireur (après genome/00-etat-de-l-art.md).
Date : 2026-10-16. Étiquettes : **mesuré ici** (outil et journal commités), **calculé**,
**littérature (éditeur, non reproduit)**. Tous les journaux sont sous
`mesures/genome/etat-de-l-art/`, tous les outils sous `outils/genome/eclaireur/`.

---

## En bref

1. **J'ai cherché où est le bruit et où est la structure des poids**, avant de concevoir. Trois
   mesures : (a) **le signe d'un zéro est une pièce de monnaie parfaite** : 12,8 % des codes MXFP4 de
   gpt-oss-20b sont des zéros (±0), et leur signe porte 0,99999999 bit d'entropie, sans aucun effet
   sur la valeur du poids (−0 = +0) ; (b) l'énergie des poids est **concentrée** : 5,8 % des blocs
   (exposants 129 et 130) portent 74 % de l'énergie des 12 tenseurs de référence ; (c) la borne
   distorsion-débit d'un codeur sans mémoire dans le domaine des poids (Blahut-Arimoto) place la
   frontière de la base loin de l'optimum (§ 3).
2. **Mécanisme 1, le codon synonyme du zéro** (§ 4). Le code MXFP4 a seize codes pour quinze valeurs :
   +0 et −0 sont des **codons synonymes**. Le signe d'un zéro est de l'**ADN non codant** : de
   l'information héritée de la quantification (le signe du poids BF16 d'origine) que le calcul ne lit
   jamais. Ramener −0 à +0 avant le codage entropique : **3,7061 bits par poids au lieu de 3,8431**
   (codeur rANS réel de F1, chaque flux décodé exactement), **−0,1370 bit, −3,56 %**, sur les 12
   tenseurs de F1 ; **0,1278 bit** sur les 72 tenseurs d'experts de gpt-oss-20b. Les poids sont égaux
   comme nombres réels ; les logits de la référence f64 sont **identiques au bit** (759 416 633
   demi-octets réécrits, 0 logit différent sur 24 jetons ; cassure : 4 826 112 différents). Coût de
   transcription : **zéro** (même décodeur, une table de moins). **Il bat la frontière sans perte**,
   au seuil déclaré avant (0,05 bit).
3. **Mécanisme 2, la mutation synonyme** (§ 5) : choisir les symboles de la base par rétroaction
   d'erreur pondérée par les entrées réelles des experts (OBS/GPTQ, le report d'erreur du neurone
   sigma-delta), sous contrainte d'entropie, **avec le même décodeur** (coût de transcription nul).
   La passe déclarée (δ = 0,01) **échoue** par sur-apprentissage (766 entrées en dimension 2 880 :
   erreur de sortie 0,2 % en calibration, 4,4 % en évaluation). Avec δ* = 1, choisi par validation
   croisée sur la calibration seule, et λ = 1 : **2,563 bits au lieu de 2,642 (−0,078)** et une
   erreur de sortie d'expert, sur des entrées réelles tenues à l'écart, **divisée par 3 à 4**
   (1,18 / 0,74 % contre 3,94 / 3,14 %), plus basse dans les 4 couches et les 2 moitiés : **elle bat
   la frontière avec perte** au critère déclaré avant. Son erreur sur les poids **monte** (4,9 % contre
   4,3 %) : la structure n'est pas dans les poids, elle est dans les entrées. Prix : elle n'est plus
   emboîtée (complément exact 1,689 bit au lieu de 1,219) ; elle sert de second génome, rapide, à côté
   du fichier exact.
4. **De bout en bout** (§ 6), 32 experts sur 768 remplacés, 2 550 positions contre la référence f64 :
   KL moyenne **0,026 contre 0,036** (médiane 0,0038 contre 0,0088), premier choix **90,9 % contre
   87,1 %** (intervalles de Wilson disjoints), perplexité +1,8 % contre +5,4 %. Les deux restent loin
   du seuil de B (0,0055) : la base, même synonyme, est un mode rapide, pas le mode exact.
5. **Verdict** (§ 7) : deux mécanismes battent la frontière, chacun dans sa branche ; aucun ne
   « génère » les poids, les deux exploitent une **synonymie** (un code sans effet sur le phénotype).

---

## D'où on part, où on va

**Au départ** (fondations/03, 07 ; ARCHITECTURE § 3 F1) : sans perte, 3,8431 bits par poids (codes
en rANS à table par voie, échelles en écart à la médiane de ligne) ; la base seule (signe et quatre
classes de magnitude) à 2,6441 bits pour 4,29 % d'erreur quadratique relative sur les poids. Les
codes sont presque indépendants sachant l'échelle (0,005 bit pour le voisin).

**Ce que ce document établit** : où sont le bruit et la structure ; un mécanisme sans perte (de valeur)
qui bat la frontière, prouvé au bit sur les logits ; la mesure d'un mécanisme avec perte jugé sur la
sortie des experts pour des entrées réelles.

**Ce qui reste** : § 8.

---

## 1. Les instruments, et leurs témoins

| Outil | Rôle | Témoin (déclaré avant) | Résultat |
|---|---|---|---|
| `capture/` (Rust, fourche de `trc-reference`) | capture les entrées réelles des experts (h après la norme, f32) et le routage, à chaque couche ; substitue des bases ; réécrit un code | logits de la fourche = ceux de `trc-reference` au bit (24 jetons) ; cassure : YaRN sans échelle | **0** logit différent ; cassure **4 826 112** [mes., `journaux/temoin-fourche*.json`] |
| `synonyme.py` | la base frontière et la mutation synonyme ; erreurs de poids et de sortie | T0 : erreur frontière sur les 12 tenseurs = 0,042919745 (07) à 1e-6 ; T1 : H = I, λ = 0 rend la frontière (0 symbole) ; T2 : H0 = 2,642 à 0,001 | T0 **0,04291974512498** (cassure 0,4246) ; T1 **0** (cassure, H réel : 1 789 132) ; T2 **2,6415** [mes., `journaux/temoins*.json`] |
| `zero-synonyme/` (Rust, fourche de la mesure F1) | codeur rANS réel, décodage exact, avec ou sans −0 → +0 | sans drapeau : redonne F1 au bit | **toutes les grandeurs de F1 égales** (A_ctx 3,843137) [mes., `journaux/zero-temoin-sans-drapeau.json`] |
| `zero_compte.py` | comptes exacts des ±0 | H(code) des 12 tenseurs = 3,860 à 0,001 ; cassure (le code 1 compté comme zéro) : l'écart bouge de > 0,05 | **3,8598** ; cassure 0,1369 → 0,3514 [mes.] |
| `borne_rd.py` | borne R(D) dans le domaine des poids (Blahut-Arimoto) | B1 : bouts de la courbe ; B2 : gaussienne à 0,05 bit | passe 1 : **B1 tombe** (non-convergence à pente 1e-6) ; B2 tient (1e-5 bit) ; cassure tombe ; correction déclarée après, voir § 3 |

**Les entrées réelles** (`journaux/capture-*.json`) : wiki.test, découpé par `trc-jetons` (les 10
premières fenêtres égalent celles du `.kld` de R1, vérifié par l'outil) ; **calibration** = fenêtres
10 à 21 (6 132 positions), **évaluation tenue à l'écart** = fenêtres 0 à 9 (5 110 positions, celles
du jugement R1). Par couche, chaque position envoie son entrée à 4 experts sur 32 : en moyenne 766
entrées de calibration et 639 d'évaluation par expert.

---

## 2. Où est le bruit, où est la structure

### 2.1 Le signe des zéros : du bruit pur

Comptes exacts sur les 72 tenseurs d'experts de gpt-oss-20b (19 110 297 600 poids,
`journaux/zero-compte-20b.json`) [mes.] :

| | +0 (code 0) | −0 (code 8) | H(signe \| zéro) | H(code) | H(valeur) | écart |
|---|---|---|---|---|---|---|
| 72 tenseurs | 6,3920 % | 6,3929 % | **0,9999999967 bit** | 3,8638 | 3,7360 | **0,1278 bit par poids** |
| 12 tenseurs de 07 | 6,8464 % | 6,8475 % | 0,99999999 bit | 3,8598 | 3,7228 | 0,1369 |
| **gpt-oss-120b**, 108 tenseurs (114 661 785 600 poids) | 6,2779 % | 6,2789 % | 0,9999999951 bit | 3,8667 | 3,7411 | **0,1256 bit par poids** |

Par tenseur, l'écart va de 0,117 à 0,196 bit par poids sur 20b, de 0,115 à 0,239 sur 120b. Aucun bloc
n'a ses 32 codes nuls (0 sur 597 196 800 pour 20b, 0 sur 3 583 180 800 pour 120b) : l'échelle d'un
bloc n'est jamais un synonyme. Journaux : `zero-compte-20b.json`, `zero-compte-120b.json`.

**Pourquoi le signe d'un zéro est aléatoire** [calculé, lecture] : un quantificateur MXFP4 arrondit au
plus près ; un poids d'origine de petite magnitude devient ±0 selon son propre signe, et les signes des
petits poids sont équiprobables. Le format garde ce signe parce que E2M1 code le signe à part
(spécification OCP MX). Le calcul, lui, ne le voit jamais : `K[8] = −0 = K[0]`.

### 2.2 L'énergie est concentrée

Sur les 12 tenseurs de référence (`journaux/borne-rd-passe1.json`, champ `exposants`) [mes.] : les
blocs d'exposant 129 portent 54,8 % de l'énergie pour 5,3 % des poids ; 129 et 130 ensemble, 74,2 %
pour 5,8 % ; les huit exposants les plus lourds, 96,9 % pour 14,6 %. L'**erreur relative poolée** sur
les poids, la métrique de la frontière (4,29 %), est donc dominée par une petite part des blocs. Une
allocation du débit qui ne servirait que ces blocs « battrait » la frontière dans cette métrique tout
en détruisant 85 % des poids : **la métrique des poids n'est pas un juge**, d'où le jugement sur la
sortie des experts (§ 5).

### 2.3 La borne d'un codeur sans mémoire

Voir § 3.

---

## 3. La borne distorsion-débit dans le domaine des poids

**Le modèle** [calculé] : `w = s·v`, `v` i.i.d. de loi p sur les 15 valeurs (±0 fusionnés),
`s = 2^(e−128)` connue. Distorsion relative `D = Σ s²(v − v̂)² / Σ s² v²`. La courbe R(D) de la source
discrète v se calcule par Blahut-Arimoto (Blahut 1972) : pour une pente β (bits par unité de
distorsion), on itère
`Q(ŷ | v) ∝ q(ŷ) 2^(−β (v − ŷ)²)`, `q(ŷ) = Σ_v p(v) Q(ŷ | v)` jusqu'au point fixe, puis
`R = Σ p(v) Q(ŷ|v) log2(Q(ŷ|v)/q(ŷ))`, `D = Σ p(v) Q(ŷ|v)(v − ŷ)²`. Une allocation **uniforme**
(la même pente pour tous les blocs) est le cas d'un quantificateur unique, celui de la frontière.

**Témoins et histoire des passes** : passe 1, B1 tombe au bout bas (à β = 1e-6, Blahut-Arimoto
demande de l'ordre de 1/β itérations ; le point n'était pas convergé) ; B2 tient (la gaussienne suit
2^(−2R) à 1e-5 bit) et sa cassure tombe. Passe 2, avec la correction déclarée après la chute (un point
de distorsion supérieure à E[v²] est remplacé par le point de débit nul) : B1bis et B2 tiennent, mais
243 points sur 1 619 seulement ont convergé et la courbe à allocation optimale se lisait hors de son
domaine : elle n'est pas publiée. Passe 3 : points uniformes convergés seulement (résultats ci-dessous).

**Les points publiés, et pourquoi ce sont des bornes même sans convergence.** Dans la zone de 1,8 à
3,2 bits, Blahut-Arimoto n'a pas atteint la tolérance déclarée (1e-11) en 200 000 itérations ; par la
règle déclarée avant la passe 3, aucun nombre « convergé » n'est donc publié pour 2,642 bits ou
4,29 %. Ce qui reste vrai sans convergence, et que je publie à la place (lecture déclarée après la
passe 3, raison ci-dessous) : **chaque itéré est un point atteignable**. *Lemme* : pour tout canal de
test Q(ŷ|v) et toute loi q sur les reproductions, `Σ p(v) Q(ŷ|v) log2(Q(ŷ|v)/q(ŷ)) ≥ I(V ; Ŷ)` (égalité
si q est la marge de Q ; c'est l'écart de Kullback-Leibler entre la marge et q, toujours ≥ 0 ; Cover
et Thomas, § 10.8) ; et `I(V ; Ŷ) ≥ R(D)` pour `D = E d(V, Ŷ)` (définition de R(D)). Donc chaque
point (R calculé, D calculé) est au-dessus de la courbe R(D) : **R(D) ≤ R calculé**. Par le théorème
de codage de source avec distorsion, tout débit au-dessus de R(D) est atteignable par des codes assez
longs.

Points de la passe 3 (`journaux/borne-rd.json`, champ `uniforme_precis`, allocation uniforme : un
seul quantificateur pour tous les blocs, comme la frontière) [mes., bornes supérieures de R(D)] :

| Débit (bits par poids) | Distorsion relative D | Lecture |
|---|---|---|
| 2,1284 | 4,55 % | ≈ l'erreur de la frontière, 0,51 bit de moins |
| 2,2631 | 3,67 % | sous la frontière en débit ET en erreur |
| 2,5091 | 2,38 % | |
| **2,6095** | **1,96 %** | au débit de la frontière (2,64), moins de la moitié de son erreur |

Par interpolation entre les deux premières lignes, R(4,29 %) ≤ ≈ 2,17 bits [calculé].

**Ce que cela veut dire.** Un codeur qui ne regarde que les poids, idéal, sans mémoire entre poids
(l'hypothèse que 03 a mesurée vraie à 0,005 bit près), pourrait atteindre l'erreur de la frontière avec
**environ 0,47 bit de moins**, ou, à son débit, **moins de la moitié de son erreur**. Ce gain n'est pas
dans une structure des poids : il est dans **la forme du quantificateur**. La frontière est contrainte
d'être une fonction du code (pour qu'un complément rende le code exact) et scalaire ; l'écart à la
borne se partage entre le gain d'un quantificateur scalaire à contrainte d'entropie (la variante
`ecsq`, § 5) et le gain de pavage d'un code vectoriel ou en treillis (au plus 0,254 bit, § 2.7 de
genome/00). **Un générateur de poids (graine, automate, dictionnaire) ne peut que viser cette même
borne** : il n'a pas d'autre structure à exploiter.

**Allocation entre exposants.** L'énergie étant concentrée (§ 2.2), une allocation non uniforme (plus
de débit aux blocs lourds) abaisse encore la borne de la métrique poolée ; la passe 2 l'a calculée hors
de son domaine (μ trop petit pour les petits exposants), elle n'est pas publiée. Retenu : la métrique
poolée des poids récompense le sacrifice des blocs légers, et ne peut pas servir de juge.

---

## 4. Mécanisme 1 : le codon synonyme du zéro

### 4.1 Le vivant

Le code génétique a 64 codons pour 20 acides aminés et un signal d'arrêt : il est **dégénéré**, et
les codons synonymes ne changent pas la protéine. Le code MXFP4 a 16 codes pour 15 valeurs : il est
dégénéré **une fois**, au zéro. Une partie du génome ne code rien ; ici, 0,128 bit par poids du
fichier code un signe que personne ne lit.

### 4.2 Le mécanisme

Avant le codage entropique, chaque demi-octet 8 (−0) devient 0 (+0). Le décodeur ne change pas : il
rend le code canonique, et la table du flux n'a plus de fréquence pour 8 (dans l'alphabet octet de
A_ctx, 256 symboles deviennent 225 possibles). **Coût de transcription nul.**

**Proposition (exactitude au bit des produits).** Soit `y = Σ_j w_j x_j` calculé dans un ordre fixé
en virgule flottante IEEE 754 (arrondi au plus près), et `w'` égal à `w` sauf `w'_j = +0` là où
`w_j = −0`. Si au moins un terme `w_j x_j` est non nul, alors `y' = y` au bit.
*Démonstration* : par récurrence sur les sommes partielles `S_k`. Tant que `S_k` est nul, son signe
peut différer (`(+0) + (−0) = +0` mais `(−0) + (−0) = −0`) ; au premier terme non nul `t`,
`S_{k+1} = S_k + t = t` exactement dans les deux calculs (`±0 + t = t` pour `t ≠ 0`), et les deux
suites coïncident ensuite puisque les opérandes sont égaux. Un terme `(±0)·x_j` vaut ±0 et ne change
jamais une somme partielle non nulle (`S + (±0) = S` pour `S ≠ 0`). ∎ Dans un noyau entier
(valeurs E2M1 doublées en entiers signés), −0 et +0 sont déjà le même entier 0. Un produit scalaire
de 2 880 termes dont aucun n'est non nul n'arrive pas dans gpt-oss (aucun bloc nul, § 2.1) ; s'il
arrivait, seul le signe d'un zéro de sortie changerait, puis disparaîtrait au biais (non nul) de
l'expert.

### 4.3 Les mesures

| Mesure | Sans le codon synonyme (F1) | Avec | Écart | Statut |
|---|---|---|---|---|
| A_ctx, tout compris (12 tenseurs) | 3,843137 | **3,706142** | **−0,136995** (−3,56 %) | mes. (`zero-canonique.json`), décodage exact |
| codes A_ctx seuls | 3,805616 | 3,668621 | −0,136995 | mes. |
| A_flux (format de 03) | 3,843442 | 3,706406 | −0,137036 | mes. |
| tronçon moyen (20b, aligné 4 Kio) | 11 990 368 o | 11 564 160 o | −3,55 % | mes. |
| demi-octets réécrits | — | 218 097 443 sur 3 185 049 600 | 6,85 % | mes. |
| base seule (niveau 0 de B) | 2,606647 | 2,559045 | −0,047602 | mes. (voir § 4.4) |
| logits f64, 24 jetons | — | 0 sur 4 826 112 différents au bit | — | mes. (`temoin-zero.json`) |

**Seuil, déclaré avant** (en tête de `zero-synonyme/src/main.rs`, commité avant la passe) : bat la
frontière si A_ctx descend d'au moins 0,05 bit par poids. **Mesuré : 0,137. Il bat la frontière.**

**Sur gpt-oss-120b** [calculé depuis la mesure] : 0,1256 bit par poids de signe de zéro sur 114,66
milliards de poids d'experts, soit **1,80 Go** qu'aucun calcul ne lit (114 661 785 600 × 0,1256 / 8 =
1,800·10⁹ octets), sur les 60,9 Go du fichier `.trc` sans perte (03) : −3,0 %. Le codeur réel n'a été
passé que sur 20b ; sur 20b il rend l'entropie à 0,00004 bit près (0,136995 contre 0,1369).

**Le toit** [calculé] : les octets d'experts lus par jeton baissent de 3,56 % ; à disque limitant, le
toit monte de 1/(1 − 0,0356) − 1 = **+3,7 %**, sans rien changer d'autre.

### 4.4 Le même codon dans la base de B

Dans la base (signe et classe), un zéro garde son signe : la classe {0 ; 0,5} se reconstruit en
±0,237·s. Sur le code canonique, ce signe n'est plus stocké (−0,0476 bit, ligne « base seule ») ; le
décodeur peut le **tirer d'un hachage de la position** (splitmix64 de r·C + c), sans lire un bit.
L'erreur sur les poids est la même au poids près (|0 − (±0,237 s)| ne dépend pas du signe) ; l'erreur
de sortie est mesurée par la variante `frontiere0` (§ 5).

---

## 5. Mécanisme 2 : la mutation synonyme

### 5.1 Le vivant, et ce qu'on en transpose

Le code génétique n'est pas une fonction quelconque des codons vers les acides aminés : parmi un million
de codes possibles, le code naturel est l'un des meilleurs pour que **les erreurs les plus probables
tombent sur des acides aminés semblables** (Freeland et Hurst 1998). Le neurone, lui, code un signal
continu en impulsions en **reportant son erreur** sur la suite (modulation sigma-delta, Yoon 2017).
Transposé : le « phénotype » d'une matrice d'expert est sa sortie W x sur les entrées que le modèle
lui donne vraiment ; une erreur de poids dans une direction que ces entrées n'excitent pas est une
**mutation synonyme**. Le mécanisme choisit les symboles de la base pour que l'erreur aille là.

### 5.2 La dérivation

Pour une matrice W (R lignes, C colonnes) et ses entrées x (poids de routeur g), l'erreur de sortie
d'une reconstruction Ŵ vaut, sur la loi des entrées,
`E[g² ‖(W − Ŵ) x‖²] = tr((W − Ŵ) H (W − Ŵ)ᵀ)`, avec `H = E[g² x xᵀ] / E[g²]` (normalisée).
Les lignes de W sont indépendantes : on traite chaque ligne w comme un problème
`min_q (w − q)ᵀ H (w − q)`, q parcourant les reconstructions permises colonne par colonne
(± centre[k] · s_b, s_b l'échelle E8M0 du bloc de la colonne).

**Lemme (rétroaction d'erreur optimale, OBS/OBC).** Si l'on fixe la colonne j à q_j et qu'on laisse
libres les colonnes suivantes F, l'accroissement minimal de l'erreur est
`(w_j − q_j)² / [H_F⁻¹]_jj`, atteint en corrigeant les colonnes libres de
`δ_F = −(w_j − q_j) [H_F⁻¹]_{F j} / [H_F⁻¹]_jj`. (Hassibi et Stork 1992 ; Frantar et al. 2022.)
*Démonstration* : minimiser `(w − q)ᵀ H (w − q)` sous la contrainte `e_jᵀ (w + δ) = q_j` par un
multiplicateur de Lagrange donne `δ = −((w_j − q_j)/[H⁻¹]_jj) H⁻¹ e_j` et l'accroissement
`(w_j − q_j)²/[H⁻¹]_jj`. ∎
Dans l'ordre des colonnes 1, …, C, les quantités `[H_F⁻¹]_jj` et `[H_F⁻¹]_{F j}` sont les lignes du
facteur de Cholesky supérieur U de H⁻¹ (Uᵀ U = H⁻¹) : `[H_F⁻¹]_jj = U_jj²` et la correction est
`−((w_j − q_j)/U_jj) U_{j, F}` (GPTQ). Je calcule U par une seule factorisation : si P renverse
l'ordre et P H P = L Lᵀ, alors U = P L⁻¹ P (démonstration en tête de `facteur_inverse`, et vérifiée :
écart 7·10⁻¹⁴ au facteur direct).

**La contrainte d'entropie.** Le symbole de la colonne j minimise
`(|w_j| − c_k s_b)² + λ c̄ U_jj² ℓ(k)`, ℓ(k) = −log2 p(k) sa longueur de code sous la loi de la base
frontière du tenseur, c̄ l'erreur moyenne par poids de la frontière dans les unités de H ; divisé par
U_jj², c'est « accroissement de l'erreur de sortie + λ c̄ bits ». λ = 0 : la rétroaction seule.

**Le témoin qui sait tomber.** Avec H = I (et λ = 0), U = I, aucune correction, chaque poids prend le
centre le plus proche : comme les centres sont les centres de gravité d'une partition contiguë, le
plus proche est celui de sa classe, et la mutation synonyme rend **exactement** la frontière (T1 :
0 symbole différent ; avec le H réel, 1 789 132 différents).

**Le décodeur ne change pas** : mêmes huit symboles, mêmes quatre centres, mêmes échelles. Le
mécanisme vit tout entier dans le codeur ; son coût de transcription est **nul**.

### 5.3 Le protocole

- Experts : couches 0, 8, 16, 23 ; experts 0, 4, …, 28 (96 matrices, 796 M poids) ; passes plus
  tardives sur un sous-ensemble déclaré (SYN_EXPERTS).
- Calibration : fenêtres 10 à 21 de wiki.test ; évaluation tenue à l'écart : fenêtres 0 à 9 ; erreurs
  de sortie pondérées par g² ; erreur de sortie d'**expert** : les trois matrices remplacées, la
  SwiGLU bornée de gpt-oss entre elles.
- Critère déclaré avant (tête de `synonyme.py`) : débit ≤ frontière (même estimateur) et erreur de
  sortie d'expert plus basse sur chacune des deux moitiés de l'évaluation et dans chacune des quatre
  couches.

### 5.4 Les résultats

**Le premier échec, et son pourquoi : le sur-apprentissage.** La passe déclarée (λ = 0, δ = 0,01,
l'amortissement de GPTQ) **ne bat pas** la frontière : débit 2,6789 bits (H0) contre 2,6381, et, sur
l'évaluation tenue à l'écart, la couche 0 est pire (0,094/0,067 contre 0,059/0,052 d'erreur de sortie
d'expert, moitiés 1 et 2) [mes., `passes/synonyme-lam0-damp0.01.json`]. Le diagnostic (hypothèse et
prédictions déclarées avant, `journaux/diagnostic-L0-E0.json`) l'explique par un nombre : chaque expert
ne reçoit que **≈ 766 entrées de calibration en dimension 2 880** ; la covariance estimée est de rang
≤ 766 et la rétroaction pousse l'erreur dans les ≈ 2 100 directions que l'échantillon ne voit pas, mais
que l'évaluation excite. Mesuré sur la matrice gate de l'expert 0, couche 0 : erreur de sortie en
calibration **0,21 %**, en évaluation **4,38 %**, frontière 3,49 %. Prédictions (1) et (2) tenues :
l'écart calibration/évaluation existe, et il se resserre avec δ (δ = 1 : 0,72 % et **2,74 %**).
Prédiction (3) **tombe** : avec la moitié des entrées, l'évaluation n'empire pas (δ = 0,01 : 4,01 %
contre 4,38 % ; δ = 1 : 2,82 % contre 2,74 %). Le défaut n'est donc pas d'abord le nombre d'entrées,
c'est le manque de régularisation de H : à δ = 0,01, la rétroaction fait confiance à des directions
mal estimées, quelle que soit la taille de l'échantillon dans cette gamme. Médiane sur les 96 matrices : rapport synonyme/frontière **0,044 en calibration, 0,84 en
évaluation**. *Le synonyme d'un échantillon n'est pas le synonyme de la loi.*

**Le choix de δ sans regarder l'évaluation** (`journaux/choix-delta.json`, procédure déclarée avant) :
experts 2 des quatre couches (hors des experts mesurés), calibration coupée en deux (fenêtres 10-15
pour ajuster, 16-21 pour juger), δ ∈ {0,1 ; 0,3 ; 1 ; 3 ; 10} : rapport moyen 0,623 ; 0,563 ;
**0,538** ; 0,553 ; 0,589. **δ* = 1** (H + moyenne(diag H)·I : la covariance mesurée, rapprochée de
l'isotropie à poids égal).

**λ = 0, δ* = 1** (8 experts par couche, `passes/synonyme-lam0-damp1.json`) [mes.] :

| | Frontière | Synonyme λ=0 | Rapport |
|---|---|---|---|
| débit H0 des symboles (bits) | 2,6381 | 2,6488 | +0,011 |
| débit H(symbole \| κ) | 2,5953 | 2,6079 | +0,013 |
| erreur relative sur les poids (gate, up, down) | 4,40 / 4,25 / 4,40 % | 4,71 / 4,55 / 4,76 % | ×1,07 |
| erreur de sortie des matrices, évaluation | 3,16 / 3,60 / 2,89 % | 1,72 / 1,99 / 2,21 % | médiane ×0,59 |
| erreur de sortie d'expert, moitiés 1 / 2 | 3,03 / 2,53 % | **0,84 / 0,65 %** | ×0,28 / ×0,26 |
| couche 0 (m1 / m2) | 5,85 / 5,19 % | 5,10 / 4,12 % | |
| couche 8 | 13,57 / 15,19 % | 5,96 / 6,62 % | |
| couche 16 | 7,87 / 8,47 % | 3,65 / 3,69 % | |
| couche 23 | 3,01 / 2,51 % | 0,83 / 0,64 % | |
| experts améliorés | — | **32 sur 32** (médiane ×0,67) | |

L'erreur de sortie baisse partout, mais le débit monte de 0,011 bit : **au critère strict déclaré
(débit ≤), λ = 0 ne bat pas encore** ; d'où la contrainte d'entropie.

**λ = 1, δ* = 1** (experts 0, 8, 16, 24 par couche, sous-ensemble déclaré avant la passe ; la frontière
refaite sur les mêmes experts, `passes/*-e0_8_16_24.json`) [mes.] :

| | Frontière (mêmes experts) | **Synonyme λ=1** | Écart |
|---|---|---|---|
| débit H0 des symboles (bits) | 2,6415 | **2,5634** | **−0,078** |
| débit H(symbole \| κ) | 2,5989 | 2,5232 | −0,076 |
| débit lu, H0 + échelles (0,0375) | 2,679 | **2,601** | −0,078 |
| erreur relative sur les poids | 4,26 / 4,20 / 4,44 % | 4,83 / 4,59 / 5,20 % | **plus haute** |
| erreur de sortie des matrices, évaluation | 3,18 / 3,48 / 2,72 % | 1,78 / 1,94 / 2,09 % | médiane ×0,60 (43 sur 48 mieux) |
| erreur de sortie d'expert, moitié 1 / 2 | 3,94 / 3,14 % | **1,18 / 0,74 %** | ×0,30 / ×0,24 |
| couche 0 | 5,50 / 4,87 % | 5,32 / 4,29 % | ×0,97 / ×0,88 |
| couche 8 | 26,80 / 25,11 % | 10,70 / 10,44 % | ×0,40 / ×0,42 |
| couche 16 | 4,92 / 5,14 % | 2,98 / 3,11 % | ×0,61 / ×0,61 |
| couche 23 | 3,92 / 3,12 % | 1,17 / 0,73 % | ×0,30 / ×0,23 |
| experts améliorés | — | 14 sur 16 (médiane ×0,73 ; pire ×1,10) | |
| complément exact H(code \| symbole) | 1,219 | 1,689 | +0,47 |

**Au critère déclaré avant** (débit ≤ frontière, erreur de sortie d'expert plus basse sur chacune des
deux moitiés et dans chacune des quatre couches) : **8 cases sur 8, à 0,078 bit de moins. La mutation
synonyme bat la frontière avec perte.** La marge la plus mince est la couche 0 (×0,97 sur la moitié 1).

**Ce que cela dit de la structure.** L'erreur sur les poids **monte** (4,3 → 4,9 %) pendant que
l'erreur de sortie est divisée par trois à quatre : la structure exploitable n'est pas dans les poids
(§ 2-3), elle est dans les **entrées** ; les poids sont du bruit vu d'eux-mêmes, et une base dont
l'erreur est rangée dans les directions muettes des entrées en coûte moins.

**Le prix, dit en un chiffre** : le complément exact derrière la base coûte 1,689 bit au lieu de 1,219
(la base n'est plus une fonction du code, H(base | code) > 0). Lu en deux niveaux, l'expert exact
coûterait 2,564 + 1,689 = 4,25 bits au lieu de 3,86 : **la mutation synonyme n'est pas un niveau 0 de
la découpe base + complément**. Son usage est celui d'un **second génome** : un fichier exact
(le code canonique, 3,706 bits, § 4) et une base synonyme séparée (2,60 bits lus), le disque payant la
place des deux (≈ 6,3 bits par poids stockés) mais ne lisant que l'un des deux par défaut d'expert.
C'est le « mode rapide et mode exact » de Stone (idees/…, § 5 quater) : la base synonyme sert le mode
rapide ou le brouillon spéculatif, le fichier exact vérifie.

**L'expert aberrant** (couche 8, expert 24) : erreurs de matrices modestes (frontière 2,4 à 3,9 %), mais
erreur de sortie d'expert **67,6 %** ; synonyme λ=0 : 18,9 %. La sortie de cet expert est petite devant
ses termes intermédiaires (compensation entre la SwiGLU et down) : une petite erreur relative en amont
devient grande en aval. Il pèse lourd dans la couche 8 et il est le premier candidat à rester exact.

---

## 6. Le jugement de bout en bout : la KL contre la référence f64

**Le protocole** (`capture/` sous-commande `kl`, puis `juge kl` du lot R) : les 10 fenêtres de R1
(2 550 positions notées), la référence f64, les experts 0, 4, …, 28 des couches 0, 8, 16 et 23
remplacés par leur base (32 experts sur 768, chacun servi à chaque position qui le route), contre le
fichier de logits `ref-openai-20b.kld` de R1. Deux passes : la base frontière, et la mutation synonyme
(λ = 0, δ* = 1 ; écrite avant le résultat de λ = 1 : c'est la variante à débit +0,011 bit, dont les
erreurs de sortie sont du même ordre que celles de λ = 1). Seuil, déclaré avant : la mutation
synonyme est meilleure de bout en bout si sa KL moyenne est sous celle de la frontière et si son taux
de premier choix identique est au-dessus.

**Résultats** (`journaux/kl-frontiere-juge.json`, `journaux/kl-synonyme-d1-juge.json`, position par
position dans `kl-*-positions.csv`) [mes.] :

| 2 550 positions, 32 experts sur 768 remplacés | Base frontière | **Mutation synonyme** | Écart |
|---|---|---|---|
| KL moyenne (± incertitude du juge) | 0,0360 ± 0,0029 | **0,0262 ± 0,0026** | −27 % |
| KL médiane | 0,0088 | **0,0038** | −56 % |
| KL 90e centile | 0,061 | 0,037 | −40 % |
| KL 99e centile | 0,495 | 0,410 | −17 % |
| KL 99,9e centile | 1,59 | 1,70 | +7 % (queue) |
| premier choix identique (Wilson 95 %) | 87,1 % [85,8 ; 88,4] | **90,9 % [89,7 ; 91,9]** | intervalles disjoints |
| perplexité (référence 460,2) | 485,9 (+5,4 %) | **468,3 (+1,8 %)** | ÷3 |

**Au seuil déclaré** (KL moyenne plus basse et premier choix plus haut) : **tenu**. L'écart des
moyennes (0,0098) vaut environ 3,6 fois l'incertitude d'une moyenne ; la comparaison n'est pas
appariée (le juge `comparer` du lot R le ferait position par position). La queue extrême (99,9e
centile) ne baisse pas : les positions les plus touchées sont celles où le routage bascule (R1 : les
bascules de routage sont le premier amplificateur), et une base meilleure ne les supprime pas.

**Ce que la KL dit de la frontière elle-même** : remplacer seulement 32 experts sur 768 (4 % des
experts, dans 4 couches sur 24) par la base de 2,64 bits coûte déjà une KL de 0,036, **six fois** le
seuil de B (0,0055, fondations/07 § 4.2) ; la mutation synonyme la ramène à 0,026, encore
quatre fois au-dessus. Une base servie sans précaution reste chère en qualité : la base synonyme est un
**mode rapide** ou un **brouillon**, pas un remplaçant silencieux du mode exact.

---

## 7. Verdict

| Mécanisme | Bits par poids lus | Erreur | Verdict au seuil déclaré |
|---|---|---|---|
| Frontière sans perte (F1) | 3,8431 | 0 | référence |
| **Codon synonyme du zéro** | **3,7061** (rANS réel, 12 tenseurs) ; −0,128 bit sur tout 20b, −0,126 sur tout 120b | **0** (logits identiques au bit sur 2 550 positions, fichier `.kld` égal octet pour octet) | **bat la frontière sans perte** (seuil 0,05 bit) |
| Base frontière (07, F1) | 2,6441 (rANS) ; 2,679 à l'estimateur H0 + échelles | poids 4,29 % ; sortie d'expert 3,9 / 3,1 % (sous-ensemble de 4 experts) | référence |
| Base frontière sur code canonique, signe des zéros haché | 2,5965 (rANS réel, `zero-canonique.json`) | poids 4,29 % (identique au poids près) ; sortie non mesurée (passe arrêtée) | égale en erreur sur les poids à −0,048 bit ; non jugée sur la sortie |
| ECSQ λ = 0,5 (sans rétroaction) | 2,615 (H0) | sortie d'expert 3,18 / 2,72 % contre 3,03 / 2,53 | ne bat pas (glisse le long de la courbe) |
| Mutation synonyme λ = 0, δ = 0,01 (déclarée) | 2,679 (H0) | sortie d'expert 1,03 / 0,79 %, couche 0 pire | **ne bat pas** (débit plus haut, sur-apprentissage) |
| Mutation synonyme λ = 0, δ* = 1 | 2,649 (H0) | sortie d'expert 0,84 / 0,65 % contre 3,03 / 2,53 | ne bat pas au critère strict (+0,011 bit), bat en erreur partout |
| **Mutation synonyme λ = 1, δ* = 1** | **2,563 (H0), −0,078** | **sortie d'expert 1,18 / 0,74 % contre 3,94 / 3,14 %, 8 cases sur 8** ; KL (variante λ = 0) 0,026 contre 0,036 | **bat la frontière avec perte** |

**Pourquoi ça marche, chiffré.** Vu des poids, gpt-oss est du bruit : codes indépendants à 0,005 bit
près, signe des zéros à 1,0000 bit d'entropie, et une borne distorsion-débit que seuls un meilleur
quantificateur ou un code vectoriel approchent (§ 3), sans rien à « générer ». Les deux mécanismes qui
gagnent n'ajoutent aucune structure aux poids : le premier **retire de l'information que le calcul ne
lit jamais** (le signe des zéros), le second **déplace l'erreur là où les entrées réelles ne la voient
pas**. Les deux sont des synonymes au sens du code génétique : des différences de code sans
différence de phénotype.

---

## 8. Pistes (la suite, par ordre de gain attendu)

1. **Porter le codon du zéro dans le format `.trc`** (v1.2) : −3,6 % d'octets lus, coût de
   transcription nul, aucune perte ; seule décision : l'empreinte d'un expert décodé se calcule sur le
   code canonique. Mesure à refaire sur le moteur : jetons par seconde et logits au bit (J1).
2. **Le second génome** : une base synonyme (λ ≈ 1, 2,60 bits lus) à côté du fichier exact canonique,
   servie aux défauts d'expert (architecture B3) ou comme **brouillon** du décodage spéculatif vérifié
   par le chemin exact (idée de Stone, § 5 quater). Mesures : KL de bout en bout avec **tous** les
   experts substitués (768), puis jetons par seconde.
3. **Plus d'entrées de calibration** : l'écart calibration/évaluation reste ×3,5 à δ* = 1 (médiane
   0,17 contre 0,59 par matrice) ; 4 à 10 fois plus de fenêtres (texte varié, pas seulement
   wiki.test) devraient rapprocher l'évaluation de la calibration. Et une régularisation apprise
   (Ledoit-Wolf) au lieu d'un δ global.
4. **La rétroaction à travers la SwiGLU** : la passe traite gate, up et down séparément, avec les
   entrées exactes de down ; une passe séquentielle (down calibré sur les sorties de gate et up déjà
   quantifiés) et un traitement spécial des experts aberrants (couche 8, expert 24 : 67,6 % d'erreur de
   sortie pour 3 % d'erreur de matrice) devraient gagner encore.
5. **Mutation synonyme à 1 bit de magnitude** (synonyme1, 4 symboles, ≈ 1,96 bit) : passe lancée puis
   **arrêtée après 2 experts** pour laisser la machine à la KL (`passes/synonyme1-ARRETEE-2-experts.log`) :
   erreur de sortie d'expert 20,5 % et 19,5 % (couche 0, experts 0 et 8) contre 25,7 % et 25,1 % pour la frontière à 1 bit sur les mêmes experts ; la frontière à 1 bit fait 18
   à 20 % en tout (`passes/frontiere1-lam0-damp0.01.json`, 1,994 bit lus). À refaire en entier.
6. **Un codeur rANS réel des symboles synonymes** : le débit publié est l'entropie (H0 et H | κ) ; F1
   montre que le codeur réel rend 2,6441 pour une entropie conditionnelle de 2,6066 plus les échelles :
   même surcoût attendu, à mesurer.
7. **Le noyau** : aucun, le décodeur de la base existe (Tome II) ; seul le codeur (la rétroaction, ≈ 10 s
   par matrice sur le processeur, O(C²R)) est à écrire en Rust ou en CUDA pour coder 120b en heures.

---

## 9. Recettes (pour RECETTES.md)

- **Réécrire −0 en +0 avant le codage entropique d'un code MXFP4** : marche (−0,137 bit, exact au bit),
  parce que le signe des zéros est de l'entropie pure que le calcul ne lit pas.
- **Juger une base avec perte sur la sortie des experts, entrées réelles tenues à l'écart** : seul juge
  qui distingue ; l'erreur poolée sur les poids est dominée par 6 % des blocs et récompense de mauvais
  choix.
- **GPTQ avec δ = 0,01 sur des experts de MoE** : échoue (sur-apprentissage, ≈ 766 entrées en
  dimension 2 880) ; **δ choisi par validation croisée sur la calibration seule** (δ* = 1) : marche.
- **Contrainte d'entropie dans la rétroaction** : marche (λ = 1 : −0,078 bit sans perdre le gain de
  sortie) ; **ECSQ sans rétroaction** : ne gagne presque rien (la frontière est déjà près de l'ECSQ).
- **Blahut-Arimoto aux pentes faibles** : ne converge pas en 3 000 itérations (≈ 1/β) ; lire ses
  itérés comme bornes supérieures de R(D) (lemme du § 3), pas comme la courbe.
- **Facteur de Cholesky de H⁻¹ par renversement** : une factorisation au lieu de deux (écart 7·10⁻¹⁴).
- **Suite de Weyl comme hachage de position** : échoue (lignes voisines presque égales) ; splitmix64 :
  marche (corrélation 0,01, au bruit).
- **Lancer plusieurs passes Python lourdes en parallèle sur la machine partagée** : à éviter (de 20 à
  500 s par expert) ; une boucle tuée laisse ses enfants vivants sous Windows.

---

## Ce qui pourrait être faux

- **Le codon du zéro et l'empreinte des experts** : le format `.trc` vérifie l'empreinte de chaque
  expert décodé contre les octets du GGUF ; un expert canonique a d'autres octets. Il faut une
  empreinte du code canonique (ou des valeurs), une décision de format à écrire, pas une mesure.
- **L'exactitude au bit** est démontrée pour un produit scalaire IEEE à ordre fixé et mesurée sur 24
  jetons de la référence f64 ; les noyaux CUDA de troncons sont en entiers ou en flottants à ordre fixé
  (Tome II ch. 05) : la même proposition s'y applique, mais n'y est pas encore mesurée.
- **Le sous-ensemble** : 4 couches sur 24, 8 puis 4 experts sur 32 par couche ; le gain de la mutation
  synonyme varie beaucoup d'une couche à l'autre (×0,97 à ×0,23) ; une couche où il s'inverserait
  n'est pas exclue. La KL (§ 6) ne substitue que 32 experts sur 768.
- **L'estimateur de débit** de la mutation synonyme est l'entropie (H0 ou H | κ), pas un codeur réel ;
  pour la frontière, le codeur réel de F1 rend 2,6441 contre 2,6066 + échelles, et rien n'indique
  que l'écart soit différent pour les symboles synonymes, mais ce n'est pas mesuré.
- **Le δ*** a été choisi sur l'expert 2 des quatre couches ; les experts mesurés sont d'autres
  experts, mais des mêmes couches.
- **Le texte de calibration et d'évaluation** est le même corpus (wiki.test), fenêtres disjointes ; une
  évaluation sur un autre domaine (code, dialogue) pourrait réduire le gain.
- **La comparaison λ = 1** se fait sur 4 experts par couche, celle de λ = 0 sur 8 ; les deux frontières
  ont été mesurées sur leurs propres sous-ensembles.
- **La borne du § 3** suppose les codes indépendants sachant l'échelle ; une dépendance non mesurée par
  03 la ferait baisser encore (et donnerait une chance aux mécanismes génératifs).
