# Lot F : verdicts de F2 et F3 contre les seuils déclarés

Seuils : `00-seuils-declares.md` (13 h 05 pour F2 et F3, 15 h 40 pour l'ajout de la mémoire
bornée), tous écrits avant le lancement qu'ils jugent. Chiffres : les journaux de ce dossier
(chaque ligne nomme le sien). Toutes les passes sur secteur (`BatteryStatus` = 2 au début et à la
fin, `*.cadre.txt`). Aucun débit n'est jugé ici.

## C1 : 100 % des experts décodés égaux à l'original

| Grandeur | Seuil | 20b (`verifier-20b.json`) | 120b (`verifier-120b.json`) | Verdict |
|---|---|---|---|---|
| experts exacts (cinq contrôles chacun) | 0 faux | 768 sur 768 | **4 608 sur 4 608** | tient |
| contrôles faux : empreinte de partie, décodage, octets, empreinte du décodé, empreinte des tranches du GGUF | 0 | 0, 0, 0, 0, 0 | 0, 0, 0, 0, 0 | tient |
| résidents égaux (octets et empreinte) | 0 faux | 315 sur 315 | 471 sur 471 | tient |
| méta : paires du GGUF octet pour octet + trois paires du codeur | identique | oui | oui | tient |
| en-tête contre GGUF (couches, experts, k, dimensions, MXFP4, taille source) | tout juste | oui | oui | tient |
| SHA-256 du GGUF, recalculée par le codeur puis par la vérification | = `telechargements.json` | 27cd6c43…5901, deux fois | 582bd40f…622d, deux fois | tient |
| cassure en mémoire (`--casser`) | exactement l'expert visé faux | (7, 13) seul (`verifier-20b-casse-memoire.json`) | (29, 101) seul (`verifier-120b-casse-memoire.json`) | tombe là où il faut |
| cassure sur une vraie copie (`casser_copie.py`, un octet changé, vu par `cmp -l`) | idem | (17, 29) seul (`casser-copie-20b.txt`) | non faite (déclaré : 57,7 Go de copie) | tombe |

Dans chaque cassure, les contrôles « empreinte de partie », « octets » et « empreinte du
décodé » tombent ; « décodage » tient (une médiane faussée ne dérange pas le rANS : elle change
e = méd + δ − 128, pas les flux) ; « empreinte des tranches du GGUF » tient (la source n'est pas
touchée). C'est le motif attendu, et il dit que les cinq contrôles ne sont pas redondants.

## Taux

| Grandeur | Seuil | Mesuré | Verdict |
|---|---|---|---|
| 20b, 12 tenseurs de F1 : octets des codes et de δ, total A_ctx, tronçons | identiques à F1 | égaux au millionième ; 3,843137 = 3,843137 ; 11 990 368 / 11 837 440 / 12 144 640 (`comparer-f1-20b.json`) | tient |
| 20b, r₀₃ (72 tenseurs) | à 0,1 % de 1,1037 | 1,103732 (écart 2,9·10⁻⁵) | tient |
| 120b, r₀₃ (108 tenseurs) | à 0,1 % de 1,1026 | **1,102592** (écart −7,7·10⁻⁶ ; `comparer-03-120b.json`) | tient |
| taille du `.trc`, 20b | repère à 1 % de 11,1 Go | 11 157 405 696 o (+0,52 %) | dans le repère |
| taille du `.trc`, 120b | repère à 1 % de 57,65 Go | **57 730 662 400 o** (+0,14 %) | dans le repère |
| plus grand tronçon (§ 4.14, « à relever ») | publié | 20b : 12 144 640 o ; **120b : 12 251 136 o** | publié |

Bits par poids du 120b (comptabilité de 03) : codes 3,820169, δ 0,031609, médianes 0,002778,
total 3,854555 ; avec les tables (224 656 o) 3,854571. Tronçons du 120b : 11 763 712 à
12 251 136 o, 12 026 060 en moyenne, contre 13 253 760 à l'origine (r = 1,102087 tronçons
complets, en-têtes, biais et bourrage compris).

## Mémoire bornée (ajout de 15 h 40)

| Grandeur | Seuil | Mesuré (`csv/pointes-memoire.csv`) | Verdict |
|---|---|---|---|
| témoin d'identité : 20b recodé à deux passes contre F2 | SHA-256 égale | e8bd6ae1…169f des deux côtés ; la copie cassée : c40f1163…7123 (`identite-20b-2passes.txt`) | tient ; l'instrument tombe |
| lecture sans tampon | test et 4 cassures | 4 sur 4 tombent, le test tient restauré (`casser-lecture.log`) | tient |
| pointe 20b, deux passes ≤ une passe (repère) | codeur ≤ 0,65 Go, vérification ≤ 1,28 Go | 0,379 Go ; 0,418 Go | dans le repère |
| **pointe 120b ≤ 1,25 × pointe 20b** | codeur, vérification | codeur 0,391 / 0,379 = **1,033** ; vérification 0,430 / 0,418 = **1,028** | tient |

Le 120b, cinq fois plus gros, se code et se vérifie dans la même fenêtre de 0,4 Go que le 20b :
la mémoire de l'outil ne dépend plus de la taille du modèle (proposition 7, `derivations.md` § 8).

## Durées (pour information, machine partagée, pas d'ABBA)

| Passe (champ `duree_s` du journal) | Durée |
|---|---|
| codeur 20b, une passe (13 h 05) | 1 005,3 s |
| codeur 20b, deux passes (15 h 42) | 188,6 s |
| codeur 120b, deux passes | 1 153,3 s (19 min 13 s) |
| vérification 20b, une passe / bornée | 136,7 s / 89,3 s |
| vérification 120b (SHA-256 comprise) | 471,2 s |

La version à deux passes lit deux fois plus et va pourtant cinq fois plus vite sur le 20b : ce
n'est **pas** un effet du code qu'on puisse affirmer. À 13 h 05, cinq lots compilaient et la
mémoire était saturée (la version à une passe a pu paginer) ; à 15 h 42, non. Ce n'est pas une
série ABBA, et aucune conclusion de vitesse n'en est tirée.

## Second chemin de C1 (ajout du 2026-10-15, 20 h 53 à 21 h 06)

Seuils : `00-seuils-declares.md`, ajout de 20 h 50 (commit c87c562, avant le premier lancement).
Outil : `second_chemin_c1.py` (Python, bibliothèque standard, écrit depuis le seul § 4 et la
spécification GGUF v3 ; aucune ligne commune avec `trc-format`, `trc-codec` ou le lecteur GGUF du
codeur, que je n'ai pas relus pour l'écrire). Lancement : `lancer_py.ps1`, priorité sous la normale,
4 fils, lectures sans tampon, verrou de la carte tenu pendant les passes. Toutes sur secteur
(`BatteryStatus` = 2 au début et à la fin de chaque passe). CSV : `csv/second-chemin-c1.csv`.

| Grandeur | Seuil | 20b (`second-chemin-20b.json`) | 120b (`second-chemin-120b.json`) | Verdict |
|---|---|---|---|---|
| lecteur Python contre lecteur de llama.cpp (`ggml-base.dll` b11515) : version, tenseurs, paires, alignement, début des données ; nom, type, décalage, taille de chaque tenseur | 0 écart | 0 (459 tenseurs) | 0 (687 tenseurs) | tient |
| pavage de la zone de données | 0 trou | 0 | 0 | tient |
| SHA-256 du GGUF par `hashlib` (OpenSSL 3.0.18), lecture sans tampon | = téléchargement = en-tête | 27cd6c43…5901 | 582bd40f…622d | tient (troisième calcul, premier hors de `sha2`) |
| en-tête § 4.3 contre GGUF et § 4.3 | tout égal | oui | oui | tient |
| MÉTA : 36 paires du GGUF octet pour octet + 3 du codeur + empreinte64 | identique | oui | oui | tient |
| TABLES : enregistrements, sommes à 4 096, empreinte64 | 0 écart | 288 | 432 | tient |
| RÉPERTOIRE : empreinte64, rangs, alignements, contiguïté, niveau 1 vide | 0 écart | 0 | 0 | tient |
| **empreinte64 de l'expert d'origine refaite depuis le GGUF contre le répertoire** | **0 faux** | **0 sur 768** | **0 sur 4 608** | **tient** |
| BIAIS_j de chaque partie contre le GGUF, octet pour octet | 0 faux | 0 | 0 | tient |
| MEDIANES_j contre `tri[B/2]` refait depuis les échelles du GGUF | 0 faux | 0 | 0 | tient |
| empreinte64 de chaque partie ; en-tête, table des flux, en-têtes rANS, bourrage nul | 0 écart | 0 | 0 | tient |
| résidents : octets comparés au GGUF, empreinte64 | 0 faux | 0 sur 315 | 0 sur 471 | tient |

**Cassures** (`-casse.json`, `-casse-decalage.json`) : chacune tombe exactement où elle vise.

| Cassure | Attendu | 20b | 120b |
|---|---|---|---|
| `--casser-expert` (bit de codes) | cet expert seul, contrôle d'empreinte seul | (3, 7) : empreinte seule | (3, 7) : empreinte seule |
| `--casser-mediane` | cet expert seul, MEDIANES seul | (5, 9) : MEDIANES seul | (29, 101) : MEDIANES seul |
| `--casser-biais` (bit du biais de la matrice 2) | cet expert seul, empreinte et BIAIS | (11, 13) : empreinte et BIAIS | (35, 127) : empreinte et BIAIS |
| `--casser-parseur` | 1 écart contre llama.cpp | 1 (`output.weight`, 32 contre 0) | 1 |
| `--casser-sha` | SHA différente | différente | différente |
| `--casser-decalage` (tranche de l'expert x + 1) | tous les experts lus faux à l'empreinte | 768 sur 768 (et MEDIANES 768) | 256 sur 256, couches 0 et 1 (déclaré) |

Dans chaque passe de cassure, les autres experts restent justes : 3 faux sur 768 et 3 faux sur 4 608.
Le décalage fait aussi tomber les médianes (elles viennent des mêmes tranches) et laisse les biais
justes (ils ne sont pas décalés) : les contrôles voient chacun leur propre octet.

**Ce que cela établit.** La chaîne de C1 sur le 120b ne passe plus par un seul lecteur du GGUF :
expert décodé par `trc-codec` → empreinte du répertoire (`verifier-120b.json`, contrôle
« empreinte du décodé ») ; empreinte du répertoire ← tranches du GGUF lues par Python, aux
décalages que donnent à la fois Python et llama.cpp (ici). Les deux égalités portent sur une
empreinte de 64 bits : pour une erreur qui n'est pas fabriquée contre SHA-256, la probabilité
qu'un expert faux passe est de 2⁻⁶⁴ par expert, 4 608 · 2⁻⁶⁴ ≈ 2,5·10⁻¹⁶ sur le modèle
(`derivations.md` § 9). Les biais et les médianes, eux, sont comparés octet pour octet.

**Ce qu'il ne fait pas.** Il ne décode pas le rANS : le maillon « octets du tronçon → expert
décodé » n'a encore qu'un décodeur processeur sur le 120b (celui du lot F). Le décodeur de la
carte (lot K, `temoin-trc`) l'a refait sur le 20b ; sur le 120b, la commande est prête au lot K.
L'épreuve du § 8 (décodeur Python d'un juge depuis le seul § 4) reste la seule qui teste la
spécification elle-même.

## Ce qui pourrait être faux

- **C1 compare le décodeur processeur au GGUF par les mêmes fonctions de lecture que le
  codeur** (`gguf::lire_dans`). Une erreur systématique de lecture (un décalage) serait commune
  au codeur et à la vérification. Ce qui l'exclut : le témoin d'identité (le 20b recodé par la
  lecture sans tampon égale le fichier de F2, écrit par l'ancienne lecture avec tampon) ; le
  test unitaire de la lecture sur un contenu connu ; la SHA-256 du GGUF entier égale à celle du
  téléchargement ; et, à venir, l'épreuve indépendante (§ 8 : un décodeur Python écrit depuis
  le seul § 4, qui lit le GGUF par numpy). ~~Pour le 120b, seuls les trois derniers valent.~~
  Barré le 2026-10-15 à 21 h 05 : le second chemin (section suivante) relit le GGUF du 120b
  par deux lecteurs qui ne doivent rien à `gguf::lire_dans` (Python, puis llama.cpp) et retrouve
  les 4 608 empreintes du répertoire ; une erreur de lecture commune au codeur et à la
  vérification est donc exclue aussi sur le 120b.
- **La cassure de copie n'est faite que sur le 20b** ; sur le 120b, la cassure est en mémoire
  (même code de vérification, un bit retourné après la lecture).
- **Les pointes de mémoire** sont des ensembles de travail échantillonnés toutes les 0,5 s ; une
  pointe plus brève peut échapper. La marge de 25 % du seuil 120b/20b est déclarée, pas mesurée.
- **Le format n'a pas été relu par un juge** : les décalages qu'utilise `casser_copie.py` sont
  lus depuis le § 4 (en-tête, répertoire, table des flux), ce qui est un début de second chemin,
  pas l'épreuve.
- **Le second chemin est écrit par le lot F** : son auteur connaît les choix du codeur (les neuf
  précisions de `REPRISE-F.md`). Quatre de ses contrôles de structure en dépendent (longueur des
  sections, place de l'empreinte des résidents, contexte fixe, « octets produits » = P) : s'ils
  avaient été lus autrement, ils tomberaient sans que le fichier soit faux. Aucun ne touche les
  empreintes d'experts, qui ne dépendent que des § 4.7, 4.11 et 4.12 et de la spécification GGUF.
- **Le lecteur Python et le codeur partagent une lecture du § 4.11** (blocs puis biais, ordre
  gate, up, down ; `ne[0]` = colonnes). Si cette lecture était fausse au regard de llama.cpp,
  les deux seraient faux ensemble ; le § 4.11 l'écrit ainsi, et la passe avant de référence du
  lot R (lue dans le GGUF, jugée contre llama.cpp en R1) est le témoin qui la valide.
