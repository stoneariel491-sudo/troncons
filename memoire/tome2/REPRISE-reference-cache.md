# Reprise : rédacteur « reference-cache » (Tome II)

Rôle : chapitres « La référence exacte et le juge » (05) et « Le cache, l'ordonnanceur et le moteur »
(06), EN et FR. Aucun calcul sur la carte. Aucune question (délégation, marquée).

Fichiers à moi seul :
- `memoire/tome2/{en,fr}/chapitres/05-reference.tex`, `06-cache-moteur.tex` ;
- `memoire/figures/tome2/reference.tex`, `memoire/figures/tome2/cache.tex` ;
- `memoire/figures/tome2/donnees/t2r-*.csv`, `t2o-*.csv`, `t2-verif-reference-cache.json` ;
- `memoire/outils/tome2_reference_cache.py` (données dérivées + 31 chiffres refaits, témoin et
  cassure `--casser`) ;
- `memoire/sources/tome2-reference-cache.bib` (kullback1951, sleator1985) ;
- cette note.

## Conventions (alignées sur REPRISE-chemin-noyaux ; réponse par délégation du 2026-10-16, réversible)
- Étiquettes `t2r-` (référence), `t2o-` (cache, ordonnanceur, moteur) ; chapitres `ch:t2-reference`,
  `ch:t2-cache`. Aucun \cref vers un autre rédacteur.
- Styles TikZ préfixés `ref` / `cch` ; filtre pgfplots `ref garder`.
- Figures chargées par le chapitre lui-même : `\ifdefined\GrapheRefRampe\else\input{…}\fi`.
- Chemins `\Racine`, `\Depot` du préambule commun ; données dérivées sous `\DonneesTomeDeux`
  (= `\Racine/figures/tome2/donnees`, \providecommand).

## Pour le fichier maître du Tome II (à qui le construit)
- `\addbibresource{\Racine/sources/tome2-reference-cache.bib}` (kullback1951, sleator1985) ; les
  chapitres citent aussi moteur-R (openai2025gptossref, openai2025gptoss20bconfig,
  ggml2026llamacppb11515, peng2023yarn, wilson1927, merity2016wikitext, goto2008anatomy), moteur-O
  (higham2002, belady1966, mattson1970, nvidia2026driverstream), commun (cover2006).
- PIÈGE trouvé : `ieee754-2019` (moteur-O.bib) a une note avec « 2^-11 » nu : lualatex s'arrête
  (« Missing $ ») à l'impression de la bibliographie. Je ne le cite pas (Higham à la place). Le lot O
  ou l'orchestrateur doit corriger la note (`$2^{-11}$`) si un autre chapitre le cite.
- Doublons biber : belady1966 (commun, moteur-O, mesures-gpt-oss), wilson1927, merity2016wikitext.
- `memoire/outils/tome2_reference_cache.py` à appeler par la construction (il s'arrête s'il trouve
  un écart entre chiffre refait et chiffre publié).

## Journal
- 2026-10-16 : lu SOCLE, ARCHITECTURE en entier, R-pour-le-memoire, O-pour-le-memoire (I, II, III),
  gpt-oss-pour-le-memoire, epreuve-J1-pour-le-memoire, epreuve-J1.md, gpt-oss.md § 0-9, REPRISE-R,
  REPRISE-O (O1 à J1+), code trc-cache, trc-juge (kld, stats), trc-reference (ops, poids),
  trc-ordo (pas).
- Script de données : 31 chiffres refaits, 0 écart ; cassure tombe. Écart d'arrondi dit : KL des
  imitations publiée 0,029, refaite 0,02905 (tolérance d'une demi-unité du chiffre publié).
- Correction portée (barrée dans 05) : « KL f32 ≈ 5e-11 » du lot O supposait le régime quadratique ;
  avec les bascules (linéaires en u, théorème des deux régimes) la borne est ≈ 4e-7 ; conclusion
  inchangée (sous le pas du format).
- Figures de 05 faites et vues (essai `memoire/essai/essai-t2r-{fr,en}.tex`, script
  `scratchpad/essai-t2r.sh` ; le scratchpad est partagé avec d'autres agents : noms uniques).
- 05 FR écrit, essai 22 p., 0 référence manquante.
- PIÈGE de l'outil Bash : les antislashs des heredocs et de sed sont mangés (\t devient tabulation) :
  tout texte LaTeX par l'outil d'écriture/édition.

- 05 EN écrit ; paire 05 commitée (0ac3ec0). Essai EN 22 p., 0 référence manquante. PIÈGE : le
  harnais EN fait par sed n'avait pas `\anglaistrue` (antislash mangé) : réécrit par l'outil d'écriture.
- Figures de 06 (cache.tex) faites et vues ; 06 FR écrit (essai 21 p., 0 manquante), commité en
  travail en cours (7f0e12e) ; 06 EN écrit.
- Étiquette pgfplots : pas de virgule dans un CSV lu par `yticklabels from table` (guillemets non
  compris) ; « -- » d'une option s'écrit `-\/-` dans le CSV (sinon tiret).
- Ajout de théorie (sources primaires) : Belady optimal (preuve par échange en trois phases),
  propriété de pile, LRU N-compétitif (Sleator-Tarjan, preuve par phases), pire cas cyclique = la
  falaise ; KL = fonction génératrice des cumulants (exacte) ; théorème des deux régimes (u² sans
  bascule, u avec bascules), ordre de grandeur vérifié (f_m(0) ≈ 8,1 à 8,8 ; E|δ| ≈ 5e-3).
- Bilan du préchargement : le premier ordre prédit ≈ −19 %, mesuré −11 % (dit dans 06).

- 06 EN : essai 21 p., 0 manquante. Guillemets ASCII de la prose anglaise remplacés par \enquote
  (script jetable, hors listings et \texttt). Paire 06 commitée.
- Correction de date dans 05 : les passes R0/R1 sur la carte (19 h 59 – 20 h 20) ≠ passes de la
  référence (15 h 35 – 17 h 35).

## État : les deux chapitres sont écrits, EN et FR, commités.
Restes possibles : relecture par un juge ; si le maître du Tome II n'ajoute pas
tome2-reference-cache.bib, kullback1951 et sleator1985 seront manquants (construire.sh tombera).
