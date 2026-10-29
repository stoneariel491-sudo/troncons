# P3, routage conditionné par le cache : jugement indépendant (2026-10-27)

Rôle : juge de la piste P3 (clé P3). Critères commités **avant** d'exécuter mon chemin : `mesures/mimetisme/P3/juge/00-criteres-du-juge.md`
(commit c23e3db). Outil : `outils/mimetisme/P3/juge/juge_p3.py` (rien d'importé de l'outil de l'expérimentateur). Journaux :
`mesures/mimetisme/P3/juge/01-accord.json`, `02-mesure.json`, `02-mesure.log`. Étiquettes : [mes.] mesuré par moi, [calc.] calculé
sur mesures, [hyp.] hypothèse.

## 1. Verdict

**Étage A REPRODUIT à l'unité ; au seuil déclaré, OUVERT, étage B justifié ; la piste NE TIENT PAS encore.**

Les nombres de l'expérimentateur sont exacts : je les retrouve tous, défaut pour défaut, par un autre lecteur GGUF, un autre produit
matriciel et un autre cache. La règle déclarée, appliquée par moi à la seule grille officielle, sans l'affinage post hoc, donne le même
verdict. Mais deux points de lecture sont faux ou trop optimistes (§ 4) et changent ce qu'il faut attendre de la suite :

1. **L'étage B tel qu'il est écrit ne peut pas dire « tient » pour un routeur biaisé réel.** Il impose les ensembles de la boucle ouverte à
   **toutes** les cellules, donc il empêche les bascules secondaires que la bascule voulue déclencherait aux couches suivantes. Le cahier dit
   cet écart « au plus de second ordre ». Les mesures du dépôt disent le contraire : 59 % des bascules du lot R sont des secondaires.
2. **Le sens de l'erreur de la « KL a priori » n'est pas inconnu.** Pour un routeur en ligne, elle est probablement trop basse : normalisée
   par les racines des cascades et non par toutes les bascules, elle vaut 0,090 au franchissement de −10 % à N = 146, **au-dessus du seuil de
   mort de 0,07**, et 0,055 à N = 238.

## 2. Le chiffre principal, refait par mon chemin [mes.]

Chemin : lecteur GGUF écrit pour ce jugement (v3, en-tête, paires clé-valeur, descripteurs, alignement) ; routeur F32 de chaque couche ;
logits en f64 par `einsum` sur h en memmap ; LRU à horodatage (768 dates, victime = plus petite date parmi les résidents non épinglés) ;
sélection V1 par `argpartition`. Durée : 5 s pour les logits, 410 s pour 26 passes, 2 fils, priorité sous la normale, verrou absent.

| critère (déclaré) | expérimentateur | juge | tenu |
|---|---|---|---|
| accord avec la capture | 122 640 / 122 640 | **122 640 / 122 640**, écart de poids 4,07e-8 | oui |
| cassure : sans le biais du routeur | 0,6544 | **0,6544** | oui (tombe) |
| défauts β = 0, N = 146 / 238 | 216 397 / 108 472 | **216 397 / 108 472** | oui, à l'unité |
| V1 β = 0,03 | −5,1 % ; −7,5 % | **−5,07 % ; −7,49 %** (205 416 ; 100 346) | oui |
| V1 β = 0,1, défauts | −16,1 % ; −22,6 % | **−16,10 % ; −22,56 %** (181 561 ; 83 999) | oui, mêmes entiers |
| V1 β = 0,1, cellules changées | 19,3 % ; 16,6 % | **19,30 % ; 16,58 %** | oui |
| franchissement de −10 %, β | 0,0604 ; 0,0410 | **0,0604 ; 0,0410** (interpolé entre 0,06 et 0,07, puis 0,04 et 0,05) | oui |
| part changée à ce franchissement | 11,98 % ; 7,31 % | **11,99 % ; 7,31 %** | oui |
| V2 β = 0,1 | −10,4 % ; −15,3 % | **−10,39 % ; −15,31 %** | oui |
| masque au hasard, même densité, β = 0,1 | +0,7 % ; +1,9 % | **+0,76 % ; +1,48 %** | oui (aucun gain) |
| β = −0,1 | +17,4 % ; +28,2 % | **+17,38 % ; +28,24 %** | oui |

Un écart, sans effet sur rien : le masque au hasard à N = 238 donne +1,48 % chez moi contre +1,9 % chez lui. Le tirage aléatoire diffère
(autre générateur, autre graine). Les deux sont sous mon critère de 2 %.

**Témoins de mon propre chemin, qui pouvaient tomber** : rejouer β = 0 avec les accès du groupe dans l'ordre croissant de logit change le
compte (216 093 et 108 433), et un LRU sans épinglage aussi (217 760 et 108 743). Mon simulateur voit donc l'ordre d'accès et la règle de
groupe, et il retombe à l'unité sur la définition déclarée. Le masque au hasard, qui change 12 % des cellules sans rien gagner, montre que
le gain vient de la résidence et non du simple fait de changer d'ensemble.

**Règle déclarée, grille officielle seule** [calc.] : à β = 0,1, −16,1 % et −22,6 % (au moins 10 % aux deux budgets) ; KL_prior =
0,309 × part = 0,060 et 0,051 (au plus 0,07). Donc **OUVERT, étage B justifié**, sans recourir à l'affinage, qui était post hoc (déclaré
à 01:20, après la courbe officielle de 01:19 ; il ne fait qu'affiner le franchissement).

## 3. Antériorité du seuil (git log)

- `1606f9f` 00:51:47 : `00-seuils-declares.md`, seul fichier du commit.
- `6f84b4a` 00:54:00 : outil et témoins synthétiques (aucune donnée lue).
- `396407c` 00:54:23 : premier contact avec les données réelles (64 positions).
- `5dfee3c` 01:19:03 : étage A ; le journal montre une attente du verrou à partir de 00:54:24, puis la lecture après 01:04.

L'ordre des commits est le bon. Git prouve l'ordre des commits, pas l'heure de la lecture. Mais tout ce que j'ai pu contrôler concorde :
l'essai est commité après le seuil, et le journal horodaté de l'étage A commence après lui. Les seuils de l'étage A n'ont pas bougé entre
1606f9f et le résultat (même texte, relu).

## 4. Ce qui est faux ou trop beau

### 4.1 L'étage B imposé supprime les cascades (grave pour la lecture de « tient »)

Le cahier impose à la référence f64 les ensembles calculés sur la trajectoire exacte. Pour les 88 % de cellules non changées, il impose
donc l'ensemble **exact**. Dans un routeur biaisé réel, la bascule voulue à (t, l) déplace h, et les cellules suivantes à faible marge
basculent à leur tour. Le dépôt l'a mesuré : P(bascule en ℓ + 1 | bascule en ℓ) = 26,6 % contre 3,4 % (`pistes/tropicale`, confirmé par
son juge à 26,65 % et 3,37 %), et sur 5 087 bascules, 3 006 sont des secondaires (59 %) contre 2 081 racines. L'imposition les interdit
toutes. Le cahier écrit que l'écart « est au plus de second ordre » (§ Limites) : cette phrase est contredite par ces mesures.

Conséquence : l'étage B mesure le **coût direct** des bascules voulues, sans leurs suites, ce qui est une borne basse vraisemblable de la KL
d'un routeur en ligne [hyp. : les suites coûtent une KL positive]. Lecture asymétrique : **une KL d'étage B au-dessus de 0,07 tue P3**
(c'est robuste) ; **une KL d'étage B sous 0,038 ne suffit pas pour « tient »**. Il faut alors un routeur biaisé en ligne dans la référence :
biais appliqué aux logits recalculés à chaque couche sur la trajectoire réelle, résidents tirés du cache simulé en même temps. C'est
l'épreuve que le cahier renvoie à « après », et c'est elle qui décide.

### 4.2 La constante de la KL a priori : le sens de l'erreur est probablement connu

0,309 = 0,0128 / (5 087 / 122 640) divise la KL retirée par **toutes** les bascules, cascades comprises. Une bascule voulue, en boucle fermée,
est une racine qui traîne ses suites. Par racine, la constante vaut 0,0128 / (2 081 / 122 640) = **0,755** [calc. ; hyp. : une bascule voulue
cascade comme une racine subie, KL additive]. À chaque franchissement de −10 % [calc. sur mes.] :

| | N = 146 | N = 238 |
|---|---|---|
| part changée | 11,99 % | 7,31 % |
| KL a priori, constante 0,309 (déclarée ; prédit plutôt l'étage B) | 0,037 | 0,023 |
| KL a priori, constante par racine 0,755 (routeur en ligne) | **0,090** (> 0,07 : mort a priori) | **0,055** (entre 0,038 et 0,07) |
| κ_max de `pour-le-memoire.md` § 5 (succès) / κ de mort | 0,317 / 0,584 | 0,520 / 0,958 |

La constante par racine, 0,755, dépasse le κ de mort à N = 146 et tombe dans la zone « non concluant » à N = 238. Ce n'est pas une mesure,
et la normalisation par racine a ses propres faux possibles : une racine de position peut être la suite d'une bascule d'une position
antérieure par le cache KV, ce qui tirerait la constante vers le bas ; et il y a 2,9 bascules voulues par position, ce qui rend l'additivité
douteuse. Elle suffit pourtant à corriger une phrase : le résultat écrit « je ne sais pas dans quel sens l'erreur va ». Pour le routeur en
ligne, le sens le plus probable est **vers le haut**.

**Sonde S2** [mes.], qui ne contredit pas la transposition sur un autre axe : à β = 0,06 et N = 146, 14 718 échanges (1,008 par cellule
changée). Le poids softmax de l'expert retiré, sur z non biaisé et parmi les quatre d'origine, a pour médiane **0,175** (moyenne des
carrés 0,0313). Pour le 4e expert des cellules à marge < 0,0095 (proxy des bascules subies), la médiane est **0,172** (0,0302). Les bascules
voulues retirent donc un expert de même poids que les bascules subies, alors que leur écart de logit est six fois plus grand (médiane
0,0296 contre 0,0046). Sur le terme direct, 0,309 n'est pas absurde. C'est le terme des cascades qui manque.

### 4.3 Ce qui est juste et que je confirme

- Le levier a de l'amplitude, et elle vient du cache : le masque au hasard ne gagne rien, le signe inversé perd.
- « Un seul expert change par cellule changée » (1,008) : confirmé.
- Les conversions en vitesse (×1,11 / ×1,19 / ×1,29 si le disque borne tout) sont de l'arithmétique juste, à condition que la vitesse
  suive 1/défauts. Ce n'est pas mesuré.
- Les faux possibles déjà dits par l'expérimentateur (boucle ouverte, texte relu et non généré, budgets du tri, premier choix de sortie non
  mesuré, fenêtres non indépendantes) restent ouverts. Je n'ai rien vu qui les aggrave, sauf la boucle ouverte, aggravée par le § 4.1.

## 5. Ce que je demande pour la suite

1. **Étage B, lu en borne basse** : β = 0,06 et 0,07 à N = 146 d'abord, comme prévu. Si la KL dépasse 0,07, P3 tombe sans appel. Sinon,
   ne pas écrire « tient ».
2. **Étage C, le seul qui peut dire « tient »** : un routeur biaisé **en ligne** dans la référence f64. Mêmes seuils (0,038 et 0,07), même
   arrêt O'Brien-Fleming. Témoin : β = 0 égal au bit à la référence. Cassure : la KL à β = 0,06 en ligne doit être au moins celle de
   l'étage B, faute de quoi il y a un bogue. Grandeur de plus : le nombre de cellules changées en boucle fermée, à comparer à la part de la
   boucle ouverte. Le rapport des deux mesure directement le facteur de cascade que le § 4.2 suppose.
3. Avant d'y engager 2,5 h : relever la RAM de pointe de la référence, et choisir N = 238 comme budget principal si le budget réel du moteur
   le permet. C'est là que la marge existe (0,055 a priori, même avec les cascades).

## 6. Fichiers

- Critères : `mesures/mimetisme/P3/juge/00-criteres-du-juge.md` (c23e3db, avant exécution).
- Outil : `outils/mimetisme/P3/juge/juge_p3.py` (`logits`, `mesure`).
- Journaux : `mesures/mimetisme/P3/juge/01-accord.json`, `02-mesure.json`, `02-mesure.log`.
- Logits recalculés (31 Mo, hors dépôt) : `~/dev/essais/troncons/mimetisme/P3/juge/Z.npy`.
- Sources du dépôt citées : `genome/05-synthese.md` § 2.2 ; `genome/pistes/tropicale/garde-tropicale.md` § 5.4 et § 7 ; `genome/pistes/tropicale/JUGEMENT.md` ;
  `genome/mimetisme/P3/cahier-etage-B.md` (§ Limites) ; `genome/mimetisme/P3/pour-le-memoire.md` § 5.
