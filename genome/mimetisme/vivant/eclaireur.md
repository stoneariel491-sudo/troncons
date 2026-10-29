# Éclaireur du vivant : ce que le monde fait, ce que nos traces en disent

Rôle : éclaireur, domaine « le vivant à toutes les échelles » de la consigne de Stone du 2026-10-26
(« mimétisme absolu, peu importe les échelles »). Date : 2026-10-27. Étiquettes : **[mes.]** mesuré ici,
outil et journal commités ; **[calc.]** calculé ici sur des mesures commitées ; **[lu]** source lue (résumé ou
texte, dit pour chacune) ; **[mém.]** de mémoire, non relu ; **[hyp.]** hypothèse dite.

Fichiers : seuils et témoins `genome/mimetisme/vivant/seuil-declare.md` (commité avant chaque calcul,
huit ajouts datés) ; outils `outils/mimetisme/vivant/` ; mesures et journaux `mesures/mimetisme/vivant/`.
Aucun fichier de modèle n'a été ouvert (le verrou de la carte était posé : séance de disque en cours) ;
tout ce qui suit vient des traces de routage de `mesures/localite-gpt-oss/` (gpt-oss-20b : 24 couches,
32 experts ; gpt-oss-120b : 36 couches, 128 experts ; k = 4 ; cinq genres de texte en lecture, 2 400 à 2 900
jetons chacun, sauf wiki 708) et des KL par position du lot B.

## D'où on part, où on va

**Au départ** : la frontière sans perte à 3,68 bits, le mode rapide (génome synonyme) à 2,64 bits mais
dont les gains de vitesse annoncés ont été barrés par le juge (×1,28 sur le 120b, ×0,94 sur le 20b contre un
fichier exact lu à la même vitesse, JUGEMENT-construction § 7) ; la graine, la duplication, l'hebbien, les spectres et la garde
tropicale globale fermés (05-synthèse § 2 et 3, pistes/tropicale) ; un disque qui limite (2,82 Go/s) et
des octets par jeton égaux à défauts de cache × 13,25 Mo (gpt-oss.md).
**Ce que ce document établit** : quels mécanismes du vivant, parmi dix bancs sur les traces, se traduisent en
un objet du pipeline ET se jugent sur les traces existantes ; lesquels tombent par les nombres ; l'un tient
(le cache à mémoire longue). **Ce qui reste** : § 5 (les expériences qui exigent le moteur ou la carte).

## 0. En bref

1. **Le seul résultat qui tient** est un réglage de cache, et il est modeste dans son principe : une
   fréquence d'usage à décroissance lente (demi-vie 32 à 128 jetons choisie sur les autres genres) retire
   **12,5 à 21,4 % des défauts contre LRU**, sur 5 genres sur 5, aux 4 budgets mesurés [mes.] ; sur le 120b
   à 20 % d'experts en cache, défauts 0,227 → 0,183 (Belady : 0,117), 40 % de l'écart LRU–Belady, soit
   ≈ +24 % de jetons par seconde si le disque limite [calc.]. L'activation de base d'ACT-R (Anderson et
   Schooler 1991, mémoire humaine en loi de puissance), posée sans réglage, fait la même chose (−13 à −20 %
   contre LRU) mais **pas mieux qu'un LFU bien réglé** : la loi de puissance n'ajoute rien, elle évite le
   réglage. Contre le LFU de demi-vie 8 de l'instrument, le gain tombe à 5 % (10 % d'experts en cache) et 14 %
   (20 %) : mon seuil déclaré (10 % contre le meilleur connu, aux deux budgets) **tombe** au sens strict.
   On pourrait croire que le gain vient d'une lecture de la séquence : le témoin de cassure (ordre des jetons
   mélangé) donne un gain **plus grand**, 20,9 % à 20 % du 120b ; c'est de la popularité à mémoire longue,
   pas de l'anticipation.
2. **Quatre idées du vivant tombent par les nombres sur gpt-oss** : la fovéation (précision graduée selon le
   poids de mélange : les poids sont presque plats, 0,34 / 0,25 / 0,21 / 0,18 en moyenne, entropie 1,93 bit sur
   2 ; 0,01 à 0,02 % des défauts sont abandonnables à 2 % de masse perdue) ; l'allocation inter-couches par valeur
   marginale (Charnov : 0,7 à 3,6 % de défauts en moins, seuil 10 %) ; la résidence partielle « polymérase
   en pause » (lire les bases de tous les experts, le complément au besoin : de 4 à 100 % de **plus** d'octets,
   prédiction écrite avant) ; la modulation par la surprise du jeton précédent (Spearman −0,09 à −0,17 avec la
   perte du mode rapide).
3. **Deux faits nouveaux sur gpt-oss**, utiles au-delà du cache : le routage de toutes les couches est
   fortement structuré (2,6 à 3,9 fois moins de composantes pour porter la moitié de l'énergie que sous
   indépendance des couches : K50 = 16 à 26 sur 768 au 20b, 43 à 85 sur 4 608 au 120b) ; et vérifier γ jetons
   d'un coup relit presque autant d'experts (l'union de 4 jetons pèse 0,69 × 4 jetons au 120b), si bien que
   le décodage spéculatif ne **rend** des octets qu'avec une acceptation α ≥ 0,9 (−21 % à γ = 4 ; avec
   α = 0,7 on lit plus qu'au pas simple) [calc. sur mes., sans cache, optimiste].
4. **Prédire ne fait pas gagner d'octets au cache.** Un prédicteur de synergies appris hors ligne (sur d'autres
   genres) devine mieux le jeton suivant que la popularité en ligne sur 4 genres sur 5 (+2 à +7 points de
   rappel), s'effondre sur le code (−14 à −25 points) et **tombe** au seuil (5 points) ; mis à la tâche
   d'évincer, il **n'ajoute rien** à un LFU bien réglé (E-J2 : −0,2 à +0,8 % de défauts). La mémoire
   épisodique dans la session (le cosinus que le circuit de la mouche approche) fait mieux aux petits budgets
   (+4 à +7 points de rappel, +20 sur le code) mais n'est tenue au seuil nulle part de façon complète (E-K), et
   mise à la tâche d'évincer (E-L) elle ne retire que 0,2 à 1,4 % de défauts de plus qu'un LFU réglé (4,0 % au
   plus, sur le code) : évincer demande un ordre parmi les experts présents, que la popularité donne déjà.
5. **La queue du préremplissage** passe son seuil de proxy sur le 120b à 512 jetons : 18 à 24 % des experts
   touchés (médiane 22 %) ne reçoivent que 1 ou 2 jetons (≈ 14 % de tous les experts, ≈ 7,5 Go à ne pas lire par invite) pour
   1,2 % des affectations ; il faut une KL du moteur pour le dire. Voisin de MoE-Spec (2026) qui élague la
   queue à la vérification.
6. **Signal à Stone** : un message envoyé à la session principale (cache à mémoire longue), aucun autre.

## 1. Ce que j'ai lu

Recherches web du 2026-10-26 et 27. « Résumé » = page de résumé ou notice lue, pas le texte entier.

| Source | Ce que j'en ai tiré | Lu |
|---|---|---|
| Dasgupta, Stevens, Navlakha, *A neural algorithm for a fundamental computing problem*, Science 358:793–796 (2017-11-10) ; préimpression https://www.biorxiv.org/content/10.1101/180471v1 | Le circuit olfactif de la mouche : 50 neurones d'entrée → 2 000 cellules de Kenyon par projection binaire clairsemée (chacune échantillonne ~6 entrées), puis « le gagnant prend tout » (≈ 5 % actives). Sur SIFT à longueur 4, la sélection au hasard donne 17,7 % de précision moyenne contre 32,4 % avec le gagnant-prend-tout. | texte de la préimpression (PDF) |
| Anderson et Schooler, *Reflections of the environment in memory*, Psychological Science 2(6):396–408 (1991), https://www.psychologicalscience.org/journals/psychological-science/j.1467-9280.1991.tb00174.x | La probabilité qu'un élément serve suit, dans le journal, la parole des parents, le courrier, les mêmes lois de fréquence et de récence que la mémoire humaine ; la mémoire est adaptée à ces statistiques. | résumé et notices |
| Mitchell et al., *Adaptive prediction of environmental changes by microorganisms*, Nature 460:220–224 (2009-07), https://cris.huji.ac.il/en/publications/adaptive-prediction-of-environmental-changes-by-microorganisms/ | *E. coli* et la levure pré-induisent les gènes du second sucre (maltose) quand le premier (lactose) arrive, l'ordre naturel étant câblé dans le réseau de régulation ; la réponse se perd si on ne l'entretient pas. Commentaire de Cooper : possible effet de bord. | résumé et commentaire |
| Charnov, *Optimal foraging, the marginal value theorem*, Theoretical Population Biology 9:129–136 (1976) | On quitte un site quand le taux de gain tombe au taux moyen. | notices secondaires |
| Core et Adelman, *Promoter-proximal pausing of RNA polymerase II: a nexus of gene regulation*, Genes & Development 33:960–982 (2019), https://genesdev.cshlp.org/content/33/15-16/960 | La polymérase s'arrête après avoir démarré, jusqu'au signal de libération : gènes amorcés. | résumé |
| Yu et Dayan, *Uncertainty, neuromodulation, and attention*, Neuron 46(4):681–692 (2005) ; version NeurIPS 2002 https://papers.neurips.cc/paper/2002/hash/758a06618c69880a6cee5314ee42d52f-Abstract.html | L'acétylcholine suit l'incertitude attendue, la noradrénaline l'incertitude inattendue (changements de contexte non signalés). | résumés |
| Steele, Tresch, Perreault, *The number and choice of muscles impact the results of muscle synergy analyses*, Front. Comput. Neurosci. 7:105 (2013), https://pmc.ncbi.nlm.nih.gov/articles/PMC3737463 | Synergies motrices : V = W × C, W (muscles × synergies), C (activations). Tresch, Cheung, d'Avella (2006) pour les algorithmes [mém.]. | résumé |
| Xue et al., *MoE-Infinity*, arXiv:2401.14361 (2024) https://arxiv.org/abs/2401.14361 | Matrices d'activation des experts par requête, comparées par cosinus à une collection pour guider préchargement et cache. | notice de recherche |
| HOBBIT (auteurs non relevés), arXiv:2411.01433 (v1 2024-11-03, v2 2024-11-06) https://arxiv.org/abs/2411.01433 | Remplace les experts « moins critiques » manqués par une version basse précision ; jusqu'à 9,93× contre l'état de l'art. | résumé |
| Edge0, *The Other Half of the Memory Wall*, arXiv 2609.18063 (2026-09-16) ; https://raw.githubusercontent.com/Edge0-AI/Edge0/main/README.md (Apache-2.0) | Experts depuis le SSD ; une tête « pré-routeur » entraînée prédit le routage du pas suivant ; adaptateur de récupération ; +59 % de débit annoncé. | README entier, résumé de l'article |
| McDanel et al., *MoE-Spec*, arXiv 2602.16052 (2026-02-17) https://arxiv.org/abs/2602.16052 | Plafond d'experts par couche à la vérification, on abandonne la queue ; +10 à 30 % contre EAGLE-3. | résumé |
| Xie et al., *EcoSpec*, arXiv 2607.12696 (2026-07-14) https://www.alphaxiv.org/abs/2607.12696 | « Dispersion d'experts » : des brouillons probables routent vers des experts disjoints ; on ajoute le coût d'experts à la sélection du brouillon ; jusqu'à 1,62×. | résumé |
| *Any-Precision LLM* (auteurs [mém.] : Park et al.), arXiv 2402.10517 ; SpecPrefetch 2607.24787 ; Fate 2502.12224 ; DraftExpert 2607.24434 | Plans de bits emboîtés ; préchargement entre couches ; spéculation sur MoE hors mémoire. | notices de recherche seulement |

Ce que je n'ai pas pu lire : le texte entier d'Anderson et Schooler, de Mitchell, de Charnov, de Yu et
Dayan (résumés seulement) ; les fiches PubMed refusaient les requêtes (cookies). Les nombres de ces sources
ne sont donc pas repris ; seules leurs idées le sont, et dites telles.

## 2. Protocole

Seuils, témoins et prédictions écrits dans `seuil-declare.md` et commités **avant** chaque calcul
(commits b7ace2d, c59685e, fdd20fb, 9278694, 69d9eaf, 8708999, f91b93a, ec9b316, ab21386). Règle commune : un mécanisme de cache
vaut s'il retire **≥ 10 % des défauts** (trois fois la règle des 3 % de 06-modeles § 7.5) contre le **meilleur
des deux politiques gratuites connues** (LRU, LFU à demi-vie 8), de même signe sur ≥ 4 genres sur 5. Les
défauts, pas le taux de succès : sur disque limitant, les octets lus par jeton valent défauts × 13,25 Mo.

Témoins tenus (`temoins.json`) : mon LRU égale `cache_lru` de l'instrument à 10⁻¹² (W1) ; causalité, les
décisions sur une moitié de trace égalent celles de la trace entière (W3) ; routage i.i.d. : aucune
politique ne gagne (W4) ; abandon de masse (W5), queue (W6), union (W7), rang planté (W8), allocation uniforme
(W9). **Cassures** (`temoins-casses.log`) : chaque témoin tombe quand on force sa condition. Le témoin de
causalité était **mou** au premier essai (la fuite ne regardait qu'un jeton) ; corrigé avant les bancs.

## 3. Résultats

### 3.1 E-A et le contrôle de demi-vie : l'éviction à mémoire longue

Moyennes sur 5 genres, succès d'un cache par couche de C experts [mes., `ea-brut.json`] :

| | C | LRU | LFU8 | ACT-R d = 0,5 | ASSOC | Belady |
|---|---|---|---|---|---|---|
| 20b | 6 (19 %) | 0,621 | 0,665 | 0,666 | 0,669 | 0,718 |
| 20b | 10 (31 %) | 0,792 | 0,822 | 0,827 | 0,828 | 0,878 |
| 120b | 13 (10 %) | 0,585 | 0,636 | 0,648 | 0,650 | 0,742 |
| 120b | 26 (20 %) | 0,773 | 0,791 | 0,816 | 0,814 | 0,883 |

Gain relatif de défauts contre le meilleur de {LRU, LFU8}, médiane des 5 genres : ACT-R 0,0 / 3,5 / 4,1 / 13,4 % ;
ASSOC 0,7 / 4,4 / 3,9 / 11,6 % (même ordre de lignes). **Verdict au seuil déclaré : tombe** (la médiane de 10 %
n'est tenue qu'à 20 % du 120b ; sensibilité d = 0,3 et 0,8 : 11,7 et 13,9 % à ce budget, ACT-R n'est donc pas
sensible à d).

**Cassure** (ordre des jetons mélangé) : ACT-R 20b/6 1,8 %, 20b/10 6,8 %, 120b/13 8,1 %, 120b/26 20,9 % ;
ASSOC 1,6 / 6,4 / 6,6 / 18,3 %. Le témoin déclaré (le gain d'ASSOC doit tomber sous le tiers) **tombe** :
ni ASSOC ni ACT-R ne lisent la séquence ; ils comptent. Une popularité stationnaire (ordre mélangé) est le
cas où un compteur à mémoire longue est optimal, d'où un gain plus grand.

**Contrôle non déclaré avant, dit tel** (`ablation_demivie.py`) : LFU de demi-vie h ∈ {4 … 512}, h choisi sur
les quatre autres genres (32 à 128 sauf code 64 à 128), évalué sur le genre testé. Gain contre le meilleur
de {LRU, LFU8}, médiane : LFU(h) 0,9 / 4,8 / 5,2 / 14,4 % ; ACT-R 0,0 / 3,5 / 4,1 / 13,4 % ; ACT-R contre
LFU(h) −0,4 / −0,3 / −0,3 / +0,1 %. **ACT-R égale un LFU bien réglé.** Contre LRU, LFU(h) retire **12,5 / 18,7 /
17,5 / 21,4 %** des défauts (5 genres sur 5 à chaque budget ; code le plus faible, 10,8 à 13,7 %)
[mes., `lfu-longue-memoire-contre-lru.json`].

### 3.2 E-B : allocation par valeur marginale (Charnov 1976) : tombe

Sac à dos exact sur les courbes de succès LRU de chaque couche apprises sur les quatre autres genres, même
total d'emplacements : défauts en moins contre l'allocation uniforme, médiane 2,0 / 1,1 / 0,7 / 3,6 % (20b 6
et 10, 120b 13 et 26), seuil 10 %. Les courbes des couches se ressemblent trop pour qu'un déplacement
rapporte [mes., `eb-verdict.json`]. Le témoin de permutation de la première passe était vide (une inversion
d'indice redonnait l'allocation vraie), trouvé en relisant, corrigé dans le code ; les chiffres ci-dessus
n'en dépendent pas (gains réels), le verdict non plus.

### 3.3 E-C : fovéation selon le poids de mélange : tombe, par la forme des poids

Poids de mélange moyens par rang 0,36 / 0,25 / 0,21 / 0,18 (120b : 0,35 / 0,25 / 0,21 / 0,19) ; médiane du
plus petit poids 0,18 (20b) et 0,19 (120b) ; entropie moyenne 1,92 bit sur 2 ; P(plus petit poids ≤ 5 %) =
0,20 % (20b) et 0,15 % (120b) ; P(plus grand ≥ 90 %) = 0,01 % [mes., `ec-poids-stats.json`]. La part des
défauts du LRU abandonnable à 2 % de masse perdue : médiane 0,012 à 0,023 %, seuil 15 % [mes., `ec-verdict.json`].
Sur gpt-oss, le critère d'importance de HOBBIT ou de l'abandon à la MoE-Spec ne peut pas être le poids de
mélange : il n'y a presque aucune différence à exploiter. (La contribution réelle d'un expert est son poids
fois la norme de sa sortie ; la norme demande le modèle, § 5.)

### 3.4 E-D : synergies de routage : tient (descriptif)

Dimension effective K50 (composantes portant 50 % de l'énergie) de la matrice jetons × (couches × experts),
contre un nul qui tire chaque couche indépendamment avec les mêmes fréquences [mes., `ed-verdict.json`] :
20b K50 = 26 / 19 / 22 / 21 / 16 contre 92 / 72 / 80 / 77 / 62 (rapport 3,5 à 3,9) ; 120b 77 / 76 / 85 / 78 / 43
contre 284 / 211 / 219 / 210 / 128 (rapport 2,6 à 3,7). Nul contre nul : rapport 1,00 (0,996 à 1,016).
Les routages des couches d'un même jeton ne sont pas indépendants : c'est la base du prédicteur de § 3.8.

### 3.5 E-E : la queue de Pareto du préremplissage : proxy tient pour le 120b à 512

Fenêtres de P jetons, par couche : « queue » = experts touchés par ≤ 2 jetons. Médiane des 5 genres
[mes., `ee-verdict.json`] :

| | P | experts touchés / tous | queue / touchés | affectations en queue |
|---|---|---|---|---|
| 20b | 128 | 69 % | 16 % | 0,96 % |
| 20b | 512 | 79 % | 10 % | 0,17 % |
| 120b | 128 | 47 % | 38 % | 6,1 % |
| 120b | 512 | 64 % | 22 % | 1,2 % |

Seuil (queue ≥ 20 % des touchés pour ≤ 2 % des affectations) : tenu pour le 120b à 512 seulement. À 512
jetons, le préremplissage lit déjà seulement 64 % des experts (≈ 34 Go des 53,6 Go d'experts) ; sauter la queue en épargne
≈ 14 % de tous (≈ 7,5 Go, ≈ 2,7 s à 2,82 Go/s) [calc.]. Mais 1,2 % des affectations, c'est au plus 4,8 % des couples
(jeton, couche) qui perdent l'un de leurs 4 experts : la KL est inconnue, **c'est un proxy**.

### 3.6 E-F : l'union sur γ jetons : borne sur la spéculation

Fraction de lectures d'une vérification de γ jetons par rapport à γ pas simples, U(γ)/(γ·k), moyenne des
genres [mes., `ef-brut.json`] : 120b 1,00 / 0,84 / 0,76 / 0,70 / 0,65 / 0,61 / 0,58 / 0,55 (γ = 1 … 8) ; 20b
1,00 / 0,75 / 0,62 / 0,54 / 0,48 / 0,44 / 0,40 / 0,37. Avec un brouillon qui ne lit pas le disque, E jetons
acceptés par passe (1 − α^{γ+1})/(1 − α), les octets relatifs par jeton généré valent U(γ + 1) / (k E)
[calc. sur mes., sans cache, sans les lectures des brouillons rejetés, donc optimiste] : 120b, α = 0,9 : 0,89 /
0,84 / 0,81 / 0,79 pour γ = 1, 2, 3, 4 ; α = 0,8 : 0,94 / 0,93 / 0,94 / 0,96 ; α = 0,7 : 0,99 / 1,04 / 1,10 /
1,16. 20b, α = 0,8, γ = 4 : 0,72. C'est le ρ du lemme B2, chiffré : sur le 120b, une vérification groupée ne
gagne que si α ≥ 0,9, et plus γ grandit plus l'union pèse (dispersion d'experts de EcoSpec).

### 3.7 E-G, E-H : deux idées du vivant tuées par un chiffre

**E-G** (polymérase en pause, Core et Adelman 2019) : lire en RAM les bases (r = 2,64 / 3,68 = 0,717 de
l'expert) de tous les experts qui tiennent, le complément au besoin. Octets B / A (A = experts entiers) :
1,04 à 2,02 selon le budget et le genre, jamais sous 1 [mes., `eg.json`], prédiction écrite avant : « tombe ».
Raison : si le taux de succès h est concave, le gain en succès est repris par le complément à relire.
**E-H** (Yu et Dayan : la surprise fait basculer en mode attentif) : la surprise du jeton précédent sous le
modèle ne prédit pas où le mode rapide perd de la KL : Spearman −0,09 (R1) et −0,17 (fenêtres neuves),
les 20 % de positions de plus forte surprise portent 14 % de la KL (hasard : 20 %) ; même le signal parfait
(la KL elle-même) ne met que 66 à 69 % de la KL dans 20 % des positions : la perte du mode rapide est
diffuse [mes., `eh.json`].

### 3.8 E-I et E-J : un prédicteur de synergies, hors ligne

Rappel@C des 4 experts du jeton t + 1 à partir de l'état du jeton t, appris sur les **quatre autres genres**
(ACP à 64 composantes de l'état 0/1 de toutes les couches, ridge vers l'état suivant) [mes., `ei-brut.json`].
Écart du meilleur de {P4, P4m} au meilleur de {popularité en ligne, association de couche}, aux deux
budgets : 20b (code, dialogue, prose-en, prose-fr, wiki) −13,7 / +3,9 / +5,4 / +2,5 / +7,1 points à C = 6 ;
120b −22,9 / +2,8 / +4,5 / −3,3 / +6,6 à C = 13. Médiane +1,8 à +3,9 points, seuil 5 : **tombe**. Témoin de
mélange des paires d'apprentissage : l'écart devient négatif (−7 à −52 points), et K = 1 est inférieur à K = 64 ;
le prédicteur lit donc bien la séquence et la structure entre couches. Le code ne transfère pas (−14 à −25
points) : ses experts diffèrent de ceux du langage naturel.
**E-J** (éviction SYN2 : prédicteur de synergies à deux jetons + popularité de demi-vie 8) : défauts en moins
contre le meilleur de {LRU, LFU8, P1} (médianes) 0,3 / 2,7 % (20b, C = 6 et 10), 3,0 / 7,7 % (120b, C = 13 et 26),
seuil 10 % : **tombe**. Témoin : score constant = P1 exactement (écart 0) ; mais l'apprentissage sur paires
mélangées donne encore +5,0 % au 120b/26 : une part du gain n'est pas de la séquence. **E-J2** (popularité de
demi-vie 64, déclarée après le contrôle de § 3.1, prédiction « tombe » écrite avant) : −0,2 / −0,1 / −0,2 / +0,8 % :
**le prédicteur de synergies n'ajoute rien à un LFU bien réglé** (et fait perdre 4 à 15 % sur le code) [mes.,
`ej-brut.json`, `ej-hl64-brut.json`]. Le gain apparent de E-J était de la mémoire longue réintroduite.

### 3.9 E-K : la mémoire épisodique clairsemée de la mouche

Dasgupta, Stevens et Navlakha : un circuit à expansion 40 fois et « gagnant prend tout » donne des étiquettes
dont le recouvrement approche la ressemblance, pour retrouver des odeurs semblables. Traduction testée,
au cosinus exact (borne favorable à toute version hachée) : retrouver dans la session les jetons passés dont
l'état de routage ressemble au jeton courant (k = 8), lire ce qui les a suivis. Écart de rappel@C,
max(KNN, KNNm) − max(P1 de demi-vie 64, P3), médiane des 5 genres [mes., `ek-verdict.json`] : **20b C = 6 : +7,2
points** (5 genres sur 5 : +12,4 / +7,2 / +7,0 / +5,3 / +10,1), C = 10 : +4,3 ; **120b C = 13 : +4,8** (code +20,0),
C = 26 : −0,3 (2 genres sur 5). Verdict strict au seuil de 5 points aux deux budgets : **tombe** (tenu au seul
20b/6). Témoins : successeurs tirés au hasard, l'écart devient −6 à −23 points ; k = 1 est inférieur à k = 8.
Le **code**, que le prédicteur hors ligne ne devine pas (−14 à −25 points), est le genre où la mémoire épisodique
gagne le plus (+8 à +20 points) : elle apprend dans la session, sans entraînement. Aux 20 % d'experts du 120b la
popularité suffit (rappel 0,82 à 0,85).
**E-L** (éviction EPI : mémoire épisodique au pas de deux jetons + popularité de demi-vie 64) : défauts en moins
contre le meilleur de {LRU, LFU8, P1(64)}, médianes 0,2 / 1,4 / 0,7 / 0,8 % (20b C = 6 et 10, 120b C = 13 et 26),
4 à 5 genres sur 5 positifs, code 1,8 à 4,0 % ; seuil 10 % : **tombe** (prédiction écrite avant : « au plus 3 à
5 % »). Témoins : successeurs au hasard −1,6 à 0,0 % ; score constant = P1(64) à 0 près ; k = 1 inférieur à k = 8 au
20b/10 et au 120b. Pourquoi le rappel ne se change pas en octets : évincer ne demande qu'un **ordre** parmi les
C experts présents, que la popularité fournit déjà ; le rappel@C demande un ensemble de tête parfait. Les 4 à 7
points de rappel gagnés profiteraient à un **préchargement** (deviner ce qu'on va demander), pas à l'éviction
[mes., `el-verdict.json`].

## 4. Candidats classés

« Neuf » = pas fait, à ma connaissance, pour gpt-oss ou pour un cache d'experts sur disque ; « vu » = le monde
l'a déjà fait. **Honnêteté d'abord : aucune idée de ce domaine n'est neuve au sens de la littérature** (LFU et
LRFU à décroissance, collections d'activations de MoE-Infinity, élagage de queue de MoE-Spec, bits emboîtés
d'Any-Precision existent). Ce qui est neuf ici, ce sont des **mesures sur gpt-oss** et le tri de ce qui
survit. Rang par ce que la mesure permet de dire :

1. **Fréquence à mémoire longue** (ACT-R, loi de puissance de la mémoire) : seul résultat qui tient, vu
   (LFU/LRFU), neuf comme réglage mesuré pour ce cache : −12,5 à −21,4 % de défauts contre LRU.
2. **Mémoire épisodique clairsemée dans la session** (circuit olfactif de la mouche) : +4 à +7 points de
   rappel aux petits budgets, +20 sur le code ; ne change rien à l'éviction (E-L), à essayer pour le
   **préchargement** ; vu sous la forme de MoE-Infinity (par requête, sur un corpus).
3. **Queue de Pareto du préremplissage** : proxy tenu (120b, 512 jetons : ≈ 14 % des experts pour 1,2 % des
   affectations) ; attend une KL ; vu à la vérification (MoE-Spec), peu vu au préremplissage [mém.].
4. **Prédicteur de synergies hors ligne** : signal réel, tombe au seuil, n'ajoute rien à un LFU réglé ; vu
   (Edge0, Fate, MoE-Infinity), neuf comme transfert entre genres (le code ne transfère pas).
5. **Fovéation par contribution réelle** (poids × norme de sortie) sur un mode rapide **emboîté** : non
   mesurable sans le modèle ; vu (HOBBIT, Any-Precision).
6. **Spéculation et union des experts** : borne chiffrée (E-F), fermée sauf α ≥ 0,9 ; vu (EcoSpec, MoE-Spec).
7. **Tués par les nombres** : fovéation par poids de mélange, allocation de Charnov, polymérase en pause,
   modulation par la surprise (§ 3.2, 3.3, 3.7).

La liste structurée rendue avec ce document porte, pour chacun, mécanisme, source, traduction, expérience,
données, gain et ce qui est fermé.

## 5. Ce que les traces ne permettent pas, et qui attend la carte ou le moteur

- Le cache à mémoire longue **dans le simulateur du moteur** (Tome II), en génération et non en lecture,
  avec la demi-vie choisie hors du texte jugé, contre LRU et SLRU de J1+ : c'est ce qui décide.
- La **contribution réelle** des experts (poids × norme de sortie), seule base honnête d'une fovéation sur
  gpt-oss ; la KL du préremplissage sans la queue ; l'entropie conditionnelle H(exact | rapide) pour un mode
  rapide emboîté. Ces trois demandent le modèle.
- La même mesure de rappel avec des états cachés (et non des routages) comme entrée : c'est ce que fait Edge0
  avec sa tête entraînée ; le résidu de ℓ route déjà ℓ + 1 dans le plan J1+.

## 6. Ce qui pourrait être faux

- **Traces de lecture, cinq genres, 2 400 à 2 900 jetons** : la génération (texte choisi par le modèle) et
  un autre genre peuvent déplacer les demi-vies et les ordres de grandeur. La trace wiki n'a que 708 jetons.
- **Cache par couche** (l'instrument de l'étude 04) et non le cache partagé ou la file de J1+ ; les budgets
  de 10 et 20 % sont par couche, pas ceux de la machine.
- **Pas de coût d'état ni de calcul** : un LFU à demi-vie coûte un compteur par expert et par couche (4 608
  flottants au 120b), négligeable ; le prédicteur de synergies coûte une projection de 4 608 × 64 par jeton.
- **Le critère « contre le meilleur connu »** dépend de ce qu'on appelle connu : contre LRU, le réglage passe
  largement ; contre LFU8 (mal réglé), il tombe. J'ai gardé le critère déclaré pour le verdict et dit l'autre.
- Le message envoyé à la session principale disait ACT-R « −12 à −18 % » contre LRU ; le chiffre exact est
  −13 à −20 % (médianes 12,8 / 17,6 / 16,5 / 20,0 %).
- **Les sources du vivant** sont lues en résumé : la fidélité de l'analogie (loi de puissance de la mémoire,
  anticipation bactérienne, amorçage de la polymérase) n'est pas jugée ; seul le mécanisme traduit se mesure.
- **E-F** suppose le brouillon gratuit et sans lectures perdues : c'est une borne optimiste ; la réalité est pire.
- Les p-valeurs ne sont pas calculées : cinq genres ne sont pas cinq échantillons indépendants (les jetons
  d'un texte partagent leur passé). La règle « même signe sur 4 genres sur 5 » est un garde-fou, pas un test.

## 7. Techniques essayées (pour RECETTES.md)

- **Marche** : déclarer seuils et prédictions avant, commiter ; un contrôle de réglage (demi-vie choisie
  sur les autres genres) avant de croire qu'un mécanisme « inspiré » bat son parent ordinaire ; un témoin de
  cassure par l'ordre mélangé, qui a montré ici que le gain n'était pas séquentiel.
- **Échoue** : fovéation par poids de mélange ; allocation inter-couches ; résidence partielle ; surprise
  comme signal ; prédicteur de synergies hors genre sur le code.
- **Pièges** : un témoin de causalité qui ne fuit que d'un jeton ne tombe pas ; une permutation remise dans le
  mauvais ordre rend le témoin vide ; sérialisation JSON des flottants numpy (une passe de dix minutes
  perdue, `ei-premiere-passe-plantee.log`) ; un tableau de prédictions à T − 2 lignes indexé à T − 1.
