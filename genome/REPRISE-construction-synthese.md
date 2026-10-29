# Reprise : construction, rôle « synthese » (synthèse de la ronde 1 et cahier de construction)

- 2026-10-17 : rôle ouvert et **terminé** (livrable complet, tout commité).
- Consigne : genome/05-synthese.md (frontière bits contre KL + CSV ; ce qui gagne et tombe et pourquoi ;
  pistes ouvertes ; cahier de construction des lots A et B).
- Sur la consigne de Stone, même jour : écrit au
  fil, commité section par section.
- Arbre sale trouvé au départ : mesures/genome/genome/kl/passe10-* (passe K10 de l'équipe genome,
  processus vivant à 07:45) : PAS à moi, non touché.

## Fichiers à moi
- genome/05-synthese.md (§§ 0 à 6, 847 lignes environ)
- genome/construction-synthese-pour-le-memoire.md (plan, énoncés, tableaux, 10 figures)
- genome/REPRISE-construction-synthese.md (cette note)
- outils/genome/synthese/frontiere.py (lit les journaux des 4 équipes ; témoin + cassure)
- mesures/genome/construction/synthese/ : frontiere.csv (23 points), erreur-contre-kl.csv,
  colonne-par-tenseur.csv, apparie-eclaireur.json, frontiere.log, frontiere-casse.log
- memoire/sources/genome-construction-synthese.bib (Zhang-Naitzat-Lim 2018 ; Martin-Mahoney 2018 ;
  résumés lus à la source le 2026-10-17)

## Résultats à retenir
- Appariée éclaireur (λ = 0 contre frontière, P1) : −0,009845 ; σ naïf 0,00190 ; σ par fenêtres
  0,00334 (2,9 σ) ; 2 060 / 2 550 positions ; premier choix +3,73 ± 0,59 points.
- Correction barrée : la KL 0,0262 est celle de λ = 0 (2,649 bits H0), pas de λ = 1.
- Colonne : 2 matrices sur 12 au seuil 0,015 → 3,6843 bits (toutes : 3,6825).
- Trois propriétés : bruit sachant l'échelle ; colonnes géantes ; erreur d'expert ≠ KL
  (KL = part lisse + queue de bascules ; routage imposé retire 88 % de la KL, R § 2.9).
- Lot A : v1.2 (bits 3 CANONIQUE et 4 COLONNES, octet 123 = Q, sorte 0x13 CODES_COL géométrie 2
  contexte 4κ + q, charge 4 = carte C/4 o, répertoire +56 empreinte canonique) ; preuve A1 sur
  gemv.cuh ; LUT compacte demi-octets 25,5 Kio (lemme A2) ; critères A-T1..A-C4.
- Lot B : <nom>.rapide.trc (bit 5 RAPIDE, BASE_CTX + CENTRES, RÉSIDENTS vides) ; B0 d'abord (KL de
  λ = 1) ; lemme B2 : α > 1 − ρ + b_d/b_e (le brouillon doit être résident ; 120b rapide 37 Go ne
  tient pas en RAM) ; critères B0..B5 ; réponse par délégation : repère = requantification llama.cpp.

## K10 (arrivée à la fin)
- La passe K10 de l'équipe genome a fini pendant ce travail : S* égal à la base sur 10 fenêtres
  (+0,0004 ± 0,0019 ; médiane ÷1,21 ; 99,9e +16 %). Intégrée dans 05 (barré « tombe »), chiffres
  recopiés à la main ; ses fichiers (mesures/genome/genome/kl/comparer10-*, kl10-*, passe10-*) NE SONT
  PAS commités (pas à moi). Quand l'équipe ou l'orchestrateur les commite : relancer
  `python -I outils/genome/synthese/frontiere.py --k10` et commiter les CSV.

## Ce qui reste (pas à ce rôle)
- Relecture de 05 par un juge qui ne l'a pas écrit (SOCLE, « la barre »).
- Porter les recettes de 05 § 6 dans RECETTES.md (orchestrateur).
- Scripts des figures F4, F5, F6, F7, F10 (note du mémoire § 6).
- Construire les lots A puis B selon 05 § 4 (A0 = la décision dans ARCHITECTURE.md d'abord).
