# Éclaireur « physique » : seuils déclarés avant toute lecture de données

Écrit le 2026-10-26, avant tout calcul sur les traces. Une seule chose a été vue avant ce fichier :
les vingt premiers jeux de poids de mélange de `w120b.wiki.generation.poids` (en-tête de fichier lu
pour connaître le format) ; ils montrent un plus petit poids de 0,09 à 0,21 sur ces 20 couples. Je le dis :
la prédiction E2 ci-dessous en tient compte. Données : traces de routage du 120b
(`mesures/localite-gpt-oss/traces-120b/traces-120b.tar.xz`), 36 couches, 128 experts, k = 4, cache global
de N = 323 emplacements (7,0 %, la VRAM de la base). Aucune carte graphique, aucun fichier modèle.

## E1. Noyau de mémoire du cache : exponentielle (LFU actuel) contre noyaux physiques

Mécanisme : le score d'un expert est Σ des accès passés pondérés par un noyau K(Δ) (Δ en jetons), on
évince le plus petit score. Le LFU de `outils/gptoss_localite.py` est K = exponentielle de demi-vie 8.
Familles comparées : (a) exponentielle, demi-vie ∈ {2, 4, 8, 16, 32, 64, 128} ; (b) Omori-Utsu
(Δ + c)^−p, c ∈ {1, 2, 4, 8}, p ∈ {0,5 ; 1 ; 1,5} ; (c) Kohlrausch exp(−(Δ/τ)^β), β ∈ {0,5 ; 0,7},
τ ∈ {4, 8, 16, 32} ; (d) deux temps de relaxation a·e^(−Δ/τ1) + (1−a)·e^(−Δ/τ2), a ∈ {0,5 ; 0,8},
τ1 ∈ {2, 4, 8}, τ2 ∈ {32, 128, 512}. Les noyaux non exponentiels sont approchés par une somme
d'exponentielles (huit temps de 1 à 256, moindres carrés non négatifs sur Δ = 0…600), l'erreur
d'approximation est écrite.
Protocole : validation croisée en laissant un genre dehors (quatre genres de lecture : code, dialogue,
prose-en, prose-fr) ; le réglage d'une famille est choisi sur les trois autres genres (moyenne des taux de
succès), évalué sur le genre laissé dehors ; on additionne les accès. Traces réservées, jamais
utilisées pour le choix : wiki lecture (708 jetons) et les deux générations.
Témoins : W1, mon simulateur à noyau exponentiel de demi-vie 8 redonne `g_lfu` de l'instrument existant
à ±0,002 sur chaque trace (même flux, mêmes règles) ; W2, cassure : l'ordre des jetons mélangé, le gain
de toute famille sur l'exponentielle doit tomber sous 0,005 (si une famille « gagne » encore, c'est un
artefact de réglage).
**Seuil** : la meilleure famille non exponentielle (validation croisée) bat la meilleure exponentielle
(validation croisée) d'au moins **+0,015** de taux de succès absolu en accès poolés, et sur au moins
3 genres sur 4 ; et le même signe sur les traces réservées. Sinon la forme du noyau est fermée.
Raison du 0,015 : à 7 %, les défauts du 120b sont 46 % des accès (LFU 0,539 sur 4 genres) ; +0,015 de
succès retire 3,3 % des défauts, donc des octets lus, soit le même ordre que le codon du zéro (+3,4 %
de débit) ; sous cela, la complexité ne paie pas.
**Prédiction écrite avant** : gain entre 0 et +0,008, famille fermée (l'exponentielle de demi-vie 8
est déjà près du plat ; le plafond Belady 0,706 se joue sur de l'information future, pas sur la forme
du noyau).

## E2. Nombres d'occupation : poids de mélange au moment des défauts

Mécanisme : les poids de mélange sont des nombres d'occupation (softmax sur 4 niveaux, loi de
Boltzmann). Un expert d'occupation faible lu pour rien coûte autant d'octets qu'un expert dominant.
On mesure, sur les défauts du cache LFU (demi-vie 8, N = 323), la part des lectures dont le poids de mélange
est sous ε, pour ε ∈ {0,02 ; 0,05 ; 0,10 ; 0,15}, et la masse de poids qu'on retirerait (Σ des poids
écartés / Σ des poids, borne L1 sur l'erreur de sortie de couche si les sorties d'experts ont des normes
comparables). Témoin : le total des poids par (jeton, couche) vaut 1 à 10⁻³ près (format 4 décimales) ;
cassure : poids mélangés au hasard entre couches, la part sous ε doit rester celle de la distribution
globale (si la part aux défauts diffère de la part globale dans la trace vraie, le défaut est corrélé au
poids ; sinon non).
**Seuil** : l'idée vaut une passe KL (moteur, hors de ce rôle) si **au moins 10 % des lectures en défaut
ont un poids sous 0,05** (≥ 10 % des octets en moins, pour une masse de poids écartée ≤ 0,05 par expert
retiré). Fermée si **moins de 3 %**. Entre les deux : seulement comme variante du mode rapide.
**Prédiction écrite avant** : sous 3 % (le plus petit poids typique de 0,09 à 0,21 sur les vingt couples
vus), donc fermée en retrait total ; en revanche 15 à 30 % des défauts sous 0,15, ce qui est le domaine
de la politique λ du lot B (servir par la base), pas un retrait.

## Résultats de E1 et E2 (ajout du 2026-10-27, après lecture ; les seuils ci-dessus n'ont pas bougé)

- **W1 tient** : le simulateur à noyau exponentiel de demi-vie 8 redonne `g_lfu` à 3·10⁻⁶ près sur les
  5 traces (code 0,4434, dialogue 0,5560, prose-en 0,5502, prose-fr 0,5993, wiki 0,5487). **W2 tient** :
  ordre des jetons mélangé, le gain de chaque famille sur l'exponentielle vaut −0,003 à +0,0017.
- **E1 tombe** : Omori-Utsu +0,0051, Kohlrausch +0,0028, deux temps +0,0044, contre le seuil +0,015
  (prédiction écrite : 0 à +0,008, tenue). Le signe est le même sur les 4 genres, la taille ne l'est pas.
  Correction de la déclaration : les temps de la somme d'exponentielles sont neuf (1, 2, 4, … 256), pas huit ;
  l'erreur de la somme d'exponentielles contre le noyau vrai est au plus 0,074 en absolu (K(0) = 1) mais
  jusqu'à 6,5 en relatif dans la queue de Δ ≤ 100 pour la pire loi de puissance : les lois de puissance ne
  sont pas fidèlement représentées dans leur queue (limite dite, sans effet sur le verdict vu la taille).
  Fait en passant : l'ordre mélangé fait passer le LFU de 0,551 à 0,514 : l'ordre des jetons ne donne que
  3,7 points ; le reste du taux est la popularité.
- **E2 tombe en retrait total** (prédiction tenue) : 0,09 % des défauts ont un poids sous 0,05 (seuil de
  fermeture : 3 % ; seuil d'intérêt : 10 %). Sous 0,15 : 7,8 % des défauts (5,5 % des accès : les défauts
  sont un peu plus souvent des poids faibles, ×1,4) ; sous 0,25 : 67 % des défauts. Somme des poids = 1 à
  10⁻⁴ près (témoin). La cassure par mélange des poids entre couches n'a pas été faite : à sa place, la
  comparaison part des défauts / part des accès ci-dessus (écart ×1,4, donc corrélation faible).

## E3. Barrière de nucléation : admission par seuil de score (déclaré le 2026-10-27, avant tout calcul E3)

Mécanisme : un expert lu sur le disque sert au calcul, puis n'entre dans le cache que si son score dépasse
celui du plus faible résident (pas d'éviction d'un résident utile pour un expert vu une fois). C'est
l'analogue de la barrière de nucléation (un germe plus petit que le rayon critique se redissout) ; en
informatique, l'admission de TinyLFU (Einziger, Friedman et Manes, 2017 [mém.]). Réalisation : après chaque
groupe, les experts du groupe sont candidats à l'éviction au même titre que les résidents (variable
BYPASS=1 du simulateur) ; le cache peut donc contenir N + 4 pendant un calcul.
Comparaison équitable : BYPASS à N = 323 contre le LFU ordinaire à N = 327 (même mémoire de pointe).
Noyau : exponentielle, demi-vie choisie en validation croisée (un genre dehors) pour chacune des deux
variantes. Même traces, mêmes témoins (W1 tient déjà pour la variante ordinaire ; W2 : ordre mélangé,
le gain de l'admission doit rester sous 0,005 — sinon l'admission gagne sur autre chose que la localité).
**Seuil** : gain poolé ≥ **+0,015** en accès, positif sur ≥ 3 genres sur 4 et sur ≥ 2 traces réservées sur 3.
**Prédiction écrite avant** : +0,003 à +0,02 ; probabilité de franchir le seuil, 35 %. Raison : l'expert d'un
défaut sert plusieurs fois dans un même jeton seulement s'il est repris, et le LFU à demi-vie courte évince
déjà les experts à score 1 ; ~~mais 13 % des accès sont des experts jamais revus dans les 100 jetons suivants, que le LFU ordinaire laisse entrer~~ (ce « 13 % » était écrit de mémoire, non mesuré ; barré le 2026-10-27, je ne le mesure pas ; il ne fonde pas la prédiction).

### Résultat de E3 (2026-10-27)
**E3 tombe** : gain poolé de l'admission −0,0012 (0,5531 contre 0,5543), négatif sur les 4 genres et les 3 traces
réservées ; mélange (W2) −0,0006. Prédiction (+0,003 à +0,02, 35 % de franchir le seuil) : fausse par le
signe, pas par la taille. Le LFU à demi-vie évince déjà ce qu'une admission écarterait. Journaux :
`mesures/mimetisme/physique/e3/`, outil `outils/mimetisme/physique/e3.py`.
