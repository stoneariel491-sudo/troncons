# P3, routeur biaisé EN LIGNE dans le moteur : résultat (2026-10-27)

Déclaration, seuils et prédictions, commités **avant** toute passe du moteur avec biais : `mesures/mimetisme/P3/06-routeur-ligne-declare.md`. Code : commit `eb78770` (option `--biais-cache <β>`, absente par défaut). Outils : `outils/mimetisme/P3/p3_routeur_ligne.py` (pilote), `p3_routeur_ligne_analyse.py`, `p3_routeur_ligne_vitesse.py`. Journaux, traces, CSV, `analyse.json` : `mesures/mimetisme/P3/routeur-ligne/` (les `.kld` lourds sont sous `essais/troncons/mimetisme/P3/routeur-ligne/`). Étiquettes : **[mes.]** mesuré ici, **[calc.]** calculé.

Banc : `gpt-oss-20b.trc`, 10 fenêtres de R1 (5 120 pas, 2 550 positions notées), carte graphique, **238 emplacements** de VRAM, LRU, quatre fils, secteur, verrou de la carte posé puis retiré. La base de comparaison est le **même moteur sans biais** (`P0`), pas la référence f64.

## 1. Verdict

| Seuil (repris de P3) | β₁ = 0,041 (décisif) | Verdict |
|---|---|---|
| défauts de cache ≥ 10 % en moins | **−10,03 %** (97 780 contre 108 679 ; le seuil est 97 811 : 31 défauts de marge, 0,03 point) | tient, de justesse |
| KL excédentaire ≤ 0,038 | **0,0314** [intervalle par fenêtres 0,0245 ; 0,0384] | tient à l'estimation ; la borne haute de l'intervalle dépasse 0,038 |
| premier choix pondéré (marge de P0 ≥ 0,3) ≥ 95 % | **96,36 %** (58 désaccords sur 1 592) [95,00 ; 97,68] | tient à l'estimation ; la borne basse touche 95 % |
| (lecture littérale, rapportée à côté) ≥ 95 % sur toutes les positions | **88,55 %** (292 désaccords sur 2 550) [87,10 ; 90,12] | non concluant (ne tombe pas : KL ≪ 0,07) |
| « tombe » : KL > 0,07 au β à −10 % | 0,0314 | non |

**Lecture pondérée (celle qui décide) : TIENT, mais à la limite sur les trois conditions à la fois, et nettement moins bien qu'hors moteur.** Lecture littérale : **NON CONCLUANT**, comme hors moteur. Le routeur biaisé en ligne marche dans le moteur, avec le gain annoncé en défauts, au prix d'une KL **2,7 fois plus grande** que celle mesurée en boucle ouverte (0,0117 à N = 238, `resultat-N238.md`).

β₂ = 0,05 (pente) : défauts −12,03 % (95 610), KL **0,0377** (sous 0,038 de 0,0003 ; borne haute 0,0464), pondéré 96,04 % [94,57 ; 97,43], littéral 87,57 % : tient aussi à l'estimation, avec encore moins de marge.

**Cassure β = 0,3 : la porte tombe, comme exigé.** Défauts −53,15 % (50 911), KL **0,0891** [0,0739 ; 0,1038] (> 0,07 : « tombe »), pondéré **88,63 %** [86,61 ; 90,55] (< 95 %), littéral 76,98 %.

## 2. Chiffres [mes.]

| passe | défauts | variation | KL (chemin B) | KL (chemin A, `juge kl`) | littéral | pondéré (≥ 0,3) | cellules à ensemble changé | dont couche 0 | même ensemble, autre ordre | KL vs réf. f64 (info) |
|---|---|---|---|---|---|---|---|---|---|---|
| P0 (β = 0) | 108 679 | | | | | | | | | 0,00368 |
| P0b (`--biais-cache 0`) | 108 679 | 0 | 0 | 0 | 100 % | 100 % | 0 | | 0 | 0,00368 |
| **β₁ = 0,041** | **97 780** | **−10,03 %** | **0,03139** | 0,03139 | 88,55 % | **96,36 %** | 12,86 % (15 799) | 7,4 % | 8,8 % | 0,03135 |
| β₂ = 0,05 | 95 610 | −12,03 % | 0,03769 | 0,03769 | 87,57 % | 96,04 % | 14,52 % | 8,7 % | 9,3 % | 0,03691 |
| β = 0,3 | 50 911 | −53,15 % | 0,08907 | 0,08907 | 76,98 % | 88,63 % | 43,77 % | 36,2 % | 11,6 % | 0,08836 |

- KL par fenêtre à β₁ : de 0,0146 à 0,0502 (aucune près de 0,07). KL médiane 0,0059, p99 0,535. Pondéré par fenêtre : de 92,7 % à 100 % (deux fenêtres sous 95 % : 92,7 % et 93,8 % ; voir `analyse.json`).
- Défauts : le compteur du moteur, `rejouer.exe` sur la trace et un LRU Python à règle de groupe (celui du juge de l'étage B) donnent **le même nombre à l'unité** pour les cinq passes [mes.].
- Rapport KL / part de cellules changées : 0,244 (β₁), 0,260 (β₂), 0,203 (β = 0,3), contre 0,16 à 0,17 hors moteur.
- PPL des positions notées : P0 461,98 ; β₁ 467,73 ; β₂ 461,78 ; β = 0,3 503,10.

## 3. Pourquoi la boucle fermée coûte plus [calc. et mes., hypothèse soutenue par un profil]

Hors moteur, les ensembles biaisés étaient calculés sur la trajectoire du modèle exact puis imposés : 7,29 % de cellules changées à β₁. En ligne : **12,86 %**. La part de cellules changées **par couche** (`cellules-par-couche.json`) croît avec la profondeur : **7,4 % à la couche 0**, 12,6 % à la couche 12, **20,1 % à la couche 23** (β₁). La couche 0 ne voit aucune dérive (son entrée est l'enchâssement et son KV ne dépend pas des experts) : ses 7,4 % sont le biais seul, et ils égalent les 7,29 % hors moteur. Le reste est la dérive : un expert changé en amont déplace le résidu, et gpt-oss amplifie toute perturbation par des bascules de routage (R1 : « d'abord par les bascules de routage ») ; ces bascules naturelles s'ajoutent aux échanges voulus. L'hypothèse « dérive amplifiée par le routage » rend compte du profil ; je n'ai pas séparé échanges voulus et bascules naturelles cellule par cellule (il faudrait le logit d'origine de chaque expert échangé, que le moteur n'écrit pas).

## 4. Témoins, cassures, seconds chemins

- **T0 (β = 0 au bit) : tient.** `P0b` (noyau neuf, vecteur de biais nul) égale `P0` sur les **5 120 empreintes64 de logits**, le **`.kld`** (SHA-256 3e43e7dc…edcb) et la **trace** (60a13ebd…a1d6), défauts égaux.
- **Le défaut n'a pas bougé** : le binaire construit depuis le HEAD d'avant l'option (`troncons-avant.exe`, SHA-256 7bc07cd4…a4d4) égale `P0` sur les **1 536 premiers pas** (trois fenêtres : empreintes et trace, 0 ligne différente). **Écart au protocole déclaré** : § 5 de la déclaration disait « 5 120 empreintes » ; j'ai fait trois fenêtres pour gagner ~13 min de carte (le cache n'agit pas sur les logits, donc le préfixe est une preuve des logits ; pas du `.kld` entier, ni des compteurs de défauts du préfixe). Dit, pas masqué.
- **Cassure du critère (β = 0,3)** : tombe (KL 0,089 > 0,07 ; pondéré 88,6 % < 95 %), dans la bande prédite.
- **Noyau** : `cargo test -p trc-noyaux routeur_biaise…` contre un oracle hôte écrit à part (160 tirages à égalités forcées, E = 6, 32, 256 ; biais nul égal au bit à `routeur_topk`) ; sa cassure (oracle sans biais) **tombe** (échec dès l'essai 7), le masque inversé diffère. Tests de noyaux, cache, modèle, ordo, programme : verts.
- **Second chemin du chiffre principal** : KL et premier choix par `juge kl` (chemin A) et par le lecteur `.kld` du juge de l'étage B (chemin B) : KL égale à 1e-6, mêmes premiers choix (`chemins_A_B_concordent` vrai sur les quatre passes). Le pondéré n'est calculé que par le chemin B (le CSV du juge n'a pas la marge).
- **Cassure de signe (β = −0,041)** : **non faite**. Lancée deux fois, arrêtée deux fois par mon propre garde-fou (RAM disponible sous 0,4 Go, puis swap 4,3 Go : d'autres processus de la machine occupaient la mémoire ; la première fois, mon analyse tournait en même temps). La logique du masque est par ailleurs couverte par le test du noyau (masque inversé) et par le signe du résultat (β > 0 retire des défauts).
- **Déterminisme** : les quatre générations de chaque bras donnent le même texte (SHA-256 du texte égal) et les mêmes défauts : β = 0,041 en ligne est déterministe sur ces runs. L'évaluation à β ≠ 0 n'a été passée qu'une fois.

## 5. Prédictions écrites avant, contre mesure

| grandeur | prédiction (06-, § 8) | mesure | |
|---|---|---|---|
| cellules changées, β₁ | 5 à 11 % | 12,86 % | **hors bande** (plus) |
| défauts, β₁ | −8 à −14 % | −10,03 % | dans la bande |
| KL, β₁ | 0,008 à 0,030 (centre 0,013) | **0,0314** | **hors bande**, 2,4 fois le centre |
| littéral, β₁ | 90 à 93 % | 88,55 % | **hors bande** (moins) |
| pondéré, β₁ | 97 à 99,5 % | 96,36 % | **hors bande** (moins) |
| β = 0,3 | KL 0,045 à 0,12 ; pondéré < 95 % ; défauts plus forts que −35 % | 0,089 ; 88,6 % ; −53,15 % | dans les bandes |
| vitesse | 0 à +6 % | +9,7 % en moyenne, **non distinguable du bruit** (§ 6) | voir § 6 |

Ma prédiction suivait la boucle ouverte ; elle ignorait la dérive (§ 3). L'erreur est dans le sens d'un levier plus cher que prévu.

## 6. Génération et vitesse [mes.]

`troncons mesurer`, mêmes options aux deux bras (20b, 238 emplacements, invite `invite-wiki-3000.txt` de 708 jetons, 256 jetons gloutons, repos de 10 s), ordre `A B B A A B B A` (deux blocs), A sans drapeau, B `--biais-cache 0,041`. Journaux : `mesures/mimetisme/P3/routeur-ligne/vitesse/`.

| passe | 1 A | 2 B | 3 B | 4 A | 5 A | 6 B | 7 B | 8 A |
|---|---|---|---|---|---|---|---|---|
| jetons/s | 4,465 | 5,009 | 4,130 | 3,738 | 3,450 | 3,234 | 4,494 | 3,728 |
| RAM disponible min (Go) | 1,96 | 3,24 | 3,45 | 2,74 | 1,45 | 0,48 | 0,37 | 2,96 |

- Moyennes : A 3,845, B 4,217 jetons/s (rapport 1,097). Écarts par bloc : +0,468 et +0,275 (même signe). **Bruit de référence** (étendue d'un bras contre lui-même) : A 1,015, B 1,775. **L'écart de 0,372 est inférieur au bruit : règle déclarée → « non distinguable du bruit ». Je n'annonce aucun gain de vitesse.**
- **La séance n'a pas été calme** : la RAM disponible est tombée à 0,37 Go et le swap est monté de 1,9 à 2,7 Go pendant les passes 5 à 7 (autres processus de la machine) ; les passes 5 et 6 sont les plus lentes. C'est la cause probable de l'étendue du bruit ; non vérifiée.
- **Ce qui est solide** (déterministe, identique aux quatre répétitions de chaque bras) : défauts par jeton généré **23,91 → 21,11 (−11,7 %)**, octets lus par jeton 287 → 253 Mo (−11,7 %), h de la génération 0,751 → 0,780. La part du temps passée à attendre les lectures est de 70 à 78 % du pas (`s_lectures / s_pas`) : un gain de vitesse du même ordre que les octets évités est plausible, **non établi**.
- **Avertissement connu** (`genome/08-placement-disque.md`) : un seul fichier `.trc` aux deux bras, donc le motif de requêtes de lecture est le même entre bras ; le niveau absolu (4 jetons/s à 238 emplacements) ne se compare à aucun autre dossier (le 20b à 362 emplacements faisait 10,9 jetons/s à O4, autre fichier-état, autre budget).
- **Les textes** des deux bras divergent dès le deuxième jeton (l'invite est du texte de wiki, sans gabarit de conversation ; les deux sorties sont médiocres). Aucune qualité de génération n'est évaluée ici.

## 7. Ce qui pourrait être faux

1. **Trois conditions à leur limite en même temps** (31 défauts de marge ; KL 0,0066 sous le seuil mais borne haute de l'intervalle 0,0006 au-dessus ; borne basse du pondéré à 0,00003 au-dessus de 95 %) : une autre série de fenêtres ou un autre texte peut faire basculer le verdict. « Tient » est l'estimation, pas la robustesse.
2. **Un budget (238), un texte (10 fenêtres de R1), un tirage par β** pour l'évaluation ; fenêtres non indépendantes (cache partagé) : l'intervalle sous-estime l'incertitude de population.
3. **Lecture de texte, pas génération libre** : en génération, un désaccord de premier choix dévie la suite ; la qualité des textes générés n'est pas mesurée (§ 6).
4. **Critère pondéré posé après lecture de N = 146** (`03-`), repris tel quel ; il ne mord pas avant la KL (JUGEMENT-N238 G1). À β₁ en ligne il est à 1,4 point au-dessus du seuil, alors que la KL est à 17 % sous le sien.
5. **Biais en f32 sur la carte**, additif, contre f64 hors moteur : des égalités de score peuvent se départager autrement (indice le plus bas) ; effet non isolé.
6. **Ordre des experts** : rendu par logit non biaisé décroissant ; 8,8 % des cellules ont le même ensemble dans un autre ordre que P0 (dérive), ce qui change l'ordre de sommation des sorties d'experts (arrondi f32) : effet de bruit numérique, non mesuré à part.
7. **Défauts mesurés avec le cache du moteur** (LRU global, règle de groupe) ; un autre cache (LFU, étage A du rapport d'affinage) n'est pas rejoué.
8. **Cassure de signe et répétition de β ≠ 0 non faites** (§ 4). **Preuve « défaut inchangé » sur trois fenêtres**, pas dix (§ 4).
9. **Vitesse** : séance non calme, aucun gain annoncé (§ 6).
10. **Préchargement et préremplissage par flux** non pris en charge avec l'option (refusés explicitement) ; l'effet du biais sur le préchargement n'est pas étudié.

## 8. Suite

1. **Décision** (Stone ou l'orchestrateur) : garder P3 comme levier « tient, à la limite » ou le durcir avant de s'en servir. Le coût réel (KL 0,031, premier choix littéral 88,6 %) est plus que le double de celui annoncé par l'étage B.
2. **Réduire la dérive** (l'effet dominant, § 3) : biais décroissant avec la profondeur (la part de cellules changées passe de 7 % à 20 % de la couche 0 à la 23), ou biais borné par la marge (échanger seulement si la marge est sous β, variante déjà listée à l'étage B), ou V2 « 4e/5e seul ». Chacun se mesure avec le banc de ce dossier (pilote et analyse prêts, 18 min la passe).
3. **Vitesse en séance calme** : refaire l'ABBA carte seule, machine libre (RAM disponible > 3 Go tout du long), au moins quatre paires ; le gain attendu est de l'ordre de −11,7 % d'octets par jeton.
4. **Génération libre** : perplexité et tâches sur textes générés avec invite en gabarit de conversation (le test de § 6 n'en dit rien).
5. Cassure de signe (β = −0,041) et un second tirage de β₁ pour le déterminisme de l'évaluation.

## 9. Techniques essayées (pour RECETTES.md)

- Second noyau à côté de l'ancien (`routeur_topk_biais`) plutôt que de modifier `routeur_topk` : le chemin par défaut n'exécute aucune ligne neuve, la preuve au bit est un diff de hachages. Le vecteur de biais (32 flottants) est monté depuis `Cache::emplacement_de` avant chaque routeur, sans arrêt du flux de calcul (l'hôte connaît l'état du cache dès la fin de `demander` de la couche précédente).
- Témoin par hachage de trace + `.kld` + empreintes de logits entre deux binaires : plus fort que « KL = 0 ».
- Échec : lancer l'analyse (lecture de 6 × 1 Go de `.kld`) pendant une passe a fait tomber la RAM disponible sous le garde-fou et tué la passe de cassure de signe ; ne jamais enchaîner analyse et passe.
- Profil de la part de cellules changées par couche : sépare le biais pur (couche 0, sans dérive) de la dérive (couches profondes) sans instrument supplémentaire.
