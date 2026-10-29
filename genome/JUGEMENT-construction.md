# Le jugement de la construction : lots A (codon du zéro, `.trc` v1.2) et B (génome synonyme, mode rapide)

Rôle : juge indépendant. Je n'ai rien construit : ni la décision v1.2, ni le codeur, ni le compagnon
rapide, ni le moteur. Date : 2026-10-22. Étiquettes : **[mes.]** mesuré ici, outil et journal commités ;
**[calc.]** calculé ici sur des mesures commitées ; **[lu]** lu dans un journal d'un autre flux, non
refait ; **[hyp.]** hypothèse dite. Seuils déclarés avant toute mesure :
`mesures/genome/construction/juge/00-seuils-declares.md` (commit 1f5fe0f, 2026-10-22 vers 3 h 55 ; à
cette heure aucun outil du juge n'avait lu un octet d'un modèle). Outils : `outils/genome/construction/juge/` ;
journaux : `mesures/genome/construction/juge/` ; moteur, `juge` et `genome-capture` construits par moi
depuis `main` (f136e27) dans ma cible (`construction-moteur.log`).

Les livrables jugés : genome/06-codon-v1-2.md (lot A), genome/07-genome-synonyme.md (lot B), et le cahier
qui les a commandés, genome/05-synthese.md § 4.

---

## 0. En bref

1. **Le lot A tient en entier, par mes chemins.** Les deux `.trc` v1.2 ont les tailles publiées à l'octet
   (10 851 844 096 et 55 930 175 488 ; −1 800 486 912 octets sur le 120b) ; **96 experts tirés au hasard
   sur 96**, décodés par un décodeur que j'ai écrit depuis la seule description du format, sont l'expert du
   GGUF au bit près, au signe des zéros près (témoin v1.0 : 40 sur 40 ; trois cassures tombent) ; **les
   logits sont identiques au bit sur dix fenêtres que personne n'avait vues**, 0 sur 5 120 sur le 20b et
   0 sur 5 120 sur le 120b (cassure : 512 sur 512). Le J1 du 120b se reproduit (2,889 contre 2,004 j/s,
   ×1,442) ~~**et son attribution aussi** : c'est l'état des fichiers, pas le format (+3,4 % au plus).~~
   **Corrigé le 2026-10-27** (voir § 6) : son attribution tombe, c'est le format v1.2, par le motif de ses
   requêtes de lecture, propre à ce disque.
2. **Le génome synonyme du lot B tient hors de R1, et la règle B2 se renforce.** Sur les fenêtres neuves,
   λ = 0 fait 0,1448 (moteur) et 0,1446 (f64 substituée) contre la référence f64, λ = 1 fait 0,1751 ;
   λ = 0 meilleure de **−0,0303 ± 0,0084 (3,6 σ)**, là où R1 donnait 2,09 σ. Contre la frontière, par la f64 substituée : **−0,1565 ± 0,0334 (4,7 σ)**, dix fenêtres sur dix, et la queue plus basse qu'elle de 26 % au 99e centile, comme sur R1. Le moteur sert le
   mode rapide comme la référence f64 (0,0037 ; premier choix 97,8 %).
3. **Deux chiffres de vitesse du lot B tombent comme gains du mode rapide** (graves, § 7) : ~~120b ×2,00~~ →
   **×1,28** contre un fichier exact que l'étage disque lit à la même vitesse ; ~~20b ×1,24~~ → **×0,94** (le mode rapide génère moins
   vite que le v1.2 exact). Les mesures du lot B se redonnent (20b : 1,220 contre 1,241) ; c'est leur
   attribution qui est fausse : elles comparaient un compagnon neuf au v1.0 du 15 octobre, que l'étage
   disque lit 1,31 à 1,39 fois moins vite **à octets égaux**. La cause avancée (le cache de fichiers du
   système) est impossible : le moteur lit sans tampon.
4. **Des constats mineurs** (§ 7, M1 à M5) : les ± des KL absolues de 07 sont naïfs (trois à six fois trop étroits ;
   les verdicts appariés, eux, sont justes) ; « la queue baisse aussi avec λ = 0 » ne se reproduit pas contre
   λ = 1 (elle se reproduit contre la frontière) ; le sens de la perplexité de λ = 0 s'inverse hors de R1 ; la règle de vitesse du lot B ne
   regardait que le bruit des passes A.
5. **Verdict** : la construction livre ce qu'elle promettait **en octets et en qualité** (le codon sans perte,
   exact au bit ; le génome synonyme, meilleur que la frontière et que λ = 1 sur un texte neuf) ; elle ne
   livre pas le gain de vitesse annoncé pour le mode rapide. Ce que la vitesse a montré, c'est que ~~l'état
   physique d'un fichier~~ le motif des requêtes de lecture d'un format (corrigé le 2026-10-27, § 6) sur ce
   disque pèse plus que tout ce que la ronde a gagné en octets.

---

## D'où on part, où on va

**Au départ** : deux lots déclarés finis. Le lot A publie un format `.trc` v1.2 sans perte (le signe d'un
zéro fondu, −1,80 Go sur le 120b), des logits identiques au bit sur R1 (les dix premières fenêtres de
wiki.test), et un J1 du 120b 1,45 fois plus rapide en v1.2, qu'il refuse lui-même d'attribuer au format.
Le lot B publie le génome synonyme sur les 768 experts du 20b (KL 0,1318 pour λ = 0 contre 0,2640 pour la
frontière, sur R1), la règle B2 qui retient λ = 0 de justesse (2,09 σ), un mode rapide dans le moteur, et
deux gains de vitesse annoncés : ×1,24 (20b) et ×2,00 (120b). Le cahier (05 § 4.5, A6) et la barre du
SOCLE demandent un juge qui n'a écrit ni la décision ni le code.

**Ce que ce document établit** : par mes propres chemins (un décodeur du format écrit depuis sa seule
description, un lecteur GGUF propre, une KL calculée par mon code, des fenêtres de texte que les lots n'ont
jamais vues, une séance de vitesse à trois fichiers), ce qui tient, ce qui tombe, et ce qui est vrai mais
mal attribué.

**Ce qui reste** : § 11.

---

## 1. Ce que j'ai refait, et par quel chemin

| Chiffre publié | Où | Mon chemin | Résultat | Verdict |
|---|---|---|---|---|
| tailles des `.trc` v1.2, gain 0,12791 et 0,12562 bit | 06 § 6 | mon lecteur du format, fichiers entiers | redonnées à l'octet | **tient** |
| C1 en valeur, 768 + 4 608 experts | 06 § 5 | mon décodeur, 96 experts tirés + 40 témoins v1.0 | 96/96, 40/40, 3 cassures tombent | **tient** |
| 0 table v1.2 avec une fente pour un 8 | 06 § 5 | mon lecteur des tables | 0 sur 540 (540 sur 540 en v1.0) | **tient** |
| logits au bit, 5 120 / 5 120, 20b et 120b | 06 § 7 | dix fenêtres **neuves**, mon script, cassure neuve | 0 / 5 120 et 0 / 5 120 ; cassure 512 / 512 | **tient** |
| J1 : 2,89 contre 1,99 j/s, r = 1,454, « pas le format » | 06 § 8 | séance à trois fichiers, mon pilote | 2,889 contre 2,004, r = 1,442 ; étage disque B/A 1,37 | **tient**, ~~attribution comprise~~ attribution **barrée** le 2026-10-27 (§ 6 : c'est le motif du format) |
| KL R1 0,2640 / 0,1522 / 0,1318 ; B2 −0,0204 ± 0,0097 | 07 § 4.2 | ma KL sur les fichiers du lot B | redonnées | **tient** |
| B2 : λ = 0 meilleure (2,09 σ) | 07 § 4.2 quater | dix fenêtres neuves, moteur (f64 : λ = 0 seul) | −0,0303 ± 0,0084, 3,6 σ | **tient, renforcé** |
| λ = 0 meilleure que la frontière (5,6 σ) | 07 § 4.2 quater | fenêtres neuves, f64 substituée | −0,1565 ± 0,0334, 4,7 σ ; rapport 0,480 (R1 0,499) | **tient** |
| S3-K : moteur rapide = f64 substituée (0,0038 ; 97,8 %) | 07 § 4.3 | fenêtres neuves | 0,0037 ; 97,8 % | **tient** |
| « la queue baisse aussi » avec λ = 0 contre λ = 1 (99e −17 %, 99,9e −14 %) | 07 § 4.2 quater | fenêtres neuves | 99e −5 % ; 99,9e +6 % (3,61 contre 3,40) | **barré** (M2) |
| « la queue baisse aussi » avec λ = 0 contre la frontière (99e −26 %, 99,9e −17 %) | 07 § 0.4 | fenêtres neuves, f64 substituée | 99e −26 %, 99,9e −18 % | **tient** |
| 20b ×1,24, gain du mode rapide | 07 § 0.5, § 4.4 | séance à trois fichiers | R/A 1,220 redonné ; **R/B 0,942** | **barré** (G2) |
| 120b ×2,00, gain du mode rapide | 07 § 0.5, § 4.4 | séance à trois fichiers | R/A 1,851 ; **R/B 1,284** ; disque R/A 1,31 | **barré** (G1) |
| cause du ×1,24 : le cache de fichiers du système | 07 § 4.4 | lecture de `trc-es`, étage disque | lectures sans tampon ; disque R/A 1,39 | **barré** (G2) |

---

## 2. J-T : le `.trc` v1.2, taille et exactitude, par mon propre décodeur

### 2.1 L'instrument

`decodeur_juge.py` (Python, numpy) lit l'en-tête, MÉTA, RÉSIDENTS, TABLES, RÉPERTOIRE et les parties de
tronçon depuis decisions/ARCHITECTURE.md §§ 4.2 à 4.12 et 4.16 seulement, et le GGUF par son propre
lecteur (v3 : paires, infos de tenseurs, alignement). Je n'ai ouvert ni `trc-format`, ni `trc-codec`, ni
le décodeur de l'épreuve J1, ni les outils du lot A avant de l'écrire. Une seule erreur au premier
lancement, dans mon lecteur de MÉTA (`self.p += self.u64()` perd les 8 octets de la longueur, parce que
Python lit `self.p` avant d'appeler `u64`) ; corrigée, dite dans le commit f136e27. Elle ne touchait que
le contrôle de MÉTA, pas le décodage.

Le décodage rANS (§ 4.9.2) est **vectorisé sur toutes les voies de toutes les tuiles** d'un flux : 1 024
itérations (256 macro-pas × 4 sous-pas) sur un tableau de T × 32 états, au lieu de 4 147 200 pas
séquentiels pour une matrice de codes. Pourquoi c'est le même décodage [calc.] : au sous-pas k d'un
macro-pas, la voie l ne lit que son état x_l et la table de son contexte ; seul le pointeur p du flux
partagé de la tuile lie les voies, et le format fixe l'ordre l = 0 … 31. Si R ⊂ {0 … 31} est l'ensemble des
voies qui renouvellent (y < L), la voie l ∈ R reçoit le mot `mots[p + #{l' ∈ R : l' < l}]`, et p avance de
|R| : c'est exactement `p + cumsum(renouvelle)[l] − 1`, une somme préfixe sur l'axe des voies. Les tuiles
sont indépendantes (chacune part de `début[t]` et de ses 32 états). Une matrice de codes (2 880 × 2 880) se
décode en ≈ 0,5 s, un expert entier en 1,8 à 2,1 s, contrôles compris.

### 2.2 J-T0 : les quatre fichiers entiers [mes., `J-T0-fichiers.json`]

| | 20b v1.0 | 20b v1.2 | 120b v1.0 | 120b v1.2 |
|---|---|---|---|---|
| fautes de structure (en-tête, empreintes de l'en-tête, de MÉTA, de la table des RÉSIDENTS, de TABLES, du RÉPERTOIRE ; entrées ; taille déclarée = taille sur le disque) | 0 | 0 | 0 | 0 |
| fichier (octets) | 11 157 405 696 | **10 851 844 096** | 57 730 662 400 | **55 930 175 488** |
| parties de tronçon, alignées | 9 226 493 952 | **8 920 932 352** | 55 416 086 528 | **53 615 599 616** |
| octets utiles des tronçons | 9 224 936 032 | 8 919 387 648 | 55 406 705 152 | 53 606 030 768 |
| plus grand tronçon | 12 144 640 | 11 755 520 | 12 251 136 | 11 878 400 |
| tables CODES_CTX qui donnent une fente à un octet portant un 8 | 216 sur 216 | **0 sur 216** | 324 sur 324 | **0 sur 324** |

Gain sur les parties alignées : **0,12791 bit** par poids d'expert (20b) et **0,12562** (120b) ; A-C2
(≥ 0,12) tient sur les deux. Les huit tailles du tableau de 06 § 6 sont redonnées **à l'octet** ; les
540 tables du lot A aussi (540 sur 540 en v1.0, 0 en v1.2). L'empreinte de la table des RÉSIDENTS se
trouve à la fin exacte de la zone de données, sans bourrage : la description (§ 4.5, « après la zone de
données ») se lit ainsi, et le fichier y obéit.

### 2.3 J-T1 : 96 experts tirés, décodés par moi [mes., `J-T1-echantillon.{json,csv,log}`]

Tirage écrit et commité avant tout décodage (`tirage-experts.json`, commit 93a88a5) : 32 experts du 20b
et 64 du 120b, `Generator(PCG64(20261022))`. Pour chacun, dans le v1.2, huit contrôles : structure de
la partie, toutes les voies finissent sur L, blocs `[e, qs]` égaux octet pour octet aux blocs du GGUF
canonisés par mon code, biais égaux au bit, chaque poids égal **en valeur** au poids du GGUF non canonisé,
empreinte de l'expert canonique reconstruit = `empreinte_canonique`, empreinte des blocs du GGUF tels quels
= `empreinte_origine`, empreinte de la partie = celle du répertoire, aucun demi-octet 8.

- **96 experts sur 96 tiennent les huit contrôles.**
- **Témoin** (réponse connue) : les 32 experts du 20b et les 8 premiers tirés du 120b, décodés dans le
  **v1.0** : décodé = GGUF tel quel, empreinte = origine, **40 sur 40** ; et pour chacun, les demi-octets
  qui changent entre le décodé v1.0 et le décodé v1.2 sont **exactement** les −0 du GGUF (par exemple
  L19 E109 du 120b : 1 746 601 changés, 1 746 601 −0), ni un de plus ni un de moins.
- **Cassures** (toutes tombent) : un mot du flux CODES_CTX de la matrice 1 changé → voies hors de L,
  octets, valeurs et empreinte canonique faux ; la canonisation retirée de mon lecteur du GGUF → octets et
  empreinte canonique du GGUF faux (l'empreinte canonique du décodé, elle, tient : elle ne lit pas le GGUF ;
  je l'avais annoncée tombante, c'est l'empreinte calculée côté GGUF qui tombe) ; un bit du premier biais
  de la matrice 2 → biais, empreinte de la partie et empreinte canonique faux.
- Part des −0 dans l'échantillon : 6,42 ± 0,11 % (20b, 32 experts) contre 6,393 % sur le fichier ;
  6,33 ± 0,10 % (120b, 64 experts) contre 6,279 % : à 0,3 et 0,5 écart-type.

**Verdict J-T : tient.** Le `.trc` v1.2 est exactement ce que le format décrit, et chaque expert tiré est
l'expert du GGUF au bit près, au signe des zéros près.

---

## 3. Les fenêtres neuves

[mes., `fenetres-{prefixe,tirage,perplexite,fondre}.json`] Les 120 000 premiers octets de wiki.test.raw
(SHA-256 173c87a5…dd08) comptent **27 680 jetons** (llama-tokenize b11515) : ils couvrent R1 (jetons
0 à 5 119), la calibration du génome synonyme (5 120 à 11 263) et deux fois autant de marge. Dix débuts de
ligne de paragraphe tirés au-delà (graine 20261022 + 1), à plus de 12 000 octets les uns des autres, aux
octets 767 283, 511 976, 615 155, 854 814, 1 148 495, 1 228 294, 1 098 980, 1 240 966, 421 030 et 358 205.
Chaque extrait (≈ 9,0 à 10,4 Ko) passe par llama-perplexity (processeur seul, options de R0, une fenêtre) ;
les dix fichiers sont fondus en `base-juge-20b.kld` (1 025 589 700 octets, la taille de R1 ; chaque fenêtre
égale à sa source octet pour octet ; cassure : une fenêtre décalée ne l'égale pas). La référence f64 de ces
fenêtres (`juge reference --yarn openai`, l'appel de R1) a pris 2 168 s et lu 755 experts distincts
(R1 : 734). KL(llama.cpp processeur ‖ référence f64) y vaut 0,0339 (R1 : 0,0255) : des fenêtres un peu
plus difficiles, rien d'anormal.

**Les experts jugés pour la première fois** [mes., `kl/routage-neuf-contre-r1.json`] : la référence f64
route 755 experts sur mes fenêtres et 734 sur R1 ; **23 experts ne sont routés que par mes fenêtres**
(465 appels sur 490 560) ; sous la référence exacte, 11 experts du 20b ne sont routés par aucune des vingt
fenêtres (R1 et les miennes). Le lot B en comptait de 36 à 39 non routés sur R1 seules (07 § 6, sous
substitution) : la KL de mes fenêtres juge une partie de ceux-là (la passe f64 substituée λ = 0 y charge
756 experts).

---

## 4. J-C1 : les logits au bit, sur les fenêtres neuves

[mes., `logits/comparer-*.json`, `logits/evaluer-*.{csv,json,log}`] `troncons evaluer --flux --empreintes`,
dix fenêtres neuves, moteur construit par moi depuis `main` ; comparaison par mon script.

| | 20b | 120b |
|---|---|---|
| v1.2 contre v1.0 : empreintes de logits différentes | **0 sur 5 120** | **0 sur 5 120** |
| `.kld` de sortie | égaux (SHA-256 1aff1a6a…29ef) | égaux (SHA-256 709367e7…8a73) |
| témoin : le v1.2 évalué deux fois | CSV identiques (fc427e9f…469b) | — |
| cassure : copie du v1.2 où le signe du biais de la rangée 0 de gate est retourné pour les 32 experts de la couche 0, `--sans-garde`, fenêtre 0 | **512 sur 512 différentes**, dès la position 0 ; 73 premiers choix changés | — |

**Verdict J-C1 : tient**, sur deux modèles et sur un texte que personne n'avait vu. La proposition A1
(05 § 4.2) est vraie du moteur réel.

---

## 5. J-K : la KL du génome synonyme sur les fenêtres neuves

### 5.1 Les instruments

**Ma KL** (`kl_juge.py`, numpy) : par position notée, Σ_{i : log p_i > −16} p_i (log p_i − log q_i),
P et Q décodés de leur codage 16 bits sans renormalisation (la convention du lot R, R-pour-le-memoire
§ 2.4). **Témoin** : sur une paire publiée par le lot B (R1, λ = 0), ma KL vaut 0,131752831 contre
0,131752832 pour `juge kl` (1,1·10⁻⁸ relatif, seuil 10⁻⁶) ; **cassure** : Q décalé d'une position,
1,634 [mes., `kl/temoin-r1-synonyme-l0.json`]. **R1 recalculé par mon code** depuis les fichiers du lot B :
frontière 0,26399, λ = 1 0,15216, λ = 0 0,13175 ; appariées λ = 1 contre frontière −0,11183 ± 0,02962,
λ = 0 contre λ = 1 −0,02040 ± 0,00974 (2,09 σ, d̄ + 2σ = −0,00092), λ = 0 contre frontière
−0,13224 ± 0,02343 : **les chiffres du lot B sont redonnés à quatre chiffres et plus.**

Sur les fenêtres neuves, deux chemins : **le moteur** (`troncons evaluer --flux --rapide` sur les
compagnons, mon chemin principal : le produit tel qu'il est servi) et **la référence f64 substituée**
(`genome-capture kl --sub`, le chemin des lots). La vérité est la référence f64 des fenêtres neuves.

### 5.2 Les nombres [mes., `kl/kl-neuf-*.json`]

| Fenêtres neuves, 768 experts substitués (2 550 positions) | KL | σ naïf | σ par fenêtres | médiane | 99e c. | 99,9e c. | premier choix | perplexité (réf. 392,5) |
|---|---|---|---|---|---|---|---|---|
| moteur exact, v1.2 | 0,00437 | 0,0008 | 0,0021 | 0,00003 | 0,100 | 0,557 | 98,0 % | 394,0 |
| **λ = 0, moteur rapide** | **0,1448** | 0,0060 | 0,0164 | 0,0608 | 1,417 | 3,61 | **71,7 %** [69,9 ; 73,4] | 402,1 |
| λ = 0, f64 substituée | 0,1446 | 0,0059 | 0,0165 | 0,0617 | 1,397 | 3,51 | 71,3 % [69,5 ; 73,0] | 399,5 |
| λ = 1, moteur rapide | 0,1751 | 0,0062 | 0,0186 | 0,0755 | 1,490 | 3,40 | 67,6 % [65,8 ; 69,4] | 453,7 |
| frontière, f64 substituée | 0,3011 | 0,0074 | 0,0415 | 0,1917 | 1,877 | 4,30 | 51,5 % [49,5 ; 53,4] | 239,8 |
| λ = 1, f64 substituée | non passée (§ 9) | | | | | | | |

Pour mémoire, sur R1 (lot B, redonné par mon code) : frontière 0,2640, λ = 1 0,1522, λ = 0 0,1318 ;
moteur exact 0,00368.

### 5.3 Les verdicts déclarés

- **J-K2, B2 refait hors de R1 : λ = 0 meilleure, et plus nettement que sur R1.** Par le moteur :
  d̄ = KL_{λ=0} − KL_{λ=1} = **−0,0303**, σ par fenêtres 0,0084, d̄ + 2σ = −0,0136 < 0 (**3,62 σ**, contre
  2,09 sur R1) ; négative dans **9 fenêtres sur 10** (la fenêtre 0 contre : +0,016) ; λ = 0 a moins de KL sur
  1 858 positions sur 2 550 ; premier choix +4,1 ± 1,1 points. Par la f64 substituée, λ = 1 n'a pas été passé (le temps, et le flux placement qui attendait le calme : § 9) ; mais les deux chemins rendent la même KL pour λ = 0 à 0,0002 près sur ces fenêtres, et pour λ = 1 sur R1 (0,1522 par les deux chemins, lot B) : le verdict par le moteur vaut pour la variante. **Ma prédiction (« égales ») est
  démentie** : le choix de λ = 0 par la règle B2 n'était pas un coup de chance des fenêtres de R1.
- **J-K1, λ = 0 contre la frontière** : par la f64 substituée, **meilleure**, d̄ = KL_{λ=0} − KL_{frontière} = **−0,1565 ± 0,0334 (4,7 σ)**, négative dans les **10 fenêtres**, sur 2 297 positions sur 2 550, premier choix +19,8 ± 3,2 points. La frontière fait 0,3011 sur mes fenêtres (0,2640 sur R1) ; le rapport λ = 0 / frontière vaut **0,480** (R1 : 0,499). **Tient**, comme prédit.
- **J-K3, le moteur rapide contre la f64 substituée** (S3-K, seuils du lot B) : KL(f64 λ = 0 ‖ moteur
  λ = 0) = **0,0037 ≤ 0,011**, premier choix identique **97,8 % ≥ 95 %** : tient (le lot B mesurait 0,0038 et
  97,8 % sur R1). Les deux chemins rendent la même KL contre la vérité : 0,1448 et 0,1446, différence
  appariée +0,0002 ± 0,0006 (égales).
- **J-K4, le mode exact** : KL 0,00437, premier choix 98,0 % (R1 : 0,00368 et 97,2 %) ; sur les mêmes
  fenêtres, llama.cpp sur le processeur fait 0,0339 contre la même référence (journal de la référence).
  La forme de C4 tient contre llama.cpp processeur ; contre llama.cpp sur la carte (le comparant exact de
  C4), non mesuré ici.

### 5.4 Ce que les fenêtres neuves disent de plus

- **Le niveau** : λ = 0 fait 0,1448 sur mes fenêtres et 0,1318 sur R1 ; le moteur exact 0,0044 et 0,0037 ;
  la référence llama.cpp 0,0339 et 0,0255. Mes fenêtres sont un peu plus difficiles pour tout le monde
  (de 10 à 33 %) ; le génome synonyme ne s'y dégrade pas plus que le reste.
- **La queue** : sur R1, le lot B écrit qu'avec λ = 0 « la queue baisse aussi » contre λ = 1 (99e centile
  −17 %, 99,9e −14 %, 07 § 4.2 quater). Sur mes fenêtres, le 99e centile baisse de 5 % (1,417 contre 1,490,
  moteur) et le **99,9e monte** (3,61 contre 3,40) ; le maximum aussi (5,50 contre 3,63). Un 99,9e centile
  de 2 550 positions repose sur deux ou trois positions : ce n'est pas une grandeur qu'on peut opposer
  d'une variante à l'autre à cette taille d'échantillon (§ 7, M2).
- **La perplexité change de sens** : sur R1, λ = 0 descendait sous l'exact (411 contre 460) et λ = 1 restait
  à +1,4 % ; sur mes fenêtres, λ = 0 est à +2,4 % (402,1 contre 392,5) et λ = 1 à +15,6 %. La phrase de 07
  § 4.2 quater « λ = 0 déforme la distribution dans une direction privilégiée que λ = 1 ne prend pas » ne
  survit pas au changement de texte ; la leçon du 05 (seule la KL juge) se confirme une fois de plus.
- **Les experts** : mes fenêtres font jouer 23 experts que R1 n'avait jamais routés (§ 3) ; leur part des
  appels est petite (0,1 %), et la KL de λ = 0 les inclut.

---

## 6. J-V : la vitesse

### 6.1 Le plan : trois fichiers par modèle, dans une seule séance

Les deux lots ont chacun comparé **un fichier neuf à un fichier ancien** : le lot A le v1.2 (écrit le
17 octobre) au v1.0 d'origine (écrit le 15) ; le lot B ses compagnons rapides (écrits le 17 et le 22) au
même v1.0 d'origine. Le lot A a vu le piège et l'a dit (06 § 8 : deux v1.0 identiques au bit se lisent à
1,74 et 1,34 Go/s) ; le lot B ne l'a pas vu. ~~Le flux « placement disque » a établi depuis (08 § 3 [lu]) que
l'état physique d'un fichier sur ce NVMe déplace son débit de 30 à 60 % à contenu égal.~~

**Corrigé le 2026-10-27**, d'après `genome/JUGEMENT-placement.md` (§ 0, §§ 5.3, 5.6, 5.7, § 12 point 3) : sur ce disque, l'écart B/A suit **le motif des requêtes de lecture que le format impose** (frontières et longueurs des tronçons) : A lu au motif de B va comme B (×1,389), B lu au motif de A va comme A (×0,715). Le gain du J1 est donc **un gain du format v1.2, propre à cette machine**, par le motif de ses tronçons et non par ses 3,3 % d'octets ; la variable exacte du motif n'est pas isolée (couper chaque requête du v1.0 en deux ne le répare pas : ×0,851 et ×0,882). Les verdicts de ce paragraphe sur le mode rapide (r(R/B)) gardent leur sens : B et R ont tous deux
un motif rapide (≈ 11,6 et 8,3 Mo par requête), A le motif lent du v1.0 (≈ 12,0 Mo). Partout ci-dessous, « à
fichier d'âge comparable » et « l'état du fichier A » se lisent « à motif de lecture comparable » et « le motif
v1.0 du fichier A ».

Ma séance met donc **les trois fichiers** de chaque modèle dans le même plan équilibré
(A B R R B A A B R R B A, rangs moyens égaux ; note pour le mémoire § 1.3) : A = v1.0 d'origine,
B = v1.2 (même écrivain que les compagnons, écrit comme eux après le 15 octobre ; l'étage disque, mesuré dans la séance, lit B et R à la même vitesse), R = compagnon rapide. Alors
r(R/A) = r(R/B) · r(B/A) : r(B/A) mesure ce que le lot A a mesuré, r(R/A) ce que le lot B a mesuré, et
**r(R/B) ce que vaut le mode rapide à état de fichier comparable**. L'étage disque seul
(`troncons disque --n 1500`, l'instrument du lot A) passe d'abord, A B R R B A. Machine calme relevée
avant et après chaque passe : **aucune des 36 passes sous charge** ; secteur à chaque passe ; verrou tenu.
[mes., `vitesse/seance-{120b,20b}.{json,log}`, `vitesse/analyse-{120b,20b}.json`]

### 6.2 Le 120b (réglages du J1 : `mesurer --flux --emplacements 326`, invite wiki-3000, 256 jetons)

| | A, v1.0 d'origine | B, v1.2 | R, rapide frontière |
|---|---|---|---|
| génération, jetons/s (4 passes) | 1,995 · 1,785 · 2,013 · 2,019 | 2,892 · 2,886 · 2,900 · 2,868 | 3,712 · 3,709 · 3,698 · 3,719 |
| médiane ; σ relatif | **2,004** ; 5,8 % | **2,889** ; 0,5 % | **3,711** ; 0,2 % |
| octets de tronçons par pas | 710,1 Mo | 686,8 Mo (× 0,9671) | 468,5 Mo |
| débit par octet en génération | 1,42 Go/s | 1,98 Go/s | 1,74 Go/s |
| succès en VRAM | 0,590 | 0,590 | 0,607 |
| texte (256 jetons) | e4c6dbac… | e4c6dbac… (le même) | 2cf1d474… (celui du lot B) |
| mémoire de pointe | 388,7 Mo | 382,3 Mo | 342,4 Mo |
| **étage disque seul** (2 passes) | **1,772 · 1,744 Go/s** | **2,394 · 2,422** | **2,324 · 2,279** |

- **J-V1 (A-C3) : r(B/A) = 1,442**, σ = 5,8 % : pas de régression, gain annoncé ; le lot A publiait 1,454.
  **Le J1 du lot A se reproduit**, et son attribution aussi : les octets ne baissent que de 3,3 % (toit du
  format +3,4 %), l'étage disque lit B 1,37 fois plus vite que A.
- **J-V2 : r(R/B) = 1,284**, contre 2,00 publié par le lot B ; seuil déclaré 2,00 × (1 − 2 × 0,058) =
  1,769 : **le ×2,00 n'est pas un gain du mode rapide.** À fichier d'âge comparable, le mode rapide
  frontière rend ×1,28 en génération (toit des octets 686,8 / 468,5 = ×1,47). Ma prédiction (×1,38)
  était trop haute : le débit par octet du compagnon (1,74 Go/s) reste sous celui du v1.2 (1,98), des
  lectures plus courtes (8,3 Mo au lieu de 11,9 Mo par tronçon) [hyp. pour la cause].
- **D'où vient le reste du ×2,00** : r(R/A) = 1,851 ici (le lot B mesurait 2,00 avec d'autres réglages :
  sans `--flux`, 329 emplacements). Le lot B décomposait son rapport en ×1,524 d'octets et un « ×1,31 de
  débit par octet, que les compteurs ne séparent pas » (07 § 4.4, note pour le mémoire B3). **L'étage disque
  seul rend R/A = 1,309** : ce ×1,31 est ~~l'état du fichier A~~ le motif de lecture v1.0 du fichier A
  (corrigé le 2026-10-27), pas le mode.

### 6.3 Le 20b (réglages de la séance s2 du lot B : `mesurer`, emplacements par défaut, 256 jetons)

| | A, v1.0 d'origine | B, v1.2 | R, rapide λ = 0 |
|---|---|---|---|
| génération, médiane ; σ | **9,395** ; 0,4 % | **12,175** ; 0,2 % | **11,466** ; 0,6 % |
| préremplissage (708 jetons) | 10,9 j/s | 13,7 j/s | 16,9 j/s |
| octets de tronçons par pas | 116,4 Mo | 112,5 Mo | 115,1 Mo |
| succès en VRAM | 0,899 | 0,899 | 0,856 |
| débit par octet en génération | 1,09 Go/s | 1,37 Go/s | 1,32 Go/s |
| texte | 1b14e44a… | 1b14e44a… (le même) | 18be41e4… (celui du lot B) |
| **étage disque seul** | **1,786 · 1,775 Go/s** | **2,461 · 2,443** | **2,475 · 2,472** |

- **r(R/A) = 1,220** : la mesure du lot B (1,241) **se reproduit** à 1,7 % près.
- **J-V3 : r(R/B) = 0,942**, seuil 1,241 × (1 − 2 × 0,0056) = 1,227 : **le ×1,24 n'est pas un gain du
  mode rapide.** Contre un fichier exact que l'étage disque lit à la même vitesse, le mode rapide λ = 0 génère **6 % moins vite** : il
  lit autant d'octets par pas (115,1 contre 112,5 Mo ; toit ×0,98), parce que son routage, avec perte,
  manque plus souvent la VRAM (0,856 contre 0,899). Il ne gagne qu'au préremplissage (×1,23), où le texte
  est imposé et les octets suivent la taille des experts.
- **La cause avancée par le lot B est impossible.** 07 § 4.4 propose « le cache de fichiers du système,
  qui garde une plus grande part d'un fichier de 8,3 Go que d'un fichier de 11,2 Go » [hyp.]. Or le moteur
  lit chaque tronçon sans tampon (`trc-es`, `FILE_FLAG_NO_BUFFERING | FILE_FLAG_OVERLAPPED`), et le flux
  placement a mesuré que le disque lit 1,0000 à 1,0057 fois les octets demandés (08 § 3.1 [lu]). La cause est
  celle du 120b : l'étage disque lit R 1,39 fois plus vite que A, B 1,38 fois.
- **r(B/A) = 1,296** sur le 20b : la v1.2 du 20b va aussi 30 % plus vite que son v1.0, pour 3,4 % d'octets
  en moins ; même cause (l'étage disque, B/A = 1,38).

### 6.4 Ce que la vitesse dit, en une phrase par lot

- **Lot A** : tout ce qu'il publie tient, y compris sa prudence ; le format rend ses 3,3 % d'octets, et les
  fichiers v1.2 sont aujourd'hui les plus rapides de la machine ~~pour une raison qui n'est pas le format~~
  **à cause du format**, par le motif de ses requêtes de lecture (corrigé le 2026-10-27, voir § 6.1).
- **Lot B** : ses mesures sont justes et se reproduisent ; leur attribution au mode rapide est fausse.
  Le mode rapide vaut, en génération et à fichiers comparables, **×1,28 sur le 120b** (pour une KL de 0,14
  contre le moteur exact, proxy du lot B) et **×0,94 sur le 20b** ; il vaut ×1,12 (120b) et ×1,23 (20b) au
  préremplissage.

---

## 7. La lecture : ce qui est faux, trop beau, ou mal attribué

J'ai lu 06 et 07 phrase à phrase contre leurs journaux, et cherché, pour chaque chiffre de leurs § 0, le
fichier commité qui le porte. Deux constats sont **graves** : ils changent ce que le projet ferait ensuite.
Les autres sont mineurs : ils ne renversent aucune conclusion, mais ils rendent un chiffre plus beau qu'il
n'est.

### Graves

**G1. Le « 120b ×2,00 » du mode rapide (07 § 0, point 5 ; § 4.4 ; note pour le mémoire B3).** Le rapport
est bien mesuré (je le redonne : r(R/A) = 1,85 aux réglages du J1) ; il est faux **comme gain du mode
rapide**. Le fichier exact de la comparaison est le v1.0 du 15 octobre, que l'étage disque lit 1,31 fois
moins vite que le compagnon, à octets égaux par lecture ; contre le v1.2, écrit le même jour que le
compagnon, le mode rapide rend ×1,28 (§ 6.2). Le lot B avait isolé ce ×1,31 et l'avait laissé « non
mesuré » ; il est mesuré. **Ce que cela change** : le cahier (05 § 4.10, B3) construit la politique mixte
des défauts sur ce gain ; ×1,28 pour une KL de 0,14 (proxy du 120b) n'est pas ×2,00 pour la même KL.

**G2. Le « 20b ×1,24 » (07 § 0, point 5 ; § 4.4 ; § 7, recette « lire les compteurs »).** Même mesure
juste (r(R/A) = 1,220 redonné), même attribution fausse, et ici le mode rapide **ne gagne rien** : ×0,94
contre le v1.2 (§ 6.3). L'hypothèse avancée pour la cause (le cache de fichiers du système) est impossible
par construction (lectures sans tampon), et le lot B disposait des deux faits pour le voir : le moteur
n'avait lu « presque les mêmes » octets par pas (07 § 4.4), et la première passe B, juste après l'écriture
du compagnon et une passe A, était deux fois plus lente que les suivantes (5,46 contre 11,8 j/s), ce
qu'aucun cache de lecture n'explique. **Ce que cela change** : sur le 20b, le mode rapide est un mode de
préremplissage (×1,23), pas de génération.

### Mineurs

**M1. Les ± des KL absolues** (07 § 0, point 1 ; § 4.2 ; tableaux de la note pour le mémoire) sont les
incertitudes **naïves** par positions : 0,2640 ± 0,0066, 0,1522 ± 0,0062. Par fenêtres, qui respecte la
corrélation des positions d'une même fenêtre, elles valent ± 0,0376 et ± 0,0203 (§ 5 ; note pour le
mémoire § 1.4 : effet de plan ≈ 32, soit ≈ 8 positions indépendantes par fenêtre). Les verdicts du lot B
reposent sur des différences **appariées** prises avec σ par fenêtres : ils ne sont pas touchés. Mais un
lecteur qui comparerait deux KL absolues avec les ± publiés se croirait trois à six fois plus précis
qu'il n'est.

**M2. La queue au 99,9e centile** (07 § 0, point 4 ; § 4.2 quater) : « avec λ = 0, la queue baisse aussi »
contre λ = 1 (−14 % au 99,9e) ne se retrouve pas sur les fenêtres neuves (+6 %) ; un 99,9e centile de
2 550 positions tient à deux ou trois positions. Contre la frontière, elle **se reproduit** : sur mes fenêtres, 99e centile 1,877 → 1,397 (**−26 %**, R1 −26 %) et 99,9e 4,30 → 3,51 (**−18 %**, R1 −17 %). C'est donc la comparaison à λ = 1 qui tombe, pas celle à la frontière (07 § 0, point 4, tient)..

**M3. La perplexité de λ = 0 « dans une direction privilégiée »** (07 § 4.2 quater) : le sens s'inverse
sur les fenêtres neuves (§ 5.4). Le lot B l'avait marqué « pourquoi : non mesuré » ; c'est le « quoi » qui
ne tient pas.

**M4. Le bruit de la règle de vitesse du lot B** ne regardait que les passes A (σ = 2,3 % sur le 20b) ; les
passes B avaient σ = 31 % à cause de la première (5,46 j/s). Avec σ = max(σ_A, σ_B), le gain n'aurait pas été
annoncé. La règle déclarée a été suivie ; elle était trop étroite pour voir que le fichier B changeait de
comportement entre sa première et sa deuxième lecture (le flux placement a vu depuis qu'une copie neuve du
20b perd en deux heures l'avance qu'elle avait juste après son écriture : 2,18 puis 1,75 Go/s, 08,
journaux p2b-D et p2b-D2 [lu]).

**M5. « Le gain ne fond pas ; il grandit »** (07 § 4.2) compare λ = 0 à 32 experts (0,727) à λ = 1 à 768
(0,576) : deux variantes. À variante égale (λ = 0 : 0,727 puis 0,499), la phrase reste vraie.

### Ce que j'ai vérifié et qui tient, en plus des mesures refaites

- 06 § 6 : le gain par tenseur vaut 2 × (part des −0) à −0,000167 … +0,000161 bit près sur les 180 tenseurs ;
  parts des −0 6,393 % (20b) et 6,279 % (120b), recalculées depuis `tailles-par-tenseur.csv`.
- 06 § 8 : les huit passes de s2 redonnent 1,988 et 2,890 j/s et r = 1,454 depuis leurs journaux.
- 07 § 4.4 : les seize passes de s2 (20b et 120b) redonnent 9,54 / 11,84 et 1,98 / 3,97 j/s depuis leurs
  journaux ; les octets par pas 0,1164 / 0,1151 et 0,7073 / 0,4641 Go aussi.
- 05 § 0, point 2 : la correction barrée de la synthèse (la KL 0,0262 est celle de λ = 0) est juste.
- Aucune ligne d'attribution ni adresse électronique dans les documents des deux lots que j'ai lus (06, 07,
  leurs notes pour le mémoire et de reprise).

---

## 8. Ce qui tient selon le juge, et ce qui est barré

### Ce qui tient selon le juge

| Chiffre | Lot | Par quel chemin je l'ai refait |
|---|---|---|
| `.trc` v1.2 : 10 851 844 096 o (20b), 55 930 175 488 o (120b), −1 800 486 912 o, 0,12791 et 0,12562 bit par poids | A | mon lecteur du format, fichiers entiers |
| chaque expert v1.2 = l'expert du GGUF, au signe des zéros près ; aucun 8 ; trois empreintes | A | mon décodeur, 96 experts tirés ; témoin v1.0 40 sur 40 |
| aucune table v1.2 ne peut produire un 8 (0 sur 540) | A | mon lecteur des tables |
| logits identiques au bit, v1.2 contre v1.0, sur les deux modèles | A | dix fenêtres neuves, 0 sur 5 120 et 0 sur 5 120, `.kld` égaux, cassure 512 sur 512 |
| J1 du 120b : v1.2 1,45 fois plus rapide que le v1.0 d'origine, ~~**pour les fichiers, pas pour le format**~~ (corrigé le 2026-10-29 : le juge du placement attribue ce gain au format v1.2, par le motif de ses requêtes de lecture, propre à ce disque ; `genome/JUGEMENT-placement.md` §§ 0, 5.3, 5.6, 5.7 ; réserve R1 de `memoire/tome3/INVENTAIRE-figures.md`) | A | séance à trois fichiers : 1,442 ; étage disque 1,37 pour 3,3 % d'octets |
| le génome synonyme λ = 0 bat λ = 1 (B2) | B | fenêtres neuves, moteur : −0,0303 ± 0,0084 (3,6 σ) ; par la f64 substituée, λ = 0 seulement (λ = 1 non passé) |
| le moteur sert le mode rapide aussi fidèlement que la f64 substituée (S3-K) | B | fenêtres neuves : 0,0037 et 97,8 % |
| le mode exact est inchangé, et proche de la f64 | A, B | fenêtres neuves : KL 0,0044, premier choix 98,0 % |
| R1 : KL 0,2640 / 0,1522 / 0,1318, appariées −0,1118 / −0,0204 / −0,1322 | B | ma KL sur leurs fichiers |
| λ = 0 meilleure que la frontière, et sa queue plus basse (99e −26 %, 99,9e −17 %) | B | fenêtres neuves, f64 substituée : −0,1565 ± 0,0334 (4,7 σ) ; 99e −26 %, 99,9e −18 % |

### Ce qui est barré

- ~~**120b ×2,00** (gain du mode rapide)~~ → **×1,28** contre un fichier exact lu à la même vitesse par l'étage disque ; le reste est
  l'état du fichier v1.0 du 15 octobre (étage disque ×1,31). Le chiffre ×2,00 reste vrai comme comparaison
  de deux fichiers.
- ~~**20b ×1,24** (gain du mode rapide)~~ → **×0,94** en génération contre le v1.2 ; ×1,23 au préremplissage.
- ~~**cause : le cache de fichiers du système**~~ → impossible (lectures sans tampon) ; cause mesurée : l'état
  physique du fichier exact.
- ~~**avec λ = 0, la queue baisse aussi** au 99,9e centile, contre λ = 1~~ → non reproduit hors de R1 ; pas une
  grandeur mesurable à 2 550 positions.
- ~~**λ = 0 déforme la distribution dans une direction privilégiée**~~ → le sens de la perplexité s'inverse
  sur d'autres fenêtres.
- Les ± des KL absolues de 07 ne sont pas barrés, ils sont **requalifiés** : naïfs ; par fenêtres, trois à six
  fois plus larges.

*Réponse par délégation du 2026-10-22, réversible* : je porte ces barres dans 07 lui-même, aux phrases
concernées (§ 0 point 5, § 4.2 quater, § 4.4), et dans la ligne des vitesses de
`construction-synonyme-pour-le-memoire.md`, chacune suivie de « (barré par le juge,
JUGEMENT-construction § …) », sans rien retirer. Raison en une ligne : le SOCLE exige qu'un chiffre
contredit soit barré là où il est publié, et le lot B a fini son rôle.

---

## 9. Ce qui pourrait être faux (dans ce jugement)

- **Une séance par modèle, un seul matin.** L'état physique des fichiers change avec le temps (une copie
  neuve du 20b a perdu en deux heures l'avance qu'elle avait juste après son écriture, 08 [lu]) ; mes
  rapports r(R/B) valent pour l'état de ces fichiers le 2026-10-22 entre 6 h 17 et 7 h 11. Ils reposent sur
  le fait, mesuré dans la même séance, que B et R se lisent à la même vitesse à l'étage disque (R/B = 0,956
  et 1,009, sous le seuil S = 11,8 % de 08) : si ce n'était plus vrai un autre jour, il faudrait refaire la
  séance, pas reprendre mon chiffre.
- **Les réglages ne sont pas tous ceux du lot B.** Sur le 120b, j'ai pris ceux du J1 (`--flux`, 326
  emplacements) pour les trois fichiers ; le lot B avait le préremplissage par pas et 329 emplacements pour
  le compagnon. Mon r(R/A) (1,85) diffère du sien (2,00) pour cette raison au moins ; ce qui juge
  l'attribution est r(R/B), mesuré aux mêmes réglages pour R et B. Sur le 20b, j'ai repris ses réglages, et
  son rapport se redonne (1,220 contre 1,241).
- **Les fenêtres neuves sont de wiki.test**, comme R1 et la calibration : un autre corpus (code, dialogue)
  reste à juger (05 § 5).
- **Mon décodeur lit la même description que les auteurs du codeur.** Un contresens de la description
  partagé par les deux ne serait pas vu par la comparaison des octets décodés au GGUF… sauf qu'il l'aurait
  été : le GGUF est lu par mon propre lecteur, sans rien du format `.trc`, et les empreintes sont des
  SHA-256 calculés de mon côté. Ce qui n'est pas couvert : une partie du format que ni le v1.0 ni le v1.2
  n'exercent (niveaux, brut, colonnes).
- **96 experts sur 5 376 (1,8 %)** par mon chemin. La probabilité qu'un défaut touchant au moins 5 % des
  experts d'un modèle échappe à 32 tirages (20b) est 0,95³² ≈ 19 % ; à 64 tirages (120b), 3,7 % [calc.].
  Le vérificateur du lot A, lui, a couvert 100 % des experts par ses deux chemins ; mon tirage juge ce
  vérificateur, il ne le remplace pas.
- **Ma KL partage la convention du lot R** (coupe à log p > −16, sans renormalisation) : elle n'est pas
  indépendante de cette convention, seulement du code. Les différences appariées n'en dépendent presque pas.
- **Mes prédictions se sont trompées deux fois** (B2 « égales », mesuré 3,6 σ ; r(R/B) du 120b ≈ 1,38, mesuré
  1,28) ; elles étaient déclarées avant, et la mesure a décidé.
- **La référence substituée λ = 1 n'a pas été passée** sur les fenêtres neuves (le temps : 47 à 52 min par
  passe sous la charge de la machine, et le flux placement attendait le calme pour sa séance) ; B2 n'y est
  jugé que par le moteur, et la frontière que par la référence substituée. Les deux chemins s'accordent à
  0,0002 sur λ = 0 ici, et sur λ = 1 à R1 ; mélanger les chemins dans une différence appariée (λ = 1 moteur
  contre frontière f64 : −0,1260 ± 0,0366) n'est publié qu'à titre indicatif.
- **`genome-capture` et le moteur** que j'ai fait tourner sont construits depuis le même code que ceux des
  lots (`main`, f136e27) ; je juge les fichiers et les affirmations, pas un second moteur. Le second chemin
  du calcul des logits reste la référence f64 du lot R.

---

## 10. Recettes (pour RECETTES.md)

- **Une séance à trois fichiers sépare le format, le mode et le fichier** (v1.0 ancien, v1.2 neuf, compagnon
  neuf, plan A B R R B A A B R R B A, étage disque d'abord) : r(R/A) = r(R/B) · r(B/A), et l'étage disque
  dit lequel des facteurs n'est pas le mécanisme. Une heure par modèle. Marche ; a fait tomber deux chiffres.
- **Avant d'attribuer un gain de vitesse à un mécanisme, mesurer l'étage disque de chaque fichier dans la
  même séance.** Coûte une minute. Marche.
- **Un décodeur de juge écrit depuis la seule description du format, dans un autre langage, vectorisé par
  somme préfixe sur les voies** : 2 s par expert en numpy, juste au bit du premier coup sur le décodage
  (une erreur d'évaluation de Python dans le lecteur de MÉTA, vue au premier lancement). Marche.
- **Des fenêtres neuves tirées loin de la région déjà vue, une fenêtre par extrait, fondues en un seul
  `.kld`** (le format de llama-perplexity se fond par simple concaténation des jetons puis des entrées) :
  tous les outils du projet (`juge reference`, `troncons evaluer`, `genome-capture kl`) les lisent sans
  changement. Marche.
- **Publier une KL absolue avec son σ par fenêtres**, pas son σ naïf (effet de plan ≈ 32 sur R1). Les
  différences appariées, elles, se jugent déjà ainsi dans le projet.
- **Ne pas comparer un 99,9e centile de 2 550 positions d'une variante à l'autre** : il tient à deux ou
  trois positions. Échoue comme grandeur de comparaison.
- **Le texte d'un verrou compte** : mon premier verrou disait « pas une séance de vitesse » ; le flux des
  pistes, qui cherchait le mot « vitesse », s'est mis en pause pour rien (corrigé de leur côté,
  `outils/pistes/spectres/commun.py`). Écrire la raison sans le mot quand ce n'est pas une séance.
- **Arrêter une boucle bash qui lance un programme natif sous Windows ne tue pas le programme** : la passe
  f64 en cours a fini seule ; sa sortie redirigée était complète, renommée à la main (`sub-l0.json`).

---

## 11. Ce qui reste

1. **La décision B3 du cahier** (politique mixte des défauts, 05 § 4.10) est à reprendre avec r(R/B) et
   non r(R/A) : sur le 120b, ×1,28 en génération pour une KL de 0,14 (proxy) ; sur le 20b, rien en génération.
   Le cahier demandait de simuler la politique sur les traces avant de la construire : c'est d'autant plus
   nécessaire.
2. **Le levier de vitesse que la construction a trouvé n'est pas un mécanisme du génome** : c'est ~~l'état
   physique des fichiers sur ce NVMe~~ le motif des requêtes de lecture du format (corrigé le 2026-10-27,
   `genome/JUGEMENT-placement.md` (§ 0, §§ 5.3, 5.6, 5.7, § 12 point 3)) (×1,30 à ×1,44 entre deux fichiers du même modèle). Le levier qui marche aujourd'hui :
   recoder les fichiers v1.0 en v1.2 ; la variable exacte du motif reste à isoler (JUGEMENT-placement § 12).
   Mes mesures d'étage disque des compagnons (R120 2,30 Go/s, R20 2,47) s'ajoutent aux tables de 08.
3. **Le témoin décisif du lot A** (v1.0 et v1.2 réécrits le même jour) n'est plus nécessaire pour juger le
   format : ~~la séance à trois fichiers montre déjà, pour le 120b et le 20b, que l'écart suit le fichier
   (étage disque) et que le format ne rend que ses octets. Il reste utile au flux placement.~~ le motif croisé
   du juge du placement (même fichier lu aux deux motifs) a tranché, sans réécrire de fichier : l'écart suit le
   motif du format, pas le fichier (corrigé le 2026-10-27, JUGEMENT-placement § 5.3).
4. **Un autre corpus** (code, dialogue) pour la KL du génome synonyme, et **la mutation synonyme du 120b**
   (07 § 8, inchangé).
5. **Porter les recettes du § 10 dans RECETTES.md** (orchestrateur) et ce jugement dans le Tome III (note
   `construction-juge-pour-le-memoire.md`).
6. Les fichiers lourds du juge (`~/dev/essais/troncons/genome/juge/`, ≈ 13 Go de `.kld`) sont
   régénérables par les outils commités ; ils peuvent être effacés quand Stone le veut (la copie à biais
   retournés l'est déjà).
