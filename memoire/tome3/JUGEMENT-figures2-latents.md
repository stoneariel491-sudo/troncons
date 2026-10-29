# Jugement : figures du Tome III, second flux, lot « espaces latents » après corrections

Juge indépendant des chiffres, 2026-10-27. Je n'ai rien tracé. Objet jugé : le commit `326969f` (lot latents du
second flux : III-7.6, III-9.1 (d), III-9.7), contre le premier flux (`c4f3fe2`, `3ce3553`, `33ff6ee`) et ses
jugements (`JUGEMENT-figures-latents.md`, `-design.md`, `-construction.md`, `-ronde.md`). Règles : SOCLE (dont la
demande de Stone du 2026-10-17, « la beauté à égalité avec la justesse »), l'inventaire (R1 à R6), les
conventions communes (`CONVENTIONS-figures.md`). Outils et journaux : `outils/genome/tome3/juge2-latents/`.

## 0. Verdict

**Les chiffres tiennent, les graves de dessin sont levés, mais III-9.7 tombe pour sa phrase de tête.**

- Chaque nombre neuf ou déplacé est refait par un chemin écrit de zéro, depuis la source quand elle existe (GGUF,
  `.sym` du lot B, captures de l'éclaireur), sinon depuis les fichiers commités. **64 nombres, tous égaux** à
  l'arrondi écrit (29 pour III-9.7, 35 pour III-7.6).
- Le script du lot régénère ses **24 fichiers `latents-*` au bit**, sans fichier en trop ni manquant. Ses deux
  témoins neufs tiennent ; leurs cassures tombent ; une cassure n'écrit rien sous `donnees/`.
- Les graves du premier flux qui touchent le lot sont **levés** : G1 (couleurs de III-9.1 et III-9.7), G2 (III-7.6
  en petits multiples) et la part du lot dans G9 (légendes). D18, D25 et les mineurs M2 à M10 du premier juge sont
  traités. D20 l'est aussi, mais la nouvelle lecture de la figure crée GN1.
- **Un grave neuf, GN1** (III-9.7). La tête dit : « Là où pointent les entrées de l'expert, le synonyme ramène
  l'erreur de sortie à au plus 0,135 de celle de la frontière. » C'est vrai des **projections** des entrées sur
  deux plans. C'est faux des entrées elles-mêmes. Pour les 1 329 entrées réelles, dans leurs 2 880 dimensions, le
  rapport ‖ΔW_s x‖ / ‖ΔW_f x‖ va de **0,49 à 0,81** (médiane 0,61). **Aucune** n'est sous 0,135.
- **9 mineurs neufs** (§ 6). Le plus visible : la tête de la rangée dit que le synonyme « éloigne ces poids de leur
  valeur exacte », or l'un des quatre, le zéro négatif de j = 11, reste à la même distance.
- Rien n'est corrigé par moi dans les fichiers du lot. GN1 et N1 demandent de réécrire des phrases et d'ajouter des
  nombres : ce n'est pas mécanique.
- **Deux incidents hors du lot** (§ 7) :
  - MiKTeX est passé de 26.2 à 26.5 vers 12 h 22, sans moi. Depuis, le préambule commun lève six erreurs
    (thmtools). Aucun pilote du mémoire ne compile plus sans erreur.
  - J'ai effacé par mégarde le PDF français du pilote du lot. Je l'ai remplacé par celui que j'ai compilé sur les
    sources du commit.

| Figure | Tient ou tombe | En une ligne |
|---|---|---|
| III-7.6 | **tient** | G2 levé ; 35 nombres égaux ; bords refaits dans le plan et dans l'espace d'origine ; noms posés par densité, pas par pureté (N3) |
| III-9.1 (d) | **tient** (réserves) | G1, D18 levés ; 32 lignes égales à la source ; « éloigne ces poids » faux pour j = 11 (N1) ; lettre (d) sur une prémisse fausse (N2) |
| III-9.7 | **tombe** | GN1 : la tête et le cône parlent des projections comme des entrées ; tous les nombres sont justes |

## 1. Méthode

1. **Lire ce qui a changé.** J'ai lu `git show 326969f`, le diff de `latents-chiffres.tex` depuis `33ff6ee` (37
   macros neuves, 11 retirées, aucune valeur gardée qui change), le `.tex`, le script et la note du lot. J'ai écrit
   mes outils d'après les légendes et les formats, sans reprendre de ligne au lot ni au premier juge.
2. **Les nombres, par mon chemin** :
   - `juge2_lecteurs.py` relit le GGUF v3, le MXFP4 de ggml, les `.sym` et les captures. Témoin :
     ‖W − Ŵ‖²_F égale Σ e_k du spectre commité du lot B, à 1,8e-12 près (frontière 40,0709, synonyme 48,0056).
     Cassure, avec les `.sym` de l'expert 1 : écart relatif de 49,9, le témoin tombe.
   - `juge2_nuage_rangee.py` et `juge2_etats.py` refont les nombres, puis les comparent à l'arrondi des macros.
     Témoin du comparateur (`--casser`, chaque valeur fausse de 1 %) : 24 nombres sur 29 et 17 sur 35 tombent ;
     les autres sont des entiers que 1 % ne déplace pas à l'arrondi.
3. **La régénération au bit** (`juge2_regen.py`). Le script du lot et ses seules entrées sont tirés du commit par
   `git archive` vers un brouillon hors du dépôt, et le script y est relancé.
   - Il faut `core.autocrlf=false` : sinon `git archive` rend des fins de ligne CRLF, et toutes les comparaisons
     tombent pour une raison qui n'est pas le lot. Je l'ai vu au premier essai.
   - La comparaison se fait par SHA-256. Les deux cassures du lot sont relancées.
   - Témoin du comparateur : un bit inversé dans chaque fichier ; les 24 comparaisons tombent.
4. **Les points tirés.** Un par série neuve au moins (graine du juge 2710202602), contrôlé à la source (§ 4).
5. **La compilation** (`juge2_compiler.py`). Le pilote du lot tourne sur les sources du commit, `lualatex` deux
   passes par langue (trois si le journal le demande). J'ai lu les pages, agrandies à 250, 300 et 800 dpi.
6. **Les phrases barrées** (`juge2_barrees.py`). Les 238 passages barrés des 188 documents Markdown du commit sont
   découpés en suites de cinq mots, puis cherchés dans le texte des légendes. Témoin : une phrase barrée glissée
   dans ce texte est trouvée.

Mémoire : au plus 1,5 Go par outil (ΔW, H et les entrées en f64 ; distances par blocs de 256 lignes).

## 2. Les graves du premier flux : levés ou non

| Grave | Ce qui était demandé | Vu dans `326969f` | |
|---|---|---|---|
| **G1** (design ; M7 du juge 1) | synonyme en bleu, frontière en gris du dictionnaire, colonnes « codon changé » en bleu pâle, ligne synonyme de la bande en bleu ; III-9.7 de même | voir la ligne suivante | **levé** |
| | | `CouleurSynonyme`, `CouleurFrontiere`, losange `CouleurFrontiereMarque`, triangle `CouleurExact`, `CouleurSynonyme!10` | |
| | | III-9.7 : courbe synonyme en tirets bleus, rose en `black!35` | |
| | | aucune `SerieX`, aucun `latRose`, aucun `black!50` (vérifié par recherche) | |
| | | rendu lu à 300 et 800 dpi : le losange gris sort sous le rond bleu là où le symbole ne change pas | |
| **G2** (design ; M2, M3 du juge 1) | III-7.6 : petits multiples, couleur jamais seule, taille à z(1) − z(2) ou retirée | voir la ligne suivante | **levé** |
| | | 2 × 4 cartes t-SNE, un expert par carte en bleu sur le nuage gris ; la place dit l'expert ; la taille disparaît | |
| | | les 614 états sous le 10e centile de z(1) − z(2) sont en noir | |
| | | en gris, bleu L\* = 38,3 et noir L\* = 9,3 (fond 89 et 73) : les trois se séparent | |
| | | les huit séries contrôlées ligne à ligne (§ 4) | |
| **G9** (part du lot) | `\Titre`, `\Legende` (tête en gras, provenance), `\Source` dans le `\caption` | les trois figures ; le pilote appelle `\LegendeFigure` ; rendu : tête en gras, étiquette « [mes.] », ligne « Données » alignée | **levé** |
| D18 / M6 | dire ±0 et les flèches | dit : « +k » et « −k » notent le niveau ±c_k, pas un zéro signé | **levé** (la flèche de j = 11 ne se voit pas : N5) |
| D20 / M8 | III-9.7 : fonction d'appui, direction des entrées | fait, mais la tête en tire une conclusion fausse | **remplacé par GN1** |
| D25 | plus de `\tiny` | 0 occurrence | **levé** |
| M4 (juge 1) | dire la définition du hasard | « somme des carrés des parts », Σp² = 12,156 % | **levé** |
| M5 | le seuil de la t-SNE sans puissance | dit : « que son initialisation par l'ACP atteint déjà » | **levé** (voir la note) |
| | | l'initialisation est `acp / acp[:,0].std() · 1e-4`, une homothétie : rangs, T et C inchangés (lu dans `latents_etats.py`, l. 319) | |
| | | écarts T + 0,155 et C + 0,042, refaits depuis les T et C du juge 1 : 0,15521 et 0,04158 | |
| M9 | « 25 experts premiers distincts » | barré dans `REPRISE-figures-latents.md`, avec la correction (27) | **levé** |
| M10 | « règle déclarée » | F et sa règle disparaissent avec les ellipses agrandies ; le seul « déclaré » restant (III-7.6) est antérieur (47b96c2) | **levé** |

La barre de M2 dans `REPRISE-figures-latents.md` (« dessinent les frontières ») est juste. Elle donne 0,51 / 0,54 /
0,51 pour z(4) − z(5) et 0,67 contre 0,43 pour z(1) − z(2), égaux à mes bords refaits (§ 3.1).

## 3. Les nombres neufs ou déplacés

### 3.1 III-7.6 (`juge2_etats.py`, sortie `journaux/juge2-etats.json`)

Mes sources :
- les logits z = W h + b, relus dans `h-L23.f32` et dans `blk.23.ffn_gate_inp.{weight,bias}` du GGUF (forme 32 × 2 880) ;
- les coordonnées commitées de l'ACP et de la t-SNE.

Les logits redonnent le CSV du lot : expert premier égal pour les 6 132 états ; z(1) − z(2) à 4,8e-10 relatif près ;
z(4) − z(5) à 5,0e-10.

| Nombre écrit | Lot | Juge | |
|---|---|---|---|
| 10e centile, médiane de z(1) − z(2) | 0,0155 ; 0,097 | 0,0154714 ; 0,0966736 (interpolation linéaire écrite ici) | = |
| états sous le 10e centile | 614 | 614 (classes 614 / 2 452 / 3 066) | = |
| bord dans le plan t-SNE : petite marge, au-delà de la médiane (et entre les deux, non écrit) | 0,70 ; 0,47 (0,63) | 0,69984 ; 0,47378 (0,62688) ; arbre k-d de scipy, 10 voisins | = |
| bord dans l'espace d'origine, z(1) − z(2) (cité du juge 1) | 0,67 ; 0,43 | 0,67345 ; 0,42717 ; refait en 2 880 dimensions, par blocs | = |
| bord, z(4) − z(5), petite marge (cité du juge 1) | 0,51 | 0,50896 (puis 0,53801 et 0,50587) | = |
| Spearman marge contre bord, origine (macro non imprimée) | −0,34 | −0,34371 | = |
| gains de la t-SNE sur l'ACP, T et C | 0,155 ; 0,042 | 0,15521 ; 0,04158 | = |
| huit experts et parts ; part des huit ; autres | 12 (22,0 %) … 27 (4,4 %) ; 80,5 % ; 19 | idem depuis mes logits ; 80,545 % ; 27 − 8 | = |
| hasard (somme des carrés des parts) | 12,2 % | 12,156 % | = |
| 30 voisins, 10 voisins, 9 voisins (cassure) | 30 ; 10 ; 9 | constantes du script, égales à l'usage | = |

Les noms des experts. Le lot pose chaque nom sur son **ancre** : l'état du groupe dont la moyenne des distances à
ses 30 plus proches voisins du même groupe est minimale.
- Mes ancres sont égales à celles du CSV, à 0 près.
- Dans l'ACP, les boîtes des noms (10 % × 7,5 % de l'étendue) se recouvrent pour **quatre paires**, pas deux comme
  le dit le retour du lot : 24-13, 24-4, 31-27, 13-4.
- Après l'écartement, plus aucune paire ne se recouvre. Cinq noms sont déplacés, de 1,2 à 3,8 % de l'étendue.
- Dans la t-SNE, aucun recouvrement.
- La **pureté** autour de chaque ancre (part, parmi ses 30 plus proches voisins, des états du même expert) est
  basse dans l'ACP : 0,23 (23), 0,20 (21), 0,10 (13), 0,07 (4), 0,20 (27). Voir N3.

### 3.2 III-9.1 (d) (`juge2_nuage_rangee.py`, clé `rangee`)

- Les 32 lignes de `latents-rangee.csv` sont égales à la source (code, valeur exacte, ±c_k des deux bases, notation
  « ±k », changement). Pour cela, j'ai décodé l'expert 0 de `blk.8.ffn_gate_exps.weight` ; ligne 2 118, bloc 52,
  E8M0 = 118, donc s_b = 2⁻⁹.
- Les niveaux ±c_k du CSV sont égaux aux centres des `.sym` ÷ 2 ; les centres sont les mêmes pour les deux bases.
- Erreur du bloc en s_b² : 7,3902 et 11,2683 (déjà refaite par le juge 1).
- **La phrase de tête** : « change 4 des 32 symboles … et éloigne ces poids de leur valeur exacte ». Les quatre
  changements :

| j | code | exact | frontière | synonyme | distance à l'exact (frontière → synonyme) |
|---|---|---|---|---|---|
| 7 | 9 | −0,5 | −c₀ = −0,237 | −c₁ = −1,424 | 0,263 → 0,924 |
| 11 | 8 (−0) | −0 | −c₀ | **+c₀** | **0,237 → 0,237** |
| 15 | 1 | +0,5 | +c₀ | +c₁ | 0,263 → 0,924 |
| 26 | 5 | +3 | +c₂ = 3,419 | +c₁ | 0,419 → 1,576 |

Trois poids s'éloignent ; le quatrième (le zéro négatif) change de signe à la même distance : N1.

### 3.3 III-9.7 (`juge2_nuage_rangee.py`, clés `entrees`, `e_k`, `appui`, `rose`, `cone`, `barres`)

Mon chemin part de la source, pas des ellipses du lot :
- les entrées de l'expert 0 sont relues dans `routage-L08.bin` (1 329 positions, égales à celles du CSV) ;
- H = Σ g² x xᵀ / Σ g², puis ses axes propres, orientés pour que la moyenne de u_kᵀx soit positive ;
- ΔW = W − Ŵ pour les deux bases ; M = Bᵀ ΔWᵀ ΔW B pour chaque plan.

| Contrôle | Résultat |
|---|---|
| λ₁, λ₂, λ₃ ; trace | 279,452 ; 33,507 ; 21,733 ; 1 188,774 : égaux au JSON à 1,6e-15 ; 100 premières valeurs propres égales au spectre du lot B à 3,6e-10 ; rang de H : 1 329 |
| coordonnées c₁, c₂, c₃ des 1 329 entrées | égales au CSV commité à 5,0e-7 (six décimales) |
| e_k des deux bases | égaux au JSON à 3,4e-15 |
| M (depuis ΔW) contre M (moments d'ordre deux des 180 points distincts de chaque ellipse commitée, M = 2 · moyenne(p pᵀ) / F²) | 2,3e-9 à 5,7e-8 relatif : un second estimateur, indépendant des moindres carrés du lot (témoin A1) |
| h(θ) des quatre CSV `latents-appui-*`, 361 angles chacun | 4,3e-6 (frontière) et 5,0e-5 (synonyme) relatif ; c'est l'arrondi à six décimales d'un h de 0,0095 à 0,032 ; x et y à 5,0e-7 |
| rose : comptes par tranche de 3° | égaux pour les 27 tranches non vides du plan (u1, u2) et les 25 du plan (u1, u3) ; 1 329 entrées comptées |
| anneau de la rose | r₀ = 0,0430 > synonyme max 0,0318 ; fin 0,0982 < frontière min 0,1156 : la rose est bien entre les deux courbes |

| Nombre écrit | Lot | Juge | |
|---|---|---|---|
| cône à 90 % autour de u1, plans (a) et (b) | ±30° ; ±24° | 29,56° ; 24,14° (89,99 % des entrées dedans) | = |
| rapport maximal dans le cône, (a), (b), tête | 0,133 ; 0,135 ; 0,135 | 0,13316 ; 0,13543 ; 0,13543 | = |
| rapports le long de u1, u2, u3 (barres) | 0,082 ; 0,217 ; 0,269 | 0,08203 ; 0,21702 ; 0,26926 (CSV à 2,3e-7) | = |
| frontière le long de u1, u2, u3 | 0,116 ; 0,119 ; 0,118 | 0,11608 ; 0,11931 ; 0,11815 | = |
| synonyme (macros non imprimées) | 0,0095 ; 0,0259 ; 0,0318 | 0,00952 ; 0,02589 ; 0,03181 | = |
| écart-type le long de u2 ; 16,5² | 5,98 ; 272 | 5,9775 ; 272,02 | = |
| λ_k sous les barres | 279,5 ; 33,5 ; 21,7 | (ci-dessus) | = |
| 181 points, 3°, 90 %, 1 % (cassure) | — | constantes et comptes, égaux à l'usage | = |

Tous les nombres de III-9.7 sont justes. Ce qui tombe, c'est ce que la tête leur fait dire (§ 5).

## 4. Régénération et points tirés

**Régénération** (`journaux/juge2-regen.json`) :
- 24 fichiers sur 24 sont égaux au bit : les 4 `appui`, `barres`, `chiffres.tex`, `etats-acp`, `etats-reperes`, les
  8 `etats-tsne-gk`, `etats-tsne`, les 4 `rangee*`, les 2 `rose` et `temoins.json`.
- Aucun fichier en trop : les six retirés par le lot ne reviennent pas.
- `--casse-appui` : A1 tombe (0,0197), B1 tient. `--casse-bord` : B1 tombe (0,0087), A1 tient. Aucun fichier des
  données ne change ; les deux dossiers jetables sont restés dans mon brouillon.
- Comparateur cassé (`journaux/juge2-regen-casse.json`) : les 24 comparaisons tombent.

**Points tirés** (graine 2710202602, contrôlés à la source) :
- **III-7.6.** Pour chacune des dix séries neuves, l'état tiré a la place, l'expert premier et la classe de marge
  de la source. Les dix séries sont `etats-acp`, `etats-tsne` et `tsne-g1` à `tsne-g8`. Exemples :
  - ACP, ligne 2 126 : position 2 354, expert 6, « autres », marge 0,0588, « autre » ;
  - t-SNE g2, ligne 1 126 : position 211, expert 24, marge 0,0119 < 0,0155, « petite ».

  En plus, **toutes les lignes** sont contrôlées :
  - 6 132 états distincts par carte, 0 ligne fausse, les « petite » en dernier ;
  - les huit CSV `tsne-gk` ont l'effectif de leur expert (1 349 … 271), et seulement lui.
- **III-9.1 (d).** j = 11 tiré : code 8, frontière −0, synonyme +0, égal au CSV. Les 32 lignes sont contrôlées.
- **III-9.7.** Un angle par courbe :

  | Courbe | θ | h du CSV | h refait |
  |---|---|---|---|
  | frontière, plan 12 | 280° | 0,118967 | 0,1189669 |
  | frontière, plan 13 | 219° | 0,118045 | 0,1180452 |
  | synonyme, plan 12 | 316° | 0,019482 | 0,0194824 |
  | synonyme, plan 13 | 153° | 0,016503 | 0,0165025 |

  Les 361 angles de chaque courbe, toutes les tranches de la rose et les trois barres sont aussi contrôlés.

## 5. Le grave neuf

**GN1. III-9.7 : la tête et le cône parlent des projections des entrées comme des entrées.**

Ce que la légende écrit :
- la tête : « Là où pointent les entrées de l'expert, le synonyme ramène l'erreur de sortie à au plus 0,135 de
  celle de la frontière ; loin d'elles, le rapport monte » ;
- le corps : « 90 % sont à moins de ±30° de u1 dans (a) … dans ce cône, l'erreur du synonyme vaut au plus 0,133
  (a) et 0,135 (b) » ;
- l'erreur de sortie y est ‖ΔW x‖, définie par la légende elle-même.

Ce que mesurent les entrées réelles, dans leurs 2 880 dimensions (`entrees_reelles` du journal) :

| Grandeur | Valeur |
|---|---|
| rapport ‖ΔW_s x‖ / ‖ΔW_f x‖, entrée par entrée | min 0,491 ; 10e centile 0,557 ; **médiane 0,610** ; 90e centile 0,698 ; max 0,808 |
| entrées sous 0,135 | **0 sur 1 329** |
| rapport quadratique pondéré par g² | 0,6107 ; le même depuis le spectre commité du lot B : √(6,155 / 16,503) = 0,6107 (écart 1,5e-11). C'est le « ÷ 2,7 » que la légende de III-9.1 (d) écrit elle-même. |
| angle entre une entrée et u1 (médiane) | **61°**, pas ±30° |
| angle entre une entrée et le plan (u1, u2) | min 42°, médiane 59° |
| part de ‖x‖² dans le plan (u1, u2) ; dans (u1, u2, u3) | 26 % ; 28,2 % (pondéré) |
| projections sur le plan (u1, u2) : rapport | médiane 0,101, max 0,158 ; 93 % sous 0,135 |

**Ce qui est vrai :**
- dans chaque plan, pour une entrée **unité** de direction v, ‖ΔW v‖ suit les courbes ;
- les **projections** des entrées sur un plan tombent, à 90 %, dans le cône de ±30° (ou ±24°), où le rapport est au
  plus 0,135.

**Ce qui est faux :** le lecteur lit « les entrées », « où pointent les entrées », « l'erreur de sortie ». Il en
conclut que, pour les entrées de l'expert, le synonyme divise l'erreur de sortie par 7,4 au moins. Il la divise par
1,6 en norme (2,7 en carré). Les entrées pointent à 59° en médiane hors du plan dessiné : 72 % de leur norme au
carré est hors des trois axes.

**Aggravant.** La phrase « Non montrés : les 2 877 autres directions, où le synonyme met l'erreur qu'il retire
ici (panneau (b) de III-9.1) » vient du premier flux ; le juge 1 ne l'avait pas relevée.
- Elle est vraie de l'**erreur sur les poids**, qui est l'objet du panneau (b). Le long de u1 à u3, cette énergie
  passe de 0,0417 à 0,0018 ; au total, elle passe de 40,07 à 48,01.
- Elle est fausse de l'**erreur de sortie**, que la figure mesure désormais en tête. L'erreur de calibration
  pondérée baisse aussi dans les autres directions : de 11,96 à 6,08. Le long de u1 à u3, elle baisse de 4,55
  à 0,07.
- Les autres directions portent donc 57 % du gain de sortie (5,87 sur 10,35). La figure, telle qu'écrite, laisse
  croire l'inverse.

**Pourquoi c'est grave.** C'est la phrase de tête : l'idée de la figure, la seule que retient un lecteur pressé.
Elle prête au mécanisme (le synonyme suit H) un effet 4,5 fois plus fort que celui que les entrées reçoivent
(÷ 7,4 au moins, contre ÷ 1,6). C'est le défaut de M8 du juge 1 (l'œil lit l'inverse), en plus fort. Les nombres,
eux, sont tous justes.

**Correction proposée** (au lot ; je ne l'ai pas faite) :
1. **La tête.** Dire le plan et dire le vrai rapport des entrées. Par exemple : « Dans les plans des premiers axes
   de H, où se projettent ses entrées, le synonyme ramène l'erreur de sortie à au plus 0,135 de celle de la
   frontière ; sur les entrées entières, dont 72 % de la norme au carré est hors de ces trois axes, à 0,61. »
2. **Le corps.** Écrire « les directions projetées des entrées » pour la rose et le cône. Écrire « l'erreur sur
   les poids » dans la phrase « Non montrés ».
3. **Les nombres.** Ils se tirent de fichiers commités, aucun n'est tapé :
   - 0,61 = √(Σλe_s / Σλe_f), depuis `spectre-L08-E00-gate.csv` (le script le lit déjà) ;
   - 72 % = 1 − `part_trace_3_axes`, depuis `nuage-L08-E00-gate.json` ;
   - la plage 0,49 à 0,81 et la médiane, depuis mon journal `juge2-nuage-rangee.json` si l'on veut les écrire. Le
     lot cite déjà un JSON de juge de cette façon : `juge-etats-marges.json`.
4. **Le dessin** peut rester : il est juste et beau. Une ligne de la clé suffirait : « directions projetées ;
   angle médian d'une entrée au plan : 59° ».

## 6. Les mineurs neufs

- **N1. III-9.1 (d), la tête : « éloigne ces poids de leur valeur exacte » est faux pour un des quatre.** En j = 11,
  le code 8 (−0) passe de −c₀ à +c₀, à 0,237 de l'exact des deux côtés (§ 3.2) ; les trois autres s'éloignent. Il
  faudrait dire : « en éloigne trois de leur valeur exacte (le quatrième, un zéro, change de signe) ». Le nombre
  (3) serait à tirer du CSV par le script.
- **N2. III-9.1 (d) : la lettre (d) repose sur une prémisse fausse.** Le lot écrit qu'il prend (d) « parce que le
  lot synonyme a déjà un (c), la part cumulée ». Or `3275a6c` (11 h 30) l'avait déjà renommée (b′) « pour laisser
  la lettre (c) » au lot latents, avant `326969f` (12 h 20).
  - Assemblée, la figure aurait (a), (b), (b′), (d). La légende de la rangée renverrait aux « panneaux (a) à
    (c) », qui n'existent pas.
  - Je rejoins N12 du juge construction du second flux. Ici, la solution la plus simple est que la rangée reprenne
    (c) et écrive « panneaux (a), (b) et (b′) ».
- **N3. III-7.6 : « l'état du groupe le plus entouré des siens » dit la pureté, la règle mesure la densité.** Aux
  ancres de l'ACP, 7 à 23 % seulement des 30 plus proches voisins sont du même expert, pour 23, 21, 13, 4 et 27.
  Dans la t-SNE, 17 % pour 13. Sur une carte grise, le nom désigne une région où l'expert est minoritaire. Trois
  sorties :
  - écrire « là où ses états sont le plus serrés » ;
  - ne nommer que dans (b) ;
  - choisir l'ancre par la pureté.

  De plus, « avec un trait de rappel s'ils en sont écartés » décrit un trait qu'on ne voit pas. Les cinq noms
  déplacés le sont de 1,2 à 3,8 % de l'étendue, soit 0,5 à 1,6 mm. Le trait reste sous la boîte du nom (10 % ×
  7,5 % de l'étendue).
- **N4. III-7.6 : la tête dit une tendance comme un fait, et le dessin ne la montre pas.**
  - Ce qui est mesuré : bord 0,70 contre 0,47 ; Spearman marge-bord −0,34 dans l'espace d'origine (refait ici) et
    −0,31 dans le plan (juge 1).
    Les états de petite marge ont plus de voisins d'un autre expert ; ils ne « se tiennent » pas tous sur les bords.
  - Dans (a) et (b), les groupes ne sont pas dessinés.
  - Dans (c), une part des points noirs est au cœur des nuées : l'expert 12 en a un amas au centre bas.
  - Proposition : « se tiennent plus souvent aux bords des groupes (0,70 de voisins d'un autre expert, contre
    0,47) ».
- **N5. III-9.1 (d) : en j = 11, la flèche ne se voit pas.** Elle mesure 0,47 s_b, raccourcie de 2,4 pt et de
  1,6 pt : agrandi à 800 dpi, il n'en reste rien entre le losange et le rond. La légende dit qu'« une flèche va … là
  où le symbole change ». Il faut une flèche plus courte en tête, ou la dire absente pour ±c₀.
- **N6. III-7.6 : la clé « un état » est en `black!30`, le fond de (c) en `black!12`** (`CouleurAutres`). Dans (c),
  un état d'un autre expert n'a pas la couleur de la clé. Deux pastilles, ou une note.
- **N7. III-7.6 : « ne les marque pas (0,51) »** donne un nombre sans son terme de comparaison. Il faudrait :
  « 0,51 sous le 10e centile comme au-delà de la médiane ». Les deux valeurs sont déjà dans le JSON du juge 1, que
  le script lit.
- **N8. Le retour et la note du lot** disent que, dans l'ACP, « 24 et 4, ainsi que 31 et 27, se cachaient ». Il y
  avait quatre paires (§ 3.1). Sans effet sur la figure.
- **N9. `tome3_latents.py`, l. 70** : le commentaire « # degrés par tranche de la rose », qui appartient à
  `PAS_ROSE`, a glissé sur la ligne de `MARGE`. Cosmétique ; la sortie est au bit.

## 7. Hors du lot

- **MiKTeX 26.2 → 26.5 (2026-10-27, vers 12 h 22).**
  - La trace : `mpmcli.log` (« this is mpmcli 4.5 (MiKTeX 26.5) », 12:22:18) ; les journaux des pilotes de 12 h 15
    et 12 h 19 disent encore 26.2.
  - L'effet : LaTeX 2026-06-01 avec thmtools 0.76 (2023/05/04) lève « Command \c@proposition already defined »
    (puis lemme, corollaire, definition, hypothese, remarque) aux lignes 190 à 195 de `memoire/commun/preambule.tex`.
  - La cause est isolée : un document de neuf lignes (scrbook, amsthm, thmtools, trois `\declaretheorem` à
    compteur partagé) suffit à reproduire l'erreur ; sans thmtools, amsthm passe.
  - La conséquence : **tout pilote et tout le mémoire** compilent désormais avec six erreurs, et un
    `-halt-on-error` s'arrête dans le préambule.
  - Ce n'est ni au lot ni au juge. À l'orchestrateur : remplacer `sibling=` par une déclaration qui passe, ou fixer
    la version, au choix de Stone. Ce n'est pas un geste que je fais sur sa machine.
- **Le PDF français du pilote du lot, effacé par moi.**
  - Une compilation de contrôle (`lualatex -halt-on-error -output-directory=<brouillon>`, lancée dans
    `memoire/essai/`) s'est arrêtée sur l'erreur ci-dessus. Elle a effacé `memoire/essai/pilote-tome3-latents.pdf`.
  - LuaTeX efface le PDF du nom du travail dans le dossier courant, malgré `-output-directory`. Je l'ai vérifié
    ensuite sur un faux PDF, dans mon brouillon.
  - Le fichier est ignoré par git et se refait. Je l'ai remplacé par le PDF français que j'ai compilé sur les
    sources du commit (§ 8). Les PDF anglais, les `.log` et les `.aux` du lot n'ont pas bougé.
- **La note pour le mémoire de la construction** (`genome/construction-codon-pour-le-memoire.md`, R1). Elle n'est
  pas de ce lot. Le juge construction du second flux l'a jugée (`01902b6` : « barre de la note pour le mémoire
  juste »). Je n'y ai rien refait.

## 8. Compilation et pages lues

- **Comment** : `juge2_compiler.py` (`journaux/compilation.json`). Le pilote du lot tourne sur les sources du commit
  `326969f`, tirées par `git archive`. Chaque langue fait deux passes ; le journal n'en demande pas de troisième.
- **Résultat, en français comme en anglais** :
  - 6 pages ;
  - **0 erreur hors du préambule commun**, et 6 erreurs dedans (thmtools, § 7) ;
  - 0 boîte trop pleine, 0 référence indéfinie, 0 « Float too large » ;
  - 2 boîtes trop creuses, dans les lignes « Données » de III-7.6 et de III-9.1 (d), à cause des longs chemins de
    fichiers. Les journaux du lot, compilés sous MiKTeX 26.2 à 12 h 15 et 12 h 19, en ont autant, avec 0 erreur.
  - La table des figures porte les trois titres courts.
- **Pages lues** : en français, les pages 3 à 6 à 100 dpi, puis les panneaux à 250, 300 et 800 dpi ; en anglais, les
  pages 4 à 6 à 100 dpi. Les nombres imprimés (texte des pages par `pdftotext`) sont ceux du § 3.
- **Typographie anglaise (D30)** : « 22.0% », « 13.1% of the variance », deux-points et point-virgule sans espace.
  Aucune typographie française ne survit.
- **Les deux langues** disent la même chose. La tête anglaise de III-9.7 porte le même défaut (GN1) : « Where the
  expert's inputs point, … at most 0.135 ».
- **III-7.6**, ce que j'ai vu :
  - les huit cartes de (c) se lisent d'un coup d'œil : 31 en une nuée, 13 dispersé partout, 12 et 24 étalés et
    mêlés ;
  - le noir des petites marges se sépare du bleu et du gris, en couleur comme en luminance ;
  - dans (a), les noms 4, 24 et 13 sont serrés mais lisibles ;
  - les traits de rappel ne se voient pas : déplacements de 0,5 à 1,6 mm, sous la boîte du nom (environ 4 × 3 mm),
    voir N3.
- **III-9.1 (d)** :
  - le losange gris sort sous le rond bleu là où rien ne change (agrandi à 800 dpi) ;
  - les trois flèches de 7, 15 et 26 se voient ; celle de 11, non (N5).
- **III-9.7** :
  - la rose est entre les deux courbes, la frontière est presque un cercle, la graduation est sur le demi-axe bas ;
  - en anglais, la clé ne chevauche plus les λ_k de (c).
  - Le dessin est juste et beau. Il est lu de travers par sa tête (GN1).

## 9. Phrases barrées et règles

- `juge2_barrees.py` (`journaux/barrees.json`) a lu 238 passages barrés dans 188 documents. Deux recoupent le texte
  des légendes, et aucun n'est un retour :
  - un faux positif : le « `~~` » que le juge 1 cite dans sa méthode, lu comme une barre ;
  - « les états de petite marge » : la phrase barrée (« dessinent les frontières ») portait sur z(4) − z(5). La
    tête neuve porte sur z(1) − z(2), mesurée (0,70 contre 0,47 ; 0,67 contre 0,43), comme la barre le dit
    elle-même. C'est sa correction, pas son retour. Voir N4 pour le ton.
- Témoin : une phrase barrée glissée dans les légendes, tirée par la graine (`genome/08-placement-disque.md`), est
  trouvée (`journaux/barrees-casse.json`).
- R1 à R4 : III-7.6, III-9.1 (d) et III-9.7 ne portent ni vitesse, ni KL de protocole, ni S\*. R3 : les nombres de
  sortie (÷ 2,7 ; ÷ 1,57) sont ceux d'une seule matrice, et la légende le dit.
- Les règles du flux :
  - chaque nombre écrit est une macro de `latents-chiffres.tex`, ce que j'ai vérifié en comparant chaque macro à
    mon calcul ;
  - seules les graduations sont tapées ;
  - les cassures écrivent dans un dossier jetable ;
  - aucune mesure sous `mesures/` n'est touchée : `git show --stat 326969f` ne contient aucun chemin `mesures/`.

## 10. Ce qui pourrait être faux

- **GN1 dépend d'une lecture**, la plus naturelle à mon sens : « les entrées », ce sont les vecteurs d'entrée
  eux-mêmes. Si la rédaction entend « les directions des entrées dans ces plans », la tête est vraie, mais elle doit
  le dire : sans le mot, le lecteur lit l'autre sens, et l'autre sens est faux d'un facteur 4,5.
- **Mes lecteurs sont neufs, mes entrées ne le sont pas.** Je relis le même GGUF, les mêmes `.sym` et les mêmes
  captures que le lot et que le juge 1 : une capture fausse à la source tromperait les trois. Ce risque est borné,
  sans être annulé, par :
  - le témoin d'énergie contre le spectre du lot B ;
  - λ et e_k égaux au JSON à 1e-15 ;
  - le rapport pondéré égal au spectre à 1e-11.
- **Les ellipses commitées sont le seul chemin du lot vers M.** Je l'ai refait depuis ΔW. L'accord (≤ 6e-8) dit que
  les ellipses sont justes, pas que la fonction d'appui était le bon objet ; ce dernier point est un choix de
  dessin, jugé au § 5.
- **Les bords** se mesurent par les 10 voisins, comme le fait le juge 1 ; je n'ai pas essayé d'autre définition.
  Ma version de l'espace d'origine redonne les siens au dernier chiffre, avec le même k et la même distance : ce
  n'est pas une seconde définition.
- **La pureté des ancres (N3)** est une mesure à 30 voisins que j'ai choisie. Avec une autre taille de voisinage,
  les nombres bougent ; le constat (dans l'ACP, les noms 13 et 4 tombent où leur expert est rare) devrait rester.
- **La lecture des pages** se fait à l'écran, à 100, 250, 300 et 800 dpi, et sous MiKTeX 26.5, avec les six erreurs
  du préambule. Les figures n'emploient pas de théorème. Les journaux du lot, compilés sous 26.2, ont 0 erreur et les
  mêmes deux boîtes trop creuses que les miens : le rendu des figures ne dépend pas de la version.
- **Le témoin de mes comparateurs** ne fait tomber qu'une partie des nombres (24 sur 29, 17 sur 35). Une erreur de
  1 % ne change pas l'arrondi d'un petit entier (10, 30, 90) : le témoin n'exerce donc pas ces comparaisons. Elles
  se font pourtant à égalité exacte, et les comptes, effectifs et lignes sont aussi comparés exactement dans les
  journaux.

## 11. Reproduire

```
cd outils/genome/tome3/juge2-latents
python -I -X utf8 juge2_regen.py <brouillon> > journaux/juge2-regen.json                      # ~15 s
python -I -X utf8 juge2_regen.py <brouillon> --casser > journaux/juge2-regen-casse.json
python -I -X utf8 juge2_nuage_rangee.py > journaux/juge2-nuage-rangee.json                    # ~10 s, < 1,5 Go
python -I -X utf8 juge2_nuage_rangee.py --casser > journaux/juge2-nuage-rangee-casse.json
python -I -X utf8 juge2_etats.py > journaux/juge2-etats.json                                  # ~40 s, < 1 Go
python -I -X utf8 juge2_etats.py --casser > journaux/juge2-etats-casse.json
python -I -X utf8 juge2_barrees.py > journaux/barrees.json
python -I -X utf8 juge2_barrees.py --casser > journaux/barrees-casse.json
python -I -X utf8 juge2_compiler.py <brouillon> > journaux/compilation.json                   # ~12 min
```
