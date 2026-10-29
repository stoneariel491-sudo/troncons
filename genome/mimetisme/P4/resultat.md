# P4 : préchargement et rétention à confiance calibrée, qui cède à la demande

Date : 2026-10-27. Expérimentateur P4. Seuils et protocole : `mesures/mimetisme/P4/00-seuils-declares.md` (commits 47339c2,
4732d35, 07caeb8, tous avant la première mesure de session). Outils : `outils/mimetisme/P4/` (`p4.py`, `p4_temoins.py`,
`p4_mesure.py`, `p4_synthese.py`, `p4_figures.py`). Mesures et journaux : `mesures/mimetisme/P4/`. Aucune carte graphique, aucun
fichier modèle, une à deux processus d'un fil, RAM du processus 105 Mo.

Étiquettes : **[mes.]** mesuré ici (trace réelle, calibration, comptes) ; **[sim.]** sorti du simulateur à événements discrets,
dont le témoin hors échantillon a MANQUÉ (voir § 2) ; **[calc.]** calculé ; **[lu]** source lue le 2026-10-27 ; **[mém.]** de
mémoire.

## 1. Verdict au seuil déclaré

**OUVERT, et plutôt du côté de « tombe » pour l'objectif +5 % au 120b.** Ni « tient » ni « tombe » au sens écrit d'avance :

- Ce qui TIENT [mes.] : la garantie de précision. La calibration conforme fendue donne, sur la moitié de test, une précision des chargements
  de **0,905 à 0,947** (agrégée **0,918**) sur les 4 genres de lecture du 120b à 7 %, pour **+0,4 à +1,5 % d'octets** lus de plus ; le
  moteur tué de O § 9.2 avait p = 0,692 pour +34 %. Seuil de précision déclaré (>= 0,85, chaque session >= 0,80) : tenu.
- Ce qui NE TIENT PAS : le gain. Bras P, 120b, 7 %, d = 2 [sim.] : code +3,58 %, dialogue +4,96 %, prose-en +2,60 %, prose-fr +2,89 %.
  Moyenne **+3,51 %**. **0 genre sur 4** à >= +5 % (dialogue manque de 0,04 point). Plus de +2 % de moyenne : pas « tombe ».
- **Génération : 0** [mes.]. prose-en (256 jetons) a un succès de cache de 98,9 % au 120b (1,6 défaut par jeton : rien à précharger) ;
  wiki (256 jetons) : aucun seuil ne passe la borne de Clopper-Pearson sur 128 jetons de calibration. La condition « génération >= +5 % » est manquée.
- **Bras R (épingler, zéro octet de plus) : mort** [sim.] : +0,09 % de moyenne en lecture (+0,05 / +0,14 / +0,09 / +0,08), au plus +0,67 % à d = 8.
- **Le simulateur n'est pas validé** (§ 2). D'après la règle 3 de l'amendement, le verdict ne pouvait de toute façon pas dépasser « ouvert ».

## 2. Témoins

| Témoin | Attendu | Obtenu | Statut |
|---|---|---|---|
| T0 LRU global (dict) contre liste simple, 2 000 accès | égal | 1 195 / 1 195 (N = 326), 2 000 / 2 000 (N = 60) | tient |
| T2 prédicteur parfait, d = 1, priorité | x1,21 à 2 % | v1 : x1,2247 (+1,2 %) ; **v2 : x1,1786 (-2,6 %)** | v1 tient, v2 manque de 0,6 point |
| T3 FIFO, prédicteur synthétique p = 0,692, couverture 0,76 (octets +33,8 % obtenus) | -11 % +/- 4 points | v1 **+5,2 %** ; v2 **+4,9 %** | **MANQUE (hors échantillon)** |
| Cassure : étiquettes mélangées | précision au hasard ; calibration sans seuil | 120b : 0,92 -> 0,14 à 0,22 à theta* ; aucun seuil trouvé en calibration, 7 sessions sur 7 | tient |
| Voisins au hasard | précision très inférieure | 120b, theta = 0 : 0,10 à 0,16 contre 0,36 à 0,40 ; aucun seuil calibrable | tient au 120b ; **au 20b 3 sessions sur 10 trouvent un seuil avec des voisins au hasard** (32 experts : la popularité seule donne de la confiance) |

Deux remarques honnêtes. (1) « Au hasard » n'est pas k/E = 0,031 : avec les étiquettes mélangées, les chargements retombent à 0,14 à 0,22, la
popularité des cellules ; c'est le vrai zéro de comparaison, et la calibration ne le franchit pas. (2) T3 est le seul point mesuré de
O ; le simulateur v1, puis v2 corrigé d'après le code du moteur (la copie et le décodage restent à la demande pour un tronçon lu d'avance,
`trc-ordo/src/lib.rs` 1109 à 1190), donnent tous deux un gain positif là où le moteur a perdu 11 %. La bissection de la fenêtre pour
rattraper x1,21 a dérapé (fenêtre 400 ms, surcoût négatif de -9 ms par couche) : abandonnée, journal gardé
(`temoins-120b-v2-bissection-ratee.log`). Conséquence : **tous les gains [sim.] ci-dessus sont des ordres de grandeur dont le signe d'erreur est
inconnu**. Le seul indice : en FIFO le même simulateur donne plus que la priorité (+6,3 % contre +3,6 % en code), ce qui n'a pas de raison
physique et dit que le modèle des fenêtres est trop généreux.

## 3. Chiffres principaux (120b, budget 7 % = 326 emplacements, d = 2, bras P, moitié de test)

| Session | jetons test | défauts / jeton | theta* | précision cal. | précision test | couverture des défauts | octets de plus | gain [sim.] | formule fermée déclarée | formule avec débordement |
|---|---|---|---|---|---|---|---|---|---|---|
| code | 1 271 | 92,0 | 0,86 | 0,911 | 0,919 | 10,9 % | +0,84 % | +3,58 % | +8,66 % | +4,12 % |
| dialogue | 1 431 | 76,0 | 0,80 | 0,904 | 0,905 | 16,9 % | +1,47 % | +4,96 % | +13,36 % | +6,10 % |
| prose-en | 1 189 | 76,4 | 0,90 | 0,918 | 0,947 | 7,9 % | +0,41 % | +2,60 % | +5,79 % | +2,88 % |
| prose-fr | 1 443 | 72,6 | 0,86 | 0,914 | 0,922 | 9,5 % | +0,72 % | +2,89 % | +6,96 % | +3,35 % |

Budget 20 % (922 emplacements) : moyenne de lecture +1,98 %, précision 0,907. Sensibilité à d (7 %, `mesure-120b-sensibilite-d.json`) : le gain P baisse
quand d monte (code +3,90 / +3,58 / +2,53 / +1,59 % pour d = 1 / 2 / 4 / 8) ; la couverture ne remonte pas. Le succès du LRU simulé est de 36 à 50 %
(59 % mesuré par le moteur, qui a de plus une RAM tiède).

Réplique 20b (cache 154 emplacements = 20 %, régime valide : 154 > (L-1)k = 92) : gain de lecture +5,05 / +9,10 / +5,85 / +6,09 %, 4 genres sur 4 à >= +5 %,
octets <= +2,5 %, précision 0,91 à 0,94 ; génération : aucune session calibrable, gain 0. **Le 20b à 7 % (54 emplacements) est écarté** : 54 < 92, le LRU global
s'effondre (succès 0,000, chaque accès est un défaut), les gains +8 à +10 % y sont ceux d'un cache qui ne sert à rien, pas d'un moteur réel.

## 4. Second chemin

La formule fermée déclarée, gain = min(U t, p min(C t, omega)) / T, **échoue** : elle donne 2 à 2,4 fois la simulation, parce qu'elle ignore que chaque
lecture de fond déborde de sa fenêtre de calcul (2,2 ms) et retarde la demande suivante d'environ t - (c + a) = 1,9 ms. Avec ce terme (gain = (U t - C x 1,9) / (T - ...)),
l'écart à la simulation est de 11 à 23 % (4,12 / 6,10 / 2,88 / 3,35 % contre 3,58 / 4,96 / 2,60 / 2,89 %), dans les 25 % déclarés. **Cette seconde formule a été
écrite après avoir vu l'écart : c'est une cohérence interne, pas un test indépendant.** Elle ne valide pas non plus le simulateur contre le moteur.

## 5. Ce qui pourrait être faux

1. Le simulateur (témoin T3 manqué ; T2 manqué de 0,6 point en v2). Le gain absolu est incertain, dans les deux sens.
2. Les traces « lecture » sont rejouées jeton par jeton comme un décodage ; le vrai préremplissage est par flux. Les traces de génération font 256 jetons : 128 pour calibrer ne suffisent pas.
3. Le LRU simulé fait 72 à 92 défauts par jeton, le moteur 59 : la part du disque dans le jeton est surestimée de quelques points.
4. L'échangeabilité de la prédiction conforme n'est pas vraie des jetons (l'historique grandit) : la précision de test (0,905 à 0,947) est >= celle de calibration, le bon sens de l'écart, mais ce n'est pas démontré.
5. Pas de RAM tiède, pas de pollution du cache par les lectures d'avance, copie et décodage supposés en tuyau, 4,1 ms par lecture (le moteur voit 5 ms).
6. Le hors-texte (calibration sur un autre genre) n'est pas mesuré ici ; la chute du rappel à +0,08 / +0,13 dit qu'il ne tient probablement pas.
7. d = 2 et le bras « annulation des seules cibles servies » fixés d'avance ; la « purge totale » donne un peu moins (+3,17 / +4,48 / +2,32 / +2,59 %), même ordre.

## 6. Suite possible

- **Ce que la mesure apprend de neuf** : la conformalité règle bien le problème de précision qui avait tué le préchargement (0,92 pour +1 % d'octets). Le goulot est maintenant la **couverture** : 8 à 17 % des défauts pour 0,9 de précision. Un prédicteur plus riche (état caché du routeur, J1+, qui demande le moteur) ou un historique plus long est le seul levier ; le plafond [calc.] reste x1,21.
- **Seul arbitre valable** : une passe ABBA du moteur avec la porte theta* (peu de lignes : émettre la lecture d'avance seulement si la confiance >= theta*), après la levée du verrou de la carte. Elle tranche aussi la validité du simulateur.
- Le bras R ne vaut pas la peine avec un LRU à 326 emplacements ; il pourrait revivre avec une politique où l'éviction est lente (P1, LFU), à mesurer alors.

Sources lues le 2026-10-27 : Angelopoulos, Bates, *A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification*, arXiv:2107.07511 (v1 15 juillet 2021, v6 7 décembre 2022) [lu, résumé] ; Angelopoulos, Bates, Candès, Jordan, Lei, *Learn then Test: Calibrating Predictive Algorithms to Achieve Risk Control*, arXiv:2110.01052 (3 octobre 2021) [lu, résumé] ; Shalunov, Hazel, Iyengar, Kuehlewind, *Low Extra Delay Background Transport (LEDBAT)*, RFC 6817, décembre 2012 [lu, résumé]. Le tri citait l'ICLR 2024 (maîtrise conforme du risque) et TCP Nice (OSDI 2002) : [mém.], non rouverts. Mon souvenir des auteurs de la méthode de séquence fixe était faux (je les avais confondus) : corrigé d'après la page.
