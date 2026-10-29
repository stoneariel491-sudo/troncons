# 01 — La machine, mesurée : le banc de chaque étage

Étude 01 de troncons. Consigne : mesurer, sur la machine de Stone, le débit et la latence de chaque
étage entre le disque et les unités de calcul, avec des outils écrits ici, puis en tirer le toit
(roofline) qui juge toute la suite du projet.

Étiquettes : **[calc.]** calculé ; **[mes.]** mesuré ici ; **[litt.]** littérature (éditeur, non
reproduit). Toutes les sources ont été consultées le 2026-10-15.

Outils : `outils/banc/` (Rust : `disque`, `memoire`, `carte` ; pilotes Python de la bibliothèque
standard : `pilote_disque.py`, `pilote_carte.py`, `pilote_thermique.py`, `pilote_llama.py`,
`analyse_disque.py`, `analyse_carte.py`). Journaux : `fondations/journaux/01-machine/`. Seuils et
témoins déclarés avant toute mesure : `00-seuils-declares.md` (une règle y est barrée, avec sa
raison, voir § 2.3).

---

## 0. En bref

| Étage | Plafond [calc.] | Mesuré ici, au mieux [mes.] | Rendement | Remarque |
|---|---|---|---|---|
| NVMe → RAM, gros blocs (≥ 1 Mio) | 7,877 Go/s (lien 4.0 ×4) ; 6,0 Go/s annoncés [litt.] | **2,8 Go/s** (16 Mio, QD 1, bruit 1 %) ; 3,8 vu deux fois, non reproduit | 36 % du lien, 47 % de l'annonce | BitLocker actif, BypassIO refusé, pilote Intel RST VMD |
| NVMe 4 Kio aléatoire | 900 k IOPS annoncés [litt.] | **≈ 54 k IOPS** (0,22 Go/s, QD ≥ 16) ; QD 1 : p50 ≈ 200 µs | ≈ 6 % | borné par le processeur : ≈ 4 s de processeur par Go lu |
| Déchiffrement BitLocker (XTS-AES-128, processeur, CNG) | | **3,2 à 4,2 Go/s sur un fil, 8,7 Go/s sur huit** (sur batterie) | | ≈ 0,25 à 0,3 s de cœur par Go lu ; même ordre que le plateau du disque sur un fil (§ 2.7) |
| RAM (processeur) | 41,6 Go/s (un seul module DDR5-5200, 64 bits) | **15,6 Go/s** (lecture, 1 fil, chargée) ; 18–23 en copie ; sur batterie 1,5 à 10, inutilisable comme plafond | ≤ 38 % | **un seul module** : la moitié du débit d'un portable à deux modules ; mesure au calme sur secteur en attente (§ 3) |
| Hôte → carte (PCIe 4.0 ×8) | 15,754 Go/s | **12,2 Go/s** (DMA depuis la RAM hôte, 64 Mio) | 77 % | 3,2 à 6,3 Go/s quand d'autres agents chargent la machine |
| Carte → hôte | 15,754 Go/s | 6,2 à 9,4 Go/s | 40 à 60 % | |
| Lecture de VRAM (shader) | 256 Go/s (GDDR6 128 bits, 16 Gbit/s) | **251,3 Go/s** | **98 %** | Vulkan = DX12 |
| GEMV f16 (128 Mio de poids) | 256 Go/s | **250 Go/s** | 98 % | bornée par la mémoire |
| GEMV 4 bits (format Q4_0, 144 Mio) | 256 Go/s | **122 Go/s** (noyau q4b) ; 95–113 (naïf) | 48 % | noyau à travailler, pas la machine |
| GEMV dont les poids restent en RAM hôte (zéro copie) | 15,754 Go/s | **11,75 Go/s** | 75 % | la carte calcule à la vitesse du lien, sans copie en VRAM |
| Calcul f32 / f16 / dot4 int8 (Vulkan) | ≈ 16,4 Tflop/s [calc., horloge 2,67 GHz relevée] | 12,6 / 13,4 / 12,3 T op/s | ≈ 77 % | f16 sans gain sur f32 ; DX12 par wgpu : int8 à 3,3 |
| Décodage 4 bits depuis les registres | | **1,31 T poids/s** (2,61 T op/s) | | 2,6 fois ce que la VRAM livre en 4 bits |
| Thermique, 5 min de GEMV, sur secteur | | **pas de bridage** (rapport fin/début 1,001, bruit 6,3 %) | | 2 685 MHz, 75 °C, 72 W |
| **Sur batterie** (découvert à 07:25) | plafond de puissance 80 W → **52,6 W** | mémoire de carte 6 001 MHz au lieu de 8 001 ; PCIe Gen 3 ; processeur ~1,5 GHz | | le portable bride **sur batterie**, pas par la chaleur (§ 5.4) |
| llama.cpp b11515, Qwen3.5-9B Q4_K_M, -ngl 99 | 49 jetons/s (toit VRAM) | **34,1 jetons/s** (au mieux, machine partagée, ±5,4) | 69 % | -ngl 24 : 2,8 jetons/s ; passage ABBA complet en attente du secteur (§ 6) |

**Le toit pour le Qwen3.5-9B Q4_K_M** (B = 5,10 Go lus par jeton, § 7) : 49 jetons/s si tout est en
VRAM ; 2,4 jetons/s si tout passe par la PCIe ; 0,55 jeton/s si tout vient du disque.
**Le facteur de compression qui rend la lecture disque aussi rapide que la PCIe : r\* = 12,2 / 2,82 =
4,33** par rapport aux octets du Q4_K_M, ~~soit ≈ 1,05 bit par poids stocké pour 4,5 bits servis à la
carte~~ soit **≈ 1,17 bit par poids stocké** pour les 5,08 bits par poids que le Q4_K_M sert en
moyenne (barré : le Q4_K_M n'est pas à 4,5 bits, il mêle des tenseurs Q6_K ; 5,08 vient de
02-quantification, § 5.2). Avec le débit annoncé du disque (6,0 Go/s, si BitLocker et VMD ne
bridaient pas), r\* tomberait à 2,03. La carte a de quoi décoder : à 12,2 Go/s d'entrée compressée,
son budget de calcul est d'environ **214 opérations par octet compressé** (§ 7.4).

**Ce qui change pour la suite du projet** (trois faits que ce banc a établis et que les autres études
doivent prendre) :
1. **Le disque réel livre 2,82 Go/s, pas 7,9** : les plafonds de 06-modeles (`modeles_physique.py`,
   `NVME_GO_S = 7.877`, plafond du lien) sont **2,8 fois trop optimistes** dès que le disque est
   l'étage limitant (gpt-oss-120b : 5,5 jetons/s au lien, 1,98 au disque mesuré, § 7.3).
2. **La PCIe vaut 12,2 Go/s au calme**, pas 6,4 (le chiffre de 04-chargement était un état chargé,
   § 4.2) : l'étage RAM → carte est 4,3 fois plus rapide que le disque, et c'est lui qui fixe r\*.
3. **Toute mesure doit noter la source d'alimentation** : sur batterie, la machine est une autre
   machine (§ 5.4). Les pilotes le font désormais (`pilote_llama.py`, `suite_secteur.py`).

**D'où on part, où on va.** Au départ : des plafonds calculés d'après les fiches techniques (lien
NVMe 7,877 Go/s, PCIe 15,754, VRAM 256, RAM 41,6) et un seul chiffre mesuré par un autre (PCIe
6,4 Go/s par CUDA, 04-chargement, sous charge). Ce que l'étude établit : le débit réel de chaque étage
sur la machine de Stone, avec témoins et ABBA, deux régimes (secteur, batterie), et le toit qui en
découle (§ 7) ; trois corrections pour les autres études (en bref, points 1 à 3). Ce qui reste : la
RAM et llama.cpp au calme sur secteur (suite prête, § 6.3), la part de BitLocker dans le plafond du
disque (§ 9), et un noyau 4 bits Vulkan au niveau de la VRAM (§ 8, point 5).

Données pour le mémoire : CSV `disque-balayage.csv` (94 cellules, passages A et B),
`toit-modeles.csv`, `toit-placements.csv`, `toit-9b-compression.csv` (r de 0,1 à 16, architectures A
et B), `thermique-secteur-charge.csv`, `thermique-batterie.csv`, `carte-lien-pcie.csv` ; sources
`memoire/sources/01-machine.bib` ; dérivations au § 7.1 (proposition 1, corollaires 2 et 3).

---

## 1. La machine (relevé du 2026-10-15)

- Processeur i7-13620H, 6 P + 4 E, 16 fils, L2 9,5 Mio, L3 24 Mio (WMI).
- **RAM : un seul module** Micron MTC8C1084S1SC56BD1, 16 Gio, DDR5 annoncé 5 600, **configuré
  à 5 200 MT/s**, emplacement « Controller0-ChannelA-DIMM0 » (WMI `Win32_PhysicalMemory`). Un module
  DDR5 = deux sous-canaux de 32 bits : 5 200 × 8 o = **41,6 Go/s** [calc.]. Un second module
  identique doublerait capacité et débit (geste et argent de Stone : je le note, je n'en décide pas).
- Carte : RTX 4060 Laptop (AD107), 8 188 Mio, pilote 591.91, horloge mémoire 8 001 MHz relevée
  (GDDR6 16 Gbit/s), lien PCIe 4.0 ×8 au plus (nvidia-smi : `pcie.link.gen.max = 4`,
  `width.max = 8`). Le lien descend en Gen 1 au repos et remonte en Gen 4 sous charge
  (`carte-lien-pcie.csv` : 216 relevés en Gen 1, 118 en Gen 4 pendant trois séries de copies).
- Disque : NVMe Samsung MZVMA1T0HCLD-00BTW (1 To), micrologiciel MXE7001Q, **derrière le contrôleur
  Intel RST VMD** (pilote de stockage `iaStor`, relevé par FSCTL_MANAGE_BYPASS_IO). Le volume C: est
  **chiffré par BitLocker** (propriété Shell `System.Volume.BitLockerProtection` = 1 ; le filtre
  `fvevol` refuse BypassIO, § 2.4). Le lien du disque n'est pas lisible sans droits d'administrateur
  (le périphérique NVMe est caché derrière VMD).
- Secteur : sur secteur pendant les mesures (Win32_Battery `BatteryStatus = 2`, 80 %).

**Biais permanent, dit d'avance.** D'autres agents travaillaient sur la machine pendant toutes ces
mesures (llama-quantize jusqu'à 8,7 cœurs, plusieurs llama-perplexity sur la carte jusqu'à 7,7 Gio
de VRAM, scripts Python ; RAM libre entre 1,0 et 4,4 Gio). Chaque passe journalise la charge
(compteur du système pour le disque, nvidia-smi pour la carte). Les chiffres « au mieux » sont des
**bornes inférieures** de ce que la machine donne au repos ; les médianes disent ce qu'elle donne
partagée.

## 2. Le disque

### 2.1 L'instrument

`disque.exe` (Rust, `windows-sys`) lit un fichier de test de **32 Gio (2 × la RAM)** ouvert avec
`FILE_FLAG_NO_BUFFERING | FILE_FLAG_OVERLAPPED`, tampons alignés par `VirtualAlloc`, `qd` lectures en
vol, par port de complétion (IOCP) ou par IoRing. Le fichier porte un motif vérifiable : chaque page
de 4 Kio commence par son numéro xor une constante, la suite est un flux xorshift64* de graine le
numéro. Chaque lecture vérifie l'en-tête de chaque page reçue, et une page complète sur 64.
Fenêtre de 2 s après 0,5 s de chauffe.

Balayage : blocs 4 Kio à 16 Mio × profondeurs 1 à 64 (octets en vol plafonnés à 256 Mio, la RAM libre
étant maigre), aléatoire et séquentiel, **en ordre ABBA** (toute la liste, puis la liste à l'envers :
chaque cellule mesurée deux fois, en ordre miroir, la dérive s'annule et l'écart A/B est le bruit).
188 passes, puis IOCP contre IoRing en ABBA deux fois sur cinq cas (40 passes).
Journal : `disque-balayage.jsonl` ; tableaux : `disque-analyse.md`.

### 2.2 Les témoins

- `--fausser` (l'attendu décalé d'une page) : 978 688 pages fausses sur 978 688 → l'instrument
  vérifie vraiment. Sans `--fausser` : 0 page fausse sur 889 344, 0 erreur, et 0 sur toutes les
  passes du balayage.
- Aucune lecture sans tampon au-dessus du lien (7,877 Go/s) : vérifié sur les 228 passes.
- Le cache, par le second chemin (compteur cumulé du système, § 2.3) : relu par le cache de Windows,
  1 Gio est livré à 1,65 Go/s pendant que le disque ne lit que 3,4 % de ces octets → le cache est
  visible quand il joue, donc absent des passes sans tampon (où le disque voit ≥ 100 % des octets).

### 2.3 Une règle barrée, et le second chemin

~~Le moteur `tampon` relu sur 1 Gio doit dépasser 7,877 Go/s.~~ Faux : l'essai du pilote a livré le
cache à 3,1 Go/s avec 2,98 s de processeur pour 3 s de fenêtre. La copie depuis le cache de Windows
est bornée par un fil de processeur, pas par la RAM. Barré avant le balayage complet et remplacé par
le témoin au compteur, plus fort.

Le second chemin : `Win32_PerfRawData_PerfDisk_PhysicalDisk` (`_Total`, `DiskReadBytesPersec`,
compteur cumulé) relevé toutes les 0,5 s par un PowerShell persistant (typeperf refuse les noms
anglais sur ce Windows français ; les classes CIM, elles, gardent leurs noms anglais), avec
l'occupation du processeur (`Win32_PerfRawData_PerfOS_Processor`). Ce qu'il a montré :
- au premier passage (A), d'autres processus lisaient jusqu'à **0,6 Go/s** sur le même disque, et
  le processeur était occupé à 90-100 % ; au second (B), 35-40 %. C'est l'origine des bruits de 50 à
  130 % sur les petits blocs ; les cellules ≥ 1 Mio restent à quelques %.
- le témoin « le disque a vu ≥ 90 % de nos octets » a échoué sur 5 passes : elles tombent toutes
  dans un trou de 14 s du relevé (la même paire d'échantillons encadre les 5), pas dans le disque.
  Dit tel quel ; ces 5 passes n'ont pas de second chemin.

### 2.4 Résultats [mes.]

Débit en Go/s (moyenne des passages A et B ; entre crochets |A − B| / moyenne) :

| bloc | aléa QD 1 | aléa QD 4 | aléa QD 16 | aléa QD 64 | séq QD 1 | séq QD 4 | séq QD 16 |
|---|---|---|---|---|---|---|---|
| 4 Kio | 0,015 [53 %] | 0,059 [44 %] | 0,125 [136 %] | 0,132 [134 %] | 0,046 [11 %] | 0,086 [8 %] | 0,188 [3 %] |
| 64 Kio | 0,205 [11 %] | 0,578 [30 %] | 0,739 [6 %] | 0,721 [10 %] | 0,390 [16 %] | 0,849 [33 %] | 2,309 [0 %] |
| 1 Mio | 1,307 [18 %] | 2,195 [17 %] | 2,327 [3 %] | 1,928 [8 %] | 1,599 [8 %] | 3,156 [43 %] | 1,900 [40 %] |
| 4 Mio | 2,314 [5 %] | 2,581 [10 %] | 2,430 [0 %] | 2,418 [2 %] | 1,041 [13 %] | 2,385 [11 %] | 1,631 [92 %] |
| 16 Mio | **2,819 [1 %]** | 2,533 [0 %] | 2,487 [2 %] | — | 2,340 [43 %] | 1,468 [73 %] | 2,206 [17 %] |

(Tableau complet, latences p50 comprises : `disque-analyse.md`.)

Ce qu'on en tire :
- **Le plateau des gros blocs est à 2,4–2,9 Go/s**, quelle que soit la profondeur. Le meilleur point
  reproductible : 16 Mio aléatoire QD 1, 2,82 Go/s, bruit 1 %. Deux cellules ont touché 3,84 Go/s
  (256 Kio QD 16 et 1 Mio QD 4, passage A) sans se reproduire au passage B : je ne les retiens pas
  comme plafond.
- Petits blocs : 4 Kio aléatoire plafonne vers 0,13–0,22 Go/s (≈ 54 k IOPS au mieux, passage B), la
  latence médiane à QD 1 est de 200 à 230 µs. Le processus consomme ≈ 4 s de processeur par Go lu en
  4 Kio (≈ 16 µs par entrée-sortie), 0,07 à 0,11 s/Go au-delà de 1 Mio.
- **IOCP et IoRing ne se distinguent pas** : sur les cinq cas, l'écart (0 à 5 %) reste sous la règle
  déclarée (≥ 2 × bruit et ≥ 3 %). IoRing coûte un peu moins de processeur sur les gros blocs (0,21
  à 0,41 s contre 0,33 à 0,58 s par passe), sans gain de débit.
- Écriture : la préparation du fichier a écrit à 0,10 Go/s, mais c'était une écriture synchrone
  à QD 1 avec `FILE_FLAG_WRITE_THROUGH` : ce n'est pas une mesure du disque, seulement du chemin choisi.

### 2.5 Pourquoi si loin de l'annonce

Samsung annonce pour le PM9C1a 6 000 Mo/s en lecture séquentielle et 900 k IOPS
[litt. : communiqué Samsung de janvier 2023 (reprises datées du 2023-01-13), dans sa version de la
salle de presse des semi-conducteurs https://news.samsungsemiconductor.com/global/samsung-electronics-unveils-high-performance-pc-ssd-that-raises-everyday-computing-and-gaming-to-a-new-level/
(la page de news.samsung.com n'a pas répondu le 2026-10-15) ; https://news.samsung.com/global/samsung-electronics-unveils-high-performance-pc-ssd-that-raises-everyday-computing-and-gaming-to-a-new-level ;
StorageReview, https://storagereview.com/?p=119560]. Ces sources ne nomment pas la référence
MZVMA1T0HCLD : l'identification au PM9C1a est probable (préfixe MZVMA), pas prouvée.

Ce que je sais, mesuré :
1. **BitLocker est actif et le filtre `fvevol` refuse BypassIO** (`disque capacites` :
   `pilote_en_echec="fvevo…"`, `raison="BitLocker Drive Enc…"`, statut 0xC00004C9). La documentation
   Microsoft donne exactement ce cas : « Volume stack bypass is disabled (fvevol.sys) … BitLocker
   Drive Encryption is enabled » [litt. : Microsoft Learn, *BypassIO for Filter Drivers*,
   https://learn.microsoft.com/en-us/windows-hardware/drivers/ifs/bypassio, mis à jour le 2025-11-05].
   Chaque octet lu traverse donc le déchiffrement logiciel du volume.
2. **Le pilote de stockage est `iaStor` (Intel RST VMD)**, pas `stornvme` : la même page réserve le
   chemin BypassIO complet à StorNVMe.
3. Le processeur était chargé par d'autres agents ; les petits blocs, liés au processeur, en
   souffrent le plus (passage A contre B).

Ce que je n'ai pas pu séparer : la part de BitLocker, celle de VMD et celle du disque lui-même. Le
test qui tranche demande un geste de Stone (§ 9).

### 2.6 IoRing, BypassIO, DirectStorage

- **IoRing** : présent dans le noyau, version maximale **400** (IORING_VERSION_4, plus récente que
  les en-têtes de `windows-sys` 0.61.2 qui s'arrêtent à la version 3), files jusqu'à 65 536 / 131 072,
  pas d'émulation en mode utilisateur (`QueryIoRingCapabilities`). Utilisable, mais sans gain
  mesurable ici (§ 2.4).
- **BypassIO** : refusé sur C: (BitLocker), voir § 2.5.
- **DirectStorage** : aucune DLL `dstorage*.dll` dans `System32` (la bibliothèque se livre avec
  l'application). Le SDK est le paquet NuGet `Microsoft.Direct3D.DirectStorage` : version stable
  **1.3.0** (2025-06-27) = **2 816 824 octets** ; préversion **1.4.0-preview2-2606.904** (2026-06-16)
  = **3 986 072 octets** (taille lue par requête HEAD sur `api.nuget.org`, rien téléchargé ; liste des
  versions : https://api.nuget.org/v3/registration5-gz-semver2/microsoft.direct3d.directstorage/index.json).
  La 1.4 ajoute Zstandard au cadre de décompression multi-niveaux, sur processeur et sur carte, et
  publie le shader de décompression Zstd ; GDeflate reste [litt. : DirectX Developer Blog,
  2026-03-11, https://devblogs.microsoft.com/directx/directstorage-1-4-release-adds-support-for-zstandard/].
  **Non mesuré** : la décompression GDeflate ou Zstd sur la carte demande le SDK (téléchargement à
  autoriser, § 9). Sur cette machine, DirectStorage tournerait de toute façon sans BypassIO.

### 2.7 Le coût de BitLocker, par un second chemin [mes.]

On ne peut pas lire le disque sans BitLocker (il faudrait suspendre le chiffrement, un geste de
Stone sur un réglage de sécurité, que je ne fais ni ne propose comme banal). On peut en revanche
mesurer ce que coûte, sur ce processeur, le déchiffrement que fvevol applique à chaque octet lu.
`aes_xts.py` appelle l'API CNG de Windows (`bcrypt.dll`, algorithme `XTS-AES`, normes SP 800-38E et
IEEE 1619-2007 [litt. : Microsoft Learn, *CNG Algorithm Identifiers*,
https://learn.microsoft.com/en-us/windows/win32/seccng/cng-algorithm-identifiers, mis à jour le
2026-05-30]) avec des unités de 4 Kio, comme un secteur de BitLocker, par morceaux de 1 Mio, de 1 à
8 fils, une clé par fil.

**Le mécanisme.** XTS chiffre chaque bloc de 16 octets j de l'unité de numéro i par
C_j = E_K1(P_j ⊕ T_j) ⊕ T_j, avec T_j = E_K2(i) ⊗ α^j dans GF(2^128) : deux clés AES, un
ajustement qui dépend de la position. Chaque bloc coûte un AES (10 tours pour une clé de 128 bits,
14 pour 256), exécuté par les instructions AES-NI, plus une multiplication par α (décalage et xor).
Les blocs sont indépendants : le déchiffrement se parallélise parfaitement entre unités.

Témoins : le vecteur 1 de l'annexe B de IEEE 1619-2007 (clés nulles, 32 octets nuls, chiffré
attendu `917cf69e…2fbf922e`) et l'aller-retour chiffrer-déchiffrer sur 1 Mio ; `--fausser` les fait
tomber tous deux (journal `aes-xts-batterie.log`, premières lignes).

| XTS-AES, déchiffrement (sur batterie) | 1 fil | 2 fils | 4 fils | 8 fils |
|---|---|---|---|---|
| clé 128 bits | **4,16 puis 3,20** (A, B ; bruit 26 %) | 5,34 | 7,65 | **8,69 Go/s** |
| clé 256 bits | 3,01 | | 7,28 | |

Ce que cela dit :
- **Sur un fil, le déchiffrement va à 3,2–4,2 Go/s : le même ordre que le plateau du disque
  (2,8 Go/s).** Si fvevol déchiffre une requête sur un seul fil, une lecture en QD 1 est bornée par
  un cœur. Mais le plateau ne monte pas avec la profondeur (2,4–2,9 Go/s de QD 1 à QD 64, § 2.4),
  alors que le processeur sait déchiffrer 8,7 Go/s sur huit fils : soit fvevol sérialise, soit la
  borne est ailleurs (VMD, le disque, sa gestion thermique). **Je ne peux pas trancher sans lire
  sans BitLocker.** C'est dit comme hypothèse, chiffrée.
- **Ce que BitLocker coûte au projet, en temps de processeur** : 1 / 3,2 à 1 / 4,2 ≈ **0,24 à
  0,31 s de cœur par Go lu** (sur batterie ; moins sur secteur, à mesurer). À 2,8 Go/s, c'est ≈ 0,7
  à 0,9 cœur occupé en permanence, que notre propre décompression sur le processeur ne pourra pas
  utiliser. Le relevé du système pendant le balayage le confirme dans l'ordre de grandeur : 15 à 26 %
  de temps noyau (sur 16 fils logiques, ≈ 2,4 à 4,2 fils) aux gros blocs (`disque-analyse.md`),
  charge des autres agents comprise.
- La clé de 256 bits coûte ≈ 10 % de plus sur un fil (14 tours contre 10) ; je ne sais pas laquelle
  BitLocker emploie ici (`manage-bde -status` demande des droits d'administrateur).

## 3. La RAM

`memoire.exe` : lecture (somme de mots de 64 bits, quatre accumulateurs), écriture (remplissage),
copie (memcpy, octets lus + écrits), de 1 à 16 fils, tampons de 512 Mio (21 × L3) ; latence par
chasse de pointeurs sur un cycle de Sattolo, un saut par ligne de 64 o. Témoin : la somme du motif
est connue (n(n−1)/2) ; `--fausser` l'a fait échouer (`memoire.log`, 1re ligne).

**Mesure 1 (02:20, machine très chargée, `memoire.log`) : inutilisable comme caractérisation.**
Premier passage : lecture 1 fil 15,6 Go/s, copie 18–23 Go/s ; puis effondrement à 2–4 Go/s pour tous
les nombres de fils, latence 290–420 ns. La RAM libre était d'environ 1 Gio et llama-quantize
occupait 8,7 cœurs : le débit mesuré était celui que les autres laissaient.

**Ce que la mesure 1 a appris à l'instrument.** Avec 1 à 2 Gio de RAM libre, Windows retire des
pages de l'ensemble de travail du banc et les range dans son magasin de compression : une lecture
« de RAM » paie alors une faute de page et une décompression. `memoire.exe` relève donc désormais le
plancher de son ensemble de travail (`SetProcessWorkingSetSize`) et **verrouille ses deux tampons**
(`VirtualLock`), et il compte les fautes de page pendant chaque série (`K32GetProcessMemoryInfo`).
Témoin neuf, déclaré avant : moins de 1 % des pages lues ont fauté. Forcé à faux (`--neuf` : un
tampon neuf à chaque passe), il tombe : 197 033 fautes pour 196 608 pages lues
(`memoire-batterie-verrou.log`). Verrouillé : 15 à 267 fautes pour 196 608 pages, témoin tenu.

**Mesure 2 (07:55, sur batterie, verrouillée, `memoire-batterie-verrou.log`) : régime batterie.**

| Lecture, Go/s (médiane) | 1 fil | 2 | 4 | 8 | 16 |
|---|---|---|---|---|---|
| passage A | 6,18 | 9,98 | 6,83 | 4,57 | 2,01 |
| passage B | 1,48 | 4,61 | 4,70 | 5,60 | 1,85 |

Le bruit ABBA dépasse 100 % : rien ne s'en tire comme plafond. Deux faits seulement :
- **la latence d'un accès dépendant est de 0,5 à 1,05 µs** sur 256 Mio, **sans faute de page** ;
  par taille : 63 ns à 2 Mio (dans les caches), 755 ns à 8 Mio, 845 à 32 Mio, 962 à 128 Mio. Une
  DRAM DDR5 répond en ~100 ns ; un échec du TLB en coûte quelques centaines de plus quand la
  traduction est **imbriquée** : la sécurité par virtualisation (VBS) et l'intégrité de la mémoire
  (HVCI) tournent ici (`Win32_DeviceGuard` : `VirtualizationBasedSecurityStatus = 2`, service 2),
  donc chaque échec du TLB parcourt deux tables de pages. Ajoutée au processeur à ~1,5 GHz sur
  batterie, c'est l'explication la plus probable ; **hypothèse, non prouvée** (il faudrait des
  grandes pages, qui demandent le privilège `SeLockMemoryPrivilege`, donc un geste
  d'administrateur) ;
- 16 fils lisent moins vite qu'un seul : sur batterie, avec un autre agent qui occupe les cœurs,
  le chemin « processeur lit la RAM » est le plus fragile de la machine.

**Conséquence pour le toit** : le chemin des poids par la carte (RAM → PCIe → carte, 12,2 Go/s
mesurés) ne dépend pas du débit du processeur vers la RAM, tant que celle-ci livre plus de 12,2 Go/s
au contrôleur PCIe (DMA). Le chemin « le processeur calcule les experts en RAM » (celui de llama.cpp
avec `-ncmoe`, et celui que suppose `modeles_physique.py`) dépend, lui, de ce débit, et je n'ai pas
encore de chiffre propre : **mesure au calme sur secteur en attente** (`suite_secteur.py`, étapes
`ram_A` et `ram_B`). D'ici là, le meilleur chiffre est 15,6 Go/s (1 fil, mesure 1, premier passage),
soit 38 % du plafond d'un module.

## 4. Hôte ↔ carte

### 4.1 L'instrument, et ce que le témoin de plafond a levé

`carte.exe transfert` (wgpu 30.0.1, Vulkan et DX12) mesure, en ordre ABBA sur les opérations, avec
les horodatages de la carte (`write_timestamp` dans l'encodeur) et le mur :
- `h2d_hote_dma` : copie d'un tampon placé en **RAM hôte** (tampon de relecture `MAP_READ`, utilisé
  comme source grâce à `MAPPABLE_PRIMARY_BUFFERS`) vers la VRAM : la vraie DMA à travers la PCIe ;
- `h2d_bar_cpu` : le processeur écrit lui-même dans un tampon projeté `MAP_WRITE` ;
- `write_buffer` : `queue.write_buffer` depuis un tampon paginable du programme (le chemin naïf) ;
- `d2h`, `d2d` ; `copie_tampon_envoi` (copie depuis le tampon `MAP_WRITE`).
Témoin : aller-retour octet pour octet (hôte → A → B → hôte) ; `--fausser` le fait tomber.

**Découverte par le témoin.** Le premier essai (`carte-essai1-tampon-envoi-en-vram.jsonl`) donnait
« hôte → carte » à 80–220 Go/s : le témoin de plafond (≤ 15,754 Go/s) l'a marqué `sous_plafond=false`.
Raison : **sous Vulkan, le pilote place les tampons `MAP_WRITE` en VRAM visible du processeur (BAR
redimensionnable)** ; la copie mesurée était VRAM → VRAM, et le vrai passage PCIe avait eu lieu
pendant l'écriture du processeur dans la projection. Sous DX12 (wgpu), le même tampon vit en RAM hôte
(copie à 12,2 Go/s). Une exception confirme : quand la VRAM était presque pleine (627 Mio libres), le
tampon d'envoi est retombé en RAM hôte et la copie a donné 7,9 Go/s, sous le plafond.

### 4.2 Résultats [mes.] (`carte.jsonl`, `carte-complement.jsonl`, `carte-lien-pcie-transferts.log`)

| Opération | 64 Mio, machine calme | sous charge | Remarque |
|---|---|---|---|
| hôte → carte, DMA depuis la RAM hôte (Vulkan) | **12,10 / 12,24 / 12,20 Go/s** (3 séries, bruit ≤ 0,7 %… 72 %) | 3,2 à 6,3 | 77 % du lien |
| processeur → BAR (Vulkan) | 9,1 Go/s | 0,45 à 4,5 | au mur, projection comprise |
| `write_buffer` (Vulkan) | 7,5 à 8,2 Go/s | 0,1 à 4,3 | une écriture par soumission |
| carte → hôte | 6,2 à 9,4 Go/s | 3,3 à 6,8 | |
| copie depuis le tampon d'envoi, DX12 | 12,0 à 12,2 Go/s | | ce tampon-là est en RAM hôte sous DX12 |

~~À 256 Mio, la DMA hôte → carte tombe à 4,4–6,3 Go/s : un effet de taille (soupçon : IOTLB).~~
**Barré** : le balayage de taille (`carte-taille-transfert.log`, 32 à 256 Mio, deux fois) a donné
3,2–4,3 Go/s à **toutes** les tailles, 64 Mio compris, puis trois séries à 64 Mio sont revenues à
12,1–12,2 Go/s un quart d'heure plus tard. La variable est le temps (la charge des autres sur la carte
et la PCIe), pas la taille. Le niveau bas (≈ 3,8 Go/s) ressemble au plafond d'un lien Gen 2 ×8
(4 Go/s) ; le lien change bien de génération (Gen 1 à Gen 4 relevées), mais je n'ai pas relevé la
génération pendant les séries lentes : hypothèse, pas mesure.

**Second chemin, indépendant** : l'étude 04 a mesuré par le runtime CUDA (`pcie-1.json`) 6,4 Go/s en
mémoire épinglée à 256 Mio, sous charge : c'est dans la plage de mes séries chargées (4,4–6,3), et
loin de mes 12,2 au calme. Les deux chemins se rejoignent ; le chiffre de 6,4 n'était pas un plafond
de CUDA mais un état de la machine.

## 5. La carte

### 5.1 VRAM [mes.]

Shader de lecture (somme de `vec4<u32>` sur 512 Mio, 1 536 groupes de 256 fils, somme vérifiée
contre le processeur ; `--fausser` la fait échouer) : **251,3 Go/s** (Vulkan, deux séries ; DX12
251,3 puis 216,5 sous charge). **98,2 % du plafond de 256 Go/s.** Copie carte → carte (lecture +
écriture) : 226–231 Go/s à 32–64 Mio, 167–237 à 96–256 Mio selon la charge. En dessous de 32 Mio les
copies dépassent 256 Go/s (L2) : attendu, et c'est le témoin positif du cache.

### 5.2 Calcul [mes.] (`alu`, chaînes indépendantes, horodatages de la carte)

| | Vulkan | DX12 (wgpu, sans DXC) |
|---|---|---|
| FMA f32 | 10,6 – **12,6 T flop/s** | 6,9 – 12,7 |
| FMA f16 (`enable f16`) | 11,3 – **13,4** | indisponible (wgpu sur DX12 n'expose ni f16 ni sous-groupes sans DXC) |
| dot4I8Packed | **12,3 T op/s** | 2,9 – 3,3 |
| décodage 4 bits (décalage, masque, conversion, FMA) | **2,61 T op/s = 1,31 T poids/s** | 2,31 |

Témoins : f32, dot4i8 et deq4 comparés à une référence processeur exécutant la même suite
(écart 0, 0 et 4e-7) ; `--fausser` les fait échouer (37 %, 1 %, 1 %). Le f16 n'a pas de référence
exacte (débit seul). Plafond f32 calculé : 24 SM × 128 voies × 2 × 2,67 GHz (horloge relevée) =
16,4 T flop/s ; mesuré 77 %.

### 5.3 GEMV : la multiplication matrice-vecteur, le cœur d'un jeton [mes.]

| Noyau | Poids | Vulkan | DX12 |
|---|---|---|---|
| f16, 8192 × 8192 | 128 Mio | **250,1 / 243,4 Go/s** (537 µs) | 216,5 / 251,4 |
| q4 naïf (Q4_0 : 16 o + échelle f16 par bloc de 32, 4,5 bits), 32768 × 8192 | 144 Mio | 95,3 – 113,5 | 31,9 |
| q4b (64 fils par ligne, 4 lectures en vol par fil) | 144 Mio | **118,9 – 122,0** (une passe à 52,5 sous charge) | |
| q4, poids en RAM hôte (zéro copie, lus à travers la PCIe) | 144 Mio | **11,75 / 11,39** | 11,5 / 9,4 |
| q4, poids dans un tampon `MAP_WRITE` (BAR) | 144 Mio | 95,3 / 113,4 (= VRAM) | 8,8 / 11,9 (= RAM hôte) |
| q4, lot de 8 vecteurs | | 14,4 / 11,8 | 0,56 / 1,35 |
| f16, lot de 8 vecteurs | | 117,6 / 115,3 (941 Gflop/s) | 48,2 / 47,1 |

Témoins : écart relatif à une référence f64 sur 64 lignes ≤ 6,2e-9 pour toutes les passes ;
`--fausser` (référence décalée de 1 %) les fait toutes échouer.

Ce que cela dit :
- **f16 atteint la VRAM** : la machine sait lire ses 251 Go/s dans un vrai calcul.
- **Le 4 bits plafonne à 122 Go/s avec mes noyaux** alors que le décodage pur depuis les registres
  coûte 1,31 T poids/s, soit 2,6 fois ce que la VRAM livre (251 Go/s = 0,45 T poids/s à 4,5 bits).
  Le manque est dans le noyau (accès aux échelles et à x, parallélisme mémoire), pas dans la machine.
  C'est un trou chiffré pour l'étude du noyau (02-quantification a son propre banc).
- **Zéro copie** : la carte calcule une GEMV dont les poids restent en RAM hôte à 11,75 Go/s, soit le
  débit de la DMA (12,2). Pour un modèle plus gros que la VRAM, on peut donc consommer les poids
  directement depuis la RAM épinglée, sans tampon de transit en VRAM, au prix d'un passage par jeton.
- **Les lots** : mes noyaux relisent x pour chaque bloc ; à 8 vecteurs ils s'effondrent (q4) ou
  plafonnent à 941 Gflop/s (f16). Ce n'est pas le plafond de calcul (12,6 T) : noyau à refaire avant
  tout usage en décodage spéculatif.
- **DX12 par wgpu est à écarter** pour ces noyaux : sans DXC, pas de f16 ni de sous-groupes, et le
  q4 tombe à 32 Go/s. Vulkan est le chemin.

### 5.4 Thermique, 5 minutes, et la découverte de la batterie [mes.]

`pilote_thermique.py` lance la GEMV q4b en boucle (`carte.exe thermique`, 20 GEMV par soumission,
débit par tranche de 5 s) et relève nvidia-smi chaque seconde (température, horloges, puissance,
raisons de bridage `clocks_throttle_reasons.active`, génération du lien). Règle déclarée avant
(`00-seuils-declares.md`) : bridage si les 30 dernières secondes tombent sous 95 % des 30 premières.
Analyse : `analyse_thermique.py`.

| Passe | Alimentation | Débit 30 premières s → 30 dernières | Rapport | Bruit (écart type des tranches) | Horloges sous charge | Puissance | Raisons de bridage | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 (03:27, `thermique.log`) | secteur | 77,75 → 77,85 Go/s | **1,001** | 6,3 % | SM 2 685 MHz, mémoire 8 101 MHz | 72,5 W médiane, 79,1 max | aucune | **pas de bridage** ; 75 °C au plus |
| 2 (07:25, `thermique-batterie.log`) | **batterie** | 60,91 → 60,04 Go/s | 0,986 | 6,1 % | SM 2 100 (min 1 110), **mémoire 6 001 MHz** | 38,6 W médiane, 49,3 max ; **plafond imposé 52,6 W** | plafond de puissance logiciel et thermique logiciel, sur **chaque** relevé chargé | pas de dérive sur 5 min, mais **bridée dès la première seconde** |

Ce que cela dit :
- **Sur secteur, la carte tient 5 minutes de GEMV sans brider** : aucune raison de bridage active,
  horloge constante, 75 °C. La règle des 95 % est tenue avec un bruit de 6 %, plus large que les
  2,5 % supposés en déclarant le seuil : je le dis, la règle reste lisible (le rapport est à 1,001).
- **Ce test n'est pas une charge maximale.** La boucle soumet 20 GEMV puis attend : la carte n'est
  occupée qu'à ~70 % et le débit (75 Go/s) est sous les 122 Go/s du banc q4b. C'est une charge de
  décodage, celle du projet, pas un test de puissance. La passe « thermique réelle » de
  `suite_secteur.py` (llama-bench, 16 × 256 jetons) la complétera.
- **Sur batterie, la machine est une autre machine** : le pilote abaisse la limite de puissance de
  la carte de 80 W (défaut ; 140 W au plus) à **52,6 W** (`enforced.power.limit`), la mémoire de la
  carte reste en P4 à 6 001 MHz (−25 % de débit de VRAM soutenu, soit 192 Go/s au plus au lieu de 256
  [calc.]), le lien PCIe redescend en Gen 3, et le processeur tourne vers 1,5 GHz
  (`Win32_Processor.CurrentClockSpeed` = 1 520). Mesures courtes sur batterie (`batterie-carte.log`) :
  la VRAM lue en rafale atteint encore 247,7 Go/s (la mémoire remonte à 8 001 MHz quelques
  secondes), la GEMV f16 tombe à 216 Go/s (−14 %), la DMA hôte → carte reste à 11,8 Go/s, mais
  **l'écriture du processeur dans le BAR tombe de 9,1 à 1,7 Go/s et `write_buffer` de 7,5 à 1,25 Go/s** :
  tout ce qui passe par le processeur s'effondre.
- Pour le projet : un chargeur de poids qui compte sur le processeur (décompression, copie) perd
  un facteur 4 à 6 sur batterie ; un chargeur qui ne fait que de la DMA et décode sur la carte
  perd peu. C'est un argument mesuré pour l'architecture B (§ 7.4).

### 5.5 Le lien PCIe change de génération

Relevé pendant les copies (`carte-lien-pcie.csv`) : Gen 1 au repos, Gen 4 sous charge, Gen 3 sur
batterie. Le chiffre de 3,2–4,3 Go/s des séries lentes (§ 4.2) ressemble à un lien Gen 2 × 8
(4 Go/s) ; non prouvé. **Toute mesure de transfert doit relever la génération du lien pendant la
mesure**, pas avant.

## 6. llama.cpp b11515, la base de comparaison

### 6.1 Protocole

`pilote_llama.py` lance `llama-bench` (b11515, `3d65c90d0`, moteur CUDA 12.4, carte RTX 4060 Laptop)
sur Qwen3.5-9B Q4_K_M (5 680 522 464 octets, 8 953 803 264 paramètres), génération seule (`-p 0
-n 48 -r 3`), une configuration par processus, en ordre ABBA. Pendant la vie du processus : ensemble
de travail de pointe et mémoire privée engagée de pointe (`GetProcessMemoryInfo`), fautes de page,
VRAM de toute la carte (nvidia-smi, valeur au repos notée juste avant). Depuis ce matin : source
d'alimentation avant et après, échantillons par répétition (`samples_ts`), et `-ncmoe` pour les
modèles MoE.

### 6.2 Ce qui est mesuré [mes.] (`llama-base.jsonl`, premier passage, interrompu après 3 sur 12)

| -ngl | chargement | jetons/s | écart type | ensemble de travail de pointe | mémoire privée de pointe | VRAM ajoutée | fautes de page |
|---|---|---|---|---|---|---|---|
| 99 (tout en VRAM) | mmap | 16,5 | 1,2 | 5 279 Mio | 5 832 Mio | 5 118 Mio | 1 376 607 |
| 99 | lecture directe (`-lm none`) | **34,1** | 5,4 | **964 Mio** | 6 367 Mio | 5 083 Mio | 270 240 |
| 24 (sur 32 couches) | mmap | **2,8** | 2,1 | 5 296 Mio | 4 677 Mio | 7 114 Mio | 1 563 456 |

Lecture prudente :
- **34,1 jetons/s tout en VRAM, soit 69 % du toit de 49,3** (§ 7). C'est la base : le noyau 4 bits
  de llama.cpp sous CUDA fait mieux que mes 122 Go/s (34,1 × 5,10 = **174 Go/s** de poids lus
  [calc.], 69 % de la VRAM).
- **mmap contre lecture directe, tout en VRAM : 16,5 contre 34,1.** En génération, les poids sont en
  VRAM dans les deux cas ; une différence d'un facteur 2 ne vient pas du chargement. Pendant ces
  passes, d'autres agents faisaient tourner llama-perplexity sur la même carte ; la VRAM ajoutée de
  la passe -ngl 24 (7 114 Mio, plus que la passe tout en VRAM) prouve qu'un autre processus a pris
  de la VRAM pendant la mesure. **Je ne retiens que l'ordre de grandeur ; l'ABBA complet est en
  attente du secteur.** Ce qui est sûr : en mmap, l'ensemble de travail garde les 5,3 Gio du fichier
  projeté (pages du cache de fichiers comptées au processus), en lecture directe il retombe à
  964 Mio une fois les poids copiés sur la carte.
- **-ngl 24 : 2,8 jetons/s.** Huit couches sur 32 restent au processeur (≈ 1,3 Go de poids lus par
  jeton en RAM [calc.]) : la génération tombe d'un facteur 12. Le processeur lit ses couches à
  ≈ 1,3 Go × 2,8 = 3,6 Go/s effectifs [calc.], loin des 15,6 Go/s de la RAM : il était chargé (un
  autre agent occupait 8,7 cœurs) et la mémoire libre était de 1 à 2 Gio (les pages projetées se
  relisaient du disque : 1,56 million de fautes).

### 6.3 Ce qui reste à mesurer (suite secteur, prête)

`suite_secteur.py`, étape `llama_9b` : 99:none, 99:mmap, 24:mmap, 16:mmap, 16:none, 8:mmap, ABBA ;
étape `llama_20b` : gpt-oss-20b MXFP4 (12,1 Go, plus gros que la VRAM ; empreinte vérifiée par
l'orchestrateur), -ngl 99 avec les experts de 12 puis 24 couches sur le processeur (`-ncmoe`) ;
étape `thermique_llama` : 16 × 256 jetons. Chaque passe dit si elle a tourné sur secteur.

## 7. Le toit

### 7.1 Le modèle

Un jeton de décodage lit B octets de poids (tous les poids utilisés, une fois). Les poids résident
sur trois étages : une fraction f_V en VRAM, f_R en RAM hôte, f_D sur le disque (f_V + f_R + f_D = 1),
la part disque stockée compressée d'un facteur r (octets servis / octets stockés). Chaque étage i a
un débit effectif D_i mesuré : D_VRAM = 251,3, D_PCIe = 12,2, D_disque = 2,82 Go/s
(`debits-mesures.json`, chaque valeur avec son journal).

Octets qui traversent chaque étage par jeton :

- **architecture A** (le processeur décompresse, la PCIe porte les octets servis) :
  O_VRAM = f_V·B, O_PCIe = (f_R + f_D)·B, O_disque = f_D·B / r, et le décodeur du processeur doit
  sortir f_D·B ;
- **architecture B** (la carte décompresse, la PCIe porte les octets compressés) :
  O_VRAM = f_V·B, O_PCIe = (f_R + f_D / r)·B, O_disque = f_D·B / r, et le décodeur de la carte doit
  sortir f_D·B, de préférence fusionné à la GEMV (décodé dans les registres, jamais réécrit en VRAM).

**Proposition 1 (borne de débit d'une chaîne d'étages).** Quel que soit l'ordonnancement, le temps
par jeton vérifie t ≥ max_i O_i / D_i ; sans aucun recouvrement, t = Σ_i O_i / D_i.

*Démonstration.* L'étage i ne peut pas faire passer plus de D_i octets par seconde ; il doit en faire
passer O_i pour le jeton : il lui faut au moins O_i / D_i secondes, et le jeton ne peut pas finir
avant que chaque étage ait fini sa part. D'où la borne inférieure. Si les étages travaillent l'un
après l'autre sans se recouvrir, les temps s'additionnent. ∎

La borne inférieure est atteinte en régime permanent quand chaque étage est alimenté sans trou :
double tampon entre étages, et les poids de la couche ℓ + 1 en vol pendant le calcul de la couche ℓ.
Les deux cas encadrent toute réalisation : le plafond est 1 / max, le plancher sans recouvrement
1 / Σ. Les deux colonnes de `toit-placements.csv` les donnent.

**Corollaire 2 (le facteur de croisement).** En architecture A, avec tous les poids hors VRAM sur le
disque (f_R = 0), le disque cesse d'être l'étage limitant dès que f_D·B / (r·D_disque) ≤ f_D·B / D_PCIe,
soit

  r ≥ r\* = D_PCIe / D_disque = 12,2 / 2,82 = **4,33** [calc. sur mesures].

Au-delà, compresser davantage ne sert plus à rien en A : la PCIe porte les octets servis. Avec une
part f_R en RAM, le seuil devient r\* · f_D / (f_R + f_D), plus petit.

**Corollaire 3 (en architecture B, il n'y a plus de croisement).** Disque et PCIe portent tous deux
f_D·B / r : le disque, plus lent, reste limitant, et le plafond du flux disque croît comme
r · D_disque jusqu'à ce que le décodeur de la carte ou la VRAM le borne. Borne haute du décodeur
mesurée : 1,31 T poids/s décodés depuis les registres (§ 5.2), soit 1,31e12 × 5,08 / 8 = **832 Go/s
servis** [calc.] ; ce n'est pas une borne de décodage entropique (03-entropie mesure les siens).

### 7.2 Les plafonds par étage [calc. sur mesures] (`toit-modeles.csv`)

| Modèle | B (Go/jeton) | tout en VRAM | tout par la PCIe | tout du disque, r = 1 | tout du disque, r = r\* |
|---|---|---|---|---|---|
| Qwen3.5-9B Q4_K_M | 5,10 | **49,3** | 2,39 | **0,55** | 2,39 |
| Qwen3.5-4B Q4_K_M | 2,73 | 92,1 | 4,47 | 1,03 | 4,47 |
| gpt-oss-120b MXFP4 (routage uniforme) | 3,60 | 69,8 | 3,39 | 0,78 | 3,39 |
| Qwen3.8-Flash-Next UD-Q2_K_XL | 4,44 | 56,6 | 2,75 | 0,64 | 2,75 |
| Kimi-K2.6 UD-Q2_K_XL | 15,42 | 16,3 | 0,79 | 0,18 | 0,79 |

(B des MoE : toujours-lus + experts lus par jeton, d'après 06-modeles, § 0.)

### 7.3 Le placement réel sur cette machine (`toit-placements.csv`)

Hypothèses de 06-modeles (§ 5.1), gardées pour que les deux études se comparent : 6,5 Go de VRAM et
11 Go de RAM pour des poids. Les toujours-lus d'abord en VRAM, puis RAM, puis disque ; les experts
remplissent le reste dans le même ordre ; routage uniforme, aucun cache dynamique (la borne
pessimiste ; le cache d'experts est l'objet de 04 et 06). Architecture A.

| Modèle | Go/jeton VRAM / RAM / disque | r = 1 (recouvert ; série) | r = 2 | r = r\* = 4,33 |
|---|---|---|---|---|
| gpt-oss-120b MXFP4 | 1,84 / 0,34 / 1,42 | **1,98 ; 1,53** | 3,97 ; 2,48 | 6,93 ; 3,73 |
| Qwen3.8-Flash-Next UD-Q2_K_XL | 3,58 / 0,13 / 0,73 | 3,85 ; 2,90 | 7,69 ; 4,65 | 14,1 ; 6,89 |
| Kimi-K2.6 UD-Q2_K_XL | 6,50 / 2,21 / 6,71 | 0,42 ; 0,32 | 0,84 ; 0,51 | 1,37 ; 0,76 |

**Second chemin, et ce qu'il corrige.** `modeles_physique.py` (06) donne 5,1–5,6 jetons/s pour
gpt-oss-120b. Refait avec ses propres hypothèses, mon outil retrouve le même ordre (1,42 Go/jeton à
7,877 Go/s = 0,18 s, soit 5,5 jetons/s) : les deux modèles s'accordent. **L'écart vient du débit du
disque** : 06 prend le plafond du lien (7,877 Go/s), le disque mesuré livre 2,82. **Le plafond
réel de gpt-oss-120b sur cette machine, sans cache et sans compression, est ≈ 2 jetons/s, pas 5,5.**
06 suppose aussi que les experts trouvés en RAM sont calculés par le processeur à 41,6 Go/s
(plafond du module) ; le meilleur débit du processeur mesuré est 15,6 Go/s (§ 3).

### 7.4 Le budget du décodeur, et pourquoi B

À débit d'entrée compressé égal à la PCIe (12,2 Go/s, architecture A au croisement), la carte a
2,61e12 / 12,2e9 ≈ **214 opérations par octet compressé** [calc.] ; au débit du disque (2,82 Go/s,
architecture B), **926**. Un décodeur rANS fait de l'ordre de la dizaine d'opérations par symbole :
le calcul n'est pas la borne, la question est le parallélisme et l'accès mémoire du décodeur
(03-entropie).

Plafond du 9B entièrement sur disque (`toit-9b-compression.csv`) :

| r | 1 | 2 | 4,33 | 8 | 16 |
|---|---|---|---|---|---|
| A (processeur décode) | 0,55 | 1,11 | 2,39 | 2,39 | 2,39 |
| B (carte décode) | 0,55 | 1,11 | 2,39 | **4,42** | **8,85** |

**Trois raisons mesurées de préférer B** : (1) en A, tout facteur au-delà de 4,33 est perdu ; (2) en
A, le processeur paie déjà ≈ 0,3 s de cœur par Go pour BitLocker (§ 2.7) avant toute
décompression ; (3) sur batterie, tout ce qui passe par le processeur perd un facteur 4 à 6 alors que
la DMA reste à 11,8 Go/s (§ 5.4). Et la carte sait consommer des poids sans les copier en VRAM
(zéro copie, 11,75 Go/s, § 5.3).

**Ce que r = 4,33 veut dire en bits.** Le Q4_K_M sert 5,08 bits par poids ; stocké à r\* = 4,33, il
tiendrait en **1,17 bit par poids** sur le disque. Aucun code entropique sans perte n'y arrive sur des
codes 4 bits (03-entropie mesure des gains de l'ordre de 10 %) : r\* ne s'atteint qu'en changeant de
représentation (quantification à 1–2 bits, codebooks, treillis : 02-quantification). Sur un
gros modèle MoE, la compression n'est d'ailleurs pas le seul levier : le taux de succès du cache
d'experts multiplie l'effet de r (04, 06).

## 8. Ce que je crois manquer dans le monde

1. **Un toit mesuré, pas annoncé, pour l'inférence hors mémoire sur portable.** Les travaux
   d'inférence depuis le stockage (FlexGen, LLM in a Flash, PowerInfer et leurs suites, lus par
   04 et 05) raisonnent sur des débits de fiche technique ou de station de travail. Sur cette
   machine, le disque livre **47 % de son annonce** (2,82 contre 6,0 Go/s) parce que le volume est
   chiffré et passe par Intel RST VMD, deux réglages par défaut d'un portable Windows grand public.
   Je ne connais pas de travail qui chiffre ce « coût du portable réel » ; un plafond calculé au
   lien est ici faux d'un facteur 2,8.
2. **Le régime batterie.** Aucun banc d'inférence que j'ai lu ne note la source d'alimentation. Ici
   elle change la limite de puissance de la carte (80 → 52,6 W), l'horloge de sa mémoire (8 → 6 GHz),
   la génération du lien (4 → 3) et divise par 4 à 6 tout ce qui passe par le processeur. Un
   chargeur pensé pour un portable doit être jugé dans les deux régimes.
3. **Le coût processeur de BitLocker pour un flux de poids** : ≈ 0,25 à 0,3 s de cœur par Go
   (mesuré ici), et la question ouverte de savoir si fvevol parallélise (le processeur sait
   déchiffrer 8,7 Go/s, le disque plafonne à 2,8 quelle que soit la profondeur de file).
4. **La décompression sur la carte, fusionnée à la GEMV, alimentée par DMA depuis la RAM épinglée
   ou en zéro copie, sous Vulkan.** DirectStorage décompresse sur la carte (GDeflate, Zstd en 1.4)
   mais vers des ressources Direct3D 12 et pour des textures ; les moteurs d'inférence décodent leurs
   formats 4 bits sur la carte mais lisent des poids déjà en VRAM. Le chemin « disque → RAM épinglée →
   PCIe (octets compressés) → décodage dans les registres de la GEMV » n'existe, à ma connaissance,
   nulle part sous Vulkan ; c'est l'architecture B, et ce banc montre qu'elle seule tire parti d'un
   facteur r au-delà de 4,33.
5. **Un noyau 4 bits Vulkan au niveau de la VRAM** : mes noyaux plafonnent à 122 Go/s (48 %),
   llama.cpp sous CUDA atteint ≈ 174 Go/s effectifs (69 %) ; la machine en offre 251 et sait décoder
   2,6 fois plus vite que la VRAM ne livre. Le manque est un noyau, pas du matériel.

## 9. Ce qu'il faut demander à Stone

Réponses par délégation (SOCLE, « gratuit, au top du top ») là où c'est possible ; restent à lui les
gestes sur sa machine.
- **Brancher le portable pendant les mesures.** `suite_secteur.py` attend 120 s de secteur et
  relance seule tout ce que la batterie a faussé (disque, AES, RAM, carte, llama.cpp 9B et 20B,
  thermique). Geste de Stone ; sans lui, les chiffres RAM et llama.cpp de cette étude restent
  provisoires.
- **Ce que BitLocker coûte vraiment au disque.** Le seul test qui tranche est une lecture sans
  déchiffrement : un second volume non chiffré (une clé USB 3.2 rapide ou un SSD externe ne mesure
  pas le même disque), ou une suspension temporaire de BitLocker. **Je ne recommande pas de
  suspendre BitLocker** : c'est la protection de ses données si le portable est volé, et le gain
  attendu (≤ 2,1 fois sur le disque) ne vaut pas ce risque pour une mesure. Réponse par délégation
  du 2026-10-15, réversible : on garde BitLocker et on conçoit pour 2,8 Go/s.
- **Un second module de RAM** (16 Gio DDR5-5600 SODIMM) doublerait capacité et débit du processeur.
  C'est son argent ; je le note, je n'en décide pas.
- **DirectStorage** : le paquet NuGet 1.3.0 pèse 2,8 Mo (sous le seuil de 500 Mo) ; un agent peut
  le prendre pour mesurer GDeflate et Zstd sur la carte, sous licence Microsoft à lire d'abord.
  Réponse par délégation du 2026-10-15, réversible : à faire par l'étude 04 si l'architecture B
  doit être comparée à DirectStorage.

## 10. Ce qui pourrait être faux

- **La machine n'a jamais été au calme.** Toutes les mesures ont tourné avec d'autres agents
  (llama-quantize, llama-perplexity, scripts) ; les chiffres « au mieux » sont des bornes inférieures
  du repos. Le plafond du disque (2,82 Go/s) est le plus exposé : le compteur du système montre
  jusqu'à 0,6 Go/s de lectures étrangères au passage A.
- **Le toit suppose des débits additifs indépendants.** En réalité, la RAM est partagée entre la DMA
  vers la carte, la lecture du disque et le processeur ; un seul module à 41,6 Go/s au plus, déjà
  occupé par BitLocker et les autres. Le recouvrement parfait (max) peut être inatteignable ; la
  colonne « en série » encadre par le bas.
- **B = 5,10 Go/jeton** ignore le cache KV, les activations et la tête de sortie si elle est partagée :
  juste pour un contexte court (c'est le cas des bancs), trop bas pour un long contexte.
- **L'identification du disque au PM9C1a** (6,0 Go/s annoncés) est probable, pas prouvée.
- **La latence RAM de 1 µs attribuée à la traduction imbriquée (VBS/HVCI)** est une hypothèse ;
  le processeur à 1,5 GHz sur batterie et la charge des autres l'expliquent peut-être autant.
- **Les mesures de llama.cpp sont contaminées** (une autre charge sur la carte, preuve : la VRAM
  ajoutée de la passe -ngl 24). L'écart mmap / lecture directe (16,5 contre 34,1) n'est pas un fait.
- **Le test thermique n'est pas une charge maximale** (~70 % d'occupation, 72 W sur 80) : « pas de
  bridage » vaut pour une charge de décodage, pas pour une charge de puissance.
- **La borne du décodeur de la carte (832 Go/s servis)** mesure un décodage de champs 4 bits depuis
  les registres ; un décodeur entropique réel (rANS, tANS) a d'autres goulets (dépendances série par
  flux, lectures de tables) et peut être bien plus lent.
- **La clé XTS de BitLocker (128 ou 256 bits) n'est pas connue** ; l'écart est ≈ 10 %.

## 11. Recettes (essayées, avec leur raison)

| Recette | Marche ? | Raison |
|---|---|---|
| Lecture sans tampon `FILE_FLAG_NO_BUFFERING` + motif vérifiable par page | oui | prouve que chaque octet vient du disque, pas d'un cache ni d'un tampon recyclé ; `--fausser` le fait tomber |
| Fichier de test de 2 × la RAM | oui | déjoue le cache même si le drapeau était ignoré |
| Second chemin par le compteur cumulé `Win32_PerfRawData_PerfDisk_PhysicalDisk` | oui, sauf un trou de 14 s | typeperf refuse les noms anglais sur Windows en français ; les classes CIM les gardent |
| Témoin « le cache relu dépasse le lien » | **non, barré** | la copie depuis le cache de Windows est bornée par un fil de processeur (3,1 Go/s) |
| IoRing contre IOCP | égalité | sur ce disque, la borne n'est pas la soumission ; IoRing coûte un peu moins de processeur |
| BypassIO | refusé | BitLocker (fvevol) ; pilote iaStor (VMD) |
| Tampon `MAP_WRITE` de wgpu comme source « hôte » sous Vulkan | **piège** | le pilote le place en VRAM visible (BAR) : la copie mesurée était VRAM → VRAM (80–220 Go/s) ; le témoin de plafond l'a levé |
| Tampon `MAP_READ` comme source DMA (`MAPPABLE_PRIMARY_BUFFERS`) | oui | vraie DMA depuis la RAM hôte, 12,2 Go/s |
| GEMV en zéro copie sur la RAM hôte | oui | 11,75 Go/s, la carte calcule au débit du lien sans tampon de transit |
| DX12 par wgpu sans DXC | à écarter | ni f16 ni sous-groupes ; q4 à 32 Go/s |
| RAM sans verrou des pages sous mémoire maigre | **non** | Windows compresse les pages du banc ; ajouter `VirtualLock` et compter les fautes |
| Témoin des fautes de page forcé à faux par un tampon neuf | oui | 197 033 fautes pour 196 608 pages : l'instrument voit les fautes |
| XTS-AES par CNG (`bcrypt.dll`) depuis Python, une clé par fil | oui | mesure le coût de BitLocker sans droits d'administrateur ; vecteur IEEE 1619 comme témoin |
| Relever la source d'alimentation à chaque passe | **indispensable** | la batterie change la machine (52,6 W, mémoire de carte à 6 GHz, processeur à 1,5 GHz) |
| Boucle de GEMV soumise par paquets de 20 avec attente | charge partielle | ~70 % d'occupation : bon test de décodage, mauvais test de puissance |
| Attendre le secteur dans un script qui relance seul la suite | à éprouver | `suite_secteur.py` ; marque « batterie » toute étape faussée et la refait |
