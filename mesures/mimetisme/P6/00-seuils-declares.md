# P6, fidélité décidée par appel : seuils déclarés avant toute lecture de trace

Écrit le 2026-10-27, rôle « expérimentateur P6 ». Ce fichier est commité avant l'extraction de
`traces-120b.tar.xz` et `traces-20b.tar.xz` et avant toute simulation. Ce que je savais en l'écrivant,
et rien d'autre : la consigne (dont les agrégats de `mesures/mimetisme/physique/e2/portillon-de-poids.json`,
dont j'ai lu le contenu), `genome/mimetisme/tri.md` § P6 et `mesures/mimetisme/tri/00-seuils-declares.md`.
Aucune ligne de `.trace` ni de `.poids` n'a été lue. Le verrou de la carte
(`~/dev/verrou-carte.txt`, séance de vitesse ABBA du juge du placement disque) existe : aucun
fichier modèle n'est lu ; l'étape 1 (KL de bout en bout) n'est pas lancée (voir § 6).

## 1. Le modèle de cache à niveaux (ce que la simulation fait, déclaré)

- Un accès a = (jeton t, couche l, rang s) appelle l'expert x = (l, e) avec le poids de mélange w dans (0,1) ;
  les quatre poids d'un (t, l) somment à 1.
- Politique : cache global de N emplacements, LFU à décroissance exponentielle de demi-vie 8 jetons
  (celle de `noyau-cache`, noyau `exp_h8`) ; le groupe (t, l) est servi entier, on évince après lui, jamais
  un expert du groupe, départage par ancienneté du dernier accès. **P1 n'ayant pas rendu de h\***, on prend
  LFU 8, comme le protocole du tri le prévoit. N = 323 pour le 120b (7 % de 4 608), N = 54 pour le 20b
  (7 % de 768). Sensibilités déclarées : N = 326 et 922 (120b), LRU et demi-vie 32 (politique).
- Un emplacement garde un expert décodé, de même taille quel que soit son niveau ; il porte une étiquette
  E (exact) ou F (rapide). **La politique ne lit pas l'étiquette** : l'ensemble des défauts est donc le même
  pour toutes les règles (c'est ce qui rend le calcul propre) ; seuls les octets et l'énergie changent.
- Octets : un défaut lu exact coûte 1 (unité B), lu rapide coûte rho = 0,718 (2,67/3,72, donnée de la
  consigne, [rel.]). Sensibilités : rho = 0,70 et 0,766 (8,31 / 10,85 Go, fichiers entiers).
- Règle d'insertion (le portillon) sur un défaut de poids w : si w < theta, lecture rapide, étiquette F ;
  sinon lecture exacte, étiquette E.
- Règle sur un succès d'un résident F, de poids w :
  - **« accepter »** : servi rapide, énergie w², aucun octet ;
  - **« remonter à theta' »** (theta' dans {0,30 ; 0,40 ; 0,50}) : si w >= theta', relecture de l'exact entier
    (coût 1, le fichier rapide n'est pas emboîté), l'emplacement passe à E, l'accès est servi exact
    (énergie 0) ; sinon servi rapide comme « accepter ». Un résident E reste E (jamais redescendu).
  - Succès d'un résident E : exact, énergie 0, aucun octet.
- Énergie perturbée E = somme des w² des accès servis rapides (hypothèse de travail : l'écart de sortie
  d'une couche est proportionnel à w, donc sa variance à w² ; **c'est une hypothèse, pas la KL**).
- Normalisations : E_tout = somme des w² de **tous** les accès (tout-rapide : le fichier rapide entier,
  theta = 1) ; octets économisés S = (octets du tout-exact - octets de la règle) / octets du tout-exact,
  avec octets du tout-exact = nombre de défauts x 1 ; S_tout = 1 - rho = 0,282.
- **r(theta) = (E / E_tout) / (S / S_tout)**. r = 1 : la perturbation par octet économisé est celle du
  tout-rapide ; r < 1 : le portillon économise des octets à meilleur prix. Remontées comprises (leurs
  octets sont dans S).

## 2. Seuils étape 0, jugés sur la génération du 120b (la charge réelle)

Jeu jugé : les deux traces de génération du 120b (`gen-prose-en`, `gen-wiki`), theta = 0,20, N = 323,
LFU 8. L'ensemble des règles est fixé ici (accepter, R 0,30, R 0,40, R 0,50) : quatre essais, comptés.

- **Tient** : il existe une règle pour laquelle, sur **chacune** des deux traces, r <= 0,70 **et**
  S >= 0,08 (8 % des octets du tout-exact). Dérivation : 0,70 et 8 % sont ceux de la consigne ; ils
  viennent des agrégats de physique (r = 0,44 à theta = 0,20 sans portage ; 8,6 % d'octets économisés).
- **Tombe** : pour **toutes** les règles, sur le cumul des deux traces, r > 0,90 **ou** S < 0,02
  (le quart du seuil de 8 %, sous lequel l'économie ne vaut pas le bruit). Le 0,90 est celui de la consigne.
- **Ouvert** : tout le reste, dit comme tel.
- Incertitude : sigma de r et de S par rééchantillonnage de blocs de 32 jetons (2 000 tirages), publiée
  avec chaque chiffre ; une trace n'a que 256 jetons (8 blocs) : le sigma sera large et la décision l'est
  avec lui.
- Lecture secondaire, non décisive : theta = 0,15 et 0,25 ; les cinq traces de génération du 20b (N = 54) ;
  les traces de lecture traitées jeton par jeton (comme le fait `noyau-cache`).
- Prior que je déclare, pour qu'on voie si je me trompe : « accepter » devrait voir r > 0,9 (les experts
  chauds, insérés F par un défaut de petit poids, servent ensuite des poids ordinaires en rapide) ;
  « remonter » devrait perdre S (la relecture à 1 après la lecture à rho coûte plus que l'exact).
  [hyp., non mesurée]

## 3. Seuil de la variante B (préremplissage par masse agrégée)

Jeu : les quatre traces de lecture du 120b (code, dialogue, prose-en, prose-fr) ; lots de 512 jetons
consécutifs (sensibilité : 128 et 256) ; par lot et par couche, chaque expert appelé est lu une fois
(l'union ; pas de cache : 4 608 experts pour 323 emplacements), exact ou rapide.
- Règle A (un seul appel) : rapide si le **plus grand** poids reçu dans le lot < theta.
- Règle B (masse agrégée) : rapide si la **somme** des poids reçus dans le lot < theta_B, theta_B balayé.
- Énergie d'un expert rapide dans un lot = somme des w² de ses appels ; octets : rho contre 1.
- On compare les deux règles à **octets économisés égaux** (S = 5, 8, 10, 14 %).
- **Tient** : à S = 8 %, r_B <= 0,70 **et** r_B <= 0,90 x r_A, sur 3 genres sur 4 (avec le sigma par lots).
- **Tombe** : r_B >= r_A (la masse n'ajoute rien au maximum) sur 3 genres sur 4, ou r_B > 0,90.
- Ouvert : le reste. (Avec 5 lots de 512 jetons par genre, l'incertitude est grande ; elle sera dite.)

## 4. Témoins, chacun capable de tomber, et la cassure

- **T0** : theta = 0 -> E = 0 et S = 0 exactement ; theta > 1 avec « accepter » -> E = E_tout exactement,
  S = 1 - rho à 1e-12, r = 1 à 1e-9. Si l'un diffère, l'instrument est faux.
- **T1 (second chemin, indépendant)** : le simulateur Rust `outils/mimetisme/physique/noyau-cache`
  (exp_h8, N = 323, 4 traces de lecture, jeton par jeton) donne `defauts`, `defauts_sous`, `defauts_g2`,
  `g2_total` ; ma simulation Python **en mode « sans portage »** (énergie comptée sur les seuls défauts
  de poids < theta, comme physique) doit redonner `part_defauts` et `energie_g2_relative_au_tout_rapide`
  de `portillon-de-poids.json` à **1e-3 près** pour les six eps, et le nombre de défauts exactement.
  Cassure : si je décale la demi-vie de 8 à 9, T1 doit tomber (écart > 1e-3 sur au moins un eps).
- **T2 (cassure demandée par la consigne : « poids mélangés entre positions »)** : les vecteurs de poids
  (les 4 poids d'un (t, l)) permutés entre positions d'une même couche. **Ma prédiction déclarée, qui
  s'écarte de celle de la consigne** : r ne monte pas à 1 mais à r0(theta), le rapport « marginal »
  (part d'énergie / part d'accès) de la loi des poids, parce qu'une porte sur w sélectionne des w petits
  quelle que soit leur place ; le mélange ne détruit que la corrélation entre défaut et petit poids. La
  corrélation défaut/poids se lit donc par r / r0(theta). Je publie r0 et r.
- **T3 (cassure qui doit donner r = 1)** : sélection au hasard, indépendante de w, à même fraction de
  défauts choisis que le portillon, 50 tirages ; r doit tomber dans [0,93 ; 1,07] sur le cumul. Si non,
  l'estimateur d'énergie par octet est biaisé et rien de ce qui suit ne vaut.
- **T4** : la simulation du cache redonne `hits/total` du Rust à 1e-3 sur les 7 traces du 120b.

## 5. Ce qui se calcule en plus (exploratoire, hors verdict, étiqueté tel)

- Borne clairvoyante : on connaît, pour chaque séjour d'un expert dans le cache, le plus grand poids reçu
  pendant le séjour ; étiquette F si ce maximum < theta. Elle borne le meilleur portillon possible, quelle
  que soit sa règle de prédiction. Si même elle ne tient pas le seuil, aucune règle de prédiction ne le
  tiendra.
- La courbe de KL(f) n'est pas estimable à l'étape 0 : on publie la courbe énergie(f) et octets(f), et la
  courbe KL prédite sous l'hypothèse **linéaire en énergie** (KL = 0,0044 + (0,145 - 0,0044) x E/E_tout),
  marquée **[hyp.]**, à ne jamais lire comme un résultat.

## 6. Étape 1 (non lancée ici) et pourquoi

L'étape 1 lit un fichier modèle de 8,31 Go (`<nom>.rapide.trc`) et le GGUF du 20b pour la KL de bout en
bout : lecture lourde interdite tant que le verrou existe. Le cahier d'étape 1 est rendu dans `resultat.md`
(seuils de la consigne : KL excédentaire <= 0,022 pour >= 8 % d'octets en moins, mort au-dessus de 0,040).

## Amendement A1 (2026-10-27, avant toute simulation ; les traces sont extraites, aucun chiffre n'est calculé)

En préparant le code, je me suis aperçu que ma prédiction du témoin T2 (§ 4) est exacte pour un seul des
deux comptages. ~~« r ne monte pas à 1 mais à r0(theta) »~~ devient :
- **comptage sans portage** (énergie comptée sur les seuls défauts de poids < theta, comme physique) :
  après mélange des vecteurs de poids entre positions, r tend vers r0(theta) = (part d'énergie des poids
  < theta) / (part des accès de poids < theta), qui est < 1 par la seule loi des poids ;
- **comptage avec portage** (règle « accepter », l'étiquette F reste sur le séjour entier) : après mélange,
  le poids des accès suivants d'un séjour est indépendant du poids du défaut qui a fixé l'étiquette ; son
  énergie moyenne est celle de la loi marginale, donc E/E_tout tend vers la part des accès tombés dans des
  séjours F, S/S_tout vers la part des défauts F, et **r tend vers 1** (à l'écart de longueur de séjour
  près). La prédiction de la consigne tient donc pour le comptage qui compte ; la mienne pour l'autre.
- T2 est jugé sur « accepter » : r après mélange dans [0,90 ; 1,10] sur le cumul des 7 traces du 120b.
  Hors de cet intervalle, l'instrument ou ce raisonnement est faux. La corrélation défaut/petit poids se lit
  par r(vrai) / r(mélangé).
- T3 (sélection au hasard) est jugé sur « accepter » et sur le cumul des 7 traces du 120b.
