# Reprise : juge du placement disque (08)

- 2026-10-22 12 h 30 : rôle ouvert. Juge indépendant de genome/08-placement-disque.md (commits 09f87a3 à 5838195).
  Livrable genome/JUGEMENT-placement.md ; outils outils/disque/placement/juge/ ; mesures mesures/disque/placement/juge/.
- PIÈGE : Write/Edit refusés dans le dépôt principal (session en worktree) : écrire dans le bloc-notes
  (scratchpad/depot/…) puis `cp` vers le dépôt ; git -C ~/dev/active/troncons.
- Arbre trouvé : fichiers non suivis des autres (__pycache__, mesures/pistes/spectres/*) : PAS à moi.
- Machine à 12 h 34 : secteur (BatteryStatus 2, 80 %) ; BitLocker C: actif (Shell.Application,
  System.Volume.BitLockerProtection = 1, sans administrateur) ; verrou libre ; pistes en cours :
  levier.py (pid 27192/28336) et normalise.py (pid 45472/22608, 0,84 cœur) → PAS CALME, attendre. Ne rien tuer.

## Pas
- [x] Lu : SOCLE, 08, REPRISE-placement, placement-pour-le-memoire, outils (lire, carte, seance, commun, analyse,
      analyse_qd), main.rs disque, trc-es, en-tête trc-format, JUGEMENT-construction §§ 6, 7, 11.
- [x] git : §§ 2.1-2.4 de 08 inchangés depuis 09f87a3 (01 h 33, avant p2a 2 h 18) ; § 2.5 commit 05 h 59 < p2b-F
      7 h 15 ; § 2.6 commit 06 h 16 < p4 10 h 22 ; § 2.7 commit 10 h 30 < p5 10 h 35. Rien tiré après coup.
- [x] Vu en lisant : R20 (compagnon λ=0, écrit 22 oct 0 h 46-0 h 51 par l'Ecrivain) rapide à + 6 h (juge
      construction 2,47 Go/s = B20) → contredit « état du 17 » ; C120 non coupé 0,763 Go/s par lecture × 4 > plateau
      → file mêlée ; critère H1 sans puissance probable ; p6 jugée contre un plancher pas contre son bruit.
- [x] 00-seuils-declares.md commité AVANT tout recalcul et toute mesure (c34d836, 12 h 45).
- [x] J0 recalcul (5796032) : tout redonné ; critère H1 sans puissance (constant 0,970/0,982) ; file de C120 :
      non coupées entourées de non coupées 0,43-0,45 Go/s = A120 → « C non coupé 1,6× » faussé ; F20 > A20 16/16 ;
      p6 : gain 4,9-8,8 % contre bruit de bout en bout 0,8-4,6 % ; citations lot B / juge = valeurs basses, pas médianes.
- [x] outils (2ec9b25) : carte_juge, lecteur (IOCP), machine, seance_juge ; analyse_juge écrit (pas encore commité).
- [x] séance principale 12 h 56-13 h 13 (9de49c5) : cartes = 08 au bit ; J2 B20/A20 1,398 (a redonné) ;
      témoins (troncons 0,945/0,977, frein 0,54 tombe, SHA 16/16, 0/16) ; J3 motif croisé : A20 lu au motif de B20
      2,445/2,449, B20 au motif de A20 1,79/1,81 → la lenteur SUIT LE MOTIF (indicatif : arrêt dans J3-08) ;
      J4 R20 2,44 = B20 (indicatif, arrêt J4-11) ; J7 q2 ×1,10/×1,14 (arrêt J7-01) ; J5 C120 tiré : t1 34 ms,
      τ 9-11 µs (08 : 17 ms, 365 µs = chemin synchrone de lire.py, pas celui du moteur) ; J6 C[U]/A[U] 0,98
      (« C non coupé 1,6× » TOMBE) ; contigu aujourd'hui ×1,26 (pas 1,43). Arrêt : batterie à J6-12 ; J8 non fait.
- [x] amendement § 5 (495ab4b, 13 h 19 ; heure barrée cbc5321) : passes à arrêt écartées, J3/J4/J7 refaites
      en J-bis, J9 (longueur des lectures, pas de fenêtre), J8. Analyses commitées (6fa1e55).
- 22 oct ~13 h 40 : figé (pause de Stone « Met une pause temporaire à tout »). Reprise 26 oct 23 h 44 (« go ») :
      secteur, 93,2 Go libres, verrou libre ; pistes : plafond_rangee.py, indices.py tournent → attendre le calme.
      QUATRE JOURS d'écart avec les mesures du 22 (R20 a ~5 jours ; A20 11 j ; B20 9 j). Retrim NON fait
      (défragmentations planifiées annulées du 23 au 26, événement 264).
- [x] Retrim fait par Stone, fini 26 oct 23 h 46 min 44 s : TOUTES les passes J-bis après (1re finie 23 h 47 min 37 s).
- [x] J-bis 23 h 47-0 h 44 (c1ee084, analyse a735439) : J3 suit le motif (×1,388 / ×0,715) ; J4 R20/A20 1,379,
      R20/B20 0,981 (état du 17 TOMBE) ; J7 q2/q4 1,116 et 1,163, q8/q4 0,97/0,91 ; J9-L LA LONGUEUR DES REQUÊTES
      DÉCIDE (A raccourci ×1,421, B allongé ×0,713) ; J9-P pas de fenêtre non ; J8 A120 entier 1,702 sans arrêt.
      Écartées : Jb4-12 (sous charge), Jb7-02 et Jb9-14 (SMART 1,031/1,036). Retrim : A20, B20 +1 à +4 %, B/A inchangé.
- [x] amendement § 6 (a735439 0 h 48 ; heure barrée 1b9110e) : J10 = A20 en deux requêtes par tronçon, q = 8.
- [x] J10 : 1 h 08 pas de calme → arrêtée avant toute passe, verrou rendu à la main ; refaite 3 h 15-3 h 17 (créneau
      d'après p7-2) : A20 en deux requêtes, q = 8 : × 0,851 (ma prédiction TOMBE). Amendement § 7 (37b31bd) → J11 q = 4 :
      × 0,882. La longueur seule ne décide pas ; « le levier est dans la lecture » barré (96bc12d) dans le jugement et
      dans mes notes de 08. Levier qui marche : recoder en v1.2.
- [x] p7-2 de l'enquête jugé (cddd056) : redonné ; relais TOMBE (vue sans la passe à arrêt ; à la lettre S = 187 %, vide).
- [x] JUGEMENT-placement.md (a8926bc) ; barres dans 08 et note mémoire (057224b).
- [x] hypothèse de relais (retrim) : à évaluer dans le jugement (J3, R20, C120 la contredisent ; protocole pour Stone).
- FIN du rôle 27 oct. ~3 h 30. Reste (jugement § 12) : isoler la variable du motif v1.0 (motifs déclarés avant) ;
  identité NVMe (geste admin de Stone) ; porter 06 § 8 et JUGEMENT-construction §§ 6, 11 (orchestrateur) ; RECETTES.
