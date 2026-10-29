# Le codon synonyme du zéro (lot A) : ce qu'il faut au mémoire (Tome III)

Rôle « codon » de la construction, 2026-10-17. Livrable : genome/06-codon-v1-2.md. Ce fichier porte ce
que le rédacteur du Tome III doit reprendre : le plan du chapitre, les énoncés et leurs démonstrations
écrites en entier, les calculs posés, les données (CSV) et les figures que ce travail mérite, belles et
vraies, chacune avec ses données et le script qui la tire. Les chiffres viennent des fichiers commités
cités ; aucun n'est recopié de mémoire.

---

## 1. Plan du chapitre (« Un codon synonyme dans le format »)

1. D'où on part : MXFP4 a seize codes pour quinze valeurs (E2M1 : 0b0000 = +0, 0b1000 = −0) ; le
   quantificateur de gpt-oss garde le signe d'une valeur arrondie à zéro ; ce signe est une pièce de
   monnaie (H = 0,9999999967 bit, équipe prédictif-élagage) que le calcul ne lit jamais.
2. Le théorème du gain (§ 2.1) et son chiffre attendu ; la mesure de l'équipe prédictif-élagage.
3. Qui lit le code 8 : ggml, la GEMV du moteur, la référence f64 (§ 2.2, proposition A1 et son
   corollaire f64) ; les deux mesures de A1.
4. Le format v1.2 au bit près (tableau de 06 § 2, figure F2) ; l'invariant des tables (lemme § 2.3).
5. Pourquoi la colonne reste hors du format (le calcul de 06 § 2, figure F5).
6. Résultats : C1 en valeur sur 768 + 4 608 experts, tailles, logits au bit, J1 en ABBA.
7. Ce qui pourrait être faux ; ce qui reste.

---

## 2. Énoncés et démonstrations

### 2.1 Le gain exact du fondu (proposition, reprise de prédictif-élagage, écrite en entier)

Soit C le code de 4 bits d'un poids et V = v(C) sa valeur, v : {0, …, 15} → ℝ, v(c) = (−1)^{c₃} K[c & 7],
K = (0, 1, 2, 3, 4, 6, 8, 12). v est injective sauf sur {0, 8} (v(0) = v(8) = 0).

**Proposition.** H(C) = H(V) + P(V = 0) · H(S | V = 0), où S est le bit de signe.

*Démonstration.* V est une fonction de C, donc H(V | C) = 0 et H(C, V) = H(C). Par la règle de chaîne,
H(C, V) = H(V) + H(C | V). Sachant V = v ≠ 0, C est déterminé (v injective hors de 0) : H(C | V = v) = 0.
Sachant V = 0, C ∈ {0, 8} et C est déterminé par S : H(C | V = 0) = H(S | V = 0). D'où
H(C | V) = Σ_v P(V = v) H(C | V = v) = P(V = 0) H(S | V = 0). ∎

**Corollaire (le gain attendu par poids).** Fondre 8 dans 0 remplace C par C' = c(C) (c(8) = 0, c
l'identité ailleurs), et H(C') = H(V). Le gain d'entropie est P(V = 0) · H(S | V = 0) ≈ P(V = 0) bit
quand le signe est une pièce juste. Il vaut aussi conditionnellement à tout contexte connu du décodeur
(classe d'échelle κ, octet voisin) : remplacer H par H(· | κ) dans la démonstration ne change rien.

**Remarque sur l'alphabet octet.** Le flux CODES_CTX code des octets (deux demi-octets) avec une table
par classe d'échelle. La même démonstration, appliquée à l'octet O = (C_bas, C_haut) et à sa valeur
(V_bas, V_haut), donne un gain de P(V_bas = 0) H(S_bas | …) + P(V_haut = 0) H(S_haut | …) bits par octet
si les signes des zéros sont indépendants de tout le reste : par poids, P(V = 0) bit. Le chiffre mesuré
(06 § 5) se compare à 2 × (part des −0 fondus), puisque sous une pièce juste les −0 sont la moitié des
zéros.

### 2.2 Proposition A1 (la GEMV rend les mêmes bits) et son corollaire f64

Énoncé et démonstration : genome/05-synthese.md § 4.2 (à reprendre tels quels). Le corollaire pour la
référence f64 est dans 06 § 1 (« Pourquoi la référence rend aussi les mêmes bits ») : même récurrence,
huit accumulateurs partis de +0, FMA ; la réduction en arbre additionne des accumulateurs égaux au bit.

À ajouter au mémoire, la **limite exacte de A1** : la démonstration suppose les x finis. Si un x vaut
±∞ ou NaN, v·x vaut NaN pour v = ±0 dans les deux calculs, et la sortie est NaN des deux côtés ; seul le
bit de signe ou la charge utile d'un NaN pourraient différer, ce qui n'est pas un logit utilisable.

### 2.3 Lemme (l'invariant des tables suffit)

**Lemme.** Si la table d'un contexte donne f[s] = 0, aucun flux, juste ou corrompu, ne fait produire s
au décodeur normatif (ARCHITECTURE § 4.9.2).

*Démonstration.* Le décodeur lit e = lut[x mod 4 096] et rend s(e). Par construction de la LUT, la fente
i porte le symbole s tel que c[s] ≤ i < c[s] + f[s] ; si f[s] = 0, l'intervalle est vide et aucune fente
ne porte s. L'état x, quel qu'il soit, ne désigne qu'une fente. ∎ (La LUT compacte de la carte et la
LUT normative du processeur sont construites depuis les mêmes fréquences, lues dans la même section
TABLES ; le lemme vaut pour les deux.)

---

## 3. Calculs posés

- Colonne hors format, ordre de grandeur sur le 20b : (0,1416 + 0,1231) × 265 420 800 / 19 110 297 600
  = 0,0037 bit par poids ; 0,2647 × 265 420 800 / 8 = 8,78 Mo (06 § 2).
- Toit de vitesse à disque limitant (05 § 4.1) : 1 / (1 − 0,1257 / 3,8549) − 1 = 3,37 %.
- Alignement des tronçons sur 4 096 : au plus 4 608 × 4 096 = 18,9 Mo sur le 120b, 0,0013 bit par poids.
- Gain mesuré sur les tronçons [mes.] : (9 226 493 952 − 8 920 932 352) × 8 / 19 110 297 600 = 0,12791 bit
  (20b) ; (55 416 086 528 − 53 615 599 616) × 8 / 114 661 785 600 = 0,12562 bit (120b).
- Le corollaire : 2 × 0,0639288 = 0,12786 contre 0,12791 (20b) ; 2 × 0,0627889 = 0,12558 contre 0,12562
  (120b) ; tenseur par tenseur, écart de −0,00017 à +0,00016 bit (180 tenseurs).
- Octets lus par jeton au J1 (déterministe) : 686 756 916 / 710 118 798 = 0,9671.
- Tampons d'arrivée : 12 × (12 251 136 − 11 878 400) = 4 472 832 octets de mémoire épinglée en moins.
- J1 s2, machine calme [mes.] : r = 2,890 / 1,988 = 1,454, σ = 5,6 % ; même contenu au bit, deux fichiers v1.0 :
  1,742 / 1,343 = 1,30 à l'étage disque seul ; le v1.2 contre le v1.0 d'origine : 2,323 / 1,742 = 1,33. Toit du
  format : 3,37 % (ci-dessus). ~~L'écart de vitesse entre fichiers est donc un effet de disposition sur le disque
  d'un ordre de grandeur plus grand que l'effet du format (06 § 8).~~
  **Corrigé le 2026-10-27**, d'après `genome/JUGEMENT-placement.md` (§ 0, §§ 5.3, 5.6, 5.7, § 12 point 3), comme
  06 § 8 et `genome/JUGEMENT-construction.md` § 6 l'ont été le même jour : sur ce disque, l'écart B/A suit **le
  motif des requêtes de lecture que le format impose** (frontières et longueurs des tronçons) : A lu au motif de B
  va comme B (×1,389), B lu au motif de A va comme A (×0,715). Le gain du J1 est donc **un gain du format v1.2,
  propre à cette machine**, par le motif de ses tronçons et non par ses 3,3 % d'octets ; la variable exacte du
  motif n'est pas isolée (couper chaque requête du v1.0 en deux ne le répare pas : ×0,851 et ×0,882). Le toit de
  3,37 % ne vaut que pour les octets : il ne borne pas l'effet du motif. L'écart 1,30 entre les deux v1.0 au même
  contenu (A et C) vient, lui, de la fragmentation extrême de C (267 473 extents ; ×1,26 sur ses seuls tronçons
  d'un extent, J5 et J6). Ce qui a changé : le motif croisé du juge du placement (même fichier lu aux deux
  motifs), que la phrase barrée ne connaissait pas.

---

## 4. Données (CSV, commitées)

- `mesures/genome/construction/codon/tailles-par-tenseur.csv` : par modèle, couche, matrice : bits par
  poids des codes v1.0 et v1.2, gain, part des −0, δ (outil : `analyse_codon.py tailles`).
- `mesures/genome/construction/codon/tailles.json` : totaux.
- `mesures/genome/construction/codon/j1-<séance>-passes.csv` et `-verdicts.json` : le J1 ABBA.
- `mesures/genome/construction/codon/tables-octets.csv` : les fréquences des tables CODES_CTX, v1.0 et
  v1.2, couches 0, L/2, L − 1 des deux modèles (lecteur indépendant `tables_octets.py`).
- `mesures/genome/construction/codon/disque-s1.*`, `j1-s1-*` (sous charge) ; `disque-s2.*`, `j1-s2-*`,
  `j1-copie-s2-*` (machine calme, 2026-10-22 : c'est s2 que tire F6).

**Déjà tiré** (2026-10-17) : `memoire/figures/tome3/codon-figures.tex` (`\GrapheCodonTheoreme` = F3,
`\GrapheCodonOctets` = F2, `\GrapheCodonJalon` = F6) et ses données `memoire/figures/tome3/donnees/codon-*.csv`,
écrites par `memoire/outils/tome3_codon.py` ; compilé sans erreur par un pilote d'essai (scrbook,
`\input{../commun/preambule}`, `\input{../figures/tome3/codon-figures}`, puis les trois commandes). Le
préambule pose `col sep=comma` : les CSV sont à virgule. F2 se lit ainsi : la ligne et la colonne 8
s'éteignent, la ligne et la colonne 0 foncent ; les lignes 7 et F sont pâles dans les deux panneaux
parce que les codes ±12 sont rares. Restent à dessiner F1, F4, F5 (sans données neuves).

---

## 5. Les figures que ce travail mérite (belles et vraies)

Direction artistique commune au mémoire (SOCLE, 2026-10-17). Chaque figure se tire des CSV ci-dessus par
un script commité.

- **F1. La roue des seize codons.** Les seize codes E2M1 sur un cercle, rangés par valeur sur la droite
  réelle repliée (−12 … 12) ; les deux codes du zéro, 0b0000 et 0b1000, au même point, reliés par un arc
  « synonyme » ; l'épaisseur de chaque rayon proportionnelle à la fréquence mesurée du code dans gpt-oss
  (tables du fichier). Avant : seize rayons, deux superposés ; après : quinze. Analogie dite en légende :
  les codons synonymes du code génétique (GGU, GGC, GGA, GGG → glycine).
- **F2. La carte des 256 octets, avant et après.** Deux grilles 16 × 16 (demi-octet fort en ligne,
  faible en colonne), couleur = log de la fréquence de la table CODES_CTX (κ = 1) d'une couche ; après
  le fondu, la ligne 8 et la colonne 8 s'éteignent et leur masse se reverse sur la ligne 0 et la colonne
  0 ; une flèche de transport entre les deux panneaux. C'est la transformation du format, montrée sur
  les données.
- **F3. Le gain par tenseur le long de la profondeur.** 36 couches × 3 matrices du 120b (et 24 × 3 du
  20b) : gain mesuré en bits par poids contre 2 × part des −0 (le corollaire § 2.1), sur un même axe ;
  les points doivent tomber sur la diagonale ; l'écart dit ce que le contexte κ et l'alphabet octet
  changent au théorème.
- **F4. La machine à états de l'accumulateur (A1).** Un diagramme des états de s ∈ {+0, non nul} (−0
  barré, inatteignable) avec les transitions sur v = ±0 et v ≠ 0 ; à côté, l'histogramme mesuré des
  8 640 lignes : 0 différente.
- **F5. Pourquoi la colonne reste dehors.** Barres du gain de la colonne par tenseur (12 tenseurs du
  20b), le seuil de 0,015 bit en trait, la couche 0 seule au-dessus ; en encart, la part du modèle entier
  (0,0037 bit) contre le gain du zéro (0,128 bit) à la même échelle.
- **F6. Le J1 en ABBA.** Les huit passes dans l'ordre du temps, jetons/s et octets par jeton, A et B en
  deux teintes, la bande ± 2σ du bruit de v1.0 ; à droite, le rapport des octets lus (déterministe) contre
  le rapport des jetons/s (bruité). Données : séance s2. ~~**À ajouter pour être vraie** : un troisième
  panneau, Go/s de l'étage disque des trois fichiers (deux v1.0 identiques au bit à 1,74 et 1,34 ; v1.2 à
  2,32), pour que la figure ne laisse pas croire que le format rend 45 % : elle doit montrer que la
  disposition du fichier, à contenu égal, en rend 30 %.~~
  **Corrigé le 2026-10-27** (réserve R1 de `memoire/tome3/INVENTAIRE-figures.md`, d'après
  `genome/JUGEMENT-placement.md` § 0, §§ 5.3, 5.6, 5.7, § 12 point 3 ; voir aussi le § 3 ci-dessus) : ce troisième
  panneau tombe. Sur cette machine, le format v1.2 rend bien le moteur environ 45 % plus rapide sur le 120b, par le
  motif de ses requêtes de lecture (A lu au motif de B ×1,389, B lu au motif de A ×0,715), non par ses octets ni
  par l'état du fichier ; l'écart entre les deux v1.0 au même contenu vient de la fragmentation de C. La figure a
  été refaite selon R1 : III-8.6 (les huit passes ABBA, les octets par jeton contre la vitesse) et III-8.6 bis (le
  motif croisé en quatre barres avec, en encart, A120 et C120 et leur fragmentation, puis la cascade refaite), dans
  `memoire/figures/tome3/codon-figures.tex`. Elle dit que ce gain ne se transporte pas à un autre disque sans y
  être remesuré.
