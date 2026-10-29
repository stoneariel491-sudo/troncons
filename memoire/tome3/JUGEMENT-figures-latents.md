# Jugement : figures du Tome III, lot « espaces latents » (III-7.6, III-9.1 (c), III-9.7)

Juge indépendant des chiffres, 2026-10-27. Je n'ai rien tracé. Demande de Stone : « prépare le Tome III :
l'inventaire des figures, puis un flux court avec un juge ». Règles : SOCLE (dont la demande du 2026-10-17,
« la beauté à égalité avec la justesse »), `memoire/tome3/INVENTAIRE-figures.md` (réserves R1 à R6).
Objet jugé : les commits 47b96c2 (seuil), 3ce3553 (III-9.1 (c), III-9.7), c4f3fe2 (III-7.6), fichiers
inchangés depuis sur `main`. Outils du juge : `outils/genome/tome3/juge-latents/` ; leurs sorties JSON
sont commitées à côté d'eux.

## 0. Verdict

**Les trois figures tiennent.** Chaque nombre écrit dans leurs légendes et annotations est retrouvé par un
chemin écrit de zéro (lecteur GGUF, décodeur MXFP4, lecteur .sym, ACP, confiance et continuité, Spearman,
accords, ellipses), sans avoir lu les scripts du lot avant de l'écrire ; les CSV du lot se régénèrent **au
bit** par ses scripts ; chaque série tracée est contrôlée à la source par des points tirés (graine du juge
27102026) ; les deux pilotes compilent, en français et en anglais, sans erreur ni boîte trop pleine, et
leurs pages ont été lues.

**Graves : 0. Mineurs : 10**, dont **un corrigé** par moi (mécanique : la cassure du témoin R0 de III-9.1 (c)
était dite « un écart d'un facteur 41 » ; 41 est l'écart relatif, le facteur est 42,4 ; § 7). Les neuf
autres sont rapportés sans correction. Le plus lourd pour la lecture (M2) : dans III-7.6, la taille des
points (marge z(4) − z(5)) ne marque pas les bords des nuées colorées (expert premier) ; je l'ai mesuré
(§ 2.1) ; la légende ne le prétend pas, mais la note de reprise du lot l'écrit, et l'œil le cherchera.

| Figure | Tient ou tombe | Pourquoi, en une ligne |
|---|---|---|
| III-7.6 | **tient** | 30 nombres refaits, tous égaux à l'arrondi ; CSV au bit ; fidélité des deux projections dite en légende (R de l'inventaire) |
| III-9.1 (c) | **tient** (un mot corrigé) | rangée, bloc, symboles, centres, erreurs refaits ; CSV au bit ; « facteur 41 » → « écart relatif de 41 » |
| III-9.7 | **tient** | λ, e_k, rapports, F, ellipses refaits ; chaque point des ellipses commitées est sur l'ellipse recalculée à 1e-6 ; CSV au bit |

## 1. Méthode

1. **Les nombres, par mon propre chemin.** J'ai lu SOCLE, l'inventaire, les notes F10 (synthèse) et
   F-S1, F-S6 (lot B), les JSON et CSV commités du lot, et `latents-figures.tex` (le produit jugé). Puis
   j'ai écrit `juge_commun.py` (GGUF v3 relu octet par octet, MXFP4, .sym, captures), `juge_etats.py`,
   `juge_rangee_nuage.py`, `juge_etats_marges.py`, **avant** d'ouvrir `outils/genome/tome3/latents_*.py`
   et `memoire/outils/tome3_latents.py`. Les définitions viennent des légendes, pas du code du lot
   (ex. : confiance T(k) et continuité C(k) de Venna et Kaski 2001, rangs comptés exactement ligne par
   ligne ; Spearman sur 2 000 000 paires tirées par ma graine, pas les 200 000 du lot).
2. **La régénération au bit.** `git archive c4f3fe2` des scripts du lot (et de leurs entrées commitées)
   dans une racine de brouillon, hors du dépôt : les scripts écrivent sous leur propre racine, aucun
   fichier de mesure commité n'est réécrit. Comparaison par `juge_regen.py` (SHA-256 des CSV et du .tex ;
   JSON champ par champ hors `duree_s`), avec son témoin `--casser`.
3. **Les points tirés.** Un point par série au moins, graine 27102026 écrite dans les outils, contrôlé
   à la source (capture h, journal de routage, GGUF, .sym), et, quand c'était possible, toutes les lignes.
4. **La compilation.** Le pilote du lot copié dans le brouillon, `lualatex` de MiKTeX deux passes en
   français et deux en anglais (`-jobname=...-en "\def\ANGLAIS{1}\input{...}"`) ; pages 4 à 6 lues dans
   les deux langues.
5. **Le faux et le trop beau.** R1 à R4, phrases barrées des sources (`~~` dans 05, 07, notes, juges),
   protocoles mêlés, échelles, fidélité des projections, encodages qui disent autre chose que la légende.

Mémoire : 6 132 × 2 880 en f64 et les distances par blocs de 256 lignes, jamais de matrice n × n ;
pointe sous 1 Go pour chaque outil du juge.

## 2. Figure par figure

### 2.1 III-7.6, l'espace latent des 6 132 états de la couche 23 — tient

Sources du juge : `h-L23.f32` et `routage-L23.bin` (éclaireur), `blk.23.ffn_gate_inp.weight` et `.bias`
relus dans le GGUF, coordonnées commitées de `etats-c23.csv`. Sortie : `juge-etats.json`.

| Nombre écrit (légende ou clé) | Lot | Juge | |
|---|---|---|---|
| états, dimensions | 6 132 ; 2 880 | 6 132 × 2 880 | = |
| huit experts premiers et parts | 12 (22,0), 24 (20,9), 31 (7,8), 23 (7,2), 21 (6,8), 13 (5,9), 4 (5,4), 27 (4,4) % | idem (argmax de z = W h + b) | = |
| part des huit ; autres en gris | 80,5 % ; 19 | 80,545 % ; 27 distincts − 8 = 19 | = |
| marge z(4) − z(5) : 10e centile ; médiane | 0,0072 ; 0,048 | 0,0071803 ; 0,047957 | = |
| ACP : CP1, CP2, plan | 13,1 ; 8,0 ; 21,0 % | 13,073 ; 7,958 ; 21,031 % | = |
| ACP : T(10), C(10) | 0,792 ; 0,917 | 0,79151 ; 0,91707 | = |
| ACP : Spearman des distances | 0,59 | 0,588 (autres paires) | = |
| t-SNE : T(10), C(10) | 0,947 ; 0,959 | 0,94672 ; 0,95866 (sur les coordonnées commitées) | = |
| t-SNE : Spearman | 0,41 | 0,410 | = |
| accord des 10 voisins : origine, ACP, t-SNE | 48,1 ; 28,7 ; 44,2 % | 48,097 ; 28,659 ; 44,237 % | = |
| accord au hasard | 12,2 % | Σ p² = 12,156 % ; deux états distincts : 12,142 % | = (M4) |
| W0 : ensembles du journal ; sans biais | 6 132 ; 3 482 | 6 132 ; 3 482 ; poids du journal à 2,8e-8 | = |
| W1 : plan permuté | T = 0,500 | ma permutation : T = 0,5005, C = 0,5028 | = |

Contrôles en plus : l'expert premier du CSV égale mon argmax pour les 6 132 états ; e1 à e4 du CSV égalent
l'ordre de mes logits pour les 6 132 ; marges du CSV à 5e-10 relatif ; coordonnées de l'ACP du CSV égales
aux miennes à 5e-7 (signes des deux axes opposés, conventions) ; les 6 132 lignes de chacun des deux CSV de
la figure (`latents-etats-acp.csv`, `-tsne.csv`) ont le bon groupe et la bonne taille, 614 / 2 452 / 3 066
par classe, gros points en dernier. La fenêtre 10 à 21 est celle de `capture.json` (`--de 10 --a 22`,
6 132 = 12 × 511). La légende dit la fidélité des deux plans (réserve de l'inventaire) et ce que la
t-SNE ne garde pas (« ses distances entre nuées et ses aires ne se lisent pas ») : c'est juste, la t-SNE
garde mieux les voisins (T 0,947) et moins les distances (Spearman 0,41 contre 0,59).

**Ce que dit la taille des points (mesuré par le juge, `juge_etats_marges.py`).** La couleur suit
l'expert premier, dont le bord est z(1) = z(2) ; la taille suit z(4) − z(5), le bord de l'ensemble des
quatre experts servis. Bord d'un état : part de ses 10 voisins dont l'expert premier diffère.

| Classe de marge | z(4) − z(5) : bord (origine ; t-SNE) | z(1) − z(2) : bord (origine ; t-SNE) |
|---|---|---|
| sous le 10e centile (gros points) | 0,509 ; 0,541 | 0,673 ; 0,700 |
| jusqu'à la médiane | 0,538 ; 0,580 | 0,595 ; 0,627 |
| au-delà | 0,506 ; 0,543 | 0,427 ; 0,474 |
| Spearman marge contre bord | −0,03 ; −0,04 | −0,34 ; −0,31 |

Les gros points de la figure ne sont pas plus au bord des nuées que les petits ; avec z(1) − z(2), ils le
seraient nettement. La légende ne prétend rien de tel (elle dit ce que la taille encode) : la figure
reste vraie. Mais la note F10 attendait que « les états de petite marge dessinent les frontières entre les
nuées », la note de reprise du lot l'écrit (« ce sont les états de petite marge qui “dessinent les
frontières” ») et l'œil le cherchera : voir M2.

### 2.2 III-9.1 (c), une rangée de 32 poids — tient (un mot corrigé)

Sources du juge : GGUF (`blk.8.ffn_gate_exps.weight`, expert 0), `.sym` du lot B (`frontiere`,
`synonyme-l1-d1`, L08-E00 et, pour la cassure, L08-E01), `spectre-L08-E00-gate.csv` du lot B. Sortie :
`juge-rangee-nuage.json`, clé `rangee`.

| Nombre écrit | Lot | Juge | |
|---|---|---|---|
| ligne, bloc, colonnes | 2 118 ; 52 ; 1 664 à 1 695 | le bloc a 4 changements, il est candidat | = |
| s_b | 2^−9 | E8M0 = 118, 2^(118 − 127) | = |
| c0, c1, c2, c3 | 0,237 ; 1,424 ; 3,419 ; 6,000 | en-tête des .sym ÷ 2 : 0,23717 ; 1,42430 ; 3,41858 ; 6 ; égaux pour les deux bases | = |
| « le symbole frontière est une fonction du code » | — | vrai sur les 8 294 400 poids : chacun des 16 codes a un seul symbole | = |
| candidats ; médiane ; moyenne ; part changée | 26 155 ; 4 ; 5,59 ; 17,5 % | 26 155 ; 4 ; 5,5926 ; 17,477 % (histogramme égal) | = |
| erreur du bloc, en s_b² | 11,27 contre 7,39 | 11,2683 ; 7,3902 | = |
| énergie de l'erreur | +20 % (40,07 → 48,01) | +19,80 % (40,0709 → 48,0056) | = |
| erreur de sortie, calibration | ÷2,7 (16,50 → 6,15) | ÷2,681 (16,503 → 6,155) | = |
| vue par l'évaluation | ÷1,57 | ÷1,5657 | = |
| témoin R0 | 1,8e-12 relatif | 1,81e-12 (frontière), 1,12e-12 (synonyme) | = |
| cassure R0 | « un écart d'un facteur 41 » | rapport 42,38 (synonyme), 50,94 (frontière) ; écart relatif 41,38 | **corrigé** (M1) |

Les 32 lignes du CSV commité (code, exact, deux symboles, deux valeurs, changement) égalent la source,
entiers exacts et réels à 2,7e-7 (six décimales écrites). Aucune valeur exacte du bloc ne sort du cadre
(|poids| ≤ 4 s_b, cadre ± 4,6). « L'erreur va vers les directions muettes de H » (dite, renvoyée au
panneau (b)) : H est de rang 1 329 ; l'énergie de l'erreur dans ses 1 551 directions de valeur propre
nulle passe de 21,53 (53,7 %) à 29,43 (61,3 %), celle des autres reste à 18,5 : vrai.

### 2.3 III-9.7, le nuage des entrées sur les axes propres de H — tient

Sources du juge : captures de calibration (et d'évaluation pour la cassure) de la couche 8, GGUF, .sym,
CSV du lot B. Sortie : `juge-rangee-nuage.json`, clé `nuage`.

| Nombre écrit | Lot | Juge | |
|---|---|---|---|
| entrées | 1 329 | 1 329 positions distinctes où l'expert 0 est parmi les quatre | = |
| λ1, λ2, λ3 ; part de la trace | 279,5 ; 33,5 ; 21,7 ; 28,2 % | 279,452 ; 33,507 ; 21,733 ; 28,154 % | = |
| spectre entier contre le lot B | — | 100 premières valeurs propres à 3,6e-10 | = |
| u1ᵀx : moyenne, écart-type | 16,5 ; 1,84 | 16,493 ; 1,8398 (population) | = |
| F | 96,9 | 96,905 (règle : 2 √λ2 / plus grand demi-axe frontière du plan (u1, u2)) | = |
| rapports synonyme / frontière le long de u1, u2, u3 | 0,082 ; 0,217 ; 0,269 | 0,08203 ; 0,21702 ; 0,26926 | = |
| autres directions | 2 877 | 2 880 − 3 | = |
| témoin N0 | 3,4e-10 | 3,36e-10 | = |
| cassure N0 (H d'évaluation) | λ1 bouge de 5,5 % | 294,83 contre 279,45, 5,50 % (1 239 entrées) | = |
| « la frontière répartit son erreur à plat » | — | demi-axes 0,1195 et 0,1159 (rapport 0,970), 0,1187 et 0,1156 (0,974) | = |

Les 1 329 points du CSV commité égalent mes coordonnées à 5e-7 (signes de u2 et u3 opposés aux miens :
le lot les tourne vers une moyenne positive, c'est écrit). Chacun des 4 × 181 points des ellipses
commitées vérifie (y/F)ᵀ M⁻¹ (y/F) = 1 avec ma M (aux signes du lot) à 1e-6 près. La flèche va bien de
l'origine à l'entrée moyenne (16,4931 ; 0,2393 ; 0,5356, aux signes du lot).

## 3. La régénération au bit

Racine de brouillon tirée de c4f3fe2 par `git archive` (scripts du lot, lecteur GGUF de 03, CSV du lot B),
sans les mesures du lot : les trois scripts de mesure ont tout réécrit de zéro, puis
`memoire/outils/tome3_latents.py` a tiré les données de figure **des mesures régénérées** (la chaîne
entière, pas un maillon). `latents_rangee.py` : 2 s ; `latents_nuage.py` : 12 s ; `latents_etats.py` :
24 min sur un fil, machine chargée par d'autres sessions (le lot : 22 min).

| Fichier | Résultat |
|---|---|
| `mesures/genome/tome3/latents/etats-c23.csv` (dont les 6 132 coordonnées t-SNE) | **égal au bit** |
| `rangee-L08-E00-gate.csv`, `nuage-L08-E00-gate-points.csv`, `-ellipses.csv` | **égaux au bit** |
| les 13 fichiers de `memoire/figures/tome3/donnees/latents-*` (dont `latents-chiffres.tex`) | **égaux au bit** |
| `etats-c23.json`, `rangee-L08-E00-gate.json`, `nuage-L08-E00-gate.json` | égaux champ par champ hors `duree_s` |

La t-SNE est donc bien déterministe, comme la légende le dit : une seconde passe, un autre jour de charge,
redonne ses 12 264 coordonnées au dernier chiffre écrit. Témoin du comparateur (`--casser` : un octet
inversé en mémoire dans chaque fichier régénéré, un champ changé dans chaque JSON) : les 20 comparaisons
tombent (`juge-regen-casse.json`). Rien n'a été écrit dans `mesures/` : les fichiers régénérés sont restés
dans le brouillon.

## 4. Les points tirés au hasard (graine 27102026)

- **III-7.6** : un état par série (g1 à g8 et « autres ») : positions 1405, 1144, 3072, 4521, 5726, 5875,
  1742, 3638, 3631. Pour chacun : expert premier et quatre experts recalculés depuis h et le GGUF, égaux
  au journal ; marge égale au CSV ; coordonnées de l'ACP égales à 5e-7. En plus, les 6 132 lignes des
  deux CSV de la figure ont été contrôlées (groupe, taille). Les coordonnées t-SNE n'ont pas d'autre source
  que la passe : elles sont contrôlées par la régénération au bit (§ 3) et par leurs T, C, accords refaits.
- **III-9.1 (c)** : les quatre séries (exact, frontière, synonyme, codons changés) et les niveaux : les 32
  lignes, toutes, contre le GGUF et les .sym.
- **III-9.7** : les entrées (cinq positions tirées, 1336, 3829, 6084, 1624, 1093 : g et c1 à c3 égaux à la
  source), puis les 1 329 ; les quatre ellipses : un point tiré par série (i = 78, 48, 164, 154), puis tous.

## 5. Compilation et pages lues

Pilote du lot (`memoire/essai/pilote-tome3-latents.tex`, copié dans le brouillon), `lualatex` deux passes,
français et anglais : sortie 0, aucune boîte trop pleine ni trop creuse, aucune référence manquante ; les
avertissements sont ceux du préambule (unicode-math, microtype, hauteur d'en-tête). Après ma correction
(§ 7), recompilé dans les deux langues : sortie 0, page 5 relue en français et en anglais ; les deux PDF
du pilote du lot (`memoire/essai/`, ignoré par git) sont remplacés par ceux-là. Pages lues (III-7.6, III-9.1 (c), III-9.7, FR et EN) :
les nombres imprimés sont ceux des tableaux ci-dessus ; les traductions disent la même chose.

## 6. Ce qui serait faux ou trop beau

- **R1** (attribution du ×1,44), **R2**, **R4** (S\*) : aucune de ces trois figures ne porte de vitesse, de
  KL ni de S\*. Rien à porter.
- **R3** (protocoles 32 / 768 experts) : aucune KL ; les nombres de sortie (÷2,7, ÷1,57) sont ceux d'une
  seule matrice, sur ses entrées de calibration et d'évaluation, et la légende le dit. Pas de mélange.
- **Phrases barrées.** J'ai relu les `~~` de 05, 07, des notes de la synthèse et du lot B, de
  JUGEMENT-construction : vitesses ×1,24 et ×2,00, « la queue ne bouge pas », S\* à 3 fenêtres, cause du
  cache. Aucune ne revit dans ces légendes. Les nombres de III-9.1 (c) qui viennent du lot B (40,07 →
  48,01 ; 16,50 → 6,15 ; ÷1,57 ; 07 § 2 et note du lot B § 2.2) n'y sont pas barrés.
- **Échelles.** III-7.6 : axes égaux pour l'ACP, aucune graduation pour la t-SNE (juste). III-9.1 (c) :
  unités de s_b, c3 hors cadre dit. III-9.7 : axes égaux (un cercle reste un cercle), même F pour les deux
  ellipses et les deux panneaux, F dit en clé et en légende : les rapports se lisent sans tromper.
- **Fidélité des projections** : dite pour les deux plans (variance, T, C, Spearman, accords), avec un
  témoin de l'instrument qui tient et une cassure qui tombe. Pas tue.
- **Ce qui est trop beau, et ne l'est pas** : la t-SNE montre des nuées par couleur ; ce n'est pas un
  artefact, l'accord dans l'espace d'origine (48,1 % contre 12,2 % au hasard) le porte. Ce qui pourrait
  l'être : la taille (M2), le seuil sans puissance (M5), la lecture de « les axes que les entrées
  occupent » (M8).

## 7. Les mineurs

- **M1 (corrigé par le juge, mécanique).** III-9.1 (c), témoin R0 : la légende disait « les fichiers d'un
  autre expert : un écart d'un facteur 41 » (EN « off by a factor 41 »). `\LatRangCassure` est
  `min(cassure_expert1_ecart_relatif)` = |‖W − Ŵ₁‖² / Σe_k − 1| = 41,38 : un écart **relatif** ; le
  facteur est 42,38 (50,94 pour la frontière). Corrigé dans `memoire/figures/tome3/latents-figures.tex` :
  « un écart relatif de 41 » / « a relative gap of 41 ». Le nombre, la macro et le script ne changent pas ;
  pilotes recompilés FR et EN.
- **M2 (rapporté).** III-7.6 : la taille (z(4) − z(5)) et la couleur (expert premier, bord z(1) = z(2))
  parlent de deux frontières différentes ; mesuré, les gros points ne sont pas au bord des nuées
  (§ 2.1). Deux sorties honnêtes, au choix de la rédaction : (a) régler la taille par z(1) − z(2), la
  marge de la couleur (ses gros points seraient au bord : 0,67 contre 0,43) ; (b) garder z(4) − z(5) (la
  marge de la garde tropicale, chapitre 11) et l'écrire en légende : « les gros points ne marquent pas
  les bords des couleurs (part des 10 voisins d'un autre expert premier : 0,51, comme les autres) ». La
  phrase de la note de reprise sur les « frontières » est fausse pour cette marge et ne doit pas passer
  dans un chapitre.
- **M3 (rapporté, design).** III-7.6 : les pastilles de la clé des tailles sont aux vraies tailles (0,85 et
  0,42 pt) : à la lecture du PDF, les deux dernières se voient à peine. Le lot l'a signalé.
- **M4 (rapporté).** III-7.6 : « 12,2 % au hasard » est Σ p² (un état compté comme son propre voisin) ;
  pour un voisin tiré parmi les autres états, le hasard est Σ n(n − 1)/(N(N − 1)) = 12,14 %, soit 12,1 %.
  0,02 point, sans effet sur la lecture (48,1 contre 12) ; c'est un choix de définition, pas une erreur
  mécanique : non corrigé.
- **M5 (rapporté).** III-7.6 : le seuil déclaré (T et C de la t-SNE ≥ ceux de l'ACP) n'a presque pas de
  puissance : l'initialisation de la t-SNE (le plan de l'ACP réduit) a exactement les T et C de l'ACP
  (rangs invariants par homothétie) et passe déjà, à égalité. Le lot n'a pas montré que ce seuil pouvait
  tomber. La t-SNE gardée le dépasse de loin (T + 0,155, C + 0,042), la conclusion tient ; mais « gardée
  par le seuil déclaré » dit plus qu'il ne prouve. Proposition : l'écrire (« un seuil que l'initialisation
  atteint déjà ») ou, au prochain lot, déclarer un seuil qui peut tomber.
- **M6 (rapporté).** III-9.1 (c) : dans la bande, « +0 » et « −0 » notent ±c0 (classe 0), pas des zéros
  signés ; au chapitre 8 (le codon synonyme du zéro), ±0 veut dire autre chose. Ni cette notation ni les
  flèches (de la base frontière à la base synonyme) ne sont dites dans la légende.
- **M7 (rapporté, palette).** Chapitre 9 : le lot « construction » trace la frontière en SerieF et le
  synonyme λ = 1 en **SerieA (bleu)** dans III-9.1 (a)(b), III-9.2 et III-9.6 (`synonyme-figures.tex`,
  ligne 5 : « Couleurs du chapitre ») ; ce lot trace la
  frontière en gris et le synonyme en **SerieB (rouge)** dans III-9.1 (c) et III-9.7. Dans une même
  figure III-9.1, (c) contredit (a)(b). À unifier (latSynonyme et latFrontiere sur les couleurs du
  chapitre, « losanges rouges » à réécrire). III-9.1 (c) porte aussi sa propre légende et renvoie aux
  « panneaux (a) et (b) » d'une autre macro : la rédaction doit les assembler en une figure.
- **M8 (rapporté, lecture).** III-9.7 : « le synonyme l'aplatit le long des axes que les entrées
  occupent » est vrai au sens de H non centrée (λ1 = 279,5, dont 16,49² ≈ 272 viennent de la moyenne),
  mais l'étalement visible du nuage est le long de u2 (écart-type 5,98 contre 1,84 le long de u1), et
  l'ellipse synonyme s'allonge justement le long de u2 : l'œil peut lire l'inverse. Proposition : « le long
  de u1, l'axe où les entrées pèsent le plus (leur moyenne) ».
- **M9 (rapporté).** La note de reprise du lot écrit « 25 experts premiers distincts », son rendu « les 17
  autres en gris » : il y en a 27, donc 19 autres (le JSON et la légende, par sa macro, disent juste).
- **M10 (rapporté).** « Règle déclarée » (F de III-9.7) et « règle déclarée avant le tirage » (bloc de
  III-9.1 (c)) : règle et résultat sont dans le même commit (3ce3553), l'histoire ne prouve pas l'avant.
  Ce sont des choix d'affichage (une échelle, un bloc typique), pas des seuils : sans conséquence, mais le
  mot « déclarée » ne doit pas se lire comme une déclaration préalable. Pour III-7.6, le seuil est bien
  antérieur (47b96c2 à 08:04:28 ; passe de 1 324 s, CSV à 08:26).

## 8. Ce qui pourrait être faux

- **Mes chemins ne sont pas tout à fait indépendants des entrées.** Je relis les mêmes captures, le même
  GGUF et les mêmes .sym que le lot : une capture fausse à la source tromperait les deux. Les témoins W0
  (le routeur relu redonne le journal de routage au bit des ensembles) et R0, N0 (égalité avec le CSV du
  lot B, écrit par un autre rôle) bornent ce risque sans l'annuler.
- **Les définitions viennent des légendes**, que j'ai lues avant d'écrire mon code : une définition
  ambiguë dans une légende (par exemple « au hasard ») a pu me conduire au même choix que le lot sans que
  ce soit le seul juste (M4 en est un).
- **Le Spearman** est refait sur d'autres paires (2 000 000, ma graine) : il confirme l'arrondi à deux
  chiffres, pas les chiffres suivants du lot.
- **La t-SNE n'a pas de source indépendante** : je n'ai pas réécrit de t-SNE ; je contrôle ses
  coordonnées par la régénération au bit et par la fidélité refaite. Une erreur dans son gradient qui
  donnerait quand même une carte fidèle (T 0,947) passerait ; j'ai relu le code (perplexité par
  dichotomie sur l'entropie, P symétrisée, gradient exact 4 (attraction − répulsion / Z), exagération,
  gains) sans y trouver d'écart à van der Maaten et Hinton 2008.
- **Le design** est jugé à la lecture des PDF à l'écran, pas imprimé ; les couleurs proches (expert 12 en
  SerieA, expert 13 en Ram) peuvent se confondre à l'impression.
- **M2 dépend de ma mesure du bord** (une définition par les voisins). Vérifié à k = 5 et k = 20 dans
  l'espace d'origine : pour z(4) − z(5), 0,480 / 0,508 / 0,471 et 0,547 / 0,570 / 0,543 (aucun ordre) ;
  pour z(1) − z(2), 0,668 / 0,573 / 0,381 et 0,684 / 0,615 / 0,479 (net). Le sens ne change pas ; une
  autre définition du bord (géométrique, sans voisins) n'a pas été essayée.

## 9. Reproduire

```
cd outils/genome/tome3/juge-latents
python -I -X utf8 juge_rangee_nuage.py > juge-rangee-nuage.json     # ~1 min
python -I -X utf8 juge_etats.py > juge-etats.json                   # ~4 min, < 1 Go
python -I -X utf8 juge_etats_marges.py > juge-etats-marges.json     # ~1 min
# régénération : voir l'en-tête de juge_regen.py (racine de brouillon par git archive)
python -I -X utf8 juge_regen.py <brouillon>/racine > juge-regen.json
python -I -X utf8 juge_regen.py <brouillon>/racine --casser > juge-regen-casse.json
```
