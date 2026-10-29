# P4, juge indépendant : seuil de reproduction, déclaré avant tout calcul du juge

Date : 2026-10-27. Avant ce fichier, le juge a lu `00-seuils-declares.md`, `resultat.md`, les journaux `mesure-120b.log` et
`temoins-120b.log`, et le code `p4.py` / `p4_mesure.py` (pour savoir ce qu'il faut refaire, pas pour le recopier). Il a ouvert
une trace (`t120b.code.lecture.trace`) pour son format seulement (3 lignes). Aucun calcul du juge n'est encore lancé.

## Chemin du juge (écrit de zéro, dans `outils/mimetisme/P4/juge/`)

1. Lecteur de trace propre (pas `chargement_localite`).
2. Prédicteur tiré du TEXTE du protocole (§ 1) : 20 voisins antérieurs (jetons <= t - 2) les plus proches au recouvrement
   cumulé des couches 0..l0, vote sur la couche l0 + d, 6 candidats, confiance = part pondérée. Écrit en boucle jeton par
   jeton (pas de produit matriciel T x T), départage des ex aequo par l'ordre d'apparition : un second chemin réel.
3. LRU global propre (groupe courant non évinçable).
4. Borne de Clopper-Pearson calculée par bissection sur la loi binomiale (pas `beta.ppf`), séquence fixe du haut vers le bas,
   départ au premier seuil qui retient >= 30 chargements (amendement 4).
5. Temps : simulateur à événements écrit d'après le texte du § 1 et de l'amendement 2 (pas d'après `des`), plus une borne
   analytique grossière (économie <= min(U x 4,1 ms, capacité des fenêtres de calcul)).

## Ce qui « reproduit » (120b, 7 % = 326 emplacements, d = 2, bras P, moitié de test, 4 genres de lecture)

- theta* du juge égal à celui de P4 à un pas de grille près (0,02) sur au moins 3 sessions sur 4 ;
- précision de test du juge à +/- 0,03 de celle de P4 par session, et agrégée >= 0,85 ;
- couverture et octets de plus du juge à +/- 30 % relatifs de ceux de P4 ;
- gain simulé du juge à +/- 1,5 point absolu de celui de P4 par session, et même position face au seuil déclaré
  (moins de 3 genres sur 4 à >= +5 %, moyenne entre +2 % et +5 %).
Par défaut, ce qui n'est pas reproduit ne tient pas.

## Témoins du juge (doivent pouvoir tomber)

- J1 étiquettes mélangées (ensembles vrais permutés entre jetons) : la calibration du juge ne doit trouver aucun seuil, et la
  précision à theta* doit tomber sous 0,3. Si la calibration trouve un seuil, le chemin du juge est dit cassé.
- J2 prédicteur parfait (tous les défauts lus d'avance, aucun faux) dans le simulateur du juge à d = 1 : rendu dans
  [x1,10 ; x1,30] (plafond x1,21 de O) ; hors de cet intervalle, le simulateur du juge est dit faux et seul le chemin
  précision / couverture compte.
- J3 génération prose-en : succès du cache recalculé indépendamment ; si < 0,95, l'argument « rien à précharger » de P4 tombe.
