# P4, préchargement et rétention à confiance calibrée : jugement indépendant

Date : 2026-10-27. Rôle : juge de P4. Seuil du juge : `mesures/mimetisme/P4/juge/00-seuil-du-juge.md`, commité en 82c49a6
avant tout calcul du juge. Outils : `outils/mimetisme/P4/juge/` (`juge_p4.py`, `juge_generation.py`), écrits d'après le texte
du protocole de P4 et non d'après son code. Mesures : `mesures/mimetisme/P4/juge/` (`juge-120b.json` et `.log`,
`juge-generation.json` et `.log`, `empreintes-traces.txt` avec les SHA-256 des sept traces). Traces extraites hors dépôt de
`mesures/localite-gpt-oss/traces-120b/traces-120b.tar.xz`. Un fil, priorité sous la normale, aucune carte, aucun fichier modèle.

## 1. Verdict : le verdict « OUVERT, plutôt du côté de tombe » de P4 est reproduit

Mon chemin diffère du sien sur chaque étage : lecteur de trace propre ; prédicteur en boucle jeton par jeton, avec
départage stable des ex aequo (P4 calcule une matrice T x T et prend `argpartition`) ; LRU propre ; borne de Clopper-Pearson
calculée par bissection sur la loi binomiale (P4 utilise le quantile bêta) ; simulateur réécrit d'après le § 1 et l'amendement 2.

120b, 326 emplacements, d = 2, bras P, moitié de test :

| Session | theta* P4 / juge | précision P4 / juge | couverture P4 / juge | octets P4 / juge | gain [sim.] P4 / juge |
|---|---|---|---|---|---|
| code | 0,86 / 0,86 | 0,919 / 0,914 | 10,9 % / 10,9 % | +0,84 % / +0,91 % | +3,58 % / +3,46 % |
| dialogue | 0,80 / 0,82 | 0,905 / 0,918 | 16,9 % / 15,1 % | +1,47 % / +1,14 % | +4,96 % / +4,39 % |
| prose-en | 0,90 / 0,90 | 0,947 / 0,947 | 7,9 % / 7,9 % | +0,41 % / +0,42 % | +2,60 % / +2,56 % |
| prose-fr | 0,86 / 0,86 | 0,922 / 0,920 | 9,5 % / 9,4 % | +0,72 % / +0,74 % | +2,89 % / +2,82 % |

Précision agrégée du juge : **0,922** (P4 : 0,918). Gain moyen de lecture du juge : **+3,31 %** (P4 : +3,51 %), 0 genre sur 4 à +5 %.
Tous les critères de reproduction déclarés sont tenus : theta* au même pas de grille ou au pas voisin (dialogue) ; précision à
moins de 0,013 ; couverture et octets à moins de 22 % relatifs (le plus grand écart, dialogue, vient du theta* voisin) ; gain à
moins de 0,6 point. La position face au seuil de P4 ne bouge pas : précision tenue, octets tenus, gain sous +5 % partout, moyenne
entre +2 % et +5 %, donc ni « tient » ni « tombe ».

Le chiffre robuste est la précision : la calibration conforme fendue donne bien environ 0,92 de précision des lectures d'avance
pour environ +1 % d'octets, par deux chemins indépendants. Le goulot est la couverture (8 à 15 % des défauts), reproduit aussi.

## 2. Contrôles

- **Ordre des commits** (git log) : seuils 47339c2 (00 h 50 min 29 s), amendement 4732d35 (00 h 52 min 35 s), premiers
  témoins sur traces 07caeb8 (00 h 58 min 24 s), mesures de session 198841c (01 h 20 min 30 s ; les journaux de mesure commités en
  a17b37c sont vides). Aucun chiffre tiré d'une trace n'est commité avant le seuil. La correction v2 du simulateur a été déclarée
  après l'échec de T3 et avant les mesures de session, et P4 le dit.
- **Témoins du juge** (pouvaient tomber) :
  - J1, étiquettes mélangées : aucun seuil calibrable sur les 4 sessions ; précision au theta* réel 0,15 à 0,21 (sous 0,30). Tient.
  - J2, prédicteur parfait à d = 1 dans mon simulateur : x1,159, dans [x1,10 ; x1,30]. Tient. Mon simulateur est un peu plus
    pessimiste que celui de P4 (x1,179) ; les deux restent sous le x1,21 calculé en O.
  - J3, génération prose-en : succès du cache 0,989 recalculé. Tient, mais voir § 3.1.
- **Témoin de P4 qui tombe** : T3 (FIFO synthétique, -11 % attendu, +4,9 % obtenu) manque, et P4 le dit au lieu de le rattraper.
  Mon simulateur met en œuvre le même modèle déclaré : notre accord est une cohérence avec ce modèle, **pas une validation contre
  le moteur**. Je ne peux pas trancher T3. Le verdict reste plafonné à « ouvert » par la règle 3 de l'amendement.

## 3. Ce qui est faux ou trop beau

1. **La jambe « génération » est mesurée sur deux traces dégénérées, et P4 ne le dit pas.** Le texte de prose-en génération
   s'achève par une réponse courte, puis boucle sur `<|return|>` et des sauts de ligne ; celui de wiki boucle sur « Here is a
   summary ». Le « 98,9 % de succès, rien à précharger » de prose-en est celui d'une boucle de blancs. Pour wiki, la calibration ne
   trouve aucun seuil parce que la moitié de calibration (avant la boucle) a une précision de 0,73 à theta 0,9, alors que la moitié
   de test (dans la boucle) atteint **0,979 à theta 0,9 (1 129 chargements) et 0,964 à 0,8** (mon chemin ; P4 avait les mêmes
   nombres dans sa courbe, 0,980 et 0,963, sans les commenter). « Génération : 0 [mes.] » est exact au sens du protocole, mais ce
   n'est ni un échec ni un succès du mécanisme : c'est une donnée non représentative, et un cas concret où l'échangeabilité casse
   (ici dans le sens prudent). La condition « génération » du seuil n'apprend rien. Le verdict ne change pas, la lecture suffit à
   le fixer.
2. **Le gain absolu dépend de l'ancrage à 460 ms.** Le code fait 92 défauts par jeton dans le LRU simulé : 92 x 4,1 ms plus les
   queues et les 80 ms de calcul dépassent déjà 460 ms, d'où un surcoût o négatif (-0,137 ms par couche chez P4, -0,192 chez moi), ce
   qui n'a pas de sens physique. Si l'on ancre chaque session à 460 ms, o vaut -1,71 ms par couche pour le code et son gain tombe à
   **+0,42 %** ; avec o = 0, il monte à +3,80 %. Selon l'ancrage, la moyenne de lecture va de +3,08 % à +3,61 %, et dialogue franchit
   +5 % dans un seul cas (+5,18 % ancré par session) : jamais plus d'un genre sur 4. Les gains sont des ordres de grandeur, comme
   P4 l'écrit ; le partage de la fenêtre a / c ne change rien (fenêtres contiguës).
3. **Phrase inexacte dans `p4_mesure.py`** : les paramètres du simulateur y sont dits « étalonnés sur le 120b, 7 %, pas sur les
   sessions mesurées ici ». En fait o est ajusté sur les quatre mêmes sessions de lecture (`calibrer_o` sur LECTURE). C'est sans
   effet sur le gain (o n'utilise pas le prédicteur), mais la phrase est fausse.
4. Borne analytique du juge (économie au plus égale à U x 4,1 ms, plafonnée par les fenêtres de calcul) : +5,8 à +11,8 %. Elle
   encadre la simulation par le haut et retrouve la « formule fermée » de P4 (+5,8 à +13,4 %), qui ignore le débordement des
   lectures de fond. Rien de trop beau dans les chiffres principaux : ils sont plutôt du côté prudent du modèle.

## 4. Ce qui reste à trancher

- La seule épreuve qui départage est celle que P4 propose : une passe ABBA du moteur avec la porte theta*, quand le verrou de la
  carte est levé. Elle validerait ou non le simulateur (T3).
- La jambe génération demande des traces de génération non dégénérées (texte qui ne boucle pas) avant de pouvoir compter.
- Pas d'envoi à la session principale : le résultat reproduit n'est pas une piste probable au seuil de +5 %.
