# Jugement de P6 : fidélité décidée par appel (portillon de poids, cache à niveaux)

Rôle : juge indépendant. Date : 2026-10-27. Objet : `genome/mimetisme/P6/resultat.md` (commit 9a8edf4).
Mes seuils : `mesures/mimetisme/P6/juge/00-seuils-du-juge.md`, commit aa1f5be, écrit avant tout calcul.
Mon chemin : `outils/mimetisme/P6/juge/` (`juge_p6.py`, `juge_controles.py`, `juge_rang.py`), Python pur,
accès après accès, sans rien importer des outils du rôle de mesure ; décroissance en 2^(−Δt/8) au lieu de la
table `exp`. Journaux : `mesures/mimetisme/P6/juge/` (`juge.json`, `juge.log`, `controles.json`, `rang.json`,
`gen20b.json`). Un fil, priorité basse, aucune carte, aucun fichier modèle lu (le verrou de la carte n'existait
plus à l'heure du jugement ; je n'en ai pas eu besoin). Traces extraites hors du dépôt.

## 0. Verdict

**Le chiffre principal est reproduit, exactement.** Les deux verdicts de classe le sont aussi : décodage
du 120b OUVERT, variante B TIENT à l'étape 0. Trois réserves, dont deux graves pour la lecture :

1. **Le « tient » de B ne pouvait presque pas tomber.** La masse (Σw) est à 2 à 4 % de l'oracle de la mesure
   elle-même (le tri par Σw², optimal par construction pour l'énergie à octets égaux), sur 8 genres sur 8
   (120b et 20b). L'étape 0 ne l'élimine pas, mais elle ne la soutient pas non plus. Le « gain de 36 % sur le
   maximum » mesure seulement l'écart entre deux substituts de la mesure, un bon et un mauvais. Il ne dit rien de
   la KL. `pour-le-memoire.md` écrit bien la proposition (r_C ≤ r_B ≤ r_A) ; `resultat.md` et le signal envoyé à
   main ne disent pas que B est quasi l'oracle.
2. **Une affirmation du verdict est fausse** : « les défauts ne sont pas corrélés aux petits poids ». Ils le sont.
   Le taux de défaut est de 35 % au rang 0 (le plus grand poids) et de 56 % au rang 3. 29,6 % des défauts sont
   sous θ = 0,20, contre 24,9 % quand on détruit le rang à l'intérieur du groupe. Le test du rôle de mesure
   (mélange des vecteurs par couche) garde le rang, et son r est aveugle à cette corrélation par construction :
   elle passe dans S (les octets), pas dans r.
3. **« Ouvert » tient au choix de θ fixe, pas au mécanisme** (lecture exploratoire, hors seuils) : à octets égaux,
   S = 8 % trace par trace, r vaut 0,669 (prose-en) et 0,573 (wiki), tous deux sous 0,70. Le verdict déclaré
   reste « ouvert » : je ne le déplace pas.

## 1. Reproduction (seuil : |ΔS| ≤ 0,002, |Δr| ≤ 1 % relatif, même classe) [mes.]

120b, génération, θ = 0,20, N = 323, LFU 8, ρ = 0,718. Défauts : 9 510 et 19 156, identiques à ceux du rôle de mesure.

| Règle | prose-en S / r (juge) | wiki S / r (juge) | cumul S / r (juge) | rôle de mesure, cumul |
|---|---|---|---|---|
| accepter | 10,10 % / 0,7249 | **7,78 %** / 0,5652 | 8,548 ± 0,40 % / 0,6879 ± 0,058 | 8,55 ± 0,40 % / 0,688 ± 0,058 |
| remonter 0,30 | 8,22 % / 0,4606 | 6,95 % / 0,3906 | 7,37 % / 0,4420 | 7,37 % / 0,442 |
| remonter 0,40 | 9,29 % / 0,5729 | 7,51 % / 0,4512 | 8,10 % / 0,5394 | 8,10 % / 0,539 |
| remonter 0,50 | 9,77 % / 0,6129 | 7,74 % / 0,5525 | 8,41 % / 0,6116 | 8,41 % / 0,612 |

Écart maximal : sous 1e-4 en S, sous 1e-3 en r. **Reproduit.** σ de S sur wiki : 0,37 point (rôle de mesure :
0,38, autre graine). Classe : aucune règle ne passe S ≥ 8 % sur wiki, aucune n'a r > 0,90 : **ouvert**, confirmé.
20b, génération, N = 54 (secondaire) : S 9,16 %, r 0,413, prose-en 7,69 % : reproduit.

**Variante B** (lots de 512, lot partiel final compris, comme le rôle de mesure) :

| genre (120b, S = 8 %) | r_A juge / mesure | r_B juge / mesure | oracle Σw² (juge) | r_B / oracle | r_B / r_A |
|---|---|---|---|---|---|
| code | 0,0933 / 0,093 | 0,0598 / 0,060 | 0,0576 | 1,04 | 0,64 |
| dialogue | 0,0701 / 0,070 | 0,0435 / 0,043 | 0,0416 | 1,04 | 0,62 |
| prose-en | 0,0743 / 0,074 | 0,0482 / 0,048 | 0,0464 | 1,04 | 0,65 |
| prose-fr | 0,0594 / 0,059 | 0,0387 / 0,039 | 0,0372 | 1,04 | 0,65 |

Reproduit à mieux que 1 %. Sans le lot partiel, les écarts montent jusqu'à 4 % (r_A code 0,097) : c'est la seule
différence de convention, elle ne change rien. 20b : r_B de 0,030 à 0,075, reproduit. Tirage au hasard : r = 0,995
à 1,010. **Verdict déclaré de B : tient, reproduit.**

## 2. Seuils commités avant la lecture [vérifié par git log]

- `4d2b915` (00:50:49) : seuils, un seul fichier, avant tout code. `c206831` (00:52:11) : amendement A1, un seul
  fichier, avant toute simulation. Premier code et premières mesures : `6ad1c77` (01:01:26). L'ordre est bon.
  Je ne peux pas prouver l'heure de l'extraction des traces : seul l'ordre des commits est vérifiable.
- Les seuils ne bougent pas entre les commits, et le verdict « ouvert » respecte la règle par trace déclarée,
  alors que le cumul passait. C'est honnête.
- Une circularité douce, déclarée : 8 % et 0,70 sont dérivés des agrégats de physique (8,6 %, 0,44), calculés
  sur les traces de lecture du même 120b, connus avant d'écrire les seuils.

## 3. Témoins

- **Le mien, T-J1, tombe comme il doit** : la porte lit un poids permuté au hasard sur toute la trace et l'énergie
  se compte sur le vrai poids ; r = 1,074 au cumul, dans [0,90 ; 1,10]. Mon T-J0 tient : θ = 0 donne S = E = 0, et θ = 2
  donne r = 1 à 6e-15. Mon T-J2 tient : les défauts sont identiques à l'unité.
- Ceux du rôle de mesure : T3 (hasard, r = 1,0001) est une vraie cassure, reproduite en esprit par T-J1. T2 (mélange)
  rend 0,614 contre [0,90 ; 1,10] déclaré, et c'est dit et barré. **Mais l'explication donnée est incomplète.** Selon
  elle, seul l'accès d'entrée, petit par sélection, retient r sous 1. Or, sous le même mélange, l'énergie des seuls
  succès des séjours F vaut 0,895 fois leur part, et pas 1 (`controles.json`). Le mélange garde le rang (les poids
  d'un groupe sont triés), et un expert froid, souvent appelé au rang 3, continue de recevoir des poids de rang 3.
- La cassure de T1 ne tombe que par le nombre de défauts : c'est dit.

## 4. Ce qui est faux ou trop beau

1. **B, quasi l'oracle de sa mesure** (§ 0.1). Le seuil « tombe si r_B ≥ r_A » ne pouvait guère tomber, car le
   maximum est un moins bon substitut de Σw² que la somme, quelle que soit la loi des poids. Le seuil « r_B ≤ 0,70 »
   est passé d'un facteur 12. Ma prédiction déclarée (r_B ≤ 1,30 × oracle sur 4 genres sur 4) tient sur 8 genres
   sur 8, à 1,015 à 1,043. Lecture : à l'étape 0, la masse dit seulement que l'énergie d'un lot se concentre dans
   les experts souvent appelés. La question vraie est entière : servir en rapide les experts rares d'un lot touche
   peu de jetons, mais touche chacun avec son poids d'appel, qui peut être grand (r_A le montre) ; avec 96,5 % de la
   KL venus des bascules de routage, la concentration sur quelques jetons peut peser autrement que l'énergie moyenne.
2. **« Les défauts ne sont pas corrélés aux petits poids »** (§ 0.2, `rang.json`, 7 traces du 120b) : les défauts
   se répartissent en 19,4 / 23,1 / 26,8 / 30,6 % des rangs 0 à 3. Le comptage sans portage donne r = 0,1845 (vrai),
   0,1856 (mélange par couche) et 0,1855 (rang détruit) : r ne voit rien, parce qu'il ne dépend que de la loi de w
   sachant w < θ. La part des défauts sous θ, elle, passe de 29,6 % à 24,9 %. L'état du cache donne donc à la porte
   environ 19 % d'octets économisés de plus (29,6 / 24,9 = 1,19) à θ égal. La phrase « aucun [gain] de l'état du cache » est à barrer.
3. **La conclusion « ouvert » mesure surtout θ** : S passe de 2,2 % (θ = 0,15) à 8,5 % (0,20) puis 16 % (0,25),
   parce que les poids se tassent autour de 0,2. Un seuil de S à θ fixe est un fil de rasoir. À S = 8 % exact (θ = 0,188
   et 0,201), r = 0,669 et 0,573 [exploratoire, hors seuils, `controles.json`]. Une porte à θ adaptatif (quantile
   glissant des poids) est la forme qu'on déploierait ; elle n'a pas été déclarée, donc elle ne compte pas ici.
4. Vérifiés et justes : la part de 77 % de l'énergie de « accepter » portée par les succès (juge : 77,2 %),
   les défauts, les σ, le 20b.
5. Hygiène : `outils/mimetisme/P6/__pycache__/tiers.cpython-313.pyc` est commité (deux fois).

## 5. Ce que P6 peut dire, et ne peut pas dire

- Il peut dire : le portillon de poids à θ = 0,20 économise 7,8 à 10,1 % des octets lus en génération du 120b
  pour 16 à 26 % de l'énergie du tout-rapide (r = 0,57 à 0,72). Au préremplissage, la masse par lot atteint
  presque l'optimum de l'énergie. Le portage de l'étiquette coûte un facteur 3,7 sur la borne clairvoyante.
- Il ne peut pas dire que la masse est une bonne règle pour la qualité : l'énergie n'est pas la KL, et à l'étape 0
  la masse est presque la mesure elle-même. Seule l'étape 1 (KL au 20b, cahier du § 6 de `resultat.md`) jugera. Elle
  doit garder la règle du maximum et le hasard comme comparaisons à octets égaux. Il faut y ajouter l'oracle Σw² :
  si la KL suit l'énergie, masse et oracle doivent donner la même KL ; s'ils divergent, l'hypothèse linéaire tombe.
- La phrase sur la non-corrélation des défauts et des petits poids est à barrer dans `resultat.md` § 0 et § 3.
