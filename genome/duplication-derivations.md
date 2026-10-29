# Duplication de gènes : les dérivations entières

Sujet « duplication » de l'étude du génome des poids (idees/biomimetisme-genome-des-poids.md § 5 bis,
§ 5 ter). Chaque résultat utilisé par les mesures (`outils/genome/duplication/`) est posé ici pas à pas.
Notations : un expert de gpt-oss-20b à la couche ℓ, indice e ; d = d_modèle = 2 880, f = d_ff = 2 880 ;
W_g, W_u ∈ ℝ^{f×d} (gate, up), W_d ∈ ℝ^{d×f} (down), biais b_g, b_u ∈ ℝ^f, b_d ∈ ℝ^d.

## 1. La symétrie qui rend la parenté invisible : la permutation des neurones

**Proposition 1.** Soit Π ∈ {0,1}^{f×f} une matrice de permutation. L'expert de poids
(Π W_g, Π W_u, W_d Πᵀ, Π b_g, Π b_u, b_d) calcule la même fonction que (W_g, W_u, W_d, b_g, b_u, b_d).

*Démonstration.* L'expert calcule y = W_d σ(W_g x + b_g, W_u x + b_u) + b_d, où σ agit composante par
composante : σ(g, u)_k = s(g_k, u_k), s(g, u) = min(g, 7) · sigmoïde(1,702 · min(g, 7)) · (borne(u, −7, 7) + 1)
(trc-reference, `ops::swiglu_oai`). Une fonction appliquée composante par composante commute avec
toute permutation : σ(Π a, Π b) = Π σ(a, b). Donc
W_d Πᵀ σ(Π W_g x + Π b_g, Π W_u x + Π b_u) + b_d = W_d Πᵀ Π σ(W_g x + b_g, W_u x + b_u) + b_d = y,
puisque Πᵀ Π = I. ∎

*Conséquence.* Deux experts nés d'une même copie puis entraînés peuvent avoir leurs neurones dans un
ordre quelconque : comparer W_g^A et W_g^B rangée i contre rangée i ne voit rien. La parenté se juge
après le meilleur appariement des neurones. Il n'existe pas d'autre symétrie continue : s n'est pas
homogène (le seuil 7, la sigmoïde, le « + 1 » sur u), donc aucune mise à l'échelle d'un neurone ne se
compense par W_d. Un appariement par permutation est la seule liberté.

*Ce que la permutation fait aux blocs MXFP4.* Les blocs de 32 courent le long de l'entrée de chaque
matrice. Pour W_g et W_u (entrée d), Π permute des rangées entières : chaque bloc reste entier. Pour W_d
(entrée f), W_d Πᵀ permute les colonnes : les blocs sont traversés. Un code conditionnel position par
position reste exact dans les deux cas (§ 3).

## 2. Le gain d'un parent pour une source gaussienne (la mesure de l'écran)

Soit une rangée enfant x ∈ ℝ^n et un parent p, modèle x = α p + z, z ⊥ p, de variances par poids
σ_x², α² σ_p², σ_z². Le coefficient de corrélation est ρ = cos(x, p), et σ_z² = σ_x² (1 − ρ²)
(projection orthogonale : ‖x‖² = ‖α p‖² + ‖z‖², ‖α p‖² = ρ² ‖x‖²).

Débit-distorsion d'une gaussienne de variance σ², distorsion quadratique D < σ² (Shannon 1959) :
R(D) = ½ log₂(σ² / D) bit par composante.
- Enfant codé seul : R₁ = ½ log₂(σ_x² / D).
- Enfant codé sachant le parent (connu du décodeur) : il reste à coder z, R₂ = ½ log₂(σ_x²(1 − ρ²) / D).
- **Gain** : g(ρ) = R₁ − R₂ = −½ log₂(1 − ρ²) bit par poids, indépendant de D tant que D < σ_x²(1 − ρ²).

Valeurs : g(0,1) = 0,0073 ; g(0,2) = 0,0294 ; g(0,3) = 0,0680 ; g(0,5) = 0,2075 ; g(0,9) = 1,198 bit.
Le témoin planté de `paires_arbre.py` (ρ₀ = 0,5) rend 0,2077, celui de `ecran_parente.py` (ρ₀ = 0,9) rend
1,198 : l'instrument lit g.

**Le plancher du hasard.** Pour une cible fixée et N vecteurs indépendants uniformes sur la sphère de
ℝ^n, cos est ≈ N(0, 1/n) pour n grand, et le maximum de N valeurs absolues vaut à peu près
√(2 ln(2N) / n). Pour le dictionnaire intra (N = 31 × 2 880 = 89 280 rangées, n = 2 880) :
√(2 ln 178 560 / 2 880) = 0,0916 (calculé). Le témoin de hasard de l'écran rend 0,084 (mesuré) : du même
ordre, un peu sous la borne parce que les rangées du dictionnaire ne sont pas indépendantes. Tout ρ
trouvé au niveau de 0,08 à 0,09 n'est qu'un maximum de corrélations fortuites.

## 3. Le gain sans perte : une information mutuelle

Soit C le code E2M1 (16 symboles) d'un poids de l'enfant, κ sa classe d'échelle (F1 : signe de
e − médiane haute de la rangée, 3 classes), P le code du parent à la position appariée. Un codeur
entropique (rANS) à une table par contexte κ dépense H(C | κ) bits par poids ; à une table par (κ, P),
H(C | κ, P). Le gain est
H(C | κ) − H(C | κ, P) = I(C ; P | κ) ≥ 0,
nul si et seulement si C et P sont indépendants sachant κ (Cover et Thomas, th. 2.6.5 et 2.5.2).

**Biais de l'estimateur.** H est estimée par comptes exacts (« plug-in »). Son biais vers le bas vaut,
au premier ordre (Miller 1955), (K − 1) / (2 N ln 2) pour K cases non vides et N échantillons. Pour
H(C | κ, P) : K ≤ 3 × 16 × 16 = 768, N = 8 294 400, biais ≤ 6,7·10⁻⁵ bit. L'information mutuelle estimée
est donc gonflée d'au plus 6·10⁻⁵ bit : tout gain sous 10⁻⁴ est indiscernable de zéro.

**Les informations ajoutées, comptées.**
- La permutation : log₂(f!) bits par expert, partagés par ses trois matrices. log₂(2 880!) =
  lgamma(2 881) / ln 2 = 28 948,6 bits (calculé) ; par poids : 28 948,6 / (3 × 2 880²) = 1,163·10⁻³.
  (Second chemin, Stirling : f log₂ f − f log₂ e + ½ log₂(2π f) = 33 096,5 − 4 155,0 + 7,1 = 28 948,6.)
- Les tables : 768 comptes de 16 bits par matrice pour D1, soit 1,48·10⁻³ bit par poids ; 192 comptes
  pour D2b (κ × 8 symboles de base × 8), 3,70·10⁻⁴.
- Un parent n'est utile que si I(C ; P | κ) dépasse la somme : 2,64·10⁻³ bit par poids pour D1,
  1,53·10⁻³ pour D2b.

**Le parent de hasard n'est pas un zéro.** Apparier l'enfant à son parent par une permutation tirée au
hasard laisse en place les colonnes (gate, up : la dimension d'entrée j reste j) : toute structure
commune à TOUS les experts selon la colonne (un canal d'entrée large pour tous) survit. Le témoin de
hasard mesure cette part commune ; la part propre à la parenté est la différence
I(C ; P | κ) − I(C ; P_hasard | κ).

## 4. Le gain avec perte à reconstruction identique (D2b, D2c)

Si la reconstruction de l'enfant est fixée (la base de B, ou l'ECSQ seule), l'erreur sur les poids et
sur la sortie est fixée au bit, et seul le débit change. Pour des indices Q de la reconstruction et un
contexte parent P′ (le symbole de base du parent, ou sa prédiction quantifiée), le débit passe de
H(Q | ctx) à H(Q | ctx, P′) : le gain est I(Q ; P′ | ctx), avec les mêmes biais et les mêmes coûts
qu'au § 3. C'est la seule manière de créditer la parenté sans la confondre avec un changement de
quantificateur.

**Pourquoi la prédiction soustraite perd (D2).** Les poids de l'enfant vivent sur une grille discrète
(16 valeurs par bloc). Un quantificateur uniforme dont le pas tombe sur la grille (Δ multiple de
2^(e − 128)) rend une erreur NULLE sur une partie des poids. Le résidu x − α p n'est plus sur la grille :
son erreur de quantification vaut ≈ Δ²/12 partout. À débit égal, l'ECSQ du résidu perd donc ce que la
grille donnait gratuitement, et ce que le parent rend (−½ log₂(1 − ρ²), § 2) est plus petit dès que ρ est
petit.

## 5. L'arbre le plus économe

Chaque expert se code seul (B bits) ou comme mutation d'un parent déjà décodé (B − s bits, s le gain de
l'arête, symétrique). Le coût d'un ordre de décodage valide est B · E − Σ_{arêtes de l'arbre} s, avec un
seul expert racine si tous les s > 0 (sinon une forêt). Minimiser le coût revient à trouver l'arbre
couvrant de poids maximal sur s (Kruskal 1956 ; la propriété de coupe assure l'optimalité du choix
glouton de l'arête la plus lourde qui ne ferme pas de cycle). Le gain par poids de la couche vaut
Σ_{arbre} s / E. Pour un graphe orienté (s non symétrique) il faudrait l'arborescence de poids maximal
(Chu-Liu/Edmonds) ; nos scores sont symétriques par construction (cos² et appariement).

Borne : le gain de l'arbre ne dépasse pas (E − 1)/E · max s.

## 6. Le paralogue sur un défaut de cache : erreur de substitution

Soit y_c(x) la sortie de l'expert manquant, y_s(x) celle d'un expert résident, sur les entrées x
routées vers c. Avec un gain β (un scalaire, moindres carrés) :
ε(c, s) = Σ‖y_c − β y_s‖² / Σ‖y_c‖² = 1 − ρ_f², ρ_f = ⟨y_c, y_s⟩ / (‖y_c‖ ‖y_s‖) (produit scalaire
sur tous les jetons et toutes les composantes), β* = ⟨y_c, y_s⟩ / ‖y_s‖².
Pour la sortie de la couche, l'expert c intervient avec son poids de routage g_c ∈ (0, 1) : l'erreur
relative de la couche est ≈ Σ g_c² ‖y_c − y_s‖² / Σ‖Σ_j g_j y_j‖², plus petite que ε d'un facteur que la
mesure donne.

Le paralogue ne lit aucun octet : il bat toute compression en débit (0 bit). Il ne vaut que si ε est
au niveau de l'erreur de la base (§ O des seuils).
