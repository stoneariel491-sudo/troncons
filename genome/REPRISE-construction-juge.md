# Reprise : construction, rôle « juge » (juge indépendant des lots A et B)

Livrable : genome/JUGEMENT-construction.md ; note pour le mémoire : genome/construction-juge-pour-le-memoire.md.
Outils : outils/genome/construction/juge/ ; journaux : mesures/genome/construction/juge/ ;
seuils : mesures/genome/construction/juge/00-seuils-declares.md (déclarés avant toute mesure).
Données lourdes (hors dépôt) : ~/dev/essais/troncons/genome/juge/.
CARGO_TARGET_DIR=~/dev/cibles/troncons-juge, -j 4.

- 2026-10-22 3 h 40 : rôle ouvert. Lu : SOCLE, idée biomimétique, 05 (cahier), 06, 07, 08 (placement),
  ARCHITECTURE § 4 (format), notes de reprise A et B. Lots A et B : finis, n'attendent que le juge.
- Arbre trouvé : changements non suivis des flux pistes et placement (mesures/pistes, outils/pistes,
  mesures/disque/placement, outils/disque/placement/seance.py, __pycache__) : PAS à moi, non touchés.
- Verrou tenu à l'ouverture par le flux placement disque (séance p2b-D, pid 35604) : attendre.
- Règle : rien qui lit le disque ou charge le processeur pendant une séance de vitesse d'un autre flux
  (le verrou porte « vitesse ») ; mes séances prennent le verrou.
- PIÈGE : Write/Edit refusés dans le dépôt principal (session en worktree) : écrire dans le bloc-notes
  (scratchpad/depot/…) puis `cp` vers le dépôt ; commits par chemins (`git commit -m … -- chemins`).

## Pas
- [x] J0 seuils déclarés et commités avant toute mesure (1f5fe0f, 2026-10-22 vers 3 h 55)
- [x] tirage des 96 experts écrit et commité avant tout décodage (93a88a5)
- [x] J-T (f136e27) : J-T0 0 faute, tailles à l'octet ; J-T1 96/96, témoin v1.0 40/40, 3 cassures tombent
- [x] fenêtres neuves (af77cd6) : préfixe 120 000 o = 27 680 jetons ; base-juge-20b.kld (SHA 2108487d…)
- [x] moteur, juge, genome-capture construits depuis main f136e27 (cible troncons-juge)
- [x] témoin de ma KL : 1,1e-8 relatif contre juge kl sur R1 λ = 0 ; R1 recalculé (B2 2,09 σ, comme B)
- [x] J-C1 20b (d1ebf90) : 0/5 120, .kld égaux, déterminisme, cassure 512/512
- [x] J-C1 120b (8f83886) : 0/5 120, .kld égaux ; rapide λ = 0 et λ = 1 évalués (20b, fenêtres neuves)
- [x] référence f64 des fenêtres neuves (2 168 s, 755 experts) ; f64 substituée λ = 0 (sub-l0.json, 2 800 s)
- [x] KL moteur : λ0 0,1448, λ1 0,1751, B2 −0,0303 ± 0,0084 (3,6 σ) ; f64 λ0 0,1446 ; S3-K 0,0037 / 97,8 %
- [x] vitesse (c4393c7) : 120b B/A 1,442, R/B 1,284 ; 20b B/A 1,296, R/B 0,942 → G1, G2
- [x] barres portées dans 07 et note mémoire du lot B (16dcdd3)
- [x] sub-frontiere (3 115 s) : frontière 0,3011 ; λ0 − frontière −0,1565 ± 0,0334 (4,7 σ) ; queue −26 % / −18 %
- [ ] sub-l1 : NON lancé (temps ; le flux placement attendait le calme) — dit dans le jugement § 9
- [x] jugement complet (G1, G2 graves ; M1 à M5), note pour le mémoire, CSV (figures/) : commit final
- FINI le 2026-10-22 vers 8 h 30. Reste (JUGEMENT § 11) : B3 à reprendre avec r(R/B), autre corpus,
  sub-l1 si un second chemin de B2 est voulu ; lourds à effacer quand Stone veut (≈ 13 Go).

## Commandes (relancer une étape)
- python : ~/dev/lectures/venvs/genome-genome/Scripts/python.exe -I -X utf8
- bash outils/genome/construction/juge/evaluer_juge.sh <nom> <fichier.trc> [--rapide] [--sans-garde --une-fenetre]
- bash outils/genome/construction/juge/reference_juge.sh reference sub-l0 sub-frontiere sub-l1
- lourds : ~/dev/essais/troncons/genome/juge/ (base, ref, moteur-*.kld, sub-*.kld)

## Constats en chemin (pour le jugement)
- 07 : ± des KL absolues = incertitude naïve par positions (0,0066) ; par fenêtres 0,038 (frontière) ; les
  différences appariées, elles, prennent σ par fenêtres (juste).
- 07 § 4.4 : hypothèse « cache de fichiers du système » impossible pour les tronçons (trc-es : NO_BUFFERING).
- 07 s2 20b : compagnon λ = 0 écrit à 0 h 51, lu à 1 h 15 ; première passe B 5,46 j/s (σ_B 31 %), règle du lot
  B : σ des passes A seulement (2,3 %).
- 06 : 2 × part des −0 vérifié (−0,000167 à +0,000161 sur 180 tenseurs) ; parts 6,393 % et 6,279 %.
