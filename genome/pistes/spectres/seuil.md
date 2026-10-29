# Piste « spectres » : seuils déclarés avant toute lecture

Écrit et commité le 2026-10-21, **avant** le calcul du premier spectre et avant tout ajustement.
Piste 05 § 3.3 (a), idée de Stone (la fractale, lois de puissance des spectres). Rien de ce fichier
ne change après la lecture ; une correction se fait en barrant (~~…~~) et en disant pourquoi.

## 1. L'échantillon (tiré avant de regarder)

- Modèle : `~/dev/modeles/gguf/gpt-oss-20b-MXFP4.gguf` (empreinte vérifiée le
  2026-10-15, `verification-gpt-oss.txt`).
- Couches : **0, 12, 23** (début, milieu, fin ; 24 couches).
- Experts : par couche, **4 experts distincts** tirés par `numpy.random.default_rng(20261021)`,
  `rng.choice(32, 4, replace=False)`, dans l'ordre des couches 0, 12, 23. Les mêmes 4 experts pour
  gate, up et down d'une couche (on suit un expert entier).
- Matrices d'experts : 3 couches × 3 rôles × 4 experts = **36** matrices 2 880 × 2 880 (MXFP4,
  déquantifiées en f64 exact).
- Matrices d'attention des mêmes couches : `attn_q` (4 096 × 2 880), `attn_k` (512 × 2 880),
  `attn_v` (512 × 2 880), `attn_output` (2 880 × 4 096), Q8_0 déquantifiées en f64 exact :
  **12** matrices. Les valeurs singulières sont min(m, n) : 2 880 pour q et o, 512 pour k et v.
- Total : **48 matrices**.

## 2. La grandeur ajustée

Comme Martin et Mahoney (arXiv 1810.01075) : la densité spectrale empirique (ESD) des valeurs propres
λᵢ = σᵢ² de la matrice de corrélation X = WᵀW (la normalisation 1/N ne change pas l'exposant). Une loi
de puissance de queue ρ(λ) ∝ λ^(−α) pour λ ≥ λ_min. (Sur les σ, la même queue a l'exposant 2α − 1.)

## 3. La méthode (Clauset, Shalizi, Newman, arXiv 0706.1062), écrite de zéro

1. Pour chaque candidat λ_min parmi les valeurs observées, telle que la queue garde **au moins
   50 points** (garde déclarée : sous 50 points, le minimum de KS se joue sur le bruit
   d'échantillon), α̂ = 1 + n / Σ ln(λᵢ / λ_min) (estimateur du maximum de vraisemblance, loi
   continue) et D = distance de Kolmogorov-Smirnov entre la fonction de répartition empirique de la
   queue et la loi ajustée. On retient le λ_min qui minimise D.
2. Sur la même queue (λ ≥ λ_min), ajustement par maximum de vraisemblance de deux concurrentes
   tronquées en λ_min : **exponentielle** (forme close) et **log-normale** (numérique).
3. Test du rapport de vraisemblance de Vuong, normalisé, comme CSN § 5 : R = Σ ℓᵢ (ℓᵢ = log p_PL −
   log p_alt, point par point), σ̂ l'écart type des ℓᵢ, p = erfc(|R| / (σ̂ √(2n))).
4. Plausibilité (CSN § 4.1, information complémentaire, ne change pas le verdict principal) :
   p_gof par 100 répliques semi-paramétriques, λ_min et α ré-estimés à chaque réplique.

## 4. Les verdicts (déclarés)

- **Verdict principal par matrice.** On dit « loi de puissance » pour une matrice **si et seulement
  si** R > 0 **et** p < 0,05 contre l'exponentielle, **et** R > 0 **et** p < 0,05 contre la
  log-normale. Sinon : « non départagée » (p ≥ 0,05 contre au moins une) ou « autre loi préférée »
  (R < 0 et p < 0,05 contre au moins une).
- **Verdict strict (rapporté à côté)** : le verdict principal **et** p_gof ≥ 0,1.
- **Verdict sur gpt-oss** : on écrit « les matrices de gpt-oss suivent une loi de puissance »
  **seulement si** le verdict principal tient pour **au moins 2/3 de l'échantillon, soit au moins 32
  matrices sur 48**. Le même décompte est rapporté par famille (gate, up, down, attention), sans
  conclusion propre à une famille sous 2/3 de la famille.

## 4 bis. Amendement du 2026-10-21, avant toute lecture des spectres réels

**Ce qui a changé.** Un essai de l'instrument sur des tirages synthétiques (aucun spectre de gpt-oss
n'était encore ajusté ; les SVD tournaient) a montré que le verdict principal du § 4 **ne peut pas
dire oui** : sur 40 tirages de Pareto vrais (n = 2 880, α = 2,5 et 3,5), 40 sont « non départagée »,
p médian contre la log-normale 0,59 et 0,63. La log-normale tronquée en x_min, avec μ très négatif et
σ grand (μ = −34, σ = 4,8 sur un tirage), épouse une loi de puissance sur toute l'étendue observée ;
c'est la limite connue que CSN décrivent eux-mêmes (leur § 6 : pour la plupart des jeux réels, la
log-normale ne peut être ni écartée ni préférée). Le témoin T-Pareto du § 5 échouera donc sous le
verdict principal ; il est gardé tel quel et rapporté.

~~On ne dit « loi de puissance » que si CSN la préfère à la log-normale avec p < 0,05.~~ Le verdict
principal est **rapporté tel que déclaré**, avec la mention qu'il n'a aucune puissance à cette
taille (mesuré : `mesures/pistes/spectres/puissance-critere.json`, outil `puissance_critere.py`).
On ajoute, déclaré ici avant toute lecture :

- **Verdict « compatible loi de puissance »** (le « modéré ou mieux » de CSN, tableau 6.2) : p_gof ≥
  0,1 **et** l'exponentielle écartée (R > 0, p < 0,05) **et** la log-normale non préférée (pas R < 0
  avec p < 0,05). Il dit « loi de puissance ou log-normale à très grand σ, indiscernables ici », et
  s'écrit toujours ainsi.
- Témoins sous ce verdict : T-Pareto doit être « compatible » (α̂ ∈ [2,3 ; 2,7]) ; T-MP (trois
  formes) et T-exp ne doivent pas l'être ; T-lognormale est rapporté sans attente (le verdict ne
  prétend pas l'écarter).
- Sa puissance se mesure sur les mêmes tirages synthétiques que ci-dessus (même outil) avant la
  lecture des spectres réels ; il n'est retenu que s'il dit « compatible » sur au moins 18 Pareto
  sur 20 pour chaque α, et sur au plus 2 exponentielles sur 20.
- Verdict sur gpt-oss sous ce critère : « compatible avec une loi de puissance » seulement pour au
  moins 32 matrices sur 48 ; même décompte par famille.

## 5. Les témoins (et leur cassure)

- **T-MP (hasard, Marchenko-Pastur, doit tomber)** : matrices gaussiennes i.i.d. aux mêmes
  dimensions (2 880 × 2 880, 4 096 × 2 880, 512 × 2 880), graine 20261021. Attendu : aucune déclarée
  « loi de puissance ». Si une l'est, l'instrument est faux et rien ne sort.
- **T-perm (structure détruite, mêmes entrées)** : chaque matrice réelle, entrées permutées au hasard
  (graine 20261021). Rapporté à côté de chaque matrice réelle (l'excès sur le hasard).
- **T-Pareto (doit être reconnu)** : 2 880 valeurs propres de loi de Pareto α = 2,5 (λ ≥ 1), passées
  par une vraie matrice U diag(√λ) Vᵀ (U, V orthogonales tirées) puis par la SVD. Attendu : « loi de
  puissance » et α̂ ∈ [2,3 ; 2,7].
- **T-exp et T-lognormale (doivent tomber)** : 2 880 valeurs exponentielles, et log-normales
  (μ = 0, σ = 1). Attendu : pas « loi de puissance ».
- **Cassure** : l'option `--casser` échange les entrées de T-Pareto et de T-MP ; les deux témoins
  doivent alors afficher ÉCHEC. Le journal de la cassure est commité à côté du journal normal.

## 6. Le second chemin du chiffre principal

Le chiffre principal (nombre de matrices « loi de puissance » et leurs α) est refait par un chemin
indépendant :
- une **seconde déquantification** écrite depuis la spécification (OCP MX v1.0 : E2M1 par ses bits
  signe / exposant / mantisse, échelle E8M0 = 2^(e − 127)) et non par la table de `structure.py` ;
  attendu : matrices égales au bit ;
- les **valeurs propres par `eigvalsh(WᵀW)`** au lieu de la SVD ; attendu : écart relatif
  < 10⁻⁸ sur les valeurs de la queue retenue ;
- un **second ajustement** (`scipy.stats` : `lognorm`, `expon`, tronquées par `logpdf − logsf`, et
  λ_min par une boucle écrite autrement) ; attendu : mêmes verdicts sur les 48 matrices, α égaux à
  10⁻⁶ près.

## 7. Le levier de compression (question 4) : ce qui se mesure, déclaré avant

Aucun chiffre de levier n'est présenté comme acquis : c'est un levier **dans le domaine des poids**,
et la propriété (c) de 05 § 2.1 dit que l'erreur de poids ne prédit pas la KL.

- **L1, sans perte, sur les codes MXFP4 (mesuré)** : information apportée sur le code de 4 bits par
  une prédiction de rang faible L̂_r (facteurs arrondis en f16, rangs r ∈ {1, 2, 4, 8, 16, 32, 64}),
  au-delà de l'échelle du bloc : H(code | échelle) − H(code | échelle, case de L̂_r / échelle) (16 cases),
  moins le coût des facteurs 16 · r · (m + n) / (m n) bits par poids. Levier net retenu = le meilleur r.
  Témoin T-perm (doit rendre ≈ 0) ; témoin positif : une matrice de rang 8 plantée plus du bruit,
  quantifiée par le même MXFP4 (doit rendre un gain net > 0).
- **L2, avec perte, borne gaussienne (calculé)** : à l'erreur relative D = 0,044 (énergie de l'erreur
  sur énergie de la matrice, celle de la base frontière, `borne-shannon-par-tenseur.json`), débit de
  remplissage inverse par rangée sur W, contre le même sur W − L̂_r plus le coût des facteurs.
- **L3, avec perte, opérationnel (mesuré)** : quantificateur scalaire uniforme à pas global, entropie
  empirique des indices (codeur entropique idéal), pas réglé par dichotomie pour la même erreur
  relative D, sur W puis sur W − L̂_r plus le coût des facteurs. Second chemin de L2.
- **Seuil de « levier »** : on parle de levier pour une famille si le gain net médian sur ses matrices
  dépasse **0,05 bit par poids** (le plus petit gain que le projet a retenu jusqu'ici, ordre de
  grandeur du gain du contexte de colonne, 05 § 0) **et** si le même calcul sur T-perm rend moins
  du quart de ce gain.

## 7 bis. Ajout du 2026-10-22, 04 h 40 (témoins du levier, après le v1 faux)

Le premier passage du témoin planté (levier v1, 04:26) a montré L2 faux (cible n fois trop grande)
et a déjà fait voir L1 = +0,157 et L3 = +0,153 bit sur le planté : ces deux attentes sont donc
posées **après** avoir vu ces valeurs, et dites comme telles. Attentes du témoin, v2 :
- T-plante-rang8 : L1, L2 et L3 au-delà de 0,05 bit (le rang 8 planté porte 30 % de l'énergie :
  borne haut débit ½ log₂(1/0,7) − c(8) = 0,257 − 0,089 = 0,168 bit pour L2, calculé ici avant) ;
- T-plante-rang8.blocs : L1 sous 0,0125 bit (le quart du seuil) ;
- T-plante-rang8.perm (ajouté) : L2 et L3 sous 0,0125 bit.
Le témoin T-blocs des matrices réelles ne calcule plus que L1 (seul usage déclaré au § 7).

## 7 ter. Ajout du 2026-10-22, 05 h 40 : L3 remplacé par sa version à tramage soustractif

Vu dans les premières lignes de `levier-v2.out` (avant la fin du passage) : L3 sans tramage est faussé
par la discrétude des matrices MXFP4. L3_0 va de 2,40 à 2,67 bits quand la borne L2_0 reste à
2,22–2,25, et le témoin T-perm rend le même « gain » que la matrice réelle (L00.up.E00 : +0,148 réel,
+0,154 permuté). ~~L3 (quantificateur uniforme à pas global, sans tramage) est le second chemin de
L2.~~ Le second chemin de L2 devient **L3d** (`levier_l3.py`) : même quantificateur, tramage
soustractif uniforme connu du décodeur, Δ = √(12 · D · ‖W‖² / N) en forme close. Attentes déclarées
ici, avant son passage : sur T-plante-rang8, L3d au-delà de 0,05 bit ; sur T-plante-rang8.perm, sous
0,0125 ; erreur relative mesurée à 1 % de la cible D. Les colonnes L3 et L3r de `levier-v2.out`
restent publiées, barrées, comme trace. La règle de levier (§ 7) s'applique à L1, L2 et L3d.

## 7 quater. Ajout du 2026-10-22, 08 h : levier v3 en une passe

Le passage v2 n'avançait plus (une matrice par heure environ : les séances ABBA des autres flux
tiennent la machine, et le v1 orphelin passe d'abord). `levier.py` v3 calcule en une seule passe L1,
L2 et L3d (le tramage de § 7 ter), sans la colonne L3 caduque ; mêmes facteurs (mêmes graines de
SVD), mêmes témoins, mêmes attentes (§ 7, § 7 bis, § 7 ter). Sortie `levier-v3.out`. Le v2 est
endormi par sa propre garde pendant ce temps ; ses lignes déjà écrites restent comme trace.

## 8. Règles de cohabitation appliquées

Pas de carte graphique, jamais le verrou ; priorité « sous la normale », 2 fils BLAS au plus ;
pause si `~/dev/verrou-carte.txt` a moins de 2 h et nomme une séance de vitesse (J1,
ABBA, vitesse). Lecture du GGUF par carte mémoire, une matrice à la fois (4,4 Mo par expert).

## 7 quinquies. Ajout du 2026-10-22, 10 h 05 : le plafond spectral, déclaré avant tout calcul

**Pourquoi.** L1, L2 et L3d mesurent un levier de rang fixe qui paie ses facteurs. Ils ne disent pas
si un autre usage du spectre (une base propre complète, un rang qui varie) pourrait faire mieux. Le
plafond le dit : le gain du meilleur codage dans la base propre, **cette base étant offerte au
décodeur sans frais**. Il se calcule sur les valeurs singulières déjà sauvées
(`valeurs-singulieres.npz`), sans relire le modèle. Aucun de ces nombres n'a été calculé avant
l'écriture de ce paragraphe.

**La grandeur** (modèle gaussien, [calc.]). W de taille m × n, p = min(m, n), q = max(m, n),
σ₁ … σ_p ses valeurs singulières, P = Σ σⱼ². On lit W comme q vecteurs de dimension p (la petite
dimension : sinon des directions de variance nulle donneraient un gain fictif), de covariance de
valeurs propres λⱼ = σⱼ² / q. À l'erreur relative D (énergie de l'erreur sur P), le remplissage
inverse donne le niveau θ tel que Σⱼ min(θ, λⱼ) = D · P / q, et le débit par poids
R_KLT(D) = (1/p) Σⱼ max(0, ½ log₂(λⱼ / θ)). La base blanche (spectre plat, même énergie) coûte
½ log₂(1/D). **Le plafond** est G(D) = ½ log₂(1/D) − R_KLT(D) ≥ 0, en bits par poids. Il majore
le gain de toute méthode qui code dans une base propre, rang fixe ou non, sous ce modèle : la base
blanche majore la base « variances par rangée » de L2 (moyennes arithmétique et géométrique), et la
transformée de Karhunen-Loève est optimale pour une source gaussienne.

**L'excès sur le hasard** : E = G(réel) − G(permuté), le permuté étant la même matrice aux entrées
mélangées (son spectre porte la loi des entrées, queue lourde comprise, et pas leur arrangement).
D = 0,044 (celle de L2 et L3d, § 7). Une courbe sur D ∈ {0,01 ; 0,02 ; 0,044 ; 0,1} est rapportée
comme information, sans verdict.

**La lecture** (par famille gate, up, down, attention ; médiane de E sur ses 12 matrices) :
- médiane E < 0,05 bit (le seuil de levier du § 7) : **plafond fermé**. Aucune méthode qui code dans
  une base propre ne peut y franchir le seuil, même sans payer la base, sous ce modèle ;
- médiane E ≥ 0,05 : **plafond ouvert**, condition nécessaire seulement. On rapporte la part que le
  meilleur levier de rang fixe payé (L2 et L3d de `levier-v3.out`) en réalise, max_r L2_r / E,
  sans la présenter comme acquise.
- Sur l'échantillon entier : la moyenne de G et de E pondérée par le nombre de poids de chaque matrice.

**Les témoins.**
- **T-MP, second chemin analytique** : G des trois T-MP (2 880 × 2 880, 4 096 × 2 880,
  512 × 2 880) doit égaler l'intégrale de la loi de Marchenko-Pastur de même rapport c = p / q,
  calculée par quadrature et non par les valeurs propres, à **0,005 bit** près (le dixième du seuil
  de levier). Sinon l'outil est faux et rien ne sort.
- **T-Pareto, positif** : le spectre de Pareto planté (α = 2,5, déjà passé par une vraie matrice et
  sa SVD) doit donner G(Pareto) − G(MP 2 880 × 2 880) ≥ 0,05.
- **Cassure** (`--casser` échange le spectre de Pareto et celui du T-MP 2 880 × 2 880) : les deux
  témoins doivent tomber. Journal commité à côté.
- **Second chemin du niveau θ** : le premier chemin cherche θ par dichotomie ; le second le prend en
  forme close (valeurs triées, sommes cumulées). Attendu : G égal à 10⁻⁹ près sur les 48 matrices,
  leurs permutés et les témoins.
- Rapporté sans attente : G(permuté) − G(MP de même forme), ce que la loi des entrées seule fait au
  spectre (matrices aléatoires à entrées lourdes).

## 7 sexies. Amendement du 2026-10-22, 10 h 20 : le témoin T-Pareto du plafond était mal posé

Premier passage de `plafond.py` (journal `plafond-v1.log`) : second chemin égal à 9·10⁻¹⁴, les quatre
T-MP égaux à l'intégrale analytique à 3·10⁻⁴ près (tiennent) ; **T-Pareto tombe** : G = 0,298, sous
G(MP 2 880 × 2 880) = 0,590, excès −0,292. L'outil s'est arrêté avant toute lecture de gpt-oss, comme
déclaré ; `plafond.out` a été écrit par ce passage mais **n'a pas été ouvert**, et la relance l'écrase.

**Pourquoi l'attente était fausse** : le plafond mesure l'écart à la platitude du spectre entier
(à haut débit, ½ log₂ de la moyenne arithmétique sur la moyenne géométrique des λ actifs). La loi de
Marchenko-Pastur de rapport 1 a une densité en 1/√x près de zéro : une foule de petites valeurs, très
loin de la platitude. Le Pareto planté (λ ≥ 1) est borné par en bas. Une queue lourde en haut ne dit
rien de seul sur le plafond ; ~~T-Pareto doit donner G(Pareto) − G(MP 2 880 × 2 880) ≥ 0,05~~ comparait
deux choses qui n'ont pas à s'ordonner ainsi. C'est aussi pourquoi l'excès se lit contre le permuté
de la même matrice, jamais contre un spectre de référence.

**Nouveau témoin positif, déclaré avant toute lecture** : T-plante-rang8 du levier (rang 8 portant
30 % de l'énergie plus bruit gaussien, quantifié MXFP4, régénéré à l'identique par le code de
`levier.py`, graine 20261021 + 50) contre sa version aux entrées permutées (la même permutation que
`levier.py`). Attendu : **E ≥ 0,05**. Prédiction à haut débit, posée ici avant : le bruit passe de
la variance 1 à 0,7 sur 2 872 directions, soit ½ log₂(1/0,7) = 0,257 bit, moins le coût de 8
directions de variance ≈ 108 (≈ 8 × ½ log₂(108/θ) / 2 880 ≈ 0,01) : **E ≈ 0,25**, rapporté sans
seuil (D = 0,044 n'est pas tout à fait le haut débit pour une loi MP de rapport 1).

**Nouvelle cassure** : `--casser` échange le spectre du planté et celui de son permuté (E devient
négatif : doit tomber) et ceux de T-MP 2 880 × 2 880 et T-MP 4 096 × 2 880 (même p, rapports
différents : doit tomber devant l'intégrale analytique). T-Pareto reste calculé et rapporté, sans
attente.

## 7 septies. Ajout du 2026-10-22, 10 h 15 : le plafond par rang, payé ou offert (avant calcul)

Le plafond (§ 7 quinquies) est ouvert pour les quatre familles (`plafond.log`). Reste à savoir **où**
il vit dans le spectre : dans quelques grandes directions (un rang faible le prendrait) ou dans la
foule des petites (seule une base complète, qui coûte autant que la matrice, le prendrait).

**La grandeur** ([calc.], même modèle gaussien, sur `valeurs-singulieres.npz`) : G_r(D) = le plafond
quand seules les r premières directions propres sont offertes, les p − r autres codées comme un
bruit blanc de variance égale à leur moyenne (remplissage inverse sur {λ₁ … λ_r} ∪ {(p − r) fois
λ̄_reste}). Rangs r ∈ {1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1 024, p}. **Levier payé** :
N_r(b) = G_r − b · r · (m + n) / (m n), facteurs à b bits par coefficient, b ∈ {16, 8, 4} ;
b = 16 est le coût de L1, L2 et L3d ; 8 et 4 sont optimistes (l'erreur des facteurs arrondis n'est
pas comptée) et se disent ainsi.

**La lecture** (règle du § 7, inchangée) : levier d'une famille si la médiane de max_r N_r(b) sur ses
12 matrices dépasse 0,05 bit **et** si le même calcul sur les permutés rend moins du quart. Lu pour
b = 16 (la règle) ; b = 8 et 4 rapportés comme sensibilité, sans verdict. La part du plafond prise
par les r premières directions, (G_r(réel) − G_r(permuté)) / E, est rapportée par famille.

**Témoins** : sur le planté, max_r N_r(16) doit dépasser 0,05 et être atteint à r = 8 (le rang
planté) ; sur son permuté, rester sous 0,0125. Second chemin de ce calcul : L2 de `levier-v3.out`
(variances par rangée et matrices réelles, au lieu de spectres et bruit blanc) ; attendu : même
signe du levier par famille, écart non borné d'avance (les deux bases diffèrent) et rapporté.
Cassure : planté et permuté échangés, le témoin doit tomber.

## 7 octies. Ajout du 2026-10-22, 10 h 40 : l'exposant prédit-il le levier ? (prédiction déclarée avant)

**D'où vient la question** (exploration, NON déclarée avant, `alpha-levier.out`) : sur les 48 matrices,
le rang de Spearman entre α̂ et max_r N_r(16) (§ 7 septies) vaut −0,64 ; 6 des 8 matrices de α̂ < 2 ont
un levier payé au-delà de 0,05 bit, contre 2 sur 40 au-dessus. Ces nombres ont été vus : ils posent la
règle, ils ne la prouvent pas. La preuve se fait sur des matrices que personne n'a regardées.

**L'échantillon neuf** (tiré à l'écriture de ce paragraphe, avant toute lecture de ses matrices) :
graine **20261022** ; `rng.choice` de 3 couches parmi {1, …, 22} privé de 12 (les couches 0, 12 et 23
déjà vues sont exclues), puis 4 experts par couche, dans l'ordre des couches, par le même générateur.
~~Tirage : couches [2, 4, 16] ; experts {2 : [4, 7, 26, 28], 4 : [9, 10, 11, 19], 16 : [1, 4, 8, 20]}~~
(erreur de transcription : ces nombres ont été écrits avant que la commande du tirage ait rendu sa
sortie ; aucune matrice n'avait été lue). **Tirage réel** de la graine 20261022 : couches **[3, 9, 21]** ;
experts {3 : [4, 8, 24, 26], 9 : [0, 14, 20, 22], 21 : [10, 18, 23, 24]} ; l'outil le refait et le vérifie. Matrices : down et gate des 4 experts et
attn_q, attn_k, attn_v, attn_output de chaque couche : **36 matrices**.

**La règle, déclarée** : α̂ < 2 ⇒ levier de rang payé (max_r N_r(16) > 0,05) ; α̂ ≥ 2 ⇒ pas de levier.
α̂ par la méthode du § 3 (x_min par KS, garde 50 points ; sans répliques p_gof), N_r par l'outil du
§ 7 septies (b = 16, mêmes rangs).

**Le critère de réussite** : parmi les matrices neuves de α̂ < 2, au moins 2/3 ont un levier ; parmi
celles de α̂ ≥ 2, au plus 10 % en ont un. Moins de 3 matrices de α̂ < 2 : « indécidable » (la règle n'a
pas été mise à l'épreuve), dit tel quel. Le Spearman neuf est rapporté sans seuil.

**Témoin de l'outil** : appliqué aux spectres des 48 matrices anciennes (`valeurs-singulieres.npz`), il
doit redonner leurs α̂ (`ajustements.out`) à 10⁻⁶ et leurs N_r (`plafond-rang.out`) à 10⁻⁶, et donc
6 sur 8 et 2 sur 40. **Cassure** (`--casser`) : les α̂ des 48 anciennes mélangés entre matrices (graine
20261022) ; la règle doit y échouer à son propre critère.

**Cohabitation** : l'outil ne démarre qu'après la fin de la chaîne en cours (`chaine.log` : « fin
normalise »), pour ne jamais dépasser 2 fils pour cette piste ; il garde la pause des séances de vitesse.

## 7 nonies. Ajout du 2026-10-22, 12 h : la base blanche comptait les échelles de rangée (avant calcul)

**Ce qui a changé.** `levier-v3.out` (fini à 11:53) donne L2_0, le débit gaussien avec une variance
par rangée. Pour L00.down.E24 il vaut 0,755 bit, contre ½ log₂(1/D) = 2,2535 pour la base blanche :
**une variance par rangée gagne déjà 1,5 bit par poids**, sans aucune base propre. Le plafond (§ 7
quinquies) et le plafond par rang (§ 7 septies) se mesuraient contre la base blanche ; ils comptent
donc comme « spectrale » la structure des canaux géants, qu'une échelle par rangée prend déjà (et que
les échelles de bloc de MXFP4 exploitent). Le L2 mesuré le montre : −0,009 sur L00.down.E24 là où
N_r(16) annonçait +0,130. ~~Le levier existe matrice par matrice (8 matrices sur 48 à b = 16)~~ :
c'étaient des plafonds contre la base blanche, pas des leviers ; le second chemin déclaré (§ 7
septies : « même signe par famille ») **tombe pour down** (+0,042 contre une médiane de L2 négative).

**Le test du § 7 octies change de nom, avant lecture de son résultat** : il éprouve « α̂ < 2 prédit
N_r(16) contre la base blanche > 0,05 », c'est-à-dire un spectre concentré dans ses premières
directions, et **plus un levier**. Quelle que soit son issue, aucun levier n'en sortira.

**Le plafond au-delà des échelles de rangée** ([calc.], sans relire le modèle) :
G_rang = L2_0 − R_KLT(D), avec R_KLT = ½ log₂(1/D) − G (`plafond.out`) et L2_0 (`levier-v3.out`,
`levier-temoin-v3.out`). Il est ≥ 0 quand la dimension des vecteurs de R_KLT est celle des rangées
(les variances par rangée sont alors la diagonale de la covariance ; Hadamard) : c'est le cas des 36
matrices d'experts (carrées, valeurs propres identiques dans les deux sens), de attn_k, attn_v et
attn_output. Pour **attn_q** (4 096 × 2 880), les vecteurs de R_KLT sont de dimension 2 880, les
colonnes : la majoration n'est pas garantie, les trois attn_q sont rapportées à part et sans verdict.
Excès E_rang = G_rang(réel) − G_rang(permuté). Lecture par famille comme au § 7 quinquies (médiane
≥ 0,05 : ouvert au-delà des échelles de rangée ; sinon fermé), attention sans attn_q (9 matrices).

**Témoins** :
- **non-négativité** : G_rang ≥ −10⁻³ pour les 45 matrices couvertes et leurs permutés (sinon
  l'orientation ou les fichiers sont faux) ;
- **planté** : E_rang ≥ 0,05 (ses rangées sont homogènes : la correction doit lui laisser presque
  tout ; mon calcul de tête sur les nombres déjà publiés donne ≈ 0,21, dit ici comme tel) ;
- **T-rangées, le témoin qui doit faire tomber l'ancienne base** : matrice gaussienne 2 880 × 2 880
  dont les rangées sont multipliées par des échelles log-normales (σ = 1,5, graine 20261022), et son
  permuté. Attendu : contre la base blanche, E ≥ 0,05 (l'artefact existe) ; au-delà des échelles de
  rangée, |E_rang| < 0,0125 (la correction l'efface) ;
- **cassure** (`--casser`) : L2_0 remplacé par ½ log₂(1/D) (la base blanche) ; T-rangées doit alors
  tomber (E_rang ≥ 0,05).

## 7 decies. Amendement du 2026-10-22, 12 h 55 : la référence du § 7 nonies était fausse (avant calcul)

Premier passage de `plafond_rangee.py` (`plafond-rangee-v1.log`, `plafond-rangee-casse-v1.log`) :
non-négativité tient (min G_rang +0,065) ; planté +0,209 (tient) ; **T-rangées tombe** : E au-delà des
échelles de rangée −0,562 au lieu de ≈ 0. Aucune ligne de gpt-oss n'est sortie (l'outil s'arrête avant).

**Pourquoi** (vérifié à part : R_KLT = 0,2015 ≤ R_rangée = 0,2230 pour T-rangées, Hadamard tient,
G_rang = +0,022) : ~~E_rang = G_rang(réel) − G_rang(permuté)~~ soustrait le permuté **complet**, qui
détruit aussi les échelles de rangée ; son spectre garde l'artefact de Marchenko-Pastur (≈ 0,58 de
« gain » d'une base offerte sur une matrice carrée au hasard), que le T-rangées, une fois ses échelles
prises, n'a presque plus (ses petites rangées passent sous θ). La référence mélange deux effets.

**La bonne référence, déclarée ici** : la même matrice aux entrées **permutées à l'intérieur de chaque
rangée** (graine 20261022 + indice de la matrice). Elle garde exactement les variances de rangée (donc
L2_0) et détruit toute structure entre rangées. E_rang = G_rang(réel) − G_rang(permuté par rangée), avec
G_rang = L2_0 − R_KLT. Demande une SVD par matrice (lecture du GGUF, une matrice à la fois).
Témoins : T-rangées, |E_rang| < 0,0125 (sa version permutée par rangée a la même loi) ; planté,
E_rang ≥ 0,05 ; non-négativité de G_rang (réel et permuté par rangée) ≥ −10⁻³ hors attn_q ; **cassure**
(`--casser`) : la référence redevient le permuté complet, T-rangées doit retomber (≈ −0,56). Lecture par
famille inchangée (médiane ≥ 0,05 : ouvert au-delà des échelles de rangée).

## 7 undecies. Ajout du 2026-10-26, 23 h 50 : la référence par rangée est-elle stable d'une graine à l'autre ? (avant calcul)

Contexte. La passe du plafond par rangée (§ 7 decies) fixe une seule permutation par matrice
(graine 20261022 + indice). Une question reste : le chiffre E_rang dépend-il de ce tirage ? La passe
coupée par la pause du 22 (`plafond-rangee-partiel.log`, 29 matrices) a été lue par l'auteur avant la
relance entière ; ce qui est déclaré ici ne dépend d'aucun verdict de famille.

Mesure : 6 matrices fixées d'avance (L00.down.E24, L00.gate.E22, L12.up.E01, L12.down.E01, L23.gate.E07
si tirée, sinon la première gate de la couche 23 ; L23.attn_output), G_rang du permuté par rangée avec
3 graines neuves (777001, 777002, 777003), comparé au G_rang de référence de la passe principale.
- **Seuil** : écart maximal entre une graine et la passe principale ≤ 0,0125 (le quart du seuil de 0,05 de
  famille, la même tolérance que les témoins du § 7 decies) ; sinon la référence est instable et les
  E_rang de la passe principale sont rapportés avec cette incertitude, sans verdict de famille au bord.
- **Témoin** : la référence « permuté complet » (la fausse, § 7 decies) sur L00.down.E24 doit s'écarter de
  plus de 0,0125 de la référence par rangée (l'écart attendu est de l'ordre de 0,1) : l'instrument sait
  distinguer deux références différentes.
- **Cassure** (`--casser`) : un décalage de 0,02 ajouté au G_rang d'une des graines doit faire échouer le
  seuil (l'instrument de comparaison sait dire non).
- Cohabitation : lancé après la fin de la passe principale (2 fils au plus pour la piste).
