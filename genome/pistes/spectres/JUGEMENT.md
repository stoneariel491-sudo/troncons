# Jugement indépendant de la piste « spectres et fractale »

Juge : rôle séparé, n'a rien fait du travail de la piste. Écrit le 2026-10-27.
Seuils du juge : `juge-seuil.md`, commité **avant** l'écriture de son outil (a52beeb).
Outils : `outils/pistes/spectres/juge/juge_csn.py` (écrit de zéro, sans lire `csn.py`,
`ajuster.py` ni `second_chemin.py`) et `comparer.py`. Journaux et CSV :
`mesures/pistes/spectres/juge/`.

## 0. Verdict du juge

**Le chiffre principal tient.** Par un chemin propre, sur les mêmes spectres :

- verdict principal (consigne) : **0 / 48**, comme publié ;
- verdict amendé « compatible » : **9 / 48**, comme publié, **les mêmes 9 matrices** (accord 48 / 48),
  mêmes décomptes par famille (gate 4, up 0, down 3, attention 2), même témoin permuté (1 / 48) ;
- λ_min égaux sur 48 / 48 et α̂ égaux (écart relatif nul) sur les 48 matrices et les 48 permutées ;
- « α̂ réel < α̂ permuté » : **48 / 48** (rapport permuté / réel de 1,26 à 8,81, médiane 3,49).

« Les matrices de gpt-oss-20b suivent une loi de puissance » **ne s'écrit pas** : 9 sur 48 au mieux, il
en fallait 32. Les témoins du juge tiennent, sa cassure fait tomber les deux témoins qu'elle vise.

**Deux choses à corriger dans le texte de la piste** (elles ne changent pas le verdict, § 4) : le
critère principal n'est pas seulement « sans puissance à n = 2 880 », il est **impossible à satisfaire
à toute taille** (théorème du § 2) ; et l'affirmation « la couche 12 de down est le seul endroit où la
loi de puissance et la log-normale se confondent » est fausse (11 matrices sur 48). Plus deux
formulations du rendu à reprendre (§ 4).

Tous les seuils J1 à J4 de `juge-seuil.md` : **TIENNENT** (`comparaison-juge-csn.txt`).

## 1. L'ordre des commits : le seuil précède-t-il la lecture ?

Vérifié par `git log --date=iso` sur `seuil.md`, `valeurs-singulieres.npz`, `ajustements.out` :

| heure (2026-10-21/22) | commit | quoi |
|---|---|---|
| 21 oct. 23:22:25 | a171622 | seuil déclaré (échantillon, CSN, 2/3, témoins, second chemin, levier) |
| 21 oct. 23:25:57 | bfc1c8c | amendement § 4 bis (critère « compatible ») |
| 21 oct. 23:34:06 | 5232e5f | valeurs singulières des 48 matrices (npz) |
| 22 oct. 01:29:58 | fdf5929 | puissance des critères : 18/20 et 20/20 Pareto, 0/20 exponentielles |
| 22 oct. 02:04:28 | eec367c | ajustements des 48 matrices réelles |

**Tient** : le seuil et son amendement sont commités avant que les spectres n'existent dans le
dépôt (npz 8 minutes après l'amendement), et l'épreuve de puissance exigée par l'amendement (au moins
18/20 Pareto pour chaque α, au plus 2/20 exponentielles) est commitée avant les ajustements réels.
Le tirage de l'échantillon, refait par le juge (`default_rng(20261021)`, `choice(32, 4)` trois fois),
redonne exactement couches 0 : [0, 6, 22, 24], 12 : [1, 3, 19, 31], 23 : [7, 21, 26, 27].

Deux réserves de forme, sans effet sur le verdict :
- l'amendement de 23:25 cite « p médian 0,59 et 0,63 » contre la log-normale sur les Pareto vrais ;
  le seul journal commité de cette épreuve (`puissance-critere.out`, 01:29) donne **0,61 et 0,69**.
  Les nombres de l'amendement viennent d'un essai antérieur qui n'a pas laissé de journal ;
  `spectres.md` cite bien 0,61 et 0,69 ;
- le critère amendé passe son épreuve de puissance **au bord** (18/20 exactement à α = 2,5).

## 2. Le critère principal ne peut jamais dire oui : un théorème, pas un manque de puissance

Posé dans `juge-seuil.md` avant calcul (J1), puis vérifié.

Sur la queue λ ≥ λ_min, posons y = ln(λ / λ_min) ≥ 0. La log-normale tronquée de paramètres (μ, σ)
a pour densité en y

  g(y) ∝ exp(−(y + ln λ_min − μ)² / (2σ²)) ∝ exp(−c₁ y² + b y),  c₁ = 1/(2σ²) > 0,  b = (μ − ln λ_min)/σ²,

une gaussienne tronquée en y. La loi de puissance ρ(λ) ∝ λ^(−α) a pour densité en y
(α − 1) e^(−(α−1) y) : c'est **le même modèle au bord c₁ = 0**, b = −(α − 1). La log-vraisemblance
ℓ(c₁, b) = Σ(−c₁ yᵢ² + b yᵢ) − n ln Z(c₁, b), Z = ∫₀^∞ exp(−c₁y² + by) dy = ½ √(π/c₁) erfcx(−b/(2√c₁)),
est continue jusqu'au bord (Z → 1/|b| quand c₁ → 0⁺, b < 0) et concave (famille exponentielle de
statistiques −y², y). Donc sup ℓ_log-normale ≥ ℓ_loi-de-puissance(α̂), et

  **R = ℓ_PL − ℓ̂_LN ≤ 0 pour toute matrice, à toute taille n** (le jacobien 1/λ est commun et s'annule).

« R > 0 et p < 0,05 contre la log-normale » est donc impossible quand la log-normale est ajustée à son
vrai maximum : le verdict principal de la consigne est vide **par construction**. La piste l'avait
mesuré (0 / 40 Pareto) et l'avait expliqué par une limite « sous le bruit à n = 2 880 » ; c'est plus
fort : aucune taille d'échantillon ne le rendrait possible.

**Vérifié** : sur les 141 spectres du juge (48 réels, 48 permutés, 45 témoins), R_log-normale ≤
**2,7·10⁻¹³** (zéro machine). La vraisemblance log-normale atteint le bord c₁ = 0 (σ = ∞) sur 11 des
48 matrices réelles et sur la plupart des Pareto vrais. Corollaire : les **13 valeurs R_lognormale > 0**
du tableau publié (`ajustements.out`, jusqu'à +0,096 sur L12.down.E19) sont des optima numériques
inachevés de la paramétrisation (μ, σ), qui part vers μ → −∞ sans l'atteindre. Aucun verdict n'en
dépend (p ≥ 0,34 partout là), mais le texte doit le dire. C'est aussi la vraie raison de « l'écart
restant de p contre la log-normale » noté au second chemin de la piste (`spectres.md` § 2).

À reprendre pour le mémoire (Tome III) : ce paragraphe est la dérivation complète, en trois lignes ;
il remplace la phrase « sur une étendue observée de quelques unités de y, la courbure y²/(2σ²) qui les
sépare est sous le bruit ».

## 3. Le chiffre principal refait

Outil : `outils/pistes/spectres/juge/juge_csn.py` (commits 2ca319b, 2ae9da5), comparaison
`comparer.py`. Différences de chemin avec la piste : KS bilatérale exacte par blocs vectorisés,
log-normale en paramètres naturels (c₁ ≥ 0, b) partant des moments et jamais du point loi de
puissance, normalisation par `erfcx`, répliques p_gof de graine 777 (et non celle de la piste).
Calcul sur processeur seul, 1 fil, priorité sous la normale, en pause pendant les séances ABBA
(séances du juge disque et du placement entre 23:45 le 26 et environ 01:20 le 27 ; cassure de 01:21
à 01:43, passe complète de 01:43 à 02:27, sans séance de vitesse pendant ces deux passes).

| contrôle (seuil `juge-seuil.md`) | attendu | mesuré | verdict |
|---|---|---|---|
| J1 verdict principal | 0 / 48 et R_LN ≤ 10⁻⁶ partout | 0 / 48 ; R_LN max 2,7·10⁻¹³ | **TIENT** |
| J2 verdict amendé | 9 ± 1, accord ≥ 45 / 48, désaccords au bord | **9 / 48**, accord **48 / 48**, aucun désaccord | **TIENT** |
| J3 λ_min et α̂ | λ_min égaux ≥ 40 / 48, α̂ à 10⁻⁶ | 48 / 48, écart nul (réels et permutés) | **TIENT** |
| J4 α̂ réel < α̂ permuté | 48 / 48 | 48 / 48 (rapport 1,26 à 8,81) | **TIENT** |

Écart des p_gof entre les deux chemins (bruit de Monte-Carlo à 100 répliques) : médian 0,01,
maximal 0,11, sans changer un verdict. Journal `juge-csn.log`, table `juge-csn.csv`.

**Les témoins du juge** (`juge-csn.log`, `juge-csn-casse.log`) :

| témoin | attendu | mesuré |
|---|---|---|
| T-Pareto du npz | compatible, α̂ ∈ [2,3 ; 2,7] | compatible, α̂ = 2,492 : **tient** |
| 20 Pareto α = 2,5 tirés par le juge (graine 4242) | ≥ 18 / 20 compatibles | **20 / 20** |
| 20 exponentielles (graine 4243) | ≤ 2 / 20 | **0 / 20** |
| 4 T-MP du npz | 0 compatible | **0** (α̂ 8,8 à 16,9, « autre loi préférée ») |
| contrôle log-normal (μ = 0, σ = 1) | σ̂ à 5 % | σ̂ = 1,006 |
| **cassure** : `pareto` et `mp/2880x2880` échangés | les deux en ÉCHEC | **les deux tombent** (T-Pareto α̂ = 16,9 non compatible ; T-MP compatible α̂ = 2,49) |

**Les spectres eux-mêmes** (`juge_npz.py`, `juge-npz.log`, lancé verrou libre) : pour L00.down.E24
(la queue la plus lourde) et L23.attn_q (compatible, α̂ < 2), déquantification écrite par le juge
depuis la spécification (E2M1 décodé par ses bits, E8M0 = 2^(e − 127) ; Q8_0), empreintes SHA-256
**égales** à celles du manifeste, valeurs singulières égales au npz à **1,5·10⁻¹⁴** près sur les 400
premières. Le seul point commun avec la piste est le lecteur GGUF du projet (décalages d'octets).

**Solidité du 9 / 48** : 4 des 9 compatibles passent l'exponentielle au bord (p = 0,010 ; 0,024 ;
0,027 ; 0,037) et 3 non-compatibles la manquent de peu (p = 0,059 ; 0,084 ; 0,093). Même en faisant
basculer tous ces cas dans le sens le plus favorable, on atteint 12 sur 48, loin de 32 : le verdict
« pas une loi de puissance » ne dépend pas de ces bords. Le nombre exact 9 en dépend un peu ; il est
reproduit, pas plus solide que ses bords.

## 4. Ce qui est faux, trop beau ou mal dit

1. **Faux** (`spectres.md` § 4.2, point 5) : « La couche 12 de down est le seul endroit où la loi de
   puissance et la log-normale se confondent vraiment ». Au chemin du juge, la log-normale ajustée
   **est** la loi de puissance (bord c₁ = 0) sur 11 matrices : les 4 down de la couche 12, mais aussi
   L00.gate.E22, L00.attn_k, L12.gate.E01, L12.attn_output, L23.down.E07, E21 et E27 (et presque, σ̂ =
   14 à 16, L23.gate.E07 et E27). Le tableau publié le montre déjà : μ = −69 à −118 pour ces sept-là.
   À corriger.
2. **Mal dit, rendu du rôle** : « gate 3,0 à 4,0 ; up 3,7 à 5,8 » se lit comme des étendues ; ce sont
   les **médianes par couche** (`spectres.md` § 4.1). Les α̂ individuels vont de 2,70 à 5,95 pour gate
   et de 3,50 à 8,32 pour up. Écrire « médianes par couche ».
3. **Mal dit, rendu du rôle** : « 4/6 sous α̂ = 2 ont un levier (tient), mais 5/30 au-dessus de 2 en
   ont un ». Depuis `seuil.md` § 7 nonies (déclaré avant la lecture du test), ce test éprouve
   « N_r(16) contre la base blanche > 0,05 », **pas un levier**. Le mot levier est à retirer de cette
   phrase ; la conclusion (la règle tombe, aucun levier n'en sort) reste.
4. **Théorème au lieu d'un manque de puissance** (§ 2) : à reformuler dans `spectres.md` § 2 et dans le
   mémoire ; les 13 R_lognormale > 0 publiés sont des optima inachevés, à signaler.
5. **Trace manquante** : les nombres « 0,59 et 0,63 » de l'amendement (§ 1) n'ont pas de journal.
6. **Ce qui n'est pas trop beau** : le verdict est négatif, il n'arrange personne ; le seul résultat
   « positif » (plus de queue que le permuté, 48 / 48) est large (rapport ≥ 1,26) et reproduit. Le
   permuté est une seule permutation par matrice ; à cet écart, une autre graine ne le renverserait
   pas, mais ce n'est pas mesuré.

## 5. Ce que le juge n'a pas jugé

- Les chiffres de levier (L1, L2, L3d), le plafond spectral (0,42 bit), le plafond par rang, le test de
  prédiction sur 36 matrices neuves, la mesure exploratoire `normalise` et la passe du plafond
  par rangée (encore en cours, non finie : le juge a seulement constaté que les 36 lignes déjà sorties
  hors attn_q donnent E_rang de +0,043 à +0,391, conforme au rendu « +0,04 à +0,39 », et que ses deux
  témoins sont écrits « TIENT » dans `plafond-rangee.log`).
- Les spectres de 46 matrices sur 48 contre le modèle (vérifiés par le second chemin de la piste, même
  auteur ; le juge en a refait 2).
- Les limites déjà dites par la piste restent entières : échantillon de 2 % des matrices, 3 couches,
  poids déquantifiés et non BF16, garde de 50 points choisie et non dérivée, Martin et Mahoney lus par
  leur seul résumé.

## 6. Traçabilité

| commit | contenu |
|---|---|
| a52beeb | `juge-seuil.md`, avant tout calcul du juge |
| 2ca319b | outil, passe sans répliques (J1, J3, J4) |
| 2ae9da5 | balayage vectorisé (identique au bit sur les 141 lignes de la passe rapide), contrôle npz écrit |
| e20651e | cassure, contrôle npz contre le modèle |
| (ce commit) | passe complète (J2, témoins), comparaison, ce jugement |

Incident dit : deux premières passes avec répliques (balayage en boucle simple, priorité « inactive »)
coupées par le juge lui-même avant toute ligne réelle, pour accélérer le balayage ; aucune ligne n'en
a été lue ni gardée.
