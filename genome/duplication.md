# La duplication de gènes dans gpt-oss-20b : parenté des experts, mesurée

Sujet « duplication » de l'étude du génome des poids (idees/biomimetisme-genome-des-poids.md § 5 bis et
§ 5 ter). Rédigé les 2026-10-16 et 17. Étiquettes : **[mes.]** mesuré ici, outil et journal commités ;
**[calc.]** calculé ; **[litt.]** littérature, non reproduite. Dérivations entières :
`genome/duplication-derivations.md`. Seuils déclarés avant la mesure : `mesures/genome/duplication/
00-seuils-declares.md` (avec son addendum et ses corrections barrées, toutes antérieures à la lecture de
l'échantillon). Outils : `outils/genome/duplication/`. Données : `mesures/genome/duplication/` (journaux
JSON, `csv/`).

---

## 0. En bref

**Verdict : la duplication ne bat pas la frontière.** Elle existe, elle se mesure, et elle vaut un
millième de bit.

1. **Les experts d'une couche ne sont pas des copies l'un de l'autre, même à une permutation des
   neurones près.** Après l'appariement optimal des 2 880 neurones (algorithme hongrois), le cos moyen
   des rangées appariées vaut 0,04 (gate), 0,03 (up), 0,07 à 0,11 (down) ; une paire de hasard rend 0,04
   [mes.]. Le meilleur parent de chaque enfant de l'échantillon, cherché parmi 63 candidats (31 de sa
   couche, 32 de la précédente), vaut 0,005 à 0,04 bit par poids en gain gaussien (§ 2) ; le témoin
   planté à ρ₀ = 0,5 est retrouvé à 0,2077 bit pour 0,2075 attendus, permutation retrouvée à 100 %.
2. **Sans perte (D1), le parent rend en moyenne 0,0034 bit par poids sur les codes MXFP4, dont
   0,0016 se retrouvent avec un parent de hasard** : la part propre à la parenté est 0,0019 bit.
   Coûts ajoutés (permutation 1,16·10⁻³, tables 1,48·10⁻³) compris, D1 passe sous A_ctx sur
   21 des 48 matrices : **ne marche pas** (seuil : les 48).
3. **Avec perte, à reconstruction identique à la base de B (D2b) : 0,0028 bit de gain moyen, dont
   0,0012 au hasard** ; la frontière de 2,6441 bits descendrait au mieux à 2,6429. **Ne marche
   pas** (24 matrices sur 48 passent le seuil).
4. **La mutation soustraite (D2) perd** : coder l'enfant comme α ⊙ parent + résidu coûte 0,49 bit
   de PLUS que le même quantificateur sans parent, parce que la soustraction fait sortir l'enfant de la
   grille MXFP4 où il était (dérivations, § 4).
5. **La mutation tronquée** (l'enfant servi par α ⊙ parent, résidu jeté) n'explique que 4,7 % de
   l'énergie des poids et rend 24 à 121 % (moyenne 91 %) d'erreur sur la sortie de l'expert, entrées
   réelles, biais exacts gardés : autant ne rien servir. Le parent brut (sans α) fait 29 à 255 %.
6. **Le paralogue fonctionnel ne sauve rien** : servir un expert manquant par le meilleur autre expert
   résident laisse 79 % (couche 0), 84 % (8), 66 % (16), 33 % (23) de l'énergie de sa sortie en erreur
   (hasard : 95, 94, 72, 47 %) ; dans la sortie de la couche, ~~**substituer n'est jamais meilleur que
   retirer l'expert**~~ (16,7 contre 13,3 % ; 13,9 contre 9,2 ; 7,1 contre 7,6 ; 3,7 contre 3,7 %).
   Corrigé : la phrase est fausse sur ses propres nombres, refait le 2026-10-29 par expert depuis `mesures/genome/duplication/csv/paralogues.csv` (rédaction du Tome III, chapitre de la duplication ; refait par le juge de la rédaction, `memoire/tome3/JUGEMENT-redaction-fr.md` § 3.3) : substituer fait mieux que retirer pour 4 experts sur 32 (couche 0), 5 sur 32 (8), 25 sur 31 (16) et 21 sur 31 (23) ; en moyenne 0,0707 contre 0,0757 à la couche 16, 0,0368 contre 0,0370 à la 23. La conclusion tient : un paralogue ne vaut pas la base.
7. **L'arbre le plus économe** (couche 23, la plus « parente », 496 paires) gagne 0,0212 bit par poids en
   borne gaussienne, ≈ 0,004 en vrais bits [calc. sur mes.], avant 0,0026 de coûts ajoutés. Sa meilleure
   arête, (23, 17) ← (23, 31), est le meilleur cas trouvé dans le modèle : 0,017 bit sans perte. Sur
   gpt-oss-120b (couche 18, 8 experts), le même tableau : paires à 0,003 à 0,005 bit, hasard 0,0016.
8. **Où est le bruit, où est la structure.** (a) Une part de la structure entre experts est **commune à
   la couche**, pas propre à une paire : le parent de hasard (mêmes colonnes d'entrée, neurones dans un
   ordre quelconque) reprend 46 % du gain en moyenne, et 88 à 94 % dans la couche 0 (des statistiques
   par colonne d'entrée partagées par les 32 experts ; le sujet predictif-elagage les prend comme
   « contexte de colonne »). (b) La parenté propre croît avec la profondeur (couche 23 : D1 gate 0,0082
   contre 0,0019 au hasard ; un moyeu, l'expert 31) mais reste sous le centième de bit. (c) Le reste est
   du bruit pour toute duplication : le meilleur parent explique 1 à 9 % de l'énergie des poids d'un
   enfant (au plus 16 % pour une seule matrice : down de (0, 24), gate de la meilleure arête).
9. **Ce que les mesures disent de chercher ensuite** (§ 7) : pas une autre parenté, mais l'erreur de
   SORTIE comme juge. Un ECSQ à pas commun (Gish et Pierce 1968) atteint 4,29 % d'erreur de poids vers
   1,5 bit, loin sous la frontière, mais son erreur de sortie va de 0,63 à 4,5 fois celle de la base selon
   l'expert [mes.] : ce qui compte est la place de l'erreur, pas sa taille. Le mécanisme biologique le
   plus prometteur d'après nos chiffres est donc l'**allocation par l'usage** (plasticité hebbienne :
   un poids vaut ce que ses entrées réelles le font peser), que le sujet predictif-elagage mesure déjà
   (ECSQ par classe κ : 2,3743 bits à l'erreur de sortie de la base ; sensibilité hebbienne : 1,76 à
   2,18 bits prédits). La duplication ne lui ajoute que 10⁻³ bit.

## D'où on part, où on va

**Au départ** : l'hypothèse de Stone (§ 5 bis) : « les experts d'une couche (ou de couches voisines) sont
parents : stocker un expert parent et, pour chaque descendant, une petite mutation coûte moins de bits
que l'expert entier ». La frontière : 3,8431 bits sans perte (A_ctx), 2,6441 bits pour la base seule à
4,2920 % d'erreur. L'état de l'art (genome/00-etat-de-l-art.md § 2.3) : des fusions d'experts sur BF16
(MC-SMoE, HC-SMoE, D²-MoE, Sub-MoE), jugées en précision de tâches, jamais en bits sur des codes de
4 bits ; la carte du modèle ne dit pas si les experts de gpt-oss sont nés par copie.

**Ce que ce travail établit** : la parenté des experts de gpt-oss-20b mesurée sur les codes MXFP4 et sur
les poids, à une permutation près (la seule symétrie de l'expert), sur la même couche et la couche
voisine ; son coût exact en bits (information mutuelle, coûts ajoutés comptés) ; l'arbre le plus
économe ; l'erreur de sortie d'une mutation tronquée et d'un paralogue sur les entrées réelles. La
duplication est réfutée par les nombres, avec la part de bruit et la part de structure.

**Ce qui reste** : § 8.

---

## 1. La question, posée en bits

Un enfant c (couche ℓ) codé sachant un parent p (déjà décodé) coûte H(c | p) au lieu de H(c) ; le gain est
l'information mutuelle I(c ; p), moins ce qu'il faut stocker pour relier l'enfant au parent. Pour un
réseau, une seule liberté rend deux experts comparables : **permuter les neurones cachés** ne change pas
la fonction (dérivations, proposition 1). La duplication de Stone devient donc : max sur p et sur Π de
I(c ; Π p), contre 3,84 bits.

## 2. La parenté brute : écran, appariement, spectre (poids seuls)

### 2.1 L'écran (borne haute, sans bijection)

`ecran_parente.py` : pour chaque rangée cible (gène), le meilleur |cos| parmi toutes les rangées de même
rôle des 31 autres experts de la couche (89 280 candidats), sans exiger d'appariement un à un : c'est la
borne haute d'une parenté gène par gène. Couches 0 à 4 (journal interrompu, `ecran-20b-interrompu-
couches-0-4.log`, arrêté pour libérer la mémoire) [mes.] :

| rôle | ρ̄ intra | témoin de hasard | gain gaussien |
|---|---|---|---|
| gate | 0,12 à 0,21 | 0,084 | 0,010 à 0,039 bit |
| down | 0,32 à 0,44 | 0,076 à 0,108 | 0,09 à 0,18 bit |

Le témoin colle à la borne calculée √(2 ln(2N)/n) = 0,092 (dérivations § 2). Le témoin planté (ρ₀ = 0,9,
`ecran-temoin-planter-0.9.json`) est retrouvé à 0,900 et 1,198 bit, et le dictionnaire de hasard ne le
voit pas (0,083).

### 2.2 L'appariement un à un (la vraie parenté d'expert à expert)

`paires_arbre.py` : coût Σ_rôles cos² entre neurones, affectation hongroise (scipy, Crouse 2016), score
= moyenne de −½ log₂(1 − cos²) sur les neurones appariés. Couche 12, quatre experts [mes.,
`paires-temoin-planter-0.5.json`] :

| paire | cos gate | cos up | cos down | score (bit/poids) |
|---|---|---|---|---|
| (0, 2) | 0,044 | 0,034 | 0,108 | 0,0053 |
| (0, 3) | 0,039 | 0,034 | 0,106 | 0,0050 |
| (2, 3) | 0,049 | 0,034 | 0,107 | 0,0049 |
| hasard | 0,040 | 0,041 | 0,039 | 0,0016 |
| plantée ρ₀ = 0,5 | 0,500 | 0,500 | 0,500 | 0,2077 (attendu 0,2075) |

Le gate et le up appariés sont au niveau du hasard ; seul down porte un peu de structure.

### 2.3 Le meilleur parent de chaque enfant de l'échantillon

`mutation.py` (63 candidats par enfant) ; tableau complet : `csv/scores-parente.csv` [mes.].

| enfant | parent choisi | score du parent (bit) | médiane intra | médiane couche précédente | même indice, couche précédente | D1 moyen sur 3 rôles | D1 au hasard |
|---|---|---|---|---|---|---|---|
| (0, 0) | (0, 9) | 0,0226 | 0,0169 | — | — | 0,0025 | 0,0024 |
| (0, 8) | (0, 9) | 0,0214 | 0,0169 | — | — | 0,0048 | 0,0047 |
| (0, 16) | (0, 9) | 0,0341 | 0,0200 | — | — | 0,0106 | 0,0093 |
| (0, 24) | (0, 9) | 0,0324 | 0,0207 | — | — | 0,0019 | 0,0014 |
| (8, 0) | (8, 31) | 0,0251 | 0,0097 | 0,0087 | 0,0095 | 0,0043 | 0,0002 |
| (8, 8) | (7, 30) | 0,0118 | 0,0074 | 0,0068 | 0,0044 | 0,0016 | 0,0003 |
| (8, 16) | (7, 11) | 0,0091 | 0,0054 | 0,0047 | 0,0058 | 0,0013 | 0,0005 |
| (8, 24) | (7, 24) | 0,0147 | 0,0072 | 0,0074 | 0,0147 | 0,0020 | 0,0002 |
| (16, 0) | (16, 17) | 0,0268 | 0,0093 | 0,0080 | 0,0176 | 0,0044 | 0,0001 |
| (16, 8) | (16, 24) | 0,0048 | 0,0040 | 0,0036 | 0,0036 | 0,0008 | 0,0007 |
| (16, 16) | (16, 6) | 0,0045 | 0,0035 | 0,0032 | 0,0032 | 0,0005 | 0,0001 |
| (16, 24) | (16, 11) | 0,0101 | 0,0046 | 0,0044 | 0,0030 | 0,0010 | 0,0001 |
| (23, 0) | (23, 22) | 0,0425 | 0,0049 | 0,0042 | 0,0100 | 0,0076 | 0,0007 |
| (23, 8) | (23, 16) | 0,0171 | 0,0047 | 0,0035 | 0,0040 | 0,0021 | 0,0006 |
| (23, 16) | (22, 13) | 0,0246 | 0,0049 | 0,0050 | 0,0088 | 0,0057 | 0,0009 |
| (23, 24) | (23, 11) | 0,0040 | 0,0032 | 0,0024 | 0,0023 | 0,0035 | 0,0027 |

Le parent sort à peine du lot : son score dépasse la médiane des candidats de 0,0008 à 0,038 bit.
Douze parents sur seize sont dans la même couche, quatre dans la précédente (dont un seul au même
indice : (7, 24) pour (8, 24)). Le même indice une couche plus bas n'est pas privilégié : son score est,
selon l'enfant, au-dessous ou au-dessus de la médiane des 32 candidats de la couche précédente.

Deux faits : dans la couche 0, les quatre enfants choisissent le même parent (0, 9) : un **moyeu**, pas
une lignée (sa structure est celle de toute la couche) ; dans la couche 8, l'expert 24 choisit (7, 24),
le même indice une couche plus bas, à 0,0147 bit : la seule trace d'une filiation par indice, et elle est
minuscule.

### 2.4 La famille : un sous-espace commun (couche 12)

`spectre_famille.py`, débit de Shannon d'une gaussienne de même spectre à ε = 4,29 % (remplissage
inverse) [mes., `spectre-c12.json`] :

| rôle | R iso | R diag | R KLT commune | témoin KLT | gain KLT − diag, net du témoin |
|---|---|---|---|---|---|
| gate | 2,271 | 2,262 | 2,144 | 2,225 | 0,072 |
| up | 2,271 | 2,262 | 2,180 | 2,245 | 0,056 |
| down | 2,271 | 2,084 | 1,980 | 2,195 | 0,070 |

Une base commune de la couche rendrait 0,06 à 0,07 bit (borne gaussienne), mais elle coûte n² = 8,3·10⁶
nombres par couche et par rôle, soit 0,5 bit par poids en f16 répartis sur 32 experts [calc.] : sept fois
son gain. Le gain diagonal de down (0,187) est déjà pris par les échelles E8M0, qui suivent la norme de
chaque rangée de down.

## 3. Le coût exact d'un expert codé comme mutation (l'échantillon)

Échantillon déclaré : enfants 0, 8, 16, 24 des couches 0, 8, 16, 23 (16 enfants, 48 matrices). Tableaux
par matrice : `csv/d1-sans-perte.csv`, `csv/d2-avec-perte.csv`, `csv/d2b-base.csv`. Verdicts :
`verdicts.json` (outil `synthese.py`, témoin `--casser` qui fait « marcher » D1 partout : tient).

Moyennes par couche et par rôle (4 enfants chacune), bits par poids [mes.] :

| couche | rôle | H(code \| κ) | D1 parent | D1 hasard | D2b parent | D2b hasard | ECSQ seule à 4,29 % | mutation soustraite | ECSQ + contexte parent |
|---|---|---|---|---|---|---|---|---|---|
| 0 | gate | 3,7686 | 0,0082 | 0,0072 | 0,0064 | 0,0056 | 1,564 | 1,882 | 1,562 |
| 0 | up | 3,7855 | 0,0064 | 0,0060 | 0,0050 | 0,0047 | 1,559 | 1,929 | 1,558 |
| 0 | down | 3,8185 | 0,0002 | 0,0001 | 0,0002 | 0,0000 | 1,049 | 1,283 | 1,043 |
| 8 | gate | 3,8208 | 0,0045 | 0,0004 | 0,0040 | 0,0003 | 1,538 | 2,049 | 1,533 |
| 8 | up | 3,8005 | 0,0008 | 0,0004 | 0,0006 | 0,0003 | 1,655 | 2,119 | 1,653 |
| 8 | down | 3,7984 | 0,0017 | 0,0001 | 0,0013 | 0,0000 | 1,626 | 2,168 | 1,619 |
| 16 | gate | 3,8099 | 0,0033 | 0,0004 | 0,0029 | 0,0002 | 1,490 | 1,999 | 1,485 |
| 16 | up | 3,8098 | 0,0007 | 0,0003 | 0,0005 | 0,0002 | 1,564 | 2,107 | 1,562 |
| 16 | down | 3,7988 | 0,0011 | 0,0001 | 0,0009 | 0,0000 | 1,568 | 2,177 | 1,564 |
| 23 | gate | 3,7978 | 0,0082 | 0,0019 | 0,0069 | 0,0013 | 1,449 | 2,091 | 1,439 |
| 23 | up | 3,7921 | 0,0041 | 0,0018 | 0,0031 | 0,0013 | 1,607 | 2,123 | 1,601 |
| 23 | down | 3,7892 | 0,0020 | 0,0001 | 0,0015 | 0,0000 | 1,584 | 2,121 | 1,579 |

(H(code | κ) est l'entropie d'ordre 0 sachant la classe d'échelle, par symbole ; A_ctx = 3,8431 compte
en plus les échelles, les tables et le codeur réel. Les débits ECSQ n'incluent pas les échelles,
0,034 bit, ni α pour la mutation, 0,0028 bit.)

Les verdicts, contre les seuils déclarés (`verdicts.json`) :

| mesure | ce qu'elle exige | résultat | verdict |
|---|---|---|---|
| D1 sans perte | gain > 2,64·10⁻³ (permutation + tables) sur les 48 matrices | gain moyen 0,0034, hasard 0,0016, net 0,0019 ; 21/48 | **ne marche pas** |
| D2 mutation soustraite | sous 2,6441 et sous l'ECSQ seule de plus d'un écart-type du hasard (3,0·10⁻⁴) | −0,486 bit en moyenne (pire que sans parent) | **ne marche pas** |
| D2c contexte parent (même reconstruction que l'ECSQ) | idem | +0,0016 bit, coût α compris ; 43/48 battent le hasard de plus d'un écart-type | gain réel, sans portée |
| D2b base + parent (même reconstruction que la base) | gain > 1,53·10⁻³ et > hasard sur les 48 | gain 0,0028, hasard 0,0012 ; 24/48 ; frontière 2,6441 → 2,6429 | **ne marche pas** |
| O sortie | D2 au plus l'erreur de la base, 4 couches sur 4 | base 6,4 %, mutation 8,6 % ; 4 enfants sur 16 sous la base | **ne marche pas** |

Le plus grand gain d'une seule matrice est 0,0170 bit (gate de (0, 16)), dont 0,0145 se retrouvent
au parent de hasard (net 0,0025) ; le plus grand gain net est 0,0109 bit (gate de (23, 0), parent
(23, 22)), puis 0,0098 (gate de (23, 16), parent (22, 13)). Rien n'approche le dixième de bit.

## 4. La mutation tronquée et la sortie de l'expert (entrées réelles)

Entrées : les états normés réellement routés vers chaque enfant (capture de l'éclaireur, 12 fenêtres de
511 jetons, `calib/h-Lll.f32`, empreintes SHA-256 dans chaque `mutation-cL.json`), au plus 2 048 jetons
par enfant ; sortie de l'expert en f64, biais compris ; témoin : les poids exacts rendent 0 [mes.].

Erreurs relatives en %, poids puis sortie [mes., `csv/t-o-sortie.csv`] :

| enfant | parent | jetons | base de B | mutation à ε ≈ 4,29 % | ECSQ seule à ε ≈ 4,29 % | mutation tronquée | parent brut (sortie) |
|---|---|---|---|---|---|---|---|
| (0, 0) | (0, 9) | 762 | 4,3 / 6,6 | 4,7 / 7,1 | 4,8 / 7,0 | 94,3 / 97,4 | 217,0 |
| (0, 8) | (0, 9) | 698 | 4,3 / 6,3 | 4,6 / 6,5 | 4,7 / 6,7 | 95,3 / 100,3 | 222,1 |
| (0, 16) | (0, 9) | 1 334 | 4,6 / 4,5 | 5,4 / 5,5 | 4,6 / 5,1 | 93,4 / 103,6 | 95,9 |
| (0, 24) | (0, 9) | 914 | 4,5 / 4,8 | 4,5 / 5,2 | 4,5 / 4,3 | 91,3 / 94,0 | 101,0 |
| (8, 0) | (8, 31) | 1 329 | 4,7 / 8,3 | 3,9 / 18,5 | 5,1 / 29,3 | 92,5 / 120,3 | 168,3 |
| (8, 8) | (7, 30) | 1 761 | 4,5 / 7,2 | 4,1 / 11,4 | 4,1 / 11,3 | 93,7 / 106,1 | 121,0 |
| (8, 16) | (7, 11) | 300 | 4,2 / 7,0 | 3,9 / 22,9 | 3,9 / 31,5 | 94,9 / 105,6 | 144,4 |
| (8, 24) | (7, 24) | 928 | 5,4 / 20,3 | 4,5 / 12,5 | 4,2 / 12,8 | 93,2 / 121,5 | 255,4 |
| (16, 0) | (16, 17) | 330 | 4,5 / 6,1 | 4,0 / 11,1 | 3,9 / 11,4 | 95,0 / 77,8 | 113,0 |
| (16, 8) | (16, 24) | 240 | 4,0 / 3,1 | 3,8 / 2,9 | 3,8 / 3,1 | 98,3 / 64,8 | 113,0 |
| (16, 16) | (16, 6) | 147 | 4,1 / 5,2 | 4,1 / 8,2 | 3,8 / 11,1 | 98,5 / 83,3 | 135,0 |
| (16, 24) | (16, 11) | 1 237 | 4,2 / 5,5 | 4,6 / 7,0 | 4,2 / 7,1 | 97,6 / 82,9 | 207,5 |
| (23, 0) | (23, 22) | 303 | 4,7 / 6,2 | 4,8 / 8,3 | 3,6 / 6,5 | 95,5 / 90,0 | 54,9 |
| (23, 8) | (23, 16) | 56 | 4,5 / 3,3 | 3,8 / 2,3 | 3,8 / 2,7 | 96,1 / 80,0 | 56,2 |
| (23, 16) | (22, 13) | 239 | 4,7 / 4,4 | 3,9 / 5,5 | 4,5 / 5,9 | 96,2 / 107,1 | 176,2 |
| (23, 24) | (23, 11) | 2 048 | 3,9 / 3,6 | 3,8 / 3,5 | 3,7 / 4,6 | 99,0 / 24,2 | 28,6 |
| **moyenne** | | | **— / 6,4** | **— / 8,6** | **— / 10,0** | **95,3 / 91,2** | |

Lecture :
- **La mutation tronquée garde 1 % à 9 % de l'énergie des poids** (moyenne 4,7 %) et rend 24 à 121 %
  d'erreur sur la sortie. Les valeurs sous 100 % des couches 16 et 23 viennent des biais : ils restent
  exacts (F32, hors de la question du codage) et portent une grande part de la sortie des experts
  profonds (pour (23, 24), le parent brut lui-même ne fait que 28,6 %). C'est l'erreur qu'on aurait en
  ne servant rien d'autre que les biais : la mutation tronquée n'apporte rien.
- **Même erreur de poids, erreur de sortie très différente** : l'ECSQ seule et la mutation tombent à
  3,6 à 5,4 % d'erreur de poids comme la base, mais l'erreur de sortie de l'ECSQ seule va de 0,63 à 4,5
  fois celle de la base : le pas commun efface les blocs de petite échelle, que la base garde. Le sujet
  predictif-elagage le voit de son côté (ECSQ à contexte d'exposant : 22 % d'erreur d'expert).
- (8, 24) est l'exception où la base elle-même rend 20,3 % : son erreur de sortie n'est pas uniforme
  non plus.
- Le choix du pas pour O est celui du balayage le plus proche de 4,29 % (pas d'interpolation possible
  sur une reconstruction) : d'où les erreurs de poids de 3,6 à 5,4 %.

## 5. L'arbre de parenté le plus économe

`paires_arbre.py --couche 23` : les 496 paires de la couche la plus « parente » de l'échantillon,
appariées une à une, puis l'arbre couvrant de poids maximal (Kruskal ; dérivations § 5)
[mes., `arbre-c23.json`] :

| quantité | valeur |
|---|---|
| score des paires : 10 % / médiane / 90 % / 99 % | 0,0031 / 0,0038 / 0,0138 / 0,0689 bit |
| témoin de hasard (8 paires) | 0,0016 bit |
| arêtes de l'arbre : min / médiane / max | 0,0037 / 0,0101 / 0,0892 bit |
| **gain de la couche codée par son arbre** (gaussien, borne haute) | **0,0212 bit par poids** |
| les quatre arêtes les plus lourdes | (17, 31) 0,089 ; (5, 31) 0,089 ; (15, 31) 0,077 ; (25, 31) 0,069 |

L'expert 31 est un **moyeu** : il porte les quatre arêtes les plus lourdes. C'est la seule trace d'une
famille dans les mesures.

**L'arête la plus lourde, mesurée en vrais bits** (`mutation.py --couche 23 --enfants 17 --parent 23,31`,
`mutation-arete-max-c23-e17-p31.json`) [mes.] :

| rôle | D1 parent | D1 hasard | D2b parent | erreur de poids de la mutation tronquée |
|---|---|---|---|---|
| gate | 0,0222 | 0,0003 | 0,0199 | 83,9 % |
| up | 0,0136 | 0,0004 | 0,0108 | 91,4 % |
| down | 0,0149 | 0,0001 | 0,0117 | 91,4 % |

Sortie de l'expert (17) : base 10,4 %, mutation à ε ≈ 4,29 % 15,3 %, mutation tronquée 109,9 %.
C'est le meilleur cas trouvé dans le modèle : 0,017 bit de moyenne, 0,014 net des coûts ajoutés, soit
3,84 → 3,83. Le rapport entre le gain réel sur les codes et le score gaussien vaut ici 0,017 / 0,089 =
0,19, et 0,0076 / 0,0425 = 0,18 pour (23, 0) ; appliqué à l'arbre, il donne **≈ 0,004 bit par poids pour
la couche 23 entière** [calc.], avant les coûts ajoutés (2,6·10⁻³) : un gain net de l'ordre du millième.

**Confirmation sur gpt-oss-120b** (`paires_arbre.py --modele 120b --couche 18 --experts 8`, 28 paires,
`paires-120b-c18-8experts.json`) [mes.] : scores 0,0030 à 0,0054 bit (hasard 0,0016) ; cos appariés
0,038 (gate), 0,032 (up), 0,094 (down) contre 0,040 au hasard. Le même tableau que sur 20b.

## 6. Les paralogues : servir un expert absent par un autre

`paralogues.py`, 32 experts par couche, au plus 96 jetons routés par expert, routage recalculé depuis
le routeur F32 du GGUF égal au routage capturé à 100 % (témoin) [mes.] :

| couche | ε meilleur paralogue (β optimal) | ε β = 1 | ε hasard | ε 5ᵉ choix du routeur | couche : substitué | couche : retiré |
|---|---|---|---|---|---|---|
| 0 | 0,792 | 1,401 | 0,945 | 1,215 | 0,167 | 0,133 |
| 8 | 0,842 | 1,439 | 0,936 | 1,239 | 0,139 | 0,092 |
| 16 | 0,658 | 0,749 | 0,721 | 0,924 | 0,071 | 0,076 |
| 23 | 0,335 | 0,435 | 0,467 | 0,564 | 0,037 | 0,037 |

Lecture : les sorties des experts se ressemblent davantage en profondeur, mais par une composante
**commune à tous** (le témoin de hasard tombe avec elles : 0,47 à la couche 23) ; ce qui est propre au
meilleur paralogue n'est que 0,13 au-dessus du hasard. La robustesse des paralogues du vivant (Gu et al.
2003) n'a pas d'équivalent ici : un défaut de cache se sert mieux par la base de B (erreur d'expert 5 à
8 %, § 4) que par le meilleur voisin (33 à 84 %).

## 7. Pourquoi l'idée échoue, et où chercher

**Le pourquoi chiffré.** Un gène dupliqué garde sa ressemblance tant que la sélection ne l'en éloigne
pas. Les experts de gpt-oss, eux, ont été entraînés pour être **différents** : le routeur n'envoie à un
expert que les jetons où il est utile, et deux experts qui se ressembleraient se partageraient les
mêmes jetons. La mesure le confirme : après la meilleure permutation, l'information mutuelle entre un
enfant et son meilleur parent est de l'ordre de 10⁻³ bit par poids sur 3,84, et ce qui en reste est
pour moitié ou davantage une propriété de la couche entière (les colonnes d'entrée, l'espace de sortie
de down), pas de la paire. Tronquer la mutation, c'est perdre l'expert : 96 % de son énergie est à lui.

**Ce que la mesure a vu en passant, et qui compte plus.** L'ECSQ seule (pas commun, contexte d'exposant)
tombe à 0,89 à 1,78 bit (moyenne 1,52, sans les 0,034 bit d'échelles) à 4,29 % d'erreur de POIDS, mais son erreur de SORTIE varie de 0,63 à 4,5 fois celle
de la base (§ 4). L'erreur de poids n'est pas le juge. Le levier n'est pas la parenté (une propriété des
poids entre eux) mais l'**usage** (une propriété des poids devant leurs entrées) : c'est l'allocation
hebbienne du sujet predictif-elagage, et c'est vers elle que nos chiffres orientent la ronde suivante
(réponse par délégation du 2026-10-17, réversible : c'est le seul mécanisme mesuré ici dont le gain se
compte en dixièmes de bit et non en millièmes).

## 8. Ce qui reste

- Le KL de la mutation tronquée n'est pas mesuré : son erreur de sortie (≈ 100 %) suffit à l'écarter ;
  le crochet `alterer_expert` de trc-reference le permettrait.
- ~~gpt-oss-120b n'est pas mesuré~~ : mesuré sur une couche et 8 experts sur 128 (§ 5) ; le coût exact
  (D1, D2b) et les paralogues n'y sont pas refaits.
- L'écran sur les 24 couches a été interrompu à la couche 4 (mémoire de la machine partagée).

## 9. Ce qui pourrait être faux

- **Le parent est choisi par un score gaussien sur les poids**, pas par le gain sur les codes. Un autre
  parent pourrait rendre un peu plus de D1. Borne : le meilleur score de toute la liste (0,043) borne le
  gain gaussien de tout parent ; le D1 réel est toujours sous le score (§ 3).
- **Une seule permutation par paire, jointe sur les trois rôles.** Des permutations par rôle seraient
  plus libres mais ne décriraient plus le même expert (la fonction exige la même Π). L'écran sans
  bijection (§ 2.1) borne ce que toute liberté de plus pourrait rendre.
- **L'échantillon** : 16 enfants sur 768, quatre profondeurs. La couche 23 montre une parenté plus forte
  que les autres ; les couches 17 à 22 ne sont pas mesurées.
- **Les entrées réelles** viennent de 12 fenêtres d'un seul corpus (celui de l'éclaireur) ; au plus
  2 048 jetons par enfant (78 à 96 pour les paralogues).
- **L'estimateur d'entropie** est biaisé vers le bas de ≤ 6,7·10⁻⁵ bit (Miller) : négligeable devant les
  gains rapportés, mais du même ordre que les plus petits (up de la couche 16).
- **La machine était partagée et chargée** (mémoire libre 0,7 à 2,6 Go) : les durées des journaux ne
  mesurent rien ; aucun chiffre de débit n'est rapporté.
