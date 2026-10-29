# P2, cache exclusif VRAM vers RAM : résultat

Date : 2026-10-27. Rôle : expérimentateur de P2. Seuil : `seuil-declare.md` (commité en 6f3d737, avant toute
lecture de trace). Outils : `outils/mimetisme/P2/`. Mesures : `mesures/mimetisme/P2/`. Aucune carte graphique,
aucun fichier modèle, un fil, 7 traces du 120b et 10 du 20b.

## 1. Verdict au seuil déclaré : OUVERT

Seuil : réduction relative de la part disque (exclusif contre inclusif, V = 326, R = 336) ≥ 15 % sur les
DEUX générations ET descente ≤ 25 % du jeton (345 ms) ; mort si < 5 % sur l'une.

| génération (V = 326, R = 336) | disque inclusif | disque exclusif | réduction | descentes par jeton | descente / jeton |
|---|---|---|---|---|---|
| prose-en | 0,2573 | 0,1845 | **28,3 %** | 36,5 | **11,5 %** |
| wiki | 0,5926 | 0,2885 | **51,3 %** | 85,9 | **27,2 %** |

La première condition tient sur les deux (28,3 % et 51,3 % contre 15 %). La seconde tombe sur wiki
(27,2 % contre 25 %). Ni « tient » ni « tombe » : **ouvert**. Le seuil n'est pas modifié après coup.
Le seuil de 25 % repose sur un jeton fixe de 345 ms ; wiki génération a 87 défauts VRAM par jeton (le
disque seul y demanderait 357 ms), son jeton réel n'est pas 345 ms. Le critère passerait si le jeton
de cette charge durait ≥ 375 ms (93,7 / 0,25). Ce n'est pas mesuré : je ne l'invoque pas pour changer le verdict.

Lecture secondaire, V = 922 (non décisive, elle n'est pas le chiffre principal déclaré) : réduction 24,1 %
et 25,0 %, descentes 17,7 et 28,6 par jeton soit 5,6 % et 9,0 % du jeton. À cette capacité, les deux
conditions tiendraient.

## 2. Témoins (tous tenus ; ils pouvaient tomber)

| témoin | résultat |
|---|---|
| T0 : R = 0 en exclusif = LRU seul | égalité exacte des entiers, 7 traces |
| T1 : inclusif à R ≤ V ajoute 0 | 0,0 à R = 80 et 160 (tolérance 1e-4) ; au plus 7,65e-4 à R = V = 326 (tolérance 1e-3 déclarée). La tolérance de 1e-4 de la consigne ne tient pas à R = V |
| T2 : exclusif = LRU de V + R | écart max 6,63e-4 (tolérance 7e-4, serré) sur 14 cellules |
| T3a : démotion supprimée, RAM jamais remplie | redonne le LRU seul exactement |
| T3b : remplissage au défaut, sans retrait ni démotion | redonne l'inclusif exactement (égalité par construction des interrupteurs ; l'indépendance vient de T4 et du Rust) |
| diagnostic `cass_c` (remplissage au défaut + retrait à la remontée) | 0,2419 et 0,5620 à R = 336 : ni l'inclusif ni l'exclusif ; prouve que les comparaisons discriminent et que la démotion est la source du gain |
| T4 : reproduit `h2.csv` de l'éclaireur | écart max 4,8e-4 (tolérance 5e-4, serré ; `h2.csv` est arrondi à 5 décimales) |

T2 sur le 20b : écart jusqu'à 1,4e-3 à V = 154 (hors tolérance de 7e-4). Diagnostic
(`holdout20b-t2-sans-epinglage.json`) : sans épinglage des groupes, l'écart est **exactement 0,000000** sur
trois traces ; l'écart vient donc de la règle de groupe, pas du théorème (le théorème est vérifié
exactement sans pins sur le 20b).

## 3. Second chemin : tient

`second_chemin.rs` (horodatages et balayage linéaire, aucune liste ordonnée) contre `cache_exclusif.py` :
154 cellules (7 traces, V = 326 et 922, R = 0, 80, 160, 336, 672, 1344, inclusif et exclusif), écart max 0
sur la part disque, le succès RAM, les accès et le nombre de descentes. Limite : les deux codes sont de moi
et traduisent la même lecture des règles ; l'indépendance de la spécification vient de T4 (code de l'éclaireur,
écart ≤ 4,8e-4).

## 4. Ce que ça dit

1. **Théorème 1 (`pour-le-memoire.md`, § 3) : l'exclusif à deux étages LRU vaut un LRU de capacité V + R.**
   Démontré par récurrence sur la pile LRU, vérifié à 6,6e-4 sur le 120b et exactement (0) sans épinglage
   sur le 20b. Le gain est la masse des distances de pile dans la bande (V, V + R] (figure 1).
2. **La RAM tiède actuelle (inclusive) est inutile tant que R ≤ V** : 0,0000 de succès RAM à R = 80 et 160 sur
   les 7 traces, et 0,0048 à 0,0137 à R = 336. L'exclusif met les R places à servir.
3. **Rentabilité en série (calcul posé, § 5 de `pour-le-memoire.md`)** : gain positif si et seulement si la
   part ρ des défauts VRAM servis par la RAM dépasse b / (a − b) = 1,09 / 3,01 = 0,362. Mesuré : prose-en
   génération ρ ≈ 0,30 (déficit en série), wiki ρ ≈ 0,52.

Temps de service des défauts par jeton, 120b, V = 326, R = 336 (a = 4,1 ms, b = 1,09 ms ; en série la descente
s'ajoute, recouverte elle disparaît ; `net-selectif-120b.csv`, lignes s = 0) :

| trace | LRU seul | exclusif en série | exclusif recouvert |
|---|---|---|---|
| prose-en génération | 154,7 ms | 160,9 (**−6,1**) | 121,1 (+33,6) |
| wiki génération | 357,6 ms | 313,8 (+43,8) | 220,1 (+137,5) |

Pour prose-en, l'exclusif simple perd en série : il faut recouvrir au moins 15,4 % de la descente pour équilibrer
(ω ≥ 1 − 33,6 / 39,75 = 0,154, avec 33,6 ms de gain recouvert et 39,75 ms de descente). Le recouvrement
(PCIe duplex avec le calcul) n'est pas mesuré.

La chaîne invite puis réponse (cache chauffé par la lecture du même genre, `chaine.csv`) donne à V = 326,
R = 336 : prose-en 0,2549 -> 0,1812 (−28,9 %), wiki 0,5912 -> 0,2859 (−51,6 %). Même ordre que les
générations à froid.

## 5. Piste post-hoc : la démotion sélective (hors seuil, dite comme telle)

Après avoir vu le verdict « ouvert », j'ai essayé de ne descendre que les victimes réutilisées au moins `s`
fois en VRAM (`seuil-declare-selectif.md`, commité avant d'ouvrir le 20b). `s = 0` redonne l'exclusif simple
exactement. À R = 336, `s = 1`, 120b (`explore-selectif.csv`, `net-selectif-120b.csv`) :

| trace | disque s=0 | disque s=1 | descentes s=0 -> s=1 | gain série s=0 -> s=1 (ms/jeton) |
|---|---|---|---|---|
| prose-en gen. | 0,1845 | **0,1769** | 36,5 -> 18,1 | −6,1 -> **+17,2** |
| wiki gen. | 0,2885 | 0,3649 | 85,9 -> 42,7 | +43,8 -> **+57,9** |
| 5 lectures | 0,273 à 0,404 | 0,234 à 0,379 (mieux sur 5/5) | ~77 -> ~44 | +2,6..16,2 -> +61,7..65,3 |

Réduction contre l'inclusif avec `s = 1` : 31,2 % (prose-en) et 38,4 % (wiki) ; descente / jeton 5,7 % et
13,5 % : les trois conditions du seuil de P2 tiendraient. Gain série positif sur les 7 traces. Contre-exemples
dits : wiki génération a une part disque pire qu'avec `s = 0` (0,3649 contre 0,2885), et à R = 672 prose-en et
wiki génération empirent avec `s = 1`.

**Test aveugle sur le 20b** (autre modèle, 24 couches, 32 experts ; seuil déclaré avant :
`seuil-declare-selectif.md` ; `holdout20b.csv`, `verdict-selectif.json`) :
- V = 54 (7,07 % des cellules, le « principal » que j'avais déclaré) : **tombe** au seuil déclaré (b échoue
  5/5). Mais ce régime est dégénéré, et c'est une erreur de ma déclaration : un jeton du 20b touche 96 cellules
  distinctes, V = 54 est plus petit ; le LRU seul a 100 % de défauts, aucune entrée n'est jamais réutilisée en
  VRAM, le filtre ne laisse donc descendre rien. Je ne redéclare pas pour sauver le résultat.
- V = 154 (secondaire déclaré) : (a) 5/5, (b) 5/5, (c) 4/5 (prose-en : descentes 0,73 × celles de `s = 0`
  contre 0,6 exigé) : **ouvert**. Réductions contre l'inclusif : 26,7 % à 52,2 %.

Lecture honnête : le filtre est cohérent avec la logique du scan-resistance (une entrée jamais réutilisée en
VRAM n'a pas de raison de coûter une descente), et il tient sur 120b (7/7 en série) et sur 20b à V = 154
(5/5 pour a et b). Mais il a été choisi après coup, le seul test aveugle est au mieux « ouvert », et il dépend
d'un régime où V dépasse l'empreinte d'un jeton.

## 6. Ce qui pourrait être faux

- Le taux de succès simulé dépasse le taux mesuré du moteur (0,74 contre 0,59 sur prose-en) : le gain
  absolu est probablement plus petit en vrai ; le tri a prévu de n'exiger que la moitié, et le seuil est
  passé avec marge sur les réductions (28 % et 51 % pour 15 % exigés).
- Les générations ont 256 jetons et démarrent à froid ; la chaîne invite-réponse donne le même ordre mais le
  texte de l'invite diffère de celui de la réponse.
- Tous les experts ont la même taille dans ce simulateur (la part d'accès égale la part d'octets). Le moteur
  a des tailles par expert (`fixer_tailles`).
- La RAM d'un étage exclusif contient des experts **décodés** (13,25 Mo) : R = 336 engage 4,45 Go. Un
  étage RAM encodé (1,8 ms à la remontée) est incompatible avec la démotion simple : il faudrait ré-encoder
  la victime. Avec la montée seule à 1,8 ms au lieu de 1,09, le surcoût est ≈ 8 ms par jeton (prose-en).
- Le temps de jeton de 345 ms est fixe dans le seuil ; wiki n'est pas dans ce régime (§ 1).
- Le recouvrement de la descente avec le calcul n'est pas mesuré. Je borne les deux cas extrêmes plutôt
  que de le supposer. Il décide du signe pour l'exclusif simple sur prose-en.
- Le LFU(h*) de P1 n'est pas essayé : P1 n'a pas de conclusion commitée à l'heure où j'écris.
- `T1` à R = V dépasse 1e-4 (cause plausible : l'épinglage ; non démontrée) ; T2 et T4 passent avec peu de marge.
- Les deux codes (Python, Rust) sont de la même main : même lecture des règles de `trc-cache`. La règle de
  RAM du moteur est lue dans `lib.rs` (l. 150-260), pas exécutée.

## 7. Suite possible

1. Moteur, ABBA `--ram-tiede` 1 / 4 / 8 Go avec le mode exclusif (carte nécessaire : après levée du verrou
   `verrou-carte.txt`, qui existe en ce moment). Mesurer le recouvrement réel de la descente : c'est ce qui
   départage l'exclusif simple de la version sélective.
2. Décision de Stone : engager 4,45 Go de RAM (R = 336 sur 15,6) ; V = 922 demande moins de RAM pour le même
   gain relatif (24-25 %).
3. Valider la démotion sélective sur des traces de génération indépendantes du 120b (quatre traces de plus,
   passe moteur) avant de la construire ; régler `s` en validation croisée et non sur les traces jugées.
4. Variante sans trafic de descente : retenir au défaut disque la copie encodée de la lecture (aucune descente)
   et la rendre évinçable en priorité quand l'entrée est en VRAM ; à simuler, non mesurée ici.

## 8. Fichiers

Seuils : `seuil-declare.md`, `seuil-declare-selectif.md`. Mémoire : `pour-le-memoire.md`, `figures/`.
Outils : `cache_exclusif.py`, `second_chemin.rs`, `verdict.py`, `explorations.py`, `holdout20b.py`,
`diag_t2_20b.py`, `verdict_selectif.py`, `net_selectif.py`, `figures.py`. Mesures : `temoins.csv`, `t1bord.csv`,
`grille.csv`, `chaine.csv`, `rust.csv`, `verdict.json`, `explore-distances.csv`, `explore-selectif.csv`,
`holdout20b.csv`, `holdout20b-temoins.json`, `holdout20b-t2-sans-epinglage.json`, `verdict-selectif.json`,
`net-selectif-120b.csv`.
Sources lues : Wong et Wilkes, « My Cache or Yours? Making Storage More Exclusive », USENIX ATC 2002
(page lue le 2026-10-27 : https://www.usenix.org/conference/2002-usenix-annual-technical-conference/my-cache-or-yours-making-storage-more-exclusive).
Sources [mém.] non relues : Mattson, Gecsei, Slutz, Traiger 1970 (distances de pile) ; Johnson et Shasha 1994
(2Q).
