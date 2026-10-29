# Reprise : étude 07, ce qui manque (synthèse)

Livrable : `fondations/07-ce-qui-manque.md`. Outils : `outils/07-synthese/` (inventaire_gptoss.py,
raffinement_mxfp4.py, plafonds.py). Journaux : `fondations/journaux/07-synthese/` (+ `csv/`).

## 2026-10-15
- Lu SOCLE, REPRISE, les six études en entier (01 à 06).
- Machine sur secteur (BatteryStatus 2) à la reprise ; suite_secteur de 01 jamais passée (RAM au calme, llama 20b : manquent).
- Fait : inventaire local gpt-oss (A 1,686 Go, R 1,9085 Go, matrice d'expert 4 406 400 o contiguë) = second chemin de 06, témoin tient, cassé tombe.
- Fait : raffinement exact MXFP4 mesuré sur 12 tenseurs de gpt-oss-20b (3,19 G poids) : base signe+2 bits H 2,64, err rel 4,29 % ; base signe+1 bit H 1,96, err 16,4 % ; MXFP4 sur gaussienne 1,33 %. Chaîne exacte.
- Fait : plafonds.py, 3 témoins (01 T1 1,994 ; 01 T2 8,85 ; 06 T3 5,57) tiennent, cassé tombe.
- Commit ba2e3cc (outils + journaux), puis plafonds.
- Fait : 07-ce-qui-manque.md écrit et commité (46b06a7), bib memoire/sources/07-synthese.bib.
- Chiffres clés (LRU calé, disque 2,58) : A 6,24 j/s (série 3,93), A0 3,59 à 1,9 Go de RAM, B1 8,88 (23 % servis par la base), C IQ3_XXS 2,50 ; base llama.cpp estimée 0,37-1,87.
- Corrigé dans le texte avant commit : ×2,5 à ×17 (pas ×3 à ×15), I2 ×2 à ×12, BitLocker 0,6-0,8 cœur, R4 +16 %, R7 +2 %.
- RESTE (pour la suite, pas pour cette étude) : trace de routage gpt-oss-120b (h(c), rho) ; base llama.cpp mesurée sur gpt-oss-120b ; lire SliceMoE et TRACE en entier.
