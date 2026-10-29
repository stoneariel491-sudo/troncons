# P1 : mémoire du cache à deux échelles (LFU à demi-vie), jugée en génération. Résultat

Rôle : expérimentateur P1. Date : 2026-10-27. Étiquettes : **[mes.]** mesuré, outil et journal commités ;
**[calc.]** calculé ; **[mém.]** de mémoire, non relu ; **[hyp.]** hypothèse dite.
Protocole déclaré avant toute lecture : `protocole.md` (commit c861e8f), seuil de `ec124f5`. Analyses post hoc
déclarées avant calcul : `posthoc-declare.md` (commits 00093d8 et le suivant).

## 0. Verdict

**Au seuil déclaré : TOMBE.** La génération prose-en du 120b donne LFU(h*) − LRU = **−0,0176** (z = −0,8), sous le
seuil de mort de +0,005 [mes.]. Le LFU à demi-vie ne passe donc pas le plan de décodage tel qu'il était posé.

**Mais ce verdict ne répond pas à la question de fond, et je le dis.** Les deux traces de génération du 120b
sont des **boucles du décodage glouton** dans leur seconde moitié : prose-en finit sur 2 jetons distincts par bloc de 32
(dès le jeton 128), wiki sur « Here is a summary » répété (4 à 5 jetons distincts par bloc sur les 100 derniers)
[mes., `figure-blocs.csv`]. Les deux écarts sont des effets de la période de la boucle, de signes opposés (§ 3). La seule
chose que le jugement établit sans réserve : **à 326 emplacements, avec ces deux traces, le LFU(32) ne bat pas le LRU de façon
robuste sur la génération du 120b.** Le gain réel sur une génération de texte qui avance reste **non mesuré**.

Les deux messages à la session principale (piste, puis correction) disent la même chose : le gain existe sur du texte
imposé (lecture), il ne se retrouve pas sur les générations saines du 20b.

## 1. Ce qui a été fait

| pas | outil | résultat |
|---|---|---|
| témoins W0 à W6, avant tout | `cache_p1.py temoins` | tous tiennent ; écart max 2,7e-5 (ETR contre cache2, égalités) |
| grille (LRU, LFU×5, ETR en Python ; mélange×5 en Rust) sur 9 traces × 2 capacités, 120b | `cache_p1.py grille`, `rust_p1.py` | `hits-120b.npz`, `hits-120b-rust.npz` |
| second chemin | `noyau-p1` (Rust) contre Python | 108 séries : écart de succès max **9,8e-6**, 5 jetons différents sur 185 844 (égalités à virgule flottante) |
| jugement au seuil | `cache_p1.py juge 120b 326` | `juge-120b-326.json` : **tombe** |
| post hoc A : fenêtres froides de 256 jetons | `fenetres_p1.py` | `fenetres-120b.json`, `fenetres-20b.json` |
| second chemin des fenêtres | `rust_fenetres_p1.py` | 504 cas fenêtre × politique, écart **0,0000** |

Témoins (`temoins.json`, `temoins.log`) : W0 mon LRU = `cache2.lru1` (écart 0, sur 8 traces) et les repères du
seuil retombent (0,7379 / 0,45279, écart ≤ 4e-6) ; W1 LFU(h = 0,001) = LRU à 0 près ; W2 LFU(∞) = `cache2` « lfu » à 0 près
(0,66268 / 0,42632 retrouvés) ; W3 M(0) = LFU(8), M(1) = LFU(128) à 0 près, ETR contre `cache2` à 2,7e-5 ;
**W4 cassure** (décroissance inversée, h = 8) tombe sous le LRU de plus de 0,02 sur chaque trace testée (**gen-wiki ne passe que de justesse, 0,0269**) ;
W5 la fonction de verdict rend « tient », « tombe », « ouvert », « ouvert » sur les quatre écarts fabriqués ; W6 Belady ≥ toute politique
(marges 0,094 et 0,165).

## 2. Les chiffres du verdict (120b, 326 emplacements, h* = 32 par validation croisée sur les autres genres)

| cas | LRU | LFU(32) | d | σ (blocs de 32) | z | oracle h (non retenu) |
|---|---|---|---|---|---|---|
| génération prose-en | 0,7379 | 0,7204 | **−0,0176** | 0,0213 | −0,8 | h = 8 : +0,0055 |
| génération wiki | 0,3944 | 0,5080 | +0,1136 | 0,0416 | 2,7 | h = 32 : +0,1136 |
| chaîne prose-en (segment de 256 jetons) | 0,7402 | 0,6953 | −0,0449 | 0,0224 | −2,0 | h = 8 : +0,0021 |
| chaîne wiki (segment de 256 jetons) | 0,3957 | 0,4938 | +0,0981 | 0,0493 | 2,0 | h = 32 : +0,0981 |

« Tient » exigerait d ≥ +0,02 et z > 2 dans les quatre cas ; **tombe**, parce que la génération prose-en est sous +0,005. Même le h oracle de prose-en
(h = 8, choisi sur la trace jugée) ne rend que +0,0055 : sur cette trace aucun h ne passe +0,02. Les z de wiki reposent sur 8 blocs ; avec la loi de Student à
7 degrés de liberté, « z > 2 » est moins fort qu'il n'y paraît (la chaîne wiki, z = 1,99, ne le passe de toute façon pas).

À 922 emplacements (descriptif) : h* = 64 ; génération prose-en +0,0058, wiki +0,0099, chaînes −0,0442 et −0,0126 ; rien.

Comparateurs (hors verdict) à 326 : horloge de couches (ETR) : −0,0111 / +0,1272 / −0,0204 / +0,1213 (elle gagne sur wiki, perd sur prose-en comme le
LFU(32)) ; mélange de deux échelles M(w*) : −0,0031 / +0,1042 / −0,0657 / +0,0892. Aucun n'est au seuil sur les quatre cas, et le mélange n'est pas
meilleur que le LFU(32) simple.

**Ce que la chaîne montre** : chauffer le cache par la lecture du même genre **n'aide pas** la génération (LRU : 0,7379 → 0,7402 ; 0,3944 → 0,3957) et
**nuit au LFU sans décroissance** (prose-en : 0,6627 en génération seule, **0,1411** en chaîne ; wiki : 0,4733 → 0,3000). C'est la décroissance qui sauve le
LFU à la frontière lecture / génération (LFU(8) en chaîne : +0,0021 et +0,0856) : les comptes de la lecture sont de la pollution quand la génération passe à
une autre région d'experts (figure 3 : similarité cosinus entre blocs de lecture et de génération de 0,4 à 0,5, et 0,3 pour la queue en boucle) [mes.].

## 3. Pourquoi les deux générations ne décident pas (figure 1)

Succès par bloc de 32 jetons, 326 emplacements [mes., `figure-blocs.csv`] :
- prose-en : LRU 0,41 · 0,38 · 0,43 · 0,73 · 0,97 · 0,99 · 0,99 · 1,00 ; LFU(32) 0,42 · 0,44 · 0,45 · 0,60 · 0,89 · 0,97 · 0,98 · 0,99. Dans la tête de texte
  sain (blocs 0 à 2), LFU(32) est au-dessus (+0,01, +0,06, +0,02). Dès le bloc 4 la boucle tient dans le LRU (2 jetons de 144 accès, 288 emplacements < 326) :
  succès ≈ 1, et les comptes anciens du LFU retardent l'adaptation.
- wiki : la boucle de 5 jetons distincts (période de l'ordre de 10 jetons, environ 1 440 accès) dépasse les 326 emplacements : c'est la pathologie du LRU sur un
  balayage cyclique (succès 0,34) ; tout ce qui a de la fréquence ou une horloge (LFU, ETR) y gagne beaucoup. Rien là-dedans ne dépend d'une demi-vie [hyp. sur la période, non comptée].

Les deux traces correspondent à ce que `mesures/epreuve-J1.md` § 6 note de la sortie du moteur sur l'invite wiki-3000 (« boucle après une centaine de jetons ») :
**les vitesses du moteur sur cette invite portent donc aussi sur une boucle** [hyp. : je n'ai relu que cette phrase du journal du moteur].

## 4. Post hoc : fenêtres froides de textes cohérents (déclarées avant calcul)

Les cinq lectures du 120b découpées en 42 fenêtres disjointes de 256 jetons, cache vide au début de chacune [mes.]. Le 20b : mêmes fenêtres sur ses cinq lectures.

| modèle, capacité | LRU moyen par genre | d̄ = LFU(h*) − LRU | σ | z | fenêtres où LFU gagne | genres ≥ +0,02 |
|---|---|---|---|---|---|---|
| 120b, 326 | 0,35 à 0,51 | **+0,0939** | 0,0029 | 32,8 | 42 / 42 | 5 / 5 (+0,081 à +0,104) |
| 120b, 922 | 0,69 à 0,81 | +0,0314 | 0,0030 | 10,4 | 38 / 42 | 4 / 5 |
| 20b, 217 | 0,67 à 0,78 | +0,0528 | 0,0020 | 27,0 | 42 / 42 | 5 / 5 |
| 20b, 307 | 0,82 à 0,90 | +0,0248 | 0,0014 | 18,2 | 41 / 42 | 5 / 5 |

Avec la règle déclarée (d̄ ≥ +0,02, z > 2, 3 genres sur 5) l'analyse A dirait « tient ». **Mais sa cassure échoue** : la décroissance inversée (h = 8) ne tombe pas
sous le LRU en fenêtre de 256 jetons (elle le dépasse de +0,0174 au 120b, et égale le LRU à 0,0005 près au 20b ; il fallait tomber de plus de 0,02). Lecture : ce n'est
pas la demi-vie que la fenêtre voit. Le **LFU sans décroissance rend déjà +0,0849** (120b, 326) ; la décroissance ajoute **+0,009** (σ 0,0018, z = 5,0) à 326 et
+0,005 à 922. Sur 256 jetons les comptes n'ont pas le temps de vieillir. Ce qui paie là est la **fréquence** (quelques experts chauds) ; la demi-vie ne paie que sur
les lectures longues (code, 326 : LFU(32) 0,445 contre LFU(∞) 0,381) et à la frontière lecture / génération (§ 2).

**Le gain des fenêtres ne se transfère pas aux vraies générations saines du 20b** (post hoc B, `juge-20b-217.json`) : à 217 emplacements, code −0,0015, dialogue +0,0015,
prose-fr +0,0524 (z 2,2), wiki −0,0297 ; à 307 : −0,0049, −0,0020, −0,0118, −0,0197 ; la chaîne est plutôt négative. Le texte imposé d'une lecture et le texte glouton du
modèle n'ont pas la même structure d'usage des experts [hyp. : le texte glouton est plus répétitif, donc plus favorable au LRU ; non mesuré directement].

## 5. Ce qui pourrait être faux

- **Traces de génération en boucle** (§ 3) : le verdict `tombe` repose sur une trace dont la moitié est une boucle de période 1 à 2. Un texte sain de 256 jetons
  peut donner un autre signe. Le verdict est celui du protocole, il n'est pas celui de la question.
- **Deux traces seulement** pour le 120b ; 8 blocs de 32 jetons par trace pour σ ; z non corrigé pour la loi de Student.
- **Cache vide au départ** : le moteur garde un cache chaud entre requêtes ; les taux simulés (0,74) dépassent ceux du moteur (0,59). Tout gain simulé est une borne
  haute avant l'ABBA.
- **Chaîne prose-en simulée** : la génération ne suit pas ce texte de lecture (invite plus courte, autre texte). Seule la chaîne wiki est réelle.
- **Capacités du 20b du protocole (54 et 154) mal choisies** : 54 est sous les 96 accès d'un jeton, le LRU y vaut 0 ; j'ai rapporté 217 et 307 comme post hoc.
- **Le jugement de la demi-vie par la cassure est fragile** : W4 passe de justesse sur gen-wiki (0,0269) et échoue sur les fenêtres froides.
- **W3 imprimait, avant la mesure principale, des taux sur la trace jugée** (M(0) = LFU(8) à 0,7434 sur la génération prose-en : le h oracle +0,0055 m'était connu
  avant le jugement). Cela n'a rien changé au protocole, déjà commité, mais je le dis.
- **Le mélange du 120b vient de noyau-p1 (Rust)**, validé par W3 (Python, aux extrêmes) et par un recoupement sur gen-prose-en (0,7404 des deux côtés), pas par un
  recalcul Python complet (plus d'une minute par trace de lecture sous charge). **Le Rust n'est pas utilisable au 20b** : sa géométrie (36 × 128) est figée dans le code ;
  un premier passage au 20b, faux, a été jeté (fichiers supprimés, jamais commités). Aucun mélange n'est donné pour le 20b.
- **Sources non relues** : LRFU, Hasselmann, Anderson et Schooler, Belady, Aho-Denning-Ullman sont citées de mémoire [mém.] (`memoire/sources/p1.bib`).
- Les durées de la consigne (70 exécutions de 10 à 30 s) étaient sous-estimées pour le mélange ; je l'ai déplacé dans Rust.

## 6. Suite possible

1. **Traces de génération saines du 120b** (au moins 4, après levée du verrou) : invites de conversation à fin naturelle (format harmony, réponse qui s'arrête) ou
   décodage avec pénalité de répétition ; compter d'abord les jetons distincts par bloc (voir `figures_p1.py`). C'est la seule mesure qui puisse rouvrir ou fermer P1.
2. **Si P1 reste ouvert** : le LFU sans décroissance coûte le même compteur et rend +0,085 en fenêtre froide ; la décroissance ne sert qu'aux sessions longues et au
   changement de phase. Piste nouvelle, non mesurée : **fondre les comptes à la frontière** (multiplier tous les comptes par un facteur < 1 au premier jeton de
   génération) plutôt que choisir une demi-vie unique ; la chaîne montre que h = 8 y gagne +0,0856 sur wiki alors que h = ∞ y perd 0,0957.
3. **Avant tout ABBA dans le moteur** : relire le texte de 256 jetons de l'invite wiki-3000 et vérifier la boucle ; sans quoi les vitesses du moteur ne disent rien d'un
   décodage typique.

## 7. Recettes (pour RECETTES.md)

- Un score de cache en espace logarithmique `log c − t·ld` dans un tas à invalidation paresseuse rend le LFU à décroissance en O(log n) par accès ; la décroissance
  infinie se fait en entiers exacts (clé = compte), sinon le départage par virgule flottante change le résultat de 1e-3 (mesuré sur le noyau Rust avec τ = 10¹⁵ ; τ = 10³⁰ règle).
- Départage à score égal par **numéro d'accès** (et non indice de groupe) pour que le témoin W1 (demi-vie → 0 = LRU) tienne exactement.
- Un score non invariant par facteur commun (mélange d'échelles) coûte 1 à 2 minutes par trace de 2 500 jetons en `numpy` sous charge : passer par Rust.
- **L'inversion de la décroissance ne se voit qu'à longue durée** ; à 256 jetons le témoin de cassure échoue et le dit.
- Avant de juger une génération, **compter les jetons distincts par bloc** : deux traces sur deux étaient des boucles.

## 8. Fichiers

Outils : `outils/mimetisme/P1/{cache_p1.py, rust_p1.py, rust_fenetres_p1.py, fenetres_p1.py, figures_p1.py, noyau-p1/}`.
Mesures : `mesures/mimetisme/P1/` (`temoins.json`, `hits-*.npz`, `juge-*.json`, `rust-120b.json`, `fenetres-*.{json,csv}`, `figure-*.csv`, journaux).
Figures : `genome/mimetisme/P1/figures/p1-{blocs-generations,fenetres-froides,topologie-usages}.png`. Note pour le mémoire : `pour-le-memoire.md`.
