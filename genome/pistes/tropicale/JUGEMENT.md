# Jugement indépendant : la garde tropicale

Juge : rôle indépendant, sans part au travail de la piste. Écrit le 2026-10-22. Objet : le livrable
`genome/pistes/tropicale/garde-tropicale.md` (dernier commit de la piste `96ea31a`) et son verdict
« la garde tombe au seuil déclaré ».

## Verdict du juge

**Le chiffre principal tient, et le verdict avec lui.** Refait par mon propre chemin, sans une ligne
du code de la piste ni de `bascules.py` : **2 905 bascules attrapées sur 5 087 (57,1 %) pour
12 264 cellules signalées sur 122 640 (10 %)**, à l'unité près ; 80 % des bascules coûteraient
**32 623 cellules (26,6 %)**, à l'unité près. Le seuil 80 / 10 a bien été commité avant la lecture,
les témoins tombent quand on les casse. La garde tropicale, telle que déclarée, **ne vaut pas d'être
construite** sur ces journaux.

**Deux réserves sur la théorie, aucune sur la mesure** (§ 4) : le corollaire du « plafond de 4 % »
n'est vrai que pour une population homogène, et il n'explique qu'environ 1 point sur les 23 qui
manquent. Les deux ne touchent pas le verdict ; elles touchent la prédiction écrite pour G2 et la
manière dont le livrable présente le nombre de garde.

## 1. Le seuil a-t-il été déclaré avant la lecture ?

Oui, au sens où git peut le montrer.

| Commit | Heure (auteur = commettant) | Contenu |
|---|---|---|
| `69260f1` | 2026-10-21 23:22:18 | `seuil-declare.md` (seul commit de ce fichier, jamais modifié depuis) et `REPRISE.md` |
| `4b2a8eb` | 23:23:32 | premiers outils de lecture (`routage.py`, `temoins.py`) et premiers journaux |
| `77d8110` | 23:25:17 | le verdict à 57,1 % |

Le fichier `seuil-declare.md` a sa date de modification à 23:22:08, avant tout fichier de sortie de la
piste. Le seuil (80 % des bascules pour au plus 10 % des cellules) est celui de 05 § 3.1, mot pour mot,
et la marge qui décide (celle de B) est fixée dans la déclaration. La prédiction écrite (55 à 65 %,
donc un échec) se déduit du seul résumé publié par le lot R.

Ce que git ne peut pas prouver : qu'aucune lecture exploratoire n'a eu lieu avant 23:22. Les 222 lignes
de code commitées 74 secondes après le seuil étaient donc écrites avant lui ; écrire un lecteur n'est
pas lire. Petit désordre sans effet : les heures écrites dans les notes (« 23 h 25 » dans
`seuil-declare.md`, « 23 h 40 » pour le pas 2 dans `REPRISE.md`) ne concordent pas avec git
(23:22 et 23:23). L'ordre des commits est le bon ; l'horloge des notes est fausse de quelques minutes.

## 2. Le chiffre principal, refait par un autre chemin

Outil : `outils/pistes/tropicale/juge/juge.py`. Journal : `mesures/pistes/tropicale/juge/juge.json`
et `juge.log`. Python pur (`struct`, sans numpy), priorité « sous la normale » demandée au système, un
fil, aucune carte, verrou de la carte jamais pris (absent au moment des passes, attente prévue).

Ce qui diffère du chemin de la piste :
- lecture écrite à partir du seul format déclaré (§ 1 de la déclaration) et des empreintes SHA-256
  déclarées, vérifiées avant décodage (les trois concordent) ;
- pas de seuil interpolé : les 122 640 cellules sont **classées** par marge de B (ex aequo départagés
  par l'indice) et l'on garde les 12 264 premières ; le coût de 80 % est le plus court préfixe du
  classement qui contient ⌈0,8 × 5 087⌉ = 4 070 bascules.

| Grandeur | Piste | Juge |
|---|---|---|
| bascules (ensembles des 4 experts différents) | 5 087 | **5 087** |
| bascules A contre C (routage imposé) | 0 | **0** |
| cellules signalées / bascules attrapées au décile | 12 264 / 2 905 | **12 264 / 2 905** |
| part des bascules au décile | 57,1 % | **57,106 %** |
| τ₁₀ | 0,012410 | 12 264e marge 0,0124092 ; 12 265e **0,0124100** (= τ₁₀ de la piste, signalement strict « < τ ») |
| ex aequo à la frontière | non dit | **1** (aucune ambiguïté de comptage) |
| coût de 80 % | 26,6 % | **32 623 cellules, 26,600 %** |
| variante marge de A | 56,1 % | **56,12 %** |
| P(bascule en ℓ+1 \| bascule en ℓ), sinon | 26,6 % ; 3,4 % | **26,65 % ; 3,37 %** |
| racines de cascade attrapées (exploratoire) | 1 773 / 2 081 | **1 773 / 2 081 (85,2 %)** |

Par couche, au même classement global : 100 % à la couche 0, 86,0 à 91,0 % aux couches 1 à 4,
37,8 % (couche 21) à 60,5 % (couche 23) aux couches 8 à 23 : les fourchettes du livrable sont exactes.

Santé des journaux, vérifiée au passage : aucun expert hors de 0 à 31, aucun doublon dans un top-4,
aucune marge NaN, négative ou nulle dans A et B. Dans C, 1 879 marges négatives : attendu, puisque le
routage y est imposé et que la « marge » mesure alors 4e − 5e de l'ensemble imposé ; C ne sert qu'au
témoin du routage imposé.

Une remarque qui conforte la définition : en comparant les listes ordonnées plutôt que les ensembles,
on trouverait 11 028 « bascules ». La piste compare les ensembles, ce qui est juste : le top-4 est un
ensemble, l'ordre interne ne change pas les experts appelés.

## 3. Les témoins tombent-ils vraiment ?

Les miens, dans `juge.json` (`temoins_du_juge`), chacun avec sa cassure :

| Témoin | Attendu | Obtenu |
|---|---|---|
| J1 : un octet d'expert changé dans une copie de B, sur une cellule sans bascule | 5 088 | **5 088** |
| J2 : lecture au mauvais pas (7 octets) | refusée | **refusée** |
| J3 : marges de B permutées (graine 20261022) | 10 % ± 2 | **10,4 %** (la piste : 10,05 % avec sa graine) |
| J4 : marges oracles (0 aux bascules) | 100 % | **100 %** : le verdict « passe » était atteignable par cet instrument |
| J5 : 600 bascules non attrapées mises à marge nulle | 2 905 + 600 − bascules chassées de la tête = 3 441 | **3 441** (64 chassées) |

Correction barrée de mon côté : la première écriture de J5 attendait ~~2 905 + 600 = 3 505~~ ; elle
oubliait que les 600 cellules qui entrent en tête en chassent 600, dont 64 bascules. Le témoin a été
réécrit avec l'attendu exact, puis relancé ; l'écart initial venait de mon attendu, pas du compte.

Les témoins de la piste (T1 à T3) sont du même type et je n'en ai pas trouvé de mort : T2 et T3 sont
refaits ci-dessus par mon code. Je n'ai pas refait les huit quantiles de T1 (je retrouve le compte de
5 087 du résumé du lot R, pas ses quantiles), ni le contrôle croisé K3 d1 (9 sur 22).

## 4. Ce qui serait faux ou trop beau

### 4.1 Le corollaire du « plafond de 4 % » n'est pas général (réserve sérieuse, hors verdict)

Le livrable écrit : « Pour tenir 80 % des bascules sur 10 % des cellules, il faut κ ≤ 0,108, c'est-à-dire
au plus 4,0 % de cellules qui basculent », et la note pour le mémoire : « une garde à marge ne tient
80 / 10 que si moins de 4,03 % des cellules basculent ». La forme close est juste (ma quadrature de
Simpson, sans la forme close, redonne b = 79,993 % et P(B) = 4,0294 % en κ = 0,1079). Mais elle porte
sur **une seule population** : une loi de marge exponentielle, un seul σ. La garde réelle applique un
seuil global à 24 couches dont la marge moyenne va de 0,061 (couche 23) à 0,193 (couche 21) et dont
κ_ℓ va de 0,016 à 0,48.

Contre-exemple, `outils/pistes/tropicale/juge/juge_modele.py` (`juge-modele.json`) : 2 couches sur 24
à marges serrées (moyenne 10⁻⁴, σ = 10⁻³) et 22 couches à marges larges (moyenne 0,1, σ = 0,004), garde
à seuil global. **P(B) = 5,26 % et pourtant b = 85,9 % pour 10 % des cellules** : la garde tient 80 / 10
au-dessus du « plafond ». Le cas est construit, pas observé ; il suffit à montrer que le corollaire est
une propriété du modèle homogène, pas de « toute garde à marge ». De même, la phrase « une queue de δ
plus lourde ne fait que baisser ce plafond » est affirmée sans démonstration (l'ordre « plus lourde » n'y
est pas défini) ; elle est vraie dans le seul cas que la piste a calculé (δ empirique contre gaussien à
taux égal), pas prouvée.

Conséquence : la prédiction écrite pour G2 (« elle échoue si plus d'environ 5 % des cellules
basculent ») doit être lue comme une prédiction du modèle homogène. Un mode rapide dont les bascules se
concentrent dans des couches à marges serrées peut la démentir ; la piste le dit d'ailleurs à demi
(« un mode rapide dont l'erreur tomberait surtout aux couches 0 à 4 ferait mieux »).

### 4.2 Le nombre de garde n'explique presque rien de l'échec mesuré (trop beau)

Le livrable place côte à côte « il faut au plus 4,0 % de bascules » et « les deux rampes en font déjà
4,15 % », ce qui se lit comme une explication de l'échec. Au taux mesuré (5 087 / 122 640 = 4,148 %), le
modèle homogène donne κ = 0,1113 et **b = 78,8 %** (`juge-modele.json`) ; la mesure dit **57,1 %**. Le
nombre de garde rend compte d'environ 1 point sur les 23 qui manquent. Le reste vient de ce que le
livrable dit par ailleurs, et c'est là l'explication : l'hétérogénéité des couches (les couches 8 à 23
à 38-60 %) et les bascules secondaires des cascades, à marge encore large. Le nombre de garde est une
belle forme close ; il ne doit pas être présenté comme la raison de l'échec.

### 4.3 Points mineurs

- **La forme de la loi de bascule a changé après lecture** : la déclaration (§ 5) posait
  P = 2Φ(−m/σ) ; la piste a retenu Φ(−m/σ) parce qu'elle ajuste mieux. C'est dit (« forme 2Φ déclarée »
  parmi les échecs) et cela ne décide rien, mais le théorème et l'extrapolation reposent sur une forme
  choisie après la lecture : ils sont des modèles, étiquetés [mod.], et doivent le rester.
- **`REPRISE.md` n'est pas à jour** : le pas 4 dit encore « < 80 % dès s ≈ 1,4 », chiffre que le
  livrable a barré pour 1,3.
- **Seuil interne au même échantillon** : τ₁₀ est le décile des marges mesurées sur les journaux
  mêmes. Cela avantage la garde ; comme elle tombe quand même, le verdict n'en est que plus sûr.
- **Détection n'est pas réparation** : déjà dit par la piste et juste. Les journaux mesurent la
  perturbation de deux rampes exactes (l'attention), pas celle du mode rapide ; refaire une couche en
  exact n'y changerait rien. Le verdict est donc « la marge ne détecte pas assez », pas « la garde ne
  répare pas assez ».
- **Les 85,2 % des racines** sont reproduits à l'unité, mais restent une lecture choisie après coup ;
  leur étiquette « exploratoire » est la bonne, et G2 est la bonne suite.

## 5. Ce que le juge n'a pas refait

Les lois de la marge (gamma, Kolmogorov-Smirnov), la corrélation entre couches, le préchargement (aires
ROC 0,567 et 0,627), l'extrapolation en s, les figures T1 à T7 et le contrôle croisé K3 d1. Ils ne
décident rien ; ils ne sont pas éprouvés par ce jugement.

## 6. Fichiers

- `outils/pistes/tropicale/juge/juge.py` : le chiffre principal, le coût de 80 %, les couches, les
  cascades, les racines et les témoins J1 à J5 ;
- `outils/pistes/tropicale/juge/juge_modele.py` : le modèle homogène au taux mesuré, le témoin en κ\*,
  le contre-exemple au corollaire ;
- `mesures/pistes/tropicale/juge/juge.json`, `juge.log`, `juge-modele.json`, `juge-modele.log`.

Pour RECETTES.md : un comptage par classement explicite (et le nombre d'ex aequo à la frontière) est un
second chemin plus sûr qu'un seuil interpolé ; un témoin par cassure doit compter ce que la cassure
déplace (ici, les bascules chassées de la tête), sinon c'est l'attendu qui est faux.

---

# Second jugement (2026-10-27) : la garde à indices multiples, la mémoire du conflit (livrable § 12)

Juge : rôle indépendant, sans part au travail de la piste ni au premier jugement. Objet : le § 12 de
`garde-tropicale.md` (commits `50bf472` seuil, `9e31d9f` mesure, `6f3ef9e` livrable) et son verdict
« gain réel de +1,61 point, sous les 5 points déclarés : pas utile, et loin de 80 % ».

## 7. Verdict du juge

**Le chiffre principal tient à l'unité, et le verdict avec lui.** Refait par mon propre script, écrit à
partir de la seule déclaration `seuil-declare-indices.md` avant d'ouvrir le code de la piste :

| Grandeur (k = 1 226 cellules par fenêtre de test) | Piste | Juge |
|---|---|---|
| bascules (ensembles des 4 experts différents) | 5 087 | **5 087** |
| M0, marge seule : attrapées, b | 2 899 ; 56,99 % | **2 899 ; 56,988 %** |
| M1, f1 seul : égal à M0 pli par pli | oui | **oui** |
| M2, profondeur seule | 2 913 ; +0,28 | **2 913 ; +0,275** (IC −0,74 à +1,17 ; 6/10) |
| **M3, tous les indices** | 2 981 ; +1,61 | **2 981 ; +1,612** |
| IC à 95 % du gain de M3 (10 000 tirages, graine 20261026) | 0,99 à 2,34 | **0,988 à 2,343** |
| fenêtres où M3 bat M0 | 9 / 10 | **9 / 10** (écarts 6, 9, 8, 8, 0, 9, 13, 21, 3, 5) |

Au seuil déclaré : gain ≥ 5 points **non** (1,61), IC excluant 0 oui, 8 fenêtres sur 10 oui. **La
mémoire du conflit n'est pas utile** au sens déclaré ; b(M3) = 58,6 % est très loin de 80 % : la garde
reste non construite. La prédiction écrite avant (+1 à +6, pas 80 %) tient.

Robustesse (calculée ici, pas dans la piste) : avec k = 1 227 (arrondi par excès), M3 gagne encore
+1,612 point (2 982 contre 2 900) ; sans pénalité (λ = 0), M3 attrape 2 980 (+1,59, IC 0,94 à 2,34, 9/10) :
la convention de la « pénalité L2 de 1 » ne change rien. Seule une pénalité absurde (λ = 10⁴, qui écrase
les coefficients) fait tomber le gain à −1,49 : l'instrument réagit donc bien au modèle qu'on lui donne.

## 8. Le seuil a-t-il été commité avant la lecture ?

Oui, au sens où git et les dates de fichiers peuvent le montrer.

| Moment | Fait |
|---|---|
| 23:41:25 | `seuil-declare-indices.md` écrit (date du fichier) |
| 23:41:29 | commit `50bf472`, ce seul fichier ; il n'a **pas changé depuis** (diff vide contre le commit) |
| 23:43:37 à 23:44:57 | `second_chemin_indices.py`, `indices_complements.py`, `indices.py` écrits (dates des fichiers) |
| 23:44:41 à 23:45:12 | tous les journaux de `mesures/pistes/tropicale/indices/` |
| 23:45:17 | commit `9e31d9f`, la mesure |

Le seuil de 5 points, les témoins W1 à W4, le second chemin et la prédiction sont dans le fichier
commité avant tout journal. Deux limites : git ne prouve pas qu'aucune lecture exploratoire n'a eu lieu
avant 23:41 ; et `indices.py` a été modifié une dernière fois à 23:44:57, **après** l'écriture de
`complements.json` (23:44:41) qui l'importe : il a donc tourné au moins deux fois, et la version
intermédiaire n'est nulle part. Ce qui neutralise ces deux limites : j'ai relu le code final contre la
déclaration (indices, modèles, λ, k = ⌊0,1 n⌋, départage par indice, rééchantillonnage, graine), il
l'applique sans écart, et mon script indépendant, écrit depuis la déclaration seule, redonne les mêmes
nombres à l'unité. Le chiffre ne dépend donc d'aucun choix fait après coup.

## 9. Mon chemin, et ce qui le distingue

Outil : `outils/pistes/tropicale/juge/juge_indices.py` ; journaux `mesures/pistes/tropicale/juge/juge-indices.json`
et `.log`. Rien n'est importé de la piste ni de `bascules.py`.
- Lecture par un type structuré numpy (4 × u8, f32) après vérification des empreintes SHA-256 de
  `seuil-declare.md` § 1 (concordantes) ; étiquette = ensembles triés différents.
- Indices sur des tableaux (couche, fenêtre, position), **vérifiés contre une boucle explicite** sur
  4 000 cellules tirées au hasard : écart maximal 0,0 pour f2, f3, f4. τ₁₀ recalculé : 0,0124099,
  cohérent avec la constante déclarée 0,01241.
- Logistique par Newton exact ; classement par `lexsort` (score décroissant, puis indice de cellule).
- Limite d'indépendance, dite : la déclaration fixe presque tout (indices, modèle, k, départage,
  graine) ; deux programmes fidèles à elle se ressemblent forcément. L'identité de l'IC au millième vient
  de ce que le même générateur, la même graine et le même tirage de 10 × 10 000 entiers produisent la
  même suite, que l'on tire ligne par ligne (piste) ou d'un bloc (juge).

## 10. Les témoins tombent-ils vraiment ?

| Témoin | Piste | Juge | Lecture du juge |
|---|---|---|---|
| Identité M1 = M0 | égalité | **égalité dans les 10 plis** | tient |
| W2, f2 f3 f4 permutés dans chaque couche | +0,33 | **+0,35** (IC −0,60 à +1,25 ; 5/10 ; autre graine) | le gain tombe à 0 : l'instrument ne fabrique pas de gain |
| W3, oracle « bascule en (ℓ−1, p) » | +10,99 | **+10,99** (3 458, IC 9,0 à 12,8 ; 10/10) | il voit un indice quand il existe ; l'attendu déclaré (> 15) était faux, la piste l'a dit |
| Part couverte par cet oracle | 3,8 % des cellules, 24,5 % des bascules | **0,0381 et 0,2447** | reproduit |
| **W4, M3 sur étiquettes mélangées** | 11,6 % (« tient ») | **22,4 %** à une autre graine | **fragile, voir ci-dessous** |

**W4 ne tient pas comme la piste le dit.** Sur vingt graines (`juge_w4.py`, `juge-w4.json`), M3 entraîné
sur étiquettes mélangées attrape **15,9 % en moyenne (écart-type 4,8 ; de 5,3 à 24,5 %)**, et **3
graines sur 20 seulement** tombent dans l'attendu déclaré de 10 ± 2. Le 11,6 % de la piste est un
tirage favorable. La raison est la même que pour la cassure de W1, que la piste a bien vue pour un
modèle à une entrée et pas pour six : une logistique ajustée sur du bruit rend une direction presque au
hasard dans l'espace des indices, et une direction au hasard sur des indices qui portent l'information
n'attrape pas 10 % en moyenne. Le témoin **tombe** (58,6 % → 16 % ± 5 : l'instrument casse quand on lui
retire l'étiquette), mais pas à l'attendu déclaré. Les attendus déclarés faux sont donc **trois sur cinq,
pas deux** (cassure de W1, W3, W4). Aucun ne touche le verdict, qui repose sur le gain, son IC, les
fenêtres, l'identité, W2 et le second chemin, tous reproduits.

## 11. Le second chemin de la piste, et l'autre classe de modèle refaite

- Le second chemin (a) de la piste **recompte** les scores écrits par `indices.py` : il éprouve le
  comptage, pas l'ajustement. Son indépendance est donc faible pour le chiffre principal. C'est mon
  § 7 qui éprouve l'ajustement, et il redonne 2 981.
- L'autre classe de modèle (b), refaite à neuf (`juge_classes.py`, bornes par `numpy.quantile`) :
  **59,07 %**, gain +2,08, 10/10 (piste : 59,05 %, une cellule d'écart, venant des bornes de quantiles).
  Ce modèle rend des scores en paliers : la frontière des 1 226 cellules coupe un palier de 116 à 160
  cellules, et la piste départage par couche croissante. Ce choix pèse peu : couche décroissante
  58,93 % (+1,95), **espérance exacte sous départage au hasard 58,97 % (+1,98)**, toujours 10/10. Du même
  côté du seuil et à moins de 0,5 point de la logistique : la barre déclarée (3 points) est tenue.

## 12. Ce qui serait faux ou trop beau

Rien de trop beau dans le chiffre : il est petit, négatif au seuil, et reproduit. Ce qui est trop fort,
c'est une partie de la lecture qui l'entoure.
- **« Plafond d'une garde qui juge cellule par cellule »** (§ 12 du livrable et valeur de retour de la
  piste : « plafond d'environ 11 points même avec un oracle »). C'est faux tel qu'écrit. W3 mesure la
  valeur d'**un** indice fuité précis (une bascule en ℓ − 1, présente pour 24,5 % des bascules), pas un
  plafond : l'oracle cellule par cellule du premier verdict (T3 ii, marge 0 aux bascules) attrape 100 %
  pour 4,2 % des cellules. Ce que W3 dit, c'est que la **cascade verticale** stricte n'explique qu'un
  quart des bascules. La phrase est à barrer et à remplacer par cela.
- **« La trace dans le temps n'apporte rien »** : à lire « aucun gain détectable » ; les IC de f3 et de
  f4 seuls montent jusqu'à +1,25 et +1,43 point. Avec ces formes linéaires, sur ces journaux, une
  contribution d'au plus ~1,4 point n'est pas exclue. Le verdict n'en change pas (même +1,4 est loin
  de 5).
- **Le témoin W4** : voir § 10 ; le tableau du livrable doit dire « tombe, mais à 16 % ± 5 selon la
  graine, l'attendu de 10 ± 2 était faux ».
- **La cohabitation** : `REPRISE.md` écrit « verrou de la carte absent pendant toutes les passes ». Le
  verrou de la séance ABBA disque `jbis` a été posé à 23:45:09 ; `second-chemin-indices.json` a été écrit
  à 23:45:12. Le second chemin, lancé avant, a donc tourné environ trois secondes après la pose du verrou
  (la séance commence par une attente du calme ; effet probablement nul, mais la phrase est inexacte).
- **L'analogie du vivant** : les deux notices citées (Botvinick, Braver, Barch, Carter, Cohen, *Psychol.
  Rev.* 108 (3), 2001, 624-652 ; Cavanagh et al., *Nat. Neurosci.* 14 (11), 2011, 1462-1467,
  doi 10.1038/nn.2925) concordent avec ce que je connais de ces articles ; je ne les ai pas revérifiées
  chez l'éditeur. Cavanagh 2011 porte sur la stimulation du noyau sous-thalamique qui défait l'effet du
  thêta médiofrontal sur le seuil : l'usage qu'en fait la piste (le conflit relève le seuil) est juste
  mais partiel. Le résultat le plus solide de cette mesure est d'ailleurs indépendant de l'analogie :
  l'information utile est dans la profondeur (f2), pas dans la position.
- **Ce que ni la piste ni le juge n'ont fait** : un autre texte (l'IC dit la variation entre dix fenêtres
  d'un même texte) ; une forme non linéaire riche (arbres) ; un balayage de la fenêtre de f4 et de son
  seuil (choix a priori, ce qui est bien pour un test déclaré). Les ablations, coefficients et Spearman
  de `complements.json` ne sont pas refaits ici : ils sont exploratoires et ne décident rien.

## 13. Ma propre cohabitation, dite

Toutes mes passes : priorité « sous la normale », un fil, aucune carte, verrou jamais pris, attente
automatique tant que le verrou annonce abba, j1 ou vitesse (de 23:49 à 00:44, mon script a attendu la
fin de la séance `jbis`). `juge_indices.py` a tourné de 00:45:11 à 00:45:28, avant la pose du verrou de
la séance p7 (00:45:32) ; `juge_classes.py` a attendu la fin de p7 et fini à 01:07:52. **Un écart** :
`juge_w4.py` a passé sa vérification du verrou juste avant 01:08:45, heure où la séance `j10` l'a posé,
puis a calculé jusqu'à 01:10:50 (un cœur, deux minutes) ; une lecture de contrôle de deux secondes a
suivi vers 01:11. Le journal de `j10` montre la pose du verrou à 01:08:45, une attente du calme à
01:08:53, et **aucune mesure enregistrée** jusqu'à 01:11:41. Je n'ai plus rien lancé ensuite.

## 14. Fichiers du second jugement

- `outils/pistes/tropicale/juge/juge_indices.py` : M0 à M3, k = 1 226 et 1 227, λ = 0 et 10⁴, IC,
  témoins identité, W2, oracle, W4 (une graine) ; `mesures/pistes/tropicale/juge/juge-indices.json`, `.log` ;
- `outils/pistes/tropicale/juge/juge_classes.py` : l'autre classe de modèle et ses trois départages ;
  `juge-classes.json`, `.log` ;
- `outils/pistes/tropicale/juge/juge_w4.py` : W4 sur vingt graines ; `juge-w4.json`, `.log`.

Pour RECETTES.md : (1) un témoin « étiquettes mélangées » ne vaut pas 10 % pour un modèle ajusté : la
direction au hasard d'un modèle entraîné sur du bruit garde l'information des indices ; on le déclare
par sa distribution sur plusieurs graines, ou on casse le test (marges de test permutées) plutôt que
l'entraînement. (2) Un second chemin qui recompte les scores d'un programme éprouve le comptage, pas le
modèle : il faut refaire l'ajustement. (3) Un modèle à paliers se juge avec l'espérance exacte sous
départage au hasard, qui ne demande aucun tirage.
