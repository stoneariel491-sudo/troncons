# P3, étage B à N = 238 : témoin β = 0,3, prédiction déclarée avant la passe (2026-10-27)

Écrit avant : la copie du journal imposé sous `B238/`, toute passe du moteur à β = 0,3, toute lecture d'une KL ou d'un premier choix de ce fichier. Source de la prédiction : `genome/mimetisme/P3/JUGEMENT-N238.md` § 6 (cahier du témoin), commité en `c26d460`.

## Ce qui est passé

- Fichier imposé : `routage-impose-V1-b0.3-N31.bin` (étage A, déjà calculé), SHA-256 attendu `2b93c38c5cadcb0b8b7c3e2f7d3268a6f0907c96e14777a0aad47d1e43d71ab7` (relevé ce jour : identique).
- Budget N = 238 (« N31 »), β = 0,3 ; −52,99 % de défauts de cache (50 988 contre 108 472), 37,72 % de cellules à ensemble changé.
- Pilote : `outils/mimetisme/P3/p3_etageB_N238.py 0.3` (mêmes garde-fous, 4 fils, une seule passe).

## Prédiction du juge (extrapolation linéaire en part de cellules changées sur les quatre passes du levier)

| grandeur | prédiction |
|---|---|
| premier choix pondéré (marge de référence ≥ 0,3) | **91,9 à 93,5 %** |
| KL | **0,061 à 0,066** (bande large 0,045 à 0,12, croissance possiblement plus que linéaire) |
| défauts | 50 988, soit −52,99 % |

## Règle fixée d'avance

- Premier choix pondéré **< 95 %** : le témoin tombe, la porte pondérée sait tomber sur le levier.
- Premier choix pondéré **≥ 95 %** : la porte pondérée est **aveugle** jusqu'à −53 % de défauts, et le grave G1 du juge devient « la condition ne sert à rien ».

Rien n'est changé aux seuils. La KL, le littéral et les défauts sont rapportés à côté, sans entrer dans la règle.
