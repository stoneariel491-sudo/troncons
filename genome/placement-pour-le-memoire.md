# Placement disque : ce qu'il faut au mémoire

Source : `genome/08-placement-disque.md`. Données : `mesures/disque/placement/` (cartes, séances p2a,
p2b-D, p2b-D2, p3, p2b-F, p2b-F2, p4 ; `figures/` pour pgfplots). Outils : `outils/disque/placement/`.
Sources : `memoire/sources/placement-disque.bib`. Chapitre proposé : Tome II, « L'étage disque », une
section « Ce que la disposition fait au débit » après le banc du disque de `fondations/01-machine.md` § 2.

## 1. Dérivations

### 1.1 Le débit d'une file de lectures (loi de Little)

Le moteur garde q lectures en vol (q = 4, `trc-es`), chacune d'un tronçon de L octets (L ≈ 12,0 Mo en
v1.0, 11,6 Mo en v1.2). Si une lecture dure t en moyenne de sa remise au système à son retour, la loi de
Little (nombre moyen en vol = débit d'arrivée × temps de séjour) donne, en régime :

  X = q · L / t.

Contrôle sur les mesures commitées [calc.] : A120 le 2026-10-22, médiane t = 27,2 ms, L = 12,03 Mo,
q = 4 → X = 1,77 Go/s, mesuré 1,742. B120 : t = 20,4 ms, L = 11,64 Mo → 2,28 Go/s, mesuré 2,254. La
médiane de t remplace la moyenne, d'où les 1 à 2 % d'écart.

### 1.2 Une lecture coupée (H1)

Une lecture sans tampon qui chevauche n extents NTFS part en n requêtes vers le volume. Modèle :

  t(n) = t₁ + (n − 1) · τ.

Avec une fraction c des lectures coupées en n̄ morceaux en moyenne :

  X = q · L / [t₁ + c (n̄ − 1) τ].

**Prédiction faite avant la mesure** (P1, sur les seuls débits commités) : si t₁ valait celui de A120
(27,4 ms), C120 (c = 0,27, n̄ = 219,6) donnerait τ = (35,9 − 27,4) ms / 59,0 = 0,14 ms.
**Mesuré** (p2a, profils de C120, moindres carrés sur les lectures paires) : **t₁ = 17,0 ms, τ = 0,37 ms**,
et la durée des lectures impaires prédite à 0,980 et 0,991 près. L'écart avec la prédiction vient de t₁ :
les lectures non coupées de C120 ne vont pas à la vitesse de A120, mais plus vite que B120 (§ 1.4). Avec
t₁ = 17,0 et τ = 0,37 : X = 4 × 12,03 / (17,0 + 0,27 × 218,6 × 0,37) = 48,1 / 38,8 = **1,24 Go/s**, mesuré
1,245 et 1,238 [calc.] : ~~le modèle rend le débit de C120 au pour cent près~~ [juge, `genome/JUGEMENT-placement.md`
G3, M1 : un modèle constant le rend aussi (identité de Little sur une droite qui passe par la moyenne) ; et ces
paramètres sont ceux de `lire.py` : au chemin du moteur, t₁ = 34 ms, τ = 9 à 11 µs, C120 à 1,37-1,38 Go/s].

τ = 0,37 ms par morceau de quelques Kio (médiane des extents de C120 : 8 Kio) est l'ordre de la latence
d'une petite lecture à faible profondeur (0,20-0,23 ms à QD 1 pour 4 Kio, `fondations/01-machine.md`
§ 2.4) : les morceaux d'une même lecture coupée se servent presque l'un après l'autre.

### 1.3 Ce que vaut la défragmentation logique (prédiction pour le 120b)

Réécrire C120 d'une traite le rendrait contigu (D20 : 5 extents pour 11,2 Go) ; une fois les données
retombées (§ 1.4), ses lectures iraient au débit de A20 réécrit, ≈ 1,78 Go/s : ~~**gain prédit 1,78 / 1,24
= 1,43**~~ **gain prédit 1,731 / 1,378 = 1,26** à l'étage disque [calc. sur mes. du juge, J5 et J6 : chemin du moteur]. Non mesuré sur le 120b (la consigne interdit sa copie) ; la commande
est dans 08 § 12.

### 1.4 Le débit d'un même contenu au cours du temps

D20 (A20 récrit d'une traite) : 2,345 Go/s à + 1 min, 2,18 à + 2-3 min, **1,78 à + 2 h 14**, égal à A20
(1,76). Fonction en escalier mesurée, trois points ; la forme exacte de la descente n'est pas mesurée.
F20 (A20 récrit comme le codeur, deux fois) : 2,37 à + 0 min, 2,03-2,10 à + 2-4 min, **1,83 à + 2 h 08**
(A20 1,78 dans la même séance). Deux écritures différentes, même descente.
Avec la loi de Little, le temps d'une lecture de 12 Mo passe de 20,5 ms à 27,0 ms : **+6,5 ms par lecture
de 12 Mo, soit ≈ 0,54 ms par Mo** que coûte l'état « retombé » [calc.].

### 1.5 Ce que vaudrait un disque au débit de B pour le moteur

Le 20b passe 17,2 s de ses 27,2 s de génération à lire. À calcul égal, un étage disque k fois plus
rapide donne un gain G = T / (T − L (1 − 1/k)). Pour k = 1,42 (B20 / A20) : G = 27,2 / (27,2 − 17,2 ×
0,296) = **1,23** [calc.]. Mesuré pour k = 1,00 (D20 retombé contre A20) : 1,002.

### 1.6 Les seuils

S = max(2 · max e_soi, 2 × 5,9 %) ; S_b = max(2 · q₉₅(|r − 1|) sur 200 partages au hasard, 5 %). Tous
deux dérivés du bruit d'un fichier à lui-même, déclarés avant les mesures (08 § 2.1).

## 2. Figures (belles et vraies)

- **P1. La carte des extents sur le volume** : une bande horizontale par fichier (A120, B120, C120, A20,
  B20, D20, F20), axe des LCN de 0 à 1 (242 283 857 grappes), occupation par case de 1/2 000 du volume ;
  C120 en nuée. Données : `figures/carte-volume.csv`. Montre : la fragmentation logique se voit ; la
  position ne prédit rien (P3).
- **P2. Le débit dans le temps pendant une passe** : débit par seconde, A120 (passes 15 et 20 : les
  arrêts de 15-25 s à 0,2-0,37 Go/s), B120 et C120 en regard. Données : `figures/temps-p2a-*.csv`. C'est
  la figure la plus parlante : même ordre de lecture, arrêts à des instants différents.
- **P3. Débit par lecture contre LCN** (nuage, une couleur par fichier ; ρ en légende). Données :
  `figures/lectures-p2a-*-lire-tout-*.csv`.
- **P4. Débit par lecture contre nombre de morceaux** (C120, échelle log en abscisse, la droite
  t(n) = t₁ + (n − 1) τ en surimpression). Même source.
- **P5. Le même contenu, quatre écritures** : barres des médianes `troncons disque` de A20 (15 oct.),
  D20 (+ 1 min, + 3 min, + 2 h), F20 (+ 1 min, + 2 h), B20 (17 oct.), avec les passes en points et la bande
  S. Données : `p2b-*/analyse.json`.
- **P5 bis. La profondeur de file** : débit contre q (1, 2, 4, 8, 16), A20 et B20, passes en points.
  Données : `p4/analyse-qd.json`, `p5/analyse-qd.json`.
- **P6. De bout en bout** : jetons/s des huit passes de p3 (A20 et D20), les deux médianes, et le gain que
  donnerait k = 1,42 (§ 1.5). Données : `p3/*.json`.

## 3. Ce qui pourrait être faux (pour le mémoire)

Voir 08 § 9. L'essentiel : rien ici ne voit la puce ; l'explication physique des données « qui
retombent » et des arrêts de A120 est une hypothèse (repli SLC vers TLC, réessais de lecture,
rafraîchissement), pas une mesure.

## 4. Ajout du 2026-10-27 : l'hypothèse de relais après le retrim

G20a et G20b (copies de A20 écrites comme le codeur juste après le retrim de Stone du 26) : à + 2 h 06,
1,778 et 1,778 Go/s ; A20 1,734 ; B20 2,506 (`mesures/disque/placement/p7-2/`). Figure proposée (P5 ter) :
les quatre copies du même contenu (D20, F20, G20a, G20b), fraîches puis à + 2 h, contre A20 et B20, avec la
date d'écriture, la place libre et le retrim marqué ; toutes lues au motif v1.0, ce que la légende doit dire
(le juge a montré que la longueur des requêtes décide : `genome/JUGEMENT-placement.md` G1).
