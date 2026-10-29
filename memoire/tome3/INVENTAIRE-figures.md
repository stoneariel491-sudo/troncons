# Tome III : l'inventaire des figures

Écrit le 2026-10-27, à la demande de Stone : « prépare le Tome III : l'inventaire des figures, puis un flux
court avec un juge ». Source : les dix-sept notes « pour le mémoire » de la quête du génome des poids, lues en
entier pour leurs figures, et l'état des fichiers vérifié le même jour (chaque CSV cité ci-dessous existe et
est commité, sauf mention contraire). Règles : SOCLE, demande du 2026-10-17 (« des schémas beaux, des
modélisations d'espace latent, des transformations de la topologie, la totale, qui soit digne de ce
travail »). Une figure belle reste vraie : elle se tire des données commitées, par un script commité.

## 0. Ce que couvre le Tome III

La quête du génome des poids, de l'état de l'art à la construction, et les pistes qui en sont sorties.
Le placement disque (08) va au **Tome II**, chapitre « L'étage disque » : son juge l'a décidé
(`genome/JUGEMENT-placement.md`, § 13 point 6). Le Tome III ne garde du disque que ce qu'il faut pour lire
le J1 juste.

Plan proposé (reprend `genome/construction-synthese-pour-le-memoire.md` § 1, élargi aux autres équipes) :

| Ch. | Titre | Sources |
|---|---|---|
| 1 | La question du génome : toit, bits lus par poids, frontière | `genome/00`, `01`, `etat-de-l-art-pour-le-memoire.md` |
| 2 | L'éclaireur : où est le bruit, où est la structure | idem, `genome/01-eclaireur.md` |
| 3 | Le génome des poids : la recette, la graine, S\* | `genome/genome.md`, `genome-pour-le-memoire.md` |
| 4 | La duplication de gènes | `genome/duplication.md`, `duplication-pour-le-memoire.md` |
| 5 | Codage prédictif et élagage synaptique | `predictif-elagage-pour-le-memoire.md` |
| 6 | Le mimétisme : six pistes du monde vers le pipeline | `genome/mimetisme/P1` à `P6`, `tri.md` |
| 7 | La synthèse de la ronde : frontière commune, deux parts de la KL | `genome/05-synthese.md`, `construction-synthese-pour-le-memoire.md` |
| 8 | Un codon synonyme dans le format (lot A, v1.2) | `genome/06-codon-v1-2.md`, `construction-codon-pour-le-memoire.md` |
| 9 | Le génome synonyme, mode rapide (lot B) | `genome/07-genome-synonyme.md`, `construction-synonyme-pour-le-memoire.md` |
| 10 | Le juge de la construction | `genome/JUGEMENT-construction.md`, `construction-juge-pour-le-memoire.md` |
| 11 | La géométrie tropicale du routeur | `genome/pistes/tropicale/` |
| 12 | Les spectres des matrices et la fractale | `genome/pistes/spectres/` |

## 1. Les états

- **T** : tracée au style du mémoire (pgfplots ou TikZ, macros `\EF{en}{fr}`, préambule commun), compilée.
- **Tx** : tracée hors style (PNG de matplotlib) : à reprendre en pgfplots, depuis le même CSV.
- **D** : données commitées et prêtes ; il ne manque que le script et la macro.
- **C** : calcul neuf sur le processeur, depuis des fichiers déjà sur la machine (captures de l'éclaireur
  sous `~\dev\essais\troncons\genome\eclaireur\calib\`, GGUF) ; le CSV tiré sera commité.
- **G** : demande la carte graphique (verrou) ou une passe du modèle.
- **S** : schéma (TikZ) sans mesure ; étiqueté « schéma » dans sa légende.
- **3D** : rendu Blender possible en plus, jamais à la place de la figure plane.

Colonne « Réserve » : ce que la figure doit corriger ou dire pour rester vraie (§ 3).

## 2. L'inventaire, chapitre par chapitre

### Ch. 1-2. La question et l'éclaireur

| N° | Origine | Figure | Données | État | Réserve |
|---|---|---|---|---|---|
| III-1.1 | EDA § 1.1 | Le bloc MXFP4 au bit près (17 octets, E8M0, demi-octets) | — | S | — |
| III-1.2 | EDA § 1.4 | La borne distorsion-débit : courbe `uniforme_precis`, points frontière (2,6441 ; 4,29 %) et frontière sur code canonique (2,5965) | `mesures/genome/etat-de-l-art/borne-rd.csv`, `journaux/borne-rd.json` | D | courbe publiée comme borne supérieure (Blahut-Arimoto), dit en légende |
| III-2.1 | EDA § 1.3 | Le signe des zéros, barres par tenseur | `journaux/zero-compte-20b.json`, `-120b.json` (`par_tenseur`) | D | — |
| III-2.2 | EDA § 1.3 | La concentration de l'énergie par exposant (cumulative) | `journaux/borne-rd-passe1.json` (`exposants`) | D | — |
| III-2.3 | EDA § 1.6 | Le diagnostic de sur-apprentissage et le choix de δ | `journaux/diagnostic-L0-E0.json`, `choix-delta.json` | D | — |

### Ch. 3. Le génome des poids

| N° | Origine | Figure | Données | État | Réserve |
|---|---|---|---|---|---|
| III-3.1 | genome 7 | Le brin, la fenêtre de 12 bits, le mélangeur, la table ; en regard l'ARN, le ribosome, le codon | — | S | analogie, pas preuve |
| III-3.2 | genome 7 | Le treillis à 4 états et un chemin de Viterbi | — | S | — |
| III-3.3 | genome 8 | Chronogramme de la transcription dans une GEMV | — | S | — |
| III-3.4 | genome 1 | Le brin sur une gaussienne contre la borne de Shannon | `mesures/genome/genome/csv/gauss-brin.csv` | D | — |
| III-3.5 | genome 2 | La graine mesurée contre le lemme 1 | `csv/graine-mesure-theorie.csv` | D | — |
| III-3.6 | genome 3 | Débit-distorsion par tenseur, recette brute et tournée, point de la base | `csv/courbes-tourne-l12.csv`, `courbes-brut-l12.csv`, `verdict-par-tenseur.csv` | D | — |
| III-3.7 | genome 4 | Le verdict W par tenseur (frontière, brut, tourne) | `csv/verdict-par-tenseur.csv` | D | — |
| III-3.8 | genome 5 | Le spectre réel contre permuté | `csv/spectre.csv` | D | — |
| III-3.9 | genome 6 | La fidélité de sortie selon le débit, base en trait | `csv/fidelite.csv` | D | — |

### Ch. 4. La duplication de gènes

| N° | Origine | Figure | Données | État | Réserve |
|---|---|---|---|---|---|
| III-4.1 | dup. schéma | La même permutation Π sur W_g, W_u, W_d ; les blocs de 32 entiers ou traversés | — | S | — |
| III-4.2 | dup. 1 | Score de parenté par candidat, hasard (0,0016) et témoin planté (0,2075) | `mesures/genome/duplication/csv/scores-parente.csv`, `paires-temoin-planter-0.5.json` | D | — |
| III-4.3 | dup. 2 | D1 par matrice : parent contre hasard, coût ajouté | `csv/d1-sans-perte.csv` | D | — |
| III-4.4 | dup. 3 | Débit-distorsion d'une matrice (L8, E0, gate) | `csv/rd-points.csv` | D | — |
| III-4.5 | dup. 4 | Même erreur de poids, erreurs de sortie différentes | `csv/t-o-sortie.csv` | D | — |
| III-4.6 | dup. 5 | Paralogues par profondeur | `csv/paralogues.csv` | D | — |
| III-4.7 | dup. 6 | Spectre de famille, couche 12 | `spectre-c12.json` | D | — |
| III-4.8 | dup. 7 | **L'arbre phylogénétique des experts de la couche 23** (MDS, arbre couvrant maximal) | `csv/phylogenie-c23-noeuds.csv`, `-aretes.csv`, `phylogenie-c23.json` | D | fidélité en légende : 30,9 % de la variance, Spearman 0,61 (témoin 0,11) |

### Ch. 5. Codage prédictif et élagage

L'équipe n'a proposé aucune figure. Ses données en portent deux, à proposer :

| N° | Origine | Figure | Données | État | Réserve |
|---|---|---|---|---|---|
| III-5.1 | proposée ici | Débit-distorsion des partitions par κ et par e, base en point | `mesures/genome/predictif-elagage/debit-distorsion-12.csv` | D | entropies idéales, dit |
| III-5.2 | proposée ici | Hebbien : ce qui tient, ce qui sur-ajuste (erreur d'expert en calibration contre évaluation) | `resume-12.csv`, `sortie-experts-12-hebb.json` | D | — |

### Ch. 6. Le mimétisme (P1 à P6, tous jugés)

| N° | Origine | Figure | Données | État | Réserve |
|---|---|---|---|---|---|
| III-6.1 | P1 1 | Succès par bloc de 32 jetons, deux générations du 120b | `mesures/mimetisme/P1/figure-blocs.csv` | Tx | P1 « ouvert », pas tombé (juge P1 § 0) |
| III-6.2 | P1 2 | Fenêtres froides : succès LRU contre politique | idem | Tx | idem |
| III-6.3 | P1 3 | **Espace latent des blocs** : matrice cosinus des usages d'experts (4 608 dimensions) | `figure-topologie.csv` | Tx | — |
| III-6.4 | P2 1 | Distances de pile, bande (V, V + R] | `mesures/mimetisme/P2/` | Tx | Mattson 1970 à relire à la source |
| III-6.5 | P2 2 | Part disque contre R, inclusif contre exclusif | idem | Tx | — |
| III-6.6 | P2 6 bis | Trajectoire s = 0 à 3 (variante sélective) | idem | D | post-hoc, dit |
| III-6.7 | P3 | La paroi du routeur décalée de β | `genome/mimetisme/P3/figures/fig-paroi.tex` | T | schéma ; **P3 étage B en cours dans une autre session** : attendre |
| III-6.8 | P3 | Pareto défauts évités contre cellules changées | `fig-pareto.tex`, `mesures/mimetisme/P3/series/` | T | idem ; ajouter le point de l'étage B quand il sera jugé |
| III-6.9 | P4 | Précision-couverture et gain par session | `figures/p4-precision-couverture.csv`, `p4-gains-par-session.csv` | Tx | « ouvert, plutôt tombe » |
| III-6.10 | P5 | Coupe 2D d'un paysage à 5^10 états : Babai, optimum exact, un bassin | `mesures/mimetisme/P5/paysage-toy.csv` | Tx | — |
| III-6.11 | P5 | Où l'erreur est déplacée, par groupe de directions propres | `spectre-erreur.csv` | Tx | — |
| III-6.12 | P5 | Gains par instance ; amortissement en δ | `etape1/gains-d1.csv`, `etape1/table-delta.csv` | Tx | poids synthétiques (étape 1) |
| III-6.13 | P6 | Le plan octets économisés contre énergie perturbée ; r selon θ | `courbe-plan-decodage.csv`, `courbe-plan-prefill-B.csv` | Tx | — |
| III-6.14 | P6 | **Le simplexe de mélange** : 36 864 points dans le tétraèdre Δ³, les quatre plans w_i = 0,20 | à tirer des traces P6 | C, 3D | — |
| III-6.15 | P6 | Les séjours : temps contre expert, barres colorées par niveau | à tirer des traces P6 | C | — |
| III-6.16 | P6 | Le softmax du routeur comme loi de Fermi-Dirac | — | S | analogie, dit |
| III-6.17 | tri § 6 | La carte du monde vers le pipeline (concepts, étages F Q K R L J, verdicts) | `genome/mimetisme/tri.md` § 6 | S | — |

### Ch. 7. La synthèse de la ronde

| N° | Origine | Figure | Données | État | Réserve |
|---|---|---|---|---|---|
| III-7.1 | synth. F1 (= EDA « figure de synthèse ») | **La frontière commune** : bits par poids contre rapport de KL, gagnants pleins, perdants creux, flèche vers leur « promesse » ; à droite l'axe sans perte 3,8434 → 3,7064 → 3,6844 | `mesures/genome/construction/synthese/frontiere.csv`, `colonne-par-tenseur.csv` | D | R3 |
| III-7.2 | synth. F2 | **L'erreur d'expert ne prédit pas la KL** | `erreur-contre-kl.csv` | D | **R4** : le point de S\* doit venir de K10 |
| III-7.3 | synth. F3 | **Deux parts de la KL, position par position** (2 550 points, densités marginales, couleur par fenêtre) | `mesures/genome/etat-de-l-art/journaux/kl-frontiere-positions.csv`, `kl-synonyme-d1-positions.csv` | D | 32 experts sur 768 (protocole P1) |
| III-7.4 | synth. F7 | Les colonnes géantes : énergie et erreur des 2 880 colonnes (la 1011 à ×144 et ×334) ; classes de colonne de blk.0 gate | `mesures/genome/genome/csv/colonnes-energie-erreur.csv` (un tenseur) | D, puis C pour les autres | — |
| III-7.5 | synth. F9 | Où le brouillon paie : le plan (ρ, α), la droite α = 1 − ρ + b_d/b_e | calcul (lemme B2) et accords de fondations/05 | S + D | — |
| III-7.6 | synth. F10 | **L'espace latent des états de la couche 23** : 6 132 états colorés par l'expert premier, taille selon la marge | captures `h-L23.f32`, routage capturé | C, 3D | fidélité de la projection dite en légende |
| — | synth. F4 | Les régions du routeur comme polyèdres | — | voir III-11.6 | fusionnée avec T6, déjà tracée |
| — | synth. F6 | La roue des codons | — | voir III-8.1 | fusionnée |
| — | synth. F5 | La mutation synonyme avant et après | — | voir III-9.1 | fusionnée avec F-S1 |
| — | synth. F8 | Le format v1.2 au bit près | — | voir III-8.7 | fusionnée |

### Ch. 8. Le codon synonyme du zéro (lot A)

| N° | Origine | Figure | Données | État | Réserve |
|---|---|---|---|---|---|
| III-8.1 | codon F1 + synth. F6 | **La roue des seize codons** E2M1 : ±0 au même point, arc « synonyme », rayons épais selon la fréquence ; avant seize, après quinze ; la pièce du signe des zéros (0,9999999967 bit) | `mesures/genome/construction/codon/tables-octets.csv`, `histo-12-gptoss20b.npz` | D | — |
| III-8.2 | codon F2 | La carte des 256 octets avant et après le fondu | `memoire/figures/tome3/donnees/codon-octets-v1{0,2}.csv` | **T** | — |
| III-8.3 | codon F3 | Le théorème tenseur par tenseur (180 tenseurs sur la diagonale) | `codon-theoreme-{20b,120b}.csv` | **T** | — |
| III-8.4 | codon F4 | La machine à états de l'accumulateur (−0 inatteignable) et les 8 640 lignes à 0 différence | journaux A1 | S + D | — |
| III-8.5 | codon F5 | Pourquoi la colonne reste dehors (12 tenseurs, seuil 0,015 bit) | `colonne-par-tenseur.csv` | D | — |
| III-8.6 | codon F6 + F-S7 + F-J1 + F-J2 | **Le J1 en ABBA** et ce qu'il attribue | `codon-j1-v1{0,2}.csv` (tracée), `mesures/genome/construction/juge/figures/vitesse-passes.csv`, `disque-passes.csv`, `mesures/disque/placement/juge/seance/` | **T à refaire** | **R1** |
| III-8.7 | synth. F8 | Le format v1.2 au bit près : en-tête, champs changés surlignés, chemin d'un demi-octet | `genome/05-synthese.md` § 4.3, `06` § 2 | S | — |
| III-8.8 | F-J6 | Le codon avant et après : part des −0 des 96 experts tirés ; tailles des quatre fichiers | `mesures/genome/construction/juge/J-T1-echantillon.csv`, `J-T0-fichiers.json` | D | — |

### Ch. 9. Le génome synonyme (lot B)

| N° | Origine | Figure | Données | État | Réserve |
|---|---|---|---|---|---|
| III-9.1 | F-S1 + synth. F5 | **La mutation synonyme dans la base propre de H**, avant et après : (a) le spectre de H ; (b) e_k selon λ_k, frontière contre synonyme ; la part cumulée en calibration et en évaluation (l'aire est le sur-apprentissage) ; (c) une rangée de 32 poids, les codons changés marqués | (a)(b) `mesures/genome/construction/synonyme/figures/spectre-L08-E00-gate.csv` ; (c) `synonyme.py` sur la même matrice | D pour (a)(b), C pour (c) | — |
| III-9.2 | F-S2 | La queue de la KL : survie log-log sur 2 550 positions, Q2_0, frontière, λ = 1, λ = 0 | `kl/kl-{frontiere,synonyme,synonyme-l0}-768-positions.csv`, `repere/kl-q2_0-*` | D | — |
| III-9.3 | F-S3 + F-J3 | **B2, fenêtre par fenêtre** : forêt des différences appariées, bandes ± 2σ ; lot B sur R1, juge sur R1 et sur fenêtres neuves | `kl/apparie-*-par-fenetre.csv`, `mesures/genome/construction/juge/figures/apparie-par-fenetre.csv` | D | les fenêtres neuves sont de wiki.test (même corpus que R1) |
| III-9.4 | F-S4 | L'alphabet : histogrammes des 8 symboles par classe κ, H0 et H(symbole \| κ) | journaux du codeur | D | — |
| III-9.5 | F-S5 | Le chemin des octets en mode rapide | figure du Tome II | S | reprendre le style du Tome II |
| III-9.6 | F-S8 | La frontière des variantes à 768 experts | `07` § 0, `kl/B2-*.json` | D | R3 : protocole à 768 experts, ne pas mêler aux points à 32 de III-7.1 |
| III-9.7 | F-S6 | Le nuage des entrées d'un expert sur les trois premiers axes de H, ellipsoïdes d'erreur | captures de calibration | C, 3D | — |

### Ch. 10. Le juge de la construction

| N° | Origine | Figure | Données | État | Réserve |
|---|---|---|---|---|---|
| III-10.1 | F-J4 | **Les experts vus** : 24 × 32 cases du 20b, qui les a routées, combien | `mesures/genome/construction/juge/figures/routage-grille.csv` | D | 11 cases vides : experts jamais jugés |
| III-10.2 | F-J5 | Le décodeur du juge : 32 voies, sous-pas, somme préfixe ; le même en séquentiel | — | S | — |
| III-10.3 | F-J7 | La difficulté des fenêtres : KL par fenêtre, mode exact, λ = 0, λ = 1 | `figures/kl-par-fenetre.csv` | D | — |
| — | F-J1, F-J2 | « Le fichier, pas le format » ; la vitesse décomposée | — | **tombent** | refondues dans III-8.6 (R1) |
| — | F-J3, F-J6 | — | — | voir III-9.3, III-8.8 | fusionnées |

### Ch. 11. La géométrie tropicale (piste jugée)

Figures tracées par la piste, macros dans `genome/pistes/tropicale/figures-tropicale.tex` (compilées le
2026-10-22, FR et EN). Ce dossier appartient au flux des pistes : le Tome III les **inclut** sans les
modifier.

| N° | Origine | Figure | État | Réserve |
|---|---|---|---|---|
| III-11.1 à 11.5 | T1 à T5 | La courbe de la garde (57,1 % pour 10 %), par couche, survie de la marge, loi de bascule, extrapolation | T | — |
| III-11.6 | T6 (+ synth. F4) | **Les polyèdres réels du routeur de la couche 12** et la bande de garde | T (PNG) | version 3D (Blender) possible |
| III-11.7 | T7 | Le théorème du nombre de garde, κ\* = 0,108 | T | — |
| III-11.8 à 11.10 | indices 1-3 | Forêt des gains, profondeur contre temps, témoins sur une même échelle | D (`mesures/pistes/tropicale/indices/`) | à faire par la piste ou plus tard, pas par ce flux |

### Ch. 12. Les spectres (piste jugée le 2026-10-27, encore active)

`genome/pistes/spectres/figures/spectres-figures.tex` : survie log-log, α̂ par matrice, levier contre le
rang. État **T**. La piste tourne encore (plafond au-delà des échelles de rangée) : le Tome III les inclut
quand elle sera close ; ce flux n'y touche pas.

## 3. Les réserves à porter (ce qui rendrait une figure fausse)

- **R1, l'attribution du ×1,44 (corrigée le 2026-10-27).** Le gain du J1 vient du format v1.2 **par le motif
  de ses requêtes de lecture**, propre à ce disque (A lu au motif de B ×1,389 ; B lu au motif de A ×0,715 ;
  `genome/JUGEMENT-placement.md` §§ 0, 5.3, 5.6, 5.7), pas de ses 3,3 % d'octets ni de l'état du fichier.
  Tombent donc : le troisième panneau prévu pour F6 (« la disposition du fichier en rend 30 % »), F-J1
  « Le fichier, pas le format », la cascade F-J2 telle qu'écrite, et la lecture de F-S7. III-8.6 les
  remplace : (a) les huit passes ABBA, bande ± 2σ ; (b) octets lus par jeton (0,9671) contre jetons/s ;
  (c) le motif croisé du juge du placement en quatre barres (A natif, A au motif B, B natif, B au motif A),
  avec en encart les deux v1.0 égaux au bit (A et C) dont l'écart vient de la fragmentation de C (267 473
  extents, ×1,26) ; (d) la cascade refaite : v1.0 → part du motif du format → part des octets (≤ 3,4 %) →
  mode rapide r(R/B) → mesuré. La légende dit que ce gain ne se transporte pas à un autre disque sans y
  être remesuré. Vérifier aussi la légende actuelle de `\GrapheCodonJalon`.
- **R2 (Tome II, pour mémoire).** La légende proposée de P5 ter du placement dit « la longueur des requêtes
  décide » : J10 et J11 l'ont barrée (×0,851 et ×0,882) ; dire « motif v1.0 ».
- **R3, ne pas mêler les protocoles.** `frontiere.csv` place λ = 1 « KL non mesurée » au protocole à 32
  experts (P1) ; la KL de λ = 1 à 768 experts (0,1522) est un autre protocole. III-7.1 garde les points à 32,
  III-9.6 porte ceux à 768 ; aucune figure ne relie les deux par un trait.
- **R4, le point de S\*.** `erreur-contre-kl.csv` porte pour S\* un rapport de KL de 1,3349 (3 fenêtres).
  La passe K10 (10 fenêtres, `mesures/genome/genome/kl/comparer10-base-contre-recette.json`, commit 39e9aa4)
  le ramène à 1,018, et 05 § 2 a barré l'ancien chiffre. Le CSV doit être régénéré depuis K10 avant de tracer
  III-7.2, et le point de 3 fenêtres barré dans la légende s'il est montré.
- **R5, les figures hors style.** Les PNG du mimétisme (Tx) ne suivent pas la direction artistique : elles se
  refont en pgfplots depuis leurs CSV ; les PNG restent comme témoins de reproduction.
- **R6, les dossiers des autres flux.** `genome/pistes/`, `mesures/pistes/`, `outils/pistes/` sont au flux des
  pistes ; `genome/mimetisme/P3/` est en travail dans une autre session (étage B). On y lit, on n'y écrit pas.

## 4. Le bilan

Environ 80 figures après fusion : 14 tracées au style (T, dont 10 par les pistes), une douzaine tracées hors
style (Tx), 37 aux données prêtes (D), 6 à calcul neuf sur le processeur (C), 12 schémas (S), aucune qui
demande la carte. Une seule doit être refaite pour rester vraie (III-8.6, R1) ; une demande un CSV régénéré (III-7.2,
R4).

## 5. Le premier flux (court, avec un juge)

Il prend les figures qui portent le Tome III, aux données prêtes, sans carte et hors des dossiers des autres
flux. Le reste suit dans un second flux, inventaire à la main.

- **Lot « construction »** (ch. 8 à 10) : III-8.1, III-8.4, III-8.5, **III-8.6 (refaite, R1)**, III-8.7,
  III-8.8, III-9.1 (a)(b), III-9.2, III-9.3, III-9.6, III-10.1, III-10.3.
- **Lot « ronde »** (ch. 1 à 4 et 7) : III-1.1, III-1.2, III-2.1, III-7.1, **III-7.2 (R4)**, III-7.3, III-7.4,
  III-3.4, III-3.6, III-4.2, III-4.8.
- **Lot « espaces latents »** (calcul sur le processeur, mémoire bornée à 3 Go) : III-7.6, III-9.1 (c),
  III-9.7 (plane ; la 3D seulement si le temps le permet).
- **Juge** : refait chaque nombre de légende depuis les CSV par son propre chemin, régénère chaque CSV par
  son script et compare au bit, compile les deux langues, cherche les phrases barrées qui survivraient dans
  une légende (R1 à R4), et juge le design (cohérence de la palette, lisibilité, une idée par figure).

Restent pour plus tard : le mimétisme en pgfplots (Tx), les schémas du ch. 3, III-4.3 à III-4.7, III-5.x,
III-6.14 et 6.15, III-7.5, III-9.4, III-9.5, III-10.2, les inclusions des pistes, et la rédaction des chapitres.

## 6. Ce qui pourrait être faux

- Les notes ont été lues pour leurs figures, pas mot à mot dans leurs dérivations : une figure proposée hors
  d'une section « figures » peut manquer.
- L'existence des CSV est vérifiée, leur contenu ne l'est pas : c'est le rôle du juge.
- Le compte du § 4 est fait à la main, à quelques unités près.
- La répartition placement → Tome II suit le juge du placement ; Stone peut la changer.
