# Piste spectres : ce qu'il faut au mémoire (Tome III)

Dérivations écrites en entier, données en CSV, figures tirées des données commitées par un script
commité. Les chiffres sont dans `spectres.md`, lus dans `mesures/pistes/spectres/rapport.json` ;
ce fichier porte le calcul, pas les résultats.

## 1. La grandeur : la densité spectrale empirique

Pour une matrice W ∈ ℝ^{m×n}, m ≤ n (sinon on transpose), la matrice de corrélation X = WWᵀ/n a les
valeurs propres λᵢ = σᵢ²/n, σᵢ les valeurs singulières de W. La densité spectrale empirique (ESD) est
ρ_W(λ) = (1/m) Σᵢ δ(λ − λᵢ). Martin et Mahoney (arXiv 1810.01075, v1 du 2018-10-02, seule version,
résumé lu le 2026-10-21) décrivent ses formes au fil de l'entraînement (5 + 1 phases) ; dans les
réseaux de l'état de l'art, une auto-régularisation « à queue lourde » qu'ils rapprochent de
l'auto-organisation des systèmes désordonnés, faite de corrélations à toutes les échelles. L'exposant
α de la queue ρ(λ) ∝ λ^{−α} est la mesure qu'en tirent leurs travaux suivants (Martin, Peng, Mahoney,
arXiv 2002.06716, v2 du 2021-06-02, Nature Communications, DOI 10.1038/s41467-021-24025-8 : les
métriques de loi de puissance distinguent mieux que les normes les modèles bien et mal entraînés).

Changement de variable : si ρ(λ) ∝ λ^{−α}, alors avec λ = σ², ρ(σ) = ρ(λ) · |dλ/dσ| ∝ σ^{−2α} · σ =
σ^{−(2α−1)}. L'exposant d'une queue dépend donc de la grandeur ajustée ; on ajuste sur λ, comme eux.

## 2. Le témoin du hasard : la loi de Marchenko-Pastur

Pour W à entrées i.i.d. de variance s², quand m, n → ∞ avec q = m/n ≤ 1 fixe, l'ESD de X = WWᵀ/n
tend vers

  ρ_MP(λ) = √((λ₊ − λ)(λ − λ₋)) / (2π s² q λ),   λ ∈ [λ₋, λ₊],   λ± = s²(1 ± √q)².

Pour les matrices carrées (q = 1) : support [0, 4s²], densité √((4s² − λ)λ) / (2π s² λ), qui diverge
en λ^{−1/2} en 0 et s'annule en racine carrée au bord droit. **Le support est borné** : il n'y a pas de
queue, et la plus grande valeur propre ne dépasse λ₊ que de fluctuations d'ordre n^{−2/3} (Tracy-Widom).
Pour q = 512/2 880 = 0,178 (attn_k, attn_v vus par leur côté court) : λ± = s²(1 ± 0,4216)², soit
[0,334 s² ; 2,021 s²]. Un ajustement de loi de puissance sur un tel spectre ne doit rien trouver :
c'est le témoin T-MP, qui doit tomber.

Le témoin T-perm (entrées de W permutées) garde la loi marginale des entrées (et leur kurtosis, qui
peut atteindre 2 000 sur down) et détruit toute structure de rang : pour des entrées à queue lourde,
la limite n'est plus MP mais elle reste sans directions privilégiées. L'écart entre W et T-perm est
ce que l'entraînement a mis dans les directions.

## 3. La méthode de Clauset, Shalizi et Newman (arXiv 0706.1062), pas à pas

**Maximum de vraisemblance de α.** Loi continue de densité p(x) = (α − 1)/x_min · (x/x_min)^{−α}, x ≥
x_min. Log-vraisemblance de n points de la queue :
  ℓ(α) = n ln(α − 1) − n ln x_min − α Σ ln(xᵢ/x_min).
dℓ/dα = n/(α − 1) − Σ ln(xᵢ/x_min) = 0 ⇒ **α̂ = 1 + n / Σ ln(xᵢ/x_min)**. Erreur type (information de
Fisher, d²ℓ/dα² = −n/(α − 1)²) : σ_α = (α̂ − 1)/√n.

**x_min par Kolmogorov-Smirnov.** Pour chaque candidat x_min (valeurs observées, queue d'au moins 50
points), F̂(x) = 1 − (x/x_min)^{1−α̂} ; D = max_x |S(x) − F̂(x)|, S la fonction de répartition empirique
de la queue ; aux points triés t₍ⱼ₎, j = 0…n − 1 : D = max(max((j + 1)/n − F̂(t₍ⱼ₎)), max(F̂(t₍ⱼ₎) − j/n)).
On retient le x_min de D minimale.

**Concurrentes tronquées en x_min.**
- Exponentielle : p(x) = λ e^{−λ(x − x_min)} ; ℓ(λ) = n ln λ − λ Σ(xᵢ − x_min) ⇒ λ̂ = 1/(x̄ − x_min).
- Log-normale : p(x) = φ((ln x − μ)/σ) / (xσ) / (1 − Φ((ln x_min − μ)/σ)) ; pas de forme close :
  maximisation numérique sur (μ, ln σ), départs multiples, ln(1 − Φ(z)) calculé par log Φ(−z) pour
  rester exact quand z est grand.

**Rapport de vraisemblance de Vuong.** ℓᵢ = ln p_PL(xᵢ) − ln p_alt(xᵢ), R = Σ ℓᵢ. Sous l'hypothèse
« les deux lois sont aussi proches de la vraie », R/(σ̂√n) suit asymptotiquement N(0, 1) (σ̂ écart type
des ℓᵢ) ; p bilatéral = erfc(|R| / (σ̂√(2n))). R > 0 avec p petit : la loi de puissance est préférée.

**Plausibilité (p_gof).** Répliques : chaque point tiré, avec la probabilité n_queue/N, de la loi de
puissance ajustée (x = x_min u^{−1/(α̂−1)}, u uniforme), sinon tiré parmi les points sous x_min ;
x_min et α ré-estimés ; p_gof = part des répliques de D au moins égale à celle des données.

**Pourquoi la log-normale ne se laisse pas écarter (le résultat du pas 1 bis).** Dans les
coordonnées y = ln(x/x_min) ≥ 0, la log-normale tronquée a pour densité en y
  p(y) ∝ exp(−(y − m)²/(2σ²)),  m = μ − ln x_min,
c'est-à-dire une gaussienne tronquée ; la loi de puissance, une exponentielle p(y) ∝ e^{−(α−1)y}. En
développant le carré : −(y − m)²/(2σ²) = −y²/(2σ²) + (m/σ²) y − m²/(2σ²). Si m → −∞ et σ² → ∞ avec
−m/σ² → α − 1 fixé, le terme quadratique y²/(2σ²) tend vers 0 sur toute étendue bornée de y : **la
log-normale contient la loi de puissance comme limite**. Sur une queue observée jusqu'à y_max, les
deux ne diffèrent que par la courbure y²/(2σ²), qu'il faut voir au-dessus du bruit d'échantillon ;
avec y_max ≈ ln(λ_max/x_min) de quelques unités et n de quelques centaines, elle ne se voit pas.
D'où le constat mesuré (pas 1 bis) : 40 lois de puissance vraies sur 40 sont « non départagées ».

## 4. Le levier : les trois calculs

**Coût d'une part de rang r.** L̂_r = (U_rΣ_r)V_rᵀ, facteurs stockés en f16 : 16 · r · (m + n) bits pour
m n poids, soit c(r) = 16 r (m + n)/(m n) ; pour 2 880 × 2 880 : c(r) = 0,011111 · r bit par poids.

**L1 (sans perte, sur les codes MXFP4).** Le code C de 4 bits d'un poids, l'exposant E de son bloc,
B_r la case de la prédiction L̂_r/2^{E−128} (valeur E2M1 la plus proche, le zéro coupé par le signe).
Le codeur entropique idéal qui connaît E dépense H(C | E) ; s'il connaît aussi B_r (le décodeur a les
facteurs), H(C | E, B_r). Le gain est l'information mutuelle conditionnelle
  I(C ; B_r | E) = H(C | E) − H(C | E, B_r) ≥ 0,
et le gain net I − c(r). Estimateur par comptage : biais ≈ (cases non vides)/(2 N ln 2), au plus
≈ 16 · 16 · 20/(2 · 8,3·10⁶ · 0,693) ≈ 4·10⁻⁴ bit pour 8,3 millions de poids : négligeable devant le
seuil de 0,05 bit. Le signe du zéro est fondu d'abord (−0 → +0) : le levier se compte au-delà du codon
synonyme déjà construit (05 § 0).

**L2 (avec perte, borne gaussienne par rangée).** Rangée i de variance par poids vᵢ, erreur absolue
visée D_tot = D · Σᵢ n vᵢ (D = 0,044). Remplissage inverse : Dᵢ = min(θ, vᵢ), θ tel que Σ Dᵢ = D_tot/n ;
débit par poids R = (1/m) Σᵢ ½ log₂(vᵢ/Dᵢ). Avec la part de rang faible, la même formule sur les
variances de rangée de W − L̂_r (l'erreur d'arrondi des facteurs est dans le résidu, donc comptée),
plus c(r). Gain net = R(W) − R(W − L̂_r) − c(r). À haut débit, si toutes les rangées sont au-dessus de
θ, le gain brut vaut (1/m) Σ ½ log₂(vᵢ/vᵢʳᵉˢ), la moyenne des demi-logarithmes de la réduction de
variance de chaque rangée.

**L3 (avec perte, opérationnel).** Quantificateur uniforme de pas Δ, indice round(x/Δ), pas réglé
par dichotomie pour Σ (x − Δ round(x/Δ))² = D_tot ; débit = entropie empirique des indices (sans
information annexe : L3 ; conditionnelle à la rangée : L3r). À haut débit, l'ECSQ à pas uniforme est
à ½ log₂(2πe/12) ≈ 0,254 bit de la borne gaussienne, le même pour W et pour le résidu : la
différence L3 est un second chemin de la différence L2.

**L3 sur une source discrète, et pourquoi il faut un tramage.** Une matrice MXFP4 ne prend que les
valeurs k · 2^{e−128}, k ∈ {0, ±1, ±2, ±3, ±4, ±6, ±8, ±12}, e l'exposant du bloc. Un quantificateur
uniforme de pas Δ, sans tramage, envoie cette grille sur ses indices d'une façon qui dépend du
rapport entre Δ et les pas de la grille : si Δ est voisin d'un pas de la grille, plusieurs valeurs
tombent dans une même cellule ou s'alignent exactement, l'erreur n'est plus uniforme et l'entropie des
indices n'est plus h(X) − log₂ Δ. Retirer L̂_r ajoute à chaque poids une petite valeur continue et
détruit l'alignement : l'entropie change sans que la structure y soit pour rien. Le témoin permuté le
montre (§ 7 ter de seuil.md : +0,148 réel, +0,154 permuté). Le tramage soustractif u ~ U(−½, ½), connu
du décodeur, rend l'erreur (q − u)Δ − x uniforme sur [−Δ/2, Δ/2] et indépendante de x, quelle que soit
la loi de x (théorème de Schuchman ; Zamir et Feder 1992) : énergie d'erreur N Δ²/12 exactement, donc
Δ = √(12 D ‖W‖² / N). Le débit d'un codeur qui connaît u est H(q | u) = I(X ; X + ΔU) (Zamir et
Feder) ; l'outil mesure H(q), qui le majore, de peu quand la densité de X varie peu à l'échelle de Δ ;
le même majorant sert pour W et pour W − L̂_r, et c'est leur différence qu'on lit.

## 5. Données et figures

- `mesures/pistes/spectres/valeurs-singulieres.npz` : toutes les valeurs singulières.
- `ajustements.out` (CSV), `second-chemin.out` (CSV), `levier.out` (CSV), `temoins.out` (JSON).
- `fig-ccdf.csv` : fonction de survie (rang/n contre λ/λ̄) en log-log, une matrice de chaque famille
  à la couche 12, son permuté, MP et Pareto : une loi de puissance y est une droite de pente −(α − 1),
  MP une chute verticale au bord.
- `fig-alpha.csv` : α̂ ± σ_α par matrice, rangé par famille et couche, plein si « compatible ».
- `fig-levier.csv` : gain net contre le rang, par famille, réel et témoin.
- Figures pgfplots : `genome/pistes/spectres/figures/*.tex`, compilées par `lualatex`.

## 6. BibTeX

`genome/pistes/spectres/spectres.bib` (Martin et Mahoney 2018 ; Martin, Peng et Mahoney 2021 ;
Clauset, Shalizi et Newman 2009 ; Marchenko et Pastur 1967 ; Vuong 1989), à porter sous
`memoire/sources/spectres.bib` par le rédacteur (la règle de cohabitation de ce rôle garde ses
fichiers sous `genome/pistes/`, `mesures/pistes/`, `outils/pistes/`). Les pages arXiv des deux
articles de Martin et Mahoney ont été lues le 2026-10-21 ; les références de journal de CSN, MP et
Vuong sont données de mémoire et à vérifier par le rédacteur.

## 7. Le plafond spectral (seuil.md § 7 quinquies à septies)

**Le modèle.** W ∈ ℝ^{m×n}, p = min(m, n), q = max(m, n) ; on lit W comme q vecteurs gaussiens de
dimension p, centrés, de covariance C de valeurs propres λⱼ = σⱼ²/q. (Le choix de la petite
dimension n'est pas un détail : vue par sa grande dimension, une matrice 512 × 2 880 aurait 2 368
directions de variance nulle, gratuites, et un gain fictif.)

**Remplissage inverse** (Cover et Thomas, th. 10.3.3, à vérifier par le rédacteur). Pour une source
gaussienne de covariance C, à erreur quadratique moyenne totale Δ_tot par vecteur, la fonction
débit-distorsion est atteinte dans la base propre de C (la transformée de Karhunen-Loève) :
  Dⱼ = min(θ, λⱼ),  Σⱼ Dⱼ = Δ_tot,  R = Σⱼ max(0, ½ log₂(λⱼ/θ))  bits par vecteur.
Avec Δ_tot = D · Σⱼ λⱼ (erreur relative D) et p poids par vecteur, le débit par poids est
R_KLT = (1/p) Σⱼ max(0, ½ log₂(λⱼ/θ)). Il ne dépend que de la forme du spectre (invariant d'échelle).

**La base blanche, et pourquoi elle majore.** Spectre plat de même énergie : λⱼ = λ̄ pour tout j,
θ = D λ̄, R_blanc = ½ log₂(1/D) (2,2535 bits à D = 0,044). Coder sans transformée, avec les variances
par coordonnée cᵢᵢ (la diagonale de C), donne à haut débit ½ log₂((Πᵢ cᵢᵢ)^{1/p}/θ) ≤ ½ log₂(c̄/θ)
(moyenne géométrique ≤ moyenne arithmétique) ; et la transformée fait mieux encore, car
det C ≤ Πᵢ cᵢᵢ (inégalité de Hadamard). Donc R_KLT ≤ R_diag ≤ R_blanc : **le plafond
G = R_blanc − R_KLT majore le gain spectral de toute méthode**, sous ce modèle, la base étant offerte.

**À haut débit, le plafond est une mesure de platitude.** Si θ < λ_min (toutes les directions
actives) : θ = D λ̄ et R_KLT = ½ log₂(λ_g/θ), λ_g la moyenne géométrique. D'où
  **G = ½ log₂(λ̄ / λ_g)**,
le logarithme du rapport des moyennes arithmétique et géométrique : la mesure de platitude
spectrale de Gray et Markel (la même que le gain de codage d'une transformée en traitement du
signal). Il est nul pour un spectre plat, grand pour un spectre étalé, **et les petites valeurs y
pèsent autant que les grandes** (ln λ est non borné vers le bas).

**Marchenko-Pastur en forme close.** Pour la loi MP de rapport c = p/q ≤ 1 et de variance 1,
λ̄ = 1 et ∫ ln λ dμ_c = −1 − ((1 − c)/c) ln(1 − c) (−1 pour c = 1 ; résultat classique sur les
déterminants de Wishart, à vérifier par le rédacteur). À haut débit :
  G_MP(c) = (1/(2 ln 2)) · (1 + ((1 − c)/c) ln(1 − c)).
- c = 1 : G = ½ log₂ e = 0,7213 bit. À D = 0,044, la foule des λ voisins de 0 (densité en λ^{−1/2})
  passe sous θ et le plafond vaut 0,5899 (quadrature) ; il tend vers 0,7213 quand D → 0 (0,6594 à
  D = 0,01).
- c = 2 880/4 096 = 0,7031 : 1 + 0,4223 · ln 0,2969 = 0,4872, G = 0,3514 ; mesuré 0,3515 à D = 0,01.
- c = 512/2 880 = 0,1778 : 1 + 4,625 · ln 0,8222 = 0,0947, G = 0,0683 ; mesuré 0,0683 (le support
  [0,334 ; 2,021] est entièrement au-dessus de θ : la formule est exacte, l'écart est la quadrature
  et le tirage).
(Ces trois contrôles sont faits ici après coup, sur les nombres de `plafond.log` : ils ne sont pas
déclarés et ne servent pas de témoin ; le témoin déclaré est la quadrature.)

**Pareto en forme close, et pourquoi le premier témoin est tombé.** Pour λ de Pareto (λ ≥ 1,
densité (α − 1) λ^{−α}, α > 2) : λ̄ = (α − 1)/(α − 2), E ln λ = 1/(α − 1). Toutes les directions sont
actives dès que θ = D λ̄ < 1, et
  G_Pareto(α) = ½ log₂((α − 1)/(α − 2)) − 1/(2 (α − 1) ln 2).
Pour α = 2,5 : 0,7925 − 0,4809 = **0,3116** ; mesuré 0,2979 sur 2 880 tirages (une loi de variance
infinie : la moyenne d'échantillon fluctue lentement). C'est **moins** que le hasard carré (0,5899) :
une queue lourde en haut, sans foule de petites valeurs, est plus plate, au sens de ce rapport, que la
loi MP de rapport 1. L'attente « Pareto au-dessus de MP » du § 7 quinquies n'avait pas de sens ;
d'où l'amendement du § 7 sexies.

**Le témoin planté, prédit.** Rang 8 portant 30 % de l'énergie plus bruit (70 %), carré : la
version permutée est ≈ MP(1), G ≈ 0,590. Le planté : 8 directions de variance ≈ 0,3 · 2 880/8 = 108
(en unités de λ̄ = 1) et 2 872 directions de bruit, loi MP(1) d'échelle 0,7. À haut débit, le bruit
gagne ½ log₂(1/0,7) = 0,257 bit sur le même bruit à pleine variance, et les 8 pointes coûtent
≈ (8/2 880) · ½ log₂(108/0,044) ≈ 0,016 bit : **E ≈ 0,24**. Mesuré : 0,216 à D = 0,044, 0,230 à
D = 0,01 (le haut débit se rapproche quand D baisse) [mes., `plafond.log`].

**Le plafond par rang.** Offrir seulement les r premières directions : le reste est codé dans une
base quelconque de leur complément, au mieux comme un bruit blanc de variance λ̄_reste (la moyenne
des p − r dernières λ) : G_r = R_blanc − R(λ₁, …, λ_r, λ̄_reste, …, λ̄_reste). G_0 = 0, G_p = G. À haut
débit : G_r = ½ log₂(λ̄ / λ_g,r), λ_g,r la moyenne géométrique de ce spectre retouché. Payer les r
directions : b bits par coefficient de facteur, b r (m + n) bits pour m n poids,
N_r(b) = G_r − b r (m + n)/(m n) ; à 2 880 × 2 880, 0,0111 · r bit par poids à b = 16.
**Pourquoi une base complète ne se paie jamais** : r = p coûte b (m + n)/q ≥ b bits par poids
(16 bits à b = 16, 4 à b = 4), quand le plafond entier ne dépasse pas ½ log₂ e ≈ 0,72 bit pour le
hasard, et 1,8 bit pour la plus étalée des 48 matrices.

## 8. Au-delà des échelles de rangée (seuil.md § 7 nonies et decies)

**Pourquoi la base blanche ne suffit pas.** Le plafond G = R_blanc − R_KLT mélange deux choses :
l'inégalité des variances par rangée (que n'importe quel codeur prend avec une échelle par rangée,
m nombres pour m n poids) et la structure entre rangées (que seule une base propre prend). On les
sépare par la chaîne
  R_KLT ≤ R_rangée ≤ R_blanc,
où R_rangée = (1/m) Σᵢ max(0, ½ log₂(vᵢ/θ)), vᵢ = (1/n) Σⱼ wᵢⱼ², Σᵢ min(θ, vᵢ) = D Σᵢ vᵢ (le L2_0 de
`levier.py`). La première inégalité vient de ce que les vᵢ sont la diagonale de S = WWᵀ/n, dont les
valeurs propres sont σⱼ²/n : coder les coordonnées d'un vecteur gaussien une à une, avec leurs propres
variances, est un schéma permis, donc la fonction débit-distorsion de S (atteinte par la transformée de
Karhunen-Loève) ne peut pas faire pire. (À haut débit, c'est l'inégalité de Hadamard,
det S ≤ Πᵢ sᵢᵢ.) La seconde est l'inégalité des moyennes. D'où
  R_blanc − R_KLT = (R_blanc − R_rangée) + (R_rangée − R_KLT) = gain des échelles + G_rang.
Pour L00.down.E24 : R_blanc = 2,254, R_rangée = 0,755 ; le gain des échelles seules vaut 1,50 bit par
poids, pour un plafond total (base blanche) de 1,74.

**L'orientation.** L'inégalité R_KLT ≤ R_rangée ne tient que si les vecteurs de R_KLT ont pour
coordonnées les rangées, c'est-à-dire si R_KLT se calcule sur S = WWᵀ/n. Pour une matrice carrée, WWᵀ
et WᵀW ont les mêmes valeurs propres : sans objet. Pour attn_k, attn_v (512 × 2 880) et attn_output
(2 880 × 4 096), la petite dimension est celle des rangées : c'est le cas. Pour attn_q (4 096 × 2 880),
non : WWᵀ/n aurait 1 216 valeurs propres nulles, et le plafond calculé sur WᵀW n'est pas majoré par
R_rangée. Les attn_q sont rapportées sans verdict.

**Le témoin nul, et pourquoi le premier était faux.** Pour dire qu'une matrice a une structure au-delà
de ses échelles, il faut la comparer à une matrice qui a les mêmes échelles et rien d'autre. Permuter
toutes les entrées (le témoin des §§ 3 à 5) détruit aussi les échelles : la matrice permutée a des
rangées homogènes, son R_rangée ≈ R_blanc, et son G_rang garde l'artefact de Marchenko-Pastur (≈ 0,59
à D = 0,044 pour une matrice carrée). La matrice T-rangées (rangées gaussiennes d'écart type e^{1,5 z})
a, elle, G_rang = 0,022 seulement : une fois les échelles prises, presque toutes ses petites rangées
sont sous θ et ne coûtent rien, et il ne reste presque plus de spectre à aplatir. D'où un « excès »
de −0,562 qui ne veut rien dire. Le bon témoin nul est la **permutation à l'intérieur de chaque
rangée** : chaque vᵢ est conservé exactement (donc R_rangée), toute dépendance entre rangées est
détruite. Sous l'hypothèse « W = échelles de rangée × bruit sans structure », la matrice et sa version
permutée par rangée ont la même loi, et l'excès E_rang est nul aux fluctuations près.

**La queue des canaux géants (mesure exploratoire, `normalise.out`).** Si W = Λ Z, Λ = diag(ℓᵢ) des
normes de rangée très inégales et Z à rangées de norme 1 sans structure, les grandes valeurs
singulières de W suivent les grands ℓᵢ (σ₁ ≥ maxᵢ ℓᵢ, avec égalité quand la rangée dominante est presque
orthogonale aux autres). La queue de l'ESD recopie alors la loi des ℓᵢ², qui n'a aucune raison d'être
une loi de puissance. Normaliser les rangées (W ↦ Λ⁻¹W = Z) doit faire disparaître la queue ;
normaliser les colonnes, non. C'est ce que rendent down et attn_output de la couche 0 (α̂ de 1,6 à
3,4–7,0 ; σ₁ / max ℓᵢ = 1,1 à 1,4).
