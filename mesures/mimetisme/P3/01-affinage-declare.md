# P3, affinage post hoc de l'étage A : déclaré avant de le lancer

Écrit le 2026-10-27 à 01 h 25, APRÈS avoir vu la courbe officielle de l'étage A (`etage-A.csv`, commit 5dfee3c). Ce qui suit est donc de l'exploration
dite comme telle : elle ne change aucun seuil de `00-seuils-declares.md` et ne peut pas retourner un verdict déjà fixé par la grille officielle.

Ce que la courbe officielle a montré (lu) : V1 à β = 0,03 retire 5,1 % (N = 146) et 7,5 % (N = 238) des défauts ; à β = 0,1, 16,1 % et 22,6 %. Le seuil de 10 % se
franchit donc entre 0,03 et 0,1, là où la grille n'a pas de point. Le KL a priori y est voisin de 0,038 (0,309 × part de cellules changées).

Ce que je fais :
1. Grille fine (ajouts) β ∈ {0,04 ; 0,05 ; 0,06 ; 0,07 ; 0,08 ; 0,15 ; 0,2}, V1 et V2, deux budgets : le β de franchissement de −10 % par interpolation linéaire entre points
   voisins, et le KL a priori à ce β. Rien d'autre n'est conclu des points ajoutés que cette interpolation.
2. Incertitude : les 10 fenêtres de 511 positions comme blocs. Pour β ∈ {0,03 ; 0,1}, gain par fenêtre = 1 − défauts_β/défauts_0 sur la fenêtre (le cache continu d'une
   fenêtre à l'autre, les défauts comptés par position), moyenne ± écart-type / √10. Une fenêtre n'est pas indépendante de la précédente (cache chaud) : l'intervalle est une
   indication, pas un test.
3. Témoin W6 sur les données réelles (déjà passé : `w6-reel.log`, tient, cassure tient).
4. Une deuxième politique d'éviction, pour savoir si le gain est un artefact du LRU : LFU à décroissance de demi-vie 8 (celle de E7), mêmes budgets, β ∈ {0,03 ; 0,1}. Si le gain
   en défauts s'effondre sous 5 % avec LFU, la piste dépend du LRU du moteur et c'est dit. La même règle de groupe (les quatre épinglés).
   Témoin : à β = 0 le LFU(8) de cette implémentation redonne le taux de succès 0,6696 de E7 à N = 154 sur les mêmes ensembles (tolérance 0,002 : les ensembles sont ceux de
   la capture, ceux de E7 viennent du journal de référence, mêmes positions ; l'écart ne vient que des égalités de clés).
