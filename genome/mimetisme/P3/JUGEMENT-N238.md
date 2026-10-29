# P3, étage B à N = 238 : jugement indépendant (2026-10-27)

Rôle : juge de la mesure à N = 238, par défaut « non reproduit = ne tient pas ». Lu : `SOCLE.md`, `resultat-N238.md`,
`JUGEMENT-etage-B.md`, `mesures/mimetisme/P3/03-critere-marge-declare.md`, `04-ensembles-N238.md`, `etage-B/N238/`.
Mon chemin : `outils/mimetisme/P3/juge/N238/juge_N238.py`, écrit sans importer `p3_*.py`, le `juge kl` ni le lecteur du juge
de N = 146 : lecteur `.kld` réécrit (paquets de 8 positions, ~200 Mo de pointe, un fil), LRU réécrit **par horodatage**
(et non par liste ordonnée comme les trois LRU déjà cités) depuis la définition de `00-seuils-declares.md` § 2.
Sorties : `mesures/mimetisme/P3/juge/N238/`. Aucun seuil changé. Pas de carte graphique, pas de verrou, aucune passe du moteur.

Ordre : je n'ai pas commité de critères à part avant mon chemin ; les valeurs à retrouver étaient dans la consigne. Règle
appliquée : égalité au dernier chiffre affiché pour les défauts et les premiers choix, écart par position de l'ordre du f32
pour la KL.

## 1. Verdict

**Reproduit**, aux deux β, au dernier chiffre affiché : KL, premier choix littéral, premier choix pondéré, défauts, imposition,
témoin T0 au bit, empreintes de T0 et T1 inchangées depuis N = 146, antériorité du critère sur les passes.
Le verdict déclaré tient tel qu'il est écrit : **pondéré « tient, partiel », littéral « non concluant »**.

Mais un défaut grave de **portée** (§ 5, G1) : sur les données réelles disponibles, la condition « premier choix pondéré
≥ 95 % » **ne mord jamais avant la KL**. Les huit fichiers réels dont la KL est ≤ 0,029 la passent tous à 97,1 % ou plus,
llama.cpp compris ; le seul fichier réel qui la manque a une KL de 0,243. Le « tient » pondéré dit donc, à ce jour,
« défauts −10 % et KL ≤ 0,038 », pas une troisième chose. Le témoin qui peut la faire tomber sur le levier demande une passe :
cahier au § 6, non lancé.

## 2. Antériorité (git)

| commit | heure | contenu |
|---|---|---|
| `c4a037a` | 05:48:45 | seuils de l'étage B ; `00-seuils-declares.md`, `02-etage-B-declare.md`, `cahier-etage-B.md` **inchangés depuis** (`git diff --stat c4a037a HEAD` vide sur les trois) |
| `e8bf954` | **08:06:07** | `03-critere-marge-declare.md`, seul fichier ; **inchangé depuis** |
| (fichiers) | 08:06:40 / 08:06:43 | journaux imposés `B238/…b0.041-N31.bin`, `…b0.05-N31.bin` écrits **après** le critère |
| `a073e61` | 08:07:17 | `04-ensembles-N238.md` + `ensembles-N238.json` (prédiction écrite) |
| (fichier) | **08:08:08** | création de `ref-openai-p3-N238-b0.041-20b.kld`, première passe neuve |

Aucun `.kld` de N = 238 n'existait avant 08:08 (relevé de tout `essais/`). Le journal de β₂ existait depuis 01:23 (calculé le
matin, `B/…b0.05-N31.bin`, identique au bit) mais aucune passe ne l'avait lu. Le script d'analyse (`205c915`, 08:09:12) est
commité avant la fin de la première passe (08:30). **Ordre respecté.**

## 3. Ce que j'ai refait

### 3.1 Empreintes (`empreintes.json`)

- `ref-openai-20b.kld` = `ref-openai-p3-T0-20b.kld` = d97fc421…2a38, **égal** à l'empreinte relevée par le juge de N = 146 ;
  `ref-openai-p3-T1-20b.kld` = 3f922699…431f, **égal** aussi. Journal β = 0 : e908eb93…baf6 à N19 **et** à N31 (le même
  fichier) ; cassure T1 : 23db486b…6046. La réutilisation de T0 et T1 est fondée.
- Journaux imposés : source `B238/`, copie lue par le moteur (`mesures/moteur/R/r1/routage/p3-N238-b*-N31.bin`, chemin
  relevé dans la commande de chaque passe) et valeur déclarée égaux : f7365cd8…13eb (β₁), 102b47f8…d319 (β₂).
- `.kld` : 5b68e543…737afa (β₁, celui que `resultat-N238.md` § 3 cite) et 8313896f…f339 (β₂). Le routage enregistré par la
  première exécution de β₁ (gardé à part) est identique au bit à celui de la dernière (bd74d8ac…c676).

### 3.2 Défauts de cache, mon LRU à horodatage (`defauts.json`)

| journal (N = 238) | défauts (moi) | déclaré | variation | cellules changées |
|---|---|---|---|---|
| β = 0 | **108 472** | 108 472 | | |
| β = 0,040 | 97 883 | 97 883 | −9,762 % (ne passe pas) | 7,136 % |
| **β₁ = 0,041** | **97 604** | 97 604 | **−10,0192 %** | 8 939 = **7,289 %** |
| β₂ = 0,050 | **95 341** | 95 341 | **−12,1054 %** | 10 831 = **8,832 %** |
| β = 0,1 (étage A) | 83 999 | 83 999 (`etage-A.csv`) | −22,56 % | 16,58 % |
| β = 0,3 (étage A) | 50 988 | 50 988 | −52,99 % | 37,72 % |

- Seuil −10 % : 0,9 × 108 472 = **97 624,8** ; β₁ passe de 20,8 défauts (0,019 point). −10,02 % est l'arrondi juste de
  −10,0192 %. β₁ est bien le premier pas de 0,001 qui franchit le seuil (0,040 le manque).
- Cassures de mon LRU (chacune doit changer le compte, chacune le change) : accès l puis t → 734 ; ordre inverse dans le groupe
  → 108 433 ; 1 000 cellules tirées au hasard → 112 137.
- **Imposition effective** : routage enregistré par le moteur = journal imposé, quatre experts dans le même ordre, dans
  **122 640 / 122 640** cellules aux deux β ; il diffère de β = 0 dans 8 939 et 10 831 cellules (exactement les cellules
  changées), et ses marges sont celles que le moteur a recalculées (écart jusqu'à 2,72 et 2,84 avec les marges du fichier
  imposé) : l'imposition a été appliquée, le fichier n'a pas été recopié.

### 3.3 KL et premiers choix relus des `.kld` (`analyse.json`, `kl-b*-positions.csv`)

| | KL (Σ sur log p > −16) | KL (tout le vocabulaire) | KL renormalisée | littéral | pondéré (marge ≥ 0,3) |
|---|---|---|---|---|---|
| β₁ = 0,041 | **0,0117202** | 0,01175 | 0,01174 | **91,96 %** (205) | **98,75 %** (20 / 1 601) |
| déclaré | 0,01172 | | | 91,96 % | 98,75 % |
| β₂ = 0,050 | **0,0153424** | 0,01536 | 0,01534 | **91,14 %** (226) | **98,38 %** (26 / 1 601) |
| déclaré | 0,01534 | | | 91,14 % | 98,38 % |

- 1 601 positions à marge ≥ 0,3 : retrouvé. Contre le CSV de `juge kl` (lu après mon calcul) : écart par position au plus
  3,6e-7 et 3,8e-7, **aucune** position où le premier choix diffère. La convention de KL pèse au plus 3e-5.
- T0 et `ref-openai-bis` : KL 0, accord 100 % (le lecteur ne fabrique pas de désaccord).

## 4. Ce qui pourrait être faux ou trop beau

### 4.1 Sensibilité au seuil de marge (post hoc, aucun seuil changé)

| marge ≥ | 0 | 0,05 | 0,1 | 0,2 | **0,3** | 0,5 | 1,0 |
|---|---|---|---|---|---|---|---|
| positions | 2 550 | 2 342 | 2 182 | 1 880 | **1 601** | 1 153 | 520 |
| β₁ | 91,96 | 95,05 | 96,47 | 97,82 | **98,75** | 99,39 | 99,81 |
| β₂ | 91,14 | **94,11** | 95,65 | 97,45 | **98,38** | 99,31 | 100 |
| N = 146, β = 0,06 | 88,43 | 91,67 | 93,72 | **95,85** | 97,44 | 98,79 | 99,23 |
| N = 146, β = 0,07 | 87,57 | 91,03 | 93,22 | **95,37** | 97,19 | 98,44 | 99,23 |

Marge minimale pour 95 % (pas de 0,005) : β₁ 0,05 ; β₂ 0,075 ; N = 146 : 0,155 et 0,185. Le résultat est solide de 0,075 à
1,0 aux deux β ; à 0,05, β₂ tombe (94,11 %). À N = 146, **0,2 suffisait déjà** à passer 95 % : `03-` ne cite que 0,1
(93,7 %) ; le 0,3 retenu n'est pas le plus petit seuil rond qui sauvait N = 146, il en est un plus large d'environ 1,5 point.

### 4.2 Intervalles (`analyse.json`)

Premier choix pondéré, 20 000 tirages :
- par fenêtres (10 blocs) : β₁ **[98,30 ; 99,19]**, β₂ [97,88 ; 98,90] (résultat : [98,30 ; 99,19] et [97,87 ; 98,91], écart
  de graine) ;
- par blocs de 51 positions contiguës (50 blocs) : β₁ [98,17 ; 99,26], β₂ [97,73 ; 98,98] ;
- part des tirages sous 95 % : **0** dans les quatre cas ; pire fenêtre : 97,30 % (β₁), 96,99 % (β₂).
La borne basse est à plus de 3 points du seuil : « tient à l'estimation » et « à l'intervalle » coïncident.

### 4.3 Le critère fixé après lecture

Dit en toutes lettres dans `03-` (a) et (c), commité avant les passes : je le confirme. Ce que cela coûte, chiffré : la
prédiction écrite avant (« pondéré > 96 % ») suivait mécaniquement de N = 146, puisque N = 238 change moins de cellules
(7,3 % contre 11,9 %) ; le rapport « désaccords pondérés / part de cellules changées » vaut 0,171 et 0,184 ici contre 0,215 et
0,203 à N = 146. Le test était donc **peu sévère** : il pouvait tomber, mais rien ne l'y poussait.

### 4.4 Le témoin manquant : la porte pondérée peut-elle tomber ?

Ce que j'ai pu faire sans moteur, sur des fichiers réels déjà calculés (aucune relance) :

| fichier réel contre `ref-openai` | KL | littéral | pondéré ≥ 0,3 | intervalle par fenêtres |
|---|---|---|---|---|
| `llamacpp-routage-openai` | 0,00168 | 97,22 % | 99,69 % | [99,37 ; 100] |
| T1 (cassure 1 %) | 0,00208 | 98,00 % | 99,81 % | [99,62 ; 100] |
| **β₁ = 0,041 (N = 238)** | 0,01172 | 91,96 % | **98,75 %** | [98,30 ; 99,19] |
| `llamacpp` (llama.cpp seul) | 0,01455 | **92,55 %** | **98,06 %** | [97,32 ; 98,77] |
| β₂ = 0,050 (N = 238) | 0,01534 | 91,14 % | 98,38 % | [97,88 ; 98,90] |
| N = 146, β = 0,06 | 0,02089 | 88,43 % | 97,44 % | [96,77 ; 98,13] |
| N = 146, β = 0,07 | 0,02393 | 87,57 % | 97,19 % | [96,20 ; 98,17] |
| `llamacpp-imite-q8-kv16` | 0,02880 | 89,80 % | 97,13 % | [96,36 ; 97,92] |
| `sans-echelle` (YaRN sans échelle) | **0,24278** | 58,16 % | **70,02 %** | [65,32 ; 73,98] |

1. **La lecture pondérée peut tomber** : sur un vrai fichier du moteur (`sans-echelle`), 70,0 % ; par un décalage d'une
   position entre référence et β₁ (cassure d'instrument), 14,75 % ; en remplaçant au hasard les premiers choix de β₁ par ceux
   de `sans-echelle` sur 20 % des positions, 93,07 % (5 % : 97,88 ; 10 % : 96,31 ; 40 % : 86,70). L'instrument n'est pas
   aveugle.
2. **Mais elle ne mord pas avant la KL** sur les données réelles : désaccord pondéré de 1,0 à 1,3 point pour 0,01 de KL
   (1,25 % à 0,0117, 1,94 % à 0,0146, 2,56 % à 0,0209, 2,87 % à 0,0288) ; à KL = 0,038 on attend 95 à 96 %, soit au mieux
   **au bord** de la porte KL. Aucun fichier réel n'est à la fois sous la porte KL et sous 95 % pondéré.
3. **Repère qui change la lecture des deux seuils** : llama.cpp contre la même référence (deux moteurs presque exacts) fait
   92,55 % littéral et 98,06 % pondéré. Le levier à β₁ est **plus proche de la référence que llama.cpp au pondéré** (98,75
   contre 98,06) et **0,6 point plus loin au littéral** (91,96 contre 92,55, dans l'intervalle [91,02 ; 92,86] de β₁). Le seuil
   littéral de 95 % rejetterait llama.cpp lui-même ; le seuil pondéré de 95 % est 3 points sous llama.cpp. Je ne change aucun
   seuil ; je le donne à qui décidera (`resultat-N238.md` § 6.1).
4. La cassure T1 passe la porte pondérée (99,81 %, 3 désaccords sur 1 601) : confirmé ; elle ne tombe que sur la porte KL du
   témoin (2,08e-3 > 1e-4).

Le témoin qui fait tomber la porte pondérée **sur le levier lui-même** demande une passe du moteur : cahier au § 6.

## 5. Défauts

**Graves**

- **G1 (portée, pas reproduction).** La condition « premier choix pondéré ≥ 95 % » n'a montré aucun pouvoir de séparation
  dans la zone admise par la KL : 8 fichiers réels à KL ≤ 0,029 la passent à ≥ 97,1 %, dont llama.cpp ; le seul fichier
  réel qui la manque est à KL 0,243 ; extrapolée, elle ne mordrait qu'au bord de la porte KL (95 à 96 % à KL 0,038). `resultat-N238.md` § 5.2 le dit pour T1 ; il faut le dire pour toute la zone : à ce jour,
  « tient (pondéré) » = « −10 % de défauts et KL ≤ 0,038 », le premier choix pondéré n'y ajoute pas de preuve propre. Le verdict
  n'est pas faux, sa troisième condition est non démontrée comme discriminante.

**Mineurs**

1. `03-` (a) ne rapporte de N = 146 que 0,1 (93,7 %) et 0,3 (97,4 %) ; 0,2 (95,85 % / 95,37 %) passait déjà. À dire.
2. `resultat-N238.md` § 2 cite llama.cpp à 90,4 % (R0, non revérifié) ; le `.kld` `ref-llamacpp-20b.kld` de r1 contre
   `ref-openai-20b.kld` donne **92,55 %** (KL 0,01455). Les deux comparaisons ne sont peut-être pas les mêmes ; la phrase
   « le 91,96 % littéral est de cet ordre » reste vraie, mais le levier est sous llama.cpp, pas au-dessus.
3. Décodage du `.kld` : Σ exp(log p) de la référence va de 0,99999 à **1,021** selon la position (quantification des
   log-probabilités sur 16 bits). Les trois conventions de KL diffèrent d'au plus 3e-5 en moyenne : sans effet sur le verdict.
4. −10 % franchi de 20,8 défauts à β₁ (dit au § 5.3 du résultat) ; β₂ tient seul avec −12,1 %.
5. Déterminisme de β₂ non répété (dit) ; les routages enregistrés de β₁ (deux exécutions) sont identiques au bit.
6. Quatre fils au lieu des deux du cahier (dit dans `03-` (e)).

## 6. Cahier du témoin à faire (non lancé : il demande le moteur)

But : montrer que la porte pondérée **peut tomber sur le levier**, sur une passe neuve, avec une prédiction déclarée ici,
avant toute passe.

- Fichier : `~/dev/essais/troncons/mimetisme/P3/routage-impose-V1-b0.3-N31.bin` (étage A, déjà calculé,
  SHA-256 2b93c38c…1ab7 ; −52,99 % de défauts, 37,72 % de cellules changées, mon LRU = `etage-A.csv`). Le copier sous
  `B238/` au même nom, vérifier l'empreinte, puis `python -I -X utf8 outils/mimetisme/P3/p3_etageB_N238.py 0.3` (même pilote,
  mêmes garde-fous : verrou, secteur, swap ≤ 4 Go, contrôle 122 640 / 122 640). ~12 min, ~2,3 Go de pointe, CPU, 4 fils ;
  lancer avec ≥ 6 Go de RAM disponible (l'incident 3 de `resultat-N238.md` § 4).
- **Prédiction déclarée** [calc., extrapolation linéaire en part de cellules changées sur les quatre passes du levier,
  rapports 0,171 à 0,215 pour le premier choix, 0,161 à 0,176 pour la KL] : premier choix pondéré **91,9 à 93,5 %**, donc
  **sous 95 %** ; KL **0,061 à 0,066** (bande large 0,045 à 0,12, la croissance pouvant être plus que linéaire). Lecture
  fixée d'avance : pondéré < 95 % → le témoin tombe, la porte pondérée a du pouvoir sur le levier ; pondéré ≥ 95 % → la porte
  pondérée est aveugle jusqu'à −53 % de défauts, et G1 devient « la condition ne sert à rien ».
- Variante facultative, β = 0,1 à N31 (SHA-256 f6c65983…c2b4, −22,56 %, 16,58 % changées) : prédiction pondéré 96,4 à 97,2 %,
  KL 0,027 à 0,029. Ce n'est pas un témoin (il devrait passer) : c'est un point de pente.

## 7. Reproduire

```
cd outils/mimetisme/P3/juge/N238
python -I -X utf8 juge_N238.py empreintes
python -I -X utf8 juge_N238.py defauts     # ~1 min
python -I -X utf8 juge_N238.py kl          # lit 12 × 1 Go en flux, ~200 Mo ; 25 à 45 min selon le disque
python -I -X utf8 juge_N238.py analyse
python -I -X utf8 juge_N238.py comparer
```
