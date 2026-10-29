# P3, routage conditionné par le cache, borné par la marge : seuils et témoins déclarés avant toute lecture de données

Écrit le 2026-10-27 (vers 00 h 55), rôle « expérimentateur P3 ». Commité avant d'ouvrir un seul octet de
`h-Lll.f32`, de `routage-Lll.bin` ou d'un poids de routeur.

Ce que j'ai lu pour fixer ceci, et rien d'autre : `genome/mimetisme/tri.md` (P3), `mesures/mimetisme/tri/00-seuils-declares.md`,
`mesures/mimetisme/humain/e7-marge-20b.json`, `mesures/mimetisme/mathematiques/m3_marges_20b.json`,
`outils/mimetisme/humain/e7_marge.py`, `outils/mimetisme/ingenierie/cache2.py` (`lru1`), `moteur/crates/trc-cache/src/lib.rs`
(`demander`), `outils/genome/eclaireur/capture/src/modele.rs` (`apres_attention`, `capturer`), `genome/05-synthese.md` § 2.2,
`mesures/moteur/R/r1_reference.py` (en-tête), et la source primaire : Skliar, van Rozendaal, Lepert, Boinovski, van Baalen, Nagel,
Whatmough, Ehteshami Bejnordi, « Mixture of Cache-Conditional Experts for Efficient Mobile Device Inference », arXiv 2412.00099 v2
(24 juin 2025), TMLR 2025, https://arxiv.org/html/2412.00099v2, consultée le 2026-10-27.

## 0. Ce que la source dit, et ce que j'en reprends

Biais additif sur les logits du routeur, avant le classement top-k : z' = z + λ·Δavg·m, m = masque binaire des experts en cache,
Δavg = étendue moyenne (max − min) des logits de la couche. z' ne sert qu'à choisir les experts ; les poids de mélange restent
calculés sur les logits non modifiés. Sur Qwen1.5-MoE, DeepSeek-V2-Lite, Phi-3.5-MoE et Mixtral, à λ = 0,5 et cache = N/2,
le taux de défaut passe de 35 % à 16 %, 28 % à 7 %, 22 % à 9 %, 40 % à 21 %, pour +0,1 % à +2,9 % de perplexité (chiffres de l'article,
non reproduits ici). Nos conditions sont plus dures (32 experts, 4 actifs, cache de 19 % et 31 %, non de 50 %).
Reprise : sélection biaisée, poids non biaisés (c'est aussi ce que fait `routage_impose` du moteur de référence : softmax sur les
logits d'origine des quatre choisis). Écart assumé : l'article normalise le biais par Δavg ; ici β est en unités brutes de logit
(grille du tri), et je rapporte l'équivalent λ = β/Δavg, Δavg mesuré par couche.

## 1. Deux étages

**Étage A, en boucle ouverte, sans passe du modèle.** Les entrées du routeur sont déjà capturées (`h-Lll.f32` : sortie de la norme
d'après l'attention, 5 110 positions, 24 couches, d = 2 880, trajectoire du modèle exact) ; le routeur est une couche linéaire
32 × 2 880 plus un biais, F32 dans le GGUF (quelques centaines de Ko par couche). Je recalcule les 32 logits de chaque cellule,
je biaise, je rejoue le cache. Cela mesure : les défauts évités, la part de cellules qui changent. Cela ne mesure pas l'effet
d'une bascule voulue sur les couches suivantes ni sur la KL : la trajectoire reste celle du modèle exact (boucle ouverte).

**Étage B, en boucle fermée : la KL excédentaire.** Expérience B du lot R : les ensembles biaisés de l'étage A écrits au format
du journal de routage (`u32 couches, u32 positions, puis par couche et position 4 × u8 experts + f32`) et imposés à la
référence f64 (`--imposer-routage`), KL contre `ref-openai`. Quatre passes de ~2 168 s, RAM de pointe inconnue, disque lourd
(9,7 Go d'experts lus par passe) : **je ne le lance pas** (verrou de la carte tenu par une séance de vitesse ABBA, et RAM non bornée à 2 Go).
Je rends le cahier : fichiers d'entrée prêts, commande, arrêt séquentiel. Le verdict final de P3 (« tient ») exige donc l'étage B.

## 2. Définitions de la mesure (étage A)

- Cellule = (position t, couche l), 5 110 × 24 = 122 640. Ordre d'accès : t croissant, puis l croissant ; dans un groupe, rang
  décroissant de logit non biaisé. La mémoire du cache traverse les 10 fenêtres (comme E7).
- Cache : global sur les 24 × 32 = 768 experts, LRU, règle de groupe de `trc-cache` (les k experts du groupe sont épinglés pendant
  le groupe, la victime est le moins récent non épinglé). Budgets : N = round(0,19 × 768) = 146 et N = round(0,31 × 768) = 238.
- Résidents au moment de la décision de (t, l) = contenu du cache juste avant ce groupe (causal : dépend des ensembles
  biaisés précédents, pas de l'avenir).
- Variante V1 « tous résidents » : top-4 de z + β·1[résident] sur les 32 experts. Variante V2 « 4e/5e seul » : les trois premiers
  logits restent ; le 4e est remplacé par le 5e si z5 + β·r5 > z4 + β·r4. Les poids restent le softmax des quatre choisis sur z non biaisé.
- Grille β officielle (tri) : {0 ; 0,01 ; 0,03 ; 0,1 ; 0,3}. Ajouts déclarés pour la forme de la courbe : {1 ; 3}. Pour les témoins : {−0,1 ; −0,3}.
- Mesures par (variante, budget, β) : défauts (échecs du cache, sur 490 560 accès), variation relative contre β = 0, part des
  cellules dont l'ensemble change, nombre moyen d'experts changés par cellule changée, part des cellules où l'expert de plus haut logit reste
  choisi, et « KL a priori » (ci-dessous).
- **KL a priori (pas une mesure)** : KL_prior(β) = 0,309 × (part de cellules dont l'ensemble change). Constante tirée de 05 § 2.2 :
  (0,0145 − 0,00168)/(5 087/122 640) = 0,309, c'est-à-dire la KL retirée par l'imposition du routage divisée par la part de cellules
  qui basculaient entre deux moteurs presque exacts [calc. sur mes.]. Hypothèses : régime des bascules à marge faible, coût par
  bascule indépendant de la marge, une cellule changée = une bascule. Elle sert à décider si l'étage B vaut ses 2,5 h ; elle ne remplace pas la KL.

## 3. Seuils

L'étage B reste celui du tri : succès si ∃ β avec ≥ 10 % de défauts en moins pour une KL excédentaire ≤ 0,038 (= 10 × 0,13/34) et
premier choix de la sortie ≥ 95 % ; mort si au β à −10 % de défauts la KL dépasse 0,07. Lecture des deux budgets : « −10 % » doit tenir
aux deux (146 et 238), sinon dit « partiel ».

Verdicts possibles de cette passe, fixés d'avance :
- **TOMBE (ferme, sans KL)** : aucun β de la grille (officielle + ajouts) ne retire ≥ 5 % des défauts au budget 146 en V1. Le levier n'a pas
  d'amplitude sur ce modèle, quel que soit son prix.
- **OUVERT, étage B justifié** : ∃ β avec ≥ 10 % de défauts en moins aux deux budgets ET KL_prior ≤ 0,07 à ce β (le facteur 2 sur 0,038 absorbe
  l'imprécision d'une constante tirée d'un autre régime).
- **OUVERT, défavorable** : ≥ 10 % de défauts évités seulement avec KL_prior > 0,07, ou seulement à un budget.
- **TIENT** : impossible sans l'étage B.

## 4. Témoins (chacun avec sa cassure, qui doit pouvoir tomber)

- W1 reproduction : le recalcul (h, poids F32, biais) redonne les 4 experts de `routage-Lll.bin` sur ≥ 99,9 % des 122 640 cellules, tout
  désaccord ayant une marge |z4 − z5| < 1e-4 ; poids softmax égaux à 1e-4 près. Cassure : recalcul sans le biais du routeur : l'accord doit tomber sous 99 %.
- W2 β = 0 : ensembles égaux à ceux de W1 sur toutes les cellules, défauts égaux (entiers) à ceux du rejeu des ensembles de `routage-Lll.bin`. Cassure : β = 0,3 doit changer des cellules (W2 échoue).
- W3 signe : défauts(β = −0,3) > défauts(0) aux deux budgets. Cassure : masque inversé (on favorise les absents) avec β = +0,3 doit faire monter les défauts.
- W4 borne E7 : en V2 avec β = τ, défauts évités ≤ 1,5 × (nombre de défauts de rang 4 avec marge < τ, recompté ici sous LRU) ; les chiffres publiés de E7
  (3,1 % à τ = 0,01 ; 8,2 % à τ = 0,03, LFU de demi-vie 8, N = 154, 5e supposé résident) sont donnés en regard, avec l'écart de politique dit. Le facteur 1,5 est une tolérance de
  dérive dynamique (un défaut évité change le cache ensuite) : **non dérivée**, signalée ; le rapport est publié quel qu'il soit.
- W5 second chemin : les ensembles biaisés rejoués par `cache2.lru1` (L = 24, E = 32) donnent exactement les mêmes nombres de défauts, ligne par ligne.
  Cassure : un ensemble permuté au hasard dans un groupe de 1 000 cellules doit changer le compte (sinon le rejeu est aveugle).
- W6 causalité : calculer les ensembles sur les 2 555 premières positions seules donne les mêmes ensembles que sur les 5 110 pour ces positions. Cassure : biais calculé avec le cache d'après le groupe (fuite d'un pas) doit être détecté.

## 5. Contraintes tenues

Pas de carte graphique ; au plus 2 fils (OMP/OPENBLAS/MKL = 2) ; priorité normale ; RAM visée < 1 Go (une couche de h à la fois en memmap, 59 Mo,
et 24 × 5 110 × 32 logits en f64 = 31 Mo) ; aucun téléchargement ; `git add` ciblé. **Verrou** : `~/dev/verrou-carte.txt` existe (séance de vitesse ABBA p7, 00 h 45) et
elle surveille la lecture des autres processus : je ne lis pas les 1,4 Go de `h-Lll.f32` tant qu'il est là ; le pilote attend sa disparition (ou ses 2 h, règle du dépôt).
