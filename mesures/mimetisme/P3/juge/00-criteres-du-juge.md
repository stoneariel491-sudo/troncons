# P3, juge indépendant : critères déclarés avant toute exécution de mon chemin

Écrit le 2026-10-27, rôle « juge P3 ». Commité avant d'avoir lancé une ligne de mon outil sur les données.
J'ai lu, avant d'écrire ceci : `00-seuils-declares.md`, `resultat.md`, `etage-A.log` (début), `p3_routage.py`,
05 § 2.2, `tri.md` (P3), `pistes/tropicale/garde-tropicale.md` (§ 5.4, § 7 : racines des cascades). Je connais donc
les chiffres à reproduire : les critères ci-dessous sont fixés en conséquence et ne bougeront pas.

## Mon chemin (rien de l'outil de l'expérimentateur n'est importé)

- Lecteur GGUF écrit de zéro (en-tête, paires clé-valeur, descripteurs de tenseurs, alignement), pour
  `blk.l.ffn_gate_inp.weight` et `.bias` du 20b. Pas `gguf_lecture.py`, pas `experts.py`.
- Logits en f64 par `np.einsum` sur h lu en memmap, couche par couche.
- Cache : LRU à horodatage (un tableau de 768 dates, victime = plus petite date parmi les résidents non épinglés),
  et non une `OrderedDict` ; règle de groupe de `trc-cache` (les k du groupe épinglés), accès dans le groupe par
  logit non biaisé décroissant, résidents de décision = contenu juste avant le groupe. Sélection V1 par `argpartition`.
- Mêmes définitions que la déclaration (§ 2), puisque c'est elles qu'on juge.

## Critères de reproduction

1. **Accord avec la capture** (mon lecteur) : ≥ 99,9 % des 122 640 cellules ; cassure : sans le biais du routeur, < 99 %.
2. **β = 0** : défauts 216 397 (N = 146) et 108 472 (N = 238) **à l'unité près** (définition déterministe). Sinon : non reproduit.
3. **Chiffre principal**, V1, grille officielle : à β = 0,1, variation des défauts −16,1 % et −22,6 %, part de cellules changées
   19,3 % et 16,6 % ; à β = 0,03 : −5,1 % et −7,5 %. Reproduit si chaque écart ≤ 0,3 point (des quasi-égalités de logits peuvent
   basculer entre deux produits matriciels). Franchissement de −10 % (interpolation linéaire en β sur une grille fine que je
   recalcule : 0,04 ; 0,05 ; 0,06 ; 0,07) : β ≈ 0,060 et 0,041, part de cellules 12,0 % et 7,3 %, écart toléré 0,005 en β et
   0,5 point en part.
4. **Verdict de la règle déclarée**, recalculé par moi sur la grille **officielle seule** (sans l'affinage post hoc) : il faut
   ≥ 10 % aux deux budgets et KL_prior = 0,309 × part ≤ 0,07 au même β.
5. **Témoins qui doivent pouvoir tomber** (les miens) : masque au hasard de même densité à β = 0,1 : |variation| < 2 % (aucun gain) ;
   β = −0,1 : défauts en hausse aux deux budgets ; V2 à β = 0,1 : −10,4 % et −15,3 % à 0,3 point près.
   Cassure de mon cache : rejouer le β = 0 avec les accès du groupe dans l'ordre **croissant** de logit doit changer le compte
   (sinon mon simulateur est aveugle à l'ordre), et un LRU sans épinglage aussi.

Par défaut : un critère non atteint = non reproduit = la piste ne tient pas sur ce point.

## Sondes déclarées (exploratoires, elles ne changent pas les critères ci-dessus)

- **S1, la constante de KL.** 0,309 = 0,0128 / (5 087 / 122 640) divise la KL retirée par **toutes** les bascules, cascades
  comprises ; or 59 % de ces bascules sont des secondaires (3 006 sur 5 087, racines 2 081, `garde-tropicale.md` § 5.4 et § 7). Une
  bascule forcée en boucle ouverte est une racine : en boucle fermée elle traîne ses suites. Je recalcule la KL a priori avec la
  constante par racine, 0,0128 / (2 081 / 122 640) = 0,755 [calc. sur hyp. : une bascule forcée cascade comme une racine subie,
  additivité], et je dis de quel côté de 0,038 et 0,07 elle tombe.
- **S2, ressemblance des bascules forcées aux bascules subies.** Pour les cellules changées à β = 0,06 (N = 146) : écart de logit
  entre l'expert retiré et l'expert ajouté, et poids softmax (sur z non biaisé) de l'expert retiré parmi les quatre d'origine ;
  en regard, les mêmes grandeurs pour l'échange 4e/5e des cellules à marge < 0,0095 (proxy des bascules subies). Si le poids
  retiré est du même ordre, la transposition de la constante n'est pas absurde sur ce point ; s'il est nettement plus grand, la
  KL a priori est sous-estimée.
