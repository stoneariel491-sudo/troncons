# La synthèse de la ronde 1 et le cahier de construction : ce que le Tome III doit porter

Rôle « synthese » de la construction (genome/05-synthese.md), 2026-10-17. Étiquettes : **[mes.]**,
**[calc.]**, **[litt.]**, **[hyp.]**. Données : `mesures/genome/construction/synthese/` ; outil :
`outils/genome/synthese/frontiere.py` ; sources neuves : `memoire/sources/genome-construction-synthese.bib`
(les autres sont dans les `.bib` des quatre équipes : `genome-etat-de-l-art.bib`, `genome-genome.bib`,
`genome-predictif-elagage.bib`, et la note de la duplication).

## 0. D'où l'on part, où l'on va (pour l'ouverture du chapitre)

- **Acquis** : le format `.trc` v1.0 exact au bit, 3,8434 bits par poids (A_flux) ; la base de B,
  2,6441 bits ; quatre équipes, quatre livrables, trois protocoles de KL.
- **Établi** : une frontière commune sur un seul juge (la KL, en rapport à la base du même protocole
  et en différence appariée) ; trois gagnants, tous synonymes ; trois propriétés des poids qui
  expliquent chaque échec ; la décomposition de la KL en part lisse et queue de bascules ; le cahier
  des lots A (v1.2) et B (compagnon rapide), avec leurs critères déclarés.
- **Reste** : construire A et B ; B0 décide la variante de B ; la garde tropicale se chiffre sur des
  journaux qui existent déjà.

## 1. Plan proposé du chapitre (Tome III, « Le génome des poids : de la ronde à la construction »)

1. La question de la ronde, et le juge (pourquoi la KL, et pas l'erreur de poids ni l'erreur d'expert).
2. Les trois protocoles et la règle de comparaison (rapport, différence appariée, blocs de fenêtres).
3. La frontière commune (figure F1) ; le tableau des 23 points.
4. Les trois propriétés des poids (bruit sachant l'échelle ; colonnes géantes ; erreur d'expert ≠ KL),
   chacune avec ses mesures croisées (figures F2, F6, F7).
5. La forme de la KL : part lisse, queue de bascules ; la preuve par le routage imposé (figure F3).
6. Mécanisme par mécanisme : gagnants et perdants, la propriété qui les a décidés (tableau de 05 § 2.3).
7. Les pistes : la géométrie tropicale (figure F4), le pont, la fractale.
8. Le lot A : le format v1.2 au bit près (figure F8), la proposition A1, le lemme A2, les critères.
9. Le lot B : le compagnon rapide, le codeur (figure F5 : la transformation avant et après), le lemme
   B2 (figure F9), les critères.
10. Ce qui pourrait être faux.

## 2. Les énoncés et leurs démonstrations (à porter en entier)

- **Proposition A1** (la GEMV du moteur rend les mêmes bits avec les codes canoniques) : 05 § 4.2.
  Démonstration en deux temps : (1) l'accumulateur ne vaut jamais −0 (départ à +0, et une somme exacte
  nulle s'arrondit à +0 en arrondi au plus près) ; (2) un pas sur un code nul est donc identique dans
  les deux calculs. Elle renforce la proposition de 01 § 4.2, qui laissait le signe d'une somme
  partielle nulle.
- **Lemme A2** (la LUT compacte en demi-octets rend la même suite de symboles) : 05 § 4.4.
- **Lemme B2** (le brouillon spéculatif doit être résident ; condition α > 1 − ρ + b_d / b_e) :
  05 § 4.11, et ses quatre corollaires.
- **Le contexte d'un symbole de CODES_COL** : la chaîne (w, k) → n = 8w + k → (β = ⌊n/32⌋,
  u = n mod 32) → i(u) = ⌊u/2⌋ + 16 (u mod 2) → col = (β mod B)·32 + i(u) → contexte 4κ(β) + q(col)
  (05 § 4.3), à poser comme une dérivation, avec la disposition de `block_mxfp4`.
- **La KL au second ordre** (pour la « part lisse ») : pour des logits z et une perturbation δz,
  KL(softmax(z) ‖ softmax(z + δz)) = ½ δzᵀ (diag(p) − p pᵀ) δz + O(‖δz‖³), la matrice étant
  l'information de Fisher de la loi catégorielle paramétrée par ses logits. Dérivation : développer
  log Σ exp(z + δz) à l'ordre 2 ; le terme d'ordre 1 s'annule contre l'espérance de δz sous p. À
  écrire en entier dans le chapitre (calcul classique, posé pas à pas).
- **La part de bascule** (forme seulement, [hyp.]) : E[KL] ≈ E[½ δzᵀ F δz] + Σ_ℓ P(m_ℓ < |δs_ℓ|) ·
  E[KL | bascule à ℓ], où m_ℓ est la marge du routeur de la couche ℓ et δs_ℓ la perturbation de
  l'écart des deux scores en jeu ; le second terme ne dépend de ‖δh‖ que par une probabilité, et sa
  valeur conditionnelle par la différence de deux experts (33 à 84 % de l'énergie de sortie selon la couche, mesurée
  par la duplication).
- **Le cadre tropical du routeur** : les régions de top-k sont des polyèdres (intersections des
  demi-espaces z_i ≥ z_j) ; la somme des k plus grands logits est un polynôme tropical convexe ; la
  distance euclidienne d'un état à la frontière la plus proche vaut m / ‖w₍₄₎ − w₍₅₎‖ (05 § 3.1).

## 3. Les tableaux (tirés des CSV, jamais recopiés)

| Tableau | Source |
|---|---|
| les trois protocoles de KL | 05 § 1.1 ; journaux `kl-*` des trois équipes |
| les 23 points de la frontière | `frontiere.csv` |
| erreur d'expert contre KL | `erreur-contre-kl.csv` |
| la colonne, tenseur par tenseur, et la règle des 0,015 bit | `colonne-par-tenseur.csv` ; `apparie-eclaireur.json` (`colonne`) |
| les quantiles de la KL (médiane, 99e, 99,9e, maximum) | journaux du juge (`kl-frontiere-juge.json`, `kl-synonyme-d1-juge.json`, `comparer-base-contre-recette.json`) |
| la différence appariée de l'éclaireur | `apparie-eclaireur.json` |
| les champs du format v1.2 | 05 § 4.3 |
| les critères A-T1 à A-C4 et B0 à B5 | 05 §§ 4.6 et 4.10 |

## 4. Les figures que ce travail mérite (belles et vraies)

Toutes se tirent des données commitées par un script commité (`memoire/figures/` ou
`outils/genome/synthese/`), dans la direction artistique du mémoire, et passent devant le juge de design.

- **F1. La frontière commune** (`frontiere.csv`, données prêtes). Deux panneaux. À gauche, le plan
  (bits par poids lus, rapport de KL à la base du même protocole), vertical logarithmique ; une forme
  de marqueur par protocole, une teinte par équipe ; gagnants pleins, perdants creux ; pour chaque
  perdant, une flèche fine vers sa « promesse » à erreur de poids ou d'expert égale (sa position sur
  l'axe des bits seul) : la figure montre la distance entre ce que promettait la métrique intermédiaire
  et ce que la KL a rendu. À droite, l'axe sans perte agrandi, 3,8434 → 3,7064 → 3,6843, en barres
  empilées par tenseur : la colonne ne vit qu'à la couche 0.
- **F2. L'erreur d'expert ne prédit pas la KL** (`erreur-contre-kl.csv`, prêtes). Un nuage, abscisse le
  rapport d'erreur d'expert, ordonnée le rapport de KL, axes logarithmiques, la diagonale y = x en
  pointillé, la zone « gagne en KL » (y < 1) teintée : trois points dans la même bande d'abscisse
  (0,74 à 1,03) et des ordonnées de 1,02 (S\*, 10 fenêtres) à 3,06 ; le synonyme seul sous 1. Le point de S\* se tire de la passe K10 (`frontiere.py --k10`, une fois son journal commité).
- **F3. Deux parts de la KL, position par position** (`kl-frontiere-positions.csv` et
  `kl-synonyme-d1-positions.csv` de l'éclaireur, prêtes). Nuage log-log de 2 550 points (KL de la base,
  KL du synonyme), la diagonale, des densités marginales ; la masse du nuage passe sous la diagonale
  (la part lisse divisée par 2,3 à la médiane) pendant que les points du coin haut restent sur elle (la
  queue des bascules). Une couleur par fenêtre montre que les queues sont groupées par fenêtre (le
  passé commun). C'est la figure qui fait comprendre pourquoi la moyenne et la médiane se contredisent.
- **F4. Les régions du routeur comme polyèdres** (à tirer : poids du routeur `blk.ℓ.ffn_gate_inp` du
  GGUF, états normés capturés par l'éclaireur, `h-Lll.f32`, qui sont exactement l'entrée du routeur).
  Une tranche affine de dimension 2 de l'espace des états (2 880 dimensions), passant par un état réel
  h₀ et engendrée par w₍₄₎ − w₍₅₎ et une seconde direction de score ; dans la tranche, l'ensemble top-4
  est constant sur des polygones convexes, calculés exactement (arrangement de droites z_i = z_j) ; une
  couleur par ensemble ; h₀ marqué, sa marge en segment jusqu'à la frontière la plus proche ; les
  perturbations δh de la base frontière et du synonyme en flèches (l'une franchit la frontière,
  l'autre non, sur une position où la mesure le montre). En 3D (Blender, rendu sur la RTX 4060) :
  la même tranche en dimension 3, les cellules en volumes translucides. Vraie par construction : la
  géométrie est celle du routeur réel, restreinte à une tranche dite.
- **F5. La transformation de la mutation synonyme, avant et après** (à tirer : `synonyme.py` sur une
  matrice, captures de calibration). (a) Le spectre de H (valeurs propres triées, log) ; (b) en
  dessous, l'énergie de l'erreur ΔW projetée sur chaque vecteur propre de H, pour la base frontière et
  pour le synonyme : la frontière répartit son erreur à plat, le synonyme la pousse vers les directions
  de petite valeur propre, « les directions muettes des entrées » ; l'aire sous le produit des deux
  courbes est l'erreur de sortie. (c) Une rangée de 32 poids d'un bloc : la valeur exacte, la
  reconstruction frontière et la reconstruction synonyme, et les codons qui changent marqués : la
  mutation est visible, synonyme pour la sortie.
- **F6. Le codon synonyme du zéro** (à tirer : `histo-12-gptoss20b.npz`, `zero-compte-*.json`). La roue
  des seize codes E2M1 (signe, deux bits d'exposant, un bit de mantisse), +0 et −0 fondus en un seul
  secteur ; à côté, l'histogramme P(+c) contre P(−c) sur les 16 codes (égaux à 10⁻⁴) et la pièce de
  monnaie du signe des zéros (0,9999999967 bit) ; en bas, la disposition de l'octet MXFP4 avant et
  après la canonisation.
- **F7. Les colonnes géantes** (prêtes en partie : `mesures/genome/genome/csv/colonnes-energie-erreur.csv`
  pour blk.8 down expert 16 ; à tirer pour les autres). L'énergie de chaque colonne (2 880, triées) et
  l'erreur du brin sur chacune, en échelle log : la colonne 1011 à ×144 d'énergie et ×334 d'erreur ;
  en regard, la carte des classes de colonne de blk.0 gate (la seule qui paie) en bande de couleur.
- **F8. Le format v1.2 au bit près** (TikZ, depuis 05 § 4.3) : l'en-tête avec les champs changés
  (version, drapeaux 3 et 4, octet 123) surlignés ; un enregistrement de carte des colonnes ; et le
  chemin d'un demi-octet de CODES_COL : (voie, macro-pas, sous-pas) → w, k → n → bloc et position →
  colonne → contexte 4κ + q, dessiné sur un bloc de 16 octets.
- **F9. Où le brouillon paie** (calculée, lemme B2) : le plan (ρ, α), la droite α = 1 − ρ + b_d/b_e pour
  b_d/b_e ∈ {0 ; 0,35 ; 0,7}, la région rentable au-dessus ; le point ρ ≈ 0,03 du routage indépendant
  (120b) ; en repères horizontaux, les accords mesurés par fondations/05 (76,8 % ; 82,1 % ; 91,9 %).
- **F10. L'espace latent des états et des régions** (à tirer : `h-L23.f32`, routage capturé). Une
  projection (ACP, puis une projection non linéaire si elle reste fidèle, fidélité dite comme l'a fait
  la duplication) des 6 132 états de calibration de la couche 23, colorés par leur expert premier, la
  taille des points par la marge du routeur : les états de petite marge dessinent les frontières entre
  les nuées. Rendu 3D possible.

## 5. Les données de mesure (CSV) prêtes pour les figures

- `mesures/genome/construction/synthese/frontiere.csv` (F1)
- `mesures/genome/construction/synthese/erreur-contre-kl.csv` (F2)
- `mesures/genome/construction/synthese/colonne-par-tenseur.csv` (F1 droite, F7)
- `mesures/genome/etat-de-l-art/journaux/kl-frontiere-positions.csv`,
  `kl-synonyme-d1-positions.csv` (F3)
- `mesures/genome/genome/kl/comparer-base-contre-recette.csv` (F3 variante pour S\*)

## 6. Ce qui manque au mémoire, dit

- Les scripts de F4, F5, F6, F7 (autres tenseurs), F10 : aucun n'est écrit.
- La garde tropicale n'a pas de mesure ; F4 l'illustre, elle ne la prouve pas.
- La KL de λ = 1 (B0) changera le point « mutation synonyme » de F1 : la figure doit se régénérer après
  B0.
- Les sources neuves ne sont lues qu'au résumé (Zhang, Naitzat et Lim ; Martin et Mahoney).
