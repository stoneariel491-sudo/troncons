# P3, routeur biaisé en ligne dans le moteur : jugement indépendant (2026-10-27)

Rôle : juge du routeur biaisé en ligne, par défaut « non reproduit = ne tient pas ». Je n'ai écrit ni le routeur ni les mesures.
Lu : `SOCLE.md`, `resultat-routeur-ligne.md`, `REPRISE-routeur.md`, `mesures/mimetisme/P3/06-routeur-ligne-declare.md`,
`mesures/mimetisme/P3/routeur-ligne/`, `JUGEMENT-N238.md`, le diff du commit `eb78770` (noyau `routeur_topk_biais` de `passe.cuh`,
`debut_couche_biais`, montage du biais dans `Moteur::pas`), `Cache::demander` et `Lru::victime` de `trc-cache`.

Mon chemin : `outils/mimetisme/P3/juge/routeur-ligne/juge_routeur_ligne.py`, écrit sans importer `p3_*.py`, `juge kl`, `rejouer`
ni le juge de N = 238 : lecteur `.kld` réécrit d'après le format (paquets de 8 positions, un fichier de 1 Go à la fois par paquet),
LRU à horodatage qui enregistre aussi la présence de chaque expert juste avant son groupe (ce que lit `Cache::emplacement_de`),
lecteur de traces et de journaux de routage. Sorties : `mesures/mimetisme/P3/juge/routeur-ligne/` (433 Ko). Aucun seuil changé.
Pas de carte graphique, pas de verrou, aucune passe du moteur ; deux fils au plus.

Base de toutes les comparaisons : `P0` (même moteur sans biais), comme déclaré. Les positions à marge ≥ 0,3 se comptent sur les
marges de **P0** : **1 592** (le 1 601 de N = 238 est compté sur la référence f64, autre base).

## 1. Verdict

**Reproduit**, au dernier chiffre affiché : défauts des cinq passes à l'unité, KL, premiers choix littéral et pondéré aux trois β,
témoin β = 0 (trace et 5 120 empreintes au bit), préfixe P-1, cassure β = 0,3, antériorité de la déclaration.
Le verdict déclaré tient **tel qu'il est écrit, à l'estimation ponctuelle** : pondéré « tient », littéral « non concluant »,
β = 0,3 « tombe ».

**Ce qui ne résiste pas à mon refait** (grave G1) : aucune des trois conditions ne tient à sa borne défavorable par fenêtres.
La borne haute de la KL est au-dessus de 0,038 pour **20 graines sur 20** ; la borne basse du pondéré est **sous 95 % pour
14 graines sur 20** (la mienne : 94,997 %) ; la marge de 31 défauts tombe à **−86** si le cache repart vide à chaque fenêtre, et
le −10 % n'est pas atteint aux budgets voisins de 238 (230, 234, 246 ; rejeu sur la même trajectoire). « Tient » est une
estimation au bord, pas un résultat robuste ; « à la limite » est le bon mot, et c'est tout ce qu'il faut en retenir.

L'hypothèse de la dérive (§ 3 du résultat) **tient** et se chiffre sans instrument neuf : au moins **39 %** des cellules changées
à β₁ sont de la dérive certaine (0 % en couche 0, 59 % en couche 23), alors que la part d'échanges en boucle ouverte est plate
avec la profondeur (7,3 % en couche 0, 7,5 % en couche 23).

## 2. Antériorité (git)

| commit / fichier | heure (−04:00) | contenu |
|---|---|---|
| `0f38124` | 10:31:47 | `06-routeur-ligne-declare.md` seul ; **inchangé depuis** (`git diff --stat 0f38124 HEAD` vide) |
| `eb78770` | 10:35:51 | code du moteur (option, noyau, test) |
| `P0` (pilote) | début 10:39:20 | première passe, sans biais |
| `B0.041` (pilote) | début 10:57:33 | première passe avec biais ; `.kld` écrit à 11:14:29 |
| `e92c685` | 11:45:27 | premiers journaux commités (P0, B0,041, B0,3, P0b) |

Seuils, témoin, cassure, grille et prédictions sont écrits avant toute passe du moteur biaisé. **Ordre respecté.** Les fichiers de
`routeur-ligne/` sont propres dans git, et leurs SHA-256 (traces, CSV d'empreintes, `.kld` présents) égalent ceux que le pilote a
relevés à la fin de chaque passe (`empreintes.json`).

## 3. Ce que j'ai refait

### 3.1 Témoins (`empreintes.json`)

- **T0** : `P0.trace` = `P0b.trace` (5 122 lignes, 0 différente) ; `P0-empreintes.csv` = `P0b-empreintes.csv` (5 121 lignes, 0
  différente). Cassure du comparateur : `B0.041` contre `P0`, 5 118 lignes différentes sur 5 121 (il tombe).
- **`.kld` de T0** : `P0.kld` = 3e43e7dc…edcb, égal au pilote. **`P0b.kld` n'existe plus** (ni `P-1.kld`) : l'égalité des `.kld`
  ne repose que sur l'empreinte relevée par le pilote. Les empreintes64 des logits des 5 120 pas couvrent la même chose ;
  mineur, mais à dire.
- **P-1** (binaire d'avant l'option) : préfixe de 1 536 pas, trace et empreintes, 0 ligne différente. Écart au protocole (trois
  fenêtres au lieu de dix) déjà dit dans le résultat.

### 3.2 Défauts (`defauts.json`), mon LRU

| passe | moi | pilote (moteur) | variation |
|---|---|---|---|
| P0 | 108 679 | 108 679 | |
| P0b | 108 679 | 108 679 | 0 |
| **B0,041** | **97 780** | 97 780 | **−10,0286 %** |
| B0,05 | 95 610 | 95 610 | −12,0253 % |
| B0,3 | 50 911 | 50 911 | −53,1547 % |

Seuil : 0,9 × 108 679 = 97 811,1 ; marge **31,1 défauts**. Cassures de mon LRU (chacune change le compte) : 1 000 cellules tirées
au hasard → 112 208 ; budget 237 → 109 432.

**Robustesse de la marge** (rejeu de comptage sur les traces commitées ; la trajectoire est celle que le cache du moteur a
produite, je ne la régénère pas) :

| convention de comptage | P0 | B0,041 | variation | marge au seuil |
|---|---|---|---|---|
| ordre de service (déclaré), cache vide, traverse les fenêtres | 108 679 | 97 780 | −10,029 % | **+31,1** |
| ordre inverse dans le groupe | 108 623 | 97 738 | −10,021 % | +22,7 |
| ordre par indice | 108 662 | 97 750 | −10,042 % | +45,8 |
| ordre au hasard, 5 graines | 108 624 à 108 652 | 97 735 à 97 758 | −10,004 à −10,042 % | **+4,6** à +45,5 |
| cache chaud (état final d'un premier passage) | 108 623 | 97 721 | −10,037 % | +39,7 |
| cache plein au départ (238 premiers experts) | 108 633 | 97 736 | −10,031 % | +33,7 |
| **cache vidé à chaque fenêtre** | 109 262 | 98 422 | **−9,921 %** | **−86,2** |

Budgets voisins (même trajectoire, contrefactuel) : 230 → −9,45 % ; 234 → −9,75 % ; 242 → −10,03 % ; 246 → −9,84 %.

Lecture : sous toutes les conventions **compatibles avec le protocole déclaré** (cache qui traverse les fenêtres), le seuil passe,
avec une marge de 4,6 à 46 défauts : l'ordre dans le groupe et l'initialisation ne le renversent pas. Il ne passe plus si le cache
repart vide à chaque fenêtre, ni à trois budgets voisins sur quatre. Le −10 % est un fil de rasoir à 238 emplacements.

### 3.3 KL et premiers choix relus des `.kld` (`analyse.json`)

| | KL (moi) | déclaré | littéral | déclaré | pondéré (≥ 0,3, 1 592) | déclaré |
|---|---|---|---|---|---|---|
| **β₁ = 0,041** | **0,031388** | 0,0314 | **88,549 %** (292) | 88,55 % | **96,357 %** (58) | 96,36 % |
| β₂ = 0,05 | 0,037692 | 0,0377 | 87,569 % (317) | 87,57 % | 96,043 % (63) | 96,0 % |
| β = 0,3 | 0,089069 | 0,089 | 76,980 % (587) | 76,98 % | 88,631 % (181) | 88,6 % |
| P0 contre réf. f64 (info) | KL(réf ‖ P0) 0,003679 | 0,00368 | | | | |

- Conventions : Σ sur log p > −16, tout le vocabulaire, renormalisée : écart ≤ 6e-5 en moyenne. Σ exp(log p) de P0 va de 0,99999 à
  1,021 (quantification, comme à N = 238).
- Contre les CSV de `juge kl` (lus après mon calcul) : écart par position ≤ 5,1e-7, **aucune** position où le premier choix diffère,
  aux trois β (`comparaison-juge-kl.json`).
- Cassure du lecteur : décalage d'une position, pondéré 14,3 %.

**Intervalles par fenêtres** (10 blocs, 20 000 tirages) :

| | KL | pondéré | littéral |
|---|---|---|---|
| β₁ (moi, graine 1) | [0,0244 ; **0,0385**] | [**94,997** ; 97,68] | [87,06 ; 90,12] |
| β₁ (résultat) | [0,0245 ; 0,0384] | [95,00 ; 97,68] | [87,10 ; 90,12] |
| β₁, 20 graines | borne haute 0,03831 à 0,03849 : **20/20 au-dessus de 0,038** | borne basse 94,96 à 95,02 % : **14/20 sous 95 %** | |
| β₁, blocs de 51 positions | [0,0264 ; 0,0370] | [95,21 ; 97,40] | |
| β₂ (moi) | [0,0286 ; 0,0464] | [94,58 ; 97,45] | [86,16 ; 89,29] |

Part des tirages hors seuil à β₁ : KL > 0,038 dans 3,5 % ; pondéré < 95 % dans 2,5 %. KL par fenêtre de 0,0146 à 0,0502 ; pondéré
par fenêtre de 92,66 % à 100 % (deux fenêtres sous 95 % : 92,66 et 93,84), comme dit.

**Sensibilité au seuil de marge** (post hoc, aucun seuil changé) : β₁ 92,84 % (0,1), 94,84 % (0,2), 95,96 % (0,25), 96,36 % (0,3),
97,06 % (0,35). À 0,2, β₁ tombe sous 95 % ; à N = 238 hors moteur il passait dès 0,05.

## 4. Le noyau (lecture, émulation, données réelles)

**Lecture de `routeur_topk_biais`** : le biais n'entre que dans `v[i] = logits[e] + biais[e]`, qui ne sert qu'aux k tours de
sélection. Après la sélection, le noyau relit `u[r] = logits[choisi_i[r]]` (non biaisés), trie par `meilleur(u, indice)` (logit
décroissant, indice croissant : indépendant du biais) et calcule les poids en f64 sur `u`. **Pas de fuite du biais dans les poids
ni dans l'ordre.** À β = 0, `logit + 0` est le logit en f32 (même −0 compare égal), le tri ne permute rien : égalité au bit
avec `routeur_topk`, ce que T0 mesure.

**Côté hôte** : le vecteur est construit depuis `Cache::emplacement_de((l, e))` juste avant `demander(l)`, après `demander(l − 1)` du
même pas : causal, conforme à la déclaration. La présence est bien définie : sans préchargement (refusé avec l'option), aucun
expert de la couche l ne peut être « en vol » avant `demander(l)`. Le tampon épinglé n'est réécrit qu'après `ev_routeur.attendre()`
de la couche précédente, donc après la fin de la copie qui le lisait ; le vecteur sur la carte est réécrit dans l'ordre du même
flux, après le routeur qui le lisait. Pas de course.

**Émulation sur l'hôte** (`noyau.json`, lecture ligne à ligne du noyau en numpy, 20 000 tirages dont un sur cinq à égalités forcées,
β ∈ {0,041 ; 0,05 ; 0,3 ; 1}) : théorème « S_β ⊇ S_0 ∩ présents, entrants ⊆ présents, sortants ⊆ absents » violé 0 fois ;
ordre dépendant du biais 0 ; poids hors softmax des logits non biaisés 0 ; β = 0 différent du top-k 0. Cassure (poids calculés sur
le score biaisé) : détectée dans 16 296 tirages sur 20 000.

**Données réelles, couche 0** (logits identiques entre P0 et Pβ : entrée = enchâssement, KV de la couche 0 sans expert) : avec la
présence rejouée par mon LRU sur la trace de la passe biaisée, **0** cellule changée incohérente avec le biais seul, aux trois β
(cassure, présence prise 997 pas plus tôt : 254, 296, 1 260 cellules incohérentes) ; **0** cellule de même ensemble dans un autre
ordre ; **0** cellule changée où les experts communs changent d'ordre relatif. Le noyau se comporte sur la carte comme il se lit.

Seule réserve, théorique : en f32, `z_a + β` et `z_b + β` peuvent devenir égaux pour deux présents très proches, départagés alors par
l'indice ; jamais observé, sans effet mesurable.

## 5. Pourquoi la dérive monte avec la profondeur (`cellules.json`)

Alignement : les 511 premiers pas de chaque fenêtre de la trace = les 5 110 positions des journaux de la référence ouverte (P0 égal à
la référence ouverte dans 98,89 % des cellules ; décalé d'un pas : 6,6 %).

| couche | 0 | 3 | 6 | 9 | 12 | 15 | 18 | 21 | 23 |
|---|---|---|---|---|---|---|---|---|---|
| changées en ligne (Pβ₁ ≠ P0) | 7,38 | 8,65 | 11,12 | 10,02 | 12,64 | 17,63 | 15,19 | 12,41 | 20,12 |
| changées en boucle ouverte, même β | 7,30 | 6,87 | 8,00 | 5,91 | 6,32 | 9,80 | 8,51 | 5,13 | 7,50 |
| bascules naturelles (P0 ≠ réf. ouverte) | 0,04 | 0,27 | 0,57 | 0,55 | 0,88 | 1,57 | 1,60 | 1,94 | 2,95 |
| dérive certaine (incohérente avec le biais seul) | 0 | 1,70 | 3,01 | 3,72 | 5,23 | 7,20 | 6,01 | 6,30 | 11,94 |
| changées, part incohérente | 0 | 19,6 | 27,1 | 37,0 | 41,3 | 40,8 | 39,5 | 50,7 | 59,3 |

(en % des cellules de la couche ; « incohérente » = un expert entrant absent du cache réel de la passe, ou un sortant présent :
impossible si les logits de la cellule sont ceux de P0, donc dérive certaine.)

1. **La boucle ouverte est plate** avec la profondeur (pente ~1 point de la couche 0 à la 23) ; la boucle fermée monte de ~11
   points. La comparaison du résultat (« 7,4 % en couche 0 égalent les 7,29 % hors moteur ») mettait une couche en face d'une
   moyenne ; refaite couche contre couche : 7,38 contre 7,30. Elle tient.
2. **Dérive certaine** : 6 207 des 15 799 cellules changées (**39,3 %**, 5,05 % de toutes les cellules), 0 en couche 0. S'y ajoutent
   1,36 % de cellules cohérentes mais à marge z4 − z5 de la référence ≥ β (un échange voulu y est impossible si les logits sont ceux
   de la référence : dérive probable). Échanges voulus possibles : au plus **6,45 %** des cellules (contre 7,29 % en boucle
   ouverte, avec un autre état du cache).
3. **Pas des bascules naturelles** : les cellules où le moteur sans biais diffère déjà de la référence ouverte (1,1 % en moyenne,
   0 % en couche 0, 3,0 % en couche 23 : la fragilité croît aussi avec la profondeur) ne portent que 806 des cellules changées
   (5,1 %). La dérive est causée par le biais lui-même, pas par la fragilité propre du moteur.
4. **Par où elle passe** : 87,5 % des cellules en dérive certaine (5 429 / 6 207) ont une couche amont changée **au même pas** ; le
   taux de dérive certaine est de 7,9 % quand une couche amont du même pas a changé, 1,6 % quand aucune n'a changé (couches 1 à 23).
   Le chemin dominant est donc le résidu du pas (une bascule en amont en entraîne d'autres en aval : la cascade de routage) ; le
   chemin par l'historique KV existe (778 cellules) mais pèse cinq fois moins.

**L'hypothèse de l'agent tient**, et elle n'exigeait pas le logit d'origine : le test de cohérence avec le cache réel donne une
borne basse de la dérive depuis les seules traces. À β = 0,3, la part incohérente tombe à 15,2 % des changées (les échanges voulus
dominent).

## 6. Ce qui pourrait être faux

1. Mon rejeu de robustesse (§ 3.2) ne régénère pas la trajectoire : sous une autre convention de cache, le moteur aurait biaisé
   vers d'autres présents. C'est une robustesse du **comptage**, pas de la boucle fermée.
2. Le test de cohérence (§ 5) suppose les logits de P0 inchangés pour déclarer une cellule « cohérente » ; une cellule cohérente peut
   encore être de la dérive : 39 % est une borne basse.
3. La marge z4 − z5 vient de la référence f64 (trajectoire exacte), pas de P0 ; en couche 0, 0,04 % des cellules changées ont une
   marge de référence ≥ β (écart moteur / référence).
4. Intervalles par fenêtres non indépendantes (cache partagé), comme dit dans le résultat.

## 7. Défauts

**Grave**

- **G1 (portée).** « Tient » ne vaut qu'à l'estimation ponctuelle, ce que la règle déclarée autorise (06- § 4), mais aucune condition
  ne tient à sa borne défavorable : KL haute ≥ 0,0383 (20 graines sur 20), pondéré bas sous 95 % (14 graines sur 20), défauts à 31
  près (−86 si le cache repart à chaque fenêtre ; budgets 230, 234, 246 sous −10 %). La phrase du résultat § 7.1 « borne basse du
  pondéré à 0,00003 au-dessus de 95 % » dépend de la graine : dans ma graine et dans 14 sur 20, elle est **sous** 95 %. À écrire :
  « borne basse au seuil (94,96 à 95,02 % selon la graine) ». Le levier ne peut pas servir de brique sans un second tirage (autre
  texte, autre budget) qui le confirme.

**Mineurs**

1. `P0b.kld` et `P-1.kld` effacés : l'égalité au bit des `.kld` de T0 ne se refait plus que par l'empreinte du pilote (traces et
   empreintes64, elles, se refont).
2. § 3 du résultat : une couche comparée à une moyenne (7,4 contre 7,29) ; juste par chance de profil, vérifié ici couche contre
   couche (7,38 contre 7,30).
3. § 3 du résultat : « il faudrait le logit d'origine » ; une borne basse était disponible depuis les traces (§ 5).
4. La porte pondérée ne mord toujours pas avant la KL (G1 de JUGEMENT-N238, confirmé en ligne) : 1,16 point de désaccord pondéré pour
   0,01 de KL à β₁ (1,0 à 1,3 hors moteur) ; à KL 0,038 on attend ~95,6 %.
5. Sensibilité au seuil de marge plus forte qu'hors moteur : β₁ passe sous 95 % dès 0,2 (94,84 %).
6. Égalités f32 entre deux présents après ajout de β : théoriques, non observées.

Rien d'autre : antériorité, chiffres, témoin, cassure, noyau et hypothèse de la dérive tiennent.

## 8. Reproduire

```
cd outils/mimetisme/P3/juge/routeur-ligne
python -I -X utf8 juge_routeur_ligne.py empreintes   # quelques secondes
python -I -X utf8 juge_routeur_ligne.py defauts      # LRU et variantes, ~10 min
python -I -X utf8 juge_routeur_ligne.py cellules     # profil par couche, dérive certaine
python -I -X utf8 juge_routeur_ligne.py noyau        # émulation du noyau, sans carte
python -I -X utf8 juge_routeur_ligne.py kl           # 5 × 1 Go en flux, deux fils, ~20 min
python -I -X utf8 juge_routeur_ligne.py analyse
python -I -X utf8 juge_routeur_ligne.py graines
python -I -X utf8 juge_routeur_ligne.py comparer
```
