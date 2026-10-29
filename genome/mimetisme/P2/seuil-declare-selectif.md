# P2, démotion sélective : hypothèse POST-HOC et seuil déclaré avant de lire les traces du 20b

Date : 2026-10-27. Ce fichier est commité avant que j'ouvre une seule trace du gpt-oss-20b.

## D'où vient l'hypothèse (dit sans fard)
Le verdict de l'exclusif simple sur le 120b est « ouvert » (`mesures/mimetisme/P2/verdict.json`) : la
réduction de la part disque passe (28,3 % et 51,3 %) mais la descente VRAM vers RAM mange 27,2 % d'un
jeton de 345 ms sur wiki génération (seuil : 25 %), et en série elle dépasse le gain sur prose-en
génération. J'ai alors essayé, après avoir vu ces chiffres, une **démotion sélective** : la victime VRAM ne
descend en RAM que si elle a été réutilisée au moins `s` fois pendant son séjour en VRAM (une entrée montée
de la RAM arrive avec son compteur à `s`, elle a déjà prouvé sa réutilisation). C'est le même geste que le
filtre d'admission des caches à deux files (2Q, Johnson et Shasha 1994 [mém.]) appliqué à la descente.
Essais faits : `s` dans {0, 1, 2, 3}, R dans {160, 336, 672}, 7 traces du 120b
(`mesures/mimetisme/P2/explore-selectif.csv`). `s = 0` redonne l'exclusif simple à l'identique
(témoin tenu). À R = 336, `s = 1` donne sur le 120b : prose-en génération 0,1845 -> 0,1769 avec 18,1
descentes par jeton au lieu de 36,5 ; wiki génération 0,2885 -> 0,3649 (pire) avec 42,6 au lieu de 85,9 ;
les 5 lectures s'améliorent à R = 160 et 336. À R = 672 prose-en génération et wiki génération empirent.
**Ces 120b ne comptent donc pas comme preuve** : j'ai choisi `s = 1` en les regardant, 4 valeurs de `s`
et 3 de R sont des degrés de liberté dépensés. Le test est le 20b, un autre modèle, jamais regardé.

## Test sur le 20b (autre modèle : 24 couches, 32 experts, k = 4 [mém., vérifié par assertion au chargement])
- Données : les 5 générations (code, dialogue, prose-en, prose-fr, wiki) et les 5 lectures du 20b
  (`traces-20b.tar.xz`). Les 5 générations décident ; les lectures sont rapportées.
- Capacités à fraction égale du nombre de cellules N (le 120b : V = 326 sur 4 608 = 7,07 %, R = 336 =
  7,29 %) : V = round(0,0707 N), R = round(0,0729 N). Secondaire : V = round(0,2001 N) (922 sur 4 608),
  même R.
- Comparaison : `s = 1` contre `s = 0` (exclusif simple) contre inclusif contre LRU seul.
- **Succès** si les trois tiennent : (a) réduction relative de la part disque contre l'inclusif ≥ 15 %
  pour `s = 1` sur au moins 4 des 5 générations ; (b) part disque de `s = 1` ≤ part disque de `s = 0` + 0,01
  sur au moins 4 des 5 ; (c) descentes de `s = 1` ≤ 0,6 × celles de `s = 0` sur les 5.
- **Mort** si (b) échoue sur 3 générations ou plus (le filtre fait pire que l'exclusif simple).
- **Ouvert** sinon.
- Le temps de jeton du 20b n'est pas connu de moi : le trafic de descente est jugé en **descentes par
  défaut VRAM** (δ), pas en millisecondes. La rentabilité en série est `ρ (a − b) − δ b > 0` par défaut
  VRAM, avec a = 4,1 et b = 1,09 ms du 120b (tailles d'experts du 20b non reprises : écart dit).

## Témoins sur le 20b
- T0 : `R = 0` redonne le LRU seul (exact). T1 : inclusif à R ≤ V ajoute ≤ 1e-4 (R = 40).
  T2 : exclusif = LRU de capacité V + R à 7e-4 près. T3 : `s = 0` redonne `exclusif` de `cache_exclusif.py`
  exactement (deux codes). Cassure : `s` infini (jamais de démotion) doit redonner le LRU seul exactement.
