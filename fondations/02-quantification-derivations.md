# Étude 02 : dérivations complètes (pour le mémoire)

Compagnon de `fondations/02-quantification.md`. Chaque résultat est posé pas à pas, avec
ses hypothèses ; les nombres viennent des journaux commités
(`fondations/journaux/02-quantification/`, CSV sous `csv/`, produits par
`outils/quant-csv-memoire.py`). Étiquettes : **[litt.]**, **[calc.]**, **[mes.]**.
Rédigé le 2026-10-15. Notation : $N$ poids, $b$ bits par poids (métadonnées comprises),
$W$ débit d'un étage en octets par seconde.

---

## D1. Le plafond de débit d'un jeton

**Hypothèses.** Décodage au lot de 1 ; chaque poids actif est lu une fois par jeton ; le
cache KV et les activations sont négligés (ils le sont pour un contexte court : l'étude 04
les chiffre). Les poids sont répartis sur des étages $i$ (VRAM, PCIe depuis la RAM,
NVMe) ; l'étage $i$ amène $B_i$ octets par jeton au débit $W_i$.

**Proposition 1 (bornes du temps par jeton).**
$$\max_i \frac{B_i}{W_i} \;\le\; t_{\text{jeton}} \;\le\; \sum_i \frac{B_i}{W_i}.$$

*Démonstration.* Chaque étage doit faire passer ses $B_i$ octets, ce qui prend au moins
$B_i/W_i$ : d'où la borne basse, atteinte quand tous les transferts se recouvrent
parfaitement. Sans aucun recouvrement, les durées s'ajoutent : borne haute. $\square$

Le plafond de jetons par seconde est donc $1/\max_i (B_i/W_i)$ au mieux. Pour un modèle
dense lu entièrement par un seul étage, $B = N b / 8$ et
$$\text{jetons/s} \le \frac{8 W}{N b}. \tag{1}$$

**Application [calc.].** Qwen3.5-9B, $N_{\text{lus}} = 8{,}95 \cdot 10^9 - 1{,}02 \cdot
10^9$ (table d'enchâssement : une ligne par jeton) ; en Q4_K_M, $B = 5{,}097$ Go [mes.,
`bits-q4km-locaux.json`] ; à $W = 7$ Go/s (PCIe sous charge, études 01 et 04), plafond
$7/5{,}097 = 1{,}37$ jeton/s ; à $W = 256$ Go/s (VRAM), 50,2. En IQ2_XXS, $B = 2{,}757$
Go [mes.] : 2,54 et 92,9.

**Corollaire (la pente).** $\partial \ln(\text{jetons/s}) / \partial \ln b = -1$ : diviser
$b$ par deux double le plafond, à tout étage. Aucun autre paramètre de la chaîne n'a
cette pente unitaire sans contrepartie de débit.

---

## D2. La comptabilité des bits par poids, format par format

On compte, par super-bloc, tous les bits stockés. Disposition lue dans
`ggml/src/ggml-common.h` (llama.cpp 843e7dc) ; les `static_assert` du fichier donnent la
taille en octets de chaque bloc, ce qui sert de témoin à chaque ligne [calc.].

| Format | Bloc | Bits du bloc | bits/poids |
|---|---|---|---|
| Q2_K | 256 poids : codes 2 bits (512), 16 octets d'échelles et minimums 4+4 bits (128), `d` et `dmin` fp16 (32) | 672 | **2,625** |
| Q4_K | 256 : codes 4 bits (1 024), 12 octets d'échelles 6 bits (96), `d`, `dmin` (32) | 1 152 | **4,5** |
| Q6_K | 256 : 4 bits bas (1 024) + 2 bits hauts (512), 16 échelles int8 (128), `d` (16) | 1 680 | **6,5625** |
| IQ2_XXS | 256 = 8 groupes de 32 ; par groupe : 4 index de grille 8 bits (32), 4 × 7 bits de signe (28), échelle 4 bits (4) ; plus `d` fp16 | 8 × 64 + 16 = 528 | **2,0625** |
| IQ3_XXS | 256 : index de grille 8 bits par 4 poids (512) ; par groupe de 32 : 4 × 7 signes + échelle 4 bits (32 × 8 = 256) ; `d` (16) | 784 | **3,0625** |
| IQ1_S | 256 : 8 bits bas d'index par 8 poids (256) ; par 32 poids : 4 × 3 bits hauts d'index, échelle 3 bits, 1 bit de décalage (16 × 8 = 128) ; `d` (16) | 400 | **1,5625** |
| TQ1_0 | 256 : 240 trits à 5 par octet (48 octets) + 16 trits à 4 par octet (4 octets) ; `d` (16) | 432 | **1,6875** |
| Q1_0 | 128 : signes (128) ; `d` fp16 (16) | 144 | **1,125** |
| MXFP4 | 32 : FP4 E2M1 (128) ; exposant partagé E8M0 (8) | 136 | **4,25** |
| NVFP4 (llama.cpp) | 64 : FP4 E2M1 (256) ; 4 échelles UE4M3, une par 16 (32) | 288 | **4,5** |
| Treillis à décalage, état libre | suite de $T$ poids, $k$ bits par poids, $L$ bits d'état | $Tk + (L-k)$ | $k + (L-k)/T$ ; $T = 4096$, $k = 2$, $L = 16$ : **2,0034** |
| Treillis tail-biting (QTIP, EXL3) | tuile de 256 poids lue circulairement | $256 k$ | **$k$** exactement (+ échelles) |
| CurveTQ | état initial stocké par bloc + champ d'échelles factorisé | — | $k + 0{,}22 + 0{,}068$ : **2,29** [litt.] |

**Le bit réel lu par jeton n'est pas le bit du type.** Un fichier « IQ2_XXS » mélange les
types : on le mesure tenseur par tenseur (`outils/quant-gguf-bits.py`, témoin : la fin du
dernier tenseur égale la fin du fichier). Qwen3.5-9B « IQ2_XXS » : 2,761 bits/poids sur
les tenseurs ; décomposition des 2,757 Go lus par jeton [mes.] : IQ2_XXS 1 516 Mo (212
tenseurs), sortie Q5_K 699 Mo, Q4_K 472 Mo (32), Q2_K 66 Mo (4), F32 4 Mo.

---

## D3. La source gaussienne, la borne et la distance en bits

**Théorème 1 (Shannon, source gaussienne sans mémoire).** Pour $X \sim \mathcal N(0,
\sigma^2)$ i.i.d. et la distorsion quadratique, la fonction distorsion-débit est
$$D(R) = \sigma^2 \, 2^{-2R}.$$
(Résultat classique ; Cover et Thomas, th. 10.3.2.) À $R = 2$ : $D = 0{,}0625\,\sigma^2$.

**Définition (distance en bits à la borne).** Un quantificateur qui atteint la MSE $D_q$
au débit $R$ est à
$$\Delta(q) = R - D^{-1}(D_q) = R + \tfrac12 \log_2 (D_q/\sigma^2)
= \tfrac12 \log_2 \frac{D_q}{\sigma^2 2^{-2R}}$$
bits de la borne : c'est le débit qu'un code optimal économiserait à qualité égale.

**Lemme 1 (conversion d'un rapport de MSE en bits).** Deux quantificateurs de la même
pente $D \propto 2^{-2R}$ autour du point de fonctionnement, de MSE $D_1 > D_2$ au même
débit, sont séparés de $\tfrac12 \log_2(D_1/D_2)$ bit à qualité égale.

*Démonstration.* $D_1 2^{-2\delta} = D_2 \iff \delta = \tfrac12\log_2(D_1/D_2)$. $\square$

**Application [mes., calc.].** MSE mesurées à 2 bits sur $\mathcal N(0,1)$ (§ 2 du livrable,
`csv/mse-gaussien.csv`) :

| Quantificateur | $R$ | $D_q$ [mes.] | $\Delta$ à la borne [calc.] |
|---|---|---|---|
| Lloyd-Max scalaire | 2 | 0,1175 | 0,455 bit |
| IQ2_XXS (grille E8 de llama.cpp) | 2,0625 | 0,1070 | 0,450 bit |
| VQ dimension 8, livre aléatoire | 2 | 0,0935 | 0,291 bit |
| Treillis à décalage $L = 16$ | 2,0034 | 0,0680 | 0,061 bit |

Treillis contre IQ2_XXS : $\tfrac12\log_2(0{,}107/0{,}068) = 0{,}327$ bit ; contre la VQ 8 :
0,230 bit. C'est l'origine des « 0,23 à 0,33 bit/poids » du trou 1.

**Remarque (régime de haute résolution).** La formule de Panter-Dite pour le scalaire
optimal à débit fixe, $D \approx \frac{\sqrt3\,\pi}{2}\sigma^2 2^{-2R} = 2{,}72\,\sigma^2
2^{-2R}$, donnerait 0,170 à $R = 2$ au lieu de 0,1175 mesuré : à 2 bits on n'est pas en
haute résolution, et seules les MSE calculées ou mesurées valent. C'est pourquoi le banc
du § 2 a été refait au lieu d'être tiré des formules asymptotiques.

---

## D4. Le quantificateur de Lloyd-Max (le témoin du banc)

**Conditions nécessaires d'optimalité** (Lloyd 1957, Max 1960) pour $2^R$ niveaux
$y_1 < \dots < y_M$ et seuils $t_j$ :
1. plus proche voisin : $t_j = (y_j + y_{j+1})/2$ ;
2. centroïde : $y_j = \mathbb E[X \mid t_{j-1} < X \le t_j]
   = \dfrac{\varphi(t_{j-1}) - \varphi(t_j)}{\Phi(t_j) - \Phi(t_{j-1})}$ pour $X \sim \mathcal N(0,1)$,
   où $\varphi$ et $\Phi$ sont la densité et la répartition normales.

On itère 1 et 2 jusqu'au point fixe (`outils/quant-mse-gaussien.py`, sur la densité
exacte). La MSE s'écrit alors en forme fermée :
$$D = 1 - \sum_j y_j^2 \,[\Phi(t_j) - \Phi(t_{j-1})],$$
car $\mathbb E[X^2] = 1$ et l'erreur est orthogonale à la reconstruction au centroïde.
Résultats [calc.] : 0,36338 (1 bit, niveaux $\pm 0{,}79788 = \pm\sqrt{2/\pi}$) ;
0,117482 (2 bits, $\pm 0{,}45278$, $\pm 1{,}51042$) ; 0,034548 (3 bits) : les valeurs de
Max (1960). Le Monte-Carlo sur $2^{20}$ échantillons les retrouve à moins de 4 erreurs-
types (seuil déclaré avant), et l'instrument tombe quand on décale tous les niveaux de 0,1.

---

## D5. Le treillis à décalage et son Viterbi

**Le code.** L'état à l'instant $t$ est une fenêtre de $L$ bits $s_t$ du flux codé ; chaque
poids fait entrer $k$ nouveaux bits : $s_{t+1} = ((s_t \ll k) \,|\, u_t) \bmod 2^L$, avec
$u_t \in \{0, \dots, 2^k - 1\}$. La reconstruction est $\hat w_t = f(s_{t+1})$, où
$f : \{0,1\}^L \to \mathbb R$ est une table (aléatoire gaussienne : « RPTC ») ou une
fonction calculée (« 1MAD », « 3INST », « mul1 »).

**Lemme 2 (prédécesseurs).** Les prédécesseurs d'un état $s'$ sont exactement les $2^k$
états $s = (s' \gg k) \,|\, (h \ll (L-k))$, $h \in \{0, \dots, 2^k-1\}$.

*Démonstration.* $s' = ((s \ll k) | u) \bmod 2^L$ fixe les $L - k$ bits bas de $s$ (ce sont
les bits hauts de $s'$) et laisse libres ses $k$ bits hauts, perdus par le décalage. $\square$

**Conséquence (Viterbi vectorisé).** Le coût cumulé $J_{t+1}(s') = \min_h J_t(s(h, s')) +
(w_t - f(s'))^2$ se calcule en remodelant le vecteur $J_t$ de taille $2^L$ en une matrice
$(2^k, 2^{L-k})$ et en prenant le minimum sur l'axe des $h$ : $O(2^L)$ par poids,
$2^{16}$ ici. C'est la recette du banc (§ 9 du livrable).

**Débit exact.** État initial libre : $(Tk + L - k)/T$ bits par poids (D2). Tail-biting :
on impose $s_T = s_0$, ce qui rend le coût exactement $k$ bits ; le Viterbi se fait alors
pour chaque état initial possible ou par l'heuristique à deux passes de QTIP. CurveTQ
mesure que le tail-biting sur blocs de 64 coûte, au même débit utile, +4,10 de perplexité
contre un état initial stocké (0,22 bit/poids) [litt.].

**Coût de décodage d'une valeur (code « mul1 », lu dans exllamav3).** Une fenêtre de 16
bits, une multiplication 32 bits par une constante, une somme des 4 octets (`dp4a` ou
`dot4U8Packed`), une mise à l'échelle : ≈ 10 opérations entières [lu]. Plafond d'un noyau
limité par le calcul : $\approx$ 624 milliards de poids/s en CUDA mesuré (§ 2.2) ; en Vulkan
la passe 4 décode 64 Mio de poids 2 bits en 0,541 ms, soit $2{,}68\cdot10^{8}$ poids en
0,541 ms $= 4{,}96\cdot 10^{11}$ poids/s [mes., calc.].

---

## D6. Le partage des bits selon l'étage (la « règle des 2,6 bits »)

**Hypothèses.** (H1) Théorème de linéarité (HIGGS, 2411.17525) : pour de petites erreurs,
la perte de qualité est $\sum_i c_i \, \varepsilon_i$, où $\varepsilon_i$ est la MSE
relative de la matrice $i$ et $c_i \ge 0$ sa sensibilité. (H2) Après rotation, $\varepsilon_i
= \kappa \, 2^{-2b_i}$ (D3, à une constante près par codeur). (H3) La matrice $i$, de $n_i$
poids, est servie par un étage de débit $W_i$ fixé (le placement est donné). (H4) Budget :
le temps de transfert par jeton $\sum_i n_i b_i / (8 W_i) \le T$ (borne haute de D1 ; avec
recouvrement parfait, on raisonne étage par étage et la conclusion est la même).

**Problème.** $\min_{b} \sum_i c_i \kappa\, 2^{-2b_i}$ sous $\sum_i n_i b_i / W_i \le 8T$.

**Proposition 2.** À l'optimum (contrainte active, multiplicateur $\lambda > 0$),
$$b_i^\star = \tfrac12 \log_2\!\left(\frac{2 \ln 2 \;\kappa\, c_i \, W_i}{\lambda\, n_i}\right).$$

*Démonstration.* Le lagrangien $\mathcal L = \sum_i c_i \kappa 2^{-2b_i} + \lambda(\sum_i
n_i b_i/W_i - 8T)$ est convexe en $b$ (somme d'exponentielles décroissantes et d'un terme
linéaire). La condition du premier ordre $\partial\mathcal L/\partial b_i = -2\ln 2\,
c_i\kappa\, 2^{-2b_i} + \lambda n_i / W_i = 0$ donne $2^{-2b_i} = \lambda n_i / (2\ln2\,
c_i \kappa W_i)$, d'où la formule ; la convexité en fait le minimum global, et $\lambda$ se
fixe par la contrainte active. $\square$

**Corollaire 1 (la règle des 2,6 bits).** Deux matrices de même densité de sensibilité
$c_i/n_i$, l'une en VRAM ($W_V$), l'autre lue par le PCIe ($W_P$) :
$$b_V^\star - b_P^\star = \tfrac12\log_2\frac{W_V}{W_P} = \tfrac12\log_2\frac{256}{7}
= 2{,}60 \text{ bits}.$$
Avec les débits mesurés (VRAM 245 Go/s, PCIe 7,6 Go/s, étude 01) : 2,51 bits [calc.].

**Proposition 3 (qui doit résider : la fréquence décide du placement, la sensibilité des
bits).** Ajoutons une probabilité d'usage $p_i$ par jeton (experts d'un MoE ; $p_i = 1$
pour un modèle dense) : le temps devient $\sum_i p_i n_i b_i/W_i$ et, la matrice n'agissant
que quand elle sert, la perte devient $\sum_i p_i c_i \kappa 2^{-2b_i}$. Alors

(a) $b_i^\star = \tfrac12\log_2(2\ln2\,\kappa c_i W_i / (\lambda n_i))$ : **$p_i$ disparaît**,
les bits ne dépendent pas de la fréquence d'usage ;

(b) la valeur optimale de la contribution de la matrice $i$ vaut
$\Lambda_i(W) = \lambda\, p_i\, n_i \,(\frac{1}{2\ln 2} + b_i^\star(W)) / W$, et le gain à
la rendre résidente est $G_i = \Lambda_i(W_P) - \Lambda_i(W_V)$, qui est **proportionnel à
$p_i$** et, puisque $W_V \gg W_P$, vaut $\approx \lambda p_i n_i (\frac{1}{2\ln2} +
b^\star_{i,P})/W_P$.

*Démonstration.* (a) Dans la condition du premier ordre, $p_i$ multiplie les deux termes et
se simplifie. (b) En $b^\star$, $c_i \kappa 2^{-2b^\star} = \lambda n_i / (2 \ln 2\, W)$ ;
en remplaçant dans $p_i(c_i\kappa 2^{-2b^\star} + \lambda n_i b^\star/W)$ on obtient
$\Lambda_i$. $\square$

**Lecture.** La résidence en VRAM coûte $n_i b_{i,V}^\star/8$ octets de VRAM ; le gain
par octet de VRAM est $\approx 8\lambda p_i (\frac{1}{2\ln2} + b^\star_{i,P}) / (W_P\,
b^\star_{i,V})$, croissant en $p_i$ et faiblement croissant en $c_i/n_i$ (par
$b^\star$, logarithmique). D'où la règle de remplissage : **trier par fréquence d'usage
d'abord, sensibilité ensuite** (sac à dos à ratio, glouton optimal à une matrice près
quand les tailles sont petites devant la VRAM). À notre connaissance, aucun outil publié
ne pose ce problème conjoint (bits, étage) ; Q-Palette (2509.20214) le pose à placement
fixe avec un coût de latence profilée.

**Ce qui pourrait être faux.** (H1) est fausse aux grandes erreurs (2 bits sur un petit
modèle : +78 % de perplexité n'est pas « petit ») ; (H2) suppose la pente de Shannon, alors
qu'un code réel a une pente un peu différente à bas débit ; $c_i$ et $p_i$ ne sont pas
indépendants (un expert rare peut être très sensible quand il sert) ; et le temps des
étages se recouvre (D1), ce qui change $W$ effectif. La règle donne la direction et
l'ordre de grandeur, à mesurer.

---

## D7. Le code emboîté et son prix

**Énoncé repris d'ApexQuant (2610.07904, prop. 3) [litt.].** Une passe de quantification
à $b$ bits par coordonnée, suivie d'une rotation aléatoire fraîche du résidu, réduit la
MSE d'un facteur $\rho^2$ constant ; $P$ passes stockent $Pb$ bits et atteignent
$\rho^{2P}$, qu'un code optimal atteint à $P(b - \Delta_1)$ bits, avec $\Delta_1 = b +
\tfrac12\log_2\rho^2$. Mesuré par eux : $\Delta_1 = 0{,}45$ (scalaire) à 0,10 (treillis).

**Application à troncons [calc.].** Matrice résidente lue en deux passes de 2 bits,
matrice lue par le PCIe en une seule :
- qualité du résident : celle d'un code optimal à $4 - 2\Delta_1$ bits ; un treillis à
  4 bits d'un coup est à $4 - \Delta_1$ ; l'écart est d'une passe, $\Delta_1 \approx 0{,}10$
  bit, soit 2,5 % des octets en VRAM ;
- stockage : 4 bits par poids pour servir les deux étages, contre $2 + 4 = 6$ bits pour
  deux copies indépendantes : $-1{,}9$ bit/poids en tenant compte des 0,10, soit $-32$ %.

---

## D8. Le critère « 2 bits acceptables » et son extrapolation

**Définition (réponse par délégation du 2026-10-15, réversible).** Pour une famille de
modèles de tailles $N$ et $2N$, le 2 bits est acceptable à la taille $2N$ si
$\mathrm{PPL}(2N, b/2) \le \mathrm{PPL}(N, b)$ avec $b \approx 4$ : à octets lus égaux
($2N \cdot b/2 = N b$), comprimer vaut au moins autant que rapetisser.

**Mesuré ici [mes.].** Qwen3.5-4B Q4_K_M : 2,730 Go, PPL 8,723 ± 0,229 ; Qwen3.5-9B
IQ2_XXS : 2,757 Go, PPL 10,605 ± 0,271. Écart : $10{,}605/8{,}723 - 1 = +21{,}6$ %. Les
intervalles à 2 erreurs-types, $[8{,}27 ; 9{,}18]$ et $[10{,}06 ; 11{,}15]$, sont disjoints :
le critère n'est pas franchi à 9B avec IQ2_XXS.

**Le point de croisement des deux fronts [mes., calc.].** Front du 9B : IQ2_XXS (2,757 Go ;
10,605), IQ2_M (3,159 ; 8,612), IQ3_XXS (3,490 ; 7,913). Front du 4B : IQ2_XXS (1,527 ;
15,493), IQ3_XXS (1,894 ; 9,777), IQ4_XS (2,503 ; 8,908), Q4_K_M (2,730 ; 8,723). Par
interpolation linéaire du front du 9B entre IQ2_XXS et IQ2_M, il atteint 8,723 à
$2{,}757 + (10{,}605 - 8{,}723)/(10{,}605 - 8{,}612) \times 0{,}402 = 3{,}137$ Go, soit
$3{,}137 \cdot 8 / 8{,}95 = 2{,}80$ bits par paramètre (enchâssement compris dans le
dénominateur) ou $3{,}137 \cdot 8 / 7{,}94 = 3{,}16$ bits par poids lu (sans la table
d'enchâssement). Au-delà, le 9B comprimé est meilleur que tout le 4B mesuré.

**Extrapolation (deux points seulement : fragile) [calc.].** Perte relative du « IQ2_XXS »
contre la base de la même taille : $\ell(4{,}2\text{B}) = 0{,}777$, $\ell(8{,}95\text{B}) =
0{,}479$. Loi de puissance par ces deux points : $\ell(N) = 0{,}479\,(N/8{,}95)^{\alpha}$,
$\alpha = \ln(0{,}479/0{,}777)/\ln(8{,}95/4{,}21) = -0{,}640$. Le critère demande que
$\ell(2N)$ tombe sous le gain de qualité d'un doublement de taille, mesuré ici à
$8{,}723/7{,}174 - 1 = 21{,}6$ % entre 4B et 9B (et qui diminue lui-même avec la taille).
En le tenant fixe à 22 % : $N = 8{,}95 \cdot (0{,}22/0{,}479)^{1/\alpha} \approx 30$
milliards de paramètres ; s'il tombe à 15 % : $\approx 55$ milliards ; à 10 % : $\approx
100$ milliards. **Avec IQ2_XXS, sur Qwen3.5, le seuil est donc au-delà de 30B**, et plutôt
50 à 100B. Avec un code de deuxième génération (Tetra), Qwen3 franchit le critère à 8B
sur le MMLU [litt.] : le codeur déplace le seuil d'un facteur 4 à 10.

Biais déclarés : base requantifiée (pessimiste d'environ 10 % sur $\ell$, § 8 du livrable),
imatrix sur le même domaine que le test (optimiste), 20 480 jetons d'évaluation.
