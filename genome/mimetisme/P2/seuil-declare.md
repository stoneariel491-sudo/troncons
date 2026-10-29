# P2, cache exclusif VRAM vers RAM : seuil déclaré avant toute lecture de données

Rôle : expérimentateur de la piste P2 (tri du mimétisme, `genome/mimetisme/tri.md` § 2). Date : 2026-10-27.
Ce fichier est commité avant que j'extraie ou lise la moindre trace. Ce que j'avais déjà vu avant de
l'écrire (dit pour que le seuil ne passe pas pour plus aveugle qu'il n'est) : le code de `cache2.py`, de
`trc-cache/src/lib.rs`, et les tableaux `h1.csv` et `h2.csv` de l'éclaireur ingénierie. Je n'ai ouvert
aucune trace.

## Source du mécanisme
Hiérarchie exclusive : quand le niveau haut évince un bloc, il le descend dans le niveau bas au lieu de
le dupliquer (Wong et Wilkes, « My cache or yours? Making storage more exclusive », USENIX ATC 2002
[source relayée par le tri, que je relis avant de conclure]).

## Données et grandeur
- Données : les 7 traces du 120b (`traces-120b.tar.xz`) : code, dialogue, prose-en, prose-fr en lecture ;
  wiki en lecture ; prose-en et wiki en génération (256 jetons). Extraites hors dépôt.
- Les « deux générations » du seuil sont `prose-en.generation` et `wiki.generation`.
- Grandeur : part des accès d'experts servis par le disque (tous les experts ont même taille en octets
  dans ce simulateur ; la part d'accès est donc la part d'octets lus), pour trois régimes : LRU seul
  (R = 0), inclusif (règle actuelle de `trc-cache`), exclusif (démotion).
- Grille : V = 326 (principal, c'est la capacité de l'éclaireur) et V = 922 (secondaire) ; R dans
  {80, 160, 336, 672, 1344} ; VRAM en LRU. Le LFU(h*) de P1 n'est essayé que si une conclusion de P1 est
  commitée avant la fin ; sinon je le dis et je ne le mesure pas.
- Temps converti par défaut évité : 4,1 ms (disque, 11,6 Mo à 2,82 Go/s) contre 1,09 ms (RAM décodée,
  13,25 Mo à 12,2 Go/s) ou 1,8 ms (RAM encodée, 0,95 ms de copie + 0,85 ms de décodage).
- Trafic de descente = (nombre de démotions par jeton, MESURÉ dans la simulation) × 1,09 ms, comparé à un
  jeton de 345 ms. Le « 38 évictions par jeton » du tri est un ordre de grandeur que je remplace par le
  décompte réel.

## Seuil (identique à celui du tri, `mesures/mimetisme/tri/00-seuils-declares.md`)
- **Tient** : réduction relative de la part disque (exclusif contre inclusif, V = 326, R = 336) **≥ 15 %**
  sur les **deux** générations, ET trafic de descente **≤ 25 %** du temps de jeton (86 ms sur 345 ms).
- **Tombe** : réduction **< 5 %** sur l'une des deux générations.
- **Ouvert** : tout le reste (entre les deux, ou une des deux conditions seule).
- Réduction relative = (disque_inclusif − disque_exclusif) / disque_inclusif. Je publie aussi la version
  contre le LRU seul : elle ne diffère de l'inclusif que de l'ordre de 1e-3 absolu.

## Témoins (déclarés avant, capables de tomber)
- **T0** : R = 0 en exclusif redonne exactement le LRU seul (écart 0, mêmes entiers de succès).
- **T1** : inclusif à R ≤ V ajoute 0. Tolérance 1e-4 sur le succès RAM pour R dans {80, 160} sur les 7
  traces. À R = V = 326 l'éclaireur a vu 3e-5 à 6e-4 sur les lectures : j'y mets 1e-3 et je le dis,
  la tolérance de 1e-4 de la consigne ne tient pas au bord R = V (cause probable : l'épinglage des
  groupes), je le vérifie au lieu de le supposer.
- **T2** : exclusif à R égale le LRU unique de capacité V + R à **7e-4** près, sur les 7 traces, pour
  R = 80 et 336. Preuve que le gain simulé est celui d'un LRU plus grand et rien d'autre.
- **T3, cassure** : la démotion supprimée doit ramener ce que la consigne annonce. Je la décline en deux
  cassures : (a) démotion supprimée et rien d'autre (RAM jamais remplie) doit redonner le LRU seul
  exactement ; (b) démotion remplacée par le remplissage au défaut disque (c'est l'inclusif) doit redonner
  l'inclusif exactement. Si l'une ne retombe pas, le simulateur contient un effet caché.
- **T4, reproduction** : mes chiffres exclusifs sur `prose-en.generation` et `tous.lecture` égalent
  ceux de `h2.csv` de l'éclaireur à 5e-4 près (implémentation séparée, même règle).

## Second chemin
Implémentation indépendante en Rust (fichier unique, hors `cache2.py` et hors mon Python), structures
différentes (horodatages et tableaux au lieu de listes ordonnées), égale à 1e-4 sur les 7 traces pour le
chiffre principal (V = 326, R = 336, inclusif et exclusif).

## Coût en ressources
~140 exécutions, un fil, RAM < 1 Go, aucun fichier modèle, aucune carte graphique. La suite ABBA moteur
(`--ram-tiede` 1 / 4 / 8 Go) demande la carte et le moteur : elle n'est pas lancée ici, et la décision
d'engager 4,45 Go de RAM (R = 336) est à Stone.

## Ce que ce seuil ne juge pas
- Le recouvrement de la descente VRAM vers RAM avec le calcul (PCIe duplex), non mesuré : je borne le
  temps net dans les deux cas extrêmes (tout en série, tout recouvert) au lieu de le supposer.
- Les générations de 256 jetons démarrent à froid ; une chaîne invite puis réponse (même genre, cache
  chauffé) est mesurée à part et ne décide pas du seuil.
