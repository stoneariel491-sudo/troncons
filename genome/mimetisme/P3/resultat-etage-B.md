# P3, étage B (la KL excédentaire) : résultat (2026-10-27)

Seuils : `mesures/mimetisme/P3/02-etage-B-declare.md` (commit c4a037a, avant toute lecture de KL ; seuils du cahier inchangés). Outils : `outils/mimetisme/P3/p3_etageB.py`, `p3_etageB_chemin2bis.py`. Journaux : `mesures/mimetisme/P3/etage-B/`. Étiquettes : **[mes.]** mesuré ici, **[calc.]** calculé.

## 1. Verdict au seuil littéral : NON CONCLUANT (budget 19 %, N = 146)

- **La condition KL tient** : KL excédentaire 0,0209 (β = 0,06) et 0,0239 (β = 0,07), seuil de succès 0,038, seuil de mort 0,07. [mes.]
- **La condition « premier choix identique ≥ 95 % » tombe** : 88,4 % et 87,6 %. [mes.]
- « tient » exige les deux : exclu. « tombe » exige KL > 0,07 au β de −10 %, ou aucun β à −5 % avec KL ≤ 0,038 : ni l'un ni l'autre. D'où « entre les deux : non concluant ».
- Le budget 31 % n'a pas été passé : même un « tient » aurait été « partiel ».
- Lecture que je propose (mon jugement, pas le seuil) : le levier coûte une KL de l'ordre de la moitié du seuil pour −10 à −11,5 % de défauts, mais il change le premier choix dans ~12 % des positions, ce qui est du même ordre que l'écart de llama.cpp à la référence (90,4 %, R0). Le seuil de 95 % n'est pas dérivé d'une grandeur mesurée dans le tri ; c'est lui qui décide ici, et il faut que Stone ou l'orchestrateur dise s'il est la bonne exigence. Je ne l'ai pas modifié.

## 2. Chiffres [mes.], 10 fenêtres, 2 550 positions notées, `juge kl` (chemin 2)

| Passe | défauts (étage A) | KL moyenne | incertitude | médiane | p99 | premier choix | durée |
|---|---|---|---|---|---|---|---|
| T0 β = 0 | 216 397 | **0** (kl_max 0, .kld identique octet pour octet à `ref-openai-20b.kld`) | 0 | 0 | 0 | 100 % | 1 345 s |
| T1 cassure, 1 226 cellules (1 %) à 4e expert aléatoire | | 2,08e-3 | 4,1e-4 | 1,2e-4 | 0,0219 | 98,0 % | 2 272 s |
| β = 0,06 | 194 904 (−9,93 %) | **0,02089** | 0,00125 | 0,0074 | 0,270 | **88,4 %** | 1 499 s |
| β = 0,07 | 191 442 (−11,53 %) | **0,02393** | 0,00149 | 0,0085 | 0,304 | **87,6 %** | 1 104 s |

- Le franchissement de −10 % se fait entre 0,06 et 0,07 ; le β qui l'atteint est 0,07. À ce β, KL 0,0239 ≤ 0,038 et ≥ 10 % de défauts en moins.
- **Témoin T0** : tient, au bit. **Cassure T1** : KL 2,08e-3 > 1e-4 déclaré, le témoin tombe comme exigé.
- **Arrêt d'O'Brien-Fleming** (cumul des fenêtres 0 à 5 > 0,07 ?) : jamais déclenché (0,0217 à β = 0,06, 0,0250 à β = 0,07). Il ne coupe pas une passe : la référence calcule couche par couche pour les 10 fenêtres, donc les logits n'existent qu'à la fin ; il n'a servi qu'entre β (écart au protocole du cahier, déclaré dans 02-).
- **KL par part de cellules changée** [calc.] : 0,0209 / 0,120 = 0,174 à β = 0,06, contre 0,309 supposé par l'étage A (donc l'a priori était pessimiste d'un facteur ~1,8 ici). Les 1 226 cellules aléatoires de T1 : 0,0021 / 0,010 = 0,21, plus bas aussi que les bascules spontanées.
- **Second chemin du chiffre principal** : recalcul numpy depuis le CSV par position (pas depuis le résumé du juge) : 0,0208902 contre 0,0208901762 (β = 0,06), 0,0239339 contre 0,0239339 (β = 0,07), mêmes premiers choix. Intervalle par rééchantillonnage des fenêtres (20 000 tirages) : β = 0,06 [0,0166 ; 0,0255], β = 0,07 [0,0191 ; 0,0296]. Les KL par fenêtre vont de 0,011 à 0,034 (β = 0,06) : aucune ne dépasse 0,07.
- **Ressources** : RAM de pointe de `juge reference` (f64, 20b) **2,29 Go** de mémoire de travail (rss max 2,26), disponible minimale du système 0,24 Go pendant T1 (1,2 à 2,4 Go aux autres passes), swap utilisé jusqu'à 2,25 Go, C: libre ≥ 82 Go. Aucun garde-fou déclenché. La passe T1 a été deux fois plus lente (2 272 s) probablement par pression mémoire (0,24 Go libres), cause non vérifiée. Les passes ont lu ~9,7 Go d'experts chacune.

## 3. Ce qui pourrait être faux

1. **Boucle ouverte** (cahier, étage A § 4.1) : les ensembles sont calculés sur la trajectoire du modèle exact puis imposés ; un routeur biaisé en ligne verrait h dériver et choisirait d'autres ensembles. La KL mesurée est celle de l'imposition, pas celle d'un routeur biaisé réel. Non mesuré.
2. **Interpolation** : seuls β = 0,06 et 0,07 ont une KL ; β = 0,065 ou la forme entre les deux sont supposées lisses.
3. **Budget 31 % non passé**, N = 146 seulement.
4. **Texte de lecture** (wiki en fenêtres de 511), pas de génération ; premier choix mesuré sur 2 550 positions notées, pas sur des réponses libres.
5. **Seuil de 95 %** non dérivé (voir § 1) ; si le critère est jugé trop dur, le verdict change, mais ce serait un changement de seuil après lecture, à déclarer comme tel et non à glisser.
6. **Fenêtres non indépendantes** (cache partagé dans l'étage A) : l'intervalle bootstrap sous-estime l'incertitude de population.
7. **Second chemin partiel** : même CSV du juge en amont ; le chemin 1 (llama-perplexity) ne lit pas un routage imposé. La KL est donc relue, pas recalculée depuis les .kld.
8. T0 identique au bit prouve la chaîne d'imposition, pas l'absence d'effet de poids : les poids de mélange sont ceux du softmax des quatre choisis (règle de l'article).

## 4. Suite

1. Décision sur le seuil de premier choix (dérivation : quelle part de changements de premier choix est tolérable pour une tâche donnée).
2. Si le levier est gardé : passer N = 238 (β ≈ 0,041 à −10 %) pour lever la mention « partiel », et la variante bornée par la marge (échanger seulement si marge < β et poids du 4e < w), qui vise le premier choix directement.
3. Routeur biaisé en ligne dans le moteur : l'épreuve finale, qui lève la limite 1.

## 5. Techniques essayées (pour RECETTES.md)

- Pilote de passe avec relevé toutes les 5 s de la mémoire de travail du processus enfant (psutil, `peak_wset`), de la RAM disponible, du swap, de C: et du secteur, et arrêt automatique sur seuil : un chiffre de RAM de pointe sans instrumentation à part. Piège : `python -I` retire les paquets utilisateur (psutil introuvable), lancer sans `-I`.
- Témoin à l'identique octet pour octet (empreinte du .kld) : plus fort que « KL = 0 » ; échoue au moindre écart.
- Échec : l'arrêt d'O'Brien-Fleming ne peut pas couper une passe de ce moteur (calcul couche par couche).
