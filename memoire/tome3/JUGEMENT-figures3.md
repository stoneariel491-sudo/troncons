# Tome III, troisième passe des figures : le jugement (chiffres et dessin)

Juge indépendant de la troisième passe, 2026-10-27. Je n'ai rien fait de ce que je juge. Objet : les commits du
préambule (`7db2673`, `4a9dfb3`, `2e3578c`, `c31bf39`) et ceux des retouches (`7a40c54`, `6137230`, `1482dbe`), contre
SOCLE (« la beauté à égalité avec la justesse »), `REPRISE-figures.md` (la troisième passe), `CONVENTIONS-figures.md`
et les quatre jugements du second flux (`JUGEMENT-figures2-construction.md`, `-latents.md`, `-ronde.md`,
`-design.md`). Aucune mesure, aucune carte graphique, aucune passe du modèle ; MiKTeX tel qu'il est installé (26.5),
sans rien y changer. Mes outils et journaux : `outils/genome/tome3/juge3/` ; mes compilations : `memoire/essai/juge3/`
(dossier ignoré par git).

**Ce document est écrit en deux temps.** Le premier commit ne porte que le § 1 : les seuils et les critères,
déclarés avant que j'aie regardé une page rendue de la troisième passe ou un PDF des tomes reconstruit. Je n'ai lu
jusqu'ici que des sources : les notes de reprise des deux rôles, les quatre jugements du second flux, et les `git
show` des sept commits (sources `.tex`, scripts, nombres). Le verdict et le reste suivent dans un commit séparé.

Le second commit ajoute le § 0 et les §§ 2 à 10 ; le § 1 est resté tel qu'il était déclaré (`6460fb2`). Deux de
mes outils ont été corrigés après un premier essai, et une de mes règles a été précisée ; je le dis au § 2.6.

## 0. Verdict

**Le préambule est réparé et ne change aucune page des Tomes I et II. Les trois phrases fausses, G7 et G10 sont
levés, et chaque nombre neuf est juste. Mais une retouche non demandée crée un grave neuf : en III-2.1, le halo blanc
posé sous la ligne « tout le modèle » cache le sommet de 37 barres. Et GD1 tombe encore à son critère déclaré, pour
un seul reste : le renvoi `\cref` ajouté dans la note de III-8.7 s'imprime dans le bleu des liens, `Accent`.**

- **Le préambule (§ 3) : tient.**
  - La cause A est refaite par mon propre document minimal : deux frères, deux erreurs. Retirer le seul crochet
    `firstaid/aliascounter` les fait disparaître. La trace montre `\newcounteralias {proposition}{proposition}`
    appelé par `\@ynthm`.
  - Le correctif A donne 0 erreur et les mêmes renvois. Mon témoin d'un vrai défaut (alias vers un autre registre,
    compteur absent) lève encore ses deux erreurs.
  - La cause B est reproduite en dix lignes, ce que le rôle n'avait pas obtenu, et sa condition est isolée : un
    `\textsuperscript` au niveau du texte courant, puis un nœud TikZ d'une autre taille qui appelle `\textsubscript`.
    Une formule ou une note de bas de page ne suffit pas. Le correctif B donne 0 erreur.
  - Le pilote commun, compilé avec le préambule d'avant, lève 6 erreurs ; avec le préambule commité, 0.
  - Les Tomes I et II, reconstruits par moi en français et en anglais : 0 erreur, 0 renvoi ni citation indéfinis,
    173, 169, 237 et 233 pages. **Toutes les pages sont égales aux PDF commités** (faits sous 26.2), par les mots et
    leurs boîtes (au plus 0,195 pt de déplacement) et par l'image (au plus 0,0033 % de pixels au-delà de 64 niveaux,
    pour un seuil de 0,05 %).
- **Une phrase fausse dans la note du rôle préambule.** « Dans le Tome II, deux preuves sont coupées autrement
  (p. 103 et 131 FR ; 81, 101 et 131 EN) » ne tient pas.
  - Les pages 103 et 131 du Tome II français sont égales au pixel près, à 150 dpi, entre le PDF commité et ma
    construction. Les mêmes coupures, « comp-teurs » et « exponen-tielle », sont dans les deux.
  - Ce que le rôle a vu vient de `pdftotext` : il extrait le « ■ » du PDF de 26.5, pas celui de 26.2, et il
    recoupe alors les lignes autrement. MuPDF extrait le « ■ » des deux PDF (71 et 71).
  - La conclusion du rôle (« même mise en page ») en sort plus forte, mais ces phrases sont à barrer (§ 3.4).
- **Les chiffres (§ 4) : tiennent.**
  - 51 nombres neufs ou déplacés sont refaits par mon code depuis `mesures/` (ou depuis le fichier commité que cite
    la légende) : 50 sont égaux à l'arrondi imprimé.
  - Le seul écart, `SynoNVarPartLargeur` (61,1 contre 61,2 en pleine précision), n'est imprimé dans aucune légende.
  - Les nombres des entrées réelles de III-9.7 sont refaits **à la source**, par un troisième chemin (GGUF, `.sym`,
    captures, lecteurs écrits ici). Ils sont égaux au journal du juge latents du second flux, au seizième chiffre.
  - La régénération donne 117 fichiers sur 121 égaux au bit ; les 4 autres (palette) sont égaux au contenu, avec
    des fins de ligne CRLF.
  - Chaque garde neuve, forcée à faux par mon propre moyen, fait tomber le script.
- **Les graves visés (§ 5)** :
  - GN2 (III-8.5) : **levé** ;
  - GN1 de la construction (III-10.1) : **levé** ;
  - GN1 des latents (III-9.7) : **levé**, avec un mineur (la borne 0,135 de la tête est écrite sans son cône) ;
  - G7 : **levé**, 61,1 % de la largeur sur la source et au rendu, en FR et en EN ;
  - G10 : **levé**, le trait passe à 0,52 mm de « partitions κ, par tenseur » en FR et à 1,19 mm en EN. Il frôle
    maintenant le « 4 » de la graduation « 2,644 » de l'encart (mineur) ;
  - GD1 : **non levé au critère**, à un geste près. Aucun bleu ne code plus de donnée hors du dictionnaire : 0 pixel
    bleu dans sept des huit figures, en FR et en EN. Mais III-8.7 en porte 461 (FR) et 473 (EN) : ceux du lien
    « figure 1.2 » que la passe a ajouté dans sa note.
  - DN1 : **en partie**. Les têtes de III-8.6 gardent « ×1,454 » et « +3,4 % » en maigre, dans les deux langues ;
    la note des retouches les dit grasses.
- **Grave neuf (1)** : **GJ1**, III-2.1 (§ 6).
  - Le trait blanc de 1,8 pt ajouté sous la ligne « tout le modèle » coupe toutes les barres qui la traversent. Il
    cache le sommet des barres qui finissent à moins de ±0,0025 bit de la moyenne : **12 barres sur 72 au 20b, 25 sur
    108 au 120b**. Ces barres paraissent toutes finir à la même hauteur.
  - C'est la zone même où la figure veut montrer que le coût est « plat ». En FR comme en EN.
- **Mineurs (11)**, § 7. Cinq sont nés de la passe : le trait de la loupe qui frôle « 2,644 », des valeurs de III-4.8
  plus près d'une autre arête que de la leur, l'étiquette du synonyme sur son point en III-7.2, les mots de couleur
  inversés de III-8.5, la borne de la tête de III-9.7. Les autres sont des restes ou des phrases de notes.
- **Ce qu'une retouche casse ailleurs (§ 8)** : GJ1 et le lien bleu de III-8.7, et rien d'autre de grave.
  - Les styles communs changés (`\Legende`, `t3 titre panneau`, version grasse des mathématiques) compilent dans les
    29 figures sans erreur ni police manquante.
  - Le diff des chevauchements, entre les PDF du second flux et les miens, ne montre aucune étiquette traversée neuve
    hors de celles que je cite.
  - Aucune donnée d'une figure que la passe ne visait n'a bougé.

| Figure | Verdict | En une ligne |
|---|---|---|
| III-2.1 signe des zéros | **tombe** (GJ1) | le halo blanc cache 37 sommets de barres et en coupe 40 autres |
| III-3.4, III-3.6, III-4.2 | tiennent | DN22, DN6, DN4 faits ; rien de neuf |
| III-4.8 arbre | tient, réserve | aucune valeur ne touche un trait (DN7), mais 4 sur 10 sont plus près d'une autre arête (M4) |
| III-7.1 frontière | **tient** (G10 levé) | 0,52 mm (FR) et 1,19 mm (EN) de « partitions κ, par tenseur » ; frôle « 2,644 » (M1) |
| III-7.2 erreur contre KL | tient, réserve | bande en tirets (GD1, DN11) ; étiquette sur son point (M6) |
| III-7.3 | tient | DN12 fait |
| III-7.4 colonne géante | tient | seconde pointe nommée, nombres justes |
| III-7.6, III-9.1 (c) | tiennent | anneaux visibles en gris (DN13) ; flèche de j = 11 visible ; 3 et 1 justes |
| III-8.1, III-8.2, III-8.4 | tiennent | le bleu est rendu à l'encre et au gris ; paires tenues |
| III-8.5 colonne | **tient** (GN2 levé) | codec réel, coût d'alphabet juste ; mots de couleur inversés (M5) |
| III-8.6 J1 | tient, réserve | « +3,4 % au plus » juste ; DN1 non fait dans sa tête (M2) |
| III-8.6 bis | tient | 1 200 et 800 tronçons, 0,140 ± 0,032, lecteurs dits |
| III-8.7 format | **tombe au critère** (GD1 b) | le lien bleu de la note ; le reste en orange de la v1.2 |
| III-9.1 (a)(b)(b′), III-9.3 | tiennent | 4 mm de plus ; cadre −0,38 à 0,10 ; « 9 fenêtres sur 10 » juste |
| III-9.6 variantes | **tient** (G7 levé) | 61,1 % de la largeur, source et rendu ; aucune étiquette sur une barre |
| III-9.7 nuage | **tient** (GN1 levé) | 0,61 (0,49 à 0,81) refait à la source ; borne 0,135 sans son cône (M3) |
| III-10.1 experts vus | **tient** (GN1 levé) | C1, 768 sur 768, confirmé par le journal du vérificateur |
| III-10.3 fenêtres | tient | fourchette des trois variantes juste |
| Tomes I et II | **tiennent** | 0 erreur, mêmes pages, égales aux PDF commités par les mots et par l'image |


## 1. Seuils et critères, déclarés avant la lecture des rendus

### 1.1 Le préambule (MiKTeX 26.5)

- **La cause.** Elle tient si, sous MiKTeX 26.5, (a) un document minimal écrit par moi (pas celui du rôle) avec
  `scrbook`, `amsthm`, `hyperref`, `cleveref`, `thmtools` et deux `\declaretheorem[sibling=…]` lève l'erreur
  « `\c@x` already defined » une fois par frère, sans le correctif ; (b) une trace (`\tracingmacros`) montre l'appel
  `\newcounteralias{x}{x}` venu du `\@ynthm` des premiers soins ; (c) l'erreur disparaît si je retire le seul crochet
  des premiers soins (`firstaid/aliascounter`), correctif absent. Si (c) ne tient pas, la cause écrite est fausse.
- **Le correctif A** tient si le même document, avec les lignes du préambule commité recopiées telles quelles, donne
  **0 erreur** et les **mêmes renvois** (`\ref` et `\cref`, texte du PDF) que sans thmtools ; et s'il ne tait pas un vrai
  défaut : un alias vers un autre registre lève encore son erreur (témoin qui doit tomber).
- **Le correctif B** tient si un document minimal à moi, un nœud TikZ contenant `\textsubscript` après un chapitre
  du Tome II, tombe sans lui et passe avec lui ; sinon je le dis non reproduit, sans le faire tomber pour autant
  (le rôle dit lui-même ne pas avoir isolé la condition).
- **Un pilote** (le pilote commun, copié dans mon dossier) : 0 erreur avec le préambule commité ; 6 avec le préambule
  d'avant `7db2673` (le témoin doit tomber).
- **Les tomes.** Je reconstruis moi-même, sous `-halt-on-error` (le `latexmkrc` du dépôt), les Tomes I et II en
  français et en anglais. Ils tiennent si : 0 erreur, 0 renvoi ni citation indéfinis, et **le même nombre de pages**
  que les PDF commités (173, 169, 237, 233).
- **« La mise en page ne change pas »**, contre les PDF commités (faits sous MiKTeX 26.2) :
  - par les mots et leurs places : pour chaque page, la suite des mots (PyMuPDF) et la boîte de chacun ; une page est
    **égale** si ses mots sont les mêmes, dans le même ordre, et si chaque boîte bouge de **moins de 0,5 pt** ; le
    carré de fin de preuve « ■ », que le rôle dit extractible sous 26.5 seulement, est écarté des deux côtés et
    compté à part ;
  - par l'image : chaque page rendue à 50 dpi en gris des deux côtés ; une page est **différente à l'œil** si plus
    de 0,05 % de ses pixels diffèrent de plus de 64 niveaux sur 255. Le bruit de référence est mesuré, pas supposé :
    le même PDF rendu deux fois (doit donner 0), et deux constructions du même tome par moi (doit donner 0) ;
  - chaque page différente par les mots ou par l'image est rendue à 150 dpi des deux côtés et lue ;
  - le verdict « même mise en page » tient si les pages diffèrent seulement là où le rôle l'a écrit (Tome II, p. 103
    et 131 en français, p. 81, 101 et 131 en anglais) ou par un glyphe sans déplacement des lignes ; toute autre page
    différente est un défaut à rapporter.
- **D'où vient une différence** (MiKTeX ou correctif) : je compile, sous 26.5, les chapitres du Tome II qui portent
  les pages différentes avec le préambule commité puis avec celui d'avant `7db2673` (`nonstopmode`), et je compare les
  deux PDF de la même façon ; s'ils sont égaux, la différence n'est pas due aux correctifs.

### 1.2 Les chiffres des retouches

- **Chaque nombre neuf ou déplacé** des `*-nombres.tex`, `*-chiffres.tex` et `synthese-nombres.csv` touchés par
  `7a40c54`, `6137230` et `1482dbe` est refait par mon code depuis les fichiers commités sous `mesures/` (ou le fichier
  commité que la légende cite), sans lire les fonctions des scripts du lot qui le calculent (je n'en ai lu que le
  `git diff`, pour savoir ce qui a changé ; je le redis au « Ce qui pourrait être faux »). Un nombre **tient** s'il est
  égal **à l'arrondi imprimé** ; je signale tout nombre à moins de 10⁻⁶ relatif d'une demi-unité de son dernier
  chiffre. Là où un second fichier existe, je le prends plutôt que celui du script.
- **Comparateur** : il doit pouvoir tomber ; chaque valeur recalculée faussée de 1 % relatif, je compte combien
  tombent (les petits entiers ne tombent pas à 1 % : je les compte à part).
- **La régénération** : les scripts touchés (`tome3_synthese`, `tome3_duplication`, `tome3_codon`, `tome3_juge`,
  `tome3_synonyme`, `tome3_latents`, `tome3_palette`) sont relancés dans une copie tirée par
  `git -c core.autocrlf=false archive` (dossier de données vide au départ, hors du dépôt) ; chaque fichier écrit est
  comparé par SHA-256 au blob commité. Ils tiennent si **tous sont égaux au bit**, sans fichier en trop ni en moins
  parmi ceux que le script écrit. Témoin du comparateur : un octet changé dans une copie, la comparaison tombe.
- **Les gardes neuves** (G7 à 50 %, GN2 contre `taux_reel`, GN1 contre `tailles.json`, E1, j = 11, J5/J6, compagnon,
  DN7, seconde pointe) : je force chacune à faux **par mon propre moyen** (une donnée changée dans ma copie, pas
  l'outil de cassure du lot) ; elle tient si le script s'arrête, et si rien n'est écrit sous `donnees/` du dépôt.
- **Les trois phrases** (GN2 construction, GN1 construction, GN1 latents) sont levées si la phrase écrite est vraie au
  sens commun, dans les deux langues, et si chacun de ses nombres tient ; une phrase vraie mais qui dit plus que ses
  nombres (une borne écrite sans son domaine) est un mineur, pas un grave.

### 1.3 Le dessin

- **Compilation** : les quatre pilotes copiés dans `memoire/essai/juge3/` (pas les PDF des lots), `lualatex`, deux
  passes (trois si le journal le demande), français et anglais : **0 erreur, 0 boîte trop pleine, 0 renvoi indéfini**,
  0 avertissement « Font shape … undefined » neuf.
- **Lecture** : chaque page touchée des huit PDF, en planche (75 à 100 dpi), puis chaque figure touchée agrandie
  (300 à 400 dpi) en couleur, en gris et en deutéranope par `outils/genome/tome3/juge2-design/vues.py` (lecture
  seule ; il appelle les fonctions de `juge-design/palette.py`). Je ne retiens qu'un défaut vu agrandi.
- **Couleurs** : ΔE CIE76 (CIELAB, D65) ; une paire que la figure demande de séparer tient si **ΔE ≥ 5 en gris** et
  **ΔE ≥ 10 en deutéranope** (Machado, sévérité 1), nominale et rendue ; sinon elle tient seulement si un second
  canal la sépare sur le rendu en gris à 300 dpi (marque, trait, étiquette directe, place). Mêmes seuils que les deux
  juges de design, pour que les verdicts se comparent. Témoin : TD2 du juge de design (rouge-vert sous la moitié de
  son ΔE en deutéranope) relancé par moi ; il doit tenir, et tomber avec des matrices identité.
- **G7 levé** si l'étendue en bits des trois variantes couvre **plus de 50 %** de la largeur du cadre, mesurée sur la
  source (macros) **et** sur le rendu (centres des marques et traits du cadre relevés dans les pixels à 400 dpi), en
  français et en anglais ; et si aucune étiquette ne couvre une marque, une barre ou un trait de barre (N1).
- **G10 levé** si, en français et en anglais, le trait de la loupe de III-7.1 ne traverse **aucune** étiquette :
  aucun pixel d'encre du trait dans la boîte des caractères d'une étiquette (boîtes relevées par PyMuPDF dans le PDF),
  vu à 400 dpi.
- **GD1 levé** si (a) `Accent` n'est plus employé pour dessiner dans aucun des huit fichiers de figures, (b) au rendu,
  aucune des huit figures du tableau de GD1 (III-2.1, III-4.8, III-7.2, III-8.1, III-8.2, III-8.4, III-8.5, III-8.7)
  ne porte de pixels à ΔE < 10 du bleu `1F5C99` ou de ses teintes (mélanges avec le blanc de 8 à 100 %), hors d'un
  sens du dictionnaire dit par sa légende, et (c) les couleurs qui remplacent le bleu tiennent contre leurs voisines
  aux seuils ci-dessus.
- **DN1** levé si les nombres et les symboles des têtes et des titres de panneau sont gras au rendu (vu à 400 dpi
  sur au moins quatre têtes, dont III-8.6 et III-4.8) et si aucune police manquante n'est signalée.
- **Chevauchement** : une étiquette traversée par un trait qui n'est pas le sien, ou qui en touche une autre, est un
  défaut (vu à 300 dpi au moins).
- **Ce qu'une retouche casse ailleurs** : je cherche, dans les huit fichiers de figures et les pilotes, chaque autre
  emploi d'un style, d'une macro ou d'une couleur que la passe a changés (`t3 titre panneau`, `\Legende`, `codon refus`,
  `codon neuf`, `\CodonNuls`, `dup arete`, `\EclZeros`, `colormap codon`, `jcons`, les cadres de III-9.3 et III-9.6), et
  chaque légende qui nomme encore une couleur, une hachure ou une bande retirées (« bleu », « blue », « hachur »,
  « hatched », « bande grise », « grey band », « tombe »/« falls » dans une clé). Une phrase qui décrit un dessin
  qui n'existe plus est un mineur ; une qui fait lire un nombre faux est un grave.
- **Grave ou mineur** : grave, une phrase de tête fausse, un nombre faux, une donnée cachée, un seuil déclaré non
  tenu ; mineur, le reste. Un grave levé dans une langue et pas dans l'autre n'est pas levé.

## 2. Ce que j'ai fait

Ordre suivi : seuils commités (`6460fb2`) avant toute page rendue ; puis tomes et documents minimaux ; puis nombres,
régénération et gardes ; puis lecture des rendus. Outils sous `outils/genome/tome3/juge3/`, journaux sous
`journaux/` ; compilations sous `memoire/essai/juge3/` (ignoré par git). Aucun fichier d'un lot, aucun fichier de mesure
ni PDF commité n'a été écrit ; MiKTeX n'a pas été touché.

1. **Documents minimaux** (`minimal-juge3.tex`, `minimal-b-juge3.tex`, `minimal_variantes.py`). Écrits de zéro. Les
   lignes des correctifs ne sont pas retapées : `extraire_correctifs.py` les tire du préambule de `HEAD`, et le
   préambule d'avant de `7db2673^`. Le préambule de `HEAD` compte 298 lignes : 273 + 14 + 11, aucune ligne changée.
2. **Tomes** (`construire_tomes.sh`). `latexmk -r memoire/latexmkrc` (donc `-halt-on-error`), nom de travail
   `j3-tN-L`, sorties sous `memoire/essai/juge3/tomes/`. Durées : 9, 7, 12 et 28 minutes.
   - Comparaison (`comparer_pdf.py`) : mots et boîtes par PyMuPDF, image en gris à 50 dpi par le même moteur des deux
     côtés.
   - Bruit de référence mesuré : le même PDF rendu deux fois, 0 ; ma construction contre celle du rôle (mêmes
     sources, même MiKTeX), 0 page différente et 0 pixel, pour le Tome I FR et le Tome II FR.
3. **Pilotes** (`compiler_pilotes.py`). Les quatre pilotes de `memoire/essai/` sont copiés dans `memoire/essai/juge3/
   pilotes/`, puis compilés en deux passes par langue (aucun ne demande de troisième passe). S'y ajoute le témoin
   « commun-avant » (préambule d'avant).
4. **Nombres** (`refaire3.py`), **régénération et gardes** (`regenerer3.py`), **source de III-9.7**
   (`sources_latents.py`) : § 4.
5. **Dessin.**
   - `figure3.py` et `zoom3.py` rendent une zone en couleur, en gris et en deutéranope. Ils appellent les matrices de
     `juge-design/palette.py` sans les modifier, comme `vues.py` du second juge, que j'ai aussi employé.
   - `croisements.py` (une zone, distances) et `croisements_vite.py` (toutes les pages, boîtes précises des
     caractères, intersection exacte) relèvent les traits qui coupent un texte. Le second compare aussi les PDF du
     second flux (`memoire/essai/juge2-design/`) aux miens.
   - `gd1_bleu.py` compte les pixels bleus d'une figure. `paires3.py` refait les paires de couleurs par une
     colorimétrie écrite ici. `tetes3.py` relève les morceaux maigres des têtes.
6. **Corrections de mes outils, dites** :
   - `gd1_bleu.py`, premier essai : la règle « ΔE < 10 d'une teinte du bleu, de 8 à 100 % » prenait pour du bleu les
     fonds pâles verts, rouges et orange (94 627 pixels de la zone gagnante en III-7.2). J'ai pris le classement au plus
     proche parmi les teintes de toutes les couleurs nommées et des gris. Le témoin (III-9.6, sens du dictionnaire)
     tient avant et après ; la cassure (seuil 0) tombe.
   - `gd1_bleu.py` et `figure3.py` cherchaient la légende par `search_for("Figure 1.")`, qui ignore la casse. En
     III-8.7, la zone s'arrêtait donc au renvoi « figure 1.2 » de la note, et le premier compte donnait 0 pixel pour
     III-8.7. Corrigé (bloc qui commence par « Figure ») : 461 et 473.
   - `refaire3.py` : ma règle « à moins de 10⁻⁶ relatif d'une demi-unité » ne dit rien pour un nombre écrit à six
     décimales (tout y est « près du bord »). Je l'ai remplacée par « à moins d'un centième d'unité du dernier
     chiffre ». Aucun nombre n'y tombe.

## 3. Le préambule

### 3.1 La cause A, refaite (`journaux/minimal.json`)

| variante (mon document, deux passes) | erreurs | renvois imprimés |
|---|---|---|
| sans correctif | **2** : `\c@proposition`, `\c@corollaire` already defined | 1.1 1.2 1.1 1.3 2.1 2.2 ; proposition 1.1, théorème 1.2, remarque 1.1, corollaire 1.3, corollaire 2.1, théorème 2.2 |
| crochet `firstaid/aliascounter` retiré, sans correctif | 0 | les mêmes |
| amsthm seul (témoin) | 0 | les mêmes |
| correctif A (lignes tirées du préambule) | **0** | les mêmes |
| correctif A + deux vrais défauts (alias vers `section`, compteur absent) | **2** : `\c@corollaire already defined`, `No counter 'inexistant'` | les mêmes |
| trace | 2 | `\newcounteralias {proposition}{proposition}`, appelé depuis `\@ynthm` |

Lu dans les sources installées :
- le `\@ynthm` des premiers soins (`latex2e-first-aid-for-external-files.ltx`, l. 335 à 357) appelle
  `\newcounteralias{##1}{##2}` ;
- `\newcounteralias` (`latex.ltx`, l. 10287) refuse un `\c@x` qui existe ;
- `thm-autoref.sty` 0.76 (l. 32 à 44) fait `\@counteralias{envname}{sibling}`, puis pose `\thmt@sibling` à
  `envname`.

**La cause écrite est juste.** Le témoin « crochet retiré » ajoute une preuve que le rôle n'avait pas : c'est bien ce
crochet, et lui seul, qui fait l'erreur.

### 3.2 La cause B, reproduite en dix lignes

`minimal-b-juge3.tex` : `article`, `tikz`, une phrase « Le 1\textsuperscript{er} essai. » au niveau du texte, puis un
nœud `font=\tiny` qui contient `ctx\textsubscript{0}`, puis un second nœud.

| variante | erreurs |
|---|---|
| exposant au niveau du texte, puis le nœud | **1** : « Giving up on this path » ; contexte `…esetcolor \restglb@settings` |
| le nœud seul | 0 |
| une formule `$x^2$` au niveau du texte, pas d'exposant | 0 |
| une note de bas de page, pas d'exposant | 0 |
| exposant, puis le nœud, correctif B | **0** |

La condition que le rôle n'avait pas isolée se lit dans `latex.ltx`. `\check@mathfonts` finit par
`\def\init@restore@glb@settings{\aftergroup\restglb@settings}`, et ce `\def` est local.
- Dans une formule, il meurt avec le groupe de la formule ; dans une note, avec la boîte de la marque.
- Un `\textsuperscript` du texte courant, sous le noyau 2026-06-01, le laisse au niveau du texte.
- Le premier `\textsubscript` qui vient ensuite, dans un nœud d'une autre taille, pose alors son `\aftergroup` dans
  le groupe du texte du nœud.

Cela explique « le chapitre 2 avant la figure suffit » : un exposant au niveau du texte du chapitre 2, et aucun dans
les chapitres 0, 1 et 3. Je n'ai pas cherché la ligne précise du chapitre 2. Le correctif B, qui enferme la commande
dans un groupe, coupe les deux effets : le jeton reste dans le nœud, et le `\def` ne fuit plus.

### 3.3 Le pilote et les tomes (`journaux/pilotes-compilation.json`, `tomes-construction.json`, `compare-t*.json`)

- Pilote commun, préambule d'avant : 6 erreurs, les six frères (corollaire, definition, hypothese, lemme,
  proposition, remarque), en FR et en EN. Avec le préambule commité : 0. Le texte est le même, page pour page.
- Les tomes :

| tome | erreurs | indéfinis | biber | boîtes trop pleines | pages (commité) | pages différentes (mots / image) | déplacement max | pixels max |
|---|---|---|---|---|---|---|---|---|
| I FR | 0 | 0 | 0 erreur | 31 | 173 (173) | 0 / 0 | 0,126 pt | 0,0012 % |
| I EN | 0 | 0 | 0 erreur | 33 | 169 (169) | 0 / 0 | 0,011 pt | 0 |
| II FR | 0 | 0 | 0 erreur, 1 avertissement | 7 | 237 (237) | 0 / 0 | 0,195 pt | 0,0029 % |
| II EN | 0 | 0 | 0 erreur, 1 avertissement | 5 | 233 (233) | 0 / 0 | — | 0,0033 % |

- Les boîtes trop pleines sont celles que le rôle dit sous 26.2.
- L'avertissement de biber du Tome II (« Overwriting field 'year' … xiao2024sinks ») vient d'une entrée de la
  bibliographie, pas du préambule.
- Je n'ai pas compilé les tomes avec le préambule d'avant : sous `-halt-on-error`, ils ne passent pas. La
  comparaison aux PDF de 26.2 répond seule à la question, puisque aucune page ne diffère.

### 3.4 Ce qui est faux dans la note du rôle préambule

- « Dans le Tome II, deux preuves sont coupées autrement : p. 103 et 131 en FR, p. 101 et 131 en EN, plus un ordre
  d'extraction d'accent p. 81 en EN » (en bref de sa valeur de retour, `REPRISE-figures3-preambule.md` § État et § 4,
  message de `2e3578c`) : **faux**.
  - À 150 dpi, en gris, les pages 103 et 131 FR et 101 EN sont égales au pixel près au PDF commité.
  - Les pages 81 et 131 EN diffèrent de 10 à 12 niveaux sur 255 au plus, sur 698 et 122 pixels : du lissage, rien qui
    se voie.
  - Les deux PDF portent « comp-teurs » et « exponen-tielle ». L'écart vient de `pdftotext` seul.
- « 26.5 rend le ■ extractible et 26.2 non » : vrai pour `pdftotext` (0 contre 71), faux pour MuPDF (71 et 71). Les
  PDF diffèrent dans leur table de caractères, pas à l'œil.
- À barrer par son auteur ou par l'orchestrateur (je ne touche pas la note d'un rôle). La conclusion, « même mise en
  page », tient, et plus fort qu'elle ne le dit.

## 4. Les chiffres

### 4.1 Les nombres neufs ou déplacés (`journaux/refaire3.json`)

51 nombres. Chacun est refait depuis la source citée, et 50 sont égaux à l'arrondi imprimé. Pour mes sources, j'ai
pris d'autres fichiers que ceux des scripts quand j'en avais :
- III-8.5 : le journal du codec réel `taux-reel-colonne-12-gptoss20b.json`, plutôt que `colonne-par-tenseur.csv`.
  Les quatre colonnes y sont égales à 0 près.
- III-10.3 et le cadre de III-9.3 : les fichiers par position (`synonyme/moteur/` et `synonyme/kl/`), plutôt que
  `kl-par-fenetre.csv` ; pour R1, ils redonnent le CSV de la forêt à 4,8·10⁻⁷ près.
- III-9.7 : le spectre commité du lot B pour ce qui s'en tire, et la source pour le reste (§ 4.2).

| Figure | Nombres | Refaits | |
|---|---|---|---|
| III-7.4 | 960 ; ×0,83, ×310, ×1,04, ×0,87 ; 44 bords ×0,70 (au plus ×0,87) ; 62 colonnes ×4,0 ; ×7,6 | 960 ; 0,8270, 310,385, 1,0431, 0,8654 ; 44, 0,7016, 0,8701 ; 62, 3,9996 ; 7,5834 | = |
| III-8.5 | coût d'alphabet 0,0029 à 0,0050 ; 0,0220 ; 3 tenseurs | 0,002946 à 0,005004 ; 0,021982 ; 3 | = |
| III-8.5 | « les barres négatives sont surtout ce coût » | 6 barres négatives, de −0,0033 à −0,0045 ; la colonne seule y fait de −0,0006 à +0,0006 | vrai |
| III-8.6 bis | 1 200 (J5), 800 (J6) ; 0,140 ± 0,032 | n = 1 200 dans les 2 passes J5, n = 800 dans les 12 passes J6 ; 0,14039, 2σ par fenêtres 0,03189 | = |
| III-10.1 | 768 sur 768 | `tailles.json` ; et le journal du vérificateur : `C1` vrai, 768 exacts, 0 faux | = |
| III-10.3 | −0,0014 ; +0,0001 ; −0,0004 ; −0,0076 à +0,0029 | −0,001429 ; +0,0000580 ; −0,000446 ; −0,007554 à +0,002921 | = |
| III-9.3 | cadre −0,38 à 0,10 ; 9 sur 10 | extrêmes −0,34525 et +0,06095, règle de marge 0,02 ; fenêtres gagnées 10, 10, 9, 10 | = |
| III-9.6 | 2,56 à 2,70 ; 61,1 % | 2,56 à 2,70 ; **61,17 %** depuis les bits en pleine précision, 61,14 % depuis le CSV arrondi à 4 décimales | 61,1 ≠ 61,2 (non imprimé) |
| III-9.1 (c) | 3 s'éloignent, 1 à même distance | 3 et 1, le 1 est le zéro de j = 11 (rangée sous `mesures/`) | = |
| III-7.6 | 0,51 au-delà de la médiane | 0,50587 (journal du juge 1) ; 0,50587 aussi dans celui du juge 2 | = |
| III-9.7 | 11,96 → 6,08 ; 57 % ; 72 % | depuis le spectre : Σ_{k≥4} λ_k e_k = 11,957 et 6,085 ; 56,7 % ; 1 − Σλ_{1..3}/Σλ = 71,8 % | = |
| III-9.7 | 0,49, 0,61, 0,81 ; 0 % ; 59° ; barre (0,610328, 0,118882, 0,197286) | § 4.2 | = |

Témoin du comparateur (`--casser`, chaque valeur ×1,01) : 30 nombres sur 51 tombent. Les 21 autres sont des petits
entiers, des zéros, ou des nombres que 1 % ne déplace pas à leur arrondi (−0,0004).

### 4.2 III-9.7 refait à la source (`sources_latents.py`, `journaux/sources-latents.json`)

Les lectures sont écrites ici d'après la description des formats :
- GGUF v3 : en-tête, clés, fiches, alignement ;
- MXFP4 de ggml : expert 0 de `blk.8.ffn_gate_exps.weight` ;
- `.sym` de `synonyme-l1-d1-P1/L08-E00.sym` ;
- `routage-L08.bin` et `h-L08.f32` des captures.

La base frontière n'a pas de fichier. Je l'ai prise comme le centre le plus proche de la grandeur E2M1 du code, avec
le signe du code : c'est une hypothèse de lecture, et le témoin T1 la juge.

| Contrôle | Résultat |
|---|---|
| T1 : ‖W − Ŵ‖²_F contre Σ e_k du spectre commité | frontière 40,070895 (écart 1,8·10⁻¹²) ; synonyme 48,005581 (1,1·10⁻¹²) : **l'hypothèse sur la frontière tient** |
| T2 : λ₁ à λ₃ contre le JSON du lot | 1,6·10⁻¹⁵ ; 1 329 entrées |
| rapport ‖ΔW_s x‖/‖ΔW_f x‖ | min **0,49145**, médiane **0,61033**, max **0,80761** ; 0 entrée sous 0,135 |
| angle d'une entrée au plan (u₁, u₂) | médiane **59,34°**, min 41,65° |
| part de la trace hors des trois axes | **71,85 %** |
| projections sur (u₁, u₂) : rapport | médiane 0,1007, **max 0,1585**, 93,4 % sous 0,135 |
| rapport quadratique pondéré | 0,61068726583 (entrées) contre 0,61068726582 (spectre) |
| cassure (centres du synonyme faux de 1 %) | T1 s'écarte de 9,1·10⁻⁴ : les témoins tombent |

Ces valeurs sont **égales au journal du juge latents du second flux au seizième chiffre**, que la figure cite. La
remarque de la note des retouches (« la plage n'est pas refaite entrée par entrée ») est levée : elle l'est ici, par
un troisième chemin.

### 4.3 La régénération (`journaux/regenerer3.json`)

- Les neuf scripts `tome3_*.py` sont relancés dans une copie `git -c core.autocrlf=false archive` de `HEAD`, avec un
  dossier de données vide au départ.
- Résultat : 121 fichiers écrits, **117 égaux au bit**, aucun en trop. Un seul manque : `palette-tome3-journal-casse.
  json`, que seule la cassure écrit.
- Les 4 différents (`palette-tome3-bascules.tex`, `-journal.json`, `-nombres.tex`, `-vues.tex`) sont **égaux au
  contenu**. `tome3_palette.py` les écrit en mode texte, donc avec des fins de ligne CRLF sous Windows ; git les
  normalise en LF. C'était déjà le cas avant la passe (`1482dbe^`). Négligeable, mais un comparateur au bit le verra.
- Témoin du comparateur : un octet ajouté à chaque fichier, 121 comparaisons sur 121 tombent.
- Le dépôt est resté intact : empreintes de `donnees/` égales avant et après.

### 4.4 Les gardes neuves, forcées à faux par mon moyen (`journaux/garde-*.json`)

| Garde | Ma cassure (dans la copie) | Résultat |
|---|---|---|
| GN2 (III-8.5) | un débit du journal du codec réel, 3,46569 → 3,46916 | `tome3_codon` s'arrête |
| GN1 (III-10.1) | `experts_exacts_v12` 768 → 767 | `tome3_juge` s'arrête |
| G7 (III-9.6) | bits de λ = 1 rapprochés de 0,04 | s'arrête : « 45,6 % de la largeur » |
| J5/J6 (III-8.6 bis) | une passe J6 à 799 tronçons | s'arrête |
| compagnon (III-8.6 bis) | la fenêtre 9 du proxy retirée | s'arrête |
| j = 11 (III-9.1 (c)) | le zéro exact mis à −0,01 | s'arrête (4 s'éloignent, 0 à même distance) |
| E1 (III-9.7) | le rapport du journal faux de 6·10⁻⁷ | témoins « TOMBENT », code 1 |
| seconde pointe (III-7.4) | colonne 961 au-dessus de 960 | le script écrit 961 ; **la compilation s'arrête** (`la seconde pointe n'est plus le premier canal…`) ; témoin sur les données du dépôt : 0 erreur |
| DN7 (III-4.8) | boîte des valeurs doublée (1,40 × 0,60 cm) | s'arrête : plus petit jeu −0,108 cm |

Aucune cassure n'a écrit sous `donnees/` du dépôt.

Une réserve sur E1. `tome3_latents.py` écrit ses données et ses témoins avant de sortir en code 1 : quand E1 tombe,
les fichiers de données de la copie sont quand même écrits. C'est le dessin des témoins A1 et B1 du lot, qui précède
la passe, et ce n'est pas un défaut de celle-ci.

## 5. Les graves visés

**GN2, III-8.5 : levé.** (a) dit maintenant « le débit gagné … (codec réel : flux codés par le rANS et décodés
exactement ; aucun fichier `.trc` écrit) », en accord avec (c), et c'est vrai : `tous_exacts` vaut vrai et chaque
tenseur est `exacts`. La garde neuve du script (les quatre colonnes contre le journal) tombe quand on la casse. N8 est
fait et juste (§ 4.1).

**GN1 de la construction, III-10.1 : levé.** « … aucune mesure de KL de la construction ne les a appelés (leur
décodage, lui, est vérifié en valeur : C1, 768 experts sur 768) ». C'est la phrase que le juge demandait, et elle est
vraie : `tailles.json` et, par un second fichier, `journaux/verifier-20b-v12.json` (C1, 768 exacts, 0 faux). Les deux
langues disent la même chose. La phrase de la note F-J4 du juge de la construction reste à barrer (hors de la passe ;
la note des retouches le signale).

**GN1 des latents, III-9.7 : levé.**
- La tête dit maintenant le plan, et la vraie valeur pour les entrées entières : « à 0,61 (médiane ; de 0,49 à
  0,81) ». Le facteur 4,5 qui faisait le grave a disparu.
- Le corps dit « directions projetées » ; « Non montrés » dit l'erreur sur les poids, et que les autres directions
  portent 57 % du gain.
- La quatrième barre, « x », montre 0,61 et sa moustache.
- Tous ces nombres sont refaits à la source (§ 4.2).
- Reste M3 : la tête garde « au plus 0,135 » sans son domaine.

**G7, III-9.6 : levé.**
- Sur la source : (2,6717 − 2,5861) / (2,70 − 2,56) = 61,1 % (61,2 % en pleine précision).
- Au rendu, à 400 dpi, en FR et en EN : cadre de 146,92 à 455,80 pt ; barres à 204,52, 365,98 et 393,34 pt ;
  61,1 %. C'est au-dessus de 50 % dans les deux mesures.
- Aucune étiquette ne couvre une marque, une barre ou un trait de barre : l'étiquette du moteur exact finit à 383 pt,
  10 pt à gauche de la barre de λ = 0, et sa flèche passe 10 pt sous le bas de cette barre (N1 levé).
- La flèche « domine sur les deux axes » traverse sa propre étiquette, comme au second flux (M11).

**G10, III-7.1 : levé.**
- Le trait de la loupe (0,40 pt) ne traverse plus « partitions κ, par tenseur ». Distance aux boîtes précises des
  caractères : 0,52 mm du « r » de « tenseur » en FR, 1,19 mm en EN.
- La note des retouches dit « environ 2 mm » : c'est 0,5 mm en FR (M9).
- Le chemin neuf fait naître M1 : le trait frôle la graduation « 2,644 » de l'encart (0,11 mm de son centre au « 4 »,
  soit 0,04 mm de son bord, en FR et en EN). À 1 600 dpi, il touche le pied du « 4 » sans traverser le nombre.
- La clé dit « pire » (« worse ») : DN8 est fait.

**GD1, le bleu : non levé au critère (b), à un geste près.**
- (a) Tenu : `Accent` ne paraît plus que dans un commentaire des huit fichiers de figures.
- (b) Au rendu, à 200 dpi, la zone de chaque figure (classement au plus proche, § 2.6) : **0 pixel bleu** en III-2.1,
  III-4.8, III-7.2, III-8.1, III-8.2, III-8.4 et III-8.5, en FR et en EN. **III-8.7 en porte 461 (FR) et 473 (EN)**.
  - Ce sont ceux du renvoi « figure 1.2 » (« … en blanc bordé, comme à la `\cref{fig:t3-codon-octets}` »), que la
    passe a ajouté dans la note du panneau (d).
  - hyperref colore les liens en `Accent` (`linkcolor=Accent`, préambule l. 189) : c'est un bleu de plus, au sens
    « renvoi », dans la figure même que GD1 visait.
  - Témoin : III-9.6 compte 1 164 et 1 107 pixels bleus (le synonyme, sens du dictionnaire) ; à la cassure, il tombe.
  - Remède mécanique : `\cref*{…}` (sans lien) ou `\ref`, dans les deux langues.
- (c) Tenu. Les dix paires neuves, refaites par ma colorimétrie (`paires3.py`, Machado recopié de l'article),
  s'écartent de 0,4 au plus de celles du lot, et leurs verdicts sont les mêmes. Neuf tiennent. `black!5` contre le
  papier (4,5 / 4,5) tombe ; la case est séparée par la forme (cadre et croix d'encre), ce que je vois au rendu.
  `VunDeux!15` contre le papier tient de peu en gris (5,6 chez moi, 5,8 chez le lot).
- Je fais tomber GD1 comme le second juge a fait tomber G7, parce que le critère était déclaré. Le défaut est d'un
  autre ordre que celui de GD1 (un lien, pas un codage), et se lève d'un astérisque.

**DN1 (mineur du second flux) : en partie.**
- Gras au rendu, à 260 et 300 dpi : « +0 », « −0 » (III-1.1), « λ = 0 » (III-7.1), « S* » (III-7.4), « 8 → 0 »
  (III-8.1), « 9 … 10 » et « λ = 0 » (III-9.3), « λ = 1 », « λ = 0 » (III-9.6, FR et EN), « H » et « 0,135 » (III-9.7),
  « 32 », « 23 », « 31 » (III-4.8), et les nombres des titres de panneau (« 72 tenseurs, 19 110 297 600 poids »).
- **Restent maigres**, en FR et en EN, « ×1,454 » et « +3,4 » dans la tête de III-8.6, la tête que DN1 citait en
  exemple ; seul le « % » est gras. La note des retouches dit « ×1,454 » gras : c'est faux (M2).
- Aucune police manquante dans les huit journaux.

## 6. Le grave neuf

**GJ1. III-2.1 : le halo blanc de la ligne « tout le modèle » cache le sommet des barres.**
- Le commit `7a40c54` a ajouté, sous la ligne en tirets du coût du modèle entier, un trait blanc de 1,8 pt
  (`\draw[white, line width=1.8pt]`), tracé **après** les barres. GD1 demandait seulement trois gris ; ce trait ne
  l'était pas.
- Il efface une bande de ±0,9 pt autour de 0,1278 (20b) et de 0,1256 (120b), soit ±0,0025 bit par poids (échelle lue
  dans le PDF : 358,8 pt par bit/poids).
- 12 barres sur 72 au 20b, et 25 sur 108 au 120b, ont leur sommet dans cette bande. Elles paraissent toutes s'arrêter
  à son bord bas, à la même hauteur. 22 et 18 autres barres, plus hautes, sont coupées d'une fente blanche.
- Vu à 400 et 500 dpi, en couleur et en gris, en FR et en EN. Au 120b, les barres des couches 4 à 8 finissent toutes
  sous la bande, et quelques-unes laissent un éclat au-dessus.
- Pourquoi grave : c'est une donnée cachée, ma règle déclarée (§ 1.3). La figure dit « plat sauf la couche 0 », et
  le halo efface les écarts de quelques millièmes qui font ce plat.
- Remède : tracer le trait blanc avant les barres, ou le retirer. La ligne en tirets d'encre se lit seule sur des
  barres grises.

## 7. Les mineurs

Nés de la passe (M2 est un reste de DN1, que la passe a laissé) :
- **M1. III-7.1** : le trait neuf de la loupe frôle le « 4 » de la graduation « 2,644 » de l'encart (FR et EN, 0,04 mm
  de bord à bord). Remède : le faire aboutir à 0,60 de la largeur de l'encart, ou au-dessus des graduations.
- **M2. III-8.6, DN1** : « ×1,454 » et « +3,4 » restent maigres dans la tête, en FR et en EN. Ce sont des `\num` en
  mode mathématique, dans `$…$`. Le `\boldmath` et le `detect-weight` de `\Legende` ne les atteignent pas, alors
  qu'ils atteignent les `\num` de texte de III-4.8.
- **M3. III-9.7, la tête** : « Dans les plans des premiers axes de H, où se projettent les entrées …, au plus 0,135 ».
  - La borne ne vaut que dans le cône de ±30° (±24°) qui garde 90 % des projections.
  - Sur toutes les projections, le rapport monte à **0,158** ; 6,6 % sont au-dessus de 0,135 (§ 4.2).
  - Dans les plans entiers, le rapport vaut 0,217 le long de u₂ et 0,269 le long de u₃, et le panneau (c) de la même
    figure le montre.
  - L'ancienne tête disait « loin d'elles, le rapport monte » ; la neuve l'a perdu. Le corps est juste (« pour une
    entrée unité de ce cône »).
  - À écrire : « … dans le cône où se projettent 90 % des entrées, au plus 0,135 ». Le grave GN1 reste levé : le nombre
    des entrées entières est dit, et juste.
- **M4. III-4.8, DN7** : aucune valeur ne touche plus un trait (plus petit jeu 0,035 cm, recalculé du CSV). Mais sur
  les 10 valeurs posées, 4 sont plus près d'une autre arête que de la leur :
  - « 0,089 » de 31–5 est plus près de 31–17 ;
  - « 0,069 » de 31–25 est plus près de 31–15, dont la valeur est 0,077 ;
  - « 0,024 » de 17–18 est plus près de 22–29 ;
  - « 0,023 » de 14–16 est plus près de 16–28.

  Trois autres sont à moins de 1 mm de l'égalité. Une valeur se lit sur la mauvaise arête. Remède : ajouter à la
  règle du script « plus près de son arête que de toute autre ».
- **M5. III-8.5, la légende de (c)** : « carrés gris foncé » (la colonne, `Encre!60`, 767676, L* ≈ 50) contre
  « losanges gris » (F1, 363D44, L* ≈ 26). Les mots de couleur sont inversés ; les formes séparent les deux séries.
  « carrés gris moyen » suffirait.
- **M6. III-7.2** :
  - l'étiquette « synonyme λ = 0 (P1) », reposée pour DN10, couvre de son halo le haut de son propre point ;
  - le bord droit de la bande, en tirets, à ×1,02, double presque le trait plein de x = 1 : deux traits à 0,4 mm,
    dont on ne sait lequel est la bande.

Restes et phrases des notes :
- **M7. Les hachures ont encore deux sens** : hors domaine (III-9.1) et « toit » des octets dans la cascade de
  III-8.6 bis (`codon-figures.tex`, l. 511 : « hachuré : un toit »). DN3 ne citait pas ce second sens ; la passe a
  retiré les deux autres.
- **M8. La note du rôle préambule** : « deux preuves coupées autrement » et « 26.5 rend le ■ extractible » (§ 3.4).
- **M9. La note des retouches** : « à environ 2 mm de “partitions κ, par tenseur” » (0,52 mm en FR) ; « ×1,454 gras »
  (faux, M2) ; « 61,1 % » (61,2 % en pleine précision ; la macro n'est imprimée nulle part, et le script calcule sur
  les bits arrondis à quatre décimales).
- **M10. Reproductibilité au bit** : `tome3_palette.py` écrit quatre fichiers en CRLF (§ 4.3), et `tome3_latents.py`
  écrit ses données avant de sortir en erreur quand un témoin tombe (§ 4.4). Les deux sont antérieurs à la passe.
- **M11. III-9.6** : la flèche « domine sur les deux axes » traverse sa propre étiquette (« les deux », « on both »),
  dont le halo la coupe. C'était déjà le cas au second flux (même croisement relevé dans son PDF) ; le cadre resserré
  la place plus au milieu du texte.

Négligeables vus en chemin, antérieurs : en III-7.1, une ligne de grille du graphique principal passe derrière la
graduation « 2,648 » de l'encart (gris très pâle) ; le bord gauche de la loupe effleure la boîte de « par » (0,2 pt,
invisible).

## 8. Ce qu'une retouche casse ailleurs

- **Les styles communs.** `\Legende` (gras jusque dans les mathématiques) et `t3 titre panneau` servent aux 29
  figures. Les huit PDF compilent avec 0 erreur, 0 boîte trop pleine, 0 renvoi indéfini et 0 police manquante.
  - Pages : 7, 14, 18 et 6, en FR et en EN.
  - Boîtes trop creuses : 12 et 9 (commun), 1 (ronde), 0 (construction), 1 (latents).
  - La version grasse de Libertinus Math (`\setmathfont[version=bold, FakeBold=2.2]`) n'est permise que dans le
    préambule. `legende-tome3.tex` doit donc être chargé avant `\begin{document}` : c'est vrai des pilotes, pas
    encore éprouvé pour un maître du Tome III.
- **Les chevauchements, avant et après.** Avec `croisements_vite.py`, sur les PDF du second flux
  (`memoire/essai/juge2-design/`) et les miens :
  - les croisements partis sont ceux que la passe visait (valeurs de III-4.8, bande de III-7.2, « moyenne » de III-7.1,
    étiquette du moteur exact de III-9.6) ;
  - aucun croisement neuf d'un trait à travers un mot, hors d'une ligne de grille cachée par un halo en III-7.4.
  - GJ1 n'est pas un croisement de texte : c'est une donnée effacée, vue à l'œil.
- **Les couleurs.**
  - Le bleu rendu à l'encre et au gris ne se confond avec aucune voisine (§ 5, GD1 c).
  - En III-8.5, les tirets de la moyenne de la colonne (`Encre!60`) et ceux de F1 (`CouleurFrontiere`) restent séparés
    en gris (ΔE ≈ 22).
  - En III-8.1, les rayons positifs (`Encre!55`) et négatifs (rouge) tiennent en gris (9,2), de peu au regard d'un
    rouge ; leur côté du cercle les sépare aussi.
- **Les données.**
  - Dans `duplication-radial-aretes.csv`, seules les colonnes `xm` et `ym` (place des valeurs) ont changé.
  - Les autres fichiers neufs ou changés sont ceux qu'annoncent les commits.
  - Aucun fichier sous `mesures/`, `genome/pistes/`, `mesures/pistes/`, `outils/pistes/` ni `genome/mimetisme/P3/`
    n'est touché par les sept commits.
- **Les légendes qui nomment une couleur.** Après la passe, « bleu » ne désigne plus que des sens du dictionnaire
  (catégorie A, R1, synonyme, gris bleuté de la frontière). Aucune légende ne nomme plus une hachure ou une bande
  retirée, sauf M5 (mots de couleur de III-8.5).
- **Les tomes I et II.** Les deux correctifs du préambule commun ne changent aucune de leurs pages (§ 3.3).

## 9. Ce qui pourrait être faux

- **Mon indépendance est celle du code, pas de la lecture.** J'ai lu les `git show` des commits, et donc le code neuf
  des scripts (le compte de j = 11, `entrees_reelles`, la règle de cadre), avant d'écrire le mien. Pour III-9.7, j'ai
  lu l'en-tête descriptif des formats dans l'outil du juge 2, pas son code. Une erreur de définition partagée
  passerait ; les témoins à la source (T1, T2) en bornent une partie.
- **La base frontière de `sources_latents.py`** est une hypothèse (centre le plus proche). Elle tient par T1 à
  1,8·10⁻¹² ; une autre fonction du code qui donnerait la même énergie totale me tromperait, ce qui est peu probable
  sur 8 294 400 poids.
- **GJ1 est classé grave par ma règle déclarée** (« une donnée cachée »). Un autre juge pourrait n'y voir qu'un
  défaut de dessin : les barres cachées sont toutes à ±0,0025 bit de la moyenne, et la tête ne cite aucune d'elles.
  Je le classe grave parce que la figure existe pour montrer ces écarts, et parce que la retouche n'était pas demandée.
- **GD1 tombe pour un lien.** Si l'on tient la couleur des renvois pour une convention du texte et non de la figure,
  GD1 est levé. Je l'ai fait tomber parce que mon critère (b) était écrit sans exception.
- **La comparaison des tomes** : mots et boîtes par MuPDF, image à 50 dpi, et seulement six pages à 150 dpi. Un
  écart de moins de 64 niveaux sur moins de 0,05 % d'une page m'échapperait ; le bruit de référence vaut 0.
- **Le rendu est celui de PyMuPDF et de pdftoppm**, pas d'un lecteur de PDF ni d'une impression. M1 (0,04 mm) se
  jouera à l'impression.
- **Les couleurs** : mes seuils sont ceux des juges de design ; la simulation de Machado est une dichromatie
  complète. Ma colorimétrie redonne celle du lot à 0,4 près, avec le même arrondi sur 8 bits du rendu.
- **DN1** est jugé à l'œil pour les mathématiques. L'épaississement (FakeBold) ne change pas le nom de la police, et
  mon outil ne sait pas le lire ; je n'ai agrandi que huit têtes.
- **La lecture des pages** : toutes les figures touchées en FR (couleur, gris, deutéranope, de 95 à 130 dpi), les
  détails de 260 à 1 600 dpi ; en EN, III-7.1, III-8.6, III-9.6 et les légendes de III-8.5, III-10.1 et III-9.7, plus
  les relevés automatiques (croisements, bleu) sur toutes les pages. Un défaut propre à l'anglais ailleurs a pu
  m'échapper.

## 10. Reproduire

```
# depuis la racine du dépôt (Git Bash)
J=outils/genome/tome3/juge3
python -I -X utf8 $J/extraire_correctifs.py memoire/essai/juge3/minimal && cp $J/minimal*-juge3.tex memoire/essai/juge3/minimal/
python -I -X utf8 $J/minimal_variantes.py memoire/essai/juge3/minimal          # cause A, correctif A, témoins
bash $J/construire_tomes.sh "t1-fr t1-en t2-fr t2-en"                           # 9 à 28 min par tome
python -I -X utf8 $J/comparer_pdf.py memoire/fr/troncons-memoire-fr.pdf memoire/essai/juge3/tomes/j3-t1-fr/j3-t1-fr.pdf sortie.json
python -I -X utf8 $J/compiler_pilotes.py                                        # 4 pilotes FR/EN + témoin commun-avant
python -I -X utf8 $J/refaire3.py [--casser]
python -I -X utf8 $J/regenerer3.py BROUILLON [--casser | --garde gn2|gn1|g7|j6|compagnon|j11|e1|pointe]
python -I -X utf8 $J/sources_latents.py [--casser]                              # lit le GGUF, les .sym et les captures ; < 1 Go
python -I -X utf8 $J/gd1_bleu.py [--casser]
python -I -X utf8 $J/paires3.py
python -I -X utf8 $J/croisements_vite.py PDF sortie.json [4-14]
python -I -X utf8 $J/tetes3.py memoire/essai/juge3/pilotes/pilote-tome3-*.pdf
python -I -X utf8 $J/figure3.py PDF PAGE DPI sortie.png ; python -I -X utf8 $J/zoom3.py PDF PAGE DPI x0 y0 x1 y1 sortie.png [couleur,gris,deuter]
```
