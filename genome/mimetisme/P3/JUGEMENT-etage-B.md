# P3, étage B : jugement indépendant (2026-10-27)

Rôle : juge de la mesure de l'étage B, par défaut « non reproduit = ne tient pas ». J'ai lu `SOCLE.md`, `cahier-etage-B.md`,
`resultat-etage-B.md`, `mesures/mimetisme/P3/02-etage-B-declare.md` et les journaux de `mesures/mimetisme/P3/etage-B/`.
Mon chemin : `outils/mimetisme/P3/juge/etageB_juge.py`, écrit sans importer ni recopier `p3_etageB*.py` ni le `juge kl` :
lecteur binaire des `.kld` en flux (16 positions à la fois, ~200 Mo de pointe), lecteur du journal de routage, LRU à règle de
groupe réécrit depuis la définition du § 2 de `00-seuils-declares.md`. Sorties : `mesures/mimetisme/P3/juge/etage-B/`.
Aucun seuil changé. Pas de carte graphique, un fil de calcul.

Honnêteté sur l'ordre : je n'ai pas commité de critères à part avant de lancer mon chemin. Les valeurs à retrouver étaient
données par la consigne ; la règle que j'ai appliquée est celle d'un calcul déterministe : égalité au dernier chiffre affiché
pour les défauts et le premier choix, écart par position de l'ordre de la précision f32 du juge pour la KL.

## 1. Verdict

**Reproduit.** Les quatre chiffres principaux sortent de mon lecteur au dernier chiffre affiché, le témoin β = 0 tombe à zéro
au bit, la cassure donne une KL non nulle, les défauts de cache se retrouvent à l'unité, les seuils précèdent toute KL.
Le verdict déclaré, **non concluant au seuil littéral** (KL tient, premier choix tombe), est donc confirmé.
Aucun défaut grave trouvé. La question des quasi-égalités (§ 4) nuance la lecture du 88 % sans changer le verdict.

## 2. Antériorité des seuils (git)

- `c4a037a` (2026-10-27 05:48:45) ne touche que `02-etage-B-declare.md` ; les seuils qu'il rappelle sont ceux de
  `00-seuils-declares.md` § 3 (commits `1606f9f` 00:51 et `5dfee3c` 01:19) et du cahier (`5dfee3c`, 01:19). Les trois fichiers
  sont **inchangés** depuis (`git diff c4a037a HEAD` vide sur les trois).
- Première passe (T0) : 1 345 s, `.kld` daté 06:11, donc lancée vers 05:49, après `c4a037a`. Le commit suivant `f0bdd25`
  (05:49:09) n'ajoute que le pilote, sans chiffre. Les `.kld` de P3 n'existaient pas avant (dates 06:11, 06:50, 07:15, 07:33).
- Ordre déclaré (T0, T1, β = 0,06, β = 0,07) respecté par les commits `8f4a334`, `3c56e2d`, `afdb7aa`, `95e5ae5`.

## 3. Ce que j'ai refait, chiffre par chiffre

### 3.1 Empreintes (`empreintes.json`)

| fichier | SHA-256 (début) |
|---|---|
| `ref-openai-20b.kld` | d97fc421…2a38 |
| `ref-openai-p3-T0-20b.kld` | d97fc421…2a38, **identique** : le témoin β = 0 tient au bit |
| `ref-openai-p3-T1-20b.kld` | 3f922699…431f (diffère) |
| `ref-openai-p3-b0.06-20b.kld` | e44761df…70a8 (diffère) |
| `ref-openai-p3-b0.07-20b.kld` | 57bacad0…793c (diffère) |

Les quatre journaux imposés de `essais/…/P3/B/` ont l'empreinte déclarée dans `fichiers-B.json`, et les **copies que le moteur a
réellement lues** (`mesures/moteur/R/r1/routage/p3-*-N19.bin`, chemin pris dans la commande de chaque passe) ont la même empreinte.
Contrôle de plus : le routage que chaque passe a enregistré (`ref-openai-p3-*-20b.bin`) porte, cellule par cellule, les quatre experts
imposés dans le même ordre (122 640 sur 122 640, aux quatre passes), alors que ses marges sont celles que le moteur a recalculées
(écart jusqu'à 2,5 à 9) : l'imposition a bien été appliquée, et non le fichier recopié. Cellules changées contre β = 0 : 1 226 (T1),
14 594 soit 11,90 % (β = 0,06), 16 975 soit 13,84 % (β = 0,07).

Précision : `etage-A.json` ne porte pas les lignes β = 0,06 et 0,07 (grille officielle seule) ; leurs empreintes sont dans
`fichiers-B.json`. Le β = 0 y est commun (même empreinte e908eb93… aux deux budgets).

### 3.2 Défauts de cache (`defauts.json`)

Mon LRU (N = 146, global sur 768 experts, les 4 du groupe épinglés, victime = moins récent non épinglé, t puis l, ordre du fichier
dans le groupe) sur les journaux imposés :

| journal | défauts (moi) | déclaré | variation |
|---|---|---|---|
| β = 0 | 216 397 | 216 397 | |
| β = 0,06 | 194 904 | 194 904 | **−9,93 %** |
| β = 0,07 | 191 442 | 191 442 | **−11,53 %** |
| cassure T1 | 217 433 | (non déclaré) | +0,48 % |

Mes cassures : le même tampon lu en position-major rend 266 244 (le lecteur peut tomber) ; l'ordre inverse dans le groupe rend
216 093 (l'ordre du fichier est celui qui reproduit).

### 3.3 KL et premier choix relus des `.kld` (`kl.json`, `comparaison-juge.json`)

Convention de llama.cpp (Σ sur log p > −16, sans renormaliser), décodage en f64 :

| passe | KL moyenne (moi) | déclaré | premier choix (moi) | déclaré |
|---|---|---|---|---|
| T1 cassure | 0,0020803 | 2,08e-3 | 98,0 % | 98,0 % |
| β = 0,06 | **0,0208902** | 0,0209 | **88,43 %** (295 désaccords) | 88,4 % |
| β = 0,07 | **0,0239339** | 0,0239 | **87,57 %** (317 désaccords) | 87,6 % |

- Par position, contre le CSV de `juge kl` (lu après mon calcul) : écart absolu maximal 2,6e-7 à 3,3e-7 (le juge décode en f32),
  **aucune** position où le premier choix diffère entre les deux lecteurs. La KL renormalisée sur tout le vocabulaire donne
  0,02085 et 0,02389 : la convention ne pèse pas.
- Cela lève la limite 7 du résultat (« la KL est relue, pas recalculée depuis les .kld ») : elle l'est maintenant, par un second lecteur.
- Les jetons des quatre fichiers sont identiques (vérifié avant tout calcul), bien que la référence ait pris ses jetons de
  `processeur.kld` et les passes de P3 de `carte_cmoe.kld`.

## 4. La question clé : le 88 % vient-il de quasi-égalités ?

Marge de référence = log p(1er) − log p(2e) de `ref-openai`, égale à l'écart de logits ; résolution du codage ≤ 2,5e-4.

| | T1 cassure (51 désaccords) | β = 0,06 (295) | β = 0,07 (317) | toutes positions |
|---|---|---|---|---|
| désaccords à marge < 0,1 | **84,3 %** | **53,6 %** | **53,3 %** | 14,4 % des positions |
| désaccords à marge < 0,3 | **94,1 %** | **86,1 %** | **85,8 %** | 37,2 % des positions |
| marge médiane des désaccords | 0,015 | 0,087 | 0,088 | (accords : 0,51) |
| le test prend le 2e de la référence | 45 / 51 | 223 / 295 | 238 / 317 | |
| premier choix si marge ≥ 0,1 | 99,6 % | **93,7 %** | **93,2 %** | |
| premier choix si marge ≥ 0,3 | 99,8 % | **97,4 %** | **97,2 %** | |

Réponse :

1. **En grande partie oui.** Les désaccords sont concentrés là où la référence hésite : la moitié sous 0,1 logit, 86 % sous 0,3,
   contre 14 % et 37 % des positions. Trois sur quatre sont un simple échange du premier et du second de la référence. Une seule
   égalité exacte de codes au sommet dans tout le texte : les égalités au sens strict ne jouent aucun rôle.
2. **Mais pas seulement, et moins que dans la cassure.** Les désaccords du levier tombent à des marges six fois plus grandes que
   ceux de la cassure (médiane 0,087 contre 0,015). Même en retirant les positions à marge < 0,1, le premier choix reste à 93,7 %
   et 93,2 %, **sous 95 %** ; il ne passe 95 % qu'en retirant toutes les positions à marge < 0,3, soit 37 % du texte. La cassure,
   elle, est presque entièrement faite de quasi-égalités (99,6 % d'accord dès la marge 0,1).
3. Ce découpage est **post hoc** : il ne change pas le verdict et ne doit pas servir à reformuler le seuil après lecture. Il dit à
   qui décidera du seuil de 95 % (§ 4.1 du résultat) que la moitié des bascules coûte presque rien en probabilité, et l'autre
   moitié non : un critère pondéré par la marge ou par la perte de probabilité serait plus juste, mais il doit être déclaré avant
   une nouvelle passe.

## 5. Défauts

**Graves** : aucun.

**Mineurs** :
- Le résultat écrit 12,0 % de cellules changées à β = 0,06 ; le compte exact est 11,90 % (14 594 / 122 640). Le rapport KL / part
  devient 0,176 au lieu de 0,174 ; sans effet.
- La comparaison au 90,4 % de llama.cpp (R0) n'est pas refaite ici.
- Le cahier compte « ~2,5 h sur 2 fils » ; les passes ont tourné avec `--fils 4`, comme la référence du 15 octobre, et le témoin au
  bit montre que le nombre de fils n'a rien changé au résultat. À dire si la séance devait rester à 2 fils.
- L'ordre des experts dans le groupe compte pour le LRU (216 093 contre 216 397) ; il est porté par le fichier, mais la déclaration
  ne le fixe que par « rang décroissant de logit non biaisé », que je n'ai pas revérifié sur les logits.
- Je n'ai pas commité de critères avant mon chemin (dit en tête).

## 6. Reproduire

```
cd outils/mimetisme/P3/juge
python -I -X utf8 etageB_juge.py empreintes
python -I -X utf8 etageB_juge.py defauts
python -I -X utf8 etageB_juge.py kl        # ~2 min, ~200 Mo, lit 4 × 1 Go
python -I -X utf8 etageB_juge.py comparer
```
