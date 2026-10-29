# Reprise : le génome des poids (recette graine + coefficients, motifs, lecture par codons)

- 2026-10-16 : sujet ouvert. Lus : SOCLE, idée § 5 ter, 03 § 1.6 et § 5, 07 § 4.2, ARCHITECTURE § 3, trc-reference (modele.rs).
- Venv : ~/dev/lectures/venvs/genome-genome (numpy, scipy).
- Fichiers à moi : genome/REPRISE-genome.md, genome/genome.md, genome/genome-pour-le-memoire.md,
  outils/genome/**, mesures/genome/genome/**, memoire/sources/genome-genome.bib.
- Carte graphique : non (consigne muette) ; processeur seul.
- Plan : (1) échantillon des 12 tenseurs de F1, frontière refaite dessus (témoin) ; (2) G1 graine+coefficients
  (LFSR, écrit de zéro) ; (3) G2 motifs partagés (dictionnaire, combinaisons) ; (4) G3 lecture par codons
  glissants (treillis, code génétique haché) ; (5) sortie d'une couche d'experts sur entrées réelles ;
  (6) KL si possible.
- Outil : outils/genome/recette (Rust, hors espace moteur/, dépend de trc-reference par chemin). Cible
  ~/dev/cibles/troncons-genome (passes longues) et troncons-genome-dev (constructions
  pendant qu'une passe tourne : l'exe est verrouillé). `.cargo/config.toml` : target-cpu=native.
- Fait : S0 frontière (tient 5,8e-15, cassure tombe) ; T1 gaussien (0,0731, cassure 0,996) ; balayage
  gaussien (l 8..16, formes) ; seuils déclarés commités (mesures/genome/genome/00-seuils-declares.md).
- Rodage couche 0 : gains 0,15 à 0,57 bit (brut), 0,21 à 0,58 (tourne) à erreur égale.
- EN COURS : passe complète codons brut puis tourne, l = 12, pas 4 (≈ 30 min chacune) →
  mesures/genome/genome/codons-{brut,tourne}-l12.{json,log} + csv/…-rangees.csv.
- Écrit, pas encore lancé : `sortie` (erreur de sortie des experts sur entrées réelles = captures de
  l'éclaireur, ~/dev/essais/troncons/genome/eclaireur/{calib,eval} : h-Lll.f32 n×2880 f32,
  routage-Lll.bin 4 o d'experts + 4 f32) ; `motifs` (RVQ partagé, témoin Lloyd-Max 0,1175 tient) ;
  `graines` (SeedLM écrit de zéro).
- RÉSULTAT W (tourne, l = 12) : 12/12 tenseurs gagnent, 0,20 à 0,60 bit (moyenne 0,319) ; brut : 11/12
  (blk.8.ffn_down tombe : poids aberrants, 6,5 % même à 3 bits). Verdicts second chemin commités.
- EN COURS : file.sh (graines SeedLM 10 configs, puis motifs 3 configs) ; ensuite `sortie` tourne.
- Outil KL prêt (outils/genome/recette-kl, cible troncons-genome-kl) : substitution Lll-Eee.f32w ;
  .kld de référence : ~/dev/essais/troncons/lot-R/r1/ref-openai-20b.kld.
- 23 h 50 : graines (SeedLM) en cours via file.sh (32 rangées/tenseur, expert 0 ; ≈ 6 min par config) puis
  motifs ; ENSUITE chaine.sh (lancée, attend « file-finie ») : sortie tourne 16 experts (écrit les .f32w
  sous ~/dev/essais/troncons/genome/genome/kl-sub/{base,recette,recette-relatif}), témoin
  fourche vide, 3 passes KL (6 fenêtres), juge comparer. Les deux scripts sautent ce qui est déjà fait.
- Trouvé : la répartition par énergie se laisse tromper par la mesure d'erreur cumulée (une forme « zéro »
  ferait 0,36 bit global) → la forme zéro N'EST PAS retenue ; la sortie (O) et la KL jugent la répartition.
- genome/genome.md : brouillon commité ; à compléter §§ 2.3, 5.4, 6, 8, 9, 10, 11 et note pour le mémoire.
- 2026-10-17 ~1 h : O (au point W) TOMBE sur couche 0 expert 0 (sortie 7,63 % contre 6,77 %) ; passe
  sortie arrêtée ; protocole F déclaré ; `fidelite` en cours (≈ 56 min par expert sous la charge des
  autres équipes ; 8 experts : 0 et 16 × couches 0, 8, 16, 23 ; journal mesures/genome/genome/fidelite.log,
  JSON à la fin ; écrit les .f32w pondérés à 2,64 b sous essais/…/kl-sub/recette-ponderee-264).
  Expert 0 couche 0 : à 2,64 b, sortie 5,25 % (uniforme) / 5,18 % (pondérée) contre 6,77 % base ;
  erreur de sortie égale à ≈ 2,40 b. La pondération diag(RΣRᵀ) n'apporte presque rien.
- ENSUITE : KL (base contre recette pondérée 2,64) sur les 8 experts : adapter chaine.sh (dossier
  recette-ponderee-264 ; la base .f32w n'est écrite que par `sortie` : écrire la base aussi, ou .sym).
- Puis : decoder (banc ABBA), § 8.2/8.3/9/en bref du document, vers_csv (fidelite.csv), note mémoire.
- ~3 h 30 : F partiel : couche 0 gagne (≈ 2,39 b à sortie égale ; −23 % d'erreur de sortie à 2,64 b) ;
  couche 8 perd en uniforme (E0 8,80 % / E16 8,93 % contre 8,30 / 7,45), pondérée gagne E0 (7,91 %),
  perd E16 (9,41 %) ; couche 16 E0 uniforme perd (6,02 contre 5,72). Exceptions 0,1 % : rien (8,98 %).
- EN COURS (3 passes) : fidelite (tourne, 8 experts) → puis kl.sh (attend « fini ») ;
  fidelite-exceptions (couche 8) ; fidelite-brut (--norme brut, couches 8 et 16, experts 0 et 16,
  pondération diag(Σ) sans rotation). Exe : cibles troncons-genome-dev / -x / -y (verrouillés pendant).
- ~5 h 30 : F arrêtée (tombe, acquis) ; brute arrêtée ; diagnostic colonnes massives commité ;
  S* (tourne + pondérée + exceptions 0,1 %) en cours seule : fidelite-sstar.log (≈ 30-50 min/expert) ;
  à la fin, kl.sh part seul (tâche b1ulwq2nh : attend « fini-sstar ») : base-8 puis S*, 3 fenêtres,
  juge comparer. Puis : tableau S* dans genome.md § 8.2, § 8.3 KL, en bref, verdict final, note mémoire,
  vers_csv (ajouter fidelite-sstar).
