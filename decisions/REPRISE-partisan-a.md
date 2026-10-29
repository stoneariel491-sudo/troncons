# Reprise : partisan de A (« l'exactitude et l'ingénierie d'abord »)

Livrable : `decisions/partisan-A.md`. Outil : `outils/decisions/partisan_a.py` (calcule seulement,
importe `outils/07-synthese/plafonds.py`). Journaux : `decisions/journaux/partisan-a/`.
Indépendance : `decisions/partisan-B.md` volontairement non lu (deux propositions indépendantes).

## 2026-10-15
- 11:00 arbre trouvé sale : un prédécesseur avait écrit l'outil et ses journaux (10:48), rien commité,
  pas de livrable. Relu en entier, gardé.
- Corrigé dans l'outil : S5 avait une marge 1,5 posée au jugé (retirée : cible = max(disque, PCIe)) ;
  S8 comptait M entier même quand le 20b tient déjà tout (M utile ajouté).
- Ajouté : S12 fenêtre minimale (tampons de d couches : 0,64 Go de RAM de pointe pour A0 au lieu de
  1,9), S13 f* = 0,958 (B1 dépasse A tant que plus de 4,2 % des défauts sont servis par la base),
  S14 contre la base exploratoire (0,49 j/s, non retenue par l'autre agent), S15 risque de B contre h,
  S16 réécriture 2 831 s (03), S17 seuils dérivés.
- Témoins S1 tiennent ; cassure (taux 1) : A, A0, A uniforme tombent, B1 tient. Commit 8737f90.
- Prochain : écrire partisan-A.md, commiter.
- 11:40 partisan-A.md écrit (thèse : A plancher et juge de B ; sacrifice 0,70 de B1 ; f* = 0,958 ;
  conteneur à préfixes, v1 à trois classes sans coupe, écart à 07 § 4.4 dit ; fenêtre 0,64 Go et
  témoin 20b/120b ; budget VRAM 414 emplacements ; 9 étapes, C1-C11, K1-K4). mesures/gpt-oss.md
  toujours absent : § 6 dit ce qui en dépend. Commit.
