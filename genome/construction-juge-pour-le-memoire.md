# Le juge de la construction : ce qu'il laisse au mémoire (Tome III)

Rôle : juge indépendant des lots A et B (genome/JUGEMENT-construction.md). Ce qui suit est la matière du
chapitre « L'épreuve de la construction » : les dérivations posées en entier, les données (CSV) et les
figures que ce travail mérite. Tous les chiffres viennent des journaux sous
`mesures/genome/construction/juge/` ; les CSV des figures sont écrits par
`outils/genome/construction/juge/donnees_juge.py` sous `mesures/genome/construction/juge/figures/`.

---

## D'où on part, où on va

Au départ : deux lots qui se disent finis, et des chiffres qui n'ont été produits que par leurs auteurs, sur
les fenêtres où leurs mécanismes ont été mis au point. Ce chapitre établit ce qui en survit quand un autre
les refait par d'autres chemins (un autre décodeur, un autre texte, un autre plan d'expérience), et
montre, chiffres en main, qu'un gain de vitesse peut être vrai pour des fichiers et faux pour le mécanisme
qu'on croyait mesurer. Ce qui reste : JUGEMENT § 11.

---

## 1. Dérivations

### 1.1 Le décodage rANS vectorisé est le décodage normatif

**Notation** (ARCHITECTURE § 4.9.2). Une tuile t a 32 voies d'états x_l ∈ [L, 2³²), un pointeur p dans
le tableau partagé `mots`, et parcourt ses macro-pas m, puis ses sous-pas k, puis ses voies l = 0 … 31
**dans l'ordre**. Un pas de la voie l calcule, avec la table c du contexte de son mot :
fente = x_l mod M ; s = sym_c(fente) ; y_l = f_c(s) · ⌊x_l / M⌋ + (fente − cum_c(s)) ; si y_l < L,
x_l ← 2¹⁶ y_l + mots[p] et p ← p + 1, sinon x_l ← y_l.

**Lemme J1 (indépendance des voies à un sous-pas).** Au sous-pas (m, k), y_l ne dépend que de x_l et de
la table du contexte du mot w = 32 m + l. *Démonstration* : les seules entrées du calcul de y_l sont x_l,
fente (fonction de x_l) et la table ; aucune autre voie n'y entre. ∎

**Proposition J2 (attribution des mots par somme préfixe).** Soit r_l = [y_l < L] et
R_l = Σ_{l' ≤ l} r_{l'}. Le traitement séquentiel l = 0 … 31 donne à toute voie l avec r_l = 1 le mot
mots[p₀ + R_l − 1], où p₀ est le pointeur au début du sous-pas, et laisse le pointeur à p₀ + R_31.
*Démonstration* par récurrence sur l : avant la voie l, le pointeur vaut p₀ + R_{l−1} (les voies
précédentes qui ont renouvelé l'ont avancé d'une unité chacune) ; si r_l = 1, la voie lit
mots[p₀ + R_{l−1}] = mots[p₀ + R_l − 1] et avance le pointeur à p₀ + R_l ; sinon il reste p₀ + R_{l−1} =
p₀ + R_l. ∎ Par le lemme J1, les y_l se calculent tous avant toute écriture ; par J2, les nouveaux états
aussi. Les tuiles étant indépendantes (chacune part de `début[t]` et de ses 32 états), le décodeur peut
traiter T × 32 voies à chaque sous-pas : 1 024 itérations par flux de codes au lieu de 4 147 200 pas. La
fin de tuile (toute voie sur L) se contrôle à la fin. C'est le décodeur du juge ; 96 experts sur 96 et
40 témoins sur 40 lui donnent raison au bit (JUGEMENT § 2.3).

### 1.2 Ce que le témoin v1.0 → v1.2 prouve

Soit D₀(x) et D₂(x) les demi-octets décodés de l'expert x dans le v1.0 et le v1.2, G(x) ceux du GGUF, et
κ(g) = g si g ≠ 8, 0 sinon. Le témoin mesure D₀(x) = G(x) (v1.0 sans perte), et le contrôle (b) mesure
D₂(x) = κ(G(x)). Alors {i : D₀(x)_i ≠ D₂(x)_i} = {i : G(x)_i ≠ κ(G(x)_i)} = {i : G(x)_i = 8} : l'ensemble
des demi-octets changés est **exactement** celui des −0, ce que le journal vérifie expert par expert
(L19 E109 du 120b : 1 746 601 et 1 746 601). C'est la forme mesurée de la phrase « la v1.2 ne change que le
signe des zéros ».

### 1.3 La séance à trois fichiers, et ce qu'elle sépare

**Le plan** A B R R B A A B R R B A : les rangs moyens des trois fichiers valent tous 6,5. Si la vitesse
d'une passe de rang i est v_X (1 + a + b i) (une dérive linéaire de la machine), la moyenne des quatre
passes de X vaut v_X (1 + a + 6,5 b) pour X = A, B, R : le rapport des moyennes est v_X / v_Y, sans terme
de dérive. (Le plan n'équilibre pas une dérive quadratique : sommes des rangs au carré 230, 214 et 206.)

**La décomposition.** Avec trois fichiers mesurés dans la même séance,
  r(R/A) = r(R/B) · r(B/A).
Le lot A mesure r(B/A) (v1.2 contre v1.0) ; le lot B mesure r(R/A) (rapide contre v1.0 d'origine). Le
toit que le format peut rendre à disque limitant est le rapport des octets lus par jeton, b_A / b_B
(0,9671⁻¹ = 1,034 pour la v1.2 ; JUGEMENT § 6). Tout r(B/A) au-delà vient d'ailleurs que du format. La
part du mode rapide se lit alors dans r(R/B), **à état de fichier comparable** (B et R ont été écrits le
même jour, par le même écrivain) ; son toit est b_B / b_R.

**Le seuil.** Avec σ = max(σ_A, σ_B, σ_R), écarts-types relatifs de quatre passes, le gain publié g du
lot B est un gain du mode si r(R/B) ≥ g (1 − 2σ). Le facteur (1 − 2σ) est la borne basse d'un rapport
de médianes à deux écarts-types de son bruit.

### 1.4 L'incertitude d'une KL moyenne : par positions, ou par fenêtres

Les 255 positions notées d'une fenêtre partagent leur passé, donc leurs bascules de routage : elles ne
sont pas indépendantes. L'écart-type par fenêtres, σ_f = s(K̄_1 … K̄_10) / √10, en tient compte ;
l'écart-type naïf σ_n = s(K_1 … K_2550) / √2550 non. Leur rapport donne l'effet de plan
deff = (σ_f / σ_n)² et un nombre de positions efficaces n_eff = n / deff. Sur R1, frontière :
σ_f = 0,0376, σ_n = 0,0066, deff ≈ 32, n_eff ≈ 79 [calc.] : une fenêtre de 255 positions vaut environ
huit positions indépendantes. Pour une **différence appariée**, deff est bien plus petit (λ = 0 contre
λ = 1 : 0,0097 contre 0,0038, deff ≈ 6,4), parce que l'appariement retire la difficulté propre à chaque
fenêtre. C'est pourquoi les lots ont raison de juger par des différences appariées, et pourquoi une KL
absolue publiée avec σ_n (07 § 0) paraît trois à six fois plus précise qu'elle n'est.

### 1.5 Refaire un résultat à 2 σ

Si une différence appariée est mesurée à z = d̄ / σ = 2,09 sur dix fenêtres, et que la vraie différence
vaut exactement d̄, une seconde série de dix fenêtres de même σ la redonne au-delà de 2 σ avec la
probabilité Φ(z − 2) = Φ(0,09) ≈ 0,54 [calc.]. Si la vraie différence est plus petite que d̄ (le résultat
retenu parce qu'il passait le seuil est biaisé vers le haut), cette probabilité baisse. Ma prédiction
déclarée (« égales ») suivait ce calcul ; la mesure l'a démentie (JUGEMENT § 5) : z = 3,62 sur les
fenêtres neuves.

---

## 2. Les données (CSV)

| Fichier | Contenu | Figure |
|---|---|---|
| `J-T1-echantillon.csv` | les 136 décodages (96 en v1.2, 40 témoins en v1.0) : contrôles, −0 du GGUF, durée | F-J6 |
| `J-T0-fichiers.json` | tailles, tables, empreintes des quatre fichiers | F-J6 (panneau tailles) |
| `figures/kl-par-fenetre.csv` | KL par fenêtre, R1 et neuves, par chemin et par variante | F-J3, F-J7 |
| `figures/apparie-par-fenetre.csv` | différences appariées par fenêtre | F-J3 |
| `figures/routage-grille.csv` | appels de chaque (couche, expert) du 20b, R1 et fenêtres neuves | F-J4 |
| `figures/vitesse-passes.csv`, `figures/disque-passes.csv` | chaque passe des deux séances | F-J1, F-J2 |
| `logits/comparer-*.json` | les comparaisons d'empreintes de logits | tableau |

---

## 3. Les figures que ce travail mérite

Belles et vraies : chacune se tire des CSV ci-dessus par un script commité, dans la direction artistique du
mémoire.

- **F-J1 « Le fichier, pas le format ».** Pour chaque fichier mesuré à l'étage disque (A120, B120, R120,
  A20, B20, R20), le débit en Go/s (deux passes, barres d'erreur), placé contre sa date d'écriture ; une
  bande horizontale autour de chaque fichier v1.0 large du toit du format (+3,4 %) ; les flèches de A à B
  montrent que l'écart mesuré dépasse dix fois ce que le format peut rendre. Le contenu n'y est pour rien :
  deux fichiers égaux au bit (A120 et C120, mesurés par le lot A) y ont deux hauteurs.
- **F-J2 « La vitesse décomposée ».** Une cascade par modèle : jetons par seconde du v1.0 d'origine → part
  du fichier (r(B/A) moins le toit du format) → part du format (≤ 3,4 %) → part du mode rapide (r(R/B),
  contre son toit b_B / b_R) → mesuré. La même cascade, dessinée avec le seul rapport publié par le lot B
  (×2,00), montre où il range ce qui revient au fichier.
- **F-J3 « B2 hors de R1 ».** Un graphe en forêt : pour chaque fenêtre, d = KL(λ = 0) − KL(λ = 1), un point ;
  deux bandes, R1 par la référence substituée (le chemin du lot B) et fenêtres neuves par le moteur, plus
  une troisième pour λ = 0 contre la frontière (R1 et neuves, référence substituée) ; la moyenne et ± 2 σ
  par fenêtres de chaque bande ; la ligne du zéro. On y voit la fenêtre 7 de R1, seule contre, la fenêtre 0
  des neuves, seule contre, et que les fenêtres neuves redonnent le signe avec plus de marge (3,6 σ contre
  2,1). Données : `figures/apparie-par-fenetre.csv` (comparaisons `r1-l0-contre-l1`,
  `neuf-moteur-l0-contre-l1`, `r1-l0-contre-frontiere`, `neuf-sub-l0-contre-frontiere`).
- **F-J4 « Les experts vus ».** La grille des 24 couches × 32 experts du 20b : chaque case colorée par qui
  l'a routée (R1 seul, fenêtres neuves seules, les deux, aucune), son intensité par le nombre d'appels
  (échelle logarithmique). C'est une carte de l'espace que le routeur parcourt sur du texte réel ; les
  11 cases vides sont les experts qu'aucune mesure de la construction n'a jugés.
- **F-J5 « Le décodeur du juge ».** Un schéma TikZ : une tuile, ses 32 voies en colonne, trois sous-pas en
  ligne ; à chaque sous-pas, les voies qui renouvellent allumées, et des flèches du flux partagé `mots`
  vers elles, dans l'ordre de la somme préfixe (proposition J2) ; à côté, la même chose en séquentiel.
  Avant et après : le même flux lu de deux manières, la même suite de symboles.
- **F-J6 « Le codon, avant et après ».** À gauche, la part des −0 de chacun des 96 experts tirés, par
  couche, contre la moyenne du fichier (6,39 % et 6,28 %) ; à droite, les tailles des quatre fichiers et
  le gain par poids d'expert (0,12791 et 0,12562 bit), avec le seuil A-C2.
- **F-J7 « La difficulté des fenêtres ».** La KL par fenêtre du mode exact, de λ = 0 et de λ = 1, R1 et
  neuves côte à côte (vingt colonnes) : la variance d'une fenêtre à l'autre est ce qui fait σ_f ≫ σ_n
  (§ 1.4).

---

## 4. Ce qui pourrait être faux

Voir JUGEMENT § 9 ; pour le mémoire, retenir : les fenêtres neuves sont de wiki.test (même corpus que R1) ;
le chemin du moteur et le chemin de la référence substituée diffèrent de 0,002 à 0,004 en KL ; la séance
de vitesse est une seule séance par modèle, sur une seule machine, un seul matin.
