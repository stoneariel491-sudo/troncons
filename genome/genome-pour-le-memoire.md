# Le génome des poids (sujet genome) : ce qu'il faut au mémoire

*Pour le rédacteur scientifique. Le document source est `genome/genome.md` ; toutes les dérivations y
sont écrites en entier ; chaque chiffre vient d'un fichier commité sous `mesures/genome/genome/`.*

## Place dans le mémoire

Un chapitre du tome de l'étude biomimétique (ou du Tome II, partie « au-delà du sans-perte ») :
**« Le génome des poids : de la graine au brin lu par codons »**. D'où il part : la frontière F1
(3,8431 bits sans perte ; 2,6441 bits pour la base de B à 4,2920 % d'erreur). Ce qu'il établit : la
graine (SeedLM) ne bat pas la frontière, et le lemme 1 dit pourquoi avant la mesure ; le brin lu par
codons, après rotation de Hadamard et avec répartition des bits entre rangées, la bat sur les 12 tenseurs
**en erreur de poids** (0,20 à 0,60 bit, 0,319 en moyenne) ; mais au même point l'erreur de **sortie**
est plus grande que celle de la base : la fidélité se règle en pondérant le brin par les entrées réelles
(§ 8.2 de genome.md). Ce qui reste : genome.md § 9.

## Dérivations (à porter en entier, avec leurs démonstrations)

| Énoncé | genome.md | Contenu |
|---|---|---|
| Lemme 1 (meilleur de N sous-espaces aléatoires) et corollaire | § 2.2 | ρ ~ Bêta((C−P)/2, P/2) ; E[min ρ] = ∫(1 − F)^N ; asymptote Γ(1 + 1/a)(a B(a,b)/N)^{1/a} |
| Lemme 2 (prédécesseurs dans le treillis à décalage) | § 3.2 | les prédécesseurs de s′ ne dépendent que de u = s′ ≫ kb |
| Proposition 1 (exactitude du Viterbi) | § 3.2 | récurrence C_p(s′) = M_p(s′ ≫ kb) + d_p(s′), principe de Bellman |
| Invariance de l'erreur par la rotation | § 3.3 | ‖W − Ŵ‖_F = ‖(W − Ŵ)Rᵀ‖_F ; W x = (W Rᵀ)(R x) |
| Proposition 2 (Everett) | § 3.4 | le choix lagrangien par rangée est optimal pour le budget qu'il dépense |
| Remplissage inverse et gain de répartition | § 3.4, § 6 | ½ log₂(MA/MG) des variances de rangée à haut débit |
| Lemme 3 (le complément exact ne rend rien gratuitement) | § 7 | R_Y + Σ H(X_i \| Z_i) ≥ H(X) ; la perte = information portée ensemble par les bits du brin |
| Erreur de sortie attendue et pondération | `src/fidelite.rs` (en-tête), genome.md § 8.2 | E‖ΔW x‖² = Σ_c′ h_c′ E[Δw′²], h = diag(R Σ Rᵀ) pour une erreur blanche dans le domaine tourné |
| Comptabilité des bits | § 4 | brin, fenêtre initiale, indice de forme, σ, tables, échelles, alignement |
| Coût de transcription | § 8.4 | opérations par poids contre 214 (et 926) par octet |

## Figures (données commitées, à tracer en pgfplots ; régénérer par `outils/genome/recette/vers_csv.py`)

1. **Le brin sur une gaussienne** contre la borne de Shannon (débit 1 à 4 bits, l = 12 et 16) :
   `csv/gauss-brin.csv` (colonnes forme, l, q, melangeur, lloyd, debit, erreur, borne_shannon).
2. **La graine, mesurée contre la théorie** (lemme 1) : `csv/graine-mesure-theorie.csv`.
3. **Les courbes débit-distorsion par tenseur**, recette (brut, tourne) et point de la base F1 :
   `csv/courbes-tourne-l12.csv`, `csv/courbes-brut-l12.csv` (norme, tenseur, bits, erreur), points de la
   base dans `csv/verdict-par-tenseur.csv`.
4. **Le verdict W par tenseur** (barres : frontière, brut, tourne) : `csv/verdict-par-tenseur.csv`.
5. **Le spectre** réel contre permuté (part d'énergie des r premières directions) : `csv/spectre.csv`.
6. **La fidélité de sortie en fonction du débit**, par expert, uniforme et pondérée, avec l'erreur de
   sortie de la base en trait horizontal : `csv/fidelite.csv` (après la passe `fidelite`).
7. **Schéma TikZ** (à dessiner) : le brin de bits, la fenêtre de 12 bits qui avance de kb, le mélangeur,
   la table de 256 valeurs, la sortie ; en regard, l'ARN, le ribosome, le codon, la table du code
   génétique. Un second schéma : le treillis (4 états, kb = 1) et un chemin de Viterbi.
8. **Chronogramme de la transcription** dans une GEMV (à dessiner) : lecture du brin, mélange, table en
   mémoire partagée, FMA avec l'activation tournée.

## Tableaux

- Verdict W par tenseur (genome.md § 5.2).
- La graine mesurée contre le lemme 1 (§ 2.3).
- Les motifs (§ 8.1).
- La structure (§ 6).
- La fidélité de sortie (§ 8.2) et la KL (§ 8.3) si mesurée.

## Sources

`memoire/sources/genome-genome.bib` (clés `genome-…`) : SeedLM (arXiv 2410.10714v2), QTIP (arXiv
2406.11235v4), Marcellin et Fischer 1990, Fischer, Marcellin et Wang 1991, Mao et Gray 2010, Max 1960,
Shannon 1948 et 1959, Crick et al. 1961, Crick 1968. Toutes consultées le 2026-10-16, métadonnées
vérifiées par l'API arXiv et par Crossref.

## Outils (annexe des outils)

`outils/genome/recette/` (Rust : `genome frontiere | gauss | codons | graines | motifs | sortie |
fidelite | decoder` ; Python : `analyse.py` second chemin du verdict, `graine_theorie.py`,
`structure.py`, `borne_par_tenseur.py`, `vers_csv.py` ; scripts `file.sh`, `chaine.sh`) ;
`outils/genome/recette-kl/` (KL d'une recette substituée, copie de la fourche de l'éclaireur plus la
substitution F32).
