# P2, cache exclusif VRAM vers RAM : jugement indépendant

Date : 2026-10-27. Rôle : juge de P2. Seuils du juge : `juge-seuil.md`, commité en 122b81d (01 h 16 min 19 s)
avant que j'extraie une seule trace. Outils : `outils/mimetisme/P2/juge/` (`juge_p2.py`, `depouiller.py`,
`a_budget_egal.py`). Mesures : `mesures/mimetisme/P2/juge/` (`juge-brut.json`, `verdict-juge.json`,
`budget-egal.json`, `journal.log` avec les empreintes SHA-256 des deux traces de génération). Un fil, priorité
sous la normale, aucune carte, aucun fichier modèle (le verrou de carte existait : seules les traces texte de
`mesures/localite-gpt-oss/` ont été lues, extraites hors dépôt).

## 1. Verdict : P2 « OUVERT » est reproduit, à l'identique

Mon chemin ne reprend rien du code de P2 : horodatage par cellule dans des tableaux, victime par argmin hors
épinglés, règle inclusive relue dans `moteur/crates/trc-cache/src/lib.rs` (l. 153-241 : rafraîchissement de la
RAM sur succès VRAM, l. 164-166), règle exclusive de Wong et Wilkes 2002 (la victime descend au plus récent de
l'étage bas, la remontée retire l'entrée du bas). Troisième chemin sans cache simulé : distances de pile de
Mattson par arbre de Fenwick.

| V = 326, R = 336 | disque inclusif | disque exclusif | réduction | descentes / jeton | descente / 345 ms |
|---|---|---|---|---|---|
| prose-en génération, P2 | 0,2573 | 0,1845 | 28,3 % | 36,5 | 11,5 % |
| prose-en génération, juge | 0,257270 | 0,184489 | 28,29 % | 36,469 | 11,52 % |
| wiki génération, P2 | 0,5926 | 0,2885 | 51,3 % | 85,9 | 27,2 % |
| wiki génération, juge | 0,592556 | 0,288493 | 51,31 % | 85,938 | 27,15 % |

Écarts : moins de 1e-5 sur les parts disque, moins de 0,1 % sur les descentes (J1 tient, seuil 1e-3 et 2 %).
Le verdict déduit retombe sur « ouvert » : réductions au-dessus de 15 % sur les deux générations, descente de
wiki au-dessus de 25 % du jeton de 345 ms. Rapportée au temps de disque propre à cette charge (357,6 ms en LRU
seul, plus long que 345 ms), la descente vaut 26,2 % : toujours au-dessus de 25 %, le verdict ne bouge pas.

## 2. Contrôle par contrôle

| contrôle | seuil du juge | observé | état |
|---|---|---|---|
| J1 reproduction | 1e-3 ; 2 % | < 1e-5 ; < 0,1 % | tient |
| J2 théorème, sans épinglage | mêmes entiers que Mattson LRU(662) | 6 801 = 6 801 ; 10 635 = 10 635 | tient |
| J2 avec épinglage | <= 7e-4 | 1,36e-4 et 1,90e-4 | tient |
| J3 cassure (a), descendre la plus récente | bouge > 1e-2 | +0,037 et +0,198 | tombe comme il doit |
| J3 cassure (b), copie gardée en RAM | bouge > 1e-2 | +0,014 et +0,063 | tombe comme il doit |
| J3 (c), RAM en FIFO | 0 attendu | 0 | comme prévu |
| J4a ordre inverse dans le groupe | <= 2e-3 | au plus 4,9e-4 | tient |
| J4b victime RAM qui évite les épinglés (inclusif, comme `lib.rs` l. 228) | rapporté | −4,1e-4 et −2,0e-3 | écart de fidélité, sans effet sur le verdict (wiki : 51,3 % -> 51,1 %) |
| J4c temps de service | 1 ms | LRU 154,74 / 357,56 ; série 160,85 / 313,78 ; recouvert 121,10 / 220,10 | tient |
| J5 sélectif `s = 1`, 120b | 1e-3 ; 2 % | 0,17689 / 0,36488 ; 18,06 / 42,65 ; `s = 0` = exclusif aux entiers près | tient |
| J5 20b, V = 154 | a 5/5, b 5/5, c 4/5 | 5/5, 5/5, 4/5 (prose-en : 0,725) | « ouvert » retrouvé |
| J5 20b, V = 54 | LRU seul à 100 % de défauts | 1,000 sur les 5 ; `s = 1` = LRU seul | régime dégénéré confirmé |
| Succès RAM de l'inclusif actuel | — | 0 à R = 160 ; 0,0048 et 0,0131 à R = 336 | confirmé |

Ordre des commits : seuil (6d325d8, 00 h 47 min 40 s) avant la première mesure (c69fba1, 00 h 56) ; seuil du
sélectif (7146816, 01 h 08) avant les fichiers du 20b (7caa281, 01 h 12), qui ne figurent pas dans 7146816. Le
changement de `cache_exclusif.py` dans 7caa281 ajoute un paramètre `epingle=True` par défaut : sans effet sur
les mesures antérieures.

## 3. Ce qui est faux ou trop beau

1. **Référence de commit fausse.** `resultat.md` et le verdict citent le seuil « commité en 6f3d737 ». Ce commit
   n'est sur aucune branche (`git branch --contains` vide) : c'est la version amendée d'un commit qui portait un
   trailer de remplissage. Le commit sur `main` est **6d325d8**, même seconde, contenu du fichier identique
   (`git diff` vide). Pas de fraude d'antériorité, mais la référence est à corriger.
2. **La référence « inclusif à R = 336 » est dégénérée par construction**, et le résultat le sait (§ 4.2) :
   avec rafraîchissement sur succès VRAM, l'inclusif à R <= V garde un sous-ensemble de la VRAM. « 28 % et 51 %
   contre l'inclusif » se lit donc « contre rien ». La vraie alternative n'est pas mesurée dans `resultat.md` :
   l'**inclusif à R' = V + R = 662** donne **exactement** la même part disque que l'exclusif à R = 336 (0,184489
   et 0,288493, égalité observée sur les deux générations, épinglage compris) **sans aucune descente**
   (`budget-egal.json`). Le vrai marché de l'exclusif est donc : économiser V entrées de RAM (environ 3,2 Go :
   7,68 Go encodés contre 4,45 Go décodés) en échange du trafic de descente. En série, cet inclusif à 662 bat
   l'exclusif à 336 sur les deux générations (+25,7 contre −6,1 ms ; +105,0 contre +43,8 ms par jeton, même avec
   des montées encodées à 1,8 ms) ; recouvert, l'exclusif gagne (+33,6 et +137,5 ms). À budget de RAM égal
   (4,45 Go : inclusif encodé R = 384), l'exclusif gagne sur wiki dans les deux régimes (+43,8 / +137,5 contre
   +22,9) et sur prose-en seulement si au moins 35 % de la descente est recouverte (contre +7,9 ms). Ce contrôle
   est hors de mon seuil déclaré : il éclaire la décision, il ne change pas le verdict.
3. **V = 922 n'est pas justifié comme option.** La suite 2 propose « V = 922, gain relatif 24 à 25 % avec moins
   de RAM ». À 13,25 Mo l'entrée décodée, 922 entrées font 12,2 Go de VRAM, pour une carte de 8 188 Mio (SOCLE) ;
   V = 326 fait 4,3 Go. Si V = 922 suppose des entrées plus petites (mode rapide), le résultat doit le dire ;
   sinon ce n'est pas une option sur ce portable.
4. **La démotion sélective n'est pas un gain net, c'est un réglage sur la même courbe.** Reproduite à
   l'identique, mais son avantage n'existe qu'en série : recouverte, elle perd sur wiki génération (253,2 ms contre
   220,1 pour l'exclusif simple, gain +104,4 contre +137,5) et gagne peu sur prose-en (117,8 contre 121,1). Comme
   l'exclusif simple, son intérêt dépend du recouvrement ω, non mesuré. Choisie après coup (dit), mécanisme connu
   (filtre d'admission de type 2Q [mém., source non relue par moi]). « Post-hoc probable » est trop fort ; je la
   classe « post-hoc, dépend de ω ».
5. **Le théorème n'est pas neuf.** Exclusif à deux étages LRU = LRU de capacité V + R, c'est l'inclusion de
   Mattson et l'argument de Wong et Wilkes. Il est juste (J2 exact) ; il ne doit pas être présenté comme une
   découverte dans le mémoire.
6. Écarts déjà dits par P2 et confirmés : simulation optimiste face au moteur (0,74 contre 0,59 de succès),
   tailles d'experts égales, jeton fixe de 345 ms, recouvrement non mesuré, T1 relâché à 1e-3 au bord R = V.

## 4. Conclusion

- **P2, exclusif simple : OUVERT, reproduit.** Les chiffres sont justes à 1e-5 par un chemin indépendant, le
  théorème est exact par un troisième chemin, les témoins de cassure tombent.
- Ce qu'il apporte vraiment : un étage RAM inclusif de taille R <= V ne sert à rien (`--ram-tiede` actuel, en
  simulation) ; l'exclusif atteint la part disque d'un inclusif de V + R entrées avec V entrées de RAM en moins,
  au prix de 36 à 86 descentes par jeton. La décision de Stone n'est pas « exclusif ou inclusif à R égal », c'est
  « 3,2 Go de RAM de plus, ou une descente recouverte ».
- Le nœud reste le recouvrement de la descente (ABBA moteur, après levée du verrou de carte) ; à mesurer en
  comparant aussi l'inclusif à R = V + R, qui ne demande aucun code nouveau.
- Démotion sélective : reproduite, post-hoc, dépend de ω ; pas d'élément nouveau pour la promouvoir.
