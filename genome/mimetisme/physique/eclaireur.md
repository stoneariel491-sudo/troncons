# Éclaireur du domaine « physique à toutes les échelles » : sept candidats, dont trois mesurés et fermés

Rôle : éclaireur, flux mimétisme absolu de troncons. Date : 2026-10-26 au 2026-10-27. Seuils déclarés et
commités avant toute lecture : `mesures/mimetisme/physique/00-seuils-declares.md` (commits 59eb5a2 et eee6925).
Outils : `outils/mimetisme/physique/` (simulateur de cache en Rust `noyau-cache`, `e1_e2.py`, `e3.py`).
Journaux : `mesures/mimetisme/physique/{e1,e2,e3}/`.

Étiquettes : **[mes.]** mesuré ici, outil et journal commités ; **[calc.]** calculé ici à partir de mesures ;
**[lu]** source dont j'ai lu le résumé ou la page (la date de consultation est celle de ce document) ;
**[mém.]** de mémoire, non relu : aucun chiffre porteur n'en dépend ; **[hyp.]** hypothèse dite.

---

## 0. En bref

1. **Le domaine physique ne livre qu'une idée à la fois neuve et ouverte** : traiter le choix des symboles de
   la mutation synonyme comme la recherche d'un état fondamental de verre de spin (le problème du vecteur le
   plus proche, CVP), par descente de coordonnées puis recuit ou échange de répliques, au lieu de la seule
   rétroaction d'erreur (qui est l'algorithme de Babai, preuve publiée en 2025). Elle n'est pas mesurée ici
   (le verrou de la carte tient, la séance disque du juge tourne, je n'ai lu aucun fichier modèle). Elle est
   la seule que je classe première.
2. **Trois mécanismes physiques sont mesurés et tombent** : un noyau de mémoire de loi de puissance
   (Omori-Utsu), de relaxation étirée (Kohlrausch) ou à deux temps pour le cache (gain +0,003 à +0,005 contre
   un seuil de +0,015) ; une barrière de nucléation pour l'admission au cache (−0,0012) ; une coupure
   « de Fermi » qui retire les experts d'occupation faible (0,09 % des défauts sont sous 0,05 de poids, seuil
   de fermeture 3 %). Les prédictions écrites avant ont tenu pour E1 et E2, et échoué par le signe pour E3.
3. **Un fait nouveau sur le cache, qui ferme tout un genre de pistes** [mes.] : sur le 120b, avec 323
   emplacements, l'ordre des jetons ne rend que 3,7 points de taux de succès (LFU 0,551 dans l'ordre, 0,514
   avec les jetons mélangés). Le taux est surtout de la popularité. L'écart au Belady (≈ 0,71 contre ≈ 0,55)
   ne se ferme donc ni par la forme du noyau de mémoire ni par l'admission : il demande de l'information sur
   l'avenir (le routage du brouillon, déjà dans le lot B).
4. **Une table que le lot B n'avait pas** [mes.] : les poids de mélange du 120b sont plats (moyennes par
   rang 0,349 ; 0,253 ; 0,211 ; 0,187). Un défaut sur deux ou presque est un poids sous 0,25 (67 % des
   défauts) et ne pèse que 18 % de l'énergie Σg² du tout-rapide. Servir par la base seulement ces défauts
   économise 19,5 % des octets de défaut pour environ deux tiers des perturbations par octet de la version
   non filtrée ; c'est la politique λ du lot B avec ses premiers chiffres, pas une idée neuve.
5. **Les gros noms de la physique sont chiffrés et écartés** : jauge de permutation des neurones
   (3·10⁻⁴ des bits d'un expert), Landauer (10¹⁰ fois sous le coût réel d'un bit lu), holographie et
   superposition (bornées par Shannon, les poids sont du bruit), réseaux de tenseurs (la propriété (a) de
   05 § 2.1).

Aucun message à la session principale : aucune de mes mesures n'a tenu son seuil, et l'idée classée première
n'est pas mesurée. Je ne signale pas une analogie comme une piste.

---

## D'où on part, où on va

**Acquis au départ** (lus dans SOCLE.md, idees/biomimetisme-genome-des-poids.md, genome/05-synthese.md § 1 à 3,
genome/JUGEMENT-construction.md, genome/pistes/tropicale/) : le sans perte est à 3,6843 bits (codon du zéro
et colonne), le mode rapide (mutation synonyme λ = 0) à 2,65 bits bat la frontière en KL sur des fenêtres neuves
(−0,1565 ± 0,0334) ; graine, duplication, hebbien, spectres et loi de puissance, S\*, garde tropicale et garde à
indices multiples sont fermés ; les poids sont du bruit une fois l'échelle connue (propriété (a)), quelques
colonnes géantes portent la structure (b), l'erreur d'expert ne prédit pas la KL (c) ; la KL a une part lisse
et une queue de bascules de routage ; le disque est le goulot (2,82 Go/s), et la vitesse du mode rapide dépend
de l'état physique des fichiers plus que des octets (JUGEMENT § 7).

**Ce que ce document établit** : (i) trois mécanismes physiques du cache et de la lecture, mesurés sur les
traces du 120b et fermés ; (ii) la table des poids de mélange aux défauts ; (iii) sept candidats classés, dont
un seul est neuf et ouvert.

**Ce qui reste** : l'expérience du candidat 1 (au sens de § 2), qui demande la carte libre de la séance disque
du juge ou au moins le retrait du verrou, et la passe KL du candidat 3 sur le moteur.

---

## 1. Ce que j'ai mesuré

Données : les sept traces de routage du 120b (`mesures/localite-gpt-oss/traces-120b/`, 36 couches, 128 experts,
k = 4, quatre genres de lecture de 10 669 jetons au total, une lecture wiki de 708 jetons, deux générations de
256) et leurs poids de mélange. Cache global de 323 emplacements (7,0 %, la VRAM de la base), évincement après
chaque groupe de k experts, jamais un expert du groupe : la règle de `g_lfu` de `outils/gptoss_localite.py`.

### 1.1 Témoins

- **W1** : mon simulateur à noyau exponentiel de demi-vie 8 redonne `g_lfu` de l'instrument existant à
  3·10⁻⁶ près sur cinq traces (code 0,4434 ; dialogue 0,5560 ; prose-en 0,5502 ; prose-fr 0,5993 ; wiki 0,5487).
  Les LRU et Belady du même instrument, à 323 emplacements : LRU 0,356 ; 0,462 ; 0,460 ; 0,510 ; 0,453 ;
  Belady 0,646 ; 0,715 ; 0,713 ; 0,743 ; 0,706 (`e1/W1-temoin.json`). La valeur publiée de LRU poolé sur les
  quatre genres était 0,449 (mesures/gpt-oss.md § 6.2) : cohérente avec la moyenne de mes quatre genres
  (0,447).
- **W2** (cassure) : ordre des jetons mélangé. Le gain de chaque famille sur l'exponentielle tombe à −0,0002,
  −0,0033, +0,0017, tous sous le 0,005 déclaré. Le témoin tombe donc bien quand la localité disparaît.
- **E2** : somme des poids par (jeton, couche) égale à 1 à 10⁻⁴ près.

### 1.2 E1. Noyaux de mémoire physiques pour le cache

Mécanisme : score = somme des accès passés pondérés par un noyau K(Δ), évincement du plus petit score. Le LFU
actuel est K exponentiel. Familles : Omori-Utsu (Δ + c)^−p, loi de décroissance des répliques sismiques
(Utsu 1961 [mém.]) qui est le noyau d'excitation du processus de Hawkes ETAS (Ogata 1988 [mém.] ; synthèse
« Hawkes Models And Their Applications », arXiv 2405.10527 [lu]) ; Kohlrausch exp(−(Δ/τ)^β), relaxation
étirée des verres ; somme de deux exponentielles, spectre de temps de relaxation à deux pics. 45 noyaux ;
les non exponentiels sont approchés par neuf exponentielles (1 à 256 jetons), erreur absolue au plus 0,074
(K(0) = 1), mais jusqu'à 6,5 en relatif dans la queue pour la pire loi de puissance (les lois de puissance
sont donc mal représentées dans leur queue : limite dite).

| Famille (réglage choisi en laissant un genre dehors) | taux poolé, 4 genres | gain sur l'exponentielle | genres gagnés sur 4 | réservées gagnées sur 3 |
|---|---|---|---|---|
| exponentielle (demi-vie 32 le plus souvent) | 0,5513 | — | — | — |
| Omori-Utsu (c = 4, p = 1) | 0,5563 | +0,0051 | 4 | 2 |
| Kohlrausch (β = 0,5, τ = 16) | 0,5541 | +0,0028 | 4 | 2 |
| deux temps (0,8 de τ = 8, 0,2 de τ = 128) | 0,5556 | +0,0044 | 4 | 2 |

Seuil déclaré : +0,015 sur 3 genres au moins et 2 réservées. **Verdict : tombe.** Prédiction écrite : 0 à
+0,008, tenue. Le signe est le même sur les quatre genres, la taille est trop petite : +0,005 de succès
retire 1,1 % des défauts. Sur les traces réservées l'exponentielle gagne la génération wiki (0,506 contre
0,498 à 0,502).

### 1.3 E3. Barrière de nucléation (admission au cache)

Mécanisme : après le calcul d'un groupe, ses experts sont candidats à l'éviction comme les résidents ; un
expert vu une fois n'entre pas s'il vaut moins que le plus faible résident. Comparaison à mémoire de pointe
égale (323 avec admission contre 327 sans). Résultat : 0,5531 contre 0,5543, **−0,0012**, négatif sur 4 genres
et 3 réservées. **Verdict : tombe**, avec une prédiction (+0,003 à +0,02) fausse par le signe. Un chiffre
« 13 % des accès jamais revus » avait été écrit de mémoire dans la déclaration : barré, non mesuré, sans rôle.

### 1.4 E2. Nombres d'occupation (coupure de Fermi)

Les poids de mélange sont un softmax sur quatre niveaux (loi de Boltzmann). Sur les défauts du LFU de demi-vie
8, part des lectures sous un poids ε (pooled, quatre genres) :

| ε | 0,05 | 0,10 | 0,15 | 0,20 | 0,25 |
|---|---|---|---|---|---|
| part des défauts sous ε | 0,09 % | 1,13 % | 7,82 % | 29,56 % | 67,06 % |
| part des accès sous ε | 0,06 % | 0,74 % | 5,54 % | 23,39 % | 59,41 % |

**Verdict : tombe en retrait total** (seuil de fermeture : 3 % sous 0,05 ; mesuré 0,09 %). Les poids sont plats
(moyenne par rang 0,349 ; 0,253 ; 0,211 ; 0,187) : un expert quasi vide n'existe pas dans ce modèle, il n'y a
rien à couper. Les défauts sont un peu plus souvent de faible poids que les accès (×1,4 sous 0,15).

### 1.5 Exploration après verdict, sans seuil : le portillon de poids

Servir par le fichier rapide (taille 0,71 de l'exact : 2,65 contre 3,73 bits [calc. sur 07 et 06]) les seuls
défauts de poids sous θ. Colonnes : octets de défaut économisés ; énergie Σg² perturbée, en part de l'énergie
d'un mode où tout serait rapide ; perturbation par octet économisé rapportée à celle de « tous les défauts en
rapide » (`e2/portillon-de-poids.json`).

| θ | défauts concernés | octets de défaut économisés | énergie Σg² perturbée / tout rapide | par octet économisé, relatif à tous les défauts en rapide |
|---|---|---|---|---|
| 0,15 | 7,8 % | 2,3 % | 0,83 % | 0,25 |
| 0,20 | 29,6 % | 8,6 % | 5,5 % | 0,44 |
| 0,25 | 67,1 % | 19,5 % | 18,3 % | 0,65 |
| tous | 100 % | 29 % | 41,9 % | 1 |

[hyp.] La perturbation par octet suppose que la KL est proportionnelle à l'énergie Σg² (réponse lisse) ; les
bascules de routage sont non linéaires (cascades ×7,9, garde tropicale) et ce n'est qu'une borne de départ.
Cette table donne les premiers chiffres de la politique λ du lot B pour le 120b ; je n'ai pas la distribution
de poids du 20b, où la KL a été mesurée.

### 1.6 Chiffrés sans aucune donnée de modèle

- **Jauge de permutation** : les 2 880 neurones intermédiaires d'un expert peuvent être permutés sans changer
  la fonction (permutation des lignes de gate et up, des colonnes de down). Écrire une seule des 2 880!
  permutations coûte log₂(2880!) = 28 949 bits, soit 2,7·10⁻⁴ des 105,8 Mbit d'un expert (0,0012 bit par
  poids). Même si un ordre canonique supprimait toute cette redondance, le gain serait sous le seuil de 0,015
  bit par poids que s'est donné le lot A : **fermé** [calc., `e1/annexe-poids-jauge-landauer.json`].
- **Landauer** : effacer un bit à 300 K coûte au moins k_B T ln 2 = 2,87·10⁻²¹ J (Landauer 1961 [mém.], vérifié
  expérimentalement par Bérut et al., Nature 2012 [mém.]). Un NVMe à 5 W lisant 2,8 Go/s dépense environ
  2·10⁻¹⁰ J par bit (5 W est un ordre de grandeur de ma mémoire, non mesuré ici) : dix ordres de grandeur
  au-dessus de la borne. Aucun mécanisme d'économie d'énergie n'en sort ; **non candidat**. Bekenstein, idem :
  aucune densité d'information n'est en jeu à cette échelle.

---

## 2. Les candidats, classés

Classement par promesse pour la mission (octets lus par jeton), puis par nouveauté. Colonne « statut » :
**neuf** (rien de tel dans troncons ni, à ma lecture, pour la grille MXFP4 emboîtée), **vu ailleurs** (la
littérature l'a fait, pas troncons), **fermé** (mesuré ou chiffré).

### Candidat 1. Recuit et échange de répliques sur les choix de la mutation synonyme (CVP, verre de spin)

**Statut : neuf pour troncons ; la méthode est de la physique statistique, l'ingrédient (descente de
coordonnées) est vu ailleurs.** Rang 1.

- **Ce que le monde fait.** Trouver l'état de plus basse énergie d'un verre de spin est le problème que le
  recuit simulé (Kirkpatrick, Gelatt et Vecchi, Science 1983 [mém.]) et l'échange de répliques ou « parallel
  tempering » (Hukushima et Nemoto 1996 [mém.]) résolvent bien mieux qu'une descente gloutonne : la descente
  s'arrête dans un minimum local, des répliques à des températures croisées le traversent. Choisir pour chaque
  poids un niveau de la grille de façon à minimiser (w − q)ᵀ H (w − q) est le CVP, un problème d'énergie de
  verre de spin avec des couplages donnés par H. Chen, Shabanzadeh, Crnčević, Hoefler et Alistarh (arXiv
  2507.18553, v1 2025-07-24, v4 2026-05-13, ICLR 2026) prouvent que **GPTQ est l'algorithme du plan le plus
  proche de Babai** sur le réseau défini par la hessienne des entrées, sans réduction LLL, avec la borne
  d'erreur de Babai [lu]. QuantEase (arXiv 2309.01885) pose le même problème comme discret non convexe et le
  résout par descente cyclique de coordonnées : jusqu'à 30 % d'erreur de quantification relative en moins que
  GPTQ en 3 et 4 bits, jusqu'à 15 % en perplexité, selon ses auteurs [lu, non reproduit]. CDQuant (arXiv
  2406.17542, Google DeepMind) fait de même avec une descente gloutonne et bat GPTQ en 2 à 4 bits [lu, non
  reproduit]. Ma recherche n'a trouvé aucun travail de recuit ou d'échange de répliques sur la quantification
  de modèles de langage ; seul un travail de 2025 formule l'arrondi AdaRound comme QUBO résolu par recuit, sur de
  petits réseaux d'images [lu, résumé de recherche].
- **Problème de troncons.** Compression avec perte, mode rapide : la mutation synonyme choisit déjà les
  symboles par rétroaction d'erreur pondérée par H = E[g² x xᵀ] (genome/07-genome-synonyme.md) ; c'est un seul passage de
  Babai. Le débit est de 2,65 bits par poids ; la KL sur le texte est le juge.
- **Traduction concrète.** Garder le codeur de B1 (même décodeur, même LUT, même format `.rapide.trc`), et
  remplacer le choix des symboles par : (1) une descente cyclique de coordonnées à partir de la solution de
  Babai, objectif H-pondéré plus λ fois le débit ; (2) un échange de répliques sur les symboles (8 températures,
  mouvements d'un symbole à un voisin de la grille, énergie incrémentale en O(n) par coup avec la ligne
  correspondante de H). Rien ne change côté décodeur, donc rien ne change dans le moteur ni dans le noyau
  CUDA.
- **Expérience.** Sur les 8 experts de l'équipe genome (couches 0, 8, 16, 23 × experts 0 et 16 du 20b), les
  entrées de calibration capturées (genome-capture, 12 fenêtres) : erreur H-pondérée de Babai contre
  descente de coordonnées contre échange de répliques, **à débit égal** (λ fixé) ; puis les mêmes erreurs sur
  des fenêtres de **tenue** jamais vues, parce que l'écart calibration/évaluation vaut déjà ×3,5 à δ\* = 1
  (05 § 3.4) et qu'un optimiseur plus fort sur-ajuste davantage. Seuil à déclarer avant : erreur de tenue en
  baisse d'au moins 10 % à débit égal sur 6 experts sur 8, puis KL appariée ≤ −0,005 contre le fichier
  λ = 0 actuel sur 10 fenêtres, par le juge. Témoin : sur une instance de n ≤ 10 poids et 5 niveaux, la
  force brute (5¹⁰ = 9,8 millions d'états) donne l'optimum exact ; le recuit doit le retrouver, Babai non.
- **Données existantes.** Fichiers de l'équipe genome (captures, plans, `outils/genome/synonyme/`), poids du
  20b en GGUF (huit experts de 13 Mo), passe KL du juge.
- **Gain attendu, honnête.** Si l'erreur H-pondérée baisse de 20 % à débit égal, la théorie de haute
  résolution (D ∝ 2^(−2R)) dit 0,16 bit par poids, soit 6 % du débit du mode rapide, donc ≈ +6 % de débit
  de lecture sur ses fichiers [calc., hyp.]. La littérature rapporte 30 % d'erreur relative en moins
  pour QuantEase sur des grilles entières depuis le BF16 : sur notre grille MXFP4 emboîtée, avec 766 entrées
  de calibration pour 2 880 dimensions, la marge est probablement plus petite et la tenue décide.
- **Déjà fermé.** ECSQ sans rétroaction (presque rien) ; S\* (égal en KL) ; l'idée « S\* + H complet » est
  ouverte (05 § 3.4) et voisine. Aucune descente de coordonnées ni recuit n'a été essayé dans troncons.
- **Variante physique, même famille.** « Quantification douce par couplage de poids » (Bernstein, Di Carlo et
  Schwab, arXiv 2601.21219, 2026-01-29 [lu, résumé de recherche]) : des attractions à courte portée entre
  poids, ajoutées à la perte pendant l'entraînement, condensent un réseau en niveaux discrets. Elle demande de
  l'entraînement ; sa version post-entraînement, avec H-pondéré à la place de la perte de tâche et un couplage
  croissant (un recuit du couplage), est le même solveur que ci-dessus.

### Candidat 2. Métrique de sortie par les routeurs aval (réponse linéaire autour de la surface de Fermi)

**Statut : vu ailleurs pour des quantificateurs appris à 3-4 bits ; neuf pour troncons.** Rang 2.

- **Ce que le monde fait.** DREAM-MoE (Park, Lee et Kim, ICML 2026, atelier AdaptFM, icml.cc/virtual/2026/75215
  [lu]) ajoute à l'objectif de calibration d'une quantification apprise des contraintes de marge par paires entre
  experts choisis et experts voisins de la frontière, et régularise chaque bloc par le comportement du
  routeur suivant ; meilleur sur 5 réglages sur 6 de trois modèles MoE (3 et 4 bits). SRA-MoE aligne le
  routeur sur les jetons dont la sortie change vraiment [lu, résumé de recherche]. Gu (arXiv 2608.11212,
  2026-07-14, pré-enregistré) mesure sur OLMoE qu'environ un tiers du dommage d'une quantification du cache KV
  passe par les bascules de routage, que la marge détecte qu'une bascule a eu lieu (AUC 0,772) mais ne dit pas
  si elle aide ou nuit (au hasard) [lu] : c'est la forme de nos propres constats de la garde tropicale (marge
  seule 57,1 %, indices multiples +1,61 point).
  La physique : la sortie d'un expert est une petite perturbation du flot résiduel ; au premier ordre, la
  variation de la marge d'un routeur aval est une forme linéaire de la perturbation, et la probabilité de
  bascule est la densité de marge en zéro fois cette forme (théorie de la réponse linéaire ; la loi de la marge
  est presque exponentielle, donc cette densité est 1/E[m], mesurée, garde tropicale § 0).
- **Problème de troncons.** La propriété (c) : l'erreur de sortie d'expert ne prédit pas la KL. La métrique
  de H ne regarde que l'entrée de l'expert ; il manque le côté sortie.
- **Traduction concrète.** Une pondération de sortie M_ℓ = Σ_(ℓ' > ℓ) R_ℓ'ᵀ D_ℓ' R_ℓ' où R_ℓ' est la matrice du
  routeur (128 × 2 880) précédée de la norme RMS, D_ℓ' la densité de marge 1/E[m_ℓ'] par couche ; l'objectif
  de quantification devient tr(M_ℓ (W − Ŵ) H (W − Ŵ)ᵀ), un produit de Kronecker (au sens de K-FAC [mém.],
  Martens et Grosse 2015) dont GPTQ n'utilise que le facteur d'entrée. Utilisé comme **proxy** dans le candidat 1,
  ou seul pour pondérer le choix entre mécanismes.
- **Expérience.** Étape 1 (sans carte, sans KL) : calculer pour les six mécanismes du tableau (c) de 05 § 2.1
  (synonyme λ = 0, S\*, partitions par κ, hebbien par e, hebbien (e, ligne, colonne), partitions par e) l'erreur
  de sortie d'expert pondérée par M_ℓ sur les captures, et tester si elle ramène l'écart entre la
  courbe erreur-KL et une droite (résidu RMS en log sur les six points, contre l'erreur d'expert brute).
  Seuil à déclarer avant : résidu réduit d'au moins 40 %. Remarque honnête : le rang des six points par l'erreur
  d'expert brute est déjà presque bon (corrélation de Spearman 0,94, un seul échange) ; la métrique doit
  corriger les amplitudes (hebbien par e : erreur 1,02 pour une KL ×3,06), pas les rangs.
- **Données existantes.** Captures de l'équipe genome, plans des mécanismes (`mesures/genome/predictif-elagage/plans/`),
  matrices de routeur en GGUF (petites), `erreur-contre-kl.csv`.
- **Gain attendu.** Indirect : un proxy de la KL sans passe de référence f64 (2 168 s par passe sur les
  fenêtres neuves) et un critère de choix de mécanisme ; au mieux une partie du −27 % de KL de la mutation
  synonyme, peut-être du même ordre que son gain actuel. Chiffre non estimable sans l'étape 1.
- **Déjà fermé.** Le détecteur de bascule par la marge est fermé (garde tropicale, JUGEMENT) ; ce qui reste
  ouvert est la **pondération du côté sortie dans la quantification**, qui n'est pas dans troncons.

### Candidat 3. Portillon de poids : servir par la base les défauts de faible poids

**Statut : vu ailleurs, dans le plan λ du lot B ; ici avec ses premiers chiffres sur le 120b.** Rang 3.

- **Ce que le monde fait.** HOBBIT (arXiv 2411.01433, Tang, Liu, Hou et al. [lu, résumé de recherche]) charge, à
  un défaut de cache, une version de faible précision d'un expert d'importance faible, estimée par la magnitude
  du poids de porte ; Lu et al. (ACL 2024, arXiv 2402.14800 [lu, résumé de recherche]) sautent dynamiquement des
  experts de faible poids sur Mixtral. Lens physique : les poids sont des nombres d'occupation.
- **Problème de troncons.** Octets de défaut lus sur le disque.
- **Traduction concrète.** À un défaut, si le poids de mélange (connu après le routeur de la couche, avant la
  lecture) est sous θ, lire le fichier `.rapide.trc` de l'expert ; sinon l'exact. Aucun format nouveau.
- **Expérience.** Mesure §1.5, déjà faite pour les octets ; reste la KL de bout en bout sur le moteur, 20b,
  10 fenêtres, θ ∈ {0,20 ; 0,25}, contre le tout-exact et le tout-rapide (la KL de ce dernier : 0,1446 à 0,1448).
- **Données existantes.** Traces et poids du 120b (§1.5) ; fichiers `.rapide.trc` du 20b (lot B) ; moteur et
  juge.
- **Gain attendu.** 8,6 % (θ = 0,20) à 19,5 % (θ = 0,25) des octets de défaut en moins, soit un débit de
  1,09 à 1,24 fois si le disque borne tout et que la vitesse suit les octets, ce que le juge a montré faux
  ailleurs (JUGEMENT § 7, G1 : 1,28 et non 2,00) ; pour une KL qui, si elle est proportionnelle à l'énergie
  perturbée, vaut 0,055 à 0,183 de celle du tout-rapide. Bornes de départ, pas des prévisions.
- **Déjà fermé.** La coupure totale (E2, 0,09 %). Le portillon est le reste du compromis.

### Candidat 4. Noyaux de mémoire de loi de puissance, de relaxation étirée, à deux temps (cache)

**Statut : neuf comme forme, FERMÉ par la mesure E1.** Rang 4.
Omori-Utsu (Utsu 1961, Ogata 1988 [mém.] ; arXiv 2405.10527 [lu]) ; Kohlrausch (verres, [mém.]) ; temps de
relaxation multiples. Mesuré : +0,0051, +0,0028, +0,0044 de taux de succès, contre un seuil de +0,015
(§ 1.2). Expérience qui reste, si on veut un dernier tour : un noyau par couche (les couches ont des
réutilisations de 0,14 à 0,53, mesures/gpt-oss.md) ; je ne le fais pas, car le mélange d'ordre ne vaut que
3,7 points : il n'y a pas de marge pour un noyau.

### Candidat 5. Barrière de nucléation pour l'admission au cache

**Statut : vu ailleurs (admission de TinyLFU [mém.]) ; FERMÉ par la mesure E3.** Rang 5.
−0,0012 contre un seuil de +0,015 (§ 1.3).

### Candidat 6. Coupure de Fermi : retirer les experts d'occupation faible

**Statut : vu ailleurs (Lu et al. 2024 [lu, résumé de recherche]) ; FERMÉ par la mesure E2.** Rang 6.
0,09 % des défauts sous 0,05 de poids (§ 1.4). Les poids de gpt-oss sont plats ; le saut d'experts de
Mixtral (k = 2, poids très inégaux) ne se transpose pas.

### Candidat 7. Réseaux de tenseurs, jauge, holographie, Landauer : les grands noms

**Statut : FERMÉS par les chiffres ou par une propriété déjà mesurée.** Rang 7.
- **Réseaux de tenseurs (opérateurs en produit de matrices)** : CompactifAI (Tomut, Orús et al., arXiv
  2401.14109 [lu, résumé de recherche]) tronque la dimension de liaison, donc les corrélations entre
  morceaux d'une matrice. La propriété (a) (information du voisin 0,005 bit, poids gaussiens à 1,5 % près ;
  90 % de l'énergie de la famille d'une couche demande 2 180 directions sur 2 880) donne le pronostic : un
  tenseur de bruit n'a pas de structure de faible intrication. Le test qui trancherait (valeurs singulières du
  réarrangement de Van Loan et Pitsianis d'un expert, coupes 45 × 64) lit 13 Mo d'un modèle ; non fait, le
  verrou de la carte tenant la séance disque du juge. Non fait n'est pas fermé : classé « pronostic défavorable ».
- **Jauge de permutation** : 2,7·10⁻⁴ des bits d'un expert (§ 1.6) : fermé.
- **Holographie, superposition de plusieurs experts dans une même mémoire** : stocker N motifs dans une mémoire
  de capacité C bits ne rend rien au-dessous de Shannon ; des poids qui sont du bruit n'ont pas de redondance
  à superposer. Même verdict que la graine. Fermé [calc., sans mesure neuve].
- **Compression avec perte par portes aléatoires et propagation d'enquête** (Ciliberti, Mézard et Zecchina,
  Phys. Rev. Lett. 95, 038701, 2005, arXiv cond-mat/0504509 [lu, résumé de recherche]) : codage de source par
  contraintes parcimonieuses, qui approche la borne de Shannon avec un encodage linéaire. C'est la lignée du
  treillis déjà mesuré (fondations/02 : le treillis ferme 88 % de l'écart du scalaire) ; le décodage par XOR
  y est son seul trait propre. Déjà vu.
- **Criticité, avalanches** : les bascules s'enchaînent ; 5 087 bascules pour 2 081 racines donnent un
  processus de branchement sous-critique de ratio ≈ 0,59 si l'on prend la taille moyenne 2,44 = 1/(1 − σ)
  [calc. sur garde-tropicale.md ; modèle de Galton-Watson, hyp.]. Cela dit que réparer la racine éteint
  des cascades courtes, et c'est exactement la mesure G2 déjà décrite (85,2 % des racines pour 10 %) : rien
  à ajouter.

---

## 3. Ce que la physique ne donne pas, pour la mission

1. **Elle ne fait pas baisser le plancher sans perte.** Sachant l'échelle, les poids sont du bruit ; tout
   mécanisme de structure (graine, motif, jauge, tenseur, holographie) bute sur l'entropie.
2. **Elle ne ferme pas l'écart du cache au Belady.** L'ordre des jetons ne vaut que 3,7 points (§ 0.3). Le
   gain restant est de l'information sur l'avenir, que seul un brouillon (le routage du mode rapide) ou le
   routeur de la couche suivante peut donner, au risque de cascades.
3. **Elle donne des règles de décision et des lunettes** (la marge est une distance à la surface de Fermi,
   les poids sont des occupations, le choix des symboles est un verre de spin) qui, mesurées, ferment ou
   ouvrent des pistes précises : trois fermées ici, une ouverte.

## 4. Ce qui pourrait être faux

- **E1 et E3 ne portent que sur le 120b et sur une capacité** (323 emplacements) ; à 20 % de budget
  (le régime atteignable ici) l'ordre des politiques peut changer. Le simulateur ne rejoue pas l'ordre réel des
  défauts d'un groupe (llama.cpp trie par numéro d'expert) ; l'écart mesuré par l'instrument existant est de
  quatre accès sur 98 304.
- **Les lois de puissance du noyau sont approchées par neuf exponentielles** : la queue est mal rendue
  (§ 1.2). Un noyau de loi de puissance exact pourrait faire un peu mieux ; je le crois sous le seuil, je ne
  l'ai pas montré.
- **Le portillon (§ 1.5) suppose la KL proportionnelle à l'énergie Σg²** et la taille du fichier rapide à
  0,71 de l'exact ; les poids du 20b, où est la KL, n'ont pas été relus.
- **Candidat 1 : un résultat de la littérature n'est pas un résultat ici.** QuantEase et CDQuant le montrent
  sur des grilles entières depuis le BF16, avec leurs propres réglages ; je ne les ai pas reproduits. Le risque
  principal est le sur-ajustement à 766 entrées de calibration.
- **La recherche web est celle de résumés** (titres, résumés, pages de conférence) ; aucun article n'est lu en
  entier. Les chiffres de la littérature portent l'étiquette « selon ses auteurs, non reproduit ».
- **Un chiffre de la déclaration, écrit de mémoire (« 13 % »), a été barré.** Les prédictions de E1 et E2 ont
  tenu, celle de E3 a échoué par le signe.

## 5. Sources

| Source | Adresse | Date | Lecture |
|---|---|---|---|
| Chen, Shabanzadeh, Crnčević, Hoefler, Alistarh, *The Geometry of LLM Quantization: GPTQ as Babai's Nearest Plane Algorithm* | https://arxiv.org/abs/2507.18553 | v1 2025-07-24, v4 2026-05-13 ; ICLR 2026 | page arXiv, consultée 2026-10-27 |
| QuantEase : Optimization-based Quantization for Language Models | https://arxiv.org/abs/2309.01885 | v1 2023-09 | résumé de recherche, 2026-10-27 (auteurs [mém.]) |
| CDQuant : Greedy Coordinate Descent for Accurate LLM Quantization | https://arxiv.org/abs/2406.17542 | 2024 | résumé de recherche, 2026-10-27 |
| Park, Lee, Kim, *DREAM-MoE* | https://icml.cc/virtual/2026/75215 | ICML 2026, atelier AdaptFM | page de conférence, 2026-10-27 |
| SRA-MoE : Output-Aware Selective Router Alignment for MoE Quantization | https://icml.cc/virtual/2026/75289 | ICML 2026 | résumé de recherche seulement |
| Gu, *Detecting a Route Flip Is Easier Than Knowing Whether to Fix It* | https://arxiv.org/abs/2608.11212 | 2026-07-14 (v1) | page arXiv, 2026-10-27 |
| Skliar et al., *Mixture of Cache-Conditional Experts for Efficient Mobile Device Inference* | https://arxiv.org/abs/2412.00099 | v1 2024-11-27, TMLR 2025 | résumé de recherche (déjà dans fondations/04) |
| Tang, Liu, Hou et al., *HOBBIT* | https://arxiv.org/abs/2411.01433 | 2024-11 | résumé de recherche |
| Lu et al., *Not All Experts are Equal* (ACL 2024) | https://arxiv.org/abs/2402.14800 | 2024 | résumé de recherche |
| Bernstein, Di Carlo, Schwab, *Soft Quantization: Model Compression Via Weight Coupling* | https://arxiv.org/abs/2601.21219 | 2026-01-29 | résumé de recherche |
| Tomut, Orús et al., *CompactifAI* | https://arxiv.org/abs/2401.14109 | 2024-01 | résumé de recherche |
| Ciliberti, Mézard, Zecchina, *Lossy data compression with random gates*, PRL 95, 038701 | https://arxiv.org/abs/cond-mat/0504509 | 2005 | résumé de recherche |
| *Hawkes Models And Their Applications* | https://arxiv.org/abs/2405.10527 | 2024 | résumé de recherche |
| Kirkpatrick, Gelatt, Vecchi, *Optimization by simulated annealing*, Science 220 ; Hukushima et Nemoto, J. Phys. Soc. Jpn 65 ; Utsu 1961 ; Ogata 1988 ; Landauer, IBM J. Res. Dev. 5, 1961 ; Bérut et al., Nature 483, 2012 ; Martens et Grosse (K-FAC), ICML 2015 ; Einziger et al. (TinyLFU), 2017 | — | — | [mém.], non relus, aucun chiffre porteur n'en dépend |
