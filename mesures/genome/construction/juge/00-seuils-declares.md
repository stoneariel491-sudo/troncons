# Les seuils du juge de la construction, déclarés avant toute mesure

Rôle : juge indépendant des lots A (codon synonyme du zéro, `.trc` v1.2, genome/06-codon-v1-2.md) et B
(génome synonyme, mode rapide, genome/07-genome-synonyme.md). Je n'ai rien construit. Écrit le
2026-10-22 vers 4 h, **avant toute mesure** : à cette heure, aucun outil du juge n'a lu un octet d'un
fichier `.trc`, d'un GGUF ou d'un `.kld`. Graine de tous les tirages : **20261022**.

Ce qui suit est une liste de mesures, chacune avec sa prédiction, son témoin (un cas dont la réponse
est connue d'avance), sa cassure (le témoin forcé à faux doit tomber) et son seuil. Un seuil repris d'un
lot est dit tel ; un seuil neuf dit de quelle grandeur mesurée il dérive.

---

## J-T : le `.trc` v1.2, taille et exactitude, par mon propre décodeur

**L'instrument.** `outils/genome/construction/juge/decodeur_juge.py` (Python et numpy), écrit **depuis
la seule description du format** (decisions/ARCHITECTURE.md §§ 4.2 à 4.12 et 4.16) ; je n'ai lu ni
`trc-format`, ni `trc-codec`, ni le décodeur Python de l'épreuve J1 (`mesures/moteur/epreuve-J1/`), ni
les outils du lot A avant de l'écrire. Il lit aussi le GGUF par son propre lecteur (GGUF v3 : en-tête,
paires, infos des tenseurs, alignement), sans passer par aucun code du dépôt. Le décodage rANS suit
§ 4.9.2 mot pour mot, vectorisé sur les 32 voies et sur toutes les tuiles d'un flux à la fois (le pas
d'une voie ne dépend que de son état ; les mots du flux partagé s'attribuent aux voies qui
renouvellent, dans l'ordre l = 0 … 31, par une somme préfixe).

**J-T0, fichiers entiers (lecture de l'en-tête, des tables et du répertoire seulement)**, sur les quatre
fichiers `gpt-oss-{20b,120b}{,-v12}.trc` :
- en-tête : magie, version, drapeaux (v1.2 : bit 3 posé, version mineure 2 ; v1.0 : drapeaux = 1),
  taille déclarée = taille sur le disque, empreinte64 de [0, 4 088) ; empreintes de fin de MÉTA, de la
  table des RÉSIDENTS, de TABLES et du RÉPERTOIRE ; répertoire : décalages multiples de 4 096, croissants,
  sans recouvrement, dans la section TRONÇONS ; `empreinte_canonique` non nulle partout en v1.2, nulle
  partout en v1.0. **Seuil : 0 faute.**
- tailles : taille du fichier, somme des parties alignées (longueur0) et des octets utiles ; bits par
  poids d'expert = 8 × somme / poids d'experts. **Seuil** : les tailles de fichiers et d'octets de
  tronçons du tableau de 06 § 6 redonnées **à l'octet** ; gain v1.0 − v1.2 ≥ 0,12 bit par poids sur
  chaque modèle (le seuil A-C2 du lot A, repris tel quel).
- tables : en v1.2, **0** table CODES_CTX qui donne une fente à l'un des 31 octets portant un
  demi-octet 8 ; en v1.0, le nombre de celles qui en donnent (témoin : le lot A en a compté 540 sur 540).

**J-T1, l'échantillon décodé.** Tirage sans remise, `numpy.random.Generator(PCG64(20261022))` :
d'abord `choice(768, 32, replace=False)` pour le 20b, puis, du même générateur, `choice(4608, 64,
replace=False)` pour le 120b ; indice i → (couche ⌊i/E⌋, expert i mod E). Le tirage est écrit dans
`mesures/genome/construction/juge/tirage-experts.json` avant tout décodage.
Pour chaque expert tiré, dans le v1.2 : (a) les 12 flux décodés, **chaque voie de chaque tuile finit sur
L** ; (b) les blocs reconstruits `[e, qs]` égaux **octet pour octet** aux blocs du GGUF canonisés par mon
propre code (demi-octet 8 → 0) ; (c) les biais égaux au bit ; (d) chaque poids égal **en valeur** au poids
du GGUF non canonisé (table E2M1 de 16 entrées, −0 = +0) ; (e) empreinte64 de l'expert canonique
reconstruit = `empreinte_canonique` du répertoire ; (f) empreinte64 des blocs du GGUF tels quels =
`empreinte_origine` ; (g) empreinte64 des octets utiles de la partie = celle du répertoire ; (h) aucun
demi-octet 8 dans le décodé. **Seuil : 0 faute sur les 96 experts et les huit contrôles.**

**Témoin (réponse connue)** : les 32 experts du 20b et les 8 premiers tirés du 120b, décodés **dans le
v1.0** : décodé = GGUF **tel quel** octet pour octet, empreinte = `empreinte_origine` ; et, pour chaque
expert, le nombre de demi-octets 8 du GGUF = le nombre de demi-octets qui diffèrent entre le décodé v1.0
et le décodé v1.2 (le seul changement de la v1.2).

**Cassures** (chacune doit faire tomber l'instrument) : (1) un mot de 16 bits d'un flux CODES_CTX changé
en mémoire avant décodage → voies hors de L ou octets différents ; (2) la canonisation retirée de mon
lecteur du GGUF → (b) et (e) tombent sur tout expert du v1.2 qui porte un −0 ; (3) un bit d'un biais
changé en mémoire → (c) et (g) tombent.

**Ce que je publie de plus** : la part des −0 dans l'échantillon, contre 6,393 % (20b) et 6,279 % (120b)
publiés par le lot A (sans seuil : un échantillon de 32 ou 64 experts n'a pas à redonner une moyenne de
fichier ; je publie l'écart en écarts-types de l'échantillon).

---

## Les fenêtres neuves

Les lots ont évalué sur R1 (les 10 premières fenêtres de 512 jetons de wiki.test, jetons 0 à 5 119) et
calibré le génome synonyme sur les fenêtres 10 à 21 (jetons 5 120 à 11 263). **Mes fenêtres n'en
recoupent aucune.** Outil `outils/genome/construction/juge/fenetres_juge.py` :
- on écarte les **120 000 premiers octets** de `wiki.test.raw` (1 290 590 octets) ; témoin : ce préfixe
  se découpe (llama-tokenize b11515) en au moins 11 776 jetons (= 23 × 512), donc il couvre R1, la
  calibration et une fenêtre de marge ; s'il en compte moins, le préfixe écarté est agrandi jusqu'à les
  couvrir, et c'est dit ;
- dix débuts de ligne tirés (`Generator(PCG64(20261022))`, après les deux tirages d'experts : graine
  20261022 + 1 pour ce générateur) dans [120 000, 1 290 590 − 12 000), chacun à plus de 12 000 octets des
  autres ; chaque extrait : 9 000 octets depuis son début, prolongés jusqu'à la fin de ligne ;
- chaque extrait passe par `llama-perplexity` (b11515, processeur seul, `-c 512 -b 512 -t 6 --seed 1
  --chunks 1 --kl-divergence-base`, les options de R0) : une fenêtre de 512 jetons par extrait ;
- les dix fichiers sont fondus en un seul `base-juge-20b.kld` (n_chunk = 10) par mon outil ; témoin :
  jetons et entrées de chaque fenêtre égaux octet pour octet à ceux de son fichier source ; le fichier
  fondu s'ouvre par `juge` (lecteur du lot R) et sa taille vaut 20 + 4 · 5 120 + 2 550 · 402 184 octets.

La référence f64 de ces fenêtres : `juge reference --yarn openai --fenetres 10 --kl-contre-base
--routage` (l'appel de R1, `mesures/moteur/R/r1_reference.py`) → `ref-juge-20b.kld`, construit depuis
`main` dans ma cible.

---

## J-C1 : les logits au bit, sur les fenêtres neuves

`troncons evaluer --flux --empreintes` (moteur construit depuis `main` dans ma cible), 10 fenêtres de
`base-juge-20b.kld`, sur 20b v1.0 et v1.2, puis 120b v1.0 et v1.2 (même découpage o200k pour les deux
modèles). Comparaison par mon script (`logits_juge.py`), pas par celui du lot A.
- **Seuil** (proposition A1, critère A-C1 du lot A, repris) : **0 empreinte de logits différente sur
  5 120 pas** par modèle ; les `.kld` de sortie égaux octet pour octet (SHA-256).
- **Témoin** : le moteur est déterministe : le 20b v1.2 évalué deux fois rend deux CSV identiques.
- **Cassure** : une copie du 20b v1.2 où le bit de signe du biais f32 de la rangée 0 de la matrice 0
  (gate) est retourné pour les 32 experts de la couche 0 (flux BIAIS, bruts : rien d'autre ne change),
  évaluée `--sans-garde` sur la première fenêtre : au moins une empreinte doit différer (attendu : la
  plupart dès la position 0, chaque position routant 4 experts de la couche 0). La copie est effacée
  après.

---

## J-V : les jetons par seconde de J1 en v1.2, et ce qui fait la vitesse

**Une séance, trois fichiers du 120b**, ordre équilibré contre une dérive linéaire,
**A B R R B A A B R R B A** (rang moyen 6,5 pour chacun) : A = `gpt-oss-120b.trc` (v1.0 d'origine),
B = `gpt-oss-120b-v12.trc`, R = `gpt-oss-120b-frontiere.rapide.trc` (`--rapide`, compagnon frontière du
lot B). Réglages du J1 (06 § 8) pour les trois : `troncons mesurer --flux --emplacements 326`, invite
wiki-3000 (SHA-256 vérifiée), 256 jetons gloutons, `--repos 10`. Puis **une séance du 20b**, même ordre :
A = `gpt-oss-20b.trc`, B = `gpt-oss-20b-v12.trc`, R = `gpt-oss-20b-synonyme-l0.rapide.trc` (`--rapide`),
avec les réglages de la séance s2 du lot B (`mesurer`, sans `--flux`, emplacements par défaut,
256 jetons, `--repos 10`). Avant chaque séance et avant et après chaque passe : secteur
(Win32_Battery = 2) et relevé des autres flux (plus de 5 % d'un cœur ou plus de 8 Mo lus en 3 s ⇒
« SOUS CHARGE » : la passe ne conclut pas) ; départ sur deux relevés vides à une minute d'écart. Mon
propre pilote (`seance_juge.py`).

Bruit : σ_X = écart-type (n − 1) relatif des 4 passes du fichier X ; σ = max(σ_A, σ_B, σ_R) de la séance.
Rapport r(X/Y) = médiane de X / médiane de Y (jetons par seconde de génération).

- **J-V1 (A-C3 du lot A, repris)** : r(B/A) du 120b : pas de régression si r ≥ 1 − 2σ ; gain annoncé si
  r − 1 > 2σ. Jetons : les 256 identifiants égaux dans les 8 passes A et B, empreinte du texte
  e4c6dbac… (celle des J1 du 15 au 22 octobre). Octets de tronçons par jeton : rapport B/A = 0,9671 à
  4 chiffres (déterministe). **Ma prédiction : r ≈ 1,45 (le résultat du lot A se reproduit), et ce n'est
  pas le format** (le toit du format est +3,4 %).
- **J-V2, le ×2,00 du lot B (120b-V, 07 § 4.4)** compare le compagnon (écrit le 17 octobre) au v1.0
  d'origine (écrit le 15, que l'étage disque lit 1,33 fois moins vite que le v1.2 : 06 § 8, 08 § 3).
  Comparé au v1.2 (écrit le 17 aussi), le mode rapide ne garde que ce que valent ses octets.
  **Prédiction : r(R/B) ≈ 2,00 / 1,45 ≈ 1,38** ; toit des octets par pas 0,707 × 0,9671 / 0,464 = 1,47.
  **Règle** : le ×2,00 est un gain **du mode rapide** si r(R/B) ≥ 2,00 · (1 − 2σ) ; sinon il est
  **confondu par l'état du fichier exact**, barré comme gain du mode et gardé comme gain de fichiers.
- **J-V3, le ×1,24 du lot B sur le 20b** (s2, compagnon λ = 0 écrit le 22 à 0 h 51, mesuré 20 min plus
  tard, contre le v1.0 du 15) : même règle, r(R/B) du 20b contre 1,241 · (1 − 2σ). **Prédiction : r(R/B)
  ≈ 1,0** (les octets par pas de génération du lot B sont égaux à 1 % près ; le gain venait du débit par
  octet). Le lot B l'attribue au cache de fichiers du système [hyp.] ; or le moteur lit sans tampon
  (`FILE_FLAG_NO_BUFFERING`, ARCHITECTURE § 4.1, et 08 § 3.1 : le disque lit 1,0000 à 1,0057 fois les
  octets demandés) : je tiens cette hypothèse pour fausse par construction, et la séance le juge.
- **J-V4, l'étage disque seul** (`troncons disque --n 1500 --graine 20261017 --repos 5`, l'instrument du
  lot A), dans la séance du 120b avant les passes du moteur, ordre A B R R B A ; et dans celle du 20b, ordre
  A B R R B A. Règle de séparation de 08 § 2.1, reprise : deux fichiers diffèrent si leurs médianes
  diffèrent de plus de S = max(2 · max e_soi, 11,8 %).

---

## J-K : la KL du génome synonyme sur les fenêtres neuves

Vérité P : `ref-juge-20b.kld` (référence f64). Candidats Q, **par le moteur** (mon chemin ; les lots ont
décidé B2 par la référence f64 substituée) : `troncons evaluer --flux --rapide` sur les compagnons
λ = 0 (`gpt-oss-20b-synonyme-l0.rapide.trc`) et λ = 1 (`gpt-oss-20b-synonyme.rapide.trc`), et le mode
exact (`gpt-oss-20b-v12.trc`) ; **par la référence f64 substituée** (`genome-capture kl --sub`, le chemin
des lots, si le temps le permet, dans cet ordre) : λ = 0, frontière, λ = 1.

**Ma KL** : `kl_juge.py`, écrit par moi, numpy : par position notée, KL = Σ_{i : log p_i > −16} p_i (log
p_i − log q_i), P et Q décodés de leur codage 16 bits (log p = pas · code + log p_min), sans
renormalisation (la convention du lot R, R-pour-le-memoire § 2.4 : un fichier contre lui-même rend 0).
Témoin : ma KL moyenne = celle de `juge kl` sur la même paire à 10⁻⁶ relatif ; cassure : Q décalé d'une
position → l'écart dépasse 10 × la KL. Incertitudes : σ par fenêtres (la moyenne des 10 KL de fenêtre
et l'écart-type de cette moyenne, 9 degrés de liberté), comme les lots.

- **J-K1 : λ = 0 contre la frontière** (par la f64 substituée ; à défaut, par le moteur, la frontière
  servie par le compagnon frontière écrit par `trc-rapide` depuis `sym/frontiere`) : meilleure si
  d̄ + 2σ < 0. Prédiction : tient (5,6 σ sur R1).
- **J-K2 : B2 entre les deux λ, refait** (la règle du lot B, `00-seuils-declares.md` du lot B, reprise
  telle quelle) : d = KL_{λ=0} − KL_{λ=1} ; λ = 0 meilleure si d̄ + 2σ < 0 ; λ = 1 meilleure si d̄ − 2σ > 0 ;
  égales sinon, et la règle du lot B garde alors λ = 1 (moins de bits). **Prédiction : égales** (2,09 σ
  sur R1, une fenêtre sur dix contre ; avec dix fenêtres neuves, la probabilité de redonner plus de 2 σ
  est de l'ordre d'une sur deux). Je publie aussi la mise en commun des 20 fenêtres (R1 + neuves), par le
  même estimateur, comme une information, sans en faire un verdict de plus.
- **J-K3 : le moteur rapide contre la f64 substituée** (S3-K du lot B, seuils repris : KL ≤ 0,011 et
  premier choix identique ≥ 95 %), pour chaque λ mesuré par les deux chemins.
- **J-K4 : le mode exact** (moteur v1.2 contre la référence f64, sur les fenêtres neuves) : publié contre
  0,00368 (O, C4) ; seuil de C4 repris tel quel (lot O).
- **Ce que je publie de plus** : quantiles (médiane, 99e, 99,9e centile), premier choix, perplexité, et
  les experts routés par mes fenêtres que R1 n'a jamais routés (journal `--routage` de la référence contre
  celui de R1) : ils sont jugés ici pour la première fois.

---

## Ce qui serait faux ou trop beau : ce que je lis en plus des mesures

Lecture de 06 et 07 phrase à phrase contre leurs journaux : chaque chiffre de leurs § 0 retrouvé dans un
fichier commité (ou dit introuvable) ; chaque attribution de cause marquée [mes.] vérifiée contre ce que
la mesure peut dire.
