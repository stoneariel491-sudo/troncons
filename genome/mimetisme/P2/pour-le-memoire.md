# P2, cache exclusif VRAM vers RAM : ce qu'il faut au mémoire (dérivations, données, figures)

Pour le rédacteur du Tome (chapitre « théorie du cache »). Rien ici n'est écrit de mémoire : chaque
chiffre vient d'un CSV de `mesures/mimetisme/P2/`, chaque figure d'un script de `outils/mimetisme/P2/`.
D'où on part : le cache d'experts de `trc-cache` est inclusif (la RAM est remplie à chaque défaut disque).
Ce que l'étape établit : le théorème 1 (l'exclusif vaut un LRU de capacité V + R), la mesure de ce qu'il
rend sur le 120b, et le coût de la descente. Ce qui reste : le recouvrement de la descente dans le moteur.

## 1. Notation

- Un accès est un expert `x` (identifiant global couche × 128 + expert). Un groupe est l'ensemble des 4
  experts d'une couche pour un jeton ; ses 4 membres ne sont jamais victimes pendant le groupe.
- Pile LRU : liste des experts déjà vus, du plus récent (rang 1) au plus ancien. La **distance de pile**
  d'un accès à `x` est le rang de `x` dans la pile juste avant l'accès (infinie au premier accès).
- `F(C)` = part des accès dont la distance de pile est ≤ C.

## 2. Lemme 1 (Mattson, Gecsei, Slutz, Traiger 1970 [mém., à relire à la source avant publication])

Un cache LRU de capacité C contient, à tout instant, les C premiers éléments de la pile LRU. Un accès
est un succès si et seulement si sa distance de pile est ≤ C. Donc le succès d'un LRU de capacité C est
`F(C)` (hors épinglage des groupes, qui ne retire que des victimes du groupe en cours).

## 3. Théorème 1 : l'exclusif à deux étages vaut un LRU de capacité V + R

Énoncé. Étage VRAM de capacité V, étage RAM de capacité R, politique LRU aux deux étages ; sur un
défaut VRAM, la victime VRAM descend en tête de la RAM ; si l'expert demandé est en RAM, il monte et
quitte la RAM ; si la RAM déborde, son plus ancien disparaît. Alors, à tout instant, VRAM = rangs
1..V de la pile, RAM = rangs V+1..V+R, et le succès total (VRAM + RAM) est `F(V + R)`.

Preuve par récurrence sur les accès. Vrai pour la pile vide. Soit un accès à `x` de rang `d`.
- `d ≤ V` : `x` va en tête, les rangs 1..d−1 glissent d'un cran ; l'ensemble des rangs 1..V est inchangé,
  la RAM aussi. Succès VRAM.
- `V < d ≤ V + R` : `x` est en RAM. Il monte et quitte la RAM. Le rang V devient V+1 : c'est la victime
  VRAM (le plus ancien de la VRAM) ; elle entre en tête de la RAM, c'est bien le rang V+1. Les rangs
  V+1..d−1 de l'ancienne pile glissent de V+2 à d, et les rangs au-delà de d sont inchangés : la RAM est
  exactement les rangs V+1..V+R de la nouvelle pile. Succès RAM.
- `d > V + R` ou premier accès : `x` va en tête, la victime VRAM (rang V) devient rang V+1 et entre en
  tête de RAM ; la RAM déborde d'un élément, son plus ancien, qui est le rang V+R+1 de la nouvelle
  pile : il sort. Les rangs 1..V+R sont ceux de la nouvelle pile. Défaut disque. ∎

Corollaire. Part servie par la RAM = `F(V + R) − F(V)` ; part disque = `1 − F(V + R)`. Le gain de
l'exclusif est la masse des distances de pile comprises dans la bande `(V, V + R]` : c'est l'aire
hachurée de la figure 1.

Avec l'épinglage, la victime est la plus ancienne **hors groupe** et non le rang V : l'égalité n'est
plus exacte. Mesure (témoin T2, 7 traces, R = 80 et 336) : l'écart au LRU de capacité V + R ne dépasse
pas 7e-4 (observé : 6,6e-4 au maximum). Sur le 20b, sans épinglage, l'écart est exactement 0 sur trois traces
(`holdout20b-t2-sans-epinglage.json`) : le théorème est exact, l'écart restant vient de la règle de groupe.

## 4. Lemme 2 : pourquoi l'inclusif de `trc-cache` n'ajoute rien tant que R ≤ V (esquisse)

Dans l'inclusif, la RAM est remplie à chaque défaut disque et rafraîchie à chaque accès à une entrée
qu'elle contient. Tout expert récemment lu est donc déjà en VRAM : la RAM contient des doublons de la
VRAM. Elle ne sert que si une de ses entrées est évincée de la VRAM sans l'être de la RAM, c'est-à-dire
si son rang de pile dépasse V alors qu'elle est encore parmi les R dernières entrées insérées. Pour
R ≤ V cela n'arrive qu'aux bords (épinglage, entrées jamais rafraîchies) : le succès RAM mesuré est 0 à
R = 80 et 160 sur les 7 traces et au plus 7,7e-4 à R = V = 326 (`t1bord.csv`). C'est une esquisse, pas
une preuve : la mesure en tient lieu ; on ne l'écrit pas « théorème ».
Au-delà (R > V) l'inclusif sert : le succès RAM vaut 0,0048 (prose-en gen., R = 336), 0,0791 (R = 672) ;
mais l'exclusif, à R égal, rend toujours plus (théorème 1 : il met R places *utiles* au lieu de doublons).

## 5. Modèle de coût et seuil de rentabilité (calcul posé)

Données du tri : un défaut disque coûte `a = 4,1` ms (11,6 Mo à 2,82 Go/s) ; un défaut servi par la RAM
décodée coûte `b = 1,09` ms (13,25 Mo à 12,2 Go/s) ; une descente VRAM vers RAM coûte `b` aussi.
Soit `φ` le nombre de défauts VRAM par jeton, `ρ` la part de ces défauts servie par la RAM.
Chaque défaut VRAM provoque une descente (sauf pendant le remplissage initial). Par jeton :

- LRU seul : `φ · a`.
- Exclusif, tout en série : `φ · [ (1 − ρ) a + ρ b + b ]`.
- Exclusif, descente entièrement recouverte : `φ · [ (1 − ρ) a + ρ b ]`.

Gain en série : `φ · [ ρ (a − b) − b ]`, positif si et seulement si `ρ > b / (a − b) = 1,09 / 3,01 = 0,362`.
Avec une fraction ω de la descente recouverte, le seuil de rentabilité est `ρ (a − b) ≥ (1 − ω) b`,
soit `ω ≥ 1 − ρ (a − b) / b`. Application aux mesures de la section 6 de `resultat.md` : prose-en
génération, `ρ ≈ 0,30` (déficit en série, il faut recouvrir au moins ~15 % de la descente) ; wiki
génération, `ρ ≈ 0,52` (gain même en série).

## 6. Figures (déjà tirées des CSV)

- `figures/fig1-distances-de-pile.{pdf,png}` : `F(C)` sur les deux générations, bande `(V, V + R]`
  hachurée. Elle montre le théorème 1 : le gain est l'aire sous la courbe entre V et V + R. Sur
  prose-en la courbe est presque plate après V (gain 0,08) ; sur wiki elle monte fort entre V et V + R
  (gain 0,32) : l'ensemble de travail du wiki est à cheval sur la frontière.
- `figures/fig2-part-disque-contre-R.{pdf,png}` : part disque contre R, inclusif contre exclusif, deux
  générations, deux capacités. L'inclusif reste collé au LRU seul tant que R ≤ V puis décroche ; la courbe
  exclusive part dès R = 80.
- À tirer au moment de la mise en page (TikZ, non encore dessiné) : la machine à états d'un expert. En
  inclusif, trois états `{disque, VRAM seule, VRAM ∧ RAM}` ; en exclusif, trois états disjoints
  `{disque, VRAM, RAM}` avec les arcs « défaut disque », « descente », « montée » ; la différence se lit
  sur les arcs.
- Pour un chapitre « topologie » : la distance de pile est la bonne coordonnée de l'espace des accès ;
  l'histogramme des distances (dérivée de la figure 1) est l'empreinte de la localité de la génération.

## 6 bis. Variante sélective (post-hoc, à présenter comme telle)

Filtre d'admission sur la descente : la victime ne descend que si elle a été réutilisée au moins `s` fois
pendant son séjour en VRAM. Propriété exacte : `s = 0` est l'exclusif simple (témoin, égalité exacte) ;
`s` infini est le LRU seul (cassure, égalité exacte sur le 20b). Effet mesuré à `s = 1`, R = 336 : moitié moins
de descentes, gain en série positif sur les 7 traces du 120b (+17 à +65 ms par jeton). Résultat du test
aveugle sur le 20b : à V = 154, 5/5 sur la réduction et sur la part disque, 4/5 sur le trafic ; à V = 54
le régime est dégénéré (V plus petit que l'empreinte d'un jeton, 96 cellules) et le filtre ne descend rien.
Figure à tirer : plan (descentes par jeton, part disque) avec les points `s = 0, 1, 2, 3` en trajectoire
pour chaque trace (`explore-selectif.csv`) ; elle montre le compromis, et que `s = 1` est le coude.

## 7. Données à citer

`mesures/mimetisme/P2/` : `temoins.csv`, `t1bord.csv`, `grille.csv` (7 traces + agrégé de lecture, deux V,
cinq R, trois régimes), `chaine.csv` (invite puis réponse), `rust.csv` (second chemin), `verdict.json`,
`explore-distances.csv`, `explore-selectif.csv`, `holdout20b.csv`, `net-selectif-120b.csv`. Sources à mettre en BibTeX : Wong et Wilkes 2002 (page USENIX lue le 2026-10-27) ; Mattson,
Gecsei, Slutz, Traiger 1970 (marquées [mém.] tant que je ne les ai pas relues à la source).
