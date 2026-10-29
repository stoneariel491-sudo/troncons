# Juge P6 : seuils déclarés avant tout calcul

Écrit le 2026-10-27, rôle « juge indépendant de P6 », avant d'avoir lancé le moindre calcul sur les traces.
J'ai lu `resultat.md`, `00-seuils-declares.md` et `tiers.py` (pour savoir quelle règle le rôle de mesure a
déclarée), et le cœur de `outils/mimetisme/physique/noyau-cache/src/main.rs` (pour la politique de cache :
compteur LFU gardé après éviction, départage par plus ancien groupe, jamais un membre du groupe). Mon outil
(`outils/mimetisme/P6/juge/juge_p6.py`) n'importe rien de `tiers.py` : lecteur, cache, étiquettes et règles
sont écrits à part, accès après accès, en Python pur ; la décroissance est calculée en 2^(−Δt/8) et non par
la table `exp` du rôle de mesure (les ex æquo peuvent donc différer d'un défaut : c'est voulu).

## 1. Reproduction du chiffre principal (variante A, génération du 120b, θ = 0,20, N = 323, LFU 8, ρ = 0,718)

- **Reproduit** si, pour chacune des 4 règles et chacune des 2 traces et au cumul, |S_juge − S_mesure| ≤ 0,002
  et |r_juge − r_mesure| ≤ 0,01 × r_mesure, **et** si la classe du verdict (« ouvert ») est la même.
- **Non reproduit** sinon : par défaut, ne tient pas.
- Point dur : `gen-wiki`, accepter, S = 7,78 % (le seul écart au seuil de 8 %, de 0,22 point).

## 2. Variante B (préremplissage, lots de 512, 120b, 4 genres de lecture)

- **Reproduit** si r_B et r_A à S = 8 % sont redonnés à 5 % relatifs près sur les 4 genres et le verdict
  déclaré (« tient », 3 genres sur 4) est le même.
- **Ma prédiction, déclarée avant** (elle peut tomber) : la règle B classe par la somme des poids et elle est
  jugée sur la somme des carrés des poids ; elle est donc presque l'oracle de sa propre mesure. Je calcule
  l'oracle (classement par Σw² lui-même, le meilleur possible pour cette mesure à octets égaux). Prédiction :
  r_B ≤ 1,30 × r_oracle sur 4 genres sur 4. Si elle tient, l'étape 0 de B n'avait presque aucun pouvoir
  d'éliminer la masse, et le « tient » de B ne dit rien de plus que « l'énergie se concentre dans les experts
  souvent appelés » ; seule l'étape 1 (KL) jugera. Si r_B > 1,30 × r_oracle sur 2 genres ou plus, ma
  prédiction est fausse et je le dirai.

## 3. Témoin du juge

- **T-J0** : θ = 0 → S = 0 et E = 0 ; θ = 2 avec « accepter » → r = 1 à 1e-9. Si non, mon outil est faux.
- **T-J1 (cassure qui doit tomber)** : poids remplacés par un tirage uniforme indépendant de la position
  (même loi marginale par permutation globale de tous les poids de la trace, étiquette décidée sur ce poids
  permuté), règle « accepter » jugée sur le **vrai** poids : r doit monter dans [0,90 ; 1,10] au cumul des
  deux générations (la porte ne voit plus rien du vrai poids). S'il reste sous 0,90, mon estimateur est biaisé.
- **T-J2** : mon nombre de défauts redonne celui du rôle de mesure à ±2 par trace.
