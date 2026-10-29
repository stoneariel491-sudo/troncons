# 07 — Ce qui manque : l'équation du jeton, la carte de l'existant, et trois architectures

Étude 07 de troncons, celle de l'architecte de recherche qui fait la synthèse des six études de
fondation (01 à 06), lues en entier. Rédigée le 2026-10-15 ; toutes les sources ont été consultées
ce jour-là.

Étiquettes : **[mes.]** mesuré ici, sur la machine de Stone, outil et journal commités ;
**[calc.]** calculé, par une formule écrite ici et un outil commité ; **[litt.]** littérature
(éditeur, non reproduit). Un chiffre repris d'une autre étude garde son étiquette et le numéro de
l'étude (« [mes. 01] »).

Outils de cette étude : `outils/07-synthese/`
- `inventaire_gptoss.py` : l'en-tête GGUF de gpt-oss-20b et 120b lu sur le disque de la machine
  (second chemin de l'étude 06) ;
- `raffinement_mxfp4.py` : la couche de base et le complément d'un code MXFP4, mesurés sur les poids
  réels (le mécanisme de l'architecture B) ;
- `plafonds.py` : l'équation du jeton appliquée aux architectures, avec trois témoins repris des
  études 01 et 06 et une cassure qui les fait tomber.

Journaux : `fondations/journaux/07-synthese/` (JSON, et `csv/` pour les figures du mémoire).

---

## 0. En bref

1. **Le juge est un maximum, et sur cette machine c'est toujours le disque qui le tient.** Le temps
   d'un jeton est encadré par `max(T_disque, T_pcie, T_carte) + t0` (étages recouverts) et par leur
   somme (étages en série). Avec les débits mesurés (disque 2,58 Go/s à la taille d'une matrice
   d'expert, PCIe 12,2, GEMV MXFP4 209, décodeur rANS 70 [mes. 01, 03]), pour gpt-oss-120b dans le
   scénario de localité retenu, le disque prend **157 ms par jeton, la PCIe 58, la carte 36**
   [calc.]. Tout levier qui ne touche pas `h_s · R / (r · D_disque)` est, ici, de l'ornement.
2. **Le modèle cible est déjà sur la machine** : gpt-oss-120b MXFP4 (63,4 Go, 3,6 fois la mémoire
   utile, poids d'origine). Second chemin fait ici sur le fichier local : **A = 1,686 Go toujours
   lus, R = 1,909 Go d'experts lus par jeton**, chaque matrice d'expert contiguë sur 4 406 400 octets
   (4,2 Mio), donc lisible d'un seul tenant sans réécrire le fichier [mes.]. L'étude 06 avait 1,69 et
   1,91 par l'en-tête distant.
3. **Trois architectures, opposées par leurs angles, toutes calculées sur les mêmes débits** :

   | | Angle | Modèle | Plafond (jetons/s) : uniforme / LRU calé / Belady calé | Plancher en série (LRU calé) | RAM de pointe | Qualité |
   |---|---|---|---|---|---|---|
   | Base llama.cpp (estimée, à mesurer) | mmap, experts sur le processeur | gpt-oss-120b | 0,14–0,81 / 0,37–1,87 / 0,59–2,66 | — | ≈ 12 Go | référence |
   | **A** | tout par la carte, octets codés sans perte de bout en bout | gpt-oss-120b | **2,05 / 6,24 / 10,3** | 3,93 | 12,3 Go | exacte par construction |
   | **A0** (A sans cache RAM) | la lecture littérale de « sans ram » | gpt-oss-120b | 1,61 / 3,59 / 5,70 | 2,68 | **1,9 Go** | exacte |
   | **B** | précision selon l'étage : raffinement exact, base seule aux défauts | gpt-oss-120b | 2,93 / ~~**8,88**~~ / 14,6 ; B1 complété : 2,02 / **6,16** / 10,21 | ~~5,09~~ 4,83 | 12,1 Go | 23 % des usages d'experts à 4,3 % d'erreur relative, à juger |
   | **C** | lire moins souvent : dense lu du disque, arbre de vérification | Llama-3.3-70B IQ3_XXS | 0,26 sans spéculation → **2,50** à 9,7 jetons par passe [litt.] | 1,68 | ≈ 12 Go | celle de l'IQ3_XXS, sans perte ajoutée |

   [calc., `plafonds.json`] Les trois scénarios de localité calent `h(c) = c^β` sur le seul point
   publié exploitable (LRU 65,9 % des demandes à 13,4 % du budget, Belady 79,1 %, Qwen3-30B-A3B) ;
   ce sont des hypothèses, et la courbe réelle de gpt-oss-120b est la première mesure à faire (elle
   ne demande aucun téléchargement).
4. **Le mécanisme neuf de B est mesuré sur les poids réels** (12 tenseurs de gpt-oss-20b,
   3,19 milliards de poids) [mes.] : on range chaque code E2M1 en une **base** (signe et 4 classes
   de magnitude, 2,64 bits d'entropie) et un **complément** (1,22 bit) qui rend le code exact. Comme
   la base est une fonction du code, la somme ne coûte rien (identité vérifiée à 10⁻⁹). Lue seule,
   la base reconstruit les poids à **4,29 % d'erreur quadratique relative** ; le MXFP4 lui-même porte
   1,33 % sur une source gaussienne. La troncature des bits de poids faible (le geste des codes
   « Matryoshka », SliceMoE) est battue des deux côtés : 4,47 % d'erreur pour 2,91 bits.
5. **Ce qui manque dans le monde, en un chiffre chacun** (§ 3) :
   - ingénierie : la chaîne disque → RAM épinglée → PCIe en octets codés → décodage sur la carte →
     cache d'experts en VRAM, sous Vulkan, sous Windows, n'existe nulle part ; **×2,5 à ×17** sur la
     base estimée ;
   - ingénierie : des lectures explicites à la taille d'un expert plutôt que des fautes de page :
     **×2 à ×12** sur l'étage disque (1,31 ou 0,22 contre 2,58 Go/s [mes. 01]) ;
   - recherche : le raffinement exact d'un format 4 bits natif, lié à l'étage : ~~**×1,42** sur A à
     localité égale (B1), ×1,75 si la RAM ne garde que la base (B2)~~ (barré par l'arbitre le 2026-10-15 : les octets des compléments n'étaient pas comptés ; comptés, B1 plafonne à 6,16 jetons/s, série 4,83, et le gain de débit de B passe à B3, 10,89 à 48,5 % d'usages servis par la base ; second chemin : `decisions/journaux/arbitre/verif-plafonds.json`, décision : `decisions/ARCHITECTURE.md` § 1.3) ;
   - recherche : la courbe `h(c)` des MoE de 2026 aux budgets d'un portable : entre le scénario
     uniforme et le scénario LRU, **×3,0** sur le plafond de A ;
   - recherche : la spéculation sur un MoE lu du disque ne paie que si `α > 1 − ρ` (ρ, la part
     d'experts réutilisés d'un jeton au suivant) ; personne ne publie ρ pour gpt-oss-120b.
6. **Le plus gros levier n'est pas un logiciel** : le volume C: est chiffré par BitLocker et passe par
   Intel RST VMD ; le disque livre 47 % de son annonce [mes. 01]. Un volume `D:` non chiffré (script
   prêt, `outils/creer-disque-modeles.ps1`, geste de Stone en administrateur) porterait A de 6,24 à
   **14,1 jetons/s** et B de 8,88 à **19,4** dans le scénario LRU, si le disque y atteint 6,0 Go/s
   [calc.] ; la part de VMD dans les 47 % n'est pas connue, c'est donc une borne haute.
7. **Ma recommandation à l'arbitre** (réponse par délégation du 2026-10-15, réversible) : construire
   A d'abord (aucun téléchargement, toutes ses briques sont déjà mesurées sur la machine : lecture
   de 4 Mio, DMA, décodeur, GEMV), dans un format de fichier qui prépare B (base et complément dans
   deux flux) ; mesurer `h(c)` et ρ sur gpt-oss-120b avant tout ; garder C pour plus tard.

---

## D'où on part, où on va

**Au départ** (le matin du 2026-10-15) : des plafonds de fiche technique (lien NVMe 7,877 Go/s, PCIe
15,754, VRAM 256), un modèle visé non choisi, et la phrase de Stone : faire tourner « un modele
ultra lourd quelcoque […] sans ram ni rien », en compressant à l'extrême et en décompressant « à
l'instant exacte du noeud ».

**Ce que les six études ont établi** : le débit réel de chaque étage, mesuré avec témoins et ABBA
(01) ; ce que vaut chaque bit retiré et le premier décodeur de treillis portable (02) ; ce qui reste
d'entropie dans les GGUF et un décodeur rANS Vulkan à 70 Go/s (03) ; tout ce qui existe pour charger,
cacher et précharger, jugé par octets ÷ débit (04) ; la spéculation et la sparsité, chiffrées pour le
régime disque (05) ; les modèles visés, leurs octets par jeton et le protocole de jugement (06).

**Ce que cette étude ajoute** : une seule équation qui contient les six études, chaque technique
placée sur l'un de ses termes, les trous chiffrés par cette équation, deux mesures neuves (le second
chemin de l'inventaire et la couche de base du MXFP4), trois architectures calculées sur les mêmes
débits, et la liste de ce qu'il faut demander à Stone.

**Ce qui reste** : la courbe de succès réelle de gpt-oss-120b (une trace de routage), la base
llama.cpp mesurée sur ce modèle, puis la construction de A, et la mesure de qualité de B.

---

## 1. L'équation du problème

### 1.1 Le jeton comme chaîne d'étages

Un jeton de décodage (lot de 1) applique chaque poids actif une fois. Ses octets traversent une
chaîne d'étages : disque → RAM → PCIe → VRAM → unités de calcul. L'étage `i` a un débit effectif
mesuré `D_i` et doit faire passer `O_i` octets par jeton. L'étude 01 l'a posé (proposition 1) :

    t ≥ max_i O_i / D_i                (aucun ordonnancement ne fait mieux)
    t = Σ_i O_i / D_i                  (sans aucun recouvrement)

J'y ajoute trois termes que les six études ont rencontrés :

    t_jeton = (1 / E_spec) · [ max(T_disque, T_pcie, T_carte) + t_lat ] + t0

- `t0` : le coût fixe d'un jeton (lancements de noyaux, synchronisations, couches récurrentes),
  **≈ 3,5 ms** [calc. sur mes. 02 : Qwen3.5-4B Q4_K_M tout en VRAM, 14,4 ms mesurés contre 10,9 ms
  pour ses 2,73 Go à 251 Go/s].
- `t_lat` : la latence que la lecture n'a pas pu cacher. Elle vaut 0 si le préchargement tient la
  file du disque pleine, et peut dominer sinon : chez Edge0, le temps bloqué sur les lectures (101,9 à
  575 ms par pas) dépasse de loin le temps où le disque travaille (au plus 12 % du pas) [litt. 04].
  C'est l'écart entre le plafond (max) et le plancher (somme).
- `E_spec` : les jetons rendus par une lecture des poids, ≥ 1 avec la spéculation (05) ; pour un MoE,
  la lecture grossit avec `n` (l'union des experts), ce qui se traite au § 1.5.

### 1.2 Les termes pour un MoE servi par la carte

Notations (04 § 1.2, 06 § 4) :
- `A` : octets toujours lus (attention, routeurs, normes, tête), résidents en VRAM ;
- `R` : octets d'experts lus par jeton ; `E_tot` : octets de tous les experts ;
- `h_v`, `h_r`, `h_s = 1 − h_v − h_r` : parts des octets d'experts servies par la VRAM, la RAM, le
  disque ;
- `r_d`, `r_p` : facteurs de compression des octets qui traversent le disque et la PCIe (octets
  servis ÷ octets transportés) ;
- `D_dec` : débit du décodeur sur la carte (octets servis produits par seconde) ; `D_g` : débit de
  la GEMV sur les poids décodés ;
- `débord = max(0, A − V)` : la part des toujours-lus qui ne tient pas en VRAM.

Pour une architecture où la carte calcule tout et décode à l'arrivée (l'architecture B de l'étude
01, devenue A ici) :

    T_disque = h_s · R / (r_d · D_disque)
    T_pcie   = (h_r · R / r_p + h_s · R / r_d + débord) / D_pcie
    T_carte  = (1 − h_v) · R / D_dec + (A + R) / D_g

Les deux termes de `T_carte` s'additionnent : le décodeur et la GEMV se partagent les mêmes
multiprocesseurs. Le disque et la PCIe se recouvrent avec la carte (moteurs de copie libres : part
cachée 0,98 à 1,01 [mes. 04]).

Le succès du cache suit un modèle à une constante, `h(c) = c^β`, où `c` est la part des octets
d'experts qu'un étage contient. `β = 1` est le routage uniforme (le pire cas, celui de 06).
`β = ln 0,659 / ln 0,134 = 0,207` cale le seul point publié d'un LRU sur un MoE fin (65,9 % de
succès à 13,4 % du budget, Qwen3-30B-A3B, une couche) ; `β = 0,117` cale Belady au même point
(79,1 %) [calc. sur litt. 04]. Deux étages : `h_v = h(c_v)`, `h_v + h_r = h(c_v + c_r)`. Le point
« succès impliqué » de moe-stream (au moins 53 % à 31 % du budget [calc. 04]) est compatible avec le
scénario LRU (0,31^0,207 = 0,78). **Ce modèle est une hypothèse dite, pas une loi** : il suppose que
la forme de la courbe de Qwen3-30B (128 experts, 8 actifs) vaut pour gpt-oss-120b (128 experts,
4 actifs), et il extrapole un point unique.

### 1.3 Les chiffres de la machine

| Grandeur | Valeur | Étiquette | Journal |
|---|---|---|---|
| Disque, lecture de 16 Mio, QD 1 | 2,82 Go/s | [mes. 01] | `01-machine/debits-mesures.json` |
| Disque, lecture de 4 Mio, QD 4 (la taille d'une matrice d'expert) | **2,58 Go/s** (retenu pour les experts) | [mes. 01] | `01-machine/disque-analyse.md` |
| Disque, 4 Kio aléatoire (fautes de page) | 0,22 Go/s, p50 200 µs en QD 1 | [mes. 01] | idem |
| Disque, annonce Samsung | 6,0 Go/s | [litt. 01] | |
| Lien du disque, PCIe 4.0 ×4 | 7,877 Go/s | [calc. 01] | |
| PCIe hôte → carte, DMA depuis la RAM épinglée, au calme | **12,2 Go/s** | [mes. 01] | `carte-complement.jsonl` |
| PCIe, copies seules (lien redescendu en Gen 3) | 6,38 Go/s | [mes. 04] | `pcie-1.json` |
| GEMV dont les poids restent en RAM hôte (zéro copie) | 11,75 Go/s | [mes. 01] | `carte.jsonl` |
| Lecture de VRAM par un shader | 251,3 Go/s | [mes. 01] | |
| GEMV MXFP4 brute, Vulkan | **209,4 Go/s** équivalents | [mes. 03] | `gemv-gptoss20b-secteur.json` |
| Décodeur rANS v4, Vulkan, sur secteur | **70 Go/s** de codes produits (CUDA : 81-82) | [mes. 03] | `rans-gptoss20b-secteur.json` |
| Décodage puis réassemblage des trois flux de classe | 41,6 Go/s | [mes. 03] | `dispersion-classes-secteur.json` |
| Calcul Vulkan f32 / f16 | 12,6 / 13,4 Tflop/s | [mes. 01] | |
| RAM, un seul module DDR5-5200 | plafond 41,6 Go/s ; 15,6 Go/s lus par un fil, machine chargée | [calc. 01] ; [mes. 01] | `memoire.log` |
| Déchiffrement XTS-AES de BitLocker | 3,2 à 4,2 Go/s par fil (batterie), soit 0,25 à 0,3 s de cœur par Go lu | [mes. 01] | `aes-xts-batterie.log` |
| VRAM et RAM utiles pour des poids | 6,5 Go et 11 Go | hypothèses dites [06] | |
| Coût fixe d'un jeton `t0` | 3,5 ms | [calc. sur mes. 02] | |

Deux mises en garde reprises des études et gardées dans tout ce qui suit :
- **Machine partagée** : toutes les mesures ont tourné avec d'autres agents ; les débits « au mieux »
  sont des bornes inférieures du repos [01].
- **Batterie** : sur batterie, la carte passe à 52,6 W, sa mémoire à 6 GHz, la PCIe en Gen 3, et tout
  ce qui passe par le processeur perd un facteur 4 à 6 ; la DMA tient à 11,8 Go/s, le décodeur à
  26,8 Go/s [mes. 01, 03]. Les chiffres de ce document sont ceux du secteur.

### 1.4 Le modèle cible, lu par un second chemin

`inventaire_gptoss.py` lit l'en-tête des deux fichiers GGUF présents sur la machine (lecteur de
l'étude 03, écrit de zéro). Témoin : la fin du dernier tenseur tombe exactement sur la taille du
fichier (63 387 346 208 octets pour le 120b) ; forcé à faux (un tenseur fictif de 4 Kio), il tombe
sur les deux fichiers (`inventaire-gptoss-casse.json`) [mes.].

| | gpt-oss-20b | gpt-oss-120b | Étude 06 (en-tête distant) |
|---|---|---|---|
| Couches, experts par couche, actifs | 24, 32, 4 | 36, 128, 4 | 36, 128, 4 |
| A, toujours lus (Q8_0 et F32) | 1,302 Go | **1,686 Go** | 1,69 Go |
| R, experts lus par jeton | 1,272 Go | **1,909 Go** | 1,91 Go |
| Tous les experts | 10,18 Go | 61,07 Go | 61,1 Go |
| Un expert (3 matrices + biais) | 13,25 Mo | 13,25 Mo | 13,2 Mo [04] |
| **Une matrice d'un expert, d'un seul tenant** | 4 406 400 o | 4 406 400 o | — |
| Table d'enchâssement (une ligne lue par jeton) | 0,615 Go | 0,615 Go | — |

Ce que le second chemin ajoute : dans ces fichiers, l'expert est la dimension la plus lente de chaque
tenseur, donc **chaque matrice d'un expert est un bloc contigu de 4,2 Mio**. Le problème des
6 912 pages par expert relevé pour d'autres GGUF (llama.cpp #27149 [litt. 04]) ne se pose pas ici :
un défaut coûte trois lectures de 4,2 Mio, la taille exacte où le disque donne 2,3 à 2,6 Go/s
[mes. 01]. Il n'est pas nécessaire de réécrire le fichier pour lire un expert d'un seul tenant ; on
le réécrit seulement pour le coder.

### 1.5 Le terme qui manque à la spéculation sur un MoE

L'étude 05 a montré que, pour un MoE à experts fins dont les experts viennent du disque, la passe de
vérification de `n` jetons lit l'union de leurs experts, et que la spéculation paie si et seulement
si `E(α, k) > U(k+1) / t` [calc. 05]. Sous l'indépendance, `U(2) / t = 2 − t/E`, d'où la condition
`α > 1 − t/E = 0,969` pour gpt-oss-120b. Mais la réutilisation réelle n'est pas nulle : si une part
`ρ` des experts du jeton suivant est déjà dans l'ensemble du jeton courant, `U(2) = t (2 − ρ)` et

    E(α, 1) = 1 + α > 2 − ρ   ⇔   α > 1 − ρ

[calc.]. Avec les réutilisations publiées, la condition devient : `α > 0,556` pour Qwen3-30B-A3B
(ρ = 0,444), `α > 0,75` pour Qwen3.6-35B-A3B (ρ ≈ un quart) [calc. sur litt. 04]. **La conclusion
« k optimal = 0 » de l'étude 05 dépend donc d'un nombre que personne ne publie pour le modèle visé.**
La même trace de routage qui donne `h(c)` donne ρ.

### 1.6 Les témoins de l'équation

`plafonds.py` refait trois chiffres publiés par d'autres études, seuil déclaré avant : 1 % sur
chaque valeur (`plafonds.json`) [calc.] :

| Témoin | Attendu | Obtenu | Tient |
|---|---|---|---|
| T1 : gpt-oss-120b, placement de l'étude 01 (§ 7.3), r = 1, recouvert | 1,98 | 1,994 | oui |
| T2 : Qwen3.5-9B tout sur le disque, r = 16, carte qui décode (étude 01) | 8,85 | 8,847 | oui |
| T3 : le placement de T1 au débit du lien (7,877 Go/s), le chiffre de l'étude 06 | 5,6 | 5,569 | oui |

Cassure : `--casser` remplace le débit mesuré du disque par celui du lien ; T1 tombe (5,569 au lieu
de 1,98), les deux autres tiennent (`plafonds-casse.json`). L'étude 01 avait écrit « 5,5 » pour
1 / 0,18 = 5,56 ; je garde l'attendu publié par 06 (5,6), le seul qui ne soit pas un arrondi.

Un écart avec l'étude 03 à signaler : elle chiffre à +14,4 % l'effet du taux sans perte (1,1026)
sur le cache, en supposant **tout** le cache codé, VRAM comprise. Or sa propre mesure (§ 4.5 : le
produit fondu au décodeur est 3,7 fois plus lent) dit que la carte doit garder ses experts décodés.
Seule la RAM grandit alors : **+13,1 %** [calc., `gain_taux_sur_cache_uniforme`].

### 1.7 Ce qui tient le maximum, et ce que coûte d'ignorer chaque terme

Pour gpt-oss-120b, architecture A, scénario LRU calé [calc.] : `T_disque` 157 ms, `T_pcie` 58 ms,
`T_carte` 36 ms. Le disque tient le maximum avec une marge de 2,7 sur la PCIe. Tant qu'il le tient,
le plafond vaut

    jetons/s ≈ r_d · D_disque / (h_s · R)

ce qui donne l'élasticité de chaque grandeur :

| Grandeur | Élasticité du plafond | Ce que vaut 10 % gagné | Remarque |
|---|---|---|---|
| `D_disque` | +1 | +10 % | BitLocker et VMD en prennent 53 % [mes. 01] |
| `r_d` (compression des octets lus) | +1 | +10 % | sans perte : 1,10 atteint [mes. 03] ; avec perte : la quantification |
| `R` (bits par poids actif) | −1 | +11 % | 02 : la pente la plus forte de la quantification |
| `h_s` (part lue du disque) | −1 | +11 % | à h = 0,77, un point de succès gagné vaut +4,5 % |
| `D_pcie`, `D_dec`, `D_g` | 0 | 0 | tant qu'ils ne tiennent pas le maximum |
| `t0` | ≈ 0,02 | 0,2 % | 3,5 ms sur 160 |

**Conséquence** : tout le travail sur la vitesse des noyaux en VRAM (le trou 5 de l'étude 01, le
régime résident de l'étude 03) rapporte moins de 2 % tant que le disque tient le maximum. C'est une
idée tuée par le nombre, pour ce régime ; elle redevient utile quand le disque ne limite plus (§ 4.2,
disque non chiffré : la PCIe reprend la main).

---

## 2. La carte de ce qui existe

Chaque technique est placée sur le terme de l'équation où elle agit. Les chiffres sont ceux des
études ; les licences ont été vérifiées par elles dans les fichiers des dépôts.

### 2.1 Sur `R` : moins de bits par poids actif (étude 02)

| Technique | Mécanisme en une ligne | Effet chiffré | Coût | Sans CUDA ? | Maturité | Licence |
|---|---|---|---|---|---|---|
| K-quants, i-quants de llama.cpp | blocs de 32 à 256, échelles 4 à 8 bits ; i-quants : VQ sur grilles E8 | Qwen3.5-9B : IQ3_XXS 3,49 Go/jeton, PPL +10 % ; IQ2_XXS 2,76 Go, +48 % [mes. 02] | minutes à heures, processeur | **oui, Vulkan** | production | MIT |
| Treillis à décalage (QTIP, EXL3) | Viterbi sur un état de 16 bits, code calculé (mul1) | MSE 0,068 à 2 bits contre 0,107 pour IQ2_XXS, soit 0,23 à 0,33 bit [mes. 02] | heures de carte | décodeur WGSL écrit ici, **124 Go/s** [mes. 02] ; codeur absent | recherche ; EXL3 en production sous CUDA | GPL-3.0 ; MIT |
| CurveTQ (2026-10), Tetra (2026-09) | treillis sans rotation ; réseau de Leech | Qwen3-32B +12 % PPL à 2,29 bits ; Qwen3-8B Tetra bat Qwen3-4B AWQ à octets égaux [litt. 02] | heures de carte | non | recherche | — ; Apache-2.0 |
| GSQ (2026) | affectations Gumbel-Softmax projetées dans les K-quants | Q2_K de Qwen3-8B 50,0 → 56,3 de moyenne [litt. 02] | heures de carte, PyTorch CUDA | **oui au décodage** (même format) | recherche | Apache-2.0 |
| Codes emboîtés (ApexQuant, MatGPTQ, Drop-by-Drop, AnyBCQ) | chaque préfixe des passes est un modèle valide | 0,10 bit par passe en treillis [litt. 02] ; « sans pénalité » pour une gaussienne sous MSE pondérée [litt., arXiv 2606.12876, résumé] | ajustement ou PTQ | non | recherche | non déclarée ; — |
| Formats natifs 4 bits (MXFP4, NVFP4, INT4 QAT) | entraînés ou ajustés en 4 bits | gpt-oss, Kimi K2.6/K3, DeepSeek V4 : la référence est déjà à 4,25 bits [mes. 06] | — | décodés dans le shader | production | selon le modèle |
| Règle des 2,6 bits (02, D6) | bits alloués selon le débit de l'étage qui sert la matrice | une matrice résidente mérite ½ log₂(256/7) ≈ 2,6 bits de plus [calc. 02] | — | — | **n'existe pas** | — |

### 2.2 Sur `r` : compression sans perte des octets transportés (étude 03)

| Technique | Mécanisme | Effet chiffré | Coût | Sans CUDA ? | Maturité | Licence |
|---|---|---|---|---|---|---|
| **rANS de troncons, codage par champs** | codes en rANS, échelles E8M0 en écart à la médiane de ligne, 3 classes | gpt-oss-120b : **r = 1,1026**, décodé exactement [mes. 03] | décodeur 70 Go/s, 3,6 % du temps de la carte | **oui, Vulkan** | prototype mesuré | à nous |
| zstd, lz4 | LZ + entropie d'octets | MXFP4 : 1,0405 et 1,000 ; K-quants : 1,012 et 1,000 [mes. 03] | processeur : 0,46 Go/s par fil (zstd) | oui (processeur) | mûr | BSD |
| GDeflate, zstd de DirectStorage 1.4 | DEFLATE en 32 sous-flux, décodé sur la carte | borné par le codage d'octets du bloc : ≤ 1,018 sur K-quants [calc. 03] | préversion 1.4 du 2026-03-11 | **oui, DX12** | préversion | MIT, Apache-2.0 |
| DFloat11, ZipNN, ZipServ, ECF8 | exposants BF16 ou FP8 codés | 10,8 bits pour 16 [litt. 03] | — | non (sauf ZipNN processeur) | publiés | Apache-2.0, MIT |
| EntQuant, vram-compression | quantification taillée pour le codeur, puis ANS | LLaMA-2 70B à 2,1 bits ; « 1 bit gagné à qualité presque égale » sur Qwen2.5-1.5B [litt. 03] | 1,5 à 3 fois plus lent que BF16 | non (nvCOMP, CUDA) | article ; prototype | Apache-2.0 ; aucune licence |
| ECSQ mesuré ici | pas uniforme + codage entropique | 0,41 à 0,46 bit de moins que Q4_K à erreur égale [mes. 03, sur substituts] | — | décodable par la v4 | mesure | — |

### 2.3 Sur `h` : ce qui garde les octets près de la carte (études 04 et 06)

| Technique | Mécanisme | Effet chiffré | Sans CUDA ? | Maturité | Licence |
|---|---|---|---|---|---|
| Cache LRU / LFU / statique | évince l'expert le moins récent / fréquent | 65,9 / 60,1 / 59,2 % à 13,4 % du budget (Belady 79,1) [litt. 04] | oui | partout | — |
| SLRU + filtre d'admission | segments probatoire et protégé | +8 à 15 points sur LRU pour GPT-OSS-120B [litt. 04, communautaire] | oui | discussion llama.cpp #20757 | MIT |
| Remplacement appris (FlashMoE), « least-stale » (SpecMD) | récence + fréquence ; ordre des couches | +51 % de succès sur LRU ; 88-92 % à 1 % de capacité [litt. 04] | — | recherche | — |
| Routage conscient du cache (Skliar et al.) | favorise les experts présents | défauts DeepSeek-V2 28 → 7 %, PPL +0,1 à 3 % [litt. 04] | oui | TMLR 2025 | — |
| Cache par tranches de bits (SliceMoE) | précision assignée à la demande, troncature compatible | latence ×1,64 à ×1,81, énergie ÷2,4 à ÷2,9 [litt., arXiv 2512.12990, résumé] | — | recherche | — |
| `--moe-cache-mib` de llama.cpp | cache VRAM des experts gardés en RAM | non chiffré [04] | oui | **expérimental** | MIT |
| Lecture paresseuse des tables (Engram, n-grammes) | une ligne lue par jeton, sur le disque | ≈ 64 Kio par jeton pour Qwen3.8 [calc. 06] | oui | llama.cpp | MIT |
| Routage par hachage (DeepSeek V4) | experts connus dès le tirage du jeton | ≈ 7 % des octets d'experts connus une passe d'avance [calc. 06] | — | **inexploité** | MIT |

### 2.4 Sur `t_lat` : cacher la latence (études 04 et 05)

| Technique | Ce qu'elle gagne | Chiffre | Sans CUDA ? |
|---|---|---|---|
| Double tampon | max au lieu de somme | ×2,09 sur des couches de 286 Mo (llama.cpp #27149) [litt. 04] | oui |
| Prédiction d'un jeton d'avance (Edge0) | temps bloqué ÷ 2,4 à 3,3 à octets presque égaux | +80 à +84 % au décodage [litt. 04] | MLX |
| Routeur ℓ+1 sur le résidu ℓ (Mixtral-offloading, HOBBIT) | 96 % juste à ℓ+1 [litt. 04] | ×1,47 avec LRU | — |
| Substitution basse précision (HOBBIT) | un défaut servi par une copie Int4 | ≤ 1 point, 30 % d'experts en basse précision sur Mixtral [litt. 04] | — |
| Report d'expert (KTransformers) | sortie ajoutée à la couche ℓ+2 | ≤ 2 points pour 6 sur 8 reportés [litt. 04] | non (AMX, Linux) |

### 2.5 Sur `E_spec` : lire moins souvent (étude 05)

| Technique | Jetons par lecture des poids | Sans CUDA ? | Remarque |
|---|---|---|---|
| Chaîne (llama.cpp : petit modèle, EAGLE-3, MTP, DFlash, n-grammes) | au plus `1/(1−α)` : 5 à α = 0,8 [calc. 05] | **oui, Vulkan** | jamais d'arbre dans `common/speculative.cpp` [lu 05] |
| Arbres (SpecExec, Sequoia) | 9,7 jetons par passe, 70B GPTQ sur RTX 4060 de bureau [litt. 05] | non | `n*` ≈ 210 jetons sur cette machine [calc. ici, § 4.3] |
| Substitut résident (SubSpec) | 27 à 35 par passe [litt. 05] | non | sur 8 Go : ×2,5 pour une cible 14B [calc. 05] |
| Spéculation bornée aux experts présents (AcceptMoE) | ×2,06, −0,27 point [litt. 05] | — | avec perte |
| Sparsité des activations (TEAL, CATS) | union de 4 jetons = 89,5 % des poids à 50 % [mes. 05] | non | tuée par la vérification |

### 2.6 Sur `D` : le chemin des octets (études 01 et 04)

| Technique | Effet sur cette machine | Statut |
|---|---|---|
| Lectures sans tampon par IOCP ou IoRing, à la taille d'un expert | 2,3 à 2,8 Go/s ; IoRing = IOCP (écart 0 à 5 %) [mes. 01] | disponible |
| Fautes de page (mmap) | 0,22 Go/s à 4 Kio, ×11 à ×14 de moins [mes. 01] | ce que fait la base |
| BypassIO | **refusé** : BitLocker (fvevol) et pilote iaStor [mes. 01] | geste de Stone (volume non chiffré) |
| DirectStorage 1.4 | disque → ressource D3D12 avec GDeflate / zstd sur la carte ; aucun moteur d'inférence ne s'en sert [litt. 04] | SDK de 3,99 Mo, non mesuré |
| Mémoire épinglée | +21 % sur la mémoire paginable [mes. 04] | disponible |
| Garder le lien en Gen 4 | 12,2 Go/s si la carte calcule pendant la copie, 6,38 si elle ne fait que copier [mes. 01, 04] | règle d'ordonnancement |
| Zéro copie (GEMV sur la RAM hôte) | 11,75 Go/s, sans tampon de transit [mes. 01] | disponible |

### 2.7 Les moteurs complets

| Moteur | Ce qu'il réunit | Windows sans CUDA | Chiffre publié |
|---|---|---|---|
| llama.cpp (b11515) | mmap, `-ncmoe`, `--moe-cache-mib`, Vulkan, spéculation en chaîne | **oui** | base de troncons, non mesurée sur gpt-oss-120b |
| PR llama.cpp #25294 | experts lus sur le disque, cache d'emplacements | non (pread, O_DIRECT) | GLM-5.2 : 2,20 jetons/s à 79 % de succès, GB10 [litt. 04] |
| SSD-LLaMA | SSD, RAM, VRAM en hiérarchie, compression des experts | non (io_uring) | DeepSeek-V4-Flash 6,72 jetons/s, RTX 5090, PCIe 5.0 [litt. 04] |
| Edge0 | prérouteur d'un jeton d'avance | non (MLX) | Qwen3.6-35B-A3B 20,4 jetons/s en 2,9 Gio, top-k réduit à 4 [litt. 04] |
| moe-stream | cache explicite, une lecture par expert | **oui**, processeur seul | Qwen3.6-35B-A3B 5,05 jetons/s avec 6 Go [litt. 04] |
| KTransformers | experts sur le processeur (AMX), report | non | — |

**Lecture d'ensemble.** Chaque terme de l'équation a ses techniques ; aucune n'est absente du monde.
Ce qui est absent, c'est leur assemblage sur cette classe de machine : disque chiffré à 2,6 Go/s, RAM
à un canal, carte de 8 Go, Windows, sans CUDA. La section suivante chiffre ce qui manque.

---

## 3. Ce qui manque dans le monde

Chaque trou est chiffré par `plafonds.py` sur gpt-oss-120b, ou par la mesure d'une étude. Je sépare
**l'ingénierie** (assembler ce qui existe, sur une machine Windows grand public sans CUDA) de **la
recherche** (un mécanisme neuf, dont le résultat n'est pas connu d'avance).

### 3.1 Ingénierie

**I1. La chaîne complète, sous Vulkan, sous Windows.** Disque (lecture explicite de 4 Mio) → RAM
épinglée (cache tiède, octets codés) → PCIe en octets codés → décodage rANS à l'arrivée → cache
d'experts décodés en VRAM → GEMV MXFP4. Chaque maillon est mesuré sur la machine (2,58 ; 12,2 ; 70 ;
209 Go/s) ; leur assemblage n'existe dans aucun moteur publié (SSD-LLaMA, la PR #25294, Edge0 et
KTransformers sont sous Linux ou macOS ; moe-stream tourne sous Windows sur le processeur seul ;
DirectStorage n'est utilisé par aucun moteur d'inférence [04]).
*Chiffre* : plafond de A **2,05 / 6,24 / 10,3 jetons/s** selon la localité, contre une base
llama.cpp estimée à **0,14–0,81 / 0,37–1,87 / 0,59–2,66** [calc.], soit **×2,5 à ×17**. L'estimation
de la base suppose des experts calculés par le processeur à 15,6 Go/s depuis 11 Go de cache de pages
et des défauts lus entre 0,22 et 1,31 Go/s, sans recouvrement : elle est à mesurer (§ 5), et c'est la
première mesure qui peut tuer A.

**I2. Lire à la taille d'un expert.** Le disque donne 0,22 Go/s à 4 Kio, 1,31 Go/s à 1 Mio en QD 1
et 2,58 Go/s à 4 Mio en QD 4 [mes. 01] : un moteur qui lit par fautes de page de 4 Kio perd ×12,
par morceaux de 1 Mio ×2. Pour gpt-oss, rien
n'est à réécrire : chaque matrice d'expert est déjà un bloc de 4,2 Mio (§ 1.4).

**I3. Tenir le lien en Gen 4.** Une copie seule laisse le lien en Gen 3 (6,38 Go/s), une copie
pendant un calcul le tient en Gen 4 (12,2) [mes. 01, 04] : ×1,9 sur la PCIe. Sans effet tant que le
disque limite (élasticité nulle, § 1.7) ; décisif dès qu'il ne limite plus (§ 4.2 : avec un disque
non chiffré, la PCIe tient le maximum de B).

**I4. La mesure de `h(c)` et de ρ sur le modèle visé.** L'instrument existe et ses témoins
synthétiques tombent quand il faut (`chargement_localite.py` [04]) ; il manque une trace de routage
de gpt-oss-120b sur un texte réel. Elle demande un llama.cpp compilé avec un rappel d'évaluation
(CUDA 13.1.2 et MSVC sont sur la machine) et **aucun téléchargement**. *Chiffre* : l'écart entre les
scénarios uniforme et LRU calé vaut **×3,0** sur le plafond de A (2,05 contre 6,24), et entre LRU et
Belady ×1,66 : c'est l'incertitude la plus grande de tout le projet.

**I5. Le régime batterie, chiffré.** Un chargeur qui ne fait que de la DMA et décode sur la carte
perd peu sur batterie (DMA 11,8 Go/s ; décodeur 26,8 Go/s, encore 10 fois le disque) ; un chargeur qui
copie ou décode par le processeur perd ×4 à ×6 [mes. 01, 03]. Aucun banc d'inférence publié ne note
la source d'alimentation. Le disque sur batterie n'est pas mesuré (BitLocker y déchiffre avec un
processeur à 1,5 GHz) : à mesurer.

**I6. La vérification en arbre dans un moteur portable.** llama.cpp ne vérifie que des chaînes : au
plus 5 jetons par lecture à α = 0,8, contre 9,7 mesurés par SpecExec sur une RTX 4060 [litt. 05].
*Chiffre* (architecture C, IQ3_XXS) : 1,29 jeton/s à la borne d'une chaîne contre 2,50 avec l'arbre
[calc.], ×1,9.

**I7. Les octets connus d'avance, inexploités.** Le routage par hachage de DeepSeek V4 (≈ 7 % des
octets d'experts connus dès le tirage du jeton) et les tables à recherche (Engram, n-grammes : 26 à
45 % des paramètres, ≈ 64 Kio lus par jeton) [06]. Le gain en débit est petit (≤ 7 %) ; le gain en
latence ne se voit pas dans le juge par débits.

**I8. Ce que coûte BitLocker à un flux de poids** : 0,25 à 0,3 s de cœur par Go [mes. 01], soit
≈ 0,6 à 0,8 cœur pour les 2,5 Go/s de défauts que lit A à son plafond (6,24 jetons/s × 0,405 Go,
LRU calé). Supportable pour A, qui ne demande rien d'autre au processeur ; rédhibitoire pour un chemin qui décoderait sur le processeur
(0,075 Go/s par fil en scalaire [mes. 03]).

### 3.2 Recherche

**R1. Le raffinement exact d'un format 4 bits natif, lié à l'étage** (le mécanisme de B, § 4.2).
- *Ce qui existe* : les codes emboîtés avec perte (ApexQuant, MatGPTQ, Drop-by-Drop, AnyBCQ) ; le
  cache par tranches de bits par troncature (SliceMoE, sur DeepSeek-V2-Lite et Qwen1.5-MoE, résumé
  lu) ; les plans de bits codés sans perte et lus selon la précision voulue, dans un contrôleur CXL
  matériel (TRACE, résumé lu ; il modélise gpt-oss-120b MXFP4 mais pour le cache KV) ; la
  substitution par une copie basse précision **séparée** (HOBBIT, qui stocke deux copies).
- *Le terme qui leur manque* : une base qui soit une **fonction** du code d'origine (donc une
  somme base + complément égale, en débit, au codage sans perte d'un seul tenant), choisie pour sa
  distorsion et non par troncature, codée par entropie, lue seule au défaut depuis le disque, et
  complétée quand l'expert entre au cache.
- *Mesuré ici* (§ 4.2) : la meilleure base à 4 classes coûte 2,64 bits pour 4,29 % d'erreur ; la
  troncature 2,91 bits pour 4,47 %. **La troncature perd 0,27 bit par poids à erreur égale** sur
  E2M1 : les niveaux du format ne sont pas uniformes, et la troncature des bits de poids faible
  regroupe mal les magnitudes.
- *Chiffre* : à localité égale, les défauts lisent 2,68 bits au lieu de 3,85, soit **×1,44** sur
  l'étage disque et ~~**×1,42** sur le plafond (B1 : 8,88 contre 6,24 jetons/s, LRU calé) ; **×1,75**
  si la RAM ne garde que la base (B2 : 10,9)~~ (barré par l'arbitre le 2026-10-15 : les octets des compléments n'étaient pas comptés ; comptés, B1 plafonne à 6,16 jetons/s, série 4,83, et le gain de débit de B passe à B3, 10,89 à 48,5 % d'usages servis par la base ; second chemin : `decisions/journaux/arbitre/verif-plafonds.json`, décision : `decisions/ARCHITECTURE.md` § 1.3). *Inconnu* : ce que coûtent en qualité 23 % (B1) à 41 %
  (B2) des usages d'experts servis à 4,3 % d'erreur. C'est la mesure qui décide de B.

**R2. L'allocation conjointe (bits, étage).** La règle des 2,6 bits de l'étude 02 (une matrice
résidente mérite ½ log₂(D_vram / D_flux) bits de plus) n'est appliquée par aucun outil ; Q-Palette
alloue sous budget de latence profilée mais à placement fixe [litt. 02]. Avec les débits de cette
machine, le rapport n'est plus 256 / 7 mais 209 / 2,58 : ½ log₂(81) = **3,2 bits** [calc.]. Le
raffinement exact (R1) en est la forme dynamique : un expert qui monte en VRAM gagne son complément
sans requantifier.

**R3. Une politique de défaut sous budget de qualité déclaré.** Attendre, reporter d'une couche,
servir la base (R1), re-router vers un expert présent : personne ne les réunit, défaut par défaut,
selon le score de routage de l'expert manquant [04]. Avec R1, la substitution ne coûte **aucun
stockage** (la base est le premier flux du même fichier), là où HOBBIT garde une seconde copie.
*Chiffre* : le gain vit dans `t_lat`, entre le plancher en série et le plafond (A, LRU : 3,93 → 6,24
jetons/s, ×1,59) ; le juge par débits ne le voit pas, une mesure sur le moteur le verra.

**R4. La spéculation sous réutilisation réelle des experts.** Condition `α > 1 − ρ` (§ 1.5). Si ρ
vaut 0,44 comme sur Qwen3-30B, un brouillon à α = 0,8 rend 1,8 jeton pour 1,56 fois les experts d'un
jeton : +16 % de débit là où l'étude 05 concluait à une perte [calc.]. *Inconnu* : ρ pour gpt-oss-120b
et pour les MoE de 2026, et sa décroissance avec `n`.

**R5. Un code à 2 bits de deuxième génération décodable en Vulkan** (treillis : décodeur écrit et
mesuré à 124 Go/s, codeur absent [02]). Pour gpt-oss, dont les experts sont nés en 4 bits, il ne
sert qu'à requantifier sous 4 bits, ce que personne ne publie : les GGUF « Q2_K » de gpt-oss-120b
gardent leurs experts en MXFP4 (62,6 Go [mes. 06]). *Chiffre* : R divisé par 1,9 (4,25 → 2,25 bits),
plafond ×1,9 à localité égale, qualité inconnue sur un modèle entraîné en 4 bits.

**R6. Les arbres de vérification pour les hybrides à règle delta** (Qwen3.5 à 3.8) : 48 Mio d'état par
nœud gardé, 12 Gio pour 256 nœuds [calc. 05]. Hors du chemin de A et B (gpt-oss est un transformeur
classique) ; il bloque C sur les modèles Qwen.

**R7. Un code à décodage en temps constant pour le régime résident.** Le décodeur entropique va
3,7 fois moins vite que la GEMV brute en VRAM [mes. 03] ; il manque un code de la famille de ZipServ
qui garde une part du gain. *Chiffre* : au mieux +10 % de capacité de la VRAM (le taux sans perte) à
vitesse égale, soit `c_v` de 0,079 à 0,087, `h_v` de 0,590 à 0,602 et `h_s` de 0,234 à 0,229 (LRU
calé) : +2 % de plafond [calc.]. Basse priorité.

### 3.3 Ce que les nombres tuent

| Idée | Le nombre qui la tue | Étude |
|---|---|---|
| Décoder dans le produit (fusion rANS + GEMV) | 3,7 fois plus lent que le brut, pas plus rapide que deux passes | 03 [mes.] |
| Treillis « sans multiplication » sur la carte | 52 contre 121 Go/s ; les comptages de bits coûtent plus que la multiplication | 02 [mes.] |
| Décoder sur le processeur | 0,075 Go/s par fil ; 6 cœurs AVX-512 ne feraient que ≈ 4 Go/s | 03 [mes., calc.] |
| Sparsité des activations sous vérification | union de 4 jetons : 89,5 % des poids ; masque commun : PPL ×17 | 05 [mes.] |
| Spéculation sur un MoE fin sous l'indépendance | il faudrait α > 0,969 (gpt-oss-120b) | 05 [calc.] ; nuancé par § 1.5 |
| DX12 par wgpu | ni f16 ni sous-groupes ; q4 à 32 Go/s | 01 [mes.] |
| IoRing au lieu d'IOCP | écart 0 à 5 %, sous le bruit | 01 [mes.] |
| Noyaux VRAM plus rapides, en régime disque | élasticité nulle, < 2 % | ici [calc.] |
| Calcul des experts tièdes par le processeur | la PCIe (58 ms) ne tient pas le maximum (disque 157 ms) : aider la PCIe ne rapporte rien ; et le processeur lit la RAM à 15,6 Go/s au mieux, chargé | ici [calc.] |
| Couche de base à 1 bit de magnitude (signe + 1 bit) | 16,4 % d'erreur relative, 12 fois le bruit propre du format | ici [mes.] |

---

## 4. Trois architectures candidates

Elles partagent le juge (06 § 7) et la machine. Elles s'opposent par l'angle : **A** réduit les
octets sans rien perdre et compte sur la carte seule ; **B** échange de la précision, là seulement où
l'octet est cher ; **C** amortit une lecture sur plusieurs jetons au lieu de lire moins.

### 4.1 A — Tout par la carte, octets codés de bout en bout, sans perte

**Modèle** : gpt-oss-120b MXFP4 (sur la machine, empreinte vérifiée). Jumeau de développement :
gpt-oss-20b (12,1 Go, plus gros que la VRAM lui aussi).

**Le chemin des octets**

```
  disque (C:, BitLocker)          RAM épinglée (fenêtre bornée M)        PCIe 4.0 x8            VRAM 8 Go                  calcul
 ┌──────────────────────┐  IOCP  ┌──────────────────────────────┐  DMA  ┌──────┐   ┌───────────────────────────┐   ┌──────────────┐
 │ experts codés (rANS, │ 4 Mio  │ tampons d'arrivée (2 x défauts│ codés │12,2  │──►│ décodeur rANS v4 (70 Go/s)│──►│ GEMV MXFP4   │
 │ 3 classes, r=1,1026) │──────► │ d'un jeton) + cache tiède codé│──────►│ Go/s │   │ ─► cache d'experts décodés│   │ brute 209    │
 │ 1 matrice = 1 bloc   │ 2,58   │ (M Go, LRU/SLRU)              │       └──────┘   │ (4,8 Go, 362 experts)     │   │ Go/s, Vulkan │
 └──────────────────────┘ Go/s   └──────────────────────────────┘                   │ + A résident (1,69 Go)    │   └──────────────┘
                                                                                    └───────────────────────────┘
 le processeur : lit le disque, tient les files ; ne décode rien, ne calcule aucun expert
```

**Le chronogramme d'un jeton** (couche ℓ ; la file du disque reçoit, pendant la couche ℓ, les
défauts prédits pour ℓ+1 par le routeur de ℓ+1 appliqué au résidu de ℓ, 96 % juste à une couche
d'avance [litt. 04], et ceux du jeton suivant dès qu'ils sont connus) :

```
 carte   : |attn ℓ|rout ℓ|déc. défauts ℓ|GEMV experts ℓ|attn ℓ+1|rout ℓ+1|déc.|GEMV|...
 PCIe    :        |==== défauts ℓ+1 (codés) ====|          |==== défauts ℓ+2 ====|
 disque  : |========= défauts ℓ+1 =========|========= défauts ℓ+2 =========|=====...   (toujours occupé)
 temps   : ~1 ms de carte par couche ; ~4,4 ms de disque par couche en moyenne (0,94 défaut x 3 matrices)
```

Le disque est occupé en permanence ; la carte attend le disque. Le plafond suppose que la file ne se
vide jamais (préchargement juste) ; le plancher, qu'aucune lecture n'est lancée avant que le routeur
de sa couche n'ait parlé.

**Plafond** (`plafonds.json`, débit disque 2,58 Go/s, M = 11 Go) [calc.] :

| Scénario de localité | h_v / h_r / h_s | T_disque / T_pcie / T_carte (ms) | Plafond | Plancher en série |
|---|---|---|---|---|
| uniforme (β = 1) | 0,079 / 0,199 / 0,723 | 485 / 131 / 59 | 2,05 | 1,47 |
| LRU calé (β = 0,207) | 0,590 / 0,176 / 0,234 | 157 / 58 / 36 | **6,24** | 3,93 |
| Belady calé (β = 0,117) | 0,744 / 0,118 / 0,139 | 93 / 36 / 29 | 10,34 | 6,17 |
| *pour comparaison : même chemin sans codage (r = 1)* | | | 1,81 / 5,42 / 8,98 | |

**La fenêtre de travail** (la lecture de « sans ram ni rien » posée par le SOCLE : la mémoire occupée
ne dépend plus de la taille du modèle, seulement d'une fenêtre bornée). Le budget de RAM `M` est un
réglage, pas une conséquence du modèle [calc., `plafond-gptoss120b-contre-ram.csv`] :

| Cache tiède en RAM (Go) | 0 | 1 | 2 | 4 | 6 | 8 | 11 |
|---|---|---|---|---|---|---|---|
| RAM de pointe (Go) | **1,9** | 2,8 | 3,8 | 5,6 | 7,5 | 9,4 | 12,3 |
| Plafond, LRU calé (jetons/s) | **3,59** | 3,83 | 4,06 | 4,52 | 4,99 | 5,47 | 6,24 |
| Plafond, uniforme | 1,61 | 1,64 | 1,67 | 1,74 | 1,82 | 1,91 | 2,05 |
| Plafond, Belady calé | 5,70 | 6,12 | 6,53 | 7,34 | 8,15 | 9,00 | 10,34 |

**A0** est la première colonne : un modèle de 63,4 Go servi avec **1,9 Go de RAM de pointe** et la
VRAM de la carte, à 3,6 jetons/s de plafond dans le scénario LRU. C'est la réponse chiffrée à
« sans ram » : la RAM ne disparaît pas, elle cesse de dépendre du modèle. Chaque Go de cache tiède
ajoute ≈ 0,24 jeton/s dans ce scénario.

**Mémoire de pointe** : VRAM ≈ 7,5 Go (A 1,69 + cache d'experts 4,8 + cache KV, activations et
tampons de décodage ≈ 1) ; RAM de 1,9 à 12,3 Go selon `M`. L'écran passe par la carte intégrée, donc
les 8 188 Mio de la carte sont disponibles ; l'hypothèse de 6,5 Go pour les poids est prudente
(+0,8 Go de VRAM vaudrait `h_v` 0,590 → 0,609, +3 % [calc.]).

**Qualité attendue** : exacte par construction. Le témoin est double : (1) chaque tronçon décodé est
comparé à son empreinte (le décodeur v4 est exact au bit sur les 108 tenseurs [mes. 03]) ; (2) les
logits de A doivent être **identiques au bit** à ceux du même moteur lisant les experts non codés
depuis la RAM (même étage de calcul, même noyau). Contre llama.cpp, la comparaison se fait contre
l'écart mesuré entre deux moteurs justes (KL 0,0055, premier choix identique à 95,96 % sur
Qwen3.5-4B [mes. 06]), à remesurer sur gpt-oss.

**Ce qu'elle sacrifie** : le processeur reste presque inactif (il ne calcule aucun expert : choix
justifié au § 3.3) ; il faut écrire tout le passage avant de gpt-oss en Vulkan (attention à puits et
à fenêtre glissante une couche sur deux, RoPE YaRN, routeur, SwiGLU bornée, biais) ; la qualité ne
gagne rien, la vitesse est bornée par la localité.

**Ce qu'il faut télécharger** : **rien**.

**Deux routes pour la construire** (réponse par délégation du 2026-10-15, réversible : la première) :
1. *Un moteur à nous* (Rust, wgpu, Vulkan) pour tout le passage avant : contrôle complet de
   l'ordonnancement couche par couche (routeur → file du disque → décodage → GEMV), qui est le cœur
   de la contribution ; les briques les plus chères existent déjà (décodeur v4, GEMV MXFP4 à 209 Go/s,
   plus rapide que les 174 Go/s effectifs de llama.cpp sous CUDA sur le 9B [mes. 01, 03]). Coût :
   une quinzaine de noyaux à écrire et à témoigner.
2. *Un fournisseur d'experts dans llama.cpp* (MIT), sur le modèle de la PR #25294 : moins de noyaux,
   mais un graphe statique qui demande une synchronisation après chaque routeur, et un ordonnancement
   qu'on ne maîtrise pas. Repli si la route 1 cale.

**Les étapes, chacune avec son témoin** :
1. Trace de routage de gpt-oss-120b (I4) : `h(c)`, ρ, réutilisation ; témoin : les cas synthétiques
   de `chargement_localite.py`.
2. Base llama.cpp mesurée sur gpt-oss-120b (mmap, `-ngl 99 --cpu-moe`, puis `-ncmoe N` +
   `--moe-cache-mib`), sur secteur, ABBA.
3. Réécriture du fichier en tronçons codés (format § 4.4) ; témoin : chaque tronçon décodé égale
   l'original.
4. Lecteur IOCP de 4 Mio vers la RAM épinglée + DMA + décodeur ; témoin : le débit de bout en bout ne
   dépasse aucun étage, et les octets arrivent exacts.
5. Passage avant Vulkan sur gpt-oss-20b, experts résidents en RAM non codés ; témoin : KL contre
   llama.cpp dans l'écart entre moteurs.
6. Experts codés, cache, préchargement ; témoin : logits identiques au bit à l'étape 5.
7. gpt-oss-120b ; jetons/s, RAM et VRAM de pointe, octets lus (compteur du système), rendement
   physique (mesuré ÷ plafond).

### 4.2 B — Précision selon l'étage : raffinement exact, base seule aux défauts

**Modèle** : gpt-oss-120b, sur le format de A étendu. Ensuite Qwen3.8-Flash-Next (512 experts,
table de n-grammes), si la qualité tient.

**Le mécanisme.** Chaque code E2M1 (signe s, magnitude m parmi {0 ; 0,5 ; 1 ; 1,5 ; 2 ; 3 ; 4 ; 6})
se range en deux flux codés par rANS :
- la **base** `b = (s, classe(m))`, avec 4 classes de magnitude ;
- le **complément**, la position de `m` dans sa classe, codé avec une table par classe (le même geste
  que les trois classes d'échelle de l'étude 03).

**Proposition (raffinement exact gratuit en débit).** Si `B = f(X)` est une fonction déterministe du
code `X`, alors `H(X) = H(B) + H(X | B)`. *Démonstration* : `H(X, B) = H(X) + H(B | X) = H(X)`
puisque `H(B | X) = 0`, et `H(X, B) = H(B) + H(X | B)`. ∎ La base et le complément ensemble ne coûtent
donc, en entropie, ni plus ni moins que le codage sans perte d'un seul tenant ; le coût réel se
limite aux en-têtes d'un second flux (≈ 0,4 % de tuile [mes. 03]). C'est le cas trivial, pour une
source discrète et un sommet sans perte, du raffinement successif d'Equitz et Cover (1991) ; le
résultat continu (la gaussienne est raffinable sans pénalité sous une MSE pondérée) est démontré par
Drop-by-Drop [litt., arXiv 2606.12876, résumé]. Ce qui est neuf ici n'est pas l'identité : c'est son
emploi sur un format natif, lié à l'étage, et sa mesure.

**Mesuré ici** (`raffinement_mxfp4.py`, 12 tenseurs de gpt-oss-20b : couches 0, 8, 16, 23 ×
gate, up, down ; 3 185 049 600 poids ; `raffinement-mxfp4-gptoss20b.json`) [mes.] :

| Couche de base | Classes de magnitude | H(base) | H(complément) | Erreur relative de la base seule |
|---|---|---|---|---|
| **signe + 2 bits, meilleure partition** | {0 ; 0,5} {1 ; 1,5 ; 2} {3 ; 4} {6} | **2,642** | 1,218 | **4,29 %** |
| signe + 2 bits, troncature de la mantisse (geste Matryoshka) | {0 ; 0,5} {1 ; 1,5} {2 ; 3} {4 ; 6} | 2,907 | 0,953 | 4,47 % |
| signe + 1 bit, meilleure partition | {0 … 1,5} {2 … 6} | 1,957 | 1,903 | 16,4 % |
| signe + 1 bit, troncature | idem | 1,957 | 1,903 | 16,4 % |
| *référence : le MXFP4 sur une gaussienne* | | | | *1,33 %* |

- H(code) = 3,860 bits ; la somme base + complément l'égale à 10⁻⁹ près sur chaque ligne (témoin) ; la
  partition identité rend une erreur nulle (témoin) ; forcée à lire la mauvaise classe, elle ne la rend
  plus et le témoin tombe (`raffinement-mxfp4-gptoss20b-casse.json`).
- Les centres de classe sont les centres de gravité pondérés par le carré de l'échelle E8M0 (donc
  optimaux dans le domaine réel) : 0,237 ; 1,424 ; 3,419 ; 6,0 (unités E2M1). Le décodeur de la base
  les tient dans quatre registres : la GEMV de la base coûte celle du MXFP4.
- Par tenseur, la meilleure base à 1 bit va de 13,7 % à 17,6 % d'erreur ; elle est 12 fois le bruit
  propre du format : écartée (§ 3.3).
- Avec les échelles (0,034 bit) et les en-têtes, la base se lit à **2,684 bits par poids**, contre
  3,855 pour le sans-perte à trois classes [mes. 03] : **×1,436 de moins par défaut**.

**Deux variantes** :
- **B1** : la VRAM garde des experts exacts, la RAM des experts exacts codés ; un défaut lit la base
  seule depuis le disque et la sert ; le complément ne se lit que si l'expert entre au cache, sur le
  temps libre du disque. Part des usages d'experts servie par la base = `h_s`.
- **B2** : la RAM ne garde que des bases (1,44 fois plus d'experts tièdes) ; tout ce qui n'est pas en
  VRAM est servi par la base. Part servie par la base = `1 − h_v`.

**Plafond** (`plafonds.json`) [calc.] :

| Scénario | B1 : plafond / série / part servie par la base | B2 (base 2 bits) | B2 (base 1 bit, écartée) | A, pour comparaison |
|---|---|---|---|---|
| uniforme | 2,93 / 2,00 / 72 % | 3,33 / 92 % | 5,25 | 2,05 |
| LRU calé | ~~**8,88** / 5,09~~ 6,16 / 4,83 / **23 %** | 10,89 / 41 % (sans compléments) | 18,19 | 6,24 |
| Belady calé | 14,62 / 7,83 / 14 % | 18,04 / 26 % | 29,90 | 10,34 |

~~Le plafond de B1 suppose que les compléments des experts admis au cache tiennent dans le temps libre
du disque ;~~ Barré par l'arbitre le 2026-10-15 : au plafond, le disque est occupé en permanence et
n'a pas de temps libre ; sous LRU tout défaut entre au cache et lit son complément. Le tableau
ci-dessus est corrigé pour B1 ; les colonnes B2 restent sans compléments (voir B3, `decisions/ARCHITECTURE.md`
§ 1.3). Phrase d'origine : sinon (chaque défaut suivi de son complément), B1 lit autant d'octets que A et ne gagne
que de la latence. Un filtre d'admission (SLRU) réduit ce trafic ; son effet sur `h` est à mesurer.

**Qualité attendue** : un ordre de grandeur seulement. Par la linéarité de HIGGS (petites erreurs,
perte ≈ somme pondérée des MSE relatives [litt. 02]), B1 dans le scénario LRU ajoute en moyenne
0,23 × 4,29 % ≈ **1,0 % d'erreur relative** sur l'ensemble des usages d'experts, du même ordre que
le bruit propre du format (1,33 % sur une gaussienne) [calc.] ; HOBBIT mesure ≤ 1 point pour 30 %
d'experts servis en basse précision sur Mixtral [litt. 04]. Rien de cela n'est une mesure de
gpt-oss-120b.

**Le seuil, déclaré avant toute mesure** (réponse par délégation du 2026-10-15, réversible) : B est
acceptable si sa divergence KL moyenne contre A (même moteur, même étage) reste sous **0,0055**,
l'écart mesuré entre deux moteurs justes sur les mêmes poids [mes. 06], et si son taux de premier
choix identique reste au-dessus de 95,96 %. Raison : une perte plus petite que l'écart entre deux
implémentations correctes ne se distingue pas d'un changement de moteur. Si le seuil tombe, la
politique de défaut (R3) choisit, défaut par défaut, entre servir la base, attendre le complément ou
re-router, selon le score de routage de l'expert manquant.

**Ce qu'elle sacrifie** : l'exactitude sur une part des usages ; une politique de plus à témoigner ;
le trafic des compléments.

**Ce qu'il faut télécharger** : rien de plus que A. Pour Qwen3.8-Flash-Next ensuite : 78,9 ou 111,3 Go
(§ 5).

**B sur un disque non chiffré** : à 6,0 Go/s, le disque cesse de limiter B1 : la PCIe prend le maximum
(48 ms contre 47 de disque, LRU calé) et le plafond monte à **19,4 jetons/s** [calc.]. C'est là, et
seulement là, que garder le lien en Gen 4 (I3), la capacité de la VRAM et l'aide du processeur pour
les experts tièdes redeviennent des leviers.

### 4.3 C — Lire moins souvent : un dense lu du disque, vérifié en arbre

**Modèle** : Llama-3.3-70B-Instruct IQ3_XXS (27 469 499 360 octets, bartowski, licence Llama 3.3
Community), brouillon Llama-3.2-1B-Instruct Q4_K_M (807 694 464 octets, licence Llama 3.2) [mes.,
tailles lues par l'API Hugging Face, `tailles-hf-denses.json`].

**L'idée** : un dense lit tous ses poids à chaque passe, mais une passe de vérification de `n` jetons
coûte presque le même temps tant que `n < n* = F · b / (2 · B_eff)`. Avec F ≈ 8 Tflop/s utiles
(60 % des 13,4 mesurés en f16, hypothèse), b = 0,38 octet par paramètre (IQ3_XXS) et B_eff = 26,9 Go
lus en 3,79 s, soit 7,1 Go/s : **n* ≈ 210 jetons** [calc.]. Un arbre de 64 à 128 nœuds est gratuit en
calcul.

**Plafond** (`dense_C` de `plafonds.json` ; 5,19 Go de la cible résidents en VRAM après le brouillon,
11 Go en RAM, le reste du disque à 2,82 Go/s ; 12 pas de brouillon par passe, 88 ms) [calc.] :

| Fichier | Go par passe | T(passe) | sans spéculation | chaîne α = 0,8, k = 4 | borne d'une chaîne (α = 0,8) | arbre, 9,7 par passe [litt.] |
|---|---|---|---|---|---|---|
| Q4_K_M | 41,9 | 9,13 s | 0,11 | 0,36 | 0,54 | 1,05 |
| **IQ3_XXS** | 26,9 | 3,79 s | 0,26 | 0,87 | 1,29 | **2,50** (série 1,68) |
| IQ2_M | 23,5 | 2,60 s | 0,37 | 1,25 | 1,86 | 3,61 |
| IQ2_XXS | 18,5 | 1,09 s | 0,85 | 2,85 | 4,24 | 8,22 |

**Mémoire de pointe** : VRAM pleine (cible 5,19 + brouillon 0,81 + arbre et cache KV ≈ 0,5 Go ; un
contexte de 4 096 jetons demande à lui seul 1,3 Go de cache KV pour 80 couches × 8 têtes × 128 × 2 ×
2 octets, ce qui renvoie 0,8 Go de plus au disque, +0,3 s par passe [calc.]) ; RAM ≈ 12 Go.

**Qualité attendue** : celle du fichier IQ3_XXS ; la vérification n'ajoute aucune perte. Mais Llama 3
se quantifie mal (Llama 3 70B : +76 % de perplexité à 2,07 bits même avec PV-tuning [litt. 02]) et le
9,7 de SpecExec vient d'un 70B GPTQ 4 bits dont les poids tenaient en RAM [litt. 05].

**Ce qu'elle sacrifie** : le terrain des MoE (un dense de 70B à 3 bits reste à 2,5 jetons/s au
mieux) ; un moteur de vérification en arbre à écrire (I6) ; 28,3 Go de téléchargement.

**Ce que la combinaison « MoE + spéculation » devient** : elle n'est ni dans A ni dans B par défaut.
Elle y entre si la trace de I4 donne ρ assez grand pour que `α > 1 − ρ` (§ 1.5), avec un brouillon
EAGLE-3 publié pour gpt-oss [litt. 05].

### 4.4 Le format commun (proposition pour l'arbitre)

Un seul fichier, réécrit depuis le GGUF d'origine, sert A et B :
- en-tête : la table des tronçons (couche, expert, matrice, décalage, longueurs des flux, empreinte) ;
- par matrice d'expert (4,2 Mio d'origine) : flux des échelles (médiane de ligne en clair, écarts en
  rANS), flux de la base (rANS, une table par tenseur), flux du complément (rANS, une table par classe
  de base), alignés sur 4 Kio pour la lecture sans tampon ;
- A lit les trois flux ; B lit les deux premiers au défaut.
Le taux de A est conservé à l'en-tête près (proposition du § 4.2).

### 4.5 Comparaison et choix

| | A | B | C |
|---|---|---|---|
| Plafond, LRU calé (série) | 6,24 (3,93) | ~~8,88 (5,09)~~ B1 6,16 (4,83) ; B3 10,89 (5,58) | 2,50 (1,68) |
| Plafond, uniforme | 2,05 | 2,93 | — (dense) |
| RAM de pointe | 1,9 à 12,3 Go | ≈ 12 Go | ≈ 12 Go |
| Qualité | exacte | à juger (seuil KL 0,0055) | IQ3_XXS |
| Téléchargement | aucun | aucun | 28,3 Go |
| Étage limitant | disque | disque (PCIe sur disque non chiffré) | disque |
| Risque principal | la localité réelle | la qualité des défauts | la qualité de Llama 3 à 3 bits |
| Ce qui est neuf | l'assemblage, sous Vulkan et Windows | le raffinement exact lié à l'étage | l'arbre en régime disque, mesuré |

Réponse par délégation du 2026-10-15, réversible : **A d'abord, dans le format qui prépare B ; B dès
que A tourne et que la trace donne `h` ; C en parallèle seulement si un agent est libre.** Raison en
une ligne : A ne demande rien à Stone, se juge exactement, et toutes ses briques sont déjà mesurées ;
B est un supplément du même fichier ; C demande un téléchargement et un moteur d'arbre pour un
plafond plus bas.

---

## 5. Les téléchargements à demander à Stone

Triés par nécessité. Aucun n'est nécessaire pour construire et juger A et B sur gpt-oss-120b.

| Rang | Nom | Source | Taille | Licence | Pourquoi |
|---|---|---|---|---|---|
| 0 | (rien) | — | — | — | A et B tournent sur gpt-oss-120b et 20b, déjà là (empreintes vérifiées, REPRISE) |
| 1 | DirectStorage 1.4.0-preview2-2606.904 | NuGet `Microsoft.Direct3D.DirectStorage` | 3 986 072 o | licence Microsoft, à lire | comparer le chemin disque → carte de A à celui de Windows (GDeflate, zstd) ; sous le seuil de 500 Mo |
| 2 | Qwen3.6-35B-A3B UD-Q4_K_M | `unsloth/Qwen3.6-35B-A3B-GGUF` | 22,13 Go | Apache-2.0 | second MoE fin (256 experts, top-8) pour la trace et ρ ; comparable à Edge0 et moe-stream [04] |
| 3 | OLMoE-1B-7B-0924 Q4_K_M | Allen AI | ≈ 4,2 Go | Apache-2.0 | première trace de routage rapide (64 experts) [04] |
| 4 | Llama-3.3-70B-Instruct IQ3_XXS + Llama-3.2-1B-Instruct Q4_K_M | `bartowski/…-GGUF` (empreintes a2a70f06…, 6f85a640…) | 27 469 499 360 + 807 694 464 o | Llama 3.3 / 3.2 Community | architecture C |
| 5 | Qwen3.8-Flash-Next UD-Q2_K_XL (ou UD-Q4_K_XL) | `unsloth/Qwen3.8-Flash-Next-GGUF` | 78,87 Go (111,33 Go) | qwen-community-1.0 | second modèle de B ; table de n-grammes (I7) [06] |
| 6 | Qwen3.5-9B-MTP-GGUF Q4_K_M | `unsloth/Qwen3.5-9B-MTP-GGUF` | 5,87 Go | Apache-2.0 | accord du MTP natif (05) |
| 7 | PyTorch avec CUDA (roue Windows) | pytorch.org | plusieurs Go (non relevé ici) | BSD | seulement pour GSQ ou EXL3 (R5) |

Avec 327 Go libres sur C: aujourd'hui (relevé ici), les rangs 2 à 5 tiennent ensemble (≈ 133 Go).

---

## 6. Ce qui pourrait être faux

- **Le modèle de succès `h(c) = c^β` est une extrapolation d'un point.** Il vient d'un LRU sur une
  couche de Qwen3-30B-A3B (128 experts, 8 actifs, un domaine) ; gpt-oss-120b a 4 actifs, et sa courbe
  peut être plus plate (moins de réutilisation) ou plus raide. Les trois scénarios encadrent ma
  croyance, ils ne bornent pas la réalité. Tous les plafonds de A et B en dépendent d'un facteur 5.
- **La base llama.cpp est estimée, pas mesurée.** Les rapports ×2,5 à ×17 tombent si llama.cpp lit
  mieux que par fautes de page de 4 Kio (le préchargement de Windows peut regrouper) ou si son
  processeur calcule moins vite que 15,6 Go/s (plus probable, ce qui creuserait l'écart).
- **Le disque à 2,58 Go/s a été mesuré machine chargée** (jusqu'à 0,6 Go/s de lectures étrangères
  [01]) ; au repos il peut être plus haut. Sur batterie, il n'est pas mesuré.
- **Le plafond suppose un recouvrement parfait et une file jamais vide.** Le plancher en série (3,93
  pour A) est plus proche de ce qu'obtiennent les moteurs publiés (18 à 45 % de leur borne [04]).
- **11 Go de RAM épinglée** : WDDM peut limiter la mémoire hôte visible de la carte ; si le cache
  tiède doit vivre en mémoire paginable, chaque succès en RAM passe par une copie du processeur
  (7,5 Go/s sur secteur, 1,25 sur batterie [mes. 01]). Non vérifié.
- **`t0` = 3,5 ms** vient d'un autre modèle (Qwen3.5-4B, sous CUDA) ; un moteur Vulkan à nous peut
  avoir un coût fixe plus grand (une synchronisation par couche pour lire le routeur : 36 par jeton).
- **La qualité de B n'est estimée que par la linéarité de HIGGS**, valable pour de petites erreurs ;
  4,29 % sur un expert n'est pas petit. Le seuil KL vient d'un modèle hybride (Qwen3.5-4B) ; l'écart
  entre moteurs sur gpt-oss peut être autre.
- **La couche de base est mesurée sur 12 tenseurs de gpt-oss-20b**, pas sur le 120b ; les entropies
  des deux modèles diffèrent de 0,001 bit sur les codes [03], ce qui rend l'écart improbable, mais il
  n'est pas mesuré.
- **SliceMoE, TRACE, Drop-by-Drop, MatGPTQ et AnyBCQ ne sont lus qu'au résumé** (API arXiv,
  2026-10-15). L'un d'eux peut faire, dans son corps, ce que j'appelle neuf en R1 (notamment SliceMoE
  sur un étage disque). À lire en entier avant de publier quoi que ce soit.
- **La condition `α > 1 − ρ`** suppose α constant et un ρ indépendant de la position ; l'union réelle
  de `n` jetons décroît moins vite que le modèle à un paramètre.
- **Le n* ≈ 210 de C** repose sur F ≈ 8 Tflop/s utiles (hypothèse) et néglige la déquantification
  dans la GEMM.
- **La VRAM utile** : 6,5 Go pour les poids est une hypothèse de 06 ; le cache KV de gpt-oss-120b à
  long contexte (fenêtre glissante une couche sur deux, 8 têtes KV) n'est pas chiffré ici.
- **Le volume non chiffré à 6,0 Go/s** est l'annonce de Samsung ; Intel RST VMD reste sur le chemin
  et sa part dans les 53 % perdus n'est pas séparée [01].

---

## 7. Recettes (essayées dans cette étude, avec leur raison)

| Recette | Marche ? | Raison |
|---|---|---|
| Charger le lecteur GGUF d'une autre étude par `importlib` | oui, après correction | `dataclass` exige que le module soit inscrit dans `sys.modules` avant son exécution |
| Second chemin de l'inventaire sur le fichier local plutôt que distant | oui | A et R retrouvés à 0,3 % ; révèle la contiguïté des matrices d'experts, que la lecture distante ne regardait pas |
| Mesurer une couche de base par la loi conjointe (échelle, code) comptée une fois | oui | toutes les partitions (7 à 1 bit, 35 à 2 bits) se calculent sur 256 × 16 comptes, en secondes, sans relire les poids |
| Centres de classe pondérés par le carré de l'échelle E8M0 | oui | donne l'erreur dans le domaine réel, pas dans celui des codes |
| Témoin d'identité de la chaîne H(X) = H(B) + H(X\|B) | oui | vérifie que H(X\|B) est calculé indépendamment, pas déduit |
| Sorties numpy dans un JSON | échec puis corrigé | `numpy.bool_` n'est pas sérialisable : convertir avant |
| Caler `h(c) = c^β` sur un point publié | à manier avec soin | une seule constante, donc une seule courbe par point ; deux points (LRU, Belady) donnent deux scénarios |
| Témoins de l'équation repris des chiffres d'autres études | oui | la cassure (débit du lien au lieu du débit mesuré) fait tomber exactement le témoin qui en dépend |
| Recherche de nouveauté par l'API arXiv avant d'écrire « neuf » | oui, et elle a déplacé la frontière | SliceMoE et TRACE font une partie de B ; la part neuve se réduit et se précise |

---

## 8. Sources (consultées le 2026-10-15)

Les sources des études 01 à 06 sont dans leurs § Sources et dans `memoire/sources/*.bib` ; je ne les
répète pas. Sources propres à cette étude (dates par l'API arXiv, première et dernière version) :

- SliceMoE: Bit-Sliced Expert Caching under Miss-Rate Constraints for Efficient MoE Inference —
  https://arxiv.org/abs/2512.12990 — 2025-12-15 / 2026-09-08 (v5). Résumé lu.
- TRACE: Unlocking Effective CXL Bandwidth via Lossless Compression and Precision Scaling —
  https://arxiv.org/abs/2509.03377 — 2025-09-03 / 2026-01-30 (v3). Résumé lu.
- Multi-Bitwidth Quantization for LLMs Using Additive Codebooks (Drop-by-Drop) —
  https://arxiv.org/abs/2606.12876 — 2026-06-11 / 2026-09-26 (v2). Résumé lu.
- MatGPTQ: Efficient and Accurate Inference over Nested Quantized Models —
  https://arxiv.org/abs/2602.03537 — 2026-02-03 / 2026-09-30 (v2). Résumé lu ; code annoncé
  `IST-DASLab/MatGPTQ` (licence non vérifiée).
- AnyBCQ: Hardware Efficient Flexible Binary-Coded Quantization for Multi-Precision LLMs —
  https://arxiv.org/abs/2510.10467 — 2025-10-12 / 2026-02-02 (v2). Résumé lu.
- W. H. R. Equitz, T. M. Cover, « Successive refinement of information », IEEE Transactions on
  Information Theory 37(2), 1991, p. 269–275.
- Tailles des fichiers Llama : API Hugging Face, dépôts `bartowski/Llama-3.3-70B-Instruct-GGUF`
  (révision b6c5c9f, 2024-12-07), `bartowski/Llama-3.2-1B-Instruct-GGUF` (révision 067b946,
  2024-10-08), `unsloth/Llama-3.3-70B-Instruct-GGUF` (révision 8f14c5c, 2025-05-10) ;
  `tailles-hf-denses.json`.
- Requêtes de nouveauté (API `export.arxiv.org`, tri par date de dépôt, User-Agent
  `troncons-recherche/1.0`) : « successive refinement » + quantification + LLM ; progressif + sans
  perte + poids ; MXFP4 + compression ; « expert offloading » + SSD ; « bit-plane » + poids ;
  Matryoshka + quantification ; MoE + SSD + inférence ; Vulkan + inférence (aucun résultat) ;
  « bit-sliced » + experts ; « entropy coding » + MoE ; spéculation + SSD.

Références au format biblatex : `memoire/sources/07-synthese.bib`.

---

## Annexe A. Les dérivations

**A.1 Le temps d'un jeton.** Proposition 1 de l'étude 01 (borne d'une chaîne d'étages), appliquée aux
octets de chaque étage du § 1.2. `T_carte` additionne décodage et GEMV parce qu'ils occupent les
mêmes multiprocesseurs ; le disque et la PCIe se recouvrent avec la carte (part cachée mesurée 0,98 à
1,01 [04]).

**A.2 Le calage de β.** `h(c) = c^β` passe par (0,134 ; 0,659) si `β = ln 0,659 / ln 0,134 =
(−0,4170) / (−2,0099) = 0,2075`, et par (0,134 ; 0,791) si `β = (−0,2345) / (−2,0099) = 0,1167`.
Vérification sur le second point publié (moe-stream, au moins 53 % à 31 %) : 0,31^0,2075 = 0,784 ≥
0,53.

**A.3 Le plafond de A, scénario LRU calé, pas à pas.**
`c_v = (6,5 − 1,686) / 61,07 = 0,0788` ; `h_v = 0,0788^0,2075 = 0,590`.
`c_r = 11 × 1,1026 / 61,07 = 0,1986` ; `h_v + h_r = 0,2774^0,2075 = 0,766` ; `h_s = 0,234`.
`T_disque = 0,234 × 1,909 / 1,1026 / 2,58 = 0,157 s`.
`T_pcie = (0,176 × 1,909 + 0,234 × 1,909) / 1,1026 / 12,2 = 0,058 s`.
`T_carte = 0,410 × 1,909 / 41,6 + (1,686 + 1,909) / 209,4 = 0,0188 + 0,0172 = 0,036 s`.
`t_max = 0,157 + 0,0035 = 0,161 s` → 6,24 jetons/s ; `t_sum = 0,254 s` → 3,93.

**A.4 La base de B.** Bits lus par poids au défaut : `2,642 × 1,003 + 0,0344 = 2,684` ;
`r_base = 4,25 / 2,684 = 1,584` ; contre le sans-perte à trois classes `4,25 / 3,8545 = 1,1026` :
`1,584 / 1,1026 = 1,436`. B1 : `T_disque = 0,234 × 1,909 / 1,584 / 2,58 = 0,109 s` → 8,88 jetons/s.

**A.5 La règle de bits à l'étage, avec les débits de cette machine.** Lagrangien de l'étude 02 (D6) :
`b_i = ½ log₂(2 ln 2 · c_i · W_i / (λ · n_i))` ; à sensibilité égale, l'écart entre une matrice lue à
`W_1` et une matrice lue à `W_2` vaut `½ log₂(W_1 / W_2)`. Avec la GEMV en VRAM (209,4) et le disque à
la taille d'un expert (2,58) : `½ log₂(81,2) = 3,17 bits`.

**A.6 La spéculation sous réutilisation.** La passe de vérification de deux jetons lit `t (2 − ρ)`
experts au lieu de `t` et rend `1 + α` jetons ; elle paie si `(1 + α) / (2 − ρ) > 1`, soit `α > 1 − ρ`.
Sous l'indépendance, `ρ = t/E` et l'on retrouve la condition de l'étude 05.

**A.7 Le coude du calcul de C.** `n* = F · b / (2 · B_eff)`, `F = 8 × 10¹²`, `b = 26,9 / 70,6 = 0,381`
octet par paramètre, `B_eff = 26,9 / 3,79 = 7,10 Go/s` : `n* = 8 × 10¹² × 0,381 / (2 × 7,10 × 10⁹) =
215`.

## Annexe B. Outils et journaux

- `outils/07-synthese/inventaire_gptoss.py` → `inventaire-gptoss.json`, `inventaire-gptoss-casse.json`.
- `outils/07-synthese/raffinement_mxfp4.py` → `raffinement-mxfp4-gptoss20b.json`,
  `raffinement-mxfp4-gptoss20b-casse.json`.
- `outils/07-synthese/plafonds.py` → `plafonds.json`, `plafonds-casse.json`, et pour le mémoire
  `csv/architectures-gptoss120b.csv`, `csv/plafond-gptoss120b-contre-ram.csv`,
  `csv/plafond-gptoss120b-contre-hs.csv`.
- `fondations/journaux/07-synthese/tailles-hf-denses.json` : tailles et empreintes des fichiers Llama.
- Commandes : `python -I -X utf8 outils/07-synthese/<outil>.py [--casser] > <journal>.json`, depuis la
  racine du dépôt.
