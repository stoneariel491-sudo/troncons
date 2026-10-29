# P3, étage B à N = 238 (budget 31 %) : résultat (2026-10-27)

Critère et protocole : `mesures/mimetisme/P3/03-critere-marge-declare.md` (commité **avant** toute passe neuve, **après** lecture de N = 146 : dit en toutes lettres dans ce texte-là). Ensembles : `04-ensembles-N238.md`. Outils : `outils/mimetisme/P3/p3_fichiers_N238.py`, `p3_etageB_N238.py`, `p3_etageB_N238_analyse.py`, `p3_etageB_N238_lecteur.py`. Journaux et chiffres : `mesures/mimetisme/P3/etage-B/N238/`. Étiquettes : **[mes.]** mesuré ici, **[calc.]** calculé.

## 1. Verdict

| Lecture | Verdict à N = 238 | Pourquoi |
|---|---|---|
| **Pondérée par la marge** (premier choix ≥ 95 % sur les positions à marge de référence ≥ 0,3 logit) | **TIENT, partiel** | β₁ = 0,041 : −10,02 % de défauts, KL 0,01172 ≤ 0,038, premier choix pondéré **98,75 %** ≥ 95 %. β₂ = 0,050 : −12,11 %, KL 0,01534, pondéré 98,38 % : tient aussi. |
| **Littérale** (95 % sur toutes les positions), lecture sévère | **NON CONCLUANT** | KL et défauts tiennent, mais le premier choix littéral vaut **91,96 %** (β₁) et 91,14 % (β₂), sous 95 %. « Tombe » n'est atteint à aucun β : KL ≪ 0,07, et −5 % de défauts est atteint avec KL ≤ 0,038. |

Pourquoi « partiel » : (i) un seul budget passé ; la condition « aux deux budgets » du tri ne peut pas être satisfaite à la lecture pondérée, N = 146 étant déjà lu et ayant inspiré le critère (ses 97,4 % / 97,2 % sont cohérents, sans valeur de test) ; (ii) boucle ouverte ; (iii) critère posé après lecture ; (iv) lecture de texte, pas génération. Ce « tient » dit : **à N = 238, le levier retire au moins 10 % des défauts sans presque jamais changer le premier choix là où la référence est tranchée**. Il ne dit pas que le routeur biaisé en ligne marche.

## 2. Chiffres [mes.]

2 550 positions notées, 10 fenêtres de 511. Marge de référence ≥ 0,3 : 1 601 positions (62,8 %).

| | β₀ = 0 | β₁ = 0,041 | β₂ = 0,050 |
|---|---|---|---|
| défauts (LRU, N = 238) | 108 472 | **97 604** (−10,019 %) | 95 341 (−12,105 %) |
| cellules à ensemble changé | 0 | 7,289 % | 8,832 % |
| KL moyenne (chemin 2) | 0 (au bit, T0) | **0,01172** | **0,01534** |
| intervalle (rééchantillonnage des fenêtres, 20 000 tirages) | | [0,00929 ; 0,01404] | [0,01179 ; 0,01880] |
| KL médiane / p99 | | 0,00251 / 0,178 | 0,00333 / 0,300 |
| premier choix, **toutes positions** | 100 % | **91,96 %** (205 désaccords) [91,06 ; 92,86] | 91,14 % (226) [89,53 ; 92,47] |
| premier choix, **marge ≥ 0,3** | 100 % | **98,75 %** (20 désaccords sur 1 601) [98,30 ; 99,19] | 98,38 % (26) [97,87 ; 98,91] |
| premier choix, marge ≥ 0,1 (pour information) | | 96,47 % | 95,65 % |
| désaccords sous 0,1 / sous 0,3 de marge | | 62,4 % / 90,2 % | 58,0 % / 88,5 % |
| KL / part de cellules changées | | 0,161 | 0,174 |
| durée de la passe | | 731 s | 706 s |
| mémoire de travail de pointe de `juge reference` | | 2,29 Go | 2,29 Go |

- Pondéré par fenêtre : β₁ de 97,3 % à 100 % (aucune fenêtre sous 95 %) ; β₂ de 97,0 % à 100 %.
- KL par fenêtre : β₁ de 0,0045 à 0,0166 ; β₂ de 0,0058 à 0,0244. Aucune fenêtre près de 0,07.
- Les deux β tiennent chaque condition de la lecture pondérée, et la KL croît avec β (monotone).
- **Prédictions écrites avant les passes** (`04-`) : KL 0,0128 (bande 0,009 à 0,017) et 0,0155 → mesuré 0,0117 et 0,0153, dans les bandes ; littéral « 91 à 93 % » → 91,96 % (β₁) ; pondéré « > 96 % » → 98,75 %. Le rapport KL / part changée est du même ordre qu'à N = 146 (0,16 à 0,17 contre 0,173 à 0,176) ; l'a priori de l'étage A (0,309) restait pessimiste d'un facteur 1,8 à 1,9.
- Comparaison avec N = 146 [calc., chiffres relus de `resultat-etage-B.md`] : pour un retrait de défauts voisin (−11,5 % à N = 146, −10,0 % ici), N = 146 coûtait 0,0239 de KL et 87,6 % de premier choix ; N = 238 coûte 0,0117 et 91,96 %. Un budget plus grand rend le même gain relatif avec presque deux fois moins de cellules changées (7,3 % contre 13,8 %).
- Contexte non revérifié ici (R0, `resultat-etage-B.md` § 1) : llama.cpp s'accorde à la référence sur le premier choix à 90,4 %. Le 91,96 % littéral est de cet ordre.

## 3. Témoins, cassures, seconds chemins

- **Témoin T0 (β = 0)** et **cassure T1 (1 %)** : repris de N = 146 sans relance, leurs fichiers de référence étant identiques (empreintes recontrôlées le jour même, `03-` (d)) : T0 KL nulle au bit, T1 KL 2,08e-3 > 1e-4 (le témoin tombe).
- **Imposition effective** [mes.] : pour chaque passe, le routage que le moteur a enregistré porte les quatre experts imposés dans **122 640 cellules sur 122 640**, et la copie lue par le moteur a l'empreinte voulue. Ce contrôle pouvait échouer et n'a pas échoué.
- **Déterminisme au bit** [mes.] : la passe β₁ a été exécutée deux fois (voir § 4) ; `.kld` identique (SHA-256 5b68e543…737afa) et CSV par position identique octet pour octet.
- **Défauts** : 97 604 et 95 341 trouvés par trois LRU (celui de l'outil, `cache2.py`, celui du juge), égaux à l'unité ; β = 0 : 108 472.
- **Second chemin du chiffre principal** : (1) numpy depuis le CSV par position de `juge kl` (premier choix recalculé de `premier_base == premier_test`, sans la colonne du juge ; marge de référence jointe position par position) ; (2) lecteur `.kld` du juge de l'étage B, KL et premiers choix recalculés depuis les `.kld` : KL 0,011720153 contre 0,011720155 et 0,015342401 contre 0,015342402, **mêmes premiers choix** (91,96 / 98,75 et 91,14 / 98,38) ; marges de la référence relues du `.kld` : écart maximal avec la colonne du CSV 0,0. Le critère est donc vérifié par un chemin qui ne partage pas le code de `juge kl`.
- Témoin de l'outil d'analyse : appliqué aux CSV de N = 146 (β = 0,06), il retrouve 88,43 % et 97,44 %, les valeurs du juge de l'étage B.

## 4. Incidents de séance (dits, rien de masqué)

1. Passe β₁, première exécution (08:08, 715,8 s, code 0) : le pilote a planté **après** la passe sur un chemin de copie du CSV du juge (r1 au lieu de r0). Le relevé de RAM de cette passe est perdu ; l'empreinte du `.kld` et le CSV ont été gardés (`premiere-passe-b0.041.json`, `juge-kl-p3-N238-b0.041.premiere.csv`).
2. Relance : arrêtée à 407 s par le garde-fou secteur (débranchement bref, revenu en moins de 5 min). Le garde-fou exige désormais 3 relevés de suite (15 s) sans secteur.
3. Relance : arrêtée à 428 s par le garde-fou swap (RAM disponible 0,01 Go, swap 4,8 Go ; pointe de la passe 2,23 Go : la pression venait d'autres processus, notamment une compilation LaTeX en cours). Relancée à RAM libre 6 Go ; passes de 731 s et 706 s, RAM disponible minimale 4,9 et 5,1 Go, swap au plus 3,78 et 3,04 Go (dont ~3 Go déjà présents avant le lancement, hérités d'autres processus), C: libre ≥ 79,7 Go.
4. La passe β₂ n'a été exécutée qu'une fois ; son déterminisme au bit n'est pas vérifié par répétition.
5. Verrou de la carte `verrou-carte.txt` écrit au lancement de chaque séance et retiré à chaque fin (absent maintenant).

## 5. Ce qui pourrait être faux

1. **Critère construit après lecture.** Le seuil de marge (0,3) a été choisi sachant qu'à N = 146 il rendait 97,4 % (0,1 rendait 93,7 %). Garde-fou : le test est sur des passes neuves. Le résultat n'est pas sur le fil à 0,3, mais le critère dépend de la marge : sur ces mêmes passes [calc., post hoc, aucun seuil changé], le premier choix passe 95 % dès la marge 0,05 à β₁ (95,05 %) et dès ~0,07 à β₂ (94,96 % à 0,07, 95,65 % à 0,1). Une marge de seuil plus basse ferait donc perdre la porte à β₂ ; je n'ai pas cherché d'autre marge que celle déclarée.
2. **Le témoin ne peut pas faire tomber la porte pondérée.** La cassure T1 (KL 2,08e-3, premier choix pondéré 99,8 % à N = 146, lu par le juge) passe aussi cette porte ; seules la porte KL et la porte « défauts » séparent les cas ici. Je n'ai pas de passe qui échoue à 95 % pondéré (il faudrait un β grand) : la sensibilité de la porte n'est pas montrée sur ces données.
3. **« ≥ 10 % de défauts » est franchi de 0,02 point à β₁** (97 604 contre un seuil de 97 624,8) : un autre texte pourrait le manquer. β₂ (−12,1 %) tient avec ample marge ; la conclusion « tient » ne dépend pas de β₁ seul.
4. **Boucle ouverte** (limite 1 de l'étage B) : les ensembles sont calculés sur la trajectoire du modèle exact puis imposés ; un routeur biaisé en ligne ne choisirait pas tout à fait les mêmes. Non mesuré.
5. **Premier choix en lecture, pas en génération.** Un changement de premier choix à marge faible peut, en génération libre, dévier la suite du texte (les erreurs s'enchaînent) ; ici chaque position est notée sur le texte réel. Non mesuré.
6. **Un budget, un texte, dix fenêtres non indépendantes** (cache partagé de l'une à l'autre) : l'intervalle par rééchantillonnage sous-estime l'incertitude de population.
7. **Le gain en défauts est celui du LRU du moteur** ; l'affinage de l'étage A avait montré ce que donne un LFU, non rejoué ici.
8. **Poids de mélange** : ceux du softmax des quatre choisis (règle de l'article de Skliar et al.) ; non comparés à d'autres règles.
9. **Pilote qui a planté une fois** (§ 4) : le correctif touche une copie de fichier après la passe, pas le calcul ; les `.kld` de β₁ des deux exécutions sont identiques au bit.

## 6. Suite

1. Décision de Stone ou de l'orchestrateur : garder le critère pondéré comme porte de P3 (il est post hoc) ou exiger le littéral ; à N = 238 le littéral dit « non concluant » (91,96 %) et le pondéré « tient ».
2. Si le levier est gardé : le routeur biaisé **en ligne** dans le moteur (l'épreuve finale, qui lève la limite 4), avec mesure en génération (limite 5).
3. Variante bornée par la marge (échanger seulement si la marge est sous β), qui vise le premier choix directement, au même budget : elle pourrait faire passer le littéral.
4. Une passe à β grand pour montrer que la porte pondérée peut tomber (limite 2).
