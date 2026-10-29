# Reprise : figures du Tome III, lot « espaces latents » (calcul sur le processeur)

Premier flux de figures du Tome III (inventaire : `memoire/tome3/INVENTAIRE-figures.md` § 5). Lot : III-7.6,
III-9.1 (c), III-9.7. Préfixe de style `lat`. Tenu le 2026-10-27.

## Fait

- **III-9.1 (c)**, une rangée de 32 poids. `\GrapheLatentsRangee` (+ `\LegendeCourteLatentsRangee`,
  `\LegendeLatentsRangee`, `\SourceLatentsRangee`). Données : `outils/genome/tome3/latents_rangee.py` →
  `mesures/genome/tome3/latents/rangee-L08-E00-gate.{csv,json}`. Compilée FR et EN.
- **III-9.7**, le nuage des entrées sur (u1, u2) et (u1, u3), ellipses frontière et synonyme. `\GrapheLatentsNuage`
  (+ légendes). Données : `outils/genome/tome3/latents_nuage.py` → `nuage-L08-E00-gate-{points,ellipses}.csv`, `.json`.
  Compilée FR et EN. Figure plane seulement.
- **III-7.6**, l'espace latent des 6 132 états de la couche 23. `\GrapheLatentsEtats` (+ légendes). Script
  `outils/genome/tome3/latents_etats.py`, seuil de t-SNE déclaré et commité avant la passe (commit 47b96c2) →
  `mesures/genome/tome3/latents/etats-c23.{csv,json}` (passe de 22 min, un fil). ACP : plan 21,0 % de la variance,
  T(10) 0,792, C(10) 0,917, Spearman 0,59. t-SNE : T 0,947, C 0,959, Spearman 0,41 → **gardée** (seuil tenu).
  Accord de l'expert premier avec ses 10 voisins : 48,1 % (origine), 28,7 % (ACP), 44,2 % (t-SNE), 12,2 % (hasard).
  Compilée FR et EN.
- Commun : `outils/genome/tome3/latents_commun.py` (lectures GGUF, .sym, captures) ; `memoire/outils/tome3_latents.py`
  (écrit `memoire/figures/tome3/donnees/latents-*.csv` et `latents-chiffres.tex`, chaque nombre des légendes en
  macro `\EF{en}{fr}`) ; `memoire/figures/tome3/latents-figures.tex` (les macros) ; pilote
  `memoire/essai/pilote-tome3-latents.tex` (ignoré par git ; PDF `pilote-tome3-latents.pdf` et `-en.pdf`).

## Décisions (prises sans question, à relire)

- **Marge du routeur** = z(4) − z(5), écart entre 4e et 5e logit biaisé (définition de la capture et de la piste
  tropicale) ; z(1) − z(2) gardé au CSV pour mémoire. Taille des points : trois classes par quantiles (sous le
  10e centile : gros ; jusqu'à la médiane : moyen ; au-delà : petit), les gros dessinés en dernier : ~~ce sont les
  états de petite marge qui « dessinent les frontières ».~~ Barré le 2026-10-27 (second flux, rôle latents) : faux
  pour cette marge. Le juge des chiffres l'a mesuré (`JUGEMENT-figures-latents.md`, § 2.1, M2) : la part des 10
  voisins d'un autre expert premier vaut 0,51 pour les gros points, 0,54 jusqu'à la médiane et 0,51 au-delà (espace d'origine) ; c'est
  z(1) − z(2), la marge de la couleur, qui marque les bords (0,67 contre 0,43). III-7.6 dessine désormais
  z(1) − z(2) (`REPRISE-figures2-latents.md`).
- **Couleurs** : les huit experts premiers les plus fréquents (choisis par le script, pas à la main), sur les
  séries du préambule + `latRose` ; les autres en gris. ~~25 experts premiers distincts~~ 27 experts premiers distincts (barré le 2026-10-27 : le
  JSON et la légende disent 27, M9 du juge des chiffres) : 32 couleurs seraient illisibles.
- **ACP** centrée non réduite sur h (2 880 dimensions) ; **t-SNE** écrite de zéro en numpy (ni sklearn ni umap
  sur la machine, rien installé), un seul fil BLAS pour être déterministe ; gardée seulement si T(10) et C(10)
  ≥ ceux de l'ACP (seuil déclaré avant, dans le script commité).
- **Rangée** : même matrice que `spectre-L08-E00-gate.csv` (couche 8, expert 0, gate) ; symboles lus dans les
  .sym du lot B (`frontiere`, `synonyme-l1-d1`), pas recalculés ; bloc tiré (graine 20261027) parmi ceux dont le
  nombre de symboles changés égale la médiane (4 sur 32) : typique par construction.
- **Nuage** : même matrice, mêmes entrées de calibration ; H non amortie et non centrée (celle du lot B) : u1
  porte la moyenne des entrées (le nuage est à u1ᵀx ≈ 16,5). Ellipse de l'erreur = image du cercle unité par
  M^{1/2}, M = Bᵀ ΔWᵀ ΔW B ; fonction d'appui ‖ΔW v‖. Ellipses centrées à l'origine (l'erreur est linéaire en x),
  une flèche va de l'origine à l'entrée moyenne. Facteur commun F = 2√λ2 / plus grand demi-axe frontière.
  Paire de plans : (u1, u2) et (u1, u3).
- 3D Blender (III-9.7) : non faite (priorité aux figures planes).

## Témoins (tous tiennent, cassures tombent)

- W0 (états) : routeur relu = journal de routage, 6 132 ensembles sur 6 132, poids à 2,8e-8 ; sans biais : 3 482.
- W1 (états) : ACP complète T = C = 1 ; plan permuté T = 0,500.
- R0 (rangée) : ‖W − Ŵ‖² = Σ e_k du CSV du lot B à 1,8e-12 ; .sym de l'expert 1 : écart ×41.
- N0 (nuage) : λ1-3, e1-3 = CSV du lot B à 3,4e-10 ; H d'évaluation : λ1 bouge de 5,5 %.

## Reste

- Le juge du flux : régénérer chaque CSV par son script et comparer au bit (les JSON portent `duree_s`, qui
  change d'une passe à l'autre : comparer les CSV et les champs hors durée) ; `latents_etats.py` demande ~22 min.
- III-9.7 en 3D (Blender, sans rien installer) : non faite ; les CSV de points et d'ellipses suffisent à la tirer
  (ajouter c3 et l'ellipsoïde 3 × 3 M au script).
- III-7.6 en 3D : non faite.
- Les chapitres (rédaction) ne sont pas de ce flux : les macros `\LegendeLatents*` et `\SourceLatents*` sont prêtes
  à inclure (`\caption[\LegendeCourteLatentsX]{\LegendeLatentsX}\sourcefig{\SourceLatentsX}`).

## Pièges

- L'outil d'écriture refuse le dépôt (session en worktree) : écrire dans le brouillon puis `cp`.
- Un nombre négatif dans une macro passée en mode math (`2^{\LatRangExpoRel}`) : écrire `\ensuremath{-}`, pas `$-$`.
- `quiver` : `v={\thisrow{a}-\thisrow{b}}`, pas `v expr`.
- La légende `legend to name` appelée par `\ref` se colore comme un lien : `\pgfplotslegendfromname`.
- t-SNE à 6 132 points, gradient exact : environ 3 min par 100 pas sur un fil.
- `sed` avec un remplacement qui commence par `\L` : GNU sed passe en minuscules (`\LatPv` → `atpv`). Éditer à l'outil.
- Clé des couleurs en pastilles TikZ (`\LatPastille`) plutôt qu'en légende pgfplots : colonnes inégales sinon.
