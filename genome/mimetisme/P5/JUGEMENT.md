# P5 : le jugement (recuit et échange de répliques sur le choix des symboles synonymes)

Rôle : juge indépendant. Je n'ai rien construit de P5. Date : 2026-10-27. Étiquettes : **[mes.]** mesuré ici, outil et
journal commités ; **[calc.]** calculé ici sur des journaux commités ; **[lu]** lu dans un journal de P5, non refait.
Seuils déclarés avant toute lecture de capture par mes outils : `mesures/mimetisme/P5/juge/00-seuil-juge.md`
(commit c5d8c30, 01 h 55 ; addendum J5 au commit 0847680, avant son lancement). Outils :
`outils/mimetisme/P5/juge/` (`juge_p5.py`, `juge_pt.py`, `resume_juge.py`, lots `.sh`) ; journaux :
`mesures/mimetisme/P5/juge/` (j1, j2, j3, j5, lam02, temoins, pt, `resume.json`).

Mon chemin est écrit de zéro en numpy : mon propre lecteur des captures (h et routage), mon H pondéré g², ma
quantification MXFP4, mon Babai par le facteur GPTQ classique (Cholesky de H⁻¹, pas la factorisation renversée de
`synonyme.py`), ma descente cyclique vectorisée sur les rangées avec g = H r tenu à jour, mon échange de répliques
(bain thermique par tirage de Gumbel, `dger` en place). Rien de `p5lib.py`, `etape1.py` ni du noyau Rust.

---

## 0. En bref

1. **Le chiffre principal tient, à l'identique.** Sur les mêmes poids synthétiques (graine 1), mon Babai rend les
   symboles de `synonyme.py::choisir` sur les 8 instances (0 différence sur 8 × 184 320) et la descente cyclique
   donne, instance par instance, **le gain d'évaluation de P5 à 4·10⁻¹⁴ point près** : médiane CD λ = 0
   **5,09 %**, au meilleur des deux λ **5,46 %** (P5 : 5,5 %), **0 instance sur 8 au-dessus de 10 %** [mes.].
   Le gain sur la calibration est aussi le leur (médiane 52,8 %) : le sur-ajustement est réel.
2. **Il tient aussi sur des poids neufs** (graine 2026, que P5 n'a jamais tirée) : médiane CD **5,5 %**, 1 instance
   sur 8 au-dessus de 10 % (12,1 % à L23-E0), 1 négative (−0,3 % à L8-E16) [mes.]. La classe du verdict,
   **OUVERT** (ni succès ni mort), se reproduit.
3. **Mes témoins tombent** : zéro balayage rend Babai exactement (écart 0) ; H d'entraînement aux colonnes
   permutées : gain d'évaluation **−91 %** en médiane, 8 / 8 négatifs ; test inclus dans l'entraînement : **+49,6 %**
   (P5 : +49,6 %). L'instrument distingue.
4. **Le mécanisme annoncé (« le levier est le nombre d'entrées de calibration ») ne tient pas au seuil** (grave, § 4).
   (a) Le « soutenu » de l'addendum 3 repose sur une lecture du seuil : le seuil déclaré dit « le gain médian de CD
   sur le test monte d'au moins 2 points » ; les deux médianes publiées côte à côte, 5,9 % puis 7,3 %, font
   **+1,4 point**, ce qui tombe dans « non tranché ». Le « +2,6 points » est la médiane des montées par instance,
   une autre grandeur. (b) Mon test qui sépare N de la source (J5, déclaré avant : **retirer** la moitié des
   entrées de calibration, même source, même test) ne fait baisser le gain médian que de **0,4 point** (médiane des
   baisses 1,7 point, 7 / 8 en baisse) : sous le seuil déclaré de 0,5 point, **non soutenu**. Ce que l'addendum 3
   a mesuré mêle « plus de N » et « des entrées prises dans le fichier d'évaluation, voisines du test », ce que P5 avait
   lui-même nommé « fuite possible ».
5. **L'échange de répliques** : mon PT reproduit la baisse de l'objectif de P5 à 0,1 point près, mais pas son gain
   d'évaluation : médiane **4,8 %** (sous ma CD), 0 / 8 au-dessus de 10 %, contre 6,8 % et 1 / 8 chez P5 ; le
   12,3 % de L0-E16 devient 6,3 %. Le chiffre PT de P5 est un tirage du chemin de l'optimiseur (§ 3).
6. Le reste se lit dans les journaux comme écrit, avec trois erreurs de texte mineures (§ 5).

## 1. La chronologie : seuil avant lecture

| Commit | Heure (−04:00) | Ce qu'il fixe | Premier journal qui suit (mtime) |
|---|---|---|---|
| ec124f5 | 00:43:05 | seuils de la piste (tri) | |
| ab92f4e | 00:49:04 | seuils de l'étape 1, témoins W1-W4 | témoins : 00:56:04 |
| 598042a | 01:08:27 | addendum 1 (64 rangées, δ = 0,3 et 0,1, point de comparaison) | `L00-E00-d1.json.err` : 01:08:28 |
| f09b0ef | 01:45:24 | addendum 2 (cible diagonale) | `diag-L00-E00-d1.json.err` : 01:45:25 |
| d958a46 | 01:49:03 | addendum 3 (variation de N) | `test2-L00-E00.json.err` : 01:49:04 |

[lu, git log et mtime] Chaque déclaration précède d'une seconde le premier fichier de son lot. Git ne prouve pas ce
qui a été regardé hors journal (le pilote de 16 rangées, dit dans l'addendum 1, n'a pas de journal) ; rien ne
l'indique avant 00:49. Deux lignes rapportées ne sont **pas** déclarées : δ = 3 (l'addendum 1 nomme 1, 0,3 et 0,1 ;
les journaux δ = 3 commencent à 01:31) et l'estimateur de Gibbs (aucun seuil ; `resultat.md` § 4 le dit lui-même,
mais l'en-tête du § 4 annonce « toutes avec seuil déclaré avant »). Aucune des deux n'entre dans le verdict, et
l'artefact de δ = 3 est déjà barré par P5. L'étape 2 n'a pas tourné : aucun journal d'étape 2 dans le dépôt
(vérifié), conforme à la règle.

## 2. Le chiffre principal par mon chemin (J0, J1, J2)

| Instance | N calib | P5, CD λ = 0 | **juge, mêmes poids** | juge, meilleur des 2 λ | **juge, poids neufs (2026)** | ΔH0 CD λ = 0 (bit) |
|---|---|---|---|---|---|---|
| L0-E0 | 762 | 4,74 | **4,74** | 4,74 | 0,40 | +0,0032 |
| L0-E16 | 1 334 | 8,87 | **8,87** | 8,87 | 6,87 | +0,0045 |
| L8-E0 | 1 329 | 7,88 | **7,88** | 7,91 | 8,06 | +0,0040 |
| L8-E16 | 300 | 3,83 | **3,83** | 3,83 | −0,27 | +0,0033 |
| L16-E0 | 330 | 3,23 | **3,23** | 3,23 | 6,87 | +0,0040 |
| L16-E16 | 147 | 1,43 | **1,43** | 1,43 | 3,90 | +0,0025 |
| L23-E0 | 303 | 7,55 | **7,55** | 7,55 | 12,07 | +0,0035 |
| L23-E16 | 239 | 5,43 | **5,43** | 6,18 | 4,07 | +0,0035 |
| **médiane** | | 5,09 | **5,09** | **5,46** | **5,47** | |
| ≥ 10 % | | 0 / 8 | **0 / 8** | 0 / 8 | **1 / 8** | |

Gains d'évaluation tenue à l'écart en %, δ = 1, 64 rangées. [mes.] Écart juge / P5 par instance ≤ 4,4·10⁻¹⁴ point ;
erreur d'évaluation de Babai et de CD égales aux JSON de P5 à 9·10⁻¹⁶ relatif ; second chemin (erreur recalculée
sur les entrées X) à 1,1·10⁻¹⁶. Seuils J1 (±1 point en médiane, ±2 par instance) et J2 (médiane dans [3 ; 10 [ %,
moins de 6 / 8 au-dessus de 10 %) : **tenus**.

La graine neuve dit l'ampleur du hasard des poids : la même instance bouge de 4 à 5 points d'une graine à l'autre
(L0-E0 4,7 → 0,4 ; L23-E0 7,6 → 12,1). Un « 1 / 8 au-dessus de 10 % » n'a donc pas de sens instance par instance ;
seule la médiane est stable (5,1 et 5,5).

**Le débit.** À λ = 0, CD monte H0 de +0,0025 à +0,0045 bit sur les 8 instances, toujours dans la tolérance de
±0,005 mais toujours du même côté. Ce biais ne fabrique pas le gain : à λ = 0,2, CD descend sous le débit de Babai
λ = 0 (−0,0005 à −0,0019 bit) et garde presque le même gain (médiane 5,46 % au meilleur des deux).

**Le PT** (phase optionnelle, descriptive, mon échange de répliques numpy, même réglage déclaré que P5 :
8 températures de 0,02 à 1,0 fois l'erreur de Babai par poids, 40 balayages, trempe depuis le meilleur état) : § 3.

## 3. L'échange de répliques par mon chemin (descriptif)

Mon échange de répliques (λ = 0, graine 1, mêmes poids que P5, générateur 11) [mes., `juge/pt/`], gains en % :

| Instance | juge PT : objectif | P5 PT λ = 0 : objectif | **juge PT : évaluation** | P5 PT λ = 0 / 0,2 : évaluation | juge CD : évaluation | ΔH0 juge PT |
|---|---|---|---|---|---|---|
| L0-E0 | 8,58 | 8,68 | **2,46** | 4,93 / 5,62 | 4,74 | 0,0047 |
| L0-E16 | 9,21 | 9,30 | **6,30** | 12,33 / 8,45 | 8,87 | 0,0051 (hors tol.) |
| L8-E0 | 7,60 | 7,63 | **9,75** | 9,14 / 9,10 | 7,88 | 0,0051 (hors tol.) |
| L8-E16 | 8,14 | 8,07 | **5,24** | 2,64 / 2,83 | 3,83 | 0,0042 |
| L16-E0 | 8,06 | 8,12 | **4,32** | 4,82 / 4,63 | 3,23 | 0,0047 |
| L16-E16 | 6,37 | 6,33 | **1,55** | 2,98 / 2,43 | 1,43 | 0,0035 |
| L23-E0 | 5,51 | 5,49 | **9,76** | 8,40 / 9,54 | 7,55 | 0,0038 |
| L23-E16 | 5,33 | 5,31 | **4,00** | 6,81 / 7,95 | 5,43 | 0,0038 |
| **médiane** | 7,83 | | **4,78** | 6,8 (meilleur des deux) | 5,09 | |

Ce que cela dit. **L'optimiseur se reproduit** : mon PT baisse l'objectif d'entraînement comme celui de P5, à 0,1
point près sur chaque instance. **Son gain d'évaluation ne se reproduit pas instance par instance** : à qualité
d'objectif égale, deux PT tombent sur des états dont l'erreur tenue à l'écart diffère de 2 à 6 points (L0-E16 :
6,3 contre 12,3). Ma médiane PT, 4,8 %, est **sous** celle de ma CD (5,1 %) ; 0 / 8 au-dessus de 10 %. La classe du
verdict se reproduit (OUVERT) ; le « PT 6,8 %, 1 / 8 » et le « +1,4 point au-dessus de CD » de P5 ne se
reproduisent pas : ils sont dans le bruit du chemin de l'optimiseur. Cela renforce la conclusion de P5 (le recuit
ne se justifie pas) et le diagnostic de sur-ajustement : un meilleur objectif ne fait pas une meilleure évaluation.

Le seul « ≥ 10 % » de P5 (PT 12,3 % à L0-E16) est pris au meilleur des deux λ : à λ = 0 sa paire est à
0,00494 bit du bord de tolérance, et à λ = 0,2 le même PT y fait 8,5 % [lu, `gains-d1.csv`]. Il ne change pas le
verdict (il en faudrait 6).

## 4. Ce qui ne tient pas : le mécanisme « N » (grave)

**(a) La lecture du seuil de l'addendum 3.** Texte déclaré (d958a46) : « soutenu si le gain médian de CD sur le
test monte d'au moins 2 points de "test2" à "plus" et monte sur ≥ 6 instances sur 8 ». Refait par mon chemin, à
l'identique de P5 [mes.] :

| | médiane test2 | médiane plus | montée des médianes | médiane des montées | en hausse |
|---|---|---|---|---|---|
| CD, gain de test | 5,86 % | 7,27 % | **+1,41 point** | +2,64 points | 7 / 8 |

« Le gain médian monte » se lit d'abord comme la montée de la médiane : +1,41 point, entre 0,5 et 2, donc **non
tranché**. `resultat.md` écrit « +5,9 % à +7,3 % (… +2,6 points ; seuil soutenu tenu) » : les deux médianes
qu'il cite font 1,4, et le 2,6 est la médiane des différences, choisie sans que la déclaration le dise. Les autres
chiffres de l'addendum se reproduisent exactement : 0,866 (moyenne de CD « plus » / Babai « test2 »), 0,941 pour
Babai seul, 7 / 8 en hausse. Ma propre déclaration J3 (« montée médiane du gain ») a la même ambiguïté ; je donne
donc les deux lectures, et seule l'une des deux tient leur seuil.

**(b) N seul (J5, déclaré avant).** Entraînement sur la première moitié des positions de calibration (même source,
N divisé par 1,8 à 4,5, 2,3 en médiane), test sur toute l'évaluation [mes.] :

| Instance | N base → demi | gain CD base | gain CD demi | baisse (points) | Babai demi / Babai base |
|---|---|---|---|---|---|
| L0-E0 | 762 → 354 | 4,74 | 3,12 | 1,62 | 1,025 |
| L0-E16 | 1 334 → 685 | 8,87 | 5,28 | 3,59 | 1,022 |
| L8-E0 | 1 329 → 700 | 7,88 | 6,22 | 1,66 | 1,056 |
| L8-E16 | 300 → 67 | 3,83 | −0,11 | 3,93 | 1,060 |
| L16-E0 | 330 → 129 | 3,23 | 4,93 | −1,70 | 1,101 |
| L16-E16 | 147 → 82 | 1,43 | −0,25 | 1,68 | 1,121 |
| L23-E0 | 303 → 114 | 7,55 | 4,51 | 3,04 | 1,059 |
| L23-E16 | 239 → 97 | 5,43 | 4,80 | 0,64 | 1,120 |
| **médiane** | | **5,09** | **4,65** | **0,43** (médiane des baisses 1,67) | **1,059** |

Au seuil déclaré (baisse du gain médian ≥ 2 points et ≥ 6 / 8 = soutenu ; < 0,5 point = non soutenu) : **non
soutenu** (0,43) ; sous l'autre lecture (médiane des baisses, 1,67) : non tranché. Diviser N par 2,3 en médiane coûte
donc moins au gain de CD qu'ajouter 40 % d'entrées venues du fichier d'évaluation ne lui rapporte. N compte, mais
faiblement : le gain de CD ne monte pas en proportion de N, et la montée de l'addendum 3 se confond avec la proximité
des entrées ajoutées et du test (fenêtres 0-4 et 5-9). Ce qui est net, en revanche : **N compte pour Babai
lui-même** (diviser N par 2 lui coûte 6 % d'erreur d'évaluation en médiane, et 2 % à 12 % selon l'instance).

**Conséquence pour la suite de P5.** La suite 1 de `resultat.md` (« le levier est le nombre d'entrées de
calibration ; N cible 2 à 3 fois plus grand ») et le signal envoyé à la session principale reposent sur un
mécanisme que mes deux tests ne soutiennent pas au seuil. Ce qui reste juste : le sur-ajustement (calibration
−52 %, évaluation −5 %), que je reproduis. Si l'on veut mesurer le levier N, le test propre est celui que P5
proposait lui-même : des fenêtres d'entraînement **lointaines** et de même source que la calibration, avec un N
qui varie à source fixe.

## 5. Erreurs de texte mineures

- `resultat.md` § 0 et addendum 2 : « rang ≤ N = 762 à 1 329 ». Les journaux donnent N = 147 à 1 334 (§ 3 de
  `resultat.md` a les bons nombres ; N moyen 593, N « plus » moyen 827, comme écrit ailleurs).
- `resultat.md` § 4 : « toutes avec seuil déclaré avant » est faux pour δ = 3 et pour l'estimateur de Gibbs (§ 1).
- Le « meilleur des deux λ » pris par instance avantage la méthode (dit par P5) ; il pèse 0,4 point en médiane pour
  CD (5,09 → 5,46).

Vérifiés et justes [calc.] : les bits du § 4 (ρ = 0,935 → 0,049 bit ; 0,946 → 0,040 ; 0,866 → 0,104 ; 0,80 → 0,161
par D ∝ 2^(−2R)) ; les journaux des témoins de P5 portent ce qu'écrit `resultat.md` [lu] : Babai rate l'optimum
sur 847 / 1 000, PT 1 000 / 1 000 à 3 000 balayages et 43 échecs à 200, gel 107 / 847, H permuté 2 / 847, second
énumérateur 12 / 12 (passe 1 ; la passe 2 n'en a pas relancé), sphère n = 16 : PT = sphère 10 / 10, Babai non optimal
6 / 10.

## 6. Verdict

**Le chiffre principal TIENT pour la descente cyclique** : reproduit à l'identique par un chemin indépendant
(CD 5,1 % en médiane, 5,5 % au meilleur des deux λ, 0 / 8 au-dessus de 10 %), et sur des poids neufs (5,5 %, 1 / 8).
**Le chiffre de l'échange de répliques ne se reproduit qu'en classe** (mon PT : 4,8 %, 0 / 8, contre 6,8 %, 1 / 8) :
son écart à CD est du bruit d'optimiseur. Le verdict de P5,
**OUVERT, sous le seuil de succès, hors de la zone de mort**, tient ; l'étape 2 n'est pas autorisée par la règle,
et elle n'a pas tourné.

**Le mécanisme annoncé NE TIENT PAS au seuil** : « soutenu » seulement sous une lecture du seuil que la déclaration
ne fixait pas (montée des médianes +1,4 point, non tranché), et non soutenu par le test qui isole N (J5 : −0,4 point
pour un N divisé par 2,3 en médiane). Le levier « nombre d'entrées de calibration » reste une hypothèse ; il ne doit pas
commander la suite de P5 tant qu'un test à source fixe et à fenêtres lointaines ne l'a pas mesuré.

Limites de ce jugement : poids synthétiques comme P5 (aucune lecture de fichier modèle) ; 64 rangées ; le PT de mon
chemin a son propre générateur et ne peut égaler celui de P5 qu'en loi.
