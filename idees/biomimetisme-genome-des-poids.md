# Le génome des poids : une idée biomimétique pour troncons

*Idée de Stone, le 2026-10-15. Mise en forme le même jour. Le projet troncons vise à faire tourner
un modèle d'IA ultra lourd sur un portable, en compressant ses poids à l'extrême et en les
décompressant au moment exact du calcul.*

---

## 1. L'idée, en ses mots

> J'ai penser à du biomimetisme informatique par exemple simjler une forme de molecule d'adn
> virtuel qui peut stocker une grande qua tutoriel d'informations en quelque sorte creer une
> nouvelle convention differentes du bit une transcription et implémentation

En une phrase : **s'inspirer de la manière dont le vivant stocke et lit son information** pour
stocker et lire les poids d'un modèle d'IA.

---

## 2. Ce qui ne marche pas : changer seulement d'alphabet

L'ADN écrit avec 4 lettres (A, C, G, T). Chaque lettre porte donc exactement **2 bits**
(log₂ 4 = 2). Écrire avec 4 symboles plutôt qu'avec 2 ne crée pas de place.

- **Shannon (1948)** : tout message a une taille minimale, son **entropie**. Aucun alphabet ne
  descend en dessous.
- Sur un ordinateur, une « molécule d'ADN virtuelle » est stockée en bits. Une nouvelle
  convention de symboles, à elle seule, ne bat pas la limite.

La force de l'ADN n'est donc **pas son alphabet**. Elle est dans ses **mécanismes**.

---

## 3. Ce qui marche : copier les mécanismes du vivant

| Mécanisme du vivant | Ce qu'il fait | Son équivalent dans troncons |
|---|---|---|
| **Expression à la demande** | La cellule porte tous ses gènes, mais ne transcrit que ceux dont elle a besoin, au moment où elle en a besoin | Les experts du modèle restent sur le disque et ne sont décodés qu'au moment du calcul, puis libérés (les « chunks » de Stone). **Déjà construit.** |
| **La recette plutôt que le résultat** | L'ADN ne contient pas la forme du corps, mais le programme qui le construit : quelques gigaoctets pour des milliers de milliards de cellules | Stocker un **petit générateur** des poids (une graine et quelques coefficients) plutôt que les poids eux-mêmes ; la carte graphique les « transcrit » au moment du calcul. **L'idée neuve à explorer.** |
| **Les familles avant le détail** | Les bases se rangent en deux familles (purines, pyrimidines) avant leur identité exacte | La découpe **base + complément** de troncons : la base donne la famille (signe, ordre de grandeur, 2,64 bits), le complément l'identité exacte (1,22 bit), sans aucun coût. **Mesurée.** |
| **La redondance qui tolère l'erreur** | Plusieurs codons donnent le même acide aminé : une mutation est souvent sans effet | Laisser les poids les moins importants en précision basse sans abîmer le résultat. **Mesuré en partie (quantification).** |
| **L'épissage** | Un même gène produit plusieurs protéines en assemblant ses morceaux autrement | Réutiliser des morceaux de poids partagés entre experts : une seule copie, plusieurs usages. **À explorer.** |
| **L'épigénétique** | Des marques chimiques disent quels gènes sont actifs, sans changer le code | Un marquage des experts « chauds » (souvent appelés) pour les garder près du calcul : le **cache d'experts** de troncons. **Construit.** |

---

## 4. Pourquoi « la recette » convient à cette machine

Le banc de mesure de troncons (`fondations/01-machine.md`) a établi que sur le portable de Stone
(RTX 4060 Laptop, 16 Go de RAM, disque NVMe chiffré) :

- **le disque est l'étage le plus lent** : 2,82 Go/s mesurés ;
- **la carte a du calcul de reste** : environ **214 opérations par octet compressé** pendant
  qu'elle attend le disque.

Un génome de poids **dépense du calcul pour économiser des octets**. C'est exactement l'échange
que cette machine demande : moins d'octets lus sur le disque, plus de calcul sur une carte qui,
sinon, attend.

Le gain se lit dans le théorème du toit du mémoire : la vitesse maximale vaut le débit du disque
divisé par les octets lus par mot. Diviser les octets par deux double la vitesse.

---

## 5. Ce que l'étude fera

**Question :** peut-on représenter les poids des experts de gpt-oss par une recette (graine +
coefficients), éventuellement combinée à la découpe base + complément, en moins de bits par poids
qu'aujourd'hui (3,84 bits sans perte), avec une qualité acceptable, et la transcrire sur la carte
assez vite ?

**Étapes :**
1. **Lire l'état de l'art à la source** : la compression des poids en graines de générateurs
   pseudo-aléatoires (SeedLM, Apple, 2024), les réseaux qui génèrent les poids d'autres réseaux
   (hyperréseaux), les codes en treillis (QTIP), et ce qui existe en biomimétisme informatique.
2. **Mesurer sur les vrais poids** de gpt-oss-20b (processeur, sans la carte) : bits par poids
   obtenus contre erreur de reconstruction, pour plusieurs tailles de graine et de coefficients.
3. **Mesurer la transcription** : un noyau sur la RTX 4060 qui régénère un expert depuis sa
   recette, et son débit, à comparer aux 2,82 Go/s du disque.
4. **Juger la qualité du texte** produit, contre la référence exacte, avec un seuil déclaré avant
   la mesure.
5. **Tout écrire** dans le mémoire (chapitre propre, en anglais et en français), avec les
   dérivations, les graphes et ce qui pourrait être faux.

**Critère de réussite** (à fixer avant la mesure) : moins de bits par poids lus sur le disque
qu'avec la compression sans perte actuelle, pour une perte de qualité sous le seuil du juge, et
une transcription plus rapide que la lecture du disque qu'elle remplace.

---

## 5 bis. La conviction de Stone, et trois pistes de plus

> Oui mais si on sait pourquoi avec du retro ingenieuring on peut savoir ce qui peut marcher j'ai
> la certitude que ce qu'on cherche se trouve dans du biomimetisme

Un échec compris dit où chercher : l'étude analysera chaque échec (quelle part des poids est du
bruit, laquelle a une structure) au lieu de s'arrêter au verdict. La conviction de Stone est
l'hypothèse de travail ; la mesure la jugera. Trois mécanismes du vivant s'ajoutent au génome :

| Mécanisme | Dans le vivant | Hypothèse mesurable sur gpt-oss |
|---|---|---|
| **Duplication de gènes** | Un gène nouveau naît d'une copie d'un ancien, puis mute | Les experts d'une couche (ou de couches voisines) sont parents : stocker un expert « parent » et, pour chaque descendant, une petite « mutation » coûte moins de bits que l'expert entier |
| **Codage prédictif** | Le cerveau ne transmet que l'écart entre ce qu'il attendait et ce qui arrive | Prédire chaque poids (depuis ses voisins, son expert parent, sa ligne) et ne stocker que l'écart : moins de bits quand la prédiction est bonne |
| **Élagage synaptique** | Le cerveau jeune retire les connexions inutiles | Une part des poids d'un expert se retire sans changer la sortie au-delà du seuil du juge |

Chacune se mesure d'abord sur les poids réels (processeur), avec un témoin et un seuil déclaré
avant, puis sur la qualité du texte.

## 5 ter. La consigne de Stone pour l'étude (2026-10-16)

> souviens toi comme précédemment leurs but n'est pas uniquement de trouver des articles et
> ressources non ce sont des scientifiques au sommet de l'immaginable le but est de concevoir un
> systeme fonctionnel et si il ne voye rien de convaincaint vers l'ADN au terme ils recherche le
> moyen biomimétique le plus prométeur jusqu'à trouver

Ce qu'elle fixe :
- **Le livrable est un système qui marche**, pas une revue : un mécanisme conçu, mesuré sur les
  poids réels, transcrit sur la carte et branché dans le moteur troncons, mesuré de bout en bout
  (jetons par seconde, fidélité).
- **Les chercheurs conçoivent** : l'état de l'art n'est qu'un point de départ ; chacun invente,
  construit et mesure.
- **Si l'ADN ne convainc pas, on ne s'arrête pas** : on cherche le mécanisme biomimétique le plus
  prometteur, guidé par ce que les échecs mesurés disent de la structure des poids, ronde après
  ronde, jusqu'à en trouver un qui batte la frontière. Pistes au-delà de l'ADN : le codage
  parcimonieux du cortex visuel (dictionnaires appris), la morphogenèse et les automates cellulaires
  (des règles locales qui génèrent une forme), l'évolution (algorithmes génétiques qui cherchent les
  graines et les dictionnaires), le repliement des protéines (une séquence courte qui donne une
  structure), la mémoire holographique (l'information répartie), l'indexation de l'hippocampe (un
  index court qui rappelle un souvenir complet), le système immunitaire (la maturation d'affinité).

## 5 quater. Des puissances de raisonnement différentes (Stone, 2026-10-17)

> je pense que ce serait interessant pour mais pas pour des taches ultra trivial un genre de puissance de raisonnement diff.rent

Lecture : un mécanisme avec perte (la variante hebbienne par exemple) ne remplace pas le chemin exact ; il donne un **niveau** de plus. Un routeur choisit le niveau selon la difficulté de l'appel (mode rapide pour le trivial, mode exact pour le raisonnement difficile), comme sa piste du « routeur et des appels différentiés » de relais. Prolongement à mesurer : le mode rapide comme **brouillon** du décodage spéculatif, vérifié par le mode exact en une passe ; le texte rendu est alors celui du modèle exact, au bit, et la vitesse vient du brouillon (rentable si l'accord α et la réutilisation des experts ρ le permettent : fondations/05-sparsite.md, α > 1 − ρ).

## 5 quinquies. Deux pistes mathématiques de Stone : géométrie tropicale et fractale (2026-10-17)

> je pensais est ce que tu penses que la geometrie fractale et la géométrie tropicale peuvent être inspirante

- **Tropicale (priorité)** : le routeur top-k est une opération du semi-anneau (max, +) ; il découpe l'espace des entrées en régions polyédriques (hypersurface tropicale ; Zhang, Naitzat et Lim, 2018, les réseaux ReLU comme fonctions tropicales, à relire à la source). Les bascules de routage mesurées (Tome II, l'amplification) arrivent près de ces frontières. À mesurer : la **marge** entre le k-ième et le (k+1)-ième score, par jeton et par couche, comme prédicteur des bascules ; s'en servir pour (1) une précision qui suit la marge (exacte près des frontières, forte compression ailleurs) et (2) prédire les experts de la couche suivante pour les précharger.
- **Fractale** : (a) les spectres des matrices de poids suivent-ils des lois de puissance (invariance d'échelle) ? si oui, codage par échelles, à relier à base + complément ; (b) la compression fractale par systèmes de fonctions itérées (Barnsley, Jacquin), probable échec pour la même raison que la graine (poids proches du bruit), à mesurer quand même ; (c) une courbe de Hilbert pour ranger les experts sur le disque selon leur co-occurrence.

## 5 sexies. L'expert pont (Stone, 2026-10-17)

> si ils sont vraiment différent est ce que tu pense que ce serait logique de coder un expert qui sert de pont entre les experts je ne sais pas trop mais je me dis que si un point ne marche pas faire le contraire peut peut etre aider mais je n'en suit pas sur

Après le verdict de la duplication (les experts de gpt-oss sont distincts : un parent n'apporte que 0,003 bit). Deux lectures :
- **pont de compression** (un expert commun, chaque expert codé en écart) : faible, l'information partagée mesurée est sous 0,01 bit une fois l'échelle du bloc connue (genome/, prédictif-élagage) ;
- **pont de vitesse (candidat de ronde)** : un petit expert toujours en VRAM, construit sur des entrées réelles pour approcher la sortie des experts absents (par exemple une application de rang faible, ou un petit expert dense ajusté aux moindres carrés sur les sorties des experts choisis), servi pendant que le vrai expert arrive du disque, puis corrigé. Le paralogue le plus proche laisse 66 à 84 % de l'énergie d'erreur ; un pont construit pour imiter devrait faire mieux. Mesures : erreur et KL sur le texte quand il remplace les experts manquants, attente retirée, et son rôle de brouillon du décodage spéculatif (§ 5 quater).

## 6. Ce qui pourrait être faux

- **Les poids d'un modèle entraîné ne sont peut-être pas « recettables »** : ils ressemblent à du
  bruit, et un bruit ne se résume pas. La recette ne peut alors qu'**approcher** les poids, avec
  perte. Toute la question est la taille de cette perte.
- **L'analogie avec l'ADN a ses limites** : le vivant tolère des erreurs qu'un modèle de langage ne
  tolère peut-être pas. Chaque mécanisme doit se juger par la mesure, pas par la beauté de
  l'analogie.
- **La transcription peut coûter trop cher** : si régénérer un expert prend plus de temps que de le
  lire, le gain disparaît. Le budget de 214 opérations par octet dit où est la limite.
- **SeedLM et les travaux voisins** sont cités ici d'après ce qu'on en sait ; ils seront relus à la
  source, avec leur date et leur adresse, avant d'entrer dans le mémoire.

---

## 7. Où cela se range

- Projet : `~\dev\active\troncons`.
- Ordre des chantiers (décidé avec Stone le 2026-10-15) : (1) le jalon J1 et son épreuve ;
  (2) le Tome II du mémoire ; **(3) cette étude** ; (4) la porte compatible pour relais.
