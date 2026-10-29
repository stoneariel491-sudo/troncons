# Seuils déclarés du tri (mimétisme), avant toute mesure des six pistes

Écrit le 2026-10-27, rôle « tri ». Ce fichier est commité avant que `genome/mimetisme/tri.md` existe.
Aucune des six mesures n'a été lancée par moi ; aucun fichier de trace ni de modèle n'a été lu pour
fixer ces seuils. Ce que j'ai lu pour les fixer, et rien d'autre : les rapports des six éclaireurs
(tels que relayés dans la consigne), `mesures/mimetisme/ingenierie/{h1,h2,h3-a,h3-b}.csv`,
`mesures/mimetisme/mathematiques/m3_marges_20b.json`, `mesures/mimetisme/humain/e7-marge-20b.json`,
`mesures/mimetisme/vivant/lfu-longue-memoire-contre-lru.json`, `outils/mimetisme/ingenierie/cache2.py`,
`moteur/crates/trc-cache/src/lib.rs` (lignes 150 à 260) et `moteur/O-pour-le-memoire.md` § 9.2.

Chaque seuil dérive d'une grandeur nommée. Chaque piste a un seuil de succès et un seuil de mort
(entre les deux : « non concluant », dit comme tel). Chaque témoin doit pouvoir tomber : la
cassure est écrite avec lui.

Grandeurs de départ, lues dans les fichiers ci-dessus :
- taux de succès du cache global à 326 emplacements (7 % du 120b), génération prose-en : LRU 0,7379,
  LFU **sans décroissance** (compteur qui ne vieillit jamais, `cache2.py` ligne 208) 0,66268,
  Belady 0,83781 (`h3-a.csv`) ;
- part des octets lus sur le disque : 0,2621 en LRU seul ; exclusif à R = 336 : 0,18449 (`h2.csv`) ;
- temps d'un défaut : 11,6 Mo lus à 2,82 Go/s = 4,1 ms ; copie RAM vers VRAM d'un expert décodé
  de 13,25 Mo à 12,2 Go/s = 1,09 ms [calc.] ; plafond de recouvrement f = 0,17 (O § 9.2).

---

## P1. Mémoire du cache à deux échelles, jugée en génération

Mesure : taux de succès global (règle de groupe de `trc-cache`) à 326 et 922 emplacements, sur les
deux traces de génération du 120b (prose-en, wiki) et sur la chaîne « lecture du genre, puis
génération » ; politiques : LRU, LFU à demi-vie h, mélange à deux demi-vies, horloge de couches.
La demi-vie est choisie par validation croisée sur les traces de lecture des **autres** genres,
jamais sur la trace jugée.

- **Succès** : LFU(h*) − LRU ≥ **+0,02** de taux de succès sur les **deux** traces de génération à
  326 emplacements, et sur la chaîne, avec écart > 2 σ (σ par blocs de 32 jetons).
  Dérivation : 0,02 sur 0,2621 de défauts en LRU, soit défauts/0,2421 = ×1,083 de vitesse si le
  disque borne tout (vitesse ∝ 1/défauts) [calc.].
- **Mort** : l'une des deux traces de génération sous **+0,005**, ou négative. Lecture : le gain
  des cinq éclaireurs est un artefact de préremplissage, et le LFU sort du plan de décodage (il reste
  pour le préremplissage).
- **Entre les deux** : non concluant ; il faut au moins quatre traces de génération de plus.
- **Témoins** : W1, la demi-vie tendant vers 0 redonne le LRU à 1e-4 (0,7379 en génération,
  0,45279 sur tous.lecture) ; W2, la demi-vie infinie redonne le LFU sans décroissance de
  `cache2.py` à 1e-4 (0,66268 ; 0,42632). Cassure : décroissance inversée (les vieux comptes
  pèsent plus) ; elle doit tomber sous le LRU de plus de 0,02.
- **Second chemin** : le simulateur Rust `outils/mimetisme/physique/noyau-cache` contre le Python
  de `cache2.py`, égaux à 1e-4 sur les sept traces.

## P2. Cache exclusif VRAM vers RAM

Mesure : part des octets lus sur le disque, exclusif contre inclusif (règle actuelle de
`trc-cache`), R de 80 à 1 344 emplacements de RAM, politique de VRAM LRU puis LFU(h*) si P1 tient,
sur les deux générations et les chaînes. Estimation de temps par défaut converti : 4,1 ms (disque)
moins 1,09 ms (RAM décodée) ou 1,8 ms (RAM encodée, 0,95 ms de copie + 0,85 ms de décodage) [calc.].

- **Succès** : réduction relative de la part disque **≥ 15 %** à R = 336 sur les **deux**
  générations, ET copies VRAM vers RAM (13,25 Mo par éviction) ≤ **25 %** du temps de jeton au
  débit PCIe mesuré. Dérivation : la simulation donne −29,6 % (0,2621 vers 0,18449) ; elle est
  trop optimiste (taux simulé 0,74 contre 0,59 mesuré par le moteur) ; on exige la moitié.
- **Mort** : réduction **< 5 %** à R = 336 sur l'une des deux générations.
- **Témoins** : R = 0 redonne le LRU seul ; inclusif à R ≤ V ajoute **0** (±1e-4) ; exclusif à R
  égale le LRU de V + R à 7e-4 près (la mesure de l'éclaireur) ; cassure : démotion supprimée
  (la victime VRAM n'entre pas en RAM) doit redonner l'inclusif.
- **Second chemin** : implémentation indépendante (Rust, hors `cache2.py`), égale à 1e-4.
- Le coût en RAM (R × 13,25 Mo) est dit tel quel ; la décision de l'engager est à Stone seul.

## P3. Routage conditionné par le cache, borné par la marge

Mesure (après levée du verrou : passe CPU du 20b qui journalise les 8 meilleurs logits du routeur
par couche et par jeton) : biais β ajouté aux logits des experts résidents avant le top-4,
β ∈ {0 ; 0,01 ; 0,03 ; 0,1 ; 0,3} ; courbe (β, défauts évités, cellules dont l'ensemble change,
KL excédentaire contre le modèle exact).

- **Succès** : exister β tel que les **défauts baissent d'au moins 10 %** avec une **KL
  excédentaire ≤ 0,038** (= 10 × 0,13/34, la pente du mode rapide : 0,13 de KL pour −34 % d'octets
  lus, linéarisée) et un premier choix identique ≥ 95 %.
- **Mort** : au β donnant −10 % de défauts, la KL excédentaire dépasse **0,07**, ou aucun β ne rend
  −5 % de défauts avec une KL sous 0,038.
- **Témoins** : β = 0 redonne le modèle exact au bit (KL = 0, ensembles identiques) ; cassure :
  β négatif (on favorise les absents) doit **augmenter** les défauts ; la borne de humain E7
  (au plus 3,1 % de défauts évitables à τ = 0,01 et 8,2 % à τ = 0,03, pour le seul échange 4e/5e,
  5e supposé résident) doit être **respectée** par la rangée « échange 4e/5e seul » de la mesure.
  Une mesure qui la dépasse avec ce seul échange est fausse.
- **Second chemin** : le rejeu du cache sur les ensembles biaisés par `cache2.py`, indépendant du
  tracé.
- Note : la borne E7 ne couvre que 4e/5e. Le biais sur tous les résidents peut changer plus d'un
  expert par cellule ; c'est ce que la mesure ajoute.

## P4. Préchargement et rétention à confiance calibrée, qui cède à la demande

Mesure, première partie sur traces (sans carte) : prédicteur de précédents de chemin (humain E4b)
et seuil de confiance θ calibré par prédiction conforme fendue (la précision visée 0,9, borne de
Clopper-Pearson sur la moitié de calibration) ; simulateur à événements discrets des lectures
(disque 2,82 Go/s, PCIe 12,2 Go/s, 4,1 ms par défaut) avec deux files : demande prioritaire,
préchargement annulé à l'arrivée d'une demande. Deux bras : P (lire d'avance) et R (épingler en
VRAM les experts prédits sans rien lire de plus : coût en octets nul).

- **Succès** : bras P ou R : gain de vitesse simulé **≥ +5 %** contre l'absence de prédiction, au
  budget de 7 %, pour au plus **5 %** d'octets de plus, sur **3 genres de lecture sur 4** et sur la
  génération, avec une précision réalisée ≥ 0,85 sur la moitié de test. Dérivation : plafond
  1/(1 − 0,17) = ×1,21 pour un prédicteur parfait (O § 9.2) ; à précision 0,9 et couverture 40 %,
  l'éclaireur calcule ×1,07 ; on exige les trois quarts de ce que ce calcul permet.
- **Mort** : gain simulé **< +2 %**, ou précision réalisée < 0,8 (la garantie ne tient pas hors
  échantillon).
- **Témoins** : le simulateur avec θ = 0 et préchargement qui ne cède pas redonne le **−11 %** du
  moteur (O § 9.2, p = 0,692, +34 % d'octets) à ±4 points ; avec un prédicteur parfait il redonne le
  plafond ×1,21 à 2 %. Cassure : étiquettes de précédents mélangées, la précision doit tomber au
  hasard.
- **Second chemin** : formule fermée gain ≈ f − (1 − p)/p × part disque, comparée à la simulation.

## P5. Recuit et échange de répliques sur le choix des symboles synonymes

Mesure (étape 1, sans fichier modèle : instances synthétiques avec le H réel de la capture ;
étape 2, après accord de l'orchestrateur sur la lecture de ~100 Mo : 8 experts du 20b, couches 0, 8,
16, 23 × experts 0 et 16) : erreur de sortie pondérée (w − q)ᵀ H (w − q) + λ × débit pour Babai
(la rétroaction actuelle), descente cyclique de coordonnées, échange de répliques (8 températures),
**à débit égal ±0,005 bit**, calculée sur les entrées de **calibration** puis sur les entrées
**d'évaluation tenues à l'écart** (fenêtres 0 à 9).

- **Succès** : erreur tenue à l'écart en baisse d'au moins **10 %** contre Babai sur **6 experts
  sur 8**, PUIS KL appariée ≤ **−0,005** contre le fichier λ = 0 actuel sur 10 fenêtres, règle du
  lot R (meilleure si d̄ + 2σ(d̄) < 0). Dérivation : la mutation synonyme actuelle a gagné
  −0,0098 ± 0,0033 sur P1 ; la moitié de ce gain est le plus petit effet qui vaille un nouveau
  fichier.
- **Mort** : tenue à l'écart en baisse de **< 3 %**, ou en hausse (sur-ajustement : 766 entrées de
  calibration pour 2 880 dimensions, H de rang ≤ 766 avant la régularisation).
- **Témoins** : instance de 10 poids sur 5 niveaux, force brute (5^10 = 9 765 625) : le recuit
  retrouve l'optimum exact, et il existe une instance (cherchée parmi 1 000 H corrélés) où Babai ne
  le retrouve pas ; sinon l'instrument ne peut pas tomber et la piste s'arrête là. Cassure : un
  seul pas de température, le recuit doit retomber sur Babai. Second chemin : décodage par sphère
  (Fincke-Pohst) à n = 16 sur dix instances.

## P6. Fidélité décidée par appel : portillon de poids, cache à niveaux

Mesure, étape 0 sur traces et fichiers `.poids` (sans carte) : défaut de poids de mélange < θ servi
par le fichier rapide (0,718 des octets, 2,67/3,72), inséré au niveau rapide ; un succès suivi d'un
poids ≥ θ' sur un expert de niveau rapide est soit accepté, soit remonté (relecture de l'exact,
3,72 bits). Proxy d'énergie perturbée : somme des w² sur les usages servis au niveau rapide. Étape 1
(après levée du verrou) : KL de bout en bout au 20b, 10 fenêtres, θ ∈ {0,20 ; 0,25}, contre
tout-exact (0,0044) et tout-rapide (0,1446 à 0,1448).

- **Succès** : étape 0 : rapport r(θ) = (énergie / énergie du tout-rapide) / (octets économisés /
  octets économisés du tout-rapide) **≤ 0,7** à θ = 0,20 avec **≥ 8 %** d'octets économisés, remontées
  comprises (la mesure de physique : 0,44 à 0,65 sans remontées). Étape 1 : KL excédentaire à
  θ = 0,20 **≤ 0,022** pour **≥ 8 %** d'octets en moins. Dérivation : le tout-rapide économise 28 %
  des octets de défaut pour 0,1446 de KL ; proportionnel, 8,6 % d'octets coûteraient 0,0445 ;
  on exige la moitié.
- **Mort** : étape 0 : r(θ) > 0,9 (le portillon ne vaut pas un tirage au hasard) ; étape 1 :
  KL excédentaire > 0,040.
- **Témoins** : θ = 0 (rien en rapide) redonne le tout-exact ; θ = 1 redonne le tout-rapide
  (28 % d'octets) ; cassure : poids mélangés entre positions, r(θ) doit monter à ~1.
- **Second chemin** : la mesure des octets de physique (`mesures/mimetisme/physique/e2/portillon-de-poids.json` :
  7,8 % / 29,6 % / 67,1 % des défauts sous 0,15 / 0,20 / 0,25) redonnée à 1e-3 par la nouvelle
  simulation sans remontée.
- Par-dessus : la courbe KL(f), part f des défauts servis en rapide, que cette piste produit,
  est la donnée qui manquait à humain #3 et sert de barre à P3.
