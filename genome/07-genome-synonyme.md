# 07 · Le génome synonyme : la mutation synonyme sur les 768 experts, et le mode rapide du moteur

Construction de troncons, lot B (cahier : genome/05-synthese.md § 4.7 à 4.11), rôle « synonyme ».
Date : 2026-10-17. Étiquettes : **[mes.]** mesuré, outil et journal commités ; **[calc.]** calculé ;
**[litt.]** littérature ; **[hyp.]** hypothèse. Journaux : `mesures/genome/construction/synonyme/`
(seuils déclarés avant : `00-seuils-declares.md`). Outils : `outils/genome/synonyme/`.

> **État du document : complet au 2026-10-22** (écrit au fil des mesures du 2026-10-17 au 2026-10-22).
> Tout chiffre est mesuré et commité ; ce qui reste ouvert est au § 8.

---

## 0. En bref

1. **La mutation synonyme tient sur les 768 experts.** Avec **tous** les experts de gpt-oss-20b servis
   par leur base (référence f64, 10 fenêtres de R1 tenues à l'écart de la calibration) : λ = 1, KL
   **0,1522 ± 0,0062** contre **0,2640 ± 0,0066** pour la frontière (−42 %) ; différence appariée
   **−0,1118 ± 0,0296** (σ par fenêtres, 3,8 σ ; meilleure dans les 10 fenêtres) ; premier choix
   **67,5 %** contre 47,8 % ; perplexité 466,5 contre 460,2 pour le modèle exact [mes.]. Critère B2 (i),
   déclaré avant : **tient**.
2. **B2 entre les deux λ retient λ = 0, de justesse** (§ 4.2 quater) : KL **0,1318 ± 0,0055**, appariée
   contre λ = 1 **−0,0204 ± 0,0097** (d̄ + 2σ = −0,0009, 2,1 σ, neuf fenêtres sur dix), premier choix
   **69,9 %** ; contre la frontière −0,1322 ± 0,0234 (5,6 σ) [mes.]. Son prix : **2,6717 bits par poids**
   (compagnon réel) contre 2,5861 pour λ = 1 et 2,6593 pour la frontière ; fichier de 8,31 Go contre
   11,16 Go pour l'exact.
3. **Le mode rapide est dans le moteur**, exact à ses témoins : le compagnon se décode par le décodeur
   du mode exact (mêmes LUT), `gemv_base` lit les centres, `--rapide` le sert ; le moteur sur la carte
   et la référence f64 rendent le même modèle rapide (λ = 0 : KL 0,0038 entre eux, premier choix
   97,8 % ; λ = 1 : 0,0017, 98,2 %) ; le moteur rapide λ = 0 fait **0,1313** contre la référence exacte ;
   le mode exact est inchangé au bit [mes.].
4. ~~**La queue ne bouge pas**~~ *(barré le 2026-10-22 : vrai pour λ = 1 seulement)* : avec λ = 1, la
   médiane de la KL est divisée par 2,65 (0,163 → 0,061) et le 99,9e centile presque pas
   (4,07 → 3,93) ; **avec λ = 0, la queue baisse aussi** : 99e centile 1,457 → 1,081 (−26 %), 99,9e
   4,07 → 3,37 (−17 %). Sans contrainte d'entropie, la rétroaction atteint une part des positions qui
   basculent ; la queue restante reste celle des bascules de routage (05 § 2.2).
5. **La vitesse, machine calme, séances déclarées avant** (§ 4.4) : ~~20b ×**1,24** en génération
   (11,84 contre 9,54 jetons par seconde, σ 2,3 %) ; **120b ×2,00** (3,97 contre 1,98, σ 6,6 %, compagnon
   frontière) : gains annoncés par la règle.~~ *(barré par le juge comme gains du mode rapide,
   JUGEMENT-construction § 6 et § 7 G1, G2 : les rapports se redonnent, mais ils comparent un compagnon
   neuf au v1.0 du 15 octobre, que l'étage disque lit 1,31 à 1,39 fois moins vite à octets égaux ; contre
   le v1.2, que l'étage disque lit à la même vitesse que les compagnons, le mode rapide rend **×1,28 sur le 120b** et **×0,94 sur
   le 20b** en génération, ×1,12 et ×1,23 au préremplissage)* Sur le 120b, les octets lus par pas baissent de 34 % ;
   sur le 20b, ils ne baissent pas (textes différents, moins de succès en VRAM) et le gain vient d'un
   débit par octet plus haut, dont la cause ~~n'est pas éprouvée [mes. ; hyp. pour la cause]~~ est l'état
   physique du fichier v1.0 *(mesuré par le juge, JUGEMENT-construction § 6.3)*.
6. **Le 120b** a son mode rapide frontière (sans calibration) : 4 608 experts vérifiés, 56 671 décodés
   sur la carte sans erreur, et KL(moteur exact ‖ moteur rapide) **0,140**, premier choix 67,5 %, deux
   fois moins que la même base sur le 20b (0,265) ; ce proxy redonne la KL vraie à 0,002 près sur le
   20b [mes.]. La mutation synonyme du 120b n'est pas écrite (pas de calibration, pas de juge f64).
7. **Repère** : la seule requantification de llama.cpp sous 2,6 bits pour ces experts (Q2_0, 2,25
   bits) fait une KL de 1,597 et 13,6 % de premier choix.


---

## D'où on part, où on va

**Au départ** : la mutation synonyme (choisir le symbole de base de chaque poids par rétroaction
d'erreur pondérée par les entrées réelles, sous contrainte d'entropie) n'était mesurée que sur
**32 experts sur 768** : λ = 0 en KL (−0,0098 ± 0,0033 appariée contre la frontière), λ = 1 en erreur
de sortie d'expert seulement (01 § 5.4 ; 05 § 0, point 2). Aucun fichier, aucun noyau, aucune option
du moteur ne la servait.

**Ce que ce document établit** : la variante λ = 1, δ* = 1 écrite pour **les 768 experts** de
gpt-oss-20b, sa KL de bout en bout avec les 768 experts substitués, et **le mode rapide** dans le
moteur : un fichier compagnon `<nom>.rapide.trc` (même décodeur, autre table de valeurs), un noyau
`gemv_base`, une option `--rapide`, mesurés en KL et en jetons par seconde.

**Ce qui reste** : § 8.

---

## 1. Ce qui est construit

| Pièce | Fichier | Ce qu'elle fait | Témoin (déclaré avant) | Résultat |
|---|---|---|---|---|
| codage des 768 experts | `outils/genome/synonyme/coder_768.sh` → `synonyme.py ecrire-sym` (**code de l'éclaireur, inchangé**) | les symboles synonymes λ = 1, δ* = 1, et ceux de la frontière | W1 : refaire L00-E00 (λ = 0) rend le fichier de l'éclaireur octet pour octet ; cassure δ = 0,99 | **tient** (SHA-256 égales, 9079dcf1…) ; cassure : 117 501 symboles différents [mes., `codage/W1-reproduction.json`] |
| second chemin des symboles | `verifier_sym.py verifier` | relit les `.sym`, reconstruit, recalcule les erreurs publiées par l'éclaireur | W2 : égales au CSV de l'éclaireur à 1e-9 (16 experts, couches 0, 8, 16, 23) | **tient : écart relatif maximal 4,4e-16** ; cassure (un bit de classe sur une ligne) : 7,2e-3, tombe [mes., `codage/W2-*.json`] |
| noyau du mode rapide | `moteur/crates/trc-noyaux/noyaux/gemv.cuh` (`gemv_base`, lecteur de valeurs en paramètre) | y = Ŵ x + b, Ŵ = ±c_k · 2^(e−128), même ordre d'opérations que `gemv_mxfp4` | carte contre référence f64, cas exact par construction ; cassure : mode exact sur les mêmes octets ; mode exact avant et après | **0 ligne différente sur 2 880** ; cassure tombe ; mode exact identique au bit [mes., test `gemv_base_exacte_au_bit_et_mode_exact_inchange`] |
| drapeau RAPIDE | `moteur/crates/trc-format` (bit 5, v1.2) | marque le compagnon ; un lecteur plus ancien le refuse | refus sous 1.2, avec brut, avec canonique | **4 cas sur 4** [mes., test `drapeau_rapide_v12`] |
| empaqueteur | `outils/genome/synonyme/rapide` (`trc-rapide coder`) | fichier exact + `.sym` → compagnon | voir S3-T1 | voir § 4.3 |
| vérification du compagnon | `trc-rapide verifier` | seconde lecture : décodé = `.sym`, échelles et biais = exact, empreintes | S3-T1 ; cassure `--casser C X` | voir § 4.3 |
| option du moteur | `troncons … --rapide` (`Config::rapide`, centres de la table CENTRES posés dans `Noyaux::centres_rapides`) | sert le compagnon ; exigée comme `--brut` | un fichier rapide sans `--rapide` et un exact avec : refusés | **refusés tous deux, erreur nommée** [mes., `rapide/refus-*.log`] |

*Réponse par délégation du 2026-10-17, réversible* : le codage reprend le code de l'éclaireur **sans
modification**, en Python sur le processeur (≈ 54 s par expert seul, 3 à 6 processus en parallèle),
au lieu du codeur Rust sur la carte du cahier (B1c). Raison : c'est la seule voie qui rend
**exactement** la variante mesurée (W1 le prouve au bit), et le 20b tient en une demi-journée ; le
codeur sur la carte reste nécessaire pour le 120b (§ 5).

## 2. Le cœur du mécanisme, en une page

Pour une ligne w d'une matrice d'expert et H = E[g² x xᵀ]/E[g²] + δ* moy(diag H) I (entrées réelles
de calibration, fenêtres 10 à 21 de wiki.test, pondérées par le carré du poids du routeur), l'erreur
de sortie d'une reconstruction q est (w − q)ᵀ H (w − q) = Σ_k λ_k ((w − q)·u_k)² dans la base propre
de H. La mutation synonyme choisit, colonne après colonne, le symbole (signe, classe k) qui minimise
l'accroissement de cette erreur plus λ fois la longueur de code du symbole, et reporte l'erreur commise
sur les colonnes suivantes par le facteur de Cholesky de H⁻¹ (OBS/GPTQ). Le décodeur ne change pas :
mêmes 8 symboles, mêmes 4 centres, mêmes échelles. Dérivation entière : 01 § 5.2 ;
note pour le mémoire § 2.

**Ce que fait la transformation, vu sur une matrice** (L8, expert 0, gate ;
`figures/spectre-L08-E00-gate.csv`) [mes.] : l'énergie de l'erreur sur les poids **monte** de 20 %
(Σ_k ‖ΔW u_k‖² : 40,07 → 48,01), l'erreur de sortie **baisse** de 2,7 fois sur la calibration
(Σ_k λ_k ‖ΔW u_k‖² : 16,50 → 6,15) et de 1,57 fois vue par l'évaluation tenue à l'écart
(16,09 → 10,28). L'erreur est déplacée vers les directions que les entrées n'excitent pas ; l'écart
entre ÷2,7 et ÷1,57 est le sur-apprentissage qui reste à δ* = 1 (1 329 entrées de calibration en
dimension 2 880 pour cet expert).

## 3. Le compagnon `<nom>.rapide.trc`, au bit près

Un fichier `.trc` ordinaire (ARCHITECTURE § 4), avec ce qui suit ; tout le reste est le format exact.

| Élément | Valeur | Raison |
|---|---|---|
| version | 1.2 | le drapeau RAPIDE est défini en v1.2 |
| drapeaux | bit 0 ALIGNÉ + **bit 5 RAPIDE** ; bits 1 (niveaux), 2 (brut), 3 (canonique) refusés avec lui | un lecteur 1.0/1.1 refuse le fichier : le mode exact ne peut pas lire des symboles par erreur |
| MÉTA | les paires du GGUF (recopiées du fichier exact) + `troncons.rapide.codeur`, `.variante` (synonyme ou frontiere), `.exact` (empreinte64 de l'en-tête du fichier exact, en hexadécimal), `.partition` (0 0 1 1 1 2 2 3), `.centres`, `.lambda`, `.amortissement`, `.calibration` | provenance ; la vérification contrôle le lien `.exact` |
| RÉSIDENTS | recopiés octet pour octet du fichier exact | le compagnon se lit seul (écart au cahier, délégation ci-dessous) |
| TABLES | par (couche, matrice) : DELTA ctx 0, CODES_CTX ctx 0, 1, 2 (comptes des demi-octets de base sur les 32 experts), **CENTRES** ctx 0 (4 f32, grandeurs doublées) | même décodeur, mêmes LUT ; la GEMV lit les centres |
| tronçon | MEDIANES, BIAIS, DELTA, CODES_CTX × 3 matrices (12 flux, comme en v1.0) | les échelles et les biais sont ceux de l'expert exact |
| demi-octet | bit 3 le signe, bits 1-0 la classe k, bit 2 nul ; l'octet t d'un bloc porte la colonne 32b + t (faible) et 32b + 16 + t (fort) | disposition de `block_mxfp4` |
| valeur servie | ±c_k · 2^(e − 128), c = (0,474331, 2,848596, 6,837154, 12,0) en grandeurs doublées | `gemv_base` |
| RÉPERTOIRE, empreinte d'origine | empreinte64 de l'**expert rapide** (blocs `[e, demi-octets de base]`, puis biais) | le mode témoin du moteur la vérifie sans changement |

*Réponse par délégation du 2026-10-17, réversible* (trois écarts au cahier § 4.8, chacun pour ne
toucher aucun chemin du mode exact) : (1) sorte **CODES_CTX** au lieu de BASE_CTX : le décodeur de
la carte, ses LUT et sa grille restent ceux du mode exact, mot pour mot, et c'est le drapeau qui dit
que les demi-octets sont des symboles ; (2) résidents recopiés au lieu d'une section vide : le moteur
ouvre le compagnon comme tout fichier (coût : 1,9 Go de disque) ; (3) empreinte d'origine = expert
rapide (la provenance de l'expert exact est dans l'en-tête, SHA-256 du GGUF, et dans `.exact`).

## 4. Les mesures

### 4.1 Le repère de l'outil de référence (critère B2 (ii))

llama.cpp b11515 ne peut requantifier les experts de gpt-oss sous 2,6 bits qu'en **Q2_0** (2,25 bits
par poids, groupes de 64) : les k-quants et les IQ ont des super-blocs de 256 poids, que 2 880 ne
divise pas. Experts seuls requantifiés (le reste du GGUF inchangé : 6 979,93 Mio contre 11 536,18),
10 fenêtres de R1 sur le processeur, options de la base « processeur » de R0 [mes.,
`repere/kl-q2_0-juge.json`] :

| | KL contre la référence f64 | médiane | premier choix | perplexité (réf. 460,2) |
|---|---|---|---|---|
| llama.cpp, experts en Q2_0 (2,25 bits) | **1,597 ± 0,019** | 1,314 | 13,6 % | 881,2 |

C'est un repère faible : un arrondi au plus proche à 2 bits, sans matrice d'importance, détruit
presque le modèle.

### 4.2 La KL de bout en bout, 768 experts substitués (pas S2)

Protocole déclaré avant (`00-seuils-declares.md`) : référence f64 avec substitution
(`genome-capture kl --sub`), 10 fenêtres de R1 (2 550 positions, tenues à l'écart de la calibration),
`juge kl` contre `ref-openai-20b.kld`.

| Variante (768 experts) | KL | médiane | 99,9e centile | premier choix | perplexité |
|---|---|---|---|---|---|
| **frontière** (symbole = fonction du code) | **0,2640 ± 0,0066** | 0,163 | 4,07 | 47,8 % | 274,1 |
| **synonyme** λ = 1, δ* = 1 | **0,1522 ± 0,0062** | **0,0615** | 3,93 | **67,5 %** [65,6 ; 69,3] | **466,5** |

[mes., `kl/kl-frontiere-768-juge.json`, `kl/kl-synonyme-768-juge.json`]. Quantiles (frontière →
synonyme) : 90e centile 0,565 → 0,328 ; 99e 1,457 → 1,295 ; maximum 6,49 → 6,94.

**Appariée** (`kl/apparie-frontiere-contre-synonyme-768.json`, `apparier.py`) [calc. sur mes.] :
d̄ = KL_synonyme − KL_frontière = **−0,1118** ; σ naïf 0,0045 ; **σ par fenêtres 0,0296** ;
d̄ + 2σ = −0,052 < 0 : **meilleure significativement** (règle B2 (i), déclarée avant). Par fenêtre
(`kl/apparie-768-par-fenetre.csv`) : d de −0,036 (fenêtre 4) à −0,345 (fenêtre 7), **négative dans les
dix**. Premier choix apparié : +0,197 ± 0,011.

Témoins : substitués = lus (frontière 732 sur 732, synonyme 725 sur 725 ; les ensembles diffèrent
parce que le routage dépend des experts servis) ; KL du CSV = KL du juge à 3,5e-12 et 8e-12 relatifs
(seuil ~~1e-12 absolu~~ 1e-9 relatif, corrigé après une chute sans cause et dit dans les seuils) ;
cassure (une ligne retirée) tombe. Témoin des substitutions : ~~768 substitués~~ 732 experts
chargés, 732 substitués (36 experts ne sont routés par aucune des 2 550 positions ; le témoin déclaré
comptait des fichiers, le compteur compte des chargements : corrigé et dit dans le fichier des seuils).

**Ce que disent ces nombres.**
- Servir **tous** les experts par la base de la frontière fait une KL de 0,264, sept fois celle de
  32 experts substitués (0,036, protocole P1) : la KL croît moins vite que le nombre d'experts
  substitués (×24 d'experts, ×7 de KL), ce qu'on attend d'erreurs dont l'essentiel passe par des
  bascules de routage, qui saturent.
- La mutation synonyme garde son avantage relatif quand on passe de 32 à 768 experts : rapport à la
  frontière **0,727** à 32 experts (λ = 0, P1) et **0,576** à 768 experts (λ = 1). Le gain ne fond pas ;
  il grandit.
- La perplexité de la frontière **baisse** (274 contre 460) pendant que sa KL est la pire : sur un
  texte brut hors du format de conversation, une distribution déformée peut mieux prédire le jeton
  suivant que le modèle exact ; la perplexité n'est pas un juge de fidélité. Celle du synonyme reste
  à +1,4 % de l'exact (ln du rapport 0,013 ± 0,016) : le synonyme ne déforme pas la distribution dans
  une direction privilégiée.
- La part lisse et la queue (05 § 2.2) : médiane ÷2,65, 90e centile ÷1,72, 99e ÷1,12, 99,9e ÷1,04.
  Plus on va dans la queue, moins le synonyme y fait : ce sont les bascules de routage, que la
  pondération par les entrées d'un expert ne voit pas. La garde tropicale (05 § 3.1) est la pièce qui
  viserait cette queue.

### 4.2 bis B0 : λ = 1 contre λ = 0 sur le protocole de l'éclaireur (32 experts)

La mesure qui manquait d'abord au cahier (05 § 4.10, B0), faite ici **après** la passe à 768 experts
(les symboles λ = 1 des 32 experts de P1 sont un sous-ensemble des 768) [mes.,
`kl/B0-*.json`] :

| P1, 32 experts, 2 550 positions | KL | appariée contre la frontière | appariée contre λ = 0 | premier choix |
|---|---|---|---|---|
| frontière (éclaireur) | 0,0360 | — | | 87,1 % |
| synonyme λ = 0 (éclaireur) | 0,0262 | −0,0098 ± 0,0033 (meilleure) | — | 90,9 % |
| **synonyme λ = 1** (ici) | **0,0350** | **−0,0010 ± 0,0022 : égale** | **+0,0088 ± 0,0032 : pire (2,8 σ)** | 87,7 % |

**Ce que cela change.** À 32 experts, la contrainte d'entropie (λ = 1) rend presque tout le gain de
KL de λ = 0 contre ses 0,078 bit ; à 768 experts, λ = 1 bat la frontière de 42 %. Les deux faits ne
se contredisent pas (des experts différents, un régime de bascules différent), mais ils disent que la
comparaison décisive est **λ = 0 contre λ = 1 à 768 experts**, comme le prévoyait la règle B0 du
cahier. Elle est déclarée (`00-seuils-declares.md`, « B2 entre les deux λ ») et faite : § 4.2 quater.

### 4.2 quater B2 entre les deux λ, à 768 experts

Codage λ = 0, δ* = 1 des 768 experts (même outil, mêmes réglages ; 768 fichiers de 12 441 636 octets,
`codage/synonyme-l0-*.log`), puis la même passe KL que λ = 1 (2026-10-21, 1 554 s) [mes.,
`kl/kl-synonyme-l0-768-juge.json`, `kl/B2-synonyme-l1-contre-l0-768.json`] :

| 768 experts, 2 550 positions | KL | médiane | 99e centile | 99,9e centile | premier choix | perplexité (réf. 460,2) |
|---|---|---|---|---|---|---|
| frontière | 0,2640 ± 0,0066 | 0,163 | 1,457 | 4,07 | 47,8 % | 274,1 |
| synonyme λ = 1 | 0,1522 ± 0,0062 | 0,0615 | 1,295 | 3,93 | 67,5 % | 466,5 |
| **synonyme λ = 0** | **0,1318 ± 0,0055** | **0,0559** | **1,081** | **3,37** | **69,9 %** [68,1 ; 71,7] | 411,0 |

**Appariée, d = KL_{λ=0} − KL_{λ=1}** : d̄ = **−0,0204** ; σ par fenêtres **0,0097** ; d̄ + 2σ =
**−0,0009 < 0** : λ = 0 **meilleure**, par la règle déclarée avant, **de justesse** (2,09 σ). Par
fenêtre (`kl/apparie-l1-contre-l0-768-par-fenetre.csv`) : négative dans **9 fenêtres sur 10**, de −0,013
à −0,048 ; la fenêtre 7 va dans l'autre sens (+0,061 : 0,113 → 0,174). λ = 0 a moins de KL sur 1 706
positions sur 2 550. Premier choix apparié : +2,4 ± 0,8 points. Contre la frontière : −0,1322 ± 0,0234
(5,6 σ), premier choix +22,1 ± 1,1 points (`kl/apparie-frontiere-contre-synonyme-l0-768.json`).
Témoins : 729 experts substitués sur 729 lus ; KL du CSV = KL du juge à 5e-12 relatif (8e-12 pour λ = 1) ; cassure (une
ligne retirée) : tombe [mes.].

**Ce que cela change.** Par la règle, **λ = 0 devient la variante du mode rapide** (son compagnon est
écrit, § 4.3). Ce qu'elle coûte : les bits que λ = 1 économisait (0,07 bit par poids, mesuré au § 4.4
sur le compagnon réel). Ce qu'elle rend : 13 % de KL en moins, et ~~**la queue** : le 99e centile baisse
de 17 % et le 99,9e de 14 %~~ *(barré par le juge, JUGEMENT-construction § 5.4 et § 7 M2 : sur dix
fenêtres neuves, le 99e centile ne baisse que de 5 % et le 99,9e monte de 6 % ; un 99,9e centile de 2 550
positions tient à deux ou trois positions)*, là où λ = 1 ne gagnait presque rien sur la frontière. Le résultat de B0
(32 experts : λ = 0 meilleure, 2,8 σ) se retrouve à 768 experts, plus faible en relatif (−13 % contre
−25 %).

**La perplexité de λ = 0 descend** (411 contre 460 ; ln du rapport −0,113 ± 0,015), comme celle de la
frontière (274) et à l'opposé de λ = 1 (+1,4 %). La leçon du 05 tient : ce chiffre ne juge pas la
fidélité (une distribution moins fidèle peut mieux prédire un texte brut hors du format de
conversation), seule la KL juge ; ~~mais il dit que λ = 0 déforme la distribution dans une direction
privilégiée que λ = 1 ne prend pas [mes. ; pourquoi : non mesuré].~~ *(barré par le juge,
JUGEMENT-construction § 5.4 et § 7 M3 : sur dix fenêtres neuves, la perplexité de λ = 0 est à +2,4 % de
l'exact et celle de λ = 1 à +15,6 % ; le sens s'inverse avec le texte)*

### 4.2 ter Le débit des symboles sur les 72 tenseurs

`verifier_sym.py debit` (définitions de l'éclaireur, 01 § 5.3) [mes., `codage/debit-72-tenseurs.json`] :

| 72 tenseurs, 768 experts | H0 des symboles | H(symbole \| κ) |
|---|---|---|
| frontière | 2,6413 | 2,5992 |
| synonyme λ = 1 | **2,5683** (−0,0730) | **2,5275** (−0,0717) |

Par rôle (moyennes de H0, synonyme contre frontière) : gate 2,556 contre 2,645 (−0,089) ; **up 2,630
contre 2,643 (−0,013)** ; down 2,518 contre 2,635 (−0,117), avec −0,62, −0,46 et −0,35 bit sur les
down des couches 0, 1, 2. Le motif est celui des 12 tenseurs de l'éclaireur (up −0,003 à −0,017) :
la matrice up, qui voit les mêmes entrées que gate, ne cède presque pas de bits à λ = 1 [mes.] ;
pourquoi n'est pas mesuré [hyp. : l'erreur de la frontière de up, dans les unités de H, est petite
devant ses écarts de longueur de code, et c̄ normalise par elle]. Le codeur rANS réel du compagnon
rend 2,5861 bits par poids contre 2,6593 (−0,0733) : la même différence que l'entropie, biais f32,
échelles et médianes compris dans les deux.

### 4.3 Le mode rapide dans le moteur (pas S3)

**S3-T1, le fichier** (variante frontière, témoin) [mes., `rapide/verifier-frontiere*.json`] : 768
experts sur 768 vérifiés (demi-octets décodés = `.sym`, échelles et biais = exact, empreintes), lien
MÉTA tient ; cassure (L7 E13) : un expert faux, l'expert visé. **Tient.** Débit réel du compagnon
frontière : **2,6593 bits par poids d'expert** (octets utiles, biais f32 compris ; 2,6600 aligné),
fichier de 8 285 093 888 octets contre 11 157 405 696 pour le fichier exact v1.0
[mes., `rapide/coder-frontiere.json`].

**S3-T2, le moteur** : `troncons generer --rapide --temoin` sur le compagnon frontière, invite de la
série O4, 32 jetons : **5 856 experts décodés sur la carte, redescendus et vérifiés, 0 erreur** ; le
texte est cohérent [mes., `rapide/temoin-moteur-frontiere.*`].

**S3-K, les deux chemins du mode rapide** (frontière) : KL(référence f64 rapide ‖ moteur rapide) =
**0,00207**, premier choix identique **98,5 %** ; seuils déclarés 0,011 et 95 % : **tient**. Le moteur
sert le mode rapide aussi fidèlement qu'il sert le mode exact (0,00368, 97,2 % ; O, C4)
[mes., `moteur/S3K-capture-contre-moteur-frontiere.json`].

**KL du moteur rapide frontière contre la référence exacte** : 0,2626 (médiane 0,164, premier choix
47,6 %, perplexité 274,6), égale à celle de la référence f64 substituée (0,2640) à l'écart près des
deux chemins [mes., `moteur/kl-moteur-frontiere-juge.json`].

**Variante synonyme** [mes., `rapide/verifier-synonyme*.json`, `moteur/*synonyme*`] : S3-T1 tient
(768 experts, lien MÉTA ; cassure L19 E2 : un expert faux, le visé) ; KL du moteur rapide contre la
référence exacte **0,1522** (médiane 0,0618, premier choix 67,4 %, perplexité 467,7), égale à celle de
la référence f64 substituée ; S3-K : KL(réf. f64 rapide ‖ moteur rapide) **0,00171**, premier choix
**98,2 %** : **tient** ; cassure (réf. f64 **frontière** contre moteur **synonyme**) : 0,190, premier
choix 50,9 % : **tombe**, comme déclaré.

**Variante λ = 0, la variante du mode rapide depuis B2** (2026-10-22) [mes., `rapide/*synonyme-l0*`,
`moteur/*synonyme-l0*`] :
- compagnon : **2,6717 bits par poids d'expert** (octets utiles, biais compris), 8 314 617 856 octets
  (8,31 Go), 301 s ; c'est **+0,0124 bit sur la frontière** et +0,0856 sur λ = 1. Sans contrainte
  d'entropie, la rétroaction d'erreur choisit des symboles un peu moins prévisibles que la fonction du
  code : λ = 0 paie sa KL en bits, là où λ = 1 gagnait les deux à la fois contre la frontière ;
- S3-T1 tient (768 experts sur 768, lien MÉTA) ; cassure L11 E27 : un expert faux, le visé ;
- KL du moteur rapide (carte) contre la référence exacte : **0,1313** (médiane 0,0561, premier choix
  **69,7 %**, perplexité 410,9), égale à celle de la référence f64 substituée (0,1318) ;
- S3-K : KL(réf. f64 rapide λ = 0 ‖ moteur rapide λ = 0) **0,0038 ≤ 0,011**, premier choix identique
  **97,8 % ≥ 95 %** : **tient** ; cassure (réf. f64 frontière contre moteur λ = 0) : 0,149, premier choix
  55,0 % : **tombe**.

| Mode rapide servi par le moteur (20b, 768 experts) | bits par poids | fichier | KL contre la référence | premier choix | S3-K |
|---|---|---|---|---|---|
| frontière (témoin) | 2,6593 | 8,29 Go | 0,2626 | 47,6 % | 0,00207 |
| synonyme λ = 1 | **2,5861** | **8,11 Go** | 0,1522 | 67,4 % | 0,00171 |
| **synonyme λ = 0 (retenue par B2)** | 2,6717 | 8,31 Go | **0,1313** | **69,7 %** | 0,0038 |
| exact (v1.0) | 3,85 | 11,16 Go | 0,0037 (O, C4) | 97,2 % | — |

### 4.4 La vitesse (S3-V)

**Séance s1 (20b, A B B A A B B A, `vitesse/pilote-s1.json`) : publiée, non concluante.** Elle a tourné
pendant la passe KL B0 (6 fils), le calcul du débit et l'écriture du compagnon du 120b, qui lit
57 Go sur le même disque [mes.] :

| | passes A (exact v1.0) | passes B (rapide synonyme) |
|---|---|---|
| jetons par seconde | 2,64 · 2,47 · 3,18 · 3,61 | 3,43 · 3,49 · 3,36 · 3,39 |
| médiane | 2,91 | 3,41 |

Rapport médian B / A = 1,17 ; bruit des passes A σ = 17,8 % ; seuil d'annonce 1 + 2σ = 1,36 : **pas
de gain annoncé**. Le moteur exact tournait ici à 2,5-3,6 jetons par seconde contre 10,9 dans la série
O4 (machine libre) : la charge du disque domine. La séance se refait machine calme (s2).

**Séance s2 (20b, A B B A A B B A, 2026-10-22, 1 h 11 à 1 h 25 ; `vitesse/pilote-s2.json`)** [mes.] :
déclarée avant (seuils § « Séance s2 ») ; A le fichier exact v1.0, B le compagnon **λ = 0** (la variante
retenue par B2) ; la séance est partie sur deux relevés vides des autres flux, et **aucune passe** n'a
eu de charge avant ou après elle (le flux des pistes s'est mis en pause sur le verrou).

| | passes A (exact v1.0) | passes B (rapide λ = 0) |
|---|---|---|
| génération, jetons par seconde | 9,39 · 9,69 · 9,83 · 9,39 | 5,46 · 11,83 · 12,22 · 11,85 |
| médiane | 9,54 | 11,84 |
| préremplissage (708 jetons), jetons par seconde | 10,8 à 11,4 | 16,9 à 17,7 |

Bruit des passes A σ = **2,3 %** (contre 17,8 % en s1) ; rapport médian B / A = **1,241** ; seuil
d'annonce 1 + 2σ = 1,046 : **gain annoncé, ~~×1,24 en génération~~** (et ×1,57 en préremplissage, non
déclaré comme critère, publié). Le prédit au toit du disque était ×1,41 à ×1,45 (cahier § 4.7).
*(Barré par le juge comme gain du mode rapide, JUGEMENT-construction § 6.3, G2 : redonné dans une séance à
trois fichiers, R/A = 1,220 ; mais contre le v1.2 exact, que l'étage disque lit à la même vitesse que le compagnon, le mode
rapide λ = 0 rend **×0,94** en génération et ×1,23 au préremplissage.)*

**Ce que disent les compteurs du moteur, et qui retient d'en dire plus** [mes., `vitesse/s2-*.json`] :
- **les deux fichiers ne génèrent pas le même texte** (le mode rapide est avec perte) : empreintes
  des textes différentes, et le texte B part dans une boucle (« The article should be about 2000
  words » répété) là où A répond en prose. Les experts routés ne sont donc pas les mêmes ;
- **par pas de génération, les octets lus sont presque égaux** : 0,1164 Go (A) contre 0,1152 Go (B).
  B lit des experts plus petits (8,32 Mo contre 12,01 Mo) mais plus souvent : taux de succès en VRAM
  0,856 contre 0,899, 3 531 défauts contre 2 472 sur 255 pas ;
- le gain de la génération vient donc d'un **débit par octet plus haut** : 1,39 Go/s (B) contre
  1,12 Go/s (A). ~~*Hypothèse, non mesurée ici* : le cache de fichiers du système, qui garde une plus
  grande part d'un fichier de 8,3 Go que d'un fichier de 11,2 Go dans 16 Go de RAM ; la première passe
  B (5,46 j/s, juste après une passe A, cache froid pour B) va dans ce sens.~~ *(barré par le juge,
  JUGEMENT-construction § 6.3 : impossible, le moteur lit les tronçons sans tampon
  (`FILE_FLAG_NO_BUFFERING`) ; la cause mesurée est l'état physique du fichier v1.0, que l'étage disque lit
  1,39 fois moins vite que le compagnon, et 1,38 fois moins vite que le v1.2.)* Le témoin qui trancherait
  (même séance, cache vidé avant chaque passe, ou octets réellement lus du disque par passe) n'a pas
  été déclaré ; ~~il reste à faire~~ *(fait par le juge, sous une autre forme : la séance à trois fichiers)* ;
- au préremplissage, où le texte est l'invite (le même pour A et B), les octets suivent la taille des
  experts : 45,4 Go (B) contre 68,5 Go (A), rapport 0,663, et la vitesse ×1,57.

Le gain annoncé tient par la règle déclarée ; sa cause n'est pas celle que prédisait le cahier (moins
d'octets par jeton), et le chiffre ne se transporte pas tel quel à un autre texte.

**120b-V (A B B A A B B A, 2026-10-22, 2 h 34 à 3 h 38 ; `vitesse/pilote-s2-120b.json`)** [mes.] : A le
fichier exact `gpt-oss-120b.trc` (v1.0, 57,73 Go), B le compagnon frontière (40,45 Go) ; seuils du
§ 120b, déclarés avant ; mêmes règles de calme, **aucune passe sous charge**.

| | passes A (exact v1.0) | passes B (rapide frontière) |
|---|---|---|
| génération, jetons par seconde | 2,08 · 1,87 · 2,12 · 1,88 | 3,95 · 3,97 · 3,98 · 3,97 |
| médiane | 1,98 | 3,97 |
| préremplissage (708 jetons), jetons par seconde | 1,43 à 1,56 | 2,99 à 3,01 |
| octets lus par pas de génération | 0,707 Go | 0,464 Go |
| débit par octet en génération | 1,32 à 1,50 Go/s | 1,83 à 1,85 Go/s |
| succès en VRAM | 0,591 | 0,610 |

Bruit des passes A σ = 6,6 % ; rapport médian B / A = **2,00** ; seuil 1 + 2σ = 1,13 : **gain annoncé,
~~×2,00~~**, au-delà du prédit au toit du disque (×1,43 à ×1,46). Ici le 120b ne tient dans aucun cache :
les **octets par pas baissent** dans le rapport des tailles d'experts (0,656 ; 12,02 contre 8,27 Mo par
expert), ce qui rend ×1,52 ; le reste (×1,31) vient d'un débit par octet plus haut, que les compteurs
ne séparent pas [mes. ; cause du second facteur non mesurée]. *(Barré par le juge comme gain du mode
rapide, JUGEMENT-construction § 6.2, G1 : le ×1,31 est mesuré, c'est l'étage disque, qui lit le compagnon
1,31 fois plus vite que le v1.0 d'origine à octets égaux par lecture ; contre le v1.2, écrit le même jour
que le compagnon, le mode rapide frontière rend **×1,28** en génération, pour un toit des octets de ×1,47.)* Les textes diffèrent encore (empreintes
e4c6dbac… et 2cf1d474…), tous deux cohérents. Le B des quatre passes est d'une régularité remarquable
(0,8 % entre la plus lente et la plus rapide) quand l'exact varie de 13 %.


## 5. Le 120b

**Pourquoi la mutation synonyme n'est pas écrite pour le 120b dans ce travail** [calc. sur mes.] :
1. *Aucune entrée de calibration* : les captures de l'éclaireur sont celles du 20b. Il faudrait la
   passe de capture de la référence f64 sur le 120b (36 couches, 128 experts ; celle du 20b a pris
   1 966 s pour 12 fenêtres et 9,95 Go d'experts lus, `capture.json`).
2. *Le codage* : 4 608 experts. Le codeur Python coûte ≈ 54 s par expert seul (mesuré ici, W1 ; les
   matrices du 120b ont les mêmes dimensions, 2 880 × 2 880) : ≈ 69 h sur un processus, ≈ 23 h avec
   le gain de parallélisme vu sur le 20b (≈ ×3). C'est le cas pour lequel le cahier prévoit le
   codeur Rust sur la carte (B1c, 05 § 4.9 : de l'ordre de la dizaine de millisecondes par matrice
   pour la rétroaction).
3. *Aucun juge* : la référence f64 du 120b sur les 10 fenêtres n'existe pas (épreuve J1, « ce qui
   manque ») ; sans elle, pas de KL de bout en bout.

**Ce qui se mesure quand même** (seuils déclarés avant, `00-seuils-declares.md` § 120b) : le compagnon
**frontière** du 120b (symbole = fonction du code, `--symboles frontiere-directe`, sans calibration),
qui a la taille du mode rapide à 0,07 bit près, donc sa vitesse ; et la KL du moteur rapide contre le
moteur exact, comme proxy de qualité. Mesurés le 2026-10-22 :

- **120b-T1** (2026-10-17) : 4 607 experts justes sur 4 608 dans la passe à cassure, le seul faux est le
  visé (L30 E77), lien MÉTA tient [mes., `rapide/verifier-frontiere-120b-casse.json`].
- **120b-T2 tient** : `troncons generer --rapide --temoin`, invite de la série O4, 32 jetons :
  **56 671 experts décodés sur la carte, redescendus et vérifiés, 0 erreur** (code 0), texte cohérent ;
  471 Go lus en 2 010 s (le mode témoin redescend chaque expert : ce n'est pas une vitesse)
  [mes., `rapide/temoin-moteur-frontiere-120b.*`].
- **Le proxy, validé d'abord sur le 20b** [mes., `proxy/`] : le moteur exact du 20b contre la
  référence f64 redonne O, C4 au dernier chiffre (0,00368 ± 0,00046, premier choix 97,18 %) ; et
  KL(moteur exact ‖ moteur rapide) égale la KL contre la référence f64 à 0,002 près :

  | 20b, 768 experts | KL(moteur exact ‖ moteur rapide) | KL(réf. f64 ‖ moteur rapide) |
  |---|---|---|
  | frontière | 0,2645 | 0,2626 |
  | synonyme λ = 1 | 0,1533 | 0,1522 |
  | synonyme λ = 0 | 0,1331 | 0,1313 |

  L'écart du moteur exact à la référence (0,0037) est petit devant les KL du mode rapide : le proxy
  les mesure à 1,5 % près.
- **Sur le 120b** (10 fenêtres de R1, `--flux` comme l'épreuve J1) : KL(moteur exact ‖ moteur rapide
  frontière) = **0,1404 ± 0,0042** (médiane 0,084 ; 99e centile 0,98 ; 99,9e 2,22), premier choix
  **67,5 %**, perplexité 401,4 contre 422,2 pour le moteur exact. Témoins : le moteur exact du 120b rend
  l'empreinte de CSV de l'épreuve J1 (a80f5f04…9498) et sa perplexité (422,21) ; exact contre exact : 0.
  **La même base frontière coûte deux fois moins de KL au 120b qu'au 20b** (0,140 contre 0,265) : plus
  d'experts (128 contre 32, 4 routés sur 128 contre 4 sur 32), et une part plus petite de chaque sortie
  passe par un expert donné [hyp., non mesurée]. Si le rapport synonyme sur frontière du 20b (0,50 pour
  λ = 0) se transportait, le synonyme du 120b serait vers 0,07 ; c'est une extrapolation, pas une mesure.


## 6. Ce qui pourrait être faux

- **Les témoins de substitution** : le premier témoin déclaré (768) était mal posé ; corrigé après
  coup (substitués = lus). Les 36 experts non routés ne sont jugés par aucune KL de ces fenêtres.
- **Le repère llama.cpp** est faible (Q2_0 sans matrice d'importance) ; une requantification
  meilleure à ≤ 2,6 bits n'existe pas dans b11515 pour des lignes de 2 880.
- **La perplexité baisse** avec la base : elle ne mesure pas la fidélité ici.
- **B2 entre les deux λ se joue de justesse** (d̄ + 2σ = −0,0009, 2,09 σ, une fenêtre sur dix contre) :
  avec dix fenêtres, σ par fenêtres est lui-même incertain d'environ 24 % (1/√(2·9)) ; une autre série
  de fenêtres pourrait rendre « égales », et la règle déclarée garderait alors λ = 1 (moins de bits).
  Le choix de λ = 0 est celui de la règle, pas une certitude ; λ = 1 reste écrit, vérifié et servi.
- **La perplexité de λ = 0 descend** (411 contre 460) : comme celle de la frontière, elle dit une
  déformation dans une direction ; la KL plus basse dit que cette déformation est plus petite que celle
  de λ = 1, pas qu'elle est sans biais.
- **La vitesse s2** compare des passes qui ne génèrent pas le même texte ; le gain ×1,24 tient par la
  règle, sa cause (cache de fichiers du système) est une hypothèse non éprouvée par un témoin. Sur une
  machine où le fichier exact tiendrait tout entier en cache, le gain pourrait disparaître ; sur une
  machine où aucun ne tient, il pourrait monter vers le prédit au toit du disque (×1,41).
- **Les 36 à 39 experts non routés** par les 2 550 positions (729 à 732 chargés sur 768) ne sont jugés
  par aucune KL ; leurs fichiers sont vérifiés (S3-T1), pas leur qualité.
- **Le 120b** n'a que la frontière (sans calibration) ; son proxy de qualité est une KL entre deux
  sorties du moteur, sans la référence f64.

## 7. Recettes (pour RECETTES.md)

- **Paramétrer le lecteur des valeurs de la GEMV** (template) plutôt qu'écrire un second noyau :
  le mode rapide coûte 40 lignes, et le mode exact garde ses fmaf au bit (témoin de carte). Marche.
- **Garder la sorte de flux du mode exact pour le compagnon** : le décodeur de la carte sert les
  deux fichiers sans une ligne de plus ; c'est le drapeau d'en-tête qui porte le sens. Marche.
- **Reproduire d'abord un fichier publié avant de lancer 768 experts** (W1) : 54 s, et la certitude
  que la variante produite est celle qui a été mesurée. Marche.
- **llama-quantize sur gpt-oss** : sous 4 bits, seuls Q2_0 et Q1_0 passent (super-blocs de 256
  contre 2 880 colonnes) ; Q2_0 à 2,25 bits fait une KL de 1,6. Échoue comme repère fort.
- **Un témoin de compteur se déclare sur ce que le compteur compte** : « 768 substitués » tombait
  pour une raison sans rapport avec la substitution.
- **Une séance de vitesse ne part que sur une machine calme relevée** (deux relevés vides des autres
  flux à une minute d'écart, relevé avant et après chaque passe, verrou qui annonce « vitesse » pour
  que les flux lents se mettent en pause) : σ des passes A tombe de 17,8 % (s1, sous charge) à 2,3 %
  (s2). Marche.
- **Lire les compteurs du moteur avant d'expliquer un gain de vitesse** : sur le 20b, ×1,24 sans
  baisse des octets par pas (textes différents, moins de succès en VRAM) ; sans les compteurs, on
  l'aurait attribué à la taille des experts. Marche (comme méthode) ; la cause reste ouverte.
- **λ = 1 contre λ = 0 se départage à 768 experts, pas à 32** : à 32 experts λ = 1 égalait la frontière,
  à 768 il la bat de 42 % ; λ = 0 bat λ = 1 aux deux échelles, de moins en moins (−25 % puis −13 %).
  Une variante jugée sur 32 experts sur 768 ne se juge pas.
- **Valider un proxy de qualité là où le vrai juge existe** (20b : KL moteur exact contre rapide égale
  la KL contre la référence f64 à 0,002 près) avant de le publier là où il n'existe pas (120b). Marche.

## 8. Ce qui reste

1. **La mutation synonyme du 120b** : il lui faut la passe de capture de la référence f64 sur le 120b
   (entrées de calibration, 36 couches, 128 experts) et le codeur sur la carte (B1c du cahier, 05 § 4.9),
   le codeur Python coûtant ≈ 23 h ; puis la même KL de bout en bout, avec la référence f64 du 120b sur
   les 10 fenêtres (épreuve J1, « ce qui manque »). Prédit, non mesuré : vers 0,07 de KL si le rapport du
   20b se transporte.
2. **La cause du gain de vitesse du 20b** : une séance déclarée avec le cache de fichiers du système
   vidé (ou mesuré) avant chaque passe, et les octets réellement lus du disque par passe ; et une
   séance à texte imposé (même suite de jetons forcée pour A et B) pour séparer l'effet du routage.
3. **B2 de justesse** : une seconde série de fenêtres tenues à l'écart (autres que R1) départagerait
   λ = 0 et λ = 1 avec plus de puissance ; tant qu'elle n'est pas faite, les deux compagnons restent
   écrits et servis.
4. **La queue de la KL** (99,9e centile 3,37 avec λ = 0) : ce sont les bascules de routage ; la garde
   tropicale (05 § 3.1) est la pièce qui la viserait. Le flux « pistes » en a rendu un premier verdict
   (commit 77d8110 : elle tombe au seuil déclaré) ; à relire avant tout couplage avec le mode rapide.
5. **Le mémoire** : figures F-S1 à F-S8 (note `construction-synonyme-pour-le-memoire.md`), CSV commités.
6. **Le juge** du flux de construction relit ce document (consigne du flux).

