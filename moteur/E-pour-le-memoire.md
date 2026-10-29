# Lot E pour le mémoire (Tome II, « le système ») : le chemin des octets

Ce fichier dit ce que le travail du lot E mérite dans le Tome II : schémas, structures au bit près,
dérivations en entier, graphes de bancs et leurs données, listings, et ce qui pourrait être faux.
Les chiffres viennent des journaux commités sous `mesures/moteur/E/journaux/` et des CSV de
`mesures/moteur/E/csv/` (régénérés par `mesures/moteur/E/analyse_e0.py`) ; les sources sont dans
`memoire/sources/moteur-E.bib`. Étiquettes du projet : [mes.], [calc.], [litt.], [hyp.], [est.].

## 0. D'où on part, où on va

**Au départ** : la décision (ARCHITECTURE.md § 2) tenait le chemin des octets pour réalisable sous
CUDA sur la foi de trois mesures faites par d'autres moyens : la DMA à 12,2 Go/s depuis un tampon
hôte de Vulkan [mes. 01], la mémoire épinglée +21 % et le recouvrement copie-calcul par le runtime
CUDA de llama.cpp appelé par ctypes [mes. 04], le disque à 2,58 Go/s en blocs de 4 Mio [mes. 01].
Trois choses n'étaient mesurées nulle part : épingler plusieurs Go sous WDDM sur une machine de
16 Go partagée, lire le disque sans tampon *directement* dans la mémoire que lit la DMA, et ce que
coûte une lecture du routeur par l'hôte à chaque couche (§ 10 de l'architecture).

**Ce que le lot établit** : deux crates à nous, sans aucune bibliothèque de CUDA liée (`trc-cuda`,
l'API du pilote chargée à l'exécution ; `trc-es`, la lecture sans tampon par port de complétion), et
les trois essais E0 qui répondent aux trois questions, chacun avec témoin, cassure et seuil déclaré.
Un fait de la machine que personne n'avait relevé : **la carte n'a qu'un moteur de copie sous
WDDM** (`CU_DEVICE_ATTRIBUTE_ASYNC_ENGINE_COUNT` = 1) [mes.].

~~**Ce qui reste** : E2, le banc de bout en bout (tous les experts du 20b, disque → VRAM décodés),
qui attend le décodeur du lot K (K1) et le format du lot F.~~ (2026-10-15, 21 h 13 à 21 h 35) **E2 est
fait** : le chemin de bout en bout transporte les 768 experts exactement (C2), sa cassure tombe là où
elle doit, et son débit tombe de 5,6 % sous le seuil, par une cause que personne n'avait vue : sur
cette machine, **le débit d'une lecture sans tampon dépend de sa seule longueur**, en deux régimes,
et toutes les longueurs de tronçon du 20b sont dans un régime lent. Lire une longueur rapide fixe
(12 Mio) rend ×1,335 (§ 3, D16 ; § 6). **Ce qui reste** : la décision de l'arbitre sur la longueur
des lectures, E2 sur le 120b, le mécanisme des deux régimes.

## 1. Schémas à dessiner (TikZ)

- **E-S1, la pile du chemin des octets.** De haut en bas : `troncons` (ordonnanceur) ; `trc-es`
  (`CreateFileW` + `FILE_FLAG_NO_BUFFERING | FILE_FLAG_OVERLAPPED`, `ReadFile`, port IOCP) et
  `trc-cuda` (`nvcuda.dll` par `LoadLibraryExW` dans System32) ; sous Windows : NTFS, filtre
  `fvevol` (BitLocker, déchiffrement logiciel, BypassIO refusé [mes. 01]), pilote `iaStor` (VMD),
  NVMe ; et pilote WDDM, moteur de copie unique, SM de la carte. Les flèches portent les débits
  mesurés (disque, DMA) et la RAM épinglée au milieu : c'est la même page physique que le disque
  écrit et que la carte lit.
- **E-S2, l'automate d'une requête de `trc-es`.** États : *soumise* → *en file* (si `profondeur`
  lectures sont déjà confiées) ou *confiée* (`ReadFile` rendu `TRUE` ou `ERROR_IO_PENDING`) →
  *achevée* (paquet dans le port, FIFO) → *récoltée* (`GetQueuedCompletionStatusEx`, l'OVERLAPPED
  est rendu, l'`Achevement` publié, une requête de la file est confiée). Transitions d'erreur :
  échec synchrone (aucun paquet ne viendra, l'erreur rendue tout de suite) ; échec au lancement
  différé (un `Achevement` avec son code). Abandon du lecteur : *confiée* → `CancelIoEx` → paquet →
  libérée ; l'OVERLAPPED n'est jamais libéré avant son paquet.
- **E-S3, les durées de vie dans `trc-cuda`.** Graphe des références comptées : `Interne`
  (contexte primaire retenu) au centre ; `Contexte`, `Flux`, `Evenement`, `MemoireCarte`,
  `HoteEpingle`, `ModuleInterne` le tiennent ; `Fonction` tient `ModuleInterne`. Le contexte n'est
  relâché qu'après le dernier objet ; le témoin `duree_de_vie_du_contexte` l'exerce.
- **E-S4, chronogramme de l'essai E0(c).** Deux lignes de temps, hôte et carte, pour trois couches :
  en `asynchrone`, l'hôte lance les 72 noyaux d'avance et la carte les enchaîne sans trou ; en
  synchrone, chaque couche montre le trou `d_sig + d_hôte + d_lanc` entre la fin du routeur et le
  début de l'expert (§ 3, D2). Les durées des noyaux (50 et 250 µs) et le trou mesuré sont reportés à
  l'échelle.
- **E-S5, le moteur de copie unique.** Une file FIFO unique pour les copies hôte → carte et carte →
  hôte, les SM à côté : une copie de retour (journal du mode témoin, logits) attend derrière les
  tronçons en vol ; la boîte aux lettres, écrite par un noyau dans la mémoire projetée, ne passe
  **pas** par cette file (§ 3, D5).
- **E-S6, la boîte aux lettres au bit près** (§ 2.1), avec l'ordre des écritures du noyau et des
  lectures de l'hôte.
- **E-S7, la fenêtre d'E2 et la vie d'un emplacement.** Six emplacements, chacun = (tranche épinglée
  de 12 144 640 o, tampon d'arrivée en VRAM de même taille, emplacement SoA de 13 254 144 o, quatre
  événements). Automate : *libre* → *lecture* (requête IOCP de `longueur0`, ou de 12 Mio en E2-V12)
  → *carte* (copie sur le flux de copie, événement « copie finie », attente par le flux de
  décodage, deux noyaux de K1, événement « décodé ») → *libre* quand l'hôte voit l'événement
  « décodé » (et, en passe témoin, après le retour de l'emplacement et les deux empreintes). Les
  compteurs de contrôle sont un tableau de 768 × 16 o en VRAM, indexé par la place de l'expert dans
  le répertoire, relu une fois en fin de passe.
- **E-S8, le chronogramme réel d'E2** (à tirer de `chrono-A-*.csv`, voir E-G9) : quatre lignes
  (disque, moteur de copie, flux de décodage, hôte), chaque tronçon un rectangle de sa soumission à
  son achèvement sur le disque, puis sa copie (≈ 0,95 ms) et son décodage (≈ 0,35 ms) ; il montre que
  la copie et le décodage tiennent dans l'ombre des quatre lectures en vol (≈ 23 ms chacune en
  lecture de `longueur0`, ≈ 16 ms en 12 Mio).
- **E-S9, la table des détections de la cassure** (à tirer de `csv/e2-2026-10-15-seance1-cassure.csv`) :
  douze lignes (une par sorte de région), quatre colonnes de contrôles (empreinte de partie,
  empreinte d'origine, compteurs de la carte en témoin, en production), cases pleines ou vides ; elle
  dit d'un regard ce que chaque contrôle garde (D14).

## 2. Structures au bit près

### 2.1 La boîte aux lettres d'une couche (mémoire hôte épinglée et projetée)

Une case de 64 octets par couche, 36 cases (2 304 octets, dans une page de 4 096) :

| Octets | Mot | Contenu | Écrit par |
|---|---|---|---|
| 0–3 | 0 | numéro de séquence `s = jeton · 64 + couche + 1` (u32) | noyau, **en dernier**, après `__threadfence_system()` |
| 4–19 | 1–4 | les 4 indices d'experts (u32, 0 à 127) | noyau |
| 20–35 | 5–8 | les 4 poids (bits IEEE-754 de f32, somme 1) | noyau |
| 36–63 | 9–15 | zéros | — |

Le numéro ne revient jamais pour un même jeton (le jeton est un compteur global), si bien qu'une case
lue avant l'écriture porte toujours un numéro faux : c'est ce que voit la cassure `sans_synchro`.
(Le moteur du lot O écrira sa propre boîte, couture N, § 5.6 : `routeur_topk` « copiés dans la boîte
aux lettres projetée » ; celle-ci est celle de l'essai.)

### 2.2 Une lecture de `trc-es` en mémoire

`Vol` (`#[repr(C)]`, en tas, adresse stable jusqu'à la récolte) : `OVERLAPPED` (32 octets sur x64 :
`Internal` u64, le NTSTATUS ; `InternalHigh` u64, les octets transférés ; `Offset` u32 et
`OffsetHigh` u32, le décalage de 64 bits ; `hEvent`, nul) en tête, puis `jeton` u64, puis l'instant de
remise au système. L'adresse de l'OVERLAPPED que rend le port est celle du `Vol` : clé de la table des
lectures confiées.

`Requete` = (jeton u64, décalage u64, longueur u32, destination *mut u8), les trois derniers
multiples de 4 096 ; `Achevement` = (jeton u64, octets u32, erreur Option<u32> (code Windows),
durée µs u32 de la remise au système à la récolte).

### 2.3 L'API de `trc-cuda` (couture C) et ses extensions

Tableau à reproduire : chaque fonction gelée du § 5.5, l'appel du pilote qu'elle fait (nom exporté
exact, ex. `cuMemcpyHtoDAsync_v2`), ses vérifications avant l'appel ; puis les extensions ajoutées
sans changer l'existant : `Contexte::nouveau_avec(Attente)`, `attente_effective`, `attribut`,
`synchroniser`, `nom`, `version_pilote` ; `Flux::fini`, `priorite` ; `Evenement::nouveau_bloquant` ;
`MemoireCarte::tout`, `octets`, `remplir` ; `HoteEpingle::pointeur`, `octets`, `lire_volatil_u32` ;
`copier_carte_carte` ; `Fonction::partagee_max`.

## 3. Dérivations (à écrire en entier)

**D1, le seuil de l'essai (c).** Le temps disque d'un jeton du 120b dans le scénario LRU calé vaut
157 ms (07 § 3.3, partisan-A étape 0b). On admet que la lecture du routeur coûte au plus 10 % de ce
temps : 0,1 × 157 = **15,7 ms par jeton**, soit, pour L = 36 couches, **436 µs par synchronisation**.
Au-delà, `t0` cesse d'être négligeable et devient un étage de l'équation du jeton (K4).

**D2, le modèle du coût d'une synchronisation.** Soit, pour une couche, `t_r` la durée du routeur
sur la carte, `t_e` celle des experts. Sans attente de l'hôte, les lancements sont en file d'avance :
la carte enchaîne, `T_async = L (t_r + t_e) + ε`, ε le temps du premier lancement. Avec une lecture
du routeur par couche, l'expert ne peut être lancé qu'après que l'hôte a vu la fin du routeur :
`T_sync = L (t_r + d_sig + d_hôte + d_lanc + t_e) + ε'`, où `d_sig` est le délai entre la fin du
noyau et le moment où l'hôte l'observe (événement ou boîte), `d_hôte` le travail de l'hôte (lire 4
indices, préparer les arguments), `d_lanc` le délai entre l'appel `cuLaunchKernel` et le début du
noyau sur la carte. D'où le coût par jeton, `T_sync − T_async = L · s`, `s = d_sig + d_hôte +
d_lanc`, indépendant de `t_r` et `t_e` tant que la carte ne recouvre rien d'autre : c'est pourquoi
l'essai mesure deux charges (0/0 et 50/250 µs) et doit trouver le même coût aux deux (témoin du
modèle). La variante `bloquant` ajoute le réveil d'un fil endormi par le système à `d_sig`.

**D2 bis, ce que la mesure a changé à D2** [mes. séance 3]. Le témoin de D2 (même coût aux deux
charges) **tombe** : 5,1 µs par synchronisation à vide contre 18,5 sous charge (`evenement`),
rapports 3,6 à 4,8 selon la variante. Le terme oublié est le débit des lancements. À vide, la base
asynchrone n'est pas `L (t_r + t_e) + ε` mais `max(L (t_r + t_e), 2L · ℓ)`, où `ℓ` est l'intervalle
minimal entre deux lancements vus par la carte : mesuré 0,831 ms pour 72 lancements, `ℓ ≈ 11,5 µs`,
bien au-dessus de `t_r + t_e ≈ 0`. La carte attend déjà les lancements ; la synchronisation n'ajoute
que la part de `d_sig + d_hôte` qui ne se cache pas derrière `ℓ`. Sous charge (`t_r + t_e = 300 µs ≫
2ℓ`), la carte est saturée en asynchrone, et la synchronisation expose la chaîne entière :
`s ≈ d_sig + d_hôte + d_lanc`, avec `d_lanc ≥ ℓ`. Estimation : `s_charge ≈ s_vide + ℓ ≈ 5,1 + 11,5
= 16,6 µs` contre 18,5 mesurés (écart 10 %, [hyp.] : `d_lanc` ne se mesure pas seul ici). Le cas qui
compte pour gpt-oss est le second (un expert lit 13 Mo : des centaines de µs), d'où le seuil jugé
sous charge : 36 × 18,5 µs = 0,666 ms par jeton, 23 fois sous 15,7 ms.

**D3, la loi de Little pour le lecteur.** Pour un système stable, débit = (requêtes en vol) ×
(taille) / (latence) : `X = q · b / R`. Avec `q` = 4, `b` = 12 Mio, et la durée médiane `R`
d'une lecture (journal, `duree_us_mediane`), le débit prédit doit retrouver le débit mesuré par le
mur ; c'est le second chemin du débit du disque (à poser avec les valeurs de la séance). Elle dit
aussi pourquoi la profondeur 1 perd : `q` = 1 laisse le disque inoccupé pendant la remise et la
récolte de chaque lecture.

**D4, la PCIe ne limite pas un tronçon.** Un tronçon de 12 Mio passe la DMA en `b / B_pcie` et le
disque en `b / B_disque` ; le rapport des deux temps est `B_disque / B_pcie` (à poser avec les
débits de la séance ; repère : 2,58 / 12,2 = 0,21 [mes. 01]). Tant qu'il reste sous 1, la copie se
cache entière derrière la lecture suivante (le moteur de copie est libre 79 % du temps).

**D5, le moteur de copie unique.** Avec un seul moteur, les copies des deux sens forment une seule
file FIFO. Une copie carte → hôte soumise derrière `k` tronçons en vol attend au pire `k · b /
B_pcie` ; pour `k` = 4 tronçons de 12 Mio à 11 Go/s, ≈ 4,6 ms. Conséquences : (i) le mode témoin
(`--temoin`, chaque expert décodé recopié vers l'hôte, § 4.12) ralentit le chemin des tronçons et ne
se chronomètre pas ; (ii) les logits d'un pas (≈ 201 k × 4 o ≈ 0,8 Mo, ≈ 73 µs) attendent derrière les
tronçons ; (iii) la boîte aux lettres, écrite par un noyau dans la mémoire projetée, échappe à la
file. Le témoin d'ordre de `trc-cuda` en a fait la preuve à son insu : une course entre une copie
aller et une copie retour sur deux flux ne s'est jamais vue en 20 essais (même file), alors que la
course entre la copie et un noyau se voit au premier essai (66 393 069 octets sur 67 108 864 lus
avant leur arrivée) [mes.].

**D6, la fenêtre épinglée du mode A0.** `d · k` tampons d'arrivée de la taille du plus grand
tronçon (§ 5.8) : 3 × 4 × 12 144 640 = 145 735 680 o ≈ 0,146 Go, plus la boîte (4 096 o) et une ligne
d'enchâssement (8 192 o). Comparée aux tailles de l'essai (a), elle dit quelle part de la RAM le mode
A0 verrouille, et ce que le mode A (cache tiède) peut demander de plus.

**D7, l'exclusion dans `trc-es`.** Invariant : toute adresse d'OVERLAPPED que rend le port est dans
la table des lectures confiées au moment où la récolte la cherche. Preuve : `ReadFile` et l'insertion
dans la table se font sous le même verrou ; la récolte attend le port hors du verrou, puis prend le
verrou avant toute recherche ; donc si le paquet arrive avant l'insertion, la récolte attend le
verrou que tient le lanceur, qui insère avant de le rendre. ∎ Le même raisonnement fonde l'abandon :
l'OVERLAPPED appartient au système de `ReadFile` jusqu'au retrait de son paquet (documentation des
ports [litt. microsoft2025iocp]), d'où l'annulation suivie de l'attente de chaque paquet.

**D8, la visibilité de la boîte.** Le noyau écrit indices et poids, puis `__threadfence_system()`
(PTX `membar.sys` : toute écriture antérieure du fil est visible de tout observateur, l'hôte compris,
avant toute écriture postérieure), puis le numéro. L'hôte lit le numéro par une lecture volatile,
puis les indices ; sur x86 (ordre TSO), deux lectures ne se réordonnent pas entre elles. Donc un hôte
qui lit le bon numéro lit les indices de ce numéro. ∎ Le témoin `sequences_absentes` = 0 et
`faux_hote` = 0 de toutes les variantes synchrones le vérifie ; la cassure le montre nécessaire.

**D9, les octets étrangers par différence de deux relevés bruts.** Le compteur « Disk Read
Bytes/sec » est de type `PERF_COUNTER_BULK_COUNT` : sa donnée brute `N` est le nombre cumulé
d'octets lus par toute la machine, et sa valeur affichée `(N₁ − N₀) / ((D₁ − D₀) / F)`
[litt. microsoft2025countervalues]. Les octets d'une passe sont donc exactement `N₁ − N₀`, relevés
au début et à la fin de la passe, sans intégrer de débit échantillonné (le chemin du lot R intègre le
débit formaté : les deux sont indépendants). Octets étrangers `E = (N₁ − N₀) − b · n`, avec `b · n`
nos octets livrés. Témoin gratuit : `N₁ − N₀ ≥ b · n` (nos lectures sans tampon vont au disque, le
compteur doit les voir) ; un compteur qui ne voit pas le disque, ou une lecture servie par un cache,
le ferait tomber.

**D10, le seuil de propreté d'une passe.** Le bruit de lecture admis par le § 6.5 est 10 % du débit
de référence (2,58 Go/s [mes. 01]) ; un autre programme qui lit `E / T` octets par seconde pendant la
passe prend au disque au plus cette part de sa bande. On déclare la passe propre si
`E / T ≤ 0,1 × 2,58 = 0,26 Go/s` : la charge étrangère reste dans le bruit déjà admis. Ce n'est pas
une correction du débit (on ne retranche rien), c'est un tri : une passe sale ne juge rien, et une
série sans deux passes A propres est « non jugée », jamais « tombée ».

### E2 : le chemin de bout en bout (dérivations écrites avant la mesure)

**D11, le seuil d'E2.** Le disque sert `B_d` octets de tronçons par seconde ; chaque tronçon de
`b` octets rend un expert de `o` octets d'origine (13 253 760 pour gpt-oss) ; le débit d'experts
servis, à la taille d'origine, vaut donc `X_servi = B_d · o / b̄ = B_d · r`, avec `r = o / b̄` le
rapport de compression moyen. La spécification prend `B_d = 2,58 Go/s` [mes. 01], `r = r(F1) =
13 253 760 / 11 990 368 = 1,105 367` (§ 4.14) et la règle `0,8 = 1 − 2 × 10 %` : seuil `0,8 × 2,58 ×
1,105 367 = 2,281 48 Go/s`. Le fichier réel a `b̄ = 12 013 664 o` (r = 1,103 224) : le même seuil
demande alors `2,281 48 / 1,103 224 = 2,068 Go/s` de tronçons, 0,2 % au-dessus du seuil d'E1
(2,064) ; les deux étapes jugent presque le même disque, l'une seul, l'autre au bout du chemin.

**D12, le débit d'une chaîne d'étages et le nombre d'emplacements.** Trois étages en série, chacun
traversé par chaque tronçon : le disque (q lectures en vol, débit `B_d` mesuré à cette profondeur),
le moteur de copie (un seul, D5 : une copie à la fois, `t_c = b / B_c`), le flux de décodage (un
expert à la fois en J1, `t_k`). En régime établi, un étage qui sert chaque objet ne peut en sortir
plus vite que sa capacité : `X ≤ min(B_d, B_c, b / t_k)` (en octets de tronçons par seconde). Pour que
l'égalité soit atteinte avec le disque pour goulot, il faut que le disque ait toujours q lectures en
vol, donc qu'un emplacement libre attende chaque achèvement. Un emplacement est tenu de la
soumission de sa lecture à la fin de son décodage ; par la loi de Little, le nombre moyen
d'emplacements occupés hors du disque vaut `N_hors = (X / b) · (t_c + t_k + δ)`, δ le délai de
l'hôte entre la fin du décodage et sa remise en service (sondage des événements, sommeil de 100 µs).
Avec `X / b ≈ 2,44·10⁹ / 1,2·10⁷ ≈ 203` tronçons par seconde, `t_c ≈ 0,96 ms`, `t_k ≈ 0,35 à
0,40 ms`, δ de l'ordre de 0,1 à 0,5 ms : `N_hors ≈ 203 × 1,8·10⁻³ ≈ 0,37`. Il faut donc `S ≥ q +
⌈N_hors⌉ = q + 1` emplacements en moyenne ; on en prend `q + 2` = 6 pour les fluctuations
(une lecture lente du p90 ne doit pas priver les autres de place). Fenêtre épinglée : 6 × 12 144 640
= 72,9 Mo ; VRAM : 6 tampons d'arrivée et 6 emplacements, 6 × (12 144 640 + 13 254 144) = 152,4 Mo.

**D13, le témoin « débit ≤ min des étages ».** D12 donne une borne qu'aucune mesure juste ne peut
dépasser : si la médiane des passes A dépasse le plus petit étage de la séance (passes B disque
seul, DMA seule, décodage seul) de plus que le bruit admis (10 %), soit un étage est mal mesuré, soit
la passe A ne fait pas ce qu'elle dit (lecture servie par un cache, horloge arrêtée trop tôt, expert
compté sans décodage). Le témoin est déclaré avant, et sa cassure naturelle est la passe B elle-même
(même suite de lectures, même fenêtre, même lecteur).

**D14, ce que chaque contrôle peut voir d'une corruption.** Soit un bit retourné dans les octets
utiles d'une partie. (i) L'empreinte64 des octets utiles arrivés dans la fenêtre épinglée diffère
de celle du répertoire, sauf collision du préfixe de SHA-256 : probabilité 2⁻⁶⁴ par expert
[hyp. : SHA-256 se comporte comme une fonction aléatoire sur ce préfixe]. (ii) L'empreinte de
l'expert d'origine refaite depuis l'emplacement décodé ne voit que les corruptions **qui changent
la sortie** : un bit des MEDIANES ou des BIAIS (flux bruts) change exactement un octet d'échelle par
bloc concerné ou un biais ; un bit d'un mot ou d'un état rANS change la suite des états, donc (avec
une forte probabilité) les symboles ; mais un champ que le décodeur ne lit pas pour produire la
sortie (couche et expert de l'en-tête de partie, octet réservé d'un en-tête de flux) ne change rien,
et seul (i) le voit. (iii) Les compteurs de la carte (le seul contrôle du mode de production)
voient les fautes de format (magie, sorte, en-tête du flux) et les voies qui ne finissent pas sur
L ; ils ne voient ni les flux bruts ni l'identité de la partie. La cassure déclarée place un bit
dans chacune de ces familles, pour que la table des détections (contrôle par contrôle) en fasse la
preuve sur le vrai chemin.

**D15, la passe témoin ne se chronomètre pas.** En passe témoin, chaque emplacement décodé
(13 254 144 o) redescend par le moteur de copie unique (D5) et l'hôte hache 12 Mo de partie et
13,25 Mo d'expert par SHA-256 sur un fil : ≈ 25 Mo par expert, à ≈ 1,5 à 2 Go/s, soit 12 à 17 ms
par expert, trois fois le temps disque d'un tronçon. Son débit est publié pour mémoire, jamais
jugé ; le seuil se juge sur les passes de production, où rien ne redescend que les compteurs, en
fin de passe (12 288 o).

**D16, la lecture lente : ce que la mesure établit, et ce qu'elle n'établit pas** [mes., séance du
2026-10-15, 21 h 13 à 21 h 35]. Le débit d'experts servis d'E2 vaut, par D11, `B_d · r` ; il est tombé
à 2,153 Go/s, soit `B_d = 1,95 Go/s` de tronçons, et la passe B (le disque seul, mêmes lectures)
donnait 1,92 : le chemin ne coûte rien (A / B = 1,016), c'est `B_d` qui manque. Quatre hypothèses
tuées ou gardées par les nombres, chacune déclarée avant sa mesure :
1. H1, le fichier (fragments) : le `lecteur` d'E1 lit le .trc à 3,03 Go/s et le GGUF à 2,58 ; le
   .trc a 33 fragments, le GGUF 2 737. Tombe, à l'envers.
2. H2 et H2 bis, l'état du disque après la copie de 11 Go : le `lecteur` lit le .trc à 3,06 juste
   avant que `chemin` y lise 1,93 à 2,04, dans la même fenêtre. Tombent.
3. H3a, la longueur : mêmes décalages tirés, même fichier, 12 Mio à 3,05 Go/s, 12 013 568 o à 2,07.
   Tient. Le balayage de 23 longueurs (8 à 13 Mio, deux ordres tirés) donne **deux régimes**, ≈ 2,9 à
   3,4 et ≈ 1,8 à 2,1 Go/s, avec une latence d'une lecture ×1,5 dans le régime lent ; 22 longueurs sur
   23 sont classées de même dans les deux ordres, si bien que la dérive dans le temps ne l'explique
   pas. Lentes : 8,5 ; 9,25 ; 10 ; 10,75 ; 11,457 ; 11,5 ; 11,582 ; 11,75 ; 12,5 Mio. Rapides : 8 ; 8,25 ;
   8,75 ; 9 ; 9,75 ; 10,25 ; 10,5 ; 11 ; 11,25 ; 12 ; 12,25 ; 12,75 ; 13 Mio.
4. Ce que la mesure n'établit pas : le mécanisme. Le premier balayage (12 Mio − g) a tué l'idée d'un
   grain d'alignement (g = 1 Mio rapide entre g = 512 Kio et g = 2 Mio lents). [hyp.] La découpe d'une
   requête en transferts par le pilote du contrôleur (VMD, `iaStorVD`) ou par le filtre de BitLocker
   (`fvevol`), qui ne se voit pas d'ici sans traçage du noyau (ETW), dont la dernière part tomberait
   mal pour certaines longueurs. À publier comme fait mesuré et inexpliqué.
Conséquence calculée : avec une longueur rapide `ℓ ≥ b_max` lue pour chaque tronçon, le disque livre
`B(ℓ)` octets lus par seconde, dont `b̄ / ℓ` sont utiles : `X_servi = B(ℓ) · (b̄ / ℓ) · r = B(ℓ) · o /
ℓ`. Pour ℓ = 12 Mio, `o / ℓ = 13 253 760 / 12 582 912 = 1,0533` ; mesuré en E2-V12 `B(ℓ) ≈ 2,69` (aux
décalages des tronçons), d'où 2,83 Go/s servis prédits, 2,834 et 2,851 mesurés. La lecture en trop
(≤ 0,75 Mio par tronçon, 4,7 % en moyenne) est payée, et rendue sept fois par le changement de
régime. La prédiction écrite avant (≈ 3,2, avec `B(ℓ) = 3,07` du `lecteur`) était fausse de 12 % :
aux décalages des tronçons, le régime rapide ne donne que 2,7 ; cet écart-là n'est pas expliqué non
plus.

## 4. Graphes de bancs (pgfplots) et leurs données

| Figure | Données | Contenu |
|---|---|---|
| E-G1 | `csv/<séance>-c-passes.csv` | coût par jeton de chaque variante (barres), deux charges côte à côte, barres d'erreur = bruit des passes miroirs, ligne du seuil 15,7 ms (échelle log) |
| E-G2 | `csv/<séance>-c-jetons.csv` | distribution des temps par jeton (boîtes à moustaches), par variante |
| E-G3 | `csv/<séance>-b-dma.csv` | Go/s de chaque passe ABBA de la DMA, 12 Mio et 64 Mio, ligne du seuil 11,0, plafond du lien 15,754 |
| E-G4 | `csv/<séance>-b-disque.csv` | Go/s du lecteur, profondeur 4 contre 1, passes A1 B1 B2 A2, ligne du seuil 2,064 ; quantiles p10/p50/p90 de la latence d'une lecture ; second chemin par la loi de Little (D3) |
| E-G6 | `csv/e1-<séance>-lecteur-passes.csv` | E1 sur le disque seul : Go/s de chaque passe (A = QD 4, B = QD 1, deux tours ABBA), propres en plein, sales en creux, contre leurs octets étrangers (axe secondaire) ; ligne du seuil 2,064 et du seuil de propreté 0,26 ; rapport Little / mur par passe |
| E-G5 | `csv/<séance>-a.csv` | essai (a) : chaque taille tentée ou non, réussie ou refusée, contre la RAM disponible au moment de la tentative |
| E-G8 | `csv/e2-2026-10-15-seance1-passes.csv`, `csv/e2-2026-10-15-v12-passes.csv`, `csv/*-etages.csv` | E2 : Go/s servis de chaque passe A (production) et B (disque seul), A1 B1 B2 A2 × 2, pour la lecture de `longueur0` et pour E2-V12 côte à côte ; ligne du seuil 2,2815 ; en encart, les trois étages (disque seul, DMA, décodage) en Go/s de tronçons sur une échelle log : le disque est le goulot d'un ordre de grandeur (DMA ×6,5, décodage ×18) |
| E-G9 | `journaux/e2-2026-10-15-seance1/chrono-1/chrono-A-t0-r0.csv` et `journaux/e2-2026-10-15-v12/chrono-v12582912-1/chrono-A-t0-r0.csv` | chronogramme (diagramme de Gantt) des 40 premiers tronçons d'une passe A : lecture (soumis → lu), copie, décodage ; deux panneaux, `longueur0` et 12 Mio ; plus la distribution des durées de lecture (`lecture_us`) des 768 tronçons |
| E-G10 | `csv/e2-balayage-2026-10-15-longueurs.csv` | **la figure de la découverte** : Go/s (QD 4) contre la longueur de la lecture, 8 à 13 Mio, les deux répliques en deux marques, les tronçons du 20b (11,29 à 11,58 Mio) et du 120b (11,22 à 11,68 Mio) en bande grisée, la ligne de 0,9 × 12 Mio ; axe secondaire, la latence médiane d'une lecture |
| E-G11 | `csv/e2-nvvn-2026-10-15-nvvn.csv` | série N V V N : les 16 passes A, Go/s servis, N et V, barres d'erreur = bruit miroir, ligne du seuil |
| E-G12 | `csv/e2-2026-10-15-seance1-cassure.csv` | la table des détections (E-S9) en matrice de cases |

## 5. Listings commentés

- `trc-cuda/src/lib.rs`, `Interne::courant` : le contexte rendu courant au besoin, par fil, avec
  une génération pour qu'un contexte relâché puis repris ne soit pas cru courant.
- `trc-cuda/src/api.rs`, la macro `table!` : chaque point d'entrée chargé par son nom exporté exact,
  un symbole absent nommé au chargement.
- `trc-es/src/lib.rs`, `Lecteur::lancer` et `Lecteur::recolter` (D7).
- `banc-chemin/noyaux/essais.cu`, `routeur_factice` (D8).
- `banc-chemin/src/disque.rs`, `CompteurDisque::cumul` et `Fenetre` (D9).
- `mesures/moteur/E/temoins_des_temoins.py` : le témoin des témoins (chaque témoin de trc-cuda et
  trc-es forcé à faux par `TRC_E_CASSER`, 7 sur 7 tombent, la suite restaurée tient).

## 6. Résultats

Source : `mesures/moteur/E/journaux/2026-10-15-seance3/resume.json` (E0, 16 h 46 à 16 h 48, secteur,
carte libre), `journaux/e1-2026-10-15-seance1/resume.json` (E1 disque, 15 h 39), `journaux/e1-temoins/`
(témoins et témoin des témoins). Tableau à reproduire (une ligne par critère : grandeur, valeur
mesurée, seuil, source du seuil, verdict) :

| Critère | Mesuré [mes.] | Seuil | Verdict |
|---|---|---|---|
| E1 témoins | 10 tests sur 10 ; 7 cassures forcées sur 7 tombent sur leur message | 0 écart | tient |
| E0 (a) épingler | 0,25 / 1 / 4 Go en 96 / 343 / 1 331 ms ; 11 Go non tenté (8,29 Go dispo.) | réussite | tient à 4 Go, 11 Go non jugé |
| E0 (b) justesse | 32 × 12 Mio, 0 écart ; cassure 1 | 0 / 1 | tient |
| E0 (b) DMA 12 Mio | médiane 12,495 Go/s (12,33–12,67), bruit 1,4 % | ≥ 11,0 | tient |
| E0 (c) synchronisations | 0,666 ms par jeton sous charge (`evenement`), 18,5 µs l'une | ≤ 15,7 ms | tient, ×23 |
| modèle D2 | coût sous charge / à vide = 3,6 à 4,8 | 1 attendu | tombe : D2 bis |
| E1 disque, séance 1 (règle 1) | médiane des A propres 1,506 Go/s (processeur des autres 69–84 %) | ≥ 2,064 | tombe sous charge |
| E1 disque, essai b de la séance 3 (règle 2) | QD 4 2,673 / 2,445 ; processeur des autres 44–54 % | ≥ 2,064, propre | non jugé |

**E1 et E2 (2026-10-15, 20 h 40 à 21 h 35, secteur, verrou du lot E)**, sources :
`journaux/e1-2026-10-15-seance3/resume.json`, `journaux/e2-2026-10-15-seance1/resume.json`,
`journaux/e2-2026-10-15-v12/resume.json`, `journaux/e2-nvvn-2026-10-15/serie.json`,
`journaux/e2-balayage-2026-10-15/balayage.json`, `journaux/e2-diag-2026-10-15/` :

| Critère | Mesuré [mes.] | Seuil | Verdict |
|---|---|---|---|
| E1 disque, séance 3 (règle 2, au calme) | médiane des A propres 2,439 Go/s (4 propres sur 4) | ≥ 2,064 | tient |
| E2, C2 transport exact | 768 / 768 à chacune des 8 passes témoin (empreinte d'origine, de partie, compteurs nuls) | 0 écart | tient |
| E2, cassure (12 bits, un par sorte de région) | 12 détectés sur 12, 0 en trop ; empreinte de partie 12, d'origine 11, compteurs 9 ; production 9 | 100 % | tombe comme il faut |
| E2, débit, lecture de `longueur0` | médiane des A propres 2,153 Go/s servis (pire 2,092) ; 2,135 en N V V N | ≥ 2,2815 | **tombe** (−5,6 %) |
| E2, débit ≤ min des étages | A / disque seul 1,016 ; DMA 12,66 ; décodage 34,27 Go/s (0,350 ms par expert) | ≤ 1,10 | tient |
| E2-V12, lectures de 12 Mio (variante, publiée à côté) | 2,834 ; 2,851 en N V V N | ≥ 2,2815 | tient |
| V / N (N V V N) | ×1,335, écart 25 %, bruit miroir ≤ 1,5 % | 2 × bruit et 3 % | distincts |
| E2 sur le 120b, C2 (`journaux/e2-120b-2026-10-15/`) | 4 608 / 4 608 aux deux passes témoin | 0 écart | tient |
| E2 sur le 120b, débit (non jugé, une séance) | N 2,063 ; V12 2,877 Go/s servis (×1,39) | 2,2815 (repère) | N sous, V au-dessus |

Graphe à faire en plus : E-G7, débit du disque en QD 4 contre l'occupation du processeur par les
autres (toutes les passes de toutes les séances, 12 points au moins) : il montre la charge de
BitLocker sur le chemin, la raison de la règle 2.

## 7. Ce qui pourrait être faux

- **La carte des longueurs est celle d'une machine, d'un fichier, d'une soirée** : 23 longueurs,
  deux répliques, le fichier du 20b, décalages tirés ; le régime d'une longueur peut dépendre du
  pilote du contrôleur, de la version de BitLocker, du micrologiciel du NVMe, de l'état du disque
  (taux de remplissage) ; elle ne se transporte pas, elle se recalibre. 9,5 Mio est resté entre les
  deux régimes ; une longueur rapide ici peut être lente sur le 120b (non mesuré).
- **E2-V12 lit des octets du tronçon suivant** : sans effet sur la justesse (ni copiés ni décodés,
  C2 tient aux trois passes témoin en 12 Mio), mais un moteur qui lirait deux tronçons voisins de la même
  couche lirait deux fois la frontière ; compté dans le ×1,335, pas optimisé.
- **Le seuil d'E2 et C5 reposent sur 2,58 Go/s mesurés en blocs de 4 Mio** (01), une longueur que ce
  balayage n'a pas couverte (8 à 13 Mio) : si 4 Mio est dans un régime rapide, le seuil compare un
  régime rapide à une lecture dans un régime lent ; le verdict « tombe » d'E2 dit d'abord cela.
- **La passe témoin d'E2 vérifie l'expert redescendu**, pas l'emplacement lu par la GEMV au moment du
  calcul : une écriture d'un autre noyau entre le décodage et la GEMV ne se verrait pas ici (le lot O
  l'exclut par l'épinglage du cache, § 5.7).

- **Les essais simulent la couche**, ils ne la calculent pas : un vrai routeur lit 2 880 × 128 poids
  et un vrai expert 13 Mo ; le coût de synchronisation du modèle D2 ne dépend pas de ces durées, mais
  une carte occupée par une GEMV pourrait retarder le lancement suivant plus qu'une attente active
  d'un seul fil. Le témoin des deux charges l'encadre, sans le prouver pour toutes.
- **La machine est partagée** : un autre agent peut lire le disque ou occuper la carte pendant une
  passe ; le pilote refuse de mesurer quand un llama-* ou le traceur tourne et journalise l'état de la
  carte avant et après chaque passe, mais un processus qui n'est ni l'un ni l'autre échappe au test.
- **L'essai (a) ne tente que ce que la RAM disponible permet** (marge de 1,5 Go déclarée) : une taille
  « non tentée » n'est pas une taille refusée par le pilote ; ce n'est qu'au calme que la question
  « 11 Go » reçoit sa réponse.
- **La variante `boite_sans_vidage`** repose sur un comportement non documenté (le pilote soumet-il
  un lancement sans appel qui le pousse ?) ; elle est publiée, jamais retenue.
- **`Contexte::memoire` rend (0, 0) en cas d'erreur** du pilote, la signature gelée n'ayant pas de
  `Result` : un appelant qui ne teste pas ce cas lirait « pas de VRAM ».
- **`Lecteur::soumettre` et `copier_vers_hote` sont des fonctions sûres** qui confient au système ou
  au pilote une écriture asynchrone : le contrat d'ordre est documenté, pas vérifié par le type.
