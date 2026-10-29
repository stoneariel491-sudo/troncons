# Piste « spectres » : seuils du juge, déclarés avant tout calcul du juge

Écrit le 2026-10-27 à 00 h 50, par le juge indépendant de la piste, **avant** d'avoir écrit ou lancé
son propre outil. Le juge a lu `seuil.md`, `ajustements.out` (le tableau publié) et le début de
`spectres.md` ; il n'a **pas** lu `csn.py`, `ajuster.py` ni `second_chemin.py`, pour que son chemin ne
recopie pas le leur. Une correction se fait en barrant et en disant pourquoi.

## Ce qui est jugé

Le chiffre principal de la piste : **0 matrice sur 48 au verdict principal, 9 sur 48 au verdict
amendé « compatible »** (il en fallait 32), avec leurs α̂ ; et l'affirmation « le α̂ réel est sous
celui du permuté dans les 48 cas ».

## Le chemin du juge (outil `outils/pistes/spectres/juge/juge_csn.py`, écrit de zéro)

Données : `mesures/pistes/spectres/valeurs-singulieres.npz` (2 Mo, déjà commité ; aucune lecture du
GGUF pendant une séance de vitesse). λ = σ². Méthode du `seuil.md` § 3 et § 4 bis, codée autrement :

- balayage de λ_min par sommes suffixes de ln λ, KS **bilatérale exacte** (max des écarts à i/n et à
  (i − 1)/n), queue ≥ 50 points ;
- log-normale tronquée ajustée dans y = ln(λ/λ_min), où elle est une **gaussienne tronquée** de
  paramètres naturels (c₁ ≥ 0, b) : densité ∝ exp(−c₁ y² + b y) sur y ≥ 0, normalisation par `erfcx`
  (stable quand c₁ → 0). La vraisemblance est concave dans ces paramètres (famille exponentielle) :
  un seul optimum, et la loi de puissance est le bord c₁ = 0 de la famille ;
- exponentielle tronquée en forme close ; Vuong normalisé, p = erfc(|R| / (σ̂ √(2n))) ;
- p_gof par 100 répliques semi-paramétriques de CSN, graine **777** (pas celle de la piste).

## Seuils (déclarés ici, avant tout calcul)

- **J1, verdict principal** : le juge doit trouver **0 / 48**. Prédiction théorique posée ici : la loi
  de puissance étant le bord c₁ = 0 de la log-normale tronquée, la vraie MLE log-normale a une
  vraisemblance ≥ celle de la loi de puissance, donc R_log-normale ≤ 0 pour toute matrice et à toute
  taille n. Attendu : R_log-normale ≤ 10⁻⁶ sur les 48 matrices, leurs 48 permutées et tous les témoins.
  Si une seule valeur dépasse, l'outil du juge est faux (rien ne sort de J1).
- **J2, verdict amendé** : le chiffre de la piste **tient** si (a) le juge trouve 9 ± 1 compatibles,
  (b) la conclusion « moins de 32 sur 48 » est la même, (c) au moins 45 matrices sur 48 ont le même
  verdict « compatible » dans les deux chemins, et (d) chaque désaccord est **au bord** : p contre
  l'exponentielle dans [0,01 ; 0,1], ou p_gof dans [0,03 ; 0,25], ou p contre la log-normale dans
  [0,01 ; 0,1], dans l'un des deux chemins. Sinon : le 9 / 48 **ne tient pas**.
- **J3, exposants** : λ_min égal (à 10⁻⁹ relatif) pour au moins 40 matrices sur 48 (la variante de KS
  peut déplacer quelques λ_min) ; là où λ_min est égal, α̂ égal à 10⁻⁶ relatif. Rapporté sans seuil :
  l'écart médian et maximal de α̂ sur les 48.
- **J4, réel contre permuté** : « α̂ réel < α̂ permuté » doit tenir dans **48 / 48** au chemin du juge,
  sinon l'affirmation est fausse telle qu'écrite.
- **Témoins du juge** (doivent tenir, sinon rien ne sort) :
  - T-Pareto de la piste (`pareto` du npz) : compatible, α̂ ∈ [2,3 ; 2,7] ;
  - 20 Pareto α = 2,5, n = 2 880, tirés par le juge (graine 4242) : au moins 18 / 20 compatibles ;
  - 20 exponentielles n = 2 880 (graine 4243) : au plus 2 / 20 compatibles ;
  - les 4 T-MP du npz : 0 compatible ;
  - contrôle de l'ajustement log-normal : 2 880 tirages log-normaux (μ = 0, σ = 1, graine 4244), λ_min
    imposé au plus petit : σ̂ à 5 % de 1.
- **Cassure** (`--casser`) : le spectre `pareto` et `mp/2880x2880` échangés dans les témoins ; les deux
  témoins doivent afficher ÉCHEC. Si la cassure ne fait rien tomber, l'instrument du juge ne sait pas
  dire non et rien ne sort.

## Ce que le juge vérifie sans calcul

- l'ordre des commits (`git log`) : seuil avant spectres, amendement avant ajustements ;
- le tirage de l'échantillon (graine 20261021) refait ;
- la cohérence entre `ajustements.out`, `spectres.md` et le rendu du rôle de recherche.

## Cohabitation

Pas de carte graphique, jamais le verrou ; un fil, priorité « inactive » fixée par l'outil lui-même ;
la partie lourde (répliques p_gof) se met en pause tant que le verrou nomme une séance de vitesse
(ABBA, J1, vitesse) de moins de 3 h. Seule la partie sans répliques (quelques secondes de calcul, sur
un fichier de 2 Mo) tourne pendant une séance.
