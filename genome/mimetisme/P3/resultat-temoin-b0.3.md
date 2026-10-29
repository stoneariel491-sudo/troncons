# P3, étage B à N = 238 : témoin β = 0,3, résultat (2026-10-27)

Prédiction et règle commitées avant la passe : `mesures/mimetisme/P3/05-temoin-b0.3-declare.md` (commit `3a3713e`). Passe unique du moteur, `p3_etageB_N238.py 0.3`, 4 fils, verrou posé et retiré. Journaux : `mesures/mimetisme/P3/etage-B/N238/` (`passe-N238-b0.3.json`, `pilote-b0.3.log`, `juge-kl-p3-N238-b0.3.{json,csv}`, `lecteur-b0.3.json`). Étiquettes : [mes.] mesuré.

## Verdict

**La porte pondérée sait tomber sur le levier.** Premier choix pondéré (marge de référence ≥ 0,3) : **91,32 %**, sous 95 % ; la règle d'avance dit « le témoin tombe ». L'instrument n'est pas aveugle, et le grave G1 du juge (porte sans pouvoir de séparation) est levé sur ce point : elle sépare, mais seulement loin dans la zone, là où la KL a déjà tombé.

## Prédiction contre mesure [mes.]

| grandeur | prédiction | mesure | lecture |
|---|---|---|---|
| premier choix pondéré (≥ 0,3) | 91,9 à 93,5 % | **91,32 %** (139 désaccords sur 1 601) ; intervalle par fenêtres [90,24 ; 92,27] | sous la bande de 0,6 point, côté plus pessimiste ; la décision (< 95 %) tient |
| KL | 0,061 à 0,066 (bande large 0,045 à 0,12) | **0,07163** (juge kl) ; 0,07163414 relu des `.kld` (écart < 1e-9) | au-dessus de la bande étroite, dans la bande large |
| défauts | 50 988 (−52,99 %) | non rejoués ici (journal imposé = celui de l'étage A, SHA-256 2b93c38c…1ab7, copie lue par le moteur identique) | |

Autres lectures : premier choix littéral **79,96 %** (511 désaccords sur 2 550) ; marge ≥ 0,1 : 84,92 % (2 182 positions) ; marge ≥ 1,0 : 95,96 % (21 sur 520). Par fenêtre, le pondéré va de 87,1 % à 94,1 % : **aucune des dix fenêtres n'atteint 95 %**. KL médiane 0,0249, p99 0,973.

## Contrôles

- Imposition effective : routage enregistré par la passe = journal imposé dans **122 640 / 122 640** cellules [mes.].
- SHA-256 du fichier imposé : 2b93c38c5cadcb0b8b7c3e2f7d3268a6f0907c96e14777a0aad47d1e43d71ab7, conforme ; `.kld` : dea8e56c…14e6, différent de la base.
- Deux chemins : `juge kl` (0,0716341444, 79,96 %) et lecteur `.kld` du juge de N = 238 (0,0716341434, 79,96 %, pondéré 91,32 %), mêmes premiers choix.
- Garde-fous : aucun arrêt ; 1 074 s, pointe 2,30 Go, RAM disponible minimale 1,64 Go (lancée avec ~3,2 Go libres, moins que les 6 Go conseillés), swap au plus 2,56 Go, C: libre ≥ 75 Go, secteur branché.
- Une seule passe : déterminisme au bit de ce β non répété.

## Ce que cela dit, et ne dit pas

- La condition « pondéré ≥ 95 % » n'est pas inutile : elle tombe à β = 0,3. Mais elle ne tombe qu'**après** la KL : à 0,0716 la KL dépasse déjà 0,07, seuil de « tombe » du critère (`03-`), à −53 % de défauts. Sur ce levier, la porte pondérée ne fournit donc pas de preuve que la KL n'ait pas déjà donnée ; elle confirme que la baisse du premier choix suit la KL (désaccord pondéré 8,7 % pour 0,0716, contre 1,25 % pour 0,0117 : environ 1,2 point par 0,01 de KL, même pente que sur les passes précédentes).
- Un point de plus sur la droite défauts / KL / premier choix : la mesure confirme la lecture du juge (la porte mord vers KL ≈ 0,04 à 0,06 au premier choix pondéré, en cohérence avec le bord prédit de 95 à 96 % à KL 0,038).
- Limites inchangées : un budget, texte de lecture, boucle ouverte, un seul tirage de la passe.
