# Reprise du routeur biaisé en ligne (P3), note télégraphique

Etat au 2026-10-27 (mis à jour après chaque pas).

- FAIT : déclaration `mesures/mimetisme/P3/06-routeur-ligne-declare.md` (commit avant toute mesure).
- FAIT : option `--biais-cache <β>` dans le moteur (commit eb78770) ; noyau neuf `routeur_topk_biais` (passe.cuh), `Noyaux::routeur_topk_biais`,
  `Modele::debut_couche_biais`, `Config::biais_cache`, tampon de biais dans `Moteur`. Tests (noyaux, cache, modèle, ordo, bin) verts ; test du noyau
  contre un oracle hôte, sa cassure tombe.
- Construction : `CARGO_TARGET_DIR=~/dev/cibles/troncons-P3 cargo build --release --offline --locked -j 4 -p troncons -p trc-cache`
  (binaire d'avant l'option : `cibles/troncons-P3/release/troncons-avant.exe`, SHA-256 7bc07cd4…a4d4).
- Séance d'évaluation (pilote `outils/mimetisme/P3/p3_routeur_ligne.py`, SANS -I) : `P0 B0.041 B0.3 P0b B0.05 P-1:3`, ~20 min par passe, lancée
  le 2026-10-27 vers 10 h 45 ; résultats sous `mesures/mimetisme/P3/routeur-ligne/<passe>*.{json,log,trace,csv}` (le .kld sous
  `essais/troncons/mimetisme/P3/routeur-ligne/`). Verrou de la carte `~/dev/verrou-carte.txt` ("P3 routeur") : à SUPPRIMER si la séance est morte.
- A FAIRE : analyse (KL par `juge kl`, premier choix littéral/pondéré, cellules changées, défauts, `rejouer` sur les traces, lecteur .kld indépendant),
  génération ABBA (A = sans drapeau, B = `--biais-cache 0.041`, 2 blocs ABBA), puis `resultat-routeur-ligne.md`.

- FINI 2026-10-27 ~13 h 40 : toutes les passes, génération ABBA, analyse, `resultat-routeur-ligne.md`. Verrou de la carte retiré. Non fait : cassure de signe (arrêtée deux fois par le garde-fou RAM), vitesse en séance calme.
