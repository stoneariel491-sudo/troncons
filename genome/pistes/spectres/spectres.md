# Piste « spectres » : la fractale et les lois de puissance des spectres de gpt-oss-20b

Piste 05 § 3.3 (a), idée de Stone (la fractale). Rôle : scientifique de la piste, en même temps que
la construction des lots A et B (consigne du 2026-10-21 : « n'oublie pas en simultané les recherches
sur les pistes »). Étiquettes : **[mes.]** mesuré, outil et journal commités ; **[calc.]** calculé par
un outil commité ou posé ici pas à pas ; **[litt.]** littérature, non reproduite ; **[hyp.]**
hypothèse dite. Tous les chiffres sont lus dans `mesures/pistes/spectres/rapport.json`, écrit par
`outils/pistes/spectres/rapport.py` depuis les journaux commités. Les seuils sont dans `seuil.md`,
commité avant toute lecture (a171622), amendé avant toute lecture des spectres réels (bfc1c8c).

---

## 0. En bref

<!-- BREF -->

---

## D'où on part, où on va

**Au départ** (05 § 3.3) : aucune mesure de pente. Les données commitées donnaient seulement la
part d'énergie à sept rangs pour l'expert 0 de chaque tenseur (`structure-spectre.json`) : l'excès
sur le hasard était modeste pour gate et up et fort pour down. La littérature (Martin et Mahoney)
donnait une hypothèse, celle des spectres « à queue lourde » des réseaux entraînés, et pas la
réponse pour gpt-oss. Le pronostic de 05 était défavorable pour la forme « compression ».

**Ce que cette étape établit** : voir § 0.

**Ce qui reste** : § 7.

---

## 1. La question, et la grandeur

Trois questions de la consigne : (1) les spectres de gpt-oss suivent-ils une loi de puissance ?
(2) avec quels exposants, par rôle et par couche ? (3) ce spectre ouvre-t-il un levier de
compression mesurable, en bits par poids ?

**La grandeur** (seuil.md § 2) : les valeurs propres λᵢ = σᵢ² de WᵀW (σᵢ les valeurs singulières),
comme Martin et Mahoney. Une queue ρ(λ) ∝ λ^{−α} sur λ a l'exposant 2α − 1 sur σ (dérivation :
`pour-le-memoire.md` § 1) ; les exposants de ce document sont sur λ.

**L'échantillon** (tiré avant de regarder, graine 20261021) : couches 0, 12, 23 ; experts
[0, 6, 22, 24] (couche 0), [1, 3, 19, 31] (couche 12), [7, 21, 26, 27] (couche 23) ; gate, up et down
de chacun (36 matrices 2 880 × 2 880, MXFP4 déquantifiées en f64 exact), plus attn_q, attn_k,
attn_v, attn_output des trois couches (12 matrices Q8_0) : **48 matrices**, soit 124 032 valeurs
singulières (36 × 2 880 + 3 × (2 880 + 512 + 512 + 2 880)), toutes sauvées (`valeurs-singulieres.npz`, 2,0 Mo), avec celles des 48 matrices
permutées et des témoins. Calcul : 617 s, processeur seul, 2 fils, priorité sous la normale [mes.].

---

## 2. L'instrument, et pourquoi le seuil déclaré a dû être amendé

**La méthode** (seuil.md § 3) : Clauset, Shalizi et Newman (arXiv 0706.1062), écrite de zéro
(`outils/pistes/spectres/csn.py`) : λ_min par minimum de la distance de Kolmogorov-Smirnov (queue
d'au moins 50 points), α par maximum de vraisemblance, rapports de vraisemblance de Vuong contre
l'exponentielle et la log-normale tronquées, plausibilité p_gof par 100 répliques. Dérivations
complètes : `pour-le-memoire.md` § 3.

**Le seuil déclaré, et sa limite mesurée avant toute lecture.** La consigne demandait de ne dire
« loi de puissance » que si la méthode la préfère à l'exponentielle **et** à la log-normale avec
p < 0,05. Un essai de l'instrument sur des tirages synthétiques, avant tout ajustement de gpt-oss, a
montré que ce critère **ne peut pas dire oui** à n = 2 880 [mes., `puissance-critere.out`] :

| 20 tirages de n = 2 880 | verdict principal | verdict amendé « compatible » | α̂ médian |
|---|---|---|---|
| Pareto α = 2,5 | 0 / 20 (20 « non départagée ») | **18 / 20** | 2,496 |
| Pareto α = 3,5 | 0 / 20 | **20 / 20** | 3,510 |
| exponentielle | 0 / 20 | **0 / 20** | — |
| log-normale σ = 1 | 0 / 20 | 4 / 20 | — |

La raison est algébrique (`pour-le-memoire.md` § 3, fin) : dans y = ln(λ/λ_min), la log-normale
tronquée est une gaussienne tronquée, la loi de puissance une exponentielle ; quand μ → −∞ et σ → ∞
avec −(μ − ln λ_min)/σ² → α − 1, la première tend vers la seconde. Sur une étendue observée de
quelques unités de y, la courbure y²/(2σ²) qui les sépare est sous le bruit. Le p médian contre la
log-normale sur les Pareto vrais est 0,61 et 0,69.

D'où l'**amendement** (seuil.md § 4 bis, commité bfc1c8c avant la lecture des spectres réels) : le
verdict principal est rapporté tel que déclaré, et on ajoute le verdict « **compatible loi de
puissance** » de CSN (leur « modéré ou mieux ») : p_gof ≥ 0,1, l'exponentielle écartée (R > 0,
p < 0,05) et la log-normale non préférée. Il se lit toujours « loi de puissance, ou log-normale de
très grand σ, indiscernables ici ». Il a passé sa propre épreuve de puissance (tableau).

**Les témoins** [mes., `temoins.out`, `temoins-casse.out`] :

| témoin | attendu | verdict principal | verdict amendé | α̂ |
|---|---|---|---|---|
| T-Pareto (α = 2,5 planté, passé par une vraie matrice 2 880 × 2 880 et sa SVD) | reconnu, α ∈ [2,3 ; 2,7] | ÉCHEC (non départagée), prévu par l'amendement | **TIENT** | 2,492 ± 0,032 |
| T-MP 2 880 × 2 880 | pas loi de puissance | TIENT (exponentielle préférée) | **TIENT** | 16,9 |
| T-MP 4 096 × 2 880, 2 880 × 4 096, 512 × 2 880 | pas loi de puissance | TIENT | **TIENT** | 14,9 ; 15,8 ; 8,8 |
| T-exp | pas loi de puissance | TIENT | **TIENT** | 5,75 |
| T-lognormale (σ = 1) | rapporté | non départagée | non compatible | 3,03 |

**La cassure** (`--casser` échange les entrées de T-Pareto et de T-MP 2 880 × 2 880) : sous le
verdict amendé, **les deux tombent** (T-Pareto non compatible, α̂ = 16,9 ; T-MP compatible, α̂ = 2,49) :
l'instrument sait dire oui et non, et c'est la donnée qui décide. Sous le verdict principal, la
cassure ne fait tomber que T-Pareto : un verdict qui ne dit jamais oui ne peut pas faire échouer un
témoin négatif ; c'est une seconde preuve, par l'instrument lui-même, de son absence de puissance.

Une remarque sur l'échelle de α, qui sert à lire le § 4 : avec cette méthode, le hasard pur
(Marchenko-Pastur) rend α̂ = 9 à 17, parce que la chute d'un spectre à support borné, vue par le
haut, ressemble à une pente très raide. **Un α̂ petit veut dire une queue lourde ; un α̂ de 10 et plus
veut dire « pas de queue ».**

**Le second chemin** [mes., `second-chemin-v2.out`] : déquantification refaite depuis la
spécification (E2M1 décodé bit à bit, échelle E8M0 = 2^(e − 127), lecture par `seek`/`read`), valeurs
propres par `eigvalsh` de la matrice de Gram au lieu de la SVD, balayage de λ_min vectorisé autrement,
α par maximisation numérique, concurrentes par `scipy.stats`, p_gof avec une autre graine :

| contrôle | attendu (seuil.md § 6) | mesuré |
|---|---|---|
| matrices égales | au bit | **48 / 48** empreintes SHA-256 égales |
| valeurs propres de la queue | écart relatif < 10⁻⁸ | ≤ 3,8·10⁻¹⁴ |
| λ_min | égaux | 48 / 48 |
| α | égaux à 10⁻⁶ | écart max 2,2·10⁻⁷ |
| verdicts | égaux | principal 48 / 48 ; compatible 48 / 48 (9 dans les deux) |

~~Second chemin v1 : α̂ de 1,1 à 2,5 au lieu de 1,6 à 6,9.~~ La première version du second chemin
était fausse (commit 0459f36, journal `second-chemin.log` gardé) : sa vraisemblance portait − α Σ ln tᵢ
au lieu de − α Σ ln(tᵢ / λ_min) ; et ses empreintes différaient sur le **signe des zéros** (le décodeur
bit à bit rend −0,0 pour le code 8, la table +0,0 : le codon synonyme du projet, retrouvé ici par
accident). Corrigé, puis vérifié égal au premier chemin sur trois spectres avant la relance. Le
seul écart restant est p contre la log-normale (jusqu'à 0,08), là où R ≈ 0 (la log-normale à sa limite
loi de puissance, p y est instable par nature) ; aucun verdict n'en dépend.

---

## 3. Le verdict : les matrices de gpt-oss ne suivent pas une loi de puissance

[mes., `ajustements.out`, `rapport.json`]

| famille | n | « loi de puissance » (principal) | **compatible** (amendé) | exponentielle écartée | log-normale préférée | p_gof ≥ 0,1 | témoin permuté compatible |
|---|---|---|---|---|---|---|---|
| gate | 12 | 0 | **4** | 4 | 0 | 12 | 0 |
| up | 12 | 0 | **0** | 0 | 3 | 6 | 0 |
| down | 12 | 0 | **3** | 7 | 4 | 5 | 0 |
| attention | 12 | 0 | **2** | 5 | 2 | 9 | 1 |
| **tout** | **48** | **0** | **9** | 16 | 9 | 32 | 1 |

**Verdict, au seuil déclaré** : 0 matrice sur 48 au verdict principal, 9 sur 48 au verdict amendé ; il
en fallait 32. **On ne peut pas écrire que les matrices de gpt-oss-20b suivent une loi de puissance**,
ni sous le critère de la consigne (qui ne peut rien dire), ni sous le critère amendé (qui pouvait dire
oui, et dit non). Aucune famille n'atteint ses 2/3 (8 sur 12) : gate est la plus proche (4 sur 12).

Ce que les 39 non-compatibles sont, au lieu d'une loi de puissance :
- **une queue trop courte pour trancher** dans la majorité des cas : la queue retenue par KS ne
  garde que 50 à 120 valeurs propres pour 18 matrices (quelques directions « pointes » au-dessus d'une
  masse quasi aléatoire) ; l'exponentielle n'y est pas écartée (elle ne l'est que pour 16 matrices
  sur 48) ;
- **une queue plus légère qu'une loi de puissance** pour up : l'exponentielle ou une log-normale de
  petit σ (0,17 à 0,85 pour 10 sur 12) est préférée ou équivalente, 5 « autre loi préférée » sur 12, p_gof < 0,1 pour
  6 sur 12 ;
- **une queue lourde mais courbée** pour down de la couche 0 et attn_output de la couche 0 : α̂ ≈ 1,6
  à 1,7 sur 565 à 973 valeurs propres, mais la log-normale est **préférée** pour les cinq (p ≤ 0,0044 ; σ = 1,8 à 3,0) et la loi
  de puissance n'est même pas plausible pour les quatre down (p_gof = 0) ; c'est l'objet du § 4.2.

---

## 4. Les exposants, par rôle et par couche, et ce qu'ils disent

### 4.1 Le tableau [mes., `rapport.json` → `alpha`]

α̂ sur λ = σ² ; entre crochets, les quatre matrices (experts dans l'ordre du tirage), en gras les
« compatibles » ; « n_q » la taille de la queue retenue ; « 5 % » la part d'énergie des 5 % premières
directions, réel / permuté (médianes).

| | couche 0 | couche 12 | couche 23 |
|---|---|---|---|
| **gate** | 3,75 [4,15 ; 3,35 ; 5,95 ; **2,98**] ; n_q 60–301 ; 5 % : 31 / 17 % | 3,96 [3,67 ; 3,78 ; 4,54 ; 4,13] ; n_q 50–91 ; 39 / 17 % | 3,02 [**3,04** ; 3,00 ; **2,70** ; **3,21**] ; n_q 186–392 ; 35 / 17 % |
| **up** | 5,84 [6,24 ; 5,43 ; 6,94 ; 3,96] ; 81–160 ; 26 / 17 % | 4,33 [3,83 ; 4,83 ; 3,50 ; 8,32] ; 55–219 ; 29 / 17 % | 3,70 [3,75 ; 3,64 ; 3,57 ; 4,12] ; 190–234 ; 26 / 17 % |
| **down** | **1,63** [1,65 ; 1,61 ; 1,71 ; 1,61] ; 565–779 ; **71 / 18 %** | 3,09 [**2,72** ; 3,18 ; **2,99** ; 3,60] ; 124–276 ; 42 / 20 % | 6,44 [6,06 ; 6,83 ; **2,74** ; 7,25] ; 105–388 ; 23 / 17 % |
| **attention** (q, k, v, o) | q 6,20 ; k 4,23 ; v 6,04 ; o 1,72 ; 5 % : 26 / 12 % | q 2,87 ; k 2,95 ; v 5,12 ; o **2,89** ; 34 / 12 % | q **1,90** ; k 1,50 ; v 1,71 ; o 4,05 ; **64 / 15 %** |
| **permuté** (médiane : gate ; up ; down ; attention) | 15,4 ; 17,2 ; 7,9 ; 8,9 | 12,5 ; 17,3 ; 5,4 ; 7,9 | 14,9 ; 13,5 ; 16,3 ; 8,7 |

Les erreurs types (α − 1)/√n_q vont de 0,02 (down, couche 0) à 0,99 (up, couche 12, E31, sur 55 points).

### 4.2 Ce qu'ils disent

1. **Toutes les matrices ont plus de queue que le hasard.** Le α̂ réel est sous celui de la même
   matrice permutée dans les 48 cas ; la médiane des permutées par case est 5,4 à 17,3, celle des
   réelles 1,6 à 6,4. L'entraînement a mis de l'énergie dans quelques directions (la part des 5 %
   premières directions est 1,25 à 5,3 fois celle du hasard), comme 05 § 2.1 (b) le disait avec un seul
   expert par tenseur ; c'est vrai des 4 experts tirés, et des matrices d'attention.
2. **up est la plus proche du hasard** : α̂ 3,5 à 8,3, queue légère, aucune compatible, 26 à 29 %
   d'énergie dans 5 % des directions contre 17 %. gate est intermédiaire et se durcit avec la
   profondeur (3 compatibles sur 4 à la couche 23, α̂ ≈ 3). Lecture [hyp.] : gate et up reçoivent la
   même entrée, mais seule la sortie de gate passe la non-linéarité qui décide quel canal s'ouvre ;
   c'est elle qui aurait à porter des directions privilégiées.
3. **down et attn_output de la couche 0, et q, k, v de la couche 23, ont des queues très lourdes**
   (α̂ = 1,5 à 1,9 : sous 2, la loi ajustée n'a même pas de moyenne finie) ; ce sont aussi les matrices dont les **entrées** ont un kurtosis énorme (down
   couche 0 : 60 à 1 988 ; attn_output couche 0 : 1 700 ; attn_k couche 23 : 896 ; `manifeste.json`).
   Les matrices qui écrivent dans le flux résiduel (down, attn_output) à la couche 0 sont celles qui
   fabriquent ses canaux aberrants (05 § 2.1 (b)).
4. **Cette queue lourde n'est pas une loi de puissance, et sa forme dit d'où elle vient** [hyp.,
   mesure exploratoire au § 4.3] : pour down de la couche 0, la log-normale est préférée (σ ≈ 1,8 à
   2,7) et la loi de puissance rejetée. Une matrice dont quelques rangées ont une norme géante a des
   valeurs singulières proches de ces normes ; son spectre de queue recopie alors la loi des normes de
   rangée, qui n'a aucune raison d'être invariante d'échelle. La queue serait la signature des
   **canaux géants**, pas d'une auto-similarité.
5. **La couche 12 de down est le seul endroit où la loi de puissance et la log-normale se confondent
   vraiment** : les 4 ajustements log-normaux partent à μ ≈ −120 à −190, σ ≈ 7 à 9,6, c'est-à-dire à la
   limite loi de puissance de la log-normale (§ 2) ; α̂ = 2,7 à 3,6 ; 2 compatibles sur 4.

**Rapport à Martin et Mahoney** [litt.] : leur résumé (arXiv 1810.01075, v1 du 2018-10-02, lu le
2026-10-21) décrit, pour les réseaux de l'état de l'art, une auto-régularisation à queue lourde faite
de corrélations à toutes les échelles, et 5 + 1 phases d'entraînement ; leur article de 2021
(arXiv 2002.06716, v2, Nature Communications) montre que des métriques tirées de ces lois de
puissance jugent mieux la qualité d'un modèle que les normes. Ce qui est mesuré ici pour gpt-oss-20b
s'accorde avec la **première moitié** (des queues plus lourdes que le hasard dans 48 matrices sur 48,
un excès qui varie fortement par rôle et par couche) et **ne confirme pas la seconde** au sens
strict : au test de CSN, la queue n'est une loi de puissance plausible que dans 9 matrices sur 48, et
la plus lourde de toutes (down, couche 0) est une log-normale. Les seuils numériques d'α de leur corps
d'article ne sont pas cités ici : seul leur résumé a été lu à la source.

### 4.3 D'où vient la queue (mesure exploratoire)

**Non déclarée avant** (`normalise.py`, `normalise.out`, `normalise.log`) ; elle soutient une
hypothèse, elle ne la prouve pas. Sur les 24 matrices gate, down et attn_output, on divise chaque rangée
par sa norme (W_r), puis, à part, chaque colonne (W_c), et on refait SVD et ajustement CSN (50 répliques).

| matrices | α̂ brute | α̂ rangées normalisées | α̂ colonnes normalisées | part des 5 % premières : brute → rangées | CV des normes de rangée / de colonne |
|---|---|---|---|---|---|
| down, couche 0 (4) | 1,61 – 1,71 | **3,35 – 6,98** | 1,61 – 1,69 | 0,68 – 0,79 → **0,23 – 0,29** | **1,26 – 1,54** / 0,13 – 0,31 |
| attn_output, couche 0 | 1,72 | **3,96** | 1,76 | 0,72 → 0,23 | 1,21 / 0,49 |
| down, couche 12 (4) | 2,72 – 3,60 | 3,21 – 4,25 | 2,82 – 4,26 | 0,36 – 0,45 → 0,30 – 0,36 | 0,35 – 0,48 / 0,24 – 0,41 |
| gate (12) | 2,70 – 5,95 | 3,08 – 6,28 | 3,05 – 6,61 | 0,27 – 0,51 → 0,27 – 0,32 | 0,11 – 0,81 / 0,07 – 0,50 |
| down, couche 23 (4) | 2,74 – 7,25 | 2,79 – 9,17 | 3,63 – 9,78 | 0,22 – 0,38 → 0,20 – 0,35 | 0,19 – 0,22 / 0,08 – 0,32 |

(Le hasard, permuté : 0,17 à 0,18 de l'énergie dans 5 % des directions.)

**Lecture.** Pour down et attn_output de la couche 0, la queue lourde **disparaît quand on égalise les
rangées** et reste intacte quand on égalise les colonnes : les normes de rangée y varient d'un facteur
de dispersion 1,2 à 1,5 (contre 0,1 à 0,8 ailleurs), et la plus grande valeur singulière n'est que 1,1 à
1,4 fois la plus grande norme de rangée (une direction ≈ une rangée). Ces rangées sont les canaux de
sortie qui écrivent dans le flux résiduel : les **canaux géants** de 05 § 2.1 (b). La queue de ces
spectres est la loi des normes de ces rangées, recopiée ; elle n'a pas de raison d'être invariante
d'échelle, et le test de CSN l'avait déjà dit (log-normale préférée, § 3). Ailleurs, la normalisation
déplace peu α̂ : l'excès sur le hasard y est faible et réparti.

C'est aussi ce qui explique le § 5 : la structure qui faisait les plus grands « plafonds » est celle que
prend une échelle par rangée, et MXFP4 a une échelle par bloc de 32 poids.

---

## 5. Le levier de compression

La question de la consigne : ce spectre ouvre-t-il un levier de compression mesurable ? On y répond en
trois étages, du plus généreux au plus honnête. (1) Le **plafond** : ce que vaudrait le spectre si la
base propre était offerte au décodeur. (2) Le **plafond par rang** : ce qu'il en reste quand on paie les
r premières directions. (3) Le **levier mesuré** sur les matrices elles-mêmes (L1 sans perte sur les
codes MXFP4, L2 et L3d avec perte). Rien de ce paragraphe n'est un gain acquis : ce sont des gains
**dans le domaine des poids**, et 05 § 2.1 (c) a montré que l'erreur de poids ne prédit pas la KL.

### 5.1 Le plafond : 0,42 bit par poids de structure au-delà du hasard, base offerte [calc., mes.]

Seuils : `seuil.md` § 7 quinquies et § 7 sexies (déclarés avant calcul) ; outil `plafond.py` ; journaux
`plafond.log`, `plafond-casse.log`, `plafond-v1.log` ; dérivations `pour-le-memoire.md` § 7.

**La grandeur.** On lit W comme max(m, n) vecteurs gaussiens de dimension p = min(m, n), de valeurs
propres λⱼ = σⱼ²/max(m, n). À l'erreur relative D = 0,044, le remplissage inverse dans la base propre
donne un débit R_KLT ; le spectre plat de même énergie coûte ½ log₂(1/D) = 2,2535 bits. Le plafond
G = ½ log₂(1/D) − R_KLT majore le gain de **toute** méthode qui code dans une base propre, sous ce
modèle (base blanche ≥ variances par rangée ≥ Karhunen-Loève). À haut débit, G = ½ log₂(λ̄/λ_g),
le rapport des moyennes arithmétique et géométrique du spectre : une mesure de platitude, où les
petites valeurs pèsent autant que les grandes. L'**excès** E = G(réel) − G(même matrice permutée).

**Les témoins.**

| témoin | attendu | mesuré | |
|---|---|---|---|
| second chemin (θ en forme close au lieu de la dichotomie) | écart ≤ 10⁻⁹ | 9,3·10⁻¹⁴ | tient |
| T-MP 2 880 × 2 880 contre l'intégrale de Marchenko-Pastur (c = 1) | écart ≤ 0,005 | 0,5898 contre 0,5899 | tient |
| T-MP 4 096 × 2 880 et 2 880 × 4 096 (c = 0,703) | ≤ 0,005 | 0,3514 et 0,3511 contre 0,3511 | tient |
| T-MP 512 × 2 880 (c = 0,178) | ≤ 0,005 | 0,0685 contre 0,0683 | tient |
| T-plante-rang8 contre son permuté | E ≥ 0,05 (prédit ≈ 0,24 à haut débit) | **E = +0,216** | tient |
| cassure (planté ↔ permuté ; T-MP 2 880 ↔ 4 096) | les trois tombent | E = −0,216 ; écarts ∓ 0,239 | tombent |
| ~~T-Pareto : G(Pareto) − G(MP) ≥ 0,05~~ | attente mal posée (§ 7 sexies) | −0,292 | barré |

~~T-Pareto, témoin positif du plafond~~ : il est tombé au premier passage, et c'est l'attente qui était
fausse, pas l'outil. La loi MP de rapport 1 a une densité en λ^{−1/2} près de zéro : une foule de petites
valeurs, très loin de la platitude (G_MP(1) = ½ log₂ e = 0,721 bit à haut débit, 0,590 à D = 0,044). Le
Pareto planté (λ ≥ 1) est borné par en bas ; sa forme close G = ½ log₂((α − 1)/(α − 2)) − 1/(2 (α − 1) ln 2)
vaut 0,312 à α = 2,5 (mesuré 0,298). **Une queue lourde en haut ne fait pas, à elle seule, un grand
plafond** : c'est pourquoi l'excès se lit contre le permuté de la même matrice, jamais contre un spectre
de référence. Le témoin a été remplacé avant toute lecture de gpt-oss (le premier passage s'arrête avant,
`plafond.out` n'a pas été ouvert).

**Le plafond, par famille** (D = 0,044 ; médianes sur 12 matrices) :

| famille | G réel | G permuté | **excès E** (min – max) | lecture (§ 7 quinquies) |
|---|---|---|---|---|
| gate | 0,846 | ≈ 0,590 | **0,254** (0,177 – 0,690) | ouvert |
| up | 0,742 | ≈ 0,590 | **0,152** (0,114 – 0,392) | ouvert |
| down | 0,990 | ≈ 0,60 | **0,356** (0,111 – 1,108) | ouvert |
| attention | 0,920 | 0,07 à 0,40 selon la forme | **0,631** (0,097 – 1,668) | ouvert |
| **échantillon** (pondéré par les poids) | **0,965** | | **0,424** | |

Les permutés tombent sur la loi MP de leur forme à 0,08 près au plus (L23.attn_k +0,076, L12.down.E03
+0,073, là où le kurtosis des entrées est le plus grand) : la loi des entrées seule ne fait presque rien
au plafond. **Les plus grands excès sont down de la couche 0 (0,95 à 1,11), attn_output de la couche 0
(1,03) et q, k, v de la couche 23 (1,14 ; 1,67 ; 1,02)** : exactement les matrices de queue très lourde
du § 4 (α̂ < 2). up a le plus petit (0,11 à 0,39).

Ce que cela veut dire : l'entraînement a mis dans ces spectres, au-delà du hasard, de quoi économiser
0,42 bit par poids sur l'échantillon, **si la base propre ne coûtait rien**. Le plafond est ouvert pour
les quatre familles. C'est une condition nécessaire, pas un levier.

### 5.2 Où vit le plafond, et ce qu'il en reste une fois la base payée [calc., mes.]

Seuil : `seuil.md` § 7 septies (avant calcul) ; outil `plafond_rang.py` ; journaux `plafond-rang.log`,
`plafond-rang-casse.log`. G_r : le plafond quand seules les r premières directions sont offertes (le reste
codé comme un bruit blanc de sa variance moyenne) ; N_r(b) = G_r − b · r (m + n)/(m n), facteurs à b bits
par coefficient (0,0111 · r bit par poids à b = 16 pour 2 880 × 2 880).

**Témoins** : T-plante-rang8, max_r N_r(16) = **+0,156 atteint à r = 8**, le rang planté (attendu > 0,05
à r = 8) ; son permuté −0,011 (attendu < 0,0125) ; la cassure (les deux échangés) les fait tomber tous les
deux (−0,011 à r = 1 ; +0,156).

**Où il vit** : part médiane du plafond prise par les r premières directions,
(G_r(réel) − G_r(permuté)) / E :

| famille | r = 8 | r = 64 | r = 512 |
|---|---|---|---|
| gate | 0,09 | 0,30 | 0,85 |
| up | 0,06 | 0,24 | 0,77 |
| down | 0,12 | 0,36 | 0,86 |
| attention | 0,11 | 0,33 | 0,67 |

**Les deux tiers du plafond vivent au-delà de la 64e direction.** La structure que l'entraînement a mise
dans ces matrices n'est pas « un rang faible plus du bruit » : elle est étalée sur des centaines de
directions, dans la forme de la masse du spectre. Une base complète la prendrait, mais r = p coûte
b (m + n)/max(m, n) ≥ b bits par poids : 16 bits pour un plafond de 1 bit au plus. Elle ne se paie jamais.

**Le levier payé, par famille** (médiane de max_r N_r(b) ; règle du § 7 : > 0,05 et témoin permuté
sous le quart) :

| famille | b = 16 (la règle) | permuté | verdict | b = 8 (sensibilité) | b = 4 (sensibilité) |
|---|---|---|---|---|---|
| gate | −0,003 | −0,011 | pas de levier | +0,003 | +0,010 |
| up | −0,009 | −0,011 | pas de levier | −0,004 | −0,001 |
| down | **+0,042** | −0,010 | **pas de levier** (sous 0,05) | +0,066 | +0,106 |
| attention | −0,005 | −0,021 | pas de levier | +0,004 | +0,028 |
| **échantillon**, moyenne pondérée de max(0, max_r N_r) | **0,022** | | | 0,038 | 0,080 |

À b = 16, **aucune famille n'a de levier** au seuil déclaré ; down en est la plus proche (0,042 pour
0,05). Les colonnes b = 8 et b = 4 sont optimistes (l'erreur des facteurs arrondis n'y est pas comptée)
et n'emportent aucun verdict : elles disent seulement que **down passerait le seuil si ses facteurs se
codaient à 8 bits sans dommage**, ce qui reste à mesurer.

~~**Le levier existe matrice par matrice**, là où l'excès est fort. À b = 16, 8 matrices sur 48 passent
0,05 bit : L00.down.E24 (+0,130, r = 4), L00.down.E00 (+0,064), L00.down.E06 (+0,055),
L00.attn_output (+0,165, r = 8), L12.down.E03 (+0,085), L12.down.E19 (+0,059), L23.attn_q (+0,127,
r = 16), L23.attn_k (+0,108, r = 8).~~ **Barré le 2026-10-22 à 12 h** (`seuil.md` § 7 nonies) : ces
nombres se mesurent contre la base blanche, qui compte comme spectrale la structure des canaux géants.
Une simple variance par rangée la prend déjà : L2_0 = 0,755 bit pour L00.down.E24 au lieu de 2,254.
Contre cette base, le levier mesuré (§ 5.4) de ces 8 matrices vaut −0,022 à −0,006, sauf L23.attn_q
(+0,109 en L2, +0,022 en L3d). Le second chemin déclaré au § 7 septies (« même signe du levier par
famille que L2 ») **tombe pour down** : +0,042 ici, médiane de L2 −0,009. Ce sont des plafonds contre la
base blanche, pas des leviers ; le tableau ci-dessus se lit ainsi.

### 5.3 L'exposant comme sélecteur : ce que la queue dit du levier

**Mesure exploratoire, non déclarée avant** (`alpha_levier.py`, `alpha-levier.out`,
`fig-alpha-levier.csv`) : sur les 48 matrices, le rang de Spearman entre α̂ (§ 4) et max_r N_r(16) vaut
**−0,64** (p = 1,1·10⁻⁶) ; entre α̂ et l'excès E, −0,62. Sous α̂ < 2, **6 matrices sur 8** ont un levier
payé au-delà de 0,05 bit (médiane +0,086) ; à α̂ ≥ 2, **2 sur 40** (médiane −0,006).

~~C'est la seule façon dont l'idée de la fractale rejoint la compression, ici : l'exposant de queue ne dit
pas que la matrice est auto-similaire (§ 3, elle ne l'est pas), mais il **désigne à bas prix les matrices
où une part de rang faible se paie**.~~ Barré (§ 7 nonies) : N_r(16) se mesure contre la base blanche ;
ce que α̂ désigne, c'est un spectre dont l'énergie se concentre dans ses premières directions, et cette
énergie est surtout celle de quelques rangées géantes (§ 4.2, point 4), qu'une échelle par rangée prend
déjà. Ces nombres ont été vus avant d'être une règle ; la règle se prouve sur des matrices neuves, et
elle a été renommée avant lecture : « α̂ < 2 prédit N_r(16) contre la base blanche > 0,05 », sans levier. Elle est déclarée (`seuil.md` § 7 octies : α̂ < 2 ⇒ levier, α̂ ≥ 2 ⇒ pas de
levier ; réussite si au moins 2/3 des α̂ < 2 ont un levier et au plus 10 % des autres ; échantillon neuf,
graine 20261022, couches 3, 9 et 21, 36 matrices).

**Le test, sur 36 matrices neuves** (`prediction.py`, `prediction.out`, `prediction.log`,
`prediction-casse.log`) [mes.] :

| contrôle | attendu | mesuré | |
|---|---|---|---|
| témoin de l'outil (48 anciennes, depuis le npz) | α̂ et N égaux à 10⁻⁶ ; 6 sur 8 et 2 sur 40 | écarts 0 et 5·10⁻⁷ ; 6 sur 8, 2 sur 40 | tient |
| cassure (α̂ mélangés entre matrices) | la règle tombe | 1 sur 8 ; 7 sur 40 ; Spearman −0,14 | tombe |
| **36 neuves**, α̂ < 2 | au moins 2/3 avec N_r(16) > 0,05 | **4 sur 6** | tient |
| **36 neuves**, α̂ ≥ 2 | au plus 10 % | **5 sur 30 (17 %)** | **tombe** |
| Spearman (sans seuil) | | −0,36 (p = 0,03) | |

**La règle tombe** à son critère déclaré. Les cinq exceptions sont des down des couches 3 et 9 (α̂ 2,6 à
3,2, N_r de +0,055 à +0,121) et un gate de la couche 21 (α̂ 2,28, +0,089) : l'énergie peut se
concentrer dans les premières directions sans que la queue soit très lourde au sens de CSN. Et, comme
le dit le § 7 nonies, ce N_r se mesure contre la base blanche : même tenue, la règle n'aurait désigné
aucun levier. L'idée de la fractale ne donne donc ici ni une loi (§ 3), ni un sélecteur fiable.

### 5.4 Le levier mesuré sur les matrices (L1, L2, L3d) : aucun [mes.]

Seuils `seuil.md` § 7, 7 bis, 7 ter, 7 quater ; outil `levier.py` (v3, une passe) ; journaux
`levier-v3.out`, `levier-v3.log`, `levier-temoin-v3.out` ; chiffres `rapport.json` → `levier`.
Les passes v1 (`levier.out`, faux sur L2, début tronqué) et v2 (`levier-v2.out`, colonne L3 sans
tramage faussée par la grille MXFP4, endormi avant la fin) restent comme traces, barrées.

**Les témoins** (planté de rang 8, 30 % de l'énergie, quantifié MXFP4) :

| témoin | attendu (§ 7 bis, 7 ter) | mesuré |
|---|---|---|
| T-plante-rang8, L1 | > 0,05 | **+0,157** |
| T-plante-rang8, L2 | > 0,05 (0,168 prédit) | **+0,161** |
| T-plante-rang8, L3d | > 0,05 | **+0,138** |
| T-plante-rang8, blocs permutés, L1 | < 0,0125 | −0,011 |
| T-plante-rang8, entrées permutées, L2 et L3d | < 0,0125 | −0,010 et −0,011 |
| erreur relative de L3d / cible D | à 1 % | 1,0001 |

**Le levier, par famille** (médiane sur les matrices du meilleur gain net sur r ∈ {1, …, 64} ; facteurs
en f16 ; entre parenthèses le maximum ; témoin = blocs permutés pour L1, entrées permutées sinon) :

| famille | L1, sans perte (codes MXFP4) | L2, borne gaussienne par rangée | L3d, quantificateur tramé | témoin (L2) | levier ? |
|---|---|---|---|---|---|
| gate | −0,0002 (+0,0091) | −0,0054 (+0,0053) | −0,0105 (−0,0016) | −0,0101 | non |
| up | −0,0072 (−0,0020) | −0,0084 (−0,0058) | −0,0115 (−0,0086) | −0,0101 | non |
| down | −0,0086 (+0,0029) | −0,0085 (−0,0026) | −0,0113 (−0,0080) | −0,0102 | non |
| attention | — (Q8_0) | −0,0143 (**+0,1085**) | −0,0142 (+0,0219) | −0,0188 | non |
| **échantillon**, moyenne pondérée de max(0, meilleur) | **0,0009** (36 matrices MXFP4) | **0,0036** | **0,0007** | | |

**Lecture.** Le meilleur rang est r = 1 en médiane partout : chaque direction de plus coûte 0,011 bit par
poids et rapporte moins. Aucune famille n'approche le seuil de 0,05 bit, sans perte comme avec perte.
**Sans perte**, sur les codes MXFP4, l'information que la part de rang faible apporte sur le code de 4
bits au-delà de l'échelle de bloc ne paie jamais ses facteurs : 6 matrices sur 36 ont un gain positif,
toutes sous 0,01 bit (les gate de la couche 23, +0,005 à +0,009). **Avec perte**, une seule matrice sur
48 passe le seuil sous la borne gaussienne, L23.attn_q (+0,109 à r = 16), et le quantificateur réel
(L3d, second chemin déclaré de L2) ne lui rend que +0,022 à r = 4 : la borne gaussienne surestime le gain
d'une matrice dont les entrées ne sont pas gaussiennes, et le second chemin ne confirme pas.

**Où est passée la structure du plafond.** Le débit par rangée L2_0 est déjà sous la base blanche
(2,254 bits) : médianes 2,154 (gate), 2,227 (up), 2,043 (down), 2,009 (attention), et 0,755 pour
L00.down.E24. Une échelle par rangée prend donc, à elle seule, l'essentiel de ce que le spectre
« excédait » (§ 5.1) ; MXFP4 a mieux encore, une échelle par bloc de 32 poids, et L1 mesure au-delà de
celle-ci. Ce qui reste au-delà des échelles de rangée est mesuré au § 5.5.

<!-- RANGEE -->

---

## 6. Ce qui pourrait être faux

1. **L'échantillon** : 48 matrices sur les 24 couches × (3 × 32 + 4) = 2 400 du modèle (2 %), 3 couches
   sur 24, 4 experts sur 32. Le verdict « pas de loi de puissance » tient pour cet échantillon tiré au
   hasard ; une couche non tirée pourrait différer. La pente avec la profondeur (gate se durcit, down
   s'adoucit de la couche 0 à la couche 23) est lue sur 3 points.
2. **La grandeur** : on ajuste λ = σ² de W (MXFP4 ou Q8_0 déquantifiées), pas les poids d'origine
   avant quantification (BF16 d'OpenAI, non téléchargés). La quantification ajoute un bruit à peu près
   blanc, qui relève le bas du spectre et peut raccourcir la queue apparente ; elle ne crée pas de
   directions dominantes. L'effet sur α n'est pas mesuré.
3. **La garde de 50 points** sur la queue est un choix déclaré, pas une dérivation : elle a été posée
   pour que le minimum de KS ne se joue pas sur une poignée de points. 5 matrices ont leur λ_min à la
   garde ou tout près (n_q = 50 à 55 : L00.attn_q, L00.attn_v, L12.gate.E01, L12.gate.E19, L12.up.E31) ; pour elles, la vraie queue de KS serait peut-être plus courte
   encore, et rien n'y serait décidable.
4. **Le verdict amendé** est posé après avoir vu que le verdict déclaré n'avait aucune puissance, mais
   avant toute lecture des spectres réels (bfc1c8c, horodaté avant `ajustements.out`) ; il a sa propre
   épreuve de puissance. Il reste un choix : CSN eux-mêmes laissent le jugement « modéré » à
   l'appréciation. Avec un critère plus lâche, sans p_gof (l'exponentielle écartée et la log-normale
   non préférée), le décompte serait 10 sur 48 ; et même le plus lâche possible (l'exponentielle
   écartée, rien d'autre) ne donnerait que 16 sur 48 : le verdict ne dépend pas de ce choix.
5. **La lecture « la queue vient des canaux géants »** (§ 4.2, point 4) est une hypothèse ; la
   mesure exploratoire du § 4.3, non déclarée avant, la soutient ou la contredit, et ne vaut pas preuve.
6. **p_gof à 100 répliques** a une précision de ± 0,03 près de 0,1 : 3 matrices ont p_gof entre 0,05
   et 0,15 (L00.attn_output 0,10 ; L23.attn_k 0,05 ; L23.down.E27 0,08) ; aucune des trois ne passerait
   à « compatible » pour autant, car l'exponentielle n'y est pas écartée ou la log-normale y est préférée.
7. **Le second chemin partage** l'échantillon, la garde de 50 points et la définition des verdicts ; il
   refait les calculs, pas les choix.
8. **Le levier** se mesure dans le domaine des poids ; 05 § 2.1 (c) a montré que l'erreur de poids ne
   prédit pas la KL. Un levier dans les poids serait une condition nécessaire, jamais suffisante.
9. **Martin et Mahoney** ne sont cités que par leurs résumés ; leurs seuils d'α et leur méthode
   d'ajustement exacte (ils ajustent souvent la densité de X = WᵀW/N avec la bibliothèque `powerlaw`)
   n'ont pas été relus ; une différence de méthode peut déplacer α d'une fraction d'unité.

10. **Le plafond est un modèle gaussien** : les rangées de W y sont des tirages d'une gaussienne de
   covariance WᵀW/q. Une matrice n'est pas un tirage ; le plafond dit ce que vaudrait le spectre pour un
   codeur qui ne connaîtrait de W que ses variances dans la base propre. Un codeur qui exploite plus
   (la loi non gaussienne des entrées, la grille MXFP4) n'est pas borné par lui. Le levier mesuré (§ 5.4)
   est là pour ça.
11. **Le plafond par rang code le reste comme un bruit blanc** : c'est la lecture la plus simple d'un
   reste « sans base » ; un reste codé par rangée (L2) peut faire un peu mieux. La part des r premières
   directions peut donc être légèrement sous-estimée, et dépasser 1 quand le permuté est mal servi par
   ce modèle (down de la couche 0 à r = 512 : 1,09 à 1,22).
12. **Les sensibilités à 8 et 4 bits par coefficient ne comptent pas l'erreur des facteurs arrondis** :
   elles sont optimistes, et aucun verdict n'en sort. Un facteur à 4 bits ajoute au résidu une erreur
   qu'il faudrait mesurer comme L2 le fait à 16 bits.
13. **La règle de l'exposant** (§ 5.3) a été vue avant d'être déclarée ; seul le test sur les couches 3,
   9 et 21 la juge. Elle porte sur α̂ de CSN avec la garde de 50 points ; un autre estimateur de queue
   déplacerait la frontière α̂ = 2.
14. **Le premier témoin positif du plafond (T-Pareto) est tombé** et a été remplacé avant toute lecture
   de gpt-oss : c'est une attente corrigée après coup, dite au § 5.1 et dans `seuil.md` § 7 sexies ; le
   témoin qui le remplace (le planté) a une réponse calculée d'avance (≈ 0,24) et rend 0,216.
---

## 7. Ce qui reste

- **Le levier** : voir § 5 pour ce qui est mesuré. Ce qui n'est pas mesuré : la KL d'une part de rang
  faible sur le texte (la seule mesure qui jugerait, 05 § 1) ; elle n'a de sens que si un levier
  apparaît dans les poids.
- **Les poids d'origine** (BF16) : refaire les spectres avant quantification dirait ce que MXFP4 fait à
  la queue ; demande un téléchargement (décision de Stone par l'orchestrateur).
- **Les 21 couches non tirées**, et le 120b : même outil, même seuil ; quelques heures de processeur.
- **Les facteurs à 8 et 4 bits** : refaire L2 et L3d avec des facteurs quantifiés pour de vrai ; c'est
  la seule voie qui ferait passer down au seuil de famille (sensibilité du § 5.2 : 0,066 et 0,106).
- **Un levier sélectif** : une part de rang faible pour les seules matrices désignées par α̂ < 2 (si la
  règle du § 5.3 tient sur l'échantillon neuf), à juger en KL sur le texte, et à placer contre le coût
  du format (une matrice sur six, dans l'échantillon, porte un levier).
- **La forme (b) et (c) de la fractale** (05 § 3.3) restent closes par leurs chiffres : rien dans ces
  spectres ne les rouvre (aucune invariance d'échelle mesurée ici).

---

## 8. Recettes (pour RECETTES.md)

- **Le test de CSN contre la log-normale n'a aucune puissance à n ≈ 3 000** : 0 sur 40 lois de puissance
  vraies reconnues. Essayer l'instrument sur des tirages synthétiques **avant** de déclarer un seuil qui
  en dépend, et chiffrer sa puissance (`puissance_critere.py`). Raison : la log-normale tronquée
  contient la loi de puissance comme limite.
- **Un verdict qui ne dit jamais oui ne peut pas faire tomber un témoin négatif** : la cassure doit
  porter sur un témoin positif et un négatif à la fois ; c'est ce qui a montré la chose ici.
- **Pour α, le hasard pur donne α̂ = 9 à 17** avec CSN (la chute d'un support borné vue par le haut) :
  lire α par rapport au même calcul sur la matrice permutée, jamais seul.
- **Comparer des matrices par empreinte exige de normaliser −0,0 en +0,0** (`w + 0.0`) : deux
  décodeurs justes de MXFP4 diffèrent sur le signe des zéros.
- **Un quantificateur uniforme sans tramage sur une matrice déjà quantifiée mesure la grille, pas la
  source** : le témoin permuté rend le même gain ; utiliser un tramage soustractif (Δ en forme close).
- **Une redirection `>` tronque son fichier même quand la commande échoue** ; une chaîne qui relance une
  étape vers le même fichier qu'un processus encore vivant le corrompt (trou de zéros) : un nom de
  sortie par version (`-v2`, `-v3`).
- **`TaskStop` n'arrête pas les processus enfants d'une chaîne bash**, et l'arrêt par PID peut être
  refusé : écrire chaque calcul long pour qu'il s'arrête de lui-même (fichier drapeau lu entre deux
  matrices), en plus de la pause sur le verrou.
- **Une garde par mot-clé sur un verrou partagé se trompe sur « pas une séance de vitesse »** : lire un
  champ, pas un mot.
- **Un plafond de codage se lit contre le permuté de la même matrice, jamais contre un spectre de
  référence** : la loi MP de rapport 1 est très loin de la platitude par le bas (½ log₂ e = 0,72 bit à
  haut débit), plus qu'un Pareto de queue lourde ; le témoin « Pareto au-dessus de MP » est tombé pour
  cette raison.
- **Avant de payer une base, demander où vit le plafond** : la part prise par les r premières
  directions (§ 5.2) dit tout de suite si un rang faible peut suffire ; ici, deux tiers au-delà de la
  64e direction.
- **Écrire un tirage dans un seuil après avoir lu la sortie de la commande, jamais avant** : le § 7 octies
  a porté un tirage inventé pendant une minute (barré).
