# P5 pour le mémoire : le choix des symboles synonymes comme verre de spin

Note de matière pour le mémoire (Tome III, chapitre « mimétisme »). Les chiffres viennent des fichiers commités sous
`mesures/mimetisme/P5/` ; les figures se régénèrent par `outils/mimetisme/P5/figures.py` depuis les CSV écrits à côté.
Étiquettes : **[mes.]** mesuré ici, outil et journal commités ; **[calc.]** calculé ici ; **[lu]** source lue ;
**[mém.]** de ma mémoire, non relu à la source.

---

## 1. Le problème, posé sans rien emprunter

Une rangée de matrice d'expert : n = 2 880 poids w_j, par blocs de 32 qui partagent une échelle s_b = 2^(e_b − 128)
(MXFP4). La mutation synonyme du lot B range chaque poids dans un des **k = 8 niveaux** ± c_m · s_j
(m = 0…3, c = (0,4743 ; 2,8486 ; 6,8372 ; 12) en grandeurs doublées ; centres de `centres.json`). On note
q_j le niveau choisi et r = w − q le résidu. L'erreur de sortie, moyennée sur les entrées x_i du modèle pondérées par
le carré g_i² du poids du routeur, est

  E_err(q) = rᵀ H r,  H = (1 / Σ g_i²) Σ_i g_i² x_i x_iᵀ + δ · m̄ · I,  m̄ = moyenne de diag(H sans amortissement).

Le second terme (amortissement δ, valeur déployée δ = 1) est l'ingrédient de GPTQ ; on y ajoute le coût de code :

  E(q) = rᵀ H r + λ′ Σ_j ℓ(q_j),  ℓ(m) = −log2 p_m (longueur de code du niveau m).

**Fait 1 (variation d'un seul poids).** Si l'on remplace q_j par un autre niveau, le résidu change de
δr = (niveau actuel) − (niveau nouveau) en position j seulement. Alors, par développement du carré,

  E(q′) − E(q) = 2 δr (H r)_j + δr² H_jj + λ′ (ℓ(m′) − ℓ(m)).

Maintenir le vecteur H r demande de lui ajouter δr · H[j, :] à chaque changement accepté : un changement coûte
n opérations, l'évaluation des k − 1 candidats d'une coordonnée coûte O(k) seulement. C'est ce qui rend les balayages
praticables (noyau `outils/mimetisme/P5/p5core/src/lib.rs`, fonction `balayage`). Vérifié [mes.] : l'énergie tenue de
façon incrémentale égale l'énergie recalculée de zéro à 1,3·10⁻¹⁵ relatif (`une` : `coherence_noyau_numpy`).

## 2. Trois lectures du même objet

### 2.1 Le plus proche vecteur (ce que Babai résout à moitié)

Soit H = V Vᵀ avec V triangulaire **supérieure** (c'est la factorisation de Cholesky de l'anti-diagonale retournée, cf.
`synonyme.py::facteur_inverse`). Alors E_err = ‖Vᵀ r‖² = Σ_i (Σ_{j ≤ i} V_ji r_j)². Le terme i ne dépend que des
résidus r_1 … r_i. Le premier terme ne dépend que de r_1 : on choisit q_1 qui le minimise. Le deuxième dépend de
r_1 (déjà fixé) et r_2 : on choisit q_2 qui le minimise, etc. C'est l'algorithme du **plan le plus proche de Babai** ;
Chen, Shabanzadeh, Crnčević, Hoefler et Alistarh montrent que GPTQ lancé de l'arrière vers l'avant lui est
mathématiquement identique [lu : « The Geometry of LLM Quantization: GPTQ as Babai's Nearest Plane Algorithm »,
arXiv 2507.18553, 2025, ICLR 2026, https://arxiv.org/abs/2507.18553, page lue le 2026-10-27].
Chaque terme est minimisé **exactement** sachant le passé, mais jamais en regardant l'avenir : le choix de q_i qui
minimise le terme i peut rendre les termes suivants plus chers. Babai est donc optimal si et seulement si, pour chaque
coordonnée, le meilleur choix local est aussi le meilleur choix global. Le témoin W1 chiffre à quel point c'est faux
quand H est mal conditionné (§ 4).

### 2.2 L'énergie d'un verre de spin

Écrivons le niveau de la coordonnée j par un état de Potts à k valeurs, σ_jm ∈ {0, 1}, Σ_m σ_jm = 1, de sorte que
r_j = w_j − s_j Σ_m c_m σ_jm. Alors

  E = const − 2 Σ_{j,m} h_{jm} σ_jm + Σ_{j,j′,m,m′} J_{jj′}^{mm′} σ_jm σ_j′m′,
  h_jm = s_j c_m (H w)_j,  J_{jj′}^{mm′} = H_{jj′} s_j s_j′ c_m c_m′.

C'est la forme d'un modèle de Potts à couplages dispersés sur le graphe **complet** (n = 2 880 sites, 8 états par
site) : un verre de spin de champ moyen. Les couplages ne sont pas des tirages indépendants : H est la somme de N
termes de rang un (N = 762 à 1 329 entrées de calibration par expert, mesuré), plus l'amortissement. Écrite ainsi,
E_err = (1/Σg²) Σ_i g_i² (x_i · r)² + δ m̄ ‖r‖² : on cherche un vecteur **discret** presque orthogonal à N motifs
x_i. C'est le cadre du perceptron binaire symétrique, dont le paysage de solutions a été étudié par Aubin, Perkins et
Zdeborová (« Storage capacity in symmetric binary perceptrons », J. Phys. A 52, 294003, 2019, arXiv 1901.00314 [lu :
résumé, pas l'article en entier]) : ils conjecturent une structure de solutions « gelée » (frozen-1RSB), signe d'un
paysage où les algorithmes locaux butent. Cette parenté est un cadre, pas un résultat : leur modèle a des motifs
gaussiens indépendants et des poids ±1 ; le nôtre a des motifs corrélés (colonnes géantes), 8 niveaux par site et un
amortissement isotrope. Le rapport N/n = 0,26 à 0,46 est dans la zone où ce cadre parle.

### 2.3 La mesure de Gibbs et ses deux algorithmes

À température T on définit π_T(q) ∝ exp(−E(q)/T). Deux dynamiques la préservent.

**Bain thermique sur une coordonnée.** On redessine q_j parmi les k niveaux avec la probabilité
p_m ∝ exp(−ΔE_m / T), où ΔE_m est la variation du Fait 1. Cette loi est exactement π_T conditionnée aux autres
coordonnées : la chaîne vérifie l'équilibre détaillé, π_T(q) P(q → q′) = π_T(q′) P(q′ → q), car
P(q → q′) = π_T(q′) / Σ_m π_T(q avec j ← m). À T → 0, p_m se concentre sur le minimum : c'est la **descente cyclique**
de coordonnées (CD, QuantEase [mém.]), qui ne change plus rien quand aucune coordonnée seule ne peut baisser E.

**Échange de répliques** (Hukushima et Nemoto, J. Phys. Soc. Jpn 65, 1604, 1996 [mém.] ; Swendsen et Wang 1986 [mém.]).
On fait tourner nt copies aux températures T_1 < … < T_nt et l'on propose d'échanger les états de deux copies voisines.
Dans l'espace produit, la loi stationnaire est ∏_a π_{T_a}(q_a). Échanger q_a et q_b multiplie son poids par
exp((β_a − β_b)(E_a − E_b)), β = 1/T ; l'acceptation de Metropolis min(1, exp((β_a − β_b)(E_a − E_b)))
rétablit l'équilibre détaillé. Les copies chaudes franchissent les barrières, les copies froides raffinent : l'état froid
reçoit de l'état chaud des configurations de bassins différents. **Le recuit simulé** (Kirkpatrick, Gelatt, Vecchi,
Science 220, 671, 1983 [mém.]) est la même idée sans échange (une seule copie dont T décroît).

Réglage retenu (étape 1) : 8 températures, T = (0,02 … 1,0) × e_b où e_b est l'erreur moyenne par poids de Babai
dans les unités de H ; échange tous les balayages, parité alternée ; taux d'échange mesuré 12 à 22 % ; 40 balayages ;
puis trempe à T = 0 du meilleur état visité. Toutes les copies partent de la solution de Babai (le recuit ne peut donc
pas être pire que Babai à l'énergie d'entraînement).

## 3. Les témoins et ce qu'ils ont dit

Tous **[mes.]**, journaux dans `mesures/mimetisme/P5/temoins-*.json`, `W3-sphere-n16.json`.

| Témoin | Montage | Résultat |
|---|---|---|
| W1 force brute | 10 poids, 5 niveaux (9 765 625 états), 1 000 matrices H corrélées (spectre log-uniforme sur 3 décades, conditionnement médian 334) | Babai n'atteint **pas** l'optimum sur 847 instances sur 1 000 (excès d'énergie médian 106 %, maximum ×33) : l'instrument peut tomber |
| W1 PT, première passe | 200 balayages, 8 températures de 0,03 à 1,5 | échoue sur 43 / 1 000 (4,3 %) : **barré**, ce réglage est trop court |
| W1 PT, réglage final | 3 000 balayages, 12 températures de 0,01 à 3 | **1 000 / 1 000** instances à l'optimum de la force brute (dont les 847 où Babai échoue) |
| W2 (i) | PT à 0 balayage, sans trempe | rend Babai exactement (1 000 / 1 000) |
| W2 (ii) | températures gelées (1e-9) | retrouve l'optimum sur 107 / 847 seulement : la machinerie tombe quand on lui retire sa chaleur |
| W2 (iii) | H permuté | 2 / 847 : tombe |
| W1 second énumérateur | numpy pur, par morceaux, 12 instances | égal au Rust à 1e-9 sur 12 / 12 |
| W3 sphère | décodage de Fincke et Pohst (énumération bornée par le rayon de Babai), n = 16, 10 instances, grille réelle, bloc 16 × 16 réel de H (amortissement 0,01) | PT = sphère sur 10 / 10 ; Babai non optimal sur 6 / 10, de 8 % à 44 % au-dessus de l'optimum |
| W4 | Babai générique contre `synonyme.py::choisir`, 8 rangées × 256 colonnes | 0 symbole différent sur 2 048 |

Lecture : à petite dimension et conditionnement fort, le **verre de spin est réel** (Babai perd jusqu'à ×33 sur le jouet,
44 % sur un bloc réel de 16 colonnes à amortissement faible) et le PT le résout. La question de la piste est si ce
verre existe aussi **à n = 2 880 et δ = 1**, où l'amortissement l'adoucit.

## 4. Résultat sur le H réel (étape 1, poids synthétiques)

Huit instances (couches 0, 8, 16, 23 × experts 0, 16), 64 rangées gaussiennes quantifiées MXFP4, δ = 1, débit égal
±0,005 bit. Gain = 1 − erreur(méthode) / erreur(Babai à λ = 0), par instance, médianes sur les 8 [mes.] :

| | descente cyclique | échange de répliques |
|---|---|---|
| baisse de l'objectif optimisé (H amorti) | 6,8 % | 7,8 % |
| baisse sur la calibration (H brut) | 51,5 % | 54,6 % |
| **baisse sur l'évaluation tenue à l'écart** | **5,5 %** (0 instance sur 8 ≥ 10 %) | **6,8 %** (1 sur 8 ≥ 10 %) |

Le seuil de succès (≥ 10 % sur ≥ 6 sur 8) n'est pas atteint ; le seuil de mort (< 3 % en médiane) non plus :
**OUVERT, loin du seuil de succès**. Les écarts de l'objectif à l'évaluation sont des **rapports de 8 à 10** : l'optimiseur
est bon sur ce qu'on lui demande, et ce qu'il apprend ne se transfère presque pas.

### Pourquoi (figure `spectre-erreur`)

Décomposons l'erreur dans la base propre (λ_k, u_k) de H_train : E = Σ_k e_k (u_kᵀ H u_k), e_k = ‖ΔW u_k‖². La
frontière répartit l'erreur de poids à peu près uniformément sur les directions (panneau gauche, courbe grise). Un
optimiseur qui minimise Σ λ_k e_k à budget d'erreur de poids à peu près fixé la **déplace vers les directions de λ_k
petit** : c'est ce que montrent les panneaux : −38 % d'erreur d'évaluation dans les trois premiers groupes de directions
(Babai 0,00602 → CD 0,00373, L8-E0, 32 rangées), mais +6 % dans les onze autres (0,01225 → 0,01303). Les sept derniers
groupes sont dans le **noyau de la calibration** (rang ≤ 762 à 1 329 sur 2 880) : le H brut de calibration y vaut zéro
(colonne `part_calib` du CSV), seul l'amortissement les voit, et pourtant l'évaluation y place 40 % (Babai) à 47 %
(CD) de son erreur. Le mécanisme est celui d'un modèle appris sur N exemples en dimension n > N : l'énergie
empirique est plate là où l'énergie vraie ne l'est pas.

### L'amortissement (figure `delta`)

Erreur d'évaluation moyenne rapportée à Babai à δ = 1 (le déployé) [mes.] : Babai 1,157 (δ = 0,1), 1,040 (0,3), 1,000 (1),
1,044 (3) ; CD 1,191, 1,039, 0,946, 0,946 ; PT 1,196, 1,025, 0,935, 0,945. Deux faits. (1) δ = 1 est près de l'optimum de
Babai ; l'optimiseur n'abaisse pas le meilleur δ. (2) À δ = 0,1 et 0,3 l'optimiseur sur-ajuste et ne bat pas Babai à δ = 1.
Un tableau de verdict par δ qui compare à Babai **au même δ** donne « 11 % » à δ = 3 ; c'est un artefact : Babai y est lui-même
dégradé de 4,4 %. **Le seul chiffre honnête est contre le Babai déployé : 5,4 à 6,5 %.**

### La finitude de l'échantillon, mesurée (addendum 3)

Test causal [mes.] : entraînement = calibration (N moyen 593 positions routées vers l'expert) contre calibration + fenêtres
0-4 d'évaluation (N moyen 827) ; test = fenêtres 5-9 ; mêmes poids synthétiques, δ = 1. Gain de CD contre Babai du même régime :
+5,9 % → +7,3 % (médiane ; hausse sur 7 instances sur 8, +2,6 points). Témoin : test inclus dans l'entraînement : +49,6 %. Erreur du test
rapportée à Babai entraîné sur la calibration seule : Babai avec les données en plus 0,941 ; CD avec les données en plus 0,866
(médiane 0,851) ; CD sans les données en plus 0,946. Lecture : l'optimiseur n'est utile que dans la mesure où H décrit la
distribution d'évaluation ; plus de données et un meilleur optimiseur se renforcent (0,866 < 0,941 × 0,946 = 0,890).
Risque dit : fenêtres 0-4 et 5-9 voisines (fuite thématique possible).

### L'estimateur de Gibbs (négatif)

La mécanique statistique de l'apprentissage (Seung, Sompolinsky et Tishby, Phys. Rev. A 45, 6056, 1992 [mém.]) prévoit
qu'un état tiré à température finie généralise mieux que le fondamental de l'énergie empirique. Testé [mes.] sur L8-E0
(32 rangées, un seul tirage de 30 balayages à une température, sans trempe) : l'erreur d'évaluation à
T/e_b = 0 ; 0,05 ; 0,2 ; 0,4 ; 0,7 ; 1,0 est de −8,1 ; −9,0 ; −8,9 ; −7,9 ; −4,3 ; −0,3 % contre Babai :
un plateau de ±1 point (le bruit d'un échantillon de 32 rangées), puis la dégradation. Pas de gain de généralisation par la chaleur ici.

### Ce que ça rapporterait en bits

À haute résolution D ∝ 2^(−2R) [calc., hypothèse de l'éclaireur, à 2,65 bits elle est approchée] : un rapport d'erreur ρ
vaut ΔR = −½ log2 ρ. Pour ρ = 0,935 (PT) : 0,049 bit par poids ; pour ρ = 0,946 (CD) : 0,040 bit ; soit 1,5 à 1,8 % de
2,65 bits, contre les 0,16 bit visés (ρ = 0,80). Coût : CD ≈ 0,1 à 0,2 s par rangée contre ≈ 6 ms pour Babai
(54 s par expert de 8 640 rangées, 07), soit ×15 à ×30 ; le PT ≈ ×15 de plus que CD (mesuré : 68 à 115 s contre 5 à 7 s pour 64 rangées).

## 5. Figures (toutes tirées des données commitées)

| Figure | Fichier | Ce qu'elle montre | Données |
|---|---|---|---|
| Coupe 2D d'un paysage à 5^10 états | `figures/paysage-toy.pdf` | Babai (cercle) et optimum exact (étoile) dans une coupe où les autres coordonnées sont figées à Babai : un bassin que le glouton n'atteint pas ; énergie de Babai 1 248, optimum 37,9 (instance 464) | `paysage-toy.csv` |
| Où l'erreur est déplacée | `figures/spectre-erreur.pdf` | l'erreur de poids, vue par H_train et par H_eval, groupe de directions propres par groupe (14 groupes) pour frontière, Babai, CD, PT | `spectre-erreur.csv` |
| Gains par instance | `figures/gains-etape1.pdf` | calibration, objectif, évaluation, CD et PT, contre les lignes à 10 % et 3 % | `etape1/gains-d1.csv` |
| Amortissement | `figures/delta.pdf` | erreur d'évaluation contre δ, trois méthodes, rapportée à Babai déployé | `etape1/table-delta.csv` |

Pistes de figures que les données permettent et que je n'ai pas tirées : la matrice de recouvrement d'états entre
répliques (q^{ab} d'Edwards-Anderson) pour dire si le paysage est à une ou plusieurs vallées ; la trace des énergies des
huit répliques au fil des balayages (le noyau ne la renvoie pas encore).

## 6. Ce qui pourrait être faux

- **Poids synthétiques** : gaussiens i.i.d. par rangée. Les vrais poids ont des colonnes géantes corrélées au H
  (05 § 2.1 b) ; l'écart Babai/optimum peut y être plus grand ou plus petit. L'étape 2 sur poids réels existe pour cela
  (non lancée).
- **64 rangées** par instance (256 déclarées) : l'écart-type entre instances est 2,6 points (CD) et 3,4 (PT) ; l'erreur
  standard de la moyenne 0,9 et 1,2 point ; intervalle à 95 % de la moyenne PT ≈ [4 ; 10] %. Il touche à peine 10 %.
- **Le meilleur de deux λ par instance** (à débit égal) gonfle un peu les gains retenus ; les deux λ sont publiés dans `gains-d1.csv`.
- **Le débit** est l'entropie d'ordre zéro des symboles de 64 rangées, pas le débit du codeur réel (contexte κ).
- **Seul le H d'entrée de gate et up** est mesuré ; down (entrée swiglu) demande les vrais poids.
- **La solution de PT n'est pas prouvée optimale** à n = 2 880 : elle l'est à n = 10 (1 000 / 1 000) et n = 16 (10 / 10).
  Un meilleur optimiseur pourrait encore baisser l'objectif ; il ne baisserait l'évaluation que de ce que la
  décomposition spectrale laisse (la part dans le noyau de la calibration), qui est la raison du verdict.
- **Une première version du cache de Cholesky** de `etape1.py` était clé sur `id(H)` : risque de réutiliser le U d'une
  matrice libérée. Corrigé (le cache tient une référence) ; W3 relancé, résultats identiques ; les 8 instances n'avaient
  qu'un H par exécution et n'étaient pas concernées.

## 7. Sources

Lues : Chen, Shabanzadeh, Crnčević, Hoefler, Alistarh, arXiv 2507.18553 (https://arxiv.org/abs/2507.18553, v4 du
2026-05-13, ICLR 2026), consulté le 2026-10-27 ; Aubin, Perkins, Zdeborová, arXiv 1901.00314
(https://arxiv.org/abs/1901.00314, J. Phys. A 52 294003, 2019), résumé consulté le 2026-10-27.
De ma mémoire, à vérifier avant le mémoire : Kirkpatrick, Gelatt, Vecchi, « Optimization by simulated annealing »,
Science 220 (1983) 671 ; Hukushima, Nemoto, « Exchange Monte Carlo method and application to spin glass simulations »,
J. Phys. Soc. Jpn. 65 (1996) 1604 ; Fincke, Pohst, Math. Comp. 44 (1985) 463 ; Babai, Combinatorica 6 (1986) 1 ;
Frantar, Ashkboos, Hoefler, Alistarh, GPTQ, arXiv 2210.17323 ; Seung, Sompolinsky, Tishby, Phys. Rev. A 45 (1992) 6056.
