# P3, routage conditionné par le cache : ce qu'il faut au mémoire (dérivations, données, figures)

Écrit le 2026-10-27. Les chiffres viennent de `mesures/mimetisme/P3/` (étage A, affinage) ; chaque grandeur dérivée dit d'où elle sort. Étiquettes : **[mes.]**, **[calc.]**, **[hyp.]**.
Source primaire : Skliar et al., arXiv 2412.00099 (`memoire/sources/p3-routage.bib`).

## 1. Le problème posé en géométrie

Un routeur de gpt-oss-20b rend, par cellule (position t, couche ℓ), 32 logits z ∈ ℝ³². L'ensemble choisi S(z) est celui des quatre plus grands logits. Dans ℝ³² les régions {z : S(z) = S₀}
sont des cônes polyédriques : leurs parois sont les hyperplans {z_i = z_j}, i ≠ j, de l'arrangement des tresses (celui du permutoèdre), et la paroi qui compte pour S est l'ensemble tropical
{z : z₍₄₎ = z₍₅₎} où la **marge** m(z) = z₍₄₎ − z₍₅₎ s'annule. La marge est la distance (à √2 près) de z à la paroi la plus proche qui change S.

Le biais de Skliar et al. est une **translation** z' = z + β·1_R, où 1_R est l'indicateur des experts résidents. Il ne bouge pas la géométrie des régions : il déplace le point z, ce qui revient à décaler, pour
une paire (a absent, b résident), la paroi z_a = z_b en z_a = z_b + β (figure `figures/fig-paroi.tex` : plan (z_b, z_a), bande de largeur β entre les deux parois). **Toute cellule dont le point tombe dans cette bande
change de choix** : a était pris, b l'est maintenant. La part de cellules changées est donc la masse de probabilité de la bande.

## 2. La masse de la bande, mesurée

Sur les 122 640 cellules, la fonction de répartition de la marge est connue à 3e-6 près (recalcul indépendant des journaux de M3, `etage-A.json`) [mes.] :

| β (unités de logit) | 0,01 | 0,03 | 0,1 | 0,3 |
|---|---|---|---|---|
| P(m < β) | 0,0818 | 0,2240 | 0,5632 | 0,9035 |
| densité moyenne P(m<β)/β | 8,2 | 7,5 | 5,6 | 3,0 |

La masse croît presque linéairement jusqu'à β ≈ 0,03 (densité de marge près de zéro g(0) ≈ 8 par unité de logit) puis sature : à β = 0,3, 90 % des cellules ont une marge sous β. Δavg (étendue moyenne des logits) = 4,136 : β = 0,1
est donc λ = 0,024 dans la normalisation de l'article.

## 3. Part de cellules changées, variante 4e/5e seul (V2)

V2 change une cellule exactement quand m < β, que le 4e (a) est absent et que le 5e (b) est résident. Si l'événement {m < β} était indépendant de la résidence :

part changée(β) = P(m < β) · P(a absent) · P(b résident | a absent).

Mesuré [mes., V2 et `etage-A.csv`] : part changée / P(m<β) = **0,237 ; 0,232 ; 0,225 ; 0,210** à β = 0,01 ; 0,03 ; 0,1 ; 0,3 pour N = 146, et 0,222 ; 0,213 ; 0,203 ; 0,188 pour N = 238.
Le rapport est presque constant en β : c'est bien un facteur de résidence, indépendant de la marge, à quelques pour cent près (la légère baisse viendrait des marges larges, où le 5e serait moins corrélé au 4e : [hyp.], non testé).
Avec P(a absent) lu dans les défauts de rang 4 de β = 0 [mes.] (66 765/122 640 = 0,544 à N = 146 ; 36 926/122 640 = 0,301 à N = 238), on déduit P(b résident | a absent) = 0,437 et 0,738 [calc., sous indépendance]. Ces
deux valeurs sont plausibles : le 5e est moins résident que la moyenne du cache (succès global 0,559 et 0,779) et d'autant moins que le cache est petit.

## 4. Rendement : un échange évite plus d'un défaut

Dans les cellules V2 changées, le 4e absent n'est pas chargé : un défaut en moins, immédiatement. Mesuré : à β ≤ 0,1, chaque expert échangé évite **1,44 à 1,57** défauts à N = 146 et 1,18 à 1,25 à N = 238
[mes., `etage-A.csv`, défauts évités / (cellules changées × experts changés par cellule)]. L'excédent sur 1 (0,2 à 0,6 défaut par échange) est dynamique : le résident b reçoit une mise à jour de récence (il sera encore là au
prochain besoin), et l'absent a n'entre pas dans le cache, donc n'évince pas un expert utile. La borne statique de E7 (compter les défauts de rang 4 de marge < τ) est respectée : le rapport mesuré sur cette borne est
0,53 à 0,78 [mes.] (tolérance 1,5), car elle suppose le 5e résident à coup sûr, ce qui coûte un facteur P(b résident | a absent) ≈ 0,44 à 0,74, un peu compensé par ce 1,2 à 1,6 de rendement.

Dans le plan (part de cellules changées, défauts évités), V1 et V2 se superposent (figure `figures/fig-pareto.tex`) [mes.] : à β ≤ 0,1, V1 change 1,00 à 1,02 expert par cellule, donc V1 ≈ V2. La monnaie du levier est
le nombre de cellules changées, avec un taux de change de 1,47 défaut par cellule (N = 146) et 1,21 (N = 238) au point −10 % [calc. : 0,1 × défauts_0 / (part changée × 122 640)].

## 5. Le critère de décision de l'étage B, posé en une grandeur

Soit f*(N) la part de cellules à changer pour atteindre −10 % de défauts [mes., franchissement interpolé de l'affinage] : f*(146) = 11,98 %, f*(238) = 7,31 %. Soit κ la KL excédentaire par part unitaire de cellules changées
(KL = κ·f, en régime linéaire). Le seuil de succès de l'étage B (KL ≤ 0,038 à −10 %) s'écrit

  κ ≤ κ_max(N) = 0,038 / f*(N) = **0,317** (N = 146) et **0,520** (N = 238).

Le seul chiffre que l'on connaisse de κ est celui des bascules spontanées entre deux moteurs presque exacts : κ₀ = (0,0145 − 0,00168) / (5 087/122 640) = 0,309 [calc. sur mes., 05 § 2.2]. Il est à 2,5 % **sous** κ_max à N = 146 (une marge infime) et à 40 %
sous κ_max à N = 238. La mort (0,07) correspond à κ = 0,584 (N = 146) et 0,958 (N = 238). Lire l'étage B comme la mesure de κ à β ≈ 0,06 : κ < 0,317 donne « tient aux deux budgets » ; 0,317 à 0,52 « tient à N = 238 seulement » ; 0,52 à 0,584 « non concluant » ; κ > 0,584 « tombe » (à N = 146 ; à N = 238 le seuil de mort est 0,958).
C'est aussi la bonne forme pour le mémoire : un théorème de seuil, κ_max = ε/f*, où ε = 0,038 est la pente linéarisée du mode rapide (P6) fois 10 points.

## 6. Figures (sources et données commitées)

- `figures/fig-pareto.tex` (pgfplots, compilé) : défauts évités contre cellules changées, V1 et V2, deux budgets, repères à −10 % et à 12 % (KL a priori 0,037). Données : `mesures/mimetisme/P3/series/*.csv`, produites par
  `outils/mimetisme/P3/p3_series.py` depuis `affinage.csv`. Direction : deux teintes (bleu froid V1, orange brûlé V2), repères gris tiretés, grille fine ; la superposition des deux courbes est le message.
- `figures/fig-paroi.tex` (TikZ, compilé) : la paroi du routeur et sa copie décalée de β dans le plan (z_b, z_a) ; la bande hachurée est la masse changée. Schéma, pas une mesure : il est étiqueté ainsi.
- À faire (données déjà là) : (i) la fonction de répartition de la marge par couche, en heatmap couche × quantile (les 24 distributions sont dans `logits-20b-eval.npy`, hors dépôt, 31 Mo ; le script se tire de `p3_routage.preparer`) ;
  (ii) la projection 2D de l'espace des logits des 5 110 positions d'une couche (ACP des 32 logits), colorée par résidence du 4e expert, avec la bande de largeur β en transparence : montre la masse de la bande dans l'espace latent du routeur ;
  (iii) la courbe KL(f) de l'étage B, avec κ_max et κ₀ en droites, dès qu'elle existe.

## 7. Données et sources

- CSV : `etage-A.csv` (grille officielle, variantes, négatifs), `affinage.csv` (grille officielle + fine), `series/*.csv` (pour pgfplots), `etage-A.json`/`affinage.json` (témoins, fenêtres, LFU), `cassures-reelles.json`, `fichiers-B.json` (empreintes des ensembles pour l'étage B).
- BibTeX : `memoire/sources/p3-routage.bib` (Skliar et al., 2025).
- Outils : `outils/mimetisme/P3/p3_routage.py` (étage A et témoins), `p3_affinage.py`, `p3_cassures_reelles.py`, `p3_fichiers_B.py`, `p3_series.py`.
