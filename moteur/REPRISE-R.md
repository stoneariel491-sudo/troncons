# Reprise du lot R (référence, juge, banc Q0)

Spécification : decisions/ARCHITECTURE.md § 5.9, § 6.1, § 6.5 (R0, R1), § 7.1 (C4). Mes fichiers :
moteur/crates/trc-{reference,jetons,juge}/**, outils/q0/**, mesures/moteur/R/**, cette note,
moteur/R-pour-le-memoire.md, memoire/sources/moteur-R.bib.

## Construction
- L'espace moteur/ (lot O) refuse de se charger tant qu'un dossier de crates/ n'a pas son Cargo.toml
  (trc-noyaux du lot K, 2026-10-15 ~12 h 45). Contournement sans toucher aux fichiers des autres :
  espace jetable hors dépôt qui dépend de trc-juge par chemin (scratchpad/construire-R), même cible
  ~/dev/cibles/troncons-R, --offline -j 4. Ne touche pas moteur/Cargo.lock.

## 2026-10-15
- Lu : SOCLE, ARCHITECTURE en entier ; llama.cpp b11515 (perplexity.cpp format .kld, openai-moe.cpp,
  rope YaRN de ggml, swiglu_oai, gating SOFTMAX_WEIGHT) ; OpenAI gpt_oss/torch/model.py et config.json
  (copies sous ~/dev/lectures/troncons/lot-R, Apache-2.0).
- TROUVAILLE : config.json de gpt-oss dit rope_scaling.truncate = false (rampe YaRN aux bornes
  réelles 8,0928 et 17,3981) ; llama.cpp b11515 arrondit (floor/ceil : 8 et 18). La référence suit
  OpenAI (le modèle) et garde la variante llama.cpp pour chiffrer l'écart. Le § 5.6 (noyau rope_yarn)
  ne dit pas laquelle : à porter à l'arbitre.
- Crates écrites : trc-reference (GGUF, poids f64 exacts, ops, passe par lots de fenêtres et pas à
  pas), trc-jetons (llama.dll vocab_only), trc-juge (format .kld, KL, Wilson, règle ABBA). 14 tests
  unitaires tiennent. Un seuil de test posé au jugé (1e-7) est tombé (5,7e-6, biais d'arrondi du
  codage 16 bits) : remplacé par la borne dérivée (le pas de codage).
- Carte occupée par le traceur 120b de l'agent gpt-oss (7,5 Go de VRAM) : R0 attend la carte.
- R2 compteurs (trc-juge::compteurs : PDH par nom anglais, GetProcessMemoryInfo, nvidia-smi -lms 250) :
  témoin mémoire TIENT (hausse 1,000 × 512 Mio ; cassure sans écriture : 2e-5, tombe comme prévu) ;
  témoin disque TOMBE (0,80 vu au lieu de ≥ 0,95) : repos de la machine 0,39 Go/s pendant le traceur
  120b de l'agent gpt-oss ; la cassure (fenêtre décalée) donne −0,01 (attendu < 0,10). À refaire carte
  et disque au calme (mesures/moteur/R/r2/compteurs-*.json).
- R0 étape processeur lancée 12 h 50 (84 s par fenêtre, deux passes de 10 fenêtres).
- R0 processeur passe 1 : PPL 455,10 ± 28,36 (10 fenêtres), 1 199 s ; passe bis en cours.
- W1 TIENT (r1/W1-chemins-20b.log) : pas = evaluer au bit, 4 826 112 logits, 0 différent ; cassure
  (pas avec la rampe llama.cpp) TOMBE : 4 625 024 différents, écart max 0,124 dès 24 jetons.
- W2 TIENT : trc-jetons = jetons de llama-perplexity (5 120), ajoute_bos = false ; cassure (« X » en
  tête du texte) TOMBE au jeton 0. Piège : LoadLibrary ne cherche pas ggml*.dll à côté de llama.dll
  → load_with_flags(LOAD_WITH_ALTERED_SEARCH_PATH).

## 2026-10-15, reprise (second agent du lot R, ~15 h)
- Premier agent mort vers 13 h 31 : passe R0 processeur-bis tronquée à la fenêtre 7 (717 918 208 o) ;
  journal gardé (r0/processeur-base-processeur-bis-mort-a-la-fenetre-7.log), .kld effacé, passe
  relancée 15 h 08 (étape `processeur-bis` ajoutée à r0_ecart.py ; priorité sous la normale pour les
  passes suivantes, celle-ci partie en normale comme la passe 1).
- L'espace moteur/ se charge de nouveau (trc-noyaux a son Cargo.toml) : construction dans l'espace,
  `cargo … -p trc-juge --offline --locked -j 4`, cible troncons-R ; Cargo.lock inchangé.
- TROUVAILLE (coût) : `Matrice::produit` relisait les n vecteurs d'entrée pour chaque rangée ; à
  5 110 positions (R1, 10 fenêtres) x = 118 Mo hors du L3 : la seule matrice de sortie (201 088
  rangées) aurait tiré ≈ 23,7 To de la mémoire vive (≈ 4·10⁵ s à 60 Go/s). Pavé : positions par 256
  (L3), rangées par 32 déquantifiées une fois (L2), tuiles de 8, noyau 2 × 2 (huit chaînes de FMA).
  Chaque sortie = `scalaire` au bit par construction (même suite d'opérations par produit).
  Témoin `produit_egal_scalaire_au_bit` TIENT ; cassure 1 (lo/hi échangés) TIENT aussi : la
  réduction est symétrique dans cet échange, cassure mal choisie ; cassure 2 (a1·b1 sur une seule
  chaîne) TOMBE (304 sorties sur 1 349). W1 rejoué après le pavage : W1-chemins-20b-pavage.log.
  Lot de 24 jetons : ≈ 1 s par couche au lieu de ≈ 5 s.
- `juge reference` lit la base fenêtre par fenêtre (51 Mo au lieu de 513 Mo).
- R2 : `juge comparer` (jugement C4 : A et B contre la même vérité V, mêmes positions, différences
  appariées, verdicts littéral et statistique).

- TROUVAILLE (instrument) : un `.kld` jugé contre lui-même donnait KL = 1,11e-3 (pas 0) : `position`
  renormalisait les log-probabilités décodées, et les ~2e5 jetons écrasés sur log_p_min ajoutent
  log Σ p̂. 16 × le seuil de 7e-5 : chemin 2 de R0/R1 et C4 aveugles. Corrigé : `position_decodee`
  (sans renormalisation) ; témoin d'identité = 0 exactement ; test et cassure.
- W1 rejoué après pavage : tient (0 sur 4 826 112) ; cassure identique au bit près à celle d'avant
  (4 625 024, 0,12399). Rampe YaRN : `juge rampe` + `rampe_yarn.py` (témoin 0,94 ulp ; cassure :
  paires 9-17) ; phrase « 8 ≤ i ≤ 17 » barrée → 9 ≤ i ≤ 17.
- R1 lancé en chaîne après R0 bis (reference, cassure sans échelle, rampe llama.cpp ; 4 fils).

- R0 processeur bis : .kld identique octet pour octet à la passe 1 (moteur processeur déterministe).
- R1 sur 20b (10 fenêtres, ≈ 16 min par passe, 4 fils) [mes.] : KL(llama processeur ‖ réf. OpenAI)
  0,0255 (médiane 0,0027, 90,4 %) ; réf. rampe llama.cpp 0,0273 ; réf. llama.cpp + imitations Q8_0
  et KV f16 0,0220 (I TOMBE, seuil 2,5e-3) ; cassure sans échelle 0,249 (57 %) ; réf. OpenAI ‖ réf.
  llama.cpp 0,0145 ; réf. ‖ réf. + imitations 0,029. D TIENT (réf. rejouée identique au bit).
  B (routage imposé) TOMBE au seuil 1e-3 : 0,00168, mais 88 % de la KL retirée. gpt-oss amplifie
  toute perturbation de 1e-3 en KL ≈ 2e-2, d'abord par les bascules de routage (top-4 discontinu).
- En cours : ref-llamacpp-bis (D pour la rampe llama.cpp + journal de routage → bascules.py).
- R0 carte et R1 carte (chemin 1) : en attente de la carte (verrou du lot K à 17 h 01,
  llama-completion de l'agent gpt-oss) ; r0_ecart.py carte attend de lui-même.

- 19 h 59 à 20 h 20 (verrou pris, carte au repos 344 Mio, secteur) : R0 carte et R1 carte faits.
  T1, T2, T3 tiennent ; 4 configurations déterministes au bit ; G_cfg = 0 exactement (carte_fit et
  carte_fitauto = carte_cmoe au bit en lots de 512) ; G_moteurs 0,022741. R1 littéral TIENT
  (0,022612 ≤ 0,022741), cassure TOMBE (0,264). Résumés : r0/r0-resume.json, r1/r1-resume-20b.json
  (les CSV et JSON de `juge kl` de R1 sont rangés sous r0/, par r0.juge_kl : cosmétique).
- R2 : témoin disque refait au calme : tient (×3), cassure tombe ; juge comparer sur moteurs réels.
- « carte_fit » de r0_ecart.py était faux (-ngl 99 abandonne --fit) : barré dans le code, vraie
  répartition « carte_fitauto » ajoutée et mesurée.
- Les passes de la référence (15 h 35 à 17 h 35, 4 fils, ≈ 2,5 Go privés) ont recouvert les passes 1
  à 4 de la série 120b de l'agent gpt-oss (16 h 47) : à lui dire (ses temps, pas nos logits).
- Reste au lot : R1 sur 120b (référence f64 du 120b : ≈ 61 Go d'experts lus par passe, ≈ 4 à 6 h
  estimées [est.] ; base llama.cpp 120b à écrire) ; Q0 après J1.

## Besoins et défauts de la spécification (à porter à l'arbitre)
1. § 5.6 `rope_yarn` ne dit pas quelle rampe (OpenAI, bornes réelles 8,0928 / 17,3981 ; llama.cpp,
   8 / 18). Proposé : la rampe d'OpenAI (le modèle, `truncate: false`) ; la mesure Y de R1 chiffre
   l'écart. Choix prudent tenu ici : la référence suit OpenAI, la variante llama.cpp reste mesurable.
2. § 7.1 C4 écrit « KL(troncons ‖ référence f64) » : lu littéralement, la base serait troncons.
   Proposé : KL(référence ‖ moteur) (la vérité en base, comme R1 au § 6.5 « KL(référence ‖ llama.cpp
   carte) ») ; `juge comparer` relève les deux sens. Réponse par délégation du 2026-10-15,
   réversible : le sens de R1, pour qu'un seul instrument juge R1 et C4.
3. § 7.1 C4 « la première ≤ la seconde » sur des moyennes : deux moteurs également justes y
   échouent une fois sur deux par le bruit. Proposé : verdict statistique sur la différence appariée
   (d̄ ≤ 2σ(d̄), ē ≥ −2σ(ē)) ; `juge comparer` rend les deux verdicts, le littéral reste celui qui
   compte tant que l'arbitre n'a pas décidé.
4. § 6.5 R1, « KL(référence ‖ llama.cpp carte) ≤ max(G_moteurs, 7e-5) », est mal posé pour un MoE
   (mesuré, § 2.8 de R-pour-le-memoire) : gpt-oss amplifie toute perturbation de 1e-3 (arrondi,
   rampe) en KL ≈ 2e-2 par les bascules du top-4 ; la distance de tout calcul approché à l'exact est
   alors du même ordre que G_moteurs, et le critère ne départage qu'une erreur grossière (cassure
   0,249) d'une référence juste, pas une petite erreur (la rampe seule : 0,0145). Proposé (R1') :
   juger la référence contre llama.cpp **à routage imposé** (les experts de llama.cpp, relevés par
   le traceur de l'agent gpt-oss, ffn_moe_argsort, sur les mêmes fenêtres de wikitext), avec les
   imitations Q8_0 et KV f16 : régime linéaire, seuil à dériver d'une passe témoin. Besoin d'un
   autre lot : une trace de routage de llama.cpp sur nos 10 fenêtres (format du traceur). Tant que
   l'arbitre n'a pas décidé, le critère littéral est appliqué et publié tel quel.
5. Même cause pour J1 C4 : « KL(troncons ‖ réf.) ≤ KL(llama ‖ réf.) » sur des moyennes dominées
   par une queue de bascules ; à juger aussi à routage imposé (ou par la part des positions sans
   bascule), sinon le verdict dépend du hasard des quasi-égalités du routeur.
6. Q1 (§ 7.3) : 0,0055 (Qwen3.5-4B) à barrer et remplacer par G_moteurs de gpt-oss-20b mesuré en
   R0 : 0,022741 (quatre fois plus) ; même réserve que 4 (amplification par les bascules).
7. § 6.5 R0 : « `--cpu-moe` contre `--fit` » ne mesure rien en lots de 512 (les deux rendent les
   mêmes octets) ; si G_cfg doit servir, le mesurer en génération (lots de 1).
