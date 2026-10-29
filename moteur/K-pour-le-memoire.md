# Lot K (noyaux), ce que le Tome II doit porter

Étapes K1 (décodeur rANS à table par voie, sur la carte) et K2 (GEMV MXFP4). Spécification :
`decisions/ARCHITECTURE.md` § 4.9 à 4.11 (couture F), § 5.6 (couture N), § 6.5. Code :
`moteur/crates/trc-noyaux/` (noyaux `noyaux/*.cuh`, enveloppes `src/`, témoins `tests/carte.rs`,
banc `banc/banc_k.cu`). Journaux : `mesures/moteur/K/`. Sources : `memoire/sources/moteur-K.bib`
(et `03-entropie.bib` pour le rANS). Les chiffres ci-dessous sont repris des journaux nommés ; le
rédacteur les relit dans les fichiers, jamais ici.

## 0. D'où on part, où on va

- **Au départ** : l'étude 03 avait un décodeur rANS v4 sur la carte (CUDA, 80,8 et 82,1 Go/s en
  ABBA sur un grand flux) et une GEMV MXFP4 brute sous Vulkan (209,4 Go/s). La table par voie
  (contexte connu du décodeur) n'existait que sur le processeur (mesure F1 de l'arbitre).
- **Ce que K établit** : le décodeur à table par voie sur la carte, exact sur les 4 608 experts de
  gpt-oss-120b (deux passes : noyaux v2 puis noyaux finaux) codés par un codeur indépendant, et sur
  les 768 experts du vrai fichier `gpt-oss-20b.trc` du lot F, par deux chemins de lancement (un
  expert, un lot) ; la GEMV MXFP4 exacte au bit sur entiers, à 3·10⁻⁷ d'une référence f64 sur poids
  réels ; les débits en ABBA contre les seuils déclarés (§ 4).
- ~~**Ce qui reste** : K3 (la passe avant, douze noyaux, jugée contre `trc-reference`), K4 (mode base
  de J2).~~ K3 est fait (§ 7) : les douze noyaux de la passe avant tiennent contre `trc-reference`
  sur les poids réels des deux modèles, et la chaîne de bout en bout tient sous routage imposé. Le
  témoin K1 contre le codeur du lot F tient aussi sur `gpt-oss-120b.trc` (4 608 / 4 608). **Ce qui
  reste** : K4 (mode base de J2) ; la chaîne sur le 120b ; la cause de l'effet de première série.

## 1. Structures au bit près (figures à dessiner)

**F-K1, la tuile rANS et la table par voie** (M4 de l'arbitre). Un macro-pas = 32 voies × 4
sous-pas = 128 octets de sortie contigus ; la voie l du macro-pas m écrit le mot de 32 bits
w = 32m + l, ses sous-pas k = 0..3 en écrivent les octets du poids faible au poids fort. Pour
CODES_CTX un bloc MXFP4 porte 16 octets = 4 mots : les voies 4q .. 4q + 3 du macro-pas m écrivent le
bloc 8m + q, et choisissent toutes les quatre la LUT du contexte κ(8m + q). Dessin : une rangée de 32
voies, groupées par 4 sous une même couleur de LUT (trois couleurs pour κ = 0, 1, 2), au-dessus de
la ligne des 128 octets produits ; en dessous, la fenêtre de mots du flux partagé (§ 2.2).

**F-K2, l'emplacement SoA** (§ 5.6) : pour gpt-oss, par matrice, codes 4 147 200 o au décalage 0,
échelles 259 200 o au décalage 4 147 200, biais 11 520 o au décalage 4 406 528, pas 4 418 048 ;
emplacement 13 254 144 o. Test `disposition_de_gpt_oss_egale_la_specification` (src/abi.rs).

**F-K3, l'entrée de LUT de géométrie 1** : 32 bits = symbole (bits 0-7) | f − 1 (bits 8-19) |
fente − cumul (bits 20-31). f − 1 et non f : f = 4 096 (symbole unique) tient en 12 bits (test
`symbole_unique_a_frequence_pleine`).

**F-K4, le descripteur de lot** `DescDecodage` (32 o : partie, emplacement, LUT, contrôle, u64
chacun) et `DescGemv` (32 o : matrice, x, y en u64, lignes, colonnes en u32).

**Tableau T-K1, ressources des noyaux** (ptxas, `-Xptxas -v`, sm_89, journal de construction à
recopier) : decoder_codes 57 registres, 49 152 o partagés (trois LUT) ; decoder_echelles 55
registres, 24 576 o (une LUT + 8 192 o de médianes) ; versions lot 61 et 57 registres ; gemv_mxfp4
71 registres ; gemv_mxfp4_lot 79 ; copier_brut 29. Occupation (Ada, 100 Kio partagés par SM, 48
warps, 64 K registres [nvidia2026adatuning]) : decoder_codes, 2 blocs de 8 warps par SM (limite :
la mémoire partagée), 16 warps par SM, 384 sur les 24 SM.

## 2. Dérivations (à écrire en entier)

### 2.1 Le pas d'un warp rend exactement le décodage scalaire

Énoncé. Soit une tuile codée par le codeur du § 4.9.2 (ordre inverse : macro-pas, sous-pas, voies
décroissants ; chaque voie part de L = 2¹⁶ ; pile de mots renversée). Le noyau, qui fait pour chaque
sous-pas les 32 voies en même temps, produit les mêmes symboles que le décodeur scalaire qui fait
les voies une à une dans l'ordre croissant.

Démonstration. (i) Le calcul de l'état d'une voie, `x ← f·(x >> 12) + b`, ne dépend que de son
propre état et de la LUT : il commute entre voies. (ii) Seul l'ordre de lecture des mots lie les
voies. Dans le décodeur scalaire, au sous-pas (m, k), les voies qui renormalisent (y < L) lisent les
mots p, p + 1, … dans l'ordre croissant des voies. Le noyau calcule `vote = ballot(y < L)` et donne à
la voie l le mot `p + popc(vote & ((1 << l) − 1))`, c'est-à-dire p plus le nombre de voies d'indice
inférieur qui lisent aussi : exactement la position scalaire. Puis `p ← p + popc(vote)`, comme le
scalaire après les 32 voies. (iii) Le codeur a émis ses mots dans l'ordre exactement inverse de ces
lectures (dernier émis = premier lu, par le renversement de la pile) : chaque voie relit le mot
qu'elle a écrit. Par récurrence sur les sous-pas, état et pointeur sont égaux à chaque étape. ∎

Contrôle gratuit. En fin de tuile chaque voie doit valoir L (l'état initial du codeur), et le
pointeur doit égaler `début[t + 1]` (ou W) ; ce second contrôle, ajouté au § 4.12 par le noyau et
par le lot F indépendamment, voit un mot de trop que le premier ne voit pas (lot F, témoin des
témoins).

### 2.2 La fenêtre de mots ne déborde jamais

Le warp tient 96 mots de 32 bits du flux (192 mots de 16) dans trois registres par voie : `cour`
(base + voie), `suiv` (base + 32 + voie), `apres` (base + 64 + voie), échangés par `shfl`.
Invariant I : avant chaque sous-pas, `(p >> 1) − base < 32`. Pendant le sous-pas, une voie lit au
plus le mot p + 31, d'indice de mot 32 bits `(p + 31) >> 1 ≤ (p >> 1) + 16` ; donc
`wi = (pos >> 1) − base < 48` : le mot est dans `cour` ou `suiv`, jamais au-delà. Après, `p' ≤ p + 32`,
donc `(p' >> 1) − base < 48` ; si `≥ 32`, la fenêtre avance de 32 (une seule fois suffit, `< 16`
ensuite), et I tient. La lecture d'avance (`apres`, version v2) est chargée une avance plus tôt et
ne sert qu'à l'avance suivante, au moins 2 sous-pas plus tard (il faut consommer 32 mots de 32 bits =
64 mots de 16, soit au moins 2 sous-pas de 32 lectures). En moyenne [calc.] : une renormalisation
apporte 16 bits et un symbole en consomme son coût en bits ; un octet de CODES_CTX coûte ≈ 2 × 3,81
= 7,6 bits (gpt-oss-120b, `bits_par_poids_entropie_tables`), d'où ≈ 7,6/16 = 0,48 lecture par voie
et par sous-pas, ≈ 15 mots de 16 par sous-pas pour le warp, et une avance de fenêtre tous les
≈ 64/15 ≈ 4,2 sous-pas ; un octet de DELTA coûte ≈ 32 × 0,034 = 1,1 bit (03 et F), d'où une avance
tous les ≈ 30 sous-pas. Avec deux registres, le mot chargé à l'avance (dans `suiv`) sert dès que
le pointeur a franchi 16 mots de 32 bits de plus, soit ≈ 2 sous-pas de CODES_CTX en moyenne ; avec le
troisième registre, le mot chargé (dans `apres`) ne sert qu'après ≈ 4,2 + 2 ≈ 6 sous-pas : sa latence est cachée derrière ces pas, ce qui
est la raison de la v2 (REPRISE-K, essais de 13 h 07). Garde : `mot32` rend 0 au-delà de ⌈W/2⌉, si
bien qu'un flux corrompu ne fait jamais lire hors de la partie.

### 2.3 La table par voie est juste et ne diverge pas

Le contexte du mot w est κ(⌊w/4⌋), fonction de δ, connu avant le décodage de CODES_CTX (DELTA est
décodé par le premier noyau, § 4.9.3) : codeur et décodeur choisissent la même table, donc (2.1)
s'applique table par table. Le choix est une adresse (`lut[ctx]` en mémoire partagée), pas une
branche : les 32 voies exécutent la même instruction, seules leurs adresses diffèrent. Le noyau lit
κ un macro-pas d'avance (v2) : l'échelle et la médiane du bloc suivant sont chargées pendant les
quatre sous-pas du bloc courant.

### 2.4 Déterminisme

Le décodeur ne fait que des opérations entières ; ses seuls atomiques sont des compteurs entiers
(commutatifs) ; la sortie de chaque voie ne dépend que de la tuile, pas de l'ordre d'exécution des
warps ni de la grille (une tuile = un warp, parcours par pas de grille). D'où : toute grille rend les
mêmes octets, et le lot rend les mêmes octets que l'expert seul (mêmes corps de carte,
`corps_echelles` et `corps_codes`), ce que le test `decodeur_en_lot_egal_au_seul` vérifie au bit.

### 2.5 Modèle de latence du décodage d'un expert (pourquoi le lot)

Pour gpt-oss, une matrice de DELTA fait 259 200 o = 2 025 macro-pas = 8 tuiles de 256 macro-pas ;
une matrice de CODES_CTX 4 147 200 o = 32 400 macro-pas = 127 tuiles. Un expert : 24 tuiles de DELTA,
381 de CODES_CTX. Chaque tuile est une chaîne de 256 × 4 = 1 024 sous-pas dépendants (l'état x de
chaque voie). Donc

  T_expert ≈ T_DELTA + T_CODES ≈ 1 024 τ_1 + 1 024 τ_16 + 2 t_lancement,

où τ_1 est la durée d'un sous-pas quand un seul warp occupe son SM (24 warps sur 24 SM : latence
pure de la chaîne : LUT partagée, multiplication, vote, deux échanges, sélection) et τ_16 celle d'un
sous-pas quand 16 warps se partagent un SM (vague unique de 381 warps sur 384 places). La phase
DELTA laisse la carte vide à 94 % (24 warps sur 384 places). En lot de n experts de la même couche :

  T_lot(n) ≈ 1 024 τ_n' + n · 1 024 τ_16 + 2 t_lancement, avec 24n warps de DELTA en vol,

et le débit par expert tend vers 1/(1 024 τ_16) quand n grandit. Le rapport attendu A/C vaut
(τ_1 + τ_16)/(τ_1/n + τ_16) à τ' ≈ τ_1. Les médianes de `decomposition_s_medianes` (journal K1)
donnent T_DELTA et T_CODES mesurés : la figure G-K2 confronte ce modèle à la mesure.

Première confrontation [mes., passe propre de 16 h 46, `journaux/interrompu-20261015-1646/`,
120b couche 17] : T_DELTA = 152 µs, T_CODES = 195 µs, trou 2 µs, d'où τ_1 = 152/1 024 = 148 ns et
τ_16 = 195/1 024 = 190 ns par sous-pas (à ≈ 2,67 GHz relevés par le pilote : ≈ 400 et ≈ 510 cycles ;
le sous-pas d'un warp seul est donc long, de l'ordre de dix latences dépendantes : LUT partagée,
multiplication, vote, deux échanges, sélection, avance de fenêtre). Le modèle prédit pour A
152 + 195 + 2 ≈ 349 µs par expert (mesuré : 343 µs, les deux lancements se chevauchant un peu) et pour
C (n = 4) (152 + 4 × 195)/4 = 233 µs par expert, **mesuré 233,2 µs** (53,35 Go/s de codes). Le
modèle n'a aucun paramètre libre : ses deux temps sont mesurés sur A, sa prédiction porte sur C.

Conséquence chiffrée : le décodage d'un expert seul est borné par la longueur de chaîne (1 024
sous-pas) et non par la bande passante ; deux leviers seulement : moins de sous-pas par tuile (N plus
petit au codage : couture F, coût en octets d'en-tête, 0,4 % par flux de plus [mes. 03]) ou plus de
tuiles en vol (le lot). La borne du lot quand n → ∞ : 12 441 600 o / 195 µs = 63,8 Go/s de codes.

### 2.6 La GEMV exacte au bit sur entiers

Valeur d'un poids : k[c] · 2^(e − 128), k ∈ {0, 1, 2, 3, 4, 6, 8, 12} signé (grandeurs E2M1
doublées, 03-derivations § 1.2). E8M0 → f32 exact par construction des bits : e ≥ 2 donne l'exposant
e − 1 (2^(e−128) normal), e ∈ {0, 1} donne les sous-normaux 2^-128 et 2^-127 (bits 0x00200000 << e) ;
les 256 valeurs sont vérifiées une à une (`e8m0_256_valeurs_fausses` = 0). Le produit d'un bloc,
Σ_i k_i x_i, se fait par `fmaf` dans un ordre fixe (un seul arrondi par opération
[nvidia2026flottants]). Témoin exact : échelles e ∈ [117, 123], x ∈ {−2, …, 2}. Chaque terme
k·x·2^(e−128) est un multiple de 2^-11 de grandeur au plus 24 · 2^-5 = 0,75 ; toute somme partielle
d'une ligne de 2 880 termes est un multiple de 2^-11 de grandeur au plus 2 160 < 2^12 : elle tient
en 12 + 11 = 23 bits ≤ 24 bits de mantisse ; aucune addition n'arrondit, dans n'importe quel ordre.
La carte doit donc égaler au bit la somme exacte : 0 ligne fausse sur 5 formes (dont 2 880 × 2 880,
37 × 96, 5 × 32), et la cassure (référence × 1,01) fait tomber 8 639 lignes sur 8 640 (commit 2e24cc6 ; la ligne qui
tient n'a pas été examinée : [hyp.] une ligne de somme nulle, que × 1,01 ne change pas).

### 2.7 La GEMV sur poids réels : borne d'erreur

Pour une ligne, la somme est faite en f32 en trois étages : 32 termes d'un bloc (ordre fixe), puis
les ⌈B/32⌉ blocs d'une voie (B = 90 : 3 blocs au plus), puis l'arbre papillon sur 32 voies (5
niveaux). Une borne a priori (Higham) : |ŷ − y| ≤ γ_{n_e} Σ|termes|, avec n_e = 32 + 3 + 5 = 40
additions en chaîne au plus, γ = n_e u / (1 − n_e u), u = 2^-24 : ≈ 2,4·10⁻⁶ × Σ|termes|. Le seuil
déclaré (10⁻⁵ de max|y|) suppose Σ|termes| ≤ 4 max|y| ; mesuré : 2,9·10⁻⁷ au pire sur 24 matrices
réelles (`k2-justesse-gptoss120b.json`), soit 34 fois sous le seuil. Le déterminisme suit de l'ordre
fixe (aucun atomique flottant) : lot et seul rendent les mêmes bits (`lot_different_du_seul` = 0).

### 2.8 Le toit de la GEMV

Une matrice 2 880 × 2 880 lit 4 406 400 o de MXFP4 équivalents (codes + échelles), plus 11 520 o
de biais et 11 520 o de x. La bande passante de la VRAM de la RTX 4060 Laptop (bus 128 bits,
GDDR6) borne le débit ; 209,4 Go/s mesurés sous Vulkan (03) sont la référence ; le seuil de K2 est
0,8 × 209,4 = 167,5 Go/s. À ce débit une couche (12 matrices de 4 experts) prend ≈ 0,32 ms : la
GEMV d'un jeton (36 couches) ≈ 11 ms, à comparer aux 157 ms de disque d'un jeton (LRU calé, 07).

## 3. Témoins et cassures (tableau T-K2)

| Témoin | Journal | Résultat | Cassure | Résultat de la cassure |
|---|---|---|---|---|
| 120b, 4 608 experts, codeur indépendant du banc, noyaux v1 | k1-justesse-gptoss120b.json | 0 faux, 0 hors L | LUT κ = 1 faussée ; bit de flux | 8 faux / 0 hors L ; 2 faux / 64 hors L |
| 120b, noyaux v2 | k1-justesse-v2-gptoss120b.json | 0 faux sur 4 608 | — | — |
| 120b, noyaux finaux | k1-justesse-v3-gptoss120b-c0-4-partiel.log et -c5-35.json (deux passes, la première arrêtée pour laisser la machine au traceur 120b) | 0 faux sur 640 + 3 968 = 4 608 | — | — |
| vrai fichier du lot F, 768 experts, contre trc-codec et le répertoire, seul et en lot | k1-trc-gptoss20b.json | 0 faux par les deux chemins | `--casser lut` ; `--casser flux` | 8 faux, 0 hors L ; 8 faux, 171 hors L, 7 pointeurs (mêmes comptes en lot) |
| enveloppes Rust (image embarquée, API du pilote) | `cargo test -p trc-noyaux` | 9 tests verts | fente, bit, magie ; référence × 1,01 (`TRC_K_CASSER=gemv`) ; descripteur de lot unique | tombent |
| GEMV entiers, E8M0, réels | k2-justesse-gptoss120b.json | 0 ligne fausse ; 2,9·10⁻⁷ | référence × 1,01 | tout tombe (k2-casse) |

Fait à dire : la fente de LUT faussée rend une sortie fausse **sans** sortir une voie de L (0 hors
L) : la fin à L ne garde pas la table (03 § 3.3) ; c'est pourquoi les tables portent une empreinte
vérifiée à l'ouverture (§ 4.12).

## 3 bis. Résultats des bancs (séance propre du 2026-10-15, 20 h 24, `mesures/moteur/K/journaux/*-2024.*`)

Tableau T-K3 (Go/s ; codes écrits pour K1, MXFP4 équivalents pour K2 ; deux processus par variante,
5 × A B C C B A chacun ; seuils déclarés avant) :

| Variante | Médianes | Pires passes | Seuil | Verdict |
|---|---|---|---|---|
| K1 A, un expert à la fois, N_DELTA = 256 (verdict déclaré) | 36,43 / 36,29 | 32,99 / 32,92 | 33,28 (0,8 × 41,6) | **tombe de 0,9 %** (première série de chaque processus) |
| K1 C, lot de 4 | 53,41 / 53,23 | 53,37 / 53,18 | 33,28 | tient |
| K1 D, DELTA en tuiles de 32 | 55,09 / 55,00 | 52,49 / 51,92 | 33,28 | tient (prédit 57 ± 10 %) |
| K1 D + lot de 4 | 58,80 / 58,72 | 58,75 / 58,64 | 33,28 | tient |
| référence refaite : v4 de 03 sous CUDA puis réassemblage | 45,79 / 45,75 (composé) | — | — | ~~41,6~~ publié par 03 avec le v4 sous Vulkan |
| copie brute (B) | 105,47 / 105,44 | — | — | — |
| K2 lot de 12 matrices | 235,35 / 235,41 | 219,13 / 220,89 | 167,5 (0,8 × 209,4) | tient (+12 % sur Vulkan) |
| K2 une matrice par lancement | 160,21 / 159,87 | — | — | — |

Ce que le mémoire doit dire, dans cet ordre : (1) le seuil déclaré tombe pour la variante déclarée, de
0,9 %, sur un effet de première série ; on ne retire pas la passe ; (2) la référence elle-même était
sous-estimée (Vulkan, 70 Go/s, au lieu de CUDA, 82,6) : contre la référence CUDA refaite, la médiane
de A tombe aussi ; (3) le modèle de latence (§ 2.5) explique pourquoi et prédit les deux remèdes ; (4)
les deux remèdes tiennent contre les deux références, l'un sans toucher au format (D), l'autre sans
toucher au codeur (C) ; (5) la prédiction de D était juste sur le total et fausse sur sa partie
DELTA (34,8 µs mesurés contre 19 à 22 prédits : avec 8 warps par SM, le sous-pas passe de 148 à
272 ns) : le modèle ignore la contention à 8 warps par SM, ce qui est à écrire dans « Ce qui pourrait
être faux ».

Décomposition (G-K2) : A : DELTA 151 à 153 µs, CODES 194,6 µs, trou 2 µs ; D : DELTA 34,8 µs.

## 4. Graphes des bancs (données CSV à tirer des journaux)

- **G-K1** : débit du décodeur (Go/s de codes) par passe, A (expert par expert), B (copie brute),
  C (lot de 4), séries A B C C B A × 5, avec le seuil 33,3 en trait horizontal et la référence de 03
  (41,6) en pointillé ; barres : min-max des passes. Journaux `journaux/k1-debit-*.json`.
- **G-K2** : décomposition du temps d'un expert (DELTA, CODES_CTX, trou entre lancements) en barres
  empilées, face au modèle du § 2.5.
- **G-K3** : débit de la GEMV (Go/s de MXFP4 équivalents), lot de 12 contre une matrice par
  lancement, ABBA × 5, seuil 167,5, référence Vulkan 209,4.
- **G-K4** : histogramme de l'écart relatif de la GEMV sur les 24 matrices réelles, seuil 10⁻⁵.
- Le script de conversion en CSV : `mesures/moteur/K/vers_csv.py` → `mesures/moteur/K/csv/`
  (`k1-debit-passes.csv`, `k1-decomposition.csv`, `k1-reference-03.csv`, `k2-debit-passes.csv`,
  `k2-ecarts-reels.csv`, `k1-justesse-par-couche.csv`, `k1-trc-par-couche.csv`).

## 5. Listings commentés

- `pas_octet` (commun.cuh) : le pas du warp, vote, comptage, fenêtre à trois registres.
- `corps_codes` (decodeur.cuh) : la table par voie et la lecture d'avance du contexte.
- `echelle_e8m0` et `produit_bloc` (gemv.cuh) : l'E8M0 exact, l'ordre fixe.

## 6. Ce qui pourrait être faux

- ~~Le témoin 120b repose sur le codeur du banc (lot K) : il prouve que le décodeur égale le § 4,
  pas que le codeur du lot F l'égale ; ce second point est prouvé sur le 20b seulement (le 120b du
  lot F n'est pas encore écrit).~~ Le second point est prouvé aussi sur le 120b depuis 20 h 52 :
  4 608 / 4 608 contre le fichier du lot F (`k1-trc-gptoss120b.json`).
- Le seuil de K1 compare un débit **par expert** (parallélisme d'un seul expert) à 41,6 Go/s mesurés
  par 03 sur un **grand flux** : la comparaison est prudente pour nous, mais ce n'est pas la même
  grandeur ; C (lot) s'en rapproche.
- Le débit du décodeur ne limite pas le jeton tant que le disque limite (0,4 ms contre 157 ms par
  jeton) : un échec de K1 au seuil ne change pas C5.
- Le modèle de latence du § 2.5 ignore la queue de vague, le recouvrement entre deux lancements et
  la contention quand plusieurs warps de DELTA partagent un SM : il a prédit juste le lot (233 µs)
  et faux la partie DELTA de D (19 à 22 µs prédits, 34,8 mesurés).
- L'effet de première série (pire passe 9 % sous les autres, dans chaque processus) n'est pas
  expliqué ; il a décidé du verdict de K1.
- Les mesures de débit dépendent de la fréquence de la carte d'un portable (gestion d'énergie) ;
  l'état de la carte avant et après chaque passe est journalisé par le pilote.

---

## 7. Étape K3 : la passe avant (douze noyaux), ce que le Tome II doit porter

Code : `noyaux/passe.cuh` (onze noyaux neufs ; `gemv_mxfp4` est celui de K2), enveloppes dans
`src/lib.rs`, structures dans `src/abi.rs`. Témoin qui fait foi : `mesures/moteur/K/temoin-k3/`
(poids réels du GGUF, contre `trc-reference`) ; témoins synthétiques : `tests/passe.rs`. Journaux :
`mesures/moteur/K/k3/` ; CSV : `mesures/moteur/K/csv/k3-*.csv` (script `k3_vers_csv.py`).
Critères déclarés avant le code : `moteur/REPRISE-K.md`, sections K3 (20 h 45, 21 h 10, 21 h 22).

### 7.0 D'où on part, où on va

- **Au départ** : le décodeur et la GEMV MXFP4 (K1, K2) ; `trc-reference` (lot R), la passe avant
  en f64, validée contre llama.cpp (R1).
- **Ce que K3 établit** : les douze noyaux d'une passe avant de gpt-oss. Contre la référence f64,
  les noyaux à seuil sont de 1,6 à 62 fois sous le leur (les noyaux exacts : 0 différence), sur les poids réels des deux modèles, et chacun est
  déterministe au bit. La chaîne entière de 24 couches, faite par ces seuls noyaux sur 160 jetons
  réels, est à KL 3,0·10⁻⁶ de la référence quand le routage est imposé. Sans imposition, l'écart
  vient de bascules de routage aux marges sous 10⁻³, la forme que le lot R a trouvée pour llama.cpp.
- **Ce qui reste** : l'assemblage dans le moteur (O2, lot O), la chaîne sur le 120b, et K4 (le mode
  base de J2).

### 7.1 Figure M-K3-1 : la passe avant, noyau par noyau

Schéma TikZ vertical : une boîte par noyau, des flèches pour les tampons, le type des données à
gauche.

```
 jeton ─► ligne_q8_0 ─► x (f32[2880])
 couche ℓ : ┌ rmsnorm(x, attn_norm) ─► h
            │ gemv_q8_0 ×3 (+biais) ─► q f32[4096], k f32[512], v f32[512]
            │ rope_yarn(q, k, position)               (en f64, un seul arrondi)
            │ ecrire_kv ─► cache f16 [case][8][64]    (case = p, ou p mod 128 si ℓ pair)
            │ attention(q, cache, puits) ─► a f32[4096]
            │ gemv_q8_0 (Wo + bo) ─► o ; combiner(x, o, n = 1)     x ← x + o
            │ rmsnorm(x, post_norm) ─► h₂ ; gemv_f32 (routeur + biais) ─► logits f32[E]
            │ routeur_topk ─► 4 indices, 4 poids ─► boîte aux lettres (case de 64 o, protocole E0 c)
            │ pour i = 0..3 : gemv_mxfp4 gate, up ─► swiglu_oai ─► gemv_mxfp4 down ─► s_i
            └ combiner(x, s₀..s₃, poids, n = 4)       x ← x + (((g₀s₀+g₁s₁)+g₂s₂)+g₃s₃)
 sortie : rmsnorm(x, output_norm) ─► gemv_q8_0 (201 088 × 2 880) ─► argmax ─► jeton suivant
```

### 7.2 Structures au bit près (tableau T-K3-1)

| Structure | Octets | Champs |
|---|---|---|
| `ParamsRope` (par valeur) | 48, alignement 8 | f64 base, facteur, ctx_origine, beta_rapide, beta_lent ; u32 dim_tete ; u32 variante (0 OpenAI, 1 llama.cpp) |
| `ParamsAttention` (par valeur) | 32 | u32 tetes, tetes_kv, dim_tete (64), debut, fin, anneau (0 ou 128) ; f32 echelle (0,125) ; u32 réservé |
| case de la boîte aux lettres du routeur | 4 (2k + 1) = 36 o utiles, dans une case de 64 | mot 0 : séquence, écrite en dernier, après `__threadfence_system` ; mots 1 à k : indices ; mots k + 1 à 2k : poids (bits f32). Protocole de l'essai E0 c du lot E |
| cache KV d'une couche | 2 · cases · 512 | f16 `[case][tête_kv][64]` ; 128 cases sur une couche paire (anneau), sinon la longueur du contexte |
| bloc Q8_0 (ggml) | 34 | f16 d, puis 32 × i8 ; l'adresse d'un bloc est paire, d'où la lecture par mots de 16 bits |

### 7.3 Dérivations (à écrire en entier)

**7.3.1 Un seul arrondi tient à 2⁻²⁴ (rmsnorm, rope_yarn, swiglu_oai, poids du routeur).** Ces
noyaux calculent en f64 sur la carte et arrondissent une seule fois vers le f32. Soit y la valeur
exacte et ŷ64 le calcul en f64. On a |ŷ64 − y| ≤ c · 2⁻⁵³ |y|, avec c petit : une dizaine
d'opérations, plus l'erreur de pow, log, exp, sin et cos de CUDA en double précision (1 à 2 ulp).
L'arrondi au plus proche ajoute |fl32(ŷ64) − ŷ64| ≤ 2⁻²⁴ |ŷ64|. D'où
|ŷ − y| ≤ (2⁻²⁴ + c · 2⁻⁵³) |y|, et l'écart normalisé du témoin vaut
e = max|ŷ − y| / max|y| ≤ 2⁻²⁴ ≈ 5,96·10⁻⁸, à 10⁻¹⁵ près. **Mesuré** (20b puis 120b) :
rmsnorm 5,2 et 5,6·10⁻⁸ ; rope_yarn 5,3 et 4,6·10⁻⁸ ; swiglu 4,9 et 3,5·10⁻⁸ ; poids du routeur 4,7
et 5,0·10⁻⁸. Tous sont sous la borne, et presque à son niveau. Le seuil du § 5.6 (10⁻⁶) laisse 17
fois de marge.
**Pourquoi la rotation se calcule en f64, en un calcul.** L'angle vaut p · θ_i, avec θ_0 = 1. En
f32, l'angle à la position p porte une erreur de l'ordre de 2⁻²⁴ p : 2,4·10⁻⁴ rad à p = 4 096,
7,8·10⁻³ rad à p = 131 072. Une erreur d'angle δ donne une erreur relative de l'ordre de δ sur la
paire tournée. Le seuil de 10⁻⁶ serait donc manqué dès p ≈ 17. En f64, l'erreur d'angle est
2⁻⁵³ p, négligeable à toute position.

**7.3.2 L'enchâssement est exact (ligne_q8_0).** d est un f16, à 11 bits de mantisse. q est un i8,
|q| ≤ 128, à 7 bits significatifs au plus (128 = 2⁷ n'en a qu'un). Le produit tient en 18 bits,
sous les 24 d'un f32, et reste dans l'étendue (|d·q| ≤ 65 504 · 128 et ≥ 2⁻²⁴) : il est exact.
**Mesuré** : 0 différence sur 64 lignes, dont la première et la dernière.

**7.3.3 Les produits exacts au bit sur entiers (gemv_q8_0, gemv_f32, gemv_mxfp4).** Lemme : si
tous les produits et toutes les sommes partielles, dans n'importe quel ordre, sont des multiples de
2⁻ᵐ bornés par 2^(24−m), le calcul en f32 est exact quel que soit l'ordre, car chaque opération
rend un nombre représentable. Application à Q8_0 : d = 2^e, e ∈ [−2, 1] ; q ∈ [−127, 127] ;
x ∈ {−1, 0, 1}. Les sommes sont des multiples de 2⁻², bornés par 128 · 32 · 127 · 2 = 1 040 384 < 2²²
pour C = 4 096. **Mesuré** : 0 différence sur 5 formes, jusqu'à 2 880 × 4 096. La même dérivation
vaut pour f32 (W, x ∈ [−8, 8], somme ≤ 184 320) et pour MXFP4 (e ∈ [127, 129], x ∈ [−2, 2] :
multiples de 2⁻¹, bornés par 138 240).

**7.3.4 Les produits sur poids réels : la borne a priori.** C'est celle du § 2.7, avec
n_e = 32 + 1 + ⌈B/32⌉ + 5 : 41 pour C = 2 880, 42 pour C = 4 096 (attn_output). D'où
γ ≈ 2,5·10⁻⁶ × Σ|termes|. **Mesuré** : 1,6 à 2,6·10⁻⁷ sur q, k, v, o, le routeur, les experts et
la sortie à 201 088 lignes, soit 39 à 62 fois sous 10⁻⁵.

**7.3.5 L'attention, la plus petite marge (1,6 fois).** Le score s_j = (q · k_j)/8 est une somme
de 64 produits en f32 : |δs_j| ≤ γ_64 Σ_t |q_t k_t| / 8, avec γ_64 ≈ 3,8·10⁻⁶. Une erreur δs
change le poids d'un facteur exp(δs) ≈ 1 + δs : l'erreur relative de la sortie est de l'ordre de
max_j |δs_j|. S'y ajoute l'erreur des sommes des e_j et des e_j v_j : au plus n/4 termes par
groupe, puis un arbre de 4, soit ≈ 1 024 additions pour n = 4 096 et γ ≈ 6·10⁻⁵ au pire. Ce sont
des bornes de pire cas ; les erreurs réelles se compensent. **Mesuré** : 2,2 à 6,2·10⁻⁶ sur la
couche à fenêtre, 0,46 à 1,9·10⁻⁶ sur la couche pleine (jusqu'à 4 096 positions), pour un seuil
de 10⁻⁵. Si C4 l'exigeait, des scores en f64 coûteraient ≈ 0,15 ms par couche au plus
[calc. : 64 têtes × 4 096 × 64 × 2 opérations à ≈ 0,2 Tflop/s en f64], sans effet devant le
disque.

**7.3.6 Le combiner est égal au bit à l'hôte.** IEEE 754 fixe le résultat de chaque addition et de
chaque multiplication en arrondi au plus proche pair : mêmes opérandes, même ordre, même mode, même
résultat. Le noyau emploie `__fmul_rn` et `__fadd_rn`, jamais contractés en fma
(nvidia2026intrinseques) ; l'hôte (Rust, x86-64, SSE) ne contracte jamais. **Cassure faite dans la
source** : avec un `fmaf` à la place, le test tombe dès l'élément 649 (tests/passe.rs). Un arrondi
de moins change des bits.

**7.3.7 Le déterminisme des sélections (argmax, routeur_topk).** Les deux noyaux prennent le
minimum de la clé (−v, i) sur les valeurs non NaN. C'est un ordre total : le minimum est associatif
et commutatif, et la réduction rend le même élément quel que soit l'arbre (fixé quand même). Les
égalités se départagent au plus petit indice. Vérifié sur des vecteurs à égalités : quatre maxima
égaux, 128 zéros, maxima aux indices 64 et 127. La cassure « plus grand indice » ne fait tomber que
ces cas. Les réductions flottantes (rmsnorm, attention) suivent un arbre fixe sur 256 fils, sans
atomique.

**7.3.8 L'ordre couche par couche égale l'ordre jeton par jeton (la chaîne).** Soit x_p^ℓ l'état de
la position p après la couche ℓ. Par causalité, x_p^ℓ ne dépend que de x_p^(ℓ−1) et des clés et
valeurs des positions q ≤ p à la couche ℓ, elles-mêmes fonctions de x_q^(ℓ−1). Dans les deux
ordres, chaque x_p^ℓ sort des mêmes noyaux, sur les mêmes octets, dans le même ordre interne. Sur
l'anneau d'une couche à fenêtre, la position p est lue juste après son écriture : les 128 cases
portent alors exactement les positions p − 127 … p. Les deux ordres rendent donc les mêmes bits.
C'est une identité de programme, non mesurée ici. `pas_egal_evaluer` (lot R) est la même identité
pour la référence.

**7.3.9 L'amplificateur de routage (D1, D2).** Soit m la marge du routeur de la référence à une
décision (l'écart entre ses 4e et 5e logits), et δ l'erreur de la chaîne f32 sur cette marge. La
décision bascule si δ > m. Une bascule remplace un expert de poids g (≈ le softmax du 4e logit) par
un autre : l'état de la position change de l'ordre de g ‖s_e − s_e'‖ au lieu de 10⁻⁷. C'est un saut,
pas un arrondi. Il se propage aux couches suivantes de la position, et un peu aux positions plus
tardives, par leur attention.
**Mesuré** (`k3/k3-chaine-d*-gptoss20b*.csv`) : sur 3 840 décisions, 334 ont une marge de
référence sous 10⁻², 34 sous 10⁻³ et 4 sous 10⁻⁴. Sous routage imposé, les états de la chaîne et
de la référence restent égaux à 10⁻⁶ près ; la carte aurait alors basculé 3 décisions, de marges
1,4·10⁻⁴, 3,3·10⁻⁴ et 7,9·10⁻⁴. δ est donc de l'ordre de 10⁻⁴ à 10⁻³, et quatre décisions de marge
plus petite n'ont pas basculé : le signe de δ décide. En routage libre, 22 décisions diffèrent, et
les premières bascules tombent aux positions 67, 87, 114, 129, 136 et 153. Ce sont exactement les
six positions qui portent la KL (99,3 % du total à elles six).
**La conséquence pour C4** : la KL de bout en bout d'un moteur f32 contre la référence f64 ne
mesure pas la précision de ses noyaux. Elle compte les décisions dont la marge est sous le δ du
moteur, chacune au coût d'une bascule. troncons (activations f32, poids exacts) doit avoir un δ plus
petit que llama.cpp, qui ramène ses activations en Q8_0 (lot R). C4 se jouera sur ce terme.

### 7.4 Résultats (tableau T-K3-2, `csv/k3-par-noyau.csv`)

| Noyau | Seuil | Pire écart 20b | Pire écart 120b | Marge (20b) | Cassure (faute injectée dans la référence) |
|---|---|---|---|---|---|
| gemv_mxfp4 | 10⁻⁵ | 2,4·10⁻⁷ | 1,6·10⁻⁷ | 41 | échelle 2^(e − 127) : tombe |
| gemv_q8_0 | 10⁻⁵ | 1,9·10⁻⁷ | 2,5·10⁻⁷ | 53 | biais omis : tombe, sauf les cas attn_k (biais nul, § 7.5) |
| gemv_f32 | 10⁻⁵ | 2,6·10⁻⁷ | 2,2·10⁻⁷ | 39 | biais omis : tombe |
| rmsnorm | 10⁻⁶ | 5,2·10⁻⁸ | 5,6·10⁻⁸ | 19 | moyenne sur n − 1 : tombe |
| rope_yarn | 10⁻⁶ | 5,3·10⁻⁸ | 4,6·10⁻⁸ | 19 | sans la concentration de YaRN : tombe |
| attention | 10⁻⁵ | 6,2·10⁻⁶ | 3,9·10⁻⁶ | 1,6 | puits omis : tombe |
| routeur_topk (poids) | 10⁻⁶ | 4,7·10⁻⁸ | 5,0·10⁻⁸ | 21 | égalité au plus grand indice : tombe (cas à égalités) |
| swiglu_oai | 10⁻⁶ | 4,9·10⁻⁸ | 3,5·10⁻⁸ | 20 | α = 1 : tombe |
| combiner, ecrire_kv, ligne_q8_0, argmax, indices du routeur | égalité | 0 | 0 | — | ordre inversé ; arrondi vers zéro ; ligne voisine ; égalité au plus grand indice : tombent |

Les deux témoins comptent 143 cas (20b) et 116 (120b). Chaque appel est fait deux fois, et les deux
sorties sont égales au bit. Chaque cassure fait tomber son seul témoin ; les onze autres tiennent
(`k3/k3-casse-*`).

Chaîne de bout en bout (tableau T-K3-3 ; gpt-oss-20b, 24 couches, 160 jetons de wikitext-2) :

| Essai | KL moyenne | KL max | Médiane | Premier choix | Verdict (seuil 7·10⁻⁵) |
|---|---|---|---|---|---|
| routage libre (tel que déclaré) | 7,28·10⁻³ | 1,02 | 2,5·10⁻⁶ | 158 / 160 | tombe |
| D2, routage imposé | 3,0·10⁻⁶ | 1,4·10⁻⁴ | 1,8·10⁻⁷ | 160 / 160 | tient |
| D2, cassure : fenêtre sur les couches impaires | 1,6·10⁻² | 1,36 | — | 156 / 160 | tombe |
| D2, cassure : poids inversés | 0,52 | 2,27 | — | 77 / 160 | tombe |

### 7.5 Trouvé en chemin (pour le journal des découvertes)

- **Le biais des clés de gpt-oss vaut exactement 0**, dans les deux GGUF : 512 valeurs sur 512, aux
  couches 0, 1 et 5 (`k3_biais_attention.py`). Les biais de q et de v sont pleins (|b| jusqu'à 3,9).
  Sans puits, un biais de clé ajouterait q · b_k à tous les scores d'une tête et le softmax
  l'effacerait. Avec le puits dans le dénominateur (xiao2024sinks), il ne s'effacerait pas : sa
  nullité est une donnée du modèle, pas une évidence. La cassure « biais omis » l'a fait voir en ne
  tombant pas sur attn_k.
- **La fenêtre ne se voit qu'après 128 positions.** Sous la cassure fenêtre, la KL des positions 0 à
  127 est égale au bit à celle de la chaîne saine (moyenne 2,632·10⁻⁶) ; sur les positions 128 à 159,
  elle vaut 8,2·10⁻². Un témoin de bout en bout plus court que la fenêtre ne voit pas cette faute.
- **Le fma change des bits** : un `fmaf` remis dans combiner fait tomber l'égalité avec l'hôte
  (§ 7.3.6).

### 7.6 Graphes (données dans `mesures/moteur/K/csv/`)

- **G-K3-1** : la marge de chaque noyau à son seuil (seuil / pire écart, échelle log), en barres 20b
  et 120b côte à côte, avec un trait à 1. L'attention est la plus serrée (1,6) ; les noyaux en f64
  tiennent à 2⁻²⁴ (`k3-par-noyau.csv`).
- **G-K3-2** : la KL par position de la chaîne (échelle log), routage libre contre imposé. Les pics
  des six bascules (positions 67, 87, 114, 129, 136, 153) disparaissent sous imposition
  (`k3-chaine-kl.csv`).
- **G-K3-3** : la KL par position sous la cassure fenêtre, avec sa marche à la position 128.
- **G-K3-4** : les décisions de routage en dispersion, marge de la référence en abscisse (échelle
  log), bascules marquées, trait vertical à 10⁻³ (`k3/k3-chaine-d1-gptoss20b-marges.csv` et
  `-d2-`).

### 7.7 Listings commentés

- `combiner` (passe.cuh) : `__fmul_rn` et `__fadd_rn`, et pourquoi aucun fma.
- `inv_freq_yarn` et `rope_yarn` : YaRN en f64, la rampe et la concentration.
- `attention` : les trois phases (scores, softmax avec puits, somme en quatre groupes) et l'anneau.
- `routeur_topk` : la réduction du warp sur un ordre total, et la case de la boîte écrite dans
  l'ordre du protocole E0 c.

### 7.8 Ce qui pourrait être faux

- Les entrées de la couche 1 sont l'enchâssement normé, pas l'état réel après la couche 0. Les
  poids et leurs formes sont réels ; la distribution des activations ne l'est qu'à peu près. La
  chaîne de bout en bout, elle, enchaîne les vraies couches.
- Les témoins par noyau ne voient que les couches 0 et 1. Les autres couches ont les mêmes formes et
  les mêmes types (relevés dans le GGUF), mais d'autres échelles : une couche aux scores
  d'attention plus pointus pourrait rapprocher l'attention de son seuil (marge 1,6 aujourd'hui). La
  chaîne passe par les 24 couches et tient sous D2 : cela borne l'effet sur le 20b, pas sur le 120b.
- La chaîne n'a tourné que sur le 20b, sur 160 positions d'une seule fenêtre. Sur le 120b, il faut
  de l'ordre de 120 Go de lectures, soit ≈ 58 Go par chemin [calc.].
- D2 impose les experts de la référence mais garde les poids de la carte. Il ne sépare donc pas une
  erreur sur les poids du routeur d'une erreur sur les experts ; les deux sont bornées par les
  témoins par noyau (4,7·10⁻⁸ et 2,4·10⁻⁷).
- Le seuil de la chaîne (7·10⁻⁵ en moyenne) était mal posé pour un MoE qui amplifie, comme ceux de
  R1 et de C4 (lot R). Il est resté tel quel et son verdict est publié ; le diagnostic a été déclaré
  après ce premier résultat (21 h 22), et c'est écrit.
- L'attention lit au plus 8 192 positions par appel (mémoire partagée : 4 o par position). C'est
  assez pour le contexte de J1 (4 096), pas pour un long contexte (J3) : il faudra une version en
  tuiles.
