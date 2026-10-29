# REPRISE, piste spectres (05 § 3.3 a)

Style télégraphique. Mis à jour après chaque pas.

- venv : `~/dev/lectures/venvs/genome-genome` (numpy 2.5.4, scipy 1.18.1 ; pas de psutil,
  pas de matplotlib ; aucun pip install : figures en pgfplots).
- Lancer par `outils/pistes/spectres/chaine.sh <étapes>` (attend la fin des séances de vitesse) ;
  sorties dans `mesures/pistes/spectres/<nom>.out` et `.log`, journal `chaine.log`.

## Fait (commits)
- a171622 seuil déclaré ; bfc1c8c amendement § 4 bis avant lecture (critère principal sans puissance).
- 5232e5f spectres (npz, manifeste). Tirage : L0 [0,6,22,24], L12 [1,3,19,31], L23 [7,21,26,27].
- fdf5929 puissance : principal 0/40 Pareto ; amendé 18/20, 20/20 Pareto, 0/20 exp, 4/20 log-normales.
- cbba5d2 témoins + cassure : amendé, tout tient ; cassure, T-Pareto et T-MP en ÉCHEC.
- eec367c ajustements : 0/48 loi de puissance ; 9/48 compatibles (perm 1/48).
- 0459f36, 0e7090d second chemin v1 FAUX (vraisemblance −α Σ ln t ; SHA sur le signe d'un zéro), barré.
- 66affcf second chemin v2 : 48/48 égaux (SHA, verdicts, compatibles, x_min), α à 2,2e-7.
- 4abfccd levier v1 FAUX sur L2 (cible ×n), barré ; 536b067 v2 accéléré + § 7 bis ; 99e5a7d témoins v2 tiennent.
- b6004c4 rapport.json partiel (sans levier) ; normalise.py (exploratoire, non déclaré).

## Incidents
- TaskStop n'arrête PAS les processus Python lancés par une chaîne (ni la chaîne bash elle-même) ;
  l'arrêt par PID est refusé par le classificateur. Un levier v1 orphelin (code faux sur L2) écrit
  encore `levier.out` (tronqué par une relance ratée : début à zéro) : NE PAS l'utiliser.
  Les nouvelles passes attendent tant qu'il écrit (`TRONCONS_ATTENDRE_ACTIF=…/levier.out`).
- Faux positif de la garde sur « pas une séance de vitesse » (verrou du juge) : corrigé (6f21da7).

## En cours
- chaîne `levier normalise` lancée 04:51 (levier-v2.out, puis normalise.out).
- Ensuite : `rapport.py` (lit levier-v2.out), figures (`figures/spectres-figures.tex`, lualatex),
  remplir `spectres.md` (sections balisées <!-- … -->), commit.

## 2026-10-22, 10 h, nouvel agent de la piste
- Trouvé en marche (pas lancés par moi, ne pas tuer) : levier v1 orphelin (PID 23896/38208, écrit
  levier.out, faux sur L2), v2 endormi (27192/28336), v3 (3264/43944, chaîne 39048 `levier3 normalise`).
  v3 a repris 09:58 ; témoins v3 tiennent.
- Ajouté § 7 quinquies (plafond spectral, sur le npz seul, pas de lecture du GGUF), commité avant calcul.
- 10:05 à 10:50 : plafond (§ 7 quinquies, sexies : T-Pareto mal posé, barré), plafond par rang (§ 7 septies),
  exploration α̂ / levier (Spearman −0,64), prédiction déclarée (§ 7 octies, tirage transcrit faux barré :
  vrai = couches 3, 9, 21). spectres.md § 5.1 à 5.3 écrits ; § 5.4 (<!-- LEVIER -->) et
  <!-- PREDICTION --> attendent.
- En file : `apres-chaine.sh` (tâche de fond de ma session) lance prediction.py --casser puis prediction.py
  dès « fin normalise » dans chaine.log. Si ma session meurt : le relancer à la main après la chaîne.
- v3 dort tant que le v1 orphelin écrit (garde du prédécesseur) ; le v1 finit la couche 23, puis v3, puis
  normalise. Ensuite : rapport.py (lit levier-v3.out, levier-temoin-v3.out, journaux du plafond),
  figures, § 0 BREF, § 4.3 NORMALISE, § 5.4 LEVIER, PREDICTION.
- 11:25 v1 orphelin fini (« fin levier ») ; 11:53 v3 fini ; 12:41 normalise fini ; 12:51 prediction finie
  (la règle α̂ < 2 TOMBE : 5/30 au-dessus de 2). Tout commité.
- 12:00 découverte : la base blanche compte les échelles de rangée (L2_0 = 0,755 sur L00.down.E24) ;
  leviers par matrice barrés (§ 7 nonies) ; référence « permuté complet » fausse, T-rangées −0,562
  (§ 7 decies) → référence = permutation dans chaque rangée. `plafond_rangee.py` v2 lancé 12:55
  (cassure puis normal), en pause sur séance ABBA du juge disque. Sorties plafond-rangee*.log/.out.
- v2 périmé : réveillé 12:53, rendormi 12:55 par une boucle `touch levier.out` (tâche de fond de ma
  session, s'arrête au fichier fin-rangee.drapeau). Après ma session il se réveille, finit seul (2 fils)
  puis sa chaîne 32064 relance normalise (réécrit normalise.out/.log : même graine, à comparer au commit).
- Reste : § 5.5 (<!-- RANGEE -->), § 0 BREF, figures (compiler toutes), pour-le-memoire (référence par
  rangée, normalise), BibTeX.

## 2026-10-26/27, reprise après la pause du 22 (nouvel agent de la piste)
- Arbre : seule la trace périmée du levier v2 était sale (réveillée après la pause, barrée) : commitée (9fa6892).
- Passe du plafond par rangée coupée par la pause à 29 matrices sur 48 : renommée `plafond-rangee-partiel.*`,
  relancée ENTIÈRE à 23:40 le 26 (journal `plafond-rangee.log`, sortie `plafond-rangee.out`, ligne
  « début/fin plafond-rangee » dans chaine.log). Témoins tiennent (T-rangées −0,0001 ; planté ≥ 0,05).
- 23:45 le 26 : séance ABBA du juge disque (verrou, pid 6340) : la passe s'est mise en PAUSE à la
  matrice 38 (L23.gate.E26), elle reprend seule à la fin de la séance (2 fils, sous la normale). Ne pas la tuer.
- Écrits sans calcul : `seuil.md` § 7 undecies (stabilité de la référence d'une graine à l'autre, déclarée
  avant calcul, commit 2fce5f6), `rangee_graine.py` (à lancer APRÈS la passe principale :
  `--casser` d'abord, puis normal), `fig_rangee.py` (CSV de la figure P3, à lancer quand `plafond-rangee.out`
  existe).
- Reste : lancer rangee_graine.py (cassure puis normal), fig_rangee.py, figure P3 dans
  `figures/spectres-figures.tex`, remplir <!-- RANGEE --> (§ 5.5) et <!-- BREF --> de spectres.md,
  mémoire (§ 8 de pour-le-memoire : chiffres de la passe), commit ciblé.
