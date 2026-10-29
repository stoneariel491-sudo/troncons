# P3, étage B à N = 238 : ensembles biaisés calculés, avant toute passe (2026-10-27)

Outil : `outils/mimetisme/P3/p3_fichiers_N238.py` ; données : `mesures/mimetisme/P3/ensembles-N238.json`. Aucune KL lue. Critère : `03-critere-marge-declare.md` (commité avant ce calcul).

| β | défauts (LRU, N = 238) | variation contre β = 0 (108 472) | rejeu par `cache2.py` (second chemin) | cellules à ensemble changé | SHA-256 du journal imposé |
|---|---|---|---|---|---|
| 0 | 108 472 | | 108 472 (étage A, W2) | 0 | e908eb93…baf6 (identique à N = 146) |
| **β₁ = 0,041** | **97 604** | **−10,019 %** | 97 604 | 7,289 % | f7365cd8…13eb |
| β₂ = 0,050 | 95 341 | −12,105 % | 95 341 | 8,832 % | 102b47f8…d319 (égal à celui de `fichiers-B.json`, calcul reproduit) |

- Seuil de −10 % : 97 624,8 défauts. β₁ est le **premier pas de 0,001** qui le franchit (0,040 donne 97 883, soit −9,76 %, déjà dans `fichiers-B.json`). β₁ est le β décisif de `03-` ; β₂ encadre par le haut (pente de la KL au-delà de −10 %, même rôle que β = 0,07 à N = 146). Le voisin de dessous (0,040) n'est pas passé : à 0,001 de β₁, il n'apprendrait rien et manque −10 % de 0,24 point.
- Défauts rejoués par deux LRU indépendants (celui de `simuler`, celui de `cache2.py`) : égaux à l'unité aux deux β. Le fichier de β₂ est identique octet pour octet à celui calculé le matin à N = 146 pour N31 : le calcul est déterministe.
- Part du plus haut logit gardé : 1,0 à β₁, 0,99999 à β₂.

## Prédiction écrite avant les passes
Rapport KL / part de cellules changées à N = 146 : 0,176 (β = 0,06) et 0,173 (β = 0,07) (`resultat-etage-B.md` § 2 corrigé par le juge § 5). Appliqué à la part changée d'ici : KL ≈ 0,175 × 0,0729 = **0,0128 à β₁** et 0,175 × 0,0883 = **0,0155 à β₂**, avec une marge de ±30 % que je donne parce que le rapport n'a que deux points (plages 0,009 à 0,017 et 0,011 à 0,020). L'a priori de l'étage A (0,309 × part) donnerait 0,0225 et 0,0273 : je mise sur la première. Premier choix littéral : entre 88 et 95 % (plus de cellules inchangées qu'à N = 146 : plausiblement 91 à 93 %) ; pondéré : au-dessus de 96 %.
