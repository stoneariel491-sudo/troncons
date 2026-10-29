# P3, routeur biaisé EN LIGNE dans le moteur : mécanisme, grandeurs, seuils, témoin et cassure, déclarés avant toute mesure (2026-10-27)

Écrit avant : l'écriture du moindre octet de code du moteur pour cette option, et avant toute passe du moteur avec biais. Aucune
KL, aucun compte de défauts, aucune vitesse du moteur biaisé n'existe au moment où j'écris. Ce qui est lu pour fixer ceci :
`SOCLE.md`, `SESSION-SUIVANTE.md`, `genome/mimetisme/P3/resultat.md`, `resultat-etage-B.md`, `resultat-N238.md`, `JUGEMENT-N238.md`,
`resultat-temoin-b0.3.md`, `mesures/mimetisme/P3/00-seuils-declares.md`, `03-critere-marge-declare.md`, `04-ensembles-N238.md`, et le code du
moteur : `moteur/crates/trc-ordo/src/lib.rs` (`Moteur::pas`, l'appel `cache.demander`), `trc-modele/src/lib.rs` (`debut_couche`),
`trc-noyaux/noyaux/passe.cuh` (`routeur_topk`), `trc-cache/src/lib.rs` (`emplacement_de`), `bins/troncons/src/main.rs`.
Source de la règle : Skliar et al., arXiv 2412.00099 v2 (biais additif sur le logit des experts en cache, poids calculés sur les logits non
biaisés), déjà lue et citée dans `00-seuils-declares.md` § 0.

## 1. Ce que l'on construit, et où

Le moteur (`troncons`, 20b) choisit les 4 experts d'une couche sur la carte : `Modele::debut_couche` lance le noyau `routeur_topk` (top-4 des
32 logits, softmax des 4), l'hôte lit les indices dans la boîte aux lettres, puis appelle `cache.demander(couche, indices, t)`. L'état
« expert présent en VRAM » est celui du cache (`trc-cache`, `Cache::emplacement_de((couche, expert))`), global sur les 24 × 32 experts, LRU.

**Le biais** : pour la couche ℓ du pas courant, l'hôte construit un vecteur `b[e] = β` si l'expert `(ℓ, e)` occupe un emplacement de VRAM
juste avant `demander(ℓ, …)`, `0` sinon (c'est exactement « le contenu du cache juste avant ce groupe » de `00-seuils-declares.md` § 2, mais
cette fois sur la trajectoire réelle du moteur biaisé, pas sur celle du moteur exact : c'est ce qui lève la limite « boucle ouverte »).
Il l'envoie à la carte (copie asynchrone depuis un tampon épinglé, sur le flux de calcul, juste avant le routeur). Un **second noyau**,
`routeur_topk_biais`, choisit les 4 experts par le score `logit + b` ; les poids de mélange sont le softmax **des logits non biaisés** des
quatre choisis (règle de l'article) ; les quatre choisis sont rendus dans l'ordre décroissant du **logit non biaisé** (égalité : indice
croissant), c'est l'ordre de `00-seuils-declares.md` § 2 pour un groupe et c'est l'ordre du noyau actuel quand β = 0.
β est en **unités brutes de logit** (comme tout P3 : pas de normalisation par l'étendue moyenne Δavg).

Ce qui ne change pas : `routeur_topk` (le noyau) n'est pas touché ; le prérempli par flux (`--flux`) n'est pas biaisé (le biais d'une
position dépend de l'état du cache après la précédente, ce que le prérempli par couche ne permet pas : l'option le **refuse**
explicitement avec `--flux`) ; le préchargement (`--prechargement`, qui prédit sans biais) est refusé avec l'option ; la garde, le cache,
l'ordonnanceur, les lectures sont ceux d'avant. Le cache et sa politique sont inchangés.

## 2. Plan de repli, décidé maintenant

L'option est **derrière un drapeau, `--biais-cache <β>`, absent par défaut**, sur `main`, sans branche : une branche changerait l'arbre de
travail que d'autres agents partagent dans ce dossier. Sans le drapeau (`Config::biais_cache = None`), le moteur lance les mêmes noyaux
dans le même ordre qu'avant : `debut_couche` appelle `routeur_topk` exactement comme avant, aucun tampon neuf n'est lu, aucune copie
neuve n'est lancée. La preuve en est la mesure (§ 5, témoin T0) : les 5 120 empreintes de logits, le `.kld` et la trace d'une passe sans
drapeau, après modification, égalent celles d'une passe du moteur construit **avant** la modification (même fenêtres, mêmes emplacements).
Si la modification du moteur se révèle plus invasive que prévu, ou si la preuve T0 tombe, le repli est de ne rien livrer sur `main`
et de laisser `genome/mimetisme/P3/REPRISE-routeur.md` avec l'état du code (diff), en le disant.

## 3. Grandeurs de décision

Banc : `gpt-oss-20b.trc`, fenêtres de R1 (`ref-openai-20b.kld`, 10 fenêtres de 512 jetons, 5 120 pas, 2 550 positions notées, cache qui
traverse les fenêtres comme à l'étage A), carte graphique, **238 emplacements** de VRAM (31 % de 768, le budget de N = 238 ; `--emplacements
238`), politique LRU du moteur, aucune RAM tiède. Quatre fils pour tout ce qui est hôte (`RAYON_NUM_THREADS`, `OMP_NUM_THREADS`,
`OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS` = 4 ; la garde de production a ses 4 fils de hachage) : comme à l'étage B, je le dis.

La base de comparaison est **le même moteur, mêmes fenêtres, mêmes emplacements, β = 0** (passe `P0`, sans le drapeau), pas la référence f64 :
la grandeur est l'effet du biais, pas l'écart du moteur à la référence (celui-là est déjà mesuré par C4). Les KL contre la référence f64 sont
rapportées à titre d'information seulement.

| # | grandeur | définition | source |
|---|---|---|---|
| G1 | défauts de cache par pas | `defauts_disque` du journal / `pas` (5 120 en évaluation) ; variation relative contre `P0` | compteurs du moteur, recoupés (§ 6) |
| G2 | KL excédentaire | KL moyenne sur les 2 550 positions notées de `juge kl --base P0.kld --test Pβ.kld` | `.kld` des deux passes |
| G3 | premier choix identique | argmax de `Pβ` = argmax de `P0`, **littéral** (2 550 positions) et **pondéré** (positions où la marge logit 1er – 2e de `P0` ≥ 0,3), intervalles par rééchantillonnage des 10 fenêtres (20 000 tirages) | `.kld` |
| G4 | jetons par seconde | génération de 256 jetons après l'invite `invite-wiki-3000.txt` (708 jetons), séries ABBA, § 7 | journaux `troncons generer` |
| G5 | part de cellules à ensemble changé | cellules (pas, couche) dont l'ensemble d'experts diffère entre `P0` et `Pβ`, relevée sur les traces | traces |

## 4. Seuils (ceux de P3, repris tels quels, aucun nouveau)

Repris de `00-seuils-declares.md` § 3 et `03-critere-marge-declare.md` (b) :

- **TIENT** (lecture pondérée, celle qui décide, comme à N = 238) : au même β, G1 ≤ −10 % **et** G2 ≤ 0,038 **et** G3 pondéré ≥ 95 %.
- **Lecture littérale** (rapportée à côté, lecture sévère) : G1 ≤ −10 %, G2 ≤ 0,038 et G3 littéral ≥ 95 %. Elle était « non concluant » à N = 238
  hors moteur (91,96 %) ; llama.cpp lui-même est à 92,55 % (JUGEMENT-N238 § 4.4) : je la rapporte, je ne la fais pas décider.
- **TOMBE** : G2 > 0,07 au β qui atteint −10 % de défauts, ou aucun β de la grille à −5 % de défauts avec G2 ≤ 0,038.
- **NON CONCLUANT** : entre les deux.
- Appliqué au premier β de la grille qui atteint −10 % de défauts : grille **β₁ = 0,041, β₂ = 0,05**, puis **β₃ = 0,06 seulement si ni β₁ ni
  β₂ n'atteint −10 %** (la boucle fermée peut répondre autrement que la boucle ouverte, où β₁ franchissait le seuil de 0,02 point seulement).
  Si β₁ le franchit, c'est β₁ qui décide et β₂ donne la pente (même règle qu'en `03-`).
- Les verdicts sont portés par l'estimation ponctuelle ; si elle passe un seuil avec la borne basse de l'intervalle en dessous, c'est dit.
- G4 ne décide pas du verdict de P3 (tableau de la décision = défauts, KL, premier choix). Aucun chiffre de vitesse n'est annoncé comme
  gain sans la règle ABBA du § 7 et sans l'avertissement connu.

## 5. Témoin et cassure

**Témoin T0 (β = 0, identique au bit).** Deux passes d'évaluation : `P0` (sans le drapeau) et `P0b` (`--biais-cache 0`, qui passe donc par
le noyau neuf avec un vecteur de biais nul). Exigence : les 5 120 empreintes64 de logits du CSV, le `.kld` (SHA-256) et la trace sont
**identiques octet pour octet**. De plus, avant toute modification, une passe `P-1` du moteur **tel qu'il est commité**
(binaire construit depuis le HEAD commité avant mes changements, copié sous `cibles/troncons-P3/troncons-avant.exe`) donne les mêmes empreintes que `P0` : c'est la preuve que le chemin par défaut
n'a pas bougé. Cassure du témoin : le noyau neuf avec le biais appliqué aux experts **absents** au lieu des présents (condition forcée à
faux), ou β = 0,3 : le CSV doit différer. L'instrument qui compare les empreintes sait tomber (il est écrit pour compter les lignes
différentes et il a déjà échoué sur les copies cassées de O3).

**Cassure du critère (la porte doit tomber).** Passe `Pβ = 0,3` : la porte doit tomber. Prédiction écrite maintenant, d'après le témoin hors
moteur (`resultat-temoin-b0.3.md` : KL 0,0716, pondéré 91,3 %) : G2 entre 0,045 et 0,12, G3 pondéré < 95 %, G1 plus fort que −35 %. Si la
cassure ne tombe pas (G2 ≤ 0,038 et pondéré ≥ 95 % à β = 0,3), l'instrument est dit aveugle et rien ne tient.

**Cassure de signe (facultative, faite si le temps le permet).** Passe `β = −0,041` : les défauts doivent **monter** au-dessus de `P0`
(on favorise les absents). Si elle baisse les défauts, la logique du masque est à l'envers.

**Test du noyau, sur la carte** (`cargo test -p trc-noyaux`) : `routeur_topk_biais` contre une version hôte écrite à part (tirages
pseudo-aléatoires de logits et de masques, k = 4, E = 32 et E = 256, égalités forcées), indices et poids égaux au bit ; avec un biais nul,
égal au bit à `routeur_topk` ; cassure (masque inversé) tombe.

## 6. Second chemin

1. **Le compte du cache**, déjà un témoin du moteur (O3) : la trace de chaque passe rejouée par `rejouer --emplacements 238` rend, **à l'unité**,
   les `defauts_disque` du journal ; cassure : `rejouer --casser`. Et un LRU à horodatage écrit à part (`juge_N238.py`) sur la même trace.
2. **KL et premiers choix** : recalculés par un lecteur `.kld` indépendant de `juge kl` (celui de `outils/mimetisme/P3/juge/`, paquets de 8
   positions), pas seulement par `juge kl` (même chemin que `JUGEMENT-N238.md` § 3.3).
3. **Cellules changées (G5)** : comparées pour le même β avec la part hors moteur (7,289 % à β₁ ; 8,832 % à β₂) : si la part en ligne en est très
   éloignée, c'est dit et cherché (la boucle fermée change la trajectoire).
4. Le noyau : le test du § 5, indépendant du moteur.

## 7. Génération (vitesse), à régler avant d'ouvrir un compteur

Un seul fichier (`gpt-oss-20b.trc`), donc le motif de lecture de requêtes est le même dans les deux bras : l'effet « motif de lecture du disque »
(`genome/08-placement-disque.md` : l'écart entre deux fichiers suit le motif de leurs requêtes, pas le fichier) ne joue pas **entre** les bras ; il
joue sur le **niveau absolu** (un autre `.trc` du même modèle, ou le même après une réécriture, irait plus ou moins vite), donc aucun chiffre
absolu de ce dossier ne se compare à un autre dossier. Séance calme, carte seule (verrou), secteur, un processus à la fois, repos de 10 s avant
chaque passe (`troncons mesurer`), mêmes options aux deux bras : seul `--biais-cache 0,041` diffère.
Ordre ABBA : `A B B A`, répété deux fois (deux blocs, soit 4 passes de chaque bras) ; A = sans le drapeau, B = `--biais-cache 0,041`. Bruit de
référence = l'écart d'un bras à lui-même (A1 contre A2, B1 contre B2). Seuil de vitesse : le gain n'est dit « gain » que si l'écart des
moyennes de B et de A dépasse le plus grand des deux écarts « bras contre lui-même » **et** a le même signe dans les deux blocs ; sinon « non
distinguable du bruit ». Rapportés à côté : défauts par jeton généré, h de la génération, octets lus par jeton, texte produit (les deux bras
sont gloutons mais divergent forcément quand un expert change ; la première divergence est notée).

## 8. Prédictions écrites avant toute passe

D'après la boucle ouverte à N = 238 (7,3 % de cellules changées à β₁ pour −10,02 %, KL 0,0117) : en ligne, G5 entre 5 et 11 % à β₁ ;
G1 entre −8 % et −14 % (le biais en ligne agit sur la trajectoire que le cache vient de créer, ce qui peut aider ou nuire : je ne sais pas le
signe de l'écart à −10,02 %) ; G2 entre 0,008 et 0,030, valeur centrale 0,013 ; G3 littéral 90 à 93 %, pondéré 97 à 99,5 %. Je n'ai aucune
raison de croire que le débit de génération monte de plus que les défauts évités (au plus de l'ordre de −10 % d'octets lus par jeton) ; si
les lectures dominent le pas (s_lectures ≈ 63 % de s_pas dans O3 à 362 emplacements), un gain de vitesse du même ordre de grandeur est
possible, mais je le prédis de 0 à +6 % à 238 emplacements, sans l'avoir mesuré.

## 9. Garde-fous de séance

Verrou de la carte `~/dev/verrou-carte.txt` écrit avant (« P3 routeur, agent, heure »), libre vérifié, supprimé à la fin ou en cas
d'échec ; secteur branché ; C: libre > 30 Go (74,9 Go au relevé de 2026-10-27) ; RAM libre ~3 Go au lancement (4,75 Go au relevé) ; le
moteur en pointe a un ensemble de travail de ~0,4 Go (journal O4) et un engagement de ~6,9 Go ; arrêt propre sur secteur coupé, swap > 4 Go ou
RAM disponible < 0,4 Go trois relevés de suite. Les passes sont séquentielles. Construction dans une cible à part
(`~/dev/cibles/troncons-P3`), jamais dans celle des autres lots.
