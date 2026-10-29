# Reprise : duplication de gènes (parenté des experts)

- 2026-10-16 : sujet ouvert. Lus : SOCLE, idée § 5 ter, 03 § 1.6, 07 § 4.2, modele.rs de trc-reference.
- venv : ~\dev\lectures\venvs\genome-duplication (numpy 2.5.4, scipy 1.18.1).
- Plan : (1) parenté brute et à permutation près des neurones (gate/up en rangées, down en colonnes),
  intra-couche et couches voisines ; (2) coût conditionnel sans perte sur les codes MXFP4 (gate, up :
  la permutation garde les blocs) ; (3) mutation avec perte contre codage indépendant, même quantifieur ;
  (4) arbre le plus économe ; (5) erreur de sortie sur entrées réelles (capture de hn).
- Outils : outils/genome/duplication/ ; données : mesures/genome/duplication/.
- Fait (commits 40d4b5c, cca766d, 0d0f972) : seuils déclarés (mesures/genome/duplication/00-seuils-declares.md,
  addendum D2b/D2c, coûts corrigés) ; témoins plantés tiennent (écran ρ₀ 0,9 ; paire 0,5 → 0,2077 b, perm 100 %).
- Premiers chiffres : paire apparié couche 12 : cos gate 0,04 / up 0,034 / down 0,107 contre hasard 0,04 ;
  score 0,005 b/poids (hasard 0,0016). Spectre famille c12 : KLT − diag 0,07 à 0,12 b (témoin 0,03 à 0,05),
  base non comptée. Essai (8,0) : D1 gain 0,0076 (gate) 0,0010 (up) ; ECSQ pas commun : poids ok mais
  sortie 29 % contre base 8,3 % ; mutation tronquée : sortie 120 %.
- Entrées réelles : capture de l'éclaireur, ~/dev/essais/troncons/genome/eclaireur/calib
  (h-Lll.f32 n×2880 f32, routage-Lll.bin 4 o + 4 f32) ; empreintes dans chaque journal mutation-c*.json.
- En cours : lancer_echantillon.sh 0 8 16 23 → mesures/genome/duplication/mutation-cL.{json,log}.
- Ensuite : paralogues.py (substitution fonctionnelle sur défaut de cache) sur 0, 8, 16, 23 (--jetons 128,
  mémoire !) ; paires_arbre.py couche 12 entière + 12→13 ; écran réduit (0,4,8,12,16,20,23, 480 rangées) ;
  synthèse CSV ; note genome/duplication-pour-le-memoire.md ; bib (arXiv 503 : réessayer, sources/ ).
- 2026-10-17 02 h 15 : échantillon couches 0, 8, 16 commité ; couche 23 en cours (lancer_echantillon.sh,
  ≈ 1 h 30 sous charge). Paralogues 0, 8, 16, 23 commités (substituer ≤ retirer, jamais mieux).
  Synthèse : synthese.py (témoin --casser tient). Bib : memoire/sources/genome-duplication.bib.
- Reste : couche 23 → synthese.py → csv/ ; paires_arbre.py --couche 12 (arbre entier, 496 paires) ;
  note genome/duplication.md (livrable) + genome/duplication-pour-le-memoire.md ; figures (script).
- Lien : le sujet predictif-elagage tient l'ECSQ par classe κ (2,37 b à erreur de sortie de la base) et la
  sensibilité hebbienne : ne pas refaire ; la parenté n'y ajoute que D2b/D2c ≈ 10⁻³ bit.
- 2026-10-17 05 h 50 : échantillon fini et commité ; verdicts.json (D1 21/48, D2 −0,49, D2b 24/48 → 2,6429 au
  mieux, O base 6,4 % / mutation 8,6 % / tronquée 91 %) ; livrable genome/duplication.md (reste § 5 arbre :
  TEXTE_ARBRE) ; note mémoire genome/duplication-pour-le-memoire.md ; bib.
- En cours : paires_arbre.py --couche 23 (496 paires) → arbre-c23.json. Puis : confirmation 120b
  (paires_arbre --modele 120b, 6 experts), remplir § 5, commit final, valeur de retour.
- 2026-10-17 07 h 40 : TERMINÉ. Arbre c23 (0,0212 b gaussien, ≈ 0,004 réel), meilleure arête (23,17)←(23,31)
  0,017 b sans perte, 120b confirmé (c18, 8 experts), figure phylogénie (MDS, fidélité dite). Livrable
  genome/duplication.md complet ; dérivations ; note mémoire ; bib. Verdict : ne bat pas la frontière.
- Si reprise : rien d'obligatoire. Options : D1/D2b sur 120b ; KL via alterer_expert (sans enjeu) ;
  écran des 24 couches (--rangees 480) ; figures TikZ finales (rédacteur).
