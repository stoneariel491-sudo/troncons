# Note de reprise : les mineurs N1 à N8 et H2 du contre-jugement de l'article court

Rôle : faire les mineurs N1 à N8 de `JUGEMENT-article-contre.md` (commit 1705c62), dans les deux langues à la fois,
puis H2 (la section « Relevés » de `juge/refaire_chiffres.py`). 2026-10-29. Branche `main`. Style télégraphique.
Aucune mesure neuve : texte, bibliographie, outil du juge. Chaque chiffre neuf est tiré d'un fichier commité, nommé
ci-dessous, et refait par `refaire_chiffres.py` (section 12).

## État

- **Fait** : N1 à N8 dans les deux langues ; H2. Contrôle du diff phrase par phrase fait (§ « Contrôle »).
- **Construit** : `bash memoire/article/construire-article.sh tout`, code 0. **EN 14 pages, FR 15 pages** (avant :
  14 et 14 ; en français, quatre entrées de bibliographie passent à la page 15). 0 erreur, 0 renvoi ou citation
  indéfini, 0 « Rerun », 0 boîte trop pleine ou creuse, BibTeX `warning$ -- 0`. Paquets arXiv refaits et compilés
  seuls par le script (pdflatex trois fois, sans BibTeX) : 14 et 15 pages, égales à l'article.
- **Vérifié** (journal : `memoire/article/correcteur/verifications-mineurs.txt`) :
  - `refaire_chiffres.py` : **164 chiffres sur 164 tiennent** (156 + 8 : la différence des lignes de flux 0,12563,
    les deux seuils 1,769 et 1,227 sortis des relevés, et 5 chiffres neufs de N2 à N4) ; **15 relevés sur 15
    corrigés** ; code 0. `--casser` : code 1. Témoin des relevés : le même outil pointé sur les `.tex` de 1705c62
    (avant ces mineurs) rend 159/164 et 6/15, code 1.
  - `parite_nombres.py` : 293 nombres distincts, 944 occurrences de part et d'autre, parité tient ; `--casser` tombe.
  - `parite_structure.py` : structure 58/58, citations 34/34 dans le même ordre (BitMoD en plus), provenance 32/32,
    figures 5/5 ; nombres dans l'ordre 890/890 avec les quatre mêmes écarts d'ordre des mots qu'avant (« 4060 »,
    « 0.00308 », « 1.0 », « 3.5 ») : multiensemble égal.
  - `longueur_resume.py` : EN 1 834 / 1 772 ; FR 1 900 / 1 830 ; limite 1 920 (le français n'a plus que 20 caractères
    de marge en LaTeX brut, 90 en texte approché).
  - `chemins_cites.py` : 4 « absents » dans chaque langue, les mêmes qu'avant ; le chemin neuf
    (`mesures/moteur/epreuve-J1/csv/s1-2026-10-16-passes.csv`) existe.

## Les mineurs

- **N1, BitMoD.** Lu moi-même le 2026-10-29 : page arXiv (https://arxiv.org/abs/2411.11745 : titre « BitMoD:
  Bit-serial Mixture-of-Datatype LLM Acceleration » ; Chen, AbouElhamayed, Dai, Wang, Andronic, Constantinides,
  Abdelfattah ; v1 2024-11-18, v2 2025-04-26 ; commentaire « HPCA 2025 ») et texte HTML v2 (§ II-C : réaffecter un
  zéro redondant à une autre valeur spéciale ; § III-A : variantes FP3 et FP4, le zéro redondant remplacé par une
  valeur prédéfinie ; poids FP16 quantifiés, donc avec perte ; aucune fréquence de −0 mesurée dans un modèle publié).
  Texte : « BitMoD replaces the redundant zero of FP3 and FP4 variants by a special value », avant NxFP ; « Both » →
  « All three », « neither » → « none » ; FR « BitMoD remplace… », « deux formats » → « trois formats ». Je n'écris
  pas « first » / « le premier » (proposé par le contre-jugement) : je n'ai pas de quoi dire qu'il est le premier.
  Entrée `chen2024bitmod` au `.bib` (année 2024 de la v1, versions et HPCA 2025 dans `howpublished`). La phrase de
  nouveauté (« We know of no work that measures… ») reste vraie : BitMoD réaffecte, avec perte, ne mesure rien d'un
  modèle publié.
- **N2, le plancher.** « troncons sits at the floor of the file format » → « troncons's KL is −0.00048, at the
  resolution floor of the logit files themselves (.kld, log q on 16 bits) ». Sources : Tome II, 07-resultats.tex
  (format `.kld`, log q sur 16 bits, KL d'un calcul exact négative, de l'ordre de −4,8 × 10⁻⁴ ; tableau C4, KV f32
  −0,00048) ; refait depuis `mesures/moteur/O/corrections/journaux/verdicts-kv-2026-10-16.json`
  (`f0_120b.comparer_kld.f32.kl_moyenne` = −0,000477, n = 255).
- **N3, la mémoire engagée.** Au § 3.1, à côté de la pointe : « troncons's private committed memory, 6.93 GB
  (llama.cpp: 6.81 GB), is, as Volume II reads it (published there, not judged), of the order of its GPU allocations
  and pinned memory, reserved against the commit limit of Windows without occupying physical RAM ». Fichier source :
  `mesures/moteur/epreuve-J1/csv/s1-2026-10-16-passes.csv` (colonne `pointe_engagee_os_mo`, octets / 10⁶, lue par
  le système sur le descripteur après la sortie, `pilote_epreuve.py` l. 126 : `PeakPagefileUsage`) : T120
  6 933,77, 6 931,30, 6 934,56 → 6,93 Go ; L120 (llama.cpp « fit -t 6 », la configuration publiée de
  `mesures/gpt-oss.md` § 3.2, `pilote_epreuve.py` l. 53) 6 809,78 et 6 809,92 → 6,81 Go. Tome II : 07-resultats.tex
  (« What the machine loses, and committed memory ») et 08-epreuve.tex (6,93 Go, constat m3, publié non jugé ; la
  figure de la séance trace aussi l'engagée de llama.cpp, depuis `memoire/figures/tome2/donnees/res-epreuve-seance.csv`).
  Le chiffre de llama.cpp est ajouté par moi (même fichier) : sans lui, un lecteur croirait l'engagée propre à
  troncons.
- **N4, llama.cpp sur la carte.** Même fichier, colonne `vram_pointe_mio` (nvidia-smi, `memory.used` de la carte
  entière, toutes les 250 ms) : T120 6 574 Mio aux trois passes ; L120 6 026 et 6 027 Mio. Texte : « nvidia-smi reads
  the whole card, other processes included, at a peak of 6 574 MiB under troncons and of 6 026 and 6 027 MiB under
  llama.cpp in that configuration (independent trial of Volume II, …), so that the large gap between the two engines
  lies in the host working set ». J'ai d'abord écrit « display included » : barré au contrôle (l'écran passe par
  l'Intel UHD, SOCLE ; le compteur est celui de la carte entière, sans dire à qui). Écarté : le 6 041 Mio de
  `mesures/base-gpt-oss/120b/resume.csv` (même configuration, autre jour, autre repos de la carte) : il n'aurait pas
  eu de chiffre de troncons au même instrument le même jour.
- **N5, tableau 2.** « their difference, from the unrounded values, is 0.12563 bit » / « leur différence, depuis
  les valeurs non arrondies, vaut 0,12563 bit ».
- **N6, ce que fait le signe.** Résumé : « and no computation of the engines considered depends on it » / « et aucun
  calcul des moteurs considérés n'en dépend » ; conclusion : « a fair coin on which no computation of the engines
  considered depends » / « une pièce juste dont aucun calcul des moteurs considérés ne dépend ». Les deux autres
  « nothing reads » (introduction ; « La pièce », § 3.2) disaient la même chose de trop : « a sign that changes no
  value » / « un signe qui ne change aucune valeur » (vrai par IEEE 754 : −0 = +0).
- **N7, Heilper et Singer.** Relu moi-même leur HTML (https://arxiv.org/html/2508.19263v1) : § 4.4 « The resulting
  streams appeared statistically uniform, with little to no redundancy across tensor blocks » ; § 4.4 évalue MXFP4 et
  NVFP4 **sans nommer le modèle** des valeurs (le contre-jugement écrivait « DeepSeek-R1 en NVFP4 » : seule la
  figure 9, sur les échelles NVFP4, nomme DeepSeek-R1). Je n'écris donc ni modèle ni taille de bloc. Texte :
  « reporting that their streams appear statistically uniform; in gpt-oss-20b, the entropy of the codes is 3.8638
  bits per weight, not 4 (Section 3.2), and our coder conditions them on the scale class » / « leurs flux lui
  paraissant statistiquement uniformes ; dans gpt-oss-20b, l'entropie des codes vaut 3,8638 bits par poids, et non
  4 (…), et notre codeur les conditionne par la classe d'échelle ». 3,8638 est déjà dans l'article
  (`zero-compte-20b.json`, `H_code`). Aucune explication de l'écart n'est avancée : seulement les deux faits.
- **N8, bibliographie.** FR `\NoteTome` : « Versions anglaise et française » (majuscule après le point). Tome I :
  « (Volume~I) » / « (Tome~I) » ajouté à la fin de `\TitreTomeI`.

## H2

`memoire/article/juge/refaire_chiffres.py` : les relevés figés sur l'article d'avant (« about 1.9 MB », « coded
chunks », etc.) sont devenus des contrôles : chaque relevé cherche la correction dans le texte des deux langues (et
l'absence de l'ancienne écriture quand elle est nommée), compte à part (15), et fait sortir en code 1 s'il tombe.
Relevés : les 7 du jugement (M6, M7 ×3 dont N5, M8, M14, M16) et 8 du contre-jugement (N1, N2, N3, N4, N6, N7, N8
×2). Section 12 neuve : les chiffres de N2 à N4 refaits depuis leurs fichiers. Le journal `juge/refaire_chiffres.txt`
est refait par l'outil (il portait la sortie du 2026-10-29 sur l'article d'avant). La docstring dit ce qui a changé.

## Contrôle (relecture du diff phrase par phrase, deux langues)

Pour chaque changement : dit-il plus que sa source ? Corrigé au contrôle :
- « display included » / « affichage compris » → « other processes included » / « autres processus compris ».
- « the gap between the two engines lies in the host working set » → « the **large** gap… » : sur la carte, troncons
  prend ~550 Mio de plus que llama.cpp, et l'engagée est du même ordre ; le seul grand écart est l'hôte.
- L'engagée « of the order of its GPU allocations…, without occupying physical RAM » est la lecture du Tome II, non
  mesurée par nous : « as Volume II reads it (published there, not judged) » / « selon la lecture du Tome II (qui la
  publie sans la juger) ».
- Heilper et Singer : « finding their streams statistically uniform » → « reporting that their streams appear… »
  (leur mot est « appeared ») ; FR « leurs flux lui paraissant… ».
- BitMoD : pas de « first ».
Laissé tel quel, vérifié : « All three are new, lossy formats into which a model is quantised again » (BitMoD part
de poids FP16) ; « none measures how often −0 occurs in a published model » (vrai pour les 100 000 premiers
caractères du HTML de BitMoD ; voir plus bas).

## Ce qui pourrait être faux

- BitMoD et Heilper et Singer ont été lus par un outil qui résume les pages (arXiv abs et HTML), pas dans leur PDF ;
  les 17 000 derniers caractères du HTML de BitMoD n'ont pas été lus (une mesure de la fréquence des −0 pourrait s'y
  trouver ; rien dans les sections II et III ne l'annonce). « HPCA 2025 » vient du champ de commentaire d'arXiv et de
  l'en-tête du papier ; je n'ai pas lu les actes.
- La pointe de la carte (nvidia-smi, carte entière, échantillonnée toutes les 250 ms) n'est pas l'empreinte propre
  d'un moteur ; l'article le dit (« whole card, other processes included »). Les pointes de troncons et de llama.cpp
  viennent de la même séance, mais de passes différentes.
- « 6,93 Go » est l'engagée du 120b dans la séance de l'épreuve ; le Tome II donne aussi 6,92 à 6,97 Go (constat m3,
  toutes séances) : l'article garde la valeur de la séance qu'il cite.
- La page de plus du français (15) : quatre entrées de bibliographie ; MiKTeX, pas le TeX Live d'arXiv.
- Les comptes de `refaire_chiffres.py` changent de sens (156 → 164) : les 8 de plus sont nommés ci-dessus.

## Ce qui reste

- À Stone seul (inchangé) : `\Emplacement`, forme du nom d'auteur, forme bilingue, compte, parrainage, catégorie,
  licence, déclarations d'arXiv.
- Hérité, laissé : le jargon (J1, s2, A-C2) défini tard ; « des juges qui n'ont pas fait le travail » sans dire qui.
- H1 (Tome III, « 540 tables des couches 0, L/2, L−1 ») : à l'orchestrateur ; non touché.
- Un contre-juge relit ces mineurs (SOCLE, « la barre »).

## Fichiers

- Sources : `memoire/article/{en,fr}/troncons-article.tex`, `memoire/article/commun/troncons-article.bib`,
  `memoire/article/juge/refaire_chiffres.py`.
- Construits : `memoire/article/{en,fr}/troncons-article.{pdf,bbl}`, `troncons-figures.pdf` (refaites par le
  script, même source, seul l'identifiant du PDF change), `arxiv-{en,fr}.tar.gz`.
- Journaux : `memoire/article/correcteur/verifications-mineurs.txt`, `memoire/article/juge/refaire_chiffres.txt`.
