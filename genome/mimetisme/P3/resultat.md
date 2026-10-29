# P3, routage conditionné par le cache, borné par la marge : résultat de l'étage A (2026-10-27)

Seuils : `mesures/mimetisme/P3/00-seuils-declares.md` (commit 1606f9f, avant toute lecture de données). Outils et journaux commités sous
`outils/mimetisme/P3/` et `mesures/mimetisme/P3/`. Étiquettes : **[mes.]** mesuré ici, **[calc.]** calculé à partir de mesures commitées, **[mém.]** de mémoire, **[hyp.]** hypothèse.

## 1. Verdict

**OUVERT, étage B justifié.** Au seuil déclaré pour l'étage A :
- TOMBE (aucun β ne retire 5 % des défauts à N = 146) : **non**. Le levier a de l'amplitude.
- OUVERT, étage B justifié (≥ 10 % de défauts en moins aux deux budgets ET KL a priori ≤ 0,07 à ce β) : **oui**. Au franchissement de −10 %, la KL a priori vaut 0,037 (N = 146) et 0,023 (N = 238).
- TIENT : **hors de portée de l'étage A**. Il faut la KL excédentaire réelle (étage B), que je n'ai pas lancée : verrou de la carte tenu à mon arrivée (séance de vitesse ABBA du disque, qui surveille les lectures des autres processus), et ~2,5 h de passes f64 à RAM de pointe inconnue (consigne : au-delà de 2 Go, rendre le cahier). Le cahier est `cahier-etage-B.md`, les fichiers d'entrée sont prêts.

La KL a priori n'est pas une mesure : c'est 0,309 fois la part de cellules changées (constante de 05 § 2.2, un autre régime). Sa proximité avec le seuil de 0,038 (0,037) interdit de conclure
dans un sens ou dans l'autre sans l'étage B. Posé en une grandeur (`pour-le-memoire.md` § 5) : le seuil de succès exige que la KL par part de cellules changée reste sous κ_max = 0,317 (N = 146) et 0,520 (N = 238) ; le seul κ connu est celui des bascules spontanées, 0,309. L'étage A ne sait dire qu'une chose : **si la KL par cellule changée est celle des bascules spontanées, P3 est au seuil ; si elle est
deux fois plus forte, P3 est mort ; si elle est moindre, P3 tient largement.**

## 2. Ce qui est mesuré [mes.]

Modèle : gpt-oss-20b, 5 110 positions (10 fenêtres de 511), 24 couches, 122 640 cellules, 490 560 accès d'experts. Cache : LRU global à règle de groupe (celui de `trc-cache`), N = 146 (19 %)
et N = 238 (31 %), bascules causales (résidents = contenu du cache juste avant le groupe), poids de mélange non biaisés.

| | N = 146 (19 %) | N = 238 (31 %) |
|---|---|---|
| défauts à β = 0 | 216 397 (succès 0,5589) | 108 472 (succès 0,7789) |
| V1 (tous résidents), β = 0,03 | −5,1 % ; 6,0 % des cellules changent | −7,5 % ; 5,4 % |
| V1, β = 0,06 | −9,9 % ; 11,9 % | −14,3 % ; 10,5 % |
| V1, β = 0,1 | **−16,1 %** ; 19,3 % | **−22,6 %** ; 16,6 % |
| V1, β = 0,3 | −40,9 % ; 48,2 % | −53,0 % ; 37,7 % |
| V2 (4e/5e seul), β = 0,1 | −10,4 % ; 12,7 % | −15,3 % ; 11,4 % |
| franchissement de −10 % : β et part de cellules, V1 | β = 0,060 ; 12,0 % | β = 0,041 ; 7,3 % |
| KL a priori à ce franchissement [calc.] | 0,037 | 0,023 |
| même β avec LFU(8) au lieu du LRU (β = 0,1, V1) | −14,1 % (base LFU 170 888) | −22,3 % (base LFU 90 216) |
| β = −0,1 (on favorise les absents) | **+17,4 %** | **+28,2 %** |
| masque au hasard, même densité, β = 0,1 | +0,7 % (aucun gain) | +1,9 % |

Autres faits [mes.] :
- À β ≤ 0,1, **un seul expert change par cellule changée** (1,00 à 1,02) et l'expert de plus haut logit reste choisi dans 99,98 à 100 % des cellules : le levier ne touche que les derniers rangs.
  À β = 1 : 1,5 expert par cellule changée et 88 % de plus haut logit conservé ; à β = 3, les résidents ne bougent plus (160 défauts) : dégénéré.
- **Rendement** : chaque expert échangé évite 1,4 à 1,6 défaut à N = 146 (1,2 à N = 238) aux petits β : le défaut du jour, plus l'expert absent qui n'entre pas dans le cache, plus
  la récence du résident ainsi tenu. Un échange évite donc plus d'un défaut.
- **Les courbes V1 et V2 se superposent** dans le plan (part de cellules changées, défauts évités) : la monnaie du levier est le nombre de cellules changées, pas la forme du biais. Toucher
  autre chose que le 4e expert ne rapporte rien aux petits β.
- Dans les 10 fenêtres, le gain est stable : V1 β = 0,1 à N = 146, −16,1 ± 0,2 % (plus faible fenêtre −15,2 %) ; à N = 238, −22,6 ± 0,3 % (−21,2 %). Les fenêtres partagent leur cache : cet intervalle est une indication.
- Équivalent λ de l'article : Δavg moyen = 4,136 ; β = 0,06 correspond à λ = 0,0145 (l'article fait λ = 0,5, sur d'autres modèles).
- La borne E7 est **respectée** : V2 évite 0,53 à 0,78 fois le nombre de défauts de rang 4 sous la marge τ recomptés sous LRU (tolérance déclarée 1,5, non dérivée).
  En regard des chiffres publiés de E7 (LFU de demi-vie 8, N = 154) : V2 évite 1,7 % à τ = 0,01 et 4,4 % à τ = 0,03, E7 bornait à 3,1 % et 8,2 %.

Conversion en vitesse [calc.] : si le disque borne tout, vitesse ∝ 1/défauts : −10 % de défauts donne ×1,11, −16 % donne ×1,19, −23 % donne ×1,29. C'est plus que P1 (×1,083 au seuil)
et de l'ordre du plafond du préchargement (×1,21) ; P2 (simulé, optimiste) promet davantage mais engage de la RAM. P3 ne coûte aucun octet de plus, seulement de la qualité : c'est la KL qui décide.

## 3. Témoins

| Témoin | Résultat | Cassure |
|---|---|---|
| W1 recalcul des logits depuis h et le routeur F32 : même ensemble que la capture | **122 640/122 640 cellules**, 0 désaccord, écart de poids softmax ≤ 4,1e-8 (seuil 1e-4) | sans le biais du routeur : accord 0,6544, tombe comme exigé |
| W2 β = 0 | défauts 216 397 et 108 472 égaux à ceux du rejeu des ensembles du fichier de capture | β = 0,3 change 48 % des cellules (V1, N = 146, réel) |
| W3 signe | β = −0,3 : 320 902 > 216 397 et 213 863 > 108 472 | masque inversé +0,1 : +17,4 % et +28,2 % ; masque au hasard +0,1 : aucun gain (`cassures-reelles.json`) |
| W4 borne E7 | respectée, rapports 0,53 à 0,78 | non applicable (borne) ; tolérance 1,5 non dérivée, dite |
| W5 second chemin | `cache2.lru1` (Python indépendant) redonne exactement le compte de défauts sur les 16 lignes V1 | 1 000 cellules abîmées : le compte change (+2,3 % et +5,0 %) |
| W6 causalité | ensembles des 2 555 premières positions égaux sur trace entière et tronquée | un biais qui lit le futur est détecté par la troncature |

Témoin supplémentaire non déclaré : les quantiles de marge recalculés (0,05 : 0,0059296 ; 0,5 : 0,083156 ; 0,75 : 0,171145) égalent ceux de E7 et M3 à 3e-6 près en relatif : le recalcul des logits est
indépendant des journaux du moteur et retombe sur eux. Autre : le LFU de demi-vie 8 implémenté pour l'affinage redonne le taux de succès de E7 à N = 154 (0,66955 contre 0,66955, tolérance déclarée 0,002).
Témoins de la machine seule (logits synthétiques) : `temoins-synthetiques.log`.

## 4. Ce qui pourrait être faux

1. **Boucle ouverte.** Les ensembles sont calculés sur la trajectoire du modèle exact. Dans un modèle réellement biaisé, h dérive de l'exact à chaque couche (une bascule voulue se propage comme une bascule subie :
   26,6 % à la couche suivante, 05 § 2.2). Les défauts ne sont donc pas exactement ceux d'un routeur biaisé en ligne. Ni l'étage A ni le B ne le mesurent ; le routeur biaisé dans le moteur est l'épreuve finale.
2. **La KL a priori est une hypothèse.** 0,309 est (0,0145 − 0,00168)/(5 087/122 640) : la KL retirée par l'imposition du routage divisée par la part de bascules **entre deux moteurs presque exacts**.
   Ces bascules ont une marge médiane de 0,0095 ; les nôtres ont une marge jusqu'à β = 0,06 à 0,1. Le coût par bascule dépend de la différence des sorties des deux experts et du poids du 4e : il peut croître
   avec la marge, ce qui ferait pencher vers « tombe ». Je ne sais pas dans quel sens l'erreur va ; c'est pourquoi le verdict reste « ouvert ».
3. **Texte de lecture, pas de génération.** Les 5 110 positions sont du texte wiki évalué par fenêtres de 511 ; le cache y suit l'ordre jeton par jeton, couche par couche (c'est l'ordre d'une génération),
   mais la localité d'un texte relu n'est pas celle d'une réponse libre (P1 pose la même limite). Le taux de succès simulé (0,56 à N = 146, LRU) n'a pas été confronté à celui du moteur.
4. **Budgets.** N = 146 et 238 viennent du tri (19 % et 31 %). Le budget réel du moteur sur la machine de Stone n'est pas lu ici.
5. **Le premier choix de la sortie ≥ 95 %** du seuil de l'étage B n'est pas mesuré : seul le plus haut logit d'expert (99,98 à 100 %) l'est, et ce n'est pas la même grandeur.
6. **Poids non biaisés** : repris de l'article et de `routage_impose`. Un biais sur les poids aussi aurait un autre coût ; non testé.
7. **Fenêtres non indépendantes.** L'écart-type par fenêtre (±0,1 à 0,3 %) sous-estime l'incertitude de population.
8. **Gain publié non reproduit.** Les 35 % → 16 % de défaut de l'article viennent d'autres modèles (cache = N/2). Les deux ne sont pas comparables (autres modèles, 50 % d'experts en cache, λ jusqu'à 0,5) ; je ne les rapproche pas.
9. **Constante E7/LFU.** L'affinage est post hoc (déclaré avant lancement, après avoir vu la courbe officielle) ; les seuils n'ont pas bougé.

## 5. Suite

1. **Étage B** (la seule mesure qui peut faire dire « tient ») : `cahier-etage-B.md`. Commencer par les deux fichiers qui encadrent le franchissement à N = 146 : β = 0,06 et 0,07 ; au contrôle β = 0 (KL nulle au bit) et au fichier de cassure (1 % de 4e experts remplacés au hasard). Après la levée du verrou et un relevé de la RAM de pointe.
2. Si l'étage B tient : écrire le biais dans `trc-cache`/l'ordonnanceur du moteur (un masque de résidents ajouté aux logits avant le top-4 ; poids non biaisés) et mesurer en ABBA sur génération, avec P1 (LFU, le gain persiste) et P2.
3. Si l'étage B tombe : la courbe (part de cellules changées, KL réelle) donne la pente de P3 ; la comparer à la barre de P6 (KL par octet économisé du mode rapide).
4. Variantes non essayées, cheap en boucle ouverte : biais proportionnel à la récence du résident, bornage explicite par la marge (échanger seulement si marge < β et poids du 4e < w), biais par couche selon la distribution des marges de la couche.

## 6. Techniques essayées (pour RECETTES.md)

- **Reproduire le routeur depuis les entrées capturées** : h (f32) × poids du routeur F32 du GGUF + biais = les 32 logits ; les 4 experts de la capture sont retrouvés 122 640 fois sur 122 640. Évite toute passe du modèle
  pour l'étude du routage ; lecture légère (le routeur : ~9 Mo ; h : 1,4 Go, une fois le verrou levé). Cassure : sans le biais du routeur, 65 % d'accord.
- **Essai léger du chemin réel avant la lecture lourde** (64 positions, 24 couches) : un bogue de format se découvre en 20 Mo et non en 1,4 Go.
- **Pilote qui attend le verrou** (relevé de la présence du fichier toutes les 60 s) : la mesure part toute seule à la levée ; elle a duré 10 min.
- **Masque au hasard de même densité** comme cassure de W3 : plus informatif que le biais négatif, dont le classement est identique à celui du masque inversé (cassure équivalente par construction, dit).
- **Une constante de KL prise ailleurs** est utile comme seuil de lancement d'une passe lourde, pas comme résultat.
- Échecs : le premier recalcul de `rejouer_cache2` portait un `if False` oublié (E posé à 32 en dur) ; corrigé avant tout chiffre.

## 7. Sources

- Skliar, van Rozendaal, Lepert, Boinovski, van Baalen, Nagel, Whatmough, Ehteshami Bejnordi, « Mixture of Cache-Conditional Experts for Efficient Mobile Device Inference », arXiv 2412.00099 v2, 24 juin 2025, TMLR 2025.
  https://arxiv.org/html/2412.00099v2 ; consultée le 2026-10-27 [lue : méthode, tableau de défauts, perplexité].
- Dépôt : `genome/05-synthese.md` § 2.2 ; `mesures/mimetisme/humain/e7-marge-20b.json` ; `mesures/mimetisme/mathematiques/m3_marges_20b.json` ; `outils/mimetisme/ingenierie/cache2.py` ; `outils/mimetisme/humain/e7_marge.py` ; `moteur/crates/trc-cache/src/lib.rs`.
