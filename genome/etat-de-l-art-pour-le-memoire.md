# Pour le mémoire : l'état de l'art et l'éclaireur du génome des poids

Note de l'éclaireur au rédacteur (2026-10-17). Tout chiffre ci-dessous vient d'un fichier commité ;
l'adresse est donnée. Chapitre proposé : « Le génome des poids, I : l'état de l'art et deux codons
synonymes », EN et FR.

## 1. Ce que le chapitre doit montrer (plan)

1. La question posée par la machine (toit, bits lus par poids) et la frontière (3,8431 ; 2,6441 à
   4,29 %), avec la figure du format MXFP4 au bit près (bloc de 17 octets, E8M0, demi-octets).
2. L'état de l'art en douze familles (genome/00-etat-de-l-art.md § 2), en tableau : dépendance
   exploitée, mesure de troncons qui la juge, pronostic (§ 4 de 00).
3. Où est le bruit, où est la structure : le signe des zéros (tableau de 01 § 2.1, figure en barres
   par tenseur depuis `journaux/zero-compte-20b.json` et `zero-compte-120b.json`, champ
   `par_tenseur`) ; la concentration de l'énergie par exposant (figure cumulative depuis
   `journaux/borne-rd-passe1.json`, champ `exposants`).
4. La borne distorsion-débit (figure : courbe `uniforme_precis` de `journaux/borne-rd.json`, en
   bits contre D log, avec le point de la frontière (2,6441 ; 4,29 %) et le point « frontière sur code
   canonique » (2,5965 ; 4,29 %)).
5. Mécanisme 1, le codon synonyme du zéro : proposition et démonstration (ci-dessous § 2.1), tableau
   de mesure (01 § 4.3), preuve au bit (SHA-256 égales, `journaux/kl-zero-canonique.sha256`).
6. Mécanisme 2, la mutation synonyme : dérivation (§ 2.2 à 2.4 ci-dessous), protocole, diagnostic
   de sur-apprentissage (`journaux/diagnostic-L0-E0.json`), choix de δ (`journaux/choix-delta.json`),
   résultats (`passes/*.json`, `passes/*.csv`), KL (`journaux/kl-*-juge.json`).
7. Ce qui pourrait être faux (01, dernière section).

## 2. Dérivations entières

### 2.1 Exactitude au bit d'un produit scalaire après −0 → +0

Soit `y = fl(…fl(fl(t_1 + t_2) + t_3)… + t_n)` une somme IEEE 754 (arrondi au plus près) dans un
ordre fixé, `t_j = fl(w_j x_j)`, et `w'` égal à `w` sauf `w'_j = +0` là où `w_j = −0`. Alors
`t'_j = t_j` si `w_j ≠ −0`, et `t'_j, t_j ∈ {+0, −0}` sinon. Soit `S_k` (resp. `S'_k`) la k-ième somme
partielle. Hypothèse de récurrence : `S_k = S'_k` au bit, ou `S_k, S'_k ∈ {±0}`. Pas : si `t_{k+1}`
est non nul, `fl(S_k + t_{k+1}) = t_{k+1} = fl(S'_k + t_{k+1})` quand `S_k ∈ {±0}`, et l'égalité est
conservée sinon (mêmes opérandes) ; si `t_{k+1} ∈ {±0}` et `S_k ≠ 0`, `fl(S_k ± 0) = S_k` des deux
côtés ; si les deux sont nuls, les deux sommes restent dans {±0}. Conclusion : `y = y'` au bit dès
qu'un terme est non nul ; sinon `y, y' ∈ {±0}`, égaux en valeur. ∎ (Le cas des huit accumulateurs de
`trc-reference` est le même raisonnement appliqué à chaque accumulateur puis à la réduction en arbre.)

### 2.2 Le lemme d'OBS pour la quantification

Problème : `min_δ (w + δ − ŵ)ᵀ H (w + δ − ŵ)` n'est pas le bon cadre ; le bon est : la ligne courante
w (erreur cumulée comprise), la colonne j fixée à q_j, les colonnes libres F ajustées. Lagrangien
`L(δ, μ) = δᵀ H δ + μ (e_jᵀ δ − (q_j − w_j))` avec δ la modification de w ; `∇_δ = 2 H δ + μ e_j = 0`
⇒ `δ = −(μ/2) H⁻¹ e_j` ; la contrainte donne `μ/2 = −(q_j − w_j)/[H⁻¹]_jj` ; d'où
`δ = ((q_j − w_j)/[H⁻¹]_jj) H⁻¹ e_j` et `δᵀ H δ = (q_j − w_j)²/[H⁻¹]_jj`. Restreint aux colonnes
non encore fixées (la sous-matrice H_F de H sur {j} ∪ F), on obtient la règle séquentielle. ∎

### 2.3 Le facteur de Cholesky de H⁻¹ par une seule factorisation

Soit P la permutation qui renverse l'ordre. Si `P H P = L Lᵀ` (L triangulaire inférieure), alors
`H = (P L P)(P L P)ᵀ = V Vᵀ` avec `V = P L P` triangulaire supérieure ; `H⁻¹ = V⁻ᵀ V⁻¹ = Uᵀ U` avec
`U = V⁻¹ = P L⁻¹ P` triangulaire supérieure : c'est le facteur de Cholesky supérieur de H⁻¹ (unique à
diagonale positive). Coût `n³/3` (Cholesky) `+ n³/3` (inverse triangulaire) au lieu de `n³` (inverse)
`+ n³/3`. Vérification mesurée : écart relatif 7·10⁻¹⁴ au calcul direct (session, voir
`outils/genome/eclaireur/synonyme.py`, `facteur_inverse`).

### 2.4 Pourquoi la mutation synonyme rend la frontière quand H = I

Avec H = I, `U = I`, aucune correction ; chaque poids choisit le centre le plus proche de |w| (signe
de w). Les centres sont les centres de gravité (pondérés par s²) d'une partition **contiguë** des
magnitudes {0 ; 0,5} {1 ; 1,5 ; 2} {3 ; 4} {6}, de centres (0,237 ; 1,424 ; 3,419 ; 6) : les
frontières de Voronoï sont 0,831 ; 2,421 ; 4,709, et chaque magnitude tombe dans la cellule de sa
classe (0,5 < 0,831 < 1 ; 2 < 2,421 < 3 ; 4 < 4,709 < 6). Donc le symbole choisi est celui de la
fonction frontière. ∎ (Témoin T1 : 0 symbole différent sur 8 294 400.)

### 2.5 Points de Blahut-Arimoto comme bornes supérieures de R(D)

Voir 01 § 3 : pour tout canal Q et toute loi q, `Σ p Q log(Q/q) = I(V;Ŷ) + D(marge ‖ q) ≥ I(V;Ŷ) ≥
R(E d)`.

## 3. Données (CSV et JSON, sous `mesures/genome/etat-de-l-art/`)

| Fichier | Contenu | Figure |
|---|---|---|
| `borne-rd.csv`, `journaux/borne-rd.json` | courbes R(D) (allocation optimale non publiée ; `uniforme_precis` publiée comme bornes) | R(D) |
| `journaux/zero-compte-*.json` | ±0 par tenseur | barres |
| `journaux/zero-canonique.json`, `zero-temoin-sans-drapeau.json` | codeur rANS réel avec et sans le codon | tableau |
| `passes/<variante>-lam<λ>-damp<δ>[-e…].csv` | par (couche, expert, rôle) : erreurs de poids et de sortie | nuages, boîtes |
| `passes/*.json` | agrégats, débits | frontière débit-erreur |
| `frontiere.csv` | chaque mécanisme placé sur le plan débit × erreur de sortie | la figure de synthèse |
| `journaux/kl-*-juge.json`, `journaux/kl-*-positions.csv` | KL position par position, frontière contre synonyme (32 experts sur 768) | distributions cumulées de la KL |
| `sources.csv`, `recherches.csv` | sources et requêtes | annexe |

## 4. Sources

`memoire/sources/genome-etat-de-l-art.bib` (45 clés neuves, métadonnées primaires) ; clés déjà
présentes réutilisées (liste en tête du fichier).
