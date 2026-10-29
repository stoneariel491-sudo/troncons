# P1, protocole opérationnel déclaré avant toute lecture d'un taux de succès

Écrit le 2026-10-27, rôle « expérimentateur P1 » (mémoire du cache à deux échelles, jugée en génération).
Ce fichier précise, sans le changer, le seuil déjà commité en `ec124f5`
(`mesures/mimetisme/tri/00-seuils-declares.md`, § P1). Il est commité avant que mes outils tournent sur
une seule trace. Rien de ce qui suit ne se règle après avoir vu un chiffre.

## Ce que j'avais vu avant d'écrire ceci (dit pour que l'on puisse en juger)

- Les chiffres de référence nommés dans la consigne et le seuil : LRU 0,7379 (génération prose-en,
  326 emplacements) et 0,45279 (`tous.lecture`) ; LFU sans décroissance 0,66268 et 0,42632 ; Belady 0,83781.
- Les fichiers des éclaireurs, lus pour cadrer : `lfu-demivie-t120b.json` (terre_cosmos) montre, **en
  lecture seule et en moyenne sur quatre genres**, LFU(32) au-dessus du LRU à 20 % ; `lfu-longue-memoire-contre-lru.json`
  (vivant), même chose en lecture.
- Je n'ai calculé **aucun taux de succès d'une politique à décroissance sur une trace de génération**, ni
  par mon outil ni par un autre. J'ai extrait les traces, compté leurs lignes (`wc -l`) et regardé 300
  octets d'un fichier de poids de mélange pour en connaître le format.

## Les données

Extraites de `mesures/localite-gpt-oss/traces-{120b,20b}/*.tar.xz` dans
`~/dev/mimetisme-P1-donnees/{t120,t20}` (hors dépôt).

- 120b (36 couches, 128 experts, k = 4) : lectures `code` (2542 jetons), `dialogue` (2862), `prose-en` (2378),
  `prose-fr` (2887), `wiki` (708) ; générations `prose-en` (256) et `wiki` (256).
- Provenance de la chaîne. `wiki` : l'invite (708 jetons) **est** la lecture, et la génération la suit
  (journal du traceur : `invite 708, produits 256`) : c'est une vraie chaîne, préremplissage puis réponse.
  `prose-en` : la génération vient d'une invite plus courte, **différente** du texte de 2378 jetons de la
  lecture ; la chaîne prose-en est donc une chaîne **simulée** (cache chauffé par un texte du même genre,
  puis une réponse d'un autre texte). C'est dit dans le résultat.
- 20b (24 couches, 32 experts, k = 4) : mêmes genres, avec générations code, dialogue, prose-en, prose-fr,
  wiki. **Secondaire** : il ne compte pas dans le verdict.

## Capacités

120b : **326** emplacements (7,07 % de 4608 ; c'est le chiffre du seuil) et **922** (20,0 %). 20b
(secondaire) : 54 et 154 emplacements (7 % et 20 % de 768).

## La règle de cache

Règle de groupe de `trc-cache`, la même que `cache2.lru1` et `gptoss_localite.g_lru` : les k experts d'un
(jeton, couche) sont épinglés pendant le groupe, la victime est le plus petit score hors du groupe,
l'éviction se fait après insertion du groupe. L'horloge est l'indice du jeton, **continu** d'un bout à
l'autre d'une chaîne. Départage à score égal : l'accès le plus ancien (numéro d'ordre d'accès) est évincé.

## Les politiques

- **LRU**.
- **LFU(h)** : compte à décroissance exponentielle, `c ← c · 2^(−Δt/h) + 1` à chaque accès, score = `c · 2^(−(t−t_dernier)/h)`,
  h en jetons ; h ∈ {8, 32, 64, 128, ∞} (∞ = compte qui ne vieillit jamais, la règle de `cache2.politique("lfu")`).
- **Mélange** M(w) : score = `(1−w)·ĉ₈ + w·ĉ₁₂₈` où `ĉ_h = c_h · ln2/h` (estimation d'un taux d'usage par jeton,
  de sorte que les deux échelles se pèsent sur la même unité) ; w ∈ {0,1 ; 0,3 ; 0,5 ; 0,7 ; 0,9}. M(0) = LFU(8) et M(1) = LFU(128) : témoins.
- **ETR** (horloge de couches, Mockingjay), mêmes paramètres que `cache2.politique("etr")` (0,95 par jeton, plancher 0,01).
  Comparateur seulement.

## Le choix de h*, jamais sur la trace jugée

Pour une trace de génération du genre g, à la capacité N : h* = argmax_h de la moyenne, sur les **lectures des
genres autres que g**, de [succès LFU(h) − succès LRU] (cache vide au début de chaque lecture, à la même N).
Pour g = prose-en : lectures code, dialogue, prose-fr, wiki. Pour g = wiki : code, dialogue, prose-en,
prose-fr. Égalité : le plus petit h. Même règle pour le w* du mélange. Le h* de la chaîne d'un genre est
celui de sa génération. On rapporte aussi le **h oracle** (le meilleur sur la trace jugée elle-même) : c'est une
borne haute inatteignable, jamais le chiffre du verdict.

## Le jugement

Quatre cas, tous à 326 emplacements sur le 120b :

1. génération `prose-en` seule, cache vide au départ ;
2. génération `wiki` seule ;
3. chaîne `prose-en` : lecture prose-en puis génération prose-en ;
4. chaîne `wiki` : lecture wiki puis génération wiki.

Dans les cas 3 et 4 la grandeur jugée est le succès **sur les 256 jetons de la génération seulement**
(le cache a été chauffé par la lecture). Le succès sur toute la chaîne est donné en plus.

Écart d = succès(LFU(h*)) − succès(LRU). Écart-type : on découpe les jetons jugés en blocs de 32
(8 blocs pour 256 jetons), on prend l'écart apparié par bloc, et σ = écart-type des blocs (n−1) / √(nombre de blocs) ;
z = d / σ.

- **Tient** : d ≥ +0,02 **et** z > 2 dans les **quatre** cas. (La consigne dit « les deux générations et la
  chaîne » ; je lis la chaîne au pluriel, une par genre, ce qui est la lecture la plus dure.)
- **Tombe** : d < +0,005 sur l'une des deux générations seules (cas 1 ou 2).
- **Ouvert** (non concluant) : tout le reste, dit comme tel.

Le verdict ne porte que sur LFU(h*). Le mélange et l'ETR sont des comparateurs ; s'ils passent là où LFU(h*)
ne passe pas, c'est écrit comme une piste voisine, pas comme un succès de P1. Les capacités 922, les
chiffres du 20b et le h oracle sont **descriptifs**.

## Les témoins (tous avant la mesure principale) et leur cassure

- **W1** : LFU(h = 0,001 jeton) redonne le LRU à 1e-4 absolu, sur chacune des sept traces du 120b (cache2) à 326
  emplacements : 0,7379 en génération prose-en, 0,45279 sur `tous.lecture` (les quatre lectures concaténées).
  Je recalcule les chiffres de référence avec `cache2.lru1`, et vérifie qu'ils retombent sur les publiés.
- **W2** : LFU(h = ∞) redonne `cache2.politique("lfu")` à 1e-4 (0,66268 ; 0,42632 pour les deux
  repères nommés ; toutes les traces du 120b à 326).
- **W3** : M(0) = LFU(8) et M(1) = LFU(128) à 1e-4. ETR : ma version contre `cache2.politique("etr")` à 1e-4
  sur une trace de lecture et une de génération.
- **Cassure W4** : décroissance **inversée** (`c ← c · 2^(+Δt/h) + 1`, les vieux comptes pèsent plus) pour
  h = 8 doit tomber **sous le LRU de plus de 0,02** sur `prose-en.generation` et sur `tous.lecture` ; sinon
  l'instrument ne voit pas la décroissance et la mesure s'arrête.
- **Cassure W5 (le verdict lui-même)** : la fonction de verdict, alimentée d'écarts fabriqués, doit rendre
  « tient » pour d = +0,03 (z grand), « tombe » pour d = +0,001 en génération, « ouvert » pour d = +0,012, et
  « ouvert » pour d = +0,03 avec z = 1,5. Si elle ne rend pas ces quatre réponses, elle est fausse.
- **W6 (monotonie)** : Belady (cache2.politique) ≥ toutes les politiques sur toute trace où je le calcule.

## Le second chemin

`outils/mimetisme/physique/noyau-cache` (Rust, écrit par le rôle physique, que je ne modifie pas) rejoue : LRU
(noyau de très courte vie), LFU(h) pour h ∈ {8, 32, 128, ∞} et M(0,5), avec des poids de mélange factices
égaux à 0,25 ; sur les traces à 326 emplacements, et sur les chaînes par différence
(succès de la chaîne moins succès de la lecture seule, la lecture étant le même préfixe). Accord exigé :
**1e-4** sur le succès de chaque trace entière. Si le départage des égalités diffère (le Rust départage par
indice de groupe, mon outil par numéro d'accès), l'écart est dit et jugé, pas caché.

## Garde

Un fil, priorité sous la normale, aucune carte, aucune lecture de fichier modèle (le verrou de la carte existe),
mémoire attendue sous 1 Go. Outils sous `outils/mimetisme/P1/`, mesures sous `mesures/mimetisme/P1/`,
documents sous `genome/mimetisme/P1/`. Les grilles (h, w, capacités) sont celles de ce fichier ; une grille
ajoutée plus tard serait annoncée comme **post hoc**, hors verdict.
