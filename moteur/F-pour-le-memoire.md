# Lot F : ce que son travail mérite dans le mémoire

Le format `.trc`, son codec et son codeur ; la preuve C1. Données et dérivations commitées :
`mesures/moteur/F/derivations.md` (en entier), `mesures/moteur/F/journaux/*.json`,
`mesures/moteur/F/csv/*.csv`, sources `memoire/sources/moteur-F.bib`.

## Schémas (TikZ)

1. **M3, le fichier `.trc` à l'échelle** : les cinq sections avec leurs décalages et longueurs
   **réels** des deux fichiers (lus dans l'en-tête, journaux `verifier-*.json` ; 20b et 120b côte
   à côte), puis le zoom sur un tronçon : en-tête de 64 octets, table de 12 descripteurs, les 12
   flux par matrice (MEDIANES, BIAIS, DELTA, CODES_CTX) avec leurs tailles mesurées, bourrage
   jusqu'à 4 096.
2. **Un flux rANS sérialisé, au bit près** (§ 4.9.1) : en-tête de 16 octets, `début[T]`,
   `états[32 T]`, `mots[W]` ; et **la tuile** : 32 voies × 256 macro-pas × 4 sous-pas, le mot
   w = m · 32 + l, les quatre voies d'un bloc qui lisent la même LUT (κ du bloc) — c'est M4.
3. **Le chemin du codeur** : GGUF → (par couche) lecture d'un tenseur → préparation des 32 ou 128
   experts en parallèle → comptes → tables → codage par paquets → écriture dans l'ordre ; les
   zones réservées (TABLES, RÉPERTOIRE) remplies à la fin ; l'en-tête en dernier ; le fil du
   SHA-256 en parallèle.
4. **La vérification C1 à cinq contrôles** par expert (empreinte de partie, décodage, octets,
   empreinte du décodé, empreinte des tranches du GGUF), et où tombe la cassure de médiane.
5. **La symétrie codeur / décodeur** (lemme 3 et proposition 4) : la pile de mots, l'ordre inverse,
   les deux contrôles gratuits.

## Structures (tableaux champ par champ)

- En-tête fixe, MÉTA, RÉSIDENTS, TABLES, RÉPERTOIRE, partie, flux : les tableaux du § 4 avec la
  colonne « valeur lue dans le fichier » remplie depuis les vrais fichiers.
- Les sortes de flux et ce que chacune produit pour gpt-oss (R = C = 2 880, B = 90).

## Graphes (pgfplots, depuis les CSV)

1. **Bits par poids par tenseur et par couche** (codes, δ, médianes), 20b et 120b
   (`csv/taux-par-tenseur-*.csv`) : la régularité entre couches et entre gate, up, down.
2. **Taille des tronçons par couche** (min, moyenne, max ; `csv/troncons-par-couche-*.csv`).
3. **F1 contre le fichier** : les 12 tenseurs de F1, point par point (`csv/f1-contre-trc-20b.csv`),
   égalité au millionième.
4. **r₀₃ du fichier contre 03** (barres 20b, 120b, avec la bande de 0,1 %).

## Théorèmes et lemmes à écrire

Les lemmes 1 à 3, la proposition 4 (les deux contrôles gratuits, et pourquoi ils ne gardent pas
la table), la proposition 5 (contexte connu du décodeur : exactitude et taux), le calcul de la
classe d'échelle des blocs de bourrage, la formule de l'expert d'origine dans le GGUF, la
comptabilité du taux et l'écart à 03 (`derivations.md` § 1 à 7).

## Le témoin des témoins

Le tableau des neuf cassures du code (`casser-temoins-f1.log`) et ce que la passe 1 a appris :
un témoin qui juge une conjonction cache la perte d'un de ses termes.

## Listings commentés

`decoder_avec` (la boucle normative du § 4.9.2, avec les deux contrôles), `coder_avec`,
`decoder_matrice_v10` (δ → e, κ → table par voie), et la boucle de vérification d'un expert.

## Ajout de F3 : le codeur à mémoire bornée

- **Schéma** : les deux passes d'une couche (comptes par paquets → tables → relecture et codage
  par paquets → écriture dans l'ordre), avec la fenêtre de mémoire dessinée à l'échelle : un
  paquet de 12 experts (≈ 0,47 Go) contre la couche entière de la version à une passe (0,42 Go
  sur le 20b, 1,69 Go sur le 120b).
- **Proposition 6** (identité des deux passes : commutativité des comptes, tables fonction des
  comptes, tronçon fonction de l'expert et des tables, ordre conservé) et **proposition 7** (borne
  de mémoire, seul le terme des biais dépend de E) : `derivations.md` § 8, en entier.
- **Le témoin d'identité** : trois SHA-256 par `Get-FileHash` (`identite-20b-2passes.txt`) :
  F2 = deux passes, copie cassée différente. Un tableau suffit.
- **Graphe** : pointe de l'ensemble de travail (barres) du codeur et de la vérification, une passe
  contre deux passes, 20b et 120b (`csv/pointes-memoire.csv`, tiré des `*.cadre.txt` par
  `vers_csv.py`), avec la droite du seuil 1,25 × 20b.
- **Ce qui pourrait être faux** : les pointes sont des ensembles de travail relevés toutes les
  0,5 s par `lancer.ps1` (une pointe plus brève peut échapper) ; la machine était partagée.
- **Le défaut de l'erreur 87** (lecture sans tampon relancée à un décalage non aligné après la
  lecture courte de fin) : petit encadré « ce que le témoin n'avait pas couvert », avec la
  quatrième cassure qui le couvre désormais.

## Ajout du 2026-10-15, 21 h : le second chemin de C1

- **Schéma** (TikZ) : la chaîne des égalités de C1 sur le 120b, en deux colonnes. À gauche, le
  premier chemin : GGUF → `gguf::lire_dans` → codeur → `.trc` → `trc-codec` → D(x), avec
  « D = G₁ octet pour octet » et « h(D) = r ». À droite, le second : GGUF → lecteur Python (décalages
  croisés avec llama.cpp) → G₂(x) → h(G₂) = r. Au centre, le répertoire r(x) où les deux se
  rejoignent ; en pointillé, le maillon qui reste à un second décodeur (lot K sur la carte,
  épreuve du § 8). C'est la figure qui dit pourquoi le second chemin ferme la faille de
  `verdicts.md` sans décoder.
- **Proposition 8** et sa borne (4 608 · 2⁻⁶⁴ ≈ 2,5·10⁻¹⁶) : `derivations.md` § 9, en entier,
  avec la remarque sur l'adversaire (anniversaire en 2³²) et l'argument « deux programmes sans
  ligne commune devraient se tromper pareil ».
- **Tableau** : les six cassures du second chemin et ce que chacune fait tomber, sur les deux
  modèles (`verdicts.md`, `csv/second-chemin-c1.csv`) ; il montre que les cinq contrôles par expert
  voient chacun leur propre octet (le décalage fait tomber empreinte et médianes, pas les biais ;
  le biais faussé fait tomber empreinte et BIAIS, pas les médianes).
- **Encadré « lecture sans tampon »** : l'arrondi des requêtes à 4 096 et la vue rendue (§ 9 des
  dérivations), et pourquoi on ne prend pas de pages au cache des autres.
- **Encadré « ce que le témoin a attrapé chez son auteur »** : la version de l'outil lisait le
  numéro de version GGUF sur la magie (curseur à 0 au lieu de 4) ; la relecture croissante de la
  tête, faite pour les métadonnées longues, a alors grossi jusqu'au fichier entier (9,6 Go de
  RAM) avant d'échouer. Corrigé : curseur à 4, relecture bornée à 256 Mio. Leçon : une boucle de
  repli sans borne transforme une erreur d'analyse en charge pour toute la machine.
- **Sources** : `memoire/sources/moteur-F.bib` (`ggml_gguf`, `llamacpp_b11515_gguf`,
  `python_hashlib_313`).
