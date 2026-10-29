# Tome III : le contre-jugement des corrections finales

Contre-juge des corrections finales, 2026-10-29. Je n'ai rien écrit de ce que je juge. Objet : le flux de
corrections qui suit le jugement final (`memoire/tome3/JUGEMENT-final.md`, commit `35dc26a`), soit les commits
`e5ce266`, `175735b`, `3293ba7`, `46d5816`, `3da79e3`, `4b071d0` et `a43281d` (`git diff 35dc26a a43281d` : 45
fichiers). Lu avant : `SOCLE.md`, `memoire/tome3/REPRISE-figures.md` (section « Rédaction »),
`JUGEMENT-redaction-fr.md`, les notes `REPRISE-redaction-*.md`, `PLAN-redaction.md`, `JUGEMENT-final.md`,
`REPRISE-final-correcteur.md`. Aucune carte graphique, aucune mesure.

Mes outils et journaux : `memoire/tome3/contre-final/`. Je les ai mis hors de `outils/` et de `mesures/` exprès :
`tome3_annexes.py` compte tout outil sous `outils/genome/` et tout journal sous `outils/genome/tome3/`. Les y
mettre aurait changé les annexes B et C d'un tome déjà construit, et le PDF commité n'aurait plus été celui que
le commit construit.

Mes constructions : trois arbres de travail détachés, hors du dépôt, sans toucher à l'arbre principal ni à
l'index :
- `3293ba7`, le commit juste avant le correctif du préambule, pour les Tomes I et II « avant » ;
- `a43281d` (deux arbres), pour les Tomes I et II « après », et pour le Tome III par `construire.sh tome3`.

## 0. Verdict

**Les quatre graves du jugement final sont levés, dans les deux langues. Aucune correction ne fait dire faux :
aucun chiffre n'a changé, les deux langues restent égales nombre pour nombre, et les renvois posés par les
répétitions pointent là où le récit a été gardé, à une imprécision près (m1). Le correctif du préambule ne
change, dans les Tomes I et II, que les pages 7 et 10, qui sont des pages de table des matières, au texte égal.
Le Tome III se reconstruit depuis le commit, page pour page égal aux PDF commités.**

- **Graves levés : 4 sur 4** (§ 1).
- **Graves neufs dans le flux : 0.**
- **Mineurs neufs : 3** (§ 4) : un renvoi à deux sauts (m1), un démonstratif sans antécédent (m2), un calque
  neuf dans l'abstract (m3).
- **Hors du flux, à savoir (H1, § 5)** : la chaîne des Tomes I et II, `construire.sh` sans argument, tombe
  (code 1) au commit d'avant comme à celui d'après. Le correctif n'y est pour rien : depuis `eb78770`
  (27 octobre), `tome2_chemin_noyaux.py` ne retrouve plus son extrait dans `passe.cuh`. Le correcteur a
  construit les Tomes I et II par `latexmk` seul, sur les fichiers engendrés tels que commités. Sa note le dit,
  mais sans dire que la chaîne tombe. Ce n'est pas un défaut des corrections : c'est un grave pour le
  propriétaire des Tomes I et II, et je le leur signale.

Je n'ai rien corrigé : rien de ce que j'ai trouvé n'est une erreur mécanique sûre, et chaque retouche d'une
source obligerait à reconstruire le Tome III (§ 4).

## 1. Les graves du jugement final

### G1. Un seul mot anglais par notion : levé

Je compte, dans `memoire/tome3/en/`, `memoire/tome3/commun/`, `memoire/figures/tome3/*.tex`,
`memoire/tome3/annexes/` et `memoire/outils/tome3_annexes.py`, chaque forme que le juge a demandé de retirer :

| forme retirée | occurrences restantes |
|---|---|
| witness, Witness (et pluriels) | 0 |
| synonym mutation, synonym genome | 0 |
| synonymous codon of zero, codon of zero | 0 |
| track, tracks, side track | 0 |
| merge, merged, merging (le fondu) | 0 |
| his, judge who | 0 |

Journal : `contre-final/journaux/formes-retirees.txt`.

La ligne « control, break / témoin, cassure » est dans les notations. Elle renvoie à `t3ecl:sec:instruments`,
dont le titre est maintenant « The instruments and their controls ».

J'ai lu chaque changement anglais en contexte : 311 lignes, plus 649 passages du pour-cent à l'espace fine,
comptés à part (`contre-final/ctxdiff.py`, `journaux/diff-en-contexte.txt`).
- Les 16 « who » devenus « that » et les 10 « his » devenus « its » désignent tous un juge, ou un objet.
- Le « its own descent » du 06 traduit « sa propre descente » : il garde l'ambiguïté du français, sans en
  ajouter.
- Une seule forme a été changée dans l'autre sens : « synonymous base » est devenu « synonym base ». C'est la
  forme des notations et des cinq autres occurrences ; la base est un nom de chose, pas la mutation.

### G2. Le Résumé français du tome anglais : levé

J'ai lu la page du Résumé dans le PDF anglais commité (`pdftotext`). Tout y est composé à la française : « 3,84
bits par poids », « 4,05 à 4,37 bits contre 3,84 », « 0,131 8 contre 0,264 0 », « 1,80 Go », « 57,1 % »,
« ×1,44 ». L'en-tête courant dit « Résumé ».

`resumes.py` du juge final, relancé : le Résumé est égal au caractère (5 511 signes), l'Abstract aussi (5 230
signes). Le groupe `\sisetup` est bien hors des deux blocs.

### G3. Les tables engendrées viennent du commit : levé

- **Le code.** J'ai lu le diff de `tome3_annexes.py` (`e5ce266`) :
  - la liste des fichiers vient de `git ls-tree -r -l -z HEAD` ;
  - les lignes et les descriptions viennent du contenu des objets (`git cat-file --batch`) ;
  - les volumes viennent de la taille des objets ;
  - une garde vérifie, par `git diff --name-only HEAD`, qu'aucun fichier compté ne diffère du commit.
  
  Aucun chemin ne lit plus l'arbre de travail pour un chiffre.
- **Refait par un autre chemin** (`contre-final/refaire_annexes.py`, qui ne reprend pas le code de l'outil) :
  - chaque ligne de la table des outils est recomptée par `git show HEAD:<chemin>` : **332 outils et 49 577
    lignes**, 0 écart ; `e4b_defauts.py` a 122 lignes ;
  - chaque dossier de la table des journaux est resommé par `git ls-tree -r -l` : **66 dossiers, 2 400
    fichiers, 78,56 Mo**, 0 écart ; `codon/` pèse 2 434 318 octets, soit 2,43 Mo.
  
  Le seul écart de mon premier passage est venu de `mesures/mimetisme/P3/` : 20 fichiers contre 18. Les deux
  de plus sont `07-second-tirage-declare.md` et `07b-amendement-garde-disque.md`, que l'annexe C exclut
  (réserve R6). Une fois la règle R6 écrite dans mon outil, l'écart tombe. C'est son témoin : il sait tomber.
- **La garde, cassée** (`journaux/garde-g3.txt`), dans l'arbre au commit `a43281d` :
  - arbre propre : code 0 ;
  - `e4b_defauts.py` allongé de deux lignes : code 1, avec le message attendu ;
  - fichier rendu : code 0.
- **Le même commit construit le même texte.** Après `construire.sh tome3`, les quatre tables regénérées sont
  égales au commit (`git diff --ignore-cr-at-eol` vide), dans un arbre en CRLF : les fins de ligne ne comptent
  plus.

### G4. L'« Il reste » de l'annexe B : levé

J'ai vu le rendu de la page 237 du PDF français (annexe B) : « à mettre l'outil des annexes dans la cible tome3
de construire.sh » est barré, et la suite dit ce qui a changé (`57db4ce`, `e5ce266`). L'anglais dit la même
chose.

La liste de la chaîne a son étape : « Il engendre alors les quatre tables des annexes A, B et C par
`memoire/outils/tome3_annexes.py` (tableaux A.2, B.1, B.2 et C.1) ». Les quatre renvois sont résolus.

## 2. Ce que disent les corrections : aucun faux

**Les nombres.** Je relance `parite_nombres.py` du juge final sur les sources de `a43281d` : **PARITÉ pour
les 18 fichiers, 0 en écart** (`journaux/parite.txt`).
- Les fichiers où des nombres redits ont été retirés baissent du même compte dans les deux langues : 09, 1 258 /
  1 260 (1 271 / 1 273 au jugement) ; 10, 1 079 / 1 079.
- Les écarts restants sont les huit qu'avait expliqués le juge.

`parite_ef.py` : notations, 51 paires (49 et les deux de la ligne neuve), 1 écart, le `\crefrange` déjà connu ;
les huit fichiers de légendes, 0 écart.

**Le sens, correction par correction.** J'ai lu tout le diff français mot à mot, et l'anglais en contexte.

| correction | ce que j'ai vérifié | tient |
|---|---|---|
| M3 (résumé, 13 point 1) | les deux fichiers sont recodés et vérifiés (`t3cod:sec:fichiers`, 08 « Les deux fichiers recodés ») ; ce qui reste, le défaut et l'effacement des v1.0, revient à Stone | oui |
| M4 | P4 « ouvert, plutôt tombe » au tableau des verdicts du 13 | oui |
| M5, la KL | le paragraphe a bien cinq phrases ; « nulle quand les deux lois sont égales » reste exact (chaque terme est nul) ; « au terme de coupe près » et la somme coupée « très légèrement négative » disent ce que le juge a relevé | oui |
| M5, Rényi | « $k = 1, \dots, n$, avec $X_{(n+1)} = 0$ » est ce que la preuve pose | oui |
| M6 | « en log de l'erreur ; en linéaire, 3,07 » ; la conclusion (3,07 > 2,64) ne bouge pas | oui |
| G4, annexe C | « en fins de ligne LF (une copie en CRLF est plus grosse) » : vrai de la taille d'un objet git sous `core.autocrlf=true` | oui |
| la réserve R1 | le 09 ne dit plus l'histoire de « l'état physique du fichier », et la phrase qui reste attribue toujours l'écart au motif des requêtes que le format impose ; aucune occurrence de « l'état du fichier » n'est ajoutée ; le décompte par fichier est le même en français qu'avant, sauf au 09, où il tombe à 0 dans les deux langues | oui |

**Les répétitions : où vont les renvois.**

| renvoi posé | cible | le récit y est |
|---|---|---|
| 02 « Quelle variante a été jugée » | `t3syn:sec:frontiere` (07, § « La frontière commune », l. 80 à 126) | oui : « Deux corrections, dites » (l. 120) porte la barre et le journal `kl-synonyme-d1-juge.json` |
| 10, R1 | `t3cod:sec:motif` (08) | oui : le tableau Jb3, ×1,389 et ×0,715, J9 (×1,421, ×0,713), J10 et J11 (×0,851, ×0,882), la description qui n'est pas un mécanisme ; les ×0,851 et ×0,882 retirés du 10 sont donc gardés au 08, et ne disparaissent pas du tome |
| 09, R1 | `t3jug:sec:r1` (10) | en partie : la lecture démentie y est, ses mesures n'y sont plus, voir m1 |
| 02, 03, 05 : les 64 codons | `t3int:sec:genome` (00, « Ce que génome veut dire ici ») | oui |

Aucun chiffre barré dans une source ne revient. La citation barrée « λ = 1 : KL 0,0262 contre 0,0360 » est
retirée du 02 ; elle reste barrée au 07 et au registre du 13.

## 3. Les constructions

### 3.1 Le préambule commun : les Tomes I et II

Le diff de `46d5816` ne touche que la boîte du numéro de page des parties et des chapitres dans la table des
matières (`\hss` au lieu de `\hfil`, posé à `\AtBeginDocument`).

J'ai construit les quatre PDF par `latexmk`, avec le même `latexmkrc` que `construire.sh`, avant (`3293ba7`)
et après (`a43281d`). Les fichiers engendrés étaient tels que commités (§ 5). Le rendu de chaque page à 72 ppp
est comparé par empreinte, et le texte de chaque page par `pdftotext` (`contre-final/pages.py`,
`journaux/pages.txt`).

| PDF | pages avant / après | pages au rendu différent | texte | après contre PDF commité (`3da79e3`) |
|---|---|---|---|---|
| Tome I EN | 169 / 169 | 7 et 10 (« Contents ») | égal | 0 page différente |
| Tome I FR | 173 / 173 | 7 et 10 | égal | 0 |
| Tome II EN | 233 / 233 | 7 et 10 (« Contents ») | égal | 0 |
| Tome II FR | 237 / 237 | 7 et 10 (« Table des matières ») | égal | 0 |

Témoin : un PDF contre lui-même donne 0 page différente. Cassure : une empreinte forcée donne 1 page
différente.

Toutes ces constructions finissent avec 0 erreur et 0 renvoi indéfini.

La première passe du Tome II anglais « après » s'est arrêtée en cours de route, code 12 de latexmk, sans erreur
dans son journal. Elle tournait alors en même temps que trois autres constructions. Relancée seule
(`latexmk -g`) : 233 pages, 0 erreur (`journaux/latex-tome2-en-apres-reprise.txt`). J'en conclus que c'était
la charge, et non le source.

**Ce que dit le correcteur est vrai** : seules les pages 7 et 10 changent, ce sont des pages de table des
matières, et le texte est égal. Les PDF commités sont, page pour page, ceux que construit le commit.

### 3.2 Le Tome III

`bash memoire/construire.sh tome3` dans un arbre au commit `a43281d` (`journaux/construction-tome3.txt`) :

| | valeur |
|---|---|
| code de sortie | 0 |
| durée | 71 min, avec les constructions des Tomes I et II en parallèle |
| pages | FR 300, EN 300 |
| erreurs, renvois ou citations indéfinis, caractères manquants | 0, 0, 0, dans les deux langues |
| biber | aucune erreur ni avertissement |
| boîtes trop pleines | FR 1 (0,57 pt), EN 3 (0,61, 0,55, 0,44 pt) ; 0 dans la table des matières |
| contre les PDF commités (`4b071d0`) | 0 page au rendu différent et 0 au texte différent, sur 300, dans chaque langue |

Le PDF anglais refait a même la taille, à l'octet, du PDF commité (9 157 163 octets). G3 tient donc jusqu'au
PDF : le commit construit le tome commité.

## 4. Les mineurs neufs

- **m1. Le renvoi du 09 fait deux sauts.**
  - Où : `fr/chapitres/09-synonyme.tex` l. 471, « réserve R1, \cref{t3jug:sec:r1}, où sont la lecture démentie
    et ses mesures » ; `en/chapitres/09-synonyme.tex`, « where the overturned reading and its measurements are
    given ».
  - Le constat : dans le même flux, les mesures (×1,389, ×0,715, ×0,851, ×0,882) ont quitté
    `t3jug:sec:r1`. Elles sont au 08 (`t3cod:sec:motif`), et le 10 y renvoie.
  - Ce n'est pas faux, puisque le lecteur arrive au 08 en passant par le 10, mais la phrase promet au 10 ce qui
    est au 08.
  - À écrire : « réserve R1, \cref{t3jug:sec:r1} ; ses mesures au \cref{t3cod:sec:motif} ».
- **m2. « Cette redondance » n'a plus d'antécédent** au 02.
  - Où : « En bref », l. 18 ; en anglais, « this redundancy ».
  - Le constat : la phrase qui disait le code dégénéré (« plusieurs codons disent la même chose ») est
    remplacée par « Une mutation synonyme change un codon sans changer la protéine (\cref{t3int:sec:genome}) »,
    et la phrase suivante dit encore « l'équivalent de cette redondance ».
  - À écrire : « l'équivalent de cette redondance du code ».
- **m3. Un calque neuf dans l'abstract.** M4 rend « plutôt du côté de tombe » par « rather on the side of
  falling ». La consigne de M1 était justement de retirer ce genre de tour.
  - Où : `en/resume.tex` et `fr/resume.tex`, bloc anglais, le même au caractère.
  - À écrire : « the calibrated-confidence prefetch leaning towards falling », dans les deux fichiers à la fois,
    pour garder l'égalité des blocs.

Pourquoi je ne les corrige pas :
- aucun n'est une erreur mécanique sûre : ce sont trois choix d'écriture ;
- toute retouche d'une source rend les deux PDF commités différents de ce que le commit construit ; il faudrait
  donc reconstruire le Tome III (de 31 à 71 minutes) et recommiter les deux PDF, ce qui revient au correcteur ;
- aucun ne fait dire faux.

## 5. Hors du flux, à savoir : la chaîne des Tomes I et II (H1)

- **Le constat.** `bash memoire/construire.sh`, sans argument, la chaîne des Tomes I et II, sort en code 1,
  aussi bien au commit `3293ba7` qu'au commit `a43281d` (`journaux/chaine-tomes12.txt`), sur ce message :

  `moteur/crates/trc-noyaux/noyaux/passe.cuh:527 ne contient plus « résidu[i] += » : extrait combiner.cuh à recaler`

- **La cause.** `eb78770` (27 octobre, P3, le routeur biaisé par le cache) a ajouté 80 lignes à `passe.cuh`, et
  le marqueur est maintenant à la ligne 607. La garde de `tome2_chemin_noyaux.py` fait ce qu'on lui demande :
  elle tombe.
- **Ce que réécriraient les outils des Tomes I et II**, lancés avant leur chute, si on laissait faire :
  - les annexes du Tome I : `annexes.py` lit tout le dépôt, et sa table des outils passerait de 96 à 452
    outils, sa table des journaux s'allongerait ;
  - `memoire/figures/donnees/tome2/caisses.csv` ;
  - le listing `memoire/listings/tome2/gemv-bloc.cuh` (34 lignes changées).
- **Ce que cela veut dire.** Les PDF commités des Tomes I et II ne se refont pas, au commit d'aujourd'hui, par
  leur propre chaîne. Ils se refont par `latexmk` seul, sur leurs fichiers engendrés tels que commités : c'est
  ce que le correcteur a fait (« par latexmk -outdir »), et ce que j'ai fait pour la preuve du § 3.1.
- **La responsabilité.** Rien de cela ne vient du flux jugé. Mais la note du correcteur ne dit pas que la
  chaîne tombe, et la règle de SOCLE (« le PDF se construit sans erreur ») n'est tenue, pour les Tomes I et II,
  qu'en contournant leurs outils de données.
- **Les suites.** C'est l'affaire du propriétaire des Tomes I et II, et ces deux tomes sont en lecture seule
  pour moi :
  - recaler les extraits du Tome II sur `passe.cuh`, et dire dans le Tome II si le code cité a changé ;
  - figer les annexes du Tome I, comme G3 l'a fait pour le Tome III.

## 6. Ce qui reste, et que je n'ai pas vu

- M8 (les décimales groupées), la relecture de langue anglaise d'un seul tenant, et les figures du mimétisme
  au rendu anglais : non faits, et le correcteur le dit. Je n'y ajoute rien.
- `construire.sh tome3` dans l'arbre principal tombe tant que `outils/mimetisme/humain/e4b_defauts.py` y est
  modifié par une autre session. C'est voulu, et c'est dit.

## 7. Ce qui pourrait être faux

- **Ma lecture de l'anglais est celle d'un non-anglophone.** J'ai lu chaque changement en contexte, mais pas
  les 300 pages ; un calque neuf ailleurs que dans le diff m'échapperait.
- **Le rendu des Tomes I et II est comparé à 72 ppp.** Une différence plus fine que le pixel passerait. Le texte
  de chaque page est égal, et les PDF « après » sont égaux, page pour page, aux PDF commités.
- **La comparaison « avant » contre « après » des Tomes I et II** porte sur des constructions faites le même
  jour, avec la même MiKTeX. Elle ne dit rien des écarts entre les PDF du 15 et du 16 octobre et ceux
  d'aujourd'hui, que le correcteur a relevés.
- **La cause de l'arrêt de la première passe du Tome II anglais** est une inférence (la charge) : le journal
  n'en dit rien. La seconde passe, seule, est propre.
- **`refaire_annexes.py` reprend deux règles de l'outil** que je ne peux pas déduire autrement : la clé de
  dossier (quatre niveaux) et l'exclusion R6. Il recompte les lignes et les tailles par son propre chemin, mais
  si la règle de rangement était fausse dans l'outil, elle le serait aussi dans le mien.
- **H1 n'est vérifié qu'aux commits `3293ba7` et `a43281d`.** Je n'ai pas cherché le premier commit où la
  chaîne tombe ; `eb78770` est le seul à toucher `passe.cuh` depuis le Tome II.

## 8. Reproduire

Depuis un arbre détaché au commit voulu (Git Bash ; Python 3.13 ; MiKTeX ; poppler) :

```
C=memoire/tome3/contre-final
bash memoire/construire.sh tome3                                  # 31 à 71 min ; en arrière-plan
bash $C/latex12.sh <arbre>                                        # Tomes I et II par latexmk seul
python -I -X utf8 $C/pages.py A.pdf B.pdf [--casser]              # rendu et texte, page à page
python -I -X utf8 $C/refaire_annexes.py <arbre>                   # annexes B et C refaites depuis le commit
python -I -X utf8 $C/ctxdiff.py <arbre> 35dc26a a43281d <fichiers>   # chaque changement en contexte
python -I -X utf8 outils/genome/tome3/juge-final/parite_nombres.py memoire/tome3
```
