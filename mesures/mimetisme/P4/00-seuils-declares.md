# P4 : préchargement et rétention à confiance calibrée. Seuils et protocole, déclarés avant toute lecture de trace

Date : 2026-10-27. Rôle : expérimentateur P4. Avant ce fichier je n'ai lu que des documents (tri, éclaireur humain,
O § 9.2, `trc-cache`), aucune trace, aucun fichier modèle. Le seuil du tri (`mesures/mimetisme/tri/00-seuils-declares.md`,
commit ec124f5) est repris tel quel ; ce fichier le précise là où il laissait des choix, tous faits ici, avant les données.

## 1. Ce qui est mesuré

Chaque session (une trace d'un genre) est coupée en deux moitiés dans l'ordre des jetons : moitié de calibration (jetons
0 à T/2 - 1), moitié de test (le reste). Tout est causal : la prédiction du jeton t n'utilise que les jetons <= t - 2
(logique de `outils/mimetisme/humain/e4b_defauts.py`, recopiée, non modifiée).

- **Prédicteur** : à la fin du routage de la couche l0, vote des 20 jetons antérieurs les plus proches (recouvrement cumulé
  des ensembles d'experts des couches 0..l0) sur l'ensemble de la couche l0 + d. Candidats : les 6 premiers experts par
  vote. Confiance d'un candidat = part pondérée des voisins qui le portent. d = 2 fixé pour le verdict ; d = 1 et d = 4
  sont des sensibilités qui ne peuvent pas rattraper un verdict.
- **Cache** : LRU global sur les cellules (couche, expert), groupe de la couche courante épinglé (règle de `trc-cache`),
  budget 7 % (120b : 326 emplacements sur 4 608 ; 20b : 54 sur 768) puis 20 % (922 ; 154). Le bras P ne modifie pas
  le cache (les lectures d'avance vont dans une zone d'accueil, comptées comme dans O § 9.2).
- **Étiquette** : un chargement (candidat de confiance >= theta, absent du cache à l'instant de la prédiction) est « juste »
  s'il est dans l'ensemble réellement choisi à la couche cible. Précision = justes / chargements.
- **Calibration conforme fendue** : sur la moitié de calibration seule, theta* = le plus petit seuil d'une grille (pas de 0,02
  de 0,30 à 1,00) tel que, pour tout seuil >= theta* de la grille, la borne inférieure de Clopper-Pearson unilatérale à 90 %
  (delta = 0,1) de la précision des chargements de confiance >= seuil est >= 0,9 (test à séquence fixe, du haut vers le bas :
  on s'arrête au premier échec). Si aucun seuil ne tient : theta* = infini, pas de préchargement, gain 0 (dit). La calibration
  se fait DANS la session (hors texte le rappel tombe à +0,08 / +0,13, humain E4). Aucune donnée de test n'entre dans theta*.
- **Simulateur à événements discrets** (disque à un serveur, lectures non interrompables une fois commencées) :
  - par couche : calcul avant routage a, routage, lectures de demande des experts absents (4,1 ms chacune, en série),
    copie 1,0 ms + décodage 0,85 ms (en tuyau, queue de 1,85 ms comptée si la couche a eu au moins une lecture de demande),
    calcul des experts c, puis un surcoût bloquant o ;
  - a + c = fenêtre de recouvrement, 80 ms par jeton répartis sur les couches (f = 80/460 = 0,17, O § 9.2) ; o est ajusté pour
    que le jeton de base (sans prédiction) dure 460 ms (2,17 j/s, séance 1 de O) au nombre de défauts simulé ; copie, décodage
    et o bloquent le disque pour le préchargement (seul le calcul laisse le disque libre) ;
  - disque 2,82 Go/s (lecture de 12,0 Mo = 4,1 ms à l'échelle du banc), PCIe 12,2 Go/s : un tronçon préchargé est supposé
    déjà copié et décodé quand il arrive (sinon aucun préchargement ne pourrait cacher la copie) ;
  - **bras P** : les chargements sont mis en file de fond ; à l'arrivée d'une demande, les lectures de fond pas encore
    commencées sont annulées, celle en vol finit (fait mal, dit) ; un tronçon de fond demandé entre-temps est promu en
    demande. Variante FIFO : pas de priorité ni d'annulation (le mécanisme tué de O § 9.2) ;
  - **bras R** : aucun octet de plus ; les candidats de confiance >= theta déjà dans le cache sont épinglés (non évinçables)
    jusqu'à la fin de la couche cible, au plus 10 % des emplacements épinglés à la fois. Horizons d = 2 (verdict), 4 et 8.
- **Octets de plus** = (lectures de demande + lectures de fond terminées ou commencées) / lectures de demande de la base - 1.
- **Gain de vitesse** = temps de la base / temps du bras - 1 sur la moitié de test, cache chauffé par la moitié de calibration
  (base et bras ont le même historique de calibration sans préchargement).

## 2. Verdict

Configuration d'éligibilité : d = 2, budget 7 %, un seul bras pour toutes les conditions (P ou R, pas un mélange par genre).
Données du verdict : 120b (le modèle sur lequel O a mesuré le -11 % ; 4 genres de lecture : code, dialogue, prose-en,
prose-fr, plus les 2 générations prose-en et wiki). Le 20b (4 genres de lecture, 3 générations) est une réplique qui
compte pour « ouvert » si elle diverge, pas pour « tient ».

- **Tient** : pour le même bras, gain simulé >= +5 % ET octets de plus <= 5 % sur au moins 3 des 4 genres de lecture du 120b,
  ET la génération (gain cumulé des 2 traces >= +5 %, chacune >= +2 %), ET précision réalisée sur la moitié de test >= 0,85
  (agrégée sur les sessions retenues, chaque session >= 0,80).
- **Tombe** : gain moyen sur les 4 genres de lecture du 120b < +2 % pour les deux bras, OU précision réalisée agrégée < 0,8.
- **Ouvert** : tout le reste (par exemple tient au 120b et pas au 20b, ou tient en lecture et pas en génération).

## 3. Témoins (déclarés avant, avec leurs tolérances)

1. **-11 %** : prédicteur synthétique à précision 0,692 et couverture 0,76 des défauts (donc octets +34 %, comme O § 9.2),
   file FIFO sans annulation : le simulateur doit rendre -11 % à +/- 4 points. Un paramètre libre est ajusté d'abord,
   sur le témoin suivant seul ; celui-ci est l'épreuve hors échantillon.
2. **Parfait** : prédicteur parfait (tous les défauts, aucun chargement faux), priorité : x1,21 à 2 % près. Le paramètre
   libre est la fenêtre de recouvrement utilisable par couche, initialement 80 ms / (nombre de couches). Si x1,21 n'est pas
   atteint, la fenêtre est ajustée UNE fois pour y arriver, et dite telle (étalonnage, pas mesure).
3. **Cassure** : étiquettes mélangées (les ensembles vrais permutés entre jetons), theta* de la vraie calibration appliqué :
   la précision doit tomber au hasard (~ k / E) ; et la calibration refaite sur étiquettes mélangées ne trouve aucun seuil.
4. Voisins au hasard (même causalité) : la précision à theta* doit être très inférieure.
5. Le simulateur à zéro prédiction redonne 460 ms par jeton par construction ; le LRU global est vérifié contre une seconde
   implémentation (liste simple) sur 2 000 accès.

## 4. Second chemin du chiffre principal

Formule fermée : gain tiré des seuls comptes (couverture u/F, précision p, fenêtre totale omega_tot) :
gain_fermé = min(U t, p * min(C t, omega_tot)) / T_base (t = 4,1 ms, U = chargements justes, C = chargements) pour la
priorité ; gain_FIFO(O) = f - (1 - p)/p * part_disque pour le FIFO. Comparée à la simulation ; écart > 25 % relatif = dit.

## 5. Ce que je ne fais pas

Pas de carte graphique, pas de fichier modèle, 2 fils au plus, RAM < 1,5 Go. Le prédicteur à état caché (routeur de la
couche suivante sur le résidu) demande le moteur : hors périmètre. La pollution du cache par les lectures d'avance (bras
P en cache) n'est pas simulée (O compte comme moi).

## 6. Amendement du 2026-10-27, écrit avant tout lancement de code (aucune trace n'a encore été lue)

Précisions de lecture du § 1 que l'écriture du simulateur a rendues nécessaires. Elles ne touchent ni les seuils ni les témoins.

1. **Annulation** : une lecture de fond non commencée est annulée quand la demande de SA couche cible arrive (elle devient
   alors une lecture de demande) ou quand sa cible est passée. Les lectures de fond pour des cibles plus lointaines restent en
   file, à priorité plus basse que toute demande. Variante de sensibilité « purge totale » : toute la file est annulée à
   chaque arrivée de demande. Le verdict utilise la première.
2. **Fenêtres** : en mode priorité, une lecture de fond ne peut COMMENCER que dans une fenêtre de calcul (le calcul c d'une
   couche, le calcul a de la suivante) ; elle peut déborder. En mode FIFO (le mécanisme tué de O), chaque lecture démarre dès que
   le disque est libre après son émission, et la demande attend toutes les lectures émises avant elle.
3. **Validité du simulateur** : si le témoin « -11 % » (hors échantillon, § 3.1) manque sa tolérance, le simulateur est dit
   non validé et le verdict ne peut pas être « tient » (au mieux « ouvert »).
4. **Début de la séquence fixe** : le premier seuil testé est le plus haut de la grille qui retient au moins 30 chargements en
   calibration (sinon 1,00 échouerait pour un simple manque d'effectif).
5. **Calibration du bras R** : même procédure, sur la population des candidats DÉJÀ présents dans le cache (ce qu'on épingle) ;
   les épingles n'agissent que sur la moitié de test.
6. **Bras P, d** : la prédiction pour la couche l0 + d part de la fin du routage de l0 ; les témoins §3.1 et §3.2 se font à d = 1
   (le mécanisme de O), le verdict à d = 2.

## 7. Constat du 2026-10-27, après les premiers témoins (v1 du simulateur) et avant toute mesure de session

Journal : `temoins-120b-v1.log`, `temoins-120b-v1.json`.
- T0 : LRU global (dict) = liste simple (1 195 / 1 195 défauts à N = 326 ; 2 000 / 2 000 à N = 60). Tient.
- T2 (parfait, d = 1, priorité) : x1,2247 à la fenêtre de 80 ms par jeton, soit +1,2 % de l'attendu 1,21 : dans les 2 %. Tient, sans étalonnage.
- **T3 (FIFO synthétique, p = 0,692, couverture 0,76, octets +33,8 %) : x1,052, soit +5,2 % là où O a mesuré -11 % (tolérance +/-4 points). MANQUE.**
  Le simulateur v1 cache trop bien le préchargement : un tronçon lu d'avance y arrive déjà copié et décodé.
- Lecture du code du moteur (`moteur/crates/trc-ordo/src/lib.rs`, lignes 1109 à 1190) : une lecture anticipée va dans un
  tampon d'hôte ; la copie vers la carte et le décodage se font à la demande, comme pour un défaut (`envoyer_et_decoder`
  sur chaque défaut prêt, y compris ceux qui viennent d'un préchargement). Le préchargement n'économise donc que la LECTURE
  (4,1 ms), pas la queue copie + décodage (1,85 ms).
- **Correction v2 (structurelle, tirée du code et non d'un réglage) : la queue de 1,85 ms s'applique aussi aux experts servis par un
  préchargement.** Les témoins T2 et T3 sont relancés avec ce seul changement. T3 n'est alors plus indépendant de la
  correction (il l'a motivée) : si T3 tient en v2, le simulateur est dit « cohérent avec le seul point mesuré de O, non validé
  hors échantillon », et le verdict ne dépasse pas « ouvert » ; si T3 manque encore, idem, plus ce constat.
- Fait noté : le LRU global à 326 emplacements donne 78,8 défauts par jeton sur le 120b en lecture (succès 45 %), contre 59 défauts
  par jeton (succès 59 %) mesurés par le moteur en O § 9.2 : le moteur a un niveau de RAM tiède en plus et d'autres traces.
