# Jugement technique indépendant du Tome II

Juge : agent « juge technique du Tome II », qui n'a écrit aucune ligne des chapitres, des figures,
des outils de données ni du moteur. Date : 2026-10-16. Objet : les deux PDF
`memoire/tome2/{en,fr}/troncons-tome2-{en,fr}.pdf` (EN 231 pages, FR 235, commit `ef30835`) et
leurs sources (`memoire/tome2/`, `memoire/figures/tome2/`, `memoire/figures/{donnees,graphes,schemas}/tome2/`).
Aucun chapitre n'est modifié par ce jugement ; aucune passe n'a tourné sur la carte.

## Verdict en bref

**Le Tome II tient.** Aucun chiffre qui décide d'un verdict n'est faux : C1, C3, C4, C5, C6
(× 2,22 garde comprise contre `fit -t 16`), C7, C10, C11, C12, K1, K2, K3, E0 à E2 se refont
depuis les CSV et journaux commités, par les outils du dépôt et par un second chemin écrit ici.
Les structures dessinées au bit près égalent `decisions/ARCHITECTURE.md` § 4 et le code. Les
démonstrations vérifiées tiennent. Les deux langues portent les mêmes nombres.

- **1 objection grave** : une estimation que le chapitre de la référence démontre fausse et barre
  (« la KL tomberait vers 5·10⁻¹¹ ») est publiée **sans barre** aux chapitres des noyaux et des
  résultats, dans les deux langues.
- **22 objections mineures** : incohérences entre chapitres (coût de la garde), qualificatifs
  faux (débit « séquentiel », « le tiers »), un chiffre hérité faux (Δω à la paire 9), des
  arrondis présentés comme des égalités, un critère (C9) absent, deux figures dont la légende ou
  l'échelle ne suit pas le texte.
- **Éloges** : reproductibilité des données au bit, parité des langues, schémas exacts, preuves
  justes, histoire des chiffres barrés tenue.

## Méthode

1. Lu en entier : `SOCLE.md` ; `decisions/ARCHITECTURE.md` § 4 et § 7 ; les dix chapitres
   français, les annexes A et B, les résumés ; les figures de format, de noyaux, de chemin, de
   référence, de cache et de résultats ; les passages anglais où un écart était possible.
2. **Reproductibilité** : copie de sauvegarde des données dérivées, puis relance des cinq outils
   du mémoire (`tome2_format.py`, `tome2_chemin_noyaux.py`, `tome2_reference_cache.py`,
   `tome2_resultats.py`, `tome2_annexes.py`) : code 0 partout, « 31 chiffres refaits, 0 écart »,
   « aucun écart aux chiffres publiés », témoin des options « tient (0 écart, 35 options) », et
   **`git status` inchangé** : les CSV et tables régénérés sont égaux octet pour octet aux
   fichiers commités.
3. **Second chemin du juge** : `memoire/outils/tome2_juge.py` (commité avec ce jugement).
   (a) Parité des nombres EN/FR, chapitre par chapitre ; témoin : `--casser` change 0.884 en
   0.885 dans le texte anglais du chapitre 08 (sans écart sinon), l'instrument trouve l'écart
   (vérifié : « tombe »). (b) Recalculs, depuis les CSV, de chaque chiffre que vise une objection.
4. Recalculs ponctuels faits à la main ou en Python contre les journaux (sections, tailles,
   Wilson, test apparié, KV f16/f32, p99, YaRN, falaise, plancher en série, disque D:, génome).
5. Code : `moteur/Cargo.toml` et `Cargo.lock` (versions), `crates/trc-format/src/lib.rs`,
   `crates/trc-noyaux/src/abi.rs`, `crates/trc-noyaux/build.rs`, `crates/trc-noyaux/noyaux/*.cuh`
   (vingt `__global__`), `crates/trc-juge/src/kld.rs`.
6. Construction : journaux LaTeX des deux PDF (0 erreur, 0 référence indéfinie) ; `pdftotext` :
   0 « ?? » ; les passages visés par les objections sont bien dans les PDF commités.

Notation : « FR l. N » renvoie à la ligne du source français ; sauf mention, le source anglais a
la même phrase à la même ligne (ch. 02 : une ligne plus bas après la l. 350).

## Objection grave

### G1. « 5·10⁻¹¹ » : une estimation démontrée fausse, publiée sans barre deux fois

**Où.** `04-noyaux.tex` FR l. 543 et EN l. 543 : « Divisée par 8 192² ≈ 6,7·10⁷, la KL du f16
(3,08·10⁻³ sur le 120b) tomberait vers 5·10⁻¹¹ [calc., ordre de grandeur, si l'erreur reste
linéaire ; les bascules de routage ne le sont pas, mais elles disparaissent avec elle] ».
`07-resultats.tex` FR l. 338 et EN l. 338 : « la KL étant du second ordre, elle serait divisée
par environ 8 192² ≈ 6,7·10⁷ : de 3,08·10⁻³ vers 5·10⁻¹¹ \calc ».

**Preuve.** Le même tome démontre le contraire. `05-reference.tex` FR l. 401-411 (théorème
« Deux régimes de la KL d'un mélange d'experts ») : KL(u) ≈ a u² + f_m(0) c u · KL_saut ; le
terme des bascules est **linéaire** en u, il ne « disparaît » pas avec l'erreur quadratique, il
est divisé par 8 192, pas par 8 192². FR l. 492 en tire la borne honnête, 0,00308 / 8 192 ≈
3,8·10⁻⁷, et **barre** explicitement « la KL du f16 tomberait vers 5·10⁻¹¹ » comme estimation
du lot O « qui supposait le régime quadratique pour toute la KL » (vérifié dans le PDF FR :
texte barré présent l. 8035 de `pdftotext`). Les chapitres 04 et 07 publient donc, sans barre,
un chiffre que le chapitre 05 barre : le lecteur reçoit deux résultats incompatibles. La source
de l'erreur est `moteur/O-pour-le-memoire.md` l. 607-609. La règle du SOCLE (« quand une mesure
contredit un chiffre publié, même le tien, barre la phrase ») vaut a fortiori quand une
démonstration du même document le contredit. La conclusion (« sous le pas du format ») reste
vraie, mais par la borne de 3,8·10⁻⁷, et la phrase « elles disparaissent avec elle » est fausse
au regard du théorème.

**Correction demandée** (EN et FR, ch. 04 l. 543 et ch. 07 l. 338) : barrer « 5·10⁻¹¹ » et la
phrase « les bascules … disparaissent avec elle » ; écrire, avec renvoi au théorème des deux
régimes et à la section « Pourquoi le f32 doit rejoindre la vérité » : « le terme sans bascule
est divisé par 8 192², celui des bascules, linéaire, par 8 192 : au plus de l'ordre de
3,8·10⁻⁷ nat, bien sous le pas du format » ; garder la mesure (−0,00048, le zéro de
l'instrument) comme seul juge.

## Objections mineures

Chacune : où, preuve, correction. Les recalculs cités sont ceux de `tome2_juge.py` sauf mention.

### m1. Le coût de la garde n'a pas la même valeur d'un chapitre à l'autre
**Où.** −1,7 % et « 5,2 à 5,3 ms » : ch. 01 FR l. 351, 359, 369 (tableau de la ronde, paragraphe
de la garde) ; ch. 03 FR l. 515 ; ch. 06 FR l. 468, 511. −1,6 % et « 5,2 à 5,4 ms » : ch. 00
l. 51, ch. 07 l. 270 et 393, ch. 08 l. 232 et 341, annexe A bloc 3.
**Preuve.** `vitesse-2026-10-16-passes.csv` : passes 05 (gardée) et 04 (sans garde) à disque
égal, 1,900152 / 1,931729 − 1 = **−1,63 %** ; attente de la garde 5,19 / 5,28 / **5,42** /
5,24 ms (passes 05, 02, 07, 08). Le ch. 07 explique lui-même que −1,7 % vient des valeurs
arrondies ; les ch. 01, 03, 06 recopient la note du lot O sans la correction.
**Correction.** −1,6 % et 5,2 à 5,4 ms partout (EN et FR), en renvoyant à l'explication du ch. 07.

### m2. « 2 × 11,0 + 3 = 24,9 % » est faux tel qu'écrit
**Où.** ch. 01 FR l. 361 ; ch. 06 FR l. 486 ; ch. 07 FR l. 238 ; EN aux mêmes lignes.
**Preuve.** Bruit de la paire 02-05 : |1,7026 − 1,9002| / 1,8014 = **10,97 %** ; 2 × 10,97 + 3 =
24,94 %. Écrit avec 11,0, l'égalité donne 25,0. Le verdict ne change pas (écart + 122 %).
**Correction.** « 2 × 10,97 + 3 = 24,9 % » (ou « 2 × 11,0 + 3 = 25,0 % »).

### m3. « le tiers … en grands blocs séquentiels » (discussion)
**Où.** ch. 09 FR l. 49 ; EN l. 49 (« a third of what Volume I measured in large sequential
blocks »).
**Preuve.** 1,55 / 2,82 = 0,55 (débit utile dans le moteur) ; 1,85 / 2,82 = 0,66 (disque seul à
la longueur des tronçons). Et 2,82 Go/s est, au Tome I, la lecture **aléatoire** de 16 Mio en
QD 1 (`memoire/fr/chapitres/03-machine.tex`, tableau du disque, colonne « aléa QD 1 », 2,819) ;
le séquentiel à 16 Mio y vaut 2,340 (QD 1) et 2,206 (QD 16).
**Correction.** « un peu plus de la moitié (1,55 Go/s utiles) à deux tiers (1,85 Go/s, disque
seul) de ce que le Tome I mesurait en lectures aléatoires de 16 Mio (2,82 Go/s) ».

### m4. « débit séquentiel du disque (2,58 Go/s, étude 01) »
**Où.** ch. 02 FR l. 412 ; EN l. 413.
**Preuve.** 2,58 Go/s est la lecture aléatoire de 4 Mio en QD 4 (Tome I, même tableau, 2,581 ;
`memoire/fr/chapitres/04-formulation.tex` l. 87) ; le ch. 03 FR l. 256 le dit correctement. Au
même endroit, « la seconde lecture y pèse au plus 2 % » : 23,6 / 1 153,3 = **2,05 %**.
**Correction.** « au débit du disque en lectures de 4 Mio en QD 4 (2,58 Go/s, étude 01) » ;
« environ 2 % ».

### m5. Δω à la paire 9 : 8,8·10⁻⁵ au lieu de 8,5·10⁻⁵
**Où.** ch. 05 FR l. 147, EN l. 147. Source : `moteur/R-pour-le-memoire.md` l. 81.
**Preuve.** θ₉ = 150 000^(−18/64) = 0,035013 ; rampe d'OpenAI r = (9 − 8,09278) / (17,39802 −
8,09278) = 0,097496, ω/θ = 0,905551 ; rampe de llama.cpp r = 0,1, ω/θ = 0,903125 ; Δω =
0,035013 × 0,002426 = **8,49·10⁻⁵** rad par position. La valeur de la paire 17 (9,8·10⁻⁵) est
juste (9,86·10⁻⁵).
**Correction.** Barrer 8,8·10⁻⁵, écrire 8,5·10⁻⁵ (dire que le chiffre vient de la note du lot R).

### m6. « K1 tombe de 0,9 % » : la pire passe manque de 1,1 %
**Où.** ch. 04 FR l. 199 (titre), 219, 234 ; EN mêmes lignes.
**Preuve.** Seuil 33,28 Go/s, jugé sur la **pire** passe A. Pires passes : 32,99 (processus 1) et
32,92 (processus 2) ; 1 − 32,99/33,28 = 0,87 %, 1 − 32,92/33,28 = **1,08 %**. Le « 0,9 % » est
celui du processus 1 seul (repris de `moteur/K-pour-le-memoire.md` l. 205).
**Correction.** « tombe de 0,9 et 1,1 % (une pire passe par processus) ». Verdict inchangé.

### m7. « 21 % de dispersion » des passes B de L12 n'est pas le bruit de la règle
**Où.** ch. 03 FR l. 503 (« 21 % selon le lot O ») ; ch. 06 FR l. 453 ; ch. 07 FR l. 277 ;
ch. 09 FR l. 90 (tableau des idées tuées).
**Preuve.** `o-jetons-s.csv`, passes `s2-16` et `s2-17` : 2,613 et 3,073 ; β = |X₁ − X₂| / X̄ =
**16,2 %** (définition du ch. 07, `t2res-def:reel`) ; 21 % est 0,46 / 2,18, l'écart rapporté à la
moyenne de A. Seuil de la règle : 2 × 16,2 + 3 = 35,4 % > + 30,4 % : verdict inchangé (non franchi).
**Correction.** Publier β = 16,2 % et le seuil 35,4 %, dire d'où venait 21 %.

### m8. × 1,335 : le calcul affiché n'est pas celui qui le donne
**Où.** ch. 03 FR l. 485 (« V / N = × 1,335 (médianes A : N 2,126 et 2,142 ; V 2,811 et
2,853) ») ; aussi l. 6, 406, 487, 513 et la figure E2.
**Preuve.** `e2-nvvn-2026-10-15-nvvn.csv` : la moyenne des quatre médianes affichées donne
2,832 / 2,134 = **1,327** ; × 1,335 est le rapport des médianes des huit passes A de chaque
lettre (2,851 / 2,135 = 1,3352). « Écart de 25 % » est 1 − 1/1,335 (N sous V), alors que le gain
de V sur N est + 33,5 %.
**Correction.** Écrire « médiane des 8 passes A : V 2,851, N 2,135, × 1,335 (+ 33,5 %) ».

### m9. La figure du codeur garde « 0,47 Go » que le texte barre
**Où.** ch. 02 FR l. 375 (légende) et `memoire/figures/tome2/schemas/format.tex` l. 299
(`\TdFmtCodeur`, barre de 0,47 sur un axe gradué en Go) ; EN l. 376.
**Preuve.** Le texte (FR l. 403) barre « ≈ 0,47 Go » : 502 252 544 o = 0,47 **Gio** = 0,50 Go.
La figure place 0,47 sur le même axe que 0,42 Go et 1,69 Go (423 014 400 et 1 692 057 600 o,
en Go décimaux) : trois barres, deux unités.
**Correction.** Barre à 0,50 ; légende « ≈ 0,50 Go (0,47 Gio) ».

### m10. L'en-tête fixe : « huit octets par rangée » n'est pas vrai de toute la figure
**Où.** ch. 02 FR l. 75 (légende de `\TdFmtEntete`).
**Preuve.** `schemas/format.tex` l. 76-103 : les rangées 17 à 19 portent les 128 o des
sections (décalages 136 à 263), la rangée 20 les 3 824 o réservés. Les décalages écrits à gauche
sont justes (136, 264, 4 088) ; seule la légende trompe.
**Correction.** « huit octets par rangée, sauf les sections (128 o, trois rangées) et le
réservé (3 824 o, une rangée), comprimés » ; ou une marque de coupure dans la figure.

### m11. « 157 ms de disque par jeton » présenté comme un fait (noyaux)
**Où.** ch. 04 FR l. 240 et l. 296.
**Preuve.** 157 ms est la prédiction du Tome I (étude 07, scénario LRU calé ; le ch. 03 FR l. 23
et l'annexe A le disent) ; la mesure du jalon vaut t_disque = **382,7 ms** (ch. 07 l. 185,
`o4-2026-10-15-s1-passes.csv`). La conclusion se renforce (0,34 ms par expert contre 383 ms).
**Correction.** Citer la mesure, ou écrire « 157 ms prédits par le Tome I, 383 ms mesurés ».

### m12. « 214 opérations par octet compressé » : le budget du lien, pas du disque
**Où.** ch. 09 FR l. 190.
**Preuve.** Tome I, `memoire/fr/chapitres/03-machine.tex` l. 391 : 214 opérations par octet
« à un débit d'entrée compressé égal au lien (12,2 Go/s) » ; « au débit du disque, 926 ». La
phrase du ch. 09 dit « la carte attend le disque » : le budget qui s'applique est 926.
**Correction.** « environ 926 opérations par octet compressé au débit du disque (214 au débit du
lien) ».

### m13. Le critère C9 manque, et « dix critères sur douze » compte C7 deux fois
**Où.** ch. 07 FR l. 59-84 (tableau des critères et encadré) ; ch. 09 l. 9.
**Preuve.** `decisions/ARCHITECTURE.md` § 7.2 déclare C9, « rendement physique (mesuré ÷ plafond
au h mesuré) : publié, pas jugé ». `grep "C9\|rendement"` sur les dix chapitres FR et sur
`moteur/O-pour-le-memoire.md` : 0 occurrence. Le tableau a douze lignes parce que C7 y figure
deux fois (plafond, écart).
**Correction.** Publier C9 (ou dire qu'il n'a pas été calculé et pourquoi) ; écrire « dix lignes
sur douze tiennent (C7 en deux lignes) ; C9 publié ».

### m14. Q8_0 : « |q| tient sur 7 bits plus le signe »
**Où.** ch. 05 FR l. 47.
**Preuve.** Pour q = −128, |q| = 128 = 2⁷ demande 8 bits ; la conclusion (au plus 18 bits
significatifs) tient parce que 128 n'a qu'un bit significatif, ce que le ch. 04 FR l. 369 écrit
correctement (« |q| ≤ 128, à 7 bits significatifs au plus »).
**Correction.** Reprendre la formulation du ch. 04.

### m15. « 11,4 ms … soit 2,4 % du pas »
**Où.** ch. 07 FR l. 266-268 ; annexe A, bloc 3 (« au plus 2,4 % »).
**Preuve.** 12 251 136 o / 1,07 Go/s = 11,45 ms ; 11,45 / 457 = **2,5 %** (2,4 % suppose 1,10 Go/s).
**Correction.** 2,5 % (ou dire quel débit donne 2,4 %).

### m16. Scores d'attention en f64 : « au plus 0,15 ms »
**Où.** ch. 04 FR l. 400.
**Preuve.** 64 × 4 096 × 64 × 2 = 33,6 Mflop ; à 0,2 Tflop/s, **0,168 ms**.
**Correction.** « environ 0,17 ms ».

### m17. La table du format corrige la spécification sans le dire
**Où.** ch. 02 FR l. 109 : LUT de 432 × 16 384 = 7 077 888 o (6,75 Mio).
**Preuve.** `decisions/ARCHITECTURE.md` § 4.6 écrit « 36 × 3 × 4 × 16 Kio = 6,9 Mo pour le 120b »,
qui n'est ni 7,08 Mo ni 6,75 Mio. Le chapitre donne le bon chiffre en silence ; le SOCLE demande
de dire ce qui a changé.
**Correction.** Une phrase (« la spécification écrit 6,9 Mo ; c'est 7,08 Mo, 6,75 Mio ») et le
point dans la liste des précisions à porter à l'arbitre.

### m18. La comparaison de mémoire n'utilise pas la base balayée
**Où.** ch. 07 FR l. 120, 133-135, 381 ; résumés (« quand llama.cpp en tient 10,9 Go »).
**Preuve.** 10,93 Go est la pointe de `fit` à 6 fils, séance du 15 octobre
(`mesures/base-gpt-oss/120b/resume.csv`). La ronde a mesuré la pointe de chaque configuration
balayée (`base-2026-10-16-passes.csv`, colonne `pointe_et_mo`) : `fit -t 16`, la base de C6,
tient 11 355 et 11 483 Mo, **11,42 Go** en moyenne. Le chiffre publié n'est pas faux (il est
étiqueté « publiée ») et il est prudent ; mais C6 et la mémoire comparent deux bases différentes.
**Correction.** Ajouter la pointe de `fit -t 16` (11,42 Go, × 29,7) à côté de 10,93 Go.

### m19. « 26 s au lieu de 7 min 50 s, × 17,5 »
**Où.** ch. 06 FR l. 422 ; ch. 07 FR l. 260.
**Preuve.** 470 / 26 = 18,1 ; × 17,5 est le rapport des débits (27,15 / 1,554 jetons/s, passes
`s2-11` à `s2-14` de `o-jetons-s.csv`), qui donnent 26,1 s contre 455,7 s (7 min 36 s).
**Correction.** Donner des durées et un rapport tirés des mêmes passes, ou dire que × 17,5 est
le rapport des débits moyens.

### m20. Génome à 2 bits : « 3,26 jetons/s, contre 1,90 » compare deux planchers
**Où.** ch. 09 FR l. 192.
**Preuve.** 1,90 est le plancher en série de la passe 03 (1,904, `vitesse-2026-10-16-passes.csv`) ;
la passe 03 mesure 2,18 jetons/s. Le calcul (0,520 × (375,1 + 80,7) + 69,3 = 306,3 ms) est juste.
**Correction.** « un plancher de 3,26 jetons/s, contre 1,90 aujourd'hui ».

### m21. Des chiffres des sources recopiés dans les chapitres du chemin et du cache sans la mise à jour du ch. 07
**Où.** ch. 01 FR l. 369 et ch. 06 FR l. 468 : « −12 % sous un bruit de 12 % » ; ch. 07 FR
l. 393 : « −12 % sous un bruit de 11 % à 12 % ».
**Preuve.** Le ch. 07 FR l. 270 publie la série déclarée : −12,3 % pour un seuil de 26,8 %, soit
un bruit de 11,9 %. Même famille que m1.
**Correction.** « −12,3 % sous un seuil de 26,8 % (bruit 11,9 %) ».

### m22. Les légendes des listings du ch. 05 diffèrent entre les langues
**Où.** ch. 05 l. 101 et l. 271 (listings `lst:t2r-2x2` et `lst:t2r-decodee`).
**Preuve.** L'anglais traduit les commentaires français du code dans la légende (« four dot
products at a time … », « 1.11e-3 measured on gpt-oss-20b ») ; le français porte une autre
légende, plus courte. C'est le seul écart de fond trouvé entre les langues (le reste des écarts
de nombres est de forme : « 4,608 » contre « 4 608 », nombres dans les légendes de tableau).
Sans conséquence, puisque le code commenté en français est sous la légende.
**Correction.** Facultative : même contenu dans les deux légendes.

## Ce qui a été vérifié et tient (éloges justifiés)

**E1. Les données se refont au bit.** Les cinq outils du mémoire relancés n'ont changé aucun
fichier commité ; leurs témoins internes tiennent (31 chiffres refaits par
`tome2_reference_cache.py`, 0 écart ; `tome2_resultats.py`, aucun écart). C'est la propriété la
plus rare d'un mémoire et elle est là.

**E2. Les deux langues portent les mêmes nombres.** Multiensembles égaux dans les ch. 00, 03, 08,
09 et les annexes ; ailleurs, seuls des écarts de forme (séparateurs dans `\num`, numéros de
colonnes de tableau, légendes de listing enrichies en anglais, m22). Prose comparée sur les
passages critiques (C6, garde, codeur borné, discussion) : même sens, mêmes barres.

**E3. Les schémas sont exacts au bit**, contre § 4 et le code : en-tête fixe (tous les décalages
de 0 à 4 088, valeurs du 120b, SHA-256 `582bd40f…622d` = `second-chemin-120b.json`), entrée de
résident (128 o), enregistrement de table, entrée du répertoire (64 o, champs 0 à 56), en-tête
de partie (magie `0x30435254` = « TRC0 » petit-boutiste) et descripteur de flux, en-tête rANS,
LUT des géométries 1 (s 0-7, f−1 8-19, i−c 20-31) et 2 (s 0-3, f 4-16, i−c 17-31), emplacement
SoA (4 147 200 / 4 406 528 / 4 418 048 / 13 254 144), structures de l'ABI (`DescDecodage` et
`DescGemv` 32 o, `ParamsRope` 48 o, `ParamsAttention` 32 o, assertions de `abi.rs`), entrée
`.kld` (n_v = 2⌈n/2⌉ + 4 = 201 092, `kld.rs`), case de la boîte aux lettres
(s = 64t + ℓ + 1). Vingt noyaux `__global__` comptés dans les sources ; versions des dépendances
égales à `Cargo.lock` ; options `-O3 -std=c++17` sans `--use_fast_math` dans `build.rs`.

**E4. Les démonstrations vérifiées tiennent**, hypothèses et étapes : les trois lemmes du rANS et
les deux contrôles gratuits ; le décodage parallèle des voies (deux formes : ballot/popc et somme
cumulée, et l'unicité de la renormalisation, y ≥ 16 f) ; la reconstruction exacte et l'expert
d'origine dans le GGUF ; l'identité des deux codeurs et la borne de mémoire (502 252 544 o) ;
le lemme d'exclusion de l'IOCP ; la visibilité de la boîte (membar.sys, TSO) ; la chaîne
d'étages et la loi de Little ; le pas d'un warp et la fenêtre de mots ; l'échelle E8M0 exacte
(sous-normaux compris) ; les sommes exactes en f32 et leurs témoins (2 160 < 2¹², 1 040 384 <
2²²) ; le combiner égal à l'hôte ; les sélections sur un ordre total ; l'optimalité de Belady
(échange en trois phases) ; LRU N-compétitif et son pire cas ; les règles B et P ; l'étage RAM
inclusif ; **la falaise du LRU partagé** (les trois points, et le corollaire : 11,98 % et
3,04 %, 140 emplacements = 1 855 580 160 o) ; l'ordre des trois flux ; les tampons d'arrivée
(contre-exemple et règle corrigée) ; la garde ; l'exactitude de la déquantification ; la KL
comme fonction génératrice des cumulants ; Gibbs ; le plancher de l'instrument ; le palindrome
qui annule une dérive linéaire.

**E5. Les chiffres refaits par un second chemin tiennent** (échantillon) : sections du `.trc` et
leurs alignements (3 171 × 4 096 = 12 988 416, etc.) ; 224 656 o de TABLES ; T = 127 tuiles,
16 780 o de partie fixe, 3,8202 bits par poids ; collision 4 608 · 2⁻⁶⁴ = 2,50·10⁻¹⁶ ; pointes
du codeur 1,033 et 1,028 ; C6 : 1,9649 / 0,8838 = 2,2233 ; tableau de la base (bruits, écarts,
seuils 10,4 et 39,6 %) ; C4 apparié sur le 120b : d̄ = −0,05764 ± 0,01198 (4,8 erreurs-types) ;
quatre intervalles de Wilson à 0,1 point ; tableau KV f16/f32 (moyennes, KL > 0,1, p99) ;
rampe seule = 55 % de l'écart de llama.cpp ; 88 % de la KL portés par les bascules ; 70 et 77 %
des bascules portés par le KV f16 ; KV 155,7 Mo = 11,8 emplacements ; plancher en série 531,5 ms
et 544,7 ms ; e^(−22,5) du préremplissage ; modèle à deux étages (151 ms, 6,6 jetons/s) ; disque
`D:` (525, 402, 268 ms) ; génome à 2 bits (306,3 ms) ; préchargement (69,2 %, −11,0 %).

**E6. L'histoire des chiffres est tenue.** × 3,85 et × 2,79 à 2,89 sont barrés partout où ils
sont écrits comme résultats (EN et FR ; ils restent nommés, sans barre, là où le texte raconte
leur histoire : introduction, résumés, constat M2) et remplacés par × 2,22 garde comprise contre la base
balayée, comme le demandait la consigne ; 41,6 → 45,8 Go/s ; 0,47 Go → 0,47 Gio ; « 24 minutes »
→ 24 s ; la bande 8 ≤ i ≤ 17 → 9 ≤ i ≤ 17 ; D2 → D2 bis ; −1,7 → −1,6 au ch. 07 avec sa raison.
Chaque chapitre a sa section « Ce qui pourrait être faux », et elles nomment les vraies fragilités
(C6 entre deux séances, C4 sur une fenêtre, cause de G1 inconnue).

## Ce que ce jugement n'a pas vérifié (ce qui pourrait être faux ici)

- Pas de relance d'une passe : les chiffres sont confrontés aux journaux et CSV commités, pas à
  une nouvelle mesure (aucun calcul sur la carte, par consigne).
- Les figures pgfplots ne sont vérifiées que par leurs données (CSV régénérés égaux) et par
  quelques lectures du code TikZ, pas point par point à l'écran.
- Les citations bibliographiques (adresses, dates) et les numéros de chapitres du Tome I n'ont
  pas été rouverts un à un.
- Les journaux bruts du lot K (`k1-*.json`, `k3/`) et de l'épreuve (`c8-juge.json`) sont lus à
  travers les notes des lots et les CSV dérivés, pas champ par champ.
- La parité EN/FR est mesurée sur les nombres et lue sur les passages critiques ; une nuance de
  prose ailleurs a pu échapper.
- Classement grave / mineur : réponse par délégation du 2026-10-16, réversible. Critère : est
  grave ce qui laisse le tome affirmer deux résultats incompatibles ou un chiffre de verdict faux ;
  le reste est mineur.

## Outil et reproduction

```
python -I -X utf8 memoire/outils/tome2_juge.py            # parité EN/FR, puis recalculs
python -I -X utf8 memoire/outils/tome2_juge.py --casser   # témoin : doit dire « tombe », code 0
```

## Reprise (2026-10-16)

Rédacteur de la reprise : agent « reprise du Tome II après le jugement », qui n'a pas écrit ce
jugement. Chaque objection a été refaite avant d'être corrigée, depuis les CSV commités, par un
second chemin commité avec la reprise : `memoire/outils/tome2_reprise.py` (35 chiffres refaits,
0 écart ; 24 contrôles « chiffre faux seulement barré », 12 par langue ; témoin `--casser` : la
génération de la passe 05 faussée de 1 %, huit contrôles tombent, « tombe », code 0). Toutes les
objections du juge se confirment ; aucune n'est contestée. Chaque correction est faite dans les
deux langues ; ce qui était faux et qu'un lecteur a pu lire est barré (`\barre`) à sa place, avec
ce qui le remplace et d'où venait l'erreur. Commits `b0a632b` à la construction finale.

| Obj. | Où (EN et FR) | Ce qui est fait | Barré ? |
|---|---|---|---|
| **G1** | ch. 04 l. 543 ; ch. 07 l. 338 | Phrase « 5·10⁻¹¹ … elles disparaissent avec elle » barrée ; remplacée, avec renvoi au théorème des deux régimes (`thm:t2r-amplification`) et à `sec:t2r-f32-theorie` : terme sans bascule ÷ 8 192², terme des bascules ÷ 8 192, borne ≈ 3,8·10⁻⁷ nat, sous le pas du format ; la mesure (−0,00048, zéro de l'instrument) reste seul juge. | oui |
| m1 | ch. 01 (tableau de la ronde, paragraphe de la garde), ch. 03 (garde sur le chemin), ch. 06 (coût mesuré, « ce qui pourrait être faux ») | −1,6 % et 5,2 à 5,4 ms partout ; 1,900152 / 1,931729 − 1 posé au ch. 06 ; source : `vitesse-2026-10-16-passes.csv`. | oui : « 5,2 à 5,3 ms » et « −1,7 % » de la note du lot O, avec leur cause (passe 07 non comptée ; débits arrondis) |
| m2 | ch. 01, 06, 07 | Bruit 10,97 % ; « 2 × 10,97 + 3 = 24,9 % ». | non (arrondi, verdict inchangé) |
| m3 | ch. 09 l. 49 et tableau l. 40 | « un peu plus de la moitié (1,55 Go/s utiles) à deux tiers (1,85 Go/s, disque seul) de ce que le Tome I mesurait en lectures aléatoires de 16 Mio (2,82 Go/s) » ; le tableau dit « aléatoires, profondeur 1 / 4 ». | oui : « le tiers … en grands blocs séquentiels » |
| m4 | ch. 02 l. 412 | « lectures aléatoires de 4 Mio en profondeur 4 (2,58 Go/s) » ; le séquentiel 4 Mio du Tome I (1,04 à 1,63 Go/s) cité ; « environ 2 % (23,6 / 1 153 = 2,05 %) ». | oui : « débit séquentiel » |
| m5 | ch. 05 l. 147 | Δω à la paire 9 posé pas à pas : θ₉ = 0,0350, r = 0,0975 (OpenAI) et 0,1 (llama.cpp), Δω ≈ 8,5·10⁻⁵ rad par position. | oui : 8,8·10⁻⁵, avec sa source (note du lot R) |
| m6 | ch. 04 (titre, tableau, liste) | « tombe de 0,9 et 1,1 % (une pire passe par processus) », calcul posé. | oui : « de 0,9 % » (premier processus seul, note du lot K) ; le titre et le tableau sont corrigés sans barre |
| m7 | ch. 03, 06, 07, 09 | β = 16,2 % (déf. `t2res-def:reel`), seuil 35,4 % contre + 30,4 % : verdict inchangé (non franchi). | oui : « 21 % », avec ce qu'il mesurait (écart ÷ moyenne de A) |
| m8 | ch. 03 (figure E2, paragraphe de l'ABBA) | × 1,335 = médianes des huit passes A (V 2,851, N 2,135), + 33,5 % ; les médianes par passe affichées donnent 1,327, dit. | oui : « écart de 25 % » (c'est 1 − 1/1,335) |
| m9 | ch. 02 (légende) ; `figures/tome2/schemas/format.tex` (`\TdFmtCodeur`) | Barre du paquet à 0,502 Go sur l'axe en Go ; légende « ≈ 0,50 Go, soit 0,47 Gio : 502 252 544 o ». | oui (légende) : « 0,47 Go » du lot F |
| m10 | ch. 02 l. 75 (légende de `\TdFmtEntete`) | « huit octets par rangée, sauf deux rangées comprimées : sections (128 o, 136 à 263, trois rangées) et réservé (3 824 o, 264 à 4 087, une rangée) ». | non (légende imprécise, pas un chiffre faux) |
| m11 | ch. 04 l. 240 et l. 296 | 383 ms de disque mesurées au jalon (`t2res-sec:c5`), 157 ms nommées comme prédiction du Tome I. | oui (l. 240) : « 157 ms » présenté comme un fait |
| m12 | ch. 09 l. 190 | « environ 926 opérations par octet compressé au débit du disque ». | oui : « 214 », avec ce qu'il est (budget au débit du lien) |
| m13 | ch. 07 (tableau, encadré, nouveau paragraphe `t2res-sec:c9`) ; ch. 09 l. 9 | **C9 calculé et publié** (jamais calculé avant) : plafond de l'équation du jeton du Tome I (ℰ = 1, t_lat = 0) au h mesuré, max(t_disque, t_PCIe, t_déc + t_GEMV) + T₀ ; J1 passe 1 : 386,2 ms contre 457,4, **rendement 0,84** (passe 6 : 0,84) ; ronde : 0,64 à 0,82. Ligne C9 au tableau. Compte : « des douze critères, onze jugés, neuf tiennent entiers ; C9 publié, pas jugé ». | oui : « Dix critères tiennent sur douze » (dix lignes, C7 deux fois, C9 absent) |
| m14 | ch. 05 l. 47 | « \|q\| ≤ 128 a au plus 7 bits significatifs », formulation du ch. 04. | oui : « 7 bits plus le signe » (faux pour q = −128) |
| m15 | ch. 07 l. 266-268 ; annexe A, bloc 3 | 11,45 ms / 457 ms = 2,5 % ; la prédiction déclarée (2,4 %, avec 1,1 Go/s et 460 ms, `seuils-declares.md`) est gardée comme déclaration et sa base dite. | non (la déclaration est un fait daté ; elle n'est pas réécrite) |
| m16 | ch. 04 l. 400 | « environ 0,17 ms » (3,36·10⁷ opérations à 0,2 Tflop/s). | oui : « au plus 0,15 ms » |
| m17 | ch. 02 l. 109, tableau des précisions, « Il reste » | La spécification écrit 6,9 Mo ; c'est 7 077 888 o = 7,08 Mo = 6,75 Mio ; ajoutée comme précision **T2** à porter à l'arbitre (treize précisions au lieu de douze). | oui : « 6,9 Mo » cité de § 4.6 |
| m18 | ch. 07 (§ mémoire, pente, synthèse) ; ch. 01 l. 337 ; résumés | Pointe de `fit -t 16` : 11 355 et 11 483 Mo, 11,42 Go, × 29,7 ; les pentes gardent la base publiée (mesurée sur les deux modèles, la plus favorable à llama.cpp), dit. | non (le chiffre publié n'était pas faux) |
| m19 | ch. 06 l. 422 ; ch. 07 l. 260 | 26 s contre 7 min 36 s, × 17,5, rapport des débits moyens des passes s2-11 à s2-14 (27,15 contre 1,554). | oui : « 7 min 50 s » (absent de ces passes) |
| m20 | ch. 09 l. 192 | « un plancher de 3,26 jetons/s, contre un plancher de 1,90 » ; la passe 03 mesure 2,18, dit. | non (présentation) |
| m21 | ch. 01 et 06 (« ce qui pourrait être faux », coût mesuré), ch. 07 l. 393 | « −12,3 % sous un seuil de 26,8 % (bruit 11,9 %) ». | non (précision) |
| m22 | ch. 05 (listings `lst:t2r-2x2`, `lst:t2r-decodee`) | Même contenu dans les deux légendes : le français cite les commentaires du code, l'anglais porte la phrase sur les accumulateurs. | sans objet |

Décisions prises par délégation (réponse par délégation du 2026-10-16, réversible) :
- C9 se calcule avec le plafond de l'équation du jeton du Tome I sans spéculation ni latence
  restante, sur les termes déjà publiés du plancher (`res-plancher.csv`) : c'est la seule lecture
  de « plafond au h mesuré » qui n'introduit aucun chiffre neuf ; le max est le disque dans toutes
  les passes, le rendement mesure donc la latence de lecture non cachée.
- Les déclarations datées (2,4 % de la ronde) ne se réécrivent pas : on dit leur base. Les
  arrondis (m2, m10, m21) se corrigent sans barre ; tout chiffre faux qu'un lecteur a pu prendre
  pour une mesure ou un calcul juste se barre.
- `\barre` (ulem) ne supporte pas `\SI` hors mode mathématique : les valeurs barrées s'écrivent en
  texte simple (`7\,min\,50\,s`) ou en math (`$\num{5e-11}$`) ; constaté à la construction
  (« Extra } » au ch. 07), corrigé.

Ce que la reprise n'a pas fait : aucune passe neuve (aucun calcul sur la carte, par consigne) ;
la série unique troncons contre `fit -t 16` en palindrome reste aux travaux futurs ; la parité
EN/FR des nombres est inchangée hors ch. 05, où l'écart de forme a diminué (deux légendes
alignées).

Reproduction :

```
python -I -X utf8 memoire/outils/tome2_reprise.py            # 0 écart, code 0
python -I -X utf8 memoire/outils/tome2_reprise.py --casser   # témoin : « tombe », code 0
python -I -X utf8 memoire/outils/tome2_juge.py               # parité EN/FR et recalculs du juge
./memoire/construire.sh tome2                                # les deux PDF
```
