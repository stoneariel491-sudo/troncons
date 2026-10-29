# Éclaireur « mathématiques et théorie de l'information » : ce que le monde fait, ce que nos données disent

Rôle : éclaireur du domaine mathématiques et théorie de l'information, flux « mimétisme absolu » du
2026-10-26. Écrit les 2026-10-26 et 2026-10-27. Étiquettes : **[mes.]** mesuré ici (outil et journal
commités) ; **[calc.]** calculé sur des mesures commitées, formule écrite ; **[lu]** lu à la source
(résumé ou page d'éditeur, texte intégral seulement quand c'est dit) ; **[mém.]** de mémoire, non relu ;
**[hyp.]** hypothèse dite. Seuils déclarés et commités avant toute lecture de trace :
`mesures/mimetisme/mathematiques/00-seuils-declares.md` (commit 2017fcf ; deux amendements datés, dont un
écrit après avoir vu qu'un de mes témoins était mal posé, § 2.1). Outils : `outils/mimetisme/mathematiques/`.
Journaux : `mesures/mimetisme/mathematiques/`.

---

## 0. En bref

1. **Le domaine donne des bornes plus que des leviers, et deux bornes mesurées ferment des voies que le
   projet gardait ouvertes.**
   - **La politique de cache est saturée** [mes.] : un prédicteur causal (moyennes mobiles + régression
     logistique, ajusté sur deux traces) mené par l'éviction « prochain usage prédit » dépasse la
     meilleure LFU (demi-vie choisie sur la trace de test, donc généreuse) de **+0,011 à +0,013** à 7 %
     d'emplacements sur trois traces de lecture jamais vues, **+0,003 à +0,007** à 20 % ; même un oracle
     qui connaît le jeton suivant ne rend que **+0,047** (T2bis). L'écart Belady − LFU (0,14 à 0,21) est
     de l'information à long horizon que l'histoire récente ne porte pas.
   - **La vérification groupée est plafonnée** [mes.] : pour T jetons consécutifs, un brouillon gratuit et
     parfait ne ferait gagner que **G(4) = 1,44** et **G(8) = 1,84** en octets d'experts par jeton
     validé (moyenne de cinq traces ; 1,34 à 1,52 et 1,66 à 1,96 selon la trace) ; avec un brouillon qui
     lit le disque au coût du mode rapide (66 % d'un jeton exact), le gain **calculé** reste **sous 1
     pour tout (acceptation, longueur) testé**, y compris acceptation 100 % (0,84 à 0,89) [calc. sur
     mes.]. Le seuil déclaré (« tué si G(4) < 1,5 ou G(8) < 2,0 ») est franchi dans le sens de la mort.
2. **Ce qui reste ouvert, dans l'ordre** : (i) changer le flux de demandes plutôt que la politique
   (routage conditionné par le cache) ; (ii) un préchargement sélectif à risque contrôlé, plafonné à ×1,21 ;
   (iii) le raffinement emboîté du mode rapide, dont l'intérêt a baissé avec M2.
3. **Le message est parti à la session principale** pour (i), avec ses réserves (une seule fois, § 6).

---

## D'où on part, où on va

**Au départ** (fichiers commités) : le cache global de gpt-oss-120b à 323 emplacements rend 0,392 (LRU
de llama.cpp), 0,480 (LFU), 0,500 (ensemble fixe oracle), 0,685 (Belady) sur la génération de 256 jetons
(`mesures/localite-gpt-oss/cache-base-contre-optimum.json`) ; « mesurer un prédicteur réel » est resté
dans la liste de ce qui reste (`mesures/gpt-oss.md` § 10) ; le préchargement par le routeur de la couche
suivante est tué pour ce prédicteur (p = 0,692, −11 %, `moteur/O-pour-le-memoire.md` § 9.2) ; le mode
rapide est un brouillon spéculatif « à mesurer » dont la rentabilité exige un brouillon sans lecture
disque (`genome/05-synthese.md` lemme B2, `idees/biomimetisme-genome-des-poids.md` § 5 quater) ; la
sparsité d'entrée par jeton a été écartée sur SmolLM2-135M parce qu'elle « ne se compose pas » avec la
vérification spéculative (`fondations/05-sparsite.md` § 5.5).

**Ce que ce document établit** : la politique n'a plus de marge mesurable à cette granularité ; la
vérification groupée a un plafond ; la liste de huit candidats ci-dessous, avec ce qui est neuf et ce
qui ne l'est pas.

**Ce qui reste** : une passe du traceur du 20b qui journalise les huit meilleurs logits par couche
(le seul manque de données pour le candidat 1), et la KL par le routage imposé du lot R.

---

## 1. Ce que j'ai lu

Consultation les 2026-10-26 et 2026-10-27 ; User-Agent des outils de recherche : neutre ; aucune donnée
personnelle dans une requête. « Résumé lu » = page de l'éditeur ou de l'archive ouverte, texte
intégral non relu.

| Source | Adresse | Ce qui est lu |
|---|---|---|
| Vitter, Krishnan, *Optimal prefetching via data compression*, J. ACM 43(5), 1996 (version FOCS 1991) | https://projects.csail.mit.edu/jacm/References/vitterk1996:771.html | notice et résumé : un bon compresseur est un bon prédicteur ; taux de défauts optimal à la limite pour les sources markoviennes |
| Curewitz, Krishnan, Vitter, *Practical prefetching via data compression*, SIGMOD 1993 | cité par la notice ci-dessus | seulement la notice |
| Song, Qu, Blumm, Barabási, *Limits of predictability in human mobility*, Science 327:1018, 2010 | https://pubmed.ncbi.nlm.nih.gov/20167789/ | résumé : borne de prédictibilité par l'entropie et l'inégalité de Fano ; une critique ultérieure (Entropy 21(4):432, 2019) note des surestimations |
| Lykouris, Vassilvitskii, *Competitive caching with machine learned advice*, J. ACM 68(4), 2021 (ICML 2018) | https://arxiv.org/abs/1802.05399 | résumé : *Predictive Marker*, garantie lisse avec l'erreur du prédicteur, robuste au pire cas |
| Antoniadis et coll., *Paging with succinct predictions*, ICML 2023 | https://arxiv.org/abs/2210.02775 | résumé : un bit de prédiction par requête suffit à des garanties proches de l'optimum |
| Song, Berger, Li, Lloyd, *Learning Relaxed Belady for CDN caching*, NSDI 2020 | https://www.usenix.org/conference/nsdi20/presentation/song | résumé : apprentissage du prochain usage, éviction de tout objet au-delà d'une « frontière de Belady » ; −4 à −25 % de trafic |
| Beckmann, Sanchez, *Talus*, HPCA 2015 | https://dspace.mit.edu/handle/1721.1/101043 | résumé : partager le flux en deux partitions supprime les falaises de la courbe de défauts |
| Equitz, Cover, *Successive refinement of information*, IEEE Trans. IT 37(2):269, 1991 | https://isl.stanford.edu/~cover/papers/transIT/0269equi.pdf | résumé et énoncé : raffinable ssi les solutions individuelles forment une chaîne de Markov ; blocs i.i.d. gaussiens raffinables |
| Nair et coll., *Matryoshka quantization*, ICML 2025 | https://arxiv.org/abs/2502.06786 | résumé (v1 et v2) : entiers emboîtés, un modèle servi à plusieurs précisions |
| Park et coll., *Any-Precision LLM*, ICML 2024 | https://arxiv.org/abs/2402.10517 | résumé : un modèle à n bits dont on garde les bits de poids fort |
| Tseng et coll., *QTIP*, NeurIPS 2024 | https://arxiv.org/abs/2406.11235 | résumé ; le projet a déjà reproduit son tableau 1 (`fondations/02-quantification.md` § 1) |
| Liu et coll., *TEAL*, ICLR 2025 | https://arxiv.org/abs/2408.14690 | résumé ; déjà lu et mesuré en partie par le projet (`fondations/05-sparsite.md`) |
| McDanel et coll., *MoE-Spec*, 2026-02-17 | https://arxiv.org/abs/2602.16052 | résumé : plafonner le nombre d'experts par couche à la vérification ; +10 à 30 % contre EAGLE-3 |
| Xie et coll., *Less experts, faster decoding (EcoSpec)*, 2026-07-14 | https://www.alphaxiv.org/abs/2607.12696 | résumé : « dispersion d'experts » entre jetons de brouillon, sélection de brouillon au coût marginal d'experts ; jusqu'à ×1,62 ; ne donne pas de chiffre propre à GPT-OSS-120B dans la page lue |
| Ranjan et coll., *Why speculative decoding works better than predicted on sparse MoE models*, NeurIPS 2026 | https://neurips.cc/virtual/2026/poster/150811 | résumé : le chevauchement des experts entre jetons de brouillon ; modèle d'entropie maximale par IPF qui prédit le nombre d'experts distincts à moins de 4 % |
| Skliar et coll., *Mixture of cache-conditional experts*, TMLR 2025 | https://arxiv.org/abs/2412.00099 | résumé : biais de routage vers les experts en cache ; plus de 50 % de défauts en moins, perplexité +0,1 à 3 %, passe sous la borne de l'oracle de cache (modèles autres que gpt-oss) |
| Liang et coll., *SSD-LLaMA*, 2026-09-16 | https://arxiv.org/abs/2609.18110 | résumé : hiérarchie SSD/RAM/VRAM, décodeur rANS CUDA ; le résumé ne donne ni politique de cache ni prédicteur |
| Angelopoulos, Bates, *A gentle introduction to conformal prediction* | https://arxiv.org/abs/2107.07511 | notice et plan seulement |
| Litvinov, *The Maslov dequantization, idempotent and tropical mathematics*, 2005 | https://arxiv.org/abs/math/0507014 | notice seulement |

De mémoire [mém.] : Belady 1966 ; Slepian, Wolf 1973 et Wyner, Ziv 1976 (codage avec information adjacente) ;
Csiszár 1975 (projection d'information, IPF) ; Leviathan, Kalman, Matias 2023 (décodage spéculatif,
acceptation i.i.d.) ; Vietri et coll. 2018 (LeCaR) ; Che et coll. 2002 (approximation du LRU) ; Shah, Lee,
Ramchandran 2013 et Joshi, Liu, Soljanin 2012 (codes MDS contre les retardataires).

---

## 2. Ce que j'ai mesuré

Données : sept traces de lecture du 120b (code, dialogue, prose-en, prose-fr, wiki : 10 669 jetons) et deux
traces de génération de 256 jetons (`mesures/localite-gpt-oss/traces-120b/traces-120b.tar.xz`). Cache et
politiques de référence : les outils du projet, appelés sans copie (`outils/gptoss_localite.py`).

### 2.1 Les témoins

| Témoin | Attendu | Résultat |
|---|---|---|
| T1 : LRU, LFU (demi-vie 8), statique oracle, Belady du projet redonnent `cache-base-contre-optimum.json` (120b, 323 emplacements, génération wiki) | écart < 10⁻⁹ | **tombé à la première écriture** (LRU, écart 5,4·10⁻⁵ : mon tableau triait les experts d'un groupe par numéro au lieu de l'ordre du score, et LRU en dépend) ; corrigé dans l'outil, non dans le seuil ; **tient à 0** ensuite |
| T3 : ordre des jetons de test mélangé (graine 20261026), Δ de PB | < +0,01 | **tient** sur les dix cas : de −0,0034 à −0,0148 |
| W1 : routage uniforme i.i.d., union de T jetons | 128·(1 − (1 − 4/128)^T) | 4,000 ; 7,876 (7,875) ; 15,271 (15,266) ; 28,725 (28,710) ; 51,021 (50,981) pour T = 1, 2, 4, 8, 16 : **tient** |
| W2 : routage figé | union = 4 | **tient** pour T de 1 à 16 |
| W3 : ordre mélangé (M2) | G(T) doit baisser, l'instrument voit l'ordre | **tient** : G(4) 1,30 mélangé contre 1,44, G(8) 1,62 contre 1,84 |
| T2 : PB avec p = indicateur vrai du prochain jeton, rien d'autre | ≥ référence + 0,10 | **tombé** (0,533 contre 0,574, dialogue, N = 323) ; ce n'est pas le cache : un oracle d'un jeton ignore la popularité des éléments non demandés, PB les range alors au hasard. Le témoin était mal posé |
| T2bis (amendement daté avant la suite) : p = prédicteur appris, relevé à 1 − 10⁻³ pour tout élément réellement demandé à l'occasion suivante | ≥ référence + 0,05 | **+0,0469 : manqué de 0,0031**. Dit. Conséquence déclarée à l'avance : le verdict de M1 est « non concluant » au sens strict |

### 2.2 M1 : un prédicteur causal pousse-t-il le cache vers Belady ?

**Le mécanisme** (Vitter et Krishnan : prédire est compresser). Pour chaque (couche, expert), des moyennes
mobiles exponentielles des demandes passées à demi-vies 1, 3, 8, 24, 96 jetons ; une régression logistique
(onze coefficients, IRLS, huit itérations, **ajustée sur prose-en et code seulement**) donne p, la
probabilité d'une demande à la prochaine occasion ; l'éviction retire le plus grand `d + 36(1 − p)/p`,
d = accès avant la prochaine occasion (un Belady dont le prochain usage est prédit, comme LRB). Modèle de
cache du projet (groupes de quatre accès, groupe courant épargné).

Résultats [mes.] (`m1_m2.json`) ; Δ = PB − max(LRU, LFU à la meilleure demi-vie de {2, 8, 32, 128} choisie
sur la trace elle-même) :

| Trace de test | N | LRU | LFU* | PB | Δ | Δ mélangé | Statique oracle | Belady |
|---|---|---|---|---|---|---|---|---|
| dialogue, lecture | 323 | 0,4621 | 0,5745 | 0,5878 | +0,0134 | −0,0134 | 0,5752 | 0,7147 |
| prose-fr, lecture | 323 | 0,5102 | 0,6118 | 0,6248 | +0,0129 | −0,0148 | 0,5780 | 0,7429 |
| wiki, lecture | 323 | 0,4533 | 0,5692 | 0,5802 | +0,0110 | −0,0137 | 0,5689 | 0,7063 |
| wiki, génération | 323 | 0,3920 | 0,5057 | 0,5093 | +0,0036 | −0,0089 | 0,4997 | 0,6845 |
| prose-en, génération | 323 | 0,7365 | 0,7461 | 0,7452 | −0,0008 | −0,0133 | 0,6852 | 0,8371 |
| dialogue, lecture | 922 | 0,7882 | 0,8418 | 0,8444 | +0,0025 | −0,0118 | 0,8437 | 0,9094 |
| prose-fr, lecture | 922 | 0,8223 | 0,8575 | 0,8642 | +0,0068 | −0,0133 | 0,8332 | 0,9229 |
| wiki, lecture | 922 | 0,7698 | 0,8227 | 0,8258 | +0,0031 | −0,0112 | 0,8358 | 0,8960 |
| wiki, génération | 922 | 0,7766 | 0,7939 | 0,7985 | +0,0046 | −0,0075 | 0,8159 | 0,8758 |
| prose-en, génération | 922 | 0,8521 | 0,8625 | 0,8687 | +0,0062 | −0,0034 | 0,8889 | 0,9128 |

**Verdict au seuil déclaré** : Δ moyen sur les trois lectures à 323 emplacements = **+0,0124**, minimum
+0,0110 : très loin de « PROBABLE » (+0,05 en moyenne et +0,03 partout), et sous « neutre » (< +0,02). Mais
T2bis a manqué son seuil de 0,0031, donc le verdict formel est **non concluant**, avec la lecture suivante,
qui est un fait mesuré : **PB réalise 29 % (0,0134 sur 0,0469) de ce que rendrait un oracle d'un jeton, et cet
oracle est lui-même sous la barre de +0,05** : la barre n'était pas atteignable par cette famille.

**Ce que disent les autres colonnes** :
- Le **statique oracle** (les N éléments les plus fréquents *de la trace elle-même*, donc triché) égale ou
  dépasse LFU et PB à 20 % : à ce budget, la popularité stationnaire du genre porte presque tout, la
  récence très peu.
- Le prédicteur appris ne bat pas la fréquence fixe de la trace en entropie : 16,96 contre 16,75 bits par
  décision (couche, jeton) sur dialogue, 17,50 contre 17,03 sur wiki ; il la bat sur prose-fr (16,30 contre
  17,06) et sur la génération prose-en (13,86 contre 15,01). Repère : un tirage uniforme de 4 experts sur 128 coûte log₂ C(128, 4) = 22,3 bits. Le routage est donc **une loi de popularité par genre plus une faible mémoire courte**.
- Le Δ **mélangé** est toujours négatif (−0,003 à −0,015) : le gain, petit, vient bien de l'ordre.

**Ce que M1 ne dit pas** : un prédicteur qui voit le contenu du jeton courant (le routage des couches
déjà passées de ce jeton, ou son état caché) est hors de la famille mesurée ; les traces de lecture sont du
texte lu, deux seulement sont de la génération, et courtes (256 jetons, démarrage à froid).

### 2.3 M2 : l'union des experts sur T jetons consécutifs

`G(T) = 4T / E|U_T|` par couche, fenêtres glissantes, sept traces de lecture (cinq distinctes), sans cache
[mes.] (`m1_m2.json`) :

| T | 2 | 3 | 4 | 6 | 8 | 12 | 16 | 24 | 32 |
|---|---|---|---|---|---|---|---|---|---|
| G(T), moyenne | 1,185 | 1,323 | **1,443** | 1,653 | **1,837** | 2,165 | 2,463 | 3,013 | 3,523 |
| plus basse trace | 1,136 | 1,242 | 1,336 | 1,506 | 1,662 | 1,943 | 2,200 | 2,669 | 3,101 |
| plus haute trace | 1,218 | 1,378 | 1,516 | 1,757 | 1,964 | 2,332 | 2,663 | 3,279 | 3,849 |
| ordre mélangé | 1,113 | 1,212 | 1,302 | 1,465 | 1,615 | 1,891 | 2,147 | 2,622 | 3,070 |
| par couche, de la pire à la meilleure (T = 8) | 1,21 à 3,35 | | | | | | | | |

**Verdict au seuil déclaré** : G(4) < 1,5 sur quatre traces sur cinq (la cinquième, prose-fr, 1,516) et G(8) < 2,0
sur les cinq : la voie « vérification groupée avec un brouillon quelconque » est **tuée au sens déclaré**. La
prédiction écrite avant (G(4) 1,4 à 1,6 ; G(8) 1,7 à 2,1) tenait.

**Gain calculé du décodage spéculatif** [calc. sur mes., `plafond_speculatif.py`, acceptation i.i.d., sans
cache ni partage entre brouillon et vérification] : gain = 4 × jetons validés par cycle / (4T/G(T) + 4γc),
c = octets lus par jeton du brouillon sur ceux d'un jeton exact.

| acceptation α | brouillon | γ = 1 | γ = 3 | γ = 7 |
|---|---|---|---|---|
| 0,7 (accord de premier choix du mode rapide, 07 § 0) | gratuit (c = 0) | 1,01 | 0,91 | 0,72 |
| 0,7 | mode rapide (c = 0,66, 07 : −34 % d'octets) | 0,72 | 0,53 | 0,35 |
| 0,9 | gratuit | 1,13 | 1,24 | 1,31 |
| 0,9 | mode rapide | 0,81 | 0,72 | 0,64 |
| 1,0 | gratuit | 1,19 | 1,44 | 1,84 |
| 1,0 | mode rapide | 0,85 | 0,84 | 0,89 |

Un brouillon qui lit le disque au coût du mode rapide ne gagne nulle part, même parfait. Ce que dit la
littérature de 2026 va dans le même sens : la vérification d'un grand arbre active beaucoup d'experts
distincts et érode le gain (MoE-Spec, EcoSpec), le chevauchement entre jetons est ce qui décide
(Ranjan et coll.) ; leurs gains (×1,2 à ×1,6) sont des gains de calcul-mémoire de GPU de centre de données,
pas de disque.

### 2.4 M3 : les marges du routeur, comme borne

`m3_marges_20b.json` [mes., description], 122 640 cellules du 20b (marge entre les 4e et 5e logits biaisés) :
part sous 0,01 : 8,2 % ; sous 0,03 : 22,4 % ; sous 0,1 : 56,3 % ; sous 0,3 : 90,3 % ; médiane 0,0832.
Échanger le 4e expert contre le 5e dans ces cellules change un accès sur quatre : le gain de succès est
au plus part(β)/4, soit **14 points au plus à β = 0,1**, et en pratique ce nombre multiplié par la
probabilité que le 4e soit un défaut et le 5e un succès [hyp. : 0,2 à 0,3, soit 3 à 4 points].

---

## 3. Les candidats, classés

Séparation : **NEUF pour le projet** (rien dans les documents lus) ; **VU** (le projet l'a déjà traité ou
écarté, ou la littérature le fait mais il n'a pas été mesuré ici) ; **MESURÉ-FERMÉ** (jugé dans ce flux).

### Candidat 1 · Routage conditionné par le cache : changer le flux, pas la politique (NEUF pour le projet)

- **Ce que le monde fait.** Skliar et coll. (TMLR 2025, arXiv 2412.00099) ajoutent un biais aux logits des
  experts déjà en cache avant le top-k : plus de 50 % de défauts en moins, perplexité +0,1 à 3 %, et un
  taux de succès au-dessus de la borne de l'oracle de cache, parce que l'oracle de Belady est optimal *pour
  un flux fixé* et que le biais change le flux [lu : résumé, modèles à experts fins et à k plus grand que
  celui de gpt-oss].
- **Pourquoi c'est ce que M1 désigne.** La politique a rendu +0,012 ; l'oracle d'un jeton +0,047 ; Belady
  seul est loin (0,14 à 0,21). Une fois la politique saturée, la seule façon de passer sous Belady est de
  changer les demandes. Les quasi-égalités existent chez nous : 56 % des cellules ont une marge 4e-5e
  sous 0,1 (M3). C'est le contraire de la garde tropicale, qui protégeait les marges ; ici, on les
  dépense, même esprit que la remarque de Stone sur l'expert pont (« si un point ne marche pas faire le
  contraire », `idees/biomimetisme-genome-des-poids.md` § 5 sexies).
- **Problème de troncons visé.** Octets lus par jeton, via le taux de succès du cache à budget fixe.
- **Traduction.** Dans le moteur, avant le top-k du routeur : `z_i ← z_i + β · [(couche, i) ∈ cache]`, β en
  unités de logit (0 = modèle exact) ; les poids de mélange restent le softmax des logits **non biaisés**
  des quatre experts choisis (ou des logits biaisés : deux variantes). Un mode de plus à côté du mode
  rapide : un deuxième bouton de qualité, continu, qui ne demande aucun nouveau fichier.
- **Expérience.** (a) *Côté succès, sans modèle* : une passe du traceur sur le 20b qui journalise, par
  couche et par jeton, les huit meilleurs (expert, logit) ; rejouer le cache global avec biais β ∈ {0 ; 0,03 ;
  0,1 ; 0,3 ; 1} sur les mêmes traces : courbe (β, succès, taux d'échange). Seuil à déclarer avant : au
  moins +10 points de succès à 7 % d'emplacements pour au plus 25 % de cellules échangées. (b) *Côté
  qualité* : la KL contre la référence f64, avec la fonction de routage imposé qui existe déjà au lot R
  (expérience B, `mesures/moteur/R/r1_reference.py` et Tome II, lot R § 2.9), sur les mêmes fenêtres que R1. Seuil à déclarer avant : KL ≤ celle d'un
  mode rapide de gain d'octets égal (0,13 pour −34 %, soit 0,038 pour −10 %).
- **Données existantes.** Insuffisantes : les journaux de routage du lot R ne gardent que l'ensemble des
  quatre experts et la marge 4e-5e (`bascules.py`), pas l'identité du 5e. M3 en tire la seule borne
  disponible.
- **Gain attendu, honnête.** Succès +3 à +4 points avec le seul échange 4e-5e [calc. de M3 et hyp. de 0,2 à 0,3 sur la probabilité] ; avec un échange plus
  profond (6e, 7e), l'article suggère bien davantage, mais sur d'autres modèles. En régime disque, +10 points
  de succès à 50 % de succès de départ = 20 % d'octets en moins (×1,25 de vitesse) [calc.]. Si l'article se
  transposait entièrement (défauts divisés par 2) : ×1,7 à ×2 [hyp., improbable ici].
- **Risque principal.** Une bascule voulue coûte comme une bascule subie : le lot R mesure 26,6 % de
  propagation à la couche suivante et 96,5 % de la KL portée par les positions qui basculent. Par un calcul
  grossier, 56 % de cellules échangées reviennent à une KL de l'ordre du mode rapide pour un gain d'octets
  bien plus faible [hyp. : linéarisation de 0,0145 de KL pour 4,15 % de bascules] ; c'est ce que (b)
  tranche.
- **Déjà fermé ?** Non pour la mesure. Fermé : la garde qui *protège* les marges (57,1 % des bascules pour 10 % des cellules ; garde à indices multiples
  58,6 %, `genome/pistes/tropicale/`, commit 9e31d9f).

### Candidat 2 · Préchargement sélectif à risque contrôlé (prédiction conforme) (NEUF pour le projet, plafond bas)

- **Ce que le monde fait.** La prédiction conforme (Vovk ; Angelopoulos et Bates, arXiv 2107.07511) donne un
  ensemble de prédiction dont la couverture est garantie sans hypothèse de loi ; la maîtrise conforme du
  risque (Angelopoulos et coll., ICLR 2024 [mém.]) étend cela à toute perte monotone. Les systèmes de
  déchargement d'experts préchargent tout ce que le prédicteur nomme (ProMoE, `fondations/05-sparsite.md`
  l. 407) ; moe-offload (Apple Silicon, https://github.com/Jakevin/moe-offload, résumé de recherche seulement) n'en garde que trois par couche.
- **Problème visé.** Le préchargement a été tué par la précision : p = 0,692, +34 % d'octets lus, −11 %
  (`moteur/O-pour-le-memoire.md` § 9.2), qui écrit lui-même « ne reviendrait qu'avec p > 0,9 environ ».
- **Traduction.** Ne précharger que les experts dont la marge **prédite** (routeur de ℓ + 1 appliqué au résidu
  de ℓ) dépasse un seuil θ calibré en conforme pour garantir p ≥ 0,9 sur le sous-ensemble choisi ; la
  couverture baisse, la précision monte.
- **Plafond, calculé.** Avec f ≈ 0,17 du temps d'un jeton cachable par recouvrement (§ 9.2), le gain
  maximal, p = 1 et couverture 100 %, est 1/(1 − 0,17) = **×1,21** ; à p = 0,9 et couverture 40 %, ≈ ×1,07
  [calc.].
- **Expérience.** Une passe du 20b qui journalise, par (couche, jeton), la marge prédite et les quatre
  experts prédits à côté des quatre vrais : courbe précision-couverture selon θ. Seuil à déclarer avant :
  p ≥ 0,9 pour une couverture ≥ 40 %.
- **Données existantes.** Aucune (il faut l'état caché avant la couche).
- **Déjà fermé ?** Le préchargement naïf. Pas le sélectif.

### Candidat 3 · Raffinement successif emboîté du mode rapide (VU en littérature ; NEUF pour le compagnon synonyme)

- **Ce que le monde fait.** Equitz et Cover (1991) : un problème de débit-distorsion est raffinable
  ssi ses solutions successives forment une chaîne de Markov ; les blocs i.i.d. gaussiens le sont.
  Matryoshka quantization (ICML 2025) et Any-Precision LLM (ICML 2024) en font des modèles qui servent
  plusieurs précisions depuis un seul stockage.
- **Ce que le projet a.** La découpe base + complément du format `.trc` (2,64 + 1,22 bit) est déjà emboîtée
  pour la base *tronquée*. Le compagnon synonyme (2,67 bits, KL 0,13) choisit ses symboles par
  rétroaction : il n'est plus une fonction du code exact poids par poids, donc il n'est pas emboîté :
  lire le rapide puis l'exact coûte 2,67 + 3,72 bits.
- **Traduction.** Coder l'exact *conditionnellement* au rapide, avec le symbole rapide comme contexte du flux
  rANS (le codeur connaît les deux, donc pas besoin de Slepian-Wolf). Borne : le rapide est une fonction du
  tenseur entier, donc le complément coûte au moins H(W) − H(rapide) ≈ 3,72 − 2,67 = **1,05 bit**
  [calc., borne idéale ; le contexte par poids coûte plus].
- **Expérience.** Mesurer H(code exact | symbole rapide, échelle) sur quelques experts du 20b, lus
  dans le GGUF et dans `<nom>.rapide.trc` (deux fois 12 Mo, pas de lecture lourde), avec le décodeur du juge
  (`outils/genome/construction/juge/decodeur_juge.py`). Seuil à déclarer avant : ≤ 1,6 bit (gain ≥ 55 %
  sur la seconde lecture).
- **Gain attendu.** Nul tant qu'une seule des deux lectures a lieu. Il ne compte que pour un brouillon qui
  lit le rapide puis une vérification qui lit le complément des mêmes experts, c'est-à-dire pour la
  voie que M2 vient de tuer. **Valeur après M2 : basse.**
- **Déjà fermé ?** La découpe sur la base tronquée est faite.

### Candidat 4 · Prédiction par compression (MESURÉ-FERMÉ, M1)

Vitter et Krishnan, LRB, Predictive Marker, un prédicteur appris : mesuré en § 2.2, **+0,012** à 7 %,
**+0,005** à 20 %, oracle d'un jeton +0,047. Les garanties de Lykouris et Vassilvitskii et d'Antoniadis
et coll. (robustesse quand le prédicteur se trompe) ne servent qu'à des prédicteurs qui valent d'être
suivis ; celui-ci ne vaut pas la complexité.
- **Ce qui reste.** Un prédicteur qui voit l'état du jeton courant (non mesuré, hors de la famille).

### Candidat 5 · Vérification groupée, plafond d'union, sélection de brouillon sous-modulaire (MESURÉ-FERMÉ, M2 ; VU en littérature)

La couverture « choisir les jetons de brouillon qui ajoutent le moins d'experts nouveaux » est une
maximisation sous-modulaire gloutonne (garantie 1 − 1/e, Nemhauser, Wolsey, Fisher 1978 [mém.]) ;
EcoSpec la fait. Le plafond de la § 2.3 vaut pour la moyenne des fenêtres ; une sélection peut monter
au-dessus (G par couche va de 1,21 à 3,35 à T = 8), mais il faudrait que le brouillon soit presque
gratuit : voir le tableau, un brouillon qui lit le disque ne gagne nulle part.

### Candidat 6 · Lissage de Maslov du top-k (MESURÉ-FERMÉ par calcul jouet, VU en théorie)

Le top-k est un polynôme tropical ; sa version lisse (log-somme-exp à température T, déquantification de
Maslov, Litvinov 2005) remplace la bascule dure par une rampe de largeur w, au prix de lire le 5e expert
dans la fenêtre. Calcul jouet (`maslov_jouet.py`, marge de densité plate, bruit gaussien d'écart-type 1, saut
supposé égal des deux côtés) [calc.] : l'erreur quadratique par rapport au routage dur exact est multipliée
par **0,91 / 0,83 / 0,74 / 0,73 / 0,84 / 0,99** pour w = 0,25 / 0,5 / 1 / 2 / 3 / 4 écarts-types. **Au mieux
−27 % de l'énergie d'erreur due aux bascules**, pour +1 expert lu dans les cellules de marge < w. À l'échange
mode rapide (0,13 de KL pour −34 % d'octets), −27 % de la part de bascule vaut au plus quelques points
d'octets et l'expert en plus les mange : **neutre au mieux**, non prioritaire. La raison de fond : le rapport
ne descend pas sous 0,73 parce que la décision dure est la cible.

### Candidat 7 · Codes à effacement contre les retards du disque (FERMÉ par la physique)

Lire n morceaux codés MDS et en utiliser k (Joshi, Liu, Soljanin ; Shah, Lee, Ramchandran [mém.]) abaisse la
latence quand les serveurs sont indépendants et que la bande passante est libre. Ici, un seul disque, borné
par sa bande passante, deux régimes de débit : n/k − 1 octets de plus lus se paient au débit, et les
lectures de 64 Kio aléatoires plafonnent à 0,74 Go/s (`fondations/01-machine.md` § 2.4), contre 2,3 à 1 Mio.

### Candidat 8 · Talus et courbes de défauts (FERMÉ par la Proposition 1 et par M1)

Talus supprime les falaises de la courbe de défauts d'un LRU. La falaise de notre LRU global est à
N = (L − 1)k = 140 emplacements (`mesures/gpt-oss.md` § 7, Proposition 1) ; le budget de la base est 323, au-delà.
M1 : LRU à 323 = 0,39 à 0,51, LFU 0,51 à 0,61 : l'écart se prend par la fréquence, que Talus n'ajoute pas.

---

## 4. Ce qui est fermé et que je n'ai pas rouvert

Graine, S\*, duplication, hebbien, spectres, garde tropicale (globale et à indices multiples), treillis
(QTIP reproduit, S\* gagne en erreur d'expert et égale en KL), sparsité d'entrée par jeton sur un modèle
dense de 135 M (mais voir la remarque suivante), borne de Shannon dans le domaine des poids (0,47 bit sous la
frontière, atteignable seulement par un quantificateur autre que scalaire, `genome/01-eclaireur.md` § 3).

**Une remarque sur la sparsité d'entrée** (TEAL, CATS) : `fondations/05-sparsite.md` § 5.5 la dit incompatible
avec la vérification spéculative (union 0,90 à n = 4). M2 retire la raison : sans spéculation, n = 1, et le
masque par jeton lit 75 % des colonnes à 25 % de sparsité pour +2,1 % de perplexité sur SmolLM2-135M. Mais
la physique du disque la referme à moitié : sauter des bandes de colonnes de 43 Kio coûte 0,2 à 0,7 Go/s
(petits blocs aléatoires), ce qui efface le gain ; il faudrait des plages ≥ 1 Mio, donc un masque grossier,
donc proche du « masque commun » dont la qualité s'effondre dans leur tableau. Non mesuré sur gpt-oss ; je ne
l'ai pas classé parmi les huit, et je ne le signale pas comme une piste.

---

## 5. Ce qui pourrait être faux

- **T2bis a manqué son seuil de 0,0031.** Le verdict de M1 est donc « non concluant » au sens que j'avais
  déclaré, et ma lecture (« la barre n'était pas atteignable ») est une lecture, pas le verdict déclaré.
- **LFU\* est généreuse** (demi-vie choisie sur la trace de test) : cela *réduit* Δ ; contre la demi-vie 8
  du projet, Δ serait plus grand (dialogue : 0,5878 contre 0,556, soit +0,032). Je ne l'ai pas retenu comme
  verdict parce que le seuil était déclaré contre la meilleure.
- **Les traces de lecture sont du texte lu**, non de la génération ; la génération n'a que 256 jetons et un
  démarrage à froid. Le routage dépend du chemin de calcul (81,1 % de choix identiques entre carte et
  processeur sur le 120b, `mesures/gpt-oss.md` § 9).
- **Le prédicteur est le plus simple possible** (une régression logistique sur onze traits) ; un prédicteur
  qui voit le routage du jeton courant n'est pas mesuré.
- **M2 est sans cache** et suppose les octets proportionnels à l'union ; le tableau du gain suppose une
  acceptation i.i.d. et un coût de brouillon constant c = 0,66 (le −34 % de 07, sur le 120b seulement).
  Un cache partagé entre brouillon et vérification, ou un brouillon plus petit que le mode rapide, sort
  de ce calcul.
- **Candidat 1** : l'article n'est lu que par son résumé, sur d'autres modèles ; la borne de M3 ne vaut que
  pour l'échange 4e-5e et le 20b ; la linéarisation de la KL est une hypothèse.
- **Le calcul jouet de Maslov** suppose une densité de marge plate et un saut égal : c'est un ordre de
  grandeur, pas une mesure.
- Les ± et les écarts de M1 n'ont pas d'intervalle : une seule graine pour les mélanges, une passe par
  cas ; les écarts de 0,01 sont dans l'ordre de grandeur de la dispersion entre traces.

---

## 6. Message à la session principale

Un seul, envoyé le 2026-10-27 après les trois mesures : la piste du candidat 1, avec ses réserves. Aucun
autre message : les résultats M1 et M2 sont des fermetures, non des pistes.

## 7. Fichiers

- Seuils et amendements : `mesures/mimetisme/mathematiques/00-seuils-declares.md`.
- Outils : `outils/mimetisme/mathematiques/{m1_m2.py, t2bis.py, plafond_speculatif.py, maslov_jouet.py}`.
- Journaux : `mesures/mimetisme/mathematiques/{m1_m2.json, m1_m2.log, temoins.json, t2bis.json,
  m3_marges_20b.json, plafond_speculatif.json, maslov_jouet.json}`.
- Reproduire : extraire `traces-120b.tar.xz` dans un dossier, puis
  `python -I outils/mimetisme/mathematiques/m1_m2.py --traces <dossier> --sortie mesures/mimetisme/mathematiques`
  (283 s, un fil, priorité sous la normale).
