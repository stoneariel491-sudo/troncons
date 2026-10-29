# P6, fidélité décidée par appel : résultat de l'étape 0 (octets et énergie, sans carte)

Rôle : expérimentateur P6. Date : 2026-10-27. Seuils : `mesures/mimetisme/P6/00-seuils-declares.md`
(commit 4d2b915, amendement A1 c206831, avant toute lecture de trace). Outils : `outils/mimetisme/P6/`
(`tiers.py`, `temoins.py`, `etape0.py`, `etape0_B.py`, `analyses.py`, `second_chemin.py`, `second_chemin_B.py`,
`niveaux-rust/`, `figures.py`). Mesures : `mesures/mimetisme/P6/`. Étiquettes : **[mes.]** mesuré ici,
journal commité ; **[calc.]** calculé de mesures commitées ; **[hyp.]** hypothèse dite ; **[mém.]** de mémoire,
non relu à la source. Aucune carte, aucune lecture de fichier modèle (le verrou
`~/dev/verrou-carte.txt` existait), 1 fil, RAM sous 1 Go.

## 0. Verdict

- **Étape 0, décodage (variante A), 120b génération : OUVERT** au seuil déclaré. Ni « tient » ni « tombe ».
  La règle « tient » exigeait, sur chacune des deux traces, r ≤ 0,70 et ≥ 8 % d'octets économisés à
  θ = 0,20. `gen-wiki` reste à **7,78 ± 0,38 %** d'octets (accepter) et 7,51 % (remonter à 0,40) ; `gen-prose-en`
  passe pour trois règles sur quatre. La règle « tombe » (toutes les règles à r > 0,90 ou S < 2 %) est loin d'être
  atteinte : r vaut 0,44 à 0,69 au cumul. Je ne déplace pas le seuil.
- **Étape 0, variante B (préremplissage, masse agrégée du lot) : TIENT** (3 genres sur 4 exigés, 4 sur 4 obtenus,
  120b et 20b) : à 8 % d'octets économisés, r = 0,039 à 0,060 (seuil 0,70), et r_B = 0,64 × r_A en moyenne
  (seuil : ≤ 0,90 × r_A). Cassure par tirage au hasard : r = 1,00.
- **Étape 1 (KL de bout en bout) : non lancée**, verrou de la carte présent et lecture de 8,31 Go requise. Le
  cahier est au § 6.
- Ce que l'étape 0 ne peut pas dire : si l'énergie (somme des w²) prédit la KL. Elle ne peut qu'éliminer.
  Une porte sur le poids baisse l'énergie par construction ; l'épreuve est l'étape 1.

## 1. Témoins [mes.]

| Témoin | Déclaré | Obtenu | Verdict |
|---|---|---|---|
| T0 : θ = 0 → E = S = 0 ; θ > 1, accepter → E = E_tout, S = 1 − ρ, r = 1 | exact, 1e-12 | 0 ; 0 ; 5,6e-16 ; 2,1e-14 ; 7,3e-14 | tient |
| T1 : comptage de physique, 4 genres de lecture, contre `portillon-de-poids.json` | défauts exacts, 1e-3 | défauts 707 322 = 707 322 ; écart max des parts 1,4e-6, des énergies 4,2e-7 | tient |
| T1, cassure : demi-vie 9 au lieu de 8 | doit tomber | défauts 703 603 ≠ 707 322 : tombe **par le nombre de défauts** ; les parts (8,3e-4) et énergies (9,6e-4) restent sous 1e-3 | tombe, mais la tolérance de 1e-3 était trop large pour le voir (l'accord réel est 1e-6) |
| T4 : taux de succès du cache contre le Rust sur les 7 traces du 120b | 1e-3 | écart max 2,7e-5 ; mais ≠ 1 défaut sur 4 traces (dialogue +1, prose-fr −1, gen-prose-en +1, gen-wiki +1) | tient au seuil déclaré ; l'égalité exacte des défauts ne tient pas (départage d'ex æquo, `exp` de la bibliothèque) |
| T3 : sélection au hasard, 50 tirages, 7 traces, accepter | r dans [0,93 ; 1,07] | 1,0001 (θ = 0,20), 1,0051 (0,25) | tient : l'estimateur n'est pas biaisé |
| T2 : poids mélangés entre positions, accepter, 7 traces | r dans [0,90 ; 1,10] (amendement A1) | **0,614** (vrai : 0,565) à θ = 0,20 ; 0,763 (vrai 0,757) à 0,25 | **tombe : ma prédiction A1 et celle de la consigne sont fausses** (§ 5) |

**Second chemin du chiffre principal** [mes.] : un automate Rust à étiquettes (`niveaux-rust`, écrit à part,
accès après accès) donne les mêmes S, E_rel et r que `tiers.py` pour les 4 règles sur les 2 générations du 120b
et les 5 générations du 20b : pire écart **6,4e-4** (journal `second_chemin.json`). Pour la variante B, un
calcul en boucles de dictionnaires redonne r(masse) et r(max) à 1e-3 sur les 4 genres (`second_chemin_B.json`).

## 2. Variante A, génération du 120b (θ = 0,20, N = 323, LFU 8, ρ = 0,718) [mes.]

S = octets économisés ; r = (E/E_tout) / (S/0,282) ; ± = 1 sigma, blocs de 32 jetons.

| Règle | `gen-prose-en` S / r | `gen-wiki` S / r | Cumul S / r | Tient ? |
|---|---|---|---|---|
| accepter | 10,10 % / **0,725** ± 0,061 | **7,78 %** ± 0,38 / 0,565 | 8,55 ± 0,40 % / 0,688 ± 0,058 | non (r sur prose-en, S sur wiki) |
| remonter à 0,30 | 8,22 % / 0,461 | **6,95 %** / 0,391 | 7,37 % / 0,442 ± 0,028 | non (S sur wiki) |
| remonter à 0,40 | 9,29 % / 0,573 | **7,51 %** / 0,451 | 8,10 ± 0,32 % / 0,539 ± 0,043 | non (S sur wiki) |
| remonter à 0,50 | 9,77 % / 0,613 | **7,74 %** / 0,553 | 8,41 % / 0,612 ± 0,043 | non (S sur wiki) |
| clairvoyant (borne) | 8,85 % / 0,140 | 7,19 % / 0,227 | 7,74 % / 0,185 ± 0,017 | hors verdict |

Au cumul des deux traces, accepter (S 8,55 %, r 0,688) et remonter à 0,40 (8,10 %, 0,539) passent les deux
seuils ; la règle déclarée voulait chaque trace séparément, parce que le milieu de la distribution (wiki,
taux de succès 0,48, 19 156 défauts) n'a pas la même loi de défauts que prose-en (taux 0,74, 9 510 défauts).
C'est pourquoi le verdict est « ouvert » et non « tient ».

Autres θ (cumul) : θ = 0,15 : S 2,2 %, r 0,58 (accepter) ; θ = 0,25 : S 15,6 à 18,3 %, r 0,50 à 0,75.

**Sensibilités** (cumul des deux générations, θ = 0,20, accepter) : N = 326 : S 8,54 %, r 0,692 ; N = 922 : 9,92 %,
0,765 ; LRU : 8,17 %, 0,763 ; demi-vie 32 : 8,93 %, 0,533 ; ρ = 0,70 : 9,09 %, 0,688 ; ρ = 0,766 : 7,09 %, 0,688.
La conclusion « ouvert » ne dépend pas de ces choix, sauf ρ = 0,766 (S 7,1 %, sous 8 %).

**Lectures secondaires** : le 20b (N = 54), cumul des 5 générations : S 9,16 %, r 0,413 (accepter) ; 4 traces sur 5
à S ≥ 8 % (prose-en 7,69 %), toutes à r ≤ 0,48. Lectures du 120b traitées jeton par jeton : S 8,35 %, r 0,559.
C'est au 20b que l'étape 1 aura lieu : l'étape 0 y est plus favorable que sur le 120b.

## 3. Ce que le prior et la consigne avaient faux [mes.]

- ~~Prior déclaré : « accepter » devrait voir r > 0,9 (portage de l'étiquette F sur les experts chauds).~~
  Mesuré : **r = 0,688** (cumul génération). Le portage coûte, mais pas autant : 77 % de l'énergie de
  « accepter » à θ = 0,20 vient des succès qui suivent l'entrée (portage), 23 % de l'entrée elle-même
  (`analyses.json`). Le portage multiplie r par 3,7 par rapport au comptage de physique (0,185 contre 0,688) ;
  il n'est pas rédhibitoire parce que les experts d'un séjour F sont des experts froids : 3,9 accès par séjour en
  moyenne sur prose-en, 1,9 sur wiki.
- ~~Consigne : « poids mélangés entre positions, r monte à ~1 ».~~ ~~Mon amendement A1 : « r tend vers 1 pour
  accepter ».~~ Le mélange rend 0,614 (au lieu de 0,565). Mon raisonnement oubliait que l'accès qui fixe
  l'étiquette est lui-même un petit poids (w < θ) et qu'il fait à lui seul l'énergie des séjours à un seul accès,
  les plus nombreux. La cassure qui donne r = 1 est le tirage au hasard (T3).
- ~~Physique : « 0,44 à 0,65 de perturbation par octet économisé ».~~ Ce chiffre divise par l'énergie des seuls
  défauts, comme si les succès restaient exacts, ce qu'un cache à un seul fichier ne permet pas. Il vaut
  presque exactement la loi marginale des poids (r₀ = 0,414 à θ = 0,20) : après mélange par couche, le comptage
  sans portage rend 0,1855 contre 0,1845 sans mélange (écart 0,001). **Les défauts ne sont pas corrélés aux petits
  poids** : tout le gain de la porte vient du poids lu à l'appel, aucun de l'état du cache. Avec le comptage honnête
  (portage compris) l'intervalle est 0,44 à 0,69, pas 0,44 à 0,65 mais du même ordre.
- Le « 8,6 % d'octets économisés » de physique tient (8,55 % ici au cumul de génération), mais c'est un
  cumul : la distribution des défauts varie d'une trace à l'autre de 7,8 à 10,1 %.

## 4. Variante B : préremplissage par masse agrégée [mes.]

Par lot de 512 jetons et par couche, chaque expert appelé est lu une fois. Règle A : rapide si le plus grand poids
reçu < θ ; règle B : si la somme des poids reçus (la masse) est parmi les plus petites. À octets économisés égaux :

| S | genre | r_A (max) | r_B (masse) | r_B / r_A | hasard |
|---|---|---|---|---|---|
| 8 % | code | 0,093 ± 0,007 | 0,060 ± 0,003 | 0,64 | 1,01 |
| 8 % | dialogue | 0,070 | 0,043 | 0,61 | 1,01 |
| 8 % | prose-en | 0,074 | 0,048 | 0,65 | 1,05 |
| 8 % | prose-fr | 0,059 | 0,039 | 0,66 | 0,98 |
| 14 % | code / dialogue / prose-en / prose-fr (r_B) | | 0,134 / 0,096 / 0,104 / 0,087 | | |

(20b, S = 8 %, r_B : 0,074, 0,030, 0,040, 0,034, wiki 0,035.) Lots de 128 et 256 : même sens, avantage de la masse
plus faible en petit lot (r_B/r_A = 0,74 à 128, 0,70 à 256, 0,64 à 512), comme attendu : la masse agrège d'autant
plus d'appels que le lot est grand. **Verdict déclaré : tient.**

En énergie, 8 % d'octets du préremplissage coûtent 1,1 à 1,7 % de l'énergie du tout-rapide (14 % : 4,3 à 6,6 %).
Sous l'hypothèse linéaire **[hyp.]** KL = 0,0044 + 0,1406 × E/E_tout : excès de KL de 0,002 à 8 %, 0,006 à 0,009
à 14 %. À ne pas lire comme un résultat. La mesure la plus fragile : l'énergie n'est pas la KL, et la perte porte sur
des experts de petite masse qui peuvent compter pour le routage de la couche suivante.

**Nouveauté honnête.** Dégrader selon l'importance de l'expert est connu (HOBBIT, Lu et al. [mém.]). Ce qui est
mesuré ici et ne l'était pas dans nos fichiers : la masse agrégée au lieu du maximum d'un appel, avec son gain de
36 % d'énergie à octets égaux, et la queue du préremplissage.

## 5. Exploratoire (hors verdict) [mes.]

- **Borne clairvoyante** : un portillon qui connaîtrait le plus grand poids que recevra l'expert pendant son séjour
  atteindrait r = 0,19 à θ = 0,20 pour ≈ 7,7 % d'octets, soit 3,7 fois moins d'énergie que le portillon causal. Il y a
  donc de la place, mais elle n'est pas dans le poids d'entrée : sa corrélation avec les poids suivants est 0,25 à 0,34.
- **Prédicteur statique** (poids moyen d'appel par expert, appris sur les 5 traces de lecture, jugé sur les générations) :
  l'écart-type de ce poids moyen entre experts n'est que 0,036 (moyenne 0,25, plage 0,09 à 0,56). Le meilleur couple
  essayé (30 réglages, tous listés dans `analyses.json`) : S 5,1 %, r 0,557 ± 0,045, contre 0,62 à S égal pour la
  porte seule : environ 10 % d'amélioration, dans 1 sigma. **Ne justifie rien.**
- **Courbe énergie(f)** (`courbe-plan-decodage.csv`) : à f = 0,19 défauts servis en rapide (θ ≈ 0,18), S = 5,3 % et
  E = 11,6 % du tout-rapide ; à f = 0,59 (θ = 0,24) S = 16,6 %, E = 43 %. La courbe KL(f) manquante reste à mesurer
  à l'étape 1 ; sous l'hypothèse linéaire, f = 0,19 donnerait un excès de 0,016.

## 6. Cahier de l'étape 1 (non lancée)

À faire après levée du verrou, sur le 20b (24 couches, 32 experts), les 10 fenêtres de 511 positions du jeu neuf,
juge `juge` du lot R (référence f64, substitution f64) avec `<nom>.rapide.trc` (8,31 Go) et le v1.2 exact :
1. **Variante B (la plus simple)** : une fenêtre est exactement un lot de 511 jetons et le juge traite couche après
   couche : la masse de chaque expert est connue avant son application. Servir en rapide les 28 % (S = 8 %) et 49 %
   (S = 14 %) d'experts de masse la plus faible, par couche ; comparer à la règle du maximum et à un tirage au hasard,
   à octets égaux. Seuil de la consigne : KL excédentaire ≤ 0,022 pour ≥ 8 % d'octets en moins ; mort > 0,040. Le
   tout-rapide donne 0,1448 ; le tout-exact 0,0044.
2. **Variante A** : rejouer le cache LFU 8 (N = 54) sur le routage de la fenêtre dans l'ordre des jetons, tenir
   l'étiquette de chaque emplacement, et servir chaque appel en exact ou en rapide selon la règle (accepter ; remonter
   à 0,40) ; θ = 0,20 et 0,25 ; les routages sont déterministes sous forçage (la fenêtre est la même vérité), donc le
   cache se simule hors ligne puis se donne au juge comme un tableau (jeton, couche, rang) → niveau.
3. Arrêt séquentiel O'Brien-Fleming (tri § 5). Au moins ~1 h de processeur par passe.
4. À mesurer en même temps, car l'étape 0 ne les voit pas : la KL en fonction de l'énergie (valider ou barrer
   l'hypothèse linéaire), et le coût en temps d'une remontée qui relit l'exact entier au beau milieu d'un jeton.

## 7. Ce qui pourrait être faux

- **L'énergie n'est pas la KL.** Tout r ci-dessus est une perturbation en somme de w², hypothèse de petite
  perturbation ; 96,5 % de la KL du mode rapide vient de bascules de routage (05 § 3.1), non linéaires. Le
  portillon peut tenir à l'énergie et tomber à la KL, ou l'inverse (si la KL est convexe en énergie, il gagne).
- **Un seul fichier rapide par ρ constant** : ρ = 0,718 est une moyenne ; les experts n'ont pas tous la même taille
  rapide. Un emplacement de VRAM de taille égale suppose un décodage identique pour les deux niveaux.
- **Traces courtes** : 256 jetons par génération (8 blocs), deux traces au 120b : l'incertitude de S (0,4 point)
  est de la taille de l'écart au seuil (0,2 point) ; le verdict « ouvert » est l'honnête.
- **LFU 8 au lieu de LFU(h\*) de P1** (P1 n'a pas rendu) ; les taux de succès simulés (0,74 et 0,48) sont plus hauts
  que celui du moteur mesuré (0,59 dans le tri) : les défauts réels sont plus nombreux, ce qui pousse S, pas r.
- **La remontée coûte un octet pour rien dans mon compte**, mais en vrai un arrêt du calcul pendant la relecture
  (4,1 ms) : les règles « remonter » ont un coût de latence non chiffré ici.
- **Prefill sans cache** : les 4 608 experts pour 323 emplacements rendent le cache inutile à 512 jetons ; à lot
  plus petit, le cache reprend de la valeur et le chiffre de B change.
- **Le bruit des témoins** : un départage d'ex æquo différent fait 1 défaut d'écart sur 4 traces (T4) ; la tolérance
  de T1 était trop large pour voir la demi-vie 9 autrement que par le nombre de défauts.

## 8. Suite possible

1. L'étape 1 de la variante B au 20b : une seule couche d'instrument à ajouter (masse par couche) et un tirage
   au hasard à même S comme cassure. C'est la mesure à faire en premier, car l'étape 0 la donne la plus
   favorable (r = 0,04) et la plus bon marché (aucun cache).
2. Pour la variante A, réunir 4 à 8 traces de génération de plus du 120b (aujourd'hui 2) avant de trancher
   « tient / tombe » ; ou lancer directement l'étape 1 au 20b où l'étape 0 passe (S 9,2 %, r 0,41).
3. Étudier ce qui prédit le plus grand poids d'un séjour (la borne clairvoyante est à r = 0,19) : ni le poids
   d'entrée (corrélation 0,3) ni le poids moyen de l'expert (écart-type 0,036) ne le font ; l'état caché, ou la
   marge du routeur (E7), pourrait.
4. Si la masse tient à la KL : P3 prend sa barre commune (pente KL par octet) ici ; sinon P3 doit en poser une autre.
