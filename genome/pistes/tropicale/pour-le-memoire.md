# La garde tropicale : pour le mémoire (Tome III)

Ce que le rédacteur scientifique porte dans le Tome III, chapitre « La géométrie tropicale du
routeur ». Le livrable de la piste est `garde-tropicale.md` ; ici : les dérivations en entier, les
données des figures, les macros, les sources. Tout chiffre vient d'un fichier commité sous
`mesures/pistes/tropicale/` ; les figures se régénèrent par `outils/pistes/tropicale/figures.py`.

## 1. D'où on part, où on va (pour l'ouverture du chapitre)

- Acquis : les bascules de routage portent l'essentiel de la KL entre deux calculs proches (lot R,
  § 2.9 et § 2.10) ; la marge du routeur les annonce en médiane (0,0095 contre 0,083).
- Établi : la marge seule n'attrape que 57,1 % des bascules pour 10 % des cellules (seuil déclaré
  80 / 10 : la garde tombe) ; elle attrape 85,2 % des racines de cascade (exploration) ; un seul
  nombre sans dimension, κ = σ / E[m], décide de toute garde à marge, et 80 / 10 demande κ ≤ 0,108.
- Reste : le κ du mode rapide (un journal de routage), et la réparation (une passe).

## 2. Les dérivations

### 2.1 Le routeur comme polynôme tropical, et la marge comme distance

Soit z(h) = W_r h + b_r ∈ ℝ³², W_r = [w₁ … w₃₂]ᵀ. Pour un ensemble S de k = 4 indices, la région
P_S = {h : z_i(h) ≥ z_j(h), ∀ i ∈ S, ∀ j ∉ S} est une intersection de k (32 − k) = 112 demi-espaces :
un polyèdre convexe (éventuellement vide). Les P_S recouvrent l'espace et ne se chevauchent que par
leurs bords. La fonction

  F_k(h) = max_{|S| = k} Σ_{i ∈ S} z_i(h)

est un maximum de fonctions affines : un polynôme tropical du semi-anneau (max, +) (« somme » = max,
« produit » = +), convexe et affine par morceaux ; ses morceaux sont exactement les P_S, et le lieu
où F_k n'est pas différentiable (où deux ensembles atteignent le max) est son hypersurface tropicale,
réunion des faces z_i = z_j avec i au rang 4 et j au rang 5. Cadre : Zhang, Naitzat et Lim (arXiv
1805.07091) pour les réseaux ReLU ; le top-k s'y range par la même algèbre.

La marge m(h) = z₍₄₎(h) − z₍₅₎(h) ≥ 0 est nulle exactement sur l'hypersurface. Si les rangs 4 et 5
sont tenus par i et j, la distance euclidienne de h à l'hyperplan z_i = z_j vaut
m / ‖w_i − w_j‖ ; c'est une borne inférieure de la distance à toute frontière de la région, car
tout changement d'ensemble exige qu'un écart entrant-sortant change de signe et que le plus petit
de ces écarts est m. La bande de garde {m < τ} est donc, le long de chaque face, une tranche
d'épaisseur 2τ / ‖w_i − w_j‖ (τ / ‖·‖ de chaque côté), et de demi-épaisseur τ / ‖P(w_i − w_j)‖ dans
une coupe par un plan de projecteur P (figure T6).

### 2.2 Pourquoi la marge est presque exponentielle

Représentation de Rényi (1953) : si X₁, …, X_n sont exponentielles indépendantes de taux λ, rangées
en ordre décroissant X₍₁₎ ≥ … ≥ X₍ₙ₎, les espacements D_k = X₍ₖ₎ − X₍ₖ₊₁₎ sont indépendants et D_k
suit une exponentielle de taux kλ. Pour une loi mère de densité f et de taux de défaillance
h(x) = f(x) / (1 − F(x)), au voisinage du haut de l'échantillon la transformation x ↦ −ln(1 − F(x))
rend les variables exponentielles de taux 1 et, localement, linéaire de pente h(x₍ₖ₎) ; d'où
D_k ≈ Exp(k h(x₍ₖ₎)). La marge m = D₄ est donc, au premier ordre, exponentielle : densité finie et non
nulle en zéro, f_m(0) ≈ 1 / E[m], et P(m < τ) ≈ τ / E[m] pour τ petit.

Mesure (`loi-marge-par-couche.csv`) : forme gamma 0,91 à 1,09 ; pente de log P(m < τ) contre log τ
sur [10⁻⁴ ; 10⁻²] : 0,90 à 1,20 ; KS à l'exponentielle 0,006 à 0,042. Les 32 logits ne sont ni
indépendants ni de même loi ; la conclusion tient.

### 2.3 La loi de bascule

Soient m_B la marge du calcul qui garde (B), et δ la perturbation, entre A et B, de l'écart entre les
experts aux rangs 4 et 5 de B. La cellule bascule dès que l'écart de A passe sous zéro : m_B + δ < 0.
Si δ est indépendante de m_B, de loi symétrique G :

  P(bascule | m_B = m) = G(−m),  et  lim_{m→0} P = G(0) = ½.

(Pour une perturbation gaussienne, Φ(−m/σ) ; la forme 2Φ(−m/σ) écrite dans le protocole déclaré
supposait une bascule certaine en zéro ; elle est fausse par la dérivation et par la mesure : sous
10⁻⁴, 58 bascules sur 106 cellules, 0,55 ± 0,05 ; vraisemblance de Φ au-dessus de celle de 2Φ aux
24 couches, `loi-bascule-sigma.csv`.) C'est une borne inférieure de la probabilité réelle : d'autres
couples que (4, 5) peuvent aussi croiser, mais il leur faut une perturbation plus grande que m.

### 2.4 La forme close de la courbe de la garde : le théorème du nombre de garde

**Hypothèses.** M ~ Exp(λ) ; δ ~ N(0, σ²) indépendante de M ; bascule ⇔ δ < −M ; la garde signale
M < τ. **Notation.** κ = λσ = σ / E[M] ; t = τ / σ ; Φ, φ la répartition et la densité normales.

**Lemme 1.** Pour κ > 0 et u ≥ 0 : e^{−κu} φ(u) = e^{κ²/2} φ(u + κ).
*Preuve.* −κu − u²/2 = −(u + κ)²/2 + κ²/2. ∎

**Lemme 2.** ∫₀^T λ e^{−λm} Φ(−m/σ) dm = ½ − e^{−λT} Φ(−T/σ) − e^{κ²/2} [Φ(T/σ + κ) − Φ(κ)].
*Preuve.* Par parties, avec U = Φ(−m/σ), dV = λe^{−λm} dm, V = −e^{−λm}, dU = −φ(m/σ)/σ dm :
∫₀^T = [−e^{−λm} Φ(−m/σ)]₀^T − ∫₀^T e^{−λm} φ(m/σ)/σ dm = ½ − e^{−λT} Φ(−T/σ) − ∫₀^{T/σ} e^{−κu} φ(u) du,
et par le lemme 1 la dernière intégrale vaut e^{κ²/2} ∫₀^{T/σ} φ(u + κ) du = e^{κ²/2} [Φ(T/σ + κ) − Φ(κ)]. ∎

**Théorème.** La part des cellules signalées est c = 1 − e^{−λτ} ; le taux de bascule est
P(B) = ½ − e^{κ²/2} Φ(−κ) ; la part des bascules signalées est

  b = [½ − e^{−λτ} Φ(−t) − e^{κ²/2} (Φ(t + κ) − Φ(κ))] / [½ − e^{κ²/2} Φ(−κ)],  λτ = −ln(1 − c), t = λτ / κ.

La courbe (c, b) ne dépend que de κ.
*Preuve.* c = P(M < τ). P(B) = lemme 2 avec T → ∞ (les termes en e^{−λT} et Φ(T/σ + κ) → 1 donnent
½ − e^{κ²/2}(1 − Φ(κ)) = ½ − e^{κ²/2} Φ(−κ)). b = P(M < τ, B) / P(B) = lemme 2 en T = τ, divisé par
P(B). Enfin λτ = −ln(1 − c) et t = τ / σ = λτ / κ ne dépendent que de (c, κ). ∎

**Vérification** (second chemin, `theoreme.py` → `theoreme.json`) : quadrature numérique (scipy,
tolérances 10⁻¹³) contre forme close sur 18 couples κ ∈ {0,01 ; 0,05 ; 0,1 ; 0,3 ; 1 ; 3},
c ∈ {1 % ; 10 % ; 30 %} : écart maximal ~~1,3·10⁻¹⁴~~ 3,7·10⁻¹⁵ (forme close écrite par le logarithme de la queue normale, stable pour κ grand). P(B) en κ = 0,2 : 0,0707601917665 (forme close)
contre 0,0707601917664 (quadrature).

**Corollaire (le plafond de 4 %).** b(c = 10 %) décroît et P(B) croît avec κ ; b = 80 % en
κ\* = 0,1079, où P(B) = 4,03 %. Donc, sous ces hypothèses, une garde à marge ne tient 80 / 10 que si
moins de 4,03 % des cellules basculent. Une loi de δ à queue plus lourde, à même P(B), place plus de
bascules à grande marge, donc baisse b : le plafond réel est plus bas. Mesuré : 4,15 % de bascules
entre les deux rampes, b = 57,1 %.

Les limites : κ → 0 donne b → 1 (les bascules se concentrent en m = 0) ; κ → ∞ donne b → c (la marge
ne sait plus rien), ce qui est le témoin T3 (i) vu par la théorie.

### 2.5 L'extrapolation (modèle)

Perturbation multipliée par s, marges inchangées : P(bascule | m) = G(−m/s). Deux G : gaussienne de σ_ℓ
ajusté par vraisemblance, et empirique (δ = m_A − m_B sur les cellules sans bascule à m_B > 0,1, par
couche). Pour les racines, δ est pris sur les seules cellules sans bascule antérieure à la même
position. Validation à s = 1 : toutes les bascules, 49,0 % (gaussien) et 62,1 % (empirique) contre
57,1 % ; racines, 85,3 % et 1 956 racines contre 85,2 % et 2 081. Tableau : `garde-tropicale.md` § 6.2 ;
données `extrapolation-garde.csv`, `cascades.json`.

### 2.6 Les cascades

P(bascule en ℓ + 1 | bascule en ℓ) = 26,6 % contre 3,4 % (`propagation.csv`), et ×75 pour une marge
au-dessus de 0,1. Lecture : après une bascule, δh n'est plus de l'ordre de l'arrondi mais de la
différence entre deux experts ; κ local devient grand ; les bascules suivantes sont hors de portée de
toute garde à marge. Racines : 2 081 (une par position à bascule), attrapées à 85,2 % ; secondaires :
3 006, à 37,7 %.

## 3. Les figures (données commitées, macros dans `figures-tropicale.tex`)

| Figure | Macro | Données | Ce qu'elle montre |
|---|---|---|---|
| T1 | `\GrapheTropicaleCourbe` | `figures/fig-courbe.csv` | la courbe (c, b) : toutes, racines, secondaires, oracle, hasard ; la zone de construction déclarée ; les points 57,1 % et 85,2 % |
| T2 | `\GrapheTropicaleCouches` | `figures/fig-par-couche.csv` | b(τ₁₀) par couche et l'échelle de δ : la profondeur |
| T3 | `\GrapheTropicaleSurvie` | `figures/fig-survie.csv` | P(m > x) en échelle logarithmique : des droites (exponentielles) |
| T4 | `\GrapheTropicaleLoiBascule` | `figures/fig-loi-bascule.csv` | P(bascule \| m), le palier ½, les modèles |
| T5 | `\GrapheTropicaleExtrapolation` | `figures/fig-extrapolation.csv` | b(τ₁₀) quand la perturbation grandit |
| T6 | `\FigureTropicaleCoupe` | `figures/coupe-routeur-c12-{fr,en}.png` | les polyèdres réels du routeur de la couche 12 et la bande de garde |
| T7 | `\GrapheTropicaleKappa` | `theoreme-kappa.csv` | le théorème : b(10 %) et P(B) contre κ, κ\* = 0,108 et la zone de construction |

À ajouter si le rédacteur le veut : les 24 couches placées sur T7 (`theoreme-par-couche.csv`).

Compilation éprouvée le 2026-10-22 : le pilote `outils/pistes/tropicale/pilote-figures.tex` (scrbook,
préambule commun, `\Racine` et `\Depot` posés en absolu) compile les sept figures sans erreur sous
lualatex, en français et en anglais (avertissements seulement de références et de biber, propres au
pilote).

## 4. Les tableaux prêts

- Le verdict et les points de la courbe : `garde-tropicale.md` § 3 (depuis `courbe-garde.csv`).
- Les couches : § 4 (depuis `decile-par-couche.csv`, `cascades-par-couche.csv`).
- Les témoins : § 2 (depuis `temoins.json`).
- La propagation : § 5.4 (depuis `propagation.csv`).

## 5. Les sources

`genome/pistes/tropicale/tropicale.bib` (à porter sous `memoire/sources/`) : Rényi 1953 (notice
vérifiée le 2026-10-22, doi:10.1007/BF02127580) ; Zhang, Naitzat et Lim 2018 (arXiv 1805.07091, déjà
lu par la synthèse le 2026-10-17).

## 6. Ce qui pourrait être faux

Voir `garde-tropicale.md` § 9 ; pour le mémoire, les trois qui comptent : la perturbation mesurée
n'est pas celle du mode rapide ; les racines sont une lecture choisie après coup ; les hypothèses du
théorème (marge exponentielle : vérifiée ; δ gaussienne : fausse dans la queue).

---

## Ajout du 2026-10-26 : la garde à indices multiples (mémoire du conflit)

Pour le Tome III. Livrable : `garde-tropicale.md` § 12. Seuil : `seuil-declare-indices.md`. Sources :
`tropicale.bib` (Botvinick et al. 2001 ; Cavanagh et al. 2011).

**Dérivation à porter : la régression logistique pénalisée par IRLS (Newton).** Pour des indices
centrés réduits z_i (avec 1 en tête) et des étiquettes y_i ∈ {0, 1}, on minimise
J(w) = −Σ [y_i ln p_i + (1 − y_i) ln (1 − p_i)] + (λ/2) ‖w_{1:}‖², p_i = σ(z_iᵀ w), λ = 1, intercept non
pénalisé. Gradient : g = Zᵀ(p − y) + Λw. Hessienne : H = Zᵀ diag(p(1 − p)) Z + Λ, définie positive pour
λ > 0 hors intercept. Pas de Newton : w ← w − H⁻¹ g. Arrêt quand max |Δw| < 10⁻⁹ (au plus 60 pas).
Le score de la garde est le logit z_iᵀ w, monotone en p_i, donc le classement ne dépend pas de la
fonction σ.

**Dérivation à porter : le coût fixé à 10 %.** Dans chaque pli de test (une fenêtre : 24 × 511 = 12 264
cellules) la garde signale exactement K = ⌊0,10 · 12 264⌋ = 1 226 cellules ; la part attrapée est
b = Σ_w (bascules signalées dans w) / 5 087. Ainsi chaque modèle coûte la même chose et ne se distingue
que par le tri.

**Dérivation à porter : le modèle à une seule entrée n'a pas de cassure par étiquettes mélangées.** Avec
un seul indice f1, le score est a·f1 + c, monotone en f1 : le classement est ±f1 quel que soit
l'ajustement. Étiquettes d'entraînement mélangées : a ≈ 0 de signe aléatoire, donc selon le pli on garde
les petites marges (≈ 57 %) ou les grandes (très peu de bascules) : moyenne observée 50,6 %, un mélange des deux signes. La cassure juste permute
les entrées du test (9,97 %).

**Dérivation à porter : l'IC par rééchantillonnage des fenêtres.** Dix fenêtres, 10 000 tirages avec
remise (graine 20261026) ; pour chaque tirage, Δ = 100 · (Σ attrapées M3 − Σ attrapées M0) / Σ bascules
des fenêtres tirées ; IC = centiles 2,5 et 97,5. Il mesure la variation entre fenêtres d'un même
texte.

**Données CSV pour les figures** (sous `mesures/pistes/tropicale/indices/`) :
`indices-resume.json` (b par modèle et par fenêtre, gains, IC, témoins), `complements.json` (ablations,
coefficients, Spearman), `scores-M3.csv` (score de chaque cellule, ordre l, w, p).

**Figures qui méritent d'être faites** (belles et vraies, à tirer de ces fichiers, script commité) :
1. *Forêt des gains* : pour M2, M3, les trois ajouts un à un et les trois retraits, le gain en points
   avec son IC, la ligne des 5 points déclarés en trait plein, 0 en tirets. Elle montre d'un coup d'œil
   que tout est f2 et que rien n'atteint la barre.
2. *Profondeur contre temps* : deux panneaux, la bascule en fonction de ln f2 (conflit plus bas, même
   position) et en fonction de ln f3 (conflit de la position précédente) par classes de quantiles, avec
   leurs Spearman (−0,105 ; −0,029) : la mémoire en profondeur a une pente, la mémoire en temps est
   plate.
3. *Les témoins sur une même échelle* : les valeurs de b (M0, M3, W2, W3, W4, cassure de W1) rangées de
   10 % à 68 %, chacune avec son attendu déclaré en repère : la figure qui montre que l'instrument sait
   tomber et sait voir.

**Mise en regard biologique, à écrire sans en faire une preuve** : le conflit instantané (la marge)
correspond à la détection de conflit de Botvinick et al. ; la relève du seuil sous conflit à l'action
de la garde (refaire en exact) ; la mémoire du conflit à f2 à f4. Résultat : la partie « profondeur »
de la mémoire aide (+1,6), la partie « temps » non. Une analogie qui propose une mesure et qu'une
mesure borne.

**Ce qui pourrait être faux** : voir § 12 du livrable (indices linéaires ou à classes grossières ;
deux rampes exactes et non le mode rapide ; dix fenêtres d'un seul texte ; deux attendus de témoins
déclarés faux et dits).
