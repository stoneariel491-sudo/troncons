# Reprise : construction, rôle « codon » (lot A, codon synonyme du zéro, format .trc v1.2)

- 2026-10-17 : rôle ouvert. Consigne : genome/05-synthese.md § 4.1 à 4.6 (cahier A). Livrable :
  genome/06-codon-v1-2.md.
- Sur la consigne de Stone, même jour : écrire
  au fil, commiter pas à pas.
- Arbre trouvé : mesures/genome/genome/kl/passe10-* et comparer10-* (passe K10 de l'équipe genome) :
  PAS à moi, non touchés. mesures/moteur/*/__pycache__ : pas à moi.
- CARGO_TARGET_DIR=~\dev\cibles\troncons-codon, -j 4.

## Constats de départ (lus, pas de mémoire)
- Les fichiers .trc sur le disque sont **v1.0** (octets 8..12 = 01 00 00 00 ; drapeaux = 1), pas
  v1.1 : la consigne dit « v1.1 », le cahier dit « v1.0 » ; la v1.1 (deux niveaux de B) n'est
  écrite par aucun codeur (trc-codec refuse niveaux ≥ 2 : « étape F4 (J2) »). trc-format lit déjà
  jusqu'à 1.1 (VERSION_MINEURE = 1). Comparaison du lot A : v1.2 contre **v1.0**.
- Un seul lecteur des valeurs E2M1 dans les noyaux : `valeur_e2m1x2` (gemv.cuh l. 33) ;
  trc-reference K_MXFP4[8] = −0.0 (f64) ; banc_k.cu et tests/carte.rs : (code & 8) ? −v : v.
- Le décodeur CUDA (decodeur.cuh) ne lit pas les valeurs des symboles : un flux CODES_CTX bâti sur
  des codes canoniques se décode sans rien changer au noyau (tables à fréquence 0 pour les 31 octets
  qui portent un demi-octet 8).
- Chiffre à égaler (taux_reel, prédictif-élagage, flux rANS réels, voies à L) : 120b 3,8549 →
  3,7292 bits par poids ; 20b 3,8509 → 3,7230.

## Pas
- [x] A0 décision v1.2 : ARCHITECTURE § 4.16 (+ invariant § 5.6) ; colonne HORS v1.2 (chiffrée,
      réponse par délégation) ; commit 8da13fb
- [x] vérification 1 : ggml kvalues_fp4[8] = 0 (ggml-common.h b11515 l. 1124-1129, SHA-256
      0061131b…595c, lu le 2026-10-17) ; carte : tests/carte.rs::gemv_lit_le_code_8_comme_0 (2 486 216
      −0, 8 640 lignes, 0 diff, cassure vue) ; référence f64 : trc-reference/tests/code_8.rs
- [x] A1 trc-format ; A2 trc-codec ; A4 codeur (--canonique) + verifier (--casser-8) ; A5 témoin
      trc-ordo + banc-chemin ; essais de l'espace 82 verts ; cassures des témoins : tests-casses.txt
- PIÈGE : lancer.ps1 en « sous la normale » affamait le codeur (16 Mio / 15-30 s) avec 4 Python d'une
  autre équipe : priorité normale. TaskStop n'a pas tué la chaîne bash : tuer les PID à la main.
- [x] identité : codeur modifié sans --canonique = gpt-oss-20b.trc de F2 (SHA-256 e8bd6ae1…169f)
- [x] 20b v1.2 : ~/dev/modeles/trc/gpt-oss-20b-v12.trc (10 851 844 096 o, SHA-256
      ef1cf740…c433) ; C1 768/768 en valeur ; cassures --casser 5 7 et --casser-8 11 3 : exactement l'expert
- [x] A-C1 20b (pilote s1, phase c1-20b) : 5 120 / 5 120 égales, .kld égaux, cassure 512/512 (--sans-garde :
      la garde de production refuse la copie à médiane faussée avant tout logit, journal -avec-garde)
- [x] 120b v1.2 : …/gpt-oss-120b-v12.trc (55 930 175 488 o, SHA-256 97c292ae…f0f3) ; C1 4 608/4 608
- [x] A-C1 120b : 5 120/5 120 égales au CSV v1.0 du 2026-10-15, .kld égaux (5b212fe9…)
- [x] analyse_codon.py tailles (A-C2 tient : 0,12791 et 0,12562) ; tables_octets.py (0/540 tables v1.2
      avec fente pour un 8)
- [x] J1 s1 (10:24-10:50) : jetons égaux 8/8, octets 0,9671, r 1,11 σ 21,6 % (pas de régression,
      gain non annoncé), mémoire −6,41 Mo ; écart trop grand → témoin « copie neuve du v1.0 » déclaré
- [x] copie_temoin.sh : phase disque s1 (v1.0 1,60 ; copie 1,41 ; v1.2 2,44 Go/s) ; fragments v1.0 65,
      v1.2 233, copie 289 545 → témoin confondu ; j1-copie s1 arrêtée après 2 passes ; copie effacée
- [x] identité 120b : v1.0 recodé aujourd'hui = 6c7b5f1d…dcce (= origine) ;
      ~/dev/modeles/trc/temoin-codon/gpt-oss-120b-v10-recode.trc (57,7 Go, À MOI, à effacer
      à la fin du rôle ou à garder si Stone veut le témoin)
- 2026-10-21, reprise (secteur, 58,9 Go libres, verrou retiré par Stone) : aucune passe de s2 n'avait
  tourné (pilote-s2.log : attente du verrou du lot B à la coupure). **Amendement de s2 déclaré à 23 h 40
  avant toute passe** (en-tête de pilote_codon.py) : phase j1 ajoutée (le j1 de s1 était sous charge),
  témoin C (v1.0 recodé, 47 745 fragments dans l'échantillon) gardé mais confondu d'avance, relevé des
  processus des autres flux avant et après chaque passe, départ sur deux relevés vides (--attendre-calme).
  Commande : python -I -X utf8 outils/genome/construction/codon/pilote_codon.py --phases disque,j1,j1-copie
  --seance s2 --attendre-calme --fichier-c ~/dev/modeles/trc/temoin-codon/gpt-oss-120b-v10-recode.trc
  (le recodage est fait : ne PAS relancer recoder_temoin_120b.sh). Puis analyse_codon.py disque/j1 --seance s2.
- PIÈGE 2026-10-21 : l'outil Edit refuse d'écrire dans le dépôt principal depuis la session en worktree ;
  les écritures passent par des scripts Python à remplacement exact (assert un seul motif).
- [x] séance s2 (2026-10-21 23 h 59 au 22 à 0 h 46, 22 passes, aucune sous charge ; commit 96533df) :
      disque A 1,74, B 2,32, C 1,34 Go/s ; j1 r = 1,454 σ 5,6 % (gain annoncé pour les fichiers) ;
      j1-copie r = 1,595 ; jetons égaux partout ; octets 0,9671 ; mémoire −6,45 Mo. Le gain suit le
      fichier (A et C identiques au bit diffèrent de 30 %), pas le format (toit 3,4 %). 06 § 0 et § 8 écrits.
- [x] F6 : tome3_codon.py tire s2 (codon-j1-v10.csv, codon-j1-v12.csv) ; panneau disque à ajouter (note § 5)
- [ ] témoin décisif de vitesse (v1.0 et v1.2 réécrits le même jour) : demande ~113 Go ou d'effacer le
      v1.0 recodé (temoin-codon/, 57,7 Go, à moi) : décision de Stone
- (ancien libellé) séance s2 (recoder_temoin_120b.sh lance pilote --phases disque,j1-copie --seance s2 --fichier-c …) ;
      puis analyse_codon.py disque --seance s2 ; j1 --seance s2 --phase j1-copie ; 06 § 8 ; § 0
- [x] figures Tome III : memoire/figures/tome3/codon-figures.tex compilé OK (F2, F3 ; F6 dès J1)
- 06 §§ 0-7, 9-12 écrits ; § 0 « En bref » à écrire en dernier
- [x] 06-codon-v1-2.md (§§ 0-12), note pour le mémoire, CSV : complets au 2026-10-22 ; reste le juge (A6 et relecture)
