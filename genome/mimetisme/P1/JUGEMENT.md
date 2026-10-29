# P1, jugement indépendant : mémoire du cache à deux échelles (LFU à demi-vie), jugée en génération

Juge : rôle « juge indépendant de P1 », 2026-10-27. Critères déclarés et commités avant d'exécuter mon chemin :
`genome/mimetisme/P1/juge/criteres.md` (commit 238965b). Outils : `outils/mimetisme/P1/juge/{juge_p1.py, sondes_p1.py}`,
écrits depuis la spécification du protocole seule, sans lire `cache_p1.py` ni `cache2.py`. Journaux et résultats :
`mesures/mimetisme/P1/juge/` (`juge.json`, `juge-oubli.json`, `sondes.json`, `*.log`, dont `passe1-oubli.log`).
Étiquettes : **[mes.]** mesuré par mon chemin ; **[lu]** vérifié dans le dépôt ou les données ; **[hyp.]** hypothèse dite.

## 0. Verdict du juge

**Le chiffre est reproduit, au bit, par un chemin indépendant. Le verdict mécanique « tombe » est exact au seuil déclaré.
Mais il ne juge pas le LFU en génération : sur la trace prose-en, il est décidé par 147 jetons produits APRÈS la fin du
message (`<|return|>` au jeton 109), que nul moteur ne produit. Sur la réponse réelle (109 jetons), LFU(32) − LRU = +0,0185.**

Statut que je retiens pour la question de fond : **ouvert**, pas tombé. Le « tombe » est celui du protocole sur ces traces ;
il ne ferme pas P1. La mesure qui décide reste celle que le rôle de mesure demande lui-même : des générations du 120b qui
s'arrêtent au jeton de fin (format harmony).

## 1. Le seuil a-t-il été commité avant la lecture ? Oui [lu]

`git log` : `ec124f5` (seuils des six pistes, 00:43:05) → `c861e8f` (protocole P1, 00:49:28) → `25db3a9` (simulateur et
témoins, 00:58:29) → `00093d8`, `d619c9c` (post hoc déclarés avant calcul) → `42b9b20` (résultats, 01:32:39). Aucun fichier
de taux n'existe dans un commit antérieur au protocole. Seul écart, déclaré par le rôle lui-même : W3 imprimait LFU(8) sur la
trace jugée avant la mesure principale (le h oracle +0,0055 était connu). Le protocole étant déjà commité, cela ne change rien.

## 2. Le chiffre principal refait par mon chemin [mes.]

120b, 326 emplacements, h* par validation croisée sur les lectures des autres genres.

| | rôle de mesure | juge | écart |
|---|---|---|---|
| h* (prose-en ; wiki) | 32 ; 32 | 32 ; 32 (moyennes +0,1039 et +0,1005) | 0 |
| LRU génération prose-en ; wiki | 0,7379 ; 0,3944 | 0,737901 ; 0,394368 | 0 |
| génération prose-en, d (z) | −0,0176 (−0,8) | −0,01755 (−0,82) | < 1e-5 |
| génération wiki | +0,1136 (2,7) | +0,1136 (2,73) | < 1e-5 |
| chaîne prose-en (segment de génération) | −0,0449 (−2,0) | −0,0449 (−2,01) | < 1e-5 |
| chaîne wiki | +0,0981 (2,0 ; 1,99) | +0,0981 (1,99) | < 1e-5 |
| fenêtres froides, 42 × 256 jetons : LFU(h*) − LRU | +0,0939, z 32,8, 42/42 | +0,0939, z 32,78, 42/42 | < 1e-4 |
| fenêtres froides : LFU(∞) − LRU ; inversée(8) − LRU | +0,0849 ; +0,0174 | +0,0849 ; +0,0174 | < 1e-4 |

Les lectures à 326 coïncident aussi avec `grille-120b.log` à 1e-5 (dialogue 0,55818 / 0,57614 / 0,57748 / 0,57670 / 0,57123,
etc.). Critère déclaré (2e-3, z à 0,2, même décision) : **tenu**. Verdict mécanique refait : **tombe** (prose-en sous +0,005).

## 3. Témoins et cassures de mon instrument [mes.]

- T1 : LFU(h = 1e-3) = LRU à 0 près (0,737901). **Tient.**
- T2 : LFU(∞) = 0,662679, le repère 0,66268 du seuil. **Tient**, mais seulement en seconde passe : voir § 5.1.
- C2 (décroissance inversée, h = 8, gen prose-en) : 0,3305 contre LRU 0,7379, soit −0,41. **Tombe**, comme exigé.
- C3 (le z est-il apparié ?) : en permutant les blocs, σ passe de 0,021 à 0,163 et z de −0,82 à −0,11. **Tombe**, comme exigé.
- C1, **cassure déclarée mal conçue (je le dis)** : un balayage cyclique de 328 clés contre 326 emplacements rend LRU 0,45
  (et non 0 : il ne manque que 2 places) et LFU(∞) 0,45 (comptes égaux, départage = LRU). C1bis (656 clés) : 0 et 0. Ni l'une
  ni l'autre ne peut séparer LFU et LRU ; c'est mon erreur, pas celle de l'instrument. **C1ter, post hoc** : 50 groupes chauds
  cyclés, chacun suivi de 2 groupes froids jamais revus : LRU 0, LFU(∞) 0,311. L'instrument voit la fréquence. (LFU(32) y rend 0 :
  la distance de réutilisation, 150 jetons, efface le compte ; cohérent.)

## 4. Ce qui est faux ou trop beau

### 4.1 La trace prose-en n'est pas une « boucle du décodage glouton » : c'est une génération au-delà de la fin [lu, mes.]

Dans `t120b.prose-en.generation.jetons` (invite de 256 jetons puis 256 produits), la génération contient la séquence harmony
complète : `<|end|>` (200007), `<|start|>` (200006), `<|channel|>` (200005), `<|message|>` (200008) aux jetons 47 à 52 et 64 à 69,
puis **`<|return|>` (200002) au jeton 109**, suivi de `<|return|>` répétés et de blancs (le `.txt` le montre : la réponse finale
« Robert Boulter appeared … as the character Jason Tyler » se termine, puis viennent des retours à la ligne). Le modèle a **fini sa
réponse proprement** ; c'est le traceur qui a continué à forcer 147 jetons. Un moteur de conversation s'arrête au jeton 109.

Effet sur le verdict, découpe tête / queue (sonde S1, déclarée avant calcul) :

| gen prose-en, 326 | tête 0-108 (réponse réelle) | queue 109-255 (après la fin) |
|---|---|---|
| LRU | 0,415 | 0,977 |
| LFU(8) − LRU | +0,0215 | −0,0063 |
| **LFU(32) − LRU** | **+0,0185** | −0,0443 |
| LFU(∞) − LRU | +0,0134 | −0,1409 |

Sur la réponse réelle, **tout h donne un gain positif** (+0,012 à +0,022) ; le négatif vient entièrement de la queue, où deux jetons
tiennent dans le cache LRU. La tête ne fait que 3 blocs entiers de 32 : pas de z utilisable, **ce n'est pas un résultat**, seulement la
preuve que le « tombe » mesure le traceur. `resultat.md` § 0 et § 3 disent « boucle du décodage glouton » : il faut lire « jetons
produits après `<|return|>` ».

### 4.2 La trace wiki n'est pas une conversation [lu]

L'invite `invite-wiki-3000.txt` est du texte WikiText brut, sans gabarit harmony, coupé au milieu d'un mot (« Ben Whish »). Le modèle y
fait de la complétion brute et répète « Here is a summary ». Tête 0-159 : LFU(32) − LRU = +0,041 ; queue en boucle : +0,234 [mes.].
Le gain wiki du verdict (+0,1136) est donc lui aussi surtout un effet de boucle, comme le rôle le dit ; je confirme.

### 4.3 Trou de spécification : le compte survit-il à l'éviction ? [mes.]

Le protocole ne le dit pas, `resultat.md` non plus. Ma première passe (compte perdu à l'éviction, LFU « dans le cache ») rend LFU(∞) =
0,2705 au lieu de 0,66268 et un h* de 8 (`passe1-oubli.log`, `juge-oubli.json`). Le repère W2 n'est retrouvé, à 1e-6, **que si le compte
de chacun des 4 608 experts est gardé à vie** (LFU « parfait », avec historique). C'est la convention mesurée par P1 ; elle doit être écrite,
car dans le moteur elle coûte une table de 4 608 compteurs (négligeable) et non un compteur par emplacement. Le verdict y est robuste :
en LFU dans le cache, gen prose-en −0,0111 (z −1,1), gen wiki +0,063, chaînes −0,025 et +0,049 ; tombe aussi.

### 4.4 Le reste

- z sur 8 blocs, sans correction de Student : le rôle le dit ; je confirme que la chaîne wiki (1,99) ne passe pas, lue à la lettre.
- Le gain des fenêtres froides (+0,094) est reproduit, mais c'est du texte **imposé** ; sa cassure (décroissance inversée) ne tombe pas
  (+0,017, z 1,9) : ce qui paie là est la fréquence, pas la demi-vie. Le rôle le dit ; je confirme au chiffre près.
- Les sources du rôle sont [mém.] et non relues : je n'en ai relu aucune non plus ; rien dans le verdict n'en dépend.

## 5. Conclusion pour Stone

- Le travail du rôle de mesure est **honnête et exact** : seuil commité avant, chiffres reproduits au bit, écarts déclarés.
- **Correction du juge** : le « tombe » est décidé par des jetons générés après la fin de la réponse. Sur la seule réponse réelle du 120b,
  le LFU(32) gagne +0,0185, sous le seuil de +0,02, et sur 3 blocs seulement : ni tombé ni tenu. **P1 reste ouvert.**
- Pour fermer : 4 générations au moins du 120b **arrêtées à `<|return|>`** (invites harmony), juger seulement les jetons produits avant la
  fin, et écrire la convention du compte (gardé à vie). Vérifier aussi que les traces de génération du 20b et les vitesses du moteur sur
  wiki-3000 ne portent pas sur des jetons d'après la fin.
