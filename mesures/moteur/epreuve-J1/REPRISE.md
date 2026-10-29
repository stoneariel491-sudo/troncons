# Reprise de l'épreuve indépendante J1 (style télégraphique)

Rapport : `mesures/epreuve-J1.md`. Outils et journaux : ce dossier. Sorties lourdes (hors dépôt) :
`~/dev/essais/troncons/epreuve-J1/` (clone propre, séances, .kld).

## 2026-10-16
- 02 h 12 : arbre propre (seuls des __pycache__ non suivis), carte libre, secteur (BatteryStatus 2).
- Geste 1 FAIT (commit 527dff5) : `decodeur_s4.py` écrit depuis le seul § 4 ; 120b 20/20, 20b 20/20
  égaux au GGUF au bit près (graine 20261016) ; résidents 471 et 315 octet pour octet ; 4 cassures
  tombent sur le seul tronçon visé. Compagnons vocab conformes.
- Clone propre → `~/dev/essais/troncons/epreuve-J1/clone` (527dff5) ; construit dans
  `~/dev/cibles/troncons-epreuve` par `construire.bat` (SANS vcvars : le build.rs de
  trc-noyaux casse si cl.exe est déjà dans le PATH).
- Copies corrompues (lots E et O) : 12/12 et 1/1 détectées par mon décodeur ; 2 dans des flux bruts
  (médiane 23:4, biais 21:24) passent le contrôle des voies : invisibles en production.
- Séance de vitesse `s1-2026-10-16` lancée à 02 h 27 (verrou pris à 02 h 26, `pilote_epreuve.py`).
- Charge étrangère notée : un `find` lancé à 21 h 52 par un autre (≈ 1 cœur), non touché.
- Reste : analyse de la séance ; C3 120b (`--ordre c3`) ; passe numpy 20b (et 120b si le temps) ;
  rapport.
- 02 h 27 à 03 h 23 : séance s1 (12 passes) : C5 tient, C7 plafond tient et écart tombe, C10 tient, base
  -t 10 +12 % (réel), C6 × 2,79, cache tiède +994 Mo.
- 03 h 23 à 04 h 17 : C3 et C11 sur 10 fenêtres du 120b : TIENNENT, = lot O octet pour octet. Blocage
  de la passe brute sous charge (G1), diagnostiqué par la pile, processus tué (le mien) ; relancée
  seule, elle passe.
- numpy f64 : 20b (6 min) et 120b (17 min), fenêtre 0 : référence du lot R à 0,504 pas ; C4 tient sur
  20b et 120b.
- 04 h 18 à 04 h 44 : compléments : témoin C2 (3 394 / 3 394), cassures du moteur (XE2 nommée, XO3
  muette et même texte, XO3t nommée), base llama.cpp 120b fenêtre 0. Orphelins nvidia-smi (G2) : les
  miens tués, celui de 01 h 38 (PID 13652, pas à moi) laissé. Verrou rendu à 04 h 44.
- 04 h 44 : passe numpy 120b sur les 708 jetons de l'invite (premier jeton de C12 : « am » ou « ... »).
- Rapport écrit : `mesures/epreuve-J1.md` ; pour le mémoire : `moteur/epreuve-J1-pour-le-memoire.md`,
  `memoire/sources/moteur-epreuve-J1.bib`.
- Reste : remplir le § 6.1 du rapport avec le premier jeton.
- 04 h 44 à 06 h 05 : premier jeton de C12 tranché : vérité f64 « ... » (1008), troncons « am » (313,
  log p vrai −10,03), cascade de 20 bascules à 707 ; vérité + KV f16 seul → 313 aussi (expérience
  déclarée, commit 549b38b) ; le KV f16 porte 70 à 77 % des bascules du 120b. Pas de rupture à 512 (PPL
  vraie 1 222 sur le passage). Invariances --contexte 1024 et --emplacements 200 : 0 ligne différente.
- FAIT : rapport complet. Rien sur la carte, verrou rendu, aucun processus à moi.
