# Lot O : ce que le cache d'experts, le moteur et le jalon J1 apportent au mémoire

Rédigé le 2026-10-15 par l'ingénieur du lot O, après le témoin O1. Étiquettes du projet : **[mes.]**
mesuré (outil et journal commités), **[calc.]** calculé, **[dém.]** démontré ici, **[vérif.]**
vérifié par un témoin sans démonstration écrite.

## D'où on part, où on va

- **Au départ** : l'architecture (`decisions/ARCHITECTURE.md` § 5.7) fixe l'API du cache (couture A)
  et un témoin (§ 6.5, O1) : le simulateur du moteur doit égaler celui de l'étude 04 « à l'unité ».
  Deux simulateurs Python existent : `outils/chargement_localite.py` (étude 04, cache **par couche**)
  et `outils/gptoss_localite.py` (cache **global** entre couches, celui de llama.cpp), avec des taux
  publiés sur les traces réelles de gpt-oss-20b.
- **Ce que l'étape établit** : `trc-cache` (Rust, sans dépendance) ; le simulateur `rejouer` est le
  code même du moteur ; **508 comparaisons à l'unité, 0 écart** contre les deux simulateurs Python
  et les taux publiés, sur traces synthétiques et réelles ; cassure : 390 écarts. Trois lemmes
  démontrés (équivalence des règles d'éviction, étage RAM inclusif, falaise du LRU global). Un
  défaut de notre première politique Belady trouvé par le témoin, corrigé, gardé.
- **Ce qui reste** : O2 (modèle), O3 (moteur sur 20b : compte du moteur = `rejouer` sur la trace du
  moteur), O4 (120b, J1). Pour J1+ : une politique consciente du cycle des couches (§ 5 ci-dessous).

## 1. Ce que le travail mérite dans le mémoire

### Schémas (TikZ)

1. **M5, l'automate d'un emplacement VRAM** : Libre → (défaut) EnVol → (`pret`) Présent →
   (éviction, jamais épinglé, jamais en vol) Libre ; à côté, l'étage RAM : une entrée naît d'une
   lecture du disque seulement, et chaque accès à un expert présent la touche (règle 2).
   En J2 les états portent le niveau (Base, Exact).
2. **Le service d'un groupe** (illustration du lemme 1) : une rangée de récence (le plus ancien à
   gauche), les k experts du groupe épinglés (hachurés), deux colonnes « règle P : évincer à chaque
   défaut » et « règle B : servir tout le groupe puis évincer », qui aboutissent au même état.
3. **La falaise** (lemme 3) : le flux cyclique des couches sur un anneau de L secteurs de k accès ;
   l'expert x de la couche ℓ, et les (L − 1)·k accès distincts qui le séparent de sa prochaine
   chance ; un LRU de N emplacements dessiné comme un arc de longueur N.
4. **Les deux étages** : deux piles LRU (V et R ≥ V) sur le même flux, la VRAM incluse dans la RAM à
   chaque frontière de groupe ; flèches « succès VRAM », « défaut RAM » (copie + décodage),
   « défaut disque » (lecture + copie + décodage).

### Structures (tableaux champ par champ)

- `Decision` (Succes, DefautRam, DefautDisque) et ce que l'ordonnanceur fait de chacune ;
- `Compteurs` (`succes_vram + succes_ram + defauts_disque = accès`) ;
- la trace de routage : format texte de l'étude 04 (une ligne par jeton, « | » entre couches,
  « E= »), et ce que `lire_trace` refuse (couches ou k inégaux, identifiant ≥ E, trace vide).

### Graphes (pgfplots)

1. **Succès contre emplacements, LRU et Belady, traces réelles de 20b** (`tous.lecture`,
   `tous.generation`) : `mesures/moteur/O/csv/falaise-20b-dense.csv` (N = 4 à 320). Marquer la
   droite N = (L − 1)·k = 92 et N = L·k = 96. Les points : LRU **0** jusqu'à 92, 9,3 % à 93, 50,3 % à
   96, **50,4 % à 120** (plateau), 69,8 % à 192, 89,6 % à 320 ; Belady 66,4 % à 92, 86,8 % à 192
   (lecture) [mes.].
2. **Succès par trace et par budget** (5 à 40 % de L·E) : `mesures/moteur/O/csv/succes-20b-rejouer.csv`
   (12 traces, 96 lignes) ; c'est la courbe du simulateur que O3 confrontera au compte du moteur.
3. **Le témoin** : un histogramme des écarts par chemin (P1 à P4) en marche normale (0 partout) et
   sous cassure (390 sur 508), tiré de `mesures/moteur/O/journaux/temoin-o1.json` et
   `temoin-o1-casse.json`.

### Tableaux

- Les quatre chemins du témoin O1, leurs comparaisons et leurs écarts (§ 3).
- Les cassures des témoins unitaires (`mesures/moteur/O/journaux/tests-casses.txt`) : neuf
  cassures, toutes tombent, la copie restaurée tient.

## 2. Dérivations

Notations : un **groupe** est la demande d'une couche à un jeton, k identifiants distincts
`G = (x_1, …, x_k)` servis dans cet ordre ; le flux global est la suite des groupes
`(t, 0), (t, 1), …, (t, L−1), (t+1, 0), …` ; un identifiant est (couche, expert) ; `S` est le
contenu du cache, ordonné du plus ancien au plus récent ; N la capacité, N ≥ k.

### Lemme 1 (deux règles d'éviction, un seul résultat) [dém.]

*Règle B* (`g_lru` de gptoss_localite.py) : pour i = 1..k, si `x_i ∈ S` le porter en fin, sinon
l'ajouter en fin ; puis, tant que |S| > N, retirer le plus ancien.
*Règle P* (trc-cache, et `cache_lru` de l'étude 04 pour une couche) : épingler G ; pour i = 1..k,
si `x_i ∈ S` le porter en fin ; sinon, si |S| = N, retirer le plus ancien de S \ G, puis ajouter
`x_i` en fin.

**Énoncé.** Partant du même S₀, les deux règles donnent les mêmes succès, dans le même ordre, et le
même S final (mêmes éléments, même ordre).

**Démonstration.**
1. *Succès.* En B, rien ne sort pendant la boucle : `x_i` est un succès ssi `x_i ∈ S₀`. En P, aucun
   élément de G ne sort (épinglé), et rien n'entre sauf des éléments de G ; les `x_i` étant
   distincts, `x_i` n'a pas été ajouté avant le pas i ; donc `x_i ∈ S` au pas i ssi `x_i ∈ S₀`.
2. *Ordre relatif de S₀ \ G.* Seuls les éléments de G bougent ; les autres gardent leur ordre dans
   les deux règles.
3. *Évictions de P.* Une fois S plein, il le reste ; chaque défaut à S plein retire le plus ancien
   de S \ G, dont l'ordre est celui de S₀ \ G privé des retirés : P retire donc les m plus anciens
   de S₀ \ G, avec m = max(0, |S₀| + d − N), d le nombre de défauts. Il existe toujours un
   candidat : si S était plein et inclus dans G au moment d'un défaut, on aurait N = |S| ≤ k − 1
   (le défaut courant n'est pas encore dans S), contraire à N ≥ k.
4. *Évictions de B.* Après la boucle, tous les éléments de G sont en fin (succès portés, défauts
   ajoutés) ; |S| = |S₀| + d ; les plus anciens sont ceux de S₀ \ G dans leur ordre ; B en retire
   m = |S₀| + d − N ≤ |S₀| + d − k = |S₀ \ G| (car d = k − |G ∩ S₀|) : exactement les m plus anciens
   de S₀ \ G.
5. *Ordre de G.* Dans les deux règles, les éléments de G finissent en queue dans l'ordre de service.
∎

*Belady.* Même démonstration en remplaçant « le plus ancien » par « le plus grand prochain usage,
égalité : le plus petit identifiant » : la clé d'un élément de S₀ \ G ne change pas pendant le
groupe (il n'est pas servi), et les deux règles retirent les m plus grandes clés de S₀ \ G.

*Corollaire.* À chaque frontière de groupe, un LRU à règle P contient les N identifiants distincts
les plus récemment servis (c'est vrai de B, dont l'ordre est l'ordre de récence).

### Lemme 2 (l'étage RAM inclusif égale un cache unique de sa taille) [dém. pour LRU ; vérif. pour Belady]

Règle de trc-cache : l'étage VRAM (V emplacements) décide seul ; l'étage RAM (R entrées) reçoit
`acceder` pour tout accès à un identifiant qu'il contient (succès VRAM compris) et `inserer` pour
toute lecture du disque, et épingle le groupe.

**Énoncé.** Si R ≥ V et la politique est LRU : `succes_vram` = succès d'un LRU seul de V
emplacements, et `succes_vram + succes_ram` = succès d'un LRU seul de R emplacements.

**Démonstration.** La VRAM évolue comme un cache seul (ses décisions ne lisent pas la RAM). Pour la
RAM, il suffit de montrer qu'elle reçoit les mêmes appels qu'un LRU seul de R emplacements, ce qui
ne peut manquer que sur un succès VRAM dont l'identifiant serait absent de la RAM. Récurrence sur les
groupes : si la RAM a évolué comme un LRU seul jusqu'à la frontière, le corollaire du lemme 1 donne
VRAM₀ = les V plus récents ⊆ les R plus récents = RAM₀. Pendant le groupe, un succès VRAM `x_i` est
dans VRAM₀ ⊆ RAM₀, et la RAM n'évince pas les éléments du groupe (épinglés) : `x_i` y est encore,
la RAM fait `acceder` comme le ferait le LRU seul. Un défaut VRAM est, pour la RAM, un succès
(`acceder`) ou un défaut (`inserer` et éviction), comme pour le LRU seul. ∎

Pour Belady, la même conclusion suit de la propriété de pile de MIN (Mattson et al. 1970,
`mattson1970`) ; avec la règle de groupe et l'épinglage, je ne l'ai pas démontrée : le témoin
`deux_etages_egalent_deux_caches_a_pile` la vérifie sur 20 configurations (graines 100 à 103,
(V, R) ∈ {(8, 8), (8, 20), (16, 40), (30, 90), (12, 160)}), et P3 la vérifie pour LRU sur 24
comparaisons. C'est le modèle « deux étages » des plafonds (`h_v = h(f_v)`, `h_r = h(f) − h(f_v)`,
gptoss_localite.py § 3) : le moteur se comporte comme l'équation qui a fixé ses seuils.

### Lemme 3 (la falaise du LRU global) [dém.]

**Énoncé.** Dans le flux cyclique des couches, un LRU global de N ≤ (L − 1)·k emplacements n'a
**aucun succès**, quel que soit le routage.

**Démonstration.** Soit x, de la couche ℓ, servi au groupe (t, ℓ). Sa prochaine demande possible est
au groupe (t+1, ℓ). Entre les deux passent les L − 1 groupes (t, ℓ+1), …, (t, L−1), (t+1, 0), …,
(t+1, ℓ−1), chacun de k identifiants distincts, d'autres couches que ℓ, donc distincts entre eux et
de x : (L − 1)·k identifiants servis après x. À la frontière qui précède (t+1, ℓ), le corollaire du
lemme 1 dit que le cache contient les N plus récents ; x en est exclu dès que N ≤ (L − 1)·k. Par le
point 1 du lemme 1, un identifiant absent au début de son groupe y est un défaut. Tout accès est
donc un défaut. ∎

**Mesuré** [mes.] : sur les traces réelles de gpt-oss-20b (L = 24, k = 4 : (L − 1)·k = 92), LRU
rend 0 succès sur 1 024 224 accès de lecture jusqu'à N = 92 inclus, 95 739 à N = 93
(`falaise-20b-dense.csv`). Belady, à N = 92, en sert 66,4 %. Le témoin unitaire
`falaise_du_lru_global` le vérifie sur des traces collantes (L = 6, k = 4, seuil 20) et tombe sous la
cassure « LRU devient MRU ».

**Au-delà de la falaise, un plateau** [mes.] : de N = 96 = L·k à 120, LRU ne gagne que 0,12 point
(50,26 → 50,37 %, lecture), Belady 6,8 points. Explication (même raisonnement) : les emplacements en
plus de L·k gardent les experts non réutilisés des couches servies depuis le plus longtemps, qui
sortent avant que leur couche ne revienne.

**Ce que cela dit au moteur** [calc.] : pour gpt-oss-120b, (L − 1)·k = 35 × 4 = 140 emplacements de
13 254 144 o, soit **1 855 580 160 o (1,73 Gio)** de VRAM au-dessous desquels LRU ne sert rien. La
VRAM de J1 (≈ 6,5 Go de cache) est bien au-dessus ; mais toute « fenêtre minimale » qui ferait
descendre le cache VRAM sous 1,86 Go avec LRU paierait h = 0, là où l'optimum hors ligne en garde
encore les deux tiers.

### Le témoin O1, posé

Quatre chemins, chacun comparé à l'unité (succès entiers ; le taux Python est reconverti en entier et
l'outil vérifie que `n / accès` redonne le flottant publié au bit près) :

| Chemin | Contre | Traces | Comparaisons | Écarts | Sous cassure |
|---|---|---|---|---|---|
| P1 | `cache_lru`, `cache_belady` de l'étude 04, couche par couche | uniforme, figée, collante (T = 4 000, L = 4, E = 128, k = 8, graine 20261015) ; C ∈ {8, 16, 32, 64} | 96 | 0 | 48 |
| P2 | `g_lru`, `g_belady` (cache global) | les mêmes, entières ; N ∈ {8, 31, 32, 51, 128, 205} | 36 | 0 | 22 |
| P3 | `g_lru` à V et à R (deux étages) | les mêmes ; (V, R) ∈ {(8, 32), (16, 64), (32, 32), (51, 205)} | 24 | 0 | 12 |
| P4 | `g_lru`, `g_belady` recalculés ; taux publiés dans `localite-gpt-oss-20b.json` | 12 traces réelles de 20b (dont `tous.*`), budgets 5 à 40 % | 192 + 160 | 0 | 168 + 140 |

## 3. Ce qui pourrait être faux

- **Le témoin compare des règles, pas des chiffres de vitesse** : il prouve que `rejouer` et les
  simulateurs Python appliquent la même règle ; il ne dit pas que cette règle est celle de
  llama.cpp (elle en diffère par l'ordre des défauts d'un même groupe : 4 et 5 succès d'écart
  mesurés par l'agent de mesure, `g_lru_llama`).
- **Le lemme 2 n'est démontré que pour LRU** ; pour Belady il n'est que vérifié.
- **Belady est un oracle** : il lit l'avenir de la trace ; ses chiffres sont des bornes, pas une
  politique du moteur.
- **La falaise dépend de l'épinglage du groupe et de N ≥ k** ; un cache qui servirait les experts
  d'un jeton dans un autre ordre (préchargement de J1+) déplace le seuil.
- **Les traces de 20b sont celles du chemin de calcul de llama.cpp** ; le moteur produira les
  siennes (O3) : les routages diffèrent un peu selon le chemin de calcul (mesuré par l'agent de
  mesure sur 120b : 81,1 % de choix identiques entre carte et processeur).

## 4. Sources

`memoire/sources/moteur-O.bib` : `belady1966`, `mattson1970` (métadonnées relues sur Crossref le
2026-10-15). Le cache LRU d'experts de Mixtral-offloading est déjà `mixtraloffload2023`
(04-chargement.bib).

---

# Partie II. Étapes O2 à O4 : le moteur (trc-modele, trc-ordo, troncons) et le jalon J1

Rédigé le 2026-10-15 au soir par l'ingénieur du lot O, au fil des mesures. Mêmes étiquettes que la
partie I. Chiffres tirés des journaux commités sous `mesures/moteur/O/journaux/o2`, `o3`, `o4` et des
CSV sous `mesures/moteur/O/csv`.

## D'où on part, où on va (partie II)

- **Au départ** : les briques des autres lots, chacune prouvée seule : le format et son codeur (F :
  C1 sur les deux modèles), le chemin des octets (E : lecteur IOCP, mémoire épinglée, C2), les douze
  noyaux de la passe avant et le décodeur (K : K1 à K3 ; la chaîne K3 tient sous routage imposé), la
  référence f64 et le juge (R : R1, `juge comparer`), le cache et son simulateur (O1). Aucune ne
  faisait tourner un modèle.
- **Ce que la partie II établit** : un programme, `troncons`, qui fait tourner gpt-oss-20b et
  gpt-oss-120b (63,4 Go) sur la machine de Stone avec **384 Mo de mémoire de pointe** (llama.cpp :
  10,9 Go pour le même modèle), **2,18 jetons/s** en génération sur le 120b (llama.cpp : ~~0,568 au
  mieux, × 3,85~~ 0,884 au mieux, `fit -t 16`, × 2,22 : base balayée, partie III § 14.2), des logits **identiques au bit** entre le fichier codé et le fichier brut sur 5 120
  pas (20b), et **six fois plus près** des mathématiques exactes du modèle que llama.cpp (KL 0,0037
  contre 0,0226, 20b) : vrai, **dont la rampe de YaRN**, un choix de modélisation (0,0145 des 0,0226
  de llama.cpp viennent de sa rampe, R-pour-le-memoire § 2.8 ; épreuve J1, constat m5) ; et l'écart
  qui restait à troncons venait tout entier de son cache KV en f16 (partie III, § 13.3).
- **Ce qui reste** : le terme de la fenêtre qui dépend du modèle (C7, écart 3,7 Mo au lieu de
  0,5 Mo déclaré) ; C4 sur le 120b (référence f64 du 120b au lot R) ; le préchargement (J1+) ; le
  préremplissage par flux.

## 5. Ce que la partie II mérite dans le mémoire

### Schémas (TikZ)

1. **M1, le chemin d'un jeton** (§ 5.1 de l'architecture), tel qu'il est construit : trois flux de
   carte (calcul en priorité haute, copie, décodage), le fil de l'hôte, le disque ; les événements
   qui les relient (`routeur ℓ` → hôte ; `copie i` → décodage ; `prêt i` → calcul ; `décodage i` →
   copie suivante dans le même tampon d'arrivée). Source : en-tête de `trc-ordo/src/lib.rs`.
2. **M2, le chronogramme d'une couche, mesuré** : depuis le CSV de `--chronogramme` (dates par
   défaut : soumission, lecture achevée, copie, décodage, routeur, fin de couche), pour un jeton du
   120b ; superposer le modèle du § 5.2. Données : `mesures/moteur/O/csv/chronogramme-120b.csv` (à
   tirer de la passe de chronogramme, voir § 9).
3. **La passe avant d'une couche, noyau par noyau** (la moitié avant le routeur, la boîte aux
   lettres, la moitié après), avec les tampons (x, h, q, k, v, a, o, h₂, logits du routeur, indices,
   poids, g, u, act, s[k]) et leurs tailles pour gpt-oss (d = 2 880, 64 têtes q, 8 têtes kv).
4. **Le témoin O2** : deux colonnes « chaîne K3, couche par couche » et « moteur, jeton par jeton »,
   les mêmes (couche, position) reliées, et l'argument du § 6.2 (même noyau, mêmes entrées).
5. **La fenêtre bornée, décomposée** : une barre empilée par modèle (contexte CUDA, noyaux, fichier
   ouvert, fenêtre épinglée, tampons, cache) depuis `etapes_memoire` (diagnostic D-C7, § 9).

### Structures (tableaux champ par champ)

- `Config` du moteur (§ 5.8 et ses extensions : `emplacements`, `vram_plafond_mio`,
  `longueur_lecture`, `chronogramme`) ;
- `CompteursMoteur` (pas, compteurs du cache, octets lus par sorte, temps de l'hôte par phase, temps
  de carte des copies et décodages) ;
- la boîte aux lettres projetée : mot 0 = séquence (écrit en dernier, barrière système), mots 1 à k =
  indices, k + 1 à 2k = poids (protocole de E0 c, lot E) ;
- la fenêtre épinglée : d · k tampons d'arrivée de `lal` octets (le plus grand tronçon, ou la
  longueur de lecture fixe), l'entrée tiède (mode A), la ligne d'enchâssement (8 Kio), la sortie
  (jeton et logits), le retour (mode témoin) ;
- le journal JSON de `troncons generer|evaluer|disque` (couture J).

### Graphes (pgfplots)

1. **Jetons/s, troncons contre llama.cpp, 120b et 20b** (barres avec intervalle min-max des
   passes) : `csv/o4-2026-10-15-s1-passes.csv` et mesures/gpt-oss.md (base llama.cpp).
2. **Le plancher en série, étage par étage** (barre empilée : disque, PCIe, décodage, GEMV, T0)
   contre le temps mesuré par jeton, 120b et 20b : mêmes CSV.
3. **Mémoire de pointe contre taille du modèle** : deux points troncons (20b 12,1 Go → 380,5 Mo ;
   120b 63,4 Go → 384,2 Mo) contre deux points llama.cpp (9,42 et 10,9 Go) : la pente est la thèse.
4. **KL par position contre la référence f64, troncons et llama.cpp** (20b, 2 550 positions) :
   `journaux/o3/c4-20b-comparer.csv` ; distribution (médianes 7,9·10⁻⁵ contre 2,9·10⁻³).
5. **C3** : un histogramme vide (0 pas différent sur 5 120) n'est pas un graphe ; un tableau suffit.

### Tableaux

- Les critères de J1 (§ 7.1) : mesure, seuil, résultat, verdict (§ 8 ci-dessous).
- Les cassures et ce qu'elles ont fait tomber (O2 : position, experts ; C3 : copie du lot E,
  médiane faussée ; cache : LRU faussé).

## 6. Dérivations

### 6.1 Lemme 4 (l'ordre des trois flux est sûr) [dém.]

**Énoncé.** Dans `Moteur::pas`, aucun emplacement d'expert n'est lu par une GEMV pendant qu'un
décodage l'écrit, et aucun tampon d'arrivée (épinglé ou en VRAM) n'est récrit avant que la copie ou
le décodage qui le lisait soit fini.

**Hypothèses.** (H1) Un flux CUDA exécute ses opérations dans l'ordre où elles sont mises en file, et
une opération ne commence qu'après la fin de la précédente (pas de lancement anticipé programmé). (H2)
`cuStreamWaitEvent(f, e)` fait attendre à toute opération mise ensuite sur f la fin de tout ce que e
a capturé (documentation du pilote, v13.4, consultée le 2026-10-15). (H3) L'hôte ne décide la couche
ℓ (demander, soumettre des lectures, mettre en file copies et décodages) qu'après avoir vu fini
l'événement `routeur ℓ`, enregistré sur le flux de calcul juste après `routeur_topk` de ℓ. (H4) Un
expert demandé par la couche ℓ est épinglé jusqu'à `liberer(ℓ)`, appelé après la mise en file de
`fin_couche(ℓ)` ; la victime d'une éviction n'est jamais épinglée ni en vol (`trc-cache`).

**Démonstration.** (a) Emplacements. Soit s un emplacement décodé pour la couche ℓ' (au jeton t) et
évincé par une demande de la couche ℓ (jeton t' ; (t', ℓ) > (t, ℓ') dans l'ordre du flux). Par (H4),
l'éviction a lieu après `liberer(ℓ')`, donc après la mise en file de `fin_couche(ℓ')` sur le flux de
calcul, et le nouveau décodage dans s est mis en file après la décision de la couche ℓ, donc par (H3)
après que l'hôte a vu fini `routeur ℓ`. Comme `routeur ℓ` est mis en file après `fin_couche(ℓ')`
sur le même flux, (H1) donne : toutes les GEMV qui lisaient s sont finies quand le décodage commence.
Réciproquement, les GEMV de la couche ℓ qui lisent s sont mises en file après
`calcul.attendre(ev_dec[i])` (H2) : elles ne commencent qu'après la fin du décodage. (b) Tampons
d'arrivée. Le tampon i sert au plus une fois par couche ; sa réutilisation à la couche ℓ suit la
décision de ℓ, donc (H3, H1) la fin de `fin_couche` des couches précédentes, qui ont attendu (H2) les
décodages de leurs défauts, qui ont attendu leurs copies. Les attentes `copie.attendre(ev_dec[i])` et
`ev_copie[i].attendre()` avant la lecture rendent ce point vrai sans (H3), ce qui le garde si le
préchargement avance les défauts. ∎

**Coût.** Une synchronisation de l'hôte par couche (36 par jeton sur le 120b) : 18,5 µs chacune sous
charge [mes. E0 c, lot E], soit 0,67 ms par jeton, 0,15 % du temps d'un jeton du 120b (457 ms).

### 6.2 Proposition 5 (jeton par jeton = couche par couche, au bit) [dém. ; vérif. O2]

**Énoncé.** Pour une suite de jetons et des poids donnés, les logits que rend le moteur (un jeton à la
fois, toutes les couches) sont égaux au bit à ceux de la chaîne K3 (une couche à la fois, toutes les
positions), si les deux lancent les mêmes noyaux avec les mêmes arguments numériques.

**Démonstration.** Par la règle de déterminisme (§ 5.6 : aucune addition atomique flottante,
réductions à arbre fixe ne dépendant que des tailles), chaque noyau est une fonction déterministe des
octets qu'il lit et de ses paramètres. On ordonne les calculs par (couche ℓ, position p). Hypothèse de
récurrence : pour tout (ℓ', p') < (ℓ, p) dans l'ordre produit (ℓ' < ℓ, ou ℓ' = ℓ et p' < p), le
résidu x en entrée de (ℓ', p') et la case p' du cache KV de ℓ' sont égaux au bit dans les deux
ordres. En (ℓ, p), les entrées sont : x (sortie de (ℓ − 1, p), égale par récurrence) ; les cases
q ≤ p du cache KV de ℓ, écrites par (ℓ, q), q < p (égales par récurrence) et (ℓ, p) lui-même ; pour une
couche à fenêtre, l'anneau de 128 contient au moment de la lecture exactement les positions
max(0, p − 127) … p dans les deux ordres (la chaîne K3 traite les positions dans l'ordre croissant
au sein d'une couche ; le moteur écrit la case p avant de la lire) ; `ParamsAttention` ne dépend que
de (p, anneau) ; les experts choisis sont ceux du routeur de (ℓ, p), calculé sur des entrées égales,
et leurs emplacements portent les mêmes octets (C1, C2). Les mêmes noyaux rendent donc les mêmes
bits. La sortie (RMSNorm, GEMV Q8_0) ne lit que x de (L − 1, p). ∎

**Vérification** (témoin O2) : 160 lignes sur 160 égales (KL, premier choix, écart relatif), KL
moyenne 7.2794050122285915·10⁻³ au chiffre près ; le chemin G (trc-modele seul, experts du GGUF) 16
sur 16. Les cassures (position décalée de 1 ; experts 0 et 1 échangés à la couche 5) font différer
toutes les lignes. Remarque : les KL de la chaîne sont dominées par cinq bascules de routage (lot K,
D1) ; le témoin O2 ne juge pas la justesse du modèle (c'est C4), il juge que le moteur calcule
**exactement** ce que K a validé.

### 6.3 Proposition 6 (C3 par construction ; le cache n'entre pas dans le calcul) [dém. ; mes.]

**Énoncé.** Si deux fichiers (codé et brut) donnent, pour chaque expert, des emplacements égaux octet
pour octet, le moteur rend les mêmes logits au bit sur toute suite de jetons, quels que soient le
nombre d'emplacements, la politique du cache et l'ordre d'arrivée des lectures.

**Démonstration.** Les GEMV d'un expert lisent son emplacement et h₂ ; l'emplacement porte, au moment
de la lecture, les octets décodés de cet expert (lemme 4), égaux par hypothèse dans les deux fichiers
(C1 pour le codé, `copier_brut` pour le brut, C2 pour le transport). Le cache ne choisit que **où**
est un expert, jamais **quels octets** il porte ; l'ordre `i = 0 … k − 1` de `combiner` est celui du
routeur, pas celui des emplacements. Les autres entrées (résidents, cache KV) ne dépendent pas du
fichier d'experts. Par la proposition 5 (déterminisme), les logits sont égaux. ∎

**Mesure.** 20b : 5 120 pas, 0 empreinte différente, `.kld` égaux octet pour octet, PPL égale
(461,978277060145) ; les deux passes n'avaient pas le même nombre d'emplacements (362 et 361) ni donc
la même suite de défauts : la partie « quel que soit le cache » est observée, pas seulement déduite.
120b : 5 120 pas, 0 empreinte différente, `.kld` égaux, PPL 422,20558522791305 des deux côtés (325 et 326 emplacements).

### 6.4 Proposition 7 (compte du moteur = rejouer) [dém. ; mes.]

Le moteur appelle `trc-cache` dans l'ordre du simulateur : pour chaque jeton t, pour chaque couche ℓ,
`demander(ℓ, G(t, ℓ), t · L + ℓ)`, `pret` sur chaque défaut (dans l'ordre des décisions), puis
`liberer(ℓ)`, et rien d'autre ne touche le cache (pas de préchargement en J1). `rejouer` fait la même
suite sur la trace écrite par le moteur (le même `G(t, ℓ)`, lu dans la boîte aux lettres). Mêmes
appels sur le même état initial ⇒ mêmes compteurs. Mesuré (20b, 5 120 pas, 362 emplacements) :
454 210 succès, 37 310 défauts, 36 948 évictions des deux côtés ; cassure (LRU faussé) : 427 984 /
63 536 / 63 174.

### 6.5 Le plancher en série recalculé dans la séance (C5) [calc. sur mes.]

07 § 1.1 pose le temps d'un jeton servi en série comme la somme des étages. Avec les quantités de la
séance O4 (génération, 120b, passe 1) :

| Étage | Formule | Valeur |
|---|---|---|
| disque | octets de tronçons lus par jeton / débit de D | 0,7072 Go / 1,848 Go/s = **382,7 ms** |
| PCIe | temps de carte des copies par jeton (événements) | **75,8 ms** (59 défauts, 1,28 ms chacun, ≈ 9,4 Go/s) |
| décodage | temps de carte des décodages par jeton | **54,2 ms** (0,92 ms par expert) |
| GEMV | (A + R) / 235 Go/s, A = 1,686 Go résidents, R = 144 × 13,25 Mo | **15,3 ms** |
| T0 | coût fixe (07) | 3,5 ms |
| **somme** | | **531,5 ms → 1,881 jeton/s** ; seuil 0,8 × = **1,505** |

Mesuré : **457 ms par jeton (2,186 j/s)**, sous la somme : les copies et décodages d'une couche se
recouvrent avec les lectures des défauts suivants de la même couche (quatre requêtes en vol). Le
disque seul (D, profondeur 4, tronçons tirés) lit 1,848 Go/s ; le moteur, avec moins de quatre
lectures en vol en moyenne (59 défauts sur 36 couches : 1,6 par couche), en tire 0,707 Go en 457 ms,
1,55 Go/s utiles. Ce qui limite J1 : la profondeur de file par couche (≤ k), que le préchargement
(J1+) doit remplir.

### 6.6 La fenêtre bornée, décomposée (C7) [mes. ; diagnostic en cours]

Proposition A.1 du partisan de A : la mémoire de l'hôte du moteur est `M = M_fixe + d · k · lal +
M_tiède + M_répertoire`, où seul le répertoire croît avec le modèle. Mesuré : 384,2 Mo (120b) contre
380,5 Mo (20b), écart **3,70 Mo**, pour un bruit de passe à passe de 82 Ko : le terme déclaré
(0,5 Mo) est trop petit. Termes qui croissent avec le modèle et que la proposition n'a pas comptés :

| Terme | 120b | 20b | Écart |
|---|---|---|---|
| fenêtre épinglée, d · k · lal, lal = plus grand tronçon arrondi | 12 × 12 251 136 | 12 × 12 144 640 | **1,28 Mo** [calc. : `octets_epingles` 147,84 contre 146,56 Mo] |
| répertoire lu (`Fichier`) + copie des longueurs dans le cache | 2 × 4 608 × 56 o | 2 × 768 × 56 o | 0,43 Mo [calc.] |
| tables (`Fichier`, 256 fréquences par table) | 36 × 3 × 4 | 24 × 3 × 4 | ≈ 0,02 Mo [calc.] |
| trace de routage gardée en mémoire (2 o par choix) | 964 × 144 × 2 | 964 × 96 × 2 | 0,09 Mo [calc.] |
| reste (événements, allocations du pilote, tables des résidents) | | | ≈ 1,9 Mo [à mesurer, D-C7] |

Le premier terme s'annule si la fenêtre a une taille fixe (12 Mio, variante L12) ; les suivants sont
proportionnels à L · E et tiennent sous 1 Mo jusqu'à ≈ 10 000 experts. Le résultat physique reste :
**la mémoire du moteur ne suit pas la taille du modèle** (+1 % pour un modèle 5,2 fois plus gros) ;
ce que le jalon a mal posé, c'est le terme de tolérance.

## 7. Ce qui pourrait être faux (partie II)

- **C5 est jugé contre un plancher qui compte la GEMV au débit de K2** (235 Go/s, autre séance) ; si
  la GEMV réelle du moteur est plus lente, le plancher est optimiste et le seuil trop haut, donc le
  verdict reste valable dans ce sens.
- **Le disque seul (D) est mesuré en tronçons tirés au hasard, profondeur 4** ; le moteur lit dans
  l'ordre de ses défauts, avec moins de requêtes en vol : le débit utile du moteur (1,55 Go/s) n'est
  pas celui de D.
- **C8 ne compte que les lectures du lecteur sans tampon** ; les lectures tamponnées de l'ouverture,
  le vocabulaire et les DLL ne sont pas comptés : une passe tombe de 54 Mo.
- **Le témoin O2 compare à la chaîne K3**, qui partage avec le moteur les noyaux et la référence ; il
  prouve l'identité du calcul, pas sa justesse (c'est C4, contre la référence f64 du lot R, elle-même
  validée contre llama.cpp à G_moteurs près).
- **C4 n'est jugé que sur le 20b** ; sur le 120b, il attend la référence f64 du 120b.
- **Le texte de C12 et la conversation harmony** sont gloutons : ils montrent que le moteur produit un
  texte cohérent, pas sa qualité (le juge, c'est C4).
- **La boîte aux lettres** est lue après l'événement du routeur (variante « evenement » de E0 c) :
  la séquence n'est qu'un témoin ; une écriture tardive de la carte vers la mémoire projetée serait
  vue comme une séquence fausse (erreur fatale), jamais comme des indices faux.

## 8. Le jalon J1, critère par critère (gpt-oss-120b sauf mention)

| Critère | Mesure | Seuil déclaré | Résultat | Verdict |
|---|---|---|---|---|
| C1 format exact | lot F (second chemin) | 0 faux sur 4 608 | 0 faux | TIENT (lot F) |
| C2 transport exact | lot E (E2) et mode témoin du moteur | 0 écart | 0 sur 4 608 (E) ; 546 sur 546 vérifiés par le moteur (20b) | TIENT |
| C3 moteur exact | empreintes des logits f32, codé contre brut, 10 × 512 pas | 0 bit différent | **0 sur 5 120** (20b et 120b), `.kld` égaux octet pour octet | **TIENT** |
| C4 moteur juste (20b) | `juge comparer`, vérité f64 | KL(réf ‖ troncons) ≤ KL(réf ‖ llama.cpp), premier choix ≥ | 0,00368 contre 0,0226 ; 97,18 % contre 89,61 % | **TIENT** (20b) ; 120b en attente de la référence |
| C5 vitesse à la demande | génération, A0, séance O4 | ≥ 0,8 × série = 1,505 j/s | **2,186 et 2,182** | **TIENT** |
| C6 (J1+) contre la base | même invite, 256 jetons | > 2 × bruit + 3 % sur ~~`fit` 0,568~~ la meilleure base mesurée, `fit -t 16` 0,884 (partie III § 14.2) | 2,18 (J1) ; 1,965 (garde, séance de la ronde), préremplissage 27 j/s (flux) | **TIENT** (~~× 3,85~~ **× 2,22** en génération, × 7 en préremplissage) |
| C7 fenêtre bornée | ensemble de travail de pointe | ≤ 1,9 Go ; écart 120b − 20b ≤ 2 × bruit + 0,5 Mo | 384,2 Mo ; écart 3,70 Mo (0,99 à fenêtre fixe) | plafond **TIENT** ; écart **TOMBE** |
| C8 octets lus | PDH contre moteur | ≤ repos × durée + 100 Mo | 3 passes sur 4 | **TOMBE** sur une passe (54 Mo) |
| C10 VRAM | nvidia-smi, 250 ms | ≤ 7 279 Mio | 6 520 à 6 537 | **TIENT** |
| C11 sans perte | PPL codé contre brut | égales | 422,20558522791305 des deux côtés (461,978277060145 sur 20b) | **TIENT** |
| C12 texte | 256 jetons, codé contre brut | égaux | même empreinte e4c6dbacb63a… sur 17 passes (codé, brut, flux, L12, préchargement) | **TIENT** |

## 9. J1+ : ce qui a été construit, mesuré, gardé ou tué

### 9.1 Le préremplissage par flux (gardé)

**Coût, posé.** Dans la boucle de pas, l'invite de P positions lit
`B_boucle = Σ_p Σ_ℓ (1 − h_{p,ℓ}) · k · t` octets (t ≈ 12,03 Mo le tronçon) ; par flux, chaque couche
lit une fois chaque expert demandé par une position au moins : `B_flux = Σ_ℓ |U_ℓ \ V_ℓ| · t`, avec
U_ℓ l'ensemble des experts choisis et V_ℓ ceux déjà en VRAM. Sous un routage uniforme,
`E|U_ℓ| = E · (1 − (1 − k/E)^P)` : pour E = 128, k = 4, P = 708, `(1 − 1/32)^708 = e^{708 · ln(0,96875)}
= e^{−22,5}` : U_ℓ est tout l'ensemble, `B_flux ≤ 36 · 128 · 12,03 Mo = 55,4 Go`, contre
`B_boucle ≈ 708 · 144 · 0,55 · 12,03 Mo ≈ 675 Go` [calc.] : un rapport d'environ 12.
**Mesuré** : 26 s au lieu de 7 min 50 s (× 17,5 : en plus des octets, la boucle paie une
synchronisation par couche et par position, que le flux fait une fois par couche).
**Exactitude** : la proposition 5 (ordre couche par couche = ordre jeton par jeton) ; témoin F :
5 120 empreintes égales sur le 20b, textes du 120b égaux.

### 9.2 Le préchargement par le routeur de la couche suivante (tué)

**Le mécanisme.** Après l'attention de ℓ, le moteur applique à son résidu la norme et le routeur
de ℓ + 1 ; les tronçons prédits absents de la VRAM sont lus d'avance, hors du cache (le compte du
cache reste celui de `rejouer`, les logits ne changent pas : 4 textes égaux).
**Le bilan, chiffré.** Une prédiction juste retire une lecture du chemin critique ; une fausse
ajoute une lecture sur un disque qui limite déjà. Avec p la part des prédictions servies et f la
part du temps d'un jeton que le recouvrement peut cacher (le calcul hors disque) :
gain ≈ f − (1 − p)/p · (part du disque) : ici p = 0,692, octets lus + 34 % (953 contre 710 Mo par
jeton), f ≈ 80/460 = 0,17 : la perte domine. **Mesuré : −11 %** (bruit 1 %). Le mécanisme ne
reviendrait qu'avec p > 0,9 environ ou un disque qui ne limite pas.

### 9.3 Les lectures de 12 Mio (non établi)

+30 % en médiane (2,18 → 2,84 j/s), chaque passe B au-dessus de chaque passe A, mais 21 % de
dispersion entre les deux passes B : la règle (gain > 2 × bruit) n'est pas franchie en quatre passes.
C'est la carte des deux régimes du disque du lot E (12 Mio lit dans le régime rapide, `longueur0` ≈
12,0 Mo dans le lent) ; la décision de l'arbitre sur la longueur des lectures en dépend.

### 9.4 Le chronogramme d'un jeton (figure M2, mesurée)

`mesures/moteur/O/csv/chronogramme-120b.csv` (8 jetons, 1 048 défauts datés). Une couche dont les
quatre experts manquent (pas 8, couche 0) : routeur fini à 0,61 ms ; les quatre lectures soumises à
1,28 / 1,96 / 2,68 / 3,18 ms finissent à 6,86 / 9,81 / 16,14 / 21,17 ms : **le disque les sert l'une
après l'autre** (≈ 5 ms pour 12 Mo, 2,4 Go/s chacune), la profondeur 4 ne les fait pas avancer
ensemble ; chaque copie (≈ 1,0 ms) et chaque décodage (≈ 0,85 ms) suivent la lecture de leur
tronçon sans attendre les autres ; la fin de la couche (23,73 ms) suit le dernier décodage de
0,6 ms. Le dessin à faire : quatre rangées (disque, copie, décodage, calcul) sur 25 ms.

## 10. Ce qui pourrait être faux (ajouts de la fin)

- **La séance 2 a un disque plus lent de 20 %** que la séance 1 (même configuration : 1,75 contre
  2,18 j/s, puis 2,18) ; la cause n'est pas mesurée (température du NVMe illisible sans droits
  d'administrateur). Les verdicts J1+ ne comparent que dans une même série.
- **L12 n'est ni établi ni réfuté** : quatre passes ne suffisent pas devant 21 % de dispersion.
- **Le préchargement est tué pour ce prédicteur et ce disque**, pas en général.
- **La conversation harmony** a été coupée à 1 024 jetons, avant `<|return|>`, et ses caractères
  coupés entre deux jetons sortent mal (défaut d'assemblage du texte, pas du modèle).

---

# Partie III : la ronde de corrections après l'épreuve indépendante (2026-10-16)

## D'où on part, où on va (partie III)

- **Au départ** : le verdict de l'épreuve (`mesures/epreuve-J1.md`) : la spécification est vraie ; C3,
  C4 (20b et 120b), C5, C10, C11, C12 tiennent ; deux constats graves (G1 : une passe figée et muette
  sous charge ; G2 : un `nvidia-smi` orphelin qui tient les tuyaux du pilote), cinq moyens (M1 : la
  production ne garde pas les flux bruts ; M2 : la base de C6 était sous-réglée ; M3 : C8 mesure la
  machine ; M4 : l'écart de C7 tombe ; M5 : le cache KV en f16 décide du premier jeton de C12), six
  mineurs.
- **Ce que la partie III établit** : G1 et G2 corrigés et témoignés (l'ancien binaire tombe, le
  nouveau tient) ; une **garde de production** qui rend toute corruption d'un tronçon ou d'une ligne
  lus une erreur fatale nommée, pour ≈ 5 ms par jeton au chemin critique ; **le cache KV en f32 rend
  troncons égal à la vérité f64 au format près sur le 120b** (KL au plancher du format, 100 % de
  premiers choix, routage égal sur 36 × 708) : tout l'écart mesurable du moteur à la vérité venait de
  l'arrondi f16 du cache ; C8 jugé par l'instrument du processus (écart constant de 19,9 Mo) ; la
  base llama.cpp balayée (§ 14.2).
- **Ce qui reste** : les décisions de l'arbitre (couture N : KV f32 ; critères C4-queue, C7, C8) ;
  la cause première de G1 (non reproduite sous charge, § 14.1).

## 12. Ce que la partie III mérite dans le mémoire

### Schémas (TikZ)
- **M8, la vie d'un tampon d'arrivée au préremplissage par flux** : frise de 12 tampons, lectures
  en vol en couleur, le contre-exemple du lemme 4 bis (la lecture s − 12 encore en vol quand s prend
  le même tampon) et la règle corrigée (le tampon libre suivant).
- **M9, la garde** : du disque au jeton, les quatre fils de hachage en parallèle de la copie et du
  décodage, la barrière `attendre_tout` avant la sortie du jeton ; la table des lignes bâtie à
  l'ouverture.
- **M10, la sortie sur erreur** : avant (erreur, destruction du moteur, `cuEventDestroy` sans fin,
  rien d'écrit ; enfant nvidia-smi qui hérite des tuyaux) et après (erreur écrite, journal d'erreur,
  `TerminateProcess` ; tâche « tuer à la fermeture »).

### Graphes (pgfplots), données commitées
- `mesures/moteur/O/corrections/csv/kv-f16-f32-par-position.csv` : KL(vérité ‖ troncons) par
  position, f16 contre f32, fenêtre 0 du 120b et du 20b, invite de 708 jetons (échelle log ; le f16
  monte avec la position, le f32 reste au plancher du format).
- `csv/vitesse-2026-10-16-passes.csv` : génération par passe (garde, sans garde, KV f32), avec le
  débit du disque de chaque passe (la variance vient du disque, pas de la garde).
- `csv/base-2026-10-16-passes.csv` : la base llama.cpp balayée (§ 14.2).

### Tableaux
- Les constats et leurs corrections (§ 14), chacun avec son témoin, sa cassure, son seuil.

## 13. Dérivations

### 13.1 Lemme 4 bis (les tampons d'arrivée du préremplissage par flux) [dém. ; défaut trouvé, corrigé]

**Énoncé.** Dans `Moteur::preremplir`, aucune lecture du disque n'écrit dans un tampon d'arrivée
épinglé i tant que (a) une autre lecture y écrit encore, (b) la copie vers la carte qui le lisait
n'est pas finie, (c) un hachage de la garde le lit encore.

**Le défaut d'avant la ronde, par un contre-exemple.** Le tampon de la s-ième lecture d'un paquet
était `s mod (d·k)`, d·k = 12, avec au plus `min(d·k, 2 · profondeur) = 8` lectures en vol, confiées
au système par `trc-es` en file, quatre à la fois. Que la lecture s − 12 reste dans le système
(achèvements dans le désordre) pendant que s − 11 … s − 1 passent par les trois autres places et sont
récoltées : la liste locale ne contient plus que s − 12 (longueur 1 < 8), et s est soumise dans le
tampon `s mod 12 = (s − 12) mod 12`, que le disque écrit encore. La copie lancée à la récolte de
s − 12 lit alors un mélange : contrôle des voies faux (erreur fatale, puis la destruction de G1), ou,
si seuls les octets bruts sont touchés, un expert faux sans erreur. Il suffit d'un retard d'environ
11 × 6,6 ms / 3 ≈ 24 ms d'une lecture sur les autres [calc. : 12 Mo à 1,8 Go/s, trois places] ; le
90ᵉ centile d'une lecture à froid relevé par le juge (172 ms) le dépasse.

**La règle corrigée et sa preuve.** Le tampon du tourniquet est pris s'il ne porte aucune lecture
en vol, sinon le suivant qui n'en porte pas (compté : `flux_conflits_evites`). Existence : au moment
du choix, au plus `min(d·k, 2·profondeur) − 1 < d·k` lectures sont en vol. (b) :
`ev_copie[i].attendre()` avant la soumission (la copie de la lecture précédente de i est mise en
file à sa récolte, donc avant). (c) : `Garde::attendre_zone` avant toute soumission. Le tampon VRAM i
n'est récrit qu'après `copie.attendre(ev_dec[i])`. ∎

**Mesuré** : sous la charge de l'épreuve (numpy f64 du 120b en même temps), la passe des 10 fenêtres
du 120b brut finit en 361 s avec **0 conflit** : le cas ne s'est pas produit dans cette passe ; la
règle est démontrée, la cause de G1 reste une hypothèse (§ 14.1).

### 13.2 Proposition 8 (la garde : aucune sortie ne dépend d'un octet non vérifié) [dém. ; mes.]

**Énoncé.** Garde active, le jeton et les logits que rend un pas (ou un préremplissage) ne dépendent
que d'octets lus dont l'empreinte64 égale celle du répertoire (tronçons : octets utiles du niveau 0 ;
lignes d'enchâssement : table bâtie à l'ouverture depuis `token_embd` vérifié en entier), à une
collision du préfixe de 64 bits de SHA-256 près.

**Démonstration.** (1) Le décodeur et la copie ne lisent d'une partie que ses octets utiles (§ 4.8 :
table des flux et flux dans `[0, utiles)` ; le bourrage n'est lu par aucun noyau). (2) Chaque lecture
achevée est confiée à la garde (`utiles[0]`, `empreinte_niveau[0]`) avant toute autre opération sur
son tampon (`apres_lecture`). (3) Aucune lecture n'écrit ce tampon avant la fin du hachage (lemme 4
bis (c), et `soumettre` sur le chemin des pas), donc l'empreinte porte sur les octets que la copie a
lus. (4) `pas` et `preremplir` appellent `attendre_tout` avant de lire le jeton ou les logits ; une
empreinte différente est une erreur. (5) Une entrée tiède servie sans lecture (`DefautRam`) a été
hachée à sa lecture ; une corruption de la RAM après coup n'est pas couverte. (6) Chaque ligne lue est
comparée à sa case avant sa copie vers la carte. Un contenu faux passe avec une probabilité 2⁻⁶⁴ par
vérification, si SHA-256 se comporte comme une fonction aléatoire [hyp. standard]. ∎

**Coût, posé puis mesuré.** Un pas du 120b lit B ≈ 0,71 Go de tronçons. Le débit de l'empreinte est
**mesuré** à 1,07 à 1,10 Go/s par fil, 4,2 à 4,3 Go/s sur quatre (`examples/debit_empreinte.rs` ;
~~2 Go/s par cœur~~ estimé par le juge). Calcul : B / w ≈ 0,65 s de cœur par pas, étalées sur quatre
fils (0,17 s de mur, sous les ≈ 0,5 s d'un pas) ; au chemin critique ne reste que le hachage de la
dernière lecture du pas, au plus 12,25 Mo / 1,07 Go/s ≈ 11,4 ms, moins le travail de carte qui la
suit. **Mesuré** : 5,2 à 5,3 ms d'attente par jeton ; à débit de disque égal (passes 04 et 05 de la
séance, 1,715 et 1,708 Go/s), 1,932 contre 1,900 j/s : **−1,7 %**. Préremplissage par flux : 55 Go
hachés pendant ses 26 s : −2,6 % (non réel). Ouverture : +0,95 s (la table des lignes : 0,615 Go lus
et hachés deux fois). Ensemble de travail : +1,9 Mo (table de 201 088 × 8 o = 1,6 Mo, et les fils), le
même pour les deux modèles.

### 13.3 L'arrondi f16 du cache KV, et pourquoi le f32 rejoint la vérité [calc. ; mes.]

Le f16 a 11 bits de mantisse : arrondi au plus proche, `k̃ = k(1 + δ)`, `|δ| ≤ u₁₆ = 2⁻¹¹ ≈ 4,9·10⁻⁴`.
Pour un score `s = c Σ_d q_d k_d` (c = 1/8, d = 64) : `|s̃ − s| ≤ c u₁₆ Σ_d |q_d k_d|` au premier ordre ;
le produit en f32 ajoute `γ₆₄ = 64 u₃₂ / (1 − 64 u₃₂) ≈ 3,8·10⁻⁶` (u₃₂ = 2⁻²⁴). La sortie de
l'attention hérite d'une erreur relative du même ordre, par les poids du softmax et par `ṽ`. En f32,
la seule erreur qui reste est celle des noyaux, `u₃₂ / u₁₆ = 2⁻¹³ ≈ 1/8 192` fois plus petite. La KL
d'une petite perturbation Δz des logits est du second ordre (`KL ≈ ½ Var_p(Δz)`) : divisée par
≈ 8 192² ≈ 6,7·10⁷, la KL du f16 (3,08·10⁻³ sur le 120b) tomberait vers 5·10⁻¹¹ [calc., ordre de
grandeur, si l'erreur reste linéaire ; les bascules de routage ne le sont pas, mais elles
disparaissent avec elle], bien sous le pas du format à 16 bits par logit (≈ 2,4·10⁻⁴ nat).
**Mesuré** (`corrections/journaux/verdicts-kv-2026-10-16.json`, `m5-ecart-logp-*.json`) :

| | KL moyenne | premier choix | positions de KL > 0,1 | KL p99 | écart max des log p |
|---|---|---|---|---|---|
| 120b, fenêtre 0, KV f16 | 0,00308 | 95,7 % | 0,39 % | 0,0747 | 3,07 nat (12 589 pas) |
| **120b, fenêtre 0, KV f32** | **−0,00048** (plancher du format) | **100 %** | 0 | 2,3·10⁻⁶ | **0,69 pas** |
| 20b, fenêtre 0, KV f16 | 0,00174 | 96,5 % | 0,39 % | 0,0529 | 2,32 nat |
| **20b, fenêtre 0, KV f32** | **−0,00048** | **100 %** | 0 | ≈ 0 | 2,04 pas (254 / 255 sous un pas) |
| 120b, invite, positions 512 à 706, f16 | 0,00963 | — | 2,05 % | 0,196 | — |
| **120b, invite, positions 512 à 706, f32** | **−0,00054** | — | 0 | 3,6·10⁻⁶ | — |

Invite de 708 jetons : argmax égaux à la vérité **708 sur 708** (f16 : 687) ; routage égal sur toutes
les (couche, position) (f16 : 96,9 et 93,1 %) ; **premier jeton de C12 : 1008, celui de la vérité**
(f16 : 313). La KL négative est celle de la référence f64 du lot R contre la même vérité (−4,8·10⁻⁴,
juge § 3.3) : un biais commun du plancher du format, qui fixe le zéro de l'instrument. Conclusion :
**l'arrondi f16 du cache KV portait tout l'écart mesurable entre troncons et les mathématiques exactes
du modèle** ; le juge l'avait borné par en dessous (70 à 77 % des bascules de routage).

**Le coût.** 18 couches pleines × 4 096 positions et 18 anneaux × 128, × 512 valeurs × (k, v) :
`18 × (4 096 + 128) × 2 × 512 × 2 o = 155,7 Mo` en f16, le double en f32 : +155,7 Mo, soit
155,7 / 13,25 = 11,8 emplacements [calc.] ; **mesuré : 326 → 314**. Sur la trace de l'invite, `rejouer`
donne h = 0,459 → 0,442 et 77,9 → 80,4 défauts par jeton (+3,2 % d'octets lus : l'ordre du coût en
vitesse quand le disque limite) [calc. sur trace mesurée]. Préremplissage par flux : −2,1 % (non
réel). La génération de C12 en f32 n'est **pas comparable** au f16 : le texte change (72304d85…, qui
commence par « ... » puis des appels d'outil simulés, comme la sortie gloutonne de llama.cpp ; le f16
tombe dans une boucle « Here is a summary »), et la boucle du f16 relevait son h à 0,590 contre 0,435
en f32 : 2,13 contre 1,50 j/s mesure l'effet du texte, pas le coût du KV f32.

### 13.4 Le plancher de C5 sans passe D froide (m1) [calc. sur mes.]

La séance commence par deux passes D ; la première est jetée (échauffement), le débit de la formule
est celui de la D gardée (1,893 Go/s ; la jetée : 1,874, sans transitoire cette fois, 90ᵉ centile
32,9 ms). Seuils de C5 : 1,45 à 1,52 j/s ; les huit passes T120 tiennent, garde comprise.

### 13.5 C8 par l'instrument du processus (M3) [mes.]

`GetProcessIoCounters` (ReadTransferCount) lu par le pilote sur la poignée après la sortie, contre le
compte du moteur (lecteur `trc-es`, qui compte aussi le chargement des résidents, plus les lectures
tamponnées de l'ouverture, 13,57 Mo) : **écart de 19,92 Mo, constant à l'octet près** sur les six
passes 120b à KV f16 de la séance (dont le vocabulaire lu par `llama.dll`, 12,98 Mo). Le PDH a donné
−10 à +30 Mo dans cette séance chaude, et +2,37 Go dans la première passe froide du juge.
Proposition (arbitre) : **C8 jugé par l'instrument du processus, borne = taille du vocabulaire +
100 Mo** ; le PDH publié, non jugé. La première version du compte du moteur ajoutait deux fois le
chargement des résidents (+1,69 Go, vu dans les journaux de la séance ; corrigé dans le code après).

### 13.6 C7 : une borne à termes nommés (M4) [calc. sur mes. ; non fermée]

Comptes 120b − 20b et coûts unitaires mesurés (`examples/memoire_unitaire.rs`,
`corrections/journaux/m4-couts-unitaires.jsonl`) :

| Terme | Δ compte | coût unitaire | Δ octets |
|---|---|---|---|
| fenêtre : d·k tampons à la taille du plus grand tronçon | 12 × (12 251 136 − 12 144 640) | 1 | 1 277 952 |
| événements horodatés (4 par défaut possible et 2 par couche) | 16 × 12 + 2 × 12 = 216 | 657 à 660 o | ≈ 142 000 |
| allocations de carte (résidents, caches KV) | 156 + 24 = 180 | ≤ 290 o | ≤ 52 000 |
| répertoire tenu deux fois (fichier, tailles du cache) | 2 × 3 840 | 56 o | 430 080 |
| table des résidents, tables rANS | 156 ; 144 | 88 o ; ≈ 560 o | ≈ 94 000 |
| trace (256 pas) | 96 o par pas | — | ≤ 49 000 |
| **somme** | | | **≈ 2,05 Mo** |

Mesuré : 2,94 Mo (juge), 3,30 et 3,70 Mo (lot O). Il reste ≈ 0,9 Mo que ces termes n'expliquent pas
(granularité des pages des petites allocations, tas) : **le modèle à termes nommés n'est pas fermé**.
Même avec lui, `Σ termes + 2 × bruit + 0,5 Mo` = 2,05 + 0,28 + 0,5 = 2,83 Mo laisse la mesure du
juge tomber de 0,11 Mo. Proposition (arbitre) : juger l'écart à **fenêtre de taille fixe**
(`--longueur-lecture 12582912` des deux côtés ; lot O : 0,99 Mo) contre `Σ termes hors fenêtre
(≈ 0,77 Mo) + 2 × bruit + 0,5 Mo` ; le verdict reste « tombe » tant que l'arbitre n'a pas tranché.
Le plafond de 1,9 Go tient avec une marge de cinq (386,8 Mo au plus, garde comprise).

## 14. Les constats, un par un

| Constat | Correction | Témoin | Cassure | Verdict |
|---|---|---|---|---|
| G1 | erreur écrite avant toute destruction, `TerminateProcess` sans détruire, `<journal>.erreur.json`, battement par couche ; tampons d'arrivée du flux corrigés (lemme 4 bis) | `temoin_sortie.py` : erreur écrite, retour en 1,5 à 4,9 s ; sous charge : passe finie, 360 battements | l'ancien binaire : 90 s d'attente des tuyaux | **corrigé** ; cause première non reproduite |
| G2 | `Drop` qui tue l'enfant, tâche « tuer à la fermeture », entrée nulle, poignées standard non héritables | 3 cas, 0 orphelin | ancien binaire : un orphelin par cas | **corrigé** |
| M1 | garde de production | copie O3 : erreur nommée couche 0, expert 30 ; cassures injectées nommées | `--sans-garde` : passes au bout sans erreur | **corrigé**, −1,7 % à disque égal |
| M2 | base balayée | § 14.2 | — | § 14.2 |
| M3 | compteurs d'E/S du processus dans le journal | écart constant 19,92 Mo | — | instrument fait ; critère à l'arbitre |
| M4 | borne à termes nommés posée | — | — | non fermée ; à l'arbitre |
| M5 | KV f32 en option (`--kv-f32`), hors couture N | égal au bit au f16 sur valeurs représentables ; vérité f64 au format près | valeurs non représentables : diffèrent | **mesuré** ; couture N à l'arbitre |
| m1 | D d'échauffement jetée | C5 recalculé | — | fait dans la séance |
| m2 | `build.rs` sans `cmd` | avec et sans vcvars, images égales | ancien `build.rs` : échec reproduit | **corrigé** |
| m3 | mémoire engagée (6,92 à 6,97 Go) et perte de la machine (0,47 à 0,63 Go) publiées | — | — | publiées, non jugées |
| m4, m6 | phrases proposées à l'arbitre (REPRISE-O) | — | — | à l'arbitre |
| m5 | « six fois plus près » requalifié | — | — | fait (§ 15) |

### 14.1 G1 : ce qu'on sait, ce qu'on ne sait pas

Sait : la destruction du moteur pouvait tourner sans fin dans `nvcuda64.dll` (juge, pile nommée) ; le
nouveau binaire ne détruit plus rien sur une erreur, et l'écrit d'abord ; le tourniquet des tampons
d'arrivée pouvait écraser une lecture en vol (lemme 4 bis). Ne sait pas : l'erreur d'origine de la
passe figée. Rejouée sous la même charge, la passe du nouveau binaire finit (0 conflit). L'ancien
binaire sous la même charge : **elle finit aussi** (338 s, `.kld` égal au lot O, `journaux/g1-sous-charge-ancien.json`) : le blocage
de l'épreuve n'est pas reproduit par cette charge ; il dépend d'un ordre d'achèvements ou d'un état de
la machine que deux rejeux n'ont pas retrouvé.

### 14.2 M2 : la base llama.cpp balayée

Séance `base-2026-10-16` (`corrections/journaux/verdicts-base-2026-10-16.json`,
`csv/base-2026-10-16-passes.csv`) : 11 passes, de 08 h 13 à 10 h 06, secteur à chaque passe, aucun
processus étranger, une passe `-t 10` d'échauffement jetée, puis le palindrome déclaré.

| Configuration | génération (j/s) | moyenne | bruit | texte |
|---|---|---|---|---|
| `fit -t 6` (la base publiée) | 0,575 ; 0,573 | 0,574 | 0,4 % | 45a1f638… |
| `fit -t 10` (la meilleure du juge) | 0,675 ; 0,654 | 0,665 | 3,2 % | 45a1f638… |
| `fit -t 12` | 0,913 ; 0,760 | 0,836 | 18,3 % | 45a1f638… |
| **`fit -t 16`** | **0,900 ; 0,867** | **0,884** | 3,7 % | 45a1f638… |
| `-ngl 99 --n-cpu-moe 34 --fit off -t 10` | 0,642 ; 0,638 | 0,640 | 0,6 % | 2bd58359… (celui de `cmoe`) |

La meilleure est `fit -t 16` : elle bat `-t 6` (+54 %), `-t 10` (+33 %) et `--n-cpu-moe 34` (+38 %),
écarts réels ; contre `-t 12` (+5,7 %), l'écart est sous le seuil (2 × 18,3 % + 3 %) : les deux sont
indiscernables. La base publiée sous-estimait llama.cpp de **54 %** (et non de 12 % : le juge n'avait
pas essayé au-delà de 10 fils). Le mécanisme est celui que le juge avait déclaré : sous mmap, chaque
fil en faute de page est une lecture en vol ; 16 fils, c'est une file plus profonde sur le disque.

**C6 recalculé** : troncons (T120g, garde active, 4 passes de la séance vitesse) 1,965 j/s, bruit
11,0 % ; base 0,884 : **× 2,22**, au-delà du seuil (2 × 11,0 % + 3 % = 24,9 %) : **C6 tient**.
~~× 3,85~~ (contre `fit -t 6`, base sous-réglée) ; ~~× 2,79 à 2,89~~ (juge, contre `-t 10`) ;
**× 2,22** contre la meilleure base mesurée à ce jour. La base peut encore être meilleure (au-delà de
16 fils, `--mlock`, d'autres `--n-cpu-moe`) : non balayée. Préremplissage : llama.cpp 3,1 à 4,0 j/s,
troncons 26,6 j/s par flux (× 7).

## 15. Corrections portées dans les textes (barrées, jamais retirées)

- O-pour-le-memoire (« D'où on part (partie II) », § 8) et REPRISE-O (O4) : ~~× 3,85~~ → le rapport
  contre la meilleure base mesurée (§ 14.2).
- « six fois plus près des mathématiques exactes du modèle que llama.cpp » : vrai, **dont la rampe de
  YaRN**, un choix de modélisation (0,0145 des 0,0226 de llama.cpp, lot R ; 0,0143 des 0,0261 sur la
  fenêtre 0, juge) ; et, partie III, l'écart restant de troncons venait tout entier de son cache KV
  en f16.

## 16. Ce qui pourrait être faux (partie III)

- **La cause de G1 n'est pas établie** : le défaut des tampons d'arrivée est démontré possible, pas
  observé (0 conflit sous la charge rejouée).
- **Le coût de la garde est mesuré sur une séance** où le disque a varié de 1,51 à 1,95 Go/s : le
  −1,7 % repose sur une paire à disque égal ; la série dit −12 % sous un bruit de 12 % (non réel).
- **KV f32 = vérité** est mesuré sur une fenêtre de 512 jetons et une invite de 708 (120b) et une
  fenêtre du 20b, pas sur les 10 fenêtres ; la vérité est celle du juge (même lecture du modèle que le
  lot R, juge § 10).
- **La garde suppose SHA-256 sans collision utile** sur 64 bits ; elle ne couvre ni la RAM tiède après
  sa lecture, ni la VRAM.
- **Le modèle à termes nommés de C7** laisse 0,9 Mo inexpliqués.
