# P2, cache exclusif : seuils du juge, déclarés avant toute lecture de trace

Date : 2026-10-27. Rôle : juge indépendant de P2. Ce fichier est commité avant que j'extraie ou lise une seule
trace. Ce que j'ai lu avant de l'écrire : `seuil-declare.md`, `seuil-declare-selectif.md`, `resultat.md`,
`cache_exclusif.py`, le début de `explorations.py`, et `moteur/crates/trc-cache/src/lib.rs` (l. 100-319).
Je n'ai ouvert aucun CSV de mesure de P2 au-delà des chiffres recopiés dans `resultat.md`.

## Mon chemin (outils/mimetisme/P2/juge/)
Un simulateur écrit à partir de `lib.rs` (inclusif) et de la règle de Wong et Wilkes 2002 (exclusif), sans
importer ni recopier `cache_exclusif.py` : horodatage par cellule dans des tableaux numpy de taille L*E, victime
= horodatage minimal hors épinglés (argmin), aucune liste ordonnée. Horodatage strictement croissant par accès
(pas `jeton·L + couche` comme le moteur ; l'effet de cet écart est mesuré en J4a). Troisième chemin, sans
simulateur de cache : distances de pile de Mattson (arbre de Fenwick) pour le LRU de capacité C.

## Seuils du juge
- **J1, reproduction du chiffre principal.** V = 326, R = 336, `prose-en.generation` et `wiki.generation` :
  part disque inclusive et exclusive égales à celles de `resultat.md` (0,2573 / 0,1845 ; 0,5926 / 0,2885) à
  **1e-3 absolu** près, descentes par jeton (36,5 ; 85,9) à **2 %** près. Le verdict déduit (réductions >= 15 %
  sur les deux, descente de wiki > 25 % de 345 ms) doit retomber sur « ouvert ». Si J1 échoue : P2 non reproduit,
  donc ne tient pas.
- **J2, théorème par un troisième chemin.** Sans épinglage, mon exclusif doit égaler EXACTEMENT (mêmes entiers)
  le LRU de capacité V + R calculé par distances de pile, sur les deux générations à R = 336 ; avec épinglage,
  écart <= 7e-4.
- **J3, témoin qui doit tomber.** Trois cassures volontaires de mon simulateur doivent déplacer la part disque
  exclusive de wiki génération de plus de **1e-2** : (a) démotion de l'entrée la PLUS récente au lieu de la
  victime ; (b) pas de retrait de la RAM à la remontée (copie gardée en RAM) ; (c) RAM en FIFO d'insertion au lieu
  de LRU... (c) est rapportée sans seuil (en exclusif strict une entrée de RAM n'est jamais touchée avant d'être
  retirée, FIFO = LRU attendu, écart 0 attendu). Si (a) ou (b) ne bouge pas, mon banc ne discrimine pas et J1
  ne compte pas.
- **J4, ce qui pourrait être trop beau.** (a) horodatage du moteur (`jeton·L + couche`, égalités dans un groupe,
  départage par ordre inverse dans le groupe) : écart sur le chiffre principal rapporté, **<= 2e-3** attendu,
  sinon le chiffre dépend d'un détail d'implémentation et je le dis ; (b) victime RAM qui respecte l'épinglage
  (comme `lib.rs` l. 228) en inclusif : écart rapporté ; (c) temps de service par jeton (série, recouvert) refait
  avec a = 4,1 ms et b = 1,09 ms à partir de mes compteurs, égal aux chiffres de `resultat.md` à 1 ms près ;
  (d) descente de wiki rapportée au temps de jeton propre à la charge (pas seulement 345 ms), rapporté sans seuil.
- **J5, piste sélective (post-hoc).** Mon implémentation de `s = 1` (compteur de succès pendant le séjour, une
  entrée montée de la RAM arrive avec le compteur à `s`) redonne sur le 120b, R = 336 : parts disque 0,1769 et
  0,3649 à 1e-3, descentes 18,1 et 42,7 à 2 %. Sur le 20b à V = 154 : verdict « ouvert » (a 5/5, b 5/5, c 4/5)
  retrouvé. Le V = 54 dégénéré : je vérifie que le LRU seul y fait 100 % de défauts.

## Règle de décision
P2 est confirmé « ouvert » si J1 et J3 tiennent ; la piste sélective reste « post-hoc probable » seulement si
J5 tient. Non reproduit = ne tient pas. Ressources : un fil, sous la normale, aucune carte, aucun fichier modèle
(seulement les traces texte de `mesures/localite-gpt-oss/`), extraites hors dépôt.
