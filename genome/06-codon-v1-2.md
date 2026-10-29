# 06 · Le codon synonyme du zéro dans le moteur : le format `.trc` v1.2

Construction de troncons, lot A (« codon »), d'après le cahier de genome/05-synthese.md §§ 4.1 à 4.6.
Date : 2026-10-17. Étiquettes : **[mes.]** mesuré, outil et journal commités ; **[calc.]** calculé par
un outil commité ou posé ici pas à pas ; **[litt.]** littérature, non reproduite ; **[hyp.]** hypothèse
dite. Outils : `outils/genome/construction/codon/` ; journaux : `mesures/genome/construction/codon/`.

La consigne de Stone pour cette étape, le 2026-10-17 : « vu qu'on a les conclusions je propose
d'avancer avec ce qu'on a on a déja pris beaucoup de temps ». Aucune recherche neuve : on porte dans le
moteur le gagnant sans perte mesuré par l'équipe prédictif-élagage, et on le mesure de bout en bout.

---

## 0. En bref

1. **Le codon synonyme du zéro est dans le moteur.** Format `.trc` **v1.2** (ARCHITECTURE § 4.16) : un
   drapeau (bit 3 CANONIQUE), une empreinte de plus par expert (l'expert canonique, au décalage 56 du
   répertoire), des tables CODES_CTX bâties sur les codes canoniques et vérifiées à l'ouverture (aucune
   fente pour les 31 octets qui portent un demi-octet 8). **Le décodeur de la carte et la GEMV n'ont pas
   une ligne de changée** : un flux v1.2 est un flux v1.0 dont l'alphabet effectif a 225 octets. Le
   moteur lit v1.0, v1.1 (en-tête) et v1.2 ; 82 essais de l'espace verts ; chaque témoin neuf tombe quand
   on le casse.
2. **Tous les lecteurs lisent le code 8 comme 0** [mes.] : ggml (table int8, 0 pour le code 8, lue à la
   source), la GEMV de la carte (8 640 lignes, 2 486 216 −0 fondus, **0 bit différent**, sommes non
   exactes, zéros des deux signes en entrée), la référence f64 (en valeur et au bit).
3. **Les deux modèles recodés** [mes.] : gpt-oss-20b **11 157 405 696 → 10 851 844 096 octets**,
   gpt-oss-120b **57 730 662 400 → 55 930 175 488** (**1 800 486 912 octets de moins**, 0,12562 bit par
   poids d'expert ; A-C2 ≥ 0,12 tient sur les deux) ; **C1 en valeur : 768 + 4 608 experts sur 5 376
   exacts**, huit contrôles à zéro faute, deux cassures qui trouvent exactement l'expert visé.
4. **Le théorème se vérifie tenseur par tenseur** [calc. sur mes.] : le gain vaut 2 × (part des −0) à
   ±0,00017 bit sur les 180 tenseurs : le signe d'un zéro est une pièce juste que rien ne prédit, et le
   rANS en récupère le bit entier.
5. **Logits identiques au bit** [mes.] : 5 120 pas sur 5 120, sur le 20b et sur le 120b ; `.kld` égaux
   octet pour octet ; sur le 120b, le v1.2 par le préremplissage par flux et le programme d'aujourd'hui
   rend les bits du v1.0 par la boucle de pas et le programme du 15 octobre.
6. **J1 sur le 120b** [mes.], séance s2 sur une machine calme (nuit du 21 au 22 octobre, aucune passe
   sous charge) : 256 jetons égaux dans les seize passes ABBA (et égaux au texte des 15 et 16 octobre) ;
   **octets de tronçons par jeton × 0,9671** (prédit 0,967) ; mémoire de pointe **−6,45 Mo** ; **2,89 contre
   1,99 jetons/s, r = 1,454 pour σ = 5,6 % : gain annoncé au seuil déclaré, pour les fichiers**. ~~Mais ce
   gain **n'est pas celui du format** : deux fichiers v1.0 **identiques au bit** se lisent à 1,74 et
   1,34 Go/s à l'étage disque seul (et rendent 1,99 et 1,81 jetons/s) ; la disposition physique d'un
   fichier sur ce NVMe déplace la vitesse de 30 % à contenu égal. La part du format est bornée par le
   rapport des octets : **au plus +3,4 %** à disque limitant. Le témoin décisif (v1.0 et v1.2 réécrits le
   même jour) reste à faire (§ 8, § 12).~~ **Corrigé le 2026-10-27**, d'après `genome/JUGEMENT-placement.md` (§ 0, §§ 5.3, 5.6, 5.7, § 12 point 3) : sur ce disque, l'écart B/A suit **le motif des requêtes de lecture que le format impose** (frontières et longueurs des tronçons) : A lu au motif de B va comme B (×1,389), B lu au motif de A va comme A (×0,715). Le gain du J1 est donc **un gain du format v1.2, propre à cette machine**, par le motif de ses tronçons et non par ses 3,3 % d'octets ; la variable exacte du motif n'est pas isolée (couper chaque requête du v1.0 en deux ne le répare pas : ×0,851 et ×0,882). Le v1.0 recodé, au même contenu que
   l'origine, est plus lent pour une autre raison : sa fragmentation extrême (267 473 extents), qui coûte
   ×1,26 au chemin du moteur. La séance s1 (sous charge, σ = 21,6 %) ne concluait pas.
7. **Hors de la v1.2, chiffré** : le contexte de la colonne d'entrée (0,0037 bit par poids sur le 20b
   entier, 8,8 Mo, contre un noyau neuf) ; réponse par délégation, réversible (§ 2).

---

## D'où on part, où on va

**Au départ** (fichiers commités) : le moteur du Tome II lit le format `.trc` **v1.0** (un niveau, flux
CODES_CTX à table par voie) ; les deux fichiers de la machine sont en v1.0 (relevé des octets 8 à 15 de
l'en-tête : version 1.0, drapeaux = 1), 11 157 405 696 octets (20b) et 57 730 662 400 octets (120b).
L'équipe prédictif-élagage a mesuré, par des flux rANS réels décodés jusqu'au retour des voies à L,
que fondre le demi-octet 8 (−0) dans le demi-octet 0 fait passer le 120b de **3,8549 à 3,7292 bits par
poids** d'expert et le 20b de 3,8509 à 3,7230 (`mesures/genome/predictif-elagage/taux-reel-toutes-
gptoss{120b,20b}.json`) [mes. de cette équipe]. La synthèse (05 § 4.2) a démontré que la GEMV du moteur
rend les mêmes bits sur les deux codes (proposition A1).

**Une précision sur la consigne, dite et non corrigée en silence.** La consigne parle de « v1.1 » pour
les fichiers actuels et demande que le moteur lise « v1.1 et v1.2 ». Les fichiers actuels sont en
**v1.0** ; la v1.1 (deux niveaux, la base de B et son complément, ARCHITECTURE § 4.15) est réservée et
n'est écrite par aucun codeur (`trc-codec` la refuse : « étape F4 (J2), pas encore écrite »). Le
lecteur de `trc-format` acceptait déjà les en-têtes jusqu'à 1.1 ; il accepte maintenant jusqu'à 1.2.
Toutes les comparaisons de ce document opposent donc **v1.2 à v1.0**, comme le cahier (05 § 4.6).

**Ce que ce document établit** : (1) que tous les lecteurs de codes du projet lisent le code 8 comme
0, comme ggml ; (2) le format v1.2, son code et ses témoins ; (3) les deux fichiers recodés, vérifiés
expert par expert, et le gain de taille sur le disque ; (4) les logits identiques au bit et le jalon J1
refait sur le 120b en v1.2 contre v1.0, en séries ABBA.

**Ce qui reste** : voir § 9.

---

## 1. Vérification 1 : qui lit le code 8, et comment

Le codon synonyme n'est sans perte que si **chaque lecteur** de codes donne au code 8 la valeur 0.
Relevé exhaustif dans le dépôt (recherche de `e2m1`, `kvalues`, `& 8`, `& 7` dans `moteur/`) :

| Lecteur | Où | Valeur du code 8 | Statut |
|---|---|---|---|
| ggml (llama.cpp b11515) | `ggml/src/ggml-common.h`, l. 1124 à 1129 : `kvalues_fp4` (int8) `0, 1, 2, 3, 4, 6, 8, 12, 0, −1, −2, −3, −4, −6, −8, −12`, et `#define kvalues_mxfp4 kvalues_fp4` | **0** (entier) | [litt.] lu à la source le 2026-10-17, https://raw.githubusercontent.com/ggml-org/llama.cpp/b11515/ggml/src/ggml-common.h, SHA-256 du fichier 0061131b615c5721fc88a78feeb22c1f8c450f1c2646a317d80796a653bf595c ; licence MIT |
| GEMV du moteur | `trc-noyaux/noyaux/gemv.cuh`, `valeur_e2m1x2` (l. 33) | −0.0f (signe par le bit 3) | seul lecteur des valeurs dans les noyaux (les autres noyaux de `passe.cuh` lisent du Q8_0 et du F32) |
| décodeur CUDA | `decodeur.cuh` | ne lit pas les valeurs : il recopie des octets | indifférent au codon |
| référence f64 | `trc-reference/src/poids.rs`, `K_MXFP4[8]` (l. 24) | −0.0 (f64) | lit le GGUF, pas le `.trc` |
| bancs et témoins | `banc_k.cu` l. 1049, `tests/carte.rs` l. 379 | `(code & 8) ? −v : v`, donc −0 | témoins seulement |

**−0 et +0 ont la même valeur** (IEEE 754 : −0 == +0). La seule question est donc celle des **bits**
d'une somme où un terme passe de −0 à +0. La proposition A1 (05 § 4.2) y répond pour la GEMV ; elle se
mesure ici par deux chemins.

**Mesure sur la carte** [mes.] : `trc-noyaux/tests/carte.rs::gemv_lit_le_code_8_comme_0`. Un expert
synthétique aux dimensions de gpt-oss (trois matrices 2 880 × 2 880), dont le signe est tiré pour toute
grandeur, la grandeur 0 comprise, porte **2 486 216 demi-octets 8** ; on le compare à sa copie
canonisée. Les x sont quelconques : mantisses pleines, exposants de 2⁻¹⁰ à 2¹⁰, un x sur 97 à +0 et un
sur 97 à −0 (le cas qui exerce le pas (2) de la démonstration), sommes **non exactes** en f32. Résultat :
**8 640 lignes, 0 différente au bit**. Cassure : un code 0 de la copie, en face d'un x non nul, mis à 1
→ la ligne 0 diffère (l'instrument peut tomber).

**Mesure sur la référence f64** [mes.] : `trc-reference/tests/code_8.rs`. Une matrice MXFP4 de 64 × 2 880
(un tiers des grandeurs à 0, signe tiré), sa copie canonisée : (1) chaque poids déquantifié égal **en
valeur** ; (2) les sorties de `Matrice::produit` (huit accumulateurs partis de +0, FMA, réduction en
arbre fixe) **égales au bit** sur 5 vecteurs, zéros des deux signes compris. Cassure : un code 0 changé
en 1 → la sortie change. La référence lit le GGUF : elle n'est pas touchée par le format ; ce témoin
établit seulement qu'elle aussi donne au code 8 la valeur de ggml.

**Pourquoi la référence rend aussi les mêmes bits** [calc.] : chacun des huit accumulateurs part de
+0,0 et avance par `acc ← RN(a·b + acc)` (FMA). C'est la récurrence de A1 avec un f64 au lieu d'un f32 :
un accumulateur ne vaut jamais −0 (une somme exacte nulle de termes qui ne sont pas tous deux −0 rend +0
en arrondi au plus près), et un pas sur un poids ±0 laisse l'accumulateur inchangé. La réduction finale
additionne des accumulateurs égaux au bit.

**Invariant écrit** (ARCHITECTURE § 5.6, ajouté par ce lot) : tout lecteur de codes lit le code 8 comme
zéro ; tout noyau neuf qui lit des codes (préremplissage par lots, GEMM) le garde, et son témoin compare
un expert à sa copie canonisée.

---

## 2. Le format `.trc` v1.2, au bit près

La décision est écrite dans ARCHITECTURE § 4.16 (couture F : toute modification du format passe par
ce document). Ce qui change, et rien d'autre :

| Où | Décalage | v1.0 | v1.2 |
|---|---|---|---|
| en-tête, version mineure | 10 (u16) | 0 | **2** |
| en-tête, drapeaux | 12 (u32) | bit 0 (aligné) ; bit 1 (niveaux) ; bit 2 (brut) | + **bit 3 CANONIQUE** |
| répertoire, chaque entrée | 56 (u64) | réservé, 0 | **`empreinte_canonique`** : empreinte64 de l'expert canonique |
| tables CODES_CTX | — | 256 fréquences | les mêmes, construites sur les codes canoniques ; **invariant vérifié à l'ouverture** : fréquence 0 pour les 31 octets qui portent un demi-octet 8 |

**L'expert canonique** : la suite d'octets de l'expert d'origine (ARCHITECTURE § 4.11 : pour j = 0, 1, 2,
les R·B blocs de 17 octets `[e, qs]` dans l'ordre β, puis les biais), où chaque demi-octet 8 des `qs`
est remplacé par 0. Les échelles et les biais ne changent pas. L'empreinte d'origine (décalage 24) reste
celle des octets du GGUF : un fichier v1.2 garde la preuve de sa provenance.

**Les refus** (`trc-format`, chacun témoin et cassure dans `tests/aller_retour.rs`) :
- bit 3 sous une version mineure < 2 (`Drapeaux`) ;
- bit 3 sur un fichier brut (bit 2 ; le chemin de référence des témoins C3 et C12 garde les octets du
  GGUF tels quels) ou à deux niveaux (la v1.2 ne définit pas la forme canonique de BASE_CTX et
  COMPL_CTX) ;
- `empreinte_canonique` non nulle sans le bit 3 (`Limites`) ;
- une table CODES_CTX d'un fichier canonique qui donne une fente à un octet portant un 8 (`Champ`) ;
- bit 4 (le COLONNES du cahier, hors v1.2) et toute version 1.3 ou plus.

**Pourquoi l'invariant des tables suffit à garantir « aucun 8 »** [calc.] : le décodeur rANS (§ 4.9.2)
ne peut rendre que le symbole s d'une fente i ∈ [c[s], c[s] + f[s]) ; un symbole de fréquence 0 n'a
aucune fente, donc aucun flux, même corrompu, ne le produit. Le contrôle porte sur les tables, que le
processeur et la carte montent toutes deux depuis la même section TABLES ; il coûte 36 × 3 × 3 × 31
lectures à l'ouverture du 120b.

**Ce qui ne change pas** : la sérialisation des flux, le décodage normatif, les noyaux du décodeur, la
taille des tables (3 × 512 octets par matrice), le format des parties. Un flux v1.2 **est** un flux
v1.0 dont l'alphabet effectif a 225 octets au lieu de 256. C'est pourquoi le décodeur de la carte n'a
pas une ligne de changée, et pourquoi le risque du lot tient dans le codeur, le vérificateur et le
témoin du moteur.

**Le contexte de la colonne d'entrée reste hors de la v1.2** (réponse par délégation du 2026-10-17,
réversible ; raison en une ligne : le gain ne paie pas le risque). La consigne dit « et le contexte de
colonne s'il tient dans le format sans risque ». Chiffré depuis `colonne-par-tenseur.csv` (synthèse)
[calc. sur mes.] : sur les 12 tenseurs mesurés du 20b, seules les matrices gate et up de la couche 0
passent le seuil de 0,015 bit par poids du cahier (−0,1416 et −0,1231 bit) ; les couches 8 et 23 rendent
de 0,005 à 0,010 bit, la couche 16 rien. Rapporté au modèle entier (24 couches × 3 matrices de
265 420 800 poids) : (0,1416 + 0,1231) × 265 420 800 / 19 110 297 600 = **0,0037 bit par poids**, soit
(0,2647 × 265 420 800) / 8 ≈ **8,8 Mo** sur 11,2 Go (0,08 %). Le prix : une sorte de flux neuve
(géométrie 2, douze contextes par symbole), un noyau de décodage neuf avec sa LUT compacte (12 LUT
normatives = 192 Kio, au-delà des 99 Kio de mémoire partagée d'un bloc), un montage de LUT neuf dans
l'ordonnanceur, un second décodeur indépendant à étendre, et un décodage 2,5 fois plus cher sur les
matrices concernées (05 § 4.4). Le cahier de 05 §§ 4.3 et 4.4 reste la spécification si un modèle à
canaux aberrants plus nombreux le fait payer.

---

## 3. Ce qui a été écrit, fichier par fichier

| Fichier | Ce qui change |
|---|---|
| `decisions/ARCHITECTURE.md` | § 4.15 (la v1.2 dans la liste des versions), § 4.16 (la décision), § 5.6 (l'invariant du code 8) |
| `moteur/crates/trc-format/src/lib.rs` | `VERSION_MINEURE = 2`, `VERSION_MINEURE_CANONIQUE`, `DRAPEAU_CANONIQUE = 8` ; `canoniser_demi`, `canoniser_octet`, `porte_un_8` ; `Entete::est_canonique` ; refus du bit 3 ; `EntreeRepertoire::empreinte_canonique` (décalage 56) et `empreinte_du_decode(canonique)` ; `verifier_tables_canoniques` à l'ouverture ; contrôle « 0 sans le drapeau » |
| `moteur/crates/trc-format/tests/aller_retour.rs` | `aller_retour_v12_canonique`, `cassures_v12_refusees` (sept refus nommés, deux acceptations témoins) |
| `moteur/crates/trc-codec/src/lib.rs` | `canoniser_qs` (rend le nombre de −0 fondus), `blocs_canoniques`, `preparer_matrice_avec(…, canonique)` ; le codage et le décodage sont ceux de la v1.0 |
| `moteur/crates/trc-codec/tests/rans.rs` | `matrice_canonique_se_reconstruit_et_gagne` |
| `moteur/bins/trc-codeur/src/coder.rs`, `main.rs` | option `--canonique` (exclusive de `--brut`) : comptes et codage sur les codes canoniques, deux empreintes par expert, version 1.2 et bit 3 ; journal : −0 fondus par (couche, matrice) |
| `moteur/bins/trc-codeur/src/verifier.rs`, `main.rs` | sur un fichier canonique : décodé contre tranches du GGUF **canonisées par un second chemin**, empreinte du décodé contre la canonique, empreinte des tranches brutes contre l'origine, empreinte des tranches canonisées contre la canonique, absence de 8, **égalité en valeur** de chaque poids ; cassure `--casser-8` |
| `moteur/crates/trc-ordo/src/lib.rs` | mode témoin : `empreinte_du_decode(canonique)` aux deux endroits (boucle de pas et préremplissage par flux) |
| `moteur/bins/banc-chemin/src/essai_e2.rs` | idem pour le banc E2 |
| `moteur/crates/trc-noyaux/tests/carte.rs` | `gemv_lit_le_code_8_comme_0` (A1 sur la carte) |
| `moteur/crates/trc-reference/tests/code_8.rs` | la référence f64 et le code 8 |

Le décodeur CUDA (`decodeur.cuh`, `commun.cuh`, `abi.rs`) et la GEMV ne changent pas.

**Les essais de l'espace de travail** [mes.] : `cargo test --offline --workspace` sous le verrou de la
carte, **82 essais, 0 échec** (`mesures/genome/construction/codon/essais-espace-2026-10-17-a.log`).
**Les témoins neufs tombent quand on les casse** [mes.] (`tests-casses.txt`) : contrôle des tables
canoniques retiré → `cassures_v12_refusees` échoue ; contrôle « empreinte canonique nulle sans
drapeau » retiré → échoue ; bit 3 accepté sous la v1.1 → deux essais échouent ; `canoniser_qs` rendu
sans effet → `matrice_canonique_se_reconstruit_et_gagne` échoue.

**Le codeur sans `--canonique` écrit toujours la v1.0 octet pour octet** [mes.] : le 20b recodé par le
codeur modifié a la SHA-256 e8bd6ae13288344d0ab29b70dd311e0045769624651b56e943ca39a878c7169f (Get-FileHash,
chemin indépendant), celle de `gpt-oss-20b.trc` relevée par le lot F le 2026-10-15
(`mesures/moteur/F/journaux/identite-20b-2passes.txt`) ; `journaux/recoder.log`. La copie a ensuite été
retirée.

---

## 4. Critères, déclarés avant les mesures

Repris du cahier (05 § 4.6), restreints au zéro seul (la colonne est hors v1.2), et précisés dans
l'en-tête de `outils/genome/construction/codon/pilote_codon.py`, commité avant toute passe (commit
a50c380) :

| Code | Mesure | Témoin et cassure | Seuil |
|---|---|---|---|
| A-T1 | aller-retour du format | sept refus nommés (§ 2) | tous tombent ; les fichiers justes passent — **tenu** (§ 3) |
| A-T2 | codec processeur | décodé = canonique au bit ; cassure : canonisation sans effet | 0 octet différent ; la cassure tombe — **tenu** (§ 3) |
| A-T4 | empreintes | `empreinte_canonique` = empreinte64(canonisé du GGUF) pour 100 % des experts, par le codeur et par le vérificateur (second chemin) | 100 % |
| C1 v1.2 | chaque expert décodé égal à l'original **en valeur** | vérificateur, 768 et 4 608 experts ; cassures `--casser` (médiane) et `--casser-8` (un 0 du décodé changé en 8 : même valeur, octets faux) | 0 expert faux ; chaque cassure trouve exactement l'expert visé |
| **A-C1** | logits au bit | `evaluer --flux`, 10 fenêtres de 512 jetons, 5 120 empreintes de logits, 20b et 120b ; témoin du programme : v1.0 d'aujourd'hui contre le CSV commité ; cassure : copie à une médiane faussée | **0 empreinte différente** ; `.kld` égaux octet pour octet (20b) ; la cassure fait différer |
| **A-C2** | taille | octets de tronçons et fichier, relevés | gain ≥ **0,12 bit par poids d'expert** sur chaque modèle (prédit 0,1280 et 0,1257) |
| **A-C3** | vitesse (J1) | ABBA ABBA, 120b, `mesurer --flux --emplacements 326`, secteur, verrou ; bruit : écart-type relatif des 4 passes v1.0 | **pas de régression** : r ≥ 1 − 2σ ; gain annoncé seulement si r − 1 > 2σ (prédit +3,4 % si le disque limite) |
| J1 | jetons, octets lus, mémoire | les 256 jetons des 8 passes ; octets de tronçons par jeton ; ensemble de travail de pointe | jetons égaux ; rapport des octets publié (prédit 0,967) ; mémoire |B − A| ≤ 2 × bruit + 0,5 Mo |

**Pourquoi des emplacements égaux** : le nombre d'emplacements du cache se calcule à l'ouverture depuis
la VRAM libre et la taille des tampons d'arrivée (12 × le plus grand tronçon) ; un plus grand tronçon
plus petit peut libérer un emplacement (le lot O l'a vu entre fichier codé et brut : 362 contre 361).
Un emplacement de plus change le cache, donc les octets lus, et mêlerait deux effets. Fixer 326 (le
nombre du J1 sur le 120b) isole le format.

---

## 5. Les deux fichiers recodés, et C1 en valeur

Codeur : `trc-codeur coder … --canonique --fils 6 --date 2026-10-17 --sha256-attendu …` (lanceur
`outils/genome/construction/codon/lancer.ps1`, suite `recoder.sh`, journal `journaux/recoder.log`).
Les fichiers v1.0 restent en place ; les v1.2 sont neufs :

| | gpt-oss-20b | gpt-oss-120b |
|---|---|---|
| fichier v1.2 | `~/dev/modeles/trc/gpt-oss-20b-v12.trc` | `…/gpt-oss-120b-v12.trc` |
| SHA-256 (Get-FileHash) | ef1cf7407edb7088bca42c9be30e2f3f87e8e052f7b6a8c877b7c26622d0c433 | 97c292ae77ad638a347d21f8cdb6f3c8e4d9121888376cb3c77d928947c5f0f3 |
| durée du codage | 361 s | 1 395 s |
| SHA-256 du GGUF recalculée par le codeur | égale à l'attendue | égale à l'attendue |

**C1 en valeur** [mes.] (`journaux/verifier-{20b,120b}-v12.json`) : **768 experts sur 768** et **4 608
sur 4 608** exacts ; chacun des huit contrôles à **zéro faute** (empreinte de la partie, décodage,
octets contre le GGUF canonisé par un second chemin, empreinte du décodé contre la canonique, empreinte
des tranches brutes contre l'origine, empreinte des tranches canonisées contre la canonique, aucun 8,
égalité en valeur) ; résidents, méta et en-tête égaux à leur source ; SHA-256 du GGUF recalculée par la
vérification égale à celle de l'en-tête. Durées : 274 s (20b) et 781 s (120b).

**Les deux cassures** (20b) [mes.] : `--casser 5 7` (un bit de la première médiane de la matrice 0 de
l'expert (5, 7) retourné après lecture) → exactement cet expert faux, contrôles « partie », « octets »,
« empreinte du décodé » et « valeur » tombés ; `--casser-8 11 3` (dans l'expert décodé (11, 3), le
premier demi-octet 0 de la matrice 0 changé en 8) → exactement cet expert faux, contrôles « octets »,
« empreinte du décodé » et « aucun 8 » tombés, **« valeur » tenu** : l'instrument distingue l'égalité
des octets de l'égalité des valeurs, ce qui est exactement ce que la v1.2 change.

**Les −0, comptés par deux chemins** [mes.] : le codeur compte 1 221 698 587 demi-octets 8 fondus sur
le 20b (6,393 % des poids d'experts) et 7 199 491 948 sur le 120b (6,279 %) ; la vérification, qui
canonise les tranches du GGUF par son propre chemin, compte les mêmes nombres à l'unité.

**Le second lecteur des tables** [mes.] (`tables_octets.py`, lecteur écrit depuis la seule
spécification, `tables-octets.json`) : en v1.2, **0 table CODES_CTX sur 540** (216 + 324) ne donne de
fente à un octet portant un 8 ; en v1.0, 540 sur 540 en donnaient, pour une masse de 412 à 1 039 sur
4 096 (13 % des fentes en moyenne).

---

## 6. Ce que le fondu rend, sur le disque

[mes.] `outils/genome/construction/codon/analyse_codon.py tailles` → `tailles.json`,
`tailles-par-tenseur.csv` (témoin : la somme des octets de codes par tenseur égale le total du
journal ; cassure, un octet ajouté à un tenseur → le témoin tombe).

| | gpt-oss-20b | gpt-oss-120b |
|---|---|---|
| poids d'experts | 19 110 297 600 | 114 661 785 600 |
| bits par poids, flux (médianes + δ + codes), v1.0 → v1.2 | 3,85057 → 3,72266 | 3,85456 → 3,72892 |
| gain sur les flux | 0,12791 bit | 0,12563 bit |
| octets de tronçons, v1.0 → v1.2 | 9 226 493 952 → 8 920 932 352 | 55 416 086 528 → 53 615 599 616 |
| **gain sur les tronçons, par poids d'expert** (A-C2 : ≥ 0,12) | **0,12791 bit — tient** | **0,12562 bit — tient** |
| octets en moins | 305 561 600 | **1 800 486 912** |
| rapport des tronçons v1.2 / v1.0 | 0,96688 | 0,96751 |
| fichier `.trc`, v1.0 → v1.2 | 11 157 405 696 → 10 851 844 096 | 57 730 662 400 → 55 930 175 488 |
| plus grand tronçon | 12 144 640 → 11 755 520 | 12 251 136 → 11 878 400 |

**Contre la prédiction** : le cahier attendait ≈ 10,85 Go et ≈ 55,93 Go (05 § 4.1) ; l'équipe
prédictif-élagage avait mesuré un gain de 0,1280 et 0,1257 bit par poids sur des flux rANS par tenseur
entier ; découpés par expert dans le format, on mesure 0,12791 et 0,12562 : l'écart (< 0,0001 bit) est
celui des tuiles partielles et de l'alignement par expert.

**Le théorème, vérifié tenseur par tenseur** [calc. sur mes.] : le corollaire de la note pour le
mémoire (§ 2.1) prédit un gain de P(V = 0) · H(S | V = 0) bit par poids, soit **2 × (part des −0)** si le
signe d'un zéro est une pièce juste et indépendante du contexte. Sur les 180 tenseurs (72 + 108),
l'écart entre le gain mesuré et 2 × (part des −0) reste entre **−0,00017 et +0,00016 bit**, en moyenne
+0,00005 : le signe d'un zéro est, dans chaque tenseur, une pièce juste que ni la classe d'échelle ni
l'octet voisin ne prédisent ; le codeur rANS en récupère le bit entier, plus une miette d'arrondi des
tables (225 symboles au lieu de 256 à normaliser sur 4 096).

**Où sont les zéros** [mes.] : le gain va de 0,115 bit (120b, couche 26, up) à **0,239 bit** (120b,
couche 0, up : 11,9 % des poids sont des −0, donc ≈ 24 % sont des zéros) ; la couche 0 est partout la
plus riche en zéros (20b : 0,196 bit en gate et en up), puis la couche 1. C'est la couche où l'état caché
porte des canaux aberrants et où le contexte de la colonne rendait ses 0,13 bit (synthèse § 0) : une
échelle de bloc tirée vers le haut par une colonne géante écrase vers zéro les autres poids du bloc
[hyp., cohérente avec les deux mesures ; non testée ici]. Les moyennes par matrice sont égales à 0,002
bit près (gate, up, down).

---

## 7. Les logits, au bit (A-C1)

[mes.] `pilote_codon.py --phases c1-20b` puis `c1-120b`, séance s1 ; `troncons evaluer --flux`, 10
fenêtres de 512 jetons de `ref-openai-20b.kld`, empreinte64 des logits f32 de chacun des 5 120 pas.

| | gpt-oss-20b | gpt-oss-120b |
|---|---|---|
| témoin du programme : v1.0 aujourd'hui contre le CSV commité du 2026-10-15 | **5 120 / 5 120 égales** | — (pas nécessaire : voir la ligne suivante) |
| **v1.2 contre v1.0** | **5 120 / 5 120 égales** | **5 120 / 5 120 égales** au CSV du 2026-10-15 |
| `.kld` | égaux octet pour octet (3e43e7dc…edcb) | égaux octet pour octet au `.kld` du 2026-10-15 (5b212fe9…bcd7be) |
| PPL des positions notées | 461,978 (= O3) | 422,206 (= O3) |
| cassure (médiane faussée, couche 0, expert 30, ligne 100, 121 → 122) | **512 lignes sur 512 différentes** (1 fenêtre, `--sans-garde`) | — |

Sur le 120b, la comparaison est plus forte que demandée : le v1.2, évalué **par le préremplissage par
flux** avec le programme d'aujourd'hui, rend au bit les logits que le v1.0 rendait **par la boucle de
pas** avec le programme du 2026-10-15. Le format, le programme et le chemin d'évaluation ont changé ;
aucun bit des logits.

**Une découverte en chemin, dite** : la première passe de la cassure (avec la garde de production,
ajoutée au moteur après O3, constat M1 de l'épreuve J1) a été refusée en 8 s, avant tout logit :
« garde de production : couche 0, expert 30 : empreinte des 11 234 960 octets utiles lus d99bc396…
au lieu de f84282ff… (répertoire) » (`journaux/s1-c1-20b-K-casse-avec-garde.log`). C'est un témoin de
la garde, gardé ; le témoin des logits a été refait `--sans-garde`, le seuil inchangé (déclaration
ajoutée à l'en-tête du pilote, 09 h 35, avant la seconde passe).

---

## 8. Le jalon J1 refait sur le 120b, v1.2 contre v1.0 (A-C3)

[mes.] `pilote_codon.py --phases j1 --seance s1` (10 h 24 à 10 h 50, après l'attente du verrou tenu par le
lot B), analyse `analyse_codon.py j1` → `j1-s1-passes.csv`, `j1-s1-verdicts.json`. Huit processus neufs
A B B A A B B A, A = `gpt-oss-120b.trc` (v1.0 d'origine), B = `gpt-oss-120b-v12.trc` ; `mesurer --flux
--emplacements 326`, invite wiki-3000, 256 jetons gloutons ; secteur et aucun llama-* avant chaque passe.

| passe | fichier | jetons/s | Mo de tronçons par jeton | débit de lecture vu par le moteur (Go/s) |
|---|---|---|---|---|
| 1 | v1.0 | 1,557 | 710,12 | 1,375 |
| 2 | v1.2 | 2,586 | 686,76 | 2,311 |
| 3 | v1.2 | 2,240 | 686,76 | 2,006 |
| 4 | v1.0 | 1,558 | 710,12 | 1,412 |
| 5 | v1.0 | 1,010 | 710,12 | 1,220 |
| 6 | v1.2 | 1,143 | 686,76 | 1,452 |
| 7 | v1.2 | 1,223 | 686,76 | 1,420 |
| 8 | v1.0 | 1,741 | 710,12 | 1,574 |

**Ce qui tient au bit** : les **256 jetons produits sont les mêmes dans les huit passes**, et le texte a
l'empreinte e4c6dbacb63a… de toutes les passes du 120b des 15 et 16 octobre (REPRISE-O : 17 passes) ;
défauts par jeton (59,08), taux de succès du cache (h = 0,5897) et emplacements (326) identiques dans les
huit passes : le format ne change ni le routage ni le cache, seulement la taille de ce qu'on lit.

**Les octets lus par jeton** (déterministes, aucun bruit) : 710 118 798 → 686 756 916 octets, **rapport
0,9671**, pour une prédiction de 0,967 (le rapport des tronçons du fichier entier est 0,9675 ; les experts
que ce texte appelle sont un peu plus riches en zéros que la moyenne).

**La vitesse, au seuil déclaré** : médianes 1,558 (v1.0) et 1,732 (v1.2) jeton/s, r = 1,112 ; mais
l'écart-type relatif des quatre passes v1.0 vaut **σ = 21,6 %** (séance bruitée : les passes 5 à 7 sont
toutes lentes, quel que soit le fichier ; d'autres équipes lisaient le disque en même temps). Verdicts :
**pas de régression** (r ≥ 1 − 2σ) ; **gain non annoncé** (r − 1 = 0,11 < 2σ = 0,43). Les rapports
appariés (A1, B2), (B3, A4), (A5, B6), (B7, A8) valent 1,66, 1,44, 1,13 et 0,70.

**La mémoire de pointe** : médianes 386,96 Mo (v1.0) et 380,56 Mo (v1.2) ; le seuil déclaré,
|B − A| ≤ 2 × bruit + 0,5 Mo = 1,25 Mo, **tombe au sens littéral, dans le bon sens** : le v1.2 occupe
6,41 Mo de moins. 4,47 Mo s'expliquent par les 12 tampons d'arrivée épinglés, dimensionnés sur le plus
grand tronçon (12 × (12 251 136 − 11 878 400) = 4 472 832 octets) [calc.] ; le reste (≈ 1,9 Mo) n'est
pas expliqué ici [hyp. : d'autres tampons à la taille du plus grand tronçon]. Le seuil était écrit pour
voir une croissance ; il est gardé tel quel et dit tombé.

**Un écart trop grand pour le format, et son témoin.** Dans les quatuors où la machine était calme
(passes 1 à 4), le v1.2 va 1,4 à 1,7 fois plus vite et le moteur y voit le disque rendre 2,0 à 2,3 Go/s
au lieu de 1,38 à 1,41 : 3,3 % d'octets en moins ne peuvent pas rendre 40 %. L'hypothèse : **la
disposition du fichier v1.0 sur le disque** (écrit le 2026-10-15, quand le disque était plus rempli et
partagé), et non le format. Elle se teste sans opinion : une **copie neuve du v1.0** (octet pour octet,
écrite aujourd'hui juste avant la séance, donc disposée comme le v1.2) remplace le v1.0 d'origine. Les
phases `disque` (l'étage disque seul, A B C C B A) et `j1-copie` (le J1 refait avec la copie) ont été
déclarées dans l'en-tête du pilote à 10 h 40, pendant la séance s1 et avant leurs passes (commit
« phases disque et j1-copie déclarées »). C'est `j1-copie` qui juge le format.

**Phase disque de s1** [mes.] (`disque-s1.json`, `troncons disque --n 1500 --graine 20261017`, ordre
A B C C B A) : v1.0 d'origine **1,64 et 1,55 Go/s**, copie neuve **1,44 et 1,38**, v1.2 **2,58 et 2,31**.
L'étage disque seul, sans calcul, lit donc le fichier v1.2 bien plus vite que le v1.0, avec des requêtes
3 % plus courtes : ce n'est pas un effet du format sur le calcul. Mais l'hypothèse de la disposition du
v1.0 tombe : relevé de `fsutil file queryextents` (`journaux/s1-fragments.txt`), le v1.0 d'origine tient en
**65 fragments**, le v1.2 en **233**, et la copie neuve en **289 545** (écrite à 54 Mo/s pendant que
d'autres équipes écrivaient). Le témoin était confondu par sa propre fragmentation ; la phase j1-copie a
été arrêtée après deux passes (gardées : copie 1,098 jeton/s, v1.2 1,259 ; mêmes 256 jetons).

**Séance s2** (déclarée à 11 h 50, avant ses passes) : le témoin devient **le v1.0 recodé aujourd'hui
par trc-codeur**, même écrivain et même jour que le v1.2, dont la SHA-256 doit égaler celle du v1.0
d'origine (6c7b5f1d…dcce ; c'est aussi le témoin d'identité du codeur modifié sur le 120b) ; ses
fragments sont relevés avant la séance. Si ce témoin se lit aussi vite que le v1.2, l'écart vient de
l'âge ou de l'emplacement physique des données sur le NVMe [hyp. à trancher], pas du format ; s'il se lit
comme le v1.0 d'origine, il faudra chercher dans le contenu, ce qu'aucun mécanisme connu de nous
n'explique.

**Avant s2, le témoin est tombé de lui-même** : l'échantillon des fragments (`journaux/s2-fragments.txt`,
11 fenêtres de 1 Gio) donne au v1.0 recodé **47 745 fragments**, contre 26 au v1.0 d'origine. Il est
confondu comme la copie de s1 ; il a été gardé (sa SHA-256 est celle du v1.0 : même contenu au bit), mais
il ne juge plus le format seul.

**Amendement de s2, déclaré le 2026-10-21 à 23 h 40, avant toute passe** (en-tête de `pilote_codon.py`,
commit 71905dd) : la phase **j1** (v1.0 d'origine contre v1.2) est ajoutée, parce que le j1 de s1 a été
pris sous charge ; la séance ne part que sur deux relevés vides des processus des autres flux à une minute
d'écart, et chaque passe est relevée avant et après (plus de 5 % d'un cœur ou 8 Mo lus en 3 s ⇒ « SOUS
CHARGE », la passe ne conclut pas). Mêmes seuils A-C3.

### Résultats de s2 (2026-10-21 à 23 h 59 au 2026-10-22 à 0 h 46, machine calme)

[mes.] `pilote_codon.py --phases disque,j1,j1-copie --seance s2 --attendre-calme` (le pilote a attendu
23 min la fin d'une passe KL du lot B) ; analyses `disque-s2.*`, `j1-s2-*`, `j1-copie-s2-*`, commit 96533df.
**Aucune des 22 passes n'a été prise sous charge** (relevés vides avant et après chacune ; secteur à chaque
passe).

**L'étage disque seul** (`troncons disque --n 1500`, A B C C B A) :

| fichier | contenu | fragments | Go/s (deux passes) |
|---|---|---|---|
| A, v1.0 d'origine (écrit le 2026-10-15) | v1.0 | 65 (relevé complet ; 26 dans l'échantillon) | 1,742 et 1,741 |
| B, v1.2 (écrit le 2026-10-17) | v1.2 | 233 (relevé complet) | 2,254 et 2,391 |
| C, v1.0 recodé (écrit le 2026-10-17) | v1.0, **égal à A au bit** | 47 745 dans l'échantillon | 1,356 et 1,331 |

**J1, A = v1.0 d'origine, B = v1.2** (`j1-s2-verdicts.json`) :

| passe | 1 A | 2 B | 3 B | 4 A | 5 A | 6 B | 7 B | 8 A |
|---|---|---|---|---|---|---|---|---|
| jetons/s | 1,981 | 2,873 | 2,892 | 1,994 | 2,006 | 2,897 | 2,887 | 1,776 |

- jetons : **les 256 identifiants égaux dans les huit passes**, texte e4c6dbac… (celui de s1 et des 15 et
  16 octobre) ; défauts 59,08 par jeton, h = 0,5897, 326 emplacements dans toutes les passes ;
- octets de tronçons par jeton : **0,9671** (710 118 798 → 686 756 916, comme en s1 : déterministe) ;
- jetons/s : médianes **1,988 (v1.0) et 2,890 (v1.2)**, **r = 1,454**, σ = 5,6 % ; rapports appariés 1,450,
  1,451, 1,444, 1,626. Au seuil déclaré : **pas de régression ; gain annoncé** (r − 1 = 0,454 > 2σ = 0,113) ;
- mémoire de pointe : médianes 388,67 Mo (v1.0) et 382,21 Mo (v1.2), **−6,45 Mo** (s1 : −6,41) ; le seuil
  tient au sens littéral, mais seulement parce que la première passe de la séance (468,4 Mo) fait un bruit
  de 79,8 Mo : sans elle, les passes v1.0 vont de 388,60 à 388,70 Mo et l'écart de 6,45 Mo est net ;
- le moteur voit le disque rendre 1,61 à 1,83 Go/s sur le v1.0 et 2,63 à 2,67 sur le v1.2.

**J1-copie, A = v1.0 recodé (C), B = v1.2** (`j1-copie-s2-verdicts.json`) : mêmes 256 jetons ; médianes
1,814 et 2,894 jetons/s, r = 1,595, σ = 4,2 %.

**Ce que s2 dit, et ce qu'il ne dit pas.**
1. **Le fichier v1.2 du 120b est, sur ce portable, 1,45 fois plus rapide que le fichier v1.0 d'origine**
   (2,89 contre 1,99 jetons/s), au même texte au bit, sur une machine calme : c'est un résultat de produit,
   mesuré et reproduit (s1, quatre premières passes calmes : 1,44 à 1,66).
2. ~~**Ce gain n'est pas attribuable au format.** Deux fichiers au **même contenu au bit** (A et C) se lisent à
   1,74 et 1,34 Go/s à l'étage disque, et rendent 1,99 et 1,81 jetons/s : la disposition physique d'un
   fichier sur ce NVMe déplace la vitesse de 30 % sans toucher un octet du contenu. L'écart B/A à l'étage
   disque (1,33) est de cet ordre. La part du format, elle, est bornée par le rapport des octets lus :
   **au plus +3,4 %** à disque limitant [calc.]. Le seuil A-C3 « gain annoncé » est donc tenu pour les
   fichiers, et la phrase « la v1.2 rend le moteur 45 % plus rapide » serait fausse.~~
   **Corrigé le 2026-10-27**, d'après `genome/JUGEMENT-placement.md` (§ 0, §§ 5.3, 5.6, 5.7, § 12 point 3) : sur ce disque, l'écart B/A suit **le motif des requêtes de lecture que le format impose** (frontières et longueurs des tronçons) : A lu au motif de B va comme B (×1,389), B lu au motif de A va comme A (×0,715). Le gain du J1 est donc **un gain du format v1.2, propre à cette machine**, par le motif de ses tronçons et non par ses 3,3 % d'octets ; la variable exacte du motif n'est pas isolée (couper chaque requête du v1.0 en deux ne le répare pas : ×0,851 et ×0,882). La borne de +3,4 % ne vaut que pour les octets : elle ne borne pas l'effet du motif. L'écart
   A/C (même contenu au bit) vient, lui, de la fragmentation extrême de C (267 473 extents ; ×1,26 au chemin du
   moteur). Le seuil A-C3 « gain annoncé » tient, et sur ce portable la v1.2 rend bien le moteur environ 45 % plus
   rapide sur le 120b ; ce chiffre ne se transporte pas à un autre disque sans y être remesuré.
3. **Le nombre de fragments n'explique pas tout** : B (233 fragments) se lit plus vite que A (65), et C
   (des dizaines de milliers) plus lentement. [hyp., non tranchée] l'emplacement physique des blocs sur la
   puce (zones écrites récemment, cache, usure) ; [hyp.] l'écart s'amplifie de 1,33 (disque seul) à 1,45
   (moteur) parce que la carte, qui attend plus le disque, tourne à des horloges plus basses : les temps de
   carte mesurés par événements (copie 91 à 99 ms par jeton contre 66 à 68, décodage 61 à 67 ms contre 42 à
   44) varient bien plus que les 3,3 % d'octets.
4. ~~**Le témoin décisif** reste à faire~~ (corrigé le 2026-10-27 : le motif croisé du juge du placement, même
   fichier lu aux deux motifs, en tient lieu sans réécrire de fichier ; sa conclusion est celle de la dernière
   phrase ci-dessous, « la disposition des tronçons du format (alignement, taille des requêtes) », voir
   `genome/JUGEMENT-placement.md` (§ 0, §§ 5.3, 5.6, 5.7, § 12 point 3)), sur une machine calme et un disque où il y a de la place : écrire
   le même jour, l'un après l'autre et sans autre écrivain, une copie neuve **du v1.0 et du v1.2** (ou les
   recoder tous les deux), relever leurs fragments, puis refaire la phase disque et le j1 sur les quatre
   fichiers. Si les deux neufs se lisent pareil, le format ne compte pour rien dans la vitesse (sauf ses
   3,3 %) ; s'il reste un écart du même signe, il faudra le chercher dans la disposition des tronçons du
   format (alignement, taille des requêtes), ce que rien de connu de nous n'explique aujourd'hui.

---

## 9. Ce qui pourrait être faux

- **A1 suppose des x finis.** Un x infini ou NaN donne NaN des deux côtés ; seul le signe ou la charge
  d'un NaN pourraient différer. Le moteur n'a jamais produit de NaN sur les 10 240 pas évalués ici ; un
  modèle qui en produirait sortirait de toute façon du domaine des logits utilisables.
- **A1 est démontrée pour la GEMV d'aujourd'hui.** Un noyau futur qui lirait les codes autrement (une
  table de 16 valeurs où l'entrée 8 vaudrait autre chose que ±0, une GEMM qui partirait d'un
  accumulateur −0, une réduction qui multiplierait par le signe) pourrait casser l'égalité. L'invariant
  est écrit dans ARCHITECTURE § 5.6 et le témoin à reprendre est `gemv_lit_le_code_8_comme_0`.
- **Le gain est celui de gpt-oss.** Il vaut 2 × (part des −0) ; un modèle MXFP4 quantifié par un outil
  qui écrit toujours +0 (le code 0) n'a rien à gagner, et la v1.2 lui coûte zéro octet (mêmes tables,
  même taille). Un modèle où le signe d'un zéro serait informatif (corrélé à son voisin) rendrait moins
  que 2 × (part des −0) : nos 180 tenseurs disent que ce n'est pas le cas ici (écart ≤ 0,00017 bit).
- **Les « emplacements égaux » du J1 isolent le format, pas le produit.** Le plus grand tronçon du v1.2
  est plus court de 372 736 octets (120b) ; les 12 tampons d'arrivée rendent 12 × 372 736 = 4 472 832 octets (4,3 Mio) de VRAM,
  moins d'un emplacement (13 254 144 octets, 12,6 Mio) ; le nombre d'emplacements par défaut ne change donc probablement pas
  [calc.], mais il n'est pas mesuré ici.
- **Le témoin de la garde masquait le témoin des logits.** Corrigé (`--sans-garde` pour la seule
  cassure) et dit (§ 7) ; la garde reste active dans toutes les autres passes.
- **La première passe d'identité a été tuée et relancée** (§ 3, journal `recoder.log`, lignes de
  08 h 43 annotées) : le verdict « TOMBE » de ces lignes est celui d'un fichier inachevé, pas une mesure.
- **Un second décodeur indépendant n'a pas été étendu à la v1.2** (A6 du cahier) : c'est le rôle d'un
  juge qui n'a écrit ni la décision ni le code (SOCLE, « la barre ») ; le décodeur Python de l'épreuve
  J1 (`mesures/moteur/epreuve-J1/`) lit la v1.0 et devrait lire la v1.2 sans changement de décodage
  (seuls l'en-tête, l'entrée du répertoire et la comparaison d'empreinte changent).

---

## 10. Recettes (pour RECETTES.md)

- **Un codon synonyme se porte dans un format par les tables, pas par le décodeur.** Fondre deux
  symboles de même valeur avant le comptage donne des tables où le symbole fondu a la fréquence 0 ; le
  décodeur, qui ne lit que des fentes, n'a rien à apprendre. Coût du portage : un drapeau, une empreinte,
  un contrôle à l'ouverture. Raison : le lemme des tables (note pour le mémoire § 2.3).
- **Garder deux empreintes quand le décodé n'est plus l'original au bit** : l'origine (provenance,
  octets du GGUF) et la canonique (ce que le décodeur doit rendre). Un vérificateur doit alors comparer
  en **valeur** et pas seulement en octets ; la cassure `--casser-8` (même valeur, octets faux) prouve
  qu'il sait faire la différence.
- **Le gain d'un synonyme se prédit avant de coder : 2 × (part du synonyme minoritaire)** quand le choix
  entre synonymes est une pièce juste ; vérifié sur 180 tenseurs à ±0,00017 bit.
- **Ne pas lancer un long calcul en priorité « sous la normale » sur cette machine quand d'autres
  processus tournent** : le codeur a lu 16 Mio toutes les 15 à 30 s, fils prêts mais non servis, CPU à
  11 % ; en priorité normale, 13 s par couche [mes., `recoder.log`] ; [hyp.] mode efficacité de
  Windows sur un processeur hybride.
- **Arrêter une tâche de fond ne tue pas forcément ses enfants** (Git Bash sous Windows) : vérifier les
  processus par leur ligne de commande, et ne tuer que les siens.
- **Une cassure doit traverser toutes les gardes en amont de l'instrument qu'elle éprouve** : la garde
  de production arrêtait la copie à médiane faussée avant les logits.

---

## 11. Réponses par délégation de ce document

- *Le contexte de la colonne d'entrée entre-t-il dans la v1.2 ?* Non (réponse par délégation du
  2026-10-17, réversible) : 0,0037 bit par poids sur le 20b entier (8,8 Mo) contre un noyau, une LUT et un
  montage neufs ; la consigne dit « s'il tient sans risque » (§ 2).
- *Le drapeau CANONIQUE sur un fichier brut ?* Refusé (réponse par délégation du 2026-10-17,
  réversible) : le brut est le chemin de référence des témoins C3 et C12 et doit garder les octets du
  GGUF.
- *`--canonique` par défaut ?* Non (réponse par délégation du 2026-10-17, réversible) : sans l'option,
  le codeur écrit la v1.0 octet pour octet, ce qui garde le témoin d'identité et la reproductibilité des
  fichiers existants ; la v1.2 se demande explicitement.
- *Noms des fichiers neufs* : `<modèle>-v12.trc` à côté des v1.0, sans rien effacer (consigne).

---

## 12. Ce qui reste

- Le témoin décisif de la vitesse (§ 8, point 4) : une copie neuve du v1.0 et une du v1.2, écrites le même
  jour l'une après l'autre sans autre écrivain, puis disque et j1 sur les quatre fichiers. Il demande
  environ 113 Go libres (ou d'effacer d'abord le v1.0 recodé, 57,7 Go, écrit par ce lot) : décision de Stone.
- En attendant, le **fichier** v1.2 du 120b est le plus rapide des trois sur ce portable (2,89 jetons/s) ;
  le désigner comme fichier par défaut est un choix de produit, pas un résultat du format.
- A6 : étendre le décodeur indépendant de l'épreuve J1 à la v1.2, par un juge qui n'a pas écrit ce lot.
- Relecture de ce document par un juge (SOCLE, « la barre »).
- Porter les recettes du § 10 dans RECETTES.md (orchestrateur).
- Les figures F1 à F6 de la note pour le mémoire (données commitées sous
  `mesures/genome/construction/codon/`).
- Décider, avec Stone ou par délégation, si les v1.2 remplacent les v1.0 comme fichiers par défaut du
  moteur (aucun fichier n'a été effacé ; 57,7 + 11,2 Go restent occupés par les v1.0).
