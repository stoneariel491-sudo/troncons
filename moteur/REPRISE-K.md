# Reprise du lot K (noyaux)

Lot K : `moteur/crates/trc-noyaux/**` ; journaux et outils `mesures/moteur/K/**` ; sources
`memoire/sources/moteur-K.bib` ; note `moteur/K-pour-le-memoire.md`. Spécification :
`decisions/ARCHITECTURE.md` § 5.6 (couture N), § 4.8 à 4.11 (couture F), § 6.5 (K1, K2).

Construction : `CARGO_TARGET_DIR=~/dev/cibles/troncons-K`, `-j 4`, `--offline`.
`build.rs` appelle nvcc via vcvars64.bat si cl.exe n'est pas dans le PATH (CUDA_PATH par défaut :
`~/dev/outils/cuda-13.1.2`). Banc C++ : `banc/construire.bat` →
`~/dev/cibles/troncons-K/banc/banc_k.exe` (mêmes sources, mêmes options).

## Critères déclarés avant tout lancement (2026-10-15, 12 h 40)

### K1 — décodeur CUDA à table par voie (§ 6.5)
- Témoin : chaque expert des **108 tenseurs du 120b** (36 couches × gate, up, down ; 128 experts)
  codé par un codeur indépendant écrit depuis le seul § 4 (banc_k), décodé sur la carte, égal
  **octet pour octet** à l'emplacement tiré du GGUF (codes, échelles, biais, bourrage) ; 0 voie
  hors de L ; 0 erreur de format. Puis, quand le lot F aura commité : sortie = `trc-codec` sur
  les flux de F (second codeur).
- Cassure : une fente de LUT corrompue (CODES_CTX, κ = 1, matrice 0) → sortie fausse ; un bit
  retourné dans un flux → voies hors de L.
- Seuil : **≥ 0,8 × 41,6 = 33,3 Go/s de codes écrits**, jugé sur la **pire** passe A d'une série
  A B B A × 5 (A = décodage expert par expert, deux lancements chacun, comme le moteur ; B = copie
  brute des mêmes octets), carte verrouillée, sur secteur. 41,6 : la variante qu'il remplace
  (décodage + réassemblage des trois flux de classe, [mes. 03]) ; 0,8 = 1 − 2 × 10 % de bruit.
  Le débit compte les seuls octets de codes (le temps inclut DELTA, les échelles et les biais) :
  choix prudent.

### K1, variante C ajoutée (déclarée le 2026-10-15 à ~~15 h 45~~ 15 h 35, heure corrigée : la première écriture portait une heure à venir ; avant sa première mesure)
- C = les experts d'une couche décodés **en un lot** (`decoder_echelles_lot` puis
  `decoder_codes_lot`, grilles (X, 3, n), extension de la couture N : fonctions ajoutées, rien
  d'existant changé). Raison : modèle de latence (K-pour-le-memoire.md § 2) : un expert seul
  n'occupe la carte qu'avec 24 warps pendant DELTA ; le lot fait tourner les DELTA ensemble.
- Lot de **n = 4** (k de gpt-oss : au plus 4 défauts par couche en J1), dans la même série que A et
  B : ordre A B C C B A, 5 passes, pilote K1 inchangé sinon (`--experts 4` au lieu de 8 : 4 × 25 Mo restent ≫ 32 Mo de L2 ; A
  n'en dépend pas autrement).
- Témoin : C rend les mêmes octets que A (vérifié avant et après la série) ; seuil : **le même
  33,3 Go/s de codes sur la pire passe**. Le verdict de K1 reste celui de A, déclaré à 12 h 40 ;
  C est publié à côté, jamais à sa place.

### K1, variante D (déclarée le 2026-10-15 à 17 h 08, avant sa première mesure de débit)
- D = les flux DELTA codés en tuiles de **N = 32** macro-pas au lieu de 256 (le format porte N dans
  chaque flux, § 4.9.1, et le décodeur le lit : **aucun changement de format**, un choix du codeur).
  Raison : la passe propre de 16 h 46 donne DELTA 152 µs sur 347 µs par expert, une chaîne de 1 024
  sous-pas sur 24 warps (modèle, K-pour-le-memoire.md § 2.5).
- Justesse (20b couche 0, 8 experts, banc) : 0 faux à N = 32 et 64. Coût mesuré (banc) : DELTA
  891 296 → 1 026 448 o pour 8 experts, **+16,9 Ko par expert, +0,14 % du tronçon**.
- Prédiction écrite avant la mesure : T_DELTA ≈ 128 sous-pas × 150 à 170 ns ≈ 19 à 22 µs, d'où
  ≈ 216 à 220 µs par expert, **≈ 57 Go/s de codes (± 10 %)**. Seuil : le même 33,28 sur la pire
  passe ; mesure informative (le verdict de K1 reste celui de A).
- Si D tient, proposition au lot F (et à l'arbitre) : N_DELTA = 32 au codeur ; l'enveloppe Rust
  devra alors dimensionner la grille de DELTA sur le T lu dans la partie (aujourd'hui
  `abi::MACRO_PAR_TUILE` = 256 fixe : la grille resterait juste, mais trop petite).

### K2 — GEMV MXFP4 (§ 6.5)
- Témoin : exact au bit sur entiers (5 formes, dont 2 880 × 2 880, 37 × 96, 5 × 32 ; échelles
  2^-2 à 2^2) ; les 256 échelles E8M0 exactes (sous-normaux compris) ; écart relatif
  max|y − y64| / max|y64| ≤ 10⁻⁵ sur poids réels contre une référence f64 ; `gemv_mxfp4` et
  `gemv_mxfp4_lot` égaux au bit.
- Cassure : référence décalée de 1 % → tout tombe.
- Seuil : **≥ 0,8 × 209,4 = 167,5 Go/s de MXFP4 équivalents** (poids × 17/32), jugé sur la pire
  passe A (lot de 12 matrices = une couche) d'une série A B B A × 5, 24 emplacements (318 Mo ≫ 32
  Mo de L2), carte verrouillée, sur secteur.

### K3 — la passe avant, douze noyaux (§ 5.6, § 6.5), déclaré le 2026-10-15 à 20 h 45, avant tout code de K3
- Les douze : `gemv_mxfp4` (K2, rejugé ici contre `trc-reference`), `gemv_q8_0`, `gemv_f32`,
  `rmsnorm`, `rope_yarn`, `ecrire_kv`, `attention`, `routeur_topk`, `swiglu_oai`, `combiner`,
  `ligne_q8_0`, `argmax` (le tableau du § 5.6 moins `decoder_matrice` et `copier_brut`, de K1).
- **Témoin** : outil `mesures/moteur/K/temoin-k3/` (hors de l'espace du moteur, comme temoin-trc).
  Poids **réels** lus dans le GGUF d'origine par `trc_reference::gguf` (chemin indépendant du
  `.trc`), couches 0 (à fenêtre) et 1 (pleine) de gpt-oss-20b, puis de gpt-oss-120b (routeur à 128
  experts). Entrées réelles : des jetons tirés (graine publiée) passés par les opérations de
  `trc-reference` en f64. **Chaque noyau est jugé seul** : son entrée est la sortie f64 de la
  référence arrondie en f32 (les erreurs ne s'enchaînent pas), sa référence est l'opération
  correspondante de `trc-reference` (`ops::rmsnorm`, `ops::Rope::tourner`, `ops::attention_tete`,
  `ops::routeur_topk`, `ops::swiglu_oai`, `poids::Matrice::produit`, `poids::rangee_f64`) appliquée
  en f64 **aux mêmes valeurs f32**.
- **Mesure de l'écart** (celle de K2) : e = max_i |y_i − y64_i| / max_i |y64_i| sur le vecteur de
  sortie entier (par appel). Seuils, ceux du § 5.6 tels quels :
  - `gemv_mxfp4`, `gemv_q8_0`, `gemv_f32` : e ≤ 10⁻⁵ sur poids réels ; **exact au bit sur
    entiers** (matrices synthétiques dont chaque somme partielle est exacte en f32) ;
  - `rmsnorm`, `rope_yarn`, `swiglu_oai` : e ≤ 10⁻⁶ ;
  - `attention` : e ≤ 10⁻⁵ (par tête et sur la sortie entière ; le plus grand fait foi), aux
    longueurs 1, 127, 128, 129, 300 (couche à fenêtre, anneau de 128) et 1, 300, 4 096 (couche
    pleine) ;
  - `routeur_topk` : indices **égaux** à la référence, poids e ≤ 10⁻⁶ ; plus des logits
    synthétiques à égalités (règle : score décroissant puis indice croissant) ;
  - `combiner` : **égal au bit** à la même somme faite sur l'hôte en f32, même ordre
    ((w₀s₀ + w₁s₁) + w₂s₂) + w₃s₃, puis résidu + somme (la forme de `trc-reference`) ;
  - `ecrire_kv`, `ligne_q8_0` : **octets égaux** (f16 arrondi au plus proche pair de `half`
    2.7.1 ; Q8_0 → f32 exact, d·q tient en 18 bits) ;
  - `argmax` : **égal** à l'argmax de l'hôte sur les mêmes f32 (égalité : plus petit indice), sur
    les logits réels de la sortie (201 088) et sur des vecteurs synthétiques à égalités.
- **Déterminisme** (couture N) : chaque noyau lancé deux fois sur les mêmes entrées rend les mêmes
  bits ; aucun atomique flottant (relu dans la source).
- **Cassures** (`--casser <noyau>`, une par noyau, une vraie faute plausible injectée dans la
  référence ; seul le témoin visé doit tomber, les onze autres tenir) : gemv_mxfp4 échelle
  2^(e − 127) ; gemv_q8_0 et gemv_f32 biais omis ; rmsnorm moyenne sur n − 1 ; rope_yarn sans la
  concentration de YaRN ; ecrire_kv arrondi vers zéro ; attention sans le puits ; routeur_topk
  égalité au plus grand indice ; swiglu_oai α = 1 ; combiner ordre inversé ; ligne_q8_0 ligne
  voisine ; argmax égalité au plus grand indice.
- Pas de seuil de débit pour K3 (la spécification n'en donne pas ; le disque limite 400 fois plus,
  07 § 1.7) : les temps sont relevés à titre informatif, sans verrou.

### K3, chaîne de bout en bout (ajoutée le 2026-10-15 à 21 h 10, avant son code ; informative, ne remplace pas le verdict par noyau)
- Mode `chaine` de temoin-k3 : la passe avant **entière** de gpt-oss, enchaînée sur la carte par les
  seuls noyaux de K1 à K3 (aucun arrondi de l'hôte entre deux noyaux), sur les **160 premiers jetons
  réels** de la fenêtre 0 de wikitext-2 (jetons lus dans l'en-tête d'un `.kld` du lot R), contre
  `Reference::evaluer` (f64, même GGUF). Ordre couche par couche (chaque expert chargé une fois par
  couche) : numériquement identique au jeton par jeton (mêmes noyaux, mêmes entrées ; l'attention est
  causale et l'anneau de 128 ne contient, au moment de lire la position p, que p − 127 … p).
  160 > 128 : les couches à fenêtre lisent vraiment leur anneau.
- Seuil déclaré : **KL(référence ‖ chaîne) moyenne sur les 160 positions ≤ 7·10⁻⁵** (le plancher
  d'instrument du projet : Q-instrument § 7.3 et terme 7·10⁻⁵ de R1) ; publiés à côté : KL maximale,
  premier choix égal à la référence (part), écart relatif des logits.
- Cassures (chacune doit faire dépasser le seuil) : `fenetre` (fenêtre posée sur les couches impaires
  au lieu des paires : faute de câblage que les témoins par noyau ne voient pas) ; `poids` (poids du
  routeur appliqués aux experts dans l'ordre inverse).
- **21 h 20, résultat sur gpt-oss-20b : la chaîne telle que déclarée TOMBE** : KL moyenne 7,28·10⁻³
  (seuil 7·10⁻⁵), KL max 1,02 (position 87), médiane 2,5·10⁻⁶, premier choix égal 158 / 160 ; les
  5 plus grandes positions portent 99,3 % de la KL (`k3/k3-chaine-gptoss20b.*`). La forme est celle
  que le lot R a trouvée entre la référence et llama.cpp (une queue lourde portée par quelques
  positions : les bascules de routage, REPRISE-R). Le seuil était mal posé pour un MoE qui amplifie
  (même défaut que R1 et C4, signalé par le lot R) ; je ne le change pas, je diagnostique.

### K3, diagnostic de la chaîne (déclaré le 2026-10-15 à 21 h 22, avant son code)
- D1, compte : pour chaque (couche, position), les quatre experts choisis par la chaîne contre ceux de
  la référence (`journal_routage` de trc-reference) ; publiés : nombre de désaccords (ensemble, et
  ordre), première bascule de chaque position et la marge du routeur de la référence à cet endroit
  (écart 4e – 5e logit).
- D2, routage imposé (`--imposer`) : la chaîne prend les experts de la référence à chaque (couche,
  position) ; ses poids restent le softmax de **ses** logits du routeur sur ces quatre experts (la
  forme de l'expérience B du lot R ; calcul de l'hôte en f64 depuis les logits f32 de la carte, la
  seule intervention de l'hôte). **Prédiction et seuil, déclarés** : si la chaîne est juste et que
  l'écart ne vient que des bascules, la KL moyenne sous routage imposé tombe sous **7·10⁻⁵** (le
  seuil inchangé), et la KL max sous 10⁻³. Si D2 tombe, l'écart a une autre cause, à chercher.
- Cassures de D2 : `fenetre` et `poids` sous routage imposé doivent dépasser 7·10⁻⁵.

## État

- 12 h 47 : noyaux écrits (decoder_echelles, decoder_codes, copier_brut, gemv_mxfp4,
  gemv_mxfp4_lot), banc C++ écrit. 20b couche 0, 8 experts : exact ; cassures : LUT → 8 experts
  faux, 0 voie hors de L (la fin à L ne garde pas la table, 03 § 3.3) ; bit de flux → 30 voies
  hors de L, 2 experts faux.
- 12 h 48 : justesse complète du 120b lancée en arrière-plan (priorité inactive, 3 fils, sans
  verrou : test de justesse, ≈ 110 Mo de VRAM) → `mesures/moteur/K/k1-justesse-gptoss120b.json`.
- 12 h 52 : GEMV, justesse 20b couche 0 : tient (2,0·10⁻⁷) ; cassure tombe partout.
- Crate Rust : Cargo.toml, build.rs (fatbin sm_89 + PTX), `abi` (5 tests), `Noyaux` (enveloppes
  sur trc-cuda), `tests/carte.rs` (3 tests sur la carte, commit 2e24cc6).
- 13 h 07 – 13 h 09 (prédécesseur, essais hors verrou, journaux dans cibles/, non commités) :
  décodeur v1 ≈ 31 à 32 Go/s de codes, **sous le seuil de 33,3** ; latence ≈ 0,36 à 0,39 ms par
  expert. Optimisations v2 écrites (13 h 12 – 13 h 20) : fenêtre de mots à trois registres
  (lecture d'avance), médianes en mémoire partagée dans decoder_echelles, κ du macro-pas suivant
  lu d'avance dans decoder_codes, ligne et reste suivis sans division ; décomposition par
  événements ajoutée au banc (TRC_FILS_ECH pour essayer la taille de bloc).
- 13 h 32 – 14 h 01 : justesse v2 sur 120b couches 17-18 (256 experts) : 0 faux.
- 15 h 06 (reprise par un nouvel agent, prédécesseur mort, arbre sale lu et gardé) : v2 reconstruite ;
  `cargo test -p trc-noyaux` vert (5 + 3) ; banc reconstruit (ptxas : decoder_codes 57 registres,
  48 Kio partagés ; decoder_echelles 55 registres, 24 Kio ; gemv 71/79 registres).
- 15 h 10 : justesse v2 complète du 120b lancée (36 couches, 3 fils, priorité basse) →
  `mesures/moteur/K/k1-justesse-v2-gptoss120b.json`.
- 15 h 20 : **second codeur du témoin K1 : le vrai fichier du lot F.** Outil
  `mesures/moteur/K/temoin-trc/` (hors de l'espace du moteur, pour ne toucher ni Cargo.toml ni
  Cargo.lock du lot O) : chaque partie de `gpt-oss-20b.trc` (11 157 405 696 o, écrit 13 h 22)
  décodée sur la carte par `Noyaux::decoder_expert`, comparée à l'emplacement tiré de
  `trc_codec::reconstruire_avec` et, remise en disposition d'origine, à l'empreinte du
  répertoire. **768 experts sur 768 exacts**, 0 voie hors de L, 0 format, 0 pointeur
  (`k1-trc-gptoss20b.json`). Cassures (8 experts, couche 0) : `lut` → 8 faux (4 499 octets de
  codes), 0 hors L ; `flux` → 8 faux, 171 voies hors de L, 7 pointeurs faux.
- 15 h 22 – 15 h 35 (~~15 h 30 – 15 h 45~~, heures corrigées) : **décodeur en lot** (`decoder_echelles_lot`, `decoder_codes_lot`,
  `abi::DescDecodage` 32 o, `Noyaux::decoder_lot`) ; corps de carte partagés avec les noyaux seuls
  (`corps_echelles`, `corps_codes`). Test `decodeur_en_lot_egal_au_seul` (3 experts, LUT propres,
  un bit de flux retourné dans le 2e : lui seul sort de L ; lot = seul au bit) ; cassure du test
  (descripteur 0 pour tous) : tombe. Banc : variante C ; `temoin-trc` décode chaque paquet de 8
  aussi en lot : **768 / 768 exacts par les deux chemins** (journal réécrit, noyaux finaux) ;
  cassures LUT et flux : mêmes comptes par les deux chemins.
- 15 h 36 : justesse v2 complète du 120b : **4 608 experts, 0 faux** (chemin brut 0 faux), 0 hors L,
  0 format (`k1-justesse-v2-gptoss120b.json`, banc du 15 h 09, noyaux v2 avant la mise en corps
  partagés). 15 h 38 : même justesse relancée avec les noyaux finaux (banc_k_v3.exe, mêmes sources
  que banc_k.exe reconstruit à 15 h 37) → `k1-justesse-v3-gptoss120b.json`.
- 15 h 50 : justesse v3 **arrêtée par moi** à la couche 4 (couches 0 à 4 : 640 experts, 0 faux ;
  `k1-justesse-v3-gptoss120b-c0-4-partiel.*`, JSON incomplet, non fermé) : la note du rôle gpt-oss
  (15 h 06) nomme banc_k parmi les causes de pagination de son traceur 120b (RAM libre 0,4 Go).
  Reprendre couches 5-35 quand la machine est calme (`banc_k.exe justesse-decodeur … 5-35 …`).
- 15 h 55 : `vers_csv.py` (CSV des figures) ; il a trouvé que `k1-trc-*.json` n'étaient pas du
  JSON valide (champ `dims` écrit au format de débogage de Rust) : outil corrigé ; **les journaux
  k1-trc-* sont à régénérer** (même commande) quand la machine est calme ; leurs comptes, lus à la
  main, restent ceux écrits ci-dessus.
- 16 h 46 : carte libre (traceur fini), **première séance interrompue** : le pilote est tombé après
  la passe A1 (PowerShell 5.1 change la première ligne de stderr du banc en erreur fatale sous
  `Stop`) ; verrou retiré par le `finally`, puis pris par le lot E à 16 h 46 min 47 s. Journaux gardés
  sous `journaux/interrompu-20261015-1646/` (hors des CSV). Ce que la passe A1 donne (un processus,
  5 × A B C C B A, secteur) : **A 36,27 Go/s médiane, pire 34,46** (≥ 33,28) ; **C (lot de 4)
  53,35, pire 53,28** ; B 105,2 ; dispersion A 5,3 %, C 0,4 % ; latence d'un expert seul 0,357 ms ;
  décomposition : DELTA 152 µs, CODES_CTX 195 µs, trou 2 µs (le modèle du § 2.5 : DELTA presque aussi
  long que CODES, 24 warps sur la carte). Pas un verdict : la série A1 B1 B2 A2 n'est pas finie.
  Pilote corrigé (`Continue` le temps de l'appel) ; attente relancée (le verrou est au lot E).
- 17 h 01 : **seconde séance, concurrente, écartée du verdict** : notre verrou pris à 17:01:58, et un
  `llama-completion` gpt-oss-120b (`-ngl 99 --cpu-moe --fit off`, rôle gpt-oss, sa série de base)
  démarré à 17:02:02 a tourné pendant toutes nos passes (VRAM 439 → 2 878 Mio dès la fin de A1).
  **À dire à l'orchestrateur et au rôle gpt-oss : leur passe 2/13 « 120b-cmoe-2 » (série de base,
  `essais/…/gpt-oss/serie-120b.out`, 17:01:48 – 17:15:51, retenue) a été recouverte par nos bancs
  pendant ses ≈ 65 premières secondes (17:02:02 – 17:03:05 : chargement et début du préremplissage) ;
  son préremplissage (2,70 j/s) est sous celui des autres passes cmoe (2,84 à l'échauffement) : à
  écarter ou à vérifier de leur côté.**
  Ce que la séance donne (à titre de bruit, journaux sous `journaux/concurrent-20261015-1701/`) :
  A 36,22 et 36,17 Go/s médianes, **pires 33,15 et 33,33** (le seuil 33,28 tombe dans A1) ; C (lot
  de 4) 53,30 et 53,25, pires 51,27 et 50,41 ; référence de 03 refaite : v4 CUDA 82,0 Go/s,
  réassemblage 102,3 → **composé 45,5 Go/s** (03 publiait 41,6 en composant le v4 **sous Vulkan**,
  70 Go/s) ; K2 : lot de 12 matrices **234,3 et 234,2 Go/s** équivalents, pires 210,4 (seuil 167,5),
  une matrice par lancement 153,5 et 155,2.
  Attente corrigée : la carte doit être libre 5 minutes de suite (`-MinutesCalme 5`).
- 17 h 10 : `abi::grilles_depuis_partie` et `Noyaux::decoder_expert_grilles` (grilles sur les T réels
  de la partie) ; 6 + 4 tests verts. Attente relancée (calme de 5 min exigé) : la série de base 120b
  du rôle gpt-oss (lancée 16 h 47, 13 passes de ≈ 13 min, ≈ 3 h, sans verrou) occupe la carte ;
  `journaux/attente-20261015-b.log`. **Prochain pas : lire les journaux du pilote, verdicts K1 (A),
  C, D, K2 ; vers_csv.py ; régénérer k1-trc-* (JSON) ; reprendre la justesse v3 couches 5-35.**
- **20 h 24 – 20 h 26 : séance propre** (calme de 5 min, verrou du lot K, secteur BatteryStatus 2 à
  chaque passe, VRAM 330 Mio avant et après chaque passe : aucun autre programme sur la carte ;
  `journaux/*-20261015-2024.*`, `pilote-20261015-2024.json`). Ordre A1 B1 D1 D2 B2 A2, puis K2 ×2.
  - **K1, verdict déclaré (A, un expert à la fois, pire passe ≥ 33,28) : TOMBE de 0,9 %.** A1 :
    médiane 36,43 Go/s, pire 32,99 ; A2 : 36,29, pire 32,92. Les deux pires passes sont la
    **première série de chaque processus** (33,0 et 32,9 ; les neuf autres de 36,3 à 36,5, écart
    0,3 %) : effet de premier passage, cause non cherchée [hyp. : réveil de la carte ou du cache
    entre l'étalonnage et la série]. La règle était la pire passe : elle tombe, je ne la change pas.
  - **Référence refaite dans la même séance** : v4 CUDA 82,69 / 82,57 Go/s, réassemblage 102,63 /
    102,61, composé **45,79 / 45,75 Go/s** ; 0,8 × 45,8 = 36,6 : contre la référence CUDA de la
    séance, A tombe aussi en médiane. ~~41,6~~ : chiffre de 03 composé avec le v4 **sous Vulkan**
    (70 Go/s) ; sous CUDA, le chemin que K1 remplace fait 45,8.
  - **C (lot de 4) tient** : 53,41 / 53,23, pires 53,37 / 53,18 (≥ 33,28 et ≥ 36,6). Modèle § 2.5 :
    (151 + 4 × 194,6)/4 = 232 µs prédits, 233 mesurés.
  - **D (DELTA en tuiles de 32) tient** : 55,09 / 55,00, pires 52,49 / 51,92 ; prédiction déclarée
    57 ± 10 % : tient (55,0). Mais **la prédiction de T_DELTA était fausse** : 34,8 µs mesurés contre
    19 à 22 prédits (272 ns par sous-pas avec 192 warps de DELTA, 8 par SM, contre 148 ns à 1 par SM) ;
    le total ne tient dans ± 10 % que parce que T_CODES domine. D + lot (C à N = 32) : **58,8**.
  - **K2 tient** : lot de 12 matrices 235,35 / 235,41 Go/s de MXFP4 équivalents, pires 219,13 /
    220,89 (seuil 167,5 ; référence Vulkan de 03 : 209,4, dépassée de 12 %) ; une matrice par
    lancement 160,2 / 159,9 ; une couche (12 matrices) en 230 µs.
  - Témoins de la séance : 0 expert faux avant et après chaque série (A, B, C, D).
  - **Repli proposé à l'arbitre** (§ 6.5 K1 : « sinon repli décidé ici ») : **D**, N_DELTA = 32 au
    codeur du lot F (aucun octet du format ne change, +0,14 % par tronçon), et le décodage en lot
    pour les défauts d'une même couche ; les deux tiennent contre les deux références (41,6 publiée
    et 45,8 refaite). Le noyau ne change pas ; l'enveloppe a déjà `grilles_depuis_partie`. Le repli
    déclaré par la spécification (flux de classe, sorte 0x05) n'est pas nécessaire : il est plus lent
    (45,8 Go/s composés) que D (55,0).
  - Pas de conséquence sur J1 : 0,34 ms par expert contre 157 ms de disque par jeton (07).
- 20 h 35 : journaux `k1-trc-*` régénérés (JSON valide) : 768 / 768 exacts par les deux chemins,
  cassures LUT et flux : 8 faux chacune (fichier du lot F inchangé depuis 13 h 22). Justesse v3
  couches 5-35 lancée (20 h 27, priorité basse).
- 20 h 35 : justesse v3 couches 5-35 : 3 968 experts, 0 faux, 0 hors L, 0 format ; avec les couches
  0-4 : **les 4 608 experts du 120b exacts avec les noyaux finaux** (corps partagés, lot).
- ~~Carte occupée par d'autres (llama-perplexity, traceur gpt-oss 120b, 7,5 Go de VRAM) : bancs de
  débit K1 et K2 en attente du créneau (verrou + aucun llama-*).~~ Faits à 20 h 24 (ci-dessus).

### Reprise de 20 h 39 (nouvel agent, arbre propre)
- 20 h 40 – 20 h 52 : **témoin K1 contre le codeur du lot F sur `gpt-oss-120b.trc`** (F3 fini) :
  **4 608 experts sur 4 608 exacts** contre trc-codec et contre l'empreinte du répertoire, par les
  deux chemins (un expert, lot), 0 voie hors de L, 0 format, 0 pointeur ; 769 s, priorité basse
  (`k1-trc-gptoss120b.json/.log`). Cassures (couche 0, 8 experts) : `lut` → 8 faux (5 587 octets
  de codes), 0 hors L ; `flux` → 8 faux, 163 voies hors de L, 8 pointeurs. Ce point du « reste » est
  clos.
- 20 h 45 : critères de K3 déclarés (ci-dessus), commit avant tout code.
- 20 h 50 : **les onze noyaux de K3 écrits** (`noyaux/passe.cuh`), enveloppes (`Noyaux::gemv_q8_0`,
  `gemv_f32`, `rmsnorm`, `rope_yarn`, `ecrire_kv`, `attention`, `routeur_topk`, `swiglu_oai`,
  `combiner`, `ligne_q8_0`, `argmax`), `abi::ParamsRope` (48 o) et `abi::ParamsAttention` (32 o) ;
  ptxas : aucun débordement (attention 97 registres, 2 304 o partagés + 4 o par position ;
  routeur_topk 144 o de pile, tableaux indexés). Anciens tests verts (7 + 4).
- 21 h 00 : **K3 TIENT sur gpt-oss-20b** : les douze témoins tiennent, 143 cas, chaque appel
  déterministe au bit (`k3/k3-gptoss20b.*`). Pires écarts contre la référence f64 : gemv_mxfp4
  2,4·10⁻⁷, gemv_q8_0 1,9·10⁻⁷, gemv_f32 2,6·10⁻⁷ (seuils 10⁻⁵) ; rmsnorm 5,2·10⁻⁸, rope_yarn
  5,3·10⁻⁸, swiglu 4,9·10⁻⁸, poids du routeur 4,7·10⁻⁸ (seuils 10⁻⁶) ; attention 6,2·10⁻⁶ (seuil
  10⁻⁵, la plus petite marge : 1,6 fois) ; combiner, ecrire_kv, ligne_q8_0, argmax, indices du
  routeur, produits sur entiers : 0 différence. **Les douze cassures** (`k3/k3-casse-*`) : chacune
  fait tomber son seul témoin, les onze autres tiennent.
- 21 h 05 : **K3 TIENT sur gpt-oss-120b** (routeur à 128 experts) : 116 cas, les douze tiennent ;
  attention 3,9·10⁻⁶, gemv 1,6 à 2,5·10⁻⁷ (`k3/k3-gptoss120b.*`).
- **Trouvé en chemin** : la cassure « biais omis » ne fait pas tomber les cas `attn_k` : **le biais
  des clés vaut exactement 0** dans les deux GGUF (512 / 512 nuls, couches 0, 1, 5 ;
  `k3_biais_attention.py`, `k3/k3-biais-attention-*.log`), alors que les biais de q et v sont
  pleins (|b| jusqu'à 3,9). Sans puits, un biais de clé ajoute q·b_k à tous les scores d'une tête et
  le softmax l'efface ; avec le puits il ne s'effacerait pas : sa nullité n'est pas une évidence,
  c'est une donnée du modèle. Le témoin reste sain (les cas q, v et sortie tombent).
- 21 h 10 – 21 h 35 : chaîne de bout en bout (déclarée 21 h 10) : **telle que déclarée, TOMBE**
  (KL moyenne 7,28·10⁻³) ; diagnostic déclaré à 21 h 22 : **D1** les six premières bascules de
  routage (positions 67, 87, 114, 129, 136, 153 ; marges de la référence 3,3·10⁻⁴ à 1,1·10⁻²) sont
  exactement les six positions qui portent la KL ; **D2 (routage imposé) TIENT** : KL moyenne
  3,0·10⁻⁶, max 1,4·10⁻⁴, premier choix 160 / 160, médiane 1,8·10⁻⁷ ; sous imposition, le routeur
  de la carte n'aurait basculé que 3 décisions sur 3 840 (marges 1,4·10⁻⁴ à 7,9·10⁻⁴). Cassures
  sous D2 : `fenetre` KL 1,6·10⁻² (nulle avant la position 128 au bit près, 8,2·10⁻² après : l'anneau
  est bien lu), `poids` 0,52 : tombent. La sortie libre est identique au bit d'un processus à
  l'autre (même CSV à 21 h 20 et 21 h 30).
  **Ce que cela dit pour O et pour C4** : la chaîne des noyaux est juste (D2) ; l'écart de bout en
  bout à la référence f64 est fait de bascules de routage aux marges < 10⁻³ (f32 contre f64), comme
  le lot R l'a trouvé pour llama.cpp. C4 (« KL(troncons ‖ réf.) ≤ KL(llama.cpp ‖ réf.) ») se jouera
  sur le nombre de bascules, pas sur la précision des noyaux.

## Ce que la spécification ne dit pas (à porter à l'arbitre ; choix prudents pris)

1. **Contexte des positions de bourrage** (§ 4.9.1, § 4.9.3) : si R·B·16 n'est pas multiple de 128,
   le flux CODES_CTX code des octets de bourrage dont le bloc ⌊w/4⌋ n'existe pas : quel κ ? Choix
   du noyau et du banc : contexte 0 ; rien n'est écrit au-delà des blocs réels. Sans objet pour
   gpt-oss (2 880 × 90 blocs). **Le lot F a pris le même choix, indépendamment** (REPRISE-F,
   précision 6 : κ = 0, celui du δ de bourrage). Proposition : l'écrire au § 4.9.3.
2. **« octets produits » de la table des flux** (§ 4.8) quand le flux est bourré : P (bourrage
   compris, comme l'en-tête du flux) ou les octets utiles ? Le noyau accepte les deux. ~~Proposition :
   les octets utiles~~ Le lot F écrit P (REPRISE-F, précision 5) ; proposition alignée sur le fichier
   réel : **P**, et le noyau garde l'acceptation des deux (réponse par délégation du 2026-10-15,
   réversible ; raison : un seul fichier existe et il écrit P).
3. Extensions de la couture N (sans rien changer d'existant) : le décodeur est **deux noyaux**
   (`decoder_echelles`, `decoder_codes`) derrière une seule enveloppe `Noyaux::decoder_expert` ;
   le tampon de contrôle u32[4] ; la disposition des LUT d'une couche u32[3][4][4096] ;
   `gemv_mxfp4_lot` (descripteurs de 32 o) ; **`decoder_echelles_lot`, `decoder_codes_lot`,
   `DescDecodage` (32 o : partie, emplacement, LUT, contrôle), `Noyaux::decoder_lot`**. Signatures
   dans `src/lib.rs` et `src/abi.rs`.
4. **Le seuil de K1 compare deux grandeurs différentes** (§ 6.5) : 41,6 Go/s est le débit de 03 sur
   un grand flux (des milliers de tuiles en vol), le débit de K1 est celui du moteur, un expert à la
   fois (381 tuiles, une vague, plus 24 tuiles de DELTA seules sur la carte : modèle du
   K-pour-le-memoire.md § 2.5). Choix prudent pris : juger A (un expert à la fois), comme déclaré à
   12 h 40 ; C (lot de k = 4) publié à côté. Proposition à l'arbitre : dire lequel des deux fait loi
   pour le moteur (A si les défauts arrivent un à un, ce qui est le cas tant que le disque limite ;
   C pour le préchargement de J1+), et rappeler que l'un comme l'autre est ~400 fois sous le temps
   disque d'un jeton (0,4 ms contre 157 ms) : l'élasticité du plafond au décodeur est nulle (07 § 1.7).
5. **K3 : le résidu de l'attention n'est pas un noyau du § 5.6.** Il passe par `combiner` avec
   n = 1 et des poids nuls, ce qui veut dire des poids de 1, sans aucune multiplication. C'est une
   extension de la couture N : `combiner` prend n, un pas entre les sorties, et des poids
   facultatifs. Rien d'existant ne change. Proposition : l'écrire au § 5.6.
6. **K3 : la boîte aux lettres du routeur n'a pas de disposition au § 5.6.** Choix pris : celle de
   l'essai E0 c du lot E (banc-chemin/noyaux/essais.cu). Une case de 64 o par couche : mot 0 = la
   séquence, écrite en dernier après une barrière système ; mots 1 à 4, les indices ; mots 5 à 8,
   les poids. Le noyau prend la séquence en argument. Raison : c'est le seul protocole mesuré
   (réponse par délégation du 2026-10-15, réversible). Proposition : l'écrire au § 5.6, pour O.
7. **K3 : les seuils de bout en bout sont mal posés pour un MoE** (même défaut que R1 et C4, porté
   par le lot R). Une chaîne de noyaux justes (D2 : 3,0·10⁻⁶) tombe à 7,3·10⁻³ en routage libre, par
   6 bascules aux marges sous 10⁻³. Proposition à l'arbitre : juger toute comparaison de bout en
   bout sous routage imposé (la forme de D2), et compter les bascules à part, avec la marge de chacune.
8. **K3 : la précision des noyaux « vecteur » n'est pas imposée.** rmsnorm, rope_yarn, swiglu et
   les poids du routeur sont faits en f64 sur la carte. Ce n'est pas une option pour rope_yarn :
   en f32, l'angle porterait une erreur de 2⁻²⁴ p, et le seuil de 10⁻⁶ du § 5.6 tomberait dès la
   position ≈ 17 (K-pour-le-memoire § 7.3.1). Proposition : l'écrire au § 5.6.
9. **K3 : l'attention lit au plus 8 192 positions par appel** (mémoire partagée de 4 o par
   position). C'est assez pour le contexte de J1 (4 096). Pour un long contexte (J3), il faudra une
   version en tuiles.

## Ce qui reste au lot K (à 21 h 50)

- **Pour l'arbitre** : le repli de K1 (D et/ou lot) et la grandeur de son seuil ; les points 1 à 9
  ci-dessus. Si D est adopté, le lot F recode, puis on relance temoin-trc sur le nouveau fichier
  (même commande).
- **L'effet de première série de K1** : la pire passe A est 9 % sous les autres, dans chaque
  processus. Cause non cherchée. Il faut la carte et le verrou ; le verrou est au lot F depuis
  20 h 52, et le pilote E2 du lot E attend derrière.
- **La chaîne de K3 sur gpt-oss-120b** : `temoin-k3.exe chaine <120b.gguf> <processeur-bis.kld>
  k3/k3-chaine-d1-gptoss120b.json k3/k3-chaine-d1-gptoss120b.csv`, puis la même avec `--imposer`
  (d2). Il faut de l'ordre de 120 Go de lectures [calc.] : à lancer quand le disque est libre (ni le
  lot F, ni E1 au calme).
- **K4** (mode base, J2).
- **Pour le lot O (O2)** : les enveloppes sont prêtes (`Noyaux::*`, `abi::ParamsRope::GPT_OSS`,
  `abi::ParamsAttention::gpt_oss(position, fenetre)`, `ParamsAttention::case`). L'ordre exact des
  appels d'une couche est celui de `mesures/moteur/K/temoin-k3/src/chaine.rs`, qui tient sous D2.
  Il est copiable tel quel dans trc-modele.
- **Pour le rédacteur** : K-pour-le-memoire.md § 7 ; csv/k3-*.csv ; memoire/sources/moteur-K.bib
  (entrées K3).
