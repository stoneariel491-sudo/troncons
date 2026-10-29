# Reprise : placement disque (08)

- 2026-10-22 1 h 20 : rôle ouvert. Demande de Stone : corrélation fragmentation, position, débit ; exploiter.
  Livrable genome/08-placement-disque.md ; outils outils/disque/placement/ ; mesures mesures/disque/placement/.
- Arbre trouvé : fichiers non suivis des autres (synonyme/vitesse s2-*, pistes/spectres, __pycache__) : PAS à moi.
- PIÈGE : Write/Edit refusés dans le dépôt principal (session en worktree) : écrire dans le bloc-notes
  (scratchpad/depot/…) puis `cp` vers le dépôt.
- Verrou tenu par lot B (pilote_vitesse.py s2, pid 42412, depuis 1 h 09) : attendre.
- Disque : 60 Go libres au départ. Règle : ≤ 12 Go à moi à la fois ; libre ≥ taille + 45 Go avant toute écriture.
- SMART NVMe lisible sans admin (température 55 °C, unités lues/écrites) : sonde dans lire.py.

## Pas
- [x] P0 lu : 06 §§ 6, 8, 12 ; trc-es (NO_BUFFERING|OVERLAPPED, une lecture par tronçon, profondeur 4) ;
      troncons disque (1 500 tronçons tirés, graine 20261017) ; trc-codeur (Ecrivain : BufWriter 8 Mio, tamponné,
      sans taille réservée) ; 01-machine § 2 (plateau 2,4-2,9 Go/s, BitLocker, iaStor VMD).
- [x] P1 carte.py (témoin tient, cassure tombe) ; cartes des 5 .trc ; p1_correler.py.
      Constats : C120 267 473 extents (médian 8 Kio), 60 morceaux/lecture ; A 1,009 et B 1,051 → H1 tuée pour A/B ;
      A à 6,7 h (1,86) plus lent que B à 110 h (2,3) → âge seul tué ; LCN moyen A 0,64, B 0,82 (H2 à tester dans A).
- [x] plan déclaré (08 § 2) AVANT toute mesure.
- [x] lire.py, placer.py, seance.py, commun.py (verrou, calme, SMART), analyse.py : essais à petite échelle verts
      (témoin SHA 8/8, cassure 0/8 ; copie traite et entrelacée = SHA source ; empreinte cassée différente).
- [x] p2a (2 h 18-2 h 33, calme, commit 1d75500, 08 § 3) : B20/A20 1,42 ; H2, H4(B), H5a, H6 thermique tombent ;
      H1 tient pour C seul (τ 0,37 ms/morceau) ; C non coupé 1,6 × plus vite que A (même contenu) ; A120 entier : arrêts ~20 s.
- [x] p2b-D (3 h 40-3 h 45, commit aca2494) : D20 = copie de A20 d'une traite (5 extents, SHA ok) ; D20/A20 1,185 ;
      D20/B20 0,858 (lu 1-3 min après écriture). D20.trc À MOI : ~/dev/essais/troncons/placement/D20.trc (11,2 Go).
- [x] p2b-D2 (5 h 55, 2 h 14 après écriture) : D20 1,779 = A20 1,760 (égaux) → le neuf retombe ; H5b tient.
- [x] p3 (5 h 58-6 h 14) : mesurer A20/D20 ABBA : 9,380 / 9,398 j/s (1,002), mêmes jetons, mêmes octets → levier « réécrire » nul.
- [x] D20 effacé (6 h 14). E20 abandonnée (08 § 2.5). Amendements § 2.5 (F20 filet, comme le codeur) et § 2.6 (H7 profondeur).
- [x] p2b-F (7 h 15-7 h 25, commit 25631c6) : F20 filet 95 extents, SHA ok ; frais F20/A20 1,24 ; F20/B20 0,89.
- [ ] p4 : arrêté 8 h 19 avant toute passe (batterie). À refaire sur secteur : seance.py p4.
- [x] F20 EFFACÉ à 10 h 03 (garde automatique) ; F2 non fait. Dossier essais/troncons/placement/ vide.
- [x] 08 complet (§§ 0-12), note pour le mémoire, bib, figures CSV.
- [ ] À refaire sur secteur : seance.py p2b-F puis ≥ 2 h après seance.py p2b-F2, puis effacer F20 ; seance.py p4.
- 2026-10-22 10 h 07 : secteur revenu, Stone : « continuer ». p2b-Fb (F20 réécrit, frais 2,03-2,10 ; arrêt de 21 s sur A20),
  p4 (q8/q16 plus lents ; q2 × 1,125 / 1,133), p5 (q2 × 1,080 sur A20 : sous S, levier non retenu ; p6 tuée par les nombres),
  p2b-Fb2 (+ 2 h 08 : F20 1,831 = A20 1,780, égaux : la manière d'écrire n'est pas la cause).
- [x] F20 EFFACÉ à 12 h 30. Dossier essais/troncons/placement/ vide. Verrou rendu. 08, note mémoire, figures à jour.
- FIN du rôle (reste : juge de 08 ; relevé quotidien A20/B20 ; défragmentation de C120 = commande pour Stone, 08 § 12).
- 2026-10-26/27, hypothèse de relais après le retrim de Stone (23 h 46) : déclarée 23 h 49 (bcae307) ; p7 (G20a, G20b,
  SHA ok, frais sous charge) ; p7-2 à + 2 h 06 : G20a 1,778, G20b 1,778, A20 1,734, B20 2,506 → TOMBE (1,025 × A20) ;
  témoin Ga/Gb 0,9998 ; cassure 0/16. Lu au seul motif v1.0 (cf. jugement G1). G20a, G20b EFFACÉS 3 h 15 ; dossier retiré.
